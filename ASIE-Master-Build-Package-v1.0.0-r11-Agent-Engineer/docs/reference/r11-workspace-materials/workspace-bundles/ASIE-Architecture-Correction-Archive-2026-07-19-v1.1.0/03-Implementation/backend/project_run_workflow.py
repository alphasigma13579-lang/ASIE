from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Callable

from backend.contracts import new_id, now_iso
from backend.module_runtime import ModuleRuntime
from backend.snapshot_assembly import canonical_hash
from backend.system_bus import BusMessage


class ProjectRunWorkflowError(ValueError):
    pass


PROJECT_RUN_PIPELINE_CONTRACT_SEQUENCE_V1 = (
    "finance.calculate.v1",
    "sector.intelligence.build.v1",
    "evidence.ledger.build.v1",
    "decision.council.evaluate.v1",
    "risk.register.build.v1",
    "execution.plan.build.v1",
    "snapshot.assemble.v1",
)


@dataclass(frozen=True)
class ProjectRunEnvelope:
    project_id: str
    scenario_id: str
    operation_id: str
    idempotency_key: str
    input_hash: str
    run_id: str
    snapshot_id: str
    source_module_id: str
    pipeline_policy_id: str = "project-run-pipeline.v1"
    pipeline_contract_sequence: tuple[str, ...] = PROJECT_RUN_PIPELINE_CONTRACT_SEQUENCE_V1

    def __post_init__(self) -> None:
        for field_name in (
            "project_id",
            "scenario_id",
            "operation_id",
            "idempotency_key",
            "input_hash",
            "run_id",
            "snapshot_id",
            "source_module_id",
            "pipeline_policy_id",
        ):
            if not str(getattr(self, field_name) or "").strip():
                raise ProjectRunWorkflowError(f"project_run_envelope_missing:{field_name}")
        if not self.pipeline_contract_sequence:
            raise ProjectRunWorkflowError("project_run_envelope_missing:pipeline_contract_sequence")

    @classmethod
    def from_request(cls, request: dict[str, Any], *, source_module_id: str) -> ProjectRunEnvelope:
        return cls(
            project_id=str(request.get("project_id") or ""),
            scenario_id=str(request.get("scenario_id") or ""),
            operation_id=str(request.get("operation_id") or ""),
            idempotency_key=str(request.get("idempotency_key") or ""),
            input_hash=str(request.get("input_hash") or ""),
            run_id=new_id("run"),
            snapshot_id=new_id("snap"),
            source_module_id=source_module_id,
        )


RunBuilder = Callable[[ProjectRunEnvelope], tuple[dict[str, Any], dict[str, Any]]]
SnapshotSaver = Callable[[dict[str, Any], dict[str, Any]], dict[str, str]]


@dataclass(frozen=True)
class ProjectRunWorkflowResult:
    run_id: str
    snapshot_id: str
    overview: dict[str, Any]
    workflow: dict[str, Any]
    idempotency_replayed: bool = False

    def to_response(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "snapshot_id": self.snapshot_id,
            "overview": self.overview,
            "workflow": self.workflow,
            "idempotency_replayed": self.idempotency_replayed,
        }


class ProjectRunIdempotencyStore:
    def __init__(self) -> None:
        self._records: dict[str, dict[str, Any]] = {}

    def begin(self, request: dict[str, Any]) -> dict[str, Any] | None:
        key = request["idempotency_key"]
        existing = self._records.get(key)
        if existing is None:
            self._records[key] = {
                "input_hash": request["input_hash"],
                "status": "in_progress",
                "created_at": now_iso(),
            }
            return None
        if existing["input_hash"] != request["input_hash"]:
            raise ProjectRunWorkflowError("request_rejected:conflicting_idempotency_key")
        if existing.get("status") == "completed":
            return deepcopy(existing["result"])
        raise ProjectRunWorkflowError("request_rejected:idempotency_key_in_progress")

    def completed_replay(self, request: dict[str, Any]) -> dict[str, Any] | None:
        existing = self._records.get(request["idempotency_key"])
        if existing is None:
            return None
        if existing["input_hash"] != request["input_hash"]:
            raise ProjectRunWorkflowError("request_rejected:conflicting_idempotency_key")
        if existing.get("status") != "completed":
            raise ProjectRunWorkflowError("request_rejected:idempotency_key_in_progress")
        result = deepcopy(existing["result"])
        result["idempotency_replayed"] = True
        return result

    def complete(self, request: dict[str, Any], result: ProjectRunWorkflowResult) -> None:
        self._records[request["idempotency_key"]] = {
            "input_hash": request["input_hash"],
            "status": "completed",
            "created_at": self._records.get(request["idempotency_key"], {}).get("created_at", now_iso()),
            "completed_at": now_iso(),
            "result": result.to_response(),
        }

    def fail(self, request: dict[str, Any]) -> None:
        self._records.pop(request["idempotency_key"], None)


