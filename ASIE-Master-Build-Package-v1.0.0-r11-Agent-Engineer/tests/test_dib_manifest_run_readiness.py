from __future__ import annotations

import unittest
from pathlib import Path

from backend.dib_api import DIBApiError, create_dib_api_controller
from backend.dib_manifest_run_readiness import DIB_MANIFEST_RUN_READINESS_ID, manifest_run_readiness_status
from backend.dib_registry_admission import assert_all_frozen_files_unchanged

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
DIB_READINESS_UI_PATH = PACKAGE_ROOT / "src" / "DIBManifestRunReadiness.tsx"
DIB_API_CLIENT_PATH = PACKAGE_ROOT / "src" / "dibApi.ts"
MAIN_PATH = PACKAGE_ROOT / "src" / "main.tsx"
DIB_API_PATH = PACKAGE_ROOT / "backend" / "dib_api.py"
DIB_READINESS_PATH = PACKAGE_ROOT / "backend" / "dib_manifest_run_readiness.py"
DIB_PROJECT_RUN_GATE_PATH = PACKAGE_ROOT / "backend" / "dib_project_run_gate.py"


class DIBManifestRunReadinessPackageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.controller = create_dib_api_controller()
        self.addCleanup(self.controller.close)

    def _start_session(self) -> dict:
        return self.controller.dispatch(
            "POST",
            "/api/dib/sessions",
            {"project_profile": {"project_id": "project_package_c", "name": "محل شاورما", "sector": "Food Service", "activity": "shawarma shop"}},
        ).to_public()["session"]

    def _required_rows(self) -> list[dict]:
        return [
            {"input_key": "startup_cost", "label": "تكلفة التأسيس", "value": 120000},
            {"input_key": "monthly_fixed_cost", "label": "التكاليف الشهرية الثابتة", "value": 42000},
            {"input_key": "unit_price", "label": "سعر الوحدة", "value": 18},
            {"input_key": "variable_cost", "label": "التكلفة المتغيرة للوحدة", "value": 7},
            {"input_key": "monthly_units", "label": "عدد الوحدات الشهري", "value": 4200},
        ]

    def test_package_c_status_and_api_route_are_declared_without_later_wiring(self) -> None:
        status = self.controller.dispatch("GET", "/api/dib/status").to_public()["dib_api"]
        readiness_status = manifest_run_readiness_status()
        self.assertEqual(status["manifest_run_readiness_id"], DIB_MANIFEST_RUN_READINESS_ID)
        self.assertEqual(readiness_status["readiness_id"], DIB_MANIFEST_RUN_READINESS_ID)
        route_paths = {route["path"] for route in status["routes"]}
        self.assertIn("/api/dib/sessions/{session_id}/project-run-readiness", route_paths)
        self.assertEqual(readiness_status["finance_engine_execution_status"], "not_executed")
        self.assertEqual(readiness_status["project_run_workflow_mount"], "not_called")
        self.assertFalse(status["external_fetch_enabled"])
        self.assertFalse(status["ai_provider_enabled"])
        self.assertFalse(status["finance_wiring_enabled"])
        self.assertFalse(status["snapshot_wiring_enabled"])

    def test_manifest_to_run_readiness_handoff_does_not_execute_finance_or_snapshot(self) -> None:
        session = self._start_session()
        session_id = session["session_id"]

        blocked = self.controller.dispatch("POST", f"/api/dib/sessions/{session_id}/project-run-readiness", {}).to_public()
        self.assertFalse(blocked["ready_for_project_run"])
        self.assertEqual(blocked["project_run_readiness"]["status"], "blocked")
        self.assertIn("DIB_APPROVED_MANIFEST_MISSING", {row["code"] for row in blocked["project_run_readiness"]["blockers"]})

        blueprint = self.controller.dispatch(
            "POST",
            f"/api/dib/sessions/{session_id}/blueprints",
            {"source": "package_c_test", "intake_payload": {"file_name": "package-c", "rows": self._required_rows()}},
        ).to_public()["blueprint"]["payload"]
        self.assertEqual(blueprint["contract_id"], "dynamic.input.blueprint.v1")

        manifest = self.controller.dispatch("POST", f"/api/dib/sessions/{session_id}/approved-manifests", {}).to_public()["approved_manifest"]["payload"]
        self.assertEqual(manifest["status"], "approved")
        gate = self.controller.dispatch("POST", f"/api/dib/sessions/{session_id}/validation-gates", {}).to_public()["validation_gate"]["payload"]
        self.assertEqual(gate["status"], "passed")

        ready = self.controller.dispatch("POST", f"/api/dib/sessions/{session_id}/project-run-readiness", {}).to_public()
        readiness = ready["project_run_readiness"]
        request = ready["project_run_request"]
        self.assertTrue(ready["ready_for_project_run"])
        self.assertEqual(readiness["status"], "ready")
        self.assertEqual(readiness["finance_engine_execution_status"], "not_executed")
        self.assertEqual(readiness["project_run_workflow_mount"], "not_called")
        self.assertEqual(request["input_contract_id"], "approved.input.manifest.v1")
        self.assertEqual(request["input_source"], "approved_input_manifest_only")
        self.assertTrue(request["requires_project_run_workflow_mount"])
        self.assertFalse(request["finance_wiring_enabled"])
        self.assertFalse(request["snapshot_wiring_enabled"])
        self.assertFalse(ready["finance_wiring_enabled"])
        self.assertFalse(ready["snapshot_wiring_enabled"])

    def test_project_run_readiness_rejects_forbidden_payloads(self) -> None:
        session = self._start_session()
        with self.assertRaises(DIBApiError) as finance_error:
            self.controller.dispatch("POST", f"/api/dib/sessions/{session['session_id']}/project-run-readiness", {"finance": {"status": "run"}})
        self.assertEqual(finance_error.exception.status, 422)

    def test_frontend_package_c_surface_is_routed_and_blocks_later_wiring(self) -> None:
        ui = DIB_READINESS_UI_PATH.read_text(encoding="utf-8")
        client = DIB_API_CLIENT_PATH.read_text(encoding="utf-8")
        main = MAIN_PATH.read_text(encoding="utf-8")
        api = DIB_API_PATH.read_text(encoding="utf-8")
        readiness = DIB_READINESS_PATH.read_text(encoding="utf-8")
        project_gate = DIB_PROJECT_RUN_GATE_PATH.read_text(encoding="utf-8")
        self.assertIn("DIB Completion Package C · Manifest-to-Run Readiness", ui)
        self.assertIn("#dib-run-readiness", main)
        self.assertIn("DIBManifestRunReadiness", main)
        self.assertIn("buildDIBProjectRunReadiness", client)
        self.assertIn("project-run-readiness", api)
        self.assertIn("DIB-COMPLETION-PACKAGE-C-MANIFEST-RUN-READINESS-v1", readiness)
        self.assertIn("build_project_run_request_from_dib_manifest", readiness)
        self.assertIn("requires_project_run_workflow_mount", project_gate)
        for source in (ui, client):
            self.assertNotIn("openai_api_key", source)
        for source in (ui, client, api, readiness):
            self.assertNotIn("runProject(", source)
            self.assertNotIn("fetchSnapshot", source)
            self.assertNotIn("finance_wiring_enabled: true", source)
            self.assertNotIn("snapshot_wiring_enabled: true", source)
        assert_all_frozen_files_unchanged(PACKAGE_ROOT)


if __name__ == "__main__":
    unittest.main()
