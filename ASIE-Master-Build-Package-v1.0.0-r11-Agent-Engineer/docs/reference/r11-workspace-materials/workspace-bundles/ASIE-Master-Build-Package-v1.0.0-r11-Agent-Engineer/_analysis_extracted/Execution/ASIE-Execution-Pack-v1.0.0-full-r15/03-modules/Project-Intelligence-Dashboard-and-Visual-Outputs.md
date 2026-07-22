# Project Intelligence Dashboard and Visual Outputs

## لوحة ذكاء المشروع والمخرجات البصرية

## Decision

This document defines a composite user experience built from approved outputs of existing ASIE Modules. It does not create a new Module, Layer, Controller, Bus, Heart, truth owner, or direct Module-to-Module path.

يحدد هذا المستند تجربة مستخدم مركبة من مخرجات موديولات ASIE الحالية. ولا ينشئ موديولًا أو طبقة أو متحكمًا أو ناقلًا أو قلبًا أو مصدر حقيقة جديدًا، ولا يسمح باتصال مباشر بين الموديولات.

Affected AAS boundaries:

- Project Wizard owns project context.
- Market Intelligence owns market evidence, sector signals, geography, source confidence, and lawful open-data outputs.
- Finance Engine owns deterministic finance, scenarios, sensitivity, and MCMC.
- Decision Council owns validation, structured viewpoints, consensus, readiness, risk synthesis, and final decision status.
- AI Advisory explains approved outputs and drafts text; it does not create facts, financial values, chart datasets, authorization, or final decisions.
- Reports owns report composition and export parity; it does not recalculate.
- Audit / Observability owns lineage visibility, authorization evidence, audit events, and presentation-policy enforcement.

## Old-Screen Use Rule

The supplied legacy screenshots are visual and workflow references only. Their company names, provider names, competitor claims, scores, percentages, currency values, dates, maps, wording, and recommendations are not approved ASIE data and must not be migrated into production.

الصور القديمة مراجع بصرية ومسارية فقط. لا تُنقل منها أسماء الشركات أو المزودين أو المنافسين أو الدرجات أو النسب أو القيم المالية أو التواريخ أو الخرائط أو الصياغات أو التوصيات إلى بيانات الإنتاج.

## Canonical Navigation

The dashboard is the project workspace, not a separate architectural component.

| Route | Arabic label | English label | Primary output owner |
| --- | --- | --- | --- |
| `/projects/:projectId/overview` | الملخص التنفيذي | Executive Overview | Decision Council + Reports |
| `/projects/:projectId/strategy` | التحليل الاستراتيجي | Strategic Analysis | Project Wizard + Market Intelligence + Decision Council |
| `/projects/:projectId/market` | السوق والمنافسة | Market & Competition | Market Intelligence |
| `/projects/:projectId/finance` | الجدوى المالية | Financial Feasibility | Finance Engine |
| `/projects/:projectId/risks` | المخاطر والحساسية | Risks & Sensitivity | Decision Council + Finance Engine |
| `/projects/:projectId/scenarios` | السيناريوهات والمحاكاة | Scenarios & Simulation | Finance Engine |
| `/projects/:projectId/decision` | مجلس القرار | Decision Council | Decision Council |
| `/projects/:projectId/execution` | خطة التنفيذ | Execution Plan | Decision Council + Reports |
| `/projects/:projectId/investment` | خريطة الاستثمار | Investment Readiness | Finance Engine + Decision Council + Reports |
| `/projects/:projectId/evidence` | الأدلة والمنهجية | Evidence & Methodology | Market Intelligence + Audit / Observability |
| `/projects/:projectId/report` | التقرير | Report | Reports |
| `/projects/:projectId/feasibility` | دراسة الجدوى الاحترافية | Professional Feasibility | Decision Council + Reports |
| `/projects/:projectId/technical` | الدراسة الفنية والتشغيلية | Technical & Operational Study | Project Wizard + Decision Council + Reports |
| `/projects/:projectId/procurement` | المنافسات والمشتريات | Procurement & Competition | Decision Council + Audit / Observability + Reports |

