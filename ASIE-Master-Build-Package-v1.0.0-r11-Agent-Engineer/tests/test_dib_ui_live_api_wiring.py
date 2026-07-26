from __future__ import annotations

import unittest
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
DIB_UI_PATH = PACKAGE_ROOT / "src" / "DIBWorkspace.tsx"
DIB_API_CLIENT_PATH = PACKAGE_ROOT / "src" / "dibApi.ts"


class DIBUILiveApiWiringTests(unittest.TestCase):
    def test_dib_workspace_and_client_expose_live_api_wiring_marker(self) -> None:
        ui = DIB_UI_PATH.read_text(encoding="utf-8")
        client = DIB_API_CLIENT_PATH.read_text(encoding="utf-8")
        self.assertIn("DIB-LIVE-002J-UI-LIVE-API-WIRING-v1", ui)
        self.assertIn("DIB-LIVE-002J-UI-LIVE-API-WIRING-v1", client)
        self.assertIn("from \"./dibApi\"", ui)
        self.assertIn("getSessionToken", client)
        self.assertIn("getActiveOrganizationId", client)
        self.assertIn("handleUnauthorized", client)

    def test_dib_client_declares_dib_api_route_family_only(self) -> None:
        client = DIB_API_CLIENT_PATH.read_text(encoding="utf-8")
        self.assertIn("/api/dib/status", client)
        self.assertIn("/api/dib/sessions", client)
        self.assertIn("/blueprints", client)
        self.assertIn("/approved-manifests", client)
        self.assertIn("/validation-gates", client)
        self.assertIn("/events", client)
        self.assertIn("/close", client)


if __name__ == "__main__":
    unittest.main()
