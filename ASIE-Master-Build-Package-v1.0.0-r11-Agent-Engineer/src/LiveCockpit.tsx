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
  onContinue?: () => void;
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

export function LiveCockpit({ projectName, sector, location, snapshotId, onContinue }: LiveCockpitProps) {
  const [scope, setScope] = useState<ComparisonScope>("السعودية");
  const context = `${sector || "قطاع المشروع"} · ${location || "الموقع المحدد"}`;
  const competitors = useMemo(
    () => ["منشأة مماثلة ١", "منشأة مماثلة ٢", "منشأة مماثلة ٣"].map((name, index) => ({
      name,
      signal: ["عرض قريب من العميل", "سعر يحتاج مقارنة", "خدمة أو موقع بديل"][index],
      pressure: ["متوسط", "مرتفع", "منخفض"][index],
    })),
    []
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
        <div className="widget-heading"><div><Compass size={20} /><div><span>قراءة الفرصة</span><strong>مؤشرات محاكاة لا نتائج سوق</strong></div></div><small>تحتاج مصادر لاحقاً</small></div>
        <div className="cockpit-kpis">
          <div className="cockpit-kpi cockpit-kpi--mint"><span>درجة التشبع</span><strong>متوسط</strong><small>محاكاة لا تستند إلى تعداد منشآت حقيقي.</small></div>
          <div className="cockpit-kpi cockpit-kpi--amber"><span>ضغط المنافسة</span><strong>قابل للاختبار</strong><small>قارن السعر والعرض والوصول ميدانياً.</small></div>
          <div className="cockpit-kpi cockpit-kpi--blue"><span>إمكان تحسين النموذج</span><strong>محتمل</strong><small>يحتاج ربطاً بين نتيجة الدراسة ودليل السوق.</small></div>
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
        <div className="widget-heading"><div><Bot size={20} /><div><span>اقتراحات الذكاء الاصطناعي</span><strong>مسودة تجريبية محكومة</strong></div></div><small>ليست توصية نهائية</small></div>
        <div className="ai-advisory-demo__list">
          <div><Lightbulb size={17} /><div><strong>تحسين الفكرة</strong><small>ابدأ بنطاق خدمة أو شريحة أو موقع أصغر قبل الالتزام بكامل رأس المال.</small></div></div>
          <div><Route size={17} /><div><strong>بديل محتمل</strong><small>اختبر نموذجاً مجاوراً أقل كثافة في الأصول إذا كان الاسترداد أو المنافسة غير مناسبين.</small></div></div>
          <div><ClipboardList size={17} /><div><strong>ما الذي يغيّر الحكم؟</strong><small>عرضا سعر موثقان، زيارة موقع، ومقارنة ثلاثة بدائل قبل تثبيت الفرضيات.</small></div></div>
        </div>
        <p>هذه العبارات قالب تطوير واضح المصدر. لا يولد الذكاء في هذه المرحلة رقماً أو حكماً سيادياً أو قراراً نيابة عن المستخدم.</p>
        <DemoTag compact />
      </article>

      <article className="vision-alignment-demo">
        <div className="widget-heading"><div><BadgeCheck size={20} /><div><span>التوافق الاستراتيجي</span><strong>رؤية 2030 واتجاهات السوق</strong></div></div><small>إطار تجريبي</small></div>
        <div className="vision-alignment-demo__grid">
          <div><span>تصنيف المشروع</span><strong>خدمي / تشغيلي</strong><small>تصنيف مؤقت يجب ضبطه بقاعدة قطاعية.</small></div>
          <div><span>ملاءمة رؤية 2030</span><strong>قيد القياس</strong><small>لا توجد درجة حقيقية قبل ربط الأهداف والبيانات الرسمية.</small></div>
          <div><span>اتجاه السوق</span><strong>فرضية قابلة للفحص</strong><small>لا تمثل توصية دولية أو مؤشراً وطنياً فعلياً.</small></div>
        </div>
        <DemoTag compact />
      </article>

      <article className="guidance-widget guidance-widget--r3">
        <div className="widget-heading"><div><Users size={20} /><div><span>ما بعد القرار</span><strong>استعداد البداية والتشغيل</strong></div></div><small>قائمة تجريبية</small></div>
        <ol><li><span>01</span><div><strong>التراخيص والجهات</strong><small>ستظهر بحسب القطاع والمدينة بعد ربط قواعد الجهات الرسمية.</small></div></li><li><span>02</span><div><strong>المستندات</strong><small>سجل تجاري، عنوان، تراخيص قطاعية، وعقود حسب نوع المشروع — محاكاة فقط الآن.</small></div></li><li><span>03</span><div><strong>فريق البداية</strong><small>اقتراح العمالة سيُبنى من نموذج التشغيل والطاقة، لا من رقم ثابت عام.</small></div></li></ol>
        <DemoTag compact />
      </article>
    </div>

    {onContinue ? <div className="cockpit-continue"><div><strong>أكملت قراءة محاكاة السوق</strong><span>انتقل الآن إلى حزمة القرار، ثم إلى خارطة البدء.</span></div><button className="primary-button" type="button" onClick={onContinue}>انتقل إلى القرار <ArrowLeft size={17} /></button></div> : null}
  </section>;
}
