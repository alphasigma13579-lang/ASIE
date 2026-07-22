# Advanced Feasibility and Investment Appraisal Algorithms

## خوارزميات دراسة الجدوى والتقييم الاستثماري المتقدم

**Status:** Mandatory for ASIE r15  
**Architecture:** Existing Modules only; no new Module, Layer, Controller, Bus, Heart, or truth owner  
**Numeric authority:** `Finance Engine`  
**AI authority:** None over facts, assumptions, formulas, rates, distributions, weights, or decisions

## Shared Rules

1. Every number has an owner, unit, currency, period, price basis, tax basis, source or approved assumption, formula version, run ID, and timestamp.
2. Nominal cash flows use nominal discount rates; real cash flows use real discount rates. Mixing bases is blocked.
3. Financial analysis, economic cost-benefit analysis, and procurement compliance are separate outputs.
4. `SWOT`, `PESTEL`, `Porter Five Forces`, `BMC`, and `VPC` structure analysis; they do not create evidence or financial values.
5. AI may explain approved results or draft original prose. AI cannot invent inputs, choose ranges, approve evidence, or issue the final decision.
6. All cross-Module messages pass through APP, ASIE System Bus, Socket Contract Layer, and Bus Controller governance.

## FST-ALG-01 Feasibility Depth Profile Selection

**Owner:** Project Wizard, using Admin-approved policy  
**Purpose:** Select the minimum study depth without allowing a user to hide required analysis.

Inputs:

- Project purpose, stage, legal form, sector/subsector, geography, capital requirement, financing route, asset intensity, regulatory exposure, environmental/social exposure, public-procurement intent, and decision audience.

Profiles:

| Profile | Intended use | Mandatory minimum |
| --- | --- | --- |
| `MICRO_STARTER` | Early individual or micro-enterprise screen | Project, market, operating, simplified finance, risk, decision limits |
| `SME_STANDARD` | Finance-ready SME decision | Full market, technical, operating, organization, legal, implementation, integrated finance, risk |
| `CORPORATE_ADVANCED` | Board/investor/corporate case | Alternatives, governance, integrated statements, funding, sensitivity, stress and MCMC where material |
| `MEGA_PROJECT` | Capital-intensive or multi-stakeholder case | Full professional chapters, economic/impact analysis where applicable, assurance and stage gates |
| `GOVERNMENT_COMPETITION` | Response to a Saudi government competition | Corporate/mega depth plus exact competition document and current MOF/Etimad procurement-reference controls |

Rules:

- Public competition intent forces `GOVERNMENT_COMPETITION`.
- A lower profile may be upgraded automatically by deterministic policy.
- Downgrade requires authorized human approval, reason, residual-risk acceptance, and cannot suppress a legally or financially required chapter.

Outputs: `feasibility.study.profile.selected.v1` or `feasibility.study.profile.blocked.v1`.

## FST-ALG-02 Study Chapter Completeness Gate

**Owner:** Decision Council, consuming owner-Module chapter states  
**Purpose:** Prevent a polished report from masking missing analysis.

Mandatory chapter states:

`not_started | needs_input | in_progress | ready | insufficient_data | blocked | stale | not_applicable`

For each chapter validate:

- Profile applicability and documented `not_applicable` reason.
- Responsible owner Module and reviewer.
- Required inputs, evidence coverage, assumptions, outputs, limitations, and validation status.
- Links to unresolved contradictions, stale evidence, and decision conditions.

Decision:

- `ready` only when every required chapter is ready and cross-study reconciliation passes.
- Any required `blocked`, `stale`, or `insufficient_data` state prevents an unqualified recommendation.
- Missing data remains visible; it is never converted to zero or hidden.

## FST-ALG-03 Cross-Study Reconciliation

**Owner:** Decision Council; each source value remains owned by its producing Module  
**Purpose:** Reconcile market, technical, operating, people, procurement, implementation, and finance assumptions.

Checks:

1. Forecast sales volume must not exceed demand evidence, practical capacity, channel capacity, or approved ramp-up.
2. Production/service capacity must reconcile with equipment, shifts, labor, yield, downtime, inventory, and implementation date.
3. Headcount, salaries, utilization, procurement lead times, and operating costs must match the operating plan.
4. CapEx commissioning dates must precede related revenue and depreciation.
5. Financing drawdowns must cover eligible uses and timing; interest and fees must reconcile with debt schedules.
6. Scenario labels, horizons, currency, inflation, tax, and price bases must match across analyses.

Output: a contradiction register with severity, owners, affected outputs, and blocking status. Reports cannot resolve contradictions by rewriting text.

## FIN-ALG-06 Integrated Financial Statement Builder

**Owner:** Finance Engine  
**Purpose:** Build monthly/quarterly/annual income statement, cash flow, and balance sheet from one controlled assumption set.

Core calculations:

