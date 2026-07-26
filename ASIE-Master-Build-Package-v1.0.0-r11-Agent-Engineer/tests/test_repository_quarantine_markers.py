from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


REQUIRED_MARKERS = [
    "docs/EKB/EKB-07-Archive-Quarantine-Map.md",
    "docs/reference/r11-workspace-materials/QUARANTINE-LOCKED.md",
    "docs/reference/r11-workspace-materials/workspace-bundles/QUARANTINE-LOCKED.md",
    "docs/reference/r11-workspace-materials/workspace-bundles/ASIE-Architecture-Correction-Archive-2026-07-18-v1.0.0/QUARANTINE-LOCKED.md",
    "docs/reference/r11-workspace-materials/workspace-bundles/ASIE-Architecture-Correction-Archive-2026-07-19-v1.1.0/QUARANTINE-LOCKED.md",
    "docs/reference/r11-workspace-materials/workspace-bundles/ASIE-Architecture-Correction-Archive-2026-07-19-v1.1.1/QUARANTINE-LOCKED.md",
    "docs/reference/r11-workspace-materials/workspace-bundles/ASIE-Next-Task-Handoff-2026-07-19-v1.0.0/QUARANTINE-LOCKED.md",
    "ASIE-Next-Task-Handoff-2026-07-19-v1.0.0/QUARANTINE-LOCKED.md",
]


FORBIDDEN_LIVE_REFERENCES = [
    "docs/reference/r11-workspace-materials/workspace-bundles/ASIE-Architecture-Correction-Archive-2026-07-18-v1.0.0",
    "docs/reference/r11-workspace-materials/workspace-bundles/ASIE-Architecture-Correction-Archive-2026-07-19-v1.1.0",
    "docs/reference/r11-workspace-materials/workspace-bundles/ASIE-Architecture-Correction-Archive-2026-07-19-v1.1.1",
    "docs/reference/r11-workspace-materials/workspace-bundles/ASIE-Next-Task-Handoff-2026-07-19-v1.0.0",
    "ASIE-Next-Task-Handoff-2026-07-19-v1.0.0",
]


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


def test_repository_surgery_r2_quarantine_markers_exist():
    for rel_path in REQUIRED_MARKERS:
        marker = ROOT / rel_path
        assert marker.exists(), rel_path
        content = _read(marker)
        assert "QUARANTINE LOCKED" in content or "Archive Quarantine" in content
        assert "Do not copy" in content or "not be used" in content or "Forbidden" in content


def test_quarantine_map_declares_r3_candidates_and_no_deletion_in_r2():
    content = _read(ROOT / "docs/EKB/EKB-07-Archive-Quarantine-Map.md")
    assert "R2 does not delete files" in content
    assert "R3 Compaction Candidates" in content
    assert "DANGEROUS_DUPLICATE" in content
    assert "Hard Prohibitions" in content
    assert "AAS Freeze" in content


def test_live_runtime_paths_do_not_reference_quarantined_bundles():
    for scan_root in LIVE_SCAN_ROOTS:
        assert scan_root.exists(), scan_root
        for path in scan_root.rglob("*"):
            if not path.is_file() or path.suffix not in {".py", ".ts", ".tsx", ".json"}:
                continue
            text = _read(path)
            for forbidden in FORBIDDEN_LIVE_REFERENCES:
                assert forbidden not in text, f"{path} references quarantined archive {forbidden}"


def test_r2_does_not_modify_frozen_runtime_policy_files():
    # R2 is a quarantine-marker package. Frozen runtime files must remain live-policy protected
    # and are not expected to contain quarantine markers.
    for rel_path in FROZEN_RUNTIME_FILES:
        path = ROOT / rel_path
        assert path.exists(), rel_path
        text = _read(path)
        assert "QUARANTINE LOCKED" not in text
        assert "ARCHIVE_LOCKED" not in text
