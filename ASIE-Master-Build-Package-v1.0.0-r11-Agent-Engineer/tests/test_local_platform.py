from __future__ import annotations

import base64
import io
import tempfile
import threading
import unittest
import warnings
import zipfile
from http.client import HTTPConnection
from pathlib import Path

from backend import asie_local_api as api
from backend.acceptance import build_acceptance_pack
from backend.decision_council import evaluate_decision_council
from backend.decision_pack import build_action_items_from_overview, build_decision_pack, render_decision_pack_html
from backend.evidence_ledger import build_evidence_ledger
from backend.execution_engine import build_execution_plan
from backend.finance_engine import finance_result_set
from backend.reports import build_report, build_report_view, render_report_html
from backend.risk_engine import build_risk_advisory_summary, build_risk_register
from backend.sector_intelligence import build_sector_intelligence
from backend.workflow import project_readiness
from backend.workspace import build_project_workspace, compare_snapshots

VALID_INPUTS = {
    "startup_cost": 250000,
    "monthly_fixed_cost": 62000,
    "unit_price": 85,
    "variable_cost": 34,
    "monthly_units": 1600,
    "annual_discount_rate": 0.10,
    "working_capital_months": 2,
}

OPERATIONAL_INPUTS = VALID_INPUTS | {
    "use_operating_capacity": True,
    "capacity_units_per_day": 80,
    "operating_days_per_month": 22,
    "utilization_rate": 0.9,
    "payroll_monthly": 28000,
    "rent_monthly": 14000,
    "utilities_monthly": 5500,
    "marketing_monthly": 7000,
    "maintenance_monthly": 3500,
    "capex_equipment": 120000,
    "capex_fitout": 85000,
    "capex_licenses_local": 45000,
    "depreciation_years": 5,
    "equity_contribution": 150000,
    "debt_amount": 0,
    "loan_grace_months": 0,
}

SECTOR_INPUTS = OPERATIONAL_INPUTS | {
    "primary_sector_id": "SEC-11",
    "subsector_id": "Software",
    "activity_description": "منصة برمجية محلية",
    "location_scope": "Saudi Arabia",
}


APPROVED_SOURCE = {
    "source_id": "APPROVED_OPEN_DATA_TEST",
    "publisher": "Example Open Publisher",
    "route": "official_open_dataset_or_api",
    "state": "enabled",
    "url": "https://example.test/dataset",
    "terms_url": "https://example.test/terms",
    "terms_hash": "sha256:source",
    "license_snapshot_ref": "license_snapshot:source",
    "attribution": "Example attribution",
    "classification": "public_open_data",
    "pdpl_check": "passed_no_personal_data",
    "nca_check": "passed_local_processing",
    "lawful_purpose": "feasibility_estimation",
    "reviewer": "human-reviewer",
    "reviewer_decision": "approved",
}

APPROVED_GASTAT_SOURCE = APPROVED_SOURCE | {
    "source_id": "GASTAT_CANDIDATE",
    "publisher": "General Authority for Statistics",
    "url": "https://database.stats.gov.sa/test-open-dataset",
}