Navigation rules:

1. The default route is `overview`.
2. A section with missing required inputs shows `needs_input`; it does not disappear.
3. A blocked section shows the exact blocking reason and responsible workflow.
4. The same `run_id`, `scenario_id`, and `as_of` timestamp remain visible across pages.
5. Changing a project input creates a new analysis run; old approved runs remain read-only and auditable.
6. Deep links preserve project, run, scenario, period, currency, locale, and filter state.
7. The feasibility route shows all profile-required chapters and their exact states; missing work remains visible.
8. The technical route reconciles capacity, process, location, equipment, staffing, quality, supply, implementation, and operating readiness with market demand and finance.
9. The procurement route appears when applicable and separates official MOF/Etimad references from exact controlling competition documents.

## Professional Feasibility Views r15

### `/feasibility`

Required visual structure:

- Study profile and purpose, study/version/as-of metadata, overall gate state, and unresolved blockers.
- Fourteen chapter navigator: executive/decision, project/strategic case/options, market/commercial, technical, operational, organization/governance, legal/regulatory/tax, ESG/impact, procurement/contracting, implementation, financial, economic/CBA, risk/uncertainty/resilience, and recommendation/gate.
- Each chapter card shows owner, state, evidence coverage, assumptions, validation, limitations, contradictions, reviewer, and drill-down.
- Financial chapter exposes integrated statements, NPV/IRR/MIRR/PI/payback conventions, working capital/funding, unit economics, debt metrics, and uncertainty outputs only when applicable.
- Frameworks such as SWOT, PESTEL, Porter, BMC, and VPC appear as evidence-linked analytical views, never as substitutes for chapters.

### `/technical`

- Location/technology/process alternatives and selection rationale.
- Designed, practical, ramp-up, and constrained capacity with bottleneck chart.
- Equipment, utilities, materials, suppliers, lead times, quality, maintenance, staffing, and operating model.
- Implementation stages, dependencies, critical path, commissioning, and acceptance criteria.
- Reconciliation panel linking demand, capacity, headcount, CapEx/OpEx, revenue start, and implementation dates.

### `/procurement`

- Applicability banner: private only, government competition, or mixed.
- Exact competition identity, entity, deadline, current document package, addenda, answers, evaluation criteria, qualification, guarantees, pricing schedule, contract type, local-content obligations, risks, and submission checklist when applicable.
- Official reference registry separates MOF/Etimad general references from exact competition controls.
- Every official form shows title, publisher, URL, version/date, hash, contract category, status, reviewer, review date, and override relation.
- No badge may say `government approved feasibility study`; permissible labels describe only the exact reviewed form/workflow.

All three routes use the universal output envelope, section-state resolver, bilingual display rules, export parity, and project-scoped authorization.

## Universal Output Envelope

Every visible metric, score, chart, warning, recommendation, and generated paragraph must carry this envelope or a resolvable reference to it:

```json
{
  "output_id": "uuid",
  "project_id": "uuid",
  "run_id": "uuid",
  "scenario_id": "baseline | optimistic | downside | custom",
  "owner_module": "string",
  "contract_id": "string.v1",
  "algorithm_id": "string",
  "algorithm_version": "semver",
  "value_type": "observed | calculated | assumption | simulation | model_inference | narrative",
  "value": null,
  "unit": "SAR | percent | month | count | index | text",
  "period": "string",
  "geography": "string",
  "evidence_refs": [],
  "assumption_refs": [],
  "formula_ref": "string",
  "confidence": null,
  "confidence_basis": "string",
  "status": "ready | needs_input | insufficient_data | blocked | stale | error | permission_denied",
  "as_of": "ISO-8601",
  "locale": "ar-SA | en",
  "audit_ref": "string"
}
```

Hard rules:

