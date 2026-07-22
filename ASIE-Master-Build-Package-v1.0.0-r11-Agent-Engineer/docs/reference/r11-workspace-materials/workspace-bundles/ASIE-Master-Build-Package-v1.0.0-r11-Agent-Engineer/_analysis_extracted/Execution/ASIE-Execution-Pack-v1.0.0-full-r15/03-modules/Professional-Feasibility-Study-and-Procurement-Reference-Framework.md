# Professional Feasibility Study and Procurement Reference Framework

## إطار دراسة الجدوى الاحترافية ومراجع المنافسات والمشتريات

**Status:** Mandatory for ASIE r15  
**Country scope:** Saudi Arabia  
**Verified:** 2026-07-13  
**Profiles:** `professional_feasibility_v1`, `official_procurement_reference_v1`, `commercial_methodology_reference_only_v1`

## 1. Decision

ASIE does not treat feasibility as a free template, a questionnaire, or a decorative report. A professional feasibility study is a structured decision process that integrates project definition, market evidence, technical and operational design, organization, regulation, finance, economic/impact analysis where applicable, uncertainty, risk, implementation, and decision conditions.

لا تتعامل ASIE مع دراسة الجدوى كنموذج خانات مجاني أو تقرير رسومي. الدراسة الاحترافية عملية قرار مترابطة يتغير عمقها حسب حجم المشروع وقطاعه ومرحلته والغرض منها.

This framework creates no new ASIE Module, Layer, Controller, Bus, Heart, or truth owner. Existing Modules own their outputs under AAS.

## 2. Authority and Methodology Classes

| Class | Arabic | Meaning | Can create numeric evidence? |
| --- | --- | --- | --- |
| `SAUDI_BINDING_REQUIREMENT` | متطلب سعودي ملزم | Exact applicable law, regulation, tender document, contract form, official instruction, or authority decision | Only when the exact document defines the value/rule |
| `OFFICIAL_PROCUREMENT_REFERENCE` | مرجع رسمي للمنافسات | Ministry of Finance or Etimad page/form used for a specific government-competition workflow | No project forecast by itself |
| `OFFICIAL_OPEN_DATA` | بيانات رسمية مفتوحة | Exact eligible dataset/API under `strict_open_data_only_v1` | Yes, within dataset scope and transformations |
| `INTERNATIONAL_METHOD_REFERENCE` | مرجع منهجي دولي | UNIDO, World Bank, IFC, Green Book, or another approved institutional guide | No; informs ASIE-authored methodology |
| `COMMERCIAL_METHOD_REFERENCE` | مرجع منهجي تجاري | Public commercial site used only to understand service categories or market practice | No; reference-only |
| `ASIE_DETERMINISTIC_MODEL` | نموذج ASIE حتمي | Versioned formula and decision logic owned by ASIE | Yes, from approved inputs |
| `ANALYTICAL_FRAMEWORK` | إطار تحليلي | SWOT, PESTEL, Porter, BMC, VPC, options analysis, stakeholder map | No automatic numeric authority |
| `AI_ADVISORY` | استشارة ذكاء | Evidence-bound explanation, drafting, challenge, classification, and missing-question assistance | Never creates finance or evidence numbers |

Authority order for a specific project:

1. Applicable Saudi law/regulation and exact authority requirement.
2. Exact competition/tender/contract documents when the project enters a government competition.
3. Approved official open data and user/document evidence.
4. ASIE deterministic algorithms and sector templates.
5. Approved international methodology cards.
6. Approved commercial methodology cards.
7. AI advisory explanation.

No lower class may override a higher class.

## 3. Feasibility Depth Profiles

Profile selection is deterministic under `FST-ALG-01`; AI may recommend questions but cannot select or downgrade the binding profile.

