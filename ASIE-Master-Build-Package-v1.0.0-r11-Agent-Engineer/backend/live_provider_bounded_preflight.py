from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Any, Callable, Mapping
from urllib.parse import quote

from backend.external_acquisition import (
    ExternalAcquisitionError,
    ExternalAcquisitionPolicy,
    GovernedExternalAcquisitionGateway,
)
from backend.live_provider_clients import (
    GovernedProviderTransport,
    PineconeKnowledgeClient,
    ProviderConfigurationError,
)
from backend.provider_security_control_plane import (
    ProviderSecurityControlPlane,
    ProviderSecurityError,
    TrustedProviderScope,
)


PROVIDERS = ("deepseek", "tavily", "google_maps_platform", "pinecone")
_SAFE_ERROR_RE = re.compile(r"^[a-z0-9_.:-]{1,240}$")


def _required_secret(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ProviderConfigurationError(f"missing_provider_secret:{name}")
    return value


def _safe_error_code(exc: Exception) -> str:
    candidate = str(exc).strip()
    if _SAFE_ERROR_RE.fullmatch(candidate):
        return candidate
    return "provider_preflight_failed_redacted"


def _base_summary(provider_id: str, operation: str, response: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "provider_id": provider_id,
        "operation": operation,
        "status_code": response.get("status_code"),
        "response_bytes": response.get("response_bytes"),
        "response_contract_validated": response.get("response_contract_validated") is True,
        "network_attempted": response.get("network_attempted") is True,
        "payload_stored": False,
        "secret_values_exposed": False,
    }


def _probe_deepseek(transport: GovernedProviderTransport, scope: TrustedProviderScope) -> dict[str, Any]:
    model = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash").strip() or "deepseek-v4-flash"
    response = transport.request_json(
        provider_id="deepseek",
        url="https://api.deepseek.com/chat/completions",
        security_context=scope.request_context("create_narrative", cost_units=1),
        headers={"Authorization": f"Bearer {_required_secret('DEEPSEEK_API_KEY')}"},
        body={
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": "Connectivity preflight only. Reply with the single word OK.",
                },
                {"role": "user", "content": "OK"},
            ],
            "thinking": {"type": "disabled"},
            "max_tokens": 8,
            "stream": False,
        },
    )
    payload = response.get("payload") if isinstance(response.get("payload"), dict) else {}
    model_compatible = payload.get("model") == model
    return {
        **_base_summary("deepseek", "create_narrative", response),
        "status": "passed" if model_compatible else "failed",
        "model_compatible": model_compatible,
        "customer_data_sent": False,
        "maximum_output_tokens": 8,
    }


def _probe_tavily(transport: GovernedProviderTransport, scope: TrustedProviderScope) -> dict[str, Any]:
    headers = {"Authorization": f"Bearer {_required_secret('TAVILY_API_KEY')}"}
    project_id = os.getenv("TAVILY_PROJECT", "").strip()
    if project_id:
        headers["X-Project-ID"] = project_id
    response = transport.request_json(
        provider_id="tavily",
        url="https://api.tavily.com/search",
        security_context=scope.request_context("search", cost_units=1),
        headers=headers,
        body={
            "query": "Saudi Arabia official government portal",
            "search_depth": "basic",
            "topic": "general",
            "max_results": 1,
            "country": "saudi arabia",
            "include_answer": False,
            "include_raw_content": False,
            "include_images": False,
            "include_usage": True,
        },
    )
    payload = response.get("payload") if isinstance(response.get("payload"), dict) else {}
    results = payload.get("results") if isinstance(payload.get("results"), list) else []
    usage = payload.get("usage") if isinstance(payload.get("usage"), dict) else {}
    return {
        **_base_summary("tavily", "search", response),
        "status": "passed",
        "result_count": len(results),
        "usage_credits": usage.get("credits"),
        "content_persisted": False,
        "content_auto_approved": False,
    }


def _probe_google_maps(transport: GovernedProviderTransport, scope: TrustedProviderScope) -> dict[str, Any]:
    address = quote("Kingdom Centre, Riyadh, Saudi Arabia", safe="")
    response = transport.request_json(
        provider_id="google_maps_platform",
        method="GET",
        url=f"https://geocode.googleapis.com/v4/geocode/address/{address}",
        security_context=scope.request_context("geocode_address", cost_units=1),
        headers={
            "X-Goog-Api-Key": _required_secret("GOOGLE_MAPS_API_KEY"),
            "X-Goog-FieldMask": "results.placeId,results.location",
            "Accept-Language": "ar",
        },
        body=None,
    )
    payload = response.get("payload") if isinstance(response.get("payload"), dict) else {}
    results = payload.get("results") if isinstance(payload.get("results"), list) else []
    return {
        **_base_summary("google_maps_platform", "geocode_address", response),
        "status": "passed" if results else "failed",
        "result_count": len(results),
        "public_test_address_only": True,
        "location_persisted": False,
    }


