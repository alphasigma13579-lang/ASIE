from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"


class CustomerLanguageFoundationTests(unittest.TestCase):
    def test_language_provider_is_mounted_at_the_application_root(self) -> None:
        main = (SRC / "main.tsx").read_text(encoding="utf-8")
        self.assertIn('import { CustomerLanguageProvider } from "./customerLanguage";', main)
        self.assertIn("<CustomerLanguageProvider>", main)
        self.assertIn("</CustomerLanguageProvider>", main)

    def test_language_contract_defaults_to_arabic_and_updates_document_direction(self) -> None:
        source = (SRC / "customerLanguage.tsx").read_text(encoding="utf-8")
        self.assertIn('const DEFAULT_CUSTOMER_LOCALE: CustomerLocale = "ar";', source)
        self.assertIn('document.documentElement.lang = locale;', source)
        self.assertIn('document.documentElement.dir = locale === "ar" ? "rtl" : "ltr";', source)
        self.assertIn("CUSTOMER_LOCALE_STORAGE_KEY", source)

    def test_unknown_customer_status_and_errors_fail_closed(self) -> None:
        source = (SRC / "customerLanguage.tsx").read_text(encoding="utf-8")
        self.assertIn('"حالة تحتاج مراجعة"', source)
        self.assertIn('"Status requires review"', source)
        self.assertIn('"تعذر إتمام الطلب.', source)
        self.assertIn('"The request could not be completed.', source)
        self.assertNotIn("return raw;", source)

    def test_customer_auth_never_renders_raw_provider_errors(self) -> None:
        source = (SRC / "AuthScreens.tsx").read_text(encoding="utf-8")
        self.assertIn("setError(customerErrorText(reason, locale));", source)
        self.assertNotRegex(source, re.compile(r"setError\([^\n]*\.message"))
        self.assertIn('minLength={6} maxLength={12} value={password}', source)
        self.assertIn('minLength={6} maxLength={12} value={newPassword}', source)

    def test_dib_engineering_routes_are_role_gated(self) -> None:
        main = (SRC / "main.tsx").read_text(encoding="utf-8")
        gate = (SRC / "EngineeringSurfaceGate.tsx").read_text(encoding="utf-8")
        routed_components = (
            "DIBE2EScenario",
            "DIBSnapshotProjectionHandoff",
            "DIBControlledFinanceWiring",
            "DIBManifestRunReadiness",
            "DIBIntakeItemGovernance",
            "DIBProjectEntryPoint",
            "DIBWorkspace",
        )
        for component in routed_components:
            self.assertIn(
                f"<EngineeringSurfaceGate><{component} /></EngineeringSurfaceGate>",
                main,
            )
        self.assertIn('identity.platform_role === "platform_admin"', gate)
        self.assertIn("customerErrorText(failure, locale)", gate)


if __name__ == "__main__":
    unittest.main()
