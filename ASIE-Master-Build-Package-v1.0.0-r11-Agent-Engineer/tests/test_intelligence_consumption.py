import json
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from backend.identity import Principal
from backend.intelligence_context import ContextComponent, IntelligenceContext
from backend.repository import Repository


class IntelligenceConsumptionTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.repo = Repository(Path(directory.name) / "asie.db")
        with closing(self.repo.connect()) as db, db:
            db.execute("INSERT INTO organizations (organization_id,name,lifecycle_status,created_at,updated_at) VALUES ('o','O','active','now','now')")
            db.execute("INSERT INTO organizations (organization_id,name,lifecycle_status,created_at,updated_at) VALUES ('other','Other','active','now','now')")
        self.project = self.repo.create_project({"organization_id": "o", "name": "P", "sector": "retail", "jurisdiction": "SA"})
        self.principal = Principal("u", "s", "o", "organization_owner")
        self.context = IntelligenceContext("native-context", "o", self.project.project_id, "SA", "retail", "native-key", components=[ContextComponent("component", "reference", {"text": "Offline evidence"}, "reference", "today", "SA", "retail", "medium", ["evidence"], "PENDING")])
        self.context.transition("VALIDATING").transition("INTEGRITY_LOCKED").transition("REVIEW_PENDING")
        self.repo.persist_validated_intelligence_context(context=self.context, principal=self.principal)
        review = self.repo.save_intelligence_review(organization_id="o", project_id=self.project.project_id, principal=self.principal, overlay={"intelligence_context_id": self.context.context_build_id, "intelligence_context_hash": self.context.context_hash, "review_scope": "context", "reviewed_output_hash": self.context.context_hash, "decision": "APPROVE"})
        with patch("backend.repository.now_iso", return_value="2026-10-11T08:00:00+00:00"):
            self.receipt = self.repo.save_intelligence_approval(organization_id="o", project_id=self.project.project_id, principal=self.principal, receipt={"intelligence_context_id": self.context.context_build_id, "intelligence_context_hash": self.context.context_hash, "review_overlay_id": review["review_overlay_id"], "review_overlay_hash": review["review_overlay_hash"], "approval_scope": "run", "approved_for_contract_version": "context.v1", "valid_until": "2026-10-11T12:00:00+03:00"})

    def consume(self, **overrides):
        return self.repo.consume_intelligence_approval(**({"receipt_id": self.receipt["approval_receipt_id"], "organization_id": "o", "project_id": self.project.project_id, "context_hash": self.context.context_hash, "contract_version": "context.v1", "expected_scope": "run", "principal": self.principal} | overrides))

    def business_rows(self):
        with closing(self.repo.connect()) as db:
            return {table: [tuple(row) for row in db.execute("SELECT * FROM " + table)] for table in ("intelligence_contexts", "intelligence_review_overlays", "intelligence_approval_receipts", "runs", "snapshots")}

    def test_receipt_consumption_is_contract_scoped_and_non_snapshot(self):
        before = self.business_rows()
        with patch("backend.repository.now_iso", return_value="2026-10-11T08:30:00+00:00"):
            consumed = self.consume()
            self.assertTrue(consumed["consumable"])
            self.assertFalse(consumed["snapshot_mutation"])
            for overrides in ({"context_hash": "wrong"}, {"contract_version": "wrong"}, {"receipt_id": "missing"}):
                with self.subTest(overrides=overrides), self.assertRaises(ValueError):
                    self.consume(**overrides)
            for principal in (None, Principal("v", "s", "o", "viewer"), Principal("x", "s", "other", "organization_owner")):
                with self.subTest(principal=principal), self.assertRaises(PermissionError):
                    self.consume(principal=principal)
            second = self.repo.create_project({"organization_id": "o", "name": "Second"})
            with self.assertRaises(ValueError):
                self.consume(project_id=second.project_id)
        self.assertEqual(before, self.business_rows())

    def test_saved_valid_receipt_expires_at_consumption_without_sleep(self):
        before = self.business_rows()
        for now in ("2026-10-11T09:00:00+00:00", "2026-10-11T09:00:01+00:00", "2026-10-11T12:00:00+03:00"):
            with self.subTest(now=now), patch("backend.repository.now_iso", return_value=now), self.assertRaisesRegex(ValueError, "approval_expired"):
                self.consume()
        self.assertEqual(before, self.business_rows())

    def test_malformed_or_missing_expiry_fails_closed_without_mutation(self):
        for value in (None, 123, True, [], {}, "", "not-a-date", "2026-10-11T10:00:00"):
            for missing in (False, True) if value is None else (False,):
                material = self.receipt | {"valid_until": value}
                if missing:
                    material.pop("valid_until")
                with closing(self.repo.connect()) as db, db:
                    db.execute("UPDATE intelligence_approval_receipts SET payload_json = ? WHERE approval_receipt_id = ?", (json.dumps(material), self.receipt["approval_receipt_id"]))
                before = self.business_rows()
                with self.subTest(value=value, missing=missing), patch("backend.repository.now_iso", return_value="2026-10-11T08:30:00+00:00"), self.assertRaisesRegex(ValueError, "approval_expiry_invalid"):
                    self.consume()
                self.assertEqual(before, self.business_rows())

    def test_tampered_expiry_and_receipt_material_cannot_be_consumed(self):
        variants = ({"valid_until": "2099-01-01T00:00:00+00:00"}, {"approval_scope": "changed"}, {"conditions": ["changed"]}, {"organization_id": "other"}, {"project_id": "other"}, {"intelligence_context_id": "other"}, {"approval_receipt_id": "other"}, {"review_overlay_id": "other"}, {"approval_receipt_hash": "changed"})
        for variant in variants:
            material = self.receipt | variant
            with closing(self.repo.connect()) as db, db:
                db.execute("UPDATE intelligence_approval_receipts SET payload_json = ? WHERE approval_receipt_id = ?", (json.dumps(material), self.receipt["approval_receipt_id"]))
            before = self.business_rows()
            with self.subTest(variant=variant), patch("backend.repository.now_iso", return_value="2026-10-11T10:00:00+00:00" if "valid_until" in variant else "2026-10-11T08:30:00+00:00"), self.assertRaisesRegex(ValueError, "approval_integrity_invalid"):
                self.consume()
            self.assertEqual(before, self.business_rows())

    def test_receipt_row_hash_and_context_identity_are_checked(self):
        for column in ("receipt_hash", "context_build_id", "created_at"):
            with closing(self.repo.connect()) as db, db:
                db.execute("UPDATE intelligence_approval_receipts SET " + column + " = ? WHERE approval_receipt_id = ?", ("changed", self.receipt["approval_receipt_id"]))
            with self.subTest(column=column), patch("backend.repository.now_iso", return_value="2026-10-11T08:30:00+00:00"), self.assertRaisesRegex(ValueError, "approval_integrity_invalid"):
                self.consume()
            original = {"receipt_hash": self.receipt["approval_receipt_hash"], "context_build_id": self.context.context_build_id, "created_at": self.receipt["created_at"]}[column]
            with closing(self.repo.connect()) as db, db:
                db.execute("UPDATE intelligence_approval_receipts SET " + column + " = ? WHERE approval_receipt_id = ?", (original, self.receipt["approval_receipt_id"]))

    def test_non_object_and_malformed_receipts_are_integrity_errors(self):
        for raw in ("[]", "null", "true", "123", '"receipt"', "{broken"):
            with closing(self.repo.connect()) as db, db:
                db.execute("UPDATE intelligence_approval_receipts SET payload_json = ? WHERE approval_receipt_id = ?", (raw, self.receipt["approval_receipt_id"]))
            before = self.business_rows()
            with self.subTest(raw=raw), self.assertRaisesRegex(ValueError, "^approval_integrity_invalid$"):
                self.consume()
            self.assertEqual(before, self.business_rows())

    def test_receipts_for_other_scope_or_unresolved_conditions_are_not_consumable(self):
        for approval_scope, conditions in (("other-operation", []), ("run", ["manual prerequisite not satisfied"])):
            review = self.repo.save_intelligence_review(organization_id="o", project_id=self.project.project_id, principal=self.principal, overlay={"intelligence_context_id": self.context.context_build_id, "intelligence_context_hash": self.context.context_hash, "review_scope": "context", "reviewed_output_hash": self.context.context_hash, "decision": "APPROVE_WITH_CONDITIONS" if conditions else "APPROVE", "conditions": conditions})
            with patch("backend.repository.now_iso", return_value="2026-10-11T08:00:00+00:00"):
                receipt = self.repo.save_intelligence_approval(organization_id="o", project_id=self.project.project_id, principal=self.principal, receipt={"intelligence_context_id": self.context.context_build_id, "intelligence_context_hash": self.context.context_hash, "review_overlay_id": review["review_overlay_id"], "review_overlay_hash": review["review_overlay_hash"], "approval_scope": approval_scope, "approved_for_contract_version": "context.v1", "valid_until": "2026-10-11T09:00:00+00:00", "conditions": conditions})
            before = self.business_rows()
            with self.subTest(approval_scope=approval_scope, conditions=conditions), patch("backend.repository.now_iso", return_value="2026-10-11T08:30:00+00:00"), self.assertRaisesRegex(ValueError, "approval_scope_mismatch|approval_conditions_unverified"):
                self.consume(receipt_id=receipt["approval_receipt_id"])
            self.assertEqual(before, self.business_rows())

    def test_future_offset_expiry_remains_consumable(self):
        before = self.business_rows()
        with patch("backend.repository.now_iso", return_value="2026-10-11T08:59:59+00:00"):
            self.assertTrue(self.consume()["consumable"])
        self.assertEqual(before, self.business_rows())


if __name__ == "__main__":
    unittest.main()
