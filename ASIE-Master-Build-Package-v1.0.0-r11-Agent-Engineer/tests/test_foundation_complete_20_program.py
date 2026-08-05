from __future__ import annotations

import json
import re
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
    assert fc20_05["state"] == "ACR_REQUIRED"
    assert fc20_05["acr"] is True
    assert all(packages[dependency]["state"] == "COMPLETE" for dependency in fc20_05["depends_on"])
    assert manifest["current_release_verdict"] == "BLOCK"
    assert manifest["external_network_authorized"] is False
    assert manifest["provider_activation_authorized"] is False
    assert manifest["public_release_authorized"] is False
