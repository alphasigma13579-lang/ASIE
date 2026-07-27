import {
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
  { id: "wizard", label: "مرشد تأسيس المشروع", description: "الموقع، القطاع، رأس المال والمدخلات", icon: Rocket, legacyIndex: 1 },
  { id: "evidence", label: "طبقة الأدلة", description: "الملفات والمصادر وخط النسب", icon: Database, legacyIndex: 2 },
  { id: "readiness", label: "جاهزية الدراسة", description: "الفجوات التي تمنع التشغيل", icon: CheckCircle2, legacyIndex: 3 },
  { id: "run", label: "تشغيل التحليل", description: "المسار الحتمي المجمّد", icon: Gauge, legacyIndex: 4 },
  { id: "reality", label: "اختبر السوق", description: "السوق والفرص بعد نتيجة الدراسة", icon: Target, legacyIndex: 5 },
  { id: "decision", label: "فهم القرار", description: "الحكم، السبب والمخاطر", icon: BookOpenCheck, legacyIndex: 6 },
  { id: "execution", label: "خارطة التنفيذ", description: "الخطوات والعوائق بعد القرار", icon: MapPinned, legacyIndex: 7 },
  { id: "snapshots", label: "تقاريري", description: "Snapshots والمخرجات المحفوظة", icon: FileText, legacyIndex: 8 },
];

const landingFeatures = [
  {
    icon: Rocket,
    title: "تعريف مشروع موجّه",
    body: "ابدأ بالموقع ثم القطاع والتصنيف والفكرة ورأس المال، ضمن خطوات محكومة لا تسمح بتجاوز الحقول الجوهرية.",
  },
  {
    icon: FileSpreadsheet,
    title: "إدخال يدوي أو CSV/XLSX",
    body: "المسار الحي يقبل الإدخال اليدوي وملفات CSV وExcel. استيراد PDF واستخراج عروض الأسعار يبقيان ضمن خطة البناء ولا يعرضان كقدرة حية.",
  },
  {
    icon: Database,
    title: "Evidence Ledger قابل للتتبع",
    body: "يرتبط كل افتراض بالدليل والتحويل والمراجعة، مع فصل واضح بين المدخلات المعتمدة والبيانات التي ما زالت تحتاج تدقيقًا.",
  },
  {
    icon: Gauge,
    title: "محرك مالي حتمي",
    body: "الحسابات تنتج من وحدات برمجية قابلة للاختبار. الذكاء الاصطناعي لا يُسمح له باختراع رقم مالي أو استبدال المعادلات.",
  },
  {
    icon: BadgeCheck,
    title: "Snapshot ثابت",
    body: "كل تشغيل ناجح ينتج مرجع قرار محفوظًا يربط النتيجة بمدخلاتها وأدلتها، ويمكن مقارنته بالتشغيلات السابقة.",
  },
  {
    icon: ShieldCheck,
    title: "قرار ومراجعة محكومة",
    body: "حزمة القرار وطبقة المراجعة البشرية تعملان داخل الحدود المعمارية، ولا تغيّران الحقائق أو الحسابات الحتمية.",
  },
] as const;

