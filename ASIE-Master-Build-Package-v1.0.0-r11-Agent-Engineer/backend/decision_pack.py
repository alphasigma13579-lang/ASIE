from __future__ import annotations

from copy import deepcopy
from html import escape
from typing import Any

from backend.contracts import new_id, now_iso
from backend.snapshot_assembly import canonical_hash


REVIEW_DECISIONS = {"draft_review", "needs_changes", "approved_local", "rejected_local"}
ACTION_STATUSES = {"open", "closed"}


def normalize_review(snapshot_id: str, run_id: str, project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    decision = str(payload.get("decision") or "draft_review")
    if decision not in REVIEW_DECISIONS:
        raise ValueError("invalid_review_decision")
    return {
        "review_id": str(payload.get("review_id") or new_id("review")),
        "snapshot_id": snapshot_id,
        "run_id": run_id,
        "project_id": project_id,
        "reviewer": str(payload.get("reviewer") or "local-reviewer"),
        "decision": decision,
        "notes": str(payload.get("notes") or ""),
        "created_at": str(payload.get("created_at") or now_iso()),
    }


def normalize_action_item_patch(project_id: str, action_item_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    status = str(payload.get("status") or "open")
    if status not in ACTION_STATUSES:
        raise ValueError("invalid_action_item_status")
    return {
        "action_item_id": action_item_id,
        "project_id": project_id,
        "status": status,
        "notes": str(payload.get("notes") or ""),
        "updated_at": now_iso(),
    }


def build_decision_pack(
    snapshot_overview: dict[str, Any],
    snapshot_report: dict[str, Any],
    reviews: list[dict[str, Any]],
) -> dict[str, Any]:
    return apply_review_overlay(build_decision_pack_base(snapshot_overview, snapshot_report), reviews)


def build_decision_pack_base(
    snapshot_overview: dict[str, Any],
    snapshot_report: dict[str, Any],
) -> dict[str, Any]:
    validate_decision_pack_snapshot_inputs(snapshot_overview, snapshot_report)
    snapshot_id = snapshot_overview["snapshot"]["snapshot_id"]
    run_id = snapshot_overview["run"]["run_id"]
    decision = snapshot_overview["decision"]
    finance = snapshot_overview.get("finance", {})
    baseline = finance.get("baseline") or {}
    readiness_gates = snapshot_overview.get("readiness_gates", {})
    risk_register = snapshot_overview.get("risk_register", {})
    execution_plan = snapshot_overview.get("execution_plan", {})
    sector_intelligence = snapshot_overview.get("sector_intelligence", {})
    audit = snapshot_overview.get("audit", {})
    memo = {
        "memo_id": f"memo_{snapshot_id}",
        "title": f"Decision memo - {snapshot_overview['project']['name']}",
        "recommendation": decision.get("sovereign_verdict", "UNKNOWN"),
        "rationale": decision.get("reason", ""),
        "review_status": "draft_review",
        "next_review_action": next_review_action("draft_review", readiness_gates),
    }
    pack = {
        "decision_pack_id": f"decision-pack_{snapshot_id}",
        "contract_id": "decision.pack.v1",
        "snapshot_id": snapshot_id,
        "run_id": run_id,
        "project_id": snapshot_overview["project"]["project_id"],
        "created_at": snapshot_overview["snapshot"]["created_at"],
        "immutable_snapshot": True,
        "memo": memo,
        "latest_review": None,
        "reviews": [],
        "finance_highlights": {
            "npv": baseline.get("npv"),
            "irr": baseline.get("irr"),
            "monthly_profit": baseline.get("monthly_profit"),
            "funding_need_after_equity": baseline.get("funding_need_after_equity"),
            "dscr": (finance.get("debt_service_profile") or {}).get("dscr"),
            "monte_carlo_status": snapshot_overview.get("monte_carlo", {}).get("status"),
        },
        "readiness_gates": readiness_gates,
        "top_risks": risk_register.get("top_risks", []),
        "risk_register": risk_register,
        "execution_plan": execution_plan,
        "sector_intelligence": sector_intelligence,
        "evidence_ledger": snapshot_overview.get("evidence_ledger", []),
        "evidence_coverage": snapshot_overview.get("evidence_coverage", {}),
        "transformation_lineage": snapshot_overview.get("transformation_lineage", []),
        "assumptions": snapshot_overview.get("assumption_book", []),
        "evidence": snapshot_overview.get("evidence_register", {}),
        "source_governance": snapshot_overview.get("source_policy", {}),
        "audit_lineage": {
            "audit_id": audit.get("audit_id"),
            "owner_path": audit.get("owner_path"),
            "algorithm_versions": audit.get("algorithm_versions", {}),
            "report_id": snapshot_report.get("report_id"),
        },
        "snapshot_assembly": {
            "contract_id": snapshot_overview["snapshot_assembly"]["contract_id"],
            "content_hash": snapshot_overview["snapshot"]["content_hash"],
            "integrity_hash": snapshot_overview["snapshot"]["integrity_hash"],
            "overview_projection_hash": snapshot_overview["snapshot_assembly"]["overview_projection_hash"],
            "report_projection_hash": snapshot_report["snapshot_assembly"]["report_projection_hash"],
            "projection_source": "immutable_saved_snapshot",
        },
        "review_overlay": None,
        "external_fetch_enabled": False,
        "ai_enabled": False,
    }
    pack["decision_pack_hash"] = canonical_hash(pack)
    return pack


def apply_review_overlay(base_pack: dict[str, Any], reviews: list[dict[str, Any]]) -> dict[str, Any]:
    pack = deepcopy(base_pack)
    expected_hash = pack.get("decision_pack_hash")
    base_material = deepcopy(pack)
    base_material.pop("decision_pack_hash", None)
    if not expected_hash or canonical_hash(base_material) != expected_hash:
        raise ValueError("decision_pack_base_hash_mismatch")
    for review in reviews:
        for identity_field in ("snapshot_id", "run_id", "project_id"):
            if review.get(identity_field) != pack.get(identity_field):
                raise ValueError(f"review_overlay_{identity_field}_mismatch")
    normalized_reviews = sorted((deepcopy(row) for row in reviews), key=lambda row: row.get("created_at", ""), reverse=True)
    latest_review = latest_review_record(normalized_reviews)
    review_status = latest_review["decision"] if latest_review else "draft_review"
    pack["latest_review"] = latest_review
    pack["reviews"] = normalized_reviews
    pack["memo"]["review_status"] = review_status
    pack["memo"]["next_review_action"] = next_review_action(review_status, pack["readiness_gates"])
    overlay_material = {
        "base_decision_pack_hash": expected_hash,
        "snapshot_id": pack["snapshot_id"],
        "reviews": normalized_reviews,
    }
    pack["review_overlay"] = {
        "overlay_id": f"review-overlay:{pack['snapshot_id']}",
        "base_decision_pack_hash": expected_hash,
        "review_count": len(normalized_reviews),
        "latest_review_id": latest_review.get("review_id") if latest_review else None,
        "overlay_hash": canonical_hash(overlay_material),
        "separate_from_snapshot_hash": True,
    }
    return pack


def validate_decision_pack_snapshot_inputs(
    snapshot_overview: dict[str, Any],
    snapshot_report: dict[str, Any],
) -> None:
    snapshot = snapshot_overview.get("snapshot", {})
    assembly = snapshot_overview.get("snapshot_assembly", {})
    report_assembly = snapshot_report.get("snapshot_assembly", {})
    if snapshot.get("immutable") is not True or assembly.get("contract_id") != "snapshot.assemble.v1":
        raise ValueError("decision_pack_requires_immutable_assembled_snapshot")
    if assembly.get("projection_source") != "immutable_assembled_snapshot":
        raise ValueError("decision_pack_requires_assembled_snapshot_projection")
    for identity_field, overview_value, report_value in (
        ("snapshot_id", snapshot.get("snapshot_id"), snapshot_report.get("snapshot_id")),
        ("run_id", snapshot_overview.get("run", {}).get("run_id"), snapshot_report.get("run_id")),
        ("project_id", snapshot_overview.get("project", {}).get("project_id"), snapshot_report.get("project_id")),
    ):
        if not overview_value or overview_value != report_value:
            raise ValueError(f"decision_pack_{identity_field}_mismatch")
    if report_assembly.get("content_hash") != snapshot.get("content_hash"):
        raise ValueError("decision_pack_content_hash_mismatch")
    if report_assembly.get("integrity_hash") != snapshot.get("integrity_hash"):
        raise ValueError("decision_pack_integrity_hash_mismatch")
    overview_projection_hash = assembly.get("overview_projection_hash")
    overview_material = deepcopy(snapshot_overview)
    overview_material.get("snapshot_assembly", {}).pop("overview_projection_hash", None)
    if not overview_projection_hash or canonical_hash(overview_material) != overview_projection_hash:
        raise ValueError("decision_pack_overview_projection_hash_mismatch")
    report_projection_hash = report_assembly.get("report_projection_hash")
    report_material = deepcopy(snapshot_report)
    report_material.get("snapshot_assembly", {}).pop("report_projection_hash", None)
    if not report_projection_hash or canonical_hash(report_material) != report_projection_hash:
        raise ValueError("decision_pack_report_projection_hash_mismatch")


def latest_review_record(reviews: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not reviews:
        return None
    return sorted(reviews, key=lambda row: row.get("created_at", ""), reverse=True)[0]


def next_review_action(review_status: str, readiness_gates: dict[str, Any]) -> str:
    if review_status == "approved_local":
        return "local_review_complete"
    if review_status == "rejected_local":
        return "rebuild_project_draft"
    if readiness_gates.get("blocked", 0):
        return "close_blocked_gates_before_approval"
    if readiness_gates.get("warnings", 0):
        return "review_warnings_or_request_changes"
    return "approve_or_request_changes"


def build_action_items_from_overview(
    project_id: str,
    overview: dict[str, Any],
    status_overrides: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    status_overrides = status_overrides or {}
    snapshot_id = overview.get("snapshot", {}).get("snapshot_id")
    run_id = overview.get("run", {}).get("run_id")
    created_at = overview.get("snapshot", {}).get("created_at")
    items: list[dict[str, Any]] = []
    for gate in (overview.get("readiness_gates") or {}).get("gates", []):
        if gate.get("status") in {"blocked", "warning"}:
            items.append(
                action_item(
                    project_id,
                    "gate",
                    str(gate.get("gate_id") or "unknown_gate"),
                    str(gate.get("label") or gate.get("gate_id") or "Readiness gate"),
                    "high" if gate.get("status") == "blocked" else "medium",
                    ", ".join(gate.get("reasons") or []),
                    "Resolve gate reasons and rerun a new snapshot.",
                    snapshot_id,
                    run_id,
                    created_at,
                )
            )
    for risk in (overview.get("risk_register") or {}).get("risks", []):
        if risk.get("status") == "open" and risk.get("severity") in {"medium", "high", "critical"}:
            items.append(
                action_item(
                    project_id,
                    "risk",
                    str(risk.get("risk_id") or "unknown_risk"),
                    str(risk.get("trigger") or risk.get("risk_id") or "Risk"),
                    str(risk.get("severity") or "medium"),
                    str(risk.get("impact") or ""),
                    str(risk.get("mitigation") or "Review and mitigate the risk."),
                    snapshot_id,
                    run_id,
                    created_at,
                )
            )
    for blocker in overview.get("blockers", []):
        if blocker.get("severity") in {"high", "critical"}:
            items.append(
                action_item(
                    project_id,
                    "blocker",
                    str(blocker.get("code") or "unknown_blocker"),
                    str(blocker.get("code") or "Blocker"),
                    str(blocker.get("severity") or "high"),
                    str(blocker.get("message") or ""),
                    "Update draft inputs or governance state, then rerun a new snapshot.",
                    snapshot_id,
                    run_id,
                    created_at,
                )
            )
    merged = []
    seen: set[str] = set()
    for item in items:
        if item["action_item_id"] in seen:
            continue
        seen.add(item["action_item_id"])
        override = status_overrides.get(item["action_item_id"], {})
        merged.append(item | {"status": override.get("status", item["status"]), "notes": override.get("notes", ""), "updated_at": override.get("updated_at")})
    return merged


def action_item(
    project_id: str,
    source_type: str,
    source_id: str,
    title: str,
    severity: str,
    message: str,
    recommended_action: str,
    snapshot_id: str | None,
    run_id: str | None,
    created_from_snapshot_at: str | None,
) -> dict[str, Any]:
    safe_source_id = "".join(char if char.isalnum() or char in {"_", "-"} else "_" for char in source_id)
    return {
        "action_item_id": f"action_{source_type}_{safe_source_id}",
        "project_id": project_id,
        "source_type": source_type,
        "source_id": source_id,
        "title": title,
        "severity": severity,
        "status": "open",
        "message": message,
        "recommended_action": recommended_action,
        "snapshot_id": snapshot_id,
        "run_id": run_id,
        "created_from_snapshot_at": created_from_snapshot_at,
    }


def render_decision_pack_html(pack: dict[str, Any]) -> str:
    finance_rows = "".join(
        f"<tr><td>{escape(key)}</td><td>{escape(str(value))}</td></tr>"
        for key, value in pack.get("finance_highlights", {}).items()
    )
    gate_rows = "".join(
        f"<tr><td>{escape(row.get('label', ''))}</td><td>{escape(row.get('status', ''))}</td>"
        f"<td>{escape(', '.join(row.get('reasons') or []))}</td></tr>"
        for row in pack.get("readiness_gates", {}).get("gates", [])
    )
    risk_rows = "".join(
        f"<tr><td>{escape(row.get('risk_id', ''))}</td><td>{escape(row.get('severity', ''))}</td>"
        f"<td>{escape(row.get('trigger', ''))}</td><td>{escape(row.get('mitigation', ''))}</td></tr>"
        for row in pack.get("top_risks", [])
    )
    milestone_rows = "".join(
        f"<tr><td>{escape(row.get('phase_id', ''))}</td><td>{escape(row.get('owner_role', ''))}</td>"
        f"<td>{escape(str(row.get('estimated_duration_days', '')))}</td></tr>"
        for row in pack.get("execution_plan", {}).get("milestones", [])
    )
    sector = pack.get("sector_intelligence", {})
    taxonomy = sector.get("taxonomy_record") or {}
    sector_rows = "".join(
        f"<tr><td>{escape(row.get('label', ''))}</td><td>{escape(row.get('sector_value', ''))}</td>"
        f"<td>{escape(row.get('evidence_status', ''))}</td></tr>"
        for row in sector.get("sector_criteria", {}).get("criteria", [])
    )
    coverage = pack.get("evidence_coverage", {})
    coverage_rows = "".join(
        f"<tr><td>{escape(row.get('target_type', ''))}</td><td>{escape(row.get('label', ''))}</td>"
        f"<td>{escape(row.get('coverage_status', ''))}</td></tr>"
        for row in coverage.get("targets", [])[:20]
    )
    ledger_rows = "".join(
        f"<tr><td>{escape(row.get('target_type', ''))}:{escape(row.get('target_id', ''))}</td>"
        f"<td>{escape(row.get('data_quality_status', ''))}</td>"
        f"<td>{escape(row.get('transformation_quality_status', ''))}</td>"
        f"<td>{escape(str(row.get('evidence_confidence_score', '')))}</td>"
        f"<td>{escape(row.get('evidence_confidence_status', ''))}</td></tr>"
        for row in pack.get("evidence_ledger", [])
    )
    lineage_rows = "".join(
        f"<tr><td>{escape(row.get('dataset_id', ''))}</td><td>{escape(row.get('transformation_id', ''))}</td>"
        f"<td>{escape(row.get('target_type', ''))}:{escape(row.get('target_id', ''))}</td>"
        f"<td>{escape(row.get('review_status', ''))}</td></tr>"
        for row in pack.get("transformation_lineage", [])
    )
    audit = pack.get("audit_lineage", {})
    memo = pack.get("memo", {})
    return f"""<!doctype html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="utf-8" />
  <title>{escape(memo.get('title', 'Decision Pack'))}</title>
  <style>
    body {{ font-family: Tahoma, Arial, sans-serif; margin: 32px; color: #17201b; }}
    table {{ width: 100%; border-collapse: collapse; margin: 12px 0 24px; }}
    th, td {{ border: 1px solid #dfe5e1; padding: 8px; text-align: right; }}
    th {{ background: #f4f6f4; }}
    .memo {{ padding: 12px; background: #f8fbec; border: 1px solid #d8e6a6; }}
    .meta {{ color: #53645a; }}
  </style>
</head>
<body>
  <h1>{escape(memo.get('title', 'Decision Pack'))}</h1>
  <p class="meta">Snapshot {escape(pack.get('snapshot_id', ''))} · Run {escape(pack.get('run_id', ''))}</p>
  <section class="memo">
    <h2>مذكرة القرار</h2>
    <p><strong>{escape(memo.get('recommendation', ''))}</strong></p>
    <p>{escape(memo.get('rationale', ''))}</p>
    <p>حالة المراجعة: {escape(memo.get('review_status', 'draft_review'))}</p>
  </section>
  <h2>المؤشرات المالية المختصرة</h2>
  <table><thead><tr><th>البند</th><th>القيمة</th></tr></thead><tbody>{finance_rows}</tbody></table>
  <h2>بوابات الجاهزية</h2>
  <table><thead><tr><th>البوابة</th><th>الحالة</th><th>الأسباب</th></tr></thead><tbody>{gate_rows}</tbody></table>
  <h2>أعلى المخاطر</h2>
  <table><thead><tr><th>الخطر</th><th>الشدة</th><th>المحفز</th><th>المعالجة</th></tr></thead><tbody>{risk_rows}</tbody></table>
  <h2>خطة التنفيذ</h2>
  <table><thead><tr><th>المرحلة</th><th>المالك</th><th>الأيام</th></tr></thead><tbody>{milestone_rows}</tbody></table>
  <h2>القطاع ومؤشرات الاستثمار</h2>
  <p>{escape(taxonomy.get('primary_sector_ar') or taxonomy.get('primary_sector') or 'غير مصنف')}</p>
  <table><thead><tr><th>المعيار</th><th>قيمة القطاع</th><th>حالة الدليل</th></tr></thead><tbody>{sector_rows}</tbody></table>
  <h2>سجل الأدلة والتغطية</h2>
  <table><thead><tr><th>نوع الهدف</th><th>الهدف</th><th>حالة التغطية</th></tr></thead><tbody>{coverage_rows}</tbody></table>
  <table><thead><tr><th>الهدف</th><th>جودة البيانات</th><th>جودة التحويل</th><th>درجة الثقة</th><th>حالة الثقة</th></tr></thead><tbody>{ledger_rows}</tbody></table>
  <h2>مسار التحويلات</h2>
  <table><thead><tr><th>Dataset</th><th>Transformation</th><th>Target</th><th>المراجعة</th></tr></thead><tbody>{lineage_rows}</tbody></table>
  <h2>التدقيق</h2>
  <p>Audit {escape(str(audit.get('audit_id') or ''))}</p>
  <p>{escape(str(audit.get('owner_path') or ''))}</p>
</body>
</html>"""
