# ASIE r11 Architect Resolution Closure

## Status

This document closes the four additional architect files received after r10 and makes r11 the single implementation source.

هذه الوثيقة تغلق ملفات المعمارية الأربعة المضافة بعد r10 وتجعل r11 مصدر التنفيذ الوحيد.

## Source Files

| Source | SHA-256 | r11 treatment |
| --- | --- | --- |
| `architect_resolutions.md` | `e0d52f860a8380d9ac7f1069df284881ff5cbbcf7713daffad5f16992e75bd28` | Reviewed source, not directly binding |
| `implementation_plan.md` | `95e9f643e0fe011dcbdb08d57af1de2c17b0c5086507fcc272cfed9622257780` | Reviewed source, not directly binding |
| `project_evaluation-ar.md` | `f96c15428b1ef58b076e2d577ce6b83b56213d5ba812a9f087a127816c477b20` | Risk assessment input |
| `architect_master_plan-v1.0.md` | `821e65a1b1580eb1fbc911ff7c36d72dfe3bbb827b20cc3283c6701acff6539f` | Roadmap input |

The files under `07-architect-decisions/originals/` preserve the original text for traceability. If any original source conflicts with this closure, AAS, Governance, r15, r10 closure, or the feasibility addendum, this closure and the higher authority documents win.

## Binding Authority Order

1. AAS v1.0.0 Frozen Baseline.
2. Agent Governance Pack.
3. Execution Pack r15.
4. Algorithm Catalog r15.
5. r10 Correction Closure and Feasibility Integration Addendum.
6. This r11 Architect Resolution Closure.
7. Original architect source files for context only.

## r11 Decisions

### R11-01: High-performance message transport

**Decision:** Approved with constraints.

Zero-copy, shared memory, PyArrow, memory-mapped files, or equivalent bulk-transfer mechanisms may be used only as implementation optimizations below the existing Socket Contract Layer.

**Mandatory constraints:**

- The logical message path remains `SCL -> APP -> System Bus -> Bus Controller -> Target Socket`.
- No direct Module-to-Module call is allowed.
- The optimization must not create a new ASIE Layer, Bus, Kernel, Broker, or Module.
- Contract validation, authorization, audit, message identity, source module, target module, and replay controls remain mandatory.
- Bulk payloads may be referenced by content-addressed handles, but those handles must be governed by the same contract and Zero Trust checks.

**ACP:** Not required if implemented as an internal transport optimization. ACP required if it changes ownership, message path, trust authority, or component names.

**Acceptance test:** `R11-AC-01` rejects any shared-memory path that bypasses SCL, APP, System Bus, Bus Controller, sockets, authorization, or audit.

### R11-02: Human-guided remediation envelope

**Decision:** Approved with constraints.

When a persona, feasibility gate, data-quality gate, or Monte Carlo gate returns `NOT_READY`, the system may produce a Remediation Envelope for the user.

**Mandatory constraints:**

- The envelope is advisory and user-facing; it does not negotiate between personas.
- Personas remain isolated and cannot read each other's outputs.
- Sovereign Verdict remains deterministic and non-voting.
- The envelope must cite the failing gate, missing input, failed threshold, evidence issue, or formula source.
- The envelope may propose user edits and re-run steps, but it must not auto-change project assumptions without explicit user action.

**ACP:** Not required if the envelope is a view/report artifact produced from existing approved results. ACP required if it becomes a new authority or changes FSDP.

**Acceptance test:** `R11-AC-02` rejects any remediation logic that lets personas communicate, vote, bargain, or modify final verdict rules.

### R11-03: Market baseline indexing and synthetic fixtures

**Decision:** Approved with strict constraints.

Synthetic baselines, demo fixtures, and human-reviewed market index cards may be used for internal build, testing, and clearly labeled reference support.

**Mandatory constraints:**

- Runtime crawling of marketplaces, commercial sites, login sites, paid APIs, or protected content remains prohibited under `strict_open_data_only_v1`.
- Builder Agent or Engineer, Tevali, or any external agent/provider is not an ASIE architectural component or authority.
- Any external collection outside runtime requires documented permission, license, terms review, human approval, and source kill switch before production use.
- Synthetic/demo data must be labeled as demo or estimated. It must not be presented as GASTAT, HRSD, Saudi authority, McKinsey, World Bank, or market fact unless supported by an approved evidence card.
- Global research and commercial references may inform ASIE-authored cards only after human review and citation. No copying, mirroring, RAG ingestion, or embedding of protected source text.

**ACP:** Not required for demo fixtures or approved evidence cards inside existing Market Intelligence contracts. ACP required if a new source authority, crawler, data-sharing route, or module is introduced.

