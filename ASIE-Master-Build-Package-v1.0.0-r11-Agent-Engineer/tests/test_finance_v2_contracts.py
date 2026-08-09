from __future__ import annotations

import copy
from decimal import Decimal

import pytest

from backend.finance_v2 import (
    FinanceContractError,
    ServerBinding,
    add_months,
    canonical_json,
    canonical_sha256,
    monthly_periods,
    parse_decimal,
    validate_finance_input,
)


MANIFEST_HASH = "sha256:" + "a" * 64


def lineage() -> dict:
    return {"assumption_refs": ["asm-1"], "evidence_refs": ["ev-1"]}


def binding() -> ServerBinding:
    return ServerBinding(
        organization_id="org-1",
        project_id="project-1",
        run_id="run-1",
        approved_manifest_id="manifest-1",
        approved_manifest_hash=MANIFEST_HASH,
        policy_ref="finance-policy-v2-dark",
    )


def valid_document() -> dict:
    periods = monthly_periods("2026-01", 12)
    return {
        "schema_version": "finance-model-input.v2",
        "document_id": "fmi_example01",
        "organization_id": "org-1",
        "project_id": "project-1",
        "run_id": "run-1",
        "currency": "SAR",
        "forecast": {
            "start_period": "2026-01",
            "monthly_periods": 12,
            "construction_periods": 0,
        },
        "archetype_ref": {
            "archetype_id": "arc_retail",
            "version": "1.0.0",
            "registry_hash": "sha256:" + "b" * 64,
        },
        "rounding_policy": {
            "money_scale": 2,
            "ratio_scale": 6,
            "mode": "ROUND_HALF_EVEN",
        },
        "revenue_streams": [
            {
                "stream_id": "rev-primary",
                "model_kind": "product_unit",
                "unit": "unit",
                "volume_series": [{"period": periods[0], "value": "100"}],
                "price_series": [{"period": periods[0], "value": "25.50"}],
                "variable_cost_series": [{"period": periods[0], "value": "10"}],
                "lineage": lineage(),
            }
        ],
        "operating_costs": [],
        "capex_assets": [],
        "working_capital": {
            "mode": "days",
            "dso_days": "15",
            "dio_days": "20",
            "dpo_days": "10",
            "lineage": lineage(),
        },
        "financing": {
            "equity_contributions": [
                {"period": periods[0], "amount": "100000", "lineage": lineage()}
            ],
            "debt_tranches": [],
        },
        "fiscal_policy": {
            "policy_id": "fiscal-none",
            "effective_from": "2026-01-01",
            "modules": [],
            "lineage": lineage(),
        },
        "scenarios": [
            {"scenario_id": "scn_baseline", "kind": "baseline", "overrides": []}
        ],
        "metadata": {
            "approved_manifest_id": "manifest-1",
            "approved_manifest_hash": MANIFEST_HASH,
            "policy_ref": "finance-policy-v2-dark",
        },
    }


def test_decimal_contract_rejects_binary_float_exponent_and_excess_scale() -> None:
    assert parse_decimal("12.3400", "$.value") == Decimal("12.3400")
    for invalid in (12.34, "1e3", "1.123456789", "NaN", "Infinity", "+1"):
        with pytest.raises(FinanceContractError) as error:
            parse_decimal(invalid, "$.value")
        assert error.value.code == "FIN2_DECIMAL_FORMAT"


def test_nonnegative_decimal_contract_is_explicit() -> None:
    with pytest.raises(FinanceContractError) as error:
        parse_decimal("-0.01", "$.value", allow_negative=False)
    assert error.value.code == "FIN2_DECIMAL_NEGATIVE"


def test_monthly_timeline_crosses_year_boundary_and_is_bounded() -> None:
    assert add_months("2026-12", 1) == "2027-01"
    assert add_months("2027-01", -1) == "2026-12"
    assert monthly_periods("2026-11", 12)[-1] == "2027-10"
    for count in (11, 241, True):
        with pytest.raises((TypeError, ValueError)):
            monthly_periods("2026-01", count)


def test_valid_document_is_bound_and_canonicalized_without_live_integration() -> None:
    document = valid_document()
    validated = validate_finance_input(document, binding=binding())
    assert validated.periods == monthly_periods("2026-01", 12)
    assert validated.input_hash == canonical_sha256(document)
    assert validated.canonical_document == canonical_json(document)
    assert validated.thaw() == document


def test_validated_document_is_immutable_against_caller_mutation() -> None:
    document = valid_document()
    validated = validate_finance_input(document, binding=binding())
    original_hash = validated.input_hash
    document["currency"] = "USD"
    document["revenue_streams"][0]["price_series"][0]["value"] = "999"
    assert validated.input_hash == original_hash
    assert validated.thaw()["currency"] == "SAR"
    assert validated.thaw()["revenue_streams"][0]["price_series"][0]["value"] == "25.50"


