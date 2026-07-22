from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, Callable

from backend.aas_kernel import AASKernel
from backend.aas_registry import UnknownRegistrationError
from backend.ai_integration import AIIntegrationError, AIIntegrationShell
from backend.contracts import new_id, now_iso
from backend.decision_council import evaluate_decision_council
from backend.decision_pack import build_decision_pack_base
from backend.evidence_ledger import build_evidence_ledger
from backend.execution_engine import build_execution_plan
from backend.finance_engine import finance_result_set
from backend.reports import build_report
from backend.risk_engine import build_risk_advisory_summary, build_risk_register
from backend.sector_intelligence import build_sector_intelligence
from backend.snapshot_assembly import assemble_snapshot, seal_module_output
from backend.system_bus import BusMessage, SystemBus


class ModuleRuntimeError(ValueError):
    pass


ModuleHandler = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True)
class ModuleExecutionResult:
    runtime_id: str
    module_id: str
    message_id: str
    status: str
    output: dict[str, Any]
    bus_record: dict[str, Any]
    executed_at: str

    def to_public(self) -> dict[str, Any]:
        return {
            "runtime_id": self.runtime_id,
            "module_id": self.module_id,
            "message_id": self.message_id,
            "status": self.status,
            "output": self.output,
            "bus_record": self.bus_record,
            "executed_at": self.executed_at,
            "guards": {
                "executed_after_bus_delivery": self.bus_record.get("delivered") is True,
                "external_fetch_enabled": False,
                "ai_enabled": False,
            },
        }


class ProjectRunWorkflowModuleAdapter:
    module_id = "module.project_run_workflow"
    allowed_inputs = frozenset(
        {
            "project_id",
            "scenario_id",
            "operation_id",
            "idempotency_key",
            "input_hash",
            "requested_at",
            "input_contract_id",
        }
    )

    def handle(self, payload: dict[str, Any]) -> dict[str, Any]:
        missing = self.allowed_inputs - set(payload)
        extra = set(payload) - self.allowed_inputs
        if missing:
            raise ModuleRuntimeError("Project Run Workflow input is missing fields: " + ", ".join(sorted(missing)))
        if extra:
            raise ModuleRuntimeError("Project Run Workflow received forbidden fields: " + ", ".join(sorted(extra)))
        if payload["input_contract_id"] != "ProjectRunHttpRequest.v1":
            raise ModuleRuntimeError("Project Run Workflow requires ProjectRunHttpRequest.v1")
        return {
            "module_id": self.module_id,
            "contract_id": "project.run.workflow.v1",
            "input_contract_id": "ProjectRunHttpRequest.v1",
            "project_id": payload["project_id"],
            "scenario_id": payload["scenario_id"],
            "operation_id": payload["operation_id"],
            "idempotency_key": payload["idempotency_key"],
            "input_hash": payload["input_hash"],
            "status": "accepted",
            "run_context_closed": True,
            "dispatch_owner": "Project Run Workflow",
            "external_fetch_enabled": False,
            "ai_enabled": False,
        }


class FinanceModuleAdapter:
    module_id = "module.finance"

    def handle(self, payload: dict[str, Any]) -> dict[str, Any]:
        finance, blockers = finance_result_set(payload.get("inputs", {}))
        if payload.get("assumption_refs"):
            finance["assumption_refs"] = list(payload["assumption_refs"])
        return {
            "module_id": self.module_id,
            "contract_id": "finance.result.v1",
            "project_id": payload["project_id"],
            "run_id": payload["run_id"],
            "snapshot_id": payload["snapshot_id"],
            "finance": finance,
            "blockers": blockers,
            "external_fetch_enabled": False,
            "ai_enabled": False,
        }


class EvidenceLedgerModuleAdapter:
    module_id = "module.evidence_ledger"

    def handle(self, payload: dict[str, Any]) -> dict[str, Any]:
        ledger = build_evidence_ledger(
            payload["evidence_register"],
            payload["source_records"],
            payload["snapshot_id"],
            payload.get("run_id"),
            payload.get("transformations", []),
        )
        return {
            "module_id": self.module_id,
            "contract_id": "evidence.ledger.v1",
            "project_id": payload["project_id"],
            "snapshot_id": payload["snapshot_id"],
            "run_id": payload.get("run_id"),
            "evidence_ledger": ledger,
            "external_fetch_enabled": False,
            "ai_enabled": False,
        }


