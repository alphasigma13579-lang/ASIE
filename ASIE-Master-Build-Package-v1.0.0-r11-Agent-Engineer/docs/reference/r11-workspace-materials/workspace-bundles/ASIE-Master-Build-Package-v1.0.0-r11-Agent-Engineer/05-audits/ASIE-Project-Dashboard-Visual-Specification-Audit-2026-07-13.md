# ASIE Project Dashboard Visual Specification Audit

## مراجعة مواصفة لوحة ذكاء المشروع

**Date:** 2026-07-13  
**Reviewed baseline:** Execution/Algorithm r13 and KIMI Master r6  
**Resulting candidate:** Execution/Algorithm r14 and KIMI Master r7  
**Scope:** 28 legacy-screen concepts, ASIE visual output routes, formulas, evidence lineage, AAS boundaries, security, bilingual UX, and KIMI implementation gates.

## Verdict

**Architecture decision:** Compliant with AAS v1.0.0 Frozen Baseline.  
**ACP required:** No.  
**Security decision:** Acceptable as a build specification after the listed guards.  
**Legal status:** This is a technical/governance review, not legal certification or government approval.

## Findings and Corrections

### High: Legacy scores could be mistaken for ASIE truth

The screenshots contain scores, percentages, amounts, company names, provider labels, competitors, dates, maps, and recommendations without current r13 lineage.

Correction:

- Classified all screenshots as functional/visual references only.
- Added `DASH-ALG-12` and `DASH-T27`.
- Production rejects copied legacy values, names, claims, maps, and wording.

### High: One confidence percentage could mislead users

The old interface mixes evidence confidence, scenario probability, sentiment, and decision confidence.

Correction:

- Separated evidence coverage, input quality, freshness, decision agreement, and simulation uncertainty.
- A composite value is explicitly `Evidence confidence index`, never probability of success.
- Named scenarios receive no probability unless MCMC produces it.

### High: Government-approval wording was not proven by r13

r13 contains ASIE deterministic algorithms and templates but no exact documentary registry proving an official government-issued feasibility, cost-benefit, charter, procurement, valuation, SWOT, BMC, or VPC form.

Correction:

- Added model-status taxonomy.
- `ASIE deterministic model` and `Strategic framework` are allowed.
- `Official form` requires issuer, exact form ID, version, scope, official source, and human review.
- `Government approved` is blocked without exact proof.

### High: Dashboard could become an accidental truth owner

Correction:

- Dashboard is defined as a composite project workspace only.
- Reports composes approved output IDs and never recalculates.
- No Dashboard Module, Layer, Controller, Bus, Heart, or direct Module call is allowed.
- Added explicit view, lineage, and run-comparison contracts.

### High: Investor and valuation outputs could become financial/legal promises

Correction:

- Funding, valuation, equity, dilution, runway, and negotiation outputs require deterministic inputs, methods, assumptions, downside case, and disclaimers.
- No guaranteed funding, return, valuation, or enforceable legal term.
- Investor-ready text is a draft requiring review.

### Medium: External-news sentiment could bypass strict source rules

Correction:

- External context is optional and unavailable by default.
- It requires an exact eligible source route under the active profile.
- Model sentiment is labeled inference and excluded from finance/readiness by default.
- Search snippets, crawlers, reference-only pages, and fallback scraping are blocked.

### Medium: Rich visuals lacked a single output schema

Correction:

- Added the universal output envelope.
- Every visible metric includes owner, contract, algorithm, version, type, unit, period, geography, scenario, evidence/assumptions, formula, confidence basis, status, timestamp, and audit reference.

### Medium: Report and dashboard could drift

Correction:

- Added `DASH-ALG-10` parity algorithm.
- Dashboard, PDF, presentation, and spreadsheet use identical output IDs for a frozen run.
- Export is blocked when raw values, units, periods, formula versions, or rounding policies differ.

## Route Coverage

| Route | Coverage |
| --- | --- |
| Executive Overview | Decision, readiness, confidence, blockers, next actions |
| Strategic Analysis | SWOT, PESTEL, Porter, BMC, VPC, cultural/national alignment |
| Market & Competition | Market boundaries, size, demand, competitors, map, prices, sources |
| Financial Feasibility | Inputs, CapEx/OpEx, forecast, margins, break-even, unit economics |
| Risks & Sensitivity | Risk layers, 5x5 matrix, sensitivity, resistance test |
| Scenarios & Simulation | Baseline/optimistic/downside/custom, MCMC configuration and bands |
| Decision Council | Validation, five personas, votes, consensus, dissent, conditions |
| Execution Plan | Recommendations, 30/60/90, milestones, KPI tree, operational risks |
| Investment Readiness | Funding need, use of funds, runway, valuation method, equity advisory |
| Evidence & Methodology | Sources, lineage, assumptions, models, runs, audit, disclaimers |
| Report | Frozen-run exports with bilingual parity |

## New Controls

- 12 dashboard algorithms: `DASH-ALG-01` through `DASH-ALG-12`.
- 23 algorithm-level negative/positive tests.
- 40 execution acceptance tests: `DASH-T01` through `DASH-T40`.
- 3 Socket Contracts for project view, lineage, and run comparison.
- 21 dashboard message types plus forbidden message patterns.
- 50 KIMI stop rules in the updated Master package.

## Bilingual and Visual Acceptance

- Arabic RTL and English LTR are first-class modes.
- Desktop and mobile screenshots are mandatory before acceptance.
- Charts require accessible tables, units, periods, scenario, source, tooltips, legends, and all non-ready states.
- Semantic colors include text/icons and declare whether higher or lower is better.
- No page-level horizontal scroll on mobile.

## Residual Risks

1. Exact official government forms remain unavailable until a separate verified model registry is populated with documentary proof.
2. Sector readiness weights require approved per-sector configuration before production scoring.
3. Actual React/API implementation and rendered visual QA are not included in this documentation-only release; KIMI must execute the r14 build prompt and acceptance suite.
4. Legal, investment, tax, privacy, and cybersecurity conclusions still require their authorized professional reviewers where applicable.

## Final Review Decision

r14 is ready to replace r13 as the visual-output build specification. It is deliberately stricter than the legacy screens: it preserves their useful depth while removing unsupported numbers, ambiguous confidence, provider authority, government-approval implications, and untraceable recommendations.
