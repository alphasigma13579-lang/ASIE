import { useCallback, useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  ArrowLeft,
  BadgeCheck,
  BarChart3,
  BookOpen,
  CheckCircle2,
  ChevronRight,
  Database,
  FileText,
  FlaskConical,
  Layers3,
  LayoutDashboard,
  Lightbulb,
  Plus,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  Target,
  TrendingUp,
} from "lucide-react";
import { fetchProjectReadiness, fetchProjectRuns, fetchProjects, fetchRunOverview } from "./api";
import type { Project, ProjectOverview, ProjectReadiness, Run } from "./contracts";

// ─── Section union ───────────────────────────────────────────────────────────
type CCSection =
  | "dashboard"
  | "today"
  | "guide"
  | "reality"
  | "market"
  | "news"
  | "strategy"
  | "opportunities"
  | "decision"
  | "reports";

// ─── Props ────────────────────────────────────────────────────────────────────
type CommandCenterProps = {
  onOpenProject: (projectId: string) => void;
  onNewProject: () => void;
  onOpenStage: (projectId: string, stage: "evidence" | "readiness" | "snapshots" | "decision") => void;
};

// ─── Internal types ───────────────────────────────────────────────────────────
type ProjectRow = {
  project: Project;
  lastRun: Run | null;
  readiness: ProjectReadiness | null;
  overview: ProjectOverview | null;
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

// ─── Constants ────────────────────────────────────────────────────────────────
const MILESTONE_FALLBACK = 8;
const MAX_PROJECTS = 8;
const MAX_ATTENTION = 4;

// ─── Helpers ──────────────────────────────────────────────────────────────────
function timeGreeting(): string {
  const h = new Date().getHours();
  if (h < 12) return "صباح الخير";
  if (h < 18) return "مساء الخير";
  return "مساء النور";
}

function formatRelative(iso: string | null | undefined): string {
  if (!iso) return "—";
  const t = new Date(iso).getTime();
  if (Number.isNaN(t)) return "—";
  const m = Math.max(0, Math.round((Date.now() - t) / 60000));
  if (m < 1) return "الآن";
  if (m < 60) return `قبل ${m} دقيقة`;
  const hr = Math.round(m / 60);
  if (hr < 24) return `قبل ${hr} ساعة`;
  const d = Math.round(hr / 24);
  if (d === 1) return "أمس";
  if (d < 30) return `قبل ${d} يوم`;
  return new Date(iso).toLocaleDateString("ar-SA", { year: "numeric", month: "short", day: "numeric" });
}

function verdictMeta(verdict: string | null | undefined): { label: string; tone: "go" | "warn" | "dim" } | null {
  if (!verdict) return null;
  if (verdict === "PRELIMINARY_ONLY") return { label: "قرار أولي متاح", tone: "go" };
  if (verdict === "REVISE_AND_REASSESS") return { label: "القرار يطلب مراجعة", tone: "warn" };
  return { label: "محجوب — أكمل النواقص", tone: "warn" };
}

function kpiValue(overview: ProjectOverview | null, outputId: string): string {
  if (!overview) return "—";
  const env = overview.kpis?.find((k) => k.output_id === outputId);
  if (env?.value !== undefined && env.value !== null) {
    const v = Number(env.value);
    return Number.isNaN(v) ? String(env.value) : v.toLocaleString("ar-SA");
  }
  return "—";
}

function fmtSAR(n: number | null | undefined): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  if (Math.abs(n) >= 1_000_000) return `${(n / 1_000_000).toFixed(1)} م.ر`;
  if (Math.abs(n) >= 1_000) return `${(n / 1_000).toFixed(1)} ك.ر`;
  return `${n.toFixed(0)} ر.س`;
}

function fmtPct(n: number | null | undefined): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  return `${(n * 100).toFixed(1)}%`;
}

function fmtMonths(n: number | null | undefined): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  if (n < 1) return "أقل من شهر";
  if (n < 12) return `${Math.round(n)} شهر`;
  return `${(n / 12).toFixed(1)} سنة`;
}

function readinessPercent(row: ProjectRow): number {
  if (!row.totalMilestones) return 0;
  return Math.round((row.completedMilestones / row.totalMilestones) * 100);
}

