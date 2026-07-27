from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from backend.contracts import new_id, now_iso
from backend.dib_runtime import FINANCE_REQUIRED_KEYS, build_dynamic_input_blueprint


class ProductAIInterviewError(RuntimeError):
    pass


INTERVIEW_CONTRACT_ID = "product.ai.interview.v2"
QUESTION_REGISTRY_ID = "question.registry.product-interview.v1"
ALLOWED_ACTIONS = {"answer", "skip", "confirm", "edit", "reject"}
ALLOWED_SECTORS = {"food_service", "retail", "services", "manufacturing", "general"}


BASE_QUESTIONS: tuple[dict[str, Any], ...] = (
    {
        "question_id": "q.location",
        "field": "location",
        "label_ar": "حدد موقع المشروع على الخريطة",
        "kind": "location",
        "required": True,
        "phase": "site_first",
    },
    {
        "question_id": "q.idea",
        "field": "idea_summary",
        "label_ar": "ما فكرة المشروع؟",
        "kind": "short_text",
        "required": True,
        "phase": "project_identity",
    },
    {
        "question_id": "q.sector",
        "field": "sector",
        "label_ar": "ما القطاع الأقرب للمشروع؟",
        "kind": "single_choice",
        "required": True,
        "phase": "project_identity",
        "choices": sorted(ALLOWED_SECTORS),
    },
    {
        "question_id": "q.geographic_scope",
        "field": "geographic_scope",
        "label_ar": "ما نطاق السوق المستهدف؟",
        "kind": "single_choice",
        "required": True,
        "phase": "market_scope",
        "choices": ["neighborhood", "city", "region", "saudi_arabia", "gcc"],
    },
    {
        "question_id": "q.capital",
        "field": "capital_available",
        "label_ar": "ما رأس المال المتاح بالريال؟",
        "kind": "money_or_unknown",
        "required": True,
        "phase": "finance_context",
    },
    {
        "question_id": "q.data_method",
        "field": "data_method",
        "label_ar": "كيف ستوفر بيانات المشروع؟",
        "kind": "single_choice",
        "required": True,
        "phase": "data_intake",
        "choices": ["manual", "csv", "xlsx", "pdf", "no_data_sanad"],
    },
)


SECTOR_QUESTIONS: dict[str, tuple[dict[str, Any], ...]] = {
    "food_service": (
        {"question_id": "q.food.service_model", "field": "service_model", "label_ar": "ما نموذج الخدمة؟", "kind": "multi_choice", "required": True, "choices": ["dine_in", "takeaway", "delivery"]},
        {"question_id": "q.food.equipment", "field": "equipment", "label_ar": "راجع المعدات الأساسية المقترحة", "kind": "confirm_list", "required": True},
        {"question_id": "q.food.seats", "field": "seat_count", "label_ar": "كم عدد المقاعد المتوقع؟", "kind": "number_or_unknown", "required": False},
    ),
    "retail": (
        {"question_id": "q.retail.channel", "field": "sales_channel", "label_ar": "ما قناة البيع؟", "kind": "multi_choice", "required": True, "choices": ["store", "online", "hybrid"]},
        {"question_id": "q.retail.inventory", "field": "inventory_scope", "label_ar": "حدد نطاق المخزون الأولي", "kind": "single_choice", "required": True, "choices": ["small", "medium", "large", "unknown"]},
    ),
    "services": (
        {"question_id": "q.services.delivery", "field": "delivery_model", "label_ar": "كيف تقدم الخدمة؟", "kind": "single_choice", "required": True, "choices": ["onsite", "remote", "hybrid"]},
        {"question_id": "q.services.team", "field": "team_roles", "label_ar": "راجع الأدوار الوظيفية اللازمة", "kind": "confirm_list", "required": True},
    ),
    "manufacturing": (
        {"question_id": "q.manufacturing.capacity", "field": "capacity_band", "label_ar": "ما نطاق الطاقة الإنتاجية؟", "kind": "single_choice", "required": True, "choices": ["pilot", "small", "medium", "unknown"]},
        {"question_id": "q.manufacturing.equipment", "field": "equipment", "label_ar": "راجع خطوط ومعدات الإنتاج", "kind": "confirm_list", "required": True},
    ),
    "general": (
        {"question_id": "q.general.model", "field": "operating_model", "label_ar": "صف نموذج التشغيل الأقرب", "kind": "short_text", "required": True},
    ),
}


