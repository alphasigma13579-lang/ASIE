# KIMI Project Dashboard Build Prompt

## أمر بناء لوحة ذكاء المشروع

## Role

Implement the ASIE Project Intelligence Dashboard under AAS v1.0.0 Frozen Baseline and the r15 Execution/Algorithm packages. You are an implementation agent, not the architecture authority.

## Read First

Before code, read and cite:

1. AAS v1.0.0 Frozen Baseline.
2. Agent Governance Pack.
3. `Project-Intelligence-Dashboard-and-Visual-Outputs.md`.
4. `Project-Dashboard-Decision-and-Presentation-Algorithms.md`.
5. Existing Module Cards, Socket Contract Catalog, Message Type Catalog, finance/market/decision algorithms, source policies, and acceptance tests.

## Scope

Build the authenticated project workspace routes:

- `/projects/:projectId/overview`
- `/projects/:projectId/strategy`
- `/projects/:projectId/market`
- `/projects/:projectId/finance`
- `/projects/:projectId/risks`
- `/projects/:projectId/scenarios`
- `/projects/:projectId/decision`
- `/projects/:projectId/execution`
- `/projects/:projectId/investment`
- `/projects/:projectId/evidence`
- `/projects/:projectId/report`

## Stack

- Frontend: React + TypeScript + Vite + pnpm.
- Backend: Python only for API, AI integration, database access, and backend orchestration.
- Shared frontend contracts: TypeScript-safe schemas under `packages/contracts`.
- Use the existing icon, chart, form, table, i18n, test, and design-system packages when present.

## Architecture Boundary

- Do not create a Dashboard Module, Dashboard Layer, orchestration controller, alternative bus, or new truth owner.
- Reports composes approved view data; it does not recalculate.
- Owner Modules produce their own outputs.
- Internal interaction follows Module -> Socket Contract Layer -> APP -> System Bus -> Bus Controller governance -> Target Socket -> Target Module.
- Frontend calls approved API/view contracts only.
- No direct frontend access to AI providers, databases, open-data sources, notification providers, or internal Modules.

## Phase 1: Contract Types

Create or update TypeScript-safe schemas for:

- Universal output envelope.
- Project dashboard view request/response.
- Output lineage request/response.
- Section state.
- Readiness result and domain contributions.
- Confidence breakdown.
- Strategic framework pack.
- Risk register and matrix.
- Scenario comparison and simulation configuration.
- Decision personas, consensus, and dissent.
- Execution roadmap and KPI tree.
- Investment readiness and disclaimer state.
- Evidence/source/model/assumption/run records.

Reject unknown enum values and incompatible contract versions.

## Phase 2: Shell and Navigation

Build:

- Project-scoped route guard.
- `ProjectRunHeader` with run/scenario/date/currency/locale.
- Responsive section navigation.
- Loading, blocked, stale, error, permission, empty, and needs-input states.
- Arabic RTL and English LTR layouts.
- Deep-link filter state.

No route may infer readiness from component presence or local frontend state.

## Phase 3: Shared Analytical Components

Build reusable components:

- `DecisionHero`
- `ReadinessScore`
- `MetricCard`
- `EvidenceBadge`
- `ConfidenceBreakdown`
- `SourceDrawer`
- `FormulaDrawer`
- `AssumptionDrawer`
- `ScenarioCompare`
- `RiskMatrix`
- `RiskRegister`
- `SensitivityPanel`
- `SimulationDistribution`
- `PersonaDecisionCard`
- `DissentPanel`
- `StrategicFrameworkTabs`
- `BusinessModelCanvas`
- `ValuePropositionCanvas`
- `CompetitorMap`
- `FinancialForecast`
- `InvestmentReadinessPanel`
- `ExecutionRoadmap`
- `OutputState`

Every metric component consumes the universal output envelope. Do not accept a bare number prop for production data.

## Phase 4: Pages

Implement page sections exactly as specified in the r15 visual-output document. Preserve the sequence:

1. Executive decision.
2. Evidence and confidence.
3. Market and strategy.
4. Deterministic finance.
5. Risks, sensitivity, and simulation.
6. Decision personas and dissent.
7. Execution and investment readiness.
8. Evidence, methods, and report.

## Phase 5: Visual Rules

- Use a restrained, dense analytical interface.
- Cards have radius 8px or less unless an existing ASIE token differs.
- Do not nest full cards.
- Use semantic colors plus labels/icons; color alone is insufficient.
- Keep primary decision, blockers, and next action near the top.
- Every chart has title, unit, period, scenario, source, tooltip, legend, and accessible table.
- Do not truncate Arabic labels or place mixed-direction identifiers incorrectly.
- Mobile has one-column flow and no page-level horizontal scrolling.
- Avoid gradients, decorative blobs, glass effects, oversized typography, and dark stock imagery.

## Phase 6: Truth and Lineage

For every visible output:

