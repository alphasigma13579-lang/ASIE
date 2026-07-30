from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import re
import sqlite3
from threading import RLock
import time
from typing import Any, Callable, Mapping, Protocol
from urllib.parse import urlsplit

from backend.live_provider_catalog import LIVE_PROVIDER_CATALOG, LiveProviderDefinition


Clock = Callable[[], float]
_PROVIDER_STATES = frozenset({"disabled", "preflight", "enabled"})
_ID_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,160}$")


class ProviderSecurityError(PermissionError):
    """Fail-closed provider admission error with a non-secret reason code."""


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    normalized = raw.strip().lower()
    if normalized not in {"0", "1", "false", "true", "no", "yes", "off", "on"}:
        raise ProviderSecurityError(f"invalid_boolean_environment:{name}")
    return normalized in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int, *, minimum: int, maximum: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ProviderSecurityError(f"invalid_integer_environment:{name}") from exc
    if value < minimum or value > maximum:
        raise ProviderSecurityError(f"environment_out_of_range:{name}")
    return value


def _env_float(name: str, default: float, *, minimum: float, maximum: float) -> float:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = float(raw)
    except ValueError as exc:
        raise ProviderSecurityError(f"invalid_float_environment:{name}") from exc
    if value < minimum or value > maximum:
        raise ProviderSecurityError(f"environment_out_of_range:{name}")
    return value


def _provider_env_token(provider_id: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "_", provider_id.upper()).strip("_")


def _host_matches(host: str, patterns: tuple[str, ...]) -> bool:
    normalized = host.lower().rstrip(".")
    for pattern in patterns:
        candidate = pattern.lower().rstrip(".")
        if candidate.startswith("*."):
            suffix = candidate[1:]
            if normalized.endswith(suffix) and normalized != suffix.lstrip("."):
                return True
        elif normalized == candidate:
            return True
    return False


def _bounded_identifier(value: Any, *, field: str) -> str:
    normalized = str(value or "").strip()
    if not _ID_RE.fullmatch(normalized):
        raise ProviderSecurityError(f"invalid_provider_context:{field}")
    return normalized


@dataclass(frozen=True)
class ProviderRequestContext:
    organization_id: str
    project_id: str
    operation: str
    cost_units: int = 1
    preflight: bool = False

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any] | None) -> "ProviderRequestContext":
        if not isinstance(value, Mapping):
            raise ProviderSecurityError("provider_request_context_required")
        organization_id = _bounded_identifier(value.get("organization_id"), field="organization_id")
        project_id = _bounded_identifier(value.get("project_id"), field="project_id")
        operation = _bounded_identifier(value.get("operation"), field="operation")
        raw_cost = value.get("cost_units", 1)
        if isinstance(raw_cost, bool):
            raise ProviderSecurityError("invalid_provider_context:cost_units")
        try:
            cost_units = int(raw_cost)
        except (TypeError, ValueError) as exc:
            raise ProviderSecurityError("invalid_provider_context:cost_units") from exc
        if cost_units < 1 or cost_units > 10_000:
            raise ProviderSecurityError("invalid_provider_context:cost_units")
        return cls(
            organization_id=organization_id,
            project_id=project_id,
            operation=operation,
            cost_units=cost_units,
            preflight=value.get("preflight") is True,
        )

    @property
    def scope_ref(self) -> str:
        digest = hashlib.sha256(
            f"{self.organization_id}\0{self.project_id}".encode("utf-8")
        ).hexdigest()
        return f"tenant-project:{digest[:24]}"


