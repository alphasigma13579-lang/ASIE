from __future__ import annotations

from html import escape
from typing import Any

from backend.snapshot_assembly import canonical_hash
from backend.funder_report import build_funder_report_projection, render_funder_report_html


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


def render_report_html(report: dict[str, Any], latest_review: dict[str, Any] | None = None) -> str:
    view = build_report_view(report, latest_review)
    kpi_rows = "".join(
        f"<tr><td>{escape(kpi['output_id'])}</td><td>{escape(str(kpi['value']))}</td>"
        f"<td>{escape(kpi['unit'])}</td><td>{escape(kpi['algorithm_id'])}</td></tr>"
        for kpi in view["headline_kpis"]
    )
    scenario_rows = "".join(
        f"<tr><td>{escape(row['scenario_id'])}</td><td>{row['npv']}</td>"
        f"<td>{row['monthly_profit']}</td><td>{escape(str(row['payback_months']))}</td></tr>"
        for row in view["scenario_table"]
    )
    assumption_rows = "".join(
        f"<tr><td>{escape(row['assumption_id'])}</td><td>{escape(row['label'])}</td>"
        f"<td>{escape(str(row['value']))}</td><td>{escape(row['review_status'])}</td></tr>"
        for row in view["assumption_book"]
    )
    source_rows = "".join(
        f"<tr><td>{escape(row['source_id'])}</td><td>{escape(row['publisher'])}</td>"
        f"<td>{escape(row['state'])}</td><td>{escape(row.get('reviewer_decision') or '')}</td></tr>"
        for group in ["enabled_sources", "candidate_sources", "reference_only", "blocked_sources"]
        for row in view["source_governance"].get(group, [])
    )
    operating_model = view.get("operating_model") or {}
    capex = view.get("capex_breakdown") or {}
    opex = view.get("opex_breakdown") or {}
    debt = view.get("debt_service_profile") or {}
    operating_rows = "".join(
        f"<tr><td>{escape(label)}</td><td>{escape(str(value))}</td></tr>"
        for label, value in [
            ("مصدر الوحدات", operating_model.get("unit_source", "")),
            ("الوحدات الشهرية", operating_model.get("monthly_units", "")),
            ("نسبة الاستخدام", operating_model.get("utilization_rate", "")),
            ("CAPEX الإجمالي", capex.get("total_capex", "")),
            ("OPEX الشهري", opex.get("total_monthly_opex", "")),
            ("الإهلاك الشهري", capex.get("depreciation_monthly", "")),
            ("دفعة الدين الشهرية", debt.get("monthly_payment", "")),
            ("DSCR", debt.get("dscr", "")),
            ("حالة خدمة الدين", debt.get("status", "")),
        ]
    )
    dataset_rows = "".join(
        f"<tr><td>{escape(row['dataset_id'])}</td><td>{escape(row['title'])}</td>"
        f"<td>{escape(row['review_status'])}</td><td>{escape(str(row.get('notes', {}).get('quality_review', {}).get('status', 'unknown')))}</td>"
        f"<td>{escape(str(row.get('row_count') or 0))}</td></tr>"
        for row in view["evidence_register"].get("datasets", [])
    )
    gate_rows = "".join(
        f"<tr><td>{escape(row['dataset_id'])}</td><td>{escape(row['status'])}</td>"
        f"<td>{escape(', '.join(row.get('reasons') or []))}</td></tr>"
        for row in view["evidence_register"].get("quality_gates", [])
    )
    evidence_rows = "".join(
        f"<tr><td>{escape(row.get('target_id') or row.get('assumption_id', ''))}</td><td>{escape(row['dataset_id'])}</td>"
        f"<td>{escape(row.get('transformation_id') or '')}</td><td>{escape(row['evidence_ref'])}</td>"
        f"<td>{escape(row['human_review_decision'])}</td></tr>"
        for row in view["evidence_register"].get("evidence_links", [])
    )
    ledger_rows = "".join(
        f"<tr><td>{escape(row.get('target_type', ''))}:{escape(row.get('target_id', ''))}</td>"
        f"<td>{escape(row.get('data_quality_status', ''))}</td>"
        f"<td>{escape(row.get('transformation_quality_status', ''))}</td>"
        f"<td>{escape(str(row.get('evidence_confidence_score', '')))}</td>"
        f"<td>{escape(row.get('evidence_confidence_status', ''))}</td></tr>"
        for row in view.get("evidence_ledger", [])
    )
    transformation_rows = "".join(
        f"<tr><td>{escape(row.get('transformation_id', ''))}</td><td>{escape(row.get('operation_type', ''))}</td>"
        f"<td>{escape(', '.join(row.get('input_columns') or []))}</td><td>{escape(str(row.get('output_value') or ''))}</td>"
        f"<td>{escape(row.get('review_status', ''))}</td></tr>"
        for row in view["evidence_register"].get("transformations", [])
    )
    lineage_rows = "".join(
        f"<tr><td>{escape(row.get('dataset_id', ''))}</td><td>{escape(row.get('transformation_id', ''))}</td>"
        f"<td>{escape(row.get('target_type', ''))}:{escape(row.get('target_id', ''))}</td>"
        f"<td>{escape(row.get('review_status', ''))}</td></tr>"
        for row in view.get("transformation_lineage", [])
    )
    gate_rows_html = "".join(
        f"<tr><td>{escape(row['label'])}</td><td>{escape(row['status'])}</td>"
        f"<td>{escape(', '.join(row.get('reasons') or []))}</td></tr>"
        for row in view["readiness_gates"].get("gates", [])
    )
    milestone_rows = "".join(
        f"<tr><td>{escape(row['phase_id'])}</td><td>{escape(row['owner_role'])}</td>"
        f"<td>{escape(str(row['estimated_duration_days']))}</td><td>{escape(', '.join(row.get('dependencies') or []))}</td></tr>"
        for row in view["execution_plan"].get("milestones", [])
    )
    risk_rows = "".join(
        f"<tr><td>{escape(row['risk_id'])}</td><td>{escape(row['severity'])}</td>"
        f"<td>{escape(row['trigger'])}</td><td>{escape(row['mitigation'])}</td></tr>"
        for row in view["risk_register"].get("top_risks", [])
    )
    sector = view["sector_intelligence"]
    taxonomy = sector.get("taxonomy_record") or {}
    sector_rows = "".join(
        f"<tr><td>{escape(row.get('label', ''))}</td><td>{escape(row.get('sector_value', ''))}</td>"
        f"<td>{escape(row.get('evidence_status', ''))}</td></tr>"
        for row in sector.get("sector_criteria", {}).get("criteria", [])
    )
    signal_rows = "".join(
        f"<tr><td>{escape(row.get('label', ''))}</td><td>{escape(row.get('value', ''))}</td>"
        f"<td>{escape(row.get('evidence_status', ''))}</td></tr>"
        for row in sector.get("investment_signal_pack", {}).get("signals", [])
    )
    coverage = view.get("evidence_coverage", {})
    coverage_rows = "".join(
        f"<tr><td>{escape(row.get('target_type', ''))}</td><td>{escape(row.get('label', ''))}</td>"
        f"<td>{escape(row.get('coverage_status', ''))}</td></tr>"
        for row in coverage.get("targets", [])[:20]
    )
    pack = view["decision_pack_summary"]
    review_row = (
        f"<tr><td>حالة المراجعة</td><td>{escape(view['review_status'])}</td></tr>"
        f"<tr><td>توصية الحزمة</td><td>{escape(pack['recommendation'])}</td></tr>"
        f"<tr><td>حالة الجاهزية</td><td>{escape(pack['readiness_status'])}</td></tr>"
        f"<tr><td>عدد المخاطر الأعلى</td><td>{escape(str(pack['top_risk_count']))}</td></tr>"
        f"<tr><td>حالة التنفيذ</td><td>{escape(pack['execution_status'])}</td></tr>"
    )
    acceptance_rows = "".join(
        f"<tr><td>{escape(row['test_id'])}</td><td>{escape(row['status'])}</td>"
        f"<td>{escape(row['evidence'])}</td></tr>"
        for row in view.get("acceptance", {}).get("tests", [])
    )
    return f"""<!doctype html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="utf-8" />
  <title>{escape(view['title'])}</title>
  <style>
    body {{ font-family: Tahoma, Arial, sans-serif; margin: 32px; color: #17201b; }}
    h1, h2 {{ margin-bottom: 8px; }}
    .meta {{ color: #53645a; margin-bottom: 24px; }}
    table {{ width: 100%; border-collapse: collapse; margin: 12px 0 24px; }}
    th, td {{ border: 1px solid #dfe5e1; padding: 8px; text-align: right; }}
    th {{ background: #f4f6f4; }}
    .verdict {{ padding: 12px; background: #f8fbec; border: 1px solid #d8e6a6; }}
  </style>
</head>
<body>
  <h1>{escape(view['title'])}</h1>
  <p class="meta">Snapshot {escape(view['snapshot_id'])} · Run {escape(view['run_id'])}</p>
  <section class="verdict">
    <h2>الملخص التنفيذي</h2>
    <p><strong>{escape(view['executive_summary']['verdict'])}</strong></p>
    <p>{escape(view['executive_summary']['reason'])}</p>
  </section>
  <h2>المؤشرات</h2>
  <table><thead><tr><th>المؤشر</th><th>القيمة</th><th>الوحدة</th><th>الخوارزمية</th></tr></thead><tbody>{kpi_rows}</tbody></table>
  <h2>السيناريوهات</h2>
  <table><thead><tr><th>السيناريو</th><th>NPV</th><th>الربح الشهري</th><th>الاسترداد</th></tr></thead><tbody>{scenario_rows}</tbody></table>
  <h2>نموذج التشغيل والتمويل</h2>
  <table><thead><tr><th>البند</th><th>القيمة</th></tr></thead><tbody>{operating_rows}</tbody></table>
  <h2>القطاع ومؤشرات الاستثمار</h2>
  <p>{escape(taxonomy.get('primary_sector_ar') or taxonomy.get('primary_sector') or 'غير مصنف')}</p>
  <table><thead><tr><th>المعيار</th><th>قيمة القطاع</th><th>حالة الدليل</th></tr></thead><tbody>{sector_rows}</tbody></table>
  <table><thead><tr><th>الإشارة</th><th>القيمة</th><th>حالة الدليل</th></tr></thead><tbody>{signal_rows}</tbody></table>
  <h2>دفتر الافتراضات</h2>
  <table><thead><tr><th>المعرف</th><th>الافتراض</th><th>القيمة</th><th>المراجعة</th></tr></thead><tbody>{assumption_rows}</tbody></table>
  <h2>سجل المصادر</h2>
  <table><thead><tr><th>المصدر</th><th>الناشر</th><th>الحالة</th><th>قرار المراجع</th></tr></thead><tbody>{source_rows}</tbody></table>
  <h2>سجل البيانات والأدلة</h2>
  <table><thead><tr><th>Dataset</th><th>العنوان</th><th>المراجعة</th><th>جودة البيانات</th><th>الصفوف</th></tr></thead><tbody>{dataset_rows}</tbody></table>
  <table><thead><tr><th>نوع الهدف</th><th>الهدف</th><th>تغطية الدليل</th></tr></thead><tbody>{coverage_rows}</tbody></table>
  <table><thead><tr><th>الهدف</th><th>جودة البيانات</th><th>جودة التحويل</th><th>درجة الثقة</th><th>حالة الثقة</th></tr></thead><tbody>{ledger_rows}</tbody></table>
  <table><thead><tr><th>Dataset</th><th>بوابة الجودة</th><th>الأسباب</th></tr></thead><tbody>{gate_rows}</tbody></table>
  <table><thead><tr><th>الهدف</th><th>Dataset</th><th>Transformation</th><th>Evidence Ref</th><th>قرار المراجع</th></tr></thead><tbody>{evidence_rows}</tbody></table>
  <h2>سجل التحويلات</h2>
  <table><thead><tr><th>Transformation</th><th>العملية</th><th>الأعمدة</th><th>الناتج</th><th>المراجعة</th></tr></thead><tbody>{transformation_rows}</tbody></table>
  <table><thead><tr><th>Dataset</th><th>Transformation</th><th>Target</th><th>حالة التحويل</th></tr></thead><tbody>{lineage_rows}</tbody></table>
  <h2>بوابات الجاهزية</h2>
  <table><thead><tr><th>البوابة</th><th>الحالة</th><th>الأسباب</th></tr></thead><tbody>{gate_rows_html}</tbody></table>
  <h2>خطة التنفيذ</h2>
  <table><thead><tr><th>المرحلة</th><th>المالك</th><th>الأيام</th><th>الاعتماديات</th></tr></thead><tbody>{milestone_rows}</tbody></table>
  <h2>أعلى المخاطر</h2>
  <table><thead><tr><th>الخطر</th><th>الشدة</th><th>المحفز</th><th>المعالجة</th></tr></thead><tbody>{risk_rows}</tbody></table>
  <h2>حزمة القرار والمراجعة</h2>
  <table><thead><tr><th>البند</th><th>القيمة</th></tr></thead><tbody>{review_row}</tbody></table>
  <h2>اختبارات القبول r10/r11</h2>
  <table><thead><tr><th>الاختبار</th><th>الحالة</th><th>الدليل</th></tr></thead><tbody>{acceptance_rows}</tbody></table>
  <h2>التدقيق</h2>
  <p>{escape(view['audit']['owner_path'])}</p>
</body>
</html>"""
