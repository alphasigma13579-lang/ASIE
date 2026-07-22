"""Local market/reference-cost assumptions with explicit maturity and review gates."""
from __future__ import annotations

from typing import Any

from backend.snapshot_assembly import canonical_hash

MATURITY = {"INITIAL", "PARTIAL", "VERIFIED"}


def build_market_context(*, organization_id: str, project_id: str, sector: str, geography: str, signals: list[dict[str, Any]]) -> dict[str, Any]:
    if not organization_id or not project_id or not sector or not geography:
        raise ValueError("market_context_scope_incomplete")
    for signal in signals:
        for key in ("source", "freshness", "geography", "sector", "confidence", "lineage", "review"):
            if not signal.get(key):
                raise ValueError("market_signal_metadata_incomplete:" + key)
    result = {"organization_id": organization_id, "project_id": project_id, "sector": sector, "geography": geography, "signals": signals, "maturity": "INITIAL" if not signals else "PARTIAL", "status": "REFERENCE_ONLY", "finance_eligible": False}
    result["market_context_hash"] = canonical_hash(result)
    return result


def build_reference_cost_assumption(*, organization_id: str, project_id: str, item_code: str, amount: float, currency: str, source: str, maturity: str = "INITIAL", review: str = "PENDING", lower: float | None = None, upper: float | None = None) -> dict[str, Any]:
    if maturity not in MATURITY or amount < 0 or not item_code or not currency or not source:
        raise ValueError("invalid_reference_cost_assumption")
    if lower is not None and upper is not None and not lower <= amount <= upper:
        raise ValueError("reference_cost_outside_range")
    result = {"organization_id": organization_id, "project_id": project_id, "item_code": item_code, "amount": amount, "currency": currency, "source": source, "maturity": maturity, "review": review, "range": {"lower": lower, "upper": upper}, "finance_eligible": maturity == "VERIFIED" and review == "APPROVED", "listed_price_is_capex": False}
    result["assumption_hash"] = canonical_hash(result)
    return result
