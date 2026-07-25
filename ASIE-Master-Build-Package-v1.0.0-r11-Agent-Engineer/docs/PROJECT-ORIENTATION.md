# ASIE Project Orientation

This document is the “read this first” map for a programmer or coding agent. It describes the product boundary, the implemented customer flow, and the non-negotiable runtime controls.

## Purpose

ASIE is a local-first decision platform for turning a project idea or project data into a traceable financial and operational analysis. Product AI guidance, Market Intelligence, deterministic Finance, and sovereign decision ownership remain separated.

## One implemented product flow, two entry paths

| Entry path | Customer input | Implemented behavior |
| --- | --- | --- |
| Idea-only | Location, sector, stage, and short idea | Template Registry selects a governed template; the bounded Product AI Interview asks decisive Question Registry prompts and creates the first needs/items list |
| Data/file | Manual numbers, rough estimates, CSV, XLSX, text PDF, or supplier quote | Data Intake extracts rows, maps them to template items, assigns source/confidence, and leaves ambiguous mappings for user review |

Both paths meet at the **Dynamic Input Blueprint**. Neither path creates a separate financial model or sends raw material to Finance.

## Dynamic Input Blueprint

The implemented blueprint is project-specific. It changes with idea, Saudi location, precise sector, operating model, project stage, financing, and available data.

Each item contains:

- item and finance keys;
- category, label, unit, and required status;
- value and state (`VALUE_ENTERED`, `CLIENT_ESTIMATE`, `INTENTIONAL_ZERO`, `NOT_APPLICABLE`, `UNKNOWN`, or `EXPERIMENTAL_ESTIMATE`);
- reason, source type, confidence, evidence references, and import lineage;
- Finance treatment and human approval status;
- item-specific market query and Evidence Pack when used.

Zero is not missing. `INTENTIONAL_ZERO` and `NOT_APPLICABLE` require a documented reason and approval. Unknown required drivers block the manifest before Finance.

## Product AI Interview

The current Product AI Interview is deterministic and registry-bounded:

- questions come only from `backend/dib_registry.py` / `src/dibRegistry.ts`;
- it may classify, ask, explain, and propose items;
- it does not invoke an external model provider;
- it does not invent final financial or market values;
- it cannot issue a sovereign verdict.

## File and supplier-quote intake

The implemented Data Intake supports:

- manual rows and JSON;
- CSV;
- XLSX;
- text-extractable PDF and supplier quotes;
- manual review for low-confidence or unmatched rows.

PDF processing is local and does not use OCR, network access, or an external document service. Non-extractable scanned PDFs fail closed and must be mapped manually; they are never silently guessed.

## Per-item Market Intelligence loop

1. The customer marks a specific item unknown or requests research.
2. A `market.query.request.v1` message is emitted.
3. The request crosses Kernel → Heart Controller → Bus Controller → ASIE System Bus → Socket Contract Layer.
4. `ASIE Market Intelligence Module` returns `market.evidence.pack.v1`.
5. The pack contains cleaned samples, P25, P75, weighted median, IQR outlier report, source references, confidence, and data-mode labels.
6. The user approves the weighted median, rejects/modifies the specification, or enters a different number.
7. Only an approved result remains eligible for the Approved Input Manifest.

Development mode can produce clearly labeled local simulated samples when no user/dataset samples exist. The pack remains a candidate assumption, not a fact or decision.

## Approved Input Manifest and Finance

The implemented order is:

```text
Dynamic Input Blueprint
→ Approved Input Manifest
→ Manifest Validation Gate
→ existing AAS Runtime Path
→ Finance Engine
→ Snapshot Assembly
```

The Manifest Validation Gate verifies:

- required items;
- approval states;
- intentional-zero and not-applicable reasons;
- market Evidence Pack identity and user decision;
- normalized finance keys;
- revision and content-hash lineage.

The Finance adapter invokes deterministic Finance calculations only with manifest-derived normalized inputs. The manifest is included inside the sealed Finance module output and therefore captured in the immutable assembled Snapshot.

## AAS Runtime Freeze

The frozen path remains byte-for-byte unchanged:

```text
Kernel
→ Heart Controller
→ Hearts M1 / M2 / M3
→ Bus Controller
→ ASIE System Bus
→ Socket Contract Layer
→ Module Runtime
→ Snapshot Assembly
```

DIB adds pre-run models, an additive runtime registry for item Market Intelligence, and a non-frozen Finance admission adapter. It does not alter frozen files, pipeline order, sealed output keys, or Snapshot Assembly.

## Revisions, reruns, and comparison

- Every DIB save creates `blueprint.revision.v1`.
- Revision records carry parent ID, sequence number, item set, interview answers, timestamp, and content hash.
- Approved manifests are retained with the corresponding revision.
- A later item/price change creates a new revision.
- A rerun creates a new Snapshot.
- Existing Snapshot comparison reports KPI, decision, acceptance, and assumption changes.
- Old Snapshots are never edited.

## Governance state

```text
AI Providers = DISABLED
Provider Policy = DENY_ALL
External Network Research = DISABLED
Market Output Authority = candidate_assumption_only
Finance Ownership = deterministic engine only
Snapshot Mutation = forbidden
```

These are intentional governance controls, not unfinished DIB tasks.

## Verification

```bash
pnpm install --frozen-lockfile
pnpm build
python -m compileall -q backend
python tools/audit_dib_runtime.py
python -m unittest discover -s tests
```

The implementation status source is `docs/IMPLEMENTATION-STATUS-MATRIX.md`; the completion record is `docs/ASIE-DIB-COMPLETE-RUNTIME-CLOSURE-2026-07-25.md`.
