import unittest

from backend.decision_council_v2_contracts import build_decision_input_manifest, validate_v2_envelope
from backend.economic_intelligence_foundations import disabled_layer_contract, require_local_reviewed_input


class V2AndEconomicFoundationTests(unittest.TestCase):
    def test_v2_manifest_is_defined_not_registered(self):
        manifest = build_decision_input_manifest(context_id="c", context_hash="ch", synthesis_pack_id="p", synthesis_pack_hash="ph", approval_receipt_id="r", approval_receipt_hash="rh")
        self.assertEqual("DEFINED_NOT_IMPLEMENTED", manifest["status"])
        self.assertFalse(manifest["registered_in_aas"])
        validate_v2_envelope({"contract_id": "decision.council.evaluate.v2", "decision_input_manifest_hash": manifest["manifest_hash"]}, manifest)

    def test_external_economic_layers_are_disabled(self):
        for layer in ("GLOBAL", "NATIONAL", "MARKET", "REFERENCE_COST"):
            result = disabled_layer_contract(layer)
            self.assertFalse(result["network_access"])
            self.assertEqual("DEFINED_NOT_IMPLEMENTED", result["status"])

    def test_local_input_requires_full_lineage_metadata(self):
        record = require_local_reviewed_input({"source": "manual", "freshness": "today", "geography": "SA", "sector": "retail", "confidence": "medium", "lineage": ["brief"], "review": "PENDING", "source_state": "reference_only"})
        self.assertFalse(record["external_fetch_enabled"])


if __name__ == "__main__": unittest.main()