def _probe_pinecone(transport: GovernedProviderTransport, scope: TrustedProviderScope) -> dict[str, Any]:
    response = PineconeKnowledgeClient.from_env(transport).describe_index(scope=scope)
    payload = response.get("payload") if isinstance(response.get("payload"), dict) else {}
    index_status = payload.get("status") if isinstance(payload.get("status"), dict) else {}
    embed = payload.get("embed") if isinstance(payload.get("embed"), dict) else {}
    field_map = embed.get("field_map") if isinstance(embed.get("field_map"), dict) else {}
    expected_model = os.getenv("PINECONE_EMBED_MODEL", "multilingual-e5-large").strip() or "multilingual-e5-large"
    compatible = bool(
        index_status.get("ready") is True
        and response.get("index_host_discovered") is True
        and embed.get("model") == expected_model
        and "chunk_text" in set(field_map.values())
    )
    return {
        **_base_summary("pinecone", "describe_index", response),
        "status": "passed" if compatible else "failed",
        "index_ready": index_status.get("ready") is True,
        "host_discovered": response.get("index_host_discovered") is True,
        "embed_model_compatible": embed.get("model") == expected_model,
        "chunk_text_compatible": "chunk_text" in set(field_map.values()),
        "write_attempted": False,
        "source_of_truth": False,
    }


_PROBES: Mapping[str, Callable[[GovernedProviderTransport, TrustedProviderScope], dict[str, Any]]] = {
    "deepseek": _probe_deepseek,
    "tavily": _probe_tavily,
    "google_maps_platform": _probe_google_maps,
    "pinecone": _probe_pinecone,
}


def run_probe(
    provider_id: str,
    transport: GovernedProviderTransport,
    scope: TrustedProviderScope | None = None,
) -> dict[str, Any]:
    if provider_id not in _PROBES:
        return {
            "provider_id": provider_id,
            "status": "failed",
            "error": "unknown_preflight_provider",
            "secret_values_exposed": False,
        }
    try:
        return _PROBES[provider_id](transport, scope or TrustedProviderScope.for_platform_preflight())
    except (ExternalAcquisitionError, ProviderConfigurationError, ProviderSecurityError) as exc:
        return {
            "provider_id": provider_id,
            "status": "failed",
            "error": _safe_error_code(exc),
            "exception_type": type(exc).__name__,
            "payload_stored": False,
            "secret_values_exposed": False,
        }
    except Exception as exc:  # Defensive CLI boundary: never emit an unknown provider message.
        return {
            "provider_id": provider_id,
            "status": "failed",
            "error": _safe_error_code(exc),
            "exception_type": type(exc).__name__,
            "payload_stored": False,
            "secret_values_exposed": False,
        }


def run(provider_id: str, network: bool) -> dict[str, Any]:
    result: dict[str, Any] = {
        "preflight_id": "fc20-03.bounded-live-provider-preflight.v1",
        "provider_id": provider_id,
        "network_requested": network,
        "network_authorized": False,
        "provider_activation_authorized": False,
        "release_authorized": False,
        "customer_data_sent": False,
        "payloads_stored": False,
        "secrets_exposed": False,
    }
    if provider_id not in PROVIDERS:
        return {**result, "status": "blocked_unknown_provider"}
    if not network:
        return {**result, "status": "configuration_only"}
    if os.getenv("ASIE_LIVE_PREFLIGHT_AUTHORIZED", "").strip().lower() != "true":
        return {**result, "status": "blocked_live_preflight_not_authorized"}

    try:
        policy = ExternalAcquisitionPolicy.from_env()
        if not policy.enabled:
            return {**result, "status": "blocked_external_network_disabled"}
        control_plane = ProviderSecurityControlPlane.from_env()
        if not control_plane.enabled:
            return {**result, "status": "blocked_provider_control_plane_disabled"}
        gateway = GovernedExternalAcquisitionGateway(policy)
        transport = GovernedProviderTransport(gateway, control_plane=control_plane)
        probe = run_probe(provider_id, transport)
    except (ExternalAcquisitionError, ProviderConfigurationError, ProviderSecurityError) as exc:
        return {
            **result,
            "status": "failed",
            "error": _safe_error_code(exc),
            "exception_type": type(exc).__name__,
        }

    return {
        **result,
        "status": "passed" if probe.get("status") == "passed" else "failed",
        "network_authorized": True,
        "probe": probe,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Bounded one-provider FC20-03 live preflight")
    parser.add_argument("--provider", choices=PROVIDERS, required=True)
    parser.add_argument("--network", action="store_true")
    args = parser.parse_args()
    result = run(args.provider, args.network)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] in {"configuration_only", "passed"} else 1


if __name__ == "__main__":
    sys.exit(main())

