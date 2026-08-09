from __future__ import annotations

from decimal import Decimal
from typing import Any

from .contracts import ValidatedFinanceInput, parse_decimal
from .debt import UnsupportedDebtProfile, build_debt_schedule
from .invariants import evaluate_invariants
from .metrics import irr_annual, llcr, minimum_dscr, mirr_annual, npv_monthly, payback_months
from .model import FinancialModel, FinancialPeriod, ZERO


def build_financial_model(validated: ValidatedFinanceInput) -> FinancialModel:
    document = validated.thaw()
    periods = validated.periods
    blockers: list[dict[str, str]] = []

    try:
        debt = build_debt_schedule(document, periods)
    except UnsupportedDebtProfile as exc:
        debt = tuple()
        blockers.append(_blocker("FIN2_DEBT_PROFILE_UNSUPPORTED", "$.financing", str(exc)))
        return FinancialModel((), debt, (), {}, "not_ready", tuple(blockers))

    if "vat" in document["fiscal_policy"]["modules"]:
        blockers.append(
            _blocker(
                "FIN2_VAT_LEDGER_NOT_READY",
                "$.fiscal_policy.modules",
                "VAT requires input/output tax ledger fields not present in S2-B",
            )
        )

    revenue = _revenue_schedule(document, periods)
    cogs = _cogs_schedule(document, periods)
    opex = _opex_schedule(document, periods)
    capex, depreciation = _capex_schedules(document, periods)
    ar, inventory, ap = _working_capital_schedules(document, periods, revenue, cogs)
    equity = _event_schedule(
        document["financing"]["equity_contributions"], periods, "amount"
    )
    fiscal_rate = _fiscal_rate(document)
    unlevered_fiscal_rate = fiscal_rate

    rows: list[FinancialPeriod] = []
    opening_cash = ZERO
    prior_nwc = ZERO
    ppe_net = ZERO
    retained_earnings = ZERO
    contributed_equity = ZERO

    for index, period in enumerate(periods):
        gross_profit = revenue[index] - cogs[index]
        ebitda = gross_profit - opex[index]
        ppe_net = ppe_net + capex[index] - depreciation[index]
        ebit = ebitda - depreciation[index]
        finance_cost = debt[index].interest_expense + debt[index].fees_paid
        earnings_before_fiscal = ebit - finance_cost
        fiscal_expense = max(ZERO, earnings_before_fiscal) * fiscal_rate
        net_income = earnings_before_fiscal - fiscal_expense

        nwc = ar[index] + inventory[index] - ap[index]
        change_nwc = nwc - prior_nwc
        prior_nwc = nwc

        # Capitalized interest is non-cash; financing fees are classified in CFF.
        cfo = (
            net_income
            + depreciation[index]
            + debt[index].interest_capitalized
            + debt[index].fees_paid
            - change_nwc
        )
        cfi = -capex[index]
        cff = (
            equity[index]
            + debt[index].drawdowns
            - debt[index].principal_paid
            - debt[index].fees_paid
        )
        ending_cash = opening_cash + cfo + cfi + cff

        retained_earnings += net_income
        contributed_equity += equity[index]
        total_assets = ending_cash + ar[index] + inventory[index] + ppe_net
        total_liabilities = ap[index] + debt[index].closing_balance
        total_equity = contributed_equity + retained_earnings

        unlevered_fiscal = max(ZERO, ebit) * unlevered_fiscal_rate
        unlevered = ebit - unlevered_fiscal + depreciation[index] - capex[index] - change_nwc
        equity_flow = cfo + cfi + debt[index].drawdowns - debt[index].principal_paid - debt[index].fees_paid
        cfads = ebitda - fiscal_expense - change_nwc - capex[index]

        rows.append(
            FinancialPeriod(
                period=period,
                revenue=revenue[index],
                cogs=cogs[index],
                gross_profit=gross_profit,
                operating_expenses=opex[index],
                ebitda=ebitda,
                depreciation=depreciation[index],
                ebit=ebit,
                interest_expense=finance_cost,
                fiscal_expense=fiscal_expense,
                net_income=net_income,
                accounts_receivable=ar[index],
                inventory=inventory[index],
                accounts_payable=ap[index],
                net_working_capital=nwc,
                change_in_working_capital=change_nwc,
                capex_additions=capex[index],
                ppe_net=ppe_net,
                equity_contributions=equity[index],
                debt_drawdowns=debt[index].drawdowns,
                principal_paid=debt[index].principal_paid,
                financing_fees=debt[index].fees_paid,
                debt_closing=debt[index].closing_balance,
                cash_from_operations=cfo,
                cash_from_investing=cfi,
                cash_from_financing=cff,
                opening_cash=opening_cash,
                ending_cash=ending_cash,
                retained_earnings=retained_earnings,
                total_assets=total_assets,
                total_liabilities=total_liabilities,
                total_equity=total_equity,
                unlevered_fcf=unlevered,
                equity_cash_flow=equity_flow,
                cfads=cfads,
            )
        )
        opening_cash = ending_cash

    period_rows = tuple(rows)
    invariants = evaluate_invariants(period_rows, debt)
    failed = [item for item in invariants if item.status == "failed"]
    blockers.extend(
        _blocker(
            f"FIN2_INVARIANT_{item.invariant_id.upper()}",
            "$.statements",
            item.reason,
        )
        for item in failed
    )

    valuation = document["valuation_policy"]
    discount = parse_decimal(valuation["discount_rate_annual"], "$.valuation_policy.discount_rate_annual", allow_negative=False)
    finance_rate = parse_decimal(valuation["finance_rate_annual"], "$.valuation_policy.finance_rate_annual", allow_negative=False)
    reinvestment = parse_decimal(valuation["reinvestment_rate_annual"], "$.valuation_policy.reinvestment_rate_annual", allow_negative=False)
    unlevered_flows = tuple(row.unlevered_fcf for row in period_rows)
    cfads = tuple(row.cfads for row in period_rows)
    debt_service = tuple(
        item.interest_paid + item.principal_paid + item.fees_paid for item in debt
    )
    total_debt = sum((item.drawdowns for item in debt), ZERO)
    ending_cash_values = tuple(row.ending_cash for row in period_rows)

    metrics: dict[str, Decimal | None] = {
        "npv_unlevered": npv_monthly(unlevered_flows, discount),
        "irr_unlevered": irr_annual(unlevered_flows),
        "mirr_unlevered": mirr_annual(unlevered_flows, finance_rate, reinvestment),
        "payback_months": payback_months(unlevered_flows),
        "break_even": _break_even(document, periods, opex),
        "funding_need": max(ZERO, -min(ending_cash_values, default=ZERO)),
        "dscr_min": minimum_dscr(cfads, debt_service),
        "llcr": llcr(cfads, debt_service, total_debt, discount),
    }
    status = "not_ready" if blockers else "ready"
    return FinancialModel(
        periods=period_rows,
        debt_schedule=debt,
        invariants=invariants,
        metrics=metrics,
        status=status,
        blockers=tuple(blockers),
    )


