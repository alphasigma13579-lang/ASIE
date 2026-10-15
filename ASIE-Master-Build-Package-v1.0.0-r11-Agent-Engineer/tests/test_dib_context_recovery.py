from __future__ import annotations

import copy
from concurrent.futures import ThreadPoolExecutor
import threading
import unittest

from backend.dib_api import DIBApiController, DIBApiError
from backend.dib_persistence import DIBPersistenceStore, DIBPersistenceError
from backend.dib_runtime import build_dynamic_input_blueprint, build_approved_input_manifest, validate_manifest_for_runtime


class DIBRecoveryPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.store = DIBPersistenceStore()
        self.addCleanup(self.store.close)
        self.session = self.store.start_session({"project_id": "synthetic-project"})
        self.sid = self.session["session_id"]
        self.blueprint = build_dynamic_input_blueprint({"project_id": "synthetic-project"}, [])

    def create(self):
        return self.store.save_blueprint(self.sid, self.blueprint)

    def update(self, reference, blueprint=None, **kwargs):
        return self.store.save_blueprint(self.sid, blueprint or self.blueprint,
            command_contract="dib.blueprint.write.v2", expected_original=reference, **kwargs)

    def snapshot(self):
        with self.store._read_connection() as connection:
            return {table: [tuple(row) for row in connection.execute(f"SELECT * FROM {table} ORDER BY rowid")]
                    for table in ("dib_sessions", "dib_blueprints", "dib_approved_manifests", "dib_validation_gates", "dib_events")}

    def test_legacy_create_preserved_and_unprotected_update_denied(self):
        first = self.create()
        self.assertEqual(first["blueprint_id"], self.blueprint["blueprint_id"])
        before = self.snapshot()
        with self.assertRaisesRegex(DIBPersistenceError, "origin_required"):
            self.store.save_blueprint(self.sid, self.blueprint)
        self.assertEqual(before, self.snapshot())

    def test_new_revision_preserves_parent_and_clears_direct_store_chain(self):
        first = self.create()
        manifest = build_approved_input_manifest(first["payload"])
        self.store.save_approved_manifest(self.sid, manifest)
        gate = validate_manifest_for_runtime(manifest)
        self.store.save_validation_gate(self.sid, gate)
        original = copy.deepcopy(self.store.load_blueprint(first["blueprint_id"]))
        saved = self.update(first["origin_reference"])
        current = self.store.load_session(self.sid)
        self.assertNotEqual(saved["blueprint_id"], first["blueprint_id"])
        self.assertEqual(saved["payload"]["parent_blueprint_id"], first["blueprint_id"])
        self.assertEqual(saved["revision"], first["revision"] + 1)
        self.assertEqual(original, self.store.load_blueprint(first["blueprint_id"]))
        self.assertIsNone(current["approved_manifest_id"])
        self.assertIsNone(current["validation_gate_id"])
        self.assertEqual(current["origin_reference"], saved["origin_reference"])

    def test_every_origin_field_is_typed_and_bound(self):
        first = self.create()
        before = self.snapshot()
        for key in first["origin_reference"]:
            wrong = dict(first["origin_reference"])
            wrong[key] = True if key == "revision" else "wrong"
            with self.subTest(key=key), self.assertRaisesRegex(DIBPersistenceError, "write_conflict"):
                self.update(wrong)
            self.assertEqual(before, self.snapshot())

    def test_concurrent_updates_have_one_winner(self):
        first = self.create()
        barrier = threading.Barrier(2)
        def save():
            barrier.wait()
            try:
                return self.update(first["origin_reference"])["blueprint_id"]
            except DIBPersistenceError as exc:
                return str(exc)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: save(), range(2)))
        self.assertEqual(results.count("dib_blueprint_write_conflict"), 1)
        self.assertEqual(len(self.snapshot()["dib_blueprints"]), 2)

    def test_concurrent_initial_creates_have_one_winner(self):
        barrier = threading.Barrier(2)
        def save():
            barrier.wait()
            try:
                return self.create()["blueprint_id"]
            except DIBPersistenceError as exc:
                return str(exc)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: save(), range(2)))
        self.assertEqual(results.count("dib_blueprint_origin_required"), 1)
        self.assertEqual(len(self.snapshot()["dib_blueprints"]), 1)

    def test_event_failure_rolls_back_revision_and_pointers(self):
        first = self.create()
        before = self.snapshot()
        original = self.store._append_event_row
        def fail(*args, **kwargs):
            raise RuntimeError("synthetic_failure")
        self.store._append_event_row = fail
        try:
            with self.assertRaisesRegex(RuntimeError, "synthetic_failure"):
                self.update(first["origin_reference"])
        finally:
            self.store._append_event_row = original
        self.assertEqual(before, self.snapshot())

    def test_governed_decision_uses_saved_target_and_no_approval_side_effect(self):
        first = self.create()
        item = first["payload"]["items"][0]
        saved = self.update(first["origin_reference"], item_decisions=[{
            "item_id": item["item_id"], "input_key": item["input_key"],
            "decision": {"action": "enter_value", "value": 123},
        }])
        changed = next(row for row in saved["payload"]["items"] if row["item_id"] == item["item_id"])
        self.assertEqual(changed["value"], 123)
        self.assertEqual(changed["required"], item["required"])
        self.assertIsNone(self.store.load_session(self.sid)["approved_manifest_id"])
        self.assertEqual(len(saved["payload"]["items"]), len(first["payload"]["items"]))

    def test_wrong_target_duplicate_and_evidence_pack_denied_without_write(self):
        first = self.create()
        item = first["payload"]["items"][0]
        command = {"item_id": item["item_id"], "input_key": item["input_key"], "decision": {"action": "enter_value", "value": 123}}
        variants = [[command | {"item_id": "wrong"}], [command, command],
                    [command | {"decision": {"action": "accept_market_median", "evidence_pack": {}}}]]
        before = self.snapshot()
        for commands in variants:
            with self.subTest(commands=commands), self.assertRaises(DIBPersistenceError):
                self.update(first["origin_reference"], item_decisions=commands)
            self.assertEqual(before, self.snapshot())

    def test_unknown_internal_fault_is_safe_server_error(self):
        controller = DIBApiController(self.store)
        original = self.store.load_session
        self.store.load_session = lambda _: (_ for _ in ()).throw(ValueError("PRIVATE_MARKER"))
        try:
            with self.assertRaises(DIBApiError) as caught:
                controller.dispatch("GET", f"/api/dib/sessions/{self.sid}")
            self.assertEqual(caught.exception.status, 500)
            self.assertEqual(caught.exception.code, "dib_operation_failed")
        finally:
            self.store.load_session = original


