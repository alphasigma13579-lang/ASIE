from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping, Sequence

import pytest

from backend.external_acquisition import ExternalAcquisitionError
from backend.live_provider_catalog import LIVE_PROVIDER_CATALOG, provider_catalog_snapshot
from backend.tavily_source_admission import TavilySourceAdmissionPolicy
from backend.live_provider_clients import (
    DeepSeekNarrativeClient,
    GoogleLocationClient,
    PineconeKnowledgeClient,
    ProviderConfigurationError,
    TavilyResearchClient,
    tenant_project_namespace,
)
from backend.provider_security_control_plane import ProviderRequestContext, TrustedProviderScope


PACKAGE_ROOT = Path(__file__).resolve().parents[1]


def trusted_scope(organization_id: str = "org-1", project_id: str = "project-1") -> TrustedProviderScope:
    return TrustedProviderScope.for_tenant(
        principal=SimpleNamespace(
            user_id="user-1",
            session_id="session-1",
            organization_id=organization_id,
            role="analyst",
        ),
        project_id=project_id,
        project_organization_resolver=lambda _: organization_id,
    )


def context_snapshot(context: ProviderRequestContext | None) -> dict[str, Any]:
    if context is None:
        return {}
    return {
        "organization_id": context.organization_id,
        "project_id": context.project_id,
        "operation": context.operation,
        "cost_units": context.cost_units,
        "preflight": context.preflight,
    }


class FakeTransport:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.index_host = "vision2030-kb-test.svc.aped-0000.pinecone.io"

    def request_json(
        self,
        *,
        provider_id: str,
        url: str,
        method: str = "POST",
        headers: Mapping[str, str] | None = None,
        body: Mapping[str, Any] | None = None,
        expected_statuses: Sequence[int] = (200,),
        security_context: ProviderRequestContext | None = None,
    ) -> dict[str, Any]:
        self.calls.append(
            {
                "kind": "json",
                "provider_id": provider_id,
                "url": url,
                "method": method,
                "headers": dict(headers or {}),
                "body": dict(body or {}),
                "expected_statuses": tuple(expected_statuses),
                "security_context": context_snapshot(security_context),
            }
        )
        if provider_id == "pinecone" and "api.pinecone.io/indexes/" in url:
            payload: Any = {
                "name": "vision2030-kb",
                "host": self.index_host,
                "status": {"ready": True, "state": "Ready"},
                "embed": {
                    "model": "multilingual-e5-large",
                    "field_map": {"text": "chunk_text"},
                },
            }
        elif provider_id == "deepseek":
            payload = {
                "id": "chat-1",
                "object": "chat.completion",
                "model": "deepseek-v4-flash",
                "choices": [{
                    "index": 0,
                    "finish_reason": "stop",
                    "message": {"role": "assistant", "content": "مسودة تفسيرية"},
                }],
                "usage": {"completion_tokens": 4, "prompt_tokens": 8, "total_tokens": 12},
            }
        elif provider_id == "tavily":
            if url.endswith("/search"):
                results: Any = [{
                    "title": "Official source",
                    "url": "https://example.com/source",
                    "content": "source",
                    "score": 0.9,
                }]
                payload = {"results": results, "response_time": 0.1, "usage": {"credits": 1}, "request_id": "tv-1"}
            elif url.endswith("/map"):
                payload = {"base_url": "example.com", "results": ["https://example.com/source"], "response_time": 0.1, "usage": {"credits": 1}, "request_id": "tv-1"}
            else:
                payload = {
                    "base_url": "example.com",
                    "results": [{"url": "https://example.com/source", "raw_content": "source"}],
                    "failed_results": [],
                    "response_time": 0.1,
                    "usage": {"credits": 1},
                    "request_id": "tv-1",
                }
        elif provider_id == "google_maps_platform":
            if "places:searchText" in url:
                payload = {
                    "places": [
                        {
                            "id": "place-1",
                            "displayName": {"text": "منافس تجريبي"},
                            "formattedAddress": "الرياض",
                            "location": {"latitude": 24.7, "longitude": 46.7},
                            "primaryType": "restaurant",
                            "businessStatus": "OPERATIONAL",
                            "googleMapsUri": "https://www.google.com/maps/place/?q=place_id:place-1",
                        }
                    ]
                }
            else:
                payload = {
                    "results": [
                        {
                            "placeId": "place-1",
                            "formattedAddress": "الرياض",
                            "location": {"latitude": 24.7, "longitude": 46.7},
                            "addressComponents": [
                                {
                                    "longText": "الرياض",
                                    "shortText": "الرياض",
                                    "types": ["locality", "political"],
                                }
                            ],
                            "viewport": {
                                "low": {"latitude": 24.6, "longitude": 46.6},
                                "high": {"latitude": 24.8, "longitude": 46.8},
                            },
                            "granularity": "ROOFTOP",
                            "plusCode": {"globalCode": "7HMPQMGF+P4"},
                        }
                    ]
                }
        elif provider_id == "pinecone" and url.endswith("/search"):
            payload = {"result": {"hits": [{"_id": "doc-1", "_score": 0.9, "fields": {"review_status": "approved"}}]}}
        else:
            payload = {}
        return {
            "provider_id": provider_id,
            "url": url,
            "status_code": 200,
            "response_bytes": 10,
            "sha256": "a" * 64,
            "payload": payload,
            "retrieved_at": "2026-07-27T00:00:00+00:00",
            "network_attempted": True,
            "review_status": "review_required",
            "eligible_for_controlled_assumptions": False,
        }

    def request_ndjson(
        self,
        *,
        provider_id: str,
        url: str,
        headers: Mapping[str, str],
        records: Sequence[Mapping[str, Any]],
        expected_statuses: Sequence[int] = (200, 201),
        security_context: ProviderRequestContext | None = None,
    ) -> dict[str, Any]:
        self.calls.append(
            {
                "kind": "ndjson",
                "provider_id": provider_id,
                "url": url,
                "headers": dict(headers),
                "records": [dict(record) for record in records],
                "expected_statuses": tuple(expected_statuses),
                "security_context": context_snapshot(security_context),
            }
        )
        return {
            "provider_id": provider_id,
            "url": url,
            "status_code": 201,
            "response_bytes": 0,
            "sha256": "b" * 64,
            "payload": {"accepted": True},
            "retrieved_at": "2026-07-27T00:00:00+00:00",
            "network_attempted": True,
            "review_status": "review_required",
            "eligible_for_controlled_assumptions": False,
        }


