import {
  AlertTriangle,
  ArrowLeft,
  BadgeCheck,
  CheckCircle2,
  Database,
  FileText,
  Layers3,
  RefreshCcw,
  Send,
  ShieldCheck,
  Sparkles,
  Target,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { fetchProjects } from "./api";
import type { Project, ProjectInputs } from "./contracts";
import {
  DIB_UI_LIVE_API_WIRING_ID,
  type DIBApprovedManifestPayload,
  type DIBBlueprintItem,
  type DIBBlueprintPayload,
  type DIBEventRecord,
  type DIBItemState,
  type DIBPersistedEntity,
  type DIBSessionRecord,
  type DIBStatusPayload,
  type DIBValidationGatePayload,
  closeDIBSession,
  fetchDIBEvents,
  fetchDIBSession,
  fetchDIBStatus,
  saveDIBApprovedManifest,
  saveDIBBlueprint,
  saveDIBValidationGate,
  startDIBSession,
} from "./dibApi";

const DIB_UI_ID = "DIB-LIVE-002E-ARABIC-UI-WORKSPACE-v1";
const DIB_UI_PROJECT_CONTEXT_BINDING_ID = "DIB-LIVE-002K-USER-PROJECT-CONTEXT-BINDING-v1";

const dibApiRoutes = [
  "GET /api/dib/status",
  "POST /api/dib/sessions",
  "GET /api/dib/sessions/{session_id}",
  "POST /api/dib/sessions/{session_id}/blueprints",
  "POST /api/dib/sessions/{session_id}/approved-manifests",
  "POST /api/dib/sessions/{session_id}/validation-gates",
  "GET /api/dib/sessions/{session_id}/events",
  "POST /api/dib/sessions/{session_id}/close",
] as const;

const forbiddenBoundaries = [
  "لا تشغيل Finance Engine من هذه الواجهة",
  "لا إنشاء Snapshot أو Decision Pack",
  "لا تفعيل AI Provider",
  "لا جلب شبكي أو مصدر خارجي",
  "لا قبول raw prompt أو مفاتيح API",
] as const;

const requiredFinanceInputKeys = ["startup_cost", "monthly_fixed_cost", "unit_price", "variable_cost", "monthly_units"] as const;
const recommendedProjectInputKeys = ["capex_equipment", "rent_monthly", "payroll_monthly", "utilities_monthly"] as const;

const inputLabels: Record<string, string> = {
  startup_cost: "تكلفة التأسيس",
  monthly_fixed_cost: "التكاليف الشهرية الثابتة",
  unit_price: "سعر الوحدة / الوجبة",
  variable_cost: "التكلفة المتغيرة للوحدة",
  monthly_units: "عدد الوحدات الشهري",
  capex_equipment: "معدات المشروع",
  rent_monthly: "الإيجار الشهري",
  payroll_monthly: "الرواتب الشهرية",
  utilities_monthly: "المرافق الشهرية",
};

const currencyInputKeys = new Set(["startup_cost", "monthly_fixed_cost", "unit_price", "variable_cost", "capex_equipment", "rent_monthly", "payroll_monthly", "utilities_monthly"]);

function hashProjectIdFromLocation(): string {
  try {
    const fromSearch = new URLSearchParams(window.location.search).get("project_id");
    if (fromSearch?.trim()) return fromSearch.trim();
    const [, hashQuery = ""] = window.location.hash.split("?", 2);
    const fromHash = new URLSearchParams(hashQuery).get("project_id");
    return fromHash?.trim() ?? "";
  } catch {
    return "";
  }
}

function asRecord(inputs: ProjectInputs): Record<string, unknown> {
  return inputs as Record<string, unknown>;
}

function asNumber(value: unknown): number | undefined {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string" && value.trim()) {
    const numeric = Number(value.replace(/[^0-9.-]/g, ""));
    return Number.isFinite(numeric) ? numeric : undefined;
  }
  return undefined;
}

