from __future__ import annotations

import json
import unittest

from backend.live_provider_catalog import LIVE_PROVIDER_CATALOG
from backend.production_provider_readiness import (
    REQUIRED_PROVIDER_SECRETS,
    assert_production_ready,
    build_presence_report,
    redact_payload,
    report_json,
)


def ready_values() -> dict[str, str]:
    values = {name: f"configured-{name.lower()}" for name in REQUIRED_PROVIDER_SECRETS}
    values.update(
        {
            "ASIE_ALLOW_EXTERNAL_FETCH": "true",
            "ASIE_PROVIDER_CONTROL_PLANE_ENABLED": "true",
            "ASIE_PROVIDER_GLOBAL_KILL_SWITCH": "false",
            "ASIE_EXTERNAL_ALLOWED_HOSTS": ",".join(
                host for provider in LIVE_PROVIDER_CATALOG for host in provider.base_hosts
            ),
        }
    )
    for provider in LIVE_PROVIDER_CATALOG:
        token = "".join(
            character if character.isalnum() else "_"
            for character in provider.provider_id.upper()
        ).strip("_")
        values[f"ASIE_PROVIDER_{token}_STATE"] = "enabled"
        values[f"ASIE_PROVIDER_{token}_KILL_SWITCH"] = "false"
    return values


class ProductionProviderReadinessTests(unittest.TestCase):
    def test_missing_required_secrets_blocks_readiness(self) -> None:
        report = build_presence_report({})
        self.assertEqual(report["status"], "blocked")
        self.assertEqual(set(report["missing_required"]), set(REQUIRED_PROVIDER_SECRETS))
        self.assertFalse(report["secrets_exposed"])

    def test_secrets_without_activation_controls_do_not_pass_readiness(self) -> None:
        values = {name: f"configured-{name.lower()}" for name in REQUIRED_PROVIDER_SECRETS}
        report = build_presence_report(values)
        self.assertEqual(report["status"], "blocked")
        self.assertIn("provider_control_plane_disabled", report["blocking_reasons"])
        self.assertIn("provider_state_not_enabled", report["blocking_reasons"])

    def test_complete_control_configuration_passes_readiness_without_granting_authority(self) -> None:
        values = ready_values()
        report = assert_production_ready(values)
        self.assertEqual(report["status"], "ready")
        self.assertEqual(report["missing_required"], [])
        self.assertFalse(report["activation_authority_granted"])
        serialized = json.dumps(report)
        for name in REQUIRED_PROVIDER_SECRETS:
            self.assertNotIn(values[name], serialized)

    def test_report_json_never_contains_secret_values(self) -> None:
        values = {name: "super-sensitive-value" for name in REQUIRED_PROVIDER_SECRETS}
        output = report_json(values)
        self.assertNotIn("super-sensitive-value", output)
        self.assertIn('"present": true', output)

    def test_redaction_is_recursive(self) -> None:
        payload = {
            "DEEPSEEK_API_KEY": "secret-a",
            "nested": {"PINECONE_API_KEY": "secret-b", "status": "ok"},
            "items": [{"token": "visible-field"}, {"ACCESS_TOKEN": "secret-c"}],
        }
        redacted = redact_payload(payload)
        self.assertEqual(redacted["DEEPSEEK_API_KEY"], "[REDACTED]")
        self.assertEqual(redacted["nested"]["PINECONE_API_KEY"], "[REDACTED]")
        self.assertEqual(redacted["items"][1]["ACCESS_TOKEN"], "[REDACTED]")
        self.assertEqual(redacted["nested"]["status"], "ok")

    def test_gate_has_no_finance_or_snapshot_output(self) -> None:
        report = build_presence_report(ready_values())
        serialized = json.dumps(report).lower()
        self.assertNotIn("normalized_inputs", serialized)
        self.assertNotIn("finance_result", serialized)
        self.assertNotIn("snapshot", serialized)


if __name__ == "__main__":
    unittest.main()
