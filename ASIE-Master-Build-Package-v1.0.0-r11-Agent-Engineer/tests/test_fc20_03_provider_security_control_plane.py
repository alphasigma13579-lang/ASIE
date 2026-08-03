from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
from threading import Event
from types import SimpleNamespace
from typing import Any, Mapping
from urllib.error import URLError
from urllib.parse import urlsplit

import pytest

from backend.external_acquisition import AcquisitionAuditSink, ExternalAcquisitionError
from backend.live_provider_clients import GovernedProviderTransport
from backend.provider_security_control_plane import (
    ProviderRequestContext,
    ProviderRuntimePolicy,
    ProviderSecurityControlPlane,
    ProviderSecurityError,
    SQLiteProviderControlStore,
    TrustedProviderScope,
)


def policy(
    provider_id: str = "tavily",
    *,
    state: str = "enabled",
    kill_switch: bool = False,
    requests: int = 3,
    cost_units: int = 10,
    threshold: int = 2,
    cooldown: int = 30,
    max_get_attempts: int = 2,
) -> ProviderRuntimePolicy:
    hosts = {
        "tavily": ("api.tavily.com",),
        "pinecone": ("api.pinecone.io", "*.pinecone.io"),
        "google_maps_platform": ("geocode.googleapis.com", "places.googleapis.com"),
    }[provider_id]
    operations = {
        "tavily": ("search", "crawl"),
        "pinecone": ("describe_index", "search_text"),
        "google_maps_platform": ("geocode_address", "search_places_text"),
    }[provider_id]
    preflight = ("describe_index",) if provider_id == "pinecone" else ()
    return ProviderRuntimePolicy(
        provider_id=provider_id,
        state=state,
        kill_switch=kill_switch,
        allowed_hosts=hosts,
        allowed_operations=operations,
        preflight_operations=preflight,
        contract_version=f"test-{provider_id}-v1",
        timeout_seconds=5.0,
        max_response_bytes=4_096,
        requests_per_window=requests,
        cost_units_per_window=cost_units,
        window_seconds=60,
        failure_threshold=threshold,
        circuit_cooldown_seconds=cooldown,
        max_get_attempts=max_get_attempts,
        retry_delay_seconds=0.01,
    )


def context(
    operation: str,
    *,
    organization_id: str = "org-a",
    project_id: str = "project-a",
    cost_units: int = 1,
    preflight: bool = False,
) -> ProviderRequestContext:
    if preflight:
        scope = TrustedProviderScope.for_platform_preflight()
    else:
        principal = SimpleNamespace(
            user_id="user-a",
            session_id="session-a",
            organization_id=organization_id,
            role="analyst",
        )
        scope = TrustedProviderScope.for_tenant(
            principal=principal,
            project_id=project_id,
            project_organization_resolver=lambda _: organization_id,
        )
    return scope.request_context(operation, cost_units=cost_units)


def test_untrusted_mapping_is_rejected_before_quota_store() -> None:
    plane = ProviderSecurityControlPlane(
        {"tavily": policy()},
        enabled=True,
    )
    with pytest.raises(ProviderSecurityError, match="provider_request_context_not_trusted"):
        plane.authorize(
            provider_id="tavily",
            url="https://api.tavily.com/search",
            context={
                "organization_id": "org-forged",
                "project_id": "project-forged",
                "operation": "search",
            },  # type: ignore[arg-type]
        )
    assert getattr(plane.store, "_usage") == {}


def test_tenant_scope_requires_membership_and_authoritative_project_ownership() -> None:
    principal = SimpleNamespace(
        user_id="user-a",
        session_id="session-a",
        organization_id="org-a",
        role="analyst",
    )
    with pytest.raises(ProviderSecurityError, match="provider_project_tenant_mismatch"):
        TrustedProviderScope.for_tenant(
            principal=principal,
            project_id="project-b",
            project_organization_resolver=lambda _: "org-b",
        )
    with pytest.raises(ProviderSecurityError, match="provider_active_tenant_membership_required"):
        TrustedProviderScope.for_tenant(
            principal=SimpleNamespace(
                user_id="platform-admin",
                session_id="session-admin",
                organization_id="org-a",
                role=None,
            ),
            project_id="project-a",
            project_organization_resolver=lambda _: "org-a",
        )


