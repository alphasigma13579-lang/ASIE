# GOV-BETA-04 — Server-Owned Manifest Chain

**Base commit:** `6615b1828a31a079b4d57616878aca64d6cf6b0a`  
**Prerequisites:** `EMERG-00`, `SEC-BETA-01`, `STAB-BETA-02`, and `SEC-BETA-03` merged  
**Release status:** `NO_GO`; emergency release freeze remains ACTIVE

## Confirmed exploit

The previous API accepted complete `manifest` and `gate` objects from the client and persisted them. The persistence layer checked contract shape and project identifiers but did not prove that:

- the referenced Blueprint existed;
- the Blueprint was the current persisted revision for the session;
- the Manifest was generated from the persisted Blueprint payload;
- the Validation Gate was generated from the persisted Manifest payload;
- either child carried a hash-linked, server-issued lineage.

This permitted the reproduced state:

```text
persisted Blueprints = 0
persisted Approved Manifests = 1
persisted Validation Gates = 1
controlled Finance = executed
```

Finance admission itself is not repaired in this package. This package removes the forged lineage that previously allowed a client to manufacture the prerequisites.

## Root repair

### Command-only API

The authenticated tenant API no longer accepts final Manifest or Gate objects.

The Manifest endpoint accepts only:

```text
expected_blueprint_id
expected_blueprint_payload_hash
expected_revision
approval_note
```

The Validation Gate endpoint accepts only:

```text
expected_manifest_id
expected_manifest_payload_hash
expected_revision
```

Empty commands remain valid for the existing click-first flow. Any final object fields such as `manifest`, `gate`, `status`, `normalized_inputs`, `blockers`, or client-supplied identifiers are rejected.

### Server generation

The server loads the current persisted parent and invokes the governed module adapter:

```text
Persisted Blueprint
→ module.approved_input_manifest
→ Server-owned Manifest
→ persisted parent hash lineage

Persisted Manifest
→ module.manifest_validation_gate
→ Server-owned Validation Gate
→ persisted parent hash lineage
```

The authenticated Principal supplies only the actor identity:

```text
approved_by_user_id
validated_by_user_id
```

The client cannot set or replace those fields.

### Hash lineage

A server-owned Manifest records:

```text
session_id
project_id
blueprint_id
blueprint_payload_hash
blueprint_revision
```

A server-owned Validation Gate records:

```text
session_id
project_id
manifest_id
manifest_payload_hash
blueprint_id
blueprint_payload_hash
revision
```

Optimistic concurrency expectations reject stale UI state with `409 stale_blueprint_lineage` or `409 stale_manifest_lineage`.

### SQLite authority boundary

`dib_manifest_chain_authorizations` issues a one-time authorization tied to:

```text
entity_type
entity_id
session_id
project_id
parent_entity_id
parent_payload_hash
expected_payload_hash
created_by_user_id
```

SQLite triggers reject direct inserts into `dib_approved_manifests` or `dib_validation_gates` unless an exact, unused authorization exists. The authorization is consumed in the same transaction as the child record.

Manifest and Gate rows are immutable after creation.

### Revision invalidation

When `current_blueprint_id` changes, database enforcement clears:

```text
approved_manifest_id
validation_gate_id
```

When `approved_manifest_id` changes, the current Validation Gate is cleared. A later Blueprint revision therefore cannot reuse an earlier Manifest or Gate.

### Existing chains

Existing current Manifest/Gate pointers created before GOV-BETA-04 have no proof of server authority. Their identifiers are recorded in:

```text
dib_manifest_chain_quarantine
```

The active session pointers are cleared. Historical entity rows are retained for audit and are not promoted into the active chain.

## Exploit regression evidence

The package tests prove:

1. A client-supplied Manifest is rejected by the tenant API.
2. A client-supplied Validation Gate is rejected by the tenant API.
3. An empty command produces a server-owned Manifest from the persisted Blueprint.
4. An empty command produces a server-owned Gate from the persisted Manifest.
5. Blueprint and Manifest hashes are preserved in the child lineage.
6. SQLite rejects direct forged Manifest persistence.
7. SQLite rejects direct forged Gate persistence.
8. A stale expected hash is rejected.
9. A new Blueprint revision invalidates active Manifest and Gate pointers.
10. Pre-GOV-BETA-04 active chains are quarantined and deactivated.
11. AAS Runtime Freeze files remain unchanged.

## Allowlist

- `backend/dib_server_owned_manifest_chain.py`
- `backend/dib_tenant_api.py`
- `tests/test_gov_beta_04_server_owned_manifest_chain.py`
- `docs/GOV-BETA-04-SERVER-OWNED-MANIFEST-CHAIN-2026-07-29.md`

## Protected boundaries

No changes are permitted to:

- AAS Runtime Freeze v1.0;
- Finance calculations or algorithms;
- direct Finance admission repair, which belongs to `ARCH-BETA-05`;
- Snapshot Assembly or immutability;
- Decision Council;
- DIB tenant ownership established by `SEC-BETA-03`.

## Exit criteria

- Full ASIE CI passes on the final PR head.
- Client-owned Manifest and Gate tests pass.
- Direct SQLite forgery tests pass.
- Parent hashes match the exact persisted records.
- Blueprint revision invalidation passes.
- No file outside the Allowlist changes.
- Emergency release freeze remains ACTIVE.
- `ARCH-BETA-05` starts only from the merge commit of this package.
