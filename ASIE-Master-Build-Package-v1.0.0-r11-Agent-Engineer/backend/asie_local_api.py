from __future__ import annotations

import copy
import json
import mimetypes
import os
import queue
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from backend import dataset_ingestion
from backend import local_runtime as runtime
from backend.decision_pack import build_decision_pack_html, build_decision_pack_projection
from backend.deployment_profile import build_operations_health, build_release_info
from backend import export_controls
from backend.finance_engine import CANONICAL_FINANCE_INPUT_KEYS
from backend.funder_report import build_funder_report_projection, render_funder_report_html
from backend.funding_readiness import (
    evaluate_funding_readiness,
    profile_catalog,
    profile_readiness_summary,
    sector_profile_catalog,
)
from backend.identity import Principal, ROLE_PERMISSIONS
from backend import intelligence_runtime
from backend.intelligence_authorization import authorize_intelligence_action
from backend.intelligence_prerun_service import IntelligencePreRunService
from backend.market_cost_intelligence import build_component_quote_request, build_pricing_components
from backend.module_runtime import CORE_INPUTS
from backend.project_run_workflow import ProjectRunWorkflow, RequestError
from backend.report_release import (
    build_release_record,
    render_release_html,
    release_document_payload,
    validate_release_record,
)
from backend.reporting import build_dashboard_projection, build_report_projection
from backend.repository import Project, Repository
from backend.runtime_freeze import (
    RUNTIME_FREEZE_SCOPE,
    runtime_freeze_manifest,
    runtime_freeze_violations,
)
from backend.snapshot_assembly import canonical_hash
from backend.workspace import (
    build_project_remediation,
    build_project_snapshot_comparison,
    build_project_workspace,
    generate_action_items,
    update_action_item_status,
)

ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DATABASE_PATH = ROOT_DIR / ".asie" / "asie_local.sqlite3"
DATABASE_PATH = Path(os.environ.get("ASIE_DB_PATH", str(DEFAULT_DATABASE_PATH)))
DIST_DIR = Path(os.environ.get("ASIE_FRONTEND_DIST", str(ROOT_DIR / "dist")))
API_HOST = os.environ.get("ASIE_API_HOST", "127.0.0.1")
API_PORT = int(os.environ.get("ASIE_API_PORT", "8794"))
REQUEST_LOG_PATH = Path(os.environ.get("ASIE_REQUEST_LOG_PATH", "")) if os.environ.get("ASIE_REQUEST_LOG_PATH") else None
ALLOW_EXTERNAL_FETCH = os.environ.get("ASIE_ALLOW_EXTERNAL_FETCH", "false").lower() == "true"
EXPORT_DIR = Path(os.environ.get("ASIE_EXPORT_DIR", str(ROOT_DIR / ".asie" / "exports")))
MAX_REQUEST_BODY_BYTES = 512 * 1024
LEGACY_ORGANIZATION_ID = "org-alpha-local"
LOCAL_FRONTEND_ORIGINS = {
    "http://localhost:5194",
    "http://127.0.0.1:5194",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
}
RATE_LIMIT_RULES: dict[str, tuple[int, int]] = {
    "POST:/api/auth/local-bootstrap": (8, 3600),
    "POST:/api/auth/sessions": (12, 3600),
    "POST:/api/auth/password-recovery-requests": (12, 3600),
}


class RateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str, *, maximum: int, window_seconds: int) -> bool:
        now = time.monotonic()
        window_start = now - window_seconds
        with self._lock:
            hits = [stamp for stamp in self._hits.get(key, []) if stamp >= window_start]
            if len(hits) >= maximum:
                self._hits[key] = hits
                return False
            hits.append(now)
            self._hits[key] = hits
            return True


REQUEST_RATE_LIMITER = RateLimiter()


def utc_now() -> str:
    return runtime.utc_now()


def write_json(handler: BaseHTTPRequestHandler, payload: dict, status: int = 200) -> None:
    body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def write_error(handler: BaseHTTPRequestHandler, code: str, status: int) -> None:
    write_json(handler, {"error": code}, status)


REPO = Repository(DATABASE_PATH)
WORKFLOW = ProjectRunWorkflow(REPO)


def deprecated_alias(name: str, replacement: str):
    import warnings

    @warnings.deprecated(f"{name} is deprecated; use {replacement}")
    def wrapper(*args, **kwargs):
        return getattr(runtime, name)(*args, **kwargs)

    wrapper.__name__ = name
    return wrapper


class ModuleFacade:
    def __init__(self, module_name: str, legacy_module: Any) -> None:
        self.module_name = module_name
        self._legacy_module = legacy_module

    def __getattr__(self, attribute: str) -> Any:
        import warnings

        value = getattr(self._legacy_module, attribute)
        if callable(value) and not attribute.startswith("_"):
            @warnings.deprecated(f"{self.module_name}.{attribute} is deprecated; use AAS Module Runtime")
            def wrapped(*args, **kwargs):
                return value(*args, **kwargs)

            wrapped.__name__ = attribute
            return wrapped
        return value


finance_engine = ModuleFacade("finance_engine", runtime)
sector_intelligence = ModuleFacade("sector_intelligence", runtime)
evidence_ledger = ModuleFacade("evidence_ledger", runtime)
decision_council = ModuleFacade("decision_council", runtime)
risk_engine = ModuleFacade("risk_engine", runtime)
execution_engine = ModuleFacade("execution_engine", runtime)
snapshot_ledger = ModuleFacade("snapshot_ledger", runtime)


