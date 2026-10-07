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

    def model(self, key="model"):
        context = IntelligenceContext("ctx-" + key, "org-a", self.project.project_id, "SA", "retail", key, components=[ContextComponent("component", "reference", {"text": "Reviewed example"}, "official-reference", "today", "SA", "retail", "medium", ["evidence-reference"], "PENDING")])
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


if __name__ == "__main__":
    unittest.main()
