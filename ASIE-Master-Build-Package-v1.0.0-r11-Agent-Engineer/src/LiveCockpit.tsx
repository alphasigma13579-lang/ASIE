import {
  ArrowLeft,
  BadgeCheck,
  Bot,
  Building2,
  ClipboardList,
  Compass,
  Lightbulb,
  MapPinned,
  Route,
  Sparkles,
  Target,
  Telescope,
  Users,
} from "lucide-react";
import { useMemo, useState } from "react";

type LiveCockpitProps = {
  projectName?: string;
  sector?: string;
  location?: string;
  snapshotId?: string | null;
  signals?: StudySignals;
  onContinue?: () => void;
};

type StudySignals = {
  monthlyProfit?: number | null;
  paybackMonths?: number | null;
  fundingGap?: number | null;
  feasibilityProbability?: number | null;
  monthlyUnits?: number | null;
};

type ComparisonScope = "السعودية" | "العالم العربي" | "العالم";

const comparisonProfiles: Record<ComparisonScope, { title: string; observation: string; lesson: string }> = {
  "السعودية": {
    title: "نموذج محلي مشابه",
    observation: "محاكاة لمنشأة بدأت بنطاق صغير، ثم توسعت بعد إثبات الطلب والتشغيل.",
    lesson: "اختبر سبب شراء العميل وتكلفة اكتسابه قبل الالتزام بتوسع كبير.",
  },
  "العالم العربي": {
    title: "نموذج إقليمي مشابه",
    observation: "محاكاة لمشروع نجح في العرض لكنه تعثر عند التوسع قبل ضبط التشغيل.",
    lesson: "لا تنقل نموذجاً إقليمياً قبل اختبار الملاءمة للسوق السعودي ومدينتك.",
  },
  "العالم": {
    title: "نموذج عالمي مشابه",
    observation: "محاكاة لمشروع ركّز على تجربة العميل وكفاءة التشغيل، لا على خفض السعر وحده.",
    lesson: "خذ المبدأ القابل للتطبيق، لا تفترض أن السوق المحلي يتصرف كالسوق العالمي.",
  },
};

function DemoTag({ compact = false }: { compact?: boolean }) {
  return <span className={compact ? "demo-badge demo-badge--compact" : "demo-badge"}>محاكاة تطوير · بيانات غير حقيقية</span>;
}

function formatStudyNumber(value: number | null | undefined, suffix = "") {
  if (typeof value !== "number" || !Number.isFinite(value)) return "غير متاح";
  return `${new Intl.NumberFormat("ar-SA", { maximumFractionDigits: 0 }).format(value)}${suffix}`;
}

function classifyProject(sector?: string) {
  const normalized = (sector ?? "").toLowerCase();
  if (/لوجست|نقل|مستودع|توصيل|تجارة|خدم/.test(normalized)) return "خدمي / تشغيلي";
  if (/صناع|إنتاج|غذائ|زراع|تصنيع/.test(normalized)) return "إنتاجي";
  if (/تقن|برمج|رقمي|منص/.test(normalized)) return "تقني / رقمي";
  return "قيد التصنيف";
}

function visionHypothesis(sector?: string) {
  const normalized = (sector ?? "").toLowerCase();
  if (/لوجست|نقل|مستودع|توصيل/.test(normalized)) return "المملكة مركزاً لوجستياً";
  if (/تقن|برمج|رقمي|منص/.test(normalized)) return "التحول الرقمي";
  if (/صح|عاف|طب/.test(normalized)) return "جودة الحياة";
  if (/صناع|إنتاج|غذائ|زراع|تصنيع/.test(normalized)) return "تنويع الاقتصاد";
  return "تنويع الاقتصاد وتمكين المنشآت";
}

