from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Iterable

CRITICAL_CHECKS = (
    "auth_ready",
    "tenant_isolation_ready",
    "dib_runtime_ready",
    "dataset_mapping_ready",
    "product_ai_interview_ready",
    "approved_manifest_gate_ready",
    "controlled_finance_ready",
    "snapshot_lineage_ready",
    "report_exports_ready",
    "deployment_health_ready",
)

DEGRADABLE_CHECKS = (
    "provider_secrets_ready",
    "external_fetch_enabled",
    "vision2030_sync_ready",
    "live_intelligence_ready",
)

SECRET_NAMES = (
    "DEEPSEEK_API_KEY",
    "TAVILY_API_KEY",
    "GOOGLE_MAPS_API_KEY",
    "PINECONE_API_KEY",
)


@dataclass(frozen=True)
class GateCheck:
    check_id: str
    passed: bool
    critical: bool
    evidence: str
    message: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "check_id": self.check_id,
            "passed": self.passed,
            "critical": self.critical,
            "evidence": self.evidence,
            "message": self.message,
        }


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "on", "ready", "passed", "success"}


def _secret_presence(env: dict[str, str]) -> dict[str, bool]:
    return {name: bool(str(env.get(name, "")).strip()) for name in SECRET_NAMES}


def _check(check_id: str, values: dict[str, Any], *, critical: bool) -> GateCheck:
    value = values.get(check_id)
    evidence = str(values.get(f"{check_id}_evidence") or "runtime_assertion")
    message = str(values.get(f"{check_id}_message") or "")
    return GateCheck(check_id=check_id, passed=_truthy(value), critical=critical, evidence=evidence, message=message)


def evaluate_beta_release(
    assertions: dict[str, Any],
    *,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Return a deterministic GO / CONDITIONAL_GO / NO_GO decision.

    The gate consumes already-produced readiness assertions. It does not invoke
    Finance, mutate Snapshot, enable providers, or expose secret values.
    """

    environment = dict(env or os.environ)
    normalized = dict(assertions)
    secret_presence = _secret_presence(environment)
    normalized.setdefault("provider_secrets_ready", all(secret_presence.values()))

    checks = [
        *[_check(check_id, normalized, critical=True) for check_id in CRITICAL_CHECKS],
        *[_check(check_id, normalized, critical=False) for check_id in DEGRADABLE_CHECKS],
    ]

    critical_failures = [item.check_id for item in checks if item.critical and not item.passed]
    degraded = [item.check_id for item in checks if not item.critical and not item.passed]

    if critical_failures:
        decision = "NO_GO"
    elif degraded:
        decision = "CONDITIONAL_GO"
    else:
        decision = "GO"

    return {
        "contract_id": "beta.release.gate.v1",
        "decision": decision,
        "release_allowed": decision in {"GO", "CONDITIONAL_GO"},
        "public_beta_allowed": decision == "GO",
        "technical_limited_beta_allowed": decision in {"GO", "CONDITIONAL_GO"},
        "critical_failures": critical_failures,
        "degraded_capabilities": degraded,
        "checks": [item.as_dict() for item in checks],
        "provider_secret_presence": secret_presence,
        "secrets_exposed": False,
        "finance_mutated": False,
        "snapshot_mutated": False,
        "external_fetch_changed": False,
    }


def assert_releaseable(report: dict[str, Any], *, allow_conditional: bool = False) -> None:
    accepted = {"GO", "CONDITIONAL_GO"} if allow_conditional else {"GO"}
    if report.get("decision") not in accepted:
        failures = ",".join(report.get("critical_failures") or report.get("degraded_capabilities") or [])
        raise RuntimeError(f"beta_release_blocked:{report.get('decision')}:{failures}")


def default_assertions_from_env(env: dict[str, str] | None = None) -> dict[str, Any]:
    environment = dict(env or os.environ)
    return {
        check_id: _truthy(environment.get(f"ASIE_BETA_{check_id.upper()}"))
        for check_id in (*CRITICAL_CHECKS, *DEGRADABLE_CHECKS)
        if check_id != "provider_secrets_ready"
    }


def main(argv: Iterable[str] | None = None) -> int:
    del argv
    report = evaluate_beta_release(default_assertions_from_env())
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    allow_conditional = _truthy(os.environ.get("ASIE_BETA_ALLOW_CONDITIONAL"))
    try:
        assert_releaseable(report, allow_conditional=allow_conditional)
    except RuntimeError:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
