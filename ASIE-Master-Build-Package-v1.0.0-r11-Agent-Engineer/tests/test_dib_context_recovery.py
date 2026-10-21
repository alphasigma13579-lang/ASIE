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

    def test_verified_legacy_omissions_are_read_only_and_never_backfilled(self):
        from backend.dib_persistence import _json_dump, _payload_hash
        from backend.dib_api import dib_customer_recovery
        first = self.create()
        for omitted in (("project_id",), ("revision",), ("project_id", "revision")):
            payload = copy.deepcopy(first["payload"])
            for key in omitted: payload.pop(key)
            with self.store._write_transaction() as connection:
                connection.execute("UPDATE dib_blueprints SET payload_json=?, payload_hash=? WHERE blueprint_id=?",
                    (_json_dump(payload), _payload_hash(payload), first["blueprint_id"]))
            before = self.snapshot()
            loaded = self.store.load_session(self.sid, allow_legacy_read=True)
            self.assertEqual(loaded["current_blueprint"], payload)
            self.assertIsNone(loaded["origin_reference"])
            self.assertEqual(dib_customer_recovery(loaded, "synthetic-org")[0]["target"], {"kind": "owner_review"})
            with self.assertRaises(DIBPersistenceError): self.store.load_session(self.sid)
            with self.assertRaises(DIBPersistenceError): self.update(first["origin_reference"])
            with self.assertRaises(DIBPersistenceError): self.store.close_session(self.sid)
            with self.assertRaises(DIBApiError):
                DIBApiController(self.store).dispatch("POST", f"/api/dib/sessions/{self.sid}/approved-manifests", {})
            self.assertEqual(before, self.snapshot())
            with self.store._write_transaction() as connection:
                connection.execute("UPDATE dib_blueprints SET payload_hash='corrupt' WHERE blueprint_id=?", (first["blueprint_id"],))
            with self.assertRaises(DIBPersistenceError): self.store.load_session(self.sid, allow_legacy_read=True)

    def test_legacy_read_opt_in_rejects_contradictory_identity_types_and_hash(self):
        from backend.dib_persistence import _payload_hash
        first = self.create()
        for change in ({"project_id": None}, {"project_id": "other"}, {"revision": True}, {"revision": "1"}, {"revision": 2}, {"blueprint_id": "other"}):
            record = copy.deepcopy(first)
            record["payload"].pop("revision" if "project_id" in change else "project_id")
            record["payload"].update(change)
            record["payload_hash"] = _payload_hash(record["payload"])
            with self.subTest(change=change), self.assertRaises(DIBPersistenceError):
                self.store._blueprint_reference(record, self.sid, "synthetic-project", allow_legacy_read=True)
        record = copy.deepcopy(first); record["payload"].pop("revision")
        record["payload_hash"] = _payload_hash(record["payload"]); record["revision"] = 2
        with self.assertRaises(DIBPersistenceError):
            self.store._blueprint_reference(record, self.sid, "synthetic-project", allow_legacy_read=True)

    def test_new_exemption_state_requires_supplied_reason_not_inherited_reason(self):
        prior = {"item_id": "item", "input_key": "unit_price", "required": True, "value": 12,
            "value_state": "USER_PROVIDED", "reason": "Earlier unrelated explanation", "evidence_refs": []}
        for state in ("INTENTIONAL_ZERO", "NOT_APPLICABLE"):
            supplied = {"item_id": "item", "input_key": "unit_price", "value": 0, "value_state": state}
            with self.subTest(state=state), self.assertRaisesRegex(DIBPersistenceError, "reason_required"):
                self.store._revision_items({"items": [prior]}, [supplied], None)
            supplied["reason"] = "Explicit current reason"
            result = self.store._revision_items({"items": [prior]}, [supplied], None)[0]
            self.assertEqual(result["reason"], "Explicit current reason")
            repeated = dict(supplied); repeated.pop("reason")
            self.assertEqual(self.store._revision_items({"items": [result]}, [repeated], None)[0]["reason"], "Explicit current reason")

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
        self.store.load_session = lambda _, *, allow_legacy_read=False: (_ for _ in ()).throw(ValueError("PRIVATE_MARKER"))
        try:
            with self.assertRaises(DIBApiError) as caught:
                controller.dispatch("GET", f"/api/dib/sessions/{self.sid}")
            self.assertEqual(caught.exception.status, 500)
            self.assertEqual(caught.exception.code, "dib_operation_failed")
            self.assertIsInstance(caught.exception.__cause__, ValueError)
            self.assertEqual(str(caught.exception.__cause__), "PRIVATE_MARKER")
        finally:
            self.store.load_session = original



