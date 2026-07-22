from __future__ import annotations

import json
import sys
import threading
import time
from collections import defaultdict, deque
from copy import deepcopy
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import parse_qs, urlparse
from warnings import deprecated

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.acceptance import build_acceptance_pack
from backend.aas_kernel import AASKernel
from backend.architecture_status import build_architecture_runtime_status
from backend.bus_controller import BusController
from backend.contracts import HOST, PORT, PROFILE_ID, SCENARIO_ID, envelope, json_dumps, new_id, now_iso
from backend.intelligence_prerun_service import IntelligencePreRunService
from backend.datasets import dataset_quality_gate, normalize_file_import_payload
from backend.decision_pack import apply_review_overlay, build_action_items_from_overview, render_decision_pack_html
from backend.evidence_ledger import build_evidence_coverage
from backend.funding_readiness import profile_catalog, sector_profile_catalog
from backend.heart_controller import HeartController, HeartTask
from backend.module_runtime import ModuleRuntime, RunScopedModuleRuntime
from backend.operations import local_operational_health
from backend.project_run_workflow import (
    PROJECT_RUN_PIPELINE_CONTRACT_SEQUENCE_V1,
    ProjectRunEnvelope,
    ProjectRunIdempotencyStore,
    ProjectRunWorkflow,
    normalize_project_run_http_request,
)
from backend.readiness_gates import build_readiness_gates
from backend.identity import Principal
from backend.repository import LEGACY_ORGANIZATION_ID, ProjectRecord, Repository
from backend.reports import build_report_view, remediation, render_report_html, render_funder_report_html
from backend.report_release import build_release_record
from backend.release_info import release_info
from backend.runtime_freeze import BUILD_OVERVIEW_REMOVAL_TARGET
from backend.sector_intelligence import sector_taxonomy
from backend.source_registry import source_policy, source_review_checklist
from backend.system_bus import BusMessage, SystemBus
from backend.snapshot_assembly import canonical_hash, seal_projection_support
from backend.transformations import build_transformation_lineage
from backend.workflow import project_readiness
from backend.workspace import build_project_remediation, build_project_workspace, compare_snapshots

REPO = Repository()
RUN_IDEMPOTENCY_STORE = ProjectRunIdempotencyStore()
MAX_JSON_BODY_BYTES = 1_048_576
LOCAL_FRONTEND_ORIGINS = {"http://127.0.0.1:5194", "http://localhost:5194"}


class RequestError(ValueError):
    def __init__(self, code: str, status: int = 400) -> None:
        super().__init__(code)
        self.code = code
        self.status = status


class LocalRateLimiter:
    """Process-local guard for the loopback API; it retains no request content."""

    def __init__(self, *, maximum: int = 120, window_seconds: int = 60) -> None:
        self.maximum = maximum
        self.window_seconds = window_seconds
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            events = self._events[key]
            while events and events[0] <= now - self.window_seconds:
                events.popleft()
            if len(events) >= self.maximum:
                return False
            events.append(now)
            return True


REQUEST_RATE_LIMITER = LocalRateLimiter()
@dataclass(frozen=True)
class LocalAASRuntimeContext:
    kernel: AASKernel
    heart_controller: HeartController
    bus_controller: BusController
    bus: SystemBus
    runtime: ModuleRuntime


_LOCAL_RUNTIME_CONTEXT: LocalAASRuntimeContext | None = None
_LOCAL_RUNTIME_BOOT_COUNT = 0
BUILD_OVERVIEW_DEPRECATION_MESSAGE = (
    "Compatibility wrapper for legacy parity tests only; remove in AAS Runtime v1.1 "
    "after legacy parity fixtures migrate"
)


class ProjectRunDataAccess(Protocol):
    def project_assumptions(self, project_id: str) -> list[dict[str, Any]]: ...

    def source_records(self) -> list[dict[str, Any]]: ...

    def project_evidence_links(self, project_id: str) -> list[dict[str, Any]]: ...

    def datasets(self) -> list[dict[str, Any]]: ...

    def project_transformations(self, project_id: str) -> list[dict[str, Any]]: ...


