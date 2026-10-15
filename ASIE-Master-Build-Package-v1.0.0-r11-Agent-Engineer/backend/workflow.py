from __future__ import annotations

from typing import Any
import hashlib

from backend.finance_engine import validate_finance_inputs
from backend.sector_intelligence import taxonomy_by_id

WIZARD_STEPS = [
    ("definition", "تعريف المشروع"),
    ("sector_intelligence", "القطاع ومؤشرات الاستثمار"),
    ("revenue_model", "نموذج الإيرادات"),
    ("costs", "التكاليف"),
    ("financing", "التمويل"),
    ("assumptions", "الافتراضات"),
    ("sources", "المصادر"),
    ("review", "المراجعة"),
    ("run", "التشغيل"),
]


def project_readiness(project: Any, assumptions: list[dict[str, Any]], sources: list[dict[str, Any]], *, include_recovery: bool = False) -> dict[str, Any]:
    inputs = project.inputs
    _values, blockers = validate_finance_inputs(inputs)
    uses_capacity = bool(inputs.get("use_operating_capacity"))
    steps = [
        step("definition", has_text(project.name) and has_text(project.sector) and has_text(project.jurisdiction)),
        step("sector_intelligence", True, review_status=sector_review_state(inputs)),
        step(
            "revenue_model",
            positive(inputs.get("unit_price"))
            and (
                positive(inputs.get("monthly_units"))
                if not uses_capacity
                else positive(inputs.get("capacity_units_per_day"))
                and positive(inputs.get("operating_days_per_month"))
                and positive(inputs.get("utilization_rate"))
            ),
        ),
        step(
            "costs",
            positive(inputs.get("startup_cost"))
            and positive(inputs.get("monthly_fixed_cost"))
            and positive(inputs.get("variable_cost")),
        ),
        step(
            "financing",
            positive(inputs.get("annual_discount_rate", 0.1))
            and number(inputs.get("working_capital_months", 2))
            and debt_terms_ready(inputs),
        ),
        step("assumptions", len(assumptions) >= 5, review_status=assumption_review_state(assumptions)),
        step("sources", True, review_status=source_review_state(sources)),
    ]
    review_ready = all(item["status"] in {"ready", "needs_review"} for item in steps) and not blockers
    steps.append(step("review", review_ready, blockers=blockers))
    steps.append(step("run", review_ready, blockers=blockers))
    return {
        "project_id": project.project_id,
        "ready_to_run": review_ready,
        "steps": steps,
        "blockers": blockers,
        **({"recovery_items": project_recovery_items(project, assumptions, sources, blockers)} if include_recovery else {}),
    }


