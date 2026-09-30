from __future__ import annotations

import json
import hashlib
from copy import deepcopy
import re

import pytest
from pathlib import Path


MANIFEST_PATH = Path(__file__).resolve().parents[2] / "FOUNDATION-COMPLETE-20.json"
EXPECTED_FROZEN_FILES = {
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
REQUIRED_PACKAGE_IDS = {f"FC20-{number:02d}" for number in range(1, 17)}


def load_manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_program_is_fail_closed_and_does_not_authorize_launch() -> None:
    manifest = load_manifest()
    assert manifest["program_id"] == "FOUNDATION-COMPLETE-20"
    assert manifest["status"] == "ACTIVE_IMPLEMENTATION_PROGRAM"
    assert manifest["current_release_verdict"] == "BLOCK"
    assert manifest["public_release_authorized"] is False
    assert manifest["external_network_authorized"] is False
    assert manifest["provider_activation_authorized"] is False
    assert manifest["rules"]["no_provider_or_network_activation_by_this_manifest"] is True


def test_package_registry_is_complete_unique_and_acyclic() -> None:
    packages = load_manifest()["packages"]
    by_id = {package["id"]: package for package in packages}
    assert set(by_id) == REQUIRED_PACKAGE_IDS
    assert len(by_id) == len(packages)

    for package in packages:
        assert package["priority"] in {"P0", "P1", "P2"}
        assert package["state"] in {"OPEN", "BLOCKED_BY_PREDECESSOR", "ACR_REQUIRED", "IN_PROGRESS", "COMPLETE"}
        assert package["scope"]
        assert package["tests"]
        assert package["id"] not in package["depends_on"]
        assert set(package["depends_on"]).issubset(by_id)

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(package_id: str) -> None:
        assert package_id not in visiting, f"dependency_cycle:{package_id}"
        if package_id in visited:
            return
        visiting.add(package_id)
        for dependency in by_id[package_id]["depends_on"]:
            visit(dependency)
        visiting.remove(package_id)
        visited.add(package_id)

    for package_id in by_id:
        visit(package_id)


def test_closed_beta_package_depends_on_every_foundational_package() -> None:
    packages = {package["id"]: package for package in load_manifest()["packages"]}
    release_package = packages["FC20-16"]
    assert set(release_package["depends_on"]) == REQUIRED_PACKAGE_IDS - {"FC20-16"}
    assert release_package["state"] == "BLOCKED_BY_PREDECESSOR"


def test_frozen_boundary_is_exact_and_requires_separate_acr() -> None:
    manifest = load_manifest()
    assert set(manifest["frozen_files"]) == EXPECTED_FROZEN_FILES
    assert manifest["rules"]["frozen_runtime_changes_require_separate_acr"] is True
    packages = {package["id"]: package for package in manifest["packages"]}
    assert packages["FC20-12"]["state"] == "ACR_REQUIRED"
    assert packages["FC20-12"]["acr"] is True


def test_complete_state_requires_executable_evidence_not_documentation() -> None:
    manifest = load_manifest()
    required = set(manifest["rules"]["package_complete_requires"])
    assert required == {
        "implementation_paths",
        "test_paths",
        "workflow_run_id",
        "commit_sha",
        "rollback_proof",
        "residual_risk_review",
    }
    assert manifest["rules"]["docs_only_completion_forbidden"] is True
    assert manifest["rules"]["exact_commit_evidence_required"] is True
    for package in manifest["packages"]:
        if package["state"] == "COMPLETE":
            evidence = package.get("completion_evidence", {})
            assert required.issubset(evidence)
            assert all(evidence[key] for key in required)


def test_active_and_complete_packages_have_completed_dependencies() -> None:
    packages = {package["id"]: package for package in load_manifest()["packages"]}
    in_progress = [package for package in packages.values() if package["state"] == "IN_PROGRESS"]
    assert len(in_progress) <= 1
    for package in packages.values():
        if package["state"] in {"IN_PROGRESS", "COMPLETE"}:
            assert all(packages[dependency]["state"] == "COMPLETE" for dependency in package["depends_on"])


def test_complete_package_evidence_uses_exact_sha_and_workflow_ids() -> None:
    for package in load_manifest()["packages"]:
        if package["state"] != "COMPLETE":
            continue
        evidence = package["completion_evidence"]
        assert re.fullmatch(r"[0-9a-f]{40}", evidence["commit_sha"])
        workflow_ids = evidence["workflow_run_id"]
        assert isinstance(workflow_ids, list) and workflow_ids
        assert all(str(workflow_id).isdigit() for workflow_id in workflow_ids)
        assert evidence["residual_risk_review"]["frozen_files_changed"] is False

def test_fc20_04_completion_gates_fc20_05_without_authorizing_launch() -> None:
    """Verify completed predecessors open FC20-05 without authorizing launch."""
    manifest = load_manifest()
    packages = {package["id"]: package for package in manifest["packages"]}
    fc20_03 = packages["FC20-03"]
    fc20_04 = packages["FC20-04"]
    fc20_05 = packages["FC20-05"]

    assert fc20_03["state"] == "COMPLETE"
    assert fc20_03["completion_evidence"]["commit_sha"] == "e63f1039ad5a2a1278f0c43a184bbfe4a4862125"
    assert all(
        provider["status"] == "PASS"
        for provider in fc20_03["completion_evidence"]["live_preflight"].values()
    )
    assert fc20_03["completion_evidence"]["residual_risk_review"]["frozen_files_changed"] is False
    assert fc20_04["state"] == "COMPLETE"
    assert all(packages[dependency]["state"] == "COMPLETE" for dependency in fc20_04["depends_on"])
    assert fc20_04["completion_evidence"]["commit_sha"] == "ef4579c7f41dead63a506f7cdf6e163d11dd5c74"
    assert fc20_04["completion_evidence"]["workflow_run_id"] == ["30968258854", "30968258858"]
    assert fc20_04["completion_evidence"]["residual_risk_review"]["frozen_files_changed"] is False
    assert fc20_05["state"] == "IN_PROGRESS"
    assert fc20_05["acr"] is True
    assert fc20_05["opened_from_commit"] == "6247a3fed8bb9cd973d36e47379cbff99d492733"
    assert fc20_05["acr_document"].endswith(
        "docs/ACR-FC20-05-PUBLIC-ECONOMIC-KNOWLEDGE-2026-08-23.md"
    )
    assert all(packages[dependency]["state"] == "COMPLETE" for dependency in fc20_05["depends_on"])
    assert manifest["current_release_verdict"] == "BLOCK"
    assert manifest["external_network_authorized"] is False
    assert manifest["provider_activation_authorized"] is False
    assert manifest["public_release_authorized"] is False

# This is a repository-governance check, not a runtime admission service.
# Registration records the owner's scope decision; it cannot activate a slice.
ROUTING_SCOPE_SHA = "d8fdedd8c768c0eb4604465fdcf870417131aff0"
ROUTING_SCOPE_BLOB = "20e3374e01ebf64260ff4d54b15b44503a0b154f"
ROUTING_SCOPE_URL = (
    "https://github.com/alphasigma13579-lang/ASIE/blob/" + ROUTING_SCOPE_SHA
    + "/ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/docs/"
    + "FC20-12-ROUTING-SCOPE-CHANGE-2026-09-27.md"
)
ROUTING_CONTROL_OWNERS = {
    "program_scope_synchronization": "Repository and Release Governance",
    "frozen_routing_acr": "AAS Architecture",
    "exact_head_foundation_recheck": "Engineering",
    "fc20_08_context_integrity": "Approved Intelligence Context",
    "fc20_09_ai_contract": "AI Governance / ACR-AIA-09",
    "fc20_11_trusted_input": "DIB / Approved Input Manifest",
    "market_location_source_authority": "ACR-AIA-05/10 and ACR-FC20-10",
    "storage_166_167_compatibility": "Knowledge Storage / Engineering",
    "single_active_execution": "Repository and Release Governance",
}


# Owner accepted the design and this bounded governance PR, not routing execution.
ELIGIBILITY_DESIGN_DECISION = {
    "id": "DECISION-FC20-12-ROUTING-ELIGIBILITY-DESIGN-2026-09-30",
    "record_url": "https://github.com/alphasigma13579-lang/ASIE/pull/176#issuecomment-5898867883",
    "recorded_at": "2026-09-29T21:04:54Z",
    "effect": "DESIGN_AND_GOVERNANCE_PR_ONLY",
    "proposal_commit_sha": "d9172df54bd9cf4f7b1332f8a8da90ce93b99204",
    "proposal_blob_sha": "1fff4ec999a600c4c1c80f550780dd48f4c3c30d"
}


# Program ordering is repository governance, never a runtime permission or lock.
# Current v2 registers defensive enabling only; no start decision is admitted.
ORDERING_DECISION = json.loads(r'''{
    "id": "DECISION-FC20-ROUTING-PRIORITY-2026-09-28",
    "record_url": "https://github.com/alphasigma13579-lang/ASIE/pull/173#issuecomment-5865171335",
    "recorded_at": "2026-09-28T07:10:06Z",
    "effect": "ORDERING_AND_GOVERNANCE_PR_ONLY"
}''')
HELD_PACKAGES = json.loads(r'''[
    {
        "package_id": "FC20-05",
        "reason": "ROUTING_PRIORITY_PENDING_ENTRY",
        "checkpoint_document": "ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/docs/FC20-ROUTING-PRIORITY-AND-FC20-05-CHECKPOINT-2026-09-28.md",
        "checkpoint_base_commit": "d56e4e5cdbb67f7e079956cba1b9cf58736a210f",
        "resume_requirement": "OWNER_DECISION_AND_EXACT_HEAD_RECHECK"
    }
]''')



# A pinned owner design decision permits this registration PR only, not start.
# The expected record is reviewed code, never copied from the supplied manifest.
DEFENSIVE_REGISTRATION = json.loads(r'''{
    "schema": "asie.foundation.defensive-enabling.v1",
    "id": "f01a_defensive_ingress",
    "state": "REGISTERED_BLOCKED",
    "registry_effect": "BOUNDED_DEFENSIVE_ENABLING_ONLY",
    "execution_authorized": false,
    "prerequisite_for": {
        "package_id": "FC20-12",
        "slice_id": "routing_repair"
    },
    "scope_document": {
        "url": "https://github.com/alphasigma13579-lang/ASIE/blob/08a825ae046ba3595981590ca03ea5ef03f04ace/ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/docs/FC20-12-F01-TRUSTED-CONTEXT-INGRESS-REPAIR-PLAN-2026-10-01.md",
        "commit_sha": "08a825ae046ba3595981590ca03ea5ef03f04ace",
        "blob_sha": "c80cb6adaa442f43c98da7b9eb34c7cc9dcd9521"
    },
    "owner_scope_decision": {
        "id": "DECISION-FC20-12-F01A-SCOPE-2026-10-01",
        "record_url": "https://github.com/alphasigma13579-lang/ASIE/pull/179#issuecomment-5920890935",
        "recorded_at": "2026-09-30T22:34:10Z",
        "effect": "SCOPE_AND_COMPATIBILITY_ACCEPTED"
    },
    "registration_decision": {
        "id": "DECISION-FC20-12-F01A-REGISTRATION-DESIGN-2026-10-01",
        "record_url": "https://github.com/alphasigma13579-lang/ASIE/pull/180#issuecomment-5921569549",
        "recorded_at": "2026-09-30T23:30:43Z",
        "effect": "DESIGN_AND_GOVERNANCE_PR_ONLY",
        "proposal_commit_sha": "c000c11f5d9952090c4bfb6622456fb550106bdb",
        "proposal_blob_sha": "e41b6e612b29e22079fbf231b299ad4aab5a9b4b"
    },
    "start_decision": null,
    "subject": {
        "baseline_commit_sha": "8fb47f3668133093197844816eb2a644793e5f20"
    },
    "allowed_paths": [
        "backend/asie_local_api.py",
        "backend/repository.py",
        "backend/intelligence_prerun_service.py",
        "tests/test_repository_intelligence.py",
        "tests/test_intelligence_prerun_service.py",
        "tests/test_intelligence_context_ingress_api.py",
        "docs/FC20-12-F01-TRUSTED-CONTEXT-INGRESS-REPAIR-PLAN-2026-10-01.md"
    ],
    "environment": "DARK_OFFLINE",
    "entry_requirements": [
        "owner_accepted_compatibility",
        "server_owned_defensive_scope",
        "permission_tenant_data_integrity_tests_T01_T09",
        "single_counted_execution",
        "separate_exact_head_start_decision"
    ],
    "delivery_evidence": null,
    "events": [],
    "closure_effect": "NONE",
    "network_authorized": false,
    "provider_activation_authorized": false,
    "deployment_authorized": false
}''')


def validate_defensive_registration(record: dict, active_target: object) -> None:
    """Accept only the reviewed blocked record; metadata cannot authorize start."""
    assert isinstance(record, dict), "invalid_defensive_record"
    assert set(record) == set(DEFENSIVE_REGISTRATION), "defensive_fields"
    assert record == DEFENSIVE_REGISTRATION, "defensive_record_mismatch"
    assert record["execution_authorized"] is False, "defensive_not_authorized"
    assert all(record[key] is False for key in (
        "network_authorized", "provider_activation_authorized", "deployment_authorized",
    )), "defensive_external_effect"
    assert active_target is None, "defensive_start_not_authorized"


def validate_defensive_transition_fixture(
    record: dict, slot: object, *, reviewed_decision: dict,
    reviewed_delivery: dict | None = None,
) -> None:
    """Test-only lifecycle model, NOT used to admit the current manifest.

    A future guard transition must pin its real owner decision/evidence separately.
    Test inputs are isolated oracles, not a manifest-supplied authority override.
    """
    target = {"kind": "slice", "package_id": "FC20-12",
              "slice_id": "f01a_defensive_ingress"}
    assert reviewed_decision and record["start_decision"] == reviewed_decision, "fixture_decision"
    assert reviewed_decision["subject"] == record["subject"], "fixture_subject"
    assert reviewed_decision["effect"] == "F01A_DEFENSIVE_START_ONLY", "fixture_effect"
    fixed = deepcopy(record)
    for key in ("state", "execution_authorized", "start_decision", "delivery_evidence", "events"):
        fixed[key] = deepcopy(DEFENSIVE_REGISTRATION[key])
    assert fixed == DEFENSIVE_REGISTRATION, "fixture_scope"
    assert all(record[key] is False for key in (
        "network_authorized", "provider_activation_authorized", "deployment_authorized",
    )), "fixture_external_effect"
    assert isinstance(record["events"], list) and record["events"], "fixture_history"
    assert record["events"][0] == {
        "type": "START", "decision_id": reviewed_decision["id"],
    }, "fixture_start_history"
    if record["state"] == "IN_PROGRESS":
        assert record["execution_authorized"] is True, "fixture_active_flag"
        assert slot == target, "fixture_active_slot"
        assert record["delivery_evidence"] is None, "fixture_premature_delivery"
        assert record["events"][-1]["type"] in {"START", "STOP_CHECKPOINT"}, "fixture_active_history"
    else:
        assert record["state"] == "DELIVERED", "fixture_state"
        assert record["execution_authorized"] is False and slot is None, "fixture_release_slot"
        assert reviewed_delivery and record["delivery_evidence"] == reviewed_delivery, "fixture_delivery"
        assert re.fullmatch(r"[0-9a-f]{40}", reviewed_delivery["commit_sha"]), "fixture_delivery_sha"
        assert reviewed_delivery["test_ids"] == [f"T-{n:02d}" for n in range(1, 10)], "fixture_tests"
        assert reviewed_delivery["review_url"] and reviewed_delivery["owner_decision_url"], "fixture_review"
        assert record["events"][-1] == {
            "type": "DELIVERED", "commit_sha": reviewed_delivery["commit_sha"],
        }, "fixture_delivery_history"


def active_execution_targets(packages: list[dict], held_ids: set[str]) -> list[str]:
    """Count package and slice claims; a package hold never hides its slices."""
    active = []
    for package in packages:
        if package["state"] == "IN_PROGRESS" and package["id"] not in held_ids:
            active.append(package["id"])
        slices = package.get("execution_slices", [])
        assert isinstance(slices, list), "invalid_execution_slices"
        for record in slices:
            assert isinstance(record, dict), "invalid_execution_slice"
            if record.get("state") == "IN_PROGRESS":
                active.append(package["id"] + "/" + record["id"])
    return active


def validate_execution_sequence(manifest: dict) -> None:
    """Validate the owner's ordering/hold record without enabling execution."""
    sequence = manifest.get("execution_sequence")
    assert isinstance(sequence, dict), "missing_execution_sequence"
    assert set(sequence) == {
        "schema", "record_effect", "ordering_decision", "priority_target",
        "max_active_executions", "active_target", "held_packages",
    }, "unknown_or_missing_sequence_field"
    assert sequence["schema"] == "asie.foundation.execution-sequence.v2", "sequence_schema"
    assert sequence["record_effect"] == "BOUNDED_DEFENSIVE_ENABLING_ONLY", "sequence_effect"
    assert sequence["ordering_decision"] == ORDERING_DECISION, "ordering_decision_mismatch"
    assert sequence["priority_target"] == {
        "kind": "slice", "package_id": "FC20-12", "slice_id": "routing_repair",
    }, "priority_target_mismatch"
    assert type(sequence["max_active_executions"]) is int
    assert sequence["max_active_executions"] == 1, "execution_limit"
    assert sequence["active_target"] is None, "execution_entry_not_authorized"
    assert sequence["held_packages"] == HELD_PACKAGES, "checkpoint_hold_mismatch"

    packages = manifest["packages"]
    by_id = {package["id"]: package for package in packages}
    assert set(by_id) == REQUIRED_PACKAGE_IDS and len(by_id) == len(packages)
    assert by_id["FC20-05"]["state"] == "IN_PROGRESS", "held_package_state_mismatch"
    for package in packages:
        assert package["state"] in {
            "OPEN", "BLOCKED_BY_PREDECESSOR", "ACR_REQUIRED", "IN_PROGRESS", "COMPLETE",
        }, "unapproved_package_state"
    held_ids = {entry["package_id"] for entry in sequence["held_packages"]}
    active = active_execution_targets(packages, held_ids)
    assert len(active) <= sequence["max_active_executions"], "multiple_active_executions"
    # Empty slot is a deliberate stop, not an exemption for one unrecorded execution.
    assert not active, "unrecorded_active_execution"


def validate_routing_registration(manifest: dict, *, allow_historical_v1: bool = False) -> None:
    """Fail closed: a later approved schema/checker change is required to execute."""
    packages = {package["id"]: package for package in manifest["packages"]}
    assert set(packages) == REQUIRED_PACKAGE_IDS
    assert len(packages) == len(manifest["packages"])
    for package in manifest["packages"]:
        if package["id"] != "FC20-12":
            assert "execution_slices" not in package, "unexpected_slice_owner"
    parent = packages["FC20-12"]
    assert parent["state"] == "ACR_REQUIRED", "parent_state_not_preserved"
    assert parent["depends_on"] == ["FC20-08", "FC20-09", "FC20-11"], "parent_dependencies_not_preserved"
    slices = parent.get("execution_slices")
    assert isinstance(slices, list) and len(slices) == 2, "missing_or_duplicate_slice"
    assert all(isinstance(item, dict) for item in slices), "invalid_execution_slice"
    assert [item.get("id") for item in slices] == [
        "routing_repair", "f01a_defensive_ingress",
    ], "unknown_or_duplicate_slice"
    validate_defensive_registration(
        slices[1], manifest.get("execution_sequence", {}).get("active_target"),
    )
    record = slices[0]
    assert isinstance(record, dict)
    schema = record.get("schema")
    assert schema in {
        "asie.foundation.routing-registration.v1",
        "asie.foundation.routing-eligibility.v2",
    }, "unapproved_slice_schema"
    is_v2 = schema == "asie.foundation.routing-eligibility.v2"
    assert is_v2 or allow_historical_v1, "current_schema_downgrade"
    fields = {
        "schema", "id", "state", "registry_effect", "execution_authorized",
        "scope_document", "owner_scope_decision", "package_entry_dependencies",
        "required_entry_controls", "closure_effect", "network_authorized",
        "provider_activation_authorized", "deployment_authorized",
    }
    if is_v2:
        fields |= {"design_decision", "eligibility_record"}
    assert set(record) == fields, "unknown_or_missing_slice_field"
    assert record["id"] == "routing_repair"
    # This goal installs an evidence-bearing record, not entry or start authority.
    assert record["state"] == "REGISTERED_BLOCKED", "unapproved_slice_state"
    assert record["registry_effect"] == (
        "EVIDENCE_TRACKING_ONLY" if is_v2 else "REGISTRATION_ONLY"
    ), "unapproved_registry_effect"
    if is_v2:
        assert record["design_decision"] == ELIGIBILITY_DESIGN_DECISION, "design_decision_mismatch"
        assert record["eligibility_record"] == {
            "subject": None,
            "commands": [],
            "paths": [],
            "environment": "DARK_OFFLINE",
            "entry_decision": None,
            "start_decision": None,
            "delivery_evidence": None,
            "invalidation_events": [],
        }, "unapproved_eligibility_claim"
    assert record["closure_effect"] == "NONE"
    for key in (
        "execution_authorized", "network_authorized",
        "provider_activation_authorized", "deployment_authorized",
    ):
        assert record[key] is False, f"unauthorized_slice_effect:{key}"
    assert record["scope_document"] == {
        "url": ROUTING_SCOPE_URL,
        "commit_sha": ROUTING_SCOPE_SHA,
        "blob_sha": ROUTING_SCOPE_BLOB,
    }, "scope_revision_mismatch"
    assert record["owner_scope_decision"] == {
        "id": "DECISION-FC20-12-ROUTING-SCOPE-2026-09-27",
        "record_url": (
            "https://github.com/alphasigma13579-lang/ASIE/pull/171"
            "#issuecomment-5851434784"
        ),
        "recorded_at": "2026-09-27T00:56:14Z",
        "effect": "SCOPE_ORDERING_ONLY",
    }, "owner_decision_mismatch"
    assert record["package_entry_dependencies"] == [
        "FC20-01", "FC20-02", "FC20-03", "FC20-04",
    ]
    assert all(
        packages[dependency]["state"] == "COMPLETE"
        for dependency in record["package_entry_dependencies"]
    ), "incomplete_entry_package"
    controls = record["required_entry_controls"]
    assert isinstance(controls, dict) and set(controls) == set(ROUTING_CONTROL_OWNERS)
    for control, owner in ROUTING_CONTROL_OWNERS.items():
        expected = {"owner": owner, "status": "PENDING", "evidence": None}
        if is_v2:
            expected["verification"] = None
        assert controls[control] == expected, f"unapproved_control_claim:{control}"
    assert packages["FC20-16"]["state"] == "BLOCKED_BY_PREDECESSOR", "release_package_not_blocked"
    assert set(packages["FC20-16"]["depends_on"]) == REQUIRED_PACKAGE_IDS - {"FC20-16"}
    assert sum(package["state"] == "IN_PROGRESS" for package in packages.values()) <= 1, "multiple_active_packages"
    assert set(manifest["frozen_files"]) == EXPECTED_FROZEN_FILES
    assert manifest["rules"]["frozen_runtime_changes_require_separate_acr"] is True
    assert manifest["current_release_verdict"] == "BLOCK"
    for key in (
        "public_release_authorized", "external_network_authorized",
        "provider_activation_authorized",
    ):
        assert manifest[key] is False, "unauthorized_program_effect"
    validate_execution_sequence(manifest)


def test_routing_registration_is_valid_but_not_executable() -> None:
    """Accept the blocked registration without granting execution authority."""
    manifest = load_manifest()
    validate_routing_registration(manifest)
    parent = next(package for package in manifest["packages"] if package["id"] == "FC20-12")
    assert parent["execution_slices"][0]["execution_authorized"] is False


def test_routing_registration_cannot_be_omitted() -> None:
    """Reject a manifest that omits the required routing registration."""
    manifest = load_manifest()
    parent = next(package for package in manifest["packages"] if package["id"] == "FC20-12")
    parent.pop("execution_slices")
    with pytest.raises(AssertionError, match="missing_or_duplicate_slice"):
        validate_routing_registration(manifest)


@pytest.mark.parametrize("path,value", [
    (("schema",), "unknown.v2"),
    (("id",), "parallel_runtime"),
    (("state",), "IN_PROGRESS"),
    (("registry_effect",), "BUILD_AUTHORIZED"),
    (("execution_authorized",), True),
    (("execution_authorized",), 0),
    (("scope_document", "commit_sha"), "0" * 40),
    (("scope_document", "blob_sha"), "0" * 40),
    (("owner_scope_decision", "effect"), "FROZEN_BUILD_APPROVED"),
    (("owner_scope_decision", "record_url"), "https://example.invalid/approval"),
    (("package_entry_dependencies",), ["FC20-01"]),
    (("required_entry_controls",), {}),
    (("required_entry_controls", "frozen_routing_acr", "status"), "APPROVED"),
    (("required_entry_controls", "fc20_08_context_integrity", "evidence"), {"claim": "PASS"}),
    (("closure_effect",), "COMPLETE"),
    (("network_authorized",), True),
    (("provider_activation_authorized",), True),
    (("deployment_authorized",), True),
    (("unknown_execution_override",), True),
])
def test_routing_registration_rejects_unapproved_mutations(path: tuple, value: object) -> None:
    """Reject unauthorized changes to routing scope, controls, or effect flags."""
    manifest = load_manifest()
    parent = next(package for package in manifest["packages"] if package["id"] == "FC20-12")
    target = parent["execution_slices"][0]
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(AssertionError):
        validate_routing_registration(manifest)


@pytest.mark.parametrize("mutation,expected_error", [
    ("duplicate_slice", "missing_or_duplicate_slice"),
    ("other_owner", "unexpected_slice_owner"),
    ("parent_state", "parent_state_not_preserved"),
    ("parent_dependencies", "parent_dependencies_not_preserved"),
    ("entry_incomplete", "incomplete_entry_package"),
    ("release_state", "release_package_not_blocked"),
    ("release_authority", "unauthorized_program_effect"),
    ("second_active_package", "multiple_active_packages"),
])
def test_routing_registration_preserves_program_boundaries(
    mutation: str, expected_error: str,
) -> None:
    """Reject mutations that weaken parent, dependency, or release boundaries."""
    manifest = load_manifest()
    packages = {package["id"]: package for package in manifest["packages"]}
    parent = packages["FC20-12"]
    if mutation == "duplicate_slice":
        parent["execution_slices"] *= 2
    elif mutation == "other_owner":
        packages["FC20-11"]["execution_slices"] = parent["execution_slices"]
    elif mutation == "parent_state":
        parent["state"] = "COMPLETE"
    elif mutation == "parent_dependencies":
        parent["depends_on"] = []
    elif mutation == "entry_incomplete":
        packages["FC20-04"]["state"] = "OPEN"
    elif mutation == "release_state":
        packages["FC20-16"]["state"] = "OPEN"
    elif mutation == "release_authority":
        manifest["public_release_authorized"] = True
    elif mutation == "second_active_package":
        packages["FC20-11"]["state"] = "IN_PROGRESS"
    with pytest.raises(AssertionError, match=rf"^{expected_error}(?:\n|$)"):
        validate_routing_registration(manifest)


def test_routing_registration_is_visible_in_governing_views() -> None:
    """Require governing views to expose the same blocked registration and decision."""
    package_root = Path(__file__).resolve().parents[1]
    paths = [
        "docs/FOUNDATION-COMPLETE-20-CORE-INTELLIGENCE-COMPLETION-PROGRAM-2026-07-29.md",
        "docs/EKB/FOUNDATION-COMPLETE-20-PACKAGE-INDEX.md",
        "docs/ACR-AIA-ROUTING-REMEDIATION-2026-09-27.md",
    ]
    for relative_path in paths:
        text = (package_root / relative_path).read_text(encoding="utf-8")
        assert "routing_repair" in text
        assert "REGISTERED_BLOCKED" in text
        assert "5851434784" in text


def test_ordering_preserves_progress_but_holds_execution() -> None:
    """Preserve unfinished package progress while no active execution target is recorded."""
    manifest = load_manifest()
    validate_execution_sequence(manifest)
    validate_routing_registration(manifest)
    assert active_execution_targets(manifest["packages"], {"FC20-05"}) == []
    packages = {package["id"]: package for package in manifest["packages"]}
    assert packages["FC20-05"]["state"] == "IN_PROGRESS"
    assert packages["FC20-12"]["execution_slices"][0]["state"] == "REGISTERED_BLOCKED"
    assert packages["FC20-12"]["execution_slices"][0]["execution_authorized"] is False


def test_sequence_is_required_not_an_optional_activity_override() -> None:
    """Reject routing registration when the required execution sequence is absent."""
    manifest = load_manifest()
    manifest.pop("execution_sequence")
    with pytest.raises(AssertionError, match="missing_execution_sequence"):
        validate_routing_registration(manifest)


@pytest.mark.parametrize("path,value", [
    (("schema",), "unknown.v2"),
    (("record_effect",), "BUILD_AUTHORIZED"),
    (("ordering_decision", "record_url"), "https://example.invalid/approval"),
    (("ordering_decision", "recorded_at"), "2026-01-01T00:00:00Z"),
    (("ordering_decision", "effect"), "FROZEN_BUILD_APPROVED"),
    (("priority_target", "package_id"), "FC20-11"),
    (("priority_target", "slice_id"), "parallel_runtime"),
    (("max_active_executions",), 2),
    (("max_active_executions",), True),
    (("active_target",), {"kind": "slice", "package_id": "FC20-12", "slice_id": "routing_repair"}),
    (("active_target",), False),
    (("held_packages",), []),
    (("held_packages",), HELD_PACKAGES * 2),
    (("held_packages", 0, "package_id"), "FC20-11"),
    (("held_packages", 0, "checkpoint_base_commit"), "0" * 40),
    (("held_packages", 0, "checkpoint_document"), "docs/nonexistent.md"),
    (("held_packages", 0, "resume_requirement"), "AUTOMATIC_ON_MERGE"),
    (("execution_authorized",), True),
])
def test_sequence_rejects_unapproved_mutations(path: tuple, value: object) -> None:
    """Reject unapproved changes to ordering, holds, or execution authority."""
    manifest = load_manifest()
    target = manifest["execution_sequence"]
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(AssertionError):
        validate_routing_registration(manifest)


@pytest.mark.parametrize("field", [
    "schema", "record_effect", "ordering_decision", "priority_target",
    "max_active_executions", "active_target", "held_packages",
])
def test_sequence_rejects_missing_fields(field: str) -> None:
    """Reject an execution sequence missing any required field."""
    manifest = load_manifest()
    manifest["execution_sequence"].pop(field)
    with pytest.raises(AssertionError, match="unknown_or_missing_sequence_field"):
        validate_routing_registration(manifest)


def test_sequence_counts_package_and_slice_execution_together() -> None:
    """Count package and slice claims together and reject concurrent execution."""
    manifest = load_manifest()
    packages = {package["id"]: package for package in manifest["packages"]}
    packages["FC20-11"]["state"] = "IN_PROGRESS"
    packages["FC20-12"]["execution_slices"][0]["state"] = "IN_PROGRESS"
    assert active_execution_targets(manifest["packages"], {"FC20-05"}) == [
        "FC20-11", "FC20-12/routing_repair",
    ]
    with pytest.raises(AssertionError, match="multiple_active_executions"):
        validate_execution_sequence(manifest)


@pytest.mark.parametrize("claim", ["package", "routing_slice", "held_package_slice"])
def test_empty_slot_denies_even_one_unrecorded_execution(claim: str) -> None:
    """Reject unrecorded execution, including slices inside a held package."""
    manifest = load_manifest()
    packages = {package["id"]: package for package in manifest["packages"]}
    if claim == "package":
        packages["FC20-11"]["state"] = "IN_PROGRESS"
    elif claim == "routing_slice":
        packages["FC20-12"]["execution_slices"][0]["state"] = "IN_PROGRESS"
    else:
        packages["FC20-05"]["execution_slices"] = [
            {"id": "hidden_work", "state": "IN_PROGRESS"},
        ]
    with pytest.raises(AssertionError, match="unrecorded_active_execution"):
        validate_execution_sequence(manifest)
    # Full registration also rejects the unauthorized state/owner.
    with pytest.raises(AssertionError):
        validate_routing_registration(manifest)


@pytest.mark.parametrize("state", ["OPEN", "PAUSED", "COMPLETE"])
def test_hold_does_not_rewrite_package_progress_to_pass_the_check(state: str) -> None:
    """Reject state rewrites that disguise the held package's unfinished progress."""
    manifest = load_manifest()
    package = next(item for item in manifest["packages"] if item["id"] == "FC20-05")
    package["state"] = state
    with pytest.raises(AssertionError, match="held_package_state_mismatch"):
        validate_execution_sequence(manifest)


def test_sequence_decision_checkpoint_and_governing_links_are_present() -> None:
    """Verify the decision, retained checkpoints, and governing-document links."""
    manifest = load_manifest()
    sequence = manifest["execution_sequence"]
    package_root = Path(__file__).resolve().parents[1]
    checkpoint_path = MANIFEST_PATH.parent / sequence["held_packages"][0]["checkpoint_document"]
    checkpoint = checkpoint_path.read_text(encoding="utf-8")
    for required in (
        sequence["ordering_decision"]["record_url"],
        sequence["ordering_decision"]["recorded_at"],
        sequence["held_packages"][0]["checkpoint_base_commit"],
        "2dccc2c45c2b1967e277edf6db6a681a04b2654a",
        "435777008e01bafc73ab3bca86cc8945e311b610",
        "NOT_BUILD_READY", "active_target = null", "historical-baseline verifier",
        "OWNER_ORDERING_DECISION_RECORDED",
    ):
        assert required in checkpoint
    for relative_path in (
        "docs/FOUNDATION-COMPLETE-20-CORE-INTELLIGENCE-COMPLETION-PROGRAM-2026-07-29.md",
        "docs/EKB/FOUNDATION-COMPLETE-20-PACKAGE-INDEX.md",
        "docs/ACR-AIA-ROUTING-REMEDIATION-2026-09-27.md",
        "docs/ASIE-BETA-EXECUTION-MASTER-PLAN-2026-09-09.md",
    ):
        text = (package_root / relative_path).read_text(encoding="utf-8")
        assert checkpoint_path.name in text
        assert "PRIORITY_AND_HOLD_ONLY" in text

def test_routing_v1_blocked_record_remains_compatible() -> None:
    """Historical v1 registration remains valid only in its blocked form."""
    manifest = load_manifest()
    record = next(p for p in manifest["packages"] if p["id"] == "FC20-12")["execution_slices"][0]
    record["schema"] = "asie.foundation.routing-registration.v1"
    record["registry_effect"] = "REGISTRATION_ONLY"
    record.pop("design_decision")
    record.pop("eligibility_record")
    for control in record["required_entry_controls"].values():
        control.pop("verification")
    validate_routing_registration(manifest, allow_historical_v1=True)


@pytest.mark.parametrize("field,value", [
    ("subject", {"commit_sha": "0" * 40}),
    ("commands", ["geocode"]),
    ("paths", ["backend/aas_kernel.py"]),
    ("environment", "LIVE"),
    ("entry_decision", {"effect": "APPROVED"}),
    ("start_decision", {"effect": "START"}),
    ("delivery_evidence", {"status": "PASS"}),
    ("invalidation_events", [{"event": "REVOKED"}]),
])
def test_routing_v2_rejects_unverified_eligibility_claims(field: str, value: object) -> None:
    """Metadata or a claimed decision cannot independently open the blocked slice."""
    manifest = load_manifest()
    record = next(p for p in manifest["packages"] if p["id"] == "FC20-12")["execution_slices"][0]
    record["eligibility_record"][field] = value
    with pytest.raises(AssertionError, match="unapproved_eligibility_claim"):
        validate_routing_registration(manifest)


@pytest.mark.parametrize("mutation", ["missing_control", "unknown_control", "verified_without_proof",
                                     "forged_proof", "changed_owner", "forged_verification", "unknown_field"])
def test_routing_v2_control_evidence_fails_closed(mutation: str) -> None:
    manifest = load_manifest()
    record = next(p for p in manifest["packages"] if p["id"] == "FC20-12")["execution_slices"][0]
    controls = record["required_entry_controls"]
    if mutation == "missing_control":
        controls.pop("single_active_execution")
    elif mutation == "unknown_control":
        controls["invented_bypass"] = controls["single_active_execution"].copy()
    elif mutation == "verified_without_proof":
        controls["single_active_execution"]["status"] = "VERIFIED"
    elif mutation == "forged_proof":
        controls["single_active_execution"]["evidence"] = {"url": "https://example.invalid/pass"}
    elif mutation == "changed_owner":
        controls["single_active_execution"]["owner"] = "browser"
    elif mutation == "forged_verification":
        controls["single_active_execution"]["verification"] = {"result": "PASS"}
    else:
        controls["single_active_execution"]["unexpected"] = "bypass"
    with pytest.raises(AssertionError):
        validate_routing_registration(manifest)


def test_routing_v2_cannot_fill_slot_or_authorize_execution() -> None:
    manifest = load_manifest()
    record = next(p for p in manifest["packages"] if p["id"] == "FC20-12")["execution_slices"][0]
    manifest["execution_sequence"]["active_target"] = {
        "kind": "slice", "package_id": "FC20-12", "slice_id": "routing_repair",
    }
    record["execution_authorized"] = True
    with pytest.raises(AssertionError):
        validate_routing_registration(manifest)


def test_current_manifest_rejects_silent_v1_downgrade() -> None:
    manifest = load_manifest()
    record = next(p for p in manifest["packages"] if p["id"] == "FC20-12")["execution_slices"][0]
    record["schema"] = "asie.foundation.routing-registration.v1"
    record["registry_effect"] = "REGISTRATION_ONLY"
    record.pop("design_decision")
    record.pop("eligibility_record")
    for control in record["required_entry_controls"].values():
        control.pop("verification")
    with pytest.raises(AssertionError, match="current_schema_downgrade"):
        validate_routing_registration(manifest)


@pytest.mark.parametrize("field,value", [
    ("id", "invented_decision"),
    ("record_url", "https://example.invalid/approval"),
    ("recorded_at", "2026-01-01T00:00:00Z"),
    ("effect", "BUILD_AUTHORIZED"),
    ("proposal_commit_sha", "0" * 40),
    ("proposal_blob_sha", "0" * 40),
])
def test_routing_v2_pins_design_decision(field: str, value: object) -> None:
    manifest = load_manifest()
    record = next(p for p in manifest["packages"] if p["id"] == "FC20-12")["execution_slices"][0]
    record["design_decision"][field] = value
    with pytest.raises(AssertionError, match="design_decision_mismatch"):
        validate_routing_registration(manifest)


def test_routing_v2_requires_design_decision() -> None:
    manifest = load_manifest()
    record = next(p for p in manifest["packages"] if p["id"] == "FC20-12")["execution_slices"][0]
    record.pop("design_decision")
    with pytest.raises(AssertionError, match="unknown_or_missing_slice_field"):
        validate_routing_registration(manifest)

# Registration acceptance and mutations: no fixture authority is used by CI.
DEFENSIVE_MUTATIONS = json.loads(r'''[[["schema"],"unknown.v2"],[["id"],"routing_repair"],[["registry_effect"],"BUILD_AUTHORIZED"],[["state"],"IN_PROGRESS"],[["execution_authorized"],true],[["execution_authorized"],0],[["scope_document","blob_sha"],"0000000000000000000000000000000000000000"],[["scope_document","commit_sha"],"main"],[["scope_document","url"],"https://example.invalid/scope"],[["subject","baseline_commit_sha"],"0000000000000000000000000000000000000000"],[["registration_decision","effect"],"START"],[["registration_decision","record_url"],"https://example.invalid/approval"],[["registration_decision","proposal_blob_sha"],"0000000000000000000000000000000000000000"],[["owner_scope_decision","recorded_at"],"2026-01-01T00:00:00Z"],[["start_decision"],{"effect":"START"}],[["allowed_paths"],["backend/aas_kernel.py"]],[["allowed_paths"],["backend/*"]],[["environment"],"LIVE"],[["prerequisite_for","slice_id"],"another_slice"],[["entry_requirements"],[]],[["closure_effect"],"COMPLETE"],[["delivery_evidence"],{"status":"PASS"}],[["events"],[{"type":"START"}]],[["network_authorized"],true],[["network_authorized"],0],[["provider_activation_authorized"],true],[["deployment_authorized"],true],[["unknown_authority_override"],true]]''')


def defensive_record(manifest: dict) -> dict:
    return next(p for p in manifest["packages"] if p["id"] == "FC20-12")["execution_slices"][1]


def test_defensive_registration_is_blocked_and_retains_routing() -> None:
    manifest = load_manifest()
    validate_routing_registration(manifest)
    assert defensive_record(manifest) == DEFENSIVE_REGISTRATION
    assert manifest["execution_sequence"]["active_target"] is None
    assert manifest["execution_sequence"]["schema"] == "asie.foundation.execution-sequence.v2"
    assert manifest["execution_sequence"]["record_effect"] == "BOUNDED_DEFENSIVE_ENABLING_ONLY"


@pytest.mark.parametrize("path,value", DEFENSIVE_MUTATIONS)
def test_defensive_registration_rejects_forged_claims(path: list, value: object) -> None:
    manifest = load_manifest()
    target = defensive_record(manifest)
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(AssertionError):
        validate_routing_registration(manifest)


@pytest.mark.parametrize("field", list(DEFENSIVE_REGISTRATION))
def test_defensive_registration_requires_every_field(field: str) -> None:
    manifest = load_manifest()
    defensive_record(manifest).pop(field)
    # A missing identifier is rejected by dispatch before field validation.
    expected_error = "unknown_or_duplicate_slice" if field == "id" else "defensive_fields"
    with pytest.raises(AssertionError, match=expected_error):
        validate_routing_registration(manifest)


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "unknown", "wrong_order", "non_dict"])
def test_registration_rejects_missing_duplicate_and_unknown_slices(mutation: str) -> None:
    manifest = load_manifest()
    slices = next(p for p in manifest["packages"] if p["id"] == "FC20-12")["execution_slices"]
    if mutation == "missing":
        slices.pop()
    elif mutation == "duplicate":
        slices.append(deepcopy(slices[1]))
    elif mutation == "unknown":
        slices[1]["id"] = "parallel_runtime"
    elif mutation == "wrong_order":
        slices.reverse()
    else:
        slices[1] = "untrusted"
    with pytest.raises(AssertionError):
        validate_routing_registration(manifest)


