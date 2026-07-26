import { AlertTriangle, ArrowLeft, BadgeCheck, Calculator, FileText, RefreshCcw, ShieldCheck, Sparkles, Target } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { fetchProjects } from "./api";
import type { Project } from "./contracts";
import {
  DIB_CONTROLLED_FINANCE_WIRING_UI_ID,
  type DIBControlledFinancePayload,
  type DIBSessionRecord,
  executeDIBControlledFinance,
  fetchLatestDIBSessionForProject,
} from "./dibApi";

const forbiddenBoundaries = [
  "لا قراءة raw UI أو raw file أو raw prompt",
  "لا تشغيل ProjectRunWorkflow من هذه الصفحة",
  "لا إنشاء Snapshot أو Decision Pack",
  "لا تفعيل AI Provider",
  "لا جلب شبكي أو مصدر خارجي",
] as const;

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : null;
}

function displayMetric(value: unknown): string {
  if (typeof value === "number") return value.toLocaleString("ar-SA");
  if (value === null || value === undefined || value === "") return "—";
  return String(value);
}

export function DIBControlledFinanceWiring() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState("");
  const [session, setSession] = useState<DIBSessionRecord | null>(null);
  const [controlledFinance, setControlledFinance] = useState<DIBControlledFinancePayload | null>(null);
  const [operationBusy, setOperationBusy] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    void loadProjects();
  }, []);

  const selectedProject = useMemo(
    () => projects.find((project) => project.project_id === selectedProjectId) ?? projects[0] ?? null,
    [projects, selectedProjectId]
  );
  const finance = asRecord(controlledFinance?.finance);
  const baseline = asRecord(finance?.baseline);
  const monteCarlo = asRecord(finance?.monte_carlo);
  const blockers = controlledFinance?.blockers ?? [];
  const canLoadSession = Boolean(selectedProject && !operationBusy);
  const canExecute = Boolean(session && !operationBusy);

  async function withOperation<T>(label: string, action: () => Promise<T>): Promise<T | null> {
    setOperationBusy(label);
    setErrorMessage(null);
    try {
      return await action();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "تعذر تنفيذ Controlled Finance Wiring");
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
    setSession(null);
    setControlledFinance(null);
  }

  async function loadLatestSession() {
    if (!selectedProject) return;
    const loaded = await withOperation("load-latest-dib-session", () => fetchLatestDIBSessionForProject(selectedProject.project_id));
    setSession(loaded);
    setControlledFinance(null);
  }

  async function runControlledFinance() {
    if (!session) return;
    const result = await withOperation("controlled-finance", () => executeDIBControlledFinance(session.session_id));
    if (result) setControlledFinance(result.controlled_finance);
  }

  return (
    <main className="app-shell dib-workspace" dir="rtl" data-ui-id={DIB_CONTROLLED_FINANCE_WIRING_UI_ID}>
      <section className="page-intro">
        <p className="eyebrow"><Sparkles size={16} aria-hidden="true" /> DIB Completion Package D · Controlled Finance Wiring</p>
        <h1>تشغيل Finance المحكوم من Manifest فقط</h1>
        <p>
          هذه الواجهة تنفذ Finance Engine بشكل محكوم بعد Approved Manifest وValidation Gate فقط. لا تمرر قيمًا خامًا، ولا تستدعي ProjectRunWorkflow، ولا تنشئ Snapshot.
        </p>
        {errorMessage ? <p className="error-banner"><AlertTriangle size={16} aria-hidden="true" /> {errorMessage}</p> : null}
        <div className="button-row">
          <a className="secondary-button" href="#dib-run-readiness"><ArrowLeft size={16} aria-hidden="true" /> العودة لجاهزية التشغيل</a>
          <button type="button" className="secondary-button" onClick={() => void loadProjects()} disabled={Boolean(operationBusy)}><RefreshCcw size={16} aria-hidden="true" /> تحديث المشاريع</button>
          <button type="button" onClick={() => void loadLatestSession()} disabled={!canLoadSession}>تحميل آخر DIB Session</button>
          <button type="button" className="primary-button" onClick={() => void runControlledFinance()} disabled={!canExecute}><Calculator size={16} aria-hidden="true" /> تشغيل Finance المحكوم</button>
        </div>
      </section>

      <section className="panel" aria-label="Project and DIB session">
        <div className="section-title"><Target size={20} aria-hidden="true" /><h2>المشروع والجلسة</h2></div>
        <div className="button-row">
          <label htmlFor="finance-project-select">اختر مشروع ASIE</label>
          <select id="finance-project-select" value={selectedProject?.project_id ?? ""} onChange={(event) => { setSelectedProjectId(event.target.value); setSession(null); setControlledFinance(null); }} disabled={Boolean(operationBusy)}>
            {projects.map((project) => <option key={project.project_id} value={project.project_id}>{project.name} · {project.project_id}</option>)}
          </select>
        </div>
        <ul className="lineage-list">
          <li>project_id: <code>{selectedProject?.project_id ?? "لا يوجد"}</code></li>
          <li>session_id: <code>{session?.session_id ?? "لم يتم تحميل جلسة"}</code></li>
          <li>manifest_id: <code>{session?.approved_manifest_id ?? "غير جاهز"}</code></li>
          <li>validation_gate_id: <code>{session?.validation_gate_id ?? "غير جاهز"}</code></li>
        </ul>
      </section>

      <section className="dashboard-grid" aria-label="Controlled Finance metrics">
        <article className="metric-card"><span>Controlled Finance</span><strong>{controlledFinance?.status ?? "لم يعمل"}</strong><small>{controlledFinance?.finance_engine_execution_status ?? "not_executed"}</small></article>
        <article className="metric-card"><span>Monthly Revenue</span><strong>{displayMetric(baseline?.revenue)}</strong><small>من normalized_inputs فقط</small></article>
        <article className="metric-card"><span>Monthly Profit</span><strong>{displayMetric(baseline?.monthly_profit)}</strong><small>Finance Engine backend</small></article>
        <article className="metric-card"><span>Monte Carlo</span><strong>{displayMetric(monteCarlo?.p_pass)}</strong><small>{String(monteCarlo?.status ?? "not_run")}</small></article>
      </section>

      <section className="panel" aria-label="Controlled Finance result">
        <div className="section-title"><BadgeCheck size={20} aria-hidden="true" /><h2>نتيجة Finance المحكومة</h2></div>
        {controlledFinance ? (
          <ul className="lineage-list">
            <li>contract_id: <code>{controlledFinance.contract_id}</code></li>
            <li>input_source: <code>{controlledFinance.input_source}</code></li>
            <li>finance_contract_id: <code>{String(controlledFinance.finance_contract_id ?? "finance.result.v1")}</code></li>
            <li>project_run_workflow_mount: <code>{controlledFinance.project_run_workflow_mount}</code></li>
            <li>snapshot_wiring_enabled: <code>{String(controlledFinance.snapshot_wiring_enabled)}</code></li>
          </ul>
        ) : <p className="muted">حمّل جلسة DIB تحتوي Manifest معتمد وValidation Gate ناجح، ثم شغّل Finance المحكوم.</p>}
      </section>

      <section className="panel" aria-label="Controlled Finance blockers">
        <div className="section-title"><FileText size={20} aria-hidden="true" /><h2>Blockers</h2></div>
        <div className="remediation-list">
          {blockers.map((blocker) => (
            <article key={blocker.code}>
              <strong>{blocker.code}</strong>
              <span>{blocker.severity}</span>
              <small>{blocker.message}</small>
            </article>
          ))}
          {blockers.length === 0 ? <p className="muted">لا توجد Blockers من مسار Controlled Finance الحالي.</p> : null}
        </div>
      </section>

      <section className="decision-command__grid" aria-label="Controlled Finance boundaries">
        <article className="panel">
          <div className="section-title"><ShieldCheck size={20} aria-hidden="true" /><h2>الممنوع</h2></div>
          <ul className="lineage-list">
            {forbiddenBoundaries.map((item) => <li key={item}>{item}</li>)}
          </ul>
        </article>
        <article className="panel">
          <div className="section-title"><FileText size={20} aria-hidden="true" /><h2>API</h2></div>
          <ul className="lineage-list">
            <li><code>POST /api/dib/sessions/{"{session_id}"}/controlled-finance</code></li>
            <li><code>finance.calculate.v1</code> من <code>approved.input.manifest.v1</code> فقط</li>
          </ul>
        </article>
      </section>
    </main>
  );
}
