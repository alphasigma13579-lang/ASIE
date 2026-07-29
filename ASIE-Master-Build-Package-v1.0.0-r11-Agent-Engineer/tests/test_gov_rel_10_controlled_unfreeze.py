from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from backend.beta_release_gate import GATE_CONTRACT_ID, canonical_sha256
from backend.dib_registry_admission import assert_all_frozen_files_unchanged
from backend.release_freeze_contract import (
    BASELINE_COMMIT,
    EXPECTED_PROTECTED_BOUNDARIES,
    EXPECTED_REASON_CODES,
    EXPECTED_SCOPE,
    EXPECTED_UNFREEZE_REQUIREMENTS,
    controlled_unfreeze_record,
)
from tools.gov_rel_10_controlled_unfreeze import (
    REJECTED,
    REVIEW_SCHEMA,
    VERIFIED,
    evaluate_controlled_unfreeze,
)

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PACKAGE_ROOT.parent
MARKER_PATH = REPOSITORY_ROOT / "EMERGENCY-RELEASE-FREEZE.json"
WORKFLOW_PATH = REPOSITORY_ROOT / ".github/workflows/governed-freeze-review.yml"

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

GOV_REL_10_ALLOWLIST = {
    "../EMERGENCY-RELEASE-FREEZE.json",
    "../SECURITY.md",
    "../.github/workflows/beta-release-gate.yml",
    "../.github/workflows/governed-freeze-review.yml",
    "backend/release_freeze_contract.py",
    "backend/beta_release_gate.py",
    "tools/enforce_release_freeze.py",
    "tools/gov_rel_10_controlled_unfreeze.py",
    "tests/test_emerg_00_release_freeze.py",
    "tests/test_beta_release_gate.py",
    "tests/test_gov_rel_09_governed_freeze_review.py",
    "tests/test_gov_rel_09a_post_merge_review_artifact.py",
    "tests/test_gov_rel_10_controlled_unfreeze.py",
    "docs/EMERG-00-RELEASE-FREEZE-AND-EXPOSURE-CONTAINMENT-2026-07-29.md",
    "docs/GOV-REL-10-CONTROLLED-UNFREEZE-EXECUTION-2026-07-29.md",
}


def valid_marker() -> dict:
    return {
        "schema": "asie.release.freeze.v1",
        "status": "CLEARED",
        "decision": "PENDING_GATE",
        "baseline_commit": BASELINE_COMMIT,
        "activated_on": "2026-07-29",
        "scope": sorted(EXPECTED_SCOPE),
        "reason_codes": sorted(EXPECTED_REASON_CODES),
        "protected_boundaries": sorted(EXPECTED_PROTECTED_BOUNDARIES),
        "release_gate_allowed": True,
        "unfreeze_requires": sorted(EXPECTED_UNFREEZE_REQUIREMENTS),
        "controlled_unfreeze": controlled_unfreeze_record(),
    }


def valid_gate(commit: str = "a" * 40) -> dict:
    report = {
        "contract_id": GATE_CONTRACT_ID,
        "decision": "CONDITIONAL_GO",
        "release_commit": commit,
        "workflow_run_id": "98765",
        "release_allowed": True,
        "public_beta_allowed": False,
        "technical_limited_beta_allowed": True,
        "code_evidence_ready": True,
        "critical_failures": [],
        "degraded_capabilities": [
            "provider_connectivity",
            "external_fetch",
            "vision2030_sync",
            "live_intelligence",
        ],
        "checks": [
            {
                "check_id": "private_deployment_smoke_passed",
                "passed": True,
                "critical": True,
                "evidence": {"commit_sha": commit},
                "message": "",
            },
            {
                "check_id": "emergency_release_freeze_cleared",
                "passed": True,
                "critical": True,
                "evidence": {"status": "CLEARED"},
                "message": "",
            },
        ],
        "deployment_image_digest": "sha256:" + "d" * 64,
        "manual_readiness_assertions_accepted": False,
        "secrets_exposed": False,
        "finance_mutated": False,
        "snapshot_mutated": False,
        "external_fetch_changed": False,
    }
    report["report_hash"] = canonical_sha256(report)
    return report


