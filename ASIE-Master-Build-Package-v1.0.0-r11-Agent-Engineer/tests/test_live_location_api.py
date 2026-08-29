"""Providerless HTTP contract tests for structured location and competitor discovery.

These tests never create a real provider client.  They prove that the API binds
a request to the selected tenant/project before any provider admission, and
that an external-provider-disabled deployment returns the beta incident shape.
"""
from __future__ import annotations

import json
import os
import tempfile
import threading
import unittest
from http.client import HTTPConnection
from pathlib import Path
from unittest.mock import patch

import backend.asie_local_api as api
from backend.repository import Repository


class FakeGoogle:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def geocode_address(self, address: str, *, scope: object) -> dict:
        self.calls.append({"operation": "geocode_address", "address": address, "scope": scope})
        return {
            "payload": {
                "results": [
                    {
                        "placeId": "place-geocode-1",
                        "formattedAddress": "حي العليا، الرياض",
                        "location": {"latitude": 24.7136, "longitude": 46.6753},
                    }
                ]
            }
        }

    def reverse_geocode(self, latitude: float, longitude: float, *, scope: object) -> dict:
        self.calls.append(
            {
                "operation": "reverse_geocode",
                "latitude": latitude,
                "longitude": longitude,
                "scope": scope,
            }
        )
        return {
            "payload": {
                "results": [
                    {
                        "placeId": "place-reverse-1",
                        "formattedAddress": "حي العليا، الرياض",
                        "location": {"latitude": latitude, "longitude": longitude},
                    }
                ]
            }
        }

    def search_places_text(self, **kwargs: object) -> dict:
        self.calls.append({"operation": "search_places_text", **kwargs})
        return {
            "payload": {
                "places": [
                    {
                        "id": "place-competitor-1",
                        "displayName": {"text": "منافس حقيقي"},
                        "formattedAddress": "الرياض",
                        "location": {"latitude": 24.714, "longitude": 46.676},
                        "primaryType": "restaurant",
                        "businessStatus": "OPERATIONAL",
                        "googleMapsUri": "https://www.google.com/maps/place/?q=place_id:place-competitor-1",
                    }
                ]
            },
            "persistence_policy": "place_id_and_project_location_only_until_terms_review",
            "eligible_for_pinecone": False,
        }


class LiveLocationApiTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.repo = Repository(Path(directory.name) / "location-api.sqlite3")
        self.user_a = self.repo.create_user(
            email="location-a@example.test",
            display_name="Location owner A",
            password="location-password-a1",
        )
        self.user_b = self.repo.create_user(
            email="location-b@example.test",
            display_name="Location owner B",
            password="location-password-b1",
        )
        self.org_a = self.repo.create_organization(name="Location Org A", owner_user_id=self.user_a["user_id"])
        self.org_b = self.repo.create_organization(name="Location Org B", owner_user_id=self.user_b["user_id"])
        self.org_a_id = self.org_a["organization_id"]
        self.org_b_id = self.org_b["organization_id"]
        self.project_a = self.repo.create_project({"name": "Location A", "organization_id": self.org_a_id})
        self.project_b = self.repo.create_project({"name": "Location B", "organization_id": self.org_b_id})
        self.token_a, _ = self.repo.create_session(email=self.user_a["email"], password="location-password-a1")

        previous_repo = api.REPO
        api.REPO = self.repo
        self.addCleanup(setattr, api, "REPO", previous_repo)
        self.server = api.ThreadingHTTPServer(("127.0.0.1", 0), api.Handler)
        thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def request(
        self,
        method: str,
        path: str,
        *,
        token: str | None = None,
        organization_id: str | None = None,
        payload: dict | None = None,
    ) -> tuple[int, dict]:
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if organization_id:
            headers["X-ASIE-Organization-Id"] = organization_id
        connection = HTTPConnection("127.0.0.1", self.server.server_address[1], timeout=10)
        try:
            connection.request(method, path, body=json.dumps(payload) if payload is not None else None, headers=headers)
            response = connection.getresponse()
            raw = response.read().decode("utf-8")
        finally:
            connection.close()
        return response.status, json.loads(raw)

    def test_disabled_google_never_constructs_a_provider_client(self) -> None:
        with (
            patch.dict(os.environ, {"ASIE_ALLOW_EXTERNAL_FETCH": "false"}, clear=False),
            patch.object(api, "_live_google_client", side_effect=AssertionError("provider client must not be built")),
        ):
            status, body = self.request(
                "POST",
                "/api/v1/location/geocode",
                token=self.token_a,
                organization_id=self.org_a_id,
                payload={"project_id": self.project_a.project_id, "address": "حي العليا، الرياض"},
            )

        self.assertEqual(503, status)
        self.assertEqual("temporarily_unavailable", body["status"])
        self.assertFalse(body["external_fetch_enabled"])
        self.assertFalse(body["network_attempted"])
        self.assertFalse(body["payment_required"])
        self.assertFalse(body["upgrade_required"])

    def test_location_routes_bind_selected_tenant_and_never_persist_device_coordinates(self) -> None:
        fake_google = FakeGoogle()
        with (
            patch.dict(os.environ, {"ASIE_ALLOW_EXTERNAL_FETCH": "true"}, clear=False),
            patch.object(api, "_live_google_client", return_value=fake_google),
        ):
            status, geocode = self.request(
                "POST",
                "/api/v1/location/geocode",
                token=self.token_a,
                organization_id=self.org_a_id,
                payload={"project_id": self.project_a.project_id, "address": "حي العليا، الرياض"},
            )
            self.assertEqual(200, status)
            self.assertEqual("location.geocode.v1", geocode["contract_id"])
            self.assertTrue(geocode["location_confirmation_required"])
            self.assertFalse(geocode["device_location_persisted"])

            status, reverse = self.request(
                "POST",
                "/api/v1/location/reverse-geocode",
                token=self.token_a,
                organization_id=self.org_a_id,
                payload={"project_id": self.project_a.project_id, "latitude": 24.7136, "longitude": 46.6753},
            )
            self.assertEqual(200, status)
            self.assertEqual("location.reverse-geocode.v1", reverse["contract_id"])
            self.assertFalse(reverse["device_location_persisted"])

            status, competitors = self.request(
                "POST",
                "/api/v1/market/competitors/search",
                token=self.token_a,
                organization_id=self.org_a_id,
                payload={
                    "project_id": self.project_a.project_id,
                    "query": "مطاعم شاورما",
                    "latitude": 24.7136,
                    "longitude": 46.6753,
                    "radius_meters": 5000,
                },
            )
            self.assertEqual(200, status)
            self.assertEqual("market.competitors.search.v1", competitors["contract_id"])
            self.assertEqual("google_places", competitors["source"])
            self.assertFalse(competitors["eligible_for_pinecone"])
            self.assertEqual(1, len(competitors["competitors"]))

        self.assertEqual(
            ["geocode_address", "reverse_geocode", "search_places_text"],
            [call["operation"] for call in fake_google.calls],
        )
        for call in fake_google.calls:
            scope = call["scope"]
            self.assertEqual(self.org_a_id, scope.organization_id)
            self.assertEqual(self.project_a.project_id, scope.project_id)
            self.assertFalse(scope.preflight)

    def test_selected_organization_blocks_a_multi_member_from_foreign_project_provider_scope(self) -> None:
        self.repo.add_membership(
            organization_id=self.org_b_id,
            user_id=self.user_a["user_id"],
            role="analyst",
            actor_user_id=self.user_b["user_id"],
        )
        status, body = self.request(
            "POST",
            "/api/v1/location/geocode",
            token=self.token_a,
            organization_id=self.org_a_id,
            payload={"project_id": self.project_b.project_id, "address": "حي العليا، الرياض"},
        )

        self.assertEqual(403, status)
        self.assertEqual("permission_denied", body["error"])

    def test_location_routes_are_registered_with_their_response_contracts(self) -> None:
        registry_path = Path(__file__).resolve().parents[1] / "registry" / "asie-canonical-api-output.v1.json"
        register = json.loads(registry_path.read_text(encoding="utf-8"))
        routes = {
            (item["method"], item["path"]): item
            for item in register["backend_only_routes"]
        }
        expected = {
            ("GET", "/api/v1/providers/readiness"): "live.intelligence.provider.readiness.v1",
            ("POST", "/api/v1/location/geocode"): "location.geocode.v1",
            ("POST", "/api/v1/location/reverse-geocode"): "location.reverse-geocode.v1",
            ("POST", "/api/v1/market/competitors/search"): "market.competitors.search.v1",
        }
        for route, response_contract in expected.items():
            with self.subTest(route=route):
                self.assertIn(route, routes)
                self.assertEqual(response_contract, routes[route]["response"])

    def test_readiness_requires_authentication_and_hides_secret_presence(self) -> None:
        status, body = self.request("GET", "/api/v1/providers/readiness")
        self.assertEqual(401, status)
        self.assertEqual("authentication_required", body["error"])

        status, body = self.request("GET", "/api/v1/providers/readiness", token=self.token_a)
        self.assertEqual(200, status)
        self.assertEqual("live.intelligence.provider.readiness.v1", body["contract_id"])
        self.assertNotIn("secret_present", json.dumps(body, ensure_ascii=False))


if __name__ == "__main__":
    unittest.main()
