from __future__ import annotations

import pytest

from backend.provider_response_contracts import (
    ProviderResponseContractError,
    validate_deepseek_narrative,
    validate_google,
    validate_pinecone,
    validate_tavily,
)


def test_deepseek_contract_accepts_narrative_and_rejects_tool_calls() -> None:
    payload = {
        "id": "chat-1",
        "object": "chat.completion",
        "model": "deepseek-v4-flash",
        "choices": [{
            "index": 0,
            "finish_reason": "stop",
            "message": {"role": "assistant", "content": "reviewable narrative"},
        }],
        "usage": {"completion_tokens": 2, "prompt_tokens": 3, "total_tokens": 5},
    }
    assert validate_deepseek_narrative(payload) is payload
    payload["choices"][0]["message"]["tool_calls"] = [{"type": "function"}]
    with pytest.raises(ProviderResponseContractError, match="message.tool_calls"):
        validate_deepseek_narrative(payload)


@pytest.mark.parametrize(
    ("operation", "payload"),
    [
        ("search", {"results": [{"title": "x", "url": "https://example.com", "content": "x", "score": 0.5}], "response_time": 0.1, "request_id": "1"}),
        ("extract", {"results": [{"url": "https://example.com", "raw_content": "x"}], "failed_results": [], "response_time": 0.1, "request_id": "1"}),
        ("crawl", {"base_url": "example.com", "results": [{"url": "https://example.com", "raw_content": "x"}], "response_time": 0.1, "request_id": "1"}),
        ("map", {"base_url": "example.com", "results": ["https://example.com"], "response_time": 0.1, "request_id": "1"}),
    ],
)
def test_tavily_contracts_are_operation_specific(operation: str, payload: dict) -> None:
    assert validate_tavily(payload, operation) is payload
    payload["results"] = [{"url": "http://private.example", "content": "x"}]
    with pytest.raises(ProviderResponseContractError):
        validate_tavily(payload, operation)


def test_google_contract_separates_geocoding_reverse_geocoding_and_places_shapes() -> None:
    geocode_result = {
        "placeId": "g-1",
        "formattedAddress": "الرياض",
        "location": {"latitude": 24.7, "longitude": 46.7},
        "addressComponents": [{"longText": "الرياض", "shortText": "الرياض", "types": ["locality", "political"]}],
        "viewport": {"low": {"latitude": 24.6, "longitude": 46.6}, "high": {"latitude": 24.8, "longitude": 46.8}},
        "granularity": "ROOFTOP",
    }
    geocode = {"results": [geocode_result]}
    reverse_geocode = {"results": [{**geocode_result, "plusCode": {"globalCode": "7HMPQMGF+P4"}}]}
    places = {
        "places": [
            {
                "id": "p-1",
                "displayName": {"text": "منافس"},
                "formattedAddress": "الرياض",
                "location": {"latitude": 24.7, "longitude": 46.7},
                "primaryType": "restaurant",
                "businessStatus": "OPERATIONAL",
                "googleMapsUri": "https://www.google.com/maps/place/?q=place_id:p-1",
            }
        ]
    }
    preflight = {"results": [{"placeId": "g-1", "location": {"latitude": 24.7, "longitude": 46.7}}]}
    assert validate_google(preflight, "geocode_preflight") is preflight
    assert validate_google(geocode, "geocode_address") is geocode
    assert validate_google(reverse_geocode, "reverse_geocode") is reverse_geocode
    assert validate_google(places, "search_places_text") is places
    with pytest.raises(ProviderResponseContractError, match="places"):
        validate_google(geocode, "search_places_text")
    preflight["results"][0]["location"]["latitude"] = "not-a-number"
    with pytest.raises(ProviderResponseContractError, match="location.latitude"):
        validate_google(preflight, "geocode_preflight")
    geocode_result.pop("formattedAddress")
    with pytest.raises(ProviderResponseContractError, match="formattedAddress"):
        validate_google(geocode, "geocode_address")


def test_pinecone_contracts_validate_index_identity_and_search_hits() -> None:
    description = {
        "name": "vision2030-kb",
        "host": "vision2030-kb.svc.region.pinecone.io",
        "status": {"ready": True, "state": "Ready"},
    }
    assert validate_pinecone(description, "describe_index", expected_index_name="vision2030-kb") is description
    with pytest.raises(ProviderResponseContractError, match="describe_index:name"):
        validate_pinecone(description, "describe_index", expected_index_name="other")

    search = {"result": {"hits": [{"_id": "doc-1", "_score": 0.8, "fields": {"review_status": "approved"}}]}}
    assert validate_pinecone(search, "search_text") is search
    search["result"]["hits"][0].pop("fields")
    with pytest.raises(ProviderResponseContractError, match="fields"):
        validate_pinecone(search, "search_text")


def test_unknown_provider_operation_has_no_permissive_fallback() -> None:
    with pytest.raises(ProviderResponseContractError, match="operation"):
        validate_tavily({}, "research")

