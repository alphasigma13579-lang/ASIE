from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

from backend.contracts import new_id, now_iso
from backend.dib_runtime import (
    FINANCE_REQUIRED_KEYS,
    ITEM_KEYWORDS,
    build_dynamic_input_blueprint,
    map_intake_to_blueprint_items,
)

MAPPING_CONTRACT_ID = "dataset.dib.mapping.v1"
MAPPING_DECISION_CONTRACT_ID = "dataset.dib.mapping.decision.v1"
SUPPORTED_DECISIONS = {"accept", "edit", "reject", "unresolved"}


def _normalize_label(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[\s_\-/:]+", " ", text)
    return re.sub(r"[^0-9a-z\u0600-\u06ff .]", "", text).strip()


def _row_digest(row: Mapping[str, Any]) -> str:
    canonical = json.dumps(dict(row), ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _candidate_key(row: Mapping[str, Any]) -> tuple[str | None, float, list[str]]:
    explicit = str(row.get("input_key") or "").strip()
    if explicit:
        return explicit, 1.0, ["explicit_input_key"]

    material = " ".join(_normalize_label(value) for value in row.values())
    scores: list[tuple[float, str, list[str]]] = []
    for input_key, aliases in ITEM_KEYWORDS.items():
        matched = [alias for alias in aliases if _normalize_label(alias) and _normalize_label(alias) in material]
        if matched:
            score = min(0.95, 0.55 + 0.08 * len(matched))
            scores.append((score, input_key, matched))
    if not scores:
        return None, 0.0, []
    scores.sort(reverse=True)
    top = scores[0]
    if len(scores) > 1 and scores[1][0] == top[0]:
        return None, top[0], [f"ambiguous:{top[1]}", f"ambiguous:{scores[1][1]}"]
    return top[1], top[0], [f"alias:{value}" for value in top[2]]


def _numeric_values(row: Mapping[str, Any]) -> list[float]:
    values: list[float] = []
    for raw in row.values():
        if isinstance(raw, bool) or raw is None or raw == "":
            continue
        if isinstance(raw, (int, float)):
            values.append(float(raw))
            continue
        cleaned = re.sub(r"[^0-9.\-]", "", str(raw))
        if cleaned in {"", "-", "."}:
            continue
        try:
            values.append(float(cleaned))
        except ValueError:
            continue
    return values


def _proposed_value(input_key: str, values: Sequence[float]) -> float | None:
    if not values:
        return None
    if input_key in {"startup_cost", "monthly_fixed_cost"} and len(values) > 1:
        return float(sum(values))
    return float(values[-1])


@dataclass(frozen=True)
class MappingPolicy:
    auto_accept_threshold: float = 0.90
    review_threshold: float = 0.55

    def validate(self) -> None:
        if not 0 <= self.review_threshold <= self.auto_accept_threshold <= 1:
            raise ValueError("invalid_dataset_mapping_thresholds")


def create_mapping_draft(
    payload: Mapping[str, Any],
    *,
    project_profile: Mapping[str, Any],
    existing_items: Sequence[Mapping[str, Any]] = (),
    policy: MappingPolicy | None = None,
) -> dict[str, Any]:
    active_policy = policy or MappingPolicy()
    active_policy.validate()
    intake = map_intake_to_blueprint_items(dict(payload), [dict(item) for item in existing_items])
    rows = intake.get("rows") or []
    proposals: list[dict[str, Any]] = []

    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            continue
        input_key, confidence, reasons = _candidate_key(row)
        values = _numeric_values(row)
        value = _proposed_value(input_key or "", values) if input_key else None
        if input_key is None or value is None:
            status = "unresolved"
        elif confidence >= active_policy.auto_accept_threshold:
            status = "review_required"
        elif confidence >= active_policy.review_threshold:
            status = "review_required"
        else:
            status = "unresolved"
        proposals.append(
            {
                "proposal_id": new_id("map"),
                "row_index": index,
                "row_digest": _row_digest(row),
                "source_row": dict(row),
                "proposed_input_key": input_key,
                "proposed_value": value,
                "confidence": round(confidence, 4),
                "reasons": reasons,
                "status": status,
                "decision": None,
                "required_for_finance": input_key in FINANCE_REQUIRED_KEYS if input_key else False,
            }
        )

    digest_material = json.dumps(
        {
            "project_id": project_profile.get("project_id"),
            "file_name": intake.get("file_name"),
            "proposals": [(p["row_digest"], p["proposed_input_key"], p["proposed_value"]) for p in proposals],
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return {
        "contract_id": MAPPING_CONTRACT_ID,
        "mapping_id": f"mapping_{hashlib.sha256(digest_material.encode('utf-8')).hexdigest()[:24]}",
        "project_id": str(project_profile.get("project_id") or ""),
        "project_profile": dict(project_profile),
        "intake": intake,
        "proposals": proposals,
        "status": "review_required",
        "policy": {
            "auto_accept_threshold": active_policy.auto_accept_threshold,
            "review_threshold": active_policy.review_threshold,
            "raw_input_finance_bypass_allowed": False,
        },
        "created_at": now_iso(),
    }


def apply_mapping_decisions(mapping: Mapping[str, Any], decisions: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    if mapping.get("contract_id") != MAPPING_CONTRACT_ID:
        raise ValueError("invalid_dataset_mapping_contract")
    by_id = {str(item.get("proposal_id")): dict(item) for item in mapping.get("proposals", [])}
    for decision in decisions:
        proposal_id = str(decision.get("proposal_id") or "")
        if proposal_id not in by_id:
            raise ValueError("unknown_dataset_mapping_proposal")
        action = str(decision.get("action") or "").lower()
        if action not in SUPPORTED_DECISIONS:
            raise ValueError("invalid_dataset_mapping_decision")
        proposal = by_id[proposal_id]
        if action == "edit":
            key = str(decision.get("input_key") or proposal.get("proposed_input_key") or "").strip()
            if not key:
                raise ValueError("edited_mapping_requires_input_key")
            value = decision.get("value", proposal.get("proposed_value"))
            proposal.update({"proposed_input_key": key, "proposed_value": value})
        proposal["decision"] = {
            "contract_id": MAPPING_DECISION_CONTRACT_ID,
            "action": action,
            "reason": str(decision.get("reason") or ""),
            "decided_at": now_iso(),
        }
        proposal["status"] = "accepted" if action in {"accept", "edit"} else action

    proposals = list(by_id.values())
    accepted = [item for item in proposals if item.get("status") == "accepted"]
    unresolved = [item for item in proposals if item.get("status") in {"review_required", "unresolved"}]
    rejected = [item for item in proposals if item.get("status") == "reject"]
    return {
        **dict(mapping),
        "proposals": proposals,
        "status": "ready" if not unresolved and accepted else "review_required",
        "summary": {
            "accepted": len(accepted),
            "unresolved": len(unresolved),
            "rejected": len(rejected),
        },
        "updated_at": now_iso(),
    }


def mapping_to_blueprint(mapping: Mapping[str, Any], existing_items: Sequence[Mapping[str, Any]] = ()) -> dict[str, Any]:
    if mapping.get("status") != "ready":
        raise ValueError("dataset_mapping_not_ready")
    items = [dict(item) for item in existing_items]
    for proposal in mapping.get("proposals", []):
        if proposal.get("status") != "accepted":
            continue
        key = str(proposal.get("proposed_input_key") or "").strip()
        if not key:
            continue
        value = proposal.get("proposed_value")
        state = "INTENTIONAL_ZERO" if value == 0 else "FILE_IMPORTED"
        items.append(
            {
                "input_key": key,
                "label": str(proposal.get("source_row", {}).get("label") or proposal.get("source_row", {}).get("item") or key),
                "category": "finance_assumption",
                "value": value,
                "unit": "unit" if key == "monthly_units" else "SAR",
                "value_state": state,
                "value_source": "dataset_mapping",
                "source_type": "dataset_mapping",
                "confidence": proposal.get("confidence", 0.0),
                "evidence_refs": [
                    f"dataset-mapping:{mapping.get('mapping_id')}:{proposal.get('row_digest')}"
                ],
                "review_status": "approved",
                "required": key in FINANCE_REQUIRED_KEYS,
                "reason": str((proposal.get("decision") or {}).get("reason") or "user_reviewed_dataset_mapping"),
                "revision": 1,
            }
        )
    blueprint = build_dynamic_input_blueprint(dict(mapping.get("project_profile") or {}), items, source="dataset_mapping")
    return {
        **blueprint,
        "dataset_mapping": {
            "mapping_id": mapping.get("mapping_id"),
            "contract_id": mapping.get("contract_id"),
            "raw_input_finance_bypass_allowed": False,
            "accepted_count": (mapping.get("summary") or {}).get("accepted", 0),
        },
    }
