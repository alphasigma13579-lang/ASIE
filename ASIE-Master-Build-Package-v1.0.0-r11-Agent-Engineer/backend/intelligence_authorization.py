"""Server-side authorization boundary for ACR-AIA-02 persistence."""
from __future__ import annotations

from typing import Any, Protocol

from backend.identity import Principal


class AuditSink(Protocol):
    def audit(self, **kwargs: Any) -> None: ...


def authorize_intelligence_action(
    principal: Principal | None,
    *, organization_id: str,
    project_id: str,
    permission: str,
    action: str,
    target_id: str,
    audit_sink: AuditSink,
    correlation_id: str | None = None,
) -> Principal:
    """Fail closed and audit both allow/deny without storing payload contents."""
    allowed = bool(
        principal
        and principal.organization_id == organization_id
        and principal.can(permission)
        and organization_id.strip()
        and project_id.strip()
    )
    actor = principal.user_id if principal else None
    audit_sink.audit(
        actor_user_id=actor, organization_id=organization_id,
        action=action, target_type="intelligence_context",
        target_id=target_id, result="allowed" if allowed else "denied",
        reason=None if allowed else "tenant_membership_or_permission_failed",
        correlation_id=correlation_id,
    )
    if not allowed:
        raise PermissionError("intelligence_authorization_denied")
    return principal
