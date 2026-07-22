"""Comparability and contradiction guards for non-sovereign synthesis."""
from __future__ import annotations

from typing import Any


def compare_signals(signals: list[dict[str, Any]]) -> dict[str, Any]:
    if len(signals) < 2:
        return {"comparable": False, "reason": "two_signals_required", "contradictions": []}
    keys = ("geography", "sector")
    incompatible = [key for key in keys if len({signal.get(key) for signal in signals}) > 1]
    contradictions = []
    for left_index, left in enumerate(signals):
        for right in signals[left_index + 1:]:
            if left.get("claim") == right.get("claim") and left.get("value") != right.get("value"):
                contradictions.append({"left": left.get("signal_id"), "right": right.get("signal_id"), "reason": "same_claim_different_value"})
    return {"comparable": not incompatible, "incompatibilities": incompatible, "contradictions": contradictions, "causality_asserted": False}
