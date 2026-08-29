from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Any


@dataclass(frozen=True)
class LiveProviderDefinition:
    provider_id: str
    role: str
    base_hosts: tuple[str, ...]
    secret_env_names: tuple[str, ...]
    optional_env_names: tuple[str, ...]
    default_model: str | None
    source_of_truth: bool
    controlled_numbers_owner: bool
    sovereign_verdict_owner: bool
    persistence_policy: str
    activation_gate: str
    allowed_operations: tuple[str, ...]
    preflight_operations: tuple[str, ...]
    contract_version: str
    default_timeout_seconds: float
    default_max_response_bytes: int
    default_requests_per_window: int
    default_cost_units_per_window: int
    default_max_get_attempts: int

    def status(self) -> dict[str, Any]:
        configured_secrets = [name for name in self.secret_env_names if bool(os.getenv(name, "").strip())]
        missing_secrets = [name for name in self.secret_env_names if name not in configured_secrets]
        return {
            "provider_id": self.provider_id,
            "role": self.role,
            "base_hosts": list(self.base_hosts),
            "configured": not missing_secrets,
            "configured_secret_names": configured_secrets,
            "missing_secret_names": missing_secrets,
            "optional_env_names": list(self.optional_env_names),
            "default_model": self.default_model,
            "source_of_truth": self.source_of_truth,
            "controlled_numbers_owner": self.controlled_numbers_owner,
            "sovereign_verdict_owner": self.sovereign_verdict_owner,
            "persistence_policy": self.persistence_policy,
            "activation_gate": self.activation_gate,
            "allowed_operations": list(self.allowed_operations),
            "preflight_operations": list(self.preflight_operations),
            "contract_version": self.contract_version,
            "default_timeout_seconds": self.default_timeout_seconds,
            "default_max_response_bytes": self.default_max_response_bytes,
            "default_requests_per_window": self.default_requests_per_window,
            "default_cost_units_per_window": self.default_cost_units_per_window,
            "default_max_get_attempts": self.default_max_get_attempts,
            "secret_values_exposed": False,
        }


LIVE_PROVIDER_CATALOG: tuple[LiveProviderDefinition, ...] = (
    LiveProviderDefinition(
        provider_id="deepseek",
        role="governed_narrative_and_reasoning_provider",
        base_hosts=("api.deepseek.com",),
        secret_env_names=("DEEPSEEK_API_KEY",),
        optional_env_names=("DEEPSEEK_MODEL",),
        default_model="deepseek-v4-flash",
        source_of_truth=False,
        controlled_numbers_owner=False,
        sovereign_verdict_owner=False,
        persistence_policy="store_template_hash_context_refs_validation_and_review_only",
        activation_gate="AIA_IACR_PROVIDER_ACTIVATION_AND_HUMAN_REVIEW_REQUIRED",
        allowed_operations=("create_narrative",),
        preflight_operations=("create_narrative",),
        contract_version="asie-deepseek-chat-contract-v1",
        default_timeout_seconds=20.0,
        default_max_response_bytes=1_048_576,
        default_requests_per_window=20,
        default_cost_units_per_window=80,
        default_max_get_attempts=1,
    ),
    LiveProviderDefinition(
        provider_id="tavily",
        role="web_search_extract_map_and_crawl_provider",
        base_hosts=("api.tavily.com",),
        secret_env_names=("TAVILY_API_KEY",),
        optional_env_names=("TAVILY_PROJECT", "TAVILY_SEARCH_DEPTH"),
        default_model=None,
        source_of_truth=False,
        controlled_numbers_owner=False,
        sovereign_verdict_owner=False,
        persistence_policy="retain_discovered_source_url_hash_timestamp_and_review_state",
        activation_gate="SOURCE_TERMS_ALLOWLIST_AND_EVIDENCE_REVIEW_REQUIRED",
        allowed_operations=("search", "extract", "crawl", "map"),
        preflight_operations=("search",),
        contract_version="asie-tavily-research-contract-v1",
        default_timeout_seconds=20.0,
        default_max_response_bytes=2_097_152,
        default_requests_per_window=30,
        default_cost_units_per_window=120,
        default_max_get_attempts=1,
    ),
    LiveProviderDefinition(
        provider_id="google_maps_platform",
        role="location_maps_geocoding_and_places_ux_provider",
        base_hosts=(
            "geocode.googleapis.com",
            "places.googleapis.com",
            "maps.googleapis.com",
        ),
        secret_env_names=("GOOGLE_MAPS_API_KEY",),
        optional_env_names=("GOOGLE_MAP_ID", "GOOGLE_MAPS_REGION", "GOOGLE_MAPS_LANGUAGE"),
        default_model=None,
        source_of_truth=False,
        controlled_numbers_owner=False,
        sovereign_verdict_owner=False,
        persistence_policy="location_identity_only_until_google_terms_review_approves_other_storage",
        activation_gate="GOOGLE_TERMS_KEY_RESTRICTIONS_AND_LOCATION_CONSENT_REQUIRED",
        allowed_operations=("geocode_address", "geocode_preflight", "search_places_text"),
        preflight_operations=("geocode_preflight",),
        contract_version="asie-google-maps-contract-v1",
        default_timeout_seconds=10.0,
        default_max_response_bytes=1_048_576,
        default_requests_per_window=60,
        default_cost_units_per_window=120,
        default_max_get_attempts=2,
    ),
    LiveProviderDefinition(
        provider_id="pinecone",
        role="knowledge_vector_storage_and_semantic_retrieval",
        base_hosts=("api.pinecone.io", "*.pinecone.io"),
        secret_env_names=("PINECONE_API_KEY",),
        optional_env_names=(
            "PINECONE_INDEX",
            "PINECONE_API_VERSION",
            "PINECONE_CLOUD",
            "PINECONE_REGION",
            "PINECONE_EMBED_MODEL",
            "PINECONE_NAMESPACE_PREFIX",
        ),
        default_model="multilingual-e5-large",
        source_of_truth=False,
        controlled_numbers_owner=False,
        sovereign_verdict_owner=False,
        persistence_policy="tenant_approved_chunks_or_policy_admitted_public_chunks_in_separate_namespaces",
        activation_gate="TENANT_NAMESPACE_RETENTION_DELETION_AND_DATA_CLASSIFICATION_REVIEW_REQUIRED",
        allowed_operations=(
            "describe_index",
            "upsert_approved_text",
            "upsert_public_knowledge",
            "search_text",
            "search_public_knowledge",
            "delete_public_knowledge",
        ),
        preflight_operations=("describe_index",),
        contract_version="asie-pinecone-data-contract-v1",
        default_timeout_seconds=12.0,
        default_max_response_bytes=2_097_152,
        default_requests_per_window=40,
        default_cost_units_per_window=200,
        default_max_get_attempts=2,
    ),
)


def provider_catalog_snapshot() -> dict[str, Any]:
    providers = [provider.status() for provider in LIVE_PROVIDER_CATALOG]
    return {
        "catalog_id": "asie-live-provider-catalog-v2",
        "providers": providers,
        "provider_count": len(providers),
        "configured_provider_count": sum(1 for provider in providers if provider["configured"]),
        "required_external_hosts": sorted({host for provider in LIVE_PROVIDER_CATALOG for host in provider.base_hosts}),
        "secrets_stored": False,
        "ai_owns_numbers": False,
        "ai_owns_verdict": False,
        "pinecone_is_source_of_truth": False,
        "tavily_results_require_source_review": True,
        "google_places_persistence_requires_terms_review": True,
    }
