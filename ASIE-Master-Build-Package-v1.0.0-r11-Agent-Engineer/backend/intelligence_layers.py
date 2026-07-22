"""Offline intelligence layer contracts; no external acquisition or sovereign scoring."""
from __future__ import annotations

from typing import Any

from backend.snapshot_assembly import canonical_hash

REQUIRED_METADATA = ("source", "freshness", "geography", "sector", "confidence", "lineage", "review")


def normalize_intelligence_signal(payload: dict[str, Any], *, organization_id: str, project_id: str) -> dict[str, Any]:
    missing = [field for field in REQUIRED_METADATA if not payload.get(field)]
    if missing:
        raise ValueError("intelligence_signal_metadata_incomplete:" + ",".join(missing))
    record = {
        "organization_id": organization_id, "project_id": project_id,
        "signal_id": str(payload.get("signal_id") or ""),
        "layer": str(payload.get("layer") or ""), "claim": str(payload.get("claim") or ""),
        "value": payload.get("value"), "source": str(payload["source"]),
        "freshness": str(payload["freshness"]), "geography": str(payload["geography"]),
        "sector": str(payload["sector"]), "confidence": str(payload["confidence"]),
        "lineage": list(payload["lineage"]) if isinstance(payload["lineage"], list) else [str(payload["lineage"])],
        "review": str(payload["review"]), "source_state": str(payload.get("source_state") or "reference_only"),
    }
    if not record["signal_id"] or not record["layer"] or not record["claim"]:
        raise ValueError("intelligence_signal_identity_incomplete")
    record["signal_hash"] = canonical_hash(record)
    return record


def build_vision2030_context(signals: list[dict[str, Any]], *, organization_id: str, project_id: str) -> dict[str, Any]:
    """Builds reference context only; it cannot produce a verdict or financial value."""
    if any(signal.get("source") != "VISION_2030_REFERENCE" or signal.get("source_state") != "reference_only" for signal in signals):
        raise ValueError("vision2030_requires_reference_only_source")
    return {
        "organization_id": organization_id, "project_id": project_id,
        "layer": "VISION_2030_STRATEGIC_REFERENCE", "status": "REFERENCE_CONTEXT_ONLY",
        "signals": signals, "verdict": None, "financial_outputs": None,
        "context_hash": canonical_hash({"signals": signals, "organization_id": organization_id, "project_id": project_id}),
    }


def disabled_global_national_layer(layer: str) -> dict[str, Any]:
    if layer not in {"GLOBAL", "NATIONAL"}:
        raise ValueError("unsupported_disabled_layer")
    return {"layer": layer, "status": "DISABLED", "external_fetch_enabled": False, "reason": "ACR-AIA-04_not_implemented"}
