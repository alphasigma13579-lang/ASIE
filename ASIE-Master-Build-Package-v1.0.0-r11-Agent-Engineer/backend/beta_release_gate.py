from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

GATE_CONTRACT_ID = "beta.release.gate.v2"
EVIDENCE_BUNDLE_SCHEMA = "asie.release.evidence.bundle.v2"
DETERMINISM_EVIDENCE_SCHEMA = "asie.cross_platform.determinism.evidence.v1"
DEPLOYMENT_EVIDENCE_SCHEMA = "asie.private.deployment.smoke.v1"
FREEZE_SCHEMA = "asie.release.freeze.v1"

REQUIRED_CODE_CHECKS = (
    "frontend_dependencies",
    "frontend_build",
    "backend_compile",
    "full_python_suite",
    "dib_product_and_dataset_runtime",
    "sec_beta_01_identity_lockdown",
    "stab_beta_02_thread_safe_persistence",
    "sec_beta_03_tenant_isolation",
    "gov_beta_04_server_owned_lineage",
    "arch_beta_05_canonical_finance_admission",
    "snapshot_lineage",
    "report_exports",
    "aas_freeze_git_blobs",
)

REQUIRED_SMOKE_CHECKS = (
    "service_health",
    "auth_boundary",
    "tenant_isolation",
    "canonical_project_run",
    "snapshot_readback",
)

DEGRADABLE_CAPABILITIES = (
    "provider_connectivity",
    "external_fetch",
    "vision2030_sync",
    "live_intelligence",
)

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_IMAGE_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


@dataclass(frozen=True)
class GateCheck:
    check_id: str
    passed: bool
    critical: bool
    evidence: Mapping[str, Any]
    message: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "check_id": self.check_id,
            "passed": self.passed,
            "critical": self.critical,
            "evidence": deepcopy(dict(self.evidence)),
            "message": self.message,
        }


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
        default=str,
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def evidence_bundle_hash(bundle: Mapping[str, Any]) -> str:
    material = dict(bundle)
    material.pop("bundle_hash", None)
    return canonical_sha256(material)


def deployment_evidence_hash(evidence: Mapping[str, Any]) -> str:
    material = dict(evidence)
    material.pop("evidence_hash", None)
    return canonical_sha256(material)


def _passed(value: Any) -> bool:
    if value is True:
        return True
    return str(value or "").strip().lower() in {"passed", "ready", "success", "enabled", "true"}


def _valid_sha256(value: Any) -> bool:
    return bool(_SHA256_RE.fullmatch(str(value or "").strip().lower()))


def _gate_check(
    check_id: str,
    passed: bool,
    *,
    critical: bool,
    evidence: Mapping[str, Any] | None = None,
    message: str = "",
) -> GateCheck:
    return GateCheck(
        check_id=check_id,
        passed=bool(passed),
        critical=critical,
        evidence=dict(evidence or {}),
        message=message,
    )


def _bundle_checks(bundle: Mapping[str, Any]) -> tuple[dict[str, Mapping[str, Any]], bool]:
    raw_checks = bundle.get("checks")
    if not isinstance(raw_checks, list):
        return {}, False
    checks: dict[str, Mapping[str, Any]] = {}
    unique = True
    for raw in raw_checks:
        if not isinstance(raw, Mapping):
            unique = False
            continue
        check_id = str(raw.get("check_id") or "")
        if not check_id or check_id in checks:
            unique = False
            continue
        checks[check_id] = raw
    return checks, unique


def _validate_code_evidence(bundle: Mapping[str, Any], expected_commit: str) -> list[GateCheck]:
    checks: list[GateCheck] = []
    schema_ok = bundle.get("schema") == EVIDENCE_BUNDLE_SCHEMA
    commit_ok = bundle.get("commit_sha") == expected_commit
    supplied_hash = str(bundle.get("bundle_hash") or "")
    hash_ok = _valid_sha256(supplied_hash) and supplied_hash == evidence_bundle_hash(bundle)
    records, unique = _bundle_checks(bundle)

    checks.append(
        _gate_check(
            "release_commit_bound",
            commit_ok,
            critical=True,
            evidence={"expected_commit": expected_commit, "evidence_commit": bundle.get("commit_sha")},
            message="Evidence must be generated from the exact release commit.",
        )
    )
    checks.append(
        _gate_check(
            "evidence_bundle_integrity",
            schema_ok and hash_ok and unique,
            critical=True,
            evidence={
                "schema": bundle.get("schema"),
                "bundle_hash": supplied_hash,
                "computed_hash": evidence_bundle_hash(bundle),
                "unique_check_ids": unique,
            },
            message="The code evidence bundle schema, hash, and check identifiers must be valid.",
        )
    )

    bundle_meta_ok = schema_ok and commit_ok and hash_ok and unique
    for check_id in REQUIRED_CODE_CHECKS:
        record = records.get(check_id)
        record_ok = bool(
            bundle_meta_ok
            and record
            and record.get("commit_sha") == expected_commit
            and _passed(record.get("status"))
            and record.get("exit_code") == 0
            and _valid_sha256(record.get("log_sha256"))
        )
        checks.append(
            _gate_check(
                check_id,
                record_ok,
                critical=True,
                evidence={
                    "commit_sha": record.get("commit_sha") if record else None,
                    "status": record.get("status") if record else "missing",
                    "exit_code": record.get("exit_code") if record else None,
                    "log_sha256": record.get("log_sha256") if record else None,
                    "claims": list(record.get("claims") or []) if record else [],
                },
                message=f"Required executable evidence is missing or failed: {check_id}",
            )
        )
    return checks


