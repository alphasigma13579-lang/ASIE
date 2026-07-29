from __future__ import annotations

import threading
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Protocol

from backend.contracts import new_id, now_iso
from backend.dib_manifest_run_readiness import build_manifest_run_readiness
from backend.dib_persistence import DIBPersistenceStore, _payload_hash
from backend.dib_server_owned_manifest_chain import SERVER_AUTHORITY
from backend.dib_tenant_boundary import DIBTenantContext
from backend.heart_controller import HeartTask
from backend.project_run_workflow import ProjectRunIdempotencyStore, ProjectRunWorkflow
from backend.repository import ASSUMPTION_META, SYSTEM_CONTEXT_INPUT_KEYS, ProjectRecord, Repository
from backend.snapshot_assembly import canonical_hash

DIB_CANONICAL_FINANCE_ADMISSION_ID = "ARCH-BETA-05-CANONICAL-FINANCE-ADMISSION-v1"
DIB_CANONICAL_FINANCE_ADMISSION_STATUS = "project_run_workflow_only"


class DIBCanonicalFinanceAdmissionError(ValueError):
    def __init__(self, code: str, status: int = 422) -> None:
        super().__init__(code)
        self.code = code
        self.status = status


class CanonicalProjectRunExecutor(Protocol):
    def execute(
        self,
        *,
        project: ProjectRecord,
        data_access: "ManifestBackedProjectRunDataAccess",
        request: dict[str, Any],
    ) -> dict[str, Any]: ...


@dataclass(frozen=True)
class CanonicalFinanceAdmissionCommand:
    scenario_id: str = "baseline"
    operation_id: str | None = None
    idempotency_key: str | None = None
    expected_manifest_id: str | None = None
    expected_manifest_payload_hash: str | None = None
    expected_gate_id: str | None = None
    expected_gate_payload_hash: str | None = None


class ManifestBackedProjectRunDataAccess:
    """Read-only data-access overlay for one server-owned Manifest execution.

    The primary Repository remains authoritative for sources, datasets, evidence
    links, and transformations. Project assumptions are projected from the active
    Approved Input Manifest so the canonical pipeline never reads stale scalar
    assumptions for this run.
    """

    def __init__(self, repository: Repository, manifest: dict[str, Any]) -> None:
        self.repository = repository
        self.manifest = deepcopy(manifest)
        self.project_id = str(manifest.get("project_id") or "")
        self.manifest_id = str(manifest.get("manifest_id") or "")
        self._assumptions = self._build_assumptions()

    def _build_assumptions(self) -> list[dict[str, Any]]:
        normalized_inputs = dict(self.manifest.get("normalized_inputs") or {})
        item_by_key = {
            str(item.get("input_key") or ""): dict(item)
            for item in self.manifest.get("items") or []
            if isinstance(item, dict) and str(item.get("input_key") or "").strip()
        }
        assumptions: list[dict[str, Any]] = []
        for input_key in sorted(normalized_inputs):
            item = item_by_key.get(input_key, {})
            label, default_unit = ASSUMPTION_META.get(input_key, (input_key, "unit"))
            assumptions.append(
                {
                    "assumption_id": f"assumption:{self.project_id}:manifest:{self.manifest_id}:{input_key}",
                    "project_id": self.project_id,
                    "input_key": input_key,
                    "label": str(item.get("label") or label),
                    "value": normalized_inputs[input_key],
                    "unit": str(item.get("unit") or default_unit),
                    "owner": "Approved Input Manifest",
                    "source_type": str(item.get("source_type") or item.get("value_source") or "approved_input_manifest"),
                    "confidence": float(item.get("confidence") if item.get("confidence") is not None else 1.0),
                    "review_status": "approved",
                    "manifest_id": self.manifest_id,
                    "blueprint_id": str(self.manifest.get("blueprint_id") or ""),
                }
            )
        return assumptions

    def project_assumptions(self, project_id: str) -> list[dict[str, Any]]:
        if project_id != self.project_id:
            raise DIBCanonicalFinanceAdmissionError("manifest_data_access_project_mismatch", 409)
        return deepcopy(self._assumptions)

    def source_records(self) -> list[dict[str, Any]]:
        return self.repository.source_records()

    def project_evidence_links(self, project_id: str) -> list[dict[str, Any]]:
        return self.repository.project_evidence_links(project_id)

    def datasets(self) -> list[dict[str, Any]]:
        return self.repository.datasets()

    def project_transformations(self, project_id: str) -> list[dict[str, Any]]:
        return self.repository.project_transformations(project_id)


