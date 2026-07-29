# DEPLOY-BETA-08 — Private Deployment Smoke

**Status:** implementation package  
**Base commit:** `9e20b980cee4936e8669198fc8c5c52f8186d489`  
**Release decision during this package:** `NO_GO`  
**Emergency Release Freeze:** remains `ACTIVE`

## 1. Purpose

`REL-BETA-07` proved that the source commit is buildable, deterministic, and protected by executable exploit-regression evidence. It intentionally left one technical release requirement unproven:

```text
private_deployment_smoke_passed
```

`DEPLOY-BETA-08` supplies that evidence without creating a public deployment. The package builds container images from the exact checked-out commit, starts them on an ephemeral GitHub Actions runner, binds every published port to `127.0.0.1`, disables external fetch, exercises live HTTP routes, emits a hashed deployment record, and destroys the containers and volumes after evidence capture.

This package does **not** clear the Emergency Release Freeze and does not authorize public or production exposure.

## 2. Private deployment boundary

The deployment uses:

```text
docker-compose.private-smoke.yml
```

Runtime bindings are restricted to:

```text
127.0.0.1:18080 → web:80
127.0.0.1:18794 → api:8794
127.0.0.1:18795 → dib-api:8795
```

The stack has no Caddy service, no `0.0.0.0` host publication, no public `80/443` binding, and no provider secrets. The Docker runtime network is declared `internal: true` and all services run with:

```text
ASIE_ENV=production
ASIE_ALLOW_EXTERNAL_FETCH=false
ASIE_ALLOW_LOCAL_BOOTSTRAP=false
ASIE_ALLOW_LEGACY_LOCAL_OPERATOR=false
```

The container processes listen on `0.0.0.0` only inside their isolated Docker network. Host publication remains loopback-only.

## 3. Exact-commit and image identity

The smoke probe requires:

```text
git rev-parse HEAD == GITHUB_SHA
```

It reads the built Docker image IDs for:

```text
api
dib-api
web
```

and computes one composite deployment digest from:

```text
exact commit SHA
+ SHA-256 of docker-compose.private-smoke.yml
+ backend image ID
+ frontend image ID
```

The result is stored as:

```text
image_digest: sha256:<64 hexadecimal characters>
```

The deployment evidence is therefore bound to both source and the concrete images used by the private deployment.

## 4. Live smoke checks

The emitted `asie.private.deployment.smoke.v1` record must prove all five checks required by `beta.release.gate.v2`.

### 4.1 `service_health`

The probe requires live `200` responses from:

```text
GET /api/health
GET /api/dib/status
GET /
```

Docker Compose must also report the three containers healthy before the probe starts.

### 4.2 `auth_boundary`

Under `ASIE_ENV=production`:

```text
POST /api/auth/local-bootstrap → 404 local_bootstrap_unavailable
POST /api/projects without Authorization → 401 authentication_required
```

Ephemeral test identities are inserted from inside the private API container through the Repository service. No HTTP bootstrap is enabled and no test token is stored in the evidence artifact.

### 4.3 `tenant_isolation`

Two independent users and organizations are created. Organization A creates a DIB session. A token belonging to Organization B must receive:

```text
GET session → 404 dib_resource_not_found
GET session events → 404
```

The owning organization must continue to use the session for the canonical run.

### 4.4 `canonical_project_run`

The probe creates this server-owned chain through live DIB HTTP routes:

```text
Persisted Blueprint
→ Server-Owned Approved Input Manifest
→ Server-Owned Validation Gate
→ controlled-finance compatibility endpoint
→ ProjectRunWorkflow
→ RunScopedModuleRuntime
→ Bus / Socket / Finance
→ Snapshot Assembly
```

The response must prove:

```text
status = executed
project_run_workflow_mount = called
workflow.contract_id = project.run.workflow.v1
finance_engine_execution_status = executed_via_project_run_workflow
```

The same command is then replayed with the same idempotency key. The second request must return the original `run_id` and `snapshot_id` with `idempotency_replayed=true`.

### 4.5 `snapshot_readback`

The resulting Snapshot is read from the main API using the owning tenant identity. The response must prove the same `snapshot_id` and immutable/sealed integrity.

## 5. Deployment evidence contract

The generated file is:

```text
deploy-beta-08-private-smoke/deployment-evidence.json
```

Its core structure is:

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

The `evidence_hash` is calculated over canonical JSON after removing only the `evidence_hash` field. Any mutation to a check, commit, image identity, network boundary, or timestamp invalidates the record.

## 6. REL-BETA-07 integration

The evidence-backed gate now has a third upstream evidence job:

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

When this package passes while the Emergency Release Freeze remains active, the expected decision is:

```text
code_evidence_ready = true
private_deployment_smoke_passed = true
critical_failures = [emergency_release_freeze_cleared]
decision = NO_GO
release_allowed = false
```

The disabled capabilities remain degradable. After a governed freeze review, they would limit the result to `CONDITIONAL_GO` for a technical limited beta unless separately proven.

## 7. Failure behavior

The package fails closed when any of the following occurs:

- checked-out commit differs from the expected release commit;
- a published port is not loopback-only;
- a container fails health checks;
- production Bootstrap becomes reachable;
- anonymous project creation succeeds;
- cross-tenant DIB access does not return the uniform denial;
- Manifest/Gate creation fails or accepts client-owned final objects;
- Finance does not pass through `ProjectRunWorkflow`;
- idempotency creates a second Run or Snapshot;
- Snapshot readback fails or is not immutable;
- image identity cannot be resolved;
- evidence hash or required check is invalid.

Container state, logs, image inspection, port bindings, and deployment evidence are uploaded even when the smoke job fails. The Docker stack and ephemeral volume are always destroyed.

## 8. Surgical allowlist

Only these files belong to this package:

```text
.github/workflows/beta-release-gate.yml
ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/docker-compose.private-smoke.yml
ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/tools/deploy_beta_08_private_smoke.py
ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/tests/test_deploy_beta_08_private_deployment_smoke.py
ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/docs/DEPLOY-BETA-08-PRIVATE-DEPLOYMENT-SMOKE-2026-07-29.md
```

## 9. Protected boundaries

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
production Hostinger deployment workflow
production docker-compose file
```

## 10. Exit condition

`DEPLOY-BETA-08` is closed only when:

1. ASIE CI succeeds on the final PR head.
2. Cross-platform determinism succeeds on the same head.
3. The private Docker deployment succeeds.
4. All five required smoke checks are `true`.
5. The deployment evidence hash is valid.
6. The release gate consumes the evidence and reports `NO_GO` only because the Emergency Release Freeze is still active.
7. The complete evidence artifact is retained and linked to the exact tested commit.

After closure, the next stage is a separate **Governed Freeze Review**. Raising or clearing the freeze is not part of this package.
