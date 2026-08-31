from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from typing import Final

DIB_FULL_PERMISSIONS: Final[frozenset[str]] = frozenset(
    {
        "dib.read",
        "dib.write",
        "dib.approve_manifest",
        "dib.run_gate",
        "dib.finance.execute",
        "dib.snapshot.handoff",
    }
)
DIB_REVIEW_PERMISSIONS: Final[frozenset[str]] = frozenset({"dib.read", "dib.approve_manifest", "dib.run_gate"})
DIB_READ_PERMISSION: Final[frozenset[str]] = frozenset({"dib.read"})

ROLE_PERMISSIONS: Final[dict[str, frozenset[str]]] = {
    "platform_admin": frozenset({"platform.manage", "platform.audit.read", "organization.support", "subscription.manage"}) | DIB_FULL_PERMISSIONS,
    "platform_support": frozenset({"organization.support", "dib.read"}),
    "organization_owner": frozenset({"organization.manage", "membership.manage", "project.create", "project.edit", "project.run", "snapshot.read", "review.write"}) | DIB_FULL_PERMISSIONS,
    "organization_admin": frozenset({"membership.manage", "project.create", "project.edit", "project.run", "snapshot.read", "review.write"}) | DIB_FULL_PERMISSIONS,
    "analyst": frozenset({"project.create", "project.edit", "project.run", "snapshot.read", "review.write"}) | DIB_FULL_PERMISSIONS,
    "reviewer": frozenset({"snapshot.read", "review.write"}) | DIB_REVIEW_PERMISSIONS,
    "viewer": frozenset({"snapshot.read"}) | DIB_READ_PERMISSION,
}

VALID_ROLES: Final[frozenset[str]] = frozenset(ROLE_PERMISSIONS)


@dataclass(frozen=True)
class Principal:
    user_id: str
    session_id: str
    organization_id: str | None
    role: str | None
    platform_role: str | None = None

    def can(self, permission: str) -> bool:
        return permission in ROLE_PERMISSIONS.get(self.platform_role or "", frozenset()) or permission in ROLE_PERMISSIONS.get(self.role or "", frozenset())


def hash_password(password: str, *, salt: str | None = None) -> str:
    if not isinstance(password, str) or len(password) < 6:
        raise ValueError("password_must_be_at_least_6_characters")
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("ascii"), 310_000)
    return f"pbkdf2_sha256$310000${salt}${digest.hex()}"


def validate_beta_password(password: str) -> None:
    """Keep closed-beta end-user passwords within the agreed 6–12 character range."""
    if not isinstance(password, str) or not 6 <= len(password) <= 12:
        raise ValueError("password_length_must_be_between_6_and_12_characters")


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt, expected = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("ascii"), int(iterations)).hex()
        return hmac.compare_digest(actual, expected)
    except (TypeError, ValueError):
        return False


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
