from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from backend.contracts import new_id, now_iso
from backend.dib_runtime import FINANCE_REQUIRED_KEYS

DIB_PROJECT_RUN_GATE_ID = "DIB-LIVE-002F-PROJECT-RUN-MANIFEST-GATE-v1"
DIB_PROJECT_RUN_GATE_STATUS = "post_freeze_manifest_gate"
DIB_PROJECT_RUN_GATE_SOURCE = "docs/EKB/EKB-02-Source-of-Truth-Matrix.md"

FORBIDDEN_DIB_PROJECT_RUN_FIELDS = frozenset(
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
        "snapshot",
        "assembled_snapshot",
        "sealed_outputs",
        "decision_pack",
    }
)

FORBIDDEN_DIB_PROJECT_RUN_TRUE_FLAGS = frozenset(
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


class DIBProjectRunGateError(ValueError):
    pass


@dataclass(frozen=True)
class DIBProjectRunGateResult:
    gate_id: str
    status: str
    project_id: str
    manifest_id: str
    manifest_validation_gate_id: str
    normalized_inputs: dict[str, Any]
    blockers: tuple[dict[str, Any], ...]
    payload_hash: str
    created_at: str

    def to_public(self) -> dict[str, Any]:
        return {
            "contract_id": "dib.project_run.manifest_gate.v1",
            "gate_id": self.gate_id,
            "gate_type": DIB_PROJECT_RUN_GATE_ID,
            "status": self.status,
            "project_id": self.project_id,
            "manifest_id": self.manifest_id,
            "manifest_validation_gate_id": self.manifest_validation_gate_id,
            "input_contract_id": "approved.input.manifest.v1",
            "normalized_inputs": dict(self.normalized_inputs),
            "blockers": list(self.blockers),
            "payload_hash": self.payload_hash,
            "created_at": self.created_at,
            "ready_for_project_run": self.status == "passed",
            "input_source": "approved_input_manifest_only",
            "raw_ui_values_accepted": False,
            "raw_ai_values_accepted": False,
            "raw_file_values_accepted": False,
            "external_fetch_enabled": False,
            "ai_provider_enabled": False,
            "finance_wiring_enabled": False,
            "snapshot_wiring_enabled": False,
            "frozen_project_run_workflow_mutated": False,
        }


def _json_dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _payload_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(_json_dump(payload).encode("utf-8")).hexdigest()


def _as_number(value: Any) -> float | None:
    if value is None or value == "" or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).replace(",", ""))
    except ValueError:
        return None


def _reject_forbidden_payload(payload: Any, *, context: str) -> None:
    def walk(value: Any, path: str) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                key_text = str(key)
                if key_text in FORBIDDEN_DIB_PROJECT_RUN_FIELDS:
                    raise DIBProjectRunGateError(f"{context} contains forbidden field: {path}.{key_text}")
                if key_text in FORBIDDEN_DIB_PROJECT_RUN_TRUE_FLAGS and item is True:
                    raise DIBProjectRunGateError(f"{context} attempted to enable forbidden flag: {path}.{key_text}")
                walk(item, f"{path}.{key_text}")
        elif isinstance(value, list):
            for index, item in enumerate(value):
                walk(item, f"{path}[{index}]")

    walk(payload, context)


def _manifest_blockers(manifest: dict[str, Any], validation_gate: dict[str, Any]) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    if manifest.get("contract_id") != "approved.input.manifest.v1":
        blockers.append({"code": "INVALID_DIB_MANIFEST_CONTRACT", "severity": "critical", "message": "DIB Project Run Gate requires approved.input.manifest.v1"})
    if manifest.get("status") != "approved":
        blockers.append({"code": "DIB_MANIFEST_NOT_APPROVED", "severity": "critical", "message": "Approved Input Manifest is not approved"})
    if validation_gate.get("contract_id") != "manifest.validation.v1":
        blockers.append({"code": "INVALID_DIB_VALIDATION_CONTRACT", "severity": "critical", "message": "DIB Project Run Gate requires manifest.validation.v1"})
    if validation_gate.get("status") != "passed":
        blockers.append({"code": "DIB_MANIFEST_VALIDATION_NOT_PASSED", "severity": "critical", "message": "Manifest Validation Gate has not passed"})
    if validation_gate.get("manifest_id") != manifest.get("manifest_id"):
        blockers.append({"code": "DIB_MANIFEST_GATE_MISMATCH", "severity": "critical", "message": "Manifest Validation Gate does not belong to this manifest"})

    inputs = manifest.get("normalized_inputs")
    if not isinstance(inputs, dict):
        blockers.append({"code": "DIB_NORMALIZED_INPUTS_MISSING", "severity": "critical", "message": "Approved Input Manifest is missing normalized_inputs"})
        return blockers
    for key in FINANCE_REQUIRED_KEYS:
        if _as_number(inputs.get(key)) is None:
            blockers.append({"code": f"DIB_PROJECT_RUN_INPUT_MISSING_{key.upper()}", "severity": "critical", "message": f"DIB Project Run input missing {key}"})
    return blockers


