# ASIE Agent and Developer Guide

Read this file before changing the repository. It is the shortest path to the current source of truth.

## Start here

1. Read [`README.md`](README.md).
2. Read the Engineering Knowledge Base entry point: [`docs/EKB/README-AR.md`](ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/docs/EKB/README-AR.md).
3. Read [`ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/AGENTS.md`](ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/AGENTS.md).
4. Read the required EKB files for the task type in [`EKB-04-Agent-Reading-Order.md`](ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/docs/EKB/EKB-04-Agent-Reading-Order.md).
5. For runtime, naming, or API changes, also read the controlled registers and canonical documents referenced by EKB.

## Repository rules

- The runnable source is inside `ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/`.
- `PROGRAM-CLOSE-10` is the current program/remediation and release-authority source; dated package records remain evidence.\n- The EKB is the highest practical knowledge map for agents and engineers.
- Do not place long-lived architecture, engine behavior, market logic, DIB rules, prompt policy, or execution plans inside task prompts when they belong in `docs/EKB/`.
- `docs/reference/` is historical provenance. Do not use it as executable source or silently change it while implementing features.
- Preserve the frozen AAS path: `Kernel -> Heart Controller -> Hearts -> Bus Controller -> ASIE System Bus -> Socket Contract Layer -> Module Runtime -> Snapshot Assembly`.
- UI, Product AI, and Market Intelligence must not call Finance directly.
- A new bus, runtime layer, contract family, external network capability, or real AI provider requires an ACR before implementation.
- Finance reads approved, normalized assumptions only. It must not read raw chat output, raw files, or unapproved market candidates.
- Do not mutate an existing Snapshot. A changed model creates a Draft Revision and a new Snapshot.

## Archive lockdown

Historical and reference material is archive-locked. Agents and engineers must not copy, import, or use files from the following paths as live implementation source:

```text
ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/docs/reference/
ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/docs/reference/r11-workspace-materials/
ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/docs/reference/r11-workspace-materials/workspace-bundles/
ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/ASIE-Next-Task-Handoff-2026-07-19-v1.0.0/
```

Archive files are provenance only. They must not replace `backend/`, `src/`, `tests/`, active `docs/EKB/`, or any frozen AAS-controlled file. If an archive contains implementation-looking files such as `backend/asie_local_api.py`, `runtime_freeze.py`, or `snapshot_assembly.py`, treat them as `DANGEROUS_DUPLICATE`, not as current source.

For repository cleanup, read `docs/EKB/EKB-06-Repository-Surgery-Inventory.md` and `docs/REPOSITORY-SURGERY-PLAN-2026-07-26.md`. Deletions require a separate PR, evidence, and passing CI.

## Verify before opening a PR

From the canonical package directory:

```bash
corepack enable
pnpm install --frozen-lockfile
pnpm build
python -m compileall -q backend
python -m unittest discover -s tests
```

Keep AI providers disabled (`DISABLED` / `DENY_ALL`) and external network disabled in development unless a separate approved ACR changes those controls.
