"""Snapshot-only projections for the funder-ready report pack.

This module deliberately contains no financial formulas. It only maps persisted
Snapshot values into the reporting contract approved by FR-0 and marks missing
accounting or evidence inputs explicitly.
"""

from __future__ import annotations

from html import escape
from typing import Any

from backend.snapshot_assembly import canonical_hash
from backend.funding_readiness import evaluate_funding_readiness


FUNDER_REPORT_CONTRACT = "funder.report.projection.v1"
BASE_PROFILE_ID = "BASE-FUNDING-V1"


def _section(section_id: str, title: str, source_refs: list[str], payload: dict[str, Any], *, status: str = "ready") -> dict[str, Any]:
    return {
        "section_id": section_id,
        "title": title,
        "status": status,
        "source_refs": source_refs,
        "payload": payload,
    }


def _readiness_status(overview: dict[str, Any]) -> str:
    if (overview.get("project") or {}).get("data_badge") == "DEMO_DATA":
        return "DRAFT_INTERNAL"
    finance = overview.get("finance") or {}
    if finance.get("status") != "ready":
        return "DRAFT_INTERNAL"
    if any(row.get("severity") == "critical" for row in overview.get("blockers", [])):
        return "DRAFT_INTERNAL"
    if overview.get("blockers"):
        return "DECISION_READY"
    return "FUNDING_BASE_READY"


def _financial_statements(finance: dict[str, Any]) -> dict[str, Any]:
    baseline = finance.get("baseline") or {}
    if not baseline:
        return {
            "status": "not_ready",
            "income_statement": {"status": "not_ready", "years": []},
            "cashflow": {"status": "not_ready", "years": []},
            "balance_sheet": {"status": "not_ready", "reason": "finance_result_set is not ready"},
            "gaps": ["finance_result_set"],
        }

    def annual(key: str) -> Any:
        value = baseline.get(key)
        return None if value is None else value * 12

    opex = baseline.get("opex_breakdown") or {}
    capex = baseline.get("capex_breakdown") or {}
    debt = baseline.get("debt_service_profile") or {}
    income_years = []
    cashflow_years = []
    for year in range(1, 6):
        income_years.append(
            {
                "year": year,
                "revenue": annual("revenue"),
                "cost_of_goods_sold": annual("variable_total"),
                "gross_profit": annual("gross_profit"),
                "operating_expenses": (opex.get("total_monthly_opex") or 0) * 12,
                "ebitda": annual("ebitda"),
                "depreciation": (capex.get("depreciation_monthly") or 0) * 12,
                "ebit": annual("ebit"),
                "annual_debt_service": debt.get("annual_debt_service"),
                "net_operating_cashflow": annual("net_operating_cashflow"),
            }
        )
        cashflow_years.append(
            {
                "year": year,
                "operating_cashflow": annual("net_operating_cashflow"),
                "capital_expenditure": capex.get("total_capex") if year == 1 else 0,
                "financing_need": baseline.get("funding_need_after_equity") if year == 1 else 0,
                "net_cashflow": annual("annual_cashflow"),
            }
        )
    return {
        "status": "partial",
        "income_statement": {
            "status": "projected",
            "period_basis": "annual_from_snapshot_monthly_run_rate",
            "years": income_years,
            "gaps": ["tax", "interest_expense", "full_net_income"] if not baseline.get("net_income") else [],
        },
        "cashflow": {
            "status": "projected",
            "period_basis": "annual_from_snapshot_monthly_run_rate",
            "years": cashflow_years,
            "gaps": ["opening_cash", "monthly_year_1_detail", "working_capital_movements"],
        },
        "balance_sheet": {
            "status": "not_ready",
            "reason": "accounting position inputs are not part of the current finance result set",
            "gaps": ["current_assets", "fixed_assets_net", "current_liabilities", "long_term_liabilities", "equity_reconciliation"],
        },
        "gaps": ["balance_sheet", "monthly_year_1_cashflow"],
    }


