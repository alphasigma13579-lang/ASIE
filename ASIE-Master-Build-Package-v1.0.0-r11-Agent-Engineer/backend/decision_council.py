from __future__ import annotations

from typing import Any


PERSONA_ORDER = [
    ("project_manager", "Execution Readiness Index"),
    ("business_advisor", "Commercial Acceptance Index"),
    ("technical_auditor", "Technical Robustness Index"),
    ("analyst_coach", "Transition Readiness Index"),
    ("resistance_test", "Pressure Survival Index"),
]

# ذ-1: persona scores are DERIVED from documented components with named
# benchmarks — never two fixed constants behind a boolean. Every persona
# output carries its formula and component values so a reviewer can defend
# "why this number" line by line. Benchmarks (SME credit-review practice):
FUNDING_SELF_COVERAGE_WEIGHT = 0.6       # share of execution score from equity coverage
OPERATING_MODEL_WEIGHT = 0.4             # share from having an operating model at all
BENCHMARK_CONTRIBUTION_MARGIN = 0.25     # healthy SME gross margin floor
BENCHMARK_DSCR = 1.2                     # minimum acceptable debt-service coverage
PAYBACK_EXCELLENT_MONTHS = 12.0          # payback at/below this scores 1.0
PAYBACK_UNACCEPTABLE_MONTHS = 36.0       # payback at/above this scores 0.0


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _persona_scores(
    finance: dict[str, Any],
    sector_status: str,
    sector_criteria_status: str,
    has_operating_model: bool,
    dscr: float | None,
    dscr_ready: bool,
) -> dict[str, dict[str, Any]]:
    baseline = finance["baseline"]
    mc = finance["monte_carlo"]

    startup_cost = float(baseline.get("startup_cost") or 0)
    funding_need = float(baseline.get("funding_need_after_equity") or 0)
    equity_coverage = _clamp01(1.0 - funding_need / startup_cost) if startup_cost > 0 else 0.0
    monthly_profit = float(baseline.get("monthly_profit") or 0)
    margin = float(baseline.get("contribution_margin") or 0)
    payback = baseline.get("payback_months")

    if dscr_ready:
        debt_coverage = 1.0 if dscr is None else _clamp01(float(dscr) / BENCHMARK_DSCR)
    else:
        debt_coverage = _clamp01(float(dscr) / BENCHMARK_DSCR) if dscr else 0.0
    criteria_score = {"supported": 1.0, "needs_evidence": 0.5}.get(sector_criteria_status, 0.0)
    if payback:
        payback_score = _clamp01(
            (PAYBACK_UNACCEPTABLE_MONTHS - float(payback))
            / (PAYBACK_UNACCEPTABLE_MONTHS - PAYBACK_EXCELLENT_MONTHS)
        )
    else:
        payback_score = 0.0

    return {
        "project_manager": {
            "value": FUNDING_SELF_COVERAGE_WEIGHT * equity_coverage
            + OPERATING_MODEL_WEIGHT * (1.0 if has_operating_model else 0.0),
            "formula": f"{FUNDING_SELF_COVERAGE_WEIGHT}*equity_coverage + {OPERATING_MODEL_WEIGHT}*has_operating_model",
            "components": {
                "equity_coverage": round(equity_coverage, 4),
                "has_operating_model": has_operating_model,
            },
        },
        "business_advisor": {
            "value": 0.3 * (1.0 if monthly_profit > 0 else 0.0)
            + 0.3 * _clamp01(margin / BENCHMARK_CONTRIBUTION_MARGIN)
            + 0.2 * debt_coverage
            + 0.2 * (1.0 if sector_status == "ready" else 0.0),
            "formula": f"0.3*profitable + 0.3*min(margin/{BENCHMARK_CONTRIBUTION_MARGIN},1) + 0.2*min(dscr/{BENCHMARK_DSCR},1) + 0.2*sector_ready",
            "components": {
                "profitable": monthly_profit > 0,
                "margin": round(margin, 4),
                "debt_coverage": round(debt_coverage, 4),
                "sector_ready": sector_status == "ready",
            },
        },
        "technical_auditor": {
            "value": 0.4 * (1.0 if finance["sensitivity"] else 0.0)
            + 0.4 * (1.0 if finance.get("operational_sensitivity") else 0.0)
            + 0.2 * criteria_score,
            "formula": "0.4*has_sensitivity + 0.4*has_operational_sensitivity + 0.2*sector_criteria_score",
            "components": {
                "has_sensitivity": bool(finance["sensitivity"]),
                "has_operational_sensitivity": bool(finance.get("operational_sensitivity")),
                "sector_criteria_score": criteria_score,
            },
        },
        "analyst_coach": {
            "value": payback_score,
            "formula": f"clamp(({PAYBACK_UNACCEPTABLE_MONTHS}-payback)/({PAYBACK_UNACCEPTABLE_MONTHS}-{PAYBACK_EXCELLENT_MONTHS}),0,1)",
            "components": {"payback_months": payback, "payback_score": round(payback_score, 4)},
        },
        "resistance_test": {
            "value": float(mc["p_pass"])
            if mc["status"] == "ready" and mc["p_pass"] is not None and dscr_ready
            else 0.0,
            "formula": "mc.p_pass when monte_carlo ready and dscr_ready else 0",
            "components": {"mc_status": mc["status"], "p_pass": mc.get("p_pass"), "dscr_ready": dscr_ready},
        },
    }


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
    dscr_ready = debt_profile.get("status") == "ready" and (dscr is None or dscr >= BENCHMARK_DSCR)
    scores = _persona_scores(
        finance, sector_status, sector_criteria_status, has_operating_model, dscr, dscr_ready
    )
    personas = [
        persona_output(
            persona_id,
            metric,
            round(scores[persona_id]["value"], 2),
            "ready",
            f"isolated_input:{persona_id}",
            "Deterministic local evaluator; reads allowed finance/readiness/sector envelopes only.",
            formula=scores[persona_id]["formula"],
            components=scores[persona_id]["components"],
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
    formula: str | None = None,
    components: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "persona_id": persona_id,
        "metric": metric,
        "value": value,
        "status": status,
        "evidence_refs": ["assumption:local-user-inputs-v1"] if value is not None else [],
        "note": note,
        "input_scope": input_scope,
        "formula": formula,
        "components": components or {},
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
