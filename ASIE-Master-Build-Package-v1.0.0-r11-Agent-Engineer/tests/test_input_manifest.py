from __future__ import annotations

import unittest

from backend.dib_finance_gate import finance_result_from_project_inputs
from backend.input_manifest import build_approved_input_manifest


class InputManifestTests(unittest.TestCase):
    def approved_items(self, *zero_keys: str) -> list[dict[str, object]]:
        keys = {"startup_cost", "monthly_fixed_cost", "unit_price", "variable_cost", "monthly_units"}
        return [
            {
                "item_id": f"item:test:{key}",
                "input_key": key,
                "finance_key": key,
                "state": "INTENTIONAL_ZERO" if key in zero_keys else "VALUE_ENTERED",
                "reason": "تشغيل رقمي عن بعد" if key in zero_keys else "",
                "approval_status": "approved",
                "treatment": "include",
                "required": True,
            }
            for key in sorted(keys)
        ]

    def test_intentional_zero_is_approved_and_preserved_before_finance(self) -> None:
        raw = {
            "startup_cost": 0,
            "monthly_fixed_cost": 0,
            "unit_price": 85,
            "variable_cost": 0,
            "monthly_units": 1600,
            "blueprint_items": self.approved_items("startup_cost", "monthly_fixed_cost", "variable_cost"),
            "blueprint_revision": 1,
            "blueprint_revision_id": "dibrev:test",
            "template_id": "template.digital.saas.v1",
        }
        manifest = build_approved_input_manifest("project_saas", raw).to_public()
        self.assertEqual(manifest["status"], "approved")
        self.assertEqual(manifest["normalized_inputs"]["startup_cost"], 0)
        self.assertEqual(manifest["normalized_inputs"]["monthly_fixed_cost"], 0)
        self.assertEqual(manifest["normalized_inputs"]["variable_cost"], 0)

        finance, blockers, gate_manifest = finance_result_from_project_inputs("project_saas", raw)
        self.assertEqual(blockers, [])
        self.assertEqual(finance["status"], "ready")
        self.assertEqual(finance["baseline"]["variable_total"], 0.0)
        self.assertEqual(gate_manifest["content_hash"], manifest["content_hash"])

    def test_zero_without_reason_is_not_a_valid_manifest(self) -> None:
        manifest = build_approved_input_manifest(
            "project_bad_zero",
            {
                "startup_cost": 0,
                "monthly_fixed_cost": 62000,
                "unit_price": 85,
                "variable_cost": 34,
                "monthly_units": 1600,
                "blueprint_items": [
                    {
                        "item_id": "item:bad:startup",
                        "input_key": "startup_cost",
                        "finance_key": "startup_cost",
                        "state": "INTENTIONAL_ZERO",
                        "approval_status": "approved",
                        "required": True,
                    },
                    *[
                        {
                            "item_id": f"item:bad:{key}",
                            "input_key": key,
                            "finance_key": key,
                            "state": "VALUE_ENTERED",
                            "approval_status": "approved",
                            "required": True,
                        }
                        for key in ("monthly_fixed_cost", "unit_price", "variable_cost", "monthly_units")
                    ],
                ],
            },
        ).to_public()
        self.assertEqual(manifest["status"], "blocked")
        self.assertIn("BLUEPRINT_REASON_REQUIRED", {row["code"] for row in manifest["blockers"]})

    def test_unknown_required_item_blocks_before_finance(self) -> None:
        raw = {
            "unit_price": 85,
            "monthly_units": 1600,
            "blueprint_items": [
                {
                    "item_id": "item:unknown:startup",
                    "input_key": "startup_cost",
                    "finance_key": "startup_cost",
                    "state": "UNKNOWN",
                    "required": True,
                    "approval_status": "draft",
                }
            ],
        }
        finance, blockers, manifest = finance_result_from_project_inputs("project_unknown", raw)
        self.assertEqual(finance["status"], "not_ready")
        self.assertEqual(manifest["status"], "blocked")
        self.assertIn("UNKNOWN_STARTUP_COST", {row["code"] for row in blockers})


if __name__ == "__main__":
    unittest.main()
