# ASIE Saudi Feasibility Decision Pack v1.0.0

## Status

- Version: `1.0.0`
- Date: `2026-07-13`
- Jurisdiction: Saudi Arabia first; GCC country packs later
- Architecture: AAS v1.0.0 Frozen Baseline
- Purpose: KIMI-ready implementation specification

## Files

| File | Purpose |
| --- | --- |
| `ASIE-SA-FEASIBILITY-BUILD-SPEC-v1.0.0.md` | Binding product, calculation, UX, evidence, and reporting specification |
| `ASIE-SA-FEASIBILITY-CATALOG-v1.0.0.json` | Machine-readable tables, formulas, KPIs, routing, and report catalog |
| `ASIE-SA-FEASIBILITY-CONTRACTS-v1.0.0.json` | Message, Socket, permission, audit, and failure contracts |
| `ASIE-SA-FEASIBILITY-ACCEPTANCE-v1.0.0.json` | Blocking acceptance-test catalog |
| `ASIE-KIMI-FEASIBILITY-IMPLEMENTATION-PROMPT-v1.0.0.md` | Exact implementation order and constraints for KIMI |

## Binding Rules

1. AAS remains the architectural authority. This pack adds domain implementation requirements only.
2. Every financial number is produced by deterministic backend code using versioned formulas and approved inputs.
3. AI explains, challenges, and writes. AI never owns a decisive number, financial formula, distribution, score, or final decision.
4. Monte Carlo is a mandatory core capability. Its headline KPI is always present or explicitly marked `NOT_READY`.
5. The five sovereign persona KPIs are always present or explicitly marked `PENDING`/`NOT_APPLICABLE`.
6. The first project page is a compact KPI decision surface. Detailed writing, numbers, schedules, and tables live in Project Workspace.
7. Subscription entitlements may change depth, collaboration, and exports. They may not change calculation truth or hide critical warnings.
8. Saudi official rules control Saudi regulatory claims. World Bank, IFC, McKinsey, and other reputable research enrich methodology and benchmarks but do not become Saudi authority.
9. All internal Module communication follows the approved AAS message path through Contracts, APP, System Bus, and governed Sockets.
10. PDF, Excel, PowerPoint, and UI must render the same immutable calculation snapshot.

## Build Order

1. Read AAS and inventory the existing implementation.
2. Implement schemas and Contracts before engines or UI.
3. Implement deterministic schedules and reconciliation gates.
4. Implement model routing and Saudi rules.
5. Implement sensitivity, stress, switching values, and Monte Carlo.
6. Implement FSDP v3.1 isolation and deterministic Sovereign Verdict synthesis.
7. Implement the KPI-first Project Dashboard and Project Workspace.
8. Implement snapshot-based Excel, PDF, and PowerPoint outputs.
9. Run every blocking test in the acceptance catalog.

## Completion Rule

The feature is not complete when screens render. It is complete only when all blocking acceptance tests pass, every output traces to one calculation snapshot, and no critical value can be generated or modified by AI or frontend code.
