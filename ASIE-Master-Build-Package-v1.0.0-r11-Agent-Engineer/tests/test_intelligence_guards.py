import unittest

from backend.intelligence_guards import compare_signals


class IntelligenceGuardTests(unittest.TestCase):
    def test_mixed_geography_is_not_comparable(self):
        result = compare_signals([{"signal_id": "a", "geography": "SA", "sector": "retail"}, {"signal_id": "b", "geography": "AE", "sector": "retail"}])
        self.assertFalse(result["comparable"])
        self.assertIn("geography", result["incompatibilities"])

    def test_contradiction_is_exposed(self):
        result = compare_signals([{"signal_id": "a", "geography": "SA", "sector": "retail", "claim": "demand", "value": True}, {"signal_id": "b", "geography": "SA", "sector": "retail", "claim": "demand", "value": False}])
        self.assertEqual(1, len(result["contradictions"]))
        self.assertFalse(result["causality_asserted"])


if __name__ == "__main__": unittest.main()
