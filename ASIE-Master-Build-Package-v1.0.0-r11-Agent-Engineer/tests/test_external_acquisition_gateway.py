from __future__ import annotations

from collections import deque
from pathlib import Path
from typing import Any

import pytest

from backend.external_acquisition import (
    AcquisitionAuditSink,
    ExternalAcquisitionError,
    ExternalAcquisitionPolicy,
    ExternalConnectorRegistry,
    ExternalConnectorSpec,
    GovernedExternalAcquisitionGateway,
    HostRateLimiter,
    _PinnedHTTPSConnection,
)


PACKAGE_ROOT = Path(__file__).resolve().parents[1]


class FakeResponse:
    def __init__(self, *, url: str, body: bytes, content_type: str, status: int = 200) -> None:
        self._url = url
        self._body = body
        self.status = status
        self.headers = {
            "Content-Type": content_type,
            "Content-Length": str(len(body)),
        }

    def read(self, amount: int = -1) -> bytes:
        return self._body if amount < 0 else self._body[:amount]

    def geturl(self) -> str:
        return self._url

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None


class FakeOpener:
    def __init__(self, *responses: FakeResponse) -> None:
        self.responses = deque(responses)
        self.requests: list[Any] = []

    def open(self, request: Any, timeout: float) -> FakeResponse:
        self.requests.append((request, timeout))
        if not self.responses:
            raise AssertionError("unexpected external request")
        return self.responses.popleft()


class DummySocket:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


class RecordingTLSContext:
    def __init__(self) -> None:
        self.server_names: list[str] = []

    def wrap_socket(self, sock: DummySocket, *, server_hostname: str) -> DummySocket:
        self.server_names.append(server_hostname)
        return sock


def public_resolver(host: str, port: int):
    assert host
    assert port == 443
    return [(2, 1, 6, "", ("8.8.8.8", port))]


def private_resolver(host: str, port: int):
    return [(2, 1, 6, "", ("127.0.0.1", port))]


def enabled_policy(*, hosts: tuple[str, ...] = ("api.example.com",), max_bytes: int = 2_097_152):
    return ExternalAcquisitionPolicy(
        enabled=True,
        allowed_hosts=hosts,
        timeout_seconds=4,
        max_response_bytes=max_bytes,
        min_interval_seconds=0,
        user_agent="ASIE-Test/1.0",
        robots_failure_mode="deny",
    )


def test_policy_is_disabled_and_empty_by_default() -> None:
    policy = ExternalAcquisitionPolicy()
    assert policy.enabled is False
    assert policy.allowed_hosts == ()
    assert policy.snapshot()["private_networks_blocked"] is True
    assert policy.snapshot()["stores_api_keys"] is False


def test_disabled_policy_blocks_before_transport() -> None:
    opener = FakeOpener()
    gateway = GovernedExternalAcquisitionGateway(
        ExternalAcquisitionPolicy(),
        resolver=public_resolver,
        opener=opener,
    )
    with pytest.raises(ExternalAcquisitionError, match="external_network_disabled_by_policy"):
        gateway.fetch_json(source_id="test", url="https://api.example.com/data")
    assert opener.requests == []


def test_https_allowlist_and_private_network_guards() -> None:
    gateway = GovernedExternalAcquisitionGateway(enabled_policy(), resolver=public_resolver, opener=FakeOpener())
    with pytest.raises(ExternalAcquisitionError, match="external_https_required"):
        gateway.fetch_json(source_id="test", url="http://api.example.com/data")
    with pytest.raises(ExternalAcquisitionError, match="external_host_not_allowlisted"):
        gateway.fetch_json(source_id="test", url="https://other.example.com/data")

    private_gateway = GovernedExternalAcquisitionGateway(
        enabled_policy(), resolver=private_resolver, opener=FakeOpener()
    )
    with pytest.raises(ExternalAcquisitionError, match="external_private_or_reserved_address_blocked"):
        private_gateway.fetch_json(source_id="test", url="https://api.example.com/data")


def test_pinned_https_connection_uses_validated_ip_and_original_tls_name() -> None:
    resolver_calls: list[tuple[str, int]] = []
    connection_attempts: list[tuple[str, int]] = []
    tls_context = RecordingTLSContext()

    def resolver(host: str, port: int):
        resolver_calls.append((host, port))
        return [
            (2, 1, 6, "", ("8.8.8.8", port)),
            (2, 1, 6, "", ("1.1.1.1", port)),
        ]

    connection = _PinnedHTTPSConnection(
        "api.example.com",
        resolver=resolver,
        context=tls_context,
    )

    def create_connection(
        address: tuple[str, int],
        timeout: object,
        source_address: object,
    ) -> DummySocket:
        connection_attempts.append(address)
        return DummySocket()

    connection._create_connection = create_connection
    connection.connect()

    assert resolver_calls == [("api.example.com", 443)]
    assert connection_attempts == [("8.8.8.8", 443)]
    assert tls_context.server_names == ["api.example.com"]


def test_pinned_https_connection_blocks_private_answer_before_socket_creation() -> None:
    connection = _PinnedHTTPSConnection(
        "api.example.com",
        resolver=private_resolver,
        context=RecordingTLSContext(),
    )
    socket_attempted = False

    def create_connection(
        address: tuple[str, int],
        timeout: object,
        source_address: object,
    ) -> DummySocket:
        nonlocal socket_attempted
        socket_attempted = True
        return DummySocket()

    connection._create_connection = create_connection
    with pytest.raises(
        ExternalAcquisitionError,
        match="external_private_or_reserved_address_blocked",
    ):
        connection.connect()
    assert socket_attempted is False


