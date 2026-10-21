from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import math
from urllib.parse import parse_qs, urlparse

from backend.dib_controlled_finance_wiring import (
    DIB_CONTROLLED_FINANCE_WIRING_ID,
    controlled_finance_wiring_status,
    execute_controlled_finance_from_dib_session,
)
from backend.dib_e2e_scenario import DIB_E2E_SCENARIO_ID, build_dib_e2e_scenario_report, dib_e2e_scenario_status
from backend.dib_intake_item_governance import (
    DIB_INTAKE_ITEM_GOVERNANCE_ID,
    apply_governed_item_decision,
    intake_item_governance_status,
    preview_intake_item_mapping,
    resolve_template_registry_surface,
)
from backend.dib_manifest_run_readiness import (
    DIB_MANIFEST_RUN_READINESS_ID,
    build_manifest_run_readiness,
    manifest_run_readiness_status,
)
from backend.dib_module_adapters import execute_dib_module_adapter
from backend.dib_persistence import DIBPersistenceError, DIBPersistenceStore, create_dib_persistence_store
from backend.dib_session_continuity import DIB_SESSION_CONTINUITY_ID, list_dib_sessions_for_project
from backend.dib_snapshot_projection_handoff import (
    DIB_SNAPSHOT_PROJECTION_HANDOFF_ID,
    build_dib_snapshot_projection_handoff,
    snapshot_projection_handoff_status,
)

DIB_API_ID = "DIB-LIVE-002D-API-v1"
DIB_API_STATUS = "post_freeze_controlled_api"
DIB_API_SOURCE = "docs/EKB/EKB-02-Source-of-Truth-Matrix.md"