def _revenue_schedule(document: dict[str, Any], periods: tuple[str, ...]) -> tuple[Decimal, ...]:
    values = [ZERO for _ in periods]
    for stream in document["revenue_streams"]:
        volume = _series(stream["volume_series"])
        price = _series(stream["price_series"])
        for index, period in enumerate(periods):
            values[index] += volume[period] * price[period]
    return tuple(values)


def _cogs_schedule(document: dict[str, Any], periods: tuple[str, ...]) -> tuple[Decimal, ...]:
    values = [ZERO for _ in periods]
    for stream in document["revenue_streams"]:
        volume = _series(stream["volume_series"])
        variable = _series(stream["variable_cost_series"])
        for index, period in enumerate(periods):
            values[index] += volume[period] * variable[period]
    return tuple(values)


def _opex_schedule(document: dict[str, Any], periods: tuple[str, ...]) -> tuple[Decimal, ...]:
    values = [ZERO for _ in periods]
    for cost in document["operating_costs"]:
        schedule = _series(cost["schedule"])
        for index, period in enumerate(periods):
            values[index] += schedule[period]
    return tuple(values)


def _capex_schedules(
    document: dict[str, Any],
    periods: tuple[str, ...],
) -> tuple[tuple[Decimal, ...], tuple[Decimal, ...]]:
    additions = [ZERO for _ in periods]
    depreciation = [ZERO for _ in periods]
    period_to_index = {period: index for index, period in enumerate(periods)}
    for asset in document["capex_assets"]:
        acquisition = period_to_index[asset["acquisition_period"]]
        cost = parse_decimal(asset["cost"], f"asset:{asset['asset_id']}.cost", allow_negative=False)
        residual = parse_decimal(asset["residual_value"], f"asset:{asset['asset_id']}.residual", allow_negative=False)
        if residual > cost:
            raise ValueError(f"{asset['asset_id']}: residual value exceeds cost")
        additions[acquisition] += cost
        monthly = (cost - residual) / Decimal(asset["useful_life_months"])
        stop = min(len(periods), acquisition + asset["useful_life_months"])
        for index in range(acquisition, stop):
            depreciation[index] += monthly
    return tuple(additions), tuple(depreciation)


