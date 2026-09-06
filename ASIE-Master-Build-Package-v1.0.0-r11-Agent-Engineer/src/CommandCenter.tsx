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
          <div><strong>تعذر تحميل لوحة القيادة</strong><p>{loadError}</p></div>
          <button className="cc-btn cc-btn--ghost" onClick={() => setReloadKey((k) => k + 1)}>
            <RefreshCw size={15} aria-hidden="true" /> إعادة المحاولة
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
          <p className="cc-crumb">ASIE / <b>لوحة القيادة</b></p>
          <h1>{timeGreeting()} — ابدأ أول مشروع لك</h1>
          <p className="cc-sub">من فكرة إلى قرار موثق خلال جلسة واحدة. عرّف مشروعك، اربط الأدلة، افحص الجاهزية، واستلم القرار.</p>
          <button className="cc-btn cc-btn--main cc-btn--lg" onClick={onNewProject}>
            <Plus size={19} aria-hidden="true" /> ابدأ مشروعك الأول
          </button>
        </div>
      </div>
    );
  }

  const ov = primary?.overview ?? null;
  const verdict = verdictMeta(ov?.decision?.sovereign_verdict);
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
            <Dial percent={readinessPercent} label="جاهزية مشروعك" caption="نحو قرار واثق" />
            <div className="cc-hero__text">
              <p className="cc-crumb">ASIE / <b>لوحة القيادة</b></p>
              <h1>
                {timeGreeting()} —<br />
                مشاريعك بخير، وواحد منها <em>ينتظر قرارك</em>
              </h1>
              <p className="cc-sub">
                هذه غرفة القيادة فقط: وضع المشاريع وما يحتاج انتباهاً. التفاصيل والأدلة تعيش في غرفها الخاصة.
              </p>
            </div>
          </header>

          {/* KPI strip */}
          <div className="cc-kpi-strip">
            <article className="cc-kpi">
              <strong>{verdict.label}</strong>
              <span>{text("آخر قرار محفوظ", "Latest saved decision")}</span>
              <button className="cc-link" onClick={() => setSection("decision")}>افتح تفسير القرار ←</button>
            </article>
            <article className="cc-kpi">
              <strong>{fmtPct(confidence)}</strong>
              <span>{text("احتمال اجتياز اختبار السيناريوهات", "Scenario test pass probability")}</span>
              <button className="cc-link" onClick={() => setSection("reality")}>حفر في السيناريوهات ←</button>
            </article>
            <article className="cc-kpi">
              <strong>{bundles.filter((b) => !b.readiness?.ready_to_run).length}</strong>
              <span>عائق تنفيذ نشط يحتاج انتباهاً</span>
              <button className="cc-link" onClick={() => primary && onOpenStage(primary.project.project_id, "readiness")}>افتح العائق ←</button>
            </article>
          </div>

          <div className="cc-grid-2">
            {/* مشاريعي */}
            <article className="cc-card">
              <h3><Layers3 size={18} aria-hidden="true" /> مشاريعي</h3>
              <p className="cc-why">افتح مشروعاً لمتابعة مساره، أو ابدأ مشروعاً جديداً.</p>
              {bundles.map((b) => {
                const steps = b.readiness?.steps ?? [];
                const done = steps.filter((s) => s.status === "ready").length;
                const total = steps.length || 9;
                const v = verdictMeta(b.overview?.decision?.sovereign_verdict);
                const state = b.overview ? v.label : b.readiness?.ready_to_run ? "جاهز للتشغيل" : "مسودة";
                const tone = b.overview ? v.tone : b.readiness?.ready_to_run ? "go" : "dim";
                return (
                  <div className="cc-row" key={b.project.project_id}>
                    <Chip tone={tone}>{state}</Chip>
                    <div className="cc-row__body">
                      <b>{b.project.name}</b>
                      <span>الخطوة {done} من {total} · آخر تحديث: {formatRelative(b.project.updated_at)}</span>
                    </div>
                    <button className="cc-btn cc-btn--ghost cc-btn--sm" onClick={() => onOpenProject(b.project.project_id)}>
                      {b.overview ? "فتح" : "إكمال"} <ArrowLeft size={13} aria-hidden="true" />
                    </button>
                  </div>
                );
              })}
              <button className="cc-btn cc-btn--main" onClick={onNewProject}>
                <Plus size={16} aria-hidden="true" /> ابدأ مشروعاً جديداً
              </button>
            </article>

            {/* ينتبه له اليوم */}
            <article className="cc-card">
              <h3><AlertTriangle size={18} aria-hidden="true" /> ينتبه له اليوم</h3>
              <p className="cc-why">تنبيهات السياق — لا تغيّر الحكم، فقط تلفت نظرك.</p>
              <AttentionList bundles={bundles} onOpenStage={onOpenStage} />
              <div className="cc-datafoot">
                <span>data_mode: live_local</span>
                <span>source: لقطات محفوظة + جاهزية حية</span>
                <span>confidence: تتبع السياق</span>
              </div>
            </article>
          </div>

          {/* principles */}
          <div className="cc-principles">
            {[
              [ShieldCheck, "لا أرقام بلا مصدر", "كل قيمة مرتبطة بلقطة محفوظة أو مدخل موثق."],
              [Database, "بياناتك محلية", "لا جلب خارجي ولا مفاتيح داخل الحزمة."],
              [FileText, "قرار قابل للرجوع", "كل حكم يحمل مرجع لقطة ثابت."],
              [BadgeCheck, "المراجعة لك", "المنصة تقترح وتوضح — القرار لك دائماً."],
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
        <SectionShell title="السوق والاتجاهات" crumb="السوق والاتجاهات">
          <Soon title="حجم السوق ومعدل النمو" icon={<Globe size={20} />} note="يتطلب ربط مصدر بيانات سوق سعودي معتمد (GASTAT / تقارير قطاعية)." />
          <Soon title="الطلب والعرض والفجوة السوقية" icon={<BarChart3 size={20} />} note="يُفعَّل بعد ربط مؤشرات الطلب القطاعية." />
          <Soon title="اتجاهات البحث وسلوك العملاء" icon={<TrendingUp size={20} />} note="يتطلب تكامل مصدر اتجاهات خارجي." />
        </SectionShell>
      ) : null}

      {/* ============ NEWS ============ */}
      {section === "news" ? (
        <SectionShell title="الأخبار الذكية" crumb="الأخبار الذكية">
          <Soon title="أخبار مفلترة حسب قطاع مشروعك" icon={<Newspaper size={20} />} note="تُفعَّل بعد ربط مصدر أخبار مع تقييم تأثير كل خبر." />
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
  const { text } = useCustomerLanguage();
  if (!overview) {
    return (
      <SectionShell title="قراري اليوم" crumb="قراري اليوم">
        <NeedData text="لا يوجد قرار محفوظ بعد. شغّل التحليل لإنشاء أول لقطة وحكم سيادي." />
        <button className="cc-btn cc-btn--main" onClick={() => onOpenStage(projectId, "run")}>شغّل التحليل</button>
      </SectionShell>
    );
  }
  const conf = overview.monte_carlo.p_pass;
  const risks = overview.risk_register.top_risks.slice(0, 5);
  const personas = overview.personas;
  return (
    <SectionShell title="قراري اليوم" crumb="قراري اليوم">
      <div className="cc-decision-hero">
        <div className={`cc-verdict cc-verdict--${verdict.tone}`}>
          <span>القرار</span>
          <strong>{verdict.label}</strong>
          <small>{text("آخر تحديث", "Last updated")} · {formatRelative(overview.snapshot.created_at)}</small>
        </div>
        <div className="cc-decision-metrics">
          <article><span>درجة الثقة</span><strong>{fmtPct(conf)}</strong></article>
          <article><span>الربح الوسيط (P50)</span><strong>{fmtSAR(overview.monte_carlo.p50_profit)}</strong></article>
          <article><span>درجة المخاطرة</span><strong>{overview.monte_carlo.status === "ready" ? "محسوبة" : "—"}</strong></article>
        </div>
      </div>

      <div className="cc-grid-2">
        <article className="cc-card">
          <h3><AlertTriangle size={17} aria-hidden="true" /> أهم المخاطر</h3>
          {risks.length ? risks.map((r) => (
            <div className="cc-row" key={r.risk_id}>
              <Chip tone={r.severity === "high" || r.severity === "critical" ? "stop" : "warn"}>{r.severity}</Chip>
              <div className="cc-row__body"><b>{r.trigger}</b><span>{r.mitigation}</span></div>
            </div>
          )) : <NeedData text="لا توجد مخاطر مسجلة في هذه اللقطة." />}
        </article>
        <article className="cc-card">
          <h3><Sparkles size={17} aria-hidden="true" /> زوايا التقييم الخمس</h3>
          {personas.map((p) => (
            <div className="cc-row" key={p.persona_id}>
              <div className="cc-row__body"><b>{p.metric}</b><span>{p.note}</span></div>
              <strong className="cc-row__val">{p.value === null ? "—" : fmtPct(p.value)}</strong>
            </div>
          ))}
        </article>
      </div>
      <p className="cc-reason">{overview.decision.reason}</p>
    </SectionShell>
  );
}

/* ------------------------------------------------------------------ */
/* مرشد تأسيس المشروع                                                   */
/* ------------------------------------------------------------------ */

function GuideSection({ overview }: { overview: ProjectOverview | null }) {
  const milestones = overview?.execution_plan.milestones ?? [];
  return (
    <SectionShell title="مرشد تأسيس المشروع" crumb="مرشد التأسيس">
      <article className="cc-card">
        <h3><CheckCircle2 size={17} aria-hidden="true" /> خطة التنفيذ</h3>
        <p className="cc-why">من لقطتك المحفوظة — مراحل ومعايير خروج واضحة.</p>
        {milestones.length ? milestones.map((m) => (
          <div className="cc-row" key={m.phase_id}>
            <Chip tone="go">{m.estimated_duration_days} يوم</Chip>
            <div className="cc-row__body"><b>{m.phase_id}</b><span>{m.exit_criteria[0] ?? m.owner_role}</span></div>
          </div>
        )) : <NeedData text="تظهر خطة التنفيذ بعد تشغيل التحليل." />}
      </article>

      <div className="cc-grid-2">
        <Soon title="اختيار الموقع" icon={<MapPin size={20} />} note="أفضل المدن والأحياء، الإيجار، الكثافة — يتطلب بيانات جغرافية سعودية." />
        <Soon title="خارطة المنافسين" icon={<Target size={20} />} note="المنافسون على الخريطة مع تقييماتهم — يتطلب مصدر أماكن/خرائط." />
        <Soon title="المشاريع المشابهة" icon={<Layers3 size={20} />} note="قصص نجاح وتعثر وفشل — يتطلب قاعدة دراسات حالة." />
        <Soon title="الموظفون والرواتب" icon={<BadgeCheck size={20} />} note="الهيكل ومتوسط الرواتب — يتطلب بيانات أجور قطاعية." />
        <Soon title="المعدات والموردون" icon={<Database size={20} />} note="الأسعار والموردون — يتطلب بيانات موردين." />
        <Soon title="التراخيص" icon={<FileText size={20} />} note="الجهات والرسوم والروابط الرسمية — يتطلب دليل التراخيص الرسمي." />
      </div>
    </SectionShell>
  );
}

/* ------------------------------------------------------------------ */
/* اختبار الواقع                                                        */
/* ------------------------------------------------------------------ */

function RealitySection({ overview }: { overview: ProjectOverview | null }) {
  const { text } = useCustomerLanguage();
  if (!overview) {
    return (
      <SectionShell title="اختبار الواقع" crumb="اختبار الواقع">
        <NeedData text="شغّل التحليل أولاً لتظهر محاكاة السيناريوهات." />
      </SectionShell>
    );
  }
  const mc = overview.monte_carlo;
  const p10 = mc.p10_profit ?? 0;
  const p50 = mc.p50_profit ?? 0;
  const p90 = mc.p90_profit ?? 0;
  const max = Math.max(Math.abs(p10), Math.abs(p50), Math.abs(p90), 1);
  return (
    <SectionShell title="اختبار الواقع" crumb="اختبار الواقع">
      <article className="cc-card">
        <h3><BarChart3 size={17} aria-hidden="true" /> {text("محاكاة السيناريوهات", "Scenario simulation")}</h3>
        <p className="cc-why">{mc.iterations.toLocaleString("ar-SA")} تشغيل محفوظ — توزيع الربح الشهري تحت الضغط.</p>
        <div className="cc-bars">
          {([["متشائم P10", p10, "#c0392b"], ["وسيط P50", p50, "#1f9d6c"], ["متفائل P90", p90, "#0b3b2d"]] as const).map(([label, v, color]) => (
            <div className="cc-bar" key={label}>
              <span>{label}</span>
              <div className="cc-bar__track"><i style={{ width: `${Math.max(4, (Math.abs(v) / max) * 100)}%`, background: color }} /></div>
              <strong>{fmtSAR(v)}</strong>
            </div>
          ))}
        </div>
        <div className="cc-gate">
          <span>احتمال اجتياز بوابات الجدوى</span>
          <strong>{fmtPct(mc.p_pass)}</strong>
        </div>
      </article>
      <div className="cc-grid-2">
        <Soon title="سيناريوهات ضغط إضافية" icon={<TrendingUp size={20} />} note="انخفاض مبيعات، ارتفاع رواتب/إيجار، تضخم — تُفعَّل مع محرك السيناريوهات الموسّع." />
        <Soon title="تحليل الحساسية" icon={<BarChart3 size={20} />} note="أثر كل افتراض على الربح ونقطة التعادل — يتطلب مصفوفة الحساسية." />
      </div>
    </SectionShell>
  );
}

/* ------------------------------------------------------------------ */
/* التوافق الاستراتيجي                                                  */
/* ------------------------------------------------------------------ */

function StrategySection({ overview }: { overview: ProjectOverview | null }) {
  const sector = overview?.sector_intelligence;
  return (
    <SectionShell title="التوافق الاستراتيجي" crumb="التوافق الاستراتيجي">
      {sector ? (
        <article className="cc-card">
          <h3><Target size={17} aria-hidden="true" /> موقع المشروع قطاعياً</h3>
          <p className="cc-why">من تحليل القطاع في لقطتك المحفوظة.</p>
          <div className="cc-row"><div className="cc-row__body"><b>القطاع</b><span>{overview!.project.sector}</span></div></div>
        </article>
      ) : <NeedData text="شغّل التحليل لعرض التوافق القطاعي." />}
      <div className="cc-grid-2">
        <Soon title="توافق رؤية 2030" icon={<Target size={20} />} note="درجة توافق مع مستهدفات الرؤية — تتطلب مصفوفة المستهدفات الرسمية." />
        <Soon title="برامج الدعم والمبادرات" icon={<BadgeCheck size={20} />} note="منشآت، بنك التنمية، الصناديق — تتطلب دليل البرامج الرسمي." />
      </div>
    </SectionShell>
  );
}

/* ------------------------------------------------------------------ */
/* الفرص الذكية                                                         */
/* ------------------------------------------------------------------ */

function OpportunitiesSection({ overview }: { overview: ProjectOverview | null }) {
  return (
    <SectionShell title="الفرص الذكية" crumb="الفرص الذكية">
      {overview ? (
        <article className="cc-card">
          <h3><Lightbulb size={17} aria-hidden="true" /> من قراءة لقطتك</h3>
          <p className="cc-why">مؤشرات مستمدة من بياناتك المحفوظة — ليست توصية نهائية.</p>
          <div className="cc-row"><div className="cc-row__body"><b>احتمال الاجتياز {fmtPct(overview.monte_carlo.p_pass)}</b><span>كلما ارتفع، اتسع هامش المناورة أمام الفرص.</span></div></div>
        </article>
      ) : <NeedData text="شغّل التحليل لتظهر مؤشرات الفرص." />}
      <div className="cc-grid-2">
        <Soon title="اقتراح موقع/حي أفضل" icon={<MapPin size={20} />} note="يتطلب بيانات جغرافية وسوقية." />
        <Soon title="منتج/خدمة إضافية وتوسّع" icon={<Lightbulb size={20} />} note="يتطلب محرك توصيات مرتبط ببيانات القطاع." />
      </div>
    </SectionShell>
  );
}

/* ------------------------------------------------------------------ */
/* فهم القرار                                                           */
/* ------------------------------------------------------------------ */

function DecisionSection({ overview }: { overview: ProjectOverview | null }) {
  const { text } = useCustomerLanguage();
  if (!overview) {
    return (
      <SectionShell title="فهم القرار" crumb="فهم القرار">
        <NeedData text="لا يوجد قرار محفوظ لتفسيره بعد." />
      </SectionShell>
    );
  }
  return (
    <SectionShell title="فهم القرار" crumb="فهم القرار">
      <article className="cc-card">
        <h3><FileText size={17} aria-hidden="true" /> لماذا هذا القرار؟</h3>
        <p className="cc-reason">{overview.decision.reason}</p>
        <div className="cc-row"><Chip tone="dim">الحكم</Chip><div className="cc-row__body"><b>{verdictMeta(overview.decision.sovereign_verdict).label}</b><span>{text("قرار محفوظ وقابل للمراجعة", "Saved and reviewable decision")}</span></div></div>
      </article>
      <article className="cc-card">
        <h3><BarChart3 size={17} aria-hidden="true" /> المؤشرات المؤثرة</h3>
        <div className="cc-kpi-grid">
          {overview.kpis.slice(0, 8).map((k: OutputEnvelope) => (
            <div className="cc-kpi-cell" key={k.output_id}>
              <span>{KPI_TITLES[k.output_id] ?? k.output_id}</span>
              <strong>{typeof k.value === "number" ? (k.unit === "percent" ? fmtPct(k.value) : k.unit === "SAR" ? fmtSAR(k.value) : String(k.value)) : "—"}</strong>
            </div>
          ))}
        </div>
      </article>
      <article className="cc-card">
        <h3><Sparkles size={17} aria-hidden="true" /> تصويت الشخصيات السيادية الخمس</h3>
        {overview.personas.map((p) => (
          <div className="cc-row" key={p.persona_id}>
            <div className="cc-row__body"><b>{p.metric}</b><span>{p.note}</span></div>
            <strong className="cc-row__val">{p.value === null ? "—" : fmtPct(p.value)}</strong>
          </div>
        ))}
        <p className="cc-why">الشخصيات تفسّر ولا تصوّت على الحكم — الحكم السيادي هو المرجع.</p>
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
    <SectionShell title="تقاريري" crumb="تقاريري">
      <p className="cc-why">مكتبة المشروع — كل تقرير مرتبط بلقطة ثابتة. تُفتح المخرجات من غرفة التقارير لكل مشروع.</p>
      {withRuns.length ? withRuns.map((b) => (
        <div className="cc-row" key={b.project.project_id}>
          <Chip tone="go">{text("محفوظ", "Saved")}</Chip>
          <div className="cc-row__body">
            <b>{b.project.name}</b>
            <span>تقرير تنفيذي · دراسة جدوى · Decision Pack · PDF/DOCX/PPTX</span>
          </div>
          <button className="cc-btn cc-btn--ghost cc-btn--sm" onClick={() => onOpenStage(b.project.project_id, "snapshots")}>
            فتح المخرجات <ArrowLeft size={13} aria-hidden="true" />
          </button>
        </div>
      )) : <NeedData text="لا توجد لقطات محفوظة بعد. شغّل التحليل في أحد مشاريعك لإنشاء أول تقرير." />}
    </SectionShell>
  );
}

/* ------------------------------------------------------------------ */
/* Attention list (derived from real data only)                         */
/* ------------------------------------------------------------------ */

function AttentionList({ bundles, onOpenStage }: { bundles: Bundle[]; onOpenStage: CommandCenterProps["onOpenStage"] }) {
  const items: Array<{ id: string; pid: string; title: string; detail: string; tone: "warn" | "stop" | "dim"; stage: "evidence" | "readiness" | "decision" | "run" }> = [];
  for (const b of bundles) {
    for (const bl of (b.readiness?.blockers ?? []).slice(0, 2)) {
      items.push({ id: `${b.project.project_id}:${bl.code}`, pid: b.project.project_id, title: `${b.project.name} — يحتاج استكمال جاهزية`, detail: bl.message, tone: "warn", stage: "readiness" });
    }
    const src = b.readiness?.steps.find((s) => s.step_id === "sources" && s.status !== "ready");
    if (src) items.push({ id: `${b.project.project_id}:ev`, pid: b.project.project_id, title: `${b.project.name} — الأدلة غير مكتملة`, detail: src.message || "اربط دليلاً قبل التشغيل.", tone: "dim", stage: "evidence" });
    if (b.overview?.decision.sovereign_verdict === "REVISE_AND_REASSESS") {
      items.push({ id: `${b.project.project_id}:vd`, pid: b.project.project_id, title: `${b.project.name} — القرار يطلب مراجعة`, detail: "آخر حكم سيادي طلب المراجعة وإعادة التقييم.", tone: "stop", stage: "decision" });
    }
  }
  const shown = items.slice(0, 4);
  if (!shown.length) {
    return (
      <div className="cc-clear">
        <CheckCircle2 size={19} aria-hidden="true" />
        <span>لا شيء يحتاج انتباهاً الآن — مشاريعك على المسار.</span>
      </div>
    );
  }
  return (
    <>
      {shown.map((it) => (
        <div className="cc-row" key={it.id}>
          <Chip tone={it.tone}>{it.stage === "readiness" ? "جاهزية" : it.stage === "evidence" ? "أدلة" : "قرار"}</Chip>
          <div className="cc-row__body"><b>{it.title}</b><span>{it.detail}</span></div>
          <button className="cc-btn cc-btn--ghost cc-btn--sm" onClick={() => onOpenStage(it.pid, it.stage)}>
            معالجة <ArrowLeft size={13} aria-hidden="true" />
          </button>
        </div>
      ))}
    </>
  );
}
