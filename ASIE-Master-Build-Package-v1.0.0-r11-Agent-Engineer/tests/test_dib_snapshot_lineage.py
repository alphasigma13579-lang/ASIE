from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from backend.dib_project_run_gate import build_dib_project_run_manifest_gate
from backend.dib_runtime import (
    FINANCE_REQUIRED_KEYS,
    build_approved_input_manifest,
    build_dynamic_input_blueprint,
    validate_manifest_for_runtime,
)
from backend.dib_snapshot_lineage import (
    DIBSnapshotLineageError,
    build_dib_projection_support_payload,
    build_dib_snapshot_lineage,
    dib_snapshot_lineage_status,
)

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
FREEZE_MANIFEST = PACKAGE_ROOT / "docs" / "ASIE-AAS-Runtime-Freeze-Manifest-v1.0.json"
SNAPSHOT_ASSEMBLY = PACKAGE_ROOT / "backend" / "snapshot_assembly.py"


class DIBSnapshotLineageTests(unittest.TestCase):
    def approved_manifest_gate_and_project_run_gate(self) -> tuple[dict, dict, dict]:
        values = {
            "startup_cost": 330000,
            "monthly_fixed_cost": 72000,
            "unit_price": 95,
            "variable_cost": 39,
            "monthly_units": 2100,
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
                "confidence": 0.9,
                "evidence_refs": [f"manual-review:{key}"],
                "review_status": "approved",
                "required": key in FINANCE_REQUIRED_KEYS,
                "reason": "human approved value for DIB snapshot lineage test",
                "revision": 1,
            }
            for key, value in values.items()
        ]
        blueprint = build_dynamic_input_blueprint(
            {
                "project_id": "project_dib_lineage",
                "name": "اختبار نسب DIB إلى Snapshot",
                "sector": "Food Service",
                "location_country": "SA",
            },
            items,
            source="test_dib_snapshot_lineage",
        )
        manifest = build_approved_input_manifest(blueprint)
        validation_gate = validate_manifest_for_runtime(manifest)
        project_run_gate = build_dib_project_run_manifest_gate(manifest, validation_gate)
        self.assertEqual(manifest["status"], "approved")
        self.assertEqual(validation_gate["status"], "passed")
        self.assertEqual(project_run_gate["status"], "passed")
        return manifest, validation_gate, project_run_gate

    def test_snapshot_lineage_builds_required_dib_chain_without_snapshot_mutation(self) -> None:
        manifest, validation_gate, project_run_gate = self.approved_manifest_gate_and_project_run_gate()

        lineage = build_dib_snapshot_lineage(
            manifest,
            validation_gate,
            project_run_gate,
            run_id="run_dib_lineage",
            snapshot_id="snapshot_dib_lineage",
        )

        self.assertEqual(lineage["contract_id"], "dib.snapshot.lineage.v1")
        self.assertEqual(lineage["status"], "prepared")
        self.assertTrue(lineage["ready_for_snapshot_projection_support"])
        self.assertEqual(lineage["input_source"], "approved_input_manifest_only")
        self.assertEqual(lineage["source_manifest_id"], manifest["manifest_id"])
        self.assertEqual(lineage["source_manifest_validation_gate_id"], validation_gate["gate_id"])
        self.assertEqual(lineage["source_project_run_manifest_gate_id"], project_run_gate["gate_id"])
        self.assertEqual(
            [item["contract_id"] for item in lineage["lineage_chain"]],
            ["approved.input.manifest.v1", "manifest.validation.v1", "dib.project_run.manifest_gate.v1"],
        )
        self.assertFalse(lineage["snapshot_mutation"])
        self.assertFalse(lineage["finance_wiring_enabled"])
        self.assertFalse(lineage["snapshot_wiring_enabled"])
        self.assertFalse(lineage["frozen_snapshot_assembly_mutated"])
        self.assertEqual(lineage["snapshot_assembly_mount"], "planned")

    def test_projection_support_payload_is_not_sealed_and_does_not_call_snapshot_assembly(self) -> None:
        manifest, validation_gate, project_run_gate = self.approved_manifest_gate_and_project_run_gate()
        lineage = build_dib_snapshot_lineage(
            manifest,
            validation_gate,
            project_run_gate,
            run_id="run_dib_projection_support",
            snapshot_id="snapshot_dib_projection_support",
        )

        support = build_dib_projection_support_payload(lineage)

        self.assertEqual(support["contract_id"], "dib.snapshot.projection_support.v1")
        self.assertEqual(support["source_lineage_contract_id"], "dib.snapshot.lineage.v1")
        self.assertEqual(support["lineage_id"], lineage["lineage_id"])
        self.assertFalse(support["sealed_envelope_created"])
        self.assertFalse(support["snapshot_mutation"])
        self.assertFalse(support["finance_wiring_enabled"])
        self.assertFalse(support["snapshot_wiring_enabled"])
        self.assertFalse(support["frozen_snapshot_assembly_mutated"])
        self.assertNotIn("sealed_outputs", support)
        self.assertNotIn("assembled_snapshot", support)

    def test_snapshot_lineage_rejects_unapproved_or_mismatched_sources(self) -> None:
        manifest, validation_gate, project_run_gate = self.approved_manifest_gate_and_project_run_gate()

        with self.assertRaisesRegex(DIBSnapshotLineageError, "approved manifest status"):
            build_dib_snapshot_lineage(
                manifest | {"status": "blocked"},
                validation_gate,
                project_run_gate,
                run_id="run_blocked_manifest",
                snapshot_id="snapshot_blocked_manifest",
            )

        with self.assertRaisesRegex(DIBSnapshotLineageError, "validation gate mismatch"):
            build_dib_snapshot_lineage(
                manifest,
                validation_gate | {"manifest_id": "other_manifest"},
                project_run_gate,
                run_id="run_mismatch_gate",
                snapshot_id="snapshot_mismatch_gate",
            )

        with self.assertRaisesRegex(DIBSnapshotLineageError, "project run manifest gate mismatch"):
            build_dib_snapshot_lineage(
                manifest,
                validation_gate,
                project_run_gate | {"manifest_id": "other_manifest"},
                run_id="run_mismatch_project_run_gate",
                snapshot_id="snapshot_mismatch_project_run_gate",
            )

    def test_snapshot_lineage_rejects_raw_ai_file_finance_or_snapshot_payloads(self) -> None:
        manifest, validation_gate, project_run_gate = self.approved_manifest_gate_and_project_run_gate()
        forbidden_payloads = [
            manifest | {"raw_prompt": "summarize inputs"},
            manifest | {"file_base64": "abc"},
            manifest | {"ai_provider_enabled": True},
            manifest | {"finance": {"status": "ready"}},
            manifest | {"assembled_snapshot": {"snapshot_id": "snap"}},
        ]

        for payload in forbidden_payloads:
            with self.subTest(payload=set(payload) - set(manifest)):
                with self.assertRaises(DIBSnapshotLineageError):
                    build_dib_snapshot_lineage(
                        payload,
                        validation_gate,
                        project_run_gate,
                        run_id="run_forbidden_payload",
                        snapshot_id="snapshot_forbidden_payload",
                    )

    def test_status_is_post_freeze_and_mounts_are_planned(self) -> None:
        status = dib_snapshot_lineage_status()

        self.assertEqual(status["lineage_id"], "DIB-LIVE-002G-SNAPSHOT-LINEAGE-v1")
        self.assertEqual(status["lineage_contract_id"], "dib.snapshot.lineage.v1")
        self.assertEqual(status["required_chain"], ["approved.input.manifest.v1", "manifest.validation.v1", "dib.project_run.manifest_gate.v1"])
        self.assertEqual(status["snapshot_assembly_mount"], "planned")
        self.assertEqual(status["projection_support_mount"], "planned")
        self.assertFalse(status["finance_wiring_enabled"])
        self.assertFalse(status["snapshot_wiring_enabled"])
        self.assertFalse(status["frozen_snapshot_assembly_mutated"])

    def test_snapshot_assembly_is_frozen_and_unchanged(self) -> None:
        manifest = json.loads(FREEZE_MANIFEST.read_text(encoding="utf-8"))
        frozen_paths = {entry["path"]: entry["sha256"] for entry in manifest["frozen_files"]}
        self.assertIn("backend/snapshot_assembly.py", frozen_paths)
        self.assertEqual(hashlib.sha256(SNAPSHOT_ASSEMBLY.read_bytes()).hexdigest(), frozen_paths["backend/snapshot_assembly.py"])


if __name__ == "__main__":
    unittest.main()
