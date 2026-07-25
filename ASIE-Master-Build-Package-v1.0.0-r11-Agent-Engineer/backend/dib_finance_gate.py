from __future__ import annotations

from decimal import Decimal
from typing import Any

from backend.finance_engine import (
    OPTIONAL_DEFAULTS,
    calculate_finance,
    monte_carlo,
    not_ready_monte_carlo,
    operational_sensitivity,
    sensitivity_matrix,
    serialize_finance,
    serialize_nested,
)
from backend.input_manifest import build_approved_input_manifest, manifest_item_map


def _blocker(code: str, message: str, *, severity: str = "critical") -> dict[str, str]:
    return {"code": code, "severity": severity, "message": message}


def _allows_zero(item_map: dict[str, dict[str, Any]], key: str) -> bool:
    item = item_map.get(key, {})
    return (
        item.get("state") in {"INTENTIONAL_ZERO", "NOT_APPLICABLE"}
        and bool(str(item.get("reason") or "").strip())
        and item.get("approval_status") == "approved"
    )


def validate_manifest_finance_inputs(
    normalized_inputs: dict[str, Any],
    manifest: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    values: dict[str, Any] = {}
    blockers = [dict(row) for row in manifest.get("blockers", []) if isinstance(row, dict)]
    item_map = manifest_item_map(manifest)

    use_capacity = bool(normalized_inputs.get("use_operating_capacity"))
    values["use_operating_capacity"] = use_capacity

    for key in ("startup_cost", "monthly_fixed_cost", "unit_price", "variable_cost"):
        raw = normalized_inputs.get(key)
        try:
            value = None if raw is None or raw == "" else Decimal(str(raw))
        except (ValueError, TypeError):
            value = None
        if value is None:
            blockers.append(_blocker(f"MISSING_{key.upper()}", f"المدخل المطلوب {key} غير معروف بعد."))
            continue
        if value < 0:
            blockers.append(_blocker(f"INVALID_NEGATIVE_{key.upper()}", f"المدخل {key} لا يمكن أن يكون سالبًا."))
            continue
        if value == 0 and key in {"startup_cost", "monthly_fixed_cost", "variable_cost"} and not _allows_zero(item_map, key):
            blockers.append(
                _blocker(
                    f"UNJUSTIFIED_ZERO_{key.upper()}",
                    f"الصفر في {key} يحتاج حالة صفر مقصود أو غير منطبق مع سبب واعتماد.",
                )
            )
            continue
        if key == "unit_price" and value <= 0:
            blockers.append(_blocker("INVALID_UNIT_PRICE", "سعر الوحدة يجب أن يكون موجبًا لحساب الإيراد والتعادل."))
            continue
        values[key] = value

    for key, default in OPTIONAL_DEFAULTS.items():
        raw = normalized_inputs.get(key)
        try:
            values[key] = default if raw is None or raw == "" else Decimal(str(raw))
        except (ValueError, TypeError):
            blockers.append(_blocker(f"INVALID_{key.upper()}", f"قيمة {key} ليست رقمًا صالحًا."))
            values[key] = default

    if use_capacity:
        for key in ("capacity_units_per_day", "operating_days_per_month", "utilization_rate"):
            if values[key] <= 0:
                blockers.append(_blocker(f"MISSING_{key.upper()}", f"المدخل {key} مطلوب عند تفعيل نموذج الطاقة."))
        if values["utilization_rate"] > 1:
            blockers.append(_blocker("INVALID_UTILIZATION_RATE", "نسبة الاستخدام يجب أن تكون بين 0 و1."))
        if not any(
            row["code"].startswith(("MISSING_CAPACITY", "MISSING_OPERATING", "MISSING_UTILIZATION"))
            for row in blockers
        ):
            values["monthly_units"] = (
                values["capacity_units_per_day"]
                * values["operating_days_per_month"]
                * values["utilization_rate"]
            )
    else:
        raw_units = normalized_inputs.get("monthly_units")
        try:
            monthly_units = None if raw_units is None or raw_units == "" else Decimal(str(raw_units))
        except (ValueError, TypeError):
            monthly_units = None
        if monthly_units is None or monthly_units <= 0:
            blockers.append(_blocker("MISSING_MONTHLY_UNITS", "الوحدات الشهرية مطلوبة كرقم موجب."))
        else:
            values["monthly_units"] = monthly_units

    if "unit_price" in values and "variable_cost" in values and values["unit_price"] <= values["variable_cost"]:
        blockers.append(
            _blocker(
                "INVALID_UNIT_ECONOMICS",
                "سعر الوحدة يجب أن يكون أعلى من التكلفة المتغيرة للوحدة قبل حساب التعادل.",
            )
        )
    if values["annual_discount_rate"] <= 0:
        blockers.append(_blocker("MISSING_DISCOUNT_RATE", "معدل الخصم السنوي مطلوب لحساب NPV وIRR."))

    values["debt_terms_ready"] = not (
        values["debt_amount"] > 0
        and (values["annual_interest_rate"] <= 0 or values["loan_years"] <= 0)
    )

    unique: list[dict[str, str]] = []
    seen: set[str] = set()
    for row in blockers:
        code = str(row.get("code") or "UNKNOWN_BLOCKER")
        if code in seen:
            continue
        seen.add(code)
        unique.append(
            {
                "code": code,
                "severity": str(row.get("severity") or "critical"),
                "message": str(row.get("message") or code),
            }
        )
    return values, unique


def finance_result_from_project_inputs(
    project_id: str,
    raw_inputs: dict[str, Any],
    *,
    assumption_refs: list[str] | None = None,
) -> tuple[dict[str, Any], list[dict[str, str]], dict[str, Any]]:
    has_blueprint = bool(raw_inputs.get("blueprint_items"))
    manifest = build_approved_input_manifest(
        project_id,
        raw_inputs,
        assumption_refs=assumption_refs or [],
        legacy_compatibility=not has_blueprint,
    ).to_public()

    values, blockers = validate_manifest_finance_inputs(manifest["normalized_inputs"], manifest)
    if blockers:
        return (
            {
                "status": "not_ready",
                "baseline": None,
                "scenarios": [],
                "sensitivity": None,
                "operational_sensitivity": None,
                "operating_model": None,
                "capex_breakdown": None,
                "opex_breakdown": None,
                "debt_service_profile": None,
                "monte_carlo": not_ready_monte_carlo(blockers),
                "assumption_refs": list(assumption_refs or []),
                "approved_input_manifest": manifest,
            },
            blockers,
            manifest,
        )

    scenarios = [calculate_finance(values, scenario_id) for scenario_id in ("conservative", "baseline", "optimistic")]
    baseline = next(item for item in scenarios if item["scenario_id"] == "baseline")
    refs = list(assumption_refs or [])
    if not refs:
        refs = ["assumption:approved-input-manifest:" + str(manifest["manifest_id"])]
    result = {
        "status": "ready",
        "baseline": serialize_finance(baseline),
        "scenarios": [serialize_finance(item) for item in scenarios],
        "sensitivity": sensitivity_matrix(values),
        "operational_sensitivity": operational_sensitivity(values),
        "operating_model": serialize_nested(baseline["operating_model"]),
        "capex_breakdown": serialize_nested(baseline["capex_breakdown"]),
        "opex_breakdown": serialize_nested(baseline["opex_breakdown"]),
        "debt_service_profile": serialize_nested(baseline["debt_service_profile"]),
        "monte_carlo": monte_carlo(baseline, values),
        "assumption_refs": refs,
        "approved_input_manifest": manifest,
    }
    return result, [], manifest
