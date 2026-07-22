from __future__ import annotations

from typing import Any


def build_readiness_gates(
    finance: dict[str, Any],
    blockers: list[dict[str, str]],
    evidence_register: dict[str, Any],
    source_policy: dict[str, Any],
) -> dict[str, Any]:
    gates = [
        financial_gate(finance, blockers),
        operating_gate(finance),
        evidence_gate(evidence_register),
        source_governance_gate(source_policy),
        debt_service_gate(finance),
    ]
    gates.append(launch_gate(gates))
    blocked = sum(1 for gate in gates if gate["status"] == "blocked")
    warnings = sum(1 for gate in gates if gate["status"] == "warning")
    return {
        "gate_set_id": "readiness-gates-v1-local",
        "status": "blocked" if blocked else "warning" if warnings else "passed",
        "passed": sum(1 for gate in gates if gate["status"] == "passed"),
        "warnings": warnings,
        "blocked": blocked,
        "gates": gates,
    }


def gate(gate_id: str, label: str, status: str, reasons: list[str]) -> dict[str, Any]:
    return {
        "gate_id": gate_id,
        "label": label,
        "status": status,
        "reasons": reasons,
    }


def financial_gate(finance: dict[str, Any], blockers: list[dict[str, str]]) -> dict[str, Any]:
    if finance.get("status") != "ready":
        return gate("financial_readiness", "Financial Readiness", "blocked", [item["code"] for item in blockers])
    baseline = finance.get("baseline") or {}
    reasons: list[str] = []
    if baseline.get("npv", 0) < 0:
        reasons.append("negative_npv")
    if baseline.get("monthly_profit", 0) <= 0:
        reasons.append("non_positive_monthly_profit")
    return gate("financial_readiness", "Financial Readiness", "blocked" if reasons else "passed", reasons)


def operating_gate(finance: dict[str, Any]) -> dict[str, Any]:
    if finance.get("status") != "ready":
        return gate("operating_readiness", "Operating Readiness", "blocked", ["finance_not_ready"])
    operating_model = finance.get("operating_model") or {}
    reasons: list[str] = []
    if not operating_model.get("monthly_units"):
        reasons.append("missing_monthly_units")
    utilization = operating_model.get("utilization_rate") or 0
    if operating_model.get("use_operating_capacity") and utilization < 0.5:
        reasons.append("low_utilization_assumption")
    return gate("operating_readiness", "Operating Readiness", "warning" if reasons else "passed", reasons)


def evidence_gate(evidence_register: dict[str, Any]) -> dict[str, Any]:
    links = evidence_register.get("evidence_links", [])
    linked_dataset_ids = set(evidence_register.get("linked_dataset_ids", []))
    failed_gates = [
        row
        for row in evidence_register.get("quality_gates", [])
        if row.get("status") == "failed" and row.get("dataset_id") in linked_dataset_ids
    ]
    reasons: list[str] = []
    if not links:
        reasons.append("no_assumption_evidence_links")
    if failed_gates:
        reasons.append("dataset_quality_gate_failed")
    return gate("evidence_readiness", "Evidence Readiness", "blocked" if failed_gates else "warning" if reasons else "passed", reasons)


def source_governance_gate(source_policy: dict[str, Any]) -> dict[str, Any]:
    if source_policy.get("external_fetch_enabled"):
        return gate("source_governance", "Source Governance", "blocked", ["external_fetch_enabled"])
    if not source_policy.get("enabled_sources", []):
        return gate("source_governance", "Source Governance", "warning", ["no_enabled_open_data_sources"])
    return gate("source_governance", "Source Governance", "passed", [])


def debt_service_gate(finance: dict[str, Any]) -> dict[str, Any]:
    if finance.get("status") != "ready":
        return gate("debt_service", "Debt Service", "blocked", ["finance_not_ready"])
    profile = finance.get("debt_service_profile") or {}
    if profile.get("status") == "not_ready":
        return gate("debt_service", "Debt Service", "blocked", ["debt_terms_not_ready"])
    dscr = profile.get("dscr")
    if dscr is not None and dscr < 1.2:
        return gate("debt_service", "Debt Service", "warning", ["dscr_below_1_2"])
    return gate("debt_service", "Debt Service", "passed", [])


def launch_gate(gates: list[dict[str, Any]]) -> dict[str, Any]:
    blocked = [row["gate_id"] for row in gates if row["status"] == "blocked"]
    warnings = [row["gate_id"] for row in gates if row["status"] == "warning"]
    if blocked:
        return gate("launch_readiness", "Launch Readiness", "blocked", blocked)
    if warnings:
        return gate("launch_readiness", "Launch Readiness", "warning", warnings)
    return gate("launch_readiness", "Launch Readiness", "passed", [])
