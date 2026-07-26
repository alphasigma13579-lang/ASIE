# Repository Surgery Plan — ASIE r11

**Date:** 2026-07-26  
**Package:** `REPOSITORY-SURGERY-R1-ARCHIVE-LOCKDOWN`  
**Status:** Controlled cleanup plan / no deletion in R1

## 1. Objective

Clean the ASIE repository without breaking live code, AAS Freeze, DIB, CI, reports, or security controls. The first step is to lock old files as historical archive so they cannot be used as live implementation input.

## 2. Problem statement

The repository contains historical workspace bundles, correction archives, handoff folders, and implementation-looking copies of runtime/API files. These are useful as provenance but dangerous as source material because they can be mistaken for current source.

The highest-risk pattern is:

```text
archive/reference path contains backend/*.py or src/*.tsx that looks live
```

Examples of risk classes:

```text
archived backend/asie_local_api.py
archived backend/runtime_freeze.py
archived architecture correction bundles
archived next-task handoff bundles
old one-page maps and duplicated correction plans
```

## 3. Non-negotiable safety constraints

```text
Do not delete directly from main.
Do not merge stale branches.
Do not replace live files with archive blobs.
Do not mutate AAS frozen files.
Do not alter DIB runtime, Finance, Snapshot, AI Provider, or external network behavior during repository cleanup.
Every cleanup step requires a PR and CI.
```

## 4. R1 scope — Archive Lockdown

R1 implements policy and guardrails only:

1. Add EKB-06 Repository Surgery Inventory.
2. Add an archive lockdown notice.
3. Update root and package AGENTS.md to prohibit archive-to-live copying.
4. Add static tests that prevent live code from referencing archive-locked zones.
5. Leave all deletion to later PRs.

## 5. R2 scope — Quarantine marking

R2 should add explicit marker files to high-risk archive directories and optionally move selected historical material under a single controlled `docs/archive/` namespace if CI proves safe.

No deletion yet unless the file is trivially generated and unreferenced.

## 6. R3 scope — Surgical deletion

R3 may delete files only after proving all of the following:

```text
not imported by live code
not required by tests/CI
not referenced by active EKB as source of truth
not a frozen AAS file
not the only copy of an active architecture decision
```

Deletion candidates should be grouped by risk class, not deleted all at once.

## 7. R4 scope — Permanent guardrails

R4 should add stronger repository hygiene checks, such as:

```text
no package-lock/package.json side effects unless dependency PR
no backend/*.py under docs/reference except registered archive exceptions
no archived file path references inside live backend/src/tests
no stale branch merge into main without fresh base
```

## 8. Archive usage rule

Archive material may be used only for:

```text
historical provenance
manual comparison
migration notes
source archaeology
```

Archive material may not be used for:

```text
implementation source
copy/paste into backend/src/tests
current architecture claims
current runtime status
current API behavior
current DIB behavior
current Finance/Snapshot behavior
```

## 9. Required reviewer behavior

Before approving deletion:

1. Check `docs/EKB/EKB-06-Repository-Surgery-Inventory.md`.
2. Check `AGENTS.md` and package `AGENTS.md` archive lockdown rules.
3. Check that the PR only touches intended files.
4. Check CI.
5. Check that no frozen file changed.

## 10. R1 result definition

R1 is successful when:

```text
Archive Lockdown is documented.
Agents are instructed not to use archives as source.
A static guard test exists.
No deletion happened.
CI passes.
```
