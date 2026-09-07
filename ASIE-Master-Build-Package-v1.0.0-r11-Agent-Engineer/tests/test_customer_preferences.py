"""Account language is self-scoped, authenticated, validated, and persistent."""
from __future__ import annotations

import json
import tempfile
import threading
import unittest
from http.client import HTTPConnection
from pathlib import Path

from backend import asie_local_api as api
from backend.repository import Repository


class CustomerPreferenceTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "preferences.sqlite3"
        self.repo = Repository(self.path)
        self.users = [
            self.repo.create_user(email=f"locale-{name}@example.test", display_name=name, password="test-pass-12")
            for name in ("a", "b")
        ]
        self.tokens = [
            self.repo.create_session(email=user["email"], password="test-pass-12")[0] for user in self.users
        ]
        old_repo = api.REPO
        api.REPO = self.repo
        self.addCleanup(setattr, api, "REPO", old_repo)
        self.server = api.ThreadingHTTPServer(("127.0.0.1", 0), api.Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def request(self, method: str, path: str, payload=None, token=None):
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        connection = HTTPConnection("127.0.0.1", self.server.server_address[1], timeout=10)
        try:
            connection.request(method, path, body=json.dumps(payload) if payload is not None else None, headers=headers)
            response = connection.getresponse()
            return response.status, json.loads(response.read())
        finally:
            connection.close()

    def test_default_and_persistence_are_per_account(self):
        self.assertEqual("ar", self.request("GET", "/api/auth/me", token=self.tokens[0])[1]["locale"])
        self.assertEqual((200, {"locale": "en"}), self.request("PATCH", "/api/auth/preferences", {"locale": "en"}, self.tokens[0]))
        self.assertEqual("en", self.request("GET", "/api/auth/me", token=self.tokens[0])[1]["locale"])
        self.assertEqual("ar", self.request("GET", "/api/auth/me", token=self.tokens[1])[1]["locale"])
        reopened = Repository(self.path)
        self.assertEqual("en", reopened.customer_locale(self.users[0]["user_id"]))
        self.assertEqual(2, reopened.user_count())
        self.assertIsNotNone(reopened.principal_for_token(self.tokens[0]))

    def test_no_client_selected_account_or_unknown_field_is_accepted(self):
        for payload in (
            {"locale": "en", "user_id": self.users[1]["user_id"]},
            {"locale": "en", "organization_id": "another-organization"},
            {"locale": "fr"}, {"locale": ["en"]}, {"locale": None}, {},
        ):
            with self.subTest(payload=payload):
                self.assertEqual(400, self.request("PATCH", "/api/auth/preferences", payload, self.tokens[0])[0])
        self.assertEqual("ar", self.repo.customer_locale(self.users[0]["user_id"]))
        self.assertEqual("ar", self.repo.customer_locale(self.users[1]["user_id"]))

    def test_anonymous_and_revoked_sessions_cannot_change_preferences(self):
        self.assertEqual(401, self.request("PATCH", "/api/auth/preferences", {"locale": "en"})[0])
        self.repo.revoke_session(self.tokens[0])
        self.assertEqual(401, self.request("PATCH", "/api/auth/preferences", {"locale": "en"}, self.tokens[0])[0])
        self.assertEqual("ar", self.repo.customer_locale(self.users[0]["user_id"]))


if __name__ == "__main__":
    unittest.main()
