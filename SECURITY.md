# Security Policy — ASIE

## Supported versions

| Branch | Status |
|---|---|
| `main` | Supported for security remediation; public release is frozen |
| `agent/*`, `feat/*`, `chore/*`, `emergency/*`, `security/*` | Working branches; not release surfaces |

## Emergency release freeze

The release baseline `8978231e190b8ccc2be59ec46acf50d6268cd41f` is **NO_GO** for public beta, production deployment, and direct external network exposure.

The canonical machine-readable control is `EMERGENCY-RELEASE-FREEZE.json`. While its status is `ACTIVE`, the Beta Release Gate must fail closed. Do not expose the API or DIB sidecar on public ports, including `80` or `443`; keep remediation environments on loopback or a private deployment network.

## Reporting a vulnerability

Do not open a public issue for security reports.

Use **GitHub private vulnerability reporting** ("Security" tab → "Report a vulnerability") on this repository. Include: affected route or module, the request sequence, whether the impact crosses an organization (tenant) boundary, and whether it touches a frozen runtime file.

You can expect an acknowledgment within 3 business days and a remediation plan or rejection rationale within 14 days.

## Intended security model

- **Local-first**: external network fetch and AI providers are disabled by default; enabling them requires an approved ACR.
- **Authentication**: PBKDF2-SHA256 password hashing; Bearer sessions stored as SHA-256 token hashes with revocation.
- **Authorization target**: organization membership, record ownership, and role permissions must all be enforced server-side.
- **Audit**: `security_audit_events` is append-only through the supported code path.
- **HTTP hardening**: origin allowlist, per-route rate limiting, `no-store`, CSP, `nosniff`, frame denial, and request IDs.
- **Snapshot integrity**: assembled snapshots are hash-sealed and immutable; persistence rejects tampered projections.

The current baseline does **not** satisfy the intended authentication and tenant-boundary model. Confirmed defects include zero-user implicit authorization, an unprotected first-run bootstrap route, and missing DIB organization ownership enforcement. Treat any older statement that these controls are complete as superseded by the active emergency freeze.

## First-run restriction

Do not use `/api/auth/local-bootstrap` or the zero-user legacy operator on any networked or production-like instance. Until `SEC-BETA-01 — Production Identity Bootstrap Lockdown` is merged and independently verified, first-run initialization is permitted only in an isolated disposable development environment with no external listener.
