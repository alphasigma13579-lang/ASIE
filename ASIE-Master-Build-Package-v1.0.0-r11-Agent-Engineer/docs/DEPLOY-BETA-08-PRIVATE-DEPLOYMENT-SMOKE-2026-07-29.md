# DEPLOY-BETA-08 — Private Deployment Smoke

**Status:** implementation package  
**Base commit:** `9e20b980cee4936e8669198fc8c5c52f8186d489`  
**Release decision:** `NO_GO`  
**Emergency Release Freeze:** `ACTIVE`

## 1. Purpose

`REL-BETA-07` proved that the source commit is buildable, deterministic, and protected by executable exploit-regression evidence. It intentionally left one technical requirement unproven:

```text
private_deployment_smoke_passed
```

`DEPLOY-BETA-08` builds the exact tested commit as Docker images, starts an ephemeral private deployment, exercises the live HTTP boundaries, emits a hashed `asie.private.deployment.smoke.v1` record, and destroys all containers and data after evidence capture.

The package does not clear the Emergency Release Freeze and does not authorize public deployment.

## 2. Private network boundary

The private stack is defined in:

```text
docker-compose.private-smoke.yml
```

Only these host bindings are permitted:

```text
127.0.0.1:18080 → web:80
127.0.0.1:18794 → api:8794
127.0.0.1:18795 → dib-api:8795
```

The stack has:

- no Caddy service;
- no public `80/443` publication;
- no provider secrets;
- `internal: true` Docker network;
- ephemeral data volume;
- external fetch disabled;
- local Bootstrap disabled;
- legacy local Principal disabled.

The services run with:

```text
ASIE_ENV=production
ASIE_ALLOW_EXTERNAL_FETCH=false
ASIE_ALLOW_LOCAL_BOOTSTRAP=false
ASIE_ALLOW_LEGACY_LOCAL_OPERATOR=false
```

## 3. Deployment defect found during execution

The first private deployment run exposed a deployment defect in all Compose profiles:

```text
python backend/dib_http_mounting.py
→ ModuleNotFoundError: No module named 'backend'
```

Running a package file directly places `/app/backend` at the front of `sys.path`, while the module imports `backend.*` from the package root.

The root correction is applied consistently in:

```text
docker-compose.yml
docker-compose.production.yml
docker-compose.private-smoke.yml
```

The canonical command is now:

```text
python -m backend.dib_http_mounting
```

No Runtime module or DIB implementation code was changed.

## 4. Shared-volume initialization

The API and DIB API intentionally share one ephemeral volume because both require the same platform identity/project database context. Starting both containers simultaneously caused a Docker copy-up race while the backend image initialized `/var/lib/asie/output`.

The workflow now starts services sequentially:

```text
api → healthy
dib-api → healthy
web → healthy
```

Each service must reach Docker Health status `healthy`; timeout, `unhealthy`, `exited`, or `dead` fails the package and prints service logs. The data model is not split to hide the race.

## 5. Exact-commit and image identity

The smoke probe requires:

```text
git rev-parse HEAD == GITHUB_SHA
```

It reads the backend and frontend Docker image IDs and computes one composite digest from:

```text
exact commit SHA
+ SHA-256 of docker-compose.private-smoke.yml
+ backend image ID
+ frontend image ID
```

The deployment evidence stores:

```text
image_digest: sha256:<64 hexadecimal characters>
```

## 6. Required live checks

The `beta.release.gate.v2` deployment evidence requires all five checks.

### `service_health`

```text
GET /api/health      → 200
GET /api/dib/status  → 200
GET /                → 200
```

### `auth_boundary`

Under `ASIE_ENV=production`:

```text
POST /api/auth/local-bootstrap → 404 local_bootstrap_unavailable
POST /api/projects without Authorization → 401 authentication_required
```

Test identities are inserted from inside the ephemeral API container through the Repository service. HTTP Bootstrap remains disabled, and credentials/tokens are not written to the evidence artifact.

### `tenant_isolation`

Two independent organizations are created. Organization A creates a DIB session. Organization B must receive:

```text
GET session        → 404 dib_resource_not_found
GET session events → 404
```

### `canonical_project_run`

The live probe creates:

```text
Persisted Blueprint
→ Server-Owned Approved Input Manifest
→ Server-Owned Validation Gate
→ controlled-finance compatibility endpoint
→ ProjectRunWorkflow
→ RunScopedModuleRuntime
→ System Bus / Socket / Finance
→ Snapshot Assembly
```

The response must prove:

```text
status = executed
project_run_workflow_mount = called
workflow.contract_id = project.run.workflow.v1
finance_engine_execution_status = executed_via_project_run_workflow
```

Replaying the same idempotency key must return the original `run_id` and `snapshot_id` with `idempotency_replayed=true`.

### `snapshot_readback`

The resulting Snapshot must be readable through the main API by its owning tenant and must prove the same `snapshot_id` and immutable/sealed integrity.

## 7. Evidence contract

The generated file is:

```text
deploy-beta-08-private-smoke/deployment-evidence.json
```

Core structure:

```json
{
  "schema": "asie.private.deployment.smoke.v1",
  "package_id": "DEPLOY-BETA-08",
  "status": "passed",
  "commit_sha": "<exact GITHUB_SHA>",
  "image_digest": "sha256:<digest>",
  "checks": {
    "service_health": true,
    "auth_boundary": true,
    "tenant_isolation": true,
    "canonical_project_run": true,
    "snapshot_readback": true
  },
  "capabilities": {
    "provider_connectivity": false,
    "external_fetch": false,
    "vision2030_sync": false,
    "live_intelligence": false
  },
  "evidence_hash": "<canonical SHA-256>"
}
```

Any mutation to the commit, image identity, checks, network boundary, or evidence material invalidates `evidence_hash`.

## 8. REL-BETA-07 integration

The release workflow now evaluates:

```text
determinism-vector
code-evidence
private-deployment-smoke
        ↓
evaluate-gate
```

The evaluator receives:

```text
--deployment-evidence deploy-beta-08-smoke/deployment-evidence.json
```

After Smoke succeeds while the freeze remains active, the expected report is:

```text
code_evidence_ready = true
private_deployment_smoke_passed = true
critical_failures = [emergency_release_freeze_cleared]
decision = NO_GO
release_allowed = false
```

The disabled external capabilities remain degradable and would limit a later governed decision to `CONDITIONAL_GO` for a technical limited beta unless separately proven.

## 9. Failure behavior

The package fails closed when:

- the checked-out commit differs from the expected release commit;
- a published port is not loopback-only;
- a service does not become healthy;
- production Bootstrap is reachable;
- anonymous project creation succeeds;
- cross-tenant DIB access succeeds;
- server-owned Manifest/Gate creation fails;
- Finance bypasses `ProjectRunWorkflow`;
- idempotency creates another Run or Snapshot;
- Snapshot readback is absent or mutable;
- image identity cannot be resolved;
- evidence hash or a required check is invalid.

Container state, logs, image inspection, port bindings, and deployment evidence are uploaded on failure. Containers and the ephemeral volume are always removed.

## 10. Surgical allowlist

```text
.github/workflows/beta-release-gate.yml
ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/docker-compose.yml
ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/docker-compose.production.yml
ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/docker-compose.private-smoke.yml
ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/tools/deploy_beta_08_private_smoke.py
ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/tests/test_deploy_beta_08_private_deployment_smoke.py
ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/docs/DEPLOY-BETA-08-PRIVATE-DEPLOYMENT-SMOKE-2026-07-29.md
```

## 11. Protected boundaries

The package does not modify:

```text
AAS Runtime Freeze files
EMERGENCY-RELEASE-FREEZE.json
Finance algorithms
ProjectRunWorkflow
Module Runtime
System Bus
Socket Contract Layer
Snapshot Assembly
Decision Council
Hostinger deployment workflow
```

## 12. Exit condition

The package closes only when:

1. ASIE CI succeeds on the final PR head.
2. Cross-platform determinism succeeds on the same head.
3. The private Docker deployment succeeds.
4. All five Smoke checks are `true`.
5. The deployment evidence hash is valid and tied to the exact image digest.
6. REL-BETA-07 consumes the evidence.
7. The gate reports `NO_GO` only because `emergency_release_freeze_cleared` remains false.
8. The complete evidence artifact is retained for the exact tested commit.

The next stage is a separate **Governed Freeze Review**. Clearing the freeze is not part of this package.