class SectorIntelligenceModuleAdapter:
    module_id = "module.sector_intelligence"

    def handle(self, payload: dict[str, Any]) -> dict[str, Any]:
        project = SimpleNamespace(
            project_id=payload["project_id"],
            name=payload.get("project_name", ""),
            sector=payload.get("project_sector", ""),
            jurisdiction=payload.get("project_jurisdiction", ""),
            inputs=payload.get("inputs", {}),
        )
        sector_intelligence = build_sector_intelligence(
            project,
            payload["evidence_register"],
            payload["source_records"],
        )
        return {
            "module_id": self.module_id,
            "contract_id": "sector.intelligence.v1",
            "project_id": payload["project_id"],
            "snapshot_id": payload["snapshot_id"],
            "run_id": payload.get("run_id"),
            "sector_intelligence": sector_intelligence,
            "external_fetch_enabled": False,
            "ai_enabled": False,
        }


class DecisionCouncilModuleAdapter:
    module_id = "module.decision_council"
    forbidden_inputs = ("risk_register", "execution_plan", "repository", "repo")

    def handle(self, payload: dict[str, Any]) -> dict[str, Any]:
        forbidden = [field for field in self.forbidden_inputs if field in payload]
        if forbidden:
            raise ModuleRuntimeError("Decision Council received forbidden downstream inputs: " + ", ".join(forbidden))
        decision_council = evaluate_decision_council(
            payload["finance"],
            payload["blockers"],
            payload["readiness_gates"],
            payload["sector_intelligence"],
        )
        return {
            "module_id": self.module_id,
            "contract_id": "decision.council.v1",
            "input_contract_id": "DecisionCouncilInputEnvelope.v1",
            "project_id": payload["project_id"],
            "snapshot_id": payload["snapshot_id"],
            "run_id": payload["run_id"],
            "decision_council": decision_council,
            "external_fetch_enabled": False,
            "ai_enabled": False,
            "forbidden_downstream_inputs": list(self.forbidden_inputs),
        }


class RiskEngineModuleAdapter:
    module_id = "module.risk_engine"
    forbidden_inputs = ("execution_plan", "decision_council", "repository", "repo")

    def handle(self, payload: dict[str, Any]) -> dict[str, Any]:
        forbidden = [field for field in self.forbidden_inputs if field in payload]
        if forbidden:
            raise ModuleRuntimeError("Risk Engine received forbidden downstream or unrelated inputs: " + ", ".join(forbidden))
        risk_register = build_risk_register(
            payload["finance"],
            payload["evidence_register"],
            payload["source_policy"],
            payload["readiness_gates"],
            project_id=payload["project_id"],
            run_id=payload["run_id"],
            snapshot_id=payload["snapshot_id"],
        )
        risk_advisory_summary = build_risk_advisory_summary(
            risk_register,
            project_id=payload["project_id"],
            run_id=payload["run_id"],
            snapshot_id=payload["snapshot_id"],
        )
        return {
            "module_id": self.module_id,
            "contract_id": "risk.register.v1",
            "advisory_contract_id": "risk.advisory.summary.v1",
            "input_contract_id": "RiskRegisterInputEnvelope.v1",
            "project_id": payload["project_id"],
            "snapshot_id": payload["snapshot_id"],
            "run_id": payload["run_id"],
            "risk_register": risk_register,
            "risk_advisory_summary": risk_advisory_summary,
            "external_fetch_enabled": False,
            "ai_enabled": False,
            "forbidden_inputs": list(self.forbidden_inputs),
        }