const usageTracks = [
  {
    title: "التجربة المحلية",
    status: "متاحة الآن",
    body: "تعريف مشروع، ربط أدلة، تشغيل محلي، Snapshot وتقارير من دون مزود خارجي.",
  },
  {
    title: "المسار الاحترافي",
    status: "قيد استكمال المنتج",
    body: "قوالب قطاعية، PDF Intake، عروض الموردين، وذكاء سوق سعودي حي بعد قبول عقودها ومصادرها.",
  },
  {
    title: "المؤسسات والفرق",
    status: "مخطط",
    body: "مساحات فرق، استحقاقات واشتراكات وتكاملات خارجية لا تُفعّل قبل بوابات الأمان والمراجعة.",
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
  return (
    <div className="asie-complete-nav" aria-label="روابط صفحة الهبوط">
      <a href="#decision-flow">كيف تعمل</a>
      <a href="#asie-capabilities">المزايا</a>
      <a className="asie-complete-nav__sanad" href="#asie-sanad">سند</a>
      <a href="#asie-usage">المسارات</a>
      <a href="#asie-faq">الأسئلة</a>
    </div>
  );
}

function LandingCompletion() {
  return (
    <div className="asie-complete-landing-sections">
      <section id="asie-capabilities" className="asie-public-section">
        <div className="asie-public-section__heading">
          <span>قدرات مرتبطة بالمعمارية الحية</span>
          <h2>واجهة موحدة لرحلة القرار، لا قالب منفصل عن النظام.</h2>
          <p>تستخدم هذه الصفحة ما هو منفذ أو مقيد فعليًا في ASIE، وتُصرّح بوضوح بما لا يزال ضمن خطة البناء.</p>
        </div>
        <div className="asie-capability-grid">
          {landingFeatures.map(({ icon: Icon, title, body }) => (
            <article className="asie-capability-card" key={title}>
              <div className="asie-capability-card__icon"><Icon size={22} aria-hidden="true" /></div>
              <h3>{title}</h3>
              <p>{body}</p>
            </article>
          ))}
        </div>
      </section>

      <section id="asie-sanad" className="asie-sanad-section">
        <div className="asie-sanad-section__copy">
          <span className="asie-status-pill">واجهة توجيه محلية</span>
          <h2>سند — يبقي المستخدم داخل رحلة المشروع.</h2>
          <p>
            في هذه الحزمة يعمل سند كواجهة مساعدة للتنقل إلى تعريف المشروع، الأدلة، الجاهزية والقرار. لا يتصل بمزود ذكاء خارجي، ولا يولد أرقامًا مالية، ولا يدّعي وجود مراجعة خبير خارجية قبل تفعيلها بعقد مستقل.
          </p>
          <div className="asie-sanad-section__actions">
            <button className="primary-button" type="button" onClick={enterProduct}><Rocket size={18} /> ابدأ مساحة المشروع</button>
            <a href="#asie-faq" className="secondary-button"><CircleHelp size={18} /> اقرأ حدود النسخة</a>
          </div>
        </div>
        <div className="asie-sanad-card" aria-label="حدود سند الحالية">
          <div className="asie-sanad-card__stamp">محكوم محليًا</div>
          <dl>
            <div><dt>توليد الأرقام</dt><dd>ممنوع</dd></div>
            <div><dt>مزود خارجي</dt><dd>غير مفعّل</dd></div>
            <div><dt>التوجيه بين الصفحات</dt><dd>متاح</dd></div>
            <div><dt>المراجعة البشرية الخارجية</dt><dd>تحتاج تفعيلًا مستقلًا</dd></div>
          </dl>
        </div>
      </section>

      <section id="asie-usage" className="asie-public-section asie-public-section--soft">
        <div className="asie-public-section__heading">
          <span>مسارات الاستخدام</span>
          <h2>لا أسعار أو وعود غير مفعّلة.</h2>
          <p>هذه البطاقات تصف حالة المنتج الحالية وخارطة البناء، وليست بوابة دفع أو عروضًا تجارية حية.</p>
        </div>
        <div className="asie-usage-grid">
          {usageTracks.map((track) => (
            <article key={track.title}>
              <span>{track.status}</span>
              <h3>{track.title}</h3>
              <p>{track.body}</p>
            </article>
          ))}
        </div>
      </section>

      <section id="asie-faq" className="asie-public-section">
        <div className="asie-public-section__heading">
          <span>أسئلة قبل البدء</span>
          <h2>حدود واضحة قبل أول مشروع.</h2>
        </div>
        <div className="asie-faq-list">
          <details open>
            <summary>هل الذكاء الاصطناعي يحسب الأرقام المالية؟</summary>
            <p>لا. الحسابات المالية حتمية وتخرج من وحدات برمجية قابلة للاختبار. واجهات الذكاء تشرح وتوجّه فقط ضمن السياسات المعتمدة.</p>
          </details>
          <details>
            <summary>ما أنواع الملفات المتاحة حاليًا؟</summary>
            <p>الإدخال اليدوي وCSV وXLSX متاحة في المسار الحي. PDF واستخراج عروض الموردين ما زالا ضمن خطة البناء ولا يعرضان هنا كقدرة مكتملة.</p>
          </details>
          <details>
            <summary>هل توجد مصادر سوق خارجية حية؟</summary>
            <p>لا في الوضع الحالي. الجلب الخارجي ومزودو الذكاء معطلون، وتظل البيانات السوقية الحية خاضعة لعقود المصادر وبوابات الجودة والمراجعة.</p>
          </details>
          <details>
            <summary>ما الذي يحفظه Snapshot؟</summary>
            <p>يحفظ مرجع التشغيل ونتيجته ومدخلاته وأدلته وفق المسار المعماري المجمّد، ليبقى القرار قابلًا للمراجعة والمقارنة.</p>
          </details>
        </div>
      </section>

      <section className="asie-public-final">
        <Sparkles size={22} aria-hidden="true" />
        <h2>ابدأ بالمشروع، ثم دع الأدلة تقود القرار.</h2>
        <p>واجهة عربية موحدة، ألوان مؤسسية ثابتة، ومسار يحترم حدود التنفيذ الفعلي.</p>
        <button type="button" className="primary-button primary-button--large" onClick={enterProduct}>ابدأ مساحة المشروع</button>
      </section>

      <footer className="asie-public-footer">
        <strong>ASIE — AlphaSigma Intelligence Engine</strong>
        <span>واجهة عربية أولًا · أخضر مؤسسي · تشغيل محكوم</span>
      </footer>
    </div>
  );
}

function WorkspaceHub({ activeStage }: { activeStage: string }) {
  return (
    <section className="asie-page-hub" aria-label="خريطة صفحات ASIE">
      <div className="asie-page-hub__heading">
        <div>
          <span>خريطة مساحة القرار</span>
          <h2>انتقل مباشرة بين صفحات ASIE الحية</h2>
        </div>
        <small>الصفحات تعرض بيانات النظام الفعلية؛ لا تضيف هذه الطبقة أي حساب أو Snapshot.</small>
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
            <span><strong>{label}</strong><small>{description}</small></span>
          </button>
        ))}
      </div>
    </section>
  );
}

