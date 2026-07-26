import { AlertTriangle, ArrowLeft, BadgeCheck, Database, FileText, RefreshCcw, Send, ShieldCheck, Sparkles, Target } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { fetchProjects } from "./api";
import type { Project } from "./contracts";
import {
  DIB_INTAKE_ITEM_GOVERNANCE_UI_ID,
  type DIBBlueprintItem,
  type DIBSessionRecord,
  applyDIBItemDecision,
  previewDIBIntakeItems,
  resolveDIBTemplateRegistry,
  saveDIBBlueprint,
  startDIBSession,
} from "./dibApi";

const forbiddenBoundaries = [
  "لا تشغيل Finance Engine من Package B",
  "لا إنشاء Snapshot أو Decision Pack",
  "لا تفعيل AI Provider",
  "لا جلب شبكي أو مصدر خارجي",
  "لا قبول raw prompt أو مفاتيح API أو ملف خام",
] as const;

function projectProfileFromProject(project: Project): Record<string, unknown> {
  const inputs = project.inputs;
  return {
    project_id: project.project_id,
    name: project.name,
    sector: project.sector,
    jurisdiction: project.jurisdiction,
    depth_profile: project.depth_profile,
    activity: inputs.activity_description || project.name,
    primary_sector_id: inputs.primary_sector_id || project.sector,
    location_country: inputs.location_country || "SA",
    location_region: inputs.location_region || "",
    location_city: inputs.location_city || "",
    location_district: inputs.location_district || "",
    source: "asie_user_project_context",
  };
}

function displayValue(item: DIBBlueprintItem): string {
  if (typeof item.value === "number") return item.value.toLocaleString("ar-SA");
  if (item.value === undefined || item.value === null || item.value === "") return "غير محدد";
  return String(item.value);
}

