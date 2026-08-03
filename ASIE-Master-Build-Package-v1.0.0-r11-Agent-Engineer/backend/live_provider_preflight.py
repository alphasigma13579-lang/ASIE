from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

from backend.external_acquisition import ExternalAcquisitionPolicy, GovernedExternalAcquisitionGateway
from backend.live_provider_catalog import provider_catalog_snapshot
from backend.provider_security_control_plane import (
    ProviderSecurityControlPlane,
    ProviderSecurityError,
)
from backend.provider_response_contracts import provider_response_contract_snapshot
from backend.live_provider_clients import (
    GovernedProviderTransport,
    PineconeKnowledgeClient,
    ProviderConfigurationError,
)


def _safe_index_summary(description: dict[str, Any]) -> dict[str, Any]:
    payload = description.get("payload")
    if not isinstance(payload, dict):
        return {"status": "invalid_description"}
    embed = payload.get("embed") if isinstance(payload.get("embed"), dict) else {}
    field_map = embed.get("field_map") if isinstance(embed, dict) and isinstance(embed.get("field_map"), dict) else {}
    index_status = payload.get("status") if isinstance(payload.get("status"), dict) else {}
    expected_model = os.getenv("PINECONE_EMBED_MODEL", "multilingual-e5-large").strip() or "multilingual-e5-large"
    actual_model = embed.get("model") if isinstance(embed, dict) else None
    return {
        "name": payload.get("name"),
        "ready": index_status.get("ready"),
        "state": index_status.get("state"),
        "metric": payload.get("metric"),
        "dimension": payload.get("dimension"),
        "vector_type": payload.get("vector_type"),
        "deletion_protection": payload.get("deletion_protection"),
        "embed_model": actual_model,
        "expected_embed_model": expected_model,
        "embed_model_compatible": actual_model == expected_model,
        "field_map": field_map,
        "chunk_text_compatible": "chunk_text" in set(field_map.values()),
        "host_discovered": bool(payload.get("host")),
        "source_of_truth": False,
    }


def run(network: bool) -> dict[str, Any]:
    policy = ExternalAcquisitionPolicy.from_env()
    control_error: str | None = None
    try:
        control_plane = ProviderSecurityControlPlane.from_env()
        control_status = control_plane.status()
    except ProviderSecurityError as exc:
        control_plane = None
        control_error = str(exc)
        control_status = {
            "control_plane_id": "asie-provider-security-control-plane-v1",
            "enabled": False,
            "status": "invalid_configuration",
            "reason": control_error,
            "secret_values_exposed": False,
            "network_authorized": False,
        }
    result: dict[str, Any] = {
        "preflight_id": "asie-live-provider-preflight-v2",
        "network_requested": network,
        "network_policy": policy.snapshot(),
        "provider_catalog": provider_catalog_snapshot(),
        "response_contracts": provider_response_contract_snapshot(),
        "live_checks": {
            "deepseek": {"status": "not_checked", "operation": "create_narrative"},
            "tavily": {"status": "not_checked", "operation": "search"},
            "google_maps_platform": {"status": "not_checked", "operation": "geocode_address"},
            "pinecone": {"status": "not_checked", "operation": "describe_index"},
        },
        "provider_security": control_status,
        "pinecone": {
            "index_name": os.getenv("PINECONE_INDEX", "vision2030-kb"),
            "status": "not_checked",
            "source_of_truth": False,
        },
        "secrets_exposed": False,
    }
    if control_error:
        result["status"] = "blocked_provider_control_configuration"
        result["error"] = control_error
        return result
    if not network:
        result["status"] = "configuration_only"
        return result
    if not policy.enabled:
        result["status"] = "blocked_external_network_disabled"
        return result
    if control_plane is None or not control_plane.enabled:
        result["status"] = "blocked_provider_control_plane_disabled"
        return result
    try:
        gateway = GovernedExternalAcquisitionGateway(policy)
        transport = GovernedProviderTransport(gateway, control_plane=control_plane)
        pinecone = PineconeKnowledgeClient.from_env(transport)
        description = pinecone.describe_index()
        summary = _safe_index_summary(description)
        compatible = bool(
            summary.get("ready")
            and summary.get("host_discovered")
            and summary.get("embed_model_compatible")
            and summary.get("chunk_text_compatible")
        )
        result["pinecone"] = {"status": "checked", **summary, "compatible": compatible}
        result["live_checks"]["pinecone"] = {
            "status": "passed" if compatible else "failed",
            "operation": "describe_index",
        }
        if compatible:
            result["status"] = "passed"
        elif not summary.get("ready"):
            result["status"] = "pinecone_not_ready"
        else:
            result["status"] = "pinecone_index_incompatible"
    except ProviderConfigurationError as exc:
        result["status"] = "missing_configuration"
        result["error"] = str(exc)
    except Exception as exc:  # CLI boundary: provider clients never include secret values in errors.
        result["status"] = "failed"
        result["error"] = str(exc)
        result["exception_type"] = type(exc).__name__
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="ASIE live-provider configuration preflight")
    parser.add_argument("--network", action="store_true", help="perform governed Pinecone Describe Index request")
    args = parser.parse_args()
    result = run(args.network)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] in {"configuration_only", "passed"} else 1


if __name__ == "__main__":
    sys.exit(main())

