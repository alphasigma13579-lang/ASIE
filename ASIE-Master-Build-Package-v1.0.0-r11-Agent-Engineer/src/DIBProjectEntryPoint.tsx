import { AlertTriangle, ArrowLeft, Database, RefreshCcw, Send, Sparkles } from "lucide-react";
import { useEffect, useState } from "react";
import { fetchProjects } from "./api";
import type { Project } from "./contracts";

export const DIB_PROJECT_WIZARD_ENTRY_POINT_ID = "DIB-LIVE-002L-PROJECT-WIZARD-ENTRY-POINT-v1";

function dibProjectUrl(projectId: string): string {
  return `#dib?project_id=${encodeURIComponent(projectId)}`;
}

function openDIBForProject(projectId: string) {
  window.location.hash = dibProjectUrl(projectId);
  window.location.reload();
}

export function DIBProjectEntryPoint() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  async function loadProjects() {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      setProjects(await fetchProjects());
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "تعذر تحميل مشاريع ASIE.");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void loadProjects();
  }, []);

  return (
    <main id="main-content" className="app-shell dib-workspace" dir="rtl" data-entry-id={DIB_PROJECT_WIZARD_ENTRY_POINT_ID}>
      <section className="page-intro">
        <p className="eyebrow"><Sparkles size={16} aria-hidden="true" /> DIB-LIVE-002L · مدخل DIB من مشروع المستخدم</p>
        <h1>افتح Dynamic Input Blueprint لمشروع حقيقي</h1>
        <p>
          هذه الصفحة تعرض مشاريع ASIE الفعلية وتفتح <code>#dib?project_id=&lt;project_id&gt;</code> للمشروع المختار.
          لا تشغّل Finance Engine، ولا تنشئ Snapshot، ولا تفعل AI Provider، ولا تنفذ أي جلب شبكي خارجي.
        </p>
        {errorMessage ? <p className="error-banner"><AlertTriangle size={16} aria-hidden="true" /> {errorMessage}</p> : null}
        <div className="button-row">
          <a className="secondary-button" href="#dashboard"><ArrowLeft size={16} aria-hidden="true" /> العودة للوحة القيادة</a>
          <button type="button" className="secondary-button" onClick={() => void loadProjects()} disabled={isLoading}>
            <RefreshCcw size={16} aria-hidden="true" /> تحديث المشاريع
          </button>
        </div>
      </section>

      <section className="panel" aria-label="مشاريع ASIE المتاحة لـDIB">
        <div className="section-title"><Database size={20} aria-hidden="true" /><h2>اختر مشروعًا لفتح DIB</h2></div>
        {isLoading ? <p className="muted">جاري تحميل المشاريع...</p> : null}
        {!isLoading && projects.length === 0 ? (
          <div className="status-banner" role="status">
            <AlertTriangle size={18} aria-hidden="true" />
            <span>لا توجد مشاريع بعد. أنشئ مشروعًا من معالج المشروع ثم عد إلى هذه الصفحة.</span>
          </div>
        ) : null}
        <div className="remediation-list">
          {projects.map((project) => (
            <article key={project.project_id}>
              <strong>{project.name}</strong>
              <span>{project.sector} · {project.jurisdiction}</span>
              <small>project_id: <code>{project.project_id}</code> · intake_mode: <code>{project.inputs.intake_mode ?? "غير محدد"}</code></small>
              <div className="button-row">
                <a className="secondary-button" href={dibProjectUrl(project.project_id)}>نسخ/فتح رابط DIB</a>
                <button type="button" className="primary-button" onClick={() => openDIBForProject(project.project_id)}>
                  <Send size={15} aria-hidden="true" /> افتح DIB لهذا المشروع
                </button>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="panel" aria-label="حدود مدخل DIB">
        <div className="section-title"><AlertTriangle size={20} aria-hidden="true" /><h2>حدود التشغيل</h2></div>
        <ul className="lineage-list">
          <li>Finance wiring = <code>false</code></li>
          <li>Snapshot wiring = <code>false</code></li>
          <li>AI Provider = <code>disabled</code></li>
          <li>Network Fetch = <code>disabled</code></li>
          <li>Route contract = <code>#dib?project_id=&lt;project_id&gt;</code></li>
        </ul>
      </section>
    </main>
  );
}
