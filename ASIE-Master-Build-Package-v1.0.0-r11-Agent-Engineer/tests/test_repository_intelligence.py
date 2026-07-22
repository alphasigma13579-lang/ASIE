import tempfile
import unittest
from pathlib import Path

from backend.identity import Principal
from backend.repository import Repository


class RepositoryIntelligenceTests(unittest.TestCase):
    def test_official_repository_enforces_tenant_and_optimistic_version(self):
        with tempfile.TemporaryDirectory() as folder:
            repo = Repository(Path(folder) / "asie.db")
            db = repo.connect()
            try:
                db.execute("INSERT INTO organizations (organization_id, name, lifecycle_status, created_at, updated_at) VALUES ('org-a','A','active','now','now')")
                db.commit()
            finally:
                db.close()
            project = repo.create_project({"organization_id": "org-a", "name": "P", "sector": "retail", "jurisdiction": "SA"})
            self.assertEqual("org-a", project.organization_id)
            principal = Principal("u", "s", "org-a", "organization_owner")
            created = repo.create_intelligence_context(payload={"organization_id": "org-a", "project_id": project.project_id, "idempotency_key": "k", "component_manifest": []}, principal=principal)
            self.assertEqual(1, created["version"])
            self.assertIsNotNone(repo.get_intelligence_context(context_build_id=created["context_build_id"], organization_id="org-a", project_id=project.project_id, principal=principal))
            with self.assertRaises(PermissionError):
                repo.get_intelligence_context(context_build_id=created["context_build_id"], organization_id="org-b", project_id=project.project_id, principal=principal)
            with self.assertRaises(RuntimeError):
                repo.update_intelligence_context(context_build_id=created["context_build_id"], organization_id="org-a", project_id=project.project_id, payload={}, expected_version=99, principal=principal)
            with self.assertRaises(ValueError):
                repo.save_intelligence_review(organization_id="org-a", project_id=project.project_id, overlay={"intelligence_context_id": created["context_build_id"], "intelligence_context_hash": "wrong"}, principal=principal)


if __name__ == "__main__": unittest.main()
