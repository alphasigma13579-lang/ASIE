from __future__ import annotations

from html import escape
from typing import Any

from backend.snapshot_assembly import canonical_hash
from backend.funder_report import build_funder_report_projection, render_funder_report_html
from backend.customer_presentation import business_text, normalize_locale, safe_narrative, status_text, text, unit_text


def remediation(blockers: list[dict[str, str]]) -> list[dict[str, Any]]:
    return [
        {
            "remediation_id": f"rem_{blocker['code'].lower()}",
            "trigger_code": blocker["code"],
            "target": "project_inputs" if blocker["code"].startswith("MISSING") else "governance_review",
            "message": blocker["message"],
            "allowed_action": "user_edit_only",
            "status": "open",
        }
        for blocker in blockers
        if blocker["severity"] in {"high", "critical"}
    ]


def build_report(overview: dict[str, Any]) -> dict[str, Any]:
    report = {
        "report_id": f"report_{overview['snapshot']['snapshot_id']}",
        "snapshot_id": overview["snapshot"]["snapshot_id"],
        "run_id": overview["run"]["run_id"],
        "project_id": overview["project"]["project_id"],
        "title": f"تقرير لقطة ASIE - {overview['project']['name']}",
        "created_at": overview["snapshot"]["created_at"],
        "snapshot_assembly": {
            "contract_id": overview.get("snapshot_assembly", {}).get("contract_id"),
            "content_hash": overview["snapshot"].get("content_hash"),
            "integrity_hash": overview["snapshot"].get("integrity_hash"),
            "projection_source": overview.get("snapshot_assembly", {}).get("projection_source"),
            "overview_projection_hash": overview.get("snapshot_assembly", {}).get("overview_projection_hash"),
        },
        "data_badge": overview["project"]["data_badge"],
        "summary": {
            "sovereign_verdict": overview["decision"]["sovereign_verdict"],
            "reason": overview["decision"]["reason"],
            "monte_carlo_status": overview["monte_carlo"]["status"],
            "monte_carlo_probability": overview["monte_carlo"]["p_pass"],
            "critical_blockers": [blocker for blocker in overview["blockers"] if blocker["severity"] == "critical"],
        },
        "sections": [
            {
                "section_id": "snapshot-parity",
                "title": "تطابق اللقطة",
                "body": "هذا التقرير يقرأ نفس لقطة التشغيل المعروضة في الواجهة ولا يعيد الحساب.",
            },
            {
                "section_id": "finance",
                "title": "المحرك المالي",
                "body": "تشمل اللقطة NPV وIRR والاسترداد والحساسية والسيناريوهات ومونت كارلو من الخلفية فقط.",
            },
            {
                "section_id": "decision-council",
                "title": "مجلس القرار",
                "body": "الشخصيات الخمس معزولة، والحكم السيادي حتمي ولا يعتمد على تصويت.",
            },
            {
                "section_id": "source-governance",
                "title": "حوكمة المصادر",
                "body": "الجلب الخارجي مغلق افتراضيًا، ولا يتم تفعيل أي مصدر إلا بعد مراجعة شروطه.",
            },
            {
                "section_id": "evidence-register",
                "title": "سجل البيانات والأدلة",
                "body": "البيانات المحلية لا تستخدم في دعم الافتراضات إلا بعد اكتمال بوابة الجودة وربطها بمراجعة بشرية وسجل تحويل قابل للتدقيق عند اشتقاق القيم.",
            },
            {
                "section_id": "execution-risk",
                "title": "خطة التنفيذ والمخاطر",
                "body": "تعرض اللقطة مراحل التنفيذ، بوابات الجاهزية، وسجل المخاطر الحتمي بدون إعادة حساب.",
            },
            {
                "section_id": "decision-pack",
                "title": "حزمة القرار والمراجعة",
                "body": "تعرض مذكرة القرار وحالة المراجعة المحلية المرتبطة باللقطة بدون تغيير نتائجها.",
            },
        ],
        "kpis": overview["kpis"],
        "finance": overview["finance"],
        "operating_model": overview["finance"].get("operating_model"),
        "capex_breakdown": overview["finance"].get("capex_breakdown"),
        "opex_breakdown": overview["finance"].get("opex_breakdown"),
        "debt_service_profile": overview["finance"].get("debt_service_profile"),
        "operational_sensitivity": overview["finance"].get("operational_sensitivity"),
        "scenarios": overview["finance"]["scenarios"],
        "sensitivity": overview["finance"]["sensitivity"],
        "decision_council": overview["decision_council"],
        "personas": overview["personas"],
        "blockers": overview["blockers"],
        "source_governance": overview["source_policy"],
        "sector_intelligence": overview.get("sector_intelligence", {}),
        "evidence_ledger": overview.get("evidence_ledger", []),
        "evidence_coverage": overview.get("evidence_coverage", {}),
        "transformation_lineage": overview.get("transformation_lineage", []),
        "assumption_book": overview.get("assumption_book", []),
        "evidence_register": overview.get("evidence_register", {}),
        "readiness_gates": overview.get("readiness_gates", {}),
        "execution_plan": overview.get("execution_plan", {}),
        "risk_register": overview.get("risk_register", {}),
        "risk_advisory_summary": overview.get("risk_advisory_summary", {}),
        "readiness": overview.get("readiness", {}),
        "acceptance": overview.get("acceptance", {}),
        "audit": overview["audit"],
    }
    report["funder_report"] = build_funder_report_projection(overview)
    report["snapshot_assembly"]["report_projection_hash"] = canonical_hash(report)
    return report


