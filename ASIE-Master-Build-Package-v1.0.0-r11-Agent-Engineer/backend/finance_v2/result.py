from __future__ import annotations

from decimal import Decimal, ROUND_HALF_EVEN, localcontext
from math import isfinite
from typing import Any

from .contracts import FinanceContractError, ValidatedFinanceInput
from .model import FinancialModel, FinancialPeriod, ZERO


ENGINE_VERSION = "2.0.0-dark.1"
_METRIC_KEYS = (
    "npv_unlevered",
    "irr_unlevered",
    "mirr_unlevered",
    "payback_months",
    "break_even",
    "funding_need",
    "dscr_min",
    "llcr",
)


def serialize_finance_result(
    validated: ValidatedFinanceInput,
    model: FinancialModel,
    *,
    include_legacy_projection: bool = False,
) -> dict[str, Any]:
    if model.source_input_hash != validated.input_hash:
        raise FinanceContractError(
            "FIN2_MODEL_INPUT_MISMATCH",
            "$.input_hash",
            "financial model was built from a different validated input",
        )
    document = validated.thaw()
    rounding = document["rounding_policy"]
    money_scale = rounding["money_scale"]
    ratio_scale = rounding["ratio_scale"]
    lineage = _collect_lineage(document)

    result = {
        "schema_version": "finance-result.v2",
        "engine_version": ENGINE_VERSION,
        "status": model.status,
        "organization_id": validated.organization_id,
        "project_id": validated.project_id,
        "run_id": validated.run_id,
        "input_document_id": validated.document_id,
        "input_hash": validated.input_hash,
        "archetype_ref": document["archetype_ref"],
        "currency": validated.currency,
        "periods": list(validated.periods),
        "rounding_policy": rounding,
        "statements": {
            "income_statement": _statement(
                model.periods,
                {
                    "revenue": "revenue",
                    "cost_of_goods_sold": "cogs",
                    "gross_profit": "gross_profit",
                    "operating_expenses": "operating_expenses",
                    "ebitda": "ebitda",
                    "depreciation": "depreciation",
                    "ebit": "ebit",
                    "finance_cost": "interest_expense",
                    "fiscal_expense": "fiscal_expense",
                    "net_income": "net_income",
                },
                money_scale,
                "income",
            ),
            "balance_sheet": _statement(
                model.periods,
                {
                    "cash": "ending_cash",
                    "accounts_receivable": "accounts_receivable",
                    "inventory": "inventory",
                    "ppe_net": "ppe_net",
                    "total_assets": "total_assets",
                    "accounts_payable": "accounts_payable",
                    "debt": "debt_closing",
                    "total_liabilities": "total_liabilities",
                    "contributed_equity": "equity_contributions",
                    "retained_earnings": "retained_earnings",
                    "total_equity": "total_equity",
                },
                money_scale,
                "balance",
                cumulative_equity=True,
            ),
            "cash_flow_statement": _statement(
                model.periods,
                {
                    "opening_cash": "opening_cash",
                    "cash_from_operations": "cash_from_operations",
                    "cash_from_investing": "cash_from_investing",
                    "cash_from_financing": "cash_from_financing",
                    "ending_cash": "ending_cash",
                    "capex": "capex_additions",
                    "debt_drawdowns": "debt_drawdowns",
                    "principal_paid": "principal_paid",
                },
                money_scale,
                "cashflow",
            ),
        },
        "cash_flows": {
            "unlevered_fcf": [_decimal(row.unlevered_fcf, money_scale) for row in model.periods],
            "equity_cash_flow": [_decimal(row.equity_cash_flow, money_scale) for row in model.periods],
            "cfads": [_decimal(row.cfads, money_scale) for row in model.periods],
        },
        "subledgers": {
            "capex": [
                {
                    "period": row.period,
                    "additions": _decimal(row.capex_additions, money_scale),
                    "depreciation": _decimal(row.depreciation, money_scale),
                    "ppe_net": _decimal(row.ppe_net, money_scale),
                }
                for row in model.periods
            ],
            "working_capital": [
                {
                    "period": row.period,
                    "accounts_receivable": _decimal(row.accounts_receivable, money_scale),
                    "inventory": _decimal(row.inventory, money_scale),
                    "accounts_payable": _decimal(row.accounts_payable, money_scale),
                    "change_in_working_capital": _decimal(row.change_in_working_capital, money_scale),
                }
                for row in model.periods
            ],
            "debt": [
                {
                    "period": period_row.period,
                    **{
                        field: _decimal(getattr(debt_row, field), money_scale)
                        for field in debt_row.__dataclass_fields__
                    },
                }
                for period_row, debt_row in zip(
                    model.periods, model.debt_schedule, strict=True
                )
            ],
            "fiscal": [
                {
                    "period": row.period,
                    "expense": _decimal(row.fiscal_expense, money_scale),
                }
                for row in model.periods
            ],
        },
        "metrics": {
            key: _metric_decimal(
                key, model.metrics.get(key), money_scale, ratio_scale
            )
            for key in _METRIC_KEYS
        },
        "invariants": [
            {
                "invariant_id": item.invariant_id,
                "status": item.status,
                "tolerance": _decimal(item.tolerance, money_scale),
                "maximum_variance": _decimal(item.maximum_variance, money_scale),
                "period_refs": list(item.period_refs),
                "reason": item.reason,
            }
            for item in model.invariants
        ],
        "scenarios": [
            {
                "scenario_id": "scn_baseline",
                "status": model.status,
                "metrics": {
                    key: _metric_decimal(
                        key, model.metrics.get(key), money_scale, ratio_scale
                    )
                    for key in _METRIC_KEYS
                },
            }
        ],
        "lineage": {
            **lineage,
            "formula_registry_version": ENGINE_VERSION,
        },
        "blockers": list(model.blockers),
        "legacy_projection": (
            _legacy_projection(
                model, document, lineage, money_scale, ratio_scale
            )
            if include_legacy_projection
            else {
                "schema_version": "finance.result.v1-compatible",
                "status": "not_available",
                "derived_from": "finance-result.v2",
                "payload": {},
            }
        ),
    }
    if include_legacy_projection:
        _apply_legacy_parity(result, money_scale, ratio_scale)
    return result


