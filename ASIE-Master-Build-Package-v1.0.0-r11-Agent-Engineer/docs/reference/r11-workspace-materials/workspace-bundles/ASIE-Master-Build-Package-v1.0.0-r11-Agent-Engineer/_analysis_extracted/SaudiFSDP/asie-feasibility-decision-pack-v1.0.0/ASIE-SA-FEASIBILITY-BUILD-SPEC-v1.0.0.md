# ASIE Saudi Feasibility and Decision Engine

## Binding Build Specification v1.0.0

### 1. Document Control

| Field | Value |
| --- | --- |
| Status | Approved implementation baseline |
| Version | 1.0.0 |
| Date | 2026-07-13 |
| Product owner | AlphaSigma Lab |
| Primary jurisdiction | Kingdom of Saudi Arabia |
| Future scope | Separate GCC country rule packs |
| Architecture | AAS v1.0.0 Frozen Baseline |
| Five-persona protocol | FSP v3.1 / Five Sovereign Decision Protocols (FSDP) |

This specification converts the approved feasibility vision into buildable requirements. It is not an ACP and does not change AAS component responsibilities.

### 2. Product Outcome

ASIE shall produce a proportionate, professional feasibility study and decision package for:

- individual and micro projects;
- small and medium projects;
- small, medium, and large establishments;
- medium and large companies;
- capital-intensive and project-finance cases;
- sector-specific Saudi projects, with later country-specific GCC expansion.

The result shall not be selected randomly or from one generic template. The system shall route each project to a model depth based on jurisdiction, legal form, enterprise size, project complexity, sector, lifecycle, financing, reporting basis, and evidence quality. Subscription controls access and depth but may not downgrade required rigor silently.

### 3. Architectural Decision

#### 3.1 Required Message Path

```text
Source Module
-> Source Socket
-> Socket Contract Layer
-> APP
-> ASIE System Bus
-> Bus Controller participation governance
-> Target Socket
-> Target Module
```

Direct Module-to-Module calls are forbidden. Frontend, report renderers, AI providers, databases, queues, and external research providers may not bypass Contracts.

#### 3.2 Capability Ownership

| Capability | Owner | Forbidden |
| --- | --- | --- |
| Project classification and model routing | Approved feasibility domain Module | Subscription-only routing or UI-owned routing |
| Financial calculations | Financial Module deterministic engine | AI, frontend, reports, or database formulas as authority |
| Saudi rule resolution | Compliance/Data capability behind Contract | Hard-coded UI rates or stale undocumented rules |
| Evidence and benchmark scoring | Research/Evidence capability | Treating prestige as proof or unlicensed copying |
| Monte Carlo and switching values | Deterministic risk capability | AI-selected distributions or untraceable randomness |
| Persona narrative | AI Module behind AI Contract | Creating financial numbers or reading another persona output |
| Persona KPI calculation | Deterministic evaluators | AI-generated scores |
| Sovereign Verdict synthesis | Deterministic Decision capability | Majority voting or AI final authority |
| Dashboard | React presentation shell | Business logic, source validation, calculations, or direct provider calls |
| Reports | Export Module from immutable snapshot | Recalculation or divergence from engine results |

No new core AAS component, controller, bus, layer, or Heart may be created.

### 4. Classification and Model Routing

#### 4.1 Independent Classification Axes

The router shall evaluate all axes independently:

1. `jurisdiction`: country, region, city, currency, timezone, effective date.
2. `legal_form`: individual, sole establishment, LLC, joint stock, nonprofit, other approved form.
3. `enterprise_size`: micro, small, medium, large under a versioned Saudi rule set.
4. `project_complexity`: lite, standard, advanced, institutional/project-finance.
5. `sector_template`: retail, service, food, manufacturing, technology, real estate, health, tourism, logistics, professional services, or approved extension.
6. `lifecycle`: idea, validation, startup, expansion, acquisition, turnaround, replacement, greenfield, brownfield.
7. `financing_structure`: self-funded, debt, mixed, investor equity, project finance, grants/support.
8. `reporting_basis`: management feasibility, IFRS for SMEs where applicable, full IFRS where applicable, or another approved basis.
9. `subscription_entitlement`: basic, professional, business, enterprise.
10. `evidence_readiness`: insufficient, preliminary, reviewable, verified.

