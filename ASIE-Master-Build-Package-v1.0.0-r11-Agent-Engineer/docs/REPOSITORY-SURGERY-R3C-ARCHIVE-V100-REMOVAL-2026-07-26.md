# Repository Surgery R3C — Architecture Correction Archive v1.0.0 Removal

Date: 2026-07-26
Status: R3C EXECUTION RECORD

## Scope

R3C removes one quarantined reference bundle only:

```text
docs/reference/r11-workspace-materials/workspace-bundles/ASIE-Architecture-Correction-Archive-2026-07-18-v1.0.0/
```

This bundle was classified in R2 as `DANGEROUS_DUPLICATE_BUNDLE` and was explicitly listed as a deletion/compaction candidate.

## Deleted Target

The removed target contained the historical ASIE Architecture Correction Archive v1.0.0 bundle, including:

- reference-pack markdown files,
- historical architecture plan/map files,
- correction-pack summaries,
- archived `backend/*.py` implementation-looking copies,
- archived verification tests,
- `ARCHIVE-MANIFEST.json`,
- `SHA256SUMS.txt`,
- `QUARANTINE-LOCKED.md`,
- `README-AR.md`,
- `VERIFICATION-RESULTS.md`.

## Why This Is Safe

- The target was under `docs/reference/`, which is non-live historical provenance.
- R2 classified the target as archive-locked and dangerous duplicate material.
- The target contained implementation-looking files that could shadow live `backend/` files.
- Current source of truth remains the live package, current EKB, current AGENTS.md, and current runtime files outside `docs/reference/`.
- Provenance remains recoverable through Git history and later retained archives such as v1.1.0 / v1.1.1 until they are processed separately.

## Boundaries

R3C does not:

- Delete v1.1.0 or v1.1.1 architecture correction archives.
- Delete the reference-copy Next Task Handoff bundle.
- Delete `docs/reference/r11-workspace-materials/` or `workspace-bundles/` root markers.
- Modify live `backend/`, `src/`, `registry/`, or production `docs/` implementation files.
- Modify AAS Runtime Freeze files.
- Modify DIB runtime, Finance, Snapshot, AI Provider, or external-network behavior.
- Copy any archive material into live implementation paths.

## Acceptance Criteria

R3C is complete only if:

- The v1.0.0 archive bundle path is absent.
- Active quarantine markers for remaining bundles are still present.
- EKB-07 records R3C as completed removal.
- Static tests validate the deletion boundary.
- CI passes before merge.

## Next Step

R3D may target exactly one remaining quarantined bundle only, likely:

```text
docs/reference/r11-workspace-materials/workspace-bundles/ASIE-Architecture-Correction-Archive-2026-07-19-v1.1.0/
```

R3D must use a separate PR, separate proof, and CI before merge.
