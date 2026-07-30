from __future__ import annotations

from typing import Any, Mapping, Sequence

import pytest

from backend.live_provider_clients import TavilyResearchClient
from backend.source_registry import normalize_source_review
from backend.tavily_source_admission import SourceAdmissionError, TavilySourceAdmissionPolicy


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
        security_context: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.calls.append({
            "provider_id": provider_id,
            "url": url,
            "body": dict(body or {}),
            "security_context": dict(security_context or {}),
        })
        return {
            "provider_id": provider_id,
            "payload": {"results": []},
            "network_attempted": True,
            "review_status": "review_required",
            "eligible_for_controlled_assumptions": False,
        }


def reviewed_source(
    *,
    source_id: str = "MONSHAAT_OPEN_DATA",
    state: str = "enabled",
    organization_id: str = "__platform__",
    project_id: str = "*",
) -> dict[str, Any]:
    return {
        "source_id": source_id,
        "publisher": "Approved publisher",
        "route": "official_open_dataset_or_api",
        "state": state,
        "url": "https://monshaat.gov.sa/open-data",
        "terms_url": "https://monshaat.gov.sa/terms",
        "terms_hash": "a" * 64,
        "license_snapshot_ref": "license:monshaat:v1",
        "attribution": "Approved publisher open data",
        "classification": "public",
        "pdpl_check": "passed",
        "nca_check": "passed",
        "lawful_purpose": "saudi_market_research",
        "reviewer": "platform-reviewer",
        "reviewer_decision": "approved",
        "organization_id": organization_id,
        "project_id": project_id,
        "discovery_allowed": True,
        "discovery_sectors": ["sme"],
        "discovery_geographies": ["saudi_arabia"],
        "allowed_paths": ["/open-data"],
    }


def client_for(records: Sequence[Mapping[str, Any]], *, organization_id: str = "org-a") -> tuple[TavilyResearchClient, RecordingTransport]:
    transport = RecordingTransport()
    policy = TavilySourceAdmissionPolicy.from_records(
        organization_id=organization_id,
        project_id="project-a",
        records=records,
    )
    return TavilyResearchClient(
        transport=transport,
        api_key="secret",
        admission_policy=policy,
    ), transport


def test_reviewed_registry_metadata_drives_server_admission_without_enabling_network() -> None:
    payload = reviewed_source()
    normalized = normalize_source_review(payload)
    persisted_shape = {
        key: value
        for key, value in normalized.items()
        if key != "notes_json"
    }
    import json
    persisted_shape["notes"] = json.loads(normalized["notes_json"])
    client, transport = client_for([persisted_shape])
    result = client.search(
        query="Saudi SME market",
        sector_id="sme",
        geography="saudi_arabia",
    )
    assert result["source_admission"]["include_domains"] == ["monshaat.gov.sa"]
    assert result["eligible_for_controlled_assumptions"] is False
    assert len(transport.calls) == 1


def test_unknown_source_and_arbitrary_seed_url_are_denied_before_transport() -> None:
    client, transport = client_for([reviewed_source()])
    with pytest.raises(SourceAdmissionError, match="unknown_source_denied"):
        client.crawl(
            source_id="UNKNOWN",
            url="https://evil.example/crawl-me",
            instructions="crawl",
        )
    assert transport.calls == []


@pytest.mark.parametrize("state", ["candidate", "reference_only"])
def test_candidate_and_reference_only_sources_cannot_extract_or_crawl(state: str) -> None:
    source = reviewed_source(source_id="MOSTAQL_PROJECTS", state=state)
    source["url"] = "https://mostaql.com/projects"
    source["allowed_paths"] = ["/projects"]
    client, transport = client_for([source])
    with pytest.raises(SourceAdmissionError, match="source_not_enabled_for_content_access"):
        client.crawl(
            source_id="MOSTAQL_PROJECTS",
            url="https://mostaql.com/projects",
            instructions="crawl",
        )
    assert transport.calls == []


def test_client_include_domains_cannot_widen_server_sector_geography_policy() -> None:
    client, transport = client_for([reviewed_source()])
    with pytest.raises(SourceAdmissionError, match="client_discovery_scope_widening_denied"):
        client.search(
            query="Saudi SME market",
            sector_id="sme",
            geography="saudi_arabia",
            include_domains=["monshaat.gov.sa", "evil.example"],
        )
    assert transport.calls == []


def test_cross_tenant_source_review_is_denied_before_transport() -> None:
    client, transport = client_for(
        [reviewed_source(organization_id="org-b", project_id="project-b")],
        organization_id="org-a",
    )
    with pytest.raises(SourceAdmissionError, match="cross_tenant_source_denied"):
        client.extract(
            urls=["https://monshaat.gov.sa/open-data/indicators"],
            source_ids={"https://monshaat.gov.sa/open-data/indicators": "MONSHAAT_OPEN_DATA"},
        )
    assert transport.calls == []