def build_report_view(report: dict[str, Any], latest_review: dict[str, Any] | None = None) -> dict[str, Any]:
    summary = report["summary"]
    evidence_register = normalize_evidence_register(report.get("evidence_register", {}))
    review_status = latest_review["decision"] if latest_review else "draft_review"
    return {
        "report_id": report["report_id"],
        "title": report["title"],
        "snapshot_id": report["snapshot_id"],
        "run_id": report["run_id"],
        "project_id": report["project_id"],
        "snapshot_assembly": report.get("snapshot_assembly", {}),
        "executive_summary": {
            "verdict": summary["sovereign_verdict"],
            "reason": summary["reason"],
            "monte_carlo_probability": summary["monte_carlo_probability"],
            "critical_blocker_count": len(summary["critical_blockers"]),
        },
        "sections": report["sections"],
        "headline_kpis": report["kpis"][:6],
        "scenario_table": report["scenarios"],
        "sensitivity": report["sensitivity"],
        "operating_model": report.get("operating_model"),
        "capex_breakdown": report.get("capex_breakdown"),
        "opex_breakdown": report.get("opex_breakdown"),
        "debt_service_profile": report.get("debt_service_profile"),
        "operational_sensitivity": report.get("operational_sensitivity"),
        "assumption_book": report.get("assumption_book", []),
        "evidence_register": evidence_register,
        "readiness_gates": normalize_readiness_gates(report.get("readiness_gates", {})),
        "execution_plan": normalize_execution_plan(report.get("execution_plan", {})),
        "risk_register": normalize_risk_register(report.get("risk_register", {})),
        "risk_advisory_summary": normalize_risk_advisory_summary(report.get("risk_advisory_summary", {})),
        "source_governance": report["source_governance"],
        "sector_intelligence": normalize_sector_intelligence(report.get("sector_intelligence", {})),
        "evidence_ledger": report.get("evidence_ledger", []),
        "evidence_coverage": normalize_evidence_coverage(report.get("evidence_coverage", {})),
        "transformation_lineage": report.get("transformation_lineage", []),
        "review_status": review_status,
        "latest_review": latest_review,
        "decision_pack_summary": {
            "recommendation": summary["sovereign_verdict"],
            "readiness_status": normalize_readiness_gates(report.get("readiness_gates", {}))["status"],
            "top_risk_count": len(normalize_risk_register(report.get("risk_register", {}))["top_risks"]),
            "execution_status": normalize_execution_plan(report.get("execution_plan", {}))["status"],
        },
        "acceptance": report.get("acceptance", {}),
        "audit": report["audit"],
        "funder_report": report.get("funder_report", {}),
    }


