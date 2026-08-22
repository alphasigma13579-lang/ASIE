from __future__ import annotations

import json
import re
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
REPOSITORY_ROOT = PACKAGE_ROOT.parent
WORKFLOW_PATH = REPOSITORY_ROOT / ".github" / "workflows" / "test-beta-06-cross-platform-determinism.yml"
GITATTRIBUTES_PATH = REPOSITORY_ROOT / ".gitattributes"
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
    ".gitattributes",
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

    def test_repository_declares_canonical_text_line_endings(self) -> None:
        attributes = GITATTRIBUTES_PATH.read_text(encoding="utf-8")
        self.assertIn("* text=auto eol=lf", attributes)
        self.assertIn("*.png binary", attributes)
        self.assertIn("*.pdf binary", attributes)
        self.assertIn("*.sqlite3 binary", attributes)

    def test_workflow_declares_windows_linux_and_hash_seed_matrix(self) -> None:
        workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
        self.assertIn("ubuntu-latest", workflow)
        self.assertIn("windows-latest", workflow)
        self.assertIn('python-version: "3.12"', workflow)
        self.assertIn('hashseed: "0"', workflow)
        self.assertIn('hashseed: "7919"', workflow)
        self.assertIn("core.longpaths true", workflow)
        self.assertIn("core.autocrlf false", workflow)
        self.assertIn("core.eol lf", workflow)
        expected_actions = {
            "actions/checkout":
                "11d5960a326750d5838078e36cf38b85af677262",
            "actions/setup-python":
                "a26af69be951a213d495a4c3e4e4022e16d87065",
            "actions/download-artifact":
                "d3f86a106a0bac45b974a628896c90dbdf5c8093",
            "actions/upload-artifact":
                "ea165f8d65b6e75b540449e92b4886f43607fa02",
        }
        uses = re.findall(r"^\s*uses:\s*([^\s#]+)", workflow, re.MULTILINE)
        self.assertTrue(uses)
        for action_ref in uses:
            action, separator, commit_sha = action_ref.partition("@")
            self.assertEqual(separator, "@")
            self.assertIn(action, expected_actions)
            self.assertEqual(commit_sha, expected_actions[action])
            self.assertRegex(commit_sha, r"^[0-9a-f]{40}$")
        self.assertNotIn("Install C3C vector test dependency", workflow)
        self.assertNotIn("python -m pip install", workflow)
        self.assertIn(
            "scripts/finance_v2_sensitivity_cross_platform.py emit "
            "--output artifacts/${{ matrix.label }}/c3c-sensitivity.json",
            workflow,
        )
        self.assertIn(
            "scripts/finance_v2_sensitivity_cross_platform.py compare "
            "--directory test-beta-06-evidence",
            workflow,
        )
        self.assertIn(
            "      - name: Show comparison evidence\n"
            "        if: always()",
            workflow,
        )
        self.assertIn(
            "      - name: Upload combined TEST-BETA-06 evidence\n"
            "        if: always()",
            workflow,
        )
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
