from __future__ import annotations

import unittest
from pathlib import Path

from backend.dib_registry_admission import assert_all_frozen_files_unchanged

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
DIB_CONTINUITY_PATH = PACKAGE_ROOT / "backend" / "dib_session_continuity.py"
DIB_PERSISTENCE_PATH = PACKAGE_ROOT / "backend" / "dib_persistence.py"
DIB_API_PATH = PACKAGE_ROOT / "backend" / "dib_api.py"
DIB_HTTP_PATH = PACKAGE_ROOT / "backend" / "dib_http_mounting.py"
DIB_UI_PATH = PACKAGE_ROOT / "src" / "DIBWorkspace.tsx"
DIB_API_CLIENT_PATH = PACKAGE_ROOT / "src" / "dibApi.ts"


class DIBSessionContinuityPackageTests(unittest.TestCase):
    def test_package_a_adds_session_query_api_without_later_wiring(self) -> None:
        continuity = DIB_CONTINUITY_PATH.read_text(encoding="utf-8")
        persistence = DIB_PERSISTENCE_PATH.read_text(encoding="utf-8")
        api = DIB_API_PATH.read_text(encoding="utf-8")
        http = DIB_HTTP_PATH.read_text(encoding="utf-8")
        self.assertIn("DIB-COMPLETION-PACKAGE-A-SESSION-CONTINUITY-v1", continuity)
        self.assertIn("list_dib_sessions_for_project", continuity)
        self.assertIn("store.list_session_ids_for_project", continuity)
        self.assertNotIn("store.connection", continuity)
        self.assertNotIn("SELECT session_id", continuity)
        self.assertIn("def list_session_ids_for_project", persistence)
        self.assertIn("WHERE project_id = ?", persistence)
        self.assertIn("status != 'closed'", persistence)
        self.assertIn("DIB session continuity detected Finance wiring enabled", continuity)
        self.assertIn("DIB session continuity detected Snapshot wiring enabled", continuity)
        self.assertIn("def _list_sessions", api)
        self.assertIn('parts == ["api", "dib", "sessions"]', api)
        self.assertIn("project_id", api)
        self.assertIn("resume_available", api)
        self.assertIn("latest_session", api)
        self.assertIn("_dispatch_path_with_optional_session_query", http)
        self.assertIn("clean_path == \"/api/dib/sessions\" and parsed.query", http)

    def test_frontend_exposes_resume_or_new_session_without_later_wiring(self) -> None:
        source = DIB_UI_PATH.read_text(encoding="utf-8")
        api_client = DIB_API_CLIENT_PATH.read_text(encoding="utf-8")
        self.assertIn("DIB_SESSION_CONTINUITY_UI_ID", source)
        self.assertIn("DIB-COMPLETION-PACKAGE-A-SESSION-CONTINUITY-v1", api_client)
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
