from __future__ import annotations

from typing import Any

from backend.contracts import now_iso
from backend.dib_manifest_run_readiness import build_manifest_run_readiness

DIB_CONTROLLED_FINANCE_WIRING_ID = "DIB-COMPLETION-PACKAGE-D-CONTROLLED-FINANCE-WIRING-v1"
DIB_CONTROLLED_FINANCE_WIRING_STATUS = "direct_execution_removed_canonical_project_run_required"
DIB_CONTROLLED_FINANCE_WIRING_SOURCE = "docs/ARCH-BETA-05-CANONICAL-FINANCE-ADMISSION-REPAIR-2026-07-29.md"

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
        "finance",
        "finance_result",
        "finance_inputs",
        "normalized_inputs",
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


def execute_controlled_finance_from_dib_session(
    session: dict[str, Any],
    *,
    scenario_id: str = "baseline",
) -> dict[str, Any]:
    """Fail closed for legacy callers.

    Direct DIB-to-Finance execution was removed by ARCH-BETA-05. The tenant-scoped
    HTTP controller owns the compatibility endpoint and routes an eligible,
    server-owned Manifest chain through the existing ProjectRunWorkflow. Internal
    callers that bypass that controller receive a blocked response and never
    execute Finance or Snapshot Assembly.
    """

    _reject_forbidden(session, context="dib_session")
    readiness = build_manifest_run_readiness(session, scenario_id=scenario_id)
    blockers = list(readiness.get("blockers") or [])
    blockers.append(
        _blocker(
            "DIB_DIRECT_FINANCE_PATH_REMOVED",
            "Direct DIB-to-Finance execution is forbidden; use the tenant-scoped canonical ProjectRunWorkflow admission.",
        )
    )
    return {
        "controlled_finance_wiring_id": DIB_CONTROLLED_FINANCE_WIRING_ID,
        "contract_id": "dib.canonical.project_run.admission.v1",
        "status": "blocked",
        "project_id": str(session.get("project_id") or ""),
        "session_id": str(session.get("session_id") or ""),
        "scenario_id": scenario_id,
        "readiness": readiness,
        "finance": None,
        "blockers": blockers,
        "finance_contract_id": "finance.result.v1",
        "finance_command_contract_id": "finance.calculate.v1",
        "finance_engine_execution_status": "not_executed",
        "project_run_workflow_mount": "required",
        "input_source": "server_owned_approved_input_manifest_only",
        "direct_finance_execution_enabled": False,
        "canonical_project_run_execution_enabled": False,
        "raw_ui_values_accepted": False,
        "raw_ai_values_accepted": False,
        "raw_file_values_accepted": False,
        "external_fetch_enabled": False,
        "ai_provider_enabled": False,
        "finance_wiring_enabled": False,
        "snapshot_wiring_enabled": False,
        "snapshot_mutation": False,
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
        "project_run_workflow_contract": "project.run.workflow.v1",
        "finance_command_contract": "finance.calculate.v1",
        "finance_result_contract": "finance.result.v1",
        "finance_engine_execution_status": "project_run_workflow_only",
        "project_run_workflow_mount": "required",
        "direct_finance_import": False,
        "direct_finance_execution_enabled": False,
        "canonical_project_run_execution_enabled": True,
        "external_fetch_enabled": False,
        "ai_provider_enabled": False,
        "finance_wiring_enabled": False,
        "snapshot_wiring_enabled": True,
        "frozen_project_run_workflow_mutated": False,
        "snapshot_assembly_mutated": False,
    }
