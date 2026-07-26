from __future__ import annotations

import unittest
from pathlib import Path

from backend.dib_registry_admission import assert_all_frozen_files_unchanged

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PACKAGE_ROOT.parent
ROOT_AGENTS = REPO_ROOT / "AGENTS.md"
PACKAGE_AGENTS = PACKAGE_ROOT / "AGENTS.md"
EKB_INVENTORY = PACKAGE_ROOT / "docs" / "EKB" / "EKB-06-Repository-Surgery-Inventory.md"
SURGERY_PLAN = PACKAGE_ROOT / "docs" / "REPOSITORY-SURGERY-PLAN-2026-07-26.md"
REFERENCE_LOCKDOWN = PACKAGE_ROOT / "docs" / "reference" / "ARCHIVE-LOCKDOWN.md"

ARCHIVE_LOCKED_MARKERS = (
    "docs/reference/r11-workspace-materials",
    "workspace-bundles/ASIE-Architecture-Correction-Archive",
    "ASIE-Next-Task-Handoff-2026-07-19-v1.0.0",
)

LIVE_CODE_DIRS = (PACKAGE_ROOT / "backend", PACKAGE_ROOT / "src")


class RepositoryArchiveLockdownTests(unittest.TestCase):
    def test_repository_surgery_inventory_and_plan_exist(self) -> None:
        self.assertTrue(EKB_INVENTORY.exists())
        self.assertTrue(SURGERY_PLAN.exists())
        self.assertTrue(REFERENCE_LOCKDOWN.exists())

        inventory = EKB_INVENTORY.read_text(encoding="utf-8")
        plan = SURGERY_PLAN.read_text(encoding="utf-8")
        lockdown = REFERENCE_LOCKDOWN.read_text(encoding="utf-8")

        self.assertIn("Archive Lockdown = ACTIVE", inventory)
        self.assertIn("DANGEROUS_DUPLICATE", inventory)
        self.assertIn("Live Source Replacement From Archive = PROHIBITED", inventory)
        self.assertIn("Do not replace live files with archive blobs", plan)
        self.assertIn("historical provenance only", lockdown)

    def test_agents_declare_archive_locked_zones_non_authoritative(self) -> None:
        root_agents = ROOT_AGENTS.read_text(encoding="utf-8")
        package_agents = PACKAGE_AGENTS.read_text(encoding="utf-8")

        for source in (root_agents, package_agents):
            self.assertIn("Archive lockdown", source)
            self.assertIn("docs/reference", source)
            self.assertIn("provenance only", source)
            self.assertIn("DANGEROUS_DUPLICATE" if source is root_agents else "If an archived file conflicts", source)

    def test_live_backend_and_frontend_do_not_reference_archive_locked_zones(self) -> None:
        offenders: list[str] = []
        for directory in LIVE_CODE_DIRS:
            for path in directory.rglob("*"):
                if not path.is_file() or path.suffix not in {".py", ".ts", ".tsx"}:
                    continue
                source = path.read_text(encoding="utf-8")
                for marker in ARCHIVE_LOCKED_MARKERS:
                    if marker in source:
                        offenders.append(f"{path.relative_to(PACKAGE_ROOT)} contains archive marker {marker}")
        self.assertEqual([], offenders)

    def test_repository_surgery_r1_does_not_mutate_frozen_runtime_files(self) -> None:
        assert_all_frozen_files_unchanged(PACKAGE_ROOT)


if __name__ == "__main__":
    unittest.main()
