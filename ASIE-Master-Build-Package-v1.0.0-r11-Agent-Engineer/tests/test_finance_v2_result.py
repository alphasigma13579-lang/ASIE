from __future__ import annotations

import json
import re
from decimal import Decimal

import pytest

from backend.finance_v2 import (
    FinanceContractError,
    build_financial_model,
    canonical_json,
    monthly_periods,
    serialize_finance_result,
    validate_finance_input,
)
from backend.finance_v2.result import (
    _apply_legacy_parity,
    _debt_coverage_state,
)
from tests.test_finance_v2_contracts import binding, valid_document


DECIMAL = re.compile(r"^-?(0|[1-9][0-9]*)(\.[0-9]+)?$")


def result(*, legacy: bool = False):
    validated = validate_finance_input(valid_document(), binding=binding())
    model = build_financial_model(validated)
    return serialize_finance_result(
        validated,
        model,
        include_legacy_projection=legacy,
    )


def test_v2_result_has_identity_versions_three_statements_and_fourteen_invariants() -> None:
    output = result()

    assert output["schema_version"] == "finance-result.v2"
    assert output["engine_version"] == "2.0.0-dark.3"
    assert output["status"] == "ready"
    assert output["organization_id"] == "org-1"
    assert output["project_id"] == "project-1"
    assert output["run_id"] == "run-1"
    assert output["input_hash"].startswith("sha256:")
    assert len(output["periods"]) == 12
    assert len(output["statements"]["income_statement"]) == 10
    assert len(output["statements"]["balance_sheet"]) == 11
    assert len(output["statements"]["cash_flow_statement"]) == 8
    assert len(output["invariants"]) == 14
    assert not [row for row in output["invariants"] if row["status"] == "failed"]
    assert output["blockers"] == []


def test_result_decimal_truth_is_string_and_deterministic() -> None:
    first = result()
    second = result()

    assert canonical_json(first) == canonical_json(second)
    for statement in first["statements"].values():
        for line in statement:
            for point in line["values"]:
                assert isinstance(point["value"], str)
                assert DECIMAL.fullmatch(point["value"])
    assert all(
        value is None or isinstance(value, str)
        for value in first["metrics"].values()
    )


def test_lineage_is_deduplicated_sorted_and_formula_versioned() -> None:
    output = result()
    assert output["lineage"]["assumption_refs"] == ["asm-1"]
    assert output["lineage"]["evidence_refs"] == ["ev-1"]
    assert output["lineage"]["formula_registry_version"] == output["engine_version"]


