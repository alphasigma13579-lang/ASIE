from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


REMOVED_CHECKSUM_STUBS = [
    "ASIE-Next-Task-Handoff-2026-07-19-v1.0.0.zip.sha256.txt",
    "ASIE-Architecture-Correction-Archive-2026-07-18-v1.0.0.zip.sha256.txt",
    "ASIE-Architecture-Correction-Archive-2026-07-19-v1.1.0.zip.sha256.txt",
    "ASIE-Architecture-Correction-Archive-2026-07-19-v1.1.1.zip.sha256.txt",
]


REQUIRED_QUARANTINE_MARKERS = [
    "docs/reference/ARCHIVE-LOCKDOWN.md",
    "docs/reference/r11-workspace-materials/QUARANTINE-LOCKED.md",
    "docs/reference/r11-workspace-materials/workspace-bundles/QUARANTINE-LOCKED.md",
    "docs/EKB/EKB-07-Archive-Quarantine-Map.md",
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


def test_r3a_removed_only_archive_checksum_stubs():
    for rel_path in REMOVED_CHECKSUM_STUBS:
        assert not (ROOT / rel_path).exists(), rel_path


def test_r3a_quarantine_markers_remain_present():
    for rel_path in REQUIRED_QUARANTINE_MARKERS:
        path = ROOT / rel_path
        assert path.exists(), rel_path
        text = _read(path)
        assert "ARCHIVE" in text or "QUARANTINE" in text


def test_r3a_execution_record_documents_boundary():
    record = ROOT / "docs/REPOSITORY-SURGERY-R3A-STUB-CLEANUP-2026-07-26.md"
    assert record.exists()
    text = _read(record)
    assert "checksum stubs only" in text
    assert "does not delete archive bundles" in text
    assert "AAS Runtime Freeze" in text
    assert "DIB runtime" in text
    assert "Finance" in text
    assert "Snapshot" in text
    assert "AI Provider" in text
    assert "external-network" in text


def test_r3a_does_not_mark_frozen_runtime_files_as_archive():
    for rel_path in FROZEN_RUNTIME_FILES:
        path = ROOT / rel_path
        assert path.exists(), rel_path
        text = _read(path)
        assert "QUARANTINE LOCKED" not in text
        assert "ARCHIVE_LOCKED" not in text