def normalize_evidence_register(register: dict[str, Any]) -> dict[str, Any]:
    return {
        "evidence_register_id": register.get("evidence_register_id", ""),
        "snapshot_id": register.get("snapshot_id", ""),
        "source_records": register.get("source_records", []),
        "source_checklists": register.get("source_checklists", []),
        "datasets": register.get("datasets", []),
        "transformations": register.get("transformations", []),
        "evidence_links": register.get("evidence_links", []),
        "quality_gates": register.get("quality_gates", []),
        "not_ready_reasons": register.get("not_ready_reasons", []),
        "external_fetch_enabled": bool(register.get("external_fetch_enabled", False)),
    }


def normalize_readiness_gates(gates: dict[str, Any]) -> dict[str, Any]:
    return {
        "gate_set_id": gates.get("gate_set_id", ""),
        "status": gates.get("status", "unknown"),
        "passed": gates.get("passed", 0),
        "warnings": gates.get("warnings", 0),
        "blocked": gates.get("blocked", 0),
        "gates": gates.get("gates", []),
    }


def normalize_execution_plan(plan: dict[str, Any]) -> dict[str, Any]:
    return {
        "execution_plan_id": plan.get("execution_plan_id", ""),
        "status": plan.get("status", "unknown"),
        "decision_ref": plan.get("decision_ref", ""),
        "estimated_total_duration_days": plan.get("estimated_total_duration_days", 0),
        "blocked_by_gates": plan.get("blocked_by_gates", []),
        "blocked_by_risks": plan.get("blocked_by_risks", []),
        "execution_constraints": plan.get("execution_constraints", []),
        "finance_refs": plan.get("finance_refs", {}),
        "risk_advisory_summary": normalize_risk_advisory_summary(plan.get("risk_advisory_summary", {})),
        "risk_advisory_refs": plan.get("risk_advisory_refs", {}),
        "milestones": plan.get("milestones", []),
    }


def normalize_risk_advisory_summary(summary: dict[str, Any]) -> dict[str, Any]:
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
        "source": summary.get("source", ""),
        "contains_full_risk_register": bool(summary.get("contains_full_risk_register", False)),
    }


def normalize_risk_register(register: dict[str, Any]) -> dict[str, Any]:
    return {
        "risk_register_id": register.get("risk_register_id", ""),
        "status": register.get("status", "unknown"),
        "readiness_gate_status": register.get("readiness_gate_status", "unknown"),
        "risks": register.get("risks", []),
        "top_risks": register.get("top_risks", []),
    }


def normalize_sector_intelligence(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "sector_intelligence_id": result.get("sector_intelligence_id", ""),
        "status": result.get("status", "needs_input"),
        "taxonomy_record": result.get("taxonomy_record", {}),
        "sector_criteria": result.get("sector_criteria", {"criteria": []}),
        "investment_signal_pack": result.get("investment_signal_pack", {"signals": []}),
        "sector_evidence_map": result.get("sector_evidence_map", {"criteria": [], "evidence_gaps": []}),
        "source_candidates": result.get("source_candidates", []),
        "external_fetch_enabled": bool(result.get("external_fetch_enabled", False)),
        "not_ready_reasons": result.get("not_ready_reasons", []),
    }


def normalize_evidence_coverage(coverage: dict[str, Any]) -> dict[str, Any]:
    return {
        "coverage_id": coverage.get("coverage_id", ""),
        "status": coverage.get("status", "needs_evidence"),
        "supported": coverage.get("supported", 0),
        "needs_evidence": coverage.get("needs_evidence", 0),
        "targets": coverage.get("targets", []),
        "gaps": coverage.get("gaps", []),
    }


