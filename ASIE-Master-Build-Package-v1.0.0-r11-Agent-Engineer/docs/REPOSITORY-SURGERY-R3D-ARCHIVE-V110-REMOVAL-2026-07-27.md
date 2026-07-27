# Repository Surgery R3D — Archived Correction Bundle v1.1.0 Removal

Date: 2026-07-27
Status: R3D EXECUTION RECORD

## Target

R3D removes exactly one previously quarantined reference bundle:

```text
docs/reference/r11-workspace-materials/workspace-bundles/ASIE-Architecture-Correction-Archive-2026-07-19-v1.1.0/
```

## Source Proof

The target bundle declared itself as:

```text
archive_name: ASIE-Architecture-Correction-Archive-2026-07-19-v1.1.0
designation: AAS Runtime Freeze v1.0
purpose: Preservation archive for ASIE reference, plans, Packs A-G, frozen implementation, ACR control, and verification
file_count: 49
```

Its `SHA256SUMS.txt` listed archive-only copies of reference docs, architecture plans, correction-pack summaries, implementation-looking backend files, and verification tests.

## Deleted Scope

R3D deletes only the v1.1.0 bundle directory under `docs/reference/r11-workspace-materials/workspace-bundles/`.

Deleted archive-only content included:

- `00-Reference-Pack/`
- `01-Plans-and-Maps/`
- `02-Correction-Pack-Summaries/`
- `03-Implementation/backend/`
- `04-Verification/tests/`
- `ARCHIVE-MANIFEST.json`
- `SHA256SUMS.txt`
- `README-AR.md`
- `VERIFICATION-RESULTS.md`
- `QUARANTINE-LOCKED.md`

## Why This Is Safe

- The target was explicitly quarantined by R2.
- The target lived under `docs/reference/`, not under live `backend/`, `src/`, `registry/`, or live docs.
- The target contained dangerous duplicate implementation-looking files, including archive copies of `backend/asie_local_api.py`, `runtime_freeze.py`, `snapshot_assembly.py`, and test files.
- R3C already removed the older v1.0.0 bundle, proving this pattern can be guarded safely.
- The newer v1.1.1 correction archive remains as the next candidate and is not removed by this package.
- Git history preserves provenance of the removed bundle.

## Boundaries

R3D does not:

- Delete `ASIE-Architecture-Correction-Archive-2026-07-19-v1.1.1/`.
- Delete the reference-copy Next Task Handoff bundle.
- Delete `docs/reference/r11-workspace-materials/` or `workspace-bundles/` root markers.
- Modify live `backend/`, `src/`, `registry/`, or runtime files.
- Modify AAS Runtime Freeze files.
- Modify DIB runtime, Finance, Snapshot, AI Provider, or external-network behavior.
- Copy archive material into live implementation paths.

## Acceptance Criteria

R3D is complete only if:

- The v1.1.0 bundle directory is absent.
- EKB-07 records R3D under completed removals.
- Remaining active quarantine markers still exist.
- v1.1.1 and Next Task Handoff reference bundles remain present.
- Static tests validate the removal boundary.
- CI passes before merge.

## Next Candidate

The next possible R3 package is:

```text
R3E — ASIE-Architecture-Correction-Archive-2026-07-19-v1.1.1 removal
```

It must be processed in a separate PR with the same proof, boundary, test, CI, and merge discipline.
