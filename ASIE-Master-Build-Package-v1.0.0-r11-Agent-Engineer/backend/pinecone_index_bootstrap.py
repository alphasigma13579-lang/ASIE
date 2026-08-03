from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
import re
import sys
from typing import Any, Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request

from backend.external_acquisition import (
    ExternalAcquisitionError,
    ExternalAcquisitionPolicy,
    GovernedExternalAcquisitionGateway,
)


PINECONE_CONTROL_PLANE = "https://api.pinecone.io"
PINECONE_API_VERSION = "2026-04"
TARGET_INDEX = "vision2030-kb-e5"
EMBED_MODEL = "multilingual-e5-large"
SOURCE_TEXT_FIELD = "chunk_text"
_INDEX_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,43}[a-z0-9])?$")
_REGION_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,62}$")


class PineconeIndexBootstrapError(RuntimeError):
    """Fail-closed, non-secret Pinecone bootstrap error."""


def _index_name(value: str, *, field: str) -> str:
    normalized = value.strip()
    if not _INDEX_RE.fullmatch(normalized):
        raise PineconeIndexBootstrapError(f"invalid_index_name:{field}")
    return normalized


def _required_secret(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise PineconeIndexBootstrapError(f"missing_provider_secret:{name}")
    return value


def _compatible(payload: Mapping[str, Any]) -> bool:
    embed = payload.get("embed") if isinstance(payload.get("embed"), dict) else {}
    field_map = embed.get("field_map") if isinstance(embed.get("field_map"), dict) else {}
    return (
        embed.get("model") == EMBED_MODEL
        and SOURCE_TEXT_FIELD in {str(value) for value in field_map.values()}
    )


def _safe_serverless_location(payload: Mapping[str, Any]) -> tuple[str, str]:
    spec = payload.get("spec") if isinstance(payload.get("spec"), dict) else {}
    serverless = spec.get("serverless") if isinstance(spec.get("serverless"), dict) else {}
    cloud = str(serverless.get("cloud") or "").strip().lower()
    region = str(serverless.get("region") or "").strip().lower()
    if cloud not in {"aws", "gcp", "azure"}:
        raise PineconeIndexBootstrapError("source_index_serverless_cloud_required")
    if not _REGION_RE.fullmatch(region):
        raise PineconeIndexBootstrapError("source_index_serverless_region_required")
    return cloud, region


def creation_payload(*, name: str, cloud: str, region: str) -> dict[str, Any]:
    return {
        "name": _index_name(name, field="target"),
        "cloud": cloud,
        "region": region,
        "embed": {
            "model": EMBED_MODEL,
            "metric": "cosine",
            "field_map": {"text": SOURCE_TEXT_FIELD},
            "write_parameters": {"input_type": "passage", "truncate": "END"},
            "read_parameters": {"input_type": "query", "truncate": "END"},
        },
        "deletion_protection": "enabled",
        "tags": {"purpose": "fc20-03c-provider-preflight"},
    }


Describe = Callable[[str], tuple[int, Mapping[str, Any]]]
Create = Callable[[Mapping[str, Any]], tuple[int, Mapping[str, Any]]]


def prepare_index(
    *,
    source_index: str,
    target_index: str,
    describe: Describe,
    create: Create,
) -> dict[str, Any]:
    source_index = _index_name(source_index, field="source")
    target_index = _index_name(target_index, field="target")
    if target_index != TARGET_INDEX:
        raise PineconeIndexBootstrapError("unexpected_target_index")

    target_status, target = describe(target_index)
    if target_status == 200:
        if not _compatible(target):
            raise PineconeIndexBootstrapError("target_index_exists_incompatible")
        return {
            "status": "existing_compatible",
            "target_index": target_index,
            "index_ready": target.get("status", {}).get("ready") is True
            if isinstance(target.get("status"), dict)
            else False,
            "embed_model_compatible": True,
            "chunk_text_compatible": True,
            "deletion_protection_enabled": target.get("deletion_protection") == "enabled",
            "write_attempted": False,
        }
    if target_status != 404:
        raise PineconeIndexBootstrapError(f"target_describe_http_status:{target_status}")

    source_status, source = describe(source_index)
    if source_status == 404:
        raise PineconeIndexBootstrapError("source_index_not_found")
    if source_status != 200:
        raise PineconeIndexBootstrapError(f"source_describe_http_status:{source_status}")
    cloud, region = _safe_serverless_location(source)
    payload = creation_payload(name=target_index, cloud=cloud, region=region)
    create_status, created = create(payload)
    if create_status not in {200, 201, 202}:
        raise PineconeIndexBootstrapError(f"create_index_http_status:{create_status}")
    if created.get("name") != target_index:
        raise PineconeIndexBootstrapError("created_index_name_mismatch")
    if not _compatible(created):
        raise PineconeIndexBootstrapError("created_index_embedding_incompatible")
    if created.get("deletion_protection") != "enabled":
        raise PineconeIndexBootstrapError("created_index_deletion_protection_missing")
    status = created.get("status") if isinstance(created.get("status"), dict) else {}
    return {
        "status": "created",
        "source_index": source_index,
        "target_index": target_index,
        "cloud": cloud,
        "region": region,
        "index_ready": status.get("ready") is True,
        "embed_model_compatible": True,
        "chunk_text_compatible": True,
        "deletion_protection_enabled": True,
        "write_attempted": True,
    }


@dataclass
class PineconeControlPlaneClient:
    gateway: GovernedExternalAcquisitionGateway
    api_key: str

    def _request(
        self,
        *,
        method: str,
        path: str,
        body: Mapping[str, Any] | None = None,
        allow_not_found: bool = False,
    ) -> tuple[int, Mapping[str, Any]]:
        url = f"{PINECONE_CONTROL_PLANE}{path}"
        parsed = self.gateway._validate_url(url)
        self.gateway.rate_limiter.wait(parsed.hostname or "")
        encoded = None if body is None else json.dumps(body, separators=(",", ":")).encode("utf-8")
        request = Request(
            url,
            data=encoded,
            method=method,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Api-Key": self.api_key,
                "X-Pinecone-Api-Version": PINECONE_API_VERSION,
                "User-Agent": self.gateway.policy.user_agent,
            },
        )
        try:
            with self.gateway.opener.open(
                request,
                timeout=self.gateway.policy.timeout_seconds,
            ) as response:
                status = int(getattr(response, "status", 200))
                raw = response.read(self.gateway.policy.max_response_bytes + 1)
        except HTTPError as exc:
            if allow_not_found and exc.code == 404:
                return 404, {}
            raise PineconeIndexBootstrapError(f"pinecone_http_status:{exc.code}") from exc
        except (URLError, TimeoutError, OSError, ValueError) as exc:
            raise PineconeIndexBootstrapError(
                f"pinecone_transport_error:{type(exc).__name__}"
            ) from exc
        if len(raw) > self.gateway.policy.max_response_bytes:
            raise PineconeIndexBootstrapError("pinecone_response_too_large")
        try:
            payload = json.loads(raw.decode("utf-8")) if raw else {}
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise PineconeIndexBootstrapError("invalid_pinecone_json") from exc
        if not isinstance(payload, dict):
            raise PineconeIndexBootstrapError("invalid_pinecone_response_shape")
        return status, payload

    def describe(self, index_name: str) -> tuple[int, Mapping[str, Any]]:
        return self._request(
            method="GET",
            path=f"/indexes/{quote(_index_name(index_name, field='describe'), safe='')}",
            allow_not_found=True,
        )

    def create(self, payload: Mapping[str, Any]) -> tuple[int, Mapping[str, Any]]:
        return self._request(
            method="POST",
            path="/indexes/create-for-model",
            body=payload,
        )


