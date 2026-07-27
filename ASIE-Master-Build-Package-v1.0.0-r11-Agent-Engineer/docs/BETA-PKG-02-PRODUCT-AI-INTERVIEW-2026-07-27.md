# BETA-PKG-02 — Product AI Interview

Date: 2026-07-27
Status: IMPLEMENTED IN PACKAGE / CI REQUIRED

## Purpose

Provide the governed first-entry path for a user who has only a project idea and does not yet possess complete project data.

The interview does not calculate Finance values and does not approve controlled assumptions. It captures context, proposes needs from governed registries, requires explicit customer review, and hands controlled candidates to the existing Dynamic Input Blueprint.

## Canonical flow

```text
Project idea
→ location-first interview
→ sector-aware Question Registry
→ required-answer gate
→ governed needs proposal
→ Accept / Edit / Reject review
→ DIB candidates
→ Approved Input Manifest
→ Controlled Finance Wiring
```

## Implemented files

- `backend/product_ai_interview.py`
- `src/ProductAIInterview.tsx`
- `tests/test_product_ai_interview.py`
- `tests/test_beta_pkg_02_guardrails.py`

## Question Registry

The registry begins with location and covers:

- project idea
- sector
- geographic scope
- available capital in SAR
- intended data intake method
- sector-specific operating questions

Initial governed sector profiles:

- Food Service
- Retail
- Services
- Manufacturing
- General

## Session states

- `in_progress`
- `ready_for_review`
- `approved`

Required questions cannot be skipped. Optional questions may be skipped explicitly.

## Needs proposal

Needs are proposed from a deterministic governed catalogue, not from an unconstrained provider response. Every need remains `review_required` until the user applies one of:

- Accept
- Edit
- Reject

Unresolved needs block DIB handoff.

## DIB handoff

The handoff creates `dynamic.input.blueprint.v1` through the existing DIB builder.

The user's declared capital may enter as `USER_PROVIDED`. Required Finance inputs remain `UNKNOWN` unless the user, reviewed dataset, or approved evidence supplies them.

The package explicitly records:

```json
{
  "ai_owns_numbers": false,
  "controlled_numbers_generated_by_ai": false
}
```

## UI

`ProductAIInterview.tsx` provides an Arabic RTL, click-first interview surface with:

- one-question-at-a-time flow
- controlled choices
- required/optional disclosure
- explicit completion review
- visible statement that Sanad does not approve Finance numbers for the user

The component is kept separate from the oversized `App.tsx` to avoid increasing frontend monolith coupling. Main-route API wiring remains part of integration work and must preserve this contract.

## Hard boundaries

This package does not modify:

- AAS Runtime Freeze
- Finance Engine calculations
- Approved Input Manifest rules
- Project Run Workflow
- Snapshot Assembly
- Decision Council
- provider activation or external network behavior
- authentication or tenant isolation

## Acceptance criteria

- location is the first question
- sector-specific questions are selected deterministically
- required questions cannot be skipped
- incomplete interview cannot generate needs
- needs cannot reach DIB before explicit review
- AI does not generate controlled Finance values
- user-provided capital retains interview lineage
- tests and full repository CI pass
