from __future__ import annotations

import unittest
from pathlib import Path

from backend.dib_module_adapters import (
    DIB_MODULE_ADAPTERS_ID,
    DIB_MODULE_ADAPTER_SPECS,
    DIBModuleAdapterError,
    assert_dib_module_adapter_alignment,
    assert_dib_module_adapters_keep_finance_unwired,
    build_dib_module_adapters,
    dib_module_adapter_status,
    execute_dib_module_adapter,
    registered_dib_module_adapter_specs,
)
from backend.dib_registry_admission import assert_all_frozen_files_unchanged
from backend.dib_runtime import DIB_CONTRACTS, DIB_MODULES, DIB_SOCKETS

PACKAGE_ROOT = Path(__file__).resolve().parents[1]


class DIBModuleAdaptersTests(unittest.TestCase):
    def test_adapter_specs_align_with_dib_runtime_without_finance_wiring(self) -> None:
        assert_dib_module_adapter_alignment()
        assert_dib_module_adapters_keep_finance_unwired()
        status = dib_module_adapter_status()
        self.assertEqual(status["adapter_id"], DIB_MODULE_ADAPTERS_ID)
        self.assertFalse(status["external_fetch_enabled"])
        self.assertFalse(status["ai_provider_enabled"])
        self.assertFalse(status["finance_wiring_enabled"])
        self.assertFalse(status["frozen_module_runtime_mutated"])
        self.assertEqual(len(DIB_MODULE_ADAPTER_SPECS), len(DIB_MODULES))

    def test_registered_adapter_specs_reference_only_dib_ids(self) -> None:
        specs = registered_dib_module_adapter_specs()
        self.assertEqual(len(specs), len(DIB_MODULES) + 1)  # customer decision is an alias inside DIB module boundary.
        for spec in specs:
            self.assertIn(spec["socket_id"], DIB_SOCKETS)
            self.assertIn(spec["consumes_contract_id"], DIB_CONTRACTS)
            self.assertIn(spec["produces_contract_id"], DIB_CONTRACTS)
            self.assertFalse(spec["external_fetch_enabled"])
            self.assertFalse(spec["ai_provider_enabled"])
            self.assertFalse(spec["finance_wiring_enabled"])

    def test_template_question_and_product_interview_adapters_are_offline(self) -> None:
        profile = {
            "project_id": "project_adapter_shawarma",
            "name": "محل شاورما",
            "sector": "Food Service",
            "activity": "shawarma shop",
            "location_country": "SA",
        }
        template = execute_dib_module_adapter("module.template_registry", {"project_profile": profile})
        self.assertEqual(template["contract_id"], "template.registry.v1")
        self.assertEqual(template["template_id"], "template:food-service:shawarma:v1")
        self.assertFalse(template["guards"]["external_fetch_enabled"])

        questions = execute_dib_module_adapter("module.question_registry", {"template_id": template["template_id"]})
        self.assertEqual(questions["contract_id"], "question.registry.v1")
        self.assertTrue(questions["questions"])

        interview = execute_dib_module_adapter("module.product_ai_interview", {"project_profile": profile})
        self.assertEqual(interview["contract_id"], "product.ai.interview.v1")
        self.assertFalse(interview["ai_provider_enabled"])
        self.assertFalse(interview["external_fetch_enabled"])
        self.assertTrue(interview["proposed_items"])

    def test_data_intake_to_manifest_validation_path_does_not_call_finance(self) -> None:
        profile = {"project_id": "project_adapter_files", "sector": "Food Service", "activity": "shawarma shop"}
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
        self.assertEqual(intake["contract_id"], "data.intake.v1")
        self.assertEqual(intake["source_type"], "manual_table")
        self.assertTrue(intake["normalized_rows"])

        blueprint = execute_dib_module_adapter(
            "module.dynamic_input_blueprint",
            {"project_profile": profile, "items": intake["mapped_items"], "source": "data_intake"},
        )
        self.assertEqual(blueprint["contract_id"], "dynamic.input.blueprint.v1")

        manifest = execute_dib_module_adapter("module.approved_input_manifest", {"blueprint": blueprint})
        self.assertEqual(manifest["contract_id"], "approved.input.manifest.v1")
        self.assertEqual(manifest["status"], "approved")
        self.assertIn("normalized_inputs", manifest)
        self.assertNotIn("finance", manifest)

        gate = execute_dib_module_adapter("module.manifest_validation_gate", {"manifest": manifest})
        self.assertEqual(gate["contract_id"], "manifest.validation.v1")
        self.assertEqual(gate["status"], "passed")
        self.assertNotIn("finance", gate)

    def test_market_customer_decision_and_revision_adapters_are_controlled(self) -> None:
        item = {"input_key": "capex_equipment", "label": "معدات محل شاورما", "value_state": "UNKNOWN"}
        pack = execute_dib_module_adapter("module.market_intelligence", {"item": item, "geography": "SA"})
        self.assertEqual(pack["contract_id"], "market.evidence.pack.v1")
        self.assertFalse(pack["external_fetch_enabled"])
        self.assertGreater(pack["weighted_median"], 0)

        decision = execute_dib_module_adapter(
            "module.customer_item_decision",
            {"item": item, "decision": {"action": "accept_market_median", "evidence_pack": pack}},
        )
        self.assertEqual(decision["contract_id"], "customer.item.decision.v1")
        self.assertEqual(decision["item"]["value_state"], "MARKET_ESTIMATED")

        profile = {"project_id": "project_revision_adapter", "sector": "Food Service"}
        blueprint = execute_dib_module_adapter("module.dynamic_input_blueprint", {"project_profile": profile, "items": [decision["item"]]})
        revision = execute_dib_module_adapter(
            "module.dib_revision",
            {
                "previous_blueprint": blueprint,
                "changes": [{"input_key": "unit_price", "action": "enter_value", "value": 22}],
                "reason": "customer_adjusted_price",
            },
        )
        self.assertEqual(revision["contract_id"], "dib.draft.revision.v1")
        self.assertEqual(revision["parent_blueprint_id"], blueprint["blueprint_id"])
        self.assertEqual(revision["revision"], blueprint["revision"] + 1)

    def test_adapters_reject_ai_provider_network_and_finance_payloads(self) -> None:
        with self.assertRaises(DIBModuleAdapterError):
            execute_dib_module_adapter(
                "module.product_ai_interview",
                {"project_profile": {"project_id": "bad"}, "ai_provider_enabled": True},
            )
        with self.assertRaises(DIBModuleAdapterError):
            execute_dib_module_adapter(
                "module.market_intelligence",
                {"input_key": "unit_price", "external_fetch_enabled": True},
            )
        with self.assertRaises(DIBModuleAdapterError):
            execute_dib_module_adapter(
                "module.manifest_validation_gate",
                {"manifest": {}, "finance": {"status": "ready"}},
            )

    def test_frozen_runtime_files_remain_unchanged(self) -> None:
        assert_all_frozen_files_unchanged(PACKAGE_ROOT)
        adapters = build_dib_module_adapters()
        self.assertIn("module.product_ai_interview", adapters)
        self.assertIn("module.customer_item_decision", adapters)


if __name__ == "__main__":
    unittest.main()
