from __future__ import annotations

from typing import Any


def build_execution_plan(
    finance: dict[str, Any],
    decision_council: dict[str, Any],
    readiness_gates: dict[str, Any],
    risk_advisory_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    gate_status = readiness_gates["status"]
    risk_advisory = normalize_risk_advisory_summary(risk_advisory_summary)
    blocked_risk_ids = risk_advisory.get("blocked_risk_ids", [])
    execution_constraints = risk_advisory.get("execution_constraints", [])
    milestones = [
        milestone("setup", [], "Project Manager", 10, ["project_scope_signed", "baseline_assumptions_reviewed"]),
        milestone("procurement", ["setup"], "Project Manager", 20, ["capex_items_confirmed", "supplier_shortlist_ready"]),
        milestone("staffing", ["setup"], "Project Manager", 15, ["staffing_plan_ready", "monthly_payroll_confirmed"]),
        milestone("launch", ["procurement", "staffing"], "Business Advisor", 12, ["operating_capacity_ready", "launch_controls_reviewed"]),
        milestone("stabilization", ["launch"], "Analyst Coach", 30, ["first_month_kpis_reviewed", "risk_register_updated"]),
    ]
    blocked_gates = [gate["gate_id"] for gate in readiness_gates["gates"] if gate["status"] == "blocked"]
    status = execution_status(
        gate_status=gate_status,
        blocked_gates=blocked_gates,
        blocked_risk_ids=blocked_risk_ids,
        execution_constraints=execution_constraints,
    )
    return {
        "execution_plan_id": "execution-plan-v1-local",
        "status": status,
        "decision_ref": decision_council["verdict"]["sovereign_verdict"],
        "estimated_total_duration_days": sum(item["estimated_duration_days"] for item in milestones),
        "blocked_by_gates": blocked_gates,
        "blocked_by_risks": blocked_risk_ids,
        "execution_constraints": execution_constraints,
        "finance_refs": {
            "finance_status": finance.get("status"),
            "baseline_npv": (finance.get("baseline") or {}).get("npv"),
            "funding_need_after_equity": (finance.get("baseline") or {}).get("funding_need_after_equity"),
        },
        "risk_advisory_summary": risk_advisory,
        "risk_advisory_refs": {
            "risk_register_ref": risk_advisory.get("risk_register_ref", ""),
            "top_risk_ids": risk_advisory.get("top_risk_ids", []),
            "blocked_risk_ids": risk_advisory.get("blocked_risk_ids", []),
        },
        "milestones": milestones,
    }


def normalize_risk_advisory_summary(summary: dict[str, Any] | None) -> dict[str, Any]:
    if not summary:
        return {
            "risk_advisory_summary_id": "",
            "contract_id": "risk.advisory.summary.v1",
            "project_id": "",
            "run_id": "",
            "snapshot_id": "",
            "status": "not_provided",
            "risk_register_ref": "",
            "top_risk_ids": [],
            "blocked_risk_ids": [],
            "execution_constraints": [],
            "source": "not_provided",
            "contains_full_risk_register": False,
        }
    return {
        "risk_advisory_summary_id": summary.get("risk_advisory_summary_id", ""),
        "contract_id": summary.get("contract_id", "risk.advisory.summary.v1"),
        "project_id": summary.get("project_id", ""),
        "run_id": summary.get("run_id", ""),
        "snapshot_id": summary.get("snapshot_id", ""),
        "status": summary.get("status", "unknown"),
        "risk_register_ref": summary.get("risk_register_ref", ""),
        "top_risk_ids": summary.get("top_risk_ids", []),
        "blocked_risk_ids": summary.get("blocked_risk_ids", []),
        "execution_constraints": summary.get("execution_constraints", []),
        "source": summary.get("source", "risk_register_summary_only"),
        "contains_full_risk_register": bool(summary.get("contains_full_risk_register", False)),
    }


def execution_status(
    *,
    gate_status: str,
    blocked_gates: list[str],
    blocked_risk_ids: list[str],
    execution_constraints: list[dict[str, Any]],
) -> str:
    if blocked_gates or blocked_risk_ids:
        return "blocked"
    if gate_status == "warning" or execution_constraints:
        return "ready_with_warnings"
    return "ready"


def milestone(
    phase_id: str,
    dependencies: list[str],
    owner_role: str,
    estimated_duration_days: int,
    exit_criteria: list[str],
) -> dict[str, Any]:
    return {
        "phase_id": phase_id,
        "dependencies": dependencies,
        "owner_role": owner_role,
        "estimated_duration_days": estimated_duration_days,
        "exit_criteria": exit_criteria,
    }