def test_provider_catalog_contains_only_approved_initial_providers() -> None:
    provider_ids = {provider.provider_id for provider in LIVE_PROVIDER_CATALOG}
    assert provider_ids == {"deepseek", "tavily", "google_maps_platform", "pinecone"}
    snapshot = provider_catalog_snapshot()
    assert snapshot["ai_owns_numbers"] is False
    assert snapshot["ai_owns_verdict"] is False
    assert snapshot["pinecone_is_source_of_truth"] is False
    assert snapshot["tavily_results_require_source_review"] is True
    assert snapshot["google_places_persistence_requires_terms_review"] is True
    assert snapshot["secrets_stored"] is False
    google = next(provider for provider in LIVE_PROVIDER_CATALOG if provider.provider_id == "google_maps_platform")
    assert google.allowed_operations == ("geocode_address", "geocode_preflight", "reverse_geocode", "search_places_text")
    assert google.preflight_operations == ("geocode_preflight",)


def test_deepseek_is_narrative_only_and_requires_governed_prompt_metadata() -> None:
    transport = FakeTransport()
    client = DeepSeekNarrativeClient(transport=transport, api_key="secret", model="deepseek-v4-flash")
    result = client.create_narrative(
        scope=trusted_scope(),
        request_id="req-1",
        prompt_template_id="sanad.project-gap-explanation.v1",
        prompt_hash="a" * 64,
        context_refs=["evidence:1", "snapshot:1"],
        messages=[{"role": "system", "content": "اكتب تفسيرًا دون أرقام جديدة."}, {"role": "user", "content": "فسّر المخاطر."}],
        thinking=True,
    )
    call = transport.calls[0]
    assert call["url"] == "https://api.deepseek.com/chat/completions"
    assert call["body"]["model"] == "deepseek-v4-flash"
    assert call["body"]["thinking"] == {"type": "enabled"}
    assert result["output_owner_domain"] == "narrative_only"
    assert result["claims_numeric_truth"] is False
    assert result["controlled_numbers"] == []
    assert result["sovereign_verdict"] is None
    assert result["human_review_status"] == "required_pending"
    assert call["security_context"]["operation"] == "create_narrative"
    assert call["security_context"]["organization_id"] == "org-1"
    assert result["prompt_content_stored"] is False

    with pytest.raises(ProviderConfigurationError, match="prompt_hash_must_be_sha256"):
        client.create_narrative(
            scope=trusted_scope(),
            request_id="req-2",
            prompt_template_id="x",
            prompt_hash="bad",
            context_refs=["evidence:1"],
            messages=[{"role": "user", "content": "test"}],
        )
    with pytest.raises(ProviderConfigurationError, match="deepseek_model_not_allowlisted"):
        DeepSeekNarrativeClient(transport=transport, api_key="secret", model="unreviewed-model")


