"""W0 tenant-isolation negative matrix.

Every sensitive HTTP surface is probed cross-tenant (organization A principal
against organization B resources) and unauthenticated after bootstrap.
A response is acceptable only when it fails closed (401/403/404/422 with an
error payload). A 2xx response that leaks or mutates another tenant's data
fails this suite.

Run with Python 3.13+:  python -m unittest tests.test_tenant_isolation_matrix
"""
from __future__ import annotations

import json
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

DATASET_PAYLOAD = {
    "source_id": "GASTAT_MATRIX",
    "title": "Isolation matrix dataset",
    "publisher": "General Authority for Statistics",
    "import_method": "manual_table",
    "review_status": "approved_for_use",
    "human_review_decision": "approved",
    "license_snapshot_ref": "license_snapshot:matrix",
    "terms_hash": "sha256:matrix",
    "classification": "public_open_data",
    "pdpl_check": "passed_no_personal_data",
    "attribution": "GASTAT attribution",
    "rows": [{"metric": "market_size", "value": 100}],
}


class TenantIsolationMatrixTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.repo = Repository(Path(directory.name) / "matrix.sqlite3")

        self.user_a = self.repo.create_user(email="matrix-a@example.test", display_name="Owner A", password="matrix-password-a1")
        self.user_b = self.repo.create_user(email="matrix-b@example.test", display_name="Owner B", password="matrix-password-b1")
        self.user_c = self.repo.create_user(email="matrix-c@example.test", display_name="Outsider", password="matrix-password-c1")
        self.org_a = self.repo.create_organization(name="Matrix Org A", owner_user_id=self.user_a["user_id"])
        self.org_b = self.repo.create_organization(name="Matrix Org B", owner_user_id=self.user_b["user_id"])
        self.org_a_id = self.org_a["organization_id"]
        self.org_b_id = self.org_b["organization_id"]

        self.project_a = self.repo.create_project({"name": "A project", "organization_id": self.org_a_id})
        self.project_b = self.repo.create_project(
            {
                "name": "B project",
                "sector": "خدمات",
                "jurisdiction": "Saudi Arabia",
                "inputs": dict(VALID_INPUTS),
                "organization_id": self.org_b_id,
            }
        )
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            overview_b, report_b = api.build_overview(self.project_b, self.repo)
        self.repo.save_run_snapshot(self.project_b.project_id, overview_b, report_b)
        self.run_b_id = overview_b["run"]["run_id"]
        self.snapshot_b_id = overview_b["snapshot"]["snapshot_id"]
        self.dataset_b = self.repo.save_dataset(DATASET_PAYLOAD | {"organization_id": self.org_b_id})
        self.dataset_b_id = self.dataset_b["dataset_id"]

        self.token_a, _ = self.repo.create_session(email=self.user_a["email"], password="matrix-password-a1")
        self.token_b, _ = self.repo.create_session(email=self.user_b["email"], password="matrix-password-b1")
        self.token_c, _ = self.repo.create_session(email=self.user_c["email"], password="matrix-password-c1")

        previous_repo = api.REPO
        api.REPO = self.repo
        self.addCleanup(setattr, api, "REPO", previous_repo)
        self.server = api.ThreadingHTTPServer(("127.0.0.1", 0), api.Handler)
        thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    # ------------------------------------------------------------------ helpers
    def request(self, method: str, path: str, *, token: str | None = None, organization_id: str | None = None,
                payload: dict | None = None) -> tuple[int, dict]:
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if organization_id:
            headers["X-ASIE-Organization-Id"] = organization_id
        body = json.dumps(payload) if payload is not None else None
        connection = HTTPConnection("127.0.0.1", self.server.server_address[1], timeout=10)
        try:
            connection.request(method, path, body=body, headers=headers)
            response = connection.getresponse()
            raw = response.read().decode("utf-8")
        finally:
            connection.close()
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = {"_non_json": raw[:200]}
        return response.status, parsed

    def assert_denied(self, status: int, body: dict, expected: int, label: str) -> None:
        self.assertEqual(expected, status, f"{label}: expected {expected}, got {status} -> {body}")
        self.assertIn("error", body, f"{label}: denial must carry an error payload")

    # ------------------------------------------------------- cross-tenant reads
    def test_cross_tenant_project_reads_denied(self) -> None:
        pid = self.project_b.project_id
        paths = [
            f"/api/projects/{pid}",
            f"/api/projects/{pid}/runs",
            f"/api/projects/{pid}/workspace",
            f"/api/projects/{pid}/remediation",
            f"/api/projects/{pid}/action-items",
            f"/api/projects/{pid}/readiness",
            f"/api/projects/{pid}/assumptions",
            f"/api/projects/{pid}/evidence-register",
            f"/api/projects/{pid}/evidence-ledger",
            f"/api/projects/{pid}/transformation-lineage",
            f"/api/projects/{pid}/evidence-coverage",
        ]
        for path in paths:
            with self.subTest(path=path):
                status, body = self.request("GET", path, token=self.token_a)
                self.assert_denied(status, body, 403, path)

    def test_cross_tenant_run_and_snapshot_reads_denied(self) -> None:
        sid = self.snapshot_b_id
        paths = [
            f"/api/runs/{self.run_b_id}/overview",
            f"/api/runs/{self.run_b_id}/audit",
            f"/api/runs/{self.run_b_id}/acceptance",
            f"/api/snapshots/{sid}",
            f"/api/snapshots/{sid}/report",
            f"/api/snapshots/{sid}/decision-pack",
            f"/api/snapshots/{sid}/decision-pack.html",
            f"/api/snapshots/{sid}/reviews",
            f"/api/snapshots/{sid}/report-view",
            f"/api/snapshots/{sid}/report.html",
            f"/api/snapshots/{sid}/funder-report.html",
            f"/api/snapshots/{sid}/release",
        ]
        for path in paths:
            with self.subTest(path=path):
                status, body = self.request("GET", path, token=self.token_a)
                self.assert_denied(status, body, 403, path)

    def test_cross_tenant_dataset_reads_and_org_scoped_lists_denied(self) -> None:
        did = self.dataset_b_id
        for path in (f"/api/datasets/{did}", f"/api/datasets/{did}/quality-gate", f"/api/datasets/{did}/transformations"):
            with self.subTest(path=path):
                status, body = self.request("GET", path, token=self.token_a)
                self.assert_denied(status, body, 403, path)
        for path in ("/api/projects", "/api/datasets"):
            with self.subTest(path=path, note="list with foreign organization header"):
                status, body = self.request("GET", path, token=self.token_a, organization_id=self.org_b_id)
                self.assert_denied(status, body, 403, path)

    # ------------------------------------------------------ cross-tenant writes
    def test_cross_tenant_project_and_dataset_writes_denied(self) -> None:
        pid = self.project_b.project_id
        cases = [
            ("POST", "/api/projects", self.org_b_id, {"name": "forged", "sector": "x", "jurisdiction": "y"}),
            ("POST", f"/api/projects/{pid}/runs", None, {"inputs": dict(VALID_INPUTS)}),
            ("POST", f"/api/projects/{pid}/assumptions", None, {"input_key": "unit_price", "value": 1}),
            ("POST", f"/api/projects/{pid}/evidence-links", None, {"dataset_id": self.dataset_b_id}),
            ("POST", "/api/datasets", self.org_b_id, dict(DATASET_PAYLOAD)),
            ("POST", "/api/datasets/manual-import", self.org_b_id, dict(DATASET_PAYLOAD)),
            ("POST", "/api/datasets/file-import", self.org_b_id, dict(DATASET_PAYLOAD)),
            ("POST", f"/api/datasets/{self.dataset_b_id}/transformations", None, {"operation": "sum"}),
            ("POST", f"/api/datasets/{self.dataset_b_id}/review", None, {"human_review_decision": "approved"}),
            ("POST", f"/api/snapshots/{self.snapshot_b_id}/reviews", None, {"verdict": "forged"}),
            ("POST", "/api/snapshots/compare", None, {"snapshot_a_id": self.snapshot_b_id, "snapshot_b_id": self.snapshot_b_id}),
            ("PATCH", f"/api/projects/{pid}", None, {"name": "hijacked"}),
            ("PATCH", f"/api/projects/{pid}/action-items/forged", None, {"status": "done"}),
        ]
        for method, path, org_header, payload in cases:
            with self.subTest(method=method, path=path):
                status, body = self.request(method, path, token=self.token_a, organization_id=org_header, payload=payload)
                self.assert_denied(status, body, 403, f"{method} {path}")
        # nothing was created or mutated inside organization B
        self.assertEqual(["B project"], [row["name"] for row in self.repo.list_projects(self.org_b_id)])
        untouched = self.repo.get_project(pid)
        self.assertEqual("B project", untouched.name)

    def test_cross_tenant_membership_and_org_admin_writes_denied(self) -> None:
        cases = [
            ("POST", f"/api/organizations/{self.org_b_id}/memberships", {"user_id": self.user_a["user_id"], "role": "viewer"}),
            ("POST", f"/api/organizations/{self.org_b_id}/data-requests", {"request_type": "export"}),
        ]
        for method, path, payload in cases:
            with self.subTest(method=method, path=path):
                status, body = self.request(method, path, token=self.token_a, payload=payload)
                self.assert_denied(status, body, 403, f"{method} {path}")

    def test_cross_tenant_intelligence_surfaces_fail_closed(self) -> None:
        pid = self.project_b.project_id
        # read path: authorization PermissionError must become a clean 403, not a dropped connection
        status, body = self.request("GET", f"/api/intelligence/contexts/ctx-foreign?project_id={pid}",
                                    token=self.token_a, organization_id=self.org_b_id)
        self.assert_denied(status, body, 403, "GET /api/intelligence/contexts cross-tenant")
        # write paths: fail closed with 422 (platform convention for authorization PermissionError on POST)
        post_cases = [
            ("/api/intelligence/contexts", {"project_id": pid, "idempotency_key": "forge-1"}),
            ("/api/intelligence/pre-runs", {"project_id": pid, "context_build_id": "ctx-f", "idempotency_key": "k-f",
                                            "geography": "riyadh", "sector": "services", "components": []}),
            ("/api/intelligence/contexts/ctx-foreign/reviews", {"project_id": pid}),
            ("/api/intelligence/contexts/ctx-foreign/approval", {"project_id": pid}),
        ]
        for path, payload in post_cases:
            with self.subTest(path=path):
                status, body = self.request("POST", path, token=self.token_a, organization_id=self.org_b_id, payload=payload)
                self.assert_denied(status, body, 422, f"POST {path}")

    # ------------------------------------------------- privilege-boundary gaps
    def test_source_review_write_requires_platform_manage(self) -> None:
        # POST /api/sources/review-record requires platform.manage; PATCH must not be weaker.
        status, body = self.request("PATCH", "/api/sources/GASTAT_MATRIX/review", token=self.token_b,
                                    payload={"human_review_decision": "approved"})
        self.assert_denied(status, body, 403, "PATCH /api/sources/{id}/review as organization principal")

    def test_platform_admin_surfaces_denied_for_organization_principals(self) -> None:
        paths = [
            "/api/admin/overview",
            "/api/operations/health",
            "/api/operations/audit-events",
            "/api/operations/release-info",
            f"/api/admin/organizations/{self.org_b_id}/subscription",
            f"/api/admin/organizations/{self.org_b_id}/notifications",
        ]
        for path in paths:
            with self.subTest(path=path):
                status, body = self.request("GET", path, token=self.token_b)
                self.assert_denied(status, body, 403, path)

    # ------------------------------------------- unauthenticated fail-closed gate
    def test_unauthenticated_requests_fail_closed_after_bootstrap(self) -> None:
        protected = [
            ("GET", "/api/projects"),
            ("GET", f"/api/projects/{self.project_a.project_id}"),
            ("GET", f"/api/snapshots/{self.snapshot_b_id}"),
            ("GET", "/api/datasets"),
            ("POST", f"/api/projects/{self.project_a.project_id}/runs"),
            ("POST", "/api/organizations"),
        ]
        for method, path in protected:
            with self.subTest(method=method, path=path):
                org_header = self.org_a_id if path in {"/api/projects", "/api/datasets"} else None
                status, body = self.request(method, path, organization_id=org_header,
                                            payload={"inputs": dict(VALID_INPUTS)} if method == "POST" else None)
                self.assert_denied(status, body, 401, f"unauthenticated {method} {path}")
        # public reference surfaces stay public
        for path in ("/api/health", "/api/funding-profiles", "/api/sector-profiles", "/api/architecture/runtime-status"):
            with self.subTest(path=path, note="public"):
                status, _body = self.request("GET", path)
                self.assertEqual(200, status, f"public surface {path} must stay reachable")

    def test_outsider_without_membership_is_denied_on_org_surfaces(self) -> None:
        status, body = self.request("GET", "/api/projects", token=self.token_c, organization_id=self.org_a_id)
        self.assert_denied(status, body, 403, "outsider list on org A")
        status, body = self.request("GET", f"/api/projects/{self.project_a.project_id}", token=self.token_c)
        self.assert_denied(status, body, 403, "outsider project read on org A")

    # ------------------------------------------------------- audit immutability
    def test_security_audit_trail_exposes_no_mutation_route(self) -> None:
        for method in ("PUT", "PATCH", "DELETE", "POST"):
            with self.subTest(method=method):
                status, body = self.request(method, "/api/operations/audit-events", token=self.token_b, payload={})
                self.assert_denied(status, body, 404, f"{method} /api/operations/audit-events")

    # ------------------------------------------------------------- positive control
    def test_owner_retains_full_access_to_own_tenant(self) -> None:
        status, body = self.request("GET", f"/api/projects/{self.project_b.project_id}", token=self.token_b)
        self.assertEqual(200, status, body)
        self.assertEqual("B project", body["project"]["name"])
        status, body = self.request("GET", f"/api/snapshots/{self.snapshot_b_id}/report", token=self.token_b)
        self.assertEqual(200, status, body)
        status, body = self.request("GET", "/api/projects", token=self.token_b, organization_id=self.org_b_id)
        self.assertEqual(200, status, body)
        self.assertEqual([self.project_b.project_id], [row["project_id"] for row in body["projects"]])


if __name__ == "__main__":
    unittest.main()
