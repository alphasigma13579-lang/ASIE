from __future__ import annotations

from typing import Any

from backend.contracts import new_id, now_iso
from backend.dib_controlled_finance_wiring import execute_controlled_finance_from_dib_session
from backend.dib_manifest_run_readiness import build_manifest_run_readiness
from backend.dib_snapshot_lineage import build_dib_projection_support_payload, build_dib_snapshot_lineage
from backend.snapshot_assembly import canonical_hash

DIB_SNAPSHOT_PROJECTION_HANDOFF_ID = "DIB-COMPLETION-PACKAGE-E-SNAPSHOT-PROJECTION-HANDOFF-v1"
DIB_SNAPSHOT_PROJECTION_HANDOFF_STATUS = "post_freeze_snapshot_projection_handoff"
DIB_SNAPSHOT_PROJECTION_HANDOFF_SOURCE = "docs/EKB/EKB-02-Source-of-Truth-Matrix.md"

FORBIDDEN_SNAPSHOT_HANDOFF_FIELDS = frozenset(
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
        "assembled_snapshot",
        "sealed_outputs",
        "decision_pack",
    }
)

FORBIDDEN_SNAPSHOT_HANDOFF_TRUE_FLAGS = frozenset(
    {
        "ai_provider_enabled",
        "ai_enabled",
        "external_fetch_enabled",
        "network_fetch",
        "network_request",
        "snapshot_wiring_enabled",
        "snapshot_mutation_enabled",
    }
)


def _reject_forbidden(value: Any, *, context: str = "dib_snapshot_projection_handoff") -> None:
    def walk(node: Any, path: str) -> None:
        if isinstance(node, dict):
            for key, item in node.items():
                key_text = str(key)
                if key_text in FORBIDDEN_SNAPSHOT_HANDOFF_FIELDS:
                    raise ValueError(f"{context}_forbidden_field:{path}.{key_text}")
                if key_text in FORBIDDEN_SNAPSHOT_HANDOFF_TRUE_FLAGS and item is True:
                    raise ValueError(f"{context}_forbidden_flag:{path}.{key_text}")
                walk(item, f"{path}.{key_text}")
        elif isinstance(node, list):
            for index, item in enumerate(node):
                walk(item, f"{path}[{index}]")

    walk(value, context)


def _blocker(code: str, message: str, *, severity: str = "critical") -> dict[str, str]:
    return {"code": code, "severity": severity, "message": message}


def _blocked_payload(session: dict[str, Any], blockers: list[dict[str, Any]], *, scenario_id: str) -> dict[str, Any]:
    return {
        "snapshot_projection_handoff_id": DIB_SNAPSHOT_PROJECTION_HANDOFF_ID,
        "contract_id": "dib.snapshot.projection_handoff.v1",
        "status": "blocked",
        "project_id": str(session.get("project_id") or ""),
        "session_id": str(session.get("session_id") or ""),
        "scenario_id": scenario_id,
        "blockers": blockers,
        "lineage": None,
        "projection_support": None,
        "controlled_finance_reference": None,
        "ready_for_snapshot_projection_handoff": False,
        "sealed_envelope_created": False,
        "snapshot_assembly_mount": "not_called",
        "projection_support_mount": "prepared_only_when_ready",
        "project_run_workflow_mount": "not_called",
        "input_source": "approved_input_manifest_only",
        "external_fetch_enabled": False,
        "ai_provider_enabled": False,
        "finance_wiring_enabled": False,
        "snapshot_wiring_enabled": False,
        "snapshot_mutation": False,
        "frozen_snapshot_assembly_mutated": False,
        "created_at": now_iso(),
    }


