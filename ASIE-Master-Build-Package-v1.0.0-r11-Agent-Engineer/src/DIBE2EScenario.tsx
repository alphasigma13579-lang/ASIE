import { useEffect, useMemo, useState } from "react";
import { fetchDIBEvents, fetchDIBSession, DIBEventRecord, DIBSessionRecord } from "./dibApi";
import { getActiveOrganizationId, getSessionToken, handleUnauthorized } from "./session";

export const DIB_E2E_SCENARIO_UI_ID = "DIB-COMPLETION-PACKAGE-G-E2E-SCENARIO-v1";

type E2EStep = {
  name: string;
  status: string;
  contract_id?: string | null;
  artifact_id?: string | null;
  blocker?: string | null;
};

type E2EReport = {
  e2e_scenario_id: string;
  contract_id: string;
  status: string;
  project_id: string;
  session_id: string;
  scenario_id: string;
  steps: E2EStep[];
  blockers: Array<{ code: string; severity: string; message: string }>;
  controlled_finance_status?: string | null;
  snapshot_projection_handoff_status?: string | null;
  audit_events_present: boolean;
  event_count: number;
  payload_hash: string;
  project_run_workflow_mount: string;
  snapshot_assembly_mount: string;
  sealed_envelope_created: boolean;
  decision_pack_created: boolean;
  external_fetch_enabled: boolean;
  ai_provider_enabled: boolean;
  finance_wiring_enabled: boolean;
  snapshot_wiring_enabled: boolean;
};

function sessionIdFromHash(): string {
  const hash = window.location.hash;
  const query = hash.includes("?") ? hash.slice(hash.indexOf("?") + 1) : "";
  return new URLSearchParams(query).get("session_id") ?? "";
}

async function requestDIBE2EReport(sessionId: string, scenarioId: string): Promise<E2EReport> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const token = getSessionToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  const organizationId = getActiveOrganizationId();
  if (organizationId) headers["X-ASIE-Organization-Id"] = organizationId;
  const response = await fetch(`/api/dib/sessions/${encodeURIComponent(sessionId)}/e2e-scenario`, {
    method: "POST",
    headers,
    body: JSON.stringify({ scenario_id: scenarioId }),
  });
  if (response.status === 401 && token) handleUnauthorized();
  const payload = await response.json() as { e2e_scenario?: E2EReport; error?: string };
  if (!response.ok || !payload.e2e_scenario) {
    throw new Error(payload.error ?? `تعذر بناء تقرير E2E (${response.status})`);
  }
  return payload.e2e_scenario;
}

