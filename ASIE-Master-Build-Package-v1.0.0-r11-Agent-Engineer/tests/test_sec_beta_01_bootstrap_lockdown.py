from __future__ import annotations

import importlib.util
import json
import os
import tempfile
import threading
import unittest
from http.client import HTTPConnection
from pathlib import Path
from types import ModuleType
from unittest import mock

from backend import asie_local_api as api
from backend.bootstrap_security import authorize_local_bootstrap, legacy_local_operator_allowed
from backend.repository import Repository

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
INITIAL_ADMIN_TOOL = PACKAGE_ROOT / "tools/create_initial_platform_admin.py"

FROZEN_FILES = {
    "backend/aas_kernel.py",
    "backend/aas_registry.py",
    "backend/heart_controller.py",
    "backend/bus_controller.py",
    "backend/system_bus.py",
    "backend/socket_contracts.py",
    "backend/module_runtime.py",
    "backend/project_run_workflow.py",
    "backend/snapshot_assembly.py",
    "backend/runtime_freeze.py",
}

SEC_BETA_01_ALLOWLIST = {
    "backend/asie_local_api.py",
    "backend/bootstrap_security.py",
    "tools/create_initial_platform_admin.py",
    "tests/test_sec_beta_01_bootstrap_lockdown.py",
    "docs/SEC-BETA-01-PRODUCTION-IDENTITY-BOOTSTRAP-LOCKDOWN-2026-07-29.md",
}