NEEDS_CATALOG: dict[str, tuple[dict[str, Any], ...]] = {
    "food_service": (
        {"need_id": "need.location", "label_ar": "موقع مناسب", "category": "site"},
        {"need_id": "need.kitchen", "label_ar": "معدات وتجهيزات المطبخ", "category": "equipment"},
        {"need_id": "need.staff", "label_ar": "طاقم تشغيل", "category": "workforce"},
        {"need_id": "need.licenses", "label_ar": "التراخيص البلدية والغذائية", "category": "licenses"},
    ),
    "retail": (
        {"need_id": "need.location", "label_ar": "موقع أو قناة بيع", "category": "site"},
        {"need_id": "need.inventory", "label_ar": "مخزون افتتاحي", "category": "inventory"},
        {"need_id": "need.pos", "label_ar": "نظام نقاط بيع", "category": "technology"},
    ),
    "services": (
        {"need_id": "need.team", "label_ar": "فريق تقديم الخدمة", "category": "workforce"},
        {"need_id": "need.tools", "label_ar": "أدوات ومنصات التشغيل", "category": "technology"},
    ),
    "manufacturing": (
        {"need_id": "need.facility", "label_ar": "منشأة إنتاج", "category": "site"},
        {"need_id": "need.line", "label_ar": "خط ومعدات إنتاج", "category": "equipment"},
        {"need_id": "need.quality", "label_ar": "ضبط جودة", "category": "quality"},
    ),
    "general": (
        {"need_id": "need.location", "label_ar": "موقع أو قناة تشغيل", "category": "site"},
        {"need_id": "need.team", "label_ar": "فريق أساسي", "category": "workforce"},
    ),
}


def _digest(value: Mapping[str, Any]) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def question_registry(sector: str = "general") -> dict[str, Any]:
    normalized = sector if sector in ALLOWED_SECTORS else "general"
    questions = [dict(row) for row in BASE_QUESTIONS + SECTOR_QUESTIONS[normalized]]
    return {
        "contract_id": "question.registry.v1",
        "registry_id": QUESTION_REGISTRY_ID,
        "sector": normalized,
        "questions": questions,
        "question_count": len(questions),
        "location_first": questions[0]["field"] == "location",
    }


