# ASIE KIMI Output Review Gate

Use this before accepting any KIMI output.

## Gate 1: AAS Traceability

- Does the output name affected AAS documents?
- Does it use official AAS terminology?
- Does it avoid inventing new layers, controllers, buses, or hearts?

## Gate 2: Stack Compliance

- Frontend is React + TypeScript + Vite + pnpm.
- Python appears only in backend scope.
- Shared frontend contracts are TypeScript-safe.

## Gate 3: Message Flow

- No direct Module-to-Module communication.
- Every internal interaction passes through approved ASIE flow.
- Redis, Celery, WebSocket, and Supabase Realtime are not described as replacements for ASIE System Bus.

## Gate 4: Contracts and Sockets

- Every Module has Contract and Socket.
- Every Socket lists accepted and returned messages.
- Every capability has permission and validation rule.

## Gate 5: Zero Trust

- Default deny is preserved.
- Security Context exists.
- AI and Plugins are least-privilege.
- Audit fields exist.

## Gate 6: Provider Neutrality

- No vendor becomes architecture.
- AI providers are behind adapters/contracts.
- Database and auth choices remain replaceable mechanisms.

## Verdict

Classify output as:

- `Accept`
- `Accept with Corrections`
- `Reject`
- `ACP Required`