def output_set(project: ProjectRecord, run_id: str, snapshot_id: str, finance: dict[str, Any]) -> list[dict[str, Any]]:
    baseline = finance["baseline"]
    if baseline is None:
        return [
            envelope(
                project=project,
                run_id=run_id,
                snapshot_id=snapshot_id,
                output_id=output_id,
                owner_module="Finance Engine",
                contract_id="finance.result.v1",
                algorithm_id=algorithm_id,
                value_type=value_type,
                value=None,
                unit=unit,
                period=period,
                status="needs_input",
                formula_ref=f"NOT_READY:{output_id}",
            )
            for output_id, algorithm_id, value_type, unit, period in [
                ("startup-cost", "FIN-ALG-01", "calculated", "SAR", "startup"),
                ("monthly-revenue", "FIN-ALG-01", "calculated", "SAR", "monthly"),
                ("monthly-profit", "FIN-ALG-01", "calculated", "SAR", "monthly"),
                ("npv", "FIN-ALG-06", "calculated", "SAR", "5-year"),
                ("irr", "FIN-ALG-07", "calculated", "percent", "5-year"),
                ("payback-months", "FIN-ALG-10", "calculated", "months", "run"),
                ("working-capital-need", "FIN-ALG-08", "calculated", "SAR", "startup"),
                ("ebitda", "FIN-ALG-13", "calculated", "SAR", "monthly"),
                ("ebit", "FIN-ALG-13", "calculated", "SAR", "monthly"),
                ("dscr", "FIN-ALG-13", "calculated", "ratio", "annual"),
                ("funding-need-after-equity", "FIN-ALG-13", "calculated", "SAR", "startup"),
                ("mc-feasibility-gate-probability", "FIN-ALG-04", "simulation", "percent", "run"),
            ]
        ]

    mc = finance["monte_carlo"]
    assumption_refs = finance["assumption_refs"]
    rows = [
        ("startup-cost", "FIN-ALG-01", baseline["startup_cost"], "SAR", "startup", "startup_cost=user_verified_input"),
        ("monthly-revenue", "FIN-ALG-01", baseline["revenue"], "SAR", "monthly", "Revenue=unit_price*monthly_units"),
        (
            "monthly-profit",
            "FIN-ALG-01",
            baseline["monthly_profit"],
            "SAR",
            "monthly",
            "Profit=revenue-variable_costs-fixed_costs",
        ),
        ("break-even-units", "FIN-ALG-09", baseline["break_even_units"], "count", "monthly", "fixed_cost/contribution"),
        ("funding-gap", "FIN-ALG-08", baseline["funding_gap"], "SAR", "startup", "max(0,initial_investment-revenue)"),
        ("working-capital-need", "FIN-ALG-08", baseline["working_capital_need"], "SAR", "startup", "operating cash buffer"),
        ("ebitda", "FIN-ALG-13", baseline["ebitda"], "SAR", "monthly", "gross_profit-total_monthly_opex"),
        ("ebit", "FIN-ALG-13", baseline["ebit"], "SAR", "monthly", "EBITDA-depreciation"),
        (
            "net-operating-cashflow",
            "FIN-ALG-13",
            baseline["net_operating_cashflow"],
            "SAR",
            "monthly",
            "EBITDA-debt_service_monthly",
        ),
        (
            "funding-need-after-equity",
            "FIN-ALG-13",
            baseline["funding_need_after_equity"],
            "SAR",
            "startup",
            "max(0,initial_investment-equity_contribution)",
        ),
        ("npv", "FIN-ALG-06", baseline["npv"], "SAR", "5-year", "discounted annual cashflows"),
        ("irr", "FIN-ALG-07", baseline["irr"], "percent", "5-year", "rate where NPV approaches zero"),
        ("payback-months", "FIN-ALG-10", baseline["payback_months"], "months", "run", "initial_investment/monthly_profit"),
        (
            "contribution-margin",
            "FIN-ALG-11",
            baseline["contribution_margin"],
            "percent",
            "monthly",
            "(price-variable_cost)/price",
        ),
        (
            "debt-service-monthly",
            "FIN-ALG-08",
            baseline["debt_service_monthly"],
            "SAR",
            "monthly",
            "amortized payment placeholder when debt input exists",
        ),
        (
            "dscr",
            "FIN-ALG-13",
            baseline["dscr"],
            "ratio",
            "annual",
            "annual EBITDA / annual debt service",
        ),
        (
            "depreciation-monthly",
            "FIN-ALG-13",
            baseline["depreciation_monthly"],
            "SAR",
            "monthly",
            "capex/depreciation_months",
        ),
    ]
    kpis = [
        envelope(
            project=project,
            run_id=run_id,
            snapshot_id=snapshot_id,
            output_id=output_id,
            owner_module="Finance Engine",
            contract_id="finance.result.v1",
            algorithm_id=algorithm_id,
            value_type="calculated",
            value=value,
            unit=unit,
            period=period,
            status="ready" if value is not None else "needs_input",
            formula_ref=formula_ref,
            assumption_refs=assumption_refs,
        )
        for output_id, algorithm_id, value, unit, period, formula_ref in rows
    ]
    kpis.append(
        envelope(
            project=project,
            run_id=run_id,
            snapshot_id=snapshot_id,
            output_id="mc-feasibility-gate-probability",
            owner_module="Finance Engine",
            contract_id="finance.mcmc.result.v1",
            algorithm_id="FIN-ALG-04",
            value_type="simulation",
            value=mc["p_pass"],
            unit="percent",
            period="run",
            status="ready" if mc["status"] == "ready" else "needs_input",
            confidence=0.68 if mc["status"] == "ready" else None,
            confidence_basis="fixed_seed_local_distributions" if mc["status"] == "ready" else "missing_inputs",
            formula_ref="P_pass=valid simulations passing deterministic feasibility gates / valid simulations",
            assumption_refs=assumption_refs if mc["status"] == "ready" else [],
        )
    )
    return kpis


