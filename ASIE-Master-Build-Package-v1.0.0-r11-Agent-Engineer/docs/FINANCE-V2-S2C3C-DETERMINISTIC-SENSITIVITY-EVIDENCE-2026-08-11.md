# FINANCE-V2-S2C3C — Deterministic Sensitivity Benchmark Evidence

- Status: `FINAL_IMPLEMENTATION_VERIFIED_AWAITING_EVIDENCE_HEAD_CI_AND_INDEPENDENT_REVIEW`
- Scope: C3C deterministic 2D sensitivity dark build only
- Governing decision: `ACR-FIN-003-C3C-v1.0.0`
- Verified implementation source SHA: `6e08d76a831f45f3958a7c97bb50a930bf4a7948`
- ASIE CI verification: [#389](https://github.com/alphasigma13579-lang/ASIE/actions/runs/31894041767)
- Cross-platform verification: [#239](https://github.com/alphasigma13579-lang/ASIE/actions/runs/31894041773)

## Correction record

The earlier #343 measurement is superseded. Its fixture executed 12 periods and
two metrics while its output labels stated the governed caps of 240 periods and
eight metrics. PR #136 review identified that mismatch. The corrected harness
constructs and asserts the actual maximum supported workload before timing.

Run #345 intentionally retained the former 5.0-second ceiling for the first
corrected measurement. All 834 Python tests passed, then the benchmark failed
only because the corrected p95 exceeded that stale ceiling. That failure
provided the corrected baseline used to derive the automated ceilings below; it
is not represented as a passing gate.

Subsequent review also required the cross-platform workflow to emit and compare
the actual C3C canonical result, rather than relying only on the pre-existing
general deterministic vector. Run #239 performs that comparison across Linux
and Windows under `PYTHONHASHSEED=0` and `PYTHONHASHSEED=7919`. The verified
result hash includes organization, project, and run provenance.

## Method

The CI-only harness `scripts/benchmark_finance_v2_sensitivity.py` runs one
warm-up followed by three full-path executions of an admitted 21×21 profile:

`prepare → 441 × (derive validated input → full Finance v2 model over 240 periods → project 8 metrics) → atomic result`

Before accepting a timing sample, the harness asserts:

- exactly 240 validated monthly periods;
- exactly 441 ordered cells;
- exactly the eight governed sensitivity metrics in every cell;
- `dark_ready` status.

It uses the production C3C engine with no monkeypatch, cache, network,
Runtime, Snapshot, or provider call.

| Parameter | Value |
|---|---:|
| K | 441 |
| Periods | 240 |
| Metrics | 8 |
| Warm-ups | 1 |
| Measured trials | 3 |
| Python | 3.13.15 |
| Runner platform | Linux 6.17.0-1022-azure x86_64 |

## Corrected baseline and exact implementation verification

The corrected #345 baseline remains the source for the governed ceiling:

| Baseline measure | Value |
|---|---:|
| Trial 1 | 7.120399158 s |
| Trial 2 | 7.080133590 s |
| Trial 3 | 7.081234730 s |
| p50 | 7.081234730 s |
| p95 | 7.120399158 s |
| Peak RSS | 33.05859375 MiB |

Run #389 verified the final repaired implementation head against those ceilings:

| Verification measure | Value |
|---|---:|
| Python tests | 882 passed |
| Trial 1 | 8.966687895 s |
| Trial 2 | 8.924399990 s |
| Trial 3 | 8.885724415 s |
| p50 | 8.924399990 s |
| p95 | 8.966687895 s |
| Peak RSS | 22.65625 MiB |
| Runtime ceiling | 10.7 s — passed |
| Memory ceiling | 64.0 MiB — passed |

The final implementation additionally requires exact boolean values at every C3C authority, admission, dark-readiness, runtime-eligibility, and global-permission gate; malformed truthy/falsy substitutes fail closed before any cell build.

The final review-repair head also makes the shared governed fixture independent
of every `test_*.py` module and of `pytest`, so the unittest-only
cross-platform emitter runs with the standard library plus production package
only. The fixture retains its original finance-input and risk-profile lineage;
therefore the canonical C3C result and serialized hashes remain unchanged.

## Cross-platform canonical evidence

Run #239 emitted the actual C3C 3×3 canonical result in all four matrix jobs and
compared the files byte-for-byte:

| Evidence | Value |
|---|---|
| Platforms | Ubuntu, Windows |
| Hash seeds | 0, 7919 |
| Canonical files compared | 4 |
| Comparison status | `byte_identical` |
| C3C result hash | `sha256:2cba97ca5e388d9826928b7064b76d6d328c3472332fdc43849e2e5d9f3f9280` |
| Serialized SHA-256 | `sha256:b007c120134ae0c55ec98087fc73385f8a7a0709e97587dbf1e5d0066d675f3a` |

## Automated ceilings

The governing ACR formula is applied without relaxation:

- raw runtime formula: `1.50 × 7.120399158 = 10.680598737s`;
- enforced runtime ceiling: `10.7s`, rounded upward to one decimal place;
- raw memory formula: `1.25 × 33.05859375 = 41.3232421875MiB`;
- enforced memory ceiling: `64.0MiB`, because the governed floor is 64MiB.

Both remain below the ACR hard caps of 60 seconds and 256MiB. The corrected
harness identifier is
`finance-v2-c3c-deterministic-21x21-max-workload.v2`.

The evidence-document commit necessarily descends from the measured
implementation SHA. Its own exact-head CI status must therefore be recorded in
PR #136 metadata after this document-only update completes. Independent
architecture/security review remains required.

Nothing here authorizes Runtime/Snapshot use or a professional, bank, G1,
production, network, or provider claim.

## Residual boundaries

This evidence validates deterministic C3C performance only. It does not
validate calibration quality, RNG, distributions, correlation, convergence,
financing readiness, external data, or any later C3D–C3F/G1 gate.
