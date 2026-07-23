from __future__ import annotations

import sys
import json
import mimetypes
import os
import re
import threading
import uuid
from collections import defaultdict, deque
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse
from warnings import deprecated

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.acceptance import build_acceptance_pack
from backend.aas_kernel import AASKernel
from backend.aas_registry import (
    APP_ID,
    AAS_CLI_RELEASE,
    AAS_RELEASE,
    AAS_SPEC_VERSION,
    HEART_COUNT,
    MANIFEST_PATH,
    boot_report as aas_boot_report,
    manifest_text as aas_manifest_text,
    module_registry,
)
from backend.bus_controller import BusController
from backend.decision_council import build_decision_result
from backend.deployment_profile import build_operations_health, build_release_info
from backend.decision_council import build_decision_result
from backend.evidence_ledger import (
    build_coverage as build_evidence_coverage,
    build_ledger as build_evidence_ledger_entries,
    build_register as build_evidence_register_entries,
    build_transformation_lineage,
)
from backend.execution_engine import build_execution_plan
from backend.finance_engine import FinanceInputs, calculate_finance
from backend.funder_report import render_funder_report_html
from backend.funding_readiness import (
    evaluate_funding_readiness,
    profile_catalog,
    profile_readiness_summary,
    sector_profile_catalog,
)
from backend.heart_controller import HeartController, HeartTask
from backend.identity import Principal
from backend.intelligence_prerun_service import IntelligencePreRunService
from backend.local_intelligence_modules import (
    evidence_register_from_ledger,
    local_decision_council,
    local_evidence_ledger,
    local_execution_engine,
    local_finance_engine,
    local_risk_engine,
    local_sector_intelligence,
    local_snapshot_assembly,
)
from backend.market_cost_intelligence import build_component_quote_request, build_pricing_components
from backend.module_runtime import ModuleRuntime, RuntimeModule, module_sealed_output_payload
from backend.project_run_workflow import ProjectRunWorkflow, RequestError
from backend.readiness_gates import evaluate_readiness_gates
from backend.report_release import build_release_record
from backend.repository import ProjectRecord, Repository
from backend.risk_engine import build_risk_register
from backend.runtime_freeze import (
    RUNTIME_FREEZE_SCOPE,
    runtime_freeze_manifest,
    runtime_freeze_violations,
)
from backend.sector_intelligence import build_sector_context, build_sector_criteria, sector_taxonomy
from backend.snapshot_assembly import assemble_snapshot
from backend.socket_contracts import SocketContract
from backend.system_bus import SystemBus
from backend.workspace import (
    build_action_items_from_overview,
    build_project_remediation,
    build_project_workspace,
    compare_snapshots,
    project_readiness,
)

HOST = os.environ.get("ASIE_HOST", "127.0.0.1")
PORT = int(os.environ.get("ASIE_PORT", "8794"))
ROOT = Path(__file__).resolve().parent.parent
STATIC_ROOT = ROOT / "dist"
LEGACY_ORGANIZATION_ID = "org_alpha_signature"
PROFILE_ID = "strict_open_data_only_v1"
LOCAL_FRONTEND_ORIGINS = {
    "http://localhost:5194",
    "http://127.0.0.1:5194",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
}
MAX_BODY_BYTES = 2 * 1024 * 1024
WINDOW_SECONDS = 60
RATE_LIMIT = 300


class RateLimiter:
    def __init__(self, limit: int, window_seconds: int) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = datetime.now(timezone.utc).timestamp()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] > self.window_seconds:
                hits.popleft()
            if len(hits) >= self.limit:
                return False
            hits.append(now)
            return True


REQUEST_RATE_LIMITER = RateLimiter(RATE_LIMIT, WINDOW_SECONDS)
RUN_IDEMPOTENCY_STORE = None


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def audit_event(action: str, **payload: Any) -> dict:
    return {"action": action, "at": utc_now(), **payload}


def write_json(handler: BaseHTTPRequestHandler, payload: dict, status: int = 200) -> None:
    body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(body)


def write_html(handler: BaseHTTPRequestHandler, html: str, status: int = 200) -> None:
    body = html.encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "text/html; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(body)


def write_error(handler: BaseHTTPRequestHandler, code: str, status: int) -> None:
    write_json(handler, {"error": code}, status)


def read_json(handler: BaseHTTPRequestHandler) -> dict:
    length = int(handler.headers.get("Content-Length", "0") or 0)
    if length > MAX_BODY_BYTES:
        raise RequestError("payload_too_large", 413)
    if length == 0:
        return {}
    return json.loads(handler.rfile.read(length).decode("utf-8"))


REPO = Repository()
AAS_KERNEL = AASKernel(REPO)
HEART_CONTROLLER = HeartController()
SYSTEM_BUS = SystemBus()
BUS_CONTROLLER = BusController(SYSTEM_BUS)


def local_runtime_context() -> Any:
    return AAS_KERNEL.runtime_context()


def heart_source_module_id(heart_assignment: dict) -> str:
    return heart_assignment.get("module_id", APP_ID)


def normalize_project_run_http_request(project_id: str, payload: dict) -> dict:
    operation_id = str(payload.get("operation_id") or new_id("op"))
    idempotency_key = str(payload.get("idempotency_key") or operation_id)
    inputs = payload.get("inputs") if isinstance(payload.get("inputs"), dict) else {}
    return {
        "project_id": project_id,
        "operation_id": operation_id,
        "idempotency_key": idempotency_key,
        "inputs": inputs,
        "actor": str(payload.get("actor") or "local-operator"),
        "correlation_id": str(payload.get("correlation_id") or new_id("corr")),
    }


