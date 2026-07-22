from __future__ import annotations

from typing import Any


def build_risk_register(
    finance: dict[str, Any],
    evidence_register: dict[str, Any],
    source_policy: dict[str, Any],
    readiness_gates: dict[str, Any],
    *,
    project_id: str = "",
    run_id: str = "",
    snapshot_id: str = "",
) -> dict[str, Any]:
    risks = [
        funding_risk(finance),
        dscr_risk(finance),
        utilization_risk(finance),
        opex_pressure_risk(finance),
        source_governance_risk(source_policy),
        evidence_readiness_risk(evidence_register),
    ]
    identity = risk_identity(project_id=project_id, run_id=run_id, snapshot_id=snapshot_id)
    return {
        "risk_register_id": f"risk-register:{identity}",
        "contract_id": "risk.register.v1",
        "project_id": project_id,
        "run_id": run_id,
        "snapshot_id": snapshot_id,
        "status": "blocked" if any(row["status"] == "open" and row["severity"] == "critical" for row in risks) else "open",
        "readiness_gate_status": readiness_gates["status"],
        "risks": risks,
        "top_risks": sorted(risks, key=lambda row: severity_rank(row["severity"]), reverse=True)[:3],
    }


def build_risk_advisory_summary(
    risk_register: dict[str, Any],
    *,
    project_id: str | None = None,
    run_id: str | None = None,
    snapshot_id: str | None = None,
) -> dict[str, Any]:
    resolved_project_id = project_id if project_id is not None else str(risk_register.get("project_id", ""))
    resolved_run_id = run_id if run_id is not None else str(risk_register.get("run_id", ""))
    resolved_snapshot_id = snapshot_id if snapshot_id is not None else str(risk_register.get("snapshot_id", ""))
    identity = risk_identity(
        project_id=resolved_project_id,
        run_id=resolved_run_id,
        snapshot_id=resolved_snapshot_id,
    )
    top_risks = risk_register.get("top_risks", [])
    open_risks = [
        row
        for row in risk_register.get("risks", [])
        if row.get("status") == "open"
    ]
    execution_constraints = [
        {
            "risk_id": row.get("risk_id", ""),
            "severity": row.get("severity", "unknown"),
            "trigger": row.get("trigger", ""),
            "owner_role": row.get("owner_role", ""),
        }
        for row in top_risks
        if row.get("severity") in {"critical", "high"}
    ]
    return {
        "risk_advisory_summary_id": f"risk-advisory:{identity}",
        "contract_id": "risk.advisory.summary.v1",
        "project_id": resolved_project_id,
        "run_id": resolved_run_id,
        "snapshot_id": resolved_snapshot_id,
        "status": risk_register.get("status", "unknown"),
        "risk_register_ref": risk_register.get("risk_register_id", ""),
        "top_risk_ids": [row.get("risk_id", "") for row in top_risks],
        "blocked_risk_ids": [
            row.get("risk_id", "")
            for row in open_risks
            if row.get("severity") == "critical"
        ],
        "execution_constraints": execution_constraints,
        "source": "risk_register_summary_only",
        "contains_full_risk_register": False,
    }


def risk_identity(*, project_id: str, run_id: str, snapshot_id: str) -> str:
    return ":".join(
        [
            project_id or "unknown-project",
            run_id or "unknown-run",
            snapshot_id or "unknown-snapshot",
        ]
    )


def risk(
    risk_id: str,
    severity: str,
    likelihood: str,
    impact: str,
    trigger: str,
    mitigation: str,
    owner_role: str,
    status: str = "open",
) -> dict[str, Any]:
    return {
        "risk_id": risk_id,
        "severity": severity,
        "likelihood": likelihood,
        "impact": impact,
        "trigger": trigger,
        "mitigation": mitigation,
        "owner_role": owner_role,
        "status": status,
    }


def funding_risk(finance: dict[str, Any]) -> dict[str, Any]:
    baseline = finance.get("baseline") or {}
    funding_need = baseline.get("funding_need_after_equity")
    if funding_need is None:
        return risk("funding_risk", "critical", "high", "execution_blocked", "finance_not_ready", "Complete finance inputs.", "Project Manager")
    if funding_need > 300000:
        return risk("funding_risk", "high", "medium", "cash_gap", "funding_need_after_equity_above_300k", "Increase equity or reduce CAPEX/OPEX before launch.", "Business Advisor")
    return risk("funding_risk", "low", "low", "manageable", "funding_need_within_local_threshold", "Track funding gap before procurement.", "Project Manager", "monitor")


