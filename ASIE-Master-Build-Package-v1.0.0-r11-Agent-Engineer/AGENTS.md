# Canonical Workspace Guide

This directory is the buildable ASIE workspace. Run commands from here.

## Map

| Path | Responsibility |
| --- | --- |
| `backend/` | Local API, repository, AAS runtime, modules, Finance, evidence, decision, risk, execution, snapshots |
| `src/` | React/Vite client and client contracts |
| `tests/` | Deterministic Python tests, including runtime-freeze invariants |
| `docs/` | Current architecture, ACRs, runbooks, orientation, and status |
| `public/` | Frontend static assets |
| `tools/` | Development and packaging helpers |
| `docs/reference/` | Preserved historical material; never the executable source of truth |

## Runtime entry points

- `backend/asie_local_api.py`: loopback development API and HTTP routing.
- `backend/project_run_workflow.py`: production project-run orchestration.
- `backend/module_runtime.py`: session-scoped module execution boundary.
- `backend/socket_contracts.py` and `backend/system_bus.py`: contract and bus enforcement.
- `backend/finance_engine.py`: deterministic financial calculations and current legacy validation.
- `backend/repository.py`: project, assumption, dataset, evidence, and snapshot persistence.
- `backend/snapshot_assembly.py`: immutable snapshot assembly and sealing.
- `tests/test_runtime_freeze.py`: protects the frozen runtime path.

`build_overview` in the local API is a deprecated compatibility wrapper for
legacy parity tests. New work belongs in `ProjectRunWorkflow`.

## Architectural boundary

Preserve this path for every runtime change:

```text
Kernel -> Heart Controller -> Hearts -> Bus Controller -> ASIE System Bus
-> Socket Contract Layer -> Module Runtime -> Snapshot Assembly
```

Do not add a direct UI-to-Finance, AI-to-Finance, internet-to-Finance, or
Market-to-Finance call. Market Intelligence remains a module behind the
existing Bus/Socket boundary. AI may classify, explain, ask, and propose; it
does not own final numbers, NPV, IRR, DSCR, or the sovereign decision.

## Product implementation status

`ACR-DIB-001` defines the approved direction for the Dynamic Input Blueprint
and Approved Input Manifest. The current runtime still has scalar/static
`ProjectInputs`, repository logic that treats numeric zero as non-meaningful,
and a Finance payload based on `project.inputs`. Treat those as explicit gaps,
not as completed features.

Before changing Finance input semantics, add the required tests and preserve
the runtime-freeze invariants. Before enabling external research or a real AI
provider, obtain a separate ACR.

## Commands

```bash
pnpm install --frozen-lockfile
pnpm build
python -m compileall -q backend
python -m unittest discover -s tests
python backend/asie_local_api.py
```

The CI workflow is `.github/workflows/asie-ci.yml` at repository root.
