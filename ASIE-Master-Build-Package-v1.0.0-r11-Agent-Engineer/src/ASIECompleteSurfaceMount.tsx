import {
  ArrowLeft,
  BarChart3,
  BadgeCheck,
  BookOpenCheck,
  CheckCircle2,
  CircleHelp,
  Database,
  FileSpreadsheet,
  FileText,
  Gauge,
  Landmark,
  LayoutDashboard,
  MapPinned,
  MessagesSquare,
  Rocket,
  ShieldCheck,
  Sparkles,
  Target,
  X,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import { CustomerLanguageSwitcher, useCustomerLanguage } from "./customerLanguage";

type PortalTargets = {
  landing: HTMLElement | null;
  landingNav: HTMLElement | null;
  workspace: HTMLElement | null;
};

type StageDefinition = {
  id: string;
  label: string;
  description: string;
  icon: typeof LayoutDashboard;
  legacyIndex: number;
};

const stageDefinitions: StageDefinition[] = [
  { id: "dashboard", label: "لوحة القيادة", description: "الملخص والإجراءات التالية", icon: LayoutDashboard, legacyIndex: 0 },
  { id: "wizard", label: "مرشد تأسيس المشروع", description: "الموقع والقطاع ورأس المال والمدخلات", icon: Rocket, legacyIndex: 1 },
  { id: "evidence", label: "الأدلة", description: "الملفات والمصادر وإمكانية تتبعها", icon: Database, legacyIndex: 2 },
  { id: "readiness", label: "جاهزية الدراسة", description: "المدخلات التي تمنع إكمال التحليل", icon: CheckCircle2, legacyIndex: 3 },
  { id: "run", label: "تشغيل التحليل", description: "إنشاء نتيجة منضبطة وقابلة للمراجعة", icon: Gauge, legacyIndex: 4 },
  { id: "reality", label: "اختبر السوق", description: "السوق والفرص بعد نتيجة الدراسة", icon: Target, legacyIndex: 5 },
  { id: "decision", label: "فهم القرار", description: "القرار وأسبابه ومخاطره", icon: BookOpenCheck, legacyIndex: 6 },
  { id: "execution", label: "خطة التنفيذ", description: "الخطوات والعوائق بعد القرار", icon: MapPinned, legacyIndex: 7 },
  { id: "snapshots", label: "تقاريري", description: "التقارير والنتائج المحفوظة", icon: FileText, legacyIndex: 8 },
];

const stageEnglish: Record<string, { label: string; description: string }> = {
  dashboard: { label: "Dashboard", description: "Summary and next actions" },
  wizard: { label: "Project setup guide", description: "Location, sector, capital, and inputs" },
  evidence: { label: "Evidence", description: "Files, sources, and traceability" },
  readiness: { label: "Readiness", description: "Gaps blocking the analysis" },
  run: { label: "Run analysis", description: "Create a governed decision reference" },
  reality: { label: "Market intelligence", description: "Market comparisons and opportunities" },
  decision: { label: "Understand the decision", description: "Decision, reasons, and risks" },
  execution: { label: "Execution plan", description: "Actions and blockers after the decision" },
  snapshots: { label: "Reports", description: "Saved reports and outputs" },
};


const landingFeatures = [
  {
    icon: Rocket,
    ar: { title: "تعريف مشروع موجّه", body: "ابدأ بالموقع ثم القطاع والفكرة ورأس المال ضمن خطوات واضحة تمنع تجاوز المعلومات الجوهرية." },
    en: { title: "Guided project setup", body: "Start with location, sector, concept, and capital through clear steps that keep essential information complete." },
  },
  {
    icon: FileSpreadsheet,
    ar: { title: "إدخال مرن للبيانات", body: "أدخل البيانات يدويًا أو استورد ملفات الجداول المتاحة، مع توضيح القدرات التي ما زالت قيد البناء." },
    en: { title: "Flexible data entry", body: "Enter data manually or import supported spreadsheet files, with unfinished capabilities clearly identified." },
  },
  {
    icon: Database,
    ar: { title: "أدلة قابلة للتتبع", body: "يرتبط كل افتراض بدليله ومراجعته، مع فصل واضح بين البيانات المعتمدة وما يحتاج إلى تدقيق." },
    en: { title: "Traceable evidence", body: "Every assumption is linked to its evidence and review, separating approved data from items that still need validation." },
  },
  {
    icon: Gauge,
    ar: { title: "حسابات منضبطة", body: "تخرج الأرقام من حسابات قابلة للاختبار، ولا يُسمح للذكاء الاصطناعي باختراع أرقام مالية." },
    en: { title: "Controlled calculations", body: "Numbers come from testable calculations; AI is never allowed to invent financial figures." },
  },
  {
    icon: BadgeCheck,
    ar: { title: "نتيجة محفوظة", body: "ينتج كل تشغيل ناجح مرجعًا محفوظًا يربط النتيجة بمدخلاتها وأدلتها ويتيح مقارنتها بنتائج سابقة." },
    en: { title: "Saved result", body: "Every successful run creates a saved reference linking the result to its inputs and evidence for later comparison." },
  },
  {
    icon: ShieldCheck,
    ar: { title: "قرار قابل للمراجعة", body: "تعرض مذكرة القرار والمراجعة البشرية الأسباب والحدود دون تغيير الحقائق أو الحسابات." },
    en: { title: "Reviewable decision", body: "The decision memo and human review explain reasons and limits without changing facts or calculations." },
  },
] as const;

const usageTracks = [
  {
    ar: { title: "التجربة المحلية", status: "متاحة الآن", body: "تعريف مشروع وربط أدلة وتشغيل محلي وتقارير من دون مزود خارجي." },
    en: { title: "Local experience", status: "Available now", body: "Set up a project, link evidence, run the analysis, and create reports without an external provider." },
  },
  {
    ar: { title: "المسار الاحترافي", status: "قيد استكمال المنتج", body: "قوالب قطاعية واستيراد مستندات وعروض موردين وذكاء سوق سعودي حي بعد اعتماد مصادرها." },
    en: { title: "Professional track", status: "In development", body: "Sector templates, document intake, supplier quotes, and live Saudi market intelligence after source approval." },
  },
  {
    ar: { title: "المؤسسات والفرق", status: "مخطط", body: "مساحات فرق وصلاحيات واشتراكات وتكاملات لا تُفعّل قبل بوابات الأمان والمراجعة." },
    en: { title: "Organizations and teams", status: "Planned", body: "Team workspaces, permissions, subscriptions, and integrations remain gated by security and review." },
  },
] as const;

function readTargets(): PortalTargets {
  return {
    landing: document.querySelector<HTMLElement>(".landing-page"),
    landingNav: document.querySelector<HTMLElement>(".landing-nav"),
    workspace: document.querySelector<HTMLElement>(".app-shell .workspace"),
  };
}

function activeStageFromDom(): string {
  const buttons = Array.from(document.querySelectorAll<HTMLButtonElement>(".sidebar .nav-group .nav-item"));
  const activeIndex = buttons.findIndex((button) => button.classList.contains("nav-item--active"));
  return stageDefinitions.find((stage) => stage.legacyIndex === activeIndex)?.id ?? "dashboard";
}

function navigateStage(stageId: string) {
  const definition = stageDefinitions.find((stage) => stage.id === stageId);
  if (!definition) return;
  const buttons = Array.from(document.querySelectorAll<HTMLButtonElement>(".sidebar .nav-group .nav-item"));
  const target = buttons[definition.legacyIndex];
  if (target) {
    target.click();
    return;
  }
  window.location.hash = stageId;
}

function enterProduct() {
  const entryButton = document.querySelector<HTMLButtonElement>(".landing-nav__actions .landing-nav__link");
  entryButton?.click();
}

function LandingNavigation() {
  const { text } = useCustomerLanguage();
  return (
    <div className="asie-complete-nav" aria-label={text("روابط صفحة الهبوط", "Landing page links")}>
      <a href="#decision-flow">{text("كيف تعمل", "How it works")}</a>
      <a href="#asie-capabilities">{text("المزايا", "Features")}</a>
      <a className="asie-complete-nav__sanad" href="#asie-sanad">{text("سند", "Sanad")}</a>
      <a href="#asie-usage">{text("المسارات", "Plans")}</a>
      <a href="#asie-faq">{text("الأسئلة", "Questions")}</a>
      <CustomerLanguageSwitcher />
    </div>
  );
}

function LandingCompletion() {
  const { locale, text } = useCustomerLanguage();
  return (
    <div className="asie-complete-landing-sections">
      <section id="asie-capabilities" className="asie-public-section">
        <div className="asie-public-section__heading">
          <span>{text("قدرات مرتبطة بما يعمل فعليًا", "Capabilities connected to the live product")}</span>
          <h2>{text("واجهة موحدة لرحلة القرار، وليست صفحة منفصلة عن النظام.", "One interface for the decision journey, not a page detached from the product.")}</h2>
          <p>{text("توضح الصفحة ما هو متاح الآن وما يزال قيد البناء دون وعود غير مفعلة.", "This page separates what is available now from what is still being built, without inactive promises.")}</p>
        </div>
        <div className="asie-capability-grid">
          {landingFeatures.map(({ icon: Icon, ar, en }) => {
            const copy = locale === "ar" ? ar : en;
            return (
              <article className="asie-capability-card" key={copy.title}>
                <div className="asie-capability-card__icon"><Icon size={22} aria-hidden="true" /></div>
                <h3>{copy.title}</h3>
                <p>{copy.body}</p>
              </article>
            );
          })}
        </div>
      </section>

      <section id="asie-sanad" className="asie-sanad-section">
        <div className="asie-sanad-section__copy">
          <span className="asie-status-pill">{text("مساعد تنقل داخل المنصة", "In-product navigation assistant")}</span>
          <h2>{text("سند يبقيك داخل رحلة المشروع.", "Sanad keeps you inside the project journey.")}</h2>
          <p>{text(
            "يوجهك سند إلى تعريف المشروع والأدلة والجاهزية والقرار، ويقودك مباشرة إلى المدخل الناقص. لا يولد أرقامًا مالية ولا يدّعي مراجعة خارجية.",
            "Sanad guides you through project setup, evidence, readiness, and decision pages, and takes you directly to a missing input. It does not generate financial figures or claim an external review."
          )}</p>
          <div className="asie-sanad-section__actions">
            <button className="primary-button" type="button" onClick={enterProduct}><Rocket size={18} /> {text("ابدأ مساحة المشروع", "Open project workspace")}</button>
            <a href="#asie-faq" className="secondary-button"><CircleHelp size={18} /> {text("اقرأ حدود النسخة", "Read product limits")}</a>
          </div>
        </div>
        <div className="asie-sanad-card" aria-label={text("حدود سند الحالية", "Current Sanad limits")}>
          <div className="asie-sanad-card__stamp">{text("مساعد آمن داخل المنصة", "Safe in-product assistant")}</div>
          <dl>
            <div><dt>{text("توليد الأرقام", "Generating numbers")}</dt><dd>{text("غير مسموح", "Not allowed")}</dd></div>
            <div><dt>{text("الاتصال الخارجي", "External connection")}</dt><dd>{text("غير مفعّل", "Disabled")}</dd></div>
            <div><dt>{text("التوجيه بين الصفحات", "Page guidance")}</dt><dd>{text("متاح", "Available")}</dd></div>
            <div><dt>{text("المراجعة البشرية الخارجية", "External human review")}</dt><dd>{text("تحتاج تفعيلًا مستقلًا", "Requires separate activation")}</dd></div>
          </dl>
        </div>
      </section>

      <section id="asie-usage" className="asie-public-section asie-public-section--soft">
        <div className="asie-public-section__heading">
          <span>{text("مسارات الاستخدام", "Usage tracks")}</span>
          <h2>{text("لا أسعار أو وعود غير مفعّلة.", "No inactive pricing or promises.")}</h2>
          <p>{text("تصف البطاقات حالة المنتج الحالية وخارطة البناء، وليست عروضًا تجارية حية.", "These cards describe current product status and roadmap; they are not live commercial offers.")}</p>
        </div>
        <div className="asie-usage-grid">
          {usageTracks.map(({ ar, en }) => {
            const copy = locale === "ar" ? ar : en;
            return <article key={copy.title}><span>{copy.status}</span><h3>{copy.title}</h3><p>{copy.body}</p></article>;
          })}
        </div>
      </section>

      <section id="asie-faq" className="asie-public-section">
        <div className="asie-public-section__heading">
          <span>{text("أسئلة قبل البدء", "Questions before you start")}</span>
          <h2>{text("حدود واضحة قبل أول مشروع.", "Clear limits before your first project.")}</h2>
        </div>
        <div className="asie-faq-list">
          <details open>
            <summary>{text("هل الذكاء الاصطناعي يحسب الأرقام المالية؟", "Does AI calculate financial figures?")}</summary>
            <p>{text("لا. الحسابات المالية منضبطة وقابلة للاختبار، بينما تشرح أدوات الذكاء وتوجّه فقط.", "No. Financial calculations are controlled and testable; AI tools only explain and guide.")}</p>
          </details>
          <details>
            <summary>{text("ما أنواع الملفات المتاحة حاليًا؟", "Which file types are currently supported?")}</summary>
            <p>{text("الإدخال اليدوي وملفات الجداول المتاحة تعمل الآن. استيراد أنواع أخرى ما زال قيد البناء.", "Manual entry and supported spreadsheet files work now. Other document types are still being built.")}</p>
          </details>
          <details>
            <summary>{text("هل توجد مصادر سوق خارجية حية؟", "Are live external market sources available?")}</summary>
            <p>{text("ليست مفعلة في الوضع الحالي. تُفتح المصادر الحية فقط بعد اعتماد المصدر وفحوص الجودة والأمان.", "Not in the current mode. Live sources are enabled only after source approval and quality and security checks.")}</p>
          </details>
          <details>
            <summary>{text("ما الذي تحفظه النتيجة؟", "What does a saved result contain?")}</summary>
            <p>{text("تحفظ نتيجة التشغيل ومدخلاتها وأدلتها لتبقى قابلة للمراجعة والمقارنة.", "It preserves the run result, inputs, and evidence for review and comparison.")}</p>
          </details>
        </div>
      </section>

      <section className="asie-public-final">
        <Sparkles size={22} aria-hidden="true" />
        <h2>{text("ابدأ بالمشروع، ثم دع الأدلة تقود القرار.", "Start with the project, then let evidence guide the decision.")}</h2>
        <p>{text("واجهة واضحة ومسار يحترم حدود التنفيذ الفعلي.", "A clear interface and a journey that respects real product limits.")}</p>
        <button type="button" className="primary-button primary-button--large" onClick={enterProduct}>{text("ابدأ مساحة المشروع", "Open project workspace")}</button>
      </section>

      <footer className="asie-public-footer">
        <strong>ASIE</strong>
        <span>{text("العربية أولًا · تشغيل منضبط", "English interface · Controlled operation")}</span>
      </footer>
    </div>
  );
}

function WorkspaceHub({ activeStage }: { activeStage: string }) {
  const { locale, text } = useCustomerLanguage();
  return (
    <section className="asie-page-hub" aria-label={text("خريطة صفحات ASIE", "ASIE page map")}>
      <div className="asie-page-hub__heading">
        <div>
          <span>{text("خريطة مساحة القرار", "Decision workspace map")}</span>
          <h2>{text("انتقل مباشرة بين صفحات المشروع", "Move directly between project pages")}</h2>
        </div>
        <small>{text("كل صفحة تعرض بيانات المشروع المحفوظة دون إعادة حسابها.", "Each page shows saved project data without recalculating it.")}</small>
      </div>
      <div className="asie-page-hub__grid">
        {stageDefinitions.map(({ id, label, description, icon: Icon }) => (
          <button
            className={activeStage === id ? "asie-page-link asie-page-link--active" : "asie-page-link"}
            key={id}
            type="button"
            onClick={() => navigateStage(id)}
            aria-current={activeStage === id ? "page" : undefined}
          >
            <Icon size={18} aria-hidden="true" />
            <span>
              <strong>{locale === "ar" ? label : stageEnglish[id]?.label}</strong>
              <small>{locale === "ar" ? description : stageEnglish[id]?.description}</small>
            </span>
          </button>
        ))}
      </div>
    </section>
  );
}

function SanadAssistant({
  onClose,
  missingLabel,
  returnStage,
  onNavigateMissing,
  onReturn,
}: {
  onClose: () => void;
  missingLabel: string;
  returnStage: string | null;
  onNavigateMissing: () => void;
  onReturn: () => void;
}) {
  const { direction, text } = useCustomerLanguage();
  return (
    <aside className="asie-sanad-assistant" aria-label={text("سند — مساعد التنقل", "Sanad — navigation assistant")} dir={direction}>
      <header>
        <div><MessagesSquare size={20} /><strong>{text("سند", "Sanad")}</strong></div>
        <button type="button" onClick={onClose} aria-label={text("إغلاق سند", "Close Sanad")}><X size={18} /></button>
      </header>
      <p>{text("يساعدك سند على معرفة ما يمنع التقدم والانتقال إلى الخطوة المطلوبة.", "Sanad explains what is blocking progress and takes you to the required step.")}</p>
      {missingLabel ? (
        <section className="asie-sanad-assistant__blocker" role="status">
          <strong>{text("ما الذي يمنع التقدم الآن؟", "What is blocking progress now?")}</strong>
          <span>{missingLabel}</span>
          <button type="button" onClick={onNavigateMissing}>
            <Target size={16} /> {text("أكمل هذا المدخل", "Complete this input")}
          </button>
        </section>
      ) : (
        <p>{text("لا يوجد مدخل إلزامي ناقص ظاهر الآن.", "No required missing input is currently visible.")}</p>
      )}
      <div>
        <button type="button" onClick={() => navigateStage("wizard")}><Rocket size={16} /> {text("عرّف المشروع", "Set up project")}</button>
        <button type="button" onClick={() => navigateStage("evidence")}><Database size={16} /> {text("اربط الأدلة", "Link evidence")}</button>
        <button type="button" onClick={() => navigateStage("decision")}><BookOpenCheck size={16} /> {text("افهم القرار", "Understand decision")}</button>
        {returnStage ? <button type="button" onClick={onReturn}><ArrowLeft size={16} /> {text("العودة إلى الصفحة السابقة", "Return to previous page")}</button> : null}
      </div>
    </aside>
  );
}

export function ASIECompleteSurfaceMount() {
  const { text } = useCustomerLanguage();
  const [targets, setTargets] = useState<PortalTargets>(() => readTargets());
  const [activeStage, setActiveStage] = useState(() => activeStageFromDom());
  const [sanadOpen, setSanadOpen] = useState(false);
  const [returnStage, setReturnStage] = useState<string | null>(() => window.sessionStorage.getItem("asie.sanad.return_stage"));

  useEffect(() => {
    const refresh = () => {
      setTargets(readTargets());
      setActiveStage(activeStageFromDom());
    };
    const observer = new MutationObserver(refresh);
    observer.observe(document.body, { subtree: true, childList: true, attributes: true, attributeFilter: ["class"] });
    window.addEventListener("hashchange", refresh);
    window.addEventListener("popstate", refresh);
    refresh();
    return () => {
      observer.disconnect();
      window.removeEventListener("hashchange", refresh);
      window.removeEventListener("popstate", refresh);
    };
  }, []);

  const missingLabel = targets.workspace?.dataset.asieMissingLabel ?? "";

  function navigateToMissingInput() {
    const currentStage = activeStageFromDom();
    if (currentStage !== "wizard" && currentStage !== "readiness") {
      window.sessionStorage.setItem("asie.sanad.return_stage", currentStage);
      setReturnStage(currentStage);
    }
    window.dispatchEvent(new CustomEvent("asie:navigate-missing-input"));
    setSanadOpen(false);
  }

  function returnFromMissingInput() {
    if (returnStage) navigateStage(returnStage);
    window.sessionStorage.removeItem("asie.sanad.return_stage");
    setReturnStage(null);
    setSanadOpen(false);
  }

    const portals = useMemo(() => {
    const items = [];
    if (targets.landingNav) items.push(createPortal(<LandingNavigation />, targets.landingNav, "asie-landing-nav"));
    if (targets.landing) items.push(createPortal(<LandingCompletion />, targets.landing, "asie-landing-completion"));
    if (targets.workspace) items.push(createPortal(<WorkspaceHub activeStage={activeStage} />, targets.workspace, "asie-workspace-hub"));
    return items;
  }, [activeStage, targets]);

  return (
    <>
      {portals}
      {targets.workspace ? (
        <>
          <button className="asie-sanad-launcher" type="button" onClick={() => setSanadOpen((value) => !value)} aria-expanded={sanadOpen}>
            <MessagesSquare size={18} aria-hidden="true" /> {text("سند", "Sanad")}
          </button>
          {sanadOpen ? <SanadAssistant onClose={() => setSanadOpen(false)} missingLabel={missingLabel} returnStage={returnStage} onNavigateMissing={navigateToMissingInput} onReturn={returnFromMissingInput} /> : null}
        </>
      ) : null}
    </>
  );
}
