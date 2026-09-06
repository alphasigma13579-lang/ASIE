from __future__ import annotations

from copy import deepcopy
from html import escape
from typing import Any

from backend.contracts import new_id, now_iso
from backend.snapshot_assembly import canonical_hash
from backend.customer_presentation import business_text, normalize_locale, safe_narrative, status_text, text


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


def render_decision_pack_html(pack: dict[str, Any], locale: str = "ar") -> str:
    """Render a localized customer memo without audit or internal identifiers."""
    locale = normalize_locale(locale)
    direction = "rtl" if locale == "ar" else "ltr"
    align = "right" if locale == "ar" else "left"
    memo = pack.get("memo", {})
    finance_rows = "".join(
        f"<tr><td>{escape(business_text(key, locale))}</td><td>{escape(str(value if value is not None else '—'))}</td></tr>"
        for key, value in pack.get("finance_highlights", {}).items()
    )
    gate_rows = "".join(
        f"<tr><td>{escape(business_text(row.get('label'), locale))}</td>"
        f"<td>{escape(status_text(row.get('status'), locale))}</td>"
        f"<td>{escape(', '.join(business_text(reason, locale) for reason in row.get('reasons') or []) or text('none', locale))}</td></tr>"
        for row in pack.get("readiness_gates", {}).get("gates", [])
    )
    risk_rows = "".join(
        f"<tr><td>{escape(business_text(row.get('trigger'), locale))}</td>"
        f"<td>{escape(status_text(row.get('severity'), locale))}</td>"
        f"<td>{escape(safe_narrative(row.get('mitigation'), locale))}</td></tr>"
        for row in pack.get("top_risks", [])
    )
    milestone_rows = "".join(
        f"<tr><td>{escape(business_text(row.get('phase_id'), locale))}</td>"
        f"<td>{escape(business_text(row.get('owner_role'), locale))}</td>"
        f"<td>{escape(str(row.get('estimated_duration_days') or '—'))}</td></tr>"
        for row in pack.get("execution_plan", {}).get("milestones", [])
    )
    labels = {
        "title": ("مذكرة القرار", "Decision memo"),
        "recommendation": ("التوصية", "Recommendation"),
        "reason": ("لماذا هذه التوصية؟", "Why this recommendation?"),
        "review": ("حالة المراجعة", "Review status"),
        "finance": ("المؤشرات المالية المختصرة", "Financial highlights"),
        "item": ("البند", "Item"),
        "value": ("القيمة", "Value"),
        "readiness": ("متطلبات الجاهزية", "Readiness requirements"),
        "risk": ("المخاطر وخطة المعالجة", "Risks and mitigation"),
        "severity": ("الأهمية", "Severity"),
        "action": ("الإجراء المقترح", "Recommended action"),
        "plan": ("خطة التنفيذ", "Execution plan"),
        "phase": ("المرحلة", "Phase"),
        "owner": ("المسؤول", "Owner"),
        "days": ("الأيام", "Days"),
        "private": ("سجل التدقيق والتفاصيل الفنية متاحان للمشرف فقط.", "The audit trail and technical details are available to administrators only."),
    }
    def label(key: str) -> str:
        pair = labels[key]
        return pair[1] if locale == "en" else pair[0]
    return f"""<!doctype html>
<html lang="{locale}" dir="{direction}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(label('title'))}</title><style>
:root{{--ink:#0f3328;--muted:#6b7d76;--line:#dce7e0;--green:#138a66;--soft:#f5f9f6}}
*{{box-sizing:border-box}}body{{font-family:Tahoma,Arial,sans-serif;margin:0;background:#f1f5f2;color:var(--ink);line-height:1.65}}
main{{max-width:1000px;margin:28px auto;background:#fff;border:1px solid var(--line);padding:38px 44px;box-shadow:0 12px 36px #12382a14}}
.memo{{padding:24px;border-radius:16px;background:linear-gradient(135deg,#edf7f2,#fff);border:1px solid var(--line)}}table{{width:100%;border-collapse:collapse;margin:12px 0 24px}}th,td{{border:1px solid var(--line);padding:9px;text-align:{align}}}th{{background:#edf7f2}}
footer{{margin-top:28px;color:var(--muted)}}@media(max-width:760px){{main{{margin:0;padding:18px}}table{{font-size:12px}}}}
</style></head><body><main>
<h1>{escape(label('title'))}</h1><div class="memo"><h2>{escape(label('recommendation'))}</h2>
<p><strong>{escape(status_text(memo.get('recommendation'), locale))}</strong></p>
<h3>{escape(label('reason'))}</h3><p>{escape(safe_narrative(memo.get('rationale'), locale))}</p>
<p>{escape(label('review'))}: {escape(status_text(memo.get('review_status'), locale))}</p></div>
<h2>{escape(label('finance'))}</h2><table><thead><tr><th>{escape(label('item'))}</th><th>{escape(label('value'))}</th></tr></thead><tbody>{finance_rows}</tbody></table>
<h2>{escape(label('readiness'))}</h2><table><thead><tr><th>{escape(text('requirement', locale))}</th><th>{escape(text('status', locale))}</th><th>{escape(text('reason', locale))}</th></tr></thead><tbody>{gate_rows}</tbody></table>
<h2>{escape(label('risk'))}</h2><table><thead><tr><th>{escape(label('risk'))}</th><th>{escape(label('severity'))}</th><th>{escape(label('action'))}</th></tr></thead><tbody>{risk_rows}</tbody></table>
<h2>{escape(label('plan'))}</h2><table><thead><tr><th>{escape(label('phase'))}</th><th>{escape(label('owner'))}</th><th>{escape(label('days'))}</th></tr></thead><tbody>{milestone_rows}</tbody></table>
<footer>{escape(label('private'))}</footer></main></body></html>"""
