from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any
from unittest.mock import patch

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from backend.finance_engine import finance_result_set
from backend.snapshot_assembly import (
    REQUIRED_MODULE_OUTPUTS,
    SNAPSHOT_VERSION,
    assemble_snapshot,
    canonical_hash,
    seal_module_output,
    seal_projection_support,
)

SCHEMA = "asie.test_beta_06.cross_platform_determinism.v1"
FIXED_TIME = "2026-07-29T00:00:00+00:00"
PROJECT_ID = "project_test_beta_06"
RUN_ID = "run_test_beta_06"
SNAPSHOT_ID = "snapshot_test_beta_06"


def _finance_inputs() -> dict[str, Any]:
    return {
        "startup_cost": "120000.00",
        "monthly_fixed_cost": "42000.00",
        "unit_price": "18.00",
        "variable_cost": "7.00",
        "monthly_units": "4200",
        "annual_discount_rate": "0.10",
        "working_capital_months": "2",
        "debt_amount": "35000.00",
        "annual_interest_rate": "0.08",
        "loan_years": "5",
        "loan_grace_months": "3",
        "equity_contribution": "180000.00",
        "depreciation_years": "5",
        "use_operating_capacity": False,
        "payroll_monthly": "26000.00",
        "rent_monthly": "8000.00",
        "utilities_monthly": "2500.00",
        "marketing_monthly": "3500.00",
        "maintenance_monthly": "2000.00",
        "capex_equipment": "70000.00",
        "capex_fitout": "42000.00",
        "capex_licenses_local": "8000.00",
    }


def _module_outputs(finance: dict[str, Any], blockers: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    common = {
        "project_id": PROJECT_ID,
        "run_id": RUN_ID,
        "snapshot_id": SNAPSHOT_ID,
        "external_fetch_enabled": False,
        "ai_enabled": False,
    }
    return {
        "finance_result": {
            **common,
            "module_id": "module.finance",
            "contract_id": "finance.result.v1",
            "finance": deepcopy(finance),
            "blockers": deepcopy(blockers),
        },
        "evidence_ledger": {
            **common,
            "module_id": "module.evidence_ledger",
            "contract_id": "evidence.ledger.v1",
            "evidence_ledger": [],
        },
        "sector_intelligence": {
            **common,
            "module_id": "module.sector_intelligence",
            "contract_id": "sector.intelligence.v1",
            "sector_intelligence": {
                "status": "ready",
                "sector": "Food Service",
                "label_ar": "خدمات الأغذية",
                "criteria": ["market", "operations", "regulation"],
            },
        },
        "decision_result": {
            **common,
            "module_id": "module.decision_council",
            "contract_id": "decision.council.v1",
            "decision_council": {
                "verdict": "CONDITIONAL_APPROVE",
                "personas": [
                    {"persona": "Project Manager", "vote": "APPROVE", "score": 0.82},
                    {"persona": "Resistance Test", "vote": "CONDITIONAL_APPROVE", "score": 0.71},
                ],
            },
        },
        "risk_result": {
            **common,
            "module_id": "module.risk_engine",
            "contract_id": "risk.register.v1",
            "risk_register": {
                "status": "ready",
                "risks": [
                    {"risk_id": "risk_01", "severity": "medium", "label_ar": "ضغط التكاليف"},
                ],
            },
            "risk_advisory_summary": {
                "status": "ready",
                "top_risk_ids": ["risk_01"],
            },
        },
        "execution_result": {
            **common,
            "module_id": "module.execution_engine",
            "contract_id": "execution.plan.v1",
            "execution_plan": {
                "status": "ready",
                "phases": [
                    {"phase": 1, "name_ar": "التحقق", "duration_days": 14},
                    {"phase": 2, "name_ar": "التأسيس", "duration_days": 45},
                ],
            },
        },
    }


def _sealed_outputs(outputs: dict[str, dict[str, Any]], *, reverse: bool = False) -> list[dict[str, Any]]:
    output_keys = list(REQUIRED_MODULE_OUTPUTS)
    if reverse:
        output_keys.reverse()
    sealed: list[dict[str, Any]] = []
    for index, output_key in enumerate(output_keys, start=1):
        producer_module_id, producer_contract_id = REQUIRED_MODULE_OUTPUTS[output_key]
        sealed.append(
            seal_module_output(
                output_key=output_key,
                producer_module_id=producer_module_id,
                producer_contract_id=producer_contract_id,
                producer_contract_version=SNAPSHOT_VERSION,
                project_id=PROJECT_ID,
                run_id=RUN_ID,
                snapshot_id=SNAPSHOT_ID,
                message_id=f"message_test_beta_06_{index}",
                correlation_id=f"correlation_test_beta_06_{output_key}",
                audit_ref=f"audit:{SNAPSHOT_ID}:{output_key}",
                produced_at=FIXED_TIME,
                output=outputs[output_key],
            )
        )
    return sealed


def _snapshot(outputs: dict[str, dict[str, Any]], *, reverse: bool = False) -> dict[str, Any]:
    projection_support = seal_projection_support(
        project_id=PROJECT_ID,
        run_id=RUN_ID,
        snapshot_id=SNAPSHOT_ID,
        correlation_id="correlation_test_beta_06_projection_support",
        audit_ref=f"audit:{SNAPSHOT_ID}:projection-support",
        produced_at=FIXED_TIME,
        projection_support={
            "contract_id": "test_beta_06.projection_support.v1",
            "locale": "ar-SA",
            "labels": ["جاهزية التنفيذ", "القبول التجاري", "المتانة الفنية"],
            "line_ending_probe": "alpha\nbeta\ngamma",
        },
    )
    payload = {
        "project_id": PROJECT_ID,
        "run_id": RUN_ID,
        "snapshot_id": SNAPSHOT_ID,
        "input_contract_id": "SnapshotAssemblyInputEnvelope.v1",
        "sealed_outputs": _sealed_outputs(outputs, reverse=reverse),
        "sealed_supporting_outputs": [projection_support],
        "project_context": {
            "name": "مشروع اختبار الحتمية",
            "sector": "Food Service",
            "jurisdiction": "SA",
        },
        "readiness_state": {
            "workflow": "ready",
            "gates": "passed",
            "run": "completed",
        },
        "blockers": [],
    }
    with patch("backend.snapshot_assembly.now_iso", return_value=FIXED_TIME):
        return assemble_snapshot(payload)


def build_vector() -> dict[str, Any]:
    finance, blockers = finance_result_set(_finance_inputs())
    if blockers or finance.get("status") != "ready":
        raise RuntimeError(f"TEST-BETA-06 finance vector is not ready: {blockers}")

    second_finance, second_blockers = finance_result_set(dict(reversed(list(_finance_inputs().items()))))
    if finance != second_finance or blockers != second_blockers:
        raise RuntimeError("Finance output changed when input dictionary order changed")

    outputs = _module_outputs(finance, blockers)
    snapshot_forward = _snapshot(outputs, reverse=False)
    snapshot_reverse = _snapshot(outputs, reverse=True)
    if snapshot_forward != snapshot_reverse:
        raise RuntimeError("Snapshot output changed when sealed module order changed")

    unicode_probe_a = {
        "z": "آخر",
        "a": "أول",
        "nested": {"b": "بيتا", "a": "ألفا"},
        "decimal": "120000.00",
    }
    unicode_probe_b = {
        "decimal": "120000.00",
        "nested": {"a": "ألفا", "b": "بيتا"},
        "a": "أول",
        "z": "آخر",
    }
    probe_hash_a = canonical_hash(unicode_probe_a)
    probe_hash_b = canonical_hash(unicode_probe_b)
    if probe_hash_a != probe_hash_b:
        raise RuntimeError("Canonical hash changed when JSON key order changed")

    determinism_payload = {
        "schema": SCHEMA,
        "fixed_time": FIXED_TIME,
        "finance": finance,
        "finance_hash": canonical_hash(finance),
        "sealed_output_hashes": {
            envelope["output_key"]: envelope["output_hash"]
            for envelope in _sealed_outputs(outputs)
        },
        "snapshot": snapshot_forward,
        "snapshot_content_hash": snapshot_forward["content_hash"],
        "snapshot_integrity_hash": snapshot_forward["integrity_hash"],
        "canonical_unicode_probe_hash": probe_hash_a,
        "invariants": {
            "finance_input_order_independent": True,
            "sealed_output_order_independent": True,
            "canonical_key_order_independent": True,
            "timestamps_fixed_for_test_only": True,
            "absolute_paths_excluded": True,
            "platform_metadata_excluded": True,
        },
    }
    return {
        "schema": SCHEMA,
        "vector_hash": canonical_hash(determinism_payload),
        "determinism_payload": determinism_payload,
    }


def canonical_json_bytes(payload: dict[str, Any]) -> bytes:
    text = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        indent=2,
        separators=(",", ": "),
        allow_nan=False,
    )
    return (text + "\n").encode("utf-8")


