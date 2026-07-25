from __future__ import annotations

from backend.aas_registry import (
    AASRegistry,
    ContractDefinition,
    ModuleDefinition,
    SocketDefinition,
)
from backend.market_intelligence import MarketIntelligenceModuleAdapter

_FINANCE_GATE_INSTALLED = False


def dib_contracts() -> tuple[ContractDefinition, ...]:
    return (
        ContractDefinition(
            contract_id="product.ai.interview.v1",
            version="1.0.0-local-core",
            owner="DIB Guided Interview",
            purpose="Bounded deterministic project interview using Template and Question Registries; no provider call.",
            required_fields=("project_id", "template_id", "questions", "answers"),
        ),
        ContractDefinition(
            contract_id="file.intake.mapping.v1",
            version="1.0.0-local-core",
            owner="DIB Data Intake",
            purpose="Map manual, CSV, XLSX, PDF, and supplier quote rows into review-required blueprint candidates.",
            required_fields=("project_id", "source_type", "mapped_candidates"),
        ),
        ContractDefinition(
            contract_id="dynamic.input.blueprint.v1",
            version="1.0.0-local-core",
            owner="Dynamic Input Blueprint",
            purpose="Governed project-specific item model where idea-only and data paths converge.",
            required_fields=("blueprint_id", "project_id", "template_id", "revision_id", "items", "content_hash"),
        ),
        ContractDefinition(
            contract_id="blueprint.revision.v1",
            version="1.0.0-local-core",
            owner="Dynamic Input Blueprint",
            purpose="Immutable revision record for later item or price changes.",
            required_fields=("blueprint_id", "revision_id", "revision", "items", "content_hash"),
        ),
        ContractDefinition(
            contract_id="approved.input.manifest.v1",
            version="1.0.0-local-core",
            owner="Manifest Validation Gate",
            purpose="Approved normalized assumptions supplied to the deterministic Finance Engine.",
            required_fields=("manifest_id", "project_id", "version", "items", "normalized_inputs", "content_hash"),
        ),
        ContractDefinition(
            contract_id="manifest.validation.v1",
            version="1.0.0-local-core",
            owner="Manifest Validation Gate",
            purpose="Validate approval, zero semantics, evidence lineage, required items, and manifest identity before Finance.",
            required_fields=("manifest_id", "project_id", "status", "blockers"),
        ),
        ContractDefinition(
            contract_id="market.query.request.v1",
            version="1.0.0-local-core",
            owner="ASIE Market Intelligence Module",
            purpose="Request item-specific governed local market evidence through Bus and Socket.",
            required_fields=(
                "project_id",
                "query_id",
                "item_id",
                "specification",
                "geography",
                "category",
            ),
        ),
        ContractDefinition(
            contract_id="market.evidence.pack.v1",
            version="1.0.0-local-core",
            owner="ASIE Market Intelligence Module",
            purpose="Return cleaned samples, P25-P75 range, weighted median, outlier report, and evidence lineage.",
            required_fields=(
                "project_id",
                "query_id",
                "item_id",
                "evidence_pack",
            ),
        ),
    )


def dib_sockets() -> tuple[SocketDefinition, ...]:
    return (
        SocketDefinition(
            socket_id="socket.market.query",
            contract_id="market.query.request.v1",
            provider_module_id="module.market_intelligence",
            consumer_module_ids=("module.project_run_workflow",),
        ),
    )


def dib_modules() -> tuple[ModuleDefinition, ...]:
    return (
        ModuleDefinition(
            module_id="module.market_intelligence",
            label="ASIE Market Intelligence Module",
            module_type="product_engine_descriptor",
            owner_file="backend/market_intelligence.py",
            provides=("socket.market.query",),
            notes=(
                "Item-specific governed evidence only.",
                "External fetch remains disabled.",
                "Returns candidate assumptions; never owns Finance or sovereign decisions.",
            ),
        ),
    )



def install_finance_manifest_gate() -> None:
    global _FINANCE_GATE_INSTALLED
    if _FINANCE_GATE_INSTALLED:
        return

    from backend.dib_finance_gate import finance_result_from_project_inputs
    from backend.module_runtime import FinanceModuleAdapter

    def handle(self, payload):
        finance, blockers, manifest = finance_result_from_project_inputs(
            str(payload["project_id"]),
            dict(payload.get("inputs") or {}),
            assumption_refs=list(payload.get("assumption_refs") or []),
        )
        return {
            "module_id": self.module_id,
            "contract_id": "finance.result.v1",
            "project_id": payload["project_id"],
            "run_id": payload["run_id"],
            "snapshot_id": payload["snapshot_id"],
            "finance": finance,
            "blockers": blockers,
            "approved_input_manifest": manifest,
            "manifest_validation_gate": {
                "status": manifest["status"],
                "contract": "approved.input.manifest.v1",
                "finance_received_raw_ui_inputs": False,
            },
            "external_fetch_enabled": False,
            "ai_enabled": False,
        }

    FinanceModuleAdapter.handle = handle
    _FINANCE_GATE_INSTALLED = True


def register_dib_runtime(registry: AASRegistry) -> AASRegistry:
    install_finance_manifest_gate()
    snapshot = registry.snapshot()
    contract_ids = {row["contract_id"] for row in snapshot["contracts"]}
    socket_ids = {row["socket_id"] for row in snapshot["sockets"]}
    module_ids = {row["module_id"] for row in snapshot["modules"]}

    for contract in dib_contracts():
        if contract.contract_id not in contract_ids:
            registry.register_contract(contract)
    for socket in dib_sockets():
        if socket.socket_id not in socket_ids:
            registry.register_socket(socket)
    for module in dib_modules():
        if module.module_id not in module_ids:
            registry.register_module(module)
    return registry


def register_market_handler(runtime) -> None:
    if "module.market_intelligence" not in runtime.handlers:
        runtime.register_handler("module.market_intelligence", MarketIntelligenceModuleAdapter().handle)
