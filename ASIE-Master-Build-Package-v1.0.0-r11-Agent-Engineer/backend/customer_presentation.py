"""Customer-facing language and presentation helpers.

This module never mutates Snapshot or domain contracts. It only projects persisted
values into safe Arabic or English display text and fails closed for unknown
internal codes.
"""

from __future__ import annotations

import re
from typing import Any

Locale = str

_TEXT = {
    "report_title": ("تقرير جدوى المشروع", "Project feasibility report"),
    "report_status": ("حالة التقرير", "Report status"),
    "saved": ("محفوظ", "Saved"),
    "notice": (
        "هذا التقرير مبني على نتيجة تحليل محفوظة، ولا يعيد الحساب ولا يمثل قبولاً أو ضماناً من جهة تمويل.",
        "This report is based on a saved analysis result. It does not recalculate results or guarantee approval by a funder.",
    ),
    "readiness": ("جاهزية المشروع", "Project readiness"),
    "requirement": ("المتطلب", "Requirement"),
    "status": ("الحالة", "Status"),
    "reason": ("ما المطلوب؟", "What is required?"),
    "study_structure": ("أقسام الدراسة", "Study sections"),
    "financial_outlook": ("التوقعات المالية", "Financial outlook"),
    "year": ("السنة", "Year"),
    "revenue": ("الإيرادات", "Revenue"),
    "gross_profit": ("إجمالي الربح", "Gross profit"),
    "operating_profit": ("الربح التشغيلي", "Operating profit"),
    "operating_cashflow": ("التدفق التشغيلي", "Operating cash flow"),
    "missing_items": ("ما الذي يحتاج استكمالاً؟", "What still needs completion?"),
    "none": ("لا توجد نواقص مسجلة", "No missing items are recorded"),
    "no_financials": ("لا توجد توقعات مالية جاهزة", "No financial outlook is ready"),
    "no_checks": ("لا توجد متطلبات تحقق متاحة", "No verification requirements are available"),
    "unknown_detail": ("تفصيل يحتاج مراجعة قبل عرضه", "Detail requires review before display"),
    "no_explanation": ("لا يتوفر شرح واضح بعد", "No clear explanation is available yet"),
    "draft": ("مسودة غير مكتملة", "Incomplete draft"),
    "ready": ("جاهز للمراجعة", "Ready for review"),
}

_STATUS = {
    "ready": ("جاهز", "Ready"),
    "passed": ("مكتمل", "Passed"),
    "partial": ("مكتمل جزئياً", "Partially complete"),
    "projected": ("تقديري", "Projected"),
    "needs_input": ("يحتاج مدخلات", "Needs input"),
    "not_ready": ("غير جاهز", "Not ready"),
    "draft_internal": ("مسودة غير مكتملة", "Incomplete draft"),
    "decision_ready": ("جاهز لمراجعة القرار", "Ready for decision review"),
    "funding_base_ready": ("جاهز للمراجعة التمويلية الأولية", "Ready for initial funding review"),
    "approved": ("معتمد", "Approved"),
    "review_required": ("بانتظار المراجعة", "Awaiting review"),
    "blocked": ("متوقف حتى استكمال المتطلبات", "Blocked until requirements are completed"),
    "high": ("مرتفع", "High"),
    "medium": ("متوسط", "Medium"),
    "low": ("منخفض", "Low"),
}

