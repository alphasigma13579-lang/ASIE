from __future__ import annotations

import unittest
from pathlib import Path

from backend.dib_api import create_dib_api_controller
from backend.dib_intake_item_governance import (
    DIB_INTAKE_ITEM_GOVERNANCE_ID,
    intake_item_governance_status,
    supplier_quote_rows_from_text,
)
from backend.dib_registry_admission import assert_all_frozen_files_unchanged

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
DIB_UI_PATH = PACKAGE_ROOT / "src" / "DIBIntakeItemGovernance.tsx"
DIB_API_CLIENT_PATH = PACKAGE_ROOT / "src" / "dibApi.ts"
MAIN_PATH = PACKAGE_ROOT / "src" / "main.tsx"
DIB_API_PATH = PACKAGE_ROOT / "backend" / "dib_api.py"


class DIBIntakeItemGovernancePackageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.controller = create_dib_api_controller()
        self.addCleanup(self.controller.close)

    def _start_session(self):
        return self.controller.dispatch(
            "POST",
            "/api/dib/sessions",
            {"project_profile": {"project_id": "project_package_b", "name": "محل شاورما", "sector": "Food Service", "activity": "shawarma shop"}},
        ).to_public()["session"]

    def test_package_b_status_and_api_routes_are_declared_without_later_wiring(self) -> None:
        status = self.controller.dispatch("GET", "/api/dib/status").to_public()["dib_api"]
        governance = intake_item_governance_status()
        self.assertEqual(status["intake_item_governance_id"], DIB_INTAKE_ITEM_GOVERNANCE_ID)
        self.assertEqual(governance["governance_id"], DIB_INTAKE_ITEM_GOVERNANCE_ID)
        self.assertTrue(governance["template_registry_ui_ready"])
        self.assertTrue(governance["supplier_quote_text_intake_ready"])
        self.assertTrue(governance["customer_item_decision_workflow_ready"])
        route_paths = {route["path"] for route in status["routes"]}
        self.assertIn("/api/dib/sessions/{session_id}/template-registry", route_paths)
        self.assertIn("/api/dib/sessions/{session_id}/intake-items", route_paths)
        self.assertIn("/api/dib/sessions/{session_id}/item-decisions", route_paths)
        self.assertFalse(status["external_fetch_enabled"])
        self.assertFalse(status["ai_provider_enabled"])
        self.assertFalse(status["finance_wiring_enabled"])
        self.assertFalse(status["snapshot_wiring_enabled"])

    def test_supplier_quote_text_intake_and_customer_decision_flow(self) -> None:
        session = self._start_session()
        session_id = session["session_id"]

        template_response = self.controller.dispatch("POST", f"/api/dib/sessions/{session_id}/template-registry", {}).to_public()
        template = template_response["template_registry"]
        self.assertEqual(template["governance_id"], DIB_INTAKE_ITEM_GOVERNANCE_ID)
        self.assertIn("startup_cost", template["template_items"])
        self.assertGreaterEqual(len(template["questions"]), 1)
        self.assertFalse(template_response["finance_wiring_enabled"])

        rows = supplier_quote_rows_from_text(
            "معدات وتجهيزات 120000\n"
            "إيجار شهري 18000\n"
            "رواتب شهرية 22000\n"
            "سعر الوجبة 18\n"
            "تكلفة مواد مباشرة 7\n"
            "عدد المبيعات الشهري 4200"
        )
        self.assertIn("monthly_units", {row["input_key"] for row in rows})
        intake_response = self.controller.dispatch(
            "POST",
            f"/api/dib/sessions/{session_id}/intake-items",
            {"source_name": "supplier_quote_package_b", "supplier_quote_text": "\n".join(f"{row['label']} {row['value']}" for row in rows)},
        ).to_public()
        mapped_items = intake_response["mapped_items"]
        self.assertGreaterEqual(len(mapped_items), 5)
        self.assertTrue(intake_response["intake"]["supplier_quote_text_intake"])
        self.assertFalse(intake_response["finance_wiring_enabled"])
        self.assertFalse(intake_response["snapshot_wiring_enabled"])

        decision_response = self.controller.dispatch(
            "POST",
            f"/api/dib/sessions/{session_id}/item-decisions",
            {"item": mapped_items[0], "decision": {"action": "enter_value", "value": mapped_items[0]["value"], "reason": "customer_reviewed"}},
        ).to_public()
        self.assertEqual(decision_response["item_decision"]["governance_id"], DIB_INTAKE_ITEM_GOVERNANCE_ID)
        self.assertEqual(decision_response["item"]["value_state"], "USER_PROVIDED")
        self.assertFalse(decision_response["finance_wiring_enabled"])
        self.assertFalse(decision_response["snapshot_wiring_enabled"])

    def test_frontend_package_b_surface_is_routed_and_blocks_later_wiring(self) -> None:
        ui = DIB_UI_PATH.read_text(encoding="utf-8")
        client = DIB_API_CLIENT_PATH.read_text(encoding="utf-8")
        main = MAIN_PATH.read_text(encoding="utf-8")
        api = DIB_API_PATH.read_text(encoding="utf-8")
        self.assertIn("DIB Completion Package B · Intake & Item Governance", ui)
        self.assertIn("Template Registry UI", ui)
        self.assertIn("Supplier Quote Text Intake", ui)
        self.assertIn("Customer Item Decision Workflow", ui)
        self.assertIn("#dib-governance", main)
        self.assertIn("DIBIntakeItemGovernance", main)
        self.assertIn("resolveDIBTemplateRegistry", client)
        self.assertIn("previewDIBIntakeItems", client)
        self.assertIn("applyDIBItemDecision", client)
        self.assertIn("def _preview_intake_items", api)
        self.assertIn("def _apply_item_decision", api)
        for source in (ui, client):
            self.assertNotIn("runProject(", source)
            self.assertNotIn("fetchSnapshot", source)
            self.assertNotIn("openai_api_key", source)
            self.assertNotIn("finance_wiring_enabled: true", source)
            self.assertNotIn("snapshot_wiring_enabled: true", source)
        self.assertNotIn("runProject(", api)
        self.assertNotIn("fetchSnapshot", api)
        self.assertNotIn("finance_wiring_enabled: true", api)
        self.assertNotIn("snapshot_wiring_enabled: true", api)
        assert_all_frozen_files_unchanged(PACKAGE_ROOT)


if __name__ == "__main__":
    unittest.main()
