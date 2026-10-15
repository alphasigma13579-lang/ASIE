from __future__ import annotations

import re
import unittest
from pathlib import Path

from backend.customer_presentation import safe_narrative, unit_text
from backend.decision_pack import render_decision_pack_html


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"


class CustomerLanguageFoundationTests(unittest.TestCase):
    def test_language_provider_is_mounted_at_the_application_root(self) -> None:
        main = (SRC / "main.tsx").read_text(encoding="utf-8")
        self.assertIn('import { CustomerLanguageProvider } from "./customerLanguage";', main)
        self.assertIn("<CustomerLanguageProvider>", main)
        self.assertIn("</CustomerLanguageProvider>", main)

    def test_language_contract_defaults_to_arabic_and_updates_document_direction(self) -> None:
        source = (SRC / "customerLanguage.tsx").read_text(encoding="utf-8")
        self.assertIn('const DEFAULT_CUSTOMER_LOCALE: CustomerLocale = "ar";', source)
        self.assertIn('document.documentElement.lang = locale;', source)
        self.assertIn('document.documentElement.dir = locale === "ar" ? "rtl" : "ltr";', source)
        self.assertIn("CUSTOMER_LOCALE_STORAGE_KEY", source)
        self.assertIn("customerLocaleFromUrl", source)
        self.assertIn('url.searchParams.set("lang", locale);', source)
        self.assertIn("window.history.replaceState", source)

    def test_unknown_customer_status_and_errors_fail_closed(self) -> None:
        source = (SRC / "customerLanguage.tsx").read_text(encoding="utf-8")
        self.assertIn('"حالة تحتاج مراجعة"', source)
        self.assertIn('"Status requires review"', source)
        self.assertIn('"تعذر إتمام الطلب.', source)
        self.assertIn('"The request could not be completed.', source)
        error_projector = source[source.index("export function customerErrorText"):source.index("const customerSourceNames")]
        self.assertNotIn("return raw;", error_projector)
        self.assertEqual("تفصيل يحتاج مراجعة قبل عرضه", safe_narrative("finance engine failed", "ar"))
        self.assertEqual("Detail requires review before display", safe_narrative("runtime failure", "en"))

    def test_unreviewed_memo_explains_review_status_in_both_languages(self) -> None:
        pack = {"memo": {"review_status": "draft_review"}}
        for locale, expected in (("ar", "بانتظار المراجعة"), ("en", "Awaiting review")):
            with self.subTest(locale=locale):
                rendered = render_decision_pack_html(pack, locale=locale)
                self.assertIn(expected, rendered)
                self.assertNotIn("draft_review", rendered)

    def test_input_controls_and_review_progress_use_selected_language(self) -> None:
        app = (SRC / "App.tsx").read_text(encoding="utf-8")
        self.assertIn('text("زيادة", "Increase")', app)
        self.assertIn('text("إنقاص", "Decrease")', app)
        self.assertIn('{text("من", "of")} {assumptions.length} {text("مكتملة", "complete")}', app)
        self.assertIn('customerLocationLabel(region, locale)', app)
        self.assertIn('customerLocationLabel(city, locale)', app)

    def test_customer_messages_preserve_safe_validation_and_units_are_localized(self) -> None:
        app = (SRC / "App.tsx").read_text(encoding="utf-8")
        language = (SRC / "customerLanguage.tsx").read_text(encoding="utf-8")
        reports = (ROOT / "backend" / "reports.py").read_text(encoding="utf-8")
        self.assertIn("customerMessageText(error, locale)", app)
        self.assertNotIn("{customerErrorText(error, locale)}", app)  # Render safe validation state without reclassifying it; catch handlers may classify exceptions.
        self.assertIn("forbiddenOperationalDetail", language)
        self.assertIn("customerUnitText(item.unit, locale)", app)
        self.assertIn("unit_text(kpi.get('unit'), locale)", reports)
        self.assertEqual("ر.س شهريًا", unit_text("SAR/month", "ar"))
        self.assertEqual("SAR/month", unit_text("SAR/month", "en"))
        self.assertEqual("وحدة قياس", unit_text("unexpected_internal_unit", "ar"))
        self.assertEqual("Unit", unit_text("unexpected_internal_unit", "en"))

    def test_default_risk_actions_remain_actionable_in_arabic(self) -> None:
        expected_actions = {
            "Complete finance inputs.": "أكمل المدخلات المالية المطلوبة.",
            "Complete interest rate and loan tenor.": "أكمل نسبة التمويل ومدة السداد.",
            "Complete operating cost inputs.": "أكمل مدخلات تكاليف التشغيل.",
            "Reduce fixed OPEX or increase validated revenue capacity.": "خفّض المصروفات الثابتة أو أثبت قدرة أعلى على تحقيق الإيراد.",
            "Complete human review for exact open datasets.": "أكمل المراجعة البشرية لمصادر البيانات المفتوحة المحددة.",
            "Link approved datasets to critical assumptions.": "اربط المصادر المعتمدة بالافتراضات المؤثرة في القرار.",
        }
        for action, expected_arabic in expected_actions.items():
            with self.subTest(action=action):
                self.assertEqual(expected_arabic, safe_narrative(action, "ar"))

    def test_browser_download_name_preserves_the_selected_report_language(self) -> None:
        source = (SRC / "api.ts").read_text(encoding="utf-8")
        self.assertIn("asie-project-report-${locale}", source)

    def test_customer_auth_never_renders_raw_provider_errors(self) -> None:
        source = (SRC / "AuthScreens.tsx").read_text(encoding="utf-8")
        self.assertIn("setError(customerErrorText(reason, locale));", source)
        self.assertNotRegex(source, re.compile(r"setError\([^\n]*\.message"))
        self.assertIn('minLength={6} maxLength={12} value={password}', source)
        self.assertIn('minLength={6} maxLength={12} value={newPassword}', source)

    def test_dib_engineering_routes_are_role_gated(self) -> None:
        main = (SRC / "main.tsx").read_text(encoding="utf-8")
        gate = (SRC / "EngineeringSurfaceGate.tsx").read_text(encoding="utf-8")
        routed_components = (
            "DIBE2EScenario",
            "DIBSnapshotProjectionHandoff",
            "DIBControlledFinanceWiring",
            "DIBManifestRunReadiness",
            "DIBIntakeItemGovernance",
            "DIBProjectEntryPoint",
            "DIBWorkspace",
        )
        for component in routed_components:
            self.assertIn(
                f"<EngineeringSurfaceGate><{component} /></EngineeringSurfaceGate>",
                main,
            )
        self.assertIn('identity.platform_role === "platform_admin"', gate)
        self.assertIn("customerErrorText(failure, locale)", gate)
        self.assertIn('window.addEventListener("hashchange", syncHash)', main)
        self.assertIn('window.removeEventListener("hashchange", syncHash)', main)
        self.assertIn("<RoutedApplication />", main)

    def test_command_center_errors_follow_the_selected_language(self) -> None:
        command_center = (SRC / "CommandCenter.tsx").read_text(encoding="utf-8")
        self.assertIn("useState<unknown>(null)", command_center)
        self.assertIn("setLoadError(err)", command_center)
        self.assertIn("customerErrorText(loadError, locale)", command_center)
        self.assertNotIn("setLoadError(customerErrorText(err, locale))", command_center)

    def test_customer_overlays_hide_internal_profile_and_user_identifiers(self) -> None:
        app = (SRC / "App.tsx").read_text(encoding="utf-8")
        self.assertNotIn("Object.entries(profile)", app)
        self.assertNotIn("authUser?.display_name || authUser?.email || authUser?.user_id", app)
        self.assertNotIn("handleAddMember", app)
        self.assertNotIn("memberUserId", app)
        self.assertIn('text("الفريق والدعوات", "Team and invitations")', app)
        live_intelligence = (SRC / "LiveIntelligenceWorkspace.tsx").read_text(encoding="utf-8")
        self.assertIn('text("بحث حي محكوم", "Governed live research")', live_intelligence)
        self.assertNotIn("<p>ذكاء حي محكوم</p>", live_intelligence)
        self.assertNotIn("function SnapshotAnalytics(", app)
        self.assertIn("customerBusinessText(membership.role, locale)", app)
        self.assertIn('customerBusinessText(String(profile.profile_id ?? ""), locale)', app)
        self.assertIn("customerBusinessText(String(profile.sector_id ?? profile.profile_id ?? \"\"), locale)", app)

    def test_sanad_opens_exact_missing_input_and_preserves_return_stage(self) -> None:
        app = (SRC / "App.tsx").read_text(encoding="utf-8")
        surface = (SRC / "ASIECompleteSurfaceMount.tsx").read_text(encoding="utf-8")
        self.assertIn('window.addEventListener("asie:navigate-missing-input"', app)
        self.assertIn('data-asie-missing-label={recoveryItems.length ?', app)
        self.assertIn('data-asie-missing-target={firstMissingInputTarget}', app)
        self.assertIn('focusWizardTarget(targetId)', app)
        self.assertIn('id="wizard-project-name"', app)
        self.assertIn('text("العودة إلى موضعك السابق", "Return to your previous place")', app)
        self.assertIn('window.dispatchEvent(new CustomEvent("asie:navigate-missing-input", { detail:', surface)
        self.assertIn('detail.generation !== projectScope.current.generation', app)
        self.assertIn('writeRecoveryStorage("asie.sanad.return_stage"', surface)
        self.assertIn('removeRecoveryStorage("asie.sanad.return_stage")', surface)
        self.assertNotIn('window.sessionStorage.', surface)
        self.assertIn('text("أكمل هذا المدخل", "Complete this input")', surface)

    def test_recovery_storage_prefers_latest_memory_and_preserves_discard_on_failure(self):
        import subprocess
        source = (SRC / "customerLanguage.tsx").read_text(encoding="utf-8")
        start = source.index("const volatileRecoveryStorage")
        functions = source[start:]
        functions = functions.replace("new Map<string, string | null>()", "new Map()")
        functions = functions.replace("export function ", "function ")
        functions = functions.replace("(key: string, value: string): boolean", "(key, value)")
        functions = functions.replace("(key: string): string | null", "(key)")
        functions = functions.replace("(key: string): void", "(key)")
        program = """
const assert = require('node:assert/strict');
const disk = new Map([['draft', 'old']]);
let fail = false;
global.window = {sessionStorage: {
 getItem(key) { return disk.get(key) ?? null; },
 setItem(key, value) { if (fail) throw Error('synthetic'); disk.set(key,value); },
 removeItem(key) { if (fail) throw Error('synthetic'); disk.delete(key); }
}};
""" + functions + """
assert.equal(readRecoveryStorage('draft'), 'old');
fail = true;
assert.equal(writeRecoveryStorage('draft', 'new'), false);
assert.equal(readRecoveryStorage('draft'), 'new');
removeRecoveryStorage('draft');
assert.equal(readRecoveryStorage('draft'), null);
fail = false;
assert.equal(writeRecoveryStorage('draft', 'later'), true);
assert.equal(readRecoveryStorage('draft'), 'later');
assert.equal(disk.get('draft'), 'later');
"""
        completed = subprocess.run(["node", "-e", program], text=True, capture_output=True, timeout=10)
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_first_project_save_transfers_its_own_generation_and_releases_busy(self):
        import subprocess
        source = (SRC / "App.tsx").read_text(encoding="utf-8")
        start = source.index("  async function handleSaveDraft()")
        end = source.index("\n  }", start) + len("\n  }")
        function = source[start:end]
        program = """
const assert = require('node:assert/strict');
let project = null, busy = false;
const projectScope = {current:{generation:0}};
const formOrigin = {current:null};
const form = {name:'Synthetic project',inputs:{}};
const locale = 'en';
const setIsBusy = value => {busy=value};
const setError = () => {};
const setOverview = () => {}, setReport = () => {}, setReportView = () => {}, setDecisionPack = () => {}, setActionItems = () => {};
const setProject = value => { project=value; projectScope.current.generation += 1; };
const createProject = async () => ({project_id:'synthetic',updated_at:'v1'});
const updateProject = async () => {throw Error('unexpected update')};
const fetchProjectWorkspace = async () => {throw Error('unexpected read')};
const loadProjectWorkspace = async id => ({project_id:id});
const customerErrorText = () => 'safe';
""" + function + """
(async () => {
 assert.equal(await handleSaveDraft(), true);
 assert.equal(project.project_id, 'synthetic');
 assert.equal(formOrigin.current, 'v1');
 assert.equal(busy, false);
})().catch(error => {console.error(error);process.exit(1)});
"""
        completed = subprocess.run(["node", "-e", program], text=True, capture_output=True, timeout=10)
        self.assertEqual(completed.returncode, 0, completed.stderr)


    def test_confirmed_owner_save_advances_dirty_baseline_for_revert(self):
        import subprocess
        source = (SRC / "App.tsx").read_text(encoding="utf-8")
        start = source.index('      const confirmedRecord = target.kind === "source_review"')
        end_text = '      setRecoveryValues(confirmedValues); setRecoveryOriginalValues(confirmedOriginal);'
        end = source.index(end_text, start) + len(end_text)
        block = source[start:end]
        program = """
const assert = require('node:assert/strict');
const ts = require('typescript');
let current = {publisher:'A', reviewer:'user'}, original = {publisher:'A', reviewer:'user'};
const target = {kind:'source_review',source_id:'synthetic-source'};
const workbench = {sources:[{source_id:'synthetic-source',publisher:'B',reviewer:'user'}]};
const ledger = {evidence_register:{transformations:[]}};
const freshDatasets = [];
const recoveryValues = {publisher:'B',reviewer:'user'};
const recoveryOriginalValues = {publisher:'A',reviewer:'user'};
const sentRecoveryKeys = new Set(['publisher']);
const setRecoveryValues = values => {current = values};
const setRecoveryOriginalValues = values => {original = values};
""" + "\neval(ts.transpileModule(" + repr(block) + """, {compilerOptions:{target:ts.ScriptTarget.ES2022}}).outputText);
assert.deepEqual(current, {publisher:'B',reviewer:'user'});
assert.deepEqual(original, current);
current = {...current,publisher:'A'};
const edited = Object.fromEntries(Object.entries(current).filter(([key,value]) => value !== original[key]));
assert.deepEqual(edited, {publisher:'A'});
const payload = {...workbench.sources[0],...edited};
assert.equal(payload.publisher,'A');
assert.equal(payload.reviewer,'user');
"""
        completed = subprocess.run(["node", "-e", program], cwd=SRC.parent, text=True, capture_output=True, timeout=10)
        self.assertEqual(completed.returncode, 0, completed.stderr)


    def test_customer_csv_is_scoped_persisted_and_restored_without_cross_project_import(self):
        import subprocess
        source = (SRC / "App.tsx").read_text(encoding="utf-8")
        scope = source[source.index("  function setProject(next:"):source.index("  useEffect(() => () =>", source.index("  function setProject(next:"))]
        persist = source[source.index("  function persistRecoveryDraft()"):source.index("  useEffect(() => { persistRecoveryDraft();")]
        program = """
const assert = require('node:assert/strict'), ts = require('typescript');
const store = new Map();
const projectScope = {current:{id:'A',generation:0,load:0}}, recoveryOperation = {current:0};
let project = {project_id:'A'}, csvText = 'private-A,100', fileImportStatus = 'A imported';
const authUser = {user_id:'user'}, activeOrganizationId = 'org';
const pendingRecoveryRestore = {current:null}, formOrigin = {current:'v1'}, activeProjectOrigin = {current:'v1'};
const form = {}, activeRecovery = null, orphanedRecovery = null, recoveryValues = {}, recoveryOriginalValues = {};
const selectedDatasetId = '', selectedTransformationId = '', wizardStep = 0, stage = 'evidence';
const recoveryStorageKey = id => `draft:user:org:${id}`;
const readRecoveryStorage = key => store.get(key) ?? null;
const writeRecoveryStorage = (key,value) => {store.set(key,value);return true};
const retainTargetDraft = () => {}, setRecoveryStorageUnavailable = () => {};
const setCsvText = value => {csvText=value}, setFileImportStatus = value => {fileImportStatus=value};
const setProjectState = value => {project=value};
"""
        setters = set(re.findall(r"\b(set[A-Z]\w*)\(", scope)) - {"setProject", "setCsvText", "setFileImportStatus", "setProjectState"}
        program += "\n" + "\n".join(f"const {name} = () => {{}};" for name in sorted(setters))
        program += "\n" + "eval(ts.transpileModule(" + repr(scope + persist) + ", {compilerOptions:{target:ts.ScriptTarget.ES2022}}).outputText);"
        program += """
persistRecoveryDraft();
setProject({project_id:'B'});
assert.equal(csvText,''); assert.equal(fileImportStatus,'');
assert.equal(store.get('draft:user:org:A:customer-csv'),'private-A,100');
csvText='private-B,200'; persistRecoveryDraft();
setProject({project_id:'A'}); assert.equal(csvText,'private-A,100');
setProject(null); setProject({project_id:'B'}); assert.equal(csvText,'private-B,200');
assert.equal(project.project_id,'B');
"""
        completed = subprocess.run(["node", "-e", program], cwd=SRC.parent, text=True, capture_output=True, timeout=10)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("form, csvText, activeRecovery", source)

    def test_ordinary_metadata_save_preserves_unsent_admin_proof_draft(self):
        import subprocess
        source = (SRC / "App.tsx").read_text(encoding="utf-8")
        start = source.index('      const confirmedRecord = target.kind === "source_review"')
        finish = '      setRecoveryValues(confirmedValues); setRecoveryOriginalValues(confirmedOriginal);'
        block = source[start:source.index(finish, start) + len(finish)]
        program = """
const assert = require('node:assert/strict'), ts = require('typescript');
const target = {kind:'dataset_metadata',dataset_id:'d'};
const workbench = {sources:[]}, ledger = {evidence_register:{transformations:[]}};
const freshDatasets = [{dataset_id:'d',title:'New title',terms_hash:'OLD'}];
const recoveryValues = {title:'New title',terms_hash:'UNSENT'}, recoveryOriginalValues = {title:'Old title',terms_hash:'OLD'};
const sentRecoveryKeys = new Set(['title']);
let values, baseline;
const setRecoveryValues = v => {values=v}, setRecoveryOriginalValues = v => {baseline=v};
""" + "\neval(ts.transpileModule(" + repr(block) + ", {compilerOptions:{target:ts.ScriptTarget.ES2022}}).outputText);"
        program += """
assert.deepEqual(values,{title:'New title',terms_hash:'UNSENT'});
assert.deepEqual(baseline,{title:'New title',terms_hash:'OLD'});
assert.deepEqual(Object.fromEntries(Object.entries(values).filter(([key,value]) => value !== baseline[key])), {terms_hash:'UNSENT'});
"""
        completed = subprocess.run(["node", "-e", program], cwd=SRC.parent, text=True, capture_output=True, timeout=10)
        self.assertEqual(completed.returncode, 0, completed.stderr)


if __name__ == "__main__":
    unittest.main()
