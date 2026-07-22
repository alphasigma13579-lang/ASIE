# ASIE AI and Plugin Rules

## AI

AI providers and AI agents are replaceable capability providers behind Contracts.

Allowed:

- Kimi, Llama, DeepSeek, Qwen, OpenAI, or another provider behind an AI Contract.
- AI Module that exposes approved capabilities.
- AI Adapter inside backend scope.
- AI output after deterministic validation.

Forbidden:

- direct frontend-to-AI provider calls;
- AI provider as architectural authority;
- AI output as final truth;
- AI modifying Kernel, Contract, Socket, Module registry, or security policy;
- AI bypassing ASIE System Bus or APP.

## Plugins

Plugins extend capability. Plugins must not redefine architecture.

Allowed:

- Plugin with Manifest, identity, permissions, lifecycle, and approved Contracts.
- Plugin that communicates through approved channels.

Forbidden:

- Plugin creating alternative System Bus;
- Plugin bypassing Socket Contract Layer;
- Plugin directly accessing another Module's data;
- Plugin expanding its own permissions;
- Plugin disabling Audit or Observability;
- Plugin becoming Truth Owner outside its approved scope.

## Provider Neutrality

ASIE must remain provider-neutral. A provider may be replaced without changing the Frozen Architecture.

## Market Evidence AI Rule

AI may summarize or explain Market Evidence Packs, but must not invent market numbers, fill missing supplier prices, override Finance Engine outputs, or choose source authority. Missing data must be marked unavailable or requested through the approved market contract.

