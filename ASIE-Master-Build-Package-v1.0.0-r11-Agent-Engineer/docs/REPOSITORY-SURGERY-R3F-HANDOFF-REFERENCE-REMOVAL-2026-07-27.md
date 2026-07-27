# Repository Surgery R3F — Reference-copy Next Task Handoff Bundle Removal

Date: 2026-07-27
Status: R3F EXECUTION RECORD

## Target

R3F removes exactly one previously quarantined reference bundle:

```text
docs/reference/r11-workspace-materials/workspace-bundles/ASIE-Next-Task-Handoff-2026-07-19-v1.0.0/
```

## Source Proof

The target bundle declared itself as:

```text
package_id: ASIE-NEXT-TASK-HANDOFF-v1.0.0
created_at: 2026-07-19
baseline: AAS Runtime Freeze v1.0
next_scope: PF-00, PF-01
file_count: 7
```

The target was later marked by R2 as:

```text
Status: DANGEROUS_DUPLICATE_BUNDLE
historical continuity material only
not a current task prompt
not a current build package
not a source for live implementation
```

## Deleted Scope

R3F deletes only the reference-copy handoff bundle directory under `docs/reference/r11-workspace-materials/workspace-bundles/`.

Deleted archive-only content included:

- `01-Work-Plan/ASIE-Post-Freeze-Work-Plan-2026-07-19.md`
- `01-Work-Plan/ASIE-Post-Freeze-Work-Plan-2026-07-19.md.sha256.txt`
- `02-Freeze-Baseline/ASIE-AAS-Runtime-Freeze-Manifest-v1.0.json`
- `02-Freeze-Baseline/ASIE-Architecture-One-Page-Map-2026-07-18.svg`
- `03-Change-Control/ASIE-Architectural-Change-Request-Template-v1.0.md`
- `README-AR.md`
- `START-NEXT-TASK.md`
- `HANDOFF-MANIFEST.json`
- `SHA256SUMS.txt`
- `QUARANTINE-LOCKED.md`

## Why This Is Safe

- The target was explicitly quarantined by R2.
- The target lived under `docs/reference/`, not under live `backend/`, `src/`, `registry/`, or live docs.
- The top-level handoff archive with the same package name was already removed in R3B.
- The correction archive family under `workspace-bundles/` was already removed in R3C, R3D, and R3E using the same guardrail pattern.
- Current EKB and current AGENTS files remain the source of truth for future work.
- Git history preserves provenance of the removed bundle.

## Boundaries

R3F does not:

- Delete `docs/reference/r11-workspace-materials/`.
- Delete `docs/reference/r11-workspace-materials/workspace-bundles/` root marker.
- Modify live `backend/`, `src/`, `registry/`, or runtime files.
- Modify AAS Runtime Freeze files.
- Modify DIB runtime, Finance, Snapshot, AI Provider, or external-network behavior.
- Copy archive material into live implementation paths.

## Acceptance Criteria

R3F is complete only if:

- The reference-copy handoff bundle directory is absent.
- EKB-07 records R3F under completed removals.
- Root quarantine markers still exist.
- Static tests validate the removal boundary.
- No live runtime file is changed.
- CI passes before merge.

## Remaining Work

After R3F, repository surgery should move from bundle deletion to small, evidence-backed compaction of any remaining heavy static artifacts or obsolete references. Each future package must remain separately scoped and CI-gated.