class ExecutionEngineModuleAdapter:
    module_id = "module.execution_engine"
    forbidden_inputs = ("risk_register", "repository", "repo")
    advisory_allowed_fields = frozenset(
        {
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
            "source",
            "contains_full_risk_register",
        }
    )
    advisory_constraint_allowed_fields = frozenset(
        {
            "risk_id",
            "severity",
            "trigger",
            "owner_role",
        }
    )

    def handle(self, payload: dict[str, Any]) -> dict[str, Any]:
        forbidden = [field for field in self.forbidden_inputs if field in payload]
        if forbidden:
            raise ModuleRuntimeError("Execution Engine received forbidden or unrelated inputs: " + ", ".join(forbidden))
        risk_advisory_summary = payload["risk_advisory_summary"]
        self.validate_risk_advisory_summary(risk_advisory_summary, payload)
        execution_plan = build_execution_plan(
            payload["finance"],
            payload["decision_council"],
            payload["readiness_gates"],
            risk_advisory_summary,
        )
        return {
            "module_id": self.module_id,
            "contract_id": "execution.plan.v1",
            "consumed_contract_ids": ["risk.advisory.summary.v1"],
            "input_contract_id": "ExecutionPlanInputEnvelope.v1",
            "project_id": payload["project_id"],
            "snapshot_id": payload["snapshot_id"],
            "run_id": payload["run_id"],
            "execution_plan": execution_plan,
            "external_fetch_enabled": False,
            "ai_enabled": False,
            "forbidden_inputs": list(self.forbidden_inputs),
        }

    def validate_risk_advisory_summary(self, summary: dict[str, Any], payload: dict[str, Any]) -> None:
        keys = set(summary)
        missing = self.advisory_allowed_fields - keys
        extra = keys - self.advisory_allowed_fields
        if missing:
            raise ModuleRuntimeError("Risk advisory summary is missing required fields: " + ", ".join(sorted(missing)))
        if extra:
            raise ModuleRuntimeError("Risk advisory summary contains forbidden fields: " + ", ".join(sorted(extra)))
        if summary.get("contract_id") != "risk.advisory.summary.v1":
            raise ModuleRuntimeError("Execution Engine requires risk.advisory.summary.v1")
        if summary.get("contains_full_risk_register") is not False:
            raise ModuleRuntimeError("Execution Engine requires closed risk advisory summary, not full risk register")
        for identity_field in ("project_id", "run_id", "snapshot_id"):
            if summary.get(identity_field) != payload.get(identity_field):
                raise ModuleRuntimeError(f"Risk advisory summary {identity_field} does not match execution payload")
        if not str(summary.get("risk_advisory_summary_id", "")).startswith("risk-advisory:"):
            raise ModuleRuntimeError("Risk advisory summary id must use risk-advisory identity")
        if not str(summary.get("risk_register_ref", "")).startswith("risk-register:"):
            raise ModuleRuntimeError("Risk advisory summary must reference a sealed risk register id")
        for list_field in ("top_risk_ids", "blocked_risk_ids", "execution_constraints"):
            if not isinstance(summary.get(list_field), list):
                raise ModuleRuntimeError(f"Risk advisory summary {list_field} must be a list")
        for constraint in summary["execution_constraints"]:
            if not isinstance(constraint, dict):
                raise ModuleRuntimeError("Risk advisory execution constraints must be objects")
            constraint_keys = set(constraint)
            extra_constraint_keys = constraint_keys - self.advisory_constraint_allowed_fields
            missing_constraint_keys = self.advisory_constraint_allowed_fields - constraint_keys
            if missing_constraint_keys:
                raise ModuleRuntimeError(
                    "Risk advisory execution constraint is missing fields: "
                    + ", ".join(sorted(missing_constraint_keys))
                )
            if extra_constraint_keys:
                raise ModuleRuntimeError(
                    "Risk advisory execution constraint contains forbidden fields: "
                    + ", ".join(sorted(extra_constraint_keys))
                )


class ReportModuleAdapter:
    module_id = "module.reports"
    forbidden_inputs = ("repository", "repo", "latest_review", "reviews", "decision_pack")

    def handle(self, payload: dict[str, Any]) -> dict[str, Any]:
        forbidden = [field for field in self.forbidden_inputs if field in payload]
        if forbidden:
            raise ModuleRuntimeError("Report Module received forbidden external review or repository inputs: " + ", ".join(forbidden))
        report = build_report(payload["overview"])
        return {
            "module_id": self.module_id,
            "contract_id": "report.snapshot.v1",
            "input_contract_id": "SnapshotReportInputEnvelope.v1",
            "project_id": payload["project_id"],
            "snapshot_id": payload["snapshot_id"],
            "run_id": payload["run_id"],
            "report": report,
            "external_fetch_enabled": False,
            "ai_enabled": False,
            "forbidden_inputs": list(self.forbidden_inputs),
        }