def emit(output_path: Path) -> None:
    first = canonical_json_bytes(build_vector())
    second = canonical_json_bytes(build_vector())
    if first != second:
        raise RuntimeError("Repeated vector generation was not byte-identical")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as handle:
        handle.write(first)
    print(json.dumps({"output": output_path.as_posix(), "bytes": len(first), "status": "deterministic"}, sort_keys=True))


def compare(directory: Path) -> None:
    vector_paths = sorted(directory.rglob("vector.json"))
    if len(vector_paths) < 2:
        raise RuntimeError(f"Expected at least two TEST-BETA-06 vectors, found {len(vector_paths)}")
    baseline_path = vector_paths[0]
    baseline_bytes = baseline_path.read_bytes()
    baseline_payload = json.loads(baseline_bytes.decode("utf-8"))
    mismatches: list[str] = []
    for path in vector_paths[1:]:
        payload_bytes = path.read_bytes()
        if payload_bytes != baseline_bytes:
            mismatches.append(path.as_posix())
            continue
        payload = json.loads(payload_bytes.decode("utf-8"))
        if payload.get("vector_hash") != baseline_payload.get("vector_hash"):
            mismatches.append(path.as_posix())
    if mismatches:
        raise RuntimeError(
            "Cross-platform determinism mismatch against "
            + baseline_path.as_posix()
            + ": "
            + ", ".join(mismatches)
        )
    print(
        json.dumps(
            {
                "status": "passed",
                "vectors_compared": len(vector_paths),
                "vector_hash": baseline_payload["vector_hash"],
                "baseline": baseline_path.as_posix(),
            },
            sort_keys=True,
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="TEST-BETA-06 cross-platform determinism evidence")
    subparsers = parser.add_subparsers(dest="command", required=True)
    emit_parser = subparsers.add_parser("emit")
    emit_parser.add_argument("--output", type=Path, required=True)
    compare_parser = subparsers.add_parser("compare")
    compare_parser.add_argument("--directory", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "emit":
        emit(args.output)
    else:
        compare(args.directory)


if __name__ == "__main__":
    main()