def test_defensive_slot_cannot_be_opened_by_a_record_claim() -> None:
    manifest = load_manifest()
    manifest["execution_sequence"]["active_target"] = {
        "kind": "slice", "package_id": "FC20-12", "slice_id": "f01a_defensive_ingress",
    }
    with pytest.raises(AssertionError, match="execution_entry_not_authorized"):
        validate_execution_sequence(manifest)
    with pytest.raises(AssertionError):
        validate_routing_registration(manifest)


def test_defensive_activity_is_counted_even_under_a_held_parent() -> None:
    manifest = load_manifest()
    defensive_record(manifest)["state"] = "IN_PROGRESS"
    assert active_execution_targets(manifest["packages"], {"FC20-05", "FC20-12"}) == [
        "FC20-12/f01a_defensive_ingress",
    ]
    with pytest.raises(AssertionError, match="unrecorded_active_execution"):
        validate_execution_sequence(manifest)
    next(p for p in manifest["packages"] if p["id"] == "FC20-11")["state"] = "IN_PROGRESS"
    with pytest.raises(AssertionError, match="multiple_active_executions"):
        validate_execution_sequence(manifest)


def test_registration_preserves_all_package_states_and_parent_scope() -> None:
    manifest = load_manifest()
    assert {p["id"]: p["state"] for p in manifest["packages"]} == json.loads(r'''{"FC20-01":"COMPLETE","FC20-02":"COMPLETE","FC20-03":"COMPLETE","FC20-04":"COMPLETE","FC20-05":"IN_PROGRESS","FC20-06":"BLOCKED_BY_PREDECESSOR","FC20-07":"BLOCKED_BY_PREDECESSOR","FC20-08":"BLOCKED_BY_PREDECESSOR","FC20-09":"BLOCKED_BY_PREDECESSOR","FC20-10":"BLOCKED_BY_PREDECESSOR","FC20-11":"OPEN","FC20-12":"ACR_REQUIRED","FC20-13":"BLOCKED_BY_PREDECESSOR","FC20-14":"BLOCKED_BY_PREDECESSOR","FC20-15":"BLOCKED_BY_PREDECESSOR","FC20-16":"BLOCKED_BY_PREDECESSOR"}''')
    parent = next(p for p in manifest["packages"] if p["id"] == "FC20-12")
    assert parent["scope"] == [
        "Implement v2 contracts and one-version-per-run dispatch",
        "Admit approved synthesis pack and pre-decision envelope without changing Decision Council v1 semantics",
        "Update Snapshot input manifest under a separately approved frozen-boundary ACR",
        "Prove v1 parity, rollback, and no parallel runtime",
    ]
    assert parent["depends_on"] == ["FC20-08", "FC20-09", "FC20-11"]
    assert manifest["execution_sequence"]["held_packages"] == HELD_PACKAGES
    assert set(manifest["frozen_files"]) == EXPECTED_FROZEN_FILES
    assert manifest["current_release_verdict"] == "BLOCK"


