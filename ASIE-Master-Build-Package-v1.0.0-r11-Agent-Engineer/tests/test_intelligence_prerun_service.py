import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from pathlib import Path

from backend.identity import Principal
from backend.intelligence_prerun_service import IntelligencePreRunService
from backend.repository import Repository


class IntelligencePreRunServiceTests(unittest.TestCase):
    def test_local_context_is_persisted_for_review_only(self):
        with tempfile.TemporaryDirectory() as folder:
            repo = Repository(Path(folder) / "asie.db")
            db = repo.connect()
            try:
                db.execute("INSERT INTO organizations (organization_id,name,lifecycle_status,created_at,updated_at) VALUES ('o','O','active','now','now')")
                db.commit()
            finally: db.close()
            project = repo.create_project({"organization_id": "o", "name": "P", "sector": "retail", "jurisdiction": "SA"})
            component = {"component_id": "c", "kind": "reference", "value": {"x": 1}, "source": "VISION_2030_REFERENCE", "freshness": "today", "geography": "SA", "sector": "retail", "confidence": "medium", "lineage": ["brief"], "review": "PENDING"}
            result = IntelligencePreRunService(repo).build_local_context(organization_id="o", project_id=project.project_id, context_build_id="ctx", idempotency_key="idem", geography="SA", sector="retail", components=[component], principal=Principal("u", "s", "o", "organization_owner"))
            self.assertEqual("REVIEW_PENDING", result["context"]["state"])
            self.assertFalse(result["snapshot_mutation"])


    def test_authorization_precedes_model_and_cache(self):
        with tempfile.TemporaryDirectory() as folder:
            repo = Repository(Path(folder) / "asie.db")
            with patch.object(repo, "_validated_intelligence_model") as validate:
                workflow = SimpleNamespace(execute=lambda **_: self.fail("cache must not be read"))
                service = IntelligencePreRunService(repo, workflow=workflow)
                with self.assertRaises(PermissionError):
                    service.build_local_context(organization_id="foreign", project_id="missing", context_build_id="ctx", idempotency_key="key", geography="SA", sector="retail", components=[], principal=None)
            validate.assert_not_called()

    def test_workflow_failure_is_not_returned_as_raw_exception_or_audit(self):
        with tempfile.TemporaryDirectory() as folder:
            repo = Repository(Path(folder) / "asie.db")
            with repo.connect() as conn:
                conn.execute("INSERT INTO organizations (organization_id,name,lifecycle_status,created_at,updated_at) VALUES ('o','O','active','now','now')")
                conn.commit()
            project = repo.create_project({"organization_id": "o", "name": "P", "sector": "retail", "jurisdiction": "SA"})
            marker = "SECRET_LOCAL_WORKFLOW_MARKER"
            workflow = SimpleNamespace(execute=lambda **_: SimpleNamespace(state="FAILED", error=marker, audit=[{"reason": marker}]))
            component = {"component_id": "c", "kind": "reference", "value": {}, "source": "official-reference", "freshness": "today", "geography": "SA", "sector": "retail", "confidence": "medium", "lineage": ["reference"], "review": "PENDING"}
            result = IntelligencePreRunService(repo, workflow=workflow).build_local_context(organization_id="o", project_id=project.project_id, context_build_id="ctx", idempotency_key="idem", geography="SA", sector="retail", components=[component], principal=Principal("u", "s", "o", "organization_owner"))
            self.assertEqual("local_context_unavailable", result["error"])
            self.assertNotIn(marker, repr(result))
            with repo.connect() as conn:
                self.assertEqual(0, conn.execute("SELECT COUNT(*) FROM intelligence_contexts").fetchone()[0])


    def test_same_key_cannot_replay_workflow_across_projects_or_after_denial(self):
        with tempfile.TemporaryDirectory() as folder:
            repo = Repository(Path(folder) / "asie.db")
            with repo.connect() as conn:
                conn.execute("INSERT INTO organizations (organization_id,name,lifecycle_status,created_at,updated_at) VALUES ('o','O','active','now','now')")
                conn.commit()
            projects = [repo.create_project({"organization_id": "o", "name": name, "sector": "retail", "jurisdiction": "SA"}) for name in ("First", "Second")]
            principal = Principal("u", "s", "o", "organization_owner")
            service = IntelligencePreRunService(repo)
            component = {"component_id": "c", "kind": "reference", "value": {}, "source": "official-reference", "freshness": "today", "geography": "SA", "sector": "retail", "confidence": "medium", "lineage": ["reference"], "review": "PENDING"}
            records = []
            for index, project in enumerate(projects):
                result = service.build_local_context(organization_id="o", project_id=project.project_id, context_build_id="ctx-" + str(index), idempotency_key="shared-key", geography="SA", sector="retail", components=[component], principal=principal)
                records.append(result["context"])
            self.assertNotEqual(records[0]["context_hash"], records[1]["context_hash"])
            self.assertEqual([project.project_id for project in projects], [record["project_id"] for record in records])
            with patch.object(service.workflow, "execute", side_effect=AssertionError("unauthorized replay")) as execute:
                with self.assertRaises(PermissionError):
                    service.build_local_context(organization_id="o", project_id=projects[0].project_id, context_build_id="ctx-0", idempotency_key="shared-key", geography="SA", sector="retail", components=[component], principal=None)
            execute.assert_not_called()


if __name__ == "__main__": unittest.main()
