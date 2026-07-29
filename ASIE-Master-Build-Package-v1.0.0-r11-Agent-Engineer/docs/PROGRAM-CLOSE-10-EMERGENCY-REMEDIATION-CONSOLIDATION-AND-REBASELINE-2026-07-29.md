# PROGRAM-CLOSE-10 — Emergency Remediation Consolidation & Rebaseline

| Field | Value |
|---|---|
| Document ID | `PROGRAM-CLOSE-10` |
| Status | `AUTHORITATIVE CURRENT PROGRAM STATE` |
| Owner | Repository and Release Governance |
| Baseline reviewed | `69b39d5a9a3050b7294a40e3441e4a6e69874fab` |
| Last reviewed | 2026-07-29 |
| Review trigger | Release-marker change, provider/network authorization, public-deployment authorization, frozen-boundary ACR, or a conflicting current-status claim |

## 1. Purpose and authority

This is the single current program-status and release-authority document for the
emergency remediation sequence. It consolidates the final state without
deleting, moving, or rewriting the dated execution records that prove how the
state was reached.

When a dated readiness plan, package record, orientation snapshot, or status
matrix conflicts with this document about current remediation or release state,
this document and the machine-readable marker
`/EMERGENCY-RELEASE-FREEZE.json` take precedence. Code, tests, frozen
manifests, canonical registers, and approved ACRs remain authoritative for their
own technical domains.

## 2. Current decision

The emergency remediation marker is:

```text
status: CLEARED
decision: PENDING_GATE
release_gate_allowed: true
```

This is a controlled technical unfreeze, not a public release authorization.

| Capability | Current authority |
|---|---|
| Exact-commit evidence gate | Allowed |
| Private loopback-only deployment smoke | Allowed |
| Technical limited validation | Allowed after exact-commit evidence |
| Public beta | Not authorized |
| Production deployment | Not authorized |
| External network/fetch | Not authorized |
| AI or data-provider activation | Not authorized |
| Google Maps activation | Not authorized |
| AAS Runtime Freeze removal or mutation | Not authorized |
| Finance, Snapshot Assembly, or Decision Council mutation | Not authorized by this package |

The exact post-merge baseline produced `CONDITIONAL_GO` for technical-limited
validation only. A later public or production decision requires a separate,
explicit governance package and fresh evidence. Silence, a green CI run, an
available secret, or a manual workflow dispatch never grants that authority.

## 3. Closed remediation and evidence packages

| Package | Pull request | Merge commit | Classification |
|---|---:|---|---|
| SEC-BETA-01 | #90 | `22437844b49ff4ae81e5936df5638129fb9cb7ec` | Closed security remediation |
| STAB-BETA-02 | #91 | `8ce8edf97203a377c87bbe8e2cb9518b442d6da0` | Closed stability remediation |
| SEC-BETA-03 | #92 | `6615b1828a31a079b4d57616878aca64d6cf6b0a` | Closed tenant-boundary remediation |
| GOV-BETA-04 | #93 | `3d29486480436c4ac02567207c449ba1dfe6a621` | Closed server-lineage remediation |
| ARCH-BETA-05 | #94 | `f0a36a18ba778dde1564df5fb6079a5bc9d2f6b8` | Closed canonical admission remediation |
| TEST-BETA-06 | #95 | `ddbcae583da3807467abf74a679c4b533e6d9918` | Closed deterministic evidence package |
| REL-BETA-07 | #96 | `9e20b980cee4936e8669198fc8c5c52f8186d489` | Closed evidence-gate package |
| DEPLOY-BETA-08 | #97 | `eef452f0ea45f4fe857d8132f124ed5cfdab5d96` | Closed private-smoke package |
| GOV-REL-09 | #98 | `e00cdc39e469e3592d0fdde3c2f365837a6414ec` | Closed eligibility-review package |
| GOV-REL-09A | #99 | `267f791c2f1ae354d9ec4ad368677f912fac6230` | Closed post-merge artifact repair |
| Recovery lockdown | #101 | `b459944ba211be32408dd642390122b24d8113ae` | Closed adjacent security remediation |
| GOV-REL-10 | #102 | `69b39d5a9a3050b7294a40e3441e4a6e69874fab` | Executed controlled unfreeze |

## 4. Bound post-merge evidence

