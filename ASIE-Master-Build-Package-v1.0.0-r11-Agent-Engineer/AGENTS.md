# Canonical Workspace Guide

This directory is the buildable ASIE workspace. Run commands from here.

## Start here

Before implementation, read the Engineering Knowledge Base:

1. `docs/EKB/README-AR.md`
2. `docs/EKB/EKB-00-Knowledge-Map.md`
3. `docs/EKB/EKB-01-Verified-Document-Inventory.md`
4. `docs/EKB/EKB-02-Source-of-Truth-Matrix.md`
5. `docs/EKB/EKB-04-Agent-Reading-Order.md`
6. `docs/EKB/EKB-05-Prompt-Policy.md`
7. The relevant domain file under `docs/EKB/domains/`
8. For repository cleanup, archive lockdown, or deletion work: `docs/EKB/EKB-06-Repository-Surgery-Inventory.md`

`PROGRAM-CLOSE-10` is the current program/remediation and release-authority source. Dated execution records are evidence, not current-state overrides.\n\nThe EKB is the reference for where knowledge lives. Long-lived requirements, engine rules, DIB behavior, market estimation logic, and governance controls belong in EKB/domain documents, not inside oversized task prompts.

## Map

| Path | Responsibility |
|---|---|
| `backend/` | Local API, repository, AAS runtime, modules, Finance, evidence, decision, risk, execution, snapshots |
| `src/` | React/Vite client and client contracts |
| `tests/` | Deterministic Python tests, including runtime-freeze invariants |
| `docs/` | Current architecture, ACRs, EKB, runbooks, orientation, and status |
| `docs/EKB/` | Engineering Knowledge Base and agent reading policy |
| `public/` | Frontend static assets |
| `tools/` | Development and packaging helpers |
| `docs/reference/` | Archive-locked historical material; never the executable source of truth |

## Archive lockdown

`docs/reference/`, `docs/reference/r11-workspace-materials/`, `docs/reference/r11-workspace-materials/workspace-bundles/`, and `ASIE-Next-Task-Handoff-2026-07-19-v1.0.0/` are archive-locked zones. They may be read for provenance only.

Do not copy source-looking files from those zones into live paths. Do not use archived `backend/*.py`, `src/*.tsx`, `tests/*.py`, or frozen-runtime-looking files as implementation source. If an archived file conflicts with active EKB or live source, active EKB and live source win.

Repository cleanup and deletion must follow `docs/REPOSITORY-SURGERY-PLAN-2026-07-26.md`. Deletion requires a dedicated PR, evidence, and passing CI.

## Architectural boundary

Preserve this path for every runtime change:

```text
Kernel -> Heart Controller -> Hearts -> Bus Controller -> ASIE System Bus
-> Socket Contract Layer -> Module Runtime -> Snapshot Assembly
```

Do not add direct UI-to-Finance, AI-to-Finance, internet-to-Finance, or Market-to-Finance calls. Market Intelligence remains a module behind the existing Bus/Socket boundary. AI may classify, explain, ask, and propose; it does not own final numbers, NPV, IRR, DSCR, or the sovereign decision.

## Product implementation status

`ACR-DIB-001` defines the approved direction for the Dynamic Input Blueprint and Approved Input Manifest. The EKB distinguishes implemented, partial, planned, reference-only, and blocked work. Do not infer implementation from documentation alone.

## Commands

```bash
pnpm install --frozen-lockfile
pnpm build
python -m compileall -q backend
python -m unittest discover -s tests
python backend/asie_local_api.py
```

The CI workflow is `.github/workflows/asie-ci.yml` at repository root.
