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

const initialItems: DIBBlueprintItem[] = [
  {
    input_key: "startup_cost",
    label: "تكلفة التأسيس",
    value_state: "USER_PROVIDED",
    value: 155000,
    evidence_refs: ["ui-live-manual:startup_cost"],
    source_type: "user_input",
    value_source: "user_input",
    review_status: "draft",
    required: true,
  },
  {
    input_key: "monthly_fixed_cost",
    label: "التكاليف الشهرية الثابتة",
    value_state: "USER_PROVIDED",
    value: 36000,
    evidence_refs: ["ui-live-manual:monthly_fixed_cost"],
    source_type: "user_input",
    value_source: "user_input",
    review_status: "draft",
    required: true,
  },
  {
    input_key: "unit_price",
    label: "سعر الوجبة",
    value_state: "USER_PROVIDED",
    value: 18,
    evidence_refs: ["ui-live-manual:unit_price"],
    source_type: "user_input",
    value_source: "user_input",
    review_status: "draft",
    required: true,
  },
  {
    input_key: "variable_cost",
    label: "تكلفة المواد للوجبة",
    value_state: "USER_PROVIDED",
    value: 7,
    evidence_refs: ["ui-live-manual:variable_cost"],
    source_type: "user_input",
    value_source: "user_input",
    review_status: "draft",
    required: true,
  },
  {
    input_key: "monthly_units",
    label: "عدد الطلبات الشهري",
    value_state: "USER_PROVIDED",
    value: 4200,
    evidence_refs: ["ui-live-manual:monthly_units"],
    source_type: "user_input",
    value_source: "user_input",
    review_status: "draft",
    required: true,
  },
];

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

function projectProfile() {
  return {
    project_id: "project_dib_workspace_live_shawarma",
    name: "محل شاورما — DIB Live API",
    sector: "Food Service",
    activity: "shawarma shop",
    location_country: "SA",
    location_scope: "city",
    intake_mode: "manual_ui_live_api",
  };
}

