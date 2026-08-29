from __future__ import annotations

"""Version-pinned, fail-closed response contracts for live providers.

The validators intentionally accept only the response fields ASIE consumes.  A
successful validation does not approve provider content; callers must preserve
the review-required boundary.
"""

from math import isfinite
from typing import Any, Callable, Mapping
from urllib.parse import urlsplit


PROVIDER_RESPONSE_CONTRACT_VERSION = "fc20-03.provider-responses.v1"


class ProviderResponseContractError(RuntimeError):
    pass


def _fail(provider: str, operation: str, field: str) -> None:
    raise ProviderResponseContractError(
        f"provider_response_contract_violation:{provider}:{operation}:{field}"
    )


def _object(value: Any, provider: str, operation: str, field: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        _fail(provider, operation, field)
    return value


def _list(value: Any, provider: str, operation: str, field: str) -> list[Any]:
    if not isinstance(value, list):
        _fail(provider, operation, field)
    return value


def _text(
    value: Any,
    provider: str,
    operation: str,
    field: str,
    *,
    maximum: int = 100_000,
    allow_empty: bool = False,
) -> str:
    if not isinstance(value, str):
        _fail(provider, operation, field)
    if (not allow_empty and not value.strip()) or len(value) > maximum:
        _fail(provider, operation, field)
    return value


def _nonnegative_int(value: Any, provider: str, operation: str, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        _fail(provider, operation, field)
    return value


def _number(value: Any, provider: str, operation: str, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(float(value)):
        _fail(provider, operation, field)
    return float(value)


def _https_url(value: Any, provider: str, operation: str, field: str) -> str:
    text = _text(value, provider, operation, field, maximum=2_000)
    parsed = urlsplit(text)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        _fail(provider, operation, field)
    return text


def _usage_credits(payload: Mapping[str, Any], provider: str, operation: str) -> None:
    if "usage" not in payload:
        return
    usage = _object(payload["usage"], provider, operation, "usage")
    _number(usage.get("credits"), provider, operation, "usage.credits")


def validate_deepseek_narrative(payload: Any) -> Mapping[str, Any]:
    provider, operation = "deepseek", "create_narrative"
    body = _object(payload, provider, operation, "payload")
    _text(body.get("id"), provider, operation, "id", maximum=240)
    _text(body.get("model"), provider, operation, "model", maximum=160)
    if body.get("object") != "chat.completion":
        _fail(provider, operation, "object")
    choices = _list(body.get("choices"), provider, operation, "choices")
    if len(choices) != 1:
        _fail(provider, operation, "choices.count")
    choice = _object(choices[0], provider, operation, "choices[0]")
    _nonnegative_int(choice.get("index"), provider, operation, "choices[0].index")
    finish_reason = choice.get("finish_reason")
    if finish_reason not in {"stop", "length", "content_filter", "insufficient_system_resource"}:
        _fail(provider, operation, "choices[0].finish_reason")
    message = _object(choice.get("message"), provider, operation, "choices[0].message")
    if message.get("role") != "assistant":
        _fail(provider, operation, "choices[0].message.role")
    if message.get("tool_calls"):
        _fail(provider, operation, "choices[0].message.tool_calls")
    _text(message.get("content"), provider, operation, "choices[0].message.content", maximum=80_000)
    usage = _object(body.get("usage"), provider, operation, "usage")
    for field in ("completion_tokens", "prompt_tokens", "total_tokens"):
        _nonnegative_int(usage.get(field), provider, operation, f"usage.{field}")
    if usage["total_tokens"] < usage["completion_tokens"] + usage["prompt_tokens"]:
        _fail(provider, operation, "usage.total_tokens")
    return body


def _validate_tavily_result_items(
    payload: Mapping[str, Any], operation: str, *, content_field: str | None
) -> None:
    results = _list(payload.get("results"), "tavily", operation, "results")
    if len(results) > 100:
        _fail("tavily", operation, "results.count")
    for index, item in enumerate(results):
        if operation == "map":
            _https_url(item, "tavily", operation, f"results[{index}]")
            continue
        result = _object(item, "tavily", operation, f"results[{index}]")
        _https_url(result.get("url"), "tavily", operation, f"results[{index}].url")
        if content_field:
            _text(
                result.get(content_field),
                "tavily",
                operation,
                f"results[{index}].{content_field}",
                maximum=500_000,
            )
        if operation == "search":
            _text(result.get("title"), "tavily", operation, f"results[{index}].title", maximum=2_000)
            score = _number(result.get("score"), "tavily", operation, f"results[{index}].score")
            if score < 0 or score > 1:
                _fail("tavily", operation, f"results[{index}].score")


def validate_tavily(payload: Any, operation: str) -> Mapping[str, Any]:
    if operation not in {"search", "extract", "crawl", "map"}:
        _fail("tavily", operation, "operation")
    body = _object(payload, "tavily", operation, "payload")
    if operation in {"crawl", "map"}:
        _text(body.get("base_url"), "tavily", operation, "base_url", maximum=2_000)
    content_field = {"search": "content", "extract": "raw_content", "crawl": "raw_content", "map": None}[operation]
    _validate_tavily_result_items(body, operation, content_field=content_field)
    if operation == "extract":
        _list(body.get("failed_results"), "tavily", operation, "failed_results")
    _number(body.get("response_time"), "tavily", operation, "response_time")
    _text(body.get("request_id"), "tavily", operation, "request_id", maximum=240)
    _usage_credits(body, "tavily", operation)
    return body


def _validate_location(value: Any, provider: str, operation: str, field: str) -> None:
    location = _object(value, provider, operation, field)
    latitude = _number(location.get("latitude"), provider, operation, f"{field}.latitude")
    longitude = _number(location.get("longitude"), provider, operation, f"{field}.longitude")
    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        _fail(provider, operation, field)


def validate_google(payload: Any, operation: str) -> Mapping[str, Any]:
    provider = "google_maps_platform"
    body = _object(payload, provider, operation, "payload")
    if operation not in {"geocode_address", "reverse_geocode", "search_places_text"}:
        _fail(provider, operation, "operation")
    key = "places" if operation == "search_places_text" else "results"
    items = _list(body.get(key), provider, operation, key)
    if len(items) > (20 if operation == "search_places_text" else 10):
        _fail(provider, operation, f"{key}.count")
    for index, item in enumerate(items):
        record = _object(item, provider, operation, f"{key}[{index}]")
        id_field = "id" if operation == "search_places_text" else "placeId"
        _text(record.get(id_field), provider, operation, f"{key}[{index}].{id_field}", maximum=512)
        _validate_location(record.get("location"), provider, operation, f"{key}[{index}].location")
    return body


def validate_pinecone(payload: Any, operation: str, *, expected_index_name: str | None = None) -> Mapping[str, Any]:
    provider = "pinecone"
    body = _object(payload, provider, operation, "payload")
    if operation == "describe_index":
        name = _text(body.get("name"), provider, operation, "name", maximum=512)
        if expected_index_name is not None and name != expected_index_name:
            _fail(provider, operation, "name")
        host = _text(body.get("host"), provider, operation, "host", maximum=1_000)
        parsed = urlsplit(f"https://{host}")
        if not parsed.hostname or not parsed.hostname.endswith(".pinecone.io"):
            _fail(provider, operation, "host")
        status = _object(body.get("status"), provider, operation, "status")
        if not isinstance(status.get("ready"), bool):
            _fail(provider, operation, "status.ready")
        _text(status.get("state"), provider, operation, "status.state", maximum=80)
    elif operation in {"upsert_approved_text", "upsert_public_knowledge"}:
        if body.get("accepted") is not True:
            _fail(provider, operation, "accepted")
    elif operation in {"search_text", "search_public_knowledge"}:
        result = _object(body.get("result"), provider, operation, "result")
        hits = _list(result.get("hits"), provider, operation, "result.hits")
        for index, item in enumerate(hits):
            hit = _object(item, provider, operation, f"result.hits[{index}]")
            _text(hit.get("_id"), provider, operation, f"result.hits[{index}]._id", maximum=512)
            _number(hit.get("_score"), provider, operation, f"result.hits[{index}]._score")
            _object(hit.get("fields"), provider, operation, f"result.hits[{index}].fields")
    elif operation == "delete_public_knowledge":
        # Pinecone delete endpoints return an empty JSON object on success.
        if body:
            _fail(provider, operation, "payload")
    else:
        _fail(provider, operation, "operation")
    return body


VALIDATORS: Mapping[tuple[str, str], Callable[[Any], Mapping[str, Any]]] = {
    ("deepseek", "create_narrative"): validate_deepseek_narrative,
    ("tavily", "search"): lambda payload: validate_tavily(payload, "search"),
    ("tavily", "extract"): lambda payload: validate_tavily(payload, "extract"),
    ("tavily", "crawl"): lambda payload: validate_tavily(payload, "crawl"),
    ("tavily", "map"): lambda payload: validate_tavily(payload, "map"),
    ("google_maps_platform", "geocode_address"): lambda payload: validate_google(payload, "geocode_address"),
    ("google_maps_platform", "reverse_geocode"): lambda payload: validate_google(payload, "reverse_geocode"),
    ("google_maps_platform", "search_places_text"): lambda payload: validate_google(payload, "search_places_text"),
    ("pinecone", "describe_index"): lambda payload: validate_pinecone(payload, "describe_index"),
    ("pinecone", "upsert_approved_text"): lambda payload: validate_pinecone(payload, "upsert_approved_text"),
    ("pinecone", "upsert_public_knowledge"): lambda payload: validate_pinecone(
        payload, "upsert_public_knowledge"
    ),
    ("pinecone", "search_text"): lambda payload: validate_pinecone(payload, "search_text"),
    ("pinecone", "search_public_knowledge"): lambda payload: validate_pinecone(
        payload, "search_public_knowledge"
    ),
    ("pinecone", "delete_public_knowledge"): lambda payload: validate_pinecone(
        payload, "delete_public_knowledge"
    ),
}


def provider_response_contract_snapshot() -> dict[str, Any]:
    operations = sorted(VALIDATORS, key=lambda item: (item[0], item[1]))
    return {
        "contract_version": PROVIDER_RESPONSE_CONTRACT_VERSION,
        "operations": [
            {"provider_id": provider_id, "operation": operation, "fail_closed": True}
            for provider_id, operation in operations
        ],
        "operation_count": len(operations),
        "all_contracts_fail_closed": True,
        "content_auto_approved": False,
    }


def validate_provider_response(provider_id: str, operation: str, payload: Any) -> Mapping[str, Any]:
    validator = VALIDATORS.get((provider_id, operation))
    if validator is None:
        _fail(provider_id, operation, "contract_missing")
    return validator(payload)

