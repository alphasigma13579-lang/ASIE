from __future__ import annotations

from decimal import Decimal, localcontext
from typing import Iterable

from .model import ZERO


def monthly_rate_from_annual(annual_rate: Decimal) -> Decimal:
    if annual_rate <= Decimal("-1"):
        raise ValueError("annual rate must be greater than -1")
    with localcontext() as context:
        context.prec = 34
        return ((Decimal(1) + annual_rate).ln() / Decimal(12)).exp() - Decimal(1)


def npv_monthly(cashflows: Iterable[Decimal], annual_rate: Decimal) -> Decimal:
    monthly_rate = monthly_rate_from_annual(annual_rate)
    with localcontext() as context:
        context.prec = 34
        base = Decimal(1) + monthly_rate
        return sum(
            (cashflow / (base**index) for index, cashflow in enumerate(cashflows, start=1)),
            ZERO,
        )


def irr_annual(cashflows: tuple[Decimal, ...]) -> Decimal | None:
    if not cashflows or not any(value < ZERO for value in cashflows) or not any(
        value > ZERO for value in cashflows
    ):
        return None

    lower = Decimal("-0.999999")
    upper = Decimal("10")
    lower_value = npv_monthly(cashflows, lower)
    upper_value = npv_monthly(cashflows, upper)
    if lower_value == ZERO:
        return lower
    if upper_value == ZERO:
        return upper
    if lower_value * upper_value > ZERO:
        return None

    with localcontext() as context:
        context.prec = 34
        for _ in range(160):
            middle = (lower + upper) / Decimal(2)
            value = npv_monthly(cashflows, middle)
            if abs(value) <= Decimal("0.00000001"):
                return middle
            if lower_value * value <= ZERO:
                upper = middle
            else:
                lower = middle
                lower_value = value
        return (lower + upper) / Decimal(2)


def mirr_annual(
    cashflows: tuple[Decimal, ...],
    finance_rate: Decimal,
    reinvestment_rate: Decimal,
) -> Decimal | None:
    if len(cashflows) < 2:
        return None
    finance_monthly = monthly_rate_from_annual(finance_rate)
    reinvest_monthly = monthly_rate_from_annual(reinvestment_rate)
    count = len(cashflows)
    present_negative = ZERO
    future_positive = ZERO
    for index, value in enumerate(cashflows, start=1):
        if value < ZERO:
            present_negative += value / ((Decimal(1) + finance_monthly) ** index)
        elif value > ZERO:
            future_positive += value * ((Decimal(1) + reinvest_monthly) ** (count - index))
    if present_negative == ZERO or future_positive == ZERO:
        return None
    with localcontext() as context:
        context.prec = 34
        monthly = (future_positive / abs(present_negative)).ln() / Decimal(count)
        monthly_rate = monthly.exp() - Decimal(1)
        return ((Decimal(1) + monthly_rate) ** Decimal(12)) - Decimal(1)


def payback_months(cashflows: Iterable[Decimal]) -> Decimal | None:
    cumulative = ZERO
    previous = ZERO
    for month, value in enumerate(cashflows, start=1):
        previous = cumulative
        cumulative += value
        if cumulative >= ZERO and previous < ZERO and value > ZERO:
            fraction = abs(previous) / value
            return Decimal(month - 1) + fraction
    return Decimal(0) if cumulative == ZERO else None


def minimum_dscr(
    cfads: tuple[Decimal, ...],
    debt_service: tuple[Decimal, ...],
) -> Decimal | None:
    ratios = [
        cash / service
        for cash, service in zip(cfads, debt_service, strict=True)
        if service > ZERO
    ]
    return min(ratios) if ratios else None


def llcr(
    cfads: tuple[Decimal, ...],
    debt_service: tuple[Decimal, ...],
    opening_debt: Decimal,
    annual_discount_rate: Decimal,
) -> Decimal | None:
    if opening_debt <= ZERO or not any(service > ZERO for service in debt_service):
        return None
    return npv_monthly(cfads, annual_discount_rate) / opening_debt
