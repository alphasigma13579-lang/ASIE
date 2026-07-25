from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.contracts import new_id, now_iso
from backend.dib_registry import governed_template, suggested_item_specs
from backend.snapshot_assembly import canonical_hash

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
APPROVED_STATES = frozenset(
    {"VALUE_ENTERED", "CLIENT_ESTIMATE", "INTENTIONAL_ZERO", "NOT_APPLICABLE", "EXPERIMENTAL_ESTIMATE"}
)
FINANCE_REQUIRED_KEYS = frozenset(
    {"startup_cost", "monthly_fixed_cost", "unit_price", "variable_cost", "monthly_units"}
)
SYSTEM_KEYS = frozenset(
    {
        "blueprint_items",
        "blueprint_id",
        "blueprint_revision_id",
        "blueprint_revision",
        "blueprint_revisions",
        "approved_input_manifest",
        "approved_input_manifests",
        "template_id",
        "interview_answers",
        "start_type",
        "primary_sector_id",
        "activity_description",
        "location_scope",
        "location_country",
        "intake_mode",
    }
)


@dataclass(frozen=True)
class DynamicInputBlueprint:
    blueprint_id: str
    project_id: str
    template_id: str
    revision_id: str
    revision: int
    parent_revision_id: str | None
    start_type: str
    items: tuple[dict[str, Any], ...]
    interview_answers: dict[str, Any]
    status: str
    created_at: str
    content_hash: str

    def to_public(self) -> dict[str, Any]:
        return {
            "blueprint_id": self.blueprint_id,
            "project_id": self.project_id,
            "template_id": self.template_id,
            "revision_id": self.revision_id,
            "revision": self.revision,
            "parent_revision_id": self.parent_revision_id,
            "start_type": self.start_type,
            "items": [dict(item) for item in self.items],
            "interview_answers": dict(self.interview_answers),
            "status": self.status,
            "created_at": self.created_at,
            "content_hash": self.content_hash,
        }


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
    blueprint_id: str = ""
    blueprint_revision_id: str = ""
    template_id: str = ""
    content_hash: str = ""

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
            "blueprint_id": self.blueprint_id,
            "blueprint_revision_id": self.blueprint_revision_id,
            "template_id": self.template_id,
            "content_hash": self.content_hash,
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


def _normal_item(project_id: str, key: str, raw: dict[str, Any], value: Any, *, legacy: bool) -> dict[str, Any]:
    has_value = value is not None and value != ""
    state = str(raw.get("state") or "").upper()
    if not state:
        if not has_value:
            state = "UNKNOWN"
        elif isinstance(value, (int, float)) and value == 0:
            state = "VALUE_ENTERED" if legacy else "UNKNOWN"
        else:
            state = "VALUE_ENTERED"
    if state not in ITEM_STATES:
        state = "UNKNOWN"

    return {
        "item_id": str(raw.get("item_id") or f"item:{project_id}:{key}"),
        "input_key": key,
        "finance_key": str(raw.get("finance_key") or key),
        "label": str(raw.get("label") or key),
        "category": str(raw.get("category") or "operating_assumption"),
        "value": value,
        "unit": str(raw.get("unit") or "unit"),
        "state": state,
        "reason": str(raw.get("reason") or "").strip(),
        "source_type": str(raw.get("source_type") or "user_input"),
        "treatment": str(raw.get("treatment") or ("exclude" if state == "NOT_APPLICABLE" else "include")),
        "approval_status": str(raw.get("approval_status") or ("approved" if legacy else "draft")),
        "confidence": raw.get("confidence", 0.65 if state == "VALUE_ENTERED" else 0.45),
        "evidence_refs": list(raw.get("evidence_refs") or []),
        "assumption_refs": list(raw.get("assumption_refs") or []),
        "required": bool(raw.get("required") or raw.get("required_for_finance")),
        "market_query": dict(raw.get("market_query") or {}) if isinstance(raw.get("market_query"), dict) else None,
        "evidence_pack": dict(raw.get("evidence_pack") or {}) if isinstance(raw.get("evidence_pack"), dict) else None,
        "review_decision": str(raw.get("review_decision") or ""),
        "import_source": dict(raw.get("import_source") or {}) if isinstance(raw.get("import_source"), dict) else None,
    }