export function DIBE2EScenario() {
  const [sessionId, setSessionId] = useState(sessionIdFromHash());
  const [scenarioId, setScenarioId] = useState("baseline");
  const [session, setSession] = useState<DIBSessionRecord | null>(null);
  const [events, setEvents] = useState<DIBEventRecord[]>([]);
  const [report, setReport] = useState<E2EReport | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const readyState = useMemo(() => ({
    hasSession: Boolean(session),
    hasBlueprint: Boolean(session?.current_blueprint),
    hasManifest: Boolean(session?.approved_manifest),
    hasGate: Boolean(session?.validation_gate),
    hasAudit: events.some((event) => String(event.event_type).startsWith("security.rbac.")),
  }), [events, session]);

  async function loadSession() {
    if (!sessionId.trim()) {
      setError("أدخل DIB Session ID أولًا.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const loaded = await fetchDIBSession(sessionId.trim());
      const loadedEvents = await fetchDIBEvents(sessionId.trim());
      setSession(loaded);
      setEvents(loadedEvents);
      setReport(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "تعذر تحميل الجلسة.");
    } finally {
      setBusy(false);
    }
  }

  async function buildReport() {
    if (!sessionId.trim()) {
      setError("أدخل DIB Session ID أولًا.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const built = await requestDIBE2EReport(sessionId.trim(), scenarioId.trim() || "baseline");
      setReport(built);
      const loadedEvents = await fetchDIBEvents(sessionId.trim());
      setEvents(loadedEvents);
    } catch (err) {
      setError(err instanceof Error ? err.message : "تعذر بناء تقرير E2E.");
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    if (sessionId) void loadSession();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <main dir="rtl" className="dib-workspace">
      <section className="cc-card dib-hero">
        <p className="eyebrow">DIB Completion Package G · {DIB_E2E_SCENARIO_UI_ID}</p>
        <h1>سيناريو DIB الكامل · End-to-End</h1>
        <p>
          هذه الصفحة تختبر تسلسل DIB الكامل من Session إلى Blueprint ثم Manifest وValidation وControlled Finance وSnapshot Projection Handoff.
          لا تستدعي ProjectRunWorkflow، ولا Snapshot Assembly، ولا Decision Pack، ولا AI Provider، ولا External Network.
        </p>
        <div className="dib-boundary-grid">
          <span>ProjectRunWorkflow: not_called</span>
          <span>Snapshot Assembly: not_called</span>
          <span>AI Provider: disabled</span>
          <span>External Network: disabled</span>
        </div>
      </section>

      <section className="cc-card">
        <h2>تحميل الجلسة</h2>
        <label>
          DIB Session ID
          <input value={sessionId} onChange={(event) => setSessionId(event.target.value)} placeholder="dib_session_..." />
        </label>
        <label>
          Scenario ID
          <input value={scenarioId} onChange={(event) => setScenarioId(event.target.value)} placeholder="baseline" />
        </label>
        <div className="dib-actions">
          <button type="button" onClick={loadSession} disabled={busy || !sessionId.trim()}>تحميل الجلسة</button>
          <button type="button" onClick={buildReport} disabled={busy || !sessionId.trim()}>بناء تقرير E2E</button>
        </div>
        {error ? <p className="error-text">{error}</p> : null}
      </section>

      <section className="cc-card">
        <h2>حالة الجلسة</h2>
        <div className="metric-grid">
          <span>Session: {readyState.hasSession ? "محمّلة" : "غير محمّلة"}</span>
          <span>Blueprint: {readyState.hasBlueprint ? "موجود" : "غير موجود"}</span>
          <span>Manifest: {readyState.hasManifest ? "موجود" : "غير موجود"}</span>
          <span>Validation Gate: {readyState.hasGate ? "موجود" : "غير موجود"}</span>
          <span>Audit Events: {readyState.hasAudit ? "مرصودة" : "غير مرصودة/غير مطلوبة"}</span>
        </div>
        {session ? <pre>{JSON.stringify({ session_id: session.session_id, project_id: session.project_id, status: session.status }, null, 2)}</pre> : null}
      </section>

      {report ? (
        <section className="cc-card">
          <h2>تقرير السيناريو الكامل</h2>
          <p className={report.status === "passed" ? "success-text" : "warning-text"}>Status: {report.status}</p>
          <div className="metric-grid">
            <span>Controlled Finance: {report.controlled_finance_status ?? "غير منفذ"}</span>
            <span>Snapshot Handoff: {report.snapshot_projection_handoff_status ?? "غير جاهز"}</span>
            <span>Audit events: {report.audit_events_present ? "نعم" : "لا"}</span>
            <span>Payload hash: {report.payload_hash}</span>
          </div>
          <h3>الخطوات</h3>
          <ul className="dib-step-list">
            {report.steps.map((step) => (
              <li key={step.name}>
                <strong>{step.name}</strong> — {step.status}
                {step.contract_id ? <small> · {step.contract_id}</small> : null}
              </li>
            ))}
          </ul>
          {report.blockers.length ? (
            <>
              <h3>العوائق</h3>
              <ul>
                {report.blockers.map((blocker) => <li key={blocker.code}>{blocker.code}: {blocker.message}</li>)}
              </ul>
            </>
          ) : null}
          <pre>{JSON.stringify(report, null, 2)}</pre>
        </section>
      ) : null}
    </main>
  );
}
