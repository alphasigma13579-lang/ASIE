from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

from backend.beta_release_gate import (
    DEGRADABLE_CAPABILITIES,
    GATE_CONTRACT_ID,
    canonical_sha256,
)
from backend.dib_registry_admission import assert_all_frozen_files_unchanged
from backend.release_freeze_contract import validate_controlled_unfreeze_marker

REVIEW_SCHEMA = "asie.controlled.unfreeze.review.v1"
PACKAGE_ID = "GOV-REL-10-CONTROLLED-UNFREEZE-EXECUTION"
VERIFIED = "TECHNICAL_LIMITED_UNFREEZE_VERIFIED"
REJECTED = "REJECT_UNFREEZE"
DEFERRED = "UNFREEZE_DEFERRED_FOUNDATION_PENDING"
FOUNDATION_PROGRAM_ID = "FOUNDATION-COMPLETE-20"
FOUNDATION_ACTIVE_STATUS = "ACTIVE_IMPLEMENTATION_PROGRAM"
FOUNDATION_BLOCK_VERDICT = "BLOCK"
FOUNDATION_CRITICAL_CHECK = "foundation_completion_program_cleared"
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_IMAGE_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def _report_hash(report: Mapping[str, Any]) -> str:
    material = dict(report)
    material.pop("review_hash", None)
    return canonical_sha256(material)


def _gate_report_hash(report: Mapping[str, Any]) -> str:
    material = dict(report)
    material.pop("report_hash", None)
    return canonical_sha256(material)


def _gate_checks(report: Mapping[str, Any]) -> tuple[dict[str, Mapping[str, Any]], bool]:
    raw = report.get("checks")
    if not isinstance(raw, list):
        return {}, False
    checks: dict[str, Mapping[str, Any]] = {}
    unique = True
    for item in raw:
        if not isinstance(item, Mapping):
            unique = False
            continue
        check_id = str(item.get("check_id") or "")
        if not check_id or check_id in checks:
            unique = False
            continue
        checks[check_id] = item
    return checks, unique


def _foundation_deferral_evidence(
    gate_report: Mapping[str, Any],
    records: Mapping[str, Mapping[str, Any]],
    *,
    contract_ok: bool,
    commit_bound: bool,
) -> tuple[bool, dict[str, Any]]:
    """Recognize the single governed shape where the fresh gate is NO_GO only
    because FOUNDATION-COMPLETE-20 is deliberately blocking release while the
    implementation program is still active. Any other deviation stays REJECT."""

    foundation = records.get(FOUNDATION_CRITICAL_CHECK) or {}
    raw_evidence = foundation.get("evidence")
    evidence = raw_evidence if isinstance(raw_evidence, Mapping) else {}
    smoke = records.get("private_deployment_smoke_passed") or {}
    freeze = records.get("emergency_release_freeze_cleared") or {}
    expected_degraded = set(DEGRADABLE_CAPABILITIES)
    actual_degraded = gate_report.get("degraded_capabilities")
    deferral_ok = bool(
        contract_ok
        and commit_bound
        and gate_report.get("decision") == "NO_GO"
        and gate_report.get("release_allowed") is False
        and gate_report.get("public_beta_allowed") is False
        and gate_report.get("technical_limited_beta_allowed") is False
        and gate_report.get("code_evidence_ready") is True
        and gate_report.get("critical_failures") == [FOUNDATION_CRITICAL_CHECK]
        and foundation.get("passed") is False
        and evidence.get("program_id") == FOUNDATION_PROGRAM_ID
        and evidence.get("status") == FOUNDATION_ACTIVE_STATUS
        and evidence.get("current_release_verdict") == FOUNDATION_BLOCK_VERDICT
        and isinstance(actual_degraded, list)
        and len(actual_degraded) == len(set(actual_degraded))
        and set(actual_degraded) == expected_degraded
        and smoke.get("passed") is True
        and freeze.get("passed") is True
        and gate_report.get("manual_readiness_assertions_accepted") is False
        and gate_report.get("secrets_exposed") is False
        and gate_report.get("finance_mutated") is False
        and gate_report.get("snapshot_mutated") is False
        and gate_report.get("external_fetch_changed") is False
        and _IMAGE_DIGEST_RE.fullmatch(
            str(gate_report.get("deployment_image_digest") or "")
        )
    )
    return deferral_ok, {
        "foundation_program_id": evidence.get("program_id"),
        "foundation_status": evidence.get("status"),
        "foundation_release_verdict": evidence.get("current_release_verdict"),
        "gate_decision": gate_report.get("decision"),
        "critical_failures": gate_report.get("critical_failures"),
    }