```text
Revenue = sum(volume_i * net_price_i)
Gross Profit = Revenue - Cost of Sales
EBITDA = Gross Profit - Operating Expenses
EBIT = EBITDA - Depreciation - Amortization
EBT = EBIT - Net Finance Cost
Net Income = EBT - Tax - Zakat adjustments according to reviewed applicability
Ending Cash = Beginning Cash + Operating CF + Investing CF + Financing CF
Assets = Liabilities + Equity
```

Controls:

- Revenue recognition, VAT, Zakat/tax, depreciation, amortization, leases, capitalization, and foreign exchange use approved policy versions.
- Tax/Zakat applicability is a reviewed input, not an AI inference or legal conclusion.
- Retained earnings reconcile to prior retained earnings plus distributable result and approved distributions.
- Balance-sheet difference above configured rounding tolerance blocks the run.
- Cash-flow closing cash must equal balance-sheet cash for every period.

Outputs: `finance.integrated.statements.result.v1` plus reconciliation exceptions.

## FIN-ALG-07 Investment Appraisal

**Owner:** Finance Engine  
**Purpose:** Compute private investment returns under explicit conventions.

```text
NPV = sum(t=0..n, CF_t / (1 + r)^t)
PI = PV(future net cash flows) / absolute(initial investment)
MIRR = (FV(positive CF at reinvestment rate) / -PV(negative CF at finance rate))^(1/n) - 1
```

Required conventions:

- Cash-flow perspective: project, equity, lender, or another named perspective.
- Time step, horizon, terminal-value method, discount-rate source/version, finance rate, reinvestment rate, nominal/real basis, pre/post-tax basis, and currency.
- NPV always displayed with the exact rate and perspective.
- IRR uses a deterministic root-finding policy. No root, multiple roots, or non-conventional cash flows return explicit warnings; IRR never silently replaces NPV.
- Payback and discounted payback report the first qualifying period and `not_reached` when absent.
- Mutually exclusive alternatives prioritize incremental NPV under the approved decision convention.

Outputs: NPV, IRR status/value, MIRR, profitability index, payback, discounted payback, terminal-value share, and limitations.

## FIN-ALG-08 Working Capital and Funding Requirement

**Owner:** Finance Engine

```text
Receivables = credit_revenue * DSO / days_in_period
Inventory = eligible_cost_base * DIO / days_in_period
Payables = eligible_purchase_base * DPO / days_in_period
Net Working Capital = Receivables + Inventory + other_current_operating_assets
                      - Payables - other_current_operating_liabilities
Cash Conversion Cycle = DSO + DIO - DPO
Funding Need = max(0, absolute(min(cumulative pre-financing cash)) + minimum_cash_buffer)
```

Rules:

- Driver definitions and eligible bases are versioned and sector-specific.
- Negative working capital is allowed when supported; it is not forced to zero.
- Funding requirement separates CapEx, pre-operating cost, working capital, financing fees, contingency, and minimum cash.
- Source/use schedule must balance for each financing close.

## FIN-ALG-09 Unit Economics and Break-Even

**Owner:** Finance Engine

```text
Contribution per Unit = Net Unit Revenue - Variable Cost per Unit
Contribution Margin % = Contribution / Net Revenue
Break-even Units = Fixed Costs / Contribution per Unit
Break-even Revenue = Fixed Costs / Contribution Margin %
CAC Payback Months = CAC / Monthly Contribution per Customer
LTV = approved cohort contribution model over approved retention horizon
```

Rules:

- Block break-even when contribution is zero/negative.
- CAC, churn, retention, ARPU, and margin definitions must be cohort- and period-consistent.
- LTV is not calculated for an inapplicable business model and never uses an infinite horizon by default.
- Display capacity utilization and time-to-break-even beside the result.

## FIN-ALG-10 Debt Service and Covenant Metrics

**Owner:** Finance Engine

```text
DSCR_t = Cash Flow Available for Debt Service_t / Debt Service_t
LLCR = NPV(CFADS over loan life at debt discount rate) / Outstanding Debt
Interest Coverage = approved earnings measure / Net Interest Expense
```

Rules:

- CFADS definition, debt service components, reserve accounts, grace periods, capitalized interest, fees, and covenant periods are explicit.
- No DSCR appears when denominator is zero or debt is absent; return `not_applicable`.
- Minimum, average, and period-by-period values are retained; averages cannot hide a covenant breach.

## FIN-ALG-11 Economic Cost-Benefit Analysis

**Owner:** Finance Engine for deterministic calculations; Decision Council owns the decision synthesis  
**Applicability:** Public, infrastructure, policy, major impact, or explicitly requested cases after methodology approval.

Required separation:

- Financial analysis uses entity cash flows and market/accounting conventions.
- Economic analysis uses the defined societal perspective, `with-project` versus `without-project` incremental flows, approved shadow/conversion factors, externalities, and distributional records.
- Taxes, subsidies, and financing flows are classified as transfers where the approved methodology requires; they are never deleted without a traceable adjustment record.

