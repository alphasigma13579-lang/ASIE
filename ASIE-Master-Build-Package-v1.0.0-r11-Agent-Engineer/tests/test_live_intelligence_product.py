from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import backend.live_intelligence_product as live_intelligence_product
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
            "source_admission": {"include_domains": ["example.com"]},
        }


class FakeGoogle:
    def __init__(self) -> None:
        self.search_scopes: list[object] = []
        self.geocode_scopes: list[TrustedProviderScope] = []
        self.preflight_scopes: list[TrustedProviderScope] = []

    def search_places_text(self, **kwargs: object) -> dict[str, object]:
        self.search_scopes.append(kwargs.get("scope"))
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

    def preflight_geocode(
        self,
        address: str,
        *,
        scope: TrustedProviderScope,
    ) -> dict[str, object]:
        if not address:
            raise AssertionError("address_required")
        self.preflight_scopes.append(scope)
        return {"payload": {"results": []}, "network_attempted": True, "review_status": "review_required"}

    def geocode_address(
        self,
        address: str,
        *,
        scope: TrustedProviderScope,
    ) -> dict[str, object]:
        if not address:
            raise AssertionError("address_required")
        self.geocode_scopes.append(scope)
        return {"payload": {"results": []}, "network_attempted": True, "review_status": "review_required"}


class FakePinecone:
    def search_public_knowledge(self, **kwargs):
        retrieved_at = datetime.now(timezone.utc) - timedelta(days=1)
        fresh_until = retrieved_at + timedelta(days=365)
        expires_at = fresh_until + timedelta(days=90)

        def iso(value: datetime) -> str:
            return value.isoformat().replace("+00:00", "Z")

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
                                "retrieved_at": iso(retrieved_at),
                                "content_sha256": "a" * 64,
                                "version": 1,
                                "freshness_days": 365,
                                "fresh_until": iso(fresh_until),
                                "expires_at": iso(expires_at),
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
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def create_narrative(self, **kwargs):
        self.calls.append(kwargs)
        return {
            "provider_id": "deepseek",
            "payload": {"choices": [{"message": {"content": "Reviewed narrative"}}]},
            "controlled_numbers": [],
            "sovereign_verdict": None,
        }


class FailingPinecone(FakePinecone):
    def search_public_knowledge(self, **kwargs):
        raise RuntimeError("simulated pinecone outage")


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


def test_preflight_forwards_platform_scope_to_google(monkeypatch):
    monkeypatch.setenv("ASIE_ALLOW_EXTERNAL_FETCH", "true")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "configured-for-fake-client")
    product = service()

    result = product.preflight()

    assert result["checks"]["google_maps_platform"]["status"] == "live"
    assert product.google.geocode_scopes == []
    assert len(product.google.preflight_scopes) == 1
    assert product.google.preflight_scopes[0].preflight is True
    assert product.google.preflight_scopes[0].organization_id == "__platform__"


def test_market_context_combines_sources_places_and_knowledge_without_finance_mutation():
    product = service()
    scope = tenant_scope()
    result = product.build_market_context(
        scope=scope,
        query="shawarma market Riyadh",
        location_query="shawarma restaurants Riyadh",
    )
    assert result["contract_id"] == "live.intelligence.context.v1"
    assert result["status"] == "review_required"
    assert len(result["source_candidates"]) == 1
    assert len(result["places"]) == 1
    assert len(result["knowledge_hits"]) == 1
    assert result["knowledge_hits"][0]["review_status"] == "review_required"
    assert result["public_evidence_context"]["status"] == "ready"
    assert result["human_review_required"] is True
    assert result["eligible_for_controlled_assumptions"] is False
    assert product.google.search_scopes == [scope]
    assert result["controlled_numbers"] == []
    assert result["finance_mutated"] is False
    assert result["snapshot_mutated"] is False
    assert len(result["context_hash"]) == 64


def test_market_context_rejects_tavily_results_outside_the_admitted_domains():
    class OutOfScopeTavily(FakeTavily):
        def search(self, **kwargs):
            response = super().search(**kwargs)
            response["payload"]["results"].append(
                {"title": "Unadmitted source", "url": "https://outside.example/evidence", "content": "Must not reach users"}
            )
            return response

    product = service()
    product.tavily = OutOfScopeTavily()

    result = product.build_market_context(
        scope=tenant_scope(),
        query="shawarma market Riyadh",
        location_query="shawarma restaurants Riyadh",
    )

    assert [candidate["url"] for candidate in result["source_candidates"]] == ["https://example.com/source"]
    assert any(failure["reason"] == "result_domain_not_admitted" for failure in result["failures"])


