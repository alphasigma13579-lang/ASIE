# EMERG-00 — Release Freeze and Exposure Containment

**Status:** CLEARED BY CONTROLLED TRANSITION  
**Decision:** PENDING_GATE  
**Baseline:** `8978231e190b8ccc2be59ec46acf50d6268cd41f`  
**Activated:** 2026-07-29  
**Controlled transition:** `GOV-REL-10-CONTROLLED-UNFREEZE-EXECUTION`

## Purpose

Contain the confirmed pre-production security and architectural failures before any public beta, production deployment, or direct network exposure. This package does not claim to remediate the defects. It prevents the existing beta gate from presenting a false release signal while the corrective packages are executed.

The containment record is historical and remains the provenance for the original freeze. The current marker is cleared only for commit-bound technical-limited gate evaluation. Public release, production deployment, provider activation, external fetch, and external network exposure remain unauthorized.

## Confirmed blockers

1. Production bootstrap can create the first `platform_admin` without a bootstrap secret.
2. A zero-user database grants an implicit `local_legacy_operator` principal.
3. DIB does not enforce organization ownership and permits cross-tenant access.
4. Client-supplied Manifest and Validation Gate objects can establish a forged Finance admission chain.
5. DIB persistence shares one SQLite connection with a threaded HTTP server.
6. The beta release gate consumes manual assertions instead of runtime evidence.

## Containment controls

- `EMERGENCY-RELEASE-FREEZE.json` is the canonical machine-readable freeze marker.
- `tools/enforce_release_freeze.py` is the executable fail-closed guard.
- The Beta Release Gate must fail while the marker status is `ACTIVE`.
- A missing, invalid, or non-mapping marker must also fail closed.
- No public beta or production deployment may use this baseline or a descendant lacking all mandatory remediation evidence.
- API and DIB services must remain on loopback or a private deployment network until the release freeze is formally removed.
- No port `80` or `443` exposure is authorized by this package.

## Protected boundaries

This package must not modify:

- AAS Runtime Freeze v1.0 files.
- Finance calculations or algorithms.
- Snapshot Assembly or snapshot immutability.
- Decision Council.

## Required remediation sequence

1. `SEC-BETA-01 — Production Identity Bootstrap Lockdown`
2. `STAB-BETA-02 — Transaction-Safe DIB Persistence`
3. `SEC-BETA-03 — DIB Tenant Ownership Boundary`
4. `GOV-BETA-04 — Server-Owned Manifest Chain`
5. `ARCH-BETA-05 — Canonical Finance Admission Repair`
6. `TEST-BETA-06 — Cross-Platform Determinism`
7. `REL-BETA-07 — Evidence-Backed Release Gate`
8. Private deployment smoke test on the same release image digest.

## Unfreeze protocol

The freeze marker may be changed from `ACTIVE` only by a dedicated release-control PR after all required packages are merged and their evidence artifacts are tied to the exact candidate commit and deployment image digest. Deleting the marker, bypassing the workflow check, or changing `release_gate_allowed` without that evidence is a release-control violation.

This transition was executed by `GOV-REL-10` and is bound to eligibility commit `b459944ba211be32408dd642390122b24d8113ae`, evidence-gate run `30451627726`, governed-review run `30451627730`, and the recorded review artifact SHA-256. The post-transition gate must still return `CONDITIONAL_GO` with public release disabled; otherwise the workflow fails closed.

## Allowlist for EMERG-00

- `EMERGENCY-RELEASE-FREEZE.json`
- `.github/workflows/beta-release-gate.yml`
- `SECURITY.md`
- `ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/tools/enforce_release_freeze.py`
- `ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/tests/test_emerg_00_release_freeze.py`
- `ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/docs/EMERG-00-RELEASE-FREEZE-AND-EXPOSURE-CONTAINMENT-2026-07-29.md`