def _validate_determinism(evidence: Mapping[str, Any], expected_commit: str) -> GateCheck:
    passed = bool(
        evidence.get("schema") == DETERMINISM_EVIDENCE_SCHEMA
        and evidence.get("commit_sha") == expected_commit
        and _passed(evidence.get("status"))
        and int(evidence.get("vectors_compared") or 0) >= 4
        and _valid_sha256(evidence.get("vector_hash"))
        and _valid_sha256(evidence.get("comparison_sha256"))
    )
    return _gate_check(
        "test_beta_06_cross_platform_determinism",
        passed,
        critical=True,
        evidence={
            "commit_sha": evidence.get("commit_sha"),
            "status": evidence.get("status"),
            "vectors_compared": evidence.get("vectors_compared"),
            "vector_hash": evidence.get("vector_hash"),
            "comparison_sha256": evidence.get("comparison_sha256"),
        },
        message="Four byte-identical Windows/Linux evidence vectors are required for the release commit.",
    )


def _validate_deployment_evidence(
    evidence: Mapping[str, Any] | None,
    expected_commit: str,
) -> tuple[GateCheck, list[GateCheck]]:
    payload = dict(evidence or {})
    supplied_hash = str(payload.get("evidence_hash") or "")
    hash_ok = bool(payload) and _valid_sha256(supplied_hash) and supplied_hash == deployment_evidence_hash(payload)
    raw_checks = payload.get("checks") if isinstance(payload.get("checks"), Mapping) else {}
    required_checks_ok = all(_passed(raw_checks.get(check_id)) for check_id in REQUIRED_SMOKE_CHECKS)
    smoke_ok = bool(
        payload.get("schema") == DEPLOYMENT_EVIDENCE_SCHEMA
        and payload.get("commit_sha") == expected_commit
        and _passed(payload.get("status"))
        and _IMAGE_DIGEST_RE.fullmatch(str(payload.get("image_digest") or ""))
        and hash_ok
        and required_checks_ok
    )
    smoke_check = _gate_check(
        "private_deployment_smoke_passed",
        smoke_ok,
        critical=True,
        evidence={
            "present": bool(payload),
            "schema": payload.get("schema"),
            "commit_sha": payload.get("commit_sha"),
            "image_digest": payload.get("image_digest"),
            "evidence_hash": supplied_hash or None,
            "required_checks": {check_id: raw_checks.get(check_id) for check_id in REQUIRED_SMOKE_CHECKS},
        },
        message="A hashed Private Deployment Smoke record for the exact commit and image digest is required.",
    )

    capabilities = payload.get("capabilities") if isinstance(payload.get("capabilities"), Mapping) else {}
    capability_checks = [
        _gate_check(
            capability,
            smoke_ok and _passed(capabilities.get(capability)),
            critical=False,
            evidence={"status": capabilities.get(capability, "unproven"), "smoke_evidence_present": bool(payload)},
            message=f"Capability is unavailable or unproven: {capability}",
        )
        for capability in DEGRADABLE_CAPABILITIES
    ]
    return smoke_check, capability_checks


def _validate_freeze(marker: Mapping[str, Any]) -> GateCheck:
    passed = bool(
        marker.get("schema") == FREEZE_SCHEMA
        and marker.get("status") == "CLEARED"
        and marker.get("release_gate_allowed") is True
    )
    return _gate_check(
        "emergency_release_freeze_cleared",
        passed,
        critical=True,
        evidence={
            "schema": marker.get("schema"),
            "status": marker.get("status"),
            "decision": marker.get("decision"),
            "release_gate_allowed": marker.get("release_gate_allowed"),
            "baseline_commit": marker.get("baseline_commit"),
        },
        message="The emergency marker must be explicitly CLEARED before any release decision can allow deployment.",
    )


