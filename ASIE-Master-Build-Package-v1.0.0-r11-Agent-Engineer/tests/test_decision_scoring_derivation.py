"""ذ-1/ذ-2: decision-council persona scores must be derived, and the MC gate documented."""
from __future__ import annotations

import unittest

from backend.decision_council import evaluate_decision_council
from backend.finance_engine import MC_FUNDING_GAP_CEILING_RATIO, finance_result_set


def _finance(overrides: dict | None = None) -> dict:
    inputs = {
        "startup_cost": "200000",
        "monthly_fixed_cost": "12000",
        "unit_price": "20",
        "variable_cost": "8",
        "monthly_units": "3000",
        "equity_contribution": "150000",
        "annual_discount_rate": "0.10",
    } | (overrides or {})
    finance, blockers = finance_result_set(inputs)
    assert not blockers, blockers
    return finance


class PersonaDerivedScoresTest(unittest.TestCase):
    def _council(self, finance: dict) -> dict:
        return evaluate_decision_council(finance, [], readiness_gates={"gates": []}, sector_intelligence={"status": "ready", "sector_criteria": {"status": "supported"}})

    def test_every_persona_carries_formula_and_components(self) -> None:
        result = self._council(_finance())
        for persona in result["personas"]:
            self.assertTrue(persona["formula"], persona["persona_id"])
            self.assertTrue(persona["components"], persona["persona_id"])

    def test_scores_are_monotonic_in_inputs_not_two_fixed_constants(self) -> None:
        strong = self._council(_finance())
        weak_finance = _finance({"monthly_units": "900", "equity_contribution": "20000"})
        weak = self._council(weak_finance)
        strong_pm = next(p for p in strong["personas"] if p["persona_id"] == "project_manager")
        weak_pm = next(p for p in weak["personas"] if p["persona_id"] == "project_manager")
        self.assertGreater(strong_pm["value"], weak_pm["value"])
        # equity coverage component must equal the formula's closed form from baseline numbers
        baseline = weak_finance["baseline"]
        startup_cost = float(baseline["startup_cost"])
        funding_need = float(baseline["funding_need_after_equity"])
        expected_coverage = max(0.0, min(1.0, 1.0 - funding_need / startup_cost))
        self.assertAlmostEqual(weak_pm["components"]["equity_coverage"], expected_coverage, places=3)

    def test_no_hardcoded_persona_constants(self) -> None:
        import inspect
        from backend import decision_council

        source = inspect.getsource(decision_council.evaluate_decision_council)
        for forbidden in ("0.74", "0.72", "0.68 if", "250000"):
            self.assertNotIn(forbidden, source)


class MonteCarloGateDefinitionTest(unittest.TestCase):
    def test_gate_definition_is_project_relative_and_documented(self) -> None:
        finance = _finance({"startup_cost": "400000", "equity_contribution": "300000"})
        mc = finance["monte_carlo"]
        self.assertEqual(mc["status"], "ready")
        gate = mc["gate_definition"]
        self.assertEqual(gate["funding_gap_ceiling_ratio"], float(MC_FUNDING_GAP_CEILING_RATIO))
        self.assertEqual(gate["funding_gap_ceiling"], 400000 * float(MC_FUNDING_GAP_CEILING_RATIO))
        self.assertIn("funding_gap <= startup_cost", gate["rule"])


if __name__ == "__main__":
    unittest.main()
