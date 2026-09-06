import { useCallback, useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  ArrowLeft,
  BadgeCheck,
  BarChart3,
  CheckCircle2,
  Database,
  FileText,
  Globe,
  Layers3,
  Lightbulb,
  MapPin,
  Newspaper,
  Plus,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  Target,
  TrendingUp,
} from "lucide-react";
import {
  fetchProjectReadiness,
  fetchProjectRuns,
  fetchProjects,
  fetchRunOverview,
} from "./api";
import { customerBusinessText, customerErrorText, customerNarrativeText, useCustomerLanguage } from "./customerLanguage";
import type { OutputEnvelope, Project, ProjectOverview, ProjectReadiness } from "./contracts";

/* ------------------------------------------------------------------ */
/* Types                                                                */
/* ------------------------------------------------------------------ */

export type CCSection =
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

type CommandCenterProps = {
  onOpenProject: (projectId: string) => void;
  onNewProject: () => void;
  onOpenStage: (projectId: string, stage: "evidence" | "readiness" | "snapshots" | "decision" | "run") => void;
};

type Bundle = {
  project: Project;
  overview: ProjectOverview | null;
  readiness: ProjectReadiness | null;
};

/* ------------------------------------------------------------------ */
/* Small helpers                                                        */
/* ------------------------------------------------------------------ */

type Locale = "ar" | "en";

function timeGreeting(locale: Locale): string {
  const h = new Date().getHours();
  if (locale === "en") return h < 12 ? "Good morning" : h < 18 ? "Good afternoon" : "Good evening";
  return h < 12 ? "صباح الخير" : h < 18 ? "مساء الخير" : "مساء النور";
}

function formatRelative(iso: string | null | undefined, locale: Locale): string {
  if (!iso) return "—";
  const t = new Date(iso).getTime();
  if (Number.isNaN(t)) return "—";
  const minutes = Math.max(0, Math.round((Date.now() - t) / 60000));
  const formatter = new Intl.RelativeTimeFormat(locale === "ar" ? "ar-SA" : "en", { numeric: "auto" });
  if (minutes < 60) return formatter.format(-minutes, "minute");
  const hours = Math.round(minutes / 60);
  if (hours < 24) return formatter.format(-hours, "hour");
  const days = Math.round(hours / 24);
  if (days < 30) return formatter.format(-days, "day");
  return new Date(iso).toLocaleDateString(locale === "ar" ? "ar-SA" : "en-US", { year: "numeric", month: "short", day: "numeric" });
}

function kpiValue(overview: ProjectOverview | null, id: string): number | null {
  const item = overview?.kpis.find((k) => k.output_id === id);
  return typeof item?.value === "number" && Number.isFinite(item.value) ? item.value : null;
}

function fmtSAR(v: number | null, locale: Locale): string {
  if (v === null) return "—";
  return new Intl.NumberFormat(locale === "ar" ? "ar-SA" : "en-US", {
    style: "currency",
    currency: "SAR",
    maximumFractionDigits: 0,
  }).format(v);
}
function fmtPct(v: number | null, locale: Locale): string {
  if (v === null) return "—";
  return new Intl.NumberFormat(locale === "ar" ? "ar-SA" : "en-US", {
    style: "percent",
    maximumFractionDigits: 0,
  }).format(v);
}

function verdictMeta(verdict: string | null | undefined, locale: Locale): { label: string; tone: "go" | "warn" | "stop" } {
  if (verdict === "PRELIMINARY_ONLY") return { label: locale === "ar" ? "ابدأ بحذر" : "Proceed carefully", tone: "go" };
  if (verdict === "REVISE_AND_REASSESS") return { label: locale === "ar" ? "عدّل وأعد التقييم" : "Revise and reassess", tone: "warn" };
  if (verdict === "BLOCKED_NOT_READY") return { label: locale === "ar" ? "لا تبدأ بعد" : "Do not start yet", tone: "stop" };
  return { label: locale === "ar" ? "لم يُقيَّم بعد" : "Not evaluated yet", tone: "warn" };
}

/* ------------------------------------------------------------------ */
/* Sub-components                                                       */
/* ------------------------------------------------------------------ */

function Dial({ percent, label, caption }: { percent: number; label: string; caption: string }) {
  const r = 40;
  const c = 2 * Math.PI * r;
  const off = c - (Math.min(100, Math.max(0, percent)) / 100) * c;
  return (
    <div className="cc-dial">
      <svg width="120" height="120" viewBox="0 0 120 120" aria-hidden="true">
        <circle cx="60" cy="60" r={r} fill="none" stroke="rgba(11,59,45,0.12)" strokeWidth="9" />
        <circle
          cx="60" cy="60" r={r} fill="none" stroke="#1f9d6c" strokeWidth="9" strokeLinecap="round"
          strokeDasharray={c} strokeDashoffset={off} transform="rotate(-90 60 60)"
          style={{ transition: "stroke-dashoffset 0.7s cubic-bezier(0.22,1,0.36,1)" }}
        />
        <text x="60" y="57" textAnchor="middle" fontSize="22" fontWeight="700" fill="#0b3b2d">{percent}%</text>
        <text x="60" y="76" textAnchor="middle" fontSize="9" fill="#8aa095">{label}</text>
      </svg>
      <div className="cc-dial__cap">{caption}</div>
    </div>
  );
}

