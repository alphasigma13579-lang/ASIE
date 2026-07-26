# Repository Surgery R2 — Quarantine Marking / Archive Compaction Candidates

Date: 2026-07-26
Status: R2 EXECUTION RECORD

## Scope

R2 adds explicit quarantine markers and prepares R3 deletion/compaction candidates.

R2 does not delete files.
R2 does not mutate AAS Freeze files.
R2 does not change DIB, Finance, Snapshot, AI Provider, or external-network behavior.

## Marked Archive Roots

| Path | R2 Status | Reason |
|---|---|---|
| `docs/reference/r11-workspace-materials/` | ARCHIVE_LOCKED_ROOT | Historical workspace material; not live implementation |
| `docs/reference/r11-workspace-materials/workspace-bundles/` | ARCHIVE_LOCKED_BUNDLE_ROOT | Contains historical bundles with implementation-looking content |

## Marked Dangerous Duplicate Bundles

| Path | R2 Classification | Why Dangerous |
|---|---|---|
| `docs/reference/r11-workspace-materials/workspace-bundles/ASIE-Architecture-Correction-Archive-2026-07-18-v1.0.0/` | DANGEROUS_DUPLICATE_BUNDLE | Contains outdated correction package material that can be mistaken for live architecture/build inputs |
| `docs/reference/r11-workspace-materials/workspace-bundles/ASIE-Architecture-Correction-Archive-2026-07-19-v1.1.0/` | DANGEROUS_DUPLICATE_BUNDLE | Later archive version, still non-authoritative after EKB admission and later DIB work |
| `docs/reference/r11-workspace-materials/workspace-bundles/ASIE-Architecture-Correction-Archive-2026-07-19-v1.1.1/` | DANGEROUS_DUPLICATE_BUNDLE | Later archive version, can shadow live AAS/EKB terminology |
| `docs/reference/r11-workspace-materials/workspace-bundles/ASIE-Next-Task-Handoff-2026-07-19-v1.0.0/` | DANGEROUS_DUPLICATE_BUNDLE | Old handoff plan; not a current task prompt or source of truth |
| `ASIE-Next-Task-Handoff-2026-07-19-v1.0.0/` | TOP_LEVEL_HANDOFF_ARCHIVE | Top-level old handoff; highest confusion risk because it sits beside live package content |

## R3 Deletion / Compaction Candidates

The following are candidates only. They require a separate PR and CI.

1. Compact or remove `docs/reference/r11-workspace-materials/workspace-bundles/ASIE-Architecture-Correction-Archive-2026-07-18-v1.0.0/`.
2. Compact or remove `docs/reference/r11-workspace-materials/workspace-bundles/ASIE-Architecture-Correction-Archive-2026-07-19-v1.1.0/`.
3. Compact or remove `docs/reference/r11-workspace-materials/workspace-bundles/ASIE-Architecture-Correction-Archive-2026-07-19-v1.1.1/`.
4. Compact or remove `docs/reference/r11-workspace-materials/workspace-bundles/ASIE-Next-Task-Handoff-2026-07-19-v1.0.0/`.
5. Compact or remove top-level `ASIE-Next-Task-Handoff-2026-07-19-v1.0.0/`.
6. Review root `*.zip.sha256.txt` archive checksum stubs and remove only if the referenced archive is represented by Git history or documented release artifacts.

## R3 Proof Required

Before deletion/compaction, R3 must prove:

- No live code imports from the target path.
- No live tests depend on the target path.
- No current EKB document requires the raw bundle content.
- The path is not part of AAS Runtime Freeze.
- Git history or a retained manifest preserves provenance.
- CI passes.

## Current Decision

R2 closes old files operationally by marking them in-place.
Physical deletion is intentionally deferred to R3.