_BUSINESS = {
    "technology_impact": ("أثر التقنية", "Technology impact"),
    "marketing_strategy": ("خطة التسويق", "Marketing plan"),
    "business_model_canvas": ("نموذج الأعمال", "Business model"),
    "balance_sheet": ("بيانات المركز المالي", "Financial position data"),
    "monthly_year_1_cashflow": ("التدفق النقدي الشهري للسنة الأولى", "Monthly first-year cash flow"),
    "finance_result_set": ("البيانات المالية الأساسية", "Core financial inputs"),
    "tax": ("الضرائب", "Tax"),
    "interest_expense": ("تكلفة التمويل", "Financing cost"),
    "full_net_income": ("صافي الربح الكامل", "Complete net income"),
    "opening_cash": ("الرصيد النقدي الافتتاحي", "Opening cash balance"),
    "working_capital_movements": ("حركة رأس المال العامل", "Working capital movements"),
    "current_assets": ("الأصول المتداولة", "Current assets"),
    "fixed_assets_net": ("صافي الأصول الثابتة", "Net fixed assets"),
    "current_liabilities": ("الالتزامات المتداولة", "Current liabilities"),
    "long_term_liabilities": ("الالتزامات طويلة الأجل", "Long-term liabilities"),
    "equity_reconciliation": ("تسوية حقوق الملكية", "Equity reconciliation"),
    "demo_data_not_admitted_to_production": ("استبدال البيانات التجريبية ببيانات مؤكدة", "Replace demo data with verified inputs"),
    "startup_cost": ("تكلفة التأسيس", "Setup cost"),
    "monthly_revenue": ("الإيراد الشهري", "Monthly revenue"),
    "monthly_profit": ("صافي الربح الشهري التقديري", "Estimated monthly net profit"),
    "break_even_units": ("وحدات التعادل", "Break-even units"),
    "funding_gap": ("فجوة التمويل", "Funding gap"),
    "working_capital_need": ("احتياج رأس المال العامل", "Working capital need"),
    "net_operating_cashflow": ("التدفق التشغيلي الصافي", "Net operating cash flow"),
    "funding_need_after_equity": ("احتياج التمويل بعد رأس مال المالك", "Funding need after owner capital"),
    "depreciation_monthly": ("الإهلاك الشهري", "Monthly depreciation"),
    "npv": ("صافي القيمة الحالية", "Net present value"),
    "irr": ("معدل العائد الداخلي", "Internal rate of return"),
    "payback_months": ("مدة الاسترداد", "Payback period"),
    "contribution_margin": ("هامش المساهمة", "Contribution margin"),
    "debt_service_monthly": ("قسط الدين الشهري", "Monthly debt payment"),
    "dscr": ("قدرة المشروع على تغطية أقساط الدين", "Debt payment coverage"),
    "setup": ("تحديد نطاق المشروع", "Define project scope"),
    "procurement": ("تأكيد المشتريات", "Confirm procurement"),
    "staffing": ("تجهيز فريق العمل", "Prepare the team"),
    "launch": ("بدء التشغيل", "Launch operations"),
    "stabilization": ("استقرار التشغيل", "Stabilize operations"),
    "project_manager": ("مدير المشروع", "Project manager"),
    "business_advisor": ("مستشار الأعمال", "Business advisor"),
    "analyst_coach": ("مستشار التحليل", "Analysis advisor"),
    "project_scope_signed": ("اعتماد نطاق المشروع", "Approve project scope"),
    "capex_items_confirmed": ("تأكيد بنود التأسيس", "Confirm setup items"),
    "staffing_plan_ready": ("اعتماد خطة الفريق", "Approve team plan"),
    "operating_capacity_ready": ("تأكيد القدرة التشغيلية", "Confirm operating capacity"),
    "first_month_kpis_reviewed": ("مراجعة نتائج الشهر الأول", "Review first-month results"),
}

_SECTIONS = {
    "01-general-information": ("المعلومات العامة", "General information"),
    "02-executive-summary": ("الملخص التنفيذي", "Executive summary"),
    "03-products-services": ("المنتجات والخدمات", "Products and services"),
    "04-technology-impact": ("أثر التقنية", "Technology impact"),
    "05-state-economy": ("السياق الاقتصادي", "Economic context"),
    "06-product-market": ("سوق المنتج أو الخدمة", "Product or service market"),
    "07-marketing-strategy": ("استراتيجية التسويق", "Marketing strategy"),
    "08-activity-human-resources": ("النشاط والموارد البشرية", "Operations and people"),
    "09-timeline": ("الجدول الزمني", "Timeline"),
    "10-technical": ("متطلبات التشغيل", "Operational requirements"),
    "11-business-model": ("نموذج الأعمال", "Business model"),
    "12-general-risks": ("المخاطر الرئيسية", "Key risks"),
    "13-capability": ("القدرة على التنفيذ", "Execution capability"),
    "14-financial-expectations": ("التوقعات المالية", "Financial outlook"),
    "15-capital-requirements": ("متطلبات رأس المال", "Capital requirements"),
    "16-results-recommendations": ("النتائج والتوصيات", "Results and recommendations"),
}

_FORBIDDEN = re.compile(
    r"(?:\b(?:project|run|snapshot|profile|contract|review|projection|release|algorithm|engine|session|manifest|payload|hash)_id\b|"
    r"\b(?:not_ready|review_required|demo_or_user_input_only|blocked_not_ready|decision[_ ]pack|monte[_ ]carlo)\b|_{1,})",
    re.IGNORECASE,
)


def normalize_locale(value: Any) -> Locale:
    return "en" if str(value).lower() == "en" else "ar"


def text(key: str, locale: Locale) -> str:
    pair = _TEXT[key]
    return pair[1] if normalize_locale(locale) == "en" else pair[0]


def status_text(value: Any, locale: Locale) -> str:
    key = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    pair = _STATUS.get(key)
    return (pair[1] if normalize_locale(locale) == "en" else pair[0]) if pair else text("unknown_detail", locale)


def business_text(value: Any, locale: Locale) -> str:
    key = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    pair = _BUSINESS.get(key)
    return (pair[1] if normalize_locale(locale) == "en" else pair[0]) if pair else status_text(value, locale)


def section_title(section: dict[str, Any], locale: Locale) -> str:
    pair = _SECTIONS.get(str(section.get("section_id", "")))
    if pair:
        return pair[1] if normalize_locale(locale) == "en" else pair[0]
    return text("unknown_detail", locale)


def safe_narrative(value: Any, locale: Locale) -> str:
    raw = str(value or "").strip()
    if not raw:
        return text("no_explanation", locale)
    has_arabic = bool(re.search(r"[\u0600-\u06ff]", raw))
    if not _FORBIDDEN.search(raw) and ((normalize_locale(locale) == "ar" and has_arabic) or (normalize_locale(locale) == "en" and not has_arabic)):
        return raw
    return business_text(raw, locale)
