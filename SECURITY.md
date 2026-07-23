# Security Policy — ASIE

## Supported versions

| Branch | Status |
|---|---|
| `main` | Supported — security fixes land here first |
| `agent/*`, `feat/*`, `chore/*` | Working branches; not release surfaces |

## Reporting a vulnerability

Do not open a public issue for security reports.

Use **GitHub private vulnerability reporting** ("Security" tab → "Report a
vulnerability") on this repository. Include: affected route or module, the
request sequence, whether the impact crosses an organization (tenant)
boundary, and whether it touches a frozen runtime file.

You can expect an acknowledgment within 3 business days and a remediation
plan or rejection rationale within 14 days.

## Security model summary

- **Local-first**: external network fetch and AI providers are disabled by
  default; enabling them requires an approved ACR.
- **Authentication**: PBKDF2-SHA256 (310,000 iterations) password hashing;
  Bearer sessions stored as SHA-256 token hashes with revocation.
- **Authorization**: organization (tenant) membership and role permissions
  are enforced server-side on every route; a negative cross-tenant matrix
  lives in `tests/test_tenant_isolation_matrix.py` and runs in CI.
- **Audit**: `security_audit_events` is append-only (insert-only code path);
  no API route mutates or deletes audit events.
- **HTTP hardening**: origin allowlist, per-route rate limiting, `no-store`,
  CSP, `nosniff`, frame denial, request IDs.
- **Snapshot integrity**: assembled snapshots are hash-sealed and immutable;
  persistence rejects tampered projections.

## First-run note (local development)

When the local database contains zero users, the API allows a one-time
`local-bootstrap` and a legacy local operator context so a developer can
create the first organization. As soon as any user exists, all surfaces fail
closed (401/403). Do not expose a zero-user instance to any network you do
not fully control.
