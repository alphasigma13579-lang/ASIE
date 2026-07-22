import tempfile
import unittest
from pathlib import Path

from backend.identity import Principal
from backend.repository import Repository


class IntelligenceConsumptionTests(unittest.TestCase):
    def test_receipt_consumption_is_contract_scoped_and_non_snapshot(self):
        with tempfile.TemporaryDirectory() as folder:
            repo = Repository(Path(folder) / "asie.db")
            db = repo.connect()
            try:
                db.execute("INSERT INTO organizations (organization_id,name,lifecycle_status,created_at,updated_at) VALUES ('o','O','active','now','now')")
                db.commit()
            finally: db.close()
            project = repo.create_project({"organization_id": "o", "name": "P"})
            principal = Principal("u", "s", "o", "organization_owner")
            db = repo.connect()
            try:
                db.execute("INSERT INTO intelligence_approval_receipts VALUES ('r','o',?,'c','rh',?, 'now')", (project.project_id, '{"intelligence_context_hash":"ch","approved_for_contract_version":"context.v1"}'))
                db.commit()
            finally: db.close()
            consumed = repo.consume_intelligence_approval(receipt_id="r", organization_id="o", project_id=project.project_id, context_hash="ch", contract_version="context.v1", principal=principal)
            self.assertTrue(consumed["consumable"])
            self.assertFalse(consumed["snapshot_mutation"])


if __name__ == "__main__": unittest.main()