class DecisionPackModuleAdapter:
    module_id = "module.decision_pack"
    allowed_inputs = frozenset(
        {
            "project_id",
            "run_id",
            "snapshot_id",
            "input_contract_id",
            "snapshot_overview",
            "snapshot_report",
        }
    )

    def handle(self, payload: dict[str, Any]) -> dict[str, Any]:
        missing = self.allowed_inputs - set(payload)
        extra = set(payload) - self.allowed_inputs
        if missing:
            raise ModuleRuntimeError("Decision Pack input is missing fields: " + ", ".join(sorted(missing)))
        if extra:
            raise ModuleRuntimeError("Decision Pack received forbidden live or review inputs: " + ", ".join(sorted(extra)))
        if payload["input_contract_id"] != "DecisionPackInputEnvelope.v1":
            raise ModuleRuntimeError("Decision Pack requires DecisionPackInputEnvelope.v1")
        overview = payload["snapshot_overview"]
        for identity_field, actual in (
            ("project_id", overview.get("project", {}).get("project_id")),
            ("run_id", overview.get("run", {}).get("run_id")),
            ("snapshot_id", overview.get("snapshot", {}).get("snapshot_id")),
        ):
            if actual != payload[identity_field]:
                raise ModuleRuntimeError(f"Decision Pack {identity_field} does not match snapshot input")
        try:
            decision_pack = build_decision_pack_base(overview, payload["snapshot_report"])
        except ValueError as exc:
            raise ModuleRuntimeError(str(exc)) from exc
        return {
            "module_id": self.module_id,
            "contract_id": "decision.pack.v1",
            "input_contract_id": "DecisionPackInputEnvelope.v1",
            "project_id": payload["project_id"],
            "run_id": payload["run_id"],
            "snapshot_id": payload["snapshot_id"],
            "decision_pack": decision_pack,
            "external_fetch_enabled": False,
            "ai_enabled": False,
            "review_overlay_included": False,
        }


class AIIntegrationModuleAdapter:
    module_id = "module.ai_integration"

    def __init__(self) -> None:
        self.shell = AIIntegrationShell()

    def handle(self, payload: dict[str, Any]) -> dict[str, Any]:
        if payload.get("input_contract_id") != "AIIntegrationInputEnvelope.v1":
            self.shell.audit_security_event(
                reason="invalid_ai_input_contract",
                request=payload,
                metadata={
                    "received_input_contract_id": payload.get("input_contract_id"),
                    "required_input_contract_id": "AIIntegrationInputEnvelope.v1",
                },
            )
            raise ModuleRuntimeError("AI Integration requires AIIntegrationInputEnvelope.v1")
        request = {key: value for key, value in payload.items() if key != "input_contract_id"}
        try:
            result = self.shell.process(request)
        except AIIntegrationError as exc:
            raise ModuleRuntimeError(str(exc)) from exc
        return {
            "module_id": self.module_id,
            "contract_id": "ai.integration.result.v1",
            "input_contract_id": "AIIntegrationInputEnvelope.v1",
            "project_id": payload["project_id"],
            "run_id": payload["run_id"],
            "snapshot_id": payload["snapshot_id"],
            "ai_result": result,
            "external_fetch_enabled": False,
            "ai_provider_enabled": False,
        }


class SnapshotAssemblyModuleAdapter:
    module_id = "module.snapshot_assembly"
    forbidden_inputs = ("repository", "repo", "report", "decision_pack", "reviews")

    def handle(self, payload: dict[str, Any]) -> dict[str, Any]:
        forbidden = [field for field in self.forbidden_inputs if field in payload]
        if forbidden:
            raise ModuleRuntimeError(
                "Snapshot Assembly received forbidden persistence or projection inputs: " + ", ".join(forbidden)
            )
        try:
            snapshot = assemble_snapshot(payload)
        except ValueError as exc:
            raise ModuleRuntimeError(str(exc)) from exc
        return {
            "module_id": self.module_id,
            "contract_id": "snapshot.assemble.v1",
            "input_contract_id": "SnapshotAssemblyInputEnvelope.v1",
            "project_id": payload["project_id"],
            "run_id": payload["run_id"],
            "snapshot_id": payload["snapshot_id"],
            "assembled_snapshot": snapshot,
            "external_fetch_enabled": False,
            "ai_enabled": False,
            "forbidden_inputs": list(self.forbidden_inputs),
        }