def test_unadmitted_path_and_query_parameters_are_denied() -> None:
    client, transport = client_for([reviewed_source()])
    with pytest.raises(SourceAdmissionError, match="source_path_not_admitted"):
        client.crawl(
            source_id="MONSHAAT_OPEN_DATA",
            url="https://monshaat.gov.sa/private",
            instructions="crawl",
        )
    with pytest.raises(SourceAdmissionError, match="source_query_parameters_not_admitted"):
        client.crawl(
            source_id="MONSHAAT_OPEN_DATA",
            url="https://monshaat.gov.sa/open-data?redirect=https://evil.example",
            instructions="crawl",
        )
    assert transport.calls == []


def test_discovery_is_server_bound_and_always_review_required() -> None:
    client, transport = client_for([reviewed_source()])
    result = client.search(
        query="Saudi SME market",
        sector_id="sme",
        geography="saudi_arabia",
    )
    assert transport.calls[0]["body"]["include_domains"] == ["monshaat.gov.sa"]
    assert result["source_admission"]["source_ids"] == ["MONSHAAT_OPEN_DATA"]
    assert result["review_status"] == "review_required"
    assert result["eligible_for_controlled_assumptions"] is False


def test_client_crawl_path_cannot_widen_server_allowed_roots() -> None:
    client, transport = client_for([reviewed_source()])
    with pytest.raises(SourceAdmissionError, match="client_graph_scope_widening_denied"):
        client.crawl(
            source_id="MONSHAAT_OPEN_DATA",
            url="https://monshaat.gov.sa/open-data",
            instructions="crawl",
            select_paths=["/private"],
        )
    assert transport.calls == []


def test_crawl_uses_server_derived_domain_and_path_filters_by_default() -> None:
    client, transport = client_for([reviewed_source()])
    client.crawl(
        source_id="MONSHAAT_OPEN_DATA",
        url="https://monshaat.gov.sa/open-data",
        instructions="crawl",
    )
    body = transport.calls[0]["body"]
    assert body["select_domains"] == [r"^monshaat\.gov\.sa$"]
    assert body["select_paths"] == [r"^/open\-data(?:/.*)?$"]
    assert body["exclude_paths"] == []
    assert body["allow_external"] is False


def test_client_can_only_narrow_crawl_to_literal_subpaths() -> None:
    client, transport = client_for([reviewed_source()])
    client.crawl(
        source_id="MONSHAAT_OPEN_DATA",
        url="https://monshaat.gov.sa/open-data",
        instructions="crawl",
        select_paths=["/open-data/reports"],
        exclude_paths=["/open-data/reports/archive"],
    )
    body = transport.calls[0]["body"]
    assert body["select_paths"] == [r"^/open\-data/reports(?:/.*)?$"]
    assert body["exclude_paths"] == [r"^/open\-data/reports/archive(?:/.*)?$"]


def test_map_uses_the_same_server_owned_graph_scope() -> None:
    client, transport = client_for([reviewed_source()])
    client.map_site(
        source_id="MONSHAAT_OPEN_DATA",
        url="https://monshaat.gov.sa/open-data",
        instructions="map",
    )
    body = transport.calls[0]["body"]
    assert body["select_domains"] == [r"^monshaat\.gov\.sa$"]
    assert body["select_paths"] == [r"^/open\-data(?:/.*)?$"]
    assert body["exclude_paths"] == []
    assert body["allow_external"] is False


@pytest.mark.parametrize(
    ("url", "reason"),
    [
        ("https://127.0.0.1/open-data", "source_ip_literal_denied"),
        ("https://localhost/open-data", "source_private_host_denied"),
        ("https://registry.internal/open-data", "source_private_host_denied"),
    ],
)
def test_internal_or_ip_source_hosts_are_denied_before_transport(url: str, reason: str) -> None:
    source = reviewed_source()
    source["url"] = url
    client, transport = client_for([source])
    with pytest.raises(SourceAdmissionError, match=reason):
        client.crawl(
            source_id="MONSHAAT_OPEN_DATA",
            url=url,
            instructions="crawl",
        )
    assert transport.calls == []


@pytest.mark.parametrize(
    "url",
    [
        "https://monshaat.gov.sa/open-data/%2e%2e/private",
        "https://monshaat.gov.sa/open-data/%5cprivate",
        "https://monshaat.gov.sa/open-data/%252e%252e/private",
    ],
)
def test_ambiguous_or_encoded_path_escape_is_denied_before_transport(url: str) -> None:
    client, transport = client_for([reviewed_source()])
    with pytest.raises(SourceAdmissionError, match="source_path_not_admitted"):
        client.crawl(
            source_id="MONSHAAT_OPEN_DATA",
            url=url,
            instructions="crawl",
        )
    assert transport.calls == []


def test_client_exclude_domains_cannot_escape_server_discovery_scope() -> None:
    client, transport = client_for([reviewed_source()])
    with pytest.raises(SourceAdmissionError, match="client_discovery_scope_widening_denied"):
        client.search(
            query="Saudi SME market",
            sector_id="sme",
            geography="saudi_arabia",
            exclude_domains=["evil.example"],
        )
    assert transport.calls == []
