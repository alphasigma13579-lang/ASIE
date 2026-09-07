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
    "ebitda": ("الربح قبل الفوائد والضرائب والإهلاك والاستهلاك", "Earnings before interest, tax, depreciation, and amortisation"),
    "ebit": ("الربح قبل الفوائد والضرائب", "Earnings before interest and tax"),
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
    "draft_review": ("بانتظار المراجعة", "Awaiting review"),
    "blocked": ("متوقف حتى استكمال المتطلبات", "Blocked until requirements are completed"),
    "high": ("مرتفع", "High"),
    "medium": ("متوسط", "Medium"),
    "low": ("منخفض", "Low"),
    "warning": ("يحتاج انتباهًا", "Needs attention"),
    "ready_with_warnings": ("جاهز مع ملاحظات", "Ready with notes"),
    "completed": ("مكتمل", "Completed"),
    "insufficient_data": ("البيانات غير كافية", "Insufficient data"),
    "preliminary_only": ("تقييم أولي", "Preliminary assessment"),
    "revise_and_reassess": ("راجع المدخلات وأعد التقييم", "Review inputs and reassess"),
    "blocked_not_ready": ("متوقف لمدخلات ناقصة", "Blocked by missing inputs"),
    "approved_local": ("معتمد داخليًا", "Internally approved"),
    "needs_changes": ("يحتاج تعديلات", "Changes required"),
    "rejected_local": ("مرفوض داخليًا", "Internally rejected"),
    "closed": ("مغلق", "Closed"),
    "open": ("مفتوح", "Open"),
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
    "complete_finance_inputs": ("أكمل المدخلات المالية المطلوبة.", "Complete the required financial inputs."),
    "increase_equity_or_reduce_capex_opex_before_launch": ("زد التمويل الذاتي أو خفّض تكاليف التأسيس والتشغيل قبل البدء.", "Increase owner funding or reduce setup and operating costs before launch."),
    "track_funding_gap_before_procurement": ("راقب فجوة التمويل قبل الالتزام بالمشتريات.", "Track the funding gap before committing to procurement."),
    "complete_interest_rate_and_loan_tenor": ("أكمل نسبة التمويل ومدة السداد.", "Complete the financing rate and repayment term."),
    "lower_debt_improve_ebitda_or_extend_tenor": ("خفّض الدين أو حسّن الربح التشغيلي أو مدّد مدة السداد.", "Lower debt, improve operating earnings, or extend the repayment term."),
    "monitor_debt_service_after_lender_terms_are_final": ("راقب التزامات السداد بعد اعتماد شروط جهة التمويل.", "Monitor repayment obligations after financing terms are finalized."),
    "validate_capacity_and_ramp_up_before_launch": ("تحقق من الطاقة التشغيلية وخطة التدرج قبل البدء.", "Validate operating capacity and the ramp-up plan before launch."),
    "keep_utilization_in_assumption_review": ("راجع افتراض نسبة التشغيل بانتظام.", "Keep the utilization assumption under review."),
    "complete_operating_cost_inputs": ("أكمل مدخلات تكاليف التشغيل.", "Complete the operating cost inputs."),
    "reduce_fixed_opex_or_increase_validated_revenue_capacity": ("خفّض تكاليف التشغيل الثابتة أو أثبت قدرة أعلى على تحقيق الإيراد.", "Reduce fixed operating costs or validate a higher revenue capacity."),
    "monitor_opex_during_stabilization": ("راقب تكاليف التشغيل خلال مرحلة الاستقرار.", "Monitor operating costs during stabilization."),
    "disable_external_fetch_and_re_review_source_policy": ("راجع إعدادات المصادر المعتمدة قبل المتابعة.", "Review approved-source settings before continuing."),
    "complete_human_review_for_exact_open_datasets": ("أكمل المراجعة البشرية لمصادر البيانات المفتوحة المحددة.", "Complete human review of the selected open datasets."),
    "keep_source_review_snapshots_current": ("حافظ على مراجعات المصادر محدثة.", "Keep source reviews current."),
    "fix_dataset_review_fields_or_remove_the_dataset_link": ("أكمل مراجعة المصدر أو افصل رابط الدليل غير المقبول.", "Complete the source review or remove the unsupported evidence link."),
    "link_approved_datasets_to_critical_assumptions": ("اربط المصادر المعتمدة بالافتراضات المؤثرة في القرار.", "Link approved sources to the assumptions that affect the decision."),
    "review_evidence_freshness_before_final_use": ("تحقق من حداثة الأدلة قبل الاعتماد النهائي.", "Review evidence freshness before final use."),
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
    "execution_readiness_index": ("جاهزية التنفيذ", "Execution readiness"),
    "commercial_acceptance_index": ("قابلية السوق", "Market acceptance"),
    "technical_robustness_index": ("متانة التشغيل", "Operational robustness"),
    "transition_readiness_index": ("جاهزية الانتقال", "Transition readiness"),
    "pressure_survival_index": ("القدرة على تحمل الضغوط", "Pressure resilience"),
    "financial_readiness": ("الجاهزية المالية", "Financial readiness"),
    "evidence_readiness": ("جاهزية الأدلة", "Evidence readiness"),
    "source_governance": ("اعتماد المصادر", "Source approval"),
    "launch_readiness": ("جاهزية بدء التشغيل", "Launch readiness"),
    "negative_npv": ("القيمة الحالية للمشروع سالبة", "The project's net present value is negative"),
    "non_positive_monthly_profit": ("الربح الشهري المتوقع غير موجب", "Expected monthly profit is not positive"),
    "no_enabled_open_data_source": ("لا يوجد مصدر سوق معتمد ومفعّل", "No approved market source is enabled"),
    "no_enabled_open_data_sources": ("لا توجد مصادر سوق معتمدة ومفعّلة", "No approved market sources are enabled"),
    "no_evidence_links": ("لا توجد أدلة مرتبطة بالافتراضات المهمة", "No evidence is linked to key assumptions"),
    "no_assumption_evidence_links": ("الافتراضات المهمة غير مرتبطة بأدلة", "Key assumptions are not linked to evidence"),
    "opex_above_60_percent_of_revenue": ("المصروفات التشغيلية مرتفعة مقارنة بالإيراد", "Operating costs are high relative to revenue"),
    "assumption_support_gap": ("نقص في الأدلة الداعمة", "Supporting evidence is missing"),
    "margin_pressure": ("ضغط على هامش الربح", "Profit margin pressure"),
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