def test_defensive_pinned_source_bytes_and_governing_links() -> None:
    package_root = Path(__file__).resolve().parents[1]
    scope = DEFENSIVE_REGISTRATION["scope_document"]
    scope_bytes = (package_root / DEFENSIVE_REGISTRATION["allowed_paths"][-1]).read_bytes().replace(b"\r\n", b"\n")
    assert hashlib.sha1(b"blob " + str(len(scope_bytes)).encode() + b"\0" + scope_bytes).hexdigest() == scope["blob_sha"]
    proposal_name = "FC20-12-F01A-DEFENSIVE-ENABLING-REGISTRATION-PROPOSAL-2026-10-01.md"
    proposal = (package_root / "docs" / proposal_name).read_bytes().replace(b"\r\n", b"\n")
    original_proposal = proposal.split(b"\n<!-- F01A-REGISTRATION-DELIVERY -->\n", 1)[0]
    assert hashlib.sha1(b"blob " + str(len(original_proposal)).encode() + b"\0" + original_proposal).hexdigest() == DEFENSIVE_REGISTRATION["registration_decision"]["proposal_blob_sha"]
    for name in (
        "docs/FOUNDATION-COMPLETE-20-CORE-INTELLIGENCE-COMPLETION-PROGRAM-2026-07-29.md",
        "docs/EKB/FOUNDATION-COMPLETE-20-PACKAGE-INDEX.md",
        "docs/ASIE-BETA-EXECUTION-MASTER-PLAN-2026-09-09.md",
    ):
        content = (package_root / name).read_text(encoding="utf-8")
        for required in (proposal_name, "f01a_defensive_ingress", "REGISTERED_BLOCKED",
                         "active_target = null", "5921569549", "BOUNDED_DEFENSIVE_ENABLING_ONLY"):
            assert required in content


