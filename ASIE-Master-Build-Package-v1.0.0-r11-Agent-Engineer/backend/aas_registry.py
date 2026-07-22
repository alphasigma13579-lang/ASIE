from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class RegistryError(ValueError):
    pass


class DuplicateRegistrationError(RegistryError):
    pass


class UnknownRegistrationError(RegistryError):
    pass


class ContractValidationError(RegistryError):
    pass


@dataclass(frozen=True)
class ContractDefinition:
    contract_id: str
    version: str
    owner: str
    purpose: str
    required_fields: tuple[str, ...] = ()
    status: str = "registered"

    def to_public(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "version": self.version,
            "owner": self.owner,
            "purpose": self.purpose,
            "required_fields": list(self.required_fields),
            "status": self.status,
        }


@dataclass(frozen=True)
class SocketDefinition:
    socket_id: str
    contract_id: str
    provider_module_id: str
    consumer_module_ids: tuple[str, ...] = ()
    direction: str = "request_response"
    status: str = "registered"

    def to_public(self) -> dict[str, Any]:
        return {
            "socket_id": self.socket_id,
            "contract_id": self.contract_id,
            "provider_module_id": self.provider_module_id,
            "consumer_module_ids": list(self.consumer_module_ids),
            "direction": self.direction,
            "status": self.status,
        }


@dataclass(frozen=True)
class ModuleDefinition:
    module_id: str
    label: str
    module_type: str
    owner_file: str
    provides: tuple[str, ...] = ()
    requires: tuple[str, ...] = ()
    lifecycle_state: str = "registered"
    external_fetch_enabled: bool = False
    notes: tuple[str, ...] = field(default_factory=tuple)

    def to_public(self) -> dict[str, Any]:
        return {
            "module_id": self.module_id,
            "label": self.label,
            "module_type": self.module_type,
            "owner_file": self.owner_file,
            "provides": list(self.provides),
            "requires": list(self.requires),
            "lifecycle_state": self.lifecycle_state,
            "external_fetch_enabled": self.external_fetch_enabled,
            "notes": list(self.notes),
        }


class AASRegistry:
    def __init__(self, registry_id: str = "aas_registry_local_v1") -> None:
        self.registry_id = registry_id
        self._contracts: dict[str, ContractDefinition] = {}
        self._sockets: dict[str, SocketDefinition] = {}
        self._modules: dict[str, ModuleDefinition] = {}

    def register_contract(self, contract: ContractDefinition) -> ContractDefinition:
        if contract.contract_id in self._contracts:
            raise DuplicateRegistrationError(f"contract already registered: {contract.contract_id}")
        if not contract.contract_id or not contract.version:
            raise ContractValidationError("contract_id and version are required")
        self._contracts[contract.contract_id] = contract
        return contract

    def register_socket(self, socket: SocketDefinition) -> SocketDefinition:
        if socket.socket_id in self._sockets:
            raise DuplicateRegistrationError(f"socket already registered: {socket.socket_id}")
        if socket.contract_id not in self._contracts:
            raise UnknownRegistrationError(f"socket references unknown contract: {socket.contract_id}")
        self._sockets[socket.socket_id] = socket
        return socket

    def register_module(self, module: ModuleDefinition) -> ModuleDefinition:
        if module.module_id in self._modules:
            raise DuplicateRegistrationError(f"module already registered: {module.module_id}")
        for socket_id in module.provides + module.requires:
            if socket_id not in self._sockets:
                raise UnknownRegistrationError(f"module references unknown socket: {socket_id}")
        if module.external_fetch_enabled:
            raise ContractValidationError("AAS local runtime forbids external fetch by default")
        self._modules[module.module_id] = module
        return module

    def contract(self, contract_id: str) -> ContractDefinition:
        try:
            return self._contracts[contract_id]
        except KeyError as exc:
            raise UnknownRegistrationError(f"unknown contract: {contract_id}") from exc

    def socket(self, socket_id: str) -> SocketDefinition:
        try:
            return self._sockets[socket_id]
        except KeyError as exc:
            raise UnknownRegistrationError(f"unknown socket: {socket_id}") from exc

    def module(self, module_id: str) -> ModuleDefinition:
        try:
            return self._modules[module_id]
        except KeyError as exc:
            raise UnknownRegistrationError(f"unknown module: {module_id}") from exc

    def validate_contract_payload(self, contract_id: str, payload: dict[str, Any]) -> None:
        contract = self.contract(contract_id)
        missing = [field_name for field_name in contract.required_fields if field_name not in payload]
        if missing:
            raise ContractValidationError(
                f"payload for {contract_id} is missing required fields: {', '.join(missing)}"
            )

    def assert_socket_contract(self, socket_id: str, contract_id: str) -> None:
        socket = self.socket(socket_id)
        if socket.contract_id != contract_id:
            raise ContractValidationError(
                f"socket {socket_id} is bound to {socket.contract_id}, not {contract_id}"
            )

    def snapshot(self) -> dict[str, Any]:
        return {
            "registry_id": self.registry_id,
            "contracts": [item.to_public() for item in self._contracts.values()],
            "sockets": [item.to_public() for item in self._sockets.values()],
            "modules": [item.to_public() for item in self._modules.values()],
            "external_fetch_enabled": False,
        }

    def counts(self) -> dict[str, int]:
        return {
            "contracts": len(self._contracts),
            "sockets": len(self._sockets),
            "modules": len(self._modules),
        }