| Profile | Arabic | Typical use | Minimum depth |
| --- | --- | --- | --- |
| `MICRO_STARTER` | مشروع فردي أو مصغر | Early idea, self-employment, low-complexity local service | Market validation, technical basics, operating plan, baseline finance, break-even, risks, 12-24 month cash view |
| `SME_STANDARD` | منشأة صغيرة أو متوسطة | New or expanding SME | Full market/technical/operational/organization/legal/finance, 36-60 month forecast, sensitivity, scenarios, implementation |
| `CORPORATE_ADVANCED` | شركة كبيرة | New business line, acquisition, major expansion | Options analysis, integrated statements, governance, funding, tax/legal review gates, MCMC, stress, portfolio dependencies |
| `MEGA_PROJECT` | مشروع ضخم | Capital-intensive, infrastructure, industrial, multi-party | Full technical engineering basis, procurement, financing, economic/impact analysis, ESG, stakeholder, phased gates, independent review |
| `GOVERNMENT_COMPETITION` | منافسة حكومية | Bid, framework agreement, qualification, government contract | Exact tender/contract/form requirements, qualification, pricing moderation, operating data, compliance matrix, bid/no-bid gate |

Selection signals include project stage, legal form, sector, capital intensity, funding structure, public impact, contract type, technical novelty, data sensitivity, geographic scale, stakeholder count, and government-competition status. Monetary thresholds are policy configuration, not hard-coded universal facts.

## 4. Professional Study Chapters

Every chapter has `required`, `conditional`, or `not_applicable` state with reason. A chapter cannot disappear silently.

### 4.1 Executive and Decision Summary

- Project identity, sponsor, location, sector/subsector, stage, legal form, study purpose, and decision date.
- Problem/opportunity, proposed solution, alternatives, target beneficiaries/customers, and intended outcomes.
- Funding need, headline financial/economic results, principal risks, readiness, decision, conditions, and next gate.
- Scope, exclusions, limitations, evidence cut-off date, and responsible reviewers.

The summary is generated last from approved outputs and never introduces a new claim.

### 4.2 Project Definition and Strategic Case

- Objectives that are specific, measurable, time-bound, and connected to the identified problem.
- Scope and boundaries: products/services, geography, capacity, time horizon, inclusions, exclusions.
- Strategic fit, sponsor capability, dependencies, constraints, and success criteria.
- Options: do-nothing/without-project case, minimum option, preferred option, and credible alternatives.
- National alignment uses approved ASIE-authored reference cards only and does not imply government endorsement.

### 4.3 Market and Commercial Study

- Market definition by offering, customer, geography, channel, period, and currency.
- Demand drivers, historical indicators, forecast method, seasonality, adoption constraints, and uncertainty.
- Supply, competitors, substitutes, concentration, capacity, entry barriers, and likely reactions.
- Customer segments, jobs/pains/gains, willingness/ability to pay, buying cycle, and acquisition channels.
- Price architecture, normalized samples, discounts, taxes, contract terms, and price elasticity where evidence permits.
- TAM/SAM/SOM only with explicit definitions, sources, and method.
- Sales volume/ramp assumptions mapped to evidence or approved assumptions.
- Commercial strategy: positioning, channels, partnerships, sales process, retention, and service levels.

SWOT, PESTEL, Porter Five Forces, BMC, and VPC are mandatory analytical tools when applicable, but their statements remain facts, calculations, assumptions, or judgments with evidence labels.

### 4.4 Technical Study

- Product/service specification and required quality/service level.
- Capacity alternatives, utilization, bottlenecks, yield, scrap/loss, and scalability.
- Technology selection, maturity, interoperability, vendor dependence, cybersecurity, and obsolescence.
- Site/location alternatives, access, utilities, logistics, zoning, climate, and expansion.
- Process flow, equipment, tools, bill of quantities, layout, inputs/raw materials, utilities, and maintenance.
- Build/buy/lease/outsource decisions and technical acceptance criteria.
- CapEx basis, supplier quotations, contingencies, lead times, and useful life.
- Required licenses, technical standards, inspections, and commissioning.

Technical assumptions must not be converted to costs until Finance Engine receives an approved quantity, unit, price basis, currency, tax treatment, date, and source/assumption reference.

### 4.5 Operational Study

- Operating model, opening hours, service capacity, workflow, inventory, maintenance, quality, and business continuity.
- Supply chain, supplier qualification, logistics, storage, reorder policy, and concentration risk.
- Staffing plan by role, shift, skills, Saudization/sector requirements, recruitment lead time, training, and payroll basis.
- Systems, data, integrations, support, incident, backup, recovery, and service management.
- Operating KPIs, control points, SOP requirements, and escalation paths.
- Ramp-up plan from pilot to steady state.

