"""Measure the governed C3C 21x21 full-path sensitivity benchmark on CI only."""

from __future__ import annotations

import argparse
import gc
import json
import math
import platform
import resource
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.finance_v2 import evaluate_sensitivity
from tests.test_finance_v2_sensitivity import _prepared


def _max_grid(profile_document: dict) -> None:
    profile_document["axes"][0]["values"] = [str(value) for value in range(1, 22)]
    profile_document["axes"][1]["values"] = [str(value) for value in range(1, 22)]
    profile_document["maximum_cells"] = 441


def _percentile_nearest_rank(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    return ordered[math.ceil(percentile * len(ordered)) - 1]


def _one_run() -> float:
    prepared = _prepared(profile_mutator=_max_grid)
    started = time.perf_counter()
    result = evaluate_sensitivity(prepared)
    elapsed = time.perf_counter() - started
    if result.status != "dark_ready" or len(result.cells) != 441:
        raise RuntimeError("C3C benchmark did not produce a complete 441-cell dark result")
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

    peak_rss_kib = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    output = {
        "benchmark": "finance-v2-c3c-deterministic-21x21.v1",
        "k": 441,
        "period_cap": 240,
        "metric_cap": 8,
        "warmups": args.warmups,
        "trials": args.trials,
        "durations_seconds": durations,
        "p50_seconds": _percentile_nearest_rank(durations, 0.50),
        "p95_seconds": _percentile_nearest_rank(durations, 0.95),
        "peak_rss_mib": peak_rss_kib / 1024,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
    }
    print(json.dumps(output, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
