"""F01A providerless HTTP regressions; not a browser/T08 completion claim."""
from __future__ import annotations

import json
import sqlite3
import tempfile
import threading
import unittest
from contextlib import ExitStack
from http.client import HTTPConnection
from pathlib import Path
from unittest.mock import patch

import backend.asie_local_api as api
from backend.intelligence_workflow import IntelligenceContextWorkflow
from backend.repository import Repository


class IntelligenceContextIngressApiTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.repo = Repository(Path(directory.name) / "ingress.sqlite3")
        self.owner = self.repo.create_user(email="ingress-owner@example.test", display_name="Owner", password="ingress-password")
        self.other = self.repo.create_user(email="ingress-other@example.test", display_name="Other", password="other-ingress-password")
        self.org = self.repo.create_organization(name="Ingress", owner_user_id=self.owner["user_id"])["organization_id"]
        self.foreign_org = self.repo.create_organization(name="Other", owner_user_id=self.other["user_id"])["organization_id"]
        self.project = self.repo.create_project({"organization_id": self.org, "name": "Custom project", "sector": "Custom activity", "jurisdiction": "SA", "inputs": {"primary_sector_id": "CUSTOM", "location_country": "SA"}})
        self.foreign = self.repo.create_project({"organization_id": self.foreign_org, "name": "Foreign", "sector": "retail", "jurisdiction": "SA"})
        self.same_org_project = self.repo.create_project({"organization_id": self.org, "name": "Second", "sector": "retail", "jurisdiction": "SA"})
        self.token, _ = self.repo.create_session(email=self.owner["email"], password="ingress-password")
        self.other_token, _ = self.repo.create_session(email=self.other["email"], password="other-ingress-password")
        self.repo.add_membership(organization_id=self.org, user_id=self.other["user_id"], role="viewer", actor_user_id=self.owner["user_id"])
        self.addCleanup(setattr, api, "REPO", api.REPO)
        api.REPO = self.repo
        server = api.ThreadingHTTPServer(("127.0.0.1", 0), api.Handler)
        self.server = server
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)

    def request(self, path, payload=None, *, token=None, org=None, method="POST", raw=None):
        headers = {"Content-Type": "application/json", "X-ASIE-Organization-Id": org or self.org}
        if token:
            headers["Authorization"] = "Bearer " + token
        body = raw if raw is not None else json.dumps(payload or {})
        conn = HTTPConnection("127.0.0.1", self.server.server_address[1], timeout=5)
        try:
            conn.request(method, path, body=None if method == "GET" else body, headers=headers)
            response = conn.getresponse()
            return response.status, json.loads(response.read())
        finally:
            conn.close()

    def counts(self):
        with self.repo.connect() as conn:
            return tuple(conn.execute("SELECT COUNT(*) FROM " + name).fetchone()[0] for name in ("intelligence_contexts", "intelligence_review_overlays", "intelligence_approval_receipts", "runs", "snapshots"))

    def test_minimal_request_creates_only_server_owned_draft_and_replays_it(self):
        payload = {"project_id": self.project.project_id, "idempotency_key": "minimal"}
        status, body = self.request("/api/intelligence/contexts", payload, token=self.token)
        self.assertEqual(201, status)
        record = body["context"]
        self.assertEqual(("DRAFT", "", 1, "SA", "Custom activity"), (record["state"], record["context_hash"], record["version"], record["geography"], record["sector"]))
        status, replay = self.request("/api/intelligence/contexts", payload, token=self.token)
        self.assertEqual(201, status)
        self.assertEqual(record, replay["context"])
        status, read = self.request("/api/intelligence/contexts/" + record["context_build_id"] + "?project_id=" + self.project.project_id, token=self.token, method="GET")
        self.assertEqual(200, status)
        self.assertEqual("", read["context"]["context_hash"])
        self.assertEqual((1, 0, 0, 0, 0), self.counts())

    def test_state_hash_and_extra_claims_are_rejected_including_blank_and_nested(self):
        for field, value in (("state", "APPROVED_FOR_RUN"), ("context_hash", "f" * 64), ("version", 4), ("geography", ""), ("sector", ""), ("components", []), ("component_manifest", []), ("approval", {"reviewer_id": "forged"}), ("organization_id", self.org), ("trusted", True), ("internal", True), ("context_build_id", "forged")):
            with self.subTest(field=field):
                status, _ = self.request("/api/intelligence/contexts", {"project_id": self.project.project_id, "idempotency_key": "forged-" + field, field: value}, token=self.token)
                self.assertEqual(400, status)
        self.assertEqual((0, 0, 0, 0, 0), self.counts())

    def test_session_role_and_selected_tenant_are_checked_before_creation(self):
        for token, org, project in ((None, self.org, self.project), (self.other_token, self.org, self.project), (self.token, self.foreign_org, self.foreign), (self.token, self.org, self.foreign)):
            with self.subTest(token=bool(token), org=org):
                with patch.object(self.repo, "create_intelligence_context", side_effect=AssertionError("write must not start")) as write:
                    status, body = self.request("/api/intelligence/contexts", {"project_id": project.project_id, "idempotency_key": "denied"}, token=token, org=org)
                self.assertEqual(422, status)
                write.assert_not_called()
                self.assertNotIn(self.foreign.project_id, json.dumps(body))
        self.assertEqual((0, 0, 0, 0, 0), self.counts())

    def test_raw_pre_run_never_constructs_service_workflow_or_execution(self):
        raw = {"project_id": self.project.project_id, "context_build_id": "raw", "idempotency_key": "raw", "geography": "SA", "sector": "Custom activity", "components": []}
        with ExitStack() as stack:
            spies = [stack.enter_context(patch.object(api, name)) for name in ("IntelligencePreRunService", "GoogleLocationClient", "DeepSeekNarrativeClient", "PineconeKnowledgeClient", "TavilyResearchClient", "AASKernel", "HeartController", "ModuleRuntime", "RunScopedModuleRuntime")]
            workflow = stack.enter_context(patch.object(IntelligenceContextWorkflow, "execute", return_value=None))
            # A harmless baseline stub prevents any raw builder from executing;
            # on vulnerable code the constructor invocation is still detected.
            spies[0].return_value.build_local_context.return_value = {"error": "baseline-stub"}
            for payload in (raw, {"project_id": self.project.project_id}, {}):
                status, _ = self.request("/api/intelligence/pre-runs", payload, token=self.token)
                self.assertIn(status, (400, 409))
            status, _ = self.request("/api/intelligence/pre-runs", token=self.token, raw="{bad json")
            self.assertEqual(400, status)
            for spy in spies:
                spy.assert_not_called()
            workflow.assert_not_called()
        self.assertEqual((0, 0, 0, 0, 0), self.counts())

    def test_draft_review_and_approval_cannot_create_any_receipt(self):
        _, body = self.request("/api/intelligence/contexts", {"project_id": self.project.project_id, "idempotency_key": "draft"}, token=self.token)
        context_id = body["context"]["context_build_id"]
        for suffix in ("reviews", "approval"):
            status, _ = self.request("/api/intelligence/contexts/" + context_id + "/" + suffix, {"project_id": self.project.project_id, "intelligence_context_hash": ""}, token=self.token)
            self.assertEqual(400, status)
        # A context belonging to another project of the same tenant is not found.
        status, _ = self.request("/api/intelligence/contexts/" + context_id + "/reviews", {"project_id": self.same_org_project.project_id, "intelligence_context_hash": ""}, token=self.token)
        self.assertEqual(400, status)
        self.assertEqual((1, 0, 0, 0, 0), self.counts())

    def test_raw_payload_cannot_override_server_locale_or_expose_failure(self):
        marker = "SECRET_INGRESS_TEST_MARKER"
        for locale in ("ar", "en"):
            self.repo.save_customer_locale(self.owner["user_id"], locale)
            status, body = self.request("/api/intelligence/pre-runs", {"project_id": self.project.project_id, "locale": "en" if locale == "ar" else "ar", "components": [{"source": marker}]}, token=self.token)
            self.assertEqual(409, status)
            message = body["error"]
            self.assertEqual(locale == "ar", any("\u0600" <= ch <= "\u06ff" for ch in message))
            self.assertNotIn(marker, json.dumps(body))
            self.assertNotIn("context_hash", message)
            self.assertNotIn("REVIEW_PENDING", message)
            with patch.object(self.repo, "create_intelligence_context", side_effect=RuntimeError(marker)):
                status, body = self.request("/api/intelligence/contexts", {"project_id": self.project.project_id, "idempotency_key": "failure"}, token=self.token)
            self.assertEqual(503, status)
            self.assertNotIn(marker, json.dumps(body))
            self.assertEqual(locale == "ar", any("\u0600" <= ch <= "\u06ff" for ch in body["error"]))
        # The schema already rejects invalid stored languages; do not weaken it
        # or write an impossible fixture to exercise the runtime fallback.
        with self.assertRaises(sqlite3.IntegrityError), self.repo.connect() as conn:
            conn.execute("UPDATE customer_preferences SET locale = 'invalid' WHERE user_id = ?", (self.owner["user_id"],))
        with patch.object(self.repo, "customer_locale", return_value="invalid"):
            status, body = self.request("/api/intelligence/pre-runs", {"project_id": self.project.project_id}, token=self.token)
        self.assertEqual(409, status)
        self.assertTrue(any("\u0600" <= ch <= "\u06ff" for ch in body["error"]))
        with self.repo.connect() as conn:
            conn.execute("DELETE FROM customer_preferences WHERE user_id = ?", (self.owner["user_id"],))
            conn.commit()
        status, body = self.request("/api/intelligence/pre-runs", {"project_id": self.project.project_id}, token=self.token)
        self.assertEqual(409, status)
        self.assertTrue(any("\u0600" <= ch <= "\u06ff" for ch in body["error"]))
        self.assertNotIn(marker, json.dumps(self.repo.security_audit_events(), ensure_ascii=False))


if __name__ == "__main__":
    unittest.main()