def legacy_module_call(name: str, *args, **kwargs):
    import warnings

    value = getattr(runtime, name)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        return value(*args, **kwargs)


def build_finance_snapshot(*args, **kwargs):
    return legacy_module_call("build_finance_snapshot", *args, **kwargs)


def build_scenarios(*args, **kwargs):
    return legacy_module_call("build_scenarios", *args, **kwargs)


def build_sensitivity(*args, **kwargs):
    return legacy_module_call("build_sensitivity", *args, **kwargs)


def build_decision_matrix(*args, **kwargs):
    return legacy_module_call("build_decision_matrix", *args, **kwargs)


def build_assumption_ledger(*args, **kwargs):
    return legacy_module_call("build_assumption_ledger", *args, **kwargs)


def build_investor_memo(*args, **kwargs):
    return legacy_module_call("build_investor_memo", *args, **kwargs)


def compute_run_fingerprint(*args, **kwargs):
    return legacy_module_call("compute_run_fingerprint", *args, **kwargs)


def build_engine_runs(*args, **kwargs):
    return legacy_module_call("build_engine_runs", *args, **kwargs)


def build_audit_trail(*args, **kwargs):
    return legacy_module_call("build_audit_trail", *args, **kwargs)


def build_risk_register(*args, **kwargs):
    return legacy_module_call("build_risk_register", *args, **kwargs)


def build_acceptance_criteria(*args, **kwargs):
    return legacy_module_call("build_acceptance_criteria", *args, **kwargs)


def validate_acceptance(*args, **kwargs):
    return legacy_module_call("validate_acceptance", *args, **kwargs)


def assemble_snapshot(project, finance, scenarios, sensitivity, decision_matrix, assumption_ledger, sector_context, evidence_ledger_data, risk_register, engines, acceptance, decision) -> dict:
    return runtime.assemble_snapshot(
        project,
        finance,
        scenarios,
        sensitivity,
        decision_matrix,
        assumption_ledger,
        sector_context,
        evidence_ledger_data,
        risk_register,
        engines,
        acceptance,
        decision,
    )


@deprecated_alias("decide_project", "AAS Module Runtime")
def decide_project(*args, **kwargs):
    pass


@deprecated_alias("validate_inputs", "AAS Module Runtime")
def validate_inputs(*args, **kwargs):
    pass


@deprecated_alias("run_engine_pipeline", "AAS Module Runtime")
def run_engine_pipeline(*args, **kwargs):
    pass


@deprecated_alias("create_snapshot", "AAS Module Runtime")
def create_snapshot(*args, **kwargs):
    pass


@deprecated_alias("analyze_project", "AAS Module Runtime")
def analyze_project(*args, **kwargs):
    pass


@deprecated_alias("assess_risks", "AAS Module Runtime")
def assess_risks(*args, **kwargs):
    pass


@deprecated_alias("load_sector_profile", "AAS Module Runtime")
def load_sector_profile(*args, **kwargs):
    pass


@deprecated_alias("build_sector_context", "AAS Module Runtime")
def build_sector_context(*args, **kwargs):
    pass


@deprecated_alias("build_evidence_ledger", "AAS Module Runtime")
def build_evidence_ledger(*args, **kwargs):
    pass


@deprecated_alias("build_coverage", "AAS Module Runtime")
def build_coverage(*args, **kwargs):
    pass


@deprecated_alias("build_report_payload", "AAS Module Runtime")
def build_report_payload(*args, **kwargs):
    pass


@deprecated_alias("build_execution_plan", "AAS Module Runtime")
def build_execution_plan(*args, **kwargs):
    pass


@deprecated_alias("build_investor_summary", "AAS Module Runtime")
def build_investor_summary(*args, **kwargs):
    pass


@deprecated_alias("build_lender_summary", "AAS Module Runtime")
def build_lender_summary(*args, **kwargs):
    pass


@deprecated_alias("build_internal_review", "AAS Module Runtime")
def build_internal_review(*args, **kwargs):
    pass


@deprecated_alias("build_evidence_register", "AAS Module Runtime")
def build_evidence_register(*args, **kwargs):
    pass


@deprecated_alias("run_project_pipeline", "ProjectRunWorkflow")
def run_project_pipeline(*args, **kwargs):
    pass


def run_project_modules(project: Project, repo: Repository | None = None) -> dict:
    return WORKFLOW.run_modules(project)


def build_overview(project: Project, repo: Repository | None = None) -> tuple[dict, dict]:
    import warnings

    warnings.warn(
        "build_overview() is deprecated; use ProjectRunWorkflow orchestration.",
        DeprecationWarning,
        stacklevel=2,
    )
    if repo is None:
        repo = REPO
    module_outputs = WORKFLOW.run_modules(project)
    overview = module_outputs["overview"]
    report = build_report_projection(overview)
    overview["snapshot"].setdefault("engine_versions", overview["snapshot"].get("engine_versions", {}))
    return overview, report