class LocalProjectRunWorkflowExecutor:
    """Executes through the frozen ProjectRunWorkflow without modifying it."""

    def __init__(
        self,
        repository: Repository,
        *,
        idempotency_store: ProjectRunIdempotencyStore | None = None,
    ) -> None:
        self.repository = repository
        self.idempotency_store = idempotency_store or ProjectRunIdempotencyStore()
        self._execution_lock = threading.RLock()

    def execute(
        self,
        *,
        project: ProjectRecord,
        data_access: ManifestBackedProjectRunDataAccess,
        request: dict[str, Any],
    ) -> dict[str, Any]:
        # Lazy import prevents DIB module initialization from owning or mutating
        # the frozen runtime. The existing local runtime factory remains the only
        # runtime bootstrap owner.
        from backend.asie_local_api import (
            execute_project_run_pipeline,
            heart_source_module_id,
            local_runtime_context,
        )

        with self._execution_lock:
            context = local_runtime_context()
            heart_assignment = context.heart_controller.assign_task(
                HeartTask(
                    task_id=request["operation_id"],
                    purpose="dib_canonical_project_run_admission",
                    requires_assist=False,
                )
            )
            source_module_id = heart_source_module_id(heart_assignment)
            workflow = ProjectRunWorkflow(
                context.runtime,
                self.idempotency_store,
                source_module_id=source_module_id,
                heart_assignment=heart_assignment,
            )
            result = workflow.run(
                request,
                build=lambda run_envelope: execute_project_run_pipeline(
                    run_envelope,
                    project=project,
                    data_access=data_access,
                ),
                save=lambda overview, report: self.repository.save_run_snapshot(
                    project.project_id,
                    overview,
                    report,
                ),
            )
            return result.to_response()


