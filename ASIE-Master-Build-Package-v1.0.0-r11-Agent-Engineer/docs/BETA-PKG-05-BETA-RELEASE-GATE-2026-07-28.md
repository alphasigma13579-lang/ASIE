# BETA-PKG-05 — Beta Release Gate

**Date:** 2026-07-28  
**Status:** Implemented pending CI and merge  
**Contract:** `beta.release.gate.v1`

## Purpose

This package closes the staged beta-readiness program with one fail-closed, auditable release decision. It does not calculate Finance results, assemble Snapshots, modify the frozen AAS Runtime, or activate providers. It evaluates evidence supplied by existing verification paths and emits one of three verdicts:

- `GO`
- `CONDITIONAL_GO`
- `NO_GO`

## Critical gates

The following gates must all be `passed`:

1. Authentication
2. Tenant isolation
3. Dataset-to-DIB mapping
4. Product AI Interview
5. Approved Input Manifest
6. Controlled Finance wiring
7. Snapshot lineage
8. Report generation
9. Deployment health

Any missing, failed, disabled, or unchecked critical gate produces `NO_GO`.

## Conditional gates

The following may be explicitly disabled for a limited technical beta, provided the UI and operating record disclose that limitation:

1. Provider readiness
2. Live Intelligence
3. Vision 2030 monthly synchronization

A conditional gap produces `CONDITIONAL_GO` only when every critical gate has passed.

## Decision matrix

| Critical gates | Conditional gates | Verdict |
|---|---|---|
| All passed | All passed | `GO` |
| All passed | One or more disabled/failed | `CONDITIONAL_GO` |
| Any not passed or missing | Any state | `NO_GO` |

## Files

- `backend/beta_release_gate.py`
- `tests/test_beta_release_gate.py`
- `.github/workflows/beta-release-gate.yml`
- `docs/BETA-PKG-05-BETA-RELEASE-GATE-2026-07-28.md`

## Workflow operation

The protected manual workflow is bound to the GitHub Environment `production` and supports:

- `conditional`: blocks only `NO_GO`.
- `strict`: requires `GO`.

The workflow reads provider secrets only through environment presence. It never serializes, logs, or uploads secret values.

## Security and architecture boundaries

The package declares and tests:

- `secrets_exposed = false`
- `finance_mutated = false`
- `snapshot_mutated = false`
- `aas_runtime_mutated = false`

No frozen runtime file is modified. No raw dataset can bypass DIB and Approved Input Manifest. No provider output becomes a controlled financial assumption through this gate.

## First production evaluation

After merge:

1. Add the four canonical provider secrets to the `production` Environment.
2. Complete Hostinger domain, HTTPS, deployment, health check, and backup verification.
3. Run `Production Provider Readiness`.
4. Run `Beta Release Gate` in `conditional` mode.
5. Resolve every critical failure.
6. Run again in `strict` mode before any public beta.

## Interpretation

The presence of the gate does not itself mean the platform is ready. Readiness exists only when a protected workflow run produces a reviewed verdict with supporting evidence. Until the production deployment and end-to-end verification are completed, the operational verdict remains fail-closed.
