from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
import os
import re
import time
from typing import Any, Mapping, Protocol, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import Request

from backend.external_acquisition import (
    ExternalAcquisitionError,
    GovernedExternalAcquisitionGateway,
    _utc_now,
)
from backend.provider_security_control_plane import (
    ProviderAdmission,
    ProviderRequestContext,
    ProviderSecurityControlPlane,
    ProviderSecurityError,
    TrustedProviderScope,
)
from backend.provider_response_contracts import (
    PROVIDER_RESPONSE_CONTRACT_VERSION,
    ProviderResponseContractError,
    validate_pinecone,
    validate_provider_response,
)
from backend.tavily_source_admission import TavilySourceAdmissionPolicy


class ProviderConfigurationError(RuntimeError):
    pass


DEEPSEEK_ALLOWED_MODELS = frozenset({"deepseek-v4-flash", "deepseek-v4-pro"})


class ProviderCancellationSignal(Protocol):
    def is_set(self) -> bool: ...


class ProviderTransport(Protocol):
    def request_json(
        self,
        *,
        provider_id: str,
        url: str,
        method: str = "POST",
        headers: Mapping[str, str] | None = None,
        body: Mapping[str, Any] | None = None,
        expected_statuses: Sequence[int] = (200,),
        security_context: ProviderRequestContext | None = None,
        cancellation_signal: ProviderCancellationSignal | None = None,
    ) -> dict[str, Any]: ...

    def request_ndjson(
        self,
        *,
        provider_id: str,
        url: str,
        headers: Mapping[str, str],
        records: Sequence[Mapping[str, Any]],
        expected_statuses: Sequence[int] = (200, 201),
        security_context: ProviderRequestContext | None = None,
        cancellation_signal: ProviderCancellationSignal | None = None,
    ) -> dict[str, Any]: ...