class DIBCanonicalFinanceAdmission:
    """Admit a server-owned DIB chain to the canonical ProjectRunWorkflow.

    This class never imports or invokes Finance Engine directly. Finance executes
    only when the existing ProjectRunWorkflow delivers finance.calculate.v1 via
    Module Runtime, System Bus, and the Finance socket.
    """

    _ALLOWED_COMMAND_FIELDS = frozenset(
        {
            "scenario_id",
            "operation_id",
            "idempotency_key",
            "expected_manifest_id",
            "expected_manifest_payload_hash",
            "expected_gate_id",
            "expected_gate_payload_hash",
        }
    )
    _FORBIDDEN_CLIENT_FIELDS = frozenset(
        {
            "finance",
            "finance_result",
            "finance_inputs",
            "normalized_inputs",
            "manifest",
            "gate",
            "blueprint",
            "project_id",
            "session_id",
            "input_hash",
            "snapshot",
            "snapshot_id",
            "run_id",
            "workflow",
        }
    )

    def __init__(
        self,
        store: DIBPersistenceStore,
        repository: Repository,
        executor: CanonicalProjectRunExecutor,
    ) -> None:
        self.store = store
        self.repository = repository
        self.executor = executor

    def status(self) -> dict[str, Any]:
        return {
            "admission_id": DIB_CANONICAL_FINANCE_ADMISSION_ID,
            "status": DIB_CANONICAL_FINANCE_ADMISSION_STATUS,
            "accepted_source_contract": "approved.input.manifest.v1",
            "required_validation_contract": "manifest.validation.v1",
            "project_run_workflow_contract": "project.run.workflow.v1",
            "finance_command_contract": "finance.calculate.v1",
            "direct_finance_import": False,
            "direct_finance_execution_enabled": False,
            "canonical_project_run_execution_enabled": True,
            "project_run_workflow_mount": "required",
            "snapshot_assembly_via_canonical_workflow": True,
            "project_record_mutated": False,
            "frozen_runtime_files_mutated": False,
        }

    def execute(
        self,
        session_id: str,
        context: DIBTenantContext,
        command_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        command = self._parse_command(command_payload or {})
        session, blueprint_record, manifest_record, gate_record = self._verified_chain(
            session_id,
            context,
            command,
        )
        manifest = dict(manifest_record["payload"])
        gate = dict(gate_record["payload"])
        readiness = build_manifest_run_readiness(session, scenario_id=command.scenario_id)
        if readiness.get("ready_for_project_run") is not True:
            return self._blocked_result(
                session,
                readiness,
                manifest_record=manifest_record,
                gate_record=gate_record,
            )

        project = self.repository.get_project(str(session["project_id"]))
        if project is None or project.organization_id != context.organization_id:
            raise DIBCanonicalFinanceAdmissionError("dib_resource_not_found", 404)

        normalized_inputs = manifest.get("normalized_inputs")
        if not isinstance(normalized_inputs, dict):
            raise DIBCanonicalFinanceAdmissionError("canonical_admission_normalized_inputs_missing")
        project_overlay = self._manifest_project_overlay(project, normalized_inputs)
        data_access = ManifestBackedProjectRunDataAccess(self.repository, manifest)
        request, lineage = self._project_run_request(
            session,
            blueprint_record=blueprint_record,
            manifest_record=manifest_record,
            gate_record=gate_record,
            scenario_id=command.scenario_id,
            operation_id=command.operation_id,
            idempotency_key=command.idempotency_key,
        )
        result = self.executor.execute(
            project=project_overlay,
            data_access=data_access,
            request=request,
        )
        return self._verified_execution_result(
            result,
            session=session,
            request=request,
            readiness=readiness,
            lineage=lineage,
        )

    def _parse_command(self, payload: dict[str, Any]) -> CanonicalFinanceAdmissionCommand:
        if not isinstance(payload, dict):
            raise DIBCanonicalFinanceAdmissionError("canonical_admission_command_object_required", 400)
        forbidden = sorted(self._FORBIDDEN_CLIENT_FIELDS & set(payload))
        if forbidden:
            raise DIBCanonicalFinanceAdmissionError(
                "canonical_admission_forbidden_fields:" + ",".join(forbidden)
            )
        unknown = sorted(set(payload) - self._ALLOWED_COMMAND_FIELDS)
        if unknown:
            raise DIBCanonicalFinanceAdmissionError(
                "canonical_admission_unknown_fields:" + ",".join(unknown)
            )
        scenario_id = str(payload.get("scenario_id") or "baseline").strip()
        if not scenario_id or len(scenario_id) > 128:
            raise DIBCanonicalFinanceAdmissionError("canonical_admission_invalid_scenario", 400)
        return CanonicalFinanceAdmissionCommand(
            scenario_id=scenario_id,
            operation_id=self._optional_text(payload.get("operation_id"), "operation_id"),
            idempotency_key=self._optional_text(payload.get("idempotency_key"), "idempotency_key"),
            expected_manifest_id=self._optional_text(payload.get("expected_manifest_id"), "expected_manifest_id"),
            expected_manifest_payload_hash=self._optional_text(
                payload.get("expected_manifest_payload_hash"),
                "expected_manifest_payload_hash",
            ),
            expected_gate_id=self._optional_text(payload.get("expected_gate_id"), "expected_gate_id"),
            expected_gate_payload_hash=self._optional_text(
                payload.get("expected_gate_payload_hash"),
                "expected_gate_payload_hash",
            ),
        )

    @staticmethod
    def _optional_text(value: Any, field: str) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        if not text or len(text) > 256:
            raise DIBCanonicalFinanceAdmissionError(f"canonical_admission_invalid_{field}", 400)
        return text

    def _verified_chain(
        self,
        session_id: str,
        context: DIBTenantContext,
        command: CanonicalFinanceAdmissionCommand,
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
        session = self.store.load_session(session_id)
        project_id = str(session.get("project_id") or "")
        project = self.repository.get_project(project_id)
        if project is None or project.organization_id != context.organization_id:
            raise DIBCanonicalFinanceAdmissionError("dib_resource_not_found", 404)

        blueprint_id = str(session.get("current_blueprint_id") or "").strip()
        manifest_id = str(session.get("approved_manifest_id") or "").strip()
        gate_id = str(session.get("validation_gate_id") or "").strip()
        if not blueprint_id:
            raise DIBCanonicalFinanceAdmissionError("canonical_admission_blueprint_missing", 409)
        if not manifest_id:
            raise DIBCanonicalFinanceAdmissionError("canonical_admission_manifest_missing", 409)
        if not gate_id:
            raise DIBCanonicalFinanceAdmissionError("canonical_admission_gate_missing", 409)

        blueprint_record = self.store.load_blueprint(blueprint_id)
        manifest_record = self.store.load_manifest(manifest_id)
        gate_record = self.store.load_validation_gate(gate_id)
        manifest = dict(manifest_record["payload"])
        gate = dict(gate_record["payload"])

        for record, name in (
            (blueprint_record, "blueprint"),
            (manifest_record, "manifest"),
            (gate_record, "gate"),
        ):
            if record.get("session_id") != session_id:
                raise DIBCanonicalFinanceAdmissionError(f"canonical_admission_{name}_session_mismatch", 409)
        if blueprint_record.get("project_id") != project_id or manifest_record.get("project_id") != project_id:
            raise DIBCanonicalFinanceAdmissionError("canonical_admission_project_lineage_mismatch", 409)

        if _payload_hash(dict(blueprint_record["payload"])) != blueprint_record.get("payload_hash"):
            raise DIBCanonicalFinanceAdmissionError("canonical_admission_blueprint_hash_mismatch", 409)
        if _payload_hash(manifest) != manifest_record.get("payload_hash"):
            raise DIBCanonicalFinanceAdmissionError("canonical_admission_manifest_hash_mismatch", 409)
        if _payload_hash(gate) != gate_record.get("payload_hash"):
            raise DIBCanonicalFinanceAdmissionError("canonical_admission_gate_hash_mismatch", 409)

        if manifest.get("contract_id") != "approved.input.manifest.v1" or manifest.get("status") != "approved":
            raise DIBCanonicalFinanceAdmissionError("canonical_admission_manifest_not_approved", 409)
        if gate.get("contract_id") != "manifest.validation.v1" or gate.get("status") != "passed":
            raise DIBCanonicalFinanceAdmissionError("canonical_admission_gate_not_passed", 409)
        if manifest.get("server_authority") != SERVER_AUTHORITY or gate.get("server_authority") != SERVER_AUTHORITY:
            raise DIBCanonicalFinanceAdmissionError("canonical_admission_server_authority_missing", 409)
        if manifest.get("blueprint_id") != blueprint_id:
            raise DIBCanonicalFinanceAdmissionError("canonical_admission_blueprint_id_mismatch", 409)
        if manifest.get("blueprint_payload_hash") != blueprint_record.get("payload_hash"):
            raise DIBCanonicalFinanceAdmissionError("canonical_admission_blueprint_lineage_hash_mismatch", 409)
        if gate.get("manifest_id") != manifest_id:
            raise DIBCanonicalFinanceAdmissionError("canonical_admission_manifest_id_mismatch", 409)
        if gate.get("manifest_payload_hash") != manifest_record.get("payload_hash"):
            raise DIBCanonicalFinanceAdmissionError("canonical_admission_manifest_lineage_hash_mismatch", 409)
        if gate.get("blueprint_id") != blueprint_id or gate.get("blueprint_payload_hash") != blueprint_record.get("payload_hash"):
            raise DIBCanonicalFinanceAdmissionError("canonical_admission_gate_blueprint_mismatch", 409)

        manifest_lineage = manifest.get("lineage") if isinstance(manifest.get("lineage"), dict) else {}
        gate_lineage = gate.get("lineage") if isinstance(gate.get("lineage"), dict) else {}
        if manifest_lineage.get("session_id") != session_id or manifest_lineage.get("project_id") != project_id:
            raise DIBCanonicalFinanceAdmissionError("canonical_admission_manifest_lineage_scope_mismatch", 409)
        if gate_lineage.get("session_id") != session_id or gate_lineage.get("project_id") != project_id:
            raise DIBCanonicalFinanceAdmissionError("canonical_admission_gate_lineage_scope_mismatch", 409)

        self._assert_expected(command.expected_manifest_id, manifest_id, "stale_manifest_lineage")
        self._assert_expected(
            command.expected_manifest_payload_hash,
            str(manifest_record.get("payload_hash") or ""),
            "stale_manifest_lineage",
        )
        self._assert_expected(command.expected_gate_id, gate_id, "stale_gate_lineage")
        self._assert_expected(
            command.expected_gate_payload_hash,
            str(gate_record.get("payload_hash") or ""),
            "stale_gate_lineage",
        )
        return session, blueprint_record, manifest_record, gate_record

    @staticmethod
    def _assert_expected(expected: str | None, actual: str, code: str) -> None:
        if expected is not None and expected != actual:
            raise DIBCanonicalFinanceAdmissionError(code, 409)

    @staticmethod
    def _manifest_project_overlay(project: ProjectRecord, normalized_inputs: dict[str, Any]) -> ProjectRecord:
        context_inputs = {
            key: deepcopy(project.inputs[key])
            for key in SYSTEM_CONTEXT_INPUT_KEYS
            if key in project.inputs
        }
        return ProjectRecord(
            project_id=project.project_id,
            name=project.name,
            sector=project.sector,
            jurisdiction=project.jurisdiction,
            depth_profile=project.depth_profile,
            inputs=context_inputs | deepcopy(normalized_inputs),
            created_at=project.created_at,
            updated_at=project.updated_at,
            organization_id=project.organization_id,
        )

    @staticmethod
    def _project_run_request(
        session: dict[str, Any],
        *,
        blueprint_record: dict[str, Any],
        manifest_record: dict[str, Any],
        gate_record: dict[str, Any],
        scenario_id: str,
        operation_id: str | None,
        idempotency_key: str | None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        lineage = {
            "session_id": session["session_id"],
            "project_id": session["project_id"],
            "blueprint_id": blueprint_record["blueprint_id"],
            "blueprint_payload_hash": blueprint_record["payload_hash"],
            "manifest_id": manifest_record["manifest_id"],
            "manifest_payload_hash": manifest_record["payload_hash"],
            "gate_id": gate_record["gate_id"],
            "gate_payload_hash": gate_record["payload_hash"],
            "scenario_id": scenario_id,
            "normalized_inputs": dict(manifest_record["payload"].get("normalized_inputs") or {}),
        }
        input_hash = canonical_hash(lineage)
        stable_idempotency_key = idempotency_key or f"idem:dib-canonical:{input_hash[:32]}"
        return (
            {
                "project_id": str(session["project_id"]),
                "scenario_id": scenario_id,
                "operation_id": operation_id or new_id("op_dib_canonical_project_run"),
                "idempotency_key": stable_idempotency_key,
                "input_hash": input_hash,
                "requested_at": now_iso(),
                "input_contract_id": "ProjectRunHttpRequest.v1",
            },
            lineage,
        )

    @staticmethod
    def _blocked_result(
        session: dict[str, Any],
        readiness: dict[str, Any],
        *,
        manifest_record: dict[str, Any],
        gate_record: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "canonical_finance_admission_id": DIB_CANONICAL_FINANCE_ADMISSION_ID,
            "contract_id": "dib.canonical.project_run.admission.v1",
            "status": "blocked",
            "project_id": str(session.get("project_id") or ""),
            "session_id": str(session.get("session_id") or ""),
            "manifest_id": str(manifest_record.get("manifest_id") or ""),
            "manifest_validation_gate_id": str(gate_record.get("gate_id") or ""),
            "readiness": readiness,
            "finance": None,
            "blockers": list(readiness.get("blockers") or []),
            "finance_engine_execution_status": "not_executed",
            "project_run_workflow_mount": "not_called_blocked_before_admission",
            "direct_finance_execution_enabled": False,
            "canonical_project_run_execution_enabled": True,
            "snapshot_mutation": False,
            "frozen_project_run_workflow_mutated": False,
            "snapshot_assembly_mutated": False,
            "created_at": now_iso(),
        }

    @staticmethod
    def _verified_execution_result(
        result: dict[str, Any],
        *,
        session: dict[str, Any],
        request: dict[str, Any],
        readiness: dict[str, Any],
        lineage: dict[str, Any],
    ) -> dict[str, Any]:
        overview = result.get("overview")
        workflow = result.get("workflow")
        if not isinstance(overview, dict) or not isinstance(workflow, dict):
            raise DIBCanonicalFinanceAdmissionError("canonical_project_run_result_invalid", 500)
        if workflow.get("contract_id") != "project.run.workflow.v1" or workflow.get("status") != "accepted":
            raise DIBCanonicalFinanceAdmissionError("canonical_project_run_workflow_not_accepted", 500)
        if overview.get("project", {}).get("project_id") != session.get("project_id"):
            raise DIBCanonicalFinanceAdmissionError("canonical_project_run_project_mismatch", 500)
        run_id = str(result.get("run_id") or "")
        snapshot_id = str(result.get("snapshot_id") or "")
        if overview.get("run", {}).get("run_id") != run_id:
            raise DIBCanonicalFinanceAdmissionError("canonical_project_run_id_mismatch", 500)
        if overview.get("snapshot", {}).get("snapshot_id") != snapshot_id:
            raise DIBCanonicalFinanceAdmissionError("canonical_snapshot_id_mismatch", 500)
        if overview.get("snapshot", {}).get("immutable") is not True:
            raise DIBCanonicalFinanceAdmissionError("canonical_snapshot_not_immutable", 500)
        finance = overview.get("finance")
        if not isinstance(finance, dict):
            raise DIBCanonicalFinanceAdmissionError("canonical_finance_result_missing", 500)
        return {
            "canonical_finance_admission_id": DIB_CANONICAL_FINANCE_ADMISSION_ID,
            "contract_id": "dib.canonical.project_run.admission.v1",
            "status": "executed" if finance.get("status") == "ready" else "blocked",
            "project_id": str(session.get("project_id") or ""),
            "session_id": str(session.get("session_id") or ""),
            "scenario_id": request["scenario_id"],
            "operation_id": request["operation_id"],
            "idempotency_key": request["idempotency_key"],
            "input_hash": request["input_hash"],
            "input_contract_id": "approved.input.manifest.v1",
            "input_source": "server_owned_approved_input_manifest_only",
            "lineage": lineage,
            "readiness": readiness,
            "run_id": run_id,
            "snapshot_id": snapshot_id,
            "project_run": result,
            "workflow": workflow,
            "finance": finance,
            "blockers": list(overview.get("blockers") or []),
            "finance_command_contract_id": "finance.calculate.v1",
            "finance_contract_id": "finance.result.v1",
            "finance_engine_execution_status": "executed_via_project_run_workflow",
            "project_run_workflow_mount": "called",
            "idempotency_replayed": bool(result.get("idempotency_replayed")),
            "direct_finance_execution_enabled": False,
            "canonical_project_run_execution_enabled": True,
            "raw_ui_values_accepted": False,
            "raw_ai_values_accepted": False,
            "raw_file_values_accepted": False,
            "external_fetch_enabled": False,
            "ai_provider_enabled": False,
            "finance_wiring_enabled": False,
            "snapshot_wiring_enabled": True,
            "snapshot_mutation": True,
            "frozen_project_run_workflow_mutated": False,
            "snapshot_assembly_mutated": False,
            "created_at": now_iso(),
        }
