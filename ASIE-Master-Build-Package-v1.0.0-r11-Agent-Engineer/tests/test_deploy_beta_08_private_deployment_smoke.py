from __future__ import annotations

import unittest
from pathlib import Path

from backend.beta_release_gate import _validate_deployment_evidence
from backend.dib_registry_admission import assert_all_frozen_files_unchanged
from tools.deploy_beta_08_private_smoke import (
    DEGRADABLE_CAPABILITIES,
    DEPLOYMENT_EVIDENCE_SCHEMA,
    REQUIRED_SMOKE_CHECKS,
    deployment_evidence_hash,
)

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PACKAGE_ROOT.parent
PRIVATE_COMPOSE_PATH = PACKAGE_ROOT / "docker-compose.private-smoke.yml"
DEFAULT_COMPOSE_PATH = PACKAGE_ROOT / "docker-compose.yml"
PRODUCTION_COMPOSE_PATH = PACKAGE_ROOT / "docker-compose.production.yml"
WORKFLOW_PATH = REPOSITORY_ROOT / ".github" / "workflows" / "beta-release-gate.yml"

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

DEPLOY_BETA_08_ALLOWLIST = {
    "../.github/workflows/beta-release-gate.yml",
    "docker-compose.yml",
    "docker-compose.production.yml",
    "docker-compose.private-smoke.yml",
    "tools/deploy_beta_08_private_smoke.py",
    "tests/test_deploy_beta_08_private_deployment_smoke.py",
    "tests/test_dib_local_gateway_integration.py",
    "docs/DEPLOY-BETA-08-PRIVATE-DEPLOYMENT-SMOKE-2026-07-29.md",
}


def valid_evidence(commit_sha: str = "a" * 40) -> dict:
    evidence = {
        "schema": DEPLOYMENT_EVIDENCE_SCHEMA,
        "package_id": "DEPLOY-BETA-08",
        "status": "passed",
        "commit_sha": commit_sha,
        "image_digest": "sha256:" + "b" * 64,
        "image_material": {
            "commit_sha": commit_sha,
            "compose_sha256": "c" * 64,
            "images": {
                "api": "sha256:" + "d" * 64,
                "dib-api": "sha256:" + "d" * 64,
                "web": "sha256:" + "e" * 64,
            },
        },
        "started_at": "2026-07-29T00:00:00+00:00",
        "finished_at": "2026-07-29T00:01:00+00:00",
        "checks": {check_id: True for check_id in REQUIRED_SMOKE_CHECKS},
        "check_details": {},
        "capabilities": {capability: False for capability in DEGRADABLE_CAPABILITIES},
        "network_boundary": {
            "loopback_only": True,
            "published_bindings": [
                "127.0.0.1:18080:80",
                "127.0.0.1:18794:8794",
                "127.0.0.1:18795:8795",
            ],
            "public_bindings": [],
            "docker_network_internal": True,
            "external_fetch_enabled": False,
            "caddy_present": False,
        },
        "secrets_exposed": False,
        "fixture_data_ephemeral": True,
        "error_code": None,
    }
    evidence["evidence_hash"] = deployment_evidence_hash(evidence)
    return evidence


class DeployBeta08PrivateDeploymentSmokeTests(unittest.TestCase):
    def test_evidence_contract_is_accepted_by_rel_beta_07(self) -> None:
        commit = "a" * 40
        smoke_check, capabilities = _validate_deployment_evidence(valid_evidence(commit), commit)
        self.assertTrue(smoke_check.passed)
        self.assertEqual("private_deployment_smoke_passed", smoke_check.check_id)
        self.assertEqual(set(DEGRADABLE_CAPABILITIES), {item.check_id for item in capabilities})
        self.assertTrue(all(not item.passed for item in capabilities))

    def test_tampered_or_cross_commit_evidence_fails_closed(self) -> None:
        commit = "a" * 40
        evidence = valid_evidence(commit)
        evidence["checks"]["tenant_isolation"] = False
        smoke_check, _ = _validate_deployment_evidence(evidence, commit)
        self.assertFalse(smoke_check.passed)

        evidence = valid_evidence(commit)
        smoke_check, _ = _validate_deployment_evidence(evidence, "f" * 40)
        self.assertFalse(smoke_check.passed)

        evidence = valid_evidence(commit)
        evidence["image_digest"] = "not-an-image-digest"
        evidence["evidence_hash"] = deployment_evidence_hash(evidence)
        smoke_check, _ = _validate_deployment_evidence(evidence, commit)
        self.assertFalse(smoke_check.passed)

    def test_private_compose_has_no_public_listener_or_external_network(self) -> None:
        compose = PRIVATE_COMPOSE_PATH.read_text(encoding="utf-8")
        self.assertIn('"127.0.0.1:18080:80"', compose)
        self.assertIn('"127.0.0.1:18794:8794"', compose)
        self.assertIn('"127.0.0.1:18795:8795"', compose)
        self.assertNotIn('\n      - "80:80"', compose)
        self.assertNotIn('\n      - "443:443"', compose)
        self.assertNotIn("  caddy:\n", compose)
        self.assertIn("internal: true", compose)
        self.assertIn('com.docker.network.bridge.host_binding_ipv4: "127.0.0.1"', compose)
        self.assertIn('ASIE_ALLOW_EXTERNAL_FETCH: "false"', compose)
        self.assertIn('ASIE_ALLOW_LOCAL_BOOTSTRAP: "false"', compose)
        self.assertIn('ASIE_ALLOW_LEGACY_LOCAL_OPERATOR: "false"', compose)

    def test_all_compose_profiles_use_import_safe_dib_module_entrypoint(self) -> None:
        canonical_command = 'command: ["python", "-m", "backend.dib_http_mounting"]'
        unsafe_command = 'command: ["python", "backend/dib_http_mounting.py"]'
        for path in (PRIVATE_COMPOSE_PATH, DEFAULT_COMPOSE_PATH, PRODUCTION_COMPOSE_PATH):
            compose = path.read_text(encoding="utf-8")
            self.assertIn(canonical_command, compose, path.name)
            self.assertNotIn(unsafe_command, compose, path.name)

    def test_workflow_runs_smoke_and_feeds_deployment_evidence_to_gate(self) -> None:
        workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
        self.assertIn("private-deployment-smoke:", workflow)
        self.assertIn("docker-compose.private-smoke.yml", workflow)
        self.assertIn("tools/deploy_beta_08_private_smoke.py", workflow)
        self.assertIn("deploy-beta-08-private-smoke-evidence", workflow)
        self.assertIn("--deployment-evidence", workflow)
        self.assertIn("deployment-evidence.json", workflow)
        self.assertIn('"${compose[@]}" up -d api', workflow)
        self.assertIn('"${compose[@]}" up -d dib-api', workflow)
        self.assertIn('"${compose[@]}" up -d web', workflow)
        self.assertNotIn("0.0.0.0:18080", workflow)

    def test_allowlist_excludes_frozen_runtime_and_freeze_marker(self) -> None:
        normalized = {path.removeprefix("../") for path in DEPLOY_BETA_08_ALLOWLIST}
        self.assertTrue(normalized.isdisjoint(FROZEN_FILES))
        self.assertNotIn("EMERGENCY-RELEASE-FREEZE.json", normalized)
        assert_all_frozen_files_unchanged(PACKAGE_ROOT)


if __name__ == "__main__":
    unittest.main()
