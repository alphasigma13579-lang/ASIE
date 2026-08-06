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
    DEFERRED,
    REJECTED,
    REVIEW_SCHEMA,
    VERIFIED,
    evaluate_controlled_unfreeze,
    main as controlled_unfreeze_main,
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
    "tests/test_rel_beta_07_evidence_release_gate.py",
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


def foundation_pending_gate(commit: str = "a" * 40) -> dict:
    report = valid_gate(commit)
    report.pop("report_hash")
    report["decision"] = "NO_GO"
    report["release_allowed"] = False
    report["technical_limited_beta_allowed"] = False
    report["critical_failures"] = ["foundation_completion_program_cleared"]
    report["checks"] = list(report["checks"]) + [
        {
            "check_id": "foundation_completion_program_cleared",
            "passed": False,
            "critical": True,
            "evidence": {
                "program_id": "FOUNDATION-COMPLETE-20",
                "status": "ACTIVE_IMPLEMENTATION_PROGRAM",
                "current_release_verdict": "BLOCK",
            },
            "message": "",
        }
    ]
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

    def test_foundation_pending_no_go_defers_without_granting_release(self) -> None:
        report = evaluate_controlled_unfreeze(
            foundation_pending_gate(),
            valid_marker(),
            expected_commit="a" * 40,
            frozen_files_unchanged=True,
        )
        self.assertEqual(DEFERRED, report["decision"])
        self.assertTrue(report["foundation_deferral"]["active"])
        self.assertEqual(["technical_limited_gate_state"], report["failures"])
        self.assertFalse(report["technical_limited_release_gate_allowed"])
        self.assertFalse(report["public_release_authorized"])
        self.assertFalse(report["external_network_authorized"])
        self.assertFalse(report["provider_activation_authorized"])

    def test_foundation_pending_with_extra_critical_failure_rejects(self) -> None:
        gate = foundation_pending_gate()
        gate.pop("report_hash")
        gate["critical_failures"] = [
            "foundation_completion_program_cleared",
            "sec_beta_01_identity_lockdown",
        ]
        gate["report_hash"] = canonical_sha256(gate)
        report = evaluate_controlled_unfreeze(
            gate,
            valid_marker(),
            expected_commit="a" * 40,
            frozen_files_unchanged=True,
        )
        self.assertEqual(REJECTED, report["decision"])
        self.assertFalse(report["foundation_deferral"]["active"])

    def test_foundation_pending_with_failed_smoke_rejects(self) -> None:
        gate = foundation_pending_gate()
        gate.pop("report_hash")
        gate["checks"] = [
            {**check, "passed": False}
            if check["check_id"] == "private_deployment_smoke_passed"
            else check
            for check in gate["checks"]
        ]
        gate["report_hash"] = canonical_sha256(gate)
        report = evaluate_controlled_unfreeze(
            gate,
            valid_marker(),
            expected_commit="a" * 40,
            frozen_files_unchanged=True,
        )
        self.assertEqual(REJECTED, report["decision"])
        self.assertFalse(report["foundation_deferral"]["active"])

    def test_foundation_pending_without_deliberate_block_state_rejects(self) -> None:
        gate = foundation_pending_gate()
        gate.pop("report_hash")
        gate["checks"] = [
            {
                **check,
                "evidence": {**check["evidence"], "current_release_verdict": "GO"},
            }
            if check["check_id"] == "foundation_completion_program_cleared"
            else check
            for check in gate["checks"]
        ]
        gate["report_hash"] = canonical_sha256(gate)
        report = evaluate_controlled_unfreeze(
            gate,
            valid_marker(),
            expected_commit="a" * 40,
            frozen_files_unchanged=True,
        )
        self.assertEqual(REJECTED, report["decision"])
        self.assertFalse(report["foundation_deferral"]["active"])

    def test_foundation_pending_with_tampered_marker_rejects(self) -> None:
        marker = valid_marker()
        marker["controlled_unfreeze"]["eligibility_review_run_id"] = "attacker"
        report = evaluate_controlled_unfreeze(
            foundation_pending_gate(),
            marker,
            expected_commit="a" * 40,
            frozen_files_unchanged=True,
        )
        self.assertEqual(REJECTED, report["decision"])
        self.assertFalse(report["foundation_deferral"]["active"])

    def test_foundation_pending_with_frozen_hash_drift_rejects(self) -> None:
        report = evaluate_controlled_unfreeze(
            foundation_pending_gate(),
            valid_marker(),
            expected_commit="a" * 40,
            frozen_files_unchanged=False,
        )
        self.assertEqual(REJECTED, report["decision"])
        self.assertFalse(report["foundation_deferral"]["active"])

    def test_require_verified_cli_defers_only_with_explicit_flag(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            gate_path = tmp_path / "gate.json"
            marker_path = tmp_path / "marker.json"
            gate_path.write_text(
                json.dumps(foundation_pending_gate()), encoding="utf-8"
            )
            marker_path.write_text(json.dumps(valid_marker()), encoding="utf-8")
            base_args = [
                "--gate-report",
                str(gate_path),
                "--freeze-marker",
                str(marker_path),
                "--expected-commit",
                "a" * 40,
                "--repository-root",
                str(REPOSITORY_ROOT),
                "--output",
                str(tmp_path / "review.json"),
                "--require-verified",
            ]
            self.assertEqual(1, controlled_unfreeze_main(base_args))
            self.assertEqual(
                0,
                controlled_unfreeze_main(base_args + ["--allow-foundation-deferral"]),
            )
            gate = foundation_pending_gate()
            gate.pop("report_hash")
            gate["critical_failures"] = ["sec_beta_01_identity_lockdown"]
            gate["report_hash"] = canonical_sha256(gate)
            gate_path.write_text(json.dumps(gate), encoding="utf-8")
            self.assertEqual(
                1,
                controlled_unfreeze_main(base_args + ["--allow-foundation-deferral"]),
            )

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
        self.assertIn("--allow-foundation-deferral", workflow)
        self.assertIn("gov-rel-10-controlled-unfreeze-review", workflow)

    def test_allowlist_is_disjoint_from_every_frozen_runtime_file(self) -> None:
        normalized = {path.removeprefix("../") for path in GOV_REL_10_ALLOWLIST}
        self.assertTrue(normalized.isdisjoint(FROZEN_FILES))
        assert_all_frozen_files_unchanged(PACKAGE_ROOT)


if __name__ == "__main__":
    unittest.main()
