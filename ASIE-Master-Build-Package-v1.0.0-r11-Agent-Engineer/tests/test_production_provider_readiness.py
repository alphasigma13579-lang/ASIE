from __future__ import annotations

import json
import unittest

from backend.production_provider_readiness import (
    REQUIRED_PROVIDER_SECRETS,
    assert_production_ready,
    build_presence_report,
    redact_payload,
    report_json,
)


class ProductionProviderReadinessTests(unittest.TestCase):
    def test_missing_required_secrets_blocks_readiness(self) -> None:
        report = build_presence_report({})
        self.assertEqual(report["status"], "blocked")
        self.assertEqual(set(report["missing_required"]), set(REQUIRED_PROVIDER_SECRETS))
        self.assertFalse(report["secrets_exposed"])

    def test_all_required_secrets_pass_presence_gate(self) -> None:
        values = {name: f"configured-{name.lower()}" for name in REQUIRED_PROVIDER_SECRETS}
        report = assert_production_ready(values)
        self.assertEqual(report["status"], "ready")
        self.assertEqual(report["missing_required"], [])
        serialized = json.dumps(report)
        for value in values.values():
            self.assertNotIn(value, serialized)

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
        values = {name: "configured" for name in REQUIRED_PROVIDER_SECRETS}
        report = build_presence_report(values)
        serialized = json.dumps(report).lower()
        self.assertNotIn("normalized_inputs", serialized)
        self.assertNotIn("finance_result", serialized)
        self.assertNotIn("snapshot", serialized)


if __name__ == "__main__":
    unittest.main()
