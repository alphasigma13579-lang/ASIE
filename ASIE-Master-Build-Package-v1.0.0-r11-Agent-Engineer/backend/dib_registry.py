from __future__ import annotations

from copy import deepcopy
from typing import Any

COMMON_FINANCE_ITEMS: tuple[dict[str, Any], ...] = (
    {"input_key": "startup_cost", "label": "تكلفة التأسيس الأساسية", "category": "capex", "unit": "SAR", "required": True, "finance_key": "startup_cost"},
    {"input_key": "monthly_fixed_cost", "label": "التكاليف الشهرية الثابتة", "category": "opex", "unit": "SAR", "required": True, "finance_key": "monthly_fixed_cost"},
    {"input_key": "unit_price", "label": "سعر بيع الوحدة", "category": "revenue", "unit": "SAR", "required": True, "finance_key": "unit_price"},
    {"input_key": "variable_cost", "label": "التكلفة المتغيرة للوحدة", "category": "variable_cost", "unit": "SAR", "required": True, "finance_key": "variable_cost"},
    {"input_key": "monthly_units", "label": "الوحدات المباعة شهريًا", "category": "revenue", "unit": "count", "required": True, "finance_key": "monthly_units"},
    {"input_key": "annual_discount_rate", "label": "معدل الخصم السنوي", "category": "finance", "unit": "ratio", "required": True, "default_value": 0.10, "finance_key": "annual_discount_rate"},
    {"input_key": "working_capital_months", "label": "أشهر رأس المال العامل", "category": "finance", "unit": "months", "required": True, "default_value": 2, "finance_key": "working_capital_months"},
)

