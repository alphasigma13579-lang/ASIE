from __future__ import annotations

from dataclasses import replace
from decimal import Decimal, localcontext
from typing import Any

from .contracts import parse_decimal
from .model import DebtPeriod, ZERO


class UnsupportedDebtProfile(ValueError):
    pass


def build_debt_schedule(
    document: dict[str, Any],
    periods: tuple[str, ...],
) -> tuple[DebtPeriod, ...]:
    aggregate = [DebtPeriod() for _ in periods]
    period_to_index = {period: index for index, period in enumerate(periods)}

    for tranche in document["financing"]["debt_tranches"]:
        profile = tranche["repayment_profile"]
        if profile == "custom_reviewed":
            raise UnsupportedDebtProfile(
                f"{tranche['tranche_id']}: custom_reviewed requires an approved schedule"
            )
        annual_rate = parse_decimal(
            tranche["annual_rate"],
            f"debt:{tranche['tranche_id']}.annual_rate",
            allow_negative=False,
        )
        monthly_rate = annual_rate / Decimal(12)
        tenor = tranche["tenor_months"]
        grace = tranche["principal_grace_months"]
        grace_policy = tranche["interest_grace_policy"]

        for draw in tranche["drawdowns"]:
            draw_index = period_to_index[draw["period"]]
            amount = parse_decimal(
                draw["amount"],
                f"debt:{tranche['tranche_id']}.drawdown",
                allow_negative=False,
            )
            _add_subloan(
                aggregate,
                draw_index=draw_index,
                amount=amount,
                monthly_rate=monthly_rate,
                tenor=tenor,
                grace=grace,
                grace_policy=grace_policy,
                profile=profile,
            )

        for fee in tranche["fees"]:
            index = period_to_index[fee["period"]]
            amount = parse_decimal(
                fee["amount"],
                f"debt:{tranche['tranche_id']}.fee",
                allow_negative=False,
            )
            aggregate[index] = replace(
                aggregate[index],
                fees_paid=aggregate[index].fees_paid + amount,
            )

    return tuple(aggregate)


def _add_subloan(
    aggregate: list[DebtPeriod],
    *,
    draw_index: int,
    amount: Decimal,
    monthly_rate: Decimal,
    tenor: int,
    grace: int,
    grace_policy: str,
    profile: str,
) -> None:
    balance = ZERO
    repayment_balance: Decimal | None = None
    repayment_months = tenor - grace

    for offset in range(tenor):
        index = draw_index + offset
        if index >= len(aggregate):
            break
        opening = balance
        drawdown = amount if offset == 0 else ZERO
        before_service = opening + drawdown
        interest = before_service * monthly_rate
        interest_paid = interest
        capitalized = ZERO
        principal = ZERO

        if offset < grace:
            if grace_policy == "capitalized":
                capitalized = interest
                interest_paid = ZERO
            closing = before_service + capitalized
        else:
            if repayment_balance is None:
                repayment_balance = before_service
            remaining = tenor - offset
            if profile == "bullet":
                principal = before_service if remaining == 1 else ZERO
            elif profile == "equal_principal":
                principal = min(before_service, repayment_balance / Decimal(repayment_months))
            elif profile == "annuity":
                payment = _annuity_payment(before_service, monthly_rate, remaining)
                principal = min(before_service, max(ZERO, payment - interest))
            else:
                raise UnsupportedDebtProfile(profile)
            closing = max(ZERO, before_service - principal)

        current = aggregate[index]
        aggregate[index] = DebtPeriod(
            opening_balance=current.opening_balance + opening,
            drawdowns=current.drawdowns + drawdown,
            interest_expense=current.interest_expense + interest,
            interest_paid=current.interest_paid + interest_paid,
            interest_capitalized=current.interest_capitalized + capitalized,
            principal_paid=current.principal_paid + principal,
            fees_paid=current.fees_paid,
            closing_balance=current.closing_balance + closing,
        )
        balance = closing


def _annuity_payment(
    balance: Decimal,
    monthly_rate: Decimal,
    remaining_months: int,
) -> Decimal:
    if remaining_months <= 0:
        return balance
    if monthly_rate == ZERO:
        return balance / Decimal(remaining_months)
    with localcontext() as context:
        context.prec = 34
        factor = (Decimal(1) + monthly_rate) ** (-remaining_months)
        return balance * monthly_rate / (Decimal(1) - factor)
