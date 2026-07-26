# EKB-07 — Archive Quarantine Map

Status: LIVE EKB REFERENCE
Package: Repository Surgery Package R2 — Quarantine Marking / Archive Compaction Candidates
Date: 2026-07-26

## Purpose

This map turns the Repository Surgery R1 lockdown into explicit bundle-level quarantine marking.

R2 does not delete files. It marks historical bundles so no agent, engineer, or automation can reasonably mistake them for current implementation sources.

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

## Quarantine Markers Added in R2

The following marker files must exist and must not be removed unless a later Repository Surgery PR replaces them with a stricter mechanism:

| Path | Classification | R3 Treatment |
|---|---|---|
| `docs/reference/r11-workspace-materials/QUARANTINE-LOCKED.md` | ARCHIVE_LOCKED_ROOT | Keep marker until compaction complete |
| `docs/reference/r11-workspace-materials/workspace-bundles/QUARANTINE-LOCKED.md` | ARCHIVE_LOCKED_BUNDLE_ROOT | Keep marker until bundle directory is removed or compacted |
| `docs/reference/r11-workspace-materials/workspace-bundles/ASIE-Architecture-Correction-Archive-2026-07-18-v1.0.0/QUARANTINE-LOCKED.md` | DANGEROUS_DUPLICATE_BUNDLE | R3 deletion/compaction candidate |
| `docs/reference/r11-workspace-materials/workspace-bundles/ASIE-Architecture-Correction-Archive-2026-07-19-v1.1.0/QUARANTINE-LOCKED.md` | DANGEROUS_DUPLICATE_BUNDLE | R3 deletion/compaction candidate |
| `docs/reference/r11-workspace-materials/workspace-bundles/ASIE-Architecture-Correction-Archive-2026-07-19-v1.1.1/QUARANTINE-LOCKED.md` | DANGEROUS_DUPLICATE_BUNDLE | R3 deletion/compaction candidate |
| `docs/reference/r11-workspace-materials/workspace-bundles/ASIE-Next-Task-Handoff-2026-07-19-v1.0.0/QUARANTINE-LOCKED.md` | DANGEROUS_DUPLICATE_BUNDLE | R3 deletion/compaction candidate |
| `ASIE-Next-Task-Handoff-2026-07-19-v1.0.0/QUARANTINE-LOCKED.md` | TOP_LEVEL_HANDOFF_ARCHIVE | R3 deletion/compaction candidate |

## R3 Compaction Candidates

These are candidates, not deletions in R2:

1. Duplicate architecture correction archives under `docs/reference/r11-workspace-materials/workspace-bundles/`.
2. Top-level `ASIE-Next-Task-Handoff-2026-07-19-v1.0.0/` directory.
3. Archive zip checksum stubs at package root if the referenced archive payload is already represented in `docs/reference/` or GitHub history.
4. Heavy static binary/image material already represented by Git history, release artifacts, or a canonical markdown/SVG source.

## Hard Prohibitions

R2 and later repository surgery work must not:

- Copy files from `docs/reference/` into `backend/`, `src/`, `tests/`, `registry/`, or live `docs/`.
- Replace live runtime files with archive bundle versions.
- Use archive bundle `backend/asie_local_api.py` or `runtime_freeze.py` as a source for patching.
- Treat archive manifests as current build manifests.
- Delete AAS Freeze files.
- Modify DIB, Finance, Snapshot, AI Provider, or external-network behavior without a separate scoped PR.

## Acceptance Criteria

R2 is complete only if:

- Bundle-level quarantine markers exist.
- EKB-07 exists.
- A test validates marker presence and prohibitions.
- No live runtime file is changed.
- No archive file is deleted in R2.
- CI passes before merge.
