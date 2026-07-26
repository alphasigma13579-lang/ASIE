from __future__ import annotations

import unittest
from pathlib import Path

from backend.dib_api import create_dib_api_controller
from backend.dib_registry_admission import assert_all_frozen_files_unchanged
from backend.dib_session_continuity import DIB_SESSION_CONTINUITY_ID, list_dib_sessions_for_project

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
DIB_UI_PATH = PACKAGE_ROOT / "src" / "DIBWorkspace.tsx"
DIB_API_CLIENT_PATH = PACKAGE_ROOT / "src" / "dibApi.ts"


class DIBSessionContinuityPackageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.controller = create_dib_api_controller()
        self.addCleanup(self.controller.close)

    def _start_session(self, project_id: str):
        return self.controller.dispatch(
            "POST",
            "/api/dib/sessions",
            {"project_profile": {"project_id": project_id, "name": project_id, "sector": "Food Service"}},
        ).to_public()["session"]

    def test_query_api_lists_latest_project_sessions_and_excludes_closed_by_default(self) -> None:
        first = self._start_session("project_resume_package_a")
        second = self._start_session("project_resume_package_a")
        other = self._start_session("other_project")
        self.controller.dispatch("POST", f"/api/dib/sessions/{first['session_id']}/close", {}).to_public()

        response = self.controller.dispatch(
            "GET",
            "/api/dib/sessions?project_id=project_resume_package_a",
        ).to_public()
        self.assertEqual(response["status"], 200)
        self.assertEqual(response["session_continuity_id"], DIB_SESSION_CONTINUITY_ID)
        self.assertTrue(response["resume_available"])
        self.assertEqual([item["session_id"] for item in response["sessions"]], [second["session_id"]])
        self.assertEqual(response["latest_session"]["session_id"], second["session_id"])
        self.assertFalse(response["finance_wiring_enabled"])
        self.assertFalse(response["snapshot_wiring_enabled"])

        unrelated = self.controller.dispatch(
            "GET",
            f"/api/dib/sessions?project_id={other['project_id']}",
        ).to_public()["sessions"]
        self.assertEqual([item["session_id"] for item in unrelated], [other["session_id"]])

    def test_session_query_can_hydrate_blueprint_manifest_gate_for_restore(self) -> None:
        session = self._start_session("project_restore_package_a")
        session_id = session["session_id"]
        self.controller.dispatch(
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
        self.controller.dispatch("POST", f"/api/dib/sessions/{session_id}/approved-manifests", {}).to_public()
        self.controller.dispatch("POST", f"/api/dib/sessions/{session_id}/validation-gates", {}).to_public()

        sessions = list_dib_sessions_for_project(self.controller.store, "project_restore_package_a")
        self.assertEqual(len(sessions), 1)
        restored = sessions[0]
        self.assertEqual(restored["current_blueprint"]["contract_id"], "dynamic.input.blueprint.v1")
        self.assertEqual(restored["approved_manifest"]["contract_id"], "approved.input.manifest.v1")
        self.assertEqual(restored["validation_gate"]["contract_id"], "manifest.validation.v1")
        self.assertFalse(restored["external_fetch_enabled"])
        self.assertFalse(restored["ai_provider_enabled"])
        self.assertFalse(restored["finance_wiring_enabled"])
        self.assertFalse(restored["snapshot_wiring_enabled"])

    def test_workspace_exposes_resume_or_new_session_without_later_wiring(self) -> None:
        source = DIB_UI_PATH.read_text(encoding="utf-8")
        api_client = DIB_API_CLIENT_PATH.read_text(encoding="utf-8")
        self.assertIn("DIB-COMPLETION-PACKAGE-A-SESSION-CONTINUITY-v1", source)
        self.assertIn("fetchDIBSessionsForProject", source)
        self.assertIn("استئناف الجلسة السابقة", source)
        self.assertIn("استئناف آخر Session", source)
        self.assertIn("بدء Session جديدة", source)
        self.assertIn("restoreSessionState", source)
        self.assertIn("GET /api/dib/sessions?project_id={project_id}", source)
        self.assertIn("/api/dib/sessions?project_id=", api_client)
        self.assertNotIn("runProject(", source)
        self.assertNotIn("fetchSnapshot", source)
        self.assertNotIn("openai_api_key", source)
        self.assertNotIn("finance_wiring_enabled: true", source)
        self.assertNotIn("snapshot_wiring_enabled: true", source)
        assert_all_frozen_files_unchanged(PACKAGE_ROOT)


if __name__ == "__main__":
    unittest.main()