@dataclass(frozen=True)
class ProviderRuntimePolicy:
    provider_id: str
    state: str
    kill_switch: bool
    allowed_hosts: tuple[str, ...]
    allowed_operations: tuple[str, ...]
    preflight_operations: tuple[str, ...]
    contract_version: str
    timeout_seconds: float
    max_response_bytes: int
    requests_per_window: int
    cost_units_per_window: int
    window_seconds: int
    failure_threshold: int
    circuit_cooldown_seconds: int
    max_get_attempts: int
    retry_delay_seconds: float

    @classmethod
    def from_definition(cls, definition: LiveProviderDefinition) -> "ProviderRuntimePolicy":
        token = _provider_env_token(definition.provider_id)
        state = os.getenv(f"ASIE_PROVIDER_{token}_STATE", "disabled").strip().lower()
        if state not in _PROVIDER_STATES:
            raise ProviderSecurityError(f"invalid_provider_state:{definition.provider_id}")
        return cls(
            provider_id=definition.provider_id,
            state=state,
            kill_switch=_env_bool(f"ASIE_PROVIDER_{token}_KILL_SWITCH", False),
            allowed_hosts=definition.base_hosts,
            allowed_operations=definition.allowed_operations,
            preflight_operations=definition.preflight_operations,
            contract_version=definition.contract_version,
            timeout_seconds=_env_float(
                f"ASIE_PROVIDER_{token}_TIMEOUT_SECONDS",
                definition.default_timeout_seconds,
                minimum=1.0,
                maximum=60.0,
            ),
            max_response_bytes=_env_int(
                f"ASIE_PROVIDER_{token}_MAX_RESPONSE_BYTES",
                definition.default_max_response_bytes,
                minimum=1_024,
                maximum=20_971_520,
            ),
            requests_per_window=_env_int(
                f"ASIE_PROVIDER_{token}_REQUESTS_PER_WINDOW",
                definition.default_requests_per_window,
                minimum=1,
                maximum=100_000,
            ),
            cost_units_per_window=_env_int(
                f"ASIE_PROVIDER_{token}_COST_UNITS_PER_WINDOW",
                definition.default_cost_units_per_window,
                minimum=1,
                maximum=1_000_000,
            ),
            window_seconds=_env_int(
                f"ASIE_PROVIDER_{token}_WINDOW_SECONDS",
                60,
                minimum=1,
                maximum=86_400,
            ),
            failure_threshold=_env_int(
                f"ASIE_PROVIDER_{token}_FAILURE_THRESHOLD",
                3,
                minimum=1,
                maximum=100,
            ),
            circuit_cooldown_seconds=_env_int(
                f"ASIE_PROVIDER_{token}_CIRCUIT_COOLDOWN_SECONDS",
                60,
                minimum=1,
                maximum=3_600,
            ),
            max_get_attempts=_env_int(
                f"ASIE_PROVIDER_{token}_MAX_GET_ATTEMPTS",
                definition.default_max_get_attempts,
                minimum=1,
                maximum=3,
            ),
            retry_delay_seconds=_env_float(
                f"ASIE_PROVIDER_{token}_RETRY_DELAY_SECONDS",
                0.25,
                minimum=0.0,
                maximum=5.0,
            ),
        )


@dataclass(frozen=True)
class ProviderAdmission:
    provider_id: str
    operation: str
    scope_ref: str
    contract_version: str
    timeout_seconds: float
    max_response_bytes: int
    max_get_attempts: int
    retry_delay_seconds: float

    def audit_metadata(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "operation": self.operation,
            "tenant_scope_ref": self.scope_ref,
            "contract_version": self.contract_version,
        }


@dataclass
class _UsageWindow:
    started_at: float
    requests: int = 0
    cost_units: int = 0


@dataclass
class _CircuitState:
    consecutive_failures: int = 0
    opened_until: float = 0.0


class ProviderControlStore(Protocol):
    backend_id: str

    def admit(
        self,
        key: tuple[str, str],
        *,
        now: float,
        window_seconds: int,
        request_limit: int,
        cost_limit: int,
        cost_units: int,
    ) -> None: ...

    def record_success(self, key: tuple[str, str]) -> None: ...

    def record_failure(
        self,
        key: tuple[str, str],
        *,
        now: float,
        threshold: int,
        cooldown_seconds: int,
    ) -> None: ...


