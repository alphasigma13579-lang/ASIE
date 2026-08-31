from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import threading
import unittest
from http.client import HTTPConnection
from pathlib import Path

from backend import asie_local_api as api
from backend.repository import Repository


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
INVITE_CLI = PACKAGE_ROOT / "tools" / "create_beta_registration_invite.py"


class BetaPasswordRegistrationTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.repo = Repository(Path(directory.name) / "registration.sqlite3")
        previous_repo = api.REPO
        api.REPO = self.repo
        self.addCleanup(setattr, api, "REPO", previous_repo)
        self.server = api.ThreadingHTTPServer(("127.0.0.1", 0), api.Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def post(self, path: str, payload: dict[str, object]) -> tuple[int, dict[str, object]]:
        connection = HTTPConnection("127.0.0.1", self.server.server_address[1], timeout=10)
        try:
            connection.request("POST", path, body=json.dumps(payload), headers={"Content-Type": "application/json"})
            response = connection.getresponse()
            return response.status, json.loads(response.read().decode("utf-8"))
        finally:
            connection.close()

    def test_email_bound_invite_creates_one_beta_owner_and_session(self) -> None:
        invite = self.repo.create_beta_registration_invite(
            email="beta-owner@example.test",
            organization_name="Beta Owner Organization",
        )
        status, body = self.post(
            "/api/auth/registrations/password",
            {
                "email": "beta-owner@example.test",
                "display_name": "Beta Owner",
                "password": "beta-pass01",
                "invite_token": invite["invite_token"],
            },
        )
        self.assertEqual(201, status)
        self.assertEqual("beta_full_access", body["entitlement_profile"])
        self.assertTrue(body["access_token"])
        memberships = self.repo.memberships_for_user(body["user"]["user_id"])
        self.assertEqual("organization_owner", memberships[0]["role"])
        self.assertEqual("beta_full_access", self.repo.subscription_for_organization(body["organization"]["organization_id"])["plan_code"])

    def test_password_length_is_limited_to_six_through_twelve_characters(self) -> None:
        for password in ("short", "thirteenchars"):
            invite = self.repo.create_beta_registration_invite(
                email=f"{len(password)}@example.test",
                organization_name="Password bounds",
            )
            status, body = self.post(
                "/api/auth/registrations/password",
                {
                    "email": invite["email"],
                    "display_name": "Beta Owner",
                    "password": password,
                    "invite_token": invite["invite_token"],
                },
            )
            self.assertEqual(400, status)
            self.assertEqual("password_length_must_be_between_6_and_12_characters", body["error"])

        for password in ("six-01", "twelve-char!"):
            invite = self.repo.create_beta_registration_invite(
                email=f"valid-{len(password)}@example.test",
                organization_name="Password bounds",
            )
            status, _body = self.post(
                "/api/auth/registrations/password",
                {
                    "email": invite["email"],
                    "display_name": "Beta Owner",
                    "password": password,
                    "invite_token": invite["invite_token"],
                },
            )
            self.assertEqual(201, status)

    def test_invite_cannot_be_used_by_a_different_email_or_reused(self) -> None:
        invite = self.repo.create_beta_registration_invite(email="bound@example.test", organization_name="Bound")
        wrong_status, wrong_body = self.post(
            "/api/auth/registrations/password",
            {"email": "other@example.test", "display_name": "Other", "password": "beta-pass02", "invite_token": invite["invite_token"]},
        )
        self.assertEqual(400, wrong_status)
        self.assertEqual("registration_invite_invalid", wrong_body["error"])
        first_status, _first_body = self.post(
            "/api/auth/registrations/password",
            {"email": "bound@example.test", "display_name": "Bound", "password": "beta-pass03", "invite_token": invite["invite_token"]},
        )
        self.assertEqual(201, first_status)
        reused_status, reused_body = self.post(
            "/api/auth/registrations/password",
            {"email": "bound@example.test", "display_name": "Bound", "password": "beta-pass03", "invite_token": invite["invite_token"]},
        )
        self.assertEqual(400, reused_status)
        self.assertEqual("registration_invite_invalid", reused_body["error"])

    def test_consumed_invite_can_be_reissued_without_reactivating_the_old_token(self) -> None:
        invite = self.repo.create_beta_registration_invite(email="again@example.test", organization_name="First")
        self.assertEqual(
            201,
            self.post(
                "/api/auth/registrations/password",
                {"email": "again@example.test", "display_name": "Again", "password": "beta-pass04", "invite_token": invite["invite_token"]},
            )[0],
        )
        replacement = self.repo.create_beta_registration_invite(email="again@example.test", organization_name="Replacement")
        self.assertNotEqual(invite["invite_token"], replacement["invite_token"])
        self.assertEqual(invite["invite_id"], replacement["invite_id"])
        self.assertEqual(
            replacement["invite_id"],
            next(event for event in self.repo.security_audit_events(limit=10) if event["action"] == "beta.invite.create")["target_id"],
        )

    def test_registered_email_is_reported_without_consuming_a_reissued_invite(self) -> None:
        invite = self.repo.create_beta_registration_invite(email="existing@example.test", organization_name="Existing")
        self.assertEqual(
            201,
            self.post(
                "/api/auth/registrations/password",
                {"email": "existing@example.test", "display_name": "Existing", "password": "beta-pass05", "invite_token": invite["invite_token"]},
            )[0],
        )
        replacement = self.repo.create_beta_registration_invite(email="existing@example.test", organization_name="Existing")
        status, body = self.post(
            "/api/auth/registrations/password",
            {"email": "existing@example.test", "display_name": "Existing", "password": "beta-pass05", "invite_token": replacement["invite_token"]},
        )
        self.assertEqual(400, status)
        self.assertEqual("email_already_registered", body["error"])

    def test_operator_cli_requires_explicit_confirmation_and_never_creates_a_session(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        database = Path(directory.name) / "invite-cli.sqlite3"
        command = [
            sys.executable,
            str(INVITE_CLI),
            "--database",
            str(database),
            "--email",
            "cli-invite@example.test",
            "--organization-name",
            "CLI Invite Organization",
        ]
        denied = subprocess.run(command, cwd=PACKAGE_ROOT, capture_output=True, text=True, timeout=30, check=False)
        self.assertNotEqual(0, denied.returncode)
        issued = subprocess.run(command + ["--confirm-invite"], cwd=PACKAGE_ROOT, capture_output=True, text=True, timeout=30, check=False)
        self.assertEqual(0, issued.returncode, issued.stderr)
        result = json.loads(issued.stdout)
        self.assertTrue(result["invite_token"])
        self.assertEqual(0, Repository(database).user_count())


if __name__ == "__main__":
    unittest.main()
