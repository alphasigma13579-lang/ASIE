import tempfile
import unittest
from pathlib import Path

from backend.intelligence_context import ContextComponent, IntelligenceContext
from backend.intelligence_context_repository import IntelligenceContextRepository


class IntelligenceContextRepositoryTests(unittest.TestCase):
    def test_tenant_lookup_and_optimistic_lock(self):
        with tempfile.TemporaryDirectory() as folder:
            repo = IntelligenceContextRepository(Path(folder) / "aia.db")
            ctx = IntelligenceContext("ctx", "org-a", "project-a", "SA", "retail", "idem", components=[ContextComponent("c", "ref", {"x": 1}, "manual", "today", "SA", "retail", "medium", ["brief"])])
            repo.create_context(ctx)
            self.assertIsNone(repo.get_context("ctx", "org-b", "project-a"))
            with self.assertRaises(RuntimeError):
                repo.update_context(ctx, expected_version=99)


if __name__ == "__main__":
    unittest.main()
