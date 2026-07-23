import {
  Activity,
  AlertTriangle,
  ArrowLeft,
  BarChart3,
  BadgeCheck,
  Calculator,
  CheckCircle2,
  Database,
  FileText,
  FileUp,
  LayoutDashboard,
  KeyRound,
  Layers3,
  MapPin,
  Play,
  RefreshCw,
  Rocket,
  ScrollText,
  ShieldCheck,
  Sparkles,
  Target,
  Users,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState, type CSSProperties } from "react";
import { LiveCockpit } from "./LiveCockpit";
import { BrandLockup } from "./BrandMark";
import {
  createEvidenceLink,
  createDatasetTransformation,
  createProjectAssumption,
  createProject,
  createSnapshotReview,
  compareSnapshots,
  fetchArchitectureRuntimeStatus,
  fetchDatasets,
  fileImportDataset,
  fetchDecisionPack,
  fetchProjectEvidenceLedger,
  fetchProjectActionItems,
  fetchProjectAssumptions,
  fetchProjectEvidenceRegister,
  fetchProjectReadiness,
  fetchProjectWorkspace,
  fetchProjects,
  fetchSectorTaxonomy,
  fetchSnapshotReport,
  fetchSnapshotReportView,
  fetchSourcePolicy,
  fetchSourceWorkbench,
  manualImportDataset,
  reviewDataset,
  runProject,
  updateProjectActionItem,
  updateProject,
} from "./api";
import type {
  ActionItem,
  AssumptionRecord,
  ArchitectureRuntimeStatus,
  DatasetRecord,
  EvidenceCoverageMatrix,
  EvidenceLedgerRecord,
  DecisionPack,
  EvidenceRegister,
  OutputEnvelope,
  Project,
  ProjectInputs,
  ProjectReadiness,
  ProjectWorkspace,
  ProjectOverview,
  ReviewDecision,
  SectorTaxonomyRecord,
  SnapshotReport,
  SnapshotReportView,
  SnapshotComparison,
  SourcePolicy,
  SourceReviewChecklist,
  SourceReviewRecord,
  TransformationLineageRecord,
  TransformationRecord,
} from "./contracts";

const workflow = [
  "إنشاء مشروع",
  "مدخلات أساسية",
  "اختيار العمق",
  "تشغيل التقييم",
  "مراجعة الحكم",
  "تقرير اللقطة",
];

type AppStage = "dashboard" | "wizard" | "evidence" | "readiness" | "run" | "reality" | "decision" | "execution" | "architecture" | "snapshots";

const appStages: Array<{ id: AppStage; label: string; description: string }> = [
  { id: "dashboard", label: "الملخص", description: "أين وصلنا الآن؟" },
  { id: "wizard", label: "عرّف مشروعك", description: "الفكرة والموقع والأرقام" },
  { id: "evidence", label: "اربط الأدلة", description: "ملفاتك ومصادر الثقة" },
  { id: "readiness", label: "افحص النواقص", description: "ما يمنع التحليل؟" },
  { id: "run", label: "شغّل التحليل", description: "أنشئ مرجع القرار" },
  { id: "reality", label: "ذكاء السوق والفرص", description: "مقارنات وتوصيات بعد الدراسة" },
  { id: "decision", label: "افهم القرار", description: "الحكم وسببه" },
  { id: "execution", label: "نفّذ التالي", description: "خطوات بعد القرار" },
  { id: "snapshots", label: "التقارير", description: "المخرجات المحفوظة" },
];

const appStageGroups: Array<{ label: string; stages: AppStage[] }> = [
  { label: "مسار الدراسة", stages: ["dashboard", "wizard"] },
  { label: "التحقق قبل التشغيل", stages: ["evidence", "readiness"] },
  { label: "القرار والتنفيذ", stages: ["run", "reality", "decision", "execution", "snapshots"] },
];

const PRODUCT_ENTRY_STORAGE_KEY = "asie.product_entry.v1";
const LEGAL_ACCEPTANCE_STORAGE_KEY = "asie.legal_acceptance.v1";

function readLocalFlag(key: string): boolean {
  try {
    return window.localStorage.getItem(key) === "1";
  } catch {
    return false;
  }
}

function writeLocalFlag(key: string, value: boolean) {
  try {
    if (value) window.localStorage.setItem(key, "1");
    else window.localStorage.removeItem(key);
  } catch {
    // Private browsing policies can deny storage; in-memory state still works.
  }
}

