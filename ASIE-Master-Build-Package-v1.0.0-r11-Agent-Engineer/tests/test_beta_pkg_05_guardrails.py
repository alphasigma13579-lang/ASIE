from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

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


def test_beta_gate_does_not_import_controlled_execution_modules() -> None:
    source = (ROOT / "backend/beta_release_gate.py").read_text(encoding="utf-8")
    prohibited = (
        "finance_result_set",
        "snapshot_assembly",
        "ProjectRunWorkflow",
        "DecisionCouncil",
        "ASIE_ALLOW_EXTERNAL_FETCH=true",
    )
    assert not any(token in source for token in prohibited)


def test_workflow_uses_production_environment_and_canonical_secrets() -> None:
    source = (ROOT.parent / ".github/workflows/beta-release-gate.yml").read_text(encoding="utf-8")
    assert "environment: production" in source
    for secret in (
        "DEEPSEEK_API_KEY",
        "TAVILY_API_KEY",
        "GOOGLE_MAPS_API_KEY",
        "PINECONE_API_KEY",
    ):
        assert f"secrets.{secret}" in source
    assert "workflow_dispatch" in source


def test_package_scope_contains_no_frozen_runtime_copy() -> None:
    package_paths = {
        "backend/beta_release_gate.py",
        "tests/test_beta_release_gate.py",
        "tests/test_beta_pkg_05_guardrails.py",
        "docs/BETA-PKG-05-BETA-RELEASE-GATE-2026-07-28.md",
    }
    assert package_paths.isdisjoint(FROZEN_FILES)
