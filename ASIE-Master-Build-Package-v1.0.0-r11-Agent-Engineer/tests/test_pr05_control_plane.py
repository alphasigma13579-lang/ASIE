from __future__ import annotations

import json
import tempfile
import threading
import unittest
from http.client import HTTPConnection
from pathlib import Path

from backend import asie_local_api as api
from backend.repository import Repository


class PR05ControlPlaneTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.repo = Repository(Path(directory.name) / "control.sqlite3")
        self.admin = self.repo.create_user(email="admin@example.test", display_name="Admin", password="strong-local-password-admin", platform_role="platform_admin")
        self.owner = self.repo.create_user(email="owner@example.test", display_name="Owner", password="strong-local-password-owner")
        self.organization = self.repo.create_organization(name="Control Organization", owner_user_id=self.owner["user_id"])
        self.token, _ = self.repo.create_session(email=self.admin["email"], password="strong-local-password-admin")
        previous = api.REPO
        api.REPO = self.repo
        self.addCleanup(setattr, api, "REPO", previous)
        self.server = api.ThreadingHTTPServer(("127.0.0.1", 0), api.Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def request(self, method: str, path: str, payload: dict | None = None, *, authenticated: bool = True) -> tuple[int, dict]:
        connection = HTTPConnection("127.0.0.1", self.server.server_address[1], timeout=10)
        try:
            body = json.dumps(payload) if payload is not None else None
            headers = {"Content-Type": "application/json"}
            if authenticated:
                headers["Authorization"] = f"Bearer {self.token}"
            connection.request(method, path, body=body, headers=headers)
            response = connection.getresponse()
            return response.status, json.loads(response.read().decode("utf-8"))
        finally:
            connection.close()

    def test_beta_access_status_exposes_free_full_access_contract(self) -> None:
        """The live HTTP contract exposes one free entitlement without upsell."""

        denied_status, denied_body = self.request("GET", "/api/v1/beta/access-status", authenticated=False)
        self.assertEqual(401, denied_status)
        self.assertEqual("authentication_required", denied_body["error"])

        with tempfile.TemporaryDirectory() as empty_directory:
            api.REPO = Repository(Path(empty_directory) / "empty-control.sqlite3")
            try:
                empty_status, empty_body = self.request("GET", "/api/v1/beta/access-status", authenticated=False)
            finally:
                api.REPO = self.repo
        self.assertEqual(401, empty_status)
        self.assertEqual("authentication_required", empty_body["error"])

        status, body = self.request("GET", "/api/v1/beta/access-status")
        self.assertEqual(200, status)
        self.assertEqual("beta_full_access", body["entitlement_profile"])
        self.assertEqual("not_applicable_during_beta", body["billing_status"])
        self.assertEqual("observability_only", body["usage_metering_mode"])
        self.assertEqual([], body["feature_restrictions"])
        self.assertFalse(body["upgrade_required"])
        self.assertFalse(body["payment_method_required"])

    def test_subscription_mutation_is_dormant_during_closed_beta(self) -> None:
        """The legacy component remains stored but cannot change beta entitlement."""

        before = self.repo.subscription_for_organization(self.organization["organization_id"])
        status, body = self.request("POST", f"/api/admin/organizations/{self.organization['organization_id']}/subscription", {"plan_code": "local_pro", "lifecycle_status": "trial", "quota": {"projects": 10}, "reason": "internal trial"})
        self.assertEqual(409, status)
        self.assertEqual("beta_billing_disabled", body["error"])
        self.assertEqual(before, self.repo.subscription_for_organization(self.organization["organization_id"]))
        denied = [
            event
            for event in self.repo.security_audit_events(organization_id=self.organization["organization_id"])
            if event["action"] == "subscription.change" and event["result"] == "denied"
        ]
        self.assertEqual(1, len(denied))
        self.assertEqual("beta_billing_disabled", denied[0]["reason"])
        self.assertTrue(denied[0]["correlation_id"])

    def test_invoice_is_blocked_but_notifications_remain_local(self) -> None:
        """Billing stays dormant without regressing the unrelated notification path."""

        status, invoice = self.request("POST", f"/api/admin/organizations/{self.organization['organization_id']}/invoices", {"amount_minor": 12500, "currency": "sar"})
        self.assertEqual(409, status)
        self.assertEqual("beta_billing_disabled", invoice["error"])
        self.assertEqual([], self.repo.local_invoices(self.organization["organization_id"]))
        denied = [
            event
            for event in self.repo.security_audit_events(organization_id=self.organization["organization_id"])
            if event["action"] == "invoice.create" and event["result"] == "denied"
        ]
        self.assertEqual(1, len(denied))
        self.assertEqual("beta_billing_disabled", denied[0]["reason"])
        self.assertTrue(denied[0]["correlation_id"])
        status, notification = self.request("POST", f"/api/admin/organizations/{self.organization['organization_id']}/notifications", {"template_id": "review_requested", "reference_type": "snapshot", "reference_id": "snap_reference"})
        self.assertEqual(201, status)
        self.assertEqual("in_app_pending", notification["notification"]["delivery_status"])
        self.assertFalse(notification["external_delivery_enabled"])

    def test_admin_overview_is_platform_authorized(self) -> None:
        status, overview = self.request("GET", "/api/admin/overview")
        self.assertEqual(200, status)
        self.assertIn(self.organization["organization_id"], [row["organization_id"] for row in overview["organizations"]])
        self.assertFalse(overview["external_payments_enabled"])
        self.assertFalse(overview["external_notifications_enabled"])


if __name__ == "__main__":
    unittest.main()
