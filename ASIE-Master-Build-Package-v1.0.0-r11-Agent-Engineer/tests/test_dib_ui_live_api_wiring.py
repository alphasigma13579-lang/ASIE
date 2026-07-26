from __future__ import annotations

import unittest
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
DIB_UI_PATH = PACKAGE_ROOT / "src" / "DIBWorkspace.tsx"
DIB_API_CLIENT_PATH = PACKAGE_ROOT / "src" / "dibApi.ts"


class DIBUILiveApiWiringTests(unittest.TestCase):
    def test_dib_workspace_uses_live_dib_api_client(self) -> None:
        source = DIB_UI_PATH.read_text(encoding="utf-8")
        for token in [
            "DIB-LIVE-002J-UI-LIVE-API-WIRING-v1",
            "from \"./dibApi\"",
            "fetchDIBStatus",
            "startDIBSession",
            "saveDIBBlueprint",
            "saveDIBApprovedManifest",
            "saveDIBValidationGate",
            "fetchDIBEvents",
            "Bearer token",
        ]:
            self.assertIn(token, source)
        self.assertNotIn('setSessionStatus("manifest_approved")', source)
        self.assertNotIn('setSessionStatus("validation_passed")', source)

    def test_dib_api_client_is_dib_only_and_uses_frontend_session_context(self) -> None:
        source = DIB_API_CLIENT_PATH.read_text(encoding="utf-8")
        for token in [
            "DIB-LIVE-002J-UI-LIVE-API-WIRING-v1",
            "getSessionToken",
            "getActiveOrganizationId",
            "handleUnauthorized",
            "/api/dib/status",
            "/api/dib/sessions",
            "/blueprints",
            "/approved-manifests",
            "/validation-gates",
            "/events",
            "/close",
        ]:
            self.assertIn(token, source)
        for forbidden in ["/api/projects/", "/api/snapshots", "/api/runs", "runProject", "fetchSnapshot", "openai_api_key"]:
            self.assertNotIn(forbidden, source)

    def test_dib_workspace_keeps_forbidden_wiring_visible(self) -> None:
        source = DIB_UI_PATH.read_text(encoding="utf-8")
        for boundary in [
            "لا تشغيل Finance Engine من هذه الواجهة",
            "لا إنشاء Snapshot أو Decision Pack",
            "لا تفعيل AI Provider",
            "لا جلب شبكي أو مصدر خارجي",
            "لا قبول raw prompt أو مفاتيح API",
        ]:
            self.assertIn(boundary, source)
        self.assertNotIn("runProject(", source)
        self.assertNotIn("fetchSnapshot", source)


if __name__ == "__main__":
    unittest.main()