def load_initial_admin_tool() -> ModuleType:
    spec = importlib.util.spec_from_file_location("asie_create_initial_platform_admin", INITIAL_ADMIN_TOOL)
    if spec is None or spec.loader is None:
        raise RuntimeError("initial_admin_tool_import_failed")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ProductionIdentityBootstrapLockdownTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.repo = Repository(Path(directory.name) / "bootstrap-lockdown.sqlite3")
        previous_repo = api.REPO
        api.REPO = self.repo
        self.addCleanup(setattr, api, "REPO", previous_repo)

        self.server = api.ThreadingHTTPServer(("127.0.0.1", 0), api.Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def request(self, method: str, path: str, payload: dict[str, object], headers: dict[str, str] | None = None) -> tuple[int, dict[str, object]]:
        connection = HTTPConnection("127.0.0.1", self.server.server_address[1], timeout=10)
        request_headers = {"Content-Type": "application/json", **(headers or {})}
        try:
            connection.request(method, path, body=json.dumps(payload), headers=request_headers)
            response = connection.getresponse()
            body = json.loads(response.read().decode("utf-8"))
            return response.status, body
        finally:
            connection.close()

    @staticmethod
    def production_environment(**overrides: str) -> dict[str, str]:
        return {
            "ASIE_ENV": "production",
            "ASIE_ALLOW_LOCAL_BOOTSTRAP": "",
            "ASIE_ALLOW_LEGACY_LOCAL_OPERATOR": "",
            "ASIE_LOCAL_BOOTSTRAP_SECRET": "",
            **overrides,
        }

    def test_production_bootstrap_is_unavailable_without_secret(self) -> None:
        with mock.patch.dict(os.environ, self.production_environment(), clear=False):
            status, body = self.request(
                "POST",
                "/api/auth/local-bootstrap",
                {
                    "email": "attacker@example.test",
                    "display_name": "Attacker",
                    "password": "strong-production-password-01",
                    "organization_name": "Captured platform",
                },
            )

        self.assertEqual(404, status)
        self.assertEqual("local_bootstrap_unavailable", body["error"])
        self.assertEqual(0, self.repo.user_count())

    def test_production_bootstrap_stays_unavailable_even_with_flags_and_secret(self) -> None:
        secret = "x" * 48
        environment = self.production_environment(
            ASIE_ALLOW_LOCAL_BOOTSTRAP="true",
            ASIE_LOCAL_BOOTSTRAP_SECRET=secret,
        )
        with mock.patch.dict(os.environ, environment, clear=False):
            status, _body = self.request(
                "POST",
                "/api/auth/local-bootstrap",
                {
                    "email": "attacker@example.test",
                    "display_name": "Attacker",
                    "password": "strong-production-password-02",
                    "organization_name": "Captured platform",
                },
                {"X-ASIE-Bootstrap-Secret": secret},
            )

        self.assertEqual(404, status)
        self.assertEqual(0, self.repo.user_count())

    def test_zero_user_production_project_creation_requires_authorization(self) -> None:
        with mock.patch.dict(os.environ, self.production_environment(), clear=False):
            status, body = self.request(
                "POST",
                "/api/projects",
                {"name": "anonymous production project", "sector": "test", "jurisdiction": "Saudi Arabia"},
            )

        self.assertEqual(401, status)
        self.assertEqual("authentication_required", body["error"])
        self.assertEqual([], self.repo.list_projects())

    def test_local_bootstrap_requires_explicit_flag_loopback_and_constant_time_secret(self) -> None:
        secret = "s" * 48
        environment = {
            "ASIE_ENV": "development",
            "ASIE_ALLOW_LOCAL_BOOTSTRAP": "true",
            "ASIE_ALLOW_LEGACY_LOCAL_OPERATOR": "",
            "ASIE_LOCAL_BOOTSTRAP_SECRET": secret,
        }
        payload = {
            "email": "owner@example.test",
            "display_name": "Owner",
            "password": "strong-development-password-01",
            "organization_name": "Local development organization",
        }

        with mock.patch.dict(os.environ, environment, clear=False):
            wrong_status, wrong_body = self.request(
                "POST",
                "/api/auth/local-bootstrap",
                payload,
                {"X-ASIE-Bootstrap-Secret": "wrong"},
            )
            success_status, success_body = self.request(
                "POST",
                "/api/auth/local-bootstrap",
                payload,
                {"X-ASIE-Bootstrap-Secret": secret},
            )
            reused_status, reused_body = self.request(
                "POST",
                "/api/auth/local-bootstrap",
                payload,
                {"X-ASIE-Bootstrap-Secret": secret},
            )

        self.assertEqual(403, wrong_status)
        self.assertEqual("local_bootstrap_secret_invalid", wrong_body["error"])
        self.assertEqual(201, success_status)
        self.assertEqual("platform_admin", success_body["user"]["platform_role"])
        self.assertEqual(409, reused_status)
        self.assertEqual("local_bootstrap_already_completed", reused_body["error"])
        self.assertEqual(1, self.repo.user_count())

    def test_legacy_operator_is_disabled_by_default_and_for_all_production_like_environments(self) -> None:
        with mock.patch.dict(
            os.environ,
            {"ASIE_ENV": "development", "ASIE_ALLOW_LEGACY_LOCAL_OPERATOR": ""},
            clear=False,
        ):
            self.assertFalse(legacy_local_operator_allowed("127.0.0.1"))

        with mock.patch.dict(
            os.environ,
            {"ASIE_ENV": "production", "ASIE_ALLOW_LEGACY_LOCAL_OPERATOR": "true"},
            clear=False,
        ):
            self.assertFalse(legacy_local_operator_allowed("127.0.0.1"))

        with mock.patch.dict(
            os.environ,
            {"ASIE_ENV": "staging", "ASIE_ALLOW_LEGACY_LOCAL_OPERATOR": "true"},
            clear=False,
        ):
            self.assertFalse(legacy_local_operator_allowed("127.0.0.1"))

    def test_non_loopback_bootstrap_is_denied_before_secret_acceptance(self) -> None:
        secret = "n" * 48
        with mock.patch.dict(
            os.environ,
            {
                "ASIE_ENV": "development",
                "ASIE_ALLOW_LOCAL_BOOTSTRAP": "true",
                "ASIE_LOCAL_BOOTSTRAP_SECRET": secret,
            },
            clear=False,
        ):
            decision = authorize_local_bootstrap(client_host="203.0.113.10", provided_secret=secret)

        self.assertFalse(decision.allowed)
        self.assertEqual(403, decision.status)
        self.assertEqual("local_bootstrap_loopback_required", decision.code)

    def test_initial_admin_cli_service_creates_once_without_http_session(self) -> None:
        tool = load_initial_admin_tool()
        result = tool.create_initial_platform_admin(
            repository=self.repo,
            email="cli-admin@example.test",
            display_name="CLI Admin",
            password="strong-cli-password-01",
            organization_name="CLI Organization",
        )

        self.assertTrue(result["created"])
        self.assertFalse(result["session_created"])
        self.assertTrue(result["login_required"])
        self.assertEqual(1, self.repo.user_count())
        with self.assertRaisesRegex(RuntimeError, "initial_admin_already_exists"):
            tool.create_initial_platform_admin(
                repository=self.repo,
                email="second@example.test",
                display_name="Second",
                password="strong-cli-password-02",
                organization_name="Second Organization",
            )

    def test_package_allowlist_excludes_frozen_runtime(self) -> None:
        self.assertTrue(SEC_BETA_01_ALLOWLIST.isdisjoint(FROZEN_FILES))


if __name__ == "__main__":
    unittest.main()
