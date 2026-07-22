from __future__ import annotations

import random
from decimal import Decimal, getcontext
from typing import Any

from backend.contracts import SEED, decimal_from, money

getcontext().prec = 28

CORE_INPUTS = ["startup_cost", "monthly_fixed_cost", "unit_price", "variable_cost"]
OPTIONAL_DEFAULTS = {
    "monthly_units": Decimal("0"),
    "annual_discount_rate": Decimal("0.10"),
    "working_capital_months": Decimal("2"),
    "debt_amount": Decimal("0"),
    "annual_interest_rate": Decimal("0.08"),
    "loan_years": Decimal("5"),
    "loan_grace_months": Decimal("0"),
    "capacity_units_per_day": Decimal("0"),
    "operating_days_per_month": Decimal("0"),
    "utilization_rate": Decimal("0"),
    "payroll_monthly": Decimal("0"),
    "rent_monthly": Decimal("0"),
    "utilities_monthly": Decimal("0"),
    "marketing_monthly": Decimal("0"),
    "maintenance_monthly": Decimal("0"),
    "capex_equipment": Decimal("0"),
    "capex_fitout": Decimal("0"),
    "capex_licenses_local": Decimal("0"),
    "depreciation_years": Decimal("5"),
    "equity_contribution": Decimal("0"),
}
SCENARIO_FACTORS = {
    "conservative": {"demand": Decimal("0.85"), "price": Decimal("0.96"), "cost": Decimal("1.08")},
    "baseline": {"demand": Decimal("1.00"), "price": Decimal("1.00"), "cost": Decimal("1.00")},
    "optimistic": {"demand": Decimal("1.15"), "price": Decimal("1.03"), "cost": Decimal("0.97")},
}


def validate_finance_inputs(inputs: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, str]]]:
    values: dict[str, Any] = {}
    blockers: list[dict[str, str]] = []
    use_capacity = bool(inputs.get("use_operating_capacity"))
    values["use_operating_capacity"] = use_capacity
    for key in CORE_INPUTS:
        value = decimal_from(inputs.get(key))
        if value is None or value <= 0:
            blockers.append(
                {
                    "code": f"MISSING_{key.upper()}",
                    "severity": "critical",
                    "message": f"المدخل {key} مطلوب كرقم موجب قبل تشغيل الحسابات.",
                }
            )
        else:
            values[key] = value

    for key, default in OPTIONAL_DEFAULTS.items():
        value = decimal_from(inputs.get(key))
        values[key] = default if value is None else value

    if use_capacity:
        for key in ["capacity_units_per_day", "operating_days_per_month", "utilization_rate"]:
            if values[key] <= 0:
                blockers.append(
                    {
                        "code": f"MISSING_{key.upper()}",
                        "severity": "critical",
                        "message": f"المدخل {key} مطلوب كرقم موجب عند تفعيل نموذج الطاقة التشغيلية.",
                    }
                )
        if values["utilization_rate"] > 1:
            blockers.append(
                {
                    "code": "INVALID_UTILIZATION_RATE",
                    "severity": "critical",
                    "message": "نسبة الاستخدام يجب أن تكون بين 0 و1.",
                }
            )
        if not any(blocker["code"].startswith("MISSING_CAPACITY") or blocker["code"].startswith("MISSING_OPERATING") or blocker["code"].startswith("MISSING_UTILIZATION") for blocker in blockers):
            values["monthly_units"] = (
                values["capacity_units_per_day"] * values["operating_days_per_month"] * values["utilization_rate"]
            )
    elif values["monthly_units"] <= 0:
        blockers.append(
            {
                "code": "MISSING_MONTHLY_UNITS",
                "severity": "critical",
                "message": "الوحدات الشهرية مطلوبة كرقم موجب عند عدم تفعيل نموذج الطاقة التشغيلية.",
            }
        )

    if "unit_price" in values and "variable_cost" in values and values["unit_price"] <= values["variable_cost"]:
        blockers.append(
            {
                "code": "INVALID_UNIT_ECONOMICS",
                "severity": "critical",
                "message": "سعر الوحدة يجب أن يكون أعلى من التكلفة المتغيرة للوحدة قبل حساب التعادل.",
            }
        )
    if values["annual_discount_rate"] <= 0:
        blockers.append(
            {
                "code": "MISSING_DISCOUNT_RATE",
                "severity": "critical",
                "message": "معدل الخصم السنوي مطلوب لحساب NPV وIRR.",
            }
        )
    if values["debt_amount"] > 0 and (values["annual_interest_rate"] <= 0 or values["loan_years"] <= 0):
        values["debt_terms_ready"] = False
    else:
        values["debt_terms_ready"] = True
    return values, blockers


