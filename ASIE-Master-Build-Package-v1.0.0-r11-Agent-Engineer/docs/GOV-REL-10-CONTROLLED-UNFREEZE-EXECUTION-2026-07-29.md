# GOV-REL-10 — Controlled Unfreeze Execution

**Status:** EXECUTED BY CONTROLLED PR  
**Eligibility baseline:** `b459944ba211be32408dd642390122b24d8113ae`  
**Previous decision:** `ELIGIBLE_FOR_UNFREEZE`  
**Resulting marker state:** `CLEARED / PENDING_GATE`

## Decision

This package clears the emergency remediation freeze only far enough to let the
evidence-backed gate evaluate the exact candidate commit. It does not authorize
a public release, production deployment, provider activation, external fetch,
or external network exposure.

The permitted outcome is a commit-bound `CONDITIONAL_GO` for technical,
private, loopback-only validation while all degradable external capabilities
remain unavailable. A `GO`/public-beta result is rejected by this package and
requires a separate governance decision.

## Bound evidence

- Eligibility commit: `b459944ba211be32408dd642390122b24d8113ae`
- Evidence gate run: `30451627726`
- Governed review run: `30451627730`
- Governed review artifact SHA-256:
  `134b77dc0d6135aba3eba02eac4c708960ef850e341bdd502067800fb9b5262a`
- Original emergency baseline:
  `8978231e190b8ccc2be59ec46acf50d6268cd41f`

## Fail-closed controls

1. The marker must preserve the original scope, reasons, protected boundaries,
   baseline, and remediation requirements.
2. `CLEARED` is invalid without the exact `controlled_unfreeze` proof.
3. The release guard and Beta Gate consume one shared marker contract.
4. The post-merge reviewer waits for the exact-commit Beta Gate artifact and
   accepts only `CONDITIONAL_GO`, no critical failures, private smoke success,
   and all four external capabilities degraded.
5. Any missing/tampered proof, stale commit, public `GO`, external capability
   activation, or frozen-file hash drift fails closed.

## Protected boundaries

The package does not change any file listed in
`docs/ASIE-AAS-Runtime-Freeze-Manifest-v1.0.json`. It does not change Finance
calculations, Snapshot Assembly, Decision Council, runtime contracts, production
Compose exposure, credentials, providers, Google Maps, or external networking.

## Authorization after merge

- Technical limited gate evaluation: allowed after fresh exact-commit evidence.
- Private loopback smoke: allowed.
- Public beta: not authorized.
- Production deployment: not authorized.
- External network exposure: not authorized.
- Provider/AI activation: not authorized.
- AAS Runtime Freeze removal: not authorized.

## Exit evidence

A successful merge is not sufficient. The exact merge commit must produce:

- successful ASIE CI and cross-platform determinism checks;
- successful Evidence-Backed Beta Release Gate with `CONDITIONAL_GO`;
- successful Governed Freeze Review using
  `tools.gov_rel_10_controlled_unfreeze`;
- unchanged hashes for every AAS Runtime Freeze file.