def build_dib_snapshot_projection_handoff(session: dict[str, Any], *, scenario_id: str = "baseline") -> dict[str, Any]:
    """Prepare a freeze-safe Snapshot projection handoff for DIB outputs.

    This is not Snapshot Assembly. It builds DIB lineage + projection support
    metadata after Manifest readiness and Controlled Finance execution. The
    output carries hashes and references only; it does not seal an envelope,
    does not mutate snapshot_assembly.py, and does not create a Decision Pack.
    """

    _reject_forbidden(session, context="dib_session")
    readiness = build_manifest_run_readiness(session, scenario_id=scenario_id)
    if not readiness.get("ready_for_project_run"):
        return _blocked_payload(session, list(readiness.get("blockers") or []), scenario_id=scenario_id)

    controlled_finance = execute_controlled_finance_from_dib_session(session, scenario_id=scenario_id)
    if controlled_finance.get("status") != "executed":
        return _blocked_payload(
            session,
            list(controlled_finance.get("blockers") or [])
            or [_blocker("DIB_CONTROLLED_FINANCE_NOT_EXECUTED", "Controlled Finance must execute before Snapshot projection handoff.")],
            scenario_id=scenario_id,
        )

    manifest = session.get("approved_manifest")
    validation_gate = session.get("validation_gate")
    manifest_gate = readiness.get("manifest_gate")
    if not isinstance(manifest, dict) or not isinstance(validation_gate, dict) or not isinstance(manifest_gate, dict):
        return _blocked_payload(
            session,
            [_blocker("DIB_SNAPSHOT_HANDOFF_SOURCE_MISSING", "Manifest, Validation Gate, and Project Run Manifest Gate are required.")],
            scenario_id=scenario_id,
        )

    run_id = str(controlled_finance.get("operation_id") or new_id("run_dib_projection"))
    snapshot_id = new_id("snap_dib_projection")
    lineage = build_dib_snapshot_lineage(manifest, validation_gate, manifest_gate, run_id=run_id, snapshot_id=snapshot_id)
    projection_support = build_dib_projection_support_payload(lineage)
    controlled_finance_reference = {
        "contract_id": "dib.controlled.finance.reference.v1",
        "controlled_finance_contract_id": controlled_finance.get("contract_id"),
        "finance_contract_id": controlled_finance.get("finance_contract_id"),
        "finance_command_contract_id": controlled_finance.get("finance_command_contract_id"),
        "finance_status": (controlled_finance.get("finance") or {}).get("status") if isinstance(controlled_finance.get("finance"), dict) else None,
        "controlled_finance_status": controlled_finance.get("status"),
        "controlled_finance_payload_hash": controlled_finance.get("payload_hash"),
        "input_hash": controlled_finance.get("input_hash"),
        "manifest_id": controlled_finance.get("manifest_id"),
        "manifest_validation_gate_id": controlled_finance.get("manifest_validation_gate_id"),
        "input_source": "approved_input_manifest_only",
        "raw_ui_values_accepted": False,
        "raw_ai_values_accepted": False,
        "raw_file_values_accepted": False,
    }
    payload_material = {
        "project_id": session.get("project_id"),
        "session_id": session.get("session_id"),
        "scenario_id": scenario_id,
        "lineage_payload_hash": lineage.get("payload_hash"),
        "projection_support_lineage_hash": projection_support.get("lineage_payload_hash"),
        "controlled_finance_payload_hash": controlled_finance.get("payload_hash"),
    }
    handoff = {
        "snapshot_projection_handoff_id": DIB_SNAPSHOT_PROJECTION_HANDOFF_ID,
        "handoff_id": new_id("dib_snapshot_projection_handoff"),
        "contract_id": "dib.snapshot.projection_handoff.v1",
        "status": "prepared",
        "project_id": str(session.get("project_id") or ""),
        "session_id": str(session.get("session_id") or ""),
        "scenario_id": scenario_id,
        "run_id": run_id,
        "planned_snapshot_id": snapshot_id,
        "source_lineage_contract_id": lineage.get("contract_id"),
        "projection_support_contract_id": projection_support.get("contract_id"),
        "controlled_finance_reference_contract_id": controlled_finance_reference["contract_id"],
        "lineage": lineage,
        "projection_support": projection_support,
        "controlled_finance_reference": controlled_finance_reference,
        "payload_hash": canonical_hash(payload_material),
        "blockers": [],
        "ready_for_snapshot_projection_handoff": True,
        "sealed_envelope_created": False,
        "snapshot_assembly_mount": "not_called",
        "projection_support_mount": "handoff_prepared_only",
        "project_run_workflow_mount": "not_called",
        "input_source": "approved_input_manifest_only",
        "external_fetch_enabled": False,
        "ai_provider_enabled": False,
        "finance_wiring_enabled": False,
        "snapshot_wiring_enabled": False,
        "snapshot_mutation": False,
        "frozen_snapshot_assembly_mutated": False,
        "created_at": now_iso(),
    }
    _reject_forbidden(handoff, context="dib_snapshot_projection_handoff_output")
    return handoff


def snapshot_projection_handoff_status() -> dict[str, Any]:
    return {
        "snapshot_projection_handoff_id": DIB_SNAPSHOT_PROJECTION_HANDOFF_ID,
        "status": DIB_SNAPSHOT_PROJECTION_HANDOFF_STATUS,
        "source": DIB_SNAPSHOT_PROJECTION_HANDOFF_SOURCE,
        "handoff_contract_id": "dib.snapshot.projection_handoff.v1",
        "lineage_contract_id": "dib.snapshot.lineage.v1",
        "projection_support_contract_id": "dib.snapshot.projection_support.v1",
        "controlled_finance_reference_contract_id": "dib.controlled.finance.reference.v1",
        "accepted_input_contract": "approved.input.manifest.v1",
        "required_validation_contract": "manifest.validation.v1",
        "snapshot_assembly_mount": "not_called",
        "project_run_workflow_mount": "not_called",
        "sealed_envelope_created": False,
        "external_fetch_enabled": False,
        "ai_provider_enabled": False,
        "finance_wiring_enabled": False,
        "snapshot_wiring_enabled": False,
        "frozen_snapshot_assembly_mutated": False,
    }
