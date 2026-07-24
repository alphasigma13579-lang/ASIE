"""B0: Origin allowlist must be deployment-configurable, never hard-coded to dev."""
from __future__ import annotations

import importlib
import os
import unittest
from unittest import mock


MODULE = "backend.asie_local_api"


class AllowedOriginsConfigurationTest(unittest.TestCase):
    def _reload(self):
        import backend.asie_local_api as api
        return importlib.reload(api)

    def test_dev_origins_used_when_env_unset(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("ASIE_ALLOWED_ORIGINS", None)
            api = self._reload()
            self.assertEqual(
                api.LOCAL_FRONTEND_ORIGINS,
                frozenset({"http://127.0.0.1:5194", "http://localhost:5194"}),
            )

    def test_configured_origins_replace_dev_defaults(self) -> None:
        with mock.patch.dict(
            os.environ,
            {"ASIE_ALLOWED_ORIGINS": "https://asie.example.com, https://beta.asie.sa/"},
        ):
            api = self._reload()
            self.assertEqual(
                api.LOCAL_FRONTEND_ORIGINS,
                frozenset({"https://asie.example.com", "https://beta.asie.sa"}),
            )

    def test_blank_env_falls_back_to_dev_origins(self) -> None:
        with mock.patch.dict(os.environ, {"ASIE_ALLOWED_ORIGINS": "  , , "}):
            api = self._reload()
            self.assertEqual(
                api.LOCAL_FRONTEND_ORIGINS,
                frozenset({"http://127.0.0.1:5194", "http://localhost:5194"}),
            )

    def tearDown(self) -> None:
        os.environ.pop("ASIE_ALLOWED_ORIGINS", None)
        self._reload()


if __name__ == "__main__":
    unittest.main()
