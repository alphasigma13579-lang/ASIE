from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from backend.beta_release_gate import (
    DETERMINISM_EVIDENCE_SCHEMA,
    REQUIRED_CODE_CHECKS,
    evaluate_beta_release,
)
from tools.rel_beta_07_evidence import (
    CHECK_SPECS,
    PACKAGE_ROOT,
    build_evidence_bundle,
    current_commit,
    verify_frozen_git_blobs,
)

REPOSITORY_ROOT = PACKAGE_ROOT.parent
WORKFLOW_PATH = REPOSITORY_ROOT / ".github" / "workflows" / "beta-release-gate.yml"
MARKER_PATH = REPOSITORY_ROOT / "EMERGENCY-RELEASE-FREEZE.json"


class RelBeta07EvidenceReleaseGateTests(unittest.TestCase):
    def test_collector_covers_every_required_code_check(self) -> None:
        executable_ids = {spec.check_id for spec in CHECK_SPECS}
        self.assertEqual(set(REQUIRED_CODE_CHECKS), executable_ids | {"aas_freeze_git_blobs"})
        joined_commands = "\n".join(" ".join(spec.command) for spec in CHECK_SPECS)
        for required_test in (
            "test_dib_complete_runtime.py",
            "test_sec_beta_01_bootstrap_lockdown.py",
            "test_local_account_recovery.py",
            "test_stab_beta_02_transaction_safe_dib_persistence.py",
            "test_sec_beta_03_dib_tenant_boundary.py",
            "test_gov_beta_04_server_owned_manifest_chain.py",
            "test_arch_beta_05_canonical_finance_admission.py",
            "test_dib_snapshot_lineage.py",
            "test_report_export_routes.py",
        ):
            self.assertIn(required_test, joined_commands)

    def test_bundle_is_commit_bound_hashed_and_rejects_manual_assertions(self) -> None:
        commit = "a" * 40
        checks = [
            {
                "check_id": check_id,
                "critical": True,
                "status": "passed",
                "commit_sha": commit,
                "exit_code": 0,
                "log_sha256": "1" * 64,
                "claims": [],
            }
            for check_id in REQUIRED_CODE_CHECKS
        ]
        bundle = build_evidence_bundle(
            checks,
            commit_sha=commit,
            expected_commit=commit,
            generated_at="2026-07-29T00:00:00+00:00",
        )
        self.assertEqual(bundle["commit_sha"], commit)
        self.assertEqual(bundle["expected_commit"], commit)
        self.assertFalse(bundle["manual_readiness_assertions_accepted"])
        self.assertEqual(len(bundle["bundle_hash"]), 64)

    def test_freeze_manifest_matches_git_object_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            record = verify_frozen_git_blobs(
                commit_sha=current_commit(),
                log_directory=Path(directory),
            )
        self.assertEqual(record["status"], "passed")
        self.assertEqual(record["exit_code"], 0)
        self.assertEqual(len(record["log_sha256"]), 64)
        self.assertIn("Git object bytes", " ".join(record["claims"]))

    def test_workflow_uses_executable_evidence_and_no_readiness_variables(self) -> None:
        workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
        self.assertNotIn("vars.", workflow)
        self.assertNotIn("ASIE_BETA_AUTH_READY", workflow)
        self.assertNotIn("ASIE_BETA_TENANT_ISOLATION_READY", workflow)
        self.assertNotIn("ASIE_BETA_DEPLOYMENT_HEALTH_READY", workflow)
        self.assertIn("pull_request:", workflow)
        self.assertIn("push:", workflow)
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("windows-latest", workflow)
        self.assertIn("ubuntu-latest", workflow)
        for label in ("ubuntu-hash0", "ubuntu-hash7919", "windows-hash0", "windows-hash7919"):
            self.assertIn(label, workflow)
        self.assertIn("tools/rel_beta_07_evidence.py", workflow)
        self.assertIn("tools/test_beta_06_determinism.py compare", workflow)
        self.assertIn("python -m backend.beta_release_gate", workflow)
        self.assertIn("rel-beta-07-determinism-*", workflow)
        self.assertIn("beta-release-gate-report.json", workflow)

    def test_repository_controlled_marker_still_requires_private_smoke(self) -> None:
        commit = "a" * 40
        checks = [
            {
                "check_id": check_id,
                "critical": True,
                "status": "passed",
                "commit_sha": commit,
                "exit_code": 0,
                "log_sha256": "1" * 64,
                "claims": [],
            }
            for check_id in REQUIRED_CODE_CHECKS
        ]
        bundle = build_evidence_bundle(
            checks,
            commit_sha=commit,
            expected_commit=commit,
            generated_at="2026-07-29T00:00:00+00:00",
        )
        determinism = {
            "schema": DETERMINISM_EVIDENCE_SCHEMA,
            "commit_sha": commit,
            "status": "passed",
            "vectors_compared": 4,
            "vector_hash": "2" * 64,
            "comparison_sha256": "3" * 64,
        }
        marker = json.loads(MARKER_PATH.read_text(encoding="utf-8"))
        report = evaluate_beta_release(
            bundle,
            determinism,
            marker,
            expected_commit=commit,
            deployment_evidence=None,
        )
        self.assertEqual(report["decision"], "NO_GO")
        self.assertTrue(report["code_evidence_ready"])
        self.assertIn("private_deployment_smoke_passed", report["critical_failures"])
        self.assertNotIn(
            "emergency_release_freeze_cleared", report["critical_failures"]
        )
        freeze_check = next(
            check
            for check in report["checks"]
            if check["check_id"] == "emergency_release_freeze_cleared"
        )
        self.assertTrue(freeze_check["passed"])
        self.assertFalse(freeze_check["evidence"]["public_release_authorized"])
        self.assertFalse(freeze_check["evidence"]["external_network_authorized"])
        self.assertFalse(freeze_check["evidence"]["provider_activation_authorized"])


if __name__ == "__main__":
    unittest.main()
