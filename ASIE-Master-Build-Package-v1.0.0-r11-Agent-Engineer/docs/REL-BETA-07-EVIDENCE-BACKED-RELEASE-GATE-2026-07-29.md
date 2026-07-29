# REL-BETA-07 — Evidence-Backed Release Gate

**Base commit:** `ddbcae583da3807467abf74a679c4b533e6d9918`  
**Prerequisites:** EMERG-00 through TEST-BETA-06 merged  
**Current release status:** `NO_GO`  
**Emergency Release Freeze:** `ACTIVE`

## Purpose

Replace the former assertion-driven Beta Release Gate with an executable, commit-bound evidence system.

The previous workflow could produce `GO` from GitHub Variables set to `true`. REL-BETA-07 removes that authority completely. Neither a repository variable, workflow input, secret-presence check, nor human readiness statement can satisfy a security or architecture check.

## Non-negotiable decision rule

A release decision may only consume:

1. an executable code-evidence bundle generated from the checked-out release commit;
2. four byte-identical TEST-BETA-06 vectors generated from that same commit;
3. a hashed Private Deployment Smoke record for the same commit and deployed image digest;
4. the repository Emergency Release Freeze marker.

Any missing file, invalid schema, altered hash, duplicate check identifier, failed command, stale commit, missing image digest, or active freeze produces `NO_GO`.

## Evidence bundle

The code evidence uses:

```text
schema: asie.release.evidence.bundle.v2
package_id: REL-BETA-07
commit_sha: <exact GITHUB_SHA>
manual_readiness_assertions_accepted: false
checks: [...]
bundle_hash: <canonical SHA-256>
```

Each check record contains:

```text
check_id
critical
status
commit_sha
command
exit_code
started_at
finished_at
duration_ms
log_path
log_sha256
claims
```

The evaluator recomputes `bundle_hash`, requires unique check identifiers, and verifies every required record against the exact release commit.

## Executable critical checks

The collector runs the following evidence surfaces directly:

1. `frontend_dependencies`
   - `pnpm install --frozen-lockfile`
2. `frontend_build`
   - production frontend build
3. `backend_compile`
   - compile all backend modules
4. `full_python_suite`
   - complete Python regression suite
5. `dib_product_and_dataset_runtime`
   - Product AI Interview runtime
   - CSV/XLSX/PDF-text Dataset-to-DIB mapping
   - unknown-item blocking
6. `sec_beta_01_identity_lockdown`
   - production Bootstrap takeover denied
   - zero-user anonymous project creation denied
   - implicit legacy principal denied
7. `stab_beta_02_thread_safe_persistence`
   - ThreadingHTTPServer concurrency
   - transaction rollback and atomic writes
8. `sec_beta_03_tenant_isolation`
   - cross-organization reads/writes/events denied
   - unknown ownership quarantined
9. `gov_beta_04_server_owned_lineage`
   - client Manifest/Gate forgery denied
   - direct forged persistence denied
   - parent hashes verified
10. `arch_beta_05_canonical_finance_admission`
    - ProjectRunWorkflow invoked
    - direct DIB-to-Finance path removed
    - Run/Snapshot idempotency preserved
11. `snapshot_lineage`
    - DIB lineage remains connected to Snapshot projections
12. `report_exports`
    - report-renderer resolution and route behavior verified
13. `aas_freeze_git_blobs`
    - SHA-256 is calculated from `git show <commit>:<path>` bytes
    - worktree CRLF/LF conversion cannot influence the result

## Cross-platform determinism

Four independent jobs run:

```text
Ubuntu  / Python 3.12 / PYTHONHASHSEED=0
Ubuntu  / Python 3.12 / PYTHONHASHSEED=7919
Windows / Python 3.12 / PYTHONHASHSEED=0
Windows / Python 3.12 / PYTHONHASHSEED=7919
```

Each job produces a deterministic Finance/Sealed Output/Snapshot vector. A final job compares all four files byte-for-byte.

The final evaluator requires:

```text
status: passed
vectors_compared >= 4
vector_hash: valid SHA-256
comparison_sha256: valid SHA-256
commit_sha == release commit
```

## Private Deployment Smoke contract

REL-BETA-07 defines but does not fabricate the deployment evidence expected from the next stage:

```text
schema: asie.private.deployment.smoke.v1
commit_sha: <release commit>
image_digest: sha256:<64 hex>
status: passed
checks:
  service_health: passed
  auth_boundary: passed
  tenant_isolation: passed
  canonical_project_run: passed
  snapshot_readback: passed
capabilities:
  provider_connectivity: passed | unavailable
  external_fetch: passed | unavailable
  vision2030_sync: passed | unavailable
  live_intelligence: passed | unavailable
evidence_hash: <canonical SHA-256>
```

The current workflow does not accept a manual path, boolean, URL, or GitHub Variable as deployment evidence. Until the governed Private Deployment Smoke workflow supplies this artifact, the gate remains `NO_GO`.

## Freeze behavior

The gate runs in two modes:

### Audit mode

Used for:

- Pull Requests;
- pushes to `main`.

Audit mode always writes and uploads the complete report. It exits successfully when the evaluator itself works, even when the report decision is `NO_GO`. This prevents an active emergency freeze from blocking corrective code merges while preserving a machine-readable denial.

### Enforce mode

Used only by `workflow_dispatch`.

Enforce mode exits non-zero unless the evidence-backed decision satisfies the selected release scope:

```text
public_beta              -> GO only
technical_limited_beta   -> GO or CONDITIONAL_GO
```

The scope selection cannot override a failed critical check.

## Decision model

### NO_GO

Produced when any critical evidence fails, including:

- stale or altered evidence;
- failed build/test/exploit command;
- fewer than four deterministic vectors;
- missing Private Deployment Smoke;
- wrong deployment image digest;
- active or invalid Emergency Release Freeze marker.

### CONDITIONAL_GO

Possible only after all critical evidence passes and the freeze is cleared, while one or more degradable capabilities remain unavailable.

### GO

Possible only after all critical evidence and all degradable capabilities pass for the exact release commit and image digest.

## Current expected report

At completion of REL-BETA-07, the repository marker remains:

```text
status: ACTIVE
decision: NO_GO
release_gate_allowed: false
```

Therefore the expected audit result is:

```text
decision: NO_GO
code_evidence_ready: true
ready_for_private_deployment_smoke: true
critical_failures:
  - private_deployment_smoke_passed
  - emergency_release_freeze_cleared
```

This is correct behavior, not a failed package.

## Allowlist

```text
.github/workflows/beta-release-gate.yml
ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/backend/beta_release_gate.py
ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/tools/rel_beta_07_evidence.py
ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/tests/test_beta_release_gate.py
ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/tests/test_rel_beta_07_evidence_release_gate.py
ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/docs/REL-BETA-07-EVIDENCE-BACKED-RELEASE-GATE-2026-07-29.md
```

## Protected boundaries

No modification is permitted to:

- AAS Runtime Freeze files or manifest;
- ProjectRunWorkflow;
- Module Runtime;
- System Bus;
- Socket Contract Layer;
- Finance algorithms;
- Snapshot Assembly;
- Decision Council;
- Emergency Release Freeze marker.

## Next stage

After this package is merged and its Audit report confirms code evidence readiness:

```text
Private Deployment Smoke
→ attach commit- and image-bound deployment evidence
→ governed review of Emergency Release Freeze
→ rerun REL-BETA-07 in Enforce mode
→ final GO / CONDITIONAL_GO / NO_GO
```
