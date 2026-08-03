from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
from http.client import HTTPSConnection
import ipaddress
import json
import os
import socket
import time
from typing import Any, Callable, Iterable, Mapping, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit
from urllib.request import (
    HTTPRedirectHandler,
    HTTPSHandler,
    ProxyHandler,
    Request,
    build_opener,
)
from urllib.robotparser import RobotFileParser


class ExternalAcquisitionError(RuntimeError):
    """Raised when a governed external acquisition request is rejected or fails."""


class ExternalResponse(Protocol):
    status: int
    headers: Mapping[str, str]

    def read(self, amount: int = -1) -> bytes: ...

    def geturl(self) -> str: ...

    def __enter__(self) -> "ExternalResponse": ...

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None: ...


Resolver = Callable[[str, int], Iterable[tuple[Any, ...]]]
Sleep = Callable[[float], None]
Clock = Callable[[], float]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int, *, minimum: int, maximum: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ExternalAcquisitionError(f"invalid_integer_environment:{name}") from exc
    if value < minimum or value > maximum:
        raise ExternalAcquisitionError(f"environment_out_of_range:{name}")
    return value


def _env_float(name: str, default: float, *, minimum: float, maximum: float) -> float:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = float(raw)
    except ValueError as exc:
        raise ExternalAcquisitionError(f"invalid_float_environment:{name}") from exc
    if value < minimum or value > maximum:
        raise ExternalAcquisitionError(f"environment_out_of_range:{name}")
    return value


@dataclass(frozen=True)
class ExternalAcquisitionPolicy:
    """Environment-backed network policy for live API and governed crawl requests.

    The policy is deliberately disabled by default. Enabling the network is not enough:
    every destination host must also appear in the allowlist. API keys remain outside
    this object and outside audit events.
    """

    enabled: bool = False
    allowed_hosts: tuple[str, ...] = ()
    timeout_seconds: float = 8.0
    max_response_bytes: int = 2_097_152
    min_interval_seconds: float = 1.0
    user_agent: str = "ASIE-Governed-Acquisition/1.0"
    robots_failure_mode: str = "deny"

    @classmethod
    def from_env(cls) -> "ExternalAcquisitionPolicy":
        hosts = tuple(
            sorted(
                {
                    item.strip().lower().rstrip(".")
                    for item in os.getenv("ASIE_EXTERNAL_ALLOWED_HOSTS", "").split(",")
                    if item.strip()
                }
            )
        )
        failure_mode = os.getenv("ASIE_EXTERNAL_ROBOTS_FAILURE_MODE", "deny").strip().lower()
        if failure_mode not in {"deny", "allow"}:
            raise ExternalAcquisitionError("invalid_robots_failure_mode")
        user_agent = os.getenv("ASIE_EXTERNAL_USER_AGENT", "ASIE-Governed-Acquisition/1.0").strip()
        if not user_agent or len(user_agent) > 160:
            raise ExternalAcquisitionError("invalid_external_user_agent")
        return cls(
            enabled=_env_bool("ASIE_ALLOW_EXTERNAL_FETCH", False),
            allowed_hosts=hosts,
            timeout_seconds=_env_float("ASIE_EXTERNAL_TIMEOUT_SECONDS", 8.0, minimum=1.0, maximum=60.0),
            max_response_bytes=_env_int(
                "ASIE_EXTERNAL_MAX_RESPONSE_BYTES", 2_097_152, minimum=1_024, maximum=20_971_520
            ),
            min_interval_seconds=_env_float(
                "ASIE_EXTERNAL_MIN_INTERVAL_SECONDS", 1.0, minimum=0.0, maximum=60.0
            ),
            user_agent=user_agent,
            robots_failure_mode=failure_mode,
        )

    def snapshot(self) -> dict[str, Any]:
        return {
            "policy_id": "asie-external-acquisition-policy-v1",
            "enabled": self.enabled,
            "allowed_hosts": list(self.allowed_hosts),
            "https_only": True,
            "private_networks_blocked": True,
            "dns_connection_pinning": True,
            "environment_proxy_bypass": True,
            "credentials_in_url_blocked": True,
            "timeout_seconds": self.timeout_seconds,
            "max_response_bytes": self.max_response_bytes,
            "min_interval_seconds": self.min_interval_seconds,
            "robots_failure_mode": self.robots_failure_mode,
            "stores_api_keys": False,
        }


