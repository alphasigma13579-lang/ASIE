import { AlertTriangle, ArrowLeft, BadgeCheck, Database, FileText, RefreshCcw, Send, ShieldCheck, Sparkles, Target } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { fetchProjects } from "./api";
import type { Project } from "./contracts";
import {
  DIB_MANIFEST_RUN_READINESS_UI_ID,
  type DIBProjectRunReadinessPayload,
  type DIBSessionRecord,
  buildDIBProjectRunReadiness,
  fetchDIBSession,
  fetchDIBSessionsForProject,
  saveDIBApprovedManifest,
  saveDIBBlueprint,
  saveDIBValidationGate,
  startDIBSession,
} from "./dibApi";

const requiredRows = [
  { input_key: "startup_cost", label: "تكلفة التأسيس", value: 120000 },
  { input_key: "monthly_fixed_cost", label: "التكاليف الشهرية الثابتة", value: 42000 },
  { input_key: "unit_price", label: "سعر الوحدة", value: 18 },
  { input_key: "variable_cost", label: "التكلفة المتغيرة للوحدة", value: 7 },
  { input_key: "monthly_units", label: "عدد الوحدات الشهري", value: 4200 },
] as const;

const forbiddenBoundaries = [
  "لا تشغيل Finance Engine من Package C",
  "لا استدعاء ProjectRunWorkflow المجمد",
  "لا إنشاء Snapshot أو Decision Pack",
  "لا تفعيل AI Provider",
  "لا جلب شبكي أو مصدر خارجي",
  "Project Run Request هنا readiness فقط من Approved Manifest",
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
    source: "asie_user_project_context",
  };
}

function shortValue(value: unknown): string {
  if (typeof value === "number") return value.toLocaleString("ar-SA");
  if (typeof value === "string" && value.trim()) return value;
  return "—";
}

