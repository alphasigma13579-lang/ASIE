from __future__ import annotations

import json
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


# Program ordering is repository governance, never a runtime permission or lock.
# v1 intentionally admits no active target while routing entry controls are pending.
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
    assert sequence["schema"] == "asie.foundation.execution-sequence.v1", "sequence_schema"
    assert sequence["record_effect"] == "PRIORITY_AND_HOLD_ONLY", "sequence_effect"
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


def validate_routing_registration(manifest: dict) -> None:
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
    assert isinstance(slices, list) and len(slices) == 1, "missing_or_duplicate_slice"
    record = slices[0]
    assert isinstance(record, dict)
    assert set(record) == {
        "schema", "id", "state", "registry_effect", "execution_authorized",
        "scope_document", "owner_scope_decision", "package_entry_dependencies",
        "required_entry_controls", "closure_effect", "network_authorized",
        "provider_activation_authorized", "deployment_authorized",
    }, "unknown_or_missing_slice_field"
    assert record["schema"] == "asie.foundation.routing-registration.v1"
    assert record["id"] == "routing_repair"
    assert record["state"] == "REGISTERED_BLOCKED", "unapproved_slice_state"
    assert record["registry_effect"] == "REGISTRATION_ONLY"
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
        assert controls[control] == {
            "owner": owner, "status": "PENDING", "evidence": None,
        }, f"unapproved_control_claim:{control}"
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
    """Preserve unfinished package progress while all execution remains held."""
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
