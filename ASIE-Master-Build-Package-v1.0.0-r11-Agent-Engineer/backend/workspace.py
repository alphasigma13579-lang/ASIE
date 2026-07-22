from __future__ import annotations

from typing import Any

from backend.decision_pack import build_action_items_from_overview
from backend.reports import build_report_view
from backend.workflow import project_readiness


def build_project_workspace(repo: Any, project_id: str) -> dict[str, Any] | None:
    project = repo.get_project(project_id)
    if project is None:
        return None
    assumptions = repo.project_assumptions(project_id)
    sources = repo.source_records()
    runs = repo.list_project_runs(project_id)
    latest_run = runs[0] if runs else None
    latest_overview = repo.get_run_overview(latest_run["run_id"]) if latest_run else None
    latest_report = repo.get_snapshot_report(latest_run["snapshot_id"]) if latest_run else None
    latest_review = repo.latest_snapshot_review(latest_run["snapshot_id"]) if latest_run else None
    action_items = (
        build_action_items_from_overview(project_id, latest_overview, repo.project_action_item_states(project_id))
        if latest_overview
        else []
    )
    return {
        "project": project.to_public(),
        "readiness": project_readiness(project, assumptions, sources),
        "assumptions": assumptions,
        "runs": [summarize_run(repo, row) for row in runs],
        "latest_overview": latest_overview,
        "latest_report_view": build_report_view(latest_report, latest_review) if latest_report else None,
        "latest_review": latest_review,
        "action_items": action_items,
        "remediation": build_project_remediation(repo, project_id),
    }


def summarize_run(repo: Any, row: dict[str, Any]) -> dict[str, Any]:
    overview = repo.get_run_overview(row["run_id"]) or {}
    return row | {
        "sovereign_verdict": overview.get("decision", {}).get("sovereign_verdict", "UNKNOWN"),
        "acceptance_status": overview.get("acceptance", {}).get("status", "unknown"),
        "data_badge": overview.get("project", {}).get("data_badge", "UNKNOWN"),
        "monte_carlo_probability": overview.get("monte_carlo", {}).get("p_pass"),
    }


def build_project_remediation(repo: Any, project_id: str) -> dict[str, Any]:
    latest_run = repo.latest_project_run(project_id)
    if latest_run:
        overview = repo.get_run_overview(latest_run["run_id"]) or {}
        return {
            "project_id": project_id,
            "source": "latest_snapshot",
            "run_id": latest_run["run_id"],
            "snapshot_id": latest_run["snapshot_id"],
            "items": overview.get("remediation_envelopes", []),
            "blockers": overview.get("blockers", []),
        }
    project = repo.get_project(project_id)
    if project is None:
        return {"project_id": project_id, "source": "missing_project", "items": [], "blockers": []}
    readiness = project_readiness(project, repo.project_assumptions(project_id), repo.source_records())
    return {
        "project_id": project_id,
        "source": "draft_readiness",
        "run_id": None,
        "snapshot_id": None,
        "items": [
            {
                "remediation_id": f"step_{step['step_id']}",
                "trigger_code": step["status"],
                "target": step["step_id"],
                "message": step["message"],
                "allowed_action": "user_edit_only",
                "status": "open",
            }
            for step in readiness["steps"]
            if step["status"] != "ready"
        ],
        "blockers": readiness["blockers"],
    }


def compare_snapshots(first: dict[str, Any], second: dict[str, Any]) -> dict[str, Any]:
    first_kpis = {item["output_id"]: item for item in first.get("kpis", [])}
    second_kpis = {item["output_id"]: item for item in second.get("kpis", [])}
    tracked = ["npv", "irr", "mc-feasibility-gate-probability", "monthly-profit", "funding-gap"]
    return {
        "comparison_id": f"compare_{first['snapshot']['snapshot_id']}_{second['snapshot']['snapshot_id']}",
        "snapshot_a_id": first["snapshot"]["snapshot_id"],
        "snapshot_b_id": second["snapshot"]["snapshot_id"],
        "project_id": first["project"]["project_id"],
        "recalculated": False,
        "metric_deltas": [metric_delta(metric, first_kpis.get(metric), second_kpis.get(metric)) for metric in tracked],
        "verdict_change": {
            "from": first["decision"]["sovereign_verdict"],
            "to": second["decision"]["sovereign_verdict"],
            "changed": first["decision"]["sovereign_verdict"] != second["decision"]["sovereign_verdict"],
        },
        "assumption_changes": compare_assumptions(first.get("assumption_book", []), second.get("assumption_book", [])),
        "acceptance_change": {
            "from": first.get("acceptance", {}).get("status"),
            "to": second.get("acceptance", {}).get("status"),
            "changed": first.get("acceptance", {}).get("status") != second.get("acceptance", {}).get("status"),
        },
    }


def metric_delta(metric: str, first: dict[str, Any] | None, second: dict[str, Any] | None) -> dict[str, Any]:
    first_value = first.get("value") if first else None
    second_value = second.get("value") if second else None
    delta = None
    if isinstance(first_value, (int, float)) and isinstance(second_value, (int, float)):
        delta = second_value - first_value
    return {
        "output_id": metric,
        "from": first_value,
        "to": second_value,
        "delta": delta,
        "unit": (second or first or {}).get("unit", ""),
    }


def compare_assumptions(first: list[dict[str, Any]], second: list[dict[str, Any]]) -> list[dict[str, Any]]:
    first_rows = {row["input_key"]: row for row in first}
    second_rows = {row["input_key"]: row for row in second}
    changes = []
    for key in sorted(set(first_rows) | set(second_rows)):
        before = first_rows.get(key, {})
        after = second_rows.get(key, {})
        if before.get("value") != after.get("value") or before.get("review_status") != after.get("review_status"):
            changes.append(
                {
                    "input_key": key,
                    "label": after.get("label") or before.get("label") or key,
                    "from": before.get("value"),
                    "to": after.get("value"),
                    "review_from": before.get("review_status"),
                    "review_to": after.get("review_status"),
                }
            )
    return changes
