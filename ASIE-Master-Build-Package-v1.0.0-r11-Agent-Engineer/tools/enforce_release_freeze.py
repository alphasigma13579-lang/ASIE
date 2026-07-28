from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

FREEZE_SCHEMA = "asie.release.freeze.v1"
BLOCKED_EXIT_CODE = 78


def evaluate_release_freeze(marker: Mapping[str, Any]) -> dict[str, Any]:
    if marker.get("schema") != FREEZE_SCHEMA:
        return {
            "allowed": False,
            "decision": "NO_GO",
            "reason": "emergency_release_freeze_schema_invalid",
        }

    status = marker.get("status")
    release_gate_allowed = marker.get("release_gate_allowed") is True
    allowed = status == "CLEARED" and release_gate_allowed
    return {
        "allowed": allowed,
        "decision": "PENDING_GATE" if allowed else "NO_GO",
        "reason": "emergency_release_freeze_cleared" if allowed else "emergency_release_freeze_active",
        "baseline_commit": marker.get("baseline_commit"),
        "reason_codes": marker.get("reason_codes", []),
    }


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
    parser = argparse.ArgumentParser(description="Fail closed while the ASIE emergency release freeze is active.")
    parser.add_argument(
        "--marker",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "EMERGENCY-RELEASE-FREEZE.json",
    )
    args = parser.parse_args(argv)
    return enforce_release_freeze(args.marker)


if __name__ == "__main__":
    raise SystemExit(main())
