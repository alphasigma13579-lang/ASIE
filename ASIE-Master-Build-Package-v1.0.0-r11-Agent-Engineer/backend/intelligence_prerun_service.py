"""Repository-backed local Pre-Run service; never invokes AAS/Snapshot assembly."""
from __future__ import annotations

from typing import Any

from backend.intelligence_context import IntelligenceContext
from backend.intelligence_workflow import IntelligenceContextWorkflow


class IntelligencePreRunService:
    def __init__(self, repository, *, workflow: IntelligenceContextWorkflow | None = None):
        self.repository = repository
        self.workflow = workflow or IntelligenceContextWorkflow()

    def build_local_context(self, *, organization_id: str, project_id: str, context_build_id: str, idempotency_key: str, geography: str, sector: str, components: list[dict[str, Any]], principal, correlation_id: str | None = None) -> dict[str, Any]:
        def builder() -> dict[str, Any]:
            context = IntelligenceContext(context_build_id, organization_id, project_id, geography, sector, idempotency_key)
            from backend.intelligence_context import ContextComponent
            context.components = [ContextComponent(**component) for component in components]
            context.transition("VALIDATING").transition("INTEGRITY_LOCKED")
            return {"context_hash": context.context_hash, "context_state": context.state, "geography": geography, "sector": sector, "components": [component.as_dict() for component in context.components]}

        result = self.workflow.execute(organization_id=organization_id, project_id=project_id, context_build_id=context_build_id, idempotency_key=idempotency_key, builder=builder)
        if result.state != "REVIEW_PENDING":
            return {"context_build_id": context_build_id, "state": result.state, "error": result.error, "audit": result.audit, "snapshot_mutation": False}
        record = self.repository.create_intelligence_context(payload={"organization_id": organization_id, "project_id": project_id, "context_build_id": context_build_id, "idempotency_key": idempotency_key, "context_hash": result.output["context_hash"], "state": "REVIEW_PENDING", "geography": geography, "sector": sector, "component_manifest": result.output["components"]}, principal=principal, correlation_id=correlation_id)
        return {"context": record, "workflow": result.__dict__, "snapshot_mutation": False, "external_fetch_enabled": False}
