from __future__ import annotations

import json
import unittest
from pathlib import Path

from backend.dib_api import DIB_API_ROUTES
from backend.dib_http_mounting import (
    DIB_HTTP_MOUNTING_ID,
    DIB_HTTP_ROUTES,
    DIBHttpMountError,
    create_dib_http_mount,
    is_dib_http_route,
)
from backend.dib_registry_admission import assert_all_frozen_files_unchanged
from backend.dib_tenant_boundary import DIBTenantContext

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
FREEZE_MANIFEST = PACKAGE_ROOT / "docs" / "ASIE-AAS-Runtime-Freeze-Manifest-v1.0.json"


class DIBHttpMountingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.context = DIBTenantContext(
            organization_id="org_http_mount_test",
            user_id="user_http_mount_test",
            principal_session_id="principal_http_mount_test",
        )
        self.mount = create_dib_http_mount(
            trusted_internal_context=self.context,
            project_organization_resolver=lambda _project_id: self.context.organization_id,
        )
        self.addCleanup(self.mount.close)

    def test_freeze_manifest_does_not_freeze_local_http_gateway(self) -> None:
        manifest = json.loads(FREEZE_MANIFEST.read_text(encoding="utf-8"))
        frozen_paths = {entry["path"] for entry in manifest["frozen_files"]}
        self.assertNotIn("backend/asie_local_api.py", frozen_paths)
        self.assertIn("backend/project_run_workflow.py", frozen_paths)
        self.assertIn("backend/snapshot_assembly.py", frozen_paths)

    def test_dib_http_mount_status_exposes_controlled_routes(self) -> None:
        status = self.mount.status()
        self.assertEqual(status["mounting_id"], DIB_HTTP_MOUNTING_ID)
        self.assertEqual(status["route_count"], len(DIB_API_ROUTES))
        self.assertEqual([route["path"] for route in DIB_HTTP_ROUTES], [route["path"] for route in DIB_API_ROUTES])
        self.assertTrue(all(route["path"].startswith("/api/dib") for route in status["routes"]))
        self.assertEqual(status["mount_strategy"], "freeze_safe_dib_http_overlay")
        self.assertTrue(status["tenant_scope_enforced_on_sidecar"])
        self.assertTrue(status["tenant_boundary"]["organization_scope_required"])
        self.assertFalse(status["external_fetch_enabled"])
        self.assertFalse(status["ai_provider_enabled"])
        self.assertFalse(status["finance_wiring_enabled"])
        self.assertFalse(status["snapshot_wiring_enabled"])
        self.assertFalse(status["frozen_http_server_mutated"])
        self.assertFalse(status["frozen_runtime_files_mutated"])
        self.assertFalse(status["snapshot_assembly_mutated"])
        self.assertFalse(status["project_run_workflow_mutated"])

    def test_dib_http_mount_recognizes_only_dib_routes(self) -> None:
        self.assertTrue(is_dib_http_route("/api/dib/status"))
        self.assertTrue(is_dib_http_route("/api/dib/sessions/session_1/events"))
        self.assertFalse(is_dib_http_route("/api/projects"))
        self.assertFalse(is_dib_http_route("/api/snapshots/snap_1"))
        self.assertTrue(self.mount.matches("GET", "/api/dib/status"))
        self.assertTrue(self.mount.matches("POST", "/api/dib/sessions"))
        self.assertFalse(self.mount.matches("PATCH", "/api/dib/status"))
        self.assertFalse(self.mount.matches("GET", "/api/projects"))

    def test_dib_http_mount_executes_session_blueprint_manifest_gate_flow(self) -> None:
        session_response = self.mount.dispatch(
            "POST",
            "/api/dib/sessions",
            {
                "project_profile": {
                    "project_id": "project_http_mount_shawarma",
                    "name": "محل شاورما",
                    "sector": "Food Service",
                    "activity": "shawarma shop",
                    "location_country": "SA",
                }
            },
        ).to_public()
        self.assertEqual(session_response["status"], 201)
        self.assertEqual(session_response["http_mounting_id"], DIB_HTTP_MOUNTING_ID)
        self.assertEqual(session_response["session"]["organization_id"], self.context.organization_id)
        self.assertFalse(session_response["external_fetch_enabled"])
        self.assertFalse(session_response["finance_wiring_enabled"])
        self.assertFalse(session_response["snapshot_wiring_enabled"])
        session_id = session_response["session"]["session_id"]

        blueprint_response = self.mount.dispatch(
            "POST",
            f"/api/dib/sessions/{session_id}/blueprints",
            {
                "source": "manual_table",
                "intake_payload": {
                    "file_name": "manual",
                    "rows": [
                        {"input_key": "startup_cost", "label": "equipment", "value": 155000},
                        {"input_key": "monthly_fixed_cost", "label": "rent and salaries", "value": 36000},
                        {"input_key": "unit_price", "label": "meal price", "value": 18},
                        {"input_key": "variable_cost", "label": "ingredients", "value": 7},
                        {"input_key": "monthly_units", "label": "monthly sales", "value": 4200},
                    ],
                },
            },
        ).to_public()
        self.assertEqual(blueprint_response["status"], 201)
        self.assertEqual(blueprint_response["blueprint"]["payload"]["contract_id"], "dynamic.input.blueprint.v1")
        self.assertFalse(blueprint_response["snapshot_mutation"])

        manifest_response = self.mount.dispatch(
            "POST",
            f"/api/dib/sessions/{session_id}/approved-manifests",
            {},
        ).to_public()
        manifest = manifest_response["approved_manifest"]["payload"]
        self.assertEqual(manifest_response["status"], 201)
        self.assertEqual(manifest["contract_id"], "approved.input.manifest.v1")
        self.assertEqual(manifest["status"], "approved")
        self.assertNotIn("finance", manifest)
        self.assertFalse(manifest_response["finance_wiring_enabled"])
        self.assertFalse(manifest_response["snapshot_mutation"])

        gate_response = self.mount.dispatch(
            "POST",
            f"/api/dib/sessions/{session_id}/validation-gates",
            {},
        ).to_public()
        gate = gate_response["validation_gate"]["payload"]
        self.assertEqual(gate_response["status"], 201)
        self.assertEqual(gate["contract_id"], "manifest.validation.v1")
        self.assertEqual(gate["status"], "passed")
        self.assertNotIn("snapshot", gate)
        self.assertFalse(gate_response["finance_wiring_enabled"])
        self.assertFalse(gate_response["snapshot_mutation"])

        loaded = self.mount.dispatch("GET", f"/api/dib/sessions/{session_id}").to_public()["session"]
        self.assertEqual(loaded["status"], "validation_passed")
        self.assertEqual(loaded["organization_id"], self.context.organization_id)
        self.assertEqual(loaded["approved_manifest"]["contract_id"], "approved.input.manifest.v1")
        self.assertEqual(loaded["validation_gate"]["contract_id"], "manifest.validation.v1")
        self.assertFalse(loaded["external_fetch_enabled"])
        self.assertFalse(loaded["ai_provider_enabled"])

    def test_dib_http_mount_rejects_missing_context_for_nonpublic_routes(self) -> None:
        unscoped = create_dib_http_mount(
            project_organization_resolver=lambda _project_id: self.context.organization_id,
        )
        self.addCleanup(unscoped.close)
        with self.assertRaises(DIBHttpMountError) as context_error:
            unscoped.dispatch("POST", "/api/dib/sessions", {"project_id": "project_context_required"})
        self.assertEqual(context_error.exception.status, 403)
        self.assertEqual(context_error.exception.code, "dib_tenant_context_required")

    def test_dib_http_mount_rejects_forbidden_payloads_and_non_dib_routes(self) -> None:
        with self.assertRaises(DIBHttpMountError) as method_error:
            self.mount.dispatch("PATCH", "/api/dib/status", {})
        self.assertEqual(method_error.exception.status, 405)

        with self.assertRaises(DIBHttpMountError) as route_error:
            self.mount.dispatch("GET", "/api/projects", {})
        self.assertEqual(route_error.exception.status, 404)

        with self.assertRaises(DIBHttpMountError) as raw_prompt_error:
            self.mount.dispatch("POST", "/api/dib/sessions", {"project_id": "bad", "raw_prompt": "make numbers"})
        self.assertEqual(raw_prompt_error.exception.status, 422)

        with self.assertRaises(DIBHttpMountError) as network_error:
            self.mount.dispatch("POST", "/api/dib/sessions", {"project_id": "bad", "external_fetch_enabled": True})
        self.assertEqual(network_error.exception.status, 422)

        with self.assertRaises(DIBHttpMountError) as finance_error:
            self.mount.dispatch("POST", "/api/dib/sessions", {"project_id": "bad", "finance": {"status": "ready"}})
        self.assertEqual(finance_error.exception.status, 422)

        with self.assertRaises(DIBHttpMountError) as snapshot_error:
            self.mount.dispatch("POST", "/api/dib/sessions", {"project_id": "bad", "snapshot": {"id": "snap"}})
        self.assertEqual(snapshot_error.exception.status, 422)

    def test_frozen_runtime_files_remain_unchanged(self) -> None:
        assert_all_frozen_files_unchanged(PACKAGE_ROOT)


if __name__ == "__main__":
    unittest.main()
