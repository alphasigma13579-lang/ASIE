# Archive Lockdown Notice

**Status:** Archive-locked / non-executable / non-authoritative  
**Effective date:** 2026-07-26

This directory is historical provenance only. It is intentionally preserved so earlier ASIE work can be audited, but it is not the live source of truth.

## Binding rule

Files under this directory must not be copied, imported, or used as active implementation source.

The live buildable workspace is:

```text
ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/
```

The live engineering knowledge map is:

```text
ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/docs/EKB/
```

## Explicit prohibitions

Do not use material under `docs/reference/` to:

```text
replace backend/*.py
replace src/*.ts or src/*.tsx
replace tests/*.py
infer current runtime behavior
infer current DIB behavior
infer current API behavior
infer current Finance/Snapshot behavior
make claims about implementation status
```

## Dangerous duplicates

Any implementation-looking file under this directory is a historical duplicate. Examples:

```text
backend/asie_local_api.py
backend/runtime_freeze.py
backend/project_run_workflow.py
backend/snapshot_assembly.py
src/*.tsx
tests/*.py
```

These may be read only as history. They are not current source.

## Cleanup path

Deletion or compaction of this archive requires a separate PR with CI and evidence that the material is not needed by live source, active EKB, or frozen architecture controls.
