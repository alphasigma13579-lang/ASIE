from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from backend.beta_release_gate import GATE_CONTRACT_ID, canonical_sha256

REVIEW_SCHEMA = "asie.governed.freeze.review.v1"
PACKAGE_ID = "GOV-REL-09"
FREEZE_SCHEMA = "asie.release.freeze.v1"

ELIGIBLE = "ELIGIBLE_FOR_UNFREEZE"
KEEP_FROZEN = "KEEP_FROZEN"
REJECT_UNFREEZE = "REJECT_UNFREEZE"

EXPECTED_SCOPE = {
    "public_beta",
    "production_deployment",
    "external_network_exposure",
}

EXPECTED_REASON_CODES = {
    "production_bootstrap_takeover",
    "zero_user_implicit_principal",
    "dib_cross_tenant_access",
    "forged_manifest_gate_finance_execution",
    "dib_thread_unsafe_sqlite",
    "release_gate_without_runtime_evidence",
}

EXPECTED_PROTECTED_BOUNDARIES = {
    "AAS Runtime Freeze v1.0",
    "Finance calculations",
    "Snapshot Assembly",
    "Decision Council",
}

EXPECTED_UNFREEZE_REQUIREMENTS = {
    "SEC-BETA-01 closed with exploit tests",
    "STAB-BETA-02 closed with concurrent HTTP tests",
    "SEC-BETA-03 closed with cross-tenant denial tests",
    "GOV-BETA-04 closed with forged lineage denial tests",
    "ARCH-BETA-05 closed with canonical ProjectRunWorkflow evidence",
    "REL-BETA-07 evidence-backed gate on the release commit",
}

REQUIRED_PACKAGE_COMMITS: dict[str, str] = {
    "SEC-BETA-01": "22437844b49ff4ae81e5936df5638129fb9cb7ec",
    "STAB-BETA-02": "8ce8edf97203a377c87bbe8e2cb9518b442d6da0",
    "SEC-BETA-03": "6615b1828a31a079b4d57616878aca64d6cf6b0a",
    "GOV-BETA-04": "3d29486480436c4ac02567207c449ba1dfe6a621",
    "ARCH-BETA-05": "f0a36a18ba778dde1564df5fb6079a5bc9d2f6b8",
    "TEST-BETA-06": "ddbcae583da3807467abf74a679c4b533e6d9918",
    "REL-BETA-07": "9e20b980cee4936e8669198fc8c5c52f8186d489",
    "DEPLOY-BETA-08": "eef452f0ea45f4fe857d8132f124ed5cfdab5d96",
}

PACKAGE_ROOT = "ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer"
REQUIRED_EVIDENCE_PATHS: dict[str, tuple[str, ...]] = {
    "SEC-BETA-01": (
        f"{PACKAGE_ROOT}/docs/SEC-BETA-01-PRODUCTION-IDENTITY-BOOTSTRAP-LOCKDOWN-2026-07-29.md",
        f"{PACKAGE_ROOT}/tests/test_sec_beta_01_bootstrap_lockdown.py",
        f"{PACKAGE_ROOT}/tests/test_sec_beta_01_initial_admin_cli.py",
    ),
    "STAB-BETA-02": (
        f"{PACKAGE_ROOT}/docs/STAB-BETA-02-TRANSACTION-SAFE-DIB-PERSISTENCE-2026-07-29.md",
        f"{PACKAGE_ROOT}/tests/test_stab_beta_02_transaction_safe_dib_persistence.py",
    ),
    "SEC-BETA-03": (
        f"{PACKAGE_ROOT}/docs/SEC-BETA-03-DIB-TENANT-OWNERSHIP-BOUNDARY-2026-07-29.md",
        f"{PACKAGE_ROOT}/tests/test_sec_beta_03_dib_tenant_boundary.py",
    ),
    "GOV-BETA-04": (
        f"{PACKAGE_ROOT}/docs/GOV-BETA-04-SERVER-OWNED-MANIFEST-CHAIN-2026-07-29.md",
        f"{PACKAGE_ROOT}/tests/test_gov_beta_04_server_owned_manifest_chain.py",
    ),
    "ARCH-BETA-05": (
        f"{PACKAGE_ROOT}/docs/ARCH-BETA-05-CANONICAL-FINANCE-ADMISSION-REPAIR-2026-07-29.md",
        f"{PACKAGE_ROOT}/tests/test_arch_beta_05_canonical_finance_admission.py",
    ),
    "TEST-BETA-06": (
        f"{PACKAGE_ROOT}/docs/TEST-BETA-06-CROSS-PLATFORM-DETERMINISM-2026-07-29.md",
        f"{PACKAGE_ROOT}/tests/test_beta_06_cross_platform_determinism.py",
    ),
    "REL-BETA-07": (
        f"{PACKAGE_ROOT}/docs/REL-BETA-07-EVIDENCE-BACKED-RELEASE-GATE-2026-07-29.md",
        f"{PACKAGE_ROOT}/tests/test_rel_beta_07_evidence_release_gate.py",
        f"{PACKAGE_ROOT}/tools/rel_beta_07_evidence.py",
    ),
    "DEPLOY-BETA-08": (
        f"{PACKAGE_ROOT}/docs/DEPLOY-BETA-08-PRIVATE-DEPLOYMENT-SMOKE-2026-07-29.md",
        f"{PACKAGE_ROOT}/tests/test_deploy_beta_08_private_deployment_smoke.py",
        f"{PACKAGE_ROOT}/tools/deploy_beta_08_private_smoke.py",
    ),
}

