from __future__ import annotations

import base64
import csv
import re
import statistics
import zipfile
from dataclasses import dataclass, field
from io import BytesIO, StringIO
from typing import Any
from xml.etree import ElementTree

from backend.contracts import new_id, now_iso
from backend.finance_engine import finance_result_set

DIB_CONTRACTS = {
    "template.registry.v1",
    "question.registry.v1",
    "product.ai.interview.v1",
    "data.intake.v1",
    "dynamic.input.blueprint.v1",
    "market.query.request.v1",
    "market.evidence.pack.v1",
    "customer.item.decision.v1",
    "approved.input.manifest.v1",
    "manifest.validation.v1",
    "dib.draft.revision.v1",
}

DIB_SOCKETS = {
    "socket.template.registry",
    "socket.question.registry",
    "socket.product.ai.interview",
    "socket.data.intake",
    "socket.dynamic.input.blueprint",
    "socket.market.query",
    "socket.customer.item.decision",
    "socket.approved.input.manifest",
    "socket.manifest.validation",
    "socket.dib.revision",
}

DIB_MODULES = {
    "module.template_registry",
    "module.question_registry",
    "module.product_ai_interview",
    "module.data_intake",
    "module.dynamic_input_blueprint",
    "module.market_intelligence",
    "module.approved_input_manifest",
    "module.manifest_validation_gate",
    "module.dib_revision",
}

FINANCE_REQUIRED_KEYS = ("startup_cost", "monthly_fixed_cost", "unit_price", "variable_cost", "monthly_units")
OPTIONAL_FINANCE_DEFAULTS = {
    "capital_available": 0,
    "use_operating_capacity": False,
    "payroll_monthly": 0,
    "rent_monthly": 0,
    "utilities_monthly": 0,
    "marketing_monthly": 0,
    "maintenance_monthly": 0,
    "capex_equipment": 0,
    "capex_fitout": 0,
    "capex_licenses_local": 0,
    "depreciation_years": 5,
    "equity_contribution": 0,
    "loan_grace_months": 0,
    "annual_discount_rate": 0.1,
    "working_capital_months": 2,
    "debt_amount": 0,
    "annual_interest_rate": 0.0,
    "loan_years": 5,
}

ITEM_STATES = {
    "UNKNOWN",
    "NOT_APPLICABLE",
    "USER_PROVIDED",
    "FILE_IMPORTED",
    "AI_SUGGESTED",
    "MARKET_ESTIMATED",
    "EVIDENCE_VERIFIED",
    "HUMAN_APPROVED",
    "REJECTED",
    "INTENTIONAL_ZERO",
}

APPROVABLE_STATES = {
    "USER_PROVIDED",
    "FILE_IMPORTED",
    "MARKET_ESTIMATED",
    "EVIDENCE_VERIFIED",
    "HUMAN_APPROVED",
    "NOT_APPLICABLE",
    "INTENTIONAL_ZERO",
}

ITEM_KEYWORDS = {
    "startup_cost": ("startup", "capex", "equipment", "fitout", "تأسيس", "معدات", "تجهيز"),
    "monthly_fixed_cost": ("fixed", "opex", "monthly", "rent", "salary", "إيجار", "رواتب", "شهري"),
    "unit_price": ("price", "selling", "meal", "unit", "سعر", "بيع", "وجبة"),
    "variable_cost": ("variable", "cogs", "ingredient", "cost per unit", "تكلفة", "مواد", "مباشرة"),
    "monthly_units": ("units", "quantity", "demand", "monthly sales", "عدد", "مبيعات", "شهري"),
}

MARKET_SAMPLE_CATALOGUE = {
    "startup_cost": [85000, 118000, 132000, 145000, 190000, 470000],
    "monthly_fixed_cost": [23000, 28000, 34000, 41000, 56000, 120000],
    "unit_price": [12, 16, 18, 20, 24, 65],
    "variable_cost": [5, 6.5, 8, 9, 11, 38],
    "monthly_units": [2600, 3600, 4200, 5200, 6400, 19000],
    "capex_equipment": [42000, 55000, 69000, 78000, 110000, 260000],
    "rent_monthly": [12000, 18000, 23000, 28000, 36000, 90000],
}


