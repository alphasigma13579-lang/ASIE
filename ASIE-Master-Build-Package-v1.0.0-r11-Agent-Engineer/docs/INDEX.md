# ASIE Documentation Index

This directory separates current operating documents from imported historical material.

## Authority order

When documents disagree, use this order:

1. `docs/ASIE-AAS-Runtime-Freeze-Manifest-v1.0.json` for frozen runtime facts.
2. Current `docs/` architecture, contract, release, and runbook records.
3. An approved ACR for a new product or contract decision.
4. `docs/reference/` only as provenance and historical context.

## Read first\n\n- [`../AGENTS.md`](../AGENTS.md): repository and agent rules.\n- [`AGENTS.md`](../AGENTS.md): canonical workspace guide.\n- [`PROJECT-ORIENTATION.md`](./PROJECT-ORIENTATION.md): product and implementation map.\n- [`IMPLEMENTATION-STATUS-MATRIX.md`](./IMPLEMENTATION-STATUS-MATRIX.md): status boundary for implementation work.\n\n## Current documents

- `ASIE-AAS-Runtime-Freeze-Manifest-v1.0.json`: frozen runtime files, contract sequence, and ACR control.
- `ASIE-Complete-System-Architecture-2026-07-21.md`: current architecture narrative.
- `ASIE-Post-Freeze-Work-Plan-2026-07-19.md`: post-freeze implementation direction.
- `ASIE-Project-Status-Assessment-2026-07-21.md`: latest recorded readiness assessment.
- `ACR-*.md`: architectural or product change records. `ACR-DIB-001` is merged and governs the Dynamic Input Blueprint implementation.

## Reference and archive material

`docs/reference/r11-workspace-materials/` contains imported workspace material, correction packs, prompts, and historical bundles. These files are searchable and preserved for provenance, but they are not executable code and do not override current `docs/` records.

Large extracted bundles intentionally remain under that reference boundary. New implementation files must not be added there; put executable code under the canonical workspace and current decisions under `docs/`.

## Dynamic Input Blueprint

The two user entry paths meet at `Dynamic Input Blueprint` before `Approved Input Manifest` and Finance. The governing record is [ACR-DIB-001](./ACR-DIB-001-Dynamic-Input-Blueprint.md), merged into `main`.
