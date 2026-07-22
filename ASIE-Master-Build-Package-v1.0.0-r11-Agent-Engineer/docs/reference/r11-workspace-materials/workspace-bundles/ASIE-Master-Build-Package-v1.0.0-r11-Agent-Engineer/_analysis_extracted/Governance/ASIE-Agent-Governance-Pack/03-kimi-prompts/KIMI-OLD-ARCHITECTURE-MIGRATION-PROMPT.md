# KIMI Old Architecture Migration Prompt

Use this when converting old KIMI output into the new AAS-compliant architecture.

```text
Review the old architecture output as migration material only.

Classify every decision as:
- Keep: acceptable as-is under AAS.
- Wrap: acceptable only behind Contract, Socket, Module, or API boundary.
- Rename: terminology must be corrected to AAS official terms.
- Reject: violates Frozen Architecture.
- ACP: requires Architecture Change Proposal.

Pay special attention to:
- Event Bus vs ASIE System Bus.
- Redis/Celery/asyncio as implementation mechanisms only.
- Supabase/Auth/RLS as mechanisms, not architectural authority.
- AI Orchestrator and Swarm Controller behind AI Contracts only.
- Python backend only.
- React + TypeScript + Vite + pnpm frontend only.

Do not propose a new architecture. Preserve AAS v1.0.0.
```

