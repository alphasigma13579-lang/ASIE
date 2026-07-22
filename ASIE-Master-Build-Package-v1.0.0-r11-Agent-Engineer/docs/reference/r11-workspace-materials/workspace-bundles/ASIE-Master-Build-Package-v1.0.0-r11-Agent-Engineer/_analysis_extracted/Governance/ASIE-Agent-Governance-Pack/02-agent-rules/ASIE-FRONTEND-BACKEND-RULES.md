# ASIE Frontend and Backend Rules

## Frontend

Frontend must be built with:

- React
- TypeScript
- Vite
- pnpm
- Node.js ecosystem

Frontend may render UI, manage browser state, call approved APIs, and consume TypeScript-safe contract types.

Frontend must not:

- contain Python;
- access database internals directly;
- call AI providers directly;
- implement ASIE System Bus;
- implement Bus Controller or Heart Controller behavior;
- bypass backend API Contracts.

## Backend

Backend uses Python only for:

- API services;
- AI integration;
- Database access;
- backend orchestration;
- workers and queues;
- validation and policy enforcement.

Backend must not become ASIE Kernel unless specifically implementing Kernel scope under AAS-10.

## API Boundary

Every frontend-backend interaction must have:

- endpoint or operation name;
- request schema;
- response schema;
- auth requirement;
- authorization rule;
- audit requirement;
- failure mode;
- related AAS references.

## Shared Contracts

Frontend-facing contracts must be TypeScript-safe.

Python models may generate or mirror contracts, but frontend must not import Python internals.

