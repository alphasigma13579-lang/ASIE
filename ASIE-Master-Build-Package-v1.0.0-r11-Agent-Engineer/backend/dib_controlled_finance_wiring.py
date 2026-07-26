from __future__ import annotations

from typing import Any

from backend.contracts import new_id, now_iso
from backend.dib_manifest_run_readiness import build_manifest_run_readiness
from backend.finance_engine import finance_result_set
from backend.snapshot_assembly import canonical_hash

DIB_CONTROLLED_FINANCE_WIRING_ID = "DIB-COMPLETION-PACKAGE-D-CONTROLLED-FINANCE-WIRING-v1"
DIB_CONTROLLED_FINANCE_WIRING_STATUS = "post_freeze_manifest_only_finance_execution"
DIB_CONTROLLED_FINANCE_WIRING_SOURCE = "docs/EKB/EKB-02-Source-of-Truth-Matrix.md"

FORBIDDEN_CONTROLLED_FINANCE_FIELDS = frozenset(
    {
        "raw_prompt",
        "prompt_template",
        "raw_file",
        "file_base64",
        "pdf_text",
        "api_key",
        "openai_api_key",
        "provider_config",
        "ai_provider",
        "finance_inputs",
        "snapshot",
        "assembled_snapshot",
        "sealed_outputs",
        "decision_pack",
    }
)

FORBIDDEN_CONTROLLED_FINANCE_TRUE_FLAGS = frozenset(
    {
        "ai_provider_enabled",
        "ai_enabled",
        "external_fetch_enabled",
        "network_fetch",
        "network_request",
        "snapshot_wiring_enabled",
    }
)


def _reject_forbidden(value: Any, *, context: str = "dib_controlled_finance_wiring") -> None:
    def walk(node: Any, path: str) -> None:
        if isinstance(node, dict):
            for key, item in node.items():
                key_text = str(key)
                if key_text in FORBIDDEN_CONTROLLED_FINANCE_FIELDS:
                    raise ValueError(f"{context}_forbidden_field:{path}.{key_text}")
                if key_text in FORBIDDEN_CONTROLLED_FINANCE_TRUE_FLAGS and item is True:
                    raise ValueError(f"{context}_forbidden_flag:{path}.{key_text}")
                walk(item, f"{path}.{key_text}")
        elif isinstance(node, list):
            for index, item in enumerate(node):
                walk(item, f"{path}[{index}]")

    walk(value, context)


def _blocker(code: str, message: str, *, severity: str = "critical") -> dict[str, str]:
    return {"code": code, "severity": severity, "message": message}


def _blocked_payload(session: dict[str, Any], readiness: dict[str, Any], blockers: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "controlled_finance_wiring_id": DIB_CONTROLLED_FINANCE_WIRING_ID,
        "contract_id": "dib.controlled.finance.wiring.v1",
        "status": "blocked",
        "project_id": str(session.get("project_id") or ""),
        "session_id": str(session.get("session_id") or ""),
        "scenario_id": str(readiness.get("scenario_id") or "baseline"),
        "readiness": readiness,
        "finance": None,
        "blockers": blockers,
        "finance_contract_id": "finance.result.v1",
        "finance_command_contract_id": "finance.calculate.v1",
        "finance_engine_execution_status": "not_executed",
        "project_run_workflow_mount": "not_called",
        "input_source": "approved_input_manifest_only",
        "controlled_finance_execution_enabled": False,
        "raw_ui_values_accepted": False,
        "raw_ai_values_accepted": False,
        "raw_file_values_accepted": False,
        "external_fetch_enabled": False,
        "ai_provider_enabled": False,
        "finance_wiring_enabled": False,
        "snapshot_wiring_enabled": False,
        "frozen_project_run_workflow_mutated": False,
        "snapshot_assembly_mutated": False,
        "created_at": now_iso(),
    }


