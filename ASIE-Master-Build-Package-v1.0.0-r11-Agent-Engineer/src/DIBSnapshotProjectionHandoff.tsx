import { AlertTriangle, ArrowLeft, BadgeCheck, Boxes, FileText, GitBranch, RefreshCcw, ShieldCheck, Sparkles, Target } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { fetchProjects } from "./api";
import type { Project } from "./contracts";
import {
  DIB_SNAPSHOT_PROJECTION_HANDOFF_UI_ID,
  type DIBSessionRecord,
  type DIBSnapshotProjectionHandoffPayload,
  buildDIBSnapshotProjectionHandoff,
  fetchLatestDIBSessionForProject,
} from "./dibApi";

const forbiddenBoundaries = [
  "لا استدعاء Snapshot Assembly من هذه الصفحة",
  "لا إنشاء sealed envelope",
  "لا إنشاء Decision Pack",
  "لا تشغيل ProjectRunWorkflow",
  "لا قراءة raw UI أو raw file أو raw prompt",
  "لا تفعيل AI Provider أو Network Fetch",
] as const;

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : null;
}

function displayValue(value: unknown): string {
  if (typeof value === "number") return value.toLocaleString("ar-SA");
  if (value === null || value === undefined || value === "") return "—";
  return String(value);
}

