from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any


ZERO = Decimal("0")


@dataclass(frozen=True, slots=True)
class DebtPeriod:
    opening_balance: Decimal = ZERO
    drawdowns: Decimal = ZERO
    interest_expense: Decimal = ZERO
    interest_paid: Decimal = ZERO
    interest_capitalized: Decimal = ZERO
    principal_paid: Decimal = ZERO
    fees_paid: Decimal = ZERO
    closing_balance: Decimal = ZERO


@dataclass(frozen=True, slots=True)
class FinancialPeriod:
    period: str
    revenue: Decimal
    cogs: Decimal
    gross_profit: Decimal
    operating_expenses: Decimal
    ebitda: Decimal
    depreciation: Decimal
    ebit: Decimal
    interest_expense: Decimal
    fiscal_expense: Decimal
    net_income: Decimal
    accounts_receivable: Decimal
    inventory: Decimal
    accounts_payable: Decimal
    net_working_capital: Decimal
    change_in_working_capital: Decimal
    capex_additions: Decimal
    ppe_net: Decimal
    equity_contributions: Decimal
    debt_drawdowns: Decimal
    principal_paid: Decimal
    financing_fees: Decimal
    debt_closing: Decimal
    cash_from_operations: Decimal
    cash_from_investing: Decimal
    cash_from_financing: Decimal
    opening_cash: Decimal
    ending_cash: Decimal
    retained_earnings: Decimal
    total_assets: Decimal
    total_liabilities: Decimal
    total_equity: Decimal
    unlevered_fcf: Decimal
    equity_cash_flow: Decimal
    cfads: Decimal


@dataclass(frozen=True, slots=True)
class InvariantResult:
    invariant_id: str
    status: str
    maximum_variance: Decimal
    tolerance: Decimal
    period_refs: tuple[str, ...]
    reason: str = ""


@dataclass(frozen=True, slots=True)
class FinancialModel:
    periods: tuple[FinancialPeriod, ...]
    debt_schedule: tuple[DebtPeriod, ...]
    invariants: tuple[InvariantResult, ...]
    metrics: dict[str, Decimal | None]
    status: str
    blockers: tuple[dict[str, str], ...]
    source_input_hash: str

    def period(self, period: str) -> FinancialPeriod:
        for row in self.periods:
            if row.period == period:
                return row
        raise KeyError(period)

    def as_internal_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "periods": [
                {
                    field: getattr(row, field)
                    for field in row.__dataclass_fields__
                }
                for row in self.periods
            ],
            "debt_schedule": [
                {
                    field: getattr(row, field)
                    for field in row.__dataclass_fields__
                }
                for row in self.debt_schedule
            ],
            "invariants": [
                {
                    "invariant_id": row.invariant_id,
                    "status": row.status,
                    "maximum_variance": row.maximum_variance,
                    "tolerance": row.tolerance,
                    "period_refs": list(row.period_refs),
                    "reason": row.reason,
                }
                for row in self.invariants
            ],
            "metrics": self.metrics,
            "blockers": list(self.blockers),
        }
