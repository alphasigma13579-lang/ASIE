from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backend import asie_local_api as api
from backend.funder_report import build_funder_report_projection
from backend.funder_report import render_funder_report_html
from backend.funding_readiness import evaluate_funding_readiness, profile_ids, sector_profile_catalog
from backend.report_release import build_release_record, validate_release_record
from backend.report_exports import export_funder_report_docx, export_funder_report_pdf, export_funder_report_pptx
from backend.snapshot_assembly import canonical_hash


class FunderReportProjectionTests(unittest.TestCase):
    def make_repo(self) -> api.Repository:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        return api.Repository(Path(temp_dir.name) / "asie-funder-test.sqlite3")

    def test_projection_is_snapshot_bound_and_has_sixteen_sections(self) -> None:
        repo = self.make_repo()
        project = repo.create_project(
            {
                "name": "حزمة تمويل تجريبية",
                "sector": "خدمات",
                "jurisdiction": "Saudi Arabia",
                "inputs": {
                    "startup_cost": 250000,
                    "monthly_fixed_cost": 62000,
                    "unit_price": 85,
                    "variable_cost": 34,
                    "monthly_units": 1600,
                    "annual_discount_rate": 0.10,
                    "working_capital_months": 2,
                    "equity_contribution": 150000,
                    "debt_amount": 0,
                    "loan_grace_months": 0,
                },
            }
        )
        overview, report = api.build_overview(project, repo)
        projection = report["funder_report"]

        self.assertEqual(projection["contract_id"], "funder.report.projection.v1")
        self.assertEqual(projection["snapshot_id"], overview["snapshot"]["snapshot_id"])
        self.assertEqual(len(projection["sections"]), 16)
        self.assertEqual(projection["sections"][13]["section_id"], "14-financial-expectations")
        self.assertEqual(projection["sections"][14]["section_id"], "15-capital-requirements")
        self.assertEqual(projection["sections"][13]["payload"]["statements"]["status"], "partial")
        self.assertIn("balance_sheet", projection["gaps"])

        unhashed = dict(projection)
        unhashed.pop("projection_hash")
        self.assertEqual(projection["projection_hash"], canonical_hash(unhashed))

    def test_projection_exposes_input_traceability_bound_to_same_snapshot(self) -> None:
        repo = self.make_repo()
        project = repo.create_project({"name": "تتبع المدخلات", "inputs": {"startup_cost": 250000}})
        overview, report = api.build_overview(project, repo)
        traceability = report["funder_report"]["input_traceability"]
        self.assertEqual("input.traceability.v1", traceability["contract_id"])
        self.assertEqual(overview["snapshot"]["snapshot_id"], traceability["snapshot_id"])
        startup = next(row for row in traceability["items"] if row["input_key"] == "startup_cost")
        self.assertEqual("user_input", startup["source_type"])
        self.assertEqual("draft", startup["review_status"])

    def test_projection_does_not_recalculate_finance(self) -> None:
        repo = self.make_repo()
        project = repo.create_project({"name": "مدخلات ناقصة", "inputs": {}})
        overview, report = api.build_overview(project, repo)
        projection = build_funder_report_projection(overview)

        self.assertEqual(projection["readiness_status"], "DRAFT_INTERNAL")
        self.assertEqual(projection["sections"][13]["payload"]["statements"]["status"], "not_ready")
        self.assertEqual(report["funder_report"]["snapshot_id"], overview["snapshot"]["snapshot_id"])

    def test_demo_projection_is_explicitly_blocked_from_production(self) -> None:
        repo = self.make_repo()
        project = repo.create_project({"name": "بيانات تجريبية", "inputs": {}})
        overview, report = api.build_overview(project, repo)
        projection = report["funder_report"]
        self.assertEqual("demo_simulated_external", projection["data_mode"])
        self.assertEqual("DEMO / LOCAL ONLY", projection["display_badge"])
        self.assertEqual("blocked", projection["production_admission"])
        self.assertEqual("DRAFT_INTERNAL", projection["readiness_status"])
        self.assertIn("demo_data_not_admitted_to_production", projection["gaps"])

    def test_html_composer_is_rtl_and_snapshot_bound(self) -> None:
        repo = self.make_repo()
        project = repo.create_project({"name": "عرض تمويلي", "inputs": {}})
        overview, report = api.build_overview(project, repo)
        html = render_funder_report_html(report["funder_report"])

        self.assertIn("lang='ar' dir='rtl'", html)
        self.assertIn(overview["snapshot"]["snapshot_id"], html)
        self.assertIn("حزمة التقرير الجاهز للتمويل", html)
        self.assertIn("الفجوات قبل الإصدار التمويلي", html)

    def test_docx_export_contains_snapshot_and_report_sections(self) -> None:
        try:
            from docx import Document
        except ModuleNotFoundError:
            self.skipTest("docx runtime is supplied by the document export environment")
        repo = self.make_repo()
        project = repo.create_project({"name": "حزمة Word", "inputs": {}})
        overview, report = api.build_overview(project, repo)
        with tempfile.TemporaryDirectory() as temp_dir:
            path = export_funder_report_docx(report["funder_report"], Path(temp_dir) / "funder.docx")
            self.assertTrue(path.exists())
            document = Document(path)
            text = "\n".join(paragraph.text for paragraph in document.paragraphs)
            self.assertIn("حزمة التقرير الجاهز للتمويل", text)
            self.assertIn("الفجوات قبل الإصدار", text)
            self.assertIn(overview["snapshot"]["snapshot_id"], "\n".join(cell.text for table in document.tables for row in table.rows for cell in row.cells))

    def test_pdf_export_is_server_side_and_snapshot_bound(self) -> None:
        import os
        import shutil
        renderer = os.environ.get("ASIE_PDF_RENDERER") or shutil.which("chrome") or shutil.which("msedge")
        if renderer is None:
            self.skipTest("server-side PDF renderer is pinned in the production image")
        repo = self.make_repo()
        project = repo.create_project({"name": "حزمة PDF", "inputs": {}})
        overview, report = api.build_overview(project, repo)
        with tempfile.TemporaryDirectory() as temp_dir:
            path = export_funder_report_pdf(report["funder_report"], Path(temp_dir) / "funder.pdf")
            self.assertTrue(path.exists())
            self.assertGreater(path.stat().st_size, 1000)
            self.assertEqual(path.read_bytes()[:5], b"%PDF-")

    def test_pptx_export_is_openxml_and_snapshot_bound(self) -> None:
        import zipfile
        repo = self.make_repo()
        project = repo.create_project({"name": "حزمة PowerPoint", "inputs": {}})
        _overview, report = api.build_overview(project, repo)
        with tempfile.TemporaryDirectory() as temp_dir:
            path = export_funder_report_pptx(report["funder_report"], Path(temp_dir) / "funder.pptx")
            with zipfile.ZipFile(path) as archive:
                self.assertIn("[Content_Types].xml", archive.namelist())
                self.assertIn("ppt/presentation.xml", archive.namelist())
                self.assertIn("ppt/slides/slide1.xml", archive.namelist())

    def test_reference_profiles_return_explainable_missing_requirements(self) -> None:
        repo = self.make_repo()
        project = repo.create_project({"name": "ملف جهة", "inputs": {}})
        overview, report = api.build_overview(project, repo)

        self.assertIn("BANK-SME-BASE-V1", profile_ids())
        result = evaluate_funding_readiness(report["funder_report"], "BANK-SME-BASE-V1")
        self.assertEqual(result["snapshot_id"], overview["snapshot"]["snapshot_id"])
        self.assertEqual(result["status"], "DRAFT_INTERNAL")
        self.assertIn("financial_projection", result["missing_requirements"])
        self.assertIn("لا يمثل قبولاً", result["acceptance_disclaimer"])

    def test_sector_profiles_are_scoped_and_reference_only(self) -> None:
        profiles = sector_profile_catalog()
        self.assertGreaterEqual(len(profiles), 4)
        retail = next(profile for profile in profiles if profile["profile_id"] == "SECTOR-RETAIL-V1")
        self.assertEqual(retail["profile_status"], "reference_only")
        self.assertEqual(retail["reviewed_at"], "2026-07-20")
        self.assertTrue(retail["not_covered_ar"])
        self.assertIn("lender_policy", retail["not_locally_verifiable"])

    def test_release_requires_matching_human_review_and_profile_readiness(self) -> None:
        repo = self.make_repo()
        project = repo.create_project({"name": "إصدار محلي", "inputs": {}})
        _overview, report = api.build_overview(project, repo)
        projection = report["funder_report"]

        blocked = build_release_record(projection, None)
        self.assertEqual(blocked["release_state"], "REVIEW_REQUIRED")
        self.assertIn("human_review_missing", blocked["blocking_reasons"])

        review = {"review_id": "review-1", "snapshot_id": projection["snapshot_id"], "reviewer": "reviewer", "decision": "approved_local", "created_at": "2026-07-20T00:00:00+00:00"}
        released = build_release_record(projection, review)
        self.assertEqual(released["release_state"], "REVIEW_REQUIRED")
        validate_release_record(projection, released)


if __name__ == "__main__":
    unittest.main()
