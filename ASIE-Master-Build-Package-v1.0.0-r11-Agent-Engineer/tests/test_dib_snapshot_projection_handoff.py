from __future__ import annotations

import unittest
from pathlib import Path

from backend.dib_api import DIBApiError, create_dib_api_controller
from backend.dib_registry_admission import assert_all_frozen_files_unchanged
from backend.dib_snapshot_projection_handoff import (
    DIB_SNAPSHOT_PROJECTION_HANDOFF_ID,
    snapshot_projection_handoff_status,
)

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
DIB_HANDOFF_UI_PATH = PACKAGE_ROOT / "src" / "DIBSnapshotProjectionHandoff.tsx"
DIB_API_CLIENT_PATH = PACKAGE_ROOT / "src" / "dibApi.ts"
MAIN_PATH = PACKAGE_ROOT / "src" / "main.tsx"
DIB_API_PATH = PACKAGE_ROOT / "backend" / "dib_api.py"
DIB_HANDOFF_PATH = PACKAGE_ROOT / "backend" / "dib_snapshot_projection_handoff.py"
SNAPSHOT_ASSEMBLY_PATH = PACKAGE_ROOT / "backend" / "snapshot_assembly.py"
PROJECT_RUN_WORKFLOW_PATH = PACKAGE_ROOT / "backend" / "project_run_workflow.py"


class DIBSnapshotProjectionHandoffPackageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.controller = create_dib_api_controller()
        self.addCleanup(self.controller.close)

    def _start_session(self) -> dict:
        return self.controller.dispatch(
            "POST",
            "/api/dib/sessions",
            {"project_profile": {"project_id": "project_package_e", "name": "محل شاورما", "sector": "Food Service", "activity": "shawarma shop"}},
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
            {"source": "package_e_test", "intake_payload": {"file_name": "package-e", "rows": self._required_rows()}},
        )
        manifest = self.controller.dispatch("POST", f"/api/dib/sessions/{session_id}/approved-manifests", {}).to_public()["approved_manifest"]["payload"]
        self.assertEqual(manifest["status"], "approved")
        gate = self.controller.dispatch("POST", f"/api/dib/sessions/{session_id}/validation-gates", {}).to_public()["validation_gate"]["payload"]
        self.assertEqual(gate["status"], "passed")
        return session_id

    def test_package_e_status_and_route_are_declared_without_snapshot_assembly_mount(self) -> None:
        status = self.controller.dispatch("GET", "/api/dib/status").to_public()["dib_api"]
        handoff_status = snapshot_projection_handoff_status()
        self.assertEqual(status["snapshot_projection_handoff_id"], DIB_SNAPSHOT_PROJECTION_HANDOFF_ID)
        self.assertEqual(handoff_status["snapshot_projection_handoff_id"], DIB_SNAPSHOT_PROJECTION_HANDOFF_ID)
        route_paths = {route["path"] for route in status["routes"]}
        self.assertIn("/api/dib/sessions/{session_id}/snapshot-projection-handoff", route_paths)
        self.assertEqual(handoff_status["snapshot_assembly_mount"], "not_called")
        self.assertFalse(handoff_status["sealed_envelope_created"])
        self.assertFalse(status["external_fetch_enabled"])
        self.assertFalse(status["ai_provider_enabled"])
        self.assertFalse(status["finance_wiring_enabled"])
        self.assertFalse(status["snapshot_wiring_enabled"])

    def test_snapshot_projection_handoff_blocks_until_manifest_and_validation_gate_exist(self) -> None:
        session = self._start_session()
        response = self.controller.dispatch("POST", f"/api/dib/sessions/{session['session_id']}/snapshot-projection-handoff", {}).to_public()
        handoff = response["snapshot_projection_handoff"]
        self.assertEqual(handoff["status"], "blocked")
        self.assertFalse(response["snapshot_projection_handoff_prepared"])
        self.assertFalse(handoff["sealed_envelope_created"])
        self.assertEqual(handoff["snapshot_assembly_mount"], "not_called")
        self.assertIn("DIB_APPROVED_MANIFEST_MISSING", {row["code"] for row in handoff["blockers"]})

    def test_snapshot_projection_handoff_prepares_lineage_and_projection_support_without_sealing_snapshot(self) -> None:
        session_id = self._prepare_ready_session()
        response = self.controller.dispatch("POST", f"/api/dib/sessions/{session_id}/snapshot-projection-handoff", {}).to_public()
        handoff = response["snapshot_projection_handoff"]
        self.assertTrue(response["snapshot_projection_handoff_prepared"])
        self.assertEqual(handoff["status"], "prepared")
        self.assertEqual(handoff["contract_id"], "dib.snapshot.projection_handoff.v1")
        self.assertEqual(handoff["source_lineage_contract_id"], "dib.snapshot.lineage.v1")
        self.assertEqual(handoff["projection_support_contract_id"], "dib.snapshot.projection_support.v1")
        self.assertEqual(handoff["controlled_finance_reference_contract_id"], "dib.controlled.finance.reference.v1")
        self.assertEqual(handoff["lineage"]["contract_id"], "dib.snapshot.lineage.v1")
        self.assertEqual(handoff["projection_support"]["contract_id"], "dib.snapshot.projection_support.v1")
        self.assertEqual(handoff["controlled_finance_reference"]["input_source"], "approved_input_manifest_only")
        self.assertEqual(handoff["controlled_finance_reference"]["controlled_finance_status"], "executed")
        self.assertFalse(handoff["sealed_envelope_created"])
        self.assertFalse(response["snapshot_mutation"])
        self.assertEqual(handoff["snapshot_assembly_mount"], "not_called")
        self.assertEqual(handoff["project_run_workflow_mount"], "not_called")
        self.assertFalse(handoff["snapshot_wiring_enabled"])
        self.assertFalse(handoff["frozen_snapshot_assembly_mutated"])

    def test_snapshot_projection_handoff_rejects_forbidden_raw_payloads(self) -> None:
        session = self._start_session()
        with self.assertRaises(DIBApiError) as snapshot_error:
            self.controller.dispatch("POST", f"/api/dib/sessions/{session['session_id']}/snapshot-projection-handoff", {"snapshot": {"status": "unsafe"}})
        self.assertEqual(snapshot_error.exception.status, 422)
        with self.assertRaises(DIBApiError) as raw_error:
            self.controller.dispatch("POST", f"/api/dib/sessions/{session['session_id']}/snapshot-projection-handoff", {"raw_file": "unsafe"})
        self.assertEqual(raw_error.exception.status, 422)

    def test_frontend_package_e_surface_is_routed_and_does_not_call_snapshot_or_project_run_workflow(self) -> None:
        ui = DIB_HANDOFF_UI_PATH.read_text(encoding="utf-8")
        client = DIB_API_CLIENT_PATH.read_text(encoding="utf-8")
        main = MAIN_PATH.read_text(encoding="utf-8")
        api = DIB_API_PATH.read_text(encoding="utf-8")
        helper = DIB_HANDOFF_PATH.read_text(encoding="utf-8")
        snapshot_assembly = SNAPSHOT_ASSEMBLY_PATH.read_text(encoding="utf-8")
        project_run_workflow = PROJECT_RUN_WORKFLOW_PATH.read_text(encoding="utf-8")
        self.assertIn("DIB Completion Package E · Snapshot Projection Handoff", ui)
        self.assertIn("#dib-snapshot-handoff", main)
        self.assertIn("DIBSnapshotProjectionHandoff", main)
        self.assertIn("buildDIBSnapshotProjectionHandoff", client)
        self.assertIn("snapshot-projection-handoff", api)
        self.assertIn("DIB-COMPLETION-PACKAGE-E-SNAPSHOT-PROJECTION-HANDOFF-v1", helper)
        self.assertIn("assemble_snapshot", snapshot_assembly)
        self.assertIn("ProjectRunWorkflow", project_run_workflow)
        for source in (ui, client, api, helper):
            self.assertNotIn("runProject(", source)
            self.assertNotIn("fetchSnapshot", source)
            self.assertNotIn("ProjectRunWorkflow(", source)
            self.assertNotIn("assemble_snapshot(", source)
            self.assertNotIn("sealed_envelope_created: true", source)
            self.assertNotIn("snapshot_wiring_enabled: true", source)
        assert_all_frozen_files_unchanged(PACKAGE_ROOT)


if __name__ == "__main__":
    unittest.main()