Legal form, enterprise size, project size, and accounting framework are not interchangeable.

#### 4.2 Complexity Score

The score shall use versioned, reviewable factors:

- capital intensity;
- debt and covenant complexity;
- construction or pre-opening duration;
- regulatory intensity;
- number of sites, entities, products, and currencies;
- imported equipment or inputs;
- technical process complexity;
- workforce intensity;
- environmental, safety, and quality exposure;
- sensitivity to price, demand, schedule, cost, interest, or FX;
- public accountability or reporting obligations;
- evidence uncertainty.

The selected depth shall be:

```text
required_depth = max(
  complexity_depth,
  regulatory_depth,
  financing_depth,
  reporting_depth,
  risk_depth
)
```

If the subscription does not permit the required depth, ASIE shall issue only a clearly labelled preliminary assessment, preserve all critical warnings, and block a false `FINAL_FEASIBILITY` status.

### 5. Saudi-First Rules

Saudi rules shall be stored as effective-dated, source-backed rule records. At minimum, the system shall support rule domains for:

- ZATCA: VAT, zakat, income tax, and applicable tax treatments;
- SOCPA: approved accounting framework selection and Saudi endorsements;
- HRSD: employment obligations and end-of-service requirements;
- GOSI: applicable employer and employee contribution rules;
- Monsha'at: enterprise-size classification;
- GASTAT: official demographic, economic, labor, and sector evidence;
- SAMA: monetary, finance, and banking indicators;
- sector regulators and licensing authorities.

No statutory rate shall be embedded permanently in frontend code. Every applied rule shall expose authority, source URL or document ID, effective dates, last human review, and calculation version.

A future GCC expansion shall create a separate country pack for each jurisdiction. Saudi rules must never be reused as a Gulf default.

### 6. Evidence and Global Research

#### 6.1 Authority by Claim Type

| Claim | Controlling evidence |
| --- | --- |
| Saudi law, fee, tax, license | Current Saudi official source |
| Accounting treatment | Applicable SOCPA-endorsed framework and approved policy |
| Project cost | Verified quotation, contract, invoice, or reviewed estimate |
| Saudi market fact | Official data or reviewed primary research |
| Strategic benchmark | Applicable, licensed, traceable professional research |
| World Bank/IFC method | Appraisal, alternatives, economic analysis, sensitivity, switching values |
| McKinsey research | Strategy, growth, competitive advantage, operating model, capital excellence, organizational and digital readiness |
| AI narrative | Explanation only; never evidence authority |

#### 6.2 Evidence Record

Each material assumption or benchmark shall record source, title, publisher, URL/document ID, publication and access dates, geography, sector, sample and methodology when available, unit, currency, applicable period, license/use classification, extraction method, applicability, limitations, reviewer, and expiry/revalidation date.

Reputation alone is not evidence. Public McKinsey research may be summarized and cited within permitted use. Proprietary tools, databases, questions, or benchmarks, including OHI content, shall not be copied, reproduced, or labelled as ASIE-owned without license.

### 7. Feasibility Model Structure

#### 7.1 Core Schedule Families

The engine shall maintain separate linked schedules for:

- project profile, geography, legal form, calendar, and reporting basis;
- products/services, channels, demand, price, volume, ramp-up, and seasonality;
- site, area, process, capacity, utilization, yield, waste, utilities, quality, and HSE;
- equipment, intangible assets, commissioning, maintenance, replacement, impairment, and disposal;
- rent, lease cash payments, right-of-use accounting when applicable, and lease liabilities;
- workforce, salaries, allowances, variable pay, employer burdens, recruitment, training, leave, insurance, and end-of-service;
- direct materials, COGS, operating expenses, pre-opening expenses, contingencies, and overheads;
- inventory, receivables, payables, bad-debt assumptions, and working capital;
- debt, fees, interest, grace periods, repayments, balloon payments, covenants, and refinancing;
- equity, owner contributions, owner compensation, withdrawals, dividends, and retained earnings;
- VAT, zakat, income tax, grants, subsidies, and other effective-dated rules;
- inflation, FX, nominal/real assumptions, and discount rates;
- income statement, balance sheet, and cash-flow statement;
- project cash flow, equity cash flow, CFADS, FCFF, and FCFE;
- break-even, unit economics, NPV, XNPV, IRR, XIRR, MIRR, PI, payback, DSCR, LLCR, and minimum liquidity;
- alternatives, scenarios, sensitivity, switching values, stress tests, and Monte Carlo;
- risk register, evidence quality, persona outputs, Sovereign Verdict, and reports.

#### 7.2 Time Model

The forecast shall include pre-operation and commissioning. It shall support monthly periods for startup, ramp-up, liquidity, and debt-service analysis and annual summaries for long horizons. Period conversion must use effective-rate mathematics rather than division by 12 unless the source rate is explicitly nominal with monthly compounding.

Nominal cash flows shall use nominal discount rates. Real cash flows shall use real discount rates. Mixed bases shall fail validation.

#### 7.3 Separate Financial Views

ASIE shall not confuse:

1. accounting statements;
2. project cash flow before financing;
3. equity investor cash flow after financing;
4. economic/social cost-benefit analysis when applicable.

Project NPV shall use an approved project cash flow and matching discount rate. Equity NPV shall use equity cash flow and cost of equity. Financing inflows shall not be inserted into project FCFF.

### 8. Deterministic Calculation Governance

Every formula shall have a stable ID, semantic version, owner, description, input schema, units, time basis, rounding rule, edge-case behavior, applicable model depths, and golden test vectors.

Mandatory controls:

- decimal arithmetic for money;
- full internal precision and presentation-only rounding;
- explicit sign conventions;
- no silent null-to-zero conversion;
- unit, currency, period, and timezone validation;
- divide-by-zero and invalid-domain protection;
- reconciliation gates before any final status;
- immutable input hash, evidence hash, formula version, and output hash;
- deterministic rerun equality for identical inputs;
- independent golden tests for high-impact formulas;
- explicit `NOT_APPLICABLE`, `NOT_READY`, and `INSUFFICIENT_EVIDENCE` states.

Required reconciliations include:

```text
Assets = Liabilities + Equity
Opening cash + CFO + CFI + CFF = Closing cash
Opening debt + Drawdowns + Accrued interest - Principal paid - Writeoffs = Closing debt
Opening gross assets + Additions - Disposals = Closing gross assets
Opening accumulated depreciation + Depreciation - Disposals = Closing accumulated depreciation
Revenue schedule total = Income statement revenue
Payroll schedule total = Income statement payroll and capitalized payroll
```

### 9. Monte Carlo Core Capability

#### 9.1 Mandatory Headline KPI

The Project Dashboard shall always show `MC_FEASIBILITY_GATE_PROBABILITY`, or `NOT_READY` when evidence cannot support simulation.

```text
P_pass = valid simulations satisfying every applicable approved gate
         / total valid simulations
```

It shall be labelled in Arabic as `احتمال اجتياز شروط الجدوى` and never as an unconditional probability of project success.

Applicable gates may include positive NPV, approved return hurdle, liquidity sufficiency, covenant DSCR, schedule/cost tolerance, and critical technical thresholds. Non-applicable gates are excluded explicitly, never treated as passed.

#### 9.2 Simulation Inputs

Depending on sector and materiality, candidates include demand, price, volume, ramp-up, churn, yield, waste, COGS, CapEx, construction duration, launch delay, utilization, DSO/DIO/DPO, interest, inflation, FX, downtime, maintenance, replacement, and terminal value.

Every stochastic input requires an evidence-backed or human-approved distribution, parameters, bounds, rationale, owner, and review date. Correlations shall be documented and the correlation matrix validated. AI may suggest questions but cannot approve a distribution or correlation.

