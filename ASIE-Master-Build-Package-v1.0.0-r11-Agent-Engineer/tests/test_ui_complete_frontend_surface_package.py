from __future__ import annotations

import unittest
from pathlib import Path

from backend.dib_registry_admission import assert_all_frozen_files_unchanged


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
MAIN = PACKAGE_ROOT / "src" / "main.tsx"
MOUNT = PACKAGE_ROOT / "src" / "ASIECompleteSurfaceMount.tsx"
SURFACE_CSS = PACKAGE_ROOT / "src" / "asie-complete-surface.css"
PACKAGE_DOC = PACKAGE_ROOT / "docs" / "UI-ALIGN-003-ASIE-COMPLETE-FRONTEND-SURFACE-PACKAGE-2026-07-27.md"


class CompleteFrontendSurfacePackageTests(unittest.TestCase):
    def test_package_files_exist(self) -> None:
        for path in (MAIN, MOUNT, SURFACE_CSS, PACKAGE_DOC):
            self.assertTrue(path.exists(), path)

    def test_complete_surface_is_loaded_last(self) -> None:
        source = MAIN.read_text(encoding="utf-8")
        legacy_index = source.index('import "./styles.css";')
        reference_index = source.index('import "./asie-reference-theme.css";')
        complete_index = source.index('import "./asie-complete-surface.css";')
        self.assertLess(legacy_index, reference_index)
        self.assertLess(reference_index, complete_index)
        self.assertIn("<ASIECompleteSurfaceMount />", source)

    def test_approved_palette_is_exact(self) -> None:
        source = SURFACE_CSS.read_text(encoding="utf-8")
        required_tokens = (
            "--asie-bg: #F5F7F3",
            "--asie-bg-secondary: #EDF2EB",
            "--asie-card: #FFFFFF",
            "--asie-card-secondary: #F4F7F2",
            "--asie-brand: #12805C",
            "--asie-brand-dark: #0B6246",
            "--asie-amber: #D97706",
            "--asie-teal: #0D9488",
            "--asie-text: #102B21",
            "--asie-text-secondary: #46574E",
            "--asie-text-muted: #7D8C83",
        )
        for token in required_tokens:
            self.assertIn(token, source)

    def test_all_frontend_surfaces_are_covered(self) -> None:
        source = SURFACE_CSS.read_text(encoding="utf-8")
        required_selectors = (
            ".landing-page",
            ".admin-shell:has(.admin-login)",
            ".legal-page",
            ".app-shell:not(.dib-workspace)",
            ".asie-page-hub",
            ".wizard-shell",
            ".evidence-ledger",
            ".decision-pack",
            ".execution-plan",
            ".snapshot-view",
            ".dib-workspace",
            ".admin-shell:not(:has(.admin-login))",
            ".asie-sanad-assistant",
            "@media (max-width: 640px)",
            "@media (prefers-reduced-motion: reduce)",
        )
        for selector in required_selectors:
            self.assertIn(selector, source)

    def test_immersive_landing_owns_a_two_column_desktop_width(self) -> None:
        source = SURFACE_CSS.read_text(encoding="utf-8")
        desktop_rule = ".landing-page .landing-hero--immersive {\n  width: min(1380px, calc(100% - 48px));"
        mobile_rule = ".landing-page .landing-hero--immersive {\n    width: calc(100% - 32px);"
        narrow_mobile_rule = ".landing-page .landing-hero--immersive {\n    width: 100%;"
        self.assertIn(desktop_rule, source)
        self.assertIn(mobile_rule, source)
        self.assertIn(narrow_mobile_rule, source)
        self.assertIn(".landing-page .landing-hero--immersive .landing-actions {\n  justify-content: flex-start;", source)

    def test_page_map_matches_approved_asie_information_architecture(self) -> None:
        source = MOUNT.read_text(encoding="utf-8")
        required_pages = (
            "لوحة القيادة",
            "مرشد تأسيس المشروع",
            "طبقة الأدلة",
            "جاهزية الدراسة",
            "تشغيل التحليل",
            "اختبر السوق",
            "فهم القرار",
            "خارطة التنفيذ",
            "تقاريري",
        )
        for page in required_pages:
            self.assertIn(page, source)

    def test_landing_completion_is_honest_about_live_capabilities(self) -> None:
        source = MOUNT.read_text(encoding="utf-8")
        self.assertIn("PDF واستخراج عروض الموردين ما زالا ضمن خطة البناء", source)
        self.assertIn("لا يتصل بمزود ذكاء خارجي", source)
        self.assertIn("ليست بوابة دفع أو عروضًا تجارية حية", source)
        self.assertNotIn("149", source)
        self.assertNotIn("449", source)

    def test_surface_mount_has_no_api_or_runtime_dependency(self) -> None:
        source = MOUNT.read_text(encoding="utf-8")
        self.assertNotIn('from "./api"', source)
        self.assertNotIn('from "./contracts"', source)
        self.assertNotIn("fetch(", source)
        self.assertNotIn("runProject", source)
        self.assertNotIn("createSnapshot", source)

    def test_ui_package_does_not_mutate_frozen_runtime_files(self) -> None:
        assert_all_frozen_files_unchanged(PACKAGE_ROOT)


if __name__ == "__main__":
    unittest.main()
