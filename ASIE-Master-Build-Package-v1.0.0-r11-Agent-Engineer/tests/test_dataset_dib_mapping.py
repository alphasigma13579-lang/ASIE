from __future__ import annotations

import pytest

from backend.dataset_dib_mapping import (
    MAPPING_CONTRACT_ID,
    apply_mapping_decisions,
    create_mapping_draft,
    mapping_to_blueprint,
)
from backend.dib_runtime import build_approved_input_manifest, validate_manifest_for_runtime


def _project() -> dict:
    return {"project_id": "project-1", "sector": "Food Service", "activity": "shawarma_shop"}


def _payload() -> dict:
    return {
        "file_name": "inputs.csv",
        "csv_text": (
            "input_key,label,value\n"
            "startup_cost,تكلفة التأسيس,100000\n"
            "monthly_fixed_cost,المصروفات الشهرية,20000\n"
            "unit_price,سعر البيع,18\n"
            "variable_cost,تكلفة الوحدة,7\n"
            "monthly_units,المبيعات الشهرية,3500\n"
        ),
    }


def test_mapping_draft_is_deterministic_and_requires_review() -> None:
    first = create_mapping_draft(_payload(), project_profile=_project())
    second = create_mapping_draft(_payload(), project_profile=_project())
    assert first["contract_id"] == MAPPING_CONTRACT_ID
    assert first["mapping_id"] == second["mapping_id"]
    assert first["status"] == "review_required"
    assert first["policy"]["raw_input_finance_bypass_allowed"] is False
    assert len(first["proposals"]) == 5
    assert all(item["status"] == "review_required" for item in first["proposals"])


def test_mapping_cannot_enter_blueprint_before_review() -> None:
    draft = create_mapping_draft(_payload(), project_profile=_project())
    with pytest.raises(ValueError, match="dataset_mapping_not_ready"):
        mapping_to_blueprint(draft)


def test_accepting_all_rows_builds_approved_manifest() -> None:
    draft = create_mapping_draft(_payload(), project_profile=_project())
    decisions = [{"proposal_id": item["proposal_id"], "action": "accept"} for item in draft["proposals"]]
    reviewed = apply_mapping_decisions(draft, decisions)
    assert reviewed["status"] == "ready"
    assert reviewed["summary"] == {"accepted": 5, "unresolved": 0, "rejected": 0}

    blueprint = mapping_to_blueprint(reviewed)
    assert blueprint["source"] == "dataset_mapping"
    assert blueprint["dataset_mapping"]["raw_input_finance_bypass_allowed"] is False
    manifest = build_approved_input_manifest(blueprint)
    gate = validate_manifest_for_runtime(manifest)
    assert manifest["status"] == "approved"
    assert gate["status"] == "passed"
    assert manifest["normalized_inputs"]["startup_cost"] == 100000
    assert manifest["normalized_inputs"]["monthly_units"] == 3500


def test_edit_decision_can_correct_target_and_value() -> None:
    payload = {"file_name": "inputs.csv", "csv_text": "label,value\nتكلفة عامة,12\n"}
    draft = create_mapping_draft(payload, project_profile=_project())
    proposal = draft["proposals"][0]
    reviewed = apply_mapping_decisions(
        draft,
        [{"proposal_id": proposal["proposal_id"], "action": "edit", "input_key": "unit_price", "value": 21}],
    )
    assert reviewed["status"] == "ready"
    blueprint = mapping_to_blueprint(reviewed)
    row = next(item for item in blueprint["items"] if item["input_key"] == "unit_price")
    assert row["value"] == 21
    assert row["review_status"] == "approved"


def test_rejected_or_unresolved_rows_never_reach_blueprint() -> None:
    draft = create_mapping_draft(_payload(), project_profile=_project())
    decisions = []
    for index, item in enumerate(draft["proposals"]):
        decisions.append({"proposal_id": item["proposal_id"], "action": "reject" if index == 0 else "accept"})
    reviewed = apply_mapping_decisions(draft, decisions)
    assert reviewed["status"] == "ready"
    blueprint = mapping_to_blueprint(reviewed)
    startup = next(item for item in blueprint["items"] if item["input_key"] == "startup_cost")
    assert startup["value_state"] == "UNKNOWN"
    manifest = build_approved_input_manifest(blueprint)
    assert manifest["status"] == "blocked"


def test_zero_requires_intentional_zero_state_after_user_acceptance() -> None:
    payload = {
        "file_name": "inputs.csv",
        "csv_text": (
            "input_key,label,value\n"
            "startup_cost,تأسيس,0\n"
            "monthly_fixed_cost,شهري,1\n"
            "unit_price,سعر,1\n"
            "variable_cost,تكلفة,1\n"
            "monthly_units,عدد,1\n"
        ),
    }
    draft = create_mapping_draft(payload, project_profile=_project())
    reviewed = apply_mapping_decisions(
        draft,
        [{"proposal_id": item["proposal_id"], "action": "accept"} for item in draft["proposals"]],
    )
    blueprint = mapping_to_blueprint(reviewed)
    startup = next(item for item in blueprint["items"] if item["input_key"] == "startup_cost")
    assert startup["value_state"] == "INTENTIONAL_ZERO"
    assert build_approved_input_manifest(blueprint)["status"] == "approved"


def test_unknown_proposal_and_invalid_action_are_rejected() -> None:
    draft = create_mapping_draft(_payload(), project_profile=_project())
    with pytest.raises(ValueError, match="unknown_dataset_mapping_proposal"):
        apply_mapping_decisions(draft, [{"proposal_id": "missing", "action": "accept"}])
    with pytest.raises(ValueError, match="invalid_dataset_mapping_decision"):
        apply_mapping_decisions(draft, [{"proposal_id": draft["proposals"][0]["proposal_id"], "action": "approve_all"}])
