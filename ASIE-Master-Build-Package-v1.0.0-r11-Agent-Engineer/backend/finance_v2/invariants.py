from __future__ import annotations

from decimal import Decimal
from typing import Callable

from .model import DebtPeriod, FinancialPeriod, InvariantResult, ZERO
from .timeline import add_months


TOLERANCE = Decimal("0.01")


def evaluate_invariants(
    periods: tuple[FinancialPeriod, ...],
    debt: tuple[DebtPeriod, ...],
) -> tuple[InvariantResult, ...]:
    results = [
        _period_invariant(
            "balance_equation",
            periods,
            lambda row, _index: row.total_assets
            - row.total_liabilities
            - row.total_equity,
        ),
        _period_invariant(
            "cash_statement_balance_sheet",
            periods,
            lambda row, _index: row.ending_cash
            - (
                row.opening_cash
                + row.cash_from_operations
                + row.cash_from_investing
                + row.cash_from_financing
            ),
        ),
        _period_invariant(
            "cash_rollforward",
            periods,
            lambda row, index: row.opening_cash
            - (periods[index - 1].ending_cash if index else ZERO),
        ),
        _period_invariant(
            "retained_earnings_rollforward",
            periods,
            lambda row, index: row.retained_earnings
            - ((periods[index - 1].retained_earnings if index else ZERO) + row.net_income),
        ),
        _period_invariant(
            "ppe_rollforward",
            periods,
            lambda row, index: row.ppe_net
            - (
                (periods[index - 1].ppe_net if index else ZERO)
                + row.capex_additions
                - row.depreciation
            ),
        ),
        _period_invariant(
            "debt_rollforward",
            periods,
            lambda row, index: row.debt_closing
            - (
                (periods[index - 1].debt_closing if index else ZERO)
                + debt[index].drawdowns
                + debt[index].interest_capitalized
                - debt[index].principal_paid
            ),
        ),
        _sources_uses(periods),
        _period_invariant(
            "gross_profit_equation",
            periods,
            lambda row, _index: row.gross_profit - row.revenue + row.cogs,
        ),
        _period_invariant(
            "ebit_equation",
            periods,
            lambda row, _index: row.ebit - row.ebitda + row.depreciation,
        ),
        _period_invariant(
            "cash_flow_equation",
            periods,
            lambda row, _index: row.ending_cash
            - row.opening_cash
            - row.cash_from_operations
            - row.cash_from_investing
            - row.cash_from_financing,
        ),
        _finite_numbers(periods, debt),
        _period_order(periods),
        InvariantResult(
            invariant_id="legacy_projection_parity",
            status="not_applicable",
            maximum_variance=ZERO,
            tolerance=TOLERANCE,
            period_refs=(),
            reason="S2-B dark build has no legacy projection",
        ),
        InvariantResult(
            invariant_id="deterministic_replay",
            status="not_applicable",
            maximum_variance=ZERO,
            tolerance=TOLERANCE,
            period_refs=(),
            reason="proved by replay tests outside a single model result",
        ),
    ]
    return tuple(results)


def _period_invariant(
    invariant_id: str,
    periods: tuple[FinancialPeriod, ...],
    variance: Callable[[FinancialPeriod, int], Decimal],
) -> InvariantResult:
    failures: list[str] = []
    maximum = ZERO
    for index, row in enumerate(periods):
        current = abs(variance(row, index))
        maximum = max(maximum, current)
        if current > TOLERANCE:
            failures.append(row.period)
    return InvariantResult(
        invariant_id=invariant_id,
        status="failed" if failures else "passed",
        maximum_variance=maximum,
        tolerance=TOLERANCE,
        period_refs=tuple(failures),
        reason="variance_exceeds_tolerance" if failures else "",
    )


def _sources_uses(periods: tuple[FinancialPeriod, ...]) -> InvariantResult:
    sources = sum(
        (
            row.equity_contributions
            + row.debt_drawdowns
            + row.cash_from_operations
            for row in periods
        ),
        ZERO,
    )
    uses = sum(
        (
            row.capex_additions
            + row.principal_paid
            + row.financing_fees
            for row in periods
        ),
        ZERO,
    ) + periods[-1].ending_cash
    variance = abs(sources - uses)
    return InvariantResult(
        invariant_id="sources_uses_balance",
        status="failed" if variance > TOLERANCE else "passed",
        maximum_variance=variance,
        tolerance=TOLERANCE,
        period_refs=(periods[-1].period,) if variance > TOLERANCE else (),
        reason="cumulative_sources_uses_mismatch" if variance > TOLERANCE else "",
    )


def _finite_numbers(
    periods: tuple[FinancialPeriod, ...],
    debt: tuple[DebtPeriod, ...],
) -> InvariantResult:
    for row in (*periods, *debt):
        for field in row.__dataclass_fields__:
            value = getattr(row, field)
            if isinstance(value, Decimal) and not value.is_finite():
                return InvariantResult(
                    invariant_id="finite_numbers",
                    status="failed",
                    maximum_variance=ZERO,
                    tolerance=TOLERANCE,
                    period_refs=(getattr(row, "period", ""),),
                    reason=f"non_finite:{field}",
                )
    return InvariantResult("finite_numbers", "passed", ZERO, TOLERANCE, ())


def _period_order(periods: tuple[FinancialPeriod, ...]) -> InvariantResult:
    failures = [
        row.period
        for index, row in enumerate(periods[1:], start=1)
        if row.period != add_months(periods[index - 1].period, 1)
    ]
    return InvariantResult(
        invariant_id="period_order",
        status="failed" if failures else "passed",
        maximum_variance=ZERO,
        tolerance=TOLERANCE,
        period_refs=tuple(failures),
        reason="period_gap_or_order" if failures else "",
    )