TEMPLATES: dict[str, dict[str, Any]] = {
    "template.food_service.shawarma.v1": {
        "template_id": "template.food_service.shawarma.v1",
        "label_ar": "محل شاورما / مطعم خدمة سريعة",
        "match_terms": ("شاورما", "shawarma", "مطعم", "restaurant", "وجبات", "food"),
        "items": (
            *COMMON_FINANCE_ITEMS,
            {"input_key": "equipment_shawarma_grill", "label": "شواية شاورما تجارية", "category": "capex_equipment", "unit": "SAR", "required": True, "finance_key": "capex_equipment"},
            {"input_key": "equipment_refrigeration", "label": "تبريد وثلاجات حفظ", "category": "capex_equipment", "unit": "SAR", "required": True, "finance_key": "capex_equipment"},
            {"input_key": "equipment_prep", "label": "معدات التحضير والتقطيع", "category": "capex_equipment", "unit": "SAR", "required": True, "finance_key": "capex_equipment"},
            {"input_key": "equipment_pos", "label": "نظام نقاط البيع", "category": "capex_equipment", "unit": "SAR", "required": False, "finance_key": "capex_equipment"},
            {"input_key": "capex_fitout", "label": "تجهيز وديكور المحل", "category": "capex", "unit": "SAR", "required": True, "finance_key": "capex_fitout"},
            {"input_key": "capex_licenses_local", "label": "التراخيص والرسوم المحلية", "category": "capex", "unit": "SAR", "required": True, "finance_key": "capex_licenses_local"},
            {"input_key": "rent_monthly", "label": "إيجار الموقع شهريًا", "category": "opex", "unit": "SAR", "required": True, "finance_key": "rent_monthly"},
            {"input_key": "payroll_monthly", "label": "الرواتب الشهرية", "category": "opex", "unit": "SAR", "required": True, "finance_key": "payroll_monthly"},
            {"input_key": "utilities_monthly", "label": "الكهرباء والمياه والغاز", "category": "opex", "unit": "SAR", "required": True, "finance_key": "utilities_monthly"},
            {"input_key": "maintenance_monthly", "label": "الصيانة والنظافة", "category": "opex", "unit": "SAR", "required": False, "finance_key": "maintenance_monthly"},
        ),
    },
    "template.digital.saas.v1": {
        "template_id": "template.digital.saas.v1",
        "label_ar": "منتج رقمي / SaaS",
        "match_terms": ("saas", "برمج", "تطبيق", "منصة", "software", "app", "digital"),
        "items": (
            *COMMON_FINANCE_ITEMS,
            {"input_key": "capex_equipment", "label": "أجهزة ومعدات تقنية", "category": "capex_equipment", "unit": "SAR", "required": False, "finance_key": "capex_equipment"},
            {"input_key": "payroll_monthly", "label": "فريق المنتج والتقنية", "category": "opex", "unit": "SAR", "required": True, "finance_key": "payroll_monthly"},
            {"input_key": "utilities_monthly", "label": "استضافة وخدمات سحابية", "category": "opex", "unit": "SAR", "required": True, "finance_key": "utilities_monthly"},
            {"input_key": "marketing_monthly", "label": "التسويق واكتساب العملاء", "category": "opex", "unit": "SAR", "required": True, "finance_key": "marketing_monthly"},
            {"input_key": "rent_monthly", "label": "إيجار المكتب", "category": "opex", "unit": "SAR", "required": False, "finance_key": "rent_monthly"},
        ),
    },
    "template.retail.v1": {
        "template_id": "template.retail.v1",
        "label_ar": "تجارة تجزئة",
        "match_terms": ("متجر", "تجزئة", "retail", "shop", "بيع"),
        "items": (
            *COMMON_FINANCE_ITEMS,
            {"input_key": "capex_equipment", "label": "تجهيزات وأرفف ونقاط بيع", "category": "capex_equipment", "unit": "SAR", "required": True, "finance_key": "capex_equipment"},
            {"input_key": "capex_fitout", "label": "تجهيز وديكور", "category": "capex", "unit": "SAR", "required": True, "finance_key": "capex_fitout"},
            {"input_key": "rent_monthly", "label": "الإيجار الشهري", "category": "opex", "unit": "SAR", "required": True, "finance_key": "rent_monthly"},
            {"input_key": "payroll_monthly", "label": "الرواتب الشهرية", "category": "opex", "unit": "SAR", "required": True, "finance_key": "payroll_monthly"},
            {"input_key": "marketing_monthly", "label": "التسويق الشهري", "category": "opex", "unit": "SAR", "required": False, "finance_key": "marketing_monthly"},
        ),
    },
    "template.manufacturing.v1": {
        "template_id": "template.manufacturing.v1",
        "label_ar": "تصنيع",
        "match_terms": ("مصنع", "تصنيع", "manufactur", "production", "إنتاج"),
        "items": (
            *COMMON_FINANCE_ITEMS,
            {"input_key": "capex_equipment", "label": "خطوط ومعدات الإنتاج", "category": "capex_equipment", "unit": "SAR", "required": True, "finance_key": "capex_equipment"},
            {"input_key": "capex_fitout", "label": "تهيئة المنشأة الصناعية", "category": "capex", "unit": "SAR", "required": True, "finance_key": "capex_fitout"},
            {"input_key": "rent_monthly", "label": "إيجار المنشأة", "category": "opex", "unit": "SAR", "required": True, "finance_key": "rent_monthly"},
            {"input_key": "payroll_monthly", "label": "العمالة والإشراف", "category": "opex", "unit": "SAR", "required": True, "finance_key": "payroll_monthly"},
            {"input_key": "utilities_monthly", "label": "الطاقة والمرافق", "category": "opex", "unit": "SAR", "required": True, "finance_key": "utilities_monthly"},
            {"input_key": "maintenance_monthly", "label": "الصيانة الوقائية", "category": "opex", "unit": "SAR", "required": True, "finance_key": "maintenance_monthly"},
        ),
    },
    "template.generic.v1": {
        "template_id": "template.generic.v1",
        "label_ar": "قالب مشروع عام",
        "match_terms": (),
        "items": COMMON_FINANCE_ITEMS,
    },
}