def execute_project_run_pipeline(run_envelope: dict, project: ProjectRecord, data_access: Repository) -> tuple[dict, dict]:
    inputs = dict(project.inputs)
    inputs.update(run_envelope.get("inputs", {}))
    finance_inputs = FinanceInputs(**{key: value for key, value in inputs.items() if key in FinanceInputs.__dataclass_fields__})
    context = local_runtime_context()
    runtime = context.runtime
    finance_result = local_finance_engine(runtime, finance_inputs)
    sector_context = build_sector_context(project.sector, project.jurisdiction)
    sector_criteria = build_sector_criteria(project.sector)
    evidence_register, ledger_entries, coverage = local_evidence_ledger(
        runtime,
        project=project,
        finance_result=finance_result,
        sector_context=sector_context,
    )
    decision = local_decision_council(
        runtime,
        finance_result=finance_result,
        evidence_coverage=coverage,
        sector_criteria=sector_criteria,
    )
    risk_register = local_risk_engine(
        runtime,
        finance_result=finance_result,
        decision=decision,
        evidence_coverage=coverage,
    )
    execution_plan = local_execution_engine(
        runtime,
        project=project,
        finance_result=finance_result,
        decision=decision,
        risk_register=risk_register,
    )
    snapshot = local_snapshot_assembly(
        runtime,
        project=project,
        finance_result=finance_result,
        sector_context=sector_context,
        evidence_register=evidence_register,
        evidence_ledger=ledger_entries,
        evidence_coverage=coverage,
        decision=decision,
        risk_register=risk_register,
        execution_plan=execution_plan,
    )
    acceptance = build_acceptance_pack(snapshot, decision, coverage)
    overview = {
        "contract_id": "project.run.overview.v1",
        "run": run_envelope.get("run", {"run_id": run_envelope.get("operation_id")}),
        "project": project.to_public(),
        "snapshot": snapshot,
        "acceptance": acceptance,
    }
    report = {
        "contract_id": "project.report.v1",
        "snapshot_id": snapshot["snapshot_id"],
        "funder_report": snapshot.get("funder_report", {}),
        "html": snapshot.get("report_html", ""),
    }
    return overview, report


def decision_pack_via_module_runtime(overview: dict, report: dict) -> dict:
    context = local_runtime_context()
    return {
        "contract_id": "decision.pack.v1",
        "snapshot_id": overview["snapshot"]["snapshot_id"],
        "decision": overview["snapshot"].get("decision", {}),
        "finance": overview["snapshot"].get("finance", {}),
        "evidence_coverage": overview["snapshot"].get("evidence_coverage", {}),
        "risk_register": overview["snapshot"].get("risk_register", {}),
        "acceptance": overview.get("acceptance", {}),
    }


def apply_review_overlay(pack: dict, reviews: list[dict]) -> dict:
    updated = deepcopy(pack)
    updated["reviews"] = reviews
    if reviews:
        updated["latest_review"] = reviews[-1]
    return updated


def render_decision_pack_html(pack: dict) -> str:
    return "\n".join(
        [
            "<!doctype html><html lang='ar' dir='rtl'><head><meta charset='utf-8'><title>حزمة القرار</title></head><body>",
            f"<h1>حزمة القرار — {pack.get('snapshot_id', '')}</h1>",
            f"<pre>{json.dumps(pack, ensure_ascii=False, indent=2)}</pre>",
            "</body></html>",
        ]
    )


def build_report_view(report: dict, latest_review: dict | None) -> dict:
    return {
        "contract_id": "report.view.v1",
        "snapshot_id": report.get("snapshot_id", ""),
        "latest_review": latest_review,
        "sections": report.get("funder_report", {}).get("sections", []),
    }


def render_report_html(report: dict, latest_review: dict | None) -> str:
    return "\n".join(
        [
            "<!doctype html><html lang='ar' dir='rtl'><head><meta charset='utf-8'><title>تقرير المشروع</title></head><body>",
            f"<h1>تقرير المشروع — {report.get('snapshot_id', '')}</h1>",
            f"<pre>{json.dumps(report.get('funder_report', {}), ensure_ascii=False, indent=2)}</pre>",
            "</body></html>",
        ]
    )


def source_policy(records: list[dict], profile_id: str) -> dict:
    return {
        "contract_id": "source.policy.v1",
        "profile_id": profile_id,
        "sources": records,
        "external_fetch_enabled": False,
    }


def source_review_checklist(record: dict) -> dict:
    return {
        "source_id": record.get("source_id", ""),
        "review_status": record.get("review_status", ""),
        "checklist": [
            "license_verified",
            "terms_hash_recorded",
            "human_review_completed",
        ],
    }


def dataset_quality_gate(dataset: dict, source: dict | None) -> dict:
    reasons: list[str] = []
    if not dataset.get("review_status") == "approved_for_use":
        reasons.append("dataset_not_approved")
    if source is not None and source.get("review_status") != "approved":
        reasons.append("source_not_approved")
    return {
        "contract_id": "dataset.quality_gate.v1",
        "dataset_id": dataset.get("dataset_id", ""),
        "can_use_for_assumptions": not reasons,
        "reasons": reasons,
    }


def normalize_file_import_payload(payload: dict) -> dict:
    normalized = dict(payload)
    normalized.setdefault("import_method", "file_upload")
    return normalized


def build_project_evidence_state(repo: Repository, project: ProjectRecord, status: str, run_id: str | None) -> tuple[dict, dict, list, dict]:
    sector = build_sector_context(project.sector, project.jurisdiction)
    ledger = repo.evidence_ledger(project.project_id)
    register = evidence_register_from_ledger(ledger)
    coverage = build_evidence_coverage(register, sector)
    return register, sector, ledger, coverage


def build_evidence_register(repo: Repository, project_id: str, status: str) -> dict:
    ledger = repo.evidence_ledger(project_id)
    return evidence_register_from_ledger(ledger)


def build_architecture_runtime_status() -> dict:
    return {
        "contract_id": "architecture.runtime_status.v1",
        "scope": RUNTIME_FREEZE_SCOPE,
        "manifest": runtime_freeze_manifest(),
        "violations": runtime_freeze_violations(),
        "boot_report": aas_boot_report(),
        "read_only": True,
    }


def local_operational_health(repo: Repository) -> dict:
    return build_operations_health(repo)


def release_info() -> dict:
    return build_release_info()


def reject_architecture_status_mutation(handler: BaseHTTPRequestHandler) -> None:
    write_json(
        handler,
        {
            "error": "architecture_runtime_status_is_read_only",
            "status": 405,
            "allowed_methods": ["GET"],
            "mutability": "read_only_projection",
            "allows_runtime_mutation": False,
        },
        405,
    )


