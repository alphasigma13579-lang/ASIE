from __future__ import annotations

import json
import hashlib
from copy import deepcopy
from functools import lru_cache
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
    source_is_canonical = source_bytes == canonical_bytes
    assert source_is_canonical, "manifest_noncanonical_source"
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
    return validate_consumption_scope_baseline(historical_consumption_manifest())


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
    """Count the conditional key-binding resume while preserving all routing holds."""
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
    validate_ci_amend(defensive_record(manifest), sequence["active_target"])


def validate_routing_registration(manifest: dict, *, allow_historical_v1: bool = False) -> None:
    """Keep routing blocked; admit only the pinned conditional review maintenance resume."""
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
    validate_ci_amend(slices[1], sequence["active_target"])
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
        validate_ci_amend_baseline(manifest)


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
    with pytest.raises(AssertionError, match="defensive_fields"):
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
        with pytest.raises(AssertionError, match="defensive_fields"):
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


# Independent fixed expectations from reviewed GitHub blobs at 864bbfe80692cb340d839f9c8a291c1d31c74006.
# Each candidate projection is terminal: its exact byte boundary is marker -> EOF.
# Never derive expected digests from mutable documents at test runtime.
CONSUMPTION_VIEW_PROJECTION_SHA256 = json.loads(r'''{"docs/FOUNDATION-COMPLETE-20-CORE-INTELLIGENCE-COMPLETION-PROGRAM-2026-07-29.md":"c71aca5fcd26ad8af4f8a18a42587875aaa36c9635ddab34807c29a7db1cdb1b","docs/EKB/FOUNDATION-COMPLETE-20-PACKAGE-INDEX.md":"f4abe5689c37805804ec7d7dceb6d67543b3f5aef0d1f6443088dd8d454bdc40","docs/ASIE-BETA-EXECUTION-MASTER-PLAN-2026-09-09.md":"c71aca5fcd26ad8af4f8a18a42587875aaa36c9635ddab34807c29a7db1cdb1b","docs/FC20-12-F01A-DEFENSIVE-ENABLING-REGISTRATION-PROPOSAL-2026-10-01.md":"c71aca5fcd26ad8af4f8a18a42587875aaa36c9635ddab34807c29a7db1cdb1b","docs/FC20-12-F01A-APPROVAL-CONSUMPTION-SCOPE-REGISTRATION-2026-10-09.md":"7285730377b5c230fb0269ebd5bf9642a6bd2ce4083fc10503623f398317bea9"}''')


def validate_consumption_governing_view(source_bytes: bytes, relative_path: str) -> None:
    """CS-07: readable diagnostics plus a per-path, exact-byte candidate seal."""
    assert isinstance(source_bytes, bytes), "consumption_view_source_bytes"
    assert relative_path in CONSUMPTION_VIEW_PROJECTION_SHA256, "consumption_view_path"
    content = source_bytes.decode("utf-8")
    assert content.count(CONSUMPTION_VIEW_MARKER) == 1, "consumption_view_marker"
    section = content.split(CONSUMPTION_VIEW_MARKER, 1)[1].lstrip("\n")
    heading, _, body = section.partition("\n")
    assert heading == CONSUMPTION_VIEW_HEADING, "consumption_view_heading"
    section = re.split(r"(?m)^(?:#{1,3}\s|<!-- )", body, maxsplit=1)[0]
    for token in CONSUMPTION_VIEW_TOKENS:
        assert token in section, "consumption_view_missing:" + token
    scope_items = re.findall(
        r"(?m)^[ \t]*(?:[-*+]|\d+[.)])[ \t]+(.*)$", section,
    )
    assert scope_items == [
        f"`{path}`" for path in CONSUMPTION_SCOPE_RECORD["allowed_paths"]
    ], "consumption_view_scope_list"
    # Readable diagnostics for common formats; the raw-byte seal below closes all other edits.
    authority_text = section.replace("`", "").replace('"', "").replace("'", "")
    authority_text = authority_text.replace("*", "").replace("~", "")
    # Strip emphasis boundaries only; identifier-internal underscores remain intact.
    authority_text = re.sub(r"(?<!\w)_+|_+(?!\w)", "", authority_text)
    assert not re.search(
        r"(?:execution_authorized|network_authorized|provider_activation_authorized"
        r"|deployment_authorized|external_network_authorized|public_release_authorized)"
        r"\s*[=:]\s*(?:true|1)\b|(?:routing_repair|f01a_defensive_ingress)"
        r"\s+(?:IN_PROGRESS|DELIVERED)\s*/\s*true",
        authority_text, re.IGNORECASE,
    ), "consumption_view_authority_claim"
    separator = ("\n" + CONSUMPTION_VIEW_MARKER + "\n").encode("utf-8")
    assert source_bytes.count(separator) == 1, "consumption_view_boundary"
    projection = source_bytes[source_bytes.index(CONSUMPTION_VIEW_MARKER.encode("utf-8")):]
    assert hashlib.sha256(projection).hexdigest() == CONSUMPTION_VIEW_PROJECTION_SHA256[relative_path], "consumption_view_projection_changed"


def test_consumption_scope_is_stopped_with_exact_history_and_one_slot() -> None:
    """CS-01/05/06: entire inverse chain, not subset assertions or delivery claims."""
    manifest = historical_consumption_manifest()
    validate_consumption_scope(defensive_record(manifest), manifest["execution_sequence"]["active_target"])
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
        manifest = historical_consumption_manifest()
        defensive_record(manifest)["events"][event_index].pop(field)
        with pytest.raises(AssertionError, match="defensive_record_mismatch"):
            validate_consumption_scope(defensive_record(manifest), manifest["execution_sequence"]["active_target"])


@pytest.mark.parametrize("event_index,event", ((4, CONSUMPTION_STOP_EVENT), (5, CONSUMPTION_SCOPE_EVENT)))
def test_consumption_scope_pins_every_evidence_leaf(event_index: int, event: dict) -> None:
    """CS-02: independent fixed oracle, not recomputed authority from the input."""
    for path in resume_leaf_paths(event):
        manifest = historical_consumption_manifest()
        target = defensive_record(manifest)["events"][event_index]
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = "[unreviewed]"
        with pytest.raises(AssertionError, match="defensive_record_mismatch"):
            validate_consumption_scope(defensive_record(manifest), manifest["execution_sequence"]["active_target"])


@pytest.mark.parametrize("record", (
    DEFENSIVE_REGISTRATION, DEFENSIVE_START_RECORD, DEFENSIVE_STOP_RECORD,
    DEFENSIVE_SCOPE_EXTENSION_RECORD, DEFENSIVE_RESUME_RECORD,
))
def test_consumption_scope_does_not_admit_any_historical_state(record: dict) -> None:
    """CS-03: preserved historical positives never become current fallbacks."""
    manifest = historical_consumption_manifest()
    next(p for p in manifest["packages"] if p["id"] == "FC20-12")["execution_slices"][1] = deepcopy(record)
    with pytest.raises(AssertionError, match="defensive_record_mismatch"):
        validate_consumption_scope(defensive_record(manifest), manifest["execution_sequence"]["active_target"])


@pytest.mark.parametrize("index", range(6))
@pytest.mark.parametrize("mutation", ("delete", "duplicate", "change"))
def test_consumption_scope_preserves_each_history_event(index: int, mutation: str) -> None:
    """CS-03: no erasure, repeated transition or retroactive amendment."""
    manifest = historical_consumption_manifest()
    events = defensive_record(manifest)["events"]
    if mutation == "delete":
        events.pop(index)
    elif mutation == "duplicate":
        events.insert(index, deepcopy(events[index]))
    else:
        events[index]["type"] = "RESUME_OVERRIDE"
    with pytest.raises(AssertionError, match="defensive_record_mismatch"):
        validate_consumption_scope(defensive_record(manifest), manifest["execution_sequence"]["active_target"])


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
    manifest = historical_consumption_manifest()
    defensive_record(manifest)[field] = value
    with pytest.raises(AssertionError):
        validate_consumption_scope(defensive_record(manifest), manifest["execution_sequence"]["active_target"])


@pytest.mark.parametrize("mutation", ("extra", "delete", "duplicate", "reorder", "wildcard", "frozen", "pr192"))
def test_consumption_scope_rejects_unapproved_paths(mutation: str) -> None:
    """CS-04: one exact new path, never an independent unmerged proposal."""
    manifest = historical_consumption_manifest()
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
        validate_consumption_scope(defensive_record(manifest), manifest["execution_sequence"]["active_target"])


@pytest.mark.parametrize("index", (4, 5))
def test_consumption_scope_rejects_unknown_authority_fields(index: int) -> None:
    """CS-02: reject extra authority fields in either new event."""
    manifest = historical_consumption_manifest()
    defensive_record(manifest)["events"][index]["supplied_approval"] = True
    with pytest.raises(AssertionError, match="defensive_record_mismatch"):
        validate_consumption_scope(defensive_record(manifest), manifest["execution_sequence"]["active_target"])


@pytest.mark.parametrize("mutation", (
    "root", "rule", "package", "dependency", "hold", "slot", "frozen", "routing", "release",
))
def test_consumption_inverse_rejects_unrelated_manifest_delta(mutation: str) -> None:
    """CS-05: entire baseline, including fields not individually selected by guards."""
    manifest = historical_consumption_manifest()
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
    content = historical_consumption_view(index_scope_historical_view(index_resume_historical_view(review_identity_historical_view(review_identity_resume_historical_view(key_binding_historical_view(key_binding_resume_historical_view(recovery_scope_historical_view(recovery_resume_historical_view(dataset_scope_historical_view(dataset_resume_historical_view(overlay_scope_historical_view(overlay_resume_historical_view(ci_scope_historical_view(ci_resume_historical_view(ci_amend_historical_view((Path(__file__).resolve().parents[1] / relative_path).read_bytes(), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path)
    validate_consumption_governing_view(content, relative_path)


@pytest.mark.parametrize("mutation", (
    "extra", "missing", "duplicate", "reorder", "unquoted_extra",
    "indented_extra", "numbered_extra", "alternate_marker_extra", "wildcard",
))
def test_consumption_view_requires_exact_ordered_scope_list(mutation: str) -> None:
    """CS-07: reject any added, removed, repeated, reordered or malformed scope item."""
    content = historical_consumption_view(index_scope_historical_view(index_resume_historical_view(review_identity_historical_view(review_identity_resume_historical_view(key_binding_historical_view(key_binding_resume_historical_view(recovery_scope_historical_view(recovery_resume_historical_view(dataset_scope_historical_view(dataset_resume_historical_view(overlay_scope_historical_view(overlay_resume_historical_view(ci_scope_historical_view(ci_resume_historical_view(ci_amend_historical_view((Path(__file__).resolve().parents[1] / CONSUMPTION_VIEW_PATHS[0]).read_bytes(), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]).decode("utf-8")
    before, section = content.split(CONSUMPTION_VIEW_MARKER, 1)
    scope_lines = [f"- `{path}`\n" for path in CONSUMPTION_SCOPE_RECORD["allowed_paths"]]
    scope_block = "".join(scope_lines)
    assert section.count(scope_block) == 1, "consumption_view_test_scope_fixture"
    extra = "- `backend/unapproved.py`\n"
    if mutation == "extra":
        changed = scope_block + extra
    elif mutation == "missing":
        changed = "".join(scope_lines[:-1])
    elif mutation == "duplicate":
        changed = scope_block + scope_lines[0]
    elif mutation == "reorder":
        changed = "".join([scope_lines[1], scope_lines[0], *scope_lines[2:]])
    elif mutation == "unquoted_extra":
        changed = scope_block + "- backend/unapproved.py\n"
    elif mutation == "indented_extra":
        changed = scope_block + "    " + extra
    elif mutation == "numbered_extra":
        changed = scope_block + "10. `backend/unapproved.py`\n"
    elif mutation == "alternate_marker_extra":
        changed = scope_block + "* `backend/unapproved.py`\n"
    else:
        changed = scope_block.replace(scope_lines[0], "- `backend/*`\n", 1)
    assert changed != scope_block
    tampered = before + CONSUMPTION_VIEW_MARKER + section.replace(scope_block, changed, 1)
    with pytest.raises(AssertionError, match=r"^consumption_view_scope_list(?:\n|$)"):
        validate_consumption_governing_view(tampered.encode("utf-8"), CONSUMPTION_VIEW_PATHS[0])


@pytest.mark.parametrize("token", CONSUMPTION_VIEW_TOKENS)
def test_consumption_view_does_not_borrow_evidence_from_other_sections(token: str) -> None:
    """CS-07: evidence outside the candidate section cannot satisfy its guard."""
    content = historical_consumption_view(index_scope_historical_view(index_resume_historical_view(review_identity_historical_view(review_identity_resume_historical_view(key_binding_historical_view(key_binding_resume_historical_view(recovery_scope_historical_view(recovery_resume_historical_view(dataset_scope_historical_view(dataset_resume_historical_view(overlay_scope_historical_view(overlay_resume_historical_view(ci_scope_historical_view(ci_resume_historical_view(ci_amend_historical_view((Path(__file__).resolve().parents[1] / CONSUMPTION_VIEW_PATHS[0]).read_bytes(), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]).decode("utf-8")
    before, section = content.split(CONSUMPTION_VIEW_MARKER, 1)
    tampered = before + token + "\n" + CONSUMPTION_VIEW_MARKER + section.replace(token, "[removed]")
    with pytest.raises(AssertionError, match="consumption_view_missing"):
        validate_consumption_governing_view(tampered.encode("utf-8"), CONSUMPTION_VIEW_PATHS[0])


@pytest.mark.parametrize("flag", (
    "execution_authorized", "network_authorized", "provider_activation_authorized",
    "deployment_authorized", "external_network_authorized", "public_release_authorized",
))
@pytest.mark.parametrize("separator", ("=", ":"))
@pytest.mark.parametrize("value", ("true", "1"))
@pytest.mark.parametrize("style", ("compact", "spaced_upper"))
@pytest.mark.parametrize("formatting", (
    "plain", "inline_code", "double_quote", "single_quote",
    "strong_star", "emphasis_star", "strong_underscore", "emphasis_underscore", "strike",
))
def test_consumption_view_rejects_contradictory_authority_assignments(
    flag: str, separator: str, value: str, style: str, formatting: str,
) -> None:
    """CS-07: plain or formatted colon/equals grants cannot hide behind false evidence."""
    content = historical_consumption_view(index_scope_historical_view(index_resume_historical_view(review_identity_historical_view(review_identity_resume_historical_view(key_binding_historical_view(key_binding_resume_historical_view(recovery_scope_historical_view(recovery_resume_historical_view(dataset_scope_historical_view(dataset_resume_historical_view(overlay_scope_historical_view(overlay_resume_historical_view(ci_scope_historical_view(ci_resume_historical_view(ci_amend_historical_view((Path(__file__).resolve().parents[1] / CONSUMPTION_VIEW_PATHS[0]).read_bytes(), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]).decode("utf-8")
    heading_line = CONSUMPTION_VIEW_HEADING + "\n"
    assert content.count(heading_line) == 1, "consumption_view_test_heading_fixture"
    gap = ""
    if style == "spaced_upper":
        flag, value, gap = flag.upper(), value.upper(), "\t"
    delimiter = {
        "plain": "", "inline_code": "`", "double_quote": '"', "single_quote": "'",
        "strong_star": "**", "emphasis_star": "*", "strong_underscore": "__",
        "emphasis_underscore": "_", "strike": "~~",
    }[formatting]
    claim = f"{delimiter}{flag}{delimiter}{gap}{separator}{gap}{delimiter}{value}{delimiter}"
    # Retain the false evidence and exact path list while adding a conflicting grant.
    tampered = content.replace(heading_line, heading_line + claim + "\n", 1)
    with pytest.raises(AssertionError, match=r"^consumption_view_authority_claim(?:\n|$)"):
        validate_consumption_governing_view(tampered.encode("utf-8"), CONSUMPTION_VIEW_PATHS[0])


@pytest.mark.parametrize("target", ("routing_repair", "f01a_defensive_ingress"))
@pytest.mark.parametrize("slash_gap", ("", " ", "\t", "\n", " \t"))
@pytest.mark.parametrize("state", ("IN_PROGRESS", "DELIVERED"))
@pytest.mark.parametrize("formatting", (
    "plain", "inline_code", "double_quote", "single_quote",
    "strong_star", "emphasis_star", "strong_underscore", "emphasis_underscore", "strike",
))
def test_consumption_view_rejects_formatted_authorized_state(
    target: str, state: str, formatting: str, slash_gap: str,
) -> None:
    """CS-07: formatting cannot conceal an execution or delivered state with true authority."""
    content = historical_consumption_view(index_scope_historical_view(index_resume_historical_view(review_identity_historical_view(review_identity_resume_historical_view(key_binding_historical_view(key_binding_resume_historical_view(recovery_scope_historical_view(recovery_resume_historical_view(dataset_scope_historical_view(dataset_resume_historical_view(overlay_scope_historical_view(overlay_resume_historical_view(ci_scope_historical_view(ci_resume_historical_view(ci_amend_historical_view((Path(__file__).resolve().parents[1] / CONSUMPTION_VIEW_PATHS[0]).read_bytes(), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]).decode("utf-8")
    heading_line = CONSUMPTION_VIEW_HEADING + "\n"
    assert content.count(heading_line) == 1, "consumption_view_test_heading_fixture"
    delimiter = {
        "plain": "", "inline_code": "`", "double_quote": '"', "single_quote": "'",
        "strong_star": "**", "emphasis_star": "*", "strong_underscore": "__",
        "emphasis_underscore": "_", "strike": "~~",
    }[formatting]
    claim = f"{delimiter}{target}{delimiter} {delimiter}{state}{slash_gap}/{slash_gap}true{delimiter}"
    tampered = content.replace(heading_line, heading_line + claim + "\n", 1)
    with pytest.raises(AssertionError, match=r"^consumption_view_authority_claim(?:\n|$)"):
        validate_consumption_governing_view(tampered.encode("utf-8"), CONSUMPTION_VIEW_PATHS[0])


@pytest.mark.parametrize("mutation", ("missing_marker", "duplicate_marker", "heading", "resume", "network"))
def test_consumption_view_rejects_ambiguous_or_implicit_authority(mutation: str) -> None:
    """CS-07: reject ambiguous section boundaries and implicit execution authority."""
    content = historical_consumption_view(index_scope_historical_view(index_resume_historical_view(review_identity_historical_view(review_identity_resume_historical_view(key_binding_historical_view(key_binding_resume_historical_view(recovery_scope_historical_view(recovery_resume_historical_view(dataset_scope_historical_view(dataset_resume_historical_view(overlay_scope_historical_view(overlay_resume_historical_view(ci_scope_historical_view(ci_resume_historical_view(ci_amend_historical_view((Path(__file__).resolve().parents[1] / CONSUMPTION_VIEW_PATHS[0]).read_bytes(), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]).decode("utf-8")
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
        validate_consumption_governing_view(content.encode("utf-8"), CONSUMPTION_VIEW_PATHS[0])


def git_blob_sha(content: bytes) -> str:
    """Return the Git blob object ID for the exact supplied bytes."""
    return hashlib.sha1(b"blob " + str(len(content)).encode() + b"\0" + content).hexdigest()


@pytest.mark.parametrize("relative_path,blob", CONSUMPTION_VIEW_PREFIX_BLOBS.items())
def test_consumption_projection_preserves_original_document_bytes(relative_path: str, blob: str) -> None:
    """CS-07: preserve each original document prefix against its pinned blob."""
    content = (Path(__file__).resolve().parents[1] / relative_path).read_bytes()
    separator = ("\n" + CONSUMPTION_VIEW_MARKER + "\n").encode()
    assert content.count(separator) == 1, "consumption_prefix_separator"
    assert git_blob_sha(content.split(separator, 1)[0]) == blob, "consumption_prefix_changed"


def test_consumption_addendum_remains_exactly_the_reviewed_blob() -> None:
    """CS-08: do not amend approved C02 policy or inherit approval onto changed content."""
    path = Path(__file__).resolve().parents[1] / "docs/FC20-12-F01A-APPROVAL-CONSUMPTION-SCOPE-ADDENDUM-2026-10-09.md"
    assert git_blob_sha(path.read_bytes()) == "042f89fce3adf1509ec0e6ee3e377c921820fde6", "consumption_addendum_changed"


@pytest.mark.parametrize("mutation", ("reverse", "swap", "old_decision", "nested_override"))
def test_consumption_scope_rejects_reordered_or_reused_authority(mutation: str) -> None:
    """CS-03: reject reordered events, reused decisions and nested overrides."""
    manifest = historical_consumption_manifest()
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
        validate_consumption_scope(defensive_record(manifest), manifest["execution_sequence"]["active_target"])


@pytest.mark.parametrize("mutation", ("missing", "duplicate", "prefix"))
def test_consumption_projection_rejects_boundary_or_prefix_edits(
    monkeypatch: pytest.MonkeyPatch, mutation: str,
) -> None:
    """CS-07: reject removed or repeated boundaries and changed historical prefixes."""
    relative_path, blob = next(iter(CONSUMPTION_VIEW_PREFIX_BLOBS.items()))
    content = (Path(__file__).resolve().parents[1] / relative_path).read_bytes()
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
    validate_ci_amend_baseline(manifest)


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

@pytest.mark.parametrize("relative_path,blob", CONSUMPTION_VIEW_PREFIX_BLOBS.items())
@pytest.mark.parametrize("mutation", ("prefix_crlf", "whole_crlf"))
def test_consumption_projection_rejects_line_ending_only_edits(
    monkeypatch: pytest.MonkeyPatch, relative_path: str, blob: str, mutation: str,
) -> None:
    """CS-07: reject byte-only prefix edits even when normalized content is identical."""
    content = (Path(__file__).resolve().parents[1] / relative_path).read_bytes()
    separator = ("\n" + CONSUMPTION_VIEW_MARKER + "\n").encode()
    assert content.count(separator) == 1, "consumption_prefix_separator"
    prefix, projection = content.split(separator, 1)
    if mutation == "prefix_crlf":
        tampered = prefix.replace(b"\n", b"\r\n") + separator + projection
        failure = r"^consumption_prefix_changed(?:\n|$)"
    else:
        tampered = content.replace(b"\n", b"\r\n")
        failure = r"^consumption_prefix_separator(?:\n|$)"
    assert tampered != content
    # Characterize the former normalization bypass, not the corrected guard.
    assert tampered.replace(b"\r\n", b"\n") == content
    monkeypatch.setattr(Path, "read_bytes", lambda _path: tampered)
    with pytest.raises(AssertionError, match=failure):
        test_consumption_projection_preserves_original_document_bytes(relative_path, blob)


@pytest.mark.parametrize("mutation", ("crlf", "trailing_blank_line", "missing_final_newline"))
def test_consumption_addendum_rejects_source_byte_edits(
    monkeypatch: pytest.MonkeyPatch, mutation: str,
) -> None:
    """CS-08: the reviewed addendum hash admits its original bytes only."""
    path = Path(__file__).resolve().parents[1] / "docs/FC20-12-F01A-APPROVAL-CONSUMPTION-SCOPE-ADDENDUM-2026-10-09.md"
    content = path.read_bytes()
    if mutation == "crlf":
        tampered = content.replace(b"\n", b"\r\n")
        assert tampered.replace(b"\r\n", b"\n") == content
    elif mutation == "trailing_blank_line":
        tampered = content + b"\n"
    else:
        assert content.endswith(b"\n"), "consumption_addendum_test_final_newline"
        tampered = content.removesuffix(b"\n")
    assert tampered != content
    monkeypatch.setattr(Path, "read_bytes", lambda _path: tampered)
    with pytest.raises(AssertionError, match=r"^consumption_addendum_changed(?:\n|$)"):
        test_consumption_addendum_remains_exactly_the_reviewed_blob()


@pytest.mark.parametrize("relative_path", CONSUMPTION_VIEW_PATHS)
@pytest.mark.parametrize("mutation", (
    "blockquoted_extra", "nested_blockquoted_extra", "escaped_flag",
    "decimal_entity_flag", "hex_entity_flag", "escaped_state", "entity_state",
    "encoded_extra_path", "suffix_heading", "suffix_comment", "suffix_h4",
    "prose_crlf", "boundary_blank_line", "trailing_blank_line", "missing_final_newline",
))
def test_consumption_view_byte_seal_rejects_markdown_and_boundary_edits(
    relative_path: str, mutation: str,
) -> None:
    """CS-07: partial Markdown parsing cannot admit any unreviewed terminal bytes."""
    source_bytes = historical_consumption_view(index_scope_historical_view(index_resume_historical_view(review_identity_historical_view(review_identity_resume_historical_view(key_binding_historical_view(key_binding_resume_historical_view(recovery_scope_historical_view(recovery_resume_historical_view(dataset_scope_historical_view(dataset_resume_historical_view(overlay_scope_historical_view(overlay_resume_historical_view(ci_scope_historical_view(ci_resume_historical_view(ci_amend_historical_view((Path(__file__).resolve().parents[1] / relative_path).read_bytes(), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path)
    content = source_bytes.decode("utf-8")
    heading_line = CONSUMPTION_VIEW_HEADING + "\n"
    assert content.count(heading_line) == 1, "consumption_view_test_heading_fixture"
    injected = {
        "blockquoted_extra": "> - backend/unapproved.py\n",
        "nested_blockquoted_extra": "> > - backend/unapproved.py\n",
        "escaped_flag": r"execution\_authorized=true" + "\n",
        "decimal_entity_flag": "execution&#95;authorized=true\n",
        "hex_entity_flag": "execution&#x5f;authorized=true\n",
        "escaped_state": r"f01a\_defensive\_ingress IN_PROGRESS/true" + "\n",
        "entity_state": "routing&#95;repair DELIVERED/true\n",
        "encoded_extra_path": "> - backend&#47;unapproved.py\n",
    }
    if mutation in injected:
        tampered = content.replace(heading_line, heading_line + injected[mutation], 1).encode("utf-8")
    elif mutation.startswith("suffix_"):
        suffix = {
            "suffix_heading": "\n### Override\nexecution_authorized=true\n",
            "suffix_comment": "\n<!-- Override -->\n> - backend/unapproved.py\n",
            "suffix_h4": "\n#### Override\nexecution&#95;authorized=true\n",
        }[mutation]
        tampered = source_bytes + suffix.encode("utf-8")
    elif mutation == "prose_crlf":
        # Change one non-token prose line only: old semantic checks still pass.
        line = "هذا إسقاط مرشح لا يعيد كتابة السجلات التاريخية."
        before, projection = content.split(CONSUMPTION_VIEW_MARKER, 1)
        lines = projection.splitlines(keepends=True)
        matches = [index for index, item in enumerate(lines) if item.startswith(line)]
        assert len(matches) == 1, "consumption_view_test_prose_fixture"
        index = matches[0]
        assert lines[index].endswith("\n")
        lines[index] = lines[index].removesuffix("\n") + "\r\n"
        tampered = (before + CONSUMPTION_VIEW_MARKER + "".join(lines)).encode("utf-8")
    elif mutation == "boundary_blank_line":
        marker_line = (CONSUMPTION_VIEW_MARKER + "\n").encode("utf-8")
        tampered = source_bytes.replace(marker_line, marker_line + b"\n", 1)
    elif mutation == "missing_final_newline":
        assert source_bytes.endswith(b"\n")
        tampered = source_bytes.removesuffix(b"\n")
    else:
        tampered = source_bytes + b"\n"
    assert tampered != source_bytes
    with pytest.raises(AssertionError, match=r"^consumption_view_projection_changed(?:\n|$)"):
        validate_consumption_governing_view(tampered, relative_path)


@pytest.mark.parametrize("relative_path", CONSUMPTION_VIEW_PATHS)
def test_consumption_view_seal_is_bound_to_its_document_path(relative_path: str) -> None:
    """CS-07: legitimate link/self-link variants cannot be borrowed across paths."""
    other_path = (
        CONSUMPTION_VIEW_PATHS[1]
        if relative_path != CONSUMPTION_VIEW_PATHS[1]
        else CONSUMPTION_VIEW_PATHS[0]
    )
    assert CONSUMPTION_VIEW_PROJECTION_SHA256[relative_path] != CONSUMPTION_VIEW_PROJECTION_SHA256[other_path]
    content = historical_consumption_view(index_scope_historical_view(index_resume_historical_view(review_identity_historical_view(review_identity_resume_historical_view(key_binding_historical_view(key_binding_resume_historical_view(recovery_scope_historical_view(recovery_resume_historical_view(dataset_scope_historical_view(dataset_resume_historical_view(overlay_scope_historical_view(overlay_resume_historical_view(ci_scope_historical_view(ci_resume_historical_view(ci_amend_historical_view((Path(__file__).resolve().parents[1] / other_path).read_bytes(), other_path), other_path), other_path), other_path), other_path), other_path), other_path), other_path), other_path), other_path), other_path), other_path), other_path), other_path), other_path), other_path)
    with pytest.raises(AssertionError, match=r"^consumption_view_projection_changed(?:\n|$)"):
        validate_consumption_governing_view(content, relative_path)


@pytest.mark.parametrize("relative_path", ("", "docs/unapproved.md", "tests/test_intelligence_consumption.py"))
def test_consumption_view_seal_rejects_unregistered_document_path(relative_path: str) -> None:
    """CS-07: no generic/default digest for an unregistered governing view."""
    content = historical_consumption_view(index_scope_historical_view(index_resume_historical_view(review_identity_historical_view(review_identity_resume_historical_view(key_binding_historical_view(key_binding_resume_historical_view(recovery_scope_historical_view(recovery_resume_historical_view(dataset_scope_historical_view(dataset_resume_historical_view(overlay_scope_historical_view(overlay_resume_historical_view(ci_scope_historical_view(ci_resume_historical_view(ci_amend_historical_view((Path(__file__).resolve().parents[1] / CONSUMPTION_VIEW_PATHS[0]).read_bytes(), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0])
    with pytest.raises(AssertionError, match=r"^consumption_view_path(?:\n|$)"):
        validate_consumption_governing_view(content, relative_path)


def test_consumption_view_seal_requires_original_source_bytes() -> None:
    """CS-07: text-mode newline normalization is not an admissible input."""
    content = recovery_scope_historical_view(recovery_resume_historical_view(dataset_scope_historical_view(dataset_resume_historical_view(overlay_scope_historical_view(overlay_resume_historical_view(ci_scope_historical_view(ci_resume_historical_view(ci_amend_historical_view((Path(__file__).resolve().parents[1] / CONSUMPTION_VIEW_PATHS[0]).read_bytes(), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]).decode("utf-8")
    with pytest.raises(AssertionError, match=r"^consumption_view_source_bytes(?:\n|$)"):
        validate_consumption_governing_view(content, CONSUMPTION_VIEW_PATHS[0])


# CRG: independent constants transcribed from the real owner receipt and reviewed
# #195 proposal. Never derive admission authority from the input manifest or docs.
CONSUMPTION_RESUME_DECISION = json.loads(r'''{
  "id": "DECISION-FC20-12-F01A-CONSUMPTION-CONDITIONAL-RESUME-2026-10-10",
  "recorded_at": "2026-10-10T19:21:30Z",
  "effect": "F01A_DEFENSIVE_RESUME_ONLY",
  "condition": "REVIEWED_GOVERNANCE_TRANSITION_MERGED_AFTER_SEPARATE_OWNER_MERGE_APPROVAL",
  "subject": {
    "baseline_commit_sha": "cf45bd9ecfda815c4c2e848f69832ebf02935fb9",
    "baseline_manifest_blob_sha": "e8d700eed195244ed6e2236ca53df655b5ac561f",
    "checkpoint": {
      "type": "STOP_CHECKPOINT",
      "recorded_at": "2026-10-09T12:31:30Z",
      "baseline_commit_sha": "23ea4b48e4c2f4c94e4f54c33bb0310bd6e0adc3",
      "baseline_manifest_blob_sha": "ac40d84cb7bfca4ea025cf754483a0561037e994",
      "application_head_sha": "6211418ca295e710be7f686bd1592bb30649f1d6",
      "reason": "CONSUMPTION_REVIEW_AND_TEST_SCOPE_GAP",
      "requested_path": "tests/test_intelligence_consumption.py",
      "evidence": {
        "url": "https://github.com/alphasigma13579-lang/ASIE/blob/23ea4b48e4c2f4c94e4f54c33bb0310bd6e0adc3/ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/docs/FC20-12-F01A-APPROVAL-CONSUMPTION-SCOPE-ADDENDUM-2026-10-09.md",
        "commit_sha": "23ea4b48e4c2f4c94e4f54c33bb0310bd6e0adc3",
        "blob_sha": "042f89fce3adf1509ec0e6ee3e377c921820fde6"
      },
      "resume_requirement": "NEW_OWNER_DECISION_AND_REVIEWED_EXACT_HEAD_GOVERNANCE_TRANSITION"
    },
    "application_head_sha": "6211418ca295e710be7f686bd1592bb30649f1d6",
    "allowed_paths": [
      "backend/asie_local_api.py",
      "backend/repository.py",
      "backend/intelligence_prerun_service.py",
      "tests/test_repository_intelligence.py",
      "tests/test_intelligence_prerun_service.py",
      "tests/test_intelligence_context_ingress_api.py",
      "docs/FC20-12-F01-TRUSTED-CONTEXT-INGRESS-REPAIR-PLAN-2026-10-01.md",
      "tests/test_live_location_api.py",
      "tests/test_intelligence_consumption.py"
    ]
  },
  "proposal_commit_sha": "0bc55b0b069fe8f1c0efb19c252a53251391c23e",
  "proposal_blob_sha": "7b73c89d3b217beb038ad16db8d1d126cba2b060",
  "record_url": "https://github.com/alphasigma13579-lang/ASIE/pull/195#issuecomment-6101266369"
}''')
CONSUMPTION_RESUME_EVENT = {
    "type": "RESUME",
    "recorded_at": "2026-10-10T19:25:17Z",
    "baseline_commit_sha": "cf45bd9ecfda815c4c2e848f69832ebf02935fb9",
    "baseline_manifest_blob_sha": "e8d700eed195244ed6e2236ca53df655b5ac561f",
    "checkpoint": deepcopy(CONSUMPTION_STOP_EVENT),
    "scope_extension": deepcopy(CONSUMPTION_SCOPE_EVENT),
    "owner_resume_decision": deepcopy(CONSUMPTION_RESUME_DECISION),
    "effect": "F01A_DEFENSIVE_RESUME_ONLY",
}
CONSUMPTION_RESUME_RECORD = deepcopy(CONSUMPTION_SCOPE_RECORD)
CONSUMPTION_RESUME_RECORD["execution_authorized"] = True
CONSUMPTION_RESUME_RECORD["events"].append(deepcopy(CONSUMPTION_RESUME_EVENT))


def validate_consumption_resume(record: dict, active_target: object) -> None:
    """CRG-01/03/04: one closed, receipt-pinned current state; no historical fallback."""
    assert isinstance(record, dict), "invalid_defensive_record"
    assert set(record) == set(CONSUMPTION_RESUME_RECORD), "defensive_fields"
    assert record == CONSUMPTION_RESUME_RECORD, "defensive_record_mismatch"
    assert record["execution_authorized"] is True, "consumption_resume_literal_flag"
    assert all(record[key] is False for key in (
        "network_authorized", "provider_activation_authorized", "deployment_authorized",
    )), "defensive_external_effect"
    assert active_target == DEFENSIVE_START_TARGET, "consumption_resume_slot"


def validate_consumption_resume_baseline(manifest: dict) -> dict:
    """CRG-05: undo only the seventh event and flag; pin the entire stopped manifest."""
    restored = deepcopy(manifest)
    record = defensive_record(restored)
    validate_consumption_resume(record, restored["execution_sequence"]["active_target"])
    assert record["events"].pop() == CONSUMPTION_RESUME_EVENT
    record["execution_authorized"] = False
    validate_consumption_scope(record, restored["execution_sequence"]["active_target"])
    source_bytes = (json.dumps(restored, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    assert git_blob_sha(source_bytes) == "e8d700eed195244ed6e2236ca53df655b5ac561f", "consumption_resume_baseline_mismatch"
    return restored


def historical_consumption_manifest() -> dict:
    """Verified stopped projection for CS historical tests only; never current admission."""
    return validate_consumption_resume_baseline(historical_consumption_resume_manifest())


CONSUMPTION_RESUME_VIEW_MARKER = "<!-- F01A-CONSUMPTION-CONDITIONAL-RESUME-2026-10-10 -->"
# Five independent #194 blobs, still unchanged through #195. These seal the entire
# historical documents, including the old marker-to-EOF CS-07 seals kept above.
CONSUMPTION_RESUME_VIEW_PREFIX_BLOBS = json.loads(r'''{"docs/FOUNDATION-COMPLETE-20-CORE-INTELLIGENCE-COMPLETION-PROGRAM-2026-07-29.md":"e1182cc0b19da6edc221c814e534bb8264be783b","docs/EKB/FOUNDATION-COMPLETE-20-PACKAGE-INDEX.md":"6b7702a846e6028965cedf8028f4c29ea1a64192","docs/ASIE-BETA-EXECUTION-MASTER-PLAN-2026-09-09.md":"3b27ed9a3320738b26c1e341f446235868151b39","docs/FC20-12-F01A-DEFENSIVE-ENABLING-REGISTRATION-PROPOSAL-2026-10-01.md":"8ada62ac7aaab62dbe244be4639a05bad684a241","docs/FC20-12-F01A-APPROVAL-CONSUMPTION-SCOPE-REGISTRATION-2026-10-09.md":"b6e992d4ddfcea63661a7aa2feb66f4f255b91a5"}''')
# Independent, path-bound fixed candidate seals; exact-head review is still required.
CONSUMPTION_RESUME_VIEW_SHA256 = json.loads(r'''{"docs/FOUNDATION-COMPLETE-20-CORE-INTELLIGENCE-COMPLETION-PROGRAM-2026-07-29.md":"1173b954c6713ff6f34a9150d9a2eb6fe7110dd071211635693cb33edbfd44d5","docs/EKB/FOUNDATION-COMPLETE-20-PACKAGE-INDEX.md":"47fe27bdb9d5c6306d03d0392783edd7d7cb6b1985a0895d1aa3a9f74ed31f5a","docs/ASIE-BETA-EXECUTION-MASTER-PLAN-2026-09-09.md":"1b34e9d916c450cde27520375d8a45e1e3e09f76064d7f429e622a95f5987a70","docs/FC20-12-F01A-DEFENSIVE-ENABLING-REGISTRATION-PROPOSAL-2026-10-01.md":"383cfc79395fcce28081611fbbc319b8e6e260c742d191f2ba4e0d389b45a450","docs/FC20-12-F01A-APPROVAL-CONSUMPTION-SCOPE-REGISTRATION-2026-10-09.md":"51e691c636ebd954114920dab53c3ea718e673a64cb60faa815c1091507f6b88"}''')


def historical_consumption_view(source_bytes: bytes, relative_path: str) -> bytes:
    """CRG-06: extract history only after sealing the complete old and new boundaries."""
    assert isinstance(source_bytes, bytes), "consumption_resume_view_source_bytes"
    assert relative_path in CONSUMPTION_RESUME_VIEW_SHA256, "consumption_resume_view_path"
    marker = CONSUMPTION_RESUME_VIEW_MARKER.encode("utf-8")
    separator = b"\n" + marker + b"\n"
    assert source_bytes.count(marker) == 1, "consumption_resume_view_marker"
    assert source_bytes.count(separator) == 1, "consumption_resume_view_boundary"
    prefix, section = source_bytes.split(separator, 1)
    assert git_blob_sha(prefix) == CONSUMPTION_RESUME_VIEW_PREFIX_BLOBS[relative_path], "consumption_resume_view_prefix_changed"
    projection = marker + b"\n" + section
    assert hashlib.sha256(projection).hexdigest() == CONSUMPTION_RESUME_VIEW_SHA256[relative_path], "consumption_resume_view_projection_changed"
    # The original CS-07 validator and per-path hashes remain authoritative for
    # their exact historical marker-to-EOF bytes; no relaxed terminal splitting.
    validate_consumption_governing_view(prefix, relative_path)
    return prefix


def test_consumption_resume_has_one_delta_and_full_inverse_chain() -> None:
    """CRG-01/02/04/05/08: exact scope/history and full old CS/RG/SG inverse chain."""
    manifest = historical_consumption_resume_manifest()
    validate_consumption_resume(defensive_record(manifest), manifest["execution_sequence"]["active_target"])
    record = defensive_record(manifest)
    assert record == CONSUMPTION_RESUME_RECORD
    assert record["events"][:-1] == CONSUMPTION_SCOPE_RECORD["events"]
    assert len(record["events"]) == 7
    assert record["events"][-1]["checkpoint"] == record["events"][4]
    assert record["events"][-1]["scope_extension"] == record["events"][5]
    assert record["allowed_paths"] == CONSUMPTION_SCOPE_RECORD["allowed_paths"]
    assert len(record["allowed_paths"]) == len(set(record["allowed_paths"])) == 9
    assert manifest["execution_sequence"]["held_packages"] == HELD_PACKAGES
    assert active_execution_targets(manifest["packages"], {"FC20-05"}) == ["FC20-12/f01a_defensive_ingress"]
    stopped = validate_consumption_resume_baseline(manifest)
    historical = validate_consumption_scope_baseline(stopped)
    validate_scope_extension_baseline(validate_resume_baseline(historical))


@pytest.mark.parametrize("field", tuple(CONSUMPTION_RESUME_EVENT))
def test_consumption_resume_requires_each_closed_event_field(field: str) -> None:
    """CRG-03: incomplete evidence/decision does not become resume authority."""
    manifest = historical_consumption_resume_manifest()
    defensive_record(manifest)["events"][-1].pop(field)
    with pytest.raises(AssertionError, match="defensive_record_mismatch"):
        validate_consumption_resume(defensive_record(manifest), manifest["execution_sequence"]["active_target"])


@pytest.mark.parametrize("path", resume_leaf_paths(CONSUMPTION_RESUME_EVENT))
def test_consumption_resume_pins_every_evidence_leaf(path: list) -> None:
    """CRG-03: receipt/subject/clock/baseline/proposal and full copies are independently pinned."""
    manifest = historical_consumption_resume_manifest()
    target = defensive_record(manifest)["events"][-1]
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = "[unreviewed]"
    with pytest.raises(AssertionError, match="defensive_record_mismatch"):
        validate_consumption_resume(defensive_record(manifest), manifest["execution_sequence"]["active_target"])


@pytest.mark.parametrize("mutation", ("historical_baseline", "old_resume", "scope_receipt",
                                     "design_receipt", "merge_receipt", "nested_override", "extra_field"))
def test_consumption_resume_rejects_reused_or_ambiguous_authority(mutation: str) -> None:
    """CRG-03: neither historical baseline nor design/scope/merge evidence is a new decision."""
    manifest = historical_consumption_resume_manifest()
    event = defensive_record(manifest)["events"][-1]
    if mutation == "historical_baseline":
        event["baseline_commit_sha"] = CONSUMPTION_STOP_EVENT["baseline_commit_sha"]
        event["baseline_manifest_blob_sha"] = CONSUMPTION_STOP_EVENT["baseline_manifest_blob_sha"]
    elif mutation == "old_resume":
        event["owner_resume_decision"] = deepcopy(DEFENSIVE_RESUME_DECISION)
    elif mutation == "scope_receipt":
        event["owner_resume_decision"] = deepcopy(CONSUMPTION_SCOPE_EVENT["owner_scope_decision"])
    elif mutation in ("design_receipt", "merge_receipt"):
        event["owner_resume_decision"]["record_url"] = (
            "https://github.com/alphasigma13579-lang/ASIE/pull/195#issuecomment-" +
            ("6101124478" if mutation == "design_receipt" else "6101174377")
        )
    elif mutation == "nested_override":
        event["owner_resume_decision"]["subject"]["trusted_override"] = True
    else:
        event["supplied_approval"] = True
    with pytest.raises(AssertionError, match="defensive_record_mismatch"):
        validate_consumption_resume(defensive_record(manifest), manifest["execution_sequence"]["active_target"])


@pytest.mark.parametrize("index", range(7))
@pytest.mark.parametrize("mutation", ("delete", "duplicate", "change", "reorder"))
def test_consumption_resume_preserves_each_event(index: int, mutation: str) -> None:
    """CRG-02: no overwritten checkpoint, reordered authority or eighth event."""
    manifest = historical_consumption_resume_manifest()
    events = defensive_record(manifest)["events"]
    if mutation == "delete":
        events.pop(index)
    elif mutation == "duplicate":
        events.insert(index, deepcopy(events[index]))
    elif mutation == "reorder":
        events[index], events[(index + 1) % len(events)] = events[(index + 1) % len(events)], events[index]
    else:
        events[index]["type"] = "RESUME_OVERRIDE"
    with pytest.raises(AssertionError, match="defensive_record_mismatch"):
        validate_consumption_resume(defensive_record(manifest), manifest["execution_sequence"]["active_target"])


@pytest.mark.parametrize("field,value", (
    ("execution_authorized", 1), ("execution_authorized", False),
    ("execution_authorized", "true"), ("state", "DELIVERED"),
    ("delivery_evidence", {"status": "PASS"}), ("closure_effect", "COMPLETE"),
    ("environment", "LIVE"), ("network_authorized", 0), ("network_authorized", True),
    ("provider_activation_authorized", True), ("deployment_authorized", True),
))
def test_consumption_resume_requires_literal_flags_and_blocks_terminal_effects(
    field: str, value: object,
) -> None:
    """CRG-04/08: Python equality with 1/0 does not confer Boolean or terminal authority."""
    manifest = historical_consumption_resume_manifest()
    defensive_record(manifest)[field] = value
    with pytest.raises(AssertionError):
        validate_consumption_resume(defensive_record(manifest), manifest["execution_sequence"]["active_target"])


@pytest.mark.parametrize("record", (
    DEFENSIVE_REGISTRATION, DEFENSIVE_START_RECORD, DEFENSIVE_STOP_RECORD,
    DEFENSIVE_SCOPE_EXTENSION_RECORD, DEFENSIVE_RESUME_RECORD, CONSUMPTION_SCOPE_RECORD,
))
def test_consumption_resume_never_admits_historical_states(record: dict) -> None:
    """CRG-07: historical inverse fixtures are test evidence, not current fallback."""
    manifest = historical_consumption_resume_manifest()
    next(p for p in manifest["packages"] if p["id"] == "FC20-12")["execution_slices"][1] = deepcopy(record)
    with pytest.raises(AssertionError, match="defensive_record_mismatch"):
        validate_consumption_resume(defensive_record(manifest), manifest["execution_sequence"]["active_target"])


@pytest.mark.parametrize("mutation", (
    "root", "rule", "package", "dependency", "hold", "slot", "frozen", "routing", "release",
))
def test_consumption_resume_inverse_rejects_every_unrelated_manifest_delta(mutation: str) -> None:
    """CRG-05: entire manifest is pinned, not a selected subset of convenient fields."""
    manifest = historical_consumption_resume_manifest()
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
    with pytest.raises(AssertionError, match="consumption_resume_baseline_mismatch"):
        validate_consumption_resume_baseline(manifest)


def test_consumption_resume_cannot_be_self_authorized_by_flag_or_fixture() -> None:
    """CRG-07: setting true without the real seventh event or using lifecycle is rejected."""
    for record in (deepcopy(CONSUMPTION_SCOPE_RECORD), lifecycle_fixture()[0]):
        record["execution_authorized"] = True
        with pytest.raises(AssertionError):
            validate_consumption_resume(record, DEFENSIVE_START_TARGET)


@pytest.mark.parametrize("relative_path", tuple(CONSUMPTION_RESUME_VIEW_SHA256))
def test_consumption_resume_preserves_old_seals_and_exact_new_projection(relative_path: str) -> None:
    """CRG-06: byte-exact full history plus a unique path-bound terminal projection."""
    source = index_scope_historical_view(index_resume_historical_view(review_identity_historical_view(review_identity_resume_historical_view(key_binding_historical_view(key_binding_resume_historical_view(recovery_scope_historical_view(recovery_resume_historical_view(dataset_scope_historical_view(dataset_resume_historical_view(overlay_scope_historical_view(overlay_resume_historical_view(ci_scope_historical_view(ci_resume_historical_view(ci_amend_historical_view((Path(__file__).resolve().parents[1] / relative_path).read_bytes(), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path)
    historical_consumption_view(source, relative_path)
    assert set(CONSUMPTION_RESUME_VIEW_SHA256) == set(CONSUMPTION_VIEW_PATHS)
    assert set(CONSUMPTION_RESUME_VIEW_PREFIX_BLOBS) == set(CONSUMPTION_VIEW_PATHS)


@pytest.mark.parametrize("relative_path", tuple(CONSUMPTION_RESUME_VIEW_SHA256))
@pytest.mark.parametrize("mutation", (
    "missing_marker", "duplicate_marker", "separator", "prefix", "prefix_crlf",
    "whole_crlf", "section_crlf", "suffix", "comment", "trailing_blank_line",
    "missing_final_newline", "forged_authority", "reorder_scope", "old_section",
))
def test_consumption_resume_view_rejects_all_unreviewed_bytes(relative_path: str, mutation: str) -> None:
    """CRG-06: no suffix/comment, normalized line ending, erased history or hidden grant."""
    source = index_scope_historical_view(index_resume_historical_view(review_identity_historical_view(review_identity_resume_historical_view(key_binding_historical_view(key_binding_resume_historical_view(recovery_scope_historical_view(recovery_resume_historical_view(dataset_scope_historical_view(dataset_resume_historical_view(overlay_scope_historical_view(overlay_resume_historical_view(ci_scope_historical_view(ci_resume_historical_view(ci_amend_historical_view((Path(__file__).resolve().parents[1] / relative_path).read_bytes(), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path)
    marker = CONSUMPTION_RESUME_VIEW_MARKER.encode()
    separator = b"\n" + marker + b"\n"
    prefix, section = source.split(separator, 1)
    if mutation == "missing_marker":
        tampered = source.replace(marker, b"", 1)
    elif mutation == "duplicate_marker":
        tampered = source + separator
    elif mutation == "separator":
        tampered = source.replace(separator, b"\n\n" + marker + b"\n", 1)
    elif mutation == "prefix":
        tampered = b"edited history\n" + source
    elif mutation == "prefix_crlf":
        tampered = prefix.replace(b"\n", b"\r\n") + separator + section
    elif mutation == "whole_crlf":
        tampered = source.replace(b"\n", b"\r\n")
    elif mutation == "section_crlf":
        tampered = prefix + separator + section.replace(b"\n", b"\r\n")
    elif mutation in ("suffix", "comment", "trailing_blank_line"):
        suffix = {"suffix": b"\n### Override\n", "comment": b"\n<!-- override -->\n",
                  "trailing_blank_line": b"\n"}[mutation]
        tampered = source + suffix
    elif mutation == "missing_final_newline":
        tampered = source.removesuffix(b"\n")
    elif mutation == "forged_authority":
        tampered = prefix + separator + section + b"\nnetwork_authorized=true\n"
    elif mutation == "reorder_scope":
        first, second = (f"- `{path}`\n".encode() for path in CONSUMPTION_SCOPE_RECORD["allowed_paths"][:2])
        tampered = prefix + separator + section.replace(first + second, second + first, 1)
    else:
        tampered = prefix.replace(CONSUMPTION_VIEW_MARKER.encode(), b"<!-- forged history -->", 1) + separator + section
    assert tampered != source, "consumption_resume_view_test_mutation"
    with pytest.raises(AssertionError, match="consumption_resume_view_"):
        historical_consumption_view(tampered, relative_path)


@pytest.mark.parametrize("relative_path", tuple(CONSUMPTION_RESUME_VIEW_SHA256))
def test_consumption_resume_view_seal_cannot_be_reused_on_another_path(relative_path: str) -> None:
    """CRG-06: a valid projection from a different document is still unauthorized."""
    other = next(path for path in CONSUMPTION_RESUME_VIEW_SHA256 if path != relative_path)
    content = index_scope_historical_view(index_resume_historical_view(review_identity_historical_view(review_identity_resume_historical_view(key_binding_historical_view(key_binding_resume_historical_view(recovery_scope_historical_view(recovery_resume_historical_view(dataset_scope_historical_view(dataset_resume_historical_view(overlay_scope_historical_view(overlay_resume_historical_view(ci_scope_historical_view(ci_resume_historical_view(ci_amend_historical_view((Path(__file__).resolve().parents[1] / other).read_bytes(), other), other), other), other), other), other), other), other), other), other), other), other), other), other), other)
    with pytest.raises(AssertionError, match="consumption_resume_view_prefix_changed"):
        historical_consumption_view(content, relative_path)


@pytest.mark.parametrize("relative_path", ("", "docs/unapproved.md", "tests/test_intelligence_consumption.py"))
def test_consumption_resume_view_has_no_default_authority(relative_path: str) -> None:
    content = index_scope_historical_view(index_resume_historical_view(review_identity_historical_view(review_identity_resume_historical_view(key_binding_historical_view(key_binding_resume_historical_view(recovery_scope_historical_view(recovery_resume_historical_view(dataset_scope_historical_view(dataset_resume_historical_view(overlay_scope_historical_view(overlay_resume_historical_view(ci_scope_historical_view(ci_resume_historical_view(ci_amend_historical_view((Path(__file__).resolve().parents[1] / CONSUMPTION_VIEW_PATHS[0]).read_bytes(), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0])
    with pytest.raises(AssertionError, match="consumption_resume_view_path"):
        historical_consumption_view(content, relative_path)


def test_consumption_resume_keeps_reviewed_design_immutable() -> None:
    """CRG-03/07: the approved #195 proposal is a pinned reference, never rewritten here."""
    path = Path(__file__).resolve().parents[1] / "docs/FC20-12-F01A-CONSUMPTION-CONDITIONAL-RESUME-PROPOSAL-2026-10-10.md"
    assert git_blob_sha(path.read_bytes()) == "7b73c89d3b217beb038ad16db8d1d126cba2b060", "consumption_resume_design_changed"


@pytest.mark.parametrize("relative_path", tuple(CONSUMPTION_RESUME_VIEW_SHA256))
def test_consumption_resume_rejects_section_transplants_even_with_original_prefix(relative_path: str) -> None:
    """CRG-06: an authentic old prefix cannot legalize another document's new section."""
    other = next(path for path in CONSUMPTION_RESUME_VIEW_SHA256 if path != relative_path)
    root = Path(__file__).resolve().parents[1]
    separator = ("\n" + CONSUMPTION_RESUME_VIEW_MARKER + "\n").encode()
    prefix = index_scope_historical_view(index_resume_historical_view(review_identity_historical_view(review_identity_resume_historical_view(key_binding_historical_view(key_binding_resume_historical_view(recovery_scope_historical_view(recovery_resume_historical_view(dataset_scope_historical_view(dataset_resume_historical_view(overlay_scope_historical_view(overlay_resume_historical_view(ci_scope_historical_view(ci_resume_historical_view(ci_amend_historical_view((root / relative_path).read_bytes(), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path).split(separator, 1)[0]
    transplanted = index_scope_historical_view(index_resume_historical_view(review_identity_historical_view(review_identity_resume_historical_view(key_binding_historical_view(key_binding_resume_historical_view(recovery_scope_historical_view(recovery_resume_historical_view(dataset_scope_historical_view(dataset_resume_historical_view(overlay_scope_historical_view(overlay_resume_historical_view(ci_scope_historical_view(ci_resume_historical_view(ci_amend_historical_view((root / other).read_bytes(), other), other), other), other), other), other), other), other), other), other), other), other), other), other), other).split(separator, 1)[1]
    with pytest.raises(AssertionError, match="consumption_resume_view_projection_changed"):
        historical_consumption_view(prefix + separator + transplanted, relative_path)


def test_consumption_resume_views_require_raw_bytes() -> None:
    path = CONSUMPTION_VIEW_PATHS[0]
    content = index_scope_historical_view(index_resume_historical_view(review_identity_historical_view(review_identity_resume_historical_view(key_binding_historical_view(key_binding_resume_historical_view(recovery_scope_historical_view(recovery_resume_historical_view(dataset_scope_historical_view(dataset_resume_historical_view(overlay_scope_historical_view(overlay_resume_historical_view(ci_scope_historical_view(ci_resume_historical_view(ci_amend_historical_view((Path(__file__).resolve().parents[1] / path).read_bytes(), path), path), path), path), path), path), path), path), path), path), path), path), path), path), path).decode("utf-8")
    with pytest.raises(AssertionError, match="consumption_resume_view_source_bytes"):
        historical_consumption_view(content, path)


# ISG: reviewed #197 index-only operation scope; registration never resumes execution.
INDEX_OPERATION = json.loads(r'''{
  "operation": "CREATE_INDEX_IF_NOT_EXISTS",
  "index_name": "idx_security_audit_origin_proof",
  "table": "security_audit_events",
  "columns": [
    "action",
    "target_type",
    "target_id",
    "organization_id"
  ],
  "unique": false,
  "implementation_path": "backend/repository.py",
  "test_path": "tests/test_repository_intelligence.py"
}''')
INDEX_SCOPE_DECISION = json.loads(r'''{
  "id": "DECISION-FC20-12-F01A-INDEX-SCOPE-REGISTRATION-PREPARATION-2026-10-11",
  "record_url": "https://github.com/alphasigma13579-lang/ASIE/pull/197#issuecomment-6110969163",
  "recorded_at": "2026-10-11T14:44:04Z",
  "effect": "PREPARE_GOVERNANCE_PR_ONLY_NO_MERGE_NO_RESUME",
  "subject": {
    "baseline_commit_sha": "83afd28398c0cef9821e08c8db1162d6ec2fdfc4",
    "baseline_manifest_blob_sha": "1cfbaf1940bfc0a1e7c276fde4a9d0a8cea05a70",
    "application_head_sha": "7df4ea3c6dfbcfb70cc219ef59622b7387052dc4",
    "allowed_paths": [
      "backend/asie_local_api.py",
      "backend/repository.py",
      "backend/intelligence_prerun_service.py",
      "tests/test_repository_intelligence.py",
      "tests/test_intelligence_prerun_service.py",
      "tests/test_intelligence_context_ingress_api.py",
      "docs/FC20-12-F01-TRUSTED-CONTEXT-INGRESS-REPAIR-PLAN-2026-10-01.md",
      "tests/test_live_location_api.py",
      "tests/test_intelligence_consumption.py"
    ],
    "allowed_schema_operations": [
      {
        "operation": "CREATE_INDEX_IF_NOT_EXISTS",
        "index_name": "idx_security_audit_origin_proof",
        "table": "security_audit_events",
        "columns": [
          "action",
          "target_type",
          "target_id",
          "organization_id"
        ],
        "unique": false,
        "implementation_path": "backend/repository.py",
        "test_path": "tests/test_repository_intelligence.py"
      }
    ]
  },
  "proposal_commit_sha": "33ac90a47966afda4917f34162f11f5826eab565",
  "proposal_blob_sha": "9be7964b01ebd393724dc2adf6a559a8a1eddd64"
}''')
INDEX_STOP_EVENT = json.loads(r'''{
  "type": "STOP_CHECKPOINT",
  "recorded_at": "2026-10-11T14:50:33Z",
  "baseline_commit_sha": "83afd28398c0cef9821e08c8db1162d6ec2fdfc4",
  "baseline_manifest_blob_sha": "1cfbaf1940bfc0a1e7c276fde4a9d0a8cea05a70",
  "application_head_sha": "7df4ea3c6dfbcfb70cc219ef59622b7387052dc4",
  "reason": "AUDIT_ORIGIN_INDEX_SCHEMA_OPERATION_OUTSIDE_REGISTERED_SCOPE",
  "evidence": {
    "url": "https://github.com/alphasigma13579-lang/ASIE/blob/33ac90a47966afda4917f34162f11f5826eab565/ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/docs/FC20-12-F01A-AUDIT-ORIGIN-INDEX-SCOPE-PROPOSAL-2026-10-11.md",
    "commit_sha": "33ac90a47966afda4917f34162f11f5826eab565",
    "blob_sha": "9be7964b01ebd393724dc2adf6a559a8a1eddd64"
  },
  "resume_requirement": "NEW_OWNER_DECISION_BOUND_TO_INDEX_OPERATION_AND_REVIEWED_EXACT_HEAD_GOVERNANCE_TRANSITION"
}''')
INDEX_SCOPE_EVENT = json.loads(r'''{
  "type": "SCOPE_EXTENSION",
  "recorded_at": "2026-10-11T14:50:33Z",
  "baseline_commit_sha": "83afd28398c0cef9821e08c8db1162d6ec2fdfc4",
  "baseline_manifest_blob_sha": "1cfbaf1940bfc0a1e7c276fde4a9d0a8cea05a70",
  "application_head_sha": "7df4ea3c6dfbcfb70cc219ef59622b7387052dc4",
  "added_paths": [],
  "added_schema_operations": [
    {
      "operation": "CREATE_INDEX_IF_NOT_EXISTS",
      "index_name": "idx_security_audit_origin_proof",
      "table": "security_audit_events",
      "columns": [
        "action",
        "target_type",
        "target_id",
        "organization_id"
      ],
      "unique": false,
      "implementation_path": "backend/repository.py",
      "test_path": "tests/test_repository_intelligence.py"
    }
  ],
  "scope_addendum": {
    "url": "https://github.com/alphasigma13579-lang/ASIE/blob/33ac90a47966afda4917f34162f11f5826eab565/ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/docs/FC20-12-F01A-AUDIT-ORIGIN-INDEX-SCOPE-PROPOSAL-2026-10-11.md",
    "commit_sha": "33ac90a47966afda4917f34162f11f5826eab565",
    "blob_sha": "9be7964b01ebd393724dc2adf6a559a8a1eddd64"
  },
  "owner_scope_decision": {
    "id": "DECISION-FC20-12-F01A-INDEX-SCOPE-REGISTRATION-PREPARATION-2026-10-11",
    "record_url": "https://github.com/alphasigma13579-lang/ASIE/pull/197#issuecomment-6110969163",
    "recorded_at": "2026-10-11T14:44:04Z",
    "effect": "PREPARE_GOVERNANCE_PR_ONLY_NO_MERGE_NO_RESUME",
    "subject": {
      "baseline_commit_sha": "83afd28398c0cef9821e08c8db1162d6ec2fdfc4",
      "baseline_manifest_blob_sha": "1cfbaf1940bfc0a1e7c276fde4a9d0a8cea05a70",
      "application_head_sha": "7df4ea3c6dfbcfb70cc219ef59622b7387052dc4",
      "allowed_paths": [
        "backend/asie_local_api.py",
        "backend/repository.py",
        "backend/intelligence_prerun_service.py",
        "tests/test_repository_intelligence.py",
        "tests/test_intelligence_prerun_service.py",
        "tests/test_intelligence_context_ingress_api.py",
        "docs/FC20-12-F01-TRUSTED-CONTEXT-INGRESS-REPAIR-PLAN-2026-10-01.md",
        "tests/test_live_location_api.py",
        "tests/test_intelligence_consumption.py"
      ],
      "allowed_schema_operations": [
        {
          "operation": "CREATE_INDEX_IF_NOT_EXISTS",
          "index_name": "idx_security_audit_origin_proof",
          "table": "security_audit_events",
          "columns": [
            "action",
            "target_type",
            "target_id",
            "organization_id"
          ],
          "unique": false,
          "implementation_path": "backend/repository.py",
          "test_path": "tests/test_repository_intelligence.py"
        }
      ]
    },
    "proposal_commit_sha": "33ac90a47966afda4917f34162f11f5826eab565",
    "proposal_blob_sha": "9be7964b01ebd393724dc2adf6a559a8a1eddd64"
  },
  "effect": "SCOPE_EXTENSION_ONLY_NO_RESUME"
}''')
INDEX_VIEW_PREFIX_BLOBS = json.loads(r'''{
  "docs/FC20-12-F01A-DEFENSIVE-ENABLING-REGISTRATION-PROPOSAL-2026-10-01.md": "ba79ba386d39a9094d1d992e96462ac3ab364936",
  "docs/FC20-12-F01A-APPROVAL-CONSUMPTION-SCOPE-REGISTRATION-2026-10-09.md": "5db18dd1b704b54c455c21ec5f6d2787528ebc37",
  "docs/FOUNDATION-COMPLETE-20-CORE-INTELLIGENCE-COMPLETION-PROGRAM-2026-07-29.md": "3f05836f7b13ad6686ce6cfe905793927796b81e",
  "docs/ASIE-BETA-EXECUTION-MASTER-PLAN-2026-09-09.md": "af5e2c95b9d8655637ff244556aefa0efb77c805",
  "docs/EKB/FOUNDATION-COMPLETE-20-PACKAGE-INDEX.md": "f7d62193e636b96948cbaf8f9c56941615eeadd7"
}''')
INDEX_VIEW_SHA256 = json.loads(r'''{
  "docs/FC20-12-F01A-DEFENSIVE-ENABLING-REGISTRATION-PROPOSAL-2026-10-01.md": "ce89b73b7c30e8e9cbad6c68a312e8da4ab60aac28179fafd3844d9890e728e5",
  "docs/FC20-12-F01A-APPROVAL-CONSUMPTION-SCOPE-REGISTRATION-2026-10-09.md": "ac775378524027a18d924cb801b8c24dd15880b3c56691f017dfccd237b3137d",
  "docs/FOUNDATION-COMPLETE-20-CORE-INTELLIGENCE-COMPLETION-PROGRAM-2026-07-29.md": "e8ebfdd3cb754d1486e3b87005498353f248604b0477948f43944b49873f5d84",
  "docs/ASIE-BETA-EXECUTION-MASTER-PLAN-2026-09-09.md": "6d677822a599686d11ae0157c195b31a3bb6e76cf19c2cb6b48fdd4932a07d6a",
  "docs/EKB/FOUNDATION-COMPLETE-20-PACKAGE-INDEX.md": "0ddc53bf9327a8ec95159c64be28d2c3e4be6773af0237361cac7192a2fde82d"
}''')
INDEX_VIEW_MARKER = '<!-- F01A-AUDIT-ORIGIN-INDEX-SCOPE-REGISTRATION-2026-10-11 -->'
INDEX_SCOPE_RECORD = deepcopy(CONSUMPTION_RESUME_RECORD)
INDEX_SCOPE_RECORD["execution_authorized"] = False
INDEX_SCOPE_RECORD["allowed_schema_operations"] = [deepcopy(INDEX_OPERATION)]
INDEX_SCOPE_RECORD["events"].extend([deepcopy(INDEX_STOP_EVENT), deepcopy(INDEX_SCOPE_EVENT)])


def validate_index_scope(record: dict, active_target: object) -> None:
    """ISG-01/03/04: admit one stopped record, with no implicit or reused resume."""
    assert isinstance(record, dict), "invalid_defensive_record"
    assert set(record) == set(INDEX_SCOPE_RECORD), "defensive_fields"
    assert record == INDEX_SCOPE_RECORD, "defensive_record_mismatch"
    # Serialized equality closes Python's False == 0 / True == 1 equivalence at
    # every nested authority copy, including all historical events and subjects.
    assert json.dumps(record, sort_keys=True) == json.dumps(INDEX_SCOPE_RECORD, sort_keys=True), "index_scope_literal_types"
    assert record["execution_authorized"] is False, "index_scope_stop_flag"
    assert all(record[key] is False for key in (
        "network_authorized", "provider_activation_authorized", "deployment_authorized",
    )), "defensive_external_effect"
    assert active_target == DEFENSIVE_START_TARGET, "index_scope_slot"
    decision = record["events"][8]["owner_scope_decision"]
    assert decision == INDEX_SCOPE_DECISION, "index_scope_decision_mismatch"
    for operations in (record["allowed_schema_operations"],
                       record["events"][8]["added_schema_operations"],
                       decision["subject"]["allowed_schema_operations"]):
        assert operations == [INDEX_OPERATION], "index_scope_operation_mismatch"
        assert operations[0]["unique"] is False, "index_scope_unique_literal"
    assert re.fullmatch(
        r"https://github\.com/alphasigma13579-lang/ASIE/pull/197#issuecomment-[0-9]+",
        decision["record_url"],
    ), "index_scope_owner_receipt_unresolved"


def validate_index_scope_baseline(manifest: dict) -> dict:
    """ISG-05: remove only the operation/STOP/scope/flag delta and seal all history."""
    restored = deepcopy(manifest)
    record = defensive_record(restored)
    validate_index_scope(record, restored["execution_sequence"]["active_target"])
    assert record["events"].pop() == INDEX_SCOPE_EVENT
    assert record["events"].pop() == INDEX_STOP_EVENT
    assert record.pop("allowed_schema_operations") == [INDEX_OPERATION]
    record["execution_authorized"] = True
    validate_consumption_resume(record, restored["execution_sequence"]["active_target"])
    source = (json.dumps(restored, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    assert git_blob_sha(source) == "1cfbaf1940bfc0a1e7c276fde4a9d0a8cea05a70", "index_scope_baseline_mismatch"
    return restored


def historical_consumption_resume_manifest() -> dict:
    """Verified seven-event historical fixture; never current-state admission."""
    return validate_index_scope_baseline(historical_index_scope_manifest())


def index_scope_historical_view(source_bytes: bytes, relative_path: str) -> bytes:
    """ISG-06: path-bound new terminal seal preserves the complete CRG/CS chain."""
    assert isinstance(source_bytes, bytes), "index_view_source_bytes"
    assert relative_path in INDEX_VIEW_SHA256, "index_view_path"
    marker = INDEX_VIEW_MARKER.encode("utf-8")
    separator = b"\n" + marker + b"\n"
    assert source_bytes.count(marker) == 1, "index_view_marker"
    assert source_bytes.count(separator) == 1, "index_view_boundary"
    prefix, section = source_bytes.split(separator, 1)
    assert git_blob_sha(prefix) == INDEX_VIEW_PREFIX_BLOBS[relative_path], "index_view_prefix_changed"
    projection = marker + b"\n" + section
    assert hashlib.sha256(projection).hexdigest() == INDEX_VIEW_SHA256[relative_path], "index_view_projection_changed"
    historical_consumption_view(prefix, relative_path)
    return prefix


def test_index_scope_has_exact_operation_history_and_full_inverse_chain() -> None:
    """ISG-01/02/05/08: one held slot, nine paths, no execution, all old oracles."""
    manifest = historical_index_scope_manifest()
    validate_index_scope(defensive_record(manifest), manifest["execution_sequence"]["active_target"])
    record = defensive_record(manifest)
    assert record == INDEX_SCOPE_RECORD
    assert record["events"][:7] == CONSUMPTION_RESUME_RECORD["events"]
    assert record["events"][7:] == [INDEX_STOP_EVENT, INDEX_SCOPE_EVENT]
    assert record["allowed_paths"] == CONSUMPTION_RESUME_RECORD["allowed_paths"]
    assert len(record["allowed_paths"]) == len(set(record["allowed_paths"])) == 9
    assert record["allowed_schema_operations"] == [INDEX_OPERATION]
    assert record["events"][-1]["added_paths"] == []
    assert active_execution_targets(manifest["packages"], {"FC20-05"}) == ["FC20-12/f01a_defensive_ingress"]
    assert manifest["execution_sequence"]["held_packages"] == HELD_PACKAGES
    resumed = validate_index_scope_baseline(manifest)
    stopped = validate_consumption_resume_baseline(resumed)
    historical = validate_consumption_scope_baseline(stopped)
    validate_scope_extension_baseline(validate_resume_baseline(historical))


@pytest.mark.parametrize("index,event", ((7, INDEX_STOP_EVENT), (8, INDEX_SCOPE_EVENT)))
def test_index_scope_requires_each_new_event_field(index: int, event: dict) -> None:
    """ISG-03: no omitted evidence, effect or decision field."""
    for key in event:
        manifest = historical_index_scope_manifest()
        defensive_record(manifest)["events"][index].pop(key)
        with pytest.raises(AssertionError, match="defensive_record_mismatch"):
            validate_index_scope(defensive_record(manifest), manifest["execution_sequence"]["active_target"])


@pytest.mark.parametrize("index,event", ((7, INDEX_STOP_EVENT), (8, INDEX_SCOPE_EVENT)))
def test_index_scope_pins_each_new_evidence_leaf(index: int, event: dict) -> None:
    """ISG-03: source, owner subject, design and clock cannot be replaced."""
    for path in resume_leaf_paths(event):
        manifest = historical_index_scope_manifest()
        target = defensive_record(manifest)["events"][index]
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = "[unreviewed]"
        with pytest.raises(AssertionError, match="defensive_record_mismatch"):
            validate_index_scope(defensive_record(manifest), manifest["execution_sequence"]["active_target"])


@pytest.mark.parametrize("copy", ("record", "event", "decision"))
@pytest.mark.parametrize("mutation", (
    "missing", "empty", "duplicate", "second", "unknown", "operation", "name", "table",
    "columns", "order", "implementation", "test", "unique_true", "unique_zero",
    "unique_one", "unique_null", "unique_string", "list_type",
))
def test_index_scope_rejects_any_operation_expansion_or_type(copy: str, mutation: str) -> None:
    """ISG-01/03: exact seven-key operation in each independently checked copy."""
    manifest = historical_index_scope_manifest()
    record = defensive_record(manifest)
    target, key = (record, "allowed_schema_operations")
    if copy == "event":
        target, key = record["events"][8], "added_schema_operations"
    elif copy == "decision":
        target, key = record["events"][8]["owner_scope_decision"]["subject"], "allowed_schema_operations"
    if mutation == "missing":
        target.pop(key)
    elif mutation == "empty":
        target[key] = []
    elif mutation in ("duplicate", "second"):
        target[key].append(deepcopy(INDEX_OPERATION))
        if mutation == "second":
            target[key][-1]["index_name"] = "other_index"
    elif mutation == "list_type":
        target[key] = tuple(target[key])
    else:
        op = target[key][0]
        fields = {"unknown": ("trusted_override", True), "operation": ("operation", "DROP_INDEX"),
                  "name": ("index_name", "other_index"), "table": ("table", "other_table"),
                  "columns": ("columns", ["target_id"]), "order": ("columns", list(reversed(op["columns"]))),
                  "implementation": ("implementation_path", "backend/other.py"),
                  "test": ("test_path", "tests/other.py"), "unique_true": ("unique", True),
                  "unique_zero": ("unique", 0), "unique_one": ("unique", 1),
                  "unique_null": ("unique", None), "unique_string": ("unique", "false")}
        field, value = fields[mutation]
        op[field] = value
    with pytest.raises(AssertionError):
        validate_index_scope(defensive_record(manifest), manifest["execution_sequence"]["active_target"])


@pytest.mark.parametrize("index", range(9))
@pytest.mark.parametrize("mutation", ("delete", "duplicate", "change", "reorder"))
def test_index_scope_preserves_all_nine_events(index: int, mutation: str) -> None:
    """ISG-02: history cannot be rewritten, duplicated or reordered."""
    manifest = historical_index_scope_manifest()
    events = defensive_record(manifest)["events"]
    if mutation == "delete":
        events.pop(index)
    elif mutation == "duplicate":
        events.insert(index, deepcopy(events[index]))
    elif mutation == "change":
        events[index]["type"] = "OVERRIDE"
    else:
        other = (index + 1) % len(events)
        events[index], events[other] = events[other], events[index]
    with pytest.raises(AssertionError, match="defensive_record_mismatch"):
        validate_index_scope(defensive_record(manifest), manifest["execution_sequence"]["active_target"])


@pytest.mark.parametrize("mutation", (
    "old_decision", "old_resume", "new_resume", "start", "delivered", "extra_path",
    "reordered_paths", "event_path", "unknown_field", "extra_subject", "old_scope",
))
def test_index_scope_rejects_reused_or_implicit_authority(mutation: str) -> None:
    """ISG-03/07: accepted design and old resume cannot grant index execution."""
    manifest = historical_index_scope_manifest()
    record = defensive_record(manifest)
    if mutation == "old_decision":
        record["events"][8]["owner_scope_decision"] = deepcopy(CONSUMPTION_SCOPE_EVENT["owner_scope_decision"])
    elif mutation == "old_scope":
        record["events"][8] = deepcopy(CONSUMPTION_SCOPE_EVENT)
    elif mutation == "old_resume":
        record["events"].append(deepcopy(CONSUMPTION_RESUME_EVENT))
        record["execution_authorized"] = True
    elif mutation in ("new_resume", "start", "delivered"):
        record["events"].append({"type": {"new_resume": "RESUME", "start": "START", "delivered": "DELIVERED"}[mutation]})
    elif mutation == "extra_path":
        record["allowed_paths"].append("src/App.tsx")
    elif mutation == "reordered_paths":
        record["allowed_paths"].reverse()
    elif mutation == "event_path":
        record["events"][8]["added_paths"] = ["backend/repository.py"]
    elif mutation == "extra_subject":
        record["events"][8]["owner_scope_decision"]["subject"]["approved"] = True
    else:
        record["trusted_override"] = True
    with pytest.raises(AssertionError):
        validate_index_scope(defensive_record(manifest), manifest["execution_sequence"]["active_target"])


@pytest.mark.parametrize("field,value", (
    ("execution_authorized", True), ("execution_authorized", 0), ("execution_authorized", 1),
    ("execution_authorized", "false"), ("state", "DELIVERED"),
    ("delivery_evidence", {"status": "PASS"}), ("closure_effect", "COMPLETE"),
    ("environment", "LIVE"), ("network_authorized", 0), ("network_authorized", True),
    ("provider_activation_authorized", True), ("deployment_authorized", True),
))
def test_index_scope_requires_literal_flags_and_no_terminal_effects(field: str, value: object) -> None:
    """ISG-04/08: fail closed even for Boolean-equivalent integers."""
    manifest = historical_index_scope_manifest()
    defensive_record(manifest)[field] = value
    with pytest.raises(AssertionError):
        validate_index_scope(defensive_record(manifest), manifest["execution_sequence"]["active_target"])


@pytest.mark.parametrize("record", (
    DEFENSIVE_REGISTRATION, DEFENSIVE_START_RECORD, DEFENSIVE_STOP_RECORD,
    DEFENSIVE_SCOPE_EXTENSION_RECORD, DEFENSIVE_RESUME_RECORD, CONSUMPTION_SCOPE_RECORD,
    CONSUMPTION_RESUME_RECORD, lifecycle_fixture()[0],
))
def test_index_scope_never_admits_historical_or_fixture_states(record: dict) -> None:
    """ISG-07: current admission has no historical or lifecycle-fixture fallback."""
    with pytest.raises(AssertionError):
        validate_index_scope(deepcopy(record), DEFENSIVE_START_TARGET)


@pytest.mark.parametrize("mutation", ("root", "rule", "package", "dependency", "hold", "slot", "frozen", "routing", "release"))
def test_index_scope_full_inverse_rejects_unrelated_manifest_delta(mutation: str) -> None:
    """ISG-05: protect the entire baseline, not just the modified slice."""
    manifest = historical_index_scope_manifest()
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
    with pytest.raises(AssertionError, match="index_scope_baseline_mismatch"):
        validate_index_scope_baseline(manifest)


@pytest.mark.parametrize("slot", (None, {}, {"kind": "package", "package_id": "FC20-05"}))
def test_index_scope_retains_counted_slot(slot: object) -> None:
    """ISG-04: stopped work still owns its registered slot."""
    manifest = historical_index_scope_manifest()
    manifest["execution_sequence"]["active_target"] = slot
    with pytest.raises(AssertionError):
        validate_index_scope(defensive_record(manifest), manifest["execution_sequence"]["active_target"])


@pytest.mark.parametrize("relative_path", tuple(INDEX_VIEW_SHA256))
def test_index_scope_projections_preserve_all_old_seals(relative_path: str) -> None:
    """ISG-06: every complete pre-transition document remains byte-exact."""
    source = index_resume_historical_view(review_identity_historical_view(review_identity_resume_historical_view(key_binding_historical_view(key_binding_resume_historical_view(recovery_scope_historical_view(recovery_resume_historical_view(dataset_scope_historical_view(dataset_resume_historical_view(overlay_scope_historical_view(overlay_resume_historical_view(ci_scope_historical_view(ci_resume_historical_view(ci_amend_historical_view((Path(__file__).resolve().parents[1] / relative_path).read_bytes(), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path)
    prefix = index_scope_historical_view(source, relative_path)
    historical_consumption_view(prefix, relative_path)
    assert set(INDEX_VIEW_SHA256) == set(INDEX_VIEW_PREFIX_BLOBS) == set(CONSUMPTION_VIEW_PATHS)


@pytest.mark.parametrize("relative_path", tuple(INDEX_VIEW_SHA256))
@pytest.mark.parametrize("mutation", (
    "missing_marker", "duplicate_marker", "separator", "prefix", "prefix_crlf", "whole_crlf",
    "section_crlf", "suffix", "comment", "trailing_blank_line", "missing_final_newline",
    "forged_authority", "scope_order", "operation", "availability_gate",
))
def test_index_scope_projection_rejects_unreviewed_bytes(relative_path: str, mutation: str) -> None:
    """ISG-06/08: neither formatting nor hidden text can relax the gated scope."""
    source = index_resume_historical_view(review_identity_historical_view(review_identity_resume_historical_view(key_binding_historical_view(key_binding_resume_historical_view(recovery_scope_historical_view(recovery_resume_historical_view(dataset_scope_historical_view(dataset_resume_historical_view(overlay_scope_historical_view(overlay_resume_historical_view(ci_scope_historical_view(ci_resume_historical_view(ci_amend_historical_view((Path(__file__).resolve().parents[1] / relative_path).read_bytes(), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path)
    marker = INDEX_VIEW_MARKER.encode()
    separator = b"\n" + marker + b"\n"
    prefix, section = source.split(separator, 1)
    if mutation == "missing_marker":
        tampered = source.replace(marker, b"", 1)
    elif mutation == "duplicate_marker":
        tampered = source + separator
    elif mutation == "separator":
        tampered = source.replace(separator, b"\n\n" + marker + b"\n", 1)
    elif mutation == "prefix":
        tampered = b"edited history\n" + source
    elif mutation == "prefix_crlf":
        tampered = prefix.replace(b"\n", b"\r\n") + separator + section
    elif mutation == "whole_crlf":
        tampered = source.replace(b"\n", b"\r\n")
    elif mutation == "section_crlf":
        tampered = prefix + separator + section.replace(b"\n", b"\r\n")
    elif mutation in ("suffix", "comment", "trailing_blank_line"):
        tampered = source + {"suffix": b"\n### Override\n", "comment": b"\n<!-- override -->\n", "trailing_blank_line": b"\n"}[mutation]
    elif mutation == "missing_final_newline":
        tampered = source.removesuffix(b"\n")
    elif mutation == "forged_authority":
        tampered = prefix + separator + section.replace(b"execution_authorized=false", b"execution_authorized=true")
    elif mutation == "scope_order":
        first, second = (f"- `{path}`\n".encode() for path in CONSUMPTION_SCOPE_RECORD["allowed_paths"][:2])
        tampered = prefix + separator + section.replace(first + second, second + first)
    elif mutation == "operation":
        tampered = prefix + separator + section.replace(b"unique=false", b"unique=true")
    else:
        tampered = prefix + separator + section.replace(b"UNKNOWN / NOT_APPROVED", b"APPROVED")
    assert tampered != source
    with pytest.raises(AssertionError, match="index_view_"):
        index_scope_historical_view(tampered, relative_path)


@pytest.mark.parametrize("relative_path", tuple(INDEX_VIEW_SHA256))
def test_index_scope_projection_cannot_borrow_other_path_bytes(relative_path: str) -> None:
    """ISG-06: both full-document and suffix transplants are rejected."""
    root = Path(__file__).resolve().parents[1]
    other = next(path for path in INDEX_VIEW_SHA256 if path != relative_path)
    source, other_source = index_resume_historical_view(review_identity_historical_view(review_identity_resume_historical_view(key_binding_historical_view(key_binding_resume_historical_view(recovery_scope_historical_view(recovery_resume_historical_view(dataset_scope_historical_view(dataset_resume_historical_view(overlay_scope_historical_view(overlay_resume_historical_view(ci_scope_historical_view(ci_resume_historical_view(ci_amend_historical_view((root / relative_path).read_bytes(), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), index_resume_historical_view(review_identity_historical_view(review_identity_resume_historical_view(key_binding_historical_view(key_binding_resume_historical_view(recovery_scope_historical_view(recovery_resume_historical_view(dataset_scope_historical_view(dataset_resume_historical_view(overlay_scope_historical_view(overlay_resume_historical_view(ci_scope_historical_view(ci_resume_historical_view(ci_amend_historical_view((root / other).read_bytes(), other), other), other), other), other), other), other), other), other), other), other), other), other), other)
    separator = ("\n" + INDEX_VIEW_MARKER + "\n").encode()
    with pytest.raises(AssertionError, match="index_view_prefix_changed"):
        index_scope_historical_view(other_source, relative_path)
    transplant = source.split(separator, 1)[0] + separator + other_source.split(separator, 1)[1]
    with pytest.raises(AssertionError, match="index_view_projection_changed"):
        index_scope_historical_view(transplant, relative_path)


@pytest.mark.parametrize("path", ("", "docs/unapproved.md", "tests/test_repository_intelligence.py"))
def test_index_scope_view_has_no_unregistered_path(path: str) -> None:
    """ISG-06: no default seal or authority for an unknown path."""
    source = index_resume_historical_view(review_identity_historical_view(review_identity_resume_historical_view(key_binding_historical_view(key_binding_resume_historical_view(recovery_scope_historical_view(recovery_resume_historical_view(dataset_scope_historical_view(dataset_resume_historical_view(overlay_scope_historical_view(overlay_resume_historical_view(ci_scope_historical_view(ci_resume_historical_view(ci_amend_historical_view((Path(__file__).resolve().parents[1] / CONSUMPTION_VIEW_PATHS[0]).read_bytes(), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0])
    with pytest.raises(AssertionError, match="index_view_path"):
        index_scope_historical_view(source, path)


def test_index_scope_view_requires_raw_bytes_and_design_is_immutable() -> None:
    """ISG-06/08: no decoded-text substitute or rewrite of accepted design gates."""
    root = Path(__file__).resolve().parents[1]
    path = CONSUMPTION_VIEW_PATHS[0]
    with pytest.raises(AssertionError, match="index_view_source_bytes"):
        index_scope_historical_view((root / path).read_text(), path)
    design = root / "docs/FC20-12-F01A-AUDIT-ORIGIN-INDEX-SCOPE-PROPOSAL-2026-10-11.md"
    assert git_blob_sha(design.read_bytes()) == "9be7964b01ebd393724dc2adf6a559a8a1eddd64", "index_scope_design_changed"


@pytest.mark.parametrize("copy", ("record", "event", "decision"))
@pytest.mark.parametrize("field", tuple(INDEX_OPERATION))
def test_index_scope_requires_each_operation_field(copy: str, field: str) -> None:
    """ISG-01: every operation identity field is mandatory in every copy."""
    manifest = historical_index_scope_manifest()
    record = defensive_record(manifest)
    operations = record["allowed_schema_operations"]
    if copy == "event":
        operations = record["events"][8]["added_schema_operations"]
    elif copy == "decision":
        operations = record["events"][8]["owner_scope_decision"]["subject"]["allowed_schema_operations"]
    operations[0].pop(field)
    with pytest.raises(AssertionError, match="defensive_record_mismatch"):
        validate_index_scope(defensive_record(manifest), manifest["execution_sequence"]["active_target"])


# IRG: receipt-pinned conditional development/testing; no live or production grant.
INDEX_RESUME_EXECUTION_SCOPE = json.loads(r'''{
  "activities": [
    "DEVELOP_REGISTERED_INDEX",
    "TEST_REGISTERED_INDEX"
  ],
  "implementation_paths": [
    "backend/repository.py",
    "tests/test_repository_intelligence.py"
  ],
  "database_scope": "DISPOSABLE_TEMPORARY_DATABASES_ONLY",
  "data_scope": "SYNTHETIC_DATA_ONLY",
  "live_database_authorized": false,
  "owner_database_authorized": false,
  "production_placement_accepted": false,
  "deployment_authorized": false,
  "application_pr_merge_authorized": false,
  "startup_criteria_status": "UNKNOWN_NOT_APPROVED",
  "maintenance_recovery_acceptance": "UNKNOWN_NOT_APPROVED",
  "query_and_proof_semantics": "UNCHANGED"
}''')
INDEX_RESUME_DECISION = json.loads(r'''{
  "id": "DECISION-FC20-12-F01A-INDEX-CONDITIONAL-RESUME-2026-10-11",
  "record_url": "https://github.com/alphasigma13579-lang/ASIE/pull/199#issuecomment-6111816253",
  "recorded_at": "2026-10-11T17:37:41Z",
  "effect": "F01A_DEFENSIVE_RESUME_ONLY",
  "condition": "REVIEWED_GOVERNANCE_TRANSITION_MERGED_AFTER_SEPARATE_OWNER_MERGE_APPROVAL",
  "subject": {
    "baseline_commit_sha": "37b96ec504d60f62bcdb5f4e69e0e5a0d8082f34",
    "baseline_manifest_blob_sha": "386687c230db26e46ad831bbaeaeddddecfae795",
    "checkpoint": {
      "type": "STOP_CHECKPOINT",
      "recorded_at": "2026-10-11T14:50:33Z",
      "baseline_commit_sha": "83afd28398c0cef9821e08c8db1162d6ec2fdfc4",
      "baseline_manifest_blob_sha": "1cfbaf1940bfc0a1e7c276fde4a9d0a8cea05a70",
      "application_head_sha": "7df4ea3c6dfbcfb70cc219ef59622b7387052dc4",
      "reason": "AUDIT_ORIGIN_INDEX_SCHEMA_OPERATION_OUTSIDE_REGISTERED_SCOPE",
      "evidence": {
        "url": "https://github.com/alphasigma13579-lang/ASIE/blob/33ac90a47966afda4917f34162f11f5826eab565/ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/docs/FC20-12-F01A-AUDIT-ORIGIN-INDEX-SCOPE-PROPOSAL-2026-10-11.md",
        "commit_sha": "33ac90a47966afda4917f34162f11f5826eab565",
        "blob_sha": "9be7964b01ebd393724dc2adf6a559a8a1eddd64"
      },
      "resume_requirement": "NEW_OWNER_DECISION_BOUND_TO_INDEX_OPERATION_AND_REVIEWED_EXACT_HEAD_GOVERNANCE_TRANSITION"
    },
    "scope_extension": {
      "type": "SCOPE_EXTENSION",
      "recorded_at": "2026-10-11T14:50:33Z",
      "baseline_commit_sha": "83afd28398c0cef9821e08c8db1162d6ec2fdfc4",
      "baseline_manifest_blob_sha": "1cfbaf1940bfc0a1e7c276fde4a9d0a8cea05a70",
      "application_head_sha": "7df4ea3c6dfbcfb70cc219ef59622b7387052dc4",
      "added_paths": [],
      "added_schema_operations": [
        {
          "operation": "CREATE_INDEX_IF_NOT_EXISTS",
          "index_name": "idx_security_audit_origin_proof",
          "table": "security_audit_events",
          "columns": [
            "action",
            "target_type",
            "target_id",
            "organization_id"
          ],
          "unique": false,
          "implementation_path": "backend/repository.py",
          "test_path": "tests/test_repository_intelligence.py"
        }
      ],
      "scope_addendum": {
        "url": "https://github.com/alphasigma13579-lang/ASIE/blob/33ac90a47966afda4917f34162f11f5826eab565/ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/docs/FC20-12-F01A-AUDIT-ORIGIN-INDEX-SCOPE-PROPOSAL-2026-10-11.md",
        "commit_sha": "33ac90a47966afda4917f34162f11f5826eab565",
        "blob_sha": "9be7964b01ebd393724dc2adf6a559a8a1eddd64"
      },
      "owner_scope_decision": {
        "id": "DECISION-FC20-12-F01A-INDEX-SCOPE-REGISTRATION-PREPARATION-2026-10-11",
        "record_url": "https://github.com/alphasigma13579-lang/ASIE/pull/197#issuecomment-6110969163",
        "recorded_at": "2026-10-11T14:44:04Z",
        "effect": "PREPARE_GOVERNANCE_PR_ONLY_NO_MERGE_NO_RESUME",
        "subject": {
          "baseline_commit_sha": "83afd28398c0cef9821e08c8db1162d6ec2fdfc4",
          "baseline_manifest_blob_sha": "1cfbaf1940bfc0a1e7c276fde4a9d0a8cea05a70",
          "application_head_sha": "7df4ea3c6dfbcfb70cc219ef59622b7387052dc4",
          "allowed_paths": [
            "backend/asie_local_api.py",
            "backend/repository.py",
            "backend/intelligence_prerun_service.py",
            "tests/test_repository_intelligence.py",
            "tests/test_intelligence_prerun_service.py",
            "tests/test_intelligence_context_ingress_api.py",
            "docs/FC20-12-F01-TRUSTED-CONTEXT-INGRESS-REPAIR-PLAN-2026-10-01.md",
            "tests/test_live_location_api.py",
            "tests/test_intelligence_consumption.py"
          ],
          "allowed_schema_operations": [
            {
              "operation": "CREATE_INDEX_IF_NOT_EXISTS",
              "index_name": "idx_security_audit_origin_proof",
              "table": "security_audit_events",
              "columns": [
                "action",
                "target_type",
                "target_id",
                "organization_id"
              ],
              "unique": false,
              "implementation_path": "backend/repository.py",
              "test_path": "tests/test_repository_intelligence.py"
            }
          ]
        },
        "proposal_commit_sha": "33ac90a47966afda4917f34162f11f5826eab565",
        "proposal_blob_sha": "9be7964b01ebd393724dc2adf6a559a8a1eddd64"
      },
      "effect": "SCOPE_EXTENSION_ONLY_NO_RESUME"
    },
    "application_head_sha": "7df4ea3c6dfbcfb70cc219ef59622b7387052dc4",
    "allowed_paths": [
      "backend/asie_local_api.py",
      "backend/repository.py",
      "backend/intelligence_prerun_service.py",
      "tests/test_repository_intelligence.py",
      "tests/test_intelligence_prerun_service.py",
      "tests/test_intelligence_context_ingress_api.py",
      "docs/FC20-12-F01-TRUSTED-CONTEXT-INGRESS-REPAIR-PLAN-2026-10-01.md",
      "tests/test_live_location_api.py",
      "tests/test_intelligence_consumption.py"
    ],
    "allowed_schema_operations": [
      {
        "operation": "CREATE_INDEX_IF_NOT_EXISTS",
        "index_name": "idx_security_audit_origin_proof",
        "table": "security_audit_events",
        "columns": [
          "action",
          "target_type",
          "target_id",
          "organization_id"
        ],
        "unique": false,
        "implementation_path": "backend/repository.py",
        "test_path": "tests/test_repository_intelligence.py"
      }
    ],
    "execution_scope": {
      "activities": [
        "DEVELOP_REGISTERED_INDEX",
        "TEST_REGISTERED_INDEX"
      ],
      "implementation_paths": [
        "backend/repository.py",
        "tests/test_repository_intelligence.py"
      ],
      "database_scope": "DISPOSABLE_TEMPORARY_DATABASES_ONLY",
      "data_scope": "SYNTHETIC_DATA_ONLY",
      "live_database_authorized": false,
      "owner_database_authorized": false,
      "production_placement_accepted": false,
      "deployment_authorized": false,
      "application_pr_merge_authorized": false,
      "startup_criteria_status": "UNKNOWN_NOT_APPROVED",
      "maintenance_recovery_acceptance": "UNKNOWN_NOT_APPROVED",
      "query_and_proof_semantics": "UNCHANGED"
    }
  },
  "proposal_commit_sha": "369832d4c296cacf114c1181b2a65b06a49fde49",
  "proposal_blob_sha": "0a87463111c78263db11ac4d3bf103c16e47f261"
}''')
INDEX_RESUME_EVENT = json.loads(r'''{
  "type": "RESUME",
  "recorded_at": "2026-10-11T17:43:21Z",
  "baseline_commit_sha": "37b96ec504d60f62bcdb5f4e69e0e5a0d8082f34",
  "baseline_manifest_blob_sha": "386687c230db26e46ad831bbaeaeddddecfae795",
  "checkpoint": {
    "type": "STOP_CHECKPOINT",
    "recorded_at": "2026-10-11T14:50:33Z",
    "baseline_commit_sha": "83afd28398c0cef9821e08c8db1162d6ec2fdfc4",
    "baseline_manifest_blob_sha": "1cfbaf1940bfc0a1e7c276fde4a9d0a8cea05a70",
    "application_head_sha": "7df4ea3c6dfbcfb70cc219ef59622b7387052dc4",
    "reason": "AUDIT_ORIGIN_INDEX_SCHEMA_OPERATION_OUTSIDE_REGISTERED_SCOPE",
    "evidence": {
      "url": "https://github.com/alphasigma13579-lang/ASIE/blob/33ac90a47966afda4917f34162f11f5826eab565/ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/docs/FC20-12-F01A-AUDIT-ORIGIN-INDEX-SCOPE-PROPOSAL-2026-10-11.md",
      "commit_sha": "33ac90a47966afda4917f34162f11f5826eab565",
      "blob_sha": "9be7964b01ebd393724dc2adf6a559a8a1eddd64"
    },
    "resume_requirement": "NEW_OWNER_DECISION_BOUND_TO_INDEX_OPERATION_AND_REVIEWED_EXACT_HEAD_GOVERNANCE_TRANSITION"
  },
  "scope_extension": {
    "type": "SCOPE_EXTENSION",
    "recorded_at": "2026-10-11T14:50:33Z",
    "baseline_commit_sha": "83afd28398c0cef9821e08c8db1162d6ec2fdfc4",
    "baseline_manifest_blob_sha": "1cfbaf1940bfc0a1e7c276fde4a9d0a8cea05a70",
    "application_head_sha": "7df4ea3c6dfbcfb70cc219ef59622b7387052dc4",
    "added_paths": [],
    "added_schema_operations": [
      {
        "operation": "CREATE_INDEX_IF_NOT_EXISTS",
        "index_name": "idx_security_audit_origin_proof",
        "table": "security_audit_events",
        "columns": [
          "action",
          "target_type",
          "target_id",
          "organization_id"
        ],
        "unique": false,
        "implementation_path": "backend/repository.py",
        "test_path": "tests/test_repository_intelligence.py"
      }
    ],
    "scope_addendum": {
      "url": "https://github.com/alphasigma13579-lang/ASIE/blob/33ac90a47966afda4917f34162f11f5826eab565/ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/docs/FC20-12-F01A-AUDIT-ORIGIN-INDEX-SCOPE-PROPOSAL-2026-10-11.md",
      "commit_sha": "33ac90a47966afda4917f34162f11f5826eab565",
      "blob_sha": "9be7964b01ebd393724dc2adf6a559a8a1eddd64"
    },
    "owner_scope_decision": {
      "id": "DECISION-FC20-12-F01A-INDEX-SCOPE-REGISTRATION-PREPARATION-2026-10-11",
      "record_url": "https://github.com/alphasigma13579-lang/ASIE/pull/197#issuecomment-6110969163",
      "recorded_at": "2026-10-11T14:44:04Z",
      "effect": "PREPARE_GOVERNANCE_PR_ONLY_NO_MERGE_NO_RESUME",
      "subject": {
        "baseline_commit_sha": "83afd28398c0cef9821e08c8db1162d6ec2fdfc4",
        "baseline_manifest_blob_sha": "1cfbaf1940bfc0a1e7c276fde4a9d0a8cea05a70",
        "application_head_sha": "7df4ea3c6dfbcfb70cc219ef59622b7387052dc4",
        "allowed_paths": [
          "backend/asie_local_api.py",
          "backend/repository.py",
          "backend/intelligence_prerun_service.py",
          "tests/test_repository_intelligence.py",
          "tests/test_intelligence_prerun_service.py",
          "tests/test_intelligence_context_ingress_api.py",
          "docs/FC20-12-F01-TRUSTED-CONTEXT-INGRESS-REPAIR-PLAN-2026-10-01.md",
          "tests/test_live_location_api.py",
          "tests/test_intelligence_consumption.py"
        ],
        "allowed_schema_operations": [
          {
            "operation": "CREATE_INDEX_IF_NOT_EXISTS",
            "index_name": "idx_security_audit_origin_proof",
            "table": "security_audit_events",
            "columns": [
              "action",
              "target_type",
              "target_id",
              "organization_id"
            ],
            "unique": false,
            "implementation_path": "backend/repository.py",
            "test_path": "tests/test_repository_intelligence.py"
          }
        ]
      },
      "proposal_commit_sha": "33ac90a47966afda4917f34162f11f5826eab565",
      "proposal_blob_sha": "9be7964b01ebd393724dc2adf6a559a8a1eddd64"
    },
    "effect": "SCOPE_EXTENSION_ONLY_NO_RESUME"
  },
  "owner_resume_decision": {
    "id": "DECISION-FC20-12-F01A-INDEX-CONDITIONAL-RESUME-2026-10-11",
    "record_url": "https://github.com/alphasigma13579-lang/ASIE/pull/199#issuecomment-6111816253",
    "recorded_at": "2026-10-11T17:37:41Z",
    "effect": "F01A_DEFENSIVE_RESUME_ONLY",
    "condition": "REVIEWED_GOVERNANCE_TRANSITION_MERGED_AFTER_SEPARATE_OWNER_MERGE_APPROVAL",
    "subject": {
      "baseline_commit_sha": "37b96ec504d60f62bcdb5f4e69e0e5a0d8082f34",
      "baseline_manifest_blob_sha": "386687c230db26e46ad831bbaeaeddddecfae795",
      "checkpoint": {
        "type": "STOP_CHECKPOINT",
        "recorded_at": "2026-10-11T14:50:33Z",
        "baseline_commit_sha": "83afd28398c0cef9821e08c8db1162d6ec2fdfc4",
        "baseline_manifest_blob_sha": "1cfbaf1940bfc0a1e7c276fde4a9d0a8cea05a70",
        "application_head_sha": "7df4ea3c6dfbcfb70cc219ef59622b7387052dc4",
        "reason": "AUDIT_ORIGIN_INDEX_SCHEMA_OPERATION_OUTSIDE_REGISTERED_SCOPE",
        "evidence": {
          "url": "https://github.com/alphasigma13579-lang/ASIE/blob/33ac90a47966afda4917f34162f11f5826eab565/ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/docs/FC20-12-F01A-AUDIT-ORIGIN-INDEX-SCOPE-PROPOSAL-2026-10-11.md",
          "commit_sha": "33ac90a47966afda4917f34162f11f5826eab565",
          "blob_sha": "9be7964b01ebd393724dc2adf6a559a8a1eddd64"
        },
        "resume_requirement": "NEW_OWNER_DECISION_BOUND_TO_INDEX_OPERATION_AND_REVIEWED_EXACT_HEAD_GOVERNANCE_TRANSITION"
      },
      "scope_extension": {
        "type": "SCOPE_EXTENSION",
        "recorded_at": "2026-10-11T14:50:33Z",
        "baseline_commit_sha": "83afd28398c0cef9821e08c8db1162d6ec2fdfc4",
        "baseline_manifest_blob_sha": "1cfbaf1940bfc0a1e7c276fde4a9d0a8cea05a70",
        "application_head_sha": "7df4ea3c6dfbcfb70cc219ef59622b7387052dc4",
        "added_paths": [],
        "added_schema_operations": [
          {
            "operation": "CREATE_INDEX_IF_NOT_EXISTS",
            "index_name": "idx_security_audit_origin_proof",
            "table": "security_audit_events",
            "columns": [
              "action",
              "target_type",
              "target_id",
              "organization_id"
            ],
            "unique": false,
            "implementation_path": "backend/repository.py",
            "test_path": "tests/test_repository_intelligence.py"
          }
        ],
        "scope_addendum": {
          "url": "https://github.com/alphasigma13579-lang/ASIE/blob/33ac90a47966afda4917f34162f11f5826eab565/ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/docs/FC20-12-F01A-AUDIT-ORIGIN-INDEX-SCOPE-PROPOSAL-2026-10-11.md",
          "commit_sha": "33ac90a47966afda4917f34162f11f5826eab565",
          "blob_sha": "9be7964b01ebd393724dc2adf6a559a8a1eddd64"
        },
        "owner_scope_decision": {
          "id": "DECISION-FC20-12-F01A-INDEX-SCOPE-REGISTRATION-PREPARATION-2026-10-11",
          "record_url": "https://github.com/alphasigma13579-lang/ASIE/pull/197#issuecomment-6110969163",
          "recorded_at": "2026-10-11T14:44:04Z",
          "effect": "PREPARE_GOVERNANCE_PR_ONLY_NO_MERGE_NO_RESUME",
          "subject": {
            "baseline_commit_sha": "83afd28398c0cef9821e08c8db1162d6ec2fdfc4",
            "baseline_manifest_blob_sha": "1cfbaf1940bfc0a1e7c276fde4a9d0a8cea05a70",
            "application_head_sha": "7df4ea3c6dfbcfb70cc219ef59622b7387052dc4",
            "allowed_paths": [
              "backend/asie_local_api.py",
              "backend/repository.py",
              "backend/intelligence_prerun_service.py",
              "tests/test_repository_intelligence.py",
              "tests/test_intelligence_prerun_service.py",
              "tests/test_intelligence_context_ingress_api.py",
              "docs/FC20-12-F01-TRUSTED-CONTEXT-INGRESS-REPAIR-PLAN-2026-10-01.md",
              "tests/test_live_location_api.py",
              "tests/test_intelligence_consumption.py"
            ],
            "allowed_schema_operations": [
              {
                "operation": "CREATE_INDEX_IF_NOT_EXISTS",
                "index_name": "idx_security_audit_origin_proof",
                "table": "security_audit_events",
                "columns": [
                  "action",
                  "target_type",
                  "target_id",
                  "organization_id"
                ],
                "unique": false,
                "implementation_path": "backend/repository.py",
                "test_path": "tests/test_repository_intelligence.py"
              }
            ]
          },
          "proposal_commit_sha": "33ac90a47966afda4917f34162f11f5826eab565",
          "proposal_blob_sha": "9be7964b01ebd393724dc2adf6a559a8a1eddd64"
        },
        "effect": "SCOPE_EXTENSION_ONLY_NO_RESUME"
      },
      "application_head_sha": "7df4ea3c6dfbcfb70cc219ef59622b7387052dc4",
      "allowed_paths": [
        "backend/asie_local_api.py",
        "backend/repository.py",
        "backend/intelligence_prerun_service.py",
        "tests/test_repository_intelligence.py",
        "tests/test_intelligence_prerun_service.py",
        "tests/test_intelligence_context_ingress_api.py",
        "docs/FC20-12-F01-TRUSTED-CONTEXT-INGRESS-REPAIR-PLAN-2026-10-01.md",
        "tests/test_live_location_api.py",
        "tests/test_intelligence_consumption.py"
      ],
      "allowed_schema_operations": [
        {
          "operation": "CREATE_INDEX_IF_NOT_EXISTS",
          "index_name": "idx_security_audit_origin_proof",
          "table": "security_audit_events",
          "columns": [
            "action",
            "target_type",
            "target_id",
            "organization_id"
          ],
          "unique": false,
          "implementation_path": "backend/repository.py",
          "test_path": "tests/test_repository_intelligence.py"
        }
      ],
      "execution_scope": {
        "activities": [
          "DEVELOP_REGISTERED_INDEX",
          "TEST_REGISTERED_INDEX"
        ],
        "implementation_paths": [
          "backend/repository.py",
          "tests/test_repository_intelligence.py"
        ],
        "database_scope": "DISPOSABLE_TEMPORARY_DATABASES_ONLY",
        "data_scope": "SYNTHETIC_DATA_ONLY",
        "live_database_authorized": false,
        "owner_database_authorized": false,
        "production_placement_accepted": false,
        "deployment_authorized": false,
        "application_pr_merge_authorized": false,
        "startup_criteria_status": "UNKNOWN_NOT_APPROVED",
        "maintenance_recovery_acceptance": "UNKNOWN_NOT_APPROVED",
        "query_and_proof_semantics": "UNCHANGED"
      }
    },
    "proposal_commit_sha": "369832d4c296cacf114c1181b2a65b06a49fde49",
    "proposal_blob_sha": "0a87463111c78263db11ac4d3bf103c16e47f261"
  },
  "effect": "F01A_DEFENSIVE_RESUME_ONLY"
}''')
INDEX_RESUME_VIEW_PREFIX_BLOBS = json.loads(r'''{
  "docs/ASIE-BETA-EXECUTION-MASTER-PLAN-2026-09-09.md": "6ad9850c3407c5a90422ac4fcb1dd2b1f5f88b3e",
  "docs/FC20-12-F01A-DEFENSIVE-ENABLING-REGISTRATION-PROPOSAL-2026-10-01.md": "6f14a56dfc1bfa329f793bfa012ecd1dff948117",
  "docs/FC20-12-F01A-APPROVAL-CONSUMPTION-SCOPE-REGISTRATION-2026-10-09.md": "391940ecbb9b6be83bd0f9e1570bdeecd3a8d4b7",
  "docs/FOUNDATION-COMPLETE-20-CORE-INTELLIGENCE-COMPLETION-PROGRAM-2026-07-29.md": "be62522331e6ee4517bd43e49ac439451dfeeb3a",
  "docs/EKB/FOUNDATION-COMPLETE-20-PACKAGE-INDEX.md": "a5e4f95f86cc0f2995097b3cbde81a9a1907c036"
}''')
INDEX_RESUME_VIEW_SHA256 = json.loads(r'''{
  "docs/ASIE-BETA-EXECUTION-MASTER-PLAN-2026-09-09.md": "4b7c66ad2500081ed0cd10f1fcddea4cd093245950d4df885fe4662150996633",
  "docs/FC20-12-F01A-DEFENSIVE-ENABLING-REGISTRATION-PROPOSAL-2026-10-01.md": "a18102e44f18cac3eac3487a2a367934300b255453f8cffe9fa167cdcb50c70b",
  "docs/FC20-12-F01A-APPROVAL-CONSUMPTION-SCOPE-REGISTRATION-2026-10-09.md": "7d396001509f6c77400ef60597dadaf43c5e9095963e04459db4e39d46f6d935",
  "docs/FOUNDATION-COMPLETE-20-CORE-INTELLIGENCE-COMPLETION-PROGRAM-2026-07-29.md": "2a2cd62bb16184f0384029b68c2d7ab04c031e2a2550f059254b6230b35207c5",
  "docs/EKB/FOUNDATION-COMPLETE-20-PACKAGE-INDEX.md": "abe2e2f6ea207761886311f08591be0d042936e5a1b6113a1d3c7872ec2e039d"
}''')
INDEX_RESUME_VIEW_MARKER = '<!-- F01A-INDEX-CONDITIONAL-RESUME-2026-10-11 -->'
INDEX_RESUME_RECORD = deepcopy(INDEX_SCOPE_RECORD)
INDEX_RESUME_RECORD["execution_authorized"] = True
INDEX_RESUME_RECORD["events"].append(deepcopy(INDEX_RESUME_EVENT))


def validate_index_resume(record: dict, active_target: object) -> None:
    """IRG-01/03/04/08: true is bound to exact synthetic, temporary-only scope."""
    assert isinstance(record, dict), "invalid_defensive_record"
    assert set(record) == set(INDEX_RESUME_RECORD), "defensive_fields"
    assert record == INDEX_RESUME_RECORD, "defensive_record_mismatch"
    assert json.dumps(record, sort_keys=True) == json.dumps(INDEX_RESUME_RECORD, sort_keys=True), "index_resume_literal_types"
    assert record["execution_authorized"] is True, "index_resume_literal_flag"
    assert all(record[key] is False for key in (
        "network_authorized", "provider_activation_authorized", "deployment_authorized",
    )), "defensive_external_effect"
    assert active_target == DEFENSIVE_START_TARGET, "index_resume_slot"
    decision = record["events"][9]["owner_resume_decision"]
    assert decision == INDEX_RESUME_DECISION, "index_resume_decision_mismatch"
    assert decision["subject"]["execution_scope"] == INDEX_RESUME_EXECUTION_SCOPE, "index_resume_execution_scope"
    assert all(decision["subject"]["execution_scope"][key] is False for key in (
        "live_database_authorized", "owner_database_authorized", "production_placement_accepted",
        "deployment_authorized", "application_pr_merge_authorized",
    )), "index_resume_forbidden_effect"
    for operations in (record["allowed_schema_operations"], decision["subject"]["allowed_schema_operations"]):
        assert operations == [INDEX_OPERATION], "index_resume_operation"
        assert operations[0]["unique"] is False, "index_resume_unique_literal"
    assert re.fullmatch(
        r"https://github\.com/alphasigma13579-lang/ASIE/pull/199#issuecomment-[0-9]+",
        decision["record_url"],
    ), "index_resume_receipt"


def validate_index_resume_baseline(manifest: dict) -> dict:
    """IRG-05: undo only the tenth event/flag and pin the entire stopped manifest."""
    restored = deepcopy(manifest)
    record = defensive_record(restored)
    validate_index_resume(record, restored["execution_sequence"]["active_target"])
    assert record["events"].pop() == INDEX_RESUME_EVENT
    record["execution_authorized"] = False
    validate_index_scope(record, restored["execution_sequence"]["active_target"])
    source = (json.dumps(restored, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    assert git_blob_sha(source) == "386687c230db26e46ad831bbaeaeddddecfae795", "index_resume_baseline_mismatch"
    return restored


def historical_index_scope_manifest() -> dict:
    """Verified nine-event fixture only; not a current authority fallback."""
    return validate_index_resume_baseline(historical_index_resume_manifest())


def index_resume_historical_view(source_bytes: bytes, relative_path: str) -> bytes:
    """IRG-06: seal complete history and one path-bound terminal resume section."""
    assert isinstance(source_bytes, bytes), "index_resume_view_source_bytes"
    assert relative_path in INDEX_RESUME_VIEW_SHA256, "index_resume_view_path"
    marker = INDEX_RESUME_VIEW_MARKER.encode("utf-8")
    separator = b"\n" + marker + b"\n"
    assert source_bytes.count(marker) == 1, "index_resume_view_marker"
    assert source_bytes.count(separator) == 1, "index_resume_view_boundary"
    prefix, section = source_bytes.split(separator, 1)
    assert git_blob_sha(prefix) == INDEX_RESUME_VIEW_PREFIX_BLOBS[relative_path], "index_resume_view_prefix_changed"
    assert hashlib.sha256(marker + b"\n" + section).hexdigest() == INDEX_RESUME_VIEW_SHA256[relative_path], "index_resume_view_projection_changed"
    index_scope_historical_view(prefix, relative_path)
    return prefix


def test_index_resume_has_one_delta_and_full_inverse_chain() -> None:
    """IRG-01/02/05/08: preserve all nine events, operation, paths and old oracles."""
    manifest = historical_index_resume_manifest()
    validate_index_resume(defensive_record(manifest), manifest["execution_sequence"]["active_target"])
    record = defensive_record(manifest)
    assert record == INDEX_RESUME_RECORD
    assert record["events"][:9] == INDEX_SCOPE_RECORD["events"]
    assert len(record["events"]) == 10
    event = record["events"][9]
    assert event["checkpoint"] == record["events"][7]
    assert event["scope_extension"] == record["events"][8]
    assert event["owner_resume_decision"]["subject"]["checkpoint"] == record["events"][7]
    assert event["owner_resume_decision"]["subject"]["scope_extension"] == record["events"][8]
    assert record["allowed_paths"] == INDEX_SCOPE_RECORD["allowed_paths"]
    assert len(record["allowed_paths"]) == 9
    assert record["allowed_schema_operations"] == [INDEX_OPERATION]
    assert manifest["execution_sequence"]["held_packages"] == HELD_PACKAGES
    assert active_execution_targets(manifest["packages"], {"FC20-05"}) == ["FC20-12/f01a_defensive_ingress"]
    stopped = validate_index_resume_baseline(manifest)
    previous_resume = validate_index_scope_baseline(stopped)
    consumption_scope = validate_consumption_resume_baseline(previous_resume)
    old_resume = validate_consumption_scope_baseline(consumption_scope)
    validate_scope_extension_baseline(validate_resume_baseline(old_resume))


@pytest.mark.parametrize("field", tuple(INDEX_RESUME_EVENT))
def test_index_resume_requires_all_event_fields(field: str) -> None:
    """IRG-03: no partial evidence can become a new resume decision."""
    manifest = historical_index_resume_manifest()
    defensive_record(manifest)["events"][9].pop(field)
    with pytest.raises(AssertionError, match="defensive_record_mismatch"):
        validate_index_resume(defensive_record(manifest), manifest["execution_sequence"]["active_target"])


def index_resume_leaf_paths(value: object, prefix: tuple = ()) -> list[tuple]:
    """Enumerate nested mapping/list leaves, including each copied operation."""
    if isinstance(value, dict) and value:
        return [path for key, child in value.items() for path in index_resume_leaf_paths(child, (*prefix, key))]
    if isinstance(value, list) and value:
        return [path for index, child in enumerate(value) for path in index_resume_leaf_paths(child, (*prefix, index))]
    return [prefix]


@pytest.mark.parametrize("path", index_resume_leaf_paths(INDEX_RESUME_EVENT))
def test_index_resume_pins_every_evidence_leaf(path: list) -> None:
    """IRG-03: independently pin receipt, timestamps, baselines and nested copies."""
    manifest = historical_index_resume_manifest()
    target = defensive_record(manifest)["events"][9]
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = "[unreviewed]"
    with pytest.raises(AssertionError, match="defensive_record_mismatch"):
        validate_index_resume(defensive_record(manifest), manifest["execution_sequence"]["active_target"])


@pytest.mark.parametrize("field", tuple(INDEX_RESUME_EXECUTION_SCOPE))
@pytest.mark.parametrize("mutation", ("missing", "changed"))
def test_index_resume_requires_closed_limited_execution_scope(field: str, mutation: str) -> None:
    """IRG-03/08: remove or broaden any restriction and admission fails."""
    manifest = historical_index_resume_manifest()
    scope = defensive_record(manifest)["events"][9]["owner_resume_decision"]["subject"]["execution_scope"]
    if mutation == "missing":
        scope.pop(field)
    else:
        scope[field] = True if field.endswith(("authorized", "accepted")) else "UNRESTRICTED"
    with pytest.raises(AssertionError, match="defensive_record_mismatch"):
        validate_index_resume(defensive_record(manifest), manifest["execution_sequence"]["active_target"])


@pytest.mark.parametrize("field", ("live_database_authorized", "owner_database_authorized", "production_placement_accepted", "deployment_authorized", "application_pr_merge_authorized"))
@pytest.mark.parametrize("value", (0, 1, "false", None))
def test_index_resume_scope_requires_literal_booleans(field: str, value: object) -> None:
    """IRG-03/08: false-like metadata never substitutes for explicit prohibitions."""
    manifest = historical_index_resume_manifest()
    defensive_record(manifest)["events"][9]["owner_resume_decision"]["subject"]["execution_scope"][field] = value
    with pytest.raises(AssertionError):
        validate_index_resume(defensive_record(manifest), manifest["execution_sequence"]["active_target"])


@pytest.mark.parametrize("mutation", ("unknown", "extra_activity", "extra_path", "path_order", "real_data", "live_database", "startup_approved", "recovery_approved", "changed_query", "empty_scope"))
def test_index_resume_never_interprets_true_as_general_execution(mutation: str) -> None:
    """IRG-08: an otherwise exact true record cannot authorize broader work."""
    manifest = historical_index_resume_manifest()
    subject = defensive_record(manifest)["events"][9]["owner_resume_decision"]["subject"]
    scope = subject["execution_scope"]
    if mutation == "unknown":
        scope["trusted_override"] = True
    elif mutation == "extra_activity":
        scope["activities"].append("DEPLOY")
    elif mutation == "extra_path":
        scope["implementation_paths"].append("backend/asie_local_api.py")
    elif mutation == "path_order":
        scope["implementation_paths"].reverse()
    elif mutation == "real_data":
        scope["data_scope"] = "OWNER_DATA"
    elif mutation == "live_database":
        scope["database_scope"] = "OWNER_DATABASE"
    elif mutation == "startup_approved":
        scope["startup_criteria_status"] = "APPROVED"
    elif mutation == "recovery_approved":
        scope["maintenance_recovery_acceptance"] = "APPROVED"
    elif mutation == "changed_query":
        scope["query_and_proof_semantics"] = "REPLACED"
    else:
        subject["execution_scope"] = {}
    with pytest.raises(AssertionError, match="defensive_record_mismatch"):
        validate_index_resume(defensive_record(manifest), manifest["execution_sequence"]["active_target"])


@pytest.mark.parametrize("mutation", ("old_resume", "scope_decision", "preparation_effect", "missing_condition", "new_branch_baseline", "old_checkpoint_baseline", "unknown_decision", "unknown_subject", "duplicate_resume"))
def test_index_resume_rejects_reused_or_ambiguous_authority(mutation: str) -> None:
    """IRG-03/07: design, publication, scope or merge approvals are not this decision."""
    manifest = historical_index_resume_manifest()
    record = defensive_record(manifest)
    event = record["events"][9]
    if mutation == "old_resume":
        event["owner_resume_decision"] = deepcopy(CONSUMPTION_RESUME_DECISION)
    elif mutation == "scope_decision":
        event["owner_resume_decision"] = deepcopy(INDEX_SCOPE_DECISION)
    elif mutation == "preparation_effect":
        event["owner_resume_decision"]["effect"] = "PREPARE_GOVERNANCE_PR_ONLY_NO_MERGE_NO_RESUME"
    elif mutation == "missing_condition":
        event["owner_resume_decision"].pop("condition")
    elif mutation == "new_branch_baseline":
        event["baseline_commit_sha"] = "63b18a192e8eac3c66ad5440a667e6d1d9959d10"
    elif mutation == "old_checkpoint_baseline":
        event["baseline_commit_sha"] = INDEX_STOP_EVENT["baseline_commit_sha"]
        event["baseline_manifest_blob_sha"] = INDEX_STOP_EVENT["baseline_manifest_blob_sha"]
    elif mutation == "unknown_decision":
        event["owner_resume_decision"]["approved"] = True
    elif mutation == "unknown_subject":
        event["owner_resume_decision"]["subject"]["override"] = True
    else:
        record["events"].append(deepcopy(event))
    with pytest.raises(AssertionError, match="defensive_record_mismatch"):
        validate_index_resume(defensive_record(manifest), manifest["execution_sequence"]["active_target"])


@pytest.mark.parametrize("index", range(10))
@pytest.mark.parametrize("mutation", ("delete", "duplicate", "change", "reorder"))
def test_index_resume_preserves_each_event(index: int, mutation: str) -> None:
    """IRG-02: every historical or current event is required in its exact position."""
    manifest = historical_index_resume_manifest()
    events = defensive_record(manifest)["events"]
    if mutation == "delete":
        events.pop(index)
    elif mutation == "duplicate":
        events.insert(index, deepcopy(events[index]))
    elif mutation == "change":
        events[index]["type"] = "OVERRIDE"
    else:
        other = (index + 1) % len(events)
        events[index], events[other] = events[other], events[index]
    with pytest.raises(AssertionError, match="defensive_record_mismatch"):
        validate_index_resume(defensive_record(manifest), manifest["execution_sequence"]["active_target"])


@pytest.mark.parametrize("field,value", (("execution_authorized", False), ("execution_authorized", 1), ("execution_authorized", "true"), ("state", "DELIVERED"), ("delivery_evidence", {"passed": True}), ("closure_effect", "COMPLETE"), ("environment", "LIVE"), ("network_authorized", 0), ("network_authorized", True), ("provider_activation_authorized", True), ("deployment_authorized", True)))
def test_index_resume_requires_literal_flags_and_no_terminal_effects(field: str, value: object) -> None:
    """IRG-04/08: no implicit Boolean authority, completion or external activation."""
    manifest = historical_index_resume_manifest()
    defensive_record(manifest)[field] = value
    with pytest.raises(AssertionError):
        validate_index_resume(defensive_record(manifest), manifest["execution_sequence"]["active_target"])


@pytest.mark.parametrize("record", (DEFENSIVE_REGISTRATION, DEFENSIVE_START_RECORD, DEFENSIVE_STOP_RECORD, DEFENSIVE_SCOPE_EXTENSION_RECORD, DEFENSIVE_RESUME_RECORD, CONSUMPTION_SCOPE_RECORD, CONSUMPTION_RESUME_RECORD, INDEX_SCOPE_RECORD, lifecycle_fixture()[0]))
def test_index_resume_never_admits_any_historical_or_fixture_state(record: dict) -> None:
    """IRG-07: only the new exact conditional decision is current authority."""
    with pytest.raises(AssertionError):
        validate_index_resume(deepcopy(record), DEFENSIVE_START_TARGET)


@pytest.mark.parametrize("mutation", ("root", "rule", "package", "dependency", "hold", "limit", "frozen", "routing", "release"))
def test_index_resume_full_inverse_rejects_every_unrelated_delta(mutation: str) -> None:
    """IRG-05: seal the full manifest, not only a convenient authority subset."""
    manifest = historical_index_resume_manifest()
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
    elif mutation == "limit":
        manifest["execution_sequence"]["max_active_executions"] = 2
    elif mutation == "frozen":
        manifest["frozen_files"].append("backend/unknown.py")
    elif mutation == "routing":
        packages["FC20-12"]["execution_slices"][0]["required_entry_controls"]["single_active_execution"]["status"] = "PASS"
    else:
        manifest["public_release_authorized"] = True
    with pytest.raises(AssertionError, match="index_resume_baseline_mismatch"):
        validate_index_resume_baseline(manifest)


@pytest.mark.parametrize("slot", (None, {}, {"kind": "package", "package_id": "FC20-05"}))
def test_index_resume_retains_single_counted_slot(slot: object) -> None:
    """IRG-04: resume retains the same slot and cannot hand it to held work."""
    manifest = historical_index_resume_manifest()
    manifest["execution_sequence"]["active_target"] = slot
    with pytest.raises(AssertionError):
        validate_index_resume(defensive_record(manifest), manifest["execution_sequence"]["active_target"])


@pytest.mark.parametrize("relative_path", tuple(INDEX_RESUME_VIEW_SHA256))
def test_index_resume_preserves_all_historical_projection_seals(relative_path: str) -> None:
    """IRG-06: full prior documents and every old oracle stay independently sealed."""
    source = review_identity_historical_view(review_identity_resume_historical_view(key_binding_historical_view(key_binding_resume_historical_view(recovery_scope_historical_view(recovery_resume_historical_view(dataset_scope_historical_view(dataset_resume_historical_view(overlay_scope_historical_view(overlay_resume_historical_view(ci_scope_historical_view(ci_resume_historical_view(ci_amend_historical_view((Path(__file__).resolve().parents[1] / relative_path).read_bytes(), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path)
    prefix = index_resume_historical_view(source, relative_path)
    index_scope_historical_view(prefix, relative_path)
    assert set(INDEX_RESUME_VIEW_SHA256) == set(INDEX_RESUME_VIEW_PREFIX_BLOBS) == set(INDEX_VIEW_SHA256)


@pytest.mark.parametrize("relative_path", tuple(INDEX_RESUME_VIEW_SHA256))
@pytest.mark.parametrize("mutation", ("missing_marker", "duplicate_marker", "separator", "prefix", "prefix_crlf", "whole_crlf", "section_crlf", "suffix", "comment", "trailing_blank_line", "missing_final_newline", "live_authority", "startup_approved", "data_scope", "scope_order"))
def test_index_resume_projection_rejects_unreviewed_bytes(relative_path: str, mutation: str) -> None:
    """IRG-06/08: exact terminal bytes, including every restricted-execution claim."""
    source = review_identity_historical_view(review_identity_resume_historical_view(key_binding_historical_view(key_binding_resume_historical_view(recovery_scope_historical_view(recovery_resume_historical_view(dataset_scope_historical_view(dataset_resume_historical_view(overlay_scope_historical_view(overlay_resume_historical_view(ci_scope_historical_view(ci_resume_historical_view(ci_amend_historical_view((Path(__file__).resolve().parents[1] / relative_path).read_bytes(), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path)
    marker = INDEX_RESUME_VIEW_MARKER.encode(); separator = b"\n" + marker + b"\n"
    prefix, section = source.split(separator, 1)
    if mutation == "missing_marker":
        tampered = source.replace(marker, b"", 1)
    elif mutation == "duplicate_marker":
        tampered = source + separator
    elif mutation == "separator":
        tampered = source.replace(separator, b"\n\n" + marker + b"\n", 1)
    elif mutation == "prefix":
        tampered = b"edited\n" + source
    elif mutation == "prefix_crlf":
        tampered = prefix.replace(b"\n", b"\r\n") + separator + section
    elif mutation == "whole_crlf":
        tampered = source.replace(b"\n", b"\r\n")
    elif mutation == "section_crlf":
        tampered = prefix + separator + section.replace(b"\n", b"\r\n")
    elif mutation in ("suffix", "comment", "trailing_blank_line"):
        tampered = source + {"suffix": b"\n### Override\n", "comment": b"\n<!-- override -->\n", "trailing_blank_line": b"\n"}[mutation]
    elif mutation == "missing_final_newline":
        tampered = source.removesuffix(b"\n")
    elif mutation == "scope_order":
        first, second = (f"- `{p}`\n".encode() for p in INDEX_SCOPE_RECORD["allowed_paths"][:2])
        tampered = prefix + separator + section.replace(first + second, second + first)
    else:
        old, new = {"live_authority": (b"live_database_authorized=false", b"live_database_authorized=true"), "startup_approved": (b"startup_criteria_status=UNKNOWN_NOT_APPROVED", b"startup_criteria_status=APPROVED"), "data_scope": (b"SYNTHETIC_DATA_ONLY", b"OWNER_DATA")}[mutation]
        tampered = prefix + separator + section.replace(old, new)
    assert tampered != source
    with pytest.raises(AssertionError, match="index_resume_view_"):
        index_resume_historical_view(tampered, relative_path)


@pytest.mark.parametrize("relative_path", tuple(INDEX_RESUME_VIEW_SHA256))
def test_index_resume_rejects_cross_path_projection_transplants(relative_path: str) -> None:
    """IRG-06: authentic content from another path cannot borrow this path's seal."""
    root = Path(__file__).resolve().parents[1]
    other = next(p for p in INDEX_RESUME_VIEW_SHA256 if p != relative_path)
    source, other_source = review_identity_historical_view(review_identity_resume_historical_view(key_binding_historical_view(key_binding_resume_historical_view(recovery_scope_historical_view(recovery_resume_historical_view(dataset_scope_historical_view(dataset_resume_historical_view(overlay_scope_historical_view(overlay_resume_historical_view(ci_scope_historical_view(ci_resume_historical_view(ci_amend_historical_view((root / relative_path).read_bytes(), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), review_identity_historical_view(review_identity_resume_historical_view(key_binding_historical_view(key_binding_resume_historical_view(recovery_scope_historical_view(recovery_resume_historical_view(dataset_scope_historical_view(dataset_resume_historical_view(overlay_scope_historical_view(overlay_resume_historical_view(ci_scope_historical_view(ci_resume_historical_view(ci_amend_historical_view((root / other).read_bytes(), other), other), other), other), other), other), other), other), other), other), other), other), other)
    separator = ("\n" + INDEX_RESUME_VIEW_MARKER + "\n").encode()
    with pytest.raises(AssertionError, match="index_resume_view_prefix_changed"):
        index_resume_historical_view(other_source, relative_path)
    with pytest.raises(AssertionError, match="index_resume_view_projection_changed"):
        index_resume_historical_view(source.split(separator, 1)[0] + separator + other_source.split(separator, 1)[1], relative_path)


@pytest.mark.parametrize("path", ("", "docs/unapproved.md", "backend/repository.py"))
def test_index_resume_projection_has_no_default_path(path: str) -> None:
    """IRG-06: no fallback seal is accepted for unregistered documents."""
    source = review_identity_historical_view(review_identity_resume_historical_view(key_binding_historical_view(key_binding_resume_historical_view(recovery_scope_historical_view(recovery_resume_historical_view(dataset_scope_historical_view(dataset_resume_historical_view(overlay_scope_historical_view(overlay_resume_historical_view(ci_scope_historical_view(ci_resume_historical_view(ci_amend_historical_view((Path(__file__).resolve().parents[1] / CONSUMPTION_VIEW_PATHS[0]).read_bytes(), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0])
    with pytest.raises(AssertionError, match="index_resume_view_path"):
        index_resume_historical_view(source, path)


def test_index_resume_requires_raw_view_bytes_and_preserves_reviewed_design() -> None:
    """IRG-06/08: source bytes and immutable design remain independent evidence."""
    root = Path(__file__).resolve().parents[1]
    path = CONSUMPTION_VIEW_PATHS[0]
    with pytest.raises(AssertionError, match="index_resume_view_source_bytes"):
        index_resume_historical_view((root / path).read_text(), path)
    assert git_blob_sha((root / "docs/FC20-12-F01A-INDEX-CONDITIONAL-RESUME-PROPOSAL-2026-10-11.md").read_bytes()) == "0a87463111c78263db11ac4d3bf103c16e47f261", "index_resume_design_changed"


@pytest.mark.parametrize("container,keys", (("decision", tuple(INDEX_RESUME_DECISION)), ("subject", tuple(INDEX_RESUME_DECISION["subject"]))))
def test_index_resume_requires_each_decision_and_subject_field(container: str, keys: tuple) -> None:
    """IRG-03: complete receipt and exact subject are mandatory, not optional metadata."""
    for field in keys:
        manifest = historical_index_resume_manifest()
        target = defensive_record(manifest)["events"][9]["owner_resume_decision"]
        if container == "subject":
            target = target["subject"]
        target.pop(field)
        with pytest.raises(AssertionError, match="defensive_record_mismatch"):
            validate_index_resume(defensive_record(manifest), manifest["execution_sequence"]["active_target"])


@pytest.mark.parametrize("path", [p for p in index_resume_leaf_paths(INDEX_RESUME_RECORD) if p[-1] == "unique"])
@pytest.mark.parametrize("value", (0, 1, "false", None))
def test_index_resume_operation_booleans_are_literal_in_every_copy(path: list, value: object) -> None:
    """IRG-03: copied historical and current operations reject false-like integers."""
    manifest = historical_index_resume_manifest()
    target = defensive_record(manifest)
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(AssertionError):
        validate_index_resume(defensive_record(manifest), manifest["execution_sequence"]["active_target"])



def test_index_resume_nested_operation_mutation_inventory_is_nonempty() -> None:
    """IRG-03: a list-blind enumerator must not silently skip operation copies."""
    paths = [p for p in index_resume_leaf_paths(INDEX_RESUME_RECORD) if p[-1] == "unique"]
    assert ("allowed_schema_operations", 0, "unique") in paths
    assert ("events", 9, "owner_resume_decision", "subject", "allowed_schema_operations", 0, "unique") in paths
    assert len(paths) >= 3


# RISG: stopped semantic-scope registration; preparation is never execution authority.
REVIEW_IDENTITY_REPAIR_SCOPE = json.loads(r'''{
  "purpose": "REVIEW_APPROVAL_STORED_CONTEXT_INTEGRITY_ONLY",
  "implementation_paths": [
    "backend/repository.py",
    "tests/test_repository_intelligence.py"
  ],
  "boundary": "EXISTING_TRANSACTIONAL_INTELLIGENCE_REVIEW_CONTEXT",
  "validation": "REUSE_CONSUMPTION_SHAPE_TYPED_ROW_EQUALITY_NATIVE_LIFECYCLE_HASH",
  "historical_read_and_origin_proof_policy": "UNCHANGED",
  "additional_schema_operations": [],
  "database_and_data_scope": "DISPOSABLE_TEMPORARY_DATABASES_SYNTHETIC_DATA_ONLY"
}''')
REVIEW_IDENTITY_STOP_EVENT = json.loads(r'''{
  "type": "STOP_CHECKPOINT",
  "recorded_at": "2026-10-11T20:51:05Z",
  "baseline_commit_sha": "abbdea3913630a7e940c454c46919f88c673aa0f",
  "baseline_manifest_blob_sha": "d76e7b0f6d18a701985469664c0cb6c1f757c869",
  "application_head_sha": "3cf88c7bae98a48c5cd950df978678f452501980",
  "reason": "REVIEW_APPROVAL_STORED_CONTEXT_INTEGRITY_OUTSIDE_INDEX_ONLY_RESUME",
  "evidence": {
    "url": "https://github.com/alphasigma13579-lang/ASIE/blob/ae4b69ee3e56930ce1af944a2577e79e5ab44681/ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/docs/FC20-12-F01A-REVIEW-IDENTITY-SCOPE-PROPOSAL-2026-10-11.md",
    "commit_sha": "ae4b69ee3e56930ce1af944a2577e79e5ab44681",
    "blob_sha": "7aa270286535f831a8eac25170ee495043b40bf5"
  },
  "resume_requirement": "NEW_OWNER_DECISION_BOUND_TO_REVIEW_APPROVAL_REPAIR_SCOPE_AND_REVIEWED_EXACT_HEAD_GOVERNANCE_TRANSITION"
}''')
REVIEW_IDENTITY_SCOPE_DECISION = json.loads(r'''{
  "id": "DECISION-FC20-12-F01A-REVIEW-IDENTITY-SCOPE-REGISTRATION-PREPARATION-2026-10-11",
  "record_url": "https://github.com/alphasigma13579-lang/ASIE/pull/201#issuecomment-6113714644",
  "recorded_at": "2026-10-11T20:44:24Z",
  "effect": "PREPARE_GOVERNANCE_PR_ONLY_NO_MERGE_NO_RESUME",
  "subject": {
    "baseline_commit_sha": "abbdea3913630a7e940c454c46919f88c673aa0f",
    "baseline_manifest_blob_sha": "d76e7b0f6d18a701985469664c0cb6c1f757c869",
    "application_head_sha": "3cf88c7bae98a48c5cd950df978678f452501980",
    "allowed_paths": [
      "backend/asie_local_api.py",
      "backend/repository.py",
      "backend/intelligence_prerun_service.py",
      "tests/test_repository_intelligence.py",
      "tests/test_intelligence_prerun_service.py",
      "tests/test_intelligence_context_ingress_api.py",
      "docs/FC20-12-F01-TRUSTED-CONTEXT-INGRESS-REPAIR-PLAN-2026-10-01.md",
      "tests/test_live_location_api.py",
      "tests/test_intelligence_consumption.py"
    ],
    "allowed_schema_operations": [
      {
        "operation": "CREATE_INDEX_IF_NOT_EXISTS",
        "index_name": "idx_security_audit_origin_proof",
        "table": "security_audit_events",
        "columns": [
          "action",
          "target_type",
          "target_id",
          "organization_id"
        ],
        "unique": false,
        "implementation_path": "backend/repository.py",
        "test_path": "tests/test_repository_intelligence.py"
      }
    ],
    "repair_scope": {
      "purpose": "REVIEW_APPROVAL_STORED_CONTEXT_INTEGRITY_ONLY",
      "implementation_paths": [
        "backend/repository.py",
        "tests/test_repository_intelligence.py"
      ],
      "boundary": "EXISTING_TRANSACTIONAL_INTELLIGENCE_REVIEW_CONTEXT",
      "validation": "REUSE_CONSUMPTION_SHAPE_TYPED_ROW_EQUALITY_NATIVE_LIFECYCLE_HASH",
      "historical_read_and_origin_proof_policy": "UNCHANGED",
      "additional_schema_operations": [],
      "database_and_data_scope": "DISPOSABLE_TEMPORARY_DATABASES_SYNTHETIC_DATA_ONLY"
    }
  },
  "proposal_commit_sha": "ae4b69ee3e56930ce1af944a2577e79e5ab44681",
  "proposal_blob_sha": "7aa270286535f831a8eac25170ee495043b40bf5"
}''')
REVIEW_IDENTITY_SCOPE_DECISION["subject"]["baseline_record"] = deepcopy(INDEX_RESUME_RECORD)
REVIEW_IDENTITY_SCOPE_DECISION["subject"]["previous_resume"] = deepcopy(INDEX_RESUME_EVENT)
REVIEW_IDENTITY_SCOPE_EVENT = json.loads(r'''{
  "type": "SCOPE_EXTENSION",
  "recorded_at": "2026-10-11T20:51:05Z",
  "baseline_commit_sha": "abbdea3913630a7e940c454c46919f88c673aa0f",
  "baseline_manifest_blob_sha": "d76e7b0f6d18a701985469664c0cb6c1f757c869",
  "application_head_sha": "3cf88c7bae98a48c5cd950df978678f452501980",
  "added_paths": [],
  "scope_addendum": {
    "url": "https://github.com/alphasigma13579-lang/ASIE/blob/ae4b69ee3e56930ce1af944a2577e79e5ab44681/ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/docs/FC20-12-F01A-REVIEW-IDENTITY-SCOPE-PROPOSAL-2026-10-11.md",
    "commit_sha": "ae4b69ee3e56930ce1af944a2577e79e5ab44681",
    "blob_sha": "7aa270286535f831a8eac25170ee495043b40bf5"
  },
  "effect": "SCOPE_EXTENSION_ONLY_NO_RESUME"
}''')
REVIEW_IDENTITY_SCOPE_EVENT["owner_scope_decision"] = deepcopy(REVIEW_IDENTITY_SCOPE_DECISION)
REVIEW_IDENTITY_SCOPE_RECORD = deepcopy(INDEX_RESUME_RECORD)
REVIEW_IDENTITY_SCOPE_RECORD["execution_authorized"] = False
REVIEW_IDENTITY_SCOPE_RECORD["events"].extend([deepcopy(REVIEW_IDENTITY_STOP_EVENT), deepcopy(REVIEW_IDENTITY_SCOPE_EVENT)])
REVIEW_IDENTITY_VIEW_PREFIX_BLOBS = json.loads(r'''{
  "docs/ASIE-BETA-EXECUTION-MASTER-PLAN-2026-09-09.md": "55eebca832956adc8ce55010749b83ddaff15d5c",
  "docs/FC20-12-F01A-DEFENSIVE-ENABLING-REGISTRATION-PROPOSAL-2026-10-01.md": "b9ec8c2625b3a81334cdd8d53669edcebd3f1197",
  "docs/FC20-12-F01A-APPROVAL-CONSUMPTION-SCOPE-REGISTRATION-2026-10-09.md": "fb96b90af891332bc93ce01502d94383c443beb2",
  "docs/FOUNDATION-COMPLETE-20-CORE-INTELLIGENCE-COMPLETION-PROGRAM-2026-07-29.md": "1040b196674222457ea45f7517dec8912931605e",
  "docs/EKB/FOUNDATION-COMPLETE-20-PACKAGE-INDEX.md": "24b5b6f2c3c06644efd1dabf2b704559a20946a3"
}''')
REVIEW_IDENTITY_VIEW_SHA256 = json.loads(r'''{
  "docs/ASIE-BETA-EXECUTION-MASTER-PLAN-2026-09-09.md": "a28a53a33180d5c606228148bfb889c3209992396b4651447bce7292617aae08",
  "docs/FC20-12-F01A-DEFENSIVE-ENABLING-REGISTRATION-PROPOSAL-2026-10-01.md": "ee9b3fcfea25a940f694169fe5caf6ca92ac25d00e7cec766841b783f094c14b",
  "docs/FC20-12-F01A-APPROVAL-CONSUMPTION-SCOPE-REGISTRATION-2026-10-09.md": "1e0ee8e0fdac453d0742aef783fbc3e857f8a613b466db92bba610664e529354",
  "docs/FOUNDATION-COMPLETE-20-CORE-INTELLIGENCE-COMPLETION-PROGRAM-2026-07-29.md": "1f5bd80fcdded4763cf54637371d71a8323f24e8b727f225724f42dce50f766f",
  "docs/EKB/FOUNDATION-COMPLETE-20-PACKAGE-INDEX.md": "7aef322a266c1355b74fb2a45d2be61b7c02d46f7eaa366785deff3e0ed3b1f0"
}''')
REVIEW_IDENTITY_VIEW_MARKER = '<!-- F01A-REVIEW-IDENTITY-SCOPE-REGISTRATION-2026-10-11 -->'


def _validate_review_identity_structure(record: dict, active_target: object) -> None:
    """RISG-01/02/03/04: exact structure only; this does not admit a receipt."""
    assert isinstance(record, dict), "invalid_defensive_record"
    assert set(record) == set(REVIEW_IDENTITY_SCOPE_RECORD), "defensive_fields"
    assert record == REVIEW_IDENTITY_SCOPE_RECORD, "defensive_record_mismatch"
    assert (lambda: json.dumps(record, sort_keys=True) == json.dumps(REVIEW_IDENTITY_SCOPE_RECORD, sort_keys=True))(), "review_identity_literal_types"
    assert record["execution_authorized"] is False, "review_identity_stop_flag"
    assert all(record[key] is False for key in (
        "network_authorized", "provider_activation_authorized", "deployment_authorized",
    )), "defensive_external_effect"
    assert active_target == DEFENSIVE_START_TARGET, "review_identity_slot"
    decision = record["events"][11]["owner_scope_decision"]
    assert decision == REVIEW_IDENTITY_SCOPE_DECISION, "review_identity_decision_mismatch"
    assert decision["subject"]["repair_scope"] == REVIEW_IDENTITY_REPAIR_SCOPE, "review_identity_repair_scope"
    assert decision["subject"]["baseline_record"] == INDEX_RESUME_RECORD, "review_identity_previous_record"
    assert decision["subject"]["previous_resume"] == INDEX_RESUME_EVENT, "review_identity_previous_resume"
    assert record["allowed_paths"] == INDEX_RESUME_RECORD["allowed_paths"], "review_identity_paths"
    assert record["allowed_schema_operations"] == [INDEX_OPERATION], "review_identity_schema_operation"
    assert record["allowed_schema_operations"][0]["unique"] is False, "review_identity_operation_literal"
    assert record["events"][11]["added_paths"] == [], "review_identity_added_paths"
    assert "added_schema_operations" not in record["events"][11], "review_identity_no_added_schema"


def validate_review_identity_scope(record: dict, active_target: object) -> None:
    """RISG-03/07: current admission requires a real, independently pinned receipt."""
    _validate_review_identity_structure(record, active_target)
    receipt = record["events"][11]["owner_scope_decision"]["record_url"]
    assert isinstance(receipt, str) and re.fullmatch(
        r"https://github\.com/alphasigma13579-lang/ASIE/pull/201#issuecomment-[0-9]+", receipt,
    ), "review_identity_receipt_missing_or_invalid"


def _review_identity_historical_inverse(manifest: dict) -> dict:
    """RISG-05: structure-only test history; NEVER current admission authority."""
    restored = deepcopy(manifest)
    record = defensive_record(restored)
    _validate_review_identity_structure(record, restored["execution_sequence"]["active_target"])
    assert record["events"].pop() == REVIEW_IDENTITY_SCOPE_EVENT
    assert record["events"].pop() == REVIEW_IDENTITY_STOP_EVENT
    record["execution_authorized"] = True
    source = (json.dumps(restored, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    assert git_blob_sha(source) == "d76e7b0f6d18a701985469664c0cb6c1f757c869", "review_identity_baseline_mismatch"
    validate_index_resume(record, restored["execution_sequence"]["active_target"])
    return restored


def validate_review_identity_scope_baseline(manifest: dict) -> dict:
    """RISG-05/07: require real current admission before validating its full inverse."""
    validate_review_identity_scope(defensive_record(manifest), manifest["execution_sequence"]["active_target"])
    return _review_identity_historical_inverse(manifest)


def historical_index_resume_manifest() -> dict:
    """Verified ten-event test history only; never accepts the current proposal."""
    return _review_identity_historical_inverse(historical_review_identity_scope_manifest())


def review_identity_historical_view(source_bytes: bytes, relative_path: str) -> bytes:
    """RISG-06: exact raw historical prefix and one path-bound terminal section."""
    assert isinstance(source_bytes, bytes), "review_identity_view_source_bytes"
    assert relative_path in REVIEW_IDENTITY_VIEW_SHA256, "review_identity_view_path"
    marker = REVIEW_IDENTITY_VIEW_MARKER.encode("utf-8")
    separator = b"\n" + marker + b"\n"
    assert source_bytes.count(marker) == 1, "review_identity_view_marker"
    assert source_bytes.count(separator) == 1, "review_identity_view_boundary"
    prefix, section = source_bytes.split(separator, 1)
    assert git_blob_sha(prefix) == REVIEW_IDENTITY_VIEW_PREFIX_BLOBS[relative_path], "review_identity_view_prefix_changed"
    assert hashlib.sha256(marker + b"\n" + section).hexdigest() == REVIEW_IDENTITY_VIEW_SHA256[relative_path], "review_identity_view_projection_changed"
    index_resume_historical_view(prefix, relative_path)
    return prefix


def test_review_identity_structural_inverse_preserves_all_ten_events_and_oracles() -> None:
    """RISG-01/02/05: structural success is not real-receipt admission."""
    manifest = historical_review_identity_scope_manifest()
    record = defensive_record(manifest)
    _validate_review_identity_structure(record, manifest["execution_sequence"]["active_target"])
    assert len(record["events"]) == 12
    assert record["events"][:10] == INDEX_RESUME_RECORD["events"]
    assert record["allowed_paths"] == INDEX_RESUME_RECORD["allowed_paths"]
    assert len(record["allowed_paths"]) == 9
    assert record["allowed_schema_operations"] == [INDEX_OPERATION]
    assert record["execution_authorized"] is False
    assert manifest["execution_sequence"]["held_packages"] == HELD_PACKAGES
    assert active_execution_targets(manifest["packages"], {"FC20-05"}) == ["FC20-12/f01a_defensive_ingress"]
    baseline = _review_identity_historical_inverse(manifest)
    index_scope = validate_index_resume_baseline(baseline)
    consumption_resume = validate_index_scope_baseline(index_scope)
    consumption_scope = validate_consumption_resume_baseline(consumption_resume)
    old_resume = validate_consumption_scope_baseline(consumption_scope)
    validate_scope_extension_baseline(validate_resume_baseline(old_resume))


def test_review_identity_historical_scope_admission_requires_actual_receipt() -> None:
    """RISG-07: the historical scope still requires its actual independently pinned receipt."""
    manifest = historical_review_identity_scope_manifest()
    validate_review_identity_scope_baseline(manifest)
    validate_review_identity_scope(defensive_record(manifest), manifest["execution_sequence"]["active_target"])


def test_review_identity_unresolved_receipt_has_no_admission_or_inverse_authority() -> None:
    """RISG-07: a preparation placeholder cannot replace the actual pinned receipt."""
    manifest = historical_review_identity_scope_manifest()
    defensive_record(manifest)["events"][11]["owner_scope_decision"]["record_url"] = "UNRESOLVED_OWNER_DECISION_RECORD_URL"
    with pytest.raises(AssertionError, match="defensive_record_mismatch"):
        validate_review_identity_scope_baseline(manifest)
    with pytest.raises(AssertionError, match="defensive_record_mismatch"):
        validate_review_identity_scope(defensive_record(manifest), manifest["execution_sequence"]["active_target"])


@pytest.mark.parametrize("event_index", (10, 11))
def test_review_identity_requires_every_new_event_field(event_index: int) -> None:
    for field in REVIEW_IDENTITY_SCOPE_RECORD["events"][event_index]:
        record = deepcopy(REVIEW_IDENTITY_SCOPE_RECORD)
        record["events"][event_index].pop(field)
        with pytest.raises(AssertionError, match="defensive_record_mismatch"):
            _validate_review_identity_structure(record, DEFENSIVE_START_TARGET)


@pytest.mark.parametrize("path", index_resume_leaf_paths(REVIEW_IDENTITY_SCOPE_RECORD["events"][11]))
def test_review_identity_pins_every_scope_decision_leaf_before_receipt(path: tuple) -> None:
    """RISG-03: exercise structure, not an early missing-receipt failure."""
    record = deepcopy(REVIEW_IDENTITY_SCOPE_RECORD)
    target = record["events"][11]
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = "[unreviewed]"
    with pytest.raises(AssertionError, match="defensive_record_mismatch"):
        _validate_review_identity_structure(record, DEFENSIVE_START_TARGET)


@pytest.mark.parametrize("path", index_resume_leaf_paths(REVIEW_IDENTITY_STOP_EVENT))
def test_review_identity_pins_every_stop_leaf(path: tuple) -> None:
    record = deepcopy(REVIEW_IDENTITY_SCOPE_RECORD)
    target = record["events"][10]
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = "[unreviewed]"
    with pytest.raises(AssertionError, match="defensive_record_mismatch"):
        _validate_review_identity_structure(record, DEFENSIVE_START_TARGET)


@pytest.mark.parametrize("field", tuple(REVIEW_IDENTITY_REPAIR_SCOPE))
@pytest.mark.parametrize("mutation", ("missing", "changed"))
def test_review_identity_repair_scope_is_closed(field: str, mutation: str) -> None:
    record = deepcopy(REVIEW_IDENTITY_SCOPE_RECORD)
    scope = record["events"][11]["owner_scope_decision"]["subject"]["repair_scope"]
    if mutation == "missing":
        scope.pop(field)
    else:
        scope[field] = "UNRESTRICTED"
    with pytest.raises(AssertionError, match="defensive_record_mismatch"):
        _validate_review_identity_structure(record, DEFENSIVE_START_TARGET)


@pytest.mark.parametrize("container", ("decision", "subject", "repair_scope"))
def test_review_identity_rejects_unknown_and_missing_nested_fields(container: str) -> None:
    original = REVIEW_IDENTITY_SCOPE_DECISION
    if container == "subject":
        original = original["subject"]
    elif container == "repair_scope":
        original = original["subject"]["repair_scope"]
    for field in (None, *original):
        record = deepcopy(REVIEW_IDENTITY_SCOPE_RECORD)
        target = record["events"][11]["owner_scope_decision"]
        if container in ("subject", "repair_scope"):
            target = target["subject"]
        if container == "repair_scope":
            target = target["repair_scope"]
        if field is None:
            target["trusted_override"] = True
        else:
            target.pop(field)
        with pytest.raises(AssertionError, match="defensive_record_mismatch"):
            _validate_review_identity_structure(record, DEFENSIVE_START_TARGET)


@pytest.mark.parametrize("index", range(12))
@pytest.mark.parametrize("mutation", ("delete", "duplicate", "change", "reorder"))
def test_review_identity_preserves_each_event(index: int, mutation: str) -> None:
    record = deepcopy(REVIEW_IDENTITY_SCOPE_RECORD)
    events = record["events"]
    if mutation == "delete":
        events.pop(index)
    elif mutation == "duplicate":
        events.insert(index, deepcopy(events[index]))
    elif mutation == "change":
        events[index]["type"] = "OVERRIDE"
    else:
        other = (index + 1) % len(events)
        events[index], events[other] = events[other], events[index]
    with pytest.raises(AssertionError, match="defensive_record_mismatch"):
        _validate_review_identity_structure(record, DEFENSIVE_START_TARGET)


@pytest.mark.parametrize("field,value", (("execution_authorized", True), ("execution_authorized", 0), ("execution_authorized", 1), ("execution_authorized", "false"), ("state", "DELIVERED"), ("delivery_evidence", {"passed": True}), ("closure_effect", "COMPLETE"), ("environment", "LIVE"), ("network_authorized", 0), ("network_authorized", True), ("provider_activation_authorized", True), ("deployment_authorized", True)))
def test_review_identity_requires_literal_flags_and_no_terminal_effects(field: str, value: object) -> None:
    record = deepcopy(REVIEW_IDENTITY_SCOPE_RECORD)
    record[field] = value
    with pytest.raises(AssertionError):
        _validate_review_identity_structure(record, DEFENSIVE_START_TARGET)


@pytest.mark.parametrize("path", [p for p in index_resume_leaf_paths(REVIEW_IDENTITY_SCOPE_RECORD) if p[-1] == "unique"])
@pytest.mark.parametrize("value", (0, 1, "false", None))
def test_review_identity_operation_boolean_is_literal_in_every_copy(path: tuple, value: object) -> None:
    record = deepcopy(REVIEW_IDENTITY_SCOPE_RECORD)
    target = record
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(AssertionError):
        _validate_review_identity_structure(record, DEFENSIVE_START_TARGET)


@pytest.mark.parametrize("mutation", ("old_scope_decision", "old_resume_decision", "resume", "start", "delivered", "extra_path", "path_order", "schema", "extra_schema", "repair_paths", "scope_override", "effect", "fake_receipt"))
def test_review_identity_rejects_implicit_or_reused_authority(mutation: str) -> None:
    record = deepcopy(REVIEW_IDENTITY_SCOPE_RECORD)
    event = record["events"][11]
    if mutation == "old_scope_decision":
        event["owner_scope_decision"] = deepcopy(INDEX_SCOPE_DECISION)
    elif mutation == "old_resume_decision":
        event["owner_scope_decision"] = deepcopy(INDEX_RESUME_DECISION)
    elif mutation in ("resume", "start", "delivered"):
        record["events"].append({"type": mutation.upper()})
    elif mutation == "extra_path":
        record["allowed_paths"].append("backend/other.py")
    elif mutation == "path_order":
        record["allowed_paths"].reverse()
    elif mutation == "schema":
        event["added_schema_operations"] = []
    elif mutation == "extra_schema":
        record["allowed_schema_operations"].append(deepcopy(INDEX_OPERATION))
    elif mutation == "repair_paths":
        event["owner_scope_decision"]["subject"]["repair_scope"]["implementation_paths"].append("backend/asie_local_api.py")
    elif mutation == "scope_override":
        event["owner_scope_decision"]["subject"]["repair_scope"]["override"] = True
    elif mutation == "fake_receipt":
        event["owner_scope_decision"]["record_url"] = "https://github.com/alphasigma13579-lang/ASIE/pull/201#issuecomment-0"
    else:
        event["owner_scope_decision"]["effect"] = "F01A_DEFENSIVE_RESUME_ONLY"
    with pytest.raises(AssertionError, match="defensive_record_mismatch"):
        _validate_review_identity_structure(record, DEFENSIVE_START_TARGET)


@pytest.mark.parametrize("record", (DEFENSIVE_REGISTRATION, DEFENSIVE_START_RECORD, DEFENSIVE_STOP_RECORD, DEFENSIVE_SCOPE_EXTENSION_RECORD, DEFENSIVE_RESUME_RECORD, CONSUMPTION_SCOPE_RECORD, CONSUMPTION_RESUME_RECORD, INDEX_SCOPE_RECORD, INDEX_RESUME_RECORD, lifecycle_fixture()[0]))
def test_review_identity_never_admits_historical_or_fixture_authority(record: dict) -> None:
    with pytest.raises(AssertionError):
        validate_review_identity_scope(deepcopy(record), DEFENSIVE_START_TARGET)


@pytest.mark.parametrize("mutation", ("root", "rule", "package", "dependency", "hold", "limit", "frozen", "routing", "release"))
def test_review_identity_full_structural_inverse_rejects_unrelated_delta(mutation: str) -> None:
    manifest = historical_review_identity_scope_manifest()
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
    elif mutation == "limit":
        manifest["execution_sequence"]["max_active_executions"] = 2
    elif mutation == "frozen":
        manifest["frozen_files"].append("backend/unknown.py")
    elif mutation == "routing":
        packages["FC20-12"]["execution_slices"][0]["required_entry_controls"]["single_active_execution"]["status"] = "PASS"
    else:
        manifest["public_release_authorized"] = True
    with pytest.raises(AssertionError, match="review_identity_baseline_mismatch"):
        _review_identity_historical_inverse(manifest)


@pytest.mark.parametrize("slot", (None, {}, {"kind": "package", "package_id": "FC20-05"}))
def test_review_identity_keeps_one_counted_slot(slot: object) -> None:
    with pytest.raises(AssertionError, match="review_identity_slot"):
        _validate_review_identity_structure(deepcopy(REVIEW_IDENTITY_SCOPE_RECORD), slot)


@pytest.mark.parametrize("relative_path", tuple(REVIEW_IDENTITY_VIEW_SHA256))
def test_review_identity_raw_projection_seals_and_historical_chain(relative_path: str) -> None:
    source = review_identity_resume_historical_view(key_binding_historical_view(key_binding_resume_historical_view(recovery_scope_historical_view(recovery_resume_historical_view(dataset_scope_historical_view(dataset_resume_historical_view(overlay_scope_historical_view(overlay_resume_historical_view(ci_scope_historical_view(ci_resume_historical_view(ci_amend_historical_view((Path(__file__).resolve().parents[1] / relative_path).read_bytes(), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path)
    prefix = review_identity_historical_view(source, relative_path)
    assert git_blob_sha(prefix) == REVIEW_IDENTITY_VIEW_PREFIX_BLOBS[relative_path]
    index_resume_historical_view(prefix, relative_path)
    assert set(REVIEW_IDENTITY_VIEW_SHA256) == set(REVIEW_IDENTITY_VIEW_PREFIX_BLOBS) == set(INDEX_RESUME_VIEW_SHA256)


@pytest.mark.parametrize("relative_path", tuple(REVIEW_IDENTITY_VIEW_SHA256))
@pytest.mark.parametrize("mutation", ("missing_marker", "duplicate_marker", "separator", "prefix", "prefix_crlf", "whole_crlf", "section_crlf", "suffix", "comment", "trailing_blank_line", "missing_final_newline", "scope", "execution", "schema", "receipt", "path_order"))
def test_review_identity_rejects_unreviewed_projection_bytes(relative_path: str, mutation: str) -> None:
    source = review_identity_resume_historical_view(key_binding_historical_view(key_binding_resume_historical_view(recovery_scope_historical_view(recovery_resume_historical_view(dataset_scope_historical_view(dataset_resume_historical_view(overlay_scope_historical_view(overlay_resume_historical_view(ci_scope_historical_view(ci_resume_historical_view(ci_amend_historical_view((Path(__file__).resolve().parents[1] / relative_path).read_bytes(), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path)
    marker = REVIEW_IDENTITY_VIEW_MARKER.encode(); separator = b"\n" + marker + b"\n"
    prefix, section = source.split(separator, 1)
    if mutation == "missing_marker":
        tampered = source.replace(marker, b"", 1)
    elif mutation == "duplicate_marker":
        tampered = source + separator
    elif mutation == "separator":
        tampered = source.replace(separator, b"\n\n" + marker + b"\n", 1)
    elif mutation == "prefix":
        tampered = b"edited\n" + source
    elif mutation == "prefix_crlf":
        tampered = prefix.replace(b"\n", b"\r\n") + separator + section
    elif mutation == "whole_crlf":
        tampered = source.replace(b"\n", b"\r\n")
    elif mutation == "section_crlf":
        tampered = prefix + separator + section.replace(b"\n", b"\r\n")
    elif mutation in ("suffix", "comment", "trailing_blank_line"):
        tampered = source + {"suffix": b"\n### Override\n", "comment": b"\n<!-- override -->\n", "trailing_blank_line": b"\n"}[mutation]
    elif mutation == "missing_final_newline":
        tampered = source.removesuffix(b"\n")
    elif mutation == "path_order":
        first, second = (f"- `{p}`\n".encode() for p in INDEX_RESUME_RECORD["allowed_paths"][:2])
        tampered = prefix + separator + section.replace(first + second, second + first)
    else:
        old, new = {"scope": (b"REVIEW_APPROVAL_STORED_CONTEXT_INTEGRITY_ONLY", b"UNRESTRICTED"), "execution": (b"IN_PROGRESS/false", b"IN_PROGRESS/true"), "schema": (b"unique=false", b"unique=true"), "receipt": (b"https://github.com/alphasigma13579-lang/ASIE/pull/201#issuecomment-6113714644", b"FORGED_RECEIPT")}[mutation]
        tampered = prefix + separator + section.replace(old, new)
    assert tampered != source
    with pytest.raises(AssertionError, match="review_identity_view_"):
        review_identity_historical_view(tampered, relative_path)


@pytest.mark.parametrize("relative_path", tuple(REVIEW_IDENTITY_VIEW_SHA256))
def test_review_identity_rejects_cross_path_transplants(relative_path: str) -> None:
    root = Path(__file__).resolve().parents[1]
    other = next(p for p in REVIEW_IDENTITY_VIEW_SHA256 if p != relative_path)
    source, other_source = review_identity_resume_historical_view(key_binding_historical_view(key_binding_resume_historical_view(recovery_scope_historical_view(recovery_resume_historical_view(dataset_scope_historical_view(dataset_resume_historical_view(overlay_scope_historical_view(overlay_resume_historical_view(ci_scope_historical_view(ci_resume_historical_view(ci_amend_historical_view((root / relative_path).read_bytes(), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), review_identity_resume_historical_view(key_binding_historical_view(key_binding_resume_historical_view(recovery_scope_historical_view(recovery_resume_historical_view(dataset_scope_historical_view(dataset_resume_historical_view(overlay_scope_historical_view(overlay_resume_historical_view(ci_scope_historical_view(ci_resume_historical_view(ci_amend_historical_view((root / other).read_bytes(), other), other), other), other), other), other), other), other), other), other), other), other)
    separator = ("\n" + REVIEW_IDENTITY_VIEW_MARKER + "\n").encode()
    with pytest.raises(AssertionError, match="review_identity_view_prefix_changed"):
        review_identity_historical_view(other_source, relative_path)
    with pytest.raises(AssertionError, match="review_identity_view_projection_changed"):
        review_identity_historical_view(source.split(separator, 1)[0] + separator + other_source.split(separator, 1)[1], relative_path)


@pytest.mark.parametrize("path", ("", "docs/unapproved.md", "backend/repository.py"))
def test_review_identity_projection_has_no_fallback(path: str) -> None:
    source = review_identity_resume_historical_view(key_binding_historical_view(key_binding_resume_historical_view(recovery_scope_historical_view(recovery_resume_historical_view(dataset_scope_historical_view(dataset_resume_historical_view(overlay_scope_historical_view(overlay_resume_historical_view(ci_scope_historical_view(ci_resume_historical_view(ci_amend_historical_view((Path(__file__).resolve().parents[1] / CONSUMPTION_VIEW_PATHS[0]).read_bytes(), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0])
    with pytest.raises(AssertionError, match="review_identity_view_path"):
        review_identity_historical_view(source, path)


def test_review_identity_requires_raw_bytes_and_keeps_accepted_design() -> None:
    root = Path(__file__).resolve().parents[1]
    path = CONSUMPTION_VIEW_PATHS[0]
    with pytest.raises(AssertionError, match="review_identity_view_source_bytes"):
        review_identity_historical_view((root / path).read_text(), path)
    assert git_blob_sha((root / "docs/FC20-12-F01A-REVIEW-IDENTITY-SCOPE-PROPOSAL-2026-10-11.md").read_bytes()) == "7aa270286535f831a8eac25170ee495043b40bf5", "review_identity_design_changed"


def test_review_identity_mutation_inventory_covers_nested_lists_and_all_operation_copies() -> None:
    paths = [p for p in index_resume_leaf_paths(REVIEW_IDENTITY_SCOPE_RECORD) if p[-1] == "unique"]
    assert ("allowed_schema_operations", 0, "unique") in paths
    assert ("events", 11, "owner_scope_decision", "subject", "allowed_schema_operations", 0, "unique") in paths
    assert ("events", 11, "owner_scope_decision", "subject", "baseline_record", "allowed_schema_operations", 0, "unique") in paths
    assert len(paths) > len([p for p in index_resume_leaf_paths(INDEX_RESUME_RECORD) if p[-1] == "unique"])


# RIRG: proposed repair-only conditional resume; real execution decision remains conditional on separately approved transition merge.
REVIEW_IDENTITY_RESUME_EXECUTION_SCOPE = json.loads(r'''{
  "activities": [
    "DEVELOP_REGISTERED_REVIEW_APPROVAL_CONTEXT_INTEGRITY",
    "TEST_REGISTERED_REVIEW_APPROVAL_CONTEXT_INTEGRITY"
  ],
  "implementation_paths": [
    "backend/repository.py",
    "tests/test_repository_intelligence.py"
  ],
  "database_scope": "DISPOSABLE_TEMPORARY_DATABASES_ONLY",
  "data_scope": "SYNTHETIC_DATA_ONLY",
  "live_database_authorized": false,
  "owner_database_authorized": false,
  "production_placement_accepted": false,
  "deployment_authorized": false,
  "application_pr_merge_authorized": false,
  "startup_criteria_status": "UNKNOWN_NOT_APPROVED",
  "maintenance_recovery_acceptance": "UNKNOWN_NOT_APPROVED",
  "query_and_proof_semantics": "UNCHANGED"
}''')
REVIEW_IDENTITY_RESUME_DECISION = json.loads(r'''{
  "id": "DECISION-FC20-12-F01A-REVIEW-IDENTITY-CONDITIONAL-RESUME-2026-10-12",
  "record_url": "https://github.com/alphasigma13579-lang/ASIE/pull/202#issuecomment-6121127349",
  "recorded_at": "2026-10-12T09:04:31Z",
  "effect": "F01A_DEFENSIVE_RESUME_ONLY",
  "condition": "REVIEWED_GOVERNANCE_TRANSITION_MERGED_AFTER_SEPARATE_OWNER_MERGE_APPROVAL",
  "subject": {
    "baseline_commit_sha": "fcfd9222e1b47b9d95b96b589ec204b91bae8378",
    "baseline_manifest_blob_sha": "ef142b9a2c2001e0bea4d6068b0f36d5c44c5a4c",
    "application_head_sha": "3cf88c7bae98a48c5cd950df978678f452501980",
    "allowed_paths": [
      "backend/asie_local_api.py",
      "backend/repository.py",
      "backend/intelligence_prerun_service.py",
      "tests/test_repository_intelligence.py",
      "tests/test_intelligence_prerun_service.py",
      "tests/test_intelligence_context_ingress_api.py",
      "docs/FC20-12-F01-TRUSTED-CONTEXT-INGRESS-REPAIR-PLAN-2026-10-01.md",
      "tests/test_live_location_api.py",
      "tests/test_intelligence_consumption.py"
    ],
    "allowed_schema_operations": [
      {
        "operation": "CREATE_INDEX_IF_NOT_EXISTS",
        "index_name": "idx_security_audit_origin_proof",
        "table": "security_audit_events",
        "columns": [
          "action",
          "target_type",
          "target_id",
          "organization_id"
        ],
        "unique": false,
        "implementation_path": "backend/repository.py",
        "test_path": "tests/test_repository_intelligence.py"
      }
    ]
  },
  "proposal_commit_sha": "ae4b69ee3e56930ce1af944a2577e79e5ab44681",
  "proposal_blob_sha": "7aa270286535f831a8eac25170ee495043b40bf5"
}''')
REVIEW_IDENTITY_RESUME_DECISION["subject"].update(checkpoint=deepcopy(REVIEW_IDENTITY_STOP_EVENT), scope_extension=deepcopy(REVIEW_IDENTITY_SCOPE_EVENT), repair_scope=deepcopy(REVIEW_IDENTITY_REPAIR_SCOPE), execution_scope=deepcopy(REVIEW_IDENTITY_RESUME_EXECUTION_SCOPE))
REVIEW_IDENTITY_RESUME_EVENT = json.loads(r'''{
  "type": "RESUME",
  "recorded_at": "2026-10-12T09:05:19Z",
  "baseline_commit_sha": "fcfd9222e1b47b9d95b96b589ec204b91bae8378",
  "baseline_manifest_blob_sha": "ef142b9a2c2001e0bea4d6068b0f36d5c44c5a4c",
  "effect": "F01A_DEFENSIVE_RESUME_ONLY"
}''')
REVIEW_IDENTITY_RESUME_EVENT.update(checkpoint=deepcopy(REVIEW_IDENTITY_STOP_EVENT), scope_extension=deepcopy(REVIEW_IDENTITY_SCOPE_EVENT), owner_resume_decision=deepcopy(REVIEW_IDENTITY_RESUME_DECISION))
REVIEW_IDENTITY_RESUME_RECORD = deepcopy(REVIEW_IDENTITY_SCOPE_RECORD)
REVIEW_IDENTITY_RESUME_RECORD["execution_authorized"] = True
REVIEW_IDENTITY_RESUME_RECORD["events"].append(deepcopy(REVIEW_IDENTITY_RESUME_EVENT))
REVIEW_IDENTITY_RESUME_VIEW_PREFIX_BLOBS = json.loads(r'''{
  "docs/ASIE-BETA-EXECUTION-MASTER-PLAN-2026-09-09.md": "cf5b5618b84034314f91c5542fa14114d43095b5",
  "docs/FC20-12-F01A-DEFENSIVE-ENABLING-REGISTRATION-PROPOSAL-2026-10-01.md": "97b126adc06e063ed29a3d4a856e82f7955631d6",
  "docs/FC20-12-F01A-APPROVAL-CONSUMPTION-SCOPE-REGISTRATION-2026-10-09.md": "6234c26c218744d6796357828f719db4802f1d10",
  "docs/FOUNDATION-COMPLETE-20-CORE-INTELLIGENCE-COMPLETION-PROGRAM-2026-07-29.md": "3702a696253433a3ce96f0a81427e52b360380a7",
  "docs/EKB/FOUNDATION-COMPLETE-20-PACKAGE-INDEX.md": "fe075505bfa6d6fe2e65562af10de044433f787a"
}''')
REVIEW_IDENTITY_RESUME_VIEW_SHA256 = json.loads(r'''{
  "docs/ASIE-BETA-EXECUTION-MASTER-PLAN-2026-09-09.md": "01a0b8b057cda6892567789f037e37d0b494a7254356b986cca89a85139f4ddb",
  "docs/FC20-12-F01A-DEFENSIVE-ENABLING-REGISTRATION-PROPOSAL-2026-10-01.md": "fc4861eb4019e9ae16aa9c50005aadbb9525b90de2ff14bc0b50b67fd87e4e49",
  "docs/FC20-12-F01A-APPROVAL-CONSUMPTION-SCOPE-REGISTRATION-2026-10-09.md": "7998049d78a7afd1096d149bb25b822131bb33e1b63e025b0203d2c7f11df8e4",
  "docs/FOUNDATION-COMPLETE-20-CORE-INTELLIGENCE-COMPLETION-PROGRAM-2026-07-29.md": "fda521c2ff483ade683f54a756a31d47b8d02209b82b7e0a8487c5df44b347e2",
  "docs/EKB/FOUNDATION-COMPLETE-20-PACKAGE-INDEX.md": "8bc042e84206fc8f5afa54ebcd07bc8ce1ce4440168f784932cc238a361b2758"
}''')
REVIEW_IDENTITY_RESUME_VIEW_MARKER = '<!-- F01A-REVIEW-IDENTITY-CONDITIONAL-RESUME-2026-10-12 -->'


def _validate_review_identity_resume_structure(record: dict, active_target: object) -> None:
    """RIRG-01/02/03/04: closed proposed structure, never an execution decision."""
    assert isinstance(record, dict), "invalid_defensive_record"
    assert set(record) == set(REVIEW_IDENTITY_RESUME_RECORD), "defensive_fields"
    if record != REVIEW_IDENTITY_RESUME_RECORD:
        raise AssertionError("defensive_record_mismatch")
    if json.dumps(record, sort_keys=True) != json.dumps(REVIEW_IDENTITY_RESUME_RECORD, sort_keys=True):
        raise AssertionError("review_identity_resume_literal_types")
    assert record["execution_authorized"] is True, "review_identity_resume_literal_flag"
    assert all(record[key] is False for key in (
        "network_authorized", "provider_activation_authorized", "deployment_authorized",
    )), "defensive_external_effect"
    assert active_target == DEFENSIVE_START_TARGET, "review_identity_resume_slot"
    subject = record["events"][12]["owner_resume_decision"]["subject"]
    assert subject["repair_scope"] == REVIEW_IDENTITY_REPAIR_SCOPE, "review_identity_resume_repair_scope"
    assert subject["execution_scope"] == REVIEW_IDENTITY_RESUME_EXECUTION_SCOPE, "review_identity_resume_execution_scope"
    assert subject["checkpoint"] == REVIEW_IDENTITY_STOP_EVENT, "review_identity_resume_checkpoint"
    assert subject["scope_extension"] == REVIEW_IDENTITY_SCOPE_EVENT, "review_identity_resume_scope_extension"
    assert subject["allowed_paths"] == REVIEW_IDENTITY_SCOPE_RECORD["allowed_paths"], "review_identity_resume_paths"
    assert subject["allowed_schema_operations"] == record["allowed_schema_operations"] == [INDEX_OPERATION], "review_identity_resume_operation"
    assert all(subject["execution_scope"][key] is False for key in (
        "live_database_authorized", "owner_database_authorized", "production_placement_accepted",
        "deployment_authorized", "application_pr_merge_authorized",
    )), "review_identity_resume_forbidden_effect"


def validate_review_identity_resume(record: dict, active_target: object) -> None:
    """RIRG-03/07: current admission needs the new real execution receipt and time."""
    _validate_review_identity_resume_structure(record, active_target)
    decision = record["events"][12]["owner_resume_decision"]
    url, timestamp = decision["record_url"], decision["recorded_at"]
    assert isinstance(url, str) and re.fullmatch(
        r"https://github\.com/alphasigma13579-lang/ASIE/pull/202#issuecomment-[0-9]+", url,
    ) and isinstance(timestamp, str) and re.fullmatch(
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z", timestamp,
    ), "review_identity_resume_execution_decision_missing"


def _review_identity_resume_historical_inverse(manifest: dict) -> dict:
    """RIRG-05: structure-only test history; never current admission authority."""
    restored = deepcopy(manifest)
    record = defensive_record(restored)
    _validate_review_identity_resume_structure(record, restored["execution_sequence"]["active_target"])
    assert record["events"].pop() == REVIEW_IDENTITY_RESUME_EVENT
    record["execution_authorized"] = False
    source = (json.dumps(restored, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    assert git_blob_sha(source) == "ef142b9a2c2001e0bea4d6068b0f36d5c44c5a4c", "review_identity_resume_baseline_mismatch"
    validate_review_identity_scope(record, restored["execution_sequence"]["active_target"])
    return restored


def validate_review_identity_resume_baseline(manifest: dict) -> dict:
    """RIRG-05/07: real current admission is mandatory before the public inverse."""
    validate_review_identity_resume(defensive_record(manifest), manifest["execution_sequence"]["active_target"])
    return _review_identity_resume_historical_inverse(manifest)


def historical_review_identity_scope_manifest() -> dict:
    """Verified twelve-event historical fixture, not a current authority fallback."""
    return _review_identity_resume_historical_inverse(historical_review_identity_resume_manifest())


def review_identity_resume_historical_view(source_bytes: bytes, relative_path: str) -> bytes:
    """RIRG-06: raw historical prefix and path-bound exact terminal projection."""
    assert isinstance(source_bytes, bytes), "review_identity_resume_view_source_bytes"
    assert relative_path in REVIEW_IDENTITY_RESUME_VIEW_SHA256, "review_identity_resume_view_path"
    marker = REVIEW_IDENTITY_RESUME_VIEW_MARKER.encode("utf-8")
    separator = b"\n" + marker + b"\n"
    assert source_bytes.count(marker) == 1, "review_identity_resume_view_marker"
    assert source_bytes.count(separator) == 1, "review_identity_resume_view_boundary"
    prefix, section = source_bytes.split(separator, 1)
    assert git_blob_sha(prefix) == REVIEW_IDENTITY_RESUME_VIEW_PREFIX_BLOBS[relative_path], "review_identity_resume_view_prefix_changed"
    assert hashlib.sha256(marker + b"\n" + section).hexdigest() == REVIEW_IDENTITY_RESUME_VIEW_SHA256[relative_path], "review_identity_resume_view_projection_changed"
    review_identity_historical_view(prefix, relative_path)
    return prefix


def test_review_identity_resume_structural_inverse_preserves_all_twelve_events() -> None:
    """RIRG-01/02/05: establish exact history independently of current admission."""
    manifest = historical_review_identity_resume_manifest()
    record = defensive_record(manifest)
    _validate_review_identity_resume_structure(record, manifest["execution_sequence"]["active_target"])
    assert len(record["events"]) == 13
    assert record["events"][:12] == REVIEW_IDENTITY_SCOPE_RECORD["events"]
    event = record["events"][12]
    for target in (event, event["owner_resume_decision"]["subject"]):
        assert target["checkpoint"] == record["events"][10]
        assert target["scope_extension"] == record["events"][11]
    assert record["allowed_paths"] == REVIEW_IDENTITY_SCOPE_RECORD["allowed_paths"]
    assert len(record["allowed_paths"]) == 9
    assert record["allowed_schema_operations"] == [INDEX_OPERATION]
    assert manifest["execution_sequence"]["held_packages"] == HELD_PACKAGES
    assert active_execution_targets(manifest["packages"], {"FC20-05"}) == ["FC20-12/f01a_defensive_ingress"]
    stopped = _review_identity_resume_historical_inverse(manifest)
    previous = validate_review_identity_scope_baseline(stopped)
    index_scope = validate_index_resume_baseline(previous)
    consumption_resume = validate_index_scope_baseline(index_scope)
    consumption_scope = validate_consumption_resume_baseline(consumption_resume)
    old_resume = validate_consumption_scope_baseline(consumption_scope)
    validate_scope_extension_baseline(validate_resume_baseline(old_resume))


def test_review_identity_resume_current_admission_requires_real_execution_decision() -> None:
    """RIRG-07: the actual pinned conditional decision and every current gate are required."""
    manifest = historical_review_identity_resume_manifest()
    validate_review_identity_resume_baseline(manifest)
    validate_review_identity_resume(defensive_record(manifest), manifest["execution_sequence"]["active_target"])


def test_review_identity_resume_missing_execution_decision_blocks_all_current_seams() -> None:
    """RIRG-07: neither unresolved receipt nor time replaces the pinned decision."""
    for field, value in (
        ("record_url", "UNRESOLVED_OWNER_EXECUTION_DECISION_RECORD_URL"),
        ("recorded_at", "UNRESOLVED_OWNER_EXECUTION_DECISION_TIME"),
    ):
        manifest = historical_review_identity_resume_manifest()
        defensive_record(manifest)["events"][12]["owner_resume_decision"][field] = value
        for validator in (validate_review_identity_resume_baseline,):
            with pytest.raises(AssertionError, match="defensive_record_mismatch"):
                validator(manifest)


@pytest.mark.parametrize("field", tuple(REVIEW_IDENTITY_RESUME_EVENT))
def test_review_identity_resume_requires_all_event_fields(field: str) -> None:
    """RIRG-03: no partial evidence can become a new resume decision."""
    manifest = historical_review_identity_resume_manifest()
    defensive_record(manifest)["events"][12].pop(field)
    with pytest.raises(AssertionError, match="defensive_record_mismatch"):
        _validate_review_identity_resume_structure(defensive_record(manifest), manifest["execution_sequence"]["active_target"])



@pytest.mark.parametrize("path", index_resume_leaf_paths(REVIEW_IDENTITY_RESUME_EVENT))
def test_review_identity_resume_pins_every_evidence_leaf(path: list) -> None:
    """RIRG-03: independently pin receipt, timestamps, baselines and nested copies."""
    manifest = historical_review_identity_resume_manifest()
    target = defensive_record(manifest)["events"][12]
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = "[unreviewed]"
    with pytest.raises(AssertionError, match="defensive_record_mismatch"):
        _validate_review_identity_resume_structure(defensive_record(manifest), manifest["execution_sequence"]["active_target"])


@pytest.mark.parametrize("field", tuple(REVIEW_IDENTITY_RESUME_EXECUTION_SCOPE))
@pytest.mark.parametrize("mutation", ("missing", "changed"))
def test_review_identity_resume_requires_closed_limited_execution_scope(field: str, mutation: str) -> None:
    """RIRG-03/08: remove or broaden any restriction and admission fails."""
    manifest = historical_review_identity_resume_manifest()
    scope = defensive_record(manifest)["events"][12]["owner_resume_decision"]["subject"]["execution_scope"]
    if mutation == "missing":
        scope.pop(field)
    else:
        scope[field] = True if field.endswith(("authorized", "accepted")) else "UNRESTRICTED"
    with pytest.raises(AssertionError, match="defensive_record_mismatch"):
        _validate_review_identity_resume_structure(defensive_record(manifest), manifest["execution_sequence"]["active_target"])


@pytest.mark.parametrize("field", ("live_database_authorized", "owner_database_authorized", "production_placement_accepted", "deployment_authorized", "application_pr_merge_authorized"))
@pytest.mark.parametrize("value", (0, 1, "false", None))
def test_review_identity_resume_scope_requires_literal_booleans(field: str, value: object) -> None:
    """RIRG-03/08: false-like metadata never substitutes for explicit prohibitions."""
    manifest = historical_review_identity_resume_manifest()
    defensive_record(manifest)["events"][12]["owner_resume_decision"]["subject"]["execution_scope"][field] = value
    with pytest.raises(AssertionError):
        _validate_review_identity_resume_structure(defensive_record(manifest), manifest["execution_sequence"]["active_target"])


@pytest.mark.parametrize("mutation", ("unknown", "extra_activity", "extra_path", "path_order", "real_data", "live_database", "startup_approved", "recovery_approved", "changed_query", "empty_scope"))
def test_review_identity_resume_never_interprets_true_as_general_execution(mutation: str) -> None:
    """RIRG-08: an otherwise exact true record cannot authorize broader work."""
    manifest = historical_review_identity_resume_manifest()
    subject = defensive_record(manifest)["events"][12]["owner_resume_decision"]["subject"]
    scope = subject["execution_scope"]
    if mutation == "unknown":
        scope["trusted_override"] = True
    elif mutation == "extra_activity":
        scope["activities"].append("DEPLOY")
    elif mutation == "extra_path":
        scope["implementation_paths"].append("backend/asie_local_api.py")
    elif mutation == "path_order":
        scope["implementation_paths"].reverse()
    elif mutation == "real_data":
        scope["data_scope"] = "OWNER_DATA"
    elif mutation == "live_database":
        scope["database_scope"] = "OWNER_DATABASE"
    elif mutation == "startup_approved":
        scope["startup_criteria_status"] = "APPROVED"
    elif mutation == "recovery_approved":
        scope["maintenance_recovery_acceptance"] = "APPROVED"
    elif mutation == "changed_query":
        scope["query_and_proof_semantics"] = "REPLACED"
    else:
        subject["execution_scope"] = {}
    with pytest.raises(AssertionError, match="defensive_record_mismatch"):
        _validate_review_identity_resume_structure(defensive_record(manifest), manifest["execution_sequence"]["active_target"])


@pytest.mark.parametrize("mutation", ("old_resume", "scope_decision", "preparation_effect", "missing_condition", "new_branch_baseline", "old_checkpoint_baseline", "unknown_decision", "unknown_subject", "duplicate_resume"))
def test_review_identity_resume_rejects_reused_or_ambiguous_authority(mutation: str) -> None:
    """RIRG-03/07: design, publication, scope or merge approvals are not this decision."""
    manifest = historical_review_identity_resume_manifest()
    record = defensive_record(manifest)
    event = record["events"][12]
    if mutation == "old_resume":
        event["owner_resume_decision"] = deepcopy(CONSUMPTION_RESUME_DECISION)
    elif mutation == "scope_decision":
        event["owner_resume_decision"] = deepcopy(REVIEW_IDENTITY_SCOPE_DECISION)
    elif mutation == "preparation_effect":
        event["owner_resume_decision"]["effect"] = "PREPARE_GOVERNANCE_PR_ONLY_NO_MERGE_NO_RESUME"
    elif mutation == "missing_condition":
        event["owner_resume_decision"].pop("condition")
    elif mutation == "new_branch_baseline":
        event["baseline_commit_sha"] = "63b18a192e8eac3c66ad5440a667e6d1d9959d10"
    elif mutation == "old_checkpoint_baseline":
        event["baseline_commit_sha"] = REVIEW_IDENTITY_STOP_EVENT["baseline_commit_sha"]
        event["baseline_manifest_blob_sha"] = REVIEW_IDENTITY_STOP_EVENT["baseline_manifest_blob_sha"]
    elif mutation == "unknown_decision":
        event["owner_resume_decision"]["approved"] = True
    elif mutation == "unknown_subject":
        event["owner_resume_decision"]["subject"]["override"] = True
    else:
        record["events"].append(deepcopy(event))
    with pytest.raises(AssertionError, match="defensive_record_mismatch"):
        _validate_review_identity_resume_structure(defensive_record(manifest), manifest["execution_sequence"]["active_target"])


@pytest.mark.parametrize("index", range(13))
@pytest.mark.parametrize("mutation", ("delete", "duplicate", "change", "reorder"))
def test_review_identity_resume_preserves_each_event(index: int, mutation: str) -> None:
    """RIRG-02: every historical or current event is required in its exact position."""
    manifest = historical_review_identity_resume_manifest()
    events = defensive_record(manifest)["events"]
    if mutation == "delete":
        events.pop(index)
    elif mutation == "duplicate":
        events.insert(index, deepcopy(events[index]))
    elif mutation == "change":
        events[index]["type"] = "OVERRIDE"
    else:
        other = (index + 1) % len(events)
        events[index], events[other] = events[other], events[index]
    with pytest.raises(AssertionError, match="defensive_record_mismatch"):
        _validate_review_identity_resume_structure(defensive_record(manifest), manifest["execution_sequence"]["active_target"])


@pytest.mark.parametrize("field,value", (("execution_authorized", False), ("execution_authorized", 1), ("execution_authorized", "true"), ("state", "DELIVERED"), ("delivery_evidence", {"passed": True}), ("closure_effect", "COMPLETE"), ("environment", "LIVE"), ("network_authorized", 0), ("network_authorized", True), ("provider_activation_authorized", True), ("deployment_authorized", True)))
def test_review_identity_resume_requires_literal_flags_and_no_terminal_effects(field: str, value: object) -> None:
    """RIRG-04/08: no implicit Boolean authority, completion or external activation."""
    manifest = historical_review_identity_resume_manifest()
    defensive_record(manifest)[field] = value
    with pytest.raises(AssertionError):
        _validate_review_identity_resume_structure(defensive_record(manifest), manifest["execution_sequence"]["active_target"])


@pytest.mark.parametrize("record", (DEFENSIVE_REGISTRATION, DEFENSIVE_START_RECORD, DEFENSIVE_STOP_RECORD, DEFENSIVE_SCOPE_EXTENSION_RECORD, DEFENSIVE_RESUME_RECORD, CONSUMPTION_SCOPE_RECORD, CONSUMPTION_RESUME_RECORD, INDEX_SCOPE_RECORD, INDEX_RESUME_RECORD, REVIEW_IDENTITY_SCOPE_RECORD, lifecycle_fixture()[0]))
def test_review_identity_resume_never_admits_any_historical_or_fixture_state(record: dict) -> None:
    """RIRG-07: only the new exact conditional decision is current authority."""
    with pytest.raises(AssertionError):
        _validate_review_identity_resume_structure(deepcopy(record), DEFENSIVE_START_TARGET)


@pytest.mark.parametrize("mutation", ("root", "rule", "package", "dependency", "hold", "limit", "frozen", "routing", "release"))
def test_review_identity_resume_full_inverse_rejects_every_unrelated_delta(mutation: str) -> None:
    """RIRG-05: seal the full manifest, not only a convenient authority subset."""
    manifest = historical_review_identity_resume_manifest()
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
    elif mutation == "limit":
        manifest["execution_sequence"]["max_active_executions"] = 2
    elif mutation == "frozen":
        manifest["frozen_files"].append("backend/unknown.py")
    elif mutation == "routing":
        packages["FC20-12"]["execution_slices"][0]["required_entry_controls"]["single_active_execution"]["status"] = "PASS"
    else:
        manifest["public_release_authorized"] = True
    with pytest.raises(AssertionError, match="review_identity_resume_baseline_mismatch"):
        _review_identity_resume_historical_inverse(manifest)


@pytest.mark.parametrize("slot", (None, {}, {"kind": "package", "package_id": "FC20-05"}))
def test_review_identity_resume_retains_single_counted_slot(slot: object) -> None:
    """RIRG-04: resume retains the same slot and cannot hand it to held work."""
    manifest = historical_review_identity_resume_manifest()
    manifest["execution_sequence"]["active_target"] = slot
    with pytest.raises(AssertionError):
        _validate_review_identity_resume_structure(defensive_record(manifest), manifest["execution_sequence"]["active_target"])


@pytest.mark.parametrize("relative_path", tuple(REVIEW_IDENTITY_RESUME_VIEW_SHA256))
def test_review_identity_resume_preserves_all_historical_projection_seals(relative_path: str) -> None:
    """RIRG-06: full prior documents and every old oracle stay independently sealed."""
    source = key_binding_historical_view(key_binding_resume_historical_view(recovery_scope_historical_view(recovery_resume_historical_view(dataset_scope_historical_view(dataset_resume_historical_view(overlay_scope_historical_view(overlay_resume_historical_view(ci_scope_historical_view(ci_resume_historical_view(ci_amend_historical_view((Path(__file__).resolve().parents[1] / relative_path).read_bytes(), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path)
    prefix = review_identity_resume_historical_view(source, relative_path)
    review_identity_historical_view(prefix, relative_path)
    assert set(REVIEW_IDENTITY_RESUME_VIEW_SHA256) == set(REVIEW_IDENTITY_RESUME_VIEW_PREFIX_BLOBS) == set(REVIEW_IDENTITY_VIEW_SHA256)


@pytest.mark.parametrize("relative_path", tuple(REVIEW_IDENTITY_RESUME_VIEW_SHA256))
@pytest.mark.parametrize("mutation", ("missing_marker", "duplicate_marker", "separator", "prefix", "prefix_crlf", "whole_crlf", "section_crlf", "suffix", "comment", "trailing_blank_line", "missing_final_newline", "live_authority", "startup_approved", "data_scope", "scope_order"))
def test_review_identity_resume_projection_rejects_unreviewed_bytes(relative_path: str, mutation: str) -> None:
    """RIRG-06/08: exact terminal bytes, including every restricted-execution claim."""
    source = key_binding_historical_view(key_binding_resume_historical_view(recovery_scope_historical_view(recovery_resume_historical_view(dataset_scope_historical_view(dataset_resume_historical_view(overlay_scope_historical_view(overlay_resume_historical_view(ci_scope_historical_view(ci_resume_historical_view(ci_amend_historical_view((Path(__file__).resolve().parents[1] / relative_path).read_bytes(), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path)
    marker = REVIEW_IDENTITY_RESUME_VIEW_MARKER.encode(); separator = b"\n" + marker + b"\n"
    prefix, section = source.split(separator, 1)
    if mutation == "missing_marker":
        tampered = source.replace(marker, b"", 1)
    elif mutation == "duplicate_marker":
        tampered = source + separator
    elif mutation == "separator":
        tampered = source.replace(separator, b"\n\n" + marker + b"\n", 1)
    elif mutation == "prefix":
        tampered = b"edited\n" + source
    elif mutation == "prefix_crlf":
        tampered = prefix.replace(b"\n", b"\r\n") + separator + section
    elif mutation == "whole_crlf":
        tampered = source.replace(b"\n", b"\r\n")
    elif mutation == "section_crlf":
        tampered = prefix + separator + section.replace(b"\n", b"\r\n")
    elif mutation in ("suffix", "comment", "trailing_blank_line"):
        tampered = source + {"suffix": b"\n### Override\n", "comment": b"\n<!-- override -->\n", "trailing_blank_line": b"\n"}[mutation]
    elif mutation == "missing_final_newline":
        tampered = source.removesuffix(b"\n")
    elif mutation == "scope_order":
        first, second = (f"- `{p}`\n".encode() for p in REVIEW_IDENTITY_SCOPE_RECORD["allowed_paths"][:2])
        tampered = prefix + separator + section.replace(first + second, second + first)
    else:
        old, new = {"live_authority": (b"live_database_authorized=false", b"live_database_authorized=true"), "startup_approved": (b"startup_criteria_status=UNKNOWN_NOT_APPROVED", b"startup_criteria_status=APPROVED"), "data_scope": (b"SYNTHETIC_DATA_ONLY", b"OWNER_DATA")}[mutation]
        tampered = prefix + separator + section.replace(old, new)
    assert tampered != source
    with pytest.raises(AssertionError, match="review_identity_resume_view_"):
        review_identity_resume_historical_view(tampered, relative_path)


@pytest.mark.parametrize("relative_path", tuple(REVIEW_IDENTITY_RESUME_VIEW_SHA256))
def test_review_identity_resume_rejects_cross_path_projection_transplants(relative_path: str) -> None:
    """RIRG-06: authentic content from another path cannot borrow this path's seal."""
    root = Path(__file__).resolve().parents[1]
    other = next(p for p in REVIEW_IDENTITY_RESUME_VIEW_SHA256 if p != relative_path)
    source, other_source = key_binding_historical_view(key_binding_resume_historical_view(recovery_scope_historical_view(recovery_resume_historical_view(dataset_scope_historical_view(dataset_resume_historical_view(overlay_scope_historical_view(overlay_resume_historical_view(ci_scope_historical_view(ci_resume_historical_view(ci_amend_historical_view((root / relative_path).read_bytes(), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), key_binding_historical_view(key_binding_resume_historical_view(recovery_scope_historical_view(recovery_resume_historical_view(dataset_scope_historical_view(dataset_resume_historical_view(overlay_scope_historical_view(overlay_resume_historical_view(ci_scope_historical_view(ci_resume_historical_view(ci_amend_historical_view((root / other).read_bytes(), other), other), other), other), other), other), other), other), other), other), other)
    separator = ("\n" + REVIEW_IDENTITY_RESUME_VIEW_MARKER + "\n").encode()
    with pytest.raises(AssertionError, match="review_identity_resume_view_prefix_changed"):
        review_identity_resume_historical_view(other_source, relative_path)
    with pytest.raises(AssertionError, match="review_identity_resume_view_projection_changed"):
        review_identity_resume_historical_view(source.split(separator, 1)[0] + separator + other_source.split(separator, 1)[1], relative_path)


@pytest.mark.parametrize("path", ("", "docs/unapproved.md", "backend/repository.py"))
def test_review_identity_resume_projection_has_no_default_path(path: str) -> None:
    """RIRG-06: no fallback seal is accepted for unregistered documents."""
    source = key_binding_historical_view(key_binding_resume_historical_view(recovery_scope_historical_view(recovery_resume_historical_view(dataset_scope_historical_view(dataset_resume_historical_view(overlay_scope_historical_view(overlay_resume_historical_view(ci_scope_historical_view(ci_resume_historical_view(ci_amend_historical_view((Path(__file__).resolve().parents[1] / CONSUMPTION_VIEW_PATHS[0]).read_bytes(), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0])
    with pytest.raises(AssertionError, match="review_identity_resume_view_path"):
        review_identity_resume_historical_view(source, path)


def test_review_identity_resume_requires_raw_view_bytes_and_preserves_reviewed_design() -> None:
    """RIRG-06/08: source bytes and immutable design remain independent evidence."""
    root = Path(__file__).resolve().parents[1]
    path = CONSUMPTION_VIEW_PATHS[0]
    with pytest.raises(AssertionError, match="review_identity_resume_view_source_bytes"):
        review_identity_resume_historical_view((root / path).read_text(), path)
    assert git_blob_sha((root / "docs/FC20-12-F01A-REVIEW-IDENTITY-SCOPE-PROPOSAL-2026-10-11.md").read_bytes()) == "7aa270286535f831a8eac25170ee495043b40bf5", "review_identity_resume_design_changed"


@pytest.mark.parametrize("container,keys", (("decision", tuple(REVIEW_IDENTITY_RESUME_DECISION)), ("subject", tuple(REVIEW_IDENTITY_RESUME_DECISION["subject"]))))
def test_review_identity_resume_requires_each_decision_and_subject_field(container: str, keys: tuple) -> None:
    """RIRG-03: complete receipt and exact subject are mandatory, not optional metadata."""
    for field in keys:
        manifest = historical_review_identity_resume_manifest()
        target = defensive_record(manifest)["events"][12]["owner_resume_decision"]
        if container == "subject":
            target = target["subject"]
        target.pop(field)
        with pytest.raises(AssertionError, match="defensive_record_mismatch"):
            _validate_review_identity_resume_structure(defensive_record(manifest), manifest["execution_sequence"]["active_target"])


@pytest.mark.parametrize("path", [p for p in index_resume_leaf_paths(REVIEW_IDENTITY_RESUME_RECORD) if p[-1] == "unique"])
@pytest.mark.parametrize("value", (0, 1, "false", None))
def test_review_identity_resume_operation_booleans_are_literal_in_every_copy(path: list, value: object) -> None:
    """RIRG-03: copied historical and current operations reject false-like integers."""
    manifest = historical_review_identity_resume_manifest()
    target = defensive_record(manifest)
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(AssertionError):
        _validate_review_identity_resume_structure(defensive_record(manifest), manifest["execution_sequence"]["active_target"])



def test_review_identity_resume_nested_operation_mutation_inventory_is_nonempty() -> None:
    """RIRG-03: a list-blind enumerator must not silently skip operation copies."""
    paths = [p for p in index_resume_leaf_paths(REVIEW_IDENTITY_RESUME_RECORD) if p[-1] == "unique"]
    assert ("allowed_schema_operations", 0, "unique") in paths
    assert ("events", 12, "owner_resume_decision", "subject", "allowed_schema_operations", 0, "unique") in paths
    assert len(paths) >= 3


@pytest.mark.parametrize("field", tuple(REVIEW_IDENTITY_REPAIR_SCOPE))
@pytest.mark.parametrize("mutation", ("missing", "changed"))
def test_review_identity_resume_pins_each_registered_repair_scope_field(field: str, mutation: str) -> None:
    """RIRG-03/08: the implementation subject is exactly the registered repair."""
    record = deepcopy(REVIEW_IDENTITY_RESUME_RECORD)
    scope = record["events"][12]["owner_resume_decision"]["subject"]["repair_scope"]
    if mutation == "missing":
        scope.pop(field)
    else:
        scope[field] = "UNRESTRICTED"
    with pytest.raises(AssertionError, match="defensive_record_mismatch"):
        _validate_review_identity_resume_structure(record, DEFENSIVE_START_TARGET)


@pytest.mark.parametrize("mutation", ("index_activities", "preparation_receipt", "preparation_time", "extra_repair_field", "extra_schema", "wrong_design", "wrong_application", "extra_implementation_path"))
def test_review_identity_resume_never_reuses_index_or_preparation_authority(mutation: str) -> None:
    """RIRG-07/08: preservation of prior index metadata grants no new index work."""
    record = deepcopy(REVIEW_IDENTITY_RESUME_RECORD)
    decision = record["events"][12]["owner_resume_decision"]
    subject = decision["subject"]
    if mutation == "index_activities":
        subject["execution_scope"]["activities"] = deepcopy(INDEX_RESUME_EXECUTION_SCOPE["activities"])
    elif mutation == "preparation_receipt":
        decision["record_url"] = REVIEW_IDENTITY_SCOPE_DECISION["record_url"]
    elif mutation == "preparation_time":
        decision["recorded_at"] = "2026-10-12T08:47:04Z"
    elif mutation == "extra_repair_field":
        subject["repair_scope"]["trusted_override"] = True
    elif mutation == "extra_schema":
        subject["repair_scope"]["additional_schema_operations"].append(deepcopy(INDEX_OPERATION))
    elif mutation == "wrong_design":
        decision["proposal_commit_sha"] = INDEX_RESUME_DECISION["proposal_commit_sha"]
    elif mutation == "wrong_application":
        subject["application_head_sha"] = subject["baseline_commit_sha"]
    else:
        subject["execution_scope"]["implementation_paths"].append("backend/asie_local_api.py")
    with pytest.raises(AssertionError, match="defensive_record_mismatch"):
        _validate_review_identity_resume_structure(record, DEFENSIVE_START_TARGET)


# KBSG: stopped key/fingerprint consistency registration; publication is not execution authority.
KEY_BINDING_REPAIR_SCOPE = json.loads(r'''{
  "purpose": "STORED_CONTEXT_KEY_FINGERPRINT_BINDING_ONLY",
  "implementation_paths": [
    "backend/repository.py",
    "tests/test_repository_intelligence.py"
  ],
  "boundary": "EXISTING_SHARED_STORED_CONTEXT_VALIDATOR",
  "validation": "RECOMPUTE_EXISTING_FINGERPRINT_FROM_TYPED_EXACT_STORED_ORG_PROJECT_KEY",
  "affected_gates": [
    "VALIDATED_CONTEXT_CONSUMPTION_READ",
    "TRANSACTIONAL_REVIEW_SAVE",
    "TRANSACTIONAL_APPROVAL_SAVE"
  ],
  "compatibility": "REJECT_INCONSISTENT_BINDING_WITHOUT_REWRITE_OR_BACKFILL",
  "historical_read_and_origin_proof_policy": "UNCHANGED",
  "native_context_hash_and_fingerprint_function": "UNCHANGED",
  "additional_schema_operations": [],
  "database_and_data_scope": "DISPOSABLE_TEMPORARY_DATABASES_SYNTHETIC_DATA_ONLY"
}''')
KEY_BINDING_STOP_EVENT = json.loads(r'''{
  "type": "STOP_CHECKPOINT",
  "recorded_at": "2026-10-12T16:08:54Z",
  "baseline_commit_sha": "3d95c5443ef18b59bf42132f3df67c6c12d00bc4",
  "baseline_manifest_blob_sha": "76b6d5b5892cf3a839f3fde95c04ff7ee366923f",
  "application_head_sha": "4fcb8b47971a8ee55fa0ae95f5928bdd5722890a",
  "reason": "STORED_KEY_FINGERPRINT_BINDING_OUTSIDE_EXISTING_VALIDATOR_REUSE_RESUME",
  "evidence": {
    "url": "https://github.com/alphasigma13579-lang/ASIE/blob/8d512f0123cf81332de306c9b1b60ee12defa906/ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/docs/FC20-12-F01A-KEY-FINGERPRINT-SCOPE-PROPOSAL-2026-10-12.md",
    "commit_sha": "8d512f0123cf81332de306c9b1b60ee12defa906",
    "blob_sha": "c932029f3c64ba0473596947e42ae1bdc1fcd51f"
  },
  "resume_requirement": "NEW_OWNER_DECISION_BOUND_TO_KEY_FINGERPRINT_BINDING_COMPATIBILITY_AND_REVIEWED_EXACT_HEAD_GOVERNANCE_TRANSITION"
}''')
KEY_BINDING_SCOPE_DECISION = json.loads(r'''{
  "id": "DECISION-FC20-12-F01A-KEY-FINGERPRINT-SCOPE-REGISTRATION-PREPARATION-2026-10-12",
  "record_url": "https://github.com/alphasigma13579-lang/ASIE/pull/204#issuecomment-6128022293",
  "recorded_at": "2026-10-12T16:06:58Z",
  "effect": "PREPARE_AND_PUBLISH_GOVERNANCE_DRAFT_ONLY_NO_MERGE_NO_RESUME",
  "subject": {
    "baseline_commit_sha": "3d95c5443ef18b59bf42132f3df67c6c12d00bc4",
    "baseline_manifest_blob_sha": "76b6d5b5892cf3a839f3fde95c04ff7ee366923f",
    "application_head_sha": "4fcb8b47971a8ee55fa0ae95f5928bdd5722890a",
    "allowed_paths": [
      "backend/asie_local_api.py",
      "backend/repository.py",
      "backend/intelligence_prerun_service.py",
      "tests/test_repository_intelligence.py",
      "tests/test_intelligence_prerun_service.py",
      "tests/test_intelligence_context_ingress_api.py",
      "docs/FC20-12-F01-TRUSTED-CONTEXT-INGRESS-REPAIR-PLAN-2026-10-01.md",
      "tests/test_live_location_api.py",
      "tests/test_intelligence_consumption.py"
    ],
    "allowed_schema_operations": [
      {
        "operation": "CREATE_INDEX_IF_NOT_EXISTS",
        "index_name": "idx_security_audit_origin_proof",
        "table": "security_audit_events",
        "columns": [
          "action",
          "target_type",
          "target_id",
          "organization_id"
        ],
        "unique": false,
        "implementation_path": "backend/repository.py",
        "test_path": "tests/test_repository_intelligence.py"
      }
    ],
    "repair_scope": {
      "purpose": "STORED_CONTEXT_KEY_FINGERPRINT_BINDING_ONLY",
      "implementation_paths": [
        "backend/repository.py",
        "tests/test_repository_intelligence.py"
      ],
      "boundary": "EXISTING_SHARED_STORED_CONTEXT_VALIDATOR",
      "validation": "RECOMPUTE_EXISTING_FINGERPRINT_FROM_TYPED_EXACT_STORED_ORG_PROJECT_KEY",
      "affected_gates": [
        "VALIDATED_CONTEXT_CONSUMPTION_READ",
        "TRANSACTIONAL_REVIEW_SAVE",
        "TRANSACTIONAL_APPROVAL_SAVE"
      ],
      "compatibility": "REJECT_INCONSISTENT_BINDING_WITHOUT_REWRITE_OR_BACKFILL",
      "historical_read_and_origin_proof_policy": "UNCHANGED",
      "native_context_hash_and_fingerprint_function": "UNCHANGED",
      "additional_schema_operations": [],
      "database_and_data_scope": "DISPOSABLE_TEMPORARY_DATABASES_SYNTHETIC_DATA_ONLY"
    }
  },
  "proposal_commit_sha": "8d512f0123cf81332de306c9b1b60ee12defa906",
  "proposal_blob_sha": "c932029f3c64ba0473596947e42ae1bdc1fcd51f"
}''')
KEY_BINDING_SCOPE_DECISION["subject"]["baseline_record"] = deepcopy(REVIEW_IDENTITY_RESUME_RECORD)
KEY_BINDING_SCOPE_DECISION["subject"]["previous_resume"] = deepcopy(REVIEW_IDENTITY_RESUME_EVENT)
KEY_BINDING_SCOPE_EVENT = json.loads(r'''{
  "type": "SCOPE_EXTENSION",
  "recorded_at": "2026-10-12T16:08:54Z",
  "baseline_commit_sha": "3d95c5443ef18b59bf42132f3df67c6c12d00bc4",
  "baseline_manifest_blob_sha": "76b6d5b5892cf3a839f3fde95c04ff7ee366923f",
  "application_head_sha": "4fcb8b47971a8ee55fa0ae95f5928bdd5722890a",
  "added_paths": [],
  "scope_addendum": {
    "url": "https://github.com/alphasigma13579-lang/ASIE/blob/8d512f0123cf81332de306c9b1b60ee12defa906/ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/docs/FC20-12-F01A-KEY-FINGERPRINT-SCOPE-PROPOSAL-2026-10-12.md",
    "commit_sha": "8d512f0123cf81332de306c9b1b60ee12defa906",
    "blob_sha": "c932029f3c64ba0473596947e42ae1bdc1fcd51f"
  },
  "effect": "SCOPE_EXTENSION_ONLY_NO_RESUME"
}''')
KEY_BINDING_SCOPE_EVENT["owner_scope_decision"] = deepcopy(KEY_BINDING_SCOPE_DECISION)
KEY_BINDING_SCOPE_RECORD = deepcopy(REVIEW_IDENTITY_RESUME_RECORD)
KEY_BINDING_SCOPE_RECORD["execution_authorized"] = False
KEY_BINDING_SCOPE_RECORD["events"].extend([deepcopy(KEY_BINDING_STOP_EVENT), deepcopy(KEY_BINDING_SCOPE_EVENT)])
KEY_BINDING_VIEW_PREFIX_BLOBS = json.loads(r'''{
  "docs/ASIE-BETA-EXECUTION-MASTER-PLAN-2026-09-09.md": "533060fff7981577e42bd2f348ee81ab3cb01ec5",
  "docs/FC20-12-F01A-DEFENSIVE-ENABLING-REGISTRATION-PROPOSAL-2026-10-01.md": "71ca98ef669999161484f5cfbb601f8833519831",
  "docs/FC20-12-F01A-APPROVAL-CONSUMPTION-SCOPE-REGISTRATION-2026-10-09.md": "0e4db455dad290f7a1b47a0f860b27ba5d076c0d",
  "docs/FOUNDATION-COMPLETE-20-CORE-INTELLIGENCE-COMPLETION-PROGRAM-2026-07-29.md": "9a02be5614a42e91c02867f707cdcfaac6df7113",
  "docs/EKB/FOUNDATION-COMPLETE-20-PACKAGE-INDEX.md": "aa8cb66b653f239c30b21bda18fa9894ba59bf08"
}''')
KEY_BINDING_VIEW_SHA256 = json.loads(r'''{
  "docs/ASIE-BETA-EXECUTION-MASTER-PLAN-2026-09-09.md": "9799f251ff4ac34be56256c54be03b18f89fb3f92eef984dd946f5271a36c747",
  "docs/FC20-12-F01A-DEFENSIVE-ENABLING-REGISTRATION-PROPOSAL-2026-10-01.md": "65c07565912e87612325371f34944ef5be49c60eb4b568852dc2c3195a7d8be6",
  "docs/FC20-12-F01A-APPROVAL-CONSUMPTION-SCOPE-REGISTRATION-2026-10-09.md": "e9443c970436beb8c3a95257ca07b19199701d0c086f5b3e975693a1c68f4e53",
  "docs/FOUNDATION-COMPLETE-20-CORE-INTELLIGENCE-COMPLETION-PROGRAM-2026-07-29.md": "3ec7939c55be39398de423c5c88402f4a016886142e0e685599d8298caff1c3d",
  "docs/EKB/FOUNDATION-COMPLETE-20-PACKAGE-INDEX.md": "2630cc34b25f35083971e5a0b7fd92bd9c4c8b2148e1b4c7aeb00899197b8b22"
}''')
KEY_BINDING_VIEW_MARKER = '<!-- F01A-KEY-FINGERPRINT-SCOPE-REGISTRATION-2026-10-12 -->'


def _validate_key_binding_structure(record: dict, active_target: object) -> None:
    """KBSG-01/02/03/04: exact structure only; this does not admit a receipt."""
    assert isinstance(record, dict), "invalid_defensive_record"
    assert set(record) == set(KEY_BINDING_SCOPE_RECORD), "defensive_fields"
    assert record == KEY_BINDING_SCOPE_RECORD, "defensive_record_mismatch"
    literal_types_match = json.dumps(record, sort_keys=True) == json.dumps(KEY_BINDING_SCOPE_RECORD, sort_keys=True)
    assert literal_types_match, "key_binding_literal_types"
    assert record["execution_authorized"] is False, "key_binding_stop_flag"
    assert all(record[key] is False for key in (
        "network_authorized", "provider_activation_authorized", "deployment_authorized",
    )), "defensive_external_effect"
    assert active_target == DEFENSIVE_START_TARGET, "key_binding_slot"
    decision = record["events"][14]["owner_scope_decision"]
    assert decision == KEY_BINDING_SCOPE_DECISION, "key_binding_decision_mismatch"
    assert decision["subject"]["repair_scope"] == KEY_BINDING_REPAIR_SCOPE, "key_binding_repair_scope"
    assert decision["subject"]["baseline_record"] == REVIEW_IDENTITY_RESUME_RECORD, "key_binding_previous_record"
    assert decision["subject"]["previous_resume"] == REVIEW_IDENTITY_RESUME_EVENT, "key_binding_previous_resume"
    assert record["allowed_paths"] == REVIEW_IDENTITY_RESUME_RECORD["allowed_paths"], "key_binding_paths"
    assert record["allowed_schema_operations"] == [INDEX_OPERATION], "key_binding_schema_operation"
    assert record["allowed_schema_operations"][0]["unique"] is False, "key_binding_operation_literal"
    assert record["events"][14]["added_paths"] == [], "key_binding_added_paths"
    assert "added_schema_operations" not in record["events"][14], "key_binding_no_added_schema"


def validate_key_binding_scope(record: dict, active_target: object) -> None:
    """KBSG-03/07: current admission requires a real, independently pinned receipt."""
    _validate_key_binding_structure(record, active_target)
    receipt = record["events"][14]["owner_scope_decision"]["record_url"]
    assert isinstance(receipt, str) and re.fullmatch(
        r"https://github\.com/alphasigma13579-lang/ASIE/pull/204#issuecomment-[0-9]+", receipt,
    ), "key_binding_receipt_missing_or_invalid"


def _key_binding_historical_inverse(manifest: dict) -> dict:
    """KBSG-05: structure-only test history; NEVER current admission authority."""
    restored = deepcopy(manifest)
    record = defensive_record(restored)
    _validate_key_binding_structure(record, restored["execution_sequence"]["active_target"])
    assert record["events"].pop() == KEY_BINDING_SCOPE_EVENT
    assert record["events"].pop() == KEY_BINDING_STOP_EVENT
    record["execution_authorized"] = True
    source = (json.dumps(restored, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    assert git_blob_sha(source) == "76b6d5b5892cf3a839f3fde95c04ff7ee366923f", "key_binding_baseline_mismatch"
    validate_review_identity_resume(record, restored["execution_sequence"]["active_target"])
    return restored


def validate_key_binding_scope_baseline(manifest: dict) -> dict:
    """KBSG-05/07: require real current admission before validating its full inverse."""
    validate_key_binding_scope(defensive_record(manifest), manifest["execution_sequence"]["active_target"])
    return _key_binding_historical_inverse(manifest)


def historical_review_identity_resume_manifest() -> dict:
    """Verified thirteen-event test history only; never accepts the current proposal."""
    return _key_binding_historical_inverse(historical_key_binding_scope_manifest())


def key_binding_historical_view(source_bytes: bytes, relative_path: str) -> bytes:
    """KBSG-06: exact raw historical prefix and one path-bound terminal section."""
    assert isinstance(source_bytes, bytes), "key_binding_view_source_bytes"
    assert relative_path in KEY_BINDING_VIEW_SHA256, "key_binding_view_path"
    marker = KEY_BINDING_VIEW_MARKER.encode("utf-8")
    separator = b"\n" + marker + b"\n"
    assert source_bytes.count(marker) == 1, "key_binding_view_marker"
    assert source_bytes.count(separator) == 1, "key_binding_view_boundary"
    prefix, section = source_bytes.split(separator, 1)
    assert git_blob_sha(prefix) == KEY_BINDING_VIEW_PREFIX_BLOBS[relative_path], "key_binding_view_prefix_changed"
    assert hashlib.sha256(marker + b"\n" + section).hexdigest() == KEY_BINDING_VIEW_SHA256[relative_path], "key_binding_view_projection_changed"
    review_identity_resume_historical_view(prefix, relative_path)
    return prefix


def test_key_binding_structural_inverse_preserves_all_thirteen_events_and_oracles() -> None:
    """KBSG-01/02/05: structural success is not real-receipt admission."""
    manifest = historical_key_binding_scope_manifest()
    record = defensive_record(manifest)
    _validate_key_binding_structure(record, manifest["execution_sequence"]["active_target"])
    assert len(record["events"]) == 15
    assert record["events"][:13] == REVIEW_IDENTITY_RESUME_RECORD["events"]
    assert record["allowed_paths"] == REVIEW_IDENTITY_RESUME_RECORD["allowed_paths"]
    assert len(record["allowed_paths"]) == 9
    assert record["allowed_schema_operations"] == [INDEX_OPERATION]
    assert record["execution_authorized"] is False
    assert manifest["execution_sequence"]["held_packages"] == HELD_PACKAGES
    assert active_execution_targets(manifest["packages"], {"FC20-05"}) == ["FC20-12/f01a_defensive_ingress"]
    baseline = _key_binding_historical_inverse(manifest)
    stopped_review = validate_review_identity_resume_baseline(baseline)
    previous_index = validate_review_identity_scope_baseline(stopped_review)
    index_scope = validate_index_resume_baseline(previous_index)
    consumption_resume = validate_index_scope_baseline(index_scope)
    consumption_scope = validate_consumption_resume_baseline(consumption_resume)
    old_resume = validate_consumption_scope_baseline(consumption_scope)
    validate_scope_extension_baseline(validate_resume_baseline(old_resume))


def test_key_binding_historical_scope_admission_requires_actual_receipt() -> None:
    """KBSG-07: historical scope still requires its actual pinned receipt."""
    manifest = historical_key_binding_scope_manifest()
    validate_key_binding_scope_baseline(manifest)
    validate_key_binding_scope(defensive_record(manifest), manifest["execution_sequence"]["active_target"])


def test_key_binding_unresolved_receipt_has_no_admission_or_inverse_authority() -> None:
    """KBSG-07: preparation placeholders cannot replace the actual pinned receipt."""
    manifest = historical_key_binding_scope_manifest()
    defensive_record(manifest)["events"][14]["owner_scope_decision"]["record_url"] = "UNRESOLVED_OWNER_DECISION_RECORD_URL"
    for validator in (validate_key_binding_scope_baseline,):
        with pytest.raises(AssertionError, match="defensive_record_mismatch"):
            validator(manifest)


@pytest.mark.parametrize("event_index", (13, 14))
def test_key_binding_requires_every_new_event_field(event_index: int) -> None:
    for field in KEY_BINDING_SCOPE_RECORD["events"][event_index]:
        record = deepcopy(KEY_BINDING_SCOPE_RECORD)
        record["events"][event_index].pop(field)
        with pytest.raises(AssertionError, match="defensive_record_mismatch"):
            _validate_key_binding_structure(record, DEFENSIVE_START_TARGET)


@pytest.mark.parametrize("path", index_resume_leaf_paths(KEY_BINDING_SCOPE_RECORD["events"][14]))
def test_key_binding_pins_every_scope_decision_leaf_before_receipt(path: tuple) -> None:
    """KBSG-03: exercise structure, not an early missing-receipt failure."""
    record = deepcopy(KEY_BINDING_SCOPE_RECORD)
    target = record["events"][14]
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = "[unreviewed]"
    with pytest.raises(AssertionError, match="defensive_record_mismatch"):
        _validate_key_binding_structure(record, DEFENSIVE_START_TARGET)


@pytest.mark.parametrize("path", index_resume_leaf_paths(KEY_BINDING_STOP_EVENT))
def test_key_binding_pins_every_stop_leaf(path: tuple) -> None:
    record = deepcopy(KEY_BINDING_SCOPE_RECORD)
    target = record["events"][13]
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = "[unreviewed]"
    with pytest.raises(AssertionError, match="defensive_record_mismatch"):
        _validate_key_binding_structure(record, DEFENSIVE_START_TARGET)


@pytest.mark.parametrize("field", tuple(KEY_BINDING_REPAIR_SCOPE))
@pytest.mark.parametrize("mutation", ("missing", "changed"))
def test_key_binding_repair_scope_is_closed(field: str, mutation: str) -> None:
    record = deepcopy(KEY_BINDING_SCOPE_RECORD)
    scope = record["events"][14]["owner_scope_decision"]["subject"]["repair_scope"]
    if mutation == "missing":
        scope.pop(field)
    else:
        scope[field] = "UNRESTRICTED"
    with pytest.raises(AssertionError, match="defensive_record_mismatch"):
        _validate_key_binding_structure(record, DEFENSIVE_START_TARGET)


@pytest.mark.parametrize("container", ("decision", "subject", "repair_scope"))
def test_key_binding_rejects_unknown_and_missing_nested_fields(container: str) -> None:
    original = KEY_BINDING_SCOPE_DECISION
    if container == "subject":
        original = original["subject"]
    elif container == "repair_scope":
        original = original["subject"]["repair_scope"]
    for field in (None, *original):
        record = deepcopy(KEY_BINDING_SCOPE_RECORD)
        target = record["events"][14]["owner_scope_decision"]
        if container in ("subject", "repair_scope"):
            target = target["subject"]
        if container == "repair_scope":
            target = target["repair_scope"]
        if field is None:
            target["trusted_override"] = True
        else:
            target.pop(field)
        with pytest.raises(AssertionError, match="defensive_record_mismatch"):
            _validate_key_binding_structure(record, DEFENSIVE_START_TARGET)


@pytest.mark.parametrize("index", range(15))
@pytest.mark.parametrize("mutation", ("delete", "duplicate", "change", "reorder"))
def test_key_binding_preserves_each_event(index: int, mutation: str) -> None:
    record = deepcopy(KEY_BINDING_SCOPE_RECORD)
    events = record["events"]
    if mutation == "delete":
        events.pop(index)
    elif mutation == "duplicate":
        events.insert(index, deepcopy(events[index]))
    elif mutation == "change":
        events[index]["type"] = "OVERRIDE"
    else:
        other = (index + 1) % len(events)
        events[index], events[other] = events[other], events[index]
    with pytest.raises(AssertionError, match="defensive_record_mismatch"):
        _validate_key_binding_structure(record, DEFENSIVE_START_TARGET)


@pytest.mark.parametrize("field,value", (("execution_authorized", True), ("execution_authorized", 0), ("execution_authorized", 1), ("execution_authorized", "false"), ("state", "DELIVERED"), ("delivery_evidence", {"passed": True}), ("closure_effect", "COMPLETE"), ("environment", "LIVE"), ("network_authorized", 0), ("network_authorized", True), ("provider_activation_authorized", True), ("deployment_authorized", True)))
def test_key_binding_requires_literal_flags_and_no_terminal_effects(field: str, value: object) -> None:
    record = deepcopy(KEY_BINDING_SCOPE_RECORD)
    record[field] = value
    with pytest.raises(AssertionError):
        _validate_key_binding_structure(record, DEFENSIVE_START_TARGET)


@pytest.mark.parametrize("path", [p for p in index_resume_leaf_paths(KEY_BINDING_SCOPE_RECORD) if p[-1] == "unique"])
@pytest.mark.parametrize("value", (0, 1, "false", None))
def test_key_binding_operation_boolean_is_literal_in_every_copy(path: tuple, value: object) -> None:
    record = deepcopy(KEY_BINDING_SCOPE_RECORD)
    target = record
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(AssertionError):
        _validate_key_binding_structure(record, DEFENSIVE_START_TARGET)


@pytest.mark.parametrize("mutation", ("old_scope_decision", "old_resume_decision", "resume", "start", "delivered", "extra_path", "path_order", "schema", "extra_schema", "repair_paths", "scope_override", "effect", "fake_receipt"))
def test_key_binding_rejects_implicit_or_reused_authority(mutation: str) -> None:
    record = deepcopy(KEY_BINDING_SCOPE_RECORD)
    event = record["events"][14]
    if mutation == "old_scope_decision":
        event["owner_scope_decision"] = deepcopy(INDEX_SCOPE_DECISION)
    elif mutation == "old_resume_decision":
        event["owner_scope_decision"] = deepcopy(REVIEW_IDENTITY_RESUME_DECISION)
    elif mutation in ("resume", "start", "delivered"):
        record["events"].append({"type": mutation.upper()})
    elif mutation == "extra_path":
        record["allowed_paths"].append("backend/other.py")
    elif mutation == "path_order":
        record["allowed_paths"].reverse()
    elif mutation == "schema":
        event["added_schema_operations"] = []
    elif mutation == "extra_schema":
        record["allowed_schema_operations"].append(deepcopy(INDEX_OPERATION))
    elif mutation == "repair_paths":
        event["owner_scope_decision"]["subject"]["repair_scope"]["implementation_paths"].append("backend/asie_local_api.py")
    elif mutation == "scope_override":
        event["owner_scope_decision"]["subject"]["repair_scope"]["override"] = True
    elif mutation == "fake_receipt":
        event["owner_scope_decision"]["record_url"] = "https://github.com/alphasigma13579-lang/ASIE/pull/204#issuecomment-0"
    else:
        event["owner_scope_decision"]["effect"] = "F01A_DEFENSIVE_RESUME_ONLY"
    with pytest.raises(AssertionError, match="defensive_record_mismatch"):
        _validate_key_binding_structure(record, DEFENSIVE_START_TARGET)


@pytest.mark.parametrize("record", (DEFENSIVE_REGISTRATION, DEFENSIVE_START_RECORD, DEFENSIVE_STOP_RECORD, DEFENSIVE_SCOPE_EXTENSION_RECORD, DEFENSIVE_RESUME_RECORD, CONSUMPTION_SCOPE_RECORD, CONSUMPTION_RESUME_RECORD, INDEX_SCOPE_RECORD, INDEX_RESUME_RECORD, REVIEW_IDENTITY_SCOPE_RECORD, REVIEW_IDENTITY_RESUME_RECORD, lifecycle_fixture()[0]))
def test_key_binding_never_admits_historical_or_fixture_authority(record: dict) -> None:
    with pytest.raises(AssertionError):
        validate_key_binding_scope(deepcopy(record), DEFENSIVE_START_TARGET)


@pytest.mark.parametrize("mutation", ("root", "rule", "package", "dependency", "hold", "limit", "frozen", "routing", "release"))
def test_key_binding_full_structural_inverse_rejects_unrelated_delta(mutation: str) -> None:
    manifest = historical_key_binding_scope_manifest()
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
    elif mutation == "limit":
        manifest["execution_sequence"]["max_active_executions"] = 2
    elif mutation == "frozen":
        manifest["frozen_files"].append("backend/unknown.py")
    elif mutation == "routing":
        packages["FC20-12"]["execution_slices"][0]["required_entry_controls"]["single_active_execution"]["status"] = "PASS"
    else:
        manifest["public_release_authorized"] = True
    with pytest.raises(AssertionError, match="key_binding_baseline_mismatch"):
        _key_binding_historical_inverse(manifest)


@pytest.mark.parametrize("slot", (None, {}, {"kind": "package", "package_id": "FC20-05"}))
def test_key_binding_keeps_one_counted_slot(slot: object) -> None:
    with pytest.raises(AssertionError, match="key_binding_slot"):
        _validate_key_binding_structure(deepcopy(KEY_BINDING_SCOPE_RECORD), slot)


@pytest.mark.parametrize("relative_path", tuple(KEY_BINDING_VIEW_SHA256))
def test_key_binding_raw_projection_seals_and_historical_chain(relative_path: str) -> None:
    source = key_binding_resume_historical_view(recovery_scope_historical_view(recovery_resume_historical_view(dataset_scope_historical_view(dataset_resume_historical_view(overlay_scope_historical_view(overlay_resume_historical_view(ci_scope_historical_view(ci_resume_historical_view(ci_amend_historical_view((Path(__file__).resolve().parents[1] / relative_path).read_bytes(), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path)
    prefix = key_binding_historical_view(source, relative_path)
    assert git_blob_sha(prefix) == KEY_BINDING_VIEW_PREFIX_BLOBS[relative_path]
    review_identity_resume_historical_view(prefix, relative_path)
    assert set(KEY_BINDING_VIEW_SHA256) == set(KEY_BINDING_VIEW_PREFIX_BLOBS) == set(REVIEW_IDENTITY_RESUME_VIEW_SHA256)


@pytest.mark.parametrize("relative_path", tuple(KEY_BINDING_VIEW_SHA256))
@pytest.mark.parametrize("mutation", ("missing_marker", "duplicate_marker", "separator", "prefix", "prefix_crlf", "whole_crlf", "section_crlf", "suffix", "comment", "trailing_blank_line", "missing_final_newline", "scope", "execution", "schema", "receipt", "path_order"))
def test_key_binding_rejects_unreviewed_projection_bytes(relative_path: str, mutation: str) -> None:
    source = key_binding_resume_historical_view(recovery_scope_historical_view(recovery_resume_historical_view(dataset_scope_historical_view(dataset_resume_historical_view(overlay_scope_historical_view(overlay_resume_historical_view(ci_scope_historical_view(ci_resume_historical_view(ci_amend_historical_view((Path(__file__).resolve().parents[1] / relative_path).read_bytes(), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path)
    marker = KEY_BINDING_VIEW_MARKER.encode(); separator = b"\n" + marker + b"\n"
    prefix, section = source.split(separator, 1)
    if mutation == "missing_marker":
        tampered = source.replace(marker, b"", 1)
    elif mutation == "duplicate_marker":
        tampered = source + separator
    elif mutation == "separator":
        tampered = source.replace(separator, b"\n\n" + marker + b"\n", 1)
    elif mutation == "prefix":
        tampered = b"edited\n" + source
    elif mutation == "prefix_crlf":
        tampered = prefix.replace(b"\n", b"\r\n") + separator + section
    elif mutation == "whole_crlf":
        tampered = source.replace(b"\n", b"\r\n")
    elif mutation == "section_crlf":
        tampered = prefix + separator + section.replace(b"\n", b"\r\n")
    elif mutation in ("suffix", "comment", "trailing_blank_line"):
        tampered = source + {"suffix": b"\n### Override\n", "comment": b"\n<!-- override -->\n", "trailing_blank_line": b"\n"}[mutation]
    elif mutation == "missing_final_newline":
        tampered = source.removesuffix(b"\n")
    elif mutation == "path_order":
        first, second = (f"- `{p}`\n".encode() for p in REVIEW_IDENTITY_RESUME_RECORD["allowed_paths"][:2])
        tampered = prefix + separator + section.replace(first + second, second + first)
    else:
        old, new = {"scope": (b"STORED_CONTEXT_KEY_FINGERPRINT_BINDING_ONLY", b"UNRESTRICTED"), "execution": (b"IN_PROGRESS/false", b"IN_PROGRESS/true"), "schema": (b"unique=false", b"unique=true"), "receipt": (b"https://github.com/alphasigma13579-lang/ASIE/pull/204#issuecomment-6128022293", b"FORGED_RECEIPT")}[mutation]
        tampered = prefix + separator + section.replace(old, new)
    assert tampered != source
    with pytest.raises(AssertionError, match="key_binding_view_"):
        key_binding_historical_view(tampered, relative_path)


@pytest.mark.parametrize("relative_path", tuple(KEY_BINDING_VIEW_SHA256))
def test_key_binding_rejects_cross_path_transplants(relative_path: str) -> None:
    root = Path(__file__).resolve().parents[1]
    other = next(p for p in KEY_BINDING_VIEW_SHA256 if p != relative_path)
    source, other_source = key_binding_resume_historical_view(recovery_scope_historical_view(recovery_resume_historical_view(dataset_scope_historical_view(dataset_resume_historical_view(overlay_scope_historical_view(overlay_resume_historical_view(ci_scope_historical_view(ci_resume_historical_view(ci_amend_historical_view((root / relative_path).read_bytes(), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), key_binding_resume_historical_view(recovery_scope_historical_view(recovery_resume_historical_view(dataset_scope_historical_view(dataset_resume_historical_view(overlay_scope_historical_view(overlay_resume_historical_view(ci_scope_historical_view(ci_resume_historical_view(ci_amend_historical_view((root / other).read_bytes(), other), other), other), other), other), other), other), other), other), other)
    separator = ("\n" + KEY_BINDING_VIEW_MARKER + "\n").encode()
    with pytest.raises(AssertionError, match="key_binding_view_prefix_changed"):
        key_binding_historical_view(other_source, relative_path)
    with pytest.raises(AssertionError, match="key_binding_view_projection_changed"):
        key_binding_historical_view(source.split(separator, 1)[0] + separator + other_source.split(separator, 1)[1], relative_path)


@pytest.mark.parametrize("path", ("", "docs/unapproved.md", "backend/repository.py"))
def test_key_binding_projection_has_no_fallback(path: str) -> None:
    source = key_binding_resume_historical_view(recovery_scope_historical_view(recovery_resume_historical_view(dataset_scope_historical_view(dataset_resume_historical_view(overlay_scope_historical_view(overlay_resume_historical_view(ci_scope_historical_view(ci_resume_historical_view(ci_amend_historical_view((Path(__file__).resolve().parents[1] / CONSUMPTION_VIEW_PATHS[0]).read_bytes(), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0])
    with pytest.raises(AssertionError, match="key_binding_view_path"):
        key_binding_historical_view(source, path)


def test_key_binding_requires_raw_bytes_and_keeps_accepted_design() -> None:
    root = Path(__file__).resolve().parents[1]
    path = CONSUMPTION_VIEW_PATHS[0]
    with pytest.raises(AssertionError, match="key_binding_view_source_bytes"):
        key_binding_historical_view((root / path).read_text(), path)
    assert git_blob_sha((root / "docs/FC20-12-F01A-KEY-FINGERPRINT-SCOPE-PROPOSAL-2026-10-12.md").read_bytes()) == "c932029f3c64ba0473596947e42ae1bdc1fcd51f", "key_binding_design_changed"


def test_key_binding_mutation_inventory_covers_nested_lists_and_all_operation_copies() -> None:
    paths = [p for p in index_resume_leaf_paths(KEY_BINDING_SCOPE_RECORD) if p[-1] == "unique"]
    assert ("allowed_schema_operations", 0, "unique") in paths
    assert ("events", 14, "owner_scope_decision", "subject", "allowed_schema_operations", 0, "unique") in paths
    assert ("events", 14, "owner_scope_decision", "subject", "baseline_record", "allowed_schema_operations", 0, "unique") in paths
    assert len(paths) > len([p for p in index_resume_leaf_paths(REVIEW_IDENTITY_RESUME_RECORD) if p[-1] == "unique"])


# KBRG: proposed repair-only conditional resume; real decision remains conditional on separately approved transition merge.
KEY_BINDING_RESUME_EXECUTION_SCOPE = json.loads(r'''{
  "activities": [
    "DEVELOP_REGISTERED_STORED_KEY_FINGERPRINT_BINDING",
    "TEST_REGISTERED_STORED_KEY_FINGERPRINT_BINDING"
  ],
  "implementation_paths": [
    "backend/repository.py",
    "tests/test_repository_intelligence.py"
  ],
  "database_scope": "DISPOSABLE_TEMPORARY_DATABASES_ONLY",
  "data_scope": "SYNTHETIC_DATA_ONLY",
  "live_database_authorized": false,
  "owner_database_authorized": false,
  "production_placement_accepted": false,
  "deployment_authorized": false,
  "application_pr_merge_authorized": false,
  "startup_criteria_status": "UNKNOWN_NOT_APPROVED",
  "maintenance_recovery_acceptance": "UNKNOWN_NOT_APPROVED",
  "query_and_proof_semantics": "UNCHANGED"
}''')
KEY_BINDING_RESUME_DECISION = json.loads(r'''{
  "id": "DECISION-FC20-12-F01A-KEY-FINGERPRINT-CONDITIONAL-RESUME-2026-10-12",
  "record_url": "https://github.com/alphasigma13579-lang/ASIE/pull/205#issuecomment-6129650208",
  "recorded_at": "2026-10-12T17:52:48Z",
  "effect": "F01A_DEFENSIVE_RESUME_ONLY",
  "condition": "REVIEWED_GOVERNANCE_TRANSITION_MERGED_AFTER_SEPARATE_OWNER_MERGE_APPROVAL",
  "subject": {
    "baseline_commit_sha": "c365c85aded98811558fd190f3a2079434f1a9ad",
    "baseline_manifest_blob_sha": "6c0defd45b71bd8b28dc85d109e5bc7d1d3e8628",
    "application_head_sha": "4fcb8b47971a8ee55fa0ae95f5928bdd5722890a",
    "allowed_paths": [
      "backend/asie_local_api.py",
      "backend/repository.py",
      "backend/intelligence_prerun_service.py",
      "tests/test_repository_intelligence.py",
      "tests/test_intelligence_prerun_service.py",
      "tests/test_intelligence_context_ingress_api.py",
      "docs/FC20-12-F01-TRUSTED-CONTEXT-INGRESS-REPAIR-PLAN-2026-10-01.md",
      "tests/test_live_location_api.py",
      "tests/test_intelligence_consumption.py"
    ],
    "allowed_schema_operations": [
      {
        "operation": "CREATE_INDEX_IF_NOT_EXISTS",
        "index_name": "idx_security_audit_origin_proof",
        "table": "security_audit_events",
        "columns": [
          "action",
          "target_type",
          "target_id",
          "organization_id"
        ],
        "unique": false,
        "implementation_path": "backend/repository.py",
        "test_path": "tests/test_repository_intelligence.py"
      }
    ]
  },
  "proposal_commit_sha": "8d512f0123cf81332de306c9b1b60ee12defa906",
  "proposal_blob_sha": "c932029f3c64ba0473596947e42ae1bdc1fcd51f"
}''')
KEY_BINDING_RESUME_DECISION["subject"].update(checkpoint=deepcopy(KEY_BINDING_STOP_EVENT), scope_extension=deepcopy(KEY_BINDING_SCOPE_EVENT), repair_scope=deepcopy(KEY_BINDING_REPAIR_SCOPE), execution_scope=deepcopy(KEY_BINDING_RESUME_EXECUTION_SCOPE))
KEY_BINDING_RESUME_EVENT = json.loads(r'''{
  "type": "RESUME",
  "recorded_at": "2026-10-12T17:53:43Z",
  "baseline_commit_sha": "c365c85aded98811558fd190f3a2079434f1a9ad",
  "baseline_manifest_blob_sha": "6c0defd45b71bd8b28dc85d109e5bc7d1d3e8628",
  "effect": "F01A_DEFENSIVE_RESUME_ONLY"
}''')
KEY_BINDING_RESUME_EVENT.update(checkpoint=deepcopy(KEY_BINDING_STOP_EVENT), scope_extension=deepcopy(KEY_BINDING_SCOPE_EVENT), owner_resume_decision=deepcopy(KEY_BINDING_RESUME_DECISION))
KEY_BINDING_RESUME_RECORD = deepcopy(KEY_BINDING_SCOPE_RECORD)
KEY_BINDING_RESUME_RECORD["execution_authorized"] = True
KEY_BINDING_RESUME_RECORD["events"].append(deepcopy(KEY_BINDING_RESUME_EVENT))
KEY_BINDING_RESUME_VIEW_PREFIX_BLOBS = json.loads(r'''{
  "docs/ASIE-BETA-EXECUTION-MASTER-PLAN-2026-09-09.md": "98d85cd86bc163cfdd9d8cb660272c8473c02094",
  "docs/FC20-12-F01A-DEFENSIVE-ENABLING-REGISTRATION-PROPOSAL-2026-10-01.md": "cb9d8d889eef69ca3db17b44fb8718e91757a694",
  "docs/FC20-12-F01A-APPROVAL-CONSUMPTION-SCOPE-REGISTRATION-2026-10-09.md": "1b7b4d836c098cf29957710b5d19747ad3d55254",
  "docs/FOUNDATION-COMPLETE-20-CORE-INTELLIGENCE-COMPLETION-PROGRAM-2026-07-29.md": "3ae44452de1f15ed1a7d8f5a49536112135d89a1",
  "docs/EKB/FOUNDATION-COMPLETE-20-PACKAGE-INDEX.md": "a24cc7b65ec2f525eccc4c54fcc404d00099ec7f"
}''')
KEY_BINDING_RESUME_VIEW_SHA256 = json.loads(r'''{
  "docs/ASIE-BETA-EXECUTION-MASTER-PLAN-2026-09-09.md": "2ee813ffc3399ffad174cbeef041c1fad359900c406dbca7df941d27a1c88edd",
  "docs/FC20-12-F01A-DEFENSIVE-ENABLING-REGISTRATION-PROPOSAL-2026-10-01.md": "b0aa6631e44249e183eaf4e256ff24305da5e97c9502fa4eddebf84e7a304c4d",
  "docs/FC20-12-F01A-APPROVAL-CONSUMPTION-SCOPE-REGISTRATION-2026-10-09.md": "0e42655d8c4462c615fd8998f467db9eabb05f06dfc2b2da45a2bd8a1f3896f5",
  "docs/FOUNDATION-COMPLETE-20-CORE-INTELLIGENCE-COMPLETION-PROGRAM-2026-07-29.md": "25cd590bac0ae8fae2a33328db120c79e253d02c9893a2f601bfb966d1078775",
  "docs/EKB/FOUNDATION-COMPLETE-20-PACKAGE-INDEX.md": "f95c471efc3450a33c8c3583e0f510b4937fc99433762c19ef7ee83b2604d8fe"
}''')
KEY_BINDING_RESUME_VIEW_MARKER = '<!-- F01A-KEY-FINGERPRINT-CONDITIONAL-RESUME-2026-10-12 -->'
def _validate_key_binding_resume_structure(record: dict, active_target: object) -> None:
    """KBRG-01/02/03/04: closed proposed structure, never an execution decision."""
    assert isinstance(record, dict), "invalid_defensive_record"
    assert set(record) == set(KEY_BINDING_RESUME_RECORD), "defensive_fields"
    if record != KEY_BINDING_RESUME_RECORD:
        raise AssertionError("defensive_record_mismatch")
    if json.dumps(record, sort_keys=True) != json.dumps(KEY_BINDING_RESUME_RECORD, sort_keys=True):
        raise AssertionError("key_binding_resume_literal_types")
    assert record["execution_authorized"] is True, "key_binding_resume_literal_flag"
    assert all(record[key] is False for key in (
        "network_authorized", "provider_activation_authorized", "deployment_authorized",
    )), "defensive_external_effect"
    assert active_target == DEFENSIVE_START_TARGET, "key_binding_resume_slot"
    subject = record["events"][15]["owner_resume_decision"]["subject"]
    assert subject["repair_scope"] == KEY_BINDING_REPAIR_SCOPE, "key_binding_resume_repair_scope"
    assert subject["execution_scope"] == KEY_BINDING_RESUME_EXECUTION_SCOPE, "key_binding_resume_execution_scope"
    assert subject["checkpoint"] == KEY_BINDING_STOP_EVENT, "key_binding_resume_checkpoint"
    assert subject["scope_extension"] == KEY_BINDING_SCOPE_EVENT, "key_binding_resume_scope_extension"
    assert subject["allowed_paths"] == KEY_BINDING_SCOPE_RECORD["allowed_paths"], "key_binding_resume_paths"
    assert subject["allowed_schema_operations"] == record["allowed_schema_operations"] == [INDEX_OPERATION], "key_binding_resume_operation"
    assert all(subject["execution_scope"][key] is False for key in (
        "live_database_authorized", "owner_database_authorized", "production_placement_accepted",
        "deployment_authorized", "application_pr_merge_authorized",
    )), "key_binding_resume_forbidden_effect"


def validate_key_binding_resume(record: dict, active_target: object) -> None:
    """KBRG-03/07: current admission needs the new real execution receipt and time."""
    _validate_key_binding_resume_structure(record, active_target)
    decision = record["events"][15]["owner_resume_decision"]
    url, timestamp = decision["record_url"], decision["recorded_at"]
    assert isinstance(url, str) and re.fullmatch(
        r"https://github\.com/alphasigma13579-lang/ASIE/pull/205#issuecomment-[0-9]+", url,
    ) and isinstance(timestamp, str) and re.fullmatch(
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z", timestamp,
    ), "key_binding_resume_execution_decision_missing"


def _key_binding_resume_historical_inverse(manifest: dict) -> dict:
    """KBRG-05: structure-only test history; never current admission authority."""
    original_record = defensive_record(manifest)
    _validate_key_binding_resume_structure(original_record, manifest["execution_sequence"]["active_target"])
    # Copy only the edited path before serializing the complete JSON tree. The
    # verified bytes below detach every returned container, without copying the
    # large RESUME event that this inverse immediately removes.
    restored = dict(manifest)
    restored["packages"] = list(manifest["packages"])
    package_index = next(i for i, package in enumerate(manifest["packages"]) if package["id"] == "FC20-12")
    package = dict(manifest["packages"][package_index])
    restored["packages"][package_index] = package
    package["execution_slices"] = list(package["execution_slices"])
    record = dict(original_record)
    package["execution_slices"][1] = record
    record["events"] = list(record["events"])
    assert record["events"].pop() == KEY_BINDING_RESUME_EVENT
    record["execution_authorized"] = False
    source = (json.dumps(restored, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    assert git_blob_sha(source) == "6c0defd45b71bd8b28dc85d109e5bc7d1d3e8628", "key_binding_resume_baseline_mismatch"
    restored = json.loads(source)
    validate_key_binding_scope(defensive_record(restored), restored["execution_sequence"]["active_target"])
    return restored


def validate_key_binding_resume_baseline(manifest: dict) -> dict:
    """KBRG-05/07: real current admission is mandatory before the public inverse."""
    validate_key_binding_resume(defensive_record(manifest), manifest["execution_sequence"]["active_target"])
    return _key_binding_resume_historical_inverse(manifest)


def historical_key_binding_scope_manifest() -> dict:
    """Verified fifteen-event historical fixture, not a current authority fallback."""
    return _key_binding_resume_historical_inverse(historical_key_binding_resume_manifest())


def key_binding_resume_historical_view(source_bytes: bytes, relative_path: str) -> bytes:
    """KBRG-06: raw historical prefix and path-bound exact terminal projection."""
    assert isinstance(source_bytes, bytes), "key_binding_resume_view_source_bytes"
    assert relative_path in KEY_BINDING_RESUME_VIEW_SHA256, "key_binding_resume_view_path"
    marker = KEY_BINDING_RESUME_VIEW_MARKER.encode("utf-8")
    separator = b"\n" + marker + b"\n"
    assert source_bytes.count(marker) == 1, "key_binding_resume_view_marker"
    assert source_bytes.count(separator) == 1, "key_binding_resume_view_boundary"
    prefix, section = source_bytes.split(separator, 1)
    assert git_blob_sha(prefix) == KEY_BINDING_RESUME_VIEW_PREFIX_BLOBS[relative_path], "key_binding_resume_view_prefix_changed"
    assert hashlib.sha256(marker + b"\n" + section).hexdigest() == KEY_BINDING_RESUME_VIEW_SHA256[relative_path], "key_binding_resume_view_projection_changed"
    key_binding_historical_view(prefix, relative_path)
    return prefix


def test_key_binding_resume_structural_inverse_preserves_all_fifteen_events() -> None:
    """KBRG-01/02/05: establish exact history independently of current admission."""
    manifest = historical_key_binding_resume_manifest()
    record = defensive_record(manifest)
    _validate_key_binding_resume_structure(record, manifest["execution_sequence"]["active_target"])
    assert len(record["events"]) == 16
    assert record["events"][:15] == KEY_BINDING_SCOPE_RECORD["events"]
    event = record["events"][15]
    for target in (event, event["owner_resume_decision"]["subject"]):
        assert target["checkpoint"] == record["events"][13]
        assert target["scope_extension"] == record["events"][14]
    assert record["allowed_paths"] == KEY_BINDING_SCOPE_RECORD["allowed_paths"]
    assert len(record["allowed_paths"]) == 9
    assert record["allowed_schema_operations"] == [INDEX_OPERATION]
    assert manifest["execution_sequence"]["held_packages"] == HELD_PACKAGES
    assert active_execution_targets(manifest["packages"], {"FC20-05"}) == ["FC20-12/f01a_defensive_ingress"]
    stopped = _key_binding_resume_historical_inverse(manifest)
    previous = validate_key_binding_scope_baseline(stopped)
    old_review_scope = validate_review_identity_resume_baseline(previous)
    old_index_resume = validate_review_identity_scope_baseline(old_review_scope)
    index_scope = validate_index_resume_baseline(old_index_resume)
    consumption_resume = validate_index_scope_baseline(index_scope)
    consumption_scope = validate_consumption_resume_baseline(consumption_resume)
    old_resume = validate_consumption_scope_baseline(consumption_scope)
    validate_scope_extension_baseline(validate_resume_baseline(old_resume))


def test_key_binding_resume_current_admission_requires_real_execution_decision() -> None:
    """KBRG-07: the actual pinned conditional decision and every current gate are required."""
    manifest = historical_key_binding_resume_manifest()
    validate_key_binding_resume_baseline(manifest)
    validate_routing_registration(load_manifest())


def test_key_binding_resume_missing_execution_decision_blocks_all_current_seams() -> None:
    """KBRG-07: neither unresolved receipt nor time replaces the pinned decision."""
    for field, value in (
        ("record_url", "UNRESOLVED_OWNER_EXECUTION_DECISION_RECORD_URL"),
        ("recorded_at", "UNRESOLVED_OWNER_EXECUTION_DECISION_TIME"),
    ):
        manifest = historical_key_binding_resume_manifest()
        defensive_record(manifest)["events"][15]["owner_resume_decision"][field] = value
        for validator in (validate_key_binding_resume_baseline,):
            with pytest.raises(AssertionError, match="defensive_record_mismatch"):
                validator(manifest)


@pytest.mark.parametrize("field", tuple(KEY_BINDING_RESUME_EVENT))
def test_key_binding_resume_requires_all_event_fields(field: str) -> None:
    """KBRG-03: no partial evidence can become a new resume decision."""
    manifest = historical_key_binding_resume_manifest()
    defensive_record(manifest)["events"][15].pop(field)
    with pytest.raises(AssertionError, match="defensive_record_mismatch"):
        _validate_key_binding_resume_structure(defensive_record(manifest), manifest["execution_sequence"]["active_target"])



@pytest.mark.parametrize("path", index_resume_leaf_paths(KEY_BINDING_RESUME_EVENT))
def test_key_binding_resume_pins_every_evidence_leaf(path: list) -> None:
    """KBRG-03: independently pin receipt, timestamps, baselines and nested copies."""
    manifest = historical_key_binding_resume_manifest()
    target = defensive_record(manifest)["events"][15]
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = "[unreviewed]"
    with pytest.raises(AssertionError, match="defensive_record_mismatch"):
        _validate_key_binding_resume_structure(defensive_record(manifest), manifest["execution_sequence"]["active_target"])


@pytest.mark.parametrize("field", tuple(KEY_BINDING_RESUME_EXECUTION_SCOPE))
@pytest.mark.parametrize("mutation", ("missing", "changed"))
def test_key_binding_resume_requires_closed_limited_execution_scope(field: str, mutation: str) -> None:
    """KBRG-03/08: remove or broaden any restriction and admission fails."""
    manifest = historical_key_binding_resume_manifest()
    scope = defensive_record(manifest)["events"][15]["owner_resume_decision"]["subject"]["execution_scope"]
    if mutation == "missing":
        scope.pop(field)
    else:
        scope[field] = True if field.endswith(("authorized", "accepted")) else "UNRESTRICTED"
    with pytest.raises(AssertionError, match="defensive_record_mismatch"):
        _validate_key_binding_resume_structure(defensive_record(manifest), manifest["execution_sequence"]["active_target"])


@pytest.mark.parametrize("field", ("live_database_authorized", "owner_database_authorized", "production_placement_accepted", "deployment_authorized", "application_pr_merge_authorized"))
@pytest.mark.parametrize("value", (0, 1, "false", None))
def test_key_binding_resume_scope_requires_literal_booleans(field: str, value: object) -> None:
    """KBRG-03/08: false-like metadata never substitutes for explicit prohibitions."""
    manifest = historical_key_binding_resume_manifest()
    defensive_record(manifest)["events"][15]["owner_resume_decision"]["subject"]["execution_scope"][field] = value
    with pytest.raises(AssertionError):
        _validate_key_binding_resume_structure(defensive_record(manifest), manifest["execution_sequence"]["active_target"])


@pytest.mark.parametrize("mutation", ("unknown", "extra_activity", "extra_path", "path_order", "real_data", "live_database", "startup_approved", "recovery_approved", "changed_query", "empty_scope"))
def test_key_binding_resume_never_interprets_true_as_general_execution(mutation: str) -> None:
    """KBRG-08: an otherwise exact true record cannot authorize broader work."""
    manifest = historical_key_binding_resume_manifest()
    subject = defensive_record(manifest)["events"][15]["owner_resume_decision"]["subject"]
    scope = subject["execution_scope"]
    if mutation == "unknown":
        scope["trusted_override"] = True
    elif mutation == "extra_activity":
        scope["activities"].append("DEPLOY")
    elif mutation == "extra_path":
        scope["implementation_paths"].append("backend/asie_local_api.py")
    elif mutation == "path_order":
        scope["implementation_paths"].reverse()
    elif mutation == "real_data":
        scope["data_scope"] = "OWNER_DATA"
    elif mutation == "live_database":
        scope["database_scope"] = "OWNER_DATABASE"
    elif mutation == "startup_approved":
        scope["startup_criteria_status"] = "APPROVED"
    elif mutation == "recovery_approved":
        scope["maintenance_recovery_acceptance"] = "APPROVED"
    elif mutation == "changed_query":
        scope["query_and_proof_semantics"] = "REPLACED"
    else:
        subject["execution_scope"] = {}
    with pytest.raises(AssertionError, match="defensive_record_mismatch"):
        _validate_key_binding_resume_structure(defensive_record(manifest), manifest["execution_sequence"]["active_target"])


@pytest.mark.parametrize("mutation", ("old_resume", "scope_decision", "preparation_effect", "missing_condition", "new_branch_baseline", "old_checkpoint_baseline", "unknown_decision", "unknown_subject", "duplicate_resume"))
def test_key_binding_resume_rejects_reused_or_ambiguous_authority(mutation: str) -> None:
    """KBRG-03/07: design, publication, scope or merge approvals are not this decision."""
    manifest = historical_key_binding_resume_manifest()
    record = defensive_record(manifest)
    event = record["events"][15]
    if mutation == "old_resume":
        event["owner_resume_decision"] = deepcopy(CONSUMPTION_RESUME_DECISION)
    elif mutation == "scope_decision":
        event["owner_resume_decision"] = deepcopy(KEY_BINDING_SCOPE_DECISION)
    elif mutation == "preparation_effect":
        event["owner_resume_decision"]["effect"] = "PREPARE_GOVERNANCE_PR_ONLY_NO_MERGE_NO_RESUME"
    elif mutation == "missing_condition":
        event["owner_resume_decision"].pop("condition")
    elif mutation == "new_branch_baseline":
        event["baseline_commit_sha"] = "63b18a192e8eac3c66ad5440a667e6d1d9959d10"
    elif mutation == "old_checkpoint_baseline":
        event["baseline_commit_sha"] = KEY_BINDING_STOP_EVENT["baseline_commit_sha"]
        event["baseline_manifest_blob_sha"] = KEY_BINDING_STOP_EVENT["baseline_manifest_blob_sha"]
    elif mutation == "unknown_decision":
        event["owner_resume_decision"]["approved"] = True
    elif mutation == "unknown_subject":
        event["owner_resume_decision"]["subject"]["override"] = True
    else:
        record["events"].append(deepcopy(event))
    with pytest.raises(AssertionError, match="defensive_record_mismatch"):
        _validate_key_binding_resume_structure(defensive_record(manifest), manifest["execution_sequence"]["active_target"])


@pytest.mark.parametrize("index", range(16))
@pytest.mark.parametrize("mutation", ("delete", "duplicate", "change", "reorder"))
def test_key_binding_resume_preserves_each_event(index: int, mutation: str) -> None:
    """KBRG-02: every historical or current event is required in its exact position."""
    manifest = historical_key_binding_resume_manifest()
    events = defensive_record(manifest)["events"]
    if mutation == "delete":
        events.pop(index)
    elif mutation == "duplicate":
        events.insert(index, deepcopy(events[index]))
    elif mutation == "change":
        events[index]["type"] = "OVERRIDE"
    else:
        other = (index + 1) % len(events)
        events[index], events[other] = events[other], events[index]
    with pytest.raises(AssertionError, match="defensive_record_mismatch"):
        _validate_key_binding_resume_structure(defensive_record(manifest), manifest["execution_sequence"]["active_target"])


@pytest.mark.parametrize("field,value", (("execution_authorized", False), ("execution_authorized", 1), ("execution_authorized", "true"), ("state", "DELIVERED"), ("delivery_evidence", {"passed": True}), ("closure_effect", "COMPLETE"), ("environment", "LIVE"), ("network_authorized", 0), ("network_authorized", True), ("provider_activation_authorized", True), ("deployment_authorized", True)))
def test_key_binding_resume_requires_literal_flags_and_no_terminal_effects(field: str, value: object) -> None:
    """KBRG-04/08: no implicit Boolean authority, completion or external activation."""
    manifest = historical_key_binding_resume_manifest()
    defensive_record(manifest)[field] = value
    with pytest.raises(AssertionError):
        _validate_key_binding_resume_structure(defensive_record(manifest), manifest["execution_sequence"]["active_target"])


@pytest.mark.parametrize("record", (DEFENSIVE_REGISTRATION, DEFENSIVE_START_RECORD, DEFENSIVE_STOP_RECORD, DEFENSIVE_SCOPE_EXTENSION_RECORD, DEFENSIVE_RESUME_RECORD, CONSUMPTION_SCOPE_RECORD, CONSUMPTION_RESUME_RECORD, INDEX_SCOPE_RECORD, INDEX_RESUME_RECORD, REVIEW_IDENTITY_SCOPE_RECORD, REVIEW_IDENTITY_RESUME_RECORD, KEY_BINDING_SCOPE_RECORD, lifecycle_fixture()[0]))
def test_key_binding_resume_never_admits_any_historical_or_fixture_state(record: dict) -> None:
    """KBRG-07: only the new exact conditional decision is current authority."""
    with pytest.raises(AssertionError):
        _validate_key_binding_resume_structure(deepcopy(record), DEFENSIVE_START_TARGET)


@pytest.mark.parametrize("mutation", ("root", "rule", "package", "dependency", "hold", "limit", "frozen", "routing", "release"))
def test_key_binding_resume_full_inverse_rejects_every_unrelated_delta(mutation: str) -> None:
    """KBRG-05: seal the full manifest, not only a convenient authority subset."""
    manifest = historical_key_binding_resume_manifest()
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
    elif mutation == "limit":
        manifest["execution_sequence"]["max_active_executions"] = 2
    elif mutation == "frozen":
        manifest["frozen_files"].append("backend/unknown.py")
    elif mutation == "routing":
        packages["FC20-12"]["execution_slices"][0]["required_entry_controls"]["single_active_execution"]["status"] = "PASS"
    else:
        manifest["public_release_authorized"] = True
    with pytest.raises(AssertionError, match="key_binding_resume_baseline_mismatch"):
        _key_binding_resume_historical_inverse(manifest)


@pytest.mark.parametrize("slot", (None, {}, {"kind": "package", "package_id": "FC20-05"}))
def test_key_binding_resume_retains_single_counted_slot(slot: object) -> None:
    """KBRG-04: resume retains the same slot and cannot hand it to held work."""
    manifest = historical_key_binding_resume_manifest()
    manifest["execution_sequence"]["active_target"] = slot
    with pytest.raises(AssertionError):
        _validate_key_binding_resume_structure(defensive_record(manifest), manifest["execution_sequence"]["active_target"])


@pytest.mark.parametrize("relative_path", tuple(KEY_BINDING_RESUME_VIEW_SHA256))
def test_key_binding_resume_preserves_all_historical_projection_seals(relative_path: str) -> None:
    """KBRG-06: full prior documents and every old oracle stay independently sealed."""
    source = recovery_scope_historical_view(recovery_resume_historical_view(dataset_scope_historical_view(dataset_resume_historical_view(overlay_scope_historical_view(overlay_resume_historical_view(ci_scope_historical_view(ci_resume_historical_view(ci_amend_historical_view((Path(__file__).resolve().parents[1] / relative_path).read_bytes(), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path)
    prefix = key_binding_resume_historical_view(source, relative_path)
    key_binding_historical_view(prefix, relative_path)
    assert set(KEY_BINDING_RESUME_VIEW_SHA256) == set(KEY_BINDING_RESUME_VIEW_PREFIX_BLOBS) == set(KEY_BINDING_VIEW_SHA256)


@pytest.mark.parametrize("relative_path", tuple(KEY_BINDING_RESUME_VIEW_SHA256))
@pytest.mark.parametrize("mutation", ("missing_marker", "duplicate_marker", "separator", "prefix", "prefix_crlf", "whole_crlf", "section_crlf", "suffix", "comment", "trailing_blank_line", "missing_final_newline", "live_authority", "startup_approved", "data_scope", "scope_order"))
def test_key_binding_resume_projection_rejects_unreviewed_bytes(relative_path: str, mutation: str) -> None:
    """KBRG-06/08: exact terminal bytes, including every restricted-execution claim."""
    source = recovery_scope_historical_view(recovery_resume_historical_view(dataset_scope_historical_view(dataset_resume_historical_view(overlay_scope_historical_view(overlay_resume_historical_view(ci_scope_historical_view(ci_resume_historical_view(ci_amend_historical_view((Path(__file__).resolve().parents[1] / relative_path).read_bytes(), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path)
    marker = KEY_BINDING_RESUME_VIEW_MARKER.encode(); separator = b"\n" + marker + b"\n"
    prefix, section = source.split(separator, 1)
    if mutation == "missing_marker":
        tampered = source.replace(marker, b"", 1)
    elif mutation == "duplicate_marker":
        tampered = source + separator
    elif mutation == "separator":
        tampered = source.replace(separator, b"\n\n" + marker + b"\n", 1)
    elif mutation == "prefix":
        tampered = b"edited\n" + source
    elif mutation == "prefix_crlf":
        tampered = prefix.replace(b"\n", b"\r\n") + separator + section
    elif mutation == "whole_crlf":
        tampered = source.replace(b"\n", b"\r\n")
    elif mutation == "section_crlf":
        tampered = prefix + separator + section.replace(b"\n", b"\r\n")
    elif mutation in ("suffix", "comment", "trailing_blank_line"):
        tampered = source + {"suffix": b"\n### Override\n", "comment": b"\n<!-- override -->\n", "trailing_blank_line": b"\n"}[mutation]
    elif mutation == "missing_final_newline":
        tampered = source.removesuffix(b"\n")
    elif mutation == "scope_order":
        first, second = (f"- `{p}`\n".encode() for p in KEY_BINDING_SCOPE_RECORD["allowed_paths"][:2])
        tampered = prefix + separator + section.replace(first + second, second + first)
    else:
        old, new = {"live_authority": (b"live_database_authorized=false", b"live_database_authorized=true"), "startup_approved": (b"startup_criteria_status=UNKNOWN_NOT_APPROVED", b"startup_criteria_status=APPROVED"), "data_scope": (b"SYNTHETIC_DATA_ONLY", b"OWNER_DATA")}[mutation]
        tampered = prefix + separator + section.replace(old, new)
    assert tampered != source
    with pytest.raises(AssertionError, match="key_binding_resume_view_"):
        key_binding_resume_historical_view(tampered, relative_path)


@pytest.mark.parametrize("relative_path", tuple(KEY_BINDING_RESUME_VIEW_SHA256))
def test_key_binding_resume_rejects_cross_path_projection_transplants(relative_path: str) -> None:
    """KBRG-06: authentic content from another path cannot borrow this path's seal."""
    root = Path(__file__).resolve().parents[1]
    other = next(p for p in KEY_BINDING_RESUME_VIEW_SHA256 if p != relative_path)
    source, other_source = recovery_scope_historical_view(recovery_resume_historical_view(dataset_scope_historical_view(dataset_resume_historical_view(overlay_scope_historical_view(overlay_resume_historical_view(ci_scope_historical_view(ci_resume_historical_view(ci_amend_historical_view((root / relative_path).read_bytes(), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), recovery_scope_historical_view(recovery_resume_historical_view(dataset_scope_historical_view(dataset_resume_historical_view(overlay_scope_historical_view(overlay_resume_historical_view(ci_scope_historical_view(ci_resume_historical_view(ci_amend_historical_view((root / other).read_bytes(), other), other), other), other), other), other), other), other), other)
    separator = ("\n" + KEY_BINDING_RESUME_VIEW_MARKER + "\n").encode()
    with pytest.raises(AssertionError, match="key_binding_resume_view_prefix_changed"):
        key_binding_resume_historical_view(other_source, relative_path)
    with pytest.raises(AssertionError, match="key_binding_resume_view_projection_changed"):
        key_binding_resume_historical_view(source.split(separator, 1)[0] + separator + other_source.split(separator, 1)[1], relative_path)


@pytest.mark.parametrize("path", ("", "docs/unapproved.md", "backend/repository.py"))
def test_key_binding_resume_projection_has_no_default_path(path: str) -> None:
    """KBRG-06: no fallback seal is accepted for unregistered documents."""
    source = recovery_scope_historical_view(recovery_resume_historical_view(dataset_scope_historical_view(dataset_resume_historical_view(overlay_scope_historical_view(overlay_resume_historical_view(ci_scope_historical_view(ci_resume_historical_view(ci_amend_historical_view((Path(__file__).resolve().parents[1] / CONSUMPTION_VIEW_PATHS[0]).read_bytes(), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0]), CONSUMPTION_VIEW_PATHS[0])
    with pytest.raises(AssertionError, match="key_binding_resume_view_path"):
        key_binding_resume_historical_view(source, path)


def test_key_binding_resume_requires_raw_view_bytes_and_preserves_reviewed_design() -> None:
    """KBRG-06/08: source bytes and immutable design remain independent evidence."""
    root = Path(__file__).resolve().parents[1]
    path = CONSUMPTION_VIEW_PATHS[0]
    with pytest.raises(AssertionError, match="key_binding_resume_view_source_bytes"):
        key_binding_resume_historical_view((root / path).read_text(), path)
    assert git_blob_sha((root / "docs/FC20-12-F01A-KEY-FINGERPRINT-SCOPE-PROPOSAL-2026-10-12.md").read_bytes()) == "c932029f3c64ba0473596947e42ae1bdc1fcd51f", "key_binding_resume_design_changed"


@pytest.mark.parametrize("container,keys", (("decision", tuple(KEY_BINDING_RESUME_DECISION)), ("subject", tuple(KEY_BINDING_RESUME_DECISION["subject"]))))
def test_key_binding_resume_requires_each_decision_and_subject_field(container: str, keys: tuple) -> None:
    """KBRG-03: complete receipt and exact subject are mandatory, not optional metadata."""
    for field in keys:
        manifest = historical_key_binding_resume_manifest()
        target = defensive_record(manifest)["events"][15]["owner_resume_decision"]
        if container == "subject":
            target = target["subject"]
        target.pop(field)
        with pytest.raises(AssertionError, match="defensive_record_mismatch"):
            _validate_key_binding_resume_structure(defensive_record(manifest), manifest["execution_sequence"]["active_target"])


@pytest.mark.parametrize("path", [p for p in index_resume_leaf_paths(KEY_BINDING_RESUME_RECORD) if p[-1] == "unique"])
@pytest.mark.parametrize("value", (0, 1, "false", None))
def test_key_binding_resume_operation_booleans_are_literal_in_every_copy(path: list, value: object) -> None:
    """KBRG-03: copied historical and current operations reject false-like integers."""
    manifest = historical_key_binding_resume_manifest()
    target = defensive_record(manifest)
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(AssertionError):
        _validate_key_binding_resume_structure(defensive_record(manifest), manifest["execution_sequence"]["active_target"])



def test_key_binding_resume_nested_operation_mutation_inventory_is_nonempty() -> None:
    """KBRG-03: a list-blind enumerator must not silently skip operation copies."""
    paths = [p for p in index_resume_leaf_paths(KEY_BINDING_RESUME_RECORD) if p[-1] == "unique"]
    assert ("allowed_schema_operations", 0, "unique") in paths
    assert ("events", 15, "owner_resume_decision", "subject", "allowed_schema_operations", 0, "unique") in paths
    assert len(paths) >= 3


@pytest.mark.parametrize("field", tuple(KEY_BINDING_REPAIR_SCOPE))
@pytest.mark.parametrize("mutation", ("missing", "changed"))
def test_key_binding_resume_pins_each_registered_repair_scope_field(field: str, mutation: str) -> None:
    """KBRG-03/08: the implementation subject is exactly the registered repair."""
    record = deepcopy(KEY_BINDING_RESUME_RECORD)
    scope = record["events"][15]["owner_resume_decision"]["subject"]["repair_scope"]
    if mutation == "missing":
        scope.pop(field)
    else:
        scope[field] = "UNRESTRICTED"
    with pytest.raises(AssertionError, match="defensive_record_mismatch"):
        _validate_key_binding_resume_structure(record, DEFENSIVE_START_TARGET)


@pytest.mark.parametrize("mutation", ("index_activities", "preparation_receipt", "preparation_time", "extra_repair_field", "extra_schema", "wrong_design", "wrong_application", "extra_implementation_path"))
def test_key_binding_resume_never_reuses_index_or_preparation_authority(mutation: str) -> None:
    """KBRG-07/08: preservation of prior index metadata grants no new index work."""
    record = deepcopy(KEY_BINDING_RESUME_RECORD)
    decision = record["events"][15]["owner_resume_decision"]
    subject = decision["subject"]
    if mutation == "index_activities":
        subject["execution_scope"]["activities"] = deepcopy(INDEX_RESUME_EXECUTION_SCOPE["activities"])
    elif mutation == "preparation_receipt":
        decision["record_url"] = KEY_BINDING_SCOPE_DECISION["record_url"]
    elif mutation == "preparation_time":
        decision["recorded_at"] = "2026-10-12T17:37:18Z"
    elif mutation == "extra_repair_field":
        subject["repair_scope"]["trusted_override"] = True
    elif mutation == "extra_schema":
        subject["repair_scope"]["additional_schema_operations"].append(deepcopy(INDEX_OPERATION))
    elif mutation == "wrong_design":
        decision["proposal_commit_sha"] = INDEX_RESUME_DECISION["proposal_commit_sha"]
    elif mutation == "wrong_application":
        subject["application_head_sha"] = subject["baseline_commit_sha"]
    else:
        subject["execution_scope"]["implementation_paths"].append("backend/asie_local_api.py")
    with pytest.raises(AssertionError, match="defensive_record_mismatch"):
        _validate_key_binding_resume_structure(record, DEFENSIVE_START_TARGET)


def test_key_binding_resume_inverse_matches_deepcopy_reference_without_aliases() -> None:
    """KBRG-05: optimized restoration preserves exact bytes and detached JSON trees."""
    manifest = historical_key_binding_resume_manifest()
    input_bytes = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    constants_bytes = json.dumps(KEY_BINDING_RESUME_RECORD, sort_keys=True)
    reference = deepcopy(manifest)
    record = defensive_record(reference)
    _validate_key_binding_resume_structure(record, reference["execution_sequence"]["active_target"])
    assert record["events"].pop() == KEY_BINDING_RESUME_EVENT
    record["execution_authorized"] = False
    reference_bytes = (json.dumps(reference, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    assert git_blob_sha(reference_bytes) == "6c0defd45b71bd8b28dc85d109e5bc7d1d3e8628"
    validate_key_binding_scope(record, reference["execution_sequence"]["active_target"])
    restored = _key_binding_resume_historical_inverse(manifest)
    second = _key_binding_resume_historical_inverse(manifest)
    assert (json.dumps(restored, ensure_ascii=False, indent=2) + "\n").encode("utf-8") == reference_bytes
    assert json.dumps(manifest, ensure_ascii=False, indent=2) + "\n" == input_bytes

    def container_ids(value: object) -> set[int]:
        if isinstance(value, dict):
            return {id(value)}.union(*(container_ids(item) for item in value.values()))
        if isinstance(value, list):
            return {id(value)}.union(*(container_ids(item) for item in value))
        return set()

    output_ids = container_ids(restored)
    for other in (manifest, second, KEY_BINDING_RESUME_RECORD, KEY_BINDING_SCOPE_RECORD):
        assert output_ids.isdisjoint(container_ids(other))
    defensive_record(restored)["events"][0]["type"] = "MUTATED_RETURN_VALUE"
    restored["packages"][0]["state"] = "MUTATED_RETURN_VALUE"
    assert json.dumps(manifest, ensure_ascii=False, indent=2) + "\n" == input_bytes
    assert json.dumps(KEY_BINDING_RESUME_RECORD, sort_keys=True) == constants_bytes
    assert (json.dumps(second, ensure_ascii=False, indent=2) + "\n").encode("utf-8") == reference_bytes
    subsequent = _key_binding_resume_historical_inverse(manifest)
    assert (json.dumps(subsequent, ensure_ascii=False, indent=2) + "\n").encode("utf-8") == reference_bytes


@pytest.mark.parametrize("corruption", ["structure", "literal_type", "unrelated_manifest"])
def test_key_binding_resume_inverse_rejection_does_not_mutate_input(corruption: str) -> None:
    """KBRG-05: rejected structure and unrelated bytes retain caller-owned data."""
    manifest = historical_key_binding_resume_manifest()
    if corruption == "structure":
        defensive_record(manifest)["events"][-1]["type"] = "UNKNOWN"
    elif corruption == "literal_type":
        defensive_record(manifest)["execution_authorized"] = 1
    else:
        manifest["program_id"] = "UNRELATED_CORRUPTION"
    before = json.dumps(manifest, sort_keys=True)
    with pytest.raises(AssertionError):
        _key_binding_resume_historical_inverse(manifest)
    assert json.dumps(manifest, sort_keys=True) == before


def test_manifest_byte_rejection_does_not_build_ci_diff(monkeypatch: pytest.MonkeyPatch) -> None:
    """CS-05: exact byte denial stays bounded even with CI assertion diagnostics."""
    import difflib

    manifest = load_manifest()
    tampered = (json.dumps(manifest, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
    diff_calls = []

    def unexpected_diff(*args, **kwargs):
        diff_calls.append(True)
        raise RuntimeError("unexpected_manifest_relational_diff")

    monkeypatch.setenv("CI", "true")
    monkeypatch.setattr(Path, "read_bytes", lambda _path: tampered)
    monkeypatch.setattr(difflib, "ndiff", unexpected_diff)
    with pytest.raises(AssertionError, match=r"^manifest_noncanonical_source(?:\n|$)"):
        load_manifest()
    assert not diff_calls, "manifest_rejection_constructed_relational_diff"


# CRSG: stopped recovery registration, never application execution authority.
RECOVERY_REPAIR_SCOPE = json.loads(r'''{
  "purpose": "CANONICAL_CUSTOMER_RECOVERY_AND_T08_ACCEPTANCE_ONLY",
  "implementation_paths": [
    "backend/asie_local_api.py",
    "backend/workspace.py",
    "backend/workflow.py",
    "backend/dib_api.py",
    "backend/dib_persistence.py",
    "backend/dib_tenant_api.py",
    "backend/dib_http_mounting.py",
    "backend/release_info.py",
    "src/contracts.ts",
    "src/dibApi.ts",
    "src/App.tsx",
    "src/customerLanguage.tsx",
    "src/ASIECompleteSurfaceMount.tsx",
    "src/DIBWorkspace.tsx",
    "src/DIBIntakeItemGovernance.tsx",
    "src/DIBManifestRunReadiness.tsx",
    "registry/asie-canonical-api-output.v1.json",
    "docs/ASIE-CANONICAL-API-OUTPUT-REGISTER-v1.0.0.md",
    "tests/test_customer_language_foundation.py",
    "tests/test_gov_beta_04_server_owned_manifest_chain.py",
    "tests/test_context_recovery_api.py",
    "tests/test_dib_context_recovery.py",
    "tests/test_customer_capability_projection.py",
    "tools/check_context_recovery_browser.py"
  ],
  "source_of_truth": "EXISTING_DIB_PROJECT_EVIDENCE_OWNERS_NO_PARALLEL_STORE_OR_ROUTE",
  "read_boundary": "TENANT_SCOPED_CONSISTENT_STORED_SESSION_BLUEPRINT_ID_REVISION_HASH_WITH_CURRENT_PROJECT_ACCESS",
  "write_boundary": "EXISTING_DIB_PERSISTENCE_ALL_UPDATES_ATOMIC_CAS_WITH_NEW_SERVER_BLUEPRINT_ID_AND_EXISTING_CHAIN_INVALIDATION",
  "compatibility": "REJECT_LEGACY_UPDATES_WITHOUT_EXPECTED_ORIGINAL_VERSION_NO_SILENT_OVERWRITE_OR_BACKFILL",
  "historical_snapshot_policy": "IMMUTABLE_EXPLICITLY_SEPARATE_FROM_CURRENT_DRAFT",
  "error_boundary": "CLOSED_SAFE_CODES_IN_DIB_API_TENANT_DIRECT_GET_AND_HTTP_PRECONTROLLER",
  "capability_declaration": "NEW_VERSIONED_PRODUCT_ENGINEERING_DISPLAY_ONLY_DECLARATION_IN_EXISTING_RELEASE_INFO_NO_RUNTIME_AUTHORITY",
  "target_mapping": "EXACT_REQUIRED_DEFICIT_OWNER_AND_LOCATION_NO_GENERIC_FALLBACK_FOR_KNOWN_REQUIRED_DEFICITS",
  "customer_presentation": "PRESERVE_WORK_SCOPED_RETURN_AR_EN_LOCAL_DETERMINISTIC_SANAD_NO_VOICE",
  "contract_change_scope": [
    "EXISTING_DIB_SESSION_READ_SERVER_RECORD_REFERENCE",
    "VERSIONED_EXISTING_BLUEPRINT_WRITE_PRECONDITIONS_ALL_THREE_EXISTING_CALLERS",
    "ALLOWLISTED_EXISTING_WORKSPACE_RECOVERY_AND_DISPLAY_PROJECTION",
    "CANONICAL_API_REGISTER_AND_COMPATIBILITY_DOCUMENTATION"
  ],
  "additional_schema_operations": [],
  "database_and_data_scope": "DISPOSABLE_TEMPORARY_DATABASES_SYNTHETIC_DATA_ONLY",
  "application_merge_authorized": false,
  "live_database_authorized": false,
  "network_provider_deployment_authorized": false,
  "production_startup_acceptance": "UNKNOWN_NOT_APPROVED",
  "acceptance_plan": "ACCEPTED_DESIGN_R01_R14_AND_ORIGINAL_T01_T09_NO_WAIVER",
  "excluded_changes": [
    "FROZEN_RUNTIME_ENGINES_FINANCE_SNAPSHOT_AAS_DECISION_COUNCIL",
    "F01B_CONTEXT_BUILDING_OR_ROUTING_ACTIVATION",
    "IDENTITY_ROLES_OR_ADMIN_RELEASE_INFO_EXPOSURE",
    "RUNTIME_ENABLE_FLAGS_OR_PARALLEL_STORE_SERVICE_ROUTE",
    "VOICE_AGENT",
    "ADDITIONAL_SCHEMA_OPERATIONS_OR_AUDIT_ORIGIN_INDEX_QUERY_PROOF_CHANGES",
    "LIVE_OWNER_DATABASE_OR_DEPLOYMENT_OR_APPLICATION_PR_MERGE"
  ]
}''')
RECOVERY_STOP_EVENT = json.loads(r'''{
  "type": "STOP_CHECKPOINT",
  "recorded_at": "2026-10-14T10:06:03Z",
  "baseline_commit_sha": "fc7ceec7ba910a6433427d19193955e78e1ac922",
  "baseline_manifest_blob_sha": "a8785adda21236df9320c7c2ff0aac8a7628c7ab",
  "application_head_sha": "b011a6b3773f4c5e0a905161b5504fff339496f6",
  "reason": "CUSTOMER_RECOVERY_CONTRACT_AND_PATH_EXTENSION_OUTSIDE_KEY_BINDING_RESUME",
  "evidence": {
    "url": "https://github.com/alphasigma13579-lang/ASIE/blob/d2e9399a61b4a939fa174a8c9bada7bd699c2990/ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/docs/FC20-12-F01A-CUSTOMER-RECOVERY-ACCEPTANCE-SCOPE-PROPOSAL-2026-10-14.md",
    "commit_sha": "d2e9399a61b4a939fa174a8c9bada7bd699c2990",
    "blob_sha": "51cc1b68aee8f88db1b7e1569c6f1f9f74206e1b"
  },
  "resume_requirement": "NEW_OWNER_DECISION_BOUND_TO_ACCEPTED_RECOVERY_SCOPE_COMPATIBILITY_AND_REVIEWED_EXACT_HEAD_GOVERNANCE_TRANSITION"
}''')
RECOVERY_SCOPE_DECISION = json.loads(r'''{
  "id": "DECISION-FC20-12-F01A-CUSTOMER-RECOVERY-SCOPE-REGISTRATION-PREPARATION-2026-10-14",
  "record_url": "https://github.com/alphasigma13579-lang/ASIE/pull/207#issuecomment-6165892821",
  "recorded_at": "2026-10-14T10:05:05.909423+00:00",
  "effect": "PREPARE_AND_PUBLISH_GOVERNANCE_DRAFT_ONLY_NO_MERGE_NO_RESUME",
  "subject": {
    "baseline_commit_sha": "fc7ceec7ba910a6433427d19193955e78e1ac922",
    "baseline_manifest_blob_sha": "a8785adda21236df9320c7c2ff0aac8a7628c7ab",
    "application_head_sha": "b011a6b3773f4c5e0a905161b5504fff339496f6",
    "allowed_paths": [
      "backend/asie_local_api.py",
      "backend/repository.py",
      "backend/intelligence_prerun_service.py",
      "tests/test_repository_intelligence.py",
      "tests/test_intelligence_prerun_service.py",
      "tests/test_intelligence_context_ingress_api.py",
      "docs/FC20-12-F01-TRUSTED-CONTEXT-INGRESS-REPAIR-PLAN-2026-10-01.md",
      "tests/test_live_location_api.py",
      "tests/test_intelligence_consumption.py",
      "backend/workspace.py",
      "backend/workflow.py",
      "backend/dib_api.py",
      "backend/dib_persistence.py",
      "backend/dib_tenant_api.py",
      "backend/dib_http_mounting.py",
      "backend/release_info.py",
      "src/contracts.ts",
      "src/dibApi.ts",
      "src/App.tsx",
      "src/customerLanguage.tsx",
      "src/ASIECompleteSurfaceMount.tsx",
      "src/DIBWorkspace.tsx",
      "src/DIBIntakeItemGovernance.tsx",
      "src/DIBManifestRunReadiness.tsx",
      "registry/asie-canonical-api-output.v1.json",
      "docs/ASIE-CANONICAL-API-OUTPUT-REGISTER-v1.0.0.md",
      "tests/test_customer_language_foundation.py",
      "tests/test_gov_beta_04_server_owned_manifest_chain.py",
      "tests/test_context_recovery_api.py",
      "tests/test_dib_context_recovery.py",
      "tests/test_customer_capability_projection.py",
      "tools/check_context_recovery_browser.py"
    ],
    "allowed_schema_operations": [
      {
        "operation": "CREATE_INDEX_IF_NOT_EXISTS",
        "index_name": "idx_security_audit_origin_proof",
        "table": "security_audit_events",
        "columns": [
          "action",
          "target_type",
          "target_id",
          "organization_id"
        ],
        "unique": false,
        "implementation_path": "backend/repository.py",
        "test_path": "tests/test_repository_intelligence.py"
      }
    ],
    "repair_scope": {
      "purpose": "CANONICAL_CUSTOMER_RECOVERY_AND_T08_ACCEPTANCE_ONLY",
      "implementation_paths": [
        "backend/asie_local_api.py",
        "backend/workspace.py",
        "backend/workflow.py",
        "backend/dib_api.py",
        "backend/dib_persistence.py",
        "backend/dib_tenant_api.py",
        "backend/dib_http_mounting.py",
        "backend/release_info.py",
        "src/contracts.ts",
        "src/dibApi.ts",
        "src/App.tsx",
        "src/customerLanguage.tsx",
        "src/ASIECompleteSurfaceMount.tsx",
        "src/DIBWorkspace.tsx",
        "src/DIBIntakeItemGovernance.tsx",
        "src/DIBManifestRunReadiness.tsx",
        "registry/asie-canonical-api-output.v1.json",
        "docs/ASIE-CANONICAL-API-OUTPUT-REGISTER-v1.0.0.md",
        "tests/test_customer_language_foundation.py",
        "tests/test_gov_beta_04_server_owned_manifest_chain.py",
        "tests/test_context_recovery_api.py",
        "tests/test_dib_context_recovery.py",
        "tests/test_customer_capability_projection.py",
        "tools/check_context_recovery_browser.py"
      ],
      "source_of_truth": "EXISTING_DIB_PROJECT_EVIDENCE_OWNERS_NO_PARALLEL_STORE_OR_ROUTE",
      "read_boundary": "TENANT_SCOPED_CONSISTENT_STORED_SESSION_BLUEPRINT_ID_REVISION_HASH_WITH_CURRENT_PROJECT_ACCESS",
      "write_boundary": "EXISTING_DIB_PERSISTENCE_ALL_UPDATES_ATOMIC_CAS_WITH_NEW_SERVER_BLUEPRINT_ID_AND_EXISTING_CHAIN_INVALIDATION",
      "compatibility": "REJECT_LEGACY_UPDATES_WITHOUT_EXPECTED_ORIGINAL_VERSION_NO_SILENT_OVERWRITE_OR_BACKFILL",
      "historical_snapshot_policy": "IMMUTABLE_EXPLICITLY_SEPARATE_FROM_CURRENT_DRAFT",
      "error_boundary": "CLOSED_SAFE_CODES_IN_DIB_API_TENANT_DIRECT_GET_AND_HTTP_PRECONTROLLER",
      "capability_declaration": "NEW_VERSIONED_PRODUCT_ENGINEERING_DISPLAY_ONLY_DECLARATION_IN_EXISTING_RELEASE_INFO_NO_RUNTIME_AUTHORITY",
      "target_mapping": "EXACT_REQUIRED_DEFICIT_OWNER_AND_LOCATION_NO_GENERIC_FALLBACK_FOR_KNOWN_REQUIRED_DEFICITS",
      "customer_presentation": "PRESERVE_WORK_SCOPED_RETURN_AR_EN_LOCAL_DETERMINISTIC_SANAD_NO_VOICE",
      "contract_change_scope": [
        "EXISTING_DIB_SESSION_READ_SERVER_RECORD_REFERENCE",
        "VERSIONED_EXISTING_BLUEPRINT_WRITE_PRECONDITIONS_ALL_THREE_EXISTING_CALLERS",
        "ALLOWLISTED_EXISTING_WORKSPACE_RECOVERY_AND_DISPLAY_PROJECTION",
        "CANONICAL_API_REGISTER_AND_COMPATIBILITY_DOCUMENTATION"
      ],
      "additional_schema_operations": [],
      "database_and_data_scope": "DISPOSABLE_TEMPORARY_DATABASES_SYNTHETIC_DATA_ONLY",
      "application_merge_authorized": false,
      "live_database_authorized": false,
      "network_provider_deployment_authorized": false,
      "production_startup_acceptance": "UNKNOWN_NOT_APPROVED",
      "acceptance_plan": "ACCEPTED_DESIGN_R01_R14_AND_ORIGINAL_T01_T09_NO_WAIVER",
      "excluded_changes": [
        "FROZEN_RUNTIME_ENGINES_FINANCE_SNAPSHOT_AAS_DECISION_COUNCIL",
        "F01B_CONTEXT_BUILDING_OR_ROUTING_ACTIVATION",
        "IDENTITY_ROLES_OR_ADMIN_RELEASE_INFO_EXPOSURE",
        "RUNTIME_ENABLE_FLAGS_OR_PARALLEL_STORE_SERVICE_ROUTE",
        "VOICE_AGENT",
        "ADDITIONAL_SCHEMA_OPERATIONS_OR_AUDIT_ORIGIN_INDEX_QUERY_PROOF_CHANGES",
        "LIVE_OWNER_DATABASE_OR_DEPLOYMENT_OR_APPLICATION_PR_MERGE"
      ]
    }
  },
  "proposal_commit_sha": "d2e9399a61b4a939fa174a8c9bada7bd699c2990",
  "proposal_blob_sha": "51cc1b68aee8f88db1b7e1569c6f1f9f74206e1b"
}''')
RECOVERY_SCOPE_DECISION["subject"]["baseline_record"] = deepcopy(KEY_BINDING_RESUME_RECORD)
RECOVERY_SCOPE_DECISION["subject"]["previous_resume"] = deepcopy(KEY_BINDING_RESUME_EVENT)
RECOVERY_SCOPE_EVENT = json.loads(r'''{
  "type": "SCOPE_EXTENSION",
  "recorded_at": "2026-10-14T10:06:03Z",
  "baseline_commit_sha": "fc7ceec7ba910a6433427d19193955e78e1ac922",
  "baseline_manifest_blob_sha": "a8785adda21236df9320c7c2ff0aac8a7628c7ab",
  "application_head_sha": "b011a6b3773f4c5e0a905161b5504fff339496f6",
  "added_paths": [
    "backend/workspace.py",
    "backend/workflow.py",
    "backend/dib_api.py",
    "backend/dib_persistence.py",
    "backend/dib_tenant_api.py",
    "backend/dib_http_mounting.py",
    "backend/release_info.py",
    "src/contracts.ts",
    "src/dibApi.ts",
    "src/App.tsx",
    "src/customerLanguage.tsx",
    "src/ASIECompleteSurfaceMount.tsx",
    "src/DIBWorkspace.tsx",
    "src/DIBIntakeItemGovernance.tsx",
    "src/DIBManifestRunReadiness.tsx",
    "registry/asie-canonical-api-output.v1.json",
    "docs/ASIE-CANONICAL-API-OUTPUT-REGISTER-v1.0.0.md",
    "tests/test_customer_language_foundation.py",
    "tests/test_gov_beta_04_server_owned_manifest_chain.py",
    "tests/test_context_recovery_api.py",
    "tests/test_dib_context_recovery.py",
    "tests/test_customer_capability_projection.py",
    "tools/check_context_recovery_browser.py"
  ],
  "scope_addendum": {
    "url": "https://github.com/alphasigma13579-lang/ASIE/blob/d2e9399a61b4a939fa174a8c9bada7bd699c2990/ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/docs/FC20-12-F01A-CUSTOMER-RECOVERY-ACCEPTANCE-SCOPE-PROPOSAL-2026-10-14.md",
    "commit_sha": "d2e9399a61b4a939fa174a8c9bada7bd699c2990",
    "blob_sha": "51cc1b68aee8f88db1b7e1569c6f1f9f74206e1b"
  },
  "effect": "SCOPE_EXTENSION_ONLY_NO_RESUME"
}''')
RECOVERY_SCOPE_EVENT["owner_scope_decision"] = deepcopy(RECOVERY_SCOPE_DECISION)
RECOVERY_SCOPE_RECORD = deepcopy(KEY_BINDING_RESUME_RECORD)
RECOVERY_SCOPE_RECORD["execution_authorized"] = False
RECOVERY_SCOPE_RECORD["allowed_paths"].extend(RECOVERY_SCOPE_EVENT["added_paths"])
RECOVERY_SCOPE_RECORD["events"].extend([deepcopy(RECOVERY_STOP_EVENT), deepcopy(RECOVERY_SCOPE_EVENT)])
RECOVERY_VIEW_PREFIX_BLOBS = json.loads(r'''{
  "docs/FOUNDATION-COMPLETE-20-CORE-INTELLIGENCE-COMPLETION-PROGRAM-2026-07-29.md": "08d8cbe265ec5e999ddc70de2669749d4ac22287",
  "docs/EKB/FOUNDATION-COMPLETE-20-PACKAGE-INDEX.md": "b6f9897cddf6ba0532ee0c92a99f8ce43f1051ca",
  "docs/ASIE-BETA-EXECUTION-MASTER-PLAN-2026-09-09.md": "0f6f44cfc85660f8099be1fbdc77d8245855892c",
  "docs/FC20-12-F01A-DEFENSIVE-ENABLING-REGISTRATION-PROPOSAL-2026-10-01.md": "d3439aed418aaac6ab8d4185d58e4d014e0168a9",
  "docs/FC20-12-F01A-APPROVAL-CONSUMPTION-SCOPE-REGISTRATION-2026-10-09.md": "00e5ac10dea0013051306954c5abb7643dc78be3"
}''')
RECOVERY_VIEW_SHA256 = json.loads(r'''{
  "docs/FOUNDATION-COMPLETE-20-CORE-INTELLIGENCE-COMPLETION-PROGRAM-2026-07-29.md": "524abe7e232166fdeeff68daf883c591b2736c0a269ca34c3ddb1ec625fbba9d",
  "docs/EKB/FOUNDATION-COMPLETE-20-PACKAGE-INDEX.md": "73c96595bfb1c99b84adecd1b4aba4f25af3154c59c1dddd5757965ea73b56fd",
  "docs/ASIE-BETA-EXECUTION-MASTER-PLAN-2026-09-09.md": "422d2218f0956f797071e89d99cdcc3c6b199545822a86c25c483c7b7e5e3d89",
  "docs/FC20-12-F01A-DEFENSIVE-ENABLING-REGISTRATION-PROPOSAL-2026-10-01.md": "e1d04bedd35d4794a74072406749949a54f2e9a733ea3b281aa9e57bbc222b42",
  "docs/FC20-12-F01A-APPROVAL-CONSUMPTION-SCOPE-REGISTRATION-2026-10-09.md": "97144983bf56d6be8b7e67821063d077aa2b3b4ece75586e5ce118ba87c7cba5"
}''')
RECOVERY_VIEW_MARKER = '<!-- F01A-CUSTOMER-RECOVERY-SCOPE-REGISTRATION-2026-10-14 -->'


def _validate_recovery_structure(record: dict, active_target: object) -> None:
    """CRSG-01/02: pin typed scope and history independently; no receipt admission."""
    assert isinstance(record, dict), "invalid_defensive_record"
    assert set(record) == set(RECOVERY_SCOPE_RECORD), "defensive_fields"
    # Do not ask pytest to construct a multi-megabyte relational failure diff.
    if record != RECOVERY_SCOPE_RECORD:
        raise AssertionError("defensive_record_mismatch")
    if json.dumps(record, sort_keys=True) != json.dumps(RECOVERY_SCOPE_RECORD, sort_keys=True):
        raise AssertionError("recovery_literal_types")
    assert record["execution_authorized"] is False, "recovery_stop_flag"
    assert active_target == DEFENSIVE_START_TARGET, "recovery_slot"
    assert record["allowed_paths"][:9] == KEY_BINDING_RESUME_RECORD["allowed_paths"], "recovery_original_paths"
    assert len(record["allowed_paths"]) == len(set(record["allowed_paths"])) == 32, "recovery_union_paths"
    assert len(RECOVERY_REPAIR_SCOPE["implementation_paths"]) == 24, "recovery_batch_paths"
    assert len(record["events"][17]["added_paths"]) == 23, "recovery_added_paths"
    assert record["allowed_schema_operations"] == [INDEX_OPERATION], "recovery_schema_operation"
    assert record["allowed_schema_operations"][0]["unique"] is False, "recovery_index_literal"
    assert "added_schema_operations" not in record["events"][17], "recovery_no_added_schema"


def validate_recovery_scope(record: dict, active_target: object) -> None:
    """CRSG-03: only the actual pinned preparation/publication receipt is admitted."""
    _validate_recovery_structure(record, active_target)
    decision = record["events"][17]["owner_scope_decision"]
    assert decision["record_url"] == "https://github.com/alphasigma13579-lang/ASIE/pull/207#issuecomment-6165892821", "recovery_receipt_missing"
    assert decision["recorded_at"] == "2026-10-14T10:05:05.909423+00:00", "recovery_decision_time"
    assert decision["effect"] == "PREPARE_AND_PUBLISH_GOVERNANCE_DRAFT_ONLY_NO_MERGE_NO_RESUME", "recovery_no_execution_authority"


def _recovery_scope_historical_inverse(manifest: dict) -> dict:
    """CRSG-04: detach a byte-verified sixteen-event history, never current authority."""
    original = defensive_record(manifest)
    _validate_recovery_structure(original, manifest["execution_sequence"]["active_target"])
    restored = dict(manifest)
    restored["packages"] = list(manifest["packages"])
    index = next(i for i, p in enumerate(manifest["packages"]) if p["id"] == "FC20-12")
    package = dict(manifest["packages"][index])
    restored["packages"][index] = package
    package["execution_slices"] = list(package["execution_slices"])
    record = dict(original)
    package["execution_slices"][1] = record
    record["events"] = list(original["events"][:16])
    record["allowed_paths"] = list(original["allowed_paths"][:9])
    record["execution_authorized"] = True
    source = (json.dumps(restored, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    assert git_blob_sha(source) == "a8785adda21236df9320c7c2ff0aac8a7628c7ab", "recovery_baseline_mismatch"
    detached = json.loads(source)
    validate_key_binding_resume(defensive_record(detached), detached["execution_sequence"]["active_target"])
    return detached


def validate_recovery_scope_baseline(manifest: dict) -> dict:
    """CRSG-03/04: current receipt admission must precede the public inverse."""
    validate_recovery_scope(defensive_record(manifest), manifest["execution_sequence"]["active_target"])
    return _recovery_scope_historical_inverse(manifest)


_RECOVERY_HISTORY_BYTES: tuple[bytes, bytes] | None = None


@lru_cache(maxsize=2, typed=True)
def _key_binding_cached_blob_sha(raw: bytes) -> str:
    """Memoize only exact immutable content digests, never fixture admission."""
    return git_blob_sha(raw)


def key_binding_fixture_blob_sha(raw: bytes) -> str:
    """Retain original buffer/subclass behavior outside the exact-bytes cache."""
    return _key_binding_cached_blob_sha(raw) if type(raw) is bytes else git_blob_sha(raw)


def historical_key_binding_resume_manifest() -> dict:
    """CRSG-04: re-pin every source read; cache only inverse-verified immutable bytes."""
    global _RECOVERY_HISTORY_BYTES
    source = recovery_resume_historical_source_bytes()
    assert key_binding_fixture_blob_sha(source) == "3e8c82ea894af7d72865229f72d0b9c576d7da31", "recovery_fixture_source_changed"
    if _RECOVERY_HISTORY_BYTES is None:
        # Validate exactly the bytes above, not a second potentially changed read.
        verified = _recovery_scope_historical_inverse(json.loads(source.decode("utf-8")))
        baseline = (json.dumps(verified, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        assert key_binding_fixture_blob_sha(baseline) == "a8785adda21236df9320c7c2ff0aac8a7628c7ab", "recovery_fixture_baseline_changed"
        _RECOVERY_HISTORY_BYTES = (source, baseline)
    assert isinstance(_RECOVERY_HISTORY_BYTES, tuple) and len(_RECOVERY_HISTORY_BYTES) == 2, "recovery_fixture_cache_shape"
    cached_source, baseline = _RECOVERY_HISTORY_BYTES
    assert isinstance(cached_source, bytes) and isinstance(baseline, bytes), "recovery_fixture_cache_type"
    source_matches = source == cached_source
    assert source_matches, "recovery_fixture_cache_source_changed"
    assert key_binding_fixture_blob_sha(baseline) == "a8785adda21236df9320c7c2ff0aac8a7628c7ab", "recovery_fixture_baseline_changed"
    # No parsed dictionaries/lists or aliases survive between cases.
    return json.loads(baseline.decode("utf-8"))


def recovery_scope_historical_view(source_bytes: bytes, relative_path: str) -> bytes:
    """CRSG-05: require exact path-specific prefix and new projection bytes."""
    assert isinstance(source_bytes, bytes), "recovery_view_source_bytes"
    assert relative_path in RECOVERY_VIEW_SHA256, "recovery_view_path"
    marker = RECOVERY_VIEW_MARKER.encode()
    separator = b"\n" + marker + b"\n"
    assert source_bytes.count(marker) == 1, "recovery_view_marker"
    assert source_bytes.count(separator) == 1, "recovery_view_boundary"
    prefix, section = source_bytes.split(separator, 1)
    assert git_blob_sha(prefix) == RECOVERY_VIEW_PREFIX_BLOBS[relative_path], "recovery_view_prefix_changed"
    assert hashlib.sha256(marker + b"\n" + section).hexdigest() == RECOVERY_VIEW_SHA256[relative_path], "recovery_view_projection_changed"
    key_binding_resume_historical_view(prefix, relative_path)
    return prefix


def test_recovery_scope_admits_only_stopped_pinned_registration() -> None:
    """CRSG-01/03/04: current admission, exact inverse and every historical oracle."""
    manifest = historical_recovery_scope_manifest()
    validate_routing_registration(load_manifest())
    record = defensive_record(manifest)
    assert record["events"][:16] == KEY_BINDING_RESUME_RECORD["events"]
    assert record["execution_authorized"] is False and len(record["events"]) == 18
    prior = validate_recovery_scope_baseline(manifest)
    stopped = validate_key_binding_resume_baseline(prior)
    previous = validate_key_binding_scope_baseline(stopped)
    old_review_scope = validate_review_identity_resume_baseline(previous)
    old_index_resume = validate_review_identity_scope_baseline(old_review_scope)
    index_scope = validate_index_resume_baseline(old_index_resume)
    consumption_resume = validate_index_scope_baseline(index_scope)
    consumption_scope = validate_consumption_resume_baseline(consumption_resume)
    old_resume = validate_consumption_scope_baseline(consumption_scope)
    validate_scope_extension_baseline(validate_resume_baseline(old_resume))


def recovery_new_leaf_paths() -> list[tuple]:
    """CRSG-06: cover each new leaf without duplicating sealed historical matrices."""
    result = [(16,) + tuple(p) for p in index_resume_leaf_paths(RECOVERY_STOP_EVENT)]
    event = deepcopy(RECOVERY_SCOPE_EVENT)
    subject = event["owner_scope_decision"]["subject"]
    subject.pop("baseline_record")
    subject.pop("previous_resume")
    result.extend((17,) + tuple(p) for p in index_resume_leaf_paths(event))
    return result


@pytest.mark.parametrize("path", recovery_new_leaf_paths())
def test_recovery_scope_pins_each_new_leaf(path: tuple) -> None:
    """CRSG-06: tampering any newly introduced scalar fails before authority."""
    record = deepcopy(RECOVERY_SCOPE_RECORD)
    target = record["events"]
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = "UNREVIEWED"
    with pytest.raises(AssertionError, match="defensive_record_mismatch"):
        _validate_recovery_structure(record, DEFENSIVE_START_TARGET)


@pytest.mark.parametrize("event_index", (16, 17))
@pytest.mark.parametrize("mutation", ("missing", "extra"))
def test_recovery_scope_closed_event_fields(event_index: int, mutation: str) -> None:
    """CRSG-06: every event field remains required and unknown fields are denied."""
    for field in RECOVERY_SCOPE_RECORD["events"][event_index]:
        record = deepcopy(RECOVERY_SCOPE_RECORD)
        if mutation == "missing":
            record["events"][event_index].pop(field)
        else:
            record["events"][event_index]["unapproved"] = True
        with pytest.raises(AssertionError, match="defensive_record_mismatch"):
            _validate_recovery_structure(record, DEFENSIVE_START_TARGET)


@pytest.mark.parametrize("container", ("decision", "subject", "repair_scope"))
@pytest.mark.parametrize("mutation", ("missing", "extra"))
def test_recovery_scope_closed_nested_objects(container: str, mutation: str) -> None:
    """CRSG-06: no missing compatibility restriction or new permission is accepted."""
    decision = RECOVERY_SCOPE_EVENT["owner_scope_decision"]
    original = decision if container == "decision" else decision["subject"] if container == "subject" else RECOVERY_REPAIR_SCOPE
    for field in original:
        record = deepcopy(RECOVERY_SCOPE_RECORD)
        target = record["events"][17]["owner_scope_decision"]
        if container != "decision":
            target = target["subject"]
        if container == "repair_scope":
            target = target["repair_scope"]
        if mutation == "missing":
            target.pop(field)
        else:
            target["unapproved"] = True
        with pytest.raises(AssertionError, match="defensive_record_mismatch"):
            _validate_recovery_structure(record, DEFENSIVE_START_TARGET)


@pytest.mark.parametrize("copy_name", ("baseline_record", "previous_resume"))
@pytest.mark.parametrize("mutation", ("missing", "different", "literal_type"))
def test_recovery_scope_preserves_nested_history(copy_name: str, mutation: str) -> None:
    """CRSG-02: complete copies remain independently pinned, including JSON types."""
    record = deepcopy(RECOVERY_SCOPE_RECORD)
    subject = record["events"][17]["owner_scope_decision"]["subject"]
    if mutation == "missing":
        subject.pop(copy_name)
    elif mutation == "different":
        subject[copy_name]["type" if copy_name == "previous_resume" else "state"] = "UNKNOWN"
    elif copy_name == "baseline_record":
        subject[copy_name]["execution_authorized"] = 1
    else:
        subject[copy_name]["owner_resume_decision"]["subject"]["execution_scope"]["live_database_authorized"] = 0
    with pytest.raises(AssertionError, match="defensive_record_mismatch|recovery_literal_types"):
        _validate_recovery_structure(record, DEFENSIVE_START_TARGET)


@pytest.mark.parametrize("event_index", range(16))
def test_recovery_scope_preserves_each_historical_event(event_index: int) -> None:
    """CRSG-02: all original events remain byte-pinned through the exact inverse."""
    record = deepcopy(RECOVERY_SCOPE_RECORD)
    record["events"][event_index]["type"] = "CHANGED"
    with pytest.raises(AssertionError, match="defensive_record_mismatch"):
        _validate_recovery_structure(record, DEFENSIVE_START_TARGET)


@pytest.mark.parametrize("value", (True, 0, 1, None, "false"))
def test_recovery_scope_requires_literal_false(value: object) -> None:
    """CRSG-01: stopped execution cannot be represented by truthy/coerced values."""
    record = deepcopy(RECOVERY_SCOPE_RECORD)
    record["execution_authorized"] = value
    with pytest.raises(AssertionError, match="defensive_record_mismatch|recovery_literal_types"):
        validate_recovery_scope(record, DEFENSIVE_START_TARGET)


@pytest.mark.parametrize("field,value", (("record_url", "UNRESOLVED_OWNER_DECISION_RECORD_URL"), ("recorded_at", "UNRESOLVED"), ("effect", "F01A_DEFENSIVE_RESUME_ONLY")))
def test_recovery_scope_denies_missing_or_execution_receipt_at_all_current_seams(field: str, value: str) -> None:
    """CRSG-03: historical or preparation data cannot accidentally enable work."""
    manifest = historical_recovery_scope_manifest()
    defensive_record(manifest)["events"][17]["owner_scope_decision"][field] = value
    for validator in (validate_recovery_scope_baseline,):
        with pytest.raises(AssertionError, match="defensive_record_mismatch"):
            validator(manifest)


@pytest.mark.parametrize("mutation", ("reorder", "remove", "extra", "duplicate", "batch_union", "schema_extra", "index_zero", "slot_release", "hold_release", "unrelated"))
def test_recovery_scope_denies_scope_slot_schema_and_unrelated_drift(mutation: str) -> None:
    """CRSG-01/04/06: cumulative registration never broadens the active batch."""
    manifest = historical_recovery_scope_manifest()
    record = defensive_record(manifest)
    if mutation == "reorder":
        record["allowed_paths"][:2] = reversed(record["allowed_paths"][:2])
    elif mutation == "remove":
        record["allowed_paths"].pop()
    elif mutation in ("extra", "duplicate"):
        record["allowed_paths"].append("unapproved.py" if mutation == "extra" else record["allowed_paths"][0])
    elif mutation == "batch_union":
        record["events"][17]["owner_scope_decision"]["subject"]["repair_scope"]["implementation_paths"] = list(record["allowed_paths"])
    elif mutation == "schema_extra":
        record["events"][17]["added_schema_operations"] = []
    elif mutation == "index_zero":
        record["allowed_schema_operations"][0]["unique"] = 0
    elif mutation == "slot_release":
        manifest["execution_sequence"]["active_target"] = None
    elif mutation == "hold_release":
        manifest["execution_sequence"]["held_packages"] = []
    else:
        manifest["program_id"] = "UNRELATED_CORRUPTION"
    before = json.dumps(manifest, sort_keys=True)
    with pytest.raises(AssertionError):
        validate_recovery_scope_baseline(manifest)
    assert json.dumps(manifest, sort_keys=True) == before


def test_recovery_inverse_is_detached_and_does_not_mutate_sources() -> None:
    """CRSG-04: no mutable cache or alias shares historical state across cases."""
    manifest = historical_recovery_scope_manifest()
    before = json.dumps(manifest, sort_keys=True)
    first = validate_recovery_scope_baseline(manifest)
    second = validate_recovery_scope_baseline(manifest)
    defensive_record(first)["events"][0]["type"] = "CHANGED_RETURN"
    assert json.dumps(manifest, sort_keys=True) == before
    assert defensive_record(second)["events"][0]["type"] == KEY_BINDING_RESUME_RECORD["events"][0]["type"]
    assert RECOVERY_SCOPE_RECORD["events"][0]["type"] == KEY_BINDING_RESUME_RECORD["events"][0]["type"]


@pytest.mark.parametrize("relative_path", tuple(RECOVERY_VIEW_SHA256))
def test_recovery_scope_projection_matches_pinned_bytes(relative_path: str) -> None:
    """CRSG-05: path-specific old prefix and new section are both checked."""
    source = recovery_resume_historical_view(dataset_scope_historical_view(dataset_resume_historical_view(overlay_scope_historical_view(overlay_resume_historical_view(ci_scope_historical_view(ci_resume_historical_view(ci_amend_historical_view((Path(__file__).resolve().parents[1] / relative_path).read_bytes(), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path)
    prefix = recovery_scope_historical_view(source, relative_path)
    assert git_blob_sha(prefix) == RECOVERY_VIEW_PREFIX_BLOBS[relative_path]
    assert b"https://github.com/alphasigma13579-lang/ASIE/pull/207#issuecomment-6165892821" in source[len(prefix):]


@pytest.mark.parametrize("relative_path", tuple(RECOVERY_VIEW_SHA256))
@pytest.mark.parametrize("mutation", ("prefix", "section", "duplicate", "boundary", "swap"))
def test_recovery_scope_projection_tampering_rejected(relative_path: str, mutation: str) -> None:
    """CRSG-05: no marker, whitespace, or cross-path projection substitution."""
    root = Path(__file__).resolve().parents[1]
    source = recovery_resume_historical_view(dataset_scope_historical_view(dataset_resume_historical_view(overlay_scope_historical_view(overlay_resume_historical_view(ci_scope_historical_view(ci_resume_historical_view(ci_amend_historical_view((root / relative_path).read_bytes(), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path)
    separator = ("\n" + RECOVERY_VIEW_MARKER + "\n").encode()
    prefix, section = source.split(separator, 1)
    if mutation == "prefix":
        source = b" " + source
    elif mutation == "section":
        source += b" "
    elif mutation == "duplicate":
        source += separator
    elif mutation == "boundary":
        source = prefix + separator.replace(b"\n", b"\r\n") + section
    else:
        other = next(path for path in RECOVERY_VIEW_SHA256 if path != relative_path)
        source = prefix + separator + recovery_resume_historical_view(dataset_scope_historical_view(dataset_resume_historical_view(overlay_scope_historical_view(overlay_resume_historical_view(ci_scope_historical_view(ci_resume_historical_view(ci_amend_historical_view((root / other).read_bytes(), other), other), other), other), other), other), other), other).split(separator, 1)[1]
    with pytest.raises(AssertionError, match="recovery_view"):
        recovery_scope_historical_view(source, relative_path)


def test_recovery_scope_design_and_seal_inventory_are_exact() -> None:
    """CRSG-05/07: accepted design and five known projections cannot be swapped."""
    assert set(RECOVERY_VIEW_SHA256) == set(RECOVERY_VIEW_PREFIX_BLOBS) == set(KEY_BINDING_RESUME_VIEW_SHA256)
    root = Path(__file__).resolve().parents[1]
    path = "docs/FC20-12-F01A-CUSTOMER-RECOVERY-ACCEPTANCE-SCOPE-PROPOSAL-2026-10-14.md"
    assert git_blob_sha((root / path).read_bytes()) == "51cc1b68aee8f88db1b7e1569c6f1f9f74206e1b"
    with pytest.raises(AssertionError, match="recovery_view_path"):
        recovery_scope_historical_view(b"anything", "docs/unapproved.md")


def test_recovery_history_optimized_fixture_matches_uncached_inverse(monkeypatch: pytest.MonkeyPatch) -> None:
    """CRSG-08: cold/warm output bytes equal the original independently checked inverse."""
    import sys

    module = sys.modules[__name__]
    monkeypatch.setattr(module, "_RECOVERY_HISTORY_BYTES", None)
    manifest = historical_recovery_scope_manifest()
    original = _recovery_scope_historical_inverse(manifest)
    expected = json.dumps(original, ensure_ascii=False, indent=2) + "\n"
    first = historical_key_binding_resume_manifest()
    second = historical_key_binding_resume_manifest()
    assert json.dumps(first, ensure_ascii=False, indent=2) + "\n" == expected
    assert json.dumps(second, ensure_ascii=False, indent=2) + "\n" == expected
    assert isinstance(_RECOVERY_HISTORY_BYTES, tuple)
    assert all(isinstance(value, bytes) for value in _RECOVERY_HISTORY_BYTES)

    def container_ids(value: object) -> set[int]:
        if isinstance(value, dict):
            return {id(value)}.union(*(container_ids(v) for v in value.values()))
        if isinstance(value, list):
            return {id(value)}.union(*(container_ids(v) for v in value))
        return set()

    assert container_ids(first).isdisjoint(container_ids(second))
    assert container_ids(first).isdisjoint(container_ids(manifest))
    assert container_ids(first).isdisjoint(container_ids(KEY_BINDING_RESUME_RECORD))
    defensive_record(first)["events"][0]["type"] = "CHANGED_RETURN"
    assert json.dumps(historical_key_binding_resume_manifest(), ensure_ascii=False, indent=2) + "\n" == expected


@pytest.mark.parametrize("warm", (False, True))
@pytest.mark.parametrize("mutation", ("byte_only", "literal_type", "history", "slot", "unrelated", "receipt", "scope"))
def test_recovery_history_original_and_optimized_reject_tampering(
    monkeypatch: pytest.MonkeyPatch, warm: bool, mutation: str,
) -> None:
    """CRSG-08: neither cache state bypasses changed bytes or typed closed authority."""
    import sys

    module = sys.modules[__name__]
    monkeypatch.setattr(module, "_RECOVERY_HISTORY_BYTES", None)
    manifest = historical_recovery_scope_manifest()
    if warm:
        historical_key_binding_resume_manifest()
    before_cache = _RECOVERY_HISTORY_BYTES
    record = defensive_record(manifest)
    if mutation == "literal_type":
        record["execution_authorized"] = 0
    elif mutation == "history":
        record["events"][0]["type"] = "CHANGED"
    elif mutation == "slot":
        manifest["execution_sequence"]["active_target"] = None
    elif mutation == "unrelated":
        manifest["program_id"] = "CHANGED"
    elif mutation == "receipt":
        record["events"][17]["owner_scope_decision"]["record_url"] = "UNRESOLVED"
    elif mutation == "scope":
        record["allowed_paths"].append("unapproved.py")
    raw = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode()
    if mutation == "byte_only":
        raw += b"\n"
    monkeypatch.setattr(Path, "read_bytes", lambda _path: raw)
    monkeypatch.setattr(module, "recovery_resume_historical_source_bytes", lambda: raw)
    with pytest.raises(AssertionError):
        _recovery_scope_historical_inverse(load_manifest())
    with pytest.raises(AssertionError, match="recovery_fixture_source_changed"):
        historical_key_binding_resume_manifest()
    assert _RECOVERY_HISTORY_BYTES is before_cache


@pytest.mark.parametrize("mutation", ("source", "baseline", "type", "shape"))
def test_recovery_history_corrupt_cache_never_returns_data(monkeypatch: pytest.MonkeyPatch, mutation: str) -> None:
    """CRSG-08: even an internally replaced cache must re-establish exact bytes."""
    import sys

    module = sys.modules[__name__]
    monkeypatch.setattr(module, "_RECOVERY_HISTORY_BYTES", None)
    historical_key_binding_resume_manifest()
    source, baseline = _RECOVERY_HISTORY_BYTES
    poisoned = (source + b" ", baseline) if mutation == "source" else (source, baseline + b" ") if mutation == "baseline" else (source, {}) if mutation == "type" else (source,)
    monkeypatch.setattr(module, "_RECOVERY_HISTORY_BYTES", poisoned)
    with pytest.raises(AssertionError, match="recovery_fixture_"):
        historical_key_binding_resume_manifest()


def test_recovery_history_warm_call_reads_source_again(monkeypatch: pytest.MonkeyPatch) -> None:
    """CRSG-08: unchanged warm bytes still require a fresh file read each time."""
    import sys

    module = sys.modules[__name__]
    monkeypatch.setattr(module, "_RECOVERY_HISTORY_BYTES", None)
    raw = MANIFEST_PATH.read_bytes()
    reads = []

    def read(_path: Path) -> bytes:
        reads.append(_path)
        return raw

    monkeypatch.setattr(Path, "read_bytes", read)
    historical_key_binding_resume_manifest()
    historical_key_binding_resume_manifest()
    assert reads == [MANIFEST_PATH, MANIFEST_PATH]


def test_recovery_history_no_second_read_and_no_cache_on_inverse_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """CRSG-08: cold validation uses pinned bytes and publishes only verified history."""
    import sys

    module = sys.modules[__name__]
    monkeypatch.setattr(module, "_RECOVERY_HISTORY_BYTES", None)
    raw = recovery_resume_historical_source_bytes()
    reads = []
    inverse_calls = []
    original = _recovery_scope_historical_inverse

    def alternating() -> bytes:
        reads.append(True)
        return raw if len(reads) == 1 else raw + b"\n"

    def checked_inverse(manifest: dict) -> dict:
        inverse_calls.append(True)
        return original(manifest)

    monkeypatch.setattr(module, "recovery_resume_historical_source_bytes", alternating)
    monkeypatch.setattr(module, "_recovery_scope_historical_inverse", checked_inverse)
    historical_key_binding_resume_manifest()
    assert len(reads) == len(inverse_calls) == 1
    with pytest.raises(AssertionError, match="recovery_fixture_source_changed"):
        historical_key_binding_resume_manifest()
    assert len(reads) == 2 and len(inverse_calls) == 1
    monkeypatch.setattr(module, "_RECOVERY_HISTORY_BYTES", None)
    monkeypatch.setattr(module, "recovery_resume_historical_source_bytes", lambda: raw)

    def failed_inverse(_manifest: dict) -> dict:
        raise AssertionError("injected_inverse_failure")

    monkeypatch.setattr(module, "_recovery_scope_historical_inverse", failed_inverse)
    with pytest.raises(AssertionError, match="injected_inverse_failure"):
        historical_key_binding_resume_manifest()
    assert _RECOVERY_HISTORY_BYTES is None


# CRRG: conditional recovery-only resume, never launch/application merge authority.
RECOVERY_RESUME_EXECUTION_SCOPE = json.loads(r'''{
  "activities": [
    "DEVELOP_REGISTERED_CANONICAL_CUSTOMER_RECOVERY",
    "TEST_REGISTERED_CANONICAL_CUSTOMER_RECOVERY"
  ],
  "implementation_paths": [
    "backend/asie_local_api.py",
    "backend/workspace.py",
    "backend/workflow.py",
    "backend/dib_api.py",
    "backend/dib_persistence.py",
    "backend/dib_tenant_api.py",
    "backend/dib_http_mounting.py",
    "backend/release_info.py",
    "src/contracts.ts",
    "src/dibApi.ts",
    "src/App.tsx",
    "src/customerLanguage.tsx",
    "src/ASIECompleteSurfaceMount.tsx",
    "src/DIBWorkspace.tsx",
    "src/DIBIntakeItemGovernance.tsx",
    "src/DIBManifestRunReadiness.tsx",
    "registry/asie-canonical-api-output.v1.json",
    "docs/ASIE-CANONICAL-API-OUTPUT-REGISTER-v1.0.0.md",
    "tests/test_customer_language_foundation.py",
    "tests/test_gov_beta_04_server_owned_manifest_chain.py",
    "tests/test_context_recovery_api.py",
    "tests/test_dib_context_recovery.py",
    "tests/test_customer_capability_projection.py",
    "tools/check_context_recovery_browser.py"
  ],
  "database_scope": "DISPOSABLE_TEMPORARY_DATABASES_ONLY",
  "data_scope": "SYNTHETIC_DATA_ONLY",
  "live_database_authorized": false,
  "owner_database_authorized": false,
  "production_placement_accepted": false,
  "deployment_authorized": false,
  "application_pr_merge_authorized": false,
  "network_authorized": false,
  "provider_activation_authorized": false,
  "startup_criteria_status": "UNKNOWN_NOT_APPROVED",
  "maintenance_recovery_acceptance": "UNKNOWN_NOT_APPROVED",
  "contract_change_scope": [
    "EXISTING_DIB_SESSION_READ_SERVER_RECORD_REFERENCE",
    "VERSIONED_EXISTING_BLUEPRINT_WRITE_PRECONDITIONS_ALL_THREE_EXISTING_CALLERS",
    "ALLOWLISTED_EXISTING_WORKSPACE_RECOVERY_AND_DISPLAY_PROJECTION",
    "CANONICAL_API_REGISTER_AND_COMPATIBILITY_DOCUMENTATION"
  ],
  "compatibility": "REJECT_LEGACY_UPDATES_WITHOUT_EXPECTED_ORIGINAL_VERSION_NO_SILENT_OVERWRITE_OR_BACKFILL",
  "historical_snapshot_policy": "IMMUTABLE_EXPLICITLY_SEPARATE_FROM_CURRENT_DRAFT",
  "audit_origin_index_query_and_proof_semantics": "UNCHANGED",
  "excluded_changes": [
    "FROZEN_RUNTIME_ENGINES_FINANCE_SNAPSHOT_AAS_DECISION_COUNCIL",
    "F01B_CONTEXT_BUILDING_OR_ROUTING_ACTIVATION",
    "IDENTITY_ROLES_OR_ADMIN_RELEASE_INFO_EXPOSURE",
    "RUNTIME_ENABLE_FLAGS_OR_PARALLEL_STORE_SERVICE_ROUTE",
    "VOICE_AGENT",
    "ADDITIONAL_SCHEMA_OPERATIONS_OR_AUDIT_ORIGIN_INDEX_QUERY_PROOF_CHANGES",
    "LIVE_OWNER_DATABASE_OR_DEPLOYMENT_OR_APPLICATION_PR_MERGE"
  ],
  "acceptance_plan": "ACCEPTED_DESIGN_R01_R14_AND_ORIGINAL_T01_T09_NO_WAIVER"
}''')
RECOVERY_RESUME_DECISION = json.loads(r'''{
  "id": "DECISION-FC20-12-F01A-CUSTOMER-RECOVERY-CONDITIONAL-RESUME-2026-10-14",
  "record_url": "https://github.com/alphasigma13579-lang/ASIE/pull/208#issuecomment-6167318361",
  "recorded_at": "2026-10-14T11:29:03.815159+00:00",
  "effect": "F01A_DEFENSIVE_RESUME_ONLY",
  "condition": "REVIEWED_GOVERNANCE_TRANSITION_MERGED_AFTER_SEPARATE_OWNER_MERGE_APPROVAL",
  "subject": {
    "baseline_commit_sha": "973c6a33080ddf50ade686a4ff8dbb21ed32c978",
    "baseline_manifest_blob_sha": "3e8c82ea894af7d72865229f72d0b9c576d7da31",
    "application_head_sha": "b011a6b3773f4c5e0a905161b5504fff339496f6",
    "allowed_paths": [
      "backend/asie_local_api.py",
      "backend/repository.py",
      "backend/intelligence_prerun_service.py",
      "tests/test_repository_intelligence.py",
      "tests/test_intelligence_prerun_service.py",
      "tests/test_intelligence_context_ingress_api.py",
      "docs/FC20-12-F01-TRUSTED-CONTEXT-INGRESS-REPAIR-PLAN-2026-10-01.md",
      "tests/test_live_location_api.py",
      "tests/test_intelligence_consumption.py",
      "backend/workspace.py",
      "backend/workflow.py",
      "backend/dib_api.py",
      "backend/dib_persistence.py",
      "backend/dib_tenant_api.py",
      "backend/dib_http_mounting.py",
      "backend/release_info.py",
      "src/contracts.ts",
      "src/dibApi.ts",
      "src/App.tsx",
      "src/customerLanguage.tsx",
      "src/ASIECompleteSurfaceMount.tsx",
      "src/DIBWorkspace.tsx",
      "src/DIBIntakeItemGovernance.tsx",
      "src/DIBManifestRunReadiness.tsx",
      "registry/asie-canonical-api-output.v1.json",
      "docs/ASIE-CANONICAL-API-OUTPUT-REGISTER-v1.0.0.md",
      "tests/test_customer_language_foundation.py",
      "tests/test_gov_beta_04_server_owned_manifest_chain.py",
      "tests/test_context_recovery_api.py",
      "tests/test_dib_context_recovery.py",
      "tests/test_customer_capability_projection.py",
      "tools/check_context_recovery_browser.py"
    ],
    "allowed_schema_operations": [
      {
        "operation": "CREATE_INDEX_IF_NOT_EXISTS",
        "index_name": "idx_security_audit_origin_proof",
        "table": "security_audit_events",
        "columns": [
          "action",
          "target_type",
          "target_id",
          "organization_id"
        ],
        "unique": false,
        "implementation_path": "backend/repository.py",
        "test_path": "tests/test_repository_intelligence.py"
      }
    ]
  },
  "proposal_commit_sha": "d2e9399a61b4a939fa174a8c9bada7bd699c2990",
  "proposal_blob_sha": "51cc1b68aee8f88db1b7e1569c6f1f9f74206e1b"
}''')
RECOVERY_RESUME_DECISION["subject"].update(checkpoint=deepcopy(RECOVERY_STOP_EVENT), scope_extension=deepcopy(RECOVERY_SCOPE_EVENT), repair_scope=deepcopy(RECOVERY_REPAIR_SCOPE), execution_scope=deepcopy(RECOVERY_RESUME_EXECUTION_SCOPE))
RECOVERY_RESUME_EVENT = json.loads(r'''{
  "type": "RESUME",
  "recorded_at": "2026-10-14T11:29:53Z",
  "baseline_commit_sha": "973c6a33080ddf50ade686a4ff8dbb21ed32c978",
  "baseline_manifest_blob_sha": "3e8c82ea894af7d72865229f72d0b9c576d7da31",
  "effect": "F01A_DEFENSIVE_RESUME_ONLY"
}''')
RECOVERY_RESUME_EVENT.update(checkpoint=deepcopy(RECOVERY_STOP_EVENT), scope_extension=deepcopy(RECOVERY_SCOPE_EVENT), owner_resume_decision=deepcopy(RECOVERY_RESUME_DECISION))
RECOVERY_RESUME_RECORD = deepcopy(RECOVERY_SCOPE_RECORD)
RECOVERY_RESUME_RECORD["execution_authorized"] = True
RECOVERY_RESUME_RECORD["events"].append(deepcopy(RECOVERY_RESUME_EVENT))
RECOVERY_RESUME_VIEW_PREFIX_BLOBS = json.loads(r'''{
  "docs/FOUNDATION-COMPLETE-20-CORE-INTELLIGENCE-COMPLETION-PROGRAM-2026-07-29.md": "34b96c55a4adbced4e853f75334d083a1e9b6539",
  "docs/EKB/FOUNDATION-COMPLETE-20-PACKAGE-INDEX.md": "9fa4606d674a1c4674fe5537be24c2f5e666c56a",
  "docs/ASIE-BETA-EXECUTION-MASTER-PLAN-2026-09-09.md": "21c54f34d05b5ed16978ec30e8d160ba875343c8",
  "docs/FC20-12-F01A-DEFENSIVE-ENABLING-REGISTRATION-PROPOSAL-2026-10-01.md": "0fecf2dd6348f071e97379d473b26558d88befc2",
  "docs/FC20-12-F01A-APPROVAL-CONSUMPTION-SCOPE-REGISTRATION-2026-10-09.md": "18bc022881772e6b59a51e862c34a8736e29b9cf"
}''')
RECOVERY_RESUME_VIEW_SHA256 = json.loads(r'''{
  "docs/FOUNDATION-COMPLETE-20-CORE-INTELLIGENCE-COMPLETION-PROGRAM-2026-07-29.md": "281a4a7cea164d9aac74cdbecbf1ddcd56ce7e1a69a37f30729a84a98f2ac2a6",
  "docs/EKB/FOUNDATION-COMPLETE-20-PACKAGE-INDEX.md": "19d43ae5998d01559f42963a2723fd91bf06a0187880e2967d93bd62726af1d1",
  "docs/ASIE-BETA-EXECUTION-MASTER-PLAN-2026-09-09.md": "efee74e1a653cc6d22ddbaa9f36c052940887baa5cde26a8cf749622f7406337",
  "docs/FC20-12-F01A-DEFENSIVE-ENABLING-REGISTRATION-PROPOSAL-2026-10-01.md": "a8ebaeb369020354f096c9c90a3d1677aa2a79c55ee5b0b5c2d4f8b78f423280",
  "docs/FC20-12-F01A-APPROVAL-CONSUMPTION-SCOPE-REGISTRATION-2026-10-09.md": "71a32d672955e58d7bfd5e273440ee67b35ae09264cd2798db90c71c60d06560"
}''')
RECOVERY_RESUME_VIEW_MARKER = '<!-- F01A-CUSTOMER-RECOVERY-CONDITIONAL-RESUME-2026-10-14 -->'
RECOVERY_RESUME_MANIFEST_BLOB = '20ef5f2af65cc5f2a1f1c06dbf0c008b039525fa'


def _validate_recovery_resume_structure(record: dict, active_target: object) -> None:
    """CRRG-01/02: closed typed resume and all pinned history, without receipt admission."""
    assert isinstance(record, dict), "invalid_defensive_record"
    assert set(record) == set(RECOVERY_RESUME_RECORD), "defensive_fields"
    if record != RECOVERY_RESUME_RECORD:
        raise AssertionError("defensive_record_mismatch")
    if json.dumps(record, sort_keys=True) != json.dumps(RECOVERY_RESUME_RECORD, sort_keys=True):
        raise AssertionError("recovery_resume_literal_types")
    assert record["execution_authorized"] is True, "recovery_resume_flag"
    assert active_target == DEFENSIVE_START_TARGET, "recovery_resume_slot"
    assert record["allowed_paths"] == RECOVERY_SCOPE_RECORD["allowed_paths"], "recovery_resume_paths"
    assert record["allowed_schema_operations"] == [INDEX_OPERATION], "recovery_resume_index"
    assert record["allowed_schema_operations"][0]["unique"] is False, "recovery_resume_index_literal"
    event = record["events"][18]
    for target in (event, event["owner_resume_decision"]["subject"]):
        assert target["checkpoint"] == RECOVERY_STOP_EVENT, "recovery_resume_checkpoint"
        assert target["scope_extension"] == RECOVERY_SCOPE_EVENT, "recovery_resume_scope"
    subject = event["owner_resume_decision"]["subject"]
    assert subject["repair_scope"] == RECOVERY_REPAIR_SCOPE, "recovery_resume_repair_scope"
    assert subject["execution_scope"] == RECOVERY_RESUME_EXECUTION_SCOPE, "recovery_resume_execution_scope"


def validate_recovery_resume(record: dict, active_target: object) -> None:
    """CRRG-03: a fresh exact execution decision and its merge condition are mandatory."""
    _validate_recovery_resume_structure(record, active_target)
    decision = record["events"][18]["owner_resume_decision"]
    assert decision["record_url"] == "https://github.com/alphasigma13579-lang/ASIE/pull/208#issuecomment-6167318361", "recovery_resume_execution_decision_missing"
    assert decision["recorded_at"] == "2026-10-14T11:29:03.815159+00:00", "recovery_resume_execution_decision_time"
    assert decision["condition"] == "REVIEWED_GOVERNANCE_TRANSITION_MERGED_AFTER_SEPARATE_OWNER_MERGE_APPROVAL", "recovery_resume_merge_condition"


def _recovery_resume_historical_inverse(manifest: dict) -> dict:
    """CRRG-04: exact detached stopped baseline, never an alternative current authority."""
    original = defensive_record(manifest)
    _validate_recovery_resume_structure(original, manifest["execution_sequence"]["active_target"])
    restored = dict(manifest)
    restored["packages"] = list(manifest["packages"])
    index = next(i for i, p in enumerate(manifest["packages"]) if p["id"] == "FC20-12")
    package = dict(manifest["packages"][index]); restored["packages"][index] = package
    package["execution_slices"] = list(package["execution_slices"])
    record = dict(original); package["execution_slices"][1] = record
    record["events"] = list(original["events"][:18])
    record["execution_authorized"] = False
    raw = (json.dumps(restored, ensure_ascii=False, indent=2) + "\n").encode()
    assert git_blob_sha(raw) == "3e8c82ea894af7d72865229f72d0b9c576d7da31", "recovery_resume_baseline_mismatch"
    detached = json.loads(raw)
    validate_recovery_scope(defensive_record(detached), detached["execution_sequence"]["active_target"])
    return detached


def validate_recovery_resume_baseline(manifest: dict) -> dict:
    """CRRG-03/04: public inverse first requires the real current execution receipt."""
    validate_recovery_resume(defensive_record(manifest), manifest["execution_sequence"]["active_target"])
    return _recovery_resume_historical_inverse(manifest)


_RECOVERY_RESUME_HISTORY_BYTES: tuple[bytes, bytes] | None = None


@lru_cache(maxsize=4, typed=True)
def _recovery_resume_cached_blob_sha(raw: bytes) -> str:
    """Memoize only a pure digest of exact immutable content, never admission state."""
    return git_blob_sha(raw)


def recovery_resume_blob_sha(raw: bytes) -> str:
    """Validate byte type before lookup; a fresh read still checks every content byte."""
    if type(raw) is not bytes:
        raise TypeError("recovery_resume_digest_requires_exact_bytes")
    return _recovery_resume_cached_blob_sha(raw)


def recovery_resume_historical_source_bytes() -> bytes:
    """CRRG-08: re-pin every read and expose only immutable inverse-verified history."""
    global _RECOVERY_RESUME_HISTORY_BYTES
    source = dataset_scope_historical_source_bytes()
    assert recovery_resume_blob_sha(source) == RECOVERY_RESUME_MANIFEST_BLOB, "recovery_resume_fixture_source_changed"
    if _RECOVERY_RESUME_HISTORY_BYTES is None:
        baseline = _recovery_resume_historical_inverse(json.loads(source.decode("utf-8")))
        raw = (json.dumps(baseline, ensure_ascii=False, indent=2) + "\n").encode()
        assert recovery_resume_blob_sha(raw) == "3e8c82ea894af7d72865229f72d0b9c576d7da31", "recovery_resume_fixture_baseline_changed"
        _RECOVERY_RESUME_HISTORY_BYTES = (source, raw)
    assert isinstance(_RECOVERY_RESUME_HISTORY_BYTES, tuple) and len(_RECOVERY_RESUME_HISTORY_BYTES) == 2, "recovery_resume_fixture_cache_shape"
    cached_source, raw = _RECOVERY_RESUME_HISTORY_BYTES
    assert type(cached_source) is bytes and type(raw) is bytes, "recovery_resume_fixture_cache_type"
    source_matches = source == cached_source
    assert source_matches, "recovery_resume_fixture_cache_source_changed"
    assert recovery_resume_blob_sha(raw) == "3e8c82ea894af7d72865229f72d0b9c576d7da31", "recovery_resume_fixture_baseline_changed"
    return raw


def historical_recovery_scope_manifest() -> dict:
    """Verified eighteen-event test fixture with fresh detached mutable containers."""
    return json.loads(recovery_resume_historical_source_bytes().decode("utf-8"))


def recovery_resume_historical_view(source_bytes: bytes, relative_path: str) -> bytes:
    """CRRG-05: preserve the exact old prefix and path-specific new terminal section."""
    assert isinstance(source_bytes, bytes), "recovery_resume_view_source_bytes"
    assert relative_path in RECOVERY_RESUME_VIEW_SHA256, "recovery_resume_view_path"
    marker = RECOVERY_RESUME_VIEW_MARKER.encode(); separator = b"\n" + marker + b"\n"
    assert source_bytes.count(marker) == 1, "recovery_resume_view_marker"
    assert source_bytes.count(separator) == 1, "recovery_resume_view_boundary"
    prefix, section = source_bytes.split(separator, 1)
    assert git_blob_sha(prefix) == RECOVERY_RESUME_VIEW_PREFIX_BLOBS[relative_path], "recovery_resume_view_prefix_changed"
    assert hashlib.sha256(marker + b"\n" + section).hexdigest() == RECOVERY_RESUME_VIEW_SHA256[relative_path], "recovery_resume_view_projection_changed"
    recovery_scope_historical_view(prefix, relative_path)
    return prefix


def test_recovery_resume_current_admission_and_complete_inverse() -> None:
    """CRRG-01/03/04: real conditional authority, preserved scope and full history."""
    manifest = historical_recovery_resume_manifest()
    validate_routing_registration(load_manifest())
    record = defensive_record(manifest)
    assert len(record["events"]) == 19 and record["events"][:18] == RECOVERY_SCOPE_RECORD["events"]
    assert len(record["allowed_paths"]) == 32
    assert len(RECOVERY_RESUME_EXECUTION_SCOPE["implementation_paths"]) == 24
    assert RECOVERY_RESUME_EXECUTION_SCOPE["implementation_paths"] == RECOVERY_REPAIR_SCOPE["implementation_paths"]
    scope = validate_recovery_resume_baseline(manifest)
    prior = validate_recovery_scope_baseline(scope)
    stopped = validate_key_binding_resume_baseline(prior)
    previous = validate_key_binding_scope_baseline(stopped)
    old_review_scope = validate_review_identity_resume_baseline(previous)
    old_index_resume = validate_review_identity_scope_baseline(old_review_scope)
    index_scope = validate_index_resume_baseline(old_index_resume)
    consumption_resume = validate_index_scope_baseline(index_scope)
    consumption_scope = validate_consumption_resume_baseline(consumption_resume)
    old_resume = validate_consumption_scope_baseline(consumption_scope)
    validate_scope_extension_baseline(validate_resume_baseline(old_resume))


def recovery_resume_new_leaf_paths() -> list[tuple]:
    """CRRG-06: enumerate new decision leaves, leaving sealed history to its own tests."""
    event = deepcopy(RECOVERY_RESUME_EVENT)
    event.pop("checkpoint"); event.pop("scope_extension")
    subject = event["owner_resume_decision"]["subject"]
    subject.pop("checkpoint"); subject.pop("scope_extension")
    return [tuple(p) for p in index_resume_leaf_paths(event)]


@pytest.mark.parametrize("path", recovery_resume_new_leaf_paths())
def test_recovery_resume_pins_each_new_leaf(path: tuple) -> None:
    """CRRG-06: every new scope, condition and identity scalar is independently pinned."""
    record = deepcopy(RECOVERY_RESUME_RECORD); target = record["events"][18]
    for key in path[:-1]: target = target[key]
    target[path[-1]] = "UNREVIEWED"
    with pytest.raises(AssertionError, match="defensive_record_mismatch"):
        _validate_recovery_resume_structure(record, DEFENSIVE_START_TARGET)


@pytest.mark.parametrize("container", ("event", "decision", "subject", "execution_scope"))
@pytest.mark.parametrize("mutation", ("missing", "extra"))
def test_recovery_resume_closed_objects(container: str, mutation: str) -> None:
    """CRRG-06: no omitted guard or extra activity can enter the closed decision."""
    def select(record: dict) -> dict:
        event = record["events"][18]
        if container == "event": return event
        decision = event["owner_resume_decision"]
        if container == "decision": return decision
        subject = decision["subject"]
        return subject if container == "subject" else subject["execution_scope"]
    for field in select(RECOVERY_RESUME_RECORD):
        record = deepcopy(RECOVERY_RESUME_RECORD); target = select(record)
        if mutation == "missing": target.pop(field)
        else: target["unapproved"] = True
        with pytest.raises(AssertionError, match="defensive_record_mismatch"):
            _validate_recovery_resume_structure(record, DEFENSIVE_START_TARGET)


@pytest.mark.parametrize("event_index", range(18))
def test_recovery_resume_preserves_each_prior_event(event_index: int) -> None:
    """CRRG-02: every prior event is preserved in the exact full-byte inverse."""
    record = deepcopy(RECOVERY_RESUME_RECORD); record["events"][event_index]["type"] = "CHANGED"
    with pytest.raises(AssertionError, match="defensive_record_mismatch"):
        _validate_recovery_resume_structure(record, DEFENSIVE_START_TARGET)


@pytest.mark.parametrize("location", ("event", "subject"))
@pytest.mark.parametrize("field", ("checkpoint", "scope_extension"))
@pytest.mark.parametrize("mutation", ("missing", "type", "literal"))
def test_recovery_resume_preserves_both_checkpoint_scope_copies(location: str, field: str, mutation: str) -> None:
    """CRRG-02: historical copies remain whole and retain strict JSON types."""
    record = deepcopy(RECOVERY_RESUME_RECORD); target = record["events"][18]
    if location == "subject": target = target["owner_resume_decision"]["subject"]
    if mutation == "missing": target.pop(field)
    elif mutation == "type": target[field]["type"] = "CHANGED"
    elif field == "scope_extension":
        target[field]["owner_scope_decision"]["subject"]["allowed_schema_operations"][0]["unique"] = 0
    else: target[field]["recorded_at"] = False
    with pytest.raises(AssertionError, match="defensive_record_mismatch|recovery_resume_literal_types"):
        _validate_recovery_resume_structure(record, DEFENSIVE_START_TARGET)


@pytest.mark.parametrize("value", (False, 0, 1, None, "true"))
def test_recovery_resume_requires_literal_true(value: object) -> None:
    """CRRG-01: only the exact conditional resume flag is admissible."""
    record = deepcopy(RECOVERY_RESUME_RECORD); record["execution_authorized"] = value
    with pytest.raises(AssertionError, match="defensive_record_mismatch|recovery_resume_literal_types"):
        validate_recovery_resume(record, DEFENSIVE_START_TARGET)


@pytest.mark.parametrize("field,value", (("record_url", "UNRESOLVED_OWNER_EXECUTION_DECISION_RECORD_URL"), ("recorded_at", "UNRESOLVED"), ("condition", "IMMEDIATE"), ("effect", "PREPARE_AND_PUBLISH_GOVERNANCE_DRAFT_ONLY_NO_MERGE_NO_RESUME")))
def test_recovery_resume_missing_or_reused_decision_denied_at_all_current_seams(field: str, value: str) -> None:
    """CRRG-03: preparation permission cannot substitute for conditional execution."""
    manifest = historical_recovery_resume_manifest(); defensive_record(manifest)["events"][18]["owner_resume_decision"][field] = value
    for validator in (validate_recovery_resume_baseline,):
        with pytest.raises(AssertionError, match="defensive_record_mismatch"):
            validator(manifest)


@pytest.mark.parametrize("event_index", (15, 17))
@pytest.mark.parametrize("field", ("record_url", "recorded_at", "effect"))
def test_recovery_resume_prior_receipt_negatives_reach_current_seams(event_index: int, field: str) -> None:
    """CRRG-02/03: preserve prior receipt negatives against a valid current baseline."""
    manifest = historical_recovery_resume_manifest()
    validate_routing_registration(load_manifest())
    event = defensive_record(manifest)["events"][event_index]
    decision = event["owner_resume_decision" if event_index == 15 else "owner_scope_decision"]
    decision[field] = "UNRESOLVED_OR_CHANGED"
    for validator in (validate_recovery_resume_baseline,):
        with pytest.raises(AssertionError, match="defensive_record_mismatch"):
            validator(manifest)


@pytest.mark.parametrize("mutation", ("scope_union", "paths", "schema", "index_zero", "slot", "hold", "unrelated"))
def test_recovery_resume_denies_scope_slot_and_unrelated_drift_without_mutation(mutation: str) -> None:
    """CRRG-04/06: inverse covers all manifest bytes, not only the changed slice."""
    manifest = historical_recovery_resume_manifest(); record = defensive_record(manifest)
    if mutation == "scope_union": record["events"][18]["owner_resume_decision"]["subject"]["execution_scope"]["implementation_paths"] = list(record["allowed_paths"])
    elif mutation == "paths": record["allowed_paths"].reverse()
    elif mutation == "schema": record["allowed_schema_operations"].append({"operation": "UNAPPROVED"})
    elif mutation == "index_zero": record["allowed_schema_operations"][0]["unique"] = 0
    elif mutation == "slot": manifest["execution_sequence"]["active_target"] = None
    elif mutation == "hold": manifest["execution_sequence"]["held_packages"] = []
    else: manifest["program_id"] = "UNRELATED"
    before = json.dumps(manifest, sort_keys=True)
    with pytest.raises(AssertionError): validate_recovery_resume_baseline(manifest)
    assert json.dumps(manifest, sort_keys=True) == before


@pytest.mark.parametrize("relative_path", tuple(RECOVERY_RESUME_VIEW_SHA256))
@pytest.mark.parametrize("mutation", ("valid", "prefix", "section", "duplicate", "boundary", "swap"))
def test_recovery_resume_projection_exact_seals(relative_path: str, mutation: str) -> None:
    """CRRG-05: exact path-specific terminal bytes preserve all old projections."""
    root = Path(__file__).resolve().parents[1]; source = dataset_scope_historical_view(dataset_resume_historical_view(overlay_scope_historical_view(overlay_resume_historical_view(ci_scope_historical_view(ci_resume_historical_view(ci_amend_historical_view((root / relative_path).read_bytes(), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path)
    separator = ("\n" + RECOVERY_RESUME_VIEW_MARKER + "\n").encode()
    prefix, section = source.split(separator, 1)
    if mutation == "valid":
        assert recovery_resume_historical_view(source, relative_path) == prefix
        return
    if mutation == "prefix": source = b" " + source
    elif mutation == "section": source += b" "
    elif mutation == "duplicate": source += separator
    elif mutation == "boundary": source = prefix + separator.replace(b"\n", b"\r\n") + section
    else:
        other = next(p for p in RECOVERY_RESUME_VIEW_SHA256 if p != relative_path)
        source = prefix + separator + dataset_scope_historical_view(dataset_resume_historical_view(overlay_scope_historical_view(overlay_resume_historical_view(ci_scope_historical_view(ci_resume_historical_view(ci_amend_historical_view((root / other).read_bytes(), other), other), other), other), other), other), other).split(separator, 1)[1]
    with pytest.raises(AssertionError, match="recovery_resume_view"):
        recovery_resume_historical_view(source, relative_path)


def test_recovery_resume_fixture_cold_warm_equivalence_and_detachment(monkeypatch: pytest.MonkeyPatch) -> None:
    """CRRG-08: optimized history equals direct inverse and never shares mutable state."""
    import sys
    module = sys.modules[__name__]; monkeypatch.setattr(module, "_RECOVERY_RESUME_HISTORY_BYTES", None)
    manifest = historical_recovery_resume_manifest(); original = validate_recovery_resume_baseline(manifest)
    expected = json.dumps(original, ensure_ascii=False, indent=2) + "\n"
    first, second = historical_recovery_scope_manifest(), historical_recovery_scope_manifest()
    assert json.dumps(first, ensure_ascii=False, indent=2) + "\n" == expected
    assert json.dumps(second, ensure_ascii=False, indent=2) + "\n" == expected
    assert isinstance(_RECOVERY_RESUME_HISTORY_BYTES, tuple) and all(isinstance(x, bytes) for x in _RECOVERY_RESUME_HISTORY_BYTES)
    def ids(value: object) -> set[int]:
        if isinstance(value, dict): return {id(value)}.union(*(ids(v) for v in value.values()))
        if isinstance(value, list): return {id(value)}.union(*(ids(v) for v in value))
        return set()
    assert ids(first).isdisjoint(ids(second)) and ids(first).isdisjoint(ids(manifest)) and ids(first).isdisjoint(ids(RECOVERY_SCOPE_RECORD))
    defensive_record(first)["events"][0]["type"] = "CHANGED_RETURN"
    assert json.dumps(historical_recovery_scope_manifest(), ensure_ascii=False, indent=2) + "\n" == expected


@pytest.mark.parametrize("warm", (False, True))
@pytest.mark.parametrize("mutation", ("bytes", "type", "history", "slot", "unrelated", "receipt", "scope"))
def test_recovery_resume_fixture_original_and_optimized_denials(monkeypatch: pytest.MonkeyPatch, warm: bool, mutation: str) -> None:
    """CRRG-08: cold and warm reads cannot reuse approval after any source change."""
    import sys
    module = sys.modules[__name__]; monkeypatch.setattr(module, "_RECOVERY_RESUME_HISTORY_BYTES", None)
    manifest = historical_recovery_resume_manifest()
    if warm: historical_recovery_scope_manifest()
    cache = _RECOVERY_RESUME_HISTORY_BYTES; record = defensive_record(manifest)
    if mutation == "type": record["execution_authorized"] = 1
    elif mutation == "history": record["events"][0]["type"] = "CHANGED"
    elif mutation == "slot": manifest["execution_sequence"]["active_target"] = None
    elif mutation == "unrelated": manifest["program_id"] = "CHANGED"
    elif mutation == "receipt": record["events"][18]["owner_resume_decision"]["record_url"] = "UNRESOLVED"
    elif mutation == "scope": record["allowed_paths"].append("unapproved.py")
    raw = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode()
    if mutation == "bytes": raw += b"\n"
    monkeypatch.setattr(Path, "read_bytes", lambda _path: raw)
    monkeypatch.setattr(module, "dataset_scope_historical_source_bytes", lambda: raw)
    with pytest.raises(AssertionError): _recovery_resume_historical_inverse(load_manifest())
    with pytest.raises(AssertionError, match="recovery_resume_fixture_source_changed"): historical_recovery_scope_manifest()
    assert _RECOVERY_RESUME_HISTORY_BYTES is cache


@pytest.mark.parametrize("mutation", ("source", "baseline", "type", "shape"))
def test_recovery_resume_fixture_poisoned_cache_rejected(monkeypatch: pytest.MonkeyPatch, mutation: str) -> None:
    """CRRG-08: cache bytes must stay typed and independently pinned on every call."""
    import sys
    module = sys.modules[__name__]; monkeypatch.setattr(module, "_RECOVERY_RESUME_HISTORY_BYTES", None)
    historical_recovery_scope_manifest(); source, baseline = _RECOVERY_RESUME_HISTORY_BYTES
    poisoned = (source+b" ", baseline) if mutation == "source" else (source, baseline+b" ") if mutation == "baseline" else (source, {}) if mutation == "type" else (source,)
    monkeypatch.setattr(module, "_RECOVERY_RESUME_HISTORY_BYTES", poisoned)
    with pytest.raises(AssertionError, match="recovery_resume_fixture_"): historical_recovery_scope_manifest()


def test_recovery_resume_fixture_single_read_and_failed_initialization(monkeypatch: pytest.MonkeyPatch) -> None:
    """CRRG-08: cold inverse consumes the pinned read and failure never publishes cache."""
    import sys
    module = sys.modules[__name__]; monkeypatch.setattr(module, "_RECOVERY_RESUME_HISTORY_BYTES", None)
    raw = dataset_scope_historical_source_bytes(); reads = []; calls = []; original = _recovery_resume_historical_inverse
    def alternating() -> bytes:
        reads.append(True)
        return raw if len(reads) == 1 else raw+b"\n"
    def checked(manifest: dict) -> dict:
        calls.append(True)
        return original(manifest)
    monkeypatch.setattr(module, "dataset_scope_historical_source_bytes", alternating); monkeypatch.setattr(module, "_recovery_resume_historical_inverse", checked)
    historical_recovery_scope_manifest()
    assert len(reads) == len(calls) == 1
    with pytest.raises(AssertionError, match="recovery_resume_fixture_source_changed"): historical_recovery_scope_manifest()
    assert len(reads) == 2 and len(calls) == 1
    monkeypatch.setattr(module, "_RECOVERY_RESUME_HISTORY_BYTES", None)
    monkeypatch.setattr(module, "dataset_scope_historical_source_bytes", lambda: raw)
    def failed(_manifest: dict) -> dict: raise AssertionError("injected_inverse_failure")
    monkeypatch.setattr(module, "_recovery_resume_historical_inverse", failed)
    with pytest.raises(AssertionError, match="injected_inverse_failure"): historical_recovery_scope_manifest()
    assert _RECOVERY_RESUME_HISTORY_BYTES is None


@pytest.mark.parametrize("raw", [b"", b"abc", b"abc\x00", b" abc ", bytes(range(256))])
def test_recovery_resume_digest_matches_original_and_content_keys(raw: bytes) -> None:
    """Distinct byte content cannot reuse an approval or a different digest."""
    _recovery_resume_cached_blob_sha.cache_clear()
    expected = git_blob_sha(raw)
    assert recovery_resume_blob_sha(raw) == expected
    fresh = memoryview(raw).tobytes()
    if len(raw) > 1:
        assert fresh is not raw
    assert recovery_resume_blob_sha(fresh) == expected
    assert _recovery_resume_cached_blob_sha.cache_info().hits == 1
    changed = raw + b"!"
    assert recovery_resume_blob_sha(changed) == git_blob_sha(changed)
    assert _recovery_resume_cached_blob_sha.cache_info().misses == 2
    if raw:
        same_length_changed = bytes([raw[0] ^ 1]) + raw[1:]
        assert len(same_length_changed) == len(raw)
        assert recovery_resume_blob_sha(same_length_changed) == git_blob_sha(same_length_changed)
        assert _recovery_resume_cached_blob_sha.cache_info().misses == 3


@pytest.mark.parametrize("raw", [bytearray(b"abc"), memoryview(b"abc"), "abc", 1, True, None])
def test_recovery_resume_digest_rejects_nonbytes_before_cache(raw: object) -> None:
    """Invalid types cannot enter or hit the content-only cache."""
    _recovery_resume_cached_blob_sha.cache_clear()
    recovery_resume_blob_sha(b"abc")
    before = _recovery_resume_cached_blob_sha.cache_info()
    with pytest.raises(TypeError, match="requires_exact_bytes"):
        recovery_resume_blob_sha(raw)
    assert _recovery_resume_cached_blob_sha.cache_info() == before


def test_recovery_resume_digest_rejects_bytes_subclass_and_bounds_storage() -> None:
    """Only exact immutable bytes enter the four-entry cache."""
    class DerivedBytes(bytes):
        pass
    _recovery_resume_cached_blob_sha.cache_clear()
    with pytest.raises(TypeError, match="requires_exact_bytes"):
        recovery_resume_blob_sha(DerivedBytes(b"abc"))
    for i in range(8):
        raw = bytes([i])
        assert recovery_resume_blob_sha(raw) == git_blob_sha(raw)
    info = _recovery_resume_cached_blob_sha.cache_info()
    assert info.maxsize == 4 and info.currsize == 4 and info.misses == 8
    assert recovery_resume_blob_sha(bytes([0])) == git_blob_sha(bytes([0]))
    assert _recovery_resume_cached_blob_sha.cache_info().misses == 9


def test_recovery_resume_digest_does_not_cache_failed_computation(monkeypatch: pytest.MonkeyPatch) -> None:
    """A digest failure cannot become a reused result on a later read."""
    _recovery_resume_cached_blob_sha.cache_clear()
    original = git_blob_sha
    def fail(raw: bytes) -> str:
        raise ValueError("synthetic_digest_failure")
    monkeypatch.setitem(globals(), "git_blob_sha", fail)
    with pytest.raises(ValueError, match="synthetic_digest_failure"):
        recovery_resume_blob_sha(b"abc")
    assert _recovery_resume_cached_blob_sha.cache_info().currsize == 0
    monkeypatch.setitem(globals(), "git_blob_sha", original)
    assert recovery_resume_blob_sha(b"abc") == original(b"abc")
    _recovery_resume_cached_blob_sha.cache_clear()


def test_recovery_resume_warm_digest_does_not_cache_pin_admission(monkeypatch: pytest.MonkeyPatch) -> None:
    """A warmed content digest cannot preserve admission after its expected pin changes."""
    recovery_resume_historical_source_bytes()
    monkeypatch.setitem(globals(), "RECOVERY_RESUME_MANIFEST_BLOB", "0" * 40)
    with pytest.raises(AssertionError, match="recovery_resume_fixture_source_changed"):
        recovery_resume_historical_source_bytes()


@pytest.mark.parametrize("position", [0, 1])
def test_recovery_resume_rejects_cached_bytes_subclasses(monkeypatch: pytest.MonkeyPatch, position: int) -> None:
    """Custom equality on byte subclasses cannot impersonate verified cached content."""
    recovery_resume_historical_source_bytes()
    class DerivedBytes(bytes):
        def __eq__(self, other: object) -> bool:
            return True
    poisoned = list(_RECOVERY_RESUME_HISTORY_BYTES)
    poisoned[position] = DerivedBytes(poisoned[position])
    monkeypatch.setitem(globals(), "_RECOVERY_RESUME_HISTORY_BYTES", tuple(poisoned))
    with pytest.raises(AssertionError, match="recovery_resume_fixture_cache_type"):
        recovery_resume_historical_source_bytes()


# DPSG: stopped Dataset provenance registration; no expanded execution authority.
DATASET_STOP_EVENT = json.loads(r'''{
  "type": "STOP_CHECKPOINT",
  "recorded_at": "2026-10-14T19:15:53Z",
  "baseline_commit_sha": "3ae62b855138d6d5c6ef36252e5a1b08a0bf800f",
  "baseline_manifest_blob_sha": "20ef5f2af65cc5f2a1f1c06dbf0c008b039525fa",
  "application_head_sha": "b011a6b3773f4c5e0a905161b5504fff339496f6",
  "reason": "DATASET_PROVENANCE_ADMISSION_AND_PATH_EXTENSION_OUTSIDE_RECOVERY_RESUME",
  "evidence": {
    "url": "https://github.com/alphasigma13579-lang/ASIE/blob/383e49df5ede8386a4715f451da4fa640acc19cc/ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/docs/FC20-12-F01A-CUSTOMER-DATASET-PROVENANCE-AMENDMENT-2026-10-14.md",
    "commit_sha": "383e49df5ede8386a4715f451da4fa640acc19cc",
    "blob_sha": "297e10abd1fb92d6e9bf812e3073f0374185b860"
  },
  "resume_requirement": "NEW_OWNER_EXECUTION_DECISION_AND_REVIEWED_SCOPE_BOUND_RESUME_MERGED_AFTER_SEPARATE_APPROVAL"
}''')
DATASET_SCOPE_EVENT = json.loads(r'''{
  "type": "SCOPE_EXTENSION",
  "recorded_at": "2026-10-14T19:15:53Z",
  "baseline_commit_sha": "3ae62b855138d6d5c6ef36252e5a1b08a0bf800f",
  "baseline_manifest_blob_sha": "20ef5f2af65cc5f2a1f1c06dbf0c008b039525fa",
  "application_head_sha": "b011a6b3773f4c5e0a905161b5504fff339496f6",
  "added_paths": [
    "backend/datasets.py",
    "backend/evidence_ledger.py",
    "src/api.ts"
  ],
  "scope_addendum": {
    "url": "https://github.com/alphasigma13579-lang/ASIE/blob/383e49df5ede8386a4715f451da4fa640acc19cc/ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/docs/FC20-12-F01A-CUSTOMER-DATASET-PROVENANCE-AMENDMENT-2026-10-14.md",
    "commit_sha": "383e49df5ede8386a4715f451da4fa640acc19cc",
    "blob_sha": "297e10abd1fb92d6e9bf812e3073f0374185b860"
  },
  "owner_scope_decision": {
    "id": "DECISION-FC20-12-F01A-DATASET-PROVENANCE-REGISTRATION-2026-10-14",
    "record_url": "https://github.com/alphasigma13579-lang/ASIE/pull/210#issuecomment-6176332891",
    "recorded_at": "2026-10-14T19:14:26.505452+00:00",
    "effect": "PREPARE_AND_PUBLISH_GOVERNANCE_DRAFT_ONLY_NO_MERGE_NO_RESUME",
    "subject": {
      "baseline_commit_sha": "3ae62b855138d6d5c6ef36252e5a1b08a0bf800f",
      "baseline_manifest_blob_sha": "20ef5f2af65cc5f2a1f1c06dbf0c008b039525fa",
      "application_head_sha": "b011a6b3773f4c5e0a905161b5504fff339496f6",
      "previous_resume_event_index": 18,
      "previous_resume_sha256": "331b3183dc392ae39b86fa256ea2ba863fe48db977e4be9e190613ab530e0cff",
      "digest_serialization": "UTF8_JSON_ENSURE_ASCII_FALSE_SORT_KEYS_TRUE_COMPACT_SEPARATORS_COMMA_COLON",
      "repair_scope": {
        "kind": "CUSTOMER_DATASET_PROVENANCE_AND_RECOVERY",
        "implementation_paths": [
          "backend/asie_local_api.py",
          "backend/workspace.py",
          "backend/workflow.py",
          "backend/dib_api.py",
          "backend/dib_persistence.py",
          "backend/dib_tenant_api.py",
          "backend/dib_http_mounting.py",
          "backend/release_info.py",
          "src/contracts.ts",
          "src/dibApi.ts",
          "src/App.tsx",
          "src/customerLanguage.tsx",
          "src/ASIECompleteSurfaceMount.tsx",
          "src/DIBWorkspace.tsx",
          "src/DIBIntakeItemGovernance.tsx",
          "src/DIBManifestRunReadiness.tsx",
          "registry/asie-canonical-api-output.v1.json",
          "docs/ASIE-CANONICAL-API-OUTPUT-REGISTER-v1.0.0.md",
          "tests/test_customer_language_foundation.py",
          "tests/test_gov_beta_04_server_owned_manifest_chain.py",
          "tests/test_context_recovery_api.py",
          "tests/test_dib_context_recovery.py",
          "tests/test_customer_capability_projection.py",
          "tools/check_context_recovery_browser.py",
          "backend/datasets.py",
          "backend/repository.py",
          "backend/evidence_ledger.py",
          "src/api.ts"
        ],
        "preserved_recovery_scope_sha256": "0d527be319b1aa0654148b0623242533529f4794f4e92824326a97f05d16b51c",
        "preserved_recovery_contract": "FULL_REGISTERED_24_FILE_RECOVERY_CONTRACT_UNCHANGED",
        "origin_policy": "CUSTOMER_OWN_STUDY_NO_LICENSE_TERMS_PROOF_PLATFORM_SOURCE_PERMISSION_REMAINS_PLATFORM_OWNED",
        "provenance": "IMMUTABLE_AUTHENTICATED_SERVER_OWNED_SUBMISSION_CONTEXT_NOT_OWNERSHIP_OR_ACCURACY_PROOF",
        "customer_source_id": "",
        "nonempty_customer_source_association": "REJECT",
        "organization_policy": "IMMUTABLE_OWNER_ORGANIZATION_AUTHORIZED_SAME_ORGANIZATION_PROJECT_REUSE",
        "creation_project_id": "AUDIT_CONTEXT_NOT_EXCLUSIVE_REUSE_BOUNDARY",
        "collection_create": "CREATE_ONLY_REJECT_EXISTING_ID",
        "review_updates": "NO_ORGANIZATION_OR_PROVENANCE_REASSIGNMENT",
        "reserved_fields": "STRICT_TYPED_VERSIONED_SERVER_FIELDS_REJECT_NESTED_INJECTION",
        "transformation": "IMMUTABLE_PARENT_AND_OWNER_BINDING",
        "material_content_change": "INVALIDATE_AFFECTED_CURRENT_APPROVAL_TRANSFORMATION_LINK_REVIEWS",
        "legacy": "NO_EXEMPTION_WITHOUT_VALID_PROVENANCE_NO_AUTOMATIC_BACKFILL",
        "quality_privacy_classification_review": "PRESERVED_APPLICABLE_CHECKS_SEPARATE_FROM_LICENSE_POLICY",
        "evidence_admission": "EXISTING_REGISTER_AND_LEDGER_FALLBACK_SHARE_TRUSTED_PROJECT_ORGANIZATION_GATE",
        "evidence_targets": [
          "assumption",
          "sector_criterion"
        ],
        "sector_source_predicate": "UNCHANGED",
        "confidence_weights": "UNCHANGED_NO_OFFICIAL_SOURCE_CREDIT_FROM_CUSTOMER_EXEMPTION",
        "historical_snapshots": "IMMUTABLE",
        "storage": "EXISTING_DATASET_NOTES_JSON_NO_NEW_STORE",
        "routes": "EXISTING_DATASET_IMPORT_CREATE_REVIEW_EVIDENCE_ROUTES",
        "additional_schema_operations": [],
        "environment": "TEMPORARY_DATABASE_SYNTHETIC_DATA_ONLY_AFTER_REVIEWED_RESUME",
        "live_database_authorized": false,
        "provider_network_deployment_authorized": false,
        "application_pr_merge_authorized": false,
        "t08": "OPEN",
        "startup_acceptance": "UNKNOWN_NOT_APPROVED"
      }
    }
  },
  "effect": "REGISTER_BOUNDED_DATASET_PROVENANCE_SCOPE_ONLY_EXECUTION_STOPPED"
}''')
DATASET_SCOPE_RECORD = deepcopy(RECOVERY_RESUME_RECORD)
DATASET_SCOPE_RECORD["execution_authorized"] = False
DATASET_SCOPE_RECORD["allowed_paths"].extend(DATASET_SCOPE_EVENT["added_paths"])
DATASET_SCOPE_RECORD["events"].extend([deepcopy(DATASET_STOP_EVENT), deepcopy(DATASET_SCOPE_EVENT)])
DATASET_VIEW_PREFIX_BLOBS = json.loads(r'''{
  "docs/FOUNDATION-COMPLETE-20-CORE-INTELLIGENCE-COMPLETION-PROGRAM-2026-07-29.md": "648544e4f15b921d04a3adae7a58a3ebe04c7aad",
  "docs/EKB/FOUNDATION-COMPLETE-20-PACKAGE-INDEX.md": "14dddd8dcfd6706fb4d89e0dcd336ed743794f22",
  "docs/ASIE-BETA-EXECUTION-MASTER-PLAN-2026-09-09.md": "5c4e2e94c9b42e862f1ac03c87a6c28217c0fc77",
  "docs/FC20-12-F01A-DEFENSIVE-ENABLING-REGISTRATION-PROPOSAL-2026-10-01.md": "b7bb0525e8dafe308749a5501b131c1235d57626",
  "docs/FC20-12-F01A-APPROVAL-CONSUMPTION-SCOPE-REGISTRATION-2026-10-09.md": "04486199b082e75a1993c8a04317b223bfca56ef"
}''')
DATASET_VIEW_SHA256 = json.loads(r'''{
  "docs/FOUNDATION-COMPLETE-20-CORE-INTELLIGENCE-COMPLETION-PROGRAM-2026-07-29.md": "86f55d9703bee6fdbad5a1c0f66d7fddf03f96908f4630d535514cb7165234df",
  "docs/EKB/FOUNDATION-COMPLETE-20-PACKAGE-INDEX.md": "96930312099ac3093daf11bfb75219272aa5eca2d578aad1a8b67f65916459b7",
  "docs/ASIE-BETA-EXECUTION-MASTER-PLAN-2026-09-09.md": "df5f02b3d4d26987dc571122216b7fda5dd9b8d1e89c3c957d0ae09d83594029",
  "docs/FC20-12-F01A-DEFENSIVE-ENABLING-REGISTRATION-PROPOSAL-2026-10-01.md": "ec028470e10f0b7cae4fee0ebc1bf2b4b676212d9f5edb99c1eaefa898bf9d2c",
  "docs/FC20-12-F01A-APPROVAL-CONSUMPTION-SCOPE-REGISTRATION-2026-10-09.md": "b587a754b86106df7b0947de1d88d68a5e25e6679783480dc59fbc52492043b6"
}''')
DATASET_VIEW_MARKER = '<!-- F01A-DATASET-PROVENANCE-SCOPE-REGISTRATION-2026-10-14 -->'
DATASET_MANIFEST_BLOB = '56e59d99d30e608b2f9b96e2abac0ed3daa0f841'


def dataset_scope_digest(value: object) -> str:
    """DPSG-01: one explicit typed canonical representation for new history references."""
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _validate_dataset_scope_structure(record: dict, active_target: object) -> None:
    """DPSG-01/02: independent closed typed scope, exact history and stopped authority."""
    assert isinstance(record, dict), "invalid_defensive_record"
    assert set(record) == set(DATASET_SCOPE_RECORD), "defensive_fields"
    if record != DATASET_SCOPE_RECORD:
        raise AssertionError("defensive_record_mismatch")
    if json.dumps(record, sort_keys=True) != json.dumps(DATASET_SCOPE_RECORD, sort_keys=True):
        raise AssertionError("dataset_scope_literal_types")
    assert record["execution_authorized"] is False, "dataset_scope_stopped"
    assert active_target == DEFENSIVE_START_TARGET, "dataset_scope_slot"
    assert len(record["events"]) == 21, "dataset_scope_events"
    assert record["allowed_paths"][:32] == RECOVERY_RESUME_RECORD["allowed_paths"], "dataset_scope_prior_paths"
    assert len(record["allowed_paths"]) == len(set(record["allowed_paths"])) == 35, "dataset_scope_union"
    subject = record["events"][20]["owner_scope_decision"]["subject"]
    assert subject["previous_resume_sha256"] == dataset_scope_digest(RECOVERY_RESUME_EVENT), "dataset_scope_resume_reference"
    assert subject["previous_resume_sha256"] == dataset_scope_digest(record["events"][18]), "dataset_scope_history_binding"
    scope = subject["repair_scope"]
    assert scope["preserved_recovery_scope_sha256"] == dataset_scope_digest(RECOVERY_REPAIR_SCOPE), "dataset_scope_recovery_contract"
    assert scope["implementation_paths"][:24] == RECOVERY_REPAIR_SCOPE["implementation_paths"], "dataset_scope_active_recovery"
    assert len(scope["implementation_paths"]) == 28, "dataset_scope_active_paths"
    assert record["allowed_schema_operations"] == [INDEX_OPERATION], "dataset_scope_schema"
    assert record["allowed_schema_operations"][0]["unique"] is False, "dataset_scope_schema_literal"


def validate_dataset_scope(record: dict, active_target: object) -> None:
    """DPSG-03: admit only the actual bounded preparation/publication receipt."""
    _validate_dataset_scope_structure(record, active_target)
    decision = record["events"][20]["owner_scope_decision"]
    assert decision["record_url"] == "https://github.com/alphasigma13579-lang/ASIE/pull/210#issuecomment-6176332891", "dataset_scope_receipt_missing"
    assert decision["recorded_at"] == "2026-10-14T19:14:26.505452+00:00", "dataset_scope_receipt_time"
    assert decision["effect"] == "PREPARE_AND_PUBLISH_GOVERNANCE_DRAFT_ONLY_NO_MERGE_NO_RESUME", "dataset_scope_no_execution_authority"


def _dataset_scope_historical_inverse(manifest: dict) -> dict:
    """DPSG-04: exact full nineteen-event baseline with a fresh detached return value."""
    original = defensive_record(manifest)
    _validate_dataset_scope_structure(original, manifest["execution_sequence"]["active_target"])
    restored = dict(manifest); restored["packages"] = list(manifest["packages"])
    index = next(i for i, p in enumerate(manifest["packages"]) if p["id"] == "FC20-12")
    package = dict(manifest["packages"][index]); restored["packages"][index] = package
    package["execution_slices"] = list(package["execution_slices"])
    record = dict(original); package["execution_slices"][1] = record
    record["events"] = list(original["events"][:19]); record["allowed_paths"] = list(original["allowed_paths"][:32]); record["execution_authorized"] = True
    raw = (json.dumps(restored, ensure_ascii=False, indent=2) + "\n").encode()
    assert recovery_resume_blob_sha(raw) == "20ef5f2af65cc5f2a1f1c06dbf0c008b039525fa", "dataset_scope_baseline_mismatch"
    detached = json.loads(raw)
    validate_recovery_resume(defensive_record(detached), detached["execution_sequence"]["active_target"])
    return detached


def validate_dataset_scope_baseline(manifest: dict) -> dict:
    """DPSG-03/04: public inverse requires the current receipt before historical checks."""
    validate_dataset_scope(defensive_record(manifest), manifest["execution_sequence"]["active_target"])
    return _dataset_scope_historical_inverse(manifest)


_DATASET_HISTORY_BYTES: tuple[bytes, bytes] | None = None


def dataset_scope_historical_source_bytes() -> bytes:
    """DPSG-08: pin each actual read; cache immutable bytes only after exact inverse."""
    global _DATASET_HISTORY_BYTES
    source = dataset_resume_historical_source_bytes()
    assert recovery_resume_blob_sha(source) == DATASET_MANIFEST_BLOB, "dataset_scope_fixture_source_changed"
    if _DATASET_HISTORY_BYTES is None:
        baseline = _dataset_scope_historical_inverse(json.loads(source.decode("utf-8")))
        raw = (json.dumps(baseline, ensure_ascii=False, indent=2) + "\n").encode()
        assert recovery_resume_blob_sha(raw) == "20ef5f2af65cc5f2a1f1c06dbf0c008b039525fa", "dataset_scope_fixture_baseline_changed"
        _DATASET_HISTORY_BYTES = (source, raw)
    assert type(_DATASET_HISTORY_BYTES) is tuple and len(_DATASET_HISTORY_BYTES) == 2, "dataset_scope_fixture_cache_shape"
    cached_source, raw = _DATASET_HISTORY_BYTES
    assert type(cached_source) is bytes and type(raw) is bytes, "dataset_scope_fixture_cache_type"
    source_matches = source == cached_source
    assert source_matches, "dataset_scope_fixture_cache_source_changed"
    assert recovery_resume_blob_sha(raw) == "20ef5f2af65cc5f2a1f1c06dbf0c008b039525fa", "dataset_scope_fixture_baseline_changed"
    return raw


def historical_recovery_resume_manifest() -> dict:
    """DPSG-08: never share mutable dictionaries or lists between historical cases."""
    return json.loads(dataset_scope_historical_source_bytes())


def dataset_scope_historical_view(source_bytes: bytes, relative_path: str) -> bytes:
    """DPSG-05: path-specific complete prefix and section seals before historical view."""
    assert type(source_bytes) is bytes, "dataset_scope_view_bytes"
    assert relative_path in DATASET_VIEW_SHA256, "dataset_scope_view_path"
    marker = DATASET_VIEW_MARKER.encode(); separator = b"\n" + marker + b"\n"
    assert source_bytes.count(marker) == source_bytes.count(separator) == 1, "dataset_scope_view_boundary"
    prefix, section = source_bytes.split(separator, 1)
    assert git_blob_sha(prefix) == DATASET_VIEW_PREFIX_BLOBS[relative_path], "dataset_scope_view_prefix_changed"
    assert hashlib.sha256(marker + b"\n" + section).hexdigest() == DATASET_VIEW_SHA256[relative_path], "dataset_scope_view_section_changed"
    recovery_resume_historical_view(prefix, relative_path)
    return prefix


def test_dataset_scope_current_admission_full_inverse_and_history() -> None:
    """DPSG-01/04: stopped registration and all prior independent validators survive."""
    manifest = historical_dataset_scope_manifest(); before = json.dumps(manifest, sort_keys=True)
    validate_routing_registration(load_manifest()); validate_execution_sequence(load_manifest())
    prior = validate_dataset_scope_baseline(manifest)
    assert json.dumps(manifest, sort_keys=True) == before
    assert len(defensive_record(prior)["events"]) == 19
    scope = validate_recovery_resume_baseline(prior)
    key_resume = validate_recovery_scope_baseline(scope)
    key_scope = validate_key_binding_resume_baseline(key_resume)
    review_resume = validate_key_binding_scope_baseline(key_scope)
    review_scope = validate_review_identity_resume_baseline(review_resume)
    index_resume = validate_review_identity_scope_baseline(review_scope)
    index_scope = validate_index_resume_baseline(index_resume)
    consumption_resume = validate_index_scope_baseline(index_scope)
    consumption_scope = validate_consumption_resume_baseline(consumption_resume)
    old = validate_consumption_scope_baseline(consumption_scope)
    validate_scope_extension_baseline(validate_resume_baseline(old))


@pytest.mark.parametrize("event_index,path", [(i, tuple(p)) for i, event in ((19, DATASET_STOP_EVENT), (20, DATASET_SCOPE_EVENT)) for p in index_resume_leaf_paths(event)])
def test_dataset_scope_pins_each_new_leaf(event_index: int, path: tuple) -> None:
    """DPSG-06: every new scalar is pinned without re-expanding historical matrices."""
    record = deepcopy(DATASET_SCOPE_RECORD); target = record["events"][event_index]
    for key in path[:-1]: target = target[key]
    target[path[-1]] = "UNREVIEWED"
    with pytest.raises(AssertionError): validate_dataset_scope(record, DEFENSIVE_START_TARGET)


@pytest.mark.parametrize("path", [(), ("events",19), ("events",19,"evidence"), ("events",20), ("events",20,"scope_addendum"), ("events",20,"owner_scope_decision"), ("events",20,"owner_scope_decision","subject"), ("events",20,"owner_scope_decision","subject","repair_scope")])
@pytest.mark.parametrize("mutation", ["missing", "extra"])
def test_dataset_scope_closed_objects(path: tuple, mutation: str) -> None:
    """DPSG-06: missing and additional fields cannot enlarge or dilute authority."""
    record = deepcopy(DATASET_SCOPE_RECORD); target = record
    for key in path: target = target[key]
    if mutation == "missing": target.pop(next(iter(target)))
    else: target["unexpected"] = True
    with pytest.raises(AssertionError): validate_dataset_scope(record, DEFENSIVE_START_TARGET)


@pytest.mark.parametrize("event_index", range(19))
def test_dataset_scope_preserves_each_prior_event(event_index: int) -> None:
    """DPSG-02: each historical event remains part of the independently pinned record."""
    record = deepcopy(DATASET_SCOPE_RECORD); record["events"][event_index]["type"] = "ALTERED"
    with pytest.raises(AssertionError): validate_dataset_scope(record, DEFENSIVE_START_TARGET)


@pytest.mark.parametrize("path,value", [(("execution_authorized",),0), (("execution_authorized",),True), (("events",20,"owner_scope_decision","subject","previous_resume_event_index"),18.0), (("events",20,"owner_scope_decision","subject","repair_scope","live_database_authorized"),0), (("allowed_schema_operations",0,"unique"),0)])
def test_dataset_scope_rejects_equal_but_wrong_json_types(path: tuple, value: object) -> None:
    """DPSG-02: Python equality never admits bool/int/float substitution."""
    record = deepcopy(DATASET_SCOPE_RECORD); target = record
    for key in path[:-1]: target = target[key]
    target[path[-1]] = value
    with pytest.raises(AssertionError): validate_dataset_scope(record, DEFENSIVE_START_TARGET)


@pytest.mark.parametrize("field,value", [("record_url","UNRESOLVED"),("recorded_at","UNRESOLVED"),("effect","F01A_DEFENSIVE_RESUME_ONLY")])
def test_dataset_scope_receipt_denials_reach_current_seams(field: str, value: str) -> None:
    """DPSG-03: all current authority entry points reject reused or absent decisions."""
    manifest = historical_dataset_scope_manifest(); defensive_record(manifest)["events"][20]["owner_scope_decision"][field] = value
    for validator in (validate_dataset_scope_baseline,):
        with pytest.raises(AssertionError): validator(manifest)


@pytest.mark.parametrize("mutation", ["slot","hold","unrelated","schema","paths"])
def test_dataset_scope_inverse_rejects_unrelated_drift_without_mutation(mutation: str) -> None:
    """DPSG-04: the whole baseline, including holds, must be byte-identical."""
    manifest = historical_dataset_scope_manifest(); record = defensive_record(manifest)
    if mutation == "slot": manifest["execution_sequence"]["active_target"] = None
    elif mutation == "hold": manifest["execution_sequence"]["max_active_executions"] = 2
    elif mutation == "unrelated": manifest["program_id"] = "CHANGED"
    elif mutation == "schema": record["allowed_schema_operations"] = []
    else: record["allowed_paths"].append("unapproved.py")
    before = json.dumps(manifest, sort_keys=True)
    with pytest.raises(AssertionError): validate_dataset_scope_baseline(manifest)
    assert json.dumps(manifest, sort_keys=True) == before


@pytest.mark.parametrize("relative_path", tuple(DATASET_VIEW_SHA256))
@pytest.mark.parametrize("mutation", ["valid","prefix","section","duplicate","boundary","swap"])
def test_dataset_scope_projection_seals(relative_path: str, mutation: str) -> None:
    """DPSG-05: exact path, old bytes, new section and unique boundary are required."""
    raw = dataset_resume_historical_view(overlay_scope_historical_view(overlay_resume_historical_view(ci_scope_historical_view(ci_resume_historical_view(ci_amend_historical_view((Path(__file__).resolve().parents[1] / relative_path).read_bytes(), relative_path), relative_path), relative_path), relative_path), relative_path), relative_path)
    if mutation == "valid":
        assert git_blob_sha(dataset_scope_historical_view(raw, relative_path)) == DATASET_VIEW_PREFIX_BLOBS[relative_path]
        return
    separator = ("\n" + DATASET_VIEW_MARKER + "\n").encode()
    expected = {
        "prefix": "dataset_scope_view_prefix_changed",
        "section": "dataset_scope_view_section_changed",
        "duplicate": "dataset_scope_view_boundary",
        "boundary": "dataset_scope_view_boundary",
        "swap": "dataset_scope_view_prefix_changed",
    }[mutation]
    if mutation == "prefix":
        raw = b" " + raw
    elif mutation == "section":
        raw += b" "
    elif mutation == "duplicate":
        raw += DATASET_VIEW_MARKER.encode()
    elif mutation == "boundary":
        # Keep every prefix byte, but invalidate the newline after the marker.
        raw = raw.replace(separator, b"\n" + DATASET_VIEW_MARKER.encode() + b"\r\n", 1)
    else:
        relative_path = next(p for p in DATASET_VIEW_SHA256 if p != relative_path)
    with pytest.raises(AssertionError, match=rf"^{expected}(?:\n|$)"):
        dataset_scope_historical_view(raw, relative_path)


def test_dataset_scope_history_equivalence_detachment_and_nonmutation(monkeypatch: pytest.MonkeyPatch) -> None:
    """DPSG-08: cold/warm immutable cache matches direct inverse with no aliases."""
    monkeypatch.setitem(globals(), "_DATASET_HISTORY_BYTES", None)
    original = validate_dataset_scope_baseline(historical_dataset_scope_manifest())
    first, second = historical_recovery_resume_manifest(), historical_recovery_resume_manifest()
    assert json.dumps(first, sort_keys=True) == json.dumps(original, sort_keys=True) == json.dumps(second, sort_keys=True)
    def ids(v: object) -> set[int]:
        if isinstance(v,dict): return {id(v)}.union(*(ids(x) for x in v.values()))
        if isinstance(v,list): return {id(v)}.union(*(ids(x) for x in v))
        return set()
    assert ids(first).isdisjoint(ids(second)) and ids(first).isdisjoint(ids(RECOVERY_RESUME_RECORD))
    defensive_record(first)["events"][0]["type"] = "MUTATED"
    assert json.dumps(historical_recovery_resume_manifest(), sort_keys=True) == json.dumps(original, sort_keys=True)


@pytest.mark.parametrize("warm", [False,True])
@pytest.mark.parametrize("mutation", ["bytes","type","history","receipt","scope","unrelated"])
def test_dataset_scope_history_original_optimized_rejection(monkeypatch: pytest.MonkeyPatch, warm: bool, mutation: str) -> None:
    """DPSG-08: no cold or warm source change can inherit cached admission."""
    monkeypatch.setitem(globals(), "_DATASET_HISTORY_BYTES", None); manifest = historical_dataset_scope_manifest()
    if warm: historical_recovery_resume_manifest()
    cache = _DATASET_HISTORY_BYTES; record = defensive_record(manifest)
    if mutation == "type": record["execution_authorized"] = 0
    elif mutation == "history": record["events"][0]["type"] = "CHANGED"
    elif mutation == "receipt": record["events"][20]["owner_scope_decision"]["record_url"] = "UNRESOLVED"
    elif mutation == "scope": record["allowed_paths"].append("unapproved.py")
    elif mutation == "unrelated": manifest["program_id"] = "CHANGED"
    raw = (json.dumps(manifest,ensure_ascii=False,indent=2)+"\n").encode()
    if mutation == "bytes": raw += b"\n"
    monkeypatch.setattr(Path,"read_bytes",lambda _path:raw)
    monkeypatch.setitem(globals(),"dataset_resume_historical_source_bytes",lambda:raw)
    with pytest.raises(AssertionError): _dataset_scope_historical_inverse(load_manifest())
    with pytest.raises(AssertionError,match="dataset_scope_fixture_source_changed"): historical_recovery_resume_manifest()
    assert _DATASET_HISTORY_BYTES is cache


@pytest.mark.parametrize("mutation", ["source","baseline","type","shape"])
def test_dataset_scope_history_poisoned_cache(monkeypatch: pytest.MonkeyPatch, mutation: str) -> None:
    """DPSG-08: poisoned cache storage is independently rejected on every read."""
    monkeypatch.setitem(globals(),"_DATASET_HISTORY_BYTES",None); historical_recovery_resume_manifest(); source,baseline = _DATASET_HISTORY_BYTES
    poison = (source+b" ",baseline) if mutation=="source" else (source,baseline+b" ") if mutation=="baseline" else (source,{}) if mutation=="type" else (source,)
    monkeypatch.setitem(globals(),"_DATASET_HISTORY_BYTES",poison)
    with pytest.raises(AssertionError): historical_recovery_resume_manifest()


def test_dataset_scope_history_single_read_and_failed_initialization(monkeypatch: pytest.MonkeyPatch) -> None:
    """DPSG-08: inverse uses exactly the verified read and never caches failed work."""
    monkeypatch.setitem(globals(),"_DATASET_HISTORY_BYTES",None); raw=dataset_resume_historical_source_bytes(); reads=[]; original=_dataset_scope_historical_inverse; calls=[]
    def alternating() -> bytes:
        reads.append(True); return raw if len(reads)==1 else raw+b"\n"
    def checked(m: dict) -> dict:
        calls.append(True); return original(m)
    monkeypatch.setitem(globals(),"dataset_resume_historical_source_bytes",alternating); monkeypatch.setitem(globals(),"_dataset_scope_historical_inverse",checked)
    historical_recovery_resume_manifest(); assert len(reads)==len(calls)==1
    with pytest.raises(AssertionError): historical_recovery_resume_manifest()
    assert len(reads)==2 and len(calls)==1
    monkeypatch.setitem(globals(),"_DATASET_HISTORY_BYTES",None); monkeypatch.setitem(globals(),"dataset_resume_historical_source_bytes",lambda:raw)
    def failed(_m: dict) -> dict: raise AssertionError("injected_inverse_failure")
    monkeypatch.setitem(globals(),"_dataset_scope_historical_inverse",failed)
    with pytest.raises(AssertionError,match="injected_inverse_failure"): historical_recovery_resume_manifest()
    assert _DATASET_HISTORY_BYTES is None


@pytest.mark.parametrize("event_index,field", [(i,f) for i in (15,17,18) for f in ("record_url","recorded_at","effect")] + [(18,"condition")])
def test_dataset_scope_historical_receipt_denials_reach_current_seams(event_index: int, field: str) -> None:
    """DPSG-03: retain historical receipt negatives at today's routing/slot admission."""
    manifest = historical_dataset_scope_manifest(); event = defensive_record(manifest)["events"][event_index]
    decision = event["owner_scope_decision"] if event_index == 17 else event["owner_resume_decision"]
    decision[field] = "UNRESOLVED_OR_REUSED"
    for validator in (validate_dataset_scope_baseline,):
        with pytest.raises(AssertionError): validator(manifest)


# DPRG: conditional registered28-file development/testing resume only.
DATASET_REPAIR_SCOPE = deepcopy(DATASET_SCOPE_EVENT["owner_scope_decision"]["subject"]["repair_scope"])
DATASET_RESUME_EXECUTION_SCOPE = json.loads(r'''{
  "kind": "BOUNDED_CUSTOMER_DATASET_PROVENANCE_AND_RECOVERY_DEVELOPMENT_TESTING",
  "implementation_paths": [
    "backend/asie_local_api.py",
    "backend/workspace.py",
    "backend/workflow.py",
    "backend/dib_api.py",
    "backend/dib_persistence.py",
    "backend/dib_tenant_api.py",
    "backend/dib_http_mounting.py",
    "backend/release_info.py",
    "src/contracts.ts",
    "src/dibApi.ts",
    "src/App.tsx",
    "src/customerLanguage.tsx",
    "src/ASIECompleteSurfaceMount.tsx",
    "src/DIBWorkspace.tsx",
    "src/DIBIntakeItemGovernance.tsx",
    "src/DIBManifestRunReadiness.tsx",
    "registry/asie-canonical-api-output.v1.json",
    "docs/ASIE-CANONICAL-API-OUTPUT-REGISTER-v1.0.0.md",
    "tests/test_customer_language_foundation.py",
    "tests/test_gov_beta_04_server_owned_manifest_chain.py",
    "tests/test_context_recovery_api.py",
    "tests/test_dib_context_recovery.py",
    "tests/test_customer_capability_projection.py",
    "tools/check_context_recovery_browser.py",
    "backend/datasets.py",
    "backend/repository.py",
    "backend/evidence_ledger.py",
    "src/api.ts"
  ],
  "activities": [
    "DEVELOP_REGISTERED_CUSTOMER_DATASET_PROVENANCE_AND_RECOVERY",
    "TEST_REGISTERED_CUSTOMER_DATASET_PROVENANCE_AND_RECOVERY"
  ],
  "repair_scope_sha256": "53e37b158f8446d29637ff8f47f29b06eeed8ec910cbcdde4f3ac4eb9a1b640f",
  "digest_serialization": "UTF8_JSON_ENSURE_ASCII_FALSE_SORT_KEYS_TRUE_COMPACT_SEPARATORS_COMMA_COLON",
  "database_scope": "DISPOSABLE_TEMPORARY_DATABASES_ONLY",
  "data_scope": "SYNTHETIC_DATA_ONLY",
  "existing_recovery_contract": "PRESERVE_FULL_REGISTERED_24_FILE_CONTRACT",
  "customer_policy": "NO_LICENSE_TERMS_PROOF_FOR_AUTHENTICATED_CUSTOMER_OWN_STUDY_MATERIAL",
  "legacy_policy": "NO_EXEMPTION_WITHOUT_VALID_PROVENANCE_NO_AUTOMATIC_BACKFILL",
  "same_owner_reuse": "AUTHORIZED_PROJECTS_WITHIN_SAME_ORGANIZATION",
  "additional_schema_operations": [],
  "live_database_authorized": false,
  "provider_activation_authorized": false,
  "external_network_authorized": false,
  "deployment_authorized": false,
  "application_merge_authorized": false,
  "production_placement_accepted": false,
  "startup_maintenance_recovery_acceptance": "UNKNOWN_NOT_APPROVED",
  "t08": "OPEN"
}''')
DATASET_RESUME_DECISION = json.loads(r'''{
  "id": "DECISION-FC20-12-F01A-CONDITIONAL-DATASET-PROVENANCE-RESUME-2026-10-15",
  "record_url": "https://github.com/alphasigma13579-lang/ASIE/pull/211#issuecomment-6189149415",
  "recorded_at": "2026-10-15T09:41:11.266227+00:00",
  "effect": "F01A_DEFENSIVE_RESUME_ONLY",
  "condition": "REVIEWED_GOVERNANCE_TRANSITION_MERGED_AFTER_SEPARATE_OWNER_MERGE_APPROVAL",
  "subject": {
    "baseline_commit_sha": "a1e82fccaba18986ae9552fbfd41364d8179fd19",
    "baseline_manifest_blob_sha": "56e59d99d30e608b2f9b96e2abac0ed3daa0f841",
    "registration_head_sha": "7f62bc0ad3ff8466cbe6fe62222c5c176b992598",
    "application_head_sha": "b011a6b3773f4c5e0a905161b5504fff339496f6"
  }
}''')
DATASET_RESUME_DECISION["subject"].update(checkpoint=deepcopy(DATASET_STOP_EVENT), scope_extension=deepcopy(DATASET_SCOPE_EVENT), repair_scope=deepcopy(DATASET_REPAIR_SCOPE), execution_scope=deepcopy(DATASET_RESUME_EXECUTION_SCOPE))
DATASET_RESUME_EVENT = json.loads(r'''{
  "type": "RESUME",
  "recorded_at": "2026-10-15T09:42:26Z",
  "baseline_commit_sha": "a1e82fccaba18986ae9552fbfd41364d8179fd19",
  "baseline_manifest_blob_sha": "56e59d99d30e608b2f9b96e2abac0ed3daa0f841",
  "effect": "F01A_DEFENSIVE_RESUME_ONLY"
}''')
DATASET_RESUME_EVENT.update(checkpoint=deepcopy(DATASET_STOP_EVENT), scope_extension=deepcopy(DATASET_SCOPE_EVENT), owner_resume_decision=deepcopy(DATASET_RESUME_DECISION))
DATASET_RESUME_RECORD = deepcopy(DATASET_SCOPE_RECORD)
DATASET_RESUME_RECORD["execution_authorized"] = True
DATASET_RESUME_RECORD["events"].append(deepcopy(DATASET_RESUME_EVENT))
DATASET_RESUME_VIEW_PREFIX_BLOBS = json.loads(r'''{
  "docs/FOUNDATION-COMPLETE-20-CORE-INTELLIGENCE-COMPLETION-PROGRAM-2026-07-29.md": "c1a4265985e8d58d185c4913f413d6e7da57c311",
  "docs/EKB/FOUNDATION-COMPLETE-20-PACKAGE-INDEX.md": "68065ccbc756347b2db19ce5611ffd6adbb8d275",
  "docs/ASIE-BETA-EXECUTION-MASTER-PLAN-2026-09-09.md": "4cd83c9a15a9e13161220e753619d0d880b8b000",
  "docs/FC20-12-F01A-DEFENSIVE-ENABLING-REGISTRATION-PROPOSAL-2026-10-01.md": "f412f07f4b5f3c6a938cafaf84ce6005c4986cfa",
  "docs/FC20-12-F01A-APPROVAL-CONSUMPTION-SCOPE-REGISTRATION-2026-10-09.md": "602e9ecfe75209d7eb2c794b7625455c7503aff0"
}''')
DATASET_RESUME_VIEW_SHA256 = json.loads(r'''{
  "docs/FOUNDATION-COMPLETE-20-CORE-INTELLIGENCE-COMPLETION-PROGRAM-2026-07-29.md": "86b66ab6a62fb9d8111278302662d6d339bc477bbe687c5f75dc03a334624ee0",
  "docs/EKB/FOUNDATION-COMPLETE-20-PACKAGE-INDEX.md": "404df0efbb2610d55ccc0e179c0fdb91670d9e207ba51d86b76fd637f8ec8cf7",
  "docs/ASIE-BETA-EXECUTION-MASTER-PLAN-2026-09-09.md": "407130071f8f53097b61e743fe50eda254bd8e6175cafdf9699a399bdefd68a0",
  "docs/FC20-12-F01A-DEFENSIVE-ENABLING-REGISTRATION-PROPOSAL-2026-10-01.md": "48a11d95a37d636bf65c768b41df070e55acb0be5dcbff23fa32aa7f0a775da7",
  "docs/FC20-12-F01A-APPROVAL-CONSUMPTION-SCOPE-REGISTRATION-2026-10-09.md": "94d4bac2f4a6980c96dc6ab4581f7f14c4a0d68665ab034534c449e4f3ad5c0f"
}''')
DATASET_RESUME_VIEW_MARKER = '<!-- F01A-DATASET-PROVENANCE-CONDITIONAL-RESUME-2026-10-15 -->'
DATASET_RESUME_MANIFEST_BLOB = '6e05c33c3df07a42ee5b7e695e3b528f9866d342'


def _validate_dataset_resume_structure(record: dict, active_target: object) -> None:
    """DPRG-01/02: closed typed resume and all pinned history, without receipt admission."""
    assert isinstance(record, dict), "invalid_defensive_record"
    assert set(record) == set(DATASET_RESUME_RECORD), "defensive_fields"
    if record != DATASET_RESUME_RECORD:
        raise AssertionError("defensive_record_mismatch")
    if json.dumps(record, sort_keys=True) != json.dumps(DATASET_RESUME_RECORD, sort_keys=True):
        raise AssertionError("dataset_resume_literal_types")
    assert record["execution_authorized"] is True, "dataset_resume_flag"
    assert active_target == DEFENSIVE_START_TARGET, "dataset_resume_slot"
    assert record["allowed_paths"] == DATASET_SCOPE_RECORD["allowed_paths"], "dataset_resume_paths"
    assert record["allowed_schema_operations"] == [INDEX_OPERATION], "dataset_resume_index"
    assert record["allowed_schema_operations"][0]["unique"] is False, "dataset_resume_index_literal"
    event = record["events"][21]
    for target in (event, event["owner_resume_decision"]["subject"]):
        assert target["checkpoint"] == DATASET_STOP_EVENT, "dataset_resume_checkpoint"
        assert target["scope_extension"] == DATASET_SCOPE_EVENT, "dataset_resume_scope"
    subject = event["owner_resume_decision"]["subject"]
    assert subject["repair_scope"] == DATASET_REPAIR_SCOPE, "dataset_resume_repair_scope"
    assert subject["execution_scope"] == DATASET_RESUME_EXECUTION_SCOPE, "dataset_resume_execution_scope"


def validate_dataset_resume(record: dict, active_target: object) -> None:
    """DPRG-03: a fresh exact execution decision and its merge condition are mandatory."""
    _validate_dataset_resume_structure(record, active_target)
    decision = record["events"][21]["owner_resume_decision"]
    assert decision["record_url"] == "https://github.com/alphasigma13579-lang/ASIE/pull/211#issuecomment-6189149415", "dataset_resume_execution_decision_missing"
    assert decision["recorded_at"] == "2026-10-15T09:41:11.266227+00:00", "dataset_resume_execution_decision_time"
    assert decision["condition"] == "REVIEWED_GOVERNANCE_TRANSITION_MERGED_AFTER_SEPARATE_OWNER_MERGE_APPROVAL", "dataset_resume_merge_condition"


def _dataset_resume_historical_inverse(manifest: dict) -> dict:
    """DPRG-04: exact detached stopped baseline, never an alternative current authority."""
    original = defensive_record(manifest)
    _validate_dataset_resume_structure(original, manifest["execution_sequence"]["active_target"])
    restored = dict(manifest)
    restored["packages"] = list(manifest["packages"])
    index = next(i for i, p in enumerate(manifest["packages"]) if p["id"] == "FC20-12")
    package = dict(manifest["packages"][index]); restored["packages"][index] = package
    package["execution_slices"] = list(package["execution_slices"])
    record = dict(original); package["execution_slices"][1] = record
    record["events"] = list(original["events"][:21])
    record["execution_authorized"] = False
    raw = (json.dumps(restored, ensure_ascii=False, indent=2) + "\n").encode()
    assert git_blob_sha(raw) == "56e59d99d30e608b2f9b96e2abac0ed3daa0f841", "dataset_resume_baseline_mismatch"
    detached = json.loads(raw)
    validate_dataset_scope(defensive_record(detached), detached["execution_sequence"]["active_target"])
    return detached


def validate_dataset_resume_baseline(manifest: dict) -> dict:
    """DPRG-03/04: public inverse first requires the real current execution receipt."""
    validate_dataset_resume(defensive_record(manifest), manifest["execution_sequence"]["active_target"])
    return _dataset_resume_historical_inverse(manifest)


_DATASET_RESUME_HISTORY_BYTES: tuple[bytes, bytes] | None = None


def dataset_resume_historical_source_bytes() -> bytes:
    """DPRG-08: re-pin every read and expose only immutable inverse-verified history."""
    global _DATASET_RESUME_HISTORY_BYTES
    source = overlay_scope_historical_source_bytes()
    # Reuse object identity only after comparing every byte of the fresh read.
    # Ineligible/poisoned caches still reach the original checks in their order.
    digest_source = source
    history = _DATASET_RESUME_HISTORY_BYTES
    if (type(source) is bytes and type(history) is tuple and len(history) == 2
            and type(history[0]) is bytes and type(history[1]) is bytes
            and source == history[0]):
        digest_source = history[0]
    assert recovery_resume_blob_sha(digest_source) == DATASET_RESUME_MANIFEST_BLOB, "dataset_resume_fixture_source_changed"
    if _DATASET_RESUME_HISTORY_BYTES is None:
        baseline = _dataset_resume_historical_inverse(json.loads(source.decode("utf-8")))
        raw = (json.dumps(baseline, ensure_ascii=False, indent=2) + "\n").encode()
        assert recovery_resume_blob_sha(raw) == "56e59d99d30e608b2f9b96e2abac0ed3daa0f841", "dataset_resume_fixture_baseline_changed"
        _DATASET_RESUME_HISTORY_BYTES = (source, raw)
    assert isinstance(_DATASET_RESUME_HISTORY_BYTES, tuple) and len(_DATASET_RESUME_HISTORY_BYTES) == 2, "dataset_resume_fixture_cache_shape"
    cached_source, raw = _DATASET_RESUME_HISTORY_BYTES
    assert type(cached_source) is bytes and type(raw) is bytes, "dataset_resume_fixture_cache_type"
    source_matches = source == cached_source
    assert source_matches, "dataset_resume_fixture_cache_source_changed"
    assert recovery_resume_blob_sha(raw) == "56e59d99d30e608b2f9b96e2abac0ed3daa0f841", "dataset_resume_fixture_baseline_changed"
    return raw


def historical_dataset_scope_manifest() -> dict:
    """Verified twenty-one-event test fixture with fresh detached mutable containers."""
    return json.loads(dataset_resume_historical_source_bytes().decode("utf-8"))


def dataset_resume_historical_view(source_bytes: bytes, relative_path: str) -> bytes:
    """DPRG-05: preserve the exact old prefix and path-specific new terminal section."""
    assert isinstance(source_bytes, bytes), "dataset_resume_view_source_bytes"
    assert relative_path in DATASET_RESUME_VIEW_SHA256, "dataset_resume_view_path"
    marker = DATASET_RESUME_VIEW_MARKER.encode(); separator = b"\n" + marker + b"\n"
    assert source_bytes.count(marker) == 1, "dataset_resume_view_marker"
    assert source_bytes.count(separator) == 1, "dataset_resume_view_boundary"
    prefix, section = source_bytes.split(separator, 1)
    assert git_blob_sha(prefix) == DATASET_RESUME_VIEW_PREFIX_BLOBS[relative_path], "dataset_resume_view_prefix_changed"
    assert hashlib.sha256(marker + b"\n" + section).hexdigest() == DATASET_RESUME_VIEW_SHA256[relative_path], "dataset_resume_view_projection_changed"
    dataset_scope_historical_view(prefix, relative_path)
    return prefix


def test_dataset_resume_current_admission_and_complete_inverse() -> None:
    """DPRG-01/03/04: real conditional authority, preserved scope and full history."""
    manifest = historical_dataset_resume_manifest()
    validate_routing_registration(load_manifest())
    record = defensive_record(manifest)
    assert len(record["events"]) == 22 and record["events"][:21] == DATASET_SCOPE_RECORD["events"]
    assert len(record["allowed_paths"]) == 35
    assert len(DATASET_RESUME_EXECUTION_SCOPE["implementation_paths"]) == 28
    assert DATASET_RESUME_EXECUTION_SCOPE["implementation_paths"] == DATASET_REPAIR_SCOPE["implementation_paths"]
    scope = validate_dataset_resume_baseline(manifest)
    recovery = validate_dataset_scope_baseline(scope)
    prior = validate_recovery_resume_baseline(recovery)
    key = validate_recovery_scope_baseline(prior)
    stopped = validate_key_binding_resume_baseline(key)
    previous = validate_key_binding_scope_baseline(stopped)
    old_review_scope = validate_review_identity_resume_baseline(previous)
    old_index_resume = validate_review_identity_scope_baseline(old_review_scope)
    index_scope = validate_index_resume_baseline(old_index_resume)
    consumption_resume = validate_index_scope_baseline(index_scope)
    consumption_scope = validate_consumption_resume_baseline(consumption_resume)
    old_resume = validate_consumption_scope_baseline(consumption_scope)
    validate_scope_extension_baseline(validate_resume_baseline(old_resume))


def dataset_resume_new_leaf_paths() -> list[tuple]:
    """DPRG-06: enumerate new decision leaves, leaving sealed history to its own tests."""
    event = deepcopy(DATASET_RESUME_EVENT)
    event.pop("checkpoint"); event.pop("scope_extension")
    subject = event["owner_resume_decision"]["subject"]
    subject.pop("checkpoint"); subject.pop("scope_extension"); subject.pop("repair_scope")
    return [tuple(p) for p in index_resume_leaf_paths(event)]


@pytest.mark.parametrize("path", dataset_resume_new_leaf_paths())
def test_dataset_resume_pins_each_new_leaf(path: tuple) -> None:
    """DPRG-06: every new scope, condition and identity scalar is independently pinned."""
    record = deepcopy(DATASET_RESUME_RECORD); target = record["events"][21]
    for key in path[:-1]: target = target[key]
    target[path[-1]] = "UNREVIEWED"
    with pytest.raises(AssertionError, match="defensive_record_mismatch"):
        _validate_dataset_resume_structure(record, DEFENSIVE_START_TARGET)


@pytest.mark.parametrize("container", ("event", "decision", "subject", "execution_scope"))
@pytest.mark.parametrize("mutation", ("missing", "extra"))
def test_dataset_resume_closed_objects(container: str, mutation: str) -> None:
    """DPRG-06: no omitted guard or extra activity can enter the closed decision."""
    def select(record: dict) -> dict:
        event = record["events"][21]
        if container == "event": return event
        decision = event["owner_resume_decision"]
        if container == "decision": return decision
        subject = decision["subject"]
        return subject if container == "subject" else subject["execution_scope"]
    for field in select(DATASET_RESUME_RECORD):
        record = deepcopy(DATASET_RESUME_RECORD); target = select(record)
        if mutation == "missing": target.pop(field)
        else: target["unapproved"] = True
        with pytest.raises(AssertionError, match="defensive_record_mismatch"):
            _validate_dataset_resume_structure(record, DEFENSIVE_START_TARGET)


@pytest.mark.parametrize("event_index", range(21))
def test_dataset_resume_preserves_each_prior_event(event_index: int) -> None:
    """DPRG-02: every prior event is preserved in the exact full-byte inverse."""
    record = deepcopy(DATASET_RESUME_RECORD); record["events"][event_index]["type"] = "CHANGED"
    with pytest.raises(AssertionError, match="defensive_record_mismatch"):
        _validate_dataset_resume_structure(record, DEFENSIVE_START_TARGET)


@pytest.mark.parametrize("location", ("event", "subject"))
@pytest.mark.parametrize("field", ("checkpoint", "scope_extension"))
@pytest.mark.parametrize("mutation", ("missing", "type", "literal"))
def test_dataset_resume_preserves_both_checkpoint_scope_copies(location: str, field: str, mutation: str) -> None:
    """DPRG-02: historical copies remain whole and retain strict JSON types."""
    record = deepcopy(DATASET_RESUME_RECORD); target = record["events"][21]
    if location == "subject": target = target["owner_resume_decision"]["subject"]
    if mutation == "missing": target.pop(field)
    elif mutation == "type": target[field]["type"] = "CHANGED"
    elif field == "scope_extension":
        target[field]["owner_scope_decision"]["subject"]["repair_scope"]["additional_schema_operations"] = ["UNAPPROVED"]
    else: target[field]["recorded_at"] = False
    with pytest.raises(AssertionError, match="defensive_record_mismatch|dataset_resume_literal_types"):
        _validate_dataset_resume_structure(record, DEFENSIVE_START_TARGET)


@pytest.mark.parametrize("value", (False, 0, 1, None, "true"))
def test_dataset_resume_requires_literal_true(value: object) -> None:
    """DPRG-01: only the exact conditional resume flag is admissible."""
    record = deepcopy(DATASET_RESUME_RECORD); record["execution_authorized"] = value
    with pytest.raises(AssertionError, match="defensive_record_mismatch|dataset_resume_literal_types"):
        validate_dataset_resume(record, DEFENSIVE_START_TARGET)


@pytest.mark.parametrize("field,value", (("record_url", "UNRESOLVED_OWNER_EXECUTION_DECISION_RECORD_URL"), ("recorded_at", "UNRESOLVED"), ("condition", "IMMEDIATE"), ("effect", "PREPARE_AND_PUBLISH_GOVERNANCE_DRAFT_ONLY_NO_MERGE_NO_RESUME")))
def test_dataset_resume_missing_or_reused_decision_denied_at_all_current_seams(field: str, value: str) -> None:
    """DPRG-03: preparation permission cannot substitute for conditional execution."""
    manifest = historical_dataset_resume_manifest(); defensive_record(manifest)["events"][21]["owner_resume_decision"][field] = value
    for validator in (validate_dataset_resume_baseline,):
        with pytest.raises(AssertionError, match="defensive_record_mismatch"):
            validator(manifest)


@pytest.mark.parametrize("event_index,field", [(i,f) for i in (15,17,18,20) for f in ("record_url","recorded_at","effect")] + [(18,"condition")])
def test_dataset_resume_prior_receipt_negatives_reach_current_seams(event_index: int, field: str) -> None:
    """DPRG-02/03: preserve prior receipt negatives against a valid current baseline."""
    manifest = historical_dataset_resume_manifest()
    validate_routing_registration(load_manifest())
    event = defensive_record(manifest)["events"][event_index]
    decision = event["owner_scope_decision" if event_index in (17,20) else "owner_resume_decision"]
    decision[field] = "UNRESOLVED_OR_CHANGED"
    for validator in (validate_dataset_resume_baseline,):
        with pytest.raises(AssertionError, match="defensive_record_mismatch"):
            validator(manifest)


@pytest.mark.parametrize("mutation", ("scope_union", "paths", "schema", "index_zero", "slot", "hold", "unrelated"))
def test_dataset_resume_denies_scope_slot_and_unrelated_drift_without_mutation(mutation: str) -> None:
    """DPRG-04/06: inverse covers all manifest bytes, not only the changed slice."""
    manifest = historical_dataset_resume_manifest(); record = defensive_record(manifest)
    if mutation == "scope_union": record["events"][21]["owner_resume_decision"]["subject"]["execution_scope"]["implementation_paths"] = list(record["allowed_paths"])
    elif mutation == "paths": record["allowed_paths"].reverse()
    elif mutation == "schema": record["allowed_schema_operations"].append({"operation": "UNAPPROVED"})
    elif mutation == "index_zero": record["allowed_schema_operations"][0]["unique"] = 0
    elif mutation == "slot": manifest["execution_sequence"]["active_target"] = None
    elif mutation == "hold": manifest["execution_sequence"]["held_packages"] = []
    else: manifest["program_id"] = "UNRELATED"
    before = json.dumps(manifest, sort_keys=True)
    with pytest.raises(AssertionError): validate_dataset_resume_baseline(manifest)
    assert json.dumps(manifest, sort_keys=True) == before


@pytest.mark.parametrize("relative_path", tuple(DATASET_RESUME_VIEW_SHA256))
@pytest.mark.parametrize("mutation", ("valid", "prefix", "section", "duplicate", "boundary", "swap"))
def test_dataset_resume_projection_exact_seals(relative_path: str, mutation: str) -> None:
    """DPRG-05: exact path-specific terminal bytes preserve all old projections."""
    root = Path(__file__).resolve().parents[1]; source = overlay_scope_historical_view(overlay_resume_historical_view(ci_scope_historical_view(ci_resume_historical_view(ci_amend_historical_view((root / relative_path).read_bytes(), relative_path), relative_path), relative_path), relative_path), relative_path)
    separator = ("\n" + DATASET_RESUME_VIEW_MARKER + "\n").encode()
    prefix, section = source.split(separator, 1)
    if mutation == "valid":
        assert dataset_resume_historical_view(source, relative_path) == prefix
        return
    if mutation == "prefix": source = b" " + source
    elif mutation == "section": source += b" "
    elif mutation == "duplicate": source += separator
    elif mutation == "boundary": source = prefix + b"\n" + DATASET_RESUME_VIEW_MARKER.encode() + b"\r\n" + section
    else:
        other = next(p for p in DATASET_RESUME_VIEW_SHA256 if p != relative_path)
        source = prefix + separator + overlay_scope_historical_view(overlay_resume_historical_view(ci_scope_historical_view(ci_resume_historical_view(ci_amend_historical_view((root / other).read_bytes(), other), other), other), other), other).split(separator, 1)[1]
    with pytest.raises(AssertionError, match="dataset_resume_view"):
        dataset_resume_historical_view(source, relative_path)


def test_dataset_resume_fixture_cold_warm_equivalence_and_detachment(monkeypatch: pytest.MonkeyPatch) -> None:
    """DPRG-08: optimized history equals direct inverse and never shares mutable state."""
    import sys
    module = sys.modules[__name__]; monkeypatch.setattr(module, "_DATASET_RESUME_HISTORY_BYTES", None)
    manifest = historical_dataset_resume_manifest(); original = validate_dataset_resume_baseline(manifest)
    expected = json.dumps(original, ensure_ascii=False, indent=2) + "\n"
    first, second = historical_dataset_scope_manifest(), historical_dataset_scope_manifest()
    assert json.dumps(first, ensure_ascii=False, indent=2) + "\n" == expected
    assert json.dumps(second, ensure_ascii=False, indent=2) + "\n" == expected
    assert isinstance(_DATASET_RESUME_HISTORY_BYTES, tuple) and all(isinstance(x, bytes) for x in _DATASET_RESUME_HISTORY_BYTES)
    def ids(value: object) -> set[int]:
        if isinstance(value, dict): return {id(value)}.union(*(ids(v) for v in value.values()))
        if isinstance(value, list): return {id(value)}.union(*(ids(v) for v in value))
        return set()
    assert ids(first).isdisjoint(ids(second)) and ids(first).isdisjoint(ids(manifest)) and ids(first).isdisjoint(ids(DATASET_SCOPE_RECORD))
    defensive_record(first)["events"][0]["type"] = "CHANGED_RETURN"
    assert json.dumps(historical_dataset_scope_manifest(), ensure_ascii=False, indent=2) + "\n" == expected


@pytest.mark.parametrize("warm", (False, True))
@pytest.mark.parametrize("mutation", ("bytes", "type", "history", "slot", "unrelated", "receipt", "scope"))
def test_dataset_resume_fixture_original_and_optimized_denials(monkeypatch: pytest.MonkeyPatch, warm: bool, mutation: str) -> None:
    """DPRG-08: cold and warm reads cannot reuse approval after any source change."""
    import sys
    module = sys.modules[__name__]; monkeypatch.setattr(module, "_DATASET_RESUME_HISTORY_BYTES", None)
    manifest = historical_dataset_resume_manifest()
    if warm: historical_dataset_scope_manifest()
    cache = _DATASET_RESUME_HISTORY_BYTES; record = defensive_record(manifest)
    if mutation == "type": record["execution_authorized"] = 1
    elif mutation == "history": record["events"][0]["type"] = "CHANGED"
    elif mutation == "slot": manifest["execution_sequence"]["active_target"] = None
    elif mutation == "unrelated": manifest["program_id"] = "CHANGED"
    elif mutation == "receipt": record["events"][21]["owner_resume_decision"]["record_url"] = "UNRESOLVED"
    elif mutation == "scope": record["allowed_paths"].append("unapproved.py")
    raw = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode()
    if mutation == "bytes": raw += b"\n"
    monkeypatch.setattr(Path, "read_bytes", lambda _path: raw)
    monkeypatch.setattr(module, "overlay_scope_historical_source_bytes", lambda: raw)
    with pytest.raises(AssertionError): _dataset_resume_historical_inverse(load_manifest())
    with pytest.raises(AssertionError, match="dataset_resume_fixture_source_changed"): historical_dataset_scope_manifest()
    assert _DATASET_RESUME_HISTORY_BYTES is cache


@pytest.mark.parametrize("mutation", ("source", "baseline", "type", "shape"))
def test_dataset_resume_fixture_poisoned_cache_rejected(monkeypatch: pytest.MonkeyPatch, mutation: str) -> None:
    """DPRG-08: cache bytes must stay typed and independently pinned on every call."""
    import sys
    module = sys.modules[__name__]; monkeypatch.setattr(module, "_DATASET_RESUME_HISTORY_BYTES", None)
    historical_dataset_scope_manifest(); source, baseline = _DATASET_RESUME_HISTORY_BYTES
    poisoned = (source+b" ", baseline) if mutation == "source" else (source, baseline+b" ") if mutation == "baseline" else (source, {}) if mutation == "type" else (source,)
    monkeypatch.setattr(module, "_DATASET_RESUME_HISTORY_BYTES", poisoned)
    with pytest.raises(AssertionError, match="dataset_resume_fixture_"): historical_dataset_scope_manifest()


def test_dataset_resume_fixture_single_read_and_failed_initialization(monkeypatch: pytest.MonkeyPatch) -> None:
    """DPRG-08: cold inverse consumes the pinned read and failure never publishes cache."""
    import sys
    module = sys.modules[__name__]; monkeypatch.setattr(module, "_DATASET_RESUME_HISTORY_BYTES", None)
    raw = overlay_scope_historical_source_bytes(); reads = []; calls = []; original = _dataset_resume_historical_inverse
    def alternating() -> bytes:
        reads.append(True)
        return raw if len(reads) == 1 else raw+b"\n"
    def checked(manifest: dict) -> dict:
        calls.append(True)
        return original(manifest)
    monkeypatch.setattr(module, "overlay_scope_historical_source_bytes", alternating); monkeypatch.setattr(module, "_dataset_resume_historical_inverse", checked)
    historical_dataset_scope_manifest()
    assert len(reads) == len(calls) == 1
    with pytest.raises(AssertionError, match="dataset_resume_fixture_source_changed"): historical_dataset_scope_manifest()
    assert len(reads) == 2 and len(calls) == 1
    monkeypatch.setattr(module, "_DATASET_RESUME_HISTORY_BYTES", None)
    monkeypatch.setattr(module, "overlay_scope_historical_source_bytes", lambda: raw)
    def failed(_manifest: dict) -> dict: raise AssertionError("injected_inverse_failure")
    monkeypatch.setattr(module, "_dataset_resume_historical_inverse", failed)
    with pytest.raises(AssertionError, match="injected_inverse_failure"): historical_dataset_scope_manifest()
    assert _DATASET_RESUME_HISTORY_BYTES is None




def test_key_binding_digest_memo_is_content_only_and_bounded() -> None:
    """Digest reuse preserves exact bytes, bounded eviction and the original hash."""
    _key_binding_cached_blob_sha.cache_clear()
    first = b"synthetic-key-binding-content"; equal = bytes(bytearray(first))
    assert first == equal and first is not equal
    assert key_binding_fixture_blob_sha(first) == git_blob_sha(first)
    assert key_binding_fixture_blob_sha(equal) == git_blob_sha(equal)
    assert _key_binding_cached_blob_sha.cache_info().hits == 1
    changed = first[:-1] + b"X"
    assert key_binding_fixture_blob_sha(changed) == git_blob_sha(changed) != git_blob_sha(first)
    key_binding_fixture_blob_sha(b"third")
    assert _key_binding_cached_blob_sha.cache_info().currsize == 2
    misses = _key_binding_cached_blob_sha.cache_info().misses
    key_binding_fixture_blob_sha(first)
    assert _key_binding_cached_blob_sha.cache_info().misses == misses + 1


def test_key_binding_digest_memo_preserves_nonexact_buffer_behavior() -> None:
    """Mutable buffers and custom bytes never inherit a cached content decision."""
    class PretendBytes(bytes):
        def __eq__(self, other): return True
        __hash__ = bytes.__hash__
    _key_binding_cached_blob_sha.cache_clear()
    mutable = bytearray(b"original")
    for raw in (mutable, memoryview(mutable), PretendBytes(b"original")):
        assert key_binding_fixture_blob_sha(raw) == git_blob_sha(raw)
    mutable[0] = ord("X")
    assert key_binding_fixture_blob_sha(mutable) == git_blob_sha(mutable) != git_blob_sha(b"original")
    assert _key_binding_cached_blob_sha.cache_info().currsize == 0
    for raw in (None, "text", 1, []):
        with pytest.raises(TypeError): git_blob_sha(raw)
        with pytest.raises(TypeError): key_binding_fixture_blob_sha(raw)


def test_key_binding_digest_memo_does_not_cache_failed_computation(monkeypatch: pytest.MonkeyPatch) -> None:
    """A failed pure digest cannot publish a cache entry."""
    import sys
    module = sys.modules[__name__]; _key_binding_cached_blob_sha.cache_clear()
    original = git_blob_sha
    def failed(raw): raise RuntimeError("synthetic_digest_failure")
    monkeypatch.setattr(module, "git_blob_sha", failed)
    with pytest.raises(RuntimeError, match="synthetic_digest_failure"):
        key_binding_fixture_blob_sha(b"fresh")
    assert _key_binding_cached_blob_sha.cache_info().currsize == 0
    monkeypatch.setattr(module, "git_blob_sha", original)
    assert key_binding_fixture_blob_sha(b"fresh") == original(b"fresh")
    _key_binding_cached_blob_sha.cache_clear()


def test_dataset_resume_digest_reuses_only_fresh_equal_bytes(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every warm lookup reads and compares source bytes before object reuse."""
    import sys
    module = sys.modules[__name__]
    monkeypatch.setattr(module, "_DATASET_RESUME_HISTORY_BYTES", None)
    baseline = dataset_resume_historical_source_bytes()
    cached_source, cached_baseline = _DATASET_RESUME_HISTORY_BYTES
    calls = []; reads = []; original = recovery_resume_blob_sha
    def fresh():
        raw = bytes(bytearray(cached_source)); reads.append(raw); return raw
    def observed(raw):
        calls.append(raw); return original(raw)
    monkeypatch.setattr(module, "overlay_scope_historical_source_bytes", fresh)
    monkeypatch.setattr(module, "recovery_resume_blob_sha", observed)
    assert dataset_resume_historical_source_bytes() == baseline
    assert len(reads) == 1 and reads[0] is not cached_source
    assert calls[0] is cached_source and calls[-1] is cached_baseline
    monkeypatch.setattr(module, "DATASET_RESUME_MANIFEST_BLOB", "0" * 40)
    with pytest.raises(AssertionError, match="dataset_resume_fixture_source_changed"):
        dataset_resume_historical_source_bytes()


@pytest.mark.parametrize("mutation", ("source_subclass", "cache_source_subclass", "cache_baseline_subclass", "cache_shape", "poisoned_source", "poisoned_baseline", "source_and_cache"))
def test_dataset_resume_digest_fast_path_preserves_denial_order(monkeypatch: pytest.MonkeyPatch, mutation: str) -> None:
    """Fast-path eligibility cannot hide changed bytes, custom equality or bad caches."""
    import sys
    module = sys.modules[__name__]
    monkeypatch.setattr(module, "_DATASET_RESUME_HISTORY_BYTES", None)
    dataset_resume_historical_source_bytes(); source, baseline = _DATASET_RESUME_HISTORY_BYTES
    class PretendBytes(bytes):
        def __eq__(self, other): return True
        __hash__ = bytes.__hash__
    fresh = source; cache = (source, baseline)
    expected = "dataset_resume_fixture_cache_type"
    if mutation == "source_subclass":
        fresh = PretendBytes(source); expected = "recovery_resume_digest_requires_exact_bytes"
    elif mutation == "cache_source_subclass": cache = (PretendBytes(source), baseline)
    elif mutation == "cache_baseline_subclass": cache = (source, PretendBytes(baseline))
    elif mutation == "cache_shape": cache = (source,); expected = "dataset_resume_fixture_cache_shape"
    elif mutation == "poisoned_source": cache = (source+b" ", baseline); expected = "dataset_resume_fixture_cache_source_changed"
    elif mutation == "poisoned_baseline": cache = (source, baseline+b" "); expected = "dataset_resume_fixture_baseline_changed"
    else:
        fresh = source[:-1]+b" "; cache = (source,); expected = "dataset_resume_fixture_source_changed"
    monkeypatch.setattr(module, "overlay_scope_historical_source_bytes", lambda: fresh)
    monkeypatch.setattr(module, "_DATASET_RESUME_HISTORY_BYTES", cache)
    with pytest.raises((AssertionError, TypeError), match=expected): dataset_resume_historical_source_bytes()
    assert _DATASET_RESUME_HISTORY_BYTES is cache


# OMSG: stopped bounded overlay maintenance registration.
OVERLAY_STOP_EVENT = json.loads(r'''{
  "type": "STOP_CHECKPOINT",
  "recorded_at": "2026-10-16T12:26:07Z",
  "baseline_commit_sha": "d1bfdd544b54f34f293a7a8dad67d7f8c56511c7",
  "baseline_manifest_blob_sha": "6e05c33c3df07a42ee5b7e695e3b528f9866d342",
  "application_head_sha": "492206f4703c9a1e5dc84fca40516cc438ca3352",
  "reason": "REVIEW_OVERLAY_CLASSIFICATION_AND_TEST_MAINTENANCE_OUTSIDE_ACTIVE_28_FILE_OPERATION",
  "evidence": {
    "decision_url": "https://github.com/alphasigma13579-lang/ASIE/pull/189#issuecomment-6215466332",
    "application_commit_sha": "492206f4703c9a1e5dc84fca40516cc438ca3352"
  },
  "resume_requirement": "NEW_OWNER_EXECUTION_DECISION_AND_REVIEWED_SCOPE_BOUND_RESUME_MERGED_AFTER_SEPARATE_APPROVAL"
}''')
OVERLAY_SCOPE_EVENT = json.loads(r'''{
  "type": "SCOPE_EXTENSION",
  "recorded_at": "2026-10-16T12:26:07Z",
  "baseline_commit_sha": "d1bfdd544b54f34f293a7a8dad67d7f8c56511c7",
  "baseline_manifest_blob_sha": "6e05c33c3df07a42ee5b7e695e3b528f9866d342",
  "application_head_sha": "492206f4703c9a1e5dc84fca40516cc438ca3352",
  "added_paths": [],
  "added_active_paths": [
    "tests/test_intelligence_prerun_service.py",
    "tests/test_intelligence_context_ingress_api.py"
  ],
  "owner_scope_decision": {
    "id": "DECISION-FC20-12-F01A-REVIEW-OVERLAY-MAINTENANCE-REGISTRATION-2026-10-16",
    "record_url": "https://github.com/alphasigma13579-lang/ASIE/pull/189#issuecomment-6215466332",
    "recorded_at": "2026-10-16T12:23:15.105926+00:00",
    "effect": "PREPARE_AND_PUBLISH_GOVERNANCE_DRAFT_ONLY_NO_MERGE_NO_RESUME",
    "subject": {
      "baseline_commit_sha": "d1bfdd544b54f34f293a7a8dad67d7f8c56511c7",
      "baseline_manifest_blob_sha": "6e05c33c3df07a42ee5b7e695e3b528f9866d342",
      "application_head_sha": "492206f4703c9a1e5dc84fca40516cc438ca3352",
      "previous_resume_event_index": 21,
      "previous_resume_sha256": "c4352c0e3e26d25b89d0c7854d31129427647fdd6da1f5838b94b66d623c4313",
      "digest_serialization": "UTF8_JSON_ENSURE_ASCII_FALSE_SORT_KEYS_TRUE_COMPACT_SEPARATORS_COMMA_COLON",
      "repair_scope": {
        "kind": "PRESERVED_DATASET_PROVENANCE_RECOVERY_WITH_REVIEW_OVERLAY_MAINTENANCE",
        "implementation_paths": [
          "backend/asie_local_api.py",
          "backend/workspace.py",
          "backend/workflow.py",
          "backend/dib_api.py",
          "backend/dib_persistence.py",
          "backend/dib_tenant_api.py",
          "backend/dib_http_mounting.py",
          "backend/release_info.py",
          "src/contracts.ts",
          "src/dibApi.ts",
          "src/App.tsx",
          "src/customerLanguage.tsx",
          "src/ASIECompleteSurfaceMount.tsx",
          "src/DIBWorkspace.tsx",
          "src/DIBIntakeItemGovernance.tsx",
          "src/DIBManifestRunReadiness.tsx",
          "registry/asie-canonical-api-output.v1.json",
          "docs/ASIE-CANONICAL-API-OUTPUT-REGISTER-v1.0.0.md",
          "tests/test_customer_language_foundation.py",
          "tests/test_gov_beta_04_server_owned_manifest_chain.py",
          "tests/test_context_recovery_api.py",
          "tests/test_dib_context_recovery.py",
          "tests/test_customer_capability_projection.py",
          "tools/check_context_recovery_browser.py",
          "backend/datasets.py",
          "backend/repository.py",
          "backend/evidence_ledger.py",
          "src/api.ts",
          "tests/test_intelligence_prerun_service.py",
          "tests/test_intelligence_context_ingress_api.py"
        ],
        "preserved_repair_scope_sha256": "53e37b158f8446d29637ff8f47f29b06eeed8ec910cbcdde4f3ac4eb9a1b640f",
        "preserved_execution_scope_sha256": "c74dbd2b30ce1f1ef1dc3fe433c52db64970f97e66e0618d2a829ed50dffbe2a",
        "preserved_contract": "FULL_REGISTERED_28_FILE_DATASET_PROVENANCE_AND_RECOVERY_CONTRACT_UNCHANGED",
        "maintenance_paths": [
          "backend/repository.py",
          "tests/test_intelligence_prerun_service.py",
          "tests/test_intelligence_context_ingress_api.py"
        ],
        "stored_review_boundary": "ONLY_STORED_JSON_DECODE_AND_EXISTING_REVIEWOVERLAY_FIELD_RECONSTRUCTION_INSIDE_EXISTING_APPROVAL_TRANSACTION",
        "caught_errors": [
          "KeyError",
          "TypeError",
          "ValueError"
        ],
        "domain_error": "review_integrity_invalid",
        "http_classification": "EXISTING_LOCALIZED_INVALID_REQUEST_400",
        "unexpected_errors": "UNCHANGED_OUTSIDE_NARROW_BOUNDARY",
        "valid_approval_status": 201,
        "overlay_acceptance_hash_conditions_defaults": "UNCHANGED_NO_NEW_DEFAULTS_NORMALIZATION_OR_VALIDATION",
        "authorization": "EXISTING_SESSION_TENANT_PROJECT_AUTHORIZATION_BEFORE_STORED_REVIEW_DECODE",
        "sqlite_cleanup": "THREE_PRERUN_TEST_CONNECTION_CONTEXTS_CLOSING_PLUS_EXISTING_TRANSACTION_NO_ASSERTION_REMOVAL",
        "regressions": [
          "DIRECT_AND_AR_EN_HTTP_STORED_CORRUPTION",
          "VALID_201",
          "TENANT_PROJECT_VIEWER_SESSION_DENIAL_BEFORE_DECODE",
          "NO_RECEIPT_RUN_SNAPSHOT_OR_EXISTING_ROW_MUTATION_ON_REJECTION",
          "UNEXPECTED_FAULT_CLASSIFICATION_UNCHANGED"
        ],
        "additional_schema_operations": [],
        "environment": "TEMPORARY_DATABASE_SYNTHETIC_DATA_ONLY_AFTER_REVIEWED_RESUME",
        "live_database_authorized": false,
        "provider_network_deployment_authorized": false,
        "application_pr_merge_authorized": false
      }
    }
  },
  "effect": "REGISTER_BOUNDED_REVIEW_OVERLAY_MAINTENANCE_ONLY_EXECUTION_STOPPED"
}''')
OVERLAY_SCOPE_RECORD = deepcopy(DATASET_RESUME_RECORD)
OVERLAY_SCOPE_RECORD["execution_authorized"] = False
OVERLAY_SCOPE_RECORD["events"].extend([deepcopy(OVERLAY_STOP_EVENT), deepcopy(OVERLAY_SCOPE_EVENT)])
OVERLAY_VIEW_PREFIX_BLOBS = json.loads(r'''{
  "docs/FOUNDATION-COMPLETE-20-CORE-INTELLIGENCE-COMPLETION-PROGRAM-2026-07-29.md": "bd7748e35f8b11ae0cc44b430af634e9aa3392a9",
  "docs/EKB/FOUNDATION-COMPLETE-20-PACKAGE-INDEX.md": "6882cdaa44dfc293419f220b5f8f5e5c35c64b27",
  "docs/ASIE-BETA-EXECUTION-MASTER-PLAN-2026-09-09.md": "96078451fa326aab39be1faa11838ed3bcf9a282",
  "docs/FC20-12-F01A-DEFENSIVE-ENABLING-REGISTRATION-PROPOSAL-2026-10-01.md": "6a4529185c7cbb44bbb4f38a3c59f189e40623c5",
  "docs/FC20-12-F01A-APPROVAL-CONSUMPTION-SCOPE-REGISTRATION-2026-10-09.md": "6e5bd88e1ee0f4f117c485754a8a03171dc1bee4"
}''')
OVERLAY_VIEW_SHA256 = json.loads(r'''{
  "docs/FOUNDATION-COMPLETE-20-CORE-INTELLIGENCE-COMPLETION-PROGRAM-2026-07-29.md": "6d11962db122b497df9a2a302846f3d9b26e21edd7e87b7786ad62fcd5f8e129",
  "docs/EKB/FOUNDATION-COMPLETE-20-PACKAGE-INDEX.md": "164a4f6606ce3f259baaa74ace58b6b08f36f9a8364b4c1f2ef36efc8eee15ff",
  "docs/ASIE-BETA-EXECUTION-MASTER-PLAN-2026-09-09.md": "374be4d6befb41cabc65007e7bdb0412d87f3ae0aca9b4eb72e9b982b991497d",
  "docs/FC20-12-F01A-DEFENSIVE-ENABLING-REGISTRATION-PROPOSAL-2026-10-01.md": "0a719dd6c0a59e405612afdf0a2b25eed3f34bbfe5937da96d979efa217001de",
  "docs/FC20-12-F01A-APPROVAL-CONSUMPTION-SCOPE-REGISTRATION-2026-10-09.md": "1f1f2e772f42dbc08897114df74540dc48f703a8406487e26c41738a617db64f"
}''')
OVERLAY_VIEW_MARKER = '<!-- F01A-REVIEW-OVERLAY-MAINTENANCE-SCOPE-2026-10-16 -->'
OVERLAY_MANIFEST_BLOB = 'e486be15c60a576e75a1cc24cdb39fd174d8aaa0'

@lru_cache(maxsize=2, typed=True)
def _overlay_scope_cached_blob_sha(raw: bytes) -> str:
    """OMSG-08: isolate the new layer's two immutable digests from historical caches."""
    return git_blob_sha(raw)


def overlay_scope_blob_sha(raw: bytes) -> str:
    """OMSG-08: preserve strict original byte typing before pure content memoization."""
    if type(raw) is not bytes:
        raise TypeError("overlay_scope_digest_requires_exact_bytes")
    return _overlay_scope_cached_blob_sha(raw)




def overlay_scope_digest(value: object) -> str:
    """OMSG-01: one explicit typed canonical representation for new history references."""
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _validate_overlay_scope_structure(record: dict, active_target: object) -> None:
    """OMSG-01/02: independent closed typed scope, exact history and stopped authority."""
    assert isinstance(record, dict), "invalid_defensive_record"
    assert set(record) == set(OVERLAY_SCOPE_RECORD), "defensive_fields"
    if record != OVERLAY_SCOPE_RECORD:
        raise AssertionError("defensive_record_mismatch")
    if json.dumps(record, sort_keys=True) != json.dumps(OVERLAY_SCOPE_RECORD, sort_keys=True):
        raise AssertionError("overlay_scope_literal_types")
    assert record["execution_authorized"] is False, "overlay_scope_stopped"
    assert active_target == DEFENSIVE_START_TARGET, "overlay_scope_slot"
    assert len(record["events"]) == 24, "overlay_scope_events"
    assert record["allowed_paths"][:35] == DATASET_RESUME_RECORD["allowed_paths"], "overlay_scope_prior_paths"
    assert len(record["allowed_paths"]) == len(set(record["allowed_paths"])) == 35, "overlay_scope_union"
    subject = record["events"][23]["owner_scope_decision"]["subject"]
    assert subject["previous_resume_sha256"] == overlay_scope_digest(DATASET_RESUME_EVENT), "overlay_scope_resume_reference"
    assert subject["previous_resume_sha256"] == overlay_scope_digest(record["events"][21]), "overlay_scope_history_binding"
    scope = subject["repair_scope"]
    assert scope["preserved_repair_scope_sha256"] == overlay_scope_digest(DATASET_REPAIR_SCOPE), "overlay_scope_recovery_contract"
    assert scope["implementation_paths"][:28] == DATASET_RESUME_EXECUTION_SCOPE["implementation_paths"], "overlay_scope_active_recovery"
    assert scope["preserved_execution_scope_sha256"] == overlay_scope_digest(DATASET_RESUME_EXECUTION_SCOPE), "overlay_scope_execution_contract"
    assert record["allowed_paths"] == DATASET_RESUME_RECORD["allowed_paths"], "overlay_scope_history_union_unchanged"
    assert record["events"][23]["added_paths"] == [], "overlay_scope_no_cumulative_paths"
    assert scope["implementation_paths"][28:] == record["events"][23]["added_active_paths"], "overlay_scope_active_delta"
    assert len(scope["implementation_paths"]) == 30, "overlay_scope_active_paths"
    assert record["allowed_schema_operations"] == [INDEX_OPERATION], "overlay_scope_schema"
    assert record["allowed_schema_operations"][0]["unique"] is False, "overlay_scope_schema_literal"


def validate_overlay_scope(record: dict, active_target: object) -> None:
    """OMSG-03: admit only the actual bounded preparation/publication receipt."""
    _validate_overlay_scope_structure(record, active_target)
    decision = record["events"][23]["owner_scope_decision"]
    assert decision["record_url"] == "https://github.com/alphasigma13579-lang/ASIE/pull/189#issuecomment-6215466332", "overlay_scope_receipt_missing"
    assert decision["recorded_at"] == "2026-10-16T12:23:15.105926+00:00", "overlay_scope_receipt_time"
    assert decision["effect"] == "PREPARE_AND_PUBLISH_GOVERNANCE_DRAFT_ONLY_NO_MERGE_NO_RESUME", "overlay_scope_no_execution_authority"


def _overlay_scope_historical_inverse(manifest: dict) -> dict:
    """OMSG-04: exact full twenty-two-event baseline with a fresh detached return value."""
    original = defensive_record(manifest)
    _validate_overlay_scope_structure(original, manifest["execution_sequence"]["active_target"])
    restored = dict(manifest); restored["packages"] = list(manifest["packages"])
    index = next(i for i, p in enumerate(manifest["packages"]) if p["id"] == "FC20-12")
    package = dict(manifest["packages"][index]); restored["packages"][index] = package
    package["execution_slices"] = list(package["execution_slices"])
    record = dict(original); package["execution_slices"][1] = record
    record["events"] = list(original["events"][:22]); record["allowed_paths"] = list(original["allowed_paths"][:35]); record["execution_authorized"] = True
    raw = (json.dumps(restored, ensure_ascii=False, indent=2) + "\n").encode()
    assert overlay_scope_blob_sha(raw) == "6e05c33c3df07a42ee5b7e695e3b528f9866d342", "overlay_scope_baseline_mismatch"
    detached = json.loads(raw)
    validate_dataset_resume(defensive_record(detached), detached["execution_sequence"]["active_target"])
    return detached


def validate_overlay_scope_baseline(manifest: dict) -> dict:
    """OMSG-03/04: public inverse requires the current receipt before historical checks."""
    validate_overlay_scope(defensive_record(manifest), manifest["execution_sequence"]["active_target"])
    return _overlay_scope_historical_inverse(manifest)


_OVERLAY_HISTORY_BYTES: tuple[bytes, bytes] | None = None


def overlay_scope_historical_source_bytes() -> bytes:
    """OMSG-08: pin each actual read; cache immutable bytes only after exact inverse."""
    global _OVERLAY_HISTORY_BYTES
    source = overlay_resume_historical_source_bytes()
    if type(_OVERLAY_HISTORY_BYTES) is tuple and len(_OVERLAY_HISTORY_BYTES) == 2:
        cached_source = _OVERLAY_HISTORY_BYTES[0]
        if type(source) is bytes and type(cached_source) is bytes and source == cached_source:
            source = cached_source
    assert overlay_scope_blob_sha(source) == OVERLAY_MANIFEST_BLOB, "overlay_scope_fixture_source_changed"
    if _OVERLAY_HISTORY_BYTES is None:
        baseline = _overlay_scope_historical_inverse(json.loads(source.decode("utf-8")))
        raw = (json.dumps(baseline, ensure_ascii=False, indent=2) + "\n").encode()
        assert overlay_scope_blob_sha(raw) == "6e05c33c3df07a42ee5b7e695e3b528f9866d342", "overlay_scope_fixture_baseline_changed"
        _OVERLAY_HISTORY_BYTES = (source, raw)
    assert type(_OVERLAY_HISTORY_BYTES) is tuple and len(_OVERLAY_HISTORY_BYTES) == 2, "overlay_scope_fixture_cache_shape"
    cached_source, raw = _OVERLAY_HISTORY_BYTES
    assert type(cached_source) is bytes and type(raw) is bytes, "overlay_scope_fixture_cache_type"
    source_matches = source == cached_source
    assert source_matches, "overlay_scope_fixture_cache_source_changed"
    assert overlay_scope_blob_sha(raw) == "6e05c33c3df07a42ee5b7e695e3b528f9866d342", "overlay_scope_fixture_baseline_changed"
    return raw


def historical_dataset_resume_manifest() -> dict:
    """OMSG-08: never share mutable dictionaries or lists between historical cases."""
    return json.loads(overlay_scope_historical_source_bytes())


def overlay_scope_historical_view(source_bytes: bytes, relative_path: str) -> bytes:
    """OMSG-05: path-specific complete prefix and section seals before historical view."""
    assert type(source_bytes) is bytes, "overlay_scope_view_bytes"
    assert relative_path in OVERLAY_VIEW_SHA256, "overlay_scope_view_path"
    marker = OVERLAY_VIEW_MARKER.encode(); separator = b"\n" + marker + b"\n"
    assert source_bytes.count(marker) == source_bytes.count(separator) == 1, "overlay_scope_view_boundary"
    prefix, section = source_bytes.split(separator, 1)
    assert git_blob_sha(prefix) == OVERLAY_VIEW_PREFIX_BLOBS[relative_path], "overlay_scope_view_prefix_changed"
    assert hashlib.sha256(marker + b"\n" + section).hexdigest() == OVERLAY_VIEW_SHA256[relative_path], "overlay_scope_view_section_changed"
    dataset_resume_historical_view(prefix, relative_path)
    return prefix


def test_overlay_scope_current_admission_full_inverse_and_history() -> None:
    """OMSG-01/04: stopped registration and all prior independent validators survive."""
    manifest = historical_overlay_scope_manifest(); before = json.dumps(manifest, sort_keys=True)
    validate_routing_registration(load_manifest()); validate_execution_sequence(load_manifest())
    prior = validate_overlay_scope_baseline(manifest)
    assert json.dumps(manifest, sort_keys=True) == before
    assert len(defensive_record(prior)["events"]) == 22
    scope = validate_dataset_resume_baseline(prior)
    recovery = validate_dataset_scope_baseline(scope)
    stopped_recovery = validate_recovery_resume_baseline(recovery)
    key_resume = validate_recovery_scope_baseline(stopped_recovery)
    key_scope = validate_key_binding_resume_baseline(key_resume)
    review_resume = validate_key_binding_scope_baseline(key_scope)
    review_scope = validate_review_identity_resume_baseline(review_resume)
    index_resume = validate_review_identity_scope_baseline(review_scope)
    index_scope = validate_index_resume_baseline(index_resume)
    consumption_resume = validate_index_scope_baseline(index_scope)
    consumption_scope = validate_consumption_resume_baseline(consumption_resume)
    old = validate_consumption_scope_baseline(consumption_scope)
    validate_scope_extension_baseline(validate_resume_baseline(old))


@pytest.mark.parametrize("event_index,path", [(i, tuple(p)) for i, event in ((22, OVERLAY_STOP_EVENT), (23, OVERLAY_SCOPE_EVENT)) for p in index_resume_leaf_paths(event)])
def test_overlay_scope_pins_each_new_leaf(event_index: int, path: tuple) -> None:
    """OMSG-06: every new scalar is pinned without re-expanding historical matrices."""
    record = deepcopy(OVERLAY_SCOPE_RECORD); target = record["events"][event_index]
    for key in path[:-1]: target = target[key]
    target[path[-1]] = "UNREVIEWED"
    with pytest.raises(AssertionError): validate_overlay_scope(record, DEFENSIVE_START_TARGET)


@pytest.mark.parametrize("path", [(), ("events",22), ("events",22,"evidence"), ("events",23), ("events",23,"owner_scope_decision"), ("events",23,"owner_scope_decision","subject"), ("events",23,"owner_scope_decision","subject","repair_scope")])
@pytest.mark.parametrize("mutation", ["missing", "extra"])
def test_overlay_scope_closed_objects(path: tuple, mutation: str) -> None:
    """OMSG-06: missing and additional fields cannot enlarge or dilute authority."""
    record = deepcopy(OVERLAY_SCOPE_RECORD); target = record
    for key in path: target = target[key]
    if mutation == "missing": target.pop(next(iter(target)))
    else: target["unexpected"] = True
    with pytest.raises(AssertionError): validate_overlay_scope(record, DEFENSIVE_START_TARGET)


@pytest.mark.parametrize("event_index", range(22))
def test_overlay_scope_preserves_each_prior_event(event_index: int) -> None:
    """OMSG-02: each historical event remains part of the independently pinned record."""
    record = deepcopy(OVERLAY_SCOPE_RECORD); record["events"][event_index]["type"] = "ALTERED"
    with pytest.raises(AssertionError): validate_overlay_scope(record, DEFENSIVE_START_TARGET)


@pytest.mark.parametrize("path,value", [(("execution_authorized",),0), (("execution_authorized",),True), (("events",23,"owner_scope_decision","subject","previous_resume_event_index"),21.0), (("events",23,"owner_scope_decision","subject","repair_scope","live_database_authorized"),0), (("allowed_schema_operations",0,"unique"),0)])
def test_overlay_scope_rejects_equal_but_wrong_json_types(path: tuple, value: object) -> None:
    """OMSG-02: Python equality never admits bool/int/float substitution."""
    record = deepcopy(OVERLAY_SCOPE_RECORD); target = record
    for key in path[:-1]: target = target[key]
    target[path[-1]] = value
    with pytest.raises(AssertionError): validate_overlay_scope(record, DEFENSIVE_START_TARGET)


@pytest.mark.parametrize("field,value", [("record_url","UNRESOLVED"),("recorded_at","UNRESOLVED"),("effect","F01A_DEFENSIVE_RESUME_ONLY")])
def test_overlay_scope_receipt_denials_reach_current_seams(field: str, value: str) -> None:
    """OMSG-03: all current authority entry points reject reused or absent decisions."""
    manifest = historical_overlay_scope_manifest(); defensive_record(manifest)["events"][23]["owner_scope_decision"][field] = value
    for validator in (validate_overlay_scope_baseline,):
        with pytest.raises(AssertionError): validator(manifest)


@pytest.mark.parametrize("mutation", ["slot","hold","unrelated","schema","paths"])
def test_overlay_scope_inverse_rejects_unrelated_drift_without_mutation(mutation: str) -> None:
    """OMSG-04: the whole baseline, including holds, must be byte-identical."""
    manifest = historical_overlay_scope_manifest(); record = defensive_record(manifest)
    if mutation == "slot": manifest["execution_sequence"]["active_target"] = None
    elif mutation == "hold": manifest["execution_sequence"]["max_active_executions"] = 2
    elif mutation == "unrelated": manifest["program_id"] = "CHANGED"
    elif mutation == "schema": record["allowed_schema_operations"] = []
    else: record["allowed_paths"].append("unapproved.py")
    before = json.dumps(manifest, sort_keys=True)
    with pytest.raises(AssertionError): validate_overlay_scope_baseline(manifest)
    assert json.dumps(manifest, sort_keys=True) == before


@pytest.mark.parametrize("relative_path", tuple(OVERLAY_VIEW_SHA256))
@pytest.mark.parametrize("mutation", ["valid","prefix","section","duplicate","boundary","swap"])
def test_overlay_scope_projection_seals(relative_path: str, mutation: str) -> None:
    """OMSG-05: exact path, old bytes, new section and unique boundary are required."""
    raw = overlay_resume_historical_view(ci_scope_historical_view(ci_resume_historical_view(ci_amend_historical_view((Path(__file__).resolve().parents[1] / relative_path).read_bytes(), relative_path), relative_path), relative_path), relative_path)
    if mutation == "valid":
        assert git_blob_sha(overlay_scope_historical_view(raw, relative_path)) == OVERLAY_VIEW_PREFIX_BLOBS[relative_path]
        return
    separator = ("\n" + OVERLAY_VIEW_MARKER + "\n").encode()
    expected = {
        "prefix": "overlay_scope_view_prefix_changed",
        "section": "overlay_scope_view_section_changed",
        "duplicate": "overlay_scope_view_boundary",
        "boundary": "overlay_scope_view_boundary",
        "swap": "overlay_scope_view_prefix_changed",
    }[mutation]
    if mutation == "prefix":
        raw = b" " + raw
    elif mutation == "section":
        raw += b" "
    elif mutation == "duplicate":
        raw += OVERLAY_VIEW_MARKER.encode()
    elif mutation == "boundary":
        # Keep every prefix byte, but invalidate the newline after the marker.
        raw = raw.replace(separator, b"\n" + OVERLAY_VIEW_MARKER.encode() + b"\r\n", 1)
    else:
        relative_path = next(p for p in OVERLAY_VIEW_SHA256 if p != relative_path)
    with pytest.raises(AssertionError, match=rf"^{expected}(?:\n|$)"):
        overlay_scope_historical_view(raw, relative_path)


def test_overlay_scope_history_equivalence_detachment_and_nonmutation(monkeypatch: pytest.MonkeyPatch) -> None:
    """OMSG-08: cold/warm immutable cache matches direct inverse with no aliases."""
    monkeypatch.setitem(globals(), "_OVERLAY_HISTORY_BYTES", None)
    original = validate_overlay_scope_baseline(historical_overlay_scope_manifest())
    first, second = historical_dataset_resume_manifest(), historical_dataset_resume_manifest()
    assert json.dumps(first, sort_keys=True) == json.dumps(original, sort_keys=True) == json.dumps(second, sort_keys=True)
    def ids(v: object) -> set[int]:
        if isinstance(v,dict): return {id(v)}.union(*(ids(x) for x in v.values()))
        if isinstance(v,list): return {id(v)}.union(*(ids(x) for x in v))
        return set()
    assert ids(first).isdisjoint(ids(second)) and ids(first).isdisjoint(ids(DATASET_RESUME_RECORD))
    defensive_record(first)["events"][0]["type"] = "MUTATED"
    assert json.dumps(historical_dataset_resume_manifest(), sort_keys=True) == json.dumps(original, sort_keys=True)


@pytest.mark.parametrize("warm", [False,True])
@pytest.mark.parametrize("mutation", ["bytes","type","history","receipt","scope","unrelated"])
def test_overlay_scope_history_original_optimized_rejection(monkeypatch: pytest.MonkeyPatch, warm: bool, mutation: str) -> None:
    """OMSG-08: no cold or warm source change can inherit cached admission."""
    monkeypatch.setitem(globals(), "_OVERLAY_HISTORY_BYTES", None); manifest = historical_overlay_scope_manifest()
    if warm: historical_dataset_resume_manifest()
    cache = _OVERLAY_HISTORY_BYTES; record = defensive_record(manifest)
    if mutation == "type": record["execution_authorized"] = 0
    elif mutation == "history": record["events"][0]["type"] = "CHANGED"
    elif mutation == "receipt": record["events"][23]["owner_scope_decision"]["record_url"] = "UNRESOLVED"
    elif mutation == "scope": record["allowed_paths"].append("unapproved.py")
    elif mutation == "unrelated": manifest["program_id"] = "CHANGED"
    raw = (json.dumps(manifest,ensure_ascii=False,indent=2)+"\n").encode()
    if mutation == "bytes": raw += b"\n"
    monkeypatch.setattr(Path,"read_bytes",lambda _path:raw)
    monkeypatch.setitem(globals(),"overlay_resume_historical_source_bytes",lambda:raw)
    with pytest.raises(AssertionError): _overlay_scope_historical_inverse(load_manifest())
    with pytest.raises(AssertionError,match="overlay_scope_fixture_source_changed"): historical_dataset_resume_manifest()
    assert _OVERLAY_HISTORY_BYTES is cache


@pytest.mark.parametrize("mutation", ["source","baseline","type","shape"])
def test_overlay_scope_history_poisoned_cache(monkeypatch: pytest.MonkeyPatch, mutation: str) -> None:
    """OMSG-08: poisoned cache storage is independently rejected on every read."""
    monkeypatch.setitem(globals(),"_OVERLAY_HISTORY_BYTES",None); historical_dataset_resume_manifest(); source,baseline = _OVERLAY_HISTORY_BYTES
    poison = (source+b" ",baseline) if mutation=="source" else (source,baseline+b" ") if mutation=="baseline" else (source,{}) if mutation=="type" else (source,)
    monkeypatch.setitem(globals(),"_OVERLAY_HISTORY_BYTES",poison)
    with pytest.raises(AssertionError): historical_dataset_resume_manifest()


def test_overlay_scope_history_single_read_and_failed_initialization(monkeypatch: pytest.MonkeyPatch) -> None:
    """OMSG-08: inverse uses exactly the verified read and never caches failed work."""
    monkeypatch.setitem(globals(),"_OVERLAY_HISTORY_BYTES",None); raw=overlay_resume_historical_source_bytes(); reads=[]; original=_overlay_scope_historical_inverse; calls=[]
    def alternating() -> bytes:
        reads.append(True); return raw if len(reads)==1 else raw+b"\n"
    def checked(m: dict) -> dict:
        calls.append(True); return original(m)
    monkeypatch.setitem(globals(),"overlay_resume_historical_source_bytes",alternating); monkeypatch.setitem(globals(),"_overlay_scope_historical_inverse",checked)
    historical_dataset_resume_manifest(); assert len(reads)==len(calls)==1
    with pytest.raises(AssertionError): historical_dataset_resume_manifest()
    assert len(reads)==2 and len(calls)==1
    monkeypatch.setitem(globals(),"_OVERLAY_HISTORY_BYTES",None); monkeypatch.setitem(globals(),"overlay_resume_historical_source_bytes",lambda:raw)
    def failed(_m: dict) -> dict: raise AssertionError("injected_inverse_failure")
    monkeypatch.setitem(globals(),"_overlay_scope_historical_inverse",failed)
    with pytest.raises(AssertionError,match="injected_inverse_failure"): historical_dataset_resume_manifest()
    assert _OVERLAY_HISTORY_BYTES is None


@pytest.mark.parametrize("event_index,field", [(i,f) for i in (15,17,18,20,21) for f in ("record_url","recorded_at","effect")] + [(18,"condition"),(21,"condition")])
def test_overlay_scope_historical_receipt_denials_reach_current_seams(event_index: int, field: str) -> None:
    """OMSG-03: retain historical receipt negatives at today's routing/slot admission."""
    manifest = historical_overlay_scope_manifest(); event = defensive_record(manifest)["events"][event_index]
    decision = event["owner_scope_decision"] if event_index in (17,20) else event["owner_resume_decision"]
    decision[field] = "UNRESOLVED_OR_REUSED"
    for validator in (validate_overlay_scope_baseline,):
        with pytest.raises(AssertionError): validator(manifest)


def test_overlay_scope_digest_is_exact_bounded_and_independent() -> None:
    """OMSG-08: content equality is sufficient; changed bytes miss and history stays separate."""
    _overlay_scope_cached_blob_sha.cache_clear()
    historical = _recovery_resume_cached_blob_sha.cache_info()
    first = b"synthetic-overlay-digest"; equal = bytes(bytearray(first))
    assert first == equal and first is not equal
    assert overlay_scope_blob_sha(first) == git_blob_sha(first)
    assert overlay_scope_blob_sha(equal) == git_blob_sha(equal)
    assert _overlay_scope_cached_blob_sha.cache_info().hits == 1
    changed = first[:-1] + b"X"
    assert overlay_scope_blob_sha(changed) == git_blob_sha(changed) != git_blob_sha(first)
    overlay_scope_blob_sha(b"third")
    assert _overlay_scope_cached_blob_sha.cache_info().currsize == 2
    misses = _overlay_scope_cached_blob_sha.cache_info().misses
    overlay_scope_blob_sha(first)
    assert _overlay_scope_cached_blob_sha.cache_info().misses == misses + 1
    assert _recovery_resume_cached_blob_sha.cache_info() == historical


def test_overlay_scope_digest_rejects_nonexact_types_before_lookup() -> None:
    """OMSG-08: custom equality, mutable buffers and scalars cannot enter the cache."""
    class PretendBytes(bytes):
        def __eq__(self, other): return True
        __hash__ = bytes.__hash__
    _overlay_scope_cached_blob_sha.cache_clear(); before = _overlay_scope_cached_blob_sha.cache_info()
    for raw in (PretendBytes(b"x"), bytearray(b"x"), memoryview(b"x"), None, "x", 0, False, [], {}):
        with pytest.raises(TypeError, match="overlay_scope_digest_requires_exact_bytes"):
            overlay_scope_blob_sha(raw)
    assert _overlay_scope_cached_blob_sha.cache_info() == before


def test_overlay_scope_digest_failed_calculation_is_not_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    """OMSG-08: cold failures publish no digest and recovery still computes original bytes."""
    _overlay_scope_cached_blob_sha.cache_clear(); original = git_blob_sha
    def failed(raw): raise RuntimeError("synthetic_overlay_digest_failure")
    monkeypatch.setitem(globals(), "git_blob_sha", failed)
    with pytest.raises(RuntimeError, match="synthetic_overlay_digest_failure"):
        overlay_scope_blob_sha(b"fresh")
    assert _overlay_scope_cached_blob_sha.cache_info().currsize == 0
    monkeypatch.setitem(globals(), "git_blob_sha", original)
    assert overlay_scope_blob_sha(b"fresh") == original(b"fresh")
    _overlay_scope_cached_blob_sha.cache_clear()


@pytest.mark.parametrize("warm", (False, True))
def test_overlay_scope_digest_matches_uncached_admission(monkeypatch: pytest.MonkeyPatch, warm: bool) -> None:
    """OMSG-08: the same bytes yield the same detached inverse with and without memoization."""
    monkeypatch.setitem(globals(), "_OVERLAY_HISTORY_BYTES", None)
    _overlay_scope_cached_blob_sha.cache_clear()
    if warm: historical_dataset_resume_manifest()
    optimized = historical_dataset_resume_manifest()
    monkeypatch.setitem(globals(), "_OVERLAY_HISTORY_BYTES", None)
    def uncached(raw: bytes) -> str:
        if type(raw) is not bytes: raise TypeError("overlay_scope_digest_requires_exact_bytes")
        return git_blob_sha(raw)
    monkeypatch.setitem(globals(), "overlay_scope_blob_sha", uncached)
    original = historical_dataset_resume_manifest()
    assert json.dumps(original, sort_keys=True) == json.dumps(optimized, sort_keys=True)
    defensive_record(original)["events"][0]["type"] = "MUTATED_RETURN"
    assert defensive_record(optimized)["events"][0]["type"] != "MUTATED_RETURN"


# OMRG: conditional registered28-file development/testing resume only.
OVERLAY_REPAIR_SCOPE = deepcopy(OVERLAY_SCOPE_EVENT["owner_scope_decision"]["subject"]["repair_scope"])
OVERLAY_RESUME_EXECUTION_SCOPE = json.loads(r'''{
  "kind": "BOUNDED_PRESERVED_RECOVERY_AND_REVIEW_OVERLAY_MAINTENANCE_DEVELOPMENT_TESTING",
  "implementation_paths": [
    "backend/asie_local_api.py",
    "backend/workspace.py",
    "backend/workflow.py",
    "backend/dib_api.py",
    "backend/dib_persistence.py",
    "backend/dib_tenant_api.py",
    "backend/dib_http_mounting.py",
    "backend/release_info.py",
    "src/contracts.ts",
    "src/dibApi.ts",
    "src/App.tsx",
    "src/customerLanguage.tsx",
    "src/ASIECompleteSurfaceMount.tsx",
    "src/DIBWorkspace.tsx",
    "src/DIBIntakeItemGovernance.tsx",
    "src/DIBManifestRunReadiness.tsx",
    "registry/asie-canonical-api-output.v1.json",
    "docs/ASIE-CANONICAL-API-OUTPUT-REGISTER-v1.0.0.md",
    "tests/test_customer_language_foundation.py",
    "tests/test_gov_beta_04_server_owned_manifest_chain.py",
    "tests/test_context_recovery_api.py",
    "tests/test_dib_context_recovery.py",
    "tests/test_customer_capability_projection.py",
    "tools/check_context_recovery_browser.py",
    "backend/datasets.py",
    "backend/repository.py",
    "backend/evidence_ledger.py",
    "src/api.ts",
    "tests/test_intelligence_prerun_service.py",
    "tests/test_intelligence_context_ingress_api.py"
  ],
  "activities": [
    "DEVELOP_REGISTERED_CUSTOMER_DATASET_PROVENANCE_AND_RECOVERY",
    "TEST_REGISTERED_CUSTOMER_DATASET_PROVENANCE_AND_RECOVERY",
    "DEVELOP_REGISTERED_REVIEW_OVERLAY_CLASSIFICATION_AND_SQLITE_TEST_CLEANUP",
    "TEST_REGISTERED_REVIEW_OVERLAY_CLASSIFICATION_AND_SQLITE_TEST_CLEANUP"
  ],
  "repair_scope_sha256": "6e27e8bdb4cc369830af1d045952d52e333941da4f7fcf27c93e4cf9a2179fc8",
  "digest_serialization": "UTF8_JSON_ENSURE_ASCII_FALSE_SORT_KEYS_TRUE_COMPACT_SEPARATORS_COMMA_COLON",
  "database_scope": "DISPOSABLE_TEMPORARY_DATABASES_ONLY",
  "data_scope": "SYNTHETIC_DATA_ONLY",
  "existing_recovery_contract": "PRESERVE_FULL_REGISTERED_28_FILE_DATASET_PROVENANCE_AND_RECOVERY_CONTRACT",
  "customer_policy": "NO_LICENSE_TERMS_PROOF_FOR_AUTHENTICATED_CUSTOMER_OWN_STUDY_MATERIAL",
  "legacy_policy": "NO_EXEMPTION_WITHOUT_VALID_PROVENANCE_NO_AUTOMATIC_BACKFILL",
  "same_owner_reuse": "AUTHORIZED_PROJECTS_WITHIN_SAME_ORGANIZATION",
  "additional_schema_operations": [],
  "live_database_authorized": false,
  "provider_activation_authorized": false,
  "external_network_authorized": false,
  "deployment_authorized": false,
  "application_merge_authorized": false,
  "production_placement_accepted": false,
  "startup_maintenance_recovery_acceptance": "UNKNOWN_NOT_APPROVED",
  "t08": "OPEN",
  "maintenance_contract": "ONLY_REGISTERED_STORED_DECODE_RECONSTRUCTION_CLASSIFICATION_THREE_SQLITE_CLEANUPS_AND_REGRESSIONS",
  "maintenance_paths": [
    "backend/repository.py",
    "tests/test_intelligence_prerun_service.py",
    "tests/test_intelligence_context_ingress_api.py"
  ],
  "preserved_execution_scope_sha256": "c74dbd2b30ce1f1ef1dc3fe433c52db64970f97e66e0618d2a829ed50dffbe2a"
}''')
OVERLAY_RESUME_DECISION = json.loads(r'''{
  "id": "DECISION-FC20-12-F01A-CONDITIONAL-REVIEW-OVERLAY-MAINTENANCE-RESUME-2026-10-16",
  "record_url": "https://github.com/alphasigma13579-lang/ASIE/pull/213#issuecomment-6216673575",
  "recorded_at": "2026-10-16T13:34:09.345253+00:00",
  "effect": "F01A_DEFENSIVE_RESUME_ONLY",
  "condition": "REVIEWED_GOVERNANCE_TRANSITION_MERGED_AFTER_SEPARATE_OWNER_MERGE_APPROVAL",
  "subject": {
    "baseline_commit_sha": "ab08297bdd8c2f880fd119ed60ee8d30869c7570",
    "baseline_manifest_blob_sha": "e486be15c60a576e75a1cc24cdb39fd174d8aaa0",
    "registration_head_sha": "7f79eb99bb7a4c88740ee8fc97673eb84541a1f5",
    "application_head_sha": "492206f4703c9a1e5dc84fca40516cc438ca3352"
  }
}''')
OVERLAY_RESUME_DECISION["subject"].update(checkpoint=deepcopy(OVERLAY_STOP_EVENT), scope_extension=deepcopy(OVERLAY_SCOPE_EVENT), repair_scope=deepcopy(OVERLAY_REPAIR_SCOPE), execution_scope=deepcopy(OVERLAY_RESUME_EXECUTION_SCOPE))
OVERLAY_RESUME_EVENT = json.loads(r'''{
  "type": "RESUME",
  "recorded_at": "2026-10-16T13:35:13Z",
  "baseline_commit_sha": "ab08297bdd8c2f880fd119ed60ee8d30869c7570",
  "baseline_manifest_blob_sha": "e486be15c60a576e75a1cc24cdb39fd174d8aaa0",
  "effect": "F01A_DEFENSIVE_RESUME_ONLY"
}''')
OVERLAY_RESUME_EVENT.update(checkpoint=deepcopy(OVERLAY_STOP_EVENT), scope_extension=deepcopy(OVERLAY_SCOPE_EVENT), owner_resume_decision=deepcopy(OVERLAY_RESUME_DECISION))
OVERLAY_RESUME_RECORD = deepcopy(OVERLAY_SCOPE_RECORD)
OVERLAY_RESUME_RECORD["execution_authorized"] = True
OVERLAY_RESUME_RECORD["events"].append(deepcopy(OVERLAY_RESUME_EVENT))
OVERLAY_RESUME_VIEW_PREFIX_BLOBS = json.loads(r'''{
  "docs/FOUNDATION-COMPLETE-20-CORE-INTELLIGENCE-COMPLETION-PROGRAM-2026-07-29.md": "7e9cef3d6ee4ef1d9ccff6052aa6ff382d62e922",
  "docs/EKB/FOUNDATION-COMPLETE-20-PACKAGE-INDEX.md": "022bd17a8c1e14a28495d15e76d942bc881f64a1",
  "docs/ASIE-BETA-EXECUTION-MASTER-PLAN-2026-09-09.md": "3d90470aa1f5c11ddd321795286229689335824a",
  "docs/FC20-12-F01A-DEFENSIVE-ENABLING-REGISTRATION-PROPOSAL-2026-10-01.md": "5327350e79c7ca6d34d5c8f273cbcd7fd210803c",
  "docs/FC20-12-F01A-APPROVAL-CONSUMPTION-SCOPE-REGISTRATION-2026-10-09.md": "ea54f5eb39340e3648645c752dbfed724f6db007"
}''')
OVERLAY_RESUME_VIEW_SHA256 = json.loads(r'''{
  "docs/FOUNDATION-COMPLETE-20-CORE-INTELLIGENCE-COMPLETION-PROGRAM-2026-07-29.md": "46229a730e0490c88c8c63e6f8867ab5b6456aa223487920d268436e1e4d7e57",
  "docs/EKB/FOUNDATION-COMPLETE-20-PACKAGE-INDEX.md": "c2d7c60539c61920ac8f3a271538e6765d946ef7b84d045ea9c844028f7ba89e",
  "docs/ASIE-BETA-EXECUTION-MASTER-PLAN-2026-09-09.md": "d157c1869dcb3ad9752771d71f5d7cad55fcbb4a2fe353ff2e8e0869e5000b8f",
  "docs/FC20-12-F01A-DEFENSIVE-ENABLING-REGISTRATION-PROPOSAL-2026-10-01.md": "b84be9408ec22bf3ab5a870542297c1246060d39ea02fe99a9dc19b52f810240",
  "docs/FC20-12-F01A-APPROVAL-CONSUMPTION-SCOPE-REGISTRATION-2026-10-09.md": "daa558d7a97311806865916a62f62ee2f5641f22f924884828dc76195cd43fbd"
}''')
OVERLAY_RESUME_VIEW_MARKER = '<!-- F01A-REVIEW-OVERLAY-MAINTENANCE-CONDITIONAL-RESUME-2026-10-16 -->'
OVERLAY_RESUME_MANIFEST_BLOB = 'b67be5e90c4a501acba1d16655561ff0d11074be'

@lru_cache(maxsize=2, typed=True)
def _overlay_resume_cached_blob_sha(raw: bytes) -> str:
    """OMRG-08: isolate the new layer's two immutable digests from historical caches."""
    return git_blob_sha(raw)


def overlay_resume_blob_sha(raw: bytes) -> str:
    """OMRG-08: preserve strict original byte typing before pure content memoization."""
    if type(raw) is not bytes:
        raise TypeError("overlay_resume_digest_requires_exact_bytes")
    return _overlay_resume_cached_blob_sha(raw)






def _validate_overlay_resume_structure(record: dict, active_target: object) -> None:
    """OMRG-01/02: closed typed resume and all pinned history, without receipt admission."""
    assert isinstance(record, dict), "invalid_defensive_record"
    assert set(record) == set(OVERLAY_RESUME_RECORD), "defensive_fields"
    if record != OVERLAY_RESUME_RECORD:
        raise AssertionError("defensive_record_mismatch")
    if json.dumps(record, sort_keys=True) != json.dumps(OVERLAY_RESUME_RECORD, sort_keys=True):
        raise AssertionError("overlay_resume_literal_types")
    assert record["execution_authorized"] is True, "overlay_resume_flag"
    assert active_target == DEFENSIVE_START_TARGET, "overlay_resume_slot"
    assert record["allowed_paths"] == OVERLAY_SCOPE_RECORD["allowed_paths"], "overlay_resume_paths"
    assert record["allowed_schema_operations"] == [INDEX_OPERATION], "overlay_resume_index"
    assert record["allowed_schema_operations"][0]["unique"] is False, "overlay_resume_index_literal"
    event = record["events"][24]
    for target in (event, event["owner_resume_decision"]["subject"]):
        assert target["checkpoint"] == OVERLAY_STOP_EVENT, "overlay_resume_checkpoint"
        assert target["scope_extension"] == OVERLAY_SCOPE_EVENT, "overlay_resume_scope"
    subject = event["owner_resume_decision"]["subject"]
    assert subject["repair_scope"] == OVERLAY_REPAIR_SCOPE, "overlay_resume_repair_scope"
    assert subject["execution_scope"] == OVERLAY_RESUME_EXECUTION_SCOPE, "overlay_resume_execution_scope"


def validate_overlay_resume(record: dict, active_target: object) -> None:
    """OMRG-03: a fresh exact execution decision and its merge condition are mandatory."""
    _validate_overlay_resume_structure(record, active_target)
    decision = record["events"][24]["owner_resume_decision"]
    assert decision["record_url"] == "https://github.com/alphasigma13579-lang/ASIE/pull/213#issuecomment-6216673575", "overlay_resume_execution_decision_missing"
    assert decision["recorded_at"] == "2026-10-16T13:34:09.345253+00:00", "overlay_resume_execution_decision_time"
    assert decision["condition"] == "REVIEWED_GOVERNANCE_TRANSITION_MERGED_AFTER_SEPARATE_OWNER_MERGE_APPROVAL", "overlay_resume_merge_condition"


def _overlay_resume_historical_inverse(manifest: dict) -> dict:
    """OMRG-04: exact detached stopped baseline, never an alternative current authority."""
    original = defensive_record(manifest)
    _validate_overlay_resume_structure(original, manifest["execution_sequence"]["active_target"])
    restored = dict(manifest)
    restored["packages"] = list(manifest["packages"])
    index = next(i for i, p in enumerate(manifest["packages"]) if p["id"] == "FC20-12")
    package = dict(manifest["packages"][index]); restored["packages"][index] = package
    package["execution_slices"] = list(package["execution_slices"])
    record = dict(original); package["execution_slices"][1] = record
    record["events"] = list(original["events"][:24])
    record["execution_authorized"] = False
    raw = (json.dumps(restored, ensure_ascii=False, indent=2) + "\n").encode()
    assert overlay_resume_blob_sha(raw) == "e486be15c60a576e75a1cc24cdb39fd174d8aaa0", "overlay_resume_baseline_mismatch"
    detached = json.loads(raw)
    validate_overlay_scope(defensive_record(detached), detached["execution_sequence"]["active_target"])
    return detached


def validate_overlay_resume_baseline(manifest: dict) -> dict:
    """OMRG-03/04: public inverse first requires the real current execution receipt."""
    validate_overlay_resume(defensive_record(manifest), manifest["execution_sequence"]["active_target"])
    return _overlay_resume_historical_inverse(manifest)


_OVERLAY_RESUME_HISTORY_BYTES: tuple[bytes, bytes] | None = None


def overlay_resume_historical_source_bytes() -> bytes:
    """OMRG-08: re-pin every read and expose only immutable inverse-verified history."""
    global _OVERLAY_RESUME_HISTORY_BYTES
    source = ci_scope_historical_source_bytes()
    if type(_OVERLAY_RESUME_HISTORY_BYTES) is tuple and len(_OVERLAY_RESUME_HISTORY_BYTES) == 2:
        cached_source = _OVERLAY_RESUME_HISTORY_BYTES[0]
        if type(source) is bytes and type(cached_source) is bytes and source == cached_source:
            source = cached_source
    assert overlay_resume_blob_sha(source) == OVERLAY_RESUME_MANIFEST_BLOB, "overlay_resume_fixture_source_changed"
    if _OVERLAY_RESUME_HISTORY_BYTES is None:
        baseline = _overlay_resume_historical_inverse(json.loads(source.decode("utf-8")))
        raw = (json.dumps(baseline, ensure_ascii=False, indent=2) + "\n").encode()
        assert overlay_resume_blob_sha(raw) == "e486be15c60a576e75a1cc24cdb39fd174d8aaa0", "overlay_resume_fixture_baseline_changed"
        _OVERLAY_RESUME_HISTORY_BYTES = (source, raw)
    assert isinstance(_OVERLAY_RESUME_HISTORY_BYTES, tuple) and len(_OVERLAY_RESUME_HISTORY_BYTES) == 2, "overlay_resume_fixture_cache_shape"
    cached_source, raw = _OVERLAY_RESUME_HISTORY_BYTES
    assert type(cached_source) is bytes and type(raw) is bytes, "overlay_resume_fixture_cache_type"
    source_matches = source == cached_source
    assert source_matches, "overlay_resume_fixture_cache_source_changed"
    assert overlay_resume_blob_sha(raw) == "e486be15c60a576e75a1cc24cdb39fd174d8aaa0", "overlay_resume_fixture_baseline_changed"
    return raw


def historical_overlay_scope_manifest() -> dict:
    """Verified twenty-four-event test fixture with fresh detached mutable containers."""
    return json.loads(overlay_resume_historical_source_bytes().decode("utf-8"))


def overlay_resume_historical_view(source_bytes: bytes, relative_path: str) -> bytes:
    """OMRG-05: preserve the exact old prefix and path-specific new terminal section."""
    assert isinstance(source_bytes, bytes), "overlay_resume_view_source_bytes"
    assert relative_path in OVERLAY_RESUME_VIEW_SHA256, "overlay_resume_view_path"
    marker = OVERLAY_RESUME_VIEW_MARKER.encode(); separator = b"\n" + marker + b"\n"
    assert source_bytes.count(marker) == 1, "overlay_resume_view_marker"
    assert source_bytes.count(separator) == 1, "overlay_resume_view_boundary"
    prefix, section = source_bytes.split(separator, 1)
    assert git_blob_sha(prefix) == OVERLAY_RESUME_VIEW_PREFIX_BLOBS[relative_path], "overlay_resume_view_prefix_changed"
    assert hashlib.sha256(marker + b"\n" + section).hexdigest() == OVERLAY_RESUME_VIEW_SHA256[relative_path], "overlay_resume_view_projection_changed"
    overlay_scope_historical_view(prefix, relative_path)
    return prefix


def test_overlay_resume_current_admission_and_complete_inverse() -> None:
    """OMRG-01/03/04: real conditional authority, preserved scope and full history."""
    manifest = historical_overlay_resume_manifest()
    validate_routing_registration(load_manifest())
    record = defensive_record(manifest)
    assert len(record["events"]) == 25 and record["events"][:24] == OVERLAY_SCOPE_RECORD["events"]
    assert len(record["allowed_paths"]) == 35
    assert len(OVERLAY_RESUME_EXECUTION_SCOPE["implementation_paths"]) == 30
    assert OVERLAY_RESUME_EXECUTION_SCOPE["implementation_paths"] == OVERLAY_REPAIR_SCOPE["implementation_paths"]
    scope = validate_overlay_resume_baseline(manifest)
    dataset_resume = validate_overlay_scope_baseline(scope)
    dataset_scope = validate_dataset_resume_baseline(dataset_resume)
    recovery = validate_dataset_scope_baseline(dataset_scope)
    prior = validate_recovery_resume_baseline(recovery)
    key = validate_recovery_scope_baseline(prior)
    stopped = validate_key_binding_resume_baseline(key)
    previous = validate_key_binding_scope_baseline(stopped)
    old_review_scope = validate_review_identity_resume_baseline(previous)
    old_index_resume = validate_review_identity_scope_baseline(old_review_scope)
    index_scope = validate_index_resume_baseline(old_index_resume)
    consumption_resume = validate_index_scope_baseline(index_scope)
    consumption_scope = validate_consumption_resume_baseline(consumption_resume)
    old_resume = validate_consumption_scope_baseline(consumption_scope)
    validate_scope_extension_baseline(validate_resume_baseline(old_resume))


def overlay_resume_new_leaf_paths() -> list[tuple]:
    """OMRG-06: enumerate new decision leaves, leaving sealed history to its own tests."""
    event = deepcopy(OVERLAY_RESUME_EVENT)
    event.pop("checkpoint"); event.pop("scope_extension")
    subject = event["owner_resume_decision"]["subject"]
    subject.pop("checkpoint"); subject.pop("scope_extension"); subject.pop("repair_scope")
    return [tuple(p) for p in index_resume_leaf_paths(event)]


@pytest.mark.parametrize("path", overlay_resume_new_leaf_paths())
def test_overlay_resume_pins_each_new_leaf(path: tuple) -> None:
    """OMRG-06: every new scope, condition and identity scalar is independently pinned."""
    record = deepcopy(OVERLAY_RESUME_RECORD); target = record["events"][24]
    for key in path[:-1]: target = target[key]
    target[path[-1]] = "UNREVIEWED"
    with pytest.raises(AssertionError, match="defensive_record_mismatch"):
        _validate_overlay_resume_structure(record, DEFENSIVE_START_TARGET)


@pytest.mark.parametrize("container", ("event", "decision", "subject", "execution_scope"))
@pytest.mark.parametrize("mutation", ("missing", "extra"))
def test_overlay_resume_closed_objects(container: str, mutation: str) -> None:
    """OMRG-06: no omitted guard or extra activity can enter the closed decision."""
    def select(record: dict) -> dict:
        event = record["events"][24]
        if container == "event": return event
        decision = event["owner_resume_decision"]
        if container == "decision": return decision
        subject = decision["subject"]
        return subject if container == "subject" else subject["execution_scope"]
    for field in select(OVERLAY_RESUME_RECORD):
        record = deepcopy(OVERLAY_RESUME_RECORD); target = select(record)
        if mutation == "missing": target.pop(field)
        else: target["unapproved"] = True
        with pytest.raises(AssertionError, match="defensive_record_mismatch"):
            _validate_overlay_resume_structure(record, DEFENSIVE_START_TARGET)


@pytest.mark.parametrize("event_index", range(24))
def test_overlay_resume_preserves_each_prior_event(event_index: int) -> None:
    """OMRG-02: every prior event is preserved in the exact full-byte inverse."""
    record = deepcopy(OVERLAY_RESUME_RECORD); record["events"][event_index]["type"] = "CHANGED"
    with pytest.raises(AssertionError, match="defensive_record_mismatch"):
        _validate_overlay_resume_structure(record, DEFENSIVE_START_TARGET)


@pytest.mark.parametrize("location", ("event", "subject"))
@pytest.mark.parametrize("field", ("checkpoint", "scope_extension"))
@pytest.mark.parametrize("mutation", ("missing", "type", "literal"))
def test_overlay_resume_preserves_both_checkpoint_scope_copies(location: str, field: str, mutation: str) -> None:
    """OMRG-02: historical copies remain whole and retain strict JSON types."""
    record = deepcopy(OVERLAY_RESUME_RECORD); target = record["events"][24]
    if location == "subject": target = target["owner_resume_decision"]["subject"]
    if mutation == "missing": target.pop(field)
    elif mutation == "type": target[field]["type"] = "CHANGED"
    elif field == "scope_extension":
        target[field]["owner_scope_decision"]["subject"]["repair_scope"]["additional_schema_operations"] = ["UNAPPROVED"]
    else: target[field]["recorded_at"] = False
    with pytest.raises(AssertionError, match="defensive_record_mismatch|overlay_resume_literal_types"):
        _validate_overlay_resume_structure(record, DEFENSIVE_START_TARGET)


@pytest.mark.parametrize("value", (False, 0, 1, None, "true"))
def test_overlay_resume_requires_literal_true(value: object) -> None:
    """OMRG-01: only the exact conditional resume flag is admissible."""
    record = deepcopy(OVERLAY_RESUME_RECORD); record["execution_authorized"] = value
    with pytest.raises(AssertionError, match="defensive_record_mismatch|overlay_resume_literal_types"):
        validate_overlay_resume(record, DEFENSIVE_START_TARGET)


@pytest.mark.parametrize("field,value", (("record_url", "UNRESOLVED_OWNER_EXECUTION_DECISION_RECORD_URL"), ("recorded_at", "UNRESOLVED"), ("condition", "IMMEDIATE"), ("effect", "PREPARE_AND_PUBLISH_GOVERNANCE_DRAFT_ONLY_NO_MERGE_NO_RESUME")))
def test_overlay_resume_missing_or_reused_decision_denied_at_all_current_seams(field: str, value: str) -> None:
    """OMRG-03: preparation permission cannot substitute for conditional execution."""
    manifest = historical_overlay_resume_manifest(); defensive_record(manifest)["events"][24]["owner_resume_decision"][field] = value
    for validator in (validate_overlay_resume_baseline,):
        with pytest.raises(AssertionError, match="defensive_record_mismatch"):
            validator(manifest)


@pytest.mark.parametrize("event_index,field", [(i,f) for i in (15,17,18,20,21,23) for f in ("record_url","recorded_at","effect")] + [(18,"condition"),(21,"condition")])
def test_overlay_resume_prior_receipt_negatives_reach_current_seams(event_index: int, field: str) -> None:
    """OMRG-02/03: preserve prior receipt negatives against a valid current baseline."""
    manifest = historical_overlay_resume_manifest()
    validate_routing_registration(load_manifest())
    event = defensive_record(manifest)["events"][event_index]
    decision = event["owner_scope_decision" if event_index in (17,20,23) else "owner_resume_decision"]
    decision[field] = "UNRESOLVED_OR_CHANGED"
    for validator in (validate_overlay_resume_baseline,):
        with pytest.raises(AssertionError, match="defensive_record_mismatch"):
            validator(manifest)


@pytest.mark.parametrize("mutation", ("scope_union", "paths", "schema", "index_zero", "slot", "hold", "unrelated"))
def test_overlay_resume_denies_scope_slot_and_unrelated_drift_without_mutation(mutation: str) -> None:
    """OMRG-04/06: inverse covers all manifest bytes, not only the changed slice."""
    manifest = historical_overlay_resume_manifest(); record = defensive_record(manifest)
    if mutation == "scope_union": record["events"][24]["owner_resume_decision"]["subject"]["execution_scope"]["implementation_paths"] = list(record["allowed_paths"])
    elif mutation == "paths": record["allowed_paths"].reverse()
    elif mutation == "schema": record["allowed_schema_operations"].append({"operation": "UNAPPROVED"})
    elif mutation == "index_zero": record["allowed_schema_operations"][0]["unique"] = 0
    elif mutation == "slot": manifest["execution_sequence"]["active_target"] = None
    elif mutation == "hold": manifest["execution_sequence"]["held_packages"] = []
    else: manifest["program_id"] = "UNRELATED"
    before = json.dumps(manifest, sort_keys=True)
    with pytest.raises(AssertionError): validate_overlay_resume_baseline(manifest)
    assert json.dumps(manifest, sort_keys=True) == before


@pytest.mark.parametrize("relative_path", tuple(OVERLAY_RESUME_VIEW_SHA256))
@pytest.mark.parametrize("mutation", ("valid", "prefix", "section", "duplicate", "boundary", "swap"))
def test_overlay_resume_projection_exact_seals(relative_path: str, mutation: str) -> None:
    """OMRG-05: exact path-specific terminal bytes preserve all old projections."""
    root = Path(__file__).resolve().parents[1]; source = ci_scope_historical_view(ci_resume_historical_view(ci_amend_historical_view((root / relative_path).read_bytes(), relative_path), relative_path), relative_path)
    separator = ("\n" + OVERLAY_RESUME_VIEW_MARKER + "\n").encode()
    prefix, section = source.split(separator, 1)
    if mutation == "valid":
        assert overlay_resume_historical_view(source, relative_path) == prefix
        return
    if mutation == "prefix": source = b" " + source
    elif mutation == "section": source += b" "
    elif mutation == "duplicate": source += separator
    elif mutation == "boundary": source = prefix + b"\n" + OVERLAY_RESUME_VIEW_MARKER.encode() + b"\r\n" + section
    else:
        other = next(p for p in OVERLAY_RESUME_VIEW_SHA256 if p != relative_path)
        source = prefix + separator + ci_scope_historical_view(ci_resume_historical_view(ci_amend_historical_view((root / other).read_bytes(), other), other), other).split(separator, 1)[1]
    with pytest.raises(AssertionError, match="overlay_resume_view"):
        overlay_resume_historical_view(source, relative_path)


def test_overlay_resume_fixture_cold_warm_equivalence_and_detachment(monkeypatch: pytest.MonkeyPatch) -> None:
    """OMRG-08: optimized history equals direct inverse and never shares mutable state."""
    import sys
    module = sys.modules[__name__]; monkeypatch.setattr(module, "_OVERLAY_RESUME_HISTORY_BYTES", None)
    manifest = historical_overlay_resume_manifest(); original = validate_overlay_resume_baseline(manifest)
    expected = json.dumps(original, ensure_ascii=False, indent=2) + "\n"
    first, second = historical_overlay_scope_manifest(), historical_overlay_scope_manifest()
    assert json.dumps(first, ensure_ascii=False, indent=2) + "\n" == expected
    assert json.dumps(second, ensure_ascii=False, indent=2) + "\n" == expected
    assert isinstance(_OVERLAY_RESUME_HISTORY_BYTES, tuple) and all(isinstance(x, bytes) for x in _OVERLAY_RESUME_HISTORY_BYTES)
    def ids(value: object) -> set[int]:
        if isinstance(value, dict): return {id(value)}.union(*(ids(v) for v in value.values()))
        if isinstance(value, list): return {id(value)}.union(*(ids(v) for v in value))
        return set()
    assert ids(first).isdisjoint(ids(second)) and ids(first).isdisjoint(ids(manifest)) and ids(first).isdisjoint(ids(OVERLAY_SCOPE_RECORD))
    defensive_record(first)["events"][0]["type"] = "CHANGED_RETURN"
    assert json.dumps(historical_overlay_scope_manifest(), ensure_ascii=False, indent=2) + "\n" == expected


@pytest.mark.parametrize("warm", (False, True))
@pytest.mark.parametrize("mutation", ("bytes", "type", "history", "slot", "unrelated", "receipt", "scope"))
def test_overlay_resume_fixture_original_and_optimized_denials(monkeypatch: pytest.MonkeyPatch, warm: bool, mutation: str) -> None:
    """OMRG-08: cold and warm reads cannot reuse approval after any source change."""
    import sys
    module = sys.modules[__name__]; monkeypatch.setattr(module, "_OVERLAY_RESUME_HISTORY_BYTES", None)
    manifest = historical_overlay_resume_manifest()
    if warm: historical_overlay_scope_manifest()
    cache = _OVERLAY_RESUME_HISTORY_BYTES; record = defensive_record(manifest)
    if mutation == "type": record["execution_authorized"] = 1
    elif mutation == "history": record["events"][0]["type"] = "CHANGED"
    elif mutation == "slot": manifest["execution_sequence"]["active_target"] = None
    elif mutation == "unrelated": manifest["program_id"] = "CHANGED"
    elif mutation == "receipt": record["events"][24]["owner_resume_decision"]["record_url"] = "UNRESOLVED"
    elif mutation == "scope": record["allowed_paths"].append("unapproved.py")
    raw = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode()
    if mutation == "bytes": raw += b"\n"
    monkeypatch.setitem(globals(), "ci_scope_historical_source_bytes", lambda: raw)
    with pytest.raises(AssertionError): _overlay_resume_historical_inverse(historical_overlay_resume_manifest())
    with pytest.raises(AssertionError, match="overlay_resume_fixture_source_changed"): historical_overlay_scope_manifest()
    assert _OVERLAY_RESUME_HISTORY_BYTES is cache


@pytest.mark.parametrize("mutation", ("source", "baseline", "type", "shape"))
def test_overlay_resume_fixture_poisoned_cache_rejected(monkeypatch: pytest.MonkeyPatch, mutation: str) -> None:
    """OMRG-08: cache bytes must stay typed and independently pinned on every call."""
    import sys
    module = sys.modules[__name__]; monkeypatch.setattr(module, "_OVERLAY_RESUME_HISTORY_BYTES", None)
    historical_overlay_scope_manifest(); source, baseline = _OVERLAY_RESUME_HISTORY_BYTES
    poisoned = (source+b" ", baseline) if mutation == "source" else (source, baseline+b" ") if mutation == "baseline" else (source, {}) if mutation == "type" else (source,)
    monkeypatch.setattr(module, "_OVERLAY_RESUME_HISTORY_BYTES", poisoned)
    with pytest.raises(AssertionError, match="overlay_resume_fixture_"): historical_overlay_scope_manifest()


def test_overlay_resume_fixture_single_read_and_failed_initialization(monkeypatch: pytest.MonkeyPatch) -> None:
    """OMRG-08: cold inverse consumes the pinned read and failure never publishes cache."""
    import sys
    module = sys.modules[__name__]; monkeypatch.setattr(module, "_OVERLAY_RESUME_HISTORY_BYTES", None)
    raw = ci_scope_historical_source_bytes(); reads = []; calls = []; original = _overlay_resume_historical_inverse
    def alternating() -> bytes:
        reads.append(True)
        return raw if len(reads) == 1 else raw+b"\n"
    def checked(manifest: dict) -> dict:
        calls.append(True)
        return original(manifest)
    monkeypatch.setitem(globals(), "ci_scope_historical_source_bytes", alternating); monkeypatch.setattr(module, "_overlay_resume_historical_inverse", checked)
    historical_overlay_scope_manifest()
    assert len(reads) == len(calls) == 1
    with pytest.raises(AssertionError, match="overlay_resume_fixture_source_changed"): historical_overlay_scope_manifest()
    assert len(reads) == 2 and len(calls) == 1
    monkeypatch.setattr(module, "_OVERLAY_RESUME_HISTORY_BYTES", None)
    monkeypatch.setitem(globals(), "ci_scope_historical_source_bytes", lambda: raw)
    def failed(_manifest: dict) -> dict: raise AssertionError("injected_inverse_failure")
    monkeypatch.setattr(module, "_overlay_resume_historical_inverse", failed)
    with pytest.raises(AssertionError, match="injected_inverse_failure"): historical_overlay_scope_manifest()
    assert _OVERLAY_RESUME_HISTORY_BYTES is None




def test_overlay_resume_digest_is_exact_bounded_and_independent() -> None:
    """OMRG-08: content equality is sufficient; changed bytes miss and history stays separate."""
    _overlay_resume_cached_blob_sha.cache_clear()
    historical = _recovery_resume_cached_blob_sha.cache_info()
    first = b"synthetic-overlay-digest"; equal = bytes(bytearray(first))
    assert first == equal and first is not equal
    assert overlay_resume_blob_sha(first) == git_blob_sha(first)
    assert overlay_resume_blob_sha(equal) == git_blob_sha(equal)
    assert _overlay_resume_cached_blob_sha.cache_info().hits == 1
    changed = first[:-1] + b"X"
    assert overlay_resume_blob_sha(changed) == git_blob_sha(changed) != git_blob_sha(first)
    overlay_resume_blob_sha(b"third")
    assert _overlay_resume_cached_blob_sha.cache_info().currsize == 2
    misses = _overlay_resume_cached_blob_sha.cache_info().misses
    overlay_resume_blob_sha(first)
    assert _overlay_resume_cached_blob_sha.cache_info().misses == misses + 1
    assert _recovery_resume_cached_blob_sha.cache_info() == historical


def test_overlay_resume_digest_rejects_nonexact_types_before_lookup() -> None:
    """OMRG-08: custom equality, mutable buffers and scalars cannot enter the cache."""
    class PretendBytes(bytes):
        def __eq__(self, other): return True
        __hash__ = bytes.__hash__
    _overlay_resume_cached_blob_sha.cache_clear(); before = _overlay_resume_cached_blob_sha.cache_info()
    for raw in (PretendBytes(b"x"), bytearray(b"x"), memoryview(b"x"), None, "x", 0, False, [], {}):
        with pytest.raises(TypeError, match="overlay_resume_digest_requires_exact_bytes"):
            overlay_resume_blob_sha(raw)
    assert _overlay_resume_cached_blob_sha.cache_info() == before


def test_overlay_resume_digest_failed_calculation_is_not_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    """OMRG-08: cold failures publish no digest and recovery still computes original bytes."""
    _overlay_resume_cached_blob_sha.cache_clear(); original = git_blob_sha
    def failed(raw): raise RuntimeError("synthetic_overlay_digest_failure")
    monkeypatch.setitem(globals(), "git_blob_sha", failed)
    with pytest.raises(RuntimeError, match="synthetic_overlay_digest_failure"):
        overlay_resume_blob_sha(b"fresh")
    assert _overlay_resume_cached_blob_sha.cache_info().currsize == 0
    monkeypatch.setitem(globals(), "git_blob_sha", original)
    assert overlay_resume_blob_sha(b"fresh") == original(b"fresh")
    _overlay_resume_cached_blob_sha.cache_clear()


@pytest.mark.parametrize("warm", (False, True))
def test_overlay_resume_digest_matches_uncached_admission(monkeypatch: pytest.MonkeyPatch, warm: bool) -> None:
    """OMRG-08: the same bytes yield the same detached inverse with and without memoization."""
    monkeypatch.setitem(globals(), "_OVERLAY_RESUME_HISTORY_BYTES", None)
    _overlay_resume_cached_blob_sha.cache_clear()
    if warm: historical_overlay_scope_manifest()
    optimized = historical_overlay_scope_manifest()
    monkeypatch.setitem(globals(), "_OVERLAY_RESUME_HISTORY_BYTES", None)
    def uncached(raw: bytes) -> str:
        if type(raw) is not bytes: raise TypeError("overlay_resume_digest_requires_exact_bytes")
        return git_blob_sha(raw)
    monkeypatch.setitem(globals(), "overlay_resume_blob_sha", uncached)
    original = historical_overlay_scope_manifest()
    assert json.dumps(original, sort_keys=True) == json.dumps(optimized, sort_keys=True)
    defensive_record(original)["events"][0]["type"] = "MUTATED_RETURN"
    assert defensive_record(optimized)["events"][0]["type"] != "MUTATED_RETURN"


def test_overlay_resume_identity_reuses_only_fresh_equal_bytes(monkeypatch: pytest.MonkeyPatch) -> None:
    """OMRG-08: every read is checked before reusing an immutable equal source identity."""
    monkeypatch.setitem(globals(), "_OVERLAY_RESUME_HISTORY_BYTES", None)
    historical_overlay_scope_manifest()
    cached, baseline = _OVERLAY_RESUME_HISTORY_BYTES
    reads = []; seen = []; original = overlay_resume_blob_sha
    def fresh():
        value = bytes(bytearray(cached)); reads.append(value)
        return value
    def observe(raw):
        seen.append(raw)
        return original(raw)
    monkeypatch.setitem(globals(), "ci_scope_historical_source_bytes", fresh)
    monkeypatch.setitem(globals(), "overlay_resume_blob_sha", observe)
    assert overlay_resume_historical_source_bytes() == baseline
    assert len(reads) == 1 and reads[0] == cached and reads[0] is not cached
    assert seen[0] is cached and seen[-1] is baseline
    changed = cached[:-1] + b"X"
    monkeypatch.setitem(globals(), "ci_scope_historical_source_bytes", lambda: changed)
    with pytest.raises(AssertionError, match="overlay_resume_fixture_source_changed"):
        overlay_resume_historical_source_bytes()
    assert seen[-1] is changed


@pytest.mark.parametrize("mutation", ("source", "baseline", "type", "shape", "source_type", "source_byte"))
def test_overlay_resume_identity_preserves_original_denial_order(monkeypatch: pytest.MonkeyPatch, mutation: str) -> None:
    """OMRG-08: compare original and identity-fast paths on the same poisoned input."""
    import inspect
    monkeypatch.setitem(globals(), "_OVERLAY_RESUME_HISTORY_BYTES", None)
    historical_overlay_scope_manifest(); source, baseline = _OVERLAY_RESUME_HISTORY_BYTES
    original_text = inspect.getsource(overlay_resume_historical_source_bytes)
    fast_block = '    if type(_OVERLAY_RESUME_HISTORY_BYTES) is tuple and len(_OVERLAY_RESUME_HISTORY_BYTES) == 2:\n        cached_source = _OVERLAY_RESUME_HISTORY_BYTES[0]\n        if type(source) is bytes and type(cached_source) is bytes and source == cached_source:\n            source = cached_source\n'
    assert original_text.count(fast_block) == 1
    namespace = dict(globals()); exec(original_text.replace(fast_block, ""), namespace)
    original = namespace["overlay_resume_historical_source_bytes"]
    fast_namespace = dict(globals()); exec(original_text, fast_namespace)
    fast = fast_namespace["overlay_resume_historical_source_bytes"]
    cache = (source+b" ", baseline) if mutation == "source" else (source, baseline+b" ") if mutation == "baseline" else (source, {}) if mutation == "type" else (source,) if mutation == "shape" else (source, baseline)
    current = bytearray(source) if mutation == "source_type" else source+b" " if mutation == "source_byte" else bytes(bytearray(source))
    monkeypatch.setitem(globals(), "ci_scope_historical_source_bytes", lambda: current)
    monkeypatch.setitem(globals(), "_OVERLAY_RESUME_HISTORY_BYTES", cache)
    namespace["ci_scope_historical_source_bytes"] = lambda: current
    fast_namespace["ci_scope_historical_source_bytes"] = lambda: current
    namespace["_OVERLAY_RESUME_HISTORY_BYTES"] = cache
    fast_namespace["_OVERLAY_RESUME_HISTORY_BYTES"] = cache
    outcomes = []
    for fn in (original, fast):
        try: fn()
        except (AssertionError, TypeError) as exc: outcomes.append((type(exc), str(exc)))
        else: outcomes.append((None, None))
    assert outcomes[0] == outcomes[1] and outcomes[0][0] is not None
    assert _OVERLAY_RESUME_HISTORY_BYTES is cache


# C3C CI registration is preparation only: STOP26/SCOPE27, never resume.
CI_STOP_EVENT = json.loads(r'''{
  "type": "STOP_CHECKPOINT",
  "recorded_at": "2026-10-17T17:26:49.722530+00:00",
  "baseline_commit_sha": "e5e13f672161a283c82634cf8df946d6e90b0aa9",
  "baseline_manifest_blob_sha": "b67be5e90c4a501acba1d16655561ff0d11074be",
  "reason": "C3C_CI_WORKFLOW_AND_GUARD_OUTSIDE_ACTIVE_EXECUTION_SCOPE",
  "evidence": {
    "decision_url": "https://github.com/alphasigma13579-lang/ASIE/blob/fe7d849b1befcabfc49fcefcb66770b1424f32af/ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/docs/ACR-FIN-003-C3C-DETERMINISTIC-2D-SENSITIVITY-DARK-BUILD-2026-08-10.md#قرار-إعداد-ونشر-الحزمة",
    "application_commit_sha": "281f11d7a6d8e9850b1da8a6b6b23ffeb4f51546",
    "ci_run_url": "https://github.com/alphasigma13579-lang/ASIE/actions/runs/39049389874"
  },
  "resume_requirement": "NEW_OWNER_EXECUTION_DECISION_AND_REVIEWED_SCOPE_BOUND_RESUME_MERGED_AFTER_SEPARATE_APPROVAL"
}''')
CI_SCOPE_EVENT = json.loads(r'''{
  "type": "SCOPE_EXTENSION",
  "recorded_at": "2026-10-17T17:26:49.722530+00:00",
  "baseline_commit_sha": "e5e13f672161a283c82634cf8df946d6e90b0aa9",
  "baseline_manifest_blob_sha": "b67be5e90c4a501acba1d16655561ff0d11074be",
  "application_head_sha": "281f11d7a6d8e9850b1da8a6b6b23ffeb4f51546",
  "added_paths": [
    "tests/test_program_close_10_repository_rebaseline.py"
  ],
  "added_repository_root_paths": [
    ".github/workflows/asie-ci.yml"
  ],
  "owner_scope_decision": {
    "id": "DECISION-FC20-12-F01A-C3C-CI-ISOLATION-REGISTRATION-2026-10-17",
    "record_url": "https://github.com/alphasigma13579-lang/ASIE/blob/fe7d849b1befcabfc49fcefcb66770b1424f32af/ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/docs/ACR-FIN-003-C3C-DETERMINISTIC-2D-SENSITIVITY-DARK-BUILD-2026-08-10.md#قرار-إعداد-ونشر-الحزمة",
    "recorded_at": "2026-10-17T17:26:49.722530+00:00",
    "effect": "PREPARE_AND_PUBLISH_ACR_AND_GOVERNANCE_DRAFT_ONLY_NO_MERGE_NO_RESUME",
    "subject": {
      "baseline_commit_sha": "e5e13f672161a283c82634cf8df946d6e90b0aa9",
      "baseline_manifest_blob_sha": "b67be5e90c4a501acba1d16655561ff0d11074be",
      "application_head_sha": "281f11d7a6d8e9850b1da8a6b6b23ffeb4f51546",
      "previous_resume_event_index": 24,
      "previous_resume_sha256": "2d743221c458df6cabe0448ebcea0f4a0824c007bf869e6955f6e5689741d628",
      "digest_serialization": "UTF8_JSON_ENSURE_ASCII_FALSE_SORT_KEYS_TRUE_COMPACT_SEPARATORS_COMMA_COLON",
      "repair_scope": {
        "kind": "PRESERVED_RECOVERY_REVIEW_MAINTENANCE_WITH_BOUNDED_C3C_CI_ISOLATION",
        "implementation_paths": [
          "backend/asie_local_api.py",
          "backend/workspace.py",
          "backend/workflow.py",
          "backend/dib_api.py",
          "backend/dib_persistence.py",
          "backend/dib_tenant_api.py",
          "backend/dib_http_mounting.py",
          "backend/release_info.py",
          "src/contracts.ts",
          "src/dibApi.ts",
          "src/App.tsx",
          "src/customerLanguage.tsx",
          "src/ASIECompleteSurfaceMount.tsx",
          "src/DIBWorkspace.tsx",
          "src/DIBIntakeItemGovernance.tsx",
          "src/DIBManifestRunReadiness.tsx",
          "registry/asie-canonical-api-output.v1.json",
          "docs/ASIE-CANONICAL-API-OUTPUT-REGISTER-v1.0.0.md",
          "tests/test_customer_language_foundation.py",
          "tests/test_gov_beta_04_server_owned_manifest_chain.py",
          "tests/test_context_recovery_api.py",
          "tests/test_dib_context_recovery.py",
          "tests/test_customer_capability_projection.py",
          "tools/check_context_recovery_browser.py",
          "backend/datasets.py",
          "backend/repository.py",
          "backend/evidence_ledger.py",
          "src/api.ts",
          "tests/test_intelligence_prerun_service.py",
          "tests/test_intelligence_context_ingress_api.py",
          "tests/test_program_close_10_repository_rebaseline.py"
        ],
        "repository_root_implementation_paths": [
          ".github/workflows/asie-ci.yml"
        ],
        "preserved_repair_scope_sha256": "6e27e8bdb4cc369830af1d045952d52e333941da4f7fcf27c93e4cf9a2179fc8",
        "preserved_execution_scope_sha256": "f4ec5b54b57829461721a39dc544c74323689e7eaaf129bfa5a8d02f5fb90515",
        "preserved_contract": "FULL_REGISTERED_30_FILE_RECOVERY_PROVENANCE_AND_REVIEW_OVERLAY_CONTRACT_UNCHANGED",
        "maintenance_paths": {
          "package_root": [
            "tests/test_program_close_10_repository_rebaseline.py"
          ],
          "repository_root": [
            ".github/workflows/asie-ci.yml"
          ]
        },
        "activity": "SPLIT_EXISTING_C3C_BENCHMARK_JOB_AND_PRESERVE_FAIL_CLOSED_REQUIRED_AGGREGATE",
        "required_status_context": "Build frontend and test backend",
        "required_status_integration_id": 15368,
        "suite_timeout_minutes": 20,
        "benchmark_job_timeout_minutes": 10,
        "benchmark_step_timeout_minutes": 10,
        "benchmark_command": "python scripts/benchmark_finance_v2_sensitivity.py --warmups 1 --trials 3",
        "same_commit": "EXPLICIT_GITHUB_SHA_CHECKOUT_AND_ACTUAL_GIT_HEAD_OUTPUT_COMPARISON",
        "aggregate": "ALWAYS_NEEDS_BOTH_EXACT_SUCCESS_AND_EXPECTED_SHA_ELSE_NON_SUCCESS",
        "preserve": "ALL_TESTS_COMMANDS_NUMERICAL_CEILINGS_MEMORY_LIMITS_TRIGGERS_CONCURRENCY_READ_ONLY_PERMISSIONS",
        "excluded": [
          "RUNTIME_CHANGES",
          "REJECTED_VALIDATION_OR_FIX",
          "BENCHMARK_SCRIPT_CHANGES",
          "PROTECTION_CHANGES",
          "PAID_RUNNERS",
          "ARTIFACT_CACHE_ADDITIONS",
          "GRAPHIFY_ACTIVATION",
          "APPLICATION_MERGE",
          "LIVE_DATABASE_DEPLOYMENT_PROVIDER"
        ],
        "implementation_authorized": false,
        "environment": "REPOSITORY_CI_SYNTHETIC_ONLY_AFTER_REVIEWED_RESUME",
        "additional_schema_operations": []
      },
      "acr_record": {
        "path": "docs/ACR-FIN-003-C3C-DETERMINISTIC-2D-SENSITIVITY-DARK-BUILD-2026-08-10.md",
        "commit_sha": "fe7d849b1befcabfc49fcefcb66770b1424f32af",
        "blob_sha": "c1db77e3e5baf4cc422cf4c36cba57cef60a9f7c"
      }
    }
  },
  "effect": "REGISTER_BOUNDED_C3C_CI_ISOLATION_ONLY_EXECUTION_STOPPED"
}''')
CI_RECORD_DELTA = json.loads(r'''{
  "execution_authorized": false,
  "allowed_paths": [
    "backend/asie_local_api.py",
    "backend/repository.py",
    "backend/intelligence_prerun_service.py",
    "tests/test_repository_intelligence.py",
    "tests/test_intelligence_prerun_service.py",
    "tests/test_intelligence_context_ingress_api.py",
    "docs/FC20-12-F01-TRUSTED-CONTEXT-INGRESS-REPAIR-PLAN-2026-10-01.md",
    "tests/test_live_location_api.py",
    "tests/test_intelligence_consumption.py",
    "backend/workspace.py",
    "backend/workflow.py",
    "backend/dib_api.py",
    "backend/dib_persistence.py",
    "backend/dib_tenant_api.py",
    "backend/dib_http_mounting.py",
    "backend/release_info.py",
    "src/contracts.ts",
    "src/dibApi.ts",
    "src/App.tsx",
    "src/customerLanguage.tsx",
    "src/ASIECompleteSurfaceMount.tsx",
    "src/DIBWorkspace.tsx",
    "src/DIBIntakeItemGovernance.tsx",
    "src/DIBManifestRunReadiness.tsx",
    "registry/asie-canonical-api-output.v1.json",
    "docs/ASIE-CANONICAL-API-OUTPUT-REGISTER-v1.0.0.md",
    "tests/test_customer_language_foundation.py",
    "tests/test_gov_beta_04_server_owned_manifest_chain.py",
    "tests/test_context_recovery_api.py",
    "tests/test_dib_context_recovery.py",
    "tests/test_customer_capability_projection.py",
    "tools/check_context_recovery_browser.py",
    "backend/datasets.py",
    "backend/evidence_ledger.py",
    "src/api.ts",
    "tests/test_program_close_10_repository_rebaseline.py"
  ],
  "allowed_repository_root_paths": [
    ".github/workflows/asie-ci.yml"
  ]
}''')
CI_VIEW_PREFIX_BLOBS = json.loads(r'''{
  "docs/FOUNDATION-COMPLETE-20-CORE-INTELLIGENCE-COMPLETION-PROGRAM-2026-07-29.md": "4d5cc7c32d2fe651196729109c798bda83feaeba",
  "docs/EKB/FOUNDATION-COMPLETE-20-PACKAGE-INDEX.md": "3c8bd3764583afa053e4ba6d8e9daa863185e8f0",
  "docs/ASIE-BETA-EXECUTION-MASTER-PLAN-2026-09-09.md": "e3e951e4ed050db7fbee37fc6908046b163d854c",
  "docs/FC20-12-F01A-DEFENSIVE-ENABLING-REGISTRATION-PROPOSAL-2026-10-01.md": "7149d57fadb0a52bb9136eb37f95589ea8e8e615",
  "docs/FC20-12-F01A-APPROVAL-CONSUMPTION-SCOPE-REGISTRATION-2026-10-09.md": "226fcff940735cb1f7293592d09b5d6ae4f67c79"
}''')
CI_VIEW_SECTION_SHA256 = json.loads(r'''{
  "docs/FOUNDATION-COMPLETE-20-CORE-INTELLIGENCE-COMPLETION-PROGRAM-2026-07-29.md": "590a59d2cee4937f11ccf9baf13f502b6867dd5b34aff1ef162efd26918df7c1",
  "docs/EKB/FOUNDATION-COMPLETE-20-PACKAGE-INDEX.md": "7d99be7e0084bc1ccb67e5902e69901d41fadc7678852d3d7b401db2b7570c8f",
  "docs/ASIE-BETA-EXECUTION-MASTER-PLAN-2026-09-09.md": "4ba19043137b9071388f5da268cc99ff2f594912abea536042feb88bd9694f5f",
  "docs/FC20-12-F01A-DEFENSIVE-ENABLING-REGISTRATION-PROPOSAL-2026-10-01.md": "24c1021623f20e0e794627b90178f200fae22200c189fde05bed1d9111acad90",
  "docs/FC20-12-F01A-APPROVAL-CONSUMPTION-SCOPE-REGISTRATION-2026-10-09.md": "c1d44c2de0b89f1b54b5b37d3199707fa09722eca82700d77f26510786b0d7cd"
}''')
CI_VIEW_MARKER = '<!-- F01A-C3C-CI-ISOLATION-SCOPE-2026-10-17 -->'
CI_MANIFEST_BLOB = '4eef63fa72b0316383c6112ee92e577514123178'
CI_BASELINE_BLOB = 'b67be5e90c4a501acba1d16655561ff0d11074be'
CI_ACR_PATH = 'docs/ACR-FIN-003-C3C-DETERMINISTIC-2D-SENSITIVITY-DARK-BUILD-2026-08-10.md'
CI_ACR_MARKER = '<!-- C3C-CI-ISOLATION-SCOPE-2026-10-17 -->'
CI_ACR_PREFIX_BLOB = '987aa6209fd2f6eba96adadbc581a23489553e34'
CI_ACR_SECTION_SHA256 = '6cda34c540a8d632d2c3659a160b53dcf9f6661476eb4b31259f2c7008ee7235'
CI_ACR_BLOB = 'c1db77e3e5baf4cc422cf4c36cba57cef60a9f7c'
CI_ACR_COMMIT = 'fe7d849b1befcabfc49fcefcb66770b1424f32af'
CI_DECISION_URL = 'https://github.com/alphasigma13579-lang/ASIE/blob/fe7d849b1befcabfc49fcefcb66770b1424f32af/ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/docs/ACR-FIN-003-C3C-DETERMINISTIC-2D-SENSITIVITY-DARK-BUILD-2026-08-10.md#قرار-إعداد-ونشر-الحزمة'

CI_SCOPE_RECORD = deepcopy(OVERLAY_RESUME_RECORD)
CI_SCOPE_RECORD.update(deepcopy(CI_RECORD_DELTA))
CI_SCOPE_RECORD["events"].extend((deepcopy(CI_STOP_EVENT), deepcopy(CI_SCOPE_EVENT)))
CI_REPAIR_SCOPE = CI_SCOPE_EVENT["owner_scope_decision"]["subject"]["repair_scope"]


def _ci_scope_literal_equal(actual: object, expected: object) -> bool:
    """CISG-01: closed JSON trees preserve types even when Python values compare equal."""
    pending = [(actual, expected)]
    while pending:
        value, oracle = pending.pop()
        if type(value) is not type(oracle): return False
        if type(oracle) is dict:
            if set(value) != set(oracle) or any(type(key) is not str for key in value): return False
            pending.extend((value[key], child) for key, child in oracle.items())
        elif type(oracle) is list:
            if len(value) != len(oracle): return False
            pending.extend(zip(value, oracle))
        elif value != oracle:
            return False
    return True


def _validate_ci_scope_structure(record: dict, active_target: object) -> None:
    """CISG-01/02: STOP26 and SCOPE27 preserve every independently pinned prior event."""
    assert type(record) is dict and set(record) == set(CI_SCOPE_RECORD), "defensive_fields"
    if record != CI_SCOPE_RECORD:
        raise AssertionError("defensive_record_mismatch")
    literal_types_match = _ci_scope_literal_equal(record, CI_SCOPE_RECORD)
    assert literal_types_match, "ci_scope_literal_types"
    assert _ci_scope_literal_equal(active_target, DEFENSIVE_START_TARGET), "ci_scope_counted_slot"
    assert record["execution_authorized"] is False, "ci_scope_execution_stopped"
    assert len(record["events"]) == 27, "ci_scope_event_count"
    assert record["events"][:25] == OVERLAY_RESUME_RECORD["events"], "ci_scope_preserved_history"
    assert record["allowed_paths"] == OVERLAY_RESUME_RECORD["allowed_paths"] + ["tests/test_program_close_10_repository_rebaseline.py"], "ci_scope_package_paths"
    assert record["allowed_repository_root_paths"] == [".github/workflows/asie-ci.yml"], "ci_scope_repository_paths"
    assert record["allowed_schema_operations"] == [INDEX_OPERATION], "ci_scope_schema_preserved"
    assert record["allowed_schema_operations"][0]["unique"] is False, "ci_scope_schema_literal"
    scope = record["events"][26]["owner_scope_decision"]["subject"]["repair_scope"]
    assert scope["implementation_paths"] == OVERLAY_RESUME_EXECUTION_SCOPE["implementation_paths"] + ["tests/test_program_close_10_repository_rebaseline.py"], "ci_scope_active_package_paths"
    assert scope["repository_root_implementation_paths"] == [".github/workflows/asie-ci.yml"], "ci_scope_active_repository_paths"
    assert scope["implementation_authorized"] is False, "ci_scope_preparation_only"
    for paths in (record["allowed_paths"], record["allowed_repository_root_paths"], scope["implementation_paths"], scope["repository_root_implementation_paths"]):
        assert len(paths) == len(set(paths)), "ci_scope_duplicate_path"
        for path in paths:
            assert type(path) is str and path and not path.startswith("/"), "ci_scope_relative_path"
            assert not any(part in ("", ".", "..") for part in path.split("/")), "ci_scope_path_traversal"
            assert not any(char in path for char in ("\\", "*", "?", "[", "]")), "ci_scope_path_wildcard"
    assert not set(record["allowed_paths"]) & set(record["allowed_repository_root_paths"]), "ci_scope_namespace_collision"


def validate_ci_scope(record: dict, active_target: object) -> None:
    """CISG-03: scope-preparation receipt cannot authorize implementation or resume."""
    _validate_ci_scope_structure(record, active_target)
    event = record["events"][26]; decision = event["owner_scope_decision"]
    subject = decision["subject"]
    assert decision["record_url"] == CI_DECISION_URL, "ci_scope_decision_url"
    assert record["events"][25]["evidence"]["decision_url"] == CI_DECISION_URL, "ci_scope_checkpoint_url"
    assert decision["effect"] == "PREPARE_AND_PUBLISH_ACR_AND_GOVERNANCE_DRAFT_ONLY_NO_MERGE_NO_RESUME", "ci_scope_preparation_receipt"
    assert subject["acr_record"] == {"path": CI_ACR_PATH, "commit_sha": CI_ACR_COMMIT, "blob_sha": CI_ACR_BLOB}, "ci_scope_acr_pins"
    prior = json.dumps(record["events"][24], ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    assert hashlib.sha256(prior).hexdigest() == subject["previous_resume_sha256"], "ci_scope_prior_resume_digest"


def _ci_scope_historical_inverse(manifest: dict) -> dict:
    """CISG-04: restore only the declared delta and prove the complete RESUME25 blob."""
    original = defensive_record(manifest)
    _validate_ci_scope_structure(original, manifest["execution_sequence"]["active_target"])
    restored = dict(manifest); restored["packages"] = list(manifest["packages"])
    index = next(i for i, package in enumerate(manifest["packages"]) if package["id"] == "FC20-12")
    package = dict(manifest["packages"][index]); restored["packages"][index] = package
    package["execution_slices"] = list(package["execution_slices"])
    record = dict(original); package["execution_slices"][1] = record
    record["events"] = list(original["events"][:25])
    for field in CI_RECORD_DELTA:
        if field in OVERLAY_RESUME_RECORD: record[field] = deepcopy(OVERLAY_RESUME_RECORD[field])
        else: record.pop(field)
    raw = (json.dumps(restored, ensure_ascii=False, indent=2) + "\n").encode()
    assert ci_scope_blob_sha(raw) == CI_BASELINE_BLOB, "ci_scope_baseline_mismatch"
    detached = json.loads(raw)
    validate_overlay_resume(defensive_record(detached), detached["execution_sequence"]["active_target"])
    return detached


def validate_ci_scope_baseline(manifest: dict) -> dict:
    """CISG-03/04: current receipt admission precedes inverse-only historical access."""
    validate_ci_scope(defensive_record(manifest), manifest["execution_sequence"]["active_target"])
    return _ci_scope_historical_inverse(manifest)


@lru_cache(maxsize=2, typed=True)
def _ci_scope_cached_blob_sha(raw: bytes) -> str:
    """CISG-08: only the current and inverse immutable byte strings are memoized."""
    return git_blob_sha(raw)


def ci_scope_blob_sha(raw: bytes) -> str:
    if type(raw) is not bytes: raise TypeError("ci_scope_digest_requires_exact_bytes")
    return _ci_scope_cached_blob_sha(raw)


_CI_SCOPE_HISTORY_BYTES: tuple[bytes, bytes] | None = None


def ci_scope_historical_source_bytes() -> bytes:
    """CISG-08: every call freshly reads, compares and independently re-pins both bytes."""
    global _CI_SCOPE_HISTORY_BYTES
    source = ci_resume_historical_source_bytes()
    if type(_CI_SCOPE_HISTORY_BYTES) is tuple and len(_CI_SCOPE_HISTORY_BYTES) == 2:
        cached_source = _CI_SCOPE_HISTORY_BYTES[0]
        if type(source) is bytes and type(cached_source) is bytes and source == cached_source:
            source = cached_source
    assert ci_scope_blob_sha(source) == CI_MANIFEST_BLOB, "ci_scope_fixture_source_changed"
    if _CI_SCOPE_HISTORY_BYTES is None:
        baseline = _ci_scope_historical_inverse(json.loads(source.decode("utf-8")))
        raw = (json.dumps(baseline, ensure_ascii=False, indent=2) + "\n").encode()
        assert ci_scope_blob_sha(raw) == CI_BASELINE_BLOB, "ci_scope_fixture_baseline_changed"
        _CI_SCOPE_HISTORY_BYTES = (source, raw)
    assert type(_CI_SCOPE_HISTORY_BYTES) is tuple and len(_CI_SCOPE_HISTORY_BYTES) == 2, "ci_scope_fixture_cache_shape"
    cached_source, raw = _CI_SCOPE_HISTORY_BYTES
    assert type(cached_source) is bytes and type(raw) is bytes, "ci_scope_fixture_cache_type"
    source_matches = source == cached_source
    assert source_matches, "ci_scope_fixture_cache_source_changed"
    assert ci_scope_blob_sha(raw) == CI_BASELINE_BLOB, "ci_scope_fixture_baseline_changed"
    return raw


def historical_overlay_resume_manifest() -> dict:
    """Fresh detached RESUME25 fixture; this is never a current admission entry point."""
    source = ci_scope_historical_source_bytes()
    manifest = json.loads(source)
    source_is_canonical = source == (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode()
    assert source_is_canonical, "manifest_noncanonical_source"
    return manifest


def ci_scope_historical_view(source_bytes: bytes, relative_path: str) -> bytes:
    """CISG-05: five exact append-only projections retain all older view seals."""
    assert type(source_bytes) is bytes, "ci_scope_view_source_bytes"
    assert type(relative_path) is str and relative_path in CI_VIEW_SECTION_SHA256, "ci_scope_view_path"
    marker = CI_VIEW_MARKER.encode(); separator = b"\n" + marker + b"\n"
    assert source_bytes.count(marker) == 1, "ci_scope_view_marker"
    assert source_bytes.count(separator) == 1, "ci_scope_view_boundary"
    prefix, section = source_bytes.split(separator, 1)
    assert git_blob_sha(prefix) == CI_VIEW_PREFIX_BLOBS[relative_path], "ci_scope_view_prefix_changed"
    assert hashlib.sha256(marker + b"\n" + section).hexdigest() == CI_VIEW_SECTION_SHA256[relative_path], "ci_scope_view_section_changed"
    overlay_resume_historical_view(prefix, relative_path)
    return prefix


def ci_scope_acr_historical_view(source_bytes: bytes) -> bytes:
    """CISG-07: ACR prefix, exact appended update and published blob are independent pins."""
    assert type(source_bytes) is bytes, "ci_scope_acr_source_bytes"
    marker = CI_ACR_MARKER.encode(); separator = b"\n" + marker + b"\n"
    assert source_bytes.count(marker) == 1, "ci_scope_acr_marker"
    assert source_bytes.count(separator) == 1, "ci_scope_acr_boundary"
    prefix, section = source_bytes.split(separator, 1)
    assert git_blob_sha(prefix) == CI_ACR_PREFIX_BLOB, "ci_scope_acr_prefix_changed"
    assert hashlib.sha256(marker + b"\n" + section).hexdigest() == CI_ACR_SECTION_SHA256, "ci_scope_acr_update_changed"
    assert git_blob_sha(source_bytes) == CI_ACR_BLOB, "ci_scope_acr_blob_changed"
    return prefix


def test_ci_scope_current_admission_and_full_inverse_chain() -> None:
    """CISG-01/04: 27 stopped events, separate path roots, and every historical oracle."""
    manifest = historical_ci_scope_manifest(); before = json.dumps(manifest, sort_keys=True)
    validate_routing_registration(load_manifest()); validate_execution_sequence(load_manifest())
    record = defensive_record(manifest)
    assert len(record["events"]) == 27 and record["execution_authorized"] is False
    assert len(record["allowed_paths"]) == 36
    assert len(CI_REPAIR_SCOPE["implementation_paths"]) == 31
    assert record["allowed_repository_root_paths"] == [".github/workflows/asie-ci.yml"]
    prior = validate_ci_scope_baseline(manifest)
    assert json.dumps(manifest, sort_keys=True) == before
    assert defensive_record(prior)["events"] == OVERLAY_RESUME_RECORD["events"]
    assert "allowed_repository_root_paths" not in defensive_record(prior)
    assert git_blob_sha((json.dumps(prior, ensure_ascii=False, indent=2) + "\n").encode()) == CI_BASELINE_BLOB
    inverse = prior
    for validator in (validate_overlay_resume_baseline, validate_overlay_scope_baseline, validate_dataset_resume_baseline, validate_dataset_scope_baseline, validate_recovery_resume_baseline, validate_recovery_scope_baseline, validate_key_binding_resume_baseline, validate_key_binding_scope_baseline, validate_review_identity_resume_baseline, validate_review_identity_scope_baseline, validate_index_resume_baseline, validate_index_scope_baseline, validate_consumption_resume_baseline, validate_consumption_scope_baseline, validate_resume_baseline, validate_scope_extension_baseline):
        inverse = validator(inverse)
    with pytest.raises(AssertionError): validate_ci_scope(defensive_record(prior), DEFENSIVE_START_TARGET)


@pytest.mark.parametrize("event_index,path", [(i,tuple(path)) for i,event in ((25,CI_STOP_EVENT),(26,CI_SCOPE_EVENT)) for path in index_resume_leaf_paths(event)])
def test_ci_scope_pins_every_new_leaf(event_index: int, path: tuple) -> None:
    """CISG-06: enumerate only the two new records, never recursively expand old history."""
    record = deepcopy(CI_SCOPE_RECORD); target = record["events"][event_index]
    for key in path[:-1]: target = target[key]
    target[path[-1]] = "UNREVIEWED"
    with pytest.raises(AssertionError): validate_ci_scope(record, DEFENSIVE_START_TARGET)


@pytest.mark.parametrize("path", [(),("events",25),("events",25,"evidence"),("events",26),("events",26,"owner_scope_decision"),("events",26,"owner_scope_decision","subject"),("events",26,"owner_scope_decision","subject","repair_scope"),("events",26,"owner_scope_decision","subject","repair_scope","maintenance_paths"),("events",26,"owner_scope_decision","subject","acr_record")])
@pytest.mark.parametrize("mutation", ("missing","extra"))
def test_ci_scope_closed_objects(path: tuple, mutation: str) -> None:
    record = deepcopy(CI_SCOPE_RECORD); target = record
    for key in path: target = target[key]
    if mutation == "missing": target.pop(next(iter(target)))
    else: target["unapproved"] = True
    with pytest.raises(AssertionError): validate_ci_scope(record, DEFENSIVE_START_TARGET)


@pytest.mark.parametrize("event_index", range(25))
def test_ci_scope_preserves_each_historical_event(event_index: int) -> None:
    record = deepcopy(CI_SCOPE_RECORD); record["events"][event_index]["type"] = "CHANGED"
    with pytest.raises(AssertionError): validate_ci_scope(record, DEFENSIVE_START_TARGET)


@pytest.mark.parametrize("path,value", [(("execution_authorized",),0),(("execution_authorized",),True),(("allowed_schema_operations",0,"unique"),0),(("events",26,"owner_scope_decision","subject","previous_resume_event_index"),24.0),(("events",26,"owner_scope_decision","subject","repair_scope","implementation_authorized"),0),(("events",26,"owner_scope_decision","subject","repair_scope","required_status_integration_id"),15368.0),(("events",26,"owner_scope_decision","subject","repair_scope","suite_timeout_minutes"),20.0),(("events",24,"owner_resume_decision","subject","execution_scope","live_database_authorized"),0)])
def test_ci_scope_equal_but_wrong_json_types(path: tuple, value: object) -> None:
    record = deepcopy(CI_SCOPE_RECORD); target = record
    for key in path[:-1]: target = target[key]
    target[path[-1]] = value
    with pytest.raises(AssertionError, match="ci_scope_literal_types|defensive_record_mismatch"):
        validate_ci_scope(record, DEFENSIVE_START_TARGET)


@pytest.mark.parametrize("field,value", [("record_url","UNRESOLVED"),("recorded_at","UNRESOLVED"),("effect","F01A_DEFENSIVE_RESUME_ONLY"),("record_url",OVERLAY_RESUME_DECISION["record_url"])])
def test_ci_scope_missing_or_reused_receipts_reach_current_seams(field: str, value: str) -> None:
    manifest = historical_ci_scope_manifest(); defensive_record(manifest)["events"][26]["owner_scope_decision"][field] = value
    for validator in (validate_ci_scope_baseline,):
        with pytest.raises(AssertionError): validator(manifest)


@pytest.mark.parametrize("event_index,field", [(i,f) for i in (15,17,18,20,21,23,24) for f in ("record_url","recorded_at","effect")]+[(18,"condition"),(21,"condition"),(24,"condition")])
def test_ci_scope_historical_receipt_negatives_reach_current_seams(event_index: int, field: str) -> None:
    manifest = historical_ci_scope_manifest(); event = defensive_record(manifest)["events"][event_index]
    decision = event["owner_scope_decision" if event_index in (17,20,23) else "owner_resume_decision"]
    decision[field] = "UNRESOLVED_OR_CHANGED"
    for validator in (validate_ci_scope_baseline,):
        with pytest.raises(AssertionError): validator(manifest)


@pytest.mark.parametrize("mutation", ("root_missing","root_extra","root_parent","root_wildcard","root_in_package","package_in_root","historical_union","active_omission","schema","slot","hold","unrelated"))
def test_ci_scope_denies_scope_slot_and_unrelated_drift(mutation: str) -> None:
    manifest = historical_ci_scope_manifest(); record = defensive_record(manifest)
    scope = record["events"][26]["owner_scope_decision"]["subject"]["repair_scope"]
    if mutation == "root_missing": record.pop("allowed_repository_root_paths")
    elif mutation == "root_extra": record["allowed_repository_root_paths"].append(".github/workflows/other.yml")
    elif mutation == "root_parent": record["allowed_repository_root_paths"] = ["../.github/workflows/asie-ci.yml"]
    elif mutation == "root_wildcard": scope["repository_root_implementation_paths"] = [".github/workflows/*"]
    elif mutation == "root_in_package": record["allowed_paths"].append(".github/workflows/asie-ci.yml")
    elif mutation == "package_in_root": record["allowed_repository_root_paths"].append("tests/test_program_close_10_repository_rebaseline.py")
    elif mutation == "historical_union": scope["implementation_paths"] = list(record["allowed_paths"])
    elif mutation == "active_omission": scope["implementation_paths"].pop(0)
    elif mutation == "schema": record["allowed_schema_operations"].append({"operation":"UNAPPROVED"})
    elif mutation == "slot": manifest["execution_sequence"]["active_target"] = None
    elif mutation == "hold": manifest["execution_sequence"]["held_packages"] = []
    else: manifest["program_id"] = "UNRELATED"
    before = json.dumps(manifest, sort_keys=True)
    for validator in (validate_ci_scope_baseline,):
        with pytest.raises(AssertionError): validator(manifest)
    assert json.dumps(manifest, sort_keys=True) == before


@pytest.mark.parametrize("relative_path", tuple(CI_VIEW_SECTION_SHA256))
@pytest.mark.parametrize("mutation", ("valid","prefix","section","duplicate","boundary","swap"))
def test_ci_scope_five_projection_seals(relative_path: str, mutation: str) -> None:
    root = Path(__file__).resolve().parents[1]; source = ci_resume_historical_view(ci_amend_historical_view((root / relative_path).read_bytes(), relative_path), relative_path)
    separator = ("\n" + CI_VIEW_MARKER + "\n").encode(); prefix, section = source.split(separator, 1)
    if mutation == "valid":
        assert ci_scope_historical_view(source, relative_path) == prefix
        return
    if mutation == "prefix": source = b" " + source
    elif mutation == "section": source += b" "
    elif mutation == "duplicate": source += separator
    elif mutation == "boundary": source = prefix + b"\n" + CI_VIEW_MARKER.encode() + b"\r\n" + section
    else:
        other = next(path for path in CI_VIEW_SECTION_SHA256 if path != relative_path)
        source = prefix + separator + ci_resume_historical_view(ci_amend_historical_view((root / other).read_bytes(), other), other).split(separator,1)[1]
    with pytest.raises(AssertionError, match="ci_scope_view"):
        ci_scope_historical_view(source, relative_path)


@pytest.mark.parametrize("value", ("text",bytearray(b"x"),None,0,False))
def test_ci_scope_projection_requires_exact_bytes(value: object) -> None:
    with pytest.raises(AssertionError, match="ci_scope_view_source_bytes"):
        ci_scope_historical_view(value, next(iter(CI_VIEW_SECTION_SHA256)))
    with pytest.raises(AssertionError, match="ci_scope_acr_source_bytes"):
        ci_scope_acr_historical_view(value)


def test_ci_scope_projection_rejects_unknown_path() -> None:
    root = Path(__file__).resolve().parents[1]; path = next(iter(CI_VIEW_SECTION_SHA256))
    raw = ci_resume_historical_view(ci_amend_historical_view((root / path).read_bytes(), path), path)
    for wrong in ("", "../" + path, ".github/workflows/asie-ci.yml", None, False):
        with pytest.raises(AssertionError, match="ci_scope_view_path"): ci_scope_historical_view(raw, wrong)


@pytest.mark.parametrize("mutation", ("valid","prefix","update","duplicate","boundary","missing"))
def test_ci_scope_acr_prefix_and_published_update_pins(mutation: str) -> None:
    source = ci_amend_historical_view((Path(__file__).resolve().parents[1] / CI_ACR_PATH).read_bytes(), CI_ACR_PATH)
    separator = ("\n" + CI_ACR_MARKER + "\n").encode(); prefix, section = source.split(separator,1)
    if mutation == "valid":
        assert ci_scope_acr_historical_view(source) == prefix
        assert CI_SCOPE_EVENT["owner_scope_decision"]["subject"]["acr_record"]["blob_sha"] == CI_ACR_BLOB
        return
    if mutation == "prefix": source = b" " + source
    elif mutation == "update": source += b" "
    elif mutation == "duplicate": source += separator
    elif mutation == "boundary": source = prefix + b"\n" + CI_ACR_MARKER.encode() + b"\r\n" + section
    else: source = prefix + section
    with pytest.raises(AssertionError, match="ci_scope_acr"): ci_scope_acr_historical_view(source)


def test_ci_scope_fixture_cold_warm_equivalence_and_detachment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(globals(), "_CI_SCOPE_HISTORY_BYTES", None)
    manifest = historical_ci_scope_manifest(); original = validate_ci_scope_baseline(manifest)
    first, second = historical_overlay_resume_manifest(), historical_overlay_resume_manifest()
    expected = json.dumps(original, ensure_ascii=False, indent=2) + "\n"
    assert json.dumps(first, ensure_ascii=False, indent=2) + "\n" == expected
    assert json.dumps(second, ensure_ascii=False, indent=2) + "\n" == expected
    def ids(value: object) -> set[int]:
        if type(value) is dict: return {id(value)}.union(*(ids(child) for child in value.values()))
        if type(value) is list: return {id(value)}.union(*(ids(child) for child in value))
        return set()
    assert ids(first).isdisjoint(ids(second)) and ids(first).isdisjoint(ids(manifest)) and ids(first).isdisjoint(ids(OVERLAY_RESUME_RECORD))
    defensive_record(first)["events"][0]["type"] = "MUTATED_RETURN"
    assert json.dumps(historical_overlay_resume_manifest(), ensure_ascii=False, indent=2) + "\n" == expected


@pytest.mark.parametrize("warm", (False,True))
@pytest.mark.parametrize("mutation", ("bytes","literal","history","slot","unrelated","receipt","root"))
def test_ci_scope_fixture_cold_warm_source_denials(monkeypatch: pytest.MonkeyPatch, warm: bool, mutation: str) -> None:
    monkeypatch.setitem(globals(), "_CI_SCOPE_HISTORY_BYTES", None)
    manifest = historical_ci_scope_manifest(); record = defensive_record(manifest)
    if warm: historical_overlay_resume_manifest()
    cache = _CI_SCOPE_HISTORY_BYTES
    if mutation == "literal": record["execution_authorized"] = 0
    elif mutation == "history": record["events"][0]["type"] = "CHANGED"
    elif mutation == "slot": manifest["execution_sequence"]["active_target"] = None
    elif mutation == "unrelated": manifest["program_id"] = "CHANGED"
    elif mutation == "receipt": record["events"][26]["owner_scope_decision"]["record_url"] = "UNRESOLVED"
    elif mutation == "root": record["allowed_repository_root_paths"].append(".github/workflows/*")
    raw = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode()
    if mutation == "bytes": raw += b"\n"
    monkeypatch.setitem(globals(), "ci_resume_historical_source_bytes", lambda: raw)
    if mutation != "bytes":
        with pytest.raises(AssertionError): _ci_scope_historical_inverse(historical_ci_scope_manifest())
    with pytest.raises(AssertionError, match="ci_scope_fixture_source_changed"): historical_overlay_resume_manifest()
    assert _CI_SCOPE_HISTORY_BYTES is cache


@pytest.mark.parametrize("mutation", ("source","baseline","type","shape","source_type"))
def test_ci_scope_fixture_poisoned_cache_rejected(monkeypatch: pytest.MonkeyPatch, mutation: str) -> None:
    monkeypatch.setitem(globals(), "_CI_SCOPE_HISTORY_BYTES", None)
    historical_overlay_resume_manifest(); source, baseline = _CI_SCOPE_HISTORY_BYTES
    poisoned = (source+b" ",baseline) if mutation == "source" else (source,baseline+b" ") if mutation == "baseline" else (source,{}) if mutation == "type" else (source,) if mutation == "shape" else (bytearray(source),baseline)
    monkeypatch.setitem(globals(), "_CI_SCOPE_HISTORY_BYTES", poisoned)
    with pytest.raises(AssertionError, match="ci_scope_fixture_"): historical_overlay_resume_manifest()


def test_ci_scope_fixture_single_read_and_failed_initialization(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(globals(), "_CI_SCOPE_HISTORY_BYTES", None)
    raw = ci_resume_historical_source_bytes(); reads = []; calls = []; original = _ci_scope_historical_inverse
    def alternating() -> bytes:
        reads.append(True)
        return raw if len(reads) == 1 else raw+b"\n"
    def checked(manifest: dict) -> dict:
        calls.append(True); return original(manifest)
    monkeypatch.setitem(globals(), "ci_resume_historical_source_bytes", alternating); monkeypatch.setitem(globals(), "_ci_scope_historical_inverse", checked)
    historical_overlay_resume_manifest(); assert len(reads) == len(calls) == 1
    with pytest.raises(AssertionError, match="ci_scope_fixture_source_changed"): historical_overlay_resume_manifest()
    assert len(reads) == 2 and len(calls) == 1
    monkeypatch.setitem(globals(), "_CI_SCOPE_HISTORY_BYTES", None)
    monkeypatch.setitem(globals(), "ci_resume_historical_source_bytes", lambda: raw)
    def failed(_manifest): raise AssertionError("injected_inverse_failure")
    monkeypatch.setitem(globals(), "_ci_scope_historical_inverse", failed)
    with pytest.raises(AssertionError, match="injected_inverse_failure"): historical_overlay_resume_manifest()
    assert _CI_SCOPE_HISTORY_BYTES is None


def test_ci_scope_digest_exact_bounded_and_independent() -> None:
    _ci_scope_cached_blob_sha.cache_clear(); prior = _overlay_resume_cached_blob_sha.cache_info()
    first = b"synthetic-ci-digest"; equal = bytes(bytearray(first))
    assert equal == first and equal is not first
    assert ci_scope_blob_sha(first) == ci_scope_blob_sha(equal) == git_blob_sha(first)
    assert _ci_scope_cached_blob_sha.cache_info().hits == 1
    changed = first[:-1]+b"X"
    assert ci_scope_blob_sha(changed) == git_blob_sha(changed) != git_blob_sha(first)
    ci_scope_blob_sha(b"third"); assert _ci_scope_cached_blob_sha.cache_info().currsize == 2
    misses = _ci_scope_cached_blob_sha.cache_info().misses; ci_scope_blob_sha(first)
    assert _ci_scope_cached_blob_sha.cache_info().misses == misses + 1
    assert _overlay_resume_cached_blob_sha.cache_info() == prior


def test_ci_scope_digest_rejects_nonexact_types_before_lookup() -> None:
    class PretendBytes(bytes):
        def __eq__(self, other): return True
        __hash__ = bytes.__hash__
    _ci_scope_cached_blob_sha.cache_clear(); before = _ci_scope_cached_blob_sha.cache_info()
    for raw in (PretendBytes(b"x"), bytearray(b"x"), memoryview(b"x"), None, "x", 0, False, [], {}):
        with pytest.raises(TypeError, match="ci_scope_digest_requires_exact_bytes"): ci_scope_blob_sha(raw)
    assert _ci_scope_cached_blob_sha.cache_info() == before


def test_ci_scope_digest_failed_computation_never_publishes(monkeypatch: pytest.MonkeyPatch) -> None:
    _ci_scope_cached_blob_sha.cache_clear(); original = git_blob_sha
    def failed(raw): raise RuntimeError("synthetic_ci_digest_failure")
    monkeypatch.setitem(globals(), "git_blob_sha", failed)
    with pytest.raises(RuntimeError, match="synthetic_ci_digest_failure"): ci_scope_blob_sha(b"fresh")
    assert _ci_scope_cached_blob_sha.cache_info().currsize == 0
    monkeypatch.setitem(globals(), "git_blob_sha", original)
    assert ci_scope_blob_sha(b"fresh") == original(b"fresh")
    _ci_scope_cached_blob_sha.cache_clear()


@pytest.mark.parametrize("warm", (False,True))
def test_ci_scope_cached_and_uncached_inverse_equivalence(monkeypatch: pytest.MonkeyPatch, warm: bool) -> None:
    monkeypatch.setitem(globals(), "_CI_SCOPE_HISTORY_BYTES", None); _ci_scope_cached_blob_sha.cache_clear()
    if warm: historical_overlay_resume_manifest()
    optimized = historical_overlay_resume_manifest()
    monkeypatch.setitem(globals(), "_CI_SCOPE_HISTORY_BYTES", None)
    def uncached(raw):
        if type(raw) is not bytes: raise TypeError("ci_scope_digest_requires_exact_bytes")
        return git_blob_sha(raw)
    monkeypatch.setitem(globals(), "ci_scope_blob_sha", uncached)
    original = historical_overlay_resume_manifest()
    assert json.dumps(original, sort_keys=True) == json.dumps(optimized, sort_keys=True)
    defensive_record(original)["events"][0]["type"] = "CHANGED"
    assert defensive_record(optimized)["events"][0]["type"] != "CHANGED"


def test_ci_scope_identity_reuses_only_fresh_equal_bytes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(globals(), "_CI_SCOPE_HISTORY_BYTES", None)
    historical_overlay_resume_manifest(); cached, baseline = _CI_SCOPE_HISTORY_BYTES
    reads = []; seen = []; original = ci_scope_blob_sha
    def fresh():
        value = bytes(bytearray(cached)); reads.append(value); return value
    def observed(raw):
        seen.append(raw); return original(raw)
    monkeypatch.setitem(globals(), "ci_resume_historical_source_bytes", fresh); monkeypatch.setitem(globals(), "ci_scope_blob_sha", observed)
    assert ci_scope_historical_source_bytes() == baseline
    assert len(reads) == 1 and reads[0] == cached and reads[0] is not cached
    assert seen[0] is cached and seen[-1] is baseline
    changed = cached[:-1]+b"X"; monkeypatch.setitem(globals(), "ci_resume_historical_source_bytes", lambda: changed)
    with pytest.raises(AssertionError, match="ci_scope_fixture_source_changed"): ci_scope_historical_source_bytes()
    assert seen[-1] is changed


@pytest.mark.parametrize("mutation", ("source","baseline","type","shape","source_type","source_byte"))
def test_ci_scope_identity_preserves_original_denial_order(monkeypatch: pytest.MonkeyPatch, mutation: str) -> None:
    import inspect
    monkeypatch.setitem(globals(), "_CI_SCOPE_HISTORY_BYTES", None)
    historical_overlay_resume_manifest(); source, baseline = _CI_SCOPE_HISTORY_BYTES
    original_text = inspect.getsource(ci_scope_historical_source_bytes)
    fast_block = '    if type(_CI_SCOPE_HISTORY_BYTES) is tuple and len(_CI_SCOPE_HISTORY_BYTES) == 2:\n        cached_source = _CI_SCOPE_HISTORY_BYTES[0]\n        if type(source) is bytes and type(cached_source) is bytes and source == cached_source:\n            source = cached_source\n'
    assert original_text.count(fast_block) == 1
    namespace = dict(globals()); exec(original_text.replace(fast_block,""),namespace)
    fast_namespace = dict(globals()); exec(original_text,fast_namespace)
    cache = (source+b" ",baseline) if mutation == "source" else (source,baseline+b" ") if mutation == "baseline" else (source,{}) if mutation == "type" else (source,) if mutation == "shape" else (source,baseline)
    current = bytearray(source) if mutation == "source_type" else source+b" " if mutation == "source_byte" else bytes(bytearray(source))
    monkeypatch.setitem(globals(),"ci_resume_historical_source_bytes",lambda:current)
    monkeypatch.setitem(globals(),"_CI_SCOPE_HISTORY_BYTES",cache)
    namespace["ci_resume_historical_source_bytes"] = lambda: current
    fast_namespace["ci_resume_historical_source_bytes"] = lambda: current
    namespace["_CI_SCOPE_HISTORY_BYTES"] = cache; fast_namespace["_CI_SCOPE_HISTORY_BYTES"] = cache
    outcomes = []
    for fn in (namespace["ci_scope_historical_source_bytes"],fast_namespace["ci_scope_historical_source_bytes"]):
        try: fn()
        except (AssertionError,TypeError) as exc: outcomes.append((type(exc),str(exc)))
        else: outcomes.append((None,None))
    assert outcomes[0] == outcomes[1] and outcomes[0][0] is not None
    assert _CI_SCOPE_HISTORY_BYTES is cache


@pytest.mark.parametrize("mutation", ("record", "literal", "cache_source", "canonical"))
def test_ci_scope_rejections_preserve_bounded_ci_diagnostics(monkeypatch: pytest.MonkeyPatch, mutation: str) -> None:
    """CISG-09: denial types/messages survive CI=true without large relational diffs."""
    import difflib
    monkeypatch.setitem(globals(), "_CI_SCOPE_HISTORY_BYTES", None)
    historical_overlay_resume_manifest(); source, baseline = _CI_SCOPE_HISTORY_BYTES
    record = deepcopy(CI_SCOPE_RECORD); diff_calls = []
    def unexpected_diff(*args, **kwargs):
        diff_calls.append(True); raise RuntimeError("unexpected_ci_scope_relational_diff")
    if mutation == "record":
        record["events"][0]["type"] = "CHANGED"
        invoke = lambda: validate_ci_scope(record, DEFENSIVE_START_TARGET)
        expected = "defensive_record_mismatch"
    elif mutation == "literal":
        record["execution_authorized"] = 0
        invoke = lambda: validate_ci_scope(record, DEFENSIVE_START_TARGET)
        expected = "ci_scope_literal_types"
    elif mutation == "cache_source":
        monkeypatch.setitem(globals(), "_CI_SCOPE_HISTORY_BYTES", (source+b" ", baseline))
        invoke = ci_scope_historical_source_bytes
        expected = "ci_scope_fixture_cache_source_changed"
    else:
        monkeypatch.setitem(globals(), "ci_scope_historical_source_bytes", lambda: baseline+b"\n")
        invoke = historical_overlay_resume_manifest
        expected = "manifest_noncanonical_source"
    outcomes = []
    for ci in ("false", "true"):
        monkeypatch.setenv("CI", ci)
        monkeypatch.setattr(difflib, "ndiff", unexpected_diff)
        try: invoke()
        except AssertionError as exc: outcomes.append((type(exc), str(exc).split("\n",1)[0]))
        else: outcomes.append((None,None))
    assert outcomes == [(AssertionError,expected), (AssertionError,expected)]
    assert not diff_calls, "ci_scope_rejection_constructed_relational_diff"


# CR28: receipt-bound conditional resume; no execution before approved governance merge.
CI_RESUME_EXECUTION_SCOPE = json.loads(r'''{
  "kind": "BOUNDED_PRESERVED_RECOVERY_REVIEW_MAINTENANCE_AND_C3C_CI_ISOLATION_DEVELOPMENT_TESTING",
  "implementation_paths": [
    "backend/asie_local_api.py",
    "backend/workspace.py",
    "backend/workflow.py",
    "backend/dib_api.py",
    "backend/dib_persistence.py",
    "backend/dib_tenant_api.py",
    "backend/dib_http_mounting.py",
    "backend/release_info.py",
    "src/contracts.ts",
    "src/dibApi.ts",
    "src/App.tsx",
    "src/customerLanguage.tsx",
    "src/ASIECompleteSurfaceMount.tsx",
    "src/DIBWorkspace.tsx",
    "src/DIBIntakeItemGovernance.tsx",
    "src/DIBManifestRunReadiness.tsx",
    "registry/asie-canonical-api-output.v1.json",
    "docs/ASIE-CANONICAL-API-OUTPUT-REGISTER-v1.0.0.md",
    "tests/test_customer_language_foundation.py",
    "tests/test_gov_beta_04_server_owned_manifest_chain.py",
    "tests/test_context_recovery_api.py",
    "tests/test_dib_context_recovery.py",
    "tests/test_customer_capability_projection.py",
    "tools/check_context_recovery_browser.py",
    "backend/datasets.py",
    "backend/repository.py",
    "backend/evidence_ledger.py",
    "src/api.ts",
    "tests/test_intelligence_prerun_service.py",
    "tests/test_intelligence_context_ingress_api.py",
    "tests/test_program_close_10_repository_rebaseline.py"
  ],
  "repository_root_implementation_paths": [
    ".github/workflows/asie-ci.yml"
  ],
  "preserved_repair_scope_sha256": "6e27e8bdb4cc369830af1d045952d52e333941da4f7fcf27c93e4cf9a2179fc8",
  "preserved_execution_scope_sha256": "f4ec5b54b57829461721a39dc544c74323689e7eaaf129bfa5a8d02f5fb90515",
  "preserved_contract": "FULL_REGISTERED_30_FILE_RECOVERY_PROVENANCE_AND_REVIEW_OVERLAY_CONTRACT_UNCHANGED",
  "maintenance_paths": {
    "package_root": [
      "tests/test_program_close_10_repository_rebaseline.py"
    ],
    "repository_root": [
      ".github/workflows/asie-ci.yml"
    ]
  },
  "activity": "SPLIT_EXISTING_C3C_BENCHMARK_JOB_AND_PRESERVE_FAIL_CLOSED_REQUIRED_AGGREGATE",
  "required_status_context": "Build frontend and test backend",
  "required_status_integration_id": 15368,
  "suite_timeout_minutes": 20,
  "benchmark_job_timeout_minutes": 10,
  "benchmark_step_timeout_minutes": 10,
  "benchmark_command": "python scripts/benchmark_finance_v2_sensitivity.py --warmups 1 --trials 3",
  "same_commit": "EXPLICIT_GITHUB_SHA_CHECKOUT_AND_ACTUAL_GIT_HEAD_OUTPUT_COMPARISON",
  "aggregate": "ALWAYS_NEEDS_BOTH_EXACT_SUCCESS_AND_EXPECTED_SHA_ELSE_NON_SUCCESS",
  "preserve": "ALL_TESTS_COMMANDS_NUMERICAL_CEILINGS_MEMORY_LIMITS_TRIGGERS_CONCURRENCY_READ_ONLY_PERMISSIONS",
  "excluded": [
    "RUNTIME_CHANGES",
    "REJECTED_VALIDATION_OR_FIX",
    "BENCHMARK_SCRIPT_CHANGES",
    "PROTECTION_CHANGES",
    "PAID_RUNNERS",
    "ARTIFACT_CACHE_ADDITIONS",
    "GRAPHIFY_ACTIVATION",
    "APPLICATION_MERGE",
    "LIVE_DATABASE_DEPLOYMENT_PROVIDER"
  ],
  "implementation_authorized": true,
  "environment": "REPOSITORY_CI_SYNTHETIC_ONLY_AFTER_REVIEWED_RESUME",
  "additional_schema_operations": [],
  "repair_scope_sha256": "1986887c653fc99f9a4e5b6419394b73baddb501c3f3a2827659e5e6f8f20d94",
  "digest_serialization": "UTF8_JSON_ENSURE_ASCII_FALSE_SORT_KEYS_TRUE_COMPACT_SEPARATORS_COMMA_COLON",
  "activities": [
    "DEVELOP_REGISTERED_CUSTOMER_DATASET_PROVENANCE_AND_RECOVERY",
    "TEST_REGISTERED_CUSTOMER_DATASET_PROVENANCE_AND_RECOVERY",
    "DEVELOP_REGISTERED_REVIEW_OVERLAY_CLASSIFICATION_AND_SQLITE_TEST_CLEANUP",
    "TEST_REGISTERED_REVIEW_OVERLAY_CLASSIFICATION_AND_SQLITE_TEST_CLEANUP",
    "DEVELOP_REGISTERED_C3C_CI_ISOLATION",
    "TEST_REGISTERED_C3C_CI_ISOLATION"
  ],
  "database_scope": "DISPOSABLE_TEMPORARY_DATABASES_ONLY",
  "data_scope": "SYNTHETIC_DATA_ONLY",
  "live_database_authorized": false,
  "provider_activation_authorized": false,
  "external_network_authorized": false,
  "deployment_authorized": false,
  "application_merge_authorized": false,
  "production_placement_accepted": false,
  "startup_maintenance_recovery_acceptance": "UNKNOWN_NOT_APPROVED",
  "t08": "OPEN"
}''')
CI_RESUME_DECISION_BASE = json.loads(r'''{
  "id": "DECISION-FC20-12-F01A-CONDITIONAL-C3C-CI-ISOLATION-RESUME-2026-10-18",
  "record_url": "https://github.com/alphasigma13579-lang/ASIE/pull/216#issuecomment-6244578523",
  "recorded_at": "2026-10-18T02:08:40.516851+00:00",
  "effect": "F01A_DEFENSIVE_RESUME_ONLY",
  "condition": "REVIEWED_GOVERNANCE_TRANSITION_MERGED_AFTER_SEPARATE_OWNER_MERGE_APPROVAL",
  "subject": {
    "baseline_commit_sha": "ce8ef8c8882ba5117f9c7f1dfbac34fc50f507af",
    "baseline_manifest_blob_sha": "4eef63fa72b0316383c6112ee92e577514123178",
    "application_head_sha": "281f11d7a6d8e9850b1da8a6b6b23ffeb4f51546",
    "checkpoint_event_index": 25,
    "checkpoint_sha256": "d2693170127b636195b52fe49d50357511d6f84369eaf7fcbe4ecd9959ff2c4d",
    "scope_extension_event_index": 26,
    "scope_extension_sha256": "fceef5c9c2ec639539a54932a11346387e9509e658b9a0d1159e261a66b20b5f",
    "repair_scope_sha256": "1986887c653fc99f9a4e5b6419394b73baddb501c3f3a2827659e5e6f8f20d94",
    "digest_serialization": "UTF8_JSON_ENSURE_ASCII_FALSE_SORT_KEYS_TRUE_COMPACT_SEPARATORS_COMMA_COLON"
  }
}''')
CI_RESUME_EVENT_BASE = json.loads(r'''{
  "type": "RESUME",
  "recorded_at": "2026-10-18T02:09:39Z",
  "baseline_commit_sha": "ce8ef8c8882ba5117f9c7f1dfbac34fc50f507af",
  "baseline_manifest_blob_sha": "4eef63fa72b0316383c6112ee92e577514123178",
  "effect": "F01A_DEFENSIVE_RESUME_ONLY"
}''')
CI_RESUME_VIEW_PREFIX_BLOBS = json.loads(r'''{
  "docs/FOUNDATION-COMPLETE-20-CORE-INTELLIGENCE-COMPLETION-PROGRAM-2026-07-29.md": "0ea82ca28821bf2f2f5647d29e9b7f4fcce9f557",
  "docs/EKB/FOUNDATION-COMPLETE-20-PACKAGE-INDEX.md": "6c032c97ea02a5f3eef3dde6a9952df96e779039",
  "docs/ASIE-BETA-EXECUTION-MASTER-PLAN-2026-09-09.md": "ab0eff1624acf541f73345f55bdfc3a7d43295a4",
  "docs/FC20-12-F01A-DEFENSIVE-ENABLING-REGISTRATION-PROPOSAL-2026-10-01.md": "9126053d02aae9acf5fa1c72b2f528ada6329c82",
  "docs/FC20-12-F01A-APPROVAL-CONSUMPTION-SCOPE-REGISTRATION-2026-10-09.md": "c269c4458473589bc723cfe39c06e9ca30bc9580"
}''')
CI_RESUME_VIEW_SECTION_SHA256 = json.loads(r'''{
  "docs/FOUNDATION-COMPLETE-20-CORE-INTELLIGENCE-COMPLETION-PROGRAM-2026-07-29.md": "9626103bb6fdba31b3312c2c8882bb82d8cd1ac4d6e1284277c81d71c093f7fa",
  "docs/EKB/FOUNDATION-COMPLETE-20-PACKAGE-INDEX.md": "2eb2d4480e9628883d86dd9e5c6cec409274b87a834f188a1b753da76b1478c6",
  "docs/ASIE-BETA-EXECUTION-MASTER-PLAN-2026-09-09.md": "d94eb1a6ec26a79bbf03cb1a055a6f051b8cb9173aa7c4034ac591b4459ae636",
  "docs/FC20-12-F01A-DEFENSIVE-ENABLING-REGISTRATION-PROPOSAL-2026-10-01.md": "479216a7843dc5335d69d940b5d5c192239382742e633e169ef503e25f400d33",
  "docs/FC20-12-F01A-APPROVAL-CONSUMPTION-SCOPE-REGISTRATION-2026-10-09.md": "776d5aa9eabd1d3949f6c280e30f10d23ca20f5fcfa24fb9917c5ff134f8fe44"
}''')
CI_RESUME_VIEW_MARKER = '<!-- F01A-C3C-CI-ISOLATION-CONDITIONAL-RESUME-2026-10-18 -->'
CI_RESUME_BASELINE_BLOB = '4eef63fa72b0316383c6112ee92e577514123178'
CI_RESUME_MANIFEST_BLOB = 'a6e7a4059ad28edbb31b507e51902f538e330a4e'

CI_RESUME_DECISION = deepcopy(CI_RESUME_DECISION_BASE)
CI_RESUME_DECISION["subject"]["execution_scope"] = deepcopy(CI_RESUME_EXECUTION_SCOPE)
CI_RESUME_EVENT = deepcopy(CI_RESUME_EVENT_BASE)
CI_RESUME_EVENT["owner_resume_decision"] = deepcopy(CI_RESUME_DECISION)
CI_RESUME_RECORD = deepcopy(CI_SCOPE_RECORD)
CI_RESUME_RECORD["execution_authorized"] = True
CI_RESUME_RECORD["events"].append(deepcopy(CI_RESUME_EVENT))
CI_RESUME_STOP_SHA256 = "d2693170127b636195b52fe49d50357511d6f84369eaf7fcbe4ecd9959ff2c4d"
CI_RESUME_SCOPE_SHA256 = "fceef5c9c2ec639539a54932a11346387e9509e658b9a0d1159e261a66b20b5f"
CI_RESUME_REPAIR_SHA256 = "1986887c653fc99f9a4e5b6419394b73baddb501c3f3a2827659e5e6f8f20d94"


def _ci_resume_canonical_sha256(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def _validate_ci_resume_structure(record: dict, active_target: object) -> None:
    """CR28-01/02: structural preparation pins history and scope; it grants no authority."""
    assert type(record) is dict and set(record) == set(CI_RESUME_RECORD), "defensive_fields"
    if record != CI_RESUME_RECORD: raise AssertionError("defensive_record_mismatch")
    types_match = _ci_scope_literal_equal(record, CI_RESUME_RECORD)
    assert types_match, "ci_resume_literal_types"
    assert _ci_scope_literal_equal(active_target, DEFENSIVE_START_TARGET), "ci_resume_counted_slot"
    assert record["execution_authorized"] is True, "ci_resume_proposed_flag"
    assert len(record["events"]) == 28, "ci_resume_event_count"
    history_matches = record["events"][:27] == CI_SCOPE_RECORD["events"]
    assert history_matches, "ci_resume_history_changed"
    assert record["allowed_paths"] == CI_SCOPE_RECORD["allowed_paths"], "ci_resume_package_paths"
    assert record["allowed_repository_root_paths"] == [".github/workflows/asie-ci.yml"], "ci_resume_repository_paths"
    assert record["allowed_schema_operations"] == [INDEX_OPERATION], "ci_resume_schema"
    assert record["allowed_schema_operations"][0]["unique"] is False, "ci_resume_schema_literal"
    subject = record["events"][27]["owner_resume_decision"]["subject"]
    assert subject["baseline_commit_sha"] == "ce8ef8c8882ba5117f9c7f1dfbac34fc50f507af", "ci_resume_baseline_commit"
    assert subject["baseline_manifest_blob_sha"] == CI_RESUME_BASELINE_BLOB, "ci_resume_baseline_blob"
    assert type(subject["checkpoint_event_index"]) is int and subject["checkpoint_event_index"] == 25, "ci_resume_checkpoint_index"
    assert type(subject["scope_extension_event_index"]) is int and subject["scope_extension_event_index"] == 26, "ci_resume_scope_index"
    assert subject["checkpoint_sha256"] == CI_RESUME_STOP_SHA256 == _ci_resume_canonical_sha256(record["events"][25]), "ci_resume_checkpoint_pin"
    assert subject["scope_extension_sha256"] == CI_RESUME_SCOPE_SHA256 == _ci_resume_canonical_sha256(record["events"][26]), "ci_resume_scope_pin"
    repair = record["events"][26]["owner_scope_decision"]["subject"]["repair_scope"]
    assert repair["implementation_authorized"] is False, "ci_resume_historical_scope_not_authority"
    assert subject["repair_scope_sha256"] == CI_RESUME_REPAIR_SHA256 == _ci_resume_canonical_sha256(repair), "ci_resume_repair_pin"
    scope = subject["execution_scope"]
    assert scope["implementation_paths"] == CI_REPAIR_SCOPE["implementation_paths"], "ci_resume_active_package_paths"
    assert scope["repository_root_implementation_paths"] == [".github/workflows/asie-ci.yml"], "ci_resume_active_repository_paths"
    assert scope["implementation_authorized"] is True, "ci_resume_conditional_scope_only"
    assert scope["additional_schema_operations"] == [], "ci_resume_no_added_schema"
    assert len(record["allowed_paths"]) == 36 and len(scope["implementation_paths"]) == 31, "ci_resume_scope_counts"


def validate_ci_resume(record: dict, active_target: object) -> None:
    """CR28-03: only the pinned fresh conditional execution receipt may enter current seams."""
    _validate_ci_resume_structure(record, active_target)
    event = record["events"][27]; decision = event["owner_resume_decision"]
    url = decision["record_url"]
    assert type(url) is str and not url.startswith("UNRESOLVED"), "ci_resume_execution_decision_unresolved"
    assert re.fullmatch(r"https://github\.com/alphasigma13579-lang/ASIE/(?:pull/[1-9][0-9]*#issuecomment-[1-9][0-9]*|blob/[0-9a-f]{40}/ASIE-Master-Build-Package-v1\.0\.0-r11-Agent-Engineer/docs/[^\s#]+#[^\s]+)", url), "ci_resume_execution_decision_url"
    previous_urls = {old[key]["record_url"] for old in record["events"][:27] for key in ("owner_resume_decision", "owner_scope_decision") if key in old}
    assert url not in previous_urls, "ci_resume_reused_receipt"
    for value in (decision["recorded_at"], event["recorded_at"]):
        assert type(value) is str and re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})", value), "ci_resume_execution_time_unresolved"
    assert decision["effect"] == "F01A_DEFENSIVE_RESUME_ONLY", "ci_resume_execution_effect"
    assert decision["condition"] == "REVIEWED_GOVERNANCE_TRANSITION_MERGED_AFTER_SEPARATE_OWNER_MERGE_APPROVAL", "ci_resume_merge_condition"


def _ci_resume_historical_inverse(manifest: dict) -> dict:
    """CR28-04: preparation-only inverse restores the complete stopped 27-event blob."""
    original = defensive_record(manifest)
    _validate_ci_resume_structure(original, manifest["execution_sequence"]["active_target"])
    restored = dict(manifest); restored["packages"] = list(manifest["packages"])
    index = next(i for i,p in enumerate(manifest["packages"]) if p["id"] == "FC20-12")
    package = dict(manifest["packages"][index]); restored["packages"][index] = package
    package["execution_slices"] = list(package["execution_slices"])
    record = dict(original); package["execution_slices"][1] = record
    record["execution_authorized"] = False; record["events"] = list(original["events"][:27])
    raw = (json.dumps(restored, ensure_ascii=False, indent=2) + "\n").encode()
    assert ci_resume_blob_sha(raw) == CI_RESUME_BASELINE_BLOB, "ci_resume_baseline_mismatch"
    detached = json.loads(raw)
    validate_ci_scope(defensive_record(detached), detached["execution_sequence"]["active_target"])
    return detached


def validate_ci_resume_preparation(manifest: dict) -> dict:
    """Explicitly non-admitting preparation check; callers receive historical state only."""
    return _ci_resume_historical_inverse(manifest)


def validate_ci_resume_baseline(manifest: dict) -> dict:
    """Public/current inverse requires genuine execution authority before historical access."""
    validate_ci_resume(defensive_record(manifest), manifest["execution_sequence"]["active_target"])
    return _ci_resume_historical_inverse(manifest)


@lru_cache(maxsize=2, typed=True)
def _ci_resume_cached_blob_sha(raw: bytes) -> str:
    return git_blob_sha(raw)


def ci_resume_blob_sha(raw: bytes) -> str:
    if type(raw) is not bytes: raise TypeError("ci_resume_digest_requires_exact_bytes")
    return _ci_resume_cached_blob_sha(raw)


_CI_RESUME_HISTORY_BYTES: tuple[bytes, bytes] | None = None


def ci_resume_historical_source_bytes() -> bytes:
    """CR28-08: fresh source read, two pinned immutable strings, no cached authority."""
    global _CI_RESUME_HISTORY_BYTES
    source = MANIFEST_PATH.read_bytes()
    if type(_CI_RESUME_HISTORY_BYTES) is tuple and len(_CI_RESUME_HISTORY_BYTES) == 2:
        cached_source = _CI_RESUME_HISTORY_BYTES[0]
        if type(source) is bytes and type(cached_source) is bytes and source == cached_source:
            source = cached_source
    assert ci_resume_blob_sha(source) == CI_RESUME_MANIFEST_BLOB, "ci_resume_fixture_source_changed"
    if _CI_RESUME_HISTORY_BYTES is None:
        baseline = _ci_amend_historical_inverse(json.loads(source))
        raw = (json.dumps(baseline, ensure_ascii=False, indent=2) + "\n").encode()
        assert ci_resume_blob_sha(raw) == CI_RESUME_BASELINE_BLOB, "ci_resume_fixture_baseline_changed"
        _CI_RESUME_HISTORY_BYTES = (source, raw)
    assert type(_CI_RESUME_HISTORY_BYTES) is tuple and len(_CI_RESUME_HISTORY_BYTES) == 2, "ci_resume_fixture_cache_shape"
    cached_source, raw = _CI_RESUME_HISTORY_BYTES
    assert type(cached_source) is bytes and type(raw) is bytes, "ci_resume_fixture_cache_type"
    source_matches = source == cached_source
    assert source_matches, "ci_resume_fixture_cache_source_changed"
    assert ci_resume_blob_sha(raw) == CI_RESUME_BASELINE_BLOB, "ci_resume_fixture_baseline_changed"
    return raw


def historical_ci_scope_manifest() -> dict:
    """Fresh canonical 27-event fixture; never an alternate current authority."""
    source = ci_resume_historical_source_bytes(); manifest = json.loads(source)
    source_is_canonical = source == (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode()
    assert source_is_canonical, "manifest_noncanonical_source"
    return manifest


def ci_resume_historical_view(source_bytes: bytes, relative_path: str) -> bytes:
    assert type(source_bytes) is bytes, "ci_resume_view_source_bytes"
    assert type(relative_path) is str and relative_path in CI_RESUME_VIEW_SECTION_SHA256, "ci_resume_view_path"
    marker = CI_RESUME_VIEW_MARKER.encode(); separator = b"\n" + marker + b"\n"
    assert source_bytes.count(marker) == 1, "ci_resume_view_marker"
    assert source_bytes.count(separator) == 1, "ci_resume_view_boundary"
    prefix, section = source_bytes.split(separator,1)
    assert git_blob_sha(prefix) == CI_RESUME_VIEW_PREFIX_BLOBS[relative_path], "ci_resume_view_prefix_changed"
    assert hashlib.sha256(marker+b"\n"+section).hexdigest() == CI_RESUME_VIEW_SECTION_SHA256[relative_path], "ci_resume_view_section_changed"
    ci_scope_historical_view(prefix, relative_path)
    return prefix


def test_ci_resume_current_admission_requires_real_execution_receipt() -> None:
    """CR28-03: real pinned execution receipt admits the conditional governance candidate."""
    manifest = load_manifest()
    validate_routing_registration(manifest); validate_execution_sequence(manifest)
    validate_ci_amend_baseline(manifest)


def test_ci_resume_preparation_inverse_and_complete_history() -> None:
    manifest = historical_ci_resume_manifest(); before = json.dumps(manifest,sort_keys=True)
    prior = validate_ci_resume_preparation(manifest)
    assert json.dumps(manifest,sort_keys=True) == before
    assert defensive_record(prior)["events"] == CI_SCOPE_RECORD["events"]
    assert defensive_record(prior)["execution_authorized"] is False
    assert len(defensive_record(prior)["allowed_paths"]) == 36
    assert defensive_record(prior)["allowed_repository_root_paths"] == [".github/workflows/asie-ci.yml"]
    assert git_blob_sha((json.dumps(prior,ensure_ascii=False,indent=2)+"\n").encode()) == CI_RESUME_BASELINE_BLOB
    inverse = prior
    for validator in (validate_ci_scope_baseline,validate_overlay_resume_baseline,validate_overlay_scope_baseline,validate_dataset_resume_baseline,validate_dataset_scope_baseline,validate_recovery_resume_baseline,validate_recovery_scope_baseline,validate_key_binding_resume_baseline,validate_key_binding_scope_baseline,validate_review_identity_resume_baseline,validate_review_identity_scope_baseline,validate_index_resume_baseline,validate_index_scope_baseline,validate_consumption_resume_baseline,validate_consumption_scope_baseline,validate_resume_baseline,validate_scope_extension_baseline):
        inverse = validator(inverse)


@pytest.mark.parametrize("location,field,placeholder", (("decision","record_url","UNRESOLVED_OWNER_EXECUTION_DECISION_RECORD_URL"),("decision","recorded_at","UNRESOLVED_OWNER_EXECUTION_DECISION_RECORDED_AT"),("event","recorded_at","UNRESOLVED_RESUME_TRANSITION_RECORDED_AT")))
def test_ci_resume_unresolved_preparation_receipt_cannot_admit(location: str, field: str, placeholder: str) -> None:
    """Explicit missing-authority mutations stay denied after the real receipt is pinned."""
    manifest = load_manifest(); validate_ci_amend_baseline(manifest)
    historical_ci_scope_manifest(); historical_ci_scope_manifest()
    event = defensive_record(manifest)["events"][27]
    target = event["owner_resume_decision"] if location == "decision" else event
    target[field] = placeholder
    for validator in (validate_ci_amend_baseline,validate_routing_registration,validate_execution_sequence):
        with pytest.raises(AssertionError,match="defensive_record_mismatch"): validator(manifest)


@pytest.mark.parametrize("path", [tuple(path) for path in index_resume_leaf_paths(CI_RESUME_EVENT)])
def test_ci_resume_pins_each_new_leaf(path: tuple) -> None:
    record = deepcopy(CI_RESUME_RECORD); target = record["events"][27]
    for key in path[:-1]: target = target[key]
    target[path[-1]] = "UNREVIEWED"
    with pytest.raises(AssertionError): _validate_ci_resume_structure(record,DEFENSIVE_START_TARGET)


@pytest.mark.parametrize("path", [(),("events",27),("events",27,"owner_resume_decision"),("events",27,"owner_resume_decision","subject"),("events",27,"owner_resume_decision","subject","execution_scope")])
@pytest.mark.parametrize("mutation", ("missing","extra"))
def test_ci_resume_closed_objects(path: tuple, mutation: str) -> None:
    record = deepcopy(CI_RESUME_RECORD); target = record
    for key in path: target = target[key]
    if mutation == "missing": target.pop(next(iter(target)))
    else: target["unapproved"] = True
    with pytest.raises(AssertionError): _validate_ci_resume_structure(record,DEFENSIVE_START_TARGET)


@pytest.mark.parametrize("index", range(27))
def test_ci_resume_preserves_every_prior_event(index: int) -> None:
    record = deepcopy(CI_RESUME_RECORD);record["events"][index]["type"]="CHANGED"
    with pytest.raises(AssertionError):_validate_ci_resume_structure(record,DEFENSIVE_START_TARGET)


@pytest.mark.parametrize("path,value", [(("execution_authorized",),1),(("execution_authorized",),False),(("allowed_schema_operations",0,"unique"),0),(("events",27,"owner_resume_decision","subject","checkpoint_event_index"),25.0),(("events",27,"owner_resume_decision","subject","scope_extension_event_index"),26.0),(("events",27,"owner_resume_decision","subject","execution_scope","implementation_authorized"),1),(("events",27,"owner_resume_decision","subject","execution_scope","live_database_authorized"),0),(("events",26,"owner_scope_decision","subject","repair_scope","implementation_authorized"),0)])
def test_ci_resume_strict_literal_types(path: tuple,value: object) -> None:
    record=deepcopy(CI_RESUME_RECORD);target=record
    for key in path[:-1]:target=target[key]
    target[path[-1]]=value
    with pytest.raises(AssertionError):_validate_ci_resume_structure(record,DEFENSIVE_START_TARGET)


@pytest.mark.parametrize("mutation", ("checkpoint_index","scope_index","checkpoint_hash","scope_hash","repair_hash","stale_baseline","root_swap","root_wildcard","root_parent","scope_union","historical_scope_true","slot","hold","unrelated"))
def test_ci_resume_inverse_rejects_scope_reference_and_unrelated_drift(mutation: str) -> None:
    manifest=historical_ci_resume_manifest();record=defensive_record(manifest);subject=record["events"][27]["owner_resume_decision"]["subject"]
    if mutation=="checkpoint_index":subject["checkpoint_event_index"]=26
    elif mutation=="scope_index":subject["scope_extension_event_index"]=25
    elif mutation=="checkpoint_hash":subject["checkpoint_sha256"]="0"*64
    elif mutation=="scope_hash":subject["scope_extension_sha256"]="0"*64
    elif mutation=="repair_hash":subject["repair_scope_sha256"]="0"*64
    elif mutation=="stale_baseline":subject["baseline_commit_sha"]="e5e13f672161a283c82634cf8df946d6e90b0aa9"
    elif mutation=="root_swap":subject["execution_scope"]["repository_root_implementation_paths"]=["tests/test_program_close_10_repository_rebaseline.py"]
    elif mutation=="root_wildcard":record["allowed_repository_root_paths"]=[".github/workflows/*"]
    elif mutation=="root_parent":record["allowed_repository_root_paths"]=["../.github/workflows/asie-ci.yml"]
    elif mutation=="scope_union":subject["execution_scope"]["implementation_paths"]=list(record["allowed_paths"])
    elif mutation=="historical_scope_true":record["events"][26]["owner_scope_decision"]["subject"]["repair_scope"]["implementation_authorized"]=True
    elif mutation=="slot":manifest["execution_sequence"]["active_target"]=None
    elif mutation=="hold":manifest["execution_sequence"]["held_packages"]=[]
    else:manifest["program_id"]="UNRELATED"
    before=json.dumps(manifest,sort_keys=True)
    with pytest.raises(AssertionError):validate_ci_resume_preparation(manifest)
    assert json.dumps(manifest,sort_keys=True)==before


@pytest.mark.parametrize("receipt", ("scope_preparation","previous_resume","merge_only","immediate","missing_url","missing_time"))
def test_ci_resume_rejects_preparation_merge_and_reused_authority(receipt: str) -> None:
    manifest=load_manifest();decision=defensive_record(manifest)["events"][27]["owner_resume_decision"]
    if receipt=="scope_preparation":decision["record_url"]=CI_SCOPE_EVENT["owner_scope_decision"]["record_url"];decision["effect"]=CI_SCOPE_EVENT["owner_scope_decision"]["effect"]
    elif receipt=="previous_resume":decision["record_url"]=OVERLAY_RESUME_DECISION["record_url"]
    elif receipt=="merge_only":decision["effect"]="GOVERNANCE_MERGE_ONLY"
    elif receipt=="immediate":decision["condition"]="IMMEDIATE"
    elif receipt=="missing_url":decision["record_url"]=""
    else:decision["recorded_at"]=""
    for validator in (validate_ci_amend_baseline,validate_routing_registration,validate_execution_sequence):
        with pytest.raises(AssertionError):validator(manifest)


@pytest.mark.parametrize("relative_path",tuple(CI_RESUME_VIEW_SECTION_SHA256))
@pytest.mark.parametrize("mutation",("valid","prefix","section","duplicate","boundary","swap"))
def test_ci_resume_projection_seals(relative_path: str,mutation: str) -> None:
    root=Path(__file__).resolve().parents[1];source=ci_amend_historical_view((root/relative_path).read_bytes(),relative_path);sep=("\n"+CI_RESUME_VIEW_MARKER+"\n").encode();prefix,section=source.split(sep,1)
    if mutation=="valid":assert ci_resume_historical_view(source,relative_path)==prefix;return
    if mutation=="prefix":source=b" "+source
    elif mutation=="section":source+=b" "
    elif mutation=="duplicate":source+=sep
    elif mutation=="boundary":source=prefix+b"\n"+CI_RESUME_VIEW_MARKER.encode()+b"\r\n"+section
    else:
        other=next(path for path in CI_RESUME_VIEW_SECTION_SHA256 if path!=relative_path);source=prefix+sep+ci_amend_historical_view((root/other).read_bytes(),other).split(sep,1)[1]
    with pytest.raises(AssertionError,match="ci_resume_view"):ci_resume_historical_view(source,relative_path)


def test_ci_resume_projection_raw_types_and_unknown_path() -> None:
    path=next(iter(CI_RESUME_VIEW_SECTION_SHA256));raw=ci_amend_historical_view((Path(__file__).resolve().parents[1]/path).read_bytes(),path)
    for value in (raw.decode(),bytearray(raw),None,False):
        with pytest.raises(AssertionError,match="ci_resume_view_source_bytes"):ci_resume_historical_view(value,path)
    for wrong in ("",None,"../"+path,".github/workflows/asie-ci.yml"):
        with pytest.raises(AssertionError,match="ci_resume_view_path"):ci_resume_historical_view(raw,wrong)


def test_ci_resume_frozen_acr_unchanged() -> None:
    raw=ci_amend_historical_view((Path(__file__).resolve().parents[1]/CI_ACR_PATH).read_bytes(), CI_ACR_PATH)
    assert git_blob_sha(raw)==CI_ACR_BLOB
    ci_scope_acr_historical_view(raw)


def test_ci_resume_fixture_cold_warm_detachment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(globals(),"_CI_RESUME_HISTORY_BYTES",None)
    manifest=historical_ci_resume_manifest();inverse=validate_ci_resume_preparation(manifest);first=historical_ci_scope_manifest();second=historical_ci_scope_manifest()
    expected=json.dumps(inverse,ensure_ascii=False,indent=2)+"\n"
    assert json.dumps(first,ensure_ascii=False,indent=2)+"\n"==expected
    assert json.dumps(second,ensure_ascii=False,indent=2)+"\n"==expected
    def ids(value):
        if type(value) is dict:return {id(value)}.union(*(ids(child) for child in value.values()))
        if type(value) is list:return {id(value)}.union(*(ids(child) for child in value))
        return set()
    assert ids(first).isdisjoint(ids(second)) and ids(first).isdisjoint(ids(manifest)) and ids(first).isdisjoint(ids(CI_SCOPE_RECORD))
    defensive_record(first)["events"][0]["type"]="MUTATED"
    assert json.dumps(historical_ci_scope_manifest(),ensure_ascii=False,indent=2)+"\n"==expected


@pytest.mark.parametrize("warm",(False,True))
@pytest.mark.parametrize("mutation",("bytes","literal","history","slot","unrelated","receipt","root"))
def test_ci_resume_fixture_cold_warm_source_denials(monkeypatch: pytest.MonkeyPatch,warm: bool,mutation: str) -> None:
    monkeypatch.setitem(globals(),"_CI_RESUME_HISTORY_BYTES",None);manifest=load_manifest();record=defensive_record(manifest)
    if warm:historical_ci_scope_manifest()
    cache=_CI_RESUME_HISTORY_BYTES
    if mutation=="literal":record["execution_authorized"]=1
    elif mutation=="history":record["events"][0]["type"]="CHANGED"
    elif mutation=="slot":manifest["execution_sequence"]["active_target"]=None
    elif mutation=="unrelated":manifest["program_id"]="CHANGED"
    elif mutation=="receipt":record["events"][27]["owner_resume_decision"]["effect"]="PREPARE_ONLY"
    elif mutation=="root":record["allowed_repository_root_paths"].append(".github/workflows/*")
    raw=(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n").encode()
    if mutation=="bytes":raw+=b"\n"
    monkeypatch.setattr(Path,"read_bytes",lambda _path:raw)
    with pytest.raises(AssertionError,match="ci_resume_fixture_source_changed"):historical_ci_scope_manifest()
    assert _CI_RESUME_HISTORY_BYTES is cache


@pytest.mark.parametrize("mutation",("source","baseline","type","shape","source_type"))
def test_ci_resume_fixture_poisoned_cache_denied(monkeypatch: pytest.MonkeyPatch,mutation: str) -> None:
    monkeypatch.setitem(globals(),"_CI_RESUME_HISTORY_BYTES",None);historical_ci_scope_manifest();source,baseline=_CI_RESUME_HISTORY_BYTES
    cache=(source+b" ",baseline) if mutation=="source" else (source,baseline+b" ") if mutation=="baseline" else (source,{}) if mutation=="type" else (source,) if mutation=="shape" else (bytearray(source),baseline)
    monkeypatch.setitem(globals(),"_CI_RESUME_HISTORY_BYTES",cache)
    with pytest.raises(AssertionError,match="ci_resume_fixture_"):historical_ci_scope_manifest()
    assert _CI_RESUME_HISTORY_BYTES is cache


def test_ci_resume_fixture_single_read_and_failed_publication(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(globals(),"_CI_RESUME_HISTORY_BYTES",None);raw=MANIFEST_PATH.read_bytes();reads=[];calls=[];original=_ci_resume_historical_inverse
    def alternate(_path):reads.append(True);return raw if len(reads)==1 else raw+b"\n"
    def checked(manifest):calls.append(True);return original(manifest)
    monkeypatch.setattr(Path,"read_bytes",alternate);monkeypatch.setitem(globals(),"_ci_resume_historical_inverse",checked)
    historical_ci_scope_manifest();assert len(reads)==len(calls)==1
    with pytest.raises(AssertionError,match="ci_resume_fixture_source_changed"):historical_ci_scope_manifest()
    assert len(reads)==2 and len(calls)==1
    monkeypatch.setitem(globals(),"_CI_RESUME_HISTORY_BYTES",None);monkeypatch.setattr(Path,"read_bytes",lambda _path:raw)
    def failed(_manifest):raise AssertionError("injected_inverse_failure")
    monkeypatch.setitem(globals(),"_ci_resume_historical_inverse",failed)
    with pytest.raises(AssertionError,match="injected_inverse_failure"):historical_ci_scope_manifest()
    assert _CI_RESUME_HISTORY_BYTES is None


def test_ci_resume_digest_bounded_exact_and_independent() -> None:
    _ci_resume_cached_blob_sha.cache_clear();prior=_ci_scope_cached_blob_sha.cache_info();raw=b"resume-digest";equal=bytes(bytearray(raw))
    assert ci_resume_blob_sha(raw)==ci_resume_blob_sha(equal)==git_blob_sha(raw)
    assert _ci_resume_cached_blob_sha.cache_info().hits==1
    changed=raw+b"x";assert ci_resume_blob_sha(changed)==git_blob_sha(changed)!=git_blob_sha(raw)
    ci_resume_blob_sha(b"third");assert _ci_resume_cached_blob_sha.cache_info().currsize==2
    misses=_ci_resume_cached_blob_sha.cache_info().misses;ci_resume_blob_sha(raw);assert _ci_resume_cached_blob_sha.cache_info().misses==misses+1
    assert _ci_scope_cached_blob_sha.cache_info()==prior


def test_ci_resume_digest_nonexact_types_and_failure_denied(monkeypatch: pytest.MonkeyPatch) -> None:
    class Pretend(bytes):
        def __eq__(self,other):return True
        __hash__=bytes.__hash__
    _ci_resume_cached_blob_sha.cache_clear();before=_ci_resume_cached_blob_sha.cache_info()
    for raw in (Pretend(b"x"),bytearray(b"x"),memoryview(b"x"),None,"x",False,0,[],{}):
        with pytest.raises(TypeError,match="ci_resume_digest_requires_exact_bytes"):ci_resume_blob_sha(raw)
    assert _ci_resume_cached_blob_sha.cache_info()==before
    original=git_blob_sha
    def failed(raw):raise RuntimeError("synthetic_ci_resume_digest_failure")
    monkeypatch.setitem(globals(),"git_blob_sha",failed)
    with pytest.raises(RuntimeError,match="synthetic_ci_resume_digest_failure"):ci_resume_blob_sha(b"fresh")
    assert _ci_resume_cached_blob_sha.cache_info().currsize==0
    monkeypatch.setitem(globals(),"git_blob_sha",original);assert ci_resume_blob_sha(b"fresh")==original(b"fresh")
    _ci_resume_cached_blob_sha.cache_clear()


@pytest.mark.parametrize("warm",(False,True))
def test_ci_resume_cached_uncached_equivalence(monkeypatch: pytest.MonkeyPatch,warm: bool) -> None:
    monkeypatch.setitem(globals(),"_CI_RESUME_HISTORY_BYTES",None);_ci_resume_cached_blob_sha.cache_clear()
    if warm:historical_ci_scope_manifest()
    first=historical_ci_scope_manifest();monkeypatch.setitem(globals(),"_CI_RESUME_HISTORY_BYTES",None)
    def uncached(raw):
        if type(raw) is not bytes:raise TypeError("ci_resume_digest_requires_exact_bytes")
        return git_blob_sha(raw)
    monkeypatch.setitem(globals(),"ci_resume_blob_sha",uncached);second=historical_ci_scope_manifest()
    assert json.dumps(first,sort_keys=True)==json.dumps(second,sort_keys=True)
    defensive_record(first)["events"][0]["type"]="MUTATED";assert defensive_record(second)["events"][0]["type"]!="MUTATED"


def test_ci_resume_identity_uses_fresh_equal_bytes_only(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(globals(),"_CI_RESUME_HISTORY_BYTES",None);historical_ci_scope_manifest();cached,baseline=_CI_RESUME_HISTORY_BYTES;reads=[];seen=[];original=ci_resume_blob_sha
    def fresh(_path):value=bytes(bytearray(cached));reads.append(value);return value
    def observed(raw):seen.append(raw);return original(raw)
    monkeypatch.setattr(Path,"read_bytes",fresh);monkeypatch.setitem(globals(),"ci_resume_blob_sha",observed)
    assert ci_resume_historical_source_bytes()==baseline
    assert len(reads)==1 and reads[0]==cached and reads[0] is not cached
    assert seen[0] is cached and seen[-1] is baseline
    changed=cached+b" ";monkeypatch.setattr(Path,"read_bytes",lambda _path:changed)
    with pytest.raises(AssertionError,match="ci_resume_fixture_source_changed"):ci_resume_historical_source_bytes()
    assert seen[-1] is changed


@pytest.mark.parametrize("mutation",("record","literal","cache_source","canonical"))
def test_ci_resume_bounded_ci_denial_equivalence(monkeypatch: pytest.MonkeyPatch,mutation: str) -> None:
    import difflib
    monkeypatch.setitem(globals(),"_CI_RESUME_HISTORY_BYTES",None);historical_ci_scope_manifest();source,baseline=_CI_RESUME_HISTORY_BYTES;record=deepcopy(CI_RESUME_RECORD);calls=[]
    def bad_diff(*args,**kwargs):calls.append(True);raise RuntimeError("unexpected_ci_resume_relational_diff")
    if mutation=="record":record["events"][0]["type"]="CHANGED";invoke=lambda:_validate_ci_resume_structure(record,DEFENSIVE_START_TARGET);expected="defensive_record_mismatch"
    elif mutation=="literal":record["execution_authorized"]=1;invoke=lambda:_validate_ci_resume_structure(record,DEFENSIVE_START_TARGET);expected="ci_resume_literal_types"
    elif mutation=="cache_source":monkeypatch.setitem(globals(),"_CI_RESUME_HISTORY_BYTES",(source+b" ",baseline));invoke=ci_resume_historical_source_bytes;expected="ci_resume_fixture_cache_source_changed"
    else:monkeypatch.setitem(globals(),"ci_resume_historical_source_bytes",lambda:baseline+b"\n");invoke=historical_ci_scope_manifest;expected="manifest_noncanonical_source"
    outcomes=[]
    for ci in (False,True):
        if ci:monkeypatch.setenv("CI","true")
        else:monkeypatch.delenv("CI",raising=False)
        monkeypatch.setattr(difflib,"ndiff",bad_diff)
        try:invoke()
        except AssertionError as exc:outcomes.append((type(exc),str(exc).split("\n",1)[0]))
        else:outcomes.append((None,None))
    assert outcomes==[(AssertionError,expected),(AssertionError,expected)] and not calls


@pytest.mark.parametrize("mutation", ("source", "baseline", "type", "shape", "source_type", "source_byte"))
def test_ci_resume_identity_preserves_original_denial_order(monkeypatch: pytest.MonkeyPatch, mutation: str) -> None:
    import inspect
    monkeypatch.setitem(globals(), "_CI_RESUME_HISTORY_BYTES", None)
    historical_ci_scope_manifest(); source, baseline = _CI_RESUME_HISTORY_BYTES
    original_text = inspect.getsource(ci_resume_historical_source_bytes)
    fast_block = '    if type(_CI_RESUME_HISTORY_BYTES) is tuple and len(_CI_RESUME_HISTORY_BYTES) == 2:\n        cached_source = _CI_RESUME_HISTORY_BYTES[0]\n        if type(source) is bytes and type(cached_source) is bytes and source == cached_source:\n            source = cached_source\n'
    assert original_text.count(fast_block) == 1
    namespace = dict(globals()); exec(original_text.replace(fast_block, ""), namespace)
    fast_namespace = dict(globals()); exec(original_text, fast_namespace)
    cache = (source+b" ", baseline) if mutation == "source" else (source, baseline+b" ") if mutation == "baseline" else (source, {}) if mutation == "type" else (source,) if mutation == "shape" else (source, baseline)
    current = bytearray(source) if mutation == "source_type" else source+b" " if mutation == "source_byte" else bytes(bytearray(source))
    monkeypatch.setattr(Path, "read_bytes", lambda _path: current)
    monkeypatch.setitem(globals(), "_CI_RESUME_HISTORY_BYTES", cache)
    namespace["_CI_RESUME_HISTORY_BYTES"] = cache
    fast_namespace["_CI_RESUME_HISTORY_BYTES"] = cache
    outcomes = []
    for fn in (namespace["ci_resume_historical_source_bytes"], fast_namespace["ci_resume_historical_source_bytes"]):
        try: fn()
        except (AssertionError, TypeError) as exc: outcomes.append((type(exc), str(exc)))
        else: outcomes.append((None, None))
    assert outcomes[0] == outcomes[1] and outcomes[0][0] is not None
    assert _CI_RESUME_HISTORY_BYTES is cache


@pytest.mark.parametrize("event_index,field", [(i, field) for i in (15,17,18,20,21,23,24,26) for field in ("record_url","recorded_at","effect")]+[(18,"condition"),(21,"condition"),(24,"condition")])
def test_ci_resume_historical_receipt_negatives_reach_current_seams(event_index: int, field: str) -> None:
    """Historical receipt corruption remains denied at every actual current seam."""
    manifest = load_manifest(); event = defensive_record(manifest)["events"][event_index]
    decision = event["owner_scope_decision" if event_index in (17,20,23,26) else "owner_resume_decision"]
    decision[field] = "UNRESOLVED_OR_CHANGED"
    for validator in (validate_ci_amend_baseline, validate_routing_registration, validate_execution_sequence):
        with pytest.raises(AssertionError, match="defensive_record_mismatch"): validator(manifest)


def test_ci_resume_stopped_history_cannot_be_current_authority() -> None:
    manifest = historical_ci_scope_manifest()
    for validator in (validate_ci_amend_baseline, validate_routing_registration, validate_execution_sequence):
        with pytest.raises(AssertionError, match="defensive_record_mismatch"): validator(manifest)


# CI29: finite, explicit pre-merge exception for the two CI maintenance files only.
CI_AMEND_EVENT = json.loads(r'''{
  "type": "CI_MAINTENANCE_EXCEPTION",
  "recorded_at": "2026-10-18T05:59:31Z",
  "owner_ci_maintenance_decision": {
    "id": "DECISION-FC20-12-C3C-SINGLE-JOB-TIMEOUT-PREMERGE-EXCEPTION-2026-10-18",
    "owner_approval_at": "2026-10-18T05:53:23.887243+00:00",
    "approval_source": "EXPLICIT_OWNER_APPROVAL_RECORDED_BY_ASSISTANT_NOT_CRYPTOGRAPHIC_SIGNATURE",
    "public_proposal_reference": {
      "url": "https://github.com/alphasigma13579-lang/ASIE/pull/217",
      "role": "PROPOSAL_REFERENCE_NOT_APPROVAL_RECEIPT_OR_MERGE_EVIDENCE"
    },
    "decision_record": {
      "path": "docs/ACR-FIN-003-C3C-DETERMINISTIC-2D-SENSITIVITY-DARK-BUILD-2026-08-10.md",
      "section_marker": "<!-- C3C-CI-TIMEOUT-PREMERGE-EXCEPTION-2026-10-18 -->",
      "section_sha256": "f00f51702d6e93dbe45adbb62b6d5ce0a7227af2d4e6080a5c0513bacea1b0cf"
    },
    "effect": "EDIT_TEST_AND_UPDATE_PR217_CI_MAINTENANCE_BEFORE_GOVERNANCE_MERGE",
    "effective_condition": "EFFECTIVE_NOW_FOR_EXACT_TWO_CI_MAINTENANCE_PATHS_ONLY",
    "subject": {
      "merged_baseline_commit_sha": "ce8ef8c8882ba5117f9c7f1dfbac34fc50f507af",
      "merged_baseline_manifest_blob_sha": "4eef63fa72b0316383c6112ee92e577514123178",
      "published_unmerged_proposal_commit_sha": "57c22bc91f276e6115b53366a88f0eec7d2ee715",
      "published_unmerged_proposal_manifest_blob_sha": "3a3e5c8506600ad92fd30242000d40b5a01f1a84",
      "previous_resume_event_index": 27,
      "previous_resume_event_sha256": "eb077cced35fc1bb8cb72f18acf69f11fae7401e42ae5efaf7fff0fe327a5134",
      "digest_serialization": "UTF8_JSON_ENSURE_ASCII_FALSE_SORT_KEYS_TRUE_COMPACT_SEPARATORS_COMMA_COLON",
      "prior_acr_blob_sha": "c1db77e3e5baf4cc422cf4c36cba57cef60a9f7c",
      "application_head_sha": "281f11d7a6d8e9850b1da8a6b6b23ffeb4f51546",
      "pending_resume28_ci_proposal_disposition": "SUPERSEDED_SPLIT_AND_20_MINUTE_DESIGN_NOT_MERGED_OR_PARALLEL_AUTHORITY",
      "superseded_sequencing": [
        "ACR-FIN-003-C3C:G-C3C-0_AND_SECTION14_MERGE_BEFORE_CI",
        "ACR-FIN-003-C3C:CI_APPENDIX_LINES393_AND430_AT_CE8EF8C",
        "F01A_REGISTRATION_PROPOSAL:SECTION4",
        "PENDING_RESUME28:MERGE_BEFORE_THE_TWO_CI_FILES_ONLY"
      ],
      "superseded_ci_purpose": "SPLIT_BUILD_TEST_AND_BENCHMARK_WITH_20_MINUTE_BUILD_TEST_BUDGET",
      "current_ci_purpose": "KEEP_EXISTING_SINGLE_SEQUENTIAL_JOB_CHANGE_ONLY_JOB_TIMEOUT_20_TO_30",
      "immediately_authorized_scope": {
        "repository_root_paths": [
          ".github/workflows/asie-ci.yml"
        ],
        "package_root_paths": [
          "tests/test_program_close_10_repository_rebaseline.py"
        ]
      },
      "workflow_contract": {
        "repository_root_path": ".github/workflows/asie-ci.yml",
        "prior_workflow_blob_sha": "19afa3d54997423e54c3aa1ecbd5ac2578458f89",
        "job_id": "build-and-test",
        "required_context": "Build frontend and test backend",
        "job_count": 1,
        "job_timeout_minutes": 30,
        "benchmark_step_timeout_minutes": 10,
        "benchmark_command": "python scripts/benchmark_finance_v2_sensitivity.py --warmups 1 --trials 3",
        "all_other_workflow_bytes_unchanged": true,
        "all_tests_and_success_criteria_preserved": true,
        "sequential_failure_behavior_preserved": true
      },
      "governance_package_total_files": 10,
      "review_date": "2026-10-18",
      "review_required_before_merge": true,
      "authorization_expires_on": "MERGE_OR_CANCELLATION_OF_THIS_EXACT_PR217_AMENDMENT",
      "future_ci_maintenance_authorized": false,
      "rationale": {
        "run_url": "https://github.com/alphasigma13579-lang/ASIE/actions/runs/39098964076",
        "attempts": [
          1,
          2
        ],
        "both_job_elapsed_seconds": 1215,
        "attempt1_pytest_passed": 22860,
        "attempt1_pytest_seconds": 1170.37,
        "attempt2_pytest_cancelled_percent": 99,
        "attempt2_pytest_summary_available": false,
        "explicit_log_cause": "RAW_STEP_LOG_CANCELLATION_WITH_EXPLICIT_GITHUB_JOB_TIMEOUT_20M0S_ANNOTATION",
        "thirty_minute_success_guaranteed": false
      },
      "general_resume_condition": "REVIEWED_GOVERNANCE_TRANSITION_MERGED_AFTER_SEPARATE_OWNER_MERGE_APPROVAL",
      "application_execution_before_governance_merge_authorized": false,
      "governance_merge_authorized": false,
      "application_merge_authorized": false,
      "deployment_authorized": false,
      "external_network_authorized": false,
      "provider_activation_authorized": false,
      "live_database_authorized": false,
      "rejected_numeric_investigation_authorized": false
    }
  }
}''')
CI_AMEND_SEALS = json.loads(r'''{
  "docs/ACR-FIN-003-C3C-DETERMINISTIC-2D-SENSITIVITY-DARK-BUILD-2026-08-10.md": {
    "prefix_blob": "c1db77e3e5baf4cc422cf4c36cba57cef60a9f7c",
    "section_sha256": "f00f51702d6e93dbe45adbb62b6d5ce0a7227af2d4e6080a5c0513bacea1b0cf"
  },
  "docs/FOUNDATION-COMPLETE-20-CORE-INTELLIGENCE-COMPLETION-PROGRAM-2026-07-29.md": {
    "prefix_blob": "a90ac8eb052c8a8c48502dd32d3df0622ebf9aca",
    "section_sha256": "78bedaafbe837e1c72bb548ecbab5619443707628912793b61ab3a65b2e48b97"
  },
  "docs/EKB/FOUNDATION-COMPLETE-20-PACKAGE-INDEX.md": {
    "prefix_blob": "78e3845b35567f5ebf660d4e7ba7f043ca06345a",
    "section_sha256": "78bedaafbe837e1c72bb548ecbab5619443707628912793b61ab3a65b2e48b97"
  },
  "docs/ASIE-BETA-EXECUTION-MASTER-PLAN-2026-09-09.md": {
    "prefix_blob": "f6f3a70c8d13e2427fe3ca83aaaa8088d80e9826",
    "section_sha256": "78bedaafbe837e1c72bb548ecbab5619443707628912793b61ab3a65b2e48b97"
  },
  "docs/FC20-12-F01A-DEFENSIVE-ENABLING-REGISTRATION-PROPOSAL-2026-10-01.md": {
    "prefix_blob": "4d70a08c05ee0018b9fff2b284af80e30a5e7c76",
    "section_sha256": "78bedaafbe837e1c72bb548ecbab5619443707628912793b61ab3a65b2e48b97"
  },
  "docs/FC20-12-F01A-APPROVAL-CONSUMPTION-SCOPE-REGISTRATION-2026-10-09.md": {
    "prefix_blob": "139cd99540afcf3cf4a7d25930dbbd3fdce9c512",
    "section_sha256": "78bedaafbe837e1c72bb548ecbab5619443707628912793b61ab3a65b2e48b97"
  }
}''')
CI_AMEND_MARKER = '<!-- C3C-CI-TIMEOUT-PREMERGE-EXCEPTION-2026-10-18 -->'
CI_AMEND_PUBLISHED_BLOB = '3a3e5c8506600ad92fd30242000d40b5a01f1a84'
CI_AMEND_WORKFLOW_BLOB = '62b358f42f6ac9149e01bc5b14828617df80ee05'

def _ci_amend_prior_record(record: dict, active_target: object) -> dict:
    """Borrow a shallow historical view only for read-only validation; never cache it."""
    if type(record) is not dict or set(record) != set(CI_RESUME_RECORD):
        raise AssertionError("defensive_fields")
    events = record["events"]
    if type(events) is not list or len(events) != 29:
        raise AssertionError("defensive_record_mismatch")
    event_matches = events[28] == CI_AMEND_EVENT
    assert event_matches, "ci_amend_event_mismatch"
    literal_types_match = _ci_scope_literal_equal(events[28], CI_AMEND_EVENT)
    assert literal_types_match, "ci_amend_literal_types"
    prior = dict(record); prior["events"] = events[:28]
    validate_ci_resume(prior, active_target)
    return prior


def validate_ci_amend(record: dict, active_target: object) -> None:
    """Immediate authority is this finite two-file CI exception, never general RESUME."""
    _ci_amend_prior_record(record, active_target)
    subject = record["events"][28]["owner_ci_maintenance_decision"]["subject"]
    assert subject["previous_resume_event_index"] == 27, "ci_amend_previous_index"
    assert _ci_resume_canonical_sha256(record["events"][27]) == subject["previous_resume_event_sha256"], "ci_amend_previous_resume_pin"
    assert subject["immediately_authorized_scope"] == {"repository_root_paths":[".github/workflows/asie-ci.yml"],"package_root_paths":["tests/test_program_close_10_repository_rebaseline.py"]}, "ci_amend_two_file_scope"
    assert subject["application_execution_before_governance_merge_authorized"] is False, "ci_amend_no_application_authority"
    assert subject["general_resume_condition"] == CI_RESUME_DECISION["condition"], "ci_amend_general_resume_condition"
    assert subject["pending_resume28_ci_proposal_disposition"] == "SUPERSEDED_SPLIT_AND_20_MINUTE_DESIGN_NOT_MERGED_OR_PARALLEL_AUTHORITY", "ci_amend_supersession"


def _ci_amend_published_inverse(manifest: dict) -> dict:
    """Return a detached exact copy of the unmerged published 28-event proposal."""
    original = defensive_record(manifest)
    validate_ci_amend(original, manifest["execution_sequence"]["active_target"])
    restored = dict(manifest); restored["packages"] = list(manifest["packages"])
    index = next(i for i,p in enumerate(manifest["packages"]) if p["id"] == "FC20-12")
    package = dict(manifest["packages"][index]); restored["packages"][index] = package
    package["execution_slices"] = list(package["execution_slices"])
    prior = dict(original); prior["events"] = original["events"][:28]
    package["execution_slices"][1] = prior
    raw = (json.dumps(restored,ensure_ascii=False,indent=2)+"\n").encode()
    assert git_blob_sha(raw) == CI_AMEND_PUBLISHED_BLOB, "ci_amend_published_baseline_mismatch"
    return json.loads(raw)


def _ci_amend_historical_inverse(manifest: dict) -> dict:
    """Reuse the existing two-immutable-bytes fixture cache, with both exact inverses."""
    return _ci_resume_historical_inverse(_ci_amend_published_inverse(manifest))


def validate_ci_amend_baseline(manifest: dict) -> dict:
    return _ci_amend_historical_inverse(manifest)


def historical_ci_resume_manifest() -> dict:
    """Fresh read and verified immutable source; fresh detached published28 fixture."""
    ci_resume_historical_source_bytes()
    source = _CI_RESUME_HISTORY_BYTES[0]
    manifest = json.loads(source)
    defensive_record(manifest)["events"].pop()
    raw = (json.dumps(manifest,ensure_ascii=False,indent=2)+"\n").encode()
    assert git_blob_sha(raw) == CI_AMEND_PUBLISHED_BLOB, "ci_amend_published_fixture_mismatch"
    return manifest


def ci_amend_historical_view(source_bytes: bytes, relative_path: str) -> bytes:
    """Pin the complete prior bytes once; old validators retain their own negative cases."""
    assert type(source_bytes) is bytes, "ci_amend_view_source_bytes"
    assert type(relative_path) is str and relative_path in CI_AMEND_SEALS, "ci_amend_view_path"
    marker = CI_AMEND_MARKER.encode(); separator = b"\n"+marker+b"\n"
    assert source_bytes.count(marker) == 1 and source_bytes.count(separator) == 1, "ci_amend_view_boundary"
    prefix,section = source_bytes.split(separator,1)
    assert git_blob_sha(prefix) == CI_AMEND_SEALS[relative_path]["prefix_blob"], "ci_amend_view_prefix_changed"
    assert hashlib.sha256(marker+b"\n"+section).hexdigest() == CI_AMEND_SEALS[relative_path]["section_sha256"], "ci_amend_view_section_changed"
    return prefix


def _ci_amend_test_record() -> dict:
    # The historical objects are borrowed read-only; only the tiny new event is copied.
    record = dict(CI_RESUME_RECORD)
    record["events"] = CI_RESUME_RECORD["events"] + [deepcopy(CI_AMEND_EVENT)]
    return record


def test_ci_amend_actual_current_state_and_both_detached_inverses() -> None:
    manifest=load_manifest(); before=json.dumps(manifest,sort_keys=True)
    validate_routing_registration(manifest); validate_execution_sequence(manifest)
    published=_ci_amend_published_inverse(manifest); stopped=validate_ci_amend_baseline(manifest)
    assert git_blob_sha((json.dumps(published,ensure_ascii=False,indent=2)+"\n").encode())==CI_AMEND_PUBLISHED_BLOB
    assert git_blob_sha((json.dumps(stopped,ensure_ascii=False,indent=2)+"\n").encode())==CI_RESUME_BASELINE_BLOB
    assert len(defensive_record(published)["events"])==28 and len(defensive_record(stopped)["events"])==27
    assert defensive_record(stopped)["events"]==CI_SCOPE_RECORD["events"]
    assert defensive_record(stopped)["events"][26]["owner_scope_decision"]["subject"]["repair_scope"]["implementation_authorized"] is False
    defensive_record(published)["events"][0]["type"]="MUTATED"
    assert json.dumps(manifest,sort_keys=True)==before
    assert defensive_record(stopped)["events"][0]["type"]!="MUTATED"
    assert historical_ci_resume_manifest()==historical_ci_resume_manifest()
    first=historical_ci_resume_manifest();second=historical_ci_resume_manifest()
    defensive_record(first)["events"][0]["type"]="MUTATED"
    assert defensive_record(second)["events"][0]["type"]!="MUTATED"


@pytest.mark.parametrize("path,value",[
    (("recorded_at",),"UNRESOLVED"),
    (("owner_ci_maintenance_decision","owner_approval_at"),"UNRESOLVED"),
    (("owner_ci_maintenance_decision","public_proposal_reference","role"),"OWNER_RECEIPT"),
    (("owner_ci_maintenance_decision","decision_record","section_sha256"),"0"*64),
    (("owner_ci_maintenance_decision","effect"),"GOVERNANCE_MERGE_ONLY"),
    (("owner_ci_maintenance_decision","effective_condition"),"GENERAL_IMMEDIATE_RESUME"),
    (("owner_ci_maintenance_decision","subject","previous_resume_event_index"),27.0),
    (("owner_ci_maintenance_decision","subject","published_unmerged_proposal_manifest_blob_sha"),"0"*40),
    (("owner_ci_maintenance_decision","subject","pending_resume28_ci_proposal_disposition"),"MERGED"),
    (("owner_ci_maintenance_decision","subject","immediately_authorized_scope","repository_root_paths"),[".github/workflows/*"]),
    (("owner_ci_maintenance_decision","subject","immediately_authorized_scope","package_root_paths"),["../.github/workflows/asie-ci.yml"]),
    (("owner_ci_maintenance_decision","subject","workflow_contract","job_timeout_minutes"),20),
    (("owner_ci_maintenance_decision","subject","workflow_contract","benchmark_step_timeout_minutes"),30),
    (("owner_ci_maintenance_decision","subject","workflow_contract","all_other_workflow_bytes_unchanged"),1),
    (("owner_ci_maintenance_decision","subject","application_execution_before_governance_merge_authorized"),0),
    (("owner_ci_maintenance_decision","subject","general_resume_condition"),"IMMEDIATE"),
    (("owner_ci_maintenance_decision","subject","authorization_expires_on"),"NEVER"),
    (("owner_ci_maintenance_decision","subject","future_ci_maintenance_authorized"),True),
])
def test_ci_amend_rejects_scope_receipt_purpose_budget_types_and_expiry(path: tuple,value: object) -> None:
    record=_ci_amend_test_record();target=record["events"][28]
    for key in path[:-1]:target=target[key]
    target[path[-1]]=value
    with pytest.raises(AssertionError,match="ci_amend_"):validate_ci_amend(record,DEFENSIVE_START_TARGET)


@pytest.mark.parametrize("mutation",("extra","missing","missing_event","prior_drift","slot"))
def test_ci_amend_closed_shape_history_and_slot(mutation: str) -> None:
    record=_ci_amend_test_record();active=DEFENSIVE_START_TARGET
    if mutation=="extra":record["events"][28]["unapproved"]=True
    elif mutation=="missing":record["events"][28].pop("recorded_at")
    elif mutation=="missing_event":record["events"].pop()
    elif mutation=="prior_drift":record["events"][27]=dict(record["events"][27],recorded_at="CHANGED")
    else:active=None
    with pytest.raises(AssertionError):validate_ci_amend(record,active)


@pytest.mark.parametrize("mutation",("program","held","old_receipt","new_effect"))
def test_ci_amend_current_seams_fail_closed(mutation: str) -> None:
    manifest=load_manifest()
    if mutation=="program":manifest["program_id"]="CHANGED"
    elif mutation=="held":manifest["execution_sequence"]["held_packages"]=[]
    elif mutation=="old_receipt":defensive_record(manifest)["events"][27]["owner_resume_decision"]["record_url"]="UNRESOLVED"
    else:defensive_record(manifest)["events"][28]["owner_ci_maintenance_decision"]["effect"]="GENERAL_RESUME"
    for validator in (validate_ci_amend_baseline,validate_routing_registration):
        with pytest.raises(AssertionError):validator(manifest)


@pytest.mark.parametrize("relative_path",tuple(CI_AMEND_SEALS))
@pytest.mark.parametrize("mutation",("valid","prefix","section","duplicate"))
def test_ci_amend_six_append_only_seals(relative_path: str,mutation: str) -> None:
    source=(Path(__file__).resolve().parents[1]/relative_path).read_bytes()
    if mutation=="valid":
        prior=ci_amend_historical_view(source,relative_path)
        if relative_path==CI_ACR_PATH:ci_scope_acr_historical_view(prior)
        else:ci_resume_historical_view(prior,relative_path)
        return
    if mutation=="prefix":source=b" "+source
    elif mutation=="section":source+=b" "
    else:source+=("\n"+CI_AMEND_MARKER+"\n").encode()
    with pytest.raises(AssertionError,match="ci_amend_view"):ci_amend_historical_view(source,relative_path)


def test_ci_amend_view_exact_types_paths_and_decision_binding() -> None:
    path=CI_ACR_PATH;raw=(Path(__file__).resolve().parents[1]/path).read_bytes()
    for bad in (None,False,0,raw.decode(),bytearray(raw)):
        with pytest.raises(AssertionError,match="ci_amend_view_source_bytes"):ci_amend_historical_view(bad,path)
    for bad in (None,"", "../"+path,".github/workflows/*"):
        with pytest.raises(AssertionError,match="ci_amend_view_path"):ci_amend_historical_view(raw,bad)
    decision=CI_AMEND_EVENT["owner_ci_maintenance_decision"]
    assert decision["decision_record"]["section_sha256"]==CI_AMEND_SEALS[path]["section_sha256"]
    assert decision["owner_approval_at"]!=CI_AMEND_EVENT["recorded_at"]
    workflow=(MANIFEST_PATH.parent/".github/workflows/asie-ci.yml").read_bytes()
    assert git_blob_sha(workflow)==CI_AMEND_WORKFLOW_BLOB


@pytest.mark.parametrize("warm",(False,True))
def test_ci_amend_new_source_drift_is_rejected_cold_and_warm(monkeypatch: pytest.MonkeyPatch,warm: bool) -> None:
    monkeypatch.setitem(globals(),"_CI_RESUME_HISTORY_BYTES",None)
    if warm:historical_ci_resume_manifest()
    cache=_CI_RESUME_HISTORY_BYTES;manifest=load_manifest()
    defensive_record(manifest)["events"][28]["owner_ci_maintenance_decision"]["subject"]["future_ci_maintenance_authorized"]=True
    changed=(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n").encode()
    monkeypatch.setattr(Path,"read_bytes",lambda _path:changed)
    with pytest.raises(AssertionError,match="ci_resume_fixture_source_changed"):historical_ci_resume_manifest()
    assert _CI_RESUME_HISTORY_BYTES is cache


def test_ci_amend_published_pending_proposal_cannot_be_current_authority() -> None:
    manifest=historical_ci_resume_manifest()
    for validator in (validate_ci_amend_baseline,validate_routing_registration,validate_execution_sequence):
        with pytest.raises(AssertionError,match="defensive_record_mismatch"):validator(manifest)
