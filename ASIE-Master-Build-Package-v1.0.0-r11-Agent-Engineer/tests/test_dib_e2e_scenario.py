from __future__ import annotations

import json
import unittest
from pathlib import Path

from backend.dib_api import DIBApiError, create_dib_api_controller
from backend.dib_e2e_scenario import DIB_E2E_SCENARIO_ID, build_dib_e2e_scenario_report, dib_e2e_scenario_status
from backend.dib_registry_admission import assert_all_frozen_files_unchanged
from backend.dib_security_audit_rbac import DIB_RUN_GATE_PERMISSION, dib_route_security_policy

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
DIB_E2E_PATH = PACKAGE_ROOT / "backend" / "dib_e2e_scenario.py"
DIB_API_PATH = PACKAGE_ROOT / "backend" / "dib_api.py"
DIB_SECURITY_PATH = PACKAGE_ROOT / "backend" / "dib_security_audit_rbac.py"
DIB_E2E_UI_PATH = PACKAGE_ROOT / "src" / "DIBE2EScenario.tsx"
MAIN_PATH = PACKAGE_ROOT / "src" / "main.tsx"
FREEZE_MANIFEST = PACKAGE_ROOT / "docs" / "ASIE-AAS-Runtime-Freeze-Manifest-v1.0.json"
PROJECT_RUN_WORKFLOW_PATH = PACKAGE_ROOT / "backend" / "project_run_workflow.py"
SNAPSHOT_ASSEMBLY_PATH = PACKAGE_ROOT / "backend" / "snapshot_assembly.py"