**Acceptance test:** `R11-AC-03` rejects unlabeled fake data, runtime crawlers, source-page ingestion, or provider-specific architecture.

### R11-04: Pre-calculated sensitivity matrix for UI responsiveness

**Decision:** Approved with constraints.

The Finance Engine may generate a pre-calculated sensitivity matrix for fast UI interaction.

**Mandatory constraints:**

- Finance Engine owns matrix generation, algorithms, assumptions, run ID, units, period, and timestamp.
- React may interpolate only inside the approved matrix domain and must visibly label values as preview estimates when they are not immutable verdict snapshots.
- Any out-of-range input, final decision, export, or formal report requires a backend calculation run.
- React must not compute NPV, IRR, DSCR, Monte Carlo, debt schedules, financial statements, persona KPIs, or Sovereign Verdict.
- Report exports use immutable backend snapshots, not UI preview values.

**ACP:** Not required if the matrix is a Finance Engine output contract. ACP required if frontend becomes a calculation owner.

**Acceptance test:** `R11-AC-04` rejects financial formulas, Monte Carlo, persona KPI logic, or verdict logic in React.

### R11-05: Implementation phasing

**Decision:** Corrected and binding.

The build must not postpone ASIE core feasibility-decision requirements that were already made mandatory in r10.

**Phase 1 core includes:**

- AAS-conformant backend skeleton.
- SCL, APP, System Bus, Bus Controller, sockets, audit, and Zero Trust gates.
- Finance Engine deterministic calculations.
- Monte Carlo feasibility-gate KPI or `NOT_READY`.
- Five sovereign personas and deterministic non-voting Sovereign Verdict.
- Project dashboard as KPI view only.
- Immutable snapshot parity across UI and exports.
- r10 and r11 rejection tests.

**Phase 2 may include:**

- Subscription packaging.
- User presentation profiles.
- More advanced recommendation card personalization.
- Payment integration.

**Correction:** The original phrase "adaptive persona system" must not be confused with FSDP sovereign personas. The five sovereign personas are core Phase 1. Presentation profiles for subscription/user experience may be Phase 2.

**Acceptance test:** `R11-AC-05` rejects any plan that defers Monte Carlo, FSDP, Sovereign Verdict, or snapshot parity out of core build.

### R11-06: Provider and technology neutrality

**Decision:** Binding clarification.

DeepSeek, OpenAI, Builder Agent or Engineer, Tevali, Pinecone, Redis, Supabase, FastAPI, PyArrow, NumPy, SciPy, Vite, and any other named tool are implementation mechanisms only.

**Mandatory constraints:**

- No provider becomes an AAS component, source of truth, compliance authority, or decision authority.
- Provider replacement must not change contracts, algorithms, snapshots, audit, or verdict semantics.
- AI may explain, classify, summarize approved ASIE-authored cards, and draft user-facing text. AI must not produce controlled numbers, official legal interpretation, final compliance judgment, Monte Carlo distributions, or finance results.

**Acceptance test:** `R11-AC-06` rejects provider-coupled architecture, provider-owned decisions, or AI-generated controlled numbers.

### R11-07: Performance claims

**Decision:** Corrected.

Performance targets such as "microseconds" or "under 5 ms" are not architectural promises unless proven by benchmark in the target environment.

**Mandatory constraints:**

- Performance goals must be measured with realistic payloads and concurrency.
- Compliance, contract validation, authorization, and audit cannot be disabled to meet latency targets.
- Benchmark results must include hardware, payload size, serialization mode, concurrency, and percentile latency.

**Acceptance test:** `R11-AC-07` rejects unverified performance claims or benchmarks that bypass security/contract checks.

## r11 Rejection Tests

| Test | Reject if |
| --- | --- |
| `R11-AC-01` | Shared memory or bulk transfer bypasses SCL, APP, System Bus, Bus Controller, sockets, authorization, or audit |
| `R11-AC-02` | Remediation allows persona communication, voting, bargaining, or auto-changing project assumptions |
| `R11-AC-03` | Demo/synthetic/market data is unlabeled, presented as official fact, crawled at runtime, or sourced without rights |
| `R11-AC-04` | React contains finance formulas, Monte Carlo, persona KPI logic, verdict logic, or final-report calculation |
| `R11-AC-05` | Core build defers Monte Carlo, FSDP, Sovereign Verdict, snapshot parity, or r10 rejection tests |
| `R11-AC-06` | A named provider becomes architectural authority or AI generates controlled numbers |
| `R11-AC-07` | Performance claims lack benchmark evidence or disable compliance controls |

## Final r11 Verdict

The four additional architect files are accepted as reviewed inputs only. Their safe, binding content is captured in this closure. r11 supersedes r10 as the single package to send to Codex or Builder Agent or Engineer.

