from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping

REQUIRED_PROVIDER_SECRETS = (
    "DEEPSEEK_API_KEY",
    "TAVILY_API_KEY",
    "GOOGLE_MAPS_API_KEY",
    "PINECONE_API_KEY",
)

OPTIONAL_PROVIDER_SETTINGS = (
    "TAVILY_PROJECT",
    "GOOGLE_MAP_ID",
)

SECRET_SUFFIXES = ("_API_KEY", "_TOKEN", "_SECRET", "_PASSWORD", "_SSH_KEY")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _present(value: Any) -> bool:
    return bool(str(value or "").strip())


def _safe_status(name: str, values: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "name": name,
        "required": name in REQUIRED_PROVIDER_SECRETS,
        "present": _present(values.get(name)),
        "value_exposed": False,
    }


def build_presence_report(values: Mapping[str, Any] | None = None) -> dict[str, Any]:
    source = values if values is not None else os.environ
    required = [_safe_status(name, source) for name in REQUIRED_PROVIDER_SECRETS]
    optional = [_safe_status(name, source) for name in OPTIONAL_PROVIDER_SETTINGS]
    missing = [item["name"] for item in required if not item["present"]]
    return {
        "contract_id": "production.provider.readiness.v1",
        "status": "ready" if not missing else "blocked",
        "required": required,
        "optional": optional,
        "missing_required": missing,
        "secrets_exposed": False,
        "checked_at": _now_iso(),
    }


def assert_production_ready(values: Mapping[str, Any] | None = None) -> dict[str, Any]:
    report = build_presence_report(values)
    if report["status"] != "ready":
        raise RuntimeError("production_provider_readiness_blocked:" + ",".join(report["missing_required"]))
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