def execute_controlled_finance_from_dib_session(session: dict[str, Any], *, scenario_id: str = "baseline") -> dict[str, Any]:
    """Execute deterministic Finance only from an Approved Input Manifest.

    This is not a ProjectRunWorkflow execution and does not assemble Snapshot. It
    verifies that the DIB Session already has Approved Input Manifest + passed
    Manifest Validation Gate, then passes only `normalized_inputs` to the backend
    finance engine. Raw UI, raw file, AI, network, and snapshot payloads are not
    accepted.
    """

    _reject_forbidden(session, context="dib_session")
    readiness = build_manifest_run_readiness(session, scenario_id=scenario_id)
    if not readiness.get("ready_for_project_run"):
        return _blocked_payload(session, readiness, list(readiness.get("blockers") or []))

    request = readiness.get("project_run_request")
    if not isinstance(request, dict):
        return _blocked_payload(
            session,
            readiness,
            [_blocker("DIB_PROJECT_RUN_REQUEST_MISSING", "Project Run request preview is required before controlled Finance execution.")],
        )
    _reject_forbidden(request, context="dib_project_run_request")
    if request.get("input_contract_id") != "approved.input.manifest.v1":
        raise ValueError("controlled_finance_requires_approved_input_manifest_contract")
    if request.get("input_source") != "approved_input_manifest_only":
        raise ValueError("controlled_finance_requires_manifest_only_input_source")
    normalized_inputs = request.get("normalized_inputs")
    if not isinstance(normalized_inputs, dict):
        raise ValueError("controlled_finance_requires_normalized_inputs")

    finance, blockers = finance_result_set(dict(normalized_inputs))
    status = "executed" if finance.get("status") == "ready" and not blockers else "blocked"
    payload_material = {
        "project_id": request.get("project_id"),
        "session_id": session.get("session_id"),
        "manifest_id": request.get("approved_input_manifest_id"),
        "manifest_validation_gate_id": request.get("manifest_validation_gate_id"),
        "manifest_gate_id": request.get("manifest_gate_id"),
        "normalized_inputs": normalized_inputs,
        "finance_status": finance.get("status"),
        "blockers": blockers,
        "input_hash": request.get("input_hash"),
    }
    return {
        "controlled_finance_wiring_id": DIB_CONTROLLED_FINANCE_WIRING_ID,
        "contract_id": "dib.controlled.finance.wiring.v1",
        "status": status,
        "project_id": str(request.get("project_id") or ""),
        "session_id": str(session.get("session_id") or ""),
        "scenario_id": scenario_id,
        "operation_id": str(request.get("operation_id") or new_id("op_dib_controlled_finance")),
        "manifest_id": str(request.get("approved_input_manifest_id") or ""),
        "manifest_validation_gate_id": str(request.get("manifest_validation_gate_id") or ""),
        "manifest_gate_id": str(request.get("manifest_gate_id") or ""),
        "input_contract_id": "approved.input.manifest.v1",
        "input_source": "approved_input_manifest_only",
        "input_hash": str(request.get("input_hash") or canonical_hash(payload_material)),
        "payload_hash": canonical_hash(payload_material),
        "readiness": readiness,
        "finance": finance,
        "blockers": blockers,
        "finance_contract_id": "finance.result.v1",
        "finance_command_contract_id": "finance.calculate.v1",
        "finance_engine_execution_status": "executed",
        "project_run_workflow_mount": "not_called",
        "controlled_finance_execution_enabled": True,
        "raw_ui_values_accepted": False,
        "raw_ai_values_accepted": False,
        "raw_file_values_accepted": False,
        "external_fetch_enabled": False,
        "ai_provider_enabled": False,
        "finance_wiring_enabled": False,
        "snapshot_wiring_enabled": False,
        "frozen_project_run_workflow_mutated": False,
        "snapshot_assembly_mutated": False,
        "created_at": now_iso(),
    }


def controlled_finance_wiring_status() -> dict[str, Any]:
    return {
        "controlled_finance_wiring_id": DIB_CONTROLLED_FINANCE_WIRING_ID,
        "status": DIB_CONTROLLED_FINANCE_WIRING_STATUS,
        "source": DIB_CONTROLLED_FINANCE_WIRING_SOURCE,
        "accepted_input_contract": "approved.input.manifest.v1",
        "required_validation_contract": "manifest.validation.v1",
        "finance_command_contract": "finance.calculate.v1",
        "finance_result_contract": "finance.result.v1",
        "finance_engine_execution_status": "controlled_manifest_only",
        "project_run_workflow_mount": "not_called",
        "external_fetch_enabled": False,
        "ai_provider_enabled": False,
        "finance_wiring_enabled": False,
        "snapshot_wiring_enabled": False,
        "frozen_project_run_workflow_mutated": False,
        "snapshot_assembly_mutated": False,
    }
