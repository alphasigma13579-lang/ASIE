from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qs, urlparse

from backend.dib_module_adapters import execute_dib_module_adapter
from backend.dib_persistence import DIBPersistenceError, DIBPersistenceStore, create_dib_persistence_store
from backend.dib_session_continuity import DIB_SESSION_CONTINUITY_ID, list_dib_sessions_for_project

DIB_API_ID = "DIB-LIVE-002D-API-v1"
DIB_API_STATUS = "post_freeze_controlled_api"
DIB_API_SOURCE = "docs/EKB/EKB-02-Source-of-Truth-Matrix.md"

FORBIDDEN_DIB_API_FIELDS = frozenset(
    {
        "raw_prompt",
        "prompt_template",
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
    {"method": "POST", "path": "/api/dib/sessions/{session_id}/blueprints", "purpose": "Build or save a Dynamic Input Blueprint."},
    {"method": "POST", "path": "/api/dib/sessions/{session_id}/approved-manifests", "purpose": "Build or save an Approved Input Manifest."},
    {"method": "POST", "path": "/api/dib/sessions/{session_id}/validation-gates", "purpose": "Build or save a Manifest Validation Gate."},
    {"method": "GET", "path": "/api/dib/sessions/{session_id}/events", "purpose": "List DIB session events and audit hashes."},
    {"method": "POST", "path": "/api/dib/sessions/{session_id}/close", "purpose": "Close a DIB session without snapshot mutation."},
)


class DIBApiError(ValueError):
    def __init__(self, code: str, status: int = 400) -> None:
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
                    raise DIBApiError(f"{context}_forbidden_field:{path}.{key_text}", 422)
                if key_text in FORBIDDEN_DIB_API_TRUE_FLAGS and item is True:
                    raise DIBApiError(f"{context}_forbidden_flag:{path}.{key_text}", 422)
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
        request_payload = dict(payload or {})
        _reject_forbidden_api_payload(request_payload)
        parts = _parts(path)
        try:
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
                    return DIBApiResponse(200, {"session": self.store.load_session(session_id)})
                if method == "GET" and tail == ["events"]:
                    return DIBApiResponse(200, {"events": self.store.list_events(session_id)})
                if method == "POST" and tail == ["blueprints"]:
                    return self._save_or_build_blueprint(session_id, request_payload)
                if method == "POST" and tail == ["approved-manifests"]:
                    return self._save_or_build_manifest(session_id, request_payload)
                if method == "POST" and tail == ["validation-gates"]:
                    return self._save_or_build_gate(session_id, request_payload)
                if method == "POST" and tail == ["close"]:
                    return DIBApiResponse(200, {"session": self.store.close_session(session_id), "snapshot_mutation": False})
        except DIBPersistenceError as exc:
            raise DIBApiError(str(exc), 422) from exc
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

    def _save_or_build_blueprint(self, session_id: str, payload: dict[str, Any]) -> DIBApiResponse:
        if isinstance(payload.get("blueprint"), dict):
            blueprint = dict(payload["blueprint"])
        else:
            session = self.store.load_session(session_id)
            project_profile = dict(payload.get("project_profile") or session["project_profile"])
            items = list(payload.get("items") or [])
            if not items and isinstance(payload.get("intake_payload"), dict):
                intake = execute_dib_module_adapter(
                    "module.data_intake",
                    {
                        "intake_payload": dict(payload["intake_payload"]),
                        "existing_items": list(payload.get("existing_items") or []),
                    },
                )
                items = list(intake.get("mapped_items") or [])
            blueprint = execute_dib_module_adapter(
                "module.dynamic_input_blueprint",
                {
                    "project_profile": project_profile,
                    "items": items,
                    "source": str(payload.get("source") or "dib_api"),
                },
            )
        saved = self.store.save_blueprint(session_id, blueprint)
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