class GovernedProviderTransport:
    """Provider transport admitted by both provider and network control planes.

    Request bodies and authorization headers are never written to the audit sink.
    Provider payloads are returned for immediate validation and review, but are
    not persisted by this transport.
    """

    def __init__(
        self,
        gateway: GovernedExternalAcquisitionGateway | None = None,
        *,
        control_plane: ProviderSecurityControlPlane | None = None,
        sleep: Any = time.sleep,
    ) -> None:
        self.gateway = gateway or GovernedExternalAcquisitionGateway()
        self.control_plane = control_plane or ProviderSecurityControlPlane.from_env()
        self.sleep = sleep

    def request_json(
        self,
        *,
        provider_id: str,
        url: str,
        method: str = "POST",
        headers: Mapping[str, str] | None = None,
        body: Mapping[str, Any] | None = None,
        expected_statuses: Sequence[int] = (200,),
        security_context: ProviderRequestContext | None = None,
        cancellation_signal: ProviderCancellationSignal | None = None,
    ) -> dict[str, Any]:
        encoded = None if body is None else json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        return self._request(
            provider_id=provider_id,
            url=url,
            method=method,
            headers=headers,
            data=encoded,
            content_type="application/json",
            expected_statuses=expected_statuses,
            parse_json=True,
            security_context=security_context,
            cancellation_signal=cancellation_signal,
        )

    def request_ndjson(
        self,
        *,
        provider_id: str,
        url: str,
        headers: Mapping[str, str],
        records: Sequence[Mapping[str, Any]],
        expected_statuses: Sequence[int] = (200, 201),
        security_context: ProviderRequestContext | None = None,
        cancellation_signal: ProviderCancellationSignal | None = None,
    ) -> dict[str, Any]:
        payload = "\n".join(json.dumps(record, ensure_ascii=False, separators=(",", ":")) for record in records).encode("utf-8")
        return self._request(
            provider_id=provider_id,
            url=url,
            method="POST",
            headers=headers,
            data=payload,
            content_type="application/x-ndjson",
            expected_statuses=expected_statuses,
            parse_json=False,
            security_context=security_context,
            cancellation_signal=cancellation_signal,
        )

    def _request(
        self,
        *,
        provider_id: str,
        url: str,
        method: str,
        headers: Mapping[str, str] | None,
        data: bytes | None,
        content_type: str,
        expected_statuses: Sequence[int],
        parse_json: bool,
        security_context: ProviderRequestContext | None,
        cancellation_signal: ProviderCancellationSignal | None,
    ) -> dict[str, Any]:
        self._raise_if_cancelled(cancellation_signal)
        if not provider_id.strip():
            raise ExternalAcquisitionError("provider_id_required")
        try:
            admission = self.control_plane.authorize(
                provider_id=provider_id,
                url=url,
                context=security_context,
            )
        except ProviderSecurityError as exc:
            host = ""
            try:
                host = urlsplit(url).hostname or ""
            except ValueError:
                pass
            self._audit(provider_id, host, "rejected", str(exc))
            raise ExternalAcquisitionError(str(exc)) from exc

        request_headers = {
            "Accept": "application/json",
            "Content-Type": content_type,
            "User-Agent": self.gateway.policy.user_agent,
        }
        request_headers.update({str(key): str(value) for key, value in (headers or {}).items()})
        request = Request(url, data=data, headers=request_headers, method=method.upper())
        attempts = admission.max_get_attempts if method.upper() == "GET" else 1
        parsed = None
        response_body = b""
        final_url = url
        status = 0

        for attempt in range(1, attempts + 1):
            try:
                self._raise_if_cancelled(cancellation_signal)
                parsed = self.gateway._validate_url(url)
                self.gateway.rate_limiter.wait(parsed.hostname or "")
                self._raise_if_cancelled(cancellation_signal)
                with self.gateway.opener.open(
                    request,
                    timeout=min(self.gateway.policy.timeout_seconds, admission.timeout_seconds),
                ) as response:
                    final_url = response.geturl()
                    self.gateway._validate_url(final_url)
                    status = int(getattr(response, "status", 200))
                    if status not in set(expected_statuses):
                        raise ExternalAcquisitionError(f"provider_http_status:{status}")
                    response_limit = min(
                        self.gateway.policy.max_response_bytes,
                        admission.max_response_bytes,
                    )
                    response_body = response.read(response_limit + 1)
                    if len(response_body) > response_limit:
                        raise ExternalAcquisitionError("provider_response_too_large")
                self._raise_if_cancelled(cancellation_signal)
                break
            except HTTPError as exc:
                transient = exc.code in {408, 425, 429, 500, 502, 503, 504}
                if transient and attempt < attempts:
                    self._raise_if_cancelled(cancellation_signal)
                    self._audit(provider_id, urlsplit(url).hostname or "", "retry", f"provider_http_status:{exc.code}", admission)
                    self.sleep(admission.retry_delay_seconds * attempt)
                    continue
                self.control_plane.record_failure(admission, transient=transient)
                reason = f"provider_http_status:{exc.code}"
                self._audit(provider_id, urlsplit(url).hostname or "", "failed", reason, admission)
                raise ExternalAcquisitionError(reason) from exc
            except (URLError, TimeoutError, OSError) as exc:
                if attempt < attempts:
                    self._raise_if_cancelled(cancellation_signal)
                    self._audit(provider_id, urlsplit(url).hostname or "", "retry", f"provider_transport_error:{type(exc).__name__}", admission)
                    self.sleep(admission.retry_delay_seconds * attempt)
                    continue
                self.control_plane.record_failure(admission, transient=True)
                reason = f"provider_transport_error:{type(exc).__name__}"
                self._audit(provider_id, urlsplit(url).hostname or "", "failed", reason, admission)
                raise ExternalAcquisitionError(reason) from exc
            except ExternalAcquisitionError as exc:
                self.control_plane.record_failure(admission, transient=False)
                host = parsed.hostname if parsed is not None else (urlsplit(url).hostname or "")
                self._audit(provider_id, host, "rejected", str(exc), admission)
                raise
            except ValueError as exc:
                self.control_plane.record_failure(admission, transient=False)
                reason = "provider_transport_error:ValueError"
                self._audit(provider_id, urlsplit(url).hostname or "", "failed", reason, admission)
                raise ExternalAcquisitionError(reason) from exc

        digest = hashlib.sha256(response_body).hexdigest()
        if not response_body:
            payload: Any = {}
        elif parse_json:
            try:
                payload = json.loads(response_body.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                self.control_plane.record_failure(admission, transient=False)
                self._audit(provider_id, parsed.hostname if parsed else "", "failed", "invalid_provider_json", admission)
                raise ExternalAcquisitionError("invalid_provider_json") from exc
        else:
            payload = {"accepted": True}

        try:
            validate_provider_response(provider_id, admission.operation, payload)
        except ProviderResponseContractError as exc:
            self.control_plane.record_failure(admission, transient=False)
            reason = str(exc)
            self._audit(provider_id, parsed.hostname if parsed else "", "failed", reason, admission)
            raise ExternalAcquisitionError(reason) from exc

        self.control_plane.record_success(admission)
        metadata = {
            **admission.audit_metadata(),
            "host": parsed.hostname if parsed else "",
            "method": method.upper(),
            "status_code": status,
            "response_bytes": len(response_body),
            "sha256": digest,
            "attempt_count": attempt,
        }
        self.gateway.audit_sink.record(
            event_type="live_provider_request",
            outcome="success",
            metadata=metadata,
        )
        return {
            "provider_id": provider_id,
            "provider_operation": admission.operation,
            "provider_contract_version": admission.contract_version,
            "response_contract_version": PROVIDER_RESPONSE_CONTRACT_VERSION,
            "response_contract_validated": True,
            "tenant_scope_ref": admission.scope_ref,
            "url": final_url,
            "status_code": status,
            "response_bytes": len(response_body),
            "sha256": digest,
            "payload": payload,
            "retrieved_at": _utc_now(),
            "network_attempted": True,
            "review_status": "review_required",
            "eligible_for_controlled_assumptions": False,
        }

    @staticmethod
    def _raise_if_cancelled(signal: ProviderCancellationSignal | None) -> None:
        if signal is not None and signal.is_set():
            raise ExternalAcquisitionError("provider_request_cancelled")

    def _audit(
        self,
        provider_id: str,
        host: str,
        outcome: str,
        reason: str,
        admission: ProviderAdmission | None = None,
    ) -> None:
        metadata: dict[str, Any] = {
            "provider_id": provider_id,
            "host": host,
            "reason": reason,
        }
        if admission is not None:
            metadata.update(admission.audit_metadata())
        self.gateway.audit_sink.record(
            event_type="live_provider_request",
            outcome=outcome,
            metadata=metadata,
        )

def _required_secret(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ProviderConfigurationError(f"missing_provider_secret:{name}")
    return value


def _bounded_text(value: Any, *, field: str, minimum: int = 1, maximum: int = 20_000) -> str:
    text = str(value or "").strip()
    if len(text) < minimum or len(text) > maximum:
        raise ProviderConfigurationError(f"invalid_text_length:{field}")
    return text


def _namespace_part(value: str) -> str:
    digest = hashlib.sha256(value.strip().encode("utf-8")).hexdigest()[:16]
    return digest


def tenant_project_namespace(organization_id: str, project_id: str, prefix: str = "asie") -> str:
    if not organization_id.strip() or not project_id.strip():
        raise ProviderConfigurationError("organization_and_project_required")
    safe_prefix = re.sub(r"[^a-z0-9-]", "-", prefix.lower()).strip("-") or "asie"
    return f"{safe_prefix}-o-{_namespace_part(organization_id)}-p-{_namespace_part(project_id)}"


def public_knowledge_namespace(prefix: str = "asie") -> str:
    safe_prefix = re.sub(r"[^a-z0-9-]", "-", prefix.lower()).strip("-") or "asie"
    return f"{safe_prefix}-public-economic-knowledge-v1"


def _provider_security_context(
    scope: TrustedProviderScope,
    operation: str,
    *,
    cost_units: int = 1,
    preflight: bool = False,
) -> ProviderRequestContext:
    if preflight != scope.preflight:
        raise ProviderSecurityError("provider_scope_preflight_mismatch")
    return scope.request_context(operation, cost_units=cost_units)


def _validated_response(
    response: dict[str, Any],
    provider_id: str,
    operation: str,
) -> dict[str, Any]:
    try:
        validate_provider_response(provider_id, operation, response.get("payload"))
    except ProviderResponseContractError as exc:
        raise ExternalAcquisitionError(str(exc)) from exc
    return {
        **response,
        "response_contract_version": PROVIDER_RESPONSE_CONTRACT_VERSION,
        "response_contract_validated": True,
    }


@dataclass
class DeepSeekNarrativeClient:
    transport: ProviderTransport
    api_key: str
    model: str = "deepseek-v4-flash"

    def __post_init__(self) -> None:
        if self.model not in DEEPSEEK_ALLOWED_MODELS:
            raise ProviderConfigurationError("deepseek_model_not_allowlisted")

    @classmethod
    def from_env(cls, transport: ProviderTransport | None = None) -> "DeepSeekNarrativeClient":
        return cls(
            transport=transport or GovernedProviderTransport(),
            api_key=_required_secret("DEEPSEEK_API_KEY"),
            model=os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash").strip() or "deepseek-v4-flash",
        )

    def create_narrative(
        self,
        *,
        scope: TrustedProviderScope,
        request_id: str,
        prompt_template_id: str,
        prompt_hash: str,
        context_refs: Sequence[str],
        messages: Sequence[Mapping[str, str]],
        thinking: bool = True,
        max_tokens: int = 2_000,
    ) -> dict[str, Any]:
        _bounded_text(request_id, field="request_id", maximum=160)
        _bounded_text(prompt_template_id, field="prompt_template_id", maximum=160)
        if not re.fullmatch(r"[a-fA-F0-9]{64}", prompt_hash):
            raise ProviderConfigurationError("prompt_hash_must_be_sha256")
        if not context_refs or len(context_refs) > 100:
            raise ProviderConfigurationError("invalid_context_refs")
        if not messages or len(messages) > 40:
            raise ProviderConfigurationError("invalid_message_count")
        safe_messages: list[dict[str, str]] = []
        for message in messages:
            role = str(message.get("role") or "")
            if role not in {"system", "user", "assistant"}:
                raise ProviderConfigurationError("invalid_deepseek_message_role")
            safe_messages.append({"role": role, "content": _bounded_text(message.get("content"), field="message")})
        if max_tokens < 1 or max_tokens > 8_000:
            raise ProviderConfigurationError("invalid_max_tokens")
        response = self.transport.request_json(
            provider_id="deepseek",
            url="https://api.deepseek.com/chat/completions",
            security_context=_provider_security_context(
                scope,
                "create_narrative",
                cost_units=max(1, (max_tokens + 999) // 1_000),
            ),
            headers={"Authorization": f"Bearer {self.api_key}"},
            body={
                "model": self.model,
                "messages": safe_messages,
                "thinking": {"type": "enabled" if thinking else "disabled"},
                "max_tokens": max_tokens,
                "stream": False,
            },
        )
        response = _validated_response(response, "deepseek", "create_narrative")
        return {
            **response,
            "request_id": request_id,
            "prompt_template_id": prompt_template_id,
            "prompt_hash": prompt_hash,
            "context_refs": list(context_refs),
            "output_owner_domain": "narrative_only",
            "claims_numeric_truth": False,
            "controlled_numbers": [],
            "sovereign_verdict": None,
            "human_review_status": "required_pending",
            "prompt_content_stored": False,
        }


@dataclass
class TavilyResearchClient:
    transport: ProviderTransport
    api_key: str
    scope: TrustedProviderScope
    project_id: str | None = None
    admission_policy: TavilySourceAdmissionPolicy | None = None

    @classmethod
    def from_env(
        cls,
        transport: ProviderTransport | None = None,
        *,
        scope: TrustedProviderScope,
        admission_policy: TavilySourceAdmissionPolicy | None = None,
    ) -> "TavilyResearchClient":
        return cls(
            transport=transport or GovernedProviderTransport(),
            api_key=_required_secret("TAVILY_API_KEY"),
            scope=scope,
            project_id=os.getenv("TAVILY_PROJECT", "").strip() or None,
            admission_policy=admission_policy,
        )

    def _admission(self) -> TavilySourceAdmissionPolicy:
        return self.admission_policy or TavilySourceAdmissionPolicy.default_deny()

    def _validated_scope(self, scope: TrustedProviderScope) -> TrustedProviderScope:
        policy = self._admission()
        if (
            scope.preflight
            or scope.organization_id != policy.organization_id
            or scope.project_id != policy.project_id
        ):
            raise ProviderSecurityError("provider_scope_source_policy_mismatch")
        return scope

    def _headers(self) -> dict[str, str]:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        if self.project_id:
            headers["X-Project-ID"] = self.project_id
        return headers

    def search(
        self,
        *,
        query: str,
        sector_id: str = "general",
        geography: str = "saudi_arabia",
        include_domains: Sequence[str] = (),
        exclude_domains: Sequence[str] = (),
        max_results: int = 10,
        search_depth: str = "basic",
        topic: str = "general",
    ) -> dict[str, Any]:
        if search_depth not in {"basic", "advanced", "fast", "ultra-fast"}:
            raise ProviderConfigurationError("invalid_tavily_search_depth")
        if topic not in {"general", "news", "finance"}:
            raise ProviderConfigurationError("invalid_tavily_topic")
        if max_results < 1 or max_results > 20:
            raise ProviderConfigurationError("invalid_tavily_max_results")
        admission = self._admission().authorize_discovery(
            sector_id=sector_id,
            geography=geography,
            requested_include_domains=include_domains,
            requested_exclude_domains=exclude_domains,
        )
        body: dict[str, Any] = {
            "query": _bounded_text(query, field="query", maximum=1_000),
            "search_depth": search_depth,
            "topic": topic,
            "max_results": max_results,
            "include_domains": admission["include_domains"],
            "exclude_domains": admission["exclude_domains"],
            "include_answer": False,
            "include_raw_content": False,
            "include_images": False,
            "include_usage": True,
        }
        if admission["geography"] == "saudi_arabia":
            body["country"] = "saudi arabia"
        response = self.transport.request_json(
            provider_id="tavily",
            url="https://api.tavily.com/search",
            security_context=_provider_security_context(
                self._validated_scope(self.scope),
                "search",
                cost_units=max_results,
            ),
            headers=self._headers(),
            body=body,
        )
        response = _validated_response(response, "tavily", "search")
        return {
            **response,
            "source_admission": admission,
            "review_status": "review_required",
            "eligible_for_controlled_assumptions": False,
        }

    def extract(
        self,
        *,
        urls: Sequence[str],
        source_ids: Mapping[str, str],
        query: str | None = None,
        depth: str = "basic",
    ) -> dict[str, Any]:
        if not urls or len(urls) > 20:
            raise ProviderConfigurationError("invalid_tavily_extract_urls")
        if depth not in {"basic", "advanced"}:
            raise ProviderConfigurationError("invalid_tavily_extract_depth")
        admissions = [
            self._admission().authorize_content_url(
                source_id=str(source_ids.get(url) or ""),
                url=url,
                operation="extract",
            )
            for url in urls
        ]
        body: dict[str, Any] = {
            "urls": list(urls),
            "extract_depth": depth,
            "format": "markdown",
            "include_images": False,
            "include_usage": True,
        }
        if query:
            body["query"] = _bounded_text(query, field="query", maximum=1_000)
            body["chunks_per_source"] = 3
        response = self.transport.request_json(
            provider_id="tavily",
            url="https://api.tavily.com/extract",
            security_context=_provider_security_context(
                self._validated_scope(self.scope),
                "extract",
                cost_units=len(urls) * (2 if depth == "advanced" else 1),
            ),
            headers=self._headers(),
            body=body,
        )
        response = _validated_response(response, "tavily", "extract")
        review_status = (
            "auto_admitted_official_open"
            if admissions
            and all(
                admission.get("review_status") == "auto_admitted_official_open"
                for admission in admissions
            )
            else "review_required"
        )
        return {
            **response,
            "source_admissions": admissions,
            "review_status": review_status,
            "eligible_for_controlled_assumptions": False,
        }

    def crawl(
        self,
        *,
        source_id: str,
        url: str,
        instructions: str,
        max_depth: int = 2,
        limit: int = 50,
        select_paths: Sequence[str] = (),
        exclude_paths: Sequence[str] = (),
    ) -> dict[str, Any]:
        if max_depth < 1 or max_depth > 5 or limit < 1 or limit > 200:
            raise ProviderConfigurationError("invalid_tavily_crawl_bounds")
        policy = self._admission()
        admission = policy.authorize_content_url(
            source_id=source_id,
            url=url,
            operation="crawl",
        )
        graph_scope = policy.authorize_graph_scope(
            admission=admission,
            requested_select_paths=select_paths,
            requested_exclude_paths=exclude_paths,
        )
        response = self.transport.request_json(
            provider_id="tavily",
            url="https://api.tavily.com/crawl",
            security_context=_provider_security_context(
                self._validated_scope(self.scope),
                "crawl",
                cost_units=max(1, (limit + 9) // 10),
            ),
            headers=self._headers(),
            body={
                "url": _bounded_text(url, field="url", maximum=2_000),
                "instructions": _bounded_text(instructions, field="instructions", maximum=2_000),
                "max_depth": max_depth,
                "limit": limit,
                "select_domains": graph_scope["select_domains"],
                "select_paths": graph_scope["select_paths"],
                "exclude_paths": graph_scope["exclude_paths"],
                "allow_external": False,
                "extract_depth": "basic",
                "include_images": False,
                "include_usage": True,
            },
        )
        response = _validated_response(response, "tavily", "crawl")
        review_status = (
            "auto_admitted_official_open"
            if admission.get("review_status") == "auto_admitted_official_open"
            else "review_required"
        )
        return {
            **response,
            "source_admission": admission,
            "review_status": review_status,
            "eligible_for_controlled_assumptions": False,
        }

    def map_site(
        self,
        *,
        source_id: str,
        url: str,
        instructions: str,
        max_depth: int = 2,
        limit: int = 100,
    ) -> dict[str, Any]:
        if max_depth < 1 or max_depth > 5 or limit < 1 or limit > 500:
            raise ProviderConfigurationError("invalid_tavily_map_bounds")
        policy = self._admission()
        admission = policy.authorize_content_url(
            source_id=source_id,
            url=url,
            operation="map",
        )
        graph_scope = policy.authorize_graph_scope(admission=admission)
        response = self.transport.request_json(
            provider_id="tavily",
            url="https://api.tavily.com/map",
            security_context=_provider_security_context(
                self._validated_scope(self.scope),
                "map",
                cost_units=max(1, (limit + 19) // 20),
            ),
            headers=self._headers(),
            body={
                "url": _bounded_text(url, field="url", maximum=2_000),
                "instructions": _bounded_text(instructions, field="instructions", maximum=2_000),
                "max_depth": max_depth,
                "limit": limit,
                "select_domains": graph_scope["select_domains"],
                "select_paths": graph_scope["select_paths"],
                "exclude_paths": graph_scope["exclude_paths"],
                "allow_external": False,
                "include_usage": True,
            },
        )
        response = _validated_response(response, "tavily", "map")
        return {
            **response,
            "source_admission": admission,
            "review_status": "review_required",
            "eligible_for_controlled_assumptions": False,
        }


@dataclass
class GoogleLocationClient:
    transport: ProviderTransport
    api_key: str
    language_code: str = "ar"
    region_code: str = "SA"

    @classmethod
    def from_env(cls, transport: ProviderTransport | None = None) -> "GoogleLocationClient":
        return cls(
            transport=transport or GovernedProviderTransport(),
            api_key=_required_secret("GOOGLE_MAPS_API_KEY"),
            language_code=os.getenv("GOOGLE_MAPS_LANGUAGE", "ar").strip() or "ar",
            region_code=os.getenv("GOOGLE_MAPS_REGION", "SA").strip() or "SA",
        )

    def geocode_address(
        self,
        address: str,
        *,
        scope: TrustedProviderScope,
    ) -> dict[str, Any]:
        encoded = quote(_bounded_text(address, field="address", maximum=1_500), safe="")
        response = self.transport.request_json(
            provider_id="google_maps_platform",
            method="GET",
            url=f"https://geocode.googleapis.com/v4/geocode/address/{encoded}",
            security_context=_provider_security_context(
                scope,
                "geocode_address",
                preflight=scope.preflight,
            ),
            headers={
                "X-Goog-Api-Key": self.api_key,
                "X-Goog-FieldMask": "results.placeId,results.location,results.formattedAddress,results.addressComponents,results.viewport,results.granularity",
                "Accept-Language": self.language_code,
            },
            body=None,
        )
        return _validated_response(response, "google_maps_platform", "geocode_address")

    def reverse_geocode(
        self,
        latitude: float,
        longitude: float,
        *,
        scope: TrustedProviderScope,
    ) -> dict[str, Any]:
        if isinstance(latitude, bool) or isinstance(longitude, bool):
            raise ProviderConfigurationError("invalid_coordinates")
        try:
            normalized_latitude = float(latitude)
            normalized_longitude = float(longitude)
        except (TypeError, ValueError) as exc:
            raise ProviderConfigurationError("invalid_coordinates") from exc
        if (
            not math.isfinite(normalized_latitude)
            or not math.isfinite(normalized_longitude)
            or not (-90 <= normalized_latitude <= 90 and -180 <= normalized_longitude <= 180)
        ):
            raise ProviderConfigurationError("invalid_coordinates")
        response = self.transport.request_json(
            provider_id="google_maps_platform",
            method="GET",
            url=(
                "https://geocode.googleapis.com/v4/geocode/location/"
                f"{normalized_latitude},{normalized_longitude}"
            ),
            security_context=_provider_security_context(
                scope,
                "reverse_geocode",
                preflight=scope.preflight,
            ),
            headers={
                "X-Goog-Api-Key": self.api_key,
                "X-Goog-FieldMask": "results.placeId,results.location,results.formattedAddress,results.addressComponents,results.viewport,results.granularity,results.plusCode",
                "Accept-Language": self.language_code,
            },
            body=None,
        )
        return _validated_response(response, "google_maps_platform", "reverse_geocode")

    def search_places_text(
        self,
        *,
        scope: TrustedProviderScope,
        text_query: str,
        latitude: float | None = None,
        longitude: float | None = None,
        radius_meters: float = 5_000,
        page_size: int = 10,
    ) -> dict[str, Any]:
        if page_size < 1 or page_size > 20:
            raise ProviderConfigurationError("invalid_google_places_page_size")
        body: dict[str, Any] = {
            "textQuery": _bounded_text(text_query, field="text_query", maximum=500),
            "languageCode": self.language_code,
            "regionCode": self.region_code,
            "pageSize": page_size,
        }
        if latitude is not None or longitude is not None:
            if latitude is None or longitude is None:
                raise ProviderConfigurationError("both_coordinates_required")
            if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
                raise ProviderConfigurationError("invalid_coordinates")
            if radius_meters <= 0 or radius_meters > 50_000:
                raise ProviderConfigurationError("invalid_location_radius")
            body["locationBias"] = {
                "circle": {
                    "center": {"latitude": latitude, "longitude": longitude},
                    "radius": radius_meters,
                }
            }
        response = self.transport.request_json(
            provider_id="google_maps_platform",
            url="https://places.googleapis.com/v1/places:searchText",
            security_context=_provider_security_context(
                scope,
                "search_places_text",
                cost_units=page_size,
            ),
            headers={
                "X-Goog-Api-Key": self.api_key,
                "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.location,places.primaryType,places.businessStatus,places.googleMapsUri",
            },
            body=body,
        )
        response = _validated_response(response, "google_maps_platform", "search_places_text")
        return {
            **response,
            "persistence_policy": "place_id_and_project_location_only_until_terms_review",
            "eligible_for_pinecone": False,
        }


@dataclass
class PineconeKnowledgeClient:
    transport: ProviderTransport
    api_key: str
    index_name: str = "vision2030-kb"
    api_version: str = "2026-04"
    namespace_prefix: str = "asie"
    _index_host: str | None = None

    @classmethod
    def from_env(cls, transport: ProviderTransport | None = None) -> "PineconeKnowledgeClient":
        return cls(
            transport=transport or GovernedProviderTransport(),
            api_key=_required_secret("PINECONE_API_KEY"),
            index_name=os.getenv("PINECONE_INDEX", "vision2030-kb").strip() or "vision2030-kb",
            api_version=os.getenv("PINECONE_API_VERSION", "2026-04").strip() or "2026-04",
            namespace_prefix=os.getenv("PINECONE_NAMESPACE_PREFIX", "asie").strip() or "asie",
        )

    def _headers(self) -> dict[str, str]:
        return {"Api-Key": self.api_key, "X-Pinecone-Api-Version": self.api_version}

    def describe_index(
        self,
        *,
        scope: TrustedProviderScope | None = None,
    ) -> dict[str, Any]:
        scope = scope or TrustedProviderScope.for_platform_preflight()
        response = self.transport.request_json(
            provider_id="pinecone",
            method="GET",
            url=f"https://api.pinecone.io/indexes/{quote(self.index_name, safe='')}",
            security_context=_provider_security_context(
                scope,
                "describe_index",
                preflight=scope.preflight,
            ),
            headers=self._headers(),
            body=None,
        )
        try:
            validate_pinecone(
                response.get("payload"),
                "describe_index",
                expected_index_name=self.index_name,
            )
        except ProviderResponseContractError as exc:
            raise ExternalAcquisitionError(str(exc)) from exc
        response = {
            **response,
            "response_contract_version": PROVIDER_RESPONSE_CONTRACT_VERSION,
            "response_contract_validated": True,
        }
        payload = response.get("payload")
        if not isinstance(payload, dict):
            raise ExternalAcquisitionError("invalid_pinecone_index_description")
        host = str(payload.get("host") or "").strip()
        if not host or not host.endswith(".pinecone.io"):
            raise ExternalAcquisitionError("invalid_pinecone_index_host")
        self._index_host = host
        return {
            **response,
            "index_name": self.index_name,
            "index_host_discovered": True,
            "index_host": host,
            "pinecone_is_source_of_truth": False,
        }

    def _host(self, scope: TrustedProviderScope) -> str:
        if not self._index_host:
            self.describe_index(scope=scope)
        if not self._index_host:
            raise ExternalAcquisitionError("pinecone_index_host_unavailable")
        return self._index_host

    def upsert_approved_text(
        self,
        *,
        scope: TrustedProviderScope,
        records: Sequence[Mapping[str, Any]],
    ) -> dict[str, Any]:
        if not records or len(records) > 100:
            raise ProviderConfigurationError("invalid_pinecone_record_batch")
        namespace = tenant_project_namespace(scope.organization_id, scope.project_id, self.namespace_prefix)
        safe_records: list[dict[str, Any]] = []
        for record in records:
            record_id = _bounded_text(record.get("_id") or record.get("id"), field="record_id", maximum=512)
            text = _bounded_text(record.get("chunk_text") or record.get("text"), field="chunk_text", maximum=8_000)
            review_status = str(record.get("review_status") or "")
            classification = str(record.get("data_classification") or "")
            if review_status != "approved":
                raise ProviderConfigurationError("pinecone_record_requires_approved_review")
            if classification not in {"public", "internal_non_sensitive"}:
                raise ProviderConfigurationError("pinecone_record_classification_forbidden")
            safe_records.append(
                {
                    "_id": record_id,
                    "chunk_text": text,
                    "source_url": _bounded_text(record.get("source_url"), field="source_url", maximum=2_000),
                    "source_id": _bounded_text(record.get("source_id"), field="source_id", maximum=240),
                    "evidence_ref": _bounded_text(record.get("evidence_ref"), field="evidence_ref", maximum=240),
                    "review_status": review_status,
                    "data_classification": classification,
                    "organization_ref": _namespace_part(scope.organization_id),
                    "project_ref": _namespace_part(scope.project_id),
                    "ingested_at": _utc_now(),
                }
            )
        response = self.transport.request_ndjson(
            provider_id="pinecone",
            url=f"https://{self._host(scope)}/records/namespaces/{quote(namespace, safe='')}/upsert",
            headers=self._headers(),
            records=safe_records,
            security_context=_provider_security_context(
                scope,
                "upsert_approved_text",
                cost_units=len(safe_records),
            ),
        )
        response = _validated_response(response, "pinecone", "upsert_approved_text")
        return {
            **response,
            "index_name": self.index_name,
            "namespace": namespace,
            "record_count": len(safe_records),
            "source_of_truth": False,
            "records_required_approved_review": True,
        }

    def search_text(
        self,
        *,
        scope: TrustedProviderScope,
        query: str,
        top_k: int = 8,
        fields: Sequence[str] = ("chunk_text", "source_url", "source_id", "evidence_ref", "review_status"),
    ) -> dict[str, Any]:
        if top_k < 1 or top_k > 50:
            raise ProviderConfigurationError("invalid_pinecone_top_k")
        namespace = tenant_project_namespace(scope.organization_id, scope.project_id, self.namespace_prefix)
        response = self.transport.request_json(
            provider_id="pinecone",
            url=f"https://{self._host(scope)}/records/namespaces/{quote(namespace, safe='')}/search",
            headers=self._headers(),
            security_context=_provider_security_context(
                scope,
                "search_text",
                cost_units=top_k,
            ),
            body={
                "query": {"inputs": {"text": _bounded_text(query, field="query", maximum=2_000)}, "top_k": top_k},
                "fields": list(fields),
            },
        )
        response = _validated_response(response, "pinecone", "search_text")
        return {
            **response,
            "index_name": self.index_name,
            "namespace": namespace,
            "source_of_truth": False,
            "retrieval_requires_evidence_validation": True,
        }

    def upsert_public_knowledge(
        self,
        *,
        scope: TrustedProviderScope,
        records: Sequence[Mapping[str, Any]],
    ) -> dict[str, Any]:
        scope.require_platform_workload("public-knowledge-sync")
        if not records or len(records) > 100:
            raise ProviderConfigurationError("invalid_pinecone_record_batch")
        namespace = public_knowledge_namespace(self.namespace_prefix)
        forbidden_customer_fields = {
            "organization_id",
            "organization_ref",
            "project_id",
            "project_ref",
            "user_id",
            "session_id",
            "snapshot_id",
            "run_id",
            "prompt",
            "query",
        }
        text_fields = (
            "source_id",
            "publisher",
            "authority",
            "source_url",
            "license_id",
            "license_ref",
            "attribution",
            "sector",
            "geography",
            "language",
            "published_at",
            "retrieved_at",
            "content_sha256",
            "fresh_until",
            "expires_at",
            "unit",
            "evidence_ref",
            "admission_status",
            "data_classification",
        )
        safe_records: list[dict[str, Any]] = []
        for record in records:
            if forbidden_customer_fields.intersection(record):
                raise ProviderConfigurationError("public_knowledge_customer_field_forbidden")
            safe: dict[str, Any] = {
                "_id": _bounded_text(
                    record.get("_id") or record.get("id"),
                    field="record_id",
                    maximum=512,
                ),
                "chunk_text": _bounded_text(
                    record.get("chunk_text") or record.get("text"),
                    field="chunk_text",
                    maximum=8_000,
                ),
            }
            for field_name in text_fields:
                safe[field_name] = _bounded_text(
                    record.get(field_name),
                    field=field_name,
                    maximum=2_000,
                )
            for field_name in ("version", "freshness_days", "chunk_index", "chunk_count"):
                value = record.get(field_name)
                if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                    raise ProviderConfigurationError(f"invalid_public_knowledge_number:{field_name}")
                safe[field_name] = value
            confidence = record.get("confidence")
            if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
                raise ProviderConfigurationError("invalid_public_knowledge_number:confidence")
            if not 0.0 <= float(confidence) <= 1.0:
                raise ProviderConfigurationError("invalid_public_knowledge_number:confidence")
            safe["confidence"] = float(confidence)
            if not re.fullmatch(r"[0-9a-f]{64}", safe["content_sha256"]):
                raise ProviderConfigurationError("invalid_public_knowledge_content_hash")
            parsed_source = urlsplit(safe["source_url"])
            if parsed_source.scheme != "https" or not parsed_source.hostname:
                raise ProviderConfigurationError("invalid_public_knowledge_source_url")
            if safe["authority"] not in {"saudi_official", "international_official"}:
                raise ProviderConfigurationError("public_knowledge_authority_forbidden")
            if safe["admission_status"] != "auto_admitted_official_open":
                raise ProviderConfigurationError("public_knowledge_admission_forbidden")
            if safe["data_classification"] != "public":
                raise ProviderConfigurationError("public_knowledge_classification_forbidden")
            safe["source_of_truth"] = False
            safe_records.append(safe)
        response = self.transport.request_ndjson(
            provider_id="pinecone",
            url=f"https://{self._host(scope)}/records/namespaces/{quote(namespace, safe='')}/upsert",
            headers=self._headers(),
            records=safe_records,
            security_context=_provider_security_context(
                scope,
                "upsert_public_knowledge",
                cost_units=len(safe_records),
            ),
        )
        response = _validated_response(response, "pinecone", "upsert_public_knowledge")
        return {
            **response,
            "index_name": self.index_name,
            "namespace": namespace,
            "record_count": len(safe_records),
            "source_of_truth": False,
            "records_required_approved_review": False,
            "records_require_policy_admission": True,
        }

    def search_public_knowledge(
        self,
        *,
        scope: TrustedProviderScope,
        query: str,
        top_k: int = 8,
    ) -> dict[str, Any]:
        if scope.preflight or scope.organization_id == "__platform__":
            raise ProviderSecurityError("public_knowledge_tenant_scope_required")
        scope.request_context("search_public_knowledge")
        if top_k < 1 or top_k > 50:
            raise ProviderConfigurationError("invalid_pinecone_top_k")
        namespace = public_knowledge_namespace(self.namespace_prefix)
        fields = (
            "chunk_text",
            "source_id",
            "publisher",
            "authority",
            "source_url",
            "license_id",
            "license_ref",
            "attribution",
            "sector",
            "geography",
            "language",
            "published_at",
            "retrieved_at",
            "content_sha256",
            "version",
            "freshness_days",
            "fresh_until",
            "expires_at",
            "unit",
            "confidence",
            "evidence_ref",
            "admission_status",
            "data_classification",
        )
        response = self.transport.request_json(
            provider_id="pinecone",
            url=f"https://{self._host(scope)}/records/namespaces/{quote(namespace, safe='')}/search",
            headers=self._headers(),
            security_context=_provider_security_context(
                scope,
                "search_public_knowledge",
                cost_units=top_k,
            ),
            body={
                "query": {
                    "inputs": {"text": _bounded_text(query, field="query", maximum=2_000)},
                    "top_k": top_k,
                },
                "fields": list(fields),
            },
        )
        response = _validated_response(response, "pinecone", "search_public_knowledge")
        return {
            **response,
            "index_name": self.index_name,
            "namespace": namespace,
            "source_of_truth": False,
            "retrieval_requires_evidence_validation": True,
            "application_persists_query": False,
            "provider_retention_governed_externally": True,
        }

    def delete_public_knowledge(
        self,
        *,
        scope: TrustedProviderScope,
        record_ids: Sequence[str] | None = None,
        delete_all: bool = False,
    ) -> dict[str, Any]:
        scope.require_platform_workload("public-knowledge-sync")
        bounded_ids = [
            _bounded_text(value, field="record_id", maximum=512)
            for value in (record_ids or ())
        ]
        if delete_all == bool(bounded_ids):
            raise ProviderConfigurationError("public_knowledge_delete_scope_invalid")
        if len(bounded_ids) > 1_000:
            raise ProviderConfigurationError("public_knowledge_delete_batch_too_large")
        namespace = public_knowledge_namespace(self.namespace_prefix)
        body: dict[str, Any] = {"namespace": namespace}
        if delete_all:
            body["deleteAll"] = True
        else:
            body["ids"] = bounded_ids
        response = self.transport.request_json(
            provider_id="pinecone",
            url=f"https://{self._host(scope)}/vectors/delete",
            headers=self._headers(),
            body=body,
            security_context=_provider_security_context(
                scope,
                "delete_public_knowledge",
                cost_units=max(1, len(bounded_ids)),
            ),
        )
        response = _validated_response(response, "pinecone", "delete_public_knowledge")
        return {
            **response,
            "index_name": self.index_name,
            "namespace": namespace,
            "deleted": len(bounded_ids),
            "delete_all": delete_all,
            "source_of_truth": False,
        }