def evaluate_controlled_unfreeze(
    gate_report: Mapping[str, Any],
    freeze_marker: Mapping[str, Any],
    *,
    expected_commit: str,
    frozen_files_unchanged: bool,
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    marker_validation = validate_controlled_unfreeze_marker(freeze_marker)
    checks.append(
        {
            "check_id": "controlled_unfreeze_marker_integrity",
            "passed": marker_validation["valid"] is True,
            "evidence": marker_validation,
        }
    )

    supplied_hash = str(gate_report.get("report_hash") or "")
    computed_hash = _gate_report_hash(gate_report)
    records, unique = _gate_checks(gate_report)
    contract_ok = bool(
        gate_report.get("contract_id") == GATE_CONTRACT_ID
        and _SHA256_RE.fullmatch(supplied_hash)
        and supplied_hash == computed_hash
        and unique
    )
    checks.append(
        {
            "check_id": "post_unfreeze_gate_contract_integrity",
            "passed": contract_ok,
            "evidence": {
                "contract_id": gate_report.get("contract_id"),
                "report_hash": supplied_hash or None,
                "computed_hash": computed_hash,
                "unique_check_ids": unique,
            },
        }
    )

    commit_bound = bool(
        _SHA_RE.fullmatch(expected_commit)
        and gate_report.get("release_commit") == expected_commit
    )
    checks.append(
        {
            "check_id": "post_unfreeze_gate_commit_bound",
            "passed": commit_bound,
            "evidence": {
                "expected_commit": expected_commit,
                "release_commit": gate_report.get("release_commit"),
            },
        }
    )

    smoke = records.get("private_deployment_smoke_passed") or {}
    freeze = records.get("emergency_release_freeze_cleared") or {}
    expected_degraded = set(DEGRADABLE_CAPABILITIES)
    actual_degraded = gate_report.get("degraded_capabilities")
    limited_gate_ok = bool(
        contract_ok
        and commit_bound
        and gate_report.get("decision") == "CONDITIONAL_GO"
        and gate_report.get("release_allowed") is True
        and gate_report.get("public_beta_allowed") is False
        and gate_report.get("technical_limited_beta_allowed") is True
        and gate_report.get("code_evidence_ready") is True
        and gate_report.get("critical_failures") == []
        and isinstance(actual_degraded, list)
        and len(actual_degraded) == len(set(actual_degraded))
        and set(actual_degraded) == expected_degraded
        and smoke.get("passed") is True
        and freeze.get("passed") is True
        and gate_report.get("manual_readiness_assertions_accepted") is False
        and gate_report.get("secrets_exposed") is False
        and gate_report.get("finance_mutated") is False
        and gate_report.get("snapshot_mutated") is False
        and gate_report.get("external_fetch_changed") is False
        and _IMAGE_DIGEST_RE.fullmatch(
            str(gate_report.get("deployment_image_digest") or "")
        )
    )
    checks.append(
        {
            "check_id": "technical_limited_gate_state",
            "passed": limited_gate_ok,
            "evidence": {
                "decision": gate_report.get("decision"),
                "critical_failures": gate_report.get("critical_failures"),
                "degraded_capabilities": actual_degraded,
                "public_beta_allowed": gate_report.get("public_beta_allowed"),
                "technical_limited_beta_allowed": gate_report.get(
                    "technical_limited_beta_allowed"
                ),
                "private_deployment_smoke_passed": smoke.get("passed"),
                "freeze_check_passed": freeze.get("passed"),
                "deployment_image_digest": gate_report.get(
                    "deployment_image_digest"
                ),
            },
        }
    )

    checks.append(
        {
            "check_id": "aas_runtime_freeze_hashes_unchanged",
            "passed": bool(frozen_files_unchanged),
            "evidence": {"frozen_files_unchanged": bool(frozen_files_unchanged)},
        }
    )

    failures = [item["check_id"] for item in checks if item["passed"] is not True]
    verified = not failures
    deferral_ok, deferral_evidence = _foundation_deferral_evidence(
        gate_report,
        records,
        contract_ok=contract_ok,
        commit_bound=commit_bound,
    )
    deferred = bool(
        not verified
        and failures == ["technical_limited_gate_state"]
        and deferral_ok
        and frozen_files_unchanged
    )
    if verified:
        decision = VERIFIED
    elif deferred:
        decision = DEFERRED
    else:
        decision = REJECTED
    report: dict[str, Any] = {
        "schema": REVIEW_SCHEMA,
        "package_id": PACKAGE_ID,
        "decision": decision,
        "review_commit": expected_commit,
        "gate_report_hash": supplied_hash or None,
        "deployment_image_digest": gate_report.get("deployment_image_digest"),
        "failures": failures,
        "checks": checks,
        "foundation_deferral": {
            "active": deferred,
            "evidence": deferral_evidence,
        },
        "technical_limited_release_gate_allowed": verified,
        "public_release_authorized": False,
        "external_network_authorized": False,
        "provider_activation_authorized": False,
        "finance_mutated": False,
        "snapshot_mutated": False,
        "aas_runtime_freeze_mutated": False,
    }
    report["review_hash"] = _report_hash(report)
    return report


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def write_report(path: Path, report: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dict(report), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify the fail-closed GOV-REL-10 controlled unfreeze transition."
    )
    parser.add_argument("--gate-report", type=Path, required=True)
    parser.add_argument("--freeze-marker", type=Path, required=True)
    parser.add_argument("--expected-commit", required=True)
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--require-verified", action="store_true")
    parser.add_argument("--allow-foundation-deferral", action="store_true")
    args = parser.parse_args(argv)

    package_root = Path(__file__).resolve().parents[1]
    try:
        assert_all_frozen_files_unchanged(package_root)
        frozen_files_unchanged = True
    except (AssertionError, OSError, KeyError, json.JSONDecodeError):
        frozen_files_unchanged = False

    report = evaluate_controlled_unfreeze(
        _load_json(args.gate_report),
        _load_json(args.freeze_marker),
        expected_commit=str(args.expected_commit or "").strip(),
        frozen_files_unchanged=frozen_files_unchanged,
    )
    write_report(args.output, report)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))

    if args.require_verified:
        acceptable = {VERIFIED}
        if args.allow_foundation_deferral:
            acceptable.add(DEFERRED)
        if report["decision"] not in acceptable:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