def _apply_legacy_parity(
    result: dict[str, Any],
    money_scale: int,
    ratio_scale: int,
) -> None:
    payload = result["legacy_projection"]["payload"]
    baseline = payload.get("baseline")
    if baseline is None:
        return
    pairs = (
        ("npv", "npv_unlevered", money_scale),
        ("irr", "irr_unlevered", ratio_scale),
        ("payback_months", "payback_months", ratio_scale),
        ("break_even_units", "break_even", money_scale),
        ("funding_gap", "funding_need", money_scale),
        ("funding_need_after_equity", "funding_need", money_scale),
        ("dscr", "dscr_min", ratio_scale),
    )
    maximum = ZERO
    failed = False
    for legacy_key, metric_key, scale in pairs:
        actual = baseline[legacy_key]
        expected = result["metrics"][metric_key]
        if actual is None or expected is None:
            failed = failed or actual is not None or expected is not None
            continue
        expected_float = float(_decimal(Decimal(expected), scale))
        if not isfinite(expected_float) or not isfinite(float(actual)):
            failed = True
            continue
        variance = abs(
            Decimal(str(actual)) - Decimal(str(expected_float))
        )
        maximum = max(maximum, variance)
        failed = failed or variance != ZERO

    for invariant in result["invariants"]:
        if invariant["invariant_id"] != "legacy_projection_parity":
            continue
        invariant["status"] = "failed" if failed else "passed"
        invariant["maximum_variance"] = _decimal(
            maximum, max(money_scale, ratio_scale)
        )
        invariant["reason"] = (
            "derived_legacy_projection_mismatch" if failed else ""
        )
        break

    if failed:
        result["status"] = "not_ready"
        for scenario in result["scenarios"]:
            scenario["status"] = "not_ready"
        result["blockers"].append(
            {
                "code": "FIN2_INVARIANT_LEGACY_PROJECTION_PARITY",
                "severity": "high",
                "field_ref": "$.legacy_projection.payload.baseline",
                "message_ar": "فشل تطابق الإسقاط المشتق مع نتيجة Finance v2.",
            }
        )