### 4.6 Organizational and Governance Study

- Ownership, governance bodies, decision rights, delegated authorities, and conflict management.
- Organization structure, accountability matrix, key-person dependence, and succession.
- Delivery model, PMO/project governance where appropriate, assurance, change control, and reporting.
- Partners, contractors, advisors, and service providers with scope and accountability.

### 4.7 Legal, Regulatory, Tax, and Compliance Study

- Legal entity, activity classification, licenses, permits, sector regulator, municipality, labor, consumer, competition, data/privacy, cybersecurity, tax/ZATCA, environmental, and contract requirements as applicable.
- Exact law/regulation/control references, version/date, applicability, owner, evidence, gap, and remediation.
- Items requiring a licensed lawyer, accountant, tax advisor, engineer, auditor, or regulator are marked `professional_review_required`.
- ASIE does not issue legal, tax, engineering, cybersecurity, or government certification.

### 4.8 Environmental, Social, Health, Safety, and Impact Study

- Environmental and social screening proportionate to project type and applicable Saudi requirements.
- Resource use, emissions, waste, water, energy, land, community, labor, accessibility, safety, and climate resilience.
- Mitigation hierarchy, monitoring indicators, responsibilities, cost, schedule, and residual impact.
- Economic/social impact analysis is separate from private financial profitability.

### 4.9 Procurement and Contracting Study

- Procurement scope, packaging, sourcing strategy, market capacity, schedule, evaluation approach, and contract type.
- Pre/post qualification, bidder requirements, technical/financial evaluation, price moderation, guarantees, insurance, change, claims, performance measurement, acceptance, payment, and closeout.
- Exact government competition profile activates only for a real Saudi government procurement use case.
- Private projects use ASIE procurement practice without claiming Ministry of Finance approval.

### 4.10 Implementation Study

- Work breakdown, milestones, dependencies, critical path, responsible owner, acceptance criterion, and evidence deliverable.
- Pre-development, design, permits, procurement, build/configuration, testing, commissioning, launch, stabilization, and handover.
- Schedule basis, resource loading, contingency, long-lead items, and stop/go gates.
- 30/60/90-day view is optional; project-specific phases govern.

### 4.11 Financial Study

- Input book with source, assumption, unit, currency, date, tax, period, scenario, and confidence basis.
- Startup uses, CapEx, pre-opening costs, working capital, financing fees, contingencies, and reserves.
- Revenue drivers: price, volume, capacity, utilization, conversion, churn/retention, mix, seasonality, contract ramp, and collection terms.
- OpEx: fixed/variable/semi-variable, staffing, rent, utilities, maintenance, technology, logistics, marketing, professional fees, insurance, compliance, and overhead allocation.
- Integrated income statement, cash-flow statement, and balance-sheet schedule where the selected profile requires them.
- Depreciation/amortization, receivables, inventory, payables, VAT/tax assumptions, financing, and distributions.
- Break-even, margins, working capital, cash conversion cycle, funding need, runway, and covenant headroom.
- NPV, IRR, MIRR, profitability index, payback, discounted payback, ROI, DSCR, and LLCR only when applicable and fully parameterized.
- Unit economics for recurring/digital models: contribution margin, CAC, LTV, LTV/CAC, CAC payback, churn, retention, MRR, ARR, NRR, and cohort basis.

### 4.12 Economic and Cost-Benefit Study

Conditional for public, infrastructure, social-impact, policy, or major externality projects.

- Define with-project and without-project cases.
- Identify incremental economic costs and benefits, transfers, externalities, distribution, beneficiaries, and displaced activity.
- Distinguish market/financial prices from economic values.
- Define appraisal period, residual value, discount rate, price basis, inflation, and shadow-price/conversion assumptions.
- Calculate economic NPV, economic IRR, benefit-cost ratio, distributional and non-monetized impacts where supportable.
- A positive financial return does not prove positive economic value, and vice versa.

### 4.13 Risk, Uncertainty, and Resilience

