from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


REMOVED_TARGET = (
    "docs/reference/r11-workspace-materials/workspace-bundles/"
    "ASIE-Architecture-Correction-Archive-2026-07-19-v1.1.0"
)

PRESERVED_TARGETS = [
    "docs/reference/r11-workspace-materials/QUARANTINE-LOCKED.md",
    "docs/reference/r11-workspace-materials/workspace-bundles/QUARANTINE-LOCKED.md",
]

LATER_REMOVED_TARGETS = [
    "docs/reference/r11-workspace-materials/workspace-bundles/ASIE-Architecture-Correction-Archive-2026-07-19-v1.1.1/QUARANTINE-LOCKED.md",
    "docs/reference/r11-workspace-materials/workspace-bundles/ASIE-Next-Task-Handoff-2026-07-19-v1.0.0/QUARANTINE-LOCKED.md",
]

LIVE_RUNTIME_FILES = [
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
]


R3D_RECORD = "docs/REPOSITORY-SURGERY-R3D-ARCHIVE-V110-REMOVAL-2026-07-27.md"
EKB_07 = "docs/EKB/EKB-07-Archive-Quarantine-Map.md"


def _read(rel_path: str) -> str:
    return (ROOT / rel_path).read_text(encoding="utf-8")


def test_r3d_removed_only_v110_archive_bundle():
    assert not (ROOT / REMOVED_TARGET).exists(), REMOVED_TARGET


def test_final_r3_state_preserves_root_markers_and_removes_later_targets():
    for rel_path in PRESERVED_TARGETS:
        path = ROOT / rel_path
        assert path.exists(), rel_path
        text = path.read_text(encoding="utf-8").casefold()
        assert "quarantine" in text or "archive" in text
    for rel_path in LATER_REMOVED_TARGETS:
        assert not (ROOT / rel_path).exists(), rel_path


def test_r3d_execution_record_documents_boundary():
    text = _read(R3D_RECORD)
    assert "R3D EXECUTION RECORD" in text
    assert "ASIE-Architecture-Correction-Archive-2026-07-19-v1.1.0" in text
    assert "file_count: 49" in text
    assert "does not" in text.casefold()
    assert "AAS Runtime Freeze" in text
    assert "DIB runtime" in text
    assert "Finance" in text
    assert "Snapshot" in text
    assert "AI Provider" in text
    assert "external-network" in text


def test_r3d_quarantine_map_records_completion_and_remaining_candidates():
    text = _read(EKB_07)
    assert "R3D" in text
    assert "ASIE-Architecture-Correction-Archive-2026-07-19-v1.1.0" in text
    assert "Completed R3 Compaction / Removal" in text
    assert "ASIE-Architecture-Correction-Archive-2026-07-19-v1.1.1" in text
    assert "Remaining R3 Compaction Candidates" in text


def test_r3d_does_not_modify_live_runtime_files_as_archive():
    for rel_path in LIVE_RUNTIME_FILES:
        path = ROOT / rel_path
        assert path.exists(), rel_path
        text = path.read_text(encoding="utf-8")
        assert "QUARANTINE LOCKED" not in text
        assert "ARCHIVE_LOCKED" not in text
