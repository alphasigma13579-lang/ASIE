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
- The EKB is the highest practical knowledge map for agents and engineers.
- Do not place long-lived architecture, engine behavior, market logic, DIB rules, prompt policy, or execution plans inside task prompts when they belong in `docs/EKB/`.
- `docs/reference/` is historical provenance. Do not use it as executable source or silently change it while implementing features.
- Preserve the frozen AAS path: `Kernel -> Heart Controller -> Hearts -> Bus Controller -> ASIE System Bus -> Socket Contract Layer -> Module Runtime -> Snapshot Assembly`.
- UI, Product AI, and Market Intelligence must not call Finance directly.
- A new bus, runtime layer, contract family, external network capability, or real AI provider requires an ACR before implementation.
- Finance reads approved, normalized assumptions only. It must not read raw chat output, raw files, or unapproved market candidates.
- Do not mutate an existing Snapshot. A changed model creates a Draft Revision and a new Snapshot.

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
