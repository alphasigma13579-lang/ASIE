from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = ROOT / "tools" / "audit_canonical_terminology.py"


class CanonicalTerminologyTests(unittest.TestCase):
    def test_live_registry_matches_canonical_terminology_register(self) -> None:
        spec = importlib.util.spec_from_file_location("audit_canonical_terminology", AUDIT_PATH)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        counts = module.run_audit()

        self.assertGreater(counts["contracts"], 0)
        self.assertGreater(counts["sockets"], 0)
        self.assertGreater(counts["modules"], 0)
        self.assertGreater(counts["concepts"], 0)
        self.assertEqual(counts["legacy_frozen_identifiers"], 1)


if __name__ == "__main__":
    unittest.main()