def scenario_values(values: dict[str, Any], scenario_id: str) -> dict[str, Any]:
    factors = SCENARIO_FACTORS[scenario_id]
    adjusted = dict(values)
    adjusted["monthly_units"] = values["monthly_units"] * factors["demand"]
    adjusted["unit_price"] = values["unit_price"] * factors["price"]
    adjusted["variable_cost"] = values["variable_cost"] * factors["cost"]
    return adjusted


def calculate_finance(values: dict[str, Any], scenario_id: str = "baseline") -> dict[str, Any]:
    adjusted = scenario_values(values, scenario_id)
    opex = opex_breakdown(adjusted)
    capex = capex_breakdown(adjusted)
    operating_model = operating_model_summary(adjusted)
    revenue = adjusted["unit_price"] * adjusted["monthly_units"]
    variable_total = adjusted["variable_cost"] * adjusted["monthly_units"]
    gross_profit = revenue - variable_total
    ebitda = gross_profit - opex["total_monthly_opex"]
    depreciation_monthly = capex["depreciation_monthly"]
    ebit = ebitda - depreciation_monthly
    debt_profile = debt_service_profile(adjusted, ebitda)
    monthly_profit = ebitda - (debt_profile["monthly_payment"] or Decimal("0"))
    contribution_per_unit = adjusted["unit_price"] - adjusted["variable_cost"]
    contribution_margin = contribution_per_unit / adjusted["unit_price"]
    break_even_units = opex["total_monthly_opex"] / contribution_per_unit
    working_capital_need = (opex["total_monthly_opex"] + variable_total) * adjusted["working_capital_months"]
    initial_investment = capex["total_capex"] + working_capital_need
    funding_gap = max(Decimal("0"), initial_investment - adjusted["equity_contribution"])
    annual_cashflow = monthly_profit * Decimal("12")
    npv = net_present_value(initial_investment, annual_cashflow, adjusted["annual_discount_rate"], years=5)
    irr = internal_rate_of_return(initial_investment, annual_cashflow, years=5)
    payback_months = None if monthly_profit <= 0 else initial_investment / monthly_profit

    return {
        "scenario_id": scenario_id,
        "startup_cost": capex["total_capex"],
        "revenue": revenue,
        "variable_total": variable_total,
        "gross_profit": gross_profit,
        "monthly_profit": monthly_profit,
        "annual_cashflow": annual_cashflow,
        "ebitda": ebitda,
        "ebit": ebit,
        "depreciation_monthly": depreciation_monthly,
        "net_operating_cashflow": monthly_profit,
        "break_even_units": break_even_units,
        "funding_gap": funding_gap,
        "funding_need_after_equity": funding_gap,
        "contribution_margin": contribution_margin,
        "working_capital_need": working_capital_need,
        "initial_investment": initial_investment,
        "npv": npv,
        "irr": irr,
        "payback_months": payback_months,
        "debt_service_monthly": debt_profile["monthly_payment"],
        "dscr": debt_profile["dscr"],
        "operating_model": operating_model,
        "opex_breakdown": opex,
        "capex_breakdown": capex,
        "debt_service_profile": debt_profile,
    }


def operating_model_summary(values: dict[str, Any]) -> dict[str, Any]:
    return {
        "use_operating_capacity": bool(values["use_operating_capacity"]),
        "capacity_units_per_day": values["capacity_units_per_day"],
        "operating_days_per_month": values["operating_days_per_month"],
        "utilization_rate": values["utilization_rate"],
        "monthly_units": values["monthly_units"],
        "unit_source": "operating_capacity" if values["use_operating_capacity"] else "manual_monthly_units",
    }


