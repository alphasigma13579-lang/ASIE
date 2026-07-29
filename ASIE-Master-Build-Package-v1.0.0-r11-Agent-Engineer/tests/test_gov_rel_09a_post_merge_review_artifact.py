from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PACKAGE_ROOT.parent
WORKFLOW_PATH = REPOSITORY_ROOT / ".github/workflows/governed-freeze-review.yml"
FREEZE_MARKER_PATH = REPOSITORY_ROOT / "EMERGENCY-RELEASE-FREEZE.json"
REVIEW_TOOL_PATH = PACKAGE_ROOT / "tools/gov_rel_09_governed_freeze_review.py"
REVIEW_DOC_PATH = PACKAGE_ROOT / "docs/GOV-REL-09A-POST-MERGE-REVIEW-ARTIFACT-REPAIR-2026-07-29.md"

GOV_REL_09A_ALLOWLIST = {
    ".github/workflows/governed-freeze-review.yml",
    "ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/tests/test_gov_rel_09_governed_freeze_review.py",
    "ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/tests/test_gov_rel_09a_post_merge_review_artifact.py",
    "ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/docs/GOV-REL-09A-POST-MERGE-REVIEW-ARTIFACT-REPAIR-2026-07-29.md",
}


class PostMergeReviewArtifactRepairTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    def test_workflow_runs_on_main_push_without_workflow_run_dependency(self) -> None:
        self.assertIn("  push:\n    branches: [main]", self.workflow)
        self.assertNotIn("workflow_run:", self.workflow)
        self.assertIn("github.event_name == 'push'", self.workflow)
        self.assertIn("github.ref == 'refs/heads/main'", self.workflow)

    def test_exact_commit_gate_run_is_resolved_fail_closed(self) -> None:
        required_fragments = (
            "actions/workflows/beta-release-gate.yml/runs?branch=main&event=push&per_page=50",
            "--arg sha \"$ASIE_REVIEW_COMMIT\"",
            ".head_sha == $sha",
            ".head_branch == \"main\"",
            ".event == \"push\"",
            ".conclusion == \"success\"",
            "Evidence gate reached a terminal non-success state",
            "No successful Evidence-Backed Beta Release Gate run found",
        )
        for fragment in required_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, self.workflow)

    def test_source_run_metadata_is_reverified_before_download(self) -> None:
        required_fragments = (
            "repos/${GITHUB_REPOSITORY}/actions/runs/${ASIE_EVIDENCE_RUN_ID}",
            "= \"Evidence-Backed Beta Release Gate\"",
            "= \"$ASIE_REVIEW_COMMIT\"",
            "= \"main\"",
            "= \"push\"",
            "= \"completed\"",
            "= \"success\"",
            "source-evidence-run.json",
        )
        for fragment in required_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, self.workflow)

    def test_artifact_name_and_required_report_are_fixed(self) -> None:
        self.assertIn("--name rel-beta-07-complete-evidence", self.workflow)
        self.assertIn(
            "test -f gov-rel-09-input/rel-beta-07-final/beta-release-gate-report.json",
            self.workflow,
        )
        self.assertIn("name: gov-rel-09-governed-freeze-review", self.workflow)
        self.assertIn("--require-eligible", self.workflow)
        self.assertIn("governed-freeze-review.sha256", self.workflow)

    def test_evaluator_uses_import_safe_module_entrypoint(self) -> None:
        self.assertIn("python -m tools.gov_rel_09_governed_freeze_review", self.workflow)
        self.assertNotIn("python tools/gov_rel_09_governed_freeze_review.py", self.workflow)

        completed = subprocess.run(
            [sys.executable, "-m", "tools.gov_rel_09_governed_freeze_review", "--help"],
            cwd=PACKAGE_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertIn("--gate-report", completed.stdout)

    def test_current_main_must_equal_reviewed_commit(self) -> None:
        self.assertIn("current_main=\"$(git rev-parse origin/main)\"", self.workflow)
        self.assertIn('test "$checked_out" = "$ASIE_REVIEW_COMMIT"', self.workflow)
        self.assertIn('test "$current_main" = "$ASIE_REVIEW_COMMIT"', self.workflow)

    def test_workflow_has_read_only_permissions(self) -> None:
        self.assertIn("permissions:\n  contents: read\n  actions: read", self.workflow)
        self.assertNotIn("contents: write", self.workflow)
        self.assertNotIn("actions: write", self.workflow)
        self.assertNotIn("pull-requests: write", self.workflow)
        self.assertNotIn("id-token: write", self.workflow)

    def test_freeze_marker_is_controlled_and_workflow_remains_read_only(self) -> None:
        marker = json.loads(FREEZE_MARKER_PATH.read_text(encoding="utf-8"))
        self.assertEqual("asie.release.freeze.v1", marker["schema"])
        self.assertEqual("CLEARED", marker["status"])
        self.assertEqual("PENDING_GATE", marker["decision"])
        self.assertIs(True, marker["release_gate_allowed"])
        transition = marker["controlled_unfreeze"]
        self.assertIs(False, transition["public_release_authorized"])
        self.assertIs(False, transition["external_network_authorized"])
        self.assertIs(False, transition["provider_activation_authorized"])
        self.assertIn("--freeze-marker ../EMERGENCY-RELEASE-FREEZE.json", self.workflow)
        for forbidden in (
            "git add ../EMERGENCY-RELEASE-FREEZE.json",
            "git commit",
            "git push",
            "sed -i",
            "contents: write",
            "id-token: write",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, self.workflow)

    def test_review_authority_remains_in_existing_evaluator(self) -> None:
        tool = REVIEW_TOOL_PATH.read_text(encoding="utf-8")
        self.assertIn('REVIEW_SCHEMA = "asie.governed.freeze.review.v1"', tool)
        self.assertIn('ELIGIBLE = "ELIGIBLE_FOR_UNFREEZE"', tool)
        self.assertIn('"unfreeze_authorized": False', tool)
        self.assertIn('"marker_mutation_permitted": False', tool)
        self.assertNotIn("EMERGENCY-RELEASE-FREEZE.json", GOV_REL_09A_ALLOWLIST)

    def test_package_document_exists(self) -> None:
        self.assertTrue(REVIEW_DOC_PATH.is_file())


if __name__ == "__main__":
    unittest.main()
