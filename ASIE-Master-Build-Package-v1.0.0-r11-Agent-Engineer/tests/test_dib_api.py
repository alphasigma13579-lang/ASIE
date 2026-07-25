from __future__ import annotations

import unittest
from pathlib import Path

from backend.dib_api import DIB_API_ID, DIB_API_ROUTES, DIBApiError, create_dib_api_controller
from backend.dib_registry_admission import assert_all_frozen_files_unchanged

PACKAGE_ROOT = Path(__file__).resolve().parents[1]


class DIBApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.controller = create_dib_api_controller()
        self.addCleanup(self.controller.close)

    def test_dib_api_status_exposes_controlled_routes_and_disabled_wiring(self) -> None:
        response = self.controller.dispatch("GET", "/api/dib/status").to_public()
        status = response["dib_api"]
        self.assertEqual(response["status"], 200)
        self.assertEqual(status["api_id"], DIB_API_ID)
        self.assertEqual(status["route_count"], len(DIB_API_ROUTES))
        self.assertTrue(all(route["path"].startswith("/api/dib") for route in status["routes"]))
        self.assertFalse(status["external_fetch_enabled"])
        self.assertFalse(status["ai_provider_enabled"])
        self.assertFalse(status["finance_wiring_enabled"])
        self.assertFalse(status["snapshot_wiring_enabled"])
        self.assertFalse(status["http_server_mutation_required"])
        self.assertFalse(status["frozen_runtime_files_mutated"])

    def test_dib_api_session_blueprint_manifest_and_gate_flow(self) -> None:
        profile = {
            "project_id": "project_api_shawarma",
            "name": "محل شاورما",
            "sector": "Food Service",
            "activity": "shawarma shop",
            "location_country": "SA",
        }
        session_response = self.controller.dispatch(
            "POST",
            "/api/dib/sessions",
            {"project_profile": profile},
        ).to_public()
        self.assertEqual(session_response["status"], 201)
        session_id = session_response["session"]["session_id"]
        self.assertFalse(session_response["snapshot_mutation"])

        blueprint_response = self.controller.dispatch(
            "POST",
            f"/api/dib/sessions/{session_id}/blueprints",
            {
                "source": "manual_table",
                "intake_payload": {
                    "file_name": "manual",
                    "rows": [
                        {"input_key": "startup_cost", "label": "equipment", "value": 155000},
                        {"input_key": "monthly_fixed_cost", "label": "rent and salaries", "value": 36000},
                        {"input_key": "unit_price", "label": "meal price", "value": 18},
                        {"input_key": "variable_cost", "label": "ingredients", "value": 7},
                        {"input_key": "monthly_units", "label": "monthly sales", "value": 4200},
                    ],
                },
            },
        ).to_public()
        self.assertEqual(blueprint_response["status"], 201)
        self.assertEqual(blueprint_response["blueprint"]["payload"]["contract_id"], "dynamic.input.blueprint.v1")
        self.assertFalse(blueprint_response["snapshot_mutation"])

        manifest_response = self.controller.dispatch(
            "POST",
            f"/api/dib/sessions/{session_id}/approved-manifests",
            {},
        ).to_public()
        manifest = manifest_response["approved_manifest"]["payload"]
        self.assertEqual(manifest_response["status"], 201)
        self.assertEqual(manifest["contract_id"], "approved.input.manifest.v1")
        self.assertEqual(manifest["status"], "approved")
        self.assertNotIn("finance", manifest)
        self.assertFalse(manifest_response["finance_wiring_enabled"])
        self.assertFalse(manifest_response["snapshot_mutation"])

        gate_response = self.controller.dispatch(
            "POST",
            f"/api/dib/sessions/{session_id}/validation-gates",
            {},
        ).to_public()
        gate = gate_response["validation_gate"]["payload"]
        self.assertEqual(gate_response["status"], 201)
        self.assertEqual(gate["contract_id"], "manifest.validation.v1")
        self.assertEqual(gate["status"], "passed")
        self.assertNotIn("snapshot", gate)
        self.assertFalse(gate_response["finance_wiring_enabled"])
        self.assertFalse(gate_response["snapshot_mutation"])

        loaded = self.controller.dispatch("GET", f"/api/dib/sessions/{session_id}").to_public()["session"]
        self.assertEqual(loaded["status"], "validation_passed")
        self.assertEqual(loaded["current_blueprint"]["contract_id"], "dynamic.input.blueprint.v1")
        self.assertEqual(loaded["approved_manifest"]["contract_id"], "approved.input.manifest.v1")
        self.assertEqual(loaded["validation_gate"]["contract_id"], "manifest.validation.v1")
        self.assertFalse(loaded["external_fetch_enabled"])
        self.assertFalse(loaded["ai_provider_enabled"])

        events = self.controller.dispatch("GET", f"/api/dib/sessions/{session_id}/events").to_public()["events"]
        self.assertEqual(
            [event["event_type"] for event in events],
            ["session.started", "blueprint.saved", "manifest.saved", "validation_gate.saved"],
        )

    def test_dib_api_rejects_forbidden_payloads_and_unknown_routes(self) -> None:
        with self.assertRaises(DIBApiError) as raw_prompt_error:
            self.controller.dispatch("POST", "/api/dib/sessions", {"project_id": "bad", "raw_prompt": "build numbers"})
        self.assertEqual(raw_prompt_error.exception.status, 422)

        session = self.controller.dispatch("POST", "/api/dib/sessions", {"project_id": "project_guarded"}).to_public()["session"]
        with self.assertRaises(DIBApiError) as finance_error:
            self.controller.dispatch(
                "POST",
                f"/api/dib/sessions/{session['session_id']}/blueprints",
                {"blueprint": {"contract_id": "dynamic.input.blueprint.v1", "finance": {"status": "ready"}}},
            )
        self.assertEqual(finance_error.exception.status, 422)

        with self.assertRaises(DIBApiError) as network_error:
            self.controller.dispatch(
                "POST",
                f"/api/dib/sessions/{session['session_id']}/approved-manifests",
                {"manifest": {"external_fetch_enabled": True}},
            )
        self.assertEqual(network_error.exception.status, 422)

        with self.assertRaises(DIBApiError) as route_error:
            self.controller.dispatch("GET", "/api/dib/unknown")
        self.assertEqual(route_error.exception.status, 404)

    def test_dib_api_can_close_session_without_snapshot_mutation(self) -> None:
        session = self.controller.dispatch("POST", "/api/dib/sessions", {"project_id": "project_close"}).to_public()["session"]
        closed = self.controller.dispatch("POST", f"/api/dib/sessions/{session['session_id']}/close").to_public()
        self.assertEqual(closed["session"]["status"], "closed")
        self.assertFalse(closed["snapshot_mutation"])
        events = self.controller.dispatch("GET", f"/api/dib/sessions/{session['session_id']}/events").to_public()["events"]
        self.assertEqual(events[-1]["event_type"], "session.closed")

    def test_frozen_runtime_files_remain_unchanged(self) -> None:
        assert_all_frozen_files_unchanged(PACKAGE_ROOT)


if __name__ == "__main__":
    unittest.main()
