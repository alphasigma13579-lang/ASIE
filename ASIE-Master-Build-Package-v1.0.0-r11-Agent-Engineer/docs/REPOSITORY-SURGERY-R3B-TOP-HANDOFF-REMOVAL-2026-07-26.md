# Repository Surgery R3B — Top-Level Handoff Archive Removal

Date: 2026-07-26
Status: R3B EXECUTION RECORD

## Scope

R3B removes one top-level archive directory only:

```text
ASIE-Next-Task-Handoff-2026-07-19-v1.0.0/
```

This directory was previously classified in R2 as `TOP_LEVEL_HANDOFF_ARCHIVE` and a deletion/compaction candidate.

## Deleted Files

The removed directory contained only the following archive files:

1. `ASIE-Next-Task-Handoff-2026-07-19-v1.0.0/01-Work-Plan/ASIE-Post-Freeze-Work-Plan-2026-07-19.md`
2. `ASIE-Next-Task-Handoff-2026-07-19-v1.0.0/01-Work-Plan/ASIE-Post-Freeze-Work-Plan-2026-07-19.md.sha256.txt`
3. `ASIE-Next-Task-Handoff-2026-07-19-v1.0.0/02-Freeze-Baseline/ASIE-AAS-Runtime-Freeze-Manifest-v1.0.json`
4. `ASIE-Next-Task-Handoff-2026-07-19-v1.0.0/02-Freeze-Baseline/ASIE-Architecture-One-Page-Map-2026-07-18.svg`
5. `ASIE-Next-Task-Handoff-2026-07-19-v1.0.0/03-Change-Control/ASIE-Architectural-Change-Request-Template-v1.0.md`
6. `ASIE-Next-Task-Handoff-2026-07-19-v1.0.0/README-AR.md`
7. `ASIE-Next-Task-Handoff-2026-07-19-v1.0.0/START-NEXT-TASK.md`
8. `ASIE-Next-Task-Handoff-2026-07-19-v1.0.0/HANDOFF-MANIFEST.json`
9. `ASIE-Next-Task-Handoff-2026-07-19-v1.0.0/SHA256SUMS.txt`

## Why This Is Safe

- The removed path was a top-level archived handoff bundle, not a live implementation root.
- R2 already marked this path as `TOP_LEVEL_HANDOFF_ARCHIVE`.
- Current authoritative task and repository governance are in EKB, AGENTS.md, and live package docs.
- The reference-copy handoff bundle under `docs/reference/r11-workspace-materials/workspace-bundles/` remains quarantined for provenance.
- Git history preserves the deleted top-level archive files.

## Boundaries

R3B does not:

- Delete the reference-copy handoff bundle under `docs/reference/`.
- Delete architecture correction archive bundles.
- Modify AAS Runtime Freeze files.
- Modify DIB runtime, Finance, Snapshot, AI Provider, or external-network behavior.
- Copy archive material into live `backend/`, `src/`, `tests/`, `registry/`, or live `docs/`.
- Treat archived `HANDOFF-MANIFEST.json` as a current runtime or task manifest.

## Proof Requirements

R3B is complete only if:

- The top-level handoff archive directory is absent.
- The quarantined reference-copy handoff marker remains present.
- R2 quarantine map remains present.
- No live runtime path references the removed top-level archive directory.
- A static test verifies the boundary.
- CI passes before merge.
