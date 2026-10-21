---
name: graphify
description: Build or query a Graphify code relationship graph for ASIE using local deterministic AST extraction. Use for graph creation, dependency paths, and graph-backed architecture questions; preserve ASIE governance and GitHub-only source rules.
---

# Graphify for ASIE in Codex

This is an ASIE-specific Codex adapter for the official `graphifyy==0.9.92` CLI, not an unmodified upstream skill. It reuses Graphify rather than implementing a graph engine.

## Authority and inputs

- Read the current repository and canonical package `AGENTS.md`, EKB-09 and task-relevant EKB before engineering work. A graph is a derived navigation aid; it never replaces required source reads or grants implementation authority.
- Verify the target repository is `alphasigma13579-lang/ASIE` and record the source commit. Under the owner's GitHub-only rule, use GitHub APIs for source evidence. Do not clone ASIE, use the retired D: checkout, or download an ASIE corpus for local indexing without an explicit change to that boundary. If there is no authorized filesystem corpus, report this blocker; fixture validation is not an ASIE graph.
- For an already authorized filesystem corpus, restrict extraction to the requested active source paths. Exclude archive/reference/quarantine paths, secrets, tenant data, generated assets and runtime environments. Inspect the selected file list before extraction; do not scan the whole home or Codex folder.
- Keep AAS, Finance, Snapshot, release markers and application provider/network settings unchanged. Do not write Claude files or `CLAUDE.md`, register hooks, modify `AGENTS.md`, or alter user-level Codex configuration.

## Runtime

Read [references/setup.md](references/setup.md) when the pinned runtime is absent or setup is requested. Use the project-isolated interpreter there, not a global `graphify` executable or an automatic upgrade. No API key, account, paid service, MCP registration, Obsidian installation or multi-agent setting is required for the supported code-only flow.

## Build an authorized code-only graph

1. Record source repository/commit, selected source paths, exclusions, output location and installed Graphify version. Keep the output and runtime outside the selected input tree. Do not overwrite an existing graph without a recoverable copy.
2. Invoke the project interpreter with explicit paths (PowerShell example, from repository root):

```powershell
$graphifyPython = Join-Path (Get-Location) '.agents/skills/graphify/.venv/Scripts/python.exe'
& $graphifyPython -m graphify extract $approvedCodePath --code-only --max-workers 1 --out $approvedOutputParent
if ($LASTEXITCODE -ne 0) { throw 'Graphify extraction failed' }
```

Define `$approvedCodePath` and `$approvedOutputParent` from the authorized scope first. On Unix the interpreter is `.venv/bin/python`. Do not use `extract` without `--code-only`, or run `label`, semantic extraction, URL fetches, live database introspection, cloud/global graph export or watch mode under this installation grant. Separate authorization is needed for those operations; pre-existing API keys are not authorization.

3. Inspect `graphify-out/graph.json`: require nonempty nodes, source locations from the selected corpus and expected relationships. Surface parser failures, missing coverage and diagnostic warnings. Run:

```powershell
& $graphifyPython -m graphify diagnose multigraph --graph $graphJson --json
& $graphifyPython -m graphify explain $knownSymbol --graph $graphJson
```

4. Use `query`, `path` or `explain` with `--graph` pointing to this graph for subsequent navigation. Verify important results against current source at the recorded commit. Label inferred edges as inferred; absence from the graph is not proof of absence from source. Rebuild only after relevant source changes and renewed scope checks.
5. HTML is optional: `-m graphify export html --graph $graphJson`. Treat it as a local artifact; do not upload it. Check its generated location before reporting it. Code-only graphs omit document semantics and can miss dynamic relationships.

## Report

State the actual source commit, scope, runtime version, node/edge counts, expected relation/query evidence, outputs, warnings and untested behavior. Distinguish skill files present, runtime installed, Codex discovery observed, and ASIE graph built. Never infer a token-saving ratio from installation or a synthetic fixture; measure comparable tasks before claiming savings.
