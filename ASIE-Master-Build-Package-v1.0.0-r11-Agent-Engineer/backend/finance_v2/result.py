from __future__ import annotations

from decimal import Decimal, ROUND_HALF_EVEN
from typing import Any

from .contracts import ValidatedFinanceInput
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
    return result


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
    if not model.periods:
        payload: dict[str, Any] = {
            "status": "not_ready",
            "baseline": None,
            "scenarios": [],
            "sensitivity": None,
            "operational_sensitivity": None,
            "operating_model": None,
            "capex_breakdown": None,
            "opex_breakdown": None,
            "debt_service_profile": None,
            "monte_carlo": {"status": "not_ready", "p_pass": None},
            "assumption_refs": lineage["assumption_refs"],
            "blockers": list(model.blockers),
        }
    else:
        count = Decimal(len(model.periods))
        average = lambda field: sum((getattr(row, field) for row in model.periods), ZERO) / count
        total_capex = sum((row.capex_additions for row in model.periods), ZERO)
        working_capital = max((row.net_working_capital for row in model.periods), default=ZERO)
        funding_need = model.metrics.get("funding_need") or ZERO
        average_revenue = average("revenue")
        average_gross = average("gross_profit")
        contribution_margin = (
            average_gross / average_revenue if average_revenue != ZERO else ZERO
        )
        monthly_units = sum(
            (
                Decimal(point["value"])
                for stream in document["revenue_streams"]
                for point in stream["volume_series"]
            ),
            ZERO,
        ) / Decimal(len(model.periods))
        average_debt_service = sum(
            (
                row.interest_paid + row.principal_paid + row.fees_paid
                for row in model.debt_schedule
            ),
            ZERO,
        ) / Decimal(len(model.periods))
        baseline = {
            "startup_cost": float(_decimal(total_capex, money_scale)),
            "revenue": float(_decimal(average_revenue, money_scale)),
            "variable_total": float(_decimal(average("cogs"), money_scale)),
            "gross_profit": float(_decimal(average_gross, money_scale)),
            "monthly_profit": float(_decimal(average("net_income"), money_scale)),
            "annual_cashflow": float(
                _decimal(
                    sum(
                        (row.equity_cash_flow for row in model.periods[:12]),
                        ZERO,
                    ),
                    money_scale,
                )
            ),
            "ebitda": float(_decimal(average("ebitda"), money_scale)),
            "ebit": float(_decimal(average("ebit"), money_scale)),
            "depreciation_monthly": float(_decimal(average("depreciation"), money_scale)),
            "net_operating_cashflow": float(_decimal(average("cash_from_operations"), money_scale)),
            "break_even_units": _legacy_float(
                model.metrics.get("break_even"), money_scale
            ),
            "funding_gap": float(_decimal(funding_need, money_scale)),
            "funding_need_after_equity": float(_decimal(funding_need, money_scale)),
            "contribution_margin": float(_decimal(contribution_margin, 6)),
            "working_capital_need": float(_decimal(working_capital, money_scale)),
            "initial_investment": float(_decimal(total_capex + working_capital, money_scale)),
            "npv": float(_decimal(model.metrics.get("npv_unlevered") or ZERO, money_scale)),
            "irr": _legacy_float(
                model.metrics.get("irr_unlevered"), ratio_scale
            ),
            "payback_months": _legacy_float(
                model.metrics.get("payback_months"), ratio_scale
            ),
            "debt_service_monthly": float(_decimal(average_debt_service, money_scale)),
            "dscr": _legacy_float(model.metrics.get("dscr_min"), ratio_scale),
        }
        payload = {
            "status": model.status,
            "baseline": baseline,
            "scenarios": [{"scenario_id": "baseline", **baseline}],
            "sensitivity": None,
            "operational_sensitivity": None,
            "operating_model": {
                "monthly_units": float(_decimal(monthly_units, money_scale)),
                "use_operating_capacity": False,
                "utilization_rate": None,
                "source": "finance-result.v2",
            },
            "capex_breakdown": {
                "capex_equipment": 0.0,
                "capex_fitout": 0.0,
                "capex_licenses_local": 0.0,
                "legacy_startup_cost": 0.0,
                "total_capex": float(_decimal(total_capex, money_scale)),
                "depreciation_years": None,
                "depreciation_monthly": float(_decimal(average("depreciation"), money_scale)),
            },
            "opex_breakdown": {
                "payroll_monthly": 0.0,
                "rent_monthly": 0.0,
                "utilities_monthly": 0.0,
                "marketing_monthly": 0.0,
                "maintenance_monthly": 0.0,
                "legacy_monthly_fixed_cost": 0.0,
                "total_monthly_opex": float(_decimal(average("operating_expenses"), money_scale)),
            },
            "debt_service_profile": {
                "status": "ready" if any(row.debt_closing > ZERO for row in model.periods) else "no_debt",
                "dscr": baseline["dscr"],
                "debt_amount": float(_decimal(sum((row.debt_drawdowns for row in model.periods), ZERO), money_scale)),
            },
            "monte_carlo": {"status": "not_ready", "p_pass": None},
            "assumption_refs": lineage["assumption_refs"],
            "blockers": list(model.blockers),
        }
    return {
        "schema_version": "finance.result.v1-compatible",
        "status": "derived",
        "derived_from": "finance-result.v2",
        "payload": payload,
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
    return format(value.quantize(quantum, rounding=ROUND_HALF_EVEN), "f")