- Show evidence badge.
- Resolve source/formula/assumption drill-down.
- Show `as_of` and run.
- Preserve raw value and approved rounding.
- Distinguish observed, calculated, assumed, simulated, inferred, narrative, reference-only, and unavailable.
- Never call evidence confidence a success probability.
- Never call internal ASIE templates government-approved.

## Phase 7: Security

- Project-scoped authorization on every request.
- Permission-denied state before any sensitive payload renders.
- Redact personal data and exact personal coordinates.
- Do not log tokens, MFA values, prompts, sensitive payloads, or private model reasoning.
- Audit view, compare, export, share, source drill-down, and blocked-state override attempts.
- Shared links are revocable, scoped, and time-bound.

## Phase 8: Test Fixtures

Use labeled fixtures only:

- `demo_sample`.
- `generated_product_mock`.
- `anonymized_real_output` after audit approval.

Fixtures must not reuse values, names, claims, maps, or wording from the legacy screenshots. Production builds must not silently fall back to fixture data.

## Expected File Shape

Adapt to the repository while preserving these responsibilities:

```text
apps/frontend/src/features/project-dashboard/
  routes/
  pages/
  components/
  charts/
  tables/
  drawers/
  i18n/
  accessibility/
  tests/
apps/backend/
  api/project_dashboard/
  services/report_composition/
  tests/project_dashboard/
packages/contracts/src/project-dashboard/
docs/architecture/project-dashboard-boundary.md
```

Backend folders are implementation boundaries, not new ASIE Modules.

## Acceptance Tests

KIMI must provide automated tests for:

- Contract schema and version rejection.
- Cross-project authorization denial.
- Bare numeric metric rejection.
- Dashboard/report parity.
- Readiness validation ceiling.
- Missing-domain `insufficient_data`.
- Confidence-type labels.
- Risk ordinal/percentage separation.
- Scenario variable disclosure.
- MCMC seed/configuration visibility.
- AI unsupported-number rejection.
- Reference-only and strict-open-data-only enforcement.
- Arabic RTL and English LTR.
- Desktop and mobile screenshots.
- Keyboard navigation, focus order, chart table alternatives, and contrast.
- Loading, empty, needs-input, stale, blocked, error, and permission states.
- No fixture fallback in production.
- No legacy screenshot values or names.

## Required Visual Verification

Run the app and capture at minimum:

- Desktop Arabic overview, finance, risks, decision, and evidence.
- Mobile Arabic overview and finance.
- Desktop English overview.
- A blocked state, stale state, needs-input state, and permission-denied state.

Verify no overlap, clipping, broken RTL, hidden units, unreadable charts, or layout shift.

## Stop Rules

Stop and report before coding if:

- A required owner output, contract, algorithm, formula, status enum, or evidence field is missing.
- You need a new ASIE Layer, Module, Controller, Bus, Heart, or direct Module call.
- A dashboard number would need to be generated by AI or frontend code.
- An official/government-approved label lacks exact documentary proof.
- A source would violate r15 open-data, reference-only, privacy, legal, or cybersecurity rules.
- A route needs access broader than the user's project scope.

## First Response

Before implementation, return:

1. AAS impact.
2. Existing owners for every page.
3. Contracts and messages used or missing.
4. Algorithms used or missing.
5. Data classification and authorization plan.
6. Route/component/file plan.
7. Test plan.
8. Missing evidence or formulas.
9. Explicit non-goals.

Do not begin coding until the preflight gate passes.

## r15 Professional Feasibility Extension

Add three routes to the existing project dashboard navigation:

- `/projects/:projectId/feasibility`
- `/projects/:projectId/technical`
- `/projects/:projectId/procurement`

Read and implement:

- `03-modules/Professional-Feasibility-Study-and-Procurement-Reference-Framework.md`.
- Algorithm Catalog `02-finance/Advanced-Feasibility-and-Investment-Appraisal-Algorithms.md`.
- The r15 contracts, messages, tests, and forbidden patterns.

Build requirements:

1. Render the fourteen professional chapters with exact owner/state/evidence/assumption/validation/limitation/contradiction/reviewer metadata.
2. Render technical capacity, operating model, implementation dependencies, and demand/capacity/finance reconciliation.
3. Render procurement applicability, exact competition package status, official reference registry, form version/applicability, and override hierarchy.
4. Render integrated financial statements, appraisal conventions, funding, unit economics, debt, CBA, sensitivity, stress, scenarios, and MCMC only from owner outputs.
5. Preserve Arabic-first RTL and English LTR parity, responsive density, chart accessibility, empty/loading/error/blocked/stale states, and PDF/dashboard parity.
6. Do not copy values, claims, provider names, competitors, or recommendations from the legacy screenshots.

Do not create a Dashboard, Feasibility, Procurement, or Methodology Module. Do not call Modules directly. Do not let frontend, Reports, AI, or a chart library calculate business truth.