class InMemoryProviderControlStore:
    """Thread-safe store for disabled/local tests only."""

    backend_id = "memory-single-process"

    def __init__(self) -> None:
        self._lock = RLock()
        self._usage: dict[tuple[str, str], _UsageWindow] = {}
        self._circuits: dict[tuple[str, str], _CircuitState] = {}

    def admit(
        self,
        key: tuple[str, str],
        *,
        now: float,
        window_seconds: int,
        request_limit: int,
        cost_limit: int,
        cost_units: int,
    ) -> None:
        with self._lock:
            state = self._circuits.get(key)
            if state and state.opened_until > now:
                raise ProviderSecurityError("provider_circuit_open")
            if state and state.opened_until and state.opened_until <= now:
                self._circuits[key] = _CircuitState()

            window = self._usage.get(key)
            if window is None or now - window.started_at >= window_seconds:
                window = _UsageWindow(started_at=now)
                self._usage[key] = window
            if window.requests + 1 > request_limit:
                raise ProviderSecurityError("provider_request_quota_exhausted")
            if window.cost_units + cost_units > cost_limit:
                raise ProviderSecurityError("provider_cost_budget_exhausted")
            window.requests += 1
            window.cost_units += cost_units

    def record_success(self, key: tuple[str, str]) -> None:
        with self._lock:
            self._circuits[key] = _CircuitState()

    def record_failure(
        self,
        key: tuple[str, str],
        *,
        now: float,
        threshold: int,
        cooldown_seconds: int,
    ) -> None:
        with self._lock:
            state = self._circuits.setdefault(key, _CircuitState())
            state.consecutive_failures += 1
            if state.consecutive_failures >= threshold:
                state.opened_until = now + cooldown_seconds


class SQLiteProviderControlStore:
    """Cross-thread/process quota and circuit state for a single shared host."""

    backend_id = "sqlite-wal-shared-host"

    def __init__(self, path: str) -> None:
        candidate = Path(str(path or "").strip())
        if not candidate.is_absolute():
            raise ProviderSecurityError("provider_control_store_path_must_be_absolute")
        if not candidate.parent.exists() or not candidate.parent.is_dir():
            raise ProviderSecurityError("provider_control_store_parent_missing")
        self.path = candidate
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            str(self.path),
            timeout=5.0,
            isolation_level=None,
        )
        connection.execute("PRAGMA busy_timeout=5000")
        return connection

    def _initialize(self) -> None:
        try:
            with self._connect() as connection:
                connection.execute("PRAGMA journal_mode=WAL")
                connection.execute("PRAGMA synchronous=FULL")
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS provider_control_usage (
                        provider_id TEXT NOT NULL,
                        scope_ref TEXT NOT NULL,
                        window_started REAL NOT NULL,
                        requests INTEGER NOT NULL,
                        cost_units INTEGER NOT NULL,
                        PRIMARY KEY (provider_id, scope_ref)
                    )
                    """
                )
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS provider_control_circuit (
                        provider_id TEXT NOT NULL,
                        scope_ref TEXT NOT NULL,
                        consecutive_failures INTEGER NOT NULL,
                        opened_until REAL NOT NULL,
                        PRIMARY KEY (provider_id, scope_ref)
                    )
                    """
                )
        except sqlite3.Error as exc:
            raise ProviderSecurityError("provider_control_store_unavailable") from exc

    def admit(
        self,
        key: tuple[str, str],
        *,
        now: float,
        window_seconds: int,
        request_limit: int,
        cost_limit: int,
        cost_units: int,
    ) -> None:
        provider_id, scope_ref = key
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            circuit = connection.execute(
                """
                SELECT consecutive_failures, opened_until
                FROM provider_control_circuit
                WHERE provider_id = ? AND scope_ref = ?
                """,
                (provider_id, scope_ref),
            ).fetchone()
            if circuit and float(circuit[1]) > now:
                connection.rollback()
                raise ProviderSecurityError("provider_circuit_open")
            if circuit and float(circuit[1]) and float(circuit[1]) <= now:
                connection.execute(
                    """
                    UPDATE provider_control_circuit
                    SET consecutive_failures = 0, opened_until = 0
                    WHERE provider_id = ? AND scope_ref = ?
                    """,
                    (provider_id, scope_ref),
                )

            usage = connection.execute(
                """
                SELECT window_started, requests, cost_units
                FROM provider_control_usage
                WHERE provider_id = ? AND scope_ref = ?
                """,
                (provider_id, scope_ref),
            ).fetchone()
            if usage is None or now - float(usage[0]) >= window_seconds:
                window_started, requests, consumed_cost = now, 0, 0
            else:
                window_started, requests, consumed_cost = float(usage[0]), int(usage[1]), int(usage[2])
            if requests + 1 > request_limit:
                connection.rollback()
                raise ProviderSecurityError("provider_request_quota_exhausted")
            if consumed_cost + cost_units > cost_limit:
                connection.rollback()
                raise ProviderSecurityError("provider_cost_budget_exhausted")
            connection.execute(
                """
                INSERT INTO provider_control_usage (
                    provider_id, scope_ref, window_started, requests, cost_units
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(provider_id, scope_ref) DO UPDATE SET
                    window_started = excluded.window_started,
                    requests = excluded.requests,
                    cost_units = excluded.cost_units
                """,
                (
                    provider_id,
                    scope_ref,
                    window_started,
                    requests + 1,
                    consumed_cost + cost_units,
                ),
            )
            connection.commit()
        except ProviderSecurityError:
            raise
        except sqlite3.Error as exc:
            connection.rollback()
            raise ProviderSecurityError("provider_control_store_unavailable") from exc
        finally:
            connection.close()

    def record_success(self, key: tuple[str, str]) -> None:
        provider_id, scope_ref = key
        try:
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT INTO provider_control_circuit (
                        provider_id, scope_ref, consecutive_failures, opened_until
                    ) VALUES (?, ?, 0, 0)
                    ON CONFLICT(provider_id, scope_ref) DO UPDATE SET
                        consecutive_failures = 0,
                        opened_until = 0
                    """,
                    (provider_id, scope_ref),
                )
        except sqlite3.Error as exc:
            raise ProviderSecurityError("provider_control_store_unavailable") from exc

    def record_failure(
        self,
        key: tuple[str, str],
        *,
        now: float,
        threshold: int,
        cooldown_seconds: int,
    ) -> None:
        provider_id, scope_ref = key
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT consecutive_failures
                FROM provider_control_circuit
                WHERE provider_id = ? AND scope_ref = ?
                """,
                (provider_id, scope_ref),
            ).fetchone()
            failures = (int(row[0]) if row else 0) + 1
            opened_until = now + cooldown_seconds if failures >= threshold else 0.0
            connection.execute(
                """
                INSERT INTO provider_control_circuit (
                    provider_id, scope_ref, consecutive_failures, opened_until
                ) VALUES (?, ?, ?, ?)
                ON CONFLICT(provider_id, scope_ref) DO UPDATE SET
                    consecutive_failures = excluded.consecutive_failures,
                    opened_until = excluded.opened_until
                """,
                (provider_id, scope_ref, failures, opened_until),
            )
            connection.commit()
        except sqlite3.Error as exc:
            connection.rollback()
            raise ProviderSecurityError("provider_control_store_unavailable") from exc
        finally:
            connection.close()


