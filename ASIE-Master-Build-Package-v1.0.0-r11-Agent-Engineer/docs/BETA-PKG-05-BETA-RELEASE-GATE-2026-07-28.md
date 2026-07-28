# BETA-PKG-05 — Beta Release Gate

**Date:** 2026-07-28  
**Status:** Implemented on package branch; merge requires CI success.

## 1. Purpose

This package creates one deterministic, auditable release decision for ASIE beta readiness. It does not infer readiness from repository presence alone. It consumes explicit readiness assertions and classifies the release as:

- `GO`
- `CONDITIONAL_GO`
- `NO_GO`

## 2. Critical checks

A failure in any critical check produces `NO_GO`:

1. Authentication readiness.
2. Tenant-isolation readiness.
3. DIB Runtime readiness.
4. Dataset-to-DIB Mapping readiness.
5. Product AI Interview readiness.
6. Approved Input Manifest Gate readiness.
7. Controlled Finance readiness.
8. Snapshot lineage readiness.
9. Report-export readiness.
10. Deployment-health readiness.

## 3. Degradable checks

A failure in a degradable check produces `CONDITIONAL_GO` when all critical checks pass:

1. Production provider secrets readiness.
2. External fetch activation.
3. Vision 2030 synchronization readiness.
4. Live Intelligence readiness.

`CONDITIONAL_GO` permits only a limited technical beta when the limitation is disclosed. It does not permit a general public beta.

## 4. Decision rules

| Decision | Rule | Public beta | Limited technical beta |
|---|---|---:|---:|
| `GO` | All critical and degradable checks pass | Yes | Yes |
| `CONDITIONAL_GO` | All critical checks pass; one or more degradable checks fail | No | Yes, by explicit workflow input |
| `NO_GO` | One or more critical checks fail | No | No |

## 5. Production workflow

Workflow:

```text
.github/workflows/beta-release-gate.yml
```

The workflow:

- runs manually through `workflow_dispatch`;
- is bound to the protected GitHub Environment `production`;
- reads secret presence without serializing secret values;
- reads explicit readiness variables from the `production` environment;
- uploads a redacted JSON decision report;
- fails unless the decision is `GO`, or the operator explicitly allows `CONDITIONAL_GO`.

## 6. Required secrets

```text
DEEPSEEK_API_KEY
TAVILY_API_KEY
GOOGLE_MAPS_API_KEY
PINECONE_API_KEY
```

The report exposes only Boolean presence values.

## 7. Required production variables

```text
ASIE_BETA_AUTH_READY
ASIE_BETA_TENANT_ISOLATION_READY
ASIE_BETA_DIB_RUNTIME_READY
ASIE_BETA_DATASET_MAPPING_READY
ASIE_BETA_PRODUCT_AI_INTERVIEW_READY
ASIE_BETA_APPROVED_MANIFEST_GATE_READY
ASIE_BETA_CONTROLLED_FINANCE_READY
ASIE_BETA_SNAPSHOT_LINEAGE_READY
ASIE_BETA_REPORT_EXPORTS_READY
ASIE_BETA_DEPLOYMENT_HEALTH_READY
ASIE_BETA_EXTERNAL_FETCH_ENABLED
ASIE_BETA_VISION2030_SYNC_READY
ASIE_BETA_LIVE_INTELLIGENCE_READY
```

Each value must be explicitly set to a truthy value such as `true`. Missing values are fail-closed.

## 8. Hard boundaries

This package does not:

- invoke or modify Finance calculations;
- mutate Snapshot Assembly;
- alter the AAS Runtime Freeze;
- enable external fetch;
- activate providers;
- expose or persist secrets;
- modify authentication or tenant isolation;
- replace operational health checks with repository-file existence.

## 9. Evidence and limitations

The gate is an aggregation mechanism. A readiness variable must be set only after its underlying test or operational verification succeeds. Setting a variable to `true` without evidence is a governance violation.

Deployment health remains `false` until the Hostinger deployment is live and HTTPS, health checks, backups, and the core user journey have been verified on the server.

## 10. Package files

```text
backend/beta_release_gate.py
.github/workflows/beta-release-gate.yml
tests/test_beta_release_gate.py
tests/test_beta_pkg_05_guardrails.py
docs/BETA-PKG-05-BETA-RELEASE-GATE-2026-07-28.md
```
