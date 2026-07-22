"""Deterministic, non-sovereign synthesis and projection helpers."""
from __future__ import annotations

from typing import Any

from backend.snapshot_assembly import canonical_hash


def build_synthesis_pack(context: dict[str, Any], *, pack_id: str) -> dict[str, Any]:
    if context.get("status") != "REFERENCE_CONTEXT_ONLY":
        raise ValueError("synthesis_requires_valid_reference_context")
    signals = context.get("signals") or []
    if not signals:
        raise ValueError("synthesis_requires_signals")
    claims = [{"signal_id": signal["signal_id"], "claim": signal["claim"], "confidence": signal["confidence"], "source": signal["source"]} for signal in signals]
    pack = {"pack_id": pack_id, "organization_id": context["organization_id"], "project_id": context["project_id"], "context_hash": context["context_hash"], "claims": claims, "verdict": None, "financial_outputs": None, "causality_asserted": False, "status": "PRE_DECISION_REFERENCE_ONLY"}
    pack["pack_hash"] = canonical_hash(pack)
    return pack


def project_synthesis(pack: dict[str, Any]) -> dict[str, Any]:
    """Read-only projection; deliberately does not recalculate or mutate input."""
    expected = pack.get("pack_hash")
    material = dict(pack)
    material.pop("pack_hash", None)
    if not expected or canonical_hash(material) != expected:
        raise ValueError("synthesis_pack_hash_mismatch")
    return {"projection_type": "deterministic_reference", "pack_id": pack["pack_id"], "claims": list(pack["claims"]), "verdict": None, "projection_hash": canonical_hash({"pack_id": pack["pack_id"], "claims": pack["claims"], "verdict": None})}