def test_legacy_projection_is_off_by_default_and_schema_satisfiable() -> None:
    output = result()
    legacy = output["legacy_projection"]
    assert legacy == {
        "schema_version": "finance.result.v1-compatible",
        "status": "not_available",
        "derived_from": "finance-result.v2",
        "payload": {},
    }

    schema_path = (
        __import__("pathlib").Path(__file__).resolve().parents[1]
        / "schemas"
        / "finance"
        / "finance-result.v2.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    legacy_schema = schema["properties"]["legacy_projection"]
    assert "required" not in legacy_schema["properties"]["payload"]
    assert (
        legacy_schema["allOf"][1]["then"]["properties"]["payload"]["maxProperties"]
        == 0
    )


def test_legacy_projection_is_derived_from_same_model_without_recalculation() -> None:
    output = result(legacy=True)
    legacy = output["legacy_projection"]

    assert legacy["status"] == "derived"
    payload = legacy["payload"]
    assert payload["baseline"]["npv"] == float(output["metrics"]["npv_unlevered"])
    assert payload["baseline"]["dscr"] == (
        None
        if output["metrics"]["dscr_min"] is None
        else float(output["metrics"]["dscr_min"])
    )
    parity = next(
        row
        for row in output["invariants"]
        if row["invariant_id"] == "legacy_projection_parity"
    )
    assert parity["status"] == "passed"
    monte_carlo = payload["monte_carlo"]
    assert monte_carlo["status"] == "not_ready"
    assert {
        "seed",
        "iterations",
        "p_pass",
        "p10_profit",
        "p50_profit",
        "p90_profit",
        "distribution_profile",
        "correlation_ref",
        "convergence",
        "label_ar",
        "label_en",
        "warning",
    } <= set(monte_carlo)
    assert monte_carlo["iterations"] == 0
    assert monte_carlo["convergence"]["status"] == "not_ready"
    assert payload["sensitivity"] is None
    assert payload["operational_sensitivity"] is None


    required_baseline = {
        "scenario_id",
        "startup_cost",
        "revenue",
        "variable_total",
        "gross_profit",
        "monthly_profit",
        "annual_cashflow",
        "ebitda",
        "ebit",
        "depreciation_monthly",
        "net_operating_cashflow",
        "break_even_units",
        "funding_gap",
        "funding_need_after_equity",
        "contribution_margin",
        "working_capital_need",
        "initial_investment",
        "npv",
        "irr",
        "payback_months",
        "debt_service_monthly",
        "dscr",
    }
    assert required_baseline <= set(payload["baseline"])
    assert payload["baseline"]["scenario_id"] == "baseline"
    assert payload["assumption_refs"] == ["asm-1"]
    assert payload["operating_model"]["monthly_units"] == 100.0
    assert {
        "use_operating_capacity",
        "capacity_units_per_day",
        "operating_days_per_month",
        "utilization_rate",
        "monthly_units",
        "unit_source",
    } <= set(payload["operating_model"])
    assert {
        "total_capex",
        "depreciation_monthly",
        "capex_equipment",
        "capex_fitout",
        "capex_licenses_local",
    } <= set(payload["capex_breakdown"])
    assert {
        "total_monthly_opex",
        "payroll_monthly",
        "rent_monthly",
        "utilities_monthly",
    } <= set(payload["opex_breakdown"])
    assert {
        "status",
        "debt_amount",
        "monthly_payment",
        "annual_debt_service",
        "dscr",
        "loan_grace_months",
        "warning",
    } <= set(payload["debt_service_profile"])
    assert payload["debt_service_profile"]["status"] == "ready"
    for nested in (
        "operating_model",
        "capex_breakdown",
        "opex_breakdown",
        "debt_service_profile",
    ):
        assert payload["baseline"][nested] == payload[nested]
        assert payload["scenarios"][0][nested] == payload[nested]


def test_legacy_capex_fallback_preserves_unclassified_v2_total() -> None:
    document = valid_document()
    document["capex_assets"] = [
        {
            "asset_id": "asset-unclassified",
            "acquisition_period": "2026-01",
            "cost": "12000",
            "residual_value": "0",
            "useful_life_months": 60,
            "depreciation_method": "straight_line",
            "lineage": {
                "assumption_refs": ["asm-1"],
                "evidence_refs": ["ev-1"],
            },
        }
    ]
    validated = validate_finance_input(document, binding=binding())
    model = build_financial_model(validated)
    output = serialize_finance_result(
        validated, model, include_legacy_projection=True
    )
    capex = output["legacy_projection"]["payload"]["capex_breakdown"]

    assert capex["total_capex"] == 12000.0
    assert capex["legacy_startup_cost"] == capex["total_capex"]
    assert capex["capex_equipment"] == 0.0
    assert capex["capex_fitout"] == 0.0
    assert capex["capex_licenses_local"] == 0.0
    assert capex["depreciation_years"] == 5.0


def test_legacy_debt_profile_has_complete_consumer_shape() -> None:
    document = valid_document()
    document["financing"]["debt_tranches"] = [
        {
            "tranche_id": "debt-1",
            "drawdowns": [{"period": "2026-01", "amount": "12000"}],
            "annual_rate": "0.05",
            "tenor_months": 12,
            "principal_grace_months": 2,
            "interest_grace_policy": "paid",
            "repayment_profile": "annuity",
            "fee_treatment": "expense_upfront",
            "fees": [],
            "lineage": {
                "assumption_refs": ["asm-1"],
                "evidence_refs": ["ev-1"],
            },
        }
    ]
    validated = validate_finance_input(document, binding=binding())
    model = build_financial_model(validated)
    output = serialize_finance_result(
        validated, model, include_legacy_projection=True
    )
    profile = output["legacy_projection"]["payload"][
        "debt_service_profile"
    ]

    assert profile["status"] == "ready"
    assert profile["debt_amount"] == 12000.0
    assert profile["monthly_payment"] is not None
    assert profile["annual_debt_service"] is not None
    assert profile["loan_grace_months"] == 2
    assert isinstance(profile["warning"], str)


def test_balance_sheet_equity_projection_is_cumulative() -> None:
    output = result()
    balance = {
        line["line_id"]: line["values"]
        for line in output["statements"]["balance_sheet"]
    }
    contributed = balance["contributed_equity"]
    assert contributed[0]["value"] == "100000.00"
    assert contributed[-1]["value"] == "100000.00"

def test_scenario_metrics_use_the_same_governed_scales_as_top_level() -> None:
    output = result()
    assert output["scenarios"][0]["metrics"] == output["metrics"]


def test_not_ready_custom_reviewed_debt_serializes_blocker_without_exception() -> None:
    document = valid_document()
    document["financing"]["debt_tranches"] = [
        {
            "tranche_id": "debt-custom",
            "drawdowns": [{"period": "2026-01", "amount": "1000"}],
            "annual_rate": "0.05",
            "tenor_months": 12,
            "principal_grace_months": 0,
            "interest_grace_policy": "paid",
            "repayment_profile": "custom_reviewed",
            "fee_treatment": "expense_upfront",
            "fees": [],
            "lineage": {
                "assumption_refs": ["asm-1"],
                "evidence_refs": ["ev-1"],
            },
        }
    ]
    validated = validate_finance_input(document, binding=binding())
    model = build_financial_model(validated)

    assert model.status == "not_ready"
    output = serialize_finance_result(validated, model)
    assert output["status"] == "not_ready"
    assert output["subledgers"]["debt"] == []
    assert output["statements"]["income_statement"][0]["values"] == []
    assert output["cash_flows"] == {
        "unlevered_fcf": [],
        "equity_cash_flow": [],
        "cfads": [],
    }
    assert output["invariants"] == []
    assert set(output["metrics"]) == {
        "npv_unlevered",
        "irr_unlevered",
        "mirr_unlevered",
        "payback_months",
        "break_even",
        "funding_need",
        "dscr_min",
        "llcr",
    }
    assert set(output["metrics"].values()) == {None}
    assert [row["code"] for row in output["blockers"]] == [
        "FIN2_DEBT_PROFILE_UNSUPPORTED"
    ]


def test_result_schema_allows_unavailable_values_only_outside_ready_gate() -> None:
    schema_path = (
        __import__("pathlib").Path(__file__).resolve().parents[1]
        / "schemas"
        / "finance"
        / "finance-result.v2.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    properties = schema["properties"]
    ready = schema["allOf"][0]["then"]["properties"]

    assert "subledgers" in schema["required"]
    assert properties["subledgers"]["required"] == [
        "capex",
        "working_capital",
        "debt",
        "fiscal",
    ]
    for statement in (
        "income_statement",
        "balance_sheet",
        "cash_flow_statement",
    ):
        values = properties["statements"]["properties"][statement]["items"][
            "properties"
        ]["values"]
        ready_values = ready["statements"]["properties"][statement]["items"][
            "properties"
        ]["values"]
        assert values["minItems"] == 0
        assert ready_values["minItems"] == 1
    for flow in ("unlevered_fcf", "equity_cash_flow", "cfads"):
        assert properties["cash_flows"]["properties"][flow]["minItems"] == 0
        assert ready["cash_flows"]["properties"][flow]["minItems"] == 1
    assert properties["invariants"]["minItems"] == 0
    assert ready["invariants"]["minItems"] == 14
    for metric in ("npv_unlevered", "funding_need"):
        assert {"type": "null"} in properties["metrics"]["properties"][metric]["anyOf"]
        assert ready["metrics"]["properties"][metric]["type"] == "string"


def test_legacy_projection_rounds_ratios_to_v2_policy() -> None:
    output = result(legacy=True)
    baseline = output["legacy_projection"]["payload"]["baseline"]

    for legacy_key, metric_key in (
        ("irr", "irr_unlevered"),
        ("payback_months", "payback_months"),
        ("dscr", "dscr_min"),
    ):
        expected = output["metrics"][metric_key]
        assert baseline[legacy_key] == (
            None if expected is None else float(expected)
        )


def test_legacy_annual_cashflow_is_first_twelve_months_not_full_horizon() -> None:
    document = valid_document()
    periods = monthly_periods("2026-01", 24)
    document["forecast"]["monthly_periods"] = 24
    stream = document["revenue_streams"][0]
    for field, value in (
        ("volume_series", "100"),
        ("price_series", "25.50"),
        ("variable_cost_series", "10"),
    ):
        stream[field] = [{"period": period, "value": value} for period in periods]

    validated = validate_finance_input(document, binding=binding())
    model = build_financial_model(validated)
    output = serialize_finance_result(
        validated,
        model,
        include_legacy_projection=True,
    )
    cashflows = [Decimal(value) for value in output["cash_flows"]["equity_cash_flow"]]
    annual = output["legacy_projection"]["payload"]["baseline"]["annual_cashflow"]

    assert len(cashflows) == 24
    assert annual == float(sum(cashflows[:12], Decimal("0")))
    assert annual != float(sum(cashflows, Decimal("0")))

def test_serializer_rejects_model_from_different_validated_input() -> None:
    first = validate_finance_input(valid_document(), binding=binding())
    model = build_financial_model(first)
    changed = valid_document()
    for point in changed["revenue_streams"][0]["price_series"]:
        point["value"] = "26.50"
    second = validate_finance_input(changed, binding=binding())

    with pytest.raises(FinanceContractError) as error:
        serialize_finance_result(second, model)
    assert error.value.code == "FIN2_MODEL_INPUT_MISMATCH"


def test_large_admitted_decimals_serialize_without_context_failure() -> None:
    document = valid_document()
    price = "12345678901234567890123"
    for point in document["revenue_streams"][0]["price_series"]:
        point["value"] = price
    validated = validate_finance_input(document, binding=binding())
    model = build_financial_model(validated)
    output = serialize_finance_result(
        validated, model, include_legacy_projection=True
    )

    revenue = next(
        row
        for row in output["statements"]["income_statement"]
        if row["line_id"] == "revenue"
    )
    assert revenue["values"][0]["value"] == (
        "1234567890123456789012300.00"
    )
    assert output["status"] == "ready"
    parity = next(
        row
        for row in output["invariants"]
        if row["invariant_id"] == "legacy_projection_parity"
    )
    assert parity["status"] == "passed"


def test_legacy_projection_is_not_ready_when_break_even_is_unavailable() -> None:
    document = valid_document()
    document["revenue_streams"][0]["model_kind"] = "service_capacity"
    validated = validate_finance_input(document, binding=binding())
    model = build_financial_model(validated)
    assert model.status == "ready"
    assert model.metrics["break_even"] is None

    output = serialize_finance_result(
        validated, model, include_legacy_projection=True
    )
    payload = output["legacy_projection"]["payload"]

    assert output["status"] == "ready"
    assert payload["status"] == "not_ready"
    assert payload["baseline"] is None
    assert payload["scenarios"] == []
    assert payload["blockers"][-1]["code"] == (
        "FIN2_LEGACY_BREAK_EVEN_UNAVAILABLE"
    )


def test_legacy_projection_blocks_values_outside_float_range() -> None:
    document = valid_document()
    price = "1" + ("0" * 309)
    for point in document["revenue_streams"][0]["price_series"]:
        point["value"] = price
    validated = validate_finance_input(document, binding=binding())
    model = build_financial_model(validated)
    output = serialize_finance_result(
        validated, model, include_legacy_projection=True
    )
    payload = output["legacy_projection"]["payload"]

    assert output["status"] == "ready"
    assert payload["status"] == "not_ready"
    assert payload["baseline"] is None
    assert payload["blockers"][-1]["code"] == "FIN2_LEGACY_NUMBER_RANGE"


def test_legacy_parity_failure_blocks_ready_result() -> None:
    output = result(legacy=True)
    output["legacy_projection"]["payload"]["baseline"]["npv"] += 1.0

    _apply_legacy_parity(output, money_scale=2, ratio_scale=6)

    parity = next(
        row
        for row in output["invariants"]
        if row["invariant_id"] == "legacy_projection_parity"
    )
    assert parity["status"] == "failed"
    assert output["status"] == "not_ready"
    assert output["scenarios"][0]["status"] == "not_ready"
    assert output["blockers"][-1]["code"] == (
        "FIN2_INVARIANT_LEGACY_PROJECTION_PARITY"
    )

def test_legacy_range_guard_includes_values_derived_from_input() -> None:
    document = valid_document()
    volume = "1" + ("0" * 309)
    stream = document["revenue_streams"][0]
    for point in stream["volume_series"]:
        point["value"] = volume
    for point in stream["price_series"]:
        point["value"] = "0.00000001"
    for point in stream["variable_cost_series"]:
        point["value"] = "0"
    validated = validate_finance_input(document, binding=binding())
    model = build_financial_model(validated)

    assert float(model.periods[0].revenue) != float("inf")
    output = serialize_finance_result(
        validated, model, include_legacy_projection=True
    )
    payload = output["legacy_projection"]["payload"]

    assert output["status"] == "ready"
    assert payload["status"] == "not_ready"
    assert payload["blockers"][-1]["code"] == "FIN2_LEGACY_NUMBER_RANGE"


def test_legacy_monthly_payment_ignores_post_tenor_forecast_months() -> None:
    def projection(months: int, draw_period: str = "2026-01") -> dict:
        document = valid_document()
        periods = monthly_periods("2026-01", months)
        document["forecast"]["monthly_periods"] = months
        stream = document["revenue_streams"][0]
        for field, value in (
            ("volume_series", "100"),
            ("price_series", "25.50"),
            ("variable_cost_series", "10"),
        ):
            stream[field] = [
                {"period": period, "value": value} for period in periods
            ]
        document["financing"]["debt_tranches"] = [
            {
                "tranche_id": "debt-1",
                "drawdowns": [
                    {"period": draw_period, "amount": "12000"}
                ],
                "annual_rate": "0.05",
                "tenor_months": 12,
                "principal_grace_months": 0,
                "interest_grace_policy": "paid",
                "repayment_profile": "annuity",
                "fee_treatment": "expense_upfront",
                "fees": [],
                "lineage": {
                    "assumption_refs": ["asm-1"],
                    "evidence_refs": ["ev-1"],
                },
            }
        ]
        validated = validate_finance_input(document, binding=binding())
        model = build_financial_model(validated)
        output = serialize_finance_result(
            validated, model, include_legacy_projection=True
        )
        return output["legacy_projection"]["payload"][
            "debt_service_profile"
        ]

    twelve = projection(12)
    twenty_four = projection(24)

    assert twelve["monthly_payment"] == twenty_four["monthly_payment"]
    assert twelve["annual_debt_service"] == (
        twenty_four["annual_debt_service"]
    )

    delayed = projection(24, draw_period="2027-01")
    assert delayed["monthly_payment"] is not None
    assert delayed["annual_debt_service"] == pytest.approx(
        delayed["monthly_payment"] * 12,
        abs=0.01,
    )
    assert delayed["annual_debt_service"] > 0

def test_legacy_range_guard_checks_cross_stream_volume_aggregate() -> None:
    document = valid_document()
    first = document["revenue_streams"][0]
    second = json.loads(json.dumps(first))
    second["stream_id"] = "rev-secondary"
    document["revenue_streams"].append(second)
    for stream in document["revenue_streams"]:
        for point in stream["volume_series"]:
            point["value"] = "1" + ("0" * 308)
        for point in stream["price_series"]:
            point["value"] = "0.00000001"
        for point in stream["variable_cost_series"]:
            point["value"] = "0"

    validated = validate_finance_input(document, binding=binding())
    model = build_financial_model(validated)
    assert float(model.periods[0].revenue) != float("inf")
    output = serialize_finance_result(
        validated, model, include_legacy_projection=True
    )
    payload = output["legacy_projection"]["payload"]

    assert output["status"] == "ready"
    assert payload["status"] == "not_ready"
    assert payload["blockers"][-1]["code"] == "FIN2_LEGACY_NUMBER_RANGE"

def test_legacy_range_guard_checks_aggregate_debt_draws() -> None:
    document = valid_document()
    periods = monthly_periods("2026-01", 24)
    document["forecast"]["monthly_periods"] = 24
    stream = document["revenue_streams"][0]
    for field, value in (
        ("volume_series", "100"),
        ("price_series", "25.50"),
        ("variable_cost_series", "10"),
    ):
        stream[field] = [
            {"period": period, "value": value} for period in periods
        ]

    amount = "1" + ("0" * 308)
    document["financing"]["debt_tranches"] = [
        {
            "tranche_id": f"debt-{index}",
            "drawdowns": [{"period": period, "amount": amount}],
            "annual_rate": "0",
            "tenor_months": 12,
            "principal_grace_months": 0,
            "interest_grace_policy": "paid",
            "repayment_profile": "equal_principal",
            "fee_treatment": "expense_upfront",
            "fees": [],
            "lineage": {
                "assumption_refs": ["asm-1"],
                "evidence_refs": ["ev-1"],
            },
        }
        for index, period in enumerate(("2026-01", "2027-01"), start=1)
    ]

    validated = validate_finance_input(document, binding=binding())
    model = build_financial_model(validated)
    assert all(float(row.debt_closing) != float("inf") for row in model.periods)
    output = serialize_finance_result(
        validated, model, include_legacy_projection=True
    )
    payload = output["legacy_projection"]["payload"]

    assert output["status"] == "ready"
    assert payload["status"] == "not_ready"
    assert payload["blockers"][-1]["code"] == "FIN2_LEGACY_NUMBER_RANGE"

def test_legacy_range_guard_checks_depreciation_years_quotient() -> None:
    document = valid_document()
    cost = "1" + ("0" * 302)
    residual = ("9" * 302) + ".99999999"
    document["capex_assets"] = [
        {
            "asset_id": "asset-near-residual",
            "acquisition_period": "2026-01",
            "cost": cost,
            "residual_value": residual,
            "useful_life_months": 12,
            "depreciation_method": "straight_line",
            "lineage": {
                "assumption_refs": ["asm-1"],
                "evidence_refs": ["ev-1"],
            },
        }
    ]

    validated = validate_finance_input(document, binding=binding())
    model = build_financial_model(validated)
    assert float(model.periods[0].capex_additions) != float("inf")
    output = serialize_finance_result(
        validated, model, include_legacy_projection=True
    )
    payload = output["legacy_projection"]["payload"]

    assert output["status"] == "ready"
    assert payload["status"] == "not_ready"
    assert payload["blockers"][-1]["code"] == "FIN2_LEGACY_NUMBER_RANGE"

def test_legacy_bullet_payment_includes_zero_service_tenor_months() -> None:
    document = valid_document()
    document["financing"]["debt_tranches"] = [
        {
            "tranche_id": "debt-bullet",
            "drawdowns": [{"period": "2026-01", "amount": "12000"}],
            "annual_rate": "0",
            "tenor_months": 12,
            "principal_grace_months": 0,
            "interest_grace_policy": "paid",
            "repayment_profile": "bullet",
            "fee_treatment": "expense_upfront",
            "fees": [],
            "lineage": {
                "assumption_refs": ["asm-1"],
                "evidence_refs": ["ev-1"],
            },
        }
    ]

    validated = validate_finance_input(document, binding=binding())
    model = build_financial_model(validated)
    output = serialize_finance_result(
        validated, model, include_legacy_projection=True
    )
    profile = output["legacy_projection"]["payload"][
        "debt_service_profile"
    ]

    assert profile["monthly_payment"] == 1000.0
    assert profile["annual_debt_service"] == 12000.0

def _annuity_debt_document() -> dict:
    document = valid_document()
    document["financing"]["debt_tranches"] = [
        {
            "tranche_id": "debt-applicability",
            "drawdowns": [{"period": "2026-01", "amount": "12000"}],
            "annual_rate": "0.05",
            "tenor_months": 12,
            "principal_grace_months": 0,
            "interest_grace_policy": "paid",
            "repayment_profile": "annuity",
            "fee_treatment": "expense_upfront",
            "fees": [],
            "lineage": {
                "assumption_refs": ["asm-1"],
                "evidence_refs": ["ev-1"],
            },
        }
    ]
    return document


def test_no_debt_projects_dscr_and_llcr_as_not_applicable() -> None:
    output = result()

    for metric_id in ("dscr_min", "llcr"):
        metric = output["debt_coverage_metrics"][metric_id]
        assert metric["metric_id"] == metric_id
        assert metric["value"] is None
        assert metric["value_status"] == "VALUE_ABSENT"
        assert metric["applicability_status"] == "NOT_APPLICABLE"
        assert metric["reason_code"] == "NO_DEBT_SERVICE"
        assert metric["blocker_codes"] == []
        assert metric["currency"] is None
        assert metric["currency_reason"] == "NOT_MONETARY_METRIC"
        assert output["metrics"][metric_id] is metric["value"]


def test_ready_debt_coverage_objects_are_the_compatibility_value_source() -> None:
    document = _annuity_debt_document()
    validated = validate_finance_input(document, binding=binding())
    model = build_financial_model(validated)
    output = serialize_finance_result(validated, model)

    for metric_id in ("dscr_min", "llcr"):
        metric = output["debt_coverage_metrics"][metric_id]
        assert metric["applicability_status"] == "APPLICABLE"
        assert metric["reason_code"] == "READY"
        assert metric["value_status"] == "VALUE_PRESENT"
        assert metric["value"] is not None
        assert output["metrics"][metric_id] == metric["value"]
        assert metric["source_artifact_id"] == output["run_id"]
        assert metric["period_range"] == {
            "start_period": output["periods"][0],
            "end_period": output["periods"][-1],
        }


@pytest.mark.parametrize(
    ("cfads_ready", "debt_schedule_ready", "reason_code"),
    [
        (False, True, "CFADS_NOT_READY"),
        (True, False, "DEBT_SCHEDULE_NOT_READY"),
        (False, False, "CFADS_AND_DEBT_SCHEDULE_NOT_READY"),
    ],
)
def test_debt_coverage_not_ready_reasons_are_deterministic(
    cfads_ready: bool,
    debt_schedule_ready: bool,
    reason_code: str,
) -> None:
    state = _debt_coverage_state(
        declared_debt=True,
        cfads_ready=cfads_ready,
        debt_schedule_ready=debt_schedule_ready,
        has_eligible_debt_service=True,
    )
    assert state == ("NOT_READY", reason_code, ())


def test_debt_coverage_blockers_are_sorted_and_do_not_collapse_to_not_ready() -> None:
    state = _debt_coverage_state(
        declared_debt=True,
        cfads_ready=False,
        debt_schedule_ready=False,
        has_eligible_debt_service=False,
        blocker_codes=("FIN2_Z_BLOCKER", "FIN2_A_BLOCKER", "FIN2_Z_BLOCKER"),
    )
    assert state == (
        "BLOCKED",
        "MULTIPLE_DEBT_COVERAGE_BLOCKERS",
        ("FIN2_A_BLOCKER", "FIN2_Z_BLOCKER"),
    )


def test_unsupported_declared_debt_projects_blocked_metric_objects() -> None:
    document = valid_document()
    document["financing"]["debt_tranches"] = [
        {
            "tranche_id": "debt-custom-applicability",
            "drawdowns": [{"period": "2026-01", "amount": "1000"}],
            "annual_rate": "0.05",
            "tenor_months": 12,
            "principal_grace_months": 0,
            "interest_grace_policy": "paid",
            "repayment_profile": "custom_reviewed",
            "fee_treatment": "expense_upfront",
            "fees": [],
            "lineage": {
                "assumption_refs": ["asm-1"],
                "evidence_refs": ["ev-1"],
            },
        }
    ]
    validated = validate_finance_input(document, binding=binding())
    model = build_financial_model(validated)
    output = serialize_finance_result(validated, model)

    for metric_id in ("dscr_min", "llcr"):
        metric = output["debt_coverage_metrics"][metric_id]
        assert metric["value"] is None
        assert metric["value_status"] == "VALUE_ABSENT"
        assert metric["applicability_status"] == "BLOCKED"
        assert metric["reason_code"] == "FIN2_DEBT_PROFILE_UNSUPPORTED"
        assert metric["blocker_codes"] == [
            "FIN2_DEBT_PROFILE_UNSUPPORTED"
        ]


def test_debt_coverage_schema_is_closed_and_required() -> None:
    schema_path = (
        __import__("pathlib").Path(__file__).resolve().parents[1]
        / "schemas"
        / "finance"
        / "finance-result.v2.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    coverage = schema["properties"]["debt_coverage_metrics"]
    metric = schema["$defs"]["debtCoverageMetric"]

    assert "debt_coverage_metrics" in schema["required"]
    assert coverage["additionalProperties"] is False
    assert coverage["required"] == ["dscr_min", "llcr"]
    assert metric["additionalProperties"] is False
    assert {
        "value_status",
        "applicability_status",
        "reason_code",
        "period_range",
        "unit",
        "currency",
        "grain",
        "source_artifact_id",
        "formula_version",
        "lineage_refs",
    } <= set(metric["required"])

