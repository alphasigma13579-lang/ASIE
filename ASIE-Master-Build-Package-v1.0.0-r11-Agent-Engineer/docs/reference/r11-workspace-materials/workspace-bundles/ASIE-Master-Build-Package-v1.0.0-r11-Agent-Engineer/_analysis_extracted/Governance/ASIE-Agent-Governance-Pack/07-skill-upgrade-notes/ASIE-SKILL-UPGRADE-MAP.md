# ASIE Skill Upgrade Map

Use this map to upgrade existing ASIE Skills.

## asie-aas-governor

Add references:

- `ASIE-GLOBAL-RULES.md`
- `ASIE-KIMI-BUILD-RULES.md`
- AAS Master Index
- AAS Glossary

Must enforce ACP triggers before implementation.

## asie-kimi-builder

Add references:

- `KIMI-MASTER-BUILD-PROMPT.md`
- `KIMI-OLD-ARCHITECTURE-MIGRATION-PROMPT.md`
- `ASIE-FRONTEND-BACKEND-RULES.md`
- `ASIE-KIMI-OUTPUT-REVIEW-GATE.md`

Must output AAS impact, files, contracts, security checks, and tests.

## asie-module-factory

Add references:

- `MODULE-CARD.template.md`
- `SOCKET-CONTRACT.template.md`
- `ASIE-MODULE-SOCKET-RULES.md`

Must reject Modules without Socket Contract.

## asie-security-auditor

Add references:

- `ASIE-ZERO-TRUST-RULES.md`
- AAS-20
- AAS-40
- AAS-50

Must treat AI and Plugins as untrusted by default.

## asie-architecture-reviewer

Add references:

- `ASIE-KIMI-OUTPUT-REVIEW-GATE.md`
- `OLD-KIMI-OUTPUT-JUDGMENT.md`
- `ASIE-GLOBAL-RULES.md`

Must lead with violations and classify each issue by severity.