def test_context_hash_excludes_only_the_volatile_evidence_clock(monkeypatch):
    as_of_values = iter(("2026-08-24T10:00:00Z", "2026-08-24T10:00:01Z"))

    def stable_evidence_context(_response):
        return {
            "contract_id": "public-knowledge-evidence.v1",
            "status": "ready",
            "as_of": next(as_of_values),
            "evidence": [
                {
                    "record_id": "vision-1",
                    "score": 0.92,
                    "chunk_text": "Stable public evidence",
                    "source_id": "vision2030-ar",
                    "publisher": "Saudi Vision 2030",
                    "authority": "saudi_official",
                    "source_url": "https://vision2030.gov.sa/",
                    "license_id": "saudi-open-data-license-2.0",
                    "license_ref": "docs/legal/third-party/saudi-open-data/README.md",
                    "attribution": "Saudi Vision 2030",
                    "sector": "all",
                    "geography": "saudi_arabia",
                    "language": "en",
                    "published_at": "unknown",
                    "retrieved_at": "2026-08-23T00:00:00Z",
                    "content_sha256": "a" * 64,
                    "version": 1,
                    "freshness_days": 365,
                    "fresh_until": "2027-08-23T00:00:00Z",
                    "expires_at": "2027-11-21T00:00:00Z",
                    "unit": "not_applicable",
                    "confidence": 0.98,
                    "evidence_ref": "public:vision2030-ar:sha256:" + "a" * 64,
                    "admission_status": "auto_admitted_official_open",
                    "data_classification": "public",
                    "source_of_truth": False,
                }
            ],
            "gaps": [],
            "permitted_uses": ["market_size"],
            "claims_project_success": False,
            "claims_funding_acceptance": False,
            "source_of_truth": False,
            "snapshot_eligible": False,
            "requires_separate_assumption_admission_for_finance": True,
        }

    monkeypatch.setattr(
        live_intelligence_product,
        "build_feasibility_evidence_context",
        stable_evidence_context,
    )
    first = service().build_market_context(
        scope=tenant_scope(),
        query="shawarma market Riyadh",
        location_query="shawarma restaurants Riyadh",
    )
    second = service().build_market_context(
        scope=tenant_scope(),
        query="shawarma market Riyadh",
        location_query="shawarma restaurants Riyadh",
    )

    assert first["public_evidence_context"]["as_of"] != second["public_evidence_context"]["as_of"]
    assert first["context_hash"] == second["context_hash"]


def test_market_context_preserves_complete_evidence_contract_when_pinecone_fails():
    product = LiveIntelligenceProductService(
        deepseek=FakeDeepSeek(),
        tavily=FakeTavily(),
        google=FakeGoogle(),
        pinecone=FailingPinecone(),
    )
    result = product.build_market_context(
        scope=tenant_scope(),
        query="shawarma market Riyadh",
        location_query="shawarma restaurants Riyadh",
    )
    context = result["public_evidence_context"]
    assert set(context) == {
        "contract_id",
        "status",
        "as_of",
        "evidence",
        "gaps",
        "permitted_uses",
        "claims_project_success",
        "claims_funding_acceptance",
        "source_of_truth",
        "snapshot_eligible",
        "requires_separate_assumption_admission_for_finance",
    }
    assert context["status"] == "not_ready"
    assert context["gaps"] == [
        {"record_id": "", "reason": "public_knowledge_unavailable"}
    ]
    assert context["requires_separate_assumption_admission_for_finance"] is True
    assert result["knowledge_hits"] == []


def test_narrative_requires_approved_context():
    try:
        service().create_reviewed_narrative(
            scope=tenant_scope(),
            request_id="request-1",
            prompt_template_id="template:market-explanation:v1",
            approved_context={"review_status": "review_required", "eligible_for_narrative": True, "evidence_refs": ["e:1"]},
            user_instruction="Explain the evidence",
        )
    except LiveIntelligenceProductError as exc:
        assert str(exc) == "approved_context_required"
    else:
        raise AssertionError("unapproved context must be rejected")


def test_reviewed_narrative_rejects_platform_preflight_scope():
    try:
        service().create_reviewed_narrative(
            scope=TrustedProviderScope.for_platform_preflight(),
            request_id="request-1",
            prompt_template_id="template:market-explanation:v1",
            approved_context={"review_status": "approved", "eligible_for_narrative": True, "evidence_refs": ["e:1"]},
            user_instruction="Explain the approved evidence",
        )
    except LiveIntelligenceProductError as exc:
        assert str(exc) == "authenticated_tenant_scope_required"
    else:
        raise AssertionError("platform preflight scope must not invoke DeepSeek")


def test_reviewed_narrative_preserves_provider_boundaries():
    product = service()
    scope = tenant_scope()
    result = product.create_reviewed_narrative(
        scope=scope,
        request_id="request-1",
        prompt_template_id="template:market-explanation:v1",
        approved_context={"review_status": "approved", "eligible_for_narrative": True, "evidence_refs": ["e:1"]},
        user_instruction="Explain the approved evidence",
    )
    assert result["contract_id"] == "live.intelligence.narrative.v1"
    assert product.deepseek.calls[0]["scope"] is scope
    assert result["controlled_numbers"] == []
    assert result["sovereign_verdict"] is None
    assert result["human_review_status"] == "required_pending"
    assert result["finance_mutated"] is False
    assert result["snapshot_mutated"] is False
