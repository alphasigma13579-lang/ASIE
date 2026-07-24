# ASIE Project Orientation

This document is the “read this first” map for a programmer or coding agent.
It describes the product boundary, the current implementation, and the order
in which a feature should be built.

## Purpose

ASIE is a local-first decision platform for turning a project idea or project
data into a traceable financial and operational analysis. The platform keeps
Product AI, Market Intelligence, deterministic Finance, and sovereign decision
separate.

## One product flow, two entry paths

There are two valid customer starts:

| Entry path | What the customer has | What the platform does |
| --- | --- | --- |
| Idea-only | A location, sector, and short idea | A governed classifier selects a template; Product AI asks only decisive questions and proposes a first needs list |
| Data/file | Numbers, rough estimates, Excel, PDF, or supplier quotes | The platform maps and normalizes the data against the selected template and asks only clarifying questions |

Both paths meet at one place: **Dynamic Input Blueprint**. They do not create
separate financial models and they do not bypass the blueprint.

## The meeting point: Dynamic Input Blueprint

The blueprint is a governed collection of project items, not a universal form.
It changes with idea, Saudi location, precise sector, revenue model, operating
nature, project stage, financing, and available data.

Every item carries:

- why it appears;
- its state (`VALUE_ENTERED`, `CLIENT_ESTIMATE`, `INTENTIONAL_ZERO`,
  `NOT_APPLICABLE`, `UNKNOWN`, or `EXPERIMENTAL_ESTIMATE`);
- source and evidence lineage;
- Finance treatment;
- approval status.

Zero is valid when intentional and explained. Unknown is not the same as zero.
An item can be added, removed, or edited by the customer, including custom
operating costs, assets, financing, and variable costs.

## Research loop

The “search for an average” action stays inside the same item. It is not a
separate page and it does not send a number directly to Finance.

1. The item has a specific specification and is marked `UNKNOWN`.
2. A governed `market.query.request.v1` is emitted through Bus/Socket.
3. Market Intelligence returns an Evidence Pack with samples, links,
   cleaned units/currencies, P25-P75, weighted median, and outlier notes.
4. The customer or reviewer accepts a candidate assumption, selects a sample,
   or enters a different value.
5. Only the approved result enters the Approved Input Manifest.

Current development mode uses simulated evidence. AI providers are
`DISABLED` / `DENY_ALL` and external network is disabled.

## Finance and snapshots

Finance must read only the approved, normalized manifest. It remains
deterministic and does not infer missing values. A run seals a Snapshot. Later
changes create a Draft Revision, a new run, a new Snapshot, and a comparison of
financial impact, risks, readiness, payback, and financing.

The frozen runtime path is:

```text
Kernel -> Heart Controller -> Hearts -> Bus Controller -> ASIE System Bus
-> Socket Contract Layer -> Module Runtime -> Snapshot Assembly
```

## What is implemented today

- AAS runtime path, ModuleRuntime session boundary, and snapshot assembly.
- Deterministic Finance and existing scalar ProjectInputs flow.
- Local API, repository, evidence, decision, risk, execution, and report paths.
- Simulated study-driven Market Intelligence after financial study.
- Dataset/manual/file intake infrastructure and evidence linking.
- React/Vite client, runtime-freeze tests, and CI build/test workflow.

## Current implementation gaps

- The Dynamic Input Blueprint editor and governed template/question registries.
- Full per-item revision persistence and customer approval UI.
- File/manual mapping into the same blueprint item model.
- The governed Product AI interview and Template/Question registries.
- Mapping Excel/PDF/manual data into the same blueprint item model.
- Per-item research request returning to an editable blueprint item.
- Full template-aware Finance readiness for every revenue and operating model.

The first backend milestone is now implemented: `backend/input_manifest.py`
builds an `Approved Input Manifest` before the existing Finance socket,
`backend/finance_engine.py` reads its normalized inputs, and repository
metadata preserves zero reasons and treatment. The legacy scalar input path is
still retained for frozen parity fixtures and must not be mistaken for the
finished customer-facing blueprint.

These gaps are intentional and recorded in `ACR-DIB-001`; do not hide them by
renaming the existing scalar form “dynamic”.

## Build order for DIB work

1. Backend item/state/source/approval models and revision persistence.
2. Approved Input Manifest and validation gate.
3. Zero-aware repository and Finance validation semantics.
4. Deterministic Template Registry and Question Registry.
5. Blueprint editor and custom item controls.
6. Data/file mapping into blueprint items.
7. Simulated Market Intelligence item research behind existing contracts.
8. Draft Revision, rerun, and snapshot comparison.
9. Acceptance tests for both entry paths and runtime-freeze invariants.

## Change control

Use an ACR before changing the frozen runtime, socket contracts, bus topology,
external network policy, or AI provider policy. Keep implementation inside the
canonical workspace and keep historical bundles under `docs/reference/`.

## Verification

```bash
pnpm install --frozen-lockfile
pnpm build
python -m compileall -q backend
python -m unittest discover -s tests
```

If a document says a flow is planned but the status matrix says it is not
implemented, the status matrix and the code win. Record any new decision in a
current document or approved ACR.
