from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backend.dib_module_adapters import execute_dib_module_adapter
from backend.dib_persistence import (
    DIB_PERSISTENCE_ID,
    DIBPersistenceError,
    create_dib_persistence_store,
)
from backend.dib_registry_admission import assert_all_frozen_files_unchanged

PACKAGE_ROOT = Path(__file__).resolve().parents[1]


class DIBPersistenceTests(unittest.TestCase):
    def test_dib_session_blueprint_manifest_and_gate_are_persisted_without_finance(self) -> None:
        store = create_dib_persistence_store()
        try:
            profile = {
                "project_id": "project_persistence_shawarma",
                "name": "محل شاورما",
                "sector": "Food Service",
                "activity": "shawarma shop",
                "location_country": "SA",
            }
            session = store.start_session(profile)
            self.assertEqual(session["status"], "active")
            self.assertFalse(session["finance_wiring_enabled"])
            self.assertFalse(session["snapshot_wiring_enabled"])

            interview = execute_dib_module_adapter("module.product_ai_interview", {"project_profile": profile})
            intake = execute_dib_module_adapter(
                "module.data_intake",
                {
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
                    "existing_items": interview["proposed_items"],
                },
            )
            blueprint = execute_dib_module_adapter(
                "module.dynamic_input_blueprint",
                {"project_profile": profile, "items": intake["mapped_items"], "source": "data_intake"},
            )
            saved_blueprint = store.save_blueprint(session["session_id"], blueprint)
            self.assertEqual(saved_blueprint["payload"]["contract_id"], "dynamic.input.blueprint.v1")

            manifest = execute_dib_module_adapter("module.approved_input_manifest", {"blueprint": blueprint})
            saved_manifest = store.save_approved_manifest(session["session_id"], manifest)
            self.assertEqual(saved_manifest["payload"]["contract_id"], "approved.input.manifest.v1")
            self.assertEqual(saved_manifest["payload"]["status"], "approved")
            self.assertNotIn("finance", saved_manifest["payload"])

            gate = execute_dib_module_adapter("module.manifest_validation_gate", {"manifest": manifest})
            saved_gate = store.save_validation_gate(session["session_id"], gate)
            self.assertEqual(saved_gate["payload"]["contract_id"], "manifest.validation.v1")
            self.assertEqual(saved_gate["payload"]["status"], "passed")
            self.assertNotIn("snapshot", saved_gate["payload"])

            loaded = store.load_session(session["session_id"])
            self.assertEqual(loaded["status"], "validation_passed")
            self.assertEqual(loaded["current_blueprint"]["blueprint_id"], blueprint["blueprint_id"])
            self.assertEqual(loaded["approved_manifest"]["manifest_id"], manifest["manifest_id"])
            self.assertEqual(loaded["validation_gate"]["gate_id"], gate["gate_id"])
            self.assertFalse(loaded["external_fetch_enabled"])
            self.assertFalse(loaded["ai_provider_enabled"])

            event_types = [event["event_type"] for event in store.list_events(session["session_id"])]
            self.assertEqual(
                event_types,
                [
                    "session.started",
                    "blueprint.saved",
                    "manifest.saved",
                    "validation_gate.saved",
                ],
            )
        finally:
            store.close()

    def test_dib_persistence_survives_reopening_sqlite_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "dib.sqlite"
            first = create_dib_persistence_store(db_path)
            session = first.start_session({"project_id": "project_reopen", "sector": "Food Service"})
            session_id = session["session_id"]
            first.close()

            second = create_dib_persistence_store(db_path)
            try:
                loaded = second.load_session(session_id)
                self.assertEqual(loaded["project_id"], "project_reopen")
                self.assertEqual(loaded["adapter_id"], DIB_PERSISTENCE_ID)
                self.assertEqual(len(second.list_events(session_id)), 1)
            finally:
                second.close()

    def test_dib_persistence_rejects_ai_network_finance_and_snapshot_payloads(self) -> None:
        store = create_dib_persistence_store()
        try:
            with self.assertRaises(DIBPersistenceError):
                store.start_session({"project_id": "bad_prompt", "raw_prompt": "calculate everything"})

            session = store.start_session({"project_id": "project_guarded"})
            with self.assertRaises(DIBPersistenceError):
                store.save_blueprint(
                    session["session_id"],
                    {
                        "contract_id": "dynamic.input.blueprint.v1",
                        "blueprint_id": "dib_bad_finance",
                        "project_id": "project_guarded",
                        "revision": 1,
                        "items": [],
                        "finance": {"status": "ready"},
                    },
                )
            with self.assertRaises(DIBPersistenceError):
                store.save_approved_manifest(
                    session["session_id"],
                    {
                        "contract_id": "approved.input.manifest.v1",
                        "manifest_id": "manifest_bad_network",
                        "blueprint_id": "dib_bad_network",
                        "project_id": "project_guarded",
                        "revision": 1,
                        "status": "blocked",
                        "external_fetch_enabled": True,
                    },
                )
            with self.assertRaises(DIBPersistenceError):
                store.save_validation_gate(
                    session["session_id"],
                    {
                        "contract_id": "manifest.validation.v1",
                        "gate_id": "gate_bad_snapshot",
                        "manifest_id": "manifest_bad_snapshot",
                        "status": "blocked",
                        "assembled_snapshot": {"snapshot_id": "snapshot_bad"},
                    },
                )
        finally:
            store.close()

    def test_dib_persistence_status_keeps_later_wiring_disabled(self) -> None:
        store = create_dib_persistence_store()
        try:
            status = store.status()
            self.assertEqual(status["persistence_id"], DIB_PERSISTENCE_ID)
            self.assertGreaterEqual(status["table_count"], 5)
            self.assertFalse(status["external_fetch_enabled"])
            self.assertFalse(status["ai_provider_enabled"])
            self.assertFalse(status["finance_wiring_enabled"])
            self.assertFalse(status["snapshot_wiring_enabled"])
            self.assertFalse(status["frozen_runtime_files_mutated"])
        finally:
            store.close()

    def test_frozen_runtime_files_remain_unchanged(self) -> None:
        assert_all_frozen_files_unchanged(PACKAGE_ROOT)


if __name__ == "__main__":
    unittest.main()