class ModuleRuntime:
    runtime_id = "module_runtime"

    def __init__(self, kernel: AASKernel, bus: SystemBus) -> None:
        self.kernel = kernel
        self.bus = bus
        self.state = "created"
        self.created_at = now_iso()
        self.bootstrapped_at: str | None = None
        self.handlers: dict[str, ModuleHandler] = {}
        self.executions: list[ModuleExecutionResult] = []

    def bootstrap(self) -> dict[str, Any]:
        if self.kernel.state != "booted":
            raise ModuleRuntimeError("kernel must be booted before Module Runtime bootstrap")
        if self.bus.state != "ready":
            raise ModuleRuntimeError("System Bus must be ready before Module Runtime bootstrap")
        self.kernel.registry.validate_contract_payload(
            "aas.module.execution.v1",
            {
                "runtime_id": self.runtime_id,
                "module_id": "aas.module_runtime",
                "message_id": "bootstrap",
                "status": "ready",
            },
        )
        self.kernel.registry.assert_socket_contract("socket.module.execution", "aas.module.execution.v1")
        self.state = "ready"
        self.bootstrapped_at = now_iso()
        return self.status()

    def register_handler(self, module_id: str, handler: ModuleHandler) -> None:
        if self.state != "ready":
            raise ModuleRuntimeError("Module Runtime must be ready before handler registration")
        module = self.kernel.registry.module(module_id)
        if module.module_type not in {"product_engine_descriptor", "runtime"}:
            raise ModuleRuntimeError(f"module type is not executable: {module.module_type}")
        if module.external_fetch_enabled:
            raise ModuleRuntimeError("external fetch modules cannot be executed in local runtime")
        self.handlers[module_id] = handler

    def register_default_handlers(self) -> None:
        self.register_handler("module.project_run_workflow", ProjectRunWorkflowModuleAdapter().handle)
        self.register_handler("module.finance", FinanceModuleAdapter().handle)
        self.register_handler("module.evidence_ledger", EvidenceLedgerModuleAdapter().handle)
        self.register_handler("module.sector_intelligence", SectorIntelligenceModuleAdapter().handle)
        self.register_handler("module.decision_council", DecisionCouncilModuleAdapter().handle)
        self.register_handler("module.risk_engine", RiskEngineModuleAdapter().handle)
        self.register_handler("module.execution_engine", ExecutionEngineModuleAdapter().handle)
        self.register_handler("module.snapshot_assembly", SnapshotAssemblyModuleAdapter().handle)
        self.register_handler("module.reports", ReportModuleAdapter().handle)
        self.register_handler("module.decision_pack", DecisionPackModuleAdapter().handle)
        self.register_handler("module.ai_integration", AIIntegrationModuleAdapter().handle)

    def execute(self, message: BusMessage) -> ModuleExecutionResult:
        if self.state != "ready":
            raise ModuleRuntimeError("Module Runtime must be ready before execution")
        try:
            self.kernel.registry.module(message.target_module_id)
        except UnknownRegistrationError as exc:
            raise ModuleRuntimeError(str(exc)) from exc
        handler = self.handlers.get(message.target_module_id)
        if handler is None:
            raise ModuleRuntimeError(f"no handler registered for module: {message.target_module_id}")

        bus_record = self.bus.publish(message)
        output = handler(message.payload)
        result = ModuleExecutionResult(
            runtime_id=self.runtime_id,
            module_id=message.target_module_id,
            message_id=message.message_id,
            status="completed",
            output=output,
            bus_record=bus_record,
            executed_at=now_iso(),
        )
        self.executions.append(result)
        return result

    def status(self) -> dict[str, Any]:
        return {
            "runtime_id": self.runtime_id,
            "state": self.state,
            "created_at": self.created_at,
            "bootstrapped_at": self.bootstrapped_at,
            "registered_handlers": sorted(self.handlers),
            "execution_count": len(self.executions),
            "last_execution": self.executions[-1].to_public() if self.executions else None,
            "guards": {
                "requires_bus_delivery": True,
                "requires_registered_handler": True,
                "external_fetch_enabled": False,
                "ai_enabled": False,
            },
        }


