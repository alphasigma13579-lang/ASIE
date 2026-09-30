from __future__ import annotations

import unittest

from backend.finance_engine import finance_result_set
from backend.input_manifest import build_approved_input_manifest


class InputManifestTests(unittest.TestCase):
    def approved_items(self, *zero_keys: str) -> list[dict[str, object]]:
        keys = {"startup_cost", "monthly_fixed_cost", "unit_price", "variable_cost", "monthly_units"}
        return [
            {
                "input_key": key,
                "state": "INTENTIONAL_ZERO" if key in zero_keys else "VALUE_ENTERED",
                "reason": "تشغيل رقمي عن بعد" if key in zero_keys else "",
                "approval_status": "approved",
                "treatment": "include",
            }
            for key in sorted(keys)
        ]

    def test_intentional_zero_is_approved_and_preserved(self) -> None:
        manifest = build_approved_input_manifest(
            "project_saas",
            {
                "startup_cost": 0,
                "monthly_fixed_cost": 0,
                "unit_price": 85,
                "variable_cost": 0,
                "monthly_units": 1600,
                "blueprint_items": self.approved_items("startup_cost", "monthly_fixed_cost", "variable_cost"),
            },
        ).to_public()

        self.assertEqual(manifest["status"], "approved")
        self.assertEqual(manifest["normalized_inputs"]["startup_cost"], 0)
        self.assertEqual(manifest["normalized_inputs"]["monthly_fixed_cost"], 0)
        self.assertEqual(manifest["normalized_inputs"]["variable_cost"], 0)

        finance, blockers = finance_result_set(manifest["normalized_inputs"], manifest=manifest)
        self.assertEqual(blockers, [])
        self.assertEqual(finance["status"], "ready")
        self.assertEqual(finance["baseline"]["variable_total"], 0.0)

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
                        "input_key": "startup_cost",
                        "state": "INTENTIONAL_ZERO",
                        "approval_status": "approved",
                    }
                ],
            },
        ).to_public()

        self.assertEqual(manifest["status"], "blocked")
        self.assertIn("BLUEPRINT_REASON_REQUIRED", {row["code"] for row in manifest["blockers"]})

    def test_unknown_required_item_blocks_before_finance(self) -> None:
        manifest = build_approved_input_manifest(
            "project_unknown",
            {
                "unit_price": 85,
                "monthly_units": 1600,
                "blueprint_items": [
                    {
                        "input_key": "startup_cost",
                        "state": "UNKNOWN",
                        "required": True,
                        "approval_status": "approved",
                    }
                ],
            },
        ).to_public()

        self.assertEqual(manifest["status"], "blocked")
        self.assertIn("UNKNOWN_STARTUP_COST", {row["code"] for row in manifest["blockers"]})


if __name__ == "__main__":
    unittest.main()