function deriveStudyAdvice(signals?: StudySignals) {
  const hasStudySignal = Object.values(signals ?? {}).some((value) => typeof value === "number" && Number.isFinite(value));
  if (!hasStudySignal) {
    return {
      hasStudySignal,
      improvement: "لا توجد نتيجة دراسة محفوظة كافية لصياغة اقتراح تجريبي مخصص.",
      alternative: "أكمل التشغيل أولاً؛ عندها تعرض المنصة فرضية بديلة مرتبطة بمؤشرات الدراسة.",
      review: "راجع المدخلات الأساسية والأدلة قبل اعتماد أي فرضية سوقية.",
      saturation: "غير مقاس",
      competition: "ينتظر نتيجة الدراسة",
      opportunity: "غير متاح",
    };
  }
  const fundingPressure = (signals?.fundingGap ?? 0) > 0;
  const weakProfit = typeof signals?.monthlyProfit === "number" && signals.monthlyProfit <= 0;
  const longPayback = typeof signals?.paybackMonths === "number" && signals.paybackMonths > 36;
  const lowFeasibility = typeof signals?.feasibilityProbability === "number" && signals.feasibilityProbability < 0.5;
  const pressure = weakProfit || longPayback || lowFeasibility || fundingPressure;
  return {
    hasStudySignal,
    improvement: weakProfit
      ? "تشير نتيجة الربح الشهري التجريبية إلى ضرورة اختبار السعر أو التكلفة أو حجم الطلب قبل التوسع."
      : longPayback
        ? "تشير مدة الاسترداد التجريبية إلى اختبار إطلاق أصغر أو مراحل استثمارية متتابعة."
        : fundingPressure
          ? "تشير فجوة التمويل التجريبية إلى ترتيب الإنفاق على مراحل قبل الالتزام بكامل رأس المال."
          : "تسمح مؤشرات الدراسة التجريبية باختبار شريحة عميل أو عرض قيمة محدد قبل التوسع.",
    alternative: pressure
      ? "فرضية بديلة: نموذج أخف في الأصول أو إطلاق محدود في نطاقك الجغرافي ثم التوسع بعد إثبات الطلب."
      : "فرضية بديلة: خدمة أو قناة مبيعات مجاورة تزيد الاستخدام قبل إضافة تكاليف ثابتة جديدة.",
    review: lowFeasibility
      ? "احتمال الاجتياز التجريبي منخفض؛ راجع الطلب والسعر والتكلفة، ثم اختبرها ميدانياً قبل القرار."
      : "ما يغيّر هذه القراءة: عروض أسعار موثقة، زيارة ميدانية، ومقارنة ثلاثة بدائل في موقعك.",
    saturation: pressure ? "تحتاج اختباراً ميدانياً" : "قابلة للاختبار",
    competition: pressure ? "تحتاج تمييز العرض" : "تحتاج مقارنة محلية",
    opportunity: pressure ? "إطلاق متدرج" : "اختبار شريحة محددة",
  };
}

function deriveTeamSize(monthlyUnits?: number | null) {
  if (typeof monthlyUnits !== "number" || monthlyUnits <= 0) return "لا يمكن تقدير الفريق دون طاقة تشغيلية";
  if (monthlyUnits <= 500) return "٢–٣ أفراد كبداية";
  if (monthlyUnits <= 1500) return "٤–٦ أفراد كبداية";
  return "٧–١٠ أفراد كبداية";
}