export function DIBIntakeItemGovernance() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState("");
  const [session, setSession] = useState<DIBSessionRecord | null>(null);
  const [templateId, setTemplateId] = useState("");
  const [templateItems, setTemplateItems] = useState<string[]>([]);
  const [questionsCount, setQuestionsCount] = useState(0);
  const [quoteText, setQuoteText] = useState("معدات وتجهيزات 120000\nإيجار شهري 18000\nرواتب شهرية 22000\nسعر الوجبة 18\nتكلفة مواد مباشرة 7\nعدد المبيعات الشهري 4200");
  const [items, setItems] = useState<DIBBlueprintItem[]>([]);
  const [unmatchedCount, setUnmatchedCount] = useState(0);
  const [operationBusy, setOperationBusy] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [savedBlueprintId, setSavedBlueprintId] = useState<string | null>(null);

  useEffect(() => {
    void loadProjects();
  }, []);

  const selectedProject = useMemo(
    () => projects.find((project) => project.project_id === selectedProjectId) ?? projects[0] ?? null,
    [projects, selectedProjectId]
  );
  const boundProfile = selectedProject ? projectProfileFromProject(selectedProject) : null;
  const canStart = Boolean(boundProfile && !session && !operationBusy);
  const canResolveTemplate = Boolean(session && !operationBusy);
  const canPreviewIntake = Boolean(session && quoteText.trim() && !operationBusy);
  const canSaveBlueprint = Boolean(session && items.length > 0 && !operationBusy);

  async function withOperation<T>(label: string, action: () => Promise<T>): Promise<T | null> {
    setOperationBusy(label);
    setErrorMessage(null);
    try {
      return await action();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "تعذر تنفيذ Package B");
      return null;
    } finally {
      setOperationBusy(null);
    }
  }

  async function loadProjects() {
    const loaded = await withOperation("load-projects", fetchProjects);
    if (!loaded) return;
    setProjects(loaded);
    setSelectedProjectId(loaded[0]?.project_id ?? "");
  }

  async function beginGovernanceSession() {
    if (!boundProfile) return;
    const started = await withOperation("start-session", () => startDIBSession(boundProfile));
    if (started) setSession(started);
  }

  async function resolveTemplate() {
    if (!session) return;
    const resolved = await withOperation("template-registry", () => resolveDIBTemplateRegistry(session.session_id, boundProfile ?? undefined));
    if (!resolved) return;
    setTemplateId(String(resolved.template_id));
    setTemplateItems(resolved.template_items ?? []);
    setQuestionsCount(resolved.questions?.length ?? 0);
  }

  async function previewSupplierQuote() {
    if (!session) return;
    const preview = await withOperation("supplier-quote-intake", () =>
      previewDIBIntakeItems(session.session_id, {
        source_name: `supplier-quote-${session.project_id}`,
        supplier_quote_text: quoteText,
        existing_items: items,
      })
    );
    if (!preview) return;
    setItems(preview.mapped_items);
    setUnmatchedCount(preview.unmatched_rows.length);
  }

  async function applyDecision(item: DIBBlueprintItem, action: "enter_value" | "mark_unknown" | "reject") {
    if (!session) return;
    const decision = await withOperation("customer-item-decision", () =>
      applyDIBItemDecision(session.session_id, item, {
        action,
        value: item.value,
        reason: action === "mark_unknown" ? "customer_requires_more_evidence" : "customer_reviewed_in_package_b",
      })
    );
    if (!decision) return;
    setItems((current) => current.map((row) => (row.input_key === item.input_key ? decision.item : row)));
  }

  async function persistGovernedBlueprint() {
    if (!session) return;
    const saved = await withOperation("save-governed-blueprint", () =>
      saveDIBBlueprint(session.session_id, {
        source: "dib_completion_package_b_intake_item_governance",
        items,
      })
    );
    if (saved?.payload.blueprint_id) setSavedBlueprintId(saved.payload.blueprint_id);
  }

  return (
    <main className="app-shell dib-workspace" dir="rtl" data-ui-id={DIB_INTAKE_ITEM_GOVERNANCE_UI_ID}>
      <section className="page-intro">
        <p className="eyebrow"><Sparkles size={16} aria-hidden="true" /> DIB Completion Package B · Intake & Item Governance</p>
        <h1>حوكمة الإدخال والبنود قبل Manifest</h1>
        <p>
          هذه الواجهة تضيف Template Registry UI، سطح إدخال حي، Supplier Quote Text Intake، وCustomer Item Decision Workflow. لا تشغل Finance، ولا تنشئ Snapshot، ولا تستخدم AI أو جلبًا خارجيًا.
        </p>
        {errorMessage ? <p className="error-banner"><AlertTriangle size={16} aria-hidden="true" /> {errorMessage}</p> : null}
        <div className="button-row">
          <a className="secondary-button" href="#dib"><ArrowLeft size={16} aria-hidden="true" /> العودة لمساحة DIB</a>
          <button type="button" className="secondary-button" onClick={() => void loadProjects()} disabled={Boolean(operationBusy)}><RefreshCcw size={16} aria-hidden="true" /> تحديث المشاريع</button>
          <button type="button" className="primary-button" onClick={() => void beginGovernanceSession()} disabled={!canStart}><Send size={16} aria-hidden="true" /> بدء جلسة حوكمة</button>
          <button type="button" onClick={() => void resolveTemplate()} disabled={!canResolveTemplate}>حل Template Registry</button>
          <button type="button" onClick={() => void previewSupplierQuote()} disabled={!canPreviewIntake}>معاينة عرض السعر</button>
          <button type="button" onClick={() => void persistGovernedBlueprint()} disabled={!canSaveBlueprint}>حفظ Blueprint محكوم</button>
        </div>
      </section>

      <section className="panel" aria-label="Project binding">
        <div className="section-title"><Target size={20} aria-hidden="true" /><h2>المشروع والجلسة</h2></div>
        <div className="button-row">
          <label htmlFor="governance-project-select">اختر مشروع ASIE</label>
          <select id="governance-project-select" value={selectedProject?.project_id ?? ""} onChange={(event) => setSelectedProjectId(event.target.value)} disabled={Boolean(session || operationBusy)}>
            {projects.map((project) => <option key={project.project_id} value={project.project_id}>{project.name} · {project.project_id}</option>)}
          </select>
        </div>
        <ul className="lineage-list">
          <li>project_id: <code>{selectedProject?.project_id ?? "لا يوجد"}</code></li>
          <li>session_id: <code>{session?.session_id ?? "لم تبدأ"}</code></li>
          <li>saved_blueprint_id: <code>{savedBlueprintId ?? "لم يحفظ"}</code></li>
        </ul>
      </section>

      <section className="dashboard-grid" aria-label="Package B metrics">
        <article className="metric-card"><span>Template Registry</span><strong>{templateId || "غير محلول"}</strong><small>{templateItems.length.toLocaleString("ar-SA")} بند من القالب</small></article>
        <article className="metric-card"><span>Question Registry</span><strong>{questionsCount.toLocaleString("ar-SA")}</strong><small>أسئلة مرجعية قبل الإدخال</small></article>
        <article className="metric-card"><span>Mapped Items</span><strong>{items.length.toLocaleString("ar-SA")}</strong><small>من Supplier Quote Text Intake</small></article>
        <article className="metric-card"><span>Unmatched Rows</span><strong>{unmatchedCount.toLocaleString("ar-SA")}</strong><small>تحتاج مراجعة بشرية</small></article>
      </section>

      <section className="panel" aria-label="Supplier Quote Text Intake">
        <div className="section-title"><FileText size={20} aria-hidden="true" /><h2>Supplier Quote Text Intake</h2></div>
        <p className="muted">أدخل نص عرض السعر بعد استخراجه. لا يتم إرسال ملف خام أو PDF base64، وإنما نص محكوم يتحول إلى صفوف وبنود قابلة للمراجعة.</p>
        <textarea value={quoteText} onChange={(event) => setQuoteText(event.target.value)} rows={8} style={{ width: "100%" }} />
      </section>

      <section className="panel" aria-label="Customer Item Decision Workflow">
        <div className="section-title"><ShieldCheck size={20} aria-hidden="true" /><h2>Customer Item Decision Workflow</h2></div>
        <div className="remediation-list">
          {items.map((item) => (
            <article key={item.input_key}>
              <strong>{item.label}</strong>
              <span>{item.input_key} · {item.value_state} · {displayValue(item)}</span>
              <small>{(item.evidence_refs ?? []).join(" · ") || "supplier_quote_text"}</small>
              <div className="button-row">
                <button type="button" onClick={() => void applyDecision(item, "enter_value")}><BadgeCheck size={15} aria-hidden="true" /> اعتماد القيمة</button>
                <button type="button" onClick={() => void applyDecision(item, "mark_unknown")}>يحتاج دليل</button>
                <button type="button" onClick={() => void applyDecision(item, "reject")}>رفض البند</button>
              </div>
            </article>
          ))}
          {items.length === 0 ? <p className="muted">ابدأ جلسة، ثم حل Template Registry، ثم عاين عرض السعر حتى تظهر البنود هنا.</p> : null}
        </div>
      </section>

      <section className="decision-command__grid" aria-label="Package B boundaries">
        <article className="panel">
          <div className="section-title"><Database size={20} aria-hidden="true" /><h2>مسارات Package B</h2></div>
          <ul className="lineage-list">
            <li><code>POST /api/dib/sessions/{session_id}/template-registry</code></li>
            <li><code>POST /api/dib/sessions/{session_id}/intake-items</code></li>
            <li><code>POST /api/dib/sessions/{session_id}/item-decisions</code></li>
          </ul>
        </article>
        <article className="panel">
          <div className="section-title"><ShieldCheck size={20} aria-hidden="true" /><h2>الممنوع</h2></div>
          <ul className="lineage-list">
            {forbiddenBoundaries.map((item) => <li key={item}>{item}</li>)}
          </ul>
        </article>
      </section>
    </main>
  );
}