- A numeric output without `owner_module`, `algorithm_id`, `unit`, `period`, and lineage is rejected.
- `confidence` must identify whether it measures evidence coverage, statistical uncertainty, model confidence, or decision agreement.
- A confidence percentage is never displayed as probability of business success unless a specific approved probability model produced it.
- Visual rounding does not change the stored value; tooltips show the unrounded value when appropriate.
- Currency values always show currency, price basis, tax treatment, and nominal/real basis where relevant.

## Evidence Badges

Every card uses one primary evidence badge:

| Code | Arabic | Meaning |
| --- | --- | --- |
| `OFFICIAL_OPEN_DATA` | بيانات رسمية مفتوحة | Exact approved official open dataset or open API under `strict_open_data_only_v1` |
| `USER_VERIFIED` | مدخل موثق من المستخدم | User-provided input with validation and audit |
| `DOCUMENT_VERIFIED` | مستند متحقق | Value parsed from an approved document and validated |
| `DETERMINISTIC_CALCULATION` | حساب حتمي | Formula-owned output from Finance Engine or Decision Council |
| `APPROVED_ASSUMPTION` | افتراض معتمد | Explicit assumption approved for the run |
| `SIMULATION` | محاكاة | MCMC or approved scenario output with configuration |
| `MODEL_INFERENCE` | استدلال نموذجي | Non-factual model classification with model/version/confidence |
| `REFERENCE_ONLY` | مرجع للاستئناس | Link or human-authored alignment card; never evidence for a numeric claim |
| `UNAVAILABLE` | غير متاح | No lawful or sufficient evidence |

## Model Status and Official-Claim Guard

The interface must distinguish internal analytical models from exact official forms.

### r14 Baseline Assessment

The reviewed r14 baseline provides ASIE-owned deterministic finance (`FIN-ALG-01` through `FIN-ALG-05`), sector criteria, market evidence, sensitivity, fixed-seed MCMC, decision validation/personas/consensus, and chart authorization. It does not contain documentary proof identifying SWOT, PESTEL, Porter, BMC, VPC, a feasibility template, cost-benefit template, project charter, procurement plan, or investment model as an exact government-issued form with form ID, version, applicability, and official source.

Therefore r15 uses those capabilities as ASIE models or analytical frameworks. KIMI must stop before adding an `Official form` or `Government approved` badge until an exact record is added to the model registry and approved by an authorized human reviewer.

| Display label | Allowed use | Required proof |
| --- | --- | --- |
| `ASIE deterministic model` / نموذج ASIE حتمي | Finance or decision algorithm owned by ASIE | Algorithm ID, formula version, tests |
| `ASIE approved template` / قالب ASIE معتمد داخليًا | Internal project-size or sector template | Template ID, owner, version, approval record |
| `Official-source aligned` / متوافق مع مصدر رسمي | Structure informed by an exact official source | Issuer, exact document URL, version/date, scope, human review |
| `Official form` / نموذج رسمي | Exact form issued for the applicable purpose | Issuing authority, form identifier, version, applicability, unchanged fields |
| `Strategic framework` / إطار تحليلي | SWOT, PESTEL, Porter, BMC, VPC | Framework name and ASIE interpretation label |
| `Estimate` / تقدير | Forecast from approved inputs | Assumptions, formula, range, date |

Forbidden claims:

- `Government approved`, `معتمد حكوميًا`, or equivalent without exact documentary proof.
- Treating Etimad, Ministry of Finance, EXPRO, GASTAT, SDAIA, NCA, DGA, GOV.SA, or any government entity as endorsing ASIE.
- Presenting SWOT, PESTEL, Porter, BMC, VPC, MCMC, valuation, investor terms, or AI-generated prose as a government form.
- Using a strategy page as a compliance certificate or as the source of a numeric score.

## Page 1: Executive Overview

### Header

- Project name, primary sector, subsector, geography, project stage, owner workspace.
- Analysis run status, `as_of`, data freshness, baseline scenario, currency, locale.
- Actions: compare runs, refresh eligible open data, export report, share under authorization.

### Required outputs

