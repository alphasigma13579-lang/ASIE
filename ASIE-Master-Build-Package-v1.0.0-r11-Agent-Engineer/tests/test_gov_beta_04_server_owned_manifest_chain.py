from __future__ import annotations

import sqlite3
import unittest
from pathlib import Path

from backend.dib_api import DIBApiError
from backend.dib_module_adapters import execute_dib_module_adapter
from backend.dib_persistence import create_dib_persistence_store
from backend.dib_registry_admission import assert_all_frozen_files_unchanged
from backend.dib_server_owned_manifest_chain import (
    DIB_SERVER_OWNED_MANIFEST_CHAIN_ID,
    DIBServerOwnedManifestChain,
    SERVER_AUTHORITY,
)
from backend.dib_tenant_api import create_tenant_scoped_dib_api_controller
from backend.dib_tenant_boundary import DIBTenantContext

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

GOV_BETA_04_ALLOWLIST = {
    "backend/dib_server_owned_manifest_chain.py",
    "backend/dib_tenant_api.py",
    "tests/test_gov_beta_04_server_owned_manifest_chain.py",
    "docs/GOV-BETA-04-SERVER-OWNED-MANIFEST-CHAIN-2026-07-29.md",
}


def valid_intake_payload() -> dict[str, object]:
    return {
        "source": "manual_table",
        "intake_payload": {
            "file_name": "manual",
            "rows": [
                {"input_key": "startup_cost", "label": "equipment", "value": 155000},
                {"input_key": "monthly_fixed_cost", "label": "rent and salaries", "value": 36000},
                {"input_key": "unit_price", "label": "meal price", "value": 18},
                {"input_key": "variable_cost", "label": "ingredients", "value": 7},
                {"input_key": "monthly_units", "label": "monthly sales", "value": 4200},
            ],
        },
    }