def bootstrap_default_registry() -> AASRegistry:
    registry = AASRegistry()
    for contract in default_contracts():
        registry.register_contract(contract)
    for socket in default_sockets():
        registry.register_socket(socket)
    for module in default_modules():
        registry.register_module(module)
    return registry


def default_contracts() -> tuple[ContractDefinition, ...]:
    return (
        ContractDefinition(
            contract_id="aas.kernel.boot.v1",
            version="1.0.0",
            owner="ASIE Kernel",
            purpose="Boot runtime without business logic.",
            required_fields=("runtime_id", "profile_id", "ports"),
        ),
        ContractDefinition(
            contract_id="aas.registry.snapshot.v1",
            version="1.0.0",
            owner="AAS Registry",
            purpose="Expose registered contracts, sockets, and modules.",
            required_fields=("registry_id", "contracts", "sockets", "modules"),
        ),
        ContractDefinition(
            contract_id="aas.heart.status.v1",
            version="1.0.0",
            owner="Heart Controller",
            purpose="Expose controller-managed heart state and health.",
            required_fields=("controller_id", "hearts"),
        ),
        ContractDefinition(
            contract_id="aas.heart.assignment.v1",
            version="1.0.0",
            owner="Heart Controller",
            purpose="Assign runtime work to hearts without business execution.",
            required_fields=("controller_id", "task_id", "purpose"),
        ),
        ContractDefinition(
            contract_id="aas.bus.status.v1",
            version="1.0.0",
            owner="Bus Controller",
            purpose="Expose Bus Controller state and admission counters.",
            required_fields=("controller_id", "state", "message_count"),
        ),
        ContractDefinition(
            contract_id="aas.bus.message.v1",
            version="1.0.0",
            owner="ASIE System Bus",
            purpose="Transport runtime messages with correlation and audit lineage.",
            required_fields=(
                "message_id",
                "operation_id",
                "idempotency_key",
                "input_hash",
                "source_module_id",
                "target_module_id",
                "contract_id",
                "socket_id",
                "correlation_id",
                "audit_ref",
                "payload",
            ),
        ),
        ContractDefinition(
            contract_id="aas.socket.enforcement.v1",
            version="1.0.0",
            owner="Socket Contract Layer",
            purpose="Enforce Socket First, Module Second before runtime delivery.",
            required_fields=("layer_id", "state", "checked_count"),
        ),
        ContractDefinition(
            contract_id="aas.module.execution.v1",
            version="1.0.0",
            owner="Module Runtime",
            purpose="Record controlled execution of a registered module after Bus and Socket checks.",
            required_fields=("runtime_id", "module_id", "message_id", "status"),
        ),
        ContractDefinition(
            contract_id="ProjectRunHttpRequest.v1",
            version="1.0.0-local-core",
            owner="Python API Request Guard",
            purpose="Sanitized project run HTTP request with no React-derived calculations.",
            required_fields=(
                "project_id",
                "scenario_id",
                "operation_id",
                "idempotency_key",
                "input_hash",
                "requested_at",
            ),
        ),
        ContractDefinition(
            contract_id="project.run.request.v1",
            version="1.0.0-local-core",
            owner="ASIE Kernel",
            purpose="Kernel admission envelope for a sanitized project run request.",
            required_fields=("project_id", "scenario_id", "operation_id", "idempotency_key", "input_hash"),
        ),
        ContractDefinition(
            contract_id="project.run.workflow.v1",
            version="1.0.0-local-core",
            owner="Project Run Workflow",
            purpose="Run context admission before module dispatch, snapshot assembly, and projections.",
            required_fields=(
                "project_id",
                "scenario_id",
                "operation_id",
                "idempotency_key",
                "input_hash",
                "requested_at",
                "input_contract_id",
            ),
        ),
        ContractDefinition(
            contract_id="project.run.completed.v1",
            version="1.0.0-local-core",
            owner="Project Run Workflow",
            purpose="Completion envelope after immutable snapshot success boundary.",
            required_fields=("project_id", "run_id", "snapshot_id", "idempotency_key"),
        ),
        ContractDefinition(
            contract_id="finance.calculate.v1",
            version="1.0.0-local-core",
            owner="Finance Module",
            purpose="Command envelope for deterministic local finance calculation.",
            required_fields=("project_id", "run_id", "snapshot_id", "inputs"),
        ),
        ContractDefinition(
            contract_id="finance.result.v1",
            version="1.0.0-local-core",
            owner="Finance Module",
            purpose="Typed financial result envelope owned by backend finance engine.",
            required_fields=("project_id", "run_id", "snapshot_id"),
        ),
        ContractDefinition(
            contract_id="evidence.ledger.build.v1",
            version="1.0.0-local-core",
            owner="Evidence Ledger Module",
            purpose="Command envelope for building evidence lineage from reviewed local data.",
            required_fields=("project_id", "snapshot_id", "run_id", "evidence_register", "source_records", "transformations"),
        ),
        ContractDefinition(
            contract_id="evidence.ledger.v1",
            version="1.0.0-local-core",
            owner="Evidence Ledger Module",
            purpose="Dataset, transformation, and target evidence lineage.",
            required_fields=("project_id", "snapshot_id"),
        ),
        ContractDefinition(
            contract_id="sector.intelligence.build.v1",
            version="1.0.0-local-core",
            owner="Sector Intelligence Module",
            purpose="Command envelope for building local sector intelligence from closed inputs.",
            required_fields=("project_id", "snapshot_id", "run_id", "inputs", "evidence_register", "source_records"),
        ),
        ContractDefinition(
            contract_id="sector.intelligence.v1",
            version="1.0.0-local-core",
            owner="Sector Intelligence Module",
            purpose="Local sector taxonomy, criteria, and evidence mapping.",
            required_fields=("project_id", "snapshot_id"),
        ),
        ContractDefinition(
            contract_id="decision.council.evaluate.v1",
            version="1.0.0-local-core",
            owner="Decision Council Module",
            purpose="Command envelope for deterministic council evaluation from sealed upstream inputs.",
            required_fields=(
                "project_id",
                "run_id",
                "snapshot_id",
                "input_contract_id",
                "finance",
                "blockers",
                "readiness_gates",
                "sector_intelligence",
            ),
        ),
        ContractDefinition(
            contract_id="decision.council.v1",
            version="1.0.0-local-core",
            owner="Decision Council Module",
            purpose="Deterministic personas and sovereign verdict from sealed upstream envelopes without voting or AI.",
            required_fields=(
                "project_id",
                "run_id",
                "snapshot_id",
                "finance",
                "blockers",
                "readiness_gates",
                "sector_intelligence",
            ),
        ),
        ContractDefinition(
            contract_id="risk.register.build.v1",
            version="1.0.0-local-core",
            owner="Risk Engine Module",
            purpose="Command envelope for building a deterministic risk register.",
            required_fields=(
                "project_id",
                "run_id",
                "snapshot_id",
                "input_contract_id",
                "finance",
                "evidence_register",
                "source_policy",
                "readiness_gates",
            ),
        ),
        ContractDefinition(
            contract_id="risk.register.v1",
            version="1.0.0-local-core",
            owner="Risk Engine Module",
            purpose="Deterministic risk register from sealed finance, evidence, source policy, and readiness envelopes.",
            required_fields=(
                "project_id",
                "run_id",
                "snapshot_id",
                "finance",
                "evidence_register",
                "source_policy",
                "readiness_gates",
            ),
        ),
        ContractDefinition(
            contract_id="risk.advisory.summary.v1",
            version="1.0.0-local-core",
            owner="Risk Engine Module",
            purpose="Closed risk advisory summary for Execution without exposing the full risk register.",
            required_fields=(
                "risk_advisory_summary_id",
                "contract_id",
                "project_id",
                "run_id",
                "snapshot_id",
                "status",
                "risk_register_ref",
                "top_risk_ids",
                "blocked_risk_ids",
                "execution_constraints",
                "contains_full_risk_register",
            ),
        ),
        ContractDefinition(
            contract_id="execution.plan.build.v1",
            version="1.0.0-local-core",
            owner="Execution Engine Module",
            purpose="Command envelope for building an execution plan from closed advisory inputs.",
            required_fields=(
                "project_id",
                "run_id",
                "snapshot_id",
                "input_contract_id",
                "finance",
                "decision_council",
                "readiness_gates",
                "risk_advisory_summary",
            ),
        ),
        ContractDefinition(
            contract_id="execution.plan.v1",
            version="1.0.0-local-core",
            owner="Execution Engine Module",
            purpose="Deterministic execution plan from sealed finance, decision council, readiness, and risk advisory envelopes.",
            required_fields=(
                "project_id",
                "run_id",
                "snapshot_id",
                "finance",
                "decision_council",
                "readiness_gates",
                "risk_advisory_summary",
            ),
        ),
        ContractDefinition(
            contract_id="aas.sealed.module.output.v1",
            version="1.0.0-local-core",
            owner="Snapshot Assembly Module",
            purpose="Immutable run-scoped module output envelope with producer, contract, correlation, and integrity lineage.",
            required_fields=(
                "envelope_id",
                "output_key",
                "producer_module_id",
                "producer_contract_id",
                "producer_contract_version",
                "project_id",
                "run_id",
                "snapshot_id",
                "output",
                "output_hash",
                "sealed",
            ),
        ),
        ContractDefinition(
            contract_id="snapshot.projection.support.v1",
            version="1.0.0-local-core",
            owner="Heart Controller",
            purpose="Sealed non-engine context required to project dashboard and report from one assembled snapshot.",
            required_fields=("project_id", "run_id", "snapshot_id", "projection_support"),
        ),
        ContractDefinition(
            contract_id="snapshot.assemble.v1",
            version="1.0.0-local-core",
            owner="Snapshot Assembly Module",
            purpose="Validate sealed run outputs and assemble one immutable snapshot without recalculation or persistence.",
            required_fields=(
                "project_id",
                "run_id",
                "snapshot_id",
                "input_contract_id",
                "sealed_outputs",
                "project_context",
                "readiness_state",
                "blockers",
            ),
        ),
        ContractDefinition(
            contract_id="ai.integration.request.v1",
            version="1.0.0-local-shell",
            owner="AI Integration Module",
            purpose="Governed AI request attempt envelope; no provider execution is enabled.",
            required_fields=(
                "request_id",
                "project_id",
                "run_id",
                "snapshot_id",
                "input_contract_id",
                "purpose",
                "prompt_class",
                "prompt_template_id",
                "prompt_hash",
                "requested_output_types",
                "context_refs",
            ),
        ),
        ContractDefinition(
            contract_id="ai.integration.result.v1",
            version="1.0.0-local-shell",
            owner="AI Integration Module",
            purpose="Governance, routing, validation, human-review, and audit result with no generated AI output.",
            required_fields=(
                "request_id",
                "project_id",
                "run_id",
                "snapshot_id",
                "status",
                "prompt_governance",
                "routing",
                "human_review_gate",
                "audit_event",
            ),
        ),
        ContractDefinition(
            contract_id="decision.pack.project.v1",
            version="1.0.0-local-core",
            owner="Decision Pack Module",
            purpose="Command envelope for projecting a decision pack from a saved immutable snapshot and report.",
            required_fields=(
                "project_id",
                "run_id",
                "snapshot_id",
                "input_contract_id",
                "snapshot_overview",
                "snapshot_report",
            ),
        ),
        ContractDefinition(
            contract_id="decision.pack.v1",
            version="1.0.0-local-core",
            owner="Decision Pack Module",
            purpose="Decision pack base projection from one immutable saved snapshot and its matching report, without review overlay.",
            required_fields=(
                "project_id",
                "run_id",
                "snapshot_id",
                "input_contract_id",
                "snapshot_overview",
                "snapshot_report",
            ),
        ),
        ContractDefinition(
            contract_id="report.snapshot.project.v1",
            version="1.0.0-local-core",
            owner="Report Module",
            purpose="Command envelope for projecting a report from a sealed snapshot overview.",
            required_fields=("project_id", "run_id", "snapshot_id", "input_contract_id", "overview"),
        ),
        ContractDefinition(
            contract_id="report.snapshot.v1",
            version="1.0.0-local-core",
            owner="Report Module",
            purpose="Snapshot report package from a sealed overview without recalculation or repository reads.",
            required_fields=("project_id", "run_id", "snapshot_id", "overview"),
        ),
    )


