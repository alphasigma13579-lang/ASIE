from __future__ import annotations

import json
import unittest
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PACKAGE_ROOT.parent


class Vision2030SyncPackageGuardrails(unittest.TestCase):
    def test_registry_contains_only_official_https_sources(self) -> None:
        registry = json.loads((PACKAGE_ROOT / "config" / "vision2030_sources.json").read_text(encoding="utf-8"))
        self.assertEqual(registry["refresh_policy"], "monthly_change_detection")
        self.assertGreaterEqual(len(registry["sources"]), 4)
        for source in registry["sources"]:
            self.assertTrue(source["url"].startswith("https://www.vision2030.gov.sa/"))
            self.assertEqual(source["authority"], "Saudi Vision 2030")

    def test_workflow_is_monthly_manual_and_secret_scoped(self) -> None:
        workflow = (REPOSITORY_ROOT / ".github" / "workflows" / "vision2030-kb-sync.yml").read_text(encoding="utf-8")
        self.assertIn('cron: "17 3 1 * *"', workflow)
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("environment: production", workflow)
        self.assertIn("secrets.TAVILY_API_KEY", workflow)
        self.assertIn("secrets.PINECONE_API_KEY", workflow)
        self.assertIn('PINECONE_INDEX: "vision2030-kb"', workflow)
        self.assertIn("actions/cache/restore@v4", workflow)
        self.assertIn("actions/cache/save@v4", workflow)
        self.assertIn("--dry-run", workflow)
        self.assertNotIn("DEEPSEEK_API_KEY", workflow)
        self.assertNotIn("GOOGLE_MAPS_API_KEY", workflow)

    def test_sync_does_not_import_frozen_runtime_or_finance(self) -> None:
        source = (PACKAGE_ROOT / "backend" / "vision2030_kb_sync.py").read_text(encoding="utf-8")
        forbidden = (
            "backend.aas_kernel",
            "backend.heart_controller",
            "backend.system_bus",
            "ProjectRunWorkflow",
            "SnapshotAssembly",
            "FinanceEngine",
            "DecisionCouncil",
        )
        for token in forbidden:
            self.assertNotIn(token, source)
        self.assertIn('"source_of_truth": False', source)
        self.assertIn('"snapshot_mutated": False', source)
        self.assertIn('"finance_mutated": False', source)

    def test_no_provider_secret_is_committed(self) -> None:
        source = (PACKAGE_ROOT / "backend" / "vision2030_kb_sync.py").read_text(encoding="utf-8")
        registry = (PACKAGE_ROOT / "config" / "vision2030_sources.json").read_text(encoding="utf-8")
        self.assertNotIn("pcsk_", source + registry)
        self.assertNotIn("tvly-", source + registry)
        self.assertNotIn("Bearer ", source + registry)


if __name__ == "__main__":
    unittest.main()
