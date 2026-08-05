# FC20-04 P0-A — Verification and Promotion Evidence

- **Status:** `MERGED / FC20-04 COMPLETE`
- **Branch:** `codex/fc20-04-p0-a`
- **Baseline:** `main@054d41605b7d3249e76866f1a56eda355427f93a`
- **Network/provider authority:** not granted; no external calls were executed
- **Implementation SHA:** `ef4579c7f41dead63a506f7cdf6e163d11dd5c74`
- **Merge commit:** `853e2b706a9e0bc49f7da061106f8c89f7c56612`
- **Pull request:** #122

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

## Official closure gates

All required gates are now satisfied:

1. the reviewed implementation is the exact tree in `ef4579c7f41dead63a506f7cdf6e163d11dd5c74`;
2. ASIE CI `30968258858` and Cross-Platform Determinism `30968258854` passed on that SHA;
3. the three Windows baseline failures remain explicitly dispositioned above and outside the surgical allowlist;
4. the committed candidate changed no frozen file;
5. PR #122 was squash-merged at `853e2b706a9e0bc49f7da061106f8c89f7c56612`;
6. the EKB and `FOUNDATION-COMPLETE-20.json` now bind completion to these committed facts.

Provider retries and quotas remain owned by FC20-03. Production pagination, job
observability, retention, backup, and incident exercises remain owned by FC20-15. This
ownership clarification does not weaken the FC20-04 admission boundary and does not
authorize a network, provider, worker, endpoint, or release.