def build_dynamic_input_blueprint(
    project_id: str,
    profile: dict[str, Any],
    *,
    start_type: str,
    interview_answers: dict[str, Any] | None = None,
    existing_items: list[dict[str, Any]] | dict[str, dict[str, Any]] | None = None,
    imported_candidates: list[dict[str, Any]] | None = None,
    template_id: str | None = None,
    revision: int = 1,
    parent_revision_id: str | None = None,
) -> DynamicInputBlueprint:
    template = governed_template(profile, template_id)
    metadata = _metadata_by_key(existing_items or [])
    candidates = _metadata_by_key(imported_candidates or [])
    rows: list[dict[str, Any]] = []

    for spec in suggested_item_specs(template["template_id"]):
        key = spec["input_key"]
        source = metadata.get(key) or candidates.get(key) or {}
        value = source.get("value", spec.get("default_value"))
        state = source.get("state")
        if not state:
            if value is None:
                state = "UNKNOWN"
            elif spec.get("default_value") is not None:
                state = "CLIENT_ESTIMATE"
            else:
                state = "VALUE_ENTERED"
        rows.append(
            _normal_item(
                project_id,
                key,
                {
                    **spec,
                    **source,
                    "state": state,
                    "required": bool(spec.get("required")),
                    "approval_status": source.get("approval_status") or "draft",
                    "source_type": source.get("source_type")
                    or ("file_import" if source.get("import_source") else "user_input"),
                },
                value,
                legacy=False,
            )
        )

    known = {row["input_key"] for row in rows}
    for key, source in {**candidates, **metadata}.items():
        if key in known:
            continue
        rows.append(_normal_item(project_id, key, source, source.get("value"), legacy=False))

    revision_id = new_id("dibrev")
    material = {
        "project_id": project_id,
        "template_id": template["template_id"],
        "revision_id": revision_id,
        "revision": revision,
        "parent_revision_id": parent_revision_id,
        "start_type": start_type,
        "items": rows,
        "interview_answers": interview_answers or {},
    }
    return DynamicInputBlueprint(
        blueprint_id=str(profile.get("blueprint_id") or f"dib:{project_id}"),
        project_id=project_id,
        template_id=template["template_id"],
        revision_id=revision_id,
        revision=revision,
        parent_revision_id=parent_revision_id,
        start_type=start_type,
        items=tuple(rows),
        interview_answers=dict(interview_answers or {}),
        status="DRAFT_REVIEW",
        created_at=now_iso(),
        content_hash=canonical_hash(material),
    )


def _market_evidence_valid(item: dict[str, Any]) -> bool:
    pack = item.get("evidence_pack")
    if not isinstance(pack, dict):
        return False
    if pack.get("contract_id") != "market.evidence.pack.v1":
        return False
    if pack.get("item_id") != item.get("item_id"):
        return False
    if pack.get("review_decision") != "approved":
        return False
    selected = pack.get("selected_value", pack.get("weighted_median"))
    try:
        return float(selected) == float(item.get("value"))
    except (TypeError, ValueError):
        return False


