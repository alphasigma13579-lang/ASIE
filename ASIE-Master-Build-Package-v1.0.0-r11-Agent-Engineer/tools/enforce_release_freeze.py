from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from backend.release_freeze_contract import evaluate_release_freeze_marker

BLOCKED_EXIT_CODE = 78


def evaluate_release_freeze(marker: Mapping[str, Any]) -> dict[str, Any]:
    return evaluate_release_freeze_marker(marker)


def enforce_release_freeze(marker_path: Path) -> int:
    if not marker_path.is_file():
        print(
            json.dumps(
                {
                    "allowed": False,
                    "decision": "NO_GO",
                    "reason": "emergency_release_freeze_marker_missing",
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return BLOCKED_EXIT_CODE

    try:
        marker = json.loads(marker_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        print(
            json.dumps(
                {
                    "allowed": False,
                    "decision": "NO_GO",
                    "reason": "emergency_release_freeze_marker_invalid",
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return BLOCKED_EXIT_CODE

    if not isinstance(marker, dict):
        result = {
            "allowed": False,
            "decision": "NO_GO",
            "reason": "emergency_release_freeze_marker_invalid",
        }
    else:
        result = evaluate_release_freeze(marker)

    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["allowed"] else BLOCKED_EXIT_CODE


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fail closed unless the governed ASIE unfreeze proof is valid."
    )
    parser.add_argument(
        "--marker",
        type=Path,
        default=Path(__file__).resolve().parents[2]
        / "EMERGENCY-RELEASE-FREEZE.json",
    )
    args = parser.parse_args(argv)
    return enforce_release_freeze(args.marker)


if __name__ == "__main__":
    raise SystemExit(main())