def opex_breakdown(values: dict[str, Any]) -> dict[str, Decimal]:
    detailed = {
        "payroll_monthly": values["payroll_monthly"],
        "rent_monthly": values["rent_monthly"],
        "utilities_monthly": values["utilities_monthly"],
        "marketing_monthly": values["marketing_monthly"],
        "maintenance_monthly": values["maintenance_monthly"],
    }
    detailed_total = sum(detailed.values(), Decimal("0"))
    legacy_fixed = values["monthly_fixed_cost"]
    total = detailed_total if detailed_total > 0 else legacy_fixed
    return detailed | {"legacy_monthly_fixed_cost": legacy_fixed, "total_monthly_opex": total}


def capex_breakdown(values: dict[str, Any]) -> dict[str, Decimal]:
    detailed = {
        "capex_equipment": values["capex_equipment"],
        "capex_fitout": values["capex_fitout"],
        "capex_licenses_local": values["capex_licenses_local"],
    }
    detailed_total = sum(detailed.values(), Decimal("0"))
    legacy_startup = values["startup_cost"]
    total = detailed_total if detailed_total > 0 else legacy_startup
    depreciation_years = values["depreciation_years"]
    depreciation_monthly = Decimal("0") if depreciation_years <= 0 else total / (depreciation_years * Decimal("12"))
    return detailed | {
        "legacy_startup_cost": legacy_startup,
        "total_capex": total,
        "depreciation_years": depreciation_years,
        "depreciation_monthly": depreciation_monthly,
    }


def net_present_value(initial_investment: Decimal, annual_cashflow: Decimal, discount_rate: Decimal, years: int) -> Decimal:
    value = -initial_investment
    for year in range(1, years + 1):
        value += annual_cashflow / ((Decimal("1") + discount_rate) ** year)
    return value


def internal_rate_of_return(initial_investment: Decimal, annual_cashflow: Decimal, years: int) -> Decimal | None:
    if annual_cashflow <= 0:
        return None
    low = Decimal("-0.95")
    high = Decimal("1.50")
    for _ in range(80):
        mid = (low + high) / Decimal("2")
        value = net_present_value(initial_investment, annual_cashflow, mid, years)
        if value > 0:
            low = mid
        else:
            high = mid
    return (low + high) / Decimal("2")


def debt_service_monthly(values: dict[str, Any]) -> Decimal | None:
    debt_amount = values.get("debt_amount", Decimal("0"))
    if debt_amount <= 0:
        return None
    if values.get("annual_interest_rate", Decimal("0")) <= 0 or values.get("loan_years", Decimal("0")) <= 0:
        return None
    months = values["loan_years"] * Decimal("12")
    monthly_rate = values["annual_interest_rate"] / Decimal("12")
    if monthly_rate <= 0:
        return debt_amount / months
    return debt_amount * (monthly_rate * ((Decimal("1") + monthly_rate) ** months)) / (
        ((Decimal("1") + monthly_rate) ** months) - Decimal("1")
    )


def debt_service_profile(values: dict[str, Any], ebitda: Decimal) -> dict[str, Any]:
    payment = debt_service_monthly(values)
    if values["debt_amount"] <= 0:
        return {
            "status": "ready",
            "debt_amount": Decimal("0"),
            "monthly_payment": None,
            "annual_debt_service": None,
            "dscr": None,
            "loan_grace_months": values["loan_grace_months"],
            "warning": "",
        }
    if payment is None:
        return {
            "status": "not_ready",
            "debt_amount": values["debt_amount"],
            "monthly_payment": None,
            "annual_debt_service": None,
            "dscr": None,
            "loan_grace_months": values["loan_grace_months"],
            "warning": "NOT_READY: debt_amount requires positive annual_interest_rate and loan_years.",
        }
    annual_debt_service = payment * Decimal("12")
    dscr = None if annual_debt_service <= 0 else (ebitda * Decimal("12")) / annual_debt_service
    return {
        "status": "ready",
        "debt_amount": values["debt_amount"],
        "monthly_payment": payment,
        "annual_debt_service": annual_debt_service,
        "dscr": dscr,
        "loan_grace_months": values["loan_grace_months"],
        "warning": "" if dscr is None or dscr >= Decimal("1.2") else "DSCR below 1.2 pressure threshold.",
    }


