# STAB-BETA-02 — Transaction-Safe DIB Persistence

**Base commit:** `22437844b49ff4ae81e5936df5638129fb9cb7ec`  
**Prerequisite:** `EMERG-00` and `SEC-BETA-01` merged  
**Release status:** `NO_GO`; emergency release freeze remains ACTIVE

## Confirmed defect

`DIBPersistenceStore` previously created one SQLite connection in its constructor and reused it for every request. The DIB sidecar uses `ThreadingHTTPServer`, so the same connection was consumed by request threads other than the thread that created it. Python correctly raised `sqlite3.ProgrammingError`.

`dib_session_continuity.py` also bypassed the persistence boundary and executed SQL through `store.connection`, coupling callers to the unsafe shared connection.

## Root repair

This package removes the shared operational connection rather than masking the failure with `check_same_thread=False`.

- Every read receives a connection scoped to that operation.
- Every write receives a connection scoped to one explicit `BEGIN IMMEDIATE` transaction.
- Connections close in `finally` blocks.
- Write failures roll back the complete session/entity/event mutation.
- SQLite foreign keys are enabled on every connection.
- `busy_timeout=30000` queues bounded writer contention.
- WAL is initialized for the database file.
- The public `:memory:` default is implemented with a private temporary SQLite file so independent request connections share one ephemeral database without a cross-thread keeper connection.
- A versioned `dib_schema_migrations` registry records schema version 1 idempotently.
- Session continuity delegates queries to `DIBPersistenceStore` and no longer accesses SQL connections directly.

## Preserved interfaces

The following public behavior remains available:

- `create_dib_persistence_store()`
- `start_session()`
- `save_blueprint()`
- `save_approved_manifest()`
- `save_validation_gate()`
- `load_session()` and entity loaders
- `list_events()`
- `close_session()`
- `_append_event()` used by the existing sidecar audit overlay

This package does not redesign tenant ownership, Manifest lineage, or Finance admission. Those remain in later packages.

## Regression evidence

The package adds tests proving:

1. Forty concurrent session creations through a real `ThreadingHTTPServer` complete with HTTP 201 and no SQLite thread exception.
2. One shared Store supports concurrent reads and audit writes without sharing a connection.
3. A forced event insertion failure rolls back the preceding session insertion, including after reopening the database.
4. WAL, foreign keys, busy timeout, connection scope, and schema version survive reopening.
5. Closing the Store is idempotent and subsequent operations fail closed.
6. AAS Runtime Freeze files remain unchanged.

## Allowlist

- `backend/dib_persistence.py`
- `backend/dib_session_continuity.py`
- `tests/test_stab_beta_02_transaction_safe_dib_persistence.py`
- `docs/STAB-BETA-02-TRANSACTION-SAFE-DIB-PERSISTENCE-2026-07-29.md`

## Protected boundaries

No changes are permitted to:

- AAS Runtime Freeze v1.0;
- Finance calculations or algorithms;
- Snapshot Assembly or immutability;
- Decision Council;
- DIB tenant ownership model;
- Manifest/Gate trust model;
- canonical Finance admission path.

## Exit criteria

- Full ASIE CI passes on the PR head.
- The threaded HTTP regression test passes.
- No file outside the allowlist changes.
- The release freeze remains ACTIVE.
- The next package, `SEC-BETA-03`, starts only from the merge commit of this package.