function Chip({ tone, children }: { tone: "go" | "warn" | "stop" | "dim"; children: React.ReactNode }) {
  return <span className={`cc-chip cc-chip--${tone}`}>{children}</span>;
}

function Soon({ title, icon, note }: { title: string; icon: React.ReactNode; note: string }) {
  const { text } = useCustomerLanguage();
  return (
    <div className="cc-soon">
      <div className="cc-soon__icon">{icon}</div>
      <div className="cc-soon__body">
        <strong>{title}</strong>
        <span>{note}</span>
      </div>
      <Chip tone="dim">{text("قيد التفعيل", "Pending activation")}</Chip>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Main component                                                       */
/* ------------------------------------------------------------------ */

export function CommandCenter({ onOpenProject, onNewProject, onOpenStage }: CommandCenterProps) {
  const { locale, text } = useCustomerLanguage();
  const [section, setSection] = useState<CCSection>("dashboard");
  const [bundles, setBundles] = useState<Bundle[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  const load = useCallback(async () => {
    setLoadError(null);
    try {
      const projects = await fetchProjects();
      const limited = projects.slice(0, 6);
      const next = await Promise.all(
        limited.map(async (project) => {
          const [runs, readiness] = await Promise.all([
            fetchProjectRuns(project.project_id).catch(() => []),
            fetchProjectReadiness(project.project_id).catch(() => null),
          ]);
          const latest = runs[0];
          let overview: ProjectOverview | null = null;
          if (latest?.snapshot_id) {
            overview = await fetchRunOverview(latest.run_id).catch(() => null);
          }
          return { project, overview, readiness } satisfies Bundle;
        })
      );
      setBundles(next);
    } catch (err) {
      setBundles(null);
      setLoadError(customerErrorText(err, locale));
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load, reloadKey]);

  const primary = useMemo(() => (bundles && bundles.length ? bundles[0] : null), [bundles]);
  const readinessPercent = useMemo(() => {
    if (!primary?.readiness) return 0;
    const steps = primary.readiness.steps ?? [];
    if (!steps.length) return primary.readiness.ready_to_run ? 100 : 0;
    const done = steps.filter((s) => s.status === "ready").length;
    return Math.round((done / steps.length) * 100);
  }, [primary]);

  /* ---------------- Loading / error / empty states ---------------- */

  if (loadError) {
    return (
      <div className="cc">
        <div className="cc-error" role="alert">
          <AlertTriangle size={26} aria-hidden="true" />
          <div><strong>{text("تعذر تحميل لوحة القيادة", "Unable to load dashboard")}</strong><p>{loadError}</p></div>
          <button className="cc-btn cc-btn--ghost" onClick={() => setReloadKey((k) => k + 1)}>
            <RefreshCw size={15} aria-hidden="true" /> {text("إعادة المحاولة", "Try again")}
          </button>
        </div>
      </div>
    );
  }

  if (bundles === null) {
    return (
      <div className="cc" aria-busy="true">
        <div className="cc-skel"><span /><span /><span /></div>
      </div>
    );
  }

  if (bundles.length === 0) {
    return (
      <div className="cc">
        <TopNav section={section} onNavigate={setSection} />
        <div className="cc-empty">
          <p className="cc-crumb">ASIE / <b>{text("لوحة القيادة", "Dashboard")}</b></p>
          <h1>{timeGreeting(locale)} — {text("ابدأ أول مشروع لك", "start your first project")}</h1>
          <p className="cc-sub">{text("من فكرة إلى قرار موثق خلال جلسة واحدة. عرّف مشروعك، اربط الأدلة، افحص الجاهزية، واستلم القرار.", "Move from an idea to a documented decision in one guided session: set up the project, link evidence, check readiness, and review the decision.")}</p>
          <button className="cc-btn cc-btn--main cc-btn--lg" onClick={onNewProject}>
            <Plus size={19} aria-hidden="true" /> {text("ابدأ مشروعك الأول", "Start your first project")}
          </button>
        </div>
      </div>
    );
  }

  const ov = primary?.overview ?? null;
  const verdict = verdictMeta(ov?.decision?.sovereign_verdict, locale);
  const confidence = ov ? ov.monte_carlo.p_pass : null;
  const kpis = ov?.kpis ?? [];

  /* ---------------- Render ---------------- */

  return (
    <div className="cc">
      <TopNav section={section} onNavigate={setSection} />

      {/* ============ DASHBOARD (default landing) ============ */}
      {section === "dashboard" ? (
        <>
          <header className="cc-hero">
            <Dial percent={readinessPercent} label={text("جاهزية مشروعك", "Project readiness")} caption={text("نحو قرار واثق", "Toward a confident decision")} />
            <div className="cc-hero__text">
              <p className="cc-crumb">ASIE / <b>{text("لوحة القيادة", "Dashboard")}</b></p>
              <h1>
                {timeGreeting(locale)} —<br />
                {text("مشاريعك بخير، وواحد منها", "Your projects are on track, and one")} <em>{text("ينتظر قرارك", "needs your decision")}</em>
              </h1>
              <p className="cc-sub">
                {text("هذه غرفة القيادة: تعرض وضع المشاريع وما يحتاج انتباهك، بينما تبقى التفاصيل والأدلة في صفحاتها.", "This dashboard shows project status and what needs your attention; details and evidence remain in their dedicated pages.")}
              </p>
            </div>
          </header>

          {/* KPI strip */}
          <div className="cc-kpi-strip">
            <article className="cc-kpi">
              <strong>{verdict.label}</strong>
              <span>{text("آخر قرار محفوظ", "Latest saved decision")}</span>
              <button className="cc-link" onClick={() => setSection("decision")}>{text("افتح تفسير القرار", "Open decision explanation")} ←</button>
            </article>
            <article className="cc-kpi">
              <strong>{fmtPct(confidence, locale)}</strong>
              <span>{text("احتمال اجتياز اختبار السيناريوهات", "Scenario test pass probability")}</span>
              <button className="cc-link" onClick={() => setSection("reality")}>{text("استعرض السيناريوهات", "Review scenarios")} ←</button>
            </article>
            <article className="cc-kpi">
              <strong>{bundles.filter((b) => !b.readiness?.ready_to_run).length}</strong>
              <span>{text("عائق نشط يحتاج انتباهك", "Active blocker needs your attention")}</span>
              <button className="cc-link" onClick={() => primary && onOpenStage(primary.project.project_id, "readiness")}>{text("افتح العائق", "Open blocker")} ←</button>
            </article>
          </div>

          <div className="cc-grid-2">
            {/* مشاريعي */}
            <article className="cc-card">
              <h3><Layers3 size={18} aria-hidden="true" /> {text("مشاريعي", "My projects")}</h3>
              <p className="cc-why">{text("افتح مشروعًا لمتابعة مساره، أو ابدأ مشروعًا جديدًا.", "Open a project to continue its journey, or start a new one.")}</p>
              {bundles.map((b) => {
                const steps = b.readiness?.steps ?? [];
                const done = steps.filter((s) => s.status === "ready").length;
                const total = steps.length || 9;
                const v = verdictMeta(b.overview?.decision?.sovereign_verdict, locale);
                const state = b.overview ? v.label : b.readiness?.ready_to_run ? text("جاهز للتشغيل", "Ready to run") : text("مسودة", "Draft");
                const tone = b.overview ? v.tone : b.readiness?.ready_to_run ? "go" : "dim";
                return (
                  <div className="cc-row" key={b.project.project_id}>
                    <Chip tone={tone}>{state}</Chip>
                    <div className="cc-row__body">
                      <b>{b.project.name}</b>
                      <span>{text("الخطوة", "Step")} {done} {text("من", "of")} {total} · {text("آخر تحديث", "Last updated")}: {formatRelative(b.project.updated_at, locale)}</span>
                    </div>
                    <button className="cc-btn cc-btn--ghost cc-btn--sm" onClick={() => onOpenProject(b.project.project_id)}>
                      {b.overview ? text("فتح", "Open") : text("إكمال", "Continue")} <ArrowLeft size={13} aria-hidden="true" />
                    </button>
                  </div>
                );
              })}
              <button className="cc-btn cc-btn--main" onClick={onNewProject}>
                <Plus size={16} aria-hidden="true" /> {text("ابدأ مشروعًا جديدًا", "Start a new project")}
              </button>
            </article>

            {/* ينتبه له اليوم */}
            <article className="cc-card">
              <h3><AlertTriangle size={18} aria-hidden="true" /> {text("ما يحتاج انتباهك اليوم", "Needs attention today")}</h3>
              <p className="cc-why">{text("تنبيهات سياقية لا تغيّر القرار، بل توضح ما يحتاج إجراءً.", "Context alerts do not change the decision; they highlight what needs action.")}</p>
              <AttentionList bundles={bundles} onOpenStage={onOpenStage} />
              <div className="cc-datafoot">
                <span>{text("البيانات من مشروعك المحفوظ", "Data comes from your saved project")}</span>
                <span>{text("الحالة محدثة من فحص الجاهزية", "Status is updated from the readiness check")}</span>
              </div>
            </article>
          </div>

          {/* principles */}
          <div className="cc-principles">
            {[
              [ShieldCheck, text("لا أرقام بلا مصدر", "No figures without a source"), text("كل قيمة مرتبطة بنتيجة محفوظة أو مدخل موثق.", "Every value is linked to a saved result or documented input.")],
              [Database, text("بياناتك محلية", "Your data stays local"), text("لا يوجد جلب خارجي في الوضع الحالي.", "External retrieval is disabled in the current mode.")],
              [FileText, text("قرار قابل للمراجعة", "Reviewable decision"), text("كل قرار يعود إلى نتيجة محفوظة ثابتة.", "Every decision links back to a fixed saved result.")],
              [BadgeCheck, text("المراجعة لك", "You control the review"), text("المنصة تشرح وتقترح، والقرار لك دائمًا.", "The platform explains and suggests; the decision remains yours.")],
            ].map(([Icon, t, b]) => {
              const I = Icon as typeof ShieldCheck;
              return (
                <article key={t as string}>
                  <I size={17} aria-hidden="true" />
                  <div><strong>{t as string}</strong><span>{b as string}</span></div>
                </article>
              );
            })}
          </div>
        </>
      ) : null}

      {/* ============ TODAY'S DECISION ============ */}
      {section === "today" ? (
        <DecisionToday overview={ov} verdict={verdict} onOpenStage={onOpenStage} projectId={primary!.project.project_id} />
      ) : null}

      {/* ============ GUIDE (مرشد تأسيس المشروع) ============ */}
      {section === "guide" ? <GuideSection overview={ov} /> : null}

      {/* ============ REALITY (اختبار الواقع) ============ */}
      {section === "reality" ? <RealitySection overview={ov} /> : null}

      {/* ============ MARKET ============ */}
      {section === "market" ? (
        <SectionShell title={text("السوق والاتجاهات", "Market and trends")} crumb={text("السوق والاتجاهات", "Market and trends")}>
          <Soon title={text("حجم السوق ومعدل النمو", "Market size and growth")} icon={<Globe size={20} />} note={text("يتطلب ربط مصدر سوق سعودي معتمد.", "Requires an approved Saudi market source.")} />
          <Soon title={text("الطلب والعرض والفجوة السوقية", "Demand, supply, and market gap")} icon={<BarChart3 size={20} />} note={text("يُفعّل بعد ربط مؤشرات طلب قطاعية معتمدة.", "Enabled after approved sector demand indicators are connected.")} />
          <Soon title={text("اتجاهات البحث وسلوك العملاء", "Search trends and customer behavior")} icon={<TrendingUp size={20} />} note={text("يتطلب مصدر اتجاهات خارجيًا معتمدًا.", "Requires an approved external trends source.")} />
        </SectionShell>
      ) : null}

      {/* ============ NEWS ============ */}
      {section === "news" ? (
        <SectionShell title={text("الأخبار الذكية", "Relevant news")} crumb={text("الأخبار الذكية", "Relevant news")}>
          <Soon title={text("أخبار مرتبطة بقطاع مشروعك", "News relevant to your project sector")} icon={<Newspaper size={20} />} note={text("تُفعّل بعد ربط مصدر أخبار معتمد وتقييم أثر كل خبر.", "Enabled after an approved news source and impact review are connected.")} />
        </SectionShell>
      ) : null}

      {/* ============ STRATEGY ============ */}
      {section === "strategy" ? <StrategySection overview={ov} /> : null}

      {/* ============ OPPORTUNITIES ============ */}
      {section === "opportunities" ? <OpportunitiesSection overview={ov} /> : null}

      {/* ============ DECISION (فهم القرار) ============ */}
      {section === "decision" ? <DecisionSection overview={ov} /> : null}

      {/* ============ REPORTS ============ */}
      {section === "reports" ? (
        <ReportsSection bundles={bundles} onOpenStage={onOpenStage} />
      ) : null}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Top navigation                                                       */
/* ------------------------------------------------------------------ */

const NAV: Array<{ id: CCSection; ar: string; en: string }> = [
  { id: "dashboard", ar: "لوحة القيادة", en: "Dashboard" },
  { id: "today", ar: "قراري اليوم", en: "Today's decision" },
  { id: "guide", ar: "مرشد التأسيس", en: "Setup guide" },
  { id: "reality", ar: "اختبار الواقع", en: "Reality test" },
  { id: "market", ar: "السوق والاتجاهات", en: "Market and trends" },
  { id: "decision", ar: "فهم القرار", en: "Understand decision" },
  { id: "reports", ar: "تقاريري", en: "Reports" },
];

function TopNav({ section, onNavigate }: { section: CCSection; onNavigate: (s: CCSection) => void }) {
  const { locale, text } = useCustomerLanguage();
  return (
    <nav className="cc-topnav" aria-label={text("أقسام لوحة القيادة", "Dashboard sections")}>
      <div className="cc-topnav__brand">
        <strong>ASIE</strong>
        <span>{text("المستشار الاستراتيجي التفاعلي", "Interactive strategy advisor")}</span>
      </div>
      <div className="cc-topnav__links">
        {NAV.map((item) => (
          <button
            key={item.id}
            className={section === item.id ? "cc-navlink cc-navlink--active" : "cc-navlink"}
            onClick={() => onNavigate(item.id)}
            aria-current={section === item.id ? "page" : undefined}
          >
            {locale === "ar" ? item.ar : item.en}
          </button>
        ))}
      </div>
      <div className="cc-topnav__mode">
        <span className="cc-dot" /> {text("تشغيل محلي", "Local operation")}
      </div>
    </nav>
  );
}

/* ------------------------------------------------------------------ */
/* Section shells                                                       */
/* ------------------------------------------------------------------ */

function SectionShell({ title, crumb, children }: { title: string; crumb: string; children: React.ReactNode }) {
  const { text } = useCustomerLanguage();
  return (
    <div className="cc-section">
      <p className="cc-crumb">ASIE / {text("لوحة القيادة", "Dashboard")} / <b>{crumb}</b></p>
      <h2 className="cc-section__title">{title}</h2>
      <div className="cc-stack">{children}</div>
    </div>
  );
}

function NeedData({ text }: { text: string }) {
  return (
    <div className="cc-needdata">
      <Database size={18} aria-hidden="true" />
      <span>{text}</span>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* قراري اليوم                                                          */
/* ------------------------------------------------------------------ */

function DecisionToday({
  overview, verdict, onOpenStage, projectId,
}: { overview: ProjectOverview | null; verdict: ReturnType<typeof verdictMeta>; onOpenStage: CommandCenterProps["onOpenStage"]; projectId: string }) {
  const { locale, text } = useCustomerLanguage();
  if (!overview) {
    return (
      <SectionShell title={text("قراري اليوم", "Decision today")} crumb={text("قراري اليوم", "Decision today")}>
        <NeedData text={text("لا يوجد قرار محفوظ بعد. شغّل التحليل لإنشاء أول نتيجة.", "No saved decision yet. Run the analysis to create the first result.")} />
        <button className="cc-btn cc-btn--main" onClick={() => onOpenStage(projectId, "run")}>{text("شغّل التحليل", "Run analysis")}</button>
      </SectionShell>
    );
  }
  const conf = overview.monte_carlo.p_pass;
  const risks = overview.risk_register.top_risks.slice(0, 5);
  const personas = overview.personas;
  return (
    <SectionShell title={text("قراري اليوم", "Decision today")} crumb={text("قراري اليوم", "Decision today")}>
      <div className="cc-decision-hero">
        <div className={`cc-verdict cc-verdict--${verdict.tone}`}>
          <span>{text("القرار", "Decision")}</span>
          <strong>{verdict.label}</strong>
          <small>{text("آخر تحديث", "Last updated")} · {formatRelative(overview.snapshot.created_at, locale)}</small>
        </div>
        <div className="cc-decision-metrics">
          <article><span>{text("درجة الثقة", "Confidence")}</span><strong>{fmtPct(conf, locale)}</strong></article>
          <article><span>{text("الربح المتوقع في السيناريو الوسيط", "Expected profit in the midpoint scenario")}</span><strong>{fmtSAR(overview.monte_carlo.p50_profit, locale)}</strong></article>
          <article><span>{text("حالة قياس المخاطر", "Risk measurement status")}</span><strong>{overview.monte_carlo.status === "ready" ? text("محسوبة", "Calculated") : "—"}</strong></article>
        </div>
      </div>

      <div className="cc-grid-2">
        <article className="cc-card">
          <h3><AlertTriangle size={17} aria-hidden="true" /> {text("أهم المخاطر", "Top risks")}</h3>
          {risks.length ? risks.map((r) => (
            <div className="cc-row" key={r.risk_id}>
              <Chip tone={r.severity === "high" || r.severity === "critical" ? "stop" : "warn"}>{customerBusinessText(r.severity, locale)}</Chip>
              <div className="cc-row__body"><b>{customerBusinessText(r.trigger, locale)}</b><span>{customerNarrativeText(r.mitigation, locale)}</span></div>
            </div>
          )) : <NeedData text={text("لا توجد مخاطر مسجلة في النتيجة الحالية.", "No risks are recorded in the current result.")} />}
        </article>
        <article className="cc-card">
          <h3><Sparkles size={17} aria-hidden="true" /> {text("زوايا التقييم الخمس", "Five assessment perspectives")}</h3>
          {personas.map((p) => (
            <div className="cc-row" key={p.persona_id}>
              <div className="cc-row__body"><b>{customerBusinessText(p.metric, locale)}</b><span>{customerNarrativeText(p.note, locale)}</span></div>
              <strong className="cc-row__val">{p.value === null ? "—" : fmtPct(p.value, locale)}</strong>
            </div>
          ))}
        </article>
      </div>
      <p className="cc-reason">{customerNarrativeText(overview.decision.reason, locale)}</p>
    </SectionShell>
  );
}

/* ------------------------------------------------------------------ */
/* مرشد تأسيس المشروع                                                   */
/* ------------------------------------------------------------------ */

function GuideSection({ overview }: { overview: ProjectOverview | null }) {
  const { locale, text } = useCustomerLanguage();
  const milestones = overview?.execution_plan.milestones ?? [];
  return (
    <SectionShell title={text("مرشد تأسيس المشروع", "Project setup guide")} crumb={text("مرشد التأسيس", "Setup guide")}>
      <article className="cc-card">
        <h3><CheckCircle2 size={17} aria-hidden="true" /> {text("خطة التنفيذ", "Execution plan")}</h3>
        <p className="cc-why">{text("من نتيجتك المحفوظة: مراحل ومعايير إكمال واضحة.", "From your saved result: clear phases and completion criteria.")}</p>
        {milestones.length ? milestones.map((m) => (
          <div className="cc-row" key={m.phase_id}>
            <Chip tone="go">{m.estimated_duration_days} {text("يوم", "days")}</Chip>
            <div className="cc-row__body"><b>{customerBusinessText(m.phase_id, locale)}</b><span>{customerNarrativeText(m.exit_criteria[0] ?? m.owner_role, locale)}</span></div>
          </div>
        )) : <NeedData text={text("تظهر خطة التنفيذ بعد تشغيل التحليل.", "The execution plan appears after the analysis runs.")} />}
      </article>

      <div className="cc-grid-2">
        <Soon title={text("اختيار الموقع", "Location selection")} icon={<MapPin size={20} />} note={text("مقارنة المدن والأحياء والإيجار والكثافة تتطلب بيانات جغرافية سعودية معتمدة.", "Comparing cities, districts, rent, and density requires approved Saudi geographic data.")} />
        <Soon title={text("خريطة المنافسين", "Competitor map")} icon={<Target size={20} />} note={text("عرض المنافسين والمسافات يتطلب مصدر أماكن وخرائط معتمدًا.", "Showing competitors and distances requires an approved places and maps source.")} />
        <Soon title={text("المشاريع المشابهة", "Comparable projects")} icon={<Layers3 size={20} />} note={text("قصص النجاح والتعثر تتطلب قاعدة دراسات حالة معتمدة.", "Success and setback cases require an approved case-study source.")} />
        <Soon title={text("الموظفون والرواتب", "Staff and salaries")} icon={<BadgeCheck size={20} />} note={text("الهيكل ومتوسط الرواتب يتطلبان بيانات أجور قطاعية معتمدة.", "Structure and salary averages require approved sector wage data.")} />
        <Soon title={text("المعدات والموردون", "Equipment and suppliers")} icon={<Database size={20} />} note={text("الأسعار والموردون يتطلبون بيانات موردين معتمدة.", "Prices and suppliers require an approved supplier source.")} />
        <Soon title={text("التراخيص", "Licenses")} icon={<FileText size={20} />} note={text("الجهات والرسوم والروابط تتطلب دليل التراخيص الرسمي.", "Authorities, fees, and links require an official licensing guide.")} />
      </div>
    </SectionShell>
  );
}

/* ------------------------------------------------------------------ */
/* اختبار الواقع                                                        */
/* ------------------------------------------------------------------ */

function RealitySection({ overview }: { overview: ProjectOverview | null }) {
  const { locale, text } = useCustomerLanguage();
  if (!overview) {
    return (
      <SectionShell title={text("اختبار الواقع", "Reality test")} crumb={text("اختبار الواقع", "Reality test")}>
        <NeedData text={text("شغّل التحليل أولًا لتظهر محاكاة السيناريوهات.", "Run the analysis first to view scenario simulation.")} />
      </SectionShell>
    );
  }
  const mc = overview.monte_carlo;
  const p10 = mc.p10_profit ?? 0;
  const p50 = mc.p50_profit ?? 0;
  const p90 = mc.p90_profit ?? 0;
  const max = Math.max(Math.abs(p10), Math.abs(p50), Math.abs(p90), 1);
  return (
    <SectionShell title={text("اختبار الواقع", "Reality test")} crumb={text("اختبار الواقع", "Reality test")}>
      <article className="cc-card">
        <h3><BarChart3 size={17} aria-hidden="true" /> {text("محاكاة السيناريوهات", "Scenario simulation")}</h3>
        <p className="cc-why">{mc.iterations.toLocaleString(locale === "ar" ? "ar-SA" : "en-US")} {text("سيناريو محفوظ يوضح توزيع الربح الشهري تحت الضغط.", "saved scenarios show the monthly profit distribution under stress.")}</p>
        <div className="cc-bars">
          {([[text("سيناريو حذر", "Cautious scenario"), p10, "#c0392b"], [text("سيناريو وسيط", "Midpoint scenario"), p50, "#1f9d6c"], [text("سيناريو متفائل", "Optimistic scenario"), p90, "#0b3b2d"]] as const).map(([label, v, color]) => (
            <div className="cc-bar" key={label}>
              <span>{label}</span>
              <div className="cc-bar__track"><i style={{ width: `${Math.max(4, (Math.abs(v) / max) * 100)}%`, background: color }} /></div>
              <strong>{fmtSAR(v, locale)}</strong>
            </div>
          ))}
        </div>
        <div className="cc-gate">
          <span>{text("احتمال استيفاء متطلبات الجدوى", "Probability of meeting feasibility requirements")}</span>
          <strong>{fmtPct(mc.p_pass, locale)}</strong>
        </div>
      </article>
      <div className="cc-grid-2">
        <Soon title={text("سيناريوهات ضغط إضافية", "Additional stress scenarios")} icon={<TrendingUp size={20} />} note={text("اختبار انخفاض المبيعات وارتفاع التكاليف ما زال قيد التفعيل.", "Sales decline and cost increase tests are pending activation.")} />
        <Soon title={text("تحليل الحساسية", "Sensitivity analysis")} icon={<BarChart3 size={20} />} note={text("يوضح أثر كل افتراض على الربح ونقطة التعادل بعد تفعيله.", "Shows how each assumption affects profit and break-even after activation.")} />
      </div>
    </SectionShell>
  );
}

/* ------------------------------------------------------------------ */
/* التوافق الاستراتيجي                                                  */
/* ------------------------------------------------------------------ */

function StrategySection({ overview }: { overview: ProjectOverview | null }) {
  const { locale, text } = useCustomerLanguage();
  const sector = overview?.sector_intelligence;
  return (
    <SectionShell title={text("التوافق الاستراتيجي", "Strategic alignment")} crumb={text("التوافق الاستراتيجي", "Strategic alignment")}>
      {sector ? (
        <article className="cc-card">
          <h3><Target size={17} aria-hidden="true" /> {text("موقع المشروع في قطاعه", "Project position in its sector")}</h3>
          <p className="cc-why">{text("مستخلص من تحليل القطاع في نتيجتك المحفوظة.", "Derived from the sector analysis in your saved result.")}</p>
          <div className="cc-row"><div className="cc-row__body"><b>{text("القطاع", "Sector")}</b><span>{customerBusinessText(overview!.project.sector, locale)}</span></div></div>
        </article>
      ) : <NeedData text={text("شغّل التحليل لعرض التوافق القطاعي.", "Run the analysis to view sector alignment.")} />}
      <div className="cc-grid-2">
        <Soon title={text("التوافق مع رؤية 2030", "Vision 2030 alignment")} icon={<Target size={20} />} note={text("يتطلب ربط المستهدفات الرسمية المعتمدة.", "Requires approved official targets.")} />
        <Soon title={text("برامج الدعم والمبادرات", "Support programs and initiatives")} icon={<BadgeCheck size={20} />} note={text("تتطلب دليل البرامج الرسمي المعتمد.", "Requires an approved official programs guide.")} />
      </div>
    </SectionShell>
  );
}

/* ------------------------------------------------------------------ */
/* الفرص الذكية                                                         */
/* ------------------------------------------------------------------ */

function OpportunitiesSection({ overview }: { overview: ProjectOverview | null }) {
  const { locale, text } = useCustomerLanguage();
  return (
    <SectionShell title={text("الفرص", "Opportunities")} crumb={text("الفرص", "Opportunities")}>
      {overview ? (
        <article className="cc-card">
          <h3><Lightbulb size={17} aria-hidden="true" /> {text("من قراءة النتيجة المحفوظة", "From the saved result")}</h3>
          <p className="cc-why">{text("مؤشرات مستمدة من بياناتك المحفوظة وليست توصية نهائية.", "Indicators derived from your saved data; they are not a final recommendation.")}</p>
          <div className="cc-row"><div className="cc-row__body"><b>{text("احتمال الاستيفاء", "Pass probability")} {fmtPct(overview.monte_carlo.p_pass, locale)}</b><span>{text("كلما ارتفع، اتسع هامش التعامل مع الفرص.", "A higher value provides more room to pursue opportunities.")}</span></div></div>
        </article>
      ) : <NeedData text={text("شغّل التحليل لتظهر مؤشرات الفرص.", "Run the analysis to view opportunity indicators.")} />}
      <div className="cc-grid-2">
        <Soon title={text("اقتراح موقع أفضل", "Suggest a better location")} icon={<MapPin size={20} />} note={text("يتطلب بيانات جغرافية وسوقية معتمدة.", "Requires approved geographic and market data.")} />
        <Soon title={text("فرص منتج أو خدمة إضافية", "Additional product or service opportunities")} icon={<Lightbulb size={20} />} note={text("يتطلب بيانات قطاعية معتمدة قبل التفعيل.", "Requires approved sector data before activation.")} />
      </div>
    </SectionShell>
  );
}

/* ------------------------------------------------------------------ */
/* فهم القرار                                                           */
/* ------------------------------------------------------------------ */

function DecisionSection({ overview }: { overview: ProjectOverview | null }) {
  const { locale, text } = useCustomerLanguage();
  if (!overview) {
    return (
      <SectionShell title={text("فهم القرار", "Understand the decision")} crumb={text("فهم القرار", "Understand the decision")}>
        <NeedData text={text("لا يوجد قرار محفوظ لتفسيره بعد.", "There is no saved decision to explain yet.")} />
      </SectionShell>
    );
  }
  return (
    <SectionShell title={text("فهم القرار", "Understand the decision")} crumb={text("فهم القرار", "Understand the decision")}>
      <article className="cc-card">
        <h3><FileText size={17} aria-hidden="true" /> {text("لماذا هذا القرار؟", "Why this decision?")}</h3>
        <p className="cc-reason">{customerNarrativeText(overview.decision.reason, locale)}</p>
        <div className="cc-row"><Chip tone="dim">{text("القرار", "Decision")}</Chip><div className="cc-row__body"><b>{verdictMeta(overview.decision.sovereign_verdict, locale).label}</b><span>{text("قرار محفوظ وقابل للمراجعة", "Saved and reviewable decision")}</span></div></div>
      </article>
      <article className="cc-card">
        <h3><BarChart3 size={17} aria-hidden="true" /> {text("المؤشرات المؤثرة", "Decision drivers")}</h3>
        <div className="cc-kpi-grid">
          {overview.kpis.slice(0, 8).map((k: OutputEnvelope) => (
            <div className="cc-kpi-cell" key={k.output_id}>
              <span>{customerBusinessText(k.output_id, locale)}</span>
              <strong>{typeof k.value === "number" ? (k.unit === "percent" ? fmtPct(k.value, locale) : k.unit === "SAR" ? fmtSAR(k.value, locale) : String(k.value)) : "—"}</strong>
            </div>
          ))}
        </div>
      </article>
      <article className="cc-card">
        <h3><Sparkles size={17} aria-hidden="true" /> {text("زوايا التقييم الخمس", "Five assessment perspectives")}</h3>
        {overview.personas.map((p) => (
          <div className="cc-row" key={p.persona_id}>
            <div className="cc-row__body"><b>{customerBusinessText(p.metric, locale)}</b><span>{customerNarrativeText(p.note, locale)}</span></div>
            <strong className="cc-row__val">{p.value === null ? "—" : fmtPct(p.value, locale)}</strong>
          </div>
        ))}
        <p className="cc-why">{text("زوايا التقييم تشرح النتيجة ولا تغيّر القرار المحفوظ.", "Assessment perspectives explain the result without changing the saved decision.")}</p>
      </article>
    </SectionShell>
  );
}

/* ------------------------------------------------------------------ */
/* تقاريري                                                              */
/* ------------------------------------------------------------------ */

function ReportsSection({ bundles, onOpenStage }: { bundles: Bundle[]; onOpenStage: CommandCenterProps["onOpenStage"] }) {
  const { text } = useCustomerLanguage();
  const withRuns = bundles.filter((b) => b.overview);
  return (
    <SectionShell title={text("تقاريري", "Reports")} crumb={text("تقاريري", "Reports")}>
      <p className="cc-why">{text("مكتبة المشروع: كل تقرير مرتبط بنتيجة محفوظة ويُفتح من صفحة تقارير المشروع.", "Project library: each report is linked to a saved result and opens from the project reports page.")}</p>
      {withRuns.length ? withRuns.map((b) => (
        <div className="cc-row" key={b.project.project_id}>
          <Chip tone="go">{text("محفوظ", "Saved")}</Chip>
          <div className="cc-row__body">
            <b>{b.project.name}</b>
            <span>{text("تقرير تنفيذي · دراسة جدوى · مذكرة قرار · ملفات قابلة للتنزيل", "Executive report · Feasibility study · Decision memo · Downloadable files")}</span>
          </div>
          <button className="cc-btn cc-btn--ghost cc-btn--sm" onClick={() => onOpenStage(b.project.project_id, "snapshots")}>
            {text("فتح التقارير", "Open reports")} <ArrowLeft size={13} aria-hidden="true" />
          </button>
        </div>
      )) : <NeedData text={text("لا توجد نتائج محفوظة بعد. شغّل التحليل في أحد مشاريعك لإنشاء أول تقرير.", "No saved results yet. Run the analysis in a project to create the first report.")} />}
    </SectionShell>
  );
}

/* ------------------------------------------------------------------ */
/* Attention list (derived from real data only)                         */
/* ------------------------------------------------------------------ */

function AttentionList({ bundles, onOpenStage }: { bundles: Bundle[]; onOpenStage: CommandCenterProps["onOpenStage"] }) {
  const { locale, text } = useCustomerLanguage();
  const items: Array<{ id: string; pid: string; title: string; detail: string; tone: "warn" | "stop" | "dim"; stage: "evidence" | "readiness" | "decision" | "run" }> = [];
  for (const b of bundles) {
    for (const blocker of (b.readiness?.blockers ?? []).slice(0, 2)) {
      items.push({
        id: `${b.project.project_id}:${blocker.code}`,
        pid: b.project.project_id,
        title: `${b.project.name} — ${text("يحتاج استكمال الجاهزية", "readiness needs completion")}`,
        detail: customerNarrativeText(blocker.message, locale),
        tone: "warn",
        stage: "readiness",
      });
    }
    const sourceStep = b.readiness?.steps.find((step) => step.step_id === "sources" && step.status !== "ready");
    if (sourceStep) {
      items.push({
        id: `${b.project.project_id}:evidence`,
        pid: b.project.project_id,
        title: `${b.project.name} — ${text("الأدلة غير مكتملة", "evidence is incomplete")}`,
        detail: customerNarrativeText(sourceStep.message || text("اربط دليلًا قبل التشغيل.", "Link evidence before running the analysis."), locale),
        tone: "dim",
        stage: "evidence",
      });
    }
    if (b.overview?.decision.sovereign_verdict === "REVISE_AND_REASSESS") {
      items.push({
        id: `${b.project.project_id}:decision`,
        pid: b.project.project_id,
        title: `${b.project.name} — ${text("القرار يحتاج مراجعة", "decision needs review")}`,
        detail: text("القرار الأخير يطلب المراجعة وإعادة التقييم.", "The latest decision requires review and reassessment."),
        tone: "stop",
        stage: "decision",
      });
    }
  }
  const shown = items.slice(0, 4);
  if (!shown.length) {
    return (
      <div className="cc-clear">
        <CheckCircle2 size={19} aria-hidden="true" />
        <span>{text("لا شيء يحتاج انتباهك الآن، ومشاريعك على المسار.", "Nothing needs your attention now; your projects are on track.")}</span>
      </div>
    );
  }
  return (
    <>
      {shown.map((item) => (
        <div className="cc-row" key={item.id}>
          <Chip tone={item.tone}>
            {item.stage === "readiness" ? text("جاهزية", "Readiness") : item.stage === "evidence" ? text("أدلة", "Evidence") : text("قرار", "Decision")}
          </Chip>
          <div className="cc-row__body"><b>{item.title}</b><span>{item.detail}</span></div>
          <button className="cc-btn cc-btn--ghost cc-btn--sm" onClick={() => onOpenStage(item.pid, item.stage)}>
            {text("معالجة", "Resolve")} <ArrowLeft size={13} aria-hidden="true" />
          </button>
        </div>
      ))}
    </>
  );
}
