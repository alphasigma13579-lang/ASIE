from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

HOST = os.environ.get("ASIE_API_HOST", "127.0.0.1")
PORT = int(os.environ.get("ASIE_API_PORT", "8794"))
SCENARIO_ID = "baseline"
SEED = 20260713
PROFILE_ID = "strict_open_data_only_v1"
DB_PATH = Path(os.environ.get("ASIE_DB_PATH", Path(__file__).with_name("asie_local.sqlite3")))


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


def money(value: Decimal) -> float:
    return float(value.quantize(Decimal("0.01")))


def decimal_from(value: Any) -> Decimal | None:
    try:
        if value is None or value == "":
            return None
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def json_dumps(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def json_loads(raw: str | None, default: Any) -> Any:
    if not raw:
        return default
    return json.loads(raw)


def envelope(
    *,
    project: Any,
    run_id: str,
    snapshot_id: str,
    output_id: str,
    owner_module: str,
    contract_id: str,
    algorithm_id: str,
    value_type: str,
    value: Any,
    unit: str,
    period: str,
    status: str = "ready",
    confidence: float | None = None,
    confidence_basis: str = "local_snapshot",
    formula_ref: str = "",
    evidence_refs: list[str] | None = None,
    assumption_refs: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "output_id": output_id,
        "project_id": project.project_id,
        "run_id": run_id,
        "scenario_id": SCENARIO_ID,
        "snapshot_id": snapshot_id,
        "owner_module": owner_module,
        "contract_id": contract_id,
        "algorithm_id": algorithm_id,
        "algorithm_version": "1.0.0-local-core",
        "value_type": value_type,
        "value": value,
        "unit": unit,
        "period": period,
        "geography": project.jurisdiction,
        "evidence_refs": evidence_refs or [],
        "assumption_refs": assumption_refs or [],
        "formula_ref": formula_ref,
        "confidence": confidence,
        "confidence_basis": confidence_basis,
        "status": status,
        "as_of": now_iso(),
        "locale": "ar-SA",
        "audit_ref": f"audit:{snapshot_id}:{output_id}",
    }
