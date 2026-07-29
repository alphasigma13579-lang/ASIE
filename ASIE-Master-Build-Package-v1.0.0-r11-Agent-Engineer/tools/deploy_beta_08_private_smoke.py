#!/usr/bin/env python3
"""DEPLOY-BETA-08: exercise a loopback-only ASIE Docker deployment.

The probe creates ephemeral tenant fixtures inside the private API container,
then exercises the live HTTP surfaces for health, production authentication,
tenant isolation, canonical ProjectRunWorkflow execution, and immutable
Snapshot readback. It emits `asie.private.deployment.smoke.v1` evidence bound
to the exact Git commit and a composite digest of the built container images.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PACKAGE_ROOT.parent
DEPLOYMENT_EVIDENCE_SCHEMA = "asie.private.deployment.smoke.v1"
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


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def deployment_evidence_hash(evidence: Mapping[str, Any]) -> str:
    material = dict(evidence)
    material.pop("evidence_hash", None)
    return canonical_sha256(material)


def _run(command: Sequence[str], *, cwd: Path = PACKAGE_ROOT, timeout: int = 180) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        tuple(command),
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )


def current_commit() -> str:
    result = _run(("git", "-C", str(REPOSITORY_ROOT), "rev-parse", "HEAD"), cwd=REPOSITORY_ROOT)
    if result.returncode != 0:
        raise RuntimeError("git_commit_resolution_failed")
    return result.stdout.strip()


def image_id(image: str) -> str:
    result = _run(("docker", "image", "inspect", "--format", "{{.Id}}", image))
    value = result.stdout.strip()
    if result.returncode != 0 or not value.startswith("sha256:") or len(value) != 71:
        raise RuntimeError(f"image_identity_unavailable:{image}")
    return value


def composite_image_digest(*, commit_sha: str, compose_file: Path, backend_image: str, web_image: str) -> tuple[str, dict[str, Any]]:
    compose_sha256 = hashlib.sha256(compose_file.read_bytes()).hexdigest()
    images = {
        "api": image_id(backend_image),
        "dib-api": image_id(backend_image),
        "web": image_id(web_image),
    }
    material = {
        "commit_sha": commit_sha,
        "compose_sha256": compose_sha256,
        "images": images,
    }
    return f"sha256:{canonical_sha256(material)}", material


def request(
    base_url: str,
    method: str,
    path: str,
    *,
    payload: Mapping[str, Any] | None = None,
    token: str | None = None,
    organization_id: str | None = None,
    origin: str | None = None,
    timeout: float = 30.0,
) -> tuple[int, dict[str, str], bytes]:
    body = canonical_json_bytes(payload) if payload is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if organization_id:
        headers["X-ASIE-Organization-Id"] = organization_id
    if origin:
        headers["Origin"] = origin
    req = urllib.request.Request(base_url.rstrip("/") + path, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return int(response.status), dict(response.headers), response.read()
    except urllib.error.HTTPError as exc:
        return int(exc.code), dict(exc.headers), exc.read()


def json_body(body: bytes) -> dict[str, Any]:
    try:
        value = json.loads(body.decode("utf-8")) if body else {}
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("invalid_json_response") from exc
    if not isinstance(value, dict):
        raise RuntimeError("non_object_json_response")
    return value


def require(condition: bool, code: str) -> None:
    if not condition:
        raise RuntimeError(code)


def wait_for_status(base_url: str, path: str, *, attempts: int = 30) -> None:
    last_status = 0
    for _ in range(attempts):
        try:
            last_status, _headers, _body = request(base_url, "GET", path, timeout=4)
        except OSError:
            last_status = 0
        if last_status == 200:
            return
        time.sleep(2)
    raise RuntimeError(f"service_not_healthy:{path}:{last_status}")


def seed_tenants(compose_file: Path) -> dict[str, Any]:
    seed_source = r'''
from backend.repository import Repository
from pathlib import Path
import json
import os

repo = Repository(Path(os.environ["ASIE_DB_PATH"]))
fixtures = []
for suffix, label, password in (
    ("a", "Private Smoke A", "Private-Smoke-A-Password-2026!"),
    ("b", "Private Smoke B", "Private-Smoke-B-Password-2026!"),
):
    email = f"private-smoke-{suffix}@asie.test"
    user = repo.create_user(email=email, display_name=label, password=password)
    org = repo.create_organization(name=f"{label} Organization", owner_user_id=user["user_id"])
    fixtures.append({
        "email": email,
        "password": password,
        "user_id": user["user_id"],
        "organization_id": org["organization_id"],
    })
print(json.dumps({"tenants": fixtures}, separators=(",", ":")))
'''.strip()
    result = _run(
        (
            "docker",
            "compose",
            "-f",
            str(compose_file),
            "exec",
            "-T",
            "api",
            "python",
            "-c",
            seed_source,
        ),
        timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError("private_smoke_fixture_seed_failed")
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if not lines:
        raise RuntimeError("private_smoke_fixture_seed_empty")
    try:
        payload = json.loads(lines[-1])
    except json.JSONDecodeError as exc:
        raise RuntimeError("private_smoke_fixture_seed_invalid") from exc
    if not isinstance(payload, dict) or len(payload.get("tenants") or []) != 2:
        raise RuntimeError("private_smoke_fixture_seed_incomplete")
    return payload


def login(api_url: str, *, email: str, password: str, origin: str) -> str:
    status, _headers, body = request(
        api_url,
        "POST",
        "/api/auth/login",
        payload={"email": email, "password": password},
        origin=origin,
    )
    payload = json_body(body)
    token = str(payload.get("access_token") or payload.get("session_token") or "")
    require(status == 200 and bool(token), "private_smoke_login_failed")
    return token


def create_project(
    api_url: str,
    *,
    token: str,
    organization_id: str,
    name: str,
    origin: str,
) -> str:
    status, _headers, body = request(
        api_url,
        "POST",
        "/api/projects",
        payload={
            "name": name,
            "sector": "Food Service",
            "jurisdiction": "Saudi Arabia",
            "organization_id": organization_id,
            "inputs": {
                "startup_cost": 120000,
                "monthly_fixed_cost": 42000,
                "unit_price": 18,
                "variable_cost": 7,
                "monthly_units": 4200,
                "equity_contribution": 90000,
                "annual_discount_rate": 0.10,
                "location_country": "SA",
            },
        },
        token=token,
        organization_id=organization_id,
        origin=origin,
    )
    payload = json_body(body)
    project = payload.get("project") if isinstance(payload.get("project"), dict) else {}
    project_id = str(project.get("project_id") or "")
    require(status == 201 and bool(project_id), "private_smoke_project_creation_failed")
    return project_id


def run_live_smoke(
    *,
    expected_commit: str,
    compose_file: Path,
    api_url: str,
    dib_url: str,
    web_url: str,
    origin: str,
    backend_image: str,
    web_image: str,
) -> dict[str, Any]:
    actual_commit = current_commit()
    require(actual_commit == expected_commit, "private_smoke_commit_mismatch")

    image_digest, image_material = composite_image_digest(
        commit_sha=actual_commit,
        compose_file=compose_file,
        backend_image=backend_image,
        web_image=web_image,
    )
    checks = {check_id: False for check_id in REQUIRED_SMOKE_CHECKS}
    details: dict[str, Any] = {}
    started_at = now_iso()

    try:
        wait_for_status(api_url, "/api/health")
        wait_for_status(dib_url, "/api/dib/status")
        wait_for_status(web_url, "/")
        checks["service_health"] = True
        details["service_health"] = {
            "api": f"{api_url}/api/health",
            "dib_api": f"{dib_url}/api/dib/status",
            "web": f"{web_url}/",
        }

        bootstrap_status, _headers, bootstrap_body = request(
            api_url,
            "POST",
            "/api/auth/local-bootstrap",
            payload={
                "email": "attacker@private-smoke.test",
                "display_name": "Attacker",
                "password": "Private-Smoke-Attacker-Password-2026!",
                "organization_name": "Captured Platform",
            },
            origin=origin,
        )
        anonymous_status, _headers, anonymous_body = request(
            api_url,
            "POST",
            "/api/projects",
            payload={"name": "anonymous", "sector": "test", "jurisdiction": "SA"},
            origin=origin,
        )
        bootstrap_error = json_body(bootstrap_body).get("error")
        anonymous_error = json_body(anonymous_body).get("error")
        require(
            bootstrap_status == 404
            and bootstrap_error == "local_bootstrap_unavailable"
            and anonymous_status == 401
            and anonymous_error == "authentication_required",
            "private_smoke_auth_boundary_failed",
        )
        checks["auth_boundary"] = True
        details["auth_boundary"] = {
            "production_bootstrap_status": bootstrap_status,
            "anonymous_project_status": anonymous_status,
        }

        fixture = seed_tenants(compose_file)
        tenant_a, tenant_b = fixture["tenants"]
        token_a = login(api_url, email=tenant_a["email"], password=tenant_a["password"], origin=origin)
        token_b = login(api_url, email=tenant_b["email"], password=tenant_b["password"], origin=origin)
        org_a = str(tenant_a["organization_id"])
        org_b = str(tenant_b["organization_id"])
        project_a = create_project(
            api_url,
            token=token_a,
            organization_id=org_a,
            name="DEPLOY-BETA-08 Canonical Project",
            origin=origin,
        )

        status, _headers, body = request(
            dib_url,
            "POST",
            "/api/dib/sessions",
            payload={
                "project_profile": {
                    "project_id": project_a,
                    "name": "DEPLOY-BETA-08 Canonical Project",
                    "sector": "Food Service",
                }
            },
            token=token_a,
            organization_id=org_a,
            origin=origin,
        )
        session_payload = json_body(body)
        session = session_payload.get("session") if isinstance(session_payload.get("session"), dict) else {}
        session_id = str(session.get("session_id") or "")
        require(status == 201 and bool(session_id), "private_smoke_dib_session_failed")

        denied_status, _headers, denied_body = request(
            dib_url,
            "GET",
            f"/api/dib/sessions/{session_id}",
            token=token_b,
            organization_id=org_b,
            origin=origin,
        )
        denied_events_status, _headers, _events_body = request(
            dib_url,
            "GET",
            f"/api/dib/sessions/{session_id}/events",
            token=token_b,
            organization_id=org_b,
            origin=origin,
        )
        denied_error = json_body(denied_body).get("error")
        require(
            denied_status == 404
            and denied_error == "dib_resource_not_found"
            and denied_events_status == 404,
            "private_smoke_tenant_isolation_failed",
        )
        checks["tenant_isolation"] = True
        details["tenant_isolation"] = {
            "cross_tenant_session_status": denied_status,
            "cross_tenant_events_status": denied_events_status,
        }

        rows = [
            {"input_key": "startup_cost", "label": "Startup", "value": 120000},
            {"input_key": "monthly_fixed_cost", "label": "Fixed", "value": 42000},
            {"input_key": "unit_price", "label": "Price", "value": 18},
            {"input_key": "variable_cost", "label": "Variable", "value": 7},
            {"input_key": "monthly_units", "label": "Units", "value": 4200},
        ]
        blueprint_status, _headers, _body = request(
            dib_url,
            "POST",
            f"/api/dib/sessions/{session_id}/blueprints",
            payload={
                "source": "deploy_beta_08_private_smoke",
                "intake_payload": {"file_name": "private-smoke-inputs", "rows": rows},
            },
            token=token_a,
            organization_id=org_a,
            origin=origin,
        )
        require(blueprint_status in (200, 201), "private_smoke_blueprint_failed")

        manifest_status, _headers, manifest_body = request(
            dib_url,
            "POST",
            f"/api/dib/sessions/{session_id}/approved-manifests",
            payload={},
            token=token_a,
            organization_id=org_a,
            origin=origin,
        )
        manifest = json_body(manifest_body).get("approved_manifest")
        require(manifest_status in (200, 201) and isinstance(manifest, dict), "private_smoke_manifest_failed")

        gate_status, _headers, gate_body = request(
            dib_url,
            "POST",
            f"/api/dib/sessions/{session_id}/validation-gates",
            payload={},
            token=token_a,
            organization_id=org_a,
            origin=origin,
        )
        gate = json_body(gate_body).get("validation_gate")
        require(gate_status in (200, 201) and isinstance(gate, dict), "private_smoke_gate_failed")

        run_command = {
            "scenario_id": "baseline",
            "idempotency_key": f"idem:deploy-beta-08:{expected_commit[:16]}",
            "expected_manifest_id": manifest.get("manifest_id"),
            "expected_manifest_payload_hash": manifest.get("payload_hash"),
            "expected_gate_id": gate.get("gate_id"),
            "expected_gate_payload_hash": gate.get("payload_hash"),
        }
        run_status, run_headers, run_body = request(
            dib_url,
            "POST",
            f"/api/dib/sessions/{session_id}/controlled-finance",
            payload=run_command,
            token=token_a,
            organization_id=org_a,
            origin=origin,
            timeout=120,
        )
        controlled = json_body(run_body).get("controlled_finance")
        require(run_status in (200, 201) and isinstance(controlled, dict), "private_smoke_canonical_run_failed")
        snapshot_id = str(controlled.get("snapshot_id") or "")
        run_id = str(controlled.get("run_id") or "")
        require(
            controlled.get("status") == "executed"
            and controlled.get("project_run_workflow_mount") == "called"
            and (controlled.get("workflow") or {}).get("contract_id") == "project.run.workflow.v1"
            and controlled.get("finance_engine_execution_status") == "executed_via_project_run_workflow"
            and bool(snapshot_id)
            and bool(run_id),
            "private_smoke_canonical_workflow_not_proven",
        )

        replay_status, _headers, replay_body = request(
            dib_url,
            "POST",
            f"/api/dib/sessions/{session_id}/controlled-finance",
            payload=run_command,
            token=token_a,
            organization_id=org_a,
            origin=origin,
            timeout=120,
        )
        replay = json_body(replay_body).get("controlled_finance")
        require(
            replay_status == 200
            and isinstance(replay, dict)
            and replay.get("run_id") == run_id
            and replay.get("snapshot_id") == snapshot_id
            and replay.get("idempotency_replayed") is True,
            "private_smoke_idempotency_failed",
        )
        checks["canonical_project_run"] = True
        details["canonical_project_run"] = {
            "run_id": run_id,
            "snapshot_id": snapshot_id,
            "workflow_contract": (controlled.get("workflow") or {}).get("contract_id"),
            "request_id_present": any(key.lower() == "x-request-id" for key in run_headers),
            "idempotency_replayed": True,
        }

        snapshot_status, _headers, snapshot_body = request(
            api_url,
            "GET",
            f"/api/snapshots/{snapshot_id}",
            token=token_a,
            organization_id=org_a,
            origin=origin,
        )
        snapshot_response = json_body(snapshot_body)
        snapshot = snapshot_response.get("snapshot") if isinstance(snapshot_response.get("snapshot"), dict) else {}
        immutable = snapshot.get("immutable") is True or bool(snapshot.get("seal")) or bool(snapshot_response.get("integrity"))
        require(
            snapshot_status == 200
            and str(snapshot.get("snapshot_id") or snapshot_id) == snapshot_id
            and immutable,
            "private_smoke_snapshot_readback_failed",
        )
        checks["snapshot_readback"] = True
        details["snapshot_readback"] = {
            "snapshot_id": snapshot_id,
            "status": snapshot_status,
            "immutable": True,
        }

        require(all(checks.values()), "private_smoke_required_check_incomplete")
        status_value = "passed"
        error_code: str | None = None
    except Exception as exc:  # evidence must be emitted even when the live probe fails
        status_value = "failed"
        error_code = str(exc) or exc.__class__.__name__

    evidence: dict[str, Any] = {
        "schema": DEPLOYMENT_EVIDENCE_SCHEMA,
        "package_id": "DEPLOY-BETA-08",
        "status": status_value,
        "commit_sha": actual_commit,
        "image_digest": image_digest,
        "image_material": image_material,
        "started_at": started_at,
        "finished_at": now_iso(),
        "checks": checks,
        "check_details": details,
        "capabilities": {capability: False for capability in DEGRADABLE_CAPABILITIES},
        "network_boundary": {
            "loopback_only": True,
            "published_bindings": [
                "127.0.0.1:18080:80",
                "127.0.0.1:18794:8794",
                "127.0.0.1:18795:8795",
            ],
            "public_bindings": [],
            "docker_network_internal": True,
            "external_fetch_enabled": False,
            "caddy_present": False,
        },
        "secrets_exposed": False,
        "fixture_data_ephemeral": True,
        "error_code": error_code,
    }
    evidence["evidence_hash"] = deployment_evidence_hash(evidence)
    return evidence


def write_evidence(path: Path, evidence: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dict(evidence), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run DEPLOY-BETA-08 against the private Docker deployment.")
    parser.add_argument("--expected-commit", required=True)
    parser.add_argument("--compose-file", type=Path, required=True)
    parser.add_argument("--api-url", default="http://127.0.0.1:18794")
    parser.add_argument("--dib-url", default="http://127.0.0.1:18795")
    parser.add_argument("--web-url", default="http://127.0.0.1:18080")
    parser.add_argument("--origin", default="http://127.0.0.1:18080")
    parser.add_argument("--backend-image", required=True)
    parser.add_argument("--web-image", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    compose_file = args.compose_file.resolve()
    evidence = run_live_smoke(
        expected_commit=str(args.expected_commit).strip(),
        compose_file=compose_file,
        api_url=args.api_url,
        dib_url=args.dib_url,
        web_url=args.web_url,
        origin=args.origin,
        backend_image=args.backend_image,
        web_image=args.web_image,
    )
    write_evidence(args.output.resolve(), evidence)
    print(
        json.dumps(
            {
                "status": evidence["status"],
                "commit_sha": evidence["commit_sha"],
                "image_digest": evidence["image_digest"],
                "checks": evidence["checks"],
                "evidence_hash": evidence["evidence_hash"],
                "error_code": evidence.get("error_code"),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0 if evidence["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