def evaluate_beta_release(
    evidence_bundle: Mapping[str, Any],
    determinism_evidence: Mapping[str, Any],
    freeze_marker: Mapping[str, Any],
    *,
    expected_commit: str,
    deployment_evidence: Mapping[str, Any] | None = None,
    workflow_run_id: str | None = None,
) -> dict[str, Any]:
    """Evaluate executable, commit-bound evidence without mutating governed domains."""

    checks = _validate_code_evidence(evidence_bundle, expected_commit)
    checks.append(_validate_determinism(determinism_evidence, expected_commit))
    smoke_check, capability_checks = _validate_deployment_evidence(deployment_evidence, expected_commit)
    checks.append(smoke_check)
    checks.append(_validate_freeze(freeze_marker))
    checks.extend(capability_checks)

    critical_failures = [check.check_id for check in checks if check.critical and not check.passed]
    degraded = [check.check_id for check in checks if not check.critical and not check.passed]
    code_check_ids = {
        "release_commit_bound",
        "evidence_bundle_integrity",
        *REQUIRED_CODE_CHECKS,
        "test_beta_06_cross_platform_determinism",
    }
    code_evidence_ready = all(check.passed for check in checks if check.check_id in code_check_ids)

    if critical_failures:
        decision = "NO_GO"
    elif degraded:
        decision = "CONDITIONAL_GO"
    else:
        decision = "GO"

    report: dict[str, Any] = {
        "contract_id": GATE_CONTRACT_ID,
        "decision": decision,
        "release_commit": expected_commit,
        "workflow_run_id": workflow_run_id,
        "release_allowed": decision in {"GO", "CONDITIONAL_GO"},
        "public_beta_allowed": decision == "GO",
        "technical_limited_beta_allowed": decision in {"GO", "CONDITIONAL_GO"},
        "code_evidence_ready": code_evidence_ready,
        "ready_for_private_deployment_smoke": code_evidence_ready,
        "critical_failures": critical_failures,
        "degraded_capabilities": degraded,
        "checks": [check.as_dict() for check in checks],
        "evidence_bundle_hash": evidence_bundle.get("bundle_hash"),
        "determinism_vector_hash": determinism_evidence.get("vector_hash"),
        "deployment_image_digest": (deployment_evidence or {}).get("image_digest"),
        "manual_readiness_assertions_accepted": False,
        "secrets_exposed": False,
        "finance_mutated": False,
        "snapshot_mutated": False,
        "external_fetch_changed": False,
    }
    report["report_hash"] = canonical_sha256(report)
    return report


def assert_releaseable(report: Mapping[str, Any], *, release_scope: str = "public_beta") -> None:
    if release_scope == "public_beta":
        accepted = {"GO"}
    elif release_scope == "technical_limited_beta":
        accepted = {"GO", "CONDITIONAL_GO"}
    else:
        raise ValueError(f"unsupported_release_scope:{release_scope}")
    if report.get("decision") not in accepted:
        failures = ",".join(report.get("critical_failures") or report.get("degraded_capabilities") or [])
        raise RuntimeError(f"beta_release_blocked:{report.get('decision')}:{failures}")


def _load_json(path: Path | None) -> dict[str, Any]:
    if path is None or not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _determinism_evidence(path: Path, expected_commit: str) -> dict[str, Any]:
    raw = path.read_bytes() if path.is_file() else b""
    try:
        comparison = json.loads(raw.decode("utf-8")) if raw else {}
    except (UnicodeDecodeError, json.JSONDecodeError):
        comparison = {}
    if not isinstance(comparison, dict):
        comparison = {}
    return {
        "schema": DETERMINISM_EVIDENCE_SCHEMA,
        "commit_sha": expected_commit,
        "status": comparison.get("status", "missing"),
        "vectors_compared": comparison.get("vectors_compared", 0),
        "vector_hash": comparison.get("vector_hash"),
        "comparison_sha256": hashlib.sha256(raw).hexdigest() if raw else None,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate the REL-BETA-07 commit-bound release evidence gate.")
    parser.add_argument("--evidence-bundle", type=Path, required=True)
    parser.add_argument("--determinism-comparison", type=Path, required=True)
    parser.add_argument("--freeze-marker", type=Path, required=True)
    parser.add_argument("--deployment-evidence", type=Path)
    parser.add_argument("--expected-commit", default=os.environ.get("GITHUB_SHA", ""), required=False)
    parser.add_argument("--workflow-run-id", default=os.environ.get("GITHUB_RUN_ID"))
    parser.add_argument("--release-scope", choices=("public_beta", "technical_limited_beta"), default="public_beta")
    parser.add_argument("--mode", choices=("audit", "enforce"), default="audit")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    expected_commit = str(args.expected_commit or "").strip()
    evidence_bundle = _load_json(args.evidence_bundle)
    determinism = _determinism_evidence(args.determinism_comparison, expected_commit)
    freeze_marker = _load_json(args.freeze_marker)
    deployment = _load_json(args.deployment_evidence) if args.deployment_evidence else None
    report = evaluate_beta_release(
        evidence_bundle,
        determinism,
        freeze_marker,
        expected_commit=expected_commit,
        deployment_evidence=deployment,
        workflow_run_id=args.workflow_run_id,
    )

    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8", newline="\n")
    print(rendered, end="")

    if args.mode == "audit":
        return 0
    try:
        assert_releaseable(report, release_scope=args.release_scope)
    except RuntimeError:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
