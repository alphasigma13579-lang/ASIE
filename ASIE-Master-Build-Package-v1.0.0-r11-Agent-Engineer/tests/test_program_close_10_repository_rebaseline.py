from __future__ import annotations

import json
import hashlib
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


def validate_ci_timeout_amendment(source: bytes) -> None:
    """Only the approved single-job 20-to-30-minute byte change is admitted."""
    assert type(source) is bytes, "ci_workflow_exact_bytes"
    current = b"    timeout-minutes: 30\n"
    previous = b"    timeout-minutes: 20\n"
    assert source.count(current) == 1, "ci_workflow_job_timeout"
    restored = source.replace(current, previous, 1)
    digest = hashlib.sha1(b"blob " + str(len(restored)).encode() + b"\0" + restored).hexdigest()
    assert digest == '19afa3d54997423e54c3aa1ecbd5ac2578458f89', "ci_workflow_unapproved_change"


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

    def test_ci_maintenance_exception_preserves_the_complete_original_workflow(self) -> None:
        source = (REPOSITORY_ROOT / ".github/workflows/asie-ci.yml").read_bytes()
        validate_ci_timeout_amendment(source)

    def test_ci_maintenance_exception_rejects_other_workflow_changes(self) -> None:
        source = (REPOSITORY_ROOT / ".github/workflows/asie-ci.yml").read_bytes()
        mutations = (
            (b"timeout-minutes: 30", b"timeout-minutes: 20"),
            (b"timeout-minutes: 10", b"timeout-minutes: 11"),
            (b"--warmups 1 --trials 3", b"--warmups 0 --trials 1"),
            (b"python -m pytest -q", b"python -m pytest -q -k subset"),
            (b"Build frontend and test backend", b"Changed required context"),
            (b"contents: read", b"contents: write"),
            (b"branches: [main,", b"branches: [other,"),
            (b"cancel-in-progress: true", b"cancel-in-progress: false"),
            (b"      - name: Run Python tests", b"      - name: Run Python tests\n        continue-on-error: true"),
        )
        for old, new in mutations:
            with self.subTest(old=old):
                self.assertEqual(source.count(old), 1)
                with self.assertRaises(AssertionError):
                    validate_ci_timeout_amendment(source.replace(old, new, 1))
        with self.assertRaises(AssertionError):
            validate_ci_timeout_amendment(source + b"\n  extra-job:\n    runs-on: ubuntu-latest\n")

    def test_ci_maintenance_workflow_guard_requires_exact_bytes(self) -> None:
        for source in (None, False, 0, "text", bytearray(b"x")):
            with self.subTest(source=source):
                with self.assertRaises(AssertionError):
                    validate_ci_timeout_amendment(source)

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
