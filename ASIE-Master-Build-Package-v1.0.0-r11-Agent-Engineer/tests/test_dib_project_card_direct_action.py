from __future__ import annotations

import unittest
from pathlib import Path

from backend.dib_registry_admission import assert_all_frozen_files_unchanged

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
DIRECT_ACTION_PATH = PACKAGE_ROOT / "src" / "DIBProjectCardDirectAction.tsx"
MAIN_PATH = PACKAGE_ROOT / "src" / "main.tsx"


class DIBProjectCardDirectActionTests(unittest.TestCase):
    def test_direct_action_mount_declares_stage_and_uses_real_projects(self) -> None:
        source = DIRECT_ACTION_PATH.read_text(encoding="utf-8")
        self.assertIn("DIB-LIVE-002M-PROJECT-CARD-DIRECT-DIB-ACTION-v1", source)
        self.assertIn('import { fetchProjects } from "./api";', source)
        self.assertIn("items.slice(0, 6)", source)
        self.assertIn("data-dib-project-card-action", source)
        self.assertIn("project.project_id", source)

    def test_direct_action_opens_project_bound_dib_route(self) -> None:
        source = DIRECT_ACTION_PATH.read_text(encoding="utf-8")
        self.assertIn("#dib?project_id=", source)
        self.assertIn("encodeURIComponent(projectId)", source)
        self.assertIn("window.location.hash = dibProjectUrl(projectId)", source)
        self.assertIn("window.location.reload()", source)
        self.assertIn("افتح DIB", source)

    def test_main_never_mounts_engineering_direct_action_in_customer_routes(self) -> None:
        main = MAIN_PATH.read_text(encoding="utf-8")
        self.assertNotIn('import { DIBProjectCardDirectActionMount } from "./DIBProjectCardDirectAction";', main)
        self.assertNotIn("showDIBCardDirectAction", main)
        self.assertNotIn("<DIBProjectCardDirectActionMount />", main)
        self.assertIn("<EngineeringSurfaceGate><DIBWorkspace /></EngineeringSurfaceGate>", main)

    def test_direct_action_preserves_no_later_wiring_boundary(self) -> None:
        source = DIRECT_ACTION_PATH.read_text(encoding="utf-8")
        self.assertNotIn("runProject(", source)
        self.assertNotIn("fetchSnapshot", source)
        self.assertNotIn("openai_api_key", source)
        self.assertNotIn("finance_wiring_enabled: true", source)
        self.assertNotIn("snapshot_wiring_enabled: true", source)
        assert_all_frozen_files_unchanged(PACKAGE_ROOT)


if __name__ == "__main__":
    unittest.main()
