# FOUNDATION-COMPLETE-20 — Core Intelligence Completion Program

| Field | Value |
|---|---|
| Program ID | `FOUNDATION-COMPLETE-20` |
| Version | `1.0.0` |
| Status | `ACTIVE IMPLEMENTATION PROGRAM` |
| Baseline | `fb40bb3ebd5110f78a67d7de590fceddc77213e9` |
| Target | Complete the foundational platform before Closed Live Beta |
| Current release verdict | `BLOCK` |
| Machine authority | `/FOUNDATION-COMPLETE-20.json` |
| Public release | Not authorized |
| External network/providers | Not authorized by this document |

## 1. Decision

ASIE will not use a beta label to excuse incomplete foundational architecture. Capabilities already declared as part of AIA, market intelligence, governed source acquisition, the Dynamic Input Blueprint, the live cockpit, evidence, and the decision path must be completed and verified before a Closed Live Beta decision.

This document and the machine manifest form one program. Individual implementation PRs may add code, tests, ACRs, migrations, and evidence, but they must not create competing program-status documents. A package is not complete because a plan exists or CI is green; it is complete only when its implementation, negative acceptance tests, exact-commit evidence, rollback proof, and residual-risk review are recorded in the manifest.

## 2. Evidence-backed as-built gaps

The following are executable-source findings at the baseline, not judgments copied from archive/reference material:

| Gap | Baseline evidence | Program owner |
|---|---|---|
| Global/National intelligence returns `DISABLED` | `backend/intelligence_layers.py` | FC20-06 |
| Global/National/Market/Cost contracts return `DEFINED_NOT_IMPLEMENTED` | `backend/economic_intelligence_foundations.py` | FC20-06/07 |
| Market context maturity stops at `PARTIAL` and remains `REFERENCE_ONLY` | `backend/market_cost_intelligence.py` | FC20-07 |
| Decision Council v2 is defined-only and not registered in AAS | `backend/decision_council_v2_contracts.py` | FC20-12 |
| AI provider registry remains `DISABLED` / `DENY_ALL`; router requires an empty registry | `backend/ai_integration.py` | FC20-09 |
| Tavily market search is invoked without a server-owned domain allowlist | `backend/live_intelligence_product.py` | FC20-02 |
| Tavily crawl accepts a seed URL without source-registry admission | `backend/live_provider_clients.py` | FC20-02 |
| GASTAT, SAMA, and MOF are candidates, not enabled sources | `backend/source_registry.py` | FC20-02/06 |
| Vision sync authority conflicts with the general `reference_only` source rule and is currently manual/fail-closed | `config/vision2030_sources.json`, `.github/workflows/vision2030-kb-sync.yml` | FC20-05 |
| Provider preflight checks Pinecone only; full provider readiness is secret-presence oriented | `backend/live_provider_preflight.py`, `backend/production_provider_readiness.py` | FC20-03/15 |
| Live workspace has UI types and controls but no registered live API client/route wiring | `src/LiveIntelligenceWorkspace.tsx`, `src/api.ts`, `backend/live_intelligence_product.py` | FC20-13 |
| Live competitor map, consented GPS, drag/drop, hide, drill-down, and realtime transport are not implemented as live product behavior | active frontend source and tests | FC20-10/13 |
| Active EKB lists many domain files that do not exist; `domains/` contains only `INDEX.md` | `docs/EKB/domains/INDEX.md` | FC20-01 |

## 3. Package registry

| ID | Priority | Package | Current state | Frozen-boundary gate |
|---|---:|---|---|---|
| FC20-01 | P0 | Canonical completeness ledger and EKB domain completion | COMPLETE | No |
| FC20-02 | P0 | Governed source registry and Tavily admission | COMPLETE | IACR/ACR for external-source activation |
| FC20-03 | P0 | External provider security control plane | IN PROGRESS | IACR/ACR |
| FC20-04 | P0 | External evidence persistence, review, and job lifecycle | Blocked | No frozen mutation |
| FC20-05 | P0 | Vision 2030 knowledge authority and Pinecone lifecycle | Blocked | Provider/source activation gate |
| FC20-06 | P1 | National and global economic intelligence | Blocked | ACR-AIA-04 class gate |
| FC20-07 | P1 | Market estimation, sector intelligence, and reference cost completion | Blocked | Market contracts/ACR |
| FC20-08 | P1 | Approved intelligence context, strategic and consulting synthesis | Blocked | AIA contract gate |
| FC20-09 | P1 | Product AI interview and governed DeepSeek activation | Blocked | AI provider IACR/ACR |
| FC20-10 | P1 | Google Maps live competitor intelligence and consented location UX | Blocked | External-provider/terms gate |
| FC20-11 | P1 | Data intake, PDF quote extraction, and blueprint mapping completion | OPEN | DIB ACR boundary |
| FC20-12 | P1 | Decision Council v2 and governed AAS dispatch | `ACR_REQUIRED` | Frozen Runtime/Manifest ACR |
| FC20-13 | P1 | Live product APIs, workspace, KPI drill-down, and realtime job UX | Blocked | Canonical API/contract updates |
| FC20-14 | P2 | KPI intelligence, Launch Guide, reports, and Decision Pack completion | Blocked | Projection contracts where required |
| FC20-15 | P0 | Operations, observability, retention, and incident controls | Blocked | No frozen mutation |
| FC20-16 | P0 | Closed Live Beta release and Hostinger deployment | Blocked by all packages | Exact-commit release decision |

