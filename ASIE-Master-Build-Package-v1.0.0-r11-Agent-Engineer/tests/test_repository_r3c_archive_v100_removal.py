from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


REMOVED_ARCHIVE = (
    "docs/reference/r11-workspace-materials/workspace-bundles/"
    "ASIE-Architecture-Correction-Archive-2026-07-18-v1.0.0"
)

RETAINED_ARCHIVES = [
    "docs/reference/r11-workspace-materials/workspace-bundles/ASIE-Architecture-Correction-Archive-2026-07-19-v1.1.0/QUARANTINE-LOCKED.md",
    "docs/reference/r11-workspace-materials/workspace-bundles/ASIE-Architecture-Correction-Archive-2026-07-19-v1.1.1/QUARANTINE-LOCKED.md",
    "docs/reference/r11-workspace-materials/workspace-bundles/ASIE-Next-Task-Handoff-2026-07-19-v1.0.0/QUARANTINE-LOCKED.md",
]

ROOT_MARKERS = [
    "docs/reference/ARCHIVE-LOCKDOWN.md",
    "docs/reference/r11-workspace-materials/QUARANTINE-LOCKED.md",
    "docs/reference/r11-workspace-materials/workspace-bundles/QUARANTINE-LOCKED.md",
]

FROZEN_RUNTIME_FILES = [
    "backend/aas_kernel.py",
    "backend/heart_controller.py",
    "backend/bus_controller.py",
    "backend/system_bus.py",
    "backend/socket_contracts.py",
    "backend/module_runtime.py",
    "backend/project_run_workflow.py",
    "backend/snapshot_assembly.py",
    "backend/runtime_freeze.py",
]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_r3c_removed_only_target_archive_directory():
    assert not (ROOT / REMOVED_ARCHIVE).exists()


def test_r3c_retains_later_quarantined_bundles_and_root_markers():
    for rel_path in ROOT_MARKERS + RETAINED_ARCHIVES:
        marker = ROOT / rel_path
        assert marker.exists(), rel_path
        text = _read(marker)
        assert "QUARANTINE" in text or "ARCHIVE" in text


def test_r3c_execution_record_documents_boundary():
    record = ROOT / "docs/REPOSITORY-SURGERY-R3C-ARCHIVE-V100-REMOVAL-2026-07-26.md"
    assert record.exists()
    text = _read(record)
    assert REMOVED_ARCHIVE in text
    assert "R3C removes one quarantined reference bundle only" in text
    assert "does not" in text
    assert "AAS Runtime Freeze" in text
    assert "DIB runtime" in text
    assert "Finance" in text
    assert "Snapshot" in text
    assert "AI Provider" in text
    assert "external-network" in text


def test_r3c_updates_ekb07_completed_removal_state():
    text = _read(ROOT / "docs/EKB/EKB-07-Archive-Quarantine-Map.md")
    assert "Completed R3 Compaction / Removal" in text
    assert "R3C" in text
    assert REMOVED_ARCHIVE in text
    assert "ASIE-Architecture-Correction-Archive-2026-07-19-v1.1.0" in text
    assert "ASIE-Architecture-Correction-Archive-2026-07-19-v1.1.1" in text


def test_r3c_does_not_mark_frozen_runtime_files_as_archive():
    for rel_path in FROZEN_RUNTIME_FILES:
        path = ROOT / rel_path
        assert path.exists(), rel_path
        text = _read(path)
        assert "QUARANTINE LOCKED" not in text
        assert "ARCHIVE_LOCKED" not in text
