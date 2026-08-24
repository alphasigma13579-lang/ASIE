from __future__ import annotations

from types import SimpleNamespace

from backend.live_intelligence_product import LiveIntelligenceProductError, LiveIntelligenceProductService
from backend.provider_security_control_plane import TrustedProviderScope


class FakeTavily:
    def search(self, **kwargs):
        return {
            "payload": {
                "results": [
                    {"title": "Official source", "url": "https://example.com/source", "content": "Market context"}
                ]
            },
            "network_attempted": True,
            "review_status": "review_required",
        }


class FakeGoogle:
    def search_places_text(self, **kwargs):
        return {
            "payload": {
                "places": [
                    {
                        "id": "place-1",
                        "displayName": {"text": "Competitor"},
                        "formattedAddress": "Riyadh",
                        "location": {"latitude": 24.7, "longitude": 46.7},
                        "primaryType": "restaurant",
                        "businessStatus": "OPERATIONAL",
                        "googleMapsUri": "https://maps.google.com/example",
                    }
                ]
            }
        }

    def geocode_address(self, address):
        return {"payload": {"results": []}, "network_attempted": True, "review_status": "review_required"}


class FakePinecone:
    def search_public_knowledge(self, **kwargs):
        return {
            "payload": {
                "result": {
                    "hits": [
                        {
                            "_id": "vision-1",
                            "_score": 0.92,
                            "fields": {
                                "chunk_text": "Vision 2030 alignment text",
                                "source_url": "https://vision2030.gov.sa/",
                                "source_id": "vision2030-ar",
                                "publisher": "Saudi Vision 2030",
                                "authority": "saudi_official",
                                "license_id": "saudi-open-data-license-2.0",
                                "license_ref": "docs/legal/third-party/saudi-open-data/README.md",
                                "attribution": "Saudi Vision 2030",
                                "sector": "all",
                                "geography": "saudi_arabia",
                                "language": "en",
                                "published_at": "unknown",
                                "retrieved_at": "2026-08-20T00:00:00Z",
                                "content_sha256": "a" * 64,
                                "version": 1,
                                "freshness_days": 365,
                                "fresh_until": "2027-08-20T00:00:00Z",
                                "expires_at": "2027-11-20T00:00:00Z",
                                "unit": "not_applicable",
                                "confidence": 0.98,
                                "evidence_ref": "public:vision2030-ar:sha256:" + "a" * 64,
                                "admission_status": "auto_admitted_official_open",
                                "data_classification": "public",
                            },
                        }
                    ]
                }
            }
        }

    def describe_index(self):
        return {"network_attempted": True, "review_status": "review_required"}


class FakeDeepSeek:
    def create_narrative(self, **kwargs):
        return {
            "provider_id": "deepseek",
            "payload": {"choices": [{"message": {"content": "Reviewed narrative"}}]},
            "controlled_numbers": [],
            "sovereign_verdict": None,
        }


def service():
    return LiveIntelligenceProductService(
        deepseek=FakeDeepSeek(), tavily=FakeTavily(), google=FakeGoogle(), pinecone=FakePinecone()
    )


def tenant_scope():
    return TrustedProviderScope.for_tenant(
        principal=SimpleNamespace(
            user_id="user-1",
            session_id="session-1",
            organization_id="org-1",
            role="analyst",
        ),
        project_id="project-1",
        project_organization_resolver=lambda _: "org-1",
    )


def test_market_context_combines_sources_places_and_knowledge_without_finance_mutation():
    result = service().build_market_context(
        scope=tenant_scope(),
        query="shawarma market Riyadh",
        location_query="shawarma restaurants Riyadh",
    )
    assert result["contract_id"] == "live.intelligence.context.v1"
    assert result["status"] == "review_required"
    assert len(result["source_candidates"]) == 1
    assert len(result["places"]) == 1
    assert len(result["knowledge_hits"]) == 1
    assert result["public_evidence_context"]["status"] == "ready"
    assert result["human_review_required"] is True
    assert result["eligible_for_controlled_assumptions"] is False
    assert result["controlled_numbers"] == []
    assert result["finance_mutated"] is False
    assert result["snapshot_mutated"] is False
    assert len(result["context_hash"]) == 64


def test_narrative_requires_approved_context():
    try:
        service().create_reviewed_narrative(
            request_id="request-1",
            prompt_template_id="template:market-explanation:v1",
            approved_context={"review_status": "review_required", "eligible_for_narrative": True, "evidence_refs": ["e:1"]},
            user_instruction="Explain the evidence",
        )
    except LiveIntelligenceProductError as exc:
        assert str(exc) == "approved_context_required"
    else:
        raise AssertionError("unapproved context must be rejected")


def test_reviewed_narrative_preserves_provider_boundaries():
    result = service().create_reviewed_narrative(
        request_id="request-1",
        prompt_template_id="template:market-explanation:v1",
        approved_context={"review_status": "approved", "eligible_for_narrative": True, "evidence_refs": ["e:1"]},
        user_instruction="Explain the approved evidence",
    )
    assert result["contract_id"] == "live.intelligence.narrative.v1"
    assert result["controlled_numbers"] == []
    assert result["sovereign_verdict"] is None
    assert result["human_review_status"] == "required_pending"
    assert result["finance_mutated"] is False
    assert result["snapshot_mutated"] is False