The reviewed merge baseline is bound to the following successful GitHub
evidence:

- Evidence-Backed Beta Release Gate run `30461033896`:
  `CONDITIONAL_GO`, no critical failures, public beta false.
- Governed Freeze Review run `30461039250`:
  `TECHNICAL_LIMITED_UNFREEZE_VERIFIED`, no failures.
- TEST-BETA-06 run `30461033818`: successful cross-platform determinism.
- Governed review report SHA-256:
  `54e31165e00cc39b17695fa819eee550482adc887a3a74e4d8cd0a0d3dccaae7`.
- Governed review artifact digest:
  `sha256:61197bf77975d51325690bd63dcfb250e56781b072c652fd1f960e929583c4ce`.

These identifiers are evidence for the reviewed baseline, not a permanent
release waiver. Every later candidate commit must produce its own applicable
checks.

## 5. Source classification

### Authoritative and live

- `/EMERGENCY-RELEASE-FREEZE.json` for machine-readable release authority.
- This document for consolidated current program state.
- `docs/ASIE-AAS-Runtime-Freeze-Manifest-v1.0.json` for frozen runtime facts.
- Active EKB, canonical registers, approved ACRs, live source, and executable
  tests for their respective domains.
- Root and package `AGENTS.md` for repository operating rules.

### Derived orientation

`PROJECT-ORIENTATION.md` and `IMPLEMENTATION-STATUS-MATRIX.md` are useful
technical orientation snapshots. Their older statements about remediation,
DIB completion, or release state do not override this document, current code,
tests, or the release marker.

### Historical evidence

Dated security, architecture, beta, deployment, release, repository-surgery,
and package records remain immutable evidence of individual steps. They are not
independent current-status authorities. Filename prefixes such as
`SEC-BETA-`, `STAB-BETA-`, `GOV-BETA-`, `ARCH-BETA-`,
`TEST-BETA-`, `REL-BETA-`, `DEPLOY-BETA-`, `GOV-REL-`, and
`REPOSITORY-SURGERY-` identify execution history unless explicitly promoted
by this index.

### Archive and reference

`docs/reference/`, `docs/archive/superseded/`, and quarantine-marker shells
are provenance only. They must never be imported, copied, or interpreted as
live implementation. Git history preserves removed archive payloads.

## 6. Workflow map

| Workflow | Purpose | Current trigger/authority |
|---|---|---|
| `asie-ci.yml` | Frontend build, backend compile, complete Python test collection | Pull requests/manual |
| `test-beta-06-cross-platform-determinism.yml` | Cross-platform deterministic vectors | PR/main/manual |
| `beta-release-gate.yml` | Exact-commit executable release evidence | PR/main/manual; decision remains scope-bound |
| `governed-freeze-review.yml` | Independent marker/gate verification | Main/manual |
| `live-intel-ci.yml` | Static and test validation of provider/deployment code | Relevant pull requests only |
| `production-provider-readiness.yml` | Secret-presence readiness, no provider activation | Relevant PR/manual protected environment |
| `vision2030-kb-sync.yml` | External source/Pinecone synchronization | Manual and fail-closed without explicit marker authority |
| `deploy-hostinger.yml` | Production deployment | Manual and fail-closed without exact-commit evidence plus explicit marker authority |

Workflow duplication is retained only where the evidence purpose differs:
general CI, deterministic evidence, and the release gate have distinct
artifacts and decisions. No workflow may infer release authority from its own
success.

## 7. Repository-cleanup decision

This package performs no file deletion, directory move, runtime refactor, or
archive restoration. It:

1. establishes one current program-state source;
2. classifies dated records without destroying provenance;
3. aligns entry-point links and EKB precedence;
4. makes the primary CI collect both `unittest` and free-function
   `pytest` tests through `pytest`;
5. keeps the package-root handoff path as a marker-only quarantine shell;
6. makes external synchronization and production deployment fail closed against
   the current release marker.

## 8. Next phase

The next phase is not an automatic public launch. It is a separately authorized
decision package that must choose one of:

1. continue private technical-limited validation with external capabilities
   disabled; or
2. propose public/production/provider authority with fresh threat review,
   exact-commit evidence, environment approval, rollback proof, and an explicit
   marker-contract change.

Until that decision merges, public release, production deployment, external
networking, providers, AI, and Google Maps remain prohibited.
