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
    assert parent["depends_on"] == ["FC20-08", "FC20-09", "FC20-11"]
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
    assert packages["FC20-16"]["state"] == "BLOCKED_BY_PREDECESSOR"
    assert set(packages["FC20-16"]["depends_on"]) == REQUIRED_PACKAGE_IDS - {"FC20-16"}
    assert sum(package["state"] == "IN_PROGRESS" for package in packages.values()) <= 1
    assert set(manifest["frozen_files"]) == EXPECTED_FROZEN_FILES
    assert manifest["rules"]["frozen_runtime_changes_require_separate_acr"] is True
    assert manifest["current_release_verdict"] == "BLOCK"
    for key in (
        "public_release_authorized", "external_network_authorized",
        "provider_activation_authorized",
    ):
        assert manifest[key] is False


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


@pytest.mark.parametrize("mutation", [
    "duplicate_slice", "other_owner", "parent_state", "parent_dependencies",
    "entry_incomplete", "release_state", "release_authority", "second_active_package",
])
def test_routing_registration_preserves_program_boundaries(mutation: str) -> None:
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
    with pytest.raises(AssertionError):
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
