# ASIE Agent and Developer Guide

Read this file before changing the repository. It is the shortest path to the
current source of truth.

## Start here

1. Read [`README.md`](README.md).
2. Read [`ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/AGENTS.md`](ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/AGENTS.md).
3. Read [`docs/PROJECT-ORIENTATION.md`](ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/docs/PROJECT-ORIENTATION.md).
4. Check [`docs/IMPLEMENTATION-STATUS-MATRIX.md`](ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/docs/IMPLEMENTATION-STATUS-MATRIX.md).
5. For the Dynamic Input Blueprint decision, read
   [`docs/ACR-DIB-001-Dynamic-Input-Blueprint.md`](ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/docs/ACR-DIB-001-Dynamic-Input-Blueprint.md).

## Repository rules

- The runnable source is inside
  `ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/`.
- `docs/reference/` is historical provenance. Do not use it as executable
  source or silently change it while implementing features.
- The frozen AAS path is:
  `Kernel -> Heart Controller -> Hearts -> Bus Controller -> ASIE System Bus -> Socket Contract Layer -> Module Runtime -> Snapshot Assembly`.
- UI, Product AI, and Market Intelligence must not call Finance directly.
- A new bus, runtime layer, contract family, external network capability, or
  real AI provider requires an ACR before implementation.
- Finance reads approved, normalized assumptions only. It must not read raw
  chat output, raw files, or unapproved market candidates.
- Do not mutate an existing Snapshot. A changed model creates a Draft Revision
  and a new Snapshot.

## Current product boundary

The idea-only path and the data/file path meet at the governed `Dynamic Input
Blueprint`. They do not meet at the Finance Engine. Every item needs a state,
reason, source, treatment, and approval before it can enter the
`Approved Input Manifest`.

`ACR-DIB-001` is merged and governs the implementation plan. The runtime
implementation is not complete yet; use the status matrix instead of
assuming that a documented flow is already executable.

## Verify before opening a PR

From the canonical package directory:

```bash
corepack enable
pnpm install --frozen-lockfile
pnpm build
python -m compileall -q backend
python -m unittest discover -s tests
```

Keep AI providers disabled (`DISABLED` / `DENY_ALL`) and external network
disabled in development unless a separate approved ACR changes those controls.
