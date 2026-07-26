from __future__ import annotations

import unittest
from pathlib import Path

from backend.dib_http_mounting import DIBHttpMount, _sidecar_auth_required
from backend.dib_registry_admission import assert_all_frozen_files_unchanged
from backend.dib_security_audit_rbac import (
    DIB_APPROVE_MANIFEST_PERMISSION,
    DIB_FINANCE_EXECUTE_PERMISSION,
    DIB_READ_PERMISSION,
    DIB_RUN_GATE_PERMISSION,
    DIB_SECURITY_AUDIT_RBAC_ID,
    DIB_SNAPSHOT_HANDOFF_PERMISSION,
    DIB_WRITE_PERMISSION,
    authorize_dib_request,
    build_dib_security_audit_event,
    dib_route_security_policy,
    dib_security_audit_rbac_status,
    extract_dib_session_id_from_path,
    is_production_environment,
    resolve_dib_auth_required,
)
from backend.identity import Principal, ROLE_PERMISSIONS

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
HTTP_MOUNTING_PATH = PACKAGE_ROOT / "backend" / "dib_http_mounting.py"
IDENTITY_PATH = PACKAGE_ROOT / "backend" / "identity.py"
SECURITY_PATH = PACKAGE_ROOT / "backend" / "dib_security_audit_rbac.py"


