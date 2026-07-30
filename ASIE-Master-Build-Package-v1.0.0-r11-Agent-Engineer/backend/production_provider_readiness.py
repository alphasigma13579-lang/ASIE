from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Mapping

from backend.live_provider_catalog import LIVE_PROVIDER_CATALOG


REQUIRED_PROVIDER_SECRETS = (
    "DEEPSEEK_API_KEY",
    "TAVILY_API_KEY",
    "GOOGLE_MAPS_API_KEY",
    "PINECONE_API_KEY",
)

OPTIONAL_PROVIDER_SETTINGS = (
    "TAVILY_PROJECT",
    "GOOGLE_MAP_ID",
    "PINECONE_INDEX",
)

SECRET_SUFFIXES = ("_API_KEY", "_TOKEN", "_SECRET", "_PASSWORD", "_SSH_KEY")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _present(value: Any) -> bool:
    return bool(str(value or "").strip())


def _truthy(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _safe_status(name: str, values: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "name": name,
        "required": name in REQUIRED_PROVIDER_SECRETS,
        "present": _present(values.get(name)),
        "value_exposed": False,
    }


def _provider_state(values: Mapping[str, Any], provider_id: str) -> str:
    token = "".join(character if character.isalnum() else "_" for character in provider_id.upper()).strip("_")
    return str(values.get(f"ASIE_PROVIDER_{token}_STATE") or "disabled").strip().lower()


def _provider_kill_switch(values: Mapping[str, Any], provider_id: str) -> bool:
    token = "".join(character if character.isalnum() else "_" for character in provider_id.upper()).strip("_")
    return _truthy(values.get(f"ASIE_PROVIDER_{token}_KILL_SWITCH"))


def build_presence_report(values: Mapping[str, Any] | None = None) -> dict[str, Any]:
    source = values if values is not None else os.environ
    required = [_safe_status(name, source) for name in REQUIRED_PROVIDER_SECRETS]
    optional = [_safe_status(name, source) for name in OPTIONAL_PROVIDER_SETTINGS]
    missing = [item["name"] for item in required if not item["present"]]

    allowed_hosts = {
        item.strip().lower().rstrip(".")
        for item in str(source.get("ASIE_EXTERNAL_ALLOWED_HOSTS") or "").split(",")
        if item.strip()
    }
    required_hosts = {
        host.lower().rstrip(".")
        for provider in LIVE_PROVIDER_CATALOG
        for host in provider.base_hosts
    }
    provider_states = {
        provider.provider_id: _provider_state(source, provider.provider_id)
        for provider in LIVE_PROVIDER_CATALOG
    }
    provider_kill_switches = {
        provider.provider_id: _provider_kill_switch(source, provider.provider_id)
        for provider in LIVE_PROVIDER_CATALOG
    }
    blocking_reasons: list[str] = []
    if missing:
        blocking_reasons.append("missing_provider_secrets")
    if not _truthy(source.get("ASIE_ALLOW_EXTERNAL_FETCH")):
        blocking_reasons.append("external_network_policy_disabled")
    if not _truthy(source.get("ASIE_PROVIDER_CONTROL_PLANE_ENABLED")):
        blocking_reasons.append("provider_control_plane_disabled")
    durable_store_configured = _present(source.get("ASIE_PROVIDER_CONTROL_DB_PATH"))
    if not durable_store_configured:
        blocking_reasons.append("provider_control_store_missing")
    if _truthy(source.get("ASIE_PROVIDER_GLOBAL_KILL_SWITCH")):
        blocking_reasons.append("provider_global_kill_switch_active")
    if any(state != "enabled" for state in provider_states.values()):
        blocking_reasons.append("provider_state_not_enabled")
    if any(provider_kill_switches.values()):
        blocking_reasons.append("provider_kill_switch_active")
    missing_hosts = sorted(required_hosts - allowed_hosts)
    if missing_hosts:
        blocking_reasons.append("provider_hosts_not_allowlisted")

    return {
        "contract_id": "production.provider.readiness.v2",
        "status": "ready" if not blocking_reasons else "blocked",
        "required": required,
        "optional": optional,
        "missing_required": missing,
        "activation_controls": {
            "external_network_enabled": _truthy(source.get("ASIE_ALLOW_EXTERNAL_FETCH")),
            "provider_control_plane_enabled": _truthy(source.get("ASIE_PROVIDER_CONTROL_PLANE_ENABLED")),
            "durable_control_store_configured": durable_store_configured,
            "control_store_path_exposed": False,
            "global_kill_switch_active": _truthy(source.get("ASIE_PROVIDER_GLOBAL_KILL_SWITCH")),
            "provider_states": provider_states,
            "provider_kill_switches": provider_kill_switches,
            "required_hosts": sorted(required_hosts),
            "missing_allowed_hosts": missing_hosts,
        },
        "blocking_reasons": blocking_reasons,
        "configuration_only": True,
        "activation_authority_granted": False,
        "secrets_exposed": False,
        "checked_at": _now_iso(),
    }


def assert_production_ready(values: Mapping[str, Any] | None = None) -> dict[str, Any]:
    report = build_presence_report(values)
    if report["status"] != "ready":
        raise RuntimeError(
            "production_provider_readiness_blocked:"
            + ",".join(report["blocking_reasons"])
        )
    return report


def redact_payload(payload: Any) -> Any:
    if isinstance(payload, dict):
        result: dict[str, Any] = {}
        for key, value in payload.items():
            upper = str(key).upper()
            if any(upper.endswith(suffix) for suffix in SECRET_SUFFIXES):
                result[key] = "[REDACTED]" if _present(value) else ""
            else:
                result[key] = redact_payload(value)
        return result
    if isinstance(payload, list):
        return [redact_payload(item) for item in payload]
    return payload


def report_json(values: Mapping[str, Any] | None = None) -> str:
    return json.dumps(build_presence_report(values), ensure_ascii=False, sort_keys=True)


def main() -> int:
    report = build_presence_report()
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["status"] == "ready" else 2


if __name__ == "__main__":
    raise SystemExit(main())
