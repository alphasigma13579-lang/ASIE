from __future__ import annotations

import base64
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from backend import asie_local_api as api
from backend.aas_registry import bootstrap_default_registry
from backend.datasets import normalize_file_import_payload
from backend.dib_finance_gate import finance_result_from_project_inputs
from backend.dib_registry import classify_project_template, governed_template, question_registry
from backend.dib_runtime_extension import dib_contracts, dib_modules, dib_sockets, register_dib_runtime
from backend.input_manifest import build_approved_input_manifest, build_dynamic_input_blueprint
from backend.intelligence_prerun_service import _market_runtime
from backend.market_intelligence import build_market_evidence_pack
from backend.project_run_workflow import ProjectRunEnvelope
from backend.system_bus import BusMessage
from backend.workspace import compare_snapshots


class DIBCompleteRuntimeTests(unittest.TestCase):
    def test_template_and_question_registries_cover_idea_path(self) -> None:
        profile = {
            "name": "محل شاورما",
            "sector": "Food Service",
            "inputs": {
                "activity_description": "شاورما دجاج ولحم في الرياض",
                "location_country": "SA",
            },
        }
        template_id = classify_project_template(profile)
        self.assertEqual(template_id, "template.food_service.shawarma.v1")
        template = governed_template(profile)
        questions = question_registry(template_id)
        self.assertGreaterEqual(len(questions), 5)
        self.assertTrue(all(row["question_id"] and row["label"] for row in questions))

        blueprint = build_dynamic_input_blueprint(
            "project_shawarma",
            profile,
            start_type="idea_only",
            interview_answers={row["question_id"]: "answered" for row in questions},
        ).to_public()
        self.assertEqual(blueprint["template_id"], template_id)
        self.assertEqual(blueprint["status"], "DRAFT_REVIEW")
        self.assertTrue(blueprint["content_hash"])
        self.assertIn("equipment_shawarma_grill", {row["input_key"] for row in blueprint["items"]})

    def test_file_intake_maps_csv_xlsx_and_pdf_quote_candidates(self) -> None:
        mapping_specs = [
            {
                "input_key": "equipment_shawarma_grill",
                "finance_key": "capex_equipment",
                "label": "شواية شاورما تجارية",
                "category": "capex_equipment",
                "unit": "SAR",
                "required": True,
            },
            {
                "input_key": "equipment_refrigeration",
                "finance_key": "capex_equipment",
                "label": "ثلاجة وتبريد",
                "category": "capex_equipment",
                "unit": "SAR",
                "required": True,
            },
        ]
        csv_payload = normalize_file_import_payload(
            {
                "file_name": "quote.csv",
                "csv_text": "description,amount\nshawarma grill,18500\nrefrigerator,12500",
                "mapping_specs": mapping_specs,
            }
        )
        self.assertEqual(csv_payload["import_method"], "manual_csv")
        self.assertEqual(len(csv_payload["file_intake"]["mapped_candidates"]), 2)

        # Minimal text PDF with standard Tj operators; no OCR or network is used.
        stream = b"BT /F1 12 Tf 72 720 Td (shawarma grill 18500 SAR) Tj 0 -20 Td (refrigerator 12500 SAR) Tj ET"
        pdf = (
            b"%PDF-1.4\n1 0 obj << /Length "
            + str(len(stream)).encode()
            + b" >>\nstream\n"
            + stream
            + b"\nendstream\nendobj\n%%EOF"
        )
        pdf_payload = normalize_file_import_payload(
            {
                "file_name": "supplier-quote.pdf",
                "file_type": "application/pdf",
                "file_base64": base64.b64encode(pdf).decode(),
                "mapping_specs": mapping_specs,
            }
        )
        self.assertEqual(pdf_payload["import_method"], "manual_table")
        self.assertEqual(pdf_payload["file_intake"]["file_type"], "pdf")
        self.assertGreaterEqual(len(pdf_payload["rows"]), 2)
        self.assertGreaterEqual(len(pdf_payload["file_intake"]["mapped_candidates"]), 2)

    def test_market_query_uses_registered_bus_socket_module_path(self) -> None:
        runtime, source_module_id = _market_runtime()
        result = runtime.execute(
            BusMessage(
                source_module_id=source_module_id,
                target_module_id="module.market_intelligence",
                contract_id="market.query.request.v1",
                socket_id="socket.market.query",
                correlation_id="corr:test:market",
                audit_ref="audit:test:market",
                payload={
                    "project_id": "project_market",
                    "query_id": "query_market",
                    "item_id": "item_market",
                    "specification": "Commercial shawarma grill, medium capacity, Saudi Arabia",
                    "geography": "Saudi Arabia / Riyadh",
                    "category": "capex_equipment",
                    "unit": "SAR",
                    "candidate_samples": [
                        {"value": 17000, "weight": 1, "source_ref": "quote:1"},
                        {"value": 18000, "weight": 1, "source_ref": "quote:2"},
                        {"value": 18500, "weight": 2, "source_ref": "quote:3"},
                        {"value": 19000, "weight": 1, "source_ref": "quote:4"},
                        {"value": 20000, "weight": 1, "source_ref": "quote:5"},
                        {"value": 150000, "weight": 0.5, "source_ref": "outlier"},
                    ],
                },
            )
        )
        pack = result.output["evidence_pack"]
        self.assertEqual(result.output["contract_id"], "market.evidence.pack.v1")
        self.assertEqual(pack["decision_authority"], "candidate_assumption_only")
        self.assertGreater(pack["p75"], pack["p25"])
        self.assertGreaterEqual(pack["outlier_report"]["excluded_count"], 1)
        self.assertFalse(pack["external_fetch_enabled"])
        self.assertFalse(pack["ai_provider_used"])
        record = runtime.bus.messages[-1]
        self.assertTrue(record["delivered"])
        self.assertEqual(record["message"]["socket_id"], "socket.market.query")
        self.assertEqual(record["message"]["target_module_id"], "module.market_intelligence")

    def test_market_evidence_requires_human_approval_before_manifest(self) -> None:
        pack = build_market_evidence_pack(
            {
                "project_id": "project_market_manifest",
                "query_id": "query_manifest",
                "item_id": "item:market:grill",
                "specification": "Commercial shawarma grill",
                "geography": "Saudi Arabia",
                "category": "capex_equipment",
                "unit": "SAR",
                "candidate_samples": [17000, 18000, 18500, 19000, 20000],
            }
        )
        base_items = [
            {
                "item_id": f"item:manifest:{key}",
                "input_key": key,
                "finance_key": key,
                "value": value,
                "state": "VALUE_ENTERED",
                "approval_status": "approved",
                "required": True,
            }
            for key, value in {
                "startup_cost": 100000,
                "monthly_fixed_cost": 30000,
                "unit_price": 30,
                "variable_cost": 12,
                "monthly_units": 3000,
            }.items()
        ]
        market_item = {
            "item_id": "item:market:grill",
            "input_key": "equipment_shawarma_grill",
            "finance_key": "capex_equipment",
            "value": pack["weighted_median"],
            "state": "EXPERIMENTAL_ESTIMATE",
            "approval_status": "approved",
            "required": True,
            "evidence_pack": pack,
        }
        pending = build_approved_input_manifest(
            "project_market_manifest",
            {"blueprint_items": [*base_items, market_item]},
        ).to_public()
        self.assertEqual(pending["status"], "blocked")
        self.assertIn("MARKET_EVIDENCE_PACK_INVALID", {row["code"] for row in pending["blockers"]})

        approved_pack = dict(pack) | {
            "review_decision": "approved",
            "selected_value": pack["weighted_median"],
        }
        approved = build_approved_input_manifest(
            "project_market_manifest",
            {"blueprint_items": [*base_items, market_item | {"evidence_pack": approved_pack}]},
        ).to_public()
        self.assertEqual(approved["status"], "approved")
        self.assertEqual(approved["normalized_inputs"]["capex_equipment"], pack["weighted_median"])

    def test_manifest_gate_precedes_deterministic_finance_and_preserves_revision(self) -> None:
        items = [
            {
                "item_id": f"item:finance:{key}",
                "input_key": key,
                "finance_key": key,
                "value": value,
                "state": "INTENTIONAL_ZERO" if value == 0 else "VALUE_ENTERED",
                "reason": "غير مطلوب في نموذج SaaS" if value == 0 else "",
                "approval_status": "approved",
                "required": True,
            }
            for key, value in {
                "startup_cost": 0,
                "monthly_fixed_cost": 0,
                "unit_price": 100,
                "variable_cost": 0,
                "monthly_units": 1000,
            }.items()
        ]
        raw = {
            "blueprint_id": "dib:saas",
            "blueprint_revision_id": "dibrev:2",
            "blueprint_revision": 2,
            "template_id": "template.digital.saas.v1",
            "blueprint_items": items,
        }
        finance, blockers, manifest = finance_result_from_project_inputs("project_saas", raw)
        self.assertEqual(blockers, [])
        self.assertEqual(finance["status"], "ready")
        self.assertEqual(manifest["version"], 2)
        self.assertEqual(manifest["blueprint_revision_id"], "dibrev:2")
        self.assertTrue(manifest["content_hash"])
        self.assertEqual(finance["approved_input_manifest"]["content_hash"], manifest["content_hash"])


