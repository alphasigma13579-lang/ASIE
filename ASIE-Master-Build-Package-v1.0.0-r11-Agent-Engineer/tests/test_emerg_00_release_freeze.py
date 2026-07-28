from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from types import ModuleType

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PACKAGE_ROOT.parent
GUARD_PATH = PACKAGE_ROOT / "tools/enforce_release_freeze.py"
MARKER_PATH = REPOSITORY_ROOT / "EMERGENCY-RELEASE-FREEZE.json"
WORKFLOW_PATH = REPOSITORY_ROOT / ".github/workflows/beta-release-gate.yml"

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

EMERG_00_ALLOWLIST = {
    "../EMERGENCY-RELEASE-FREEZE.json",
    "../.github/workflows/beta-release-gate.yml",
    "../SECURITY.md",
    "tools/enforce_release_freeze.py",
    "tests/test_emerg_00_release_freeze.py",
    "docs/EMERG-00-RELEASE-FREEZE-AND-EXPOSURE-CONTAINMENT-2026-07-29.md",
}


def load_guard_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("asie_emergency_release_freeze", GUARD_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("release_freeze_guard_import_failed")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class EmergencyReleaseFreezeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.guard = load_guard_module()

    def write_marker(self, payload: object) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        marker_path = Path(temp_dir.name) / "freeze.json"
        marker_path.write_text(json.dumps(payload), encoding="utf-8")
        return marker_path

    def test_active_freeze_blocks_release_gate_execution(self) -> None:
        marker_path = self.write_marker(
            {
                "schema": "asie.release.freeze.v1",
                "status": "ACTIVE",
                "release_gate_allowed": False,
                "baseline_commit": "8978231e190b8ccc2be59ec46acf50d6268cd41f",
                "reason_codes": ["production_bootstrap_takeover"],
            }
        )

        self.assertEqual(self.guard.enforce_release_freeze(marker_path), self.guard.BLOCKED_EXIT_CODE)

    def test_missing_or_invalid_marker_fails_closed(self) -> None:
        missing_path = Path(tempfile.gettempdir()) / "asie-release-freeze-missing.json"
        if missing_path.exists():
            missing_path.unlink()
        self.assertEqual(self.guard.enforce_release_freeze(missing_path), self.guard.BLOCKED_EXIT_CODE)

        invalid_path = self.write_marker(["not", "a", "mapping"])
        self.assertEqual(self.guard.enforce_release_freeze(invalid_path), self.guard.BLOCKED_EXIT_CODE)

    def test_gate_opens_only_for_explicit_cleared_marker(self) -> None:
        marker_path = self.write_marker(
            {
                "schema": "asie.release.freeze.v1",
                "status": "CLEARED",
                "release_gate_allowed": True,
            }
        )
        self.assertEqual(self.guard.enforce_release_freeze(marker_path), 0)

    def test_repository_marker_records_active_no_go_baseline(self) -> None:
        marker = json.loads(MARKER_PATH.read_text(encoding="utf-8"))
        self.assertEqual(marker["schema"], "asie.release.freeze.v1")
        self.assertEqual(marker["status"], "ACTIVE")
        self.assertEqual(marker["decision"], "NO_GO")
        self.assertFalse(marker["release_gate_allowed"])
        self.assertEqual(marker["baseline_commit"], "8978231e190b8ccc2be59ec46acf50d6268cd41f")
        self.assertIn("production_bootstrap_takeover", marker["reason_codes"])
        self.assertIn("dib_cross_tenant_access", marker["reason_codes"])

    def test_workflow_enforces_freeze_before_beta_evaluator(self) -> None:
        workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
        guard_command = "python tools/enforce_release_freeze.py --marker ../EMERGENCY-RELEASE-FREEZE.json"
        evaluator_command = "python -m backend.beta_release_gate"
        self.assertIn(guard_command, workflow)
        self.assertIn(evaluator_command, workflow)
        self.assertLess(workflow.index(guard_command), workflow.index(evaluator_command))

    def test_emerg_00_allowlist_excludes_frozen_runtime(self) -> None:
        normalized_allowlist = {path.removeprefix("../") for path in EMERG_00_ALLOWLIST}
        self.assertTrue(normalized_allowlist.isdisjoint(FROZEN_FILES))


if __name__ == "__main__":
    unittest.main()
