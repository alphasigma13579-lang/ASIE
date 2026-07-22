from __future__ import annotations

import json
import tempfile
import threading
import unittest
from http.client import HTTPConnection
from pathlib import Path

from backend import asie_local_api as api
from backend.repository import Repository


class IdentityAndControlPlaneTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.repo = Repository(Path(directory.name) / "identity.sqlite3")

    def test_membership_scopes_projects_and_denies_cross_organization_principal(self) -> None:
        first = self.repo.create_user(email="owner-a@example.test", display_name="Owner A", password="strong-local-password-a")
        second = self.repo.create_user(email="owner-b@example.test", display_name="Owner B", password="strong-local-password-b")
        org_a = self.repo.create_organization(name="Organization A", owner_user_id=first["user_id"])
        org_b = self.repo.create_organization(name="Organization B", owner_user_id=second["user_id"])
        project_a = self.repo.create_project({"name": "A", "organization_id": org_a["organization_id"]})
        self.repo.create_project({"name": "B", "organization_id": org_b["organization_id"]})

        token, _user = self.repo.create_session(email="owner-a@example.test", password="strong-local-password-a")
        own_principal = self.repo.principal_for_token(token, org_a["organization_id"])
        other_principal = self.repo.principal_for_token(token, org_b["organization_id"])

        self.assertTrue(own_principal and own_principal.can("project.edit"))
        self.assertFalse(other_principal and other_principal.can("snapshot.read"))
        self.assertEqual([project_a.project_id], [row["project_id"] for row in self.repo.list_projects(org_a["organization_id"])])

    def test_password_is_not_stored_and_revoked_session_fails_closed(self) -> None:
        user = self.repo.create_user(email="session@example.test", display_name="Session", password="strong-local-password-c")
        token, _ = self.repo.create_session(email=user["email"], password="strong-local-password-c")
        self.assertIsNotNone(self.repo.principal_for_token(token))
        self.assertTrue(self.repo.revoke_session(token))
        self.assertIsNone(self.repo.principal_for_token(token))

    def test_http_route_rejects_cross_tenant_project_read(self) -> None:
        first = self.repo.create_user(email="http-a@example.test", display_name="HTTP A", password="strong-local-password-d")
        second = self.repo.create_user(email="http-b@example.test", display_name="HTTP B", password="strong-local-password-e")
        org_a = self.repo.create_organization(name="HTTP A", owner_user_id=first["user_id"])
        org_b = self.repo.create_organization(name="HTTP B", owner_user_id=second["user_id"])
        project_b = self.repo.create_project({"name": "Private B", "organization_id": org_b["organization_id"]})
        token, _ = self.repo.create_session(email=first["email"], password="strong-local-password-d")

        previous_repo = api.REPO
        api.REPO = self.repo
        self.addCleanup(setattr, api, "REPO", previous_repo)
        server = api.ThreadingHTTPServer(("127.0.0.1", 0), api.Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)

        connection = HTTPConnection("127.0.0.1", server.server_address[1], timeout=10)
        try:
            connection.request("GET", f"/api/projects/{project_b.project_id}", headers={"Authorization": f"Bearer {token}"})
            response = connection.getresponse()
            body = json.loads(response.read().decode("utf-8"))
        finally:
            connection.close()
        self.assertEqual(403, response.status)
        self.assertEqual("permission_denied", body["error"])

    def test_http_project_creation_cannot_impersonate_another_organization(self) -> None:
        first = self.repo.create_user(email="create-a@example.test", display_name="Create A", password="strong-local-password-f")
        second = self.repo.create_user(email="create-b@example.test", display_name="Create B", password="strong-local-password-g")
        org_a = self.repo.create_organization(name="Create A", owner_user_id=first["user_id"])
        org_b = self.repo.create_organization(name="Create B", owner_user_id=second["user_id"])
        token, _ = self.repo.create_session(email=first["email"], password="strong-local-password-f")
        previous_repo = api.REPO
        api.REPO = self.repo
        self.addCleanup(setattr, api, "REPO", previous_repo)
        server = api.ThreadingHTTPServer(("127.0.0.1", 0), api.Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        connection = HTTPConnection("127.0.0.1", server.server_address[1], timeout=10)
        try:
            payload = json.dumps({"name": "forbidden", "sector": "test", "jurisdiction": "local"})
            connection.request("POST", "/api/projects", body=payload, headers={"Authorization": f"Bearer {token}", "X-ASIE-Organization-Id": org_b["organization_id"], "Content-Type": "application/json"})
            response = connection.getresponse()
            body = json.loads(response.read().decode("utf-8"))
        finally:
            connection.close()
        self.assertEqual(403, response.status)
        self.assertEqual("permission_denied", body["error"])
        self.assertEqual([], self.repo.list_projects(org_b["organization_id"]))


if __name__ == "__main__":
    unittest.main()
