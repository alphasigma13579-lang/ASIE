import {
  ArrowUpLeft,
  Building2,
  ChevronLeft,
  CircleDollarSign,
  Compass,
  Eye,
  EyeOff,
  Landmark,
  MapPinned,
  Route,
  SlidersHorizontal,
  Sparkles,
  Store,
  Target,
  Telescope,
} from "lucide-react";
import { useMemo, useState } from "react";

type DemoMeta = {
  assumedSource: string;
  observedAt: string;
  confidence: "تجريبي";
};

type DemoCompetitor = {
  id: string;
  name: string;
  sector: string;
  area: string;
  x: number;
  y: number;
  signal: string;
  strength: string;
  meta: DemoMeta;
};

type BenchmarkCase = {
  id: string;
  title: string;
  sector: string;
  geography: string;
  status: string;
  observation: string;
  lesson: string;
  meta: DemoMeta;
};

type MacroSignal = {
  id: string;
  title: string;
  scope: string;
  direction: string;
  implication: string;
  caveat: string;
  meta: DemoMeta;
};

const localMeta = (assumedSource: string): DemoMeta => ({
  assumedSource,
  observedAt: "2026-07-20 (local seed)",
  confidence: "تجريبي",
});

const demoCompetitors: DemoCompetitor[] = [
  { id: "demo-1", name: "نقطة قهوة", sector: "مقاهي", area: "وسط المدينة", x: 31, y: 37, signal: "إقبال صباحي مرتفع", strength: "متوسط", meta: localMeta("مسح منافسين افتراضي") },
  { id: "demo-2", name: "ركن البن", sector: "مقاهي", area: "الواجهة", x: 61, y: 28, signal: "قريب من مكاتب", strength: "مرتفع", meta: localMeta("مسح منافسين افتراضي") },
  { id: "demo-3", name: "مذاق الحي", sector: "مطاعم", area: "وسط المدينة", x: 49, y: 58, signal: "خدمة توصيل نشطة", strength: "متوسط", meta: localMeta("مسح منافسين افتراضي") },
  { id: "demo-4", name: "سلة يومية", sector: "تجزئة", area: "الواجهة", x: 73, y: 64, signal: "مواقف متاحة", strength: "منخفض", meta: localMeta("مسح منافسين افتراضي") },
  { id: "demo-5", name: "مقهى الحديقة", sector: "مقاهي", area: "الحديقة", x: 23, y: 70, signal: "وجهة عائلية", strength: "منخفض", meta: localMeta("مسح منافسين افتراضي") },
];

const benchmarkCases: BenchmarkCase[] = [
  { id: "benchmark-local", title: "مقهى خدمة سريعة", sector: "مقاهي", geography: "محلي", status: "نمو منضبط", observation: "بدأ بنطاق محدود ثم اختبر ساعات الذروة قبل التوسع.", lesson: "اختبر حركة الموقع والعرض اليومي بدليل ميداني قبل تثبيت الفرضية.", meta: localMeta("ملف حالة محلي مصطنع") },
  { id: "benchmark-regional", title: "علامة طعام قريبة", sector: "مطاعم", geography: "إقليمي", status: "تعثر تشغيلي", observation: "توسع أسرع من جاهزية فريقه ومسار التوريد.", lesson: "افصل بين صلاحية الطلب وجاهزية التنفيذ؛ كلاهما يحتاج دليلاً مستقلاً.", meta: localMeta("ملف حالة إقليمي مصطنع") },
  { id: "benchmark-global", title: "متجر حي متخصص", sector: "تجزئة", geography: "عالمي", status: "ملاءمة موقع قوية", observation: "ربط العرض بسلوك الحي لا بمساحة المتجر فقط.", lesson: "قارن نمط المنطقة وسبب الزيارة، لا أسماء المنافسين وحدها.", meta: localMeta("ملف حالة عالمي مصطنع") },
];