def test_control_plane_is_disabled_by_default_and_exposes_no_secret_values(monkeypatch) -> None:
    for name in (
        "ASIE_PROVIDER_CONTROL_PLANE_ENABLED",
        "ASIE_PROVIDER_GLOBAL_KILL_SWITCH",
        "ASIE_PROVIDER_TAVILY_STATE",
        "TAVILY_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("TAVILY_API_KEY", "must-not-appear")
    plane = ProviderSecurityControlPlane.from_env()
    status = plane.status()
    assert status["enabled"] is False
    assert status["network_authorized"] is False
    assert status["secret_values_exposed"] is False
    assert "must-not-appear" not in json.dumps(status)
    with pytest.raises(ProviderSecurityError, match="provider_control_plane_disabled"):
        plane.authorize(
            provider_id="tavily",
            url="https://api.tavily.com/search",
            context=context("search"),
        )


@pytest.mark.parametrize(
    ("provider_id", "url", "operation"),
    [
        ("tavily", "https://evil.example/search", "search"),
        ("pinecone", "https://pinecone.io/indexes", "describe_index"),
        ("pinecone", "https://api.pinecone.io.evil.example/indexes", "describe_index"),
    ],
)
def test_provider_id_is_cryptographically_bounded_to_its_host(
    provider_id: str,
    url: str,
    operation: str,
) -> None:
    plane = ProviderSecurityControlPlane(
        {provider_id: policy(provider_id, state="enabled")},
        enabled=True,
    )
    with pytest.raises(ProviderSecurityError, match="provider_host_mismatch"):
        plane.authorize(
            provider_id=provider_id,
            url=url,
            context=context(operation, preflight=operation == "describe_index"),
        )


def test_preflight_state_allows_only_explicit_preflight_operation() -> None:
    plane = ProviderSecurityControlPlane(
        {"pinecone": policy("pinecone", state="preflight")},
        enabled=True,
    )
    admission = plane.authorize(
        provider_id="pinecone",
        url="https://api.pinecone.io/indexes/vision2030-kb",
        context=context("describe_index", preflight=True),
    )
    assert admission.operation == "describe_index"
    with pytest.raises(ProviderSecurityError, match="provider_not_enabled_for_live_operation"):
        plane.authorize(
            provider_id="pinecone",
            url="https://tenant.svc.region.pinecone.io/records/namespaces/a/search",
            context=context("search_text"),
        )
    with pytest.raises(ProviderSecurityError, match="provider_preflight_operation_not_allowed"):
        plane.authorize(
            provider_id="pinecone",
            url="https://tenant.svc.region.pinecone.io/records/namespaces/a/search",
            context=context("search_text", preflight=True),
        )


def test_quota_and_cost_budget_are_tenant_scoped_and_atomic() -> None:
    plane = ProviderSecurityControlPlane(
        {"tavily": policy(requests=2, cost_units=3)},
        enabled=True,
    )
    first_admission = plane.authorize(
        provider_id="tavily",
        url="https://api.tavily.com/search",
        context=context("search", cost_units=1),
    )
    plane.authorize(
        provider_id="tavily",
        url="https://api.tavily.com/search",
        context=context("search", cost_units=1),
    )
    with pytest.raises(ProviderSecurityError, match="provider_request_quota_exhausted"):
        plane.authorize(
            provider_id="tavily",
            url="https://api.tavily.com/search",
            context=context("search", cost_units=1),
        )
    other_tenant = plane.authorize(
        provider_id="tavily",
        url="https://api.tavily.com/search",
        context=context("search", organization_id="org-b", cost_units=3),
    )
    assert other_tenant.scope_ref != first_admission.scope_ref
    with pytest.raises(ProviderSecurityError, match="provider_cost_budget_exhausted"):
        plane.authorize(
            provider_id="tavily",
            url="https://api.tavily.com/search",
            context=context("search", organization_id="org-c", cost_units=4),
        )


def test_circuit_opens_after_transient_failures_and_recovers_after_cooldown() -> None:
    now = [100.0]
    plane = ProviderSecurityControlPlane(
        {"tavily": policy(threshold=2, cooldown=30)},
        enabled=True,
        clock=lambda: now[0],
    )
    first = plane.authorize(
        provider_id="tavily",
        url="https://api.tavily.com/search",
        context=context("search"),
    )
    plane.record_failure(first, transient=True)
    second = plane.authorize(
        provider_id="tavily",
        url="https://api.tavily.com/search",
        context=context("search"),
    )
    plane.record_failure(second, transient=True)
    with pytest.raises(ProviderSecurityError, match="provider_circuit_open"):
        plane.authorize(
            provider_id="tavily",
            url="https://api.tavily.com/search",
            context=context("search"),
        )
    now[0] = 131.0
    recovered = plane.authorize(
        provider_id="tavily",
        url="https://api.tavily.com/search",
        context=context("search"),
    )
    assert recovered.provider_id == "tavily"


@pytest.mark.parametrize(
    ("global_kill", "provider_kill", "reason"),
    [
        (True, False, "provider_global_kill_switch_active"),
        (False, True, "provider_kill_switch_active"),
    ],
)
def test_kill_switches_fail_before_any_network_admission(
    global_kill: bool,
    provider_kill: bool,
    reason: str,
) -> None:
    plane = ProviderSecurityControlPlane(
        {"tavily": policy(kill_switch=provider_kill)},
        enabled=True,
        global_kill_switch=global_kill,
    )
    with pytest.raises(ProviderSecurityError, match=reason):
        plane.authorize(
            provider_id="tavily",
            url="https://api.tavily.com/search",
            context=context("search"),
        )


class FakeResponse:
    status = 200

    def __init__(self, url: str) -> None:
        self.url = url

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None

    def geturl(self) -> str:
        return self.url

    def read(self, amount: int = -1) -> bytes:
        return b'{"results":[]}'


class RetryOnceOpener:
    def __init__(self) -> None:
        self.calls = 0
        self.timeouts: list[float] = []

    def open(self, request: Any, timeout: float) -> FakeResponse:
        self.calls += 1
        self.timeouts.append(timeout)
        if self.calls == 1:
            raise URLError("temporary")
        return FakeResponse(request.full_url)


class InvalidResponseOpener(RetryOnceOpener):
    def open(self, request: Any, timeout: float) -> FakeResponse:
        self.calls += 1
        self.timeouts.append(timeout)
        response = FakeResponse(request.full_url)
        response.read = lambda amount=-1: b'{}'  # type: ignore[method-assign]
        return response


class FakeRateLimiter:
    def wait(self, host: str) -> None:
        return None


class FakeGateway:
    def __init__(self, opener: RetryOnceOpener) -> None:
        self.policy = SimpleNamespace(
            timeout_seconds=8.0,
            max_response_bytes=8_192,
            user_agent="ASIE-Test",
        )
        self.opener = opener
        self.rate_limiter = FakeRateLimiter()
        self.audit_sink = AcquisitionAuditSink()
        self.validations = 0

    def _validate_url(self, url: str):
        self.validations += 1
        return urlsplit(url)


def test_governed_transport_retries_get_once_without_logging_secret() -> None:
    opener = RetryOnceOpener()
    gateway = FakeGateway(opener)
    sleeps: list[float] = []
    plane = ProviderSecurityControlPlane(
        {"google_maps_platform": policy("google_maps_platform", max_get_attempts=2)},
        enabled=True,
    )
    transport = GovernedProviderTransport(
        gateway=gateway,
        control_plane=plane,
        sleep=sleeps.append,
    )
    result = transport.request_json(
        provider_id="google_maps_platform",
        method="GET",
        url="https://geocode.googleapis.com/v4/geocode/address/riyadh",
        headers={"X-Goog-Api-Key": "must-not-appear"},
        security_context=context("geocode_address"),
    )
    assert opener.calls == 2
    assert opener.timeouts == [5.0, 5.0]
    assert sleeps == [0.01]
    assert gateway.validations >= 3
    assert result["provider_contract_version"] == "test-google_maps_platform-v1"
    assert "must-not-appear" not in json.dumps(gateway.audit_sink.snapshot())


def test_governed_transport_cancels_before_network_and_between_retries() -> None:
    opener = RetryOnceOpener()
    gateway = FakeGateway(opener)
    plane = ProviderSecurityControlPlane(
        {"google_maps_platform": policy("google_maps_platform", max_get_attempts=2)},
        enabled=True,
    )
    transport = GovernedProviderTransport(gateway=gateway, control_plane=plane)
    cancelled = Event()
    cancelled.set()
    with pytest.raises(ExternalAcquisitionError, match="provider_request_cancelled"):
        transport.request_json(
            provider_id="google_maps_platform",
            method="GET",
            url="https://geocode.googleapis.com/v4/geocode/address/riyadh",
            security_context=context("geocode_address"),
            cancellation_signal=cancelled,
        )
    assert opener.calls == 0

    cancelled.clear()

    def cancel_during_backoff(_: float) -> None:
        cancelled.set()

    transport = GovernedProviderTransport(
        gateway=gateway,
        control_plane=plane,
        sleep=cancel_during_backoff,
    )
    with pytest.raises(ExternalAcquisitionError, match="provider_request_cancelled"):
        transport.request_json(
            provider_id="google_maps_platform",
            method="GET",
            url="https://geocode.googleapis.com/v4/geocode/address/riyadh",
            security_context=context("geocode_address"),
            cancellation_signal=cancelled,
        )
    assert opener.calls == 1


def test_response_contract_violation_fails_before_transport_success_audit() -> None:
    opener = InvalidResponseOpener()
    gateway = FakeGateway(opener)
    plane = ProviderSecurityControlPlane({"tavily": policy()}, enabled=True)
    transport = GovernedProviderTransport(gateway=gateway, control_plane=plane)
    with pytest.raises(ExternalAcquisitionError, match="provider_response_contract_violation:tavily:search"):
        transport.request_json(
            provider_id="tavily",
            url="https://api.tavily.com/search",
            security_context=context("search"),
            body={"query": "x"},
        )
    events = gateway.audit_sink.snapshot()
    assert any(event["outcome"] == "failed" for event in events)
    assert not any(event["outcome"] == "success" for event in events)


def test_disabled_control_plane_denies_before_gateway_validation_or_open() -> None:
    opener = RetryOnceOpener()
    gateway = FakeGateway(opener)
    transport = GovernedProviderTransport(
        gateway=gateway,
        control_plane=ProviderSecurityControlPlane(
            {"tavily": policy()},
            enabled=False,
        ),
    )
    with pytest.raises(ExternalAcquisitionError, match="provider_control_plane_disabled"):
        transport.request_json(
            provider_id="tavily",
            url="https://api.tavily.com/search",
            headers={"Authorization": "Bearer must-not-appear"},
            body={"query": "x"},
            security_context=context("search"),
        )
    assert gateway.validations == 0
    assert opener.calls == 0
    assert "must-not-appear" not in json.dumps(gateway.audit_sink.snapshot())


def test_sqlite_store_persists_quota_across_control_plane_instances(tmp_path) -> None:
    database = tmp_path / "provider-control.sqlite3"
    first_plane = ProviderSecurityControlPlane(
        {"tavily": policy(requests=2, cost_units=10)},
        enabled=True,
        store=SQLiteProviderControlStore(str(database)),
    )
    second_plane = ProviderSecurityControlPlane(
        {"tavily": policy(requests=2, cost_units=10)},
        enabled=True,
        store=SQLiteProviderControlStore(str(database)),
    )
    first_plane.authorize(
        provider_id="tavily",
        url="https://api.tavily.com/search",
        context=context("search"),
    )
    second_plane.authorize(
        provider_id="tavily",
        url="https://api.tavily.com/search",
        context=context("search"),
    )
    with pytest.raises(ProviderSecurityError, match="provider_request_quota_exhausted"):
        first_plane.authorize(
            provider_id="tavily",
            url="https://api.tavily.com/search",
            context=context("search"),
        )


def test_sqlite_admission_is_atomic_under_concurrent_workers(tmp_path) -> None:
    plane = ProviderSecurityControlPlane(
        {"tavily": policy(requests=5, cost_units=100)},
        enabled=True,
        store=SQLiteProviderControlStore(str(tmp_path / "atomic.sqlite3")),
    )

    def attempt(_: int) -> str:
        try:
            plane.authorize(
                provider_id="tavily",
                url="https://api.tavily.com/search",
                context=context("search"),
            )
            return "allowed"
        except ProviderSecurityError as exc:
            return str(exc)

    with ThreadPoolExecutor(max_workers=10) as executor:
        outcomes = list(executor.map(attempt, range(20)))
    assert outcomes.count("allowed") == 5
    assert outcomes.count("provider_request_quota_exhausted") == 15


def test_sqlite_circuit_state_survives_new_control_plane_instance(tmp_path) -> None:
    database = tmp_path / "circuit.sqlite3"
    first_plane = ProviderSecurityControlPlane(
        {"tavily": policy(requests=10, threshold=2, cooldown=30)},
        enabled=True,
        store=SQLiteProviderControlStore(str(database)),
        clock=lambda: 100.0,
    )
    admission = first_plane.authorize(
        provider_id="tavily",
        url="https://api.tavily.com/search",
        context=context("search"),
    )
    first_plane.record_failure(admission, transient=True)

    second_plane = ProviderSecurityControlPlane(
        {"tavily": policy(requests=10, threshold=2, cooldown=30)},
        enabled=True,
        store=SQLiteProviderControlStore(str(database)),
        clock=lambda: 100.0,
    )
    admission = second_plane.authorize(
        provider_id="tavily",
        url="https://api.tavily.com/search",
        context=context("search"),
    )
    second_plane.record_failure(admission, transient=True)

    third_plane = ProviderSecurityControlPlane(
        {"tavily": policy(requests=10, threshold=2, cooldown=30)},
        enabled=True,
        store=SQLiteProviderControlStore(str(database)),
        clock=lambda: 100.0,
    )
    with pytest.raises(ProviderSecurityError, match="provider_circuit_open"):
        third_plane.authorize(
            provider_id="tavily",
            url="https://api.tavily.com/search",
            context=context("search"),
        )


def test_enabled_control_plane_from_env_requires_absolute_durable_store(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("ASIE_PROVIDER_CONTROL_PLANE_ENABLED", "true")
    monkeypatch.delenv("ASIE_PROVIDER_CONTROL_DB_PATH", raising=False)
    with pytest.raises(ProviderSecurityError, match="provider_control_store_required"):
        ProviderSecurityControlPlane.from_env()

    monkeypatch.setenv(
        "ASIE_PROVIDER_CONTROL_DB_PATH",
        str(tmp_path / "configured.sqlite3"),
    )
    plane = ProviderSecurityControlPlane.from_env()
    status = plane.status()
    assert status["control_store_backend"] == "sqlite-wal-shared-host"
    assert status["durable_control_store_required_when_enabled"] is True

