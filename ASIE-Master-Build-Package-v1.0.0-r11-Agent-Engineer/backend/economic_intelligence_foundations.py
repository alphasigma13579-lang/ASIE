"""Defined-only Global/National/Market/Cost contracts with network permanently disabled."""
from __future__ import annotations

from typing import Any

from backend.snapshot_assembly import canonical_hash

LAYERS = {"GLOBAL", "NATIONAL", "MARKET", "REFERENCE_COST"}


def disabled_layer_contract(layer: str) -> dict[str, Any]:
    if layer not in LAYERS:
        raise ValueError("unknown_economic_intelligence_layer")
    return {"layer": layer, "status": "DEFINED_NOT_IMPLEMENTED", "external_fetch_enabled": False, "provider_enabled": False, "network_access": False, "source_state": "candidate_or_reference_only", "contract_hash": canonical_hash({"layer": layer, "status": "DEFINED_NOT_IMPLEMENTED"})}


def require_local_reviewed_input(record: dict[str, Any]) -> dict[str, Any]:
    required = ("source", "freshness", "geography", "sector", "confidence", "lineage", "review")
    missing = [key for key in required if not record.get(key)]
    if missing:
        raise ValueError("economic_input_metadata_incomplete:" + ",".join(missing))
    if record.get("source_state") not in {"reference_only", "candidate", "user_verified"}:
        raise ValueError("economic_input_source_state_not_allowed")
    return dict(record) | {"external_fetch_enabled": False, "network_access": False}
