from __future__ import annotations

from backend.live_provider_preflight import run


def test_preflight_configuration_mode_exposes_no_secrets(monkeypatch) -> None:
    monkeypatch.delenv("PINECONE_API_KEY", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_MAPS_API_KEY", raising=False)
    monkeypatch.delenv("ASIE_ALLOW_EXTERNAL_FETCH", raising=False)
    result = run(False)
    assert result["status"] == "configuration_only"
    assert result["pinecone"]["index_name"] == "vision2030-kb"
    assert result["secrets_exposed"] is False
    assert result["network_policy"]["enabled"] is False
    assert result["provider_security"]["enabled"] is False
    assert result["provider_security"]["network_authorized"] is False
    assert result["response_contracts"]["operation_count"] == 10
    assert result["response_contracts"]["all_contracts_fail_closed"] is True
    assert result["response_contracts"]["content_auto_approved"] is False
    assert set(result["live_checks"]) == {
        "deepseek",
        "tavily",
        "google_maps_platform",
        "pinecone",
    }
    assert all(item["status"] == "not_checked" for item in result["live_checks"].values())


def test_network_preflight_fails_closed_when_external_fetch_is_disabled(monkeypatch) -> None:
    monkeypatch.setenv("ASIE_ALLOW_EXTERNAL_FETCH", "false")
    monkeypatch.setenv("ASIE_EXTERNAL_ALLOWED_HOSTS", "api.pinecone.io,*.pinecone.io")
    result = run(True)
    assert result["status"] == "blocked_external_network_disabled"
    assert result["secrets_exposed"] is False


def test_network_preflight_fails_before_transport_when_control_plane_is_disabled(monkeypatch) -> None:
    monkeypatch.setenv("ASIE_ALLOW_EXTERNAL_FETCH", "true")
    monkeypatch.setenv("ASIE_EXTERNAL_ALLOWED_HOSTS", "api.pinecone.io,*.pinecone.io")
    monkeypatch.setenv("ASIE_PROVIDER_CONTROL_PLANE_ENABLED", "false")
    result = run(True)
    assert result["status"] == "blocked_provider_control_plane_disabled"
    assert result["secrets_exposed"] is False
    assert result["provider_security"]["enabled"] is False


def test_preflight_rejects_enabled_control_plane_without_durable_store(monkeypatch) -> None:
    monkeypatch.setenv("ASIE_PROVIDER_CONTROL_PLANE_ENABLED", "true")
    monkeypatch.delenv("ASIE_PROVIDER_CONTROL_DB_PATH", raising=False)
    result = run(False)
    assert result["status"] == "blocked_provider_control_configuration"
    assert result["error"] == "provider_control_store_required"
    assert result["provider_security"]["secret_values_exposed"] is False