def lifecycle_fixture() -> tuple[dict, dict, dict]:
    record = deepcopy(DEFENSIVE_REGISTRATION)
    decision = {
        "id": "ISOLATED_TEST_START_NOT_OWNER_APPROVAL",
        "effect": "F01A_DEFENSIVE_START_ONLY",
        "subject": deepcopy(record["subject"]),
    }
    record.update(state="IN_PROGRESS", execution_authorized=True,
                  start_decision=deepcopy(decision),
                  events=[{"type": "START", "decision_id": decision["id"]}])
    slot = {"kind": "slice", "package_id": "FC20-12", "slice_id": "f01a_defensive_ingress"}
    return record, slot, decision


def test_future_start_fixture_matches_one_slot_but_never_current_admission() -> None:
    record, slot, decision = lifecycle_fixture()
    validate_defensive_transition_fixture(record, slot, reviewed_decision=decision)
    with pytest.raises(AssertionError):
        validate_defensive_registration(record, slot)
    manifest = load_manifest()
    next(p for p in manifest["packages"] if p["id"] == "FC20-12")["execution_slices"][1] = record
    manifest["execution_sequence"]["active_target"] = slot
    with pytest.raises(AssertionError):
        validate_routing_registration(manifest)


@pytest.mark.parametrize("mutation", ["missing_decision", "forged_decision", "subject",
                                      "scope", "frozen_path", "slot", "flag", "history", "release"])