_UNITS = {
    "sar": ("ر.س", "SAR"),
    "sar_month": ("ر.س شهريًا", "SAR/month"),
    "sar_year": ("ر.س سنويًا", "SAR/year"),
    "percent": ("٪", "%"),
    "percentage": ("٪", "%"),
    "probability": ("احتمال", "Probability"),
    "count": ("عدد", "Count"),
    "unit": ("وحدة", "Unit"),
    "units": ("وحدة", "Units"),
    "month": ("شهر", "Month"),
    "months": ("شهر", "Months"),
    "year": ("سنة", "Year"),
    "years": ("سنة", "Years"),
    "day": ("يوم", "Day"),
    "days": ("يوم", "Days"),
    "ratio": ("نسبة", "Ratio"),
}


_FORBIDDEN = re.compile(
    r"(?:\b(?:project|run|snapshot|profile|contract|review|projection|release|algorithm|engine|session|manifest|payload|hash)_id\b|"
    r"\b(?:not_ready|review_required|demo_or_user_input_only|blocked_not_ready|decision[_ ]pack|monte[_ ]carlo|finance[_ ]engine|runtime)\b|_{1,})",
    re.IGNORECASE,
)


def normalize_locale(value: Any) -> Locale:
    return "en" if str(value).lower() == "en" else "ar"


def _normalize_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9\u0600-\u06ff]+", "_", str(value or "").strip().lower()).strip("_")


def text(key: str, locale: Locale) -> str:
    pair = _TEXT[key]
    return pair[1] if normalize_locale(locale) == "en" else pair[0]


def status_text(value: Any, locale: Locale) -> str:
    key = _normalize_key(value)
    pair = _STATUS.get(key)
    return (pair[1] if normalize_locale(locale) == "en" else pair[0]) if pair else text("unknown_detail", locale)


def business_text(value: Any, locale: Locale) -> str:
    key = _normalize_key(value)
    pair = _BUSINESS.get(key)
    return (pair[1] if normalize_locale(locale) == "en" else pair[0]) if pair else status_text(value, locale)


def unit_text(value: Any, locale: Locale) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    key = _normalize_key(raw).replace("_per_", "_")
    pair = _UNITS.get(key)
    if pair:
        return pair[1] if normalize_locale(locale) == "en" else pair[0]
    return "Unit" if normalize_locale(locale) == "en" else "وحدة قياس"


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
