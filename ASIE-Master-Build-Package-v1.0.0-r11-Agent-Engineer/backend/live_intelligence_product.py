from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from typing import Any, Mapping, Protocol, Sequence
from urllib.parse import urlparse

from backend.live_provider_clients import (
    DeepSeekNarrativeClient,
    GoogleLocationClient,
    PineconeKnowledgeClient,
    TavilyResearchClient,
)
from backend.provider_security_control_plane import TrustedProviderScope
from backend.public_knowledge import (
    build_feasibility_evidence_context,
    build_unavailable_feasibility_evidence_context,
)


class LiveIntelligenceProductError(RuntimeError):
    pass


class ProviderBundle(Protocol):
    deepseek: DeepSeekNarrativeClient
    tavily: TavilyResearchClient
    google: GoogleLocationClient
    pinecone: PineconeKnowledgeClient


def _present(name: str) -> bool:
    return bool(os.getenv(name, "").strip())


def _safe_error(exc: Exception) -> dict[str, str]:
    return {"error_type": type(exc).__name__, "reason": str(exc)[:240]}


def _sha256_json(payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _stable_context_hash_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    stable = dict(payload)
    evidence_context = stable.get("public_evidence_context")
    if isinstance(evidence_context, Mapping):
        stable["public_evidence_context"] = {
            key: value for key, value in evidence_context.items() if key != "as_of"
        }
    return stable


def _admitted_tavily_domains(search: Mapping[str, Any]) -> frozenset[str]:
    """Read only the server-derived discovery domains returned with a search."""
    admission = search.get("source_admission")
    raw_domains = admission.get("include_domains") if isinstance(admission, Mapping) else ()
    if not isinstance(raw_domains, Sequence) or isinstance(raw_domains, (str, bytes)):
        return frozenset()
    return frozenset(
        domain
        for value in raw_domains
        if isinstance(value, str)
        for domain in [value.strip().casefold().rstrip(".")]
        if domain
    )


def _is_admitted_tavily_result_url(value: Any, domains: frozenset[str]) -> bool:
    if not isinstance(value, str) or not domains:
        return False
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.hostname) and parsed.hostname.casefold().rstrip(".") in domains


def provider_status_snapshot() -> dict[str, Any]:
    enabled = os.getenv("ASIE_ALLOW_EXTERNAL_FETCH", "false").strip().lower() in {"1", "true", "yes", "on"}
    providers = {
        "deepseek": {"secret_present": _present("DEEPSEEK_API_KEY"), "capability": "narrative_only"},
        "tavily": {"secret_present": _present("TAVILY_API_KEY"), "capability": "search_extract_crawl"},
        "google_maps_platform": {"secret_present": _present("GOOGLE_MAPS_API_KEY"), "capability": "location_places"},
        "pinecone": {"secret_present": _present("PINECONE_API_KEY"), "capability": "knowledge_retrieval"},
    }
    for row in providers.values():
        row["status"] = "disabled" if not enabled else ("configured" if row["secret_present"] else "missing_secret")
        row["secret_value_exposed"] = False
    return {
        "contract_id": "live.intelligence.provider.status.v1",
        "external_fetch_enabled": enabled,
        "providers": providers,
        "controlled_numbers_allowed": False,
        "finance_mutated": False,
        "snapshot_mutated": False,
    }