class DIBSecurityAuditRBACTests(unittest.TestCase):
    def test_security_package_status_and_permissions_are_declared(self) -> None:
        status = dib_security_audit_rbac_status({"ASIE_ENV": "production", "ASIE_DIB_REQUIRE_AUTH": "false"})
        self.assertEqual(status["security_audit_rbac_id"], DIB_SECURITY_AUDIT_RBAC_ID)
        self.assertTrue(status["production_environment"])
        self.assertTrue(status["production_auth_bypass_blocked"])
        self.assertIn(DIB_READ_PERMISSION, status["permissions"])
        self.assertIn(DIB_WRITE_PERMISSION, status["permissions"])
        self.assertIn(DIB_APPROVE_MANIFEST_PERMISSION, status["permissions"])
        self.assertIn(DIB_RUN_GATE_PERMISSION, status["permissions"])
        self.assertIn(DIB_FINANCE_EXECUTE_PERMISSION, status["permissions"])
        self.assertIn(DIB_SNAPSHOT_HANDOFF_PERMISSION, status["permissions"])

    def test_production_cannot_disable_dib_auth_but_status_stays_public(self) -> None:
        production_env = {"ASIE_ENV": "production", "ASIE_DIB_REQUIRE_AUTH": "false"}
        local_env = {"ASIE_ENV": "local", "ASIE_DIB_REQUIRE_AUTH": "false"}
        self.assertTrue(is_production_environment(production_env))
        self.assertFalse(is_production_environment(local_env))
        self.assertFalse(resolve_dib_auth_required("/api/dib/status", production_env))
        self.assertTrue(resolve_dib_auth_required("/api/dib/sessions", production_env))
        self.assertFalse(resolve_dib_auth_required("/api/dib/sessions", local_env))

    def test_route_permissions_are_precise(self) -> None:
        cases = {
            ("GET", "/api/dib/sessions"): DIB_READ_PERMISSION,
            ("POST", "/api/dib/sessions"): DIB_WRITE_PERMISSION,
            ("POST", "/api/dib/sessions/s1/approved-manifests"): DIB_APPROVE_MANIFEST_PERMISSION,
            ("POST", "/api/dib/sessions/s1/validation-gates"): DIB_RUN_GATE_PERMISSION,
            ("POST", "/api/dib/sessions/s1/project-run-readiness"): DIB_RUN_GATE_PERMISSION,
            ("POST", "/api/dib/sessions/s1/controlled-finance"): DIB_FINANCE_EXECUTE_PERMISSION,
            ("POST", "/api/dib/sessions/s1/snapshot-projection-handoff"): DIB_SNAPSHOT_HANDOFF_PERMISSION,
        }
        for (method, path), expected_permission in cases.items():
            with self.subTest(method=method, path=path):
                self.assertEqual(dib_route_security_policy(method, path)["permission_required"], expected_permission)
        status_policy = dib_route_security_policy("GET", "/api/dib/status")
        self.assertIsNone(status_policy["permission_required"])
        self.assertTrue(status_policy["public_route"])

    def test_principal_authorization_uses_role_permissions(self) -> None:
        viewer = Principal(user_id="u1", session_id="sess1", organization_id="org1", role="viewer")
        analyst = Principal(user_id="u2", session_id="sess2", organization_id="org1", role="analyst")
        reviewer = Principal(user_id="u3", session_id="sess3", organization_id="org1", role="reviewer")
        self.assertTrue(authorize_dib_request(viewer, "GET", "/api/dib/sessions/s1")["authorized"])
        self.assertFalse(authorize_dib_request(viewer, "POST", "/api/dib/sessions/s1/blueprints")["authorized"])
        self.assertTrue(authorize_dib_request(reviewer, "POST", "/api/dib/sessions/s1/approved-manifests")["authorized"])
        self.assertFalse(authorize_dib_request(reviewer, "POST", "/api/dib/sessions/s1/controlled-finance")["authorized"])
        self.assertTrue(authorize_dib_request(analyst, "POST", "/api/dib/sessions/s1/controlled-finance")["authorized"])
        self.assertTrue(authorize_dib_request(analyst, "POST", "/api/dib/sessions/s1/snapshot-projection-handoff")["authorized"])
        self.assertIn(DIB_WRITE_PERMISSION, ROLE_PERMISSIONS["analyst"])

    def test_audit_event_is_session_scoped_and_does_not_store_raw_payload(self) -> None:
        principal = Principal(user_id="u1", session_id="session_web", organization_id="org1", role="analyst")
        authorization = authorize_dib_request(principal, "POST", "/api/dib/sessions/dib_session_1/blueprints")
        event = build_dib_security_audit_event(
            method="POST",
            path="/api/dib/sessions/dib_session_1/blueprints",
            principal=principal,
            authorization=authorization,
            http_status=201,
            request_payload={"some": "payload"},
        )
        self.assertEqual(event["event_type"], "security.rbac.granted")
        self.assertEqual(event["session_id"], "dib_session_1")
        self.assertEqual(event["permission_required"], DIB_WRITE_PERMISSION)
        self.assertFalse(event["raw_payload_stored"])
        self.assertIn("request_payload_hash", event)
        self.assertEqual(extract_dib_session_id_from_path("/api/dib/sessions/dib_session_1/events"), "dib_session_1")

    def test_http_mount_exposes_security_status_without_enabling_network_or_snapshot(self) -> None:
        mount = DIBHttpMount()
        self.addCleanup(mount.close)
        status = mount.status()
        self.assertEqual(status["security_audit_rbac_id"], DIB_SECURITY_AUDIT_RBAC_ID)
        self.assertTrue(status["production_auth_bypass_blocked"])
        self.assertTrue(status["security_audit_rbac"]["rbac_enforced_on_sidecar"])
        self.assertFalse(status["external_fetch_enabled"])
        self.assertFalse(status["ai_provider_enabled"])
        self.assertFalse(status["finance_wiring_enabled"])
        self.assertFalse(status["snapshot_wiring_enabled"])
        route_policy = {route["path"]: route["security_policy"] for route in status["routes"]}
        self.assertEqual(route_policy["/api/dib/sessions/{session_id}/controlled-finance"]["permission_required"], DIB_FINANCE_EXECUTE_PERMISSION)

    def test_sidecar_source_enforces_rbac_and_production_auth_guard_without_freeze_mutation(self) -> None:
        http_source = HTTP_MOUNTING_PATH.read_text(encoding="utf-8")
        identity_source = IDENTITY_PATH.read_text(encoding="utf-8")
        security_source = SECURITY_PATH.read_text(encoding="utf-8")
        self.assertIn("resolve_dib_auth_required", http_source)
        self.assertIn("authorize_dib_request", http_source)
        self.assertIn("permission_denied", http_source)
        self.assertIn("security.rbac.granted", security_source)
        self.assertIn("security.rbac.denied", security_source)
        self.assertIn("production_auth_bypass_blocked", http_source)
        self.assertIn("dib.finance.execute", identity_source)
        self.assertIn("dib.snapshot.handoff", identity_source)
        self.assertFalse(_sidecar_auth_required("/api/dib/status"))
        assert_all_frozen_files_unchanged(PACKAGE_ROOT)


if __name__ == "__main__":
    unittest.main()
