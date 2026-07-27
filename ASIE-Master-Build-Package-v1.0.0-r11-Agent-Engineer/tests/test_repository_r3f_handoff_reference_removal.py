from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

REMOVED_HANDOFF_REFERENCE_BUNDLE = (
    ROOT
    / "docs/reference/r11-workspace-materials/workspace-bundles/ASIE-Next-Task-Handoff-2026-07-19-v1.0.0"
)

PRESERVED_ROOT_MARKERS = [
    ROOT / "docs/reference/r11-workspace-materials/QUARANTINE-LOCKED.md",
    ROOT / "docs/reference/r11-workspace-materials/workspace-bundles/QUARANTINE-LOCKED.md",
]

R3F_RECORD = ROOT / "docs/REPOSITORY-SURGERY-R3F-HANDOFF-REFERENCE-REMOVAL-2026-07-27.md"
EKB_07 = ROOT / "docs/EKB/EKB-07-Archive-Quarantine-Map.md"

LIVE_POLICY_FILES = [
    ROOT / "backend/aas_kernel.py",
    ROOT / "backend/heart_controller.py",
    ROOT / "backend/bus_controller.py",
    ROOT / "backend/system_bus.py",
    ROOT / "backend/socket_contracts.py",
    ROOT / "backend/module_runtime.py",
    ROOT / "backend/project_run_workflow.py",
    ROOT / "backend/snapshot_assembly.py",
    ROOT / "backend/runtime_freeze.py",
]

LIVE_SCAN_ROOTS = [
    ROOT / "backend",
    ROOT / "src",
    ROOT / "registry",
]

FORBIDDEN_REMOVED_REFERENCE = (
    "docs/reference/r11-workspace-materials/workspace-bundles/"
    "ASIE-Next-Task-Handoff-2026-07-19-v1.0.0"
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_r3f_reference_handoff_bundle_is_removed():
    assert not REMOVED_HANDOFF_REFERENCE_BUNDLE.exists()


def test_r3f_root_quarantine_markers_are_preserved():
    for marker in PRESERVED_ROOT_MARKERS:
        assert marker.exists(), marker
        content = _read(marker)
        assert "QUARANTINE LOCKED" in content or "Archive Quarantine" in content


def test_r3f_execution_record_and_ekb_are_consistent():
    assert R3F_RECORD.exists()
    record = _read(R3F_RECORD)
    assert "R3F" in record
    assert "Reference-copy Next Task Handoff" in record
    assert "No live runtime file is changed" in record

    ekb = _read(EKB_07)
    assert "R3F" in ekb
    assert FORBIDDEN_REMOVED_REFERENCE in ekb
    assert "Completed R3 Compaction / Removal" in ekb


def test_r3f_live_runtime_files_are_not_quarantine_marked():
    for path in LIVE_POLICY_FILES:
        assert path.exists(), path
        text = _read(path)
        assert "QUARANTINE LOCKED" not in text
        assert "ARCHIVE_LOCKED" not in text


def test_r3f_live_paths_do_not_reference_removed_reference_bundle():
    for scan_root in LIVE_SCAN_ROOTS:
        assert scan_root.exists(), scan_root
        for path in scan_root.rglob("*"):
            if not path.is_file() or path.suffix not in {".py", ".ts", ".tsx", ".json"}:
                continue
            assert FORBIDDEN_REMOVED_REFERENCE not in _read(path)
