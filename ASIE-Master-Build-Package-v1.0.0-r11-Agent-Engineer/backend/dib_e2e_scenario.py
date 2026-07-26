from __future__ import annotations

import hashlib
import json
from typing import Any

from backend.contracts import now_iso
from backend.dib_controlled_finance_wiring import execute_controlled_finance_from_dib_session
from backend.dib_manifest_run_readiness import build_manifest_run_readiness
from backend.dib_snapshot_projection_handoff import build_dib_snapshot_projection_handoff

DIB_E2E_SCENARIO_ID = "DIB-COMPLETION-PACKAGE-G-E2E-SCENARIO-v1"
DIB_E2E_SCENARIO_STATUS = "post_freeze_end_to_end_user_flow_hardening"
DIB_E2E_SCENARIO_SOURCE = "docs/EKB/EKB-02-Source-of-Truth-Matrix.md"

FORBIDDEN_E2E_FIELDS = frozenset(
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

FORBIDDEN_E2E_TRUE_FLAGS = frozenset(
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

E2E_REQUIRED_SESSION_FIELDS = ("session_id", "project_id", "project_profile")
E2E_REQUIRED_ARTIFACTS = ("current_blueprint", "approved_manifest", "validation_gate")


def _json_dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _payload_hash(value: Any) -> str:
    return hashlib.sha256(_json_dump(value).encode("utf-8")).hexdigest()


def _reject_forbidden(value: Any, *, context: str = "dib_e2e_scenario") -> None:
    def walk(node: Any, path: str) -> None:
        if isinstance(node, dict):
            for key, item in node.items():
                key_text = str(key)
                if key_text in FORBIDDEN_E2E_FIELDS:
                    raise ValueError(f"{context}_forbidden_field:{path}.{key_text}")
                if key_text in FORBIDDEN_E2E_TRUE_FLAGS and item is True:
                    raise ValueError(f"{context}_forbidden_flag:{path}.{key_text}")
                walk(item, f"{path}.{key_text}")
        elif isinstance(node, list):
            for index, item in enumerate(node):
                walk(item, f"{path}[{index}]")

    walk(value, context)


def _step(name: str, status: str, *, contract_id: str | None = None, artifact_id: str | None = None, blocker: str | None = None) -> dict[str, Any]:
    return {
        "name": name,
        "status": status,
        "contract_id": contract_id,
        "artifact_id": artifact_id,
        "blocker": blocker,
    }


def _blocker(code: str, message: str, *, severity: str = "critical") -> dict[str, str]:
    return {"code": code, "severity": severity, "message": message}


def _session_blockers(session: dict[str, Any]) -> list[dict[str, str]]:
    blockers: list[dict[str, str]] = []
    for field in E2E_REQUIRED_SESSION_FIELDS:
        if not session.get(field):
            blockers.append(_blocker(f"DIB_E2E_SESSION_MISSING_{field.upper()}", f"DIB E2E scenario requires session.{field}."))
    for artifact in E2E_REQUIRED_ARTIFACTS:
        if not isinstance(session.get(artifact), dict):
            blockers.append(_blocker(f"DIB_E2E_ARTIFACT_MISSING_{artifact.upper()}", f"DIB E2E scenario requires {artifact}."))
    return blockers


def build_dib_e2e_scenario_report(
    session: dict[str, Any],
    *,
    scenario_id: str = "baseline",
    events: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build a post-freeze end-to-end DIB scenario report.

    This helper verifies the implemented DIB user flow using persisted session
    artifacts only. It does not call ProjectRunWorkflow, does not assemble a
    Snapshot, does not create a Decision Pack, does not enable AI Provider, and
    does not perform external network fetches.
    """

    _reject_forbidden(session, context="dib_e2e_session")
    for event in events or []:
        _reject_forbidden(event, context="dib_e2e_event")

    blockers = _session_blockers(session)
    steps: list[dict[str, Any]] = [
        _step("project_context_bound", "passed" if session.get("project_id") else "blocked", artifact_id=str(session.get("project_id") or "")),
        _step("dib_session_available", "passed" if session.get("session_id") else "blocked", artifact_id=str(session.get("session_id") or "")),
        _step(
            "dynamic_input_blueprint_available",
            "passed" if isinstance(session.get("current_blueprint"), dict) else "blocked",
            contract_id=(session.get("current_blueprint") or {}).get("contract_id") if isinstance(session.get("current_blueprint"), dict) else None,
            artifact_id=(session.get("current_blueprint") or {}).get("blueprint_id") if isinstance(session.get("current_blueprint"), dict) else None,
        ),
        _step(
            "approved_input_manifest_available",
            "passed" if isinstance(session.get("approved_manifest"), dict) else "blocked",
            contract_id=(session.get("approved_manifest") or {}).get("contract_id") if isinstance(session.get("approved_manifest"), dict) else None,
            artifact_id=(session.get("approved_manifest") or {}).get("manifest_id") if isinstance(session.get("approved_manifest"), dict) else None,
        ),
        _step(
            "manifest_validation_gate_available",
            "passed" if isinstance(session.get("validation_gate"), dict) else "blocked",
            contract_id=(session.get("validation_gate") or {}).get("contract_id") if isinstance(session.get("validation_gate"), dict) else None,
            artifact_id=(session.get("validation_gate") or {}).get("gate_id") if isinstance(session.get("validation_gate"), dict) else None,
        ),
    ]

    readiness: dict[str, Any] | None = None
    controlled_finance: dict[str, Any] | None = None
    snapshot_handoff: dict[str, Any] | None = None

    if not blockers:
        readiness = build_manifest_run_readiness(session, scenario_id=scenario_id)
        if readiness.get("ready_for_project_run"):
            steps.append(_step("manifest_to_run_readiness", "passed", contract_id="dib.project_run.manifest_gate.v1", artifact_id=(readiness.get("manifest_gate") or {}).get("gate_id")))
        else:
            steps.append(_step("manifest_to_run_readiness", "blocked", blocker="DIB_E2E_READINESS_BLOCKED"))
            blockers.extend(list(readiness.get("blockers") or []))

    if not blockers:
        controlled_finance = execute_controlled_finance_from_dib_session(session, scenario_id=scenario_id)
        if controlled_finance.get("status") == "executed":
            steps.append(_step("controlled_finance_executed", "passed", contract_id=controlled_finance.get("contract_id"), artifact_id=controlled_finance.get("payload_hash")))
        else:
            steps.append(_step("controlled_finance_executed", "blocked", blocker="DIB_E2E_CONTROLLED_FINANCE_BLOCKED"))
            blockers.extend(list(controlled_finance.get("blockers") or []))

    if not blockers:
        snapshot_handoff = build_dib_snapshot_projection_handoff(session, scenario_id=scenario_id)
        if snapshot_handoff.get("status") == "prepared":
            steps.append(_step("snapshot_projection_handoff_prepared", "passed", contract_id=snapshot_handoff.get("contract_id"), artifact_id=snapshot_handoff.get("handoff_id")))
        else:
            steps.append(_step("snapshot_projection_handoff_prepared", "blocked", blocker="DIB_E2E_SNAPSHOT_HANDOFF_BLOCKED"))
            blockers.extend(list(snapshot_handoff.get("blockers") or []))

    event_types = {str(event.get("event_type") or "") for event in (events or []) if isinstance(event, dict)}
    audit_events_present = bool(event_types.intersection({"security.rbac.granted", "security.rbac.denied"}))
    steps.append(_step("session_events_available", "passed" if events is not None else "not_checked", artifact_id=str(len(events or []))))
    steps.append(_step("security_audit_events_observed", "passed" if audit_events_present else "not_checked", artifact_id=",".join(sorted(event_types)) if event_types else None))

    status = "passed" if not blockers else "blocked"
    payload_material = {
        "scenario_id": scenario_id,
        "session_id": session.get("session_id"),
        "project_id": session.get("project_id"),
        "step_statuses": [(step["name"], step["status"]) for step in steps],
        "blocker_codes": [blocker.get("code") for blocker in blockers],
        "readiness_hash": _payload_hash(readiness) if readiness else None,
        "controlled_finance_hash": _payload_hash(controlled_finance) if controlled_finance else None,
        "snapshot_handoff_hash": _payload_hash(snapshot_handoff) if snapshot_handoff else None,
    }
    report = {
        "e2e_scenario_id": DIB_E2E_SCENARIO_ID,
        "contract_id": "dib.e2e.scenario_report.v1",
        "status": status,
        "project_id": str(session.get("project_id") or ""),
        "session_id": str(session.get("session_id") or ""),
        "scenario_id": scenario_id,
        "steps": steps,
        "blockers": blockers,
        "readiness": readiness,
        "controlled_finance_status": (controlled_finance or {}).get("status"),
        "snapshot_projection_handoff_status": (snapshot_handoff or {}).get("status"),
        "audit_events_present": audit_events_present,
        "event_count": len(events or []),
        "payload_hash": _payload_hash(payload_material),
        "project_run_workflow_mount": "not_called",
        "snapshot_assembly_mount": "not_called",
        "sealed_envelope_created": False,
        "decision_pack_created": False,
        "input_source": "approved_input_manifest_only",
        "external_fetch_enabled": False,
        "ai_provider_enabled": False,
        "finance_wiring_enabled": False,
        "snapshot_wiring_enabled": False,
        "snapshot_mutation": False,
        "frozen_runtime_files_mutated": False,
        "created_at": now_iso(),
    }
    _reject_forbidden(report, context="dib_e2e_report")
    return report


def dib_e2e_scenario_status() -> dict[str, Any]:
    return {
        "e2e_scenario_id": DIB_E2E_SCENARIO_ID,
        "status": DIB_E2E_SCENARIO_STATUS,
        "source": DIB_E2E_SCENARIO_SOURCE,
        "report_contract_id": "dib.e2e.scenario_report.v1",
        "required_flow": [
            "project_context_bound",
            "dib_session_available",
            "dynamic_input_blueprint_available",
            "approved_input_manifest_available",
            "manifest_validation_gate_available",
            "manifest_to_run_readiness",
            "controlled_finance_executed",
            "snapshot_projection_handoff_prepared",
            "session_events_available",
        ],
        "project_run_workflow_mount": "not_called",
        "snapshot_assembly_mount": "not_called",
        "sealed_envelope_created": False,
        "decision_pack_created": False,
        "external_fetch_enabled": False,
        "ai_provider_enabled": False,
        "finance_wiring_enabled": False,
        "snapshot_wiring_enabled": False,
        "frozen_runtime_files_mutated": False,
    }
