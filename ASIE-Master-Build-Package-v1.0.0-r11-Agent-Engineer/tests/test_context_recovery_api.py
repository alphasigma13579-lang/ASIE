from __future__ import annotations

from types import SimpleNamespace
import unittest
from unittest.mock import patch

from backend import asie_local_api as api
from backend.workflow import project_readiness


class CurrentRecoveryProjectionTests(unittest.TestCase):
    def test_project_evidence_projection_excludes_other_organization_and_corrupt_links(self):
        rows = [{"dataset_id": "own", "organization_id": "org-a", "source_id": "source", "review_status": "approved"},
                {"dataset_id": "foreign", "organization_id": "org-b", "source_id": "source", "review_status": "approved", "private": "synthetic-secret"}]
        repo = SimpleNamespace(source_records=lambda: [], datasets=lambda: rows,
            project_evidence_links=lambda _: [{"dataset_id": "own"}, {"dataset_id": "foreign", "private": "synthetic-secret"}, {"dataset_id": "own", "transformation_id": "foreign-transform"}],
            project_transformations=lambda _: [{"transformation_id": "own-transform", "dataset_id": "own"}, {"transformation_id": "foreign-transform", "dataset_id": "foreign", "private": "synthetic-secret"}])
        repo.read_project_evidence = lambda project_id: {"source_records": repo.source_records(), "datasets": repo.datasets(), "evidence_links": repo.project_evidence_links(project_id), "transformations": repo.project_transformations(project_id)}
        with patch.object(api, "dataset_quality_gate", side_effect=lambda row, source, **context: {"dataset_id": row["dataset_id"], "status": "passed", "reasons": []}):
            result = api.build_evidence_register(repo, "project-a", "draft", organization_id="org-a")
        self.assertEqual([row["dataset_id"] for row in result["datasets"]], ["own"])
        self.assertEqual(result["linked_dataset_ids"], ["own"])
        self.assertNotIn("foreign", str(result))
        self.assertNotIn("synthetic-secret", str(result))
        self.assertEqual(len(result["evidence_links"]), 1)
        self.assertEqual(len(result["transformations"]), 1)

    def test_current_readiness_targets_name_and_derived_cost_inputs_exactly(self):
        project = SimpleNamespace(project_id="p", organization_id="o", updated_at="version", name="", sector="", jurisdiction="", inputs={})
        readiness = project_readiness(project, [], [], include_recovery=True)
        self.assertNotIn("recovery_items", project_readiness(project, [], []))
        items = {row["requirement_code"]: row for row in readiness["recovery_items"]}
        self.assertEqual(items["MISSING_PROJECT_NAME"]["target"]["field_keys"], ["name"])
        self.assertEqual(items["MISSING_PROJECT_JURISDICTION"]["target"]["field_keys"], ["jurisdiction"])
        self.assertNotIn("monthly_fixed_cost", items["MISSING_MONTHLY_FIXED_COST"]["target"]["field_keys"])
        self.assertEqual(items["ASSUMPTION_COUNT_REQUIRED"]["count"], {"current": 0, "required": 5, "remaining": 5})
        self.assertTrue(all(row["action"]["allowed"] is False for row in items.values()))
        self.assertTrue(all(row["source"]["organization_id"] == "o" for row in items.values()))


