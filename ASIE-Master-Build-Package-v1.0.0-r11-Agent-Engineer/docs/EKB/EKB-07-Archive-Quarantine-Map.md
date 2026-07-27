# EKB-07 — Archive Quarantine Map

Status: LIVE EKB REFERENCE
Package: Repository Surgery R2/R3 Archive Quarantine and Compaction Map
Date: 2026-07-26

## Purpose

This map turns the Repository Surgery R1 lockdown into explicit bundle-level quarantine marking and records later approved compaction/removal steps.

R2 did not delete files. It marked historical bundles so no agent, engineer, or automation can reasonably mistake them for current implementation sources.

R3 packages may delete or compact one quarantined target at a time after proving the target is not live code, not a live test dependency, not an AAS Freeze member, and not required as a current EKB source of truth.

## Governing Rule

The only live implementation root remains:

```text
ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/
```

Inside that root, the following path is not live implementation:

```text
docs/reference/
```

Any implementation-looking file under `docs/reference/`, including `backend/*.py`, `src/*.tsx`, `runtime_freeze.py`, `snapshot_assembly.py`, `asie_local_api.py`, registry files, route files, and frozen-runtime lookalikes, is classified as:

```text
ARCHIVE_LOCKED / DANGEROUS_DUPLICATE / NOT EXECUTABLE / NOT AUTHORITATIVE
```

## Active Quarantine Markers

The following marker files must exist until a later Repository Surgery PR removes or replaces the corresponding target:

| Path | Classification | Current Treatment |
|---|---|---|
| `docs/reference/r11-workspace-materials/QUARANTINE-LOCKED.md` | ARCHIVE_LOCKED_ROOT | Keep marker until compaction complete |
| `docs/reference/r11-workspace-materials/workspace-bundles/QUARANTINE-LOCKED.md` | ARCHIVE_LOCKED_BUNDLE_ROOT | Keep marker until bundle directory is removed or compacted |
| `docs/reference/r11-workspace-materials/workspace-bundles/ASIE-Architecture-Correction-Archive-2026-07-19-v1.1.1/QUARANTINE-LOCKED.md` | DANGEROUS_DUPLICATE_BUNDLE | R3 deletion/compaction candidate |
| `docs/reference/r11-workspace-materials/workspace-bundles/ASIE-Next-Task-Handoff-2026-07-19-v1.0.0/QUARANTINE-LOCKED.md` | DANGEROUS_DUPLICATE_BUNDLE | R3 deletion/compaction candidate |

## Completed R3 Compaction / Removal

| Package | Removed Target | Scope |
|---|---|---|
| R3A | package-root archive `*.zip.sha256.txt` stubs | Removed checksum stubs only |
| R3B | `ASIE-Next-Task-Handoff-2026-07-19-v1.0.0/` at package root | Removed top-level handoff archive only |
| R3C | `docs/reference/r11-workspace-materials/workspace-bundles/ASIE-Architecture-Correction-Archive-2026-07-18-v1.0.0/` | Removed one quarantined v1.0.0 correction archive bundle |
| R3D | `docs/reference/r11-workspace-materials/workspace-bundles/ASIE-Architecture-Correction-Archive-2026-07-19-v1.1.0/` | Removed one quarantined v1.1.0 correction archive bundle |

## Remaining R3 Compaction Candidates

These are candidates, not automatically approved deletions:

1. `docs/reference/r11-workspace-materials/workspace-bundles/ASIE-Architecture-Correction-Archive-2026-07-19-v1.1.1/`.
2. `docs/reference/r11-workspace-materials/workspace-bundles/ASIE-Next-Task-Handoff-2026-07-19-v1.0.0/`.
3. Heavy static binary/image material already represented by Git history, release artifacts, or a canonical markdown/SVG source.

## Hard Prohibitions

R2 and later repository surgery work must not:

- Copy files from `docs/reference/` into `backend/`, `src/`, `tests/`, `registry/`, or live `docs/`.
- Replace live runtime files with archive bundle versions.
- Use archive bundle `backend/asie_local_api.py` or `runtime_freeze.py` as a source for patching.
- Treat archive manifests as current build manifests.
- Delete AAS Freeze files.
- Modify DIB, Finance, Snapshot, AI Provider, or external-network behavior without a separate scoped PR.

## Acceptance Criteria

R3 compaction is acceptable only if:

- The target was already quarantined or explicitly listed as a compaction candidate.
- One PR removes one target scope only.
- Current EKB is updated to distinguish active markers from completed removals.
- Static tests validate the removal boundary.
- No live runtime file is changed.
- CI passes before merge.
