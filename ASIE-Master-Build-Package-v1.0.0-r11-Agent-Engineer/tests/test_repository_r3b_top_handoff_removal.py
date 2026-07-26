from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

REMOVED_TOP_LEVEL_HANDOFF = "ASIE-Next-Task-Handoff-2026-07-19-v1.0.0"

REFERENCE_HANDOFF_MARKER = (
    "docs/reference/r11-workspace-materials/workspace-bundles/"
    "ASIE-Next-Task-Handoff-2026-07-19-v1.0.0/QUARANTINE-LOCKED.md"
)

LIVE_SCAN_ROOTS = [
    ROOT / "backend",
    ROOT / "src",
    ROOT / "registry",
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


def test_r3b_top_level_handoff_archive_is_removed():
    assert not (ROOT / REMOVED_TOP_LEVEL_HANDOFF).exists()


def test_r3b_reference_copy_remains_quarantined_for_provenance():
    marker = ROOT / REFERENCE_HANDOFF_MARKER
    assert marker.exists()
    text = _read(marker)
    assert "QUARANTINE LOCKED" in text
    assert "DANGEROUS_DUPLICATE_BUNDLE" in text
    assert "historical continuity material" in text


def test_r3b_execution_record_documents_boundary():
    record = ROOT / "docs/REPOSITORY-SURGERY-R3B-TOP-HANDOFF-REMOVAL-2026-07-26.md"
    assert record.exists()
    text = _read(record)
    assert "TOP_LEVEL_HANDOFF_ARCHIVE" in text
    assert "does not" in text
    assert "AAS Runtime Freeze" in text
    assert "DIB runtime" in text
    assert "Finance" in text
    assert "Snapshot" in text
    assert "AI Provider" in text
    assert "external-network" in text


def test_r3b_live_runtime_paths_do_not_reference_removed_top_level_handoff():
    for scan_root in LIVE_SCAN_ROOTS:
        assert scan_root.exists(), scan_root
        for path in scan_root.rglob("*"):
            if not path.is_file() or path.suffix not in {".py", ".ts", ".tsx", ".json"}:
                continue
            assert REMOVED_TOP_LEVEL_HANDOFF not in _read(path), path


def test_r3b_does_not_mark_frozen_runtime_files_as_archive():
    for rel_path in FROZEN_RUNTIME_FILES:
        path = ROOT / rel_path
        assert path.exists(), rel_path
        text = _read(path)
        assert "QUARANTINE LOCKED" not in text
        assert "ARCHIVE_LOCKED" not in text
