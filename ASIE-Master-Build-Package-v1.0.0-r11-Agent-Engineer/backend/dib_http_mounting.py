from __future__ import annotations

import json
import os
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

from backend.dib_api import DIB_API_ROUTES, DIBApiController, DIBApiError, create_dib_api_controller
from backend.dib_persistence import create_dib_persistence_store
from backend.dib_security_audit_rbac import (
    DIB_SECURITY_AUDIT_RBAC_ID,
    authorize_dib_request,
    build_dib_security_audit_event,
    dib_route_security_policy,
    dib_security_audit_rbac_status,
    extract_dib_session_id_from_path,
    resolve_dib_auth_required,
)
from backend.repository import Repository

DIB_HTTP_MOUNTING_ID = "DIB-LIVE-002H-HTTP-MOUNTING-v1"
DIB_LOCAL_GATEWAY_INTEGRATION_ID = "DIB-LIVE-002I-LOCAL-API-GATEWAY-INTEGRATION-v1"
DIB_HTTP_MOUNTING_STATUS = "post_freeze_http_mounting_overlay"
DIB_HTTP_MOUNTING_SOURCE = "docs/EKB/EKB-02-Source-of-Truth-Matrix.md"

DIB_HTTP_ALLOWED_METHODS = frozenset({"GET", "POST", "OPTIONS"})
DIB_HTTP_DEFAULT_HOST = "127.0.0.1"
DIB_HTTP_DEFAULT_PORT = 8795
DIB_HTTP_MAX_JSON_BODY_BYTES = 1_048_576

