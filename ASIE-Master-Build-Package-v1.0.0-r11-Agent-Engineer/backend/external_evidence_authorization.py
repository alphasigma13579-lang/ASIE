from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Protocol


READ: Final[str] = "external_evidence.read"
WRITE: Final[str] = "external_evidence.write"
REVIEW: Final[str] = "external_evidence.review"
CANCEL: Final[str] = "external_evidence.cancel"

VALID_ACTIONS: Final[frozenset[str]] = frozenset({READ, WRITE, REVIEW, CANCEL})
ROLE_ACTIONS: Final[dict[str, frozenset[str]]] = {
    "platform_admin": VALID_ACTIONS,
    "organization_owner": VALID_ACTIONS,
    "organization_admin": VALID_ACTIONS,
    "analyst": frozenset({READ, WRITE, CANCEL}),
    "reviewer": frozenset({READ, REVIEW}),
    "viewer": frozenset({READ}),
}


class PrincipalLike(Protocol):
    user_id: str
    session_id: str
    organization_id: str | None
    role: str | None
    platform_role: str | None

    def can(self, permission: str) -> bool: ...


class ProjectOwnershipResolver(Protocol):
    def project_belongs_to(self, organization_id: str, project_id: str) -> bool: ...


class ExternalEvidenceAuthorizationError(PermissionError):
    """A deliberately non-enumerating authorization failure."""


@dataclass(frozen=True, slots=True)
class AuthorizedScope:
    organization_id: str
    project_id: str
    actor_user_id: str
    action: str


class ExternalEvidenceAuthorizer:
    """Fail-closed, server-owned tenant/project authorization for FC20-04."""

    def __init__(self, ownership: ProjectOwnershipResolver) -> None:
        self._ownership = ownership

    def authorize(
        self,
        principal: PrincipalLike,
        *,
        organization_id: str,
        project_id: str,
        action: str,
    ) -> AuthorizedScope:
        if action not in VALID_ACTIONS:
            raise ExternalEvidenceAuthorizationError("external_evidence_access_denied")
        if not principal.user_id or not principal.session_id:
            raise ExternalEvidenceAuthorizationError("external_evidence_access_denied")
        if not organization_id or not project_id:
            raise ExternalEvidenceAuthorizationError("external_evidence_access_denied")
        if principal.organization_id != organization_id:
            raise ExternalEvidenceAuthorizationError("external_evidence_access_denied")
        if not self._ownership.project_belongs_to(organization_id, project_id):
            raise ExternalEvidenceAuthorizationError("external_evidence_access_denied")

        roles = tuple(role for role in (principal.platform_role, principal.role) if role)
        role_allowed = any(action in ROLE_ACTIONS.get(role, frozenset()) for role in roles)
        explicit_allowed = bool(principal.can(action))
        if not role_allowed and not explicit_allowed:
            raise ExternalEvidenceAuthorizationError("external_evidence_access_denied")

        return AuthorizedScope(
            organization_id=organization_id,
            project_id=project_id,
            actor_user_id=principal.user_id,
            action=action,
        )
