# FINANCE-V2-S2C3C — Deterministic Sensitivity Benchmark Evidence

- Status: `RATIFIED_CEILINGS_AWAITING_EXACT_HEAD_CI_AND_REVIEW`
- Scope: C3C deterministic 2D sensitivity dark build only
- Governing decision: `ACR-FIN-003-C3C-v1.0.0`
- Measured source SHA: `6e0dd7c84d2d180e9ca5397ee4a2f9ae7178d058`
- ASIE CI run: [#343](https://github.com/alphasigma13579-lang/ASIE/actions/runs/31541457602)
- Cross-platform run: [#193](https://github.com/alphasigma13579-lang/ASIE/actions/runs/31541457609)

## Method

The CI-only harness `scripts/benchmark_finance_v2_sensitivity.py` runs one warm-up followed by three full-path executions of an admitted 21×21 profile:

`prepare → 441 × (derive validated input → full Finance v2 model) → atomic result`

It uses the production C3C engine with no monkeypatch, no cache, no network, no Runtime/Snapshot call, and records monotonic elapsed time plus Linux process peak RSS.

| Parameter | Value |
|---|---:|
| K | 441 |
| Period cap | 240 |
| Metric cap | 8 |
| Warm-ups | 1 |
| Measured trials | 3 |
| Python | 3.13.14 |
| Runner platform | Linux 6.17.0-1020-azure x86_64 |

## Measured baseline

| Measure | Value |
|---|---:|
| Trial 1 | 0.784672001 s |
| Trial 2 | 0.783921702 s |
| Trial 3 | 0.781302323 s |
| p50 | 0.781302323 s |
| p95 | 0.784672001 s |
| Peak RSS | 31.47265625 MiB |

## Ratified automated ceilings

The governing formula is applied without relaxation:

- `runtime_ceiling = min(60s, max(5s, 1.50 × p95)) = 5.0s`
- `memory_ceiling = min(256MiB, max(64MiB, 1.25 × peak_RSS)) = 64.0MiB`

The harness enforces both ceilings in ASIE CI on every PR revision. Any exceedance fails CI. These ceilings authorize neither Runtime/Snapshot use nor a professional, bank, G1, or production claim.

## Residual boundaries

This evidence validates deterministic C3C performance only. It does not validate calibration quality, RNG, distributions, correlation, convergence, financing readiness, external data, or any later C3D–C3F/G1 gate.
