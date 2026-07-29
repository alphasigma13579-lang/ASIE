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
CANONICAL_ADMISSION_PATH = PACKAGE_ROOT / "backend" / "dib_canonical_finance_admission.py"
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
            {
                "project_profile": {
                    "project_id": "project_package_d",
                    "name": "محل شاورما",
                    "sector": "Food Service",
                    "activity": "shawarma shop",
                }
            },
        ).to_public()["session"]

    @staticmethod
    def _required_rows() -> list[dict]:
        return [
            {"input_key": "startup_cost", "label": "تكلفة التأسيس", "value": 120000},
            {"input_key": "monthly_fixed_cost", "label": "التكاليف الشهرية الثابتة", "value": 42000},
            {"input_key": "unit_price", "label": "سعر الوحدة", "value": 18},
            {"input_key": "variable_cost", "label": "التكلفة المتغيرة للوحدة", "value": 7},
            {"input_key": "monthly_units", "label": "عدد الوحدات الشهري", "value": 4200},
        ]

    def _prepare_legacy_ready_session(self) -> str:
        session = self._start_session()
        session_id = session["session_id"]
        self.controller.dispatch(
            "POST",
            f"/api/dib/sessions/{session_id}/blueprints",
            {
                "source": "legacy_package_d_test",
                "intake_payload": {
                    "file_name": "package-d",
                    "rows": self._required_rows(),
                },
            },
        )
        self.controller.dispatch(
            "POST",
            f"/api/dib/sessions/{session_id}/approved-manifests",
            {},
        )
        self.controller.dispatch(
            "POST",
            f"/api/dib/sessions/{session_id}/validation-gates",
            {},
        )
        return session_id

    def test_status_declares_project_run_workflow_only(self) -> None:
        status = controlled_finance_wiring_status()
        self.assertEqual(DIB_CONTROLLED_FINANCE_WIRING_ID, status["controlled_finance_wiring_id"])
        self.assertEqual("project_run_workflow_only", status["finance_engine_execution_status"])
        self.assertEqual("required", status["project_run_workflow_mount"])
        self.assertFalse(status["direct_finance_import"])
        self.assertFalse(status["direct_finance_execution_enabled"])
        self.assertTrue(status["canonical_project_run_execution_enabled"])

    def test_internal_controller_cannot_execute_finance_even_with_legacy_ready_chain(self) -> None:
        session_id = self._prepare_legacy_ready_session()
        response = self.controller.dispatch(
            "POST",
            f"/api/dib/sessions/{session_id}/controlled-finance",
            {},
        ).to_public()
        controlled = response["controlled_finance"]
        self.assertFalse(response["controlled_finance_executed"])
        self.assertEqual("blocked", controlled["status"])
        self.assertIsNone(controlled["finance"])
        self.assertEqual("not_executed", controlled["finance_engine_execution_status"])
        self.assertEqual("required", controlled["project_run_workflow_mount"])
        self.assertIn(
            "DIB_DIRECT_FINANCE_PATH_REMOVED",
            {row["code"] for row in controlled["blockers"]},
        )

    def test_legacy_route_still_rejects_raw_or_finance_payloads(self) -> None:
        session = self._start_session()
        for payload in ({"finance": {"status": "run"}}, {"raw_file": "unsafe"}):
            with self.assertRaises(DIBApiError) as raised:
                self.controller.dispatch(
                    "POST",
                    f"/api/dib/sessions/{session['session_id']}/controlled-finance",
                    payload,
                )
            self.assertEqual(422, raised.exception.status)

    def test_frontend_compatibility_route_remains_without_direct_finance_import(self) -> None:
        ui = DIB_FINANCE_UI_PATH.read_text(encoding="utf-8")
        client = DIB_API_CLIENT_PATH.read_text(encoding="utf-8")
        main = MAIN_PATH.read_text(encoding="utf-8")
        api = DIB_API_PATH.read_text(encoding="utf-8")
        finance_helper = DIB_FINANCE_PATH.read_text(encoding="utf-8")
        canonical = CANONICAL_ADMISSION_PATH.read_text(encoding="utf-8")
        project_run_workflow = PROJECT_RUN_WORKFLOW_PATH.read_text(encoding="utf-8")
        module_runtime = MODULE_RUNTIME_PATH.read_text(encoding="utf-8")
        self.assertIn("DIB Completion Package D · Controlled Finance Wiring", ui)
        self.assertIn("#dib-finance-wiring", main)
        self.assertIn("DIBControlledFinanceWiring", main)
        self.assertIn("executeDIBControlledFinance", client)
        self.assertIn("controlled-finance", api)
        self.assertNotIn("from backend.finance_engine", finance_helper)
        self.assertNotIn("finance_result_set", finance_helper)
        self.assertNotIn("from backend.finance_engine", canonical)
        self.assertNotIn("finance_result_set", canonical)
        self.assertIn("ProjectRunWorkflow(", canonical)
        self.assertIn("ProjectRunWorkflow", project_run_workflow)
        self.assertIn("FinanceModuleAdapter", module_runtime)
        assert_all_frozen_files_unchanged(PACKAGE_ROOT)


if __name__ == "__main__":
    unittest.main()