class AcquisitionAuditSink:
    sensitive_fields = frozenset({"authorization", "api_key", "key", "token", "secret", "headers", "payload"})

    def __init__(self) -> None:
        self._events: list[dict[str, Any]] = []

    def record(self, *, event_type: str, outcome: str, metadata: Mapping[str, Any]) -> dict[str, Any]:
        safe_metadata: dict[str, Any] = {}
        for key, value in metadata.items():
            if key.lower() in self.sensitive_fields:
                safe_metadata[key] = "[redacted]"
            elif isinstance(value, (str, int, float, bool)) or value is None:
                safe_metadata[key] = value
            elif isinstance(value, (list, tuple)):
                safe_metadata[key] = [
                    item for item in value if isinstance(item, (str, int, float, bool)) or item is None
                ]
            else:
                safe_metadata[key] = type(value).__name__
        event = {
            "audit_event_id": f"external-acquisition:{len(self._events) + 1}",
            "event_type": event_type,
            "outcome": outcome,
            "metadata": safe_metadata,
            "payload_stored": False,
            "secrets_stored": False,
            "created_at": _utc_now(),
        }
        self._events.append(event)
        return dict(event)

    def snapshot(self) -> dict[str, Any]:
        return {
            "sink_id": "asie-external-acquisition-audit-v1",
            "event_count": len(self._events),
            "events": [dict(event) for event in self._events],
            "payloads_stored": False,
            "secrets_stored": False,
        }


class HostRateLimiter:
    def __init__(self, interval_seconds: float, *, clock: Clock = time.monotonic, sleep: Sleep = time.sleep) -> None:
        self.interval_seconds = interval_seconds
        self.clock = clock
        self.sleep = sleep
        self._last_request_at: dict[str, float] = {}

    def wait(self, host: str) -> None:
        if self.interval_seconds <= 0:
            return
        now = self.clock()
        previous = self._last_request_at.get(host)
        if previous is not None:
            remaining = self.interval_seconds - (now - previous)
            if remaining > 0:
                self.sleep(remaining)
                now = self.clock()
        self._last_request_at[host] = now


@dataclass(frozen=True)
class ExternalConnectorSpec:
    connector_id: str
    host: str
    source_class: str
    purpose: str
    terms_reviewed: bool
    requires_api_key: bool = False

    def snapshot(self) -> dict[str, Any]:
        return {
            "connector_id": self.connector_id,
            "host": self.host,
            "source_class": self.source_class,
            "purpose": self.purpose,
            "terms_reviewed": self.terms_reviewed,
            "requires_api_key": self.requires_api_key,
            "stores_api_key": False,
        }


class ExternalConnectorRegistry:
    """Registers connector metadata only; it never stores credentials."""

    def __init__(self, policy: ExternalAcquisitionPolicy) -> None:
        self.policy = policy
        self._connectors: dict[str, ExternalConnectorSpec] = {}

    def register(self, spec: ExternalConnectorSpec) -> dict[str, Any]:
        if not spec.connector_id or spec.connector_id in self._connectors:
            raise ExternalAcquisitionError("invalid_or_duplicate_connector_id")
        normalized_host = spec.host.strip().lower().rstrip(".")
        if normalized_host != spec.host:
            raise ExternalAcquisitionError("connector_host_must_be_normalized")
        if not spec.terms_reviewed:
            raise ExternalAcquisitionError("connector_terms_review_required")
        if not _host_matches_allowlist(normalized_host, self.policy.allowed_hosts):
            raise ExternalAcquisitionError("connector_host_not_allowlisted")
        self._connectors[spec.connector_id] = spec
        return {
            **spec.snapshot(),
            "status": "ready" if self.policy.enabled else "registered_network_disabled",
        }

    def snapshot(self) -> dict[str, Any]:
        return {
            "registry_id": "asie-external-connector-registry-v1",
            "network_enabled": self.policy.enabled,
            "connector_count": len(self._connectors),
            "connectors": [spec.snapshot() for spec in self._connectors.values()],
            "stores_credentials": False,
        }