def _aggregate_value(normalized: dict[str, Any], finance_key: str, value: Any) -> None:
    if finance_key in normalized and isinstance(normalized[finance_key], (int, float)) and isinstance(value, (int, float)):
        normalized[finance_key] = normalized[finance_key] + value
    else:
        normalized[finance_key] = value


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
        value = meta.get("value", inputs.get(key))
        item = _normal_item(project_id, key, meta, value, legacy=legacy_compatibility)
        if assumption_refs and not item["assumption_refs"]:
            item["assumption_refs"] = list(assumption_refs)
        items.append(item)

        if str(meta.get("state") or "").upper() and str(meta.get("state")).upper() not in ITEM_STATES:
            blockers.append(_blocker("INVALID_BLUEPRINT_ITEM_STATE", f"حالة البند {key} غير معروفة."))

        state = item["state"]
        reason = item["reason"]
        approval_status = item["approval_status"]
        required = item["required"] or key in FINANCE_REQUIRED_KEYS

        if state in {"INTENTIONAL_ZERO", "NOT_APPLICABLE"} and not reason:
            blockers.append(_blocker("BLUEPRINT_REASON_REQUIRED", f"البند {key} يحتاج سببًا موثقًا لحالة {state}."))
        if state == "EXPERIMENTAL_ESTIMATE":
            if approval_status != "approved":
                blockers.append(_blocker("EXPERIMENTAL_ESTIMATE_NOT_APPROVED", f"التقدير التجريبي للبند {key} لم يعتمد بعد."))
            elif not _market_evidence_valid(item):
                blockers.append(_blocker("MARKET_EVIDENCE_PACK_INVALID", f"حزمة الدليل السوقي للبند {key} غير معتمدة أو لا تطابق القيمة."))
        if state == "UNKNOWN" and required:
            blockers.append(_blocker(f"UNKNOWN_{key.upper()}", f"البند المطلوب {key} غير معروف بعد."))
        if state in APPROVED_STATES and approval_status != "approved":
            blockers.append(_blocker("BLUEPRINT_ITEM_NOT_APPROVED", f"البند {key} لم يعتمد بعد."))

        if state in APPROVED_STATES and approval_status == "approved":
            if state == "NOT_APPLICABLE":
                accepted_value: Any = 0
            elif value is None or value == "":
                if state == "INTENTIONAL_ZERO":
                    accepted_value = 0
                else:
                    blockers.append(_blocker("APPROVED_ITEM_VALUE_MISSING", f"البند المعتمد {key} لا يحتوي قيمة."))
                    continue
            else:
                accepted_value = value
            if item["treatment"] != "exclude" or state == "NOT_APPLICABLE":
                _aggregate_value(normalized, item["finance_key"], accepted_value)

    for required_key in FINANCE_REQUIRED_KEYS:
        if required_key not in normalized:
            blockers.append(_blocker(f"MANIFEST_MISSING_{required_key.upper()}", f"الـManifest لا يحتوي البند المالي المطلوب {required_key}."))

    version = int(inputs.get("blueprint_revision") or max(1, len(inputs.get("blueprint_revisions") or [])))
    blueprint_id = str(inputs.get("blueprint_id") or f"dib:{project_id}")
    blueprint_revision_id = str(inputs.get("blueprint_revision_id") or "")
    template_id = str(inputs.get("template_id") or "template.generic.v1")
    status = "approved" if not blockers else "blocked"
    created_at = now_iso()
    material = {
        "project_id": project_id,
        "version": version,
        "status": status,
        "blueprint_id": blueprint_id,
        "blueprint_revision_id": blueprint_revision_id,
        "template_id": template_id,
        "items": items,
        "normalized_inputs": normalized,
        "blockers": blockers,
    }
    return ApprovedInputManifest(
        manifest_id=new_id("manifest"),
        project_id=project_id,
        version=version,
        status=status,
        items=tuple(items),
        normalized_inputs=normalized,
        blockers=tuple(blockers),
        created_at=created_at,
        legacy_compatibility=legacy_compatibility,
        blueprint_id=blueprint_id,
        blueprint_revision_id=blueprint_revision_id,
        template_id=template_id,
        content_hash=canonical_hash(material),
    )


def manifest_item_map(manifest: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not isinstance(manifest, dict):
        return {}
    return {
        str(item.get("input_key")): item
        for item in manifest.get("items", [])
        if isinstance(item, dict) and item.get("input_key")
    }