def test_canonical_hash_is_independent_of_mapping_insertion_order() -> None:
    document = valid_document()
    reordered = dict(reversed(list(document.items())))
    assert canonical_json(document) == canonical_json(reordered)
    assert canonical_sha256(document) == canonical_sha256(reordered)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("organization_id", "org-other"),
        ("project_id", "project-other"),
        ("run_id", "run-other"),
    ],
)
def test_forged_identity_is_rejected(field: str, value: str) -> None:
    document = valid_document()
    document[field] = value
    with pytest.raises(FinanceContractError) as error:
        validate_finance_input(document, binding=binding())
    assert error.value.code == "FIN2_SERVER_BINDING_MISMATCH"
    assert error.value.field_ref == f"$.{field}"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("approved_manifest_id", "manifest-forged"),
        ("approved_manifest_hash", "sha256:" + "c" * 64),
        ("policy_ref", "client-policy"),
    ],
)
def test_forged_server_metadata_is_rejected(field: str, value: str) -> None:
    document = valid_document()
    document["metadata"][field] = value
    with pytest.raises(FinanceContractError) as error:
        validate_finance_input(document, binding=binding())
    assert error.value.code == "FIN2_SERVER_BINDING_MISMATCH"


def test_missing_and_unknown_top_level_fields_fail_closed() -> None:
    missing = valid_document()
    del missing["working_capital"]
    with pytest.raises(FinanceContractError) as error:
        validate_finance_input(missing, binding=binding())
    assert error.value.code == "FIN2_REQUIRED_FIELD"

    unknown = valid_document()
    unknown["client_model_selection"] = "v2"
    with pytest.raises(FinanceContractError) as error:
        validate_finance_input(unknown, binding=binding())
    assert error.value.code == "FIN2_UNKNOWN_FIELD"


def test_exactly_one_baseline_is_required() -> None:
    for scenarios in (
        [{"scenario_id": "scn_down", "kind": "deterministic", "overrides": []}],
        [
            {"scenario_id": "scn_base_1", "kind": "baseline", "overrides": []},
            {"scenario_id": "scn_base_2", "kind": "baseline", "overrides": []},
        ],
    ):
        document = valid_document()
        document["scenarios"] = scenarios
        with pytest.raises(FinanceContractError) as error:
            validate_finance_input(document, binding=binding())
        assert error.value.code == "FIN2_BASELINE_COUNT"


def test_series_rejects_duplicate_unordered_and_out_of_horizon_periods() -> None:
    base = valid_document()
    series = base["revenue_streams"][0]["volume_series"]

    duplicate = copy.deepcopy(base)
    duplicate["revenue_streams"][0]["volume_series"] = [series[0], dict(series[0])]
    with pytest.raises(FinanceContractError) as error:
        validate_finance_input(duplicate, binding=binding())
    assert error.value.code == "FIN2_PERIOD_DUPLICATE"

    unordered = copy.deepcopy(base)
    unordered["revenue_streams"][0]["volume_series"] = [
        {"period": "2026-02", "value": "10"},
        {"period": "2026-01", "value": "10"},
    ]
    with pytest.raises(FinanceContractError) as error:
        validate_finance_input(unordered, binding=binding())
    assert error.value.code == "FIN2_PERIOD_ORDER"

    outside = copy.deepcopy(base)
    outside["revenue_streams"][0]["volume_series"][0]["period"] = "2027-01"
    with pytest.raises(FinanceContractError) as error:
        validate_finance_input(outside, binding=binding())
    assert error.value.code == "FIN2_PERIOD_HORIZON"


def test_unregistered_revenue_formula_surface_is_rejected() -> None:
    document = valid_document()
    document["revenue_streams"][0]["model_kind"] = "eval(user_expression)"
    with pytest.raises(FinanceContractError) as error:
        validate_finance_input(document, binding=binding())
    assert error.value.code == "FIN2_REVENUE_MODEL"


def test_fiscal_module_requires_bounded_rate() -> None:
    missing = valid_document()
    missing["fiscal_policy"]["modules"] = ["vat"]
    with pytest.raises(FinanceContractError) as error:
        validate_finance_input(missing, binding=binding())
    assert error.value.code == "FIN2_DECIMAL_FORMAT"

    excessive = valid_document()
    excessive["fiscal_policy"]["modules"] = ["vat"]
    excessive["fiscal_policy"]["vat_rate"] = "1.01"
    with pytest.raises(FinanceContractError) as error:
        validate_finance_input(excessive, binding=binding())
    assert error.value.code == "FIN2_FISCAL_RATE"


def test_debt_grace_must_be_less_than_tenor() -> None:
    document = valid_document()
    document["financing"]["debt_tranches"] = [
        {
            "tranche_id": "debt-1",
            "drawdowns": [{"period": "2026-01", "amount": "1000"}],
            "annual_rate": "0.05",
            "tenor_months": 12,
            "principal_grace_months": 12,
            "interest_grace_policy": "paid",
            "repayment_profile": "annuity",
            "fees": [],
            "lineage": lineage(),
        }
    ]
    with pytest.raises(FinanceContractError) as error:
        validate_finance_input(document, binding=binding())
    assert error.value.code == "FIN2_DEBT_GRACE"