def _statement(
    periods: tuple[FinancialPeriod, ...],
    lines: dict[str, str],
    scale: int,
    formula_prefix: str,
    *,
    cumulative_equity: bool = False,
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    cumulative = ZERO
    for line_id, field in lines.items():
        values = []
        for row in periods:
            value = getattr(row, field)
            if cumulative_equity and line_id == "contributed_equity":
                cumulative += value
                value = cumulative
            values.append({"period": row.period, "value": _decimal(value, scale)})
        if cumulative_equity and line_id == "contributed_equity":
            cumulative = ZERO
        output.append(
            {
                "line_id": line_id,
                "values": values,
                "formula_id": f"fin2.{formula_prefix}.{line_id}.v1",
                "input_refs": [f"finance-model-input.v2:{field}"],
            }
        )
    return output


def _legacy_projection(
    model: FinancialModel,
    document: dict[str, Any],
    lineage: dict[str, list[str]],
    money_scale: int,
    ratio_scale: int,
) -> dict[str, Any]:
    monte_carlo = _legacy_not_ready_monte_carlo()
    if not model.periods:
        payload = _legacy_unavailable_payload(
            lineage,
            list(model.blockers),
            monte_carlo,
        )
    elif model.metrics.get("break_even") is None:
        payload = _legacy_unavailable_payload(
            lineage,
            [
                *model.blockers,
                {
                    "code": "FIN2_LEGACY_BREAK_EVEN_UNAVAILABLE",
                    "severity": "high",
                    "field_ref": "$.metrics.break_even",
                    "message_ar": "لا يمكن تمثيل نقطة التعادل المطلوبة في عقد v1.",
                },
            ],
            monte_carlo,
        )
    elif not _legacy_numbers_supported(model, document):
        payload = _legacy_unavailable_payload(
            lineage,
            [
                *model.blockers,
                {
                    "code": "FIN2_LEGACY_NUMBER_RANGE",
                    "severity": "high",
                    "field_ref": "$.legacy_projection",
                    "message_ar": "تتجاوز قيمة مالية نطاق الأرقام الآمن لعقد v1.",
                },
            ],
            monte_carlo,
        )
    else:
        count = Decimal(len(model.periods))
        average = (
            lambda field: sum(
                (getattr(row, field) for row in model.periods), ZERO
            )
            / count
        )
        total_capex = sum((row.capex_additions for row in model.periods), ZERO)
        working_capital = max(
            (row.net_working_capital for row in model.periods), default=ZERO
        )
        funding_need = model.metrics.get("funding_need") or ZERO
        average_revenue = average("revenue")
        average_gross = average("gross_profit")
        contribution_margin = (
            average_gross / average_revenue
            if average_revenue != ZERO
            else ZERO
        )
        monthly_units = sum(
            (
                Decimal(point["value"])
                for stream in document["revenue_streams"]
                for point in stream["volume_series"]
            ),
            ZERO,
        ) / count
        scheduled_debt_payment = tuple(
            row.interest_paid + row.principal_paid
            for row in model.debt_schedule
        )
        active_debt_payments = tuple(
            value for value in scheduled_debt_payment if value > ZERO
        )
        debt_amount = sum(
            (row.debt_drawdowns for row in model.periods), ZERO
        )
        has_debt = debt_amount > ZERO or any(
            row.debt_closing > ZERO for row in model.periods
        )
        representative_monthly_payment = (
            sum(active_debt_payments, ZERO)
            / Decimal(len(active_debt_payments))
            if active_debt_payments
            else ZERO
        )
        first_year_debt_service = sum(
            scheduled_debt_payment[:12], ZERO
        )
        depreciation_monthly = average("depreciation")
        depreciation_years = (
            ZERO
            if depreciation_monthly <= ZERO
            else total_capex / (depreciation_monthly * Decimal("12"))
        )
        loan_grace_months = max(
            (
                int(row["principal_grace_months"])
                for row in document["financing"]["debt_tranches"]
            ),
            default=0,
        )

        operating_model = {
            "use_operating_capacity": False,
            "capacity_units_per_day": 0.0,
            "operating_days_per_month": 0.0,
            "utilization_rate": 0.0,
            "monthly_units": float(_decimal(monthly_units, money_scale)),
            "unit_source": "manual_monthly_units",
        }
        capex_breakdown = {
            "capex_equipment": 0.0,
            "capex_fitout": 0.0,
            "capex_licenses_local": 0.0,
            "legacy_startup_cost": float(
                _decimal(total_capex, money_scale)
            ),
            "total_capex": float(_decimal(total_capex, money_scale)),
            "depreciation_years": float(
                _decimal(depreciation_years, ratio_scale)
            ),
            "depreciation_monthly": float(
                _decimal(depreciation_monthly, money_scale)
            ),
        }
        opex_breakdown = {
            "payroll_monthly": 0.0,
            "rent_monthly": 0.0,
            "utilities_monthly": 0.0,
            "marketing_monthly": 0.0,
            "maintenance_monthly": 0.0,
            "legacy_monthly_fixed_cost": float(
                _decimal(average("operating_expenses"), money_scale)
            ),
            "total_monthly_opex": float(
                _decimal(average("operating_expenses"), money_scale)
            ),
        }
        dscr = _legacy_float(model.metrics.get("dscr_min"), ratio_scale)
        debt_service_profile = {
            "status": "ready",
            "debt_amount": float(_decimal(debt_amount, money_scale)),
            "monthly_payment": (
                float(
                    _decimal(
                        representative_monthly_payment, money_scale
                    )
                )
                if has_debt
                else None
            ),
            "annual_debt_service": (
                float(_decimal(first_year_debt_service, money_scale))
                if has_debt
                else None
            ),
            "dscr": dscr,
            "loan_grace_months": loan_grace_months,
            "warning": (
                ""
                if not has_debt or dscr is None or dscr >= 1.2
                else "DSCR below 1.2 pressure threshold."
            ),
        }
        baseline = {
            "scenario_id": "baseline",
            "startup_cost": float(_decimal(total_capex, money_scale)),
            "revenue": float(_decimal(average_revenue, money_scale)),
            "variable_total": float(
                _decimal(average("cogs"), money_scale)
            ),
            "gross_profit": float(_decimal(average_gross, money_scale)),
            "monthly_profit": float(
                _decimal(average("net_income"), money_scale)
            ),
            "annual_cashflow": float(
                _decimal(
                    sum(
                        (
                            row.equity_cash_flow
                            for row in model.periods[:12]
                        ),
                        ZERO,
                    ),
                    money_scale,
                )
            ),
            "ebitda": float(_decimal(average("ebitda"), money_scale)),
            "ebit": float(_decimal(average("ebit"), money_scale)),
            "depreciation_monthly": capex_breakdown[
                "depreciation_monthly"
            ],
            "net_operating_cashflow": float(
                _decimal(average("cash_from_operations"), money_scale)
            ),
            "break_even_units": _legacy_float(
                model.metrics.get("break_even"), money_scale
            ),
            "funding_gap": float(_decimal(funding_need, money_scale)),
            "funding_need_after_equity": float(
                _decimal(funding_need, money_scale)
            ),
            "contribution_margin": float(
                _decimal(contribution_margin, ratio_scale)
            ),
            "working_capital_need": float(
                _decimal(working_capital, money_scale)
            ),
            "initial_investment": float(
                _decimal(total_capex + working_capital, money_scale)
            ),
            "npv": float(
                _decimal(
                    model.metrics.get("npv_unlevered") or ZERO,
                    money_scale,
                )
            ),
            "irr": _legacy_float(
                model.metrics.get("irr_unlevered"), ratio_scale
            ),
            "payback_months": _legacy_float(
                model.metrics.get("payback_months"), ratio_scale
            ),
            "debt_service_monthly": debt_service_profile[
                "monthly_payment"
            ],
            "dscr": dscr,
            "operating_model": operating_model,
            "capex_breakdown": capex_breakdown,
            "opex_breakdown": opex_breakdown,
            "debt_service_profile": debt_service_profile,
        }
        payload = {
            "status": model.status,
            "baseline": baseline,
            "scenarios": [dict(baseline)],
            "sensitivity": None,
            "operational_sensitivity": None,
            "operating_model": operating_model,
            "capex_breakdown": capex_breakdown,
            "opex_breakdown": opex_breakdown,
            "debt_service_profile": debt_service_profile,
            "monte_carlo": monte_carlo,
            "assumption_refs": lineage["assumption_refs"],
            "blockers": list(model.blockers),
        }
    return {
        "schema_version": "finance.result.v1-compatible",
        "status": "derived",
        "derived_from": "finance-result.v2",
        "payload": payload,
    }


def _legacy_unavailable_payload(
    lineage: dict[str, list[str]],
    blockers: list[dict[str, Any]],
    monte_carlo: dict[str, Any],
) -> dict[str, Any]:
    return {
        "status": "not_ready",
        "baseline": None,
        "scenarios": [],
        "sensitivity": None,
        "operational_sensitivity": None,
        "operating_model": None,
        "capex_breakdown": None,
        "opex_breakdown": None,
        "debt_service_profile": None,
        "monte_carlo": monte_carlo,
        "assumption_refs": lineage["assumption_refs"],
        "blockers": blockers,
    }


def _legacy_numbers_supported(
    model: FinancialModel,
    document: dict[str, Any],
) -> bool:
    values: list[Decimal] = []
    for row in (*model.periods, *model.debt_schedule):
        values.extend(
            value
            for field in row.__dataclass_fields__
            if isinstance((value := getattr(row, field)), Decimal)
        )
    values.extend(
        value for value in model.metrics.values() if isinstance(value, Decimal)
    )

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)
        elif isinstance(value, str):
            candidate = value.removeprefix("-")
            if (
                candidate.count(".") <= 1
                and candidate.replace(".", "").isdigit()
            ):
                values.append(Decimal(value))

    walk(document)
    try:
        return all(isfinite(float(value)) for value in values)
    except (OverflowError, ValueError):
        return False