```text
ENPV = sum(t=0..n, Economic Net Benefit_t / (1 + social_discount_rate)^t)
BCR = PV(Economic Benefits) / PV(Economic Costs)
```

Outputs: ENPV, EIRR status/value, BCR, cost-effectiveness metric when benefits cannot be monetized, beneficiaries, losers, fiscal effects, non-monetized impacts, assumptions, and ethical limits.

Stop when social discount rate, perspective, counterfactual, valuation method, or material non-monetized impact is missing.

## FIN-ALG-12 Scenario, Stress, Sensitivity, and MCMC Integration

**Owner:** Finance Engine  
**Relation:** Orchestrates `FIN-ALG-03` and `FIN-ALG-04`; it does not replace them.

Analysis stack:

1. Baseline deterministic run.
2. One-variable sensitivity and switching values.
3. Coherent named scenarios with internally consistent assumptions.
4. Stress tests for severe but plausible events and covenant/liquidity effects.
5. Monte Carlo only when approved distributions and correlations are available.

MCMC requirements:

- Fixed seed, iteration count, pseudo-random generator version, variable list, units, distribution family, parameters, truncation, source/approval, and correlation matrix.
- Correlation matrix must be validated for symmetry, unit diagonal, bounds, and positive-semidefinite handling under a documented policy.
- Simulation recalculates the full approved finance model for each draw; it does not simulate the final score directly.
- Outputs include P5/P25/P50/P75/P95, expected NPV, probability NPV is below zero, funding shortfall probability, covenant breach probability where applicable, and convergence diagnostics.
- A probability is a model result under stated assumptions, never a universal probability of project success.

Forbidden:

- AI-selected ranges, distributions, correlations, weights, seed, or interpretation that changes the computed decision.
- Presenting optimistic/base/downside labels as probabilities without an approved probability model.

## PROC-ALG-01 Procurement Applicability and Reference Selection

**Owner:** Decision Council, using Audit/Observability-approved reference metadata  
**Purpose:** Decide whether the project is a private feasibility case, a government procurement response, or both.

Rules:

- A government competition requires competition ID, procuring entity, exact competition documents, submission deadline, contract type, qualification route, and official source URLs.
- MOF/Etimad general pages are official references but do not replace the exact competition booklet, addenda, answers, award criteria, or contract.
- Missing exact documents returns `procurement.exact.documents.required.v1` and blocks a compliance-ready label.

## PROC-ALG-02 Official Form Version and Applicability Gate

**Owner:** Audit / Observability with authorized procurement/legal reviewer  
**Purpose:** Validate an exact MOF/Etimad form before controlled use.

Required fields:

- Official publisher/domain, canonical URL, exact form title, document type, contract category, version/date, retrieval date, file hash, source-page hash, current/superseded status, applicable workflow, reviewer, review date, next review, storage/retention status, and competition override record.

Decision:

- `approved_reference`: current and applicable as a reference.
- `controlled_template`: exact official file approved for the named purpose in the controlled vault.
- `superseded`, `wrong_contract_type`, `exact_competition_controls`, or `review_required`: blocked for active use.

## METH-ALG-01 Methodology Reference Registration

**Owner:** Market Intelligence for metadata; Audit / Observability for approval  
**Purpose:** Register international or commercial methodology references without promoting them to Saudi authority.

Store only canonical metadata, authority class, allowed purpose, terms/rights review, approved ASIE-authored methodology card, reviewers, review dates, expiry, and disclaimers. A methodology reference cannot produce a project number or approval badge.

## METH-ALG-02 Commercial Methodology Non-Copying Guard

**Owner:** Audit / Observability  
**Purpose:** Protect third-party rights, specifically including `aljdwa.com`.

Blocked unless written permission/license explicitly allows it:

- Automated browsing, crawling, scraping, scheduled monitoring, page capture, dataset creation, copying, structural reconstruction, embeddings, vectorization, RAG ingestion, or AI summarization of Aljdwa content.

Allowed:

- Canonical URL and rights metadata.
- Human reviewer records an original high-level observation without copying protected expression or structure.
- AI consumes only a reviewed, original ASIE methodology card; it never receives the page or copied text.

Any later permission must be document-specific, purpose-specific, time-bound, revocable, and reviewed before adapter status changes.

## Required Audit Events

- Profile selection/downgrade, chapter state, contradiction, finance run, statement reconciliation, appraisal convention, economic adjustment, scenario/MCMC configuration, procurement applicability, official-form review, methodology-card approval/rejection, commercial-access block, export, and final decision.
- Audit logs contain IDs and reason codes, not secrets, hidden prompts, unnecessary personal data, or protected source content.

## Release Gate

The professional study cannot be labeled complete when a mandatory chapter, reconciliation, financial balance, exact procurement document, formula convention, source approval, or material risk treatment is missing. No output may claim Ministry, Etimad, UNIDO, World Bank, IFC, Green Book, Aljdwa, or other third-party approval or endorsement.
