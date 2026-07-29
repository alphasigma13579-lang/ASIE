from __future__ import annotations

import unittest

from backend.beta_release_gate import (
    DEGRADABLE_CAPABILITIES,
    DEPLOYMENT_EVIDENCE_SCHEMA,
    DETERMINISM_EVIDENCE_SCHEMA,
    EVIDENCE_BUNDLE_SCHEMA,
    REQUIRED_CODE_CHECKS,
    REQUIRED_SMOKE_CHECKS,
    assert_releaseable,
    deployment_evidence_hash,
    evaluate_beta_release,
    evidence_bundle_hash,
)

COMMIT = "a" * 40
OTHER_COMMIT = "b" * 40


def _record(check_id: str, *, commit: str = COMMIT, status: str = "passed") -> dict[str, object]:
    return {
        "check_id": check_id,
        "critical": True,
        "status": status,
        "commit_sha": commit,
        "command": ["python", "-m", "unittest"],
        "exit_code": 0 if status == "passed" else 1,
        "log_sha256": "1" * 64,
        "claims": [f"claim:{check_id}"],
    }


def _bundle(*, commit: str = COMMIT) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema": EVIDENCE_BUNDLE_SCHEMA,
        "package_id": "REL-BETA-07",
        "commit_sha": commit,
        "expected_commit": commit,
        "generated_at": "2026-07-29T00:00:00+00:00",
        "generator": "test",
        "manual_readiness_assertions_accepted": False,
        "checks": [_record(check_id, commit=commit) for check_id in REQUIRED_CODE_CHECKS],
    }
    payload["bundle_hash"] = evidence_bundle_hash(payload)
    return payload


def _determinism(*, commit: str = COMMIT) -> dict[str, object]:
    return {
        "schema": DETERMINISM_EVIDENCE_SCHEMA,
        "commit_sha": commit,
        "status": "passed",
        "vectors_compared": 4,
        "vector_hash": "2" * 64,
        "comparison_sha256": "3" * 64,
    }


def _deployment(*, commit: str = COMMIT, degraded: str | None = None) -> dict[str, object]:
    capabilities = {capability: "passed" for capability in DEGRADABLE_CAPABILITIES}
    if degraded:
        capabilities[degraded] = "unavailable"
    payload: dict[str, object] = {
        "schema": DEPLOYMENT_EVIDENCE_SCHEMA,
        "commit_sha": commit,
        "image_digest": "sha256:" + "4" * 64,
        "status": "passed",
        "checks": {check_id: "passed" for check_id in REQUIRED_SMOKE_CHECKS},
        "capabilities": capabilities,
    }
    payload["evidence_hash"] = deployment_evidence_hash(payload)
    return payload


def _freeze(*, cleared: bool) -> dict[str, object]:
    return {
        "schema": "asie.release.freeze.v1",
        "status": "CLEARED" if cleared else "ACTIVE",
        "decision": "PENDING_GATE" if cleared else "NO_GO",
        "release_gate_allowed": cleared,
        "baseline_commit": "8978231e190b8ccc2be59ec46acf50d6268cd41f",
    }


