# Graphify installation evidence — 2026-10-17

## Scope and plan

Owner request: install Graphify for ASIE in Codex at project scope, inspect current repository/skills/AGENTS first, preserve Claude files and AAS, and perform an initial test. This is the bounded engineering task record: inspect authority and official upstream; prepare a repository-scoped CLI adapter; validate it against synthetic code; publish an isolated review branch. Safe checkpoint: reviewable commit, no merge, no application/provider execution and no ASIE clone or corpus extraction. Scope excludes application changes and token-saving claims.

ASIE source inspected through GitHub APIs only, base commit `e5e13f672161a283c82634cf8df946d6e90b0aa9`. Its recursive tree was complete (`truncated=false`); no existing `.agents/skills`, `.codex/skills`, or Graphify path was present. No open Graphify PR was found. Root/canonical AGENTS, README, PROGRAM-CLOSE-10 and EKB entry/order/knowledge-map/inventory/source-matrix/prompt-policy/goal contract were read. The installed ASIE RC4 overlay and reference skill inventory were inspected without modification. The retired ASIE D: copy was not used.

## Source and compatibility

Official repository: `Graphify-Labs/graphify`, reviewed commit `86c57be8204673c2a1b9849a3292a7dd3ab373d8`, version `0.9.92`. Verified official package name: `graphifyy` (double y). PyPI installation metadata points back to the same repository. Official license is Apache-2.0 with retained MIT portions.

OpenAI documents repository discovery under `.agents/skills/`. Upstream's Codex installer currently targets `.codex/skills`, injects AGENTS instructions and registers hooks. Its full Codex skill includes auto-install/upgrade and semantic/GitHub-clone workflows incompatible with this bounded ASIE installation. The delivered skill is explicitly a compact project adapter for the official CLI, not a byte-for-byte installation of that upstream skill. It preserves ordinary skill discovery, without changing global configuration or automatic invocation policy.

## Actual local validation

Installed only into a disposable environment under this chat's `work/graphify-runtime`, using Python 3.14.6 and `graphifyy==0.9.92`, with binary distributions from PyPI. Thirty packages installed; no optional extras were selected. This is a smoke runtime, not a permanent ASIE runtime. The project setup instructions use an ignored `.venv` inside the skill and pin the direct dependency; transitive dependencies are not fully locked.

Command: `python -m graphify extract <synthetic-input> --code-only --max-workers 1 --out <separate-output>`.

| Check | Observed result |
|---|---|
| Input | 3 synthetic files: 2 Python, 1 TypeScript; no ASIE code or tenant data |
| Extract | Exit 0; 7 nodes, 8 edges, 2 communities |
| Expected cross-file Python call | `total_order() -> subtotal()`, EXTRACTED, order.py:L5 |
| Expected TypeScript call | `renderTotal() -> formatTotal()`, EXTRACTED, view.ts:L6 |
| Path/query/explain | Exit 0, expected symbols and source locations returned |
| Graph diagnostics | No dangling/missing endpoints, self-loops, exact duplicates or collapsed endpoint pairs in this fixture |
| HTML export | Exit 0; graph.html produced (25,848 bytes) |
| pip check | Exit 0; no broken requirements |
| Basic skill checks | Frontmatter name/description, setup reference and pinned requirement verified |
| Official quick_validate.py | Could not run: PyYAML absent in both inspected Python environments; no extra dependency installed |

No ASIE suite was run because only skill instructions/setup metadata are added and the source-of-truth boundary excludes a local ASIE checkout. These fixture results do not qualify the full application, all Graphify languages, semantic extraction, actual Codex host discovery, or token savings. Code-only headless extraction produced graph.json and analysis; GRAPH_REPORT.md was not generated or claimed. No API backend was configured for this test; network packet capture was not performed.

## Protected boundaries and remaining gate

Only `.agents/skills/graphify/` is allowed in this change. Root/package AGENTS, Claude/CLAUDE files, AAS, Finance, Snapshot, EKB, application manifests, provider/network policy, global skill folders and Codex user config remain outside the change. Existing governance instructions are not replaced by a derived graph.

State at handoff: project skill prepared and fixture-validated on a review branch; not merged into main, not observed in a fresh ASIE Codex session, no ASIE graph built. After owner-approved merge, a Codex environment using the updated repository must verify `$graphify` discovery. Creating a local ASIE corpus additionally requires an explicit change to the GitHub-only boundary; this installation does not grant it. Revert the skill addition for repository rollback; no AAS or application rollback is needed.