if __name__ == "__main__":
    unittest.main()

class DIBRecoveryCommandBoundaryTests(DIBRecoveryPersistenceTests):
    def test_workspace_initial_intake_then_versioned_second_save(self):
        controller = DIBApiController(self.store)
        first = controller.dispatch("POST", f"/api/dib/sessions/{self.sid}/blueprints", {
            "contract_id": "dib.blueprint.write.v2", "expected_original": None,
            "intake_payload": {"file_name": "synthetic-input.csv", "rows": [{"input_key": "unit_price", "value": 15, "label": "Price"}]},
        }).payload["blueprint"]
        rows = copy.deepcopy(first["payload"]["items"])
        row = next(row for row in rows if row["input_key"] == "unit_price")
        row.update(value=20, value_state="USER_PROVIDED")
        second = controller.dispatch("POST", f"/api/dib/sessions/{self.sid}/blueprints", {
            "contract_id": "dib.blueprint.write.v2", "expected_original": first["origin_reference"], "items": rows,
        }).payload["blueprint"]
        self.assertNotEqual(first["blueprint_id"], second["blueprint_id"])
        self.assertEqual(next(row for row in second["payload"]["items"] if row["input_key"] == "unit_price")["value"], 20)
        self.assertEqual(self.store.load_blueprint(first["blueprint_id"])["payload"], first["payload"])

    def test_null_or_empty_decisions_do_not_create_revision(self):
        first = self.create()
        before = self.snapshot()
        for value in (None, [], {}, "bad"):
            with self.subTest(value=value), self.assertRaises(DIBApiError):
                DIBApiController(self.store).dispatch("POST", f"/api/dib/sessions/{self.sid}/blueprints", {
                    "contract_id": "dib.blueprint.write.v2", "expected_original": first["origin_reference"], "item_decisions": value,
                })
            self.assertEqual(before, self.snapshot())

    def test_full_list_cannot_assert_evidence_authority_or_implicit_exemption(self):
        first = self.create()
        before = self.snapshot()
        for change in ({"value_state": "EVIDENCE_VERIFIED", "value": 15},
                       {"value_state": "HUMAN_APPROVED", "value": 15},
                       {"action": "accept_market_median", "evidence_pack": {"weighted_median": 15}},
                       {"value_state": "NOT_APPLICABLE", "reason": "", "value": 0},
                       {"value_state": "INTENTIONAL_ZERO", "reason": "", "value": 0},
                       {"evidence_refs": ["verified:invented"]}):
            payload = copy.deepcopy(first["payload"])
            payload["items"][0].update(change)
            with self.subTest(change=change), self.assertRaises(DIBPersistenceError):
                self.update(first["origin_reference"], payload)
            self.assertEqual(before, self.snapshot())

    def test_explicit_zero_preserves_identity_and_uses_user_metadata(self):
        first = self.create()
        payload = copy.deepcopy(first["payload"])
        payload["items"][0].update(value=0, value_state="INTENTIONAL_ZERO", reason="No expenditure applies to this synthetic case")
        saved = self.update(first["origin_reference"], payload)
        row = saved["payload"]["items"][0]
        self.assertEqual(row["item_id"], first["payload"]["items"][0]["item_id"])
        self.assertEqual(row["confidence"], 0.78)
        self.assertEqual(row["source_type"], "user_input")
        self.assertEqual(row["value_state"], "INTENTIONAL_ZERO")

    def test_full_list_identity_required_types_and_omitted_items(self):
        first = self.create()
        original = first["payload"]["items"][0]
        before = self.snapshot()
        for change in ({"item_id": "other"}, {"required": not original["required"]}, {"required": int(original["required"])}, {"value_state": []}):
            payload = copy.deepcopy(first["payload"])
            payload["items"] = [original | change]
            with self.subTest(change=change), self.assertRaises(DIBPersistenceError):
                self.update(first["origin_reference"], payload)
            self.assertEqual(before, self.snapshot())
        payload = copy.deepcopy(first["payload"])
        payload["items"] = [original | {"value": 12, "value_state": "USER_PROVIDED"}]
        saved = self.update(first["origin_reference"], payload)
        self.assertEqual(saved["payload"]["items"][1:], first["payload"]["items"][1:])
        before = self.snapshot()
        payload = copy.deepcopy(saved["payload"])
        payload["items"][0].update(value=True)
        with self.assertRaises(DIBPersistenceError):
            self.update(saved["origin_reference"], payload)
        self.assertEqual(before, self.snapshot())

    def test_real_preview_reimport_retains_ids_and_original_evidence(self):
        from backend.dib_intake_item_governance import preview_intake_item_mapping
        first = self.create()
        preview = preview_intake_item_mapping({"file_name": "synthetic.csv", "csv_text": "input_key,label,value\nunit_price,Unit price,27\n"}, first["payload"]["items"])
        originals = {item["input_key"]: item for item in first["payload"]["items"]}
        rows = [item | {"item_id": originals[item["input_key"]]["item_id"], "required": originals[item["input_key"]]["required"]} for item in preview["mapped_items"]]
        saved = self.update(first["origin_reference"], first["payload"] | {"items": rows})
        row = next(item for item in saved["payload"]["items"] if item["input_key"] == "unit_price")
        self.assertEqual(row["value"], 27)
        self.assertEqual(row["item_id"], originals["unit_price"]["item_id"])
        self.assertEqual(self.store.load_blueprint(first["blueprint_id"])["payload"], first["payload"])

    def test_consistent_read_reference_during_concurrent_revision(self):
        first = self.create()
        barrier = threading.Barrier(2)
        def writer():
            barrier.wait()
            return self.update(first["origin_reference"])
        def reader():
            barrier.wait()
            observations = [self.store.load_session(self.sid) for _ in range(20)]
            for loaded in observations:
                blueprint, origin = loaded["current_blueprint"], loaded["origin_reference"]
                self.assertEqual(blueprint["blueprint_id"], origin["blueprint_id"])
                self.assertEqual(blueprint["revision"], origin["revision"])
                from backend.dib_persistence import _payload_hash
                self.assertEqual(_payload_hash(blueprint), origin["payload_hash"])
            return observations
        with ThreadPoolExecutor(max_workers=2) as pool:
            write = pool.submit(writer)
            read = pool.submit(reader)
            write.result(); self.assertEqual(len(read.result()), 20)

    def test_corrupt_stored_hash_denies_read_and_update_without_repair(self):
        first = self.create()
        with self.store._write_transaction() as connection:
            connection.execute("UPDATE dib_blueprints SET payload_hash = 'corrupted' WHERE blueprint_id = ?", (first["blueprint_id"],))
        before = self.snapshot()
        with self.assertRaisesRegex(DIBPersistenceError, "integrity_invalid"):
            self.store.load_session(self.sid)
        with self.assertRaisesRegex(DIBPersistenceError, "integrity_invalid"):
            self.update(first["origin_reference"])
        self.assertEqual(before, self.snapshot())


