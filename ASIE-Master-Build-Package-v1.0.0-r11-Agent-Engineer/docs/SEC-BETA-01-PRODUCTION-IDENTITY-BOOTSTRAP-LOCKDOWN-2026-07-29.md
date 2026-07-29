# SEC-BETA-01 — Production Identity Bootstrap Lockdown

**Base commit:** `d734c1c9225eb69ce35e335c7a1f4a0d4949869b`  
**Prerequisite:** `EMERG-00` merged and release freeze ACTIVE  
**Scope:** identity bootstrap and zero-user authorization only

## Confirmed exploit

At the pre-fix baseline, a production process with an empty user database permitted:

1. `POST /api/auth/local-bootstrap` without a bootstrap secret, creating a `platform_admin`.
2. Unauthenticated project creation through the implicit `local_legacy_operator` principal.

These paths made the first network request capable of taking ownership of the platform.

## Remediation rules

### Production and production-like environments

- The HTTP local-bootstrap route is unavailable, even when local-development flags or a secret are supplied.
- A zero-user database never creates an implicit Principal.
- Unknown environment names fail as production-like rather than development-like.
- The first platform administrator is created through a local CLI that does not create or print a session token.

### Explicit local development compatibility

HTTP local bootstrap is available only when every condition is true:

- `ASIE_ENV` is one of `development`, `dev`, `local`, `test`, or `testing`.
- `ASIE_ALLOW_LOCAL_BOOTSTRAP=true` is set explicitly.
- The request originates from a loopback address.
- `ASIE_LOCAL_BOOTSTRAP_SECRET` contains at least 32 characters.
- `X-ASIE-Bootstrap-Secret` matches using constant-time comparison.
- The database still contains zero users.

The legacy local operator is disabled by default. It is permitted only in a non-production environment, from loopback, with `ASIE_ALLOW_LEGACY_LOCAL_OPERATOR=true` explicitly set.

## Production first-admin procedure

Set the initial password in the process environment, then run the CLI locally on the host:

```bash
export ASIE_INITIAL_ADMIN_PASSWORD='use-a-secret-manager-value'
python tools/create_initial_platform_admin.py \
  --database data/asie.sqlite3 \
  --email admin@example.com \
  --display-name 'Platform Administrator' \
  --organization-name 'ASIE Platform' \
  --confirm-empty-database
unset ASIE_INITIAL_ADMIN_PASSWORD
```

The administrator must then log in through the normal `/api/auth/login` route. The CLI does not return a bearer token.

## Exploit regression tests

- production bootstrap without a secret is denied and creates no user;
- production bootstrap remains denied even with flags and a valid secret;
- zero-user unauthenticated project creation returns `401`;
- development bootstrap rejects a wrong secret;
- authorized loopback development bootstrap succeeds once and cannot be reused;
- non-loopback bootstrap is denied before secret acceptance;
- legacy local operator is disabled by default and in all production-like environments;
- the CLI service creates one initial administrator without an HTTP session;
- the real CLI entrypoint executes successfully, emits no token, and refuses reuse;
- the legacy collection fixture remains available only through explicit local-development opt-in.

## Allowlist

- `backend/asie_local_api.py`
- `backend/bootstrap_security.py`
- `tools/create_initial_platform_admin.py`
- `tests/test_sec_beta_01_bootstrap_lockdown.py`
- `tests/test_sec_beta_01_initial_admin_cli.py`
- `tests/test_organization_scope_resolution.py`
- `docs/SEC-BETA-01-PRODUCTION-IDENTITY-BOOTSTRAP-LOCKDOWN-2026-07-29.md`

## Protected boundaries

No changes are permitted to AAS Runtime Freeze, Finance calculations, Snapshot Assembly, or Decision Council.

## Exit criteria

This package may merge only after full ASIE CI succeeds and the exploit regression tests pass on the PR head. The global release decision remains `NO_GO`; this package closes only the production identity-bootstrap P0.