FORBIDDEN_DIB_API_FIELDS = frozenset(
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

FORBIDDEN_DIB_API_TRUE_FLAGS = frozenset(
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

DIB_API_ROUTES: tuple[dict[str, Any], ...] = (
    {"method": "GET", "path": "/api/dib/status", "purpose": "Read DIB API status and disabled wiring flags."},
    {"method": "POST", "path": "/api/dib/sessions", "purpose": "Start a DIB session from a governed project profile."},
    {"method": "GET", "path": "/api/dib/sessions?project_id={project_id}", "purpose": "List resumable DIB sessions for one ASIE project."},
    {"method": "GET", "path": "/api/dib/sessions/{session_id}", "purpose": "Load a persisted DIB session."},
    {"method": "POST", "path": "/api/dib/sessions/{session_id}/template-registry", "purpose": "Resolve Template Registry and Question Registry for the session project."},
    {"method": "POST", "path": "/api/dib/sessions/{session_id}/intake-items", "purpose": "Preview governed manual, CSV, or supplier quote text intake items."},
    {"method": "POST", "path": "/api/dib/sessions/{session_id}/item-decisions", "purpose": "Apply a governed Customer Item Decision before Manifest approval."},
    {"method": "POST", "path": "/api/dib/sessions/{session_id}/blueprints", "purpose": "Build or save a Dynamic Input Blueprint."},
    {"method": "POST", "path": "/api/dib/sessions/{session_id}/approved-manifests", "purpose": "Build or save an Approved Input Manifest."},
    {"method": "POST", "path": "/api/dib/sessions/{session_id}/validation-gates", "purpose": "Build or save a Manifest Validation Gate."},
    {"method": "POST", "path": "/api/dib/sessions/{session_id}/project-run-readiness", "purpose": "Build Manifest-to-Run readiness without executing Finance or Snapshot."},
    {"method": "POST", "path": "/api/dib/sessions/{session_id}/controlled-finance", "purpose": "Execute controlled Finance from Approved Input Manifest only, without ProjectRunWorkflow or Snapshot."},
    {"method": "POST", "path": "/api/dib/sessions/{session_id}/snapshot-projection-handoff", "purpose": "Prepare DIB Snapshot lineage and projection support handoff without assembling Snapshot."},
    {"method": "POST", "path": "/api/dib/sessions/{session_id}/e2e-scenario", "purpose": "Build a DIB end-to-end scenario report without ProjectRunWorkflow or Snapshot Assembly."},
    {"method": "GET", "path": "/api/dib/sessions/{session_id}/events", "purpose": "List DIB session events and audit hashes."},
    {"method": "POST", "path": "/api/dib/sessions/{session_id}/close", "purpose": "Close a DIB session without snapshot mutation."},
)


DIB_SAFE_ERROR_CODES = frozenset(['canonical_admission_invalid_operation_id', 'canonical_admission_invalid_idempotency_key', 'canonical_admission_invalid_expected_manifest_id', 'canonical_admission_invalid_expected_manifest_payload_hash', 'canonical_admission_invalid_expected_gate_id', 'canonical_admission_invalid_expected_gate_payload_hash', 'canonical_admission_blueprint_session_mismatch', 'canonical_admission_manifest_session_mismatch', 'canonical_admission_gate_session_mismatch', 'stale_gate_lineage', 'canonical_admission_forbidden_fields', 'canonical_admission_unknown_fields', 'dib_item_decision_invalid', 'dib_item_target_changed', 'dib_item_value_invalid', 'dib_item_reason_required', 'client_owned_manifest_rejected', 'client_owned_gate_rejected', 'aas_registry_freeze_hash_changed', 'approved_manifest_requires_blueprint', 'approved_manifest_requires_persisted_blueprint', 'authentication_required', 'blueprint_session_lineage_mismatch', 'canonical_admission_blueprint_hash_mismatch', 'canonical_admission_blueprint_id_mismatch', 'canonical_admission_blueprint_lineage_hash_mismatch', 'canonical_admission_blueprint_missing', 'canonical_admission_command_object_required', 'canonical_admission_gate_blueprint_mismatch', 'canonical_admission_gate_hash_mismatch', 'canonical_admission_gate_lineage_scope_mismatch', 'canonical_admission_gate_missing', 'canonical_admission_gate_not_passed', 'canonical_admission_invalid_scenario', 'canonical_admission_manifest_hash_mismatch', 'canonical_admission_manifest_id_mismatch', 'canonical_admission_manifest_lineage_hash_mismatch', 'canonical_admission_manifest_lineage_scope_mismatch', 'canonical_admission_manifest_missing', 'canonical_admission_manifest_not_approved', 'canonical_admission_normalized_inputs_missing', 'canonical_admission_project_lineage_mismatch', 'canonical_admission_server_authority_missing', 'canonical_finance_result_missing', 'canonical_project_run_executor_unavailable', 'canonical_project_run_id_mismatch', 'canonical_project_run_project_mismatch', 'canonical_project_run_result_invalid', 'canonical_project_run_workflow_not_accepted', 'canonical_snapshot_id_mismatch', 'canonical_snapshot_not_immutable', 'customer_item_decision_requires_item_and_decision', 'dib_api_forbidden_field', 'dib_api_forbidden_flag', 'dib_api_route_not_found', 'dib_blueprint_contract_invalid', 'dib_blueprint_identity_invalid', 'dib_blueprint_integrity_invalid', 'dib_blueprint_items_invalid', 'dib_blueprint_object_required', 'dib_blueprint_origin_required', 'dib_blueprint_project_mismatch', 'dib_blueprint_revision_invalid', 'dib_blueprint_write_conflict', 'dib_blueprint_write_contract_invalid', 'dib_contract_admission_does_not_match_runtime', 'dib_http_forbidden_field', 'dib_http_forbidden_flag', 'dib_http_method_not_allowed', 'dib_http_route_not_found', 'dib_module_admission_does_not_match_runtime', 'dib_operation_failed', 'dib_organization_context_required', 'dib_principal_session_required', 'dib_project_not_found', 'dib_project_ownership_resolver_required', 'dib_quarantine_context_forbidden', 'dib_request_invalid', 'dib_resource_not_found', 'dib_session_closed', 'dib_session_not_found', 'dib_session_query_requires_project_id', 'dib_session_requires_project_profile', 'dib_socket_admission_does_not_match_runtime', 'dib_tenant_context_required', 'dib_user_context_required', 'invalid_content_length', 'invalid_expected_revision', 'invalid_json', 'json_object_required', 'manifest_data_access_project_mismatch', 'manifest_session_lineage_mismatch', 'manifest_validation_requires_manifest', 'organization_required', 'permission_denied', 'request_body_too_large', 'stale_blueprint_lineage', 'stale_manifest_lineage', 'unknown_customer_item_decision', 'unsupported_dib_data_intake_type', 'unsupported_governed_dib_intake_payload', 'validation_gate_requires_persisted_manifest'])

def safe_dib_error_code(code: object) -> str:
    """Expose only registered literal errors, never payload keys or exception details."""
    if type(code) is not str:
        return "dib_operation_failed"
    # Canonical admission appends client field names; retain only its fixed category.
    for prefix in ("canonical_admission_forbidden_fields:", "canonical_admission_unknown_fields:"):
        if code.startswith(prefix):
            return prefix[:-1]
    return code if code in DIB_SAFE_ERROR_CODES else "dib_operation_failed"


class DIBApiError(ValueError):
    def __init__(self, code: str, status: int = 400) -> None:
        code = safe_dib_error_code(code)
        if code == "dib_operation_failed":
            status = 500
        super().__init__(code)
        self.code = code
        self.status = status


@dataclass(frozen=True)
class DIBApiResponse:
    status: int
    payload: dict[str, Any]

    def to_public(self) -> dict[str, Any]:
        return {
            "status": self.status,
            **self.payload,
            "api_id": DIB_API_ID,
            "session_continuity_id": DIB_SESSION_CONTINUITY_ID,
            "intake_item_governance_id": DIB_INTAKE_ITEM_GOVERNANCE_ID,
            "manifest_run_readiness_id": DIB_MANIFEST_RUN_READINESS_ID,
            "controlled_finance_wiring_id": DIB_CONTROLLED_FINANCE_WIRING_ID,
            "snapshot_projection_handoff_id": DIB_SNAPSHOT_PROJECTION_HANDOFF_ID,
            "e2e_scenario_id": DIB_E2E_SCENARIO_ID,
            "external_fetch_enabled": False,
            "ai_provider_enabled": False,
            "finance_wiring_enabled": False,
            "snapshot_wiring_enabled": False,
        }


def _reject_forbidden_api_payload(payload: Any, *, context: str = "dib_api") -> None:
    def walk(value: Any, path: str) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                key_text = str(key)
                if key_text in FORBIDDEN_DIB_API_FIELDS:
                    raise DIBApiError("dib_api_forbidden_field", 422)
                if key_text in FORBIDDEN_DIB_API_TRUE_FLAGS and item is True:
                    raise DIBApiError("dib_api_forbidden_flag", 422)
                walk(item, f"{path}.{key_text}")
        elif isinstance(value, list):
            for index, item in enumerate(value):
                walk(item, f"{path}[{index}]")

    walk(payload, context)


def _parts(path: str) -> list[str]:
    cleaned = urlparse(path).path.strip("/")
    return cleaned.split("/") if cleaned else []


def _query(path: str) -> dict[str, list[str]]:
    return parse_qs(urlparse(path).query, keep_blank_values=False)


def _query_value(path: str, key: str) -> str:
    values = _query(path).get(key) or []
    return str(values[0] if values else "").strip()


def _query_bool(path: str, key: str, *, default: bool = False) -> bool:
    value = _query_value(path, key).lower()
    if not value:
        return default
    return value in {"1", "true", "yes", "on"}


class DIBApiController:
    def __init__(self, store: DIBPersistenceStore | None = None) -> None:
        self.store = store or create_dib_persistence_store()

    def status(self) -> dict[str, Any]:
        persistence_status = self.store.status()
        return {
            "api_id": DIB_API_ID,
            "session_continuity_id": DIB_SESSION_CONTINUITY_ID,
            "intake_item_governance_id": DIB_INTAKE_ITEM_GOVERNANCE_ID,
            "manifest_run_readiness_id": DIB_MANIFEST_RUN_READINESS_ID,
            "controlled_finance_wiring_id": DIB_CONTROLLED_FINANCE_WIRING_ID,
            "snapshot_projection_handoff_id": DIB_SNAPSHOT_PROJECTION_HANDOFF_ID,
            "e2e_scenario_id": DIB_E2E_SCENARIO_ID,
            "intake_item_governance": intake_item_governance_status(),
            "manifest_run_readiness": manifest_run_readiness_status(),
            "controlled_finance_wiring": controlled_finance_wiring_status(),
            "snapshot_projection_handoff": snapshot_projection_handoff_status(),
            "e2e_scenario": dib_e2e_scenario_status(),
            "status": DIB_API_STATUS,
            "source": DIB_API_SOURCE,
            "route_count": len(DIB_API_ROUTES),
            "routes": list(DIB_API_ROUTES),
            "persistence": persistence_status,
            "external_fetch_enabled": False,
            "ai_provider_enabled": False,
            "finance_wiring_enabled": False,
            "snapshot_wiring_enabled": False,
            "http_server_mutation_required": False,
            "frozen_runtime_files_mutated": False,
        }

    def dispatch(self, method: str, path: str, payload: dict[str, Any] | None = None) -> DIBApiResponse:
        method = method.upper().strip()
        parts = _parts(path)
        try:
            if payload is not None and type(payload) is not dict:
                raise DIBApiError("json_object_required", 400)
            request_payload = dict(payload or {})
            _reject_forbidden_api_payload(request_payload)
            if method == "GET" and parts == ["api", "dib", "status"]:
                return DIBApiResponse(200, {"dib_api": self.status()})
            if method == "POST" and parts == ["api", "dib", "sessions"]:
                return self._start_session(request_payload)
            if method == "GET" and parts == ["api", "dib", "sessions"]:
                return self._list_sessions(path)
            if len(parts) >= 4 and parts[:3] == ["api", "dib", "sessions"]:
                session_id = parts[3]
                tail = parts[4:]
                if method == "GET" and not tail:
                    return DIBApiResponse(200, {"session": self.store.load_session(session_id, allow_legacy_read=True)})
                if method == "GET" and tail == ["events"]:
                    return DIBApiResponse(200, {"events": self.store.list_events(session_id)})
                if method == "POST" and tail == ["template-registry"]:
                    return self._resolve_template_registry(session_id, request_payload)
                if method == "POST" and tail == ["intake-items"]:
                    return self._preview_intake_items(session_id, request_payload)
                if method == "POST" and tail == ["item-decisions"]:
                    return self._apply_item_decision(session_id, request_payload)
                if method == "POST" and tail == ["blueprints"]:
                    return self._save_or_build_blueprint(session_id, request_payload)
                if method == "POST" and tail == ["approved-manifests"]:
                    return self._save_or_build_manifest(session_id, request_payload)
                if method == "POST" and tail == ["validation-gates"]:
                    return self._save_or_build_gate(session_id, request_payload)
                if method == "POST" and tail == ["project-run-readiness"]:
                    return self._build_project_run_readiness(session_id, request_payload)
                if method == "POST" and tail == ["controlled-finance"]:
                    return self._execute_controlled_finance(session_id, request_payload)
                if method == "POST" and tail == ["snapshot-projection-handoff"]:
                    return self._build_snapshot_projection_handoff(session_id, request_payload)
                if method == "POST" and tail == ["e2e-scenario"]:
                    return self._build_e2e_scenario_report(session_id, request_payload)
                if method == "POST" and tail == ["close"]:
                    return DIBApiResponse(200, {"session": self.store.close_session(session_id), "snapshot_mutation": False})
        except DIBApiError:
            raise
        except DIBPersistenceError as exc:
            code = safe_dib_error_code(str(exc))
            status = 500 if code == "dib_operation_failed" else (409 if code in {"dib_blueprint_origin_required", "dib_blueprint_write_conflict", "dib_blueprint_integrity_invalid", "dib_session_closed"} else 422)
            raise DIBApiError(code, status) from exc
        except ValueError as exc:
            raise DIBApiError(safe_dib_error_code(str(exc)), 422) from exc
        except Exception as exc:
            raise DIBApiError("dib_operation_failed", 500) from exc
        raise DIBApiError("dib_api_route_not_found", 404)

    def _list_sessions(self, path: str) -> DIBApiResponse:
        project_id = _query_value(path, "project_id")
        if not project_id:
            raise DIBApiError("dib_session_query_requires_project_id", 400)
        sessions = list_dib_sessions_for_project(
            self.store,
            project_id,
            include_closed=_query_bool(path, "include_closed", default=False),
            limit=_query_value(path, "limit") or 10,
        )
        return DIBApiResponse(
            200,
            {
                "sessions": sessions,
                "latest_session": sessions[0] if sessions else None,
                "resume_available": bool(sessions),
                "project_id": project_id,
                "snapshot_mutation": False,
                "finance_wiring_enabled": False,
            },
        )

    def _start_session(self, payload: dict[str, Any]) -> DIBApiResponse:
        project_profile = payload.get("project_profile") if isinstance(payload.get("project_profile"), dict) else payload
        if not isinstance(project_profile, dict) or not project_profile.get("project_id"):
            raise DIBApiError("dib_session_requires_project_profile", 400)
        session = self.store.start_session(dict(project_profile))
        return DIBApiResponse(201, {"session": session, "snapshot_mutation": False})

    def _resolve_template_registry(self, session_id: str, payload: dict[str, Any]) -> DIBApiResponse:
        session = self.store.load_session(session_id)
        project_profile = payload.get("project_profile") if isinstance(payload.get("project_profile"), dict) else session["project_profile"]
        resolved = resolve_template_registry_surface(dict(project_profile), str(payload.get("template_id") or "") or None)
        return DIBApiResponse(200, {"template_registry": resolved, "snapshot_mutation": False})

    def _preview_intake_items(self, session_id: str, payload: dict[str, Any]) -> DIBApiResponse:
        session = self.store.load_session(session_id)
        existing_items = payload.get("existing_items")
        if not isinstance(existing_items, list):
            existing_items = list((session.get("current_blueprint") or {}).get("items") or [])
        intake = preview_intake_item_mapping(payload, [dict(item) for item in existing_items if isinstance(item, dict)])
        return DIBApiResponse(
            200,
            {
                "intake": intake,
                "mapped_items": list(intake.get("mapped_items") or []),
                "unmatched_rows": list(intake.get("unmatched_rows") or []),
                "snapshot_mutation": False,
                "finance_wiring_enabled": False,
            },
        )

    def _apply_item_decision(self, session_id: str, payload: dict[str, Any]) -> DIBApiResponse:
        self.store.load_session(session_id)
        item = payload.get("item")
        decision = payload.get("decision")
        if not isinstance(item, dict) or not isinstance(decision, dict):
            raise DIBApiError("customer_item_decision_requires_item_and_decision", 400)
        result = apply_governed_item_decision(dict(item), dict(decision))
        return DIBApiResponse(
            200,
            {
                "item_decision": result,
                "item": result.get("item"),
                "snapshot_mutation": False,
                "finance_wiring_enabled": False,
            },
        )

    def _build_project_run_readiness(self, session_id: str, payload: dict[str, Any]) -> DIBApiResponse:
        session = self.store.load_session(session_id)
        readiness = build_manifest_run_readiness(session, scenario_id=str(payload.get("scenario_id") or "baseline"))
        return DIBApiResponse(
            200,
            {
                "project_run_readiness": readiness,
                "ready_for_project_run": bool(readiness.get("ready_for_project_run")),
                "project_run_request": readiness.get("project_run_request"),
                "finance_wiring_enabled": False,
                "snapshot_mutation": False,
            },
        )

    def _execute_controlled_finance(self, session_id: str, payload: dict[str, Any]) -> DIBApiResponse:
        session = self.store.load_session(session_id)
        controlled = execute_controlled_finance_from_dib_session(session, scenario_id=str(payload.get("scenario_id") or "baseline"))
        return DIBApiResponse(
            200,
            {
                "controlled_finance": controlled,
                "controlled_finance_executed": controlled.get("status") == "executed",
                "finance_engine_execution_status": controlled.get("finance_engine_execution_status"),
                "finance_wiring_enabled": False,
                "snapshot_mutation": False,
            },
        )

    def _build_snapshot_projection_handoff(self, session_id: str, payload: dict[str, Any]) -> DIBApiResponse:
        session = self.store.load_session(session_id)
        handoff = build_dib_snapshot_projection_handoff(session, scenario_id=str(payload.get("scenario_id") or "baseline"))
        return DIBApiResponse(
            200,
            {
                "snapshot_projection_handoff": handoff,
                "snapshot_projection_handoff_prepared": handoff.get("status") == "prepared",
                "sealed_envelope_created": False,
                "snapshot_mutation": False,
                "finance_wiring_enabled": False,
            },
        )

    def _build_e2e_scenario_report(self, session_id: str, payload: dict[str, Any]) -> DIBApiResponse:
        session = self.store.load_session(session_id)
        events = self.store.list_events(session_id)
        report = build_dib_e2e_scenario_report(session, scenario_id=str(payload.get("scenario_id") or "baseline"), events=events)
        return DIBApiResponse(
            200,
            {
                "e2e_scenario": report,
                "e2e_scenario_passed": report.get("status") == "passed",
                "project_run_workflow_mount": "not_called",
                "snapshot_mutation": False,
                "finance_wiring_enabled": False,
            },
        )

    def _save_or_build_blueprint(self, session_id: str, payload: dict[str, Any]) -> DIBApiResponse:
        if "item_decisions" in payload:
            if (set(payload) - {"contract_id", "expected_original", "item_decisions"}
                    or type(payload["item_decisions"]) is not list or not payload["item_decisions"]):
                raise DIBApiError("dib_item_decision_invalid", 422)
            session = self.store.load_session(session_id)
            blueprint = session.get("current_blueprint")
            if not isinstance(blueprint, dict):
                raise DIBApiError("dib_blueprint_origin_required", 409)
        elif isinstance(payload.get("blueprint"), dict):
            blueprint = dict(payload["blueprint"])
        else:
            session = self.store.load_session(session_id)
            project_profile = dict(payload.get("project_profile") or session["project_profile"])
            items = list(payload.get("items") or [])
            current = session.get("current_blueprint")
            if not items and isinstance(payload.get("intake_payload"), dict):
                persisted_items = current.get("items", []) if isinstance(current, dict) else None
                intake = execute_dib_module_adapter(
                    "module.data_intake",
                    {
                        "intake_payload": dict(payload["intake_payload"]),
                        "existing_items": persisted_items if persisted_items is not None else list(payload.get("existing_items") or []),
                    },
                )
                items = list(intake.get("mapped_items") or [])
                if persisted_items is not None:
                    identities = {item["input_key"]: item["item_id"] for item in persisted_items}
                    items = [item | {"item_id": identities[item["input_key"]]} if item["input_key"] in identities else item for item in items]
            if isinstance(current, dict):
                # Preserve persisted identities; the store merges submitted items under CAS.
                blueprint = current | {"items": items}
            else:
                blueprint = execute_dib_module_adapter(
                    "module.dynamic_input_blueprint",
                    {
                        "project_profile": project_profile,
                        "items": items,
                        "source": str(payload.get("source") or "dib_api"),
                    },
                )
        saved = self.store.save_blueprint(
            session_id, blueprint, expected_original=payload.get("expected_original"),
            command_contract=payload.get("contract_id"), item_decisions=payload.get("item_decisions"),
        )
        return DIBApiResponse(201, {"blueprint": saved, "snapshot_mutation": False})

    def _save_or_build_manifest(self, session_id: str, payload: dict[str, Any]) -> DIBApiResponse:
        if isinstance(payload.get("manifest"), dict):
            manifest = dict(payload["manifest"])
        else:
            blueprint = payload.get("blueprint")
            if not isinstance(blueprint, dict):
                session = self.store.load_session(session_id)
                blueprint = session.get("current_blueprint")
            if not isinstance(blueprint, dict):
                raise DIBApiError("approved_manifest_requires_blueprint", 400)
            manifest = execute_dib_module_adapter("module.approved_input_manifest", {"blueprint": dict(blueprint)})
        saved = self.store.save_approved_manifest(session_id, manifest)
        return DIBApiResponse(201, {"approved_manifest": saved, "finance_wiring_enabled": False, "snapshot_mutation": False})

    def _save_or_build_gate(self, session_id: str, payload: dict[str, Any]) -> DIBApiResponse:
        if isinstance(payload.get("gate"), dict):
            gate = dict(payload["gate"])
        else:
            manifest = payload.get("manifest")
            if not isinstance(manifest, dict):
                session = self.store.load_session(session_id)
                manifest = session.get("approved_manifest")
            if not isinstance(manifest, dict):
                raise DIBApiError("manifest_validation_requires_manifest", 400)
            gate = execute_dib_module_adapter("module.manifest_validation_gate", {"manifest": dict(manifest)})
        saved = self.store.save_validation_gate(session_id, gate)
        return DIBApiResponse(201, {"validation_gate": saved, "finance_wiring_enabled": False, "snapshot_mutation": False})

    def close(self) -> None:
        self.store.close()


def create_dib_api_controller(store: DIBPersistenceStore | None = None) -> DIBApiController:
    return DIBApiController(store)


def dib_customer_recovery(session: dict[str, Any], organization_id: str) -> list[dict[str, Any]]:
    """Project stored draft deficits without building a Manifest, Gate, or Finance result."""
    from backend.dib_runtime import FINANCE_REQUIRED_KEYS, APPROVABLE_STATES, ITEM_STATES
    blueprint = session.get("current_blueprint")
    origin = session.get("origin_reference")
    if not blueprint:
        return []
    if not origin:
        return [{"recovery_id": f"dib:{session['session_id']}:legacy-origin", "requirement_code": "DIB_ITEM_INTEGRITY_REVIEW_REQUIRED",
            "reason_key": "dib_item_integrity_review_required", "required": True, "severity": "required",
            "source": {"kind": "dib_blueprint", "organization_id": organization_id, "project_id": session["project_id"], "entity_id": blueprint["blueprint_id"]},
            "target": {"kind": "owner_review"}, "action": {"required_permission": "dib.write", "allowed": False, "responsible_role": "project_editor"},
            "resolution": "unmapped"}]
    items = []
    stored_rows = blueprint.get("items", [])
    valid_rows = isinstance(stored_rows, list) and all(isinstance(row, dict) for row in stored_rows)
    candidates = stored_rows if valid_rows else []
    identities = [row.get("item_id") for row in candidates]
    keys = [row.get("input_key") for row in candidates]
    integrity_invalid = (not valid_rows or any(type(value) is not str or not value for value in identities + keys)
        or len(set(value for value in identities if isinstance(value, str))) != len(identities)
        or len(set(value for value in keys if isinstance(value, str))) != len(keys)
        or any(type(row.get("value_state")) is not str or row["value_state"] not in ITEM_STATES for row in candidates))
    rows = {row.get("input_key"): row for row in candidates if isinstance(row.get("input_key"), str)}
    # A rejected optional/default/custom item also blocks Manifest approval and
    # needs the same exact, version-bound correction target as a required item.
    recovery_keys = list(FINANCE_REQUIRED_KEYS)
    if not integrity_invalid:
        recovery_keys.extend(key for key, row in rows.items()
                             if key not in FINANCE_REQUIRED_KEYS and row["value_state"] == "REJECTED")
    for key in recovery_keys:
        row = rows.get(key)
        if integrity_invalid:
            target, reason = {"kind": "owner_review"}, "DIB_ITEM_INTEGRITY_REVIEW_REQUIRED"
        elif not row:
            target, reason = {"kind": "owner_review"}, "DIB_REQUIRED_ITEM_MISSING"
        else:
            value, state = row.get("value"), row.get("value_state")
            numeric = type(value) in {int, float} and math.isfinite(value)
            if state not in ITEM_STATES or not isinstance(row.get("item_id"), str) or not row["item_id"]:
                target, reason = {"kind": "owner_review"}, "DIB_ITEM_INTEGRITY_REVIEW_REQUIRED"
            elif state in APPROVABLE_STATES and numeric and (value != 0 or state in {"NOT_APPLICABLE", "INTENTIONAL_ZERO"}):
                continue
            else:
                target = {"kind": "dib_item", "session_id": session["session_id"], "blueprint_id": origin["blueprint_id"],
                          "item_id": row["item_id"], "input_key": key, "field_keys": [key]}
                reason = "DIB_ITEM_VALUE_REQUIRED"
        items.append({"recovery_id": f"dib:{session['session_id']}:{key}", "requirement_code": reason, "reason_key": reason.lower(),
            "required": True, "severity": "required", "source": {"kind": "dib_blueprint", "organization_id": organization_id,
                "project_id": session["project_id"], "entity_id": origin["blueprint_id"], "revision": origin["revision"], "payload_hash": origin["payload_hash"]},
            "target": target, "action": {"required_permission": "dib.write", "allowed": False, "responsible_role": "project_editor"},
            "resolution": "unmapped" if target["kind"] == "owner_review" else "unresolved"})
    return items
