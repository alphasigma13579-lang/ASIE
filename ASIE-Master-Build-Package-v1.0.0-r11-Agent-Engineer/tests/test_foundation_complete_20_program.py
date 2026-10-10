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
    """CS-05: reject source-byte changes hidden by JSON parsing or text decoding."""
    source_bytes = MANIFEST_PATH.read_bytes()
    manifest = json.loads(source_bytes.decode("utf-8"))
    canonical_bytes = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    # .gitattributes requires LF on every supported platform; do not normalize here.
    assert source_bytes == canonical_bytes, "manifest_noncanonical_source"
    return manifest


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
# Current v2 admits the pinned stopped scope extension and retains its counted slot.
# The conditional START is historical; replay and all other starts remain blocked.
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


# Conditional owner instruction is pinned by reviewed code, never by the manifest.
# This candidate becomes operative only after a separately approved governance merge.
DEFENSIVE_START_DECISION = json.loads(r'''{
    "id": "DECISION-FC20-12-F01A-CONDITIONAL-START-2026-10-03",
    "record_url": "https://github.com/alphasigma13579-lang/ASIE/pull/181#issuecomment-5963212063",
    "recorded_at": "2026-10-02T23:43:38Z",
    "effect": "F01A_DEFENSIVE_START_ONLY",
    "subject": {
        "baseline_commit_sha": "de88be7710164c2fe9f176759745b986b0400112"
    },
    "condition": "REVIEWED_GOVERNANCE_TRANSITION_MERGED_AFTER_SEPARATE_OWNER_MERGE_APPROVAL"
}''')
DEFENSIVE_START_TARGET = {
    "kind": "slice", "package_id": "FC20-12", "slice_id": "f01a_defensive_ingress",
}
DEFENSIVE_START_RECORD = deepcopy(DEFENSIVE_REGISTRATION)
DEFENSIVE_START_RECORD.update(
    state="IN_PROGRESS", execution_authorized=True,
    subject=deepcopy(DEFENSIVE_START_DECISION["subject"]),
    start_decision=deepcopy(DEFENSIVE_START_DECISION),
    events=[{"type": "START", "decision_id": DEFENSIVE_START_DECISION["id"]}],
)


# Reviewed checkpoint oracle is independent of the manifest and isolated lifecycle fixture.
DEFENSIVE_STOP_EVENT = json.loads(r'''{
  "type": "STOP_CHECKPOINT",
  "recorded_at": "2026-10-05T10:21:21Z",
  "baseline_commit_sha": "23659956064e6750edbf7ef0ffb7f812ae05b985",
  "reason": "OUT_OF_SCOPE_TEST_FIXTURE",
  "requested_path": "tests/test_live_location_api.py",
  "evidence": {
    "url": "https://github.com/alphasigma13579-lang/ASIE/blob/23659956064e6750edbf7ef0ffb7f812ae05b985/ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/docs/FC20-12-F01A-TEST-FIXTURE-SCOPE-ADDENDUM-2026-10-04.md",
    "commit_sha": "23659956064e6750edbf7ef0ffb7f812ae05b985",
    "blob_sha": "0fe787204f5808b9aae843e0d5d4d94fd31b2609"
  },
  "resume_requirement": "NEW_OWNER_DECISION_AND_REVIEWED_EXACT_HEAD_GOVERNANCE_TRANSITION"
}''')
DEFENSIVE_STOP_RECORD = deepcopy(DEFENSIVE_START_RECORD)
DEFENSIVE_STOP_RECORD.update(execution_authorized=False)
DEFENSIVE_STOP_RECORD["events"].append(deepcopy(DEFENSIVE_STOP_EVENT))


# Reviewed scope delta is pinned separately from the input manifest.
# STOP, original scope/decisions, and the isolated lifecycle fixture stay unchanged.
DEFENSIVE_SCOPE_EXTENSION_EVENT = json.loads(r'''{
  "type": "SCOPE_EXTENSION",
  "recorded_at": "2026-10-06T19:41:02Z",
  "baseline_commit_sha": "5daa0b15b8b120575ea627429b754bd655ffd346",
  "added_paths": [
    "tests/test_live_location_api.py"
  ],
  "scope_addendum": {
    "url": "https://github.com/alphasigma13579-lang/ASIE/blob/23659956064e6750edbf7ef0ffb7f812ae05b985/ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/docs/FC20-12-F01A-TEST-FIXTURE-SCOPE-ADDENDUM-2026-10-04.md",
    "commit_sha": "23659956064e6750edbf7ef0ffb7f812ae05b985",
    "blob_sha": "0fe787204f5808b9aae843e0d5d4d94fd31b2609"
  },
  "owner_scope_decision": {
    "id": "DECISION-FC20-12-F01A-TEST-FIXTURE-SCOPE-DESIGN-2026-10-06",
    "record_url": "https://github.com/alphasigma13579-lang/ASIE/pull/185#issuecomment-6023988634",
    "recorded_at": "2026-10-06T19:34:56Z",
    "subject": {
      "baseline_commit_sha": "1213fe78da66072a246c8592e69b5f4ebb91b22a"
    },
    "effect": "SCOPE_DESIGN_APPROVED_NO_MERGE_NO_RESUME",
    "proposal_commit_sha": "1213fe78da66072a246c8592e69b5f4ebb91b22a",
    "proposal_blob_sha": "eeaf6354a9fc8b790812cb876cb95d4574bb562b"
  },
  "effect": "SCOPE_EXTENSION_ONLY_NO_RESUME"
}''')
DEFENSIVE_SCOPE_EXTENSION_RECORD = deepcopy(DEFENSIVE_STOP_RECORD)
DEFENSIVE_SCOPE_EXTENSION_RECORD["allowed_paths"].extend(
    DEFENSIVE_SCOPE_EXTENSION_EVENT["added_paths"],
)
DEFENSIVE_SCOPE_EXTENSION_RECORD["events"].append(
    deepcopy(DEFENSIVE_SCOPE_EXTENSION_EVENT),
)


# RG-01..RG-08: independent oracle from the reviewed receipt, not manifest input.
# Candidate authority becomes effective only after separately approved governance merge.
DEFENSIVE_RESUME_DECISION = json.loads(r'''{
  "id": "DECISION-FC20-12-F01A-CONDITIONAL-RESUME-2026-10-07",
  "recorded_at": "2026-10-06T21:53:52Z",
  "effect": "F01A_DEFENSIVE_RESUME_ONLY",
  "condition": "REVIEWED_GOVERNANCE_TRANSITION_MERGED_AFTER_SEPARATE_OWNER_MERGE_APPROVAL",
  "subject": {
    "baseline_commit_sha": "65efaba85e7a5ca2c944486f88c15ab95a7bd5e5",
    "baseline_manifest_blob_sha": "7b32044eabe0fe450bf2d5ba0d2aa4dee67ad545",
    "checkpoint": {
      "type": "STOP_CHECKPOINT",
      "recorded_at": "2026-10-05T10:21:21Z",
      "baseline_commit_sha": "23659956064e6750edbf7ef0ffb7f812ae05b985",
      "reason": "OUT_OF_SCOPE_TEST_FIXTURE",
      "requested_path": "tests/test_live_location_api.py",
      "evidence": {
        "url": "https://github.com/alphasigma13579-lang/ASIE/blob/23659956064e6750edbf7ef0ffb7f812ae05b985/ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/docs/FC20-12-F01A-TEST-FIXTURE-SCOPE-ADDENDUM-2026-10-04.md",
        "commit_sha": "23659956064e6750edbf7ef0ffb7f812ae05b985",
        "blob_sha": "0fe787204f5808b9aae843e0d5d4d94fd31b2609"
      },
      "resume_requirement": "NEW_OWNER_DECISION_AND_REVIEWED_EXACT_HEAD_GOVERNANCE_TRANSITION"
    },
    "allowed_paths": [
      "backend/asie_local_api.py",
      "backend/repository.py",
      "backend/intelligence_prerun_service.py",
      "tests/test_repository_intelligence.py",
      "tests/test_intelligence_prerun_service.py",
      "tests/test_intelligence_context_ingress_api.py",
      "docs/FC20-12-F01-TRUSTED-CONTEXT-INGRESS-REPAIR-PLAN-2026-10-01.md",
      "tests/test_live_location_api.py"
    ]
  },
  "proposal_commit_sha": "8398d9fa9f09bf04779420e50d40c1ed684051ec",
  "proposal_blob_sha": "bfa9d315ae66a804f9a12dcd532d05e61d841b8b",
  "record_url": "https://github.com/alphasigma13579-lang/ASIE/pull/187#issuecomment-6026149350"
}''')
DEFENSIVE_RESUME_EVENT = {
    "type": "RESUME",
    "recorded_at": "2026-10-06T22:03:09Z",
    "baseline_commit_sha": "65efaba85e7a5ca2c944486f88c15ab95a7bd5e5",
    "baseline_manifest_blob_sha": "7b32044eabe0fe450bf2d5ba0d2aa4dee67ad545",
    "checkpoint": deepcopy(DEFENSIVE_STOP_EVENT),
    "scope_extension": deepcopy(DEFENSIVE_SCOPE_EXTENSION_EVENT),
    "owner_resume_decision": deepcopy(DEFENSIVE_RESUME_DECISION),
    "effect": "F01A_DEFENSIVE_RESUME_ONLY",
}
DEFENSIVE_RESUME_RECORD = deepcopy(DEFENSIVE_SCOPE_EXTENSION_RECORD)
DEFENSIVE_RESUME_RECORD["execution_authorized"] = True
DEFENSIVE_RESUME_RECORD["events"].append(deepcopy(DEFENSIVE_RESUME_EVENT))


# CS: independent, receipt-pinned STOP/scope oracle. Preparation is not resume authority.
CONSUMPTION_STOP_EVENT = json.loads(r'''{"type":"STOP_CHECKPOINT","recorded_at":"2026-10-09T12:31:30Z","baseline_commit_sha":"23ea4b48e4c2f4c94e4f54c33bb0310bd6e0adc3","baseline_manifest_blob_sha":"ac40d84cb7bfca4ea025cf754483a0561037e994","application_head_sha":"6211418ca295e710be7f686bd1592bb30649f1d6","reason":"CONSUMPTION_REVIEW_AND_TEST_SCOPE_GAP","requested_path":"tests/test_intelligence_consumption.py","evidence":{"url":"https://github.com/alphasigma13579-lang/ASIE/blob/23ea4b48e4c2f4c94e4f54c33bb0310bd6e0adc3/ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/docs/FC20-12-F01A-APPROVAL-CONSUMPTION-SCOPE-ADDENDUM-2026-10-09.md","commit_sha":"23ea4b48e4c2f4c94e4f54c33bb0310bd6e0adc3","blob_sha":"042f89fce3adf1509ec0e6ee3e377c921820fde6"},"resume_requirement":"NEW_OWNER_DECISION_AND_REVIEWED_EXACT_HEAD_GOVERNANCE_TRANSITION"}''')
CONSUMPTION_SCOPE_EVENT = json.loads(r'''{"type":"SCOPE_EXTENSION","recorded_at":"2026-10-09T12:31:30Z","baseline_commit_sha":"23ea4b48e4c2f4c94e4f54c33bb0310bd6e0adc3","added_paths":["tests/test_intelligence_consumption.py"],"scope_addendum":{"url":"https://github.com/alphasigma13579-lang/ASIE/blob/23ea4b48e4c2f4c94e4f54c33bb0310bd6e0adc3/ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/docs/FC20-12-F01A-APPROVAL-CONSUMPTION-SCOPE-ADDENDUM-2026-10-09.md","commit_sha":"23ea4b48e4c2f4c94e4f54c33bb0310bd6e0adc3","blob_sha":"042f89fce3adf1509ec0e6ee3e377c921820fde6"},"owner_scope_decision":{"id":"DECISION-FC20-12-F01A-CONSUMPTION-REGISTRATION-PREPARATION-2026-10-09","record_url":"https://github.com/alphasigma13579-lang/ASIE/pull/193#issuecomment-6080941469","recorded_at":"2026-10-09T12:31:30Z","effect":"PREPARE_GOVERNANCE_PR_ONLY_NO_MERGE_NO_RESUME","subject":{"baseline_commit_sha":"23ea4b48e4c2f4c94e4f54c33bb0310bd6e0adc3","baseline_manifest_blob_sha":"ac40d84cb7bfca4ea025cf754483a0561037e994","application_head_sha":"6211418ca295e710be7f686bd1592bb30649f1d6"},"proposal_commit_sha":"fa806ce545a3432739167fbe042a731930b15f9e","proposal_blob_sha":"042f89fce3adf1509ec0e6ee3e377c921820fde6"},"effect":"SCOPE_EXTENSION_ONLY_NO_RESUME"}''')
CONSUMPTION_SCOPE_RECORD = deepcopy(DEFENSIVE_RESUME_RECORD)
CONSUMPTION_SCOPE_RECORD["execution_authorized"] = False
CONSUMPTION_SCOPE_RECORD["allowed_paths"].extend(CONSUMPTION_SCOPE_EVENT["added_paths"])
CONSUMPTION_SCOPE_RECORD["events"].extend([
    deepcopy(CONSUMPTION_STOP_EVENT), deepcopy(CONSUMPTION_SCOPE_EVENT),
])