function nextStepLabel(row: ProjectRow): string {
  const steps = row.readiness?.steps ?? [];
  if (!steps.length) return "لم تُفحص الجاهزية بعد";
  const idx = steps.findIndex((s) => s.status !== "ready");
  if (idx === -1) return "كل خطوات الجاهزية مكتملة";
  return `الخطوة ${idx + 1} من ${steps.length} · ${steps[idx].label}`;
}

// ─── Small UI helpers ─────────────────────────────────────────────────────────
function Chip({ label, tone }: { label: string; tone: "go" | "warn" | "dim" | "gold" }) {
  return <span className={`cc-chip cc-chip--${tone}`}>{label}</span>;
}

function Soon() {
  return (
    <div className="cc-soon">
      <Sparkles size={20} />
      <div>
        <strong>قيد التفعيل</strong>
        <p>هذا القسم سيكون متاحاً عند توصيل مصادر البيانات الخارجية.</p>
      </div>
    </div>
  );
}

function NeedData({ message }: { message?: string }) {
  return (
    <div className="cc-needdata">
      <Database size={18} />
      <span>{message ?? "لا توجد بيانات كافية لعرض هذا المقياس بعد."}</span>
    </div>
  );
}

function SectionShell({ title, icon, children }: { title: string; icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <section className="cc-card">
      <h2 className="cc-section__title">
        {icon}
        {title}
      </h2>
      {children}
    </section>
  );
}

// ─── Dial ─────────────────────────────────────────────────────────────────────
function Dial({ percent }: { percent: number }) {
  const r = 38;
  const circ = 2 * Math.PI * r;
  const offset = circ - (Math.min(100, Math.max(0, percent)) / 100) * circ;
  return (
    <div className="cc-dial">
      <svg width="96" height="96" viewBox="0 0 96 96" aria-hidden="true">
        <circle cx="48" cy="48" r={r} fill="none" stroke="var(--line)" strokeWidth="8" />
        <circle
          cx="48"
          cy="48"
          r={r}
          fill="none"
          stroke="var(--em)"
          strokeWidth="8"
          strokeDasharray={circ}
          strokeDashoffset={offset}
          strokeLinecap="round"
          style={{ transform: "rotate(-90deg)", transformOrigin: "center", transition: "stroke-dashoffset 0.6s ease" }}
        />
        <text x="48" y="54" textAnchor="middle" fill="var(--deep)" fontSize="15" fontWeight="700">
          {percent}%
        </text>
      </svg>
      <p className="cc-datafoot">جاهزية المشروع</p>
    </div>
  );
}

// ─── TopNav ───────────────────────────────────────────────────────────────────
function TopNav({
  active,
  onNav,
}: {
  active: CCSection;
  onNav: (s: CCSection) => void;
}) {
  const links: { id: CCSection; label: string }[] = [
    { id: "dashboard", label: "لوحة القيادة" },
    { id: "today", label: "قراري اليوم" },
    { id: "guide", label: "مرشد التأسيس" },
    { id: "reality", label: "اختبار الواقع" },
    { id: "market", label: "السوق والاتجاهات" },
    { id: "decision", label: "فهم القرار" },
    { id: "reports", label: "تقاريري" },
  ];
  return (
    <nav className="cc-topnav" aria-label="Command Center navigation">
      <div className="cc-topnav__brand">
        <LayoutDashboard size={20} />
        <span>ASIE / المستشار الاستراتيجي التفاعلي</span>
      </div>
      <div className="cc-topnav__links">
        {links.map((l) => (
          <button
            key={l.id}
            className={`cc-navlink${active === l.id ? " cc-navlink--active" : ""}`}
            onClick={() => onNav(l.id)}
          >
            {l.label}
          </button>
        ))}
      </div>
      <div className="cc-topnav__mode">
        <span className="cc-dot" />
        محلي · LOCAL ONLY
      </div>
    </nav>
  );
}

