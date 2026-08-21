"""Emit and compare deterministic C3C sensitivity results across CI platforms."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from collections.abc import Sequence


_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def _ensure_repository_imports() -> None:
    repository_root = str(_REPOSITORY_ROOT)
    if repository_root not in sys.path:
        sys.path.insert(0, repository_root)


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def emit(output: Path) -> dict[str, object]:
    _ensure_repository_imports()
    from backend.finance_v2 import (
        canonical_json,
        canonical_sha256,
        evaluate_sensitivity,
    )
    from tests.finance_v2_sensitivity_fixture import controlled_sensitivity_prepared_run

    result = evaluate_sensitivity(controlled_sensitivity_prepared_run())
    payload = result.as_dict()
    if result.status != "dark_ready" or len(result.cells) != 9:
        raise RuntimeError("C3C cross-platform vector is not a complete 3x3 result")
    if result.result_hash != canonical_sha256(
        result.as_dict(include_hash=False)
    ):
        raise RuntimeError("C3C result hash does not match its canonical preimage")

    encoded = canonical_json(payload).encode("utf-8")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(encoded)
    return {
        "mode": "emit",
        "output": output.as_posix(),
        "bytes": len(encoded),
        "result_hash": result.result_hash,
        "serialized_sha256": "sha256:" + hashlib.sha256(encoded).hexdigest(),
    }


def compare(directory: Path) -> dict[str, object]:
    files = sorted(directory.glob("**/c3c-sensitivity.json"))
    if len(files) != 4:
        raise RuntimeError(
            f"expected four C3C platform vectors, found {len(files)}"
        )
    payloads = [path.read_bytes() for path in files]
    baseline = payloads[0]
    mismatches = [
        files[index].as_posix()
        for index, payload in enumerate(payloads)
        if payload != baseline
    ]
    if mismatches:
        raise RuntimeError(
            "C3C canonical bytes differ across platforms: "
            + ", ".join(mismatches)
        )
    decoded = json.loads(baseline.decode("utf-8"))
    return {
        "mode": "compare",
        "status": "byte_identical",
        "vector_count": len(files),
        "files": [path.as_posix() for path in files],
        "result_hash": decoded["result_hash"],
        "serialized_sha256": "sha256:"
        + hashlib.sha256(baseline).hexdigest(),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    emit_parser = subparsers.add_parser("emit")
    emit_parser.add_argument("--output", type=Path, required=True)
    compare_parser = subparsers.add_parser("compare")
    compare_parser.add_argument("--directory", type=Path, required=True)
    args = parser.parse_args(argv)

    output = (
        emit(args.output)
        if args.command == "emit"
        else compare(args.directory)
    )
    print(_canonical_json(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
