"""App/session regression checks in Chromium with intercepted, tenant-labelled APIs.

No real GPS, backend, provider, account or secret is used. This imports the
production App and API modules, not a parallel implementation of their state.
"""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
import unittest
from urllib.parse import urlsplit
from urllib.request import urlopen

from playwright.sync_api import expect, sync_playwright
import check_location_consent_browser as consent

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = consent.ORIGIN
FIXTURE = ORIGIN + "/tools/browser/app-session.html"
INITIAL_SESSION = """
localStorage.setItem("asie.product_entry.v1", "1");
localStorage.setItem("asie.legal_acceptance.v1", "1");
sessionStorage.setItem("asie.session_token.v1", "test-session-a");
sessionStorage.setItem("asie.active_organization.v1", "org-a");
"""
MEMBERSHIPS = [
    {"organization_id": "org-a", "organization_name": "مؤسسة ألف", "role": "organization_owner"},
    {"organization_id": "org-b", "organization_name": "مؤسسة باء", "role": "organization_owner"},
]


class AppSessionBrowserChecks(unittest.TestCase):
    """Prove isolation across real App transitions and asynchronous API replies."""

    @classmethod
    def setUpClass(cls):
        """Use an isolated Chromium process without any real browser session."""
        cls.playwright = sync_playwright().start()
        cls.addClassCleanup(cls.playwright.stop)
        cls.browser = cls.playwright.chromium.launch()
        cls.addClassCleanup(cls.browser.close)

    @contextmanager
    def app(self, location="#wizard"):
        """Intercept every API and reject all non-loopback traffic."""
        context = self.browser.new_context(locale="ar-SA", service_workers="block",
                                           viewport={"width": 1280, "height": 1000})
        context.add_init_script(INITIAL_SESSION + consent.GEOLOCATION_STUB)
        state = {"blocked": [], "errors": [], "requests": [], "pending": [],
                 "defer_projects": False, "login_number": 0, "locale": "ar", "defer_locale": False, "locale_pending": []}
        policy = {"profile_id": "TEST_ONLY", "external_fetch_enabled": False, "rule": "",
                  "enabled_sources": [], "candidate_sources": [], "reference_only": [],
                  "blocked_sources": []}

        def route_request(route):
            target = urlsplit(route.request.url)
            if target.scheme != "http" or target.netloc != "127.0.0.1:5195":
                state["blocked"].append(route.request.url)
                route.abort()
                return
            path = target.path
            if not path.startswith("/api"):
                route.continue_()
                return
            headers = route.request.headers
            state["requests"].append((path, headers.get("x-asie-organization-id"),
                                      route.request.method))
            if path == "/api/auth/me":
                if not headers.get("authorization"):
                    route.fulfill(status=401, json={"error": "authentication_required"})
                    return
                payload = {"user_id": "user-test", "platform_role": None,
                           "memberships": MEMBERSHIPS, "locale": state["locale"], "external_access_enabled": False}
            elif path == "/api/auth/preferences" and route.request.method == "PATCH":
                state["locale"] = route.request.post_data_json["locale"]
                payload = {"locale": state["locale"]}
                if state["defer_locale"]:
                    state["defer_locale"] = False
                    state["locale_pending"].append(route)
                    return
            elif path == "/api/auth/login":
                state["login_number"] += 1
                payload = {"access_token": "test-login-" + str(state["login_number"]),
                           "token_type": "Bearer", "user": {"user_id": "user-test",
                           "display_name": "اختبار", "email": "test@example.invalid",
                           "platform_role": None}, "memberships": MEMBERSHIPS,
                           "external_access_enabled": False}
            elif path == "/api/auth/logout":
                payload = {"ok": True}
            elif path == "/api/snapshots/snapshot-probe/report.html":
                route.fulfill(status=200, body="<html><body>snapshot probe</body></html>", content_type="text/html")
                return
            elif path == "/api/snapshots/snapshot-stale/report.html":
                route.fulfill(status=500, json={"error": "PRIVATE-STALE-SNAPSHOT-ERROR"})
                return
            elif path == "/api/source-policy":
                payload = policy
            elif path == "/api/sources":
                payload = {"sources": [], "checklists": [], "external_fetch_enabled": False}
            elif path == "/api/projects" and route.request.method == "GET":
                if state["defer_projects"]:
                    state["defer_projects"] = False
                    state["pending"].append(route)
                    return
                payload = {"projects": []}
            elif path == "/api/datasets":
                payload = {"datasets": []}
            elif path == "/api/sector-taxonomy":
                payload = {"taxonomy": []}
            elif path == "/api/architecture/runtime-status":
                payload = {}
            else:
                state["blocked"].append(path)
                route.fulfill(status=500, json={"error": "unexpected_test_api"})
                return
            route.fulfill(status=200, json=payload)

        context.route("**/*", route_request)
        page = context.new_page()
        page.on("pageerror", lambda error: state["errors"].append(str(error)))
        try:
            page.goto(FIXTURE + location)
            expect(page.locator(".location-consent")).to_be_visible()
            yield page, state
            self.assertEqual(state["blocked"], [], "Unexpected API or outbound traffic")
            self.assertEqual(state["errors"], [], "Uncaught browser errors")
        except Exception:
            page.screenshot(path=str(consent.ARTIFACTS / (self._testMethodName + "-failure.png")),
                            full_page=True)
            raise
        finally:
            context.close()

    def location(self, page):
        """Navigate through the real sidebar, never reload away the state defect."""
        close = page.get_by_role("button", name="عودة إلى المسار", exact=True)
        if close.count():
            close.click()
        page.locator(".sidebar").get_by_role("button", name="عرّف مشروعك").click()
        expect(page.get_by_role("button", name=consent.REQUEST, exact=True)).to_be_visible()

    def settings(self, page):
        """Open the existing account overlay and wait until it is usable."""
        close = page.get_by_role("button", name="عودة إلى المسار", exact=True)
        if not close.is_visible():
            page.locator(".sidebar").get_by_role("button", name="الحساب والفريق", exact=True).click()
        expect(close).to_be_visible()
        expect(page.get_by_role("heading", name="منظمتك النشطة", exact=True)).to_be_visible()

    def switch(self, page, organization="org-b"):
        """Select an organization and reopen settings after the real context reset."""
        self.settings(page)
        name = "مؤسسة باء" if organization == "org-b" else "مؤسسة ألف"
        target = page.locator(".org-chip").filter(has_text=name)
        already_active = target.evaluate("(element) => element.classList.contains('org-chip--active')")
        target.click()
        if already_active:
            expect(page.locator(".org-chip--active")).to_contain_text(name)
            return

        # An effective context switch deliberately remounts App. Its established
        # history bootstrap closes the old overlay and returns to #dashboard;
        # reopen the real settings control only after that new lifetime exists.
        page.wait_for_function(
            """(expected) =>
                sessionStorage.getItem("asie.active_organization.v1") === expected &&
                window.location.hash === "#dashboard"
            """,
            arg=organization,
        )
        self.settings(page)
        expect(page.locator(".org-chip--active")).to_contain_text(name)

    def confirm_location(self, page):
        """Confirm the emulated candidate through the production GPS control."""
        page.get_by_role("button", name=consent.REQUEST, exact=True).click()
        page.evaluate("window.__gps.succeed(window.__gps.calls.length - 1, "
                      "{latitude: 24.7136, longitude: 46.6753, accuracy: 12})")
        page.get_by_role("button", name=consent.CONFIRM, exact=True).click()
        expect(page.get_by_label("خط العرض")).to_have_value("24.7136")
        page.get_by_label("الحي أو الشارع").fill("PRIVATE-ORG-A-DRAFT")

    def assert_empty_location(self, page):
        """Both confirmed coordinates and manually entered draft context must clear."""
        self.location(page)
        expect(page.get_by_label("خط العرض")).to_have_value("")
        expect(page.get_by_label("خط الطول")).to_have_value("")
        expect(page.get_by_label("الحي أو الشارع")).to_have_value("")

    def login(self, page):
        """Sign in through the real AuthScreen against the intercepted API."""
        expect(page.get_by_role("heading", name="تسجيل الدخول إلى مساحة العمل")).to_be_visible()
        page.get_by_label("البريد الإلكتروني").fill("test@example.invalid")
        page.get_by_label("كلمة المرور", exact=True).fill("test-pass-12")
        page.get_by_role("button", name="دخول", exact=True).click()
        expect(page.locator(".sidebar")).to_be_visible()

    def defer_projects(self, page, state):
        """Start a real API-client request whose response is released after a switch."""
        state["defer_projects"] = True
        page.evaluate("""async () => {
            const api = await import("/src/api.ts");
            window.__sessionProbe = null;
            void api.fetchProjects().then(
              value => { window.__sessionProbe = {status: "fulfilled", value}; },
              () => { window.__sessionProbe = {status: "rejected"}; }
            );
        }""")
        deadline = time.monotonic() + 5
        while not state["pending"] and time.monotonic() < deadline:
            page.wait_for_timeout(20)
        self.assertEqual(len(state["pending"]), 1, "Deferred request never reached API interception")


    def test_delayed_language_save_cannot_continue_after_session_context_changes(self):
        with self.app() as (page, state):
            state["defer_locale"] = True
            page.get_by_label("الحي أو الشارع").fill("OLD-SESSION-DRAFT")
            page.get_by_role("button", name="English", exact=True).first.click()
            deadline = time.monotonic() + 5
            while not state["locale_pending"] and time.monotonic() < deadline:
                page.wait_for_timeout(20)
            self.assertEqual(1, len(state["locale_pending"]))
            page.get_by_role("button", name="العربية", exact=True).first.click()
            page.evaluate("async () => (await import('/src/session.ts')).setActiveOrganizationId('org-b')")
            # The explicit URL selection survives the new workspace lifetime and
            # is synchronized to the account without reviving the old request.
            expect(page.locator("html")).to_have_attribute("lang", "ar")
            expect(page.get_by_label("الحي أو الشارع")).to_have_value("")
            self.assertTrue(any(path == "/api/auth/me" and organization == "org-b"
                                for path, organization, _ in state["requests"]))
            deadline = time.monotonic() + 5
            while (state["locale"] != "ar" or
                   sum(path == "/api/auth/preferences" for path, _, _ in state["requests"]) < 2) and time.monotonic() < deadline:
                page.wait_for_timeout(20)
            self.assertEqual("ar", state["locale"])
            self.assertEqual(2, sum(path == "/api/auth/preferences" for path, _, _ in state["requests"]))
            state["locale_pending"].pop().fulfill(status=200, json={"locale": "en"})
            page.evaluate("() => Promise.resolve()")
            expect(page.locator("html")).to_have_attribute("lang", "ar")
            self.assertEqual("ar", state["locale"])

    def test_rapid_language_switches_persist_the_last_choice(self):
        with self.app() as (page, state):
            state["defer_locale"] = True
            page.get_by_role("button", name="English", exact=True).first.click()
            deadline = time.monotonic() + 5
            while not state["locale_pending"] and time.monotonic() < deadline:
                page.wait_for_timeout(20)
            self.assertEqual(1, len(state["locale_pending"]))
            page.get_by_role("button", name="العربية", exact=True).first.click()
            state["locale_pending"].pop().fulfill(status=200, json={"locale": "en"})
            deadline = time.monotonic() + 5
            while state["locale"] != "ar" and time.monotonic() < deadline:
                page.wait_for_timeout(20)
            self.assertEqual("ar", state["locale"])
            expect(page.locator("html")).to_have_attribute("lang", "ar")
            self.assertEqual("ar", page.evaluate("new URL(location.href).searchParams.get('lang')"))
            page.evaluate("localStorage.setItem('asie.customer_locale.v1', 'en')")
            page.reload()
            expect(page.get_by_role("button", name=consent.REQUEST, exact=True)).to_be_visible()
            expect(page.locator("html")).to_have_attribute("lang", "ar")

    def test_shared_language_link_overrides_account_and_persists(self):
        with self.app("?lang=en#wizard") as (page, state):
            expect(page.locator("html")).to_have_attribute("lang", "en")
            self.assertEqual("en", page.evaluate("new URL(location.href).searchParams.get('lang')"))
            deadline = time.monotonic() + 5
            while state["locale"] != "en" and time.monotonic() < deadline:
                page.wait_for_timeout(20)
            self.assertEqual("en", state["locale"])
            self.assertTrue(any(path == "/api/auth/preferences" and method == "PATCH"
                                for path, _organization, method in state["requests"]))

    def test_mobile_navigation_starts_compact_and_remains_usable(self):
        for locale in ("ar", "en"):
            with self.subTest(locale=locale), self.app() as (page, _state):
                page.set_viewport_size({"width": 390, "height": 844})
                if locale == "en":
                    page.get_by_role("button", name="English", exact=True).first.click()
                toggle_name = "فتح قائمة التنقل" if locale == "ar" else "Open navigation menu"
                toggle = page.get_by_role("button", name=toggle_name, exact=True)
                expect(toggle).to_be_visible()
                expect(toggle).to_have_attribute("aria-expanded", "false")
                expect(page.locator("#workspace-navigation")).not_to_be_visible()
                toggle.click()
                expect(page.locator("#workspace-navigation")).to_be_visible()
                page.locator("#workspace-navigation .nav-item").filter(
                    has_text="التقارير" if locale == "ar" else "Reports"
                ).click()
                page.wait_for_function("window.location.hash === '#snapshots'")
                expect(page.locator(".sidebar__mobile-toggle")).to_have_attribute("aria-expanded", "false")
                expect(page.locator("#workspace-navigation")).not_to_be_visible()

    def test_customer_routes_hide_internal_tokens_in_both_languages(self):
        forbidden = re.compile(
            r"project_id|run_id|snapshot_id|profile_id|contract_id|review_id|"
            r"projection_hash|release_hash|readiness_hash|review_required|not_ready|"
            r"demo_or_user_input_only|blocked_not_ready|no_evidence_links",
            re.IGNORECASE,
        )
        stages = ("dashboard", "wizard", "evidence", "readiness", "run",
                  "reality", "decision", "execution", "snapshots")
        for locale in ("ar", "en"):
            with self.subTest(locale=locale), self.app() as (page, _state):
                if locale == "en":
                    page.get_by_role("button", name="English", exact=True).first.click()
                links = page.locator(".asie-page-link")
                self.assertEqual(len(stages), links.count())
                for index, stage in enumerate(stages):
                    links.nth(index).click()
                    page.wait_for_function("expected => window.location.hash === expected", arg=f"#{stage}")
                    visible_text = page.locator(".workspace").inner_text()
                    self.assertIsNone(forbidden.search(visible_text), f"{stage}: leaked an internal token")

    def test_sanad_opens_exact_missing_field_and_returns_without_losing_draft(self):
        """Use the production Sanad portal and real navigation on both screen sizes."""
        for locale in ("ar", "en"):
            for width in (390, 1280):
                with self.subTest(locale=locale, width=width), self.app() as (page, _state):
                    page.set_viewport_size({"width": width, "height": 900})
                    if locale == "en":
                        page.get_by_role("button", name="English", exact=True).first.click()
                    draft = page.locator("#wizard-location-district")
                    draft.fill("حي الاختبار")
                    label = "تقاريري" if locale == "ar" else "Reports"
                    page.locator(".asie-page-link").filter(has_text=label).click()
                    page.wait_for_function("window.location.hash === '#snapshots'")
                    page.locator(".asie-sanad-launcher").click()
                    assistant = page.locator(".asie-sanad-assistant")
                    expect(assistant).to_contain_text(
                        "اختر المنطقة" if locale == "ar" else "Select a region"
                    )
                    assistant.get_by_role("button", name="أكمل هذا المدخل" if locale == "ar" else "Complete this input", exact=True).click()
                    page.wait_for_function("window.location.hash === '#wizard'")
                    expect(page.locator("#wizard-location-region")).to_be_focused()
                    expect(draft).to_have_value("حي الاختبار")
                    page.screenshot(path=str(consent.ARTIFACTS / f"sanad-missing-{locale}-{width}.png"), full_page=True)
                    page.get_by_role("button", name="العودة إلى موضعك السابق" if locale == "ar" else "Return to your previous place", exact=True).click()
                    page.wait_for_function("window.location.hash === '#snapshots'")
                    self.assertIsNone(page.evaluate("sessionStorage.getItem('asie.sanad.return_stage')"))
                    page.locator(".asie-sanad-launcher").click()
                    expect(page.locator(".asie-sanad-assistant").get_by_role(
                        "button", name="العودة إلى الصفحة السابقة" if locale == "ar" else "Return to previous page", exact=True
                    )).to_have_count(0)
                    self.assertFalse(any(method != "GET" and path != "/api/auth/preferences" for path, _, method in _state["requests"]))

    def test_location_labels_follow_language_without_changing_stored_values(self):
        """Display translations must not rewrite the project's location identifiers."""
        with self.app() as (page, _state):
            page.get_by_role("button", name="English", exact=True).first.click()
            expect(page.locator("html")).to_have_attribute("lang", "en")
            expect(page.locator("html")).to_have_attribute("dir", "ltr")
            region = page.locator("#wizard-location-region")
            city = page.locator("#wizard-location-city")
            values = region.locator("option").evaluate_all(
                "(options) => options.map(option => option.value).filter(Boolean)"
            )
            self.assertEqual(len(values), 13)
            for value in values:
                region.select_option(value)
                labels = region.locator("option").all_text_contents() + city.locator("option").all_text_contents()
                self.assertTrue(labels)
                for label in labels:
                    self.assertFalse(any("\u0600" <= char <= "\u06ff" for char in label), label)
                    self.assertNotIn("requires review", label)
            region.select_option("منطقة الرياض")
            expect(region.locator("option:checked")).to_have_text("Riyadh Region")
            expect(city.locator('option[value="الرياض"]')).to_have_text("Riyadh")
            page.get_by_role("button", name="العربية", exact=True).first.click()
            expect(page.locator("html")).to_have_attribute("dir", "rtl")
            expect(region).to_have_value("منطقة الرياض")
            expect(region.locator("option:checked")).to_have_text("منطقة الرياض")
            expect(city.locator('option[value="الرياض"]')).to_have_text("الرياض")
            self.assertFalse(any(method != "GET" and path != "/api/auth/preferences" for path, _, method in _state["requests"]))

    def test_same_organization_navigation_preserves_draft(self):
        """A normal navigation or reselecting the same organization is not a reset."""
        with self.app() as (page, state):
            self.confirm_location(page)
            self.switch(page, "org-a")
            self.location(page)
            expect(page.get_by_label("خط العرض")).to_have_value("24.7136")
            expect(page.get_by_label("الحي أو الشارع")).to_have_value("PRIVATE-ORG-A-DRAFT")

    def test_manual_zero_coordinates_are_retained_and_can_be_cleared(self):
        """Optional numeric coordinates distinguish explicit zero from no value."""
        with self.app() as (page, state):
            self.location(page)
            latitude = page.get_by_label("خط العرض")
            longitude = page.get_by_label("خط الطول")
            latitude.fill("0")
            longitude.fill("0")
            expect(latitude).to_have_value("0")
            expect(longitude).to_have_value("0")
            latitude.fill("")
            longitude.fill("")
            expect(latitude).to_have_value("")
            expect(longitude).to_have_value("")

    def test_snapshot_document_includes_active_organization(self):
        """Document requests keep the same selected-organization boundary as JSON APIs."""
        with self.app() as (page, state):
            page.evaluate("""async () => {
                window.open = () => null;
                const api = await import("/src/api.ts");
                await api.openSnapshotDocument("snapshot-probe", "report.html", "open");
            }""")
            self.assertIn(
                ("/api/snapshots/snapshot-probe/report.html", "org-a", "GET"),
                state["requests"],
            )

    def test_stale_snapshot_error_body_is_rejected_after_organization_switch(self):
        """A delayed document-error body cannot surface after the selected context changes."""
        with self.app() as (page, _state):
            page.evaluate("""async () => {
                const originalFetch = window.fetch;
                window.__resumeSnapshotError = null;
                window.__sessionProbe = null;
                window.fetch = async (...args) => {
                    const response = await originalFetch(...args);
                    if (String(args[0]).includes("/api/snapshots/snapshot-stale/report.html")) {
                        const readJson = response.json.bind(response);
                        response.json = () => new Promise(resolve => {
                            window.__resumeSnapshotError = () => readJson().then(resolve);
                        });
                    }
                    return response;
                };
                const api = await import("/src/api.ts");
                void api.openSnapshotDocument("snapshot-stale", "report.html", "open").then(
                    () => { window.__sessionProbe = {status: "fulfilled"}; },
                    error => { window.__sessionProbe = {status: "rejected", message: String(error.message)}; },
                );
            }""")
            page.wait_for_function("typeof window.__resumeSnapshotError === 'function'")
            self.switch(page)
            page.evaluate("window.__resumeSnapshotError()")
            page.wait_for_function("window.__sessionProbe !== null")
            probe = page.evaluate("window.__sessionProbe")
            self.assertEqual("rejected", probe["status"])
            self.assertEqual("تغير الحساب أو المؤسسة؛ أعد المحاولة في المساحة الحالية.", probe["message"])

    def test_failed_session_storage_write_cannot_publish_partial_context(self):
        """A failed organization write rolls back the token and emits no mixed-session event."""
        with self.app() as (page, _state):
            probe = page.evaluate("""async () => {
                const session = await import("/src/session.ts");
                const beforeRevision = session.getSessionRevision();
                let events = 0;
                const unsubscribe = session.onSessionContextChanged(() => { events += 1; });
                const originalRemoveItem = Storage.prototype.removeItem;
                Storage.prototype.removeItem = function(key) {
                    if (key === "asie.active_organization.v1") {
                        throw new DOMException("simulated storage failure", "QuotaExceededError");
                    }
                    return originalRemoveItem.call(this, key);
                };
                try {
                    session.setSessionToken("test-session-b");
                } finally {
                    Storage.prototype.removeItem = originalRemoveItem;
                    unsubscribe();
                }
                return {
                    token: sessionStorage.getItem("asie.session_token.v1"),
                    organization: sessionStorage.getItem("asie.active_organization.v1"),
                    revision: session.getSessionRevision(),
                    beforeRevision,
                    events,
                };
            }""")
            self.assertEqual("test-session-a", probe["token"])
            self.assertEqual("org-a", probe["organization"])
            self.assertEqual(probe["beforeRevision"], probe["revision"])
            self.assertEqual(0, probe["events"])

    def test_organization_switch_discards_confirmed_parent_form(self):
        """Regression: keying only the child GPS control does not clear App.form."""
        with self.app() as (page, state):
            self.confirm_location(page)
            self.switch(page)
            self.assert_empty_location(page)
            self.assertFalse(any(method != "GET" for _, _, method in state["requests"]))

    def test_logout_then_login_discards_parent_form(self):
        """A later login cannot recover the previous session's unsaved draft."""
        with self.app() as (page, state):
            self.confirm_location(page)
            self.settings(page)
            page.get_by_role("button", name="تسجيل الخروج وإنهاء الجلسة").click()
            self.login(page)
            self.assert_empty_location(page)

    def test_expired_session_then_login_discards_parent_form(self):
        """Server-reported expiration clears the same workspace boundary."""
        with self.app() as (page, state):
            self.confirm_location(page)
            page.evaluate('async () => (await import("/src/session.ts")).handleUnauthorized()')
            self.login(page)
            self.assert_empty_location(page)

    def test_old_success_is_rejected_after_organization_switch(self):
        """An old response must not become a current-scope result."""
        with self.app() as (page, state):
            self.defer_projects(page, state)
            self.switch(page)
            state["pending"].pop().fulfill(status=200, json={"projects": [{"name": "PRIVATE-ORG-A"}]})
            page.wait_for_function("window.__sessionProbe !== null")
            self.assertEqual(page.evaluate("window.__sessionProbe.status"), "rejected")

    def test_old_response_is_rejected_after_switching_back(self):
        """A -> B -> A is a new lifetime, not permission to revive the original reply."""
        with self.app() as (page, state):
            self.defer_projects(page, state)
            self.switch(page)
            self.switch(page, "org-a")
            state["pending"].pop().fulfill(status=200, json={"projects": [{"name": "PRIVATE-ORG-A"}]})
            page.wait_for_function("window.__sessionProbe !== null")
            self.assertEqual(page.evaluate("window.__sessionProbe.status"), "rejected")

    def test_old_unauthorized_reply_cannot_clear_current_session(self):
        """A stale 401 must not log out the currently selected organization."""
        with self.app() as (page, state):
            self.defer_projects(page, state)
            self.switch(page)
            state["pending"].pop().fulfill(status=401, json={"error": "expired_old_context"})
            page.wait_for_function("window.__sessionProbe !== null")
            self.assertEqual(page.evaluate("window.__sessionProbe.status"), "rejected")
            self.assertEqual(page.evaluate("sessionStorage.getItem('asie.session_token.v1')"), "test-session-a")
            self.assertEqual(page.evaluate("sessionStorage.getItem('asie.active_organization.v1')"), "org-b")
            expect(page.locator(".org-chip--active")).to_contain_text("مؤسسة باء")


if __name__ == "__main__":
    consent.ARTIFACTS.mkdir(exist_ok=True)
    env = dict(os.environ, ASIE_ALLOW_EXTERNAL_FETCH="false", ASIE_PROVIDER_CONTROL_ENABLED="false")
    pnpm = shutil.which("pnpm")
    if not pnpm:
        raise SystemExit("pnpm is required for the loopback App fixture")
    server = subprocess.Popen(
        [pnpm, "exec", "vite", "--host", "127.0.0.1", "--port", "5195", "--strictPort"],
        cwd=ROOT, env=env,
    )
    try:
        for attempt in range(150):
            if server.poll() is not None:
                raise SystemExit("App fixture server exited before readiness")
            try:
                with urlopen(FIXTURE, timeout=1) as response:
                    if response.status == 200:
                        break
            except OSError:
                time.sleep(0.2)
        else:
            raise SystemExit("App fixture server did not become ready")
        unittest.main(verbosity=2)
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=5)