def default_sockets() -> tuple[SocketDefinition, ...]:
    return (
        SocketDefinition(
            socket_id="socket.kernel.boot",
            contract_id="aas.kernel.boot.v1",
            provider_module_id="aas.kernel",
        ),
        SocketDefinition(
            socket_id="socket.registry.snapshot",
            contract_id="aas.registry.snapshot.v1",
            provider_module_id="aas.registry",
        ),
        SocketDefinition(
            socket_id="socket.heart.status",
            contract_id="aas.heart.status.v1",
            provider_module_id="aas.heart_controller",
        ),
        SocketDefinition(
            socket_id="socket.heart.assignment",
            contract_id="aas.heart.assignment.v1",
            provider_module_id="aas.heart_controller",
        ),
        SocketDefinition(
            socket_id="socket.bus.status",
            contract_id="aas.bus.status.v1",
            provider_module_id="aas.bus_controller",
        ),
        SocketDefinition(
            socket_id="socket.bus.message",
            contract_id="aas.bus.message.v1",
            provider_module_id="aas.system_bus",
        ),
        SocketDefinition(
            socket_id="socket.contract.enforcement",
            contract_id="aas.socket.enforcement.v1",
            provider_module_id="aas.socket_contract_layer",
        ),
        SocketDefinition(
            socket_id="socket.module.execution",
            contract_id="aas.module.execution.v1",
            provider_module_id="aas.module_runtime",
        ),
        SocketDefinition(
            socket_id="socket.project.run",
            contract_id="project.run.workflow.v1",
            provider_module_id="module.project_run_workflow",
        ),
        SocketDefinition(
            socket_id="socket.finance.evaluate",
            contract_id="finance.calculate.v1",
            provider_module_id="module.finance",
        ),
        SocketDefinition(
            socket_id="socket.evidence.ledger",
            contract_id="evidence.ledger.build.v1",
            provider_module_id="module.evidence_ledger",
        ),
        SocketDefinition(
            socket_id="socket.sector.intelligence",
            contract_id="sector.intelligence.build.v1",
            provider_module_id="module.sector_intelligence",
        ),
        SocketDefinition(
            socket_id="socket.decision.council",
            contract_id="decision.council.evaluate.v1",
            provider_module_id="module.decision_council",
        ),
        SocketDefinition(
            socket_id="socket.risk.register",
            contract_id="risk.register.build.v1",
            provider_module_id="module.risk_engine",
        ),
        SocketDefinition(
            socket_id="socket.execution.plan",
            contract_id="execution.plan.build.v1",
            provider_module_id="module.execution_engine",
        ),
        SocketDefinition(
            socket_id="socket.snapshot.assemble",
            contract_id="snapshot.assemble.v1",
            provider_module_id="module.snapshot_assembly",
        ),
        SocketDefinition(
            socket_id="socket.ai.integration",
            contract_id="ai.integration.request.v1",
            provider_module_id="module.ai_integration",
        ),
        SocketDefinition(
            socket_id="socket.decision.pack",
            contract_id="decision.pack.project.v1",
            provider_module_id="module.decision_pack",
        ),
        SocketDefinition(
            socket_id="socket.report.snapshot",
            contract_id="report.snapshot.project.v1",
            provider_module_id="module.reports",
        ),
    )


