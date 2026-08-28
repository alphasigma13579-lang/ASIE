"""Real-browser behavior checks with an emulated GPS API; never calls providers.

Run from the canonical package after installing requirements-browser.txt and
the Chromium browser: python tools/check_location_consent_browser.py
The fixture imports production React code but is not a production build entry.
"""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
import unittest
from urllib.parse import urlsplit
from urllib.request import urlopen

from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "http://127.0.0.1:5195"
FIXTURE = ORIGIN + "/tools/browser/location-consent.html"
ARTIFACTS = ROOT / "browser-artifacts"
REQUEST = "تحديد موقعي بإذني"
RETRY = "إعادة طلب موقعي"
CONFIRM = "تأكيد الإحداثيات لموقعي"
CANCEL = "إلغاء استخدام موقع الجهاز"
GEOLOCATION_STUB = """
(() => {
  const calls = [];
  window.__gps = {
    calls,
    succeed(index, coords) { calls[index].success({coords}); },
    fail(index, code) { calls[index].error({code, message: "PRIVATE ERROR MUST NOT APPEAR"}); },
  };
  Object.defineProperty(navigator, "geolocation", {
    configurable: true,
    value: {getCurrentPosition(success, error, options) {calls.push({success, error, options});}},
  });
})();
"""


class LocationConsentBrowserChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright = sync_playwright().start()
        cls.addClassCleanup(cls.playwright.stop)
        cls.browser = cls.playwright.chromium.launch()
        cls.addClassCleanup(cls.browser.close)

    @contextmanager
    def page(self, *, init="", mobile=False):
        context = self.browser.new_context(
            viewport={"width": 390, "height": 844} if mobile else {"width": 1000, "height": 900},
            locale="ar-SA",
            service_workers="block",
        )
        blocked, errors = [], []
        def route_request(route):
            target = urlsplit(route.request.url)
            if target.scheme == "http" and target.netloc == "127.0.0.1:5195" and not target.path.startswith("/api"):
                route.continue_()
            else:
                blocked.append(route.request.url)
                route.abort()
        context.route("**/*", route_request)
        context.add_init_script(GEOLOCATION_STUB + "\n" + init)
        page = context.new_page()
        page.on("pageerror", lambda error: errors.append(str(error)))
        try:
            page.goto(FIXTURE)
            expect(page.get_by_role("button", name=REQUEST, exact=True)).to_be_visible()
            yield page
            self.assertEqual(blocked, [], "Browser attempted unexpected outbound traffic")
            self.assertEqual(errors, [], "Uncaught browser errors")
        except Exception:
            page.screenshot(path=str(ARTIFACTS / (self._testMethodName + "-failure.png")), full_page=True)
            raise
        finally:
            context.close()

    def succeed(self, page, index=0, *, latitude=24.7136, longitude=46.6753, accuracy=12.4):
        page.evaluate(
            "([index, coords]) => window.__gps.succeed(index, coords)",
            [index, {"latitude": latitude, "longitude": longitude, "accuracy": accuracy}],
        )

    def assert_unconfirmed(self, page):
        expect(page.get_by_test_id("confirmed")).to_have_text("[]")

    def test_no_request_on_mount_or_manual_entry(self):
        with self.page() as page:
            self.assertEqual(page.evaluate("window.__gps.calls.length"), 0)
            page.get_by_label("خط العرض اليدوي").fill("25")
            page.get_by_label("خط الطول اليدوي").fill("47")
            self.assertEqual(page.evaluate("window.__gps.calls.length"), 0)
            self.assert_unconfirmed(page)

    def test_confirmation_is_explicit_and_only_coordinates_cross_boundary(self):
        with self.page() as page:
            page.get_by_role("button", name=REQUEST, exact=True).click()
            self.assertEqual(page.evaluate("window.__gps.calls.length"), 1)
            self.assertEqual(page.evaluate("window.__gps.calls[0].options"), {
                "enableHighAccuracy": True, "timeout": 10000, "maximumAge": 0,
            })
            self.succeed(page)
            expect(page.get_by_role("status")).to_contain_text("موقع مؤقت")
            expect(page.get_by_text("13 متر", exact=True)).to_be_visible()
            expect(page.get_by_text("24.713600", exact=True)).to_be_visible()
            self.assert_unconfirmed(page)
            page.screenshot(path=str(ARTIFACTS / "desktop-candidate.png"), full_page=True)
            expect(page.get_by_label("خط العرض اليدوي")).to_have_value("")
            page.get_by_role("button", name=CONFIRM, exact=True).click()
            values = json.loads(page.get_by_test_id("confirmed").inner_text())
            self.assertEqual(values, [{"latitude": 24.7136, "longitude": 46.6753}])
            expect(page.get_by_role("button", name=REQUEST, exact=True)).to_be_focused()
            expect(page.get_by_label("خط العرض اليدوي")).to_have_value("24.7136")
            expect(page.get_by_label("خط الطول اليدوي")).to_have_value("46.6753")
            self.assertIsNone(page.evaluate("localStorage.getItem('location')"))
            self.assertEqual(page.evaluate("localStorage.length + sessionStorage.length"), 0)

    def test_permission_errors_preserve_manual_entry_and_hide_raw_error(self):
        for code, message in [(1, "لم تسمح"), (2, "تعذر تحديد"), (3, "انتهت مهلة")]:
            with self.subTest(code=code), self.page() as page:
                page.get_by_role("button", name=REQUEST, exact=True).click()
                page.evaluate("(code) => window.__gps.fail(0, code)", code)
                expect(page.get_by_role("status")).to_contain_text(message)
                expect(page.locator("body")).not_to_contain_text("PRIVATE ERROR")
                self.assert_unconfirmed(page)
                page.get_by_label("خط العرض اليدوي").fill("26")
                expect(page.get_by_label("خط العرض اليدوي")).to_have_value("26")

    def test_invalid_coordinates_and_accuracy_cannot_be_confirmed(self):
        cases = [(91, 46, 1), (-91, 46, 1), (24, 181, 1), (24, -181, 1), (24, 46, -1)]
        for latitude, longitude, accuracy in cases:
            with self.subTest(values=(latitude, longitude, accuracy)), self.page() as page:
                page.get_by_role("button", name=REQUEST, exact=True).click()
                self.succeed(page, latitude=latitude, longitude=longitude, accuracy=accuracy)
                expect(page.get_by_role("status")).to_contain_text("تعذر تحديد")
                expect(page.get_by_role("button", name=CONFIRM, exact=True)).to_have_count(0)
                self.assert_unconfirmed(page)
        for field in ("latitude", "longitude", "accuracy"):
            for invalid in ("NaN", "Infinity", "-Infinity"):
                with self.subTest(field=field, invalid=invalid), self.page() as page:
                    page.get_by_role("button", name=REQUEST, exact=True).click()
                    page.evaluate("window.__gps.succeed(0, {latitude: 24, longitude: 46, accuracy: 1, " + field + ": " + invalid + "})")
                    expect(page.get_by_role("status")).to_contain_text("تعذر تحديد")
                    self.assert_unconfirmed(page)

    def test_cancel_ignores_late_success_and_error(self):
        with self.page() as page:
            page.get_by_role("button", name=REQUEST, exact=True).click()
            page.get_by_role("button", name=CANCEL, exact=True).click()
            self.succeed(page)
            page.evaluate("window.__gps.fail(0, 1)")
            expect(page.get_by_role("status")).to_contain_text("أُلغي")
            expect(page.get_by_role("button", name=CONFIRM, exact=True)).to_have_count(0)
            self.assert_unconfirmed(page)

    def test_retry_ignores_stale_callback_and_accepts_only_latest(self):
        with self.page() as page:
            page.get_by_role("button", name=REQUEST, exact=True).click()
            page.get_by_role("button", name=RETRY, exact=True).click()
            self.succeed(page, 0, latitude=22)
            page.evaluate("window.__gps.fail(0, 1)")
            expect(page.get_by_role("status")).to_contain_text("بانتظار")
            self.succeed(page, 1, latitude=25)
            page.evaluate("window.__gps.fail(1, 1)")
            page.get_by_role("button", name=CONFIRM, exact=True).click()
            self.assertEqual(json.loads(page.get_by_test_id("confirmed").inner_text()),
                             [{"latitude": 25, "longitude": 46.6753}])

    def test_cancel_discards_candidate(self):
        with self.page() as page:
            page.get_by_role("button", name=REQUEST, exact=True).click()
            self.succeed(page)
            page.get_by_role("button", name=CANCEL, exact=True).click()
            expect(page.get_by_role("button", name=CONFIRM, exact=True)).to_have_count(0)
            self.assert_unconfirmed(page)

    def test_unmount_invalidates_callback_and_remount_starts_empty(self):
        with self.page() as page:
            page.get_by_role("button", name=REQUEST, exact=True).click()
            page.get_by_role("button", name="تبديل المكون للاختبار").click()
            self.succeed(page)
            page.evaluate("window.__gps.fail(0, 1)")
            self.assert_unconfirmed(page)
            page.get_by_role("button", name="تبديل المكون للاختبار").click()
            expect(page.get_by_role("button", name=REQUEST, exact=True)).to_be_visible()
            expect(page.get_by_role("button", name=CONFIRM, exact=True)).to_have_count(0)
            self.assertEqual(page.evaluate("window.__gps.calls.length"), 1)

    def test_context_switch_discards_pending_and_candidate_positions(self):
        for complete in (False, True):
            with self.subTest(complete=complete), self.page() as page:
                page.get_by_role("button", name=REQUEST, exact=True).click()
                if complete:
                    self.succeed(page)
                    expect(page.get_by_role("button", name=CONFIRM, exact=True)).to_be_visible()
                page.get_by_role("button", name="تغيير السياق للاختبار").click()
                self.succeed(page)
                page.evaluate("window.__gps.fail(0, 1)")
                expect(page.get_by_role("button", name=REQUEST, exact=True)).to_be_visible()
                expect(page.get_by_role("button", name=CONFIRM, exact=True)).to_have_count(0)
                self.assert_unconfirmed(page)
                self.assertEqual(page.evaluate("window.__gps.calls.length"), 1)

    def test_insecure_or_unsupported_environment_never_requests_gps(self):
        cases = [
            ('Object.defineProperty(window, "isSecureContext", {value: false});', "HTTPS"),
            ('Object.defineProperty(navigator, "geolocation", {value: undefined});', "لا يدعم"),
        ]
        for init, message in cases:
            with self.subTest(message=message), self.page(init=init) as page:
                page.get_by_role("button", name=REQUEST, exact=True).click()
                expect(page.get_by_role("status")).to_contain_text(message)
                self.assertEqual(page.evaluate("window.__gps.calls.length"), 0)
                page.get_by_label("خط الطول اليدوي").fill("47")
                self.assert_unconfirmed(page)

    def test_synchronous_failure_does_not_break_manual_entry(self):
        with self.page(init='navigator.geolocation.getCurrentPosition = () => {throw new Error("PRIVATE ERROR")};') as page:
            page.get_by_role("button", name=REQUEST, exact=True).click()
            expect(page.get_by_role("status")).to_contain_text("تعذر تحديد")
            expect(page.locator("body")).not_to_contain_text("PRIVATE ERROR")
            page.get_by_label("خط العرض اليدوي").fill("24")
            self.assert_unconfirmed(page)

    def test_mobile_rtl_keyboard_confirmation_and_manual_override(self):
        with self.page(mobile=True) as page:
            self.assertEqual(page.locator("html").get_attribute("dir"), "rtl")
            page.get_by_role("button", name=REQUEST, exact=True).focus()
            page.keyboard.press("Enter")
            self.succeed(page)
            page.screenshot(path=str(ARTIFACTS / "mobile-candidate.png"), full_page=True)
            page.get_by_role("button", name=CONFIRM, exact=True).focus()
            page.keyboard.press("Enter")
            expect(page.get_by_role("status")).to_contain_text("تم نقل")
            page.get_by_label("خط العرض اليدوي").fill("26")
            expect(page.get_by_label("خط العرض اليدوي")).to_have_value("26")
            self.assertTrue(page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"))
            for control in page.locator(".location-consent button, .location-fields input").all():
                box = control.bounding_box()
                self.assertIsNotNone(box)
                self.assertGreaterEqual(box["x"], 0)
                self.assertLessEqual(box["x"] + box["width"], 390)
                self.assertGreaterEqual(box["height"], 44)


if __name__ == "__main__":
    ARTIFACTS.mkdir(exist_ok=True)
    # Prevent a developer's ambient provider flags from affecting this harness.
    env = dict(os.environ, ASIE_ALLOW_EXTERNAL_FETCH="false", ASIE_PROVIDER_CONTROL_ENABLED="false")
    pnpm = shutil.which("pnpm")
    if not pnpm:
        raise SystemExit("pnpm is required for the local fixture server")
    server = subprocess.Popen(
        [pnpm, "exec", "vite", "--host", "127.0.0.1", "--port", "5195", "--strictPort"],
        cwd=ROOT, env=env,
    )
    try:
        for attempt in range(150):
            if server.poll() is not None:
                raise SystemExit("Fixture server exited before readiness")
            try:
                with urlopen(FIXTURE, timeout=1) as response:
                    if response.status == 200:
                        break
            except OSError:
                time.sleep(0.2)
        else:
            raise SystemExit("Fixture server did not become ready")
        unittest.main(verbosity=2)
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=5)