class CurrentRecoveryHttpTests(unittest.TestCase):
    from tests import test_tenant_isolation_matrix as fixture
    setUp = fixture.TenantIsolationMatrixTests.setUp
    request = fixture.TenantIsolationMatrixTests.request

    def test_current_project_reads_contain_no_foreign_dataset_and_preserve_snapshot(self):
        before = self.repo.get_run_overview(self.run_b_id)
        for suffix in ("workspace", "evidence-register", "evidence-ledger"):
            status, body = self.request("GET", f"/api/projects/{self.project_a.project_id}/{suffix}", token=self.token_a, organization_id=self.org_a_id)
            self.assertEqual(status, 200, (suffix, body))
            self.assertNotIn(self.dataset_b_id, str(body))
            self.assertNotIn(self.org_b_id, str(body))
            if suffix == "workspace":
                self.assertNotIn("recovery_items", body["readiness"])
                self.assertEqual(body["current_recovery"]["source"], "current_draft")
                self.assertEqual(body["capabilities"][0]["state"], "disabled")
                self.assertNotIn("sbom", str(body["capabilities"]))
        self.assertEqual(before, self.repo.get_run_overview(self.run_b_id))
        self.assertEqual(self.repo.list_project_runs(self.project_a.project_id), [])

    def test_exact_transformation_edit_cannot_reparent_foreign_record(self):
        own = self.repo.save_dataset(self.fixture.DATASET_PAYLOAD | {"organization_id": self.org_a_id})
        foreign = self.repo.save_transformation(self.dataset_b_id, {"operation_type": "select_column", "input_columns": ["value"], "review_status": "draft"})
        status, body = self.request("POST", f"/api/datasets/{own['dataset_id']}/transformations", token=self.token_a, organization_id=self.org_a_id,
            payload={"transformation_id": foreign["transformation_id"], "operation_type": "select_column", "input_columns": ["value"], "review_status": "approved"})
        self.assertEqual(status, 404)
        self.assertEqual(body["error"], "transformation_not_found")
        self.assertEqual(self.repo.get_transformation(foreign["transformation_id"]), foreign)


class EvidenceRecoveryIdentityTests(unittest.TestCase):
    def project(self):
        return SimpleNamespace(project_id='p', organization_id='o', updated_at='v')

    def register(self):
        return dict(source_records=[], datasets=[], quality_gates=[], transformations=[], evidence_links=[], linked_dataset_ids=[])

    def test_unknown_requirements_have_distinct_opaque_stable_identities(self):
        targets = [{'target_type': 'PRIVATE_MARKER', 'target_id': value, 'coverage_status': 'unsupported'} for value in ('one', 'two')]
        first = api.current_evidence_recovery(self.project(), self.register(), {'targets': targets})
        second = api.current_evidence_recovery(self.project(), self.register(), {'targets': targets})
        self.assertEqual(first, second)
        self.assertEqual(len({item['recovery_id'] for item in first}), 2)
        self.assertNotIn('PRIVATE_MARKER', str(first))
        self.assertTrue(all(item['target'] == {'kind': 'owner_review'} for item in first))

    def test_broken_link_uses_existing_target_and_valid_replacement_clears_deficit(self):
        target = {'target_type': 'assumption', 'target_id': 'owned-assumption', 'coverage_status': 'unsupported', 'source_version': 'current'}
        register = self.register() | {'unresolved_dependency_count': 1,
            'unresolved_dependency_targets': [api.canonical_hash({'type': target['target_type'], 'id': target['target_id']})]}
        result = api.current_evidence_recovery(self.project(), register, {'targets': [target]})
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['target'], {'kind': 'evidence_binding', 'target_type': 'assumption', 'target_id': 'owned-assumption'})
        self.assertEqual(api.current_evidence_recovery(self.project(), register, {'targets': [target | {'coverage_status': 'supported'}]}), [])
        unknown = register | {'unresolved_dependency_targets': ['opaque-unmapped']}
        self.assertEqual(api.current_evidence_recovery(self.project(), unknown, {'targets': []})[0]['target'], {'kind': 'owner_review'})