@dataclass(frozen=True)
class DIBBusMessage:
    source_module_id: str
    target_module_id: str
    contract_id: str
    socket_id: str
    payload: dict[str, Any]
    correlation_id: str = field(default_factory=lambda: new_id("corr"))
    audit_ref: str = field(default_factory=lambda: new_id("audit"))
    message_id: str = field(default_factory=lambda: new_id("msg"))
    created_at: str = field(default_factory=now_iso)

    def validate(self) -> None:
        if self.contract_id not in DIB_CONTRACTS:
            raise ValueError(f"unknown_dib_contract:{self.contract_id}")
        if self.socket_id not in DIB_SOCKETS:
            raise ValueError(f"unknown_dib_socket:{self.socket_id}")
        if self.source_module_id not in DIB_MODULES and not self.source_module_id.startswith("aas."):
            raise ValueError(f"unknown_dib_source_module:{self.source_module_id}")
        if self.target_module_id not in DIB_MODULES:
            raise ValueError(f"unknown_dib_target_module:{self.target_module_id}")


class DIBBus:
    def __init__(self) -> None:
        self.messages: list[dict[str, Any]] = []

    def dispatch(self, message: DIBBusMessage, handler) -> dict[str, Any]:
        message.validate()
        result = handler(message.payload)
        self.messages.append({"message": message.__dict__, "delivered": True, "executed_at": now_iso()})
        return result


def canonical_template_registry() -> dict[str, Any]:
    return {
        "contract_id": "template.registry.v1",
        "registry_id": "template:project-input:v1",
        "templates": [
            {
                "template_id": "template:food-service:shawarma:v1",
                "sector": "Food Service",
                "activity": "shawarma_shop",
                "required_item_keys": list(FINANCE_REQUIRED_KEYS),
                "recommended_item_keys": ["capex_equipment", "rent_monthly", "payroll_monthly", "utilities_monthly"],
                "aliases": {key: list(values) for key, values in ITEM_KEYWORDS.items()},
            },
            {
                "template_id": "template:generic-startup:v1",
                "sector": "General",
                "activity": "generic_project",
                "required_item_keys": list(FINANCE_REQUIRED_KEYS),
                "recommended_item_keys": ["capex_equipment", "rent_monthly", "payroll_monthly"],
                "aliases": {key: list(values) for key, values in ITEM_KEYWORDS.items()},
            },
        ],
    }


def canonical_question_registry() -> dict[str, Any]:
    return {
        "contract_id": "question.registry.v1",
        "registry_id": "questions:dib:v1",
        "questions": [
            {"question_id": "q:site", "field": "location", "kind": "choice", "required": True},
            {"question_id": "q:sector", "field": "sector", "kind": "choice", "required": True},
            {"question_id": "q:model", "field": "operating_model", "kind": "choice", "required": True},
            {"question_id": "q:equipment", "field": "equipment", "kind": "confirm_list", "required": True},
            {"question_id": "q:pricing", "field": "unit_price", "kind": "number_or_estimate", "required": True},
            {"question_id": "q:volume", "field": "monthly_units", "kind": "number_or_estimate", "required": True},
        ],
    }


def _as_number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    cleaned = re.sub(r"[^0-9.\-]", "", str(value))
    if cleaned in {"", "-", "."}:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _item(input_key: str, *, value: Any = None, state: str = "UNKNOWN", label: str | None = None, source_type: str = "user_input", evidence_refs: list[str] | None = None, reason: str = "", required: bool = False, confidence: float = 0.5) -> dict[str, Any]:
    if state not in ITEM_STATES:
        raise ValueError(f"invalid_blueprint_item_state:{state}")
    return {
        "item_id": new_id("dib_item"),
        "input_key": input_key,
        "label": label or input_key,
        "category": "finance_assumption",
        "value": value,
        "unit": "SAR" if input_key not in {"monthly_units", "depreciation_years", "loan_years"} else "unit",
        "value_state": state,
        "value_source": source_type,
        "source_type": source_type,
        "confidence": confidence,
        "evidence_refs": evidence_refs or [],
        "review_status": "draft",
        "required": required,
        "reason": reason,
        "revision": 1,
    }


