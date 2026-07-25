from __future__ import annotations

import math
import re
from dataclasses import dataclass
from statistics import median
from typing import Any

from backend.contracts import new_id, now_iso
from backend.snapshot_assembly import canonical_hash

SIMULATED_CATALOG: tuple[dict[str, Any], ...] = (
    {"terms": ("شواية", "shawarma", "grill"), "base": 18500.0, "unit": "SAR", "category": "capex_equipment"},
    {"terms": ("ثلاجة", "تبريد", "refriger"), "base": 12500.0, "unit": "SAR", "category": "capex_equipment"},
    {"terms": ("تحضير", "تقطيع", "prep"), "base": 6800.0, "unit": "SAR", "category": "capex_equipment"},
    {"terms": ("نقاط البيع", "pos"), "base": 4200.0, "unit": "SAR", "category": "capex_equipment"},
    {"terms": ("إيجار", "rent"), "base": 13500.0, "unit": "SAR/month", "category": "opex"},
    {"terms": ("رواتب", "payroll", "labor"), "base": 42000.0, "unit": "SAR/month", "category": "opex"},
    {"terms": ("استضافة", "cloud", "hosting"), "base": 3500.0, "unit": "SAR/month", "category": "opex"},
    {"terms": ("تسويق", "marketing"), "base": 8500.0, "unit": "SAR/month", "category": "opex"},
    {"terms": ("سعر", "price", "unit"), "base": 30.0, "unit": "SAR", "category": "revenue"},
)


@dataclass(frozen=True)
class MarketEvidencePack:
    evidence_pack_id: str
    contract_id: str
    query_id: str
    project_id: str
    item_id: str
    specification: str
    geography: str
    category: str
    unit: str
    samples: tuple[dict[str, Any], ...]
    p25: float
    p75: float
    weighted_median: float
    sample_count: int
    outlier_report: dict[str, Any]
    confidence: str
    data_mode: str
    evidence_refs: tuple[str, ...]
    review_decision: str
    selected_value: float | None
    created_at: str
    content_hash: str

    def to_public(self) -> dict[str, Any]:
        return {
            "evidence_pack_id": self.evidence_pack_id,
            "contract_id": self.contract_id,
            "query_id": self.query_id,
            "project_id": self.project_id,
            "item_id": self.item_id,
            "specification": self.specification,
            "geography": self.geography,
            "category": self.category,
            "unit": self.unit,
            "samples": [dict(sample) for sample in self.samples],
            "p25": self.p25,
            "p75": self.p75,
            "weighted_median": self.weighted_median,
            "sample_count": self.sample_count,
            "outlier_report": dict(self.outlier_report),
            "confidence": self.confidence,
            "data_mode": self.data_mode,
            "evidence_refs": list(self.evidence_refs),
            "review_decision": self.review_decision,
            "selected_value": self.selected_value,
            "created_at": self.created_at,
            "content_hash": self.content_hash,
            "external_fetch_enabled": False,
            "ai_provider_used": False,
            "decision_authority": "candidate_assumption_only",
        }


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        result = float(value)
        return result if math.isfinite(result) and result >= 0 else None
    text = str(value).replace(",", "").strip()
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return None
    result = float(match.group(0))
    return result if math.isfinite(result) and result >= 0 else None


def _quantile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("market_query_requires_samples")
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * q
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def _weighted_median(samples: list[dict[str, Any]]) -> float:
    rows = sorted(samples, key=lambda row: row["value"])
    total_weight = sum(float(row.get("weight") or 1.0) for row in rows)
    threshold = total_weight / 2
    cumulative = 0.0
    for row in rows:
        cumulative += float(row.get("weight") or 1.0)
        if cumulative >= threshold:
            return float(row["value"])
    return float(rows[-1]["value"])


def _normalize_samples(raw_samples: Any, *, unit: str) -> list[dict[str, Any]]:
    if not isinstance(raw_samples, list):
        return []
    rows: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_samples):
        if isinstance(raw, dict):
            value = _number(raw.get("value", raw.get("price", raw.get("amount"))))
            source_ref = str(raw.get("source_ref") or raw.get("evidence_ref") or f"sample:{index + 1}")
            weight = _number(raw.get("weight")) or 1.0
            sample_unit = str(raw.get("unit") or unit)
            date = str(raw.get("date") or raw.get("observed_at") or "")
        else:
            value = _number(raw)
            source_ref = f"sample:{index + 1}"
            weight = 1.0
            sample_unit = unit
            date = ""
        if value is None:
            continue
        rows.append(
            {
                "sample_id": f"market-sample:{index + 1}",
                "value": round(value, 4),
                "unit": sample_unit,
                "weight": round(float(weight), 4),
                "source_ref": source_ref,
                "date": date,
            }
        )
    return rows


