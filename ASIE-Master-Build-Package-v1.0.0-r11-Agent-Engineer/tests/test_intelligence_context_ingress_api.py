"""F01A providerless HTTP regressions; not a browser/T08 completion claim."""
from __future__ import annotations

import json
import sqlite3
import tempfile
import threading
import unittest
from contextlib import ExitStack
from datetime import datetime, timedelta, timezone
from http.client import HTTPConnection
from pathlib import Path
from unittest.mock import patch

import backend.asie_local_api as api
from backend.intelligence_workflow import IntelligenceContextWorkflow
from backend.intelligence_context import ContextComponent, IntelligenceContext
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

    def request(self, path, payload=None, *, token=None, org=None, method="POST", raw=None, content_length=None):
        headers = {"Content-Type": "application/json"}
        # An empty selection omits the tenant header; None keeps the fixture default.
        if org != "":
            headers["X-ASIE-Organization-Id"] = self.org if org is None else org
        if content_length is not None:
            headers["Content-Length"] = str(content_length)
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
                self.assertEqual(401 if token is None else 422, status)
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

    def test_malformed_review_and_approval_fields_are_safe_validation_errors(self):
        """Valid-context HTTP input errors return 400, never database 503."""
        principal = self.repo.principal_for_token(self.token, self.org)
        context = IntelligenceContext("ctx-http-reviewed", self.org, self.project.project_id, "SA", "Custom activity", "http-reviewed", components=[ContextComponent("evidence", "reference", {"summary": "Isolated ingress fixture"}, "official-reference", "today", "SA", "Custom activity", "medium", ["evidence-reference"])])
        context.transition("VALIDATING").transition("INTEGRITY_LOCKED").transition("REVIEW_PENDING")
        self.repo.persist_validated_intelligence_context(context=context, principal=principal)
        route = "/api/intelligence/contexts/" + context.context_build_id
        overlay = {"project_id": self.project.project_id, "intelligence_context_hash": context.context_hash, "review_scope": "offline-example", "reviewed_output_hash": context.context_hash, "decision": "APPROVE"}
        status, body = self.request(route + "/reviews", overlay, token=self.token)
        self.assertEqual(201, status)
        review = body["review"]
        receipt = {"project_id": self.project.project_id, "intelligence_context_hash": context.context_hash, "review_overlay_id": review["review_overlay_id"], "review_overlay_hash": review["review_overlay_hash"], "approval_scope": "offline-example", "approved_for_contract_version": "offline.example.v1", "valid_until": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()}
        marker = "SECRET_INVALID_APPROVAL_MARKER"
        cases = (
            ("reviews", overlay | {"reason": [marker]}),
            ("reviews", overlay | {"review_overlay_id": review["review_overlay_id"]}),
            ("reviews", overlay | {"review_overlay_id": "unknown-client-id"}),
            ("approval", receipt | {"review_overlay_id": [marker]}),
            ("approval", receipt | {"approval_receipt_id": "client-receipt-id"}),
        )
        for locale in ("ar", "en"):
            self.repo.save_customer_locale(self.owner["user_id"], locale)
            for suffix, payload in cases:
                with self.subTest(locale=locale, suffix=suffix, payload=payload):
                    status, body = self.request(route + "/" + suffix, payload, token=self.token)
                    self.assertEqual(400, status)
                    self.assertNotIn(marker, json.dumps(body))
                    self.assertEqual(locale == "ar", any("\u0600" <= ch <= "\u06ff" for ch in body["error"]))
        self.assertEqual((1, 1, 0, 0, 0), self.counts())

    def ingress_routes(self):
        project_query = "?project_id=" + self.project.project_id
        return (
            ("GET", "/api/intelligence/contexts/unknown" + project_query),
            ("POST", "/api/intelligence/contexts"),
            ("POST", "/api/intelligence/pre-runs"),
            ("POST", "/api/intelligence/contexts/unknown/reviews"),
            ("POST", "/api/intelligence/contexts/unknown/approval"),
        )

    def test_missing_invalid_expired_and_revoked_sessions_preserve_401(self):
        self.repo.save_customer_locale(self.owner["user_id"], "en")
        expired_token, _ = self.repo.create_session(email=self.owner["email"], password="ingress-password")
        expired_principal = self.repo.principal_for_token(expired_token)
        with self.repo.connect() as conn:
            conn.execute("UPDATE sessions SET expires_at = ? WHERE session_id = ?", ((datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(), expired_principal.session_id))
            conn.commit()
        revoked_token, _ = self.repo.create_session(email=self.owner["email"], password="ingress-password")
        self.assertTrue(self.repo.revoke_session(revoked_token))
        with ExitStack() as stack:
            spies = [stack.enter_context(patch.object(self.repo, name, side_effect=AssertionError("data access must not start"))) for name in ("get_intelligence_context", "create_intelligence_context", "save_intelligence_review", "save_intelligence_approval")]
            read_body = stack.enter_context(patch.object(api, "read_json", side_effect=AssertionError("body must not be read")))
            for token in (None, "invalid-test-session", expired_token, revoked_token):
                for method, route in self.ingress_routes():
                    with self.subTest(session=token is not None, method=method, route=route):
                        status, body = self.request(route, {"project_id": self.project.project_id, "locale": "en"}, token=token, method=method)
                        self.assertEqual(401, status)
                        self.assertEqual(401, body["status"])
                        # Invalid sessions cannot select the account's saved English locale.
                        self.assertTrue(any("\u0600" <= ch <= "\u06ff" for ch in body["error"]))
                        self.assertNotIn(self.project.project_id, json.dumps(body))
            read_body.assert_not_called()
            for spy in spies:
                spy.assert_not_called()
        self.assertEqual((0, 0, 0, 0, 0), self.counts())

    def test_tenant_denial_preserves_authenticated_account_locale_without_access(self):
        with ExitStack() as stack:
            spies = [stack.enter_context(patch.object(self.repo, name, side_effect=AssertionError("tenant data access must not start"))) for name in ("get_intelligence_context", "create_intelligence_context", "save_intelligence_review", "save_intelligence_approval")]
            read_body = stack.enter_context(patch.object(api, "read_json", side_effect=AssertionError("body must not be read")))
            for locale in ("ar", "en"):
                self.repo.save_customer_locale(self.owner["user_id"], locale)
                for organization in ("", self.foreign_org):
                    for method, route in self.ingress_routes():
                        with self.subTest(locale=locale, organization=organization, method=method, route=route):
                            status, body = self.request(route, {"project_id": self.project.project_id, "locale": "en" if locale == "ar" else "ar"}, token=self.token, org=organization, method=method)
                            self.assertEqual(403 if method == "GET" else 422, status)
                            self.assertEqual(status, body["status"])
                            self.assertEqual(locale == "ar", any("\u0600" <= ch <= "\u06ff" for ch in body["error"]))
                            self.assertNotIn(self.foreign_org, json.dumps(body))
                            self.assertNotIn(self.foreign.project_id, json.dumps(body))
                            self.assertNotIn(self.project.project_id, json.dumps(body))
            read_body.assert_not_called()
            for spy in spies:
                spy.assert_not_called()
        self.assertEqual((0, 0, 0, 0, 0), self.counts())

    def test_oversized_request_preserves_413_and_safe_account_language(self):
        marker = "SECRET_OVERSIZED_BODY_MARKER"
        with ExitStack() as stack:
            spies = [stack.enter_context(patch.object(self.repo, name, side_effect=AssertionError("write must not start"))) for name in ("create_intelligence_context", "save_intelligence_review", "save_intelligence_approval")]
            for locale in ("ar", "en"):
                self.repo.save_customer_locale(self.owner["user_id"], locale)
                for method, route in self.ingress_routes():
                    if method == "GET":
                        continue
                    with self.subTest(locale=locale, route=route):
                        # Exercise the real length guard without sending a large body.
                        status, body = self.request(route, token=self.token, raw=marker, content_length=api.MAX_JSON_BODY_BYTES + 1)
                        self.assertEqual(413, status)
                        self.assertEqual(413, body["status"])
                        self.assertEqual(locale == "ar", any("\u0600" <= ch <= "\u06ff" for ch in body["error"]))
                        self.assertNotIn(marker, json.dumps(body))
                        self.assertNotIn("request_body_too_large", json.dumps(body))
            for spy in spies:
                spy.assert_not_called()
        self.assertEqual((0, 0, 0, 0, 0), self.counts())


if __name__ == "__main__":
    unittest.main()