def build_product_ai_interview(profile: dict[str, Any]) -> dict[str, Any]:
    sector = str(profile.get("sector") or profile.get("primary_sector_id") or "general")
    activity = str(profile.get("activity") or profile.get("activity_description") or profile.get("name") or "project")
    template = "template:food-service:shawarma:v1" if "shawarma" in activity.lower() or "شاور" in activity else "template:generic-startup:v1"
    items = []
    for key in FINANCE_REQUIRED_KEYS:
        items.append(_item(key, state="AI_SUGGESTED", label=key.replace("_", " "), source_type="product_ai_interview", required=True, confidence=0.45))
    for key in ["capex_equipment", "rent_monthly", "payroll_monthly", "utilities_monthly"]:
        items.append(_item(key, state="AI_SUGGESTED", label=key.replace("_", " "), source_type="product_ai_interview", required=False, confidence=0.4))
    return {
        "contract_id": "product.ai.interview.v1",
        "interview_id": new_id("interview"),
        "project_profile": dict(profile),
        "template_id": template,
        "sector": sector,
        "activity": activity,
        "questions": canonical_question_registry()["questions"],
        "proposed_items": items,
        "ai_provider_enabled": False,
        "external_fetch_enabled": False,
    }


def parse_csv_rows(csv_text: str) -> list[dict[str, Any]]:
    return [dict(row) for row in csv.DictReader(StringIO(csv_text or ""))]


def parse_xlsx_rows(file_base64: str) -> list[dict[str, Any]]:
    raw = base64.b64decode(file_base64)
    with zipfile.ZipFile(BytesIO(raw)) as archive:
        shared_strings = _xlsx_shared_strings(archive)
        sheet_candidates = sorted(name for name in archive.namelist() if name.startswith("xl/worksheets/sheet") and name.endswith(".xml"))
        if not sheet_candidates:
            return []
        with archive.open(sheet_candidates[0]) as sheet_file:
            root = ElementTree.parse(sheet_file).getroot()
    ns = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    matrix: list[list[str]] = []
    for row in root.findall(".//x:sheetData/x:row", ns):
        values = []
        for cell in row.findall("x:c", ns):
            values.append(_xlsx_cell_value(cell, shared_strings, ns))
        matrix.append(values)
    if not matrix:
        return []
    headers = [str(value or f"column_{index + 1}") for index, value in enumerate(matrix[0])]
    return [{headers[index]: values[index] if index < len(values) else "" for index in range(len(headers))} for values in matrix[1:]]


def _xlsx_shared_strings(archive: zipfile.ZipFile) -> list[str]:
    try:
        with archive.open("xl/sharedStrings.xml") as shared_file:
            root = ElementTree.parse(shared_file).getroot()
    except KeyError:
        return []
    ns = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    return ["".join(node.text or "" for node in item.findall(".//x:t", ns)) for item in root.findall("x:si", ns)]


def _xlsx_cell_value(cell: ElementTree.Element, shared_strings: list[str], ns: dict[str, str]) -> str:
    inline_node = cell.find("x:is/x:t", ns)
    if inline_node is not None:
        return inline_node.text or ""
    value_node = cell.find("x:v", ns)
    if value_node is None:
        return ""
    raw_value = value_node.text or ""
    if cell.attrib.get("t") == "s":
        try:
            return shared_strings[int(raw_value)]
        except (ValueError, IndexError):
            return ""
    return raw_value


def parse_pdf_quote_text(payload: dict[str, Any]) -> str:
    if payload.get("pdf_text"):
        return str(payload["pdf_text"])
    if payload.get("file_base64"):
        raw = base64.b64decode(str(payload["file_base64"]))
        return raw.decode("latin-1", errors="ignore")
    return ""


def _match_input_key(row: dict[str, Any]) -> str | None:
    material = " ".join(str(value).lower() for value in row.values())
    for input_key, words in ITEM_KEYWORDS.items():
        if any(word.lower() in material for word in words):
            return input_key
    return None