class CustomerDatasetProvenanceTests(unittest.TestCase):
    from tests import test_tenant_isolation_matrix as fixture
    setUp = fixture.TenantIsolationMatrixTests.setUp
    request = fixture.TenantIsolationMatrixTests.request

    def customer_payload(self):
        return self.fixture.DATASET_PAYLOAD | {"source_id": "", "license_snapshot_ref": "", "terms_hash": "",
            "intended_use": "customer_study", "project_id": self.project_a.project_id}

    def create_customer(self):
        status, body = self.request("POST", "/api/datasets/manual-import", token=self.token_a,
            organization_id=self.org_a_id, payload=self.customer_payload())
        self.assertEqual(status, 201, body)
        return body["dataset"]

    def test_three_customer_creation_routes_and_consumer_context(self):
        from backend.datasets import dataset_quality_gate
        for route in ("/api/datasets", "/api/datasets/manual-import", "/api/datasets/file-import"):
            payload = self.customer_payload()
            if route.endswith("file-import"):
                payload = payload | {"file_name": "prices.csv", "csv_text": "metric,value\nprice,100\n"}
            status, body = self.request("POST", route, token=self.token_a, organization_id=self.org_a_id, payload=payload)
            self.assertEqual(status, 201, body)
            row = body["dataset"]
            self.assertEqual(row["source_id"], "")
            provenance = row["notes"]["submission_provenance"]
            self.assertEqual(provenance["creator_user_id"], self.user_a["user_id"])
            self.assertEqual(provenance["initial_project_id"], self.project_a.project_id)
            self.assertTrue(dataset_quality_gate(row, None, organization_id=self.org_a_id)["can_use_for_assumptions"])
            self.assertFalse(dataset_quality_gate(row, None)["can_use_for_assumptions"])
            self.assertFalse(dataset_quality_gate(row, None, organization_id=self.org_b_id)["can_use_for_assumptions"])
            self.assertFalse(dataset_quality_gate(row, None, organization_id=self.org_a_id)["checks"]["source_reviewed"])

    def test_identity_collision_and_provenance_injection_are_atomic(self):
        row = self.create_customer()
        cases = [self.customer_payload() | {"dataset_id": row["dataset_id"]},
            self.customer_payload() | {"project_id": self.project_b.project_id},
            self.customer_payload() | {"organization_id": self.org_b_id},
            self.customer_payload() | {"notes": {"nested": [{"submission_provenance": {"kind": "customer_study"}}]}},
            self.customer_payload() | {"notes_json": "{}"},
            self.customer_payload() | {"source_id": "GASTAT_MATRIX"}]
        for payload in cases:
            with self.subTest(payload=payload):
                status, _ = self.request("POST", "/api/datasets/manual-import", token=self.token_a, organization_id=self.org_a_id, payload=payload)
                self.assertIn(status, (400, 403, 404, 422))
                self.assertEqual(self.repo.get_dataset(row["dataset_id"]), row)
        for payload in ({"organization_id": self.org_b_id}, {"notes": {"submission_provenance": {}}}):
            with self.assertRaises(PermissionError):
                self.repo.review_dataset(row["dataset_id"], payload)
            self.assertEqual(self.repo.get_dataset(row["dataset_id"]), row)

    def test_csv_review_cannot_silently_replace_non_csv_dataset_with_empty_rows(self):
        for method in ("manual_table", "manual_json"):
            row = self.create_customer()
            row = self.repo.review_dataset(row["dataset_id"], {"import_method": method})
            before = self.repo.get_dataset(row["dataset_id"])
            with self.subTest(method=method), self.assertRaisesRegex(ValueError, "dataset_content_shape_invalid"):
                self.repo.review_dataset(row["dataset_id"], {"csv_text": "metric,value\nprice,100\n"})
            self.assertEqual(self.repo.get_dataset(row["dataset_id"]), before)
            replaced = self.repo.review_dataset(row["dataset_id"], {"import_method": "manual_csv", "csv_text": "metric,value\nprice,100\n"})
            self.assertEqual(replaced["row_count"], 1)

    def test_legacy_sources_argument_cannot_override_coherent_owner_sources(self):
        expected = self.repo.read_project_evidence(self.project_a.project_id)["source_records"]
        for supplied in ([], [{"source_id": "invented-caller-source"}]):
            register = api.build_evidence_register(self.repo, self.project_a.project_id, "synthetic", supplied, organization_id=self.org_a_id)
            self.assertEqual(register["source_records"], expected)

    def test_content_replacement_invalidates_dependents_and_malformed_rolls_back(self):
        row = self.create_customer()
        transform = self.repo.save_transformation(row["dataset_id"], {"operation_type": "select_column", "input_columns": ["value"], "review_status": "approved"})
        link = self.repo.save_evidence_link(self.project_a.project_id, {"target_id": "synthetic-target", "dataset_id": row["dataset_id"], "human_review_decision": "approved"})
        for bad in ({"rows": "bad"}, {"rows": [{"value": 1}, 9]}, {"csv_text": None}, {"json_rows": None}, {"csv_text": "a,b\n1\n", "import_method": "manual_csv"}, {"csv_text": "a,a\n1,2", "import_method": "manual_csv"}, {"csv_text": 'a,b\nx,"unterminated', "import_method": "manual_csv"}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.repo.review_dataset(row["dataset_id"], bad)
            self.assertEqual(self.repo.get_dataset(row["dataset_id"]), row)
            self.assertEqual(self.repo.get_transformation(transform["transformation_id"]), transform)
        metadata = self.repo.review_dataset(row["dataset_id"], {"title": "Revised title"})
        self.assertEqual(metadata["review_status"], "approved_for_use")
        self.assertEqual(self.repo.get_transformation(transform["transformation_id"]), transform)
        updated = self.repo.review_dataset(row["dataset_id"], {"rows": row["preview"], "review_status": "approved_for_use", "human_review_decision": "approved"})
        self.assertEqual(updated["review_status"], "review_required")
        self.assertEqual(updated["human_review_decision"], "")
        self.assertEqual(self.repo.get_transformation(transform["transformation_id"])["review_status"], "review_required")
        self.assertEqual(self.repo.get_evidence_link(self.project_a.project_id, "synthetic-target", row["dataset_id"])["human_review_decision"], "")
        with self.assertRaisesRegex(ValueError, "dataset_revision_conflict"):
            self.repo.save_evidence_link(self.project_a.project_id, link, expected_dataset_revision=row["updated_at"])
        empty = self.repo.review_dataset(row["dataset_id"], {"rows": []})
        self.assertEqual(empty["row_count"], 0)
        self.assertEqual(empty["preview"], [])

    def test_malformed_or_legacy_provenance_has_no_license_exemption(self):
        import copy
        from backend.datasets import dataset_quality_gate
        row = self.create_customer()
        for change in ({"version": True}, {"version": 2}, {"created_at": "bad"}, {"organization_id": self.org_b_id}, {"kind": "unknown"}, {"initial_project_id": ""}):
            corrupted = copy.deepcopy(row)
            corrupted["notes"]["submission_provenance"].update(change)
            gate = dataset_quality_gate(corrupted, None, organization_id=self.org_a_id)
            self.assertFalse(gate["can_use_for_assumptions"])
            self.assertIn("missing_terms_hash", gate["reasons"])
        legacy = copy.deepcopy(row)
        del legacy["notes"]["submission_provenance"]
        self.assertIn("missing_license_snapshot_ref", dataset_quality_gate(legacy, None, organization_id=self.org_a_id)["reasons"])

    def test_raw_file_import_shapes_and_nested_provenance_rejected(self):
        from backend.datasets import normalize_file_import_payload
        for value in (None, 2, {}, []):
            with self.subTest(value=value), self.assertRaises(ValueError):
                normalize_file_import_payload({"file_name": "prices.csv", "csv_text": value})
        with self.assertRaises(PermissionError):
            normalize_file_import_payload({"file_name": "prices.csv", "csv_text": "a\n1", "notes": {"inside": {"submission_provenance": {}}}})

    def test_shared_organization_reuse_and_ledger_fallback_no_official_credit(self):
        from backend.evidence_ledger import build_evidence_ledger
        row = self.create_customer()
        project = self.repo.create_project({"name": "Another study", "organization_id": self.org_a_id})
        for kind in ("assumption", "sector_criterion"):
            self.repo.save_evidence_link(project.project_id, {"target_type": kind, "target_id": kind,
                "dataset_id": row["dataset_id"], "human_review_decision": "approved"}, expected_dataset_revision=row["updated_at"])
        register = api.build_evidence_register(self.repo, project.project_id, "draft", organization_id=self.org_a_id)
        self.assertEqual(register["consuming_context"]["organization_id"], self.org_a_id)
        register["quality_gates"] = []
        entries = build_evidence_ledger(register, [], "synthetic")
        self.assertEqual(len(entries), 2)
        for entry in entries:
            self.assertTrue(entry["can_support_target"])
            self.assertEqual(entry["source_id"], "")
            self.assertEqual(entry["material_origin"], "customer_study")
            self.assertEqual(entry["evidence_confidence_factors"]["source_review"], 0)
        register.pop("consuming_context")
        self.assertTrue(all(not entry["can_support_target"] for entry in build_evidence_ledger(register, [], "synthetic")))

    def test_replacement_rollback_preserves_all_rows_and_historical_snapshot(self):
        import sqlite3
        row = self.create_customer()
        transform = self.repo.save_transformation(row["dataset_id"], {"operation_type": "select_column", "input_columns": ["value"], "review_status": "approved"})
        before_snapshot = self.repo.get_run_overview(self.run_b_id)
        with self.repo.connect() as conn:
            conn.execute("CREATE TRIGGER synthetic_abort_invalidation BEFORE UPDATE ON transformations BEGIN SELECT RAISE(ABORT, 'synthetic rollback'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            self.repo.review_dataset(row["dataset_id"], {"rows": [{"metric": "price", "value": 200}]})
        self.assertEqual(self.repo.get_dataset(row["dataset_id"]), row)
        self.assertEqual(self.repo.get_transformation(transform["transformation_id"]), transform)
        self.assertEqual(self.repo.get_run_overview(self.run_b_id), before_snapshot)

    def test_common_writer_cannot_reparent_transformation(self):
        row = self.create_customer()
        transform = self.repo.save_transformation(row["dataset_id"], {"operation_type": "select_column", "input_columns": ["value"]})
        with self.assertRaises(PermissionError):
            self.repo.save_transformation(self.dataset_b_id, {"transformation_id": transform["transformation_id"], "operation_type": "select_column", "input_columns": ["value"]})
        self.assertEqual(self.repo.get_transformation(transform["transformation_id"]), transform)

    def test_zero_user_local_external_imports_remain_legacy(self):
        import tempfile
        from pathlib import Path
        from backend.repository import LEGACY_ORGANIZATION_ID
        with tempfile.TemporaryDirectory() as directory:
            legacy_repo = api.Repository(Path(directory) / "legacy.sqlite3")
            with patch.object(api, "REPO", legacy_repo), patch.object(api, "legacy_local_operator_allowed", return_value=True):
                for route in ("/api/datasets", "/api/datasets/manual-import", "/api/datasets/file-import"):
                    payload = self.fixture.DATASET_PAYLOAD | {"file_name": "data.csv", "csv_text": "metric,value\nprice,100\n"}
                    status, body = self.request("POST", route, organization_id=LEGACY_ORGANIZATION_ID, payload=payload)
                    self.assertEqual(status, 201, body)
                    self.assertNotIn("submission_provenance", body["dataset"]["notes"])

    def test_valid_quoted_csv_and_tail_replacement_require_review(self):
        from backend.datasets import normalize_dataset_payload
        import json
        parsed = normalize_dataset_payload({"import_method": "manual_csv", "csv_text": 'item,price\n"quoted, item",10\n"two\nlines",20\n'})
        self.assertEqual(json.loads(parsed["preview_json"])[1]["item"], "two\nlines")
        row = self.create_customer()
        first = [{"metric": "price", "value": index} for index in range(8)]
        second = first[:5] + list(reversed(first[5:]))
        saved = self.repo.review_dataset(row["dataset_id"], {"rows": first})
        approved = self.repo.review_dataset(row["dataset_id"], {"review_status": "approved_for_use", "human_review_decision": "approved"})
        replaced = self.repo.review_dataset(row["dataset_id"], {"rows": second})
        self.assertEqual(approved["preview"], replaced["preview"])
        self.assertEqual(approved["notes"]["profile"], replaced["notes"]["profile"])
        self.assertEqual(replaced["review_status"], "review_required")

    def test_coherent_read_never_combines_pre_replacement_transform_with_new_link(self):
        row = self.create_customer()
        transform = self.repo.save_transformation(row["dataset_id"], {"operation_type": "select_column", "input_columns": ["value"], "review_status": "approved"})
        self.repo.save_evidence_link(self.project_a.project_id, {"target_id": "old-target", "dataset_id": row["dataset_id"], "transformation_id": transform["transformation_id"], "human_review_decision": "approved"})
        original = self.repo._dataset_from_row
        changed = False
        def concurrent_write(stored):
            nonlocal changed
            result = original(stored)
            if not changed and result["dataset_id"] == row["dataset_id"]:
                changed = True
                self.repo.review_dataset(row["dataset_id"], {"rows": [{"metric": "price", "value": 300}]})
                current = self.repo.review_dataset(row["dataset_id"], {"review_status": "approved_for_use", "human_review_decision": "approved"})
                self.repo.save_evidence_link(self.project_a.project_id, {"target_id": "new-target", "dataset_id": row["dataset_id"], "transformation_id": transform["transformation_id"], "human_review_decision": "approved"}, expected_dataset_revision=current["updated_at"])
            return result
        with patch.object(self.repo, "_dataset_from_row", side_effect=concurrent_write):
            coherent = api.build_evidence_register(self.repo, self.project_a.project_id, "synthetic", organization_id=self.org_a_id)
        self.assertTrue(changed)
        self.assertNotIn("new-target", [link["target_id"] for link in coherent["evidence_links"]])
        from backend.evidence_ledger import build_evidence_ledger
        fresh = api.build_evidence_register(self.repo, self.project_a.project_id, "synthetic", organization_id=self.org_a_id)
        entries = build_evidence_ledger(fresh, fresh["source_records"], "synthetic", transformations=fresh["transformations"])
        new = next(entry for entry in entries if entry["target_id"] == "new-target")
        self.assertFalse(new["can_support_target"])
        self.assertEqual(new["transformation_status"], "review_required")

    def test_manifest_overlay_keeps_its_assumptions_and_uses_repository_snapshot(self):
        from backend.dib_canonical_finance_admission import ManifestBackedProjectRunDataAccess
        overlay = ManifestBackedProjectRunDataAccess(self.repo, {"project_id": self.project_a.project_id,
            "manifest_id": "synthetic-manifest", "normalized_inputs": {"unit_price": 987}, "items": []})
        expected = overlay.project_assumptions(self.project_a.project_id)
        self.assertEqual(expected[0]["value"], 987)
        with patch.object(self.repo, "read_project_evidence", wraps=self.repo.read_project_evidence) as coherent:
            api.build_evidence_register(overlay, self.project_a.project_id, "synthetic", organization_id=self.org_a_id)
            coherent.assert_called_once_with(self.project_a.project_id)
        self.assertEqual(overlay.project_assumptions(self.project_a.project_id), expected)
        with self.assertRaisesRegex(ValueError, "manifest_data_access_project_mismatch"):
            api.build_evidence_register(overlay, self.project_b.project_id, "synthetic", organization_id=self.org_b_id)
        with self.assertRaisesRegex(TypeError, "coherent_evidence_reader_required"):
            api.build_evidence_register(SimpleNamespace(repository=self.repo), self.project_a.project_id, "synthetic", organization_id=self.org_a_id)
