# BETA-PKG-03 — Live Intelligence Product Wiring

Date: 2026-07-27  
Status: implementation package

## 1. Purpose

Connect the governed provider foundation admitted in LIVE-INTEL-001 and the Vision 2030 knowledge synchronization admitted in LIVE-INTEL-002 to a product-facing intelligence service without bypassing evidence review, Finance ownership, Snapshot Assembly, or the AAS Runtime Freeze.

## 2. Canonical flow

```text
User query and project location
→ Live Intelligence Product Service
→ Tavily source candidates
→ Google Maps location/place context
→ Pinecone Vision 2030 retrieval
→ Human evidence review
→ Approved narrative context
→ DeepSeek narrative explanation
```

The provider layer does not write controlled Finance inputs and does not assemble a Snapshot.

## 3. Added implementation

- `backend/live_intelligence_product.py`
- `src/LiveIntelligenceWorkspace.tsx`
- `tests/test_live_intelligence_product.py`
- `tests/test_beta_pkg_03_guardrails.py`

## 4. Provider responsibilities

| Provider | Product responsibility | Admission state |
|---|---|---|
| Tavily | Discover web sources and summaries | Evidence candidate; review required |
| Google Maps Platform | Resolve location and nearby place context | Display/context only under persistence policy |
| Pinecone | Retrieve approved Vision 2030 chunks | Retrieval result; evidence validation required |
| DeepSeek | Explain approved evidence | Narrative only; human review pending |

## 5. Product contracts

### `live.intelligence.provider.status.v1`

Exposes presence-only provider configuration and network policy state. It never exposes secret values.

### `live.intelligence.preflight.v1`

Runs controlled provider checks when external fetch is enabled. DeepSeek is not called with an arbitrary test prompt; its connectivity is exercised only through an approved prompt template.

### `live.intelligence.context.v1`

Collects source candidates, places, governed public-economic evidence, failures, and a deterministic context hash. The public evidence is exposed both as the complete `public_evidence_context` contract and as backward-compatible `knowledge_hits` rows carrying `review_status: review_required`. Each evidence row includes its publisher, source URL, retrieval and freshness dates, geography, sector, unit, confidence, and lineage reference.

The response keeps `public_evidence_context.as_of` for freshness disclosure, but excludes that volatile clock field alone from `context_hash`. Evidence, gaps, status, and every other result field remain hash-bound, so identical evidence yields the same integrity marker while material readiness changes still change it. The contract declares:

```json
{
  "human_review_required": true,
  "eligible_for_controlled_assumptions": false,
  "controlled_numbers": [],
  "finance_mutated": false,
  "snapshot_mutated": false
}
```

### `live.intelligence.narrative.v1`

Permits DeepSeek narration only after the context has both:

- `review_status = approved`
- `eligible_for_narrative = true`

The response remains `human_review_status = required_pending`.

## 6. User-interface disclosure

The Arabic RTL workspace displays:

- provider status: disabled, configured, missing secret, live, or failed;
- a clear notice when external fetch is disabled;
- source links marked as requiring review;
- place-result counts and public-economic evidence cards with source, freshness, geography, sector, unit, and confidence;
- provider failures without exposing credentials;
- an explicit statement that results are not automatically used as financial values or final decisions.

## 7. Boundaries

This package does not modify:

- AAS Runtime Freeze files;
- Finance calculations;
- Approved Input Manifest rules;
- ProjectRunWorkflow order;
- Snapshot Assembly;
- Decision Council logic;
- authentication or tenant isolation;
- provider API keys or GitHub secrets.

## 8. Deferred work

- expose the service through authenticated local API routes;
- persist evidence-review decisions in the Evidence Ledger;
- integrate the workspace into the main user journey after App modularization;
- execute production provider preflight after secrets are configured;
- admit reviewed context into designated intelligence modules through approved contracts.

## 9. Acceptance criteria

- frontend build passes;
- backend compiles;
- all Python tests pass;
- no direct Finance or Snapshot import exists in the service;
- unreviewed context cannot invoke DeepSeek narration;
- all externally acquired results remain review-required by default;
- provider and error status is visible without secret disclosure.