def _input_traceability(overview: dict[str, Any]) -> dict[str, Any]:
    """Expose the persisted input-to-assumption chain without recalculation."""
    rows = overview.get("assumption_book") or []
    items = [
        {
            "input_key": row.get("input_key"),
            "assumption_id": row.get("assumption_id"),
            "source_type": row.get("source_type"),
            "review_status": row.get("review_status"),
            "confidence": row.get("confidence"),
        }
        for row in rows
    ]
    return {
        "contract_id": "input.traceability.v1",
        "project_id": (overview.get("project") or {}).get("project_id", ""),
        "snapshot_id": (overview.get("snapshot") or {}).get("snapshot_id", ""),
        "items": items,
        "unreviewed_count": sum(1 for item in items if item.get("review_status") != "approved"),
    }


def build_funder_report_projection(overview: dict[str, Any], profile_id: str = BASE_PROFILE_ID) -> dict[str, Any]:
    """Map an assembled overview into the FR-0 funder report contract."""
    project = overview.get("project") or {}
    finance = overview.get("finance") or {}
    baseline = finance.get("baseline") or {}
    snapshot_id = (overview.get("snapshot") or {}).get("snapshot_id", "")
    source = [f"snapshot:{snapshot_id}"] if snapshot_id else []
    financial_statements = _financial_statements(finance)
    readiness_status = _readiness_status(overview)
    inputs = project.get("inputs") or {}
    projection = {
        "contract_id": FUNDER_REPORT_CONTRACT,
        "contract_version": "1.0.0",
        "profile_id": profile_id,
        "profile_status": "base_profile_only",
        "snapshot_id": snapshot_id,
        "run_id": (overview.get("run") or {}).get("run_id", ""),
        "project_id": project.get("project_id", ""),
        "data_mode": "demo_simulated_external" if project.get("data_badge") == "DEMO_DATA" else "user_verified",
        "display_badge": "DEMO / LOCAL ONLY" if project.get("data_badge") == "DEMO_DATA" else "USER VERIFIED",
        "production_admission": "blocked" if project.get("data_badge") == "DEMO_DATA" else "local_only",
        "input_traceability": _input_traceability(overview),
        "readiness_status": readiness_status,
        "sections": [
            _section("01-general-information", "المعلومات العامة", source, {"project": project}),
            _section("02-executive-summary", "الملخص التنفيذي", source, {"decision": overview.get("decision", {}), "kpis": overview.get("kpis", [])}),
            _section("03-products-services", "المنتجات والخدمات", source, {"activity_description": (project.get("inputs") or {}).get("activity_description", "")}),
            _section("04-technology-impact", "أثر التقنية", source, {"status": "needs_input", "reason": "technology impact evidence is not yet modeled"}, status="needs_input"),
            _section("05-state-economy", "اقتصاد الدولة والسياق", ["sector_intelligence"] + source, {"sector_intelligence": overview.get("sector_intelligence", {})}),
            _section("06-product-market", "سوق المنتج أو الخدمة", ["sector_intelligence", "evidence_ledger"] + source, {"sector_intelligence": overview.get("sector_intelligence", {}), "evidence_coverage": overview.get("evidence_coverage", {})}),
            _section("07-marketing-strategy", "استراتيجية التسويق", source, {"status": "needs_input", "reason": "marketing plan inputs are not yet modeled"}, status="needs_input"),
            _section("08-activity-human-resources", "النشاط والموارد البشرية", ["execution_plan"] + source, {"execution_plan": overview.get("execution_plan", {})}),
            _section("09-timeline", "الجدول الزمني", ["execution_plan"] + source, {"milestones": (overview.get("execution_plan") or {}).get("milestones", [])}),
            _section("10-technical", "القسم الفني", ["finance", "execution_plan"] + source, {"operating_model": finance.get("operating_model"), "capex": finance.get("capex_breakdown")}),
            _section("11-business-model", "نموذج الأعمال", source, {"status": "needs_input", "reason": "business model canvas is not yet a persisted projection"}, status="needs_input"),
            _section("12-general-risks", "عوامل المخاطر العامة", ["risk_register"] + source, {"risk_register": overview.get("risk_register", {})}),
            _section("13-capability", "القدرة التنفيذية", ["readiness", "execution_plan"] + source, {"readiness": overview.get("readiness", {}), "execution_plan": overview.get("execution_plan", {})}),
            _section("14-financial-expectations", "التوقعات المالية", ["finance"] + source, {"statements": financial_statements, "baseline": baseline}),
            _section("15-capital-requirements", "متطلبات رأس المال والاستراتيجية", ["finance"] + source, {"uses": {"initial_investment": baseline.get("initial_investment"), "capex": (finance.get("capex_breakdown") or {}).get("total_capex"), "working_capital": baseline.get("working_capital_need")}, "sources": {"equity": inputs.get("equity_contribution"), "external_funding_need": baseline.get("funding_need_after_equity"), "debt": (finance.get("debt_service_profile") or {}).get("debt_amount")}}),
            _section("16-results-recommendations", "النتائج والتوصيات", ["decision", "readiness_gates"] + source, {"decision": overview.get("decision", {}), "readiness_gates": overview.get("readiness_gates", {}), "blockers": overview.get("blockers", [])}),
        ],
        "evidence": {
            "assumption_refs": finance.get("assumption_refs", []),
            "evidence_ledger": overview.get("evidence_ledger", []),
            "evidence_register_id": (overview.get("evidence_register") or {}).get("evidence_register_id", ""),
            "transformation_lineage": overview.get("transformation_lineage", []),
        },
        "gaps": [
            *(["demo_data_not_admitted_to_production"] if project.get("data_badge") == "DEMO_DATA" else []),
            "technology_impact",
            "marketing_strategy",
            "business_model_canvas",
            *financial_statements.get("gaps", []),
        ],
    }
    projection["profile_readiness"] = evaluate_funding_readiness(projection)
    projection["projection_hash"] = canonical_hash(projection)
    return projection


