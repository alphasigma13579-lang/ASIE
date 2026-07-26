# Repository Surgery R3A — Safe Archive Checksum Stub Cleanup

Date: 2026-07-26
Status: R3A EXECUTION RECORD

## Scope

R3A removes only stale package-root `*.zip.sha256.txt` checksum stubs for archive ZIP payloads.

This is a deliberately small deletion package. It does not delete archive bundles, documentation bundles, code, tests, manifests, AAS Freeze files, DIB runtime files, Finance files, Snapshot files, AI Provider files, or external-network behavior.

## Deleted Files

The following package-root checksum stubs were removed:

1. `ASIE-Next-Task-Handoff-2026-07-19-v1.0.0.zip.sha256.txt`
2. `ASIE-Architecture-Correction-Archive-2026-07-18-v1.0.0.zip.sha256.txt`
3. `ASIE-Architecture-Correction-Archive-2026-07-19-v1.1.0.zip.sha256.txt`
4. `ASIE-Architecture-Correction-Archive-2026-07-19-v1.1.1.zip.sha256.txt`

## Why This Is Safe

- The deleted files were checksum stubs only.
- They were not executable code.
- They were not runtime manifests.
- They were not imported by live `backend/`, `src/`, or `registry/` paths.
- Archive provenance remains available through Git history and the quarantined archive bundles.
- R2 already marked the related archive bundles as `ARCHIVE_LOCKED` / `DANGEROUS_DUPLICATE` / `NOT EXECUTABLE` / `NOT AUTHORITATIVE`.

## Boundaries

R3A does not:

- Delete any archive directory.
- Delete any current EKB document.
- Modify AAS Runtime Freeze files.
- Modify DIB runtime, Finance, Snapshot, AI Provider, or external-network behavior.
- Copy any archive material into live implementation paths.
- Treat archived `ARCHIVE-MANIFEST.json` or `HANDOFF-MANIFEST.json` as current runtime manifests.

## Acceptance Criteria

R3A is complete only if:

- The four checksum stubs are absent.
- R2 quarantine markers remain present.
- A static test verifies the removal and the boundary.
- CI passes.

## Next Step

R3B may target one archive directory only, starting with a separate proof that the target directory has no live imports, no live test dependency, no EKB dependency requiring raw content, and no AAS Freeze membership.
