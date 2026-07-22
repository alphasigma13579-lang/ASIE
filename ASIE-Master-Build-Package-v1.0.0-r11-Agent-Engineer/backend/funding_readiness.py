"""Deterministic local funding-readiness checks over a report projection."""

from __future__ import annotations

from typing import Any

from backend.snapshot_assembly import canonical_hash

FUNDING_READINESS_CONTRACT = "funding.readiness.profile.v1"
PROFILE_REVIEW_DATE = "2026-07-20"

FUNDING_PROFILES: dict[str, dict[str, Any]] = {
    "BASE-FUNDING-V1": {"label_ar": "حزمة التمويل الأساسية", "profile_status": "reference_only", "requirements": [("identity", "هوية المشروع والـSnapshot", "core"), ("study_sections", "الأقسام الستة عشر", "core"), ("financial_projection", "التوقعات المالية", "core"), ("evidence_traceability", "تتبع الأدلة والافتراضات", "core"), ("risk_execution", "المخاطر وخطة التنفيذ", "core")]},
    "BANK-SME-BASE-V1": {"label_ar": "ملف تمويل مصرفي مرجعي للمنشآت", "profile_status": "reference_only", "requirements": [("identity", "هوية المشروع والـSnapshot", "core"), ("financial_projection", "التوقعات المالية", "core"), ("balance_sheet", "المركز المالي", "required"), ("cashflow_detail", "التدفقات النقدية التفصيلية", "required"), ("funding_sources_uses", "مصادر واستخدامات التمويل", "required"), ("dscr", "قدرة خدمة الدين DSCR", "required"), ("evidence_traceability", "تتبع الأدلة والافتراضات", "core")]},
    "DEVELOPMENT-FUND-BASE-V1": {"label_ar": "ملف صندوق تنمية مرجعي", "profile_status": "reference_only", "requirements": [("identity", "هوية المشروع والـSnapshot", "core"), ("market", "دراسة السوق والطلب", "required"), ("technical", "الدراسة الفنية والطاقة التشغيلية", "required"), ("capex", "تفصيل الاستثمار التأسيسي", "required"), ("execution", "القدرة وخطة التنفيذ", "required"), ("funding_sources_uses", "مصادر واستخدامات التمويل", "required"), ("evidence_traceability", "تتبع الأدلة والافتراضات", "core")]},
    "INVESTOR-EQUITY-BASE-V1": {"label_ar": "ملف مستثمر/حقوق ملكية مرجعي", "profile_status": "reference_only", "requirements": [("identity", "هوية المشروع والـSnapshot", "core"), ("market", "دراسة السوق والطلب", "required"), ("business_model", "نموذج الأعمال", "required"), ("scenarios", "السيناريوهات والحساسية", "required"), ("risk_execution", "المخاطر وخطة التنفيذ", "required"), ("evidence_traceability", "تتبع الأدلة والافتراضات", "core")]},
}

# Local reference packs only. These are not official lender or regulator rules.
SECTOR_PROFILES: dict[str, dict[str, Any]] = {
    "SECTOR-RETAIL-V1": {
        "label_ar": "قطاع التجزئة — مرجع محلي",
        "sector_ar": "التجزئة",
        "scope_ar": "مشروعات بيع السلع عبر متجر فعلي أو قناة رقمية",
        "reviewed_at": PROFILE_REVIEW_DATE,
        "profile_status": "reference_only",
        "not_covered_ar": ["اشتراطات البلدية أو الترخيص الخاصة بالموقع", "حدود الائتمان أو سياسات الجهة الممولة"],
        "not_locally_verifiable": ["regulatory_acceptance", "lender_policy", "merchant_acquirer_terms"],
    },
    "SECTOR-FOOD-SERVICE-V1": {
        "label_ar": "قطاع الأغذية والمشروبات — مرجع محلي",
        "sector_ar": "الأغذية والمشروبات",
        "scope_ar": "مشروعات المطاعم والمقاهي وخدمات الأغذية",
        "reviewed_at": PROFILE_REVIEW_DATE,
        "profile_status": "reference_only",
        "not_covered_ar": ["اشتراطات الصحة وسلامة الغذاء المحلية", "اعتماد الموقع والقدرة الاستيعابية من الجهة المختصة"],
        "not_locally_verifiable": ["regulatory_acceptance", "food_safety_license", "lender_policy"],
    },
    "SECTOR-MANUFACTURING-V1": {
        "label_ar": "قطاع التصنيع — مرجع محلي",
        "sector_ar": "التصنيع",
        "scope_ar": "مشروعات الإنتاج والتحويل الصناعي الصغيرة والمتوسطة",
        "reviewed_at": PROFILE_REVIEW_DATE,
        "profile_status": "reference_only",
        "not_covered_ar": ["الرخص الصناعية والبيئية", "اعتماد المواصفات الفنية للمنتج"],
        "not_locally_verifiable": ["industrial_license", "environmental_permit", "lender_policy"],
    },
    "SECTOR-DIGITAL-SERVICES-V1": {
        "label_ar": "الخدمات الرقمية — مرجع محلي",
        "sector_ar": "الخدمات الرقمية",
        "scope_ar": "البرمجيات والمنصات والاشتراكات والخدمات المهنية الرقمية",
        "reviewed_at": PROFILE_REVIEW_DATE,
        "profile_status": "reference_only",
        "not_covered_ar": ["الخصوصية والأمن السيبراني حسب الولاية القضائية", "شروط مزودي الدفع أو الاستضافة"],
        "not_locally_verifiable": ["privacy_compliance", "payment_provider_terms", "lender_policy"],
    },
}