// ─── AttentionList ────────────────────────────────────────────────────────────
function AttentionList({
  items,
  onOpenStage,
}: {
  items: AttentionItem[];
  onOpenStage: (projectId: string, stage: "evidence" | "readiness" | "snapshots" | "decision") => void;
}) {
  if (items.length === 0) {
    return (
      <div className="cc-clear">
        <CheckCircle2 size={20} />
        لا شيء يحتاج انتباهاً الآن — مشاريعك على المسار.
      </div>
    );
  }
  return (
    <div className="cc-stack">
      {items.map((item) => (
        <div className="cc-row" key={item.id}>
          <div className="cc-row__body">
            <Chip label={item.kind === "readiness" ? "جاهزية" : item.kind === "evidence" ? "أدلة" : "قرار"} tone={item.kind === "decision" ? "warn" : "dim"} />
            <div>
              <b>{item.title}</b>
              <span>{item.detail}</span>
            </div>
          </div>
          <button className="cc-btn cc-btn--ghost cc-btn--sm" onClick={() => onOpenStage(item.projectId, item.stage)}>
            معالجة
            <ArrowLeft size={14} />
          </button>
        </div>
      ))}
    </div>
  );
}

// ─── Section components ───────────────────────────────────────────────────────

function DecisionToday({ rows }: { rows: ProjectRow[] }) {
  const primary = rows[0] ?? null;
  if (!primary) return <NeedData message="أنشئ مشروعاً أولاً لترى قرارات اليوم." />;
  const verdict = verdictMeta(primary.lastRun?.sovereign_verdict);
  const ov = primary.overview;
  const baseline = ov?.finance?.baseline ?? null;
  return (
    <div className="cc-decision-hero">
      <div>
        <p className="cc-crumb">قراري اليوم · {primary.project.name}</p>
        {verdict ? (
          <div className={`cc-verdict cc-verdict--${verdict.tone}`}>{verdict.label}</div>
        ) : (
          <div className="cc-verdict cc-verdict--dim">لا حكم بعد — شغّل التحليل أولاً</div>
        )}
        <div className="cc-decision-metrics">
          <div className="cc-kpi-cell">
            <span>الربح الشهري</span>
            <strong>{baseline ? fmtSAR(baseline.monthly_profit) : "—"}</strong>
          </div>
          <div className="cc-kpi-cell">
            <span>الاستثمار الأولي</span>
            <strong>{baseline ? fmtSAR(baseline.initial_investment) : "—"}</strong>
          </div>
          <div className="cc-kpi-cell">
            <span>فترة الاسترداد</span>
            <strong>{baseline ? fmtMonths(baseline.payback_months) : "—"}</strong>
          </div>
          <div className="cc-kpi-cell">
            <span>NPV</span>
            <strong>{baseline ? fmtSAR(baseline.npv) : "—"}</strong>
          </div>
        </div>
        {!baseline && <NeedData message="شغّل التحليل لترى الأرقام المالية الموثقة." />}
      </div>
      {primary && <Dial percent={readinessPercent(primary)} />}
    </div>
  );
}

