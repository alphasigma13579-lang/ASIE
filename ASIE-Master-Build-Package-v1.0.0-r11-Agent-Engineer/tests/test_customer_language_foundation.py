from __future__ import annotations

import re
import unittest
from pathlib import Path

from backend.customer_presentation import safe_narrative
from backend.decision_pack import render_decision_pack_html


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
        self.assertEqual("تفصيل يحتاج مراجعة قبل عرضه", safe_narrative("finance engine failed", "ar"))
        self.assertEqual("Detail requires review before display", safe_narrative("runtime failure", "en"))

    def test_unreviewed_memo_explains_review_status_in_both_languages(self) -> None:
        pack = {"memo": {"review_status": "draft_review"}}
        for locale, expected in (("ar", "بانتظار المراجعة"), ("en", "Awaiting review")):
            with self.subTest(locale=locale):
                rendered = render_decision_pack_html(pack, locale=locale)
                self.assertIn(expected, rendered)
                self.assertNotIn("draft_review", rendered)

    def test_input_controls_and_review_progress_use_selected_language(self) -> None:
        app = (SRC / "App.tsx").read_text(encoding="utf-8")
        self.assertIn('text("زيادة", "Increase")', app)
        self.assertIn('text("إنقاص", "Decrease")', app)
        self.assertIn('{text("من", "of")} {assumptions.length} {text("مكتملة", "complete")}', app)
        self.assertIn('customerLocationLabel(region, locale)', app)
        self.assertIn('customerLocationLabel(city, locale)', app)

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
        self.assertIn('window.addEventListener("hashchange", syncHash)', main)
        self.assertIn('window.removeEventListener("hashchange", syncHash)', main)
        self.assertIn("<RoutedApplication />", main)

    def test_command_center_errors_follow_the_selected_language(self) -> None:
        command_center = (SRC / "CommandCenter.tsx").read_text(encoding="utf-8")
        self.assertIn("useState<unknown>(null)", command_center)
        self.assertIn("setLoadError(err)", command_center)
        self.assertIn("customerErrorText(loadError, locale)", command_center)
        self.assertNotIn("setLoadError(customerErrorText(err, locale))", command_center)

    def test_customer_overlays_hide_internal_profile_and_user_identifiers(self) -> None:
        app = (SRC / "App.tsx").read_text(encoding="utf-8")
        self.assertNotIn("Object.entries(profile)", app)
        self.assertNotIn("authUser?.display_name || authUser?.email || authUser?.user_id", app)
        self.assertNotIn("handleAddMember", app)
        self.assertNotIn("memberUserId", app)
        self.assertIn('text("الفريق والدعوات", "Team and invitations")', app)
        live_intelligence = (SRC / "LiveIntelligenceWorkspace.tsx").read_text(encoding="utf-8")
        self.assertIn('text("بحث حي محكوم", "Governed live research")', live_intelligence)
        self.assertNotIn("<p>ذكاء حي محكوم</p>", live_intelligence)
        self.assertNotIn("function SnapshotAnalytics(", app)
        self.assertIn("customerBusinessText(membership.role, locale)", app)
        self.assertIn('customerBusinessText(String(profile.profile_id ?? ""), locale)', app)
        self.assertIn("customerBusinessText(String(profile.sector_id ?? profile.profile_id ?? \"\"), locale)", app)

    def test_sanad_opens_exact_missing_input_and_preserves_return_stage(self) -> None:
        app = (SRC / "App.tsx").read_text(encoding="utf-8")
        surface = (SRC / "ASIECompleteSurfaceMount.tsx").read_text(encoding="utf-8")
        self.assertIn('window.addEventListener("asie:navigate-missing-input"', app)
        self.assertIn('data-asie-missing-label={firstMissingInputLabel', app)
        self.assertIn('data-asie-missing-target={firstMissingInputTarget}', app)
        self.assertIn('focusWizardTarget(targetId)', app)
        self.assertIn('id="wizard-project-name"', app)
        self.assertIn('text("العودة إلى موضعك السابق", "Return to your previous place")', app)
        self.assertIn('window.dispatchEvent(new CustomEvent("asie:navigate-missing-input"))', surface)
        self.assertIn('sessionStorage.setItem("asie.sanad.return_stage"', surface)
        self.assertIn('sessionStorage.removeItem("asie.sanad.return_stage")', surface)
        self.assertIn('text("أكمل هذا المدخل", "Complete this input")', surface)


if __name__ == "__main__":
    unittest.main()
