from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from backend.dib_project_run_gate import (
    DIBProjectRunGateError,
    build_dib_project_run_manifest_gate,
    build_project_run_request_from_dib_manifest,
    dib_project_run_gate_status,
)
from backend.dib_runtime import (
    FINANCE_REQUIRED_KEYS,
    build_approved_input_manifest,
    build_dynamic_input_blueprint,
    validate_manifest_for_runtime,
)

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
FREEZE_MANIFEST = PACKAGE_ROOT / "docs" / "ASIE-AAS-Runtime-Freeze-Manifest-v1.0.json"


class DIBProjectRunManifestGateTests(unittest.TestCase):
    def approved_manifest_and_gate(self) -> tuple[dict, dict]:
        values = {
            "startup_cost": 240000,
            "monthly_fixed_cost": 61000,
            "unit_price": 85,
            "variable_cost": 34,
            "monthly_units": 1600,
        }
        items = [
            {
                "item_id": f"dib_item_{key}",
                "input_key": key,
                "label": key,
                "category": "finance_assumption",
                "value": value,
                "unit": "SAR" if key != "monthly_units" else "unit",
                "value_state": "USER_PROVIDED",
                "value_source": "user_input",
                "source_type": "user_input",
                "confidence": 0.88,
                "evidence_refs": [f"manual-review:{key}"],
                "review_status": "approved",
                "required": key in FINANCE_REQUIRED_KEYS,
                "reason": "human approved value for DIB manifest gate test",
                "revision": 1,
            }
            for key, value in values.items()
        ]
        blueprint = build_dynamic_input_blueprint(
            {
                "project_id": "project_dib_gate",
                "name": "اختبار بوابة DIB",
                "sector": "Food Service",
                "location_country": "SA",
            },
            items,
            source="test_project_run_manifest_gate",
        )
        manifest = build_approved_input_manifest(blueprint)
        gate = validate_manifest_for_runtime(manifest)
        self.assertEqual(manifest["status"], "approved")
        self.assertEqual(gate["status"], "passed")
        return manifest, gate

    def test_manifest_gate_allows_only_valid_approved_manifest(self) -> None:
        manifest, validation_gate = self.approved_manifest_and_gate()

        gate = build_dib_project_run_manifest_gate(manifest, validation_gate)

        self.assertEqual(gate["contract_id"], "dib.project_run.manifest_gate.v1")
        self.assertEqual(gate["status"], "passed")
        self.assertTrue(gate["ready_for_project_run"])
        self.assertEqual(gate["input_contract_id"], "approved.input.manifest.v1")
        self.assertEqual(gate["input_source"], "approved_input_manifest_only")
        self.assertEqual(set(FINANCE_REQUIRED_KEYS) - set(gate["normalized_inputs"]), set())
        self.assertFalse(gate["raw_ui_values_accepted"])
        self.assertFalse(gate["raw_ai_values_accepted"])
        self.assertFalse(gate["raw_file_values_accepted"])
        self.assertFalse(gate["external_fetch_enabled"])
        self.assertFalse(gate["ai_provider_enabled"])
        self.assertFalse(gate["finance_wiring_enabled"])
        self.assertFalse(gate["snapshot_wiring_enabled"])
        self.assertFalse(gate["frozen_project_run_workflow_mutated"])

    def test_project_run_request_is_manifest_derived_and_not_raw_input(self) -> None:
        manifest, validation_gate = self.approved_manifest_and_gate()

        request = build_project_run_request_from_dib_manifest(
            manifest,
            validation_gate,
            operation_id="op_dib_gate_test",
            idempotency_key="idem_dib_gate_test",
        )

        self.assertEqual(request["project_id"], manifest["project_id"])
        self.assertEqual(request["input_contract_id"], "approved.input.manifest.v1")
        self.assertEqual(request["input_source"], "approved_input_manifest_only")
        self.assertEqual(request["approved_input_manifest_id"], manifest["manifest_id"])
        self.assertEqual(request["manifest_validation_gate_id"], validation_gate["gate_id"])
        self.assertEqual(request["normalized_inputs"], manifest["normalized_inputs"])
        self.assertTrue(request["requires_project_run_workflow_mount"])
        self.assertFalse(request["finance_wiring_enabled"])
        self.assertFalse(request["snapshot_wiring_enabled"])
        self.assertNotIn("finance", request)
        self.assertNotIn("snapshot", request)
        self.assertNotIn("raw_prompt", request)
        self.assertNotIn("raw_file", request)

    def test_manifest_gate_blocks_unapproved_manifest(self) -> None:
        manifest, validation_gate = self.approved_manifest_and_gate()
        blocked_manifest = manifest | {"status": "blocked", "blockers": [{"code": "TEST", "severity": "critical"}]}

        gate = build_dib_project_run_manifest_gate(blocked_manifest, validation_gate)

        self.assertEqual(gate["status"], "blocked")
        self.assertFalse(gate["ready_for_project_run"])
        self.assertIn("DIB_MANIFEST_NOT_APPROVED", {item["code"] for item in gate["blockers"]})
        with self.assertRaisesRegex(DIBProjectRunGateError, "blocked"):
            build_project_run_request_from_dib_manifest(blocked_manifest, validation_gate)

    def test_manifest_gate_blocks_unpassed_or_mismatched_validation_gate(self) -> None:
        manifest, validation_gate = self.approved_manifest_and_gate()
        bad_gate = validation_gate | {"status": "blocked", "manifest_id": "other_manifest"}

        gate = build_dib_project_run_manifest_gate(manifest, bad_gate)

        self.assertEqual(gate["status"], "blocked")
        codes = {item["code"] for item in gate["blockers"]}
        self.assertIn("DIB_MANIFEST_VALIDATION_NOT_PASSED", codes)
        self.assertIn("DIB_MANIFEST_GATE_MISMATCH", codes)

    def test_manifest_gate_rejects_raw_ai_file_finance_or_snapshot_payloads(self) -> None:
        manifest, validation_gate = self.approved_manifest_and_gate()
        forbidden_payloads = [
            manifest | {"raw_prompt": "calculate finance"},
            manifest | {"file_base64": "abc"},
            manifest | {"ai_provider_enabled": True},
            manifest | {"finance": {"status": "ready"}},
            manifest | {"snapshot": {"snapshot_id": "snap"}},
        ]

        for payload in forbidden_payloads:
            with self.subTest(payload=set(payload) - set(manifest)):
                with self.assertRaises(DIBProjectRunGateError):
                    build_dib_project_run_manifest_gate(payload, validation_gate)

    def test_gate_status_is_post_freeze_and_not_mounted_to_project_run_yet(self) -> None:
        status = dib_project_run_gate_status()

        self.assertEqual(status["gate_id"], "DIB-LIVE-002F-PROJECT-RUN-MANIFEST-GATE-v1")
        self.assertEqual(status["project_run_workflow_mount"], "planned")
        self.assertFalse(status["finance_wiring_enabled"])
        self.assertFalse(status["snapshot_wiring_enabled"])
        self.assertFalse(status["frozen_project_run_workflow_mutated"])

    def test_aas_frozen_files_remain_unchanged(self) -> None:
        manifest = json.loads(FREEZE_MANIFEST.read_text(encoding="utf-8"))
        for entry in manifest["frozen_files"]:
            path = PACKAGE_ROOT / entry["path"]
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(digest, entry["sha256"], entry["path"])


if __name__ == "__main__":
    unittest.main()
