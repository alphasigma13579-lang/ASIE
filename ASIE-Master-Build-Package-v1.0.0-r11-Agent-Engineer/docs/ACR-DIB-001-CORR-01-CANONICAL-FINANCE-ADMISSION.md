# ACR-DIB-001-CORR-01 — Canonical Finance Admission Conformance Repair

**Classification:** Architectural conformance repair; no new runtime and no change to AAS Runtime Freeze.  
**Parent decision:** ACR-DIB-001 — Dynamic Input Blueprint.  
**Implementation package:** ARCH-BETA-05 — Canonical Finance Admission Repair.  
**Base commit:** `3d29486480436c4ac02567207c449ba1dfe6a621`.

## Violation corrected

The previous DIB compatibility path called Finance directly and explicitly bypassed `ProjectRunWorkflow`. This contradicted the parent ACR requirement that DIB outputs enter the canonical execution chain rather than call Finance directly.

## Binding correction

The only permitted DIB execution path is:

```text
Persisted DIB Session
→ Server-Owned Approved Input Manifest
→ Server-Owned Manifest Validation Gate
→ Canonical Finance Admission
→ ProjectRunWorkflow
→ Heart assignment
→ RunScopedModuleRuntime
→ System Bus
→ Socket Contract Layer
→ Finance Module
→ remaining canonical modules
→ Snapshot Assembly
```

The legacy `/controlled-finance` route may remain as a compatibility route name, but it must invoke this canonical path. It is not permitted to execute Finance independently.

## Non-negotiable guards

- DIB admission code must not import `finance_result_set` or `backend.finance_engine`.
- The active Manifest and Validation Gate must be persisted, server-owned, tenant-scoped, approved/passed, and hash-consistent.
- Client-supplied Finance inputs, normalized inputs, Manifest, Gate, Run ID, Snapshot ID, or input hash are forbidden.
- Manifest values are projected into a per-run immutable `ProjectRecord`; the persisted Project record is not modified.
- Finance executes through `finance.calculate.v1` and returns `finance.result.v1` through Module Runtime.
- Snapshot is assembled only by the canonical pipeline and remains immutable.
- Idempotency must replay the same Run and Snapshot for the same lineage.

## Frozen boundary

This correction does not modify:

- `backend/project_run_workflow.py`;
- `backend/module_runtime.py`;
- `backend/system_bus.py`;
- `backend/socket_contracts.py`;
- `backend/snapshot_assembly.py`;
- Finance algorithms;
- Decision Council;
- AAS Runtime Freeze manifests.

## Acceptance

Conformance is restored only when executable tests prove the canonical Workflow contract is accepted, Finance consumes Manifest values rather than legacy Project scalars, one immutable Snapshot is persisted, direct execution remains blocked, and the frozen-file verification remains green.
