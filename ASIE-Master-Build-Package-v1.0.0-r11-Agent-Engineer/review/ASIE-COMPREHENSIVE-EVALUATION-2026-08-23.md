# ASIE comprehensive evaluation and FC20-05 readiness record

| Field | Value |
|---|---|
| Record ID | `ASIE-COMPREHENSIVE-EVALUATION-2026-08-23` |
| Owner | Principal architecture and independent audit gate |
| Status | `PRE-REVIEW / EXACT-HEAD EVIDENCE PENDING` |
| Version | `0.1.0` |
| Baseline | `main@6247a3fed8bb9cd973d36e47379cbff99d492733` |
| Rebuilt prerequisite baseline | `main@0a0da250ba507589a645c0c43a92c8ef076dedd4` |
| Last reviewed | `2026-08-23` |
| Public release | `BLOCK` |
| Network/provider activation | `BLOCK` |
| Supersedes | none |
| Review trigger | every commit, reviewer finding, live canary, or material contract change |

## Executive decision

The platform is suitable for continued governed construction and offline product
validation. It is **not yet proven as a professional feasibility service that
can be relied on for any Saudi project, and it is not proven as bank-ready or
public-live**.

Current decision split:

- FC20-05 dark implementation: `APPROVE WITH CONDITIONS` before external review.
- ASIE continued controlled build: `APPROVE WITH CONDITIONS`.
- Bank-grade or institutionally accepted feasibility claim: `BLOCK`.
- Public release, recurring external sync, or live provider activation: `BLOCK`.

The decision is deliberately narrower than CI status. Passing code gates cannot
replace lender-profile validation, real dataset/canary evidence, professional
financial review, recovery exercises, or a public-release authorization.

## Evidence basis

| Evidence | Classification | What it proves | What it does not prove |
|---|---|---|---|
| `FOUNDATION-COMPLETE-20.json` | authoritative program ledger | FC20-02/03/04 completion evidence, FC20-05 dependency state, release/network blocks | FC20-05 completion before exact-head evidence is recorded |
| `docs/FEASIBILITY-COMPLETE-01-...md` | authoritative execution plan | the accepted professional/bank-readiness gaps and gates | completion of later finance/lender/pilot work |
| `backend/finance_v2/*` and finance-v2 tests | executable implementation/evidence | deterministic statements, debt, scenario, sensitivity and result contracts implemented to their current slices | universal sector coverage, lender acceptance, actual/reforecast completion |
| `backend/public_knowledge.py` and FC20-05 tests | executable dark implementation/evidence | registry admission, quarantine, versioning, public namespace boundary, evidence validation, delete/restore/reindex | real-source retrieval quality, provider cost, production durability |
| `src/App.tsx`, `src/CommandCenter.tsx`, `src/LiveCockpit.tsx` | product implementation | Arabic guided journey, snapshot/decision navigation and explicit development simulations | live competitor map, draggable cockpit, complete realtime UX |
| `.github/workflows/*` | executable delivery controls | Linux CI, selected Windows determinism, freeze/release/provider gates | complete SAST/SCA/DAST, browser E2E, accessibility and load coverage |
| Baseline local gates | reproduced evidence | frontend build passed; baseline Python result was `978 passed, 4 failed, 3 skipped` with three reproducible Windows test defects and one isolated transient socket failure | post-change exact-head Python pass |
| Current pre-review gates | reproduced evidence | Python compile succeeds; registry validates 12 sources/7 enabled/0 private-auto with one bounded-crawl source; runnable local unit/evidence/crawl/tombstone checks pass; frozen files match; frontend production build passes with 1,599 transformed modules | full Python exact-head pass while pytest is unavailable in the current runner |

## Evaluation matrix