def profile_ids() -> list[str]:
    return sorted(FUNDING_PROFILES)


def profile_catalog() -> list[dict[str, Any]]:
    return [
        {"profile_id": profile_id, "label_ar": FUNDING_PROFILES[profile_id]["label_ar"], "profile_status": FUNDING_PROFILES[profile_id]["profile_status"], "requirement_count": len(FUNDING_PROFILES[profile_id]["requirements"])}
        for profile_id in profile_ids()
    ]


def sector_profile_catalog() -> list[dict[str, Any]]:
    return [
        {
            "profile_id": profile_id,
            "label_ar": profile["label_ar"],
            "sector_ar": profile["sector_ar"],
            "scope_ar": profile["scope_ar"],
            "reviewed_at": profile["reviewed_at"],
            "profile_status": profile["profile_status"],
            "not_covered_ar": list(profile["not_covered_ar"]),
            "not_locally_verifiable": list(profile["not_locally_verifiable"]),
        }
        for profile_id, profile in sorted(SECTOR_PROFILES.items())
    ]


def _check(requirement_id: str, label: str, status: str, reason: str = "", source_refs: list[str] | None = None) -> dict[str, Any]:
    return {"requirement_id": requirement_id, "label": label, "status": status, "reason": reason, "source_refs": source_refs or []}