class ProviderSecurityControlPlane:
    """Fail-closed provider activation, scope, budget, and circuit admission."""

    def __init__(
        self,
        policies: Mapping[str, ProviderRuntimePolicy],
        *,
        enabled: bool = False,
        global_kill_switch: bool = False,
        store: ProviderControlStore | None = None,
        clock: Clock = time.monotonic,
    ) -> None:
        self.policies = dict(policies)
        self.enabled = enabled
        self.global_kill_switch = global_kill_switch
        self.store = store or InMemoryProviderControlStore()
        self.clock = clock

    @classmethod
    def from_env(cls) -> "ProviderSecurityControlPlane":
        policies = {
            definition.provider_id: ProviderRuntimePolicy.from_definition(definition)
            for definition in LIVE_PROVIDER_CATALOG
        }
        enabled = _env_bool("ASIE_PROVIDER_CONTROL_PLANE_ENABLED", False)
        if enabled:
            store_path = os.getenv("ASIE_PROVIDER_CONTROL_DB_PATH", "").strip()
            if not store_path:
                raise ProviderSecurityError("provider_control_store_required")
            store: ProviderControlStore = SQLiteProviderControlStore(store_path)
        else:
            store = InMemoryProviderControlStore()
        return cls(
            policies,
            enabled=enabled,
            global_kill_switch=_env_bool("ASIE_PROVIDER_GLOBAL_KILL_SWITCH", False),
            store=store,
        )

    def authorize(
        self,
        *,
        provider_id: str,
        url: str,
        context: Mapping[str, Any] | None,
    ) -> ProviderAdmission:
        if not self.enabled:
            raise ProviderSecurityError("provider_control_plane_disabled")
        if self.global_kill_switch:
            raise ProviderSecurityError("provider_global_kill_switch_active")
        policy = self.policies.get(str(provider_id or "").strip())
        if policy is None:
            raise ProviderSecurityError("unknown_provider_denied")
        if policy.kill_switch:
            raise ProviderSecurityError("provider_kill_switch_active")
        if policy.state == "disabled":
            raise ProviderSecurityError("provider_disabled")
        request_context = ProviderRequestContext.from_mapping(context)
        if request_context.operation not in policy.allowed_operations:
            raise ProviderSecurityError("provider_operation_not_allowed")
        if request_context.preflight:
            if request_context.operation not in policy.preflight_operations:
                raise ProviderSecurityError("provider_preflight_operation_not_allowed")
        elif policy.state != "enabled":
            raise ProviderSecurityError("provider_not_enabled_for_live_operation")

        try:
            parsed = urlsplit(str(url or "").strip())
            port = parsed.port
        except ValueError as exc:
            raise ProviderSecurityError("provider_destination_invalid") from exc
        host = (parsed.hostname or "").lower().rstrip(".")
        if (
            parsed.scheme.lower() != "https"
            or not host
            or parsed.username
            or parsed.password
            or port not in {None, 443}
            or parsed.fragment
        ):
            raise ProviderSecurityError("provider_destination_invalid")
        if not _host_matches(host, policy.allowed_hosts):
            raise ProviderSecurityError("provider_host_mismatch")

        key = (policy.provider_id, request_context.scope_ref)
        now = self.clock()
        self.store.admit(
            key,
            now=now,
            window_seconds=policy.window_seconds,
            request_limit=policy.requests_per_window,
            cost_limit=policy.cost_units_per_window,
            cost_units=request_context.cost_units,
        )
        return ProviderAdmission(
            provider_id=policy.provider_id,
            operation=request_context.operation,
            scope_ref=request_context.scope_ref,
            contract_version=policy.contract_version,
            timeout_seconds=policy.timeout_seconds,
            max_response_bytes=policy.max_response_bytes,
            max_get_attempts=policy.max_get_attempts,
            retry_delay_seconds=policy.retry_delay_seconds,
        )

    def record_success(self, admission: ProviderAdmission) -> None:
        self.store.record_success((admission.provider_id, admission.scope_ref))

    def record_failure(self, admission: ProviderAdmission, *, transient: bool) -> None:
        if not transient:
            return
        policy = self.policies[admission.provider_id]
        self.store.record_failure(
            (admission.provider_id, admission.scope_ref),
            now=self.clock(),
            threshold=policy.failure_threshold,
            cooldown_seconds=policy.circuit_cooldown_seconds,
        )

    def status(self) -> dict[str, Any]:
        return {
            "control_plane_id": "asie-provider-security-control-plane-v1",
            "enabled": self.enabled,
            "global_kill_switch": self.global_kill_switch,
            "providers": [
                {
                    "provider_id": policy.provider_id,
                    "state": policy.state,
                    "kill_switch": policy.kill_switch,
                    "contract_version": policy.contract_version,
                    "allowed_hosts": list(policy.allowed_hosts),
                    "allowed_operations": list(policy.allowed_operations),
                    "preflight_operations": list(policy.preflight_operations),
                    "timeout_seconds": policy.timeout_seconds,
                    "max_response_bytes": policy.max_response_bytes,
                    "requests_per_window": policy.requests_per_window,
                    "cost_units_per_window": policy.cost_units_per_window,
                    "window_seconds": policy.window_seconds,
                    "failure_threshold": policy.failure_threshold,
                    "circuit_cooldown_seconds": policy.circuit_cooldown_seconds,
                    "max_get_attempts": policy.max_get_attempts,
                }
                for policy in sorted(self.policies.values(), key=lambda item: item.provider_id)
            ],
            "default_deny": True,
            "tenant_scoped_budgets": True,
            "control_store_backend": self.store.backend_id,
            "durable_control_store_required_when_enabled": True,
            "secret_values_exposed": False,
            "network_authorized": False,
        }