class EvidenceBackedBetaReleaseGateTests(unittest.TestCase):
    def test_complete_commit_bound_evidence_produces_go(self) -> None:
        report = evaluate_beta_release(
            _bundle(),
            _determinism(),
            _freeze(cleared=True),
            expected_commit=COMMIT,
            deployment_evidence=_deployment(),
            workflow_run_id="run-1",
        )

        self.assertEqual(report["decision"], "GO")
        self.assertTrue(report["release_allowed"])
        self.assertTrue(report["public_beta_allowed"])
        self.assertTrue(report["code_evidence_ready"])
        self.assertEqual(report["critical_failures"], [])
        self.assertEqual(report["degraded_capabilities"], [])
        self.assertFalse(report["manual_readiness_assertions_accepted"])
        self.assertEqual(len(report["report_hash"]), 64)

    def test_active_freeze_forces_no_go_after_all_other_evidence_passes(self) -> None:
        report = evaluate_beta_release(
            _bundle(),
            _determinism(),
            _freeze(cleared=False),
            expected_commit=COMMIT,
            deployment_evidence=_deployment(),
        )

        self.assertEqual(report["decision"], "NO_GO")
        self.assertFalse(report["release_allowed"])
        self.assertTrue(report["code_evidence_ready"])
        self.assertIn("emergency_release_freeze_cleared", report["critical_failures"])

    def test_missing_private_smoke_fails_closed_but_code_can_be_ready(self) -> None:
        report = evaluate_beta_release(
            _bundle(),
            _determinism(),
            _freeze(cleared=False),
            expected_commit=COMMIT,
            deployment_evidence=None,
        )

        self.assertEqual(report["decision"], "NO_GO")
        self.assertTrue(report["ready_for_private_deployment_smoke"])
        self.assertIn("private_deployment_smoke_passed", report["critical_failures"])
        self.assertIn("emergency_release_freeze_cleared", report["critical_failures"])

    def test_stale_commit_evidence_is_rejected(self) -> None:
        report = evaluate_beta_release(
            _bundle(commit=OTHER_COMMIT),
            _determinism(commit=OTHER_COMMIT),
            _freeze(cleared=True),
            expected_commit=COMMIT,
            deployment_evidence=_deployment(commit=OTHER_COMMIT),
        )

        self.assertEqual(report["decision"], "NO_GO")
        self.assertIn("release_commit_bound", report["critical_failures"])
        self.assertIn("test_beta_06_cross_platform_determinism", report["critical_failures"])
        self.assertIn("private_deployment_smoke_passed", report["critical_failures"])

    def test_tampered_bundle_hash_is_rejected(self) -> None:
        bundle = _bundle()
        checks = list(bundle["checks"])
        checks[0] = dict(checks[0]) | {"status": "failed", "exit_code": 1}
        bundle["checks"] = checks

        report = evaluate_beta_release(
            bundle,
            _determinism(),
            _freeze(cleared=True),
            expected_commit=COMMIT,
            deployment_evidence=_deployment(),
        )

        self.assertEqual(report["decision"], "NO_GO")
        self.assertIn("evidence_bundle_integrity", report["critical_failures"])

    def test_degradable_capability_produces_conditional_go_only_after_critical_evidence(self) -> None:
        report = evaluate_beta_release(
            _bundle(),
            _determinism(),
            _freeze(cleared=True),
            expected_commit=COMMIT,
            deployment_evidence=_deployment(degraded="live_intelligence"),
        )

        self.assertEqual(report["decision"], "CONDITIONAL_GO")
        self.assertFalse(report["public_beta_allowed"])
        self.assertTrue(report["technical_limited_beta_allowed"])
        self.assertEqual(report["degraded_capabilities"], ["live_intelligence"])
        with self.assertRaisesRegex(RuntimeError, "beta_release_blocked:CONDITIONAL_GO"):
            assert_releaseable(report, release_scope="public_beta")
        assert_releaseable(report, release_scope="technical_limited_beta")

    def test_invalid_release_scope_cannot_override_evidence(self) -> None:
        report = evaluate_beta_release(
            _bundle(),
            _determinism(),
            _freeze(cleared=True),
            expected_commit=COMMIT,
            deployment_evidence=_deployment(),
        )
        with self.assertRaisesRegex(ValueError, "unsupported_release_scope"):
            assert_releaseable(report, release_scope="ignore-security")

    def test_report_never_exposes_unselected_bundle_material_or_mutates_domains(self) -> None:
        bundle = _bundle()
        bundle["secret_material"] = "must-not-appear"
        bundle["bundle_hash"] = evidence_bundle_hash(bundle)
        report = evaluate_beta_release(
            bundle,
            _determinism(),
            _freeze(cleared=True),
            expected_commit=COMMIT,
            deployment_evidence=_deployment(),
        )

        self.assertNotIn("must-not-appear", str(report))
        self.assertFalse(report["secrets_exposed"])
        self.assertFalse(report["finance_mutated"])
        self.assertFalse(report["snapshot_mutated"])
        self.assertFalse(report["external_fetch_changed"])


if __name__ == "__main__":
    unittest.main()
