from __future__ import annotations

import json
import re

from backend.finance_v2 import (
    build_financial_model,
    canonical_json,
    serialize_finance_result,
    validate_finance_input,
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
    assert output["engine_version"] == "2.0.0-dark.1"
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
    assert payload["monte_carlo"] == {"status": "not_ready", "p_pass": None}
    assert payload["sensitivity"] is None
    assert payload["operational_sensitivity"] is None


def test_balance_sheet_equity_projection_is_cumulative() -> None:
    output = result()
    balance = {
        line["line_id"]: line["values"]
        for line in output["statements"]["balance_sheet"]
    }
    contributed = balance["contributed_equity"]
    assert contributed[0]["value"] == "100000.00"
    assert contributed[-1]["value"] == "100000.00"