| Widget | Arabic title | Required content | Owner |
| --- | --- | --- | --- |
| Final decision | الحكم التنفيذي | `APPROVE`, `CONDITIONAL_APPROVE`, `REVISE`, `REJECT`, or `BLOCKED`; reasons and conditions | Decision Council |
| Readiness score | درجة الجاهزية | 0-10, band, domain contributions, validation ceiling, version | Decision Council |
| Confidence summary | ملخص الثقة | Evidence coverage, uncertainty band, decision agreement; separate values | Decision Council using approved Market Intelligence inputs |
| Key indicators | المؤشرات الحاسمة | Market, finance, risk, execution, and alignment indicators | Owner Modules |
| Blocking issues | العوائق الحرجة | Missing inputs, stale data, legal block, validation failures | Audit + owner |
| Next best actions | الخطوات التالية | Prioritized actions with owner, due window, expected evidence | Decision Council + Reports |
| Source summary | ملخص الأدلة | Source count by badge, freshness, missing categories | Market Intelligence |

The page must answer in the first viewport: What is the decision? How ready is the project? What is blocking it? What should happen next?

## Page 2: Strategic Analysis

Sections appear in this order:

1. Idea brief: problem, proposed solution, target users, geography, business model, stage.
2. Context completeness: required fields, missing facts, confidence in sector classification.
3. SWOT: strengths, weaknesses, opportunities, threats; each item carries evidence or `judgment` status.
4. PESTEL: political/regulatory, economic, social/cultural, technological, environmental, legal.
5. Porter Five Forces: rivalry, new entrants, supplier power, buyer power, substitutes.
6. Business Model Canvas: customer segments, value propositions, channels, relationships, revenue streams, key resources, key activities, partners, cost structure.
7. Value Proposition Canvas: customer jobs, pains, gains, products/services, pain relievers, gain creators.
8. National alignment: approved ASIE-authored reference cards only, with non-endorsement notice.
9. Cultural fit and sensitivity: evidence-backed factors, risks, review flags, and mitigation.
10. Multidimensional radar: market, differentiation, profitability, execution, innovation, plus sector-selected criteria.

Strategic frameworks do not create financial inputs automatically. Any proposed number must return to the Project Wizard or Finance input approval flow.

## Page 3: Market and Competition

Required sections:

- Market definition and boundaries: product/service, customer, geography, period, currency.
- Market size: `TAM`, `SAM`, and `SOM` only when definitions and data support them; otherwise show unavailable.
- Demand indicators: source, frequency, regional scope, trend, seasonality, confidence.
- Competition intensity: competitor count, concentration if calculable, substitutes, entry barriers.
- Competitor table: name, category, geography, offering, price basis, source, observation date, confidence.
- Competitor map: approximate public/business locations only; no private personal coordinates.
- Customer segments: needs, buying behavior, evidence coverage, estimated accessibility.
- Price distribution: normalized unit, currency, median, IQR, sample count, outlier count.
- Similar cases: official/open evidence when eligible; Mostaql remains reference-only with zero backend retrieval.
- Market gaps and opportunity signals: evidence refs and counter-evidence.
- Source health: freshness, access state, legal eligibility, and kill-switch state.

### External context and news

An external-context panel is optional. It is `UNAVAILABLE` unless an exact lawful approved source and bounded input exist. A sentiment or topic model output is labeled `MODEL_INFERENCE`, names its model/version, shows uncertainty, and is excluded from readiness and finance by default. Tavily, a news page, or a search result is never displayed as the factual source of a number.

## Page 4: Financial Feasibility

### Input readiness

Before results, show:

- Required, supplied, verified, assumed, missing, stale, and rejected inputs.
- Source map for price, volume, cost, tax, salary, rent, equipment, and working-capital inputs.
- VAT and tax handling status; ASIE must not provide tax or legal certification.
- Template ID, sector, project size, formula version, run time, currency, and nominal/real basis.

### Baseline outputs