export function DIBManifestRunReadiness() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState("");
  const [sessions, setSessions] = useState<DIBSessionRecord[]>([]);
  const [session, setSession] = useState<DIBSessionRecord | null>(null);
  const [readiness, setReadiness] = useState<DIBProjectRunReadinessPayload | null>(null);
  const [operationBusy, setOperationBusy] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    void loadProjects();
  }, []);

  const selectedProject = useMemo(
    () => projects.find((project) => project.project_id === selectedProjectId) ?? projects[0] ?? null,
    [projects, selectedProjectId]
  );
  const latestSession = sessions[0] ?? null;
  const manifestStatus = session?.approved_manifest?.status ?? "missing";
  const gateStatus = session?.validation_gate?.status ?? "missing";
  const canStart = Boolean(selectedProject && !session && !operationBusy);
  const canResume = Boolean(latestSession && !session && !operationBusy);
  const canPrepare = Boolean(session && !session.current_blueprint && !operationBusy);
  const canApproveManifest = Boolean(session?.current_blueprint && !session.approved_manifest && !operationBusy);
  const canRunGate = Boolean(session?.approved_manifest && !session.validation_gate && !operationBusy);
  const canCheckReadiness = Boolean(session && !operationBusy);

  async function withOperation<T>(label: string, action: () => Promise<T>): Promise<T | null> {
    setOperationBusy(label);
    setErrorMessage(null);
    try {
      return await action();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "تعذر تنفيذ Package C");
      return null;
    } finally {
      setOperationBusy(null);
    }
  }

  async function loadProjects() {
    const loaded = await withOperation("load-projects", fetchProjects);
    if (!loaded) return;
    setProjects(loaded);
    const nextId = loaded[0]?.project_id ?? "";
    setSelectedProjectId(nextId);
    if (nextId) void loadSessions(nextId);
  }

  async function loadSessions(projectId: string) {
    const loaded = await withOperation("load-sessions", () => fetchDIBSessionsForProject(projectId));
    if (loaded) setSessions(loaded);
  }

  function selectProject(projectId: string) {
    setSelectedProjectId(projectId);
    setSession(null);
    setReadiness(null);
    if (projectId) void loadSessions(projectId);
  }

  async function beginSession() {
    if (!selectedProject) return;
    const started = await withOperation("start-session", () => startDIBSession(projectProfileFromProject(selectedProject)));
    if (!started) return;
    setSession(started);
    await loadSessions(started.project_id);
  }

  async function resumeLatestSession() {
    if (!latestSession) return;
    const loaded = await withOperation("resume-session", () => fetchDIBSession(latestSession.session_id));
    if (loaded) setSession(loaded);
  }

  async function refreshSession() {
    if (!session) return;
    const loaded = await withOperation("refresh-session", () => fetchDIBSession(session.session_id));
    if (loaded) setSession(loaded);
  }

  async function prepareBaselineBlueprint() {
    if (!session) return;
    const saved = await withOperation("baseline-blueprint", () =>
      saveDIBBlueprint(session.session_id, {
        source: "dib_completion_package_c_manifest_run_readiness",
        intake_payload: {
          file_name: `package-c-baseline-${session.project_id}`,
          rows: requiredRows.map((row) => ({ ...row })),
        },
      })
    );
    if (saved) await refreshSession();
  }

  async function approveManifest() {
    if (!session) return;
    const saved = await withOperation("approve-manifest", () => saveDIBApprovedManifest(session.session_id));
    if (saved) await refreshSession();
  }

  async function runValidationGate() {
    if (!session) return;
    const saved = await withOperation("validation-gate", () => saveDIBValidationGate(session.session_id));
    if (saved) await refreshSession();
  }

  async function checkReadiness() {
    if (!session) return;
    const result = await withOperation("project-run-readiness", () => buildDIBProjectRunReadiness(session.session_id));
    if (result) setReadiness(result.project_run_readiness);
  }

  return (
    <main className="app-shell dib-workspace" dir="rtl" data-ui-id={DIB_MANIFEST_RUN_READINESS_UI_ID}>
      <section className="page-intro">
        <p className="eyebrow"><Sparkles size={16} aria-hidden="true" /> DIB Completion Package C · Manifest-to-Run Readiness</p>
        <h1>جاهزية Manifest للتسليم إلى Project Run</h1>
        <p>
          هذه الواجهة تفحص هل Approved Input Manifest وManifest Validation Gate جاهزان لبناء Project Run Request محكوم. لا تشغل Finance Engine، ولا تستدعي ProjectRunWorkflow، ولا تنشئ Snapshot.
        </p>
        {errorMessage ? <p className="error-banner"><AlertTriangle size={16} aria-hidden="true" /> {errorMessage}</p> : null}
        <div className="button-row">
          <a className="secondary-button" href="#dib"><ArrowLeft size={16} aria-hidden="true" /> العودة لمساحة DIB</a>
          <button type="button" className="secondary-button" onClick={() => void loadProjects()} disabled={Boolean(operationBusy)}><RefreshCcw size={16} aria-hidden="true" /> تحديث المشاريع</button>
          <button type="button" className="primary-button" onClick={() => void beginSession()} disabled={!canStart}><Send size={16} aria-hidden="true" /> بدء Session</button>
          <button type="button" onClick={() => void resumeLatestSession()} disabled={!canResume}>استئناف آخر Session</button>
          <button type="button" onClick={() => void prepareBaselineBlueprint()} disabled={!canPrepare}>تجهيز Blueprint اختباري</button>
          <button type="button" onClick={() => void approveManifest()} disabled={!canApproveManifest}>اعتماد Manifest</button>
          <button type="button" onClick={() => void runValidationGate()} disabled={!canRunGate}>تشغيل Validation Gate</button>
          <button type="button" onClick={() => void checkReadiness()} disabled={!canCheckReadiness}>فحص Run Readiness</button>
        </div>
      </section>

      <section className="panel" aria-label="Project and session binding">
        <div className="section-title"><Target size={20} aria-hidden="true" /><h2>المشروع والجلسة</h2></div>
        <div className="button-row">
          <label htmlFor="run-readiness-project-select">اختر مشروع ASIE</label>
          <select id="run-readiness-project-select" value={selectedProject?.project_id ?? ""} onChange={(event) => selectProject(event.target.value)} disabled={Boolean(session || operationBusy)}>
            {projects.map((project) => <option key={project.project_id} value={project.project_id}>{project.name} · {project.project_id}</option>)}
          </select>
        </div>
        <ul className="lineage-list">
          <li>project_id: <code>{selectedProject?.project_id ?? "لا يوجد"}</code></li>
          <li>session_id: <code>{session?.session_id ?? "لم تبدأ"}</code></li>
          <li>latest_session: <code>{latestSession?.session_id ?? "لا توجد"}</code></li>
        </ul>
      </section>

      <section className="dashboard-grid" aria-label="Package C metrics">
        <article className="metric-card"><span>Blueprint</span><strong>{session?.current_blueprint ? "جاهز" : "ناقص"}</strong><small>{session?.current_blueprint_id ?? "لا يوجد"}</small></article>
        <article className="metric-card"><span>Manifest</span><strong>{manifestStatus}</strong><small>{session?.approved_manifest_id ?? "لا يوجد"}</small></article>
        <article className="metric-card"><span>Validation Gate</span><strong>{gateStatus}</strong><small>{session?.validation_gate_id ?? "لا يوجد"}</small></article>
        <article className="metric-card"><span>Run Readiness</span><strong>{readiness?.status ?? "لم يفحص"}</strong><small>Finance execution = not_executed</small></article>
      </section>

      <section className="decision-command__grid" aria-label="Readiness output">
        <article className="panel">
          <div className="section-title"><BadgeCheck size={20} aria-hidden="true" /><h2>Project Run Readiness</h2></div>
          {readiness ? (
            <ul className="lineage-list">
              <li>readiness_id: <code>{readiness.readiness_id}</code></li>
              <li>status: <code>{readiness.status}</code></li>
              <li>ready_for_project_run: <code>{String(readiness.ready_for_project_run)}</code></li>
              <li>input_source: <code>{readiness.input_source}</code></li>
              <li>workflow_mount: <code>{readiness.project_run_workflow_mount}</code></li>
              <li>finance_execution: <code>{readiness.finance_engine_execution_status}</code></li>
            </ul>
          ) : <p className="muted">لم يتم فحص الجاهزية بعد.</p>}
        </article>
        <article className="panel">
          <div className="section-title"><AlertTriangle size={20} aria-hidden="true" /><h2>Blockers</h2></div>
          <ul className="lineage-list">
            {(readiness?.blockers ?? []).map((blocker) => <li key={blocker.code}>{blocker.severity}: <code>{blocker.code}</code> · {blocker.message}</li>)}
          </ul>
          {readiness && readiness.blockers.length === 0 ? <p className="muted">لا توجد موانع في readiness gate.</p> : null}
        </article>
      </section>

      <section className="panel" aria-label="Project run request preview">
        <div className="section-title"><Database size={20} aria-hidden="true" /><h2>Project Run Request Preview</h2></div>
        {readiness?.project_run_request ? (
          <ul className="lineage-list">
            <li>approved_input_manifest_id: <code>{shortValue(readiness.project_run_request.approved_input_manifest_id)}</code></li>
            <li>manifest_validation_gate_id: <code>{shortValue(readiness.project_run_request.manifest_validation_gate_id)}</code></li>
            <li>manifest_gate_id: <code>{shortValue(readiness.project_run_request.manifest_gate_id)}</code></li>
            <li>requires_project_run_workflow_mount: <code>{shortValue(readiness.project_run_request.requires_project_run_workflow_mount)}</code></li>
            <li>input_hash: <code>{shortValue(readiness.project_run_request.input_hash)}</code></li>
          </ul>
        ) : <p className="muted">لا يوجد Project Run Request Preview إلا إذا أصبحت الجاهزية ready.</p>}
      </section>

      <section className="decision-command__grid" aria-label="Package C boundaries">
        <article className="panel">
          <div className="section-title"><FileText size={20} aria-hidden="true" /><h2>مسار Package C</h2></div>
          <ul className="lineage-list">
            <li><code>Approved Input Manifest</code></li>
            <li><code>Manifest Validation Gate</code></li>
            <li><code>POST /api/dib/sessions/{"{session_id}"}/project-run-readiness</code></li>
            <li><code>dib.project_run.manifest_gate.v1</code></li>
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
