import { ArrowLeft, BadgeCheck, CheckCircle2, Database, FileText, Layers3, ShieldCheck, Sparkles, Target } from "lucide-react";
import { useMemo, useState } from "react";

type DIBItemState = "UNKNOWN" | "USER_PROVIDED" | "MARKET_ESTIMATED" | "APPROVED" | "BLOCKED";

type DIBItem = {
  input_key: string;
  label: string;
  value_state: DIBItemState;
  value?: number | string;
  evidence_label: string;
  decision: "بانتظار قرار العميل" | "مقبول" | "يحتاج تعديل";
};

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

const initialItems: DIBItem[] = [
  {
    input_key: "capex_equipment",
    label: "معدات محل شاورما",
    value_state: "MARKET_ESTIMATED",
    value: 155000,
    evidence_label: "Market Evidence Pack محلي تجريبي — لا يوجد fetch خارجي",
    decision: "بانتظار قرار العميل",
  },
  {
    input_key: "rent_monthly",
    label: "الإيجار الشهري",
    value_state: "USER_PROVIDED",
    value: 18000,
    evidence_label: "مدخل يدوي يحتاج مراجعة المستخدم",
    decision: "بانتظار قرار العميل",
  },
  {
    input_key: "unit_price",
    label: "سعر الوجبة",
    value_state: "USER_PROVIDED",
    value: 18,
    evidence_label: "مدخل يدوي قابل للتعديل قبل Manifest",
    decision: "بانتظار قرار العميل",
  },
  {
    input_key: "monthly_units",
    label: "عدد الطلبات الشهري",
    value_state: "UNKNOWN",
    evidence_label: "ينتظر تقدير المستخدم أو ملف مدخلات",
    decision: "يحتاج تعديل",
  },
];

function formatCurrency(value: number | string | undefined): string {
  if (typeof value !== "number") return value ? String(value) : "غير محدد";
  return new Intl.NumberFormat("ar-SA", { style: "currency", currency: "SAR", maximumFractionDigits: 0 }).format(value);
}

function arabicState(state: DIBItemState): string {
  const labels: Record<DIBItemState, string> = {
    UNKNOWN: "غير مكتمل",
    USER_PROVIDED: "مدخل من المستخدم",
    MARKET_ESTIMATED: "تقدير سوقي محلي",
    APPROVED: "معتمد للـManifest",
    BLOCKED: "محجوب",
  };
  return labels[state];
}

export function DIBWorkspace() {
  const [items, setItems] = useState<DIBItem[]>(initialItems);
  const [sessionStatus, setSessionStatus] = useState<"active" | "blueprint_saved" | "manifest_approved" | "validation_passed">("active");

  const approvedCount = items.filter((item) => item.value_state === "APPROVED").length;
  const blockedCount = items.filter((item) => item.value_state === "BLOCKED" || item.value_state === "UNKNOWN").length;
  const canApproveManifest = approvedCount > 0 && blockedCount === 0;

  const timeline = useMemo(
    () => [
      { label: "DIB Session", status: "active", done: true },
      { label: "Dynamic Input Blueprint", status: sessionStatus === "active" ? "جاهز للحفظ" : "saved", done: sessionStatus !== "active" },
      { label: "Approved Input Manifest", status: canApproveManifest ? "قابل للاعتماد" : "محجوب حتى تراجع البنود", done: sessionStatus === "manifest_approved" || sessionStatus === "validation_passed" },
      { label: "Manifest Validation Gate", status: sessionStatus === "validation_passed" ? "passed" : "لم يعمل بعد", done: sessionStatus === "validation_passed" },
    ],
    [canApproveManifest, sessionStatus]
  );

  function approveItem(inputKey: string) {
    setItems((current) =>
      current.map((item) =>
        item.input_key === inputKey
          ? {
              ...item,
              value_state: "APPROVED",
              decision: "مقبول",
              value: item.value ?? 0,
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
              value_state: "BLOCKED",
              decision: "يحتاج تعديل",
            }
          : item
      )
    );
  }

  return (
    <main id="main-content" className="app-shell dib-workspace" dir="rtl" data-ui-id={DIB_UI_ID}>
      <section className="page-intro">
        <p className="eyebrow"><Sparkles size={16} aria-hidden="true" /> DIB-LIVE-002E · واجهة عربية محكومة</p>
        <h1>مساحة Dynamic Input Blueprint</h1>
        <p>
          هذه واجهة عمل عربية لمراجعة البنود قبل تحويلها إلى Approved Input Manifest. لا تشغل الحساب المالي، ولا تنشئ Snapshot، ولا تستخدم AI أو شبكة خارجية.
        </p>
        <div className="button-row">
          <a className="secondary-button" href="#dashboard"><ArrowLeft size={16} aria-hidden="true" /> العودة للمنصة</a>
          <button type="button" className="primary-button" onClick={() => setSessionStatus("blueprint_saved")}>حفظ Blueprint محلي</button>
          <button type="button" disabled={!canApproveManifest} onClick={() => setSessionStatus("manifest_approved")}>اعتماد Manifest</button>
          <button type="button" disabled={sessionStatus !== "manifest_approved"} onClick={() => setSessionStatus("validation_passed")}>تشغيل Validation Gate</button>
        </div>
      </section>

      <section className="dashboard-grid" aria-label="مؤشرات DIB">
        <article className="metric-card"><span>حالة الجلسة</span><strong>{sessionStatus}</strong><small>لا يوجد snapshot_mutation</small></article>
        <article className="metric-card"><span>البنود المعتمدة</span><strong>{approvedCount.toLocaleString("ar-SA")}</strong><small>تدخل لاحقًا في Manifest فقط</small></article>
        <article className="metric-card"><span>البنود المحجوبة</span><strong>{blockedCount.toLocaleString("ar-SA")}</strong><small>تمنع الاعتماد حتى المراجعة</small></article>
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
              <span>{item.input_key} · {arabicState(item.value_state)} · {formatCurrency(item.value)}</span>
              <small>{item.evidence_label}</small>
              <div className="button-row">
                <button type="button" onClick={() => approveItem(item.input_key)}><CheckCircle2 size={15} aria-hidden="true" /> اعتماد البند</button>
                <button type="button" onClick={() => blockItem(item.input_key)}><ShieldCheck size={15} aria-hidden="true" /> يحتاج تعديل</button>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="decision-command__grid" aria-label="حدود الواجهة وعقود API">
        <article className="panel">
          <div className="section-title"><Database size={20} aria-hidden="true" /><h2>واجهات API المرجعية</h2></div>
          <ul className="lineage-list">
            {dibApiRoutes.map((route) => <li key={route}><code>{route}</code></li>)}
          </ul>
          <p className="muted">التركيب داخل HTTP server ما زال مرحلة لاحقة؛ هذه الواجهة تحفظ حدود المنتج ولا تكسر Freeze.</p>
        </article>
        <article className="panel">
          <div className="section-title"><FileText size={20} aria-hidden="true" /><h2>الممنوع في هذه المرحلة</h2></div>
          <ul className="lineage-list">
            {forbiddenBoundaries.map((item) => <li key={item}><BadgeCheck size={15} aria-hidden="true" /> {item}</li>)}
          </ul>
        </article>
      </section>
    </main>
  );
}
