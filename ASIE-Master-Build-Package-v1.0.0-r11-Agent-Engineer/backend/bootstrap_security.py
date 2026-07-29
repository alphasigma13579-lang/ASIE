from __future__ import annotations

import hmac
import ipaddress
import os
from dataclasses import dataclass

NON_PRODUCTION_ENVIRONMENTS = frozenset({"development", "dev", "local", "test", "testing"})
TRUE_VALUES = frozenset({"1", "true", "yes", "on"})
MINIMUM_BOOTSTRAP_SECRET_LENGTH = 32


@dataclass(frozen=True)
class BootstrapAuthorization:
    allowed: bool
    code: str
    status: int


def deployment_environment() -> str:
    return os.environ.get("ASIE_ENV", "development").strip().lower() or "development"


def environment_flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in TRUE_VALUES


def is_production_like_environment() -> bool:
    return deployment_environment() not in NON_PRODUCTION_ENVIRONMENTS


def is_loopback_host(host: str | None) -> bool:
    if not host:
        return False
    normalized = host.strip().split("%", 1)[0]
    try:
        return ipaddress.ip_address(normalized).is_loopback
    except ValueError:
        return normalized.lower() == "localhost"


def legacy_local_operator_allowed(client_host: str | None) -> bool:
    return (
        not is_production_like_environment()
        and environment_flag("ASIE_ALLOW_LEGACY_LOCAL_OPERATOR")
        and is_loopback_host(client_host)
    )


def authorize_local_bootstrap(*, client_host: str | None, provided_secret: str | None) -> BootstrapAuthorization:
    if is_production_like_environment():
        return BootstrapAuthorization(False, "local_bootstrap_unavailable", 404)
    if not environment_flag("ASIE_ALLOW_LOCAL_BOOTSTRAP"):
        return BootstrapAuthorization(False, "local_bootstrap_unavailable", 404)
    if not is_loopback_host(client_host):
        return BootstrapAuthorization(False, "local_bootstrap_loopback_required", 403)

    configured_secret = os.environ.get("ASIE_LOCAL_BOOTSTRAP_SECRET", "")
    if len(configured_secret) < MINIMUM_BOOTSTRAP_SECRET_LENGTH:
        return BootstrapAuthorization(False, "local_bootstrap_secret_not_configured", 503)
    if not provided_secret or not hmac.compare_digest(provided_secret, configured_secret):
        return BootstrapAuthorization(False, "local_bootstrap_secret_invalid", 403)
    return BootstrapAuthorization(True, "local_bootstrap_authorized", 200)
