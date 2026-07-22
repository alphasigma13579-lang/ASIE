# ASIE Global Agent Rules

## Binding Reference

All ASIE work must comply with `AAS v1.0.0 Frozen Baseline`.

An agent must treat the AAS package as the architectural source of truth, not prior conversation memory, old KIMI output, framework defaults, or vendor documentation.

## Non-Negotiable Architecture

1. Do not add a new ASIE layer.
2. Do not add a new Controller.
3. Do not add a new Bus.
4. Do not add a fourth Heart.
5. Do not bypass ASIE System Bus.
6. Do not allow direct Module-to-Module communication.
7. Do not run any Module without Socket Contract.
8. Do not communicate outside APP when the interaction is inside ASIE.
9. Do not place business logic in ASIE Kernel.
10. Do not let Hearts execute business logic.
11. Do not let AI, Plugin, Provider, Database, Queue, or Framework become architectural authority.

## Golden Rule

ASIE does not integrate with technologies.
ASIE integrates with Contracts.

Every technology must sit behind one of these controlled boundaries:

- API Contract
- Socket Contract
- Module Contract
- Plugin Contract
- AI Contract
- Data Access Contract

## Component Boundaries

| Component | Allowed Role | Forbidden Role |
| --- | --- | --- |
| ASIE Kernel | Boot, configuration loading, runtime initialization | Business engine, provider adapter, AI router |
| Heart Controller | Manage Heart state, distribution, recovery | Business logic executor |
| Three Hearts | Runtime execution roles under Controller | Security bypass, Module authority |
| Bus Controller | Registry, validation, compatibility, isolation, participation governance | Broker, Kernel, business router |
| ASIE System Bus | Official message transport | Business logic, direct provider integration |
| Socket Contract Layer | Contract enforcement for Sockets | Generic API layer |
| Modules | Functional capability implementation | Direct peer communication, Kernel mutation |
| Plugins | Controlled external extensions | Internal core component, architecture modifier |
| AI | Assisted capability behind Contract | Truth owner, final authority, policy owner |
| Database | Persistence and retrieval | Architectural source of truth |

## ACP Triggers

Require an Architecture Change Proposal before any change that:

- changes Kernel, Heart Controller, Three Hearts, Bus Controller, ASIE System Bus, Socket Contract Layer, or Module responsibilities;
- adds a core component, layer, controller, bus, or heart;
- changes the trust model, authorization authority, message path, or source-of-truth ownership;
- lets AI, Plugin, Provider, Database, Queue, or Framework redefine architecture;
- changes official AAS terminology.

## Default Decision

If an agent cannot prove compliance, it must stop and mark the work as `Needs Review` or `ACP Required`.

