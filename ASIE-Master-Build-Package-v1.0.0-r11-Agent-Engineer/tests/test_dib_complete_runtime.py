from __future__ import annotations

import base64
import io
import unittest
import zipfile

from backend.dib_runtime import (
    DIB_CONTRACTS,
    DIB_MODULES,
    DIB_SOCKETS,
    apply_customer_decision,
    build_approved_input_manifest,
    build_dynamic_input_blueprint,
    build_product_ai_interview,
    compare_blueprint_revisions,
    create_draft_revision,
    finance_from_approved_manifest,
    map_intake_to_blueprint_items,
    request_market_evidence,
    run_idea_to_manifest_flow,
    validate_manifest_for_runtime,
    DIBBus,
)


def minimal_xlsx_base64() -> str:
    sheet = """<?xml version='1.0' encoding='UTF-8' standalone='yes'?>
<worksheet xmlns='http://schemas.openxmlformats.org/spreadsheetml/2006/main'><sheetData>
<row r='1'><c r='A1' t='inlineStr'><is><t>input_key</t></is></c><c r='B1' t='inlineStr'><is><t>label</t></is></c><c r='C1' t='inlineStr'><is><t>value</t></is></c></row>
<row r='2'><c r='A2' t='inlineStr'><is><t>startup_cost</t></is></c><c r='B2' t='inlineStr'><is><t>equipment quote</t></is></c><c r='C2'><v>150000</v></c></row>
</sheetData></worksheet>"""
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w") as archive:
        archive.writestr("xl/worksheets/sheet1.xml", sheet)
    return base64.b64encode(payload.getvalue()).decode("ascii")


class DIBCompleteRuntimeTests(unittest.TestCase):
    def test_all_diagram_runtime_identifiers_are_present(self) -> None:
        self.assertIn("template.registry.v1", DIB_CONTRACTS)
        self.assertIn("question.registry.v1", DIB_CONTRACTS)
        self.assertIn("product.ai.interview.v1", DIB_CONTRACTS)
        self.assertIn("data.intake.v1", DIB_CONTRACTS)
        self.assertIn("dynamic.input.blueprint.v1", DIB_CONTRACTS)
        self.assertIn("market.query.request.v1", DIB_CONTRACTS)
        self.assertIn("market.evidence.pack.v1", DIB_CONTRACTS)
        self.assertIn("customer.item.decision.v1", DIB_CONTRACTS)
        self.assertIn("approved.input.manifest.v1", DIB_CONTRACTS)
        self.assertIn("manifest.validation.v1", DIB_CONTRACTS)
        self.assertIn("dib.draft.revision.v1", DIB_CONTRACTS)
        self.assertIn("socket.market.query", DIB_SOCKETS)
        self.assertIn("module.market_intelligence", DIB_MODULES)
        self.assertIn("module.dynamic_input_blueprint", DIB_MODULES)

    def test_idea_only_path_reaches_finance_without_raw_inputs(self) -> None:
        result = run_idea_to_manifest_flow(
            {
                "project_id": "project_shawarma",
                "name": "محل شاورما",
                "sector": "Food Service",
                "activity": "shawarma shop",
                "location_country": "SA",
            }
        )
        self.assertEqual(result["manifest"]["status"], "approved")
        self.assertEqual(result["manifest_validation"]["status"], "passed")
        self.assertEqual(result["finance"]["status"], "ready")
        self.assertEqual(result["blockers"], [])
        self.assertTrue(result["bus_messages"])
        self.assertTrue(all(row["message"]["socket_id"] in DIB_SOCKETS for row in result["bus_messages"]))
        self.assertIn("approved_input_manifest", result["finance"])

    def test_csv_xlsx_and_pdf_quote_are_mapped_to_blueprint_items(self) -> None:
        profile = {"project_id": "project_files", "sector": "Food Service", "activity": "shawarma shop"}
        interview = build_product_ai_interview(profile)
        csv_result = map_intake_to_blueprint_items(
            {
                "file_name": "assumptions.csv",
                "csv_text": "input_key,label,value\nunit_price,meal selling price,18\nvariable_cost,ingredients,7\nmonthly_units,monthly sales,4200\nmonthly_fixed_cost,rent and salaries,36000\n",
            },
            interview["proposed_items"],
        )
        xlsx_result = map_intake_to_blueprint_items(
            {"file_name": "supplier.xlsx", "file_base64": minimal_xlsx_base64()},
            csv_result["mapped_items"],
        )
        pdf_result = map_intake_to_blueprint_items(
            {"file_name": "quote.pdf", "pdf_text": "equipment quote startup_cost SAR 155000"},
            xlsx_result["mapped_items"],
        )
        blueprint = build_dynamic_input_blueprint(profile, pdf_result["mapped_items"], source="file_intake")
        approved_items = []
        for item in blueprint["items"]:
            if item["input_key"] in {"startup_cost", "monthly_fixed_cost", "unit_price", "variable_cost", "monthly_units"}:
                approved_items.append(item | {"value_state": item.get("value_state") or "FILE_IMPORTED", "review_status": "approved"})
            else:
                approved_items.append(item)
        manifest = build_approved_input_manifest(blueprint | {"items": approved_items})
        self.assertEqual(manifest["status"], "approved")
        self.assertGreater(manifest["normalized_inputs"]["startup_cost"], 0)
        self.assertEqual(validate_manifest_for_runtime(manifest)["status"], "passed")

    def test_unknown_required_item_blocks_manifest_validation_before_finance(self) -> None:
        blueprint = build_dynamic_input_blueprint({"project_id": "project_unknown"}, [])
        manifest = build_approved_input_manifest(blueprint)
        gate = validate_manifest_for_runtime(manifest)
        self.assertEqual(manifest["status"], "blocked")
        self.assertEqual(gate["status"], "blocked")
        finance, blockers = finance_from_approved_manifest(manifest)
        self.assertEqual(finance["status"], "not_ready")
        self.assertTrue(blockers)

    def test_market_research_returns_same_item_to_customer_decision(self) -> None:
        item = {"input_key": "capex_equipment", "label": "معدات محل شاورما", "value_state": "UNKNOWN"}
        pack = request_market_evidence(DIBBus(), item, geography="SA")
        updated = apply_customer_decision(item, {"action": "accept_market_median", "evidence_pack": pack})
        self.assertEqual(updated["input_key"], item["input_key"])
        self.assertEqual(updated["value_state"], "MARKET_ESTIMATED")
        self.assertGreater(updated["value"], 0)
        self.assertTrue(updated["evidence_refs"])

    def test_draft_revision_and_revision_comparison_are_runtime_objects(self) -> None:
        profile = {"project_id": "project_revision", "sector": "Food Service"}
        base = run_idea_to_manifest_flow(profile)["blueprint"]
        revised = create_draft_revision(
            base,
            [{"input_key": "unit_price", "action": "enter_value", "value": 22}],
            reason="customer_adjusted_price",
        )
        comparison = compare_blueprint_revisions(base, revised)
        self.assertEqual(revised["parent_blueprint_id"], base["blueprint_id"])
        self.assertEqual(revised["contract_id"], "dib.draft.revision.v1")
        self.assertTrue(any(change["input_key"] == "unit_price" for change in comparison["item_changes"]))


if __name__ == "__main__":
    unittest.main()
