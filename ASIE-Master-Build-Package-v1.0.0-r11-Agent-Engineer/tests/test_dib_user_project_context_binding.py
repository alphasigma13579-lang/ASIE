from __future__ import annotations

import unittest
from pathlib import Path

from backend.dib_registry_admission import assert_all_frozen_files_unchanged

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
DIB_UI_PATH = PACKAGE_ROOT / "src" / "DIBWorkspace.tsx"
MAIN_PATH = PACKAGE_ROOT / "src" / "main.tsx"


class DIBUserProjectContextBindingTests(unittest.TestCase):
    def test_workspace_declares_project_context_binding_and_loads_real_projects(self) -> None:
        source = DIB_UI_PATH.read_text(encoding="utf-8")
        self.assertIn("DIB-LIVE-002K-USER-PROJECT-CONTEXT-BINDING-v1", source)
        self.assertIn('import { fetchProjects } from "./api";', source)
        self.assertIn("projectProfileFromProject", source)
        self.assertIn("startDIBSession(boundProjectProfile)", source)
        self.assertIn("source: \"asie_user_project_context\"", source)
        self.assertIn("اختر مشروع ASIE", source)
        self.assertIn("/api/projects", source)

    def test_workspace_removes_fixed_demo_project_profile(self) -> None:
        source = DIB_UI_PATH.read_text(encoding="utf-8")
        self.assertNotIn("project_dib_workspace_live_shawarma", source)
        self.assertNotIn("محل شاورما — DIB Live API", source)
        self.assertNotIn("manual_ui_live_api", source)
        self.assertIn("selectedProject.project_id", source)
        self.assertIn("project_context", source)

    def test_project_bound_dib_route_supports_project_id_query_without_freeze_mutation(self) -> None:
        main = MAIN_PATH.read_text(encoding="utf-8")
        self.assertIn('currentHash.startsWith("#dib")', main)
        source = DIB_UI_PATH.read_text(encoding="utf-8")
        self.assertIn('new URLSearchParams(window.location.search).get("project_id")', source)
        self.assertIn('new URLSearchParams(hashQuery).get("project_id")', source)
        assert_all_frozen_files_unchanged(PACKAGE_ROOT)

    def test_bound_workspace_still_blocks_forbidden_later_wiring(self) -> None:
        source = DIB_UI_PATH.read_text(encoding="utf-8")
        self.assertIn("لا تشغيل Finance Engine من هذه الواجهة", source)
        self.assertIn("لا إنشاء Snapshot أو Decision Pack", source)
        self.assertIn("لا تفعيل AI Provider", source)
        self.assertIn("لا جلب شبكي أو مصدر خارجي", source)
        self.assertNotIn("runProject(", source)
        self.assertNotIn("fetchSnapshot", source)
        self.assertNotIn("openai_api_key", source)
        self.assertNotIn("finance_wiring_enabled: true", source)
        self.assertNotIn("snapshot_wiring_enabled: true", source)


if __name__ == "__main__":
    unittest.main()
