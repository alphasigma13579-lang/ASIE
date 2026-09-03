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
from types import SimpleNamespace
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


class FakeMarketContextService:
    def __init__(self, *, status: str = "review_required") -> None:
        self.calls: list[dict] = []
        self.status = status

    def build_market_context(self, **kwargs: object) -> dict:
        self.calls.append(kwargs)
        scope = kwargs["scope"]
        return {
            "contract_id": "live.intelligence.context.v1",
            "project_id": scope.project_id,
            "organization_id": scope.organization_id,
            "status": self.status,
            "source_candidates": [],
            "places": [],
            "knowledge_hits": [],
            "public_evidence_context": {"status": "not_ready", "evidence": [], "gaps": []},
            "failures": [],
            "human_review_required": True,
            "eligible_for_controlled_assumptions": False,
            "controlled_numbers": [],
            "finance_mutated": False,
            "snapshot_mutated": False,
            "context_hash": "a" * 64,
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
            platform_role="platform_admin",
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
        self.project_a = self.repo.create_project(
            {
                "name": "Location A",
                "organization_id": self.org_a_id,
                "inputs": {
                    "location_latitude": 24.7136,
                    "location_longitude": 46.6753,
                    "primary_sector_id": "SEC-11",
                    "location_country": "Saudi Arabia",
                },
            }
        )
        self.project_b = self.repo.create_project(
            {
                "name": "Location B",
                "organization_id": self.org_b_id,
                "inputs": {"location_latitude": 21.4858, "location_longitude": 39.1925},
            }
        )
        self.token_a, _ = self.repo.create_session(email=self.user_a["email"], password="location-password-a1")
        self.token_b, _ = self.repo.create_session(email=self.user_b["email"], password="location-password-b1")

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
        events = [
            event for event in self.repo.security_audit_events(organization_id=self.org_a_id)
            if event["action"] == "provider.request" and event["target_id"] == "google_maps_platform"
        ]
        self.assertEqual("denied", events[-1]["result"])
        self.assertEqual("external_fetch_disabled", events[-1]["reason"])

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

    def test_market_routes_reject_coordinates_that_do_not_match_the_confirmed_project_location(self) -> None:
        with (
            patch.dict(os.environ, {"ASIE_ALLOW_EXTERNAL_FETCH": "true"}, clear=False),
            patch.object(api, "_live_google_client", side_effect=AssertionError("mismatched coordinates must not reach Google")),
        ):
            for path, payload in (
                (
                    "/api/v1/location/reverse-geocode",
                    {"project_id": self.project_a.project_id, "latitude": 21.4858, "longitude": 39.1925},
                ),
                (
                    "/api/v1/market/competitors/search",
                    {
                        "project_id": self.project_a.project_id,
                        "query": "مطاعم شاورما",
                        "latitude": 21.4858,
                        "longitude": 39.1925,
                        "radius_meters": 3000,
                    },
                ),
            ):
                with self.subTest(path=path):
                    status, body = self.request(
                        "POST",
                        path,
                        token=self.token_a,
                        organization_id=self.org_a_id,
                        payload=payload,
                    )
                    self.assertEqual(409, status)
                    self.assertEqual("project_location_mismatch", body["error"])

    def test_market_routes_require_a_confirmed_project_location_before_provider_admission(self) -> None:
        unlocated = self.repo.create_project({"name": "Unlocated", "organization_id": self.org_a_id})
        with (
            patch.dict(os.environ, {"ASIE_ALLOW_EXTERNAL_FETCH": "true"}, clear=False),
            patch.object(api, "_live_google_client", side_effect=AssertionError("unconfirmed location must not reach Google")),
        ):
            status, body = self.request(
                "POST",
                "/api/v1/location/reverse-geocode",
                token=self.token_a,
                organization_id=self.org_a_id,
                payload={"project_id": unlocated.project_id, "latitude": 24.7136, "longitude": 46.6753},
            )
        self.assertEqual(409, status)
        self.assertEqual("confirmed_project_location_required", body["error"])

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

    def test_live_market_context_is_tenant_bound_and_requires_confirmed_location(self) -> None:
        service = FakeMarketContextService()
        with (
            patch.dict(os.environ, {"ASIE_ALLOW_EXTERNAL_FETCH": "true"}, clear=False),
            patch.object(api, "_live_market_context_service", return_value=service),
        ):
            status, body = self.request(
                "POST",
                "/api/v1/intelligence/market-context",
                token=self.token_a,
                organization_id=self.org_a_id,
                payload={
                    "project_id": self.project_a.project_id,
                    "query": "سوق المطاعم في الرياض",
                    "location_query": "مطاعم قرب العليا",
                    "sector_id": "untrusted-client-sector",
                    "geography": "untrusted-client-geography",
                },
            )

        self.assertEqual(200, status)
        self.assertEqual("live.intelligence.customer-context.v1", body["contract_id"])
        self.assertNotIn("organization_id", body)
        self.assertNotIn("project_id", body)
        self.assertNotIn("failures", body)
        self.assertIsNone(body["public_evidence_context"]["as_of"])
        self.assertEqual(1, len(service.calls))
        call = service.calls[0]
        self.assertEqual(self.org_a_id, call["scope"].organization_id)
        self.assertEqual(self.project_a.project_id, call["scope"].project_id)
        self.assertEqual((24.7136, 46.6753), (call["latitude"], call["longitude"]))
        self.assertEqual("SEC-11", call["sector_id"])
        self.assertEqual("Saudi Arabia", call["geography"])
        self.assertFalse(body["finance_mutated"])
        self.assertFalse(body["snapshot_mutated"])
        matching_events = [
            event for event in self.repo.security_audit_events(organization_id=self.org_a_id)
            if event["action"] == "live_market_context" and event["result"] == "allowed"
        ]
        self.assertEqual(1, len(matching_events))
        self.assertEqual(self.user_a["user_id"], matching_events[0]["actor_user_id"])

    def test_live_market_context_records_an_empty_provider_response_as_a_failure(self) -> None:
        service = FakeMarketContextService(status="failed")
        with (
            patch.dict(os.environ, {"ASIE_ALLOW_EXTERNAL_FETCH": "true"}, clear=False),
            patch.object(api, "_live_market_context_service", return_value=service),
        ):
            status, body = self.request(
                "POST",
                "/api/v1/intelligence/market-context",
                token=self.token_a,
                organization_id=self.org_a_id,
                payload={
                    "project_id": self.project_a.project_id,
                    "query": "سوق المطاعم في الرياض",
                    "location_query": "مطاعم قرب العليا",
                },
            )

        self.assertEqual(200, status)
        self.assertEqual("failed", body["status"])
        events = [
            event for event in self.repo.security_audit_events(organization_id=self.org_a_id)
            if event["action"] == "live_market_context"
        ]
        self.assertEqual("failed", events[-1]["result"])
        self.assertEqual("no_reviewable_results", events[-1]["reason"])

    def test_official_discovery_policy_preserves_source_block_and_existing_scopes(self) -> None:
        scope = SimpleNamespace(organization_id=self.org_a_id, project_id=self.project_a.project_id)
        blocked = {
            "source_id": "blocked-source",
            "route": "official_open_dataset_or_api",
            "state": "blocked",
            "url": "https://blocked.example.test/data",
            "notes": {
                "discovery_allowed": True,
                "discovery_sectors": ["food_service"],
                "discovery_geographies": ["saudi_arabia"],
            },
        }
        enabled = {
            "source_id": "enabled-source",
            "route": "official_open_dataset_or_api",
            "state": "enabled",
            "url": "https://enabled.example.test/data",
            "notes": {
                "discovery_allowed": True,
                "discovery_sectors": ["food_service"],
                "discovery_geographies": ["saudi_arabia"],
            },
        }
        with patch.object(api.REPO, "source_records", return_value=[blocked, enabled]):
            policy = api._official_discovery_policy(scope)

        self.assertEqual([enabled], list(policy.records))

    def test_customer_market_context_normalizes_optional_display_values(self) -> None:
        view = api._customer_market_context(
            {
                "status": "review_required",
                "knowledge_hits": [
                    {"confidence": "0.8"},
                    {"confidence": 2},
                    {"confidence": True},
                ],
                "public_evidence_context": {"as_of": 20260902},
            }
        )
        self.assertEqual([0.8, None, None], [row["confidence"] for row in view["knowledge_hits"]])
        self.assertEqual("20260902", view["public_evidence_context"]["as_of"])

    def test_live_market_context_stays_disabled_without_network_authorization(self) -> None:
        with (
            patch.dict(os.environ, {"ASIE_ALLOW_EXTERNAL_FETCH": "false"}, clear=False),
            patch.object(api, "_live_market_context_service", side_effect=AssertionError("service must not be created")),
        ):
            status, body = self.request(
                "POST",
                "/api/v1/intelligence/market-context",
                token=self.token_a,
                organization_id=self.org_a_id,
                payload={
                    "project_id": self.project_a.project_id,
                    "query": "سوق المطاعم في الرياض",
                    "location_query": "مطاعم قرب العليا",
                },
            )

        self.assertEqual(503, status)
        self.assertEqual("temporarily_unavailable", body["status"])
        self.assertFalse(body["network_attempted"])
        events = [
            event for event in self.repo.security_audit_events(organization_id=self.org_a_id)
            if event["action"] == "live_market_context"
        ]
        self.assertEqual("denied", events[-1]["result"])
        self.assertEqual("external_fetch_disabled", events[-1]["reason"])

    def test_live_market_context_restricts_live_providers_to_platform_admin(self) -> None:
        self.repo.add_membership(
            organization_id=self.org_a_id,
            user_id=self.user_b["user_id"],
            role="analyst",
            actor_user_id=self.user_a["user_id"],
        )
        with (
            patch.dict(os.environ, {"ASIE_ALLOW_EXTERNAL_FETCH": "true"}, clear=False),
            patch.object(api, "_live_market_context_service", side_effect=AssertionError("non-owner must not construct providers")),
        ):
            status, body = self.request(
                "POST",
                "/api/v1/intelligence/market-context",
                token=self.token_b,
                organization_id=self.org_a_id,
                payload={
                    "project_id": self.project_a.project_id,
                    "query": "سوق المطاعم في الرياض",
                    "location_query": "مطاعم قرب العليا",
                },
            )

        self.assertEqual(403, status)
        self.assertEqual("permission_denied", body["error"])

    def test_google_live_routes_restrict_providers_to_platform_admin(self) -> None:
        self.repo.add_membership(
            organization_id=self.org_a_id,
            user_id=self.user_b["user_id"],
            role="analyst",
            actor_user_id=self.user_a["user_id"],
        )
        with (
            patch.dict(os.environ, {"ASIE_ALLOW_EXTERNAL_FETCH": "true"}, clear=False),
            patch.object(api, "_live_google_client", side_effect=AssertionError("non-owner must not construct providers")),
        ):
            status, body = self.request(
                "POST",
                "/api/v1/location/geocode",
                token=self.token_b,
                organization_id=self.org_a_id,
                payload={"project_id": self.project_a.project_id, "address": "حي العليا، الرياض"},
            )

        self.assertEqual(403, status)
        self.assertEqual("permission_denied", body["error"])

    def test_live_market_context_audits_provider_configuration_failure(self) -> None:
        class UnavailableMarketContextService:
            def build_market_context(self, **_: object) -> dict:
                raise ValueError("missing_provider_secret")

        with (
            patch.dict(os.environ, {"ASIE_ALLOW_EXTERNAL_FETCH": "true"}, clear=False),
            patch.object(api, "_live_market_context_service", return_value=UnavailableMarketContextService()),
        ):
            status, body = self.request(
                "POST",
                "/api/v1/intelligence/market-context",
                token=self.token_a,
                organization_id=self.org_a_id,
                payload={
                    "project_id": self.project_a.project_id,
                    "query": "سوق المطاعم في الرياض",
                    "location_query": "مطاعم قرب العليا",
                },
            )

        self.assertEqual(503, status)
        self.assertEqual("temporarily_unavailable", body["status"])
        events = [
            event for event in self.repo.security_audit_events(organization_id=self.org_a_id)
            if event["action"] == "live_market_context"
        ]
        self.assertEqual("failed", events[-1]["result"])
        self.assertEqual("provider_unavailable", events[-1]["reason"])

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
            ("POST", "/api/v1/intelligence/market-context"): "live.intelligence.customer-context.v1",
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

        status, body = self.request("GET", "/api/v1/providers/readiness", token=self.token_b)
        self.assertEqual(403, status)
        self.assertEqual("permission_denied", body["error"])


if __name__ == "__main__":
    unittest.main()