def _legacy_not_ready_monte_carlo() -> dict[str, Any]:
    return {
        "status": "not_ready",
        "seed": 0,
        "iterations": 0,
        "p_pass": None,
        "p10_profit": None,
        "p50_profit": None,
        "p90_profit": None,
        "distribution_profile": "NOT_READY",
        "correlation_ref": "NOT_READY",
        "convergence": {
            "min_iterations": 0,
            "actual_iterations": 0,
            "status": "not_ready",
        },
        "label_ar": "احتمال اجتياز بوابات الجدوى",
        "label_en": "Probability of passing feasibility gates",
        "warning": "NOT_READY: FIN2_SIMULATION_NOT_READY",
    }

def _collect_lineage(document: dict[str, Any]) -> dict[str, list[str]]:
    assumptions: set[str] = set()
    evidence: set[str] = set()

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            if set(value) >= {"assumption_refs", "evidence_refs"}:
                assumptions.update(value["assumption_refs"])
                evidence.update(value["evidence_refs"])
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(document)
    return {
        "assumption_refs": sorted(assumptions),
        "evidence_refs": sorted(evidence),
    }


def _metric_decimal(
    key: str,
    value: Decimal | None,
    money_scale: int,
    ratio_scale: int,
) -> str | None:
    if value is None:
        return None
    scale = (
        money_scale
        if key in {"npv_unlevered", "funding_need", "break_even"}
        else ratio_scale
    )
    return _decimal(value, scale)


def _legacy_float(value: Decimal | None, scale: int) -> float | None:
    return None if value is None else float(_decimal(value, scale))


def _decimal(value: Decimal, scale: int) -> str:
    quantum = Decimal(1).scaleb(-scale)
    coefficient_digits = len(value.as_tuple().digits)
    integer_digits = max(1, value.adjusted() + 1)
    with localcontext() as context:
        context.prec = max(
            28,
            coefficient_digits + scale + 4,
            integer_digits + scale + 4,
        )
        rounded = value.quantize(quantum, rounding=ROUND_HALF_EVEN)
    return format(rounded, "f")
