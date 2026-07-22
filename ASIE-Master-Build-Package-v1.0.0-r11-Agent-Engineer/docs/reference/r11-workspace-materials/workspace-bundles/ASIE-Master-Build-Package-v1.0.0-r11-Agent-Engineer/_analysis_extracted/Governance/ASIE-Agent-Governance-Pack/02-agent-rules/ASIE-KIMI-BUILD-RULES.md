# ASIE KIMI Build Rules

KIMI is an implementation agent. KIMI must not redesign ASIE.

## Required Build Stack

| Area | Decision |
| --- | --- |
| Frontend runtime | Node.js ecosystem |
| Frontend framework | React |
| Frontend language | TypeScript; JavaScript only where unavoidable |
| Frontend build tool | Vite |
| Package manager | pnpm |
| Backend language | Python |
| Backend scope | API, AI integration, Database access, backend orchestration |

## Hard Prohibitions

- Do not use Python in frontend code, frontend routing, state, styling, UI components, or browser behavior.
- Do not use npm or yarn as the project package manager unless an ACP explicitly changes the stack. Use pnpm.
- Do not let Redis, Celery, asyncio, WebSocket, Supabase Realtime, or queues replace ASIE System Bus.
- Do not let FastAPI endpoints become direct Module-to-Module channels.
- Do not let frontend call AI providers directly.
- Do not let frontend call database or storage directly unless an approved API Contract explicitly permits the pattern.

## KIMI Output Requirements

Every KIMI task must produce:

1. affected AAS documents;
2. files to create or modify;
3. boundary statement;
4. contracts used or created;
5. security context;
6. message flow;
7. tests or acceptance checks;
8. explicit non-goals.

## Required Monorepo Shape

Use this default shape unless a later implementation decision overrides it without violating AAS:

```text
apps/
  frontend/        # React + TypeScript + Vite + pnpm
  backend/         # Python backend: API + AI + Database
packages/
  contracts/       # TypeScript-safe frontend contract types and shared schemas
  aas-rules/       # machine-readable guardrails, if generated later
docs/
  aas/             # AAS reference
  architecture/    # implementation architecture notes
```

## Migration Rule For Old KIMI Output

Old KIMI decisions are not automatically rejected. They must be classified:

- `Keep`: technology choice fits AAS and does not become authority.
- `Wrap`: technology is acceptable only behind Contract or Module.
- `Rename`: terminology conflicts with AAS and must be corrected.
- `Reject`: violates Frozen Architecture or creates bypass.
- `ACP`: changes core architecture and needs formal proposal.

