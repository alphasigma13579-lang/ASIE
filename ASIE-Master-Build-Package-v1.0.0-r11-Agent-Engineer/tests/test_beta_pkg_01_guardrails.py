from __future__ import annotations

from pathlib import Path

from backend.dib_registry_admission import assert_all_frozen_files_unchanged

PACKAGE_ROOT = Path(__file__).resolve().parents[1]

FROZEN_RUNTIME_FILES = (
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
    "docs/ASIE-AAS-Runtime-Freeze-Manifest-v1.0.json",
)


def test_beta_pkg_01_artifacts_exist() -> None:
    assert (PACKAGE_ROOT / "backend/dataset_dib_mapping.py").is_file()
    assert (PACKAGE_ROOT / "docs/BETA-PKG-01-DATASET-TO-DIB-MAPPING-COMPLETION-2026-07-27.md").is_file()


def test_mapping_module_declares_no_raw_finance_bypass() -> None:
    text = (PACKAGE_ROOT / "backend/dataset_dib_mapping.py").read_text(encoding="utf-8")
    assert '"raw_input_finance_bypass_allowed": False' in text
    assert "finance_result_set(" not in text
    assert "finance_from_approved_manifest(" not in text


def test_mapping_module_uses_existing_dib_blueprint_builder() -> None:
    text = (PACKAGE_ROOT / "backend/dataset_dib_mapping.py").read_text(encoding="utf-8")
    assert "build_dynamic_input_blueprint" in text
    assert "map_intake_to_blueprint_items" in text
    assert 'MAPPING_CONTRACT_ID = "dataset.dib.mapping.v1"' in text


def test_package_document_preserves_frozen_runtime_boundary() -> None:
    document = (PACKAGE_ROOT / "docs/BETA-PKG-01-DATASET-TO-DIB-MAPPING-COMPLETION-2026-07-27.md").read_text(encoding="utf-8")
    assert "Frozen-runtime boundary" in document
    assert "This package does not modify" in document
    assert "the Runtime Freeze Manifest" in document
    assert_all_frozen_files_unchanged(PACKAGE_ROOT)