export function DIBSnapshotProjectionHandoff() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState("");
  const [session, setSession] = useState<DIBSessionRecord | null>(null);
  const [handoff, setHandoff] = useState<DIBSnapshotProjectionHandoffPayload | null>(null);
  const [operationBusy, setOperationBusy] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    void loadProjects();
  }, []);

  const selectedProject = useMemo(
    () => projects.find((project) => project.project_id === selectedProjectId) ?? projects[0] ?? null,
    [projects, selectedProjectId]
  );
  const lineage = asRecord(handoff?.lineage);
  const projectionSupport = asRecord(handoff?.projection_support);
  const financeReference = asRecord(handoff?.controlled_finance_reference);
  const blockers = handoff?.blockers ?? [];
  const canLoadSession = Boolean(selectedProject && !operationBusy);
  const canPrepare = Boolean(session && !operationBusy);

  async function withOperation<T>(label: string, action: () => Promise<T>): Promise<T | null> {
    setOperationBusy(label);
    setErrorMessage(null);
    try {
      return await action();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "تعذر تجهيز Snapshot Projection Handoff");
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
    setHandoff(null);
  }

  async function loadLatestSession() {
    if (!selectedProject) return;
    const loaded = await withOperation("load-latest-dib-session", () => fetchLatestDIBSessionForProject(selectedProject.project_id));
    setSession(loaded);
    setHandoff(null);
  }

  async function prepareHandoff() {
    if (!session) return;
    const result = await withOperation("snapshot-projection-handoff", () => buildDIBSnapshotProjectionHandoff(session.session_id));
    if (result) setHandoff(result.snapshot_projection_handoff);
  }

  return (
    <main className="app-shell dib-workspace" dir="rtl" data-ui-id={DIB_SNAPSHOT_PROJECTION_HANDOFF_UI_ID}>
      <section className="page-intro">
        <p className="eyebrow"><Sparkles size={16} aria-hidden="true" /> DIB Completion Package E · Snapshot Projection Handoff</p>
        <h1>تجهيز Lineage للـSnapshot بدون إنشاء Snapshot</h1>
        <p>
          هذه الواجهة تجهز DIB lineage وProjection Support metadata بعد Controlled Finance. لا تستدعي Snapshot Assembly، ولا تنشئ sealed envelope، ولا تنتج Decision Pack.
        </p>
        {errorMessage ? <p className="error-banner"><AlertTriangle size={16} aria-hidden="true" /> {errorMessage}</p> : null}
        <div className="button-row">
          <a className="secondary-button" href="#dib-finance-wiring"><ArrowLeft size={16} aria-hidden="true" /> العودة لتشغيل Finance المحكوم</a>
          <button type="button" className="secondary-button" onClick={() => void loadProjects()} disabled={Boolean(operationBusy)}><RefreshCcw size={16} aria-hidden="true" /> تحديث المشاريع</button>
          <button type="button" onClick={() => void loadLatestSession()} disabled={!canLoadSession}>تحميل آخر DIB Session</button>
          <button type="button" className="primary-button" onClick={() => void prepareHandoff()} disabled={!canPrepare}><GitBranch size={16} aria-hidden="true" /> تجهيز Snapshot Handoff</button>
        </div>
      </section>

      <section className="panel" aria-label="Project and DIB session">
        <div className="section-title"><Target size={20} aria-hidden="true" /><h2>المشروع والجلسة</h2></div>
        <div className="button-row">
          <label htmlFor="snapshot-handoff-project-select">اختر مشروع ASIE</label>
          <select id="snapshot-handoff-project-select" value={selectedProject?.project_id ?? ""} onChange={(event) => { setSelectedProjectId(event.target.value); setSession(null); setHandoff(null); }} disabled={Boolean(operationBusy)}>
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

      <section className="dashboard-grid" aria-label="Snapshot projection metrics">
        <article className="metric-card"><span>Handoff</span><strong>{handoff?.status ?? "لم يجهز"}</strong><small>{handoff?.snapshot_assembly_mount ?? "not_called"}</small></article>
        <article className="metric-card"><span>Lineage</span><strong>{displayValue(lineage?.contract_id)}</strong><small>{displayValue(lineage?.payload_hash)}</small></article>
        <article className="metric-card"><span>Projection Support</span><strong>{displayValue(projectionSupport?.contract_id)}</strong><small>sealed_envelope=false</small></article>
        <article className="metric-card"><span>Finance Ref</span><strong>{displayValue(financeReference?.finance_status)}</strong><small>{displayValue(financeReference?.controlled_finance_payload_hash)}</small></article>
      </section>

      <section className="decision-command__grid" aria-label="Snapshot projection handoff output">
        <article className="panel">
          <div className="section-title"><BadgeCheck size={20} aria-hidden="true" /><h2>Snapshot Projection Handoff</h2></div>
          {handoff ? (
            <ul className="lineage-list">
              <li>handoff_id: <code>{displayValue(handoff.handoff_id)}</code></li>
              <li>contract_id: <code>{handoff.contract_id}</code></li>
              <li>planned_snapshot_id: <code>{displayValue(handoff.planned_snapshot_id)}</code></li>
              <li>payload_hash: <code>{displayValue(handoff.payload_hash)}</code></li>
              <li>sealed_envelope_created: <code>{String(handoff.sealed_envelope_created)}</code></li>
              <li>snapshot_wiring_enabled: <code>{String(handoff.snapshot_wiring_enabled)}</code></li>
            </ul>
          ) : <p className="muted">حمّل جلسة DIB تحتوي Manifest/Gate/Controlled Finance readiness، ثم جهز handoff.</p>}
        </article>
        <article className="panel">
          <div className="section-title"><AlertTriangle size={20} aria-hidden="true" /><h2>Blockers</h2></div>
          <ul className="lineage-list">
            {blockers.map((blocker) => <li key={blocker.code}>{blocker.severity}: <code>{blocker.code}</code> · {blocker.message}</li>)}
          </ul>
          {handoff && blockers.length === 0 ? <p className="muted">لا توجد موانع في handoff الحالي.</p> : null}
        </article>
      </section>

      <section className="decision-command__grid" aria-label="Projection boundaries">
        <article className="panel">
          <div className="section-title"><ShieldCheck size={20} aria-hidden="true" /><h2>الممنوع</h2></div>
          <ul className="lineage-list">
            {forbiddenBoundaries.map((item) => <li key={item}>{item}</li>)}
          </ul>
        </article>
        <article className="panel">
          <div className="section-title"><Boxes size={20} aria-hidden="true" /><h2>Projection Support</h2></div>
          <ul className="lineage-list">
            <li>lineage_contract: <code>{displayValue(projectionSupport?.source_lineage_contract_id)}</code></li>
            <li>projection_contract: <code>{displayValue(projectionSupport?.contract_id)}</code></li>
            <li>lineage_payload_hash: <code>{displayValue(projectionSupport?.lineage_payload_hash)}</code></li>
          </ul>
        </article>
        <article className="panel">
          <div className="section-title"><FileText size={20} aria-hidden="true" /><h2>API</h2></div>
          <ul className="lineage-list">
            <li><code>POST /api/dib/sessions/{"{session_id}"}/snapshot-projection-handoff</code></li>
            <li><code>dib.snapshot.projection_handoff.v1</code> كـhandoff فقط</li>
          </ul>
        </article>
      </section>
    </main>
  );
}
