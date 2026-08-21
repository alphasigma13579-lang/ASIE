# FINANCE-V2-S2C3C — Deterministic Sensitivity Benchmark Evidence

- Evidence version: `v2.0.0`
- Status: `IMPLEMENTATION_SOURCE_VERIFIED_AWAITING_EVIDENCE_COMMIT_GATES`
- Owner: Finance Engineering + Principal Architecture
- Last verified: 2026-08-21
- Scope: C3C deterministic 2D sensitivity dark build only
- Governing decisions: `ACR-FIN-003-C3C-v1.0.0` and `ACR-FIN-004-v0.2.0`
- Verified implementation source SHA: `c110006713765b7070d37851632ceab6db82a63b`
- ASIE CI verification: [#446](https://github.com/alphasigma13579-lang/ASIE/actions/runs/32515874702)
- Cross-platform verification: [#297](https://github.com/alphasigma13579-lang/ASIE/actions/runs/32515874825)

## Decision and claim boundary

The verified source implements deterministic C3C only. It proves bounded,
repeatable execution of an approved two-axis profile. It does not authorize
Runtime, Snapshot, provider, network, professional, bank, G1, or production
use. It does not establish calibration quality, financing readiness, or the
later C3D-C3F gates.

## Correction record

Earlier benchmark records are superseded because their fixture executed 12
periods and two metrics while labeling the workload as 240 periods and eight
metrics. The current harness constructs the actual maximum workload and rejects
a sample unless the complete result is present.

The repair deliberately kept the fail-closed contract. A selected metric that
is absent, non-finite, or not applicable to a result contract without
applicability envelopes makes the whole sensitivity result `not_ready` with
`cells=[]`; it is never replaced by null or zero.

Two intermediate failures prevented false closure:

- [ASIE CI #443](https://github.com/alphasigma13579-lang/ASIE/actions/runs/32513123742) rejected a test that incorrectly demanded all eight metrics from
  the 12-period default fixture.
- [Cross-Platform #295](https://github.com/alphasigma13579-lang/ASIE/actions/runs/32513914559) rejected a fixture-value change that pushed default-grid
  IRR outside the supported solver range and therefore produced an atomic
  `not_ready` result.
- [ASIE CI #445](https://github.com/alphasigma13579-lang/ASIE/actions/runs/32515050281) then passed all 884 Python tests and completed the true maximum
  workload, but correctly failed the stale 10.7-second gate. That run became
  the governed full-workload baseline.
- The final source #446 preserved the workload, applied the ACR ceiling formula,
  and passed the complete test and benchmark gates.

No engine behavior, IRR solver range, metric availability rule, or hard cap was
weakened to obtain a green result.

## Method

The CI-only harness `scripts/benchmark_finance_v2_sensitivity.py` runs one
warm-up followed by three full-path executions of an admitted 21×21 profile:

`prepare → 441 × (derive validated input → full Finance v2 model over 240 periods → project 8 metrics) → atomic result`

Before accepting any timing sample, the harness asserts:

- exactly 240 validated monthly periods;
- `status="dark_ready"`;
- `cell_count=441` and exactly 441 ordered cells;
- the exact eight governed metric IDs in their governed order;
- the exact eight keys in every cell;
- successful Decimal parsing and `is_finite()` for every one of the
  `441×8=3,528` projected values.

It uses the production C3C engine with no monkeypatch, cache, network, Runtime,
Snapshot, or provider call.

| Parameter | Value |
|---|---:|
| K | 441 |
| Periods | 240 |
| Metrics per cell | 8 |
| Finite metric values asserted per trial | 3,528 |
| Warm-ups | 1 |
| Measured trials | 3 |
| Python | 3.13.15 |
| Runner platform | Linux 6.17.0-1022-azure x86_64 |

## Full-workload baseline

[ASIE CI #445](https://github.com/alphasigma13579-lang/ASIE/actions/runs/32515050281) measured the corrected maximum workload at source
`38952be0c713bc42ae14f039e14784cd426c09c2`. The workload and finite-value
assertions completed successfully; only the superseded 10.7-second gate failed.

| Baseline measure | Value |
|---|---:|
| Trial 1 | 19.97435415800001 s |
| Trial 2 | 19.925822582999984 s |
| Trial 3 | 19.916704827000018 s |
| p50 | 19.925822582999984 s |
| p95 | 19.97435415800001 s |
| Peak RSS | 22.85546875 MiB |

## Automated ceilings

The governing ACR formula is applied directly:

- runtime:
  `min(60, max(5, 1.50 × 19.97435415800001)) = 29.961531237000017s`;
- memory baseline calculation:
  `1.25 × 22.85546875 = 28.5693359375MiB`;
- enforced memory ceiling: `64.0MiB`, because the governed floor is 64MiB.

The runtime ceiling remains below the 60-second hard cap. The memory ceiling
remains below the 256MiB hard cap. The workload is not reduced and the hard
caps are unchanged.

The harness emits the baseline p95, runtime ceiling, and memory ceiling in its
JSON evidence so the gate cannot be separated from its provenance.

## Exact implementation verification

ASIE CI #446 verified
`c110006713765b7070d37851632ceab6db82a63b`:

| Verification measure | Value |
|---|---:|
| Python tests | 884 passed |
| Warnings | 10 |
| Test duration | 78.84 s |
| Trial 1 | 19.342305273999983 s |
| Trial 2 | 19.408510444 s |
| Trial 3 | 19.459285378000004 s |
| p50 | 19.408510444 s |
| p95 | 19.459285378000004 s |
| Peak RSS | 23.66796875 MiB |
| Runtime ceiling | 29.961531237000017 s — passed |
| Memory ceiling | 64.0 MiB — passed |

## Cross-platform canonical evidence

Cross-Platform #297 emitted the actual C3C 3×3 canonical result in all four
matrix jobs and compared the files byte-for-byte:

| Evidence | Value |
|---|---|
| Platforms | Ubuntu, Windows |
| Hash seeds | 0, 7919 |
| Canonical files compared | 4 |
| Comparison status | `byte_identical` |
| C3C result hash | `sha256:118149783a246f1697287f4c23598e7da09367fdcbd12ab7c67b588706aaa48e` |
| Serialized SHA-256 | `sha256:162486eed3d5d157791b9d4cb6e211dae15cfbf7287cd685e4375ad80136cc4b` |

## Traceability

| Requirement | Implementation/evidence |
|---|---|
| T-C3C-007 maximum grid | benchmark asserts 441 ordered cells |
| T-C3C-010 unavailable metric | atomic `not_ready`, empty cells, no null/zero |
| T-C3C-015 cross-platform result | Cross-Platform #297, four byte-identical files |
| T-C3C-016 protected paths | no Runtime, Snapshot, Decision Council, or AAS freeze file changed |
| T-C3C-017 dark import boundary | existing import-boundary tests, 884-test suite |
| T-C3C-018 performance evidence | ASIE CI #445 baseline and #446 passing gate |

The evidence-document commit necessarily descends from the verified
implementation source. It cannot embed its own SHA without changing that SHA.
Its exact-head CI and reviewer status must therefore be verified from PR #136
after this document update. The source SHA and measured runs above remain the
immutable implementation evidence.

## Residual boundaries

This evidence validates deterministic C3C correctness, bounded maximum-workload
execution, and cross-platform canonical equality only. It does not validate
calibration quality, RNG, distributions, correlation, convergence, professional
finance approval, external data, or any later C3D-C3F/G1 gate.