def test_actual_project_run_uses_manifest_gate_before_finance_and_seals_it(self) -> None:
    api.reset_local_module_runtime_for_tests()
    temp_dir = tempfile.TemporaryDirectory()
    self.addCleanup(temp_dir.cleanup)
    repo = api.Repository(Path(temp_dir.name) / "dib-runtime.sqlite3")
    items = [
        {
            "item_id": f"item:runtime:{key}",
            "input_key": key,
            "finance_key": key,
            "value": value,
            "state": "VALUE_ENTERED",
            "approval_status": "approved",
            "required": True,
        }
        for key, value in {
            "startup_cost": 120000,
            "monthly_fixed_cost": 30000,
            "unit_price": 35,
            "variable_cost": 14,
            "monthly_units": 4000,
        }.items()
    ]
    project = repo.create_project(
        {
            "name": "DIB runtime project",
            "sector": "Food Service",
            "jurisdiction": "Saudi Arabia",
            "depth_profile": "validation",
            "inputs": {
                "template_id": "template.food_service.shawarma.v1",
                "blueprint_id": "dib:runtime",
                "blueprint_revision_id": "dibrev:runtime:1",
                "blueprint_revision": 1,
                "blueprint_items": items,
            },
        }
    )
    envelope = ProjectRunEnvelope(
        project_id=project.project_id,
        scenario_id="baseline",
        operation_id="op_dib_runtime",
        idempotency_key="idem_dib_runtime",
        input_hash="sha256:dib-runtime",
        run_id="run_dib_runtime",
        snapshot_id="snap_dib_runtime",
        source_module_id="aas.heart.M1",
    )
    overview, _report = api.execute_project_run_pipeline(envelope, project=project, data_access=repo)
    executions = [
        row for row in api.local_runtime_context().runtime.executions
        if row.module_id == "module.finance" and row.output.get("project_id") == project.project_id
    ]
    self.assertEqual(len(executions), 1)
    finance_output = executions[0].output
    self.assertEqual(finance_output["manifest_validation_gate"]["status"], "approved")
    self.assertFalse(finance_output["manifest_validation_gate"]["finance_received_raw_ui_inputs"])
    self.assertEqual(finance_output["approved_input_manifest"]["contract_id"], "approved.input.manifest.v1")
    finance_lineage = next(
        row for row in overview["snapshot_assembly"]["lineage"]
        if row["output_key"] == "finance_result"
    )
    self.assertEqual(finance_lineage["producer_contract_id"], "finance.result.v1")

    def test_additive_registry_does_not_modify_frozen_default_registry(self) -> None:
        base = bootstrap_default_registry()
        base_counts = base.counts()
        extension = register_dib_runtime(bootstrap_default_registry())
        self.assertEqual(base.counts(), base_counts)
        self.assertGreater(extension.counts()["contracts"], base_counts["contracts"])
        self.assertEqual(extension.socket("socket.market.query").contract_id, "market.query.request.v1")
        self.assertEqual(extension.module("module.market_intelligence").label, "ASIE Market Intelligence Module")
        self.assertIn("approved.input.manifest.v1", {row.contract_id for row in dib_contracts()})
        self.assertEqual(dib_sockets()[0].socket_id, "socket.market.query")
        self.assertEqual(dib_modules()[0].module_id, "module.market_intelligence")

    def test_revision_and_snapshot_comparison_remain_immutable(self) -> None:
        first = {
            "snapshot": {"snapshot_id": "snap_a"},
            "project": {"project_id": "project_compare"},
            "decision": {"sovereign_verdict": "REVISE"},
            "acceptance": {"status": "conditional"},
            "kpis": [
                {"output_id": "npv", "value": 1000, "unit": "SAR"},
                {"output_id": "monthly-profit", "value": 100, "unit": "SAR"},
            ],
            "assumption_book": [{"input_key": "unit_price", "label": "Price", "value": 20, "review_status": "approved"}],
        }
        second = {
            "snapshot": {"snapshot_id": "snap_b"},
            "project": {"project_id": "project_compare"},
            "decision": {"sovereign_verdict": "APPROVE"},
            "acceptance": {"status": "passed"},
            "kpis": [
                {"output_id": "npv", "value": 1800, "unit": "SAR"},
                {"output_id": "monthly-profit", "value": 160, "unit": "SAR"},
            ],
            "assumption_book": [{"input_key": "unit_price", "label": "Price", "value": 24, "review_status": "approved"}],
        }
        comparison = compare_snapshots(first, second)
        self.assertFalse(comparison["recalculated"])
        self.assertTrue(comparison["verdict_change"]["changed"])
        self.assertEqual(comparison["assumption_changes"][0]["from"], 20)
        self.assertEqual(first["snapshot"]["snapshot_id"], "snap_a")


if __name__ == "__main__":
    unittest.main()