def run(*, network: bool) -> dict[str, Any]:
    result: dict[str, Any] = {
        "bootstrap_id": "fc20-03c.pinecone-integrated-index-bootstrap.v1",
        "network_requested": network,
        "network_authorized": False,
        "customer_data_sent": False,
        "vectors_written": False,
        "payloads_stored": False,
        "secret_values_exposed": False,
        "provider_activation_authorized": False,
        "release_authorized": False,
    }
    if not network:
        return {**result, "status": "configuration_only"}
    if os.getenv("ASIE_PINECONE_INDEX_BOOTSTRAP_AUTHORIZED", "").strip().lower() != "true":
        return {**result, "status": "blocked_bootstrap_not_authorized"}

    try:
        policy = ExternalAcquisitionPolicy.from_env()
        if not policy.enabled:
            return {**result, "status": "blocked_external_network_disabled"}
        if set(policy.allowed_hosts) != {"api.pinecone.io"}:
            return {**result, "status": "blocked_bootstrap_host_policy"}
        gateway = GovernedExternalAcquisitionGateway(policy)
        client = PineconeControlPlaneClient(gateway, _required_secret("PINECONE_API_KEY"))
        prepared = prepare_index(
            source_index=os.getenv("PINECONE_SOURCE_INDEX", "vision2030-kb"),
            target_index=os.getenv("PINECONE_TARGET_INDEX", TARGET_INDEX),
            describe=client.describe,
            create=client.create,
        )
    except (PineconeIndexBootstrapError, ExternalAcquisitionError) as exc:
        reason = str(exc)
        if not re.fullmatch(r"[a-z0-9_.:-]{1,240}", reason):
            reason = "pinecone_index_bootstrap_failed_redacted"
        return {
            **result,
            "status": "failed",
            "network_authorized": True,
            "error": reason,
            "exception_type": type(exc).__name__,
        }

    return {
        **result,
        "status": "passed",
        "network_authorized": True,
        "bootstrap": prepared,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Create one protected FC20-03C Pinecone integrated index")
    parser.add_argument("--network", action="store_true")
    args = parser.parse_args()
    result = run(network=args.network)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] in {"configuration_only", "passed"} else 1


if __name__ == "__main__":
    sys.exit(main())
