from __future__ import annotations

import re
from typing import Any

from backend.dib_module_adapters import execute_dib_module_adapter

DIB_INTAKE_ITEM_GOVERNANCE_ID = "DIB-COMPLETION-PACKAGE-B-INTAKE-ITEM-GOVERNANCE-v1"
DIB_INTAKE_ITEM_GOVERNANCE_STATUS = "post_freeze_intake_item_governance"
DIB_INTAKE_ITEM_GOVERNANCE_SOURCE = "docs/EKB/EKB-02-Source-of-Truth-Matrix.md"

FORBIDDEN_GOVERNANCE_FIELDS = frozenset(
    {
        "raw_prompt",
        "prompt_template",
        "raw_file",
        "file_base64",
        "pdf_text",
        "api_key",
        "openai_api_key",
        "provider_config",
        "ai_provider",
        "finance",
        "finance_result",
        "finance_inputs",
        "snapshot",
        "assembled_snapshot",
        "sealed_outputs",
        "decision_pack",
    }
)

FORBIDDEN_GOVERNANCE_TRUE_FLAGS = frozenset(
    {
        "ai_provider_enabled",
        "ai_enabled",
        "external_fetch_enabled",
        "network_fetch",
        "network_request",
        "finance_wiring_enabled",
        "snapshot_wiring_enabled",
    }
)

QUOTE_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("monthly_units", ("عدد", "مبيعات", "طلبات", "units", "quantity", "demand", "sales")),
    ("unit_price", ("سعر", "بيع", "وجبة", "price", "selling", "meal", "unit price")),
    ("variable_cost", ("مواد", "مكونات", "تكلفة مباشرة", "تكلفة الوحدة", "ingredient", "variable", "cogs")),
    ("rent_monthly", ("إيجار", "rent", "lease")),
    ("payroll_monthly", ("رواتب", "راتب", "salary", "payroll", "wage")),
    ("utilities_monthly", ("كهرباء", "مياه", "مرافق", "utilities", "electric", "water")),
    ("capex_equipment", ("معدات", "معدة", "equipment", "machine", "oven", "fridge")),
    ("monthly_fixed_cost", ("شهري", "fixed", "monthly", "opex")),
    ("startup_cost", ("تأسيس", "تجهيز", "معدات", "فرن", "ثلاجة", "capex", "equipment", "fitout", "startup")),
)


def _reject_forbidden(value: Any, *, context: str = "dib_intake_item_governance") -> None:
    def walk(node: Any, path: str) -> None:
        if isinstance(node, dict):
            for key, item in node.items():
                key_text = str(key)
                if key_text in FORBIDDEN_GOVERNANCE_FIELDS:
                    raise ValueError(f"{context}_forbidden_field:{path}.{key_text}")
                if key_text in FORBIDDEN_GOVERNANCE_TRUE_FLAGS and item is True:
                    raise ValueError(f"{context}_forbidden_flag:{path}.{key_text}")
                walk(item, f"{path}.{key_text}")
        elif isinstance(node, list):
            for index, item in enumerate(node):
                walk(item, f"{path}[{index}]")

    walk(value, context)


def _as_number(value: Any) -> float | None:
    if value is None or value == "" or isinstance(value, bool):
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


def _input_key_for_quote_line(line: str) -> str:
    material = line.lower()
    for input_key, keywords in QUOTE_KEYWORDS:
        if any(keyword.lower() in material for keyword in keywords):
            return input_key
    return "startup_cost"


def supplier_quote_rows_from_text(text: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in str(text or "").splitlines():
        numeric = _as_number(line)
        if numeric is None:
            continue
        label = re.sub(r"[0-9,.\-]+", "", line).strip(" :\t-—") or "supplier_quote_item"
        input_key = _input_key_for_quote_line(line)
        rows.append({"input_key": input_key, "label": label[:80], "value": numeric})
    return rows


def resolve_template_registry_surface(project_profile: dict[str, Any], template_id: str | None = None) -> dict[str, Any]:
    _reject_forbidden(project_profile, context="project_profile")
    payload: dict[str, Any] = {"project_profile": dict(project_profile)}
    if template_id:
        payload["template_id"] = template_id
    template = execute_dib_module_adapter("module.template_registry", payload)
    questions = execute_dib_module_adapter("module.question_registry", {"template_id": template["template_id"]})
    return {
        "governance_id": DIB_INTAKE_ITEM_GOVERNANCE_ID,
        "contract_id": "template.registry.v1",
        "template_registry": template,
        "question_registry": questions,
        "template_id": template["template_id"],
        "template_items": list(template.get("template_items") or []),
        "questions": list(questions.get("questions") or []),
        "external_fetch_enabled": False,
        "ai_provider_enabled": False,
        "finance_wiring_enabled": False,
        "snapshot_wiring_enabled": False,
    }


def governed_intake_payload(payload: dict[str, Any]) -> dict[str, Any]:
    _reject_forbidden(payload)
    source_name = str(payload.get("source_name") or payload.get("file_name") or "manual_intake")
    if isinstance(payload.get("rows"), list):
        return {"file_name": source_name, "rows": [dict(row) for row in payload["rows"] if isinstance(row, dict)]}
    if payload.get("supplier_quote_text"):
        return {
            "file_name": source_name if "." in source_name else f"{source_name}.supplier-quote.txt",
            "rows": supplier_quote_rows_from_text(str(payload.get("supplier_quote_text") or "")),
        }
    if payload.get("csv_text"):
        return {"file_name": source_name if source_name.endswith(".csv") else f"{source_name}.csv", "csv_text": str(payload.get("csv_text") or "")}
    raise ValueError("unsupported_governed_dib_intake_payload")


def preview_intake_item_mapping(payload: dict[str, Any], existing_items: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    intake_payload = governed_intake_payload(payload)
    intake = execute_dib_module_adapter(
        "module.data_intake",
        {
            "intake_payload": intake_payload,
            "existing_items": list(existing_items or []),
        },
    )
    return intake | {
        "governance_id": DIB_INTAKE_ITEM_GOVERNANCE_ID,
        "supplier_quote_text_intake": bool(payload.get("supplier_quote_text")),
        "template_registry_ui_ready": True,
        "customer_item_decision_ready": True,
        "external_fetch_enabled": False,
        "ai_provider_enabled": False,
        "finance_wiring_enabled": False,
        "snapshot_wiring_enabled": False,
    }


def apply_governed_item_decision(item: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:
    _reject_forbidden({"item": item, "decision": decision})
    result = execute_dib_module_adapter("module.customer_item_decision", {"item": dict(item), "decision": dict(decision)})
    return result | {
        "governance_id": DIB_INTAKE_ITEM_GOVERNANCE_ID,
        "customer_item_decision_workflow": True,
        "external_fetch_enabled": False,
        "ai_provider_enabled": False,
        "finance_wiring_enabled": False,
        "snapshot_wiring_enabled": False,
    }


def intake_item_governance_status() -> dict[str, Any]:
    return {
        "governance_id": DIB_INTAKE_ITEM_GOVERNANCE_ID,
        "status": DIB_INTAKE_ITEM_GOVERNANCE_STATUS,
        "source": DIB_INTAKE_ITEM_GOVERNANCE_SOURCE,
        "template_registry_ui_ready": True,
        "live_intake_surface_ready": True,
        "supplier_quote_text_intake_ready": True,
        "customer_item_decision_workflow_ready": True,
        "external_fetch_enabled": False,
        "ai_provider_enabled": False,
        "finance_wiring_enabled": False,
        "snapshot_wiring_enabled": False,
        "frozen_runtime_files_mutated": False,
    }
