# BETA-PKG-01 — Dataset-to-DIB Mapping Completion

**Date:** 2026-07-27  
**Status:** implementation candidate; CI and merge required  
**Package:** ASIE Beta Readiness Program

## 1. Objective

Complete the controlled bridge from imported dataset rows to the existing Dynamic Input Blueprint without reopening DIB Runtime, Approved Input Manifest, Project Run Gate, or Controlled Finance Wiring.

## 2. Canonical flow

```text
CSV / XLSX / supported intake rows
→ data.intake.v1
→ dataset.dib.mapping.v1 draft
→ explicit user review per proposal
→ accepted dataset mapping
→ dynamic.input.blueprint.v1
→ approved.input.manifest.v1
→ manifest.validation.v1
→ controlled Finance
```

Raw dataset rows are never eligible to bypass the mapping review or Approved Input Manifest.

## 3. Added implementation

### `backend/dataset_dib_mapping.py`

Provides:

- deterministic mapping draft generation;
- stable mapping ID based on canonical project/file/row content;
- explicit `input_key` mapping at confidence `1.0`;
- alias-based deterministic matching using the existing DIB `ITEM_KEYWORDS` registry;
- ambiguity detection;
- numeric candidate extraction;
- user decisions: `accept`, `edit`, `reject`, `unresolved`;
- conversion only from a fully reviewed mapping into a DIB Blueprint;
- evidence references carrying mapping and row digests;
- intentional-zero handling;
- hard declaration that raw-input Finance bypass is forbidden.

## 4. Mapping contracts

### `dataset.dib.mapping.v1`

The mapping draft contains:

- `mapping_id`;
- project identity and project profile;
- the original governed intake result;
- one proposal per source row;
- proposed DIB input key and numeric value;
- confidence and reasons;
- row digest;
- review status and decision;
- policy snapshot.

### `dataset.dib.mapping.decision.v1`

Every proposal requires an explicit user decision. `edit` may correct the target input key and value. Rejected rows do not enter the DIB.

## 5. State rules

| Mapping state | DIB eligibility |
|---|---:|
| `review_required` | No |
| `unresolved` | No |
| `reject` | No |
| `accepted` | Yes |

The full mapping becomes `ready` only when no proposal remains unresolved or awaiting review and at least one proposal is accepted.

## 6. Zero-value control

An accepted dataset value of zero becomes `INTENTIONAL_ZERO`, not a generic imported zero. This preserves the existing Approved Input Manifest rule that rejects unjustified zeros.

## 7. Finance boundary

This package does not invoke Finance directly. It produces a DIB Blueprint only. Finance remains reachable through:

```text
DIB Blueprint
→ Approved Input Manifest
→ Manifest Validation
→ Controlled Finance Wiring
```

## 8. Frozen-runtime boundary

This package does not modify:

- `backend/aas_kernel.py`;
- `backend/heart_controller.py`;
- `backend/bus_controller.py`;
- `backend/system_bus.py`;
- `backend/socket_contracts.py`;
- `backend/module_runtime.py`;
- `backend/project_run_workflow.py`;
- `backend/snapshot_assembly.py`;
- `backend/runtime_freeze.py`;
- the Runtime Freeze Manifest.

It also does not change Finance calculations, Snapshot assembly, Decision Council, tenant isolation, or provider-network behavior.

## 9. Verification coverage

`tests/test_dataset_dib_mapping.py` verifies:

- deterministic mapping IDs;
- mandatory review;
- no blueprint before readiness;
- accepted rows reach the existing Approved Input Manifest;
- edit decisions correct key/value;
- rejected rows never reach the DIB;
- missing required rows block the manifest;
- intentional zero behavior;
- unknown proposals and invalid decisions are rejected.

## 10. Acceptance criteria

The package is accepted only when:

1. frontend build succeeds;
2. backend compilation succeeds;
3. all Python tests succeed;
4. no frozen runtime file changes;
5. raw dataset input cannot reach Finance directly;
6. a reviewed CSV dataset can produce an Approved Input Manifest that passes runtime validation.

## 11. Deferred from this package

The following remain separate work and are not silently claimed here:

- visual mapping-review workspace integration into the main user journey;
- PDF supplier-quote extraction quality;
- AI-assisted semantic mapping;
- live market evidence wiring;
- Product AI Interview.

The deterministic backend mapping contract is the beta-safe prerequisite for those later surfaces.