function SanadAssistant({ onClose }: { onClose: () => void }) {
  return (
    <aside className="asie-sanad-assistant" aria-label="سند — مساعد التنقل المحلي">
      <header>
        <div><MessagesSquare size={20} /><strong>سند</strong></div>
        <button type="button" onClick={onClose} aria-label="إغلاق سند"><X size={18} /></button>
      </header>
      <p>مساعد تنقل محلي. لا يولد أرقامًا، ولا يتصل بمزود خارجي، ولا يتجاوز بوابات ASIE.</p>
      <div>
        <button type="button" onClick={() => navigateStage("wizard")}><Rocket size={16} /> عرّف المشروع</button>
        <button type="button" onClick={() => navigateStage("evidence")}><Database size={16} /> اربط الأدلة</button>
        <button type="button" onClick={() => navigateStage("decision")}><BookOpenCheck size={16} /> افهم القرار</button>
      </div>
    </aside>
  );
}

export function ASIECompleteSurfaceMount() {
  const [targets, setTargets] = useState<PortalTargets>(() => readTargets());
  const [activeStage, setActiveStage] = useState(() => activeStageFromDom());
  const [sanadOpen, setSanadOpen] = useState(false);

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
            <MessagesSquare size={18} aria-hidden="true" /> سند
          </button>
          {sanadOpen ? <SanadAssistant onClose={() => setSanadOpen(false)} /> : null}
        </>
      ) : null}
    </>
  );
}