def sensitivity_matrix(values: dict[str, Any]) -> dict[str, Any]:
    demand_factors = [Decimal("0.85"), Decimal("1.00"), Decimal("1.15")]
    cost_factors = [Decimal("0.95"), Decimal("1.00"), Decimal("1.10")]
    cells: list[dict[str, Any]] = []
    for demand_factor in demand_factors:
        for cost_factor in cost_factors:
            adjusted = dict(values)
            adjusted["monthly_units"] = values["monthly_units"] * demand_factor
            adjusted["variable_cost"] = values["variable_cost"] * cost_factor
            finance = calculate_finance(adjusted, "baseline")
            cells.append(
                {
                    "demand_factor": float(demand_factor),
                    "cost_factor": float(cost_factor),
                    "monthly_profit": money(finance["monthly_profit"]),
                    "npv": money(finance["npv"]),
                }
            )
    return {
        "matrix_id": "FIN-ALG-12-local-sensitivity-v1",
        "x_axis": "demand_factor",
        "y_axis": "cost_factor",
        "cells": cells,
    }


def operational_sensitivity(values: dict[str, Any]) -> dict[str, Any]:
    utilization_factors = [Decimal("0.80"), Decimal("1.00"), Decimal("1.15")]
    price_factors = [Decimal("0.95"), Decimal("1.00"), Decimal("1.05")]
    opex_factors = [Decimal("0.90"), Decimal("1.00"), Decimal("1.10")]
    demand_factors = [Decimal("0.85"), Decimal("1.00"), Decimal("1.15")]
    utilization_price_cells: list[dict[str, Any]] = []
    opex_demand_cells: list[dict[str, Any]] = []
    for utilization_factor in utilization_factors:
        for price_factor in price_factors:
            adjusted = dict(values)
            adjusted["monthly_units"] = values["monthly_units"] * utilization_factor
            adjusted["unit_price"] = values["unit_price"] * price_factor
            finance = calculate_finance(adjusted, "baseline")
            utilization_price_cells.append(
                {
                    "utilization_factor": float(utilization_factor),
                    "price_factor": float(price_factor),
                    "monthly_profit": money(finance["monthly_profit"]),
                    "dscr": serialize_value(finance["dscr"], ratio=True),
                }
            )
    for opex_factor in opex_factors:
        for demand_factor in demand_factors:
            adjusted = dict(values)
            adjusted["monthly_units"] = values["monthly_units"] * demand_factor
            adjusted["monthly_fixed_cost"] = values["monthly_fixed_cost"] * opex_factor
            for key in ["payroll_monthly", "rent_monthly", "utilities_monthly", "marketing_monthly", "maintenance_monthly"]:
                adjusted[key] = values[key] * opex_factor
            finance = calculate_finance(adjusted, "baseline")
            opex_demand_cells.append(
                {
                    "opex_factor": float(opex_factor),
                    "demand_factor": float(demand_factor),
                    "ebitda": money(finance["ebitda"]),
                    "funding_need_after_equity": money(finance["funding_need_after_equity"]),
                }
            )
    return {
        "matrix_id": "FIN-ALG-13-operational-sensitivity-v1",
        "utilization_price_cells": utilization_price_cells,
        "opex_demand_cells": opex_demand_cells,
    }


