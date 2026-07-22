# KIMI Implementation Prompt

## ASIE Saudi Feasibility and Decision Engine v1.0.0

```text
ROLE

You are implementing ASIE under ASIE Architecture Standard (AAS) v1.0.0 Frozen Baseline.
You are an implementation agent. You are not the architecture authority and must not reinterpret, simplify, replace, or extend AAS core architecture.

BINDING INPUTS

Read and implement all files in ASIE Saudi Feasibility Decision Pack v1.0.0:

1. README.md
2. ASIE-SA-FEASIBILITY-BUILD-SPEC-v1.0.0.md
3. ASIE-SA-FEASIBILITY-CATALOG-v1.0.0.json
4. ASIE-SA-FEASIBILITY-CONTRACTS-v1.0.0.json
5. ASIE-SA-FEASIBILITY-ACCEPTANCE-v1.0.0.json

AAS is higher authority than this implementation pack. If any ambiguity appears, stop and report it. Do not invent a new layer, Controller, Bus, Heart, source of truth, or message path.

MANDATORY STACK

- Frontend: React + TypeScript + Vite + pnpm in the Node.js ecosystem.
- Backend: Python only for API, AI integration, database access, and backend orchestration.
- Frontend-facing Contracts must be TypeScript-safe.
- Money calculations must use decimal arithmetic.

NON-NEGOTIABLE DOMAIN RULES

1. Deterministic backend code owns every financial number and decisive KPI.
2. AI explains, challenges assumptions, and writes. AI never generates financial numbers, approves distributions, creates persona scores, or owns the final verdict.
3. Monte Carlo is mandatory. The first project page always shows the probability of passing feasibility gates or NOT_READY with a reason.
4. Do not label Monte Carlo output as unconditional project success probability.
5. Five Sovereign Decision Protocols v3.1 are fixed and isolated:
   Project Manager -> Business Advisor -> Technical Auditor -> Analyst Coach -> Resistance Test -> Sovereign Verdict.
6. A persona must never read another persona output during its run.
7. Persona KPI values are deterministic; persona AI only explains them.
8. Sovereign Verdict requires all five schema-valid outputs and deterministic synthesis. Voting is forbidden.
9. The first project page is KPI-first and contains minimal text. Detailed writing, tables, formulas, schedules, and reports live in Project Workspace.
10. Excel, PDF, PowerPoint, and UI must use the same immutable calculation snapshot.
11. Subscription may change depth and exports but cannot change truth or hide critical warnings, Monte Carlo status, or persona KPI statuses.
12. Saudi official sources control Saudi regulatory claims. Global research enriches methods and benchmarks but never becomes Saudi authority.

AAS HARD RULES

- Do not bypass ASIE System Bus.
- Do not allow direct Module-to-Module communication.
- Do not run any Module without a Socket Contract.
- Do not place business logic in Kernel, Heart Controller, Three Hearts, Bus Controller, System Bus, or Socket Contract Layer.
- Do not let FastAPI, Redis, Celery, asyncio, WebSocket, Supabase, database, queue, AI provider, or other technology replace an AAS component.
- Do not let frontend call AI providers, database, storage, or internal Modules directly.
- ASIE integrates with Contracts, not technologies.

PHASE 0 - INVENTORY AND COMPLIANCE MAP

Before changing code:

1. Identify affected AAS documents and existing implementation components.
2. Map existing files to the required capabilities and Contracts.
3. Classify existing work as Keep, Wrap, Rename, Reject, or ACP.
4. Identify any direct Dashboard-to-engine, Module-to-Module, frontend-to-AI, or report recalculation path.
5. Produce the intended file plan, boundary statement, message flow, permissions, failure behavior, and tests.
6. Stop if a requested implementation would change frozen AAS responsibilities.

Do not delete or rewrite unrelated user work. Work with the current repository state.

PHASE 1 - CONTRACTS FIRST

Implement versioned schemas and types for every Contract and message in the Contract Catalog before implementing engines or UI.

Suggested targets, adapted to the existing repository without creating a competing architecture:

- packages/contracts/src/feasibility/
- packages/contracts/src/finance/
- packages/contracts/src/evidence/
- packages/contracts/src/risk/
- packages/contracts/src/decision/
- packages/contracts/src/reports/
- apps/backend/asie/modules/<approved-module-boundary>/

Every message requires the global envelope, security context, correlation/causation IDs, Contract ID, Socket ID, project ID, versions, and audit fields.

PHASE 2 - ROUTER AND SAUDI RULE PACK

Implement independent classification axes and deterministic model-depth selection.

- Location and market scope are collected first.
- Legal form, enterprise size, project complexity, sector, financing, reporting basis, subscription, and evidence readiness remain separate.
- Required model depth is the maximum required by complexity, regulation, financing, reporting, and risk.
- Insufficient subscription produces PRELIMINARY_ONLY and never a false final feasibility result.
- Saudi statutory and regulatory rules are effective-dated, source-backed, human-reviewed, and absent from frontend constants.
- A non-Saudi GCC project without an approved country pack must fail closed for regulatory calculations.

PHASE 3 - DETERMINISTIC FINANCIAL ENGINE

Implement the table and formula catalogs as versioned schedules.

Required capabilities include:

- revenue by product, channel, unit, price, ramp-up, and seasonality;
- capacity, yield, waste, and production constraints;
- CapEx, commissioning, depreciation, amortization, impairment, replacement, and disposal;
- rent and lease cash/accounting separation;
- workforce and fully loaded employee cost;
- COGS, OpEx, pre-opening, contingency, inventory, receivables, and payables;
- debt facilities, fees, interest, grace periods, repayments, covenants, DSCR, and LLCR;
- VAT, zakat, tax, grants, inflation, FX, and discount basis through approved rules;
- integrated income statement, balance sheet, and cash-flow statement;
- separate project cash flow, equity cash flow, FCFF, FCFE, and CFADS;
- NPV/XNPV, IRR/XIRR validation, MIRR, PI, payback, break-even, minimum cash, and funding gap.

Do not silently convert null to zero. Do not mix real and nominal values. Do not mix monthly and annual rates. Do not put financing inflows into FCFF. Detect multiple/no IRR roots.

Block final output when any required reconciliation fails.

PHASE 4 - EVIDENCE AND RESEARCH

Implement the assumption and evidence registries with source quality, freshness, applicability, limitations, licensing, and human review.

- Saudi official evidence controls Saudi law and regulatory claims.
- World Bank/IFC methods may support alternatives, economic analysis, sensitivity, and switching values.
- McKinsey and other approved research may support strategy, growth, market, operating model, capital excellence, organizational readiness, and digital readiness.
- Do not treat brand reputation as proof.
- Do not scrape, reproduce, or ingest proprietary tools or databases without license.
- Do not call an ASIE-created metric McKinsey OHI or imply endorsement.

PHASE 5 - SENSITIVITY, STRESS, SWITCHING VALUES, AND MONTE CARLO

Implement deterministic risk analysis against immutable financial snapshots.

Monte Carlo requirements:

- distributions and correlations require approved evidence or authorized human approval;
- validate bounds, parameter domains, and the correlation matrix;
- preserve seed, RNG, engine version, distributions, correlations, gates, iteration counts, rejected iterations, and convergence diagnostics;
- start at configured minimum iterations and evaluate convergence for the headline probability and material percentiles;
- report P10/P50/P90, positive-NPV probability, cash-shortfall probability, P90 funding need, covenant breach where applicable, key drivers, and warnings;
- exclude NOT_APPLICABLE gates explicitly;
- do not publish a numeric headline when evidence is insufficient or convergence fails without approved caveat.

The permanent headline KPI is:

P_pass = valid simulations passing all applicable approved feasibility gates / all valid simulations.

Arabic label: احتمال اجتياز شروط الجدوى.

PHASE 6 - FSDP v3.1

Implement deterministic persona KPI evaluators and isolated AI persona execution.

Permanent KPIs:

- Project Manager: Execution Readiness Index.
- Business Advisor: Commercial Acceptance Index.
- Technical Auditor: Technical Robustness Index.
- Analyst Coach: Transition Readiness Index.
- Resistance Test: Pressure Survival Index.

Each persona output requires judgement, evidence, reasons, confidence, confidence explanation, exactly one success metric, next action or validation requirement, and what would change the judgement.

The persona runner must enforce strict context isolation. The deterministic synthesizer must refuse to run with missing, invalid, duplicated, out-of-order, or cross-contaminated persona runs. Do not implement voting.

PHASE 7 - KPI-FIRST FRONTEND

Build the usable Project Dashboard as the first screen, not a marketing page.

First page:

1. Summary band: Sovereign Verdict, Monte Carlo feasibility-gate probability, Evidence Confidence.
2. Persona band: all five persona KPIs with PENDING/RUNNING/VALUE/ERROR/NOT_APPLICABLE states.
3. Adaptive band: five to seven routed financial/technical decision KPIs.

Keep text minimal. Do not place large tables, long reports, formulas, methodology, or source lists on the first page. Every KPI must open lineage and detail.

Project Workspace routes:

- Overview
- Market
- Technical
- Financial
- Risk & Monte Carlo
- Five Personas
- Evidence & Assumptions
- Reports

Dashboard components render Contract data and dispatch typed actions only. They do not own workflow or business logic.

PHASE 8 - REPORTS

Generate Excel, PDF, and PowerPoint only from an immutable approved snapshot.

- Excel: executive KPI summary, Sovereign Verdict, Monte Carlo, five persona KPIs, professional schedules, formula references, evidence, persona details, and checks.
- PDF: KPI-first executive opening followed by the complete written feasibility study with assumptions and limitations.
- PowerPoint: KPI-first executive deck, not a copy of PDF paragraphs.

Every format must carry and reconcile the same snapshot, calculation, formula, rule, evidence, Monte Carlo, persona, and verdict IDs. Report renderers must not recalculate.

PHASE 9 - TESTS AND RELEASE GATE

Implement and run every test in ASIE-SA-FEASIBILITY-ACCEPTANCE-v1.0.0.json.

The release is blocked unless every blocking test passes. Do not mark tests as passed without executable evidence. Produce test commands, results, and any remaining risk.

EXPECTED OUTPUT FROM YOU

For each phase, return:

1. AAS impact and affected documents.
2. Files created or modified.
3. Boundary statement.
4. Contracts and Sockets used or created.
5. Message flow.
6. Security and permission checks.
7. Tests run and exact results.
8. Non-goals.
9. Known risks and blockers.
10. Keep/Wrap/Rename/Reject/ACP classification for affected old implementation.

STOP CONDITIONS

Stop and report rather than improvise when:

- AAS files are missing or contradictory;
- a Contract or Socket cannot be identified;
- a requested behavior requires a new core component or changed trust/message path;
- a Saudi statutory rule lacks current approved evidence;
- a financial formula lacks defined units, period, or cash-flow basis;
- a Monte Carlo distribution or correlation lacks approval;
- persona isolation cannot be proven;
- reports cannot be reconciled to one snapshot;
- user-owned changes make safe implementation impossible.

DEFINITION OF DONE

Screens rendering is not completion. Completion requires deterministic calculations, passed reconciliations, reproducible Monte Carlo, isolated five-persona execution, deterministic Sovereign Verdict, KPI-first UI, one-click Project Workspace detail, snapshot-identical reports, complete audit lineage, and all blocking acceptance tests passing.
```
