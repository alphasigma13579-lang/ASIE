import tempfile
import unittest
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


if __name__ == "__main__": unittest.main()
