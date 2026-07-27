from __future__ import annotations

import pytest

from backend.product_ai_interview import (
    ProductAIInterviewError,
    apply_answer,
    interview_to_dib,
    propose_needs,
    question_registry,
    review_needs,
    start_interview,
)


def _complete_food_interview():
    session = start_interview(
        organization_id="org-1",
        project_id="project-1",
        idea_summary="محل شاورما",
        sector="food_service",
    )
    answers = {
        "q.location": {"lat": 24.7136, "lng": 46.6753},
        "q.idea": "محل شاورما للطلبات الخارجية والتوصيل",
        "q.sector": "food_service",
        "q.geographic_scope": "city",
        "q.capital": 250000,
        "q.data_method": "no_data_sanad",
        "q.food.service_model": ["takeaway", "delivery"],
        "q.food.equipment": ["shawarma_grill", "refrigerator", "prep_table"],
    }
    for question_id, value in answers.items():
        session = apply_answer(session, question_id=question_id, action="answer", value=value)
    session = apply_answer(session, question_id="q.food.seats", action="skip")
    return session


def test_registry_is_location_first_and_sector_aware():
    registry = question_registry("food_service")
    assert registry["location_first"] is True
    assert registry["questions"][0]["field"] == "location"
    assert any(row["question_id"] == "q.food.equipment" for row in registry["questions"])


def test_required_question_cannot_be_skipped():
    session = start_interview(organization_id="org", project_id="project")
    with pytest.raises(ProductAIInterviewError, match="required_question_cannot_be_skipped"):
        apply_answer(session, question_id="q.location", action="skip")


def test_complete_interview_reaches_review_state():
    session = _complete_food_interview()
    assert session["status"] == "ready_for_review"
    assert session["unresolved_required_count"] == 0
    assert session["ai_owns_numbers"] is False


def test_needs_require_explicit_review():
    session = _complete_food_interview()
    proposal = propose_needs(session)
    blocked = review_needs(proposal, [])
    assert blocked["status"] == "blocked"
    assert blocked["blockers"]

    decisions = [{"need_id": row["need_id"], "action": "accept"} for row in proposal["needs"]]
    approved = review_needs(proposal, decisions)
    assert approved["status"] == "approved"
    assert all(row["status"] == "accepted" for row in approved["needs"])


def test_interview_handoff_creates_dib_without_ai_finance_numbers():
    session = _complete_food_interview()
    proposal = propose_needs(session)
    reviewed = review_needs(
        proposal,
        [{"need_id": row["need_id"], "action": "accept"} for row in proposal["needs"]],
    )
    blueprint = interview_to_dib(session, reviewed)
    assert blueprint["contract_id"] == "dynamic.input.blueprint.v1"
    assert blueprint["source"] == "product_ai_interview"
    assert blueprint["project_profile"]["location"] == {"lat": 24.7136, "lng": 46.6753}
    assert blueprint["interview_lineage"]["controlled_numbers_generated_by_ai"] is False

    by_key = {row["input_key"]: row for row in blueprint["items"]}
    assert by_key["capital_available"]["value"] == 250000
    for key in ("startup_cost", "monthly_fixed_cost", "unit_price", "variable_cost", "monthly_units"):
        assert by_key[key]["value"] is None
        assert by_key[key]["value_state"] == "UNKNOWN"
        assert by_key[key]["reason"] == "AI_must_not_generate_controlled_number"


def test_unreviewed_needs_cannot_reach_dib():
    session = _complete_food_interview()
    proposal = propose_needs(session)
    with pytest.raises(ProductAIInterviewError, match="needs_review_not_approved"):
        interview_to_dib(session, review_needs(proposal, []))
