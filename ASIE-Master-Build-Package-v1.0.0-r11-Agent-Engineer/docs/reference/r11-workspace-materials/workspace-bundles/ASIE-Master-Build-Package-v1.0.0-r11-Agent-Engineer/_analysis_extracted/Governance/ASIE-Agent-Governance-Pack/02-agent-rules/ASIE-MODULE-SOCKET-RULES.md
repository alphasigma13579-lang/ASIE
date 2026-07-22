# ASIE Module and Socket Rules

## Module Identity

Modules are not Plugins.

Examples of Modules:

- Financial Module
- Geo Module
- Research Module
- Document Module
- Market Module
- AI Module
- Export Module
- Notification Module
- Payment Module
- Compliance Module

## Required Module Fields

Every Module must define:

- Manifest
- Contract
- Capabilities
- Dependencies
- Configuration
- Health
- Lifecycle
- Permissions
- Socket bindings

## Socket Is The Contract

Every Socket must define:

- Socket ID
- Socket Type
- Protocol
- Accepted Messages
- Returned Messages
- Priority
- Permissions
- Required Capabilities
- Health Status
- Owner
- Version

## Communication Rule

Modules must not know each other directly.

Allowed path:

```text
Module -> Socket Contract Layer -> APP -> ASIE System Bus -> Bus Controller governance -> Target Socket -> Target Module
```

Forbidden path:

```text
Module -> Module
```

## Bus Controller Separation

Bus Controller governs:

- Module Discovery
- Module Loading
- Module Unloading
- Registration
- Contract Validation
- Version Compatibility
- Health Monitoring
- Priority Management
- Isolation
- Recovery

ASIE System Bus transports messages. It must not absorb all Bus Controller responsibilities.

## ASIE Market Intelligence Module Rule

Market data must be implemented through **ASIE Market Intelligence Module** only. Do not create a `Market Data Layer`. Do not let UI, AI Agent, Plugin, Finance Engine, or another Module call market providers directly. All market interactions must use approved market Socket Contracts.