- Risk register and 5x5 matrix with cause-event-impact structure.
- One-way and multi-way sensitivity.
- Baseline, upside, downside, and stress scenarios with explicit changed variables.
- Break-even thresholds and switching values.
- Fixed-seed MCMC under `FIN-ALG-04` and `FIN-ALG-12` when approved distributions and ranges exist.
- Model risk, evidence risk, bias, optimism, correlation, tail risk, and black-swan limitations.
- Mitigation, contingency, leading indicators, trigger, owner, and residual risk.

### 4.14 Recommendation and Gate Decision

Allowed outcomes:

- `PROCEED`.
- `PROCEED_WITH_CONDITIONS`.
- `PILOT_FIRST`.
- `REVISE_AND_REASSESS`.
- `HOLD`.
- `NO_GO`.
- `BLOCKED_MISSING_EVIDENCE`.
- `BLOCKED_COMPLIANCE`.

The decision includes conditions, owners, evidence to obtain, expiry/review date, dissent, and re-evaluation triggers. It is not based on a single score.

## 5. Depth Matrix

| Chapter | Micro | SME | Corporate | Mega | Government competition |
| --- | --- | --- | --- | --- | --- |
| Executive/strategic | Required | Required | Required | Required | Required + bid/no-bid |
| Market/commercial | Focused | Full | Advanced | Advanced | Contract-demand and competitor/bid market |
| Technical | Basics | Full | Advanced | Engineering basis + independent review | Exact specification compliance |
| Operational | Basics | Full | Full | Full + resilience | Operating data and performance obligations |
| Organization/governance | Owner roles | Structure | Governance/RACI | Multi-party governance | Bid team, authority, subcontractor controls |
| Legal/regulatory | Screening | Full | Full | Independent review | Exact system/tender/contract compliance |
| ESG/impact | Screening | Conditional | Required by risk | Full | As tender/applicable rules require |
| Financial horizon | 12-24 months | 36-60 months | Life/strategy horizon | Project life | Contract period + obligations |
| Integrated statements | Conditional | Recommended | Required | Required | As form/financing requires |
| Sensitivity/scenarios | Required | Required | Required | Required | Required for bid resilience |
| MCMC | Optional | Conditional | Recommended | Required when material uncertainty supports it | Conditional; never replaces bid rules |
| Economic CBA | Not typical | Conditional | Conditional | Required for public/impact case | Conditional to authority requirement |
| Procurement | Simple sourcing | Full sourcing | Strategic sourcing | Full contracting strategy | Exact official profile |

## 6. Saudi Official Procurement Reference Catalog

These pages are official, public reference indexes for the Saudi government procurement context. They are not open datasets and do not become general feasibility templates.

| ID | Reference | Canonical URL | Verified scope | ASIE status |
| --- | --- | --- | --- | --- |
| `PROC-REF-MOF-CONTRACTS` | Ministry of Finance Contracts and Projects / العقود والمشاريع | `https://www.mof.gov.sa/docslibrary/ContractsProjects/Pages/default.aspx` | Official digital-library index for contracts/projects | Official procurement reference |
| `PROC-REF-MOF-TERMS` | Tender Terms and Specifications Forms / نماذج كراسات الشروط والمواصفات | `https://www.mof.gov.sa/Knowledgecenter/newGovTendandProcLow/Pages/Terms_Conditions.aspx` | Official forms for tender books and specifications | Official procurement reference |
| `PROC-REF-MOF-OPDATA` | Operational Data Forms / نماذج البيانات التشغيلية | `https://www.mof.gov.sa/Knowledgecenter/newGovTendandProcLow/Pages/OperatiionData.aspx` | Categories including technology, medical, consulting/training, catering, O&M, supplies, vehicles, capital projects, roads, and city cleaning | Official procurement reference |
| `PROC-REF-MOF-FORMS` | Government Tender and Procurement Forms / النماذج | `https://www.mof.gov.sa/Knowledgecenter/newGovTendandProcLow/Pages/forms.aspx` | Electronic tender-book filling, terms/specifications, framework agreements, contractor evaluation, qualification, price moderation, operational data, arbitration, tender launch, contracts, award decisions | Official procurement reference |
| `PROC-REF-ETIMAD-CONTENT` | Etimad Competition Content / محتوى المنافسات والمشتريات | `https://etimad.sa/LandingPage/CompetationContent` | System/regulations, guidance, qualification, contractor evaluation, and terms/specification forms by contract type | Official procurement reference |