class Handler(BaseHTTPRequestHandler):
    def _allow_request(self) -> bool:
        self.request_id = new_id("req")
        origin = self.headers.get("Origin")
        if origin and origin not in LOCAL_FRONTEND_ORIGINS:
            write_error(self, "origin_not_allowed", 403)
            return False
        route_key = f"{self.client_address[0]}:{self.command}:{urlparse(self.path).path}"
        if not REQUEST_RATE_LIMITER.allow(route_key):
            write_error(self, "rate_limit_exceeded", 429)
            return False
        return True

    def _require_platform_permission(self, permission: str) -> Principal | None:
        principal = self._principal()
        if principal is None:
            return None
        if principal.can(permission) or principal.can("platform.manage"):
            return principal
        REPO.audit(actor_user_id=principal.user_id, organization_id=None, action="authorization.check", target_type="platform", target_id=permission, result="denied", reason=permission, correlation_id=self.request_id)
        write_error(self, "permission_denied", 403)
        return None

    def _bearer_token(self) -> str | None:
        value = self.headers.get("Authorization", "")
        return value[7:].strip() if value.startswith("Bearer ") and value[7:].strip() else None

    def _principal(self, organization_id: str | None = None) -> Principal | None:
        token = self._bearer_token()
        principal = REPO.principal_for_token(token, organization_id) if token else None
        if principal is None and REPO.user_count() == 0 and organization_id in {None, LEGACY_ORGANIZATION_ID}:
            return Principal(
                user_id="local_legacy_operator",
                session_id="local_legacy_session",
                organization_id=LEGACY_ORGANIZATION_ID,
                role="organization_owner",
            )
        if principal is None:
            write_error(self, "authentication_required", 401)
            return None
        return principal

    def _require_organization_permission(self, organization_id: str, permission: str) -> Principal | None:
        principal = self._principal(organization_id)
        if principal is None:
            return None
        if principal.can(permission) or principal.can("platform.manage"):
            return principal
        REPO.audit(actor_user_id=principal.user_id, organization_id=organization_id, action="authorization.check", target_type="organization", target_id=organization_id, result="denied", reason=permission)
        write_error(self, "permission_denied", 403)
        return None

    def _require_project_permission(self, project_id: str, permission: str) -> ProjectRecord | None:
        project = REPO.get_project(project_id)
        if project is None:
            write_error(self, "project_not_found", 404)
            return None
        if self._require_organization_permission(project.organization_id, permission) is None:
            return None
        return project

    def _require_snapshot_permission(self, snapshot_id: str, permission: str = "snapshot.read") -> str | None:
        project_id = REPO.snapshot_project_id(snapshot_id)
        if project_id is None:
            write_error(self, "snapshot_not_found", 404)
            return None
        return project_id if self._require_project_permission(project_id, permission) else None

    def _require_run_permission(self, run_id: str, permission: str = "snapshot.read") -> str | None:
        project_id = REPO.run_project_id(run_id)
        if project_id is None:
            write_error(self, "run_not_found", 404)
            return None
        return project_id if self._require_project_permission(project_id, permission) else None

    def _require_dataset_permission(self, dataset_id: str, permission: str = "snapshot.read") -> bool:
        organization_id = REPO.dataset_organization_id(dataset_id)
        if organization_id is None:
            write_error(self, "dataset_not_found", 404)
            return False
        return self._require_organization_permission(organization_id, permission) is not None

    def do_OPTIONS(self) -> None:
        if not self._allow_request():
            return
        write_json(self, {"ok": True})

    def do_GET(self) -> None:
        try:
            self._dispatch_get()
        except PermissionError as exc:
            write_error(self, str(exc) or "permission_denied", 403)
        except RequestError as exc:
            write_error(self, exc.code, exc.status)

    def _dispatch_get(self) -> None:
        if not self._allow_request():
            return
        path = urlparse(self.path).path
        if path == "/api/health":
            write_json(self, {"ok": True, "service": "asie-local-api", "strict_profile": PROFILE_ID})
            return
        if path == "/api/funding-profiles":
            write_json(self, {"profiles": profile_catalog(), "external_fetch_enabled": False, "reference_only": True})
            return
        if path == "/api/sector-profiles":
            write_json(self, {"profiles": sector_profile_catalog(), "external_fetch_enabled": False, "reference_only": True})
            return
        if path == "/api/architecture/runtime-status":
            write_json(self, build_architecture_runtime_status())
            return
        if path == "/api/operations/health":
            if self._require_platform_permission("platform.manage") is None:
                return
            write_json(self, local_operational_health(REPO))
            return
        if path == "/api/operations/audit-events":
            if self._require_platform_permission("platform.manage") is None:
                return
            requested_limit = parse_qs(urlparse(self.path).query).get("limit", ["100"])[0]
            try:
                limit = int(requested_limit)
            except ValueError:
                write_error(self, "invalid_limit", 400)
                return
            write_json(self, {"events": REPO.security_audit_events(limit=limit), "read_only": True})
            return
        if path == "/api/operations/release-info":
            if self._require_platform_permission("platform.audit.read") is None:
                return
            write_json(self, release_info())
            return
        if path == "/api/admin/overview":
            if self._require_platform_permission("platform.manage") is None:
                return
            organizations = REPO.control_plane_organizations()
            write_json(self, {"organizations": organizations, "users": REPO.control_plane_users(), "invoices": REPO.local_invoices(), "health": local_operational_health(REPO), "external_payments_enabled": False, "external_notifications_enabled": False})
            return
        if path.startswith("/api/admin/organizations/") and path.endswith("/subscription"):
            if self._require_platform_permission("platform.manage") is None:
                return
            organization_id = path.split("/")[4]
            subscription = REPO.subscription_for_organization(organization_id)
            if subscription is None:
                write_error(self, "organization_not_found", 404)
                return
            write_json(self, {"subscription": subscription, "usage": REPO.usage_summary(organization_id), "invoices": REPO.local_invoices(organization_id)})
            return
        if path.startswith("/api/admin/organizations/") and path.endswith("/notifications"):
            if self._require_platform_permission("platform.manage") is None:
                return
            organization_id = path.split("/")[4]
            write_json(self, {"notifications": REPO.notifications_for_organization(organization_id), "external_delivery_enabled": False})
            return
        if path == "/api/auth/me":
            principal = self._principal()
            if principal is None:
                return
            write_json(self, {"user_id": principal.user_id, "platform_role": principal.platform_role, "memberships": REPO.memberships_for_user(principal.user_id), "external_access_enabled": False})
            return
        if path.startswith("/api/intelligence/contexts/"):
            context_id = path.split("/")[4]
            organization_id = self.headers.get("X-ASIE-Organization-Id", "")
            project_id = parse_qs(urlparse(self.path).query).get("project_id", [""])[0]
            principal = self._principal(organization_id)
            if not organization_id or not project_id or principal is None:
                write_error(self, "permission_denied", 403)
                return
            context = REPO.get_intelligence_context(context_build_id=context_id, organization_id=organization_id, project_id=project_id, principal=principal)
            if context is None:
                write_error(self, "intelligence_context_not_found", 404)
                return
            write_json(self, {"context": context, "snapshot_mutation": False, "external_fetch_enabled": False})
            return
        if self._principal() is None:
            return
        if path.startswith("/api/projects/"):
            if self._require_project_permission(path.split("/")[3], "snapshot.read") is None:
                return
        elif path.startswith("/api/runs/"):
            if self._require_run_permission(path.split("/")[3]) is None:
                return
        elif path.startswith("/api/snapshots/"):
            if self._require_snapshot_permission(path.split("/")[3]) is None:
                return
        elif path.startswith("/api/datasets/"):
            if not self._require_dataset_permission(path.split("/")[3]):
                return
        if path == "/api/source-policy":
            write_json(self, source_policy(REPO.source_records(), PROFILE_ID))
            return
        if path == "/api/sources":
            sources = REPO.source_records()
            write_json(
                self,
                {
                    "sources": sources,
                    "checklists": [source_review_checklist(row) for row in sources],
                    "external_fetch_enabled": False,
                },
            )
            return
        if path == "/api/sector-taxonomy":
            write_json(self, {"taxonomy": sector_taxonomy(), "external_fetch_enabled": False})
            return
        if path == "/api/datasets":
            organization_id = self.headers.get("X-ASIE-Organization-Id", "") or (LEGACY_ORGANIZATION_ID if REPO.user_count() == 0 else "")
            if not organization_id or self._require_organization_permission(organization_id, "snapshot.read") is None:
                return
            write_json(self, {"datasets": REPO.datasets(organization_id), "external_fetch_enabled": False})
            return
        if path.startswith("/api/datasets/"):
            parts = path.split("/")
            dataset_id = parts[3]
            dataset = REPO.get_dataset(dataset_id)
            if dataset is None:
                write_error(self, "dataset_not_found", 404)
                return
            if len(parts) == 4:
                write_json(self, {"dataset": dataset})
                return
            if len(parts) == 5 and parts[4] == "quality-gate":
                source = REPO.get_source_record(dataset["source_id"])
                write_json(self, dataset_quality_gate(dataset, source))
                return
            if len(parts) == 5 and parts[4] == "transformations":
                write_json(self, {"transformations": REPO.dataset_transformations(dataset_id)})
                return
        if path == "/api/projects":
            organization_id = self.headers.get("X-ASIE-Organization-Id", "") or (LEGACY_ORGANIZATION_ID if REPO.user_count() == 0 else "")
            if not organization_id or self._require_organization_permission(organization_id, "snapshot.read") is None:
                return
            write_json(self, {"projects": REPO.list_projects(organization_id)})
            return
        if path.startswith("/api/projects/"):
            parts = path.split("/")
            if len(parts) == 4:
                project = REPO.get_project(parts[3])
                if project is None:
                    write_error(self, "project_not_found", 404)
                    return
                write_json(self, {"project": project.to_public()})
                return
            if len(parts) == 5 and parts[4] == "runs":
                project = REPO.get_project(parts[3])
                if project is None:
                    write_error(self, "project_not_found", 404)
                    return
                write_json(self, {"runs": REPO.list_project_runs(parts[3])})
                return
            if len(parts) == 5 and parts[4] == "workspace":
                workspace = build_project_workspace(REPO, parts[3])
                if workspace is None:
                    write_error(self, "project_not_found", 404)
                    return
                write_json(self, workspace)
                return
            if len(parts) == 5 and parts[4] == "remediation":
                if REPO.get_project(parts[3]) is None:
                    write_error(self, "project_not_found", 404)
                    return
                write_json(self, build_project_remediation(REPO, parts[3]))
                return
            if len(parts) == 5 and parts[4] == "action-items":
                project = REPO.get_project(parts[3])
                if project is None:
                    write_error(self, "project_not_found", 404)
                    return
                latest_run = REPO.latest_project_run(parts[3])
                if not latest_run:
                    write_json(self, {"action_items": []})
                    return
                overview = REPO.get_run_overview(latest_run["run_id"]) or {}
                states = REPO.project_action_item_states(parts[3])
                write_json(self, {"action_items": build_action_items_from_overview(parts[3], overview, states)})
                return
            if len(parts) == 5 and parts[4] == "readiness":
                project = REPO.get_project(parts[3])
                if project is None:
                    write_error(self, "project_not_found", 404)
                    return
                write_json(
                    self,
                    project_readiness(project, REPO.project_assumptions(parts[3]), REPO.source_records()),
                )
                return
            if len(parts) == 5 and parts[4] == "assumptions":
                project = REPO.get_project(parts[3])
                if project is None:
                    write_error(self, "project_not_found", 404)
                    return
                write_json(self, {"assumptions": REPO.project_assumptions(parts[3])})
                return
            if len(parts) == 5 and parts[4] == "evidence-register":
                project = REPO.get_project(parts[3])
                if project is None:
                    write_error(self, "project_not_found", 404)
                    return
                write_json(self, build_evidence_register(REPO, parts[3], "draft"))
                return
            if len(parts) == 5 and parts[4] == "evidence-ledger":
                project = REPO.get_project(parts[3])
                if project is None:
                    write_error(self, "project_not_found", 404)
                    return
                evidence_register, sector, ledger, coverage = build_project_evidence_state(REPO, project, "draft", None)
                write_json(
                    self,
                    {
                        "evidence_register": evidence_register,
                        "sector_intelligence": sector,
                        "evidence_ledger": ledger,
                        "evidence_coverage": coverage,
                        "transformation_lineage": build_transformation_lineage(
                            ledger,
                            evidence_register.get("transformations", []),
                        ),
                    },
                )
                return
            if len(parts) == 5 and parts[4] == "transformation-lineage":
                project = REPO.get_project(parts[3])
                if project is None:
                    write_error(self, "project_not_found", 404)
                    return
                evidence_register, _sector, ledger, _coverage = build_project_evidence_state(REPO, project, "draft", None)
                write_json(
                    self,
                    {
                        "transformations": evidence_register.get("transformations", []),
                        "transformation_lineage": build_transformation_lineage(
                            ledger,
                            evidence_register.get("transformations", []),
                        ),
                    },
                )
                return
            if len(parts) == 5 and parts[4] == "evidence-coverage":
                project = REPO.get_project(parts[3])
                if project is None:
                    write_error(self, "project_not_found", 404)
                    return
                _evidence_register, _sector, _ledger, coverage = build_project_evidence_state(REPO, project, "draft", None)
                write_json(self, {"evidence_coverage": coverage})
                return
        if path.startswith("/api/runs/") and path.endswith("/overview"):
            run_id = path.split("/")[3]
            overview = REPO.get_run_overview(run_id)
            if overview is None:
                write_error(self, "run_not_found", 404)
                return
            write_json(self, overview)
            return
        if path.startswith("/api/runs/") and path.endswith("/audit"):
            run_id = path.split("/")[3]
            audit = REPO.get_run_audit(run_id)
            if audit is None:
                write_error(self, "run_not_found", 404)
                return
            write_json(self, audit)
            return
        if path.startswith("/api/runs/") and path.endswith("/acceptance"):
            run_id = path.split("/")[3]
            overview = REPO.get_run_overview(run_id)
            if overview is None:
                write_error(self, "run_not_found", 404)
                return
            write_json(self, overview["acceptance"])
            return
        if path.startswith("/api/snapshots/") and path.endswith("/report"):
            snapshot_id = path.split("/")[3]
            report = REPO.get_snapshot_report(snapshot_id)
            if report is None:
                write_error(self, "snapshot_not_found", 404)
                return
            write_json(self, report)
            return
        if path.startswith("/api/snapshots/") and path.endswith("/decision-pack"):
            snapshot_id = path.split("/")[3]
            overview = REPO.get_snapshot_overview(snapshot_id)
            report = REPO.get_snapshot_report(snapshot_id)
            if overview is None or report is None:
                write_error(self, "snapshot_not_found", 404)
                return
            base_pack = decision_pack_via_module_runtime(overview, report)
            write_json(self, apply_review_overlay(base_pack, REPO.snapshot_reviews(snapshot_id)))
            return
        if path.startswith("/api/snapshots/") and path.endswith("/decision-pack.html"):
            snapshot_id = path.split("/")[3]
            overview = REPO.get_snapshot_overview(snapshot_id)
            report = REPO.get_snapshot_report(snapshot_id)
            if overview is None or report is None:
                write_error(self, "snapshot_not_found", 404)
                return
            base_pack = decision_pack_via_module_runtime(overview, report)
            pack = apply_review_overlay(base_pack, REPO.snapshot_reviews(snapshot_id))
            write_html(self, render_decision_pack_html(pack))
            return
        if path.startswith("/api/snapshots/") and path.endswith("/reviews"):
            snapshot_id = path.split("/")[3]
            if REPO.get_snapshot_overview(snapshot_id) is None:
                write_error(self, "snapshot_not_found", 404)
                return
            write_json(self, {"reviews": REPO.snapshot_reviews(snapshot_id)})
            return
        if path.startswith("/api/snapshots/") and len(path.split("/")) == 4:
            snapshot_id = path.split("/")[3]
            overview = REPO.get_snapshot_overview(snapshot_id)
            if overview is None:
                write_error(self, "snapshot_not_found", 404)
                return
            write_json(self, overview)
            return
        if path.startswith("/api/snapshots/") and path.endswith("/report-view"):
            snapshot_id = path.split("/")[3]
            report = REPO.get_snapshot_report(snapshot_id)
            if report is None:
                write_error(self, "snapshot_not_found", 404)
                return
            write_json(self, build_report_view(report, REPO.latest_snapshot_review(snapshot_id)))
            return
        if path.startswith("/api/snapshots/") and path.endswith("/report.html"):
            snapshot_id = path.split("/")[3]
            report = REPO.get_snapshot_report(snapshot_id)
            if report is None:
                write_error(self, "snapshot_not_found", 404)
                return
            write_html(self, render_report_html(report, REPO.latest_snapshot_review(snapshot_id)))
            return
        if path.startswith("/api/snapshots/") and path.endswith("/funder-report.html"):
            snapshot_id = path.split("/")[3]
            report = REPO.get_snapshot_report(snapshot_id)
            if report is None:
                write_error(self, "snapshot_not_found", 404)
                return
            write_html(self, render_funder_report_html(report.get("funder_report", {})))
            return
        if path.startswith("/api/snapshots/") and path.endswith("/release"):
            snapshot_id = path.split("/")[3]
            overview = REPO.get_snapshot_overview(snapshot_id)
            report = REPO.get_snapshot_report(snapshot_id)
            if overview is None or report is None:
                write_error(self, "snapshot_not_found", 404)
                return
            write_json(self, build_release_record(report.get("funder_report", {}), REPO.latest_snapshot_review(snapshot_id)))
            return
        write_error(self, "not_found", 404)

    def do_POST(self) -> None:
        if not self._allow_request():
            return
        path = urlparse(self.path).path
        if path == "/api/architecture/runtime-status":
            reject_architecture_status_mutation(self)
            return
        try:
            payload = read_json(self)
            if path == "/api/auth/local-bootstrap":
                if REPO.user_count() != 0:
                    write_error(self, "local_bootstrap_already_completed", 409)
                    return
                user = REPO.create_user(email=str(payload.get("email") or ""), display_name=str(payload.get("display_name") or ""), password=str(payload.get("password") or ""), platform_role="platform_admin")
                organization = REPO.create_organization(name=str(payload.get("organization_name") or "مساحة ASIE المحلية"), owner_user_id=user["user_id"])
                token, _authenticated_user = REPO.create_session(email=user["email"], password=str(payload.get("password") or ""))
                REPO.audit(actor_user_id=user["user_id"], organization_id=organization["organization_id"], action="local_bootstrap", target_type="organization", target_id=organization["organization_id"], result="allowed")
                write_json(self, {"access_token": token, "token_type": "Bearer", "user": user, "organization": organization, "external_access_enabled": False}, 201)
                return
            if path == "/api/auth/login":
                token, user = REPO.create_session(email=str(payload.get("email") or ""), password=str(payload.get("password") or ""))
                write_json(self, {"access_token": token, "token_type": "Bearer", "user": user, "memberships": REPO.memberships_for_user(user["user_id"]), "external_access_enabled": False})
                return
            if path == "/api/auth/password-recovery/request":
                write_json(self, REPO.create_password_recovery_request(email=str(payload.get("email") or "")))
                return
            if path == "/api/auth/password-recovery/complete":
                try:
                    result = REPO.consume_password_recovery_token(token=str(payload.get("recovery_token") or ""), password=str(payload.get("new_password") or ""))
                except ValueError as exc:
                    write_error(self, str(exc), 400)
                    return
                write_json(self, result)
                return
            if path == "/api/auth/logout":
                principal = self._principal()
                token = self._bearer_token()
                if principal is None or token is None:
                    return
                REPO.revoke_session(token)
                REPO.audit(actor_user_id=principal.user_id, organization_id=None, action="session.logout", target_type="session", target_id=principal.session_id, result="allowed")
                write_json(self, {"ok": True})
                return
            if path.startswith("/api/admin/users/") and path.endswith("/local-password-reset"):
                principal = self._require_platform_permission("platform.manage")
                if principal is None:
                    return
                user_id = path.split("/")[4]
                user = REPO.reset_local_password(user_id=user_id, password=str(payload.get("new_password") or ""), actor_user_id=principal.user_id)
                write_json(self, {"user": user, "sessions_revoked": True, "external_delivery_enabled": False})
                return
            if path.startswith("/api/admin/organizations/") and path.endswith("/subscription"):
                organization_id = path.split("/")[4]
                principal = self._require_platform_permission("subscription.manage")
                if principal is None:
                    return
                subscription = REPO.set_subscription(
                    organization_id=organization_id,
                    plan_code=str(payload.get("plan_code") or ""),
                    lifecycle_status=str(payload.get("lifecycle_status") or ""),
                    quota=payload.get("quota") if isinstance(payload.get("quota"), dict) else {},
                    actor_user_id=principal.user_id,
                    reason=str(payload.get("reason") or ""),
                )
                REPO.audit(actor_user_id=principal.user_id, organization_id=organization_id, action="subscription.change", target_type="organization_entitlement", target_id=organization_id, result="allowed", reason=str(payload.get("reason") or ""), correlation_id=self.request_id)
                REPO.create_notification(organization_id=organization_id, template_id="subscription_changed", reference_type="subscription", reference_id=organization_id)
                write_json(self, {"subscription": subscription, "external_payments_enabled": False})
                return
            if path.startswith("/api/admin/organizations/") and path.endswith("/invoices"):
                organization_id = path.split("/")[4]
                principal = self._require_platform_permission("subscription.manage")
                if principal is None:
                    return
                invoice = REPO.create_local_invoice(organization_id=organization_id, amount_minor=int(payload.get("amount_minor") or 0), currency=str(payload.get("currency") or "SAR"), actor_user_id=principal.user_id)
                write_json(self, {"invoice": invoice, "payment_collection_enabled": False}, 201)
                return
            if path.startswith("/api/admin/organizations/") and path.endswith("/notifications"):
                organization_id = path.split("/")[4]
                principal = self._require_platform_permission("platform.manage")
                if principal is None:
                    return
                notification = REPO.create_notification(organization_id=organization_id, template_id=str(payload.get("template_id") or ""), reference_type=str(payload.get("reference_type") or "manual"), reference_id=str(payload.get("reference_id") or organization_id), recipient_user_id=str(payload.get("recipient_user_id") or "") or None)
                REPO.audit(actor_user_id=principal.user_id, organization_id=organization_id, action="notification.create", target_type="notification", target_id=notification["notification_id"], result="allowed", reason=notification["template_id"], correlation_id=self.request_id)
                write_json(self, {"notification": notification, "external_delivery_enabled": False}, 201)
                return
            if path == "/api/organizations":
                principal = self._principal()
                if principal is None:
                    return
                organization = REPO.create_organization(name=str(payload.get("name") or ""), owner_user_id=principal.user_id)
                REPO.audit(actor_user_id=principal.user_id, organization_id=organization["organization_id"], action="organization.create", target_type="organization", target_id=organization["organization_id"], result="allowed")
                write_json(self, {"organization": organization}, 201)
                return
            if path.startswith("/api/organizations/") and path.endswith("/memberships"):
                organization_id = path.split("/")[3]
                principal = self._require_organization_permission(organization_id, "membership.manage")
                if principal is None:
                    return
                membership = REPO.add_membership(organization_id=organization_id, user_id=str(payload.get("user_id") or ""), role=str(payload.get("role") or ""), actor_user_id=principal.user_id)
                write_json(self, {"membership": membership}, 201)
                return
            if path.startswith("/api/organizations/") and path.endswith("/data-requests"):
                organization_id = path.split("/")[3]
                principal = self._require_organization_permission(organization_id, "organization.manage")
                if principal is None:
                    return
                request = REPO.create_organization_data_request(
                    organization_id=organization_id,
                    request_type=str(payload.get("request_type") or ""),
                    requested_by_user_id=principal.user_id,
                    legal_basis=str(payload.get("legal_basis") or ""),
                    notes=str(payload.get("notes") or ""),
                )
                REPO.audit(actor_user_id=principal.user_id, organization_id=organization_id, action="organization.data_request", target_type="data_request", target_id=request["request_id"], result="queued", reason=request["request_type"], correlation_id=self.request_id)
                write_json(self, {"data_request": request, "snapshot_mutation": False, "automatic_deletion": False}, 202)
                return
            if path == "/api/intelligence/contexts":
                organization_id = self.headers.get("X-ASIE-Organization-Id", "")
                principal = self._principal(organization_id)
                if not organization_id or principal is None:
                    write_error(self, "permission_denied", 403)
                    return
                record = REPO.create_intelligence_context(payload=payload | {"organization_id": organization_id}, principal=principal, correlation_id=self.request_id)
                write_json(self, {"context": record, "snapshot_mutation": False, "external_fetch_enabled": False}, 201)
                return
            if path == "/api/intelligence/pre-runs":
                organization_id = self.headers.get("X-ASIE-Organization-Id", "")
                principal = self._principal(organization_id)
                if not organization_id or principal is None:
                    write_error(self, "permission_denied", 403)
                    return
                required = ("project_id", "context_build_id", "idempotency_key", "geography", "sector")
                if any(not payload.get(key) for key in required) or not isinstance(payload.get("components"), list):
                    write_error(self, "pre_run_payload_incomplete", 400)
                    return
                result = IntelligencePreRunService(REPO).build_local_context(organization_id=organization_id, project_id=str(payload["project_id"]), context_build_id=str(payload["context_build_id"]), idempotency_key=str(payload["idempotency_key"]), geography=str(payload["geography"]), sector=str(payload["sector"]), components=payload["components"], principal=principal, correlation_id=self.request_id)
                write_json(self, result, 201 if result.get("context") else 422)
                return
            if path.startswith("/api/intelligence/contexts/") and path.endswith("/reviews"):
                context_id = path.split("/")[4]
                organization_id = self.headers.get("X-ASIE-Organization-Id", "")
                principal = self._principal(organization_id)
                if not organization_id or principal is None:
                    write_error(self, "permission_denied", 403)
                    return
                project_id = str(payload.get("project_id") or "")
                record = REPO.save_intelligence_review(organization_id=organization_id, project_id=project_id, overlay=payload | {"intelligence_context_id": context_id}, principal=principal, correlation_id=self.request_id)
                write_json(self, {"review": record, "snapshot_mutation": False}, 201)
                return
            if path.startswith("/api/intelligence/contexts/") and path.endswith("/approval"):
                context_id = path.split("/")[4]
                organization_id = self.headers.get("X-ASIE-Organization-Id", "")
                principal = self._principal(organization_id)
                if not organization_id or principal is None:
                    write_error(self, "permission_denied", 403)
                    return
                project_id = str(payload.get("project_id") or "")
                record = REPO.save_intelligence_approval(organization_id=organization_id, project_id=project_id, receipt=payload | {"intelligence_context_id": context_id}, principal=principal, correlation_id=self.request_id)
                write_json(self, {"approval": record, "snapshot_mutation": False}, 201)
                return
            if self._principal() is None:
                return
            if path in {"/api/datasets/manual-import", "/api/datasets/file-import"}:
                organization_id = self.headers.get("X-ASIE-Organization-Id", "") or (LEGACY_ORGANIZATION_ID if REPO.user_count() == 0 else "")
                if not organization_id or self._require_organization_permission(organization_id, "project.edit") is None:
                    return
                payload = payload | {"organization_id": organization_id}
            elif path.startswith("/api/datasets/"):
                if not self._require_dataset_permission(path.split("/")[3], "project.edit"):
                    return
            elif path.startswith("/api/snapshots/") and path.endswith("/reviews"):
                if self._require_snapshot_permission(path.split("/")[3], "review.write") is None:
                    return
            elif path == "/api/sources/review-record":
                principal = self._principal()
                if principal is None or not principal.can("platform.manage"):
                    write_error(self, "permission_denied", 403)
                    return
            if path == "/api/projects":
                organization_id = self.headers.get("X-ASIE-Organization-Id", "") or (LEGACY_ORGANIZATION_ID if REPO.user_count() == 0 else "")
                if not organization_id or self._require_organization_permission(organization_id, "project.create") is None:
                    return
                project = REPO.create_project(payload | {"organization_id": organization_id})
                write_json(self, {"project": project.to_public()}, 201)
                return
            if path.startswith("/api/projects/"):
                project_id = path.split("/")[3]
                permission = "project.run" if path.endswith("/runs") else "project.edit"
                if self._require_project_permission(project_id, permission) is None:
                    return
            if path.startswith("/api/projects/") and path.endswith("/runs"):
                project_id = path.split("/")[3]
                project = REPO.get_project(project_id)
                if project is None:
                    write_error(self, "project_not_found", 404)
                    return
                request = normalize_project_run_http_request(project.project_id, payload)
                replayed = RUN_IDEMPOTENCY_STORE.completed_replay(request)
                if replayed is not None:
                    write_json(self, replayed, 200)
                    return
                context = local_runtime_context()
                heart_assignment = context.heart_controller.assign_task(
                    HeartTask(
                        task_id=request["operation_id"],
                        purpose="project_run_workflow",
                        requires_assist=False,
                    )
                )
                source_module_id = heart_source_module_id(heart_assignment)
                workflow = ProjectRunWorkflow(
                    context.runtime,
                    RUN_IDEMPOTENCY_STORE,
                    source_module_id=source_module_id,
                    heart_assignment=heart_assignment,
                )
                result = workflow.run(
                    request,
                    build=lambda run_envelope: execute_project_run_pipeline(
                        run_envelope,
                        project=project,
                        data_access=REPO,
                    ),
                    save=lambda overview, report: REPO.save_run_snapshot(project.project_id, overview, report),
                )
                write_json(self, result.to_response(), 200 if result.idempotency_replayed else 201)
                return
            if path.startswith("/api/projects/") and path.endswith("/assumptions"):
                project_id = path.split("/")[3]
                project = REPO.get_project(project_id)
                if project is None:
                    write_error(self, "project_not_found", 404)
                    return
                write_json(self, {"assumption": REPO.save_assumption(project_id, payload)}, 201)
                return
            if path.startswith("/api/projects/") and path.endswith("/evidence-links"):
                project_id = path.split("/")[3]
                project = REPO.get_project(project_id)
                if project is None:
                    write_error(self, "project_not_found", 404)
                    return
                target_type = str(payload.get("target_type") or "assumption")
                target_id = str(payload.get("target_id") or payload.get("assumption_id") or "")
                if target_type == "assumption":
                    assumptions = {row["assumption_id"] for row in REPO.project_assumptions(project_id)}
                    if target_id not in assumptions:
                        write_error(self, "assumption_not_found", 404)
                        return
                elif target_type == "sector_criterion":
                    _register, sector, _ledger, _coverage = build_project_evidence_state(REPO, project, "draft", None)
                    criteria = {
                        row["criterion_id"]
                        for row in sector.get("sector_criteria", {}).get("criteria", [])
                    }
                    if target_id not in criteria:
                        write_error(self, "sector_criterion_not_found", 404)
                        return
                else:
                    write_error(self, "invalid_evidence_target_type", 400)
                    return
                dataset = REPO.get_dataset(str(payload.get("dataset_id") or ""))
                if dataset is None:
                    write_error(self, "dataset_not_found", 404)
                    return
                if dataset["organization_id"] != project.organization_id:
                    write_error(self, "dataset_organization_mismatch", 403)
                    return
                transformation_id = str(payload.get("transformation_id") or "")
                if transformation_id:
                    transformation = REPO.get_transformation(transformation_id)
                    if transformation is None:
                        write_error(self, "transformation_not_found", 404)
                        return
                    if transformation["dataset_id"] != dataset["dataset_id"]:
                        write_error(self, "transformation_dataset_mismatch", 400)
                        return
                gate = dataset_quality_gate(dataset, REPO.get_source_record(dataset["source_id"]))
                if not gate["can_use_for_assumptions"]:
                    write_error(self, "dataset_quality_gate_failed:" + ",".join(gate["reasons"]), 422)
                    return
                write_json(self, {"evidence_link": REPO.save_evidence_link(project_id, payload)}, 201)
                return
            if path == "/api/datasets":
                organization_id = self.headers.get("X-ASIE-Organization-Id", "") or (LEGACY_ORGANIZATION_ID if REPO.user_count() == 0 else "")
                if not organization_id or self._require_organization_permission(organization_id, "project.edit") is None:
                    return
                record = REPO.save_dataset(payload | {"organization_id": organization_id})
                write_json(self, {"dataset": record}, 201)
                return
            if path == "/api/datasets/manual-import":
                payload.setdefault("import_method", "manual_csv" if payload.get("csv_text") else "manual_table")
                record = REPO.save_dataset(payload)
                write_json(self, {"dataset": record}, 201)
                return
            if path == "/api/datasets/file-import":
                record = REPO.save_dataset(normalize_file_import_payload(payload))
                write_json(self, {"dataset": record, "external_fetch_enabled": False}, 201)
                return
            if path.startswith("/api/datasets/") and path.endswith("/transformations"):
                dataset_id = path.split("/")[3]
                if REPO.get_dataset(dataset_id) is None:
                    write_error(self, "dataset_not_found", 404)
                    return
                transformation = REPO.save_transformation(dataset_id, payload)
                write_json(self, {"transformation": transformation}, 201)
                return
            if path.startswith("/api/datasets/") and path.endswith("/review"):
                dataset_id = path.split("/")[3]
                record = REPO.review_dataset(dataset_id, payload)
                if record is None:
                    write_error(self, "dataset_not_found", 404)
                    return
                write_json(self, {"dataset": record})
                return
            if path == "/api/sources/review-record":
                record = REPO.save_source_review(payload)
                write_json(self, {"source": record}, 201)
                return
            if path.startswith("/api/snapshots/") and path.endswith("/reviews"):
                snapshot_id = path.split("/")[3]
                overview = REPO.get_snapshot_overview(snapshot_id)
                report = REPO.get_snapshot_report(snapshot_id)
                if overview is None or report is None:
                    write_error(self, "snapshot_not_found", 404)
                    return
                review = REPO.save_snapshot_review(
                    snapshot_id,
                    overview["run"]["run_id"],
                    overview["project"]["project_id"],
                    payload,
                )
                reviewed_project = REPO.get_project(overview["project"]["project_id"])
                if reviewed_project is not None:
                    REPO.create_notification(
                        organization_id=reviewed_project.organization_id,
                        template_id="review_recorded",
                        reference_type="snapshot_review",
                        reference_id=review["review_id"],
                    )
                write_json(self, {"review": review}, 201)
                return
            if path == "/api/snapshots/compare":
                first_id = str(payload.get("snapshot_a_id") or payload.get("first_snapshot_id") or "")
                second_id = str(payload.get("snapshot_b_id") or payload.get("second_snapshot_id") or "")
                first = REPO.get_snapshot_overview(first_id)
                second = REPO.get_snapshot_overview(second_id)
                if first is None or second is None:
                    write_error(self, "snapshot_not_found", 404)
                    return
                if self._require_snapshot_permission(first_id) is None or self._require_snapshot_permission(second_id) is None:
                    return
                if first["project"]["project_id"] != second["project"]["project_id"]:
                    write_error(self, "snapshot_project_mismatch", 400)
                    return
                write_json(self, compare_snapshots(first, second))
                return
        except PermissionError as exc:
            write_error(self, str(exc), 422)
            return
        except RequestError as exc:
            write_error(self, exc.code, exc.status)
            return
        except (ValueError, json.JSONDecodeError):
            write_error(self, "invalid_request", 400)
            return
        write_error(self, "not_found", 404)

    def do_PATCH(self) -> None:
        if not self._allow_request():
            return
        path = urlparse(self.path).path
        if path == "/api/architecture/runtime-status":
            reject_architecture_status_mutation(self)
            return
        try:
            payload = read_json(self)
            if self._principal() is None:
                return
            if path.startswith("/api/projects/"):
                parts = path.split("/")
                if len(parts) == 6 and parts[4] == "action-items":
                    project_id = parts[3]
                    if self._require_project_permission(project_id, "review.write") is None:
                        return
                    action_item_id = parts[5]
                    if REPO.get_project(project_id) is None:
                        write_error(self, "project_not_found", 404)
                        return
                    state = REPO.save_action_item_state(project_id, action_item_id, payload)
                    latest_run = REPO.latest_project_run(project_id)
                    if not latest_run:
                        write_json(self, {"action_item": state})
                        return
                    overview = REPO.get_run_overview(latest_run["run_id"]) or {}
                    items = build_action_items_from_overview(
                        project_id,
                        overview,
                        REPO.project_action_item_states(project_id),
                    )
                    item = next((row for row in items if row["action_item_id"] == action_item_id), state)
                    write_json(self, {"action_item": item})
                    return
                if len(parts) == 4:
                    if self._require_project_permission(parts[3], "project.edit") is None:
                        return
                    project = REPO.update_project(parts[3], payload)
                    if project is None:
                        write_error(self, "project_not_found", 404)
                        return
                    write_json(self, {"project": project.to_public()})
                    return
            if path.startswith("/api/sources/") and path.endswith("/review"):
                if self._require_platform_permission("platform.manage") is None:
                    return
                source_id = path.split("/")[3]
                payload["source_id"] = source_id
                record = REPO.save_source_review(payload)
                write_json(self, {"source": record})
                return
        except PermissionError as exc:
            write_error(self, str(exc), 422)
            return
        except RequestError as exc:
            write_error(self, exc.code, exc.status)
            return
        except (ValueError, json.JSONDecodeError):
            write_error(self, "invalid_request", 400)
            return
        write_error(self, "not_found", 404)

    def do_PUT(self) -> None:
        if not self._allow_request():
            return
        path = urlparse(self.path).path
        if path == "/api/architecture/runtime-status":
            reject_architecture_status_mutation(self)
            return
        write_error(self, "not_found", 404)

    def do_DELETE(self) -> None:
        if not self._allow_request():
            return
        path = urlparse(self.path).path
        if path == "/api/architecture/runtime-status":
            reject_architecture_status_mutation(self)
            return
        write_error(self, "not_found", 404)

    def log_message(self, format: str, *args: Any) -> None:
        return


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"ASIE local API running at http://{HOST}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