def build_dib_project_run_manifest_gate(manifest: dict[str, Any], validation_gate: dict[str, Any]) -> dict[str, Any]:
    _reject_forbidden_payload(manifest, context="approved_manifest")
    _reject_forbidden_payload(validation_gate, context="manifest_validation_gate")
    blockers = _manifest_blockers(manifest, validation_gate)
    normalized_inputs = dict(manifest.get("normalized_inputs") or {}) if not blockers else {}
    payload = {
        "manifest_id": manifest.get("manifest_id"),
        "manifest_validation_gate_id": validation_gate.get("gate_id"),
        "project_id": manifest.get("project_id"),
        "normalized_inputs": normalized_inputs,
        "blockers": blockers,
        "input_source": "approved_input_manifest_only",
    }
    result = DIBProjectRunGateResult(
        gate_id=new_id("dib_project_run_gate"),
        status="passed" if not blockers else "blocked",
        project_id=str(manifest.get("project_id") or ""),
        manifest_id=str(manifest.get("manifest_id") or ""),
        manifest_validation_gate_id=str(validation_gate.get("gate_id") or ""),
        normalized_inputs=normalized_inputs,
        blockers=tuple(blockers),
        payload_hash=_payload_hash(payload),
        created_at=now_iso(),
    )
    return result.to_public()


def build_project_run_request_from_dib_manifest(
    manifest: dict[str, Any],
    validation_gate: dict[str, Any],
    *,
    scenario_id: str = "baseline",
    operation_id: str | None = None,
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    gate = build_dib_project_run_manifest_gate(manifest, validation_gate)
    if gate["status"] != "passed":
        raise DIBProjectRunGateError("DIB Project Run Manifest Gate is blocked")
    request = {
        "project_id": gate["project_id"],
        "scenario_id": scenario_id,
        "operation_id": operation_id or new_id("op_dib_project_run"),
        "idempotency_key": idempotency_key or new_id("idem_dib_project_run"),
        "input_contract_id": "approved.input.manifest.v1",
        "input_source": "approved_input_manifest_only",
        "approved_input_manifest_id": gate["manifest_id"],
        "manifest_validation_gate_id": gate["manifest_validation_gate_id"],
        "manifest_gate_id": gate["gate_id"],
        "normalized_inputs": dict(gate["normalized_inputs"]),
        "input_hash": gate["payload_hash"],
        "requires_project_run_workflow_mount": True,
        "raw_ui_values_accepted": False,
        "raw_ai_values_accepted": False,
        "raw_file_values_accepted": False,
        "external_fetch_enabled": False,
        "ai_provider_enabled": False,
        "finance_wiring_enabled": False,
        "snapshot_wiring_enabled": False,
        "frozen_project_run_workflow_mutated": False,
    }
    _reject_forbidden_payload(request, context="project_run_request")
    return request


def dib_project_run_gate_status() -> dict[str, Any]:
    return {
        "gate_id": DIB_PROJECT_RUN_GATE_ID,
        "status": DIB_PROJECT_RUN_GATE_STATUS,
        "source": DIB_PROJECT_RUN_GATE_SOURCE,
        "accepted_input_contract": "approved.input.manifest.v1",
        "required_validation_contract": "manifest.validation.v1",
        "project_run_workflow_mount": "planned",
        "external_fetch_enabled": False,
        "ai_provider_enabled": False,
        "finance_wiring_enabled": False,
        "snapshot_wiring_enabled": False,
        "frozen_project_run_workflow_mutated": False,
    }