class RunScopedModuleRuntime:
    def __init__(
        self,
        runtime: ModuleRuntime,
        *,
        project_id: str,
        run_id: str,
        snapshot_id: str,
        source_module_id: str = "aas.heart_controller",
        operation_id: str = "",
        idempotency_key: str = "",
        input_hash: str = "",
    ) -> None:
        if runtime.state != "ready":
            raise ModuleRuntimeError("run-scoped runtime requires a ready Module Runtime")
        try:
            runtime.kernel.registry.module(source_module_id)
        except UnknownRegistrationError as exc:
            raise ModuleRuntimeError(str(exc)) from exc
        self.runtime = runtime
        self.project_id = project_id
        self.run_id = run_id
        self.snapshot_id = snapshot_id
        self.source_module_id = source_module_id
        self.operation_id = operation_id or new_id("op")
        self.idempotency_key = idempotency_key or new_id("idem")
        self.input_hash = input_hash or f"run-scoped:{project_id}:{run_id}:{snapshot_id}"
        self.sealed_outputs: dict[str, dict[str, Any]] = {}
        self.assembled = False

    def execute_and_seal(self, output_key: str, message: BusMessage) -> ModuleExecutionResult:
        if self.assembled:
            raise ModuleRuntimeError("run-scoped runtime cannot execute modules after snapshot assembly")
        for identity_field, expected in (
            ("project_id", self.project_id),
            ("run_id", self.run_id),
            ("snapshot_id", self.snapshot_id),
        ):
            if message.payload.get(identity_field) != expected:
                raise ModuleRuntimeError(f"run-scoped message {identity_field} mismatch")
        for envelope_field, expected in (
            ("operation_id", self.operation_id),
            ("idempotency_key", self.idempotency_key),
            ("input_hash", self.input_hash),
        ):
            if getattr(message, envelope_field) != expected:
                raise ModuleRuntimeError(f"run-scoped message {envelope_field} mismatch")
        if output_key in self.sealed_outputs:
            raise ModuleRuntimeError(f"run-scoped output already sealed: {output_key}")
        result = self.runtime.execute(message)
        result_contract_id = str(result.output.get("contract_id") or "")
        if not result_contract_id:
            raise ModuleRuntimeError("module output is missing result contract_id")
        contract = self.runtime.kernel.registry.contract(result_contract_id)
        self.sealed_outputs[output_key] = seal_module_output(
            output_key=output_key,
            producer_module_id=result.module_id,
            producer_contract_id=result_contract_id,
            producer_contract_version=contract.version,
            project_id=self.project_id,
            run_id=self.run_id,
            snapshot_id=self.snapshot_id,
            message_id=result.message_id,
            correlation_id=message.correlation_id,
            audit_ref=message.audit_ref,
            produced_at=result.executed_at,
            output=result.output,
        )
        return result

    def assemble(
        self,
        *,
        project_context: dict[str, Any],
        readiness_state: dict[str, Any],
        blockers: list[dict[str, Any]],
        sealed_supporting_outputs: list[dict[str, Any]] | None = None,
    ) -> ModuleExecutionResult:
        if self.assembled:
            raise ModuleRuntimeError("run-scoped snapshot has already been assembled")
        result = self.runtime.execute(
            BusMessage(
                source_module_id=self.source_module_id,
                target_module_id="module.snapshot_assembly",
                contract_id="snapshot.assemble.v1",
                socket_id="socket.snapshot.assemble",
                correlation_id=f"corr:{self.run_id}:snapshot-assembly",
                audit_ref=f"audit:{self.snapshot_id}:snapshot-assembly",
                operation_id=self.operation_id,
                idempotency_key=self.idempotency_key,
                input_hash=self.input_hash,
                payload={
                    "project_id": self.project_id,
                    "run_id": self.run_id,
                    "snapshot_id": self.snapshot_id,
                    "input_contract_id": "SnapshotAssemblyInputEnvelope.v1",
                    "sealed_outputs": list(self.sealed_outputs.values()),
                    "project_context": project_context,
                    "readiness_state": readiness_state,
                    "blockers": blockers,
                    "sealed_supporting_outputs": sealed_supporting_outputs or [],
                },
            )
        )
        self.assembled = True
        return result


def bootstrap_module_runtime(kernel: AASKernel, bus: SystemBus) -> ModuleRuntime:
    runtime = ModuleRuntime(kernel, bus)
    runtime.bootstrap()
    return runtime
