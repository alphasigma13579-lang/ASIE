from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backend.asie_local_api import reset_local_module_runtime_for_tests
from backend.dib_api import DIBApiError
from backend.dib_persistence import create_dib_persistence_store
from backend.dib_registry_admission import assert_all_frozen_files_unchanged
from backend.dib_tenant_api import create_tenant_scoped_dib_api_controller
from backend.dib_tenant_boundary import (
    DIBTenantContext,
    project_organization_resolver_from_repository,
)
from backend.repository import Repository

PACKAGE_ROOT = Path(__file__).resolve().parents[1]

FROZEN_FILES = {
    "backend/aas_kernel.py",
    "backend/aas_registry.py",
    "backend/heart_controller.py",
    "backend/bus_controller.py",
    "backend/system_bus.py",
    "backend/socket_contracts.py",
    "backend/module_runtime.py",
    "backend/project_run_workflow.py",
    "backend/snapshot_assembly.py",
    "backend/runtime_freeze.py",
}

ARCH_BETA_05_ALLOWLIST = {
    "backend/dib_canonical_finance_admission.py",
    "backend/dib_controlled_finance_wiring.py",
    "backend/dib_tenant_api.py",
    "tests/test_arch_beta_05_canonical_finance_admission.py",
    "tests/test_dib_controlled_finance_wiring.py",
    "docs/ARCH-BETA-05-CANONICAL-FINANCE-ADMISSION-REPAIR-2026-07-29.md",
}


class CanonicalFinanceAdmissionTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_local_module_runtime_for_tests()
        self.addCleanup(reset_local_module_runtime_for_tests)
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        self.repository = Repository(root / "platform.sqlite3")
        self.user = self.repository.create_user(
            email="owner@example.test",
            display_name="Owner",
            password="canonical-admission-password-01",
        )
        self.organization = self.repository.create_organization(
            name="Canonical Org",
            owner_user_id=self.user["user_id"],
        )
        self.project = self.repository.create_project(
            {
                "name": "Canonical Project",
                "sector": "Food Service",
                "jurisdiction": "SA",
                "depth_profile": "standard",
                "organization_id": self.organization["organization_id"],
                "inputs": {
                    "startup_cost": 1,
                    "monthly_fixed_cost": 1,
                    "unit_price": 1,
                    "variable_cost": 1,
                    "monthly_units": 1,
                    "location_country": "SA",
                },
            }
        )
        self.context = DIBTenantContext(
            organization_id=self.organization["organization_id"],
            user_id=self.user["user_id"],
            principal_session_id="principal_session_arch_beta_05",
        )
        self.store = create_dib_persistence_store(str(root / "dib.sqlite3"))
        self.controller = create_tenant_scoped_dib_api_controller(
            self.store,
            project_organization_resolver=project_organization_resolver_from_repository(self.repository),
            project_repository=self.repository,
            trusted_internal_context=self.context,
        )
        self.addCleanup(self.controller.close)

    @staticmethod
    def required_rows() -> list[dict[str, object]]:
        return [
            {"input_key": "startup_cost", "label": "Startup", "value": 120000},
            {"input_key": "monthly_fixed_cost", "label": "Fixed", "value": 42000},
            {"input_key": "unit_price", "label": "Price", "value": 18},
            {"input_key": "variable_cost", "label": "Variable", "value": 7},
            {"input_key": "monthly_units", "label": "Units", "value": 4200},
        ]

    def prepare_server_owned_chain(self) -> tuple[str, dict, dict]:
        session = self.controller.dispatch(
            "POST",
            "/api/dib/sessions",
            {
                "project_profile": {
                    "project_id": self.project.project_id,
                    "name": self.project.name,
                    "sector": self.project.sector,
                }
            },
        ).to_public()["session"]
        session_id = str(session["session_id"])
        self.controller.dispatch(
            "POST",
            f"/api/dib/sessions/{session_id}/blueprints",
            {
                "source": "arch_beta_05_test",
                "intake_payload": {
                    "file_name": "canonical-inputs",
                    "rows": self.required_rows(),
                },
            },
        )
        manifest = self.controller.dispatch(
            "POST",
            f"/api/dib/sessions/{session_id}/approved-manifests",
            {},
        ).to_public()["approved_manifest"]
        gate = self.controller.dispatch(
            "POST",
            f"/api/dib/sessions/{session_id}/validation-gates",
            {},
        ).to_public()["validation_gate"]
        self.assertEqual("approved", manifest["payload"]["status"])
        self.assertEqual("passed", gate["payload"]["status"])
        return session_id, manifest, gate

    def test_manifest_executes_only_through_project_run_workflow_and_persists_snapshot(self) -> None:
        session_id, manifest, gate = self.prepare_server_owned_chain()
        response = self.controller.dispatch(
            "POST",
            f"/api/dib/sessions/{session_id}/controlled-finance",
            {
                "scenario_id": "baseline",
                "idempotency_key": "idem:arch-beta-05:canonical-run",
                "expected_manifest_id": manifest["manifest_id"],
                "expected_manifest_payload_hash": manifest["payload_hash"],
                "expected_gate_id": gate["gate_id"],
                "expected_gate_payload_hash": gate["payload_hash"],
            },
        ).to_public()
        controlled = response["controlled_finance"]
        self.assertEqual("executed", controlled["status"])
        self.assertEqual("called", controlled["project_run_workflow_mount"])
        self.assertEqual("project.run.workflow.v1", controlled["workflow"]["contract_id"])
        self.assertEqual("accepted", controlled["workflow"]["status"])
        self.assertEqual("executed_via_project_run_workflow", controlled["finance_engine_execution_status"])
        self.assertEqual("finance.calculate.v1", controlled["finance_command_contract_id"])
        self.assertEqual("finance.result.v1", controlled["finance_contract_id"])
        self.assertEqual(120000.0, controlled["finance"]["baseline"]["startup_cost"])
        self.assertTrue(controlled["snapshot_mutation"])
        self.assertTrue(controlled["project_run"]["overview"]["snapshot"]["immutable"])
        self.assertEqual(
            controlled["run_id"],
            controlled["project_run"]["overview"]["run"]["run_id"],
        )
        self.assertEqual(
            controlled["snapshot_id"],
            controlled["project_run"]["overview"]["snapshot"]["snapshot_id"],
        )
        persisted = self.repository.get_snapshot_overview(controlled["snapshot_id"])
        self.assertIsNotNone(persisted)
        self.assertEqual(120000.0, persisted["finance"]["baseline"]["startup_cost"])
        original_project = self.repository.get_project(self.project.project_id)
        self.assertEqual(1, original_project.inputs["startup_cost"])

    def test_idempotency_replays_same_run_and_snapshot_once(self) -> None:
        session_id, manifest, gate = self.prepare_server_owned_chain()
        command = {
            "idempotency_key": "idem:arch-beta-05:replay",
            "expected_manifest_id": manifest["manifest_id"],
            "expected_gate_id": gate["gate_id"],
        }
        first = self.controller.dispatch(
            "POST",
            f"/api/dib/sessions/{session_id}/controlled-finance",
            command,
        ).to_public()["controlled_finance"]
        second_response = self.controller.dispatch(
            "POST",
            f"/api/dib/sessions/{session_id}/controlled-finance",
            command,
        )
        second = second_response.to_public()["controlled_finance"]
        self.assertEqual(200, second_response.status)
        self.assertEqual(first["run_id"], second["run_id"])
        self.assertEqual(first["snapshot_id"], second["snapshot_id"])
        self.assertTrue(second["idempotency_replayed"])
        with self.repository.connect() as connection:
            run_count = connection.execute(
                "SELECT COUNT(*) AS count FROM runs WHERE project_id = ?",
                (self.project.project_id,),
            ).fetchone()["count"]
            snapshot_count = connection.execute(
                "SELECT COUNT(*) AS count FROM snapshots WHERE project_id = ?",
                (self.project.project_id,),
            ).fetchone()["count"]
        self.assertEqual(1, int(run_count))
        self.assertEqual(1, int(snapshot_count))

    def test_stale_or_client_owned_execution_material_is_rejected(self) -> None:
        session_id, manifest, gate = self.prepare_server_owned_chain()
        for payload in (
            {"finance_inputs": {"startup_cost": 1}},
            {"normalized_inputs": {"startup_cost": 1}},
            {"manifest": manifest["payload"]},
            {"gate": gate["payload"]},
        ):
            with self.assertRaises(DIBApiError) as raised:
                self.controller.dispatch(
                    "POST",
                    f"/api/dib/sessions/{session_id}/controlled-finance",
                    payload,
                )
            self.assertEqual(422, raised.exception.status)
        with self.assertRaises(DIBApiError) as stale:
            self.controller.dispatch(
                "POST",
                f"/api/dib/sessions/{session_id}/controlled-finance",
                {"expected_manifest_payload_hash": "0" * 64},
            )
        self.assertEqual(409, stale.exception.status)
        self.assertEqual("stale_manifest_lineage", stale.exception.code)

    def test_direct_helper_has_no_finance_import_and_fails_closed(self) -> None:
        source = (PACKAGE_ROOT / "backend" / "dib_controlled_finance_wiring.py").read_text(encoding="utf-8")
        admission = (PACKAGE_ROOT / "backend" / "dib_canonical_finance_admission.py").read_text(encoding="utf-8")
        self.assertNotIn("from backend.finance_engine", source)
        self.assertNotIn("finance_result_set", source)
        self.assertNotIn("from backend.finance_engine", admission)
        self.assertNotIn("finance_result_set", admission)
        self.assertIn("ProjectRunWorkflow(", admission)
        self.assertIn("execute_project_run_pipeline", admission)
        self.assertIn("project_run_workflow_mount\": \"called", admission)

    def test_allowlist_excludes_frozen_runtime(self) -> None:
        self.assertTrue(ARCH_BETA_05_ALLOWLIST.isdisjoint(FROZEN_FILES))
        assert_all_frozen_files_unchanged(PACKAGE_ROOT)


if __name__ == "__main__":
    unittest.main()
