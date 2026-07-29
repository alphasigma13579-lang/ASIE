from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from backend.repository import Repository

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
CLI_PATH = PACKAGE_ROOT / "tools/create_initial_platform_admin.py"


class InitialPlatformAdminCliTests(unittest.TestCase):
    def test_cli_creates_first_admin_without_returning_session_token(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        database = Path(directory.name) / "initial-admin.sqlite3"
        environment = os.environ.copy()
        environment["ASIE_INITIAL_ADMIN_PASSWORD"] = "strong-cli-entrypoint-password-01"

        command = [
            sys.executable,
            str(CLI_PATH),
            "--database",
            str(database),
            "--email",
            "initial-admin@example.test",
            "--display-name",
            "Initial Admin",
            "--organization-name",
            "Initial Organization",
            "--confirm-empty-database",
        ]
        completed = subprocess.run(
            command,
            cwd=PACKAGE_ROOT,
            env=environment,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

        self.assertEqual(0, completed.returncode, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertTrue(result["created"])
        self.assertFalse(result["session_created"])
        self.assertTrue(result["login_required"])
        self.assertNotIn("access_token", result)
        self.assertNotIn("token", result)
        self.assertEqual(1, Repository(database).user_count())

        repeated = subprocess.run(
            command,
            cwd=PACKAGE_ROOT,
            env=environment,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        self.assertNotEqual(0, repeated.returncode)
        self.assertIn("initial_admin_already_exists", repeated.stderr)


if __name__ == "__main__":
    unittest.main()
