# Old KIMI Output Judgment

This file reviews `ماذا قام به KIMI على المعمارية السا(1).txt` as old-architecture output.

## Verdict

Partially usable as technology selection material.

Not acceptable as final ASIE architecture.

## Keep

| Decision | Condition |
| --- | --- |
| React + TypeScript | Add Vite and pnpm explicitly. |
| Python + FastAPI backend | Backend only: API, AI, Database, orchestration. |
| PostgreSQL + pgvector | Persistence mechanism only. |
| Redis/Celery | Queue/workers only, not ASIE System Bus. |
| WebSocket | Transport mechanism only. |
| Multiple AI providers | Behind AI Contracts only. |

## Wrap

| Decision | Required Boundary |
| --- | --- |
| Supabase Auth | Auth mechanism behind Zero Trust policy. |
| Supabase Realtime | Notification/transport mechanism, not System Bus. |
| AI Orchestrator | AI Module or backend adapter behind Contract. |
| Swarm Controller | Must not become architectural controller. |
| Payment | Payment Module with Contract and Socket. |
| Report Engine | Document/Export Module with Contract and Socket. |

## Rename

| Old Term | Correct AAS Treatment |
| --- | --- |
| Event Bus | Implementation event mechanism, not ASIE System Bus. |
| AI Orchestrator | AI capability/service behind Contract. |
| Swarm Controller | AI workflow component, not ASIE Controller. |
| Backend Architecture | Implementation architecture under AAS, not ASIE architecture itself. |

## Reject

- Any direct Module-to-Module communication.
- Any Redis Pub/Sub path described as the official ASIE System Bus.
- Any AI provider called directly by frontend or Module without Contract.
- Any database/auth mechanism described as architectural source of truth.
- Any new Controller not approved by AAS.

## ACP Required

- Adding a real new controller.
- Replacing ASIE System Bus with a technical queue.
- Changing Bus Controller responsibilities.
- Making AI Orchestrator a system-level authority.
- Changing Kernel, Heart Controller, Three Hearts, Bus Controller, System Bus, or Socket Contract Layer boundaries.

