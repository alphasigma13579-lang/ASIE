from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schemas" / "finance"
ACR = ROOT / "docs" / "ACR-FIN-002-FINANCE-MODEL-V2-AND-PROJECT-ARCHETYPE-CONTRACT-2026-08-09.md"

INPUT_SCHEMA = SCHEMA_DIR / "finance-model-input.v2.schema.json"
ARCHETYPE_SCHEMA = SCHEMA_DIR / "project-archetype.v1.schema.json"
RESULT_SCHEMA = SCHEMA_DIR / "finance-result.v2.schema.json"

EXPECTED_ARCHETYPE_FAMILIES = {
    "retail_trade",
    "manufacturing",
    "food_hospitality",
    "professional_services",
    "saas_subscription",
    "marketplace_commission",
    "real_estate_lease",
    "transport_logistics",
    "capacity_health_education",
    "agriculture_cycle",
    "construction_contract",
}

FROZEN_FILES = {
    "backend/aas_kernel.py",
    "backend/aas_registry.py",
    "backend/heart_controller.py",
    "backend/bus_controller.py",
    "backend/system_bus.py",
    "backend/socket_contracts.py",
    "backend/module_runtime.py",
    "backend/project_run_workflow.py",
    "backend/snapshot_assembly.py",
    "backend/runtime_freeze.py",
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_s1_artifacts_exist_and_are_utf8_json() -> None:
    assert ACR.is_file()
    for path in (INPUT_SCHEMA, ARCHETYPE_SCHEMA, RESULT_SCHEMA):
        document = load(path)
        assert document["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert document["type"] == "object"
        assert document["additionalProperties"] is False


def test_finance_input_contract_binds_identity_versions_and_core_ledgers() -> None:
    document = load(INPUT_SCHEMA)
    required = set(document["required"])
    assert {
        "schema_version",
        "document_id",
        "organization_id",
        "project_id",
        "run_id",
        "currency",
        "forecast",
        "archetype_ref",
        "rounding_policy",
        "revenue_streams",
        "operating_costs",
        "capex_assets",
        "working_capital",
        "financing",
        "fiscal_policy",
        "valuation_policy",
        "scenarios",
        "metadata",
    } <= required
    assert document["properties"]["schema_version"]["const"] == "finance-model-input.v2"
    assert document["properties"]["forecast"]["properties"]["monthly_periods"] == {
        "type": "integer",
        "minimum": 12,
        "maximum": 240,
    }
    assert document["properties"]["metadata"]["required"] == [
        "approved_manifest_id",
        "approved_manifest_hash",
        "policy_ref",
    ]
    baseline_rule = document["properties"]["scenarios"]["allOf"][0]
    assert baseline_rule["minContains"] == baseline_rule["maxContains"] == 1
    assert document["$defs"]["decimal"]["type"] == "string"
    assert "pattern" in document["$defs"]["decimal"]
    assert document["properties"]["rounding_policy"]["properties"]["mode"]["enum"] == [
        "ROUND_HALF_EVEN"
    ]


def test_archetype_interface_has_all_mandatory_families_and_human_gate() -> None:
    document = load(ARCHETYPE_SCHEMA)
    actual = set(document["properties"]["family"]["enum"])
    assert actual == EXPECTED_ARCHETYPE_FAMILIES
    assert document["properties"]["status"]["enum"] == [
        "draft",
        "finance_reviewed",
        "sector_reviewed",
        "approved_l1",
        "deprecated",
    ]
    encoded = json.dumps(document, ensure_ascii=False, sort_keys=True)
    assert '"approved_l1"' in encoded
    assert '"finance_reviewer_status"' in encoded
    assert '"sector_reviewer_status"' in encoded
    assert '"accepted"' in encoded
    assert '"golden_case_refs"' in encoded


def test_finance_result_contract_requires_three_statements_and_fail_closed_evidence() -> None:
    document = load(RESULT_SCHEMA)
    statement_required = set(document["properties"]["statements"]["required"])
    assert statement_required == {
        "income_statement",
        "balance_sheet",
        "cash_flow_statement",
    }
    assert document["properties"]["schema_version"]["const"] == "finance-result.v2"
    invariants = document["properties"]["invariants"]
    assert invariants["minItems"] == 0
    assert invariants["maxItems"] == 14
    ready_invariants = document["allOf"][0]["then"]["properties"]["invariants"]
    assert ready_invariants["minItems"] == 14
    assert len(invariants["items"]["properties"]["invariant_id"]["enum"]) == 14
    assert document["properties"]["legacy_projection"]["properties"]["derived_from"][
        "const"
    ] == "finance-result.v2"
    legacy_required = set(
        document["properties"]["legacy_projection"]["allOf"][0]["then"]["properties"][
            "payload"
        ]["required"]
    )
    assert {"baseline", "scenarios", "debt_service_profile", "monte_carlo"} <= legacy_required
    encoded = json.dumps(document, ensure_ascii=False, sort_keys=True)
    assert '"maxItems": 0' in encoded
    assert '"minItems": 1' in encoded
    assert '"status": {"const": "failed"}' in encoded


def test_acr_is_traceable_and_does_not_authorize_frozen_changes_or_release() -> None:
    text = ACR.read_text(encoding="utf-8")
    assert "main@f4d38bb28c950c0ebae0e465ad7d2d4534f6c081" in text
    assert "PASS — BUILD READY FOR S2 WITHIN THIS ACR" in text
    assert "G1 يبقى BLOCK" in text
    assert "لا شبكة ولا مزود ولا Production" in text
    assert "finance.calculate.v1" in text
    assert "finance.result.v1" in text
    assert "finance_model_v2" in text
    assert "T-FIN" in text and "T-PROP" in text
    assert "Phase M0" in text and "Phase M5" in text
    assert "التراجع والاستعادة" in text
    for frozen_path in FROZEN_FILES:
        assert f"`{frozen_path}`" in text


def test_s1_schema_ids_are_unique_and_versioned() -> None:
    ids = {load(path)["$id"] for path in (INPUT_SCHEMA, ARCHETYPE_SCHEMA, RESULT_SCHEMA)}
    assert len(ids) == 3
    assert all(".schema.json" in schema_id for schema_id in ids)