def _host_matches_allowlist(host: str, allowed_hosts: Iterable[str]) -> bool:
    normalized = host.lower().rstrip(".")
    for allowed in allowed_hosts:
        candidate = allowed.lower().rstrip(".")
        if candidate.startswith("*."):
            suffix = candidate[1:]
            if normalized.endswith(suffix) and normalized != suffix.lstrip("."):
                return True
        elif normalized == candidate:
            return True
    return False


def _default_resolver(host: str, port: int) -> Iterable[tuple[Any, ...]]:
    return socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)


def _resolve_public_addresses(
    resolver: Resolver,
    host: str,
    port: int,
) -> tuple[str, ...]:
    try:
        literal = ipaddress.ip_address(host)
        addresses = [literal]
    except ValueError:
        try:
            resolved = list(resolver(host, port))
        except OSError as exc:
            raise ExternalAcquisitionError("external_dns_resolution_failed") from exc
        addresses = []
        for row in resolved:
            try:
                sockaddr = row[4]
            except (IndexError, TypeError) as exc:
                raise ExternalAcquisitionError(
                    "external_dns_returned_invalid_address"
                ) from exc
            if not sockaddr:
                continue
            try:
                addresses.append(ipaddress.ip_address(sockaddr[0]))
            except (ValueError, TypeError) as exc:
                raise ExternalAcquisitionError(
                    "external_dns_returned_invalid_address"
                ) from exc
    if not addresses:
        raise ExternalAcquisitionError("external_dns_no_addresses")
    if any(not address.is_global for address in addresses):
        raise ExternalAcquisitionError("external_private_or_reserved_address_blocked")
    return tuple(dict.fromkeys(str(address) for address in addresses))


class _PinnedHTTPSConnection(HTTPSConnection):
    """Connect to a validated numeric address while retaining host-bound TLS."""

    def __init__(self, host: str, *, resolver: Resolver, **kwargs: Any) -> None:
        self._resolver = resolver
        super().__init__(host, **kwargs)

    def connect(self) -> None:
        if self._tunnel_host:
            raise ExternalAcquisitionError("external_proxy_tunnel_forbidden")
        port = self.port or 443
        addresses = _resolve_public_addresses(self._resolver, self.host, port)
        last_error: OSError | None = None
        for address in addresses:
            raw_socket: Any | None = None
            try:
                raw_socket = self._create_connection(
                    (address, port),
                    self.timeout,
                    self.source_address,
                )
                self.sock = self._context.wrap_socket(
                    raw_socket,
                    server_hostname=self.host,
                )
                return
            except OSError as exc:
                last_error = exc
                if raw_socket is not None:
                    raw_socket.close()
        raise OSError("external_pinned_connection_failed") from last_error


class _PinnedHTTPSHandler(HTTPSHandler):
    def __init__(self, resolver: Resolver) -> None:
        super().__init__()
        self._resolver = resolver

    def https_open(self, request: Request):
        def connection_factory(host: str, **kwargs: Any) -> _PinnedHTTPSConnection:
            return _PinnedHTTPSConnection(
                host,
                resolver=self._resolver,
                **kwargs,
            )

        return self.do_open(
            connection_factory,
            request,
            context=self._context,
            check_hostname=self._check_hostname,
        )


