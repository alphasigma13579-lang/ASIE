from __future__ import annotations

import json
import tempfile
import threading
import unittest
from http.client import HTTPConnection
from pathlib import Path

from backend import asie_local_api as api
from backend.repository import Repository
from backend.market_context import market_provider_policy, normalize_market_location


class LocalAlphaLoopTests(unittest.TestCase):
    def test_market_context_is_local_only_and_cannot_own_decision_truth(self) -> None:
        record = normalize_market_location({"record_type": "competitor", "name": "محل تجريبي", "sector": "خدمات", "geography": "الرياض", "coordinates": {"lat": 24.7, "lng": 46.7}, "data_mode": "demo_simulated_external"})
        self.assertEqual("DEMO / LOCAL ONLY", record["display_badge"])
        self.assertEqual("blocked", record["production_admission"])
        self.assertFalse(record["external_fetch_enabled"])
        self.assertEqual("context_only", record["decision_authority"])
        policy = market_provider_policy()
        self.assertFalse(policy["google_maps_enabled"])
        self.assertFalse(policy["gps_enabled"])
        self.assertFalse(policy["may_change_finance_or_verdict"])

    def test_customer_loop_stays_local_and_reaches_snapshot_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Repository(Path(directory) / "alpha.sqlite3")
            user = repo.create_user(email="alpha@example.test", display_name="Alpha", password="strong-local-password-alpha")
            organization = repo.create_organization(name="Alpha local", owner_user_id=user["user_id"])
            token, _ = repo.create_session(email=user["email"], password="strong-local-password-alpha")
            previous_repo = api.REPO
            api.REPO = repo
            server = api.ThreadingHTTPServer(("127.0.0.1", 0), api.Handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                headers = {"Authorization": f"Bearer {token}", "X-ASIE-Organization-Id": organization["organization_id"], "Content-Type": "application/json"}
                connection = HTTPConnection("127.0.0.1", server.server_address[1], timeout=20)
                try:
                    project_payload = {"name": "Alpha project", "sector": "خدمات", "jurisdiction": "Saudi Arabia", "depth_profile": "standard", "inputs": {"startup_cost": 250000, "monthly_fixed_cost": 62000, "unit_price": 85, "variable_cost": 34, "monthly_units": 1600, "activity_description": "خدمة محلية"}}
                    connection.request("POST", "/api/projects", body=json.dumps(project_payload), headers=headers)
                    project_response = connection.getresponse()
                    project_body = json.loads(project_response.read().decode("utf-8"))
                    self.assertEqual(201, project_response.status)
                    project_id = project_body["project"]["project_id"]
                    connection.request("POST", f"/api/projects/{project_id}/runs", body=json.dumps({"scenario_id": "baseline"}), headers=headers)
                    run_response = connection.getresponse()
                    run_body = json.loads(run_response.read().decode("utf-8"))
                    self.assertEqual(201, run_response.status)
                    overview = run_body["overview"]
                    snapshot_id = overview["snapshot"]["snapshot_id"]
                    self.assertTrue(overview["snapshot"]["immutable"])
                    self.assertFalse(overview["audit"]["source_fetch_enabled"])
                    connection.request("GET", f"/api/snapshots/{snapshot_id}/funder-report.html", headers=headers)
                    report_response = connection.getresponse()
                    report_html = report_response.read().decode("utf-8")
                    self.assertEqual(200, report_response.status)
                    self.assertIn(snapshot_id, report_html)
                    self.assertIn("lang='ar' dir='rtl'", report_html)
                finally:
                    connection.close()
            finally:
                server.shutdown()
                server.server_close()
                api.REPO = previous_repo


if __name__ == "__main__":
    unittest.main()