def test_tavily_disables_generated_answer_and_external_crawl_expansion() -> None:
    transport = FakeTransport()
    source = {
        "source_id": "MONSHAAT_OPEN_DATA",
        "publisher": "Monsha'at",
        "route": "official_open_dataset_or_api",
        "state": "enabled",
        "url": "https://monshaat.gov.sa/open-data",
        "terms_url": "https://monshaat.gov.sa/terms",
        "terms_hash": "a" * 64,
        "license_snapshot_ref": "license:monshaat:v1",
        "attribution": "Monsha'at open data",
        "classification": "public",
        "pdpl_check": "passed",
        "nca_check": "passed",
        "lawful_purpose": "saudi_market_research",
        "reviewer": "platform-reviewer",
        "reviewer_decision": "approved",
        "organization_id": "__platform__",
        "project_id": "*",
        "discovery_allowed": True,
        "discovery_sectors": ["sme"],
        "discovery_geographies": ["saudi_arabia"],
        "allowed_paths": ["/open-data"],
    }
    policy = TavilySourceAdmissionPolicy.from_records(
        organization_id="org-1",
        project_id="project-1",
        records=[source],
    )
    client = TavilyResearchClient(
        transport=transport,
        api_key="secret",
        scope=trusted_scope(),
        project_id="asie",
        admission_policy=policy,
    )
    result = client.search(
        query="المنشآت الصغيرة في السعودية",
        sector_id="sme",
        geography="saudi_arabia",
        include_domains=["monshaat.gov.sa"],
    )
    search_call = transport.calls[-1]
    assert search_call["url"] == "https://api.tavily.com/search"
    assert search_call["body"]["include_answer"] is False
    assert search_call["body"]["include_raw_content"] is False
    assert search_call["body"]["country"] == "saudi arabia"
    assert search_call["body"]["include_domains"] == ["monshaat.gov.sa"]
    assert search_call["headers"]["X-Project-ID"] == "asie"
    assert result["eligible_for_controlled_assumptions"] is False

    crawl = client.crawl(
        source_id="MONSHAAT_OPEN_DATA",
        url="https://monshaat.gov.sa/open-data/indicators",
        instructions="ابحث عن البيانات المفتوحة",
    )
    crawl_call = transport.calls[-1]
    assert crawl_call["url"] == "https://api.tavily.com/crawl"
    assert crawl_call["body"]["allow_external"] is False
    assert crawl_call["body"]["limit"] == 50
    assert crawl["source_admission"]["source_id"] == "MONSHAAT_OPEN_DATA"
    assert crawl["eligible_for_controlled_assumptions"] is False


def test_google_key_stays_in_header_and_places_are_not_pinecone_eligible() -> None:
    transport = FakeTransport()
    client = GoogleLocationClient(transport=transport, api_key="google-secret")

    preflight_scope = TrustedProviderScope.for_platform_preflight()
    client.geocode_address(
        "الرياض، المملكة العربية السعودية",
        scope=preflight_scope,
    )
    preflight_call = transport.calls[-1]
    assert preflight_call["security_context"]["preflight"] is True
    assert preflight_call["security_context"]["organization_id"] == "__platform__"

    client.geocode_address(
        "حي العليا، الرياض",
        scope=trusted_scope(),
    )
    call = transport.calls[-1]
    assert "google-secret" not in call["url"]
    assert call["headers"]["X-Goog-Api-Key"] == "google-secret"
    assert call["method"] == "GET"

    client.reverse_geocode(
        24.7136,
        46.6753,
        scope=trusted_scope(),
    )
    call = transport.calls[-1]
    assert call["url"] == "https://geocode.googleapis.com/v4/geocode/location/24.7136,46.6753"
    assert "google-secret" not in call["url"]
    assert call["headers"]["X-Goog-Api-Key"] == "google-secret"
    assert call["security_context"]["operation"] == "reverse_geocode"

    result = client.search_places_text(
        scope=trusted_scope(),
        text_query="مطاعم شاورما",
        latitude=24.7136,
        longitude=46.6753,
        radius_meters=5000,
    )
    call = transport.calls[-1]
    assert call["url"] == "https://places.googleapis.com/v1/places:searchText"
    assert "google-secret" not in call["url"]
    assert result["eligible_for_pinecone"] is False
    assert result["persistence_policy"] == "place_id_and_project_location_only_until_terms_review"
    assert call["security_context"]["operation"] == "search_places_text"


