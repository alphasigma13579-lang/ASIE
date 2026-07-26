from __future__ import annotations

from typing import Any

from backend.contracts import now_iso
from backend.dib_project_run_gate import (
    DIBProjectRunGateError,
    build_dib_project_run_manifest_gate,
    build_project_run_request_from_dib_manifest,
    dib_project_run_gate_status,
)

DIB_MANIFEST_RUN_READINESS_ID = "DIB-COMPLETION-PACKAGE-C-MANIFEST-RUN-READINESS-v1"
DIB_MANIFEST_RUN_READINESS_STATUS = "post_freeze_manifest_to_run_readiness"
DIB_MANIFEST_RUN_READINESS_SOURCE = "docs/EKB/EKB-02-Source-of-Truth-Matrix.md"

FORBIDDEN_READINESS_FIELDS = frozenset(
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
        "finance",
        "finance_result",
        "finance_inputs",
        "snapshot",
        "assembled_snapshot",
        "sealed_outputs",
        "decision_pack",
    }
)

FORBIDDEN_READINESS_TRUE_FLAGS = frozenset(
    {
        "ai_provider_enabled",
        "ai_enabled",
        "external_fetch_enabled",
        "network_fetch",
        "network_request",
        "finance_wiring_enabled",
        "snapshot_wiring_enabled",
    }
)


def _reject_forbidden(value: Any, *, context: str = "dib_manifest_run_readiness") -> None:
    def walk(node: Any, path: str) -> None:
        if isinstance(node, dict):
            for key, item in node.items():
                key_text = str(key)
                if key_text in FORBIDDEN_READINESS_FIELDS:
                    raise ValueError(f"{context}_forbidden_field:{path}.{key_text}")
                if key_text in FORBIDDEN_READINESS_TRUE_FLAGS and item is True:
                    raise ValueError(f"{context}_forbidden_flag:{path}.{key_text}")
                walk(item, f"{path}.{key_text}")
        elif isinstance(node, list):
            for index, item in enumerate(node):
                walk(item, f"{path}[{index}]")

    walk(value, context)


def _blocker(code: str, message: str, *, severity: str = "critical") -> dict[str, str]:
    return {"code": code, "severity": severity, "message": message}


def build_manifest_run_readiness(session: dict[str, Any], *, scenario_id: str = "baseline") -> dict[str, Any]:
    """Build a controlled readiness handoff from DIB Manifest to Project Run Gate.

    This helper deliberately does not execute Finance Engine, does not call the
    frozen ProjectRunWorkflow, and does not assemble Snapshot. It only confirms
    whether the current Approved Input Manifest and Manifest Validation Gate are
    suitable to create a manifest-derived Project Run request.
    """

    _reject_forbidden(session, context="dib_session")
    manifest = session.get("approved_manifest")
    validation_gate = session.get("validation_gate")
    blockers: list[dict[str, str]] = []
    if not isinstance(manifest, dict):
        blockers.append(_blocker("DIB_APPROVED_MANIFEST_MISSING", "Approved Input Manifest is required before run readiness."))
    if not isinstance(validation_gate, dict):
        blockers.append(_blocker("DIB_VALIDATION_GATE_MISSING", "Manifest Validation Gate is required before run readiness."))

    readiness: dict[str, Any] = {
        "readiness_id": DIB_MANIFEST_RUN_READINESS_ID,
        "status": "blocked" if blockers else "pending_gate",
        "project_id": str(session.get("project_id") or ""),
        "session_id": str(session.get("session_id") or ""),
        "scenario_id": scenario_id,
        "blockers": blockers,
        "manifest_gate": None,
        "project_run_request": None,
        "ready_for_project_run": False,
        "finance_engine_execution_status": "not_executed",
        "project_run_workflow_mount": "not_called",
        "input_source": "approved_input_manifest_only",
        "external_fetch_enabled": False,
        "ai_provider_enabled": False,
        "finance_wiring_enabled": False,
        "snapshot_wiring_enabled": False,
        "frozen_project_run_workflow_mutated": False,
        "snapshot_assembly_mutated": False,
        "created_at": now_iso(),
    }
    if blockers:
        return readiness

    try:
        gate = build_dib_project_run_manifest_gate(dict(manifest), dict(validation_gate))
        readiness["manifest_gate"] = gate
        readiness["blockers"] = list(gate.get("blockers") or [])
        readiness["status"] = "ready" if gate.get("status") == "passed" else "blocked"
        readiness["ready_for_project_run"] = gate.get("status") == "passed"
        if readiness["ready_for_project_run"]:
            request = build_project_run_request_from_dib_manifest(dict(manifest), dict(validation_gate), scenario_id=scenario_id)
            readiness["project_run_request"] = request
    except DIBProjectRunGateError as exc:
        readiness["status"] = "blocked"
        readiness["ready_for_project_run"] = False
        readiness["blockers"] = [_blocker("DIB_PROJECT_RUN_GATE_BLOCKED", str(exc))]

    _reject_forbidden(readiness, context="dib_manifest_run_readiness_output")
    return readiness


def manifest_run_readiness_status() -> dict[str, Any]:
    return {
        "readiness_id": DIB_MANIFEST_RUN_READINESS_ID,
        "status": DIB_MANIFEST_RUN_READINESS_STATUS,
        "source": DIB_MANIFEST_RUN_READINESS_SOURCE,
        "project_run_gate": dib_project_run_gate_status(),
        "accepted_input_contract": "approved.input.manifest.v1",
        "required_validation_contract": "manifest.validation.v1",
        "project_run_workflow_mount": "not_called",
        "finance_engine_execution_status": "not_executed",
        "external_fetch_enabled": False,
        "ai_provider_enabled": False,
        "finance_wiring_enabled": False,
        "snapshot_wiring_enabled": False,
        "frozen_project_run_workflow_mutated": False,
        "snapshot_assembly_mutated": False,
    }
