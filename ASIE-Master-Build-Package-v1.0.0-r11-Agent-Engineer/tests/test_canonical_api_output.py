from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from audit_canonical_api_output import run_audit  # noqa: E402


class CanonicalApiOutputAuditTests(unittest.TestCase):
    def test_active_api_and_output_surfaces_match_canonical_registry(self) -> None:
        counts = run_audit()
        self.assertGreater(counts["frontend_routes"], 0)
        self.assertGreater(counts["frontend_functions"], 0)
        self.assertEqual(counts["sealed_output_mappings"], 6)
        self.assertEqual(counts["public_type_interfaces"], 3)


if __name__ == "__main__":
    unittest.main()
