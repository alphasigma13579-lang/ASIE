from __future__ import annotations

import hashlib
import json
import os
from typing import Any, Mapping
from urllib.parse import urlparse

from backend.contracts import new_id, now_iso
from backend.identity import Principal

DIB_SECURITY_AUDIT_RBAC_ID = "DIB-COMPLETION-PACKAGE-F-SECURITY-AUDIT-RBAC-v1"
DIB_SECURITY_AUDIT_RBAC_STATUS = "post_freeze_dib_security_audit_rbac"
DIB_SECURITY_AUDIT_RBAC_SOURCE = "docs/EKB/EKB-02-Source-of-Truth-Matrix.md"

DIB_READ_PERMISSION = "dib.read"
DIB_WRITE_PERMISSION = "dib.write"
DIB_APPROVE_MANIFEST_PERMISSION = "dib.approve_manifest"
DIB_RUN_GATE_PERMISSION = "dib.run_gate"
DIB_FINANCE_EXECUTE_PERMISSION = "dib.finance.execute"
DIB_SNAPSHOT_HANDOFF_PERMISSION = "dib.snapshot.handoff"

DIB_SECURITY_PERMISSIONS = frozenset(
    {
        DIB_READ_PERMISSION,
        DIB_WRITE_PERMISSION,
        DIB_APPROVE_MANIFEST_PERMISSION,
        DIB_RUN_GATE_PERMISSION,
        DIB_FINANCE_EXECUTE_PERMISSION,
        DIB_SNAPSHOT_HANDOFF_PERMISSION,
    }
)

PRODUCTION_ENV_VALUES = frozenset({"production", "prod", "live"})
AUTH_FALSE_VALUES = frozenset({"0", "false", "no", "off"})


def _clean_path(path: str) -> str:
    parsed = urlparse(path)
    return parsed.path.rstrip("/") or "/"


def _path_parts(path: str) -> list[str]:
    return [part for part in _clean_path(path).strip("/").split("/") if part]