def test_google_response_contract_rejects_unvalidated_echoed_fields() -> None:
    class IncompleteGoogleTransport(FakeTransport):
        def request_json(self, **kwargs: Any) -> dict[str, Any]:
            response = super().request_json(**kwargs)
            payload = response["payload"]
            if "places:searchText" in str(kwargs["url"]):
                payload["places"][0].pop("googleMapsUri")
            else:
                payload["results"][0].pop("formattedAddress")
            return response

    client = GoogleLocationClient(transport=IncompleteGoogleTransport(), api_key="google-secret")
    with pytest.raises(ExternalAcquisitionError, match="formattedAddress"):
        client.geocode_address("الرياض", scope=trusted_scope())
    with pytest.raises(ExternalAcquisitionError, match="googleMapsUri"):
        client.search_places_text(
            scope=trusted_scope(),
            text_query="مطاعم شاورما",
            latitude=24.7136,
            longitude=46.6753,
        )


def test_pinecone_uses_existing_vision2030_index_and_tenant_project_namespace() -> None:
    transport = FakeTransport()
    client = PineconeKnowledgeClient(
        transport=transport,
        api_key="pinecone-secret",
        index_name="vision2030-kb",
        namespace_prefix="asie",
    )
    description = client.describe_index()
    assert description["index_name"] == "vision2030-kb"
    assert description["pinecone_is_source_of_truth"] is False
    assert transport.calls[0]["url"] == "https://api.pinecone.io/indexes/vision2030-kb"
    assert "pinecone-secret" not in transport.calls[0]["url"]

    result = client.upsert_approved_text(
        scope=trusted_scope(),
        records=[
            {
                "_id": "vision-2030-001",
                "chunk_text": "نص موثق من وثيقة رؤية السعودية 2030.",
                "source_url": "https://www.vision2030.gov.sa/",
                "source_id": "VISION2030_OFFICIAL",
                "evidence_ref": "evidence:vision2030:001",
                "review_status": "approved",
                "data_classification": "public",
            }
        ],
    )
    upsert_call = transport.calls[-1]
    assert upsert_call["kind"] == "ndjson"
    assert transport.index_host in upsert_call["url"]
    assert result["index_name"] == "vision2030-kb"
    assert result["source_of_truth"] is False
    assert result["records_required_approved_review"] is True
    assert upsert_call["records"][0]["review_status"] == "approved"
    assert upsert_call["records"][0]["organization_ref"] != "org-1"
    assert upsert_call["records"][0]["project_ref"] != "project-1"

    search = client.search_text(
        scope=trusted_scope(),
        query="مستهدفات المنشآت الصغيرة",
    )
    assert search["retrieval_requires_evidence_validation"] is True
    assert "/records/namespaces/" in transport.calls[-1]["url"]
    assert transport.calls[-1]["body"]["query"]["top_k"] == 8


def test_pinecone_rejects_unreviewed_or_sensitive_records() -> None:
    client = PineconeKnowledgeClient(transport=FakeTransport(), api_key="secret", index_name="vision2030-kb")
    base = {
        "_id": "1",
        "chunk_text": "text",
        "source_url": "https://example.com",
        "source_id": "source",
        "evidence_ref": "evidence:1",
    }
    with pytest.raises(ProviderConfigurationError, match="requires_approved_review"):
        client.upsert_approved_text(
            scope=trusted_scope("org", "project"),
            records=[{**base, "review_status": "draft", "data_classification": "public"}],
        )
    with pytest.raises(ProviderConfigurationError, match="classification_forbidden"):
        client.upsert_approved_text(
            scope=trusted_scope("org", "project"),
            records=[{**base, "review_status": "approved", "data_classification": "secret"}],
        )


def test_namespace_is_deterministic_and_isolates_projects() -> None:
    first = tenant_project_namespace("org-1", "project-1")
    assert first == tenant_project_namespace("org-1", "project-1")
    assert first != tenant_project_namespace("org-1", "project-2")
    assert first != tenant_project_namespace("org-2", "project-1")
    assert "org-1" not in first
    assert "project-1" not in first


def test_live_clients_do_not_import_frozen_runtime() -> None:
    source = (PACKAGE_ROOT / "backend" / "live_provider_clients.py").read_text(encoding="utf-8")
    catalog = (PACKAGE_ROOT / "backend" / "live_provider_catalog.py").read_text(encoding="utf-8")
    combined = source + catalog
    for forbidden in (
        "backend.aas_kernel",
        "backend.system_bus",
        "ProjectRunWorkflow",
        "SnapshotAssembly",
        "FinanceEngine",
    ):
        assert forbidden not in combined
    assert "vision2030-kb" in source
    assert "deepseek-v4-flash" in source
    assert "include_answer\": False" in source
    assert "eligible_for_pinecone\": False" in source