const macroSignals: MacroSignal[] = [
  { id: "macro-local", title: "حركة المناطق المكتبية", scope: "محلي", direction: "إشارة تحتاج تحققاً", implication: "قد تدعم تجربة صباحية قصيرة إذا أثبتها الرصد الميداني.", caveat: "ليست قراءة لحظية أو مصدر حكومي؛ مجرد سيناريو عرض.", meta: localMeta("مؤشر حركة محلي مصطنع") },
  { id: "macro-regional", title: "تفضيل الطلب المريح", scope: "إقليمي", direction: "سياق قابل للمقارنة", implication: "اختبر أثر الطلب المسبق والتوصيل في نموذج الخدمة.", caveat: "لا يمثل سوقاً فعلياً أو توقعات مالية.", meta: localMeta("مذكرة سياق إقليمي مصطنعة") },
  { id: "macro-global", title: "التركيز على كفاءة التشغيل", scope: "عالمي", direction: "فرضية متابعة", implication: "حوّلها إلى سؤال دليل: ما الذي يحمي الجودة عند الذروة؟", caveat: "ليس توصية أو تنبؤاً خارجياً.", meta: localMeta("موجز سوق عالمي مصطنع") },
];

const sectors = ["مقاهي", "مطاعم", "تجزئة"];

function DemoProvenance({ meta, compact = false }: { meta: DemoMeta; compact?: boolean }) {
  return <div className={compact ? "demo-provenance demo-provenance--compact" : "demo-provenance"}>
    <span>DEMO / LOCAL ONLY</span>
    {!compact ? <small>مصدر مفترض: {meta.assumedSource} · {meta.observedAt} · الثقة: {meta.confidence}</small> : null}
  </div>;
}