def step(
    step_id: str,
    ready: bool,
    *,
    review_status: str = "ready",
    blockers: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    label = dict(WIZARD_STEPS)[step_id]
    if blockers:
        status = "blocked"
        message = "توجد بوابات تمنع هذه الخطوة."
    elif not ready:
        status = "needs_input"
        message = "تحتاج هذه الخطوة إلى مدخلات إضافية."
    elif review_status == "needs_review":
        status = "needs_review"
        message = "جاهزة مبدئيًا لكنها تحتاج مراجعة بشرية."
    else:
        status = "ready"
        message = "جاهزة."
    return {"step_id": step_id, "label": label, "status": status, "message": message}


def has_text(value: Any) -> bool:
    return bool(str(value or "").strip())


def positive(value: Any) -> bool:
    try:
        return float(value) > 0
    except (TypeError, ValueError):
        return False


def number(value: Any) -> bool:
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False


def debt_terms_ready(inputs: dict[str, Any]) -> bool:
    try:
        debt = float(inputs.get("debt_amount", 0) or 0)
    except (TypeError, ValueError):
        return False
    if debt <= 0:
        return True
    return positive(inputs.get("annual_interest_rate")) and positive(inputs.get("loan_years"))


def assumption_review_state(assumptions: list[dict[str, Any]]) -> str:
    if any(row.get("review_status") in {"draft", "needs_review"} for row in assumptions):
        return "needs_review"
    return "ready"


def source_review_state(sources: list[dict[str, Any]]) -> str:
    if not any(row.get("state") == "enabled" for row in sources):
        return "needs_review"
    return "ready"


def sector_review_state(inputs: dict[str, Any]) -> str:
    sector_id = str(inputs.get("primary_sector_id") or "").strip()
    if not sector_id or sector_id not in taxonomy_by_id():
        return "needs_review"
    return "ready"


# Navigation projection of the existing readiness predicates, never a new run gate.
FINANCE_RECOVERY_FIELDS = {
    "MISSING_STARTUP_COST": ["startup_cost"],
    "MISSING_MONTHLY_FIXED_COST": ["payroll_monthly", "rent_monthly", "utilities_monthly", "marketing_monthly", "maintenance_monthly", "other_monthly_costs"],
    "MISSING_UNIT_PRICE": ["unit_price"],
    "MISSING_VARIABLE_COST": ["variable_cost"],
    "MISSING_MONTHLY_UNITS": ["monthly_units"],
    "MISSING_CAPACITY_UNITS_PER_DAY": ["capacity_units_per_day"],
    "MISSING_OPERATING_DAYS_PER_MONTH": ["operating_days_per_month"],
    "MISSING_UTILIZATION_RATE": ["utilization_rate"],
    "INVALID_UTILIZATION_RATE": ["utilization_rate"],
    "INVALID_UNIT_ECONOMICS": ["unit_price", "variable_cost"],
    "MISSING_DISCOUNT_RATE": ["annual_discount_rate"],
}


def recovery_item(project: Any, requirement: str, target: dict[str, Any], *,
                  required: bool = True, source_kind: str = "project_draft",
                  entity_id: str | None = None, updated_at: str | None = None,
                  permission: str = "project.edit", count: dict[str, int] | None = None) -> dict[str, Any]:
    """Project-owned display target; permission admission is applied at the HTTP boundary."""
    identity = entity_id or project.project_id
    result = {
        "recovery_id": f"{source_kind}:{identity}:{requirement}",
        "requirement_code": requirement,
        "reason_key": requirement.lower(),
        "required": required,
        "severity": "required" if required else "review",
        "source": {"kind": source_kind, "organization_id": project.organization_id,
                   "project_id": project.project_id, "entity_id": identity,
                   "updated_at": updated_at if updated_at is not None else project.updated_at},
        "target": target,
        "action": {"required_permission": permission, "allowed": False,
                   "responsible_role": "platform_admin" if permission == "platform.manage" else "project_editor"},
        "resolution": "unmapped" if target["kind"] == "owner_review" else "unresolved",
    }
    if count is not None:
        result["count"] = dict(count)
    return result


def project_recovery_items(project: Any, assumptions: list[dict[str, Any]],
                           sources: list[dict[str, Any]], blockers: list[dict[str, str]]) -> list[dict[str, Any]]:
    """Explain current draft deficits without reading or altering historical results."""
    items: list[dict[str, Any]] = []
    def fields(code: str, keys: list[str], required: bool = True) -> None:
        items.append(recovery_item(project, code, {
            "kind": "project_field" if len(keys) == 1 else "project_fields", "field_keys": keys,
        }, required=required))
    for key in ("name", "sector", "jurisdiction"):
        if not has_text(getattr(project, key)):
            fields(f"MISSING_PROJECT_{key.upper()}", [key])
    if sector_review_state(project.inputs) == "needs_review":
        fields("SECTOR_REVIEW_REQUIRED", ["primary_sector_id"], False)
    for blocker in blockers:
        code = blocker["code"]
        if code in FINANCE_RECOVERY_FIELDS:
            fields(code, list(FINANCE_RECOVERY_FIELDS[code]))
        else:
            # Unknown owner code stays visibly unresolved; no guessed input target.
            item = recovery_item(project, "UNMAPPED_READINESS_REQUIREMENT", {"kind": "owner_review"})
            item["recovery_id"] += ":" + hashlib.sha256(code.encode("utf-8")).hexdigest()[:16]
            items.append(item)
    inputs = project.inputs
    if not number(inputs.get("working_capital_months", 2)):
        fields("INVALID_WORKING_CAPITAL_MONTHS", ["working_capital_months"])
    if not positive(inputs.get("annual_discount_rate", 0.1)) and not any(i["requirement_code"] == "MISSING_DISCOUNT_RATE" for i in items):
        fields("MISSING_DISCOUNT_RATE", ["annual_discount_rate"])
    if not debt_terms_ready(inputs):
        if not number(inputs.get("debt_amount", 0) or 0):
            fields("INVALID_DEBT_AMOUNT", ["debt_amount"])
        else:
            missing = [key for key in ("annual_interest_rate", "loan_years") if not positive(inputs.get(key))]
            fields("MISSING_DEBT_TERMS", missing)
    # These are existing readiness requirements, not invented assumption names.
    if len(assumptions) < 5:
        items.append(recovery_item(project, "ASSUMPTION_COUNT_REQUIRED", {"kind": "assumption_add"},
                     count={"current": len(assumptions), "required": 5, "remaining": 5 - len(assumptions)}))
    for row in assumptions:
        if row.get("review_status") in {"draft", "needs_review"}:
            items.append(recovery_item(project, "ASSUMPTION_REVIEW_REQUIRED",
                {"kind": "assumption_review", "target_id": row["assumption_id"]}, required=False,
                source_kind="assumption", entity_id=row["assumption_id"], updated_at=row.get("updated_at")))
    if source_review_state(sources) == "needs_review":
        for row in sources:
            if row.get("state") == "reference_only" or row.get("reviewer_decision") == "reference_only":
                continue
            items.append(recovery_item(project, "SOURCE_REVIEW_REQUIRED",
                {"kind": "source_review", "source_id": row["source_id"]}, required=False,
                source_kind="source_review", entity_id=row["source_id"], updated_at=row.get("reviewed_at"), permission="platform.manage"))
        if not any(row.get("state") != "reference_only" and row.get("reviewer_decision") != "reference_only" for row in sources):
            items.append(recovery_item(project, "SOURCE_OWNER_REVIEW_REQUIRED", {"kind": "owner_review"}, required=False, permission="platform.manage"))
    return items