def test_future_lifecycle_model_rejects_mismatch(mutation: str) -> None:
    record, slot, decision = lifecycle_fixture()
    if mutation == "missing_decision":
        record["start_decision"] = None
    elif mutation == "forged_decision":
        record["start_decision"]["id"] = "forged"
    elif mutation == "subject":
        record["subject"]["baseline_commit_sha"] = "0" * 40
    elif mutation == "scope":
        record["network_authorized"] = True
    elif mutation == "frozen_path":
        record["allowed_paths"].append("backend/aas_kernel.py")
    elif mutation == "slot":
        slot = None
    elif mutation == "flag":
        record["execution_authorized"] = 1
    elif mutation == "history":
        record["events"] = []
    else:
        record["state"] = "DELIVERED"
        record["execution_authorized"] = False
        slot = None
    with pytest.raises(AssertionError):
        validate_defensive_transition_fixture(record, slot, reviewed_decision=decision)


def test_stop_checkpoint_keeps_counted_slot_until_reviewed_delivery() -> None:
    record, slot, decision = lifecycle_fixture()
    record["events"].append({"type": "STOP_CHECKPOINT", "reason": "scope_changed"})
    validate_defensive_transition_fixture(record, slot, reviewed_decision=decision)
    with pytest.raises(AssertionError, match="fixture_active_slot"):
        validate_defensive_transition_fixture(record, None, reviewed_decision=decision)
    delivery = {
        "commit_sha": "1" * 40, "test_ids": [f"T-{n:02d}" for n in range(1, 10)],
        "review_url": "https://example.invalid/isolated-test-review",
        "owner_decision_url": "https://example.invalid/isolated-test-delivery",
    }
    record.update(state="DELIVERED", execution_authorized=False, delivery_evidence=deepcopy(delivery))
    record["events"].append({"type": "DELIVERED", "commit_sha": delivery["commit_sha"]})
    validate_defensive_transition_fixture(record, None, reviewed_decision=decision,
                                         reviewed_delivery=delivery)
    for field in ("commit_sha", "test_ids", "review_url", "owner_decision_url"):
        invalid = deepcopy(record)
        invalid["delivery_evidence"].pop(field)
        with pytest.raises(AssertionError):
            validate_defensive_transition_fixture(invalid, None, reviewed_decision=decision,
                                                 reviewed_delivery=delivery)
    with pytest.raises(AssertionError):
        validate_defensive_registration(record, None)


def test_current_sequence_rejects_silent_v1_downgrade() -> None:
    manifest = load_manifest()
    manifest["execution_sequence"]["schema"] = "asie.foundation.execution-sequence.v1"
    manifest["execution_sequence"]["record_effect"] = "PRIORITY_AND_HOLD_ONLY"
    with pytest.raises(AssertionError, match="sequence_schema"):
        validate_execution_sequence(manifest)
