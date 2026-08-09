from __future__ import annotations

from decimal import Decimal, ROUND_HALF_EVEN
from typing import Any

from .contracts import ValidatedFinanceInput
from .model import FinancialModel, FinancialPeriod, ZERO


ENGINE_VERSION = "2.0.0-dark.1"


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
                    "period": period,
                    **{
                        field: _decimal(getattr(row, field), money_scale)
                        for field in row.__dataclass_fields__
                    },
                }
                for period, row in zip(validated.periods, model.debt_schedule, strict=True)
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
            key: None if value is None else _decimal(
                value,
                money_scale if key in {"npv_unlevered", "funding_need", "break_even"} else ratio_scale,
            )
            for key, value in model.metrics.items()
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
                    key: None if value is None else _decimal(value, ratio_scale)
                    for key, value in model.metrics.items()
                },
            }
        ],
        "lineage": {
            **lineage,
            "formula_registry_version": ENGINE_VERSION,
        },
        "blockers": list(model.blockers),
        "legacy_projection": (
            _legacy_projection(model, document, lineage, money_scale)
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
    scale: int,
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
            "startup_cost": float(_decimal(total_capex, scale)),
            "revenue": float(_decimal(average_revenue, scale)),
            "variable_total": float(_decimal(average("cogs"), scale)),
            "gross_profit": float(_decimal(average_gross, scale)),
            "monthly_profit": float(_decimal(average("net_income"), scale)),
            "annual_cashflow": float(_decimal(sum((row.equity_cash_flow for row in model.periods), ZERO), scale)),
            "ebitda": float(_decimal(average("ebitda"), scale)),
            "ebit": float(_decimal(average("ebit"), scale)),
            "depreciation_monthly": float(_decimal(average("depreciation"), scale)),
            "net_operating_cashflow": float(_decimal(average("cash_from_operations"), scale)),
            "break_even_units": None if model.metrics.get("break_even") is None else float(model.metrics["break_even"]),
            "funding_gap": float(_decimal(funding_need, scale)),
            "funding_need_after_equity": float(_decimal(funding_need, scale)),
            "contribution_margin": float(_decimal(contribution_margin, 6)),
            "working_capital_need": float(_decimal(working_capital, scale)),
            "initial_investment": float(_decimal(total_capex + working_capital, scale)),
            "npv": float(_decimal(model.metrics.get("npv_unlevered") or ZERO, scale)),
            "irr": None if model.metrics.get("irr_unlevered") is None else float(model.metrics["irr_unlevered"]),
            "payback_months": None if model.metrics.get("payback_months") is None else float(model.metrics["payback_months"]),
            "debt_service_monthly": float(_decimal(average_debt_service, scale)),
            "dscr": None if model.metrics.get("dscr_min") is None else float(model.metrics["dscr_min"]),
        }
        payload = {
            "status": model.status,
            "baseline": baseline,
            "scenarios": [{"scenario_id": "baseline", **baseline}],
            "sensitivity": None,
            "operational_sensitivity": None,
            "operating_model": {
                "monthly_units": float(_decimal(monthly_units, scale)),
                "use_operating_capacity": False,
                "utilization_rate": None,
                "source": "finance-result.v2",
            },
            "capex_breakdown": {
                "capex_equipment": 0.0,
                "capex_fitout": 0.0,
                "capex_licenses_local": 0.0,
                "legacy_startup_cost": 0.0,
                "total_capex": float(_decimal(total_capex, scale)),
                "depreciation_years": None,
                "depreciation_monthly": float(_decimal(average("depreciation"), scale)),
            },
            "opex_breakdown": {
                "payroll_monthly": 0.0,
                "rent_monthly": 0.0,
                "utilities_monthly": 0.0,
                "marketing_monthly": 0.0,
                "maintenance_monthly": 0.0,
                "legacy_monthly_fixed_cost": 0.0,
                "total_monthly_opex": float(_decimal(average("operating_expenses"), scale)),
            },
            "debt_service_profile": {
                "status": "ready" if any(row.debt_closing > ZERO for row in model.periods) else "no_debt",
                "dscr": baseline["dscr"],
                "debt_amount": float(_decimal(sum((row.debt_drawdowns for row in model.periods), ZERO), scale)),
            },
            "monte_carlo": {"status": "not_ready", "p_pass": None},
            "assumption_refs": [],
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


def _decimal(value: Decimal, scale: int) -> str:
    quantum = Decimal(1).scaleb(-scale)
    return format(value.quantize(quantum, rounding=ROUND_HALF_EVEN), "f")
