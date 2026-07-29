from __future__ import annotations

import json
import os
import threading
import unittest
from contextlib import closing
from http.client import HTTPConnection
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from backend import asie_local_api as api
from backend.repository import Repository


class LocalAccountRecoveryTests(unittest.TestCase):
    def test_self_service_request_is_non_enumerating_and_issues_no_token(self) -> None:
        with TemporaryDirectory() as directory:
            repo = Repository(Path(directory) / "self-recovery.sqlite3")
            user = repo.create_user(
                email="self@example.test",
                display_name="Self",
                password="strong-local-password-old",
            )

            existing = repo.create_password_recovery_request(email=user["email"])
            missing = repo.create_password_recovery_request(email="missing@example.test")

            self.assertEqual(
                {"accepted": True, "external_delivery_enabled": False},
                existing,
            )
            self.assertEqual(existing, missing)
            self.assertNotIn("recovery_token", existing)
            with closing(repo.connect()) as connection:
                token_count = connection.execute(
                    "SELECT COUNT(*) AS count FROM password_recovery_tokens"
                ).fetchone()["count"]
            self.assertEqual(0, token_count)
            with self.assertRaisesRegex(ValueError, "invalid_or_expired_recovery_token"):
                repo.consume_password_recovery_token(
                    token="not-issued",
                    password="strong-local-password-new",
                )

    def test_local_admin_reset_revokes_existing_sessions_and_accepts_new_password(self) -> None:
        with TemporaryDirectory() as directory:
            repo = Repository(Path(directory) / "recovery.sqlite3")
            admin = repo.create_user(
                email="admin@example.test",
                display_name="Admin",
                password="strong-local-password-admin",
                platform_role="platform_admin",
            )
            user = repo.create_user(
                email="user@example.test",
                display_name="User",
                password="strong-local-password-user",
            )
            token, _ = repo.create_session(
                email=user["email"],
                password="strong-local-password-user",
            )
            repo.reset_local_password(
                user_id=user["user_id"],
                password="strong-local-password-new",
                actor_user_id=admin["user_id"],
            )
            self.assertIsNone(repo.principal_for_token(token))
            next_token, _ = repo.create_session(
                email=user["email"],
                password="strong-local-password-new",
            )
            self.assertIsNotNone(repo.principal_for_token(next_token))
            self.assertIn(
                "identity.local_password_reset",
                [event["action"] for event in repo.security_audit_events(limit=10)],
            )


class PasswordRecoveryHttpLockdownTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.repo = Repository(Path(directory.name) / "http-recovery.sqlite3")
        self.repo.create_user(
            email="platform-admin@example.test",
            display_name="Platform Admin",
            password="strong-platform-admin-password",
            platform_role="platform_admin",
        )
        previous_repo = api.REPO
        api.REPO = self.repo
        self.addCleanup(setattr, api, "REPO", previous_repo)

        self.server = api.ThreadingHTTPServer(("127.0.0.1", 0), api.Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def request(self, path: str, payload: dict[str, object]) -> tuple[int, dict[str, object]]:
        connection = HTTPConnection("127.0.0.1", self.server.server_address[1], timeout=10)
        try:
            connection.request(
                "POST",
                path,
                body=json.dumps(payload),
                headers={"Content-Type": "application/json"},
            )
            response = connection.getresponse()
            return response.status, json.loads(response.read().decode("utf-8"))
        finally:
            connection.close()

    def test_anonymous_http_recovery_issues_no_secret_and_complete_fails_closed(self) -> None:
        environment = {
            "ASIE_ENV": "production",
            "ASIE_ALLOW_LOCAL_BOOTSTRAP": "",
            "ASIE_ALLOW_LEGACY_LOCAL_OPERATOR": "",
        }
        with mock.patch.dict(os.environ, environment, clear=False):
            existing_status, existing_body = self.request(
                "/api/auth/password-recovery/request",
                {"email": "platform-admin@example.test"},
            )
            missing_status, missing_body = self.request(
                "/api/auth/password-recovery/request",
                {"email": "missing@example.test"},
            )
            complete_status, complete_body = self.request(
                "/api/auth/password-recovery/complete",
                {
                    "recovery_token": "attacker-controlled",
                    "new_password": "attacker-controlled-password",
                },
            )

        self.assertEqual(202, existing_status)
        self.assertEqual(existing_status, missing_status)
        self.assertEqual(existing_body, missing_body)
        self.assertEqual(
            {"accepted": True, "external_delivery_enabled": False},
            existing_body,
        )
        self.assertNotIn("recovery_token", existing_body)
        self.assertEqual(503, complete_status)
        self.assertEqual(
            "password_recovery_external_delivery_unavailable",
            complete_body["error"],
        )
        token, user = self.repo.create_session(
            email="platform-admin@example.test",
            password="strong-platform-admin-password",
        )
        self.assertEqual("platform_admin", user["platform_role"])
        self.assertIsNotNone(self.repo.principal_for_token(token))


if __name__ == "__main__":
    unittest.main()
