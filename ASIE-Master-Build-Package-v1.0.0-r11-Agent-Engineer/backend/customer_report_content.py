"""Localized, read-only business content shared by funder document formats."""
from __future__ import annotations

import math
from typing import Any

from backend.customer_presentation import business_text, normalize_locale, safe_narrative, status_text

_LABELS = {
    "summary": ("الملخص التنفيذي", "Executive summary"),
    "decision": ("نتيجة التقييم", "Assessment result"),
    "reason": ("سبب النتيجة", "Reason for the result"),
    "metrics": ("المؤشرات الرئيسية", "Key metrics"),
    "metric": ("المؤشر", "Metric"),
    "value": ("القيمة المحفوظة", "Saved value"),
    "unit": ("الوحدة", "Unit"),
    "status": ("الحالة", "Status"),
    "risks": ("المخاطر والإجراءات المقترحة", "Risks and recommended actions"),
    "risk": ("الخطر", "Risk"),
    "severity": ("الأهمية", "Severity"),
    "action": ("الإجراء المقترح", "Recommended action"),
    "plan": ("خطوات التنفيذ", "Execution steps"),
    "phase": ("الخطوة", "Step"),
    "owner": ("المسؤول", "Owner"),
    "days": ("المدة بالأيام", "Duration in days"),
    "done": ("معيار الإتمام", "Completion criterion"),
    "empty": ("لم تتوفر معلومات محفوظة لهذا القسم بعد.", "No saved information is available for this section yet."),
}
_UNITS = {
    "sar": ("ريال سعودي", "Saudi riyal"),
    "sar/month": ("ريال سعودي شهريًا", "Saudi riyal per month"),
    "sar/year": ("ريال سعودي سنويًا", "Saudi riyal per year"),
    "month": ("شهر", "month"), "months": ("أشهر", "months"),
    "year": ("سنة", "year"), "years": ("سنوات", "years"),
    "unit": ("وحدة", "unit"), "units": ("وحدات", "units"),
    "count": ("عدد", "count"), "ratio": ("نسبة", "ratio"),
    "%": ("٪", "%"), "percent": ("٪", "%"),
    "probability": ("احتمال", "probability"), "days": ("أيام", "days"),
}


def report_label(key: str, locale: str) -> str:
    return _LABELS[key][normalize_locale(locale) == "en"]


def _number(value: Any) -> str:
    # Formatting only: do not infer, annualize, round, or recalculate a value.
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return "—"
    if isinstance(value, float) and not math.isfinite(value):
        return "—"
    return str(value)


def _rows(value: Any) -> list[dict[str, Any]]:
    return [row for row in value if isinstance(row, dict)] if isinstance(value, list) else []


def customer_report_groups(projection: dict[str, Any], locale: str = "ar") -> list[dict[str, Any]]:
    """Read existing section payloads without changing the persisted projection."""
    locale = normalize_locale(locale)
    sections = {row.get("section_id"): row for row in _rows(projection.get("sections"))}

    def payload(section_id: str) -> dict[str, Any]:
        value = sections.get(section_id, {}).get("payload")
        return value if isinstance(value, dict) else {}

    summary = payload("02-executive-summary")
    decision = summary.get("decision") or {}
    if not isinstance(decision, dict):
        decision = {}
    register = payload("12-general-risks").get("risk_register") or {}
    if not isinstance(register, dict):
        register = {}
    risks = _rows(register.get("top_risks")) or _rows(register.get("risks"))
    milestones = _rows(payload("09-timeline").get("milestones"))
    metric_rows = []
    for row in _rows(summary.get("kpis")):
        raw_unit = str(row.get("unit") or "").lower()
        pair = _UNITS.get(raw_unit)
        unit = pair[locale == "en"] if pair else "—"
        metric_rows.append([
            business_text(row.get("output_id"), locale), _number(row.get("value")),
            unit, status_text(row.get("status"), locale),
        ])

    groups = [
        ("summary", ["decision", "reason"], [[
            status_text(decision.get("sovereign_verdict"), locale),
            safe_narrative(decision.get("reason"), locale),
        ]]),
        ("metrics", ["metric", "value", "unit", "status"], metric_rows),
        ("risks", ["risk", "severity", "action"], [[
            business_text(row.get("trigger"), locale),
            status_text(row.get("severity"), locale),
            safe_narrative(row.get("mitigation"), locale),
        ] for row in risks]),
        ("plan", ["phase", "owner", "days", "done"], [[
            business_text(row.get("phase_id"), locale),
            business_text(row.get("owner_role"), locale),
            _number(row.get("estimated_duration_days")),
            " · ".join(business_text(item, locale) for item in row.get("exit_criteria", []) if isinstance(item, str))
            if isinstance(row.get("exit_criteria"), list) else "—",
        ] for row in milestones]),
    ]
    return [{
        "title": report_label(title, locale),
        "headers": [report_label(key, locale) for key in headers],
        "rows": rows,
        "empty": report_label("empty", locale),
    } for title, headers, rows in groups]