FORBIDDEN_DIB_HTTP_FIELDS = frozenset(
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

FORBIDDEN_DIB_HTTP_TRUE_FLAGS = frozenset(
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

DIB_HTTP_ROUTES: tuple[dict[str, Any], ...] = tuple(
    {
        "method": route["method"],
        "path": route["path"],
        "mounting": "direct_controller_dispatch",
        "source_api": "backend.dib_api.DIBApiController",
        "security_policy": dib_route_security_policy(route["method"], route["path"]),
    }
    for route in DIB_API_ROUTES
)


class DIBHttpMountError(ValueError):
    def __init__(self, code: str, status: int = 400) -> None:
        super().__init__(code)
        self.code = code
        self.status = status


@dataclass(frozen=True)
class DIBHttpResponse:
    status: int
    payload: dict[str, Any]

    def to_public(self) -> dict[str, Any]:
        return {
            "status": self.status,
            **self.payload,
            "http_mounting_id": DIB_HTTP_MOUNTING_ID,
            "local_gateway_integration_id": DIB_LOCAL_GATEWAY_INTEGRATION_ID,
            "security_audit_rbac_id": DIB_SECURITY_AUDIT_RBAC_ID,
            "rbac_enforced_on_sidecar": True,
            "production_auth_bypass_blocked": True,
            "external_fetch_enabled": False,
            "ai_provider_enabled": False,
            "finance_wiring_enabled": False,
            "snapshot_wiring_enabled": False,
            "frozen_http_server_mutated": False,
            "frozen_runtime_files_mutated": False,
        }


def _reject_forbidden_http_payload(payload: Any, *, context: str = "dib_http") -> None:
    def walk(value: Any, path: str) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                key_text = str(key)
                if key_text in FORBIDDEN_DIB_HTTP_FIELDS:
                    raise DIBHttpMountError(f"{context}_forbidden_field:{path}.{key_text}", 422)
                if key_text in FORBIDDEN_DIB_HTTP_TRUE_FLAGS and item is True:
                    raise DIBHttpMountError(f"{context}_forbidden_flag:{path}.{key_text}", 422)
                walk(item, f"{path}.{key_text}")
        elif isinstance(value, list):
            for index, item in enumerate(value):
                walk(item, f"{path}[{index}]")

    walk(payload, context)


def _clean_path(path: str) -> str:
    parsed = urlparse(path)
    return parsed.path.rstrip("/") or "/"


def is_dib_http_route(path: str) -> bool:
    clean_path = _clean_path(path)
    return clean_path in {"/api/dib/status", "/api/dib/sessions"} or clean_path.startswith("/api/dib/sessions/")


def _dispatch_path_with_optional_session_query(path: str) -> str:
    parsed = urlparse(path)
    clean_path = _clean_path(path)
    if clean_path == "/api/dib/sessions" and parsed.query:
        return path
    return clean_path


def _resolved_dib_db_path(db_path: str | None = None) -> str:
    if db_path is not None:
        return str(db_path)
    return os.environ.get("ASIE_DIB_DB_PATH", ":memory:").strip() or ":memory:"


def _sidecar_auth_required(path: str) -> bool:
    if _clean_path(path) == "/api/dib/status":
        return False
    return resolve_dib_auth_required(path)


class DIBHttpMount:
    """Freeze-safe local HTTP mount for the governed DIB API controller.

    This object deliberately does not mutate backend/asie_local_api.py at import time,
    does not alter AAS frozen files, and does not start a network listener unless the
    explicit sidecar runner is called by an operator or Docker Compose.
    """

    def __init__(self, controller: DIBApiController | None = None) -> None:
        self.controller = controller or create_dib_api_controller(create_dib_persistence_store(_resolved_dib_db_path()))

    def status(self) -> dict[str, Any]:
        return {
            "mounting_id": DIB_HTTP_MOUNTING_ID,
            "local_gateway_integration_id": DIB_LOCAL_GATEWAY_INTEGRATION_ID,
            "security_audit_rbac_id": DIB_SECURITY_AUDIT_RBAC_ID,
            "status": DIB_HTTP_MOUNTING_STATUS,
            "source": DIB_HTTP_MOUNTING_SOURCE,
            "route_count": len(DIB_HTTP_ROUTES),
            "routes": list(DIB_HTTP_ROUTES),
            "security_audit_rbac": dib_security_audit_rbac_status(),
            "allowed_methods": sorted(DIB_HTTP_ALLOWED_METHODS),
            "mount_strategy": "freeze_safe_dib_http_overlay",
            "uses_controller": "backend.dib_api.DIBApiController",
            "local_sidecar_available": True,
            "local_sidecar_host": DIB_HTTP_DEFAULT_HOST,
            "local_sidecar_port": DIB_HTTP_DEFAULT_PORT,
            "sidecar_auth_required_by_default": True,
            "sidecar_auth_status_exemption": "/api/dib/status",
            "production_auth_bypass_blocked": True,
            "persistence": self.controller.store.status(),
            "external_fetch_enabled": False,
            "ai_provider_enabled": False,
            "finance_wiring_enabled": False,
            "snapshot_wiring_enabled": False,
            "frozen_http_server_mutated": False,
            "frozen_runtime_files_mutated": False,
            "snapshot_assembly_mutated": False,
            "project_run_workflow_mutated": False,
        }

    def matches(self, method: str, path: str) -> bool:
        return method.upper().strip() in DIB_HTTP_ALLOWED_METHODS and is_dib_http_route(path)

    def dispatch(self, method: str, path: str, payload: dict[str, Any] | None = None) -> DIBHttpResponse:
        method = method.upper().strip()
        if method not in DIB_HTTP_ALLOWED_METHODS:
            raise DIBHttpMountError("dib_http_method_not_allowed", 405)
        clean_path = _clean_path(path)
        if not is_dib_http_route(clean_path):
            raise DIBHttpMountError("dib_http_route_not_found", 404)
        request_payload = dict(payload or {})
        _reject_forbidden_http_payload(request_payload)
        try:
            response = self.controller.dispatch(method, _dispatch_path_with_optional_session_query(path), request_payload)
        except DIBApiError as exc:
            raise DIBHttpMountError(exc.code, exc.status) from exc
        return DIBHttpResponse(response.status, response.to_public())

    def close(self) -> None:
        self.controller.close()


def create_dib_http_mount(controller: DIBApiController | None = None, db_path: str | None = None) -> DIBHttpMount:
    if controller is not None:
        return DIBHttpMount(controller)
    return DIBHttpMount(create_dib_api_controller(create_dib_persistence_store(_resolved_dib_db_path(db_path))))


class DIBHttpSidecarHandler(BaseHTTPRequestHandler):
    mount = create_dib_http_mount()
    auth_repo = Repository()

    def _read_json_body(self) -> dict[str, Any]:
        try:
            length = int(self.headers.get("Content-Length", "0") or 0)
        except ValueError as exc:
            raise DIBHttpMountError("invalid_content_length", 400) from exc
        if length < 0:
            raise DIBHttpMountError("invalid_content_length", 400)
        if length > DIB_HTTP_MAX_JSON_BODY_BYTES:
            raise DIBHttpMountError("request_body_too_large", 413)
        if length == 0:
            return {}
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise DIBHttpMountError("invalid_json", 400) from exc
        if not isinstance(payload, dict):
            raise DIBHttpMountError("json_object_required", 400)
        return payload

    def _write_json(self, payload: dict[str, Any], status: int = 200) -> None:
        secured_payload = {
            **payload,
            "security_audit_rbac_id": DIB_SECURITY_AUDIT_RBAC_ID,
            "rbac_enforced_on_sidecar": True,
            "production_auth_bypass_blocked": True,
        }
        raw = json.dumps(secured_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type, X-ASIE-Organization-Id")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.end_headers()
        self.wfile.write(raw)

    def _bearer_token(self) -> str | None:
        value = self.headers.get("Authorization", "")
        return value[7:].strip() if value.startswith("Bearer ") and value[7:].strip() else None

    def _record_gateway_audit(
        self,
        method: str,
        status: int,
        payload: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        session_id = extract_dib_session_id_from_path(self.path)
        if not session_id:
            return
        principal = getattr(self, "_dib_gateway_principal", None)
        authorization = getattr(self, "_dib_gateway_authorization", None) or dib_route_security_policy(method, self.path)
        audit_event = build_dib_security_audit_event(
            method=method,
            path=self.path,
            principal=principal,
            authorization=authorization,
            http_status=status,
            request_payload=payload or {},
            error=error,
        )
        try:
            self.mount.controller.store._append_event(
                session_id,
                event_type=str(audit_event["event_type"]),
                entity_type="dib_security_audit",
                entity_id=str(audit_event["event_id"]),
                payload=audit_event,
            )
        except Exception:
            # Security audit must never make the primary DIB request fail.
            return

    def _require_gateway_auth(self, method: str) -> bool:
        self._dib_gateway_principal = None
        self._dib_gateway_authorization = dib_route_security_policy(method, self.path)
        if method == "OPTIONS":
            self._dib_gateway_authorization = authorize_dib_request(None, method, self.path)
            return True
        if not _sidecar_auth_required(self.path):
            policy = dib_route_security_policy(method, self.path)
            self._dib_gateway_authorization = {
                **policy,
                "authorized": True,
                "authorization_status": "auth_disabled_nonproduction",
                "principal_present": False,
            }
            return True
        token = self._bearer_token()
        organization_id = self.headers.get("X-ASIE-Organization-Id") or None
        principal = self.auth_repo.principal_for_token(token, organization_id) if token else None
        self._dib_gateway_principal = principal
        authorization = authorize_dib_request(principal, method, self.path)
        self._dib_gateway_authorization = authorization
        if principal is None:
            self._write_json(
                {
                    "error": "authentication_required",
                    "status": 401,
                    "http_mounting_id": DIB_HTTP_MOUNTING_ID,
                    "local_gateway_integration_id": DIB_LOCAL_GATEWAY_INTEGRATION_ID,
                    "permission_required": authorization.get("permission_required"),
                    "external_fetch_enabled": False,
                    "ai_provider_enabled": False,
                    "finance_wiring_enabled": False,
                    "snapshot_wiring_enabled": False,
                },
                401,
            )
            self._record_gateway_audit(method, 401, error="authentication_required")
            return False
        if not authorization.get("authorized"):
            self._write_json(
                {
                    "error": "permission_denied",
                    "status": 403,
                    "http_mounting_id": DIB_HTTP_MOUNTING_ID,
                    "local_gateway_integration_id": DIB_LOCAL_GATEWAY_INTEGRATION_ID,
                    "permission_required": authorization.get("permission_required"),
                    "authorization_status": authorization.get("authorization_status"),
                    "external_fetch_enabled": False,
                    "ai_provider_enabled": False,
                    "finance_wiring_enabled": False,
                    "snapshot_wiring_enabled": False,
                },
                403,
            )
            self._record_gateway_audit(method, 403, error="permission_denied")
            return False
        return True

    def _handle(self, method: str) -> None:
        if not self._require_gateway_auth(method):
            return
        payload: dict[str, Any] = {}
        try:
            payload = self._read_json_body() if method == "POST" else {}
            response = self.mount.dispatch(method, self.path, payload).to_public()
            self._write_json(response, response["status"])
            self._record_gateway_audit(method, int(response["status"]), payload)
        except DIBHttpMountError as exc:
            self._write_json(
                {
                    "error": exc.code,
                    "status": exc.status,
                    "http_mounting_id": DIB_HTTP_MOUNTING_ID,
                    "local_gateway_integration_id": DIB_LOCAL_GATEWAY_INTEGRATION_ID,
                    "external_fetch_enabled": False,
                    "ai_provider_enabled": False,
                    "finance_wiring_enabled": False,
                    "snapshot_wiring_enabled": False,
                },
                exc.status,
            )
            self._record_gateway_audit(method, exc.status, payload, error=exc.code)

    def do_OPTIONS(self) -> None:
        self._write_json({"ok": True, "http_mounting_id": DIB_HTTP_MOUNTING_ID})

    def do_GET(self) -> None:
        self._handle("GET")

    def do_POST(self) -> None:
        self._handle("POST")


def run_dib_http_sidecar(host: str | None = None, port: int | None = None) -> None:
    resolved_host = host or os.environ.get("ASIE_DIB_HTTP_HOST", DIB_HTTP_DEFAULT_HOST)
    resolved_port = int(port or os.environ.get("ASIE_DIB_HTTP_PORT", str(DIB_HTTP_DEFAULT_PORT)))
    server = ThreadingHTTPServer((resolved_host, resolved_port), DIBHttpSidecarHandler)
    server.serve_forever()


if __name__ == "__main__":
    run_dib_http_sidecar()
