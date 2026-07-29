from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PACKAGE_ROOT.parent
PACKAGE_PREFIX = PACKAGE_ROOT.name
BUNDLE_SCHEMA = "asie.release.evidence.bundle.v2"
FREEZE_MANIFEST_PATH = "docs/ASIE-AAS-Runtime-Freeze-Manifest-v1.0.json"


@dataclass(frozen=True)
class CheckSpec:
    check_id: str
    command: tuple[str, ...]
    claims: tuple[str, ...]
    timeout_seconds: int = 1200


PYTHON = sys.executable
CHECK_SPECS: tuple[CheckSpec, ...] = (
    CheckSpec(
        "frontend_dependencies",
        ("pnpm", "install", "--frozen-lockfile"),
        ("frontend dependencies resolve from the committed lockfile",),
    ),
    CheckSpec(
        "frontend_build",
        ("pnpm", "build"),
        ("the production frontend bundle compiles",),
    ),
    CheckSpec(
        "backend_compile",
        (PYTHON, "-m", "compileall", "-q", "backend"),
        ("all backend Python modules compile",),
    ),
    CheckSpec(
        "full_python_suite",
        (PYTHON, "-m", "unittest", "discover", "-s", "tests"),
        ("the complete Python regression suite passes on the release commit",),
        timeout_seconds=1800,
    ),
    CheckSpec(
        "dib_product_and_dataset_runtime",
        (PYTHON, "-m", "unittest", "discover", "-s", "tests", "-p", "test_dib_complete_runtime.py", "-v"),
        (
            "Product AI Interview executes through governed DIB objects",
            "CSV, XLSX, and PDF-text intake map into DIB",
            "unknown required inputs block manifest validation",
        ),
    ),
    CheckSpec(
        "sec_beta_01_identity_lockdown",
        (PYTHON, "-m", "unittest", "discover", "-s", "tests", "-p", "test_sec_beta_01_bootstrap_lockdown.py", "-v"),
        (
            "production bootstrap takeover is blocked",
            "zero-user anonymous project creation is blocked",
            "legacy local principal requires explicit development opt-in",
        ),
    ),
    CheckSpec(
        "stab_beta_02_thread_safe_persistence",
        (
            PYTHON,
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests",
            "-p",
            "test_stab_beta_02_transaction_safe_dib_persistence.py",
            "-v",
        ),
        (
            "ThreadingHTTPServer DIB requests do not share an unsafe SQLite connection",
            "concurrent writes remain atomic",
        ),
    ),
    CheckSpec(
        "sec_beta_03_tenant_isolation",
        (PYTHON, "-m", "unittest", "discover", "-s", "tests", "-p", "test_sec_beta_03_dib_tenant_boundary.py", "-v"),
        (
            "cross-tenant session reads are denied",
            "cross-tenant DIB writes and event reads are denied",
            "unproven legacy ownership is quarantined",
        ),
    ),
    CheckSpec(
        "gov_beta_04_server_owned_lineage",
        (
            PYTHON,
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests",
            "-p",
            "test_gov_beta_04_server_owned_manifest_chain.py",
            "-v",
        ),
        (
            "client-supplied Manifest and Gate objects are rejected",
            "direct forged persistence is rejected",
            "Blueprint to Manifest to Gate hashes are server-owned",
        ),
    ),
    CheckSpec(
        "arch_beta_05_canonical_finance_admission",
        (
            PYTHON,
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests",
            "-p",
            "test_arch_beta_05_canonical_finance_admission.py",
            "-v",
        ),
        (
            "DIB Finance admission invokes ProjectRunWorkflow",
            "direct DIB to Finance execution is removed",
            "idempotent replay returns the original Run and Snapshot",
        ),
    ),
    CheckSpec(
        "snapshot_lineage",
        (PYTHON, "-m", "unittest", "discover", "-s", "tests", "-p", "test_dib_snapshot_lineage.py", "-v"),
        ("Snapshot lineage remains bound to DIB source artifacts",),
    ),
    CheckSpec(
        "report_exports",
        (PYTHON, "-m", "unittest", "discover", "-s", "tests", "-p", "test_report_export_routes.py", "-v"),
        ("report export routes resolve the production renderer consistently",),
    ),
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
        default=str,
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _scrubbed_environment() -> dict[str, str]:
    environment = dict(os.environ)
    for name in tuple(environment):
        upper = name.upper()
        if any(token in upper for token in ("TOKEN", "SECRET", "PASSWORD")) or upper.endswith("_KEY"):
            environment.pop(name, None)
    environment.update(
        {
            "ASIE_ENV": "test",
            "ASIE_ALLOW_LOCAL_BOOTSTRAP": "false",
            "CI": "true",
            "PYTHONHASHSEED": "0",
            "PYTHONUTF8": "1",
            "TZ": "UTC",
        }
    )
    return environment


def _git(*args: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ("git", "-C", str(REPOSITORY_ROOT), *args),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=check,
        timeout=120,
    )


def current_commit() -> str:
    return _git("rev-parse", "HEAD").stdout.decode("ascii").strip()


def _write_log(log_path: Path, stdout: bytes, stderr: bytes) -> str:
    payload = stdout + b"\n--- STDERR ---\n" + stderr
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_bytes(payload)
    return sha256_bytes(payload)


def run_check(spec: CheckSpec, *, commit_sha: str, log_directory: Path) -> dict[str, Any]:
    started_at = now_iso()
    started = time.monotonic()
    try:
        result = subprocess.run(
            spec.command,
            cwd=PACKAGE_ROOT,
            env=_scrubbed_environment(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=spec.timeout_seconds,
            check=False,
        )
        exit_code = int(result.returncode)
        stdout = result.stdout
        stderr = result.stderr
    except subprocess.TimeoutExpired as exc:
        exit_code = 124
        stdout = exc.stdout or b""
        stderr = (exc.stderr or b"") + f"\nTIMEOUT after {spec.timeout_seconds} seconds".encode("utf-8")
    duration_ms = int((time.monotonic() - started) * 1000)
    log_path = log_directory / f"{spec.check_id}.log"
    log_sha256 = _write_log(log_path, stdout, stderr)
    return {
        "check_id": spec.check_id,
        "critical": True,
        "status": "passed" if exit_code == 0 else "failed",
        "commit_sha": commit_sha,
        "command": list(spec.command),
        "exit_code": exit_code,
        "duration_ms": duration_ms,
        "started_at": started_at,
        "finished_at": now_iso(),
        "log_path": log_path.relative_to(PACKAGE_ROOT).as_posix(),
        "log_sha256": log_sha256,
        "claims": list(spec.claims),
    }


def verify_frozen_git_blobs(*, commit_sha: str, log_directory: Path) -> dict[str, Any]:
    started_at = now_iso()
    manifest_ref = f"{commit_sha}:{PACKAGE_PREFIX}/{FREEZE_MANIFEST_PATH}"
    manifest_raw = _git("show", manifest_ref).stdout
    manifest = json.loads(manifest_raw.decode("utf-8"))
    rows: list[dict[str, Any]] = []
    passed = True
    for item in manifest.get("frozen_files", []):
        relative_path = str(item.get("path") or "")
        expected = str(item.get("sha256") or "")
        blob_ref = f"{commit_sha}:{PACKAGE_PREFIX}/{relative_path}"
        try:
            raw = _git("show", blob_ref).stdout
            actual = sha256_bytes(raw)
            item_passed = bool(relative_path and actual == expected)
            error = ""
        except subprocess.CalledProcessError as exc:
            actual = ""
            item_passed = False
            error = exc.stderr.decode("utf-8", errors="replace")
        passed = passed and item_passed
        rows.append(
            {
                "path": relative_path,
                "expected_sha256": expected,
                "actual_sha256": actual,
                "passed": item_passed,
                "error": error,
            }
        )
    log_payload = {
        "manifest_ref": manifest_ref,
        "frozen_file_count": len(rows),
        "rows": rows,
    }
    log_path = log_directory / "aas_freeze_git_blobs.log"
    rendered = (json.dumps(log_payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_bytes(rendered)
    return {
        "check_id": "aas_freeze_git_blobs",
        "critical": True,
        "status": "passed" if passed and bool(rows) else "failed",
        "commit_sha": commit_sha,
        "command": ["git", "show", f"{commit_sha}:{PACKAGE_PREFIX}/<frozen-path>"],
        "exit_code": 0 if passed and bool(rows) else 1,
        "duration_ms": 0,
        "started_at": started_at,
        "finished_at": now_iso(),
        "log_path": log_path.relative_to(PACKAGE_ROOT).as_posix(),
        "log_sha256": sha256_bytes(rendered),
        "claims": [
            "all AAS Runtime Freeze files match the manifest using Git object bytes",
            "worktree line-ending conversion cannot satisfy or break this check",
        ],
    }


def build_evidence_bundle(
    checks: Iterable[dict[str, Any]],
    *,
    commit_sha: str,
    expected_commit: str,
    generated_at: str | None = None,
) -> dict[str, Any]:
    bundle: dict[str, Any] = {
        "schema": BUNDLE_SCHEMA,
        "package_id": "REL-BETA-07",
        "commit_sha": commit_sha,
        "expected_commit": expected_commit,
        "generated_at": generated_at or now_iso(),
        "generator": "tools/rel_beta_07_evidence.py",
        "manual_readiness_assertions_accepted": False,
        "checks": list(checks),
    }
    bundle["bundle_hash"] = hashlib.sha256(canonical_json_bytes(bundle)).hexdigest()
    return bundle


def collect(*, expected_commit: str, output_path: Path, log_directory: Path) -> dict[str, Any]:
    commit_sha = current_commit()
    records = [run_check(spec, commit_sha=commit_sha, log_directory=log_directory) for spec in CHECK_SPECS]
    records.append(verify_frozen_git_blobs(commit_sha=commit_sha, log_directory=log_directory))
    bundle = build_evidence_bundle(records, commit_sha=commit_sha, expected_commit=expected_commit)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(bundle, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(
        json.dumps(
            {
                "status": "collected",
                "commit_sha": commit_sha,
                "expected_commit": expected_commit,
                "checks": len(records),
                "failed": [record["check_id"] for record in records if record["status"] != "passed"],
                "bundle_hash": bundle["bundle_hash"],
                "output": output_path.as_posix(),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return bundle


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Collect executable REL-BETA-07 evidence for the checked-out commit.")
    parser.add_argument("collect", nargs="?")
    parser.add_argument("--expected-commit", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--log-directory", type=Path, required=True)
    args = parser.parse_args(argv)
    collect(
        expected_commit=str(args.expected_commit).strip(),
        output_path=args.output,
        log_directory=args.log_directory,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