- Startup cost and working capital.
- CapEx and OpEx breakdown.
- Monthly revenue, gross profit, EBITDA where applicable, operating profit, net cash flow.
- Gross margin and net margin.
- Break-even month and break-even units.
- Cumulative cash requirement and maximum cash deficit.
- ROI and payback period.
- NPV and IRR only when discount rate, horizon, cash-flow convention, and formula version are supplied.
- Unit economics only when applicable: CAC, LTV, LTV/CAC, CAC payback, contribution margin, churn, MRR/ARR, retention, and NPS source.

Every metric card must show formula, input lineage, scenario, period, and whether it is observed, assumed, or calculated.

### Forecast visuals

- Monthly 36-month revenue, expense, profit, and cash-flow series.
- Cumulative cash curve and break-even marker.
- Cost composition and use-of-funds chart.
- Profit bridge waterfall.
- Comparison table for baseline, optimistic, and downside scenarios.

## Page 5: Risks and Sensitivity

### Risk layers

At minimum:

- Market risk.
- Financial risk.
- Operational risk.
- Regulatory/compliance risk.
- Cybersecurity and data risk.
- Cultural/social risk.
- Strategic risk.
- Evidence and model risk.

Each risk record contains `risk_id`, cause, event, impact, category, probability band, impact band, exposure, evidence, owner, control, treatment, target date, residual risk, status, and audit trail.

### Risk matrix

- 5x5 probability-impact matrix.
- Exact band definitions visible in methodology.
- No invented probability percentages when only ordinal bands are available.
- Clicking a cell filters the register.

### Sensitivity

- Revenue decrease, cost increase, and demand/occupancy change are mandatory axes.
- Additional sector-specific axes come from `sector.evaluation.criteria.v1`.
- Show baseline, changed variable, delta, affected outputs, and threshold at which decision band changes.

### Resistance test

The resistance-test panel contains:

- Strongest opposing case.
- Fragile assumptions.
- Missing data required to confirm or reject each assumption.
- Failure scenarios and leading indicators.
- Countermeasures and stop/go thresholds.

AI may draft opposing arguments from approved evidence. It must not create numeric evidence or mark an assumption as verified.

## Page 6: Scenarios and Simulation

Required scenario cards:

- Baseline / الأساسي.
- Optimistic / المتفائل.
- Downside / المتشائم.
- Custom scenarios when authorized.

Each scenario shows the exact changed variables, input ranges, source/assumption refs, customers/units, monthly profit, maximum expected cash deficit, break-even, and probability only when generated by an approved simulation.

MCMC presentation requires:

- Fixed seed.
- Iteration count.
- Distribution family and parameters for each variable.
- P5, P25, P50, P75, P95.
- Downside probability and defined threshold.
- Histogram and cumulative distribution.
- Run configuration and reproducibility action.

`optimistic`, `baseline`, and `downside` labels are not probabilities by themselves.

## Page 7: Decision Council

Required sections:

- Validation Gate result and failed checks.
- Five approved ASIE personas from `DEC-ALG-02`.
- For each persona: strengths, weaknesses, risks, recommendation, confidence basis, vote, evidence refs.
- Vote distribution, consensus score, disagreement spread, and preserved dissent.
- Final decision band and binding conditions.
- Contradictory evidence and unresolved assumptions.
- Re-evaluation triggers.

The UI must not expose private chain-of-thought. It displays structured conclusions and evidence references only.

## Page 8: Execution Plan

Required sections:

- Execution diagnosis: market strength, strategic alignment, national alignment, cultural fit, team readiness, operational complexity, and risk status.
- Prioritized recommendations with evidence, owner, effort, expected result, and dependency.
- 30/60/90-day plan or sector-appropriate phases.
- Milestones with success criteria and stop/go gates.
- Operational risk register and mitigation actions.
- Required tests, permits, contracts, suppliers, staffing, and system readiness as applicable.
- KPI tree: leading indicators, lagging indicators, target, source, frequency, owner.
- Timeline or Gantt generated from approved tasks, not AI dates presented as fact.

## Page 9: Investment Readiness

