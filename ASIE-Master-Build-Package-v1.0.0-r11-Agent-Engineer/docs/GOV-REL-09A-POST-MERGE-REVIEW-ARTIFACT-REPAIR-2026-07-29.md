# GOV-REL-09A — Post-Merge Review Artifact Repair

**Base commit:** `e00cdc39e469e3592d0fdde3c2f365837a6414ec`  
**Predecessor:** `GOV-REL-09 — Governed Freeze Review`  
**Scope:** GitHub Actions orchestration and evidence observability only

## Problem statement

`GOV-REL-09` introduced a correct fail-closed evaluator, but its automatic execution depended on a separate `workflow_run` event. The available operational evidence could prove the Pull Request CI, but could not reliably expose a post-merge `gov-rel-09-governed-freeze-review` Artifact bound to the current `main` commit.

This was an orchestration and evidence-observability gap. It was not permission to bypass the review or to mutate the Emergency Release Freeze marker.

## Root repair

The governed review now runs directly on every `push` to `main`.

The review does not reproduce or simulate release evidence. Instead, it waits for the independent `Evidence-Backed Beta Release Gate` workflow to finish for the exact same commit, then verifies the source run through the GitHub Actions API before downloading its immutable Artifact.

Canonical sequence:

```text
push to main
→ Evidence-Backed Beta Release Gate starts
→ Governed Freeze Review starts
→ review waits for the exact-commit gate run
→ gate run must complete successfully
→ source-run metadata is independently revalidated
→ rel-beta-07-complete-evidence is downloaded
→ GOV-REL-09 evaluator revalidates hashes, lineage, packages, smoke, and marker
→ gov-rel-09-governed-freeze-review Artifact is uploaded
```

## Exact-run requirements

The accepted source run must satisfy every condition:

- workflow name is `Evidence-Backed Beta Release Gate`;
- workflow file is `beta-release-gate.yml`;
- `head_sha` equals the exact reviewed `main` commit;
- `head_branch` equals `main`;
- event equals `push`;
- status equals `completed`;
- conclusion equals `success`;
- Artifact name equals `rel-beta-07-complete-evidence`;
- the Artifact contains `rel-beta-07-final/beta-release-gate-report.json`.

A failed, cancelled, timed-out, action-required, missing, stale, cross-branch, or cross-commit run fails closed.

## Current-main guard

Before reading evidence, the workflow fetches `origin/main` and requires:

```text
checked-out commit
== ASIE_REVIEW_COMMIT
== origin/main
```

A newer commit arriving before review completion invalidates the review rather than allowing an eligibility decision for stale code.

## Review output

The existing `asie.governed.freeze.review.v1` evaluator remains the sole review authority. This package does not create a second decision engine.

The output Artifact contains:

```text
governed-freeze-review.json
governed-freeze-review.sha256
source-evidence-run.json
```

The source-run metadata is retained so the review can be traced to the exact GitHub Actions run used as evidence.

## Manual fallback

`workflow_dispatch` remains available on `main` for recovery and audit. It requires both:

- the exact evidence Run ID;
- the exact current `main` commit.

The same source-run metadata validation applies. Manual execution cannot supply readiness booleans, alter hashes, skip lineage checks, or authorize marker mutation.

## Permissions

The workflow has read-only permissions:

```yaml
permissions:
  contents: read
  actions: read
```

It cannot:

- modify repository contents;
- mutate the Emergency Release Freeze marker;
- merge a Pull Request;
- deploy publicly;
- create a release;
- write an approval label;
- change provider configuration.

## Regression guards

`test_gov_rel_09a_post_merge_review_artifact.py` proves:

- automatic review is driven by `push` to `main`;
- no automatic dependency on `workflow_run` remains;
- the evidence run is filtered by exact SHA, branch, event, and successful conclusion;
- terminal non-success states fail immediately;
- source-run metadata is revalidated before download;
- the Artifact name and gate report path are fixed;
- `origin/main` must equal the reviewed commit;
- permissions remain read-only;
- the Emergency Release Freeze remains `ACTIVE / NO_GO`;
- the existing GOV-REL-09 evaluator remains the only eligibility authority.

## Surgical allowlist

Only these three files may change:

```text
.github/workflows/governed-freeze-review.yml
ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/tests/test_gov_rel_09a_post_merge_review_artifact.py
ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/docs/GOV-REL-09A-POST-MERGE-REVIEW-ARTIFACT-REPAIR-2026-07-29.md
```

## Protected boundaries

No changes are permitted to:

- `EMERGENCY-RELEASE-FREEZE.json`;
- AAS Runtime Freeze;
- Finance calculations;
- ProjectRunWorkflow;
- Module Runtime;
- System Bus;
- Socket Contract Layer;
- Snapshot Assembly;
- Decision Council;
- release-gate decision logic;
- private deployment implementation;
- provider activation;
- public deployment.

## Exit criteria

The package may close only after:

1. full ASIE CI succeeds;
2. the cross-platform determinism workflow succeeds;
3. the Pull Request contains exactly the three allowlisted files;
4. the merged `main` commit triggers the evidence gate;
5. a successful `gov-rel-09-governed-freeze-review` Artifact is emitted;
6. the Artifact decision is `ELIGIBLE_FOR_UNFREEZE` for the exact current `main` commit;
7. the Emergency Release Freeze remains unchanged.

Even after these criteria pass, `GOV-REL-10` remains a separate controlled package. This repair does not clear the marker and does not authorize release.