The detailed scope, dependency graph, negative acceptance tests, and frozen-boundary flags are authoritative in `/FOUNDATION-COMPLETE-20.json`. The table above is a reader-facing projection; if it ever differs, the machine manifest controls.

## 4. Execution order

### Phase A — Truth, sources, and security

`FC20-01 → FC20-02 → FC20-03 → FC20-04`

This phase establishes the source of truth, server-owned admission, provider control plane, and tenant-safe evidence lifecycle. No external provider is enabled merely because these controls compile.

### Phase B — Knowledge and core intelligence

`FC20-05 + FC20-06 + FC20-07 → FC20-08`

Vision knowledge, national/global indicators, market estimation, and reference cost become reviewed inputs to an approved intelligence context. Every signal carries source, freshness, geography, sector, confidence, lineage, and review.

### Phase C — AI, location, and input completion

`FC20-09 + FC20-10 + FC20-11`

DeepSeek is admitted only through the existing AI shell, Google Maps becomes a consented and terms-governed product capability, and all data/file/quote paths converge on the server-built Approved Input Manifest.

### Phase D — Governed decision integration

`FC20-12`

Decision Council v2 and Snapshot admission require a separate frozen-boundary ACR. Decision Council v1 parity, one-version-per-run dispatch, rollback, and a new freeze manifest are mandatory. There is no silent fallback and no parallel runtime.

### Phase E — Product completeness and operations

`FC20-13 + FC20-14 + FC20-15`

Complete the live API/UI, independent widgets, drill-down, realtime job states, KPI/Launch Guide/report projections, observability, retention, restore, incident response, quotas, canary, and kill switches.

### Phase F — Closed Live Beta

`FC20-16`

Deploy only an exact reviewed commit. Access is invitation-only; public signup and public release remain denied. Provider/network authority is environment-scoped and time-bounded. Hostinger deployment requires TLS, secret injection, migrations, live smoke, monitoring, backup, restore rehearsal, and rollback evidence.

## 5. Package completion contract

A package may move to `COMPLETE` only when all of the following are present:

1. implementation paths;
2. regression and negative-acceptance test paths;
3. exact commit SHA;
4. successful workflow run ID and immutable evidence artifact;
5. migration and compatibility evidence where applicable;
6. rollback proof;
7. security and tenant-isolation review;
8. residual-risk review;
9. source-of-truth/EKB update without duplicate status claims.

A plan, markdown record, secret-presence check, mock response, passing compile, or manual assertion cannot satisfy this contract alone.

## 6. Frozen boundary

The current AAS Runtime Freeze files remain untouched by this program manifest. FC20-12 is the only package that may propose frozen-path changes, and it must do so through a separate approved ACR, updated freeze manifest, parity evidence, and rollback proof. Earlier packages must remain pre-run, provider, evidence, product, or projection work outside the frozen execution path.

Finance remains the owner of controlled numbers. Snapshot Assembly remains the sovereign truth-sealing boundary. AI, Tavily, Pinecone, Google Maps, the UI, and external evidence cannot call Finance directly or mutate a Snapshot.

## 7. Current release authority

This program changes the readiness verdict to `BLOCK` while foundational completion is underway. It does not authorize public release, production deployment, provider activation, external network access, Google Maps, Vision sync, or Hostinger deployment. Those authorities require completion evidence and a separate exact-commit decision.

## 8. Anti-fragmentation rule

No additional top-level remediation program is created while FOUNDATION-COMPLETE-20 is active. Work is tracked by package IDs inside the machine manifest. Package PRs update the manifest atomically with code and evidence. Historical package documents remain evidence and do not become parallel current-state authorities.
