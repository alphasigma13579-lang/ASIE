# QUARANTINE LOCKED — Workspace Bundles

Status: ARCHIVE_LOCKED_BUNDLE_ROOT
Package: Repository Surgery Package R2

Every bundle below this directory is a historical archive bundle.

These bundles are allowed to preserve provenance only. They are not allowed to serve as implementation input for the current platform.

Forbidden use:

- copying `backend/*.py` from a bundle into live `backend/`
- copying `src/*.tsx` from a bundle into live `src/`
- replacing live `runtime_freeze.py`, `snapshot_assembly.py`, or `asie_local_api.py` with archived versions
- using archived `ARCHIVE-MANIFEST.json` as a current runtime manifest
- treating archived plans as newer than EKB unless a current EKB document explicitly admits them

R3 may delete or compact these bundles after proving no live references depend on them.
