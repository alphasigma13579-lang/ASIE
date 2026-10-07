import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
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

    def model(self, key="model", *, lineage=None):
        context = IntelligenceContext("ctx-" + key, "org-a", self.project.project_id, "SA", "retail", key, components=[ContextComponent("component", "reference", {"text": "Reviewed example"}, "official-reference", "today", "SA", "retail", "medium", ["evidence-reference"] if lineage is None else lineage, "PENDING")])
        return context.transition("VALIDATING").transition("INTEGRITY_LOCKED").transition("REVIEW_PENDING")

    def review(self, context, **overrides):
        return {"intelligence_context_id": context.context_build_id, "intelligence_context_hash": context.context_hash, "review_scope": "offline-example", "reviewed_output_hash": context.context_hash, "decision": "APPROVE", **overrides}

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


if __name__ == "__main__":
    unittest.main()
