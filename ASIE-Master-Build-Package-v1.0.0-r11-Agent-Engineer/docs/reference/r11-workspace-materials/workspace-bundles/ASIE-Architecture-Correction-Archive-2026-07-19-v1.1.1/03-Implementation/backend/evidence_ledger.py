from __future__ import annotations

from typing import Any

from backend.datasets import dataset_quality_gate
from backend.transformations import transformation_quality_review


def build_evidence_ledger(
    evidence_register: dict[str, Any],
    source_records: list[dict[str, Any]],
    snapshot_id: str,
    run_id: str | None = None,
    transformations: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    datasets = {row["dataset_id"]: row for row in evidence_register.get("datasets", [])}
    sources = {row["source_id"]: row for row in source_records}
    gates = {row["dataset_id"]: row for row in evidence_register.get("quality_gates", [])}
    transformations_by_id = {row["transformation_id"]: row for row in transformations or []}
    ledger = []
    for link in evidence_register.get("evidence_links", []):
        dataset = datasets.get(link.get("dataset_id"), {})
        source = sources.get(dataset.get("source_id"), {})
        gate = gates.get(dataset.get("dataset_id")) or dataset_quality_gate(dataset, source)
        transformation = transformations_by_id.get(link.get("transformation_id") or "", {})
        transformation_review = (
            transformation_quality_review(transformation, dataset)
            if link.get("transformation_id")
            else {"status": "not_required", "reasons": []}
        )
        transformation_ready = not link.get("transformation_id") or transformation_review.get("status") == "passed"
        confidence = evidence_confidence_score(source, dataset, gate, transformation_review, link)
        ledger.append(
            {
                "ledger_id": f"ledger_{link.get('evidence_link_id')}",
                "evidence_link_id": link.get("evidence_link_id", ""),
                "project_id": link.get("project_id", ""),
                "snapshot_id": snapshot_id,
                "run_id": run_id,
                "target_type": link.get("target_type") or "assumption",
                "target_id": link.get("target_id") or link.get("assumption_id", ""),
                "dataset_id": dataset.get("dataset_id", ""),
                "dataset_title": dataset.get("title", ""),
                "source_id": source.get("source_id", dataset.get("source_id", "")),
                "source_state": source.get("state", "candidate"),
                "dataset_review_status": dataset.get("review_status", ""),
                "quality_gate_status": gate.get("status", "failed"),
                "data_quality_status": gate.get("quality_review", {}).get("status", "unknown"),
                "data_quality_reasons": gate.get("quality_review", {}).get("reasons", []),
                "can_support_target": bool(
                    gate.get("can_use_for_assumptions")
                    and link.get("human_review_decision") == "approved"
                    and transformation_ready
                ),
                "evidence_confidence_score": confidence["score"],
                "evidence_confidence_status": confidence["status"],
                "evidence_confidence_factors": confidence["factors"],
                "evidence_ref": link.get("evidence_ref", ""),
                "transformation_id": link.get("transformation_id") or "",
                "transformation_status": transformation.get(
                    "review_status",
                    "not_required" if not link.get("transformation_id") else "missing",
                ),
                "transformation_quality_status": transformation_review.get("status", "not_required"),
                "transformation_review_reasons": transformation_review.get("reasons", []),
                "transformation_operation": transformation.get("operation_type", ""),
                "transformation_output_value": transformation.get("output_value"),
                "transformation_output_unit": transformation.get("output_unit", ""),
                "transformation_note": link.get("transformation_note", ""),
                "human_review_decision": link.get("human_review_decision", ""),
                "external_fetch_enabled": False,
            }
        )
    return ledger


def evidence_confidence_score(
    source: dict[str, Any],
    dataset: dict[str, Any],
    gate: dict[str, Any],
    transformation_review: dict[str, Any],
    link: dict[str, Any],
) -> dict[str, Any]:
    factors = {
        "source_review": 0.25 if source.get("state") == "enabled" and source.get("reviewer_decision") == "approved" else 0.0,
        "dataset_review": 0.2 if dataset.get("review_status") == "approved_for_use" and dataset.get("human_review_decision") == "approved" else 0.0,
        "data_quality": quality_score(gate.get("quality_review", {}).get("status", "unknown")),
        "transformation_review": transformation_score(transformation_review.get("status", "not_required")),
        "evidence_link_review": 0.1 if link.get("human_review_decision") == "approved" else 0.0,
    }
    score = round(min(1.0, sum(factors.values())), 2)
    status = "high" if score >= 0.8 else "medium" if score >= 0.55 else "low"
    return {"score": score, "status": status, "factors": factors}


def quality_score(status: str) -> float:
    if status == "passed":
        return 0.25
    if status == "warning":
        return 0.15
    return 0.0


def transformation_score(status: str) -> float:
    if status == "passed":
        return 0.2
    if status == "warning":
        return 0.1
    if status == "not_required":
        return 0.12
    return 0.0


def build_evidence_coverage(
    assumptions: list[dict[str, Any]],
    sector_intelligence: dict[str, Any],
    evidence_ledger: list[dict[str, Any]],
) -> dict[str, Any]:
    assumption_targets = [
        {
            "target_type": "assumption",
            "target_id": row["assumption_id"],
            "label": row.get("label", row["assumption_id"]),
            "coverage_status": target_status("assumption", row["assumption_id"], evidence_ledger),
        }
        for row in assumptions
    ]
    sector_targets = [
        {
            "target_type": "sector_criterion",
            "target_id": row["criterion_id"],
            "label": row.get("label", row["criterion_id"]),
            "coverage_status": target_status("sector_criterion", row["criterion_id"], evidence_ledger),
        }
        for row in (sector_intelligence.get("sector_criteria") or {}).get("criteria", [])
    ]
    targets = assumption_targets + sector_targets
    gaps = [
        {
            "target_type": row["target_type"],
            "target_id": row["target_id"],
            "label": row["label"],
            "reason": "no_approved_evidence_binding",
        }
        for row in targets
        if row["coverage_status"] != "supported"
    ]
    supported = sum(1 for row in targets if row["coverage_status"] == "supported")
    return {
        "coverage_id": f"evidence-coverage:{sector_intelligence.get('sector_intelligence_id', 'local')}",
        "status": "supported" if targets and supported == len(targets) else "needs_evidence",
        "supported": supported,
        "needs_evidence": len(targets) - supported,
        "targets": targets,
        "gaps": gaps,
    }


def target_status(target_type: str, target_id: str, ledger: list[dict[str, Any]]) -> str:
    if any(
        row.get("target_type") == target_type and row.get("target_id") == target_id and row.get("can_support_target")
        for row in ledger
    ):
        return "supported"
    if target_type == "sector_criterion" and target_id == "vision_2030_alignment":
        return "reference_only"
    return "needs_evidence"