This page is advisory and must show a financial/legal disclaimer.

Required sections:

- Investment-readiness status and blockers.
- Proposed funding stage only when project stage and need support it.
- Funding range from deterministic use-of-funds and runway calculations.
- Use of funds by product, team, marketing, operations, compliance, and contingency.
- Runway, burn, cash deficit, and milestone financed.
- Valuation range only when method, assumptions, comparables, and limitations are visible.
- Equity range and negotiation strength as advisory outputs, not legal terms.
- Investor profile and eligibility rationale.
- Founder protections and term warnings as general information, requiring professional legal review.
- Investor-ready narrative assembled from approved facts and visibly labeled as a draft.

Forbidden:

- Guaranteed funding or valuation.
- Legal advice or enforceable term-sheet language.
- Invented investors, comparable transactions, or market multiples.
- Hiding downside scenario or dilution assumptions.

## Page 10: Evidence and Methodology

Required tabs:

| Tab | Arabic | Content |
| --- | --- | --- |
| Sources | المصادر | Exact URL/dataset/API, issuer, title, access class, license, retrieval date, freshness |
| Lineage | سلسلة الإثبات | Input to transformation to algorithm to output to chart/report |
| Assumptions | الافتراضات | Owner, value/range, reason, approval, expiry, affected outputs |
| Models | النماذج | Algorithm/template IDs, versions, owner, validation status, limitations |
| Runs | التشغيلات | Run comparison, configuration, seed, user, timestamp, status |
| Audit | التدقيق | Access, changes, approvals, exports, blocks, source suspension |
| Disclaimers | التنبيهات النظامية | Finance, investment, legal, data, AI, and official-source notices |

Every chart tooltip links to this page at the relevant evidence or formula record.

## Page 11: Report

The report is a frozen view of one approved `run_id`.

- Report numbers must match dashboard numbers for the same run and scenario.
- Export does not trigger recalculation.
- Arabic export is RTL and English export is LTR.
- Sources, assumptions, formula versions, simulation configuration, dissent, and disclaimers are included.
- A stale or superseded run is labeled visibly.
- PDF, presentation, and spreadsheet exports share the same output IDs.

## Visual System

### Layout

- Arabic is RTL; English is LTR. Mixed identifiers, formulas, URLs, and currency codes preserve readable direction.
- Desktop uses a 12-column content grid; mobile uses one column with no horizontal page scrolling.
- Cards are reserved for repeated metrics, risks, personas, scenarios, and bounded tools. Do not nest full cards inside cards.
- Card radius is 8px or less unless the established design system specifies otherwise.
- Dense analytical pages use section headers, dividers, tables, and drawers instead of oversized whitespace.
- Primary decision, blockers, and next action remain above the fold on desktop and near the top on mobile.

### Semantic colors

| Meaning | Color role | Rule |
| --- | --- | --- |
| Positive/ready | Green | Never used alone; include text/icon |
| Caution/revise | Amber | Indicates action or uncertainty |
| High risk/blocked | Red | Reserved for material risk, failure, or block |
| Informational/calculated | Blue | Deterministic or contextual information |
| Model inference | Violet | Must include `MODEL_INFERENCE` label |
| Neutral/unavailable | Gray | Missing, stale, reference-only, or inactive |

Do not color a low numeric value green unless lower is explicitly better. All progress bars declare directionality.

### Metric card anatomy

1. Title and owner icon.
2. Primary value, unit, and period.
3. Status band and comparison basis.
4. Evidence badge.
5. Confidence type and value when applicable.
6. `as_of` timestamp.
7. Drill-down to formula/evidence.
8. Accessible text alternative.

### Charts

- Axes, units, period, scenario, source, and zero baseline are explicit.
- Truncated axes require a visible marker.
- Tooltips include raw value, display value, evidence badge, and timestamp.
- Legends remain visible and keyboard accessible.
- Tables are available as an accessible alternative to charts.
- Empty, loading, insufficient, blocked, stale, error, and permission-denied states have distinct messages.

