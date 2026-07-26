from __future__ import annotations

import unittest
from pathlib import Path

from backend.dib_registry_admission import assert_all_frozen_files_unchanged

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
DIB_UI_PATH = PACKAGE_ROOT / "src" / "DIBWorkspace.tsx"
DIB_API_CLIENT_PATH = PACKAGE_ROOT / "src" / "dibApi.ts"


class DIBUILiveApiWiringTests(unittest.TestCase):
    def test_dib_workspace_declares_live_api_wiring_without_local_only_state_machine(self) -> None:
        source = DIB_UI_PATH.read_text(encoding="utf-8")
        self.assertIn("DIB-LIVE-002J-UI-LIVE-API-WIRING-v1", source)
        self.assertIn("from \"./dibApi\"", source)
        self.assertIn("fetchDIBStatus", source)
        self.assertIn("startDIBSession", source)
        self.assertIn("saveDIBBlueprint", source)
        self.assertIn("saveDIBApprovedManifest", source)
        self.assertIn("saveDIBValidationGate", source)
        self.assertIn("fetchDIBEvents", source)
        self.assertIn("/api/dib/...", source)
        self.assertIn("Bearer token", source)
        self.assertNotIn('setSessionStatus("manifest_approved")', source)
        self.assertNotIn('setSessionStatus("validation_passed")', source)

    def test_dib_api_client_uses_only_dib_routes_and_frontend_session_headers(self) -> None:
        source = DIB_API_CLIENT_PATH.read_text(encoding="utf-8")
        self.assertIn("DIB-LIVE-002J-UI-LIVE-API-WIRING-v1", source)
        self.assertIn("getSessionToken", source)
        self.assertIn("getActiveOrganizationId", source)
        self.assertIn("handleUnauthorized", source)
        expected_routes = [
            '"/api/dib/status"',
            '"/api/dib/sessions"',
            '`/api/dib/sessions/${sessionId}`',
            '`/api/dib/sessions/${sessionId}/blueprints`',
            '`/api/dib/sessions/${sessionId}/approved-manifests`',
            '`/api/dib/sessions/${sessionId}/validation-gates`',
            '`/api/dib/sessions/${sessionId}/events`',
            '`/api/dib/sessions/${sessionId}/close`',
        ]
        for route in expected_routes:
            self.assertIn(route, source)
        self.assertNotIn("/api/projects/", source)
        self.assertNotIn("/api/snapshots", source)
        self.assertNotIn("/api/runs", source)
        self.assertNotIn("runProject", source)
        self.assertNotIn("fetchSnapshot", source)
        self.assertNotIn("openai_api_key", source)

    def test_dib_workspace_keeps_forbidden_wiring_visible_and_disabled(self) -> None:
        source = DIB_UI_PATH.read_text(encoding="utf-8")
        self.assertIn("لا تشغيل Finance Engine من هذه الواجهة", source)
        self.assertIn("لا إنشاء Snapshot أو Decision Pack", source)
        self.assertIn("لا تفعيل AI Provider", source)
        self.assertIn("لا جلب شبكي أو مصدر خارجي", source)
        self.assertIn("finance_wiring_enabled=false", source)
        self.assertNotIn("runProject(", source)
        self.assertNotIn("fetchSnapshot", source)
        self.assertNotIn("saveDIBValidationGate(session.session_id, { finance", source)
        assert_all_frozen_files_unchanged(PACKAGE_ROOT)


if __name__ == "__main__":
    unittest.main()
