# ASIE Documentation Index

**Status:** LIVE NAVIGATION INDEX  
**Owner:** Repository and Release Governance  
**Last reviewed:** 2026-07-29

This index separates current authority from derived orientation, dated evidence,
and historical provenance. A file being present under docs/ does not by itself
make it a current source of truth.

## Read first

1. [Root AGENTS](../../AGENTS.md) — repository operating rules.
2. [Package AGENTS](../AGENTS.md) — canonical workspace guide.
3. [PROGRAM-CLOSE-10](./PROGRAM-CLOSE-10-EMERGENCY-REMEDIATION-CONSOLIDATION-AND-REBASELINE-2026-07-29.md) — current program state and release authority.
4. [EKB Arabic entry](./EKB/README-AR.md) and the task-specific EKB reading order.
5. The relevant canonical register, approved ACR, code, and tests.

## Authority order

When facts conflict, use the authority for the relevant domain:

1. /EMERGENCY-RELEASE-FREEZE.json for machine-readable release authority.
2. PROGRAM-CLOSE-10 for consolidated current remediation/program status.
3. ASIE-AAS-Runtime-Freeze-Manifest-v1.0.json for frozen runtime facts.
4. Binding constitutions, canonical registers, and approved ACRs.
5. Active EKB plus live code and executable tests.
6. Derived orientation documents.
7. Dated execution records.
8. docs/archive/superseded/ and docs/reference/ as provenance only.

## Authoritative current documents

- PROGRAM-CLOSE-10-EMERGENCY-REMEDIATION-CONSOLIDATION-AND-REBASELINE-2026-07-29.md
- ASIE-AAS-Runtime-Freeze-Manifest-v1.0.json
- AIA-01-Intelligence-Constitution-v1.0.0.md
- ASIE-CANONICAL-TERMINOLOGY-REGISTER-v1.0.0.md
- ASIE-CANONICAL-API-OUTPUT-REGISTER-v1.0.0.md
- approved ACR records, with their correction records where applicable
- active EKB, live source, registries, and tests

## Derived orientation

- PROJECT-ORIENTATION.md
- IMPLEMENTATION-STATUS-MATRIX.md
- system maps and architecture narratives not promoted to a binding ACR

These documents help navigation. They do not override the current release
marker, PROGRAM-CLOSE-10, executable behavior, or frozen manifests.

## Dated execution evidence

Files with dated package prefixes—including SEC-BETA-, STAB-BETA-, GOV-BETA-,
ARCH-BETA-, TEST-BETA-, REL-BETA-, DEPLOY-BETA-, GOV-REL-, BETA-PKG-, and
REPOSITORY-SURGERY-—are preserved evidence of individual decisions and
changes. They are historical records after closure, not parallel current-status
documents.

No dated record is deleted or moved by PROGRAM-CLOSE-10.

## Archive and quarantine

- docs/archive/superseded/: explicitly superseded documents.
- docs/reference/: archive-locked provenance; never executable source.
- quarantine-marker shells: path-level warnings retained after payload
  compaction; not implementation content.

Git history preserves removed archive payloads. New implementation belongs in
live source paths; current long-lived knowledge belongs in EKB, canonical
registers, approved ACRs, or this index's named current authority.
