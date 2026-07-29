from __future__ import annotations

import json
import sqlite3
import tempfile
import threading
import unittest
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path

from backend.dib_http_mounting import DIBHttpSidecarHandler, create_dib_http_mount
from backend.dib_persistence import create_dib_persistence_store
from backend.dib_registry_admission import assert_all_frozen_files_unchanged
from backend.dib_tenant_boundary import (
    DIB_MIGRATION_USER_ID,
    DIB_QUARANTINE_ORGANIZATION_ID,
    DIBTenantBoundary,
    DIBTenantBoundaryError,
    DIBTenantContext,
)
from backend.repository import Repository

PACKAGE_ROOT = Path(__file__).resolve().parents[1]

FROZEN_FILES = {
    "backend/aas_kernel.py",
    "backend/aas_registry.py",
    "backend/heart_controller.py",
    "backend/bus_controller.py",
    "backend/system_bus.py",
    "backend/socket_contracts.py",
    "backend/module_runtime.py",
    "backend/project_run_workflow.py",
    "backend/snapshot_assembly.py",
    "backend/runtime_freeze.py",
}

SEC_BETA_03_ALLOWLIST = {
    "backend/dib_tenant_boundary.py",
    "backend/dib_tenant_api.py",
    "backend/dib_http_mounting.py",
    "tests/test_dib_http_mounting.py",
    "tests/test_sec_beta_03_dib_tenant_boundary.py",
    "docs/SEC-BETA-03-DIB-TENANT-OWNERSHIP-BOUNDARY-2026-07-29.md",
}


class DIBTenantOwnershipBoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        self.auth_repo = Repository(root / "identity.sqlite3")

        self.user_a = self.auth_repo.create_user(
            email="owner-a@example.test",
            display_name="Owner A",
            password="tenant-password-a-01",
        )
        self.org_a = self.auth_repo.create_organization(name="Org A", owner_user_id=self.user_a["user_id"])
        self.project_a = self.auth_repo.create_project(
            {"name": "Project A", "organization_id": self.org_a["organization_id"]}
        )
        self.token_a, _ = self.auth_repo.create_session(
            email=self.user_a["email"], password="tenant-password-a-01"
        )

        self.user_b = self.auth_repo.create_user(
            email="owner-b@example.test",
            display_name="Owner B",
            password="tenant-password-b-01",
        )
        self.org_b = self.auth_repo.create_organization(name="Org B", owner_user_id=self.user_b["user_id"])
        self.project_b = self.auth_repo.create_project(
            {"name": "Project B", "organization_id": self.org_b["organization_id"]}
        )
        self.token_b, _ = self.auth_repo.create_session(
            email=self.user_b["email"], password="tenant-password-b-01"
        )

        self.mount = create_dib_http_mount(
            db_path=str(root / "dib.sqlite3"),
            auth_repo=self.auth_repo,
        )
        self.addCleanup(self.mount.close)

        mount = self.mount

        class Handler(DIBHttpSidecarHandler):
            pass

        Handler.mount = mount
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def request(
        self,
        method: str,
        path: str,
        *,
        token: str,
        organization_id: str,
        payload: dict[str, object] | None = None,
    ) -> tuple[int, dict[str, object]]:
        connection = HTTPConnection("127.0.0.1", self.server.server_address[1], timeout=15)
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "X-ASIE-Organization-Id": organization_id,
        }
        try:
            connection.request(
                method,
                path,
                body=json.dumps(payload) if payload is not None else None,
                headers=headers,
            )
            response = connection.getresponse()
            body = json.loads(response.read().decode("utf-8"))
            return response.status, body
        finally:
            connection.close()

    def test_org_a_cannot_read_write_or_enumerate_org_b_dib_session(self) -> None:
        created_status, created_body = self.request(
            "POST",
            "/api/dib/sessions",
            token=self.token_b,
            organization_id=self.org_b["organization_id"],
            payload={"project_profile": {"project_id": self.project_b.project_id, "sector": "test"}},
        )
        self.assertEqual(201, created_status)
        session_id = str(created_body["session"]["session_id"])
        self.assertEqual(self.org_b["organization_id"], created_body["session"]["organization_id"])

        read_status, read_body = self.request(
            "GET",
            f"/api/dib/sessions/{session_id}",
            token=self.token_a,
            organization_id=self.org_a["organization_id"],
        )
        self.assertEqual(404, read_status)
        self.assertEqual("dib_resource_not_found", read_body["error"])

        events_status, _ = self.request(
            "GET",
            f"/api/dib/sessions/{session_id}/events",
            token=self.token_a,
            organization_id=self.org_a["organization_id"],
        )
        self.assertEqual(404, events_status)

        write_status, _ = self.request(
            "POST",
            f"/api/dib/sessions/{session_id}/blueprints",
            token=self.token_a,
            organization_id=self.org_a["organization_id"],
            payload={"source": "manual", "items": []},
        )
        self.assertEqual(404, write_status)

        list_status, _ = self.request(
            "GET",
            f"/api/dib/sessions?project_id={self.project_b.project_id}",
            token=self.token_a,
            organization_id=self.org_a["organization_id"],
        )
        self.assertEqual(404, list_status)

        owner_status, owner_body = self.request(
            "GET",
            f"/api/dib/sessions/{session_id}",
            token=self.token_b,
            organization_id=self.org_b["organization_id"],
        )
        self.assertEqual(200, owner_status)
        self.assertEqual(session_id, owner_body["session"]["session_id"])
        self.assertEqual(self.org_b["organization_id"], owner_body["session"]["organization_id"])

    def test_org_a_cannot_start_session_for_org_b_project(self) -> None:
        status, body = self.request(
            "POST",
            "/api/dib/sessions",
            token=self.token_a,
            organization_id=self.org_a["organization_id"],
            payload={"project_profile": {"project_id": self.project_b.project_id}},
        )
        self.assertEqual(404, status)
        self.assertEqual("dib_resource_not_found", body["error"])

    def test_existing_sessions_are_migrated_only_with_proven_project_ownership(self) -> None:
        store = create_dib_persistence_store()
        self.addCleanup(store.close)
        proven_session = store.start_session({"project_id": "proven_project"})
        unknown_session = store.start_session({"project_id": "unknown_project"})

        boundary = DIBTenantBoundary(
            store,
            project_organization_resolver=lambda project_id: "org_a" if project_id == "proven_project" else None,
        )
        status = boundary.status()
        self.assertEqual(1, status["migrated_session_count"])
        self.assertEqual(1, status["quarantined_session_count"])

        context = DIBTenantContext("org_a", "user_a", "principal_session_a")
        migrated = boundary.load_session(context, proven_session["session_id"])
        self.assertEqual("org_a", migrated["organization_id"])
        self.assertEqual(DIB_MIGRATION_USER_ID, migrated["created_by_user_id"])

        with self.assertRaisesRegex(DIBTenantBoundaryError, "dib_session_not_found"):
            boundary.load_session(context, unknown_session["session_id"])

        with store._read_connection() as connection:
            rows = {
                row["session_id"]: row["organization_id"]
                for row in connection.execute(
                    "SELECT session_id, organization_id FROM dib_tenant_bindings"
                ).fetchall()
            }
        self.assertEqual("org_a", rows[proven_session["session_id"]])
        self.assertEqual(DIB_QUARANTINE_ORGANIZATION_ID, rows[unknown_session["session_id"]])

    def test_quarantine_cannot_be_used_as_a_request_context(self) -> None:
        with self.assertRaisesRegex(DIBTenantBoundaryError, "dib_quarantine_context_forbidden"):
            DIBTenantContext(
                DIB_QUARANTINE_ORGANIZATION_ID,
                "platform_admin",
                "principal_session_admin",
            )

    def test_tenant_binding_is_required_and_immutable_at_database_boundary(self) -> None:
        store = create_dib_persistence_store()
        self.addCleanup(store.close)
        boundary = DIBTenantBoundary(store, project_organization_resolver=lambda _project_id: "org_a")
        context = DIBTenantContext("org_a", "user_a", "principal_session_a")
        session = boundary.start_session(context, {"project_id": "project_a"})

        with self.assertRaisesRegex(sqlite3.IntegrityError, "dib_tenant_binding_immutable"):
            with store._write_transaction() as connection:
                connection.execute(
                    "UPDATE dib_tenant_bindings SET organization_id = 'org_b' WHERE session_id = ?",
                    (session["session_id"],),
                )

        with self.assertRaisesRegex(sqlite3.IntegrityError, "dib_tenant_binding_required"):
            store.start_session({"project_id": "unbound_project"})

    def test_package_allowlist_excludes_frozen_runtime(self) -> None:
        self.assertTrue(SEC_BETA_03_ALLOWLIST.isdisjoint(FROZEN_FILES))
        assert_all_frozen_files_unchanged(PACKAGE_ROOT)


if __name__ == "__main__":
    unittest.main()
