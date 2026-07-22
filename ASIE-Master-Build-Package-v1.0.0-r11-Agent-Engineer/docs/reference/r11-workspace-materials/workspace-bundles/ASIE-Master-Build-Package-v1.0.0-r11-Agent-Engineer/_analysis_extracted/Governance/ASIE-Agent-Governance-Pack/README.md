# ASIE Agent Governance Pack

This pack turns the ASIE AAS v1.0.0 Frozen Baseline into operational rules, KIMI build prompts, templates, and review gates.

## Authority

The source of truth is `01-aas-reference/`.

Authority order:

1. `AAS-01 — ASIE Constitution`
2. `AAS-02 — ASIE Operating Architecture`
3. Component-specific AAS document
4. `AAS-MI — ASIE Architecture Standard Master Index`
5. `AAS-GL — ASIE Architecture Standard Glossary`
6. `AAS-FAS — ASIE Final Adoption Statement`
7. `02-agent-rules/`
8. KIMI prompts, templates, and review gates

If any generated work conflicts with AAS, AAS wins.

## Structure

| Folder | Purpose |
| --- | --- |
| `01-aas-reference/` | Frozen AAS documents and official supporting decisions. |
| `02-agent-rules/` | Mandatory rules for Codex, KIMI, and other implementation agents. |
| `03-kimi-prompts/` | Prompt packs for implementation under AAS constraints. |
| `04-templates/` | Contract, Module, Socket, ACP, and review templates. |
| `05-review-gates/` | Acceptance gates before approving KIMI output. |
| `06-old-kimi-output-review/` | Migration judgment for KIMI output based on old architecture. |
| `07-skill-upgrade-notes/` | Notes for upgrading ASIE Skills to use this pack. |

## Core Rule

ASIE does not integrate with technologies.
ASIE integrates with Contracts.

Technologies such as Redis, PostgreSQL, Supabase, FastAPI, Vite, AI providers, and WebSockets are implementation mechanisms only. None of them may become architectural authority.

