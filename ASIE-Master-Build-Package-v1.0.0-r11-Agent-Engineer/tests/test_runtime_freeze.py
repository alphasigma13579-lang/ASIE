from __future__ import annotations

import ast
import hashlib
import inspect
import json
import tempfile
import textwrap
import unittest
import warnings
from pathlib import Path
from unittest.mock import patch

from backend import asie_local_api as api
from backend.project_run_workflow import ProjectRunEnvelope, ProjectRunIdempotencyStore, ProjectRunWorkflow


FREEZE_INPUTS = {
    "startup_cost": 250000,
    "monthly_fixed_cost": 62000,
    "unit_price": 85,
    "variable_cost": 34,
    "monthly_units": 1600,
    "annual_discount_rate": 0.10,
    "working_capital_months": 2,
}


def referenced_symbols(value: object) -> set[str]:
    tree = ast.parse(textwrap.dedent(inspect.getsource(value)))
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    attributes = {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
    return names | attributes


class RuntimeFreezeTests(unittest.TestCase):
    def make_repo(self) -> api.Repository:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        return api.Repository(Path(temp_dir.name) / "asie-freeze-test.sqlite3")

    def make_envelope(self, project_id: str, suffix: str) -> ProjectRunEnvelope:
        return ProjectRunEnvelope(
            project_id=project_id,
            scenario_id="baseline",
            operation_id=f"op_freeze_{suffix}",
            idempotency_key=f"idem_freeze_{suffix}",
            input_hash=f"sha256:freeze:{suffix}",
            run_id=f"run_freeze_{suffix}",
            snapshot_id=f"snap_freeze_{suffix}",
            source_module_id="aas.heart.M1",
        )

    def test_legacy_build_overview_is_deprecated_and_always_converts_to_run_envelope(self) -> None:
        repo = self.make_repo()
        project = repo.create_project({"name": "Legacy parity fixture", "inputs": FREEZE_INPUTS})

        self.assertIn("legacy parity tests only", api.build_overview.__deprecated__)
        self.assertEqual(api.BUILD_OVERVIEW_REMOVAL_TARGET, "AAS Runtime v1.1")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            with self.assertRaisesRegex(TypeError, "legacy ProjectRecord fixtures only"):
                api.build_overview({}, repo)
            with self.assertRaisesRegex(TypeError, "legacy Repository fixtures only"):
                api.build_overview(project, object())

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", DeprecationWarning)
            with patch.object(api, "execute_project_run_pipeline", return_value=({}, {})) as execute:
                api.build_overview(project, repo)

        run_envelope = execute.call_args.args[0]
        self.assertIsInstance(run_envelope, ProjectRunEnvelope)
        self.assertEqual(run_envelope.project_id, project.project_id)
        self.assertEqual(execute.call_args.kwargs, {"project": project, "data_access": repo})
        self.assertTrue(any("legacy parity tests only" in str(row.message) for row in caught))

    def test_http_routes_do_not_reference_legacy_build_overview(self) -> None:
        self.assertNotIn("build_overview", referenced_symbols(api.Handler))

    def test_project_run_workflow_does_not_reference_legacy_build_overview(self) -> None:
        self.assertNotIn("build_overview", referenced_symbols(ProjectRunWorkflow))

    def test_pipeline_uses_one_session_and_all_core_engines_cross_bus_socket(self) -> None:
        api.reset_local_module_runtime_for_tests()
        repo = self.make_repo()
        project = repo.create_project({"name": "Freeze bus path", "inputs": FREEZE_INPUTS})
        run_envelope = self.make_envelope(project.project_id, "bus_path")
        real_session = api.RunScopedModuleRuntime

        with patch.object(api, "RunScopedModuleRuntime", side_effect=real_session) as session_constructor:
            overview, _report = api.execute_project_run_pipeline(
                run_envelope,
                project=project,
                data_access=repo,
            )

        records = [
            record
            for record in api.local_runtime_context().bus.messages
            if record["message"].get("operation_id") == run_envelope.operation_id
        ]
        pipeline_records = [
            record
            for record in records
            if record["message"].get("contract_id") in run_envelope.pipeline_contract_sequence
        ]
        self.assertEqual(session_constructor.call_count, 1)
        self.assertEqual(
            tuple(record["message"]["contract_id"] for record in pipeline_records),
            run_envelope.pipeline_contract_sequence,
        )
        self.assertTrue(all(record["delivered"] for record in pipeline_records))
        self.assertTrue(all(record["admission"]["reason"] == "accepted" for record in pipeline_records))
        self.assertEqual(
            {row["output_key"] for row in overview["snapshot_assembly"]["lineage"]},
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
        self.assertEqual(
            sum(record["message"]["contract_id"] == "snapshot.assemble.v1" for record in records),
            1,
        )

        direct_engine_symbols = {
            "finance_result_set",
            "build_evidence_ledger",
            "build_sector_intelligence",
            "evaluate_decision_council",
            "build_risk_register",
            "build_execution_plan",
        }
        self.assertTrue(direct_engine_symbols.isdisjoint(referenced_symbols(api.execute_project_run_pipeline)))

    def test_idempotency_replay_does_not_create_second_snapshot(self) -> None:
        api.reset_local_module_runtime_for_tests()
        repo = self.make_repo()
        project = repo.create_project({"name": "Freeze replay", "inputs": FREEZE_INPUTS})
        request = api.normalize_project_run_http_request(
            project.project_id,
            {"scenario_id": "baseline", "idempotency_key": "idem_freeze_replay"},
        )
        context = api.local_runtime_context()
        workflow = ProjectRunWorkflow(context.runtime, ProjectRunIdempotencyStore())

        def build(run_envelope: ProjectRunEnvelope) -> tuple[dict, dict]:
            return api.execute_project_run_pipeline(run_envelope, project=project, data_access=repo)

        def save(overview: dict, report: dict) -> dict[str, str]:
            return repo.save_run_snapshot(project.project_id, overview, report)

        first = workflow.run(request, build=build, save=save)
        replayed = workflow.run(request, build=build, save=save)

        assembly_records = [
            record
            for record in context.bus.messages
            if record["message"].get("operation_id") == request["operation_id"]
            and record["message"].get("contract_id") == "snapshot.assemble.v1"
        ]
        self.assertFalse(first.idempotency_replayed)
        self.assertTrue(replayed.idempotency_replayed)
        self.assertEqual(first.snapshot_id, replayed.snapshot_id)
        self.assertEqual(len(repo.list_project_runs(project.project_id)), 1)
        self.assertEqual(len(assembly_records), 1)

    def test_failed_module_output_prevents_partial_snapshot(self) -> None:
        api.reset_local_module_runtime_for_tests()
        repo = self.make_repo()
        project = repo.create_project({"name": "Freeze failed output", "inputs": FREEZE_INPUTS})
        request = api.normalize_project_run_http_request(
            project.project_id,
            {"scenario_id": "baseline", "idempotency_key": "idem_freeze_failure"},
        )
        context = api.local_runtime_context()
        workflow = ProjectRunWorkflow(context.runtime, ProjectRunIdempotencyStore())

        with patch.object(api, "risk_register_via_module_runtime", side_effect=RuntimeError("risk output failed")):
            with self.assertRaisesRegex(RuntimeError, "risk output failed"):
                workflow.run(
                    request,
                    build=lambda run_envelope: api.execute_project_run_pipeline(
                        run_envelope,
                        project=project,
                        data_access=repo,
                    ),
                    save=lambda overview, report: repo.save_run_snapshot(project.project_id, overview, report),
                )

        operation_contracts = [
            record["message"].get("contract_id")
            for record in context.bus.messages
            if record["message"].get("operation_id") == request["operation_id"]
        ]
        self.assertNotIn("snapshot.assemble.v1", operation_contracts)
        self.assertEqual(repo.list_project_runs(project.project_id), [])

    def test_report_and_decision_pack_runtime_paths_do_not_reference_engines(self) -> None:
        direct_engine_symbols = {
            "finance_result_set",
            "build_evidence_ledger",
            "build_sector_intelligence",
            "evaluate_decision_council",
            "build_risk_register",
            "build_execution_plan",
        }
        self.assertTrue(direct_engine_symbols.isdisjoint(referenced_symbols(api.report_via_module_runtime)))
        self.assertTrue(direct_engine_symbols.isdisjoint(referenced_symbols(api.decision_pack_via_module_runtime)))

    def test_runtime_status_declares_freeze_and_acr_control(self) -> None:
        status = api.build_architecture_runtime_status()

        self.assertEqual(status["runtime_freeze"]["status"], "frozen")
        self.assertEqual(status["runtime_freeze"]["version"], "1.0")
        self.assertEqual(status["runtime_freeze"]["effective_at"], "2026-07-19T00:22:00+03:00")
        self.assertEqual(status["runtime_freeze"]["timezone"], "Asia/Riyadh")
        self.assertTrue(status["runtime_freeze"]["architectural_change_request_required"])
        self.assertFalse(status["runtime_freeze"]["legacy_compatibility"]["production_reachable"])
        self.assertTrue(status["guards"]["requires_architectural_change_request"])
        self.assertEqual(status["final_aas_acceptance"]["status"], "passed")

    def test_frozen_runtime_files_match_freeze_manifest(self) -> None:
        workspace = Path(api.__file__).resolve().parent.parent
        manifest = json.loads(
            (workspace / "docs" / "ASIE-AAS-Runtime-Freeze-Manifest-v1.0.json").read_text(encoding="utf-8")
        )

        self.assertEqual(manifest["status"], "frozen")
        self.assertEqual(manifest["change_control"], "architectural_change_request_required")
        self.assertEqual(
            tuple(manifest["pipeline_contract_sequence"]),
            api.PROJECT_RUN_PIPELINE_CONTRACT_SEQUENCE_V1,
        )
        for frozen_file in manifest["frozen_files"]:
            with self.subTest(path=frozen_file["path"]):
                actual_hash = hashlib.sha256((workspace / frozen_file["path"]).read_bytes()).hexdigest()
                self.assertEqual(actual_hash, frozen_file["sha256"])


if __name__ == "__main__":
    unittest.main()
