from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from backend.finance_v2 import (
    build_financial_model,
    canonical_json,
    serialize_finance_result,
    validate_finance_input,
)
from tests.test_finance_v2_contracts import binding, valid_document


TARGET = "$.revenue_streams[rev-primary].volume_series[*].value"


def _serialize(document):
    validated = validate_finance_input(document, binding=binding())
    model = build_financial_model(validated)
    return validated, serialize_finance_result(validated, model)


def test_deterministic_scenario_changes_governed_driver_and_is_reproducible() -> None:
    document = valid_document()
    document["scenarios"] = [
        {"scenario_id": "scn_base", "kind": "baseline", "overrides": []},
        {
            "scenario_id": "scn_down",
            "kind": "deterministic",
            "overrides": [
                {
                    "target_ref": TARGET,
                    "operation": "multiply",
                    "value": "0.5",
                }
            ],
        },
    ]

    validated, first = _serialize(document)
    _, second = _serialize(document)
    rows = {row["scenario_id"]: row for row in first["scenarios"]}
    baseline = rows["scn_base"]
    downside = rows["scn_down"]

    assert first["status"] == "ready"
    assert first["blockers"] == []
    assert baseline["kind"] == "baseline"
    assert baseline["input_hash"] == validated.input_hash
    assert baseline["override_refs"] == []
    assert downside["kind"] == "deterministic"
    assert downside["status"] == "ready"
    assert downside["input_hash"] != validated.input_hash
    assert downside["override_refs"] == [TARGET]
    assert Decimal(downside["metrics"]["npv_unlevered"]) < Decimal(
        baseline["metrics"]["npv_unlevered"]
    )
    assert validated.thaw()["revenue_streams"][0]["volume_series"][0]["value"] == "100"
    assert canonical_json(first) == canonical_json(second)


def test_specific_period_override_is_scoped_and_has_distinct_hash() -> None:
    document = valid_document()
    target = "$.revenue_streams[rev-primary].price_series[2026-01].value"
    document["scenarios"].append(
        {
            "scenario_id": "scn_month_one",
            "kind": "deterministic",
            "overrides": [
                {
                    "target_ref": target,
                    "operation": "replace",
                    "value": "1",
                }
            ],
        }
    )

    validated, output = _serialize(document)
    scenario = output["scenarios"][1]

    assert scenario["status"] == "ready"
    assert scenario["input_hash"] != validated.input_hash
    assert scenario["override_refs"] == [target]
    assert scenario["metrics"] != output["scenarios"][0]["metrics"]


def test_missing_allowlisted_target_fails_closed_in_result() -> None:
    document = valid_document()
    document["scenarios"].append(
        {
            "scenario_id": "scn_missing",
            "kind": "deterministic",
            "overrides": [
                {
                    "target_ref": "$.revenue_streams[rev-missing].volume_series[*].value",
                    "operation": "multiply",
                    "value": "0.5",
                }
            ],
        }
    )

    _, output = _serialize(document)
    scenario = output["scenarios"][1]

    assert output["status"] == "not_ready"
    assert scenario["status"] == "invalid"
    assert all(value is None for value in scenario["metrics"].values())
    assert [item["code"] for item in output["blockers"]] == [
        "FIN2_SCENARIO_INVALID"
    ]


def test_invalid_scenario_arithmetic_is_not_coerced_to_zero() -> None:
    document = valid_document()
    document["scenarios"].append(
        {
            "scenario_id": "scn_negative",
            "kind": "deterministic",
            "overrides": [
                {
                    "target_ref": TARGET,
                    "operation": "add",
                    "value": "-1000",
                }
            ],
        }
    )

    _, output = _serialize(document)

    assert output["status"] == "not_ready"
    assert output["scenarios"][1]["status"] == "invalid"
    assert output["blockers"][0]["code"] == "FIN2_SCENARIO_INVALID"


def test_simulation_request_is_explicitly_not_ready_until_calibrated() -> None:
    document = valid_document()
    document["scenarios"].append(
        {
            "scenario_id": "scn_mc",
            "kind": "simulation",
            "overrides": [],
            "simulation": {
                "seed": 42,
                "iterations": 1000,
                "distribution_profile_ref": "dist-reviewed-v1",
                "correlation_profile_ref": "corr-reviewed-v1",
            },
        }
    )

    validated, output = _serialize(document)
    scenario = output["scenarios"][1]

    assert output["status"] == "not_ready"
    assert scenario["status"] == "not_ready"
    assert scenario["input_hash"] == validated.input_hash
    assert all(value is None for value in scenario["metrics"].values())
    assert scenario["simulation_summary"] == {
        "seed": 42,
        "iterations": 1000,
        "distribution_profile_ref": "dist-reviewed-v1",
        "correlation_profile_ref": "corr-reviewed-v1",
        "quantiles": {},
    }
    assert output["blockers"][0]["code"] == "FIN2_SIMULATION_NOT_READY"


def test_scenario_json_schemas_expose_governed_contract() -> None:
    schema_dir = Path(__file__).resolve().parents[1] / "schemas" / "finance"
    input_schema = json.loads(
        (schema_dir / "finance-model-input.v2.schema.json").read_text(
            encoding="utf-8"
        )
    )
    result_schema = json.loads(
        (schema_dir / "finance-result.v2.schema.json").read_text(
            encoding="utf-8"
        )
    )

    scenario_input = input_schema["properties"]["scenarios"]["items"]
    target = scenario_input["properties"]["overrides"]["items"]["properties"][
        "target_ref"
    ]
    assert target["pattern"].startswith("^(?:\\$\\.")
    assert len(scenario_input["allOf"]) == 3

    scenario_result = result_schema["properties"]["scenarios"]["items"]
    assert {
        "scenario_id",
        "kind",
        "status",
        "input_hash",
        "override_refs",
        "metrics",
    } <= set(scenario_result["required"])
    assert scenario_result["properties"]["metrics"]["$ref"] == "#/properties/metrics"


def test_legacy_projection_with_nonbaseline_scenario_fails_closed() -> None:
    document = valid_document()
    document["scenarios"].append(
        {
            "scenario_id": "scn_down",
            "kind": "deterministic",
            "overrides": [
                {
                    "target_ref": TARGET,
                    "operation": "multiply",
                    "value": "0.9",
                }
            ],
        }
    )
    validated = validate_finance_input(document, binding=binding())
    model = build_financial_model(validated)

    output = serialize_finance_result(
        validated,
        model,
        include_legacy_projection=True,
    )

    assert output["status"] == "not_ready"
    assert output["legacy_projection"] == {
        "schema_version": "finance.result.v1-compatible",
        "status": "not_available",
        "derived_from": "finance-result.v2",
        "payload": {},
    }
    assert output["blockers"][-1]["code"] == (
        "FIN2_LEGACY_SCENARIO_PROJECTION_NOT_READY"
    )
