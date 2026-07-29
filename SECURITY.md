# Security Policy — ASIE

## Supported versions

| Branch | Status |
|---|---|
| `main` | Supported for security remediation and private technical validation |
| `agent/*`, `feat/*`, `chore/*`, `emergency/*`, `security/*` | Working branches; not release surfaces |

## Controlled unfreeze state

The emergency remediation marker is `CLEARED / PENDING_GATE` under
`GOV-REL-10-CONTROLLED-UNFREEZE-EXECUTION`. This state permits the
evidence-backed gate to evaluate the exact commit; it does not authorize a
public beta, production deployment, provider activation, external fetch, or
external network exposure.

The canonical machine-readable control is
`EMERGENCY-RELEASE-FREEZE.json`. A cleared marker is accepted only when its
controlled-unfreeze proof matches the governed eligibility evidence. Missing,
weak, or tampered proof fails closed.

Permitted after a successful exact-commit gate:

- private loopback-only smoke validation;
- technical limited evaluation with external capabilities degraded.

Still prohibited:

- public ports, including `80` or `443`;
- public beta or production deployment;
- AI/provider activation or external network fetch;
- removal or mutation of the AAS Runtime Freeze.

## Reporting a vulnerability

Do not open a public issue for security reports.

Use **GitHub private vulnerability reporting** ("Security" tab → "Report a
vulnerability") on this repository. Include the affected route or module, the
request sequence, whether the impact crosses an organization boundary, and
whether it touches a frozen runtime file.

You can expect an acknowledgment within 3 business days and a remediation plan
or rejection rationale within 14 days.

## Intended security model

- **Local-first**: external network fetch and AI providers are disabled by
  default; enabling them requires an approved ACR and a separate release
  decision.
- **Authentication**: zero-user access fails closed; production bootstrap
  requires governed initialization; public password recovery issues no bearer
  secret and cannot complete without an approved delivery channel.
- **Authorization**: organization membership, record ownership, and role
  permissions are enforced server-side.
- **DIB persistence**: tenant ownership is stored and checked, and SQLite work
  uses request-safe transaction lifecycles.
- **Finance admission**: server-owned Manifest and Validation Gate lineage must
  enter through the canonical ProjectRunWorkflow.
- **Audit**: security events remain append-only through supported code paths.
- **HTTP hardening**: origin allowlist, per-route rate limiting, `no-store`,
  CSP, `nosniff`, frame denial, and request IDs.
- **Snapshot integrity**: assembled snapshots are hash-sealed and immutable;
  persistence rejects tampered projections.

These claims remain subject to the exact-commit executable evidence gate. A
green workflow does not itself grant public-release authority.

## First-run restriction

Use only the governed first-admin initialization path. Anonymous
`/api/auth/local-bootstrap` and implicit zero-user principals must remain
unavailable in production and networked environments. Administrative password
reset remains authenticated; public self-service recovery remains fail closed.