def default_modules() -> tuple[ModuleDefinition, ...]:
    return (
        ModuleDefinition(
            module_id="aas.kernel",
            label="ASIE Kernel",
            module_type="runtime",
            owner_file="backend/aas_kernel.py",
            provides=("socket.kernel.boot",),
            notes=("Boots runtime only.", "Contains no business calculations."),
        ),
        ModuleDefinition(
            module_id="aas.registry",
            label="AAS Registry",
            module_type="runtime",
            owner_file="backend/aas_registry.py",
            provides=("socket.registry.snapshot",),
            notes=("Registers contracts, sockets, and module descriptors.",),
        ),
        ModuleDefinition(
            module_id="aas.heart_controller",
            label="Heart Controller",
            module_type="runtime",
            owner_file="backend/heart_controller.py",
            provides=("socket.heart.status", "socket.heart.assignment"),
            notes=("Controls Primary, Assist, and Reserve hearts.", "Does not execute business logic."),
        ),
        ModuleDefinition(
            module_id="aas.heart.M1",
            label="Primary Heart M1",
            module_type="runtime",
            owner_file="backend/hearts.py",
            notes=("Assigned only by Heart Controller.", "Does not execute business logic."),
        ),
        ModuleDefinition(
            module_id="aas.heart.M2",
            label="Assist Heart M2",
            module_type="runtime",
            owner_file="backend/hearts.py",
            notes=("Assigned only by Heart Controller when assist is required.", "Does not execute business logic."),
        ),
        ModuleDefinition(
            module_id="aas.heart.M3",
            label="Reserve Heart M3",
            module_type="runtime",
            owner_file="backend/hearts.py",
            notes=("Reserve failover identity controlled by Heart Controller.", "Does not execute business logic."),
        ),
        ModuleDefinition(
            module_id="aas.bus_controller",
            label="Bus Controller",
            module_type="runtime",
            owner_file="backend/bus_controller.py",
            provides=("socket.bus.status",),
            notes=("Admits or rejects runtime messages.", "Does not execute business logic."),
        ),
        ModuleDefinition(
            module_id="aas.system_bus",
            label="ASIE System Bus",
            module_type="runtime",
            owner_file="backend/system_bus.py",
            provides=("socket.bus.message",),
            notes=("Transports accepted messages only.", "Does not call product engines in package 3."),
        ),
        ModuleDefinition(
            module_id="aas.socket_contract_layer",
            label="Socket Contract Layer",
            module_type="runtime",
            owner_file="backend/socket_contracts.py",
            provides=("socket.contract.enforcement",),
            notes=("Enforces Socket First, Module Second.", "Does not execute business logic."),
        ),
        ModuleDefinition(
            module_id="aas.module_runtime",
            label="Module Runtime",
            module_type="runtime",
            owner_file="backend/module_runtime.py",
            provides=("socket.module.execution",),
            notes=("Executes registered module handlers only after Bus and Socket checks.",),
        ),
        ModuleDefinition(
            module_id="module.project_run_workflow",
            label="Project Run Workflow",
            module_type="runtime",
            owner_file="backend/project_run_workflow.py",
            provides=("socket.project.run",),
            requires=(
                "socket.finance.evaluate",
                "socket.evidence.ledger",
                "socket.sector.intelligence",
                "socket.decision.council",
                "socket.risk.register",
                "socket.execution.plan",
                "socket.snapshot.assemble",
                "socket.report.snapshot",
            ),
            notes=(
                "Owns project run admission and idempotency context.",
                "Dispatches only through Bus/Socket and does not own product facts.",
            ),
        ),
        ModuleDefinition(
            module_id="module.finance",
            label="Finance Module",
            module_type="product_engine_descriptor",
            owner_file="backend/finance_engine.py",
            provides=("socket.finance.evaluate",),
            notes=("Descriptor only in package 1; wrapping happens later.",),
        ),
        ModuleDefinition(
            module_id="module.evidence_ledger",
            label="Evidence Ledger Module",
            module_type="product_engine_descriptor",
            owner_file="backend/evidence_ledger.py",
            provides=("socket.evidence.ledger",),
            notes=("Descriptor only in package 1; wrapping happens later.",),
        ),
        ModuleDefinition(
            module_id="module.sector_intelligence",
            label="Sector Intelligence Module",
            module_type="product_engine_descriptor",
            owner_file="backend/sector_intelligence.py",
            provides=("socket.sector.intelligence",),
            notes=("Descriptor only in package 1; wrapping happens later.",),
        ),
        ModuleDefinition(
            module_id="module.decision_council",
            label="Decision Council Module",
            module_type="product_engine_descriptor",
            owner_file="backend/decision_council.py",
            provides=("socket.decision.council",),
            notes=("Descriptor only in package 1; no AI and no voting.",),
        ),
        ModuleDefinition(
            module_id="module.risk_engine",
            label="Risk Engine Module",
            module_type="product_engine_descriptor",
            owner_file="backend/risk_engine.py",
            provides=("socket.risk.register",),
            notes=("Descriptor only in package 5; independent from Execution Engine.",),
        ),
        ModuleDefinition(
            module_id="module.execution_engine",
            label="Execution Engine Module",
            module_type="product_engine_descriptor",
            owner_file="backend/execution_engine.py",
            provides=("socket.execution.plan",),
            notes=("Descriptor only in package 6; independent from Risk Engine.",),
        ),
        ModuleDefinition(
            module_id="module.snapshot_assembly",
            label="Snapshot Assembly Module",
            module_type="product_engine_descriptor",
            owner_file="backend/snapshot_assembly.py",
            provides=("socket.snapshot.assemble",),
            requires=(
                "socket.finance.evaluate",
                "socket.evidence.ledger",
                "socket.sector.intelligence",
                "socket.decision.council",
                "socket.risk.register",
                "socket.execution.plan",
            ),
            notes=(
                "Validates sealed outputs and assembles immutable snapshots only.",
                "Does not call engines, recalculate, persist, fetch, or invoke AI.",
            ),
        ),
        ModuleDefinition(
            module_id="module.ai_integration",
            label="AI Integration Shell",
            module_type="product_engine_descriptor",
            owner_file="backend/ai_integration.py",
            provides=("socket.ai.integration",),
            notes=(
                "Governed shell only: provider registry is empty and model routing is disabled.",
                "Cannot own controlled numbers, finance, legal interpretation, source activation, or sovereign verdicts.",
            ),
        ),
        ModuleDefinition(
            module_id="module.decision_pack",
            label="Decision Pack Module",
            module_type="product_engine_descriptor",
            owner_file="backend/decision_pack.py",
            provides=("socket.decision.pack",),
            requires=("socket.snapshot.assemble", "socket.report.snapshot"),
            notes=(
                "Projects an immutable saved snapshot only.",
                "Review overlay is applied outside the module and does not change snapshot or decision pack base hashes.",
            ),
        ),
        ModuleDefinition(
            module_id="module.reports",
            label="Report Module",
            module_type="product_engine_descriptor",
            owner_file="backend/reports.py",
            provides=("socket.report.snapshot",),
            notes=("Descriptor only in package 1; reports read snapshots.",),
        ),
    )