_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_IMAGE_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def _canonical_hash_without(value: Mapping[str, Any], key: str) -> str:
    material = dict(value)
    material.pop(key, None)
    return canonical_sha256(material)


def review_report_hash(report: Mapping[str, Any]) -> str:
    return _canonical_hash_without(report, "review_hash")


def _gate_report_hash(report: Mapping[str, Any]) -> str:
    return _canonical_hash_without(report, "report_hash")


def _check(
    check_id: str,
    passed: bool,
    *,
    rejection: bool,
    evidence: Mapping[str, Any] | None = None,
    message: str = "",
) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "passed": bool(passed),
        "rejection": bool(rejection),
        "evidence": dict(evidence or {}),
        "message": message,
    }


def _unique_string_set(value: Any) -> tuple[set[str], bool]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        return set(), False
    return set(value), len(set(value)) == len(value)


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


def git_is_ancestor(repository_root: Path, ancestor: str, descendant: str) -> bool:
    if not (_SHA_RE.fullmatch(ancestor) and _SHA_RE.fullmatch(descendant)):
        return False
    completed = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant],
        cwd=repository_root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return completed.returncode == 0


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def evaluate_governed_freeze_review(
    gate_report: Mapping[str, Any],
    freeze_marker: Mapping[str, Any],
    *,
    expected_commit: str,
    repository_root: Path,
    ancestor_resolver: Callable[[Path, str, str], bool] = git_is_ancestor,
    path_exists: Callable[[Path], bool] | None = None,
) -> dict[str, Any]:
    path_exists = path_exists or Path.is_file
    checks: list[dict[str, Any]] = []

    supplied_gate_hash = str(gate_report.get("report_hash") or "")
    computed_gate_hash = _gate_report_hash(gate_report)
    gate_hash_ok = bool(_SHA256_RE.fullmatch(supplied_gate_hash)) and supplied_gate_hash == computed_gate_hash
    gate_records, gate_check_ids_unique = _gate_checks(gate_report)
    gate_contract_ok = bool(
        gate_report.get("contract_id") == GATE_CONTRACT_ID
        and gate_hash_ok
        and gate_check_ids_unique
    )
    checks.append(
        _check(
            "release_gate_contract_integrity",
            gate_contract_ok,
            rejection=True,
            evidence={
                "contract_id": gate_report.get("contract_id"),
                "report_hash": supplied_gate_hash or None,
                "computed_hash": computed_gate_hash,
                "unique_check_ids": gate_check_ids_unique,
            },
            message="The REL-BETA-07 report contract, hash, and check identifiers must be valid.",
        )
    )

    commit_bound = bool(
        _SHA_RE.fullmatch(expected_commit)
        and gate_report.get("release_commit") == expected_commit
    )
    checks.append(
        _check(
            "release_commit_bound",
            commit_bound,
            rejection=True,
            evidence={
                "expected_commit": expected_commit,
                "gate_release_commit": gate_report.get("release_commit"),
            },
            message="Freeze eligibility evidence must be generated from the exact reviewed commit.",
        )
    )

    smoke_record = gate_records.get("private_deployment_smoke_passed") or {}
    freeze_record = gate_records.get("emergency_release_freeze_cleared") or {}
    other_critical_failures = [
        str(item.get("check_id"))
        for item in gate_records.values()
        if item.get("critical") is True
        and item.get("check_id") != "emergency_release_freeze_cleared"
        and item.get("passed") is not True
    ]
    pre_unfreeze_gate_ok = bool(
        gate_contract_ok
        and commit_bound
        and gate_report.get("decision") == "NO_GO"
        and gate_report.get("release_allowed") is False
        and gate_report.get("public_beta_allowed") is False
        and gate_report.get("technical_limited_beta_allowed") is False
        and gate_report.get("code_evidence_ready") is True
        and gate_report.get("critical_failures") == ["emergency_release_freeze_cleared"]
        and smoke_record.get("passed") is True
        and freeze_record.get("passed") is False
        and not other_critical_failures
        and gate_report.get("manual_readiness_assertions_accepted") is False
        and gate_report.get("secrets_exposed") is False
        and gate_report.get("finance_mutated") is False
        and gate_report.get("snapshot_mutated") is False
        and gate_report.get("external_fetch_changed") is False
        and bool(_IMAGE_DIGEST_RE.fullmatch(str(gate_report.get("deployment_image_digest") or "")))
    )
    checks.append(
        _check(
            "pre_unfreeze_release_gate_state",
            pre_unfreeze_gate_ok,
            rejection=False,
            evidence={
                "decision": gate_report.get("decision"),
                "critical_failures": gate_report.get("critical_failures"),
                "code_evidence_ready": gate_report.get("code_evidence_ready"),
                "private_deployment_smoke_passed": smoke_record.get("passed"),
                "deployment_image_digest": gate_report.get("deployment_image_digest"),
                "other_critical_failures": other_critical_failures,
            },
            message="The only remaining critical release blocker must be the active emergency freeze itself.",
        )
    )

    scope, scope_unique = _unique_string_set(freeze_marker.get("scope"))
    reasons, reasons_unique = _unique_string_set(freeze_marker.get("reason_codes"))
    boundaries, boundaries_unique = _unique_string_set(freeze_marker.get("protected_boundaries"))
    requirements, requirements_unique = _unique_string_set(freeze_marker.get("unfreeze_requires"))
    marker_contract_ok = bool(
        freeze_marker.get("schema") == FREEZE_SCHEMA
        and freeze_marker.get("status") == "ACTIVE"
        and freeze_marker.get("decision") == "NO_GO"
        and freeze_marker.get("release_gate_allowed") is False
        and scope_unique
        and scope == EXPECTED_SCOPE
        and reasons_unique
        and reasons == EXPECTED_REASON_CODES
        and boundaries_unique
        and boundaries == EXPECTED_PROTECTED_BOUNDARIES
        and requirements_unique
        and requirements == EXPECTED_UNFREEZE_REQUIREMENTS
        and _SHA_RE.fullmatch(str(freeze_marker.get("baseline_commit") or ""))
    )
    marker_canonical_sha256 = hashlib.sha256(
        json.dumps(
            dict(freeze_marker),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()
    checks.append(
        _check(
            "freeze_marker_contract_integrity",
            marker_contract_ok,
            rejection=True,
            evidence={
                "schema": freeze_marker.get("schema"),
                "status": freeze_marker.get("status"),
                "decision": freeze_marker.get("decision"),
                "release_gate_allowed": freeze_marker.get("release_gate_allowed"),
                "baseline_commit": freeze_marker.get("baseline_commit"),
                "marker_canonical_sha256": marker_canonical_sha256,
            },
            message="The active freeze marker must remain canonical and unmodified during review.",
        )
    )

    baseline = str(freeze_marker.get("baseline_commit") or "")
    baseline_is_ancestor = bool(
        marker_contract_ok
        and ancestor_resolver(repository_root, baseline, expected_commit)
    )
    checks.append(
        _check(
            "freeze_baseline_lineage",
            baseline_is_ancestor,
            rejection=True,
            evidence={"baseline_commit": baseline, "review_commit": expected_commit},
            message="The reviewed commit must descend from the emergency freeze baseline.",
        )
    )

    package_lineage: dict[str, dict[str, Any]] = {}
    package_history_ok = True
    for package_id, merge_commit in REQUIRED_PACKAGE_COMMITS.items():
        present = ancestor_resolver(repository_root, merge_commit, expected_commit)
        package_lineage[package_id] = {"merge_commit": merge_commit, "ancestor": present}
        package_history_ok = package_history_ok and present
    checks.append(
        _check(
            "required_package_history",
            package_history_ok,
            rejection=True,
            evidence={"packages": package_lineage},
            message="Every governed remediation and evidence package merge must be in the reviewed commit history.",
        )
    )

    package_paths: dict[str, dict[str, bool]] = {}
    package_paths_ok = True
    for package_id, paths in REQUIRED_EVIDENCE_PATHS.items():
        resolved: dict[str, bool] = {}
        for relative in paths:
            present = path_exists(repository_root / relative)
            resolved[relative] = present
            package_paths_ok = package_paths_ok and present
        package_paths[package_id] = resolved
    checks.append(
        _check(
            "required_package_evidence_paths",
            package_paths_ok,
            rejection=False,
            evidence={"packages": package_paths},
            message="Required package documents, executable tests, and evidence collectors must exist in the reviewed tree.",
        )
    )

    rejection_failures = [
        check["check_id"] for check in checks if check["rejection"] and not check["passed"]
    ]
    readiness_failures = [
        check["check_id"] for check in checks if not check["rejection"] and not check["passed"]
    ]
    if rejection_failures:
        decision = REJECT_UNFREEZE
    elif readiness_failures:
        decision = KEEP_FROZEN
    else:
        decision = ELIGIBLE

    report: dict[str, Any] = {
        "schema": REVIEW_SCHEMA,
        "package_id": PACKAGE_ID,
        "decision": decision,
        "review_commit": expected_commit,
        "freeze_status": freeze_marker.get("status"),
        "freeze_baseline_commit": freeze_marker.get("baseline_commit"),
        "freeze_marker_canonical_sha256": marker_canonical_sha256,
        "gate_report_hash": supplied_gate_hash or None,
        "deployment_image_digest": gate_report.get("deployment_image_digest"),
        "rejection_failures": rejection_failures,
        "readiness_failures": readiness_failures,
        "checks": checks,
        "unfreeze_authorized": False,
        "marker_mutation_permitted": False,
        "release_allowed": False,
        "public_beta_allowed": False,
        "required_next_package": "GOV-REL-10-CONTROLLED-UNFREEZE-EXECUTION",
        "finance_mutated": False,
        "snapshot_mutated": False,
        "aas_runtime_freeze_mutated": False,
    }
    report["review_hash"] = review_report_hash(report)
    return report


def write_report(path: Path, report: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dict(report), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate governed eligibility to clear the ASIE emergency release freeze.")
    parser.add_argument("--gate-report", type=Path, required=True)
    parser.add_argument("--freeze-marker", type=Path, required=True)
    parser.add_argument("--expected-commit", required=True)
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--require-eligible", action="store_true")
    args = parser.parse_args(argv)

    report = evaluate_governed_freeze_review(
        _load_json(args.gate_report),
        _load_json(args.freeze_marker),
        expected_commit=str(args.expected_commit or "").strip(),
        repository_root=args.repository_root.resolve(),
    )
    write_report(args.output, report)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))

    if args.require_eligible and report["decision"] != ELIGIBLE:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