def render_funder_report_html(projection: dict[str, Any]) -> str:
    """Render the read-only Arabic review view for a funder projection."""
    sections = projection.get("sections", [])
    section_cards = "".join(
        f"<article class='section-card status-{escape(str(section.get('status', 'unknown')))}'>"
        f"<div class='section-number'>{escape(section.get('section_id', '').split('-')[0])}</div>"
        f"<div><h3>{escape(section.get('title', ''))}</h3>"
        f"<span class='status'>{escape(section.get('status', 'unknown'))}</span></div></article>"
        for section in sections
    )
    financial = next((row for row in sections if row.get("section_id") == "14-financial-expectations"), {})
    statements = (financial.get("payload") or {}).get("statements") or {}
    income_years = ((statements.get("income_statement") or {}).get("years") or [])
    income_rows = "".join(
        "<tr>" + "".join(f"<td>{escape(str(row.get(key, '—')))}</td>" for key in ["year", "revenue", "gross_profit", "ebitda", "ebit", "net_operating_cashflow"]) + "</tr>"
        for row in income_years
    )
    gaps = "".join(f"<li>{escape(str(gap))}</li>" for gap in projection.get("gaps", [])) or "<li>لا توجد فجوات مسجلة</li>"
    profile = projection.get("profile_readiness") or {}
    profile_rows = "".join(
        f"<tr><td>{escape(str(row.get('label', '')))}</td><td>{escape(str(row.get('status', '')))}</td><td>{escape(str(row.get('reason', '')) or '—')}</td></tr>"
        for row in profile.get("checks", [])
    ) or "<tr><td colspan='3'>لا يوجد ملف تحقق</td></tr>"
    return f"""<!doctype html>
<html lang='ar' dir='rtl'>
<head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>حزمة التقرير التمويلي — {escape(str(projection.get('project_id', '')))}</title>
<style>
:root {{ --ink:#172554; --muted:#64748b; --line:#dbe4ef; --blue:#2563eb; --soft:#f8fafc; --warn:#fff7ed; }}
* {{ box-sizing:border-box; }} body {{ margin:0; background:#eef3f8; color:#172033; font-family:Tahoma,Arial,sans-serif; line-height:1.65; }}
.page {{ max-width:1120px; margin:28px auto; background:#fff; border:1px solid var(--line); box-shadow:0 12px 36px #1e3a8a18; }}
.hero {{ padding:38px 44px; color:#fff; background:linear-gradient(135deg,#172554,#1d4ed8); }} h1 {{ margin:0 0 8px; font-size:32px; }} h2 {{ margin:28px 0 12px; color:var(--ink); }} h3 {{ margin:0; color:var(--ink); font-size:17px; }}
.meta {{ color:#dbeafe; font-size:13px; }} .badge {{ display:inline-block; padding:6px 12px; border-radius:999px; background:#dbeafe; color:#1e3a8a; font-weight:700; }}
.content {{ padding:30px 44px 46px; }} .notice {{ padding:16px; background:var(--warn); border:1px solid #fed7aa; border-radius:12px; color:#7c2d12; }}
.section-grid {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:12px; }} .section-card {{ display:flex; gap:12px; align-items:center; min-height:76px; padding:14px; border:1px solid var(--line); border-radius:12px; background:var(--soft); }}
.section-number {{ width:38px; height:38px; display:grid; place-items:center; border-radius:10px; background:#dbeafe; color:var(--blue); font-weight:700; }} .status {{ color:var(--muted); font-size:12px; }}
table {{ width:100%; border-collapse:collapse; margin:12px 0 24px; font-size:13px; }} th,td {{ border:1px solid var(--line); padding:9px; text-align:right; }} th {{ background:#eff6ff; color:var(--ink); }}
ul {{ margin-top:8px; }} footer {{ padding:18px 44px; border-top:1px solid var(--line); color:var(--muted); font-size:12px; }}
@media(max-width:760px) {{ .hero,.content,footer {{ padding-left:18px; padding-right:18px; }} .section-grid {{ grid-template-columns:1fr; }} h1 {{ font-size:25px; }} }}
@media print {{ body {{ background:#fff; }} .page {{ margin:0; border:0; box-shadow:none; max-width:none; }} }}
</style></head>
<body><main class='page'>
<header class='hero'><h1>حزمة التقرير الجاهز للتمويل</h1><div class='meta'>Snapshot: {escape(str(projection.get('snapshot_id', '')))} · Run: {escape(str(projection.get('run_id', '')))} · Profile: {escape(str(projection.get('profile_id', '')))}</div><p><span class='badge'>{escape(str(projection.get('readiness_status', 'unknown')))}</span></p></header>
<section class='content'>
<div class='notice'>هذه معاينة قراءة مبنية على Snapshot محفوظ. لا يعيد العرض الحساب، ولا يمثل قبولاً أو ضماناً من أي جهة تمويل.</div>
<h2>ملف الجاهزية التمويلية</h2><p><span class='badge'>{escape(str(profile.get('profile_id', '')))} · {escape(str(profile.get('status', 'unknown')))}</span></p>
<table><thead><tr><th>المتطلب</th><th>الحالة</th><th>السبب أو الفجوة</th></tr></thead><tbody>{profile_rows}</tbody></table>
<h2>هيكل الدراسة</h2><div class='section-grid'>{section_cards}</div>
<h2>التوقعات المالية</h2>
<table><thead><tr><th>السنة</th><th>الإيرادات</th><th>إجمالي الربح</th><th>EBITDA</th><th>EBIT</th><th>التدفق التشغيلي</th></tr></thead><tbody>{income_rows or '<tr><td colspan="6">لا توجد توقعات مالية جاهزة</td></tr>'}</tbody></table>
<h2>الفجوات قبل الإصدار التمويلي</h2><ul>{gaps}</ul>
</section><footer>عقد التقرير: {escape(str(projection.get('contract_id', '')))} · Hash الإسقاط: {escape(str(projection.get('projection_hash', '')))}</footer>
</main></body></html>"""
