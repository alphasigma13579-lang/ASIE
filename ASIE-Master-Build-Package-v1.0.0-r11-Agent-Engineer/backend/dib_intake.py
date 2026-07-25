from __future__ import annotations

import re
from typing import Any

ALIASES: dict[str, tuple[str, ...]] = {
    "startup_cost": ("تكلفة التأسيس", "startup", "establishment", "initial cost"),
    "monthly_fixed_cost": ("تكاليف ثابتة", "monthly fixed", "fixed cost"),
    "unit_price": ("سعر الوحدة", "سعر البيع", "unit price", "selling price"),
    "variable_cost": ("تكلفة متغيرة", "variable cost", "cost per unit"),
    "monthly_units": ("وحدات شهرية", "مبيعات شهرية", "monthly units", "monthly volume"),
    "rent_monthly": ("إيجار", "rent", "lease"),
    "payroll_monthly": ("رواتب", "أجور", "payroll", "salary", "labor"),
    "utilities_monthly": ("كهرباء", "مياه", "غاز", "مرافق", "utilities"),
    "marketing_monthly": ("تسويق", "marketing", "ads"),
    "maintenance_monthly": ("صيانة", "maintenance"),
    "capex_equipment": ("معدات", "equipment", "machinery"),
    "capex_fitout": ("تجهيز", "ديكور", "fitout", "fit-out"),
    "capex_licenses_local": ("ترخيص", "رسوم", "license", "permit"),
    "equipment_shawarma_grill": ("شواية شاورما", "shawarma grill", "grill"),
    "equipment_refrigeration": ("ثلاجة", "تبريد", "freezer", "refriger"),
    "equipment_prep": ("تحضير", "تقطيع", "prep", "cutter"),
    "equipment_pos": ("نقاط البيع", "pos", "cashier"),
}


def _text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().lower()


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    match = re.search(r"-?\d[\d,]*(?:\.\d+)?", str(value))
    if not match:
        return None
    try:
        return float(match.group(0).replace(",", ""))
    except ValueError:
        return None


def _row_description(row: dict[str, Any]) -> str:
    preferred = ("description", "item", "name", "label", "البند", "الوصف", "الصنف")
    for key in preferred:
        if key in row and _text(row[key]):
            return str(row[key])
    text_values = [str(value) for value in row.values() if value not in {None, ""} and _number(value) is None]
    return " ".join(text_values)


def _row_amount(row: dict[str, Any]) -> float | None:
    preferred = ("amount", "price", "value", "cost", "total", "المبلغ", "السعر", "القيمة", "الإجمالي")
    for key in preferred:
        if key in row:
            value = _number(row[key])
            if value is not None:
                return value
    numeric = [_number(value) for value in row.values()]
    values = [value for value in numeric if value is not None]
    return values[-1] if values else None


def _score(description: str, spec: dict[str, Any]) -> int:
    key = str(spec.get("input_key") or "")
    label = _text(spec.get("label"))
    description = _text(description)
    score = 0
    if label and label in description:
        score += 8
    for alias in ALIASES.get(key, ()):
        if _text(alias) in description:
            score += 6
    for token in re.findall(r"[\w\u0600-\u06ff]+", f"{label} {key.replace('_', ' ')}"):
        if len(token) >= 3 and token in description:
            score += 1
    return score


def map_rows_to_blueprint_candidates(
    rows: list[dict[str, Any]],
    specs: list[dict[str, Any]],
    *,
    dataset_id: str = "",
    file_name: str = "",
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    used_keys: set[str] = set()
    for index, row in enumerate(rows):
        description = _row_description(row)
        amount = _row_amount(row)
        if amount is None:
            continue
        ranked = sorted(
            ((score := _score(description, spec), spec) for spec in specs),
            key=lambda pair: pair[0],
            reverse=True,
        )
        best_score, best_spec = ranked[0] if ranked else (0, {})
        base_key = str(best_spec.get("input_key") or "") if best_score > 0 else ""
        if not base_key:
            slug = re.sub(r"[^a-z0-9]+", "_", description.lower()).strip("_")[:32] or f"row_{index + 1}"
            base_key = f"imported_{slug}"
            best_spec = {
                "input_key": base_key,
                "label": description or f"بند مستورد {index + 1}",
                "category": "custom",
                "unit": "SAR",
                "finance_key": base_key,
                "required": False,
            }
        key = base_key
        counter = 2
        while key in used_keys:
            key = f"{base_key}_{counter}"
            counter += 1
        used_keys.add(key)
        candidates.append(
            {
                "item_id": f"imported:{dataset_id or 'local'}:{index + 1}",
                "input_key": key,
                "finance_key": str(best_spec.get("finance_key") or base_key),
                "label": str(best_spec.get("label") or description),
                "category": str(best_spec.get("category") or "custom"),
                "value": amount,
                "unit": str(best_spec.get("unit") or "SAR"),
                "state": "CLIENT_ESTIMATE",
                "reason": "قيمة مستوردة وتحتاج مطابقة واعتماد المستخدم.",
                "source_type": "file_import",
                "treatment": "include",
                "approval_status": "draft",
                "confidence": 0.55 if best_score >= 6 else 0.35,
                "required": bool(best_spec.get("required")),
                "import_source": {
                    "dataset_id": dataset_id,
                    "file_name": file_name,
                    "row_index": index,
                    "raw_row": dict(row),
                    "mapping_score": best_score,
                    "mapping_status": "matched" if best_score > 0 else "custom_unmatched",
                },
                "evidence_refs": [f"dataset:{dataset_id}:row:{index + 1}"] if dataset_id else [],
            }
        )
    return candidates