class ServerOwnedManifestChainTests(unittest.TestCase):
    def setUp(self) -> None:
        self.store = create_dib_persistence_store()
        self.context = DIBTenantContext(
            organization_id="org_manifest_owner",
            user_id="user_manifest_owner",
            principal_session_id="principal_manifest_owner",
        )
        self.controller = create_tenant_scoped_dib_api_controller(
            self.store,
            project_organization_resolver=lambda project_id: (
                self.context.organization_id if project_id == "project_manifest_chain" else None
            ),
            trusted_internal_context=self.context,
        )
        self.addCleanup(self.controller.close)
        session_response = self.controller.dispatch(
            "POST",
            "/api/dib/sessions",
            {"project_profile": {"project_id": "project_manifest_chain", "sector": "Food Service"}},
        ).to_public()
        self.session_id = str(session_response["session"]["session_id"])
        blueprint_response = self.controller.dispatch(
            "POST",
            f"/api/dib/sessions/{self.session_id}/blueprints",
            valid_intake_payload(),
        ).to_public()
        self.blueprint_record = blueprint_response["blueprint"]

    def test_client_cannot_submit_final_manifest_or_gate(self) -> None:
        with self.assertRaises(DIBApiError) as manifest_error:
            self.controller.dispatch(
                "POST",
                f"/api/dib/sessions/{self.session_id}/approved-manifests",
                {
                    "manifest": {
                        "contract_id": "approved.input.manifest.v1",
                        "manifest_id": "forged_manifest",
                        "blueprint_id": "forged_blueprint",
                        "project_id": "project_manifest_chain",
                        "status": "approved",
                        "normalized_inputs": {},
                    }
                },
            )
        self.assertEqual(422, manifest_error.exception.status)
        self.assertEqual("client_owned_manifest_rejected", manifest_error.exception.code)

        manifest_response = self.controller.dispatch(
            "POST",
            f"/api/dib/sessions/{self.session_id}/approved-manifests",
            {
                "expected_blueprint_id": self.blueprint_record["blueprint_id"],
                "expected_blueprint_payload_hash": self.blueprint_record["payload_hash"],
                "expected_revision": self.blueprint_record["payload"]["revision"],
                "approval_note": "reviewed by authenticated owner",
            },
        ).to_public()
        manifest = manifest_response["approved_manifest"]
        self.assertTrue(manifest_response["manifest_server_owned"])
        self.assertEqual(SERVER_AUTHORITY, manifest["payload"]["server_authority"])
        self.assertEqual(self.context.user_id, manifest["payload"]["approved_by_user_id"])
        self.assertEqual(self.blueprint_record["payload_hash"], manifest["payload"]["blueprint_payload_hash"])

        with self.assertRaises(DIBApiError) as gate_error:
            self.controller.dispatch(
                "POST",
                f"/api/dib/sessions/{self.session_id}/validation-gates",
                {
                    "gate": {
                        "contract_id": "manifest.validation.v1",
                        "gate_id": "forged_gate",
                        "manifest_id": manifest["manifest_id"],
                        "status": "passed",
                    }
                },
            )
        self.assertEqual(422, gate_error.exception.status)
        self.assertEqual("client_owned_gate_rejected", gate_error.exception.code)

        gate_response = self.controller.dispatch(
            "POST",
            f"/api/dib/sessions/{self.session_id}/validation-gates",
            {
                "expected_manifest_id": manifest["manifest_id"],
                "expected_manifest_payload_hash": manifest["payload_hash"],
                "expected_revision": manifest["payload"]["revision"],
            },
        ).to_public()
        gate = gate_response["validation_gate"]
        self.assertTrue(gate_response["validation_gate_server_owned"])
        self.assertEqual(SERVER_AUTHORITY, gate["payload"]["server_authority"])
        self.assertEqual(self.context.user_id, gate["payload"]["validated_by_user_id"])
        self.assertEqual(manifest["payload_hash"], gate["payload"]["manifest_payload_hash"])
        self.assertEqual(self.blueprint_record["payload_hash"], gate["payload"]["blueprint_payload_hash"])

    def test_sqlite_rejects_direct_forged_manifest_and_gate(self) -> None:
        forged_manifest = {
            "contract_id": "approved.input.manifest.v1",
            "manifest_id": "forged_direct_manifest",
            "project_id": "project_manifest_chain",
            "blueprint_id": self.blueprint_record["blueprint_id"],
            "revision": 1,
            "status": "approved",
            "items": [],
            "normalized_inputs": {},
            "blockers": [],
        }
        with self.assertRaisesRegex(sqlite3.IntegrityError, "dib_server_manifest_authority_required"):
            self.store.save_approved_manifest(self.session_id, forged_manifest)

        manifest = self.controller.dispatch(
            "POST",
            f"/api/dib/sessions/{self.session_id}/approved-manifests",
            {},
        ).to_public()["approved_manifest"]
        forged_gate = {
            "contract_id": "manifest.validation.v1",
            "gate_id": "forged_direct_gate",
            "manifest_id": manifest["manifest_id"],
            "status": "passed",
            "blockers": [],
        }
        with self.assertRaisesRegex(sqlite3.IntegrityError, "dib_server_gate_authority_required"):
            self.store.save_validation_gate(self.session_id, forged_gate)

    def test_stale_expectation_is_rejected_and_new_blueprint_invalidates_chain(self) -> None:
        with self.assertRaises(DIBApiError) as stale_error:
            self.controller.dispatch(
                "POST",
                f"/api/dib/sessions/{self.session_id}/approved-manifests",
                {"expected_blueprint_payload_hash": "stale_hash"},
            )
        self.assertEqual(409, stale_error.exception.status)
        self.assertEqual("stale_blueprint_lineage", stale_error.exception.code)

        manifest = self.controller.dispatch(
            "POST",
            f"/api/dib/sessions/{self.session_id}/approved-manifests",
            {},
        ).to_public()["approved_manifest"]
        gate = self.controller.dispatch(
            "POST",
            f"/api/dib/sessions/{self.session_id}/validation-gates",
            {},
        ).to_public()["validation_gate"]
        self.assertIsNotNone(manifest["manifest_id"])
        self.assertIsNotNone(gate["gate_id"])

        previous = dict(self.blueprint_record["payload"])
        replacement = {
            **previous,
            "blueprint_id": "replacement_blueprint",
            "revision": int(previous.get("revision") or 1) + 1,
        }
        self.store.save_blueprint(self.session_id, replacement)
        session = self.store.load_session(self.session_id)
        self.assertEqual("replacement_blueprint", session["current_blueprint_id"])
        self.assertIsNone(session["approved_manifest_id"])
        self.assertIsNone(session["validation_gate_id"])
        self.assertNotIn("approved_manifest", session)
        self.assertNotIn("validation_gate", session)

    def test_preexisting_unproven_chain_is_quarantined_and_pointers_are_cleared(self) -> None:
        legacy_store = create_dib_persistence_store()
        self.addCleanup(legacy_store.close)
        session = legacy_store.start_session({"project_id": "legacy_chain_project"})
        blueprint = execute_dib_module_adapter(
            "module.dynamic_input_blueprint",
            {
                "project_profile": {"project_id": "legacy_chain_project"},
                "items": [],
                "source": "legacy_test",
            },
        )
        blueprint_record = legacy_store.save_blueprint(session["session_id"], blueprint)
        manifest = execute_dib_module_adapter(
            "module.approved_input_manifest",
            {"blueprint": blueprint_record["payload"]},
        )
        manifest_record = legacy_store.save_approved_manifest(session["session_id"], manifest)
        gate = execute_dib_module_adapter(
            "module.manifest_validation_gate",
            {"manifest": manifest_record["payload"]},
        )
        legacy_store.save_validation_gate(session["session_id"], gate)

        chain = DIBServerOwnedManifestChain(legacy_store)
        migrated = legacy_store.load_session(session["session_id"])
        self.assertIsNone(migrated["approved_manifest_id"])
        self.assertIsNone(migrated["validation_gate_id"])
        self.assertEqual(1, chain.status()["legacy_chain_quarantine_count"])

    def test_status_and_package_boundaries(self) -> None:
        status = self.controller.status()["server_owned_manifest_chain"]
        self.assertEqual(DIB_SERVER_OWNED_MANIFEST_CHAIN_ID, status["manifest_chain_id"])
        self.assertTrue(status["client_owned_manifest_rejected"])
        self.assertTrue(status["client_owned_gate_rejected"])
        self.assertTrue(status["one_time_authorization_required"])
        self.assertTrue(GOV_BETA_04_ALLOWLIST.isdisjoint(FROZEN_FILES))
        assert_all_frozen_files_unchanged(PACKAGE_ROOT)


if __name__ == "__main__":
    unittest.main()
