"""Measure the governed C3C 21x21 full-path sensitivity benchmark on CI only."""

from __future__ import annotations

import argparse
import gc
import json
import math
import platform
import sys
import time
from pathlib import Path

RUNTIME_CEILING_SECONDS = 10.7
MEMORY_CEILING_MIB = 64.0

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.finance_v2 import evaluate_sensitivity, monthly_periods
from tests.finance_v2_sensitivity_fixture import controlled_sensitivity_prepared_run


_METRIC_IDS = [
    "npv_unlevered",
    "irr_unlevered",
    "mirr_unlevered",
    "payback_months",
    "break_even",
    "funding_need",
    "dscr_min",
    "llcr",
]


def _max_input(document: dict) -> None:
    start_period = document["forecast"]["start_period"]
    periods = monthly_periods(start_period, 240)
    document["forecast"]["monthly_periods"] = 240
    for stream in document["revenue_streams"]:
        for series_name in (
            "volume_series",
            "price_series",
            "variable_cost_series",
            "capacity_series",
        ):
            if series_name not in stream:
                continue
            seed_value = stream[series_name][0]["value"]
            stream[series_name] = [
                {"period": period, "value": seed_value}
                for period in periods
            ]
    for cost in document["operating_costs"]:
        seed_value = cost["schedule"][0]["value"]
        cost["schedule"] = [
            {"period": period, "value": seed_value}
            for period in periods
        ]


def _max_profile(profile_document: dict) -> None:
    profile_document["axes"][0]["values"] = [str(value) for value in range(1, 22)]
    profile_document["axes"][1]["values"] = [str(value) for value in range(1, 22)]
    profile_document["metric_ids"] = list(_METRIC_IDS)
    profile_document["maximum_cells"] = 441


def _percentile_nearest_rank(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    return ordered[math.ceil(percentile * len(ordered)) - 1]


def _peak_rss_mib(ru_maxrss: float, platform_name: str = sys.platform) -> float:
    if platform_name == "darwin":
        return ru_maxrss / (1024 * 1024)
    if platform_name.startswith("linux"):
        return ru_maxrss / 1024
    raise RuntimeError(
        f"unsupported ru_maxrss unit on platform {platform_name!r}"
    )


def _one_run() -> float:
    prepared = controlled_sensitivity_prepared_run(
        input_mutator=_max_input,
        profile_mutator=_max_profile,
    )
    if len(prepared.validated_input.periods) != 240:
        raise RuntimeError("C3C benchmark input does not contain 240 periods")
    started = time.perf_counter()
    result = evaluate_sensitivity(prepared)
    elapsed = time.perf_counter() - started
    if (
        result.status != "dark_ready"
        or len(result.cells) != 441
        or tuple(result.metric_ids) != tuple(_METRIC_IDS)
        or any(len(cell.metrics) != 8 for cell in result.cells)
    ):
        raise RuntimeError(
            "C3C benchmark did not produce the complete "
            "441-cell, 240-period, eight-metric dark result"
        )
    return elapsed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--warmups", type=int, default=1)
    parser.add_argument("--trials", type=int, default=3)
    args = parser.parse_args()
    if args.warmups < 0 or args.trials < 3:
        raise SystemExit("warmups must be >= 0 and trials must be >= 3")

    for _ in range(args.warmups):
        _one_run()
        gc.collect()

    durations: list[float] = []
    for _ in range(args.trials):
        gc.collect()
        durations.append(_one_run())

    try:
        import resource
    except ImportError as exc:
        raise SystemExit(
            "C3C RSS benchmark supports Linux and macOS only"
        ) from exc
    peak_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    output = {
        "benchmark": "finance-v2-c3c-deterministic-21x21-max-workload.v2",
        "k": 441,
        "period_cap": 240,
        "metric_cap": 8,
        "warmups": args.warmups,
        "trials": args.trials,
        "durations_seconds": durations,
        "p50_seconds": _percentile_nearest_rank(durations, 0.50),
        "p95_seconds": _percentile_nearest_rank(durations, 0.95),
        "peak_rss_mib": _peak_rss_mib(peak_rss),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
    }
    print(json.dumps(output, sort_keys=True))
    if output["p95_seconds"] > RUNTIME_CEILING_SECONDS:
        raise SystemExit(
            f"C3C p95 {output['p95_seconds']:.6f}s exceeds "
            f"{RUNTIME_CEILING_SECONDS:.3f}s"
        )
    if output["peak_rss_mib"] > MEMORY_CEILING_MIB:
        raise SystemExit(
            f"C3C peak RSS {output['peak_rss_mib']:.3f}MiB exceeds "
            f"{MEMORY_CEILING_MIB:.3f}MiB"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