| Axis | Status | Classification | Evidence-backed judgment | Required exit gate |
|---|---|---|---|---|
| Product value | `PARTIAL` | Risk | The product has an Arabic guided project journey and deterministic decision path, but professional completeness for every project remains explicitly blocked. | Complete the remaining FEASIBILITY workstreams and representative sector golden cases. |
| Saudi funding standards | `MISSING/PARTIAL` | High risk | Funder reports and readiness projections exist, but no current, product-specific lender-profile registry and no bank/SDB validation prove acceptance. No official accreditation may be claimed. | Versioned lender/product profiles, effective dates, evidence, reviewer sign-off, and bank/SDB pilot. |
| Financial model correctness | `PARTIAL/STRONG FOUNDATION` | Risk | Finance V2 has deterministic statements, debt coverage, scenarios and governed sensitivity. Actual/reforecast lifecycle, full archetype coverage and professional validation remain incomplete. | Complete governed lifecycle slices, invariants, golden cases and independent finance reviewer/CPA review. |
| Market data | `PARTIAL` | High risk | FC20-05 provides a governed public corpus contract for seven enabled official sources plus candidates/references. It has no real dataset canary or structured indicator validation yet. | Dry-run and one-source canary evidence, structured data/unit validation, freshness monitoring and conflict policy. |
| AI and RAG | `PARTIAL` | High risk | Retrieval evidence is source-qualified and abstains on malformed/stale evidence; injection markers quarantine content. Live model routing and grounded-answer evaluations remain disabled/unproven. | Adversarial multilingual eval set, retrieval quality thresholds, refusal/conflict tests and separate model activation AIA. |
| Architecture | `PARTIAL/CONTROLLED` | Risk | Public data, tenant evidence, Finance, Snapshot and AAS responsibilities are separated. The dark-build file corpus is not a production durability design. | Durable source-of-truth adapter, backup/restore, concurrency and migration ADR before recurring operation. |
| Multi-tenancy | `EXISTS/OFFLINE-PROVEN` | Risk | Existing tenant tests plus the new fixed public namespace prevent tenant writes and preserve tenant-scoped reads/quotas. Live deployment isolation is not exercised here. | Exact-head cross-tenant suite plus deployed negative exercise without customer data. |
| Security and privacy | `PARTIAL/CONTROLLED` | High risk | Identity, tenant scope, SSRF, provider quotas, secret redaction and release freeze have tests. Continuous SAST/SCA/DAST and production security operation are not evidenced in CI. | Add security scanning/evidence, deployed authorization tests, retention/privacy review and incident exercise. |
| Arabic UX | `PARTIAL` | Improvement | The guided path covers location, sector, classification, project, gap, audience and capital with Arabic-first copy and visible not-ready states. Full browser E2E and usability evidence are absent. | Browser E2E, keyboard/screen-reader/RTL QA and representative-user validation. |
| Live cockpit | `PARTIAL/DEMO` | Product gap | KPI drill-down exists in command views, but the competitor map and opportunity guidance are explicitly labelled simulated; drag/drop and user-controlled module hiding are not implemented. | FC20-10 and FC20-13 live map, consented GPS, modular widgets, persistence, drill-down and realtime states. |
| Performance and cost | `PARTIAL` | High risk | Finance sensitivity has a benchmark gate and FC20-05 bounds batches/top-k/provider quotas. No real Tavily/Pinecone latency, ingestion volume or cost-per-study evidence exists. | Canary p50/p95, bytes/records, credits/vector cost, budget alerts and cost-per-study model. |
| Reliability | `PARTIAL` | High risk | FC20-05 is idempotent by hash and compensates partial update/delete/restore/reindex paths. Production corpus backup and disaster recovery are not proven. | Durable-store restore, provider outage/retry exercise, concurrency test and RPO/RTO evidence. |
| Tests and CI | `PARTIAL/EXTENSIVE` | Defect + risk | The repository has 119 Python test files and 884 statically discovered test functions/methods, Linux CI and selected Windows determinism. Current exact-head full Python execution is pending and browser/security suites are incomplete. | All required workflows green on one SHA; no disabled tests; browser E2E/security/performance evidence attached. |
| Operations | `MISSING/PARTIAL` | High risk | Provider readiness, kill switches and deployment workflows exist, but FC20-15 remains blocked and public-corpus alerts/runbooks/backup ownership are incomplete. | Monitoring, actionable alerts, retention, backup/restore, on-call and incident runbooks. |
| Licensing and compliance | `PARTIAL` | Risk | Saudi Open Data License v2 Arabic/English snapshots and per-source metadata are present; ambiguous/private sources remain non-ingested. This is not a legal/PDPL/NCA certification. | Per-dataset terms verification, attribution rendering, deletion/retention mapping and qualified legal/privacy review. |
| Code quality | `PARTIAL/GOOD FOUNDATION` | Improvement | Core financial and provider boundaries are explicit and heavily tested. The large frontend surface, legacy compatibility paths and documentation volume increase drift risk. | Keep atomic PRs, contract tests, dead-path removal decisions and generated traceability checks. |
| Commercial readiness | `MISSING/PARTIAL` | High risk | The value proposition and Arabic conversion path are visible. Support model, validated willingness-to-pay, cost per study, service level and bank-grade assurance are not proven. | Closed pilot, support/runbook capacity, unit economics and measured conversion/completion evidence. |