export function DIBWorkspace() {
  const [items, setItems] = useState<DIBBlueprintItem[]>(initialItems);
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
  }, []);

  const visibleItems = blueprint?.payload.items ?? session?.current_blueprint?.items ?? items;
  const approvedManifest = manifest?.payload ?? session?.approved_manifest ?? null;
  const gatePayload = validationGate?.payload ?? session?.validation_gate ?? null;
  const sessionStatus = session?.status ?? "not_started";
  const approvedCount = visibleItems.filter((item) => item.value_state !== "UNKNOWN" && item.value_state !== "REJECTED").length;
  const blockedCount = visibleItems.filter((item) => item.value_state === "UNKNOWN" || item.value_state === "REJECTED").length;
  const canSaveBlueprint = Boolean(session && !operationBusy);
  const canApproveManifest = Boolean(session && (blueprint || session.current_blueprint) && !operationBusy);
  const canRunGate = Boolean(session && approvedManifest?.status === "approved" && !operationBusy);

  const timeline = useMemo(
    () => [
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
    [approvedManifest?.status, blueprint, gatePayload?.status, session, sessionStatus]
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
    const started = await withOperation("start-session", () => startDIBSession(projectProfile()));
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
        source: "dib_ui_live_api",
        intake_payload: {
          file_name: "dib-ui-live-manual-table",
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
          value_state: value === "" ? "UNKNOWN" : "USER_PROVIDED",
          review_status: value === "" ? "draft" : "approved",
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
              value_source: "user_input",
              source_type: "user_input",
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
    <main id="main-content" className="app-shell dib-workspace" dir="rtl" data-ui-id={DIB_UI_LIVE_API_WIRING_ID} data-parent-ui-id={DIB_UI_ID}>
      <section className="page-intro">
        <p className="eyebrow"><Sparkles size={16} aria-hidden="true" /> DIB-LIVE-002J · واجهة عربية متصلة فعليًا بالـAPI</p>
        <h1>مساحة Dynamic Input Blueprint</h1>
        <p>
          هذه الواجهة تستدعي مسارات <code>/api/dib/...</code> عبر طبقة API الأمامية، وترسل Bearer token وبيئة المنظمة تلقائيًا. لا تشغل الحساب المالي، ولا تنشئ Snapshot، ولا تستخدم AI أو شبكة خارجية.
        </p>
        {errorMessage ? <p className="error-banner"><AlertTriangle size={16} aria-hidden="true" /> {errorMessage}</p> : null}
        <div className="button-row">
          <a className="secondary-button" href="#dashboard"><ArrowLeft size={16} aria-hidden="true" /> العودة للمنصة</a>
          <button type="button" className="secondary-button" onClick={() => void loadDIBStatus()} disabled={Boolean(operationBusy)}><RefreshCcw size={16} aria-hidden="true" /> تحديث حالة DIB</button>
          <button type="button" className="primary-button" onClick={() => void beginSession()} disabled={Boolean(operationBusy)}><Send size={16} aria-hidden="true" /> بدء Session عبر API</button>
          <button type="button" disabled={!canSaveBlueprint} onClick={() => void persistBlueprint()}>حفظ Blueprint عبر API</button>
          <button type="button" disabled={!canApproveManifest} onClick={() => void persistManifest()}>اعتماد Manifest عبر API</button>
          <button type="button" disabled={!canRunGate} onClick={() => void persistValidationGate()}>تشغيل Validation Gate عبر API</button>
          <button type="button" disabled={!session || Boolean(operationBusy)} onClick={() => void closeSession()}>إغلاق Session</button>
        </div>
      </section>

      <section className="dashboard-grid" aria-label="مؤشرات DIB">
        <article className="metric-card"><span>حالة الجلسة</span><strong>{sessionStatus}</strong><small>{session?.session_id ?? "لم تبدأ بعد"}</small></article>
        <article className="metric-card"><span>البنود القابلة للـManifest</span><strong>{approvedCount.toLocaleString("ar-SA")}</strong><small>تدخل في Approved Input Manifest فقط</small></article>
        <article className="metric-card"><span>البنود المحجوبة</span><strong>{blockedCount.toLocaleString("ar-SA")}</strong><small>تظهر كـblockers عند الاعتماد</small></article>
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
        <div className="section-title"><Target size={20} aria-hidden="true" /><h2>بنود Blueprint</h2></div>
        <div className="remediation-list">
          {items.map((item) => (
            <article key={item.input_key}>
              <strong>{item.label}</strong>
              <span>{item.input_key} · {arabicState(item.value_state)} · {formatCurrency(item.value, item.unit)}</span>
              <small>{(item.evidence_refs ?? ["ui-live-manual"]).join(" · ")}</small>
              <div className="button-row">
                <input aria-label={`قيمة ${item.label}`} type="number" value={item.value ?? ""} onChange={(event) => updateItemValue(item.input_key, event.target.value)} />
                <button type="button" onClick={() => approveItem(item.input_key)}><CheckCircle2 size={15} aria-hidden="true" /> اعتماد البند</button>
                <button type="button" onClick={() => blockItem(item.input_key)}><ShieldCheck size={15} aria-hidden="true" /> يحتاج تعديل</button>
              </div>
            </article>
          ))}
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

      <section className="panel" aria-label="أحداث DIB">
        <div className="section-title"><RefreshCcw size={20} aria-hidden="true" /><h2>DIB Events</h2></div>
        {events.length ? (
          <ul className="lineage-list">
            {events.map((event) => <li key={event.event_id}>{eventLabel(event.event_type)} · <code>{event.payload_hash.slice(0, 12)}</code></li>)}
          </ul>
        ) : <p className="muted">لا توجد أحداث بعد.</p>}
      </section>
    </main>
  );
}