def dscr_risk(finance: dict[str, Any]) -> dict[str, Any]:
    profile = finance.get("debt_service_profile") or {}
    if profile.get("status") == "not_ready":
        return risk("dscr_risk", "critical", "high", "decision_blocked", "debt_terms_not_ready", "Complete interest rate and loan tenor.", "Business Advisor")
    dscr = profile.get("dscr")
    if dscr is not None and dscr < 1.2:
        return risk("dscr_risk", "high", "medium", "debt_pressure", "dscr_below_1_2", "Lower debt, improve EBITDA, or extend tenor.", "Business Advisor")
    return risk("dscr_risk", "low", "low", "manageable", "no_debt_or_dscr_ready", "Monitor debt service after lender terms are final.", "Business Advisor", "monitor")


def utilization_risk(finance: dict[str, Any]) -> dict[str, Any]:
    operating_model = finance.get("operating_model") or {}
    utilization = operating_model.get("utilization_rate")
    if operating_model.get("use_operating_capacity") and utilization is not None and utilization > 0.85:
        return risk("utilization_risk", "medium", "medium", "volume_shortfall", "high_utilization_assumption", "Validate capacity and ramp-up before launch.", "Project Manager")
    return risk("utilization_risk", "low", "low", "manageable", "utilization_assumption_not_aggressive", "Keep utilization in assumption review.", "Analyst Coach", "monitor")


def opex_pressure_risk(finance: dict[str, Any]) -> dict[str, Any]:
    baseline = finance.get("baseline") or {}
    opex = (finance.get("opex_breakdown") or {}).get("total_monthly_opex")
    revenue = baseline.get("revenue")
    if not opex or not revenue:
        return risk("opex_pressure_risk", "critical", "high", "decision_blocked", "opex_or_revenue_not_ready", "Complete operating cost inputs.", "Technical Auditor")
    ratio = opex / revenue
    if ratio > 0.6:
        return risk("opex_pressure_risk", "high", "medium", "margin_pressure", "opex_above_60_percent_of_revenue", "Reduce fixed OPEX or increase validated revenue capacity.", "Project Manager")
    return risk("opex_pressure_risk", "low", "low", "manageable", "opex_ratio_within_local_threshold", "Monitor OPEX during stabilization.", "Project Manager", "monitor")


def source_governance_risk(source_policy: dict[str, Any]) -> dict[str, Any]:
    if source_policy.get("external_fetch_enabled"):
        return risk("source_governance_risk", "critical", "high", "policy_violation", "external_fetch_enabled", "Disable external fetch and re-review source policy.", "Technical Auditor")
    if not source_policy.get("enabled_sources", []):
        return risk("source_governance_risk", "medium", "high", "evidence_limit", "no_enabled_open_data_source", "Complete human review for exact open datasets.", "Technical Auditor")
    return risk("source_governance_risk", "low", "low", "manageable", "enabled_sources_reviewed", "Keep source review snapshots current.", "Technical Auditor", "monitor")


def evidence_readiness_risk(evidence_register: dict[str, Any]) -> dict[str, Any]:
    linked_dataset_ids = set(evidence_register.get("linked_dataset_ids", []))
    if any(
        row.get("status") == "failed" and row.get("dataset_id") in linked_dataset_ids
        for row in evidence_register.get("quality_gates", [])
    ):
        return risk("evidence_readiness_risk", "high", "high", "assumption_support_gap", "dataset_quality_gate_failed", "Fix dataset review fields or remove the dataset link.", "Analyst Coach")
    if not evidence_register.get("evidence_links", []):
        return risk("evidence_readiness_risk", "medium", "high", "assumption_support_gap", "no_evidence_links", "Link approved datasets to critical assumptions.", "Analyst Coach")
    return risk("evidence_readiness_risk", "low", "low", "manageable", "evidence_links_present", "Review evidence freshness before final use.", "Analyst Coach", "monitor")


def severity_rank(severity: str) -> int:
    return {"low": 1, "medium": 2, "high": 3, "critical": 4}.get(severity, 0)
