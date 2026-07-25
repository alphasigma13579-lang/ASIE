import { useCallback, useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  ArrowLeft,
  BadgeCheck,
  CheckCircle2,
  Database,
  FileText,
  Layers3,
  Plus,
  RefreshCw,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { fetchProjectReadiness, fetchProjectRuns, fetchProjects } from "./api";
import type { Project, ProjectReadiness, Run } from "./contracts";

type DashboardProps = {
  onOpenProject: (projectId: string) => void;
  onNewProject: () => void;
  onOpenStage: (projectId: string, stage: "evidence" | "readiness" | "snapshots" | "decision") => void;
};

type ProjectRow = {
  project: Project;
  lastRun: Run | null;
  readiness: ProjectReadiness | null;
  completedMilestones: number;
  totalMilestones: number;
};

type AttentionItem = {
  id: string;
  projectId: string;
  title: string;
  detail: string;
  kind: "readiness" | "evidence" | "decision";
  stage: "evidence" | "readiness" | "snapshots" | "decision";
};

const MILESTONE_FALLBACK = 8;
const MAX_DASHBOARD_PROJECTS = 8;
const MAX_ATTENTION_ITEMS = 4;

function timeGreeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return "صباح الخير";
  if (hour < 18) return "مساء الخير";
  return "مساء النور";
}

function formatRelative(iso: string | null | undefined): string {
  if (!iso) return "—";
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "—";
  const diffMinutes = Math.max(0, Math.round((Date.now() - then) / 60000));
  if (diffMinutes < 1) return "الآن";
  if (diffMinutes < 60) return `قبل ${diffMinutes} دقيقة`;
  const diffHours = Math.round(diffMinutes / 60);
  if (diffHours < 24) return `قبل ${diffHours} ساعة`;
  const diffDays = Math.round(diffHours / 24);
  if (diffDays === 1) return "أمس";
  if (diffDays < 30) return `قبل ${diffDays} يوم`;
  return new Date(iso).toLocaleDateString("ar-SA", { year: "numeric", month: "short", day: "numeric" });
}

function verdictMeta(verdict: string | null | undefined): { label: string; tone: "go" | "warn" | "dim" } | null {
  if (!verdict) return null;
  if (verdict === "PRELIMINARY_ONLY") return { label: "قرار أولي متاح", tone: "go" };
  if (verdict === "REVISE_AND_REASSESS") return { label: "القرار يطلب مراجعة", tone: "warn" };
  return { label: "محجوب — أكمل النواقص", tone: "warn" };
}

function rowStatus(row: ProjectRow): { label: string; tone: "go" | "warn" | "dim" } {
  const verdict = verdictMeta(row.lastRun?.sovereign_verdict);
  if (verdict) return verdict;
  if (row.readiness?.ready_to_run) return { label: "جاهز للتشغيل", tone: "go" };
  return { label: "مسودة", tone: "dim" };
}

function nextStepLabel(row: ProjectRow): string {
  const steps = row.readiness?.steps ?? [];
  if (!steps.length) return "لم تُفحص الجاهزية بعد";
  const idx = steps.findIndex((item) => item.status !== "ready");
  if (idx === -1) return "كل خطوات الجاهزية مكتملة";
  const current = idx + 1;
  return `الخطوة ${current} من ${steps.length} · ${steps[idx].label}`;
}

function readinessPercent(row: ProjectRow): number {
  if (!row.totalMilestones) return 0;
  return Math.round((row.completedMilestones / row.totalMilestones) * 100);
}

function ReadinessDial({ percent, label }: { percent: number; label: string }) {
  const radius = 34;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (Math.min(100, Math.max(0, percent)) / 100) * circumference;
  return (
    <div className="dash-dial">
      <svg width="84" height="84" viewBox="0 0 84 84" aria-hidden="true">
        <circle cx="42" cy="42" r={radius} fill="none" stroke="var(--line)" strokeWidth="7" />
        <circle
          cx="42"
          cy="42"
          r={radius}
          fill="none"
          stroke="var(--em)"
          strokeWidth="7"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          style={{ transform: "rotate(-90deg)", transformOrigin: "center", transition: "stroke-dashoffset 0.5s ease" }}
        />
        <text x="42" y="47" textAnchor="middle" fill="var(--deep)" fontSize="14" fontWeight="700">
          {percent}%
        </text>
      </svg>
      <div className="dash-dial__label">
        <strong>جاهزية المشروع</strong>
        <span>{label}</span>
      </div>
    </div>
  );
}

