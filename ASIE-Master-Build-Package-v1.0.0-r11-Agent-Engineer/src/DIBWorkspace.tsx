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
import { useEffect, useMemo, useRef, useState } from "react";
import { fetchProjects } from "./api";
import type { Project, ProjectInputs } from "./contracts";
import {
  DIB_SESSION_CONTINUITY_UI_ID,
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
  fetchDIBSessionsForProject,
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
  "GET /api/dib/sessions?project_id={project_id}",
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

const currencyInputKeys = new Set([
  "startup_cost",
  "monthly_fixed_cost",
  "unit_price",
  "variable_cost",
  "capex_equipment",
  "rent_monthly",
  "payroll_monthly",
  "utilities_monthly",
]);

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

function shortDate(value?: string): string {
  if (!value) return "غير معروف";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString("ar-SA", { dateStyle: "medium", timeStyle: "short" });
}

export function DIBWorkspace() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setProjectState] = useState("");
  const [items, setItems] = useState<DIBBlueprintItem[]>([]);
  const [status, setStatus] = useState<DIBStatusPayload | null>(null);
  const [session, setSessionState] = useState<DIBSessionRecord | null>(null);
  const requestScope = useRef({ project: selectedProjectId, session: session?.session_id, origin: session?.origin_reference?.payload_hash, epoch: 0 });
  const operationSequence = useRef(0);
  function setSelectedProjectId(project: string) {
    if (requestScope.current.project !== project) {
      requestScope.current = { ...requestScope.current, project, epoch: requestScope.current.epoch + 1 };
    }
    setProjectState(project);
  }
  function setSession(next: DIBSessionRecord | null) {
    if (requestScope.current.session !== next?.session_id || requestScope.current.origin !== next?.origin_reference?.payload_hash) {
      requestScope.current = { ...requestScope.current, session: next?.session_id, origin: next?.origin_reference?.payload_hash, epoch: requestScope.current.epoch + 1 };
    }
    setSessionState(next);
  }
  useEffect(() => () => { requestScope.current.epoch += 1; }, []);

  const [resumableSessions, setResumableSessions] = useState<DIBSessionRecord[]>([]);
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
  const visibleItems = items;
  const approvedManifest = manifest?.payload ?? session?.approved_manifest ?? null;
  const gatePayload = validationGate?.payload ?? session?.validation_gate ?? null;
  const latestResumeSession = resumableSessions[0] ?? null;
  const sessionStatus = session?.status ?? "not_started";
  const approvedCount = visibleItems.filter((item) => item.value_state !== "UNKNOWN" && item.value_state !== "REJECTED").length;
  const blockedCount = visibleItems.filter((item) => item.value_state === "UNKNOWN" || item.value_state === "REJECTED").length;
  const hasUnsavedItems = Boolean(session && JSON.stringify(items) !== JSON.stringify(session.current_blueprint?.items ?? itemsFromProject(selectedProject)));
  const canBeginSession = Boolean(selectedProject && !operationBusy && !hasUnsavedItems);
  const canResumeSession = Boolean(latestResumeSession && !session && !operationBusy);
  const legacyReadOnly = Boolean(session?.current_blueprint && !session.origin_reference);
  const canSaveBlueprint = Boolean(session && selectedProject && !operationBusy && !legacyReadOnly);
  const canApproveManifest = Boolean(session && (blueprint || session.current_blueprint) && !operationBusy && !hasUnsavedItems && !legacyReadOnly);
  const canRunGate = Boolean(session && approvedManifest?.status === "approved" && !operationBusy && !hasUnsavedItems && !legacyReadOnly);

  const timeline = useMemo(
    () => [
      { label: "User Project Context", status: selectedProject ? selectedProject.project_id : "لا يوجد مشروع", done: Boolean(selectedProject) },
      { label: "DIB Session Continuity", status: resumableSessions.length ? `${resumableSessions.length} جلسة قابلة للاستئناف` : "لا توجد جلسة سابقة", done: resumableSessions.length > 0 || Boolean(session) },
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
    [approvedManifest?.status, blueprint, gatePayload?.status, selectedProject, session, sessionStatus, resumableSessions.length]
  );

  async function withOperation<T>(label: string, action: () => Promise<T>): Promise<T | null> {
    setOperationBusy(label);
    setErrorMessage(null);
    const epoch = requestScope.current.epoch;
    const operation = ++operationSequence.current;
    try {
      const result = await action();
      return requestScope.current.epoch === epoch ? result : null;
    } catch (error) {
      if (requestScope.current.epoch !== epoch) return null;
      setErrorMessage(error instanceof Error ? error.message : "تعذر تنفيذ عملية DIB");
      return null;
    } finally {
      if (operationSequence.current === operation) setOperationBusy(null);
    }
  }

  function clearLiveSessionState(project: Project | null) {
    setItems(itemsFromProject(project));
    setSession(null);
    setBlueprint(null);
    setManifest(null);
    setValidationGate(null);
    setEvents([]);
  }

  function restoreSessionState(loaded: DIBSessionRecord, project: Project | null = selectedProject) {
    setSession(loaded);
    setBlueprint(loaded.current_blueprint ? { payload: loaded.current_blueprint, origin_reference: loaded.origin_reference ?? undefined, payload_hash: loaded.origin_reference?.payload_hash } : null);
    setManifest(loaded.approved_manifest ? { payload: loaded.approved_manifest } : null);
    setValidationGate(loaded.validation_gate ? { payload: loaded.validation_gate } : null);
    setItems(loaded.current_blueprint?.items ?? itemsFromProject(project));
  }

  async function loadDIBStatus() {
    const result = await withOperation("status", fetchDIBStatus);
    if (result) setStatus(result);
  }

  async function loadProjectSessions(projectId: string) {
    if (!projectId) {
      setResumableSessions([]);
      return;
    }
    const loaded = await withOperation("load-project-sessions", () => fetchDIBSessionsForProject(projectId));
    if (loaded) setResumableSessions(loaded);
  }

  async function loadUserProjects() {
    if (hasUnsavedItems) return;
    const loaded = await withOperation("load-projects", fetchProjects);
    if (!loaded) return;
    setProjects(loaded);
    const requestedProjectId = hashProjectIdFromLocation();
    const nextProject = loaded.find((project) => project.project_id === requestedProjectId) ?? loaded[0] ?? null;
    setSelectedProjectId(nextProject?.project_id ?? "");
    clearLiveSessionState(nextProject);
    if (nextProject) void loadProjectSessions(nextProject.project_id);
    else setResumableSessions([]);
  }

  function selectProject(projectId: string) {
    const nextProject = projects.find((project) => project.project_id === projectId) ?? null;
    setSelectedProjectId(nextProject?.project_id ?? "");
    clearLiveSessionState(nextProject);
    if (nextProject) void loadProjectSessions(nextProject.project_id);
    else setResumableSessions([]);
  }

  async function readSessionState(id: string) {
    const loaded = await fetchDIBSession(id);
    const loadedEvents = await fetchDIBEvents(id);
    return { loaded, loadedEvents };
  }

  function applySessionState(result: { loaded: DIBSessionRecord; loadedEvents: typeof events }) {
    restoreSessionState(result.loaded);
    setEvents(result.loadedEvents);
  }

  async function refreshSession(nextSessionId = session?.session_id) {
    if (!nextSessionId || hasUnsavedItems) return;
    const result = await withOperation("refresh-session", () => readSessionState(nextSessionId));
    if (result) applySessionState(result);
  }

  async function resumeSession(sessionId: string) {
    const result = await withOperation("resume-session", () => readSessionState(sessionId));
    if (result) applySessionState(result);
  }

  async function beginSession() {
    if (!boundProjectProfile || hasUnsavedItems) return;
    const result = await withOperation("start-session", async () => {
      const started = await startDIBSession(boundProjectProfile);
      return { ...await readSessionState(started.session_id), sessions: await fetchDIBSessionsForProject(started.project_id) };
    });
    if (result) { applySessionState(result); setResumableSessions(result.sessions); }
  }

  async function persistBlueprint() {
    if (!session || legacyReadOnly) return;
    const result = await withOperation("save-blueprint", async () => {
      const saved = await saveDIBBlueprint(session.session_id, {
        source: "dib_ui_user_project_context_binding",
        expected_original: session.origin_reference ?? null,
        ...(session.origin_reference ? { items } : { intake_payload: {
          file_name: `project-context-${selectedProject?.project_id ?? session.project_id}`,
          rows: items.map((item) => ({ input_key: item.input_key, label: item.label, value: item.value ?? "" })),
        } }),
      });
      const loaded = await fetchDIBSession(session.session_id);
      if (!saved.origin_reference || !loaded.origin_reference ||
          saved.origin_reference.payload_hash !== loaded.origin_reference.payload_hash ||
          saved.origin_reference.blueprint_id !== loaded.origin_reference.blueprint_id ||
          saved.origin_reference.revision !== loaded.origin_reference.revision) {
        throw new Error("تغيرت البيانات بعد الحفظ. احتُفظ بالتعديلات الحالية؛ أعد تحميل النسخة قبل المتابعة.");
      }
      return { saved, loaded };
    });
    if (!result) return;
    restoreSessionState(result.loaded);
    setBlueprint(result.saved);
  }

  async function persistManifest() {
    if (!session || legacyReadOnly || hasUnsavedItems) return;
    const result = await withOperation("approve-manifest", async () => {
      await saveDIBApprovedManifest(session.session_id);
      return { ...await readSessionState(session.session_id), sessions: await fetchDIBSessionsForProject(session.project_id) };
    });
    if (result) { applySessionState(result); setResumableSessions(result.sessions); }
  }

  async function persistValidationGate() {
    if (!session || legacyReadOnly || hasUnsavedItems) return;
    const result = await withOperation("validation-gate", async () => {
      await saveDIBValidationGate(session.session_id);
      return { ...await readSessionState(session.session_id), sessions: await fetchDIBSessionsForProject(session.project_id) };
    });
    if (result) { applySessionState(result); setResumableSessions(result.sessions); }
  }

  async function closeSession() {
    if (!session || legacyReadOnly || hasUnsavedItems) return;
    const result = await withOperation("close-session", async () => {
      const closed = await closeDIBSession(session.session_id);
      return { ...await readSessionState(closed.session_id), sessions: await fetchDIBSessionsForProject(closed.project_id) };
    });
    if (result) { applySessionState(result); setResumableSessions(result.sessions); }
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
          reason: numeric === 0 && item.value_state !== "INTENTIONAL_ZERO" ? "" : item.reason,
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
              reason: item.value === 0 && item.value_state !== "INTENTIONAL_ZERO" ? "" : item.reason,
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
    <main
      id="main-content"
      className="app-shell dib-workspace"
      dir="rtl"
      data-ui-id={DIB_UI_PROJECT_CONTEXT_BINDING_ID}
      data-parent-ui-id={DIB_UI_ID}
      data-live-api-id={DIB_UI_LIVE_API_WIRING_ID}
      data-session-continuity-id={DIB_SESSION_CONTINUITY_UI_ID}
    >
      <section className="page-intro">
        <p className="eyebrow"><Sparkles size={16} aria-hidden="true" /> DIB Completion Package A · Session Continuity</p>
        <h1>مساحة Dynamic Input Blueprint</h1>
        <p>
          هذه الواجهة تقرأ مشاريع ASIE الفعلية من <code>/api/projects</code>، وتفتح أو تستأنف DIB Session باستخدام <code>project_id</code> وبيانات المشروع المختار. لا تشغل الحساب المالي، ولا تنشئ Snapshot، ولا تستخدم AI أو شبكة خارجية.
        </p>
        {errorMessage ? <p className="error-banner"><AlertTriangle size={16} aria-hidden="true" /> {errorMessage}</p> : null}
        <div className="button-row">
          <a className="secondary-button" href="#dashboard"><ArrowLeft size={16} aria-hidden="true" /> العودة للمنصة</a>
          <button type="button" className="secondary-button" onClick={() => void loadDIBStatus()} disabled={Boolean(operationBusy)}><RefreshCcw size={16} aria-hidden="true" /> تحديث حالة DIB</button>
          <button type="button" className="secondary-button" onClick={() => void loadUserProjects()} disabled={Boolean(operationBusy) || hasUnsavedItems}><RefreshCcw size={16} aria-hidden="true" /> تحديث المشاريع</button>
          <button type="button" className="primary-button" onClick={() => void beginSession()} disabled={!canBeginSession}><Send size={16} aria-hidden="true" /> بدء Session للمشروع</button>
          <button type="button" disabled={!canSaveBlueprint} onClick={() => void persistBlueprint()}>حفظ Blueprint عبر API</button>
          {legacyReadOnly ? <p role="status">هذه نسخة سابقة تحتاج مراجعة المسؤول قبل تعديلها؛ بقيت بياناتها الأصلية محفوظة.</p> : null}
          {hasUnsavedItems ? <p role="status">لديك تعديلات غير محفوظة. احفظها قبل اعتماد المدخلات أو فحصها أو إغلاق الجلسة.</p> : null}
          <button type="button" disabled={!canApproveManifest} onClick={() => void persistManifest()}>اعتماد Manifest عبر API</button>
          <button type="button" disabled={!canRunGate} onClick={() => void persistValidationGate()}>تشغيل Validation Gate عبر API</button>
          <button type="button" disabled={!session || Boolean(operationBusy) || hasUnsavedItems || legacyReadOnly} onClick={() => void closeSession()}>إغلاق Session</button>
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

      <section className="panel" aria-label="استئناف DIB Session">
        <div className="section-title"><Layers3 size={20} aria-hidden="true" /><h2>استئناف الجلسة السابقة</h2></div>
        <p className="muted">Package A يضيف البحث عن آخر جلسات DIB المرتبطة بنفس <code>project_id</code>، ثم يسمح بالاستئناف أو بدء جلسة جديدة.</p>
        <div className="button-row">
          <button type="button" className="primary-button" disabled={!canResumeSession} onClick={() => latestResumeSession && void resumeSession(latestResumeSession.session_id)}>
            <Send size={16} aria-hidden="true" /> استئناف آخر Session
          </button>
          <button type="button" disabled={!canBeginSession} onClick={() => void beginSession()}>بدء Session جديدة</button>
          <button type="button" disabled={!selectedProject || Boolean(operationBusy)} onClick={() => selectedProject && void loadProjectSessions(selectedProject.project_id)}>
            <RefreshCcw size={16} aria-hidden="true" /> تحديث الجلسات السابقة
          </button>
        </div>
        <div className="remediation-list">
          {resumableSessions.map((item) => (
            <article key={item.session_id}>
              <strong>{item.status}</strong>
              <span>session_id: <code>{item.session_id}</code></span>
              <small>updated_at: {shortDate(item.updated_at)} · blueprint: <code>{item.current_blueprint_id ?? "—"}</code> · manifest: <code>{item.approved_manifest_id ?? "—"}</code></small>
              <div className="button-row">
                <button type="button" onClick={() => void resumeSession(item.session_id)} disabled={Boolean(operationBusy || session)}>استئناف هذه الجلسة</button>
              </div>
            </article>
          ))}
          {resumableSessions.length === 0 ? <p className="muted">لا توجد جلسة سابقة قابلة للاستئناف لهذا المشروع.</p> : null}
        </div>
      </section>

      <section className="dashboard-grid" aria-label="مؤشرات DIB">
        <article className="metric-card"><span>حالة الجلسة</span><strong>{sessionStatus}</strong><small>{session?.session_id ?? "لم تبدأ بعد"}</small></article>
        <article className="metric-card"><span>المشروع</span><strong>{selectedProject ? "مرتبط" : "غير مرتبط"}</strong><small>{selectedProject?.project_id ?? "لا يوجد project_id"}</small></article>
        <article className="metric-card"><span>الجلسات السابقة</span><strong>{resumableSessions.length.toLocaleString("ar-SA")}</strong><small>استئناف أو بدء جديد</small></article>
        <article className="metric-card"><span>البنود القابلة للـManifest</span><strong>{approvedCount.toLocaleString("ar-SA")}</strong><small>المحجوبة: {blockedCount.toLocaleString("ar-SA")}</small></article>
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
              {!item.item_id ? <small>احفظ المسودة أولًا، ثم راجع البند وسبب الصفر من نسخته المحفوظة.</small> : null}
              <div className="button-row">
                <input disabled={Boolean(operationBusy) || legacyReadOnly} aria-label={`قيمة ${item.label}`} type="number" value={item.value ?? ""} onChange={(event) => updateItemValue(item.input_key, event.target.value)} />
                {item.item_id && item.value_state === "INTENTIONAL_ZERO" ? <input disabled={Boolean(operationBusy) || legacyReadOnly} aria-label={`سبب الصفر المقصود ${item.label}`} placeholder="سبب اعتماد قيمة صفر" value={item.reason ?? ""} onChange={(event) => setItems((current) => current.map((row) => row.input_key === item.input_key ? { ...row, reason: event.target.value } : row))} /> : null}
                <button type="button" disabled={Boolean(operationBusy) || !item.item_id || legacyReadOnly} onClick={() => approveItem(item.input_key)}><CheckCircle2 size={15} aria-hidden="true" /> اعتماد البند</button>
                <button type="button" disabled={Boolean(operationBusy) || !item.item_id || legacyReadOnly} onClick={() => blockItem(item.input_key)}><ShieldCheck size={15} aria-hidden="true" /> يحتاج تعديل</button>
              </div>
            </article>
          ))}
          {items.length === 0 ? <p className="muted">اختر مشروعًا حتى يتم توليد بنود Blueprint من مدخلاته أو استئناف جلسة محفوظة.</p> : null}
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
