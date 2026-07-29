# ARCH-BETA-05 — Canonical Finance Admission Repair

**Base commit:** `3d29486480436c4ac02567207c449ba1dfe6a621`  
**Prerequisites:** EMERG-00 through GOV-BETA-04 merged  
**Release status:** `NO_GO`; emergency release freeze remains ACTIVE

## Confirmed architectural violation

The previous DIB compatibility endpoint imported `finance_result_set` directly and executed Finance while explicitly reporting:

```text
project_run_workflow_mount = not_called
```

That path bypassed the canonical execution sequence required by ACR-DIB-001 and the frozen AAS runtime:

```text
ProjectRunWorkflow
→ RunScopedModuleRuntime
→ System Bus
→ Socket Contract Layer
→ Finance Module
→ downstream governed modules
→ Snapshot Assembly
```

The defect was not in Finance formulas. It was an unauthorized admission path around the canonical runtime.

## Root repair

### 1. Direct execution removed

`backend/dib_controlled_finance_wiring.py` no longer imports:

```text
backend.finance_engine
finance_result_set
```

The legacy internal helper now fails closed with:

```text
DIB_DIRECT_FINANCE_PATH_REMOVED
```

It cannot execute Finance or assemble Snapshot.

### 2. Compatibility endpoint converted to canonical admission

The public route remains for frontend compatibility:

```text
POST /api/dib/sessions/{session_id}/controlled-finance
```

Its semantics are now:

```text
server-owned Manifest chain
→ canonical admission verification
→ ProjectRunWorkflow
→ canonical runtime pipeline
```

It is no longer a direct Finance endpoint.

### 3. Exact lineage required

Admission verifies all active persisted records:

```text
DIB Session
├── current Blueprint ID + payload hash
├── server-owned Approved Manifest ID + payload hash
└── server-owned Validation Gate ID + payload hash
```

The following must match exactly:

- session ID;
- project ID;
- organization ownership;
- Blueprint ID and hash;
- Manifest ID and hash;
- Gate ID and hash;
- Manifest and Gate server authority;
- active session pointers;
- approved/passed statuses.

Client-provided Finance inputs, normalized inputs, Manifest, Gate, Project ID, Session ID, input hash, run ID, or snapshot ID are rejected.

### 4. Manifest-only Project overlay

The persisted Project row is not changed.

For one canonical run, the admission service builds an immutable `ProjectRecord` overlay containing:

```text
safe project context fields
+
server-owned Manifest.normalized_inputs
```

Legacy scalar Finance values stored in `project.inputs` cannot override Manifest values. The Project database row remains unchanged after the run.

### 5. Manifest-backed assumptions

The canonical pipeline receives a read-only Data Access overlay. Sources, datasets, evidence links, and transformations remain owned by the primary Repository. Project assumptions for this run are projected from the active Manifest and carry Manifest-specific assumption IDs.

### 6. Canonical request

Only fields already accepted by the frozen `ProjectRunWorkflowModuleAdapter` are sent:

```text
project_id
scenario_id
operation_id
idempotency_key
input_hash
requested_at
input_contract_id = ProjectRunHttpRequest.v1
```

The `input_hash` binds:

- DIB session;
- project;
- Blueprint ID/hash;
- Manifest ID/hash;
- Gate ID/hash;
- scenario;
- normalized inputs.

No frozen contract or runtime file is modified.

### 7. Idempotency

When no key is supplied, the server derives a stable idempotency key from the lineage hash. Repeating the same request returns the same Run and Snapshot. Reusing a key with different lineage is rejected by the existing `ProjectRunIdempotencyStore`.

### 8. Snapshot semantics

Snapshot Assembly is not called directly by DIB. It is reached only as the final stage of the canonical Project Run pipeline. The response records:

```text
project_run_workflow_mount = called
snapshot_mutation = true
snapshot immutable = true
```

## Exploit regression evidence

The package proves:

1. the direct helper cannot execute Finance;
2. no DIB admission module imports `finance_result_set`;
3. client-owned Finance inputs are rejected;
4. stale Manifest or Gate hashes are rejected;
5. Project legacy scalar values cannot override Manifest values;
6. the Workflow contract is `project.run.workflow.v1` and status is accepted;
7. Finance is produced through `finance.calculate.v1` / `finance.result.v1`;
8. one immutable Snapshot is persisted;
9. repeating the same idempotency key returns the same Run and Snapshot;
10. the original Project row remains unchanged.

## Allowlist

- `backend/dib_canonical_finance_admission.py`
- `backend/dib_controlled_finance_wiring.py`
- `backend/dib_tenant_api.py`
- `tests/test_arch_beta_05_canonical_finance_admission.py`
- `tests/test_dib_controlled_finance_wiring.py`
- `docs/ARCH-BETA-05-CANONICAL-FINANCE-ADMISSION-REPAIR-2026-07-29.md`
- `docs/ACR-DIB-001-CORR-01-CANONICAL-FINANCE-ADMISSION.md`

## Protected boundaries

No modifications are permitted to:

- AAS Runtime Freeze v1.0;
- `backend/project_run_workflow.py`;
- `backend/module_runtime.py`;
- `backend/system_bus.py`;
- `backend/socket_contracts.py`;
- Finance algorithms;
- `backend/snapshot_assembly.py`;
- Decision Council.

The package invokes these existing boundaries; it does not alter them.

## Exit criteria

- Full ASIE CI passes on the final PR head.
- Static guard finds no direct Finance import in DIB admission code.
- Integration test proves Workflow, Bus/Module Runtime, Finance, and immutable Snapshot execution.
- Manifest values win over stale Project scalar values.
- Idempotent replay creates no additional Run or Snapshot.
- Diff remains inside the allowlist.
- Emergency release freeze remains ACTIVE.
- TEST-BETA-06 does not start until this package is merged.
