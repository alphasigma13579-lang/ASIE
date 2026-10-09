"""Offline local-model example. HTTP never invokes this builder.

This is not the production evidence resolver or AAS admission path.
"""
from __future__ import annotations

from typing import Any

from backend.intelligence_context import ContextComponent, IntelligenceContext, idempotency_fingerprint
from backend.intelligence_workflow import IntelligenceContextWorkflow


class IntelligencePreRunService:
    def __init__(self, repository, *, workflow: IntelligenceContextWorkflow | None = None):
        self.repository = repository
        self.workflow = workflow

    def build_local_context(self, *, organization_id: str, project_id: str, context_build_id: str, idempotency_key: str, geography: str, sector: str, components: list[dict[str, Any]], principal, correlation_id: str | None = None) -> dict[str, Any]:
        # Authorization and saved scope precede model creation, cache and replay.
        scope = self.repository.intelligence_project_scope(organization_id=organization_id, project_id=project_id, principal=principal, correlation_id=correlation_id)
        if scope != {"geography": geography, "sector": sector}:
            raise ValueError("context_saved_scope_mismatch")
        context = IntelligenceContext(context_build_id, organization_id, project_id, geography, sector, idempotency_key)
        try:
            context.components = [ContextComponent(**component) for component in components]
            context.transition("VALIDATING").transition("INTEGRITY_LOCKED").transition("REVIEW_PENDING")
            context = self.repository._validated_intelligence_model(context)
        except (TypeError, ValueError):
            return {"error": "local_context_validation_failed", "snapshot_mutation": False, "external_fetch_enabled": False}

        def builder() -> dict[str, Any]:
            return {"context_hash": context.context_hash, "context_state": context.state, "geography": context.geography, "sector": context.sector, "components": [component.as_dict() for component in context.components]}

        workflow = self.workflow
        if workflow is None:
            workflow = self.workflow = IntelligenceContextWorkflow()
        # The existing offline workflow cache keys tenant + key, so scope the
        # supplied key by project here rather than changing the workflow contract.
        key = idempotency_fingerprint(organization_id, project_id, idempotency_key)
        try:
            result = workflow.execute(organization_id=organization_id, project_id=project_id, context_build_id=context_build_id, idempotency_key=key, builder=builder)
            if result.state != "REVIEW_PENDING" or not isinstance(result.output, dict) or result.output.get("context_hash") != context.context_hash:
                return {"error": "local_context_unavailable", "snapshot_mutation": False, "external_fetch_enabled": False}
            record = self.repository.persist_validated_intelligence_context(context=context, principal=principal, correlation_id=correlation_id)
        except (ValueError, RuntimeError, TimeoutError, OSError):
            return {"error": "local_context_unavailable", "snapshot_mutation": False, "external_fetch_enabled": False}
        return {"context": record, "snapshot_mutation": False, "external_fetch_enabled": False}