export function LiveCockpit() {
  const [sector, setSector] = useState("مقاهي");
  const [selectedId, setSelectedId] = useState("demo-1");
  const [selectedBenchmarkId, setSelectedBenchmarkId] = useState("benchmark-local");
  const [selectedMacroId, setSelectedMacroId] = useState("macro-local");
  const [visibleWidgets, setVisibleWidgets] = useState({ signals: true, benchmark: true, macro: true, guidance: true });

  const visibleCompetitors = useMemo(() => demoCompetitors.filter((competitor) => competitor.sector === sector), [sector]);
  const selectedCompetitor = visibleCompetitors.find((competitor) => competitor.id === selectedId) ?? visibleCompetitors[0];
  const sectorBenchmark = benchmarkCases.find((item) => item.sector === sector) ?? benchmarkCases[0];
  const selectedBenchmark = benchmarkCases.find((item) => item.id === selectedBenchmarkId) ?? sectorBenchmark;
  const selectedMacro = macroSignals.find((item) => item.id === selectedMacroId) ?? macroSignals[0];
  const toggleWidget = (widget: keyof typeof visibleWidgets) => setVisibleWidgets((current) => ({ ...current, [widget]: !current[widget] }));

  return <section className="live-cockpit live-cockpit--r2" aria-label="مرصد محلي لاختبار واقع المشروع">
    <header className="cockpit-intro">
      <div>
        <p className="eyebrow"><Sparkles size={15} /> محاكاة السوق والسياق</p>
        <h2>هل فرضية مشروعك قريبة من الواقع؟</h2>
        <p>غرفة استكشاف محلية قبل القرار: السوق، نماذج مشابهة، وسياق عمل محتمل. لا توجد بيانات خارجية أو توصية تلقائية في هذه الصفحة.</p>
      </div>
      <span className="demo-badge">DEMO · LOCAL ONLY</span>
    </header>

    <section className="smart-input-hub" aria-label="سياق العرض المحلي">
      <div className="smart-input-hub__title"><SlidersHorizontal size={20} /><div><strong>سياق مشروعك</strong><span>تغيّر الفلاتر ما تراه فقط، ولا تحفظ أو تحسب قراراً.</span></div></div>
      <label>القطاع<select value={sector} onChange={(event) => { const nextSector = event.target.value; setSector(nextSector); setSelectedId(demoCompetitors.find((item) => item.sector === nextSector)?.id ?? ""); setSelectedBenchmarkId(benchmarkCases.find((item) => item.sector === nextSector)?.id ?? "benchmark-local"); }}>{sectors.map((item) => <option key={item}>{item}</option>)}</select></label>
      <label>النطاق<select defaultValue="وسط المدينة"><option>وسط المدينة</option><option>الواجهة</option><option>الحديقة</option></select></label>
      <label>سؤال الاستكشاف<select defaultValue="اختيار موقع"><option>اختيار موقع</option><option>فهم المنافسين</option><option>استكمال الدليل</option></select></label>
      <button className="cockpit-location-button" type="button"><Compass size={17} /> موقع تجريبي</button>
    </section>

    <div className="cockpit-toolbar" aria-label="إدارة وحدات العرض">
      <span>وحدات العمل المستقلة</span>
      <button type="button" onClick={() => toggleWidget("signals")}>{visibleWidgets.signals ? <EyeOff size={15} /> : <Eye size={15} />}{visibleWidgets.signals ? "إخفاء الإشارات" : "إظهار الإشارات"}</button>
      <button type="button" onClick={() => toggleWidget("benchmark")}>{visibleWidgets.benchmark ? <EyeOff size={15} /> : <Eye size={15} />}{visibleWidgets.benchmark ? "إخفاء المقارنات" : "إظهار المقارنات"}</button>
      <button type="button" onClick={() => toggleWidget("macro")}>{visibleWidgets.macro ? <EyeOff size={15} /> : <Eye size={15} />}{visibleWidgets.macro ? "إخفاء السياق" : "إظهار السياق"}</button>
      <button type="button" onClick={() => toggleWidget("guidance")}>{visibleWidgets.guidance ? <EyeOff size={15} /> : <Eye size={15} />}{visibleWidgets.guidance ? "إخفاء الخطوات" : "إظهار الخطوات"}</button>
    </div>

    <div className="cockpit-grid cockpit-grid--r2">
      <article className="market-map-widget">
        <div className="widget-heading"><div><MapPinned size={20} /><div><span>خريطة السوق</span><strong>المنافسون والموقع المرشح</strong></div></div><small>{visibleCompetitors.length} إشارات محلية</small></div>
        <div className="local-map" role="application" aria-label="خريطة سوق محلية تجريبية قابلة لاختيار المنافسين">
          <span className="map-road map-road--one" /><span className="map-road map-road--two" /><span className="map-zone map-zone--one">منطقة أعمال</span><span className="map-zone map-zone--two">واجهة نشطة</span>
          {visibleCompetitors.map((competitor) => <button key={competitor.id} type="button" className={competitor.id === selectedCompetitor?.id ? "map-marker map-marker--active" : "map-marker"} style={{ left: `${competitor.x}%`, top: `${competitor.y}%` }} onClick={() => setSelectedId(competitor.id)} aria-label={`عرض ${competitor.name}`}><Store size={14} /></button>)}
          <div className="site-marker" style={{ left: "52%", top: "41%" }}><Target size={15} /><span>موقع مرشح</span></div>
        </div>
        {selectedCompetitor ? <div className="map-insight"><Building2 size={18} /><div><strong>{selectedCompetitor.name}</strong><span>{selectedCompetitor.area} · ضغط منافسة {selectedCompetitor.strength}</span><small>{selectedCompetitor.signal}</small></div><ChevronLeft size={18} /></div> : null}
        <DemoProvenance meta={selectedCompetitor?.meta ?? localMeta("مسح افتراضي")} />
      </article>

      {visibleWidgets.signals ? <article className="cockpit-kpis-widget">
        <div className="widget-heading"><div><CircleDollarSign size={20} /><div><span>إشارات للمراجعة</span><strong>ليست مؤشرات أداء حقيقية</strong></div></div><small>3 فرضيات</small></div>
        <div className="cockpit-kpis">
          <button type="button" className="cockpit-kpi cockpit-kpi--mint"><span>فرضية الطلب</span><strong>تحتاج رصداً</strong><small>راقب ساعات الذروة والحركة ميدانياً.</small></button>
          <button type="button" className="cockpit-kpi cockpit-kpi--amber"><span>ضغط المنافسة</span><strong>{selectedCompetitor?.strength ?? "غير محدد"}</strong><small>استكشف العرض والسعر والخدمة، لا تتخذ قراراً من الخريطة.</small></button>
          <button type="button" className="cockpit-kpi cockpit-kpi--blue"><span>فجوة الدليل</span><strong>زيارة موقع</strong><small>أضف المواقف والوصول والإيجار كدليل منفصل.</small></button>
        </div>
        <DemoProvenance meta={localMeta("إشارات عرض محلية مصطنعة")} />
      </article> : null}

      {visibleWidgets.benchmark ? <article className="benchmark-widget">
        <div className="widget-heading"><div><Telescope size={20} /><div><span>أين أنت من الواقع؟</span><strong>نماذج مشابهة للمقارنة</strong></div></div><small>ملفات حالة محلية</small></div>
        <div className="benchmark-tabs" role="tablist" aria-label="نماذج المقارنة">
          {benchmarkCases.map((item) => <button type="button" key={item.id} role="tab" aria-selected={item.id === selectedBenchmark?.id} className={item.id === selectedBenchmark?.id ? "benchmark-tab benchmark-tab--active" : "benchmark-tab"} onClick={() => setSelectedBenchmarkId(item.id)}>{item.geography}</button>)}
        </div>
        {selectedBenchmark ? <div className="benchmark-detail"><span>{selectedBenchmark.status}</span><strong>{selectedBenchmark.title}</strong><p>{selectedBenchmark.observation}</p><div><ArrowUpLeft size={15} /><small>{selectedBenchmark.lesson}</small></div><DemoProvenance meta={selectedBenchmark.meta} /></div> : null}
      </article> : null}

      {visibleWidgets.macro ? <article className="macro-widget">
        <div className="widget-heading"><div><Landmark size={20} /><div><span>السياق الأكبر</span><strong>إشارات خارج حدود الموقع</strong></div></div><small>محاكاة محلية</small></div>
        <div className="macro-list">{macroSignals.map((item) => <button type="button" key={item.id} className={item.id === selectedMacro?.id ? "macro-row macro-row--active" : "macro-row"} onClick={() => setSelectedMacroId(item.id)}><span>{item.scope}</span><strong>{item.title}</strong><small>{item.direction}</small></button>)}</div>
        {selectedMacro ? <div className="macro-detail"><strong>{selectedMacro.implication}</strong><small>{selectedMacro.caveat}</small><DemoProvenance meta={selectedMacro.meta} /></div> : null}
      </article> : null}

      {visibleWidgets.guidance ? <article className="guidance-widget guidance-widget--r2">
        <div className="widget-heading"><div><Route size={20} /><div><span>خطوة التحقق التالية</span><strong>حوّل الإشارة إلى دليل</strong></div></div><small>لا قرار تلقائي</small></div>
        <ol><li><span>01</span><div><strong>زر الموقع في وقتين مختلفين</strong><small>دوّن الحركة والوصول والمواقف كما تراها، لا كما تفترضها الخريطة.</small></div></li><li><span>02</span><div><strong>قارن عرض ثلاثة منافسين</strong><small>أضف السعر والخدمة والفئة المستهدفة في صفحة الأدلة.</small></div></li><li><span>03</span><div><strong>اربط ما يثبت الفرضية</strong><small>تنتقل الأدلة للمراجعة الخلفية؛ هذه الصفحة لا تغيّر Snapshot.</small></div></li></ol>
        <DemoProvenance meta={localMeta("قائمة إرشاد محلية مصطنعة")} />
      </article> : null}
    </div>
  </section>;
}
