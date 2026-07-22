from __future__ import annotations

from typing import Any

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


def project_readiness(project: Any, assumptions: list[dict[str, Any]], sources: list[dict[str, Any]]) -> dict[str, Any]:
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
