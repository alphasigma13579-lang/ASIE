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

    def request(self, method: str, path: str, payload: dict | None = None) -> tuple[int, dict]:
        connection = HTTPConnection("127.0.0.1", self.server.server_address[1], timeout=10)
        try:
            body = json.dumps(payload) if payload is not None else None
            connection.request(method, path, body=body, headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"})
            response = connection.getresponse()
            return response.status, json.loads(response.read().decode("utf-8"))
        finally:
            connection.close()

    def test_subscription_change_is_audited_and_does_not_enable_payment(self) -> None:
        status, body = self.request("POST", f"/api/admin/organizations/{self.organization['organization_id']}/subscription", {"plan_code": "local_pro", "lifecycle_status": "trial", "quota": {"projects": 10}, "reason": "internal trial"})
        self.assertEqual(200, status)
        self.assertEqual("trial", body["subscription"]["lifecycle_status"])
        self.assertFalse(body["external_payments_enabled"])
        self.assertEqual("subscription.change", self.repo.security_audit_events(limit=1)[0]["action"])

    def test_invoice_and_notifications_are_local_only(self) -> None:
        status, invoice = self.request("POST", f"/api/admin/organizations/{self.organization['organization_id']}/invoices", {"amount_minor": 12500, "currency": "sar"})
        self.assertEqual(201, status)
        self.assertEqual("issued_uncollected", invoice["invoice"]["status"])
        self.assertFalse(invoice["payment_collection_enabled"])
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
