"""B2-2: SQLite must queue concurrent writers instead of failing with lock errors."""
from __future__ import annotations

import tempfile
import threading
import unittest
from pathlib import Path

from backend.repository import Repository


class ConcurrentWriteTest(unittest.TestCase):
    def test_parallel_project_creates_never_raise_database_locked(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Repository(Path(temp_dir) / "concurrent.sqlite3")
            user = repo.create_user(email="w@asie.test", display_name="W", password="x" * 12)
            org = repo.create_organization(name="W Org", owner_user_id=user["user_id"])
            errors: list[BaseException] = []

            def create_project(index: int) -> None:
                try:
                    repo.create_project(
                        {
                            "name": f"مشروع {index}",
                            "sector": "مقهى مختص",
                            "jurisdiction": "الرياض",
                            "organization_id": org["organization_id"],
                            "inputs": {"monthly_units": "1000", "unit_price": "15"},
                        }
                    )
                except BaseException as exc:  # noqa: BLE001 - asserted below
                    errors.append(exc)

            threads = [threading.Thread(target=create_project, args=(i,)) for i in range(10)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=60)

            self.assertEqual(errors, [], f"concurrent writes failed: {errors!r}")
            projects = repo.list_projects(org["organization_id"])
            self.assertEqual(len(projects), 10)
            journal_mode = repo.connect().execute("PRAGMA journal_mode").fetchone()[0]
            self.assertEqual(journal_mode.lower(), "wal")


if __name__ == "__main__":
    unittest.main()