export function LiveCockpit({ projectName, sector, location, snapshotId, signals, onContinue }: LiveCockpitProps) {
  const [scope, setScope] = useState<ComparisonScope>("السعودية");
  const context = `${sector || "قطاع المشروع"} · ${location || "الموقع المحدد"}`;
  const studyAdvice = deriveStudyAdvice(signals);
  const projectType = classifyProject(sector);
  const vision = visionHypothesis(sector);
  const teamSize = deriveTeamSize(signals?.monthlyUnits);
  const competitors = useMemo(
    () => ["١", "٢", "٣"].map((number, index) => ({
      name: `${location || "النطاق المحدد"} · منشأة مماثلة ${number}`,
      signal: ["عرض قريب من العميل", "سعر يحتاج مقارنة", "خدمة أو موقع بديل"][index],
      pressure: ["متوسط", "مرتفع", "منخفض"][index],
    })),
    [location]
  );
  const profile = comparisonProfiles[scope];

  return <section className="live-cockpit live-cockpit--r3" aria-label="ذكاء السوق والفرص التجريبي">
    <header className="cockpit-intro">
      <div>
        <p className="eyebrow"><Sparkles size={15} aria-hidden="true" /> مرحلة ما بعد الدراسة المالية</p>
        <h2>ذكاء السوق والفرص</h2>
        <p>هذه المرحلة تقرأ سياق المشروع واللقطة الناتجة من الدراسة، ثم تعرض محاكاة واضحة للمنافسة والفرص والتوصيات. لا توجد مصادر حية أو حكم استثماري في بيئة التطوير.</p>
      </div>
      <DemoTag />
    </header>

    <section className="market-context-strip" aria-label="سياق التحليل التجريبي">
      <div><span>المشروع</span><strong>{projectName || "مسودة المشروع"}</strong></div>
      <div><span>السياق</span><strong>{context}</strong></div>
      <div><span>مرجع الدراسة</span><strong>{snapshotId ? snapshotId.slice(-10) : "لم تنشأ لقطة بعد"}</strong></div>
      <DemoTag compact />
    </section>

    <div className="cockpit-grid cockpit-grid--r3">
      <article className="market-map-widget">
        <div className="widget-heading"><div><MapPinned size={20} /><div><span>المنافسة في النطاق</span><strong>إشارات تجريبية حول الموقع</strong></div></div><small>ليست خريطة فعلية</small></div>
        <div className="local-map local-map--demo" role="img" aria-label="خريطة تجريبية لمنافسين محتملين">
          <span className="map-road map-road--one" /><span className="map-road map-road--two" /><span className="map-zone map-zone--one">منطقة حركة</span><span className="map-zone map-zone--two">نطاق المشروع</span>
          {competitors.map((competitor, index) => <div className={`map-marker map-marker--static map-marker--${index + 1}`} key={competitor.name}><Building2 size={14} /></div>)}
          <div className="site-marker" style={{ left: "52%", top: "41%" }}><Target size={15} /><span>موقع مرشح</span></div>
        </div>
        <div className="market-signal-list">
          {competitors.map((competitor) => <div key={competitor.name}><strong>{competitor.name}</strong><span>{competitor.signal} · ضغط {competitor.pressure}</span></div>)}
        </div>
        <DemoTag compact />
      </article>

      <article className="cockpit-kpis-widget">
        <div className="widget-heading"><div><Compass size={20} /><div><span>قراءة الفرصة</span><strong>مؤشرات محاكاة مشتقة من الدراسة</strong></div></div><small>ليست نتائج سوق</small></div>
        <div className="cockpit-kpis">
          <div className="cockpit-kpi cockpit-kpi--mint"><span>درجة التشبع</span><strong>{studyAdvice.saturation}</strong><small>قالب تطوير، لا يستند إلى تعداد منشآت حقيقي.</small></div>
          <div className="cockpit-kpi cockpit-kpi--amber"><span>ضغط المنافسة</span><strong>{studyAdvice.competition}</strong><small>اربطه لاحقاً بمقارنة السعر والعرض والوصول ميدانياً.</small></div>
          <div className="cockpit-kpi cockpit-kpi--blue"><span>إمكان تحسين النموذج</span><strong>{studyAdvice.opportunity}</strong><small>{studyAdvice.hasStudySignal ? "يتغير بحسب مخرجات الدراسة، لا بحسب بيانات سوق حية." : "يظهر بعد اكتمال الدراسة."}</small></div>
        </div>
        <DemoTag compact />
      </article>

      <article className="benchmark-widget">
        <div className="widget-heading"><div><Telescope size={20} /><div><span>مقارنات مرجعية</span><strong>سعودية ثم عربية ثم عالمية</strong></div></div><small>حالات تجريبية</small></div>
        <div className="benchmark-tabs" role="tablist" aria-label="نطاق المقارنة">
          {(Object.keys(comparisonProfiles) as ComparisonScope[]).map((item) => <button type="button" key={item} role="tab" aria-selected={scope === item} className={scope === item ? "benchmark-tab benchmark-tab--active" : "benchmark-tab"} onClick={() => setScope(item)}>{item}</button>)}
        </div>
        <div className="benchmark-detail"><span>حالة محاكاة</span><strong>{profile.title}</strong><p>{profile.observation}</p><div><ArrowLeft size={15} /><small>{profile.lesson}</small></div></div>
        <DemoTag compact />
      </article>

      <article className="ai-advisory-demo">
        <div className="widget-heading"><div><Bot size={20} /><div><span>اقتراحات الذكاء الاصطناعي</span><strong>استنتاجات تجريبية من بيانات الدراسة</strong></div></div><small>ليست توصية نهائية</small></div>
        <div className="ai-advisory-demo__list">
          <div><Lightbulb size={17} /><div><strong>تحسين الفكرة</strong><small>{studyAdvice.improvement}</small></div></div>
          <div><Route size={17} /><div><strong>بديل محتمل</strong><small>{studyAdvice.alternative}</small></div></div>
          <div><ClipboardList size={17} /><div><strong>ما الذي يغيّر الحكم؟</strong><small>{studyAdvice.review}</small></div></div>
        </div>
        {studyAdvice.hasStudySignal ? <p>إشارات الدراسة التجريبية: صافي شهري {formatStudyNumber(signals?.monthlyProfit, " ر.س")} · استرداد {formatStudyNumber(signals?.paybackMonths, " شهراً")} · فجوة تمويل {formatStudyNumber(signals?.fundingGap, " ر.س")}.</p> : null}
        <p>لا يولد الذكاء هنا رقماً أو حكماً سيادياً أو قراراً نيابة عن المستخدم، ولا تدخل هذه المحاكاة في اللقطة أو التقرير.</p>
        <DemoTag compact />
      </article>

      <article className="vision-alignment-demo">
        <div className="widget-heading"><div><BadgeCheck size={20} /><div><span>التوافق الاستراتيجي</span><strong>رؤية 2030 واتجاهات السوق</strong></div></div><small>إطار تجريبي</small></div>
        <div className="vision-alignment-demo__grid">
          <div><span>تصنيف تجريبي</span><strong>{projectType}</strong><small>مشتق من وصف القطاع ويحتاج قاعدة تصنيف معتمدة لاحقاً.</small></div>
          <div><span>فرضية توافق مع رؤية 2030</span><strong>{vision}</strong><small>ليست درجة مواءمة ولا تعتمد على بيانات رسمية حية.</small></div>
          <div><span>اتجاه السوق</span><strong>{studyAdvice.hasStudySignal ? "فرضية مرتبطة بالدراسة" : "ينتظر الدراسة"}</strong><small>لا يمثل توصية دولية أو مؤشراً وطنياً فعلياً.</small></div>
        </div>
        <DemoTag compact />
      </article>

      <article className="guidance-widget guidance-widget--r3">
        <div className="widget-heading"><div><Users size={20} /><div><span>ما بعد القرار</span><strong>استعداد البداية والتشغيل</strong></div></div><small>قائمة تجريبية</small></div>
        <ol><li><span>01</span><div><strong>التراخيص والجهات</strong><small>ستظهر بحسب {location || "الموقع"} والقطاع بعد ربط قواعد الجهات الرسمية.</small></div></li><li><span>02</span><div><strong>المستندات</strong><small>سجل تجاري، عنوان، تراخيص قطاعية، وعقود حسب نوع المشروع — محاكاة فقط الآن.</small></div></li><li><span>03</span><div><strong>فريق البداية التجريبي</strong><small>{teamSize}؛ مشتق من الطاقة التشغيلية المدخلة وليس متطلباً رسمياً.</small></div></li></ol>
        <DemoTag compact />
      </article>
    </div>

    {onContinue ? <div className="cockpit-continue"><div><strong>أكملت قراءة محاكاة السوق</strong><span>انتقل الآن إلى حزمة القرار، ثم إلى خارطة البدء.</span></div><button className="primary-button" type="button" onClick={onContinue}>انتقل إلى القرار <ArrowLeft size={17} /></button></div> : null}
  </section>;
}