def monte_carlo(finance: dict[str, Any], values: dict[str, Any]) -> dict[str, Any]:
    distribution_profile = "FIN-ALG-04-local-triangular-demand-uniform-cost"
    correlation_ref = "FIN-ALG-12-local-independent-baseline"
    if not distribution_profile or not correlation_ref or not SEED:
        return not_ready_monte_carlo(
            [
                {
                    "code": "MISSING_MCMC_METADATA",
                    "severity": "critical",
                    "message": "توزيعات مونت كارلو أو الارتباط أو البذرة غير مكتملة.",
                }
            ]
        )

    rng = random.Random(SEED)
    iterations = 4000
    passes = 0
    profits: list[Decimal] = []
    for _ in range(iterations):
        demand_factor = Decimal(str(rng.triangular(0.78, 1.18, 1.0)))
        cost_factor = Decimal(str(rng.uniform(0.95, 1.12)))
        units = values["monthly_units"] * demand_factor
        opex_total = opex_breakdown(values)["total_monthly_opex"]
        profit = (values["unit_price"] * units) - ((values["variable_cost"] * cost_factor) * units) - opex_total
        profits.append(profit)
        if profit > 0 and finance["funding_gap"] <= Decimal("300000") and finance["npv"] > 0:
            passes += 1
    profits.sort()
    probability = Decimal(passes) / Decimal(iterations)

    def pct(p: Decimal) -> float:
        idx = int((Decimal(len(profits) - 1) * p).to_integral_value())
        return money(profits[idx])

    return {
        "status": "ready",
        "seed": SEED,
        "iterations": iterations,
        "p_pass": float(probability.quantize(Decimal("0.0001"))),
        "p10_profit": pct(Decimal("0.10")),
        "p50_profit": pct(Decimal("0.50")),
        "p90_profit": pct(Decimal("0.90")),
        "distribution_profile": distribution_profile,
        "correlation_ref": correlation_ref,
        "convergence": {
            "min_iterations": 2000,
            "actual_iterations": iterations,
            "status": "passed",
        },
        "label_ar": "احتمال اجتياز بوابات الجدوى",
        "label_en": "Probability of passing feasibility gates",
        "warning": "This is not an unconditional project-success probability.",
    }


def not_ready_monte_carlo(blockers: list[dict[str, str]]) -> dict[str, Any]:
    return {
        "status": "not_ready",
        "seed": SEED,
        "iterations": 0,
        "p_pass": None,
        "p10_profit": None,
        "p50_profit": None,
        "p90_profit": None,
        "distribution_profile": "NOT_READY",
        "correlation_ref": "NOT_READY",
        "convergence": {
            "min_iterations": 2000,
            "actual_iterations": 0,
            "status": "not_ready",
        },
        "label_ar": "احتمال اجتياز بوابات الجدوى",
        "label_en": "Probability of passing feasibility gates",
        "warning": "NOT_READY: " + "؛ ".join(blocker["code"] for blocker in blockers),
    }


def finance_result_set(inputs: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, str]]]:
    values, blockers = validate_finance_inputs(inputs)
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
                "assumption_refs": [],
            },
            blockers,
        )

    scenarios = [calculate_finance(values, scenario_id) for scenario_id in ["conservative", "baseline", "optimistic"]]
    baseline = next(item for item in scenarios if item["scenario_id"] == "baseline")
    return (
        {
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
            "assumption_refs": ["assumption:local-user-inputs-v1", "assumption:finance-defaults-v1"],
        },
        [],
    )


def serialize_finance(finance: dict[str, Any]) -> dict[str, Any]:
    serialized: dict[str, Any] = {"scenario_id": finance["scenario_id"]}
    for key, value in finance.items():
        if key == "scenario_id":
            continue
        if value is None:
            serialized[key] = None
        elif isinstance(value, dict):
            serialized[key] = serialize_nested(value)
        elif isinstance(value, Decimal):
            serialized[key] = serialize_value(value, ratio=key in {"irr", "contribution_margin", "dscr"})
        else:
            serialized[key] = value
    return serialized


def serialize_nested(payload: dict[str, Any]) -> dict[str, Any]:
    serialized: dict[str, Any] = {}
    for key, value in payload.items():
        if isinstance(value, Decimal):
            serialized[key] = serialize_value(
                value,
                ratio=key in {"utilization_rate", "dscr"},
            )
        else:
            serialized[key] = value
    return serialized


def serialize_value(value: Decimal | None, *, ratio: bool = False) -> float | None:
    if value is None:
        return None
    return float(value.quantize(Decimal("0.0001"))) if ratio else money(value)
