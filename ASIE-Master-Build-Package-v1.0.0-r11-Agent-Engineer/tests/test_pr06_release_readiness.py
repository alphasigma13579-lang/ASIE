from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PR06ReleaseReadinessTests(unittest.TestCase):
    def test_document_language_and_rtl_shell_are_declared(self) -> None:
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn('<html lang="ar" dir="rtl">', html)
        self.assertIn('href="#main-content"', html)

    def test_accessibility_baseline_includes_skip_link_focus_and_alerts(self) -> None:
        css = (ROOT / "src" / "styles.css").read_text(encoding="utf-8")
        app = (ROOT / "src" / "App.tsx").read_text(encoding="utf-8")
        admin = (ROOT / "src" / "AdminConsole.tsx").read_text(encoding="utf-8")
        self.assertIn(".skip-link", css)
        self.assertIn(":focus-visible", css)
        self.assertIn('role="alert"', app)
        self.assertIn('role="alert"', admin)

    def test_browser_clients_only_call_relative_api_paths(self) -> None:
        for source in (ROOT / "src" / "api.ts", ROOT / "src" / "AdminConsole.tsx"):
            body = source.read_text(encoding="utf-8")
            self.assertNotIn('fetch("http', body)
            self.assertNotIn("fetch('http", body)

    def test_external_admission_remains_disabled_in_runtime_and_control_plane(self) -> None:
        api = (ROOT / "backend" / "asie_local_api.py").read_text(encoding="utf-8")
        operations = (ROOT / "backend" / "operations.py").read_text(encoding="utf-8")
        self.assertIn('"external_payments_enabled": False', api)
        self.assertIn('"external_notifications_enabled": False', api)
        self.assertIn('"external_access_enabled": False', operations)


if __name__ == "__main__":
    unittest.main()
