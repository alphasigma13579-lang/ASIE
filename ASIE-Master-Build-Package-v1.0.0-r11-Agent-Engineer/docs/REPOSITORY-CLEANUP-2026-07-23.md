# Repository Cleanup Record - 2026-07-23

## Scope

This cleanup makes the repository easier to enter and safer to maintain without changing Runtime behavior or deleting preserved reference material.

## Findings

- The runnable project is nested under `ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/`.
- `main` is the integration branch at the time of this record.
- The repository settings currently report `agent/asie-r11-ui-foundation` as the default branch. That branch is behind `main` and should be changed to `main` in GitHub repository settings by an owner.
- `docs/reference/r11-workspace-materials/` contains historical and extracted bundles. They are retained for provenance but are not runtime source.
- The repository had no root navigation README, root ignore policy, or editor policy. The existing `.github/workflows/asie-ci.yml` already selects the canonical workspace and was left unchanged.

## Changes in this cleanup

- Added a root README that points to the canonical workspace and records the AAS runtime path.
- Added a root `.gitignore` for Python, Node, local databases, generated output, secrets, and archives.
- Added `.editorconfig` for consistent text formatting.
- Added `docs/INDEX.md` with authority order and reference-boundary rules.
- Kept the existing `.github/workflows/asie-ci.yml` as the single CI workflow; no duplicate workflow is introduced.

## Deliberately not changed

- No Finance, Runtime, Bus, Socket, Module, Snapshot, or contract code.
- No deletion of historical workspace bundles or checksum records.
- No branch deletion or default-branch mutation through this PR.
- No activation of external network access or AI providers.

## Follow-up outside this cleanup

1. Set the GitHub default branch to `main`.
2. Review stale `agent/*` branches and delete only after confirming their work is merged or intentionally retained.
3. Merge ACR-DIB-001 before implementing Dynamic Input Blueprint Runtime changes.
