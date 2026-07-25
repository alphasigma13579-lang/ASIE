from __future__ import annotations

import unittest

from tools.audit_dib_runtime import run_audit


class DIBRuntimeAuditTests(unittest.TestCase):
    def test_complete_dib_runtime_audit(self) -> None:
        counts = run_audit()
        self.assertEqual(counts["sockets"], 1)
        self.assertEqual(counts["modules"], 1)
        self.assertGreaterEqual(counts["contracts"], 8)
        self.assertEqual(counts["frozen_files_verified"], 10)


if __name__ == "__main__":
    unittest.main()
