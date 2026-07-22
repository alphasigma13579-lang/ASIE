# Official Strategy Reference Algorithms

## خوارزميات المراجع الاستراتيجية الرسمية

**Owner:** Market Intelligence + Audit / Observability with authorized human reviewers  
**Rule:** Source pages are reference-only. Deterministic controls prevent retrieval and unauthorized propagation. AI writes only from approved ASIE-authored cards.

## REF-ALG-01 Reference Registration and Canonicalization

Purpose: register an official reference without retrieving or storing its content.

Inputs:

- Official URL supplied by an authorized curator.
- Publisher and official Arabic/English title.
- Reference purpose and source language.

Steps:

1. Normalize scheme and hostname without making a network request.
2. Remove display-only fragments such as a trailing `#?`.
3. Match the canonical URL against the approved strategy-reference allowlist.
4. Deduplicate by canonical URL and reference ID.
5. Set `access_class=reference_only` and `purpose=inspiration_and_alignment_only`.
6. Record curator, review date, status, and next review.
7. Reject any payload containing target content, HTML, screenshot, image, logo, or embedding.

The duplicate SDAIA National Strategy for Data and AI URL resolves to one canonical record.

## REF-ALG-02 Original Synthesis and Non-Copying Guard

Purpose: ensure an ASIE alignment card is independently written and does not contain source material.

Inputs:

- Curator-authored ASIE themes, questions, and interpretation.
- Source metadata only.
- Originality and accuracy review decisions.

Checks:

1. No source-content fields, attachments, screenshots, HTML, or embeddings exist.
2. Text is organized around an ASIE product/project question and implementation decision.
3. Official names and titles are accurate and attributed.
4. No quotation is present except a separately reviewed unavoidable official title or identifier.
5. No copied list structure, branded taxonomy, diagram, page hierarchy, or reconstructed search snippet is present.
6. Human reviewers approve accuracy, originality, attribution, and non-endorsement.
7. Card version and expiry are set.

Result: `approved`, `rejected`, or `pending_human_review`. AI cannot create an approved decision.

## REF-ALG-03 Strategy Alignment Pack Builder

Purpose: produce useful national-alignment guidance from approved ASIE-authored cards.

Steps:

1. Receive project context and requested alignment themes through `market.strategy.reference.v1`.
2. Load only approved, unexpired card fields.
3. Select relevant original ASIE questions and interpretations.
4. Produce project-specific analysis in new wording.
5. Separate source metadata, ASIE interpretation, project question, recommendation, and formal-control gap.
6. Attach official URL, publisher, card review date, and language.
7. Add `ASIE interpretation; not government approval, certification, or endorsement`.
8. Exclude any expired, withdrawn, unreviewed, or copied card.

The pack cannot enter deterministic Finance inputs as a numeric authority.

## REF-ALG-04 Strategy vs Formal Compliance Claim Guard

Purpose: prevent orientation pages from being used as laws, regulations, standards, or control evidence.

Rules:

- NCA National Cybersecurity Strategy themes do not prove NCNICC, ECC, DCC, CCC, CSCC, or sector-control compliance.
- DGA digital-transformation and sustainable-development pages do not prove DGA certification or regulatory compliance.
- GOV.SA e-participation does not authorize collecting consultations, submissions, metrics, or participant data.
- SDAIA terms and strategy pages do not prove SDAIA approval, certification, or measurement of ASIE.

Decision:

```text
IF claim_type is legal, regulatory, control, certification, or official measurement
AND evidence is only a strategy/overview/reference page
THEN reject claim and request the exact formal instrument.
```

## REF-ALG-05 Reference Expiry, Withdrawal, and Unavailability

Purpose: stop stale or unavailable references from silently authorizing published alignment copy.

Triggers:

- Review date reached.
- Official title, URL, publisher, or strategy version changes.
- Curator or reviewer withdraws the card.
- Source becomes unavailable or returns a technical rejection during manual review.
- Accuracy, originality, or endorsement concern is raised.

Actions:

1. Set card to `expired`, `withdrawn`, or `review_required`.
2. Block new AI, Project Wizard, and Reports use.
3. Identify previously published ASIE outputs using the card.
4. Notify Content/Governance and Legal reviewers where applicable.
5. Do not use crawler, mirror, cached page, search snippets, or third-party retrieval as a fallback.
6. Require a new human review and new card version before reactivation.

