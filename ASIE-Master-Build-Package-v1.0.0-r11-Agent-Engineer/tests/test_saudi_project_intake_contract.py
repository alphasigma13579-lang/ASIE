from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "src" / "App.tsx").read_text(encoding="utf-8")
CONTRACTS = (ROOT / "src" / "contracts.ts").read_text(encoding="utf-8")


class SaudiProjectIntakeContractTests(unittest.TestCase):
    def test_saudi_scope_is_explicit_and_device_location_is_not_requested(self):
        self.assertIn('value="المملكة العربية السعودية" readOnly', APP)
        self.assertNotIn("navigator.geolocation", APP)
        self.assertIn("لا تُقرأ إحداثيات الجهاز تلقائيًا", APP)

    def test_location_is_structured_in_frontend_contract(self):
        for field in (
            "location_country",
            "location_region",
            "location_city",
            "location_district",
            "location_latitude",
            "location_longitude",
        ):
            self.assertIn(field, CONTRACTS)
            self.assertIn(field, APP)

    def test_custom_sector_and_subsector_are_real_inputs(self):
        self.assertIn("اسم القطاع", APP)
        self.assertIn("وصف التصنيف", APP)
        self.assertIn('primary_sector_id: "CUSTOM"', APP)
        self.assertNotIn("أضفنا مكاناً لقطاع جديد", APP)

    def test_project_defaults_do_not_impersonate_user_financial_data(self):
        self.assertIn("capital_available: 0", APP)
        self.assertIn("startup_cost: 0", APP)
        self.assertIn('name: ""', APP)

    def test_incomplete_steps_are_blocked_before_persistence(self):
        self.assertIn("validateWizardStep", APP)
        self.assertIn("اختر المنطقة داخل المملكة", APP)
        self.assertIn("اكتب اسمًا واضحًا للمشروع", APP)


if __name__ == "__main__":
    unittest.main()
