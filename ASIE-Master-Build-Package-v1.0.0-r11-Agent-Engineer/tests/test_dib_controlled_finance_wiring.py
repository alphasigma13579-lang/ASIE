from __future__ import annotations

import unittest
from pathlib import Path

from backend.dib_api import DIBApiError, create_dib_api_controller
from backend.dib_controlled_finance_wiring import (
    DIB_CONTROLLED_FINANCE_WIRING_ID,
    controlled_finance_wiring_status,
)
from backend.dib_registry_admission import assert_all_frozen_files_unchanged

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
DIB_FINANCE_UI_PATH = PACKAGE_ROOT / "src" / "DIBControlledFinanceWiring.tsx"
DIB_API_CLIENT_PATH = PACKAGE_ROOT / "src" / "dibApi.ts"
MAIN_PATH = PACKAGE_ROOT / "src" / "main.tsx"
DIB_API_PATH = PACKAGE_ROOT / "backend" / "dib_api.py"
DIB_FINANCE_PATH = PACKAGE_ROOT / "backend" / "dib_controlled_finance_wiring.py"
PROJECT_RUN_WORKFLOW_PATH = PACKAGE_ROOT / "backend" / "project_run_workflow.py"
MODULE_RUNTIME_PATH = PACKAGE_ROOT / "backend" / "module_runtime.py"


class DIBControlledFinanceWiringPackageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.controller = create_dib_api_controller()
        self.addCleanup(self.controller.close)

    def _start_session(self) -> dict:
        return self.controller.dispatch(
            "POST",
            "/api/dib/sessions",
            {"project_profile": {"project_id": "project_package_d", "name": "محل شاورما", "sector": "Food Service", "activity": "shawarma shop"}},
        ).to_public()["session"]

    def _required_rows(self) -> list[dict]:
        return [
            {"input_key": "startup_cost", "label": "تكلفة التأسيس", "value": 120000},
            {"input_key": "monthly_fixed_cost", "label": "التكاليف الشهرية الثابتة", "value": 42000},
            {"input_key": "unit_price", "label": "سعر الوحدة", "value": 18},
            {"input_key": "variable_cost", "label": "التكلفة المتغيرة للوحدة", "value": 7},
            {"input_key": "monthly_units", "label": "عدد الوحدات الشهري", "value": 4200},
        ]

    def _prepare_ready_session(self) -> str:
        session = self._start_session()
        session_id = session["session_id"]
        self.controller.dispatch(
            "POST",
            f"/api/dib/sessions/{session_id}/blueprints",
            {"source": "package_d_test", "intake_payload": {"file_name": "package-d", "rows": self._required_rows()}},
        )
        manifest = self.controller.dispatch("POST", f"/api/dib/sessions/{session_id}/approved-manifests", {}).to_public()["approved_manifest"]["payload"]
        self.assertEqual(manifest["status"], "approved")
        gate = self.controller.dispatch("POST", f"/api/dib/sessions/{session_id}/validation-gates", {}).to_public()["validation_gate"]["payload"]
        self.assertEqual(gate["status"], "passed")
        return session_id

    def test_package_d_status_and_route_are_declared_without_snapshot_or_project_run_workflow_mount(self) -> None:
        status = self.controller.dispatch("GET", "/api/dib/status").to_public()["dib_api"]
        finance_status = controlled_finance_wiring_status()
        self.assertEqual(status["controlled_finance_wiring_id"], DIB_CONTROLLED_FINANCE_WIRING_ID)
        self.assertEqual(finance_status["controlled_finance_wiring_id"], DIB_CONTROLLED_FINANCE_WIRING_ID)
        route_paths = {route["path"] for route in status["routes"]}
        self.assertIn("/api/dib/sessions/{session_id}/controlled-finance", route_paths)
        self.assertEqual(finance_status["project_run_workflow_mount"], "not_called")
        self.assertFalse(status["external_fetch_enabled"])
        self.assertFalse(status["ai_provider_enabled"])
        self.assertFalse(status["finance_wiring_enabled"])
        self.assertFalse(status["snapshot_wiring_enabled"])

    def test_controlled_finance_blocks_until_manifest_and_validation_gate_exist(self) -> None:
        session = self._start_session()
        response = self.controller.dispatch("POST", f"/api/dib/sessions/{session['session_id']}/controlled-finance", {}).to_public()
        controlled = response["controlled_finance"]
        self.assertEqual(controlled["status"], "blocked")
        self.assertEqual(controlled["finance_engine_execution_status"], "not_executed")
        self.assertFalse(response["controlled_finance_executed"])
        self.assertIn("DIB_APPROVED_MANIFEST_MISSING", {row["code"] for row in controlled["blockers"]})

    def test_controlled_finance_executes_only_from_approved_manifest_inputs(self) -> None:
        session_id = self._prepare_ready_session()
        response = self.controller.dispatch("POST", f"/api/dib/sessions/{session_id}/controlled-finance", {}).to_public()
        controlled = response["controlled_finance"]
        finance = controlled["finance"]
        self.assertTrue(response["controlled_finance_executed"])
        self.assertEqual(controlled["status"], "executed")
        self.assertEqual(controlled["input_contract_id"], "approved.input.manifest.v1")
        self.assertEqual(controlled["input_source"], "approved_input_manifest_only")
        self.assertEqual(controlled["finance_command_contract_id"], "finance.calculate.v1")
        self.assertEqual(controlled["finance_contract_id"], "finance.result.v1")
        self.assertEqual(controlled["project_run_workflow_mount"], "not_called")
        self.assertEqual(controlled["finance_engine_execution_status"], "executed")
        self.assertEqual(finance["status"], "ready")
        self.assertIsNotNone(finance["baseline"]["monthly_profit"])
        self.assertFalse(controlled["raw_ui_values_accepted"])
        self.assertFalse(controlled["raw_ai_values_accepted"])
        self.assertFalse(controlled["raw_file_values_accepted"])
        self.assertFalse(controlled["snapshot_wiring_enabled"])
        self.assertFalse(controlled["frozen_project_run_workflow_mutated"])

    def test_controlled_finance_rejects_forbidden_raw_or_finance_payloads(self) -> None:
        session = self._start_session()
        with self.assertRaises(DIBApiError) as finance_error:
            self.controller.dispatch("POST", f"/api/dib/sessions/{session['session_id']}/controlled-finance", {"finance": {"status": "run"}})
        self.assertEqual(finance_error.exception.status, 422)
        with self.assertRaises(DIBApiError) as raw_error:
            self.controller.dispatch("POST", f"/api/dib/sessions/{session['session_id']}/controlled-finance", {"raw_file": "unsafe"})
        self.assertEqual(raw_error.exception.status, 422)

    def test_frontend_package_d_surface_is_routed_and_does_not_call_project_run_or_snapshot(self) -> None:
        ui = DIB_FINANCE_UI_PATH.read_text(encoding="utf-8")
        client = DIB_API_CLIENT_PATH.read_text(encoding="utf-8")
        main = MAIN_PATH.read_text(encoding="utf-8")
        api = DIB_API_PATH.read_text(encoding="utf-8")
        finance_helper = DIB_FINANCE_PATH.read_text(encoding="utf-8")
        project_run_workflow = PROJECT_RUN_WORKFLOW_PATH.read_text(encoding="utf-8")
        module_runtime = MODULE_RUNTIME_PATH.read_text(encoding="utf-8")
        self.assertIn("DIB Completion Package D · Controlled Finance Wiring", ui)
        self.assertIn("#dib-finance-wiring", main)
        self.assertIn("DIBControlledFinanceWiring", main)
        self.assertIn("executeDIBControlledFinance", client)
        self.assertIn("controlled-finance", api)
        self.assertIn("DIB-COMPLETION-PACKAGE-D-CONTROLLED-FINANCE-WIRING-v1", finance_helper)
        self.assertIn("finance_result_set", finance_helper)
        self.assertIn("ProjectRunWorkflow", project_run_workflow)
        self.assertIn("FinanceModuleAdapter", module_runtime)
        for source in (ui, client, api, finance_helper):
            self.assertNotIn("runProject(", source)
            self.assertNotIn("fetchSnapshot", source)
            self.assertNotIn("ProjectRunWorkflow(", source)
            self.assertNotIn("assemble_snapshot(", source)
            self.assertNotIn("snapshot_wiring_enabled: true", source)
        assert_all_frozen_files_unchanged(PACKAGE_ROOT)


if __name__ == "__main__":
    unittest.main()
