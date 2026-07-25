"""Repository-backed governed Pre-Run service.

Market item research executes through the canonical AAS path:
Kernel -> Heart Controller -> ASIE System Bus -> Socket Contract Layer ->
ASIE Market Intelligence Module. External fetch and AI providers remain disabled.
"""
from __future__ import annotations

from typing import Any

from backend.aas_kernel import AASKernel
from backend.aas_registry import bootstrap_default_registry
from backend.bus_controller import BusController
from backend.dib_runtime_extension import install_finance_manifest_gate, register_dib_runtime, register_market_handler
from backend.heart_controller import HeartController, HeartTask
from backend.intelligence_context import IntelligenceContext
from backend.intelligence_workflow import IntelligenceContextWorkflow
from backend.module_runtime import ModuleRuntime
from backend.system_bus import BusMessage, SystemBus

# Install the additive manifest gate before the local API creates its default ModuleRuntime.
# Frozen AAS files remain byte-for-byte unchanged.
install_finance_manifest_gate()


def _market_runtime() -> tuple[ModuleRuntime, str]:
    registry = register_dib_runtime(bootstrap_default_registry())
    kernel = AASKernel(registry=registry)
    kernel.boot()
    hearts = HeartController(kernel)
    hearts.bootstrap()
    bus_controller = BusController(kernel, hearts)
    bus_controller.bootstrap()
    bus = SystemBus(bus_controller)
    bus.bootstrap()
    runtime = ModuleRuntime(kernel, bus)
    runtime.bootstrap()
    runtime.register_default_handlers()
    register_market_handler(runtime)
    assignment = hearts.assign_task(
        HeartTask(
            task_id="market-pre-run",
            purpose="market_item_evidence",
            requires_assist=False,
        )
    )
    assigned = assignment.get("assignments", [])
    if not assigned:
        raise ValueError("market_pre_run_heart_assignment_failed")
    return runtime, f"aas.heart.{assigned[0]['heart_id']}"


def _expand_market_components(
    *,
    project_id: str,
    context_build_id: str,
    geography: str,
    sector: str,
    components: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    market_components = [component for component in components if component.get("kind") == "market_query"]
    if not market_components:
        return [dict(component) for component in components]

    runtime, source_module_id = _market_runtime()
    expanded: list[dict[str, Any]] = []
    for index, component in enumerate(components):
        if component.get("kind") != "market_query":
            expanded.append(dict(component))
            continue
        raw = component.get("value")
        if not isinstance(raw, dict):
            raise ValueError("market_query_component_value_must_be_object")
        query_id = str(raw.get("query_id") or f"{context_build_id}:market:{index + 1}")
        payload = {
            "project_id": project_id,
            "query_id": query_id,
            "item_id": str(raw.get("item_id") or component.get("component_id") or ""),
            "specification": str(raw.get("specification") or ""),
            "geography": str(raw.get("geography") or geography),
            "category": str(raw.get("category") or "market_assumption"),
            "unit": str(raw.get("unit") or ""),
            "candidate_samples": raw.get("candidate_samples") or [],
            "source_refs": raw.get("source_refs") or [],
        }
        message = BusMessage(
            source_module_id=source_module_id,
            target_module_id="module.market_intelligence",
            contract_id="market.query.request.v1",
            socket_id="socket.market.query",
            correlation_id=f"corr:{context_build_id}:{query_id}",
            audit_ref=f"audit:{context_build_id}:{query_id}",
            payload=payload,
        )
        result = runtime.execute(message)
        pack = result.output["evidence_pack"]
        expanded.append(
            {
                "component_id": str(component.get("component_id") or f"component:{query_id}"),
                "kind": "market_evidence_pack",
                "value": pack,
                "source": "ASIE Market Intelligence Module",
                "freshness": str(pack.get("created_at") or component.get("freshness") or ""),
                "geography": str(pack.get("geography") or geography),
                "sector": str(component.get("sector") or sector),
                "confidence": str(pack.get("confidence") or "low"),
                "lineage": [
                    "market.query.request.v1",
                    "socket.market.query",
                    "module.market_intelligence",
                    "market.evidence.pack.v1",
                    str(pack.get("content_hash") or ""),
                ],
                "review": "PENDING",
            }
        )
    return expanded


class IntelligencePreRunService:
    def __init__(self, repository, *, workflow: IntelligenceContextWorkflow | None = None):
        self.repository = repository
        self.workflow = workflow or IntelligenceContextWorkflow()

    def build_local_context(
        self,
        *,
        organization_id: str,
        project_id: str,
        context_build_id: str,
        idempotency_key: str,
        geography: str,
        sector: str,
        components: list[dict[str, Any]],
        principal,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        def builder() -> dict[str, Any]:
            context = IntelligenceContext(
                context_build_id,
                organization_id,
                project_id,
                geography,
                sector,
                idempotency_key,
            )
            from backend.intelligence_context import ContextComponent

            expanded = _expand_market_components(
                project_id=project_id,
                context_build_id=context_build_id,
                geography=geography,
                sector=sector,
                components=components,
            )
            context.components = [ContextComponent(**component) for component in expanded]
            context.transition("VALIDATING").transition("INTEGRITY_LOCKED")
            return {
                "context_hash": context.context_hash,
                "context_state": context.state,
                "geography": geography,
                "sector": sector,
                "components": [component.as_dict() for component in context.components],
            }

        result = self.workflow.execute(
            organization_id=organization_id,
            project_id=project_id,
            context_build_id=context_build_id,
            idempotency_key=idempotency_key,
            builder=builder,
        )
        if result.state != "REVIEW_PENDING":
            return {
                "context_build_id": context_build_id,
                "state": result.state,
                "error": result.error,
                "audit": result.audit,
                "snapshot_mutation": False,
            }
        record = self.repository.create_intelligence_context(
            payload={
                "organization_id": organization_id,
                "project_id": project_id,
                "context_build_id": context_build_id,
                "idempotency_key": idempotency_key,
                "context_hash": result.output["context_hash"],
                "state": "REVIEW_PENDING",
                "geography": geography,
                "sector": sector,
                "component_manifest": result.output["components"],
            },
            principal=principal,
            correlation_id=correlation_id,
        )
        return {
            "context": record,
            "workflow": result.__dict__,
            "snapshot_mutation": False,
            "external_fetch_enabled": False,
            "aas_market_path": [
                "Kernel",
                "Heart Controller",
                "ASIE System Bus",
                "Socket Contract Layer",
                "ASIE Market Intelligence Module",
            ],
        }
