from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.contracts import new_id, now_iso


ITEM_STATES = frozenset(
    {
        "VALUE_ENTERED",
        "CLIENT_ESTIMATE",
        "INTENTIONAL_ZERO",
        "NOT_APPLICABLE",
        "UNKNOWN",
        "EXPERIMENTAL_ESTIMATE",
    }
)
APPROVED_STATES = frozenset({"VALUE_ENTERED", "CLIENT_ESTIMATE", "INTENTIONAL_ZERO", "NOT_APPLICABLE"})
FINANCE_REQUIRED_KEYS = frozenset(
    {"startup_cost", "monthly_fixed_cost", "unit_price", "variable_cost", "monthly_units"}
)
SYSTEM_KEYS = frozenset(
    {"blueprint_items", "primary_sector_id", "activity_description", "location_scope", "location_country", "intake_mode"}
)


@dataclass(frozen=True)
class ApprovedInputManifest:
    manifest_id: str
    project_id: str
    version: int
    status: str
    items: tuple[dict[str, Any], ...]
    normalized_inputs: dict[str, Any]
    blockers: tuple[dict[str, str], ...]
    created_at: str
    legacy_compatibility: bool = False

    def to_public(self) -> dict[str, Any]:
        return {
            "manifest_id": self.manifest_id,
            "project_id": self.project_id,
            "version": self.version,
            "status": self.status,
            "items": [dict(item) for item in self.items],
            "normalized_inputs": dict(self.normalized_inputs),
            "blockers": [dict(blocker) for blocker in self.blockers],
            "created_at": self.created_at,
            "legacy_compatibility": self.legacy_compatibility,
        }


def _metadata_by_key(raw: Any) -> dict[str, dict[str, Any]]:
    if isinstance(raw, dict):
        return {str(key): dict(value) for key, value in raw.items() if isinstance(value, dict)}
    if isinstance(raw, list):
        return {
            str(row.get("input_key")): dict(row)
            for row in raw
            if isinstance(row, dict) and str(row.get("input_key") or "").strip()
        }
    return {}


def _blocker(code: str, message: str, *, severity: str = "critical") -> dict[str, str]:
    return {"code": code, "severity": severity, "message": message}


def build_approved_input_manifest(
    project_id: str,
    inputs: dict[str, Any],
    *,
    assumption_refs: list[str] | None = None,
    legacy_compatibility: bool = False,
) -> ApprovedInputManifest:
    metadata = _metadata_by_key(inputs.get("blueprint_items"))
    keys = set(inputs) - SYSTEM_KEYS
    keys.update(metadata)
    items: list[dict[str, Any]] = []
    normalized: dict[str, Any] = {}
    blockers: list[dict[str, str]] = []

    for key in sorted(keys):
        if key == "other_monthly_costs" or key.startswith("_"):
            continue
        meta = metadata.get(key, {})
        value = inputs.get(key)
        has_value = value is not None and value != ""
        state = str(meta.get("state") or "").upper()
        if not state:
            if not has_value:
                state = "UNKNOWN"
            elif isinstance(value, (int, float)) and value == 0:
                state = "UNKNOWN"
            else:
                state = "VALUE_ENTERED"
        if state not in ITEM_STATES:
            blockers.append(_blocker("INVALID_BLUEPRINT_ITEM_STATE", f"حالة البند {key} غير معروفة."))
            state = "UNKNOWN"

        reason = str(meta.get("reason") or "").strip()
        source_type = str(meta.get("source_type") or ("user_input" if legacy_compatibility else "user_input"))
        treatment = str(meta.get("treatment") or ("exclude" if state == "NOT_APPLICABLE" else "include"))
        approval_status = str(meta.get("approval_status") or ("approved" if legacy_compatibility else "draft"))
        confidence = meta.get("confidence", 0.65 if state == "VALUE_ENTERED" else 0.45)
        item = {
            "item_id": str(meta.get("item_id") or f"item:{project_id}:{key}"),
            "input_key": key,
            "label": str(meta.get("label") or key),
            "category": str(meta.get("category") or "operating_assumption"),
            "value": value,
            "unit": str(meta.get("unit") or "unit"),
            "state": state,
            "reason": reason,
            "source_type": source_type,
            "treatment": treatment,
            "approval_status": approval_status,
            "confidence": confidence,
            "evidence_refs": list(meta.get("evidence_refs") or []),
            "assumption_refs": list(meta.get("assumption_refs") or assumption_refs or []),
        }
        items.append(item)

        if state in {"INTENTIONAL_ZERO", "NOT_APPLICABLE"} and not reason:
            blockers.append(_blocker("BLUEPRINT_REASON_REQUIRED", f"البند {key} يحتاج سببًا موثقًا لحالة {state}."))
        if state == "EXPERIMENTAL_ESTIMATE" and approval_status != "approved":
            blockers.append(_blocker("EXPERIMENTAL_ESTIMATE_NOT_APPROVED", f"التقدير التجريبي للبند {key} لم يعتمد بعد."))
        if state == "UNKNOWN" and (key in FINANCE_REQUIRED_KEYS or meta.get("required") is True):
            blockers.append(_blocker(f"UNKNOWN_{key.upper()}", f"البند المطلوب {key} غير معروف بعد."))

        if state in APPROVED_STATES and approval_status == "approved":
            if state == "NOT_APPLICABLE":
                normalized[key] = 0
            elif has_value:
                normalized[key] = value

    status = "approved" if not blockers else "blocked"
    return ApprovedInputManifest(
        manifest_id=new_id("manifest"),
        project_id=project_id,
        version=1,
        status=status,
        items=tuple(items),
        normalized_inputs=normalized,
        blockers=tuple(blockers),
        created_at=now_iso(),
        legacy_compatibility=legacy_compatibility,
    )


def manifest_item_map(manifest: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not isinstance(manifest, dict):
        return {}
    return {
        str(item.get("input_key")): item
        for item in manifest.get("items", [])
        if isinstance(item, dict) and item.get("input_key")
    }