def validate_consumption_scope(record: dict, active_target: object) -> None:
    """Admit only this stopped scope proposal; no historical state or resume fallback."""
    assert isinstance(record, dict), "invalid_defensive_record"
    assert set(record) == set(CONSUMPTION_SCOPE_RECORD), "defensive_fields"
    assert record == CONSUMPTION_SCOPE_RECORD, "defensive_record_mismatch"
    assert record["execution_authorized"] is False, "consumption_scope_stop_flag"
    assert all(record[key] is False for key in (
        "network_authorized", "provider_activation_authorized", "deployment_authorized",
    )), "defensive_external_effect"
    assert active_target == DEFENSIVE_START_TARGET, "consumption_scope_slot"


def validate_consumption_scope_baseline(manifest: dict) -> dict:
    """CS-05: inverse only two events/one path/flag; pin every byte of the old manifest."""
    restored = deepcopy(manifest)
    record = defensive_record(restored)
    validate_consumption_scope(record, restored["execution_sequence"]["active_target"])
    assert record["events"].pop() == CONSUMPTION_SCOPE_EVENT
    assert record["events"].pop() == CONSUMPTION_STOP_EVENT
    assert [record["allowed_paths"].pop()] == CONSUMPTION_SCOPE_EVENT["added_paths"]
    record["execution_authorized"] = True
    assert record == DEFENSIVE_RESUME_RECORD
    baseline_bytes = (json.dumps(restored, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    blob = hashlib.sha1(b"blob " + str(len(baseline_bytes)).encode() + b"\0" + baseline_bytes).hexdigest()
    assert blob == "ac40d84cb7bfca4ea025cf754483a0561037e994", "consumption_scope_baseline_mismatch"
    return restored


def historical_resume_manifest() -> dict:
    """Verified inverse projection for historical tests only, not current admission."""
    return validate_consumption_scope_baseline(load_manifest())


def validate_defensive_resume(record: dict, active_target: object) -> None:
    """Validate pinned historical resume in historical tests only; never current admission."""
    assert isinstance(record, dict), "invalid_defensive_record"
    assert set(record) == set(DEFENSIVE_RESUME_RECORD), "defensive_fields"
    assert record == DEFENSIVE_RESUME_RECORD, "defensive_record_mismatch"
    assert record["execution_authorized"] is True, "defensive_resume_flag"
    assert all(record[key] is False for key in (
        "network_authorized", "provider_activation_authorized", "deployment_authorized",
    )), "defensive_external_effect"
    assert active_target == DEFENSIVE_START_TARGET, "defensive_resume_slot"


def validate_resume_baseline(manifest: dict) -> dict:
    """RG-05: undo only RESUME/flag and restore the entire pinned #186 manifest."""
    restored = deepcopy(manifest)
    record = defensive_record(restored)
    validate_defensive_resume(record, restored["execution_sequence"]["active_target"])
    assert record["events"].pop() == DEFENSIVE_RESUME_EVENT
    record["execution_authorized"] = False
    assert record == DEFENSIVE_SCOPE_EXTENSION_RECORD
    baseline_bytes = (json.dumps(restored, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    blob = hashlib.sha1(b"blob " + str(len(baseline_bytes)).encode() + b"\0" + baseline_bytes).hexdigest()
    assert blob == "7b32044eabe0fe450bf2d5ba0d2aa4dee67ad545", "resume_baseline_mismatch"
    return restored


def historical_scope_extension_manifest() -> dict:
    """Verified historical projection only; never a current admission fallback."""
    return validate_resume_baseline(historical_resume_manifest())


def validate_defensive_checkpoint(record: dict, active_target: object) -> None:
    """Admit only the pinned stopped scope delta; never resume from metadata."""
    assert isinstance(record, dict), "invalid_defensive_record"
    assert set(record) == set(DEFENSIVE_SCOPE_EXTENSION_RECORD), "defensive_fields"
    assert record == DEFENSIVE_SCOPE_EXTENSION_RECORD, "defensive_record_mismatch"
    assert record["execution_authorized"] is False, "defensive_stop_flag"
    assert all(record[key] is False for key in (
        "network_authorized", "provider_activation_authorized", "deployment_authorized",
    )), "defensive_external_effect"
    assert active_target == DEFENSIVE_START_TARGET, "defensive_stop_slot"
    # IN_PROGRESS records outstanding work, not permission to continue. The slot
    # remains counted; scope expansion and resume need separate reviewed transitions.


def validate_defensive_start(record: dict, active_target: object) -> None:
    """Accept only this pinned conditional start; no fixture or metadata grants authority."""
    assert isinstance(record, dict), "invalid_defensive_record"
    assert set(record) == set(DEFENSIVE_START_RECORD), "defensive_fields"
    assert record == DEFENSIVE_START_RECORD, "defensive_record_mismatch"
    assert record["execution_authorized"] is True, "defensive_start_flag"
    assert all(record[key] is False for key in (
        "network_authorized", "provider_activation_authorized", "deployment_authorized",
    )), "defensive_external_effect"
    assert active_target == DEFENSIVE_START_TARGET, "defensive_start_slot"
    # Equality to the pinned record rejects missing/repeated start, delivery,
    # checkpoint deletion/replay, unreviewed resume, and forged terminal evidence.
    # A real checkpoint/delivery requires its own reviewed guard transition.


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
        assert all(
            isinstance(event, dict) and event.get("type") == "STOP_CHECKPOINT"
            for index, event in enumerate(record["events"]) if index > 0
        ), "fixture_active_history"
    else:
        assert record["state"] == "DELIVERED", "fixture_state"
        assert record["execution_authorized"] is False and slot is None, "fixture_release_slot"
        assert reviewed_delivery and record["delivery_evidence"] == reviewed_delivery, "fixture_delivery"
        assert re.fullmatch(r"[0-9a-f]{40}", reviewed_delivery["commit_sha"]), "fixture_delivery_sha"
        assert reviewed_delivery["test_ids"] == [f"T-{n:02d}" for n in range(1, 10)], "fixture_tests"
        assert reviewed_delivery["review_url"] and reviewed_delivery["owner_decision_url"], "fixture_review"
        assert all(
            isinstance(event, dict) and event.get("type") == "STOP_CHECKPOINT"
            for index, event in enumerate(record["events"])
            if 0 < index < len(record["events"]) - 1
        ), "fixture_delivery_history"
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


def execution_sequence_record(manifest: dict) -> dict:
    """Require complete sequence structure before inspecting any execution claim."""
    sequence = manifest.get("execution_sequence")
    assert isinstance(sequence, dict), "missing_execution_sequence"
    assert set(sequence) == {
        "schema", "record_effect", "ordering_decision", "priority_target",
        "max_active_executions", "active_target", "held_packages",
    }, "unknown_or_missing_sequence_field"
    return sequence


def validate_execution_sequence(manifest: dict) -> None:
    """Count the reserved stopped defensive slice while preserving the routing hold."""
    sequence = execution_sequence_record(manifest)
    assert sequence["schema"] == "asie.foundation.execution-sequence.v2", "sequence_schema"
    assert sequence["record_effect"] == "BOUNDED_DEFENSIVE_ENABLING_ONLY", "sequence_effect"
    assert sequence["ordering_decision"] == ORDERING_DECISION, "ordering_decision_mismatch"
    assert sequence["priority_target"] == {
        "kind": "slice", "package_id": "FC20-12", "slice_id": "routing_repair",
    }, "priority_target_mismatch"
    assert type(sequence["max_active_executions"]) is int
    assert sequence["max_active_executions"] == 1, "execution_limit"
    assert sequence["active_target"] == DEFENSIVE_START_TARGET, "execution_target_mismatch"
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
    assert active == ["FC20-12/f01a_defensive_ingress"], "unrecorded_active_execution"
    validate_consumption_scope(defensive_record(manifest), sequence["active_target"])


def validate_routing_registration(manifest: dict, *, allow_historical_v1: bool = False) -> None:
    """Keep routing blocked; current admission pins STOP/scope, never execution authority."""
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
    sequence = execution_sequence_record(manifest)
    validate_consumption_scope(slices[1], sequence["active_target"])
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
    if not allow_historical_v1:
        validate_consumption_scope_baseline(manifest)


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
    """Preserve held progress and count only the pinned F-01A defensive slice."""
    manifest = load_manifest()
    validate_execution_sequence(manifest)
    validate_routing_registration(manifest)
    assert active_execution_targets(manifest["packages"], {"FC20-05"}) == [
        "FC20-12/f01a_defensive_ingress",
    ]
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
        "FC20-11", "FC20-12/routing_repair", "FC20-12/f01a_defensive_ingress",
    ]
    with pytest.raises(AssertionError, match="multiple_active_executions"):
        validate_execution_sequence(manifest)


@pytest.mark.parametrize("claim", ["package", "routing_slice", "held_package_slice"])
def test_pinned_slot_denies_any_additional_execution(claim: str) -> None:
    """Reject additional execution, including slices inside a held package."""
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
    with pytest.raises(AssertionError, match="multiple_active_executions"):
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
    """Return the F-01A record from the canonical slice position for these tests."""
    return next(p for p in manifest["packages"] if p["id"] == "FC20-12")["execution_slices"][1]


def test_defensive_checkpoint_is_pinned_and_retains_blocked_routing() -> None:
    """Preserve historical stopped admission separately from the reviewed resume."""
    manifest = historical_scope_extension_manifest()
    validate_defensive_checkpoint(defensive_record(manifest), manifest["execution_sequence"]["active_target"])
    assert defensive_record(manifest) == DEFENSIVE_SCOPE_EXTENSION_RECORD
    assert manifest["execution_sequence"]["active_target"] == DEFENSIVE_START_TARGET
    assert manifest["execution_sequence"]["schema"] == "asie.foundation.execution-sequence.v2"
    assert manifest["execution_sequence"]["record_effect"] == "BOUNDED_DEFENSIVE_ENABLING_ONLY"


@pytest.mark.parametrize("path,value", DEFENSIVE_MUTATIONS)
def test_defensive_registration_rejects_forged_claims(path: list, value: object) -> None:
    """Reject each unauthorized mutation of the pinned defensive registration."""
    record = deepcopy(DEFENSIVE_REGISTRATION)
    target = record
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(AssertionError):
        validate_defensive_registration(record, None)


@pytest.mark.parametrize("field", list(DEFENSIVE_REGISTRATION))
def test_defensive_registration_requires_every_field(field: str) -> None:
    """Reject missing registration fields, including early identifier dispatch failures."""
    manifest = load_manifest()
    defensive_record(manifest).pop(field)
    # A missing identifier is rejected by dispatch before field validation.
    expected_error = "unknown_or_duplicate_slice" if field == "id" else "defensive_fields"
    with pytest.raises(AssertionError, match=expected_error):
        validate_routing_registration(manifest)


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "unknown", "wrong_order", "non_dict"])
def test_registration_rejects_missing_duplicate_and_unknown_slices(mutation: str) -> None:
    """Reject invalid slice membership, ordering, and non-dictionary records."""
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
    """Reject filling the slot while replaying the old blocked registration."""
    manifest = load_manifest()
    next(p for p in manifest["packages"] if p["id"] == "FC20-12")["execution_slices"][1] = deepcopy(DEFENSIVE_REGISTRATION)
    with pytest.raises(AssertionError, match="unrecorded_active_execution"):
        validate_execution_sequence(manifest)
    with pytest.raises(AssertionError):
        validate_routing_registration(manifest)


def test_defensive_activity_is_counted_even_under_a_held_parent() -> None:
    """Count held-parent slice activity and reject unrecorded or concurrent execution."""
    manifest = load_manifest()
    manifest["execution_sequence"]["active_target"] = None
    assert active_execution_targets(manifest["packages"], {"FC20-05", "FC20-12"}) == [
        "FC20-12/f01a_defensive_ingress",
    ]
    with pytest.raises(AssertionError, match="execution_target_mismatch"):
        validate_execution_sequence(manifest)
    manifest["execution_sequence"]["active_target"] = deepcopy(DEFENSIVE_START_TARGET)
    next(p for p in manifest["packages"] if p["id"] == "FC20-11")["state"] = "IN_PROGRESS"
    with pytest.raises(AssertionError, match="multiple_active_executions"):
        validate_execution_sequence(manifest)


def test_registration_preserves_all_package_states_and_parent_scope() -> None:
    """Preserve package progress, parent scope, dependencies, holds, and release block."""
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
    """Verify pinned source bytes and references without treating Git hashes as approval."""
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
    """Build isolated synthetic start data; it is not a real owner authorization."""
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
    """Accept the synthetic start model while proving current admission still rejects it."""
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
    """Reject synthetic lifecycle mutations that break decision, scope, or slot checks."""
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
    """Keep the synthetic slot counted at a checkpoint until validated fixture delivery."""
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



@pytest.mark.parametrize("state,event_types", [
    ("IN_PROGRESS", ["DELIVERED", "STOP_CHECKPOINT"]),
    ("IN_PROGRESS", ["START", "STOP_CHECKPOINT"]),
    ("DELIVERED", ["DELIVERED", "STOP_CHECKPOINT", "DELIVERED"]),
    ("DELIVERED", ["DELIVERED", "DELIVERED"]),
])
def test_lifecycle_history_rejects_activity_after_delivery_and_repeated_start(
    state: str, event_types: list[str],
) -> None:
    """Reject resumed activity or repeated terminal events under the original decision."""
    record, slot, decision = lifecycle_fixture()
    delivery = {
        "commit_sha": "1" * 40, "test_ids": [f"T-{n:02d}" for n in range(1, 10)],
        "review_url": "https://example.invalid/isolated-test-review",
        "owner_decision_url": "https://example.invalid/isolated-test-delivery",
    }
    for event_type in event_types:
        if event_type == "START":
            record["events"].append(deepcopy(record["events"][0]))
        elif event_type == "DELIVERED":
            record["events"].append({"type": event_type, "commit_sha": delivery["commit_sha"]})
        else:
            record["events"].append({"type": event_type, "reason": "isolated-test-checkpoint"})
    if state == "DELIVERED":
        record.update(state=state, execution_authorized=False, delivery_evidence=deepcopy(delivery))
        slot = None
    with pytest.raises(AssertionError, match="fixture_(active|delivery)_history"):
        validate_defensive_transition_fixture(
            record, slot, reviewed_decision=decision, reviewed_delivery=delivery,
        )


def test_current_sequence_rejects_silent_v1_downgrade() -> None:
    """Reject downgrading the current sequence to its historical v1 schema."""
    manifest = load_manifest()
    manifest["execution_sequence"]["schema"] = "asie.foundation.execution-sequence.v1"
    manifest["execution_sequence"]["record_effect"] = "PRIORITY_AND_HOLD_ONLY"
    with pytest.raises(AssertionError, match="sequence_schema"):
        validate_execution_sequence(manifest)


@pytest.mark.parametrize("path,value", [
    (("state",), "REGISTERED_BLOCKED"),
    (("state",), "DELIVERED"),
    (("execution_authorized",), False),
    (("execution_authorized",), 1),
    (("start_decision",), None),
    (("start_decision", "id"), "ISOLATED_TEST_START_NOT_OWNER_APPROVAL"),
    (("start_decision", "record_url"), "https://example.invalid/forged"),
    (("start_decision", "recorded_at"), "2026-01-01T00:00:00Z"),
    (("start_decision", "effect"), "ROUTING_START"),
    (("start_decision", "subject", "baseline_commit_sha"), "0" * 40),
    (("start_decision", "condition"), "AUTOMATIC_ON_PUSH"),
    (("subject", "baseline_commit_sha"), DEFENSIVE_REGISTRATION["subject"]["baseline_commit_sha"]),
    (("scope_document", "blob_sha"), "0" * 40),
    (("allowed_paths",), ["backend/*"]),
    (("allowed_paths",), ["backend/snapshot_assembly.py"]),
    (("entry_requirements",), []),
    (("environment",), "LIVE"),
    (("events",), []),
    (("events",), [{"type": "START", "decision_id": "forged"}]),
    (("delivery_evidence",), {"status": "PASS"}),
    (("closure_effect",), "COMPLETE"),
    (("network_authorized",), True),
    (("network_authorized",), 0),
    (("provider_activation_authorized",), True),
    (("deployment_authorized",), True),
    (("unknown_override",), True),
])
def test_pinned_start_rejects_unreviewed_authority(path: tuple, value: object) -> None:
    """Preserve the historical start oracle's negative coverage, not current admission."""
    record = deepcopy(DEFENSIVE_START_RECORD)
    target = record
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(AssertionError):
        validate_defensive_start(record, DEFENSIVE_START_TARGET)


@pytest.mark.parametrize("slot", [
    None, False, {},
    {"kind": "slice", "package_id": "FC20-12", "slice_id": "routing_repair"},
    {"kind": "package", "package_id": "FC20-05"},
])
def test_pinned_start_requires_its_exact_counted_slot(slot: object) -> None:
    """An active slice cannot hide or redirect its counted execution slot."""
    manifest = load_manifest()
    manifest["execution_sequence"]["active_target"] = slot
    with pytest.raises(AssertionError):
        validate_routing_registration(manifest)


@pytest.mark.parametrize("event", [
    {"type": "START", "decision_id": DEFENSIVE_START_DECISION["id"]},
    {"type": "DELIVERED", "commit_sha": "1" * 40},
    {"type": "STOP_CHECKPOINT", "reason": "unreviewed"},
])
def test_pinned_start_does_not_accept_unreviewed_lifecycle_events(event: dict) -> None:
    """A separate reviewed transition must preserve a real checkpoint or delivery."""
    manifest = load_manifest()
    defensive_record(manifest)["events"].append(event)
    with pytest.raises(AssertionError, match="defensive_record_mismatch"):
        validate_routing_registration(manifest)


def test_historical_blocked_registration_cannot_replace_current_start() -> None:
    """Keep the historical oracle testable but reject erasing the current start."""
    validate_defensive_registration(deepcopy(DEFENSIVE_REGISTRATION), None)
    manifest = load_manifest()
    next(p for p in manifest["packages"] if p["id"] == "FC20-12")["execution_slices"][1] = deepcopy(DEFENSIVE_REGISTRATION)
    manifest["execution_sequence"]["active_target"] = None
    with pytest.raises(AssertionError):
        validate_routing_registration(manifest)


CONDITIONAL_START_MARKER = "<!-- F01A-CONDITIONAL-START-2026-10-03 -->"
CONDITIONAL_START_HEADING = "### انتقال بدء F-01A الدفاعي المشروط — مرشح 2026-10-03"
CONDITIONAL_START_STATE = "f01a_defensive_ingress وحده IN_PROGRESS/true"
GOVERNING_VIEW_PATHS = (
    "docs/FOUNDATION-COMPLETE-20-CORE-INTELLIGENCE-COMPLETION-PROGRAM-2026-07-29.md",
    "docs/EKB/FOUNDATION-COMPLETE-20-PACKAGE-INDEX.md",
    "docs/ASIE-BETA-EXECUTION-MASTER-PLAN-2026-09-09.md",
    "docs/FC20-12-F01A-DEFENSIVE-ENABLING-REGISTRATION-PROPOSAL-2026-10-01.md",
)


def validate_conditional_start_governing_view(content: str) -> None:
    """Require the pinned state and decision inside the unique F-01A section."""
    assert content.count(CONDITIONAL_START_MARKER) == 1, "conditional_start_section_marker"
    section = content.split(CONDITIONAL_START_MARKER, 1)[1].lstrip("\n")
    heading, _, body = section.partition("\n")
    assert heading == CONDITIONAL_START_HEADING, "conditional_start_section_heading"
    section = re.split(r"(?m)^(?:#{1,3}\s|<!-- )", body, maxsplit=1)[0]
    for required in (
        DEFENSIVE_START_DECISION["record_url"],
        DEFENSIVE_START_DECISION["subject"]["baseline_commit_sha"],
        "F01A_DEFENSIVE_START_ONLY",
        CONDITIONAL_START_STATE,
        "REVIEWED_GOVERNANCE_TRANSITION_MERGED_AFTER_SEPARATE_OWNER_MERGE_APPROVAL",
    ):
        assert required in section, "conditional_start_section_missing:" + required


def test_conditional_start_is_visible_in_governing_views() -> None:
    """Bind human projections to the pinned decision, subject, and merge condition."""
    package_root = Path(__file__).resolve().parents[1]
    for relative_path in GOVERNING_VIEW_PATHS:
        content = (package_root / relative_path).read_text(encoding="utf-8")
        validate_conditional_start_governing_view(content)


@pytest.mark.parametrize("relative_path", GOVERNING_VIEW_PATHS)
@pytest.mark.parametrize("mutation", (
    "missing_marker", "duplicate_marker", "missing_f01a_state",
    "state_before_section", "state_in_next_section",
))
def test_conditional_start_view_rejects_unscoped_state(relative_path: str, mutation: str) -> None:
    """Reject missing or misplaced F-01A state despite unrelated IN_PROGRESS text."""
    package_root = Path(__file__).resolve().parents[1]
    content = (package_root / relative_path).read_text(encoding="utf-8")
    if mutation == "missing_marker":
        content = content.replace(CONDITIONAL_START_MARKER, "")
    elif mutation == "duplicate_marker":
        content += "\n" + CONDITIONAL_START_MARKER + "\n"
    else:
        content = content.replace(CONDITIONAL_START_STATE, "f01a_defensive_ingress وحده REGISTERED_BLOCKED/false")
        if mutation == "state_before_section":
            content = CONDITIONAL_START_STATE + "\n" + content
        elif mutation == "state_in_next_section":
            content += "\n### Unrelated section\n" + CONDITIONAL_START_STATE + "\n"
    assert "IN_PROGRESS" in content, "fixture_must_retain_unrelated_progress"
    with pytest.raises(AssertionError, match="conditional_start_section"):
        validate_conditional_start_governing_view(content)


def test_historical_start_cannot_replay_over_current_checkpoint() -> None:
    """Keep historical START testable, but never erase STOP from current admission."""
    validate_defensive_start(deepcopy(DEFENSIVE_START_RECORD), DEFENSIVE_START_TARGET)
    manifest = load_manifest()
    next(p for p in manifest["packages"] if p["id"] == "FC20-12")["execution_slices"][1] = deepcopy(DEFENSIVE_START_RECORD)
    with pytest.raises(AssertionError, match="defensive_record_mismatch"):
        validate_routing_registration(manifest)


@pytest.mark.parametrize("mutation", (
    "resume", "integer_flag", "erase_stop", "erase_start", "reverse_history",
    "duplicate_stop", "wrong_head", "wrong_evidence_blob", "wrong_path",
    "wrong_time", "missing_resume_requirement", "scope_expansion", "terminal",
))
def test_checkpoint_rejects_replay_resume_and_scope_expansion(mutation: str) -> None:
    """A stopped slot cannot acquire authority from history or scope metadata."""
    manifest = historical_scope_extension_manifest()
    record = defensive_record(manifest)
    if mutation == "resume":
        record["execution_authorized"] = True
    elif mutation == "integer_flag":
        record["execution_authorized"] = 0
    elif mutation == "erase_stop":
        record["events"].pop(1)
    elif mutation == "erase_start":
        record["events"].pop(0)
    elif mutation == "reverse_history":
        record["events"].reverse()
    elif mutation == "duplicate_stop":
        record["events"].append(deepcopy(record["events"][1]))
    elif mutation == "wrong_head":
        record["events"][1]["baseline_commit_sha"] = "0" * 40
    elif mutation == "wrong_evidence_blob":
        record["events"][1]["evidence"]["blob_sha"] = "0" * 40
    elif mutation == "wrong_path":
        record["events"][1]["requested_path"] = "backend/*"
    elif mutation == "wrong_time":
        record["events"][1]["recorded_at"] = "2026-01-01T00:00:00Z"
    elif mutation == "missing_resume_requirement":
        record["events"][1].pop("resume_requirement")
    elif mutation == "scope_expansion":
        record["allowed_paths"].append(DEFENSIVE_STOP_EVENT["requested_path"])
    elif mutation == "terminal":
        record["state"] = "DELIVERED"
        record["delivery_evidence"] = {"status": "PASS"}
    with pytest.raises(AssertionError):
        validate_defensive_checkpoint(defensive_record(manifest), manifest["execution_sequence"]["active_target"])


def test_checkpoint_keeps_single_slot_and_original_start_scope() -> None:
    """Prove STOP retains the sole slot, original scope, and complete START history."""
    manifest = historical_scope_extension_manifest()
    record = defensive_record(manifest)
    assert record["execution_authorized"] is False
    assert record["state"] == "IN_PROGRESS"
    assert record["events"][:2] == [*DEFENSIVE_START_RECORD["events"], DEFENSIVE_STOP_EVENT]
    assert record["events"][2:] == [DEFENSIVE_SCOPE_EXTENSION_EVENT]
    assert record["allowed_paths"][:-1] == DEFENSIVE_START_RECORD["allowed_paths"]
    assert record["allowed_paths"][-1:] == DEFENSIVE_SCOPE_EXTENSION_EVENT["added_paths"]
    restored = deepcopy(record)
    restored["events"].pop()
    restored["allowed_paths"].pop()
    assert restored == DEFENSIVE_STOP_RECORD
    restored["execution_authorized"] = True
    restored["events"].pop()
    assert restored == DEFENSIVE_START_RECORD
    sequence = manifest["execution_sequence"]
    assert active_execution_targets(manifest["packages"], {p["package_id"] for p in sequence["held_packages"]}) == ["FC20-12/f01a_defensive_ingress"]


STOP_CHECKPOINT_MARKER = "<!-- F01A-STOP-CHECKPOINT-2026-10-05 -->"
STOP_CHECKPOINT_HEADING = "### توقف F-01A الدفاعي — مرشح 2026-10-05"
STOP_CHECKPOINT_VIEW_TOKENS = (
    "IN_PROGRESS/false", "active_target محفوظ ومحسوب", "STOP_CHECKPOINT",
    DEFENSIVE_STOP_EVENT["baseline_commit_sha"],
    DEFENSIVE_STOP_EVENT["requested_path"],
    DEFENSIVE_STOP_EVENT["evidence"]["url"],
    DEFENSIVE_STOP_EVENT["resume_requirement"],
)


def validate_stop_checkpoint_governing_view(content: str) -> None:
    """Require checkpoint evidence inside one uniquely bounded projection section."""
    assert content.count(STOP_CHECKPOINT_MARKER) == 1, "stop_checkpoint_section_marker"
    section = content.split(STOP_CHECKPOINT_MARKER, 1)[1].lstrip("\n")
    heading, _, body = section.partition("\n")
    assert heading == STOP_CHECKPOINT_HEADING, "stop_checkpoint_section_heading"
    section = re.split(r"(?m)^(?:#{1,3}\s|<!-- )", body, maxsplit=1)[0]
    for required in STOP_CHECKPOINT_VIEW_TOKENS:
        assert required in section, "stop_checkpoint_section_missing:" + required


@pytest.mark.parametrize("relative_path", GOVERNING_VIEW_PATHS)
def test_stop_checkpoint_is_visible_in_governing_views(relative_path: str) -> None:
    """Bind each derived view to the pinned stopped state and resume restriction."""
    content = (Path(__file__).resolve().parents[1] / relative_path).read_text(encoding="utf-8")
    validate_stop_checkpoint_governing_view(content)


@pytest.mark.parametrize("relative_path", GOVERNING_VIEW_PATHS)
@pytest.mark.parametrize("token", STOP_CHECKPOINT_VIEW_TOKENS)
def test_stop_checkpoint_view_rejects_missing_or_unscoped_evidence(relative_path: str, token: str) -> None:
    """Reject moving required evidence outside the checkpoint's bounded section."""
    content = (Path(__file__).resolve().parents[1] / relative_path).read_text(encoding="utf-8")
    before, section = content.split(STOP_CHECKPOINT_MARKER, 1)
    # The removed evidence appears outside the bounded section and still cannot pass.
    tampered = before + token + "\n" + STOP_CHECKPOINT_MARKER + section.replace(token, "[removed]")
    with pytest.raises(AssertionError, match="stop_checkpoint_section_missing"):
        validate_stop_checkpoint_governing_view(tampered)


@pytest.mark.parametrize("mutation", ("missing_marker", "duplicate_marker", "wrong_heading"))
def test_stop_checkpoint_view_rejects_ambiguous_section(mutation: str) -> None:
    """Reject absent, duplicate, or incorrectly headed checkpoint sections."""
    content = (Path(__file__).resolve().parents[1] / GOVERNING_VIEW_PATHS[0]).read_text(encoding="utf-8")
    if mutation == "missing_marker":
        content = content.replace(STOP_CHECKPOINT_MARKER, "")
    elif mutation == "duplicate_marker":
        content += "\n" + STOP_CHECKPOINT_MARKER
    else:
        content = content.replace(STOP_CHECKPOINT_HEADING, "### توقف غير مثبت")
    with pytest.raises(AssertionError):
        validate_stop_checkpoint_governing_view(content)


@pytest.mark.parametrize("path,value", [
    (("state",), "REGISTERED_BLOCKED"),
    (("state",), "DELIVERED"),
    (("execution_authorized",), True),
    (("execution_authorized",), 0),
    (("start_decision",), None),
    (("start_decision", "id"), "ISOLATED_TEST_START_NOT_OWNER_APPROVAL"),
    (("start_decision", "record_url"), "https://example.invalid/forged"),
    (("start_decision", "recorded_at"), "2026-01-01T00:00:00Z"),
    (("start_decision", "effect"), "ROUTING_START"),
    (("start_decision", "subject", "baseline_commit_sha"), "0" * 40),
    (("start_decision", "condition"), "AUTOMATIC_ON_PUSH"),
    (("subject", "baseline_commit_sha"), DEFENSIVE_REGISTRATION["subject"]["baseline_commit_sha"]),
    (("scope_document", "blob_sha"), "0" * 40),
    (("allowed_paths",), ["backend/*"]),
    (("allowed_paths",), ["backend/snapshot_assembly.py"]),
    (("entry_requirements",), []),
    (("environment",), "LIVE"),
    (("events",), []),
    (("events",), [{"type": "START", "decision_id": "forged"}]),
    (("delivery_evidence",), {"status": "PASS"}),
    (("closure_effect",), "COMPLETE"),
    (("network_authorized",), True),
    (("network_authorized",), 0),
    (("provider_activation_authorized",), True),
    (("deployment_authorized",), True),
    (("unknown_override",), True),
])
def test_pinned_checkpoint_rejects_unreviewed_authority(path: tuple, value: object) -> None:
    """Preserve full authority/scope coverage on the historical stopped record too."""
    manifest = historical_scope_extension_manifest()
    target = defensive_record(manifest)
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(AssertionError):
        validate_defensive_checkpoint(defensive_record(manifest), manifest["execution_sequence"]["active_target"])


def test_checkpoint_evidence_bytes_match_pinned_git_blob() -> None:
    """Bind the checkpoint evidence file to its reviewed Git blob."""
    package_root = Path(__file__).resolve().parents[1]
    evidence_bytes = (package_root / "docs/FC20-12-F01A-TEST-FIXTURE-SCOPE-ADDENDUM-2026-10-04.md").read_bytes().replace(b"\r\n", b"\n")
    blob = hashlib.sha1(b"blob " + str(len(evidence_bytes)).encode() + b"\0" + evidence_bytes).hexdigest()
    assert blob == DEFENSIVE_STOP_EVENT["evidence"]["blob_sha"]


# SG-01..SG-07: reviewed registration only; these do not admit application execution.
SCOPE_EXTENSION_MARKER = "<!-- F01A-SCOPE-EXTENSION-2026-10-06 -->"
SCOPE_EXTENSION_HEADING = "### تسجيل توسعة F-01A دون استئناف — مرشح 2026-10-06"
SCOPE_EXTENSION_VIEW_PATHS = (
    *GOVERNING_VIEW_PATHS,
    "docs/FC20-12-F01A-TEST-FIXTURE-SCOPE-REGISTRATION-PROPOSAL-2026-10-06.md",
)
SCOPE_EXTENSION_VIEW_TOKENS = (
    "REGISTRATION_CANDIDATE / REVIEW_REQUIRED / NOT_EFFECTIVE_UNTIL_SEPARATE_OWNER_MERGE_APPROVAL",
    "IN_PROGRESS/false", "execution_authorized=false",
    "active_target محفوظ ومحسوب", "ثمانية مسارات",
    "SCOPE_EXTENSION", "SCOPE_EXTENSION_ONLY_NO_RESUME",
    DEFENSIVE_SCOPE_EXTENSION_EVENT["recorded_at"],
    DEFENSIVE_SCOPE_EXTENSION_EVENT["baseline_commit_sha"],
    DEFENSIVE_SCOPE_EXTENSION_EVENT["added_paths"][0],
    DEFENSIVE_SCOPE_EXTENSION_EVENT["scope_addendum"]["url"],
    DEFENSIVE_SCOPE_EXTENSION_EVENT["scope_addendum"]["blob_sha"],
    DEFENSIVE_SCOPE_EXTENSION_EVENT["owner_scope_decision"]["id"],
    DEFENSIVE_SCOPE_EXTENSION_EVENT["owner_scope_decision"]["record_url"],
    DEFENSIVE_SCOPE_EXTENSION_EVENT["owner_scope_decision"]["recorded_at"],
    DEFENSIVE_SCOPE_EXTENSION_EVENT["owner_scope_decision"]["subject"]["baseline_commit_sha"],
    DEFENSIVE_SCOPE_EXTENSION_EVENT["owner_scope_decision"]["effect"],
    DEFENSIVE_SCOPE_EXTENSION_EVENT["owner_scope_decision"]["proposal_blob_sha"],
    DEFENSIVE_STOP_EVENT["resume_requirement"],
    "delivery_evidence=null", "closure_effect=NONE", "DARK_OFFLINE",
    "network/provider/deployment=false", "REGISTERED_BLOCKED/false", "PENDING",
)


def validate_scope_extension_governing_view(content: str) -> None:
    """Require scope and non-resumption evidence inside the bounded historical section."""
    assert content.count(SCOPE_EXTENSION_MARKER) == 1, "scope_extension_section_marker"
    section = content.split(SCOPE_EXTENSION_MARKER, 1)[1].lstrip("\n")
    heading, _, body = section.partition("\n")
    assert heading == SCOPE_EXTENSION_HEADING, "scope_extension_section_heading"
    section = re.split(r"(?m)^(?:#{1,3}\s|<!-- )", body, maxsplit=1)[0]
    for token in SCOPE_EXTENSION_VIEW_TOKENS:
        assert token in section, "scope_extension_section_missing:" + token
    assert not re.search(
        r"execution_authorized\s*=\s*(?:true|1)\b|IN_PROGRESS/true",
        section, re.IGNORECASE,
    ), "scope_extension_view_resume_claim"


def validate_scope_extension_baseline(manifest: dict) -> None:
    """SG-05: reversing ONLY the two approved additions restores the entire baseline."""
    restored = deepcopy(manifest)
    record = defensive_record(restored)
    assert record["events"].pop() == DEFENSIVE_SCOPE_EXTENSION_EVENT
    assert record["allowed_paths"].pop() == "tests/test_live_location_api.py"
    assert record == DEFENSIVE_STOP_RECORD
    baseline_bytes = (json.dumps(restored, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    blob = hashlib.sha1(b"blob " + str(len(baseline_bytes)).encode() + b"\0" + baseline_bytes).hexdigest()
    assert blob == "12673dfcd4a3345f1d359b13c3fc3d210a5caca6", "scope_extension_baseline_mismatch"


def test_scope_extension_is_exact_and_does_not_resume() -> None:
    """SG-01/02/04: one appended path/event, preserved history, slot and false flags."""
    manifest = historical_scope_extension_manifest()
    validate_defensive_checkpoint(defensive_record(manifest), manifest["execution_sequence"]["active_target"])
    record = defensive_record(manifest)
    assert record == DEFENSIVE_SCOPE_EXTENSION_RECORD
    assert record["allowed_paths"] == [
        *DEFENSIVE_STOP_RECORD["allowed_paths"], "tests/test_live_location_api.py",
    ]
    assert len(record["allowed_paths"]) == len(set(record["allowed_paths"])) == 8
    assert record["events"] == [*DEFENSIVE_STOP_RECORD["events"], DEFENSIVE_SCOPE_EXTENSION_EVENT]
    assert set(record["events"][-1]) == {
        "type", "recorded_at", "baseline_commit_sha", "added_paths",
        "scope_addendum", "owner_scope_decision", "effect",
    }
    for key in ("execution_authorized", "network_authorized",
                "provider_activation_authorized", "deployment_authorized"):
        assert record[key] is False


@pytest.mark.parametrize("mutation", (
    "extra", "delete", "duplicate", "reorder", "wildcard", "frozen",
))
def test_scope_extension_rejects_other_paths(mutation: str) -> None:
    """SG-01: neither the new decision nor the existing START widens other paths."""
    manifest = historical_scope_extension_manifest()
    paths = defensive_record(manifest)["allowed_paths"]
    if mutation == "extra":
        paths.append("src/App.tsx")
    elif mutation == "delete":
        paths.pop()
    elif mutation == "duplicate":
        paths.append(paths[-1])
    elif mutation == "reorder":
        paths.reverse()
    elif mutation == "wildcard":
        paths[-1] = "tests/*"
    else:
        paths[-1] = "backend/aas_kernel.py"
    with pytest.raises(AssertionError, match="defensive_record_mismatch"):
        validate_defensive_checkpoint(defensive_record(manifest), manifest["execution_sequence"]["active_target"])


@pytest.mark.parametrize("mutation", (
    "missing_extension", "duplicate_extension", "extension_before_stop",
    "remove_start", "remove_stop", "alter_start", "alter_stop", "old_start_replay",
))
def test_scope_extension_rejects_history_changes(mutation: str) -> None:
    """SG-02: scope extension does not erase or re-authorize the historical START/STOP."""
    manifest = historical_scope_extension_manifest()
    record = defensive_record(manifest)
    history = record["events"]
    if mutation == "missing_extension":
        history.pop()
    elif mutation == "duplicate_extension":
        history.append(deepcopy(history[-1]))
    elif mutation == "extension_before_stop":
        history[1], history[2] = history[2], history[1]
    elif mutation == "remove_start":
        history.pop(0)
    elif mutation == "remove_stop":
        history.pop(1)
    elif mutation == "alter_start":
        history[0]["decision_id"] = "forged"
    elif mutation == "alter_stop":
        history[1]["resume_requirement"] = "AUTOMATIC"
    else:
        record["execution_authorized"] = True
        history.append(deepcopy(history[0]))
    with pytest.raises(AssertionError):
        validate_defensive_checkpoint(defensive_record(manifest), manifest["execution_sequence"]["active_target"])


@pytest.mark.parametrize("path,value", [
    (("type",), "START"),
    (("recorded_at",), "2026-01-01T00:00:00Z"),
    (("baseline_commit_sha",), "main"),
    (("baseline_commit_sha",), "0" * 40),
    (("added_paths",), []),
    (("added_paths",), ["src/App.tsx"]),
    (("added_paths",), ["tests/test_live_location_api.py", "src/App.tsx"]),
    (("effect",), "RESUME"),
    (("scope_addendum", "url"), "https://example.invalid/addendum"),
    (("scope_addendum", "commit_sha"), "main"),
    (("scope_addendum", "blob_sha"), "0" * 40),
    (("owner_scope_decision",), None),
    (("owner_scope_decision",), {}),
    (("owner_scope_decision", "id"), "ISOLATED_TEST_START_NOT_OWNER_APPROVAL"),
    (("owner_scope_decision", "record_url"), "https://example.invalid/decision"),
    (("owner_scope_decision", "recorded_at"), "2026-01-01T00:00:00Z"),
    (("owner_scope_decision", "effect"), "F01A_DEFENSIVE_START_ONLY"),
    (("owner_scope_decision", "subject", "baseline_commit_sha"), "0" * 40),
    (("owner_scope_decision", "proposal_commit_sha"), "main"),
    (("owner_scope_decision", "proposal_blob_sha"), "0" * 40),
    (("unknown_authority_override",), True),
])
def test_scope_extension_rejects_unpinned_authority(path: tuple, value: object) -> None:
    """SG-03: reviewed code, not the supplied event, pins the real decision and evidence."""
    manifest = historical_scope_extension_manifest()
    target = defensive_record(manifest)["events"][2]
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(AssertionError, match="defensive_record_mismatch"):
        validate_defensive_checkpoint(defensive_record(manifest), manifest["execution_sequence"]["active_target"])


@pytest.mark.parametrize("field", list(DEFENSIVE_SCOPE_EXTENSION_EVENT))
def test_scope_extension_requires_all_event_fields(field: str) -> None:
    """SG-03: no missing field can downgrade the closed event to a broad permission."""
    manifest = historical_scope_extension_manifest()
    defensive_record(manifest)["events"][2].pop(field)
    with pytest.raises(AssertionError, match="defensive_record_mismatch"):
        validate_defensive_checkpoint(defensive_record(manifest), manifest["execution_sequence"]["active_target"])


def test_scope_extension_proposal_bytes_match_reviewed_git_blob() -> None:
    """SG-03: hash the reviewed original, not a modified historical approval."""
    package_root = Path(__file__).resolve().parents[1]
    content = (package_root / "docs/FC20-12-F01A-TEST-FIXTURE-SCOPE-REGISTRATION-PROPOSAL-2026-10-06.md").read_bytes().replace(b"\r\n", b"\n")
    original = content.split(("\n" + SCOPE_EXTENSION_MARKER + "\n").encode(), 1)[0]
    blob = hashlib.sha1(b"blob " + str(len(original)).encode() + b"\0" + original).hexdigest()
    assert blob == DEFENSIVE_SCOPE_EXTENSION_EVENT["owner_scope_decision"]["proposal_blob_sha"]


def test_scope_extension_reverses_only_approved_manifest_delta() -> None:
    """SG-05: pin all program rules, states, controls, evidence and frozen surfaces too."""
    validate_scope_extension_baseline(historical_scope_extension_manifest())


@pytest.mark.parametrize("mutation", (
    "package_title", "package_state", "dependency", "control", "release", "rule", "hold",
))
def test_scope_extension_baseline_rejects_unrelated_changes(mutation: str) -> None:
    """SG-05: even a non-permission edit outside the two deltas is not silently accepted."""
    manifest = historical_scope_extension_manifest()
    by_id = {package["id"]: package for package in manifest["packages"]}
    if mutation == "package_title":
        by_id["FC20-05"]["title"] = "changed"
    elif mutation == "package_state":
        by_id["FC20-11"]["state"] = "COMPLETE"
    elif mutation == "dependency":
        by_id["FC20-12"]["depends_on"].pop()
    elif mutation == "control":
        by_id["FC20-12"]["execution_slices"][0]["required_entry_controls"]["single_active_execution"]["status"] = "PASS"
    elif mutation == "release":
        manifest["public_release_authorized"] = True
    elif mutation == "rule":
        manifest["rules"]["single_source_of_truth"] = False
    else:
        manifest["execution_sequence"]["held_packages"] = []
    with pytest.raises(AssertionError, match="scope_extension_baseline_mismatch"):
        validate_scope_extension_baseline(manifest)


def test_scope_extension_cannot_admit_fixture_or_previous_checkpoint() -> None:
    """SG-06: synthetic lifecycle, bare old STOP and old START are not current admission."""
    fixture, slot, decision = lifecycle_fixture()
    validate_defensive_transition_fixture(fixture, slot, reviewed_decision=decision)
    for record in (fixture, DEFENSIVE_STOP_RECORD, DEFENSIVE_START_RECORD):
        manifest = load_manifest()
        next(p for p in manifest["packages"] if p["id"] == "FC20-12")["execution_slices"][1] = deepcopy(record)
        with pytest.raises(AssertionError, match="defensive_record_mismatch"):
            validate_routing_registration(manifest)


@pytest.mark.parametrize("relative_path", SCOPE_EXTENSION_VIEW_PATHS)
def test_scope_extension_is_visible_without_resume_in_governing_views(relative_path: str) -> None:
    """SG-07: preserve the historical scope-only projection and its non-resumption."""
    content = (Path(__file__).resolve().parents[1] / relative_path).read_text(encoding="utf-8")
    validate_scope_extension_governing_view(content)


@pytest.mark.parametrize("relative_path", SCOPE_EXTENSION_VIEW_PATHS)
@pytest.mark.parametrize("token", SCOPE_EXTENSION_VIEW_TOKENS)
def test_scope_extension_view_rejects_unscoped_evidence(relative_path: str, token: str) -> None:
    """SG-07: a token elsewhere, including historical text, cannot complete the current view."""
    content = (Path(__file__).resolve().parents[1] / relative_path).read_text(encoding="utf-8")
    before, section = content.split(SCOPE_EXTENSION_MARKER, 1)
    tampered = before + token + "\n" + SCOPE_EXTENSION_MARKER + section.replace(token, "[removed]")
    with pytest.raises(AssertionError, match="scope_extension_section_missing"):
        validate_scope_extension_governing_view(tampered)


@pytest.mark.parametrize("mutation", (
    "missing_marker", "duplicate_marker", "wrong_heading", "resume_flag", "resume_state",
))
def test_scope_extension_view_rejects_ambiguity_and_resume_claim(mutation: str) -> None:
    """SG-07: do not accept a misleading active claim merely because false appears too."""
    content = (Path(__file__).resolve().parents[1] / SCOPE_EXTENSION_VIEW_PATHS[0]).read_text(encoding="utf-8")
    if mutation == "missing_marker":
        content = content.replace(SCOPE_EXTENSION_MARKER, "")
    elif mutation == "duplicate_marker":
        content += "\n" + SCOPE_EXTENSION_MARKER
    elif mutation == "wrong_heading":
        content = content.replace(SCOPE_EXTENSION_HEADING, "### غير معتمد")
    elif mutation == "resume_flag":
        content = content.replace(SCOPE_EXTENSION_HEADING + "\n", SCOPE_EXTENSION_HEADING + "\nexecution_authorized=true\n", 1)
    else:
        content = content.replace(SCOPE_EXTENSION_HEADING + "\n", SCOPE_EXTENSION_HEADING + "\nIN_PROGRESS/true\n", 1)
    with pytest.raises(AssertionError, match="scope_extension_"):
        validate_scope_extension_governing_view(content)

# RG acceptance for the conditional-resume transition; no application/runtime proof.
RESUME_TRANSITION_MARKER = "<!-- F01A-CONDITIONAL-RESUME-TRANSITION-2026-10-07 -->"
RESUME_TRANSITION_HEADING = "### انتقال استئناف F-01A الدفاعي المشروط — مرشح 2026-10-07"
RESUME_VIEW_PATHS = (
    *SCOPE_EXTENSION_VIEW_PATHS,
    "docs/FC20-12-F01A-CONDITIONAL-RESUME-PROPOSAL-2026-10-06.md",
)
RESUME_VIEW_TOKENS = (
    "GOVERNANCE_TRANSITION_CANDIDATE / REVIEW_REQUIRED / NOT_EFFECTIVE_UNTIL_SEPARATE_OWNER_MERGE_APPROVAL",
    "f01a_defensive_ingress IN_PROGRESS/true", "execution_authorized=true",
    "active_target محفوظ ومحسوب", "ثمانية مسارات",
    "START → STOP_CHECKPOINT → SCOPE_EXTENSION → RESUME",
    DEFENSIVE_RESUME_EVENT["recorded_at"],
    DEFENSIVE_RESUME_EVENT["baseline_commit_sha"],
    DEFENSIVE_RESUME_EVENT["baseline_manifest_blob_sha"],
    DEFENSIVE_RESUME_DECISION["id"],
    DEFENSIVE_RESUME_DECISION["record_url"],
    DEFENSIVE_RESUME_DECISION["recorded_at"],
    DEFENSIVE_RESUME_DECISION["effect"],
    DEFENSIVE_RESUME_DECISION["condition"],
    DEFENSIVE_RESUME_DECISION["proposal_commit_sha"],
    DEFENSIVE_RESUME_DECISION["proposal_blob_sha"],
    DEFENSIVE_STOP_EVENT["resume_requirement"],
    "delivery_evidence=null", "closure_effect=NONE", "DARK_OFFLINE",
    "network/provider/deployment=false", "REGISTERED_BLOCKED/false", "PENDING",
    "RG-01–RG-08", "SG-05", "FC20-05 held",
)


def validate_resume_governing_view(content: str) -> None:
    """RG-07: only one bounded, candidate projection can describe this transition."""
    assert content.count(RESUME_TRANSITION_MARKER) == 1, "resume_section_marker"
    section = content.split(RESUME_TRANSITION_MARKER, 1)[1].lstrip("\n")
    heading, _, body = section.partition("\n")
    assert heading == RESUME_TRANSITION_HEADING, "resume_section_heading"
    section = re.split(r"(?m)^(?:#{1,3}\s|<!-- )", body, maxsplit=1)[0]
    for token in RESUME_VIEW_TOKENS:
        assert token in section, "resume_section_missing:" + token
    for path in DEFENSIVE_SCOPE_EXTENSION_RECORD["allowed_paths"]:
        assert path in section, "resume_section_scope:" + path
    assert not re.search(
        r"(?:network_authorized|provider_activation_authorized|deployment_authorized"
        r"|external_network_authorized|public_release_authorized)\s*=\s*(?:true|1)\b"
        r"|routing_repair\s+(?:IN_PROGRESS|DELIVERED)/true",
        section, re.IGNORECASE,
    ), "resume_view_external_claim"


def test_conditional_resume_preserves_exact_history_scope_and_slot() -> None:
    """RG-01/02/04/08: one flag/event, no routing, release, closure or second execution."""
    manifest = historical_resume_manifest()
    validate_defensive_resume(defensive_record(manifest), manifest["execution_sequence"]["active_target"])
    record = defensive_record(manifest)
    assert record == DEFENSIVE_RESUME_RECORD
    assert record["execution_authorized"] is True
    assert record["events"][:-1] == DEFENSIVE_SCOPE_EXTENSION_RECORD["events"]
    assert record["events"][-1] == DEFENSIVE_RESUME_EVENT
    assert record["allowed_paths"] == DEFENSIVE_SCOPE_EXTENSION_RECORD["allowed_paths"]
    assert len(record["allowed_paths"]) == len(set(record["allowed_paths"])) == 8
    assert record["subject"] == DEFENSIVE_START_RECORD["subject"]
    assert record["start_decision"] == DEFENSIVE_START_DECISION
    assert record["state"] == "IN_PROGRESS"
    assert record["environment"] == "DARK_OFFLINE"
    assert record["delivery_evidence"] is None and record["closure_effect"] == "NONE"
    assert active_execution_targets(
        manifest["packages"],
        {p["package_id"] for p in manifest["execution_sequence"]["held_packages"]},
    ) == ["FC20-12/f01a_defensive_ingress"]
    historical = validate_resume_baseline(manifest)
    validate_defensive_checkpoint(
        defensive_record(historical), historical["execution_sequence"]["active_target"],
    )
    validate_scope_extension_baseline(historical)


@pytest.mark.parametrize("field", list(DEFENSIVE_RESUME_EVENT))
def test_resume_requires_every_event_field(field: str) -> None:
    """RG-03: missing evidence cannot reduce the closed event to a broad flag."""
    manifest = historical_resume_manifest()
    defensive_record(manifest)["events"][-1].pop(field)
    with pytest.raises(AssertionError, match="defensive_record_mismatch"):
        validate_defensive_resume(defensive_record(manifest), manifest["execution_sequence"]["active_target"])


def resume_leaf_paths(value: dict, prefix: tuple = ()) -> list[tuple]:
    """Enumerate independent oracle leaves; never derive expected evidence from input."""
    paths = []
    for key, child in value.items():
        path = (*prefix, key)
        if isinstance(child, dict):
            paths.extend(resume_leaf_paths(child, path))
        else:
            paths.append(path)
    return paths


@pytest.mark.parametrize("path", resume_leaf_paths(DEFENSIVE_RESUME_EVENT))
def test_resume_rejects_each_changed_evidence_leaf(path: tuple) -> None:
    """RG-02/03: pin times, subjects, checkpoint, scope, proposal and actual receipt."""
    manifest = historical_resume_manifest()
    target = defensive_record(manifest)["events"][-1]
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = "[unreviewed]"
    with pytest.raises(AssertionError, match="defensive_record_mismatch"):
        validate_defensive_resume(defensive_record(manifest), manifest["execution_sequence"]["active_target"])


@pytest.mark.parametrize("decision", (
    None, {}, DEFENSIVE_START_DECISION,
    DEFENSIVE_SCOPE_EXTENSION_EVENT["owner_scope_decision"],
    {"record_url": "https://github.com/alphasigma13579-lang/ASIE/pull/186"},
))
def test_resume_rejects_old_or_supplied_decision(decision: object) -> None:
    """RG-03/06: START, scope design, merge or supplied metadata are not new approval."""
    manifest = historical_resume_manifest()
    defensive_record(manifest)["events"][-1]["owner_resume_decision"] = deepcopy(decision)
    with pytest.raises(AssertionError, match="defensive_record_mismatch"):
        validate_defensive_resume(defensive_record(manifest), manifest["execution_sequence"]["active_target"])


@pytest.mark.parametrize("mutation", (
    "erase_start", "erase_stop", "erase_extension", "erase_resume", "duplicate_resume",
    "reverse", "resume_before_stop", "alter_stop", "old_start_replay",
))
def test_resume_rejects_history_replay_and_erasure(mutation: str) -> None:
    """RG-02: original history is immutable; no repeated/reordered transition."""
    manifest = historical_resume_manifest()
    record = defensive_record(manifest)
    history = record["events"]
    if mutation.startswith("erase_"):
        history.pop({"erase_start": 0, "erase_stop": 1, "erase_extension": 2, "erase_resume": 3}[mutation])
    elif mutation == "duplicate_resume":
        history.append(deepcopy(history[-1]))
    elif mutation == "reverse":
        history.reverse()
    elif mutation == "resume_before_stop":
        history[1], history[3] = history[3], history[1]
    elif mutation == "alter_stop":
        history[1]["reason"] = "AUTO_RESUME"
    else:
        history.append(deepcopy(history[0]))
    with pytest.raises(AssertionError, match="defensive_record_mismatch"):
        validate_defensive_resume(defensive_record(manifest), manifest["execution_sequence"]["active_target"])


@pytest.mark.parametrize("path,value", [
    (("execution_authorized",), False),
    (("execution_authorized",), 1),
    (("execution_authorized",), "true"),
    (("allowed_paths",), ["backend/*"]),
    (("allowed_paths",), ["backend/snapshot_assembly.py"]),
    (("state",), "DELIVERED"),
    (("environment",), "LIVE"),
    (("delivery_evidence",), {"status": "PASS"}),
    (("closure_effect",), "COMPLETE"),
    (("network_authorized",), True),
    (("network_authorized",), 0),
    (("provider_activation_authorized",), True),
    (("deployment_authorized",), True),
    (("f01b_authorized",), True),
    (("supplied_authority",), {"reviewed": True}),
])
def test_resume_rejects_execution_and_scope_overrides(path: tuple, value: object) -> None:
    """RG-01/04/06/08: exact boolean and no external, frozen, F01B or delivery effect."""
    manifest = historical_resume_manifest()
    target = defensive_record(manifest)
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(AssertionError):
        validate_defensive_resume(defensive_record(manifest), manifest["execution_sequence"]["active_target"])


@pytest.mark.parametrize("level", ("event", "decision", "subject", "checkpoint", "extension"))
def test_resume_rejects_unknown_authority_fields(level: str) -> None:
    """RG-03/06: no permissive extensibility or trusted flag in nested authority."""
    manifest = historical_resume_manifest()
    event = defensive_record(manifest)["events"][-1]
    target = {
        "event": event, "decision": event["owner_resume_decision"],
        "subject": event["owner_resume_decision"]["subject"],
        "checkpoint": event["checkpoint"], "extension": event["scope_extension"],
    }[level]
    target["trusted_override"] = True
    with pytest.raises(AssertionError, match="defensive_record_mismatch"):
        validate_defensive_resume(defensive_record(manifest), manifest["execution_sequence"]["active_target"])


@pytest.mark.parametrize("historical_record", (
    DEFENSIVE_REGISTRATION, DEFENSIVE_START_RECORD,
    DEFENSIVE_STOP_RECORD, DEFENSIVE_SCOPE_EXTENSION_RECORD,
))
def test_resume_rejects_historical_record_as_current(historical_record: dict) -> None:
    """RG-06: historical positives remain tested separately, not admitted as downgrades."""
    manifest = historical_resume_manifest()
    next(p for p in manifest["packages"] if p["id"] == "FC20-12")["execution_slices"][1] = deepcopy(historical_record)
    with pytest.raises(AssertionError, match="defensive_record_mismatch"):
        validate_defensive_resume(defensive_record(manifest), manifest["execution_sequence"]["active_target"])


@pytest.mark.parametrize("mutation", (
    "package_title", "package_state", "dependency", "control", "release", "rule",
    "hold", "frozen", "unknown_root", "unknown_package", "slice",
))
def test_resume_baseline_rejects_all_unrelated_manifest_changes(mutation: str) -> None:
    """RG-05: a complete inverse hash, not selected-field equality, preserves all data."""
    manifest = historical_resume_manifest()
    by_id = {p["id"]: p for p in manifest["packages"]}
    if mutation == "package_title":
        by_id["FC20-05"]["title"] = "changed"
    elif mutation == "package_state":
        by_id["FC20-11"]["state"] = "COMPLETE"
    elif mutation == "dependency":
        by_id["FC20-12"]["depends_on"].pop()
    elif mutation == "control":
        by_id["FC20-12"]["execution_slices"][0]["required_entry_controls"]["single_active_execution"]["status"] = "PASS"
    elif mutation == "release":
        manifest["public_release_authorized"] = True
    elif mutation == "rule":
        manifest["rules"]["single_source_of_truth"] = False
    elif mutation == "hold":
        manifest["execution_sequence"]["held_packages"] = []
    elif mutation == "frozen":
        manifest["frozen_files"].append("backend/unknown.py")
    elif mutation == "unknown_root":
        manifest["override"] = True
    elif mutation == "unknown_package":
        by_id["FC20-05"]["override"] = True
    else:
        by_id["FC20-12"]["execution_slices"][0]["eligibility_record"]["paths"].append("backend/aas_kernel.py")
    with pytest.raises(AssertionError, match="resume_baseline_mismatch"):
        validate_resume_baseline(manifest)


@pytest.mark.parametrize("relative_path", RESUME_VIEW_PATHS)
def test_resume_is_visible_only_as_candidate_in_governing_views(relative_path: str) -> None:
    """RG-07: all six derived views match the pinned decision and its effective condition."""
    content = (Path(__file__).resolve().parents[1] / relative_path).read_text(encoding="utf-8")
    validate_resume_governing_view(content)


@pytest.mark.parametrize("token", RESUME_VIEW_TOKENS)
def test_resume_view_rejects_unscoped_evidence(token: str) -> None:
    """RG-07: the same bounded parser must reject evidence moved outside its section."""
    content = (Path(__file__).resolve().parents[1] / RESUME_VIEW_PATHS[0]).read_text(encoding="utf-8")
    before, section = content.split(RESUME_TRANSITION_MARKER, 1)
    tampered = before + token + "\n" + RESUME_TRANSITION_MARKER + section.replace(token, "[removed]")
    with pytest.raises(AssertionError, match="resume_section_missing"):
        validate_resume_governing_view(tampered)


@pytest.mark.parametrize("mutation", ("missing_marker", "duplicate_marker", "wrong_heading", "network", "routing"))
def test_resume_view_rejects_ambiguous_or_external_claim(mutation: str) -> None:
    """RG-07/08: candidate text must not grant external or routing authority."""
    content = (Path(__file__).resolve().parents[1] / RESUME_VIEW_PATHS[0]).read_text(encoding="utf-8")
    if mutation == "missing_marker":
        content = content.replace(RESUME_TRANSITION_MARKER, "")
    elif mutation == "duplicate_marker":
        content += "\n" + RESUME_TRANSITION_MARKER
    elif mutation == "wrong_heading":
        content = content.replace(RESUME_TRANSITION_HEADING, "### غير معتمد")
    else:
        claim = "network_authorized=true" if mutation == "network" else "routing_repair IN_PROGRESS/true"
        content = content.replace(RESUME_TRANSITION_HEADING + "\n", RESUME_TRANSITION_HEADING + "\n" + claim + "\n", 1)
    with pytest.raises(AssertionError, match="resume_"):
        validate_resume_governing_view(content)


def test_resume_proposal_original_bytes_match_reviewed_blob() -> None:
    """RG-03/07: adding projection text cannot rewrite the owner-approved original."""
    package_root = Path(__file__).resolve().parents[1]
    content = (package_root / RESUME_VIEW_PATHS[-1]).read_bytes().replace(b"\r\n", b"\n")
    separator = ("\n" + RESUME_TRANSITION_MARKER + "\n").encode()
    assert content.count(separator) == 1, "resume_proposal_marker"
    original = content.split(separator, 1)[0]
    blob = hashlib.sha1(b"blob " + str(len(original)).encode() + b"\0" + original).hexdigest()
    assert blob == DEFENSIVE_RESUME_DECISION["proposal_blob_sha"]


@pytest.mark.parametrize("mutation", ("extra", "delete", "duplicate", "reorder", "wildcard", "frozen"))
def test_resume_rejects_changed_application_path_list(mutation: str) -> None:
    """RG-01: conditional resume does not reauthorize any scope-list edits."""
    manifest = historical_resume_manifest()
    paths = defensive_record(manifest)["allowed_paths"]
    if mutation == "extra":
        paths.append("src/App.tsx")
    elif mutation == "delete":
        paths.pop()
    elif mutation == "duplicate":
        paths.append(paths[-1])
    elif mutation == "reorder":
        paths.reverse()
    elif mutation == "wildcard":
        paths[-1] = "tests/*"
    else:
        paths[-1] = "backend/aas_kernel.py"
    with pytest.raises(AssertionError, match="defensive_record_mismatch"):
        validate_defensive_resume(defensive_record(manifest), manifest["execution_sequence"]["active_target"])


@pytest.mark.parametrize("mutation", ("missing", "duplicate"))
def test_resume_proposal_rejects_separator_mutation(
    monkeypatch: pytest.MonkeyPatch, mutation: str,
) -> None:
    """Reject both boundary mutations; characterize the former first-split behavior."""
    package_root = Path(__file__).resolve().parents[1]
    content = (package_root / RESUME_VIEW_PATHS[-1]).read_bytes().replace(b"\r\n", b"\n")
    separator = ("\n" + RESUME_TRANSITION_MARKER + "\n").encode()
    assert content.count(separator) == 1, "resume_proposal_marker"
    original = content.split(separator, 1)[0]
    if mutation == "missing":
        tampered = content.replace(separator, b"\n", 1)
        # Former split returned the entire file, obscuring the missing boundary.
        assert tampered.split(separator, 1)[0] == tampered
    else:
        tampered = content + separator + b"duplicate projection\n"
        # Former split kept identical reviewed bytes despite a duplicate boundary.
        assert tampered.split(separator, 1)[0] == original
    monkeypatch.setattr(Path, "read_bytes", lambda _path: tampered)
    with pytest.raises(AssertionError, match=r"^resume_proposal_marker(?:\n|$)"):
        test_resume_proposal_original_bytes_match_reviewed_blob()

# CS acceptance: governance only, no runtime/security/provider readiness claim.
CONSUMPTION_VIEW_MARKER = "<!-- F01A-CONSUMPTION-SCOPE-REGISTRATION-2026-10-09 -->"
CONSUMPTION_VIEW_HEADING = "### تسجيل نطاق استهلاك F-01A دون استئناف — مرشح 2026-10-09"
CONSUMPTION_VIEW_TOKENS = json.loads(r'''["GOVERNANCE_TRANSITION_CANDIDATE / REVIEW_REQUIRED / NOT_EFFECTIVE_UNTIL_SEPARATE_OWNER_MERGE_APPROVAL","f01a_defensive_ingress IN_PROGRESS/false","execution_authorized=false","active_target محفوظ ومحسوب","تسعة مسارات","START → STOP_CHECKPOINT → SCOPE_EXTENSION → RESUME → STOP_CHECKPOINT → SCOPE_EXTENSION","2026-10-09T12:31:30Z","23ea4b48e4c2f4c94e4f54c33bb0310bd6e0adc3","ac40d84cb7bfca4ea025cf754483a0561037e994","6211418ca295e710be7f686bd1592bb30649f1d6","DECISION-FC20-12-F01A-CONSUMPTION-REGISTRATION-PREPARATION-2026-10-09","https://github.com/alphasigma13579-lang/ASIE/pull/193#issuecomment-6080941469","PREPARE_GOVERNANCE_PR_ONLY_NO_MERGE_NO_RESUME","fa806ce545a3432739167fbe042a731930b15f9e","042f89fce3adf1509ec0e6ee3e377c921820fde6","NEW_OWNER_DECISION_AND_REVIEWED_EXACT_HEAD_GOVERNANCE_TRANSITION","CS-01–CS-08","T08 OPEN","FC20-05 held","delivery_evidence=null","closure_effect=NONE","DARK_OFFLINE","network/provider/deployment=false","REGISTERED_BLOCKED/false","PENDING","2dccc2c45c2b1967e277edf6db6a681a04b2654a","435777008e01bafc73ab3bca86cc8945e311b610"]''')
CONSUMPTION_VIEW_PREFIX_BLOBS = json.loads(r'''{"docs/FOUNDATION-COMPLETE-20-CORE-INTELLIGENCE-COMPLETION-PROGRAM-2026-07-29.md":"3fea7b946c23b008bdfd79af13da9516b97f2052","docs/EKB/FOUNDATION-COMPLETE-20-PACKAGE-INDEX.md":"3d396b65bb582e59d0eec721245724336d04b84d","docs/ASIE-BETA-EXECUTION-MASTER-PLAN-2026-09-09.md":"6e4ce8d86537548b350e9757a515b1839621a9d6","docs/FC20-12-F01A-DEFENSIVE-ENABLING-REGISTRATION-PROPOSAL-2026-10-01.md":"fa5cf3dd7eb973fed73507fe26df2d16be5238a0"}''')
CONSUMPTION_VIEW_PATHS = (
    *CONSUMPTION_VIEW_PREFIX_BLOBS,
    "docs/FC20-12-F01A-APPROVAL-CONSUMPTION-SCOPE-REGISTRATION-2026-10-09.md",
)


def validate_consumption_governing_view(content: str) -> None:
    """CS-07: require evidence in one bounded section, not in historical material."""
    assert content.count(CONSUMPTION_VIEW_MARKER) == 1, "consumption_view_marker"
    section = content.split(CONSUMPTION_VIEW_MARKER, 1)[1].lstrip("\n")
    heading, _, body = section.partition("\n")
    assert heading == CONSUMPTION_VIEW_HEADING, "consumption_view_heading"
    section = re.split(r"(?m)^(?:#{1,3}\s|<!-- )", body, maxsplit=1)[0]
    for token in CONSUMPTION_VIEW_TOKENS:
        assert token in section, "consumption_view_missing:" + token
    for path in CONSUMPTION_SCOPE_RECORD["allowed_paths"]:
        assert path in section, "consumption_view_scope:" + path
    assert not re.search(
        r"(?:execution_authorized|network_authorized|provider_activation_authorized"
        r"|deployment_authorized|external_network_authorized|public_release_authorized)"
        r"\s*=\s*(?:true|1)\b|(?:routing_repair|f01a_defensive_ingress)"
        r"\s+(?:IN_PROGRESS|DELIVERED)/true",
        section, re.IGNORECASE,
    ), "consumption_view_authority_claim"


def test_consumption_scope_is_stopped_with_exact_history_and_one_slot() -> None:
    """CS-01/05/06: entire inverse chain, not subset assertions or delivery claims."""
    manifest = load_manifest()
    validate_routing_registration(manifest)
    record = defensive_record(manifest)
    assert record == CONSUMPTION_SCOPE_RECORD
    assert record["execution_authorized"] is False
    assert record["events"][:4] == DEFENSIVE_RESUME_RECORD["events"]
    assert record["events"][4:] == [CONSUMPTION_STOP_EVENT, CONSUMPTION_SCOPE_EVENT]
    assert len(record["allowed_paths"]) == len(set(record["allowed_paths"])) == 9
    assert record["allowed_paths"][:-1] == DEFENSIVE_RESUME_RECORD["allowed_paths"]
    assert record["allowed_paths"][-1:] == ["tests/test_intelligence_consumption.py"]
    historical = validate_consumption_scope_baseline(manifest)
    validate_defensive_resume(defensive_record(historical), DEFENSIVE_START_TARGET)
    validate_scope_extension_baseline(validate_resume_baseline(historical))
    assert active_execution_targets(
        manifest["packages"],
        {p["package_id"] for p in manifest["execution_sequence"]["held_packages"]},
    ) == ["FC20-12/f01a_defensive_ingress"]


@pytest.mark.parametrize("event_index,event", ((4, CONSUMPTION_STOP_EVENT), (5, CONSUMPTION_SCOPE_EVENT)))
def test_consumption_scope_requires_all_event_fields(event_index: int, event: dict) -> None:
    """CS-02: every evidence field is mandatory."""
    for field in event:
        manifest = load_manifest()
        defensive_record(manifest)["events"][event_index].pop(field)
        with pytest.raises(AssertionError, match="defensive_record_mismatch"):
            validate_routing_registration(manifest)


@pytest.mark.parametrize("event_index,event", ((4, CONSUMPTION_STOP_EVENT), (5, CONSUMPTION_SCOPE_EVENT)))
def test_consumption_scope_pins_every_evidence_leaf(event_index: int, event: dict) -> None:
    """CS-02: independent fixed oracle, not recomputed authority from the input."""
    for path in resume_leaf_paths(event):
        manifest = load_manifest()
        target = defensive_record(manifest)["events"][event_index]
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = "[unreviewed]"
        with pytest.raises(AssertionError, match="defensive_record_mismatch"):
            validate_routing_registration(manifest)


@pytest.mark.parametrize("record", (
    DEFENSIVE_REGISTRATION, DEFENSIVE_START_RECORD, DEFENSIVE_STOP_RECORD,
    DEFENSIVE_SCOPE_EXTENSION_RECORD, DEFENSIVE_RESUME_RECORD,
))
def test_consumption_scope_does_not_admit_any_historical_state(record: dict) -> None:
    """CS-03: preserved historical positives never become current fallbacks."""
    manifest = load_manifest()
    next(p for p in manifest["packages"] if p["id"] == "FC20-12")["execution_slices"][1] = deepcopy(record)
    with pytest.raises(AssertionError, match="defensive_record_mismatch"):
        validate_routing_registration(manifest)


@pytest.mark.parametrize("index", range(6))
@pytest.mark.parametrize("mutation", ("delete", "duplicate", "change"))
def test_consumption_scope_preserves_each_history_event(index: int, mutation: str) -> None:
    """CS-03: no erasure, repeated transition or retroactive amendment."""
    manifest = load_manifest()
    events = defensive_record(manifest)["events"]
    if mutation == "delete":
        events.pop(index)
    elif mutation == "duplicate":
        events.insert(index, deepcopy(events[index]))
    else:
        events[index]["type"] = "RESUME_OVERRIDE"
    with pytest.raises(AssertionError, match="defensive_record_mismatch"):
        validate_routing_registration(manifest)


@pytest.mark.parametrize("field,value", (
    ("execution_authorized", True), ("execution_authorized", 0),
    ("state", "DELIVERED"), ("delivery_evidence", {"status": "PASS"}),
    ("closure_effect", "COMPLETE"), ("environment", "LIVE"),
    ("network_authorized", True), ("network_authorized", 0),
    ("provider_activation_authorized", True), ("deployment_authorized", True),
    ("supplied_approval", True),
))
def test_consumption_scope_rejects_implicit_resume_or_delivery(field: str, value: object) -> None:
    """CS-04: equality alone must not admit non-boolean flags."""
    manifest = load_manifest()
    defensive_record(manifest)[field] = value
    with pytest.raises(AssertionError):
        validate_routing_registration(manifest)


@pytest.mark.parametrize("mutation", ("extra", "delete", "duplicate", "reorder", "wildcard", "frozen", "pr192"))
def test_consumption_scope_rejects_unapproved_paths(mutation: str) -> None:
    """CS-04: one exact new path, never an independent unmerged proposal."""
    manifest = load_manifest()
    paths = defensive_record(manifest)["allowed_paths"]
    if mutation == "extra":
        paths.append("src/App.tsx")
    elif mutation == "delete":
        paths.pop()
    elif mutation == "duplicate":
        paths.append(paths[-1])
    elif mutation == "reorder":
        paths.reverse()
    else:
        paths[-1] = {
            "wildcard": "tests/*", "frozen": "backend/aas_kernel.py",
            "pr192": "tests/test_tenant_isolation_matrix.py",
        }[mutation]
    with pytest.raises(AssertionError, match="defensive_record_mismatch"):
        validate_routing_registration(manifest)


@pytest.mark.parametrize("index", (4, 5))
def test_consumption_scope_rejects_unknown_authority_fields(index: int) -> None:
    """CS-02: reject extra authority fields in either new event."""
    manifest = load_manifest()
    defensive_record(manifest)["events"][index]["supplied_approval"] = True
    with pytest.raises(AssertionError, match="defensive_record_mismatch"):
        validate_routing_registration(manifest)


@pytest.mark.parametrize("mutation", (
    "root", "rule", "package", "dependency", "hold", "slot", "frozen", "routing", "release",
))
def test_consumption_inverse_rejects_unrelated_manifest_delta(mutation: str) -> None:
    """CS-05: entire baseline, including fields not individually selected by guards."""
    manifest = load_manifest()
    packages = {p["id"]: p for p in manifest["packages"]}
    if mutation == "root":
        manifest["override"] = True
    elif mutation == "rule":
        manifest["rules"]["single_source_of_truth"] = False
    elif mutation == "package":
        packages["FC20-05"]["title"] = "changed"
    elif mutation == "dependency":
        packages["FC20-12"]["depends_on"].pop()
    elif mutation == "hold":
        manifest["execution_sequence"]["held_packages"] = []
    elif mutation == "slot":
        manifest["execution_sequence"]["max_active_executions"] = 2
    elif mutation == "frozen":
        manifest["frozen_files"].append("backend/unknown.py")
    elif mutation == "routing":
        packages["FC20-12"]["execution_slices"][0]["required_entry_controls"]["single_active_execution"]["status"] = "PASS"
    else:
        manifest["public_release_authorized"] = True
    with pytest.raises(AssertionError, match="consumption_scope_baseline_mismatch"):
        validate_consumption_scope_baseline(manifest)


@pytest.mark.parametrize("relative_path", CONSUMPTION_VIEW_PATHS)
def test_consumption_scope_candidate_is_consistent_in_governing_views(relative_path: str) -> None:
    """CS-07: require the same bounded candidate evidence in every governing view."""
    content = (Path(__file__).resolve().parents[1] / relative_path).read_text(encoding="utf-8")
    validate_consumption_governing_view(content)


@pytest.mark.parametrize("token", CONSUMPTION_VIEW_TOKENS)
def test_consumption_view_does_not_borrow_evidence_from_other_sections(token: str) -> None:
    """CS-07: evidence outside the candidate section cannot satisfy its guard."""
    content = (Path(__file__).resolve().parents[1] / CONSUMPTION_VIEW_PATHS[0]).read_text(encoding="utf-8")
    before, section = content.split(CONSUMPTION_VIEW_MARKER, 1)
    tampered = before + token + "\n" + CONSUMPTION_VIEW_MARKER + section.replace(token, "[removed]")
    with pytest.raises(AssertionError, match="consumption_view_missing"):
        validate_consumption_governing_view(tampered)


@pytest.mark.parametrize("mutation", ("missing_marker", "duplicate_marker", "heading", "resume", "network"))
def test_consumption_view_rejects_ambiguous_or_implicit_authority(mutation: str) -> None:
    """CS-07: reject ambiguous section boundaries and implicit execution authority."""
    content = (Path(__file__).resolve().parents[1] / CONSUMPTION_VIEW_PATHS[0]).read_text(encoding="utf-8")
    if mutation == "missing_marker":
        content = content.replace(CONSUMPTION_VIEW_MARKER, "")
    elif mutation == "duplicate_marker":
        content += "\n" + CONSUMPTION_VIEW_MARKER
    elif mutation == "heading":
        content = content.replace(CONSUMPTION_VIEW_HEADING, "### غير معتمد")
    else:
        claim = "execution_authorized=true" if mutation == "resume" else "network_authorized=true"
        content = content.replace(CONSUMPTION_VIEW_HEADING + "\n", CONSUMPTION_VIEW_HEADING + "\n" + claim + "\n", 1)
    with pytest.raises(AssertionError, match="consumption_view_"):
        validate_consumption_governing_view(content)


def git_blob_sha(content: bytes) -> str:
    """Return the Git blob object ID for the exact supplied bytes."""
    return hashlib.sha1(b"blob " + str(len(content)).encode() + b"\0" + content).hexdigest()


@pytest.mark.parametrize("relative_path,blob", CONSUMPTION_VIEW_PREFIX_BLOBS.items())
def test_consumption_projection_preserves_original_document_bytes(relative_path: str, blob: str) -> None:
    """CS-07: preserve each original document prefix against its pinned blob."""
    content = (Path(__file__).resolve().parents[1] / relative_path).read_bytes().replace(b"\r\n", b"\n")
    separator = ("\n" + CONSUMPTION_VIEW_MARKER + "\n").encode()
    assert content.count(separator) == 1, "consumption_prefix_separator"
    assert git_blob_sha(content.split(separator, 1)[0]) == blob, "consumption_prefix_changed"


def test_consumption_addendum_remains_exactly_the_reviewed_blob() -> None:
    """CS-08: do not amend approved C02 policy or inherit approval onto changed content."""
    path = Path(__file__).resolve().parents[1] / "docs/FC20-12-F01A-APPROVAL-CONSUMPTION-SCOPE-ADDENDUM-2026-10-09.md"
    assert git_blob_sha(path.read_bytes().replace(b"\r\n", b"\n")) == "042f89fce3adf1509ec0e6ee3e377c921820fde6"


@pytest.mark.parametrize("mutation", ("reverse", "swap", "old_decision", "nested_override"))
def test_consumption_scope_rejects_reordered_or_reused_authority(mutation: str) -> None:
    """CS-03: reject reordered events, reused decisions and nested overrides."""
    manifest = load_manifest()
    events = defensive_record(manifest)["events"]
    if mutation == "reverse":
        events.reverse()
    elif mutation == "swap":
        events[4], events[5] = events[5], events[4]
    elif mutation == "old_decision":
        events[5]["owner_scope_decision"] = deepcopy(DEFENSIVE_RESUME_DECISION)
    else:
        events[5]["owner_scope_decision"]["subject"]["trusted_override"] = True
    with pytest.raises(AssertionError, match="defensive_record_mismatch"):
        validate_routing_registration(manifest)


@pytest.mark.parametrize("mutation", ("missing", "duplicate", "prefix"))
def test_consumption_projection_rejects_boundary_or_prefix_edits(
    monkeypatch: pytest.MonkeyPatch, mutation: str,
) -> None:
    """CS-07: reject removed or repeated boundaries and changed historical prefixes."""
    relative_path, blob = next(iter(CONSUMPTION_VIEW_PREFIX_BLOBS.items()))
    content = (Path(__file__).resolve().parents[1] / relative_path).read_bytes().replace(b"\r\n", b"\n")
    separator = ("\n" + CONSUMPTION_VIEW_MARKER + "\n").encode()
    if mutation == "missing":
        tampered = content.replace(separator, b"\n", 1)
    elif mutation == "duplicate":
        tampered = content + separator
    else:
        tampered = b"modified history\n" + content
    monkeypatch.setattr(Path, "read_bytes", lambda _path: tampered)
    with pytest.raises(AssertionError, match="consumption_prefix_"):
        test_consumption_projection_preserves_original_document_bytes(relative_path, blob)


def test_consumption_manifest_loader_preserves_canonical_source() -> None:
    """CS-05: admit the exact LF source bytes without dropping or changing fields."""
    source_bytes = MANIFEST_PATH.read_bytes()
    manifest = load_manifest()
    assert source_bytes == (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    validate_consumption_scope_baseline(manifest)


@pytest.mark.parametrize("mutation", (
    "leading_space", "trailing_blank_line", "missing_final_newline",
    "compact", "indentation", "crlf",
))
def test_consumption_manifest_loader_rejects_byte_only_changes(
    monkeypatch: pytest.MonkeyPatch, mutation: str,
) -> None:
    """CS-05: unchanged parsed values cannot conceal changes to manifest bytes."""
    source_bytes = MANIFEST_PATH.read_bytes()
    manifest = json.loads(source_bytes.decode("utf-8"))
    if mutation == "leading_space":
        tampered = b" " + source_bytes
    elif mutation == "trailing_blank_line":
        tampered = source_bytes + b"\n"
    elif mutation == "missing_final_newline":
        tampered = source_bytes.removesuffix(b"\n")
    elif mutation == "compact":
        tampered = (json.dumps(manifest, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
    elif mutation == "indentation":
        tampered = (json.dumps(manifest, ensure_ascii=False, indent=4) + "\n").encode("utf-8")
    else:
        tampered = source_bytes.replace(b"\n", b"\r\n")
    assert tampered != source_bytes
    # The former parse-only loader accepted all six identical-content variants.
    assert json.loads(tampered.decode("utf-8")) == manifest
    monkeypatch.setattr(Path, "read_bytes", lambda _path: tampered)
    with pytest.raises(AssertionError, match=r"^manifest_noncanonical_source(?:\n|$)"):
        validate_consumption_scope_baseline(load_manifest())
