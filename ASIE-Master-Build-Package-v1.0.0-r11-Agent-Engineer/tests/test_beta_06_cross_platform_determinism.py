from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from backend.dib_registry_admission import assert_all_frozen_files_unchanged
from tools.test_beta_06_determinism import (
    SCHEMA,
    build_vector,
    canonical_json_bytes,
    compare,
    emit,
)

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = PACKAGE_ROOT.parents[0] / ".github" / "workflows" / "test-beta-06-cross-platform-determinism.yml"
TOOL_PATH = PACKAGE_ROOT / "tools" / "test_beta_06_determinism.py"

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

TEST_BETA_06_ALLOWLIST = {
    ".github/workflows/test-beta-06-cross-platform-determinism.yml",
    "ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/tools/test_beta_06_determinism.py",
    "ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/tests/test_beta_06_cross_platform_determinism.py",
    "ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/docs/TEST-BETA-06-CROSS-PLATFORM-DETERMINISM-2026-07-29.md",
}


class TestBeta06CrossPlatformDeterminism(unittest.TestCase):
    def test_vector_is_byte_identical_across_repeated_generation(self) -> None:
        first = build_vector()
        second = build_vector()
        self.assertEqual(first, second)
        self.assertEqual(SCHEMA, first["schema"])
        self.assertEqual(first["vector_hash"], second["vector_hash"])
        self.assertEqual(canonical_json_bytes(first), canonical_json_bytes(second))

    def test_vector_covers_finance_sealed_outputs_and_snapshot_hashes(self) -> None:
        vector = build_vector()
        payload = vector["determinism_payload"]
        self.assertEqual("ready", payload["finance"]["status"])
        self.assertEqual(20260713, payload["finance"]["monte_carlo"]["seed"])
        self.assertEqual(4000, payload["finance"]["monte_carlo"]["iterations"])
        self.assertEqual(
            {
                "finance_result",
                "evidence_ledger",
                "sector_intelligence",
                "decision_result",
                "risk_result",
                "execution_result",
            },
            set(payload["sealed_output_hashes"]),
        )
        self.assertTrue(payload["snapshot"]["immutable"])
        self.assertEqual(payload["snapshot_content_hash"], payload["snapshot"]["content_hash"])
        self.assertEqual(payload["snapshot_integrity_hash"], payload["snapshot"]["integrity_hash"])
        self.assertTrue(all(payload["invariants"].values()))

    def test_emitted_json_is_utf8_lf_only_and_compare_accepts_identical_vectors(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for label in ("ubuntu-hash0", "ubuntu-hash7919", "windows-hash0", "windows-hash7919"):
                emit(root / label / "vector.json")
            compare(root)
            raw = (root / "windows-hash0" / "vector.json").read_bytes()
            self.assertTrue(raw.endswith(b"\n"))
            self.assertNotIn(b"\r\n", raw)
            decoded = json.loads(raw.decode("utf-8"))
            self.assertEqual(SCHEMA, decoded["schema"])

    def test_compare_fails_closed_on_single_byte_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            emit(root / "ubuntu" / "vector.json")
            emit(root / "windows" / "vector.json")
            path = root / "windows" / "vector.json"
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["vector_hash"] = "0" * 64
            path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
            with self.assertRaises(RuntimeError):
                compare(root)

    def test_workflow_declares_windows_linux_and_hash_seed_matrix(self) -> None:
        workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
        self.assertIn("ubuntu-latest", workflow)
        self.assertIn("windows-latest", workflow)
        self.assertIn('python-version: "3.12"', workflow)
        self.assertIn('hashseed: "0"', workflow)
        self.assertIn('hashseed: "7919"', workflow)
        self.assertIn("actions/upload-artifact@v4", workflow)
        self.assertIn("actions/download-artifact@v4", workflow)
        self.assertIn("compare --directory", workflow)
        self.assertIn("fail-fast: false", workflow)

    def test_tool_excludes_platform_and_absolute_path_material_from_vector(self) -> None:
        source = TOOL_PATH.read_text(encoding="utf-8")
        for forbidden in (
            "platform.system(",
            "sys.platform",
            "os.name",
            "Path.cwd()",
            "socket.gethostname(",
        ):
            self.assertNotIn(forbidden, source)
        vector_text = canonical_json_bytes(build_vector()).decode("utf-8")
        self.assertNotIn(str(PACKAGE_ROOT), vector_text)
        self.assertNotIn("\\\\", vector_text)

    def test_allowlist_excludes_frozen_runtime(self) -> None:
        package_relative_allowlist = {
            path.removeprefix("ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/")
            for path in TEST_BETA_06_ALLOWLIST
            if path.startswith("ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/")
        }
        self.assertTrue(package_relative_allowlist.isdisjoint(FROZEN_FILES))
        assert_all_frozen_files_unchanged(PACKAGE_ROOT)


if __name__ == "__main__":
    unittest.main()