class LocalPlatformTests(unittest.TestCase):
    def setUp(self) -> None:
        legacy_warning_scope = warnings.catch_warnings()
        legacy_warning_scope.__enter__()
        warnings.filterwarnings(
            "ignore",
            message="Compatibility wrapper for legacy parity tests only.*",
            category=DeprecationWarning,
        )
        self.addCleanup(legacy_warning_scope.__exit__, None, None, None)

    def make_repo(self) -> api.Repository:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        return api.Repository(Path(temp_dir.name) / "asie-test.sqlite3")

    def test_project_run_snapshot_report_parity(self) -> None:
        repo = self.make_repo()
        project = repo.create_project(
            {
                "name": "اختبار مسار كامل",
                "sector": "خدمات",
                "jurisdiction": "Saudi Arabia",
                "depth_profile": "starter",
                "inputs": VALID_INPUTS,
            }
        )

        overview, report = api.build_overview(project, repo)
        repo.save_run_snapshot(project.project_id, overview, report)
        stored_overview = repo.get_run_overview(overview["run"]["run_id"])
        stored_report = repo.get_snapshot_report(overview["snapshot"]["snapshot_id"])
        audit = repo.get_run_audit(overview["run"]["run_id"])

        self.assertIsNotNone(stored_overview)
        self.assertIsNotNone(stored_report)
        self.assertIsNotNone(audit)
        self.assertEqual(stored_overview["snapshot"]["snapshot_id"], stored_report["snapshot_id"])
        self.assertEqual(stored_overview["kpis"], stored_report["kpis"])
        self.assertEqual(stored_overview["finance"]["scenarios"], stored_report["scenarios"])
        self.assertEqual(stored_overview["decision"]["sovereign_verdict"], stored_report["summary"]["sovereign_verdict"])
        self.assertEqual(audit["source_fetch_enabled"], False)
        self.assertTrue(stored_overview["snapshot"]["immutable"])
        self.assertEqual(stored_report["assumption_book"], stored_overview["assumption_book"])
        self.assertEqual(stored_report["evidence_register"]["snapshot_id"], stored_overview["snapshot"]["snapshot_id"])
        self.assertEqual(stored_report["acceptance"]["status"], "passed")
        self.assertEqual(stored_overview["acceptance"]["passed"], 13)

    def test_overview_and_report_are_projections_of_same_assembled_snapshot(self) -> None:
        repo = self.make_repo()
        project = repo.create_project({"name": "Assembly projection parity", "inputs": SECTOR_INPUTS})

        overview, report = api.build_overview(project, repo)

        assembly = overview["snapshot_assembly"]
        self.assertEqual(assembly["contract_id"], "snapshot.assemble.v1")
        self.assertEqual(assembly["projection_source"], "immutable_assembled_snapshot")
        self.assertEqual(overview["snapshot"]["content_hash"], report["snapshot_assembly"]["content_hash"])
        self.assertEqual(overview["snapshot"]["integrity_hash"], report["snapshot_assembly"]["integrity_hash"])
        self.assertEqual(len(assembly["lineage"]), 7)
        self.assertEqual(
            {row["output_key"] for row in assembly["lineage"]},
            {
                "finance_result",
                "evidence_ledger",
                "sector_intelligence",
                "decision_result",
                "risk_result",
                "execution_result",
                "projection_support",
            },
        )
        self.assertTrue(
            all(
                overview["run"]["run_id"] in correlation_id
                for correlation_id in assembly["correlation_map"].values()
            )
        )

    def test_local_aas_runtime_boots_once_across_project_runs(self) -> None:
        api.reset_local_module_runtime_for_tests()
        repo = self.make_repo()
        first_project = repo.create_project({"name": "Runtime lifetime A", "inputs": SECTOR_INPUTS})
        second_project = repo.create_project({"name": "Runtime lifetime B", "inputs": OPERATIONAL_INPUTS})

        first_overview, _first_report = api.build_overview(first_project, repo)
        second_overview, _second_report = api.build_overview(second_project, repo)

        self.assertEqual(api.local_runtime_boot_count(), 1)
        self.assertIs(api.local_module_runtime(), api.local_module_runtime())
        self.assertNotEqual(first_overview["run"]["run_id"], second_overview["run"]["run_id"])
        self.assertNotEqual(first_overview["snapshot"]["snapshot_id"], second_overview["snapshot"]["snapshot_id"])
        self.assertEqual(first_overview["snapshot_assembly"]["contract_id"], "snapshot.assemble.v1")
        self.assertEqual(second_overview["snapshot_assembly"]["contract_id"], "snapshot.assemble.v1")

    def test_project_run_accepts_controller_assigned_heart_as_runtime_source(self) -> None:
        repo = self.make_repo()
        project = repo.create_project({"name": "Assigned heart source", "inputs": SECTOR_INPUTS})

        overview, report = api.build_overview(project, repo, source_module_id="aas.heart.M1")

        self.assertEqual(overview["audit"]["runtime_source_module_id"], "aas.heart.M1")
        self.assertEqual(report["snapshot_assembly"]["content_hash"], overview["snapshot"]["content_hash"])
        self.assertEqual(overview["snapshot_assembly"]["contract_id"], "snapshot.assemble.v1")

    def test_project_run_pipeline_requires_closed_envelope(self) -> None:
        repo = self.make_repo()
        project = repo.create_project({"name": "Closed pipeline envelope", "inputs": SECTOR_INPUTS})

        with self.assertRaisesRegex(TypeError, "requires ProjectRunEnvelope"):
            api.execute_project_run_pipeline(None, project=project, data_access=repo)

    def test_project_run_pipeline_requests_snapshot_assembly_once(self) -> None:
        api.reset_local_module_runtime_for_tests()
        repo = self.make_repo()
        project = repo.create_project({"name": "Single assembly request", "inputs": SECTOR_INPUTS})
        run_envelope = api.ProjectRunEnvelope(
            project_id=project.project_id,
            scenario_id="baseline",
            operation_id="op_single_assembly",
            idempotency_key="idem_single_assembly",
            input_hash="sha256:single-assembly-input",
            run_id="run_single_assembly",
            snapshot_id="snap_single_assembly",
            source_module_id="aas.heart.M1",
        )

        overview, _report = api.execute_project_run_pipeline(
            run_envelope,
            project=project,
            data_access=repo,
        )

        operation_messages = [
            record["message"]
            for record in api.local_runtime_context().bus.messages
            if record["message"].get("operation_id") == run_envelope.operation_id
        ]
        assembly_messages = [
            message for message in operation_messages if message.get("contract_id") == "snapshot.assemble.v1"
        ]
        pipeline_contracts = [
            message["contract_id"]
            for message in operation_messages
            if message.get("contract_id") in run_envelope.pipeline_contract_sequence
        ]
        self.assertEqual(len(assembly_messages), 1)
        self.assertEqual(tuple(pipeline_contracts), run_envelope.pipeline_contract_sequence)
        self.assertEqual(overview["run"]["run_id"], run_envelope.run_id)
        self.assertEqual(overview["snapshot"]["snapshot_id"], run_envelope.snapshot_id)
        self.assertTrue(all(message["input_hash"] == run_envelope.input_hash for message in operation_messages))

    def test_snapshot_persistence_rejects_tampered_report_before_atomic_write(self) -> None:
        repo = self.make_repo()
        project = repo.create_project({"name": "Atomic snapshot guard", "inputs": SECTOR_INPUTS})
        overview, report = api.build_overview(project, repo)
        tampered_report = report | {
            "snapshot_assembly": report["snapshot_assembly"] | {"integrity_hash": "tampered"}
        }

        with self.assertRaisesRegex(ValueError, "integrity hash mismatch"):
            repo.save_run_snapshot(project.project_id, overview, tampered_report)

        self.assertIsNone(repo.get_run_overview(overview["run"]["run_id"]))
        self.assertIsNone(repo.get_snapshot_report(overview["snapshot"]["snapshot_id"]))

    def test_snapshot_persistence_rejects_tampered_overview_projection(self) -> None:
        repo = self.make_repo()
        project = repo.create_project({"name": "Overview projection guard", "inputs": SECTOR_INPUTS})
        overview, report = api.build_overview(project, repo)
        tampered_overview = overview | {"finance": overview["finance"] | {"status": "tampered"}}

        with self.assertRaisesRegex(ValueError, "overview projection hash mismatch"):
            repo.save_run_snapshot(project.project_id, tampered_overview, report)

        self.assertIsNone(repo.get_run_overview(overview["run"]["run_id"]))

    def test_finance_engine_outputs_npv_irr_payback_and_sensitivity(self) -> None:
        repo = self.make_repo()
        project = repo.create_project({"name": "Finance", "inputs": VALID_INPUTS})

        overview, _report = api.build_overview(project, repo)
        output_ids = {item["output_id"] for item in overview["kpis"]}

        self.assertEqual(overview["finance"]["status"], "ready")
        self.assertIn("npv", output_ids)
        self.assertIn("irr", output_ids)
        self.assertIn("payback-months", output_ids)
        self.assertEqual(len(overview["finance"]["scenarios"]), 3)
        self.assertEqual(len(overview["finance"]["sensitivity"]["cells"]), 9)
        self.assertEqual(overview["monte_carlo"]["convergence"]["status"], "passed")
        self.assertTrue(all(item["assumption_refs"] for item in overview["kpis"]))

    def test_build_overview_finance_matches_direct_engine_after_runtime_replacement(self) -> None:
        repo = self.make_repo()
        project = repo.create_project({"name": "Finance runtime parity", "inputs": VALID_INPUTS})
        direct_finance, direct_blockers = finance_result_set(project.inputs)
        direct_finance["assumption_refs"] = [row["assumption_id"] for row in repo.project_assumptions(project.project_id)]

        overview, report = api.build_overview(project, repo)

        self.assertFalse(hasattr(api, "finance_result_set"))
        self.assertEqual(direct_blockers, [])
        self.assertEqual(overview["finance"], direct_finance)
        self.assertEqual(report["scenarios"], direct_finance["scenarios"])
        self.assertEqual(overview["acceptance"]["status"], "passed")

    def test_build_overview_evidence_ledger_matches_direct_builder_after_runtime_replacement(self) -> None:
        repo = self.make_repo()
        repo.save_source_review(APPROVED_GASTAT_SOURCE)
        project = repo.create_project({"name": "Evidence runtime parity", "inputs": SECTOR_INPUTS})
        dataset = repo.save_dataset(
            {
                "source_id": "GASTAT_CANDIDATE",
                "title": "Runtime parity dataset",
                "publisher": "General Authority for Statistics",
                "import_method": "manual_table",
                "review_status": "approved_for_use",
                "human_review_decision": "approved",
                "license_snapshot_ref": "license_snapshot:runtime-parity",
                "terms_hash": "sha256:runtime-parity",
                "classification": "public_open_data",
                "pdpl_check": "passed_no_personal_data",
                "attribution": "GASTAT attribution",
                "rows": [{"metric": "market_size", "value": 100}],
            }
        )
        repo.save_evidence_link(
            project.project_id,
            {
                "target_type": "sector_criterion",
                "target_id": "market_size",
                "dataset_id": dataset["dataset_id"],
                "evidence_ref": "dataset:runtime-parity:market_size",
                "human_review_decision": "approved",
            },
        )

        overview, report = api.build_overview(project, repo)
        direct_ledger = build_evidence_ledger(
            overview["evidence_register"],
            overview["evidence_register"]["source_records"],
            overview["snapshot"]["snapshot_id"],
            overview["run"]["run_id"],
            overview["evidence_register"].get("transformations", []),
        )

        self.assertFalse(hasattr(api, "build_evidence_ledger"))
        self.assertEqual(overview["evidence_ledger"], direct_ledger)
        self.assertEqual(report["evidence_ledger"], direct_ledger)
        self.assertTrue(overview["evidence_ledger"][0]["can_support_target"])

    def test_build_overview_sector_intelligence_matches_direct_builder_after_runtime_replacement(self) -> None:
        repo = self.make_repo()
        repo.save_source_review(APPROVED_GASTAT_SOURCE)
        project = repo.create_project({"name": "Sector runtime parity", "inputs": SECTOR_INPUTS})
        evidence_register = api.build_evidence_register(repo, project.project_id, "parity_snapshot", repo.source_records())
        direct_sector = build_sector_intelligence(project, evidence_register, repo.source_records())

        overview, report = api.build_overview(project, repo)
        runtime_evidence_register = overview["evidence_register"]
        parity_sector = build_sector_intelligence(project, runtime_evidence_register, repo.source_records())

        self.assertFalse(hasattr(api, "build_sector_intelligence"))
        self.assertEqual(overview["sector_intelligence"], parity_sector)
        self.assertEqual(report["sector_intelligence"], parity_sector)
        self.assertEqual(parity_sector["status"], direct_sector["status"])
        self.assertEqual(parity_sector["taxonomy_record"], direct_sector["taxonomy_record"])
        self.assertFalse(overview["sector_intelligence"]["external_fetch_enabled"])

    def test_build_overview_decision_council_matches_direct_builder_after_runtime_replacement(self) -> None:
        repo = self.make_repo()
        project = repo.create_project({"name": "Decision runtime parity", "inputs": SECTOR_INPUTS})

        overview, report = api.build_overview(project, repo)
        direct_decision = evaluate_decision_council(
            overview["finance"],
            overview["blockers"],
            overview["readiness_gates"],
            overview["sector_intelligence"],
        )

        self.assertFalse(hasattr(api, "evaluate_decision_council"))
        self.assertEqual(overview["decision_council"], direct_decision)
        self.assertEqual(overview["decision"], direct_decision["verdict"])
        self.assertEqual(overview["personas"], direct_decision["personas"])
        self.assertEqual(report["decision_council"], direct_decision)
        self.assertNotIn("risk_register", overview["personas"][0]["permitted_input_refs"])
        self.assertNotIn("execution_plan", overview["personas"][0]["permitted_input_refs"])

    def test_decision_council_runtime_rejects_downstream_risk_and_execution_inputs(self) -> None:
        repo = self.make_repo()
        project = repo.create_project({"name": "Decision forbidden inputs", "inputs": SECTOR_INPUTS})
        overview, _report = api.build_overview(project, repo)

        with self.assertRaises(ValueError):
            runtime = api.local_module_runtime()
            runtime.execute(
                api.BusMessage(
                    source_module_id="aas.heart_controller",
                    target_module_id="module.decision_council",
                    contract_id="decision.council.evaluate.v1",
                    socket_id="socket.decision.council",
                    correlation_id="corr:test:decision-forbidden",
                    audit_ref="audit:test:decision-forbidden",
                    payload={
                        "project_id": project.project_id,
                        "run_id": overview["run"]["run_id"],
                        "snapshot_id": overview["snapshot"]["snapshot_id"],
                        "input_contract_id": "DecisionCouncilInputEnvelope.v1",
                        "finance": overview["finance"],
                        "blockers": overview["blockers"],
                        "readiness_gates": overview["readiness_gates"],
                        "sector_intelligence": overview["sector_intelligence"],
                        "risk_register": overview["risk_register"],
                        "execution_plan": overview["execution_plan"],
                    },
                )
            )

    def test_build_overview_risk_register_matches_direct_builder_after_runtime_replacement(self) -> None:
        repo = self.make_repo()
        project = repo.create_project({"name": "Risk runtime parity", "inputs": SECTOR_INPUTS})

        overview, report = api.build_overview(project, repo)
        direct_risk = build_risk_register(
            overview["finance"],
            overview["evidence_register"],
            overview["source_policy"],
            overview["readiness_gates"],
            project_id=project.project_id,
            run_id=overview["run"]["run_id"],
            snapshot_id=overview["snapshot"]["snapshot_id"],
        )
        direct_advisory = build_risk_advisory_summary(
            direct_risk,
            project_id=project.project_id,
            run_id=overview["run"]["run_id"],
            snapshot_id=overview["snapshot"]["snapshot_id"],
        )

        self.assertFalse(hasattr(api, "build_risk_register"))
        self.assertEqual(overview["risk_register"], direct_risk)
        self.assertEqual(overview["risk_advisory_summary"], direct_advisory)
        self.assertEqual(report["risk_register"], direct_risk)
        self.assertEqual(report["risk_advisory_summary"], direct_advisory)
        self.assertEqual(overview["risk_register"]["risks"][0]["risk_id"], "funding_risk")
        self.assertIn(overview["run"]["run_id"], overview["risk_register"]["risk_register_id"])
        self.assertIn(overview["snapshot"]["snapshot_id"], overview["risk_register"]["risk_register_id"])
        self.assertEqual(overview["risk_advisory_summary"]["run_id"], overview["run"]["run_id"])
        self.assertEqual(overview["risk_advisory_summary"]["snapshot_id"], overview["snapshot"]["snapshot_id"])
        self.assertNotIn("risks", overview["risk_advisory_summary"])
        self.assertNotIn("top_risks", overview["risk_advisory_summary"])

    def test_risk_engine_runtime_rejects_decision_and_execution_inputs(self) -> None:
        repo = self.make_repo()
        project = repo.create_project({"name": "Risk forbidden inputs", "inputs": SECTOR_INPUTS})
        overview, _report = api.build_overview(project, repo)

        with self.assertRaises(ValueError):
            runtime = api.local_module_runtime()
            runtime.execute(
                api.BusMessage(
                    source_module_id="aas.heart_controller",
                    target_module_id="module.risk_engine",
                    contract_id="risk.register.build.v1",
                    socket_id="socket.risk.register",
                    correlation_id="corr:test:risk-forbidden",
                    audit_ref="audit:test:risk-forbidden",
                    payload={
                        "project_id": project.project_id,
                        "run_id": overview["run"]["run_id"],
                        "snapshot_id": overview["snapshot"]["snapshot_id"],
                        "input_contract_id": "RiskRegisterInputEnvelope.v1",
                        "finance": overview["finance"],
                        "evidence_register": overview["evidence_register"],
                        "source_policy": overview["source_policy"],
                        "readiness_gates": overview["readiness_gates"],
                        "decision_council": overview["decision_council"],
                        "execution_plan": overview["execution_plan"],
                    },
                )
            )

    def test_build_overview_execution_plan_matches_direct_builder_after_runtime_replacement(self) -> None:
        repo = self.make_repo()
        project = repo.create_project({"name": "Execution runtime parity", "inputs": SECTOR_INPUTS})

        overview, report = api.build_overview(project, repo)
        direct_execution = build_execution_plan(
            overview["finance"],
            overview["decision_council"],
            overview["readiness_gates"],
            overview["risk_advisory_summary"],
        )

        self.assertFalse(hasattr(api, "build_execution_plan"))
        self.assertEqual(overview["execution_plan"], direct_execution)
        self.assertEqual(report["execution_plan"], direct_execution)
        self.assertEqual(
            overview["execution_plan"]["risk_advisory_summary"],
            overview["risk_advisory_summary"],
        )
        self.assertFalse(overview["execution_plan"]["risk_advisory_summary"]["contains_full_risk_register"])
        self.assertEqual(
            overview["execution_plan"]["blocked_by_risks"],
            overview["risk_advisory_summary"]["blocked_risk_ids"],
        )
        self.assertEqual(
            overview["execution_plan"]["execution_constraints"],
            overview["risk_advisory_summary"]["execution_constraints"],
        )
        self.assertEqual(
            [item["phase_id"] for item in overview["execution_plan"]["milestones"]],
            ["setup", "procurement", "staffing", "launch", "stabilization"],
        )

    def test_execution_engine_runtime_rejects_risk_inputs(self) -> None:
        repo = self.make_repo()
        project = repo.create_project({"name": "Execution forbidden inputs", "inputs": SECTOR_INPUTS})
        overview, _report = api.build_overview(project, repo)

        with self.assertRaises(ValueError):
            runtime = api.local_module_runtime()
            runtime.execute(
                api.BusMessage(
                    source_module_id="aas.heart_controller",
                    target_module_id="module.execution_engine",
                    contract_id="execution.plan.build.v1",
                    socket_id="socket.execution.plan",
                    correlation_id="corr:test:execution-forbidden",
                    audit_ref="audit:test:execution-forbidden",
                    payload={
                        "project_id": project.project_id,
                        "run_id": overview["run"]["run_id"],
                        "snapshot_id": overview["snapshot"]["snapshot_id"],
                        "input_contract_id": "ExecutionPlanInputEnvelope.v1",
                        "finance": overview["finance"],
                        "decision_council": overview["decision_council"],
                        "readiness_gates": overview["readiness_gates"],
                        "risk_advisory_summary": overview["risk_advisory_summary"],
                        "risk_register": overview["risk_register"],
                    },
                )
            )

    def test_execution_engine_runtime_rejects_full_risk_shaped_advisory(self) -> None:
        repo = self.make_repo()
        project = repo.create_project({"name": "Execution advisory boundary", "inputs": SECTOR_INPUTS})
        overview, _report = api.build_overview(project, repo)

        full_risk_shaped_summary = overview["risk_register"] | {
            "risk_advisory_summary_id": "risk-advisory:bad",
            "contains_full_risk_register": True,
        }
        with self.assertRaises(ValueError):
            runtime = api.local_module_runtime()
            runtime.execute(
                api.BusMessage(
                    source_module_id="aas.heart_controller",
                    target_module_id="module.execution_engine",
                    contract_id="execution.plan.build.v1",
                    socket_id="socket.execution.plan",
                    correlation_id="corr:test:execution-bad-advisory",
                    audit_ref="audit:test:execution-bad-advisory",
                    payload={
                        "project_id": project.project_id,
                        "run_id": overview["run"]["run_id"],
                        "snapshot_id": overview["snapshot"]["snapshot_id"],
                        "input_contract_id": "ExecutionPlanInputEnvelope.v1",
                        "finance": overview["finance"],
                        "decision_council": overview["decision_council"],
                        "readiness_gates": overview["readiness_gates"],
                        "risk_advisory_summary": full_risk_shaped_summary,
                    },
                )
            )

    def test_execution_engine_runtime_rejects_advisory_identity_mismatch(self) -> None:
        repo = self.make_repo()
        project = repo.create_project({"name": "Execution advisory identity mismatch", "inputs": SECTOR_INPUTS})
        overview, _report = api.build_overview(project, repo)
        mismatched_summary = overview["risk_advisory_summary"] | {"snapshot_id": "snap_wrong"}

        with self.assertRaises(ValueError):
            runtime = api.local_module_runtime()
            runtime.execute(
                api.BusMessage(
                    source_module_id="aas.heart_controller",
                    target_module_id="module.execution_engine",
                    contract_id="execution.plan.build.v1",
                    socket_id="socket.execution.plan",
                    correlation_id="corr:test:execution-advisory-identity",
                    audit_ref="audit:test:execution-advisory-identity",
                    payload={
                        "project_id": project.project_id,
                        "run_id": overview["run"]["run_id"],
                        "snapshot_id": overview["snapshot"]["snapshot_id"],
                        "input_contract_id": "ExecutionPlanInputEnvelope.v1",
                        "finance": overview["finance"],
                        "decision_council": overview["decision_council"],
                        "readiness_gates": overview["readiness_gates"],
                        "risk_advisory_summary": mismatched_summary,
                    },
                )
            )

    def test_execution_engine_runtime_rejects_advisory_extra_fields(self) -> None:
        repo = self.make_repo()
        project = repo.create_project({"name": "Execution advisory strict keys", "inputs": SECTOR_INPUTS})
        overview, _report = api.build_overview(project, repo)
        leaky_summary = overview["risk_advisory_summary"] | {"mitigation": "leaked full risk detail"}

        with self.assertRaises(ValueError):
            runtime = api.local_module_runtime()
            runtime.execute(
                api.BusMessage(
                    source_module_id="aas.heart_controller",
                    target_module_id="module.execution_engine",
                    contract_id="execution.plan.build.v1",
                    socket_id="socket.execution.plan",
                    correlation_id="corr:test:execution-advisory-extra",
                    audit_ref="audit:test:execution-advisory-extra",
                    payload={
                        "project_id": project.project_id,
                        "run_id": overview["run"]["run_id"],
                        "snapshot_id": overview["snapshot"]["snapshot_id"],
                        "input_contract_id": "ExecutionPlanInputEnvelope.v1",
                        "finance": overview["finance"],
                        "decision_council": overview["decision_council"],
                        "readiness_gates": overview["readiness_gates"],
                        "risk_advisory_summary": leaky_summary,
                    },
                )
            )

    def test_execution_plan_consumes_blocked_risk_ids_without_full_risk_register(self) -> None:
        repo = self.make_repo()
        project = repo.create_project({"name": "Execution consumes advisory", "inputs": SECTOR_INPUTS})
        overview, _report = api.build_overview(project, repo)
        readiness = overview["readiness_gates"] | {
            "status": "passed",
            "gates": [
                gate | {"status": "passed"}
                for gate in overview["readiness_gates"]["gates"]
            ],
        }
        advisory = overview["risk_advisory_summary"] | {
            "status": "blocked",
            "blocked_risk_ids": ["dscr_risk"],
            "execution_constraints": [
                {
                    "risk_id": "dscr_risk",
                    "severity": "critical",
                    "trigger": "debt_terms_not_ready",
                    "owner_role": "Business Advisor",
                }
            ],
        }

        execution = build_execution_plan(
            overview["finance"],
            overview["decision_council"],
            readiness,
            advisory,
        )

        self.assertEqual(execution["status"], "blocked")
        self.assertEqual(execution["blocked_by_gates"], [])
        self.assertEqual(execution["blocked_by_risks"], ["dscr_risk"])
        self.assertEqual(execution["execution_constraints"], advisory["execution_constraints"])
        self.assertNotIn("risk_register", execution)

    def test_build_overview_report_matches_direct_builder_after_runtime_replacement(self) -> None:
        repo = self.make_repo()
        project = repo.create_project({"name": "Report runtime parity", "inputs": SECTOR_INPUTS})

        overview, report = api.build_overview(project, repo)
        direct_report = build_report(overview)

        self.assertFalse(hasattr(api, "build_report"))
        self.assertEqual(report, direct_report)
        self.assertEqual(report["snapshot_id"], overview["snapshot"]["snapshot_id"])
        self.assertEqual(report["execution_plan"], overview["execution_plan"])
        self.assertEqual(report["risk_register"], overview["risk_register"])
        self.assertEqual(report["risk_advisory_summary"], overview["risk_advisory_summary"])

    def test_report_runtime_rejects_repository_and_review_inputs(self) -> None:
        repo = self.make_repo()
        project = repo.create_project({"name": "Report forbidden inputs", "inputs": SECTOR_INPUTS})
        overview, _report = api.build_overview(project, repo)

        with self.assertRaises(ValueError):
            runtime = api.local_module_runtime()
            runtime.execute(
                api.BusMessage(
                    source_module_id="aas.heart_controller",
                    target_module_id="module.reports",
                    contract_id="report.snapshot.project.v1",
                    socket_id="socket.report.snapshot",
                    correlation_id="corr:test:report-forbidden",
                    audit_ref="audit:test:report-forbidden",
                    payload={
                        "project_id": project.project_id,
                        "run_id": overview["run"]["run_id"],
                        "snapshot_id": overview["snapshot"]["snapshot_id"],
                        "input_contract_id": "SnapshotReportInputEnvelope.v1",
                        "overview": overview,
                        "reviews": [],
                        "repository": "forbidden",
                    },
                )
            )

    def test_missing_finance_inputs_returns_not_ready(self) -> None:
        repo = self.make_repo()
        project = repo.create_project({"name": "مدخلات ناقصة", "inputs": {}})

        overview, _report = api.build_overview(project, repo)

        self.assertEqual(overview["run"]["status"], "blocked")
        self.assertEqual(overview["decision"]["sovereign_verdict"], "BLOCKED_NOT_READY")
        self.assertEqual(overview["monte_carlo"]["status"], "not_ready")
        self.assertEqual(overview["finance"]["status"], "not_ready")
        self.assertGreaterEqual(len(overview["remediation_envelopes"]), 1)
        self.assertFalse(overview["readiness"]["ready_to_run"])
        self.assertTrue(any(step["status"] == "blocked" for step in overview["readiness"]["steps"]))

    def test_project_patch_readiness_and_assumption_book(self) -> None:
        repo = self.make_repo()
        project = repo.create_project({"name": "Draft", "inputs": {"unit_price": 90}})

        updated = repo.update_project(project.project_id, {"inputs": VALID_INPUTS})
        self.assertIsNotNone(updated)
        assumptions = repo.project_assumptions(project.project_id)
        readiness = project_readiness(updated, assumptions, repo.source_records())

        self.assertGreaterEqual(len(assumptions), 7)
        self.assertTrue(any(row["input_key"] == "startup_cost" for row in assumptions))
        self.assertTrue(readiness["ready_to_run"])
        self.assertTrue(any(step["status"] == "needs_review" for step in readiness["steps"]))

    def test_report_view_and_html_use_same_snapshot(self) -> None:
        repo = self.make_repo()
        project = repo.create_project({"name": "Report", "inputs": VALID_INPUTS})
        overview, report = api.build_overview(project, repo)

        view = build_report_view(report)
        html = render_report_html(report)

        self.assertEqual(view["snapshot_id"], overview["snapshot"]["snapshot_id"])
        self.assertIn(overview["snapshot"]["snapshot_id"], html)
        self.assertIn("دفتر الافتراضات", html)
        self.assertIn("سجل المصادر", html)
        self.assertIn("اختبارات القبول r10/r11", html)

    def test_two_runs_produce_distinct_immutable_snapshots(self) -> None:
        repo = self.make_repo()
        project = repo.create_project({"name": "Two runs", "inputs": VALID_INPUTS})
        first_overview, first_report = api.build_overview(project, repo)
        repo.save_run_snapshot(project.project_id, first_overview, first_report)
        second_overview, second_report = api.build_overview(project, repo)
        repo.save_run_snapshot(project.project_id, second_overview, second_report)

        runs = repo.list_project_runs(project.project_id)

        self.assertEqual(len(runs), 2)
        self.assertNotEqual(first_overview["snapshot"]["snapshot_id"], second_overview["snapshot"]["snapshot_id"])
        self.assertTrue(first_overview["snapshot"]["immutable"])
        self.assertTrue(second_overview["snapshot"]["immutable"])

    def test_project_workspace_keeps_projects_separate(self) -> None:
        repo = self.make_repo()
        first = repo.create_project({"name": "First", "inputs": VALID_INPUTS})
        second = repo.create_project({"name": "Second", "inputs": VALID_INPUTS | {"monthly_units": 900}})
        first_overview, first_report = api.build_overview(first, repo)
        second_overview, second_report = api.build_overview(second, repo)
        repo.save_run_snapshot(first.project_id, first_overview, first_report)
        repo.save_run_snapshot(second.project_id, second_overview, second_report)

        first_workspace = build_project_workspace(repo, first.project_id)
        second_workspace = build_project_workspace(repo, second.project_id)

        self.assertEqual(len(first_workspace["runs"]), 1)
        self.assertEqual(len(second_workspace["runs"]), 1)
        self.assertEqual(first_workspace["runs"][0]["project_id"], first.project_id)
        self.assertEqual(second_workspace["runs"][0]["project_id"], second.project_id)

    def test_snapshot_compare_reads_saved_snapshots_without_recalculation(self) -> None:
        repo = self.make_repo()
        project = repo.create_project({"name": "Compare", "inputs": VALID_INPUTS})
        first_overview, first_report = api.build_overview(project, repo)
        repo.save_run_snapshot(project.project_id, first_overview, first_report)
        repo.update_project(project.project_id, {"inputs": {"monthly_units": 2200}})
        updated = repo.get_project(project.project_id)
        second_overview, second_report = api.build_overview(updated, repo)
        repo.save_run_snapshot(project.project_id, second_overview, second_report)

        comparison = compare_snapshots(first_overview, second_overview)

        self.assertFalse(comparison["recalculated"])
        self.assertEqual(comparison["snapshot_a_id"], first_overview["snapshot"]["snapshot_id"])
        self.assertEqual(comparison["snapshot_b_id"], second_overview["snapshot"]["snapshot_id"])
        self.assertTrue(any(item["output_id"] == "npv" and item["delta"] is not None for item in comparison["metric_deltas"]))
        self.assertTrue(any(item["input_key"] == "monthly_units" for item in comparison["assumption_changes"]))

    def test_old_snapshot_report_stays_stable_after_project_edit(self) -> None:
        repo = self.make_repo()
        project = repo.create_project({"name": "Stable", "inputs": VALID_INPUTS})
        overview, report = api.build_overview(project, repo)
        repo.save_run_snapshot(project.project_id, overview, report)
        before = repo.get_snapshot_report(overview["snapshot"]["snapshot_id"])
        repo.update_project(project.project_id, {"inputs": {"monthly_units": 2500}})
        after = repo.get_snapshot_report(overview["snapshot"]["snapshot_id"])

        self.assertEqual(before, after)
        self.assertEqual(after["snapshot_id"], overview["snapshot"]["snapshot_id"])

    def test_enabled_source_requires_human_review_evidence(self) -> None:
        repo = self.make_repo()

        with self.assertRaises(PermissionError):
            repo.save_source_review(
                {
                    "source_id": "OPEN_DATA_WITHOUT_TERMS",
                    "publisher": "Example",
                    "route": "official_open_dataset_or_api",
                    "state": "enabled",
                    "url": "https://example.test/dataset",
                }
            )

    def test_complete_source_review_can_enable_without_external_fetch(self) -> None:
        repo = self.make_repo()
        repo.save_source_review(
            {
                "source_id": "APPROVED_OPEN_DATA_TEST",
                "publisher": "Example",
                "route": "official_open_dataset_or_api",
                "state": "enabled",
                "url": "https://example.test/dataset",
                "terms_url": "https://example.test/terms",
                "terms_hash": "sha256:test",
                "license_snapshot_ref": "license_snapshot:test",
                "attribution": "Example attribution",
                "classification": "public_open_data",
                "pdpl_check": "passed_no_personal_data",
                "nca_check": "passed_local_processing",
                "lawful_purpose": "feasibility_estimation",
                "reviewer": "human-reviewer",
                "reviewer_decision": "approved",
            }
        )

        policy = api.source_policy(repo.source_records(), api.PROFILE_ID)

        self.assertFalse(policy["external_fetch_enabled"])
        self.assertTrue(any(row["source_id"] == "APPROVED_OPEN_DATA_TEST" for row in policy["enabled_sources"]))

    def test_reference_only_source_does_not_enable_external_fetch(self) -> None:
        repo = self.make_repo()
        repo.save_source_review(
            {
                "source_id": "REFERENCE_ONLY_TEST",
                "publisher": "Reference",
                "route": "reference_only_link",
                "state": "reference_only",
                "url": "https://example.test/reference",
            }
        )

        policy = api.source_policy(repo.source_records(), api.PROFILE_ID)

        self.assertFalse(policy["external_fetch_enabled"])
        self.assertTrue(any(row["source_id"] == "REFERENCE_ONLY_TEST" for row in policy["reference_only"]))

    def test_r10_r11_guardrails_remain_visible(self) -> None:
        repo = self.make_repo()
        project = repo.create_project({"name": "Guardrails", "inputs": VALID_INPUTS})
        overview, _report = api.build_overview(project, repo)

        self.assertTrue(all(item["owner_module"] == "Finance Engine" for item in overview["kpis"]))
        self.assertTrue(overview["decision"]["no_vote"])
        self.assertFalse(overview["decision"]["advisory_consensus_visible_as_verdict"])
        self.assertEqual(overview["source_policy"]["profile_id"], api.PROFILE_ID)
        self.assertIn("React finance calculation", overview["audit"]["forbidden_paths"])
        self.assertEqual(overview["decision_council"]["isolation_order"][0], "project_manager")
        self.assertEqual(overview["acceptance"]["failed"], 0)

    def test_acceptance_pack_fails_when_frontend_guard_is_missing(self) -> None:
        repo = self.make_repo()
        project = repo.create_project({"name": "Guard failure", "inputs": VALID_INPUTS})
        overview, _report = api.build_overview(project, repo)
        overview["audit"]["forbidden_paths"] = [
            item for item in overview["audit"]["forbidden_paths"] if item != "React finance calculation"
        ]

        acceptance = build_acceptance_pack(overview)

        self.assertEqual(acceptance["status"], "failed")
        self.assertTrue(any(item["test_id"] == "R11-AC-04" and item["status"] == "failed" for item in acceptance["tests"]))

    def test_dataset_without_license_quality_gate_fails(self) -> None:
        repo = self.make_repo()
        repo.save_source_review(APPROVED_SOURCE)
        dataset = repo.save_dataset(
            {
                "source_id": APPROVED_SOURCE["source_id"],
                "title": "Manual local table",
                "publisher": "Example Open Publisher",
                "import_method": "manual_table",
                "review_status": "review_required",
                "rows": [{"month": "2026-01", "value": 10}],
            }
        )

        gate = api.dataset_quality_gate(dataset, repo.get_source_record(dataset["source_id"]))

        self.assertEqual(gate["status"], "failed")
        self.assertFalse(gate["can_use_for_assumptions"])
        self.assertIn("missing_license_snapshot_ref", gate["reasons"])
        self.assertFalse(gate["checks"]["external_fetch_enabled"])

    def test_dataset_without_enabled_source_quality_gate_fails(self) -> None:
        repo = self.make_repo()
        dataset = repo.save_dataset(
            {
                "source_id": "GASTAT_CANDIDATE",
                "title": "Candidate source table",
                "publisher": "General Authority for Statistics",
                "import_method": "manual_table",
                "review_status": "approved_for_use",
                "human_review_decision": "approved",
                "license_snapshot_ref": "license_snapshot:dataset",
                "terms_hash": "sha256:dataset",
                "classification": "public_open_data",
                "pdpl_check": "passed_no_personal_data",
                "attribution": "GASTAT attribution pending exact dataset",
                "rows": [{"month": "2026-01", "value": 10}],
            }
        )

        gate = api.dataset_quality_gate(dataset, repo.get_source_record(dataset["source_id"]))

        self.assertEqual(gate["status"], "failed")
        self.assertIn("source_not_enabled_by_human_review", gate["reasons"])

    def test_approved_dataset_can_link_to_assumption(self) -> None:
        repo = self.make_repo()
        repo.save_source_review(APPROVED_SOURCE)
        project = repo.create_project({"name": "Evidence link", "inputs": VALID_INPUTS})
        assumption = repo.project_assumptions(project.project_id)[0]
        dataset = repo.save_dataset(
            {
                "source_id": APPROVED_SOURCE["source_id"],
                "title": "Approved local open dataset snapshot",
                "publisher": APPROVED_SOURCE["publisher"],
                "import_method": "manual_table",
                "review_status": "approved_for_use",
                "human_review_decision": "approved",
                "license_snapshot_ref": "license_snapshot:dataset",
                "terms_hash": "sha256:dataset",
                "classification": "public_open_data",
                "pdpl_check": "passed_no_personal_data",
                "attribution": "Example attribution",
                "rows": [{"metric": "monthly_units", "value": 1600}],
            }
        )
        gate = api.dataset_quality_gate(dataset, repo.get_source_record(dataset["source_id"]))
        self.assertTrue(gate["can_use_for_assumptions"])

        link = repo.save_evidence_link(
            project.project_id,
            {
                "assumption_id": assumption["assumption_id"],
                "dataset_id": dataset["dataset_id"],
                "evidence_ref": f"dataset:{dataset['dataset_id']}:monthly_units",
                "transformation_note": "manual mapping only",
                "human_review_decision": "approved",
            },
        )
        register = api.build_evidence_register(repo, project.project_id, "draft")

        self.assertEqual(link["dataset_id"], dataset["dataset_id"])
        self.assertEqual(register["evidence_links"][0]["assumption_id"], assumption["assumption_id"])
        self.assertEqual(register["quality_gates"][0]["status"], "passed")

    def test_report_contains_dataset_evidence_links(self) -> None:
        repo = self.make_repo()
        repo.save_source_review(APPROVED_SOURCE)
        project = repo.create_project({"name": "Report evidence", "inputs": VALID_INPUTS})
        assumption = repo.project_assumptions(project.project_id)[0]
        dataset = repo.save_dataset(
            {
                "source_id": APPROVED_SOURCE["source_id"],
                "title": "Report dataset",
                "publisher": APPROVED_SOURCE["publisher"],
                "import_method": "manual_table",
                "review_status": "approved_for_use",
                "human_review_decision": "approved",
                "license_snapshot_ref": "license_snapshot:dataset",
                "terms_hash": "sha256:dataset",
                "classification": "public_open_data",
                "pdpl_check": "passed_no_personal_data",
                "attribution": "Example attribution",
                "rows": [{"metric": "monthly_units", "value": 1600}],
            }
        )
        repo.save_evidence_link(
            project.project_id,
            {
                "assumption_id": assumption["assumption_id"],
                "dataset_id": dataset["dataset_id"],
                "evidence_ref": "dataset:report:monthly_units",
                "transformation_note": "manual mapping only",
                "human_review_decision": "approved",
            },
        )

        overview, report = api.build_overview(project, repo)
        html = render_report_html(report)

        self.assertEqual(report["evidence_register"]["evidence_links"][0]["dataset_id"], dataset["dataset_id"])
        self.assertIn("سجل البيانات والأدلة", html)
        self.assertIn("Report dataset", html)
        self.assertFalse(overview["audit"]["source_fetch_enabled"])

    def test_old_snapshot_stays_stable_after_dataset_edit(self) -> None:
        repo = self.make_repo()
        repo.save_source_review(APPROVED_SOURCE)
        project = repo.create_project({"name": "Dataset stable", "inputs": VALID_INPUTS})
        dataset = repo.save_dataset(
            {
                "source_id": APPROVED_SOURCE["source_id"],
                "title": "Before edit",
                "publisher": APPROVED_SOURCE["publisher"],
                "import_method": "manual_table",
                "review_status": "approved_for_use",
                "human_review_decision": "approved",
                "license_snapshot_ref": "license_snapshot:dataset",
                "terms_hash": "sha256:dataset",
                "classification": "public_open_data",
                "pdpl_check": "passed_no_personal_data",
                "attribution": "Example attribution",
                "rows": [{"metric": "monthly_units", "value": 1600}],
            }
        )
        overview, report = api.build_overview(project, repo)
        repo.save_run_snapshot(project.project_id, overview, report)
        before = repo.get_snapshot_report(overview["snapshot"]["snapshot_id"])

        repo.review_dataset(dataset["dataset_id"], {"title": "After edit", "review_status": "archived"})
        after = repo.get_snapshot_report(overview["snapshot"]["snapshot_id"])

        self.assertEqual(before, after)
        self.assertEqual(after["evidence_register"]["datasets"][0]["title"], "Before edit")

    def test_dataset_payload_rejects_external_fetch(self) -> None:
        repo = self.make_repo()

        with self.assertRaises(PermissionError):
            repo.save_dataset(
                {
                    "source_id": "GASTAT_CANDIDATE",
                    "title": "Blocked fetch",
                    "publisher": "Example",
                    "import_method": "manual_table",
                    "fetch_url": "https://example.test/data.csv",
                }
            )

    def test_operating_capacity_derives_monthly_units(self) -> None:
        repo = self.make_repo()
        project = repo.create_project({"name": "Capacity", "inputs": OPERATIONAL_INPUTS})

        overview, _report = api.build_overview(project, repo)
        baseline = overview["finance"]["baseline"]

        self.assertEqual(overview["finance"]["operating_model"]["unit_source"], "operating_capacity")
        self.assertAlmostEqual(overview["finance"]["operating_model"]["monthly_units"], 1584.0)
        self.assertAlmostEqual(baseline["operating_model"]["monthly_units"], 1584.0)
        self.assertAlmostEqual(baseline["revenue"], 134640.0)

    def test_manual_monthly_units_remain_backward_compatible(self) -> None:
        repo = self.make_repo()
        project = repo.create_project({"name": "Manual units", "inputs": VALID_INPUTS | {"monthly_units": 1600}})

        overview, _report = api.build_overview(project, repo)

        self.assertEqual(overview["finance"]["operating_model"]["unit_source"], "manual_monthly_units")
        self.assertEqual(overview["finance"]["operating_model"]["monthly_units"], 1600.0)

    def test_opex_capex_depreciation_ebitda_and_ebit(self) -> None:
        repo = self.make_repo()
        project = repo.create_project({"name": "Operating model", "inputs": OPERATIONAL_INPUTS})

        overview, _report = api.build_overview(project, repo)
        finance = overview["finance"]
        baseline = finance["baseline"]

        self.assertEqual(finance["opex_breakdown"]["total_monthly_opex"], 58000.0)
        self.assertEqual(finance["capex_breakdown"]["total_capex"], 250000.0)
        self.assertAlmostEqual(finance["capex_breakdown"]["depreciation_monthly"], 4166.67, places=2)
        self.assertAlmostEqual(baseline["ebitda"], 22784.0)
        self.assertAlmostEqual(baseline["ebit"], 18617.33, places=2)
        self.assertIn("operational_sensitivity", finance)
        self.assertEqual(len(finance["operational_sensitivity"]["utilization_price_cells"]), 9)
        self.assertEqual(len(finance["operational_sensitivity"]["opex_demand_cells"]), 9)

    def test_debt_service_profile_not_ready_when_debt_terms_are_invalid(self) -> None:
        repo = self.make_repo()
        project = repo.create_project(
            {
                "name": "Debt not ready",
                "inputs": OPERATIONAL_INPUTS | {"debt_amount": 300000, "annual_interest_rate": 0, "loan_years": 5},
            }
        )

        overview, _report = api.build_overview(project, repo)

        self.assertEqual(overview["finance"]["status"], "ready")
        self.assertEqual(overview["finance"]["debt_service_profile"]["status"], "not_ready")
        self.assertIsNone(overview["finance"]["debt_service_profile"]["dscr"])
        self.assertEqual(overview["decision"]["sovereign_verdict"], "BLOCKED_NOT_READY")

    def test_old_snapshot_stays_stable_after_operational_input_edit(self) -> None:
        repo = self.make_repo()
        project = repo.create_project({"name": "Operational snapshot", "inputs": OPERATIONAL_INPUTS})
        overview, report = api.build_overview(project, repo)
        repo.save_run_snapshot(project.project_id, overview, report)
        before = repo.get_snapshot_report(overview["snapshot"]["snapshot_id"])

        repo.update_project(project.project_id, {"inputs": {"capacity_units_per_day": 120, "payroll_monthly": 35000}})
        after = repo.get_snapshot_report(overview["snapshot"]["snapshot_id"])

        self.assertEqual(before, after)
        self.assertEqual(after["finance"]["operating_model"]["monthly_units"], 1584.0)
        self.assertEqual(after["finance"]["opex_breakdown"]["total_monthly_opex"], 58000.0)

    def test_execution_plan_has_stable_milestones(self) -> None:
        repo = self.make_repo()
        project = repo.create_project({"name": "Execution", "inputs": OPERATIONAL_INPUTS})

        overview, report = api.build_overview(project, repo)
        phases = [item["phase_id"] for item in overview["execution_plan"]["milestones"]]

        self.assertEqual(phases, ["setup", "procurement", "staffing", "launch", "stabilization"])
        self.assertEqual(overview["execution_plan"]["estimated_total_duration_days"], 87)
        self.assertEqual(report["execution_plan"], overview["execution_plan"])

    def test_missing_evidence_and_source_create_readiness_warnings(self) -> None:
        repo = self.make_repo()
        project = repo.create_project({"name": "Warnings", "inputs": OPERATIONAL_INPUTS})

        overview, _report = api.build_overview(project, repo)
        gates = {item["gate_id"]: item for item in overview["readiness_gates"]["gates"]}

        self.assertEqual(gates["evidence_readiness"]["status"], "warning")
        self.assertIn("no_assumption_evidence_links", gates["evidence_readiness"]["reasons"])
        self.assertEqual(gates["source_governance"]["status"], "warning")
        self.assertEqual(overview["readiness_gates"]["status"], "warning")
        self.assertNotEqual(overview["run"]["status"], "blocked")

    def test_dscr_not_ready_creates_blocked_gate_and_critical_risk(self) -> None:
        repo = self.make_repo()
        project = repo.create_project(
            {
                "name": "Debt gate",
                "inputs": OPERATIONAL_INPUTS | {"debt_amount": 300000, "annual_interest_rate": 0, "loan_years": 5},
            }
        )

        overview, _report = api.build_overview(project, repo)
        gates = {item["gate_id"]: item for item in overview["readiness_gates"]["gates"]}
        risks = {item["risk_id"]: item for item in overview["risk_register"]["risks"]}

        self.assertEqual(gates["debt_service"]["status"], "blocked")
        self.assertEqual(overview["execution_plan"]["status"], "blocked")
        self.assertEqual(risks["dscr_risk"]["severity"], "critical")
        self.assertEqual(overview["decision"]["sovereign_verdict"], "BLOCKED_NOT_READY")

    def test_old_snapshot_stays_stable_after_risk_execution_input_edit(self) -> None:
        repo = self.make_repo()
        project = repo.create_project({"name": "Risk stable", "inputs": OPERATIONAL_INPUTS})
        overview, report = api.build_overview(project, repo)
        repo.save_run_snapshot(project.project_id, overview, report)
        before = repo.get_snapshot_report(overview["snapshot"]["snapshot_id"])

        repo.update_project(project.project_id, {"inputs": {"debt_amount": 500000, "annual_interest_rate": 0}})
        after = repo.get_snapshot_report(overview["snapshot"]["snapshot_id"])

        self.assertEqual(before, after)
        self.assertEqual(after["execution_plan"]["milestones"][0]["phase_id"], "setup")
        self.assertEqual(after["risk_register"]["risks"][0]["risk_id"], "funding_risk")

    def test_decision_pack_reads_saved_snapshot_without_recalculation(self) -> None:
        repo = self.make_repo()
        project = repo.create_project({"name": "Decision pack stable", "inputs": OPERATIONAL_INPUTS})
        overview, report = api.build_overview(project, repo)
        repo.save_run_snapshot(project.project_id, overview, report)
        stored_overview = repo.get_snapshot_overview(overview["snapshot"]["snapshot_id"])
        stored_report = repo.get_snapshot_report(overview["snapshot"]["snapshot_id"])

        repo.update_project(project.project_id, {"inputs": {"monthly_units": 9999, "unit_price": 220}})
        pack = build_decision_pack(stored_overview, stored_report, [])

        self.assertTrue(pack["immutable_snapshot"])
        self.assertEqual(pack["snapshot_id"], overview["snapshot"]["snapshot_id"])
        self.assertEqual(pack["finance_highlights"]["npv"], overview["finance"]["baseline"]["npv"])
        self.assertEqual(pack["memo"]["recommendation"], overview["decision"]["sovereign_verdict"])

    def test_decision_pack_runtime_base_is_snapshot_only_and_review_overlay_hash_is_separate(self) -> None:
        repo = self.make_repo()
        project = repo.create_project({"name": "Decision pack runtime", "inputs": OPERATIONAL_INPUTS})
        overview, report = api.build_overview(project, repo)
        repo.save_run_snapshot(project.project_id, overview, report)
        stored_overview = repo.get_snapshot_overview(overview["snapshot"]["snapshot_id"])
        stored_report = repo.get_snapshot_report(overview["snapshot"]["snapshot_id"])

        base_pack = api.decision_pack_via_module_runtime(stored_overview, stored_report)
        review = repo.save_snapshot_review(
            overview["snapshot"]["snapshot_id"],
            overview["run"]["run_id"],
            project.project_id,
            {"reviewer": "human-reviewer", "decision": "approved_local", "notes": "local only"},
        )
        reviewed_pack = api.apply_review_overlay(base_pack, [review])

        self.assertEqual(base_pack["contract_id"], "decision.pack.v1")
        self.assertIsNone(base_pack["review_overlay"])
        self.assertEqual(base_pack["reviews"], [])
        self.assertEqual(reviewed_pack["decision_pack_hash"], base_pack["decision_pack_hash"])
        self.assertEqual(reviewed_pack["memo"]["recommendation"], base_pack["memo"]["recommendation"])
        self.assertEqual(reviewed_pack["memo"]["review_status"], "approved_local")
        self.assertTrue(reviewed_pack["review_overlay"]["separate_from_snapshot_hash"])
        self.assertEqual(
            reviewed_pack["review_overlay"]["base_decision_pack_hash"],
            base_pack["decision_pack_hash"],
        )
        self.assertEqual(
            reviewed_pack["snapshot_assembly"]["integrity_hash"],
            overview["snapshot"]["integrity_hash"],
        )

    def test_decision_pack_runtime_rejects_tampered_saved_projection(self) -> None:
        repo = self.make_repo()
        project = repo.create_project({"name": "Decision pack tamper guard", "inputs": OPERATIONAL_INPUTS})
        overview, report = api.build_overview(project, repo)
        tampered_overview = overview | {"finance": overview["finance"] | {"status": "tampered"}}

        with self.assertRaisesRegex(ValueError, "overview_projection_hash_mismatch"):
            api.decision_pack_via_module_runtime(tampered_overview, report)

    def test_review_decision_saves_on_snapshot_without_changing_verdict(self) -> None:
        repo = self.make_repo()
        project = repo.create_project({"name": "Review", "inputs": OPERATIONAL_INPUTS})
        overview, report = api.build_overview(project, repo)
        repo.save_run_snapshot(project.project_id, overview, report)
        before_verdict = repo.get_snapshot_overview(overview["snapshot"]["snapshot_id"])["decision"]["sovereign_verdict"]

        review = repo.save_snapshot_review(
            overview["snapshot"]["snapshot_id"],
            overview["run"]["run_id"],
            project.project_id,
            {"reviewer": "local-reviewer", "decision": "approved_local", "notes": "ok"},
        )
        pack = build_decision_pack(
            repo.get_snapshot_overview(overview["snapshot"]["snapshot_id"]),
            repo.get_snapshot_report(overview["snapshot"]["snapshot_id"]),
            repo.snapshot_reviews(overview["snapshot"]["snapshot_id"]),
        )
        after_verdict = repo.get_snapshot_overview(overview["snapshot"]["snapshot_id"])["decision"]["sovereign_verdict"]

        self.assertEqual(review["snapshot_id"], overview["snapshot"]["snapshot_id"])
        self.assertEqual(pack["latest_review"]["decision"], "approved_local")
        self.assertEqual(before_verdict, after_verdict)

    def test_action_items_generate_and_close_without_snapshot_mutation(self) -> None:
        repo = self.make_repo()
        project = repo.create_project({"name": "Action items", "inputs": OPERATIONAL_INPUTS})
        overview, report = api.build_overview(project, repo)
        repo.save_run_snapshot(project.project_id, overview, report)
        before = repo.get_snapshot_report(overview["snapshot"]["snapshot_id"])
        items = build_action_items_from_overview(project.project_id, overview, {})

        self.assertTrue(any(item["source_type"] == "gate" for item in items))
        target = items[0]
        repo.save_action_item_state(project.project_id, target["action_item_id"], {"status": "closed", "notes": "done"})
        merged = build_action_items_from_overview(
            project.project_id,
            overview,
            repo.project_action_item_states(project.project_id),
        )
        after = repo.get_snapshot_report(overview["snapshot"]["snapshot_id"])

        self.assertEqual(before, after)
        self.assertEqual(next(item for item in merged if item["action_item_id"] == target["action_item_id"])["status"], "closed")

    def test_decision_pack_html_contains_snapshot_run_and_audit_lineage(self) -> None:
        repo = self.make_repo()
        project = repo.create_project({"name": "Decision HTML", "inputs": OPERATIONAL_INPUTS})
        overview, report = api.build_overview(project, repo)
        pack = build_decision_pack(overview, report, [])
        html = render_decision_pack_html(pack)

        self.assertIn(overview["snapshot"]["snapshot_id"], html)
        self.assertIn(overview["run"]["run_id"], html)
        self.assertIn(overview["audit"]["audit_id"], html)
        self.assertIn("مذكرة القرار", html)

    def test_sector_intelligence_result_is_saved_in_snapshot(self) -> None:
        repo = self.make_repo()
        project = repo.create_project({"name": "Sector project", "inputs": SECTOR_INPUTS})

        overview, report = api.build_overview(project, repo)

        self.assertEqual(overview["sector_intelligence"]["status"], "ready")
        self.assertEqual(overview["sector_intelligence"]["taxonomy_record"]["primary_sector_id"], "SEC-11")
        self.assertEqual(report["sector_intelligence"], overview["sector_intelligence"])
        self.assertFalse(overview["sector_intelligence"]["external_fetch_enabled"])

    def test_missing_sector_returns_readiness_warning_without_external_fetch(self) -> None:
        repo = self.make_repo()
        project = repo.create_project({"name": "No sector", "inputs": OPERATIONAL_INPUTS})

        overview, _report = api.build_overview(project, repo)
        readiness_steps = {row["step_id"]: row for row in overview["readiness"]["steps"]}

        self.assertEqual(overview["sector_intelligence"]["status"], "needs_input")
        self.assertEqual(readiness_steps["sector_intelligence"]["status"], "needs_review")
        self.assertIn("missing_primary_sector_id", overview["sector_intelligence"]["not_ready_reasons"])
        self.assertFalse(overview["sector_intelligence"]["external_fetch_enabled"])

    def test_each_sector_criterion_has_evidence_status(self) -> None:
        repo = self.make_repo()
        project = repo.create_project({"name": "Sector criteria", "inputs": SECTOR_INPUTS})

        overview, _report = api.build_overview(project, repo)
        statuses = {row["evidence_status"] for row in overview["sector_intelligence"]["sector_criteria"]["criteria"]}

        self.assertTrue(statuses)
        self.assertTrue(statuses.issubset({"supported", "needs_evidence", "reference_only"}))
        self.assertTrue(overview["sector_intelligence"]["sector_evidence_map"]["evidence_gaps"])

    def test_old_snapshot_stays_stable_after_sector_edit(self) -> None:
        repo = self.make_repo()
        project = repo.create_project({"name": "Sector stable", "inputs": SECTOR_INPUTS})
        overview, report = api.build_overview(project, repo)
        repo.save_run_snapshot(project.project_id, overview, report)
        before = repo.get_snapshot_report(overview["snapshot"]["snapshot_id"])

        repo.update_project(project.project_id, {"inputs": {"primary_sector_id": "SEC-07", "subsector_id": "Commercial Real Estate"}})
        after = repo.get_snapshot_report(overview["snapshot"]["snapshot_id"])

        self.assertEqual(before, after)
        self.assertEqual(after["sector_intelligence"]["taxonomy_record"]["primary_sector_id"], "SEC-11")

    def test_sector_source_candidates_do_not_enable_automatically(self) -> None:
        repo = self.make_repo()
        project = repo.create_project({"name": "Sector sources", "inputs": SECTOR_INPUTS})

        overview, _report = api.build_overview(project, repo)
        source_states = {row["source_id"]: row["state"] for row in overview["sector_intelligence"]["source_candidates"]}

        self.assertIn("GASTAT_CANDIDATE", source_states)
        self.assertNotIn("enabled", set(source_states.values()))
        self.assertFalse(any(row["can_contribute_data_now"] for row in overview["sector_intelligence"]["source_candidates"]))

    def test_decision_council_reads_sector_without_vote_or_ai(self) -> None:
        repo = self.make_repo()
        project = repo.create_project({"name": "Sector council", "inputs": SECTOR_INPUTS})

        overview, _report = api.build_overview(project, repo)

        self.assertTrue(overview["decision_council"]["no_vote"])
        self.assertFalse(overview["decision"]["advisory_consensus_visible_as_verdict"])
        self.assertTrue(
            all("sector.intelligence.v1" in persona["permitted_input_refs"] for persona in overview["personas"])
        )

    def test_manual_csv_dataset_creates_column_profile_without_external_fetch(self) -> None:
        repo = self.make_repo()
        dataset = repo.save_dataset(
            {
                "source_id": "GASTAT_CANDIDATE",
                "title": "Manual CSV",
                "publisher": "ASIE local manual entry",
                "import_method": "manual_csv",
                "review_status": "review_required",
                "csv_text": "metric,value,unit\nmonthly_units,1600,count\nunit_price,,SAR\nunit_price,85,SAR",
            }
        )

        profile = dataset["notes"]["profile"]

        self.assertEqual(dataset["row_count"], 3)
        self.assertEqual(profile["value"]["row_count"], 3)
        self.assertEqual(profile["value"]["missing_count"], 1)
        self.assertFalse(dataset["notes"]["external_fetch_allowed"])

    def test_dataset_quality_review_rejects_extreme_missing_values(self) -> None:
        repo = self.make_repo()
        repo.save_source_review(APPROVED_SOURCE)
        dataset = repo.save_dataset(
            {
                "source_id": APPROVED_SOURCE["source_id"],
                "title": "Bad quality dataset",
                "publisher": APPROVED_SOURCE["publisher"],
                "import_method": "manual_csv",
                "review_status": "approved_for_use",
                "human_review_decision": "approved",
                "license_snapshot_ref": "license_snapshot:bad-quality",
                "terms_hash": "sha256:bad-quality",
                "classification": "public_open_data",
                "pdpl_check": "passed_no_personal_data",
                "attribution": "Example attribution",
                "csv_text": "metric,value\nmarket_size,\nmarket_size,\nmarket_size,\nmarket_size,\nmarket_size,100",
            }
        )

        gate = api.dataset_quality_gate(dataset, repo.get_source_record(dataset["source_id"]))

        self.assertEqual(dataset["notes"]["quality_review"]["status"], "rejected")
        self.assertEqual(gate["status"], "rejected")
        self.assertFalse(gate["can_use_for_assumptions"])
        self.assertIn("missing_values_above_80_percent", gate["reasons"])

    def test_dataset_quality_warning_can_still_support_after_review(self) -> None:
        repo = self.make_repo()
        repo.save_source_review(APPROVED_SOURCE)
        dataset = repo.save_dataset(
            {
                "source_id": APPROVED_SOURCE["source_id"],
                "title": "Warning quality dataset",
                "publisher": APPROVED_SOURCE["publisher"],
                "import_method": "manual_table",
                "review_status": "approved_for_use",
                "human_review_decision": "approved",
                "license_snapshot_ref": "license_snapshot:warning-quality",
                "terms_hash": "sha256:warning-quality",
                "classification": "public_open_data",
                "pdpl_check": "passed_no_personal_data",
                "attribution": "Example attribution",
                "rows": [
                    {"metric": "market_size", "value": 100},
                    {"metric": "market_size", "value": 100},
                    {"metric": "market_size", "value": 120},
                ],
            }
        )

        gate = api.dataset_quality_gate(dataset, repo.get_source_record(dataset["source_id"]))

        self.assertEqual(gate["status"], "warning")
        self.assertTrue(gate["can_use_for_assumptions"])
        self.assertIn("duplicate_rows_detected", gate["quality_review"]["reasons"])

    def test_xlsx_file_import_creates_column_profile_without_external_fetch(self) -> None:
        repo = self.make_repo()
        dataset = repo.save_dataset(
            api.normalize_file_import_payload(
                {
                    "source_id": "GASTAT_CANDIDATE",
                    "file_name": "local-market.xlsx",
                    "file_base64": make_xlsx_base64([["metric", "value"], ["market_size", "100"], ["market_size", "120"]]),
                    "publisher": "ASIE local file import",
                    "review_status": "review_required",
                }
            )
        )

        profile = dataset["notes"]["profile"]

        self.assertEqual(dataset["row_count"], 2)
        self.assertEqual(dataset["import_method"], "manual_table")
        self.assertEqual(profile["value"]["mean"], 110)
        self.assertFalse(dataset["notes"]["external_fetch_allowed"])

    def test_unapproved_dataset_cannot_support_evidence_target(self) -> None:
        repo = self.make_repo()
        project = repo.create_project({"name": "Ungated evidence", "inputs": SECTOR_INPUTS})
        dataset = repo.save_dataset(
            {
                "source_id": "GASTAT_CANDIDATE",
                "title": "Unapproved local table",
                "publisher": "ASIE local manual entry",
                "import_method": "manual_table",
                "review_status": "review_required",
                "rows": [{"metric": "market_size", "value": 1}],
            }
        )
        repo.save_evidence_link(
            project.project_id,
            {
                "target_type": "sector_criterion",
                "target_id": "market_size",
                "dataset_id": dataset["dataset_id"],
                "evidence_ref": "dataset:unapproved:market_size",
                "transformation_note": "manual mapping",
                "human_review_decision": "approved",
            },
        )

        overview, _report = api.build_overview(project, repo)
        market_size = next(
            row for row in overview["sector_intelligence"]["sector_criteria"]["criteria"] if row["criterion_id"] == "market_size"
        )

        self.assertEqual(market_size["evidence_status"], "needs_evidence")
        self.assertFalse(overview["evidence_ledger"][0]["can_support_target"])

    def test_approved_dataset_binding_supports_sector_criterion(self) -> None:
        repo = self.make_repo()
        repo.save_source_review(APPROVED_GASTAT_SOURCE)
        project = repo.create_project({"name": "Sector supported", "inputs": SECTOR_INPUTS})
        dataset = repo.save_dataset(
            {
                "source_id": "GASTAT_CANDIDATE",
                "title": "Approved sector dataset",
                "publisher": "General Authority for Statistics",
                "import_method": "manual_table",
                "review_status": "approved_for_use",
                "human_review_decision": "approved",
                "license_snapshot_ref": "license_snapshot:sector",
                "terms_hash": "sha256:sector",
                "classification": "public_open_data",
                "pdpl_check": "passed_no_personal_data",
                "attribution": "GASTAT attribution",
                "rows": [{"metric": "market_size", "value": 100}],
            }
        )
        repo.save_evidence_link(
            project.project_id,
            {
                "target_type": "sector_criterion",
                "target_id": "market_size",
                "dataset_id": dataset["dataset_id"],
                "evidence_ref": "dataset:sector:market_size",
                "transformation_note": "manual sector mapping",
                "human_review_decision": "approved",
            },
        )

        overview, report = api.build_overview(project, repo)
        market_size = next(
            row for row in overview["sector_intelligence"]["sector_criteria"]["criteria"] if row["criterion_id"] == "market_size"
        )

        self.assertEqual(market_size["evidence_status"], "supported")
        self.assertTrue(overview["evidence_ledger"][0]["can_support_target"])
        self.assertEqual(report["evidence_ledger"], overview["evidence_ledger"])
        self.assertEqual(report["evidence_coverage"], overview["evidence_coverage"])

    def test_approved_transformation_binds_dataset_to_target_lineage(self) -> None:
        repo = self.make_repo()
        repo.save_source_review(APPROVED_GASTAT_SOURCE)
        project = repo.create_project({"name": "Transformation lineage", "inputs": SECTOR_INPUTS})
        dataset = repo.save_dataset(
            {
                "source_id": "GASTAT_CANDIDATE",
                "title": "Approved transform dataset",
                "publisher": "General Authority for Statistics",
                "import_method": "manual_table",
                "review_status": "approved_for_use",
                "human_review_decision": "approved",
                "license_snapshot_ref": "license_snapshot:transform",
                "terms_hash": "sha256:transform",
                "classification": "public_open_data",
                "pdpl_check": "passed_no_personal_data",
                "attribution": "GASTAT attribution",
                "rows": [{"metric": "market_size", "value": 100}, {"metric": "market_size", "value": 120}],
            }
        )
        transformation = repo.save_transformation(
            dataset["dataset_id"],
            {
                "operation_type": "aggregate_average",
                "input_columns": ["value"],
                "output_unit": "index",
                "review_status": "approved",
            },
        )
        repo.save_evidence_link(
            project.project_id,
            {
                "target_type": "sector_criterion",
                "target_id": "market_size",
                "dataset_id": dataset["dataset_id"],
                "transformation_id": transformation["transformation_id"],
                "evidence_ref": "dataset:transform:market_size",
                "transformation_note": "average value from backend transformation",
                "human_review_decision": "approved",
            },
        )

        overview, report = api.build_overview(project, repo)
        pack = build_decision_pack(overview, report, [])
        market_size = next(
            row for row in overview["sector_intelligence"]["sector_criteria"]["criteria"] if row["criterion_id"] == "market_size"
        )

        self.assertEqual(transformation["output_value"], "110.00")
        self.assertEqual(market_size["evidence_status"], "supported")
        self.assertEqual(overview["evidence_ledger"][0]["transformation_id"], transformation["transformation_id"])
        self.assertTrue(overview["evidence_ledger"][0]["can_support_target"])
        self.assertEqual(overview["evidence_ledger"][0]["data_quality_status"], "passed")
        self.assertEqual(overview["evidence_ledger"][0]["transformation_quality_status"], "passed")
        self.assertGreaterEqual(overview["evidence_ledger"][0]["evidence_confidence_score"], 0.8)
        self.assertEqual(report["transformation_lineage"], overview["transformation_lineage"])
        self.assertEqual(pack["transformation_lineage"], overview["transformation_lineage"])

    def test_unapproved_transformation_cannot_support_target(self) -> None:
        repo = self.make_repo()
        repo.save_source_review(APPROVED_GASTAT_SOURCE)
        project = repo.create_project({"name": "Transformation not reviewed", "inputs": SECTOR_INPUTS})
        dataset = repo.save_dataset(
            {
                "source_id": "GASTAT_CANDIDATE",
                "title": "Unapproved transform dataset",
                "publisher": "General Authority for Statistics",
                "import_method": "manual_table",
                "review_status": "approved_for_use",
                "human_review_decision": "approved",
                "license_snapshot_ref": "license_snapshot:transform",
                "terms_hash": "sha256:transform",
                "classification": "public_open_data",
                "pdpl_check": "passed_no_personal_data",
                "attribution": "GASTAT attribution",
                "rows": [{"metric": "market_size", "value": 100}],
            }
        )
        transformation = repo.save_transformation(
            dataset["dataset_id"],
            {"operation_type": "aggregate_average", "input_columns": ["value"], "review_status": "review_required"},
        )
        repo.save_evidence_link(
            project.project_id,
            {
                "target_type": "sector_criterion",
                "target_id": "market_size",
                "dataset_id": dataset["dataset_id"],
                "transformation_id": transformation["transformation_id"],
                "evidence_ref": "dataset:transform:market_size",
                "transformation_note": "pending transformation review",
                "human_review_decision": "approved",
            },
        )

        overview, _report = api.build_overview(project, repo)
        market_size = next(
            row for row in overview["sector_intelligence"]["sector_criteria"]["criteria"] if row["criterion_id"] == "market_size"
        )

        self.assertEqual(market_size["evidence_status"], "needs_evidence")
        self.assertFalse(overview["evidence_ledger"][0]["can_support_target"])
        self.assertEqual(overview["evidence_ledger"][0]["transformation_status"], "review_required")
        self.assertEqual(overview["evidence_ledger"][0]["transformation_quality_status"], "warning")

    def test_old_snapshot_stays_stable_after_transformation_edit(self) -> None:
        repo = self.make_repo()
        repo.save_source_review(APPROVED_GASTAT_SOURCE)
        project = repo.create_project({"name": "Transformation stable", "inputs": SECTOR_INPUTS})
        dataset = repo.save_dataset(
            {
                "source_id": "GASTAT_CANDIDATE",
                "title": "Stable transform dataset",
                "publisher": "General Authority for Statistics",
                "import_method": "manual_table",
                "review_status": "approved_for_use",
                "human_review_decision": "approved",
                "license_snapshot_ref": "license_snapshot:transform",
                "terms_hash": "sha256:transform",
                "classification": "public_open_data",
                "pdpl_check": "passed_no_personal_data",
                "attribution": "GASTAT attribution",
                "rows": [{"metric": "market_size", "value": 100}],
            }
        )
        transformation = repo.save_transformation(
            dataset["dataset_id"],
            {"operation_type": "aggregate_average", "input_columns": ["value"], "review_status": "approved"},
        )
        repo.save_evidence_link(
            project.project_id,
            {
                "target_type": "sector_criterion",
                "target_id": "market_size",
                "dataset_id": dataset["dataset_id"],
                "transformation_id": transformation["transformation_id"],
                "evidence_ref": "dataset:transform:market_size",
                "transformation_note": "before",
                "human_review_decision": "approved",
            },
        )
        overview, report = api.build_overview(project, repo)
        repo.save_run_snapshot(project.project_id, overview, report)
        before = repo.get_snapshot_report(overview["snapshot"]["snapshot_id"])

        repo.save_transformation(
            dataset["dataset_id"],
            {
                "transformation_id": transformation["transformation_id"],
                "operation_type": "aggregate_sum",
                "input_columns": ["value"],
                "review_status": "approved",
            },
        )
        after = repo.get_snapshot_report(overview["snapshot"]["snapshot_id"])

        self.assertEqual(before, after)
        self.assertEqual(after["transformation_lineage"][0]["operation_type"], "aggregate_average")

    def test_evidence_ledger_snapshot_stays_stable_after_link_edit(self) -> None:
        repo = self.make_repo()
        repo.save_source_review(APPROVED_GASTAT_SOURCE)
        project = repo.create_project({"name": "Ledger stable", "inputs": SECTOR_INPUTS})
        dataset = repo.save_dataset(
            {
                "source_id": "GASTAT_CANDIDATE",
                "title": "Before ledger edit",
                "publisher": "General Authority for Statistics",
                "import_method": "manual_table",
                "review_status": "approved_for_use",
                "human_review_decision": "approved",
                "license_snapshot_ref": "license_snapshot:ledger",
                "terms_hash": "sha256:ledger",
                "classification": "public_open_data",
                "pdpl_check": "passed_no_personal_data",
                "attribution": "GASTAT attribution",
                "rows": [{"metric": "market_size", "value": 100}],
            }
        )
        repo.save_evidence_link(
            project.project_id,
            {
                "target_type": "sector_criterion",
                "target_id": "market_size",
                "dataset_id": dataset["dataset_id"],
                "evidence_ref": "dataset:ledger:market_size",
                "transformation_note": "before",
                "human_review_decision": "approved",
            },
        )
        overview, report = api.build_overview(project, repo)
        repo.save_run_snapshot(project.project_id, overview, report)
        before = repo.get_snapshot_report(overview["snapshot"]["snapshot_id"])

        repo.save_evidence_link(
            project.project_id,
            {
                "target_type": "sector_criterion",
                "target_id": "competition_intensity",
                "dataset_id": dataset["dataset_id"],
                "evidence_ref": "dataset:ledger:competition",
                "transformation_note": "after",
                "human_review_decision": "approved",
            },
        )
        after = repo.get_snapshot_report(overview["snapshot"]["snapshot_id"])

        self.assertEqual(before, after)
        self.assertEqual(after["evidence_ledger"][0]["target_id"], "market_size")

    def test_architecture_runtime_status_endpoint_is_read_only(self) -> None:
        server = api.ThreadingHTTPServer(("127.0.0.1", 0), api.Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        port = server.server_address[1]

        get_status, get_body = request_local_json(port, "GET", "/api/architecture/runtime-status")
        self.assertEqual(get_status, 200)
        self.assertEqual(get_body["mutability"], "read_only_projection")
        self.assertFalse(get_body["guards"]["allows_runtime_mutation"])
        self.assertEqual(get_body["allowed_methods"], ["GET"])

        for method in ("POST", "PATCH", "PUT", "DELETE"):
            with self.subTest(method=method):
                status, body = request_local_json(
                    port,
                    method,
                    "/api/architecture/runtime-status",
                    body='{"attempt":"mutate"}' if method in {"POST", "PATCH"} else None,
                )
                self.assertEqual(status, 405)
                self.assertEqual(body["error"], "architecture_runtime_status_is_read_only")
                self.assertEqual(body["mutability"], "read_only_projection")
                self.assertFalse(body["allows_runtime_mutation"])


def make_xlsx_base64(rows: list[list[str]]) -> str:
    shared_strings: list[str] = []

    def shared_index(value: str) -> int:
        if value not in shared_strings:
            shared_strings.append(value)
        return shared_strings.index(value)

    sheet_rows = []
    for row_index, row in enumerate(rows, start=1):
        cells = []
        for col_index, value in enumerate(row):
            column = chr(ord("A") + col_index)
            cells.append(f'<c r="{column}{row_index}" t="s"><v>{shared_index(str(value))}</v></c>')
        sheet_rows.append(f'<row r="{row_index}">{"".join(cells)}</row>')

    shared_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        + "".join(f"<si><t>{value}</t></si>" for value in shared_strings)
        + "</sst>"
    )
    sheet_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetData>{"".join(sheet_rows)}</sheetData></worksheet>'
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("xl/sharedStrings.xml", shared_xml)
        archive.writestr("xl/worksheets/sheet1.xml", sheet_xml)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def request_local_json(port: int, method: str, path: str, body: str | None = None) -> tuple[int, dict]:
    connection = HTTPConnection("127.0.0.1", port, timeout=10)
    try:
        headers = {"Content-Type": "application/json"}
        connection.request(method, path, body=body, headers=headers)
        response = connection.getresponse()
        raw = response.read().decode("utf-8")
        return response.status, api.json.loads(raw)
    finally:
        connection.close()


if __name__ == "__main__":
    unittest.main()