class WorkflowRunMessage:
    def __init__(self, workflow: ProjectRunWorkflow, project: Project) -> None:
        self.workflow = workflow
        self.project = project
        self.result: dict | None = None
        self.error: Exception | None = None

    def run(self) -> dict:
        try:
            self.result = self.workflow.run_modules(self.project)
            return self.result
        except Exception as exc:  # noqa: BLE001
            self.error = exc
            raise


class ChangeQueue:
    def __init__(self) -> None:
        self._subscribers: list[queue.Queue] = []
        self._lock = threading.Lock()

    def publish(self, payload: dict) -> None:
        with self._lock:
            subscribers = list(self._subscribers)
        for subscriber in subscribers:
            try:
                subscriber.put_nowait(payload)
            except queue.Full:
                pass

    def subscribe(self) -> queue.Queue:
        subscriber: queue.Queue = queue.Queue(maxsize=32)
        with self._lock:
            self._subscribers.append(subscriber)
        return subscriber

    def unsubscribe(self, subscriber: queue.Queue) -> None:
        with self._lock:
            if subscriber in self._subscribers:
                self._subscribers.remove(subscriber)


CHANGE_QUEUE = ChangeQueue()


def publish_change(event: str, payload: dict) -> None:
    CHANGE_QUEUE.publish({"event": event, "payload": payload, "timestamp": utc_now()})


class ProjectQueue:
    def __init__(self) -> None:
        self._queue: queue.Queue[WorkflowRunMessage] = queue.Queue()
        self._worker = threading.Thread(target=self._work, daemon=True)
        self._worker.start()

    def _work(self) -> None:
        while True:
            message = self._queue.get()
            try:
                message.run()
            except Exception:  # noqa: BLE001
                pass
            finally:
                self._queue.task_done()

    def submit(self, message: WorkflowRunMessage) -> None:
        self._queue.put(message)


PROJECT_QUEUE = ProjectQueue()