def evaluate_funding_readiness(projection: dict[str, Any], profile_id: str = "BASE-FUNDING-V1") -> dict[str, Any]:
    profile = FUNDING_PROFILES.get(profile_id)
    snapshot_id = str(projection.get("snapshot_id") or "")
    if profile is None:
        result = {"contract_id": FUNDING_READINESS_CONTRACT, "profile_id": profile_id, "profile_status": "unknown", "status": "REVIEW_REQUIRED", "snapshot_id": snapshot_id, "checks": [_check("profile", "ملف الجهة", "blocked", "unknown_profile")], "missing_requirements": ["profile"], "warnings": []}
        result["readiness_hash"] = canonical_hash(result)
        return result
    sections = {row.get("section_id", ""): row for row in projection.get("sections", [])}
    finance = (sections.get("14-financial-expectations") or {}).get("payload", {})
    statements = finance.get("statements") or {}
    income = statements.get("income_statement") or {}
    cashflow = statements.get("cashflow") or {}
    balance_sheet = statements.get("balance_sheet") or {}
    capital = (sections.get("15-capital-requirements") or {}).get("payload") or {}
    evidence = projection.get("evidence") or {}
    checks: list[dict[str, Any]] = []
    for requirement_id, label, level in profile["requirements"]:
        status, reason, refs = "passed", "", []
        if requirement_id == "identity":
            status = "passed" if snapshot_id and projection.get("project_id") else "blocked"; reason = "missing_snapshot_or_project_identity" if status == "blocked" else ""; refs = [f"snapshot:{snapshot_id}"] if snapshot_id else []
        elif requirement_id == "study_sections":
            status = "passed" if len(sections) == 16 else "blocked"; reason = "study_sections_incomplete" if status == "blocked" else ""
        elif requirement_id == "financial_projection":
            status = "passed" if income.get("years") and finance.get("baseline") else "blocked"; reason = "financial_projection_not_ready" if status == "blocked" else ""; refs = ["finance"]
        elif requirement_id == "balance_sheet":
            status = "passed" if balance_sheet.get("status") == "projected" else "blocked"; reason = "balance_sheet_not_available" if status == "blocked" else ""; refs = ["finance"]
        elif requirement_id == "cashflow_detail":
            status = "passed" if cashflow.get("status") == "projected" and not cashflow.get("gaps") else "blocked"; reason = "cashflow_detail_not_available" if status == "blocked" else ""; refs = ["finance"]
        elif requirement_id == "funding_sources_uses":
            sources, uses = capital.get("sources") or {}, capital.get("uses") or {}; status = "passed" if uses.get("initial_investment") is not None and sources.get("external_funding_need") is not None else "blocked"; reason = "funding_sources_or_uses_incomplete" if status == "blocked" else ""; refs = ["finance"]
        elif requirement_id == "dscr":
            dscr = (finance.get("baseline") or {}).get("dscr"); status = "passed" if dscr is not None and dscr >= 1.2 else "warning" if dscr is not None else "blocked"; reason = "dscr_below_1_2" if status == "warning" else "dscr_not_available" if status == "blocked" else ""; refs = ["finance"]
        elif requirement_id == "evidence_traceability":
            status = "passed" if evidence.get("evidence_register_id") and evidence.get("assumption_refs") else "warning"; reason = "evidence_register_or_assumptions_incomplete" if status == "warning" else ""; refs = [evidence.get("evidence_register_id", "")] if evidence.get("evidence_register_id") else []
        elif requirement_id == "market":
            status = "passed" if (sections.get("06-product-market") or {}).get("status") == "ready" else "warning"; reason = "market_evidence_needs_review" if status == "warning" else ""; refs = ["sector_intelligence", "evidence_ledger"]
        elif requirement_id == "technical":
            status = "passed" if (sections.get("10-technical") or {}).get("status") == "ready" else "warning"; reason = "technical_inputs_need_review" if status == "warning" else ""; refs = ["finance", "execution_plan"]
        elif requirement_id == "capex":
            status = "passed" if (finance.get("baseline") or {}).get("initial_investment") is not None else "blocked"; reason = "capex_not_available" if status == "blocked" else ""; refs = ["finance"]
        elif requirement_id == "execution":
            status = "passed" if (sections.get("13-capability") or {}).get("payload", {}).get("execution_plan") else "warning"; reason = "execution_plan_needs_review" if status == "warning" else ""; refs = ["execution_plan"]
        elif requirement_id == "risk_execution":
            status = "passed" if (sections.get("12-general-risks") or {}).get("payload", {}).get("risk_register") else "warning"; reason = "risk_register_needs_review" if status == "warning" else ""; refs = ["risk_register", "execution_plan"]
        elif requirement_id == "business_model":
            status = "passed" if (sections.get("11-business-model") or {}).get("status") == "ready" else "warning"; reason = "business_model_not_persisted" if status == "warning" else ""; refs = ["project_inputs"]
        elif requirement_id == "scenarios":
            status = "passed" if projection.get("scenarios") else "warning"; reason = "scenario_projection_missing" if status == "warning" else ""; refs = ["finance"]
        if level == "core" and status == "warning": status = "passed"
        checks.append(_check(requirement_id, label, status, reason, refs))
    missing = [row["requirement_id"] for row in checks if row["status"] == "blocked"]
    warnings = [row["requirement_id"] for row in checks if row["status"] == "warning"]
    result = {"contract_id": FUNDING_READINESS_CONTRACT, "profile_id": profile_id, "profile_label_ar": profile["label_ar"], "profile_status": profile["profile_status"], "status": "DRAFT_INTERNAL" if missing else "DECISION_READY" if warnings else "FUNDER_PROFILE_READY", "snapshot_id": snapshot_id, "checks": checks, "missing_requirements": missing, "warnings": warnings, "acceptance_disclaimer": "مرور قائمة متطلبات مرجعية؛ لا يمثل قبولاً أو قراراً من الجهة."}
    result["readiness_hash"] = canonical_hash(result)
    return result