def test_default_gateway_bypasses_environment_proxy_and_reports_dns_pinning() -> None:
    gateway = GovernedExternalAcquisitionGateway(
        enabled_policy(),
        resolver=public_resolver,
    )
    handler_names = {
        handler.__class__.__name__
        for handler in gateway.opener.handlers
    }
    assert "ProxyHandler" not in handler_names
    assert "_PinnedHTTPSHandler" in handler_names
    assert gateway.status()["policy"]["dns_connection_pinning"] is True
    assert gateway.status()["policy"]["environment_proxy_bypass"] is True


def test_api_json_fetch_returns_review_required_envelope() -> None:
    opener = FakeOpener(
        FakeResponse(
            url="https://api.example.com/data",
            body=b'{"value": 42, "source": "official"}',
            content_type="application/json; charset=utf-8",
        )
    )
    gateway = GovernedExternalAcquisitionGateway(
        enabled_policy(),
        resolver=public_resolver,
        opener=opener,
        rate_limiter=HostRateLimiter(0),
    )
    result = gateway.fetch_json(source_id="OFFICIAL_TEST", url="https://api.example.com/data")

    assert result["payload"] == {"value": 42, "source": "official"}
    assert result["network_attempted"] is True
    assert result["review_status"] == "review_required"
    assert result["eligible_for_controlled_assumptions"] is False
    assert len(result["sha256"]) == 64
    assert gateway.status()["audit"]["event_count"] == 1
    assert gateway.status()["audit"]["events"][0]["outcome"] == "success"


def test_response_size_and_content_type_are_bounded() -> None:
    oversized = FakeOpener(
        FakeResponse(url="https://api.example.com/data", body=b"12345", content_type="application/json")
    )
    gateway = GovernedExternalAcquisitionGateway(
        enabled_policy(max_bytes=4), resolver=public_resolver, opener=oversized
    )
    with pytest.raises(ExternalAcquisitionError, match="external_response_too_large"):
        gateway.fetch_json(source_id="test", url="https://api.example.com/data")

    wrong_type = FakeOpener(
        FakeResponse(url="https://api.example.com/data", body=b"{}", content_type="text/html")
    )
    gateway = GovernedExternalAcquisitionGateway(enabled_policy(), resolver=public_resolver, opener=wrong_type)
    with pytest.raises(ExternalAcquisitionError, match="unexpected_content_type"):
        gateway.fetch_json(source_id="test", url="https://api.example.com/data")


def test_crawl_obeys_robots_before_reading_page() -> None:
    denied_opener = FakeOpener(
        FakeResponse(
            url="https://www.example.com/robots.txt",
            body=b"User-agent: *\nDisallow: /private\n",
            content_type="text/plain",
        )
    )
    gateway = GovernedExternalAcquisitionGateway(
        enabled_policy(hosts=("www.example.com",)), resolver=public_resolver, opener=denied_opener
    )
    with pytest.raises(ExternalAcquisitionError, match="robots_policy_denied"):
        gateway.fetch_html(source_id="SITE", url="https://www.example.com/private/report")
    assert len(denied_opener.requests) == 1

    allowed_opener = FakeOpener(
        FakeResponse(
            url="https://www.example.com/robots.txt",
            body=b"User-agent: *\nAllow: /public\n",
            content_type="text/plain",
        ),
        FakeResponse(
            url="https://www.example.com/public/report",
            body="<html><title>تقرير</title></html>".encode("utf-8"),
            content_type="text/html; charset=utf-8",
        ),
    )
    gateway = GovernedExternalAcquisitionGateway(
        enabled_policy(hosts=("www.example.com",)), resolver=public_resolver, opener=allowed_opener
    )
    result = gateway.fetch_html(source_id="SITE", url="https://www.example.com/public/report")
    assert "<title>تقرير</title>" in result["payload"]
    assert result["mode"] == "crawl"
    assert len(allowed_opener.requests) == 2


def test_connector_registry_requires_terms_and_allowlist_without_secrets() -> None:
    policy = enabled_policy(hosts=("geocode.googleapis.com", "*.data.gov.sa"))
    registry = ExternalConnectorRegistry(policy)

    with pytest.raises(ExternalAcquisitionError, match="connector_terms_review_required"):
        registry.register(
            ExternalConnectorSpec(
                connector_id="unreviewed",
                host="geocode.googleapis.com",
                source_class="location",
                purpose="reverse geocoding",
                terms_reviewed=False,
            )
        )

    registered = registry.register(
        ExternalConnectorSpec(
            connector_id="google-geocoding-v4",
            host="geocode.googleapis.com",
            source_class="location",
            purpose="forward and reverse geocoding",
            terms_reviewed=True,
            requires_api_key=True,
        )
    )
    assert registered["status"] == "ready"
    assert registered["stores_api_key"] is False
    assert registry.snapshot()["stores_credentials"] is False


def test_audit_sink_redacts_credentials_and_payloads() -> None:
    sink = AcquisitionAuditSink()
    event = sink.record(
        event_type="external_acquisition",
        outcome="rejected",
        metadata={"api_key": "secret", "headers": {"Authorization": "Bearer x"}, "host": "example.com"},
    )
    assert event["metadata"]["api_key"] == "[redacted]"
    assert event["metadata"]["headers"] == "[redacted]"
    assert event["metadata"]["host"] == "example.com"
    assert event["payload_stored"] is False


def test_gateway_is_not_wired_into_frozen_runtime() -> None:
    source = (PACKAGE_ROOT / "backend" / "external_acquisition.py").read_text(encoding="utf-8")
    assert "ProjectRunWorkflow" not in source
    assert "SnapshotAssembly" not in source
    assert "backend.aas_kernel" not in source
    assert "backend.system_bus" not in source
    assert '"eligible_for_controlled_assumptions": False' in source
    assert '"review_status": "review_required"' in source
