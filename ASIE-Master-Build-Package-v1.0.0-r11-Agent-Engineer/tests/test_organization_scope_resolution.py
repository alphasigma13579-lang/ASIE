"""W1 organization-scope resolution for collection endpoints.

Regression tests for a silent-failure bug: an authenticated caller hitting
GET/POST /api/projects or /api/datasets without X-ASIE-Organization-Id used
to get an empty reply (connection drop) because the handler returned without
writing a response. The scope now resolves to the caller's first membership,
explicit headers are still honored and verified server-side, users with no
memberships get a clean 400, and legacy zero-user mode is unchanged.

Run with Python 3.13+:  python -m unittest tests.test_organization_scope_resolution
"""
from __future__ import annotations

import json
import tempfile
import threading
import unittest
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


class OrganizationScopeResolutionTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.repo = Repository(Path(directory.name) / "scope.sqlite3")

        self.owner = self.repo.create_user(email="scope-owner@example.test", display_name="Owner", password="scope-password-1")
        self.org = self.repo.create_organization(name="Scope Org", owner_user_id=self.owner["user_id"])
        self.org_second = self.repo.create_organization(name="Scope Org Two", owner_user_id=self.owner["user_id"])
        self.outsider = self.repo.create_user(email="scope-outsider@example.test", display_name="Outsider", password="scope-password-2")
        self.loner = self.repo.create_user(email="scope-loner@example.test", display_name="No Orgs", password="scope-password-3")

        self.token_owner, _ = self.repo.create_session(email=self.owner["email"], password="scope-password-1")
        self.token_outsider, _ = self.repo.create_session(email=self.outsider["email"], password="scope-password-2")
        self.token_loner, _ = self.repo.create_session(email=self.loner["email"], password="scope-password-3")

        previous_repo = api.REPO
        api.REPO = self.repo
        self.addCleanup(setattr, api, "REPO", previous_repo)
        self.server = api.ThreadingHTTPServer(("127.0.0.1", 0), api.Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def request(
        self, method: str, path: str, *, token: str | None = None, organization_id: str | None = None, payload: dict | None = None
    ) -> tuple[int, dict]:
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if organization_id:
            headers["X-ASIE-Organization-Id"] = organization_id
        connection = HTTPConnection("127.0.0.1", self.server.server_address[1], timeout=15)
        try:
            connection.request(method, path, body=json.dumps(payload) if payload is not None else None, headers=headers)
            response = connection.getresponse()
            raw = response.read()
            status = response.status
        finally:
            connection.close()
        self.assertTrue(raw, f"{method} {path} must never answer with an empty body (silent connection drop)")
        return status, json.loads(raw.decode("utf-8"))

    # ------------------------------------------------------------------ defaults to first membership
    def test_projects_collection_defaults_to_caller_membership(self) -> None:
        status, body = self.request("GET", "/api/projects", token=self.token_owner)
        self.assertEqual(200, status)
        self.assertIn("projects", body)

    def test_datasets_collection_defaults_to_caller_membership(self) -> None:
        status, body = self.request("GET", "/api/datasets", token=self.token_owner)
        self.assertEqual(200, status)
        self.assertIn("datasets", body)

    def test_project_creation_defaults_to_caller_membership(self) -> None:
        status, body = self.request(
            "POST",
            "/api/projects",
            token=self.token_owner,
            payload={"name": "Scoped", "sector": "خدمات", "jurisdiction": "Saudi Arabia", "inputs": dict(VALID_INPUTS)},
        )
        self.assertEqual(201, status)
        self.assertEqual(self.org["organization_id"], body["project"]["organization_id"])

    # ------------------------------------------------------------------ explicit header honored and verified
    def test_explicit_header_selects_second_membership(self) -> None:
        status, body = self.request(
            "POST",
            "/api/projects",
            token=self.token_owner,
            organization_id=self.org_second["organization_id"],
            payload={"name": "Scoped Two", "sector": "خدمات", "jurisdiction": "Saudi Arabia", "inputs": dict(VALID_INPUTS)},
        )
        self.assertEqual(201, status)
        self.assertEqual(self.org_second["organization_id"], body["project"]["organization_id"])

    def test_explicit_foreign_organization_is_denied(self) -> None:
        status, body = self.request("GET", "/api/projects", token=self.token_outsider, organization_id=self.org["organization_id"])
        self.assertEqual(403, status)
        self.assertEqual("permission_denied", body["error"])

    # ------------------------------------------------------------------ clean failure, never silent
    def test_user_without_memberships_gets_clean_400(self) -> None:
        status, body = self.request("GET", "/api/projects", token=self.token_loner)
        self.assertEqual(400, status)
        self.assertEqual("organization_required", body["error"])

    def test_unauthenticated_gets_401_not_empty_reply(self) -> None:
        status, body = self.request("GET", "/api/projects")
        self.assertEqual(401, status)
        self.assertEqual("authentication_required", body["error"])


class LegacyScopeResolutionTests(unittest.TestCase):
    """Zero-user legacy mode keeps the legacy organization scope."""

    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.repo = Repository(Path(directory.name) / "legacy.sqlite3")
        previous_repo = api.REPO
        api.REPO = self.repo
        self.addCleanup(setattr, api, "REPO", previous_repo)
        self.server = api.ThreadingHTTPServer(("127.0.0.1", 0), api.Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def test_legacy_mode_projects_collection_stays_open(self) -> None:
        connection = HTTPConnection("127.0.0.1", self.server.server_address[1], timeout=15)
        try:
            connection.request("GET", "/api/projects", headers={"Content-Type": "application/json"})
            response = connection.getresponse()
            raw = response.read()
            self.assertEqual(200, response.status)
        finally:
            connection.close()
        self.assertIn("projects", json.loads(raw.decode("utf-8")))


if __name__ == "__main__":
    unittest.main()