function itemStateForProjectInput(inputs: ProjectInputs, inputKey: string): DIBItemState {
  const rawInputs = asRecord(inputs);
  if (!(inputKey in rawInputs)) return "UNKNOWN";
  const value = asNumber(rawInputs[inputKey]);
  if (value === undefined) return "UNKNOWN";
  if (value === 0) return "INTENTIONAL_ZERO";
  return "USER_PROVIDED";
}

function projectInputItem(project: Project, inputKey: string, required: boolean): DIBBlueprintItem {
  const rawInputs = asRecord(project.inputs);
  const value = asNumber(rawInputs[inputKey]);
  const state = itemStateForProjectInput(project.inputs, inputKey);
  return {
    input_key: inputKey,
    label: inputLabels[inputKey] ?? inputKey,
    value_state: state,
    value,
    unit: inputKey === "monthly_units" ? "unit" : currencyInputKeys.has(inputKey) ? "SAR" : "unit",
    evidence_refs: [`project_context:${project.project_id}:${inputKey}`],
    source_type: "project_context",
    value_source: "asie_project_inputs",
    review_status: state === "UNKNOWN" ? "draft" : "approved",
    required,
    reason: state === "UNKNOWN" ? "missing_from_user_project_context" : "bound_from_user_project_context",
  };
}

function itemsFromProject(project: Project | null): DIBBlueprintItem[] {
  if (!project) return [];
  return [
    ...requiredFinanceInputKeys.map((key) => projectInputItem(project, key, true)),
    ...recommendedProjectInputKeys.map((key) => projectInputItem(project, key, false)),
  ];
}

function formatCurrency(value: number | string | null | undefined, unit?: string): string {
  if (typeof value !== "number") return value ? String(value) : "غير محدد";
  if (unit === "unit") return value.toLocaleString("ar-SA");
  return new Intl.NumberFormat("ar-SA", { style: "currency", currency: "SAR", maximumFractionDigits: 0 }).format(value);
}

function arabicState(state: DIBItemState): string {
  const labels: Record<DIBItemState, string> = {
    UNKNOWN: "غير مكتمل",
    NOT_APPLICABLE: "غير منطبق",
    USER_PROVIDED: "مدخل من المستخدم",
    FILE_IMPORTED: "مستورد من ملف",
    AI_SUGGESTED: "مقترح واجهة فقط",
    MARKET_ESTIMATED: "تقدير سوقي محلي",
    EVIDENCE_VERIFIED: "موثق بدليل",
    HUMAN_APPROVED: "معتمد بشريًا",
    REJECTED: "مرفوض",
    INTENTIONAL_ZERO: "صفر مقصود",
  };
  return labels[state];
}

function eventLabel(eventType: string): string {
  const labels: Record<string, string> = {
    "session.started": "بدأت الجلسة",
    "blueprint.saved": "تم حفظ Blueprint",
    "manifest.saved": "تم حفظ Manifest",
    "validation_gate.saved": "تم حفظ Validation Gate",
    "session.closed": "تم إغلاق الجلسة",
  };
  return labels[eventType] ?? eventType;
}

function projectProfileFromProject(project: Project) {
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
    location_scope: inputs.location_scope || "project_context",
    intake_mode: inputs.intake_mode || "project_context_binding",
    source: "asie_user_project_context",
  };
}

