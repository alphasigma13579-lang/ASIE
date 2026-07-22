# ASIE Zero Trust Rules

Zero Trust is a security envelope around all ASIE layers. It is not a new ASIE layer.

## Default Trust

No entity is trusted by default:

- User
- Module
- Plugin
- AI Agent
- API client
- Provider
- Database
- Queue
- Internal service

## Enforcement Points

Security policy must be enforced before execution at:

- API request
- Module activation
- Contract binding
- Socket binding
- Message dispatch
- Provider invocation
- AI invocation
- Database access

## AI Security

AI is untrusted by default.

AI must not:

- own final truth;
- modify Contract;
- modify ASIE Kernel;
- bypass ASIE System Bus;
- disable Module;
- make irreversible policy decisions without deterministic validation.

Use this principle:

```text
Deterministic Code Owns the Truth.
AI Explains the Truth.
```

## Database Security

RLS, JWT, Supabase Auth, Casbin, and RBAC are mechanisms, not architecture.

They may enforce policy, but they do not replace AAS, APP, Contracts, Socket Contract Layer, or Bus Controller governance.

## Violation Defaults

If validation fails, deny.
If policy cannot be evaluated, deny.
If Contract is missing, deny.
If Socket is not auditable, deny.
If Module attempts direct communication, isolate.

## Market Data Zero Trust Rule

AI Agents, Plugins, UI Components, and Modules must not directly access market providers, price sources, or RAG Cache. Market requests must pass through ASIE Market Intelligence Module and approved Socket Contracts, with audit events for rejection and provider bypass attempts.

