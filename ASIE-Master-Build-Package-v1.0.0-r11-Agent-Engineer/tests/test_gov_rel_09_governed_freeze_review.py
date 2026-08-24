from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from backend.beta_release_gate import GATE_CONTRACT_ID, canonical_sha256
from backend.dib_registry_admission import assert_all_frozen_files_unchanged
from tools.gov_rel_09_governed_freeze_review import (
    ELIGIBLE,
    KEEP_FROZEN,
    REJECT_UNFREEZE,
    EXPECTED_PROTECTED_BOUNDARIES,
    EXPECTED_REASON_CODES,
    EXPECTED_SCOPE,
    EXPECTED_UNFREEZE_REQUIREMENTS,
    REQUIRED_EVIDENCE_PATHS,
    REQUIRED_PACKAGE_COMMITS,
    REVIEW_SCHEMA,
    evaluate_governed_freeze_review,
    review_report_hash,
    write_report,
)

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PACKAGE_ROOT.parent
WORKFLOW_PATH = REPOSITORY_ROOT / ".github" / "workflows" / "governed-freeze-review.yml"
FREEZE_MARKER_PATH = REPOSITORY_ROOT / "EMERGENCY-RELEASE-FREEZE.json"

GOV_REL_09_ALLOWLIST = {
    "../.github/workflows/governed-freeze-review.yml",
    "tools/gov_rel_09_governed_freeze_review.py",
    "tests/test_gov_rel_09_governed_freeze_review.py",
    "docs/GOV-REL-09-GOVERNED-FREEZE-REVIEW-2026-07-29.md",
}

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


def valid_freeze_marker() -> dict:
    return {
        "schema": "asie.release.freeze.v1",
        "status": "ACTIVE",
        "decision": "NO_GO",
        "baseline_commit": "8978231e190b8ccc2be59ec46acf50d6268cd41f",
        "activated_on": "2026-07-29",
        "scope": sorted(EXPECTED_SCOPE),
        "reason_codes": sorted(EXPECTED_REASON_CODES),
        "protected_boundaries": sorted(EXPECTED_PROTECTED_BOUNDARIES),
        "release_gate_allowed": False,
        "unfreeze_requires": sorted(EXPECTED_UNFREEZE_REQUIREMENTS),
    }


def valid_gate_report(commit: str = "a" * 40) -> dict:
    report = {
        "contract_id": GATE_CONTRACT_ID,
        "decision": "NO_GO",
        "release_commit": commit,
        "workflow_run_id": "12345",
        "release_allowed": False,
        "public_beta_allowed": False,
        "technical_limited_beta_allowed": False,
        "code_evidence_ready": True,
        "ready_for_private_deployment_smoke": True,
        "critical_failures": ["emergency_release_freeze_cleared"],
        "degraded_capabilities": [
            "provider_connectivity",
            "external_fetch",
            "vision2030_sync",
            "live_intelligence",
        ],
        "checks": [
            {
                "check_id": "release_commit_bound",
                "passed": True,
                "critical": True,
                "evidence": {"expected_commit": commit, "evidence_commit": commit},
                "message": "",
            },
            {
                "check_id": "private_deployment_smoke_passed",
                "passed": True,
                "critical": True,
                "evidence": {"commit_sha": commit},
                "message": "",
            },
            {
                "check_id": "emergency_release_freeze_cleared",
                "passed": False,
                "critical": True,
                "evidence": {"status": "ACTIVE"},
                "message": "",
            },
        ],
        "evidence_bundle_hash": "b" * 64,
        "determinism_vector_hash": "c" * 64,
        "deployment_image_digest": "sha256:" + "d" * 64,
        "manual_readiness_assertions_accepted": False,
        "secrets_exposed": False,
        "finance_mutated": False,
        "snapshot_mutated": False,
        "external_fetch_changed": False,
    }
    report["report_hash"] = canonical_sha256(report)
    return report


def all_ancestors(_root: Path, _ancestor: str, _descendant: str) -> bool:
    return True


def all_paths(_path: Path) -> bool:
    return True


