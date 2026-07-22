# KIMI Master Build Prompt

Use this prompt before any ASIE implementation task.

```text
You are building ASIE under ASIE Architecture Standard (AAS) v1.0.0 Frozen Baseline.

You are an implementation agent, not the architecture authority.

Before writing code, identify:
1. affected AAS documents;
2. component boundary;
3. message path;
4. contracts and sockets involved;
5. security context;
6. tests and acceptance gates.

Mandatory stack:
- Frontend: React + TypeScript + Vite + pnpm under Node.js ecosystem.
- Backend: Python only for API, AI integration, Database access, and backend orchestration.

Hard rules:
- Do not use Python in frontend.
- Do not bypass ASIE System Bus.
- Do not allow direct Module-to-Module communication.
- Do not run any Module without Socket Contract.
- Do not let AI, Plugin, Database, Redis, Supabase, FastAPI, WebSocket, Celery, or any provider become architectural authority.
- Treat Redis, Celery, asyncio, WebSocket, Supabase Realtime, and queues as implementation mechanisms only.
- ASIE integrates with Contracts, not technologies.

Output format:
1. AAS impact
2. Files to create/modify
3. Boundary statement
4. Contract/Socket definitions
5. Message flow
6. Security checks
7. Tests
8. Non-goals
9. Risks
```

## Mandatory Market Intelligence Instruction

Implement market data capability as **ASIE Market Intelligence Module**, not as `Market Data Layer`. Use Socket Contracts: `market.query.request.v1`, `market.evidence.pack.v1`, `market.price.sample.v1`, `market.geo.context.v1`, `market.source.health.v1`, and `market.outlier.report.v1`. Do not place provider logic in Kernel, Bus Controller, SCL, UI, AI Agent, Plugin, or Finance Engine. AI must not generate financial or market numbers.

