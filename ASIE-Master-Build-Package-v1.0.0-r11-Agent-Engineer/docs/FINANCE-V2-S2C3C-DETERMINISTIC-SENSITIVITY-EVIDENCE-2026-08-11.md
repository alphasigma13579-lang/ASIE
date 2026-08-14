# FINANCE-V2-S2C3C — Deterministic Sensitivity Benchmark Evidence

- Status: `CORRECTED_MAX_WORKLOAD_BASELINE_AWAITING_EXACT_HEAD_CI_AND_REVIEW`
- Scope: C3C deterministic 2D sensitivity dark build only
- Governing decision: `ACR-FIN-003-C3C-v1.0.0`
- Measured source SHA: `865112280d64663cfee7686843f8f8b9aa19a7cb`
- ASIE CI baseline run: [#345](https://github.com/alphasigma13579-lang/ASIE/actions/runs/31801057520)
- Cross-platform run: [#195](https://github.com/alphasigma13579-lang/ASIE/actions/runs/31801057515)

## Correction record

The earlier #343 measurement is superseded. Its fixture executed 12 periods and
two metrics while its output labels stated the governed caps of 240 periods and
eight metrics. PR #136 review identified that mismatch. The corrected harness
constructs and asserts the actual maximum supported workload before timing.

Run #345 intentionally retained the former 5.0-second ceiling for the first
corrected measurement. All 834 Python tests passed, then the benchmark failed
only because the corrected p95 exceeded that stale ceiling. That failure is the
source measurement used below; it is not represented as a passing gate.

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

## Corrected measured baseline

| Measure | Value |
|---|---:|
| Trial 1 | 7.120399158 s |
| Trial 2 | 7.080133590 s |
| Trial 3 | 7.081234730 s |
| p50 | 7.081234730 s |
| p95 | 7.120399158 s |
| Peak RSS | 33.05859375 MiB |

## Proposed automated ceilings

The governing ACR formula is applied without relaxation:

- raw runtime formula: `1.50 × 7.120399158 = 10.680598737s`;
- enforced runtime ceiling: `10.7s`, rounded upward to one decimal place;
- raw memory formula: `1.25 × 33.05859375 = 41.3232421875MiB`;
- enforced memory ceiling: `64.0MiB`, because the governed floor is 64MiB.

Both remain well below the ACR hard caps of 60 seconds and 256MiB. The corrected
harness identifier is
`finance-v2-c3c-deterministic-21x21-max-workload.v2`.

These numbers remain subject to exact-head CI and independent
architecture/security review. They authorize neither Runtime/Snapshot use nor
a professional, bank, G1, production, network, or provider claim.

## Residual boundaries

This evidence validates deterministic C3C performance only. It does not
validate calibration quality, RNG, distributions, correlation, convergence,
financing readiness, external data, or any later C3D–C3F/G1 gate.
