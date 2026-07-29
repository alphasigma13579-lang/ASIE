# GOV-REL-09 — Governed Freeze Review

**Status:** implementation package  
**Base commit:** `eef452f0ea45f4fe857d8132f124ed5cfdab5d96`  
**Emergency Release Freeze:** remains `ACTIVE`  
**Official release decision during this package:** `NO_GO`

## 1. Purpose

The emergency release marker was created to fail closed after confirmed P0/P1 findings. The remediation packages and the private deployment smoke are now merged, but a green release workflow is not itself authority to edit the marker.

`GOV-REL-09` adds a separate, deterministic review contract:

```text
asie.governed.freeze.review.v1
```

The review consumes immutable evidence from an `Evidence-Backed Beta Release Gate` run for the exact current `main` commit. It revalidates the evidence hash, commit binding, remediation history, marker contract, and required package paths.

This package does not clear the marker and does not authorize release.

## 2. Decisions

The reviewer emits exactly one decision:

- `ELIGIBLE_FOR_UNFREEZE` — all governed preconditions are proven and the emergency marker is the only remaining critical release blocker.
- `KEEP_FROZEN` — evidence is structurally valid, but one or more readiness requirements remain incomplete.
- `REJECT_UNFREEZE` — evidence integrity, commit lineage, marker contract, or required package history is invalid.

Every report also fixes the following values:

```text
unfreeze_authorized: false
marker_mutation_permitted: false
release_allowed: false
public_beta_allowed: false
required_next_package: GOV-REL-10-CONTROLLED-UNFREEZE-EXECUTION
```

## 3. Evidence chain

The automatic path is:

```text
Evidence-Backed Beta Release Gate on main
→ rel-beta-07-complete-evidence Artifact
→ Governed Freeze Review
→ governed-freeze-review.json
```

The workflow runs automatically only when:

- the triggering release-gate workflow completed successfully;
- its `head_branch` is `main`;
- the Artifact commit equals the exact reviewed commit;
- the reviewed commit still equals the current `origin/main` head.

A manual dispatch exists only as a recovery path. It requires an evidence run ID and an exact commit, and the same current-main and evidence-binding checks still apply.

## 4. Required pre-unfreeze release state

The consumed `beta.release.gate.v2` report must prove:

```text
decision: NO_GO
release_allowed: false
public_beta_allowed: false
technical_limited_beta_allowed: false
code_evidence_ready: true
private_deployment_smoke_passed: true
critical_failures:
  - emergency_release_freeze_cleared
```

The reviewer rejects:

- a missing or invalid report hash;
- duplicate check identifiers;
- a report from another commit;
- manual readiness assertions;
- any additional critical failure;
- missing private deployment evidence;
- invalid deployment image digest;
- any claimed Finance, Snapshot, or external-fetch mutation.

## 5. Marker integrity

The reviewer requires the existing marker to remain:

```text
schema: asie.release.freeze.v1
status: ACTIVE
decision: NO_GO
release_gate_allowed: false
```

It verifies the exact scope, reason codes, protected boundaries, unfreeze requirements, and baseline commit. It also proves that the reviewed commit descends from the original emergency baseline:

```text
8978231e190b8ccc2be59ec46acf50d6268cd41f
```

The marker is read-only in this package.

## 6. Required package lineage

The following merge commits must all be ancestors of the reviewed `main` commit:

| Package | Required merge commit |
|---|---|
| SEC-BETA-01 | `22437844b49ff4ae81e5936df5638129fb9cb7ec` |
| STAB-BETA-02 | `8ce8edf97203a377c87bbe8e2cb9518b442d6da0` |
| SEC-BETA-03 | `6615b1828a31a079b4d57616878aca64d6cf6b0a` |
| GOV-BETA-04 | `3d29486480436c4ac02567207c449ba1dfe6a621` |
| ARCH-BETA-05 | `f0a36a18ba778dde1564df5fb6079a5bc9d2f6b8` |
| TEST-BETA-06 | `ddbcae583da3807467abf74a679c4b533e6d9918` |
| REL-BETA-07 | `9e20b980cee4936e8669198fc8c5c52f8186d489` |
| DEPLOY-BETA-08 | `eef452f0ea45f4fe857d8132f124ed5cfdab5d96` |

The workflow checks out full Git history and uses `git merge-base --is-ancestor`; file presence or PR descriptions are not accepted as substitutes for history.

## 7. Evidence-path verification

For every package, the reviewer also requires its canonical implementation record and executable regression assets to exist in the reviewed tree. This includes:

- security exploit tests;
- threaded HTTP/SQLite tests;
- tenant-isolation denial tests;
- Manifest/Gate forgery tests;
- canonical ProjectRunWorkflow admission tests;
- cross-platform determinism tests;
- release evidence collector;
- private deployment smoke probe.

Missing executable evidence produces `KEEP_FROZEN` even when history is otherwise valid.

## 8. Report integrity

The generated report contains:

```text
schema: asie.governed.freeze.review.v1
package_id: GOV-REL-09
review_commit
freeze_baseline_commit
freeze_marker_canonical_sha256
gate_report_hash
deployment_image_digest
checks
rejection_failures
readiness_failures
review_hash
```

`review_hash` is SHA-256 over canonical UTF-8 JSON excluding the hash field itself.

## 9. Surgical allowlist

Only four files are permitted:

```text
.github/workflows/governed-freeze-review.yml
ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/tools/gov_rel_09_governed_freeze_review.py
ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/tests/test_gov_rel_09_governed_freeze_review.py
ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/docs/GOV-REL-09-GOVERNED-FREEZE-REVIEW-2026-07-29.md
```

Explicitly excluded:

- `EMERGENCY-RELEASE-FREEZE.json`;
- AAS Runtime Freeze files;
- Finance calculations;
- ProjectRunWorkflow;
- Module Runtime;
- System Bus and Socket Contracts;
- Snapshot Assembly;
- Decision Council;
- production deployment workflow;
- provider activation or secret values.

## 10. Merge and post-merge gate

Before merge:

- ASIE CI must pass;
- frontend build must pass;
- backend compile must pass;
- the complete Python suite must pass;
- all `GOV-REL-09` regression tests must pass;
- the four-file allowlist must remain exact.

After merge:

1. push to `main` triggers the evidence-backed release gate;
2. successful completion triggers `Governed Freeze Review` automatically;
3. the generated Artifact must be inspected and its hash verified;
4. only `ELIGIBLE_FOR_UNFREEZE` permits starting `GOV-REL-10`;
5. release remains `NO_GO` until the separate controlled marker transition and a fresh release-gate run both succeed.
