# FINANCE-V2-S2C3C — Deterministic Sensitivity Benchmark Evidence

- Evidence version: `v2.4.0`
- Status: `FINAL_REVIEW_GAP_REPAIR_SOURCE_VERIFIED_AWAITING_EVIDENCE_HEAD_GATES`
- Owner: Finance Engineering + Principal Architecture
- Last verified: 2026-08-22
- Scope: C3C deterministic 2D sensitivity dark build only
- Governing decisions: `ACR-FIN-003-C3C-v1.0.0` and `ACR-FIN-004-v0.2.0`
- Verified implementation source SHA: `271606804293f6f831fb47e3b14a04843ccb924d`
- ASIE CI verification: [#455](https://github.com/alphasigma13579-lang/ASIE/actions/runs/32542989778)
- Cross-platform verification: [#306](https://github.com/alphasigma13579-lang/ASIE/actions/runs/32542989781)

## Decision and claim boundary

The verified source implements deterministic C3C only. It proves bounded,
repeatable execution of an approved two-axis profile. It does not authorize
Runtime, Snapshot, provider, network, professional, bank, G1, or production
use. It does not establish calibration quality, financing readiness, or the
later C3D-C3F gates.

## Final review-repair scope

The verified source incorporates independent audits of the actionable findings
across four exact-head CodeRabbit reviews without treating their suggestions as
authority:

- it keeps Finance-model metric Decimals at full finite precision and documents
  why applying the eight-decimal input quantizer to output metrics would change
  financial values and the result hash;
- it requires non-empty `axis_id` and `target_ref` values in the result
  schema and asserts those constraints;
- it emits cross-platform evidence bytes through the shared
  `finance-v2-canonical-json.v1` serializer and tests the emitted bytes;
- it proves a grid above the hard cap is rejected before any model build;
- it makes the governed dependency tuple unambiguous without changing its
  value;
- it constrains blocker text and severity to the actual fail-closed serializer;
- it requires the exact Ubuntu/Windows and hash-seed label matrix, not merely
  four equal files;
- it pins nested profile, axis, and cell fields in the result-hash preimage
  regression test;
- it compares migrated non-idempotent `fixed_overrides` against an established
  equivalent input baseline for identical cell input hashes and metrics, and
  pins the fixed-override failure as an atomic `not_ready` result;
- it states that the mocked 441-cell test proves grid structure and invocation
  counts while the CI benchmark exercises the real 441×240×8 path;
- it rejects unsupported shared-kernel operations instead of falling through
  to addition, with a direct regression test;
- it requires unique top-level result `axis_ids`; admitted profiles already
  reject duplicate axis IDs and require at least two values per axis;
- it guards the exact C3C emit/compare workflow commands, retains diagnostic
  evidence on comparison failure, and bounds CI execution time; and
- it leaves engine calculations, the 441-cell hard cap, fail-closed behavior,
  and all protected paths unchanged.

## Correction record

Earlier benchmark records are superseded because their fixture executed 12
periods and two metrics while labeling the workload as 240 periods and eight
metrics. The current harness constructs the actual maximum workload and rejects
a sample unless the complete result is present.

The repair deliberately kept the fail-closed contract. A selected metric that
is absent, non-finite, or not applicable to a result contract without
applicability envelopes makes the whole sensitivity result `not_ready` with
`cells=[]`; it is never replaced by null or zero.

Three intermediate failures prevented false closure:

- [ASIE CI #443](https://github.com/alphasigma13579-lang/ASIE/actions/runs/32513123742) rejected a test that incorrectly demanded all eight metrics from
  the 12-period default fixture.
- [Cross-Platform #295](https://github.com/alphasigma13579-lang/ASIE/actions/runs/32513914559) rejected a fixture-value change that pushed default-grid
  IRR outside the supported solver range and therefore produced an atomic
  `not_ready` result.
- [ASIE CI #454](https://github.com/alphasigma13579-lang/ASIE/actions/runs/32542837786) rejected the final-gap test because its
  `FinanceContractError` import was missing; the one-line test import was
  corrected before rerunning every gate.

The corrected baseline and subsequent verified sources were separate events:

- [ASIE CI #445](https://github.com/alphasigma13579-lang/ASIE/actions/runs/32515050281) passed all 884 Python tests and completed the true maximum
  workload, but correctly failed the stale 10.7-second gate. That run became
  the governed full-workload baseline.
- ASIE CI #446 preserved the workload, applied the ACR ceiling formula, and
  passed the complete test and benchmark gates.
- ASIE CI #448 and Cross-Platform #299 verified the first review-repair source.
- ASIE CI #450 and Cross-Platform #301 verified the schema and integrity
  review-repair source.
- ASIE CI #452 and Cross-Platform #303 verified the fixed-override regression
  source.
- ASIE CI #455 and Cross-Platform #306 verified the final gap-repair source
  without changing the workload, hard caps, financial calculations, or
  canonical C3C result.

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

ASIE CI #455 verified
`271606804293f6f831fb47e3b14a04843ccb924d`:

| Verification measure | Value |
|---|---:|
| Python tests | 890 passed |
| Warnings | 10 |
| Test duration | 78.43 s |
| Trial 1 | 19.403038527999996 s |
| Trial 2 | 19.558964340000017 s |
| Trial 3 | 19.546192899999966 s |
| p50 | 19.546192899999966 s |
| p95 | 19.558964340000017 s |
| Peak RSS | 22.93359375 MiB |
| Runtime ceiling | 29.961531237000017 s — passed |
| Memory ceiling | 64.0 MiB — passed |

## Cross-platform canonical evidence

Cross-Platform #306 emitted the actual C3C 3×3 canonical result in all four
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
| T-C3C-015 cross-platform result | Cross-Platform #306, four byte-identical files |
| T-C3C-016 protected paths | no Runtime, Snapshot, Decision Council, or AAS freeze file changed |
| T-C3C-017 dark import boundary | existing import-boundary tests, 890-test suite |
| T-C3C-018 performance evidence | ASIE CI #445 baseline and #455 passing gate |

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