class ControlledUnfreezeTests(unittest.TestCase):
    def test_exact_limited_gate_and_marker_are_verified_without_public_authority(self) -> None:
        report = evaluate_controlled_unfreeze(
            valid_gate(),
            valid_marker(),
            expected_commit="a" * 40,
            frozen_files_unchanged=True,
        )
        self.assertEqual(REVIEW_SCHEMA, report["schema"])
        self.assertEqual(VERIFIED, report["decision"])
        self.assertTrue(report["technical_limited_release_gate_allowed"])
        self.assertFalse(report["public_release_authorized"])
        self.assertFalse(report["external_network_authorized"])
        self.assertFalse(report["provider_activation_authorized"])
        self.assertFalse(report["finance_mutated"])
        self.assertFalse(report["snapshot_mutated"])
        self.assertFalse(report["aas_runtime_freeze_mutated"])
        self.assertEqual([], report["failures"])

    def test_tampered_marker_proof_fails_closed(self) -> None:
        marker = valid_marker()
        marker["controlled_unfreeze"]["eligibility_review_run_id"] = "attacker"
        report = evaluate_controlled_unfreeze(
            valid_gate(),
            marker,
            expected_commit="a" * 40,
            frozen_files_unchanged=True,
        )
        self.assertEqual(REJECTED, report["decision"])
        self.assertIn("controlled_unfreeze_marker_integrity", report["failures"])

    def test_stale_or_tampered_gate_fails_closed(self) -> None:
        gate = valid_gate()
        gate["release_commit"] = "b" * 40
        report = evaluate_controlled_unfreeze(
            gate,
            valid_marker(),
            expected_commit="a" * 40,
            frozen_files_unchanged=True,
        )
        self.assertEqual(REJECTED, report["decision"])
        self.assertIn("post_unfreeze_gate_contract_integrity", report["failures"])
        self.assertIn("post_unfreeze_gate_commit_bound", report["failures"])

    def test_public_go_is_rejected_by_this_limited_transition(self) -> None:
        gate = valid_gate()
        gate["decision"] = "GO"
        gate["public_beta_allowed"] = True
        gate["degraded_capabilities"] = []
        gate["report_hash"] = canonical_sha256(
            {key: value for key, value in gate.items() if key != "report_hash"}
        )
        report = evaluate_controlled_unfreeze(
            gate,
            valid_marker(),
            expected_commit="a" * 40,
            frozen_files_unchanged=True,
        )
        self.assertEqual(REJECTED, report["decision"])
        self.assertIn("technical_limited_gate_state", report["failures"])

    def test_frozen_hash_drift_rejects_transition(self) -> None:
        report = evaluate_controlled_unfreeze(
            valid_gate(),
            valid_marker(),
            expected_commit="a" * 40,
            frozen_files_unchanged=False,
        )
        self.assertEqual(REJECTED, report["decision"])
        self.assertIn("aas_runtime_freeze_hashes_unchanged", report["failures"])

    def test_repository_transition_and_workflow_are_fail_closed(self) -> None:
        marker = json.loads(MARKER_PATH.read_text(encoding="utf-8"))
        self.assertEqual(valid_marker(), marker)
        workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
        self.assertIn("ASIE_FREEZE_STATUS", workflow)
        self.assertIn("env.ASIE_FREEZE_STATUS == 'CLEARED'", workflow)
        self.assertIn("tools.gov_rel_10_controlled_unfreeze", workflow)
        self.assertIn("--require-verified", workflow)
        self.assertIn("gov-rel-10-controlled-unfreeze-review", workflow)

    def test_allowlist_is_disjoint_from_every_frozen_runtime_file(self) -> None:
        normalized = {path.removeprefix("../") for path in GOV_REL_10_ALLOWLIST}
        self.assertTrue(normalized.isdisjoint(FROZEN_FILES))
        assert_all_frozen_files_unchanged(PACKAGE_ROOT)


if __name__ == "__main__":
    unittest.main()