class _GovernedRedirectHandler(HTTPRedirectHandler):
    def __init__(self, validator: Callable[[str], None]) -> None:
        super().__init__()
        self._validator = validator

    def redirect_request(self, req: Request, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> Request | None:
        self._validator(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class GovernedExternalAcquisitionGateway:
    """Live-ready acquisition gateway for allowlisted HTTPS APIs and websites.

    This gateway is outside the frozen analytical runtime. Retrieved material must
    still pass source review, transformation lineage, evidence linking, and human
    review before any downstream engine may use it.
    """

    json_content_types = frozenset({"application/json", "text/json"})
    html_content_types = frozenset({"text/html", "application/xhtml+xml"})

    def __init__(
        self,
        policy: ExternalAcquisitionPolicy | None = None,
        *,
        audit_sink: AcquisitionAuditSink | None = None,
        resolver: Resolver = _default_resolver,
        opener: Any | None = None,
        rate_limiter: HostRateLimiter | None = None,
    ) -> None:
        self.policy = policy or ExternalAcquisitionPolicy.from_env()
        self.audit_sink = audit_sink or AcquisitionAuditSink()
        self.resolver = resolver
        self.rate_limiter = rate_limiter or HostRateLimiter(self.policy.min_interval_seconds)
        self.opener = opener or build_opener(
            ProxyHandler({}),
            _PinnedHTTPSHandler(self.resolver),
            _GovernedRedirectHandler(self._validate_url),
        )

    def status(self) -> dict[str, Any]:
        return {
            "gateway_id": "asie-governed-external-acquisition-v1",
            "status": "enabled" if self.policy.enabled else "disabled_by_default",
            "policy": self.policy.snapshot(),
            "audit": self.audit_sink.snapshot(),
            "runtime_integration": "not_connected_to_frozen_aas_runtime",
        }

    def fetch_json(
        self,
        *,
        source_id: str,
        url: str,
        headers: Mapping[str, str] | None = None,
    ) -> dict[str, Any]:
        return self._fetch(
            source_id=source_id,
            url=url,
            accepted_types=self.json_content_types,
            headers=headers,
            mode="api",
            parse_json=True,
        )

    def fetch_html(
        self,
        *,
        source_id: str,
        url: str,
        headers: Mapping[str, str] | None = None,
    ) -> dict[str, Any]:
        self._assert_robots_allowed(url)
        return self._fetch(
            source_id=source_id,
            url=url,
            accepted_types=self.html_content_types,
            headers=headers,
            mode="crawl",
            parse_json=False,
        )

    def _fetch(
        self,
        *,
        source_id: str,
        url: str,
        accepted_types: frozenset[str],
        headers: Mapping[str, str] | None,
        mode: str,
        parse_json: bool,
    ) -> dict[str, Any]:
        if not source_id.strip():
            raise ExternalAcquisitionError("source_id_required")
        parsed = self._validate_url(url)
        self.rate_limiter.wait(parsed.hostname or "")
        request_headers = {"Accept": "application/json" if parse_json else "text/html,application/xhtml+xml"}
        request_headers.update({str(key): str(value) for key, value in (headers or {}).items()})
        request_headers["User-Agent"] = self.policy.user_agent
        request = Request(url, headers=request_headers, method="GET")
        try:
            with self.opener.open(request, timeout=self.policy.timeout_seconds) as response:
                final_url = response.geturl()
                self._validate_url(final_url)
                status = int(getattr(response, "status", 200))
                if status < 200 or status >= 300:
                    raise ExternalAcquisitionError(f"external_http_status:{status}")
                content_type = str(response.headers.get("Content-Type", "")).split(";", 1)[0].strip().lower()
                if content_type not in accepted_types and not (parse_json and content_type.endswith("+json")):
                    raise ExternalAcquisitionError(f"unexpected_content_type:{content_type or 'missing'}")
                content_length = response.headers.get("Content-Length")
                if content_length and int(content_length) > self.policy.max_response_bytes:
                    raise ExternalAcquisitionError("external_response_too_large")
                body = self._read_limited(response)
        except ExternalAcquisitionError as exc:
            self._record_failure(source_id=source_id, url=url, mode=mode, reason=str(exc))
            raise
        except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
            reason = f"external_transport_error:{type(exc).__name__}"
            self._record_failure(source_id=source_id, url=url, mode=mode, reason=reason)
            raise ExternalAcquisitionError(reason) from exc

        digest = hashlib.sha256(body).hexdigest()
        retrieval_id = f"external:{source_id}:{digest[:16]}"
        try:
            payload: Any = json.loads(body.decode("utf-8")) if parse_json else body.decode("utf-8")
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            reason = "invalid_external_payload_encoding" if isinstance(exc, UnicodeDecodeError) else "invalid_external_json"
            self._record_failure(source_id=source_id, url=url, mode=mode, reason=reason)
            raise ExternalAcquisitionError(reason) from exc

        self.audit_sink.record(
            event_type="external_acquisition",
            outcome="success",
            metadata={
                "source_id": source_id,
                "mode": mode,
                "host": parsed.hostname,
                "status_code": status,
                "content_type": content_type,
                "response_bytes": len(body),
                "sha256": digest,
            },
        )
        return {
            "retrieval_id": retrieval_id,
            "source_id": source_id,
            "mode": mode,
            "url": final_url,
            "retrieved_at": _utc_now(),
            "status_code": status,
            "content_type": content_type,
            "response_bytes": len(body),
            "sha256": digest,
            "payload": payload,
            "network_attempted": True,
            "review_status": "review_required",
            "eligible_for_controlled_assumptions": False,
        }

    def _assert_robots_allowed(self, url: str) -> None:
        parsed = self._validate_url(url)
        origin = f"{parsed.scheme}://{parsed.hostname}"
        if parsed.port:
            origin += f":{parsed.port}"
        robots_url = urljoin(origin + "/", "robots.txt")
        self.rate_limiter.wait(parsed.hostname or "")
        request = Request(robots_url, headers={"User-Agent": self.policy.user_agent}, method="GET")
        try:
            with self.opener.open(request, timeout=self.policy.timeout_seconds) as response:
                final_url = response.geturl()
                self._validate_url(final_url)
                body = self._read_limited(response).decode("utf-8", errors="replace")
        except HTTPError as exc:
            if exc.code == 404:
                return
            if self.policy.robots_failure_mode == "allow":
                return
            raise ExternalAcquisitionError(f"robots_fetch_denied:{exc.code}") from exc
        except (URLError, TimeoutError, OSError, ExternalAcquisitionError) as exc:
            if self.policy.robots_failure_mode == "allow":
                return
            raise ExternalAcquisitionError("robots_fetch_failed_closed") from exc
        parser = RobotFileParser()
        parser.set_url(robots_url)
        parser.parse(body.splitlines())
        if not parser.can_fetch(self.policy.user_agent, url):
            raise ExternalAcquisitionError("robots_policy_denied")

    def _read_limited(self, response: ExternalResponse) -> bytes:
        body = response.read(self.policy.max_response_bytes + 1)
        if len(body) > self.policy.max_response_bytes:
            raise ExternalAcquisitionError("external_response_too_large")
        return body

    def _validate_url(self, url: str):
        if not self.policy.enabled:
            raise ExternalAcquisitionError("external_network_disabled_by_policy")
        parsed = urlsplit(url)
        if parsed.scheme.lower() != "https":
            raise ExternalAcquisitionError("external_https_required")
        if parsed.username or parsed.password:
            raise ExternalAcquisitionError("credentials_in_url_forbidden")
        host = (parsed.hostname or "").lower().rstrip(".")
        if not host:
            raise ExternalAcquisitionError("external_hostname_required")
        if parsed.port not in {None, 443}:
            raise ExternalAcquisitionError("external_port_forbidden")
        if not _host_matches_allowlist(host, self.policy.allowed_hosts):
            raise ExternalAcquisitionError("external_host_not_allowlisted")
        self._validate_host_addresses(host, parsed.port or 443)
        return parsed

    def _validate_host_addresses(self, host: str, port: int) -> None:
        _resolve_public_addresses(self.resolver, host, port)

    def _record_failure(self, *, source_id: str, url: str, mode: str, reason: str) -> None:
        parsed = urlsplit(url)
        self.audit_sink.record(
            event_type="external_acquisition",
            outcome="rejected",
            metadata={
                "source_id": source_id,
                "mode": mode,
                "host": parsed.hostname,
                "reason": reason,
            },
        )
