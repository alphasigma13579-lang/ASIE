from __future__ import annotations

import unittest
from pathlib import Path

from backend.dib_registry_admission import assert_all_frozen_files_unchanged

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
DIB_UI_PATH = PACKAGE_ROOT / "src" / "DIBWorkspace.tsx"
MAIN_PATH = PACKAGE_ROOT / "src" / "main.tsx"


class DIBArabicUIWorkspaceTests(unittest.TestCase):
    def test_dib_workspace_declares_arabic_rtl_ui_and_routes(self) -> None:
        source = DIB_UI_PATH.read_text(encoding="utf-8")
        self.assertIn("DIB-LIVE-002E-ARABIC-UI-WORKSPACE-v1", source)
        self.assertIn('dir="rtl"', source)
        self.assertIn("مساحة Dynamic Input Blueprint", source)
        self.assertIn("GET /api/dib/status", source)
        self.assertIn("POST /api/dib/sessions/{session_id}/validation-gates", source)
        self.assertIn("Approved Input Manifest", source)
        self.assertIn("Manifest Validation Gate", source)

    def test_dib_workspace_blocks_later_wiring_in_visible_copy(self) -> None:
        source = DIB_UI_PATH.read_text(encoding="utf-8")
        blocked_boundaries = [
            "لا تشغيل Finance Engine من هذه الواجهة",
            "لا إنشاء Snapshot أو Decision Pack",
            "لا تفعيل AI Provider",
            "لا جلب شبكي أو مصدر خارجي",
            "لا قبول raw prompt أو مفاتيح API",
        ]
        for boundary in blocked_boundaries:
            self.assertIn(boundary, source)
        self.assertNotIn("runProject(", source)
        self.assertNotIn("fetchSnapshot", source)
        self.assertNotIn("openai_api_key", source)

    def test_dib_workspace_is_hash_mounted_without_local_api_mutation(self) -> None:
        main = MAIN_PATH.read_text(encoding="utf-8")
        self.assertIn("DIBWorkspace", main)
        self.assertIn('currentHash.startsWith("#dib")', main)
        assert_all_frozen_files_unchanged(PACKAGE_ROOT)


if __name__ == "__main__":
    unittest.main()
