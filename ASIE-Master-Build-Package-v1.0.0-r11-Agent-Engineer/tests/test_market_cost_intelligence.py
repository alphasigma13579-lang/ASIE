import unittest

from backend.market_cost_intelligence import build_market_context, build_reference_cost_assumption


class MarketCostTests(unittest.TestCase):
    def test_market_context_is_not_finance_eligible(self):
        result = build_market_context(organization_id="o", project_id="p", sector="retail", geography="SA", signals=[{"source": "manual", "freshness": "today", "geography": "SA", "sector": "retail", "confidence": "low", "lineage": ["brief"], "review": "PENDING"}])
        self.assertFalse(result["finance_eligible"])
        self.assertEqual("PARTIAL", result["maturity"])

    def test_cost_requires_verified_approved_for_finance(self):
        draft = build_reference_cost_assumption(organization_id="o", project_id="p", item_code="eq", amount=10, currency="SAR", source="manual")
        approved = build_reference_cost_assumption(organization_id="o", project_id="p", item_code="eq", amount=10, currency="SAR", source="manual", maturity="VERIFIED", review="APPROVED")
        self.assertFalse(draft["finance_eligible"])
        self.assertTrue(approved["finance_eligible"])
        self.assertFalse(approved["listed_price_is_capex"])

    def test_range_guard(self):
        with self.assertRaises(ValueError):
            build_reference_cost_assumption(organization_id="o", project_id="p", item_code="eq", amount=100, currency="SAR", source="manual", lower=1, upper=10)


if __name__ == "__main__": unittest.main()
