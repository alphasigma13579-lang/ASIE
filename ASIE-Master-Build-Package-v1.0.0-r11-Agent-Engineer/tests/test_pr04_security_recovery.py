from __future__ import annotations

import json
import tempfile
import threading
import unittest
from http.client import HTTPConnection
from pathlib import Path

from backend import asie_local_api as api
from backend.recovery import create_local_backup, restore_local_backup
from backend.repository import Repository


class PR04SecurityAndRecoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)
        self.repo = Repository(self.directory / "platform.sqlite3")
        self.admin = self.repo.create_user(
            email="admin@example.test",
            display_name="Admin",
            password="strong-local-password-admin",
            platform_role="platform_admin",
        )
        self.token, _ = self.repo.create_session(email=self.admin["email"], password="strong-local-password-admin")
        self.previous_repo = api.REPO
        api.REPO = self.repo
        self.addCleanup(setattr, api, "REPO", self.previous_repo)
        self.server = api.ThreadingHTTPServer(("127.0.0.1", 0), api.Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def request(self, method: str, path: str, *, headers: dict[str, str] | None = None, body: str | None = None) -> tuple[int, dict[str, str], dict[str, object]]:
        connection = HTTPConnection("127.0.0.1", self.server.server_address[1], timeout=10)
        try:
            connection.request(method, path, body=body, headers=headers or {})
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), json.loads(response.read().decode("utf-8"))
        finally:
            connection.close()

    def test_origin_is_strict_and_api_errors_have_request_correlation(self) -> None:
        status, headers, body = self.request("GET", "/api/health", headers={"Origin": "https://untrusted.example"})
        self.assertEqual(403, status)
        self.assertEqual("origin_not_allowed", body["error"])
        self.assertTrue(body["request_id"])
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(headers["Cache-Control"], "no-store")

    def test_local_origin_and_operations_health_are_server_authorized(self) -> None:
        status, headers, body = self.request(
            "GET",
            "/api/operations/health",
            headers={"Origin": "http://127.0.0.1:5194", "Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(200, status)
        self.assertEqual("http://127.0.0.1:5194", headers["Access-Control-Allow-Origin"])
        self.assertEqual("local_read_only", body["mode"])
        self.assertFalse(body["external_access_enabled"])
        self.assertEqual("ok", body["database"]["integrity_check"])

    def test_release_info_is_read_only_and_reports_external_access_disabled(self) -> None:
        status, _headers, body = self.request(
            "GET",
            "/api/operations/release-info",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(200, status)
        self.assertEqual("ASIE-local-r11-2026-07-20", body["release_id"])
        self.assertFalse(body["external_access_enabled"])
        self.assertEqual("deferred", body["backup_encryption"]["status"])
        self.assertGreaterEqual(len(body["sbom"]["dependencies"]), 5)

    def test_oversized_payload_is_rejected_before_reading_body(self) -> None:
        status, _headers, body = self.request(
            "POST",
            "/api/auth/login",
            headers={"Content-Length": str(api.MAX_JSON_BODY_BYTES + 1)},
        )
        self.assertEqual(413, status)
        self.assertEqual("request_body_too_large", body["error"])

    def test_organization_data_request_is_authorized_and_never_deletes_automatically(self) -> None:
        organization = self.repo.create_organization(name="Privacy org", owner_user_id=self.admin["user_id"])
        status, _headers, body = self.request(
            "POST",
            f"/api/organizations/{organization['organization_id']}/data-requests",
            headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"},
            body=json.dumps({"request_type": "delete", "legal_basis": "verified local request"}),
        )
        self.assertEqual(202, status)
        self.assertEqual("queued_for_legal_review", body["data_request"]["status"])
        self.assertFalse(body["automatic_deletion"])
        self.assertFalse(body["snapshot_mutation"])

    def test_backup_restore_verifies_database_and_snapshot_integrity(self) -> None:
        project = self.repo.create_project({"name": "Archive project"})
        connection = self.repo.connect()
        try:
            connection.execute(
                "INSERT INTO snapshots (snapshot_id, project_id, run_id, created_at, overview_json, report_json) VALUES (?, ?, ?, ?, ?, ?)",
                ("snap_archive", project.project_id, "run_archive", "2026-07-19T00:00:00+00:00", '{"snapshot":{"integrity_hash":"immutable-hash"}}', '{}'),
            )
            connection.commit()
        finally:
            connection.close()
        archive = self.directory / "archives" / "backup.asie-backup.zip"
        created = create_local_backup(database_path=self.repo.db_path, destination=archive)
        restored_path = self.directory / "restored.sqlite3"
        restored = restore_local_backup(archive_path=archive, target_database_path=restored_path)
        restored_repo = Repository(restored_path)
        self.assertEqual("ok", restored["sqlite_integrity"])
        self.assertEqual(created["files"]["asie_local.sqlite3"]["sha256"], restored["database_sha256"])
        self.assertEqual("immutable-hash", restored_repo.get_snapshot_overview("snap_archive")["snapshot"]["integrity_hash"])


if __name__ == "__main__":
    unittest.main()
