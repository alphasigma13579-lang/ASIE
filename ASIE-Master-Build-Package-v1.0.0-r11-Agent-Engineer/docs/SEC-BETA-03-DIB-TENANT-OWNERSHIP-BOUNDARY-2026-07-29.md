# SEC-BETA-03 — DIB Tenant Ownership Boundary

**Base commit:** `8ce8edf97203a377c87bbe8e2cb9518b442d6da0`  
**Prerequisites:** `EMERG-00`, `SEC-BETA-01`, and `STAB-BETA-02` merged  
**Release status:** `NO_GO`; emergency release freeze remains ACTIVE

## Confirmed exploit

The previous DIB sidecar authenticated a Principal and checked RBAC permissions, but the DIB database had no authoritative organization ownership record. A Principal from `org_a` with `dib.read` could request a session created for `org_b` and receive HTTP 200.

The defect was not a missing role. It was a missing object-ownership boundary.

## Root repair

This package introduces one immutable tenant binding for every DIB session:

```text
session_id
organization_id
project_id
created_by_user_id
created_at
```

All child DIB records already carry a mandatory `session_id` foreign key and therefore inherit the session ownership boundary. New sessions cannot be inserted without a non-quarantined binding in the same transaction.

### Trusted request context

Every non-public HTTP request now carries a server-created `DIBTenantContext` derived from the authenticated Principal:

```text
organization_id
user_id
principal_session_id
```

The Controller rejects non-public requests without this context. The client cannot establish or replace the context through JSON. The reserved quarantine organization is forbidden as a request context, including for platform-level identities.

### Project ownership

Before starting or listing a DIB session, the tenant-scoped Controller resolves the project through the primary ASIE Repository and verifies:

```text
principal.organization_id == project.organization_id
```

Mismatch and absence both return the same `404 dib_resource_not_found` response.

### Session ownership

Every session route verifies:

```text
binding.session_id == requested session
binding.organization_id == principal.organization_id
binding.organization_id != __dib_quarantine__
```

The check occurs before reads, writes, events, Manifest actions, Validation Gate actions, Finance admission requests, snapshot handoff requests, or session closure. Session reads, event reads, and closure are projected through the tenant boundary itself rather than merely prechecked and delegated to an unscoped projection.

### Existing records

Migration is evidence-based:

1. The existing DIB session `project_id` is resolved through the primary ASIE Repository.
2. When the project has a verified live `organization_id`, the session is bound to that organization and marked with `created_by_user_id=__migration__`.
3. When project ownership cannot be resolved, the session is assigned only to:

```text
__dib_quarantine__
```

Unknown records are never assigned automatically to `org_local_legacy` or any other live organization. No valid tenant context can read quarantined rows.

### Database enforcement

- `dib_tenant_bindings` is keyed one-to-one by `session_id`.
- The binding foreign key is deferred so binding and session are created atomically.
- A trigger rejects session insertion without a non-quarantined binding.
- A trigger prevents changing or deleting the bound session, organization, or project after migration.
- A trigger prevents changing the DIB session project after binding.
- Migration may promote a quarantined row only while package-owned immutability triggers are temporarily absent inside the same exclusive migration transaction; triggers are recreated before commit.
- Central security audit records denied cross-tenant attempts without exposing the target object.

## Exploit regression evidence

The package proves through a real `ThreadingHTTPServer`:

1. `org_b` can create and read its own DIB session.
2. `org_a` receives 404 when reading the `org_b` session.
3. `org_a` receives 404 for the `org_b` session events.
4. `org_a` receives 404 when writing a Blueprint to the `org_b` session.
5. `org_a` cannot enumerate sessions for the `org_b` project.
6. `org_a` cannot start a session for the `org_b` project.
7. Existing sessions with proven project ownership are migrated to the verified organization.
8. Existing sessions without proven ownership remain quarantined.
9. The quarantine organization cannot be used as a request context.
10. The tenant binding is immutable at the SQLite boundary.
11. A raw unbound session insertion is rejected.

## Allowlist

- `backend/dib_tenant_boundary.py`
- `backend/dib_tenant_api.py`
- `backend/dib_http_mounting.py`
- `tests/test_dib_http_mounting.py`
- `tests/test_sec_beta_03_dib_tenant_boundary.py`
- `docs/SEC-BETA-03-DIB-TENANT-OWNERSHIP-BOUNDARY-2026-07-29.md`

## Protected boundaries

No changes are permitted to:

- AAS Runtime Freeze v1.0;
- Finance calculations or algorithms;
- Snapshot Assembly or immutability;
- Decision Council;
- Manifest/Gate trust model;
- canonical Finance admission path.

## Exit criteria

- Full ASIE CI passes on the PR head.
- The real HTTP cross-tenant exploit matrix passes.
- Proven historical ownership is migrated and unproven ownership remains quarantined.
- No file outside the allowlist changes.
- The emergency release freeze remains ACTIVE.
- `GOV-BETA-04` starts only from the merge commit of this package.
