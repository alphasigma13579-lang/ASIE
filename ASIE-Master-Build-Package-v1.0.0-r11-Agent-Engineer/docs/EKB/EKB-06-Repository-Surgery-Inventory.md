# EKB-06 — Repository Surgery Inventory

**Status:** RC1  
**Date:** 2026-07-26  
**Scope:** ASIE r11 repository hygiene, archive lockdown, and live-source protection.

## 1. Purpose

This inventory classifies repository material so agents, engineers, and automation can distinguish current buildable source from historical material. Its purpose is to prevent stale archive files from being copied, imported, or treated as authoritative in the live ASIE workspace.

## 2. Binding rule

The live source of truth remains:

```text
ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/
```

The current engineering reading order remains governed by:

```text
docs/EKB/README-AR.md
docs/EKB/EKB-00-Knowledge-Map.md
docs/EKB/EKB-01-Verified-Document-Inventory.md
docs/EKB/EKB-02-Source-of-Truth-Matrix.md
docs/EKB/EKB-04-Agent-Reading-Order.md
docs/EKB/EKB-05-Prompt-Policy.md
```

No archive, handoff package, correction archive, extracted workspace bundle, or historical backend copy may override the live package or EKB.

## 3. Classification labels

| Label | Meaning | May be used for implementation? |
|---|---|---:|
| `LIVE` | Current buildable source, tests, active docs, active EKB | Yes |
| `REFERENCE` | Useful background only; not authoritative for current implementation | No direct copy |
| `ARCHIVE_LOCKED` | Historical preserved material; read-only provenance | No |
| `DANGEROUS_DUPLICATE` | Old copy of a live runtime/API/source file in archive/reference paths | No |
| `DELETE_CANDIDATE` | Candidate for later deletion after evidence review and CI-safe PR | No |
| `DO_NOT_TOUCH` | Frozen AAS, active EKB, AGENTS, CI, or active runtime guard files | Only under governing rules |

## 4. Live protected paths

These paths are current and protected from archive replacement:

```text
backend/
src/
tests/
docs/EKB/
docs/ASIE-AAS-Runtime-Freeze-Manifest-v1.0.json
AGENTS.md
ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/AGENTS.md
.github/workflows/asie-ci.yml
```

## 5. Archive-locked zones

The following zones are **archive-locked**. Files inside them must not be copied into live paths, imported by code, or used to infer current implementation status without checking EKB and live source.

```text
docs/reference/
docs/reference/r11-workspace-materials/
docs/reference/r11-workspace-materials/workspace-bundles/
ASIE-Next-Task-Handoff-2026-07-19-v1.0.0/
```

## 6. Dangerous duplicate indicators

The following patterns are high-risk when found inside archive/reference/handoff folders:

```text
*/backend/*.py
*/src/*.tsx
*/src/*.ts
*/tests/*.py
*/runtime_freeze.py
*/asie_local_api.py
*/snapshot_assembly.py
*/project_run_workflow.py
*/aas_registry.py
*/module_runtime.py
```

These files may be kept temporarily for provenance, but they are `DANGEROUS_DUPLICATE` and must never be treated as implementation input.

## 7. Initial observed risk areas

The repository currently includes historical workspace bundles and correction archives that contain old implementation-looking files. Examples include archived copies of backend/runtime files under:

```text
docs/reference/r11-workspace-materials/workspace-bundles/ASIE-Architecture-Correction-Archive-2026-07-19-v1.1.0/
docs/reference/r11-workspace-materials/workspace-bundles/ASIE-Architecture-Correction-Archive-2026-07-19-v1.1.1/
docs/reference/r11-workspace-materials/workspace-bundles/ASIE-Next-Task-Handoff-2026-07-19-v1.0.0/
ASIE-Next-Task-Handoff-2026-07-19-v1.0.0/
```

These are not live code. They are locked as historical provenance until a later deletion PR removes or compacts them.

## 8. Agent lockdown rule

Before editing any live file, an agent must:

1. Ignore archive-locked source-looking files as implementation candidates.
2. Read active EKB and active source files only.
3. Treat archive files as evidence of history, not current behavior.
4. Refuse to replace a live file with content from `docs/reference/` or any handoff/archive bundle.
5. Open a small PR with CI for each cleanup/deletion step.

## 9. Deletion policy

Deletion requires a later PR that proves:

```text
not imported by live code
not required by tests/CI
not referenced by active EKB as source of truth
not a frozen AAS file
not the only copy of an active architectural decision
```

Until then, archive material is locked, not deleted.

## 10. Current R1 decision

`Repository Surgery Package R1` does not delete old files. It establishes:

```text
Archive Lockdown = ACTIVE
Dangerous Duplicate Handling = ACTIVE
Live Source Replacement From Archive = PROHIBITED
Deletion Requires Later Evidence PR = REQUIRED
```
