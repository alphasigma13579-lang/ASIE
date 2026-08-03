from __future__ import annotations

"""Presence-only contract for the FC20-03 provider-preflight secret store.

This module never serializes, hashes, logs, or returns secret values.  It does
not authorize network access or provider activation.
"""

import json
import os
from datetime import datetime, timezone
from typing import Any, Mapping


REQUIRED_PROVIDER_SECRETS = (
    "DEEPSEEK_API_KEY",
    "TAVILY_API_KEY",
    "GOOGLE_MAPS_API_KEY",
    "PINECONE_API_KEY",
)

OPTIONAL_PROVIDER_SECRETS = (
    "TAVILY_PROJECT",
    "GOOGLE_MAP_ID",
)

ALLOWED_SECRET_STORE_BACKENDS = frozenset({"github_environment"})


def _present(value: Any) -> bool:
    return bool(str(value or "").strip())


def _presence(name: str, source: Mapping[str, Any], *, required: bool) -> dict[str, Any]:
    return {
        "name": name,
        "required": required,
        "present": _present(source.get(name)),
        "value_exposed": False,
    }


def build_secret_store_report(values: Mapping[str, Any] | None = None) -> dict[str, Any]:
    source = values if values is not None else os.environ
    backend = str(source.get("ASIE_PROVIDER_SECRET_STORE_BACKEND") or "").strip().lower()
    required = [_presence(name, source, required=True) for name in REQUIRED_PROVIDER_SECRETS]
    optional = [_presence(name, source, required=False) for name in OPTIONAL_PROVIDER_SECRETS]
    missing = [item["name"] for item in required if not item["present"]]
    blocking_reasons: list[str] = []
    if backend not in ALLOWED_SECRET_STORE_BACKENDS:
        blocking_reasons.append("unapproved_secret_store_backend")
    if missing:
        blocking_reasons.append("missing_provider_secrets")
    return {
        "contract_id": "fc20-03.provider-preflight-secret-store.v1",
        "status": "ready" if not blocking_reasons else "blocked",
        "secret_store_backend": backend or "not_configured",
        "required": required,
        "optional": optional,
        "missing_required": missing,
        "blocking_reasons": blocking_reasons,
        "secret_values_exposed": False,
        "network_authorized": False,
        "provider_activation_authorized": False,
        "release_authorized": False,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


def main() -> int:
    report = build_secret_store_report()
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["status"] == "ready" else 2


if __name__ == "__main__":
    raise SystemExit(main())

