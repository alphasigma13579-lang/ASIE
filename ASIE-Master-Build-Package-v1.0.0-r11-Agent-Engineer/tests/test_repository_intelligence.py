import json
import sqlite3
from contextlib import closing
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from backend.identity import Principal
from backend.intelligence_context import ContextComponent, IntelligenceContext
from backend.repository import Repository


class RepositoryIntelligenceTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.repo = Repository(Path(directory.name) / "asie.db")
        with self.repo.connect() as conn:
            for org in ("org-a", "org-b"):
                conn.execute("INSERT INTO organizations (organization_id, name, lifecycle_status, created_at, updated_at) VALUES (?, ?, 'active', 'now', 'now')", (org, org))
            conn.commit()
        self.project = self.repo.create_project({"organization_id": "org-a", "name": "P", "sector": "retail", "jurisdiction": "SA"})
        self.second = self.repo.create_project({"organization_id": "org-a", "name": "Second", "sector": "retail", "jurisdiction": "SA"})
        self.foreign = self.repo.create_project({"organization_id": "org-b", "name": "Foreign", "sector": "retail", "jurisdiction": "SA"})
        self.principal = Principal("u", "s", "org-a", "organization_owner")

    def draft(self, key="draft", project=None):
        return self.repo.create_intelligence_context(payload={"project_id": (project or self.project).project_id, "idempotency_key": key}, principal=self.principal)

    def model(self, key="model", *, lineage=None, component_fields=None):
        context = IntelligenceContext("ctx-" + key, "org-a", self.project.project_id, "SA", "retail", key, components=[ContextComponent("component", "reference", {"text": "Reviewed example"}, "official-reference", "today", "SA", "retail", "medium", ["evidence-reference"] if lineage is None else lineage, "PENDING")])
        if component_fields:
            context.components = [replace(context.components[0], **component_fields)]
        return context.transition("VALIDATING").transition("INTEGRITY_LOCKED").transition("REVIEW_PENDING")

    def review(self, context, **overrides):
        return {"intelligence_context_id": context.context_build_id, "intelligence_context_hash": context.context_hash, "review_scope": "offline-example", "reviewed_output_hash": context.context_hash, "decision": "APPROVE", **overrides}


    def origin_events(self):
        with closing(self.repo.connect()) as conn:
            return [dict(row) for row in conn.execute("SELECT * FROM security_audit_events WHERE action = 'aia.context.origin.v1'")]

    def test_internal_key_type_rejected_before_lifecycle_fingerprint_or_insert(self):
        for key in (123, True, {}, {"key": "x"}, [], ["x"], None, "", "   "):
            context = self.model()
            context.idempotency_key = key
            with self.subTest(key=key), patch.object(IntelligenceContext, "transition", side_effect=AssertionError("lifecycle reached")), patch("backend.repository.idempotency_fingerprint", side_effect=AssertionError("fingerprint reached")), patch.object(self.repo, "_insert_intelligence_context", side_effect=AssertionError("insert reached")), self.assertRaisesRegex(ValueError, "context_idempotency_key_invalid"):
                self.repo.persist_validated_intelligence_context(context=context, principal=self.principal)
        with closing(self.repo.connect()) as conn:
            self.assertEqual(0, conn.execute("SELECT COUNT(*) FROM intelligence_contexts").fetchone()[0])
        self.assertEqual([], self.origin_events())

    def test_new_context_origin_is_atomic_unique_and_survives_draft_cas(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            records = list(pool.map(lambda _: self.draft("origin-concurrent"), range(2)))
        self.assertEqual(records[0], records[1])
        original_proof = self.origin_events()
        self.assertEqual(1, len(original_proof))
        self.assertEqual(records[0]["context_build_id"], original_proof[0]["target_id"])
        updated = self.repo.update_intelligence_context(context_build_id=records[0]["context_build_id"], organization_id="org-a", project_id=self.project.project_id, payload={}, expected_version=1, principal=self.principal)
        self.assertEqual(updated, self.draft("origin-concurrent"))
        self.assertEqual(original_proof, self.origin_events())
        model = self.model("origin-native")
        saved = self.repo.persist_validated_intelligence_context(context=model, principal=self.principal)
        self.assertEqual(saved, self.repo.persist_validated_intelligence_context(context=model, principal=self.principal))
        self.assertEqual(2, len(self.origin_events()))

    def test_legacy_replay_fails_closed_without_retroactive_origin(self):
        draft = self.draft("legacy")
        with closing(self.repo.connect()) as conn, conn:
            conn.execute("DELETE FROM security_audit_events WHERE action = 'aia.context.origin.v1'")
            original = tuple(conn.execute("SELECT * FROM intelligence_contexts").fetchone())
        with self.assertRaisesRegex(ValueError, "context_idempotency_conflict"):
            self.draft("legacy")
        self.assertEqual([], self.origin_events())
        read = self.repo.get_intelligence_context(context_build_id=draft["context_build_id"], organization_id="org-a", project_id=self.project.project_id, principal=self.principal)
        self.assertEqual(draft, read)
        with closing(self.repo.connect()) as conn:
            self.assertEqual(original, tuple(conn.execute("SELECT * FROM intelligence_contexts").fetchone()))
        self.repo.update_intelligence_context(context_build_id=draft["context_build_id"], organization_id="org-a", project_id=self.project.project_id, payload={}, expected_version=1, principal=self.principal)
        self.assertEqual([], self.origin_events())
        with self.assertRaisesRegex(ValueError, "context_idempotency_conflict"):
            self.draft("legacy")
        self.draft("new-key")
        self.assertEqual(1, len(self.origin_events()))

    def test_replay_rejects_malformed_shape_identity_and_client_origin(self):
        corruptions = [{"trusted": True}, {"origin": "public_draft"}, {"organization_id": "org-b"}, {"project_id": "foreign"}, {"context_build_id": "client-owned"}, {"version": True}, {"created_at": "forged"}, {"idempotency_key": "different"}, {"idempotency_fingerprint": "forged"}, {"component_manifest": [{"trusted": True}]}]
        for index, claims in enumerate(corruptions):
            key = "shape-" + str(index)
            draft = self.draft(key)
            with closing(self.repo.connect()) as conn, conn:
                conn.execute("UPDATE intelligence_contexts SET payload_json = ? WHERE context_build_id = ?", (json.dumps(draft | claims), draft["context_build_id"]))
                before = tuple(conn.execute("SELECT * FROM intelligence_contexts WHERE context_build_id = ?", (draft["context_build_id"],)).fetchone())
            with self.subTest(claims=claims), self.assertRaisesRegex(ValueError, "context_idempotency_conflict"):
                self.draft(key)
            with closing(self.repo.connect()) as conn:
                self.assertEqual(before, tuple(conn.execute("SELECT * FROM intelligence_contexts WHERE context_build_id = ?", (draft["context_build_id"],)).fetchone()))

    def test_origin_insert_failure_rolls_back_context_then_retry_creates_one_pair(self):
        with closing(self.repo.connect()) as conn, conn:
            conn.execute("CREATE TRIGGER fail_origin BEFORE INSERT ON security_audit_events WHEN NEW.action = 'aia.context.origin.v1' BEGIN SELECT RAISE(ABORT, 'injected_origin_failure'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            self.draft("retry")
        with closing(self.repo.connect()) as conn, conn:
            self.assertEqual(0, conn.execute("SELECT COUNT(*) FROM intelligence_contexts").fetchone()[0])
            conn.execute("DROP TRIGGER fail_origin")
        self.assertEqual([], self.origin_events())
        self.draft("retry")
        self.assertEqual(1, len(self.origin_events()))

    def test_origin_proof_scope_path_material_and_duplicate_are_fail_closed(self):
        changes = ({"organization_id": "org-b"}, {"target_id": "another-context"}, {"target_type": "other"}, {"action": "aia.context.create"}, {"result": "allowed"}, {"actor_user_id": None}, {"correlation_id": "forged"}, {"reason": "not-json"})
        for index, changeset in enumerate(changes):
            key = "proof-" + str(index)
            draft = self.draft(key)
            proof = self.origin_events()[-1]
            with closing(self.repo.connect()) as conn, conn:
                conn.execute("UPDATE security_audit_events SET " + ", ".join(field + " = ?" for field in changeset) + " WHERE event_id = ?", (*changeset.values(), proof["event_id"]))
            with self.subTest(changeset=changeset), self.assertRaisesRegex(ValueError, "context_idempotency_conflict"):
                self.draft(key)
        for field, value in (("policy", "unsupported"), ("creation_path", "validated_model"), ("project_id", self.second.project_id), ("creation_fingerprint", "different")):
            key = "material-" + field
            self.draft(key)
            proof = self.origin_events()[-1]
            reason = json.loads(proof["reason"]) | {field: value}
            with closing(self.repo.connect()) as conn, conn:
                conn.execute("UPDATE security_audit_events SET reason = ? WHERE event_id = ?", (json.dumps(reason, ensure_ascii=False, separators=(",", ":")), proof["event_id"]))
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "context_idempotency_conflict"):
                self.draft(key)
        self.draft("duplicate")
        proof = self.origin_events()[-1]
        with closing(self.repo.connect()) as conn, conn:
            conn.execute("INSERT INTO security_audit_events (event_id, actor_user_id, organization_id, action, target_type, target_id, result, reason, correlation_id, created_at) SELECT 'duplicate-proof', actor_user_id, organization_id, action, target_type, target_id, result, reason, correlation_id, created_at FROM security_audit_events WHERE event_id = ?", (proof["event_id"],))
        with self.assertRaisesRegex(ValueError, "context_idempotency_conflict"):
            self.draft("duplicate")

    def test_malformed_replay_json_and_missing_fields_are_safe_conflicts(self):
        for index, material in enumerate(("not-json", "[]", "null", "123", "{}")):
            key = "malformed-" + str(index)
            draft = self.draft(key)
            with closing(self.repo.connect()) as conn, conn:
                conn.execute("UPDATE intelligence_contexts SET payload_json = ? WHERE context_build_id = ?", (material, draft["context_build_id"]))
            with self.subTest(material=material), self.assertRaisesRegex(ValueError, "^context_idempotency_conflict$"):
                self.draft(key)

    def test_authorized_other_actor_can_replay_but_changed_scope_cannot(self):
        draft = self.draft("other-actor")
        other = Principal("second-owner", "s2", "org-a", "organization_owner")
        replay = self.repo.create_intelligence_context(payload={"project_id": self.project.project_id, "idempotency_key": "other-actor"}, principal=other, correlation_id="aia.context.origin.v1")
        self.assertEqual(draft, replay)
        proof = self.origin_events()
        self.assertEqual("u", proof[0]["actor_user_id"])
        with patch.object(self.repo, "intelligence_project_scope", return_value={"geography": "AE", "sector": "retail"}):
            self.repo.update_intelligence_context(context_build_id=draft["context_build_id"], organization_id="org-a", project_id=self.project.project_id, payload={}, expected_version=1, principal=self.principal)
            with self.assertRaisesRegex(ValueError, "context_idempotency_conflict"):
                self.draft("other-actor")
        self.assertEqual(proof, self.origin_events())

    def test_context_insert_failure_and_precommit_interruption_leave_no_orphans(self):
        with closing(self.repo.connect()) as conn, conn:
            conn.execute("CREATE TRIGGER fail_context BEFORE INSERT ON intelligence_contexts BEGIN SELECT RAISE(ABORT, 'injected_context_failure'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            self.draft("context-failure")
        self.assertEqual([], self.origin_events())
        with closing(self.repo.connect()) as conn, conn:
            self.assertEqual(0, conn.execute("SELECT COUNT(*) FROM intelligence_contexts").fetchone()[0])
            conn.execute("DROP TRIGGER fail_context")
        self.draft("context-failure")
        self.assertEqual(1, len(self.origin_events()))

        class InterruptedConnection(sqlite3.Connection):
            def __exit__(connection, exc_type, exc_value, traceback):
                if exc_type is None and connection.in_transaction:
                    connection.rollback()
                    raise RuntimeError("injected_precommit_interruption")
                return super().__exit__(exc_type, exc_value, traceback)

        def connect():
            connection = sqlite3.connect(self.repo.db_path, factory=InterruptedConnection)
            connection.row_factory = sqlite3.Row
            return connection

        with patch.object(self.repo, "connect", side_effect=connect), self.assertRaisesRegex(RuntimeError, "injected_precommit_interruption"):
            self.draft("interrupted")
        with closing(self.repo.connect()) as conn:
            self.assertEqual(1, conn.execute("SELECT COUNT(*) FROM intelligence_contexts").fetchone()[0])
        self.assertEqual(1, len(self.origin_events()))
        self.draft("interrupted")
        self.assertEqual(2, len(self.origin_events()))

    def test_native_replay_requires_native_proof_and_accepts_reconstructed_retry(self):
        original = self.model("native-retry")
        saved = self.repo.persist_validated_intelligence_context(context=original, principal=self.principal)
        reconstructed = self.model("native-retry")
        self.assertEqual(saved, self.repo.persist_validated_intelligence_context(context=reconstructed, principal=self.principal))
        proof = self.origin_events()[0]
        reason = json.loads(proof["reason"])
        self.assertEqual("validated_model", reason["creation_path"])
        with closing(self.repo.connect()) as conn, conn:
            conn.execute("DELETE FROM security_audit_events WHERE event_id = ?", (proof["event_id"],))
        with self.assertRaisesRegex(ValueError, "context_idempotency_conflict"):
            self.repo.persist_validated_intelligence_context(context=reconstructed, principal=self.principal)
        self.assertEqual([], self.origin_events())

    def test_client_owned_consistent_legacy_identity_and_old_allow_event_do_not_prove_origin(self):
        draft = self.draft("legacy-client-id")
        client_id = "ctx-client-chosen"
        with closing(self.repo.connect()) as conn, conn:
            conn.execute("DELETE FROM security_audit_events WHERE action = 'aia.context.origin.v1'")
            conn.execute("UPDATE intelligence_contexts SET context_build_id = ?, payload_json = ? WHERE context_build_id = ?", (client_id, json.dumps(draft | {"context_build_id": client_id}), draft["context_build_id"]))
            conn.execute("UPDATE security_audit_events SET target_id = ? WHERE action = 'aia.context.create'", (client_id,))
            before = tuple(conn.execute("SELECT * FROM intelligence_contexts").fetchone())
        with self.assertRaisesRegex(ValueError, "context_idempotency_conflict"):
            self.repo.create_intelligence_context(payload={"project_id": self.project.project_id, "idempotency_key": "legacy-client-id"}, principal=self.principal, correlation_id="aia.context.origin.v1")
        with closing(self.repo.connect()) as conn:
            self.assertEqual(before, tuple(conn.execute("SELECT * FROM intelligence_contexts").fetchone()))
        self.assertEqual([], self.origin_events())

    def test_official_repository_enforces_tenant_and_optimistic_version(self):
        created = self.draft()
        self.assertEqual((1, "DRAFT", ""), (created["version"], created["state"], created["context_hash"]))
        self.assertIsNotNone(self.repo.get_intelligence_context(context_build_id=created["context_build_id"], organization_id="org-a", project_id=self.project.project_id, principal=self.principal))
        with self.assertRaises(PermissionError):
            self.repo.get_intelligence_context(context_build_id=created["context_build_id"], organization_id="org-b", project_id=self.project.project_id, principal=self.principal)
        with self.assertRaises(RuntimeError):
            self.repo.update_intelligence_context(context_build_id=created["context_build_id"], organization_id="org-a", project_id=self.project.project_id, payload={}, expected_version=99, principal=self.principal)
        with self.assertRaises(ValueError):
            self.repo.save_intelligence_review(organization_id="org-a", project_id=self.project.project_id, overlay={"intelligence_context_id": created["context_build_id"], "intelligence_context_hash": "wrong"}, principal=self.principal)

    def test_public_payload_never_accepts_authority_even_empty_or_nested(self):
        for field, value in (("organization_id", "org-a"), ("state", "REVIEW_PENDING"), ("context_hash", ""), ("version", 4), ("components", []), ("component_manifest", []), ("geography", "SA"), ("sector", "retail"), ("approval", {"reviewer_id": "u"}), ("trusted", True)):
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.repo.create_intelligence_context(payload={"project_id": self.project.project_id, "idempotency_key": field, field: value}, principal=self.principal)
        with self.repo.connect() as conn:
            self.assertEqual(0, conn.execute("SELECT COUNT(*) FROM intelligence_contexts").fetchone()[0])

    def test_draft_update_preserves_identity_and_cas_has_one_winner(self):
        draft = self.draft()
        def update():
            try:
                return self.repo.update_intelligence_context(context_build_id=draft["context_build_id"], organization_id="org-a", project_id=self.project.project_id, payload={}, expected_version=1, principal=self.principal)
            except RuntimeError:
                return None
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: update(), range(2)))
        self.assertEqual(1, sum(result is not None for result in results))
        current = self.repo.get_intelligence_context(context_build_id=draft["context_build_id"], organization_id="org-a", project_id=self.project.project_id, principal=self.principal)
        self.assertEqual((2, "DRAFT", ""), (current["version"], current["state"], current["context_hash"]))
        for payload in ({"state": "REVIEW_PENDING"}, {"context_hash": "f" * 64}, {"component_manifest": []}, {"idempotency_key": "changed"}):
            with self.assertRaises(ValueError):
                self.repo.update_intelligence_context(context_build_id=draft["context_build_id"], organization_id="org-a", project_id=self.project.project_id, payload=payload, expected_version=2, principal=self.principal)
        self.assertEqual(current, self.repo.get_intelligence_context(context_build_id=draft["context_build_id"], organization_id="org-a", project_id=self.project.project_id, principal=self.principal))

    def test_idempotency_is_scoped_and_authorized_before_replay(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            records = list(pool.map(lambda _: self.draft("same-key"), range(2)))
        self.assertEqual(records[0], records[1])
        second = self.draft("same-key", self.second)
        self.assertNotEqual(records[0]["context_build_id"], second["context_build_id"])
        for principal in (None, Principal("foreign", "s", "org-b", "organization_owner"), Principal("viewer", "s", "org-a", "viewer")):
            with patch.object(self.repo, "_insert_intelligence_context") as insert, self.assertRaises(PermissionError):
                self.repo.create_intelligence_context(payload={"project_id": self.project.project_id, "idempotency_key": "same-key"}, principal=principal)
            insert.assert_not_called()
        self.assertIsNone(self.repo.get_intelligence_context(context_build_id=records[0]["context_build_id"], organization_id="org-a", project_id=self.second.project_id, principal=self.principal))

    def test_validated_model_requires_real_lifecycle_hash_and_saved_scope(self):
        context = self.model()
        record = self.repo.persist_validated_intelligence_context(context=context, principal=self.principal)
        self.assertEqual((4, "REVIEW_PENDING", context.context_hash), (record["version"], record["state"], record["context_hash"]))
        with self.assertRaises(ValueError):
            self.repo.persist_validated_intelligence_context(context={"trusted": True}, principal=self.principal)
        for attribute, value in (("context_hash", "f" * 64), ("state", "APPROVED_FOR_RUN"), ("version", True), ("geography", "foreign")):
            original = getattr(context, attribute)
            setattr(context, attribute, value)
            with self.subTest(attribute=attribute), self.assertRaises(ValueError):
                self.repo.persist_validated_intelligence_context(context=context, principal=self.principal)
            setattr(context, attribute, original)
        with self.assertRaises(ValueError):
            self.repo.update_intelligence_context(context_build_id=context.context_build_id, organization_id="org-a", project_id=self.project.project_id, payload={}, expected_version=4, principal=self.principal)
        self.assertEqual(record, self.repo.get_intelligence_context(context_build_id=context.context_build_id, organization_id="org-a", project_id=self.project.project_id, principal=self.principal))

    def test_draft_review_rejected_and_reviewer_is_bound_to_principal(self):
        draft = self.draft()
        with self.assertRaises(ValueError):
            self.repo.save_intelligence_review(organization_id="org-a", project_id=self.project.project_id, overlay={"intelligence_context_id": draft["context_build_id"], "intelligence_context_hash": "", "review_scope": "offline-example", "reviewed_output_hash": "x", "decision": "APPROVE"}, principal=self.principal)
        context = self.model()
        self.repo.persist_validated_intelligence_context(context=context, principal=self.principal)
        with self.assertRaises(PermissionError):
            self.repo.save_intelligence_review(organization_id="org-a", project_id=self.project.project_id, overlay=self.review(context, reviewer_id="forged"), principal=self.principal)
        review = self.repo.save_intelligence_review(organization_id="org-a", project_id=self.project.project_id, overlay=self.review(context), principal=self.principal)
        self.assertEqual("u", review["reviewer_id"])
        receipt = {"intelligence_context_id": context.context_build_id, "intelligence_context_hash": context.context_hash, "review_overlay_id": review["review_overlay_id"], "review_overlay_hash": review["review_overlay_hash"], "approval_scope": "offline-example", "approved_for_contract_version": "offline.example.v1", "valid_until": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()}
        with self.assertRaises(ValueError):
            self.repo.save_intelligence_approval(organization_id="org-a", project_id=self.project.project_id, receipt=receipt | {"conditions": ["forged"]}, principal=self.principal)
        saved = self.repo.save_intelligence_approval(organization_id="org-a", project_id=self.project.project_id, receipt=receipt, principal=self.principal)
        self.assertTrue(saved["approval_receipt_hash"])
        with self.assertRaises(ValueError):
            self.repo.save_intelligence_approval(organization_id="org-a", project_id=self.project.project_id, receipt=receipt | {"intelligence_context_id": draft["context_build_id"], "intelligence_context_hash": ""}, principal=self.principal)
        self.assertEqual("REVIEW_PENDING", self.repo.get_intelligence_context(context_build_id=context.context_build_id, organization_id="org-a", project_id=self.project.project_id, principal=self.principal)["state"])

    def test_missing_saved_scope_remains_missing(self):
        project = self.repo.create_project({"organization_id": "org-a", "name": "Incomplete", "inputs": {"location_country": "", "primary_sector_id": ""}})
        record = self.draft("missing", project)
        self.assertEqual(("", ""), (record["geography"], record["sector"]))
        self.assertEqual([], record["component_manifest"])

    def approval_request(self):
        """Create a native reviewed context and an unsigned receipt request."""
        context = self.model()
        self.repo.persist_validated_intelligence_context(context=context, principal=self.principal)
        review = self.repo.save_intelligence_review(organization_id="org-a", project_id=self.project.project_id, overlay=self.review(context), principal=self.principal)
        receipt = {"intelligence_context_id": context.context_build_id, "intelligence_context_hash": context.context_hash, "review_overlay_id": review["review_overlay_id"], "review_overlay_hash": review["review_overlay_hash"], "approval_scope": "offline-example", "approved_for_contract_version": "offline.example.v1", "valid_until": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()}
        return context, review, receipt

    def test_review_and_approval_reject_non_string_fields_before_storage(self):
        """Malformed model fields fail validation without inserting records."""
        context, _, receipt = self.approval_request()
        overlay = self.review(context) | {"reason": "", "review_overlay_hash": ""}
        for payload, method, argument in ((overlay, self.repo.save_intelligence_review, "overlay"), (receipt | {"approval_receipt_hash": ""}, self.repo.save_intelligence_approval, "receipt")):
            for field in payload:
                for value in ([], {}, None, True, 123):
                    with self.subTest(argument=argument, field=field, value=value), self.assertRaisesRegex(ValueError, "^invalid_intelligence_approval_request$"):
                        method(organization_id="org-a", project_id=self.project.project_id, principal=self.principal, **{argument: payload | {field: value}})
        with self.repo.connect() as conn:
            self.assertEqual(1, conn.execute("SELECT COUNT(*) FROM intelligence_review_overlays").fetchone()[0])
            self.assertEqual(0, conn.execute("SELECT COUNT(*) FROM intelligence_approval_receipts").fetchone()[0])

    def test_record_ids_are_server_owned_even_for_cross_tenant_guesses(self):
        """Guessed or replayed client IDs cannot reach the lookup or insert."""
        context, review, receipt = self.approval_request()
        saved = self.repo.save_intelligence_approval(organization_id="org-a", project_id=self.project.project_id, receipt=receipt, principal=self.principal)
        scopes = (("org-a", self.project.project_id, self.principal), ("org-b", self.foreign.project_id, Principal("foreign", "s", "org-b", "organization_owner")))
        for org, project, principal in scopes:
            for payload, method, argument, field, known_id, error in (
                (self.review(context), self.repo.save_intelligence_review, "overlay", "review_overlay_id", review["review_overlay_id"], "invalid_intelligence_review"),
                (receipt, self.repo.save_intelligence_approval, "receipt", "approval_receipt_id", saved["approval_receipt_id"], "invalid_intelligence_approval"),
            ):
                for value in (known_id, "unused-client-id", ""):
                    with self.subTest(org=org, field=field, value=value), patch.object(self.repo, "_intelligence_review_context", side_effect=AssertionError("client ID must not trigger lookup")) as lookup, self.assertRaisesRegex(ValueError, "^" + error + "$"):
                        method(organization_id=org, project_id=project, principal=principal, **{argument: payload | {field: value}})
                    lookup.assert_not_called()
        second_review = self.repo.save_intelligence_review(organization_id="org-a", project_id=self.project.project_id, overlay=self.review(context), principal=self.principal)
        second_receipt = self.repo.save_intelligence_approval(organization_id="org-a", project_id=self.project.project_id, receipt=receipt, principal=self.principal)
        self.assertNotEqual(review["review_overlay_id"], second_review["review_overlay_id"])
        self.assertNotEqual(saved["approval_receipt_id"], second_receipt["approval_receipt_id"])

    def test_approval_expiry_distinguishes_invalid_from_expired(self):
        """Invalid and naive dates differ from equal or past aware expiries."""
        _, _, receipt = self.approval_request()
        for value, error in (("not-a-date", "approval_expiry_invalid"), ("2026-10-07T00:00:00", "approval_expiry_invalid"), ("2026-10-06T00:00:00+00:00", "approval_expired"), ("2026-10-07T00:00:00+00:00", "approval_expired")):
            with self.subTest(value=value), patch("backend.repository.now_iso", return_value="2026-10-07T00:00:00+00:00"), self.assertRaisesRegex(ValueError, "^" + error + "$"):
                self.repo.save_intelligence_approval(organization_id="org-a", project_id=self.project.project_id, receipt=receipt | {"valid_until": value}, principal=self.principal)
        with self.repo.connect() as conn:
            self.assertEqual(0, conn.execute("SELECT COUNT(*) FROM intelligence_approval_receipts").fetchone()[0])


    def test_native_lineage_is_validated_before_serialization(self):
        """Lock the original malformed model; coercion must not make it valid."""
        for index, lineage in enumerate(("evidence-reference", ("evidence-reference",), {"evidence-reference": True}, [123], [True], [{}], [""], ["   "])):
            context = self.model("bad-lineage-" + str(index), lineage=lineage)
            with self.subTest(lineage=lineage), patch.object(self.repo, "_insert_intelligence_context") as insert, self.assertRaisesRegex(ValueError, "^context_component_invalid$"):
                self.repo.persist_validated_intelligence_context(context=context, principal=self.principal)
            insert.assert_not_called()
        with self.repo.connect() as conn:
            for table in ("intelligence_contexts", "intelligence_review_overlays", "intelligence_approval_receipts", "runs", "snapshots"):
                self.assertEqual(0, conn.execute("SELECT COUNT(*) FROM " + table).fetchone()[0])
        valid = self.model("valid-lineage", lineage=["evidence-reference", "manual:brief"])
        saved = self.repo.persist_validated_intelligence_context(context=valid, principal=self.principal)
        self.assertEqual(["evidence-reference", "manual:brief"], saved["component_manifest"][0]["lineage"])

    def test_review_and_receipt_audit_targets_match_server_owned_ids(self):
        context = self.model("audit")
        self.repo.persist_validated_intelligence_context(context=context, principal=self.principal)
        review = self.repo.save_intelligence_review(organization_id="org-a", project_id=self.project.project_id, overlay=self.review(context), principal=self.principal, correlation_id="review-attempt")
        receipt = {"intelligence_context_id": context.context_build_id, "intelligence_context_hash": context.context_hash, "review_overlay_id": review["review_overlay_id"], "review_overlay_hash": review["review_overlay_hash"], "approval_scope": "offline-example", "approved_for_contract_version": "offline.example.v1", "valid_until": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()}
        saved = self.repo.save_intelligence_approval(organization_id="org-a", project_id=self.project.project_id, receipt=receipt, principal=self.principal, correlation_id="receipt-attempt")
        events = self.repo.security_audit_events(organization_id="org-a")
        for action, target, correlation in (("aia.review.save", review["review_overlay_id"], "review-attempt"), ("aia.approval.save", saved["approval_receipt_id"], "receipt-attempt")):
            with self.subTest(action=action):
                matching = [event for event in events if event["action"] == action and event["correlation_id"] == correlation]
                self.assertEqual(1, len(matching))
                self.assertEqual(("u", "org-a", "allowed", target), tuple(matching[0][key] for key in ("actor_user_id", "organization_id", "result", "target_id")))

    def test_context_review_can_authorize_run_without_mutating_context(self):
        """Review and approval scopes have distinct native contract meanings."""
        context = self.model("scope")
        original = self.repo.persist_validated_intelligence_context(context=context, principal=self.principal)
        review = self.repo.save_intelligence_review(organization_id="org-a", project_id=self.project.project_id, overlay=self.review(context, review_scope="context"), principal=self.principal)
        receipt = {"intelligence_context_id": context.context_build_id, "intelligence_context_hash": context.context_hash, "review_overlay_id": review["review_overlay_id"], "review_overlay_hash": review["review_overlay_hash"], "approval_scope": "run", "approved_for_contract_version": "offline.example.v1", "valid_until": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()}
        for invalid in ({"intelligence_context_hash": "wrong"}, {"review_overlay_hash": "wrong"}, {"review_overlay_id": "missing"}, {"conditions": ["forged"]}):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                self.repo.save_intelligence_approval(organization_id="org-a", project_id=self.project.project_id, receipt=receipt | invalid, principal=self.principal)
        saved = self.repo.save_intelligence_approval(organization_id="org-a", project_id=self.project.project_id, receipt=receipt, principal=self.principal)
        self.assertEqual(("context", "run"), (review["review_scope"], saved["approval_scope"]))
        self.assertEqual(saved, self.repo.get_intelligence_approval_receipt(receipt_id=saved["approval_receipt_id"], organization_id="org-a", project_id=self.project.project_id, principal=self.principal))
        self.assertEqual(original, self.repo.get_intelligence_context(context_build_id=context.context_build_id, organization_id="org-a", project_id=self.project.project_id, principal=self.principal))
        with self.repo.connect() as conn:
            self.assertEqual(1, conn.execute("SELECT COUNT(*) FROM intelligence_approval_receipts").fetchone()[0])
            for table in ("runs", "snapshots"):
                self.assertEqual(0, conn.execute("SELECT COUNT(*) FROM " + table).fetchone()[0])

    def test_review_and_approval_denials_precede_context_lookup(self):
        context, _, receipt = self.approval_request()
        for principal in (None, Principal("foreign", "s", "org-b", "organization_owner"), Principal("viewer", "s", "org-a", "viewer")):
            for method, argument, payload in ((self.repo.save_intelligence_review, "overlay", self.review(context)), (self.repo.save_intelligence_approval, "receipt", receipt)):
                with self.subTest(principal=principal, argument=argument), patch.object(self.repo, "_intelligence_review_context") as lookup, self.assertRaises(PermissionError):
                    method(organization_id="org-a", project_id=self.project.project_id, principal=principal, **{argument: payload})
                lookup.assert_not_called()
        with self.repo.connect() as conn:
            self.assertEqual(1, conn.execute("SELECT COUNT(*) FROM intelligence_review_overlays").fetchone()[0])
            self.assertEqual(0, conn.execute("SELECT COUNT(*) FROM intelligence_approval_receipts").fetchone()[0])



    def test_ownership_denials_never_record_allowed_authorization(self):
        cases = ((self.principal, self.foreign.project_id), (self.principal, "missing-project"), (None, self.project.project_id), (Principal("viewer", "s", "org-a", "viewer"), self.project.project_id))
        for index, (principal, project_id) in enumerate(cases):
            correlation = "ownership-denial-" + str(index)
            with self.subTest(index=index), self.assertRaises(PermissionError):
                self.repo._authorize_intelligence(principal=principal, organization_id="org-a", project_id=project_id, permission="project.edit", action="aia.context.request", target_id="attempt-context", correlation_id=correlation)
            events = [event for event in self.repo.security_audit_events() if event["correlation_id"] == correlation]
            self.assertEqual(1, len(events))
            self.assertEqual("denied", events[0]["result"])
            self.assertEqual("attempt-context", events[0]["target_id"])
        self.repo._authorize_intelligence(principal=self.principal, organization_id="org-a", project_id=self.project.project_id, permission="project.edit", action="aia.context.request", target_id="attempt-context", correlation_id="owned-allowed")
        events = [event for event in self.repo.security_audit_events() if event["correlation_id"] == "owned-allowed"]
        self.assertEqual(1, len(events))
        self.assertEqual(("u", "org-a", "allowed"), tuple(events[0][key] for key in ("actor_user_id", "organization_id", "result")))

    def test_context_creation_audit_links_actual_insert_and_replay_ids(self):
        records = []
        for correlation in ("draft-insert", "draft-replay"):
            records.append(self.repo.create_intelligence_context(payload={"project_id": self.project.project_id, "idempotency_key": "audit-draft"}, principal=self.principal, correlation_id=correlation))
        context = self.model("audit-native")
        for correlation in ("native-insert", "native-replay"):
            records.append(self.repo.persist_validated_intelligence_context(context=context, principal=self.principal, correlation_id=correlation))
        self.assertEqual(records[0], records[1])
        self.assertEqual(records[2], records[3])
        events = self.repo.security_audit_events()
        for record, correlation in zip(records, ("draft-insert", "draft-replay", "native-insert", "native-replay")):
            with self.subTest(correlation=correlation):
                matching = [event for event in events if event["action"] == "aia.context.create" and event["correlation_id"] == correlation]
                self.assertEqual(1, len(matching))
                self.assertEqual(("u", "org-a", "allowed", record["context_build_id"]), tuple(matching[0][key] for key in ("actor_user_id", "organization_id", "result", "target_id")))
        with self.repo.connect() as conn:
            self.assertEqual(2, conn.execute("SELECT COUNT(*) FROM intelligence_contexts").fetchone()[0])

    def test_update_authorization_audit_targets_context_before_transaction(self):
        draft = self.draft("audit-update")
        seen = []
        def audit(**event):
            if event["action"] == "aia.context.update":
                seen.append(event)
                # Authorization must precede the mutation.
                with self.repo.connect() as conn:
                    self.assertEqual(1, conn.execute("SELECT version FROM intelligence_contexts WHERE context_build_id = ?", (draft["context_build_id"],)).fetchone()[0])
            return original_audit(**event)
        original_audit = self.repo.audit
        with patch.object(self.repo, "audit", side_effect=audit):
            updated = self.repo.update_intelligence_context(context_build_id=draft["context_build_id"], organization_id="org-a", project_id=self.project.project_id, payload={}, expected_version=1, principal=self.principal, correlation_id="update-attempt")
        self.assertEqual(2, updated["version"])
        self.assertEqual(1, len(seen))
        self.assertEqual(("u", "org-a", "allowed", draft["context_build_id"], "update-attempt"), tuple(seen[0][key] for key in ("actor_user_id", "organization_id", "result", "target_id", "correlation_id")))

    def test_native_component_string_metadata_rejects_original_wrong_types(self):
        fields = ("component_id", "kind", "source", "freshness", "geography", "sector", "confidence", "review")
        for field in fields:
            for index, value in enumerate((123, True, ["wrong"], {"wrong": 1})):
                context = self.model("typed-" + field + "-" + str(index), component_fields={field: value})
                with self.subTest(field=field, value=value), patch.object(self.repo, "_insert_intelligence_context") as insert, self.assertRaisesRegex(ValueError, "^context_component_invalid$"):
                    self.repo.persist_validated_intelligence_context(context=context, principal=self.principal)
                insert.assert_not_called()
        valid = self.model("valid-metadata")
        saved = self.repo.persist_validated_intelligence_context(context=valid, principal=self.principal)
        self.assertEqual("official-reference", saved["component_manifest"][0]["source"])
        with self.repo.connect() as conn:
            self.assertEqual(1, conn.execute("SELECT COUNT(*) FROM intelligence_contexts").fetchone()[0])
            for table in ("intelligence_review_overlays", "intelligence_approval_receipts", "runs", "snapshots"):
                self.assertEqual(0, conn.execute("SELECT COUNT(*) FROM " + table).fetchone()[0])


    def test_project_id_normalization_precedes_ownership_storage_and_replay(self):
        """The public repository and HTTP boundary use the same saved ID."""
        project_id = self.project.project_id
        created = self.repo.create_intelligence_context(payload={"project_id": " \t" + project_id + "\n ", "idempotency_key": "normalized"}, principal=self.principal)
        replay = self.repo.create_intelligence_context(payload={"project_id": project_id, "idempotency_key": "normalized"}, principal=self.principal)
        self.assertEqual(project_id, created["project_id"])
        self.assertEqual(created, replay)
        for invalid in (self.foreign.project_id, "missing-project", ""):
            with self.subTest(invalid=invalid), patch.object(self.repo, "_insert_intelligence_context") as insert, self.assertRaises(PermissionError):
                self.repo.create_intelligence_context(payload={"project_id": " \t" + invalid + "\n ", "idempotency_key": "normalized"}, principal=self.principal)
            insert.assert_not_called()
        # Normalize the lookup, not the original payload validation or key.
        for payload in ({"project_id": " " * 257 + project_id, "idempotency_key": "oversized"}, {"project_id": project_id, "idempotency_key": "extra", "trusted": True}):
            with self.subTest(payload=payload), patch.object(self.repo, "_insert_intelligence_context") as insert, self.assertRaisesRegex(ValueError, "^invalid_context_request$"):
                self.repo.create_intelligence_context(payload=payload, principal=self.principal)
            insert.assert_not_called()
        with self.repo.connect() as conn:
            self.assertEqual(1, conn.execute("SELECT COUNT(*) FROM intelligence_contexts").fetchone()[0])

    def test_identity_claim_denials_are_audited_before_lookup_without_raw_claims(self):
        context, _, receipt = self.approval_request()
        marker = "SECRET_FORGED_IDENTITY_MARKER"
        cases = (
            (self.repo.save_intelligence_review, "overlay", self.review(context), "reviewer_id", "aia.review.save", "reviewer_identity_mismatch"),
            (self.repo.save_intelligence_review, "overlay", self.review(context), "reviewer_role", "aia.review.save", "reviewer_identity_mismatch"),
            (self.repo.save_intelligence_approval, "receipt", receipt, "organization_id", "aia.approval.save", "receipt_organization_mismatch"),
            (self.repo.save_intelligence_approval, "receipt", receipt, "project_id", "aia.approval.save", "receipt_project_mismatch"),
        )
        for method, argument, payload, field, action, reason in cases:
            correlation = "identity-denial-" + field
            with self.subTest(field=field), patch.object(self.repo, "_intelligence_review_context") as lookup, self.assertRaisesRegex(PermissionError, "^intelligence_access_denied$"):
                method(organization_id="org-a", project_id=self.project.project_id, principal=self.principal, correlation_id=correlation, **{argument: payload | {field: marker}})
            lookup.assert_not_called()
            events = [event for event in self.repo.security_audit_events() if event["correlation_id"] == correlation and event["action"] == action]
            denied = [event for event in events if event["result"] == "denied"]
            allowed = [event for event in events if event["result"] == "allowed"]
            self.assertEqual(1, len(denied))
            self.assertEqual(1, len(allowed))
            self.assertEqual(("u", "org-a", "intelligence_context", reason), tuple(denied[0][key] for key in ("actor_user_id", "organization_id", "target_type", "reason")))
            self.assertTrue(denied[0]["target_id"])
            self.assertEqual(allowed[0]["target_id"], denied[0]["target_id"])
            self.assertNotEqual(context.context_build_id, denied[0]["target_id"])
            self.assertNotIn(marker, str(events))
        with self.repo.connect() as conn:
            counts = tuple(conn.execute("SELECT COUNT(*) FROM " + table).fetchone()[0] for table in ("intelligence_contexts", "intelligence_review_overlays", "intelligence_approval_receipts", "runs", "snapshots"))
        self.assertEqual((1, 1, 0, 0, 0), counts)

if __name__ == "__main__":
    unittest.main()