def start_interview(*, organization_id: str, project_id: str, idea_summary: str = "", sector: str = "general") -> dict[str, Any]:
    if not organization_id.strip() or not project_id.strip():
        raise ProductAIInterviewError("organization_and_project_required")
    normalized_sector = sector if sector in ALLOWED_SECTORS else "general"
    registry = question_registry(normalized_sector)
    session = {
        "contract_id": INTERVIEW_CONTRACT_ID,
        "interview_id": new_id("product_interview"),
        "organization_id": organization_id,
        "project_id": project_id,
        "sector": normalized_sector,
        "idea_summary": idea_summary.strip(),
        "status": "in_progress",
        "answers": {},
        "question_registry_id": registry["registry_id"],
        "questions": registry["questions"],
        "current_question_id": registry["questions"][0]["question_id"],
        "ai_provider_enabled": False,
        "ai_owns_numbers": False,
        "external_fetch_enabled": False,
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    session["session_digest"] = _digest(session)
    return session


def apply_answer(session: Mapping[str, Any], *, question_id: str, action: str, value: Any = None) -> dict[str, Any]:
    if action not in ALLOWED_ACTIONS:
        raise ProductAIInterviewError("invalid_interview_action")
    questions = [dict(row) for row in session.get("questions", [])]
    question = next((row for row in questions if row.get("question_id") == question_id), None)
    if question is None:
        raise ProductAIInterviewError("unknown_interview_question")
    answers = dict(session.get("answers") or {})
    if action == "reject":
        answers[question_id] = {"status": "rejected", "value": None, "updated_at": now_iso()}
    elif action == "skip":
        if question.get("required"):
            raise ProductAIInterviewError("required_question_cannot_be_skipped")
        answers[question_id] = {"status": "skipped", "value": None, "updated_at": now_iso()}
    else:
        if value in (None, "") and question.get("required"):
            raise ProductAIInterviewError("required_answer_missing")
        answers[question_id] = {"status": "answered", "value": value, "updated_at": now_iso(), "action": action}

    unresolved_required = [
        row for row in questions
        if row.get("required") and answers.get(row["question_id"], {}).get("status") != "answered"
    ]
    next_question = unresolved_required[0]["question_id"] if unresolved_required else None
    updated = dict(session)
    updated.update(
        {
            "answers": answers,
            "status": "ready_for_review" if not unresolved_required else "in_progress",
            "current_question_id": next_question,
            "unresolved_required_count": len(unresolved_required),
            "updated_at": now_iso(),
        }
    )
    updated["session_digest"] = _digest(updated)
    return updated


def propose_needs(session: Mapping[str, Any]) -> dict[str, Any]:
    if session.get("status") not in {"ready_for_review", "approved"}:
        raise ProductAIInterviewError("interview_not_ready_for_needs")
    sector = str(session.get("sector") or "general")
    needs = []
    for row in NEEDS_CATALOG.get(sector, NEEDS_CATALOG["general"]):
        need = dict(row)
        need.update({"status": "suggested", "source_type": "governed_catalog", "review_required": True})
        needs.append(need)
    return {
        "contract_id": "product.needs.proposal.v1",
        "proposal_id": new_id("needs_proposal"),
        "interview_id": session["interview_id"],
        "sector": sector,
        "needs": needs,
        "ai_generated_numbers": False,
        "review_required": True,
        "created_at": now_iso(),
    }


def review_needs(proposal: Mapping[str, Any], decisions: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    decision_map = {str(row.get("need_id")): dict(row) for row in decisions}
    reviewed = []
    blockers = []
    for raw in proposal.get("needs", []):
        need = dict(raw)
        decision = decision_map.get(str(need.get("need_id")), {})
        action = str(decision.get("action") or "unresolved")
        if action not in {"accept", "edit", "reject"}:
            blockers.append({"code": "UNRESOLVED_NEED", "need_id": need.get("need_id")})
            need["status"] = "unresolved"
        elif action == "reject":
            need["status"] = "rejected"
        else:
            need.update(dict(decision.get("changes") or {}))
            need["status"] = "accepted"
        reviewed.append(need)
    return {
        "contract_id": "customer.need.decision.v1",
        "proposal_id": proposal.get("proposal_id"),
        "status": "approved" if not blockers else "blocked",
        "needs": reviewed,
        "blockers": blockers,
        "reviewed_at": now_iso(),
    }


def interview_to_dib(session: Mapping[str, Any], reviewed_needs: Mapping[str, Any]) -> dict[str, Any]:
    if session.get("status") not in {"ready_for_review", "approved"}:
        raise ProductAIInterviewError("interview_not_ready_for_dib")
    if reviewed_needs.get("status") != "approved":
        raise ProductAIInterviewError("needs_review_not_approved")
    answers = session.get("answers") or {}
    answer_by_field: dict[str, Any] = {}
    for question in session.get("questions", []):
        answer = answers.get(question.get("question_id"), {})
        if answer.get("status") == "answered":
            answer_by_field[str(question.get("field"))] = answer.get("value")
    profile = {
        "project_id": session["project_id"],
        "organization_id": session["organization_id"],
        "sector": session.get("sector"),
        "idea_summary": answer_by_field.get("idea_summary") or session.get("idea_summary"),
        "location": answer_by_field.get("location"),
        "geographic_scope": answer_by_field.get("geographic_scope"),
        "data_method": answer_by_field.get("data_method"),
    }
    items = []
    capital = answer_by_field.get("capital_available")
    if isinstance(capital, (int, float)):
        items.append(
            {
                "item_id": new_id("dib_item"),
                "input_key": "capital_available",
                "label": "رأس المال المتاح",
                "category": "finance_assumption",
                "value": capital,
                "unit": "SAR",
                "value_state": "USER_PROVIDED",
                "value_source": "product_ai_interview",
                "source_type": "product_ai_interview",
                "confidence": 0.8,
                "evidence_refs": [f"interview:{session['interview_id']}:q.capital"],
                "review_status": "approved",
                "required": False,
                "reason": "user_answer",
                "revision": 1,
            }
        )
    for key in FINANCE_REQUIRED_KEYS:
        items.append(
            {
                "item_id": new_id("dib_item"),
                "input_key": key,
                "label": key.replace("_", " "),
                "category": "finance_assumption",
                "value": None,
                "unit": "unit" if key == "monthly_units" else "SAR",
                "value_state": "UNKNOWN",
                "value_source": "product_ai_interview",
                "source_type": "product_ai_interview",
                "confidence": 0.0,
                "evidence_refs": [f"interview:{session['interview_id']}"],
                "review_status": "draft",
                "required": True,
                "reason": "AI_must_not_generate_controlled_number",
                "revision": 1,
            }
        )
    blueprint = build_dynamic_input_blueprint(profile, items, source="product_ai_interview")
    blueprint["interview_lineage"] = {
        "interview_id": session["interview_id"],
        "session_digest": session.get("session_digest"),
        "needs_proposal_id": reviewed_needs.get("proposal_id"),
        "controlled_numbers_generated_by_ai": False,
    }
    blueprint["approved_needs"] = [row for row in reviewed_needs.get("needs", []) if row.get("status") == "accepted"]
    return blueprint
