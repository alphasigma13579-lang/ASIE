from __future__ import annotations

import json
from typing import Any

import pytest

from backend.live_provider_bounded_preflight import PROVIDERS, run, run_probe


class FakeTransport:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def request_json(self, *, provider_id: str, **kwargs: Any) -> dict[str, Any]:
        self.calls.append({"provider_id": provider_id, **kwargs})
        payloads = {
            "deepseek": {
                "id": "chatcmpl-preflight",
                "object": "chat.completion",
                "model": "deepseek-v4-flash",
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": "OK"},
                    }
                ],
                "usage": {"completion_tokens": 1, "prompt_tokens": 5, "total_tokens": 6},
            },
            "tavily": {
                "results": [
                    {
                        "url": "https://www.gov.sa/",
                        "title": "Saudi Arabia",
                        "content": "Official portal",
                        "score": 1.0,
                    }
                ],
                "response_time": 0.1,
                "request_id": "preflight-request",
                "usage": {"credits": 1},
            },
            "google_maps_platform": {
                "results": [
                    {
                        "placeId": "public-place-id",
                        "location": {"latitude": 24.711, "longitude": 46.674},
                    }
                ]
            },
            "pinecone": {
                "name": "vision2030-kb",
                "host": "vision2030-kb.svc.pinecone.io",
                "status": {"ready": True, "state": "Ready"},
                "embed": {
                    "model": "multilingual-e5-large",
                    "field_map": {"text": "chunk_text"},
                },
            },
        }
        return {
            "provider_id": provider_id,
            "status_code": 200,
            "response_bytes": 100,
            "response_contract_validated": True,
            "network_attempted": True,
            "payload": payloads[provider_id],
            "index_host_discovered": provider_id == "pinecone",
        }


@pytest.fixture(autouse=True)
def provider_secrets(monkeypatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "deepseek-secret-must-not-appear")
    monkeypatch.setenv("TAVILY_API_KEY", "tavily-secret-must-not-appear")
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "google-secret-must-not-appear")
    monkeypatch.setenv("PINECONE_API_KEY", "pinecone-secret-must-not-appear")


def test_offline_mode_never_authorizes_network() -> None:
    result = run("deepseek", False)
    assert result["status"] == "configuration_only"
    assert result["network_authorized"] is False
    assert result["provider_activation_authorized"] is False
    assert result["release_authorized"] is False
    assert result["secrets_exposed"] is False


def test_network_requires_separate_explicit_authorization(monkeypatch) -> None:
    monkeypatch.delenv("ASIE_LIVE_PREFLIGHT_AUTHORIZED", raising=False)
    result = run("deepseek", True)
    assert result["status"] == "blocked_live_preflight_not_authorized"
    assert result["network_authorized"] is False


@pytest.mark.parametrize("provider_id", PROVIDERS)
def test_fake_provider_probe_is_bounded_and_redacted(provider_id: str) -> None:
    result = run_probe(provider_id, FakeTransport())  # type: ignore[arg-type]
    serialized = json.dumps(result)
    assert result["status"] == "passed"
    assert result["secret_values_exposed"] is False
    assert "payload" not in result
    assert "must-not-appear" not in serialized
    if provider_id == "pinecone":
        assert result["write_attempted"] is False


def test_unknown_exception_message_is_redacted() -> None:
    class FailingTransport:
        def request_json(self, **kwargs: Any) -> dict[str, Any]:
            raise RuntimeError("Bearer secret-value-must-not-appear")

    result = run_probe("deepseek", FailingTransport())  # type: ignore[arg-type]
    assert result["status"] == "failed"
    assert result["error"] == "provider_preflight_failed_redacted"
    assert "secret-value-must-not-appear" not in json.dumps(result)



def test_google_preflight_uses_its_own_minimal_operation() -> None:
    transport = FakeTransport()
    result = run_probe("google_maps_platform", transport)  # type: ignore[arg-type]
    assert result["operation"] == "geocode_preflight"
    assert len(transport.calls) == 1
    call = transport.calls[0]
    assert call["security_context"].operation == "geocode_preflight"
    assert call["headers"]["X-Goog-FieldMask"] == "results.placeId,results.location"