def render_report_html(report: dict[str, Any], latest_review: dict[str, Any] | None = None, locale: str = "ar") -> str:
    """Render a concise customer report; engineering diagnostics remain server-side."""
    locale = normalize_locale(locale)
    direction = "rtl" if locale == "ar" else "ltr"
    align = "right" if locale == "ar" else "left"
    view = build_report_view(report, latest_review)
    summary = view["executive_summary"]
    kpi_rows = "".join(
        f"<tr><td>{escape(business_text(kpi.get('output_id'), locale))}</td>"
        f"<td>{escape(str(kpi.get('value') if kpi.get('value') is not None else '—'))}</td>"
        f"<td>{escape(unit_text(kpi.get('unit'), locale))}</td>"
        f"<td>{escape(status_text(kpi.get('status'), locale))}</td></tr>"
        for kpi in view["headline_kpis"]
    )
    gate_rows = "".join(
        f"<tr><td>{escape(business_text(row.get('label'), locale))}</td>"
        f"<td>{escape(status_text(row.get('status'), locale))}</td>"
        f"<td>{escape(', '.join(business_text(reason, locale) for reason in row.get('reasons') or []) or text('none', locale))}</td></tr>"
        for row in view["readiness_gates"].get("gates", [])
    )
    risk_rows = "".join(
        f"<tr><td>{escape(business_text(row.get('trigger'), locale))}</td>"
        f"<td>{escape(status_text(row.get('severity'), locale))}</td>"
        f"<td>{escape(safe_narrative(row.get('mitigation'), locale))}</td></tr>"
        for row in view["risk_register"].get("top_risks", [])
    )
    milestone_rows = "".join(
        f"<tr><td>{escape(business_text(row.get('phase_id'), locale))}</td>"
        f"<td>{escape(business_text(row.get('owner_role'), locale))}</td>"
        f"<td>{escape(str(row.get('estimated_duration_days') or '—'))}</td>"
        f"<td>{escape(', '.join(business_text(item, locale) for item in row.get('exit_criteria') or []) or text('none', locale))}</td></tr>"
        for row in view["execution_plan"].get("milestones", [])
    )
    evidence_register = view.get("evidence_register", {})
    source_records = {
        str(source.get("source_id") or ""): source
        for source in evidence_register.get("source_records", [])
        if isinstance(source, dict)
    }
    evidence_rows_list: list[str] = []
    supported_dataset_ids = {
        str(item["dataset_id"])
        for item in view.get("evidence_ledger", [])
        if isinstance(item, dict) and item.get("dataset_id") and item.get("can_support_target") is True
    }
    for dataset in evidence_register.get("datasets", []):
        if not isinstance(dataset, dict):
            continue
        if str(dataset.get("dataset_id") or "") not in supported_dataset_ids:
            continue
        source = source_records.get(str(dataset.get("source_id") or ""), {})
        source_url = str(source.get("url") or "")
        source_action = (
            f'<a href="{escape(source_url, quote=True)}" target="_blank" rel="noopener noreferrer">'
            f'{"فتح المصدر الرسمي" if locale == "ar" else "Open official source"}</a>'
            if source_url.startswith("https://")
            else ("الرابط غير متاح" if locale == "ar" else "Link unavailable")
        )
        evidence_rows_list.append(
            f"<tr><td>{escape(str(dataset.get('title') or ('دليل موثق' if locale == 'ar' else 'Documented evidence')))}</td>"
            f"<td>{escape(str(dataset.get('publisher') or source.get('publisher') or '—'))}</td>"
            f"<td>{escape(status_text(dataset.get('review_status') or dataset.get('human_review_decision'), locale))}</td>"
            f"<td>{source_action}</td>"
            f"<td>{escape(safe_narrative(dataset.get('attribution') or source.get('attribution') or '—', locale))}</td></tr>"
        )
    evidence_rows = "".join(evidence_rows_list) or (
        f'<tr><td colspan="5">{"لا توجد أدلة معتمدة مرتبطة بهذا التقرير بعد." if locale == "ar" else "No approved evidence is linked to this report yet."}</td></tr>'
    )
    labels = {
        "summary": ("الملخص التنفيذي", "Executive summary"),
        "decision": ("القرار", "Decision"),
        "why": ("لماذا؟", "Why?"),
        "metrics": ("المؤشرات الرئيسية", "Key metrics"),
        "value": ("القيمة", "Value"),
        "unit": ("الوحدة", "Unit"),
        "evidence": ("الأدلة المستخدمة", "Evidence used"),
        "publisher": ("الجهة الناشرة", "Publisher"),
        "review": ("حالة المراجعة", "Review status"),
        "source": ("المصدر", "Source"),
        "attribution": ("الإسناد", "Attribution"),
        "readiness": ("متطلبات الجاهزية", "Readiness requirements"),
        "risks": ("المخاطر وخطة المعالجة", "Risks and mitigation"),
        "risk": ("الخطر", "Risk"),
        "severity": ("الأهمية", "Severity"),
        "mitigation": ("الإجراء المقترح", "Recommended action"),
        "plan": ("خطة التنفيذ", "Execution plan"),
        "phase": ("المرحلة", "Phase"),
        "owner": ("المسؤول", "Owner"),
        "days": ("الأيام", "Days"),
        "done": ("معيار الإتمام", "Completion criterion"),
        "internal": ("التفاصيل الفنية وسجل التدقيق متاحة للمشرف فقط.", "Technical details and the audit trail are available to administrators only."),
    }
    def label(key: str) -> str:
        pair = labels[key]
        return pair[1] if locale == "en" else pair[0]
    return f"""<!doctype html>
<html lang="{locale}" dir="{direction}">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(text('report_title', locale))}</title>
<style>
:root{{--ink:#0f3328;--muted:#6b7d76;--line:#dce7e0;--green:#138a66;--soft:#f5f9f6}}
*{{box-sizing:border-box}}body{{font-family:Tahoma,Arial,sans-serif;margin:0;background:#f1f5f2;color:var(--ink);line-height:1.65}}
main{{max-width:1080px;margin:28px auto;background:white;border:1px solid var(--line);padding:38px 44px;box-shadow:0 12px 36px #12382a14}}
header{{padding:24px;border-radius:16px;background:linear-gradient(135deg,#0b3d2e,#138a66);color:white}}h1{{margin:0}}h2{{margin-top:30px}}
.notice{{margin-top:18px;padding:14px;border:1px solid var(--line);border-radius:12px;background:var(--soft)}}table{{width:100%;border-collapse:collapse;margin:12px 0 24px}}th,td{{border:1px solid var(--line);padding:9px;text-align:{align}}}th{{background:#edf7f2}}
@media(max-width:760px){{main{{margin:0;padding:18px}}table{{font-size:12px}}}}@media print{{body{{background:#fff}}main{{margin:0;box-shadow:none;border:0}}}}
</style></head><body><main>
<header><h1>{escape(text('report_title', locale))}</h1><p>{escape(status_text(view['review_status'], locale))}</p></header>
<div class="notice">{escape(text('notice', locale))}</div>
<h2>{escape(label('summary'))}</h2>
<table><tbody><tr><th>{escape(label('decision'))}</th><td>{escape(status_text(summary.get('verdict'), locale))}</td></tr>
<tr><th>{escape(label('why'))}</th><td>{escape(safe_narrative(summary.get('reason'), locale))}</td></tr></tbody></table>
<h2>{escape(label('metrics'))}</h2><table><thead><tr><th>{escape(text('requirement', locale))}</th><th>{escape(label('value'))}</th><th>{escape(label('unit'))}</th><th>{escape(text('status', locale))}</th></tr></thead><tbody>{kpi_rows}</tbody></table>
<h2>{escape(label('evidence'))}</h2><table><thead><tr><th>{escape(text('requirement', locale))}</th><th>{escape(label('publisher'))}</th><th>{escape(label('review'))}</th><th>{escape(label('source'))}</th><th>{escape(label('attribution'))}</th></tr></thead><tbody>{evidence_rows}</tbody></table>
<h2>{escape(label('readiness'))}</h2><table><thead><tr><th>{escape(text('requirement', locale))}</th><th>{escape(text('status', locale))}</th><th>{escape(text('reason', locale))}</th></tr></thead><tbody>{gate_rows}</tbody></table>
<h2>{escape(label('risks'))}</h2><table><thead><tr><th>{escape(label('risk'))}</th><th>{escape(label('severity'))}</th><th>{escape(label('mitigation'))}</th></tr></thead><tbody>{risk_rows}</tbody></table>
<h2>{escape(label('plan'))}</h2><table><thead><tr><th>{escape(label('phase'))}</th><th>{escape(label('owner'))}</th><th>{escape(label('days'))}</th><th>{escape(label('done'))}</th></tr></thead><tbody>{milestone_rows}</tbody></table>
<footer>{escape(label('internal'))}</footer>
</main></body></html>"""
