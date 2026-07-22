from __future__ import annotations

from typing import Any


PERSONA_ORDER = [
    ("project_manager", "Execution Readiness Index"),
    ("business_advisor", "Commercial Acceptance Index"),
    ("technical_auditor", "Technical Robustness Index"),
    ("analyst_coach", "Transition Readiness Index"),
    ("resistance_test", "Pressure Survival Index"),
]


def evaluate_decision_council(
    finance: dict[str, Any],
    blockers: list[dict[str, str]],
    readiness_gates: dict[str, Any] | None = None,
    sector_intelligence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if finance["status"] != "ready":
        personas = [
            persona_output(persona_id, metric, None, "needs_input", "project_envelope_only", "ينتظر مدخلات مالية صالحة.")
            for persona_id, metric in PERSONA_ORDER
        ]
        verdict = {
            "sovereign_verdict": "BLOCKED_NOT_READY",
            "reason": "لا يمكن إصدار حكم سيادي حتى تكتمل المدخلات الإلزامية.",
            "critical_truth_visible": True,
            "determined_by": "Decision Council deterministic gates",
            "no_vote": True,
            "advisory_consensus_visible_as_verdict": False,
        }
        return result(personas, verdict)

    baseline = finance["baseline"]
    mc = finance["monte_carlo"]
    operating_model = finance.get("operating_model") or {}
    debt_profile = finance.get("debt_service_profile") or {}
    sector_status = (sector_intelligence or {}).get("status", "needs_input")
    sector_criteria_status = ((sector_intelligence or {}).get("sector_criteria") or {}).get("status", "needs_evidence")
    has_operating_model = bool(operating_model.get("monthly_units"))
    dscr = debt_profile.get("dscr")
    dscr_ready = debt_profile.get("status") == "ready" and (dscr is None or dscr >= 1.2)
    scores = {
        "project_manager": 0.74 if baseline["funding_need_after_equity"] <= 250000 and has_operating_model else 0.50,
        "business_advisor": 0.72
        if baseline["monthly_profit"] > 0 and baseline["contribution_margin"] > 0.25 and dscr_ready and sector_status == "ready"
        else 0.42,
        "technical_auditor": 0.68
        if finance["sensitivity"] and finance.get("operational_sensitivity") and sector_criteria_status in {"supported", "needs_evidence"}
        else 0.46,
        "analyst_coach": 0.68 if baseline["payback_months"] and baseline["payback_months"] <= 36 else 0.48,
        "resistance_test": mc["p_pass"] if mc["status"] == "ready" and mc["p_pass"] is not None and dscr_ready else 0.0,
    }
    personas = [
        persona_output(
            persona_id,
            metric,
            round(scores[persona_id], 2),
            "ready",
            f"isolated_input:{persona_id}",
            "Deterministic local evaluator; reads allowed finance/readiness/sector envelopes only.",
        )
        for persona_id, metric in PERSONA_ORDER
    ]

    blocked_gates = [
        gate["gate_id"]
        for gate in (readiness_gates or {}).get("gates", [])
        if gate.get("status") == "blocked"
    ]
    if any(blocker["severity"] == "critical" for blocker in blockers):
        verdict_code = "BLOCKED_NOT_READY"
        reason = "بوابة حتمية حرجة تمنع الحكم النهائي."
    elif blocked_gates:
        verdict_code = "BLOCKED_NOT_READY"
        reason = "بوابات الجاهزية الحتمية تمنع الانتقال للمرحلة التالية: " + ", ".join(blocked_gates)
    elif mc["status"] != "ready":
        verdict_code = "BLOCKED_NOT_READY"
        reason = "Monte Carlo غير جاهز، لذلك لا يصدر حكم سيادي."
    elif debt_profile.get("status") == "not_ready":
        verdict_code = "BLOCKED_NOT_READY"
        reason = "خدمة الدين غير جاهزة لأن شروط التمويل ناقصة أو غير صالحة."
    elif mc["p_pass"] < 0.45 or baseline["npv"] < 0 or (dscr is not None and dscr < 1.0):
        verdict_code = "REVISE_AND_REASSESS"
        reason = "احتمال اجتياز بوابات الجدوى أو صافي القيمة الحالية أو تغطية خدمة الدين لا يدعم التقدم الآن."
    else:
        verdict_code = "PRELIMINARY_ONLY"
        reason = "تشغيل محلي حتمي متاح، لكن الأدلة المفتوحة الرسمية لم تُفعّل بعد."

    verdict = {
        "sovereign_verdict": verdict_code,
        "reason": reason,
        "critical_truth_visible": True,
        "determined_by": "Decision Council deterministic gates",
        "no_vote": True,
        "advisory_consensus_visible_as_verdict": False,
    }
    return result(personas, verdict)


def persona_output(
    persona_id: str,
    metric: str,
    value: float | None,
    status: str,
    input_scope: str,
    note: str,
) -> dict[str, Any]:
    return {
        "persona_id": persona_id,
        "metric": metric,
        "value": value,
        "status": status,
        "evidence_refs": ["assumption:local-user-inputs-v1"] if value is not None else [],
        "note": note,
        "input_scope": input_scope,
        "permitted_input_refs": ["finance.result.v1", "finance.mcmc.result.v1", "sector.intelligence.v1"],
    }


def result(personas: list[dict[str, Any]], verdict: dict[str, Any]) -> dict[str, Any]:
    return {
        "protocol_id": "FSDP-v1-local",
        "isolation_order": [persona_id for persona_id, _metric in PERSONA_ORDER],
        "personas": personas,
        "verdict": verdict,
        "no_vote": True,
    }
