# ASIE Saudi Feasibility Decision Integration Addendum v1.0.0

## Status and precedence

This addendum was introduced in Master r9 and is carried forward as binding in Master r10. It integrates `ASIE-Saudi-Feasibility-Decision-Pack-v1.0.0.zip` for feasibility decisions and user-facing feasibility outputs, subject to the frozen AAS baseline. The r10 correction-closure matrix adds mandatory traceability and rejection tests; it does not change AAS.

Precedence is: (1) AAS v1.0.0 Frozen Baseline and approved ACPs; (2) this addendum for conflicts explicitly resolved below; (3) Execution Pack r15 and Algorithm Catalog r15; (4) Saudi Feasibility Decision Pack v1.0.0; (5) earlier Master r8 documents where they do not conflict. An unresolved conflict is `NEEDS_REVIEW`, never an invitation to invent a reconciliation.

## Architecture-preserving capability mapping

Generic feasibility-pack labels are logical capability labels, not permission to add physical ASIE Modules, layers, controllers, buses, or hearts.

| Feasibility-pack label | Required implementation home | Rule |
|---|---|---|
| `ASIE.MOD.FEASIBILITY` | Project Wizard / existing approved feasibility capability | Do not create a new Feasibility Module. |
| `ASIE.MOD.FINANCIAL` | Finance Engine Module | Sole owner of deterministic financial schedules and metrics. |
| `ASIE.MOD.EVIDENCE` | Market Intelligence Module and approved source-adapter contracts | No direct provider access. |
| `ASIE.MOD.RISK` | Finance Engine risk capability; Decision Council consumes approved outputs | No new Risk Module without ACP. |
| `ASIE.MOD.DECISION` | Decision Council Module | Owns gates, persona orchestration, and deterministic synthesis; does not recalculate finance. |
| `ASIE.MOD.AI` | AI Advisory Module behind AI Contract | Explanation, challenge, and drafting only. |
| `ASIE.MOD.EXPORT` | Reports Module | Renders immutable approved snapshots; never recalculates. |

Every cross-capability interaction uses Socket Contract Layer -> APP -> System Bus -> Bus Controller governance -> target Socket. The dashboard is a React UI presentation shell and dispatches typed view actions only.

## Decision and simulation rules

1. `FIN-ALG-04` and `FIN-ALG-12` remain the authoritative Finance Engine implementation for Monte Carlo/MCMC, scenarios, stress, sensitivity, and switching values.
2. Monte Carlo is mandatory as a project headline KPI: **Probability of passing feasibility gates**. Never call it unconditional project-success probability. Without valid distributions, correlations, seed, convergence, or inputs, show `NOT_READY` and the blocking reason.
3. Existing consensus/vote outputs (`DEC-ALG-03`) are advisory diagnostics only. They never produce, override, or appear as the FSDP Sovereign Verdict.
4. FSDP runs in fixed isolated order: Project Manager -> Business Advisor -> Technical Auditor -> Analyst Coach -> Resistance Test -> Sovereign Verdict.
5. Personas receive only permitted deterministic input envelopes and cannot view another persona output. Persona KPI values and the Sovereign Verdict are deterministic; AI only explains them.
6. Sovereign Verdict is blocked until all five schema-valid persona outputs and deterministic gates are available.

## Product, evidence, and country rules

- Capture country/location and market scope before project detail.
- The first project page is compact and KPI-first: Sovereign Verdict, Monte Carlo feasibility-gate probability, Evidence Confidence, five persona KPIs, and 5–7 profile-routed KPIs. Schedules and lengthy narrative belong in Project Workspace and Excel/PDF/PPT.
- Exports use the same immutable snapshot and lead with KPIs, verdict, Monte Carlo, and persona indicators. Renderers do not recalculate.
- Subscription changes depth, diagnostics, collaboration, templates, and exports; it cannot alter truth or hide critical warnings, Monte Carlo state, funding gap, or persona status.
- Saudi official rules and sources govern Saudi studies. Every future GCC country is a separate versioned rule pack, not a Gulf average.
- World Bank/IFC/McKinsey may inform human-reviewed ASIE-authored evidence cards only; they are not Saudi legal, tax, or approval authority. Restricted content is never scraped, copied, vectorized, or automatically retrieved.

## Mandatory preflight additions

KIMI must confirm: approved mapping without new core components; Monte Carlo ranges/distributions/correlation/fixed seed/convergence/audit IDs; FSDP isolation and no-vote verdict tests; explicit depth profile and subscription entitlement; and one snapshot contract proving Excel/PDF/PPT parity.