#### 9.3 Reproducibility and Convergence

Each run shall store seed, engine version, random generator, input snapshot, distribution catalog version, correlation matrix, requested and valid iterations, rejected iterations, convergence diagnostics, and run duration.

The engine shall begin with a configured minimum iteration count and continue or warn based on convergence tolerances for the headline probability and material percentiles. A fixed iteration count alone is not evidence of stability. Tail metrics require stricter convergence or an explicit low-confidence warning.

#### 9.4 Required Outputs

- feasibility-gate probability;
- probability NPV is positive;
- P10/P50/P90 for NPV and funding need;
- probability and timing of cash shortfall;
- probability of cost and schedule overrun when modelled;
- covenant breach probability when debt exists;
- key drivers and rank correlations;
- distribution and convergence diagnostics;
- a clear uncertainty and evidence caveat.

### 10. FSP v3.1 / FSDP

#### 10.1 Fixed Personas

| Persona | Sovereign question | Persistent KPI |
| --- | --- | --- |
| Project Manager | Can this be implemented correctly? | Execution Readiness Index |
| Business Advisor | Will the market pay? | Commercial Acceptance Index |
| Technical Auditor | How can the system fail technically? | Technical Robustness Index |
| Analyst Coach | What is the next practical step? | Transition Readiness Index |
| Resistance Test | Will it survive pressure? | Pressure Survival Index |

Persona KPIs are computed by deterministic evaluators from approved gates and evidence. AI personas explain and challenge those results; they do not invent scores.

#### 10.2 Isolation and Order

Each persona sees raw approved project data, deterministic outputs, and approved evidence needed for its role. It shall not read, reference, or infer another persona's result during its run.

```text
Project Manager
-> Business Advisor
-> Technical Auditor
-> Analyst Coach
-> Resistance Test
-> Sovereign Verdict
```

The synthesizer shall not run until all five outputs are schema-valid. Voting is forbidden. Every persona output requires judgement, evidence, reasons, confidence, confidence explanation, exactly one success metric, practical next action or validation requirement, and what would change the judgement.

### 11. KPI-First Project Dashboard

The first page is a decision surface, not a report and not an architecture diagram.

#### 11.1 Permanent Summary Band

- Sovereign Verdict status;
- Monte Carlo feasibility-gate probability;
- Evidence Confidence status.

#### 11.2 Permanent Persona Band

The five persona KPIs are always visible in one compact row or responsive strip. Before completion they display `PENDING`; when a KPI is not applicable, they display `NOT_APPLICABLE` with a drill-down reason.

#### 11.3 Adaptive Project Band

Display five to seven decision KPIs selected by the routed model. Candidate KPIs include total investment, funding gap, minimum cash, break-even date, payback, revenue, EBITDA, net cash flow, NPV, IRR/MIRR, DSCR, LLCR, utilization, and schedule readiness.

A metric shall appear only when it is defined, applicable, traceable, and decision-relevant. `IRR` shall be suppressed or marked invalid when cash-flow sign patterns make it unreliable.

#### 11.4 UI Rules

- Minimal text; label, value, unit, status, and small context only.
- No large tables, long narratives, formulas, or methodology text on the first page.
- Every KPI opens its lineage, assumptions, formula version, and detailed analysis.
- Mock or synthetic results carry a visible `DEMO_DATA` badge.
- Dashboard renders state and dispatches typed actions only.
- Dashboard never calculates, validates sources, calls AI/providers, or generates reports directly.

### 12. Project Workspace

Project Workspace shall provide one-click access to:

1. `Overview`: headline, persona, and adaptive KPIs.
2. `Market`: market evidence, competitors, demand, pricing, and global benchmarks.
3. `Technical`: site, capacity, process, equipment, utilities, staffing, implementation, quality, and HSE.
4. `Financial`: assumptions, schedules, statements, investment appraisal, financing, and reconciliations.
5. `Risk & Monte Carlo`: scenarios, sensitivity, switching values, stress, simulation, distributions, drivers, and convergence.
6. `Five Personas`: isolated judgements, evidence, confidence, next actions, and change conditions.
7. `Evidence & Assumptions`: complete provenance, quality, freshness, and human approvals.
8. `Reports`: Excel, PDF, PowerPoint, status, version, and immutable snapshot ID.