class DIBRecoveryCommandBoundaryTests(DIBRecoveryPersistenceTests):
    def test_partial_item_save_preserves_other_items_and_origin_conflicts(self):
        first = self.create()
        controller = DIBApiController(self.store)
        row = copy.deepcopy(first["payload"]["items"][0])
        row.update(value=0, value_state="INTENTIONAL_ZERO", reason="Synthetic explicit zero")
        command = {"contract_id": "dib.blueprint.write.v2", "expected_original": first["origin_reference"], "items": [row]}
        saved = controller.dispatch("POST", f"/api/dib/sessions/{self.sid}/blueprints", command)
        self.assertEqual(saved.status, 201)
        current = self.store.load_session(self.sid)["current_blueprint"]
        self.assertEqual([item["item_id"] for item in current["items"]], [item["item_id"] for item in first["payload"]["items"]])
        self.assertEqual(current["items"][1:], first["payload"]["items"][1:])
        self.assertEqual(current["items"][0]["value_state"], "INTENTIONAL_ZERO")
        self.assertEqual(current["items"][0]["reason"], row["reason"])
        before = self.snapshot()
        with self.assertRaises(DIBApiError) as caught:
            controller.dispatch("POST", f"/api/dib/sessions/{self.sid}/blueprints", command)
        self.assertEqual(caught.exception.status, 409)
        self.assertEqual(before, self.snapshot())
        row = copy.deepcopy(current["items"][1])
        row.update(value=125, value_state="USER_PROVIDED")
        original = self.store.load_session(self.sid)["origin_reference"]
        saved = controller.dispatch("POST", f"/api/dib/sessions/{self.sid}/blueprints", command | {"expected_original": original, "items": [row]})
        self.assertEqual(saved.status, 201)
        after = self.store.load_session(self.sid)["current_blueprint"]
        self.assertEqual(after["items"][0], current["items"][0])
        self.assertEqual(after["items"][2:], current["items"][2:])
        self.assertEqual(after["items"][1]["value"], 125)

    def test_initial_items_reject_forged_authority_and_malformed_data_atomically(self):
        from backend.dib_runtime import _item
        base = _item("startup_cost", value=100, state="USER_PROVIDED", required=True, confidence=0.78)
        base["review_status"] = "approved"
        changes = [
            {"value_state": "HUMAN_APPROVED"}, {"value_state": "EVIDENCE_VERIFIED"},
            {"value_state": "MARKET_ESTIMATED"}, {"evidence_refs": {"verified": "invented"}},
            {"evidence_refs": ["verified:invented"]}, {"evidence_refs": [True]},
            {"evidence_refs": ["file:"]}, {"evidence_refs": ["file:" + "x" * 512]},
            {"value_state": "INTENTIONAL_ZERO", "value": 0, "reason": ""},
            {"value_state": "NOT_APPLICABLE", "value": 0, "reason": " "},
            {"value_state": "NOT_APPLICABLE", "value": 3, "reason": "Synthetic"},
            {"value": True}, {"value": float("nan")}, {"value": float("inf")}, {"value": "10"},
            {"item_id": 1}, {"input_key": True}, {"required": False}, {"required": 1},
            {"review_status": "verified"}, {"source_type": "evidence_verified", "value_source": "evidence_verified"},
            {"approved_by": "forged"}, {"action": "approve"}, {"evidence_pack": {}},
            {"source_type": []}, {"value_source": {}}, {"review_status": []},
            {"confidence": float("nan")}, {"confidence": True}, {"revision": True}, {"revision": 0},
            {"category": {"approved_by": "forged"}}, {"label": []}, {"unit": {}}, {"reason": []},
            {"value_state": "AI_SUGGESTED", "value_source": "product_ai_interview", "source_type": "product_ai_interview", "confidence": .45, "review_status": "draft"},
            {"value_state": "FILE_IMPORTED", "value_source": "file_import", "source_type": "file_import", "confidence": .72},
        ]
        controller = DIBApiController(self.store)
        before = self.snapshot()
        for route in ("items", "blueprint"):
            for change in changes:
                with self.subTest(route=route, change=change):
                    rows = [base | change]
                    command = {"items": rows} if route == "items" else {"blueprint": build_dynamic_input_blueprint({"project_id": "synthetic-project"}, rows)}
                    with self.assertRaises(DIBApiError) as caught:
                        controller.dispatch("POST", f"/api/dib/sessions/{self.sid}/blueprints", command)
                    self.assertEqual(caught.exception.status, 422)
                    self.assertEqual(before, self.snapshot())
        for rows in ([base, base | {"input_key": "unit_price"}], [base, base | {"item_id": "another"}], None, {}, [None]):
            with self.subTest(rows=rows), self.assertRaises(DIBPersistenceError):
                self.store.save_blueprint(self.sid, self.blueprint | {"items": rows})
            self.assertEqual(before, self.snapshot())

    def test_initial_canonical_adapters_and_decisions_preserve_all_metadata(self):
        from backend.dib_module_adapters import execute_dib_module_adapter
        from backend.dib_intake_item_governance import apply_governed_item_decision
        profile = {"project_id": "synthetic-project"}
        ai = execute_dib_module_adapter("module.product_ai_interview", {"project_profile": profile})["proposed_items"]
        file_rows = execute_dib_module_adapter("module.data_intake", {"intake_payload": {"file_name": "synthetic.csv", "csv_text": "input_key,value\nunit_price,0\n"}})["mapped_items"]
        entered = apply_governed_item_decision(file_rows[0], {"action": "enter_value", "value": 12})["item"]
        unknown = apply_governed_item_decision(entered, {"action": "mark_unknown", "reason": "Synthetic unknown"})["item"]
        rejected = apply_governed_item_decision(file_rows[0], {"action": "reject", "reason": "Synthetic reject"})["item"]
        exempt_ai = apply_governed_item_decision(ai[0], {"action": "not_applicable", "reason": "Synthetic exemption"})["item"]
        exempt_file = apply_governed_item_decision(file_rows[0], {"action": "not_applicable", "reason": "Synthetic exemption"})["item"]
        zero = entered | {"value": 0, "value_state": "INTENTIONAL_ZERO", "reason": "Synthetic explicit zero"}
        for rows in (ai, file_rows, [entered], [unknown], [rejected], [exempt_ai], [exempt_file], [zero]):
            with self.subTest(state=rows[0]["value_state"]):
                sid = self.store.start_session(profile)["session_id"]
                blueprint = build_dynamic_input_blueprint(profile, rows)
                saved = self.store.save_blueprint(sid, blueprint)
                self.assertEqual(saved["payload"]["items"], blueprint["items"])
                for item in rows:
                    self.assertIn(item, saved["payload"]["items"])
                loaded = self.store.load_session(sid)
                self.assertIsNone(loaded["approved_manifest_id"])
                self.assertIsNone(loaded["validation_gate_id"])

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

    def test_repeated_intake_uses_persisted_identity_and_retains_cas(self):
        controller = DIBApiController(self.store)
        path = f"/api/dib/sessions/{self.sid}/blueprints"
        first = controller.dispatch("POST", path, {
            "intake_payload": {"file_name": "first.csv", "csv_text": "input_key,value\nunit_price,15\nmonthly_units,30\n"},
        }).payload["blueprint"]
        original = copy.deepcopy(first["payload"])
        identities = {row["input_key"]: row["item_id"] for row in original["items"]}
        command = {
            "contract_id": "dib.blueprint.write.v2", "expected_original": first["origin_reference"],
            "intake_payload": {"file_name": "second.csv", "csv_text": "input_key,value\nunit_price,20\nsynthetic_extra,4\n"},
            "existing_items": [{"input_key": "unit_price", "item_id": "client-replacement"}],
        }
        second = controller.dispatch("POST", path, command).payload["blueprint"]
        rows = {row["input_key"]: row for row in second["payload"]["items"]}
        self.assertEqual(rows["unit_price"]["item_id"], identities["unit_price"])
        self.assertEqual(rows["unit_price"]["value"], 20)
        self.assertEqual(rows["unit_price"]["value_state"], "FILE_IMPORTED")
        self.assertEqual(rows["unit_price"]["review_status"], "draft")
        self.assertEqual(rows["unit_price"]["evidence_refs"], ["file:second.csv"])
        self.assertEqual(rows["monthly_units"], next(row for row in original["items"] if row["input_key"] == "monthly_units"))
        self.assertNotIn(rows["synthetic_extra"]["item_id"], identities.values())
        self.assertNotEqual(rows["synthetic_extra"]["item_id"], "client-replacement")
        self.assertEqual(self.store.load_blueprint(first["blueprint_id"])["payload"], original)
        before = self.snapshot()
        with self.assertRaises(DIBApiError) as stale:
            controller.dispatch("POST", path, command)
        self.assertEqual(stale.exception.status, 409)
        self.assertEqual(before, self.snapshot())
        forged = copy.deepcopy(rows["unit_price"])
        forged["item_id"] = "client-replacement"
        with self.assertRaises(DIBApiError) as mismatch:
            controller.dispatch("POST", path, {
                "contract_id": "dib.blueprint.write.v2", "expected_original": second["origin_reference"], "items": [forged],
            })
        self.assertEqual(mismatch.exception.status, 422)
        self.assertEqual(mismatch.exception.code, "dib_item_target_changed")
        self.assertEqual(before, self.snapshot())
        with self.assertRaises(DIBApiError) as missing:
            controller.dispatch("POST", path, {"intake_payload": command["intake_payload"]})
        self.assertEqual(missing.exception.status, 409)
        self.assertEqual(before, self.snapshot())
        bad_blueprint = copy.deepcopy(second["payload"])
        bad_blueprint["items"][0]["item_id"] = "client-replacement"
        with self.assertRaises(DIBApiError) as explicit:
            controller.dispatch("POST", path, {
                "contract_id": "dib.blueprint.write.v2", "expected_original": second["origin_reference"],
                "blueprint": bad_blueprint,
            })
        self.assertEqual(explicit.exception.status, 422)
        self.assertEqual(before, self.snapshot())

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

    def test_tenant_legacy_read_and_list_keep_ownership_and_do_not_enable_writes(self):
        from backend.dib_persistence import _json_dump, _payload_hash
        status, body = self.call('POST', '/api/dib/sessions', {'project_profile': {'project_id': self.project_a.project_id}})
        self.assertEqual(status, 201)
        sid = body['session']['session_id']
        status, body = self.call('POST', f'/api/dib/sessions/{sid}/blueprints', {'items': []})
        self.assertEqual(status, 201)
        store = self.mount.controller.store
        saved = store.load_session(sid)['current_blueprint']
        for omitted in (("project_id",), ("revision",), ("project_id", "revision")):
            payload = copy.deepcopy(saved)
            for key in omitted: payload.pop(key)
            with store._write_transaction() as conn:
                conn.execute('UPDATE dib_blueprints SET payload_json=?,payload_hash=? WHERE blueprint_id=?', (_json_dump(payload), _payload_hash(payload), saved['blueprint_id']))
            with store._read_connection() as conn:
                before = {table:[tuple(row) for row in conn.execute(f'SELECT * FROM {table}')] for table in ('dib_sessions','dib_blueprints','dib_approved_manifests','dib_validation_gates')}
            status, body = self.call('GET', f'/api/dib/sessions/{sid}')
            self.assertEqual(status, 200)
            self.assertIsNone(body['session']['origin_reference'])
            self.assertEqual(body['session']['current_blueprint'], payload)
            self.assertEqual(body['session']['recovery_items'][0]['target'], {'kind':'owner_review'})
            status, body = self.call('GET', '/api/dib/sessions?project_id=' + self.project_a.project_id)
            self.assertEqual(status, 200)
            self.assertIsNone(body['sessions'][0]['origin_reference'])
            status, _ = self.request('GET', f'/api/dib/sessions/{sid}', token=self.token_b, organization_id=self.org_b['organization_id'])
            self.assertEqual(status, 404)
            for tail in ('approved-manifests','validation-gates','project-run-readiness','close'):
                status, body = self.call('POST', f'/api/dib/sessions/{sid}/{tail}', {})
                self.assertGreaterEqual(status, 400, (tail,body))
            with store._read_connection() as conn:
                after = {table:[tuple(row) for row in conn.execute(f'SELECT * FROM {table}')] for table in before}
            self.assertEqual(before,after)

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
    def test_all_fixed_finance_admission_codes_preserve_domain_status(self):
        codes = ["canonical_admission_invalid_" + key for key in ("operation_id", "idempotency_key", "expected_manifest_id", "expected_manifest_payload_hash", "expected_gate_id", "expected_gate_payload_hash")]
        codes += ["canonical_admission_" + key + "_session_mismatch" for key in ("blueprint", "manifest", "gate")]
        codes += ["stale_gate_lineage"]
        for code in codes:
            for status in (400, 409):
                with self.subTest(code=code, status=status):
                    error = DIBApiError(code, status)
                    self.assertEqual((error.code, error.status), (code, status))
                    private = DIBApiError(code + ":PRIVATE_MARKER", status)
                    self.assertEqual((private.code, private.status), ("dib_operation_failed", 500))

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


if __name__ == "__main__":
    unittest.main()
