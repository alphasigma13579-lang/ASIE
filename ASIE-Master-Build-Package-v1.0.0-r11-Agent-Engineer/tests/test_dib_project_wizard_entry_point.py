from __future__ import annotations

import unittest
from pathlib import Path

from backend.dib_registry_admission import assert_all_frozen_files_unchanged

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
DIB_ENTRY_PATH = PACKAGE_ROOT / "src" / "DIBProjectEntryPoint.tsx"
MAIN_PATH = PACKAGE_ROOT / "src" / "main.tsx"
DIB_UI_PATH = PACKAGE_ROOT / "src" / "DIBWorkspace.tsx"


class DIBProjectWizardEntryPointTests(unittest.TestCase):
    def test_entry_point_declares_stage_and_loads_real_projects(self) -> None:
        source = DIB_ENTRY_PATH.read_text(encoding="utf-8")
        self.assertIn("DIB-LIVE-002L-PROJECT-WIZARD-ENTRY-POINT-v1", source)
        self.assertIn('import { fetchProjects } from "./api";', source)
        self.assertIn("اختر مشروعًا لفتح DIB", source)
        self.assertIn("#dib?project_id=", source)
        self.assertIn("openDIBForProject", source)
        self.assertIn("window.location.reload()", source)

    def test_main_mounts_entry_before_dib_workspace(self) -> None:
        main = MAIN_PATH.read_text(encoding="utf-8")
        self.assertIn('import { DIBProjectEntryPoint } from "./DIBProjectEntryPoint";', main)
        entry_index = main.index('currentHash.startsWith("#dib-entry")')
        workspace_index = main.index('currentHash.startsWith("#dib")')
        self.assertLess(entry_index, workspace_index)

    def test_entry_point_preserves_no_later_wiring_boundary(self) -> None:
        source = DIB_ENTRY_PATH.read_text(encoding="utf-8")
        self.assertIn("لا تشغّل Finance Engine", source)
        self.assertIn("ولا تنشئ Snapshot", source)
        self.assertIn("ولا تفعل AI Provider", source)
        self.assertIn("ولا تنفذ أي جلب شبكي خارجي", source)
        self.assertIn("Finance wiring =", source)
        self.assertIn("Snapshot wiring =", source)
        self.assertIn("Network Fetch =", source)
        self.assertNotIn("runProject(", source)
        self.assertNotIn("fetchSnapshot", source)
        self.assertNotIn("openai_api_key", source)

    def test_existing_dib_workspace_still_accepts_project_id_route(self) -> None:
        workspace = DIB_UI_PATH.read_text(encoding="utf-8")
        self.assertIn('new URLSearchParams(window.location.search).get("project_id")', workspace)
        self.assertIn('new URLSearchParams(hashQuery).get("project_id")', workspace)
        assert_all_frozen_files_unchanged(PACKAGE_ROOT)


if __name__ == "__main__":
    unittest.main()