def normalize_project_run_http_request(project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    allowed_fields = {"scenario_id", "operation_id", "idempotency_key"}
    unknown_fields = set(payload) - allowed_fields
    if unknown_fields:
        raise ProjectRunWorkflowError("request_rejected:forbidden_fields:" + ",".join(sorted(unknown_fields)))
    scenario_id = str(payload.get("scenario_id") or "baseline")
    operation_id = str(payload.get("operation_id") or new_id("op"))
    idempotency_key = str(payload.get("idempotency_key") or new_id("idem"))
    input_hash = canonical_hash(
        {
            "project_id": project_id,
            "scenario_id": scenario_id,
        }
    )
    return {
        "project_id": project_id,
        "scenario_id": scenario_id,
        "operation_id": operation_id,
        "idempotency_key": idempotency_key,
        "input_hash": input_hash,
        "requested_at": now_iso(),
        "input_contract_id": "ProjectRunHttpRequest.v1",
    }


class ProjectRunWorkflow:
    def __init__(
        self,
        runtime: ModuleRuntime,
        idempotency_store: ProjectRunIdempotencyStore,
        *,
        source_module_id: str = "aas.heart_controller",
        heart_assignment: dict[str, Any] | None = None,
    ) -> None:
        self.runtime = runtime
        self.idempotency_store = idempotency_store
        self.source_module_id = source_module_id
        self.heart_assignment = deepcopy(heart_assignment) if heart_assignment else None

    def run(
        self,
        request: dict[str, Any],
        *,
        build: RunBuilder,
        save: SnapshotSaver,
    ) -> ProjectRunWorkflowResult:
        replayed = self.idempotency_store.begin(request)
        if replayed is not None:
            return ProjectRunWorkflowResult(
                run_id=replayed["run_id"],
                snapshot_id=replayed["snapshot_id"],
                overview=replayed["overview"],
                workflow=replayed["workflow"],
                idempotency_replayed=True,
            )
        try:
            workflow_record = self.runtime.execute(
                BusMessage(
                    source_module_id=self.source_module_id,
                    target_module_id="module.project_run_workflow",
                    contract_id="project.run.workflow.v1",
                    socket_id="socket.project.run",
                    correlation_id=f"corr:{request['operation_id']}:project-run-workflow",
                    audit_ref=f"audit:{request['operation_id']}:project-run-workflow",
                    operation_id=request["operation_id"],
                    idempotency_key=request["idempotency_key"],
                    input_hash=request["input_hash"],
                    payload=request,
                )
            )
            run_envelope = ProjectRunEnvelope.from_request(
                request,
                source_module_id=self.source_module_id,
            )
            overview, report = build(run_envelope)
            if overview.get("run", {}).get("run_id") != run_envelope.run_id:
                raise ProjectRunWorkflowError("pipeline_result_run_id_mismatch")
            if overview.get("snapshot", {}).get("snapshot_id") != run_envelope.snapshot_id:
                raise ProjectRunWorkflowError("pipeline_result_snapshot_id_mismatch")
            save(overview, report)
            result = ProjectRunWorkflowResult(
                run_id=overview["run"]["run_id"],
                snapshot_id=overview["snapshot"]["snapshot_id"],
                overview=overview,
                workflow=workflow_record.output
                | {
                    "assigned_source_module_id": self.source_module_id,
                    "heart_assignment": deepcopy(self.heart_assignment),
                    "pipeline_policy_id": run_envelope.pipeline_policy_id,
                },
            )
            self.idempotency_store.complete(request, result)
            return result
        except Exception:
            self.idempotency_store.fail(request)
            raise