def _payload_hash(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def is_production_environment(environ: Mapping[str, str] | None = None) -> bool:
    env = environ or os.environ
    for key in ("ASIE_ENV", "APP_ENV", "ENV", "NODE_ENV"):
        value = str(env.get(key, "")).strip().lower()
        if value in PRODUCTION_ENV_VALUES:
            return True
    return False


def resolve_dib_auth_required(path: str, environ: Mapping[str, str] | None = None) -> bool:
    """Resolve DIB auth without allowing production bypasses.

    `/api/dib/status` remains a health/readiness exception. Every other DIB
    route is authenticated by default. `ASIE_DIB_REQUIRE_AUTH=false` can relax
    auth only outside production-like environments.
    """

    if _clean_path(path) == "/api/dib/status":
        return False
    env = environ or os.environ
    if is_production_environment(env):
        return True
    configured = str(env.get("ASIE_DIB_REQUIRE_AUTH", "true")).strip().lower()
    return configured not in AUTH_FALSE_VALUES


def dib_route_security_policy(method: str, path: str) -> dict[str, Any]:
    method = method.upper().strip()
    clean = _clean_path(path)
    parts = _path_parts(path)
    policy = {
        "method": method,
        "path": clean,
        "permission_required": DIB_READ_PERMISSION,
        "audit_action": "dib.read",
        "public_route": False,
        "rbac_enforced": True,
    }
    if method == "OPTIONS":
        return {**policy, "permission_required": None, "audit_action": "dib.preflight", "public_route": True, "rbac_enforced": False}
    if method == "GET" and clean == "/api/dib/status":
        return {**policy, "permission_required": None, "audit_action": "dib.status.read", "public_route": True, "rbac_enforced": False}
    if method == "GET" and parts == ["api", "dib", "sessions"]:
        return {**policy, "permission_required": DIB_READ_PERMISSION, "audit_action": "dib.sessions.query"}
    if method == "POST" and parts == ["api", "dib", "sessions"]:
        return {**policy, "permission_required": DIB_WRITE_PERMISSION, "audit_action": "dib.session.start"}
    if len(parts) >= 4 and parts[:3] == ["api", "dib", "sessions"]:
        tail = parts[4:]
        if method == "GET" and not tail:
            return {**policy, "permission_required": DIB_READ_PERMISSION, "audit_action": "dib.session.read"}
        if method == "GET" and tail == ["events"]:
            return {**policy, "permission_required": DIB_READ_PERMISSION, "audit_action": "dib.events.read"}
        if method == "POST" and tail == ["template-registry"]:
            return {**policy, "permission_required": DIB_READ_PERMISSION, "audit_action": "dib.template_registry.resolve"}
        if method == "POST" and tail == ["intake-items"]:
            return {**policy, "permission_required": DIB_WRITE_PERMISSION, "audit_action": "dib.intake.preview"}
        if method == "POST" and tail == ["item-decisions"]:
            return {**policy, "permission_required": DIB_WRITE_PERMISSION, "audit_action": "dib.item_decision.apply"}
        if method == "POST" and tail == ["blueprints"]:
            return {**policy, "permission_required": DIB_WRITE_PERMISSION, "audit_action": "dib.blueprint.save"}
        if method == "POST" and tail == ["approved-manifests"]:
            return {**policy, "permission_required": DIB_APPROVE_MANIFEST_PERMISSION, "audit_action": "dib.manifest.approve"}
        if method == "POST" and tail == ["validation-gates"]:
            return {**policy, "permission_required": DIB_RUN_GATE_PERMISSION, "audit_action": "dib.validation_gate.run"}
        if method == "POST" and tail == ["project-run-readiness"]:
            return {**policy, "permission_required": DIB_RUN_GATE_PERMISSION, "audit_action": "dib.project_run_readiness.build"}
        if method == "POST" and tail == ["controlled-finance"]:
            return {**policy, "permission_required": DIB_FINANCE_EXECUTE_PERMISSION, "audit_action": "dib.controlled_finance.execute"}
        if method == "POST" and tail == ["snapshot-projection-handoff"]:
            return {**policy, "permission_required": DIB_SNAPSHOT_HANDOFF_PERMISSION, "audit_action": "dib.snapshot_projection_handoff.prepare"}
        if method == "POST" and tail == ["e2e-scenario"]:
            return {**policy, "permission_required": DIB_RUN_GATE_PERMISSION, "audit_action": "dib.e2e_scenario.report"}
        if method == "POST" and tail == ["close"]:
            return {**policy, "permission_required": DIB_WRITE_PERMISSION, "audit_action": "dib.session.close"}
    return {**policy, "permission_required": DIB_READ_PERMISSION, "audit_action": "dib.route.unknown"}


def authorize_dib_request(principal: Principal | None, method: str, path: str) -> dict[str, Any]:
    policy = dib_route_security_policy(method, path)
    permission = policy["permission_required"]
    if permission is None:
        return {
            **policy,
            "authorized": True,
            "authorization_status": "public_route",
            "principal_present": principal is not None,
        }
    if principal is None:
        return {
            **policy,
            "authorized": False,
            "authorization_status": "authentication_required",
            "principal_present": False,
        }
    authorized = principal.can(str(permission))
    return {
        **policy,
        "authorized": authorized,
        "authorization_status": "authorized" if authorized else "permission_denied",
        "principal_present": True,
        "principal_user_id": principal.user_id,
        "principal_session_id": principal.session_id,
        "principal_organization_id": principal.organization_id,
        "principal_role": principal.role,
        "principal_platform_role": principal.platform_role,
    }


def extract_dib_session_id_from_path(path: str) -> str | None:
    parts = _path_parts(path)
    if len(parts) >= 4 and parts[:3] == ["api", "dib", "sessions"]:
        return parts[3]
    return None


def build_dib_security_audit_event(
    *,
    method: str,
    path: str,
    principal: Principal | None,
    authorization: dict[str, Any],
    http_status: int,
    request_payload: dict[str, Any] | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    session_id = extract_dib_session_id_from_path(path)
    authorized = bool(authorization.get("authorized")) and http_status < 400
    return {
        "event_id": new_id("dib_security_audit"),
        "event_type": "security.rbac.granted" if authorized else "security.rbac.denied",
        "security_audit_rbac_id": DIB_SECURITY_AUDIT_RBAC_ID,
        "audit_action": authorization.get("audit_action"),
        "method": method.upper().strip(),
        "path": _clean_path(path),
        "session_id": session_id,
        "permission_required": authorization.get("permission_required"),
        "authorization_status": authorization.get("authorization_status"),
        "http_status": http_status,
        "authorized": authorized,
        "principal_user_id": getattr(principal, "user_id", None),
        "principal_session_id": getattr(principal, "session_id", None),
        "principal_organization_id": getattr(principal, "organization_id", None),
        "principal_role": getattr(principal, "role", None),
        "principal_platform_role": getattr(principal, "platform_role", None),
        "request_payload_hash": _payload_hash(request_payload or {}),
        "raw_payload_stored": False,
        "error": error,
        "external_fetch_enabled": False,
        "ai_provider_enabled": False,
        "finance_wiring_enabled": False,
        "snapshot_wiring_enabled": False,
        "created_at": now_iso(),
    }


def dib_security_audit_rbac_status(environ: Mapping[str, str] | None = None) -> dict[str, Any]:
    env = environ or os.environ
    return {
        "security_audit_rbac_id": DIB_SECURITY_AUDIT_RBAC_ID,
        "status": DIB_SECURITY_AUDIT_RBAC_STATUS,
        "source": DIB_SECURITY_AUDIT_RBAC_SOURCE,
        "permissions": sorted(DIB_SECURITY_PERMISSIONS),
        "rbac_enforced_on_sidecar": True,
        "audit_event_types": ["security.rbac.granted", "security.rbac.denied"],
        "auth_status_exemption": "/api/dib/status",
        "production_environment": is_production_environment(env),
        "production_auth_bypass_blocked": True,
        "external_fetch_enabled": False,
        "ai_provider_enabled": False,
        "finance_wiring_enabled": False,
        "snapshot_wiring_enabled": False,
        "frozen_runtime_files_mutated": False,
    }
