# FC20-04 P0-A — Pre-Commit Verification Evidence

- **Status:** `IMPLEMENTATION VERIFIED / COMMIT AND CI PENDING`
- **Branch:** `codex/fc20-04-p0-a`
- **Baseline:** `main@054d41605b7d3249e76866f1a56eda355427f93a`
- **Network/provider authority:** not granted; no external calls were executed
- **Commit/push:** not performed

## Implemented closure controls

1. Five immutable external-evidence contracts with bounded validation and hash binding.
2. Tenant/project-authorized SQLite persistence with additive migration registry.
3. Application and database enforcement of the `job -> candidate -> artifact` lineage.
4. Candidate source, canonical URL, and provenance binding before artifact deduplication.
5. Redacted, fail-closed audit for rejected artifacts and approved-context admission.
6. Approved-context admission that requires:
   - an artifact, not a candidate;
   - a fresh capture at the requested evaluation time;
   - the latest server-recorded review to be approved;
   - no revocation or supersession;
   - same-tenant and owned-project authorization.
7. Deterministic job lifecycle, cancellation/partial failure rejection, idempotent replay,
   review hash binding, supersession, and tenant-isolation tests.

## Surgical files

### Backend

- `backend/external_evidence_authorization.py`
- `backend/external_evidence_contracts.py`
- `backend/external_evidence_persistence.py`

### Tests

- `tests/test_fc20_04_external_evidence_contracts.py`
- `tests/test_fc20_04_external_evidence_migrations.py`
- `tests/test_fc20_04_external_evidence_persistence.py`
- `tests/test_fc20_04_external_evidence_tenant_isolation.py`
- `tests/test_fc20_04_external_evidence_admission.py`

### Evidence

- `docs/FC20-04-P0-A-PRE-COMMIT-EVIDENCE-2026-08-05.md`

No frozen AAS, Finance, Decision Council, `repository.py`, or `asie_local_api.py` file
was changed.

## Reproducible verification

Run from the canonical package directory with the FC20 virtual environment.

```powershell
& '..\..\.venv-fc20\Scripts\python.exe' -B -m compileall -q backend
& '..\..\.venv-fc20\Scripts\python.exe' -B -m pytest -q -p no:cacheprovider `
  tests/test_fc20_04_external_evidence_contracts.py `
  tests/test_fc20_04_external_evidence_migrations.py `
  tests/test_fc20_04_external_evidence_persistence.py `
  tests/test_fc20_04_external_evidence_tenant_isolation.py `
  tests/test_fc20_04_external_evidence_admission.py
& '..\..\.venv-fc20\Scripts\python.exe' -B -m pytest -q -p no:cacheprovider `
  tests/test_runtime_freeze.py tests/test_foundation_complete_20_program.py
& '..\..\.venv-fc20\Scripts\python.exe' -B -m pytest -q -p no:cacheprovider
```

Observed results on 2026-08-05:

| Verification | Result |
|---|---:|
| Backend compile | PASS |
| FC20-04 offline tests | `30 passed` |
| Runtime Freeze + FOUNDATION | `17 passed` |
| Full repository regression | `681 passed, 4 skipped, 3 failed` |

The three full-suite failures are outside the FC20-04 surgical files and reproduce
independently in the existing Windows baseline:

1. `test_concurrent_writes` — SQLite file remains open during temporary-directory cleanup.
2. `test_gov_rel_09_governed_freeze_review` — Windows path-separator mismatch.
3. `test_report_export_routes` — PDF renderer availability probe disagrees with the route.

They are not repaired in this slice because doing so would cross its allowlist and, for
the storage/API cases, the explicit denylist.

## Rollback proof

- Migration creation is transactional; the negative migration test proves both schema
  objects and the migration registry are absent after a failed migration.
- Migration checksum drift fails closed.
- The schema is additive and isolated under `external_evidence_*` tables.
- A direct mismatched `job_id/candidate_id` artifact insert is rejected by SQLite.
- An artifact write is absent when normal audit or rejection audit persistence fails.
- Rollback before commit is removal of these untracked surgical files only; no existing
  database table or frozen runtime file needs destructive rollback.

## Remaining official closure gates

This evidence must not be used to mark FC20-04 `COMPLETE` until all of the following exist:

1. reviewed commit SHA containing only the surgical allowlist;
2. successful required CI workflow run IDs bound to that exact SHA;
3. an explicit disposition or repair record for the three repository-baseline failures;
4. frozen-file diff evidence from the committed candidate;
5. update of the FC20-04 EKB/domain record and `FOUNDATION-COMPLETE-20.json` using the
   committed evidence, not this pre-commit workspace state.