def local_runtime_context() -> LocalAASRuntimeContext:
    global _LOCAL_RUNTIME_CONTEXT, _LOCAL_RUNTIME_BOOT_COUNT
    if _LOCAL_RUNTIME_CONTEXT is not None:
        return _LOCAL_RUNTIME_CONTEXT
    kernel = AASKernel()
    kernel.boot()
    heart_controller = HeartController(kernel)
    heart_controller.bootstrap()
    bus_controller = BusController(kernel, heart_controller)
    bus_controller.bootstrap()
    bus = SystemBus(bus_controller)
    bus.bootstrap()
    runtime = ModuleRuntime(kernel, bus)
    runtime.bootstrap()
    runtime.register_default_handlers()
    _LOCAL_RUNTIME_CONTEXT = LocalAASRuntimeContext(
        kernel=kernel,
        heart_controller=heart_controller,
        bus_controller=bus_controller,
        bus=bus,
        runtime=runtime,
    )
    _LOCAL_RUNTIME_BOOT_COUNT += 1
    return _LOCAL_RUNTIME_CONTEXT


def local_module_runtime() -> ModuleRuntime:
    return local_runtime_context().runtime


def local_runtime_boot_count() -> int:
    return _LOCAL_RUNTIME_BOOT_COUNT


def reset_local_module_runtime_for_tests() -> None:
    global _LOCAL_RUNTIME_CONTEXT, _LOCAL_RUNTIME_BOOT_COUNT
    _LOCAL_RUNTIME_CONTEXT = None
    _LOCAL_RUNTIME_BOOT_COUNT = 0


def source_module_for_session(session: RunScopedModuleRuntime | None) -> str:
    return session.source_module_id if session else "aas.heart_controller"


def envelope_for_session(session: RunScopedModuleRuntime | None) -> dict[str, str]:
    if session is None:
        return {}
    return {
        "operation_id": session.operation_id,
        "idempotency_key": session.idempotency_key,
        "input_hash": session.input_hash,
    }


def heart_source_module_id(assignment: dict[str, Any]) -> str:
    assigned = assignment.get("assignments", [])
    if not assigned:
        raise ValueError("heart_assignment_failed:no_assignment")
    return f"aas.heart.{assigned[0]['heart_id']}"


