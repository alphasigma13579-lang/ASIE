from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Iterable

CRITICAL_GATES = (
    "auth",
    "tenant_isolation",
    "dataset_to_dib",
    "product_ai_interview",
    "approved_input_manifest",
    "controlled_finance",
    "snapshot_lineage",
    "reports",
    "deployment_health",
)

CONDITIONAL_GATES = (
    "provider_readiness",
    "live_intelligence",
    "vision2030_sync",
)

VALID_STATUSES = {"passed", "failed", "disabled", "not_checked"}


@dataclass(frozen=True)
class GateResult:
    gate_id: str
    status: str
    critical: bool
    evidence: tuple[str, ...] = ()
    note: str = ""

    def validate(self) -> None:
        if self.gate_id not in {*CRITICAL_GATES, *CONDITIONAL_GATES}:
            raise ValueError(f"unknown_beta_gate:{self.gate_id}")
        if self.status not in VALID_STATUSES:
            raise ValueError(f"invalid_beta_gate_status:{self.status}")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _env_present(name: str) -> bool:
    return bool(str(os.getenv(name, "")).strip())


def provider_presence_snapshot() -> dict[str, bool]:
    return {
        "DEEPSEEK_API_KEY": _env_present("DEEPSEEK_API_KEY"),
        "TAVILY_API_KEY": _env_present("TAVILY_API_KEY"),
        "GOOGLE_MAPS_API_KEY": _env_present("GOOGLE_MAPS_API_KEY"),
        "PINECONE_API_KEY": _env_present("PINECONE_API_KEY"),
    }


def default_gate_results() -> list[GateResult]:
    """Return a fail-closed baseline for manual or CI evaluation.

    Product/runtime gates are expected to be promoted to ``passed`` by the
    verification harness. Provider gates are derived from presence-only
    environment checks and never expose secret values.
    """
    provider_presence = provider_presence_snapshot()
    providers_ready = all(provider_presence.values())
    external_fetch = os.getenv("ASIE_ALLOW_EXTERNAL_FETCH", "false").strip().lower() == "true"

    results = [
        GateResult(gate_id=gate_id, status="not_checked", critical=True)
        for gate_id in CRITICAL_GATES
    ]
    results.extend(
        [
            GateResult(
                gate_id="provider_readiness",
                status="passed" if providers_ready else "disabled",
                critical=False,
                note="presence-only verification",
            ),
            GateResult(
                gate_id="live_intelligence",
                status="passed" if providers_ready and external_fetch else "disabled",
                critical=False,
                note="external fetch remains explicit opt-in",
            ),
            GateResult(
                gate_id="vision2030_sync",
                status="passed" if provider_presence["TAVILY_API_KEY"] and provider_presence["PINECONE_API_KEY"] else "disabled",
                critical=False,
                note="monthly workflow requires Tavily and Pinecone secrets",
            ),
        ]
    )
    return results


def evaluate_beta_release(results: Iterable[GateResult]) -> dict[str, Any]:
    rows = list(results)
    seen = set()
    for row in rows:
        row.validate()
        if row.gate_id in seen:
            raise ValueError(f"duplicate_beta_gate:{row.gate_id}")
        seen.add(row.gate_id)

    missing = [gate for gate in (*CRITICAL_GATES, *CONDITIONAL_GATES) if gate not in seen]
    failed_critical = [row.gate_id for row in rows if row.critical and row.status != "passed"]
    failed_conditional = [row.gate_id for row in rows if not row.critical and row.status != "passed"]

    if missing or failed_critical:
        verdict = "NO_GO"
    elif failed_conditional:
        verdict = "CONDITIONAL_GO"
    else:
        verdict = "GO"

    return {
        "contract_id": "beta.release.gate.v1",
        "evaluated_at": _utc_now(),
        "verdict": verdict,
        "critical_failures": failed_critical,
        "conditional_gaps": failed_conditional,
        "missing_gates": missing,
        "gates": [asdict(row) for row in rows],
        "secrets_exposed": False,
        "finance_mutated": False,
        "snapshot_mutated": False,
        "aas_runtime_mutated": False,
    }


def write_report(path: str, results: Iterable[GateResult]) -> dict[str, Any]:
    report = evaluate_beta_release(results)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    return report


if __name__ == "__main__":
    output_path = os.getenv("ASIE_BETA_GATE_REPORT", "beta-release-gate-report.json")
    report = write_report(output_path, default_gate_results())
    print(json.dumps({
        "contract_id": report["contract_id"],
        "verdict": report["verdict"],
        "critical_failures": report["critical_failures"],
        "conditional_gaps": report["conditional_gaps"],
        "secrets_exposed": False,
    }, ensure_ascii=False))
