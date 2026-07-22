import unittest

from backend.intelligence_layers import build_vision2030_context, normalize_intelligence_signal
from backend.intelligence_synthesis import build_synthesis_pack, project_synthesis


class IntelligenceSynthesisTests(unittest.TestCase):
    def test_pack_and_projection_are_non_sovereign(self):
        signal = normalize_intelligence_signal({"signal_id": "v", "layer": "strategic", "claim": "supports diversification", "source": "VISION_2030_REFERENCE", "source_state": "reference_only", "freshness": "today", "geography": "SA", "sector": "retail", "confidence": "medium", "lineage": ["brief"], "review": "reviewed"}, organization_id="o", project_id="p")
        context = build_vision2030_context([signal], organization_id="o", project_id="p")
        pack = build_synthesis_pack(context, pack_id="pack-1")
        projection = project_synthesis(pack)
        self.assertIsNone(pack["verdict"])
        self.assertIsNone(projection["verdict"])

    def test_tampering_fails_closed(self):
        with self.assertRaises(ValueError):
            project_synthesis({"pack_id": "x", "claims": [], "pack_hash": "wrong"})


if __name__ == "__main__": unittest.main()