export function DIBWorkspace() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState("");
  const [items, setItems] = useState<DIBBlueprintItem[]>([]);
  const [status, setStatus] = useState<DIBStatusPayload | null>(null);
  const [session, setSession] = useState<DIBSessionRecord | null>(null);
  const [blueprint, setBlueprint] = useState<DIBPersistedEntity<DIBBlueprintPayload> | null>(null);
  const [manifest, setManifest] = useState<DIBPersistedEntity<DIBApprovedManifestPayload> | null>(null);
  const [validationGate, setValidationGate] = useState<DIBPersistedEntity<DIBValidationGatePayload> | null>(null);
  const [events, setEvents] = useState<DIBEventRecord[]>([]);
  const [operationBusy, setOperationBusy] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    void loadDIBStatus();
    void loadUserProjects();
  }, []);

  const selectedProject = useMemo(
    () => projects.find((project) => project.project_id === selectedProjectId) ?? projects[0] ?? null,
    [projects, selectedProjectId]
  );
  const boundProjectProfile = selectedProject ? projectProfileFromProject(selectedProject) : null;
  const visibleItems = blueprint?.payload.items ?? session?.current_blueprint?.items ?? items;
  const approvedManifest = manifest?.payload ?? session?.approved_manifest ?? null;
  const gatePayload = validationGate?.payload ?? session?.validation_gate ?? null;
  const sessionStatus = session?.status ?? "not_started";
  const approvedCount = visibleItems.filter((item) => item.value_state !== "UNKNOWN" && item.value_state !== "REJECTED").length;
  const blockedCount = visibleItems.filter((item) => item.value_state === "UNKNOWN" || item.value_state === "REJECTED").length;
  const canBeginSession = Boolean(selectedProject && !operationBusy);
  const canSaveBlueprint = Boolean(session && selectedProject && !operationBusy);
  const canApproveManifest = Boolean(session && (blueprint || session.current_blueprint) && !operationBusy);
  const canRunGate = Boolean(session && approvedManifest?.status === "approved" && !operationBusy);

  const timeline = useMemo(
    () => [
      { label: "User Project Context", status: selectedProject ? selectedProject.project_id : "لا يوجد مشروع", done: Boolean(selectedProject) },
      { label: "DIB Session", status: sessionStatus, done: Boolean(session) },
      {
        label: "Dynamic Input Blueprint",
        status: blueprint || session?.current_blueprint ? "saved" : "ينتظر الحفظ عبر API",
        done: Boolean(blueprint || session?.current_blueprint),
      },
      {
        label: "Approved Input Manifest",
        status: approvedManifest?.status ?? "لم يعتمد بعد",
        done: approvedManifest?.status === "approved",
      },
      {
        label: "Manifest Validation Gate",
        status: gatePayload?.status ?? "لم يعمل بعد",
        done: gatePayload?.status === "passed",
      },
    ],
    [approvedManifest?.status, blueprint, gatePayload?.status, selectedProject, session, sessionStatus]
  );

  async function withOperation<T>(label: string, action: () => Promise<T>): Promise<T | null> {
    setOperationBusy(label);
    setErrorMessage(null);
    try {
      return await action();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "تعذر تنفيذ عملية DIB");
      return null;
    } finally {
      setOperationBusy(null);
    }
  }

  async function loadDIBStatus() {
    const result = await withOperation("status", fetchDIBStatus);
    if (result) setStatus(result);
  }

  async function loadUserProjects() {
    const loaded = await withOperation("load-projects", fetchProjects);
    if (!loaded) return;
    setProjects(loaded);
    const requestedProjectId = hashProjectIdFromLocation();
    const nextProject = loaded.find((project) => project.project_id === requestedProjectId) ?? loaded[0] ?? null;
    setSelectedProjectId(nextProject?.project_id ?? "");
    setItems(itemsFromProject(nextProject));
    setSession(null);
    setBlueprint(null);
    setManifest(null);
    setValidationGate(null);
    setEvents([]);
  }

  function selectProject(projectId: string) {
    const nextProject = projects.find((project) => project.project_id === projectId) ?? null;
    setSelectedProjectId(nextProject?.project_id ?? "");
    setItems(itemsFromProject(nextProject));
    setSession(null);
    setBlueprint(null);
    setManifest(null);
    setValidationGate(null);
    setEvents([]);
  }

  async function refreshSession(nextSessionId = session?.session_id) {
    if (!nextSessionId) return;
    const loaded = await fetchDIBSession(nextSessionId);
    setSession(loaded);
    if (loaded.current_blueprint) setBlueprint({ payload: loaded.current_blueprint });
    if (loaded.approved_manifest) setManifest({ payload: loaded.approved_manifest });
    if (loaded.validation_gate) setValidationGate({ payload: loaded.validation_gate });
    setEvents(await fetchDIBEvents(nextSessionId));
  }

  async function beginSession() {
    if (!boundProjectProfile) return;
    const started = await withOperation("start-session", () => startDIBSession(boundProjectProfile));
    if (!started) return;
    setSession(started);
    setBlueprint(null);
    setManifest(null);
    setValidationGate(null);
    await refreshSession(started.session_id);
  }

  async function persistBlueprint() {
    if (!session) return;
    const saved = await withOperation("save-blueprint", () =>
      saveDIBBlueprint(session.session_id, {
        source: "dib_ui_user_project_context_binding",
        intake_payload: {
          file_name: `project-context-${selectedProject?.project_id ?? session.project_id}`,
          rows: items.map((item) => ({ input_key: item.input_key, label: item.label, value: item.value ?? "" })),
        },
      })
    );
    if (!saved) return;
    setBlueprint(saved);
    await refreshSession(session.session_id);
  }

  async function persistManifest() {
    if (!session) return;
    const saved = await withOperation("approve-manifest", () => saveDIBApprovedManifest(session.session_id));
    if (!saved) return;
    setManifest(saved);
    await refreshSession(session.session_id);
  }

  async function persistValidationGate() {
    if (!session) return;
    const saved = await withOperation("validation-gate", () => saveDIBValidationGate(session.session_id));
    if (!saved) return;
    setValidationGate(saved);
    await refreshSession(session.session_id);
  }

  async function closeSession() {
    if (!session) return;
    const closed = await withOperation("close-session", () => closeDIBSession(session.session_id));
    if (!closed) return;
    setSession(closed);
    await refreshSession(closed.session_id);
  }

  function updateItemValue(inputKey: string, value: string) {
    setItems((current) =>
      current.map((item) => {
        if (item.input_key !== inputKey) return item;
        const numeric = Number(value);
        return {
          ...item,
          value: value === "" || Number.isNaN(numeric) ? undefined : numeric,
          value_state: value === "" ? "UNKNOWN" : numeric === 0 ? "INTENTIONAL_ZERO" : "USER_PROVIDED",
          review_status: value === "" ? "draft" : "approved",
          source_type: "project_context_override",
          value_source: "user_project_context_override",
        };
      })
    );
  }

  function approveItem(inputKey: string) {
    setItems((current) =>
      current.map((item) =>
        item.input_key === inputKey
          ? {
              ...item,
              value_state: item.value === 0 ? "INTENTIONAL_ZERO" : "USER_PROVIDED",
              review_status: "approved",
              value_source: item.value_source || "asie_project_inputs",
              source_type: item.source_type || "project_context",
            }
          : item
      )
    );
  }

  function blockItem(inputKey: string) {
    setItems((current) =>
      current.map((item) =>
        item.input_key === inputKey
          ? {
              ...item,
              value_state: "UNKNOWN",
              review_status: "draft",
              reason: "customer_requires_revision_before_manifest",
            }
          : item
      )
    );
  }

  return (
    <main id="main-content" className="app-shell dib-workspace" dir="rtl" data-ui-id={DIB_UI_PROJECT_CONTEXT_BINDING_ID} data-parent-ui-id={DIB_UI_ID} data-live-api-id={DIB_UI_LIVE_API_WIRING_ID}>
      <section className="page-intro">
        <p className="eyebrow"><Sparkles size={16} aria-hidden="true" /> DIB-LIVE-002K · ربط DIB بسياق مشروع المستخدم</p>
        <h1>مساحة Dynamic Input Blueprint</h1>
        <p>
          هذه الواجهة تقرأ مشاريع ASIE الفعلية من <code>/api/projects</code>، وتبدأ DIB Session باستخدام <code>project_id</code> وبيانات المشروع المختار. لا تشغل الحساب المالي، ولا تنشئ Snapshot، ولا تستخدم AI أو شبكة خارجية.
        </p>
        {errorMessage ? <p className="error-banner"><AlertTriangle size={16} aria-hidden="true" /> {errorMessage}</p> : null}
        <div className="button-row">
          <a className="secondary-button" href="#dashboard"><ArrowLeft size={16} aria-hidden="true" /> العودة للمنصة</a>
          <button type="button" className="secondary-button" onClick={() => void loadDIBStatus()} disabled={Boolean(operationBusy)}><RefreshCcw size={16} aria-hidden="true" /> تحديث حالة DIB</button>
          <button type="button" className="secondary-button" onClick={() => void loadUserProjects()} disabled={Boolean(operationBusy)}><RefreshCcw size={16} aria-hidden="true" /> تحديث المشاريع</button>
          <button type="button" className="primary-button" onClick={() => void beginSession()} disabled={!canBeginSession}><Send size={16} aria-hidden="true" /> بدء Session للمشروع</button>
          <button type="button" disabled={!canSaveBlueprint} onClick={() => void persistBlueprint()}>حفظ Blueprint عبر API</button>
          <button type="button" disabled={!canApproveManifest} onClick={() => void persistManifest()}>اعتماد Manifest عبر API</button>
          <button type="button" disabled={!canRunGate} onClick={() => void persistValidationGate()}>تشغيل Validation Gate عبر API</button>
          <button type="button" disabled={!session || Boolean(operationBusy)} onClick={() => void closeSession()}>إغلاق Session</button>
        </div>
      </section>

      <section className="panel" aria-label="سياق مشروع المستخدم">
        <div className="section-title"><Target size={20} aria-hidden="true" /><h2>المشروع المرتبط</h2></div>
        {projects.length > 0 ? (
          <div className="button-row">
            <label htmlFor="dib-project-select">اختر مشروع ASIE</label>
            <select id="dib-project-select" value={selectedProject?.project_id ?? ""} onChange={(event) => selectProject(event.target.value)} disabled={Boolean(operationBusy || session)}>
              {projects.map((project) => (
                <option key={project.project_id} value={project.project_id}>{project.name} · {project.project_id}</option>
              ))}
            </select>
          </div>
        ) : <p className="muted">لا توجد مشاريع متاحة. أنشئ مشروعًا أولًا من منصة ASIE ثم عد إلى هذه المساحة.</p>}
        {selectedProject ? (
          <ul className="lineage-list">
            <li>project_id: <code>{selectedProject.project_id}</code></li>
            <li>name: {selectedProject.name}</li>
            <li>sector: {selectedProject.sector}</li>
            <li>jurisdiction: {selectedProject.jurisdiction}</li>
            <li>intake_mode: <code>{selectedProject.inputs.intake_mode ?? "غير محدد"}</code></li>
          </ul>
        ) : null}
      </section>

      <section className="dashboard-grid" aria-label="مؤشرات DIB">
        <article className="metric-card"><span>حالة الجلسة</span><strong>{sessionStatus}</strong><small>{session?.session_id ?? "لم تبدأ بعد"}</small></article>
        <article className="metric-card"><span>المشروع</span><strong>{selectedProject ? "مرتبط" : "غير مرتبط"}</strong><small>{selectedProject?.project_id ?? "لا يوجد project_id"}</small></article>
        <article className="metric-card"><span>البنود القابلة للـManifest</span><strong>{approvedCount.toLocaleString("ar-SA")}</strong><small>تدخل في Approved Input Manifest فقط</small></article>
        <article className="metric-card"><span>Gateway</span><strong>{status?.local_gateway_integration_id ? "Sidecar" : "status فقط"}</strong><small>finance_wiring_enabled=false</small></article>
      </section>

      <section className="panel" aria-label="مسار DIB">
        <div className="section-title"><Layers3 size={20} aria-hidden="true" /><h2>مسار DIB قبل Finance</h2></div>
        <div className="workflow-steps">
          {timeline.map((step, index) => (
            <article className={step.done ? "workflow-step workflow-step--done" : "workflow-step"} key={step.label}>
              <span>{index + 1}</span>
              <strong>{step.label}</strong>
              <small>{step.status}</small>
            </article>
          ))}
        </div>
      </section>

      <section className="panel" aria-label="بنود Dynamic Input Blueprint">
        <div className="section-title"><Target size={20} aria-hidden="true" /><h2>بنود Blueprint من سياق المشروع</h2></div>
        <div className="remediation-list">
          {items.map((item) => (
            <article key={item.input_key}>
              <strong>{item.label}</strong>
              <span>{item.input_key} · {arabicState(item.value_state)} · {formatCurrency(item.value, item.unit)}</span>
              <small>{(item.evidence_refs ?? ["project_context"]).join(" · ")}</small>
              <div className="button-row">
                <input aria-label={`قيمة ${item.label}`} type="number" value={item.value ?? ""} onChange={(event) => updateItemValue(item.input_key, event.target.value)} />
                <button type="button" onClick={() => approveItem(item.input_key)}><CheckCircle2 size={15} aria-hidden="true" /> اعتماد البند</button>
                <button type="button" onClick={() => blockItem(item.input_key)}><ShieldCheck size={15} aria-hidden="true" /> يحتاج تعديل</button>
              </div>
            </article>
          ))}
          {items.length === 0 ? <p className="muted">اختر مشروعًا حتى يتم توليد بنود Blueprint من مدخلاته.</p> : null}
        </div>
      </section>

      <section className="panel" aria-label="آخر Blueprint محفوظ">
        <div className="section-title"><Database size={20} aria-hidden="true" /><h2>آخر Blueprint من API</h2></div>
        {blueprint?.payload ? (
          <ul className="lineage-list">
            <li><code>{blueprint.payload.contract_id}</code></li>
            <li>blueprint_id: <code>{blueprint.payload.blueprint_id}</code></li>
            <li>items: {blueprint.payload.items.length.toLocaleString("ar-SA")}</li>
          </ul>
        ) : <p className="muted">لم يتم حفظ Blueprint بعد.</p>}
      </section>

      <section className="decision-command__grid" aria-label="Manifest وValidation">
        <article className="panel">
          <div className="section-title"><BadgeCheck size={20} aria-hidden="true" /><h2>Approved Input Manifest</h2></div>
          {approvedManifest ? (
            <ul className="lineage-list">
              <li>status: <code>{approvedManifest.status}</code></li>
              <li>manifest_id: <code>{approvedManifest.manifest_id}</code></li>
              <li>blockers: {(approvedManifest.blockers ?? []).length.toLocaleString("ar-SA")}</li>
            </ul>
          ) : <p className="muted">لم يعتمد Manifest بعد.</p>}
        </article>
        <article className="panel">
          <div className="section-title"><ShieldCheck size={20} aria-hidden="true" /><h2>Manifest Validation Gate</h2></div>
          {gatePayload ? (
            <ul className="lineage-list">
              <li>status: <code>{gatePayload.status}</code></li>
              <li>gate_id: <code>{gatePayload.gate_id}</code></li>
              <li>blockers: {(gatePayload.blockers ?? []).length.toLocaleString("ar-SA")}</li>
            </ul>
          ) : <p className="muted">لم يعمل Validation Gate بعد.</p>}
        </article>
      </section>

      <section className="decision-command__grid" aria-label="حدود الواجهة وعقود API">
        <article className="panel">
          <div className="section-title"><Database size={20} aria-hidden="true" /><h2>واجهات API الفعلية</h2></div>
          <ul className="lineage-list">
            {dibApiRoutes.map((route) => <li key={route}><code>{route}</code></li>)}
          </ul>
          <p className="muted">الواجهة متصلة عبر Nginx إلى DIB Sidecar؛ المصادقة تمر من طبقة API الأمامية باستخدام Bearer token.</p>
        </article>
        <article className="panel">
          <div className="section-title"><FileText size={20} aria-hidden="true" /><h2>الممنوع في هذه المرحلة</h2></div>
          <ul className="lineage-list">
            {forbiddenBoundaries.map((item) => <li key={item}><BadgeCheck size={15} aria-hidden="true" /> {item}</li>)}
          </ul>
        </article>
      </section>

      <section className="panel" aria-label="سجل أحداث DIB">
        <div className="section-title"><FileText size={20} aria-hidden="true" /><h2>أحداث DIB</h2></div>
        <ul className="lineage-list">
          {events.map((event) => <li key={event.event_id}>{eventLabel(event.event_type)} · <code>{event.payload_hash}</code></li>)}
        </ul>
        {events.length === 0 ? <p className="muted">لا توجد أحداث بعد.</p> : null}
      </section>
    </main>
  );
}