def finance_via_module_runtime(
    project: ProjectRecord,
    *,
    run_id: str,
    snapshot_id: str,
    assumption_refs: list[str] | None = None,
    session: RunScopedModuleRuntime | None = None,
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    message = BusMessage(
            source_module_id=source_module_for_session(session),
            target_module_id="module.finance",
            contract_id="finance.calculate.v1",
            socket_id="socket.finance.evaluate",
            correlation_id=f"corr:{run_id}:finance",
            audit_ref=f"audit:{snapshot_id}:finance-runtime",
            **envelope_for_session(session),
            payload={
                "project_id": project.project_id,
                "run_id": run_id,
                "snapshot_id": snapshot_id,
                "inputs": project.inputs,
                "assumption_refs": assumption_refs or [],
            },
    )
    result = session.execute_and_seal("finance_result", message) if session else local_module_runtime().execute(message)
    output = result.output
    return output["finance"], output["blockers"]


def evidence_ledger_via_module_runtime(
    *,
    project_id: str,
    evidence_register: dict[str, Any],
    source_records: list[dict[str, Any]],
    snapshot_id: str,
    run_id: str | None,
    transformations: list[dict[str, Any]],
    session: RunScopedModuleRuntime | None = None,
) -> list[dict[str, Any]]:
    message = BusMessage(
            source_module_id=source_module_for_session(session),
            target_module_id="module.evidence_ledger",
            contract_id="evidence.ledger.build.v1",
            socket_id="socket.evidence.ledger",
            correlation_id=f"corr:{run_id or 'draft'}:evidence-ledger",
            audit_ref=f"audit:{snapshot_id}:evidence-ledger-runtime",
            **envelope_for_session(session),
            payload={
                "project_id": project_id,
                "snapshot_id": snapshot_id,
                "run_id": run_id,
                "evidence_register": evidence_register,
                "source_records": source_records,
                "transformations": transformations,
            },
    )
    result = session.execute_and_seal("evidence_ledger", message) if session else local_module_runtime().execute(message)
    return result.output["evidence_ledger"]


def sector_intelligence_via_module_runtime(
    project: ProjectRecord,
    *,
    evidence_register: dict[str, Any],
    source_records: list[dict[str, Any]],
    snapshot_id: str,
    run_id: str | None,
    session: RunScopedModuleRuntime | None = None,
) -> dict[str, Any]:
    message = BusMessage(
            source_module_id=source_module_for_session(session),
            target_module_id="module.sector_intelligence",
            contract_id="sector.intelligence.build.v1",
            socket_id="socket.sector.intelligence",
            correlation_id=f"corr:{run_id or 'draft'}:sector-intelligence",
            audit_ref=f"audit:{snapshot_id}:sector-intelligence-runtime",
            **envelope_for_session(session),
            payload={
                "project_id": project.project_id,
                "snapshot_id": snapshot_id,
                "run_id": run_id,
                "project_name": project.name,
                "project_sector": project.sector,
                "project_jurisdiction": project.jurisdiction,
                "inputs": project.inputs,
                "evidence_register": evidence_register,
                "source_records": source_records,
            },
    )
    result = session.execute_and_seal("sector_intelligence", message) if session else local_module_runtime().execute(message)
    return result.output["sector_intelligence"]


def decision_council_via_module_runtime(
    *,
    project_id: str,
    run_id: str,
    snapshot_id: str,
    finance: dict[str, Any],
    blockers: list[dict[str, Any]],
    readiness_gates: dict[str, Any],
    sector_intelligence: dict[str, Any],
    session: RunScopedModuleRuntime | None = None,
) -> dict[str, Any]:
    message = BusMessage(
            source_module_id=source_module_for_session(session),
            target_module_id="module.decision_council",
            contract_id="decision.council.evaluate.v1",
            socket_id="socket.decision.council",
            correlation_id=f"corr:{run_id}:decision-council",
            audit_ref=f"audit:{snapshot_id}:decision-council-runtime",
            **envelope_for_session(session),
            payload={
                "project_id": project_id,
                "run_id": run_id,
                "snapshot_id": snapshot_id,
                "input_contract_id": "DecisionCouncilInputEnvelope.v1",
                "finance": finance,
                "blockers": blockers,
                "readiness_gates": readiness_gates,
                "sector_intelligence": sector_intelligence,
            },
    )
    result = session.execute_and_seal("decision_result", message) if session else local_module_runtime().execute(message)
    return result.output["decision_council"]


def risk_register_via_module_runtime(
    *,
    project_id: str,
    run_id: str,
    snapshot_id: str,
    finance: dict[str, Any],
    evidence_register: dict[str, Any],
    source_policy_result: dict[str, Any],
    readiness_gates: dict[str, Any],
    session: RunScopedModuleRuntime | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    message = BusMessage(
            source_module_id=source_module_for_session(session),
            target_module_id="module.risk_engine",
            contract_id="risk.register.build.v1",
            socket_id="socket.risk.register",
            correlation_id=f"corr:{run_id}:risk-register",
            audit_ref=f"audit:{snapshot_id}:risk-runtime",
            **envelope_for_session(session),
            payload={
                "project_id": project_id,
                "run_id": run_id,
                "snapshot_id": snapshot_id,
                "input_contract_id": "RiskRegisterInputEnvelope.v1",
                "finance": finance,
                "evidence_register": evidence_register,
                "source_policy": source_policy_result,
                "readiness_gates": readiness_gates,
            },
    )
    result = session.execute_and_seal("risk_result", message) if session else local_module_runtime().execute(message)
    return result.output["risk_register"], result.output["risk_advisory_summary"]


def execution_plan_via_module_runtime(
    *,
    project_id: str,
    run_id: str,
    snapshot_id: str,
    finance: dict[str, Any],
    decision_council: dict[str, Any],
    readiness_gates: dict[str, Any],
    risk_advisory_summary: dict[str, Any],
    session: RunScopedModuleRuntime | None = None,
) -> dict[str, Any]:
    message = BusMessage(
            source_module_id=source_module_for_session(session),
            target_module_id="module.execution_engine",
            contract_id="execution.plan.build.v1",
            socket_id="socket.execution.plan",
            correlation_id=f"corr:{run_id}:execution-plan",
            audit_ref=f"audit:{snapshot_id}:execution-runtime",
            **envelope_for_session(session),
            payload={
                "project_id": project_id,
                "run_id": run_id,
                "snapshot_id": snapshot_id,
                "input_contract_id": "ExecutionPlanInputEnvelope.v1",
                "finance": finance,
                "decision_council": decision_council,
                "readiness_gates": readiness_gates,
                "risk_advisory_summary": risk_advisory_summary,
            },
    )
    result = session.execute_and_seal("execution_result", message) if session else local_module_runtime().execute(message)
    return result.output["execution_plan"]


def report_via_module_runtime(
    overview: dict[str, Any],
    runtime: ModuleRuntime | None = None,
    source_module_id: str = "aas.heart_controller",
    operation_id: str = "",
    idempotency_key: str = "",
    input_hash: str = "",
) -> dict[str, Any]:
    active_runtime = runtime or local_module_runtime()
    result = active_runtime.execute(
        BusMessage(
            source_module_id=source_module_id,
            target_module_id="module.reports",
            contract_id="report.snapshot.project.v1",
            socket_id="socket.report.snapshot",
            correlation_id=f"corr:{overview['run']['run_id']}:report",
            audit_ref=f"audit:{overview['snapshot']['snapshot_id']}:report-runtime",
            operation_id=operation_id or f"op:{overview['run']['run_id']}:report",
            idempotency_key=idempotency_key or f"idem:{overview['snapshot']['snapshot_id']}:report",
            input_hash=input_hash or canonical_hash(
                {
                    "projection": "report",
                    "run_id": overview["run"]["run_id"],
                    "snapshot_id": overview["snapshot"]["snapshot_id"],
                }
            ),
            payload={
                "project_id": overview["project"]["project_id"],
                "run_id": overview["run"]["run_id"],
                "snapshot_id": overview["snapshot"]["snapshot_id"],
                "input_contract_id": "SnapshotReportInputEnvelope.v1",
                "overview": overview,
            },
        )
    )
    return result.output["report"]


def decision_pack_via_module_runtime(
    snapshot_overview: dict[str, Any],
    snapshot_report: dict[str, Any],
) -> dict[str, Any]:
    runtime = local_module_runtime()
    operation_id = f"op:{snapshot_overview['run']['run_id']}:decision-pack"
    idempotency_key = f"idem:{snapshot_overview['snapshot']['snapshot_id']}:decision-pack"
    input_hash = canonical_hash(
        {
            "projection": "decision_pack",
            "run_id": snapshot_overview["run"]["run_id"],
            "snapshot_id": snapshot_overview["snapshot"]["snapshot_id"],
            "report_snapshot_id": snapshot_report["snapshot_id"],
        }
    )
    result = runtime.execute(
        BusMessage(
            source_module_id="aas.heart_controller",
            target_module_id="module.decision_pack",
            contract_id="decision.pack.project.v1",
            socket_id="socket.decision.pack",
            correlation_id=f"corr:{snapshot_overview['run']['run_id']}:decision-pack",
            audit_ref=f"audit:{snapshot_overview['snapshot']['snapshot_id']}:decision-pack-runtime",
            operation_id=operation_id,
            idempotency_key=idempotency_key,
            input_hash=input_hash,
            payload={
                "project_id": snapshot_overview["project"]["project_id"],
                "run_id": snapshot_overview["run"]["run_id"],
                "snapshot_id": snapshot_overview["snapshot"]["snapshot_id"],
                "input_contract_id": "DecisionPackInputEnvelope.v1",
                "snapshot_overview": snapshot_overview,
                "snapshot_report": snapshot_report,
            },
        )
    )
    return result.output["decision_pack"]


def project_overview_from_assembled_snapshot(assembled: dict[str, Any]) -> dict[str, Any]:
    support_envelope = assembled.get("supporting_outputs", {}).get("projection_support")
    if not support_envelope:
        raise ValueError("assembled snapshot is missing sealed projection support")
    support = support_envelope.get("projection_support")
    if not isinstance(support, dict):
        raise ValueError("assembled snapshot projection support is invalid")
    required_support = {
        "project",
        "run",
        "snapshot",
        "kpis",
        "blockers",
        "source_policy",
        "evidence_coverage",
        "transformation_lineage",
        "assumption_book",
        "evidence_register",
        "readiness_gates",
        "readiness",
        "remediation_envelopes",
        "audit",
        "acceptance",
    }
    missing_support = required_support - set(support)
    if missing_support:
        raise ValueError("sealed projection support is missing fields: " + ", ".join(sorted(missing_support)))

    outputs = assembled["module_outputs"]
    finance = deepcopy(outputs["finance_result"]["finance"])
    decision_council = deepcopy(outputs["decision_result"]["decision_council"])
    risk_output = outputs["risk_result"]
    snapshot = deepcopy(support["snapshot"])
    snapshot.update(
        {
            "snapshot_version": assembled["snapshot_version"],
            "assembled_at": assembled["assembled_at"],
            "content_hash": assembled["content_hash"],
            "integrity_hash": assembled["integrity_hash"],
        }
    )
    overview = {
        "project": deepcopy(support["project"]),
        "run": deepcopy(support["run"]),
        "snapshot": snapshot,
        "finance": finance,
        "decision_council": decision_council,
        "decision": deepcopy(decision_council["verdict"]),
        "monte_carlo": deepcopy(finance["monte_carlo"]),
        "personas": deepcopy(decision_council["personas"]),
        "kpis": deepcopy(support["kpis"]),
        "blockers": deepcopy(support["blockers"]),
        "source_policy": deepcopy(support["source_policy"]),
        "sector_intelligence": deepcopy(outputs["sector_intelligence"]["sector_intelligence"]),
        "evidence_ledger": deepcopy(outputs["evidence_ledger"]["evidence_ledger"]),
        "evidence_coverage": deepcopy(support["evidence_coverage"]),
        "transformation_lineage": deepcopy(support["transformation_lineage"]),
        "assumption_book": deepcopy(support["assumption_book"]),
        "evidence_register": deepcopy(support["evidence_register"]),
        "readiness_gates": deepcopy(support["readiness_gates"]),
        "execution_plan": deepcopy(outputs["execution_result"]["execution_plan"]),
        "risk_register": deepcopy(risk_output["risk_register"]),
        "risk_advisory_summary": deepcopy(risk_output["risk_advisory_summary"]),
        "readiness": deepcopy(support["readiness"]),
        "remediation_envelopes": deepcopy(support["remediation_envelopes"]),
        "audit": deepcopy(support["audit"]),
        "acceptance": deepcopy(support["acceptance"]),
        "snapshot_assembly": {
            "contract_id": assembled["assembly_contract_id"],
            "snapshot_version": assembled["snapshot_version"],
            "assembled_at": assembled["assembled_at"],
            "content_hash": assembled["content_hash"],
            "integrity_hash": assembled["integrity_hash"],
            "lineage": deepcopy(assembled["lineage"]),
            "correlation_map": deepcopy(assembled["correlation_map"]),
            "projection_source": "immutable_assembled_snapshot",
        },
    }
    overview["audit"]["snapshot_assembly_ref"] = f"assembly:{assembled['snapshot_id']}:{assembled['integrity_hash']}"
    overview["snapshot_assembly"]["overview_projection_hash"] = canonical_hash(overview)
    return overview


def execute_project_run_pipeline(
    run_envelope: ProjectRunEnvelope,
    *,
    project: ProjectRecord,
    data_access: ProjectRunDataAccess,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not isinstance(run_envelope, ProjectRunEnvelope):
        raise TypeError("execute_project_run_pipeline requires ProjectRunEnvelope")
    if run_envelope.project_id != project.project_id:
        raise ValueError("project run envelope project_id mismatch")
    if run_envelope.pipeline_contract_sequence != PROJECT_RUN_PIPELINE_CONTRACT_SEQUENCE_V1:
        raise ValueError("unsupported project run pipeline contract sequence")
    run_id = run_envelope.run_id
    snapshot_id = run_envelope.snapshot_id
    created_at = now_iso()
    assumptions = data_access.project_assumptions(project.project_id)
    runtime = local_module_runtime()
    session = RunScopedModuleRuntime(
        runtime,
        project_id=project.project_id,
        run_id=run_id,
        snapshot_id=snapshot_id,
        source_module_id=run_envelope.source_module_id,
        operation_id=run_envelope.operation_id,
        idempotency_key=run_envelope.idempotency_key,
        input_hash=run_envelope.input_hash,
    )
    finance, input_blockers = finance_via_module_runtime(
        project,
        run_id=run_id,
        snapshot_id=snapshot_id,
        assumption_refs=[row["assumption_id"] for row in assumptions],
        session=session,
    )
    sources = data_access.source_records()
    policy = source_policy(sources, PROFILE_ID)
    blockers = list(input_blockers)
    blockers.extend(
        [
            {
                "code": "DEMO_OR_USER_INPUT_ONLY",
                "severity": "high",
                "message": "النتائج محسوبة من مدخلات محلية/تجريبية وليست من مصدر رسمي مفتوح مفعّل.",
            },
            {
                "code": "OPEN_DATA_NOT_ENABLED",
                "severity": "medium",
                "message": "لا يوجد مصدر خارجي مفعّل حتى تكتمل مراجعة الشروط والنسبة والتصنيف.",
            },
        ]
    )
    kpis = output_set(project, run_id, snapshot_id, finance)
    audit = {
        "audit_id": f"audit_{snapshot_id}",
        "run_id": run_id,
        "snapshot_id": snapshot_id,
        "profile_id": PROFILE_ID,
        "owner_path": "ProjectRunWorkflow -> execute_project_run_pipeline -> RunScopedModuleRuntime",
        "forbidden_paths": [
            "React finance calculation",
            "AI-owned controlled numbers",
            "direct source fetch without enabled source review",
            "persona voting for Sovereign Verdict",
        ],
        "output_audit_refs": [item["audit_ref"] for item in kpis],
        "algorithm_versions": sorted({item["algorithm_id"]: item["algorithm_version"] for item in kpis}.items()),
        "source_fetch_enabled": False,
        "runtime_source_module_id": run_envelope.source_module_id,
        "pipeline_policy_id": run_envelope.pipeline_policy_id,
    }
    evidence_register = build_evidence_register(data_access, project.project_id, snapshot_id, sources)
    sector_intelligence = sector_intelligence_via_module_runtime(
        project,
        evidence_register=evidence_register,
        source_records=sources,
        snapshot_id=snapshot_id,
        run_id=run_id,
        session=session,
    )
    transformations = evidence_register.get("transformations", [])
    evidence_ledger = evidence_ledger_via_module_runtime(
        project_id=project.project_id,
        evidence_register=evidence_register,
        source_records=sources,
        snapshot_id=snapshot_id,
        run_id=run_id,
        transformations=transformations,
        session=session,
    )
    transformation_lineage = build_transformation_lineage(evidence_ledger, transformations)
    evidence_coverage = build_evidence_coverage(assumptions, sector_intelligence, evidence_ledger)
    if sector_intelligence["status"] != "ready":
        blockers.append(
            {
                "code": "SECTOR_CLASSIFICATION_NEEDS_INPUT",
                "severity": "medium",
                "message": "التصنيف القطاعي الرسمي غير مكتمل؛ تظهر مؤشرات القطاع كفجوات أدلة حتى يتم اختياره.",
            }
        )
    readiness_gates = build_readiness_gates(finance, blockers, evidence_register, policy)
    decision_council = decision_council_via_module_runtime(
        project_id=project.project_id,
        run_id=run_id,
        snapshot_id=snapshot_id,
        finance=finance,
        blockers=blockers,
        readiness_gates=readiness_gates,
        sector_intelligence=sector_intelligence,
        session=session,
    )
    risk_register, risk_advisory_summary = risk_register_via_module_runtime(
        project_id=project.project_id,
        run_id=run_id,
        snapshot_id=snapshot_id,
        finance=finance,
        evidence_register=evidence_register,
        source_policy_result=policy,
        readiness_gates=readiness_gates,
        session=session,
    )
    execution_plan = execution_plan_via_module_runtime(
        project_id=project.project_id,
        run_id=run_id,
        snapshot_id=snapshot_id,
        finance=finance,
        decision_council=decision_council,
        readiness_gates=readiness_gates,
        risk_advisory_summary=risk_advisory_summary,
        session=session,
    )
    provisional_overview = {
        "project": project.to_public()
        | {
            "run_id": run_id,
            "snapshot_id": snapshot_id,
            "data_badge": "USER_VERIFIED" if finance["status"] == "ready" else "DEMO_DATA",
            "data_mode": "user_verified" if finance["status"] == "ready" else "demo_simulated_external",
            "display_badge": "USER VERIFIED" if finance["status"] == "ready" else "DEMO / LOCAL ONLY",
            "production_admission": "local_only" if finance["status"] == "ready" else "blocked",
            "status": "local_snapshot_ready" if finance["status"] == "ready" else "needs_input",
        },
        "run": {
            "run_id": run_id,
            "scenario_id": run_envelope.scenario_id,
            "status": "completed" if finance["status"] == "ready" else "blocked",
            "created_at": created_at,
        },
        "snapshot": {
            "snapshot_id": snapshot_id,
            "immutable": True,
            "created_at": created_at,
        },
        "finance": finance,
        "decision_council": decision_council,
        "decision": decision_council["verdict"],
        "monte_carlo": finance["monte_carlo"],
        "personas": decision_council["personas"],
        "kpis": kpis,
        "blockers": blockers,
        "source_policy": policy,
        "sector_intelligence": sector_intelligence,
        "evidence_ledger": evidence_ledger,
        "evidence_coverage": evidence_coverage,
        "transformation_lineage": transformation_lineage,
        "assumption_book": assumptions,
        "evidence_register": evidence_register,
        "readiness_gates": readiness_gates,
        "execution_plan": execution_plan,
        "risk_register": risk_register,
        "risk_advisory_summary": risk_advisory_summary,
        "readiness": project_readiness(project, assumptions, sources),
        "remediation_envelopes": remediation(blockers),
        "audit": audit,
    }
    provisional_overview["acceptance"] = build_acceptance_pack(provisional_overview)
    provisional_overview["audit"]["acceptance_status"] = provisional_overview["acceptance"]["status"]
    provisional_overview["audit"]["acceptance_id"] = provisional_overview["acceptance"]["acceptance_id"]
    module_projection_fields = {
        "finance",
        "decision_council",
        "decision",
        "monte_carlo",
        "personas",
        "sector_intelligence",
        "evidence_ledger",
        "execution_plan",
        "risk_register",
        "risk_advisory_summary",
    }
    projection_support = {
        key: deepcopy(value)
        for key, value in provisional_overview.items()
        if key not in module_projection_fields
    }
    sealed_projection_support = seal_projection_support(
        project_id=project.project_id,
        run_id=run_id,
        snapshot_id=snapshot_id,
        correlation_id=f"corr:{run_id}:projection-support",
        audit_ref=f"audit:{snapshot_id}:projection-support",
        produced_at=created_at,
        projection_support=projection_support,
    )
    assembled = session.assemble(
        project_context={
            "project_id": project.project_id,
            "name": project.name,
            "sector": project.sector,
            "jurisdiction": project.jurisdiction,
        },
        readiness_state={
            "workflow": projection_support["readiness"].get("status"),
            "gates": readiness_gates.get("status"),
            "run": projection_support["run"]["status"],
        },
        blockers=blockers,
        sealed_supporting_outputs=[sealed_projection_support],
    ).output["assembled_snapshot"]
    overview = project_overview_from_assembled_snapshot(assembled)
    report = report_via_module_runtime(
        overview,
        runtime=runtime,
        source_module_id=run_envelope.source_module_id,
        operation_id=run_envelope.operation_id,
        idempotency_key=run_envelope.idempotency_key,
        input_hash=run_envelope.input_hash,
    )
    return overview, report


@deprecated(BUILD_OVERVIEW_DEPRECATION_MESSAGE)
def build_overview(
    project: ProjectRecord,
    repo: Repository,
    *,
    source_module_id: str = "aas.heart_controller",
    operation_id: str = "",
    idempotency_key: str = "",
    input_hash: str = "",
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Legacy parity wrapper; never use from HTTP routes or ProjectRunWorkflow."""
    if not isinstance(project, ProjectRecord):
        raise TypeError("build_overview accepts legacy ProjectRecord fixtures only")
    if not isinstance(repo, Repository):
        raise TypeError("build_overview accepts legacy Repository fixtures only")
    run_id = new_id("run")
    snapshot_id = new_id("snap")
    compatibility_envelope = ProjectRunEnvelope(
        project_id=project.project_id,
        scenario_id=SCENARIO_ID,
        operation_id=operation_id or f"op:{run_id}:compatibility-run",
        idempotency_key=idempotency_key or f"idem:{run_id}:compatibility-run",
        input_hash=input_hash
        or canonical_hash(
            {
                "project_id": project.project_id,
                "run_id": run_id,
                "scenario_id": SCENARIO_ID,
                "snapshot_id": snapshot_id,
            }
        ),
        run_id=run_id,
        snapshot_id=snapshot_id,
        source_module_id=source_module_id,
    )
    return execute_project_run_pipeline(
        compatibility_envelope,
        project=project,
        data_access=repo,
    )


def build_evidence_register(
    repo: ProjectRunDataAccess,
    project_id: str,
    snapshot_id: str,
    sources: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    source_records = sources if sources is not None else repo.source_records()
    source_by_id = {row["source_id"]: row for row in source_records}
    links = repo.project_evidence_links(project_id)
    linked_dataset_ids = {row["dataset_id"] for row in links}
    datasets = [
        row for row in repo.datasets() if row["dataset_id"] in linked_dataset_ids or row["review_status"] != "archived"
    ]
    gates = [dataset_quality_gate(row, source_by_id.get(row["source_id"])) for row in datasets]
    return {
        "evidence_register_id": f"evidence_{snapshot_id}",
        "snapshot_id": snapshot_id,
        "source_records": source_records,
        "source_checklists": [source_review_checklist(row) for row in source_records],
        "datasets": datasets,
        "transformations": repo.project_transformations(project_id),
        "evidence_links": links,
        "linked_dataset_ids": sorted(linked_dataset_ids),
        "quality_gates": gates,
        "not_ready_reasons": [
            f"{gate['dataset_id']}:{reason}"
            for gate in gates
            if gate["status"] != "passed" and gate["dataset_id"] in linked_dataset_ids
            for reason in gate["reasons"]
        ],
        "external_fetch_enabled": False,
    }


def build_project_evidence_state(
    repo: Repository,
    project: ProjectRecord,
    snapshot_id: str,
    run_id: str | None,
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    sources = repo.source_records()
    assumptions = repo.project_assumptions(project.project_id)
    evidence_register = build_evidence_register(repo, project.project_id, snapshot_id, sources)
    sector = sector_intelligence_via_module_runtime(
        project,
        evidence_register=evidence_register,
        source_records=sources,
        snapshot_id=snapshot_id,
        run_id=run_id,
    )
    transformations = evidence_register.get("transformations", [])
    ledger = evidence_ledger_via_module_runtime(
        project_id=project.project_id,
        evidence_register=evidence_register,
        source_records=sources,
        snapshot_id=snapshot_id,
        run_id=run_id,
        transformations=transformations,
    )
    coverage = build_evidence_coverage(assumptions, sector, ledger)
    return evidence_register, sector, ledger, coverage


def read_json(handler: BaseHTTPRequestHandler) -> dict[str, Any]:
    try:
        length = int(handler.headers.get("Content-Length", "0") or 0)
    except ValueError as exc:
        raise RequestError("invalid_content_length") from exc
    if length < 0:
        raise RequestError("invalid_content_length")
    if length > MAX_JSON_BODY_BYTES:
        raise RequestError("request_body_too_large", 413)
    if length == 0:
        return {}
    try:
        raw = handler.rfile.read(length).decode("utf-8")
        payload = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RequestError("invalid_json") from exc
    if not isinstance(payload, dict):
        raise RequestError("json_object_required")
    return payload


def _write_security_headers(handler: BaseHTTPRequestHandler) -> None:
    origin = handler.headers.get("Origin")
    if origin in LOCAL_FRONTEND_ORIGINS:
        handler.send_header("Access-Control-Allow-Origin", origin)
        handler.send_header("Vary", "Origin")
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, OPTIONS")
    handler.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type, X-ASIE-Organization-Id, X-Request-Id")
    handler.send_header("Access-Control-Max-Age", "600")
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("X-Content-Type-Options", "nosniff")
    handler.send_header("X-Frame-Options", "DENY")
    handler.send_header("Referrer-Policy", "no-referrer")
    handler.send_header("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
    handler.send_header("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'; base-uri 'none'")
    request_id = getattr(handler, "request_id", None)
    if request_id:
        handler.send_header("X-Request-Id", request_id)


def write_json(handler: BaseHTTPRequestHandler, payload: dict[str, Any], status: int = 200) -> None:
    raw = json_dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(raw)))
    _write_security_headers(handler)
    handler.end_headers()
    handler.wfile.write(raw)


def write_html(handler: BaseHTTPRequestHandler, payload: str, status: int = 200) -> None:
    raw = payload.encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "text/html; charset=utf-8")
    handler.send_header("Content-Length", str(len(raw)))
    _write_security_headers(handler)
    handler.end_headers()
    handler.wfile.write(raw)


def write_error(handler: BaseHTTPRequestHandler, message: str, status: int) -> None:
    write_json(handler, {"error": message, "status": status, "request_id": getattr(handler, "request_id", None)}, status)


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