function stageFromLocation(): AppStage {
  const rawStage = window.location.hash.replace(/^#/, "") as AppStage;
  return appStages.some((item) => item.id === rawStage) ? rawStage : "dashboard";
}

const wizardJourney = [
  { label: "موقع العميل", icon: MapPin },
  { label: "القطاع", icon: Layers3 },
  { label: "التصنيف الدقيق", icon: Target },
  { label: "اسم المشروع", icon: Rocket },
  { label: "الفجوة والميزة", icon: AlertTriangle },
  { label: "الجمهور", icon: Users },
  { label: "رأس المال", icon: Calculator },
  { label: "طريقة التفاصيل", icon: Database },
];

const firstMinuteJourney: Array<{ stage: AppStage; title: string; body: string }> = [
  { stage: "wizard", title: "عرّف المشروع", body: "اكتب الفكرة والموقع وأهم الأرقام فقط." },
  { stage: "evidence", title: "اربط ما يثبتها", body: "أضف ملفاً أو دليلاً محلياً يدعم الافتراضات." },
  { stage: "run", title: "شغّل التحليل", body: "تتحقق المنصة من النواقص قبل إنشاء مرجع القرار." },
  { stage: "reality", title: "ذكاء السوق والفرص", body: "قارن المشروع بالسوق بعد ظهور نتيجة الدراسة." },
  { stage: "decision", title: "افهم القرار", body: "اقرأ الحكم، السبب، المخاطر، والخطوة القادمة." },
];

const wizardStepHelp = [
  "ابدأ بالمكان. الموقع هو أول عدسة لفهم السوق والمنافسين والتكاليف.",
  "اختر المجال الكبير للمشروع: صحة، تعليم، تجارة، تقنية، أو غيره.",
  "اختر النوع الدقيق داخل القطاع حتى لا تكون الدراسة عامة.",
  "سمّ المشروع بلغة بسيطة. الاسم يساعدك لاحقاً في قراءة التقرير.",
  "قل لنا لماذا يحتاج السوق هذا المشروع، وما الذي يجعله مختلفاً.",
  "حدد من سيدفع أو يستفيد: أفراد، مؤسسات، شركات، أو مزيج.",
  "ابدأ برأس المال المتاح. لا تحتاج كل التفاصيل من أول دقيقة.",
  "اختر كيف تريد تعبئة باقي الأرقام: بنفسك، من ملف، أو بمساعدة تقديرية عند تفعيلها.",
];

const arabicSubsectorLabels: Record<string, string> = {
  "Heavy Manufacturing": "الصناعات الثقيلة",
  "Light Manufacturing": "الصناعات الخفيفة",
  "Food Manufacturing": "الصناعات الغذائية",
  Pharmaceuticals: "الصناعات الدوائية",
  "Real Estate Development": "التطوير العقاري",
  "Commercial Real Estate": "العقارات التجارية",
  "Residential Real Estate": "العقارات السكنية",
  "Industrial Real Estate": "العقارات الصناعية",
  "Land Transport": "النقل البري",
  Warehousing: "المستودعات والتخزين",
  "E-commerce Logistics": "خدمات توصيل التجارة الإلكترونية",
  "Ports & Airports": "الموانئ والمطارات",
  "Leisure Tourism": "السياحة الترفيهية",
  "Hotels & Hospitality": "الفنادق والضيافة",
  "Events & Festivals": "الفعاليات والمهرجانات",
  "Cinema & Production": "السينما والإنتاج",
  AI: "الذكاء الاصطناعي",
  "Cloud Computing": "الحوسبة السحابية",
  Cybersecurity: "الأمن السيبراني",
  Software: "البرمجيات",
  "Data Centers": "مراكز البيانات",
  Banks: "البنوك",
  Insurance: "التأمين",
  Financing: "التمويل",
  "Capital Markets": "أسواق المال",
  Investment: "الاستثمار",
  Hospitals: "المستشفيات",
  Clinics: "العيادات",
  HealthTech: "التقنيات الصحية",
  "Medical Devices": "الأجهزة الطبية",
  Agriculture: "الزراعة",
  "Food Security": "الأمن الغذائي",
  AgriTech: "التقنيات الزراعية",
  Livestock: "الثروة الحيوانية",
  "Food Supply Chains": "سلاسل إمداد الغذاء",
};

function arabicSubsectorLabel(value: string): string {
  return arabicSubsectorLabels[value] ?? value;
}

const saudiCitiesByRegion: Record<string, string[]> = {
  "منطقة الرياض": ["الرياض", "الخرج", "الدرعية", "الدوادمي", "المجمعة", "شقراء", "الزلفي", "وادي الدواسر", "عفيف"],
  "منطقة مكة المكرمة": ["مكة المكرمة", "جدة", "الطائف", "رابغ", "القنفذة", "الليث", "خليص"],
  "منطقة المدينة المنورة": ["المدينة المنورة", "ينبع", "العلا", "بدر", "مهد الذهب"],
  "منطقة القصيم": ["بريدة", "عنيزة", "الرس", "البكيرية", "المذنب"],
  "المنطقة الشرقية": ["الدمام", "الخبر", "الظهران", "الأحساء", "الجبيل", "القطيف", "حفر الباطن", "رأس تنورة"],
  "منطقة عسير": ["أبها", "خميس مشيط", "بيشة", "محايل عسير", "النماص"],
  "منطقة تبوك": ["تبوك", "ضباء", "الوجه", "أملج", "حقل"],
  "منطقة حائل": ["حائل", "بقعاء"],
  "منطقة الحدود الشمالية": ["عرعر", "رفحاء", "طريف"],
  "منطقة جازان": ["جازان", "صبيا", "أبو عريش", "صامطة", "بيش"],
  "منطقة نجران": ["نجران", "شرورة"],
  "منطقة الباحة": ["الباحة", "بلجرشي", "المندق", "المخواة"],
  "منطقة الجوف": ["سكاكا", "دومة الجندل", "القريات", "طبرجل"],
};

function governedNameError(value: string, label: string, minimumLength = 3, maximumLength = 60): string | null {
  const normalized = value.trim().replace(/\s+/g, " ");
  if (normalized.length < minimumLength) return `${label} قصير جدًا.`;
  if (normalized.length > maximumLength) return `${label} طويل جدًا؛ الحد الأقصى ${maximumLength} حرفًا.`;
  if (!/^[\p{L}\p{N}][\p{L}\p{N}\s'’\-ـ]*$/u.test(normalized)) {
    return `${label} يجب أن يحتوي على حروف وأرقام ومسافات فقط.`;
  }
  if (/(.)\1{2,}/u.test(normalized) || /^(.{1,4})\1{2,}$/u.test(normalized)) {
    return `${label} يحتوي على تكرار غير مقبول للحروف أو المقاطع.`;
  }
  const distinctLetters = new Set((normalized.match(/\p{L}/gu) ?? []).map((letter) => letter.toLocaleLowerCase("ar-SA")));
  if (distinctLetters.size < 2) return `${label} غير واضح؛ اكتب اسمًا حقيقيًا ومفهومًا.`;
  return null;
}

const assumptionArabicLabels: Record<string, string> = {
  primary_sector_id: "القطاع",
  subsector_id: "النشاط التفصيلي",
  activity_description: "وصف النشاط",
  location_scope: "نطاق السوق",
  location_country: "الدولة",
  location_region: "المنطقة",
  location_city: "المدينة",
  location_district: "الحي أو الشارع",
  location_latitude: "خط العرض",
  location_longitude: "خط الطول",
  gap_statement: "حاجة السوق",
  competitive_edge: "الميزة التنافسية",
  target_audience: "الجمهور المستهدف",
  intake_mode: "طريقة إدخال التفاصيل",
  capital_available: "رأس المال المتاح",
  startup_cost: "تكلفة التأسيس",
  monthly_fixed_cost: "المصاريف الشهرية الثابتة",
  other_monthly_costs: "بنود شهرية أخرى",
  unit_price: "سعر البيع أو الخدمة",
  variable_cost: "تكلفة تقديم الخدمة",
  monthly_units: "العملاء أو الطلبات شهريًا",
  use_operating_capacity: "استخدام الطاقة التشغيلية",
  capacity_units_per_day: "الطاقة التشغيلية اليومية",
  operating_days_per_month: "أيام التشغيل شهريًا",
  utilization_rate: "نسبة الاستفادة من الطاقة",
  payroll_monthly: "الرواتب الشهرية",
  rent_monthly: "الإيجار الشهري",
  utilities_monthly: "المرافق الشهرية",
  marketing_monthly: "التسويق الشهري",
  maintenance_monthly: "الصيانة الشهرية",
  capex_equipment: "تكلفة المعدات",
  capex_fitout: "تكلفة التجهيز",
  capex_licenses_local: "تكلفة التراخيص",
  depreciation_years: "سنوات الإهلاك",
  equity_contribution: "المساهمة الذاتية",
  loan_grace_months: "فترة السماح",
  annual_discount_rate: "معدل الخصم السنوي",
  working_capital_months: "أشهر رأس المال العامل",
  debt_amount: "مبلغ القرض",
  annual_interest_rate: "تكلفة التمويل السنوية",
  loan_years: "مدة القرض",
};

const assumptionReviewGroups = [
  { id: "identity", label: "هوية المشروع وموقعه", keys: ["primary_sector_id", "subsector_id", "activity_description", "location_scope", "location_country", "location_region", "location_city", "location_district", "location_latitude", "location_longitude"] },
  { id: "market", label: "السوق والميزة والجمهور", keys: ["gap_statement", "competitive_edge", "target_audience", "intake_mode"] },
  { id: "operations", label: "التشغيل والطاقة", keys: ["monthly_units", "use_operating_capacity", "capacity_units_per_day", "operating_days_per_month", "utilization_rate"] },
  { id: "finance", label: "التكاليف والإيرادات", keys: ["capital_available", "startup_cost", "monthly_fixed_cost", "unit_price", "variable_cost", "payroll_monthly", "rent_monthly", "utilities_monthly", "marketing_monthly", "maintenance_monthly", "capex_equipment", "capex_fitout", "capex_licenses_local", "depreciation_years", "equity_contribution"] },
  { id: "funding", label: "التمويل والخصم", keys: ["loan_grace_months", "annual_discount_rate", "working_capital_months", "debt_amount", "annual_interest_rate", "loan_years"] },
];

function assumptionArabicLabel(item: AssumptionRecord): string {
  return assumptionArabicLabels[item.input_key] ?? item.label;
}

function monthlyFixedCostFromInputs(inputs: ProjectInputs): number {
  const components = [
    inputs.payroll_monthly,
    inputs.rent_monthly,
    inputs.utilities_monthly,
    inputs.marketing_monthly,
    inputs.maintenance_monthly,
  ].map((value) => Number(value) || 0);
  const otherCostsTotal = (inputs.other_monthly_costs ?? []).reduce((total, item) => total + Math.max(0, Number(item.amount) || 0), 0);
  const detailedTotal = components.reduce((total, value) => total + Math.max(0, value), 0) + otherCostsTotal;
  return detailedTotal > 0 ? detailedTotal : Number(inputs.monthly_fixed_cost) || 0;
}

const defaultInputs: Required<ProjectInputs> = {
  primary_sector_id: "",
  subsector_id: "",
  activity_description: "",
  location_scope: "المملكة العربية السعودية",
  location_country: "SA",
  location_region: "",
  location_city: "",
  location_district: "",
  location_latitude: 0,
  location_longitude: 0,
  gap_statement: "",
  competitive_edge: "",
  target_audience: "",
  intake_mode: "",
  capital_available: 0,
  startup_cost: 0,
  monthly_fixed_cost: 0,
  other_monthly_costs: [],
  unit_price: 0,
  variable_cost: 0,
  monthly_units: 0,
  use_operating_capacity: false,
  capacity_units_per_day: 0,
  operating_days_per_month: 0,
  utilization_rate: 0,
  payroll_monthly: 0,
  rent_monthly: 0,
  utilities_monthly: 0,
  marketing_monthly: 0,
  maintenance_monthly: 0,
  capex_equipment: 0,
  capex_fitout: 0,
  capex_licenses_local: 0,
  depreciation_years: 0,
  equity_contribution: 0,
  loan_grace_months: 0,
  annual_discount_rate: 0,
  working_capital_months: 0,
  debt_amount: 0,
  annual_interest_rate: 0,
  loan_years: 0,
  blueprint_items: [],
};

function formatValue(output: OutputEnvelope): string {
  if (output.value === null) return "NOT_READY";
  if (typeof output.value === "string") return output.value;
  if (output.unit === "percent") return `${Math.round(output.value * 1000) / 10}%`;
  if (output.unit === "SAR") {
    return new Intl.NumberFormat("ar-SA", {
      style: "currency",
      currency: "SAR",
      maximumFractionDigits: 0,
    }).format(output.value);
  }
  return new Intl.NumberFormat("ar-SA", { maximumFractionDigits: 2 }).format(output.value);
}

function statusText(status: string): string {
  const map: Record<string, string> = {
    ready: "جاهز",
    passed: "اجتازت",
    warning: "تحذير",
    blocked: "محجوب",
    ready_with_warnings: "جاهز مع تحذيرات",
    needs_input: "يحتاج مدخلات",
    insufficient_data: "بيانات غير كافية",
    completed: "مكتمل",
    PRELIMINARY_ONLY: "تقييم أولي فقط",
    REVISE_AND_REASSESS: "راجع وأعد التقييم",
    BLOCKED_NOT_READY: "متوقف لمدخلات ناقصة",
    USER_VERIFIED: "مدخلات مستخدم",
    DEMO_DATA: "بيانات تجريبية",
    candidate: "مرشح للمراجعة",
    reference_only: "مرجعي فقط",
    approved_for_use: "معتمد للاستخدام",
    review_required: "بانتظار المراجعة",
    rejected: "مرفوض",
    unknown: "غير معروف",
    approved: "معتمد",
    draft: "مسودة",
    needs_review: "يحتاج مراجعة",
    pending: "قيد الانتظار",
    enabled: "مفعّل",
    disabled: "غير مفعّل",
    manual_csv: "إدخال CSV",
    manual_table: "إدخال يدوي",
    aggregate_average: "حساب المتوسط",
    aggregate_sum: "حساب المجموع",
    select_column: "اختيار عمود",
    manual_derivation_note: "ملاحظة اشتقاق",
  };
  return map[status] ?? status;
}

function metricTitle(id: string): string {
  const titles: Record<string, string> = {
    "startup-cost": "تكلفة التأسيس",
    "monthly-revenue": "الإيراد الشهري",
    "monthly-profit": "صافي شهري تقديري",
    "break-even-units": "وحدات التعادل",
    "funding-gap": "فجوة التمويل",
    "working-capital-need": "احتياج رأس المال العامل",
    ebitda: "EBITDA",
    ebit: "EBIT",
    "net-operating-cashflow": "التدفق التشغيلي الصافي",
    "funding-need-after-equity": "احتياج التمويل بعد رأس المال",
    "depreciation-monthly": "الإهلاك الشهري",
    dscr: "DSCR",
    npv: "صافي القيمة الحالية",
    irr: "معدل العائد الداخلي",
    "payback-months": "مدة الاسترداد",
    "contribution-margin": "هامش المساهمة",
    "debt-service-monthly": "خدمة الدين الشهرية",
    "mc-feasibility-gate-probability": "احتمال اجتياز بوابات الجدوى",
  };
  return titles[id] ?? id;
}

function MetricCard({ output }: { output: OutputEnvelope }) {
  return (
    <article className="metric-card">
      <div className="metric-card__top">
        <span className="metric-card__owner">{output.owner_module}</span>
        <BadgeCheck size={18} aria-hidden="true" />
      </div>
      <strong>{metricTitle(output.output_id)}</strong>
      <div className="metric-card__value">{formatValue(output)}</div>
      <dl className="lineage-list">
        <div>
          <dt>العقد</dt>
          <dd>{output.contract_id}</dd>
        </div>
        <div>
          <dt>الخوارزمية</dt>
          <dd>{output.algorithm_id}</dd>
        </div>
        <div>
          <dt>الحالة</dt>
          <dd>{statusText(output.status)}</dd>
        </div>
      </dl>
    </article>
  );
}

function SnapshotAnalytics({ overview }: { overview: ProjectOverview | null }) {
  const baseline = overview?.finance.baseline;
  const bars = baseline
    ? [
        ["الإيراد الشهري", baseline.revenue, "#168259"],
        ["التكاليف المتغيرة", baseline.variable_total, "#e29b45"],
        ["المصاريف التشغيلية", baseline.opex_breakdown.total_monthly_opex, "#7f8da3"],
        ["الربح الشهري", baseline.monthly_profit, baseline.monthly_profit >= 0 ? "#7ccf75" : "#d66a6a"],
      ] as Array<[string, number, string]>
    : [];
  const max = Math.max(...bars.map(([, value]) => Math.abs(value)), 1);
  const probability = overview?.monte_carlo.p_pass;
  return (
    <div className="dashboard-analytics-grid">
      <article className="panel analytics-panel analytics-panel--financial">
        <div className="section-title"><BarChart3 size={20} aria-hidden="true" /><h2>صورة الأداء المالي</h2><small>{baseline ? "من Finance Snapshot · شهري" : "تظهر بعد Snapshot"}</small></div>
        {bars.length ? (
          <div className="comparison-chart" role="img" aria-label="مقارنة الإيرادات والتكاليف والربح الشهري">
            {bars.map(([label, value, color]) => <div className="comparison-chart__row" key={label}><span>{label}</span><div className="comparison-chart__track"><i style={{ width: `${Math.max(3, Math.min(100, Math.abs(value) / max * 100))}%`, background: color }} /></div><strong>{new Intl.NumberFormat("ar-SA", { maximumFractionDigits: 0 }).format(value)} ر.س</strong></div>)}
          </div>
        ) : <p className="empty-state">لا توجد أرقام عرضية قبل إنشاء Snapshot. ستظهر المقارنة من مخرجات Finance المحفوظة فقط.</p>}
        <small className="chart-caption">المقارنة بين بنود متجانسة زمنياً؛ لا تعيد الواجهة الحساب.</small>
      </article>
      <article className="panel analytics-panel analytics-panel--decision">
        <div className="section-title"><Target size={20} aria-hidden="true" /><h2>قوة القرار</h2><small>{overview ? "Monte Carlo من Snapshot" : "غير متاح قبل التشغيل"}</small></div>
        {probability !== undefined && probability !== null ? (
          <div className="decision-gauge" role="img" aria-label={`احتمال اجتياز البوابات ${Math.round(probability * 100)} بالمئة`}>
            <div className="decision-gauge__ring" style={{ "--gauge": `${Math.round(probability * 100)}%` } as CSSProperties}><strong>{Math.round(probability * 100)}%</strong><span>احتمال الاجتياز</span></div>
            <div className="decision-gauge__meta"><span>التشغيلات</span><strong>{overview!.monte_carlo.iterations.toLocaleString("ar-SA")}</strong><small>{statusText(overview!.decision.sovereign_verdict)}</small></div>
          </div>
        ) : <p className="empty-state">ستظهر قوة القرار واحتمال الاجتياز بعد تشغيل تحليل مرتبط بالمدخلات والأدلة.</p>}
      </article>
    </div>
  );
}

function normalizeNumericInput(rawValue: string): string {
  return rawValue
    .replace(/[٠-٩]/g, (digit) => String("٠١٢٣٤٥٦٧٨٩".indexOf(digit)))
    .replace(/[۰-۹]/g, (digit) => String("۰۱۲۳۴۵۶۷۸۹".indexOf(digit)))
    .replace(/[٫,،]/g, ".")
    .replace(/\s/g, "");
}

function NumberField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number;
  onChange: (nextValue: number) => void;
}) {
  const [draftValue, setDraftValue] = useState(String(Number.isFinite(value) ? value : 0));
  const [isEditing, setIsEditing] = useState(false);

  useEffect(() => {
    if (!isEditing) setDraftValue(String(Number.isFinite(value) ? value : 0));
  }, [isEditing, value]);

  function updateDraft(rawValue: string) {
    const normalized = normalizeNumericInput(rawValue);
    if (normalized !== "" && !/^\d*(?:\.\d*)?$/.test(normalized)) return;
    setDraftValue(normalized);
    if (normalized === "" || normalized === ".") return;
    const nextValue = Number(normalized);
    if (Number.isFinite(nextValue) && nextValue >= 0) onChange(nextValue);
  }

  function commitDraft() {
    setIsEditing(false);
    const normalized = normalizeNumericInput(draftValue);
    const nextValue = normalized === "" || normalized === "." ? 0 : Math.max(0, Number(normalized));
    const safeValue = Number.isFinite(nextValue) ? nextValue : 0;
    setDraftValue(String(safeValue));
    onChange(safeValue);
  }

  function stepValue(delta: number) {
    const currentValue = Number(normalizeNumericInput(draftValue)) || 0;
    const nextValue = Math.max(0, currentValue + delta);
    setDraftValue(String(nextValue));
    onChange(nextValue);
  }

  return (
    <label className="field">
      <span>{label}</span>
      <span className="number-input-control">
        <input
          type="text"
          inputMode="decimal"
          dir="ltr"
          value={draftValue}
          required
          onFocus={(event) => {
            setIsEditing(true);
            event.currentTarget.select();
          }}
          onBlur={commitDraft}
          onChange={(event) => updateDraft(event.target.value)}
          aria-label={label}
        />
        <span className="number-input-control__steppers" aria-hidden="false">
          <button type="button" tabIndex={-1} aria-label={`زيادة ${label}`} onMouseDown={(event) => event.preventDefault()} onClick={() => stepValue(1)}>▲</button>
          <button type="button" tabIndex={-1} aria-label={`إنقاص ${label}`} onMouseDown={(event) => event.preventDefault()} onClick={() => stepValue(-1)}>▼</button>
        </span>
      </span>
    </label>
  );
}

function arrayBufferToBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let binary = "";
  const chunkSize = 0x8000;
  for (let index = 0; index < bytes.length; index += chunkSize) {
    const chunk = bytes.subarray(index, index + chunkSize);
    binary += String.fromCharCode(...chunk);
  }
  return window.btoa(binary);
}

function LoadingState() {
  return (
    <main id="main-content" className="app-shell app-shell--center" aria-busy="true">
      <Activity className="spin" size={28} aria-hidden="true" />
      <p>جاري تجهيز مساحة ASIE المحلية...</p>
    </main>
  );
}

function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <main id="main-content" className="app-shell app-shell--center" role="alert">
      <AlertTriangle size={32} aria-hidden="true" />
      <h1>الخدمة المحلية غير جاهزة</h1>
      <p>{message}</p>
      <button className="primary-button" onClick={onRetry}>
        <RefreshCw size={18} aria-hidden="true" />
        إعادة المحاولة
      </button>
    </main>
  );
}

export function App() {
  const [sourcePolicy, setSourcePolicy] = useState<SourcePolicy | null>(null);
  const [sources, setSources] = useState<SourceReviewRecord[]>([]);
  const [sourceChecklists, setSourceChecklists] = useState<SourceReviewChecklist[]>([]);
  const [sectorTaxonomy, setSectorTaxonomy] = useState<SectorTaxonomyRecord[]>([]);
  const [datasets, setDatasets] = useState<DatasetRecord[]>([]);
  const [transformations, setTransformations] = useState<TransformationRecord[]>([]);
  const [transformationLineage, setTransformationLineage] = useState<TransformationLineageRecord[]>([]);
  const [draftEvidenceRegister, setDraftEvidenceRegister] = useState<EvidenceRegister | null>(null);
  const [evidenceLedger, setEvidenceLedger] = useState<EvidenceLedgerRecord[]>([]);
  const [evidenceCoverage, setEvidenceCoverage] = useState<EvidenceCoverageMatrix | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [project, setProject] = useState<Project | null>(null);
  const [workspace, setWorkspace] = useState<ProjectWorkspace | null>(null);
  const [comparison, setComparison] = useState<SnapshotComparison | null>(null);
  const [readiness, setReadiness] = useState<ProjectReadiness | null>(null);
  const [assumptions, setAssumptions] = useState<AssumptionRecord[]>([]);
  const [overview, setOverview] = useState<ProjectOverview | null>(null);
  const [report, setReport] = useState<SnapshotReport | null>(null);
  const [reportView, setReportView] = useState<SnapshotReportView | null>(null);
  const [decisionPack, setDecisionPack] = useState<DecisionPack | null>(null);
  const [architectureStatus, setArchitectureStatus] = useState<ArchitectureRuntimeStatus | null>(null);
  const [actionItems, setActionItems] = useState<ActionItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isBusy, setIsBusy] = useState(false);
  const [hasEnteredProduct, setHasEnteredProduct] = useState(() => readLocalFlag(PRODUCT_ENTRY_STORAGE_KEY));
  const [legalAccepted, setLegalAccepted] = useState(() => readLocalFlag(LEGAL_ACCEPTANCE_STORAGE_KEY));
  const [stage, setStage] = useState<AppStage>(() => stageFromLocation());
  const [pageDirection, setPageDirection] = useState<"forward" | "back">("forward");
  const lastStageRef = useRef<AppStage>("dashboard");
  const historyNavigationRef = useRef(false);
  const [wizardStep, setWizardStep] = useState(0);
  const [maxUnlockedWizardStep, setMaxUnlockedWizardStep] = useState(0);
  const [showCustomSector, setShowCustomSector] = useState(false);
  const [showCustomSubsector, setShowCustomSubsector] = useState(false);
  const [csvText, setCsvText] = useState("metric,value,unit\nmonthly_units,1600,count\nunit_price,85,SAR");
  const [selectedDatasetId, setSelectedDatasetId] = useState("");
  const [selectedTransformationId, setSelectedTransformationId] = useState("");
  const [transformationOperation, setTransformationOperation] = useState("aggregate_average");
  const [transformationColumn, setTransformationColumn] = useState("value");
  const [fileImportStatus, setFileImportStatus] = useState("");
  const [form, setForm] = useState({
    name: "",
    sector: "",
    jurisdiction: "المملكة العربية السعودية",
    depth_profile: "starter",
    inputs: {
      ...defaultInputs,
      gap_statement: "",
      competitive_edge: "",
      target_audience: "",
      intake_mode: "",
      capital_available: 0,
    },
  });

  const activeStep = useMemo(() => {
    if (report) return 5;
    if (overview) return 4;
    if (project) return 3;
    return 1;
  }, [overview, project, report]);

  const activeStageIndex = appStages.findIndex((item) => item.id === stage);
  const latestRun = workspace?.runs[0];
  const openActionItems = actionItems.filter((item) => item.status !== "closed");
  const readinessBlocked = readiness?.steps.filter((item) => item.status !== "ready") ?? [];
  const evidenceGateCount = (draftEvidenceRegister?.quality_gates ?? overview?.evidence_register.quality_gates ?? []).filter(
    (item) => item.status === "passed"
  ).length;
  const evidenceLinkCount = (draftEvidenceRegister?.evidence_links ?? overview?.evidence_register.evidence_links ?? []).length;
  const decisionStatus = decisionPack?.latest_review?.decision ?? "draft_review";
  const canRunCurrentProject = Boolean(project && readiness?.ready_to_run);
  const snapshotOverview = workspace?.latest_overview ?? overview;
  const snapshotMetricValue = (outputId: string): number | null => {
    const value = snapshotOverview?.kpis.find((item) => item.output_id === outputId)?.value;
    return typeof value === "number" && Number.isFinite(value) ? value : null;
  };
  const commandMetrics = ["npv", "irr", "payback-months", "funding-need-after-equity", "mc-feasibility-gate-probability"]
    .map((metricId) => snapshotOverview?.kpis.find((item) => item.output_id === metricId))
    .filter((item): item is OutputEnvelope => Boolean(item));
  const commandAction = !project
    ? { label: "ابدأ تعريف المشروع", detail: "لم تُنشأ مسودة مشروع بعد.", stage: "wizard" as AppStage, action: "navigate" as const }
    : !readiness
      ? { label: "اربط أدلة المشروع", detail: "أضف ما يثبت أرقامك قبل فحص الجاهزية.", stage: "evidence" as AppStage, action: "navigate" as const }
      : !readiness.ready_to_run
        ? { label: "عالج متطلبات الجاهزية", detail: `${readinessBlocked.length} متطلباً يحتاج انتباهاً قبل التشغيل.`, stage: "readiness" as AppStage, action: "navigate" as const }
        : !snapshotOverview
          ? { label: "شغّل التحليل", detail: "المشروع جاهز لإنشاء أول Snapshot ثابت.", stage: "run" as AppStage, action: "run" as const }
          : { label: "افتح ذكاء السوق والفرص", detail: "اقرأ المقارنات والتوصيات بعد ظهور نتيجة الدراسة.", stage: "reality" as AppStage, action: "navigate" as const };

  function updateInputs(nextInputs: Partial<ProjectInputs>) {
    setForm((current) => ({
      ...current,
      inputs: {
        ...current.inputs,
        ...nextInputs,
      },
    }));
  }

  function updateStructuredLocation(
    part: "location_region" | "location_city" | "location_district" | "location_latitude" | "location_longitude",
    value: string | number
  ) {
    setForm((current) => {
      const inputs = { ...current.inputs, [part]: value };
      const location = [
        inputs.location_district,
        inputs.location_city,
        inputs.location_region,
        "المملكة العربية السعودية",
      ].filter(Boolean).join("، ");
      return {
        ...current,
        jurisdiction: "المملكة العربية السعودية",
        inputs: {
          ...inputs,
          location_country: "SA",
          location_scope: location,
        },
      };
    });
  }

  const mcOutput = useMemo(
    () => overview?.kpis.find((item) => item.output_id === "mc-feasibility-gate-probability"),
    [overview]
  );
  const selectedSector = useMemo(
    () => sectorTaxonomy.find((item) => item.sector_id === form.inputs.primary_sector_id),
    [form.inputs.primary_sector_id, sectorTaxonomy]
  );
  const selectedDataset = useMemo(
    () => datasets.find((item) => item.dataset_id === selectedDatasetId) ?? datasets[0],
    [datasets, selectedDatasetId]
  );
  const selectedDatasetTransformations = useMemo(
    () => transformations.filter((item) => item.dataset_id === selectedDataset?.dataset_id),
    [selectedDataset?.dataset_id, transformations]
  );

  useEffect(() => {
    const stateStage = window.history.state?.asie_stage as AppStage | undefined;
    const hashValue = window.location.hash.replace(/^#/, "") as AppStage;
    const hashStage = appStages.some((item) => item.id === hashValue) ? hashValue : undefined;
    const restoredStage = hashStage ?? (stateStage && appStages.some((item) => item.id === stateStage) ? stateStage : "dashboard");
    window.history.replaceState({ asie_stage: restoredStage }, "", window.location.pathname + window.location.search + `#${restoredStage}`);
    lastStageRef.current = restoredStage;
    setStage(restoredStage);

    const onPopState = (event: PopStateEvent) => {
      const nextStage = event.state?.asie_stage as AppStage | undefined;
      if (!nextStage || !appStages.some((item) => item.id === nextStage)) return;
      historyNavigationRef.current = true;
      setPageDirection(appStages.findIndex((item) => item.id === nextStage) < appStages.findIndex((item) => item.id === lastStageRef.current) ? "back" : "forward");
      setStage(nextStage);
    };
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  useEffect(() => {
    if (lastStageRef.current === stage) return;
    const nextIndex = appStages.findIndex((item) => item.id === stage);
    const previousIndex = appStages.findIndex((item) => item.id === lastStageRef.current);
    setPageDirection(nextIndex < previousIndex ? "back" : "forward");
    if (!historyNavigationRef.current) {
      window.history.pushState({ asie_stage: stage }, "", window.location.pathname + window.location.search + `#${stage}`);
    }
    historyNavigationRef.current = false;
    lastStageRef.current = stage;
  }, [stage]);

  async function loadPolicy() {
    setError(null);
    try {
      const [nextPolicy, workbench, nextProjects, nextDatasets, nextTaxonomy, nextArchitectureStatus] = await Promise.all([
        fetchSourcePolicy(),
        fetchSourceWorkbench(),
        fetchProjects(),
        fetchDatasets(),
        fetchSectorTaxonomy(),
        fetchArchitectureRuntimeStatus(),
      ]);
      setSourcePolicy(nextPolicy);
      setSources(workbench.sources);
      setSourceChecklists(workbench.checklists);
      setProjects(nextProjects);
      setDatasets(nextDatasets);
      setSelectedDatasetId((current) => current || nextDatasets[0]?.dataset_id || "");
      setSectorTaxonomy(nextTaxonomy);
      setArchitectureStatus(nextArchitectureStatus);
    } catch (err) {
      setError(err instanceof Error ? err.message : "تعذر الاتصال بالخدمة المحلية.");
    }
  }

  useEffect(() => {
    void loadPolicy();
  }, []);

  async function loadProjectWorkspace(projectId: string) {
    const [nextReadiness, nextAssumptions, nextWorkspace, nextEvidenceRegister, nextEvidenceLedger] = await Promise.all([
      fetchProjectReadiness(projectId),
      fetchProjectAssumptions(projectId),
      fetchProjectWorkspace(projectId),
      fetchProjectEvidenceRegister(projectId),
      fetchProjectEvidenceLedger(projectId),
    ]);
    setReadiness(nextReadiness);
    setAssumptions(nextAssumptions);
    setWorkspace(nextWorkspace);
    setActionItems(nextWorkspace.action_items ?? []);
    setDraftEvidenceRegister(nextEvidenceRegister);
    setEvidenceLedger(nextEvidenceLedger.evidence_ledger);
    setEvidenceCoverage(nextEvidenceLedger.evidence_coverage);
    setTransformations(nextEvidenceLedger.evidence_register.transformations ?? []);
    setTransformationLineage(nextEvidenceLedger.transformation_lineage ?? []);
    setSelectedDatasetId((current) => current || nextEvidenceLedger.evidence_register.datasets[0]?.dataset_id || "");
    setSelectedTransformationId((current) => current || nextEvidenceLedger.evidence_register.transformations?.[0]?.transformation_id || "");
    setProjects((items) => {
      const withoutCurrent = items.filter((item) => item.project_id !== nextWorkspace.project.project_id);
      return [nextWorkspace.project, ...withoutCurrent].slice(0, 12);
    });
    if (nextWorkspace.runs.length >= 2) {
      setComparison(await compareSnapshots(nextWorkspace.runs[1].snapshot_id ?? "", nextWorkspace.runs[0].snapshot_id ?? ""));
    } else {
      setComparison(null);
    }
  }

  async function handleSaveDraft() {
    setIsBusy(true);
    setError(null);
    setOverview(null);
    setReport(null);
    setReportView(null);
    setDecisionPack(null);
    setActionItems([]);
    try {
      const nextProject = project ? await updateProject(project.project_id, form) : await createProject(form);
      setProject(nextProject);
      await loadProjectWorkspace(nextProject.project_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "تعذر حفظ المسودة.");
    } finally {
      setIsBusy(false);
    }
  }

  async function handleApproveAssumptions(items: AssumptionRecord[]) {
    if (!project) {
      setError("احفظ بيانات المشروع أولًا قبل اعتماد الافتراضات.");
      return;
    }
    const pendingItems = items.filter((item) => item.review_status !== "approved");
    if (!pendingItems.length) return;
    setIsBusy(true);
    setError(null);
    try {
      for (const item of pendingItems) {
        await createProjectAssumption(project.project_id, {
          ...item,
          source_type: "manual_review",
          confidence: Math.max(item.confidence, 0.8),
          review_status: "approved",
        });
      }
      await loadProjectWorkspace(project.project_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "تعذر حفظ المراجعة البشرية.");
    } finally {
      setIsBusy(false);
    }
  }

  async function handleRunProject() {
    if (!project) return;
    setIsBusy(true);
    setError(null);
    setReport(null);
    setReportView(null);
    setDecisionPack(null);
    try {
      const nextOverview = await runProject(project.project_id);
      setOverview(nextOverview);
      setReadiness(nextOverview.readiness);
      setAssumptions(nextOverview.assumption_book);
      setDecisionPack(await fetchDecisionPack(nextOverview.snapshot.snapshot_id));
      await loadProjectWorkspace(project.project_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "تعذر تشغيل التقييم.");
    } finally {
      setIsBusy(false);
    }
  }

  async function handleOpenReport() {
    if (!overview) return;
    setIsBusy(true);
    setError(null);
    try {
      setReport(await fetchSnapshotReport(overview.snapshot.snapshot_id));
      setReportView(await fetchSnapshotReportView(overview.snapshot.snapshot_id));
      setDecisionPack(await fetchDecisionPack(overview.snapshot.snapshot_id));
      if (project) {
        setActionItems(await fetchProjectActionItems(project.project_id));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "تعذر فتح تقرير اللقطة.");
    } finally {
      setIsBusy(false);
    }
  }

  async function handleOpenDecisionPack() {
    if (!overview) return;
    setIsBusy(true);
    setError(null);
    try {
      setDecisionPack(await fetchDecisionPack(overview.snapshot.snapshot_id));
      if (project) {
        setActionItems(await fetchProjectActionItems(project.project_id));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "تعذر فتح حزمة القرار.");
    } finally {
      setIsBusy(false);
    }
  }

  async function handleReviewDecision(decision: ReviewDecision) {
    if (!overview) return;
    setIsBusy(true);
    setError(null);
    try {
      await createSnapshotReview(overview.snapshot.snapshot_id, {
        reviewer: "local-reviewer",
        decision,
        notes: decision === "approved_local" ? "اعتماد مراجعة محلية." : "قرار مراجعة محلية.",
      });
      setDecisionPack(await fetchDecisionPack(overview.snapshot.snapshot_id));
      setReportView(await fetchSnapshotReportView(overview.snapshot.snapshot_id));
      if (project) {
        await loadProjectWorkspace(project.project_id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "تعذر حفظ قرار المراجعة.");
    } finally {
      setIsBusy(false);
    }
  }

  async function handleCloseActionItem(actionItemId: string) {
    if (!project) return;
    setIsBusy(true);
    setError(null);
    try {
      await updateProjectActionItem(project.project_id, actionItemId, {
        status: "closed",
        notes: "أغلق محليًا ضمن workflow المراجعة.",
      });
      setActionItems(await fetchProjectActionItems(project.project_id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "تعذر إغلاق بند المعالجة.");
    } finally {
      setIsBusy(false);
    }
  }

  async function handleCreateLocalDataset() {
    setIsBusy(true);
    setError(null);
    try {
      const dataset = await manualImportDataset({
        source_id: "GASTAT_CANDIDATE",
        title: `${form.name} - مدخلات محلية للمراجعة`,
        publisher: "ASIE local manual entry",
        import_method: csvText.trim() ? "manual_csv" : "manual_table",
        review_status: "review_required",
        csv_text: csvText,
        rows: [
          { field: "startup_cost", value: form.inputs.startup_cost ?? "", unit: "SAR" },
          { field: "monthly_fixed_cost", value: form.inputs.monthly_fixed_cost ?? "", unit: "SAR" },
          { field: "monthly_units", value: form.inputs.monthly_units ?? "", unit: "count" },
        ],
      });
      setDatasets((items) => [dataset, ...items.filter((item) => item.dataset_id !== dataset.dataset_id)]);
      setSelectedDatasetId(dataset.dataset_id);
      if (project) {
        await loadProjectWorkspace(project.project_id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "تعذر إنشاء dataset محلي.");
    } finally {
      setIsBusy(false);
    }
  }

  async function handleFileImport(file: File | null) {
    if (!file) return;
    setIsBusy(true);
    setError(null);
    setFileImportStatus("");
    try {
      const basePayload = {
        file_name: file.name,
        file_type: file.type,
        source_id: "GASTAT_CANDIDATE",
        title: `${form.name} - ${file.name}`,
        publisher: "ASIE local file import",
        review_status: "review_required",
      };
      const dataset = file.name.toLowerCase().endsWith(".xlsx")
        ? await fileImportDataset({
            ...basePayload,
            file_base64: arrayBufferToBase64(await file.arrayBuffer()),
          })
        : await fileImportDataset({
            ...basePayload,
            csv_text: await file.text(),
          });
      setDatasets((items) => [dataset, ...items.filter((item) => item.dataset_id !== dataset.dataset_id)]);
      setSelectedDatasetId(dataset.dataset_id);
      setFileImportStatus(`${dataset.title} · ${dataset.row_count} صف · ${dataset.columns.length} أعمدة`);
      if (project) {
        await loadProjectWorkspace(project.project_id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "تعذر استيراد الملف المحلي.");
    } finally {
      setIsBusy(false);
    }
  }

  async function handleCreateTransformation() {
    const dataset = datasets.find((item) => item.dataset_id === selectedDatasetId);
    if (!dataset) {
      setError("اختر dataset أولًا قبل إنشاء التحويل.");
      return;
    }
    const column = transformationColumn || dataset.columns[0] || "";
    setIsBusy(true);
    setError(null);
    try {
      const transformation = await createDatasetTransformation(dataset.dataset_id, {
        operation_type: transformationOperation,
        operation_label: `${transformationOperation}:${column || "dataset"}`,
        input_columns: column ? [column] : [],
        output_unit: column === "value" ? "unit" : "",
        review_status: "approved",
      });
      setTransformations((items) => [
        transformation,
        ...items.filter((item) => item.transformation_id !== transformation.transformation_id),
      ]);
      setSelectedTransformationId(transformation.transformation_id);
      if (project) {
        await loadProjectWorkspace(project.project_id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "تعذر إنشاء التحويل.");
    } finally {
      setIsBusy(false);
    }
  }

  async function handleReviewSelectedDataset(reviewStatus: "approved_for_use" | "rejected") {
    const dataset = selectedDataset;
    if (!dataset) {
      setError("اختر dataset أولًا قبل المراجعة.");
      return;
    }
    setIsBusy(true);
    setError(null);
    try {
      const reviewed = await reviewDataset(dataset.dataset_id, {
        review_status: reviewStatus,
        human_review_decision: reviewStatus === "approved_for_use" ? "approved" : "rejected",
        license_snapshot_ref: dataset.license_snapshot_ref || `local_license_review:${dataset.dataset_id}`,
        terms_hash: dataset.terms_hash || `local_terms_hash:${dataset.dataset_id}`,
        classification: dataset.classification || "local_manual_dataset_pending_source_terms",
        pdpl_check: dataset.pdpl_check || "local_review_no_personal_data_claim",
        attribution: dataset.attribution || dataset.publisher || "local attribution pending exact source terms",
      });
      setDatasets((items) => [reviewed, ...items.filter((item) => item.dataset_id !== reviewed.dataset_id)]);
      if (project) {
        await loadProjectWorkspace(project.project_id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "تعذر حفظ مراجعة Dataset.");
    } finally {
      setIsBusy(false);
    }
  }

  async function handleReviewSelectedTransformation(reviewStatus: "approved" | "review_required" | "rejected") {
    const transformation = transformations.find((item) => item.transformation_id === selectedTransformationId);
    if (!selectedDataset || !transformation) {
      setError("اختر Transformation قبل المراجعة.");
      return;
    }
    setIsBusy(true);
    setError(null);
    try {
      const reviewed = await createDatasetTransformation(selectedDataset.dataset_id, {
        ...transformation,
        review_status: reviewStatus,
        review_notes:
          reviewStatus === "approved"
            ? "local transformation review approved"
            : reviewStatus === "rejected"
              ? "local transformation review rejected"
              : "local transformation review needs changes",
      });
      setTransformations((items) => [reviewed, ...items.filter((item) => item.transformation_id !== reviewed.transformation_id)]);
      if (project) {
        await loadProjectWorkspace(project.project_id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "تعذر حفظ مراجعة التحويل.");
    } finally {
      setIsBusy(false);
    }
  }

  async function handleLinkApprovedDataset() {
    if (!project) return;
    const register = draftEvidenceRegister ?? overview?.evidence_register;
    const approvedGate =
      register?.quality_gates.find((item) => item.dataset_id === selectedDatasetId && item.can_use_for_assumptions) ??
      register?.quality_gates.find((item) => item.can_use_for_assumptions);
    const firstAssumption = assumptions[0] ?? overview?.assumption_book[0];
    if (!approvedGate || !firstAssumption) {
      setError("لا يوجد dataset مجاز أو افتراض متاح للربط.");
      return;
    }
    setIsBusy(true);
    setError(null);
    try {
      await createEvidenceLink(project.project_id, {
        assumption_id: firstAssumption.assumption_id,
        dataset_id: approvedGate.dataset_id,
        transformation_id: selectedTransformationId || undefined,
        evidence_ref: `dataset:${approvedGate.dataset_id}:${firstAssumption.input_key}`,
        transformation_note: selectedTransformationId
          ? "backend transformation lineage attached; no frontend calculation"
          : "manual evidence mapping; no frontend calculation",
        human_review_decision: "approved",
      });
      await loadProjectWorkspace(project.project_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "تعذر ربط الدليل بالافتراض.");
    } finally {
      setIsBusy(false);
    }
  }

  async function handleLinkSectorCriterion() {
    if (!project) return;
    const register = draftEvidenceRegister ?? overview?.evidence_register;
    const approvedGate =
      register?.quality_gates.find((item) => item.dataset_id === selectedDatasetId && item.can_use_for_assumptions) ??
      register?.quality_gates.find((item) => item.can_use_for_assumptions);
    const firstCriterion = overview?.sector_intelligence.sector_criteria.criteria.find(
      (item) => item.evidence_status === "needs_evidence"
    );
    if (!approvedGate || !firstCriterion) {
      setError("لا يوجد dataset مجاز أو معيار قطاعي يحتاج دليلًا.");
      return;
    }
    setIsBusy(true);
    setError(null);
    try {
      await createEvidenceLink(project.project_id, {
        target_type: "sector_criterion",
        target_id: firstCriterion.criterion_id,
        dataset_id: approvedGate.dataset_id,
        transformation_id: selectedTransformationId || undefined,
        evidence_ref: `dataset:${approvedGate.dataset_id}:${firstCriterion.criterion_id}`,
        transformation_note: selectedTransformationId
          ? "backend transformation lineage attached to sector criterion"
          : "manual sector evidence mapping; no frontend calculation",
        human_review_decision: "approved",
      });
      await loadProjectWorkspace(project.project_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "تعذر ربط الدليل بمعيار القطاع.");
    } finally {
      setIsBusy(false);
    }
  }

  function validateWizardStepAt(step: number): string | null {
    if (step === 0 && !saudiCitiesByRegion[form.inputs.location_region]) return "اختر المنطقة من القائمة المعتمدة.";
    if (step === 0 && !(saudiCitiesByRegion[form.inputs.location_region] ?? []).includes(form.inputs.location_city)) return "اختر المدينة من القائمة.";
    if (step === 0 && form.inputs.location_district?.trim()) {
      const districtError = governedNameError(form.inputs.location_district, "اسم الحي أو الشارع", 2, 50);
      if (districtError) return districtError;
    }
    if (step === 1 && !form.inputs.primary_sector_id?.trim()) return "اختر القطاع أو أضف قطاعك.";
    if (step === 1 && form.inputs.primary_sector_id === "CUSTOM" && !form.sector.trim()) return "اكتب اسم القطاع.";
    if (step === 2 && !form.inputs.subsector_id?.trim()) return "اختر التصنيف الدقيق أو أضف تصنيفك.";
    if (step === 3) {
      const nameError = governedNameError(form.name, "اسم المشروع");
      if (nameError) return nameError;
    }
    if (step === 4 && !form.inputs.gap_statement?.trim()) return "حدد الفجوة التي يعالجها المشروع.";
    if (step === 4 && !form.inputs.competitive_edge?.trim()) return "حدد الميزة التي يقدمها المشروع.";
    if (step === 5 && !form.inputs.target_audience?.trim()) return "اختر جمهور المشروع.";
    if (step === 6 && (!Number.isFinite(form.inputs.capital_available) || form.inputs.capital_available <= 0)) {
      return "اختر رأس المال المتاح أو اكتب مبلغًا أكبر من صفر.";
    }
    if (step === 7 && !form.inputs.intake_mode?.trim()) return "اختر طريقة تعبئة تفاصيل المشروع.";
    if (step === 7 && form.inputs.intake_mode === "file" && !fileImportStatus && datasets.length === 0) {
      return "ارفع ملف CSV أو Excel قبل فحص النواقص.";
    }
    if (step === 7 && form.inputs.intake_mode === "manual") {
      if (form.inputs.startup_cost <= 0) return "اكتب تكلفة التأسيس التقريبية.";
      if (form.inputs.unit_price <= 0) return "اكتب سعر البيع أو الخدمة.";
      if (form.inputs.monthly_units <= 0) return "اكتب عدد العملاء أو الطلبات شهريًا.";
      if (form.inputs.variable_cost > form.inputs.unit_price) return "تكلفة تقديم الخدمة لا ينبغي أن تتجاوز سعر البيع دون توضيح.";
      if (form.inputs.annual_discount_rate <= 0) return "اكتب معدل الخصم السنوي المستخدم في التقييم.";
      if (form.inputs.working_capital_months < 0) return "أشهر رأس المال العامل لا يمكن أن تكون سالبة.";
      if (form.inputs.debt_amount > 0 && form.inputs.annual_interest_rate <= 0) return "اكتب معدل تكلفة التمويل للقرض.";
      if (form.inputs.debt_amount > 0 && form.inputs.loan_years <= 0) return "اكتب مدة القرض بالسنوات.";
    }
    return null;
  }

  function validateWizardStep(): string | null {
    return validateWizardStepAt(wizardStep);
  }

  function unlockAndOpenWizardStep(nextStep: number) {
    const bounded = Math.min(nextStep, wizardJourney.length - 1);
    setMaxUnlockedWizardStep((current) => Math.max(current, bounded));
    setWizardStep(bounded);
  }

  function handleSaveAndAdvance() {
    unlockAndOpenWizardStep(wizardStep + 1);
  }

  async function handleWizardPrimary() {
    const validationError = validateWizardStep();
    if (validationError) {
      setError(validationError);
      return;
    }
    setError(null);
    if (wizardStep < wizardJourney.length - 1) {
      handleSaveAndAdvance();
      return;
    }
    await handleSaveDraft();
    setStage("evidence");
  }

  function advanceWizardFromChoice() {
    unlockAndOpenWizardStep(wizardStep + 1);
  }

  function navigateFromReadiness(stepId: string, status?: string) {
    if (stepId === "sources") {
      setStage("evidence");
      return;
    }
    if (stepId === "run" && status === "ready") {
      setStage("run");
      return;
    }
    const wizardTargets: Record<string, number> = {
      definition: 0,
      sector_intelligence: 1,
      revenue_model: 7,
      costs: 7,
      financing: 7,
      assumptions: 7,
      review: 7,
      run: 7,
    };
    const target = wizardTargets[stepId] ?? 0;
    setMaxUnlockedWizardStep((current) => Math.max(current, target));
    setWizardStep(target);
    setStage("wizard");
    setError(null);
  }

  async function handleRunAndOpenMarketIntelligence() {
    await handleRunProject();
    setStage("reality");
  }

  function openProject(item: Project) {
    setProject(item);
    setForm({
      name: item.name,
      sector: item.sector,
      jurisdiction: item.jurisdiction,
      depth_profile: item.depth_profile,
      inputs: { ...defaultInputs, ...item.inputs },
    });
    setMaxUnlockedWizardStep(wizardJourney.length - 1);
    setStage("wizard");
    void loadProjectWorkspace(item.project_id);
  }

  if (!hasEnteredProduct) {
    return (
      <main id="main-content" className="landing-page">
        <nav className="landing-nav" aria-label="تنقل صفحة ASIE">
          <BrandLockup subtitle="مرصد القرار المحلي" />
          <div className="landing-nav__status"><span /> وضع محلي محكوم</div>
          <div className="landing-nav__actions"><button className="landing-nav__link" onClick={() => { writeLocalFlag(PRODUCT_ENTRY_STORAGE_KEY, true); setHasEnteredProduct(true); }}>دخول المساحة</button><a className="landing-nav__link" href="#admin" onClick={(event) => { event.preventDefault(); window.location.hash = "admin"; window.location.reload(); }}>لوحة المشغّل</a></div>
        </nav>
        <section className="landing-hero landing-hero--immersive">
          <div className="landing-copy">
            <p className="landing-kicker"><Sparkles size={16} aria-hidden="true" /> من الدليل إلى قرار يمكن الرجوع إليه</p>
            <h1>لا تبحث عن رقمٍ جميل.<br /><em>ابنِ قراراً تعرف لماذا تثق به.</em></h1>
            <p className="landing-lede">
              مساحة عمل عربية تحول مشروعك المحلي إلى رحلة منظمة: مدخلات، أدلة، جاهزية، ثم Snapshot ثابت يربط القرار بسببِه.
            </p>
            <div className="landing-actions">
              <button className="primary-button primary-button--large landing-cta" onClick={() => { writeLocalFlag(PRODUCT_ENTRY_STORAGE_KEY, true); setHasEnteredProduct(true); }}>
                <Rocket size={20} aria-hidden="true" />
                ابدأ مساحة قرار محلية
              </button>
              <a className="landing-text-link" href="#decision-flow">شاهد كيف تعمل المنصة <ArrowLeft size={17} aria-hidden="true" /></a>
            </div>
            <div className="trust-row" aria-label="ضمانات ASIE">
              <span><ShieldCheck size={16} aria-hidden="true" /> لا شبكة خارجية</span>
              <span><Database size={16} aria-hidden="true" /> أدلة محلية</span>
              <span><BadgeCheck size={16} aria-hidden="true" /> Snapshot غير قابل للتغيير</span>
            </div>
          </div>
          <div className="decision-orbit" aria-label="تصور متحرك توضيحي لرحلة القرار">
            <div className="orbit-glow" />
            <div className="orbit-ring orbit-ring--one" />
            <div className="orbit-ring orbit-ring--two" />
            <div className="signal signal--one" /><div className="signal signal--two" /><div className="signal signal--three" />
            <article className="orbit-core">
              <span className="orbit-core__label">قرار المشروع</span>
              <strong>قيد البناء</strong>
              <small>من بيانات المثال فقط</small>
            </article>
            <article className="float-card float-card--evidence"><Database size={18} /><div><span>طبقة الأدلة</span><strong>مراجعة محلية</strong></div><i /></article>
            <article className="float-card float-card--readiness"><CheckCircle2 size={18} /><div><span>الجاهزية</span><strong>تحقق قبل التشغيل</strong></div></article>
            <article className="float-card float-card--snapshot"><Layers3 size={18} /><div><span>Snapshot</span><strong>مرجع ثابت</strong></div></article>
            <span className="orbit-caption">تصور توضيحي — لا يمثل بيانات مشروع حقيقية</span>
          </div>
        </section>
        <section className="service-ribbon" aria-label="خدمات المنصة">
          {[
            ["إدخال موجّه", "اسأل عن ما يحتاجه القرار فقط", Target],
            ["دليل قابل للتتبع", "اربط البيانات بتحويلها ومراجعتها", Database],
            ["جاهزية صريحة", "اعرف النواقص قبل أن تشغّل", CheckCircle2],
            ["مراجعة بشرية", "طبقة مستقلة لا تغير الحقيقة", Users],
          ].map(([title, body, Icon]) => {
            const ServiceIcon = Icon as typeof Target;
            return <article key={title as string}><ServiceIcon size={20} aria-hidden="true" /><div><strong>{title as string}</strong><span>{body as string}</span></div></article>;
          })}
        </section>
        <section className="decision-flow" id="decision-flow">
          <div className="decision-flow__intro"><p className="eyebrow">رحلة واحدة، لا مسارات خفية</p><h2>خدمة المنصة ليست “توليد جواب”؛ بل تنظيم سؤال القرار.</h2></div>
          <div className="decision-flow__steps">
            {[
              ["01", "عرّف المشروع", "النطاق، القطاع، والهدف قبل التفاصيل."],
              ["02", "اربط ما تعرفه", "بيانات محلية وخط نسب واضح لكل إدخال."],
              ["03", "تحقق من الجاهزية", "تظهر العوائق كما هي، لا تُخفى."],
              ["04", "شغّل وراجع", "قرار وإسقاطات تعود إلى Snapshot واحد."],
            ].map(([number, title, body]) => <article key={number}><span>{number}</span><h3>{title}</h3><p>{body}</p></article>)}
          </div>
        </section>
      </main>
    );
  }

  if (error && !sourcePolicy) return <ErrorState message={error} onRetry={loadPolicy} />;
  if (!sourcePolicy) return <LoadingState />;

  if (!legalAccepted) {
    return (
      <main id="main-content" className="legal-page">
        <section className="legal-card">
          <BrandLockup subtitle="خطوة أخيرة قبل البدء" landing />
          <p className="eyebrow">موافقة محلية مؤقتة</p>
          <h1>أكمل ملفك قبل استخدام المنصة</h1>
          <p className="muted">هذه البوابة تحفظ مسار المستخدم فقط في هذه النسخة المحلية، ولا تضيف صلاحيات أو اشتراكًا فعليًا.</p>
          <div className="legal-list">
            {[
              ["سياسة الخصوصية", "لا نضع مفاتيح أو مزودين داخل الحزمة، ولا يتم الجلب الخارجي في هذه المرحلة."],
              ["الملكية الفكرية", "المشروع والبيانات المحلية تبقى داخل بيئة التشغيل المحلية."],
              ["حوكمة البيانات", "أي مصدر عام أو حكومي يبقى مرشحًا حتى تمر مراجعة الشروط والجودة."],
              ["حدود القرار", "الاعتماد المحلي ليس ترخيصًا حكوميًا ولا وعدًا استثماريًا."],
            ].map(([title, body]) => (
              <article key={title}>
                <ShieldCheck size={20} aria-hidden="true" />
                <div>
                  <strong>{title}</strong>
                  <p>{body}</p>
                </div>
              </article>
            ))}
          </div>
          <button className="primary-button primary-button--large" onClick={() => { writeLocalFlag(LEGAL_ACCEPTANCE_STORAGE_KEY, true); setLegalAccepted(true); setStage(project ? "dashboard" : "wizard"); }}>
            <CheckCircle2 size={20} aria-hidden="true" />
            أوافق وأبدأ
          </button>
        </section>
      </main>
    );
  }

  return (
    <main id="main-content" className="app-shell">
      <aside className="sidebar" aria-label="مسار مساحة المشروع">
        <BrandLockup subtitle="مرصد القرار المحلي" />
        <nav>
          {appStageGroups.map((group) => (
            <div className="nav-group" key={group.label}>
              <span className="nav-group__label">{group.label}</span>
              {group.stages.map((stageId) => {
                const item = appStages.find((candidate) => candidate.id === stageId);
                if (!item) return null;
                return (
                  <button
                    className={stage === item.id ? "nav-item nav-item--active" : "nav-item"}
                    key={item.id}
                    onClick={() => setStage(item.id)}
                    aria-current={stage === item.id ? "page" : undefined}
                  >
                    <strong>{item.label}</strong>
                    <span>{item.description}</span>
                  </button>
                );
              })}
            </div>
          ))}
        </nav>
        <button className="nav-item nav-item--quiet" onClick={() => { writeLocalFlag(LEGAL_ACCEPTANCE_STORAGE_KEY, false); setLegalAccepted(false); }}>
          <ScrollText size={16} aria-hidden="true" />
          الوثائق القانونية
        </button>
        <div className="sidebar-note">
          <Database size={18} aria-hidden="true" />
          <span>{sourcePolicy.profile_id}</span>
        </div>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div>
            <p className="eyebrow">تشغيل محلي · بدون مفاتيح داخل الحزمة · لا جلب خارجي</p>
            <h1>{appStages.find((item) => item.id === stage)?.label ?? "ASIE"}</h1>
            <p>{project ? `${project.sector} · ${project.jurisdiction}` : "ابدأ من تعريف المشروع، ثم دع المنصة تقودك خطوة بخطوة"}</p>
          </div>
          <div className="topbar__actions topbar__actions--minimal">
            {overview ? (
            <button disabled={isBusy} onClick={handleOpenReport} title="فتح التقرير">
              <FileText size={18} aria-hidden="true" />
              <span>افتح التقرير</span>
            </button>
            ) : null}
          </div>
        </header>

        {error ? (
          <section className="status-banner status-banner--error" role="alert" aria-live="assertive">
            <AlertTriangle size={18} aria-hidden="true" />
            <span>{error}</span>
          </section>
        ) : null}

        <section className={`panel product-flow product-flow--${stage}`} aria-label="تقدم المشروع">
          <div className="section-title">
            <Sparkles size={20} aria-hidden="true" />
            <h2>مسار المستخدم الحالي</h2>
          </div>
          <div className="stage-rail">
            {appStages.map((item, index) => (
              <button
                className={
                  stage === item.id
                    ? "stage-node stage-node--active"
                    : index < activeStageIndex
                      ? "stage-node stage-node--done"
                      : "stage-node"
                }
                key={item.id}
                onClick={() => setStage(item.id)}
              >
                <span>{index + 1}</span>
                <strong>{item.label}</strong>
              </button>
            ))}
          </div>
          <div className="journey-metrics">
            <article>
              <LayoutDashboard size={18} aria-hidden="true" />
              <span>المشاريع</span>
              <strong>{projects.length}</strong>
            </article>
            <article>
              <Database size={18} aria-hidden="true" />
              <span>الأدلة المرتبطة</span>
              <strong>{evidenceLinkCount}</strong>
            </article>
            <article>
              <AlertTriangle size={18} aria-hidden="true" />
              <span>نواقص الجاهزية</span>
              <strong>{readinessBlocked.length}</strong>
            </article>
            <article>
              <FileText size={18} aria-hidden="true" />
              <span>آخر Snapshot</span>
              <strong>{latestRun?.snapshot_id ? latestRun.snapshot_id.slice(-6) : "لا يوجد"}</strong>
            </article>
          </div>
        </section>

        {stage !== "dashboard" ? (
          <section className="next-action-banner" aria-label="الخطوة التالية">
            <div>
              <span>الخطوة التالية</span>
              <strong>{commandAction.label}</strong>
              <p>{commandAction.detail}</p>
            </div>
            <button className="primary-button" disabled={isBusy} onClick={() => {
              setStage(commandAction.stage);
              if (commandAction.action === "run") void handleRunAndOpenMarketIntelligence();
            }}>
              {commandAction.action === "run" ? <Play size={18} aria-hidden="true" /> : <ArrowLeft size={18} aria-hidden="true" />}
              {commandAction.label}
            </button>
          </section>
        ) : null}

        <div className={`client-page-shell client-page-shell--${pageDirection}`} key={stage}>
        {stage === "dashboard" ? (
          <section className="command-center" aria-label="مركز قيادة القرار">
            <article className="command-hero">
              <div className="command-hero__copy">
                <p className="eyebrow">مركز قيادة العميل · خطوة واحدة واضحة في كل مرة</p>
                <h2>{project?.name ?? "حوّل فكرتك إلى قرار مفهوم"}</h2>
                <div className="command-verdict">
                  <span>أين أنت الآن؟</span>
                  <strong>{snapshotOverview ? statusText(snapshotOverview.decision.sovereign_verdict) : project ? "المشروع تحت التجهيز" : "لم تبدأ بعد"}</strong>
                  <p>{snapshotOverview?.decision.reason ?? "لا تحتاج فهم كل الصفحات الآن. ابدأ بتعريف المشروع، وبعدها تظهر لك النواقص والإجراء التالي تلقائياً."}</p>
                </div>
              </div>
              <div className="command-next-action">
                <span>الإجراء التالي</span>
                <strong>{commandAction.label}</strong>
                <p>{commandAction.detail}</p>
                <button
                  className="primary-button"
                  data-testid="primary-command-action"
                  disabled={isBusy}
                  onClick={() => {
                    setStage(commandAction.stage);
                    if (commandAction.action === "run") void handleRunAndOpenMarketIntelligence();
                  }}
                >
                  {commandAction.action === "run" ? <Play size={18} aria-hidden="true" /> : <ArrowLeft size={18} aria-hidden="true" />}
                  {commandAction.label}
                </button>
              </div>
            </article>

            <section className="command-context-strip" aria-label="سياق القرار الحالي">
              <div>
                <span>المشروع</span>
                <strong>{project?.name ?? "لم يُنشأ بعد"}</strong>
                <small>{project ? `${project.sector} · ${project.jurisdiction}` : "يظهر بعد حفظ المسودة"}</small>
              </div>
              <div>
                <span>حالة البيانات</span>
                <strong>{snapshotOverview ? "مرجع محفوظ" : project ? "مسودة محلية" : "بانتظار البداية"}</strong>
                <small>{snapshotOverview ? "القيم المعروضة من Snapshot الخادم" : "لا تُعرض قيم تقديرية قبل التشغيل"}</small>
              </div>
              <div className="command-context-strip__source">
                <Database size={17} aria-hidden="true" />
                <div>
                  <span>مصدر الحقيقة</span>
                  <strong>{snapshotOverview ? "Snapshot غير قابل للتغيير" : "حالة المشروع من الخادم"}</strong>
                </div>
              </div>
            </section>

            <div className="first-minute-journey" aria-label="المسار المبسط لأول تحليل">
              {firstMinuteJourney.map((item, index) => {
                // This compact rail is rendered on the dashboard itself; the
                // detailed current step is shown in the destination page.
                const currentIndex = !project ? 0 : !snapshotOverview ? 1 : 4;
                return (
                  <button
                    key={item.stage}
                    className={
                      index === currentIndex
                        ? "first-minute-step first-minute-step--active"
                        : index < currentIndex
                          ? "first-minute-step first-minute-step--done"
                          : "first-minute-step"
                    }
                    onClick={() => setStage(item.stage)}
                  >
                    <span>{index + 1}</span>
                    <strong>{item.title}</strong>
                    <small>{item.body}</small>
                  </button>
                );
              })}
            </div>

            <div className="command-status-grid">
              <article>
                <span>هل أستطيع التشغيل؟</span>
                <strong>{readiness ? (readiness.ready_to_run ? "جاهز للتشغيل" : "يحتاج إكمالاً") : "لم تُفحص بعد"}</strong>
                <small>{readiness ? `${readinessBlocked.length} عائق ظاهر` : "الحالة من الخادم بعد حفظ المسودة"}</small>
              </article>
              <article>
                <span>هل لدي أدلة؟</span>
                <strong>{evidenceCoverage ? `${evidenceCoverage.supported} مدعوم` : "غير متاح بعد"}</strong>
                <small>{evidenceCoverage ? `${evidenceCoverage.needs_evidence} يحتاج دليلاً` : "لا تُستنتج الثقة من الواجهة"}</small>
              </article>
              <article>
                <span>ما أكبر ما يقلقني؟</span>
                <strong>{snapshotOverview ? `${snapshotOverview.risk_register.top_risks.length} مخاطر عليا` : "غير متاح قبل Snapshot"}</strong>
                <small>{snapshotOverview ? "من سجل المخاطر المحفوظ" : "سيظهر بعد التشغيل"}</small>
              </article>
              <article>
                <span>مرجع القرار</span>
                <strong>{snapshotOverview?.snapshot.snapshot_id?.slice(-8) ?? "لا يوجد"}</strong>
                <small>{snapshotOverview ? "مرجع القرار الحالي" : "لن تظهر قيمة قبل التشغيل"}</small>
              </article>
            </div>

            <SnapshotAnalytics overview={snapshotOverview} />

            <div className="command-detail-grid">
              <article className="panel command-kpis">
                <div className="section-title"><BarChart3 size={20} aria-hidden="true" /><h2>مؤشرات القرار</h2></div>
                {commandMetrics.length ? (
                  <div className="command-kpis__grid">
                    {commandMetrics.map((metric) => <MetricCard output={metric} key={metric.output_id} />)}
                  </div>
                ) : <p className="empty-state">لا توجد مؤشرات قرار محفوظة بعد. لن تعرض المنصة قيماً تقديرية قبل إنشاء Snapshot.</p>}
              </article>
              <article className="panel command-snapshot">
                <div className="section-title"><Layers3 size={20} aria-hidden="true" /><h2>مرجع الحقيقة</h2></div>
                {snapshotOverview ? (
                  <>
                    <strong>Snapshot {snapshotOverview.snapshot.snapshot_id}</strong>
                    <p>التقرير وحزمة القرار والمراجعة تقرأ من هذه اللقطة، ولا تعيد الواجهة الحساب.</p>
                    <div className="button-row">
                      <button onClick={() => { setStage("decision"); void handleOpenDecisionPack(); }} disabled={isBusy}>حزمة القرار</button>
                      <button onClick={() => { setStage("decision"); void handleOpenReport(); }} disabled={isBusy}>التقرير</button>
                    </div>
                  </>
                ) : <p className="empty-state">عند نجاح التشغيل سيظهر هنا معرف اللقطة المرجعية وسجلها.</p>}
              </article>
            </div>

            <div className="command-detail-grid">
              <article className="panel command-risks">
                <div className="section-title"><AlertTriangle size={20} aria-hidden="true" /><h2>المخاطر والإجراء التالي</h2></div>
                {snapshotOverview?.risk_register.top_risks.length ? (
                  <div className="command-risk-list">
                    {snapshotOverview.risk_register.top_risks.slice(0, 3).map((risk) => <article key={risk.risk_id}><strong>{risk.trigger}</strong><span>{risk.severity} · {risk.owner_role}</span><small>{risk.mitigation}</small></article>)}
                  </div>
                ) : <p className="empty-state">لا يوجد سجل مخاطر محفوظ لعرضه بعد.</p>}
              </article>
              <article className="panel command-timeline">
                <div className="section-title"><RefreshCw size={20} aria-hidden="true" /><h2>سجل اللقطات</h2></div>
                <div className="run-list">
                  {(workspace?.runs ?? []).slice(0, 3).map((run) => <article key={run.run_id}><strong>{statusText(run.status)}</strong><span>{run.snapshot_id}</span><small>{run.created_at}</small></article>)}
                  {!workspace?.runs.length ? <p className="empty-state">لا يوجد تغير محفوظ لمقارنته بعد.</p> : null}
                </div>
              </article>
            </div>
          </section>
        ) : null}

        {stage === "wizard" ? (
          <section className="panel wizard-board">
            <div className="section-title">
              <Rocket size={20} aria-hidden="true" />
              <h2>معالج المشروع</h2>
            </div>
            <div className="wizard-rail" aria-label="تقدم معالج المشروع">
              <span className="wizard-progress-label">الخطوة {wizardStep + 1} من {wizardJourney.length}</span>
              <strong>{wizardJourney[wizardStep].label}</strong>
              <span className="wizard-progress-track" aria-hidden="true">
                <span style={{ width: `${((wizardStep + 1) / wizardJourney.length) * 100}%` }} />
              </span>
            </div>
            <div className="wizard-focus">
              <div>
                <p className="eyebrow">الخطوة {wizardStep + 1} من {wizardJourney.length}</p>
                <h2>{wizardJourney[wizardStep].label}</h2>
                <p className="muted">
                  {wizardStepHelp[wizardStep] ?? "أكمل هذه الخطوة ثم تابع."}
                </p>
              </div>
              <div className="button-row">
                <button disabled={wizardStep === 0} onClick={() => setWizardStep((current) => Math.max(current - 1, 0))}>
                  السابق
                </button>
                <button className="primary-button" disabled={isBusy || Boolean(validateWizardStep())} onClick={handleWizardPrimary}>
                  {wizardStep < wizardJourney.length - 1 ? "التالي" : "افحص النواقص"}
                </button>
              </div>
            </div>
          </section>
        ) : null}

        {stage === "evidence" ? (
          <section className="panel evidence-workbench-intro">
            <div className="section-title">
              <Database size={20} aria-hidden="true" />
              <h2>لوحة الأدلة</h2>
            </div>
            <div className="journey-metrics">
              <article>
                <Database size={18} aria-hidden="true" />
                <span>مجموعات البيانات</span>
                <strong>{datasets.length}</strong>
              </article>
              <article>
                <ShieldCheck size={18} aria-hidden="true" />
                <span>اجتازت الجودة</span>
                <strong>{evidenceGateCount}</strong>
              </article>
              <article>
                <FileUp size={18} aria-hidden="true" />
                <span>التحويلات</span>
                <strong>{transformations.length}</strong>
              </article>
              <article>
                <BadgeCheck size={18} aria-hidden="true" />
                <span>سجل الأدلة</span>
                <strong>{evidenceLedger.length}</strong>
              </article>
            </div>
            <p className="muted">الأدلة هي المعلومات التي تثبت أرقام مشروعك. ارفع ملفًا أو أدخل بياناتك، ثم افحص الجودة واعتمد الدليل قبل ربطه بالتحليل.</p>
            <div className="evidence-guidance">
              <article><strong>ما الذي أرفعه؟</strong><span>مبيعات، عروض أسعار، إيجارات، رواتب، أو تقرير رسمي يخص السوق السعودي.</span></article>
              <article><strong>ماذا تفعل المنصة؟</strong><span>تفحص الملف، توضّح النواقص، ثم تعرض لك ما يحتاج اعتمادًا بشريًا.</span></article>
              <article><strong>متى أشغّل التحليل؟</strong><span>{canRunCurrentProject ? "المشروع جاهز. شغّل التحليل لإنشاء أول نتيجة محفوظة." : "أكمل متطلبات الجاهزية أولًا؛ سنرشدك إليها خطوة بخطوة."}</span></article>
            </div>
            <div className="next-action-banner__actions">
              <button className="primary-button" disabled={isBusy} onClick={() => canRunCurrentProject ? void handleRunAndOpenMarketIntelligence() : setStage("readiness")}>
                <Play size={18} aria-hidden="true" />
                {canRunCurrentProject ? "شغّل التحليل الآن" : "انتقل إلى فحص الجاهزية"}
              </button>
            </div>
          </section>
        ) : null}

        {stage === "readiness" ? (
          <section className="panel readiness-board">
            <div className="section-title">
              <CheckCircle2 size={20} aria-hidden="true" />
              <h2>جاهزية المشروع قبل التحليل</h2>
            </div>
            <div className="readiness-actions">
              <button
                type="button"
                onClick={() => {
                  const firstIncomplete = readiness?.steps.find((item) => item.status !== "ready");
                  navigateFromReadiness(firstIncomplete?.step_id ?? "definition", firstIncomplete?.status);
                }}
              >
                <ArrowLeft size={17} aria-hidden="true" />
                العودة إلى أول متطلب ناقص
              </button>
              <small>اضغط على أي بطاقة للذهاب مباشرة إلى مكان تعديلها.</small>
            </div>
            <div className="workflow-steps">
              {(readiness?.steps ?? []).map((item, index) => (
                <button
                  type="button"
                  className={item.status === "ready" ? "workflow-step workflow-step--done workflow-step--action" : "workflow-step workflow-step--action"}
                  key={item.step_id}
                  title={`${item.label}: ${item.message}`}
                  onClick={() => navigateFromReadiness(item.step_id, item.status)}
                >
                  <span>{index + 1}</span>
                  <strong>{item.label}</strong>
                  <small>{item.message}</small>
                  <em>{item.status === "ready" ? "عرض المدخلات" : "انتقل لإكمالها"}</em>
                </button>
              ))}
            </div>
            {!readiness ? <p className="muted">احفظ المسودة أولًا لعرض الجاهزية خطوة بخطوة.</p> : null}
          </section>
        ) : null}

        {stage === "run" ? (
          <section className="panel run-board">
            <div className="section-title">
              <Play size={20} aria-hidden="true" />
              <h2>تشغيل التحليل</h2>
            </div>
            <p className="muted">
              عند الضغط على الزر، تنشئ المنصة نتيجة محفوظة من بياناتك الحالية. لا تحتاج إلى معرفة التفاصيل التقنية.
            </p>
            <button className="primary-button primary-button--large" disabled={!canRunCurrentProject || isBusy} onClick={handleRunAndOpenMarketIntelligence}>
              <Play size={20} aria-hidden="true" />
              ابدأ التحليل
            </button>
            {!project ? <p className="muted">أنشئ المسودة قبل التشغيل.</p> : null}
            {readiness && !readiness.ready_to_run ? <p className="muted">هناك بوابات جاهزية محجوبة. راجع قسم الجاهزية.</p> : null}
          </section>
        ) : null}

        {stage === "reality" ? (
          <section className="reality-page" aria-label="ذكاء السوق والفرص بعد الدراسة">
            <header className="page-intro">
              <p className="eyebrow">بعد الدراسة المالية · محاكاة تطوير</p>
              <h2>اقرأ السوق والفرص قبل اعتماد القرار</h2>
              <p>تأتي هذه المرحلة بعد تشغيل الدراسة. المقارنات والمنافسون والتوصيات المعروضة هنا بيانات تجريبية صريحة؛ لا تدخل اللقطة ولا التقرير ولا الحكم في هذه البيئة.</p>
            </header>
            <LiveCockpit
              projectName={project?.name}
              sector={project?.sector}
              location={project?.inputs.location_scope}
              snapshotId={snapshotOverview?.snapshot.snapshot_id}
              signals={{
                monthlyProfit: snapshotMetricValue("monthly-profit"),
                paybackMonths: snapshotMetricValue("payback-months"),
                fundingGap: snapshotMetricValue("funding-need-after-equity") ?? snapshotMetricValue("funding-gap"),
                feasibilityProbability: snapshotMetricValue("mc-feasibility-gate-probability"),
                monthlyUnits: project?.inputs.monthly_units ?? null,
              }}
              onContinue={() => setStage("decision")}
            />
          </section>
        ) : null}

        {stage === "decision" ? (
          <section className="decision-command" aria-label="مساحة قرار العميل">
            <article className="decision-command__hero">
              <div>
                <p className="eyebrow">مساحة القرار · إسقاط محفوظ لا يعيد الحساب</p>
                <h2>{snapshotOverview ? statusText(snapshotOverview.decision.sovereign_verdict) : "القرار غير متاح بعد"}</h2>
                <p>{snapshotOverview?.decision.reason ?? "شغّل تحليلاً صالحاً أولاً لإظهار الحكم وسببه من Snapshot محفوظ."}</p>
              </div>
              <div className="decision-command__identity">
                <span>مرجع اللقطة</span>
                <strong>{snapshotOverview?.snapshot.snapshot_id ?? "—"}</strong>
                <small>{snapshotOverview ? `Run ${snapshotOverview.run.run_id}` : "لا توجد هوية قرار قبل التشغيل"}</small>
              </div>
            </article>

            <div className="decision-command__summary">
              <article><span>المراجعة البشرية</span><strong>{statusText(decisionStatus)}</strong><small>طبقة فوق القرار وليست تعديلاً للـ Snapshot</small></article>
              <article><span>الإجراءات المفتوحة</span><strong>{openActionItems.length}</strong><small>مستخرجة من الحزمة المحفوظة</small></article>
              <article><span>حالة التنفيذ</span><strong>{snapshotOverview ? statusText(snapshotOverview.execution_plan.status) : "غير متاح"}</strong><small>تتبع القيود والمراحل من الإسقاط</small></article>
            </div>

            {snapshotOverview ? (
              <section className="decision-intelligence" aria-label="ذكاء القرار: المحاكاة والشخصيات الخمس">
                <header><div><p className="eyebrow">ذكاء القرار المحفوظ</p><h2>اختبر القرار من خمس زوايا ومحاكاة المخاطر</h2><p>هذه إسقاطات من Snapshot الحالي؛ الشخصيات تفسّر ولا تصوّت، والحكم السيادي يبقى المرجع.</p></div><button onClick={() => void handleOpenDecisionPack()} disabled={isBusy}>فتح التفسير الكامل <ArrowLeft size={16} /></button></header>
                <div className="decision-intelligence__grid">
                  <article className="monte-carlo-widget">
                    <div className="intelligence-widget__heading"><div><Calculator size={20} /><span>محاكاة Monte Carlo</span></div><small>{snapshotOverview.monte_carlo.status === "ready" ? "محاكاة جاهزة" : "تحتاج مدخلات"}</small></div>
                    <strong>{snapshotOverview.monte_carlo.p_pass === null ? "NOT_READY" : `${Math.round(snapshotOverview.monte_carlo.p_pass * 100)}%`}</strong>
                    <p>احتمال اجتياز بوابات الجدوى عبر {snapshotOverview.monte_carlo.iterations.toLocaleString("ar-SA")} تشغيل محفوظ.</p>
                    <div className="simulation-scale"><i style={{ width: `${Math.max(0, Math.min(100, (snapshotOverview.monte_carlo.p_pass ?? 0) * 100))}%` }} /><span>ضعيف</span><span>متوازن</span><span>قوي</span></div>
                  </article>
                  <div className="persona-kpi-grid">
                    {snapshotOverview.personas.map((persona) => <button key={persona.persona_id} className="persona-kpi" onClick={() => void handleOpenDecisionPack()}><span>{persona.metric}</span><strong>{persona.value === null ? "NOT_READY" : `${Math.round(persona.value * 100)}%`}</strong><small>{statusText(persona.status)} · افتح التفسير</small></button>)}
                  </div>
                </div>
              </section>
            ) : null}

            <div className="decision-command__grid">
              <article className="panel decision-rationale">
                <div className="section-title"><FileText size={20} aria-hidden="true" /><h2>لماذا هذا القرار؟</h2></div>
                {decisionPack ? <><strong>{decisionPack.memo.recommendation}</strong><p>{decisionPack.memo.rationale}</p><small>Decision Pack {decisionPack.decision_pack_hash.slice(-10)}</small></> : <p className="empty-state">افتح حزمة القرار لعرض المذكرة المحفوظة من Snapshot.</p>}
                <div className="button-row"><button disabled={!snapshotOverview || isBusy} onClick={handleOpenDecisionPack}>فتح حزمة القرار</button><button disabled={!snapshotOverview || isBusy} onClick={handleOpenReport}>فتح التقرير</button></div>
              </article>
              <article className="panel decision-evidence">
                <div className="section-title"><Database size={20} aria-hidden="true" /><h2>ثقة الأدلة</h2></div>
                <strong>{snapshotOverview ? `${snapshotOverview.evidence_coverage.supported} مدعوم` : "غير متاح"}</strong>
                <p>{snapshotOverview ? `${snapshotOverview.evidence_coverage.needs_evidence} عنصر يحتاج دليلاً قبل تحسين قوة القرار.` : "ستظهر تغطية الأدلة من اللقطة بعد التشغيل."}</p>
                <button disabled={!snapshotOverview} onClick={() => setStage("evidence")}>تفاصيل الأدلة وخط النسب</button>
              </article>
            </div>

            <div className="decision-command__grid">
              <article className="panel">
                <div className="section-title"><AlertTriangle size={20} aria-hidden="true" /><h2>المخاطر والتخفيف</h2></div>
                <div className="command-risk-list">
                  {(decisionPack?.top_risks ?? snapshotOverview?.risk_register.top_risks ?? []).slice(0, 4).map((risk) => <article key={risk.risk_id}><strong>{risk.trigger}</strong><span>{risk.severity} · {risk.owner_role}</span><small>{risk.mitigation}</small></article>)}
                </div>
                {!snapshotOverview?.risk_register.top_risks.length ? <p className="empty-state">لا توجد مخاطر محفوظة لعرضها بعد.</p> : null}
              </article>
              <article className="panel">
                <div className="section-title"><Target size={20} aria-hidden="true" /><h2>خطة التنفيذ</h2></div>
                <div className="execution-list">
                  {(decisionPack?.execution_plan.milestones ?? snapshotOverview?.execution_plan.milestones ?? []).slice(0, 4).map((milestone) => <article key={milestone.phase_id}><strong>{milestone.phase_id}</strong><span>{milestone.owner_role} · {milestone.estimated_duration_days} يوم</span><small>{milestone.exit_criteria[0] ?? "لا يوجد معيار خروج معلن"}</small></article>)}
                </div>
                {!snapshotOverview?.execution_plan.milestones.length ? <p className="empty-state">تظهر مراحل التنفيذ مع Snapshot المكتمل فقط.</p> : null}
              </article>
            </div>

            <article className="panel decision-review-panel">
              <div className="section-title"><Users size={20} aria-hidden="true" /><h2>المراجعة البشرية والإجراءات</h2></div>
              <p className="muted">الاعتماد أو الرفض يحفظان overlay منفصلاً ولا يغيران الحكم أو hash أو بيانات الـ Snapshot.</p>
              <div className="button-row">
                <button disabled={!decisionPack || isBusy} onClick={() => handleReviewDecision("approved_local")}>اعتماد محلي</button>
                <button disabled={!decisionPack || isBusy} onClick={() => handleReviewDecision("needs_changes")}>طلب تعديل</button>
                <button disabled={!decisionPack || isBusy} onClick={() => handleReviewDecision("rejected_local")}>رفض محلي</button>
              </div>
              <div className="remediation-list">
                {actionItems.slice(0, 6).map((item) => <article key={item.action_item_id}><strong>{item.title}</strong><span>{item.message || item.recommended_action}</span><small>{item.severity} · {item.status}</small>{item.status === "open" ? <button disabled={isBusy} onClick={() => handleCloseActionItem(item.action_item_id)}>إغلاق الإجراء</button> : null}</article>)}
                {!actionItems.length ? <p className="empty-state">لا توجد إجراءات مفتوحة في الحزمة الحالية.</p> : null}
              </div>
            </article>
          </section>
        ) : null}

        {stage === "execution" ? (
          <section className="execution-page" aria-label="خارطة تنفيذ المشروع">
            <header className="page-intro">
              <p className="eyebrow">خارطة البدء والتنفيذ · محاكاة تطوير</p>
              <h2>حوّل القرار إلى بداية مشروع عملية</h2>
              <p>تجمع هذه الصفحة خطة التنفيذ من اللقطة مع قائمة بدء تجريبية: الجهات والمستندات وفريق البداية. لا تمثل متطلبات تنظيمية حقيقية قبل ربط المصادر الرسمية.</p>
            </header>
            <div className="execution-page__grid">
              <article className="panel">
                <div className="section-title"><Target size={20} aria-hidden="true" /><h2>الخطوات القادمة</h2></div>
                <div className="execution-list">
                  {(decisionPack?.execution_plan.milestones ?? snapshotOverview?.execution_plan.milestones ?? []).map((milestone) => <article key={milestone.phase_id}><strong>{milestone.phase_id}</strong><span>{milestone.owner_role} · {milestone.estimated_duration_days} يوم</span><small>{milestone.exit_criteria[0] ?? "لا يوجد معيار خروج معلن"}</small></article>)}
                </div>
                {!snapshotOverview?.execution_plan.milestones.length ? <p className="empty-state">شغّل التحليل أولاً كي تظهر خارطة تنفيذ مرتبطة بالقرار المحفوظ.</p> : null}
              </article>
              <article className="panel execution-page__action">
                <div className="section-title"><CheckCircle2 size={20} aria-hidden="true" /><h2>إجراء اليوم</h2></div>
                <strong>{openActionItems[0]?.title ?? "لا يوجد إجراء مفتوح"}</strong>
                <p>{openActionItems[0]?.message || openActionItems[0]?.recommended_action || "بعد ظهور القرار ستُعرض هنا الخطوة الأهم مع سببها."}</p>
                {openActionItems[0]?.status === "open" ? <button className="primary-button" disabled={isBusy} onClick={() => handleCloseActionItem(openActionItems[0].action_item_id)}>إتمام الإجراء</button> : null}
              </article>
            </div>
            <section className="launch-readiness-demo" aria-label="استعداد بدء المشروع التجريبي">
              <header><div><p className="eyebrow">ما الذي يحتاجه المشروع للبدء؟</p><h2>قائمة تأسيس تجريبية حسب نوع المشروع</h2></div><span className="demo-badge demo-badge--compact">محاكاة تطوير · غير تنظيمية</span></header>
              <div className="launch-readiness-demo__grid">
                <article><KeyRound size={20} aria-hidden="true" /><strong>الجهات والتراخيص</strong><p>سجل تجاري، عنوان، ورخصة قطاعية محتملة. القائمة الفعلية ستتغير حسب القطاع والمدينة ونوع النشاط.</p><small>لا تعتمد هذه القائمة قبل ربط الجهات الرسمية.</small></article>
                <article><FileText size={20} aria-hidden="true" /><strong>المستندات</strong><p>هوية الملاك، عقد موقع، وصف النشاط، عروض موردين، وخطة تشغيل أولية — أمثلة تجريبية فقط.</p><small>المستندات المطلوبة فعلياً ستأتي من قواعد معتمدة.</small></article>
                <article><Users size={20} aria-hidden="true" /><strong>فريق البداية</strong><p>هيكل الفريق سيُقترح من الطاقة التشغيلية وساعات العمل والمبيعات المتوقعة، لا من رقم موحّد لكل مشروع.</p><small>لا يوجد تقدير عمالة فعلي في هذه البيئة بعد.</small></article>
              </div>
            </section>
          </section>
        ) : null}

        {stage === "snapshots" ? (
          <section className="snapshots-page" aria-label="التقارير المحفوظة">
            <header className="page-intro">
              <p className="eyebrow">مخرجات محفوظة · لا إعادة حساب</p>
              <h2>التقارير واللقطات المرجعية</h2>
              <p>كل تقرير هنا مرتبط بـ Snapshot ثابت. إذا لم تُنشأ لقطة بعد، ستظهر الحالة بوضوح ولن تعرض المنصة أرقاماً بديلة.</p>
            </header>

            {workspace?.runs.length ? (
              <div className="snapshot-list">
                {workspace.runs.map((run) => (
                  <article className="snapshot-card" key={run.run_id}>
                    <div className="snapshot-card__identity">
                      <span>Snapshot مرجعي</span>
                      <strong>{run.snapshot_id ?? "بدون Snapshot"}</strong>
                      <small>{run.created_at} · التشغيل {statusText(run.status)}</small>
                    </div>
                    <div className="snapshot-card__decision">
                      <span>حالة الحكم</span>
                      <strong>{run.sovereign_verdict ? statusText(run.sovereign_verdict) : "غير متاح"}</strong>
                      <small>{run.acceptance_status ? `المراجعة: ${statusText(run.acceptance_status)}` : "المراجعة لم تُسجل بعد"}</small>
                    </div>
                    <div className="button-row snapshot-card__actions">
                      {run.snapshot_id ? (
                        <>
                          <a className="secondary-action" href={`/api/snapshots/${run.snapshot_id}/report.html`} target="_blank" rel="noreferrer">فتح التقرير</a>
                          <a className="secondary-action" href={`/api/snapshots/${run.snapshot_id}/decision-pack.html`} target="_blank" rel="noreferrer">فتح حزمة القرار</a>
                        </>
                      ) : <span className="muted">لا توجد مخرجات قابلة للفتح.</span>}
                    </div>
                  </article>
                ))}
              </div>
            ) : (
              <article className="panel snapshots-empty-state">
                <Layers3 size={26} aria-hidden="true" />
                <div>
                  <h3>{project ? "لا توجد لقطة لهذا المشروع بعد" : "اختر مشروعاً أو ابدأ مشروعاً جديداً"}</h3>