class DIBE2EScenarioPackageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.controller = create_dib_api_controller()
        self.addCleanup(self.controller.close)

    def _required_rows(self) -> list[dict]:
        return [
            {"input_key": "startup_cost", "label": "تكلفة التأسيس", "value": 120000},
            {"input_key": "monthly_fixed_cost", "label": "التكاليف الشهرية الثابتة", "value": 42000},
            {"input_key": "unit_price", "label": "سعر الوحدة", "value": 18},
            {"input_key": "variable_cost", "label": "التكلفة المتغيرة للوحدة", "value": 7},
            {"input_key": "monthly_units", "label": "عدد الوحدات الشهري", "value": 4200},
        ]

    def _prepare_ready_session(self) -> str:
        session = self.controller.dispatch(
            "POST",
            "/api/dib/sessions",
            {"project_profile": {"project_id": "project_package_g", "name": "محل شاورما", "sector": "Food Service", "activity": "shawarma shop"}},
        ).to_public()["session"]
        session_id = session["session_id"]
        self.controller.dispatch(
            "POST",
            f"/api/dib/sessions/{session_id}/blueprints",
            {"source": "package_g_test", "intake_payload": {"file_name": "package-g", "rows": self._required_rows()}},
        )
        manifest = self.controller.dispatch("POST", f"/api/dib/sessions/{session_id}/approved-manifests", {}).to_public()["approved_manifest"]["payload"]
        self.assertEqual(manifest["status"], "approved")
        gate = self.controller.dispatch("POST", f"/api/dib/sessions/{session_id}/validation-gates", {}).to_public()["validation_gate"]["payload"]
        self.assertEqual(gate["status"], "passed")
        return session_id

    def test_package_g_status_route_and_security_policy_are_declared(self) -> None:
        status = self.controller.dispatch("GET", "/api/dib/status").to_public()["dib_api"]
        scenario_status = dib_e2e_scenario_status()
        self.assertEqual(status["e2e_scenario_id"], DIB_E2E_SCENARIO_ID)
        self.assertEqual(scenario_status["e2e_scenario_id"], DIB_E2E_SCENARIO_ID)
        route_paths = {route["path"] for route in status["routes"]}
        self.assertIn("/api/dib/sessions/{session_id}/e2e-scenario", route_paths)
        policy = dib_route_security_policy("POST", "/api/dib/sessions/s1/e2e-scenario")
        self.assertEqual(policy["permission_required"], DIB_RUN_GATE_PERMISSION)
        self.assertEqual(policy["audit_action"], "dib.e2e_scenario.report")
        self.assertEqual(scenario_status["project_run_workflow_mount"], "not_called")
        self.assertEqual(scenario_status["snapshot_assembly_mount"], "not_called")

    def test_e2e_scenario_blocks_until_required_artifacts_exist(self) -> None:
        session = self.controller.dispatch(
            "POST",
            "/api/dib/sessions",
            {"project_profile": {"project_id": "project_package_g_blocked", "name": "مشروع ناقص", "sector": "Retail"}},
        ).to_public()["session"]
        response = self.controller.dispatch("POST", f"/api/dib/sessions/{session['session_id']}/e2e-scenario", {}).to_public()
        report = response["e2e_scenario"]
        self.assertFalse(response["e2e_scenario_passed"])
        self.assertEqual(report["status"], "blocked")
        blocker_codes = {row["code"] for row in report["blockers"]}
        self.assertIn("DIB_E2E_ARTIFACT_MISSING_CURRENT_BLUEPRINT", blocker_codes)
        self.assertIn("DIB_E2E_ARTIFACT_MISSING_APPROVED_MANIFEST", blocker_codes)
        self.assertIn("DIB_E2E_ARTIFACT_MISSING_VALIDATION_GATE", blocker_codes)

    def test_e2e_scenario_passes_ready_manifest_finance_and_snapshot_handoff_flow(self) -> None:
        session_id = self._prepare_ready_session()
        response = self.controller.dispatch("POST", f"/api/dib/sessions/{session_id}/e2e-scenario", {}).to_public()
        report = response["e2e_scenario"]
        self.assertTrue(response["e2e_scenario_passed"])
        self.assertEqual(report["status"], "passed")
        step_statuses = {step["name"]: step["status"] for step in report["steps"]}
        self.assertEqual(step_statuses["project_context_bound"], "passed")
        self.assertEqual(step_statuses["dynamic_input_blueprint_available"], "passed")
        self.assertEqual(step_statuses["approved_input_manifest_available"], "passed")
        self.assertEqual(step_statuses["manifest_validation_gate_available"], "passed")
        self.assertEqual(step_statuses["manifest_to_run_readiness"], "passed")
        self.assertEqual(step_statuses["controlled_finance_executed"], "passed")
        self.assertEqual(step_statuses["snapshot_projection_handoff_prepared"], "passed")
        self.assertEqual(report["controlled_finance_status"], "executed")
        self.assertEqual(report["snapshot_projection_handoff_status"], "prepared")
        self.assertEqual(report["project_run_workflow_mount"], "not_called")
        self.assertEqual(report["snapshot_assembly_mount"], "not_called")
        self.assertFalse(report["sealed_envelope_created"])
        self.assertFalse(report["decision_pack_created"])
        self.assertFalse(report["external_fetch_enabled"])
        self.assertFalse(report["ai_provider_enabled"])
        self.assertFalse(report["snapshot_wiring_enabled"])

    def test_e2e_helper_rejects_forbidden_raw_payloads(self) -> None:
        with self.assertRaises(ValueError):
            build_dib_e2e_scenario_report({"session_id": "s1", "project_id": "p1", "project_profile": {}, "raw_file": "unsafe"})
        session_id = self._prepare_ready_session()
        with self.assertRaises(DIBApiError) as raw_error:
            self.controller.dispatch("POST", f"/api/dib/sessions/{session_id}/e2e-scenario", {"openai_api_key": "unsafe"})
        self.assertEqual(raw_error.exception.status, 422)

    def test_frontend_e2e_surface_is_routed_and_freeze_safe(self) -> None:
        ui = DIB_E2E_UI_PATH.read_text(encoding="utf-8")
        main = MAIN_PATH.read_text(encoding="utf-8")
        api = DIB_API_PATH.read_text(encoding="utf-8")
        security = DIB_SECURITY_PATH.read_text(encoding="utf-8")
        helper = DIB_E2E_PATH.read_text(encoding="utf-8")
        freeze = json.loads(FREEZE_MANIFEST.read_text(encoding="utf-8"))
        frozen_paths = {entry["path"] for entry in freeze["frozen_files"]}
        self.assertIn("DIB Completion Package G", ui)
        self.assertIn("#dib-e2e-scenario", main)
        self.assertIn("DIBE2EScenario", main)
        self.assertIn("/e2e-scenario", api)
        self.assertIn("dib.e2e_scenario.report", security)
        self.assertIn("DIB-COMPLETION-PACKAGE-G-E2E-SCENARIO-v1", helper)
        self.assertIn("backend/project_run_workflow.py", frozen_paths)
        self.assertIn("backend/snapshot_assembly.py", frozen_paths)
        project_run_workflow = PROJECT_RUN_WORKFLOW_PATH.read_text(encoding="utf-8")
        snapshot_assembly = SNAPSHOT_ASSEMBLY_PATH.read_text(encoding="utf-8")
        self.assertIn("ProjectRunWorkflow", project_run_workflow)
        self.assertIn("assemble_snapshot", snapshot_assembly)
        for source in (ui, api, security, helper):
            self.assertNotIn("runProject(", source)
            self.assertNotIn("fetchSnapshot", source)
            self.assertNotIn("ProjectRunWorkflow(", source)
            self.assertNotIn("assemble_snapshot(", source)
            self.assertNotIn("snapshot_wiring_enabled: true", source)
            self.assertNotIn("ai_provider_enabled: true", source)
        assert_all_frozen_files_unchanged(PACKAGE_ROOT)


if __name__ == "__main__":
    unittest.main()
