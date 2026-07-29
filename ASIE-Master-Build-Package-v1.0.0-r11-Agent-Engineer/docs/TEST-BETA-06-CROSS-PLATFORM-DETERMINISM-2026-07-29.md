# TEST-BETA-06 — Cross-Platform Determinism

**Base commit:** `f0a36a18ba778dde1564df5fb6079a5bc9d2f6b8`  
**Prerequisite:** `ARCH-BETA-05` merged  
**Release status:** `NO_GO`; Emergency Release Freeze remains `ACTIVE`

## Objective

Prove that the deterministic ASIE calculation and integrity surfaces produce the same canonical evidence bytes when executed on the same release commit under materially different runtime conditions:

- Ubuntu runner;
- Windows runner;
- Python `3.12`;
- `PYTHONHASHSEED=0`;
- `PYTHONHASHSEED=7919`;
- UTF-8 mode;
- UTC environment.

The package does not change product algorithms. It creates reproducible evidence around the existing implementation.

## Determinism vector

Each matrix job independently builds one fixed vector containing:

1. deterministic Finance Engine output;
2. all six required sealed module-output hashes;
3. Projection Support sealed-envelope hash;
4. assembled Snapshot content hash;
5. assembled Snapshot integrity hash;
6. Arabic Unicode canonical-hash probe;
7. fixed identifiers and a fixed test timestamp;
8. invariants proving input-order and sealed-output-order independence.

The Finance vector includes:

- baseline, conservative, and optimistic scenarios;
- NPV, IRR, payback, DSCR, CapEx, OpEx, and working capital;
- sensitivity matrices;
- deterministic Monte Carlo using seed `20260713` and `4000` iterations.

## Controlled nondeterminism

The evidence vector excludes:

- generated UUIDs;
- wall-clock time;
- host names;
- absolute paths;
- operating-system labels;
- temporary-directory paths;
- environment-specific separators;
- locale-derived formatting.

The test timestamp, Project ID, Run ID, Snapshot ID, message IDs, correlation IDs, and audit references are fixed in the test harness only. Production code is not patched or altered.

`Snapshot Assembly.now_iso` is patched only while constructing the test vector so the full integrity hash can be compared. The production `backend/snapshot_assembly.py` file remains unchanged.

## Repository text canonicalization

The first Windows execution exposed two repository-level defects before the deterministic vector could run:

1. archived paths exceeded the traditional Windows path limit;
2. Git converted frozen Python files to CRLF, causing frozen-file SHA-256 checks to fail.

The root repair is repository-wide and non-algorithmic:

```text
.gitattributes
* text=auto eol=lf
```

Binary formats are marked explicitly so they are never normalized. Windows matrix jobs also configure before checkout:

```text
core.longpaths=true
core.autocrlf=false
core.eol=lf
```

This ensures the checked-out bytes match the canonical repository bytes and makes AAS Runtime Freeze checks reproducible on Windows. No frozen file content or checksum was changed.

## Cross-platform matrix

The workflow creates four independent artifacts:

```text
ubuntu-hash0
ubuntu-hash7919
windows-hash0
windows-hash7919
```

Each job:

1. configures deterministic checkout behavior where required;
2. compiles the evidence harness;
3. runs the targeted regression tests;
4. generates the vector twice in-process;
5. requires both generations to be byte-identical;
6. writes UTF-8 JSON with LF line endings;
7. uploads `vector.json`.

A separate Ubuntu comparison job downloads all four artifacts and requires exact byte equality. Semantic equality alone is insufficient.

## Fail-closed rules

The workflow fails when any of the following occurs:

- checkout changes frozen repository bytes;
- Finance returns blockers or `not_ready`;
- repeated generation differs;
- Finance changes when input dictionary order changes;
- Snapshot changes when sealed module order changes;
- canonical hash changes when JSON key order changes;
- any artifact differs by one byte;
- any matrix job is skipped or fails;
- fewer than two artifacts reach the comparison job.

## Protected boundaries

No modification is permitted to:

- AAS Runtime Freeze v1.0;
- `backend/project_run_workflow.py`;
- `backend/module_runtime.py`;
- `backend/system_bus.py`;
- `backend/socket_contracts.py`;
- `backend/finance_engine.py`;
- `backend/snapshot_assembly.py`;
- Decision Council;
- production contracts.

The package imports and executes existing public functions for test evidence only.

## Allowlist

```text
.gitattributes
.github/workflows/test-beta-06-cross-platform-determinism.yml
ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/tools/test_beta_06_determinism.py
ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/tests/test_beta_06_cross_platform_determinism.py
ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/docs/TEST-BETA-06-CROSS-PLATFORM-DETERMINISM-2026-07-29.md
```

## Required evidence before merge

- normal ASIE CI succeeds on the final PR head;
- all four matrix jobs succeed;
- the byte-comparison job succeeds;
- the combined evidence artifact exists;
- the final diff contains only the allowlisted files;
- frozen-file checksum guards succeed on Ubuntu and Windows.

## Scope limitation

This package proves deterministic computation and canonical serialization for the selected critical vector. It does not prove:

- production deployment readiness;
- database-engine equivalence beyond the vector;
- browser rendering equivalence;
- external provider equivalence;
- network behavior;
- runtime performance parity.

Those claims are outside TEST-BETA-06.

## Release decision

Completion of TEST-BETA-06 does not lift the Emergency Release Freeze.

The release remains:

```text
status: ACTIVE
decision: NO_GO
release_gate_allowed: false
```

The next governed package is:

```text
REL-BETA-07 — Evidence-Backed Release Gate
```

REL-BETA-07 must evaluate the actual release commit and consume evidence from all closed emergency packages before any unfreeze decision.