## FC20-05 gap map after implementation

| State | Capability/evidence |
|---|---|
| `EXISTS` | Unified source registry; exact HTTPS host/path admission; official-open automatic lane; bounded extract/crawl with returned-URL re-admission; private/reference-only lane; content fingerprint; freshness/expiry; quarantine audit; canonical dark corpus; fixed public Pinecone namespace; separately audited platform-only writes/deletes; tenant-scoped reads; retrieval lineage/temporal/license revalidation; feasibility permitted-use/abstention contract; tombstone-safe sync; delete/restore/reindex and compensation tests; bilingual Saudi license snapshots. |
| `PARTIAL` | Public source extraction currently treats pages as text rather than verified typed datasets; World Bank/IMF entries are API documentation roots, not indicator adapters; production corpus uses no durable shared store; content anomaly detection is bounded deterministic screening, not full DLP/malware analysis; product integration exposes evidence in the service but has no complete customer-facing citation component. |
| `CONFLICT` | The old Vision-only operational document is now explicitly marked superseded while the program ledger uses the broader public-economic scope; completion evidence remains intentionally absent. The workflow cache cannot be called a production source of truth. |
| `MISSING` | Real dry-run/canary results; quality and cost evidence; durable store/backup/restore; structured dataset schema and unit validation; concurrency proof; live citation UX; recurring schedule authority; CodeRabbit/Copilot exact-head adjudication; all-workflow exact-head evidence. |

## Claims policy

Allowed now:

- “ASIE contains a governed offline foundation for dynamic feasibility and
  public economic evidence.”
- “The platform can show source-qualified context and explicit gaps.”
- “Selected financial-model slices are deterministic and tested.”

Blocked now:

- “Accepted/approved by Saudi banks, SDB, Ministry of Finance, Monsha'at or any
  regulator.”
- “Reliable for every project in Saudi Arabia.”
- “The public corpus is live/current” before an authorized successful sync.
- “A market signal predicts project success or funding acceptance.”
- “PDPL/NCA compliant” as a certification claim.

## Root-cause repair and PR boundaries

1. License replacement PR #141 was independently reviewed and merged as
   `74e502ec9bc311e62fdd75f3bf4d0006eaf3c1d4`; stale PR #126 was closed.
2. Windows portability PR #142 was independently reviewed and merged as
   `0a0da250ba507589a645c0c43a92c8ef076dedd4`; it changed tests only.
3. Submit FC20-05 implementation, contracts, registry, ACR, EKB, workflow and
   evaluation as one capability PR only after prerequisites are resolved.
4. Keep PR #125 under separate independent review.
5. Do not merge PR #124, #42 or #10; only re-propose still-valid ideas in new
   small requests.

## Exact-head gates still required

- focused FC20-05, provider, tenant-isolation and feasibility tests;
- full Python suite and frontend production build;
- Linux and Windows required workflows;
- freeze-manifest and protected-contract diff;
- secret scan and workflow guardrails;
- dry-run only after explicit provider/network authority, then one-source
  canary under a separate authorization;
- CodeRabbit and Copilot review with no commit while either review is pending;
- independent adjudication of every Critical/High finding;
- final committed SHA, workflow run IDs, rollback proof and residual-risk
  record before `FC20-05.state=COMPLETE`.

## Final readiness rule

Until every exact-head gate above is attached to the same commit, the only
honest overall verdict is:

```text
CONTINUED CONTROLLED BUILD: APPROVE WITH CONDITIONS
FC20-05 DARK IMPLEMENTATION: APPROVE WITH CONDITIONS
BANK-GRADE FEASIBILITY CLAIM: BLOCK
PUBLIC/LIVE RELEASE: BLOCK
```