@dataclass
class LiveIntelligenceProductService:
    deepseek: Any
    tavily: Any
    google: Any
    pinecone: Any

    def preflight(self) -> dict[str, Any]:
        status = provider_status_snapshot()
        checks: dict[str, Any] = {}
        if not status["external_fetch_enabled"]:
            return {
                "contract_id": "live.intelligence.preflight.v1",
                "status": "disabled",
                "checks": status["providers"],
                "secrets_exposed": False,
            }

        for provider_id, operation in {
            "pinecone": lambda: self.pinecone.describe_index(),
            "tavily": lambda: self.tavily.search(query="Saudi Vision 2030 official portal", include_domains=["vision2030.gov.sa"], max_results=1),
            "google_maps_platform": lambda: self.google.preflight_geocode(
                "الرياض، المملكة العربية السعودية",
                scope=TrustedProviderScope.for_platform_preflight(),
            ),
        }.items():
            try:
                response = operation()
                checks[provider_id] = {
                    "status": "live",
                    "network_attempted": bool(response.get("network_attempted", True)),
                    "review_status": response.get("review_status", "review_required"),
                }
            except Exception as exc:
                checks[provider_id] = {"status": "failed", **_safe_error(exc)}

        checks["deepseek"] = {
            "status": "configured" if _present("DEEPSEEK_API_KEY") else "missing_secret",
            "network_attempted": False,
            "reason": "narrative provider is exercised only with an approved prompt template",
        }
        overall = "ready" if all(row["status"] in {"live", "configured"} for row in checks.values()) else "degraded"
        return {
            "contract_id": "live.intelligence.preflight.v1",
            "status": overall,
            "checks": checks,
            "secrets_exposed": False,
            "finance_mutated": False,
            "snapshot_mutated": False,
        }

    def build_market_context(
        self,
        *,
        scope: TrustedProviderScope,
        query: str,
        location_query: str,
        sector_id: str = "general",
        geography: str = "saudi_arabia",
        latitude: float | None = None,
        longitude: float | None = None,
    ) -> dict[str, Any]:
        if scope.preflight or scope.organization_id == "__platform__":
            raise LiveIntelligenceProductError("authenticated_tenant_scope_required")
        scope.request_context("search_public_knowledge")
        if not query.strip() or not location_query.strip():
            raise LiveIntelligenceProductError("query_and_location_required")

        source_candidates: list[dict[str, Any]] = []
        failures: list[dict[str, Any]] = []

        try:
            search = self.tavily.search(
                query=query,
                sector_id=sector_id,
                geography=geography,
                max_results=8,
                search_depth="advanced",
            )
            payload = search.get("payload") if isinstance(search, Mapping) else None
            results = payload.get("results", []) if isinstance(payload, Mapping) else []
            admitted_domains = _admitted_tavily_domains(search) if isinstance(search, Mapping) else frozenset()
            for index, row in enumerate(results[:8], 1):
                if not isinstance(row, Mapping):
                    continue
                if not _is_admitted_tavily_result_url(row.get("url"), admitted_domains):
                    failures.append({"provider": "tavily", "error_type": "SourceAdmissionError", "reason": "result_domain_not_admitted"})
                    continue
                source_candidates.append(
                    {
                        "candidate_id": f"tavily:{index}",
                        "provider": "tavily",
                        "title": str(row.get("title") or "")[:240],
                        "url": str(row.get("url") or "")[:2000],
                        "summary": str(row.get("content") or "")[:1200],
                        "review_status": "review_required",
                        "eligible_for_controlled_assumptions": False,
                    }
                )
        except Exception as exc:
            failures.append({"provider": "tavily", **_safe_error(exc)})

        places: list[dict[str, Any]] = []
        try:
            place_response = self.google.search_places_text(
                scope=scope,
                text_query=location_query,
                latitude=latitude,
                longitude=longitude,
                page_size=10,
            )
            payload = place_response.get("payload") if isinstance(place_response, Mapping) else None
            rows = payload.get("places", []) if isinstance(payload, Mapping) else []
            for row in rows[:10]:
                if not isinstance(row, Mapping):
                    continue
                places.append(
                    {
                        "place_id": row.get("id"),
                        "display_name": row.get("displayName"),
                        "formatted_address": row.get("formattedAddress"),
                        "location": row.get("location"),
                        "primary_type": row.get("primaryType"),
                        "business_status": row.get("businessStatus"),
                        "google_maps_uri": row.get("googleMapsUri"),
                        "persistence_policy": "place_id_and_project_location_only_until_terms_review",
                    }
                )
        except Exception as exc:
            failures.append({"provider": "google_maps_platform", **_safe_error(exc)})

        public_evidence_context = build_unavailable_feasibility_evidence_context(
            "public_knowledge_unavailable"
        )
        try:
            response = self.pinecone.search_public_knowledge(
                scope=scope,
                query=query,
                top_k=8,
            )
            public_evidence_context = build_feasibility_evidence_context(response)
        except Exception as exc:
            failures.append({"provider": "pinecone", **_safe_error(exc)})

        knowledge_hits = [
            {**dict(evidence), "review_status": "review_required"}
            for evidence in public_evidence_context.get("evidence") or []
            if isinstance(evidence, Mapping)
        ]
        product_status = "review_required" if source_candidates or places or knowledge_hits else "failed"
        result = {
            "contract_id": "live.intelligence.context.v1",
            "project_id": scope.project_id,
            "organization_id": scope.organization_id,
            "status": product_status,
            "source_candidates": source_candidates,
            "places": places,
            "knowledge_hits": knowledge_hits,
            "public_evidence_context": public_evidence_context,
            "failures": failures,
            "human_review_required": True,
            "eligible_for_controlled_assumptions": False,
            "controlled_numbers": [],
            "finance_mutated": False,
            "snapshot_mutated": False,
        }
        result["context_hash"] = _sha256_json(_stable_context_hash_payload(result))
        return result

    def create_reviewed_narrative(
        self,
        *,
        scope: TrustedProviderScope,
        request_id: str,
        prompt_template_id: str,
        approved_context: Mapping[str, Any],
        user_instruction: str,
    ) -> dict[str, Any]:
        if scope.preflight or scope.organization_id == "__platform__":
            raise LiveIntelligenceProductError("authenticated_tenant_scope_required")
        scope.request_context("create_narrative")
        if approved_context.get("review_status") != "approved":
            raise LiveIntelligenceProductError("approved_context_required")
        if approved_context.get("eligible_for_narrative") is not True:
            raise LiveIntelligenceProductError("context_not_eligible_for_narrative")
        context_hash = _sha256_json(approved_context)
        response = self.deepseek.create_narrative(
            scope=scope,
            request_id=request_id,
            prompt_template_id=prompt_template_id,
            prompt_hash=context_hash,
            context_refs=[str(value) for value in approved_context.get("evidence_refs", [])],
            messages=[
                {"role": "system", "content": "Explain approved evidence. Do not create financial numbers or sovereign verdicts."},
                {"role": "user", "content": user_instruction},
            ],
            thinking=True,
            max_tokens=1800,
        )
        return {
            **response,
            "contract_id": "live.intelligence.narrative.v1",
            "approved_context_hash": context_hash,
            "human_review_status": "required_pending",
            "finance_mutated": False,
            "snapshot_mutated": False,
        }
