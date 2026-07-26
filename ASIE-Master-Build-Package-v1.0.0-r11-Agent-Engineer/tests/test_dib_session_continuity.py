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

    def test_query_api_lists_project_sessions_without_later_wiring(self) -> None:
        session = self.controller.dispatch(
            "POST",
            "/api/dib/sessions",
            {"project_profile": {"project_id": "project_resume_package_a", "name": "resume", "sector": "Food Service"}},
        ).to_public()["session"]

        response = self.controller.dispatch(
            "GET",
            "/api/dib/sessions?project_id=project_resume_package_a",
        ).to_public()

        self.assertEqual(response["status"], 200)
        self.assertEqual(response["session_continuity_id"], DIB_SESSION_CONTINUITY_ID)
        self.assertTrue(response["resume_available"])
        self.assertIn(session["session_id"], {item["session_id"] for item in response["sessions"]})
        self.assertEqual(response["latest_session"]["project_id"], "project_resume_package_a")
        self.assertFalse(response["finance_wiring_enabled"])
        self.assertFalse(response["snapshot_wiring_enabled"])

    def test_session_continuity_helper_hydrates_current_blueprint_for_restore(self) -> None:
        session = self.controller.dispatch(
            "POST",
            "/api/dib/sessions",
            {"project_profile": {"project_id": "project_restore_package_a", "name": "restore", "sector": "Food Service"}},
        ).to_public()["session"]
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

        sessions = list_dib_sessions_for_project(self.controller.store, "project_restore_package_a")
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0]["current_blueprint"]["contract_id"], "dynamic.input.blueprint.v1")
        self.assertFalse(sessions[0]["external_fetch_enabled"])
        self.assertFalse(sessions[0]["ai_provider_enabled"])
        self.assertFalse(sessions[0]["finance_wiring_enabled"])
        self.assertFalse(sessions[0]["snapshot_wiring_enabled"])

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