class GovernedFreezeReviewTests(unittest.TestCase):
    def test_all_governed_requirements_produce_eligibility_without_authority(self) -> None:
        commit = "a" * 40
        review = evaluate_governed_freeze_review(
            valid_gate_report(commit),
            valid_freeze_marker(),
            expected_commit=commit,
            repository_root=REPOSITORY_ROOT,
            ancestor_resolver=all_ancestors,
            path_exists=all_paths,
        )

        self.assertEqual(REVIEW_SCHEMA, review["schema"])
        self.assertEqual(ELIGIBLE, review["decision"])
        self.assertFalse(review["unfreeze_authorized"])
        self.assertFalse(review["marker_mutation_permitted"])
        self.assertFalse(review["release_allowed"])
        self.assertFalse(review["public_beta_allowed"])
        self.assertEqual("GOV-REL-10-CONTROLLED-UNFREEZE-EXECUTION", review["required_next_package"])
        self.assertEqual(review["review_hash"], review_report_hash(review))
        self.assertEqual([], review["rejection_failures"])
        self.assertEqual([], review["readiness_failures"])

    def test_tampered_gate_report_rejects_unfreeze(self) -> None:
        commit = "a" * 40
        gate = valid_gate_report(commit)
        gate["code_evidence_ready"] = False

        review = evaluate_governed_freeze_review(
            gate,
            valid_freeze_marker(),
            expected_commit=commit,
            repository_root=REPOSITORY_ROOT,
            ancestor_resolver=all_ancestors,
            path_exists=all_paths,
        )

        self.assertEqual(REJECT_UNFREEZE, review["decision"])
        self.assertIn("release_gate_contract_integrity", review["rejection_failures"])

    def test_extra_critical_release_failure_keeps_freeze_active(self) -> None:
        commit = "a" * 40
        gate = valid_gate_report(commit)
        gate["critical_failures"] = [
            "private_deployment_smoke_passed",
            "emergency_release_freeze_cleared",
        ]
        gate["checks"][1]["passed"] = False
        gate["report_hash"] = canonical_sha256(
            {key: value for key, value in gate.items() if key != "report_hash"}
        )

        review = evaluate_governed_freeze_review(
            gate,
            valid_freeze_marker(),
            expected_commit=commit,
            repository_root=REPOSITORY_ROOT,
            ancestor_resolver=all_ancestors,
            path_exists=all_paths,
        )

        self.assertEqual(KEEP_FROZEN, review["decision"])
        self.assertIn("pre_unfreeze_release_gate_state", review["readiness_failures"])
        self.assertEqual([], review["rejection_failures"])

    def test_missing_required_package_commit_rejects_unfreeze(self) -> None:
        commit = "a" * 40
        missing_commit = REQUIRED_PACKAGE_COMMITS["GOV-BETA-04"]

        def lineage(_root: Path, ancestor: str, _descendant: str) -> bool:
            return ancestor != missing_commit

        review = evaluate_governed_freeze_review(
            valid_gate_report(commit),
            valid_freeze_marker(),
            expected_commit=commit,
            repository_root=REPOSITORY_ROOT,
            ancestor_resolver=lineage,
            path_exists=all_paths,
        )

        self.assertEqual(REJECT_UNFREEZE, review["decision"])
        self.assertIn("required_package_history", review["rejection_failures"])

    def test_missing_executable_evidence_path_keeps_freeze_active(self) -> None:
        commit = "a" * 40
        missing_path = next(iter(REQUIRED_EVIDENCE_PATHS["SEC-BETA-03"]))

        def paths(path: Path) -> bool:
            return not path.as_posix().endswith(missing_path)

        review = evaluate_governed_freeze_review(
            valid_gate_report(commit),
            valid_freeze_marker(),
            expected_commit=commit,
            repository_root=REPOSITORY_ROOT,
            ancestor_resolver=all_ancestors,
            path_exists=paths,
        )

        self.assertEqual(KEEP_FROZEN, review["decision"])
        self.assertIn("required_package_evidence_paths", review["readiness_failures"])

    def test_review_does_not_mutate_marker_and_writes_only_report(self) -> None:
        commit = "a" * 40
        marker = valid_freeze_marker()
        original = copy.deepcopy(marker)
        review = evaluate_governed_freeze_review(
            valid_gate_report(commit),
            marker,
            expected_commit=commit,
            repository_root=REPOSITORY_ROOT,
            ancestor_resolver=all_ancestors,
            path_exists=all_paths,
        )
        self.assertEqual(original, marker)

        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "governed-freeze-review.json"
            write_report(output, review)
            restored = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(ELIGIBLE, restored["decision"])
            self.assertEqual(review["review_hash"], restored["review_hash"])

    def test_repository_marker_transition_and_workflow_are_commit_bound(self) -> None:
        marker = json.loads(FREEZE_MARKER_PATH.read_text(encoding="utf-8"))
        self.assertEqual("CLEARED", marker["status"])
        self.assertEqual("PENDING_GATE", marker["decision"])
        self.assertTrue(marker["release_gate_allowed"])
        transition = marker["controlled_unfreeze"]
        self.assertFalse(transition["public_release_authorized"])
        self.assertFalse(transition["external_network_authorized"])
        self.assertFalse(transition["provider_activation_authorized"])

        workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
        self.assertIn("  push:\n    branches: [main]", workflow)
        self.assertNotIn("workflow_run:", workflow)
        self.assertIn("actions/workflows/beta-release-gate.yml/runs?branch=main&event=push", workflow)
        self.assertIn(".head_sha == $sha", workflow)
        self.assertIn(".head_branch == \"main\"", workflow)
        self.assertIn(".event == \"push\"", workflow)
        self.assertIn(".conclusion == \"success\"", workflow)
        self.assertIn("gh run download", workflow)
        self.assertIn("--name rel-beta-07-complete-evidence", workflow)
        self.assertIn("git rev-parse origin/main", workflow)
        self.assertIn("tools/gov_rel_09_governed_freeze_review.py", workflow)
        self.assertIn("--require-eligible", workflow)
        self.assertIn("env.ASIE_FREEZE_STATUS == 'ACTIVE'", workflow)
        self.assertIn("env.ASIE_FREEZE_STATUS == 'CLEARED'", workflow)
        self.assertIn("tools.gov_rel_10_controlled_unfreeze", workflow)
        self.assertIn("--require-verified", workflow)
        self.assertIn("fetch-depth: 0", workflow)

    def test_surgical_allowlist_excludes_marker_and_frozen_runtime(self) -> None:
        normalized = {path.removeprefix("../") for path in GOV_REL_09_ALLOWLIST}
        self.assertNotIn("EMERGENCY-RELEASE-FREEZE.json", normalized)
        self.assertTrue(normalized.isdisjoint(FROZEN_FILES))
        assert_all_frozen_files_unchanged(PACKAGE_ROOT)


if __name__ == "__main__":
    unittest.main()
