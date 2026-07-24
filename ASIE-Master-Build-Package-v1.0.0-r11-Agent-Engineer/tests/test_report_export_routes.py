"""W1 snapshot-bound report export routes.

The funder report exporters (PDF/DOCX/PPTX) existed as library functions only.
These tests pin the HTTP surface: exports stream bytes for the owning tenant,
fail closed cross-tenant and unauthenticated, stay snapshot-bound (404 for
unknown snapshots), degrade to a clean 503 when the production runtime
(python-docx / pinned Chromium renderer) is absent, and leave an audit event.

Run with Python 3.13+:  python -m unittest tests.test_report_export_routes
"""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import threading
import unittest
import warnings
from http.client import HTTPConnection
from pathlib import Path

from backend import asie_local_api as api
from backend.repository import Repository

VALID_INPUTS = {
    "startup_cost": 250000,
    "monthly_fixed_cost": 62000,
    "unit_price": 85,
    "variable_cost": 34,
    "monthly_units": 1600,
    "annual_discount_rate": 0.10,
    "working_capital_months": 2,
}

EXPORT_PATHS = ("pdf", "docx", "pptx")


def _docx_available() -> bool:
    try:
        import docx  # noqa: F401
    except ModuleNotFoundError:
        return False
    return True


def _pdf_renderer_available() -> bool:
    if os.environ.get("ASIE_PDF_RENDERER"):
        return True
    return shutil.which("chrome") is not None or shutil.which("msedge") is not None


class ReportExportRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.repo = Repository(Path(directory.name) / "exports.sqlite3")

        self.user_a = self.repo.create_user(email="exports-a@example.test", display_name="Owner A", password="exports-password-a1")
        self.user_b = self.repo.create_user(email="exports-b@example.test", display_name="Owner B", password="exports-password-b1")
        self.org_a = self.repo.create_organization(name="Exports Org A", owner_user_id=self.user_a["user_id"])
        self.org_b = self.repo.create_organization(name="Exports Org B", owner_user_id=self.user_b["user_id"])

        self.project_b = self.repo.create_project(
            {
                "name": "B export project",
                "sector": "خدمات",
                "jurisdiction": "Saudi Arabia",
                "inputs": dict(VALID_INPUTS),
                "organization_id": self.org_b["organization_id"],
            }
        )
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            overview_b, report_b = api.build_overview(self.project_b, self.repo)
        self.repo.save_run_snapshot(self.project_b.project_id, overview_b, report_b)
        self.snapshot_b_id = overview_b["snapshot"]["snapshot_id"]
        self.assertTrue(report_b.get("funder_report"), "fixture must produce a funder report projection")

        self.token_a, _ = self.repo.create_session(email=self.user_a["email"], password="exports-password-a1")
        self.token_b, _ = self.repo.create_session(email=self.user_b["email"], password="exports-password-b1")

        previous_repo = api.REPO
        api.REPO = self.repo
        self.addCleanup(setattr, api, "REPO", previous_repo)
        self.server = api.ThreadingHTTPServer(("127.0.0.1", 0), api.Handler)
        thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    # ------------------------------------------------------------------ helpers
    def request_bytes(self, path: str, *, token: str | None = None) -> tuple[int, dict[str, str], bytes]:
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        connection = HTTPConnection("127.0.0.1", self.server.server_address[1], timeout=30)
        try:
            connection.request("GET", path, headers=headers)
            response = connection.getresponse()
            raw = response.read()
            response_headers = {key.lower(): value for key, value in response.getheaders()}
            status = response.status
        finally:
            connection.close()
        return status, response_headers, raw

    def export_path(self, snapshot_id: str, export_format: str) -> str:
        return f"/api/snapshots/{snapshot_id}/funder-report.{export_format}"

    # ------------------------------------------------------------------ positive paths
    def test_pptx_export_streams_snapshot_bound_bytes(self) -> None:
        status, headers, raw = self.request_bytes(self.export_path(self.snapshot_b_id, "pptx"), token=self.token_b)
        self.assertEqual(200, status)
        self.assertEqual(
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            headers.get("content-type"),
        )
        self.assertIn("attachment", headers.get("content-disposition", ""))
        self.assertIn(self.snapshot_b_id, headers.get("content-disposition", ""))
        self.assertTrue(raw.startswith(b"PK"), "PPTX export must be a zip container")
        self.assertGreater(len(raw), 500)

    def test_docx_export_streams_or_reports_missing_runtime(self) -> None:
        status, headers, raw = self.request_bytes(self.export_path(self.snapshot_b_id, "docx"), token=self.token_b)
        if _docx_available():
            self.assertEqual(200, status)
            self.assertEqual(
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                headers.get("content-type"),
            )
            self.assertTrue(raw.startswith(b"PK"), "DOCX export must be a zip container")
        else:
            self.assertEqual(503, status)
            self.assertIn(b"document runtime", raw)

    def test_pdf_export_streams_or_reports_missing_renderer(self) -> None:
        status, headers, raw = self.request_bytes(self.export_path(self.snapshot_b_id, "pdf"), token=self.token_b)
        if _pdf_renderer_available():
            self.assertEqual(200, status)
            self.assertEqual("application/pdf", headers.get("content-type"))
            self.assertTrue(raw.startswith(b"%PDF"), "PDF export must carry the PDF magic header")
        else:
            self.assertEqual(503, status)
            self.assertIn(b"PDF renderer", raw)

    # ------------------------------------------------------------------ fail-closed paths
    def test_exports_fail_closed_cross_tenant(self) -> None:
        for export_format in EXPORT_PATHS:
            with self.subTest(export_format=export_format):
                status, _headers, raw = self.request_bytes(
                    self.export_path(self.snapshot_b_id, export_format), token=self.token_a
                )
                self.assertEqual(403, status)
                self.assertIn(b"permission_denied", raw)

    def test_exports_require_authentication(self) -> None:
        for export_format in EXPORT_PATHS:
            with self.subTest(export_format=export_format):
                status, _headers, raw = self.request_bytes(self.export_path(self.snapshot_b_id, export_format))
                self.assertEqual(401, status)
                self.assertIn(b"authentication_required", raw)

    def test_export_unknown_snapshot_is_404(self) -> None:
        for export_format in EXPORT_PATHS:
            with self.subTest(export_format=export_format):
                status, _headers, raw = self.request_bytes(
                    self.export_path("snap_missing_export", export_format), token=self.token_b
                )
                self.assertEqual(404, status)

    # ------------------------------------------------------------------ audit
    def test_export_is_audited(self) -> None:
        status, _headers, _raw = self.request_bytes(self.export_path(self.snapshot_b_id, "pptx"), token=self.token_b)
        self.assertEqual(200, status)
        events = self.repo.security_audit_events(limit=50)
        export_events = [
            event
            for event in events
            if event.get("action") == "report.export" and event.get("target_id") == self.snapshot_b_id
        ]
        self.assertTrue(export_events, "export downloads must leave an audit event")
        self.assertEqual("allowed", export_events[0].get("result"))
        self.assertEqual("pptx", export_events[0].get("reason"))
        self.assertEqual(self.user_b["user_id"], export_events[0].get("actor_user_id"))


if __name__ == "__main__":
    unittest.main()