## Bilingual Naming

- Arabic UI defaults to Arabic titles and explanations.
- English UI defaults to English titles and explanations.
- Official source names remain in their official language, with a localized explanatory label when useful.
- Algorithm IDs, contract IDs, formula symbols, product names, and URLs are not translated.
- Arabic numbers follow the selected locale policy consistently; stored values remain locale-neutral.
- Export language equals the user's selected report language, not the source-page language.

## Security and Privacy

- Every project route requires project-scoped authorization and entitlement checks.
- Shared links are revocable, time-bound, least-privilege, and audited.
- No secret, token, MFA data, private prompt, full sensitive payload, or hidden model reasoning appears in the dashboard.
- Personal data is minimized and masked by default.
- Exact personal coordinates are not shown on competitor or market maps.
- Export and share actions emit audit events.
- Frontend never calls AI, database, open-data source, messaging provider, or another Module directly.
- All internal data movement follows the approved Socket Contract Layer, APP, System Bus, and Bus Controller governance path.

## Legacy Screenshot Functional Crosswalk

The screenshot references below identify concepts only. Values and wording are discarded.

| Ref | Legacy concept | ASIE destination |
| --- | --- | --- |
| `L01` | Strategic score card | Overview > Readiness with evidence coverage |
| `L02` | Sensitivity factors | Risks > Sensitivity with baseline and formula |
| `L03` | News impact | Market > Optional external-context inference |
| `L04-L05` | Final score and judgment | Overview > Readiness + Decision Council verdict |
| `L06` | Strategic radar | Strategy > Sector-aware multidimensional radar |
| `L07` | National/cultural alignment | Strategy > Alignment and cultural review |
| `L08` | Risk layers | Risks > Risk register and category cards |
| `L09` | Multidimensional layers | Strategy > Domain decomposition |
| `L10` | Three scenarios | Scenarios > Exact variable comparison |
| `L11-L13` | Execution diagnosis and risks | Execution > Diagnosis, risks, actions |
| `L14-L15` | Forecast and financial indicators | Finance > Forecast, unit economics, limitations |
| `L16-L17` | Funding and negotiation | Investment > Use of funds and advisory terms |
| `L18` | Investor narrative | Investment > Audited draft narrative |
| `L19-L20` | Growth channels and milestones | Execution > KPI tree and milestone roadmap |
| `L21` | Similar projects | Market > Similar cases with lawful evidence rules |
| `L22-L23` | SWOT, BMC, VPC, risk matrix | Strategy and Risks pages |
| `L24` | Resistance test | Risks > Resistance test and assumption register |
| `L25` | Advanced market/finance analysis | Market + Finance + Execution routes |
| `L26` | Map and market risks | Market > Competitor map and evidence-backed risks |
| `L27-L28` | Recommendations and expert panels | Decision Council > Structured persona outputs |

## Required Frontend Components

These are implementation components, not ASIE architectural components:

- `ProjectRunHeader`
- `DecisionHero`
- `ReadinessScore`
- `EvidenceBadge`
- `MetricCard`
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

Frontend stack is React + TypeScript + Vite + pnpm. Frontend receives TypeScript-safe view contracts and contains no Python runtime, financial formula implementation, AI provider call, source retrieval, or authorization authority.

## Acceptance Summary

The dashboard is accepted only when:

1. Every old-screen concept maps to an ASIE route or is explicitly rejected.
2. No legacy value, name, provider claim, or wording appears as production truth.
3. Every numeric output resolves to an owner, contract, algorithm, formula, source/assumption, unit, period, run, and timestamp.
4. Dashboard and report values match for the same run.
5. Arabic RTL and English LTR pass desktop and mobile visual tests.
6. Every chart has an accessible table and all required states.
7. Final score, confidence, simulation probability, and decision agreement are not conflated.
8. Official-source alignment is not represented as government approval.
9. Strict open-data-only, reference-only, AI, privacy, security, and audit rules remain enforced.
10. No new ASIE architectural component or direct Module call is introduced.