QUESTIONS: dict[str, tuple[dict[str, Any], ...]] = {
    "template.food_service.shawarma.v1": (
        {"question_id": "service_model", "label": "هل الخدمة محلية فقط أم تشمل التوصيل؟", "type": "choice", "options": ["محلي", "توصيل", "هجين"], "required": True},
        {"question_id": "menu_scope", "label": "هل المشروع شاورما فقط أم قائمة أوسع؟", "type": "choice", "options": ["شاورما فقط", "شاورما ومقبلات", "قائمة أوسع"], "required": True},
        {"question_id": "site_area_m2", "label": "ما المساحة التقريبية للموقع بالمتر المربع؟", "type": "number", "required": True},
        {"question_id": "daily_capacity", "label": "كم وجبة تستهدف يوميًا؟", "type": "number", "required": True},
        {"question_id": "new_or_used_equipment", "label": "هل تقبل معدات مستعملة بحالة موثقة؟", "type": "choice", "options": ["جديدة فقط", "جديدة أو مستعملة"], "required": True},
    ),
    "template.digital.saas.v1": (
        {"question_id": "customer_type", "label": "هل العملاء أفراد أم منشآت؟", "type": "choice", "options": ["أفراد", "منشآت", "كلاهما"], "required": True},
        {"question_id": "billing_model", "label": "ما نموذج التحصيل؟", "type": "choice", "options": ["شهري", "سنوي", "حسب الاستخدام"], "required": True},
        {"question_id": "team_size", "label": "كم حجم الفريق عند الإطلاق؟", "type": "number", "required": True},
        {"question_id": "hosting_model", "label": "هل الاستضافة سحابية بالكامل؟", "type": "choice", "options": ["نعم", "هجين"], "required": True},
    ),
    "template.retail.v1": (
        {"question_id": "sales_channel", "label": "ما قناة البيع؟", "type": "choice", "options": ["متجر", "إلكتروني", "هجين"], "required": True},
        {"question_id": "inventory_model", "label": "هل المخزون مملوك أم بالعمولة؟", "type": "choice", "options": ["مملوك", "عمولة", "هجين"], "required": True},
        {"question_id": "site_area_m2", "label": "ما مساحة الموقع التقريبية؟", "type": "number", "required": False},
    ),
    "template.manufacturing.v1": (
        {"question_id": "product_family", "label": "ما عائلة المنتج الرئيسية؟", "type": "text", "required": True},
        {"question_id": "monthly_capacity", "label": "ما الطاقة الإنتاجية الشهرية المستهدفة؟", "type": "number", "required": True},
        {"question_id": "facility_model", "label": "هل المنشأة مملوكة أم مستأجرة؟", "type": "choice", "options": ["مملوكة", "مستأجرة"], "required": True},
        {"question_id": "automation_level", "label": "ما مستوى الأتمتة؟", "type": "choice", "options": ["يدوي", "نصف آلي", "آلي"], "required": True},
    ),
    "template.generic.v1": (
        {"question_id": "revenue_model", "label": "كيف يحقق المشروع الإيراد؟", "type": "text", "required": True},
        {"question_id": "operating_model", "label": "ما طبيعة التشغيل الأساسية؟", "type": "text", "required": True},
        {"question_id": "monthly_volume", "label": "ما الحجم الشهري المستهدف؟", "type": "number", "required": True},
    ),
}


def template_catalog() -> list[dict[str, Any]]:
    return [
        {
            "template_id": template["template_id"],
            "label_ar": template["label_ar"],
            "item_count": len(template["items"]),
        }
        for template in TEMPLATES.values()
    ]


def classify_project_template(profile: dict[str, Any]) -> str:
    text = " ".join(
        str(profile.get(key) or "")
        for key in ("name", "idea", "sector", "activity_description", "primary_sector_id", "subsector_id")
    ).lower()
    for template_id, template in TEMPLATES.items():
        if template_id == "template.generic.v1":
            continue
        if any(term.lower() in text for term in template["match_terms"]):
            return template_id
    return "template.generic.v1"


def governed_template(profile: dict[str, Any], template_id: str | None = None) -> dict[str, Any]:
    selected = template_id or classify_project_template(profile)
    if selected not in TEMPLATES:
        selected = "template.generic.v1"
    template = deepcopy(TEMPLATES[selected])
    template["questions"] = deepcopy(list(QUESTIONS.get(selected, QUESTIONS["template.generic.v1"])))
    template["profile"] = deepcopy(profile)
    template["registry_status"] = "ACTIVE_LOCAL_DETERMINISTIC"
    template["ai_provider_used"] = False
    return template


def question_registry(template_id: str) -> list[dict[str, Any]]:
    return deepcopy(list(QUESTIONS.get(template_id, QUESTIONS["template.generic.v1"])))


def suggested_item_specs(template_id: str) -> list[dict[str, Any]]:
    template = TEMPLATES.get(template_id, TEMPLATES["template.generic.v1"])
    return deepcopy(list(template["items"]))