def map_intake_to_blueprint_items(payload: dict[str, Any], existing_items: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    file_name = str(payload.get("file_name") or "manual")
    extension = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
    rows: list[dict[str, Any]] = []
    pdf_text = ""
    if extension == "csv" or payload.get("csv_text"):
        rows = parse_csv_rows(str(payload.get("csv_text") or ""))
    elif extension in {"xlsx", "xls"} or str(payload.get("file_type") or "").endswith("spreadsheetml.sheet"):
        rows = parse_xlsx_rows(str(payload.get("file_base64") or ""))
    elif extension == "pdf" or payload.get("pdf_text"):
        pdf_text = parse_pdf_quote_text(payload)
        rows = quote_rows_from_text(pdf_text)
    elif isinstance(payload.get("rows"), list):
        rows = [dict(row) for row in payload["rows"] if isinstance(row, dict)]
    else:
        raise ValueError("unsupported_dib_data_intake_type")

    mapped = {item["input_key"]: dict(item) for item in (existing_items or [])}
    unmatched_rows = []
    for row in rows:
        input_key = str(row.get("input_key") or "").strip() or (_match_input_key(row) or "")
        numeric_candidates = [_as_number(value) for value in row.values()]
        numeric_values = [value for value in numeric_candidates if value is not None]
        if not input_key or not numeric_values:
            unmatched_rows.append(row)
            continue
        value = sum(numeric_values) if input_key in {"startup_cost", "monthly_fixed_cost"} and len(numeric_values) > 1 else numeric_values[-1]
        mapped[input_key] = _item(
            input_key,
            value=value,
            state="FILE_IMPORTED",
            label=str(row.get("label") or row.get("item") or input_key),
            source_type="file_import",
            evidence_refs=[f"file:{file_name}"],
            confidence=0.72,
            required=input_key in FINANCE_REQUIRED_KEYS,
        )
    return {
        "contract_id": "data.intake.v1",
        "intake_id": new_id("intake"),
        "file_name": file_name,
        "file_type": extension or "manual_table",
        "rows": rows[:50],
        "pdf_text_extracted": bool(pdf_text),
        "mapped_items": list(mapped.values()),
        "unmatched_rows": unmatched_rows,
        "external_fetch_enabled": False,
    }


def quote_rows_from_text(text: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in text.splitlines():
        value = _as_number(line)
        if value is None:
            continue
        key = _match_input_key({"line": line}) or "startup_cost"
        rows.append({"input_key": key, "label": line.strip()[:80] or key, "value": value})
    return rows


def build_dynamic_input_blueprint(project_profile: dict[str, Any], items: list[dict[str, Any]], *, source: str = "runtime") -> dict[str, Any]:
    by_key: dict[str, dict[str, Any]] = {}
    for item in items:
        key = str(item.get("input_key") or "").strip()
        if key:
            by_key[key] = dict(item)
    for key in FINANCE_REQUIRED_KEYS:
        by_key.setdefault(key, _item(key, state="UNKNOWN", label=key.replace("_", " "), required=True))
    return {
        "contract_id": "dynamic.input.blueprint.v1",
        "blueprint_id": new_id("dib"),
        "project_id": str(project_profile.get("project_id") or new_id("project")),
        "project_profile": dict(project_profile),
        "source": source,
        "items": list(by_key.values()),
        "revision": 1,
        "created_at": now_iso(),
    }


def _filtered_market_samples(input_key: str, candidate_values: list[float] | None = None) -> list[float]:
    values = list(candidate_values or MARKET_SAMPLE_CATALOGUE.get(input_key) or [10, 20, 30])
    if len(values) < 4:
        return values
    ordered = sorted(values)
    q1 = ordered[len(ordered) // 4]
    q3 = ordered[(len(ordered) * 3) // 4]
    iqr = q3 - q1
    if iqr <= 0:
        return ordered
    low, high = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    filtered = [value for value in ordered if low <= value <= high]
    return filtered or ordered


def build_market_evidence_pack(payload: dict[str, Any]) -> dict[str, Any]:
    input_key = str(payload.get("input_key") or "")
    samples = _filtered_market_samples(input_key, [_as_number(value) for value in payload.get("samples", []) if _as_number(value) is not None] or None)
    ordered = sorted(samples)
    median = statistics.median(ordered)
    p25 = ordered[max(0, round((len(ordered) - 1) * 0.25))]
    p75 = ordered[min(len(ordered) - 1, round((len(ordered) - 1) * 0.75))]
    return {
        "contract_id": "market.evidence.pack.v1",
        "market_query_contract_id": "market.query.request.v1",
        "evidence_pack_id": new_id("market_pack"),
        "input_key": input_key,
        "query": payload.get("query") or input_key,
        "geography": payload.get("geography") or payload.get("location_country") or "SA",
        "sample_count": len(ordered),
        "outlier_policy": "IQR_1_5_FILTER",
        "p25": p25,
        "weighted_median": median,
        "p75": p75,
        "source_refs": [f"simulated-market:{input_key}:p{idx}" for idx, _ in enumerate(ordered, 1)],
        "confidence": 0.66 if len(ordered) >= 5 else 0.52,
        "external_fetch_enabled": False,
        "provider": "local_simulated_market_intelligence",
    }


def request_market_evidence(bus: DIBBus, item: dict[str, Any], *, geography: str = "SA") -> dict[str, Any]:
    message = DIBBusMessage(
        source_module_id="module.dynamic_input_blueprint",
        target_module_id="module.market_intelligence",
        contract_id="market.query.request.v1",
        socket_id="socket.market.query",
        payload={"input_key": item["input_key"], "query": item.get("label") or item["input_key"], "geography": geography},
    )
    return bus.dispatch(message, build_market_evidence_pack)


def apply_customer_decision(item: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:
    action = str(decision.get("action") or "").lower()
    updated = dict(item)
    if action == "accept_market_median":
        pack = decision.get("evidence_pack") or {}
        updated["value"] = pack.get("weighted_median")
        updated["value_state"] = "MARKET_ESTIMATED"
        updated["value_source"] = "market_evidence"
        updated["source_type"] = "market_evidence"
        updated["evidence_refs"] = list(pack.get("source_refs") or [])
        updated["confidence"] = pack.get("confidence", 0.6)
    elif action == "enter_value":
        updated["value"] = decision.get("value")
        updated["value_state"] = "USER_PROVIDED"
        updated["value_source"] = "user_input"
        updated["source_type"] = "user_input"
        updated["confidence"] = 0.78
    elif action == "mark_unknown":
        updated["value"] = None
        updated["value_state"] = "UNKNOWN"
        updated["reason"] = str(decision.get("reason") or "customer_unknown")
    elif action == "not_applicable":
        updated["value"] = 0
        updated["value_state"] = "NOT_APPLICABLE"
        updated["reason"] = str(decision.get("reason") or "not_applicable_to_model")
    elif action == "reject":
        updated["value_state"] = "REJECTED"
        updated["review_status"] = "rejected"
    else:
        raise ValueError("unknown_customer_item_decision")
    updated["review_status"] = "approved" if updated.get("value_state") in APPROVABLE_STATES else updated.get("review_status", "draft")
    updated["revision"] = int(updated.get("revision") or 1) + 1
    return updated


def build_approved_input_manifest(blueprint: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(OPTIONAL_FINANCE_DEFAULTS)
    blockers: list[dict[str, str]] = []
    approved_items = []
    for item in blueprint.get("items", []):
        row = dict(item)
        key = str(row.get("input_key") or "")
        state = str(row.get("value_state") or row.get("state") or "UNKNOWN")
        value = row.get("value")
        if state not in ITEM_STATES:
            blockers.append({"code": "INVALID_BLUEPRINT_ITEM_STATE", "severity": "critical", "message": f"Invalid state for {key}"})
        if key in FINANCE_REQUIRED_KEYS and state == "UNKNOWN":
            blockers.append({"code": f"UNKNOWN_{key.upper()}", "severity": "critical", "message": f"Required item {key} is unknown"})
        numeric = _as_number(value)
        if key in FINANCE_REQUIRED_KEYS and state in APPROVABLE_STATES:
            if numeric is None:
                blockers.append({"code": f"MISSING_{key.upper()}", "severity": "critical", "message": f"Required item {key} has no numeric value"})
            elif numeric == 0 and state not in {"NOT_APPLICABLE", "INTENTIONAL_ZERO"}:
                blockers.append({"code": f"UNJUSTIFIED_ZERO_{key.upper()}", "severity": "critical", "message": f"Zero value for {key} requires explicit state"})
            else:
                normalized[key] = numeric
        elif numeric is not None:
            normalized[key] = numeric
        approved_items.append(row | {"state": state})
    for key in FINANCE_REQUIRED_KEYS:
        if key not in normalized:
            blockers.append({"code": f"MISSING_{key.upper()}", "severity": "critical", "message": f"Required item {key} not normalized"})
    return {
        "contract_id": "approved.input.manifest.v1",
        "manifest_id": new_id("manifest"),
        "project_id": blueprint["project_id"],
        "blueprint_id": blueprint["blueprint_id"],
        "revision": blueprint.get("revision", 1),
        "status": "approved" if not blockers else "blocked",
        "items": approved_items,
        "normalized_inputs": normalized,
        "blockers": blockers,
        "created_at": now_iso(),
    }


def validate_manifest_for_runtime(manifest: dict[str, Any]) -> dict[str, Any]:
    blockers = list(manifest.get("blockers") or [])
    if manifest.get("contract_id") != "approved.input.manifest.v1":
        blockers.append({"code": "INVALID_MANIFEST_CONTRACT", "severity": "critical", "message": "Manifest contract mismatch"})
    if manifest.get("status") != "approved":
        blockers.append({"code": "MANIFEST_NOT_APPROVED", "severity": "critical", "message": "Manifest is not approved"})
    inputs = manifest.get("normalized_inputs") or {}
    for key in FINANCE_REQUIRED_KEYS:
        value = _as_number(inputs.get(key))
        if value is None:
            blockers.append({"code": f"RUNTIME_MISSING_{key.upper()}", "severity": "critical", "message": f"Runtime input missing {key}"})
    return {
        "contract_id": "manifest.validation.v1",
        "gate_id": new_id("manifest_gate"),
        "manifest_id": manifest.get("manifest_id"),
        "status": "passed" if not blockers else "blocked",
        "blockers": blockers,
        "created_at": now_iso(),
    }


def finance_from_approved_manifest(manifest: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, str]]]:
    gate = validate_manifest_for_runtime(manifest)
    if gate["status"] != "passed":
        return {"status": "not_ready", "baseline": None, "manifest_validation": gate}, gate["blockers"]
    finance, blockers = finance_result_set(dict(manifest["normalized_inputs"]))
    finance["approved_input_manifest"] = {
        "manifest_id": manifest["manifest_id"],
        "blueprint_id": manifest["blueprint_id"],
        "contract_id": manifest["contract_id"],
        "manifest_validation": gate,
    }
    return finance, blockers


def create_draft_revision(previous_blueprint: dict[str, Any], changes: list[dict[str, Any]], *, reason: str = "user_revision") -> dict[str, Any]:
    by_key = {item["input_key"]: dict(item) for item in previous_blueprint.get("items", [])}
    for change in changes:
        key = str(change.get("input_key") or "")
        if not key:
            continue
        current = by_key.get(key, _item(key, state="UNKNOWN"))
        by_key[key] = apply_customer_decision(current, change) if change.get("action") else (current | dict(change))
    return previous_blueprint | {
        "blueprint_id": new_id("dib"),
        "parent_blueprint_id": previous_blueprint.get("blueprint_id"),
        "revision": int(previous_blueprint.get("revision") or 1) + 1,
        "revision_reason": reason,
        "items": list(by_key.values()),
        "created_at": now_iso(),
        "contract_id": "dib.draft.revision.v1",
    }


def compare_blueprint_revisions(first: dict[str, Any], second: dict[str, Any]) -> dict[str, Any]:
    first_rows = {row["input_key"]: row for row in first.get("items", [])}
    second_rows = {row["input_key"]: row for row in second.get("items", [])}
    changes = []
    for key in sorted(set(first_rows) | set(second_rows)):
        before, after = first_rows.get(key, {}), second_rows.get(key, {})
        if before.get("value") != after.get("value") or before.get("value_state") != after.get("value_state"):
            changes.append({"input_key": key, "from": before.get("value"), "to": after.get("value"), "state_from": before.get("value_state"), "state_to": after.get("value_state")})
    return {
        "comparison_id": new_id("dib_compare"),
        "first_blueprint_id": first.get("blueprint_id"),
        "second_blueprint_id": second.get("blueprint_id"),
        "revision_delta": int(second.get("revision") or 0) - int(first.get("revision") or 0),
        "item_changes": changes,
    }


def run_idea_to_manifest_flow(project_profile: dict[str, Any]) -> dict[str, Any]:
    bus = DIBBus()
    interview = bus.dispatch(
        DIBBusMessage("aas.heart_controller", "module.product_ai_interview", "product.ai.interview.v1", "socket.product.ai.interview", project_profile),
        build_product_ai_interview,
    )
    blueprint = build_dynamic_input_blueprint(project_profile, interview["proposed_items"], source="product_ai_interview")
    updated_items = []
    for item in blueprint["items"]:
        if item["input_key"] in FINANCE_REQUIRED_KEYS:
            pack = request_market_evidence(bus, item, geography=str(project_profile.get("location_country") or "SA"))
            updated_items.append(apply_customer_decision(item, {"action": "accept_market_median", "evidence_pack": pack}))
        else:
            updated_items.append(item)
    blueprint = blueprint | {"items": updated_items, "revision": 2}
    manifest = build_approved_input_manifest(blueprint)
    gate = validate_manifest_for_runtime(manifest)
    finance, blockers = finance_from_approved_manifest(manifest)
    return {"interview": interview, "blueprint": blueprint, "manifest": manifest, "manifest_validation": gate, "finance": finance, "blockers": blockers, "bus_messages": bus.messages}
