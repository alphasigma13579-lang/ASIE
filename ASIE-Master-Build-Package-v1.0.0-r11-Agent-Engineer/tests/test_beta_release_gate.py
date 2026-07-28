from __future__ import annotations

import json
from pathlib import Path

from backend.beta_release_gate import (
    CONDITIONAL_GATES,
    CRITICAL_GATES,
    GateResult,
    evaluate_beta_release,
    write_report,
)


def _all_passed():
    return [
        GateResult(gate_id=gate, status="passed", critical=True, evidence=(f"test:{gate}",))
        for gate in CRITICAL_GATES
    ] + [
        GateResult(gate_id=gate, status="passed", critical=False, evidence=(f"test:{gate}",))
        for gate in CONDITIONAL_GATES
    ]


def test_all_gates_passed_returns_go():
    report = evaluate_beta_release(_all_passed())
    assert report["verdict"] == "GO"
    assert report["critical_failures"] == []
    assert report["conditional_gaps"] == []


def test_optional_provider_gap_returns_conditional_go():
    rows = _all_passed()
    rows[-1] = GateResult(gate_id="vision2030_sync", status="disabled", critical=False)
    report = evaluate_beta_release(rows)
    assert report["verdict"] == "CONDITIONAL_GO"
    assert report["conditional_gaps"] == ["vision2030_sync"]


def test_critical_manifest_failure_returns_no_go():
    rows = [
        GateResult(
            gate_id=row.gate_id,
            status="failed" if row.gate_id == "approved_input_manifest" else row.status,
            critical=row.critical,
            evidence=row.evidence,
        )
        for row in _all_passed()
    ]
    report = evaluate_beta_release(rows)
    assert report["verdict"] == "NO_GO"
    assert "approved_input_manifest" in report["critical_failures"]


def test_missing_gate_is_fail_closed():
    report = evaluate_beta_release(_all_passed()[:-1])
    assert report["verdict"] == "NO_GO"
    assert "vision2030_sync" in report["missing_gates"]


def test_report_never_claims_runtime_mutation(tmp_path: Path):
    path = tmp_path / "report.json"
    report = write_report(str(path), _all_passed())
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert report["finance_mutated"] is False
    assert saved["snapshot_mutated"] is False
    assert saved["aas_runtime_mutated"] is False
    assert saved["secrets_exposed"] is False


def test_duplicate_gate_rejected():
    rows = _all_passed() + [GateResult(gate_id="auth", status="passed", critical=True)]
    try:
        evaluate_beta_release(rows)
    except ValueError as exc:
        assert "duplicate_beta_gate:auth" in str(exc)
    else:
        raise AssertionError("duplicate gate must be rejected")