function GuideSection({ rows }: { rows: ProjectRow[] }) {
  const primary = rows[0] ?? null;
  if (!primary) return <NeedData message="أنشئ مشروعاً لترى مرشد التأسيس." />;
  const steps = primary.readiness?.steps ?? [];
  const done = steps.filter((s) => s.status === "ready").length;
  const pending = steps.filter((s) => s.status !== "ready");
  return (
    <div>
      <div className="cc-bars">
        <div className="cc-bar" style={{ width: `${steps.length ? Math.round((done / steps.length) * 100) : 0}%` }} />
      </div>
      <p className="cc-datafoot">{done} من {steps.length} خطوات جاهزية مكتملة · {primary.project.name}</p>
      {pending.length > 0 && (
        <div className="cc-stack" style={{ marginTop: "12px" }}>
          {pending.slice(0, 4).map((s) => (
            <div className="cc-row" key={s.step_id}>
              <div className="cc-row__body">
                <Chip label="ينتظر" tone="warn" />
                <div>
                  <b>{s.label}</b>
                  {s.message && <span>{s.message}</span>}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
      {pending.length === 0 && (
        <div className="cc-clear">
          <CheckCircle2 size={18} />
          كل خطوات الجاهزية مكتملة — المشروع جاهز للتشغيل.
        </div>
      )}
    </div>
  );
}

function RealitySection({ rows }: { rows: ProjectRow[] }) {
  const primary = rows[0] ?? null;
  const baseline = primary?.overview?.finance?.baseline ?? null;
  if (!baseline) return <NeedData message="شغّل التحليل لترى اختبار الواقع المالي." />;
  const mc = primary?.overview?.monte_carlo;
  const prob = mc?.p_pass ?? null;
  return (
    <div className="cc-kpi-grid">
      <div className="cc-kpi-cell">
        <span>التعادل (وحدات/شهر)</span>
        <strong className="cc-row__val">{baseline.break_even_units.toLocaleString("ar-SA")}</strong>
      </div>
      <div className="cc-kpi-cell">
        <span>احتمال النجاح (MC)</span>
        <strong className="cc-row__val">{prob !== null ? fmtPct(prob) : "—"}</strong>
      </div>
      <div className="cc-kpi-cell">
        <span>EBITDA الشهري</span>
        <strong className="cc-row__val">{fmtSAR(baseline.ebitda)}</strong>
      </div>
      <div className="cc-kpi-cell">
        <span>الفجوة التمويلية</span>
        <strong className="cc-row__val">{fmtSAR(baseline.funding_gap)}</strong>
      </div>
      <div className="cc-kpi-cell">
        <span>هامش المساهمة</span>
        <strong className="cc-row__val">{fmtSAR(baseline.contribution_margin)}</strong>
      </div>
      <div className="cc-kpi-cell">
        <span>IRR</span>
        <strong className="cc-row__val">{baseline.irr !== null ? fmtPct(baseline.irr) : "—"}</strong>
      </div>
    </div>
  );
}

function StrategySection() {
  return <Soon />;
}

function OpportunitiesSection() {
  return <Soon />;
}

function DecisionSection({ rows }: { rows: ProjectRow[] }) {
  const primary = rows[0] ?? null;
  const council = primary?.overview?.decision_council ?? null;
  if (!council) return <NeedData message="شغّل التحليل لترى حزمة القرار." />;
  const verdict = council.verdict;
  const meta = verdictMeta(verdict?.sovereign_verdict);
  return (
    <div>
      {meta && (
        <div className={`cc-verdict cc-verdict--${meta.tone}`} style={{ marginBottom: "12px" }}>
          {meta.label}
        </div>
      )}
      {verdict?.reason && <p className="cc-reason">{verdict.reason}</p>}
      <div className="cc-gate">
        {council.personas?.slice(0, 3).map((p) => (
          <div className="cc-row" key={p.persona_id}>
            <div className="cc-row__body">
              <Chip label={p.persona_id} tone="dim" />
              <div>
                <b>{p.metric ?? p.persona_id}</b>
                {p.note && <span>{p.note}</span>}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function ReportsSection({ rows }: { rows: ProjectRow[] }) {
  if (!rows.length) return <NeedData message="أنشئ مشروعاً أولاً لترى التقارير." />;
  return (
    <div className="cc-stack">
      {rows.map((row) => {
        const verdict = verdictMeta(row.lastRun?.sovereign_verdict);
        return (
          <div className="cc-row" key={row.project.project_id}>
            <div className="cc-row__body">
              {verdict ? <Chip label={verdict.label} tone={verdict.tone} /> : <Chip label="مسودة" tone="dim" />}
              <div>
                <b>{row.project.name}</b>
                <span>آخر تحديث: {formatRelative(row.project.updated_at)}</span>
              </div>
            </div>
            {row.lastRun?.snapshot_id && (
              <span className="cc-datafoot">لقطة #{row.lastRun.snapshot_id.slice(0, 8)}</span>
            )}
          </div>
        );
      })}
    </div>
  );
}

// ─── Main CommandCenter ───────────────────────────────────────────────────────
export function CommandCenter({ onOpenProject, onNewProject, onOpenStage }: CommandCenterProps) {
  const [section, setSection] = useState<CCSection>("dashboard");
  const [rows, setRows] = useState<ProjectRow[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  const load = useCallback(async () => {
    setLoadError(null);
    try {
      const projects = await fetchProjects();
      const limited = projects.slice(0, MAX_PROJECTS);
      const nextRows = await Promise.all(
        limited.map(async (project) => {
          const [runs, readiness] = await Promise.all([
            fetchProjectRuns(project.project_id).catch(() => [] as Run[]),
            fetchProjectReadiness(project.project_id).catch(() => null),
          ]);
          const latest = runs[0] ?? null;
          let overview: ProjectOverview | null = null;
          if (latest?.snapshot_id) {
            overview = await fetchRunOverview(latest.run_id).catch(() => null);
          }
          const steps = readiness?.steps ?? [];
          const completed = steps.filter((s) => s.status === "ready").length;
          return {
            project,
            lastRun: latest,
            readiness,
            overview,
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

  const attention = useMemo<AttentionItem[]>(() => {
    if (!rows) return [];
    const items: AttentionItem[] = [];
    for (const row of rows) {
      for (const blocker of (row.readiness?.blockers ?? []).slice(0, 2)) {
        items.push({
          id: `${row.project.project_id}:${blocker.code}`,
          projectId: row.project.project_id,
          title: `${row.project.name} — يحتاج استكمال جاهزية`,
          detail: blocker.message,
          kind: "readiness",
          stage: "readiness",
        });
      }
      const sourcesStep = row.readiness?.steps.find((s) => s.step_id === "sources" && s.status !== "ready");
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
    return items.slice(0, MAX_ATTENTION);
  }, [rows]);

  // ── loading / error / skeleton states ──────────────────────────────────────
  if (loadError) {
    return (
      <div className="cc">
        <TopNav active={section} onNav={setSection} />
        <div className="cc-error">
          <AlertTriangle size={24} />
          <div>
            <strong>تعذر تحميل لوحة القيادة</strong>
            <p>{loadError}</p>
          </div>
          <button className="cc-btn cc-btn--ghost cc-btn--sm" onClick={() => setReloadKey((k) => k + 1)}>
            <RefreshCw size={14} />
            إعادة المحاولة
          </button>
        </div>
      </div>
    );
  }

  if (rows === null) {
    return (
      <div className="cc">
        <TopNav active={section} onNav={setSection} />
        <div className="cc-skel">
          <span />
          <span />
          <span />
        </div>
      </div>
    );
  }

  // ── empty state ────────────────────────────────────────────────────────────
  if (rows.length === 0) {
    return (
      <div className="cc">
        <TopNav active={section} onNav={setSection} />
        <p className="cc-crumb">ASIE / <b>لوحة القيادة</b></p>
        <div className="cc-empty">
          <p>{timeGreeting()} — ابدأ أول مشروع لك</p>
          <h1>من فكرة إلى <em>قرار موثق</em> خلال جلسة واحدة</h1>
          <button className="cc-btn cc-btn--main cc-btn--lg" onClick={onNewProject}>
            <Plus size={18} />
            ابدأ مشروعك الأول
          </button>
        </div>
      </div>
    );
  }

  const primary = rows[0];
  const primaryPercent = readinessPercent(primary);
  const baseline = primary.overview?.finance?.baseline ?? null;

  // ── render ─────────────────────────────────────────────────────────────────
  return (
    <div className="cc">
      <TopNav active={section} onNav={setSection} />
      <p className="cc-crumb">ASIE / <b>لوحة القيادة</b></p>

      {/* ── DASHBOARD section ────────────────────────────────────────────── */}
      {section === "dashboard" && (
        <div>
          {/* Hero */}
          <div className="cc-hero">
            <div>
              <h1>{timeGreeting()} — مشاريعك ({rows.length}) بخير</h1>
              <p>كل ما يحتاج انتباهك اليوم في مكان واحد: جاهزية المشاريع، القرارات المعلقة، والخطوة التالية.</p>
            </div>
            <Dial percent={primaryPercent} />
          </div>

          {/* KPI strip */}
          <div className="cc-kpi-strip">
            <div className="cc-kpi">
              <span>الربح الشهري (أساسي)</span>
              <strong>{baseline ? fmtSAR(baseline.monthly_profit) : "—"}</strong>
              <small>{baseline ? "من آخر تحليل" : "شغّل التحليل"}</small>
            </div>
            <div className="cc-kpi">
              <span>فترة الاسترداد</span>
              <strong>{baseline ? fmtMonths(baseline.payback_months) : "—"}</strong>
              <small>{baseline ? "سيناريو أساسي" : "—"}</small>
            </div>
            <div className="cc-kpi">
              <span>جاهزية المشروع</span>
              <strong>{primaryPercent}%</strong>
              <small>{nextStepLabel(primary)}</small>
            </div>
          </div>

          {/* 2-col grid */}
          <div className="cc-grid-2">
            {/* Projects card */}
            <div className="cc-card">
              <h3><Layers3 size={18} /> مشاريعي</h3>
              <p className="cc-why">مشاريعك مرتبة بأحدث تحديث. افتح أي مشروع لمتابعة رحلة القرار.</p>
              <div className="cc-stack">
                {rows.map((row) => {
                  const verdict = verdictMeta(row.lastRun?.sovereign_verdict);
                  const tone = verdict?.tone ?? (row.readiness?.ready_to_run ? "go" : "dim");
                  const statusLabel = verdict?.label ?? (row.readiness?.ready_to_run ? "جاهز للتشغيل" : "مسودة");
                  return (
                    <div className="cc-row" key={row.project.project_id}>
                      <div className="cc-row__body">
                        <Chip label={statusLabel} tone={tone} />
                        <div>
                          <b>{row.project.name}</b>
                          <span>{nextStepLabel(row)} · {formatRelative(row.project.updated_at)}</span>
                        </div>
                      </div>
                      <button className="cc-btn cc-btn--ghost cc-btn--sm" onClick={() => onOpenProject(row.project.project_id)}>
                        فتح <ArrowLeft size={14} />
                      </button>
                    </div>
                  );
                })}
              </div>
              <button className="cc-btn cc-btn--main cc-btn--sm" onClick={onNewProject} style={{ marginTop: "12px" }}>
                <Plus size={14} /> مشروع جديد
              </button>
            </div>

            {/* Attention card */}
            <div className="cc-card">
              <h3><Sparkles size={18} /> ينتبه له اليوم</h3>
              <p className="cc-why">عناصر تحتاج إجراء منك — مستخرجة من جاهزية المشاريع وأحكامها المحفوظة فقط.</p>
              <AttentionList items={attention} onOpenStage={onOpenStage} />
            </div>
          </div>

          {/* Principles strip */}
          <div className="cc-principles">
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
      )}

      {/* ── TODAY section ─────────────────────────────────────────────────── */}
      {section === "today" && (
        <SectionShell title="قراري اليوم" icon={<Target size={20} />}>
          <DecisionToday rows={rows} />
        </SectionShell>
      )}

      {/* ── GUIDE section ─────────────────────────────────────────────────── */}
      {section === "guide" && (
        <SectionShell title="مرشد التأسيس" icon={<BookOpen size={20} />}>
          <GuideSection rows={rows} />
        </SectionShell>
      )}

      {/* ── REALITY section ───────────────────────────────────────────────── */}
      {section === "reality" && (
        <SectionShell title="اختبار الواقع" icon={<FlaskConical size={20} />}>
          <RealitySection rows={rows} />
        </SectionShell>
      )}

      {/* ── MARKET section (coming) ───────────────────────────────────────── */}
      {section === "market" && (
        <SectionShell title="السوق والاتجاهات" icon={<TrendingUp size={20} />}>
          <Soon />
        </SectionShell>
      )}

      {/* ── NEWS section (coming) ─────────────────────────────────────────── */}
      {section === "news" && (
        <SectionShell title="آخر الأخبار" icon={<Lightbulb size={20} />}>
          <Soon />
        </SectionShell>
      )}

      {/* ── STRATEGY section (coming) ─────────────────────────────────────── */}
      {section === "strategy" && (
        <SectionShell title="الاستراتيجية" icon={<ChevronRight size={20} />}>
          <StrategySection />
        </SectionShell>
      )}

      {/* ── OPPORTUNITIES section (coming) ────────────────────────────────── */}
      {section === "opportunities" && (
        <SectionShell title="الفرص" icon={<BarChart3 size={20} />}>
          <OpportunitiesSection />
        </SectionShell>
      )}

      {/* ── DECISION section ──────────────────────────────────────────────── */}
      {section === "decision" && (
        <SectionShell title="فهم القرار" icon={<ShieldCheck size={20} />}>
          <DecisionSection rows={rows} />
        </SectionShell>
      )}

      {/* ── REPORTS section ───────────────────────────────────────────────── */}
      {section === "reports" && (
        <SectionShell title="تقاريري" icon={<FileText size={20} />}>
          <ReportsSection rows={rows} />
        </SectionShell>
      )}
    </div>
  );
}