### 13. Reports

#### 13.1 Excel

Excel shall open with an executive KPI summary containing Sovereign Verdict, Monte Carlo, the five persona KPIs, and the routed project KPIs. It shall also include inputs, evidence register, sector schedules, revenue, COGS, OpEx, CapEx, depreciation, leases, workforce, working capital, debt, tax/zakat/VAT outputs, statements, appraisal, scenarios, Monte Carlo outputs, persona details, checks, and formula catalog references.

Exported formulas may be transparent and protected, but the backend snapshot remains authoritative. The workbook shall reconcile to the snapshot and display pass/fail checks.

#### 13.2 PDF

PDF shall provide the professional written study. Its executive opening shall contain Sovereign Verdict, Monte Carlo, all five persona KPIs, and routed project KPIs before the written sections: scope, methodology, data quality, market, technical, operational, financial, risk, Monte Carlo, personas, recommendations, conditions, assumptions, limitations, and appendices.

#### 13.3 PowerPoint

PowerPoint shall start with KPIs, Sovereign Verdict, Monte Carlo, and the five persona indicators, followed by market, financial, technical, risks, scenarios, recommendations, and next actions. It must not become a text-heavy copy of the PDF.

#### 13.4 Snapshot Integrity

Every UI and report output shall share:

- `calculation_run_id`;
- `project_snapshot_id`;
- `formula_catalog_version`;
- `rule_pack_version`;
- `evidence_snapshot_hash`;
- `monte_carlo_run_id` and seed when applicable;
- `persona_run_ids`;
- `generated_at` and locale.

### 14. Subscription Entitlements

Subscriptions may control collaboration seats, scenario count, evidence retrieval depth, benchmark breadth, Monte Carlo diagnostics, portfolio views, custom templates, and export formats.

Subscriptions shall never hide or alter:

- calculation correctness;
- critical data-quality warnings;
- funding gap or cash-shortfall risk;
- model invalidity or failed reconciliation;
- Monte Carlo headline status/KPI;
- the five persona KPI statuses;
- material assumptions and limitations;
- the reason a final feasibility status is blocked.

### 15. Security, Audit, and Failure

All requests require security context, project authorization, Contract ID, Socket ID, correlation ID, source/target identity, idempotency key where relevant, and audit timestamp.

Failure shall be explicit and fail closed for:

- missing or unauthorized Contract;
- invalid project access;
- missing critical inputs;
- stale or invalid Saudi rule pack;
- failed financial reconciliation;
- unsupported currency/period conversion;
- invalid stochastic distribution or correlation matrix;
- non-converged simulation without approved caveat;
- persona isolation violation;
- report/snapshot mismatch;
- direct Module or provider bypass.

### 16. Non-Goals

- No automated claim that a project is government approved.
- No replacement for licensed legal, accounting, engineering, or investment advice.
- No copying of proprietary research tools or databases.
- No AI-generated financial values, decisive scores, distributions, or final verdicts.
- No generic Gulf rule set.
- No direct frontend ownership of platform logic.
- No report engine recalculation.

### 17. Definition of Done

The implementation is accepted only when:

1. every required Contract and Socket is explicit and versioned;
2. all financial schedules reconcile;
3. Monte Carlo is reproducible, evidence-backed, correlated, and convergence-checked;
4. all five persona KPIs are deterministic and persona runs remain isolated;
5. the first page contains compact KPIs only;
6. Project Workspace exposes every detailed table and report easily;
7. Excel, PDF, PowerPoint, and UI match one immutable snapshot;
8. subscription cannot suppress critical truth;
9. AI cannot create or modify a decisive number or final verdict;
10. every blocking acceptance test passes.
