from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


REMOVED_TARGET = (
    "docs/reference/r11-workspace-materials/workspace-bundles/"
    "ASIE-Architecture-Correction-Archive-2026-07-19-v1.1.1"
)

PRESERVED_TARGETS = [
    "docs/reference/r11-workspace-materials/QUARANTINE-LOCKED.md",
    "docs/reference/r11-workspace-materials/workspace-bundles/QUARANTINE-LOCKED.md",
    "docs/reference/r11-workspace-materials/workspace-bundles/ASIE-Next-Task-Handoff-2026-07-19-v1.0.0/QUARANTINE-LOCKED.md",
]

FORBIDDEN_LIVE_ROOTS = [
    ROOT / "backend",
    ROOT / "src",
    ROOT / "registry",
]

FROZEN_RUNTIME_FILES = [
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


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_r3e_removed_only_v111_correction_archive_bundle():
    assert not (ROOT / REMOVED_TARGET).exists()
    for rel_path in PRESERVED_TARGETS:
        assert (ROOT / rel_path).exists(), rel_path


def test_r3e_execution_record_declares_boundaries():
    record = _read(ROOT / "docs/REPOSITORY-SURGERY-R3E-ARCHIVE-V111-REMOVAL-2026-07-27.md")
    assert "R3E" in record
    assert REMOVED_TARGET in record
    assert "docs/reference" in record
    assert "DIB runtime" in record
    assert "AAS Runtime Freeze" in record
    assert "external-network behavior" in record
    assert "does not" in record


def test_ekb07_records_r3e_completed_removal():
    ekb = _read(ROOT / "docs/EKB/EKB-07-Archive-Quarantine-Map.md")
    assert "R3E" in ekb
    assert REMOVED_TARGET in ekb
    assert "Completed R3 Compaction / Removal" in ekb
    assert "Remaining R3 Compaction Candidates" in ekb


def test_r3e_does_not_reference_removed_archive_from_live_paths():
    for root in FORBIDDEN_LIVE_ROOTS:
        assert root.exists(), root
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix not in {".py", ".ts", ".tsx", ".json"}:
                continue
            assert REMOVED_TARGET not in _read(path), path


def test_r3e_does_not_modify_frozen_runtime_files_with_archive_markers():
    for rel_path in FROZEN_RUNTIME_FILES:
        path = ROOT / rel_path
        assert path.exists(), rel_path
        text = _read(path)
        assert "QUARANTINE LOCKED" not in text
        assert "ARCHIVE_LOCKED" not in text