def _catalog_base(specification: str, category: str) -> tuple[float, str]:
    text = f"{specification} {category}".lower()
    for row in SIMULATED_CATALOG:
        if any(term.lower() in text for term in row["terms"]):
            return float(row["base"]), str(row["unit"])
    category_defaults = {
        "capex_equipment": (10000.0, "SAR"),
        "capex": (25000.0, "SAR"),
        "opex": (8000.0, "SAR/month"),
        "revenue": (50.0, "SAR"),
        "variable_cost": (20.0, "SAR"),
    }
    return category_defaults.get(category, (5000.0, "SAR"))


def _simulated_samples(specification: str, category: str, unit: str) -> list[dict[str, Any]]:
    base, catalog_unit = _catalog_base(specification, category)
    factors = (0.74, 0.82, 0.90, 0.96, 1.0, 1.05, 1.12, 1.21, 1.35)
    return [
        {
            "sample_id": f"sim:{index + 1}",
            "value": round(base * factor, 2),
            "unit": unit or catalog_unit,
            "weight": 1.0 if index not in {0, len(factors) - 1} else 0.5,
            "source_ref": f"demo-simulated-catalog:{category}:{index + 1}",
            "date": "",
        }
        for index, factor in enumerate(factors)
    ]


def build_market_evidence_pack(payload: dict[str, Any]) -> dict[str, Any]:
    required = ("project_id", "query_id", "item_id", "specification", "geography", "category")
    missing = [field for field in required if not str(payload.get(field) or "").strip()]
    if missing:
        raise ValueError("market_query_missing_fields:" + ",".join(missing))

    specification = str(payload["specification"]).strip()
    category = str(payload["category"]).strip()
    unit = str(payload.get("unit") or "")
    samples = _normalize_samples(payload.get("candidate_samples"), unit=unit)
    data_mode = "user_or_dataset_samples"
    if not samples:
        samples = _simulated_samples(specification, category, unit)
        data_mode = "demo_simulated_external"

    values = [float(row["value"]) for row in samples]
    q1 = _quantile(values, 0.25)
    q3 = _quantile(values, 0.75)
    iqr = q3 - q1
    low = max(0.0, q1 - 1.5 * iqr)
    high = q3 + 1.5 * iqr
    outliers = [row for row in samples if float(row["value"]) < low or float(row["value"]) > high]
    accepted = [row for row in samples if row not in outliers] or samples
    accepted_values = [float(row["value"]) for row in accepted]
    p25 = round(_quantile(accepted_values, 0.25), 4)
    p75 = round(_quantile(accepted_values, 0.75), 4)
    weighted = round(_weighted_median(accepted), 4)
    evidence_refs = tuple(dict.fromkeys(str(row["source_ref"]) for row in accepted))
    confidence = "medium" if data_mode == "user_or_dataset_samples" and len(accepted) >= 5 else "low"

    created_at = now_iso()
    material = {
        "contract_id": "market.evidence.pack.v1",
        "query_id": str(payload["query_id"]),
        "project_id": str(payload["project_id"]),
        "item_id": str(payload["item_id"]),
        "specification": specification,
        "geography": str(payload["geography"]),
        "category": category,
        "unit": unit or str(accepted[0].get("unit") or ""),
        "samples": accepted,
        "p25": p25,
        "p75": p75,
        "weighted_median": weighted,
        "outlier_report": {
            "method": "IQR_1_5",
            "low": round(low, 4),
            "high": round(high, 4),
            "excluded_sample_ids": [row["sample_id"] for row in outliers],
            "excluded_count": len(outliers),
        },
        "data_mode": data_mode,
        "evidence_refs": evidence_refs,
    }
    pack = MarketEvidencePack(
        evidence_pack_id=new_id("marketpack"),
        contract_id="market.evidence.pack.v1",
        query_id=str(payload["query_id"]),
        project_id=str(payload["project_id"]),
        item_id=str(payload["item_id"]),
        specification=specification,
        geography=str(payload["geography"]),
        category=category,
        unit=material["unit"],
        samples=tuple(accepted),
        p25=p25,
        p75=p75,
        weighted_median=weighted,
        sample_count=len(accepted),
        outlier_report=material["outlier_report"],
        confidence=confidence,
        data_mode=data_mode,
        evidence_refs=evidence_refs,
        review_decision="PENDING",
        selected_value=None,
        created_at=created_at,
        content_hash=canonical_hash(material),
    )
    return pack.to_public()


class MarketIntelligenceModuleAdapter:
    module_id = "module.market_intelligence"

    def handle(self, payload: dict[str, Any]) -> dict[str, Any]:
        evidence_pack = build_market_evidence_pack(payload)
        return {
            "module_id": self.module_id,
            "contract_id": "market.evidence.pack.v1",
            "project_id": payload["project_id"],
            "query_id": payload["query_id"],
            "item_id": payload["item_id"],
            "evidence_pack": evidence_pack,
            "external_fetch_enabled": False,
            "ai_enabled": False,
        }