export function Dashboard({ onOpenProject, onNewProject, onOpenStage }: DashboardProps) {
  const [rows, setRows] = useState<ProjectRow[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  const load = useCallback(async () => {
    setLoadError(null);
    try {
      const projects = await fetchProjects();
      const limited = projects.slice(0, MAX_DASHBOARD_PROJECTS);
      const nextRows = await Promise.all(
        limited.map(async (project) => {
          const [runs, readiness] = await Promise.all([
            fetchProjectRuns(project.project_id).catch(() => [] as Run[]),
            fetchProjectReadiness(project.project_id).catch(() => null),
          ]);
          const steps = readiness?.steps ?? [];
          const completed = steps.filter((item) => item.status === "ready").length;
          return {
            project,
            lastRun: runs[0] ?? null,
            readiness,
            completedMilestones: completed,
            totalMilestones: steps.length || MILESTONE_FALLBACK,
          } satisfies ProjectRow;
        })
      );
      setRows(nextRows);
    } catch (err) {
      setRows(null);
      setLoadError(err instanceof Error ? err.message : "تعذر تحميل لوحة القيادة.");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load, reloadKey]);

  const attention = useMemo(() => {
    if (!rows) return [];
    const items: AttentionItem[] = [];
    for (const row of rows) {
      const blockers = row.readiness?.blockers ?? [];
      for (const blocker of blockers.slice(0, 2)) {
        items.push({
          id: `${row.project.project_id}:${blocker.code}`,
          projectId: row.project.project_id,
          title: `${row.project.name} — يحتاج استكمال جاهزية`,
          detail: blocker.message,
          kind: "readiness",
          stage: "readiness",
        });
      }
      const sourcesStep = row.readiness?.steps.find((item) => item.step_id === "sources" && item.status !== "ready");
      if (sourcesStep) {
        items.push({
          id: `${row.project.project_id}:evidence`,
          projectId: row.project.project_id,
          title: `${row.project.name} — الأدلة غير مكتملة`,
          detail: sourcesStep.message || "اربط مصدراً أو دليلاً محلياً قبل تشغيل التحليل.",
          kind: "evidence",
          stage: "evidence",
        });
      }
      if (row.lastRun?.sovereign_verdict === "REVISE_AND_REASSESS") {
        items.push({
          id: `${row.project.project_id}:verdict`,
          projectId: row.project.project_id,
          title: `${row.project.name} — القرار يطلب مراجعة`,
          detail: "آخر حكم سيادي طلب المراجعة وإعادة التقييم. راجع حزمة القرار.",
          kind: "decision",
          stage: "decision",
        });
      }
    }
    return items.slice(0, MAX_ATTENTION_ITEMS);
  }, [rows]);

  if (loadError) {
    return (
      <div className="dash">
        <div className="dash-error">
          <AlertTriangle size={24} />
          <div>
            <strong>تعذر تحميل لوحة القيادة</strong>
            <p>{loadError}</p>
          </div>
          <button className="btn ghost sm" onClick={() => setReloadKey((key) => key + 1)}>
            <RefreshCw size={14} />
            إعادة المحاولة
          </button>
        </div>
      </div>
    );
  }

  if (rows === null) {
    return (
      <div className="dash">
        <div className="dash-skeleton">
          <span />
          <span />
          <span />
        </div>
      </div>
    );
  }

  if (rows.length === 0) {
    return (
      <div className="dash">
        <p className="crumb">ASIE / <b>لوحة القيادة</b></p>
        <div className="dash-empty">
          <p>{timeGreeting()} — ابدأ أول مشروع لك</p>
          <h1>
            من فكرة إلى <em>قرار موثق</em> خلال جلسة واحدة
          </h1>
          <div className="dash-empty__steps">
            <article>
              <span>01</span>
              <h3>عرّف مشروعك</h3>
              <p>الموقع، القطاع، ورأس المال في خطوات موجهة.</p>
            </article>
            <article>
              <span>02</span>
              <h3>اربط الأدلة</h3>
              <p>بياناتك وملفاتك تدعم كل افتراض.</p>
            </article>
            <article>
              <span>03</span>
              <h3>افحص الجاهزية</h3>
              <p>تظهر النواقص بوضوح قبل التشغيل.</p>
            </article>
            <article>
              <span>04</span>
              <h3>استلم القرار</h3>
              <p>حكم سيادي مع السبب والمخاطر والتالي.</p>
            </article>
          </div>
          <button className="btn main lg" onClick={onNewProject}>
            <Plus size={18} />
            ابدأ مشروعك الأول
          </button>
        </div>
      </div>
    );
  }

  const primary = rows[0];
  const primaryPercent = readinessPercent(primary);

  return (
    <div className="dash">
      <p className="crumb">ASIE / <b>لوحة القيادة</b></p>

      <div className="phead">
        <div>
          <h1 className="pt">{timeGreeting()} — مشاريعك ({rows.length}) بخير</h1>
          <p className="psub">
            كل ما يحتاج انتباهك اليوم في مكان واحد: جاهزية المشاريع، القرارات المعلقة، والخطوة التالية لكل مشروع.
          </p>
        </div>
        <ReadinessDial percent={primaryPercent} label={nextStepLabel(primary)} />
      </div>

      <div className="card">
        <h3>
          <Layers3 size={18} />
          مشاريعي
        </h3>
        <p className="why">مشاريعك مرتبة بأحدث تحديث. افتح أي مشروع لمتابعة رحلة القرار من حيث توقفت.</p>
        {rows.map((row) => {
          const status = rowStatus(row);
          return (
            <div className="row" key={row.project.project_id}>
              <span className={`st ${status.tone}`}>{status.label}</span>
              <div>
                <b>{row.project.name}</b>
                <span>
                  {nextStepLabel(row)} · آخر تحديث: {formatRelative(row.project.updated_at)}
                </span>
              </div>
              <button className="btn ghost sm" onClick={() => onOpenProject(row.project.project_id)}>
                فتح
                <ArrowLeft size={14} />
              </button>
            </div>
          );
        })}
        <button className="btn main sm" onClick={onNewProject}>
          <Plus size={14} />
          مشروع جديد
        </button>
      </div>

      <div className="card">
        <h3>
          <Sparkles size={18} />
          ينتبه له اليوم
        </h3>
        <p className="why">عناصر تحتاج إجراء منك — مستخرجة من جاهزية المشاريع وأحكامها المحفوظة فقط.</p>
        {attention.length === 0 ? (
          <div className="dash-clear">
            <CheckCircle2 size={20} />
            لا شيء يحتاج انتباهاً الآن — مشاريعك على المسار.
          </div>
        ) : (
          attention.map((item) => (
            <div className="row" key={item.id}>
              <span className={`st ${item.kind === "decision" ? "warn" : "dim"}`}>
                {item.kind === "readiness" ? "جاهزية" : item.kind === "evidence" ? "أدلة" : "قرار"}
              </span>
              <div>
                <b>{item.title}</b>
                <span>{item.detail}</span>
              </div>
              <button className="btn ghost sm" onClick={() => onOpenStage(item.projectId, item.stage)}>
                معالجة
                <ArrowLeft size={14} />
              </button>
            </div>
          ))
        )}
      </div>

      <div className="dash-principles">
        <article>
          <Database size={18} />
          <div>
            <strong>لا أرقام بلا مصدر</strong>
            <span>كل قيمة تعرضها المنصة مرتبطة بلقطة محفوظة أو مدخل موثق.</span>
          </div>
        </article>
        <article>
          <ShieldCheck size={18} />
          <div>
            <strong>بياناتك محلية</strong>
            <span>لا جلب خارجي ولا مفاتيح داخل الحزمة في هذه المرحلة.</span>
          </div>
        </article>
        <article>
          <FileText size={18} />
          <div>
            <strong>قرار قابل للرجوع</strong>
            <span>كل حكم يحمل مرجع لقطة ثابت يمكن مراجعته لاحقاً.</span>
          </div>
        </article>
        <article>
          <BadgeCheck size={18} />
          <div>
            <strong>المراجعة لك</strong>
            <span>المنصة تقترح وتوضح — القرار النهائي واعتماده لك دائماً.</span>
          </div>
        </article>
      </div>
    </div>
  );
}
