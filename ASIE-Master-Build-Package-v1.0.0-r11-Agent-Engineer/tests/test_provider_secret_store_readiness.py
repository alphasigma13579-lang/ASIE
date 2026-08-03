from __future__ import annotations

import json
import unittest

from backend.provider_secret_store_readiness import (
    REQUIRED_PROVIDER_SECRETS,
    build_secret_store_report,
)


class ProviderSecretStoreReadinessTests(unittest.TestCase):
    def test_missing_backend_and_secrets_fail_closed(self) -> None:
        report = build_secret_store_report({})
        self.assertEqual(report["status"], "blocked")
        self.assertEqual(set(report["missing_required"]), set(REQUIRED_PROVIDER_SECRETS))
        self.assertIn("unapproved_secret_store_backend", report["blocking_reasons"])
        self.assertFalse(report["network_authorized"])

    def test_github_environment_with_all_required_names_is_presence_ready(self) -> None:
        values = {name: f"test-value-for-{name}" for name in REQUIRED_PROVIDER_SECRETS}
        values["ASIE_PROVIDER_SECRET_STORE_BACKEND"] = "github_environment"
        report = build_secret_store_report(values)
        self.assertEqual(report["status"], "ready")
        self.assertEqual(report["missing_required"], [])
        self.assertFalse(report["provider_activation_authorized"])
        self.assertFalse(report["release_authorized"])

    def test_serialized_report_never_contains_secret_values(self) -> None:
        values = {name: "must-never-appear" for name in REQUIRED_PROVIDER_SECRETS}
        values.update({
            "ASIE_PROVIDER_SECRET_STORE_BACKEND": "github_environment",
            "ASIE_ALLOW_EXTERNAL_FETCH": "true",
            "ASIE_PROVIDER_CONTROL_PLANE_ENABLED": "true",
        })
        report = build_secret_store_report(values)
        serialized = json.dumps(report)
        self.assertNotIn("must-never-appear", serialized)
        self.assertTrue(all(item["value_exposed"] is False for item in report["required"]))
        self.assertFalse(report["network_authorized"])
        self.assertFalse(report["provider_activation_authorized"])

    def test_unapproved_backend_is_rejected_even_when_secrets_exist(self) -> None:
        values = {name: "configured" for name in REQUIRED_PROVIDER_SECRETS}
        values["ASIE_PROVIDER_SECRET_STORE_BACKEND"] = "local_env_file"
        report = build_secret_store_report(values)
        self.assertEqual(report["status"], "blocked")
        self.assertIn("unapproved_secret_store_backend", report["blocking_reasons"])


if __name__ == "__main__":
    unittest.main()

