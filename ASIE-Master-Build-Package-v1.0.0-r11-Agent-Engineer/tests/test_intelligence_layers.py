import unittest

from backend.intelligence_layers import build_vision2030_context, disabled_global_national_layer, normalize_intelligence_signal


class IntelligenceLayerTests(unittest.TestCase):
    def signal(self):
        return normalize_intelligence_signal({"signal_id": "v-1", "layer": "strategic", "claim": "supports diversification", "value": True, "source": "VISION_2030_REFERENCE", "source_state": "reference_only", "freshness": "2026-07-21", "geography": "SA", "sector": "retail", "confidence": "medium", "lineage": ["manual:brief"], "review": "reference_reviewed"}, organization_id="org-a", project_id="p-a")

    def test_vision_is_non_sovereign_reference(self):
        result = build_vision2030_context([self.signal()], organization_id="org-a", project_id="p-a")
        self.assertIsNone(result["verdict"])
        self.assertIsNone(result["financial_outputs"])

    def test_global_and_national_are_disabled(self):
        self.assertEqual("DISABLED", disabled_global_national_layer("GLOBAL")["status"])
        self.assertEqual("DISABLED", disabled_global_national_layer("NATIONAL")["status"])

    def test_metadata_is_required(self):
        with self.assertRaises(ValueError):
            normalize_intelligence_signal({"signal_id": "x", "layer": "strategic", "claim": "x"}, organization_id="o", project_id="p")


if __name__ == "__main__": unittest.main()
