from __future__ import annotations

import json
import unittest
from pathlib import Path

from backend.dib_registry_admission import assert_all_frozen_files_unchanged


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PACKAGE_ROOT.parent
PROGRAM_DOC = (
    PACKAGE_ROOT
    / "docs"
    / "PROGRAM-CLOSE-10-EMERGENCY-REMEDIATION-CONSOLIDATION-AND-REBASELINE-2026-07-29.md"
)
PROGRAM_DOC_NAME = PROGRAM_DOC.name


class ProgramClose10RepositoryRebaselineTests(unittest.TestCase):
    def test_single_current_program_state_is_linked_from_entrypoints(self) -> None:
        self.assertTrue(PROGRAM_DOC.exists())
        program = PROGRAM_DOC.read_text(encoding="utf-8")
        self.assertIn("AUTHORITATIVE CURRENT PROGRAM STATE", program)
        self.assertIn("69b39d5a9a3050b7294a40e3441e4a6e69874fab", program)
        self.assertIn("Public beta | Not authorized", program)
        self.assertIn("Production deployment | Not authorized", program)
        self.assertIn("External network/fetch | Not authorized", program)

        entrypoints = (
            REPOSITORY_ROOT / "README.md",
            REPOSITORY_ROOT / "AGENTS.md",
            PACKAGE_ROOT / "AGENTS.md",
            PACKAGE_ROOT / "docs" / "INDEX.md",
            PACKAGE_ROOT / "docs" / "EKB" / "EKB-02-Source-of-Truth-Matrix.md",
            PACKAGE_ROOT / "docs" / "EKB" / "EKB-04-Agent-Reading-Order.md",
        )
        for path in entrypoints:
            self.assertIn(PROGRAM_DOC_NAME, path.read_text(encoding="utf-8"), str(path))

    def test_machine_marker_keeps_external_and_public_authority_disabled(self) -> None:
        marker = json.loads(
            (REPOSITORY_ROOT / "EMERGENCY-RELEASE-FREEZE.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(marker["status"], "CLEARED")
        self.assertEqual(marker["decision"], "PENDING_GATE")
        transition = marker["controlled_unfreeze"]
        self.assertIs(transition["public_release_authorized"], False)
        self.assertIs(transition["external_network_authorized"], False)
        self.assertIs(transition["provider_activation_authorized"], False)

    def test_general_ci_collects_unittest_and_pytest_style_tests(self) -> None:
        workflow = (
            REPOSITORY_ROOT / ".github" / "workflows" / "asie-ci.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("python -m pytest -q", workflow)
        self.assertNotIn("python -m unittest discover -s tests", workflow)

    def test_external_sync_is_manual_and_marker_authorized(self) -> None:
        workflow = (
            REPOSITORY_ROOT / ".github" / "workflows" / "vision2030-kb-sync.yml"
        ).read_text(encoding="utf-8")
        self.assertNotIn("schedule:", workflow)
        self.assertIn("authorization_commit", workflow)
        self.assertIn("external_network_authorized", workflow)
        self.assertIn("provider_activation_authorized", workflow)
        self.assertIn("git rev-parse origin/main", workflow)

    def test_production_deploy_requires_exact_commit_evidence_and_authority(self) -> None:
        workflow = (
            REPOSITORY_ROOT / ".github" / "workflows" / "deploy-hostinger.yml"
        ).read_text(encoding="utf-8")
        for token in (
            "release_commit",
            "release_evidence_run_id",
            "public_release_authorized",
            "production_deployment_authorized",
            "git rev-parse origin/main",
            'git checkout --detach "$ASIE_RELEASE_COMMIT"',
        ):
            self.assertIn(token, workflow)

    def test_handoff_payload_remains_marker_only_without_deletion(self) -> None:
        shell = PACKAGE_ROOT / "ASIE-Next-Task-Handoff-2026-07-19-v1.0.0"
        self.assertTrue(shell.is_dir())
        entries = sorted(path.name for path in shell.iterdir())
        self.assertEqual(entries, ["QUARANTINE-LOCKED.md"])
        marker = (shell / "QUARANTINE-LOCKED.md").read_text(encoding="utf-8")
        self.assertIn("QUARANTINE LOCKED", marker)

    def test_program_close_does_not_mutate_frozen_runtime_files(self) -> None:
        assert_all_frozen_files_unchanged(PACKAGE_ROOT)


if __name__ == "__main__":
    unittest.main()
