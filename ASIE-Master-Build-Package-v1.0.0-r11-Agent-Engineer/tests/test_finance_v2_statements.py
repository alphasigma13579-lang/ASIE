from __future__ import annotations

import copy
from decimal import Decimal

import pytest

from backend.finance_v2 import build_financial_model, validate_finance_input
from tests.test_finance_v2_contracts import binding, lineage, valid_document


def build(document: dict):
    return build_financial_model(validate_finance_input(document, binding=binding()))


def test_integrated_statements_balance_every_period() -> None:
    document = valid_document()
    periods = [row["period"] for row in document["revenue_streams"][0]["price_series"]]
    document["operating_costs"] = [
        {
            "cost_id": "opex-rent",
            "behavior": "fixed",
            "schedule": [{"period": period, "value": "300"} for period in periods],
            "lineage": lineage(),
        }
    ]
    document["capex_assets"] = [
        {
            "asset_id": "asset-machine",
            "acquisition_period": periods[0],
            "cost": "12000",
            "useful_life_months": 24,
            "depreciation_method": "straight_line",
            "residual_value": "0",
            "lineage": lineage(),
        }
    ]

    model = build(document)

    assert model.status == "ready"
    assert not model.blockers
    assert len(model.periods) == 12
    assert len(model.invariants) == 14
    assert not [item for item in model.invariants if item.status == "failed"]
    assert model.periods[0].depreciation == Decimal("500")
    assert model.periods[0].ppe_net == Decimal("11500")
    assert model.periods[-1].ppe_net == Decimal("6000")
    for row in model.periods:
        assert row.total_assets == pytest.approx(
            row.total_liabilities + row.total_equity, abs=Decimal("0.01")
        )
        assert row.ending_cash == (
            row.opening_cash
            + row.cash_from_operations
            + row.cash_from_investing
            + row.cash_from_financing
        )
    assert model.metrics["npv_unlevered"] is not None
    assert model.metrics["break_even"] == Decimal("300") / Decimal("15.50")


def test_zero_rate_equal_principal_debt_honors_grace_and_reaches_zero() -> None:
    document = valid_document()
    document["financing"]["debt_tranches"] = [
        {
            "tranche_id": "debt-main",
            "drawdowns": [{"period": "2026-01", "amount": "1200"}],
            "annual_rate": "0",
            "tenor_months": 12,
            "principal_grace_months": 2,
            "interest_grace_policy": "paid",
            "repayment_profile": "equal_principal",
            "fee_treatment": "expense_upfront",
            "fees": [],
            "lineage": lineage(),
        }
    ]

    model = build(document)

    assert model.status == "ready"
    assert model.debt_schedule[0].principal_paid == 0
    assert model.debt_schedule[1].principal_paid == 0
    assert all(row.principal_paid == Decimal("120") for row in model.debt_schedule[2:])
    assert model.debt_schedule[-1].closing_balance == 0
    assert model.metrics["dscr_min"] is not None
    assert model.metrics["llcr"] is not None


def test_capitalized_interest_is_non_cash_and_balances_with_debt() -> None:
    document = valid_document()
    document["financing"]["debt_tranches"] = [
        {
            "tranche_id": "debt-capitalized",
            "drawdowns": [{"period": "2026-01", "amount": "1200"}],
            "annual_rate": "0.12",
            "tenor_months": 12,
            "principal_grace_months": 2,
            "interest_grace_policy": "capitalized",
            "repayment_profile": "annuity",
            "fee_treatment": "expense_upfront",
            "fees": [],
            "lineage": lineage(),
        }
    ]

    model = build(document)
    first = model.periods[0]
    debt = model.debt_schedule[0]

    assert debt.interest_capitalized == Decimal("12")
    assert debt.interest_paid == 0
    assert debt.closing_balance == Decimal("1212")
    assert first.cash_from_operations == (
        first.net_income
        + first.depreciation
        + debt.interest_capitalized
        - first.change_in_working_capital
    )
    assert model.status == "ready"
    assert not [item for item in model.invariants if item.status == "failed"]


def test_financing_fee_is_expensed_but_classified_once_in_cash_flow() -> None:
    document = valid_document()
    document["financing"]["debt_tranches"] = [
        {
            "tranche_id": "debt-fee",
            "drawdowns": [{"period": "2026-01", "amount": "1200"}],
            "annual_rate": "0",
            "tenor_months": 12,
            "principal_grace_months": 0,
            "interest_grace_policy": "paid",
            "repayment_profile": "bullet",
            "fee_treatment": "expense_upfront",
            "fees": [{"fee_id": "fee-1", "period": "2026-01", "amount": "25"}],
            "lineage": lineage(),
        }
    ]

    model = build(document)
    first = model.periods[0]

    assert first.interest_expense == Decimal("25")
    assert first.financing_fees == Decimal("25")
    assert model.status == "ready"
    assert not [item for item in model.invariants if item.status == "failed"]


def test_vat_fails_closed_until_input_output_tax_ledger_contract_exists() -> None:
    document = valid_document()
    document["fiscal_policy"]["modules"] = ["vat"]
    document["fiscal_policy"]["vat_rate"] = "0.15"

    model = build(document)

    assert model.status == "not_ready"
    assert {item["code"] for item in model.blockers} == {"FIN2_VAT_LEDGER_NOT_READY"}
    assert not [item for item in model.invariants if item.status == "failed"]


def test_replay_is_deterministic_and_does_not_mutate_validated_input() -> None:
    document = valid_document()
    validated = validate_finance_input(document, binding=binding())
    before = validated.canonical_document

    first = build_financial_model(validated)
    second = build_financial_model(validated)

    assert first == second
    assert validated.canonical_document == before
    assert validated.thaw() == document


@pytest.mark.parametrize(
    ("price", "variable_cost", "opex", "expected_profit"),
    [
        ("25.50", "10", "300", "1250"),
        ("12", "12", "0", "0"),
        ("100", "30", "2000", "5000"),
    ],
)
def test_revenue_cost_equations_hold_across_bounded_cases(
    price: str,
    variable_cost: str,
    opex: str,
    expected_profit: str,
) -> None:
    document = valid_document()
    for row in document["revenue_streams"][0]["price_series"]:
        row["value"] = price
    for row in document["revenue_streams"][0]["variable_cost_series"]:
        row["value"] = variable_cost
    periods = [row["period"] for row in document["revenue_streams"][0]["price_series"]]
    if Decimal(opex):
        document["operating_costs"] = [
            {
                "cost_id": "opex-case",
                "behavior": "fixed",
                "schedule": [{"period": period, "value": opex} for period in periods],
                "lineage": lineage(),
            }
        ]

    model = build(document)
    first = model.periods[0]

    assert first.gross_profit == first.revenue - first.cogs
    assert first.ebitda == Decimal(expected_profit)
    assert first.ebit == first.ebitda - first.depreciation