def _working_capital_schedules(
    document: dict[str, Any],
    periods: tuple[str, ...],
    revenue: tuple[Decimal, ...],
    cogs: tuple[Decimal, ...],
) -> tuple[tuple[Decimal, ...], tuple[Decimal, ...], tuple[Decimal, ...]]:
    policy = document["working_capital"]
    if policy["mode"] == "explicit_schedule":
        return (
            tuple(_series(policy["accounts_receivable"])[period] for period in periods),
            tuple(_series(policy["inventory"])[period] for period in periods),
            tuple(_series(policy["accounts_payable"])[period] for period in periods),
        )
    dso = parse_decimal(policy["dso_days"], "$.working_capital.dso_days", allow_negative=False)
    dio = parse_decimal(policy["dio_days"], "$.working_capital.dio_days", allow_negative=False)
    dpo = parse_decimal(policy["dpo_days"], "$.working_capital.dpo_days", allow_negative=False)
    days = Decimal(30)
    return (
        tuple(value * dso / days for value in revenue),
        tuple(value * dio / days for value in cogs),
        tuple(value * dpo / days for value in cogs),
    )


def _event_schedule(
    events: list[dict[str, Any]],
    periods: tuple[str, ...],
    value_key: str,
) -> tuple[Decimal, ...]:
    values = {period: ZERO for period in periods}
    for event in events:
        values[event["period"]] += parse_decimal(
            event[value_key], f"event:{event['period']}.{value_key}", allow_negative=False
        )
    return tuple(values[period] for period in periods)


def _fiscal_rate(document: dict[str, Any]) -> Decimal:
    policy = document["fiscal_policy"]
    rate = ZERO
    if "income_tax" in policy["modules"]:
        rate += parse_decimal(policy["income_tax_rate"], "$.fiscal_policy.income_tax_rate", allow_negative=False)
    if "zakat" in policy["modules"]:
        rate += parse_decimal(policy["zakat_rate"], "$.fiscal_policy.zakat_rate", allow_negative=False)
    if rate > Decimal(1):
        raise ValueError("combined fiscal rate exceeds 1")
    return rate


def _break_even(
    document: dict[str, Any],
    periods: tuple[str, ...],
    opex: tuple[Decimal, ...],
) -> Decimal | None:
    if not all(stream["model_kind"] == "product_unit" for stream in document["revenue_streams"]):
        return None
    total_volume = ZERO
    total_contribution = ZERO
    for stream in document["revenue_streams"]:
        volume = _series(stream["volume_series"])
        price = _series(stream["price_series"])
        variable = _series(stream["variable_cost_series"])
        for period in periods:
            total_volume += volume[period]
            total_contribution += volume[period] * (price[period] - variable[period])
    if total_volume <= ZERO:
        return None
    contribution_per_unit = total_contribution / total_volume
    if contribution_per_unit <= ZERO:
        return None
    average_opex = sum(opex, ZERO) / Decimal(len(opex))
    return average_opex / contribution_per_unit


def _series(rows: list[dict[str, str]]) -> dict[str, Decimal]:
    return {
        row["period"]: parse_decimal(row["value"], f"series:{row['period']}")
        for row in rows
    }


def _blocker(code: str, field_ref: str, message: str) -> dict[str, str]:
    return {
        "code": code,
        "severity": "high",
        "field_ref": field_ref,
        "message_ar": message,
    }