def build_source_policy_payload(repo: Repository) -> dict:
    policy = repo.source_policy()
    return {
        "policy_id": policy["policy_id"],
        "strict_open_data_profile": policy["strict_open_data_profile"],
        "allow_external_fetch": ALLOW_EXTERNAL_FETCH,
        "review_required_before_import": True,
        "source_classes": policy["source_classes"],
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "ASIELocalAPI/1.0"
    protocol_version = "HTTP/1.1"

    def log_message(self, format: str, *args: Any) -> None:
        if REQUEST_LOG_PATH:
            REQUEST_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
            with REQUEST_LOG_PATH.open("a", encoding="utf-8") as handle:
                handle.write(f"{utc_now()} {self.address_string()} {format % args}\n")

    def _request_id(self) -> str:
        return self.headers.get("X-Request-Id", uuid.uuid4().hex)

    def _write_security_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'; base-uri 'none'")
        self.send_header("X-Request-Id", self._request_id())
        origin = self.headers.get("Origin")
        if origin in LOCAL_FRONTEND_ORIGINS:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-ASIE-Organization-Id, X-Request-Id")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, OPTIONS")

    def end_headers(self) -> None:
        self._write_security_headers()
        super().end_headers()

    def _allow_request(self) -> bool:
        origin = self.headers.get("Origin")
        if origin and origin not in LOCAL_FRONTEND_ORIGINS:
            write_error(self, "origin_not_allowed", 403)
            return False
        route_key = f"{self.command}:{urlparse(self.path).path}"
        maximum, window = RATE_LIMIT_RULES.get(route_key, (120, 60))
        key = f"{self.client_address[0]}:{route_key}"
        if not REQUEST_RATE_LIMITER.allow(key, maximum=maximum, window_seconds=window):
            write_error(self, "rate_limited", 429)
            return False
        return True

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length > MAX_REQUEST_BODY_BYTES:
            raise RequestError("request_too_large", 413)
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        return json.loads(raw.decode("utf-8"))

    def _bearer_token(self) -> str | None:
        header = self.headers.get("Authorization", "")
        if header.startswith("Bearer "):
            return header[7:]
        return None

    def _principal(self, organization_id: str | None = None) -> Principal | None:
        token = self._bearer_token()
        principal = REPO.principal_for_token(token, organization_id) if token else None
        if principal is None and REPO.user_count() == 0 and organization_id in {None, LEGACY_ORGANIZATION_ID}:
            return Principal(
                user_id="legacy-operator",
                email="legacy@asie.local",
                display_name="Legacy Local Operator",
                organization_id=LEGACY_ORGANIZATION_ID,
                role="organization_owner",
                platform_role="platform_admin",
            )
        if principal is None:
            write_error(self, "authentication_required", 401)
            return None
        return principal

    def _require_platform_permission(self, permission: str) -> Principal | None:
        principal = self._principal()
        if principal is None:
            return None
        if not principal.can(permission):
            write_error(self, "permission_denied", 403)
            return None
        return principal

    def _require_organization_permission(self, organization_id: str, permission: str) -> Principal | None:
        principal = self._principal(organization_id)
        if principal is None:
            return None
        if principal.organization_id != organization_id or not (principal.can(permission) or principal.can("platform.manage")):
            REPO.audit("authorization_denied", organization_id=organization_id, actor_id=principal.user_id, payload={"permission": permission})
            write_error(self, "permission_denied", 403)
            return None
        return principal

    def _require_project_permission(self, project_id: str, permission: str) -> Principal | None:
        project = REPO.get_project(project_id)
        if project is None:
            write_error(self, "project_not_found", 404)
            return None
        return self._require_organization_permission(project.organization_id, permission)

    def _require_snapshot_permission(self, snapshot_id: str, permission: str = "snapshot.read") -> Principal | None:
        project_id = REPO.snapshot_project_id(snapshot_id)
        if project_id is None:
            write_error(self, "snapshot_not_found", 404)
            return None
        return self._require_project_permission(project_id, permission)

    def _require_run_permission(self, run_id: str, permission: str = "snapshot.read") -> Principal | None:
        project_id = REPO.run_project_id(run_id)
        if project_id is None:
            write_error(self, "run_not_found", 404)
            return None
        return self._require_project_permission(project_id, permission)

    def _require_dataset_permission(self, dataset_id: str, permission: str) -> Principal | None:
        dataset = REPO.get_dataset(dataset_id)
        if dataset is None:
            write_error(self, "dataset_not_found", 404)
            return None
        return self._require_organization_permission(dataset["organization_id"], permission)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Content-Length", "0")
        self.end_headers()

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
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/api/health":
            write_json(self, {"status": "ok", "timestamp": utc_now(), "runtime_freeze": RUNTIME_FREEZE_SCOPE})
            return
        if path == "/api/funding-profiles":
            write_json(self, {"profiles": profile_catalog()})
            return
        if path == "/api/sector-profiles":
            write_json(self, {"profiles": sector_profile_catalog()})
            return
        if path == "/api/architecture/runtime-status":
            write_json(
                self,
                {
                    "scope": RUNTIME_FREEZE_SCOPE,
                    "manifest": runtime_freeze_manifest(),
                    "violations": runtime_freeze_violations(),
                },
            )
            return
        if path == "/api/operations/health":
            if self._require_platform_permission("platform.audit.read") is None:
                return
            write_json(self, build_operations_health(REPO))
            return
        if path == "/api/operations/audit-events":
            if self._require_platform_permission("platform.audit.read") is None:
                return
            limit_raw = parse_qs(parsed.query).get("limit", ["50"])[0]
            try:
                limit = max(1, min(int(limit_raw), 200))
            except ValueError:
                limit = 50
            write_json(self, {"events": REPO.security_audit_events(limit=limit)})
            return
        if path == "/api/operations/release-info":
            if self._require_platform_permission("platform.audit.read") is None:
                return
            write_json(self, build_release_info())
            return
        if path.startswith("/api/admin/organizations/"):
            parts = path.split("/")
            if len(parts) == 5 and parts[4] == "subscription":
                if self._require_platform_permission("platform.manage") is None:
                    return
                record = REPO.get_subscription(parts[3])
                if record is None:
                    write_error(self, "subscription_not_found", 404)
                    return
                write_json(self, {"subscription": record})
                return
            if len(parts) == 5 and parts[4] == "notifications":
                if self._require_platform_permission("platform.manage") is None:
                    return
                write_json(self, {"notifications": REPO.list_notifications(parts[3])})
                return
        if path == "/api/admin/overview":
            if self._require_platform_permission("platform.manage") is None:
                return
            write_json(self, REPO.platform_overview())
            return
        if path == "/api/auth/me":
            principal = self._principal(self.headers.get("X-ASIE-Organization-Id") or None)
            if principal is None:
                return
            write_json(
                self,
                {
                    "user": REPO.get_user(principal.user_id),
                    "principal": {
                        "organization_id": principal.organization_id,
                        "role": principal.role,
                        "platform_role": principal.platform_role,
                        "permissions": sorted(principal.permissions()),
                    },
                    "memberships": REPO.list_memberships_for_user(principal.user_id),
                },
            )
            return
        if path.startswith("/api/intelligence/contexts/"):
            context_id = path.split("/")[4]
            organization_id = self.headers.get("X-ASIE-Organization-Id", "")
            project_id = parse_qs(parsed.query).get("project_id", [""])[0]
            principal = self._principal(organization_id)
            if not organization_id or not project_id or principal is None:
                write_error(self, "permission_denied", 403)
                return
            context = REPO.get_intelligence_context(
                context_build_id=context_id,
                organization_id=organization_id,
                project_id=project_id,
                principal=principal,
            )
            if context is None:
                write_error(self, "context_not_found", 404)
                return
            write_json(self, context)
            return
        if self._principal() is None:
            return
        if path == "/api/source-policy":
            write_json(self, build_source_policy_payload(REPO))
            return
        if path == "/api/sources":
            write_json(self, {"sources": REPO.source_records()})
            return
        if path == "/api/sector-taxonomy":
            write_json(self, {"taxonomy": REPO.sector_taxonomy()})
            return
        if path == "/api/datasets":
            organization_id = self.headers.get("X-ASIE-Organization-Id", "") or (LEGACY_ORGANIZATION_ID if REPO.user_count() == 0 else "")
            if not organization_id or self._require_organization_permission(organization_id, "snapshot.read") is None:
                return
            write_json(self, {"datasets": REPO.list_datasets(organization_id)})
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
                write_json(self, {"quality_gate": REPO.dataset_quality_gate(dataset_id)})
                return
            if len(parts) == 5 and parts[4] == "transformations":
                write_json(self, {"transformations": REPO.list_transformations(dataset_id)})
                return
        if path.startswith("/api/projects/") or path.startswith("/api/runs/") or path.startswith("/api/snapshots/") or path.startswith("/api/datasets/"):
            if path.startswith("/api/projects/"):
                project_id = path.split("/")[3]
                if self._require_project_permission(project_id, "snapshot.read") is None:
                    return
            elif path.startswith("/api/runs/"):
                if self._require_run_permission(path.split("/")[3]) is None:
                    return
            elif path.startswith("/api/snapshots/"):
                if self._require_snapshot_permission(path.split("/")[3]) is None:
                    return
            else:
                if self._require_dataset_permission(path.split("/")[3], "snapshot.read") is None:
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
                write_json(self, {"runs": REPO.list_runs(parts[3])})
                return
            if len(parts) == 5 and parts[4] == "workspace":
                write_json(self, build_project_workspace(REPO, parts[3]))
                return
            if len(parts) == 5 and parts[4] == "remediation":
                write_json(self, build_project_remediation(REPO, parts[3]))
                return
            if len(parts) == 5 and parts[4] == "action-items":
                write_json(self, {"items": REPO.list_action_items(parts[3])})
                return
            if len(parts) == 5 and parts[4] == "readiness":
                project = REPO.get_project(parts[3])
                if project is None:
                    write_error(self, "project_not_found", 404)
                    return
                write_json(self, {"readiness": project.readiness})
                return
            if len(parts) == 5 and parts[4] == "assumptions":
                write_json(self, {"assumptions": REPO.list_assumptions(parts[3])})
                return
            if len(parts) == 5 and parts[4] == "evidence-register":
                project = REPO.get_project(parts[3])
                if project is None:
                    write_error(self, "project_not_found", 404)
                    return
                write_json(self, {"evidence_register": legacy_module_call("build_evidence_register", project)})
                return
            if len(parts) == 5 and parts[4] == "evidence-ledger":
                write_json(self, {"evidence_ledger": REPO.evidence_ledger(parts[3])})
                return
            if len(parts) == 5 and parts[4] == "transformation-lineage":
                write_json(self, {"transformations": REPO.transformation_lineage(parts[3])})
                return
            if len(parts) == 5 and parts[4] == "evidence-coverage":
                write_json(self, {"evidence_coverage": REPO.evidence_coverage(parts[3])})
                return
        if path.startswith("/api/runs/"):
            parts = path.split("/")
            if len(parts) == 5 and parts[4] == "overview":
                overview = REPO.get_run_overview(parts[3])
                if overview is None:
                    write_error(self, "run_not_found", 404)
                    return
                write_json(self, overview)
                return
            if len(parts) == 5 and parts[4] == "audit":
                write_json(self, {"audit": REPO.run_audit(parts[3])})
                return
            if len(parts) == 5 and parts[4] == "acceptance":
                overview = REPO.get_run_overview(parts[3])
                if overview is None:
                    write_error(self, "run_not_found", 404)
                    return
                write_json(self, {"acceptance": overview["acceptance"]})
                return
        if path.startswith("/api/snapshots/"):
            parts = path.split("/")
            if len(parts) == 4:
                overview = REPO.get_snapshot_overview(parts[3])
                if overview is None:
                    write_error(self, "snapshot_not_found", 404)
                    return
                write_json(self, {"snapshot": overview["snapshot"]})
                return
            if len(parts) == 5 and parts[4] == "report":
                report = REPO.get_snapshot_report(parts[3])
                if report is None:
                    write_error(self, "snapshot_not_found", 404)
                    return
                write_json(self, report)
                return
            if len(parts) == 5 and parts[4] == "decision-pack":
                overview = REPO.get_snapshot_overview(parts[3])
                if overview is None:
                    write_error(self, "snapshot_not_found", 404)
                    return
                projection = build_decision_pack_projection(overview)
                write_json(self, projection)
                return
            if len(parts) == 5 and parts[4] == "decision-pack.html":
                overview = REPO.get_snapshot_overview(parts[3])
                if overview is None:
                    write_error(self, "snapshot_not_found", 404)
                    return
                html = build_decision_pack_html(build_decision_pack_projection(overview))
                body = html.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            if len(parts) == 5 and parts[4] == "reviews":
                write_json(self, {"reviews": REPO.list_snapshot_reviews(parts[3])})
                return
            if len(parts) == 5 and parts[4] == "report-view":
                report = REPO.get_snapshot_report(parts[3])
                if report is None:
                    write_error(self, "snapshot_not_found", 404)
                    return
                html = report["html"]
                body = html.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            if len(parts) == 5 and parts[4] == "report.html":
                report = REPO.get_snapshot_report(parts[3])
                if report is None:
                    write_error(self, "snapshot_not_found", 404)
                    return
                html = report["html"]
                body = html.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            if len(parts) == 5 and parts[4] == "funder-report.html":
                report = REPO.get_snapshot_report(parts[3])
                if report is None:
                    write_error(self, "snapshot_not_found", 404)
                    return
                html = render_funder_report_html(report["funder_report"])
                body = html.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            if len(parts) == 5 and parts[4] == "release":
                report = REPO.get_snapshot_report(parts[3])
                if report is None:
                    write_error(self, "snapshot_not_found", 404)
                    return
                write_json(self, release_document_payload(report["funder_report"]))
                return
        write_error(self, "not_found", 404)

    def do_POST(self) -> None:
        if not self._allow_request():
            return
        parsed = urlparse(self.path)
        path = parsed.path
        try:
            payload = self._read_json()
            if path == "/api/auth/local-bootstrap":
                if REPO.user_count() != 0:
                    write_error(self, "bootstrap_unavailable", 409)
                    return
                email = str(payload.get("email", "")).strip().lower()
                display_name = str(payload.get("display_name", "")).strip()
                password = str(payload.get("password", ""))
                organization_name = str(payload.get("organization_name", "")).strip()
                if not email or not display_name or not organization_name or len(password) < 12:
                    write_error(self, "invalid_bootstrap_payload", 422)
                    return
                user = REPO.create_user(email=email, display_name=display_name, password=password, platform_role="platform_admin")
                organization = REPO.create_organization(name=organization_name, owner_user_id=user["user_id"])
                token, _session = REPO.create_session(email=email, password=password)
                write_json(
                    self,
                    {
                        "token": token,
                        "user": user,
                        "organization": organization,
                        "memberships": REPO.list_memberships_for_user(user["user_id"]),
                    },
                    201,
                )
                return
            if path == "/api/auth/sessions":
                try:
                    token, session = REPO.create_session(email=str(payload.get("email", "")).strip().lower(), password=str(payload.get("password", "")))
                except ValueError:
                    REPO.audit("login_failed", payload={"email": str(payload.get("email", "")).strip().lower()})
                    write_error(self, "invalid_credentials", 401)
                    return
                write_json(self, {"token": token, "user": REPO.get_user(session["user_id"]), "memberships": REPO.list_memberships_for_user(session["user_id"])}, 201)
                return
            if path == "/api/auth/password-recovery-requests":
                request = REPO.create_password_recovery_request(email=str(payload.get("email", "")).strip().lower())
                write_json(self, {"request": request}, 201)
                return
            if path == "/api/auth/password-recovery-confirmations":
                try:
                    REPO.complete_password_recovery(token=str(payload.get("token", "")), new_password=str(payload.get("new_password", "")))
                except ValueError:
                    write_error(self, "invalid_recovery_token", 422)
                    return
                write_json(self, {"status": "password_updated"})
                return
            if path == "/api/auth/logout":
                token = self._bearer_token()
                if token:
                    REPO.revoke_session(token)
                write_json(self, {"status": "signed_out"})
                return
            if path == "/api/organizations":
                principal = self._principal()
                if principal is None:
                    return
                name = str(payload.get("name", "")).strip()
                if not name:
                    write_error(self, "invalid_organization_payload", 422)
                    return
                organization = REPO.create_organization(name=name, owner_user_id=principal.user_id)
                write_json(self, {"organization": organization, "memberships": REPO.list_memberships_for_user(principal.user_id)}, 201)
                return
            if path.startswith("/api/organizations/") and path.endswith("/memberships"):
                organization_id = path.split("/")[3]
                if self._require_organization_permission(organization_id, "membership.manage") is None:
                    return
                membership = REPO.add_membership(
                    organization_id=organization_id,
                    user_id=str(payload.get("user_id", "")),
                    role=str(payload.get("role", "viewer")),
                )
                write_json(self, {"membership": membership}, 201)
                return
            if path.startswith("/api/organizations/") and path.endswith("/data-requests"):
                organization_id = path.split("/")[3]
                principal = self._require_organization_permission(organization_id, "membership.manage")
                if principal is None:
                    return
                request = REPO.record_data_request(
                    organization_id=organization_id,
                    request_type=str(payload.get("request_type", "export")),
                    status="recorded",
                    payload={"requested_by": principal.user_id},
                )
                write_json(self, {"request": request}, 201)
                return
            if path == "/api/intelligence/contexts":
                organization_id = self.headers.get("X-ASIE-Organization-Id", "")
                principal = self._principal(organization_id)
                if not organization_id or principal is None:
                    write_error(self, "permission_denied", 403)
                    return
                context = REPO.create_intelligence_context(
                    organization_id=organization_id,
                    project_id=str(payload.get("project_id", "")),
                    actor_id=principal.user_id,
                    principal=principal,
                    idempotency_key=str(payload.get("idempotency_key", "")),
                )
                write_json(self, context, 201)
                return
            if path == "/api/intelligence/pre-runs":
                organization_id = self.headers.get("X-ASIE-Organization-Id", "")
                principal = self._principal(organization_id)
                if not organization_id or principal is None:
                    write_error(self, "permission_denied", 403)
                    return
                result = IntelligencePreRunService(REPO).build_local_context(
                    organization_id=organization_id,
                    project_id=str(payload.get("project_id", "")),
                    context_build_id=str(payload.get("context_build_id", "")),
                    actor_id=principal.user_id,
                    principal=principal,
                    idempotency_key=str(payload.get("idempotency_key", "")),
                    geography=str(payload.get("geography", "")),
                    sector=str(payload.get("sector", "")),
                    components=payload.get("components", []),
                )
                write_json(self, result, 201)
                return
            if path.startswith("/api/intelligence/contexts/") and path.endswith("/reviews"):
                organization_id = self.headers.get("X-ASIE-Organization-Id", "")
                principal = self._principal(organization_id)
                if not organization_id or principal is None:
                    write_error(self, "permission_denied", 403)
                    return
                context_build_id = path.split("/")[4]
                review = REPO.save_intelligence_review(
                    context_build_id=context_build_id,
                    organization_id=organization_id,
                    actor_id=principal.user_id,
                    principal=principal,
                    payload=payload,
                )
                write_json(self, review, 201)
                return
            if path.startswith("/api/intelligence/contexts/") and path.endswith("/approval"):
                organization_id = self.headers.get("X-ASIE-Organization-Id", "")
                principal = self._principal(organization_id)
                if not organization_id or principal is None:
                    write_error(self, "permission_denied", 403)
                    return
                context_build_id = path.split("/")[4]
                approval = REPO.save_intelligence_approval(
                    context_build_id=context_build_id,
                    organization_id=organization_id,
                    actor_id=principal.user_id,
                    principal=principal,
                    payload=payload,
                )
                write_json(self, approval, 201)
                return
            if self._principal() is None:
                return
            if path == "/api/datasets":
                organization_id = self.headers.get("X-ASIE-Organization-Id", "") or (LEGACY_ORGANIZATION_ID if REPO.user_count() == 0 else "")
                if not organization_id or self._require_organization_permission(organization_id, "project.edit") is None:
                    return
                record = REPO.save_dataset(payload | {"organization_id": organization_id})
                write_json(self, {"dataset": record}, 201)
                return
            if path == "/api/datasets/manual-import":
                organization_id = self.headers.get("X-ASIE-Organization-Id", "") or (LEGACY_ORGANIZATION_ID if REPO.user_count() == 0 else "")
                if not organization_id or self._require_organization_permission(organization_id, "project.edit") is None:
                    return
                record = dataset_ingestion.import_manual_dataset(REPO, payload | {"organization_id": organization_id})
                write_json(self, {"dataset": record}, 201)
                return
            if path == "/api/datasets/file-import":
                organization_id = self.headers.get("X-ASIE-Organization-Id", "") or (LEGACY_ORGANIZATION_ID if REPO.user_count() == 0 else "")
                if not organization_id or self._require_organization_permission(organization_id, "project.edit") is None:
                    return
                record = dataset_ingestion.import_file_dataset(REPO, payload | {"organization_id": organization_id})
                write_json(self, {"dataset": record}, 201)
                return
            if path.startswith("/api/datasets/"):
                if not self._require_dataset_permission(path.split("/")[3], "project.edit"):
                    return
                if path.endswith("/transformations"):
                    record = REPO.record_transformation(path.split("/")[3], payload)
                    write_json(self, {"transformation": record}, 201)
                    return
                if path.endswith("/review"):
                    record = REPO.review_dataset(path.split("/")[3], payload)
                    write_json(self, {"dataset": record})
                    return
            if path == "/api/sources/review-record":
                if self._require_platform_permission("platform.manage") is None:
                    return
                record = REPO.save_source_review(payload)
                write_json(self, {"source": record}, 201)
                return
            if path.startswith("/api/snapshots/") and path.endswith("/reviews"):
                snapshot_id = path.split("/")[3]
                if self._require_snapshot_permission(snapshot_id, "review.write") is None:
                    return
                review = REPO.save_snapshot_review(snapshot_id, payload)
                write_json(self, {"review": review}, 201)
                return
            if path.startswith("/api/projects/"):
                project_id = path.split("/")[3]
                permission = "project.run" if path.endswith("/runs") else "project.edit"
                if self._require_project_permission(project_id, permission) is None:
                    return
                if path.endswith("/runs"):
                    project = REPO.get_project(project_id)
                    if project is None:
                        write_error(self, "project_not_found", 404)
                        return
                    if "inputs" in payload:
                        project.inputs.update(payload["inputs"])
                    message = WorkflowRunMessage(WORKFLOW, project)
                    try:
                        module_outputs = message.run()
                    except RequestError as exc:
                        write_error(self, exc.code, exc.status)
                        return
                    overview = module_outputs["overview"]
                    report = build_report_projection(overview)
                    ids = REPO.save_run_snapshot(project.project_id, overview, report)
                    REPO.upsert_action_items(project.project_id, generate_action_items(overview, report))
                    publish_change("snapshot.created", {"project_id": project.project_id, "snapshot_id": ids["snapshot_id"]})
                    write_json(self, {"run_id": ids["run_id"], "snapshot_id": ids["snapshot_id"], "acceptance": overview["acceptance"]}, 201)
                    return
                if path.endswith("/assumptions"):
                    record = REPO.record_assumption(project_id, payload)
                    write_json(self, {"assumption": record}, 201)
                    return
                if path.endswith("/evidence-links"):
                    record = REPO.link_evidence(project_id, payload)
                    write_json(self, {"evidence_link": record}, 201)
                    return
            if path == "/api/projects":
                organization_id = self.headers.get("X-ASIE-Organization-Id", "") or (LEGACY_ORGANIZATION_ID if REPO.user_count() == 0 else "")
                if not organization_id or self._require_organization_permission(organization_id, "project.edit") is None:
                    return
                name = str(payload.get("name", "")).strip()
                if not name:
                    write_error(self, "invalid_project_payload", 422)
                    return
                project = REPO.create_project(
                    {
                        "name": name,
                        "sector": str(payload.get("sector", "")).strip(),
                        "jurisdiction": str(payload.get("jurisdiction", "Saudi Arabia")).strip() or "Saudi Arabia",
                        "inputs": payload.get("inputs", {}),
                        "organization_id": organization_id,
                    }
                )
                write_json(self, {"project": project.to_public()}, 201)
                return
            if path == "/api/exports/funder-report":
                snapshot_id = str(payload.get("snapshot_id", ""))
                export_format = str(payload.get("format", "pdf")).lower()
                if self._require_snapshot_permission(snapshot_id, "snapshot.read") is None:
                    return
                report = REPO.get_snapshot_report(snapshot_id)
                if report is None:
                    write_error(self, "snapshot_not_found", 404)
                    return
                projection = report["funder_report"]
                EXPORT_DIR.mkdir(parents=True, exist_ok=True)
                try:
                    if export_format == "pdf":
                        from backend.report_exports import export_funder_report_pdf

                        target = EXPORT_DIR / f"{snapshot_id}-funder-report.pdf"
                        export_funder_report_pdf(projection, target)
                    elif export_format == "docx":
                        from backend.report_exports import export_funder_report_docx

                        target = EXPORT_DIR / f"{snapshot_id}-funder-report.docx"
                        export_funder_report_docx(projection, target)
                    elif export_format == "xlsx":
                        from backend.report_exports import export_funder_report_xlsx

                        target = EXPORT_DIR / f"{snapshot_id}-funder-report.xlsx"
                        export_funder_report_xlsx(projection, target)
                    elif export_format == "pptx":
                        from backend.report_exports import export_funder_report_pptx

                        target = EXPORT_DIR / f"{snapshot_id}-funder-report.pptx"
                        export_funder_report_pptx(projection, target)
                    else:
                        write_error(self, "unsupported_export_format", 422)
                        return
                except Exception as exc:  # noqa: BLE001
                    write_error(self, f"export_failed:{exc}", 500)
                    return
                write_json(self, {"export_path": str(target)}, 201)
                return
            if path == "/api/snapshots/compare":
                first_id = str(payload.get("snapshot_a_id", ""))
                second_id = str(payload.get("snapshot_b_id", ""))
                if self._require_snapshot_permission(first_id) is None or self._require_snapshot_permission(second_id) is None:
                    return
                first = REPO.get_snapshot_overview(first_id)
                second = REPO.get_snapshot_overview(second_id)
                if first is None or second is None:
                    write_error(self, "snapshot_not_found", 404)
                    return
                write_json(self, compare_snapshots(first, second))
                return
        except json.JSONDecodeError:
            write_error(self, "invalid_json", 400)
            return
        except PermissionError as exc:
            write_error(self, str(exc), 422)
            return
        except RequestError as exc:
            write_error(self, exc.code, exc.status)
            return
        except ValueError as exc:
            write_error(self, str(exc), 422)
            return
        write_error(self, "not_found", 404)

    def do_PATCH(self) -> None:
        if not self._allow_request():
            return
        parsed = urlparse(self.path)
        path = parsed.path
        try:
            payload = self._read_json()
            if self._principal() is None:
                return
            if path.startswith("/api/sources/") and path.endswith("/review"):
                if self._require_platform_permission("platform.manage") is None:
                    return
                source_id = path.split("/")[3]
                payload["source_id"] = source_id
                record = REPO.save_source_review(payload)
                write_json(self, {"source": record})
                return
            if path.startswith("/api/projects/"):
                parts = path.split("/")
                if len(parts) == 4:
                    if self._require_project_permission(parts[3], "project.edit") is None:
                        return
                    project = REPO.update_project(parts[3], payload)
                    if project is None:
                        write_error(self, "project_not_found", 404)
                        return
                    write_json(self, {"project": project.to_public()})
                    return
                if len(parts) == 6 and parts[4] == "action-items":
                    if self._require_project_permission(parts[3], "review.write") is None:
                        return
                    item = update_action_item_status(REPO, parts[3], parts[5], str(payload.get("status", "")))
                    if item is None:
                        write_error(self, "action_item_not_found", 404)
                        return
                    write_json(self, {"item": item})
                    return
            write_error(self, "not_found", 404)
        except json.JSONDecodeError:
            write_error(self, "invalid_json", 400)
        except PermissionError as exc:
            write_error(self, str(exc), 422)
        except RequestError as exc:
            write_error(self, exc.code, exc.status)


def compare_snapshots(first: dict, second: dict) -> dict:
    first_snapshot = first["snapshot"]
    second_snapshot = second["snapshot"]
    deltas = {}
    for key in ("break_even_units", "payback_months", "npv", "decision_score"):
        first_value = first_snapshot.get(key)
        second_value = second_snapshot.get(key)
        if first_value is not None and second_value is not None:
            deltas[key] = second_value - first_value
    return {
        "first_snapshot_id": first_snapshot["snapshot_id"],
        "second_snapshot_id": second_snapshot["snapshot_id"],
        "deltas": deltas,
    }


def main() -> None:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer((API_HOST, API_PORT), Handler)
    print(f"ASIE local API listening on http://{API_HOST}:{API_PORT}")
    print(f"Runtime freeze scope: {RUNTIME_FREEZE_SCOPE}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
