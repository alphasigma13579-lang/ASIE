from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Mapping, Sequence

import pytest

from backend.live_provider_clients import (
    PineconeKnowledgeClient,
    ProviderConfigurationError,
    TavilyResearchClient,
    public_knowledge_namespace,
    tenant_project_namespace,
)
from backend.provider_security_control_plane import (
    ProviderRequestContext,
    ProviderSecurityError,
    TrustedProviderScope,
)
from backend.public_knowledge import PublicKnowledgeSourcePolicy


class RecordingTransport:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

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
                "provider_id": provider_id,
                "url": url,
                "method": method,
                "body": dict(body or {}),
                "security_context": security_context,
            }
        )
        if "/indexes/" in url:
            payload: dict[str, Any] = {
                "name": "vision2030-kb",
                "host": "vision2030-kb-test.svc.region.pinecone.io",
                "status": {"ready": True, "state": "Ready"},
            }
        elif url.endswith("/crawl"):
            payload = {
                "base_url": str((body or {}).get("url") or ""),
                "results": [
                    {
                        "url": "https://mof.gov.sa/en/generalservcies/open-data/dataset-a",
                        "raw_content": "Official public economic evidence " * 20,
                    }
                ],
                "response_time": 0.1,
                "request_id": "crawl-request-1",
                "usage": {"credits": 1},
            }
        elif url.endswith("/search"):
            payload = {"result": {"hits": []}}
        else:
            payload = {}
        return {"provider_id": provider_id, "payload": payload}

    def request_ndjson(
        self,
        *,
        provider_id: str,
        url: str,
        headers: Mapping[str, str],
        records: Sequence[Mapping[str, Any]],
        security_context: ProviderRequestContext,
    ) -> dict[str, Any]:
        self.calls.append(
            {
                "provider_id": provider_id,
                "url": url,
                "records": [dict(record) for record in records],
                "security_context": security_context,
            }
        )
        return {"provider_id": provider_id, "payload": {"accepted": True}}


def tenant_scope(organization_id: str = "org-a", project_id: str = "project-a") -> TrustedProviderScope:
    return TrustedProviderScope.for_tenant(
        principal=SimpleNamespace(
            user_id="user-a",
            session_id="session-a",
            organization_id=organization_id,
            role="analyst",
        ),
        project_id=project_id,
        project_organization_resolver=lambda _: organization_id,
    )


def public_record() -> dict[str, Any]:
    return {
        "_id": "public-mof-0001",
        "chunk_text": "Official public economic evidence " * 20,
        "source_id": "mof-open-data",
        "publisher": "Ministry of Finance",
        "authority": "saudi_official",
        "source_url": "https://mof.gov.sa/en/generalservcies/open-data/Pages/default.aspx",
        "license_id": "saudi-open-data-license-2.0",
        "license_ref": "docs/legal/third-party/saudi-open-data/README.md",
        "attribution": "Ministry of Finance",
        "sector": "all",
        "geography": "saudi_arabia",
        "language": "en",
        "published_at": "unknown",
        "retrieved_at": "2026-08-23T00:00:00Z",
        "content_sha256": "a" * 64,
        "version": 1,
        "freshness_days": 31,
        "fresh_until": "2026-09-23T00:00:00Z",
        "expires_at": "2026-10-23T00:00:00Z",
        "unit": "not_applicable",
        "confidence": 0.95,
        "evidence_ref": "public:mof-open-data:sha256:" + "a" * 64,
        "admission_status": "auto_admitted_official_open",
        "data_classification": "public",
        "chunk_index": 1,
        "chunk_count": 1,
    }


def public_registry() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "sources": [
            {
                "source_id": "mof-open-data",
                "publisher": "Ministry of Finance",
                "authority": "saudi_official",
                "url": "https://mof.gov.sa/en/generalservcies/open-data/Pages/default.aspx",
                "state": "enabled",
                "admission_mode": "official_open_auto",
                "license_id": "saudi-open-data-license-2.0",
                "license_ref": "docs/legal/third-party/saudi-open-data/README.md",
                "attribution": "Ministry of Finance",
                "classification": "public_open_data",
                "geographies": ["saudi_arabia"],
                "sectors": ["all"],
                "language": "en",
                "freshness_days": 31,
                "expiry_days": 62,
                "unit": "not_applicable",
                "confidence": 0.95,
                "allowed_paths": ["/en/generalservcies/open-data"],
                "allow_query_parameters": False,
                "acquisition_mode": "crawl",
                "crawl_max_depth": 2,
                "crawl_limit": 10,
            }
        ],
    }


def test_only_exact_platform_workload_can_be_issued() -> None:
    scope = TrustedProviderScope.for_platform_workload("public-knowledge-sync")
    assert scope.organization_id == "__platform__"
    assert scope.project_id == "public-knowledge-sync"
    assert scope.preflight is False

    with pytest.raises(ProviderSecurityError, match="platform_provider_workload_not_allowed"):
        TrustedProviderScope.for_platform_workload("arbitrary-admin-job")


def test_tenant_scope_rejects_reserved_platform_organization() -> None:
    principal = SimpleNamespace(
        user_id="user-a",
        session_id="session-a",
        organization_id="__platform__",
        role="analyst",
    )
    with pytest.raises(ProviderSecurityError, match="invalid_provider_context:organization_id"):
        TrustedProviderScope.for_tenant(
            principal=principal,
            project_id="project-a",
            project_organization_resolver=lambda _: "__platform__",
        )

    principal.organization_id = "org-a"
    with pytest.raises(
        ProviderSecurityError,
        match="invalid_provider_context:project_organization_id",
    ):
        TrustedProviderScope.for_tenant(
            principal=principal,
            project_id="project-a",
            project_organization_resolver=lambda _: "__platform__",
        )


