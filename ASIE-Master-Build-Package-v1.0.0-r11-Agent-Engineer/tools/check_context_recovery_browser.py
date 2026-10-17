"""Customer recovery acceptance in the real App with disposable synthetic HTTP owners.

All non-loopback traffic is denied. No provider, live database, or account is used.
The existing App fixture imports production components; this is not another UI.
"""
from contextlib import contextmanager
import copy
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
import unittest
from urllib.parse import urlsplit, parse_qs
from urllib.request import urlopen
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "http://127.0.0.1:5195"
FIXTURE = ORIGIN + "/tools/browser/app-session.html"
ARTIFACTS = Path(os.environ.get("ASIE_RECOVERY_ARTIFACTS", "/tmp/asie-recovery-browser"))


def project_fixture():
    return {"project_id": "synthetic-project-a", "organization_id": "synthetic-org-a", "name": "", "sector": "Services", "jurisdiction": "SA", "depth_profile": "starter", "created_at": "2026-10-14T00:00:00Z", "updated_at": "version-one", "inputs": {"startup_cost": 100, "unit_price": 20, "variable_cost": 10, "monthly_units": 100, "monthly_fixed_cost": 10}}


def requirement(project):
    return {"recovery_id": "synthetic-requirement-name", "requirement_code": "MISSING_PROJECT_NAME", "reason_key": "missing_project_name", "required": True, "severity": "required", "source": {"kind": "project_draft", "organization_id": project["organization_id"], "project_id": project["project_id"], "entity_id": project["project_id"], "updated_at": project["updated_at"]}, "target": {"kind": "project_field", "field_keys": ["name"]}, "action": {"required_permission": "project.edit", "allowed": True, "responsible_role": "project_editor"}, "resolution": "unresolved"}


class CustomerRecoveryBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pw = sync_playwright().start()
        cls.addClassCleanup(cls.pw.stop)
        executable = os.environ.get("ASIE_TEST_CHROMIUM")
        cls.browser = cls.pw.chromium.launch(**({"executable_path": executable} if executable else {}))
        cls.addClassCleanup(cls.browser.close)
        ARTIFACTS.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def app(self, locale="ar", mobile=False, storage_failure=False, evidence=False, source_review=False, administrator=False, dataset_proof=False, customer_classification=False, two_projects=False):
        context = self.browser.new_context(viewport={"width": 390 if mobile else 1280, "height": 900}, locale=locale, service_workers="block")
        state = {"project": project_fixture(), "requests": [], "blocked": [], "errors": [], "fail_save": False, "dib_conflict": False, "dib_value": None, "dib_revision": 1, "fail_next_dib_read": False, "fail_read_after_save": False, "expire_dib": False, "defer_dib": False, "pending_dib": [], "source_revision": 1}
        state["datasets"] = [{"dataset_id": "synthetic-dataset", "organization_id": "synthetic-org-a", "source_id": "source", "title": "", "publisher": "Synthetic publisher", "updated_at": "dataset-v1", "columns": [], "preview": [], "notes": {}, "row_count": 0, "review_status": "draft"}] if evidence else []
        state["sources"] = [{"source_id": "synthetic-source", "publisher": "Synthetic source", "route": "official_open_dataset_or_api", "state": "candidate", "url": "https://example.invalid/source", "terms_url": "https://example.invalid/terms", "terms_hash": "PRIVATE-SOURCE-TERMS", "license_snapshot_ref": "PRIVATE-LICENSE-REFERENCE", "classification": "public", "pdpl_check": "Synthetic reviewed", "nca_check": "Synthetic reviewed", "lawful_purpose": "Synthetic research", "attribution": "Synthetic source", "reviewer": "Synthetic reviewer", "reviewer_decision": "", "reviewed_at": "source-v1", "notes": {"organization_id": "synthetic-org-a", "project_id": "synthetic-project-a", "discovery_allowed": False, "discovery_sectors": ["services"], "discovery_geographies": ["SA"], "allowed_paths": ["/source"], "allow_query_parameters": False, "state_reason": "Synthetic preservation", "notes": "Synthetic note"}}] if source_review else []
        if dataset_proof:
            state["datasets"][0].update(terms_hash="PRIVATE-DATASET-TERMS", license_snapshot_ref="PRIVATE-DATASET-LICENSE")
        if customer_classification:
            state["datasets"][0]["source_id"] = ""
            state["datasets"][0]["notes"] = {"submission_provenance": {"version": 1, "kind": "customer_study", "organization_id": "synthetic-org-a", "creator_user_id": "synthetic-user", "initial_project_id": "synthetic-project-a", "created_at": "2026-10-15T00:00:00+00:00"}}
        def evidence_requirements(state=state):
            if dataset_proof or customer_classification:
                item = requirement(state["project"])
                fields = ["terms_hash", "license_snapshot_ref", "title"] if dataset_proof else ["classification"]
                return [item | {"recovery_id": "dataset-metadata", "requirement_code": "DATASET_METADATA_REQUIRED", "source": item["source"] | {"kind": "dataset", "entity_id": state["datasets"][0]["dataset_id"], "updated_at": state["datasets"][0]["updated_at"]}, "target": {"kind": "dataset_metadata", "dataset_id": "synthetic-dataset", "field_keys": fields}}]
            if source_review:
                if state["sources"][0]["state"] == "enabled": return []
                item = requirement(state["project"])
                return [item | {"recovery_id": "source-review", "requirement_code": "SOURCE_REVIEW_REQUIRED", "source": item["source"] | {"kind": "source_review", "entity_id": "synthetic-source", "version": state["sources"][0]["reviewed_at"]}, "target": {"kind": "source_review", "source_id": "synthetic-source"}, "action": {"required_permission": "platform.manage", "allowed": administrator, "responsible_role": "platform_administrator"}}]
            if not state["datasets"] or state["datasets"][0]["title"]: return []
            item = requirement(state["project"])
            return [item | {"recovery_id": "dataset-title", "requirement_code": "DATASET_METADATA_REQUIRED", "source": item["source"] | {"kind": "dataset", "entity_id": state["datasets"][0]["dataset_id"], "updated_at": state["datasets"][0]["updated_at"]}, "target": {"kind": "dataset_metadata", "dataset_id": state["datasets"][0]["dataset_id"], "field_keys": ["title"]}}]
        initial = '''localStorage.setItem("asie.product_entry.v1", "1"); localStorage.setItem("asie.legal_acceptance.v1", "1");
        sessionStorage.setItem("asie.session_token.v1", "synthetic-token"); sessionStorage.setItem("asie.active_organization.v1", "synthetic-org-a");
        sessionStorage.setItem("asie.recovery.last.v1:synthetic-user:synthetic-org-a", "synthetic-project-a");'''
        if storage_failure:
            initial += '''const originalSet=Storage.prototype.setItem; Storage.prototype.setItem=function(k,v){if(k.startsWith("asie.recovery.edit"))throw new DOMException("synthetic storage unavailable");return originalSet.call(this,k,v)};'''
        context.add_init_script(initial)
        def session(state=state):
            revision = state["dib_revision"]
            origin = {"session_id": state.get("session_id", "synthetic-dib-session"), "project_id": state["project"]["project_id"], "blueprint_id": f"private-blueprint-{revision}", "revision": revision, "payload_hash": f"PRIVATE-ORIGIN-HASH-{revision}"}
            item = {"item_id": "private-item", "input_key": "unit_price", "label": "INTERNAL-UNSAFE-LABEL", "value": state["dib_value"], "value_state": "UNKNOWN" if state["dib_value"] is None else "USER_PROVIDED", "required": True}
            recovery = {"recovery_id": "private-recovery", "requirement_code": "DIB_ITEM_VALUE_REQUIRED", "reason_key": "dib_item_value_required", "required": True, "severity": "required", "source": {"kind": "dib_blueprint", "organization_id": state["project"]["organization_id"], "project_id": state["project"]["project_id"], "entity_id": origin["blueprint_id"], "revision": revision, "payload_hash": origin["payload_hash"]}, "target": {"kind": "dib_item", "session_id": origin["session_id"], "blueprint_id": origin["blueprint_id"], "item_id": item["item_id"], "input_key": "unit_price", "field_keys": ["unit_price"]}, "action": {"required_permission": "dib.write", "allowed": True, "responsible_role": "project_editor"}, "resolution": "unresolved"}
            return {"session_id": origin["session_id"], "project_id": origin["project_id"], "status": "blueprint_saved", "project_profile": {}, "created_at": "2026-10-14T00:00:00Z", "origin_reference": origin, "current_blueprint": {"blueprint_id": origin["blueprint_id"], "project_id": origin["project_id"], "revision": revision, "contract_id": "dynamic.input.blueprint.v1", "items": [item]}, "recovery_items": [] if state["dib_value"] else [recovery], "approved_manifest": None, "validation_gate": None}
        owners = {state["project"]["project_id"]: state}
        if two_projects:
            state["project"]["name"] = "Synthetic project A"
            second = copy.deepcopy(state)
            second["project"].update(project_id="synthetic-project-b", name="Synthetic project B")
            second["session_id"] = "synthetic-dib-session-b"
            second["datasets"][0]["dataset_id"] = "synthetic-dataset-b"
            for key in ("requests", "blocked", "errors"): second[key] = state[key]
            owners["synthetic-project-b"] = second
        state["owners"] = owners
        def route_owned(route, state):
            register = {"datasets": state["datasets"], "transformations": [], "quality_gates": [], "source_records": state["sources"], "source_checklists": [], "evidence_links": state.get("evidence_links", []), "linked_dataset_ids": [], "not_ready_reasons": []}
            project_id = state["project"]["project_id"]
            session_id = state.get("session_id", "synthetic-dib-session")
            dataset_id = state["datasets"][0]["dataset_id"] if state["datasets"] else "synthetic-dataset"
            url = urlsplit(route.request.url)
            if url.scheme != "http" or url.netloc != "127.0.0.1:5195":
                state["blocked"].append(route.request.url); route.abort(); return
            if not url.path.startswith("/api"):
                route.continue_(); return
            path, method = url.path, route.request.method
            state["requests"].append((method, path, route.request.post_data_json if route.request.post_data else None))
            payload = {}
            if state["expire_dib"] and path.startswith("/api/dib/"):
                route.fulfill(status=401, json={"error": "authentication_required"}); return
            if path == "/api/auth/me": payload = {"user_id": "synthetic-user", "platform_role": "platform_admin" if administrator else None, "locale": locale, "memberships": [{"organization_id": "synthetic-org-a", "organization_name": "Synthetic organization", "role": "organization_owner"}, {"organization_id": "synthetic-org-b", "organization_name": "Other synthetic organization", "role": "organization_owner"}]}
            elif path == "/api/auth/preferences": payload = {"locale": locale}
            elif path == "/api/source-policy": payload = {"profile_id": "synthetic", "enabled_sources": [], "candidate_sources": [], "reference_only": [], "blocked_sources": [], "external_fetch_enabled": False, "rule": ""}
            elif path == "/api/sources": payload = {"sources": state["sources"], "checklists": []}
            elif path == "/api/sources/synthetic-source/review" and method == "PATCH":
                command = route.request.post_data_json
                old_notes = state["sources"][0]["notes"]
                scope_keys = {"organization_id", "project_id", "discovery_allowed", "discovery_sectors", "discovery_geographies", "allowed_paths", "allow_query_parameters", "state_reason"}
                state["source_revision"] += 1
                state["sources"][0].update({key: value for key, value in command.items() if key not in scope_keys | {"notes"}})
                state["sources"][0].update(reviewed_at=f"source-v{state['source_revision']}", notes=old_notes | {key: command[key] for key in scope_keys if key in command} | {"notes": command.get("notes", old_notes.get("notes", ""))})
                payload = {"source": state["sources"][0]}
            elif path == "/api/projects": payload = {"projects": [owner["project"] for owner in owners.values()] if route.request.headers.get("x-asie-organization-id") == "synthetic-org-a" else []}
            elif path in ("/api/datasets/manual-import", "/api/datasets/file-import") and method == "POST":
                command = route.request.post_data_json
                row = {"dataset_id": "synthetic-created", "organization_id": "synthetic-org-a", "source_id": "", "title": command["title"], "publisher": command["publisher"], "review_status": "review_required", "updated_at": "created-v1", "columns": ["item", "price"], "preview": [], "row_count": 1, "notes": {}}
                state["datasets"].append(row)
                payload = {"dataset": row}
            elif path == "/api/datasets": payload = {"datasets": [dataset for owner in owners.values() for dataset in owner["datasets"]]}
            elif path == f"/api/datasets/{dataset_id}/review" and method == "POST":
                state["datasets"][0].update(route.request.post_data_json | {"updated_at": "dataset-v2"})
                payload = {"dataset": state["datasets"][0]}
            elif path == "/api/sector-taxonomy": payload = {"taxonomy": []}
            elif path == "/api/architecture/runtime-status": payload = {}
            elif path == "/api/dib/sessions": payload = {"sessions": [session(state)]}
            elif path == f"/api/dib/sessions/{session_id}":
                if state["fail_next_dib_read"]:
                    state["fail_next_dib_read"] = False
                    route.fulfill(status=500, json={"error": "PRIVATE-EXCEPTION-MARKER"}); return
                payload = {"session": session(state)}
                if state["defer_dib"]:
                    state["pending_dib"].append((route, copy.deepcopy(payload))); return
            elif path == f"/api/dib/sessions/{session_id}/blueprints":
                command = route.request.post_data_json
                if state["dib_conflict"] or command["expected_original"] != session(state)["origin_reference"]:
                    route.fulfill(status=409, json={"error": "dib_blueprint_write_conflict"}); return
                state["dib_value"] = command["item_decisions"][0]["decision"]["value"]
                state["dib_revision"] += 1
                if state["fail_read_after_save"]: state["fail_next_dib_read"] = True
                loaded = session(state); payload = {"blueprint": {"payload": loaded["current_blueprint"], "origin_reference": loaded["origin_reference"]}}
            elif path == f"/api/projects/{project_id}" and method == "PATCH":
                if state["fail_save"]: route.fulfill(status=500, json={"error": "PRIVATE-EXCEPTION-MARKER"}); return
                state["project"] = state["project"] | route.request.post_data_json | {"updated_at": "version-two"}; payload = {"project": state["project"]}
            elif path.startswith(f"/api/projects/{project_id}/"):
                tail = path.rsplit("/", 1)[1]
                items = [] if state["project"]["name"] else [requirement(state["project"])]
                readiness = {"project_id": state["project"]["project_id"], "ready_to_run": False, "steps": [], "blockers": []}
                if tail == "readiness": payload = readiness
                elif tail == "runs" and method == "GET": payload = {"runs": []}
                elif tail == "assumptions": payload = {"assumptions": []}
                elif tail == "evidence-register": payload = register
                elif tail == "evidence-ledger": payload = {"evidence_register": register, "evidence_ledger": [], "evidence_coverage": {"targets": [], "gaps": [], "supported": 0, "needs_evidence": 0}, "transformation_lineage": [], "recovery_items": evidence_requirements(state)}
                elif tail == "workspace": payload = {"project": state["project"], "readiness": readiness, "assumptions": [], "runs": [], "latest_overview": None, "latest_report_view": None, "latest_review": None, "action_items": [], "remediation": {"source": "draft_readiness", "items": [], "blockers": []}, "current_recovery": {"contract_id": "customer.recovery.v1", "source": "current_draft", "organization_id": "synthetic-org-a", "project_id": project_id, "updated_at": state["project"]["updated_at"], "items": items}, "capabilities": [{"capability_id": "intelligence_context_construction", "state": "disabled", "owner": "intelligence_ingress", "version": "v1", "evidence_ref": "private-policy", "reason_key": "context_construction_disabled"}]}
                else: state["blocked"].append(path); route.fulfill(status=500, json={"error": "unexpected_test_api"}); return
            else: state["blocked"].append(path); route.fulfill(status=500, json={"error": "unexpected_test_api"}); return
            route.fulfill(status=200, json=payload)
        def route(route):
            url = urlsplit(route.request.url)
            path = url.path
            requested_project = parse_qs(url.query).get("project_id", [None])[0]
            command = route.request.post_data_json if route.request.post_data else {}
            if isinstance(command, dict): requested_project = requested_project or command.get("project_id")
            owner = owners.get(requested_project, state)
            for candidate in owners.values():
                if (path.startswith(f"/api/projects/{candidate['project']['project_id']}/")
                        or path == f"/api/projects/{candidate['project']['project_id']}"
                        or (path == f"/api/dib/sessions/{candidate.get('session_id', 'synthetic-dib-session')}" or path.startswith(f"/api/dib/sessions/{candidate.get('session_id', 'synthetic-dib-session')}/"))
                        or any(path == f"/api/datasets/{row['dataset_id']}/review" for row in candidate["datasets"])):
                    owner = candidate
            route_owned(route, owner)
        context.route("**/*", route)
        page = context.new_page(); page.on("pageerror", lambda error: state["errors"].append(str(error)))
        try:
            page.goto(FIXTURE + f"?lang={locale}#readiness")
            expect(page.locator(".workspace")).to_be_visible()
            self.navigate(page, locale)
            yield page, state
            self.assertEqual(state["blocked"], [])
            self.assertEqual(state["errors"], [])
            allowed_run_reads = {f"/api/projects/{project_id}/runs" for project_id in owners}
            self.assertFalse(any(
                "pre-runs" in path or "manifest" in path or "validation-gate" in path
                or ("/runs" in path and not (method == "GET" and path in allowed_run_reads))
                for method, path, _ in state["requests"]
            ))
            visible = page.locator("body").inner_text()
            for marker in ("PRIVATE-ORIGIN-HASH", "private-blueprint", "private-item", "INTERNAL-UNSAFE-LABEL", "PRIVATE-EXCEPTION-MARKER"):
                self.assertNotIn(marker, visible)
        finally:
            page.screenshot(path=str(ARTIFACTS / f"{self._testMethodName}-{locale}-{'mobile' if mobile else 'desktop'}.png"), full_page=True)
            context.close()

    def navigate(self, page, locale):
        expect(page.locator(".workspace")).to_be_visible()
        nav = page.locator("#workspace-navigation")
        toggle = page.get_by_role("button", name="فتح قائمة التنقل" if locale == "ar" else "Open navigation menu", exact=True)
        expect(nav.and_(page.locator(":visible")).or_(toggle.and_(page.locator(":visible"))).first).to_be_visible()
        if not nav.is_visible(): toggle.click()
        expect(nav).to_be_visible()
        page.locator("#workspace-navigation .nav-item").filter(has_text="افحص النواقص" if locale == "ar" else "Check missing inputs").click()
        expect(page.get_by_role("heading", name="نواقص المسودة الحالية" if locale == "ar" else "Current draft requirements", exact=True)).to_be_visible()

    def store_step_seven_draft(self, page, owner, inputs):
        project = owner["project"]
        project["name"] = project["name"] or "Synthetic wizard project"
        project["inputs"].update({
            "location_region": "منطقة الرياض", "location_city": "الرياض", "location_district": "",
            "primary_sector_id": "services", "subsector_id": "synthetic-services",
            "gap_statement": "Synthetic local need", "competitive_edge": "Synthetic service advantage",
            "target_audience": "individuals", "capital_available": 100, "annual_discount_rate": 0.1,
            "working_capital_months": 0, "debt_amount": 0, "annual_interest_rate": 0, "loan_years": 0,
            **inputs,
        })
        form = {key: copy.deepcopy(project[key]) for key in ("name", "sector", "jurisdiction", "depth_profile", "inputs")}
        draft = {"project_id": project["project_id"], "organization_id": project["organization_id"],
                 "form": form, "formOrigin": project["updated_at"], "wizardStep": 7, "stage": "wizard"}
        page.evaluate("draft => sessionStorage.setItem(`asie.recovery.edit.v1:synthetic-user:synthetic-org-a:${draft.project_id}`, JSON.stringify(draft))", draft)

    def continue_from_summary(self, page, owner, locale="en"):
        expect(page.locator(".workspace")).to_be_visible()
        nav = page.locator("#workspace-navigation")
        toggle = page.get_by_role("button", name="فتح قائمة التنقل" if locale == "ar" else "Open navigation menu", exact=True)
        expect(nav.and_(page.locator(":visible")).or_(toggle.and_(page.locator(":visible"))).first).to_be_visible()
        if not nav.is_visible(): toggle.click()
        nav.locator(".nav-item").filter(has_text="الملخص" if locale == "ar" else "Summary").click()
        page.locator(".cc-row").filter(has=page.get_by_text(owner["project"]["name"], exact=True)).get_by_role("button", name="إكمال" if locale == "ar" else "Continue", exact=True).click()
        expect(page.locator(".wizard-progress-label")).to_contain_text("8")
        expect(page.locator("#wizard-intake-choices")).to_be_visible()
        expect(page.locator(".next-action-banner").get_by_role("button", name="عالج متطلبات الجاهزية" if locale == "ar" else "Complete readiness requirements", exact=True)).to_be_visible()

    def test_capacity_mode_validates_and_focuses_only_visible_capacity_inputs(self):
        for locale, mobile in (("ar", False), ("en", True)):
            with self.subTest(locale=locale, mobile=mobile), self.app(locale, mobile) as (page, state):
                self.store_step_seven_draft(page, state, {
                    "intake_mode": "manual", "monthly_units": 0, "use_operating_capacity": True,
                    "capacity_units_per_day": 0, "operating_days_per_month": 0, "utilization_rate": 0,
                })
                page.reload()
                self.continue_from_summary(page, state, locale)
                primary = page.locator(".wizard-focus").get_by_role("button", name="افحص النواقص" if locale == "ar" else "Check missing inputs", exact=True)
                expect(page.locator("#wizard-monthly-units")).to_have_count(0)
                for field, value in (("capacity_units_per_day", "12"), ("operating_days_per_month", "22"), ("utilization_rate", "0.5")):
                    expect(primary).to_be_disabled()
                    expect(page.locator(".workspace")).to_have_attribute("data-asie-missing-target", f"wizard-{field}")
                    page.get_by_role("button", name="سند" if locale == "ar" else "Sanad", exact=True).click()
                    page.get_by_role("button", name="أكمل هذا المدخل" if locale == "ar" else "Complete this input", exact=True).click()
                    control = page.locator(f"#wizard-{field}")
                    expect(control).to_be_visible(); expect(control).to_be_focused()
                    if field == "utilization_rate":
                        control.fill("1.1"); expect(primary).to_be_disabled()
                        expect(page.locator(".workspace")).to_have_attribute("data-asie-missing-target", "wizard-utilization_rate")
                    control.fill(value)
                expect(primary).to_be_enabled()
                capacity = page.get_by_label("استخدام نموذج الطاقة التشغيلية" if locale == "ar" else "Use operating-capacity model", exact=True)
                capacity.uncheck()
                expect(page.locator("#wizard-monthly-units")).to_have_value("0")
                expect(primary).to_be_disabled()
                capacity.check(); expect(primary).to_be_enabled()
                primary.click()
                expect(page.locator(".evidence-workbench-intro")).to_be_visible()
                writes = [body for method, path, body in state["requests"] if method == "PATCH" and path == "/api/projects/synthetic-project-a"]
                self.assertEqual(len(writes), 1)
                saved = writes[0]["inputs"]
                self.assertEqual(saved["monthly_units"], 0)
                self.assertTrue(saved["use_operating_capacity"])
                self.assertEqual((saved["capacity_units_per_day"], saved["operating_days_per_month"], saved["utilization_rate"]), (12, 22, 0.5))

    def test_file_intake_completion_requires_current_project_import_or_linked_available_data(self):
        with self.app("en", evidence=True, two_projects=True) as (page, state):
            other = state["owners"]["synthetic-project-b"]
            state["datasets"][0].update(title="Project A quotation", notes={"submission_provenance": {"initial_project_id": "synthetic-project-a"}})
            other["datasets"] = []
            self.store_step_seven_draft(page, state, {"intake_mode": "file"})
            self.store_step_seven_draft(page, other, {"intake_mode": "file"})
            page.reload()
            self.continue_from_summary(page, state)
            primary = page.locator(".wizard-focus").get_by_role("button", name="Check missing inputs", exact=True)
            expect(primary).to_be_disabled()
            page.locator("#wizard-data-file").set_input_files({"name": "project-a.csv", "mimeType": "text/csv", "buffer": b"item,price\nA quotation,123"})
            expect(primary).to_be_enabled()
            imports = [body for method, path, body in state["requests"] if method == "POST" and path == "/api/datasets/file-import"]
            self.assertEqual(len(imports), 1)
            self.assertEqual(imports[0]["project_id"], "synthetic-project-a")
            self.continue_from_summary(page, other)
            expect(primary).to_be_disabled()
            expect(page.locator("#wizard-data-file")).to_be_visible()
            for project_id, dataset_id, allowed in (
                ("synthetic-project-a", "synthetic-dataset", False),
                ("synthetic-project-b", "unavailable-dataset", False),
                ("synthetic-project-b", "synthetic-dataset", True),
            ):
                other["evidence_links"] = [{"project_id": project_id, "dataset_id": dataset_id}]
                self.continue_from_summary(page, state)
                self.continue_from_summary(page, other)
                if allowed: expect(primary).to_be_enabled()
                else: expect(primary).to_be_disabled()
            self.assertEqual(state["datasets"][0]["notes"]["submission_provenance"]["initial_project_id"], "synthetic-project-a")
            self.assertFalse(any(method == "POST" and "evidence-links" in path for method, path, _ in state["requests"]))

    def test_exact_name_focus_failed_save_retains_and_success_returns(self):
        for locale, mobile in (("ar", False), ("en", True)):
            with self.subTest(locale=locale, mobile=mobile), self.app(locale, mobile) as (page, state):
                page.get_by_role("button", name=re.compile("^افتح المتطلب" if locale == "ar" else "^Open requirement")).click()
                field = page.get_by_label("اسم المشروع" if locale == "ar" else "Project name", exact=True)
                expect(field).to_be_focused(); field.fill("Synthetic retained name")
                state["fail_save"] = True
                save = page.get_by_role("button", name="حفظ وإعادة فحص المتطلب" if locale == "ar" else "Save and recheck requirement", exact=True)
                save.click(); expect(save).to_be_enabled(); expect(field).to_have_value("Synthetic retained name")
                state["fail_save"] = False; save.click()
                expect(page.get_by_role("status").filter(has_text="تحقق المصدر" if locale == "ar" else "source confirms")).to_be_visible()
                page.get_by_role("button", name="العودة إلى موضعي مع حفظ العمل الحالي" if locale == "ar" else "Return to my place, keeping current work", exact=True).click()
                expect(page.get_by_role("heading", name="نواقص المسودة الحالية" if locale == "ar" else "Current draft requirements", exact=True)).to_be_focused()

    def test_evidence_buttons_require_an_explicit_target(self):
        with self.app("en", evidence=True) as (page, state):
            expect(page.get_by_role("button", name="Open requirement 1", exact=True)).to_be_enabled()
            page.locator("#workspace-navigation .nav-item").filter(has_text="Link evidence").click()
            expect(page.get_by_role("button", name="Link evidence", exact=True)).to_be_disabled()
            expect(page.get_by_role("button", name="Link requirement", exact=True)).to_be_disabled()
            expect(page.get_by_text("To link evidence, open the specific requirement", exact=False)).to_be_visible()
            self.assertFalse(any(method == "POST" and "evidence-links" in path for method, path, _ in state["requests"]))

    def test_sanad_moves_to_current_requirement_after_previous_one_is_resolved(self):
        for locale in ("ar", "en"):
            with self.subTest(locale=locale), self.app(locale, evidence=True) as (page, state):
                page.get_by_role("button", name="افتح المتطلب 1" if locale == "ar" else "Open requirement 1", exact=True).click()
                page.get_by_label("اسم المشروع" if locale == "ar" else "Project name", exact=True).fill("Synthetic resolved name")
                page.get_by_role("button", name="حفظ وإعادة فحص المتطلب" if locale == "ar" else "Save and recheck requirement", exact=True).click()
                expect(page.get_by_role("status").filter(has_text="تحقق المصدر" if locale == "ar" else "source confirms")).to_be_visible()
                expect(page.get_by_label("اسم المشروع" if locale == "ar" else "Project name", exact=True)).to_have_value("Synthetic resolved name")
                expected = "بيانات المراجعة المطلوبة غير مكتملة. أدخل الدليل الحقيقي؛ لا تُنشأ إقرارات تلقائية." if locale == "ar" else "Required review metadata is missing. Supply actual evidence; declarations are not generated automatically."
                expect(page.locator(".workspace")).to_have_attribute("data-asie-missing-label", expected)
                expect(page.locator(".workspace")).to_have_attribute("data-asie-recovery-index", "0")
                page.get_by_role("button", name="سند" if locale == "ar" else "Sanad", exact=True).click()
                expect(page.locator(".asie-sanad-assistant__blocker")).to_contain_text(expected)
                page.get_by_role("button", name="أكمل هذا المدخل" if locale == "ar" else "Complete this input", exact=True).click()
                expect(page.get_by_role("textbox", name="عنوان البيانات" if locale == "ar" else "Dataset title", exact=True)).to_be_focused()
                self.assertEqual(state["project"]["name"], "Synthetic resolved name")
                self.assertEqual(state["datasets"][0]["title"], "")

    def test_refresh_preserves_unsaved_project_input(self):
        with self.app("en") as (page, state):
            page.get_by_role("button", name=re.compile("^Open requirement")).click()
            page.get_by_label("Project name", exact=True).fill("Unsaved retained draft")
            page.reload()
            expect(page.get_by_label("Project name", exact=True)).to_have_value("Unsaved retained draft")
            self.assertEqual(state["project"]["name"], "")

    def test_dib_original_reference_conflict_and_source_specific_save(self):
        with self.app("en") as (page, state):
            page.get_by_role("combobox", name="Session", exact=True).select_option("synthetic-dib-session")
            page.get_by_role("button", name="Edit this input", exact=True).click()
            page.get_by_label("Value", exact=True).fill("25")
            state["dib_revision"] += 1
            page.get_by_role("button", name="Save and reread", exact=True).click()
            expect(page.get_by_role("status").filter(has_text="original version changed")).to_be_visible()
            expect(page.get_by_label("Value", exact=True)).to_have_value("25")
            page.get_by_role("button", name="Review current revision before retrying", exact=True).click()
            expect(page.get_by_text("Currently saved value", exact=False)).to_be_visible()
            expect(page.get_by_label("Value", exact=True)).to_have_value("25")
            page.get_by_role("button", name="I reviewed the current revision and choose it as my value's basis", exact=True).click()
            page.get_by_role("button", name="Save and reread", exact=True).click()
            expect(page.get_by_role("status").filter(has_text="source confirms this input")).to_be_visible()
            self.assertEqual(state["dib_value"], 25)
            self.assertFalse(any(method == "PATCH" for method, _, _ in state["requests"]))

    def test_committed_save_failed_read_preserves_work_and_orphaned_refresh(self):
        with self.app("en") as (page, state):
            page.get_by_role("combobox", name="Session", exact=True).select_option("synthetic-dib-session")
            page.get_by_role("button", name="Edit this input", exact=True).click()
            page.get_by_label("Value", exact=True).fill("31")
            page.get_by_label("Decision reason", exact=True).fill("Synthetic retained rationale")
            state["fail_read_after_save"] = True
            page.get_by_role("button", name="Save and reread", exact=True).click()
            expect(page.get_by_role("button", name="Save and reread", exact=True)).to_be_enabled()
            expect(page.get_by_label("Value", exact=True)).to_have_value("31")
            self.assertEqual(state["dib_value"], 31)
            self.assertEqual(state["dib_revision"], 2)
            page.reload()
            expect(page.get_by_label("Retained value", exact=True)).to_have_value("31")
            expect(page.get_by_role("textbox", name="Retained reason", exact=True)).to_have_value("Synthetic retained rationale")
            expect(page.get_by_role("button", name="Save and reread", exact=True)).to_have_count(0)
            writes = [row for row in state["requests"] if row[0] == "POST" and row[1].endswith("/blueprints")]
            self.assertEqual(len(writes), 1)
            page.get_by_role("button", name="Discard this retained draft", exact=True).click()
            expect(page.get_by_label("Retained value", exact=True)).to_have_count(0)

    def test_expired_session_keeps_scoped_draft_and_never_saves(self):
        with self.app("en") as (page, state):
            page.get_by_role("combobox", name="Session", exact=True).select_option("synthetic-dib-session")
            page.get_by_role("button", name="Edit this input", exact=True).click()
            page.get_by_label("Value", exact=True).fill("42")
            state["expire_dib"] = True
            page.get_by_role("button", name="Save and reread", exact=True).click()
            expect(page.get_by_label("Value", exact=True)).to_have_count(0)
            self.assertEqual(page.evaluate("sessionStorage.getItem('asie.session_token.v1')"), None)
            stored = page.evaluate("sessionStorage.getItem('asie.recovery.dib.v1:synthetic-user:synthetic-org-a:synthetic-project-a')")
            self.assertEqual(json.loads(stored)["value"], "42")
            self.assertIsNone(state["dib_value"])

    def test_keyboard_zoom_and_back_forward_preserve_project_draft(self):
        for locale in ("ar", "en"):
            with self.subTest(locale=locale), self.app(locale, mobile=True) as (page, state):
                button = page.get_by_role("button", name=re.compile("^افتح المتطلب" if locale == "ar" else "^Open requirement"))
                button.focus(); page.keyboard.press("Enter")
                field = page.get_by_label("اسم المشروع" if locale == "ar" else "Project name", exact=True)
                expect(field).to_be_focused(); field.fill("Keyboard retained draft")
                page.evaluate("document.documentElement.style.zoom='2'")
                field.scroll_into_view_if_needed(); expect(field).to_be_visible()
                self.assertEqual(page.evaluate("document.documentElement.dir"), "rtl" if locale == "ar" else "ltr")
                page.keyboard.press("Tab")
                self.assertNotEqual(page.evaluate("document.activeElement.tagName"), "BODY")
                page.evaluate("history.pushState({}, '', '#synthetic-browser-history')")
                page.go_back(); expect(field).to_have_value("Keyboard retained draft")
                page.go_forward(); expect(field).to_have_value("Keyboard retained draft")
                self.assertEqual(state["project"]["name"], "")

    def test_delayed_old_session_reply_cannot_restore_another_organization(self):
        for late_status in (200, 401):
            with self.subTest(late_status=late_status), self.app("en") as (page, state):
                state["defer_dib"] = True
                page.get_by_role("combobox", name="Session", exact=True).select_option("synthetic-dib-session")
                deadline = time.monotonic() + 5
                while not state["pending_dib"] and time.monotonic() < deadline:
                    page.wait_for_timeout(20)
                self.assertEqual(len(state["pending_dib"]), 1)
                page.locator(".sidebar").get_by_role("button", name="Account and team", exact=True).click()
                page.locator(".org-chip").filter(has_text="Other synthetic organization").click()
                page.wait_for_function("sessionStorage.getItem('asie.active_organization.v1') === 'synthetic-org-b'")
                pending, body = state["pending_dib"].pop()
                pending.fulfill(status=late_status, json=body if late_status == 200 else {"error": "PRIVATE-OLD-SESSION"})
                page.wait_for_timeout(100)
                expect(page.get_by_label("Project session inputs", exact=True)).to_have_count(0)
                self.assertEqual(page.evaluate("sessionStorage.getItem('asie.session_token.v1')"), "synthetic-token")
                self.assertNotIn("PRIVATE-OLD-SESSION", page.locator("body").inner_text())

    def test_dataset_draft_survives_return_reopen_refresh_and_uses_dataset_owner(self):
        with self.app("en", evidence=True) as (page, state):
            page.get_by_role("button", name="Open requirement 2", exact=True).click()
            field = page.get_by_label("Dataset title", exact=True)
            field.fill("Retained dataset title")
            page.get_by_role("button", name="Return to my place, keeping current work", exact=True).click()
            page.get_by_role("button", name="Open requirement 1", exact=True).click()
            page.get_by_label("Project name", exact=True).fill("Independent unsaved project name")
            page.get_by_role("button", name="Return to my place, keeping current work", exact=True).click()
            page.get_by_role("button", name="Open requirement 2", exact=True).click()
            expect(field).to_have_value("Retained dataset title")
            page.reload(); expect(field).to_have_value("Retained dataset title")
            page.get_by_role("button", name="Save and recheck requirement", exact=True).click()
            expect(page.get_by_role("status").filter(has_text="source confirms")).to_be_visible()
            self.assertEqual(state["datasets"][0]["title"], "Retained dataset title")
            self.assertEqual(state["project"]["name"], "")
            self.assertFalse(any(method == "PATCH" for method, _, _ in state["requests"]))

    def test_restored_old_form_cannot_overwrite_new_project_version(self):
        with self.app("en") as (page, state):
            page.get_by_role("button", name="Open requirement 1", exact=True).click()
            page.get_by_label("Project name", exact=True).fill("Old draft name")
            page.get_by_role("button", name="Return to my place, keeping current work", exact=True).click()
            state["project"]["updated_at"] = "concurrent-version"
            state["project"]["inputs"]["unit_price"] = 999
            page.reload()
            page.get_by_role("button", name="Open requirement 1", exact=True).click()
            page.get_by_role("button", name="Save and recheck requirement", exact=True).click()
            expect(page.get_by_role("status").filter(has_text=re.compile("changed|older"))).to_be_visible()
            self.assertFalse(any(method == "PATCH" for method, _, _ in state["requests"]))
            page.get_by_role("button", name="Review current source before retrying", exact=True).click()
            page.get_by_role("button", name="I reviewed the source and choose this revision for this requirement", exact=True).click()
            page.get_by_role("button", name="Save and recheck requirement", exact=True).click()
            expect(page.get_by_role("status").filter(has_text="source confirms")).to_be_visible()
            self.assertEqual(state["project"]["name"], "Old draft name")
            self.assertEqual(state["project"]["inputs"]["unit_price"], 999)

    def test_source_admin_details_require_explicit_protected_entry(self):
        for administrator in (False, True):
            with self.subTest(administrator=administrator), self.app("en", source_review=True, administrator=administrator) as (page, state):
                page.get_by_role("button", name="Open requirement 2", exact=True).click()
                expect(page.get_by_label("Verified terms fingerprint", exact=True)).to_have_count(0)
                self.assertNotIn("PRIVATE-SOURCE-TERMS", page.locator("body").inner_text())
                entry = page.get_by_role("button", name="Open administrative review of this source", exact=True)
                if not administrator:
                    expect(entry).to_have_count(0)
                    continue
                entry.click()
                expect(page.get_by_role("heading", name="Platform administration source review", exact=True)).to_be_visible()
                expect(page.locator(".client-page-shell")).to_have_count(0)
                expect(page.get_by_label("Verified terms fingerprint", exact=True)).to_have_value("PRIVATE-SOURCE-TERMS")
                page.get_by_role("combobox", name="Source state", exact=True).select_option("enabled")
                page.get_by_role("combobox", name="Reviewer decision", exact=True).select_option("approved")
                page.get_by_role("button", name="Save and recheck requirement", exact=True).click()
                expect(page.get_by_role("status").filter(has_text="source confirms")).to_be_visible()
                writes = [body for method, path, body in state["requests"] if method == "PATCH" and path == "/api/sources/synthetic-source/review"]
                self.assertEqual(len(writes), 1)
                self.assertEqual(writes[0]["organization_id"], "synthetic-org-a")
                self.assertEqual(writes[0]["project_id"], "synthetic-project-a")
                self.assertEqual(writes[0]["allowed_paths"], ["/source"])
                self.assertEqual(writes[0]["notes"], "Synthetic note")
                self.assertFalse(writes[0]["discovery_allowed"])

    def test_customer_pasted_csv_survives_refresh_and_import_has_no_official_source(self):
        with self.app("en") as (page, state):
            def open_evidence():
                page.locator("#workspace-navigation .nav-item").filter(has_text="Link evidence").click()
            open_evidence()
            field = page.get_by_role("textbox", name="Paste comma-separated data", exact=True)
            field.fill("item,price\nMy quotation,123")
            page.reload()
            open_evidence()
            expect(field).to_have_value("item,price\nMy quotation,123")
            page.get_by_title("Create a manual dataset", exact=True).click()
            expect(page.get_by_role("combobox", name="Dataset to transform", exact=True)).to_have_value("synthetic-created")
            sent = [body for method, path, body in state["requests"] if path == "/api/datasets/manual-import" and method == "POST"]
            self.assertEqual(len(sent), 1)
            self.assertEqual(sent[0]["csv_text"], "item,price\nMy quotation,123")
            self.assertEqual(sent[0]["intended_use"], "customer_study")
            self.assertEqual(sent[0]["project_id"], "synthetic-project-a")
            self.assertEqual(sent[0]["source_id"], "")
            self.assertNotIn("terms_hash", sent[0])
            self.assertNotIn("license_snapshot_ref", sent[0])

    def test_dataset_proof_is_admin_only_while_other_metadata_remains_editable(self):
        for administrator in (False, True):
            with self.subTest(administrator=administrator), self.app("en", evidence=True, dataset_proof=True, administrator=administrator) as (page, state):
                page.get_by_role("button", name="Open requirement 2", exact=True).click()
                expect(page.get_by_label("Verified terms fingerprint", exact=True)).to_have_count(0)
                expect(page.get_by_label("Dataset title", exact=True)).to_be_editable()
                page.get_by_label("Dataset title", exact=True).fill("Retained ordinary metadata")
                page.get_by_role("button", name="Save and recheck requirement", exact=True).click()
                expect(page.get_by_role("status").filter(has_text="still reports")).to_be_visible()
                write = [body for method, path, body in state["requests"] if method == "POST" and path.endswith("/review")][-1]
                self.assertEqual(write, {"title": "Retained ordinary metadata"})
                entry = page.get_by_role("button", name="Open administrative license review of this dataset", exact=True)
                if not administrator:
                    expect(entry).to_have_count(0)
                    continue
                entry.click()
                expect(page.locator(".client-page-shell")).to_have_count(0)
                expect(page.get_by_label("Verified terms fingerprint", exact=True)).to_have_value("PRIVATE-DATASET-TERMS")
                page.get_by_label("Verified terms fingerprint", exact=True).fill("UNSENT-ADMIN-PROOF")
                page.get_by_role("button", name="Return to customer workspace keeping work", exact=True).click()
                expect(page.get_by_label("Verified terms fingerprint", exact=True)).to_have_count(0)
                page.get_by_label("Dataset title", exact=True).fill("Second ordinary metadata edit")
                page.get_by_role("button", name="Save and recheck requirement", exact=True).click()
                expect(page.get_by_role("status").filter(has_text="still reports")).to_be_visible()
                self.assertEqual(state["datasets"][0]["terms_hash"], "PRIVATE-DATASET-TERMS")
                entry.click()
                expect(page.get_by_label("Verified terms fingerprint", exact=True)).to_have_value("UNSENT-ADMIN-PROOF")

    def test_customer_dataset_accepts_truthful_nonpublic_classification(self):
        with self.app("en", evidence=True, customer_classification=True) as (page, state):
            page.get_by_role("button", name="Open requirement 2", exact=True).click()
            field = page.locator("label").filter(has=page.get_by_text("Classify your data by sensitivity and intended sharing", exact=True)).get_by_role("textbox")
            field.fill("Private project quotations")
            expect(page.get_by_label("Verified terms fingerprint", exact=True)).to_have_count(0)
            page.get_by_role("button", name="Save and recheck requirement", exact=True).click()
            expect(page.get_by_role("status").filter(has_text="still reports")).to_be_visible()
            self.assertEqual(state["datasets"][0]["classification"], "Private project quotations")
            self.assertEqual(state["datasets"][0]["source_id"], "")

    def test_source_post_save_baseline_allows_reverting_a_changed_value(self):
        with self.app("en", source_review=True, administrator=True) as (page, state):
            page.get_by_role("button", name="Open requirement 2", exact=True).click()
            page.get_by_role("button", name="Open administrative review of this source", exact=True).click()
            field = page.get_by_label("Publisher", exact=True)
            save = page.get_by_role("button", name="Save and recheck requirement", exact=True)
            field.fill("Changed publisher")
            save.click()
            expect(page.get_by_role("status").filter(has_text="still reports this requirement")).to_be_visible()
            self.assertEqual(state["sources"][0]["publisher"], "Changed publisher")
            expect(field).to_have_value("Changed publisher")
            field.fill("Synthetic source")
            save.click()
            expect(save).to_be_enabled()
            self.assertEqual(state["sources"][0]["publisher"], "Synthetic source")
            expect(field).to_have_value("Synthetic source")
            self.assertEqual(state["source_revision"], 3)

    def test_same_organization_projects_keep_distinct_drafts_and_owner_writes(self):
        with self.app("en", evidence=True, two_projects=True) as (page, state):
            def switch(letter):
                page.locator("#workspace-navigation .nav-item").filter(has_text="Summary").click()
                page.locator(".cc-row").filter(has=page.get_by_text(f"Synthetic project {letter}", exact=True)).get_by_role("button", name="Continue", exact=True).click()
                self.navigate(page, "en")
            def evidence():
                page.locator("#workspace-navigation .nav-item").filter(has_text="Link evidence").click()
            def metadata(value=None):
                page.get_by_role("button", name="Open requirement 1", exact=True).click()
                field = page.get_by_role("textbox", name="Dataset title", exact=True)
                if value is not None: field.fill(value)
                return field
            def close_metadata():
                page.get_by_role("button", name="Return to my place, keeping current work", exact=True).click()
            def dib(session_id, value=None):
                selector = page.get_by_role("combobox", name="Session", exact=True)
                expect(selector.locator(f'option[value="{session_id}"]')).to_have_count(1)
                if selector.is_enabled() and selector.input_value() != session_id:
                    selector.select_option(session_id)
                expect(selector).to_have_value(session_id)
                field = page.get_by_role("spinbutton", name="Value", exact=True)
                edit = page.get_by_role("button", name="Edit this input", exact=True).and_(page.locator(":enabled"))
                expect(field.or_(edit).first).to_be_visible()
                if not field.is_visible(): edit.click()
                expect(field).to_be_visible()
                if value is not None: field.fill(value)
                return field
            metadata("A metadata draft"); close_metadata()
            dib("synthetic-dib-session", "111")
            evidence(); csv = page.get_by_role("textbox", name="Paste comma-separated data", exact=True)
            csv.fill("item,price\nA quotation,111")
            switch("B")
            expect(metadata()).to_have_value("")
            page.get_by_role("textbox", name="Dataset title", exact=True).fill("B metadata draft"); close_metadata()
            expect(dib("synthetic-dib-session-b")).to_have_value("")
            page.get_by_role("spinbutton", name="Value", exact=True).fill("222")
            evidence(); expect(csv).to_have_value(""); csv.fill("item,price\nB quotation,222")
            switch("A")
            expect(metadata()).to_have_value("A metadata draft"); close_metadata()
            expect(dib("synthetic-dib-session")).to_have_value("111")
            page.reload(); self.navigate(page, "en")
            expect(dib("synthetic-dib-session")).to_have_value("111")
            evidence(); expect(csv).to_have_value("item,price\nA quotation,111")
            self.navigate(page, "en"); page.go_back(); page.go_forward()
            self.navigate(page, "en")
            expect(metadata()).to_have_value("A metadata draft")
            page.get_by_role("button", name="Save and recheck requirement", exact=True).click()
            expect(page.get_by_role("status").filter(has_text="source confirms this deficit is resolved")).to_be_visible()
            self.assertEqual(state["datasets"][0]["title"], "A metadata draft")
            other = state["owners"]["synthetic-project-b"]
            self.assertEqual(other["datasets"][0]["title"], "")
            expect(dib("synthetic-dib-session")).to_have_value("111")
            page.get_by_role("button", name="Save and reread", exact=True).click()
            expect(page.get_by_role("status").filter(has_text="source confirms this input")).to_be_visible()
            self.assertEqual(state["dib_value"], 111); self.assertIsNone(other["dib_value"])
            evidence(); page.get_by_title("Create a manual dataset", exact=True).click()
            expect(page.get_by_role("combobox", name="Dataset to transform", exact=True)).to_have_value("synthetic-created")
            imported = [body for method, path, body in state["requests"] if method == "POST" and path == "/api/datasets/manual-import"]
            self.assertEqual(len(imported), 1)
            self.assertEqual((imported[0]["project_id"], imported[0]["csv_text"]), ("synthetic-project-a", "item,price\nA quotation,111"))
            switch("B"); expect(metadata()).to_have_value("B metadata draft"); close_metadata()
            expect(dib("synthetic-dib-session-b")).to_have_value("222")
            evidence(); expect(csv).to_have_value("item,price\nB quotation,222")
            self.assertFalse(any(path.startswith("/api/dib/sessions/synthetic-dib-session-b/") and method == "POST" for method, path, _ in state["requests"]))
            self.assertFalse(any(path == "/api/datasets/synthetic-dataset-b/review" and method == "POST" for method, path, _ in state["requests"]))
            stored = page.evaluate("Object.fromEntries(Object.entries(sessionStorage).filter(([key])=>key.includes('customer-csv')))")
            self.assertTrue(any(key.endswith('synthetic-project-a:customer-csv') and 'A quotation' in value for key,value in stored.items()))
            self.assertTrue(any(key.endswith('synthetic-project-b:customer-csv') and 'B quotation' in value for key,value in stored.items()))

    def test_delayed_project_a_session_cannot_replace_project_b_in_same_organization(self):
        with self.app("en", evidence=True, two_projects=True) as (page, state):
            state["defer_dib"] = True
            page.get_by_role("combobox", name="Session", exact=True).select_option("synthetic-dib-session")
            deadline = time.monotonic() + 5
            while not state["pending_dib"] and time.monotonic() < deadline: page.wait_for_timeout(20)
            self.assertEqual(len(state["pending_dib"]), 1)
            page.locator("#workspace-navigation .nav-item").filter(has_text="Summary").click()
            page.locator(".cc-row").filter(has=page.get_by_text("Synthetic project B", exact=True)).get_by_role("button", name="Continue", exact=True).click()
            self.navigate(page, "en")
            page.get_by_role("combobox", name="Session", exact=True).select_option("synthetic-dib-session-b")
            page.get_by_role("button", name="Edit this input", exact=True).click()
            page.get_by_role("spinbutton", name="Value", exact=True).fill("222")
            pending, body = state["pending_dib"].pop(); pending.fulfill(status=200, json=body)
            expect(page.get_by_role("spinbutton", name="Value", exact=True)).to_have_value("222")
            expect(page.get_by_role("combobox", name="Session", exact=True)).to_have_value("synthetic-dib-session-b")
            self.assertEqual(page.evaluate("sessionStorage.getItem('asie.active_organization.v1')"), "synthetic-org-a")
            self.assertFalse(any(method == "POST" for method, _, _ in state["requests"]))

    def test_storage_failure_disclosed_without_losing_live_edit(self):
        with self.app("en", storage_failure=True) as (page, _state):
            page.get_by_role("button", name=re.compile("^Open requirement")).click()
            page.get_by_label("Project name", exact=True).fill("Live only draft")
            expect(page.get_by_role("status").filter(has_text="Browser draft storage is unavailable")).to_be_visible()
            expect(page.get_by_label("Project name", exact=True)).to_have_value("Live only draft")


if __name__ == "__main__":
    server = subprocess.Popen([shutil.which("pnpm") or "pnpm", "exec", "vite", "--host", "127.0.0.1", "--port", "5195", "--strictPort"], cwd=ROOT,
        env=dict(os.environ, ASIE_ALLOW_EXTERNAL_FETCH="false", ASIE_PROVIDER_CONTROL_ENABLED="false", PNPM_HOME="/tmp/asie-pnpm", XDG_DATA_HOME="/tmp/asie-xdg-data", XDG_CACHE_HOME="/tmp/asie-xdg-cache"), stdout=subprocess.DEVNULL)
    try:
        for _ in range(150):
            if server.poll() is not None: raise SystemExit("Synthetic fixture server exited")
            try:
                with urlopen(FIXTURE, timeout=1) as response:
                    if response.status == 200: break
            except OSError: time.sleep(.2)
        else: raise SystemExit("Synthetic fixture server unavailable")
        unittest.main(verbosity=2)
    finally:
        server.terminate(); server.wait(timeout=10)
