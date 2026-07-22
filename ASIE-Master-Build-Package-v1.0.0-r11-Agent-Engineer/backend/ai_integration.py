from __future__ import annotations

from copy import deepcopy
from typing import Any

from backend.contracts import now_iso


class AIIntegrationError(ValueError):
    pass


class SecurityAuditSink:
    sensitive_fields = frozenset(
        {
            "prompt_text",
            "prompt",
            "content",
            "api_key",
            "secret",
            "token",
            "headers",
            "messages",
            "provider_config",
        }
    )

    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def record(self, *, event_type: str, reason: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        safe_metadata = self._safe_metadata(metadata or {})
        event = {
            "audit_event_id": f"ai-security-audit:{len(self.events) + 1}",
            "event_type": event_type,
            "reason": reason,
            "metadata": safe_metadata,
            "prompt_content_stored": False,
            "payload_content_stored": False,
            "created_at": now_iso(),
        }
        self.events.append(deepcopy(event))
        return event

    def snapshot(self) -> dict[str, Any]:
        return {
            "sink_id": "ai-security-audit-local-v1",
            "event_count": len(self.events),
            "events": deepcopy(self.events),
            "stores_prompt_content": False,
            "stores_provider_secrets": False,
        }

    def _safe_metadata(self, metadata: dict[str, Any]) -> dict[str, Any]:
        safe: dict[str, Any] = {}
        for key, value in metadata.items():
            if key in self.sensitive_fields:
                safe[key] = "[redacted]"
            elif isinstance(value, (str, int, float, bool)) or value is None:
                safe[key] = value
            elif isinstance(value, list):
                safe[key] = [item for item in value if isinstance(item, (str, int, float, bool))]
            else:
                safe[key] = str(type(value).__name__)
        return safe


class ProviderPolicyEngine:
    allowed_statuses = frozenset({"DISABLED", "GOVERNED", "MAINTENANCE", "READ_ONLY", "ACTIVE"})

    def __init__(self, *, status: str = "DISABLED", policy: str = "DENY_ALL", whitelist: list[str] | None = None) -> None:
        if status not in self.allowed_statuses:
            raise AIIntegrationError("invalid_provider_policy_status")
        self.status = status
        self.policy = policy
        self.whitelist = tuple(whitelist or [])

    def evaluate_registration(self, provider_metadata: dict[str, Any]) -> dict[str, Any]:
        provider_id = str(provider_metadata.get("provider_id") or "")
        if self.status in {"DISABLED", "MAINTENANCE", "READ_ONLY"} or self.policy == "DENY_ALL":
            return self._decision(False, "provider_registration_denied_by_policy", provider_id)
        if self.policy == "ALLOW_WHITELIST" or self.status == "GOVERNED":
            return self._decision(
                provider_id in self.whitelist,
                "provider_allowed_by_whitelist" if provider_id in self.whitelist else "provider_not_whitelisted",
                provider_id,
            )
        if self.status == "ACTIVE":
            return self._decision(True, "provider_allowed_active_policy", provider_id)
        return self._decision(False, "provider_policy_not_configured", provider_id)

    def snapshot(self) -> dict[str, Any]:
        return {
            "policy_engine_id": "ai-provider-policy-local-v1",
            "status": self.status,
            "policy": self.policy,
            "whitelist": list(self.whitelist),
            "registration_decision_owner": "policy_engine",
        }

    def _decision(self, allowed: bool, reason: str, provider_id: str) -> dict[str, Any]:
        return {
            "allowed": allowed,
            "reason": reason,
            "provider_id": provider_id,
            "status": self.status,
            "policy": self.policy,
        }


class ProviderRegistry:
    def __init__(self, policy_engine: ProviderPolicyEngine | None = None, audit_sink: SecurityAuditSink | None = None) -> None:
        self._providers: dict[str, dict[str, Any]] = {}
        self.policy_engine = policy_engine or ProviderPolicyEngine()
        self.audit_sink = audit_sink or SecurityAuditSink()

    def register(self, provider_metadata: dict[str, Any]) -> dict[str, Any]:
        decision = self.policy_engine.evaluate_registration(provider_metadata)
        if not decision["allowed"]:
            self.audit_sink.record(
                event_type="ai_provider_registration_rejected",
                reason=decision["reason"],
                metadata={
                    "provider_id": decision["provider_id"],
                    "registry_id": "ai-provider-registry-local-v1",
                    "policy_status": decision["status"],
                    "policy": decision["policy"],
                },
            )
            raise AIIntegrationError(decision["reason"])
        provider_id = decision["provider_id"]
        self._providers[provider_id] = {
            "provider_id": provider_id,
            "status": "registered_disabled_until_runtime_policy_allows_use",
        }
        return deepcopy(self._providers[provider_id])

    def snapshot(self) -> dict[str, Any]:
        return {
            "registry_id": "ai-provider-registry-local-v1",
            "status": self.policy_engine.status,
            "policy": self.policy_engine.policy,
            "policy_engine": self.policy_engine.snapshot(),
            "providers": [deepcopy(row) for row in self._providers.values()],
            "provider_count": len(self._providers),
            "registration_enabled": self.policy_engine.status not in {"DISABLED", "MAINTENANCE", "READ_ONLY"}
            and self.policy_engine.policy != "DENY_ALL",
            "external_network_enabled": False,
            "registration_decision_owner": "policy_engine",
            "security_audit": self.audit_sink.snapshot(),
        }


class ModelRouter:
    def route(self, provider_registry: ProviderRegistry) -> dict[str, Any]:
        registry = provider_registry.snapshot()
        if registry["provider_count"] != 0:
            raise AIIntegrationError("ai_provider_registry_must_remain_empty")
        return {
            "router_id": "ai-model-router-local-v1",
            "status": "disabled_no_provider",
            "provider_id": None,
            "model_id": None,
            "network_attempted": False,
        }


class PromptGovernance:
    allowed_prompt_classes = frozenset({"explanation", "summarization", "translation", "draft_narrative"})
    forbidden_prompt_classes = frozenset(
        {
            "financial_calculation",
            "sovereign_verdict",
            "legal_interpretation",
            "source_activation",
            "controlled_numeric_truth",
        }
    )
    forbidden_output_types = frozenset(
        {
            "controlled_number",
            "financial_result",
            "sovereign_verdict",
            "legal_interpretation",
            "source_governance_decision",
        }
    )

    def evaluate(self, request: dict[str, Any]) -> dict[str, Any]:
        prompt_class = str(request.get("prompt_class") or "")
        output_types = request.get("requested_output_types")
        if not isinstance(output_types, list):
            raise AIIntegrationError("requested_output_types_must_be_list")
        reasons: list[str] = []
        if prompt_class in self.forbidden_prompt_classes:
            reasons.append(f"forbidden_prompt_class:{prompt_class}")
        elif prompt_class not in self.allowed_prompt_classes:
            reasons.append(f"unregistered_prompt_class:{prompt_class}")
        forbidden_outputs = sorted(self.forbidden_output_types.intersection(str(item) for item in output_types))
        reasons.extend(f"forbidden_output_type:{item}" for item in forbidden_outputs)
        return {
            "policy_id": "ai-prompt-governance-v1",
            "status": "blocked" if reasons else "allowed_but_disabled",
            "reasons": reasons,
            "allowed_prompt_classes": sorted(self.allowed_prompt_classes),
            "forbidden_prompt_classes": sorted(self.forbidden_prompt_classes),
            "forbidden_output_types": sorted(self.forbidden_output_types),
            "prompt_content_forwarded": False,
        }


class OutputValidation:
    forbidden_owner_domains = frozenset({"finance", "legal", "sovereign_decision", "source_governance"})

    def validate(self, candidate: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(candidate, dict):
            raise AIIntegrationError("ai_candidate_output_must_be_object")
        violations: list[str] = []
        owner_domain = str(candidate.get("owner_domain") or "")
        if owner_domain in self.forbidden_owner_domains:
            violations.append(f"forbidden_owner_domain:{owner_domain}")
        if candidate.get("claims_numeric_truth") is True:
            violations.append("numeric_truth_claim_forbidden")
        if candidate.get("controlled_numbers"):
            violations.append("controlled_numbers_forbidden")
        if candidate.get("sovereign_verdict") is not None:
            violations.append("sovereign_verdict_forbidden")
        if candidate.get("legal_interpretation") is not None:
            violations.append("legal_interpretation_forbidden")
        return {
            "validator_id": "ai-output-validation-v1",
            "status": "rejected" if violations else "passed",
            "violations": violations,
            "can_own_controlled_numbers": False,
            "can_own_finance": False,
            "can_own_legal_interpretation": False,
            "can_own_sovereign_verdict": False,
        }


class HumanReviewGate:
    def evaluate(self, governance: dict[str, Any]) -> dict[str, Any]:
        blocked = governance["status"] == "blocked"
        return {
            "gate_id": "ai-human-review-gate-v1",
            "status": "not_applicable_blocked" if blocked else "required_pending",
            "required_for_any_future_ai_output": True,
            "bypass_allowed": False,
            "approved": False,
        }


class AIIntegrationShell:
    allowed_request_fields = frozenset(
        {
            "request_id",
            "project_id",
            "run_id",
            "snapshot_id",
            "purpose",
            "prompt_class",
            "prompt_template_id",
            "prompt_hash",
            "requested_output_types",
            "context_refs",
        }
    )

    def __init__(self) -> None:
        self.security_audit = SecurityAuditSink()
        self.provider_registry = ProviderRegistry(audit_sink=self.security_audit)
        self.model_router = ModelRouter()
        self.prompt_governance = PromptGovernance()
        self.output_validation = OutputValidation()
        self.human_review_gate = HumanReviewGate()
        self.audit_events: list[dict[str, Any]] = []

    def process(self, request: dict[str, Any]) -> dict[str, Any]:
        missing = self.allowed_request_fields - set(request)
        extra = set(request) - self.allowed_request_fields
        if missing:
            self.audit_security_event(
                reason="ai_request_missing_fields",
                request=request,
                metadata={"missing_fields": sorted(missing)},
            )
            raise AIIntegrationError("ai_request_missing_fields:" + ",".join(sorted(missing)))
        if extra:
            self.audit_security_event(
                reason="ai_request_forbidden_fields",
                request=request,
                metadata={"forbidden_fields": sorted(extra)},
            )
            raise AIIntegrationError("ai_request_forbidden_fields:" + ",".join(sorted(extra)))
        try:
            governance = self.prompt_governance.evaluate(request)
        except AIIntegrationError:
            self.audit_security_event(
                reason="invalid_requested_output_types",
                request=request,
                metadata={"requested_output_types_type": type(request.get("requested_output_types")).__name__},
            )
            raise
        routing = (
            {
                "router_id": "ai-model-router-local-v1",
                "status": "skipped_governance_blocked",
                "provider_id": None,
                "model_id": None,
                "network_attempted": False,
            }
            if governance["status"] == "blocked"
            else self.model_router.route(self.provider_registry)
        )
        review_gate = self.human_review_gate.evaluate(governance)
        status = "rejected_governance" if governance["status"] == "blocked" else "disabled_no_provider"
        security_event = None
        if governance["status"] == "blocked":
            security_event = self.audit_security_event(
                reason="prompt_governance_blocked",
                request=request,
                metadata={"governance_reasons": governance["reasons"]},
            )
        audit_event = {
            "audit_event_id": f"ai-audit:{request['request_id']}",
            "event_type": "ai_request_attempt",
            "request_id": request["request_id"],
            "project_id": request["project_id"],
            "run_id": request["run_id"],
            "snapshot_id": request["snapshot_id"],
            "purpose": request["purpose"],
            "prompt_class": request["prompt_class"],
            "prompt_template_id": request["prompt_template_id"],
            "prompt_hash": request["prompt_hash"],
            "prompt_content_stored": False,
            "governance_status": governance["status"],
            "routing_status": routing["status"],
            "outcome": status,
            "network_attempted": False,
            "security_audit_ref": security_event["audit_event_id"] if security_event else None,
            "created_at": now_iso(),
        }
        self.audit_events.append(deepcopy(audit_event))
        return {
            "request_id": request["request_id"],
            "project_id": request["project_id"],
            "run_id": request["run_id"],
            "snapshot_id": request["snapshot_id"],
            "status": status,
            "provider_registry": self.provider_registry.snapshot(),
            "routing": routing,
            "prompt_governance": governance,
            "output_validation": self.output_validation.validate({}),
            "human_review_gate": review_gate,
            "output": None,
            "audit_event": audit_event,
            "security_audit_event": security_event,
            "external_fetch_enabled": False,
            "ai_provider_enabled": False,
        }

    def audit_security_event(
        self,
        *,
        reason: str,
        request: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        request = request or {}
        safe_metadata = {
            "request_id": request.get("request_id"),
            "project_id": request.get("project_id"),
            "run_id": request.get("run_id"),
            "snapshot_id": request.get("snapshot_id"),
            "purpose": request.get("purpose"),
            "prompt_class": request.get("prompt_class"),
            "prompt_template_id": request.get("prompt_template_id"),
            "prompt_hash": request.get("prompt_hash"),
            "contract": "ai.integration.request.v1",
            "module": "module.ai_integration",
            "correlation_id": request.get("correlation_id"),
        }
        if metadata:
            safe_metadata.update(metadata)
        return self.security_audit.record(
            event_type="ai_request_rejected",
            reason=reason,
            metadata=safe_metadata,
        )

    def status(self) -> dict[str, Any]:
        return {
            "module_id": "module.ai_integration",
            "state": "disabled_governed",
            "provider_registry": self.provider_registry.snapshot(),
            "audit_event_count": len(self.audit_events),
            "security_audit": self.security_audit.snapshot(),
            "external_fetch_enabled": False,
            "ai_provider_enabled": False,
        }