### Storage policy

ASIE may store in `official_reference_registry`:

- Official title, issuer, canonical URL, document/form category, discovered download URL, last reviewed date, reviewer, applicability, supersession status, and cryptographic hash of an authorized snapshot.
- An exact downloaded form only in a controlled document vault when its official download path, internal purpose, terms review, retention, access, and non-redistribution decision are documented.
- Normalized ASIE requirement cards written in original language by an authorized reviewer.

ASIE must not:

- Crawl the Ministry/Etimad domain or download all forms in bulk.
- Assume every linked file is current or applicable.
- Publicly republish or modify official forms.
- Send raw forms to an external AI provider without a documented lawful basis and security/privacy approval.
- Use a form from one contract type for another.
- claim that a private feasibility study is Ministry-approved merely because it uses an ASIE checklist informed by these references.

For a real competition, the exact competition document published for that procurement remains controlling over a generic library form.

## 7. International Methodology Reference Catalog

These sources support ASIE-authored professional methodology. They are references, not copied templates and not Saudi legal authority.

| ID | Institution/reference | URL | ASIE use |
| --- | --- | --- | --- |
| `METH-REF-UNIDO-FS` | UNIDO Manual for the Preparation of Industrial Feasibility Studies | `https://www.unido.org/sites/default/files/files/2021-02/manual_for_the_preparation_of_industrial_feasibility_studies.pdf` | `reference_pending_revalidation`: endpoint returned HTTP 502 during the 2026-07-13 check; no card activation until an authorized human revalidates issuer, document, rights and availability |
| `METH-REF-WB-EAIO` | World Bank Economic Analysis of Investment Operations | `https://documents1.worldbank.org/curated/en/792771468323717830/pdf/298210REPLACEMENT.pdf` | Financial/economic distinction, alternatives, incremental costs/benefits, externalities, sensitivity/risk |
| `METH-REF-IFC-FS` | IFC Feasibility Studies and Project Planning | `https://www.ifc.org/content/dam/ifc/doc/mgrt/parttwo-feasibilitystudies.pdf` | Stakeholders, regulatory/financing requirements, planning proportionality |
| `METH-REF-UK-GREENBOOK` | UK Green Book 2026 | `https://www.gov.uk/government/publications/the-green-book-appraisal-and-evaluation-in-central-government` | Options, costs, benefits, risks, evidence-based appraisal; reference only outside UK authority |

An authorized human curator writes original ASIE methodology cards. AI receives those cards, not copied source pages or manuals.

## 8. Commercial Methodology Reference: Aljdwa

| Field | Value |
| --- | --- |
| ID | `COMM-METH-REF-ALJDWA` |
| Official name | Aljdwa / الجدوى |
| Canonical URL | `https://www.aljdwa.com/` |
| Terms URL | `https://www.aljdwa.com/الشروط-والأحكام/` |
| Classification | Saudi commercial feasibility-services reference |
| Status | `reference_only` |
| Automated access | Blocked |
| AI direct browsing | Blocked |
| Copying/reproduction | Blocked without written permission |
| Allowed ASIE use | Outbound link, metadata, and original human-reviewed methodology card |

The reviewed terms state that content/services may not be copied, distributed, resold, or reproduced without written permission and identify platform materials as intellectual property. Therefore:

1. A human reviewer may visit the public site and record high-level service categories and an original general observation.
2. The reviewer must not copy lists, paragraphs, examples, tables, prices, reports, designs, brands, or client claims.
3. AI may use the approved original ASIE card to ask better questions or compare ASIE's own methodology coverage.
4. AI must not browse, crawl, scrape, summarize, embed, vectorize, monitor, or reproduce `aljdwa.com` content.
5. The site cannot be used as evidence for project demand, price, success probability, financial assumptions, competitor performance, or official accreditation.
6. Written permission or a valid license may be reviewed for a future controlled route; it is not active in r15.

## 9. AI Role in Advanced Feasibility

Allowed:

- Classify user narrative into the professional chapter structure.
- Generate a missing-information questionnaire from approved templates.
- Draft evidence-bound SWOT, PESTEL, Porter, BMC, and VPC items.
- Challenge assumptions, identify contradictions, draft scenarios, and propose risk hypotheses.
- Explain deterministic financial/economic outputs and simulation distributions.
- Draft the executive summary, recommendations, implementation narrative, and investor narrative from approved output IDs.
- Compare study completeness against approved ASIE methodology cards.

Forbidden:

- Generate prices, volumes, costs, discount rates, probabilities, tax rates, market sizes, or forecast values.
- Mark an assumption as verified.
- Select a favorable scenario as expected without deterministic policy.
- Issue legal, engineering, tax, cybersecurity, procurement, investment, or government approval.
- Read blocked/reference-only source content directly.
- Copy methodology text or recreate a competitor's report structure.
- Hide dissent, missing evidence, downside outcomes, or model limitations.

## 10. Platform Placement

| Platform location | Function |
| --- | --- |
| Project Wizard > Study Purpose | Select investment, expansion, financing, internal decision, impact, or government competition purpose |
| Project Wizard > Depth Profile | Deterministic profile selection with explanation and blocked downgrade |
| `/projects/:projectId/feasibility` | Integrated chapter navigator, completeness, gates, evidence, and decision |
| `/projects/:projectId/technical` | Capacity, site, technology, process, equipment, staffing, operations, and technical risks |
| `/projects/:projectId/procurement` | Conditional procurement strategy and official government-competition compliance matrix |
| Finance | Integrated statements, appraisal, funding, working capital, unit economics, sensitivity, scenarios, MCMC |
| Risks | Risk register, switching values, stress, resilience, model/evidence risk |
| Evidence | Source, assumption, model, methodology-card, official-form, version, and review registry |
| Admin > Methodology Registry | International/commercial cards, original-writing review, expiry, access status |
| Admin > Official Procurement Registry | MOF/Etimad metadata, exact forms, version/applicability, authorized snapshots, supersession |
| Reports | Profile-specific professional feasibility report and controlled government-competition appendix |

## 11. Required Data Records

- `feasibility_study_profiles`.
- `feasibility_chapter_requirements`.
- `feasibility_chapter_states`.
- `feasibility_options`.
- `technical_capacity_models`.
- `operating_models`.
- `financial_model_inputs`.
- `financial_statement_runs`.
- `investment_appraisal_results`.
- `economic_analysis_results`.
- `procurement_reference_registry`.
- `official_form_versions`.
- `methodology_reference_registry`.
- `methodology_cards`.
- `methodology_review_events`.

Database records remain persistence, not architectural authority.

## 12. Stop Conditions

Stop the study or affected chapter when:

- Required evidence, unit, period, geography, currency, source, or assumption approval is missing.
- Technical capacity and commercial demand are inconsistent.
- A financial forecast exceeds approved capacity without a phased expansion record.
- A formula, discount rate, distribution, correlation, or benchmark is missing.
- A government competition lacks its exact competition documents.
- A generic MOF/Etimad form is treated as the controlling tender document.
- An official form is stale, superseded, or from the wrong contract type.
- AI or a commercial site supplies a number.
- Aljdwa content is requested for automated access, copying, embedding, or monitoring.
- A report claims government, Ministry, Etimad, UNIDO, World Bank, IFC, or Green Book approval/endorsement.

## 13. Acceptance Requirements

1. The selected depth profile is reproducible and cannot be downgraded to hide required analysis.
2. Every professional chapter has state, owner, evidence requirements, and completion gate.
3. Market demand, technical capacity, operating resources, and financial volume reconcile.
4. Integrated statements balance where required.
5. Investment appraisal formulas use explicit conventions and versions.
6. Economic CBA is separate from private financial analysis.
7. Monte Carlo remains fixed-seed, range/distribution/correlation controlled, and reproducible.
8. The exact government competition document overrides generic references.
9. Ministry/Etimad references are exact, versioned, reviewed, and not bulk crawled.
10. Aljdwa is reference-only; AI uses only an approved original ASIE methodology card.
11. Arabic/English outputs preserve source identity and use original ASIE prose.
12. No methodology or source becomes an architectural authority or bypasses Contracts.
