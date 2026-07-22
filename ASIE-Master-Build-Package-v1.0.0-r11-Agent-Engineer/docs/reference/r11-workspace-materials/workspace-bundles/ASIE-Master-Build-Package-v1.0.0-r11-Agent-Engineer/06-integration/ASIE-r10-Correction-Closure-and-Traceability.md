# ASIE Master r10 — Correction Closure and Traceability

## Status

This document closes the six r9 feasibility-integration corrections at the build-specification level. It does not claim production implementation or live-source availability.

**Architectural decision:** Compliant with AAS v1.0.0 Frozen Baseline.  
**Affected AAS:** AAS-12, AAS-14, AAS-15, AAS-16, AAS-17, AAS-18, AAS-20, AAS-40.  
**ACP:** Not required. These rules clarify implementation inside existing Module, Contract, System Bus, and Zero Trust boundaries; no core component, trust authority, or message path changes.

## Mandatory correction matrix

| ID | Closed correction | Required owner and boundary | Acceptance rejection test | Fail condition |
| --- | --- | --- | --- | --- |
| R10-01 | Logical feasibility labels never create physical Modules. | Project Wizard, Finance Engine, Market Intelligence, Decision Council, AI Advisory, and Reports only; cross-capability traffic follows SCL → APP → System Bus → Bus Controller → target Socket. | `R10-AC-01` | Any new Risk, Evidence, Export, Feasibility, Procurement, Methodology, or Dashboard Module/layer; or any direct Module call. |
| R10-02 | Sovereign Verdict is deterministic and non-voting. | Decision Council orchestrates only; persona envelopes remain isolated. `DEC-ALG-03` is advisory diagnostic data. | `R10-AC-02` | A vote, consensus, or AI output creates, alters, overrides, or is displayed as the Sovereign Verdict. |
| R10-03 | Monte Carlo feasibility-gate probability is permanent, reproducible, and truthfully gated. | Finance Engine owns inputs, distributions, correlations, seed, convergence, and result; UI only renders typed output. | `R10-AC-03` | Missing valid inputs, correlation, seed, convergence, or distribution still produces a probability; UI calls it success probability; calculation happens outside Finance Engine. |
| R10-04 | Dashboard is a presentation shell, never a truth owner. | React + TypeScript + Vite + pnpm frontend consumes typed view contracts; Python is backend-only. | `R10-AC-04` | UI calculates finance, generates chart values, contacts AI/providers directly, or bypasses a contract/System Bus path. |
| R10-05 | Subscription does not change truth. | Subscription / Usage controls entitlement only; Finance Engine, Decision Council, and Reports retain material truth. | `R10-AC-05` | A plan hides critical warning, Monte Carlo state, funding gap, or persona status; or changes a deterministic result. |
| R10-06 | Saudi authority always prevails over global research. | Market Intelligence holds approved evidence cards and source-adapter contracts; AI Advisory may explain approved cards only. | `R10-AC-06` | World Bank, IFC, McKinsey, or any global research is treated as Saudi law/tax/approval authority, automatically fetched, copied, embedded, or used without human-reviewed ASIE-authored evidence card. |

## Required test evidence

Each `R10-AC-*` result must retain: test ID, code revision, environment, actor/role, input fixture, expected rejection, actual result, timestamp, calculation snapshot ID when applicable, evidence snapshot ID when applicable, and reviewer decision. A missing record is a failed test.

## Release rule

The Master specification is **Good — correction closed** only when all six tests are mapped and present. A built ASIE release remains `UNVERIFIED` until those tests execute successfully against KIMI-delivered code. This distinction is deliberate: documents can constrain a build; they cannot prove its runtime behaviour.
