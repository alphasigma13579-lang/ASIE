from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from backend.repository import Repository


class LocalAccountRecoveryTests(unittest.TestCase):
    def test_local_self_service_recovery_is_one_time_and_revokes_sessions(self) -> None:
        with TemporaryDirectory() as directory:
            repo = Repository(Path(directory) / "self-recovery.sqlite3")
            user = repo.create_user(email="self@example.test", display_name="Self", password="strong-local-password-old")
            token, _ = repo.create_session(email=user["email"], password="strong-local-password-old")
            request = repo.create_password_recovery_request(email=user["email"])
            self.assertTrue(request["accepted"])
            self.assertFalse(repo.create_password_recovery_request(email="missing@example.test")["recovery_token"])
            repo.consume_password_recovery_token(token=request["recovery_token"], password="strong-local-password-new")
            self.assertIsNone(repo.principal_for_token(token))
            with self.assertRaisesRegex(ValueError, "invalid_or_expired_recovery_token"):
                repo.consume_password_recovery_token(token=request["recovery_token"], password="strong-local-password-again")

    def test_local_admin_reset_revokes_existing_sessions_and_accepts_new_password(self) -> None:
        with TemporaryDirectory() as directory:
            repo = Repository(Path(directory) / "recovery.sqlite3")
            admin = repo.create_user(email="admin@example.test", display_name="Admin", password="strong-local-password-admin", platform_role="platform_admin")
            user = repo.create_user(email="user@example.test", display_name="User", password="strong-local-password-user")
            token, _ = repo.create_session(email=user["email"], password="strong-local-password-user")
            repo.reset_local_password(user_id=user["user_id"], password="strong-local-password-new", actor_user_id=admin["user_id"])
            self.assertIsNone(repo.principal_for_token(token))
            next_token, _ = repo.create_session(email=user["email"], password="strong-local-password-new")
            self.assertIsNotNone(repo.principal_for_token(next_token))
            self.assertIn("identity.local_password_reset", [event["action"] for event in repo.security_audit_events(limit=10)])


if __name__ == "__main__":
    unittest.main()