def test_public_namespace_is_fixed_and_separate_from_tenant_namespaces() -> None:
    public = public_knowledge_namespace("asie")
    assert public == "asie-public-economic-knowledge-v1"
    assert public != tenant_project_namespace("org-a", "project-a", "asie")


def test_tenant_cannot_write_or_delete_public_knowledge() -> None:
    client = PineconeKnowledgeClient(transport=RecordingTransport(), api_key="secret")
    scope = tenant_scope()
    with pytest.raises(ProviderSecurityError, match="public_knowledge_platform_workload_required"):
        client.upsert_public_knowledge(scope=scope, records=[public_record()])
    with pytest.raises(ProviderSecurityError, match="public_knowledge_platform_workload_required"):
        client.delete_public_knowledge(scope=scope, record_ids=["public-mof-0001"])


def test_platform_write_uses_public_namespace_and_rejects_customer_fields() -> None:
    transport = RecordingTransport()
    client = PineconeKnowledgeClient(transport=transport, api_key="secret")
    scope = TrustedProviderScope.for_platform_workload("public-knowledge-sync")
    result = client.upsert_public_knowledge(scope=scope, records=[public_record()])
    assert result["namespace"] == "asie-public-economic-knowledge-v1"
    assert transport.calls[-1]["security_context"].organization_id == "__platform__"
    assert transport.calls[-1]["security_context"].operation == "upsert_public_knowledge"
    assert "organization_ref" not in transport.calls[-1]["records"][0]
    assert "project_ref" not in transport.calls[-1]["records"][0]

    forbidden = public_record()
    forbidden["organization_id"] = "org-a"
    with pytest.raises(ProviderConfigurationError, match="public_knowledge_customer_field_forbidden"):
        client.upsert_public_knowledge(scope=scope, records=[forbidden])


def test_platform_delete_uses_exact_body_and_validates_empty_response() -> None:
    transport = RecordingTransport()
    client = PineconeKnowledgeClient(transport=transport, api_key="secret")
    scope = TrustedProviderScope.for_platform_workload("public-knowledge-sync")

    by_id = client.delete_public_knowledge(
        scope=scope,
        record_ids=["public-mof-0001"],
    )
    assert by_id["deleted"] == 1
    assert by_id["delete_all"] is False
    assert transport.calls[-1]["url"].endswith("/vectors/delete")
    assert transport.calls[-1]["body"] == {
        "namespace": "asie-public-economic-knowledge-v1",
        "ids": ["public-mof-0001"],
    }

    all_records = client.delete_public_knowledge(scope=scope, delete_all=True)
    assert all_records["delete_all"] is True
    assert transport.calls[-1]["body"] == {
        "namespace": "asie-public-economic-knowledge-v1",
        "deleteAll": True,
    }

    with pytest.raises(ProviderConfigurationError, match="public_knowledge_delete_scope_invalid"):
        client.delete_public_knowledge(
            scope=scope,
            record_ids=["public-mof-0001"],
            delete_all=True,
        )


def test_two_tenants_read_same_public_namespace_but_keep_request_scopes() -> None:
    transport = RecordingTransport()
    client = PineconeKnowledgeClient(transport=transport, api_key="secret")
    first = client.search_public_knowledge(scope=tenant_scope("org-a", "project-a"), query="GDP")
    second = client.search_public_knowledge(scope=tenant_scope("org-b", "project-b"), query="GDP")
    assert first["namespace"] == second["namespace"] == "asie-public-economic-knowledge-v1"
    assert first["application_persists_query"] is False
    assert first["provider_retention_governed_externally"] is True
    searches = [call for call in transport.calls if call["url"].endswith("/search")]
    assert [call["security_context"].organization_id for call in searches] == ["org-a", "org-b"]
    assert all(
        call["security_context"].operation == "search_public_knowledge"
        for call in searches
    )
    assert all("query" not in str(call["security_context"]) for call in searches)


def test_preflight_scope_cannot_read_or_mutate_public_corpus() -> None:
    client = PineconeKnowledgeClient(transport=RecordingTransport(), api_key="secret")
    scope = TrustedProviderScope.for_platform_preflight()
    with pytest.raises(ProviderSecurityError, match="public_knowledge_tenant_scope_required"):
        client.search_public_knowledge(scope=scope, query="GDP")
    with pytest.raises(ProviderSecurityError, match="public_knowledge_platform_workload_required"):
        client.delete_public_knowledge(scope=scope, delete_all=True)


def test_public_crawl_uses_exact_platform_scope_and_admitted_graph_paths() -> None:
    transport = RecordingTransport()
    scope = TrustedProviderScope.for_platform_workload("public-knowledge-sync")
    client = TavilyResearchClient(
        transport=transport,
        api_key="secret",
        scope=scope,
        admission_policy=PublicKnowledgeSourcePolicy.from_registry(public_registry()),
    )
    result = client.crawl(
        source_id="mof-open-data",
        url="https://mof.gov.sa/en/generalservcies/open-data/Pages/default.aspx",
        instructions="Crawl official open data only.",
        max_depth=2,
        limit=10,
        select_paths=["/en/generalservcies/open-data"],
    )
    assert result["review_status"] == "auto_admitted_official_open"
    call = transport.calls[-1]
    assert call["security_context"].organization_id == "__platform__"
    assert call["body"]["select_domains"] == [r"^mof\.gov\.sa$"]
    assert call["body"]["select_paths"] == [
        r"^/en/generalservcies/open\-data(?:/.*)?$"
    ]
    assert call["body"]["allow_external"] is False