class DIBRecoveryProjectionTests(unittest.TestCase):
    def test_unknown_state_and_missing_identity_require_owner_review(self):
        from backend.dib_api import dib_customer_recovery
        from backend.dib_runtime import FINANCE_REQUIRED_KEYS
        for row in ({"input_key": FINANCE_REQUIRED_KEYS[0], "item_id": "item", "value": 1, "value_state": "unknown_external_state"},
                    {"input_key": FINANCE_REQUIRED_KEYS[0], "value": None, "value_state": "UNKNOWN"}):
            session = {"session_id": "s", "project_id": "p", "current_blueprint": {"items": [row]},
                       "origin_reference": {"blueprint_id": "b", "revision": 1, "payload_hash": "h"}}
            result = dib_customer_recovery(session, "o")
            target = next(item for item in result if item["recovery_id"].endswith(":" + FINANCE_REQUIRED_KEYS[0]))
            self.assertEqual(target["target"], {"kind": "owner_review"})
            self.assertEqual(target["requirement_code"], "DIB_ITEM_INTEGRITY_REVIEW_REQUIRED")
            self.assertNotIn("unknown_external_state", str(result))

    def test_duplicate_or_untyped_stored_identity_never_offers_an_unwritable_editor(self):
        from backend.dib_api import dib_customer_recovery
        from backend.dib_runtime import FINANCE_REQUIRED_KEYS
        row = {"input_key": FINANCE_REQUIRED_KEYS[0], "item_id": "item", "value": 1, "value_state": "USER_PROVIDED"}
        for rows in ([row, row], [row, row | {"input_key": FINANCE_REQUIRED_KEYS[1]}],
                     [row | {"item_id": None}], [row | {"value_state": []}]):
            session = {"session_id": "s", "project_id": "p", "current_blueprint": {"items": rows},
                       "origin_reference": {"blueprint_id": "b", "revision": 1, "payload_hash": "h"}}
            with self.subTest(rows=rows):
                result = dib_customer_recovery(session, "o")
                self.assertTrue(result)
                self.assertTrue(all(item["target"] == {"kind": "owner_review"} for item in result))
                self.assertTrue(all(item["requirement_code"] == "DIB_ITEM_INTEGRITY_REVIEW_REQUIRED" for item in result))


