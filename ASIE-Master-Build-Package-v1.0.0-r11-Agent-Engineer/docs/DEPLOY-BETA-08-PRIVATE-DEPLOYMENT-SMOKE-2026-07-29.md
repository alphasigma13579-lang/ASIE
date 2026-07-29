# DEPLOY-BETA-08 — Private Deployment Smoke

**Base commit:** `9e20b980cee4936e8669198fc8c5c52f8186d489`  
**Release decision:** `NO_GO`  
**Emergency Release Freeze:** `ACTIVE`

## 1. Purpose

`DEPLOY-BETA-08` proves the last technical prerequisite left by `REL-BETA-07`:

```text
private_deployment_smoke_passed
```

The package builds Docker images from the exact tested commit, starts an ephemeral private stack, exercises live HTTP security and runtime boundaries, emits `asie.private.deployment.smoke.v1`, and destroys all containers and data after evidence capture.

It does not clear the Emergency Release Freeze and does not authorize public deployment.

## 2. Private network boundary

Host publication is restricted to:

```text
127.0.0.1:18080 → web:80
127.0.0.1:18794 → api:8794
127.0.0.1:18795 → dib-api:8795
```

The stack uses two Docker networks:

```text
asie-private-smoke-internal
  internal: true
  purpose: service-to-service traffic

asie-private-smoke-loopback
  bridge host binding: 127.0.0.1
  purpose: host-side Smoke probe only
```

There is no Caddy service and no public `80/443` binding. All services run with:

```text
ASIE_ENV=production
ASIE_ALLOW_EXTERNAL_FETCH=false
ASIE_ALLOW_LOCAL_BOOTSTRAP=false
ASIE_ALLOW_LEGACY_LOCAL_OPERATOR=false
```

The loopback bridge is required because Docker internal networks have no connection to host interfaces and therefore cannot provide host port mappings. Public exposure remains prohibited because every mapping and the bridge default binding are fixed to `127.0.0.1`.

## 3. Deployment defects found and repaired

### 3.1 Shared-volume copy-up race

Starting `api` and `dib-api` simultaneously against the same fresh volume caused a Docker copy-up race. The workflow now starts services sequentially:

```text
api → healthy
dib-api → healthy
web → healthy
```

The shared data boundary was preserved rather than splitting databases to hide the race.

### 3.2 Non-import-safe DIB entrypoint

All Compose profiles previously used:

```text
python backend/dib_http_mounting.py
```

Inside the image this failed with:

```text
ModuleNotFoundError: No module named 'backend'
```

The canonical command is now used consistently in:

```text
docker-compose.yml
docker-compose.production.yml
docker-compose.private-smoke.yml
```

```text
python -m backend.dib_http_mounting
```

The legacy integration test was corrected to prohibit regression to the broken command.

## 4. Exact commit and image identity

The probe requires:

```text
git rev-parse HEAD == GITHUB_SHA
```

One composite deployment digest is calculated from:

```text
exact commit SHA
+ private Compose SHA-256
+ backend image ID
+ frontend image ID
```

and stored as:

```text
image_digest: sha256:<64 hex characters>
```

## 5. Required live checks

### `service_health`

```text
GET /api/health      → 200
GET /api/dib/status  → 200
GET /                → 200
```

### `auth_boundary`

Under production configuration:

```text
POST /api/auth/local-bootstrap → 404 local_bootstrap_unavailable
POST /api/projects without Authorization → 401 authentication_required
```

### `tenant_isolation`

Two independent organizations are created. Organization B must receive uniform denial for Organization A's DIB resources:

```text
GET session        → 404 dib_resource_not_found
GET session events → 404
```

### `canonical_project_run`

The live flow must prove:

```text
Blueprint
→ Server-Owned Manifest
→ Server-Owned Validation Gate
→ controlled-finance compatibility endpoint
→ ProjectRunWorkflow
→ RunScopedModuleRuntime
→ System Bus / Socket / Finance
→ Snapshot Assembly
```

Required response evidence:

```text
status = executed
project_run_workflow_mount = called
workflow.contract_id = project.run.workflow.v1
finance_engine_execution_status = executed_via_project_run_workflow
```

An idempotent replay must return the original `run_id` and `snapshot_id`.

### `snapshot_readback`

The owning tenant must read the same Snapshot through the main API and verify immutable/sealed integrity.

## 6. Evidence contract

```json
{
  "schema": "asie.private.deployment.smoke.v1",
  "package_id": "DEPLOY-BETA-08",
  "status": "passed",
  "commit_sha": "<exact commit>",
  "image_digest": "sha256:<digest>",
  "checks": {
    "service_health": true,
    "auth_boundary": true,
    "tenant_isolation": true,
    "canonical_project_run": true,
    "snapshot_readback": true
  },
  "evidence_hash": "<canonical SHA-256>"
}
```

Any mutation to the commit, image identity, checks, network boundary, or evidence material invalidates the record.

## 7. Release-gate integration

`REL-BETA-07` evaluates:

```text
determinism evidence
+ executable code evidence
+ private deployment evidence
+ emergency freeze state
```

After the Smoke succeeds while the freeze remains active, the required result is:

```text
code_evidence_ready = true
private_deployment_smoke_passed = true
critical_failures = [emergency_release_freeze_cleared]
decision = NO_GO
release_allowed = false
```

Disabled external capabilities remain degradable and may limit a later governed decision to `CONDITIONAL_GO`.

## 8. Fail-closed conditions

The package fails if:

- commit or image identity differs;
- any port is not loopback-only;
- a service fails Health;
- Bootstrap or anonymous project creation becomes possible;
- cross-tenant access succeeds;
- Manifest/Gate authority is not server-owned;
- Finance bypasses `ProjectRunWorkflow`;
- idempotency creates another Run or Snapshot;
- Snapshot readback is missing or mutable;
- evidence integrity is invalid.

Container state, logs, image inspection, port bindings, and available evidence are uploaded on failure. The stack and volume are always removed.

## 9. Surgical allowlist

```text
.github/workflows/beta-release-gate.yml
ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/docker-compose.yml
ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/docker-compose.production.yml
ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/docker-compose.private-smoke.yml
ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/tools/deploy_beta_08_private_smoke.py
ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/tests/test_deploy_beta_08_private_deployment_smoke.py
ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/tests/test_dib_local_gateway_integration.py
ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/docs/DEPLOY-BETA-08-PRIVATE-DEPLOYMENT-SMOKE-2026-07-29.md
```

## 10. Protected boundaries

No changes are permitted to:

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

## 11. Exit condition

The package closes only when:

1. ASIE CI succeeds on the final head.
2. Cross-platform determinism succeeds on the same head.
3. The private Docker deployment succeeds.
4. All five Smoke checks are true.
5. Deployment evidence and image digest are valid.
6. The release gate consumes the evidence.
7. The only critical blocker is `emergency_release_freeze_cleared`.
8. Complete evidence is retained for the exact tested commit.

The following stage is a separate **Governed Freeze Review**.