class DIBRecoveryHttpSafetyTests(unittest.TestCase):
    from tests import test_sec_beta_03_dib_tenant_boundary as fixtures
    setUp = fixtures.DIBTenantOwnershipBoundaryTests.setUp
    request = fixtures.DIBTenantOwnershipBoundaryTests.request

    def call(self, method, path, payload=None):
        return self.request(method, path, token=self.token_a, organization_id=self.org_a['organization_id'], payload=payload)

    def test_auth_store_failure_returns_safe_500(self):
        from unittest.mock import patch
        with patch.object(self.mount.auth_repo, 'principal_for_token', side_effect=RuntimeError('PRIVATE_MARKER')):
            status, body = self.call('GET', '/api/dib/sessions')
        self.assertEqual((status, body['error']), (500, 'dib_internal_error'))
        self.assertNotIn('PRIVATE_MARKER', str(body))

    def test_nested_http_and_tenant_errors_are_redacted_from_response_and_events(self):
        from unittest.mock import patch
        status, body = self.call('POST', '/api/dib/sessions', {'project_profile': {'project_id': self.project_a.project_id}})
        self.assertEqual(status, 201)
        sid = body['session']['session_id']
        path = f'/api/dib/sessions/{sid}'
        status, body = self.call('POST', path + '/blueprints', {'PRIVATE_MARKER': [{'api_key': 'PRIVATE_MARKER'}]})
        self.assertEqual(status, 422)
        self.assertNotIn('PRIVATE_MARKER', str(body))
        with patch.object(self.mount.controller.store, 'load_session', side_effect=RuntimeError('PRIVATE_MARKER')):
            status, body = self.call('GET', path)
        self.assertEqual(status, 500)
        self.assertNotIn('PRIVATE_MARKER', str(body))
        with patch.object(self.mount.controller.store, 'save_blueprint', side_effect=RuntimeError('PRIVATE_MARKER')):
            status, body = self.call('POST', path + '/blueprints', {'items': []})
        self.assertEqual(status, 500)
        self.assertNotIn('PRIVATE_MARKER', str(body))
        status, events = self.call('GET', path + '/events')
        self.assertEqual(status, 200)
        self.assertNotIn('PRIVATE_MARKER', str(events))

    def test_current_project_ownership_is_rechecked_for_existing_session(self):
        status, body = self.call('POST', '/api/dib/sessions', {'project_profile': {'project_id': self.project_a.project_id}})
        self.assertEqual(status, 201)
        sid = body['session']['session_id']
        with self.auth_repo.connect() as connection:
            connection.execute('UPDATE projects SET organization_id = ? WHERE project_id = ?', (self.org_b['organization_id'], self.project_a.project_id))
        for method, suffix, payload in [('GET', '', None), ('GET', '/events', None), ('POST', '/blueprints', {'items': []})]:
            with self.subTest(method=method, suffix=suffix):
                status, body = self.call(method, f'/api/dib/sessions/{sid}{suffix}', payload)
                self.assertEqual(status, 404)
                self.assertNotIn(self.org_b['organization_id'], str(body))
        with self.auth_repo.connect() as connection:
            connection.execute('DELETE FROM projects WHERE project_id = ?', (self.project_a.project_id,))
        status, body = self.call('GET', f'/api/dib/sessions/{sid}')
        self.assertEqual(status, 404)

    def test_read_only_member_cannot_write_and_receives_no_action_authority(self):
        status, body = self.call('POST', '/api/dib/sessions', {'project_profile': {'project_id': self.project_a.project_id}})
        sid = body['session']['session_id']
        status, _ = self.call('POST', f'/api/dib/sessions/{sid}/blueprints', {'items': []})
        self.assertEqual(status, 201)
        self.auth_repo.add_membership(organization_id=self.org_a['organization_id'], user_id=self.user_b['user_id'], role='viewer')
        status, body = self.request('GET', f'/api/dib/sessions/{sid}', token=self.token_b, organization_id=self.org_a['organization_id'])
        self.assertEqual(status, 200)
        self.assertTrue(body['session']['recovery_items'])
        self.assertTrue(all(not item['action']['allowed'] for item in body['session']['recovery_items']))
        status, body = self.request('POST', f'/api/dib/sessions/{sid}/blueprints', token=self.token_b, organization_id=self.org_a['organization_id'], payload={'items': []})
        self.assertEqual(status, 403)

class DIBSafeCanonicalErrorTests(unittest.TestCase):
    def test_dynamic_client_field_details_are_removed_without_changing_rejection_status(self):
        for category in ("canonical_admission_forbidden_fields", "canonical_admission_unknown_fields"):
            for suffix in ("finance_inputs", "PRIVATE_MARKER_secret_nested_key"):
                with self.subTest(category=category, suffix=suffix):
                    error = DIBApiError(category + ":" + suffix, 422)
                    self.assertEqual(error.code, category)
                    self.assertEqual(error.status, 422)
                    self.assertNotIn(suffix, str(error))
                    self.assertEqual(DIBApiError(error.code, 422).code, category)
        unknown = DIBApiError("PRIVATE_MARKER_unknown", 422)
        self.assertEqual((unknown.code, unknown.status), ("dib_operation_failed", 500))
