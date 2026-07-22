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
  { id: "reality", label: "اختبر السوق", description: "السياق والمنافسون" },
  { id: "evidence", label: "اربط الأدلة", description: "ملفاتك ومصادر الثقة" },
  { id: "readiness", label: "افحص النواقص", description: "ما يمنع التحليل؟" },
  { id: "run", label: "شغّل التحليل", description: "أنشئ مرجع القرار" },
  { id: "decision", label: "افهم القرار", description: "الحكم وسببه" },
  { id: "execution", label: "نفّذ التالي", description: "خطوات بعد القرار" },
  { id: "snapshots", label: "التقارير", description: "المخرجات المحفوظة" },
];

const appStageGroups: Array<{ label: string; stages: AppStage[] }> = [
  { label: "مسار القرار", stages: ["dashboard", "wizard", "reality"] },
  { label: "التحقق قبل التشغيل", stages: ["evidence", "readiness"] },
  { label: "القرار والتنفيذ", stages: ["run", "decision", "execution", "snapshots"] },
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
  intake_mode: "manual",
  capital_available: 0,
  startup_cost: 0,
  monthly_fixed_cost: 0,
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

function NumberField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number;
  onChange: (nextValue: number) => void;
}) {
  return (
    <label className="field">
      <span>{label}</span>
      <input
        min="0"
        type="number"
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
      />
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
      intake_mode: "manual",
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
  const commandMetrics = ["npv", "irr", "payback-months", "funding-need-after-equity", "mc-feasibility-gate-probability"]
    .map((metricId) => snapshotOverview?.kpis.find((item) => item.output_id === metricId))
    .filter((item): item is OutputEnvelope => Boolean(item));
  const commandAction = !project
    ? { label: "ابدأ تعريف المشروع", detail: "لم تُنشأ مسودة مشروع بعد.", stage: "wizard" as AppStage, action: "navigate" as const }
    : !readiness
      ? { label: "افحص الجاهزية", detail: "احفظ المشروع لعرض بوابات الجاهزية من الخادم.", stage: "wizard" as AppStage, action: "navigate" as const }
      : !readiness.ready_to_run
        ? { label: "عالج متطلبات الجاهزية", detail: `${readinessBlocked.length} متطلباً يحتاج انتباهاً قبل التشغيل.`, stage: "readiness" as AppStage, action: "navigate" as const }
        : !snapshotOverview
          ? { label: "شغّل التحليل", detail: "المشروع جاهز لإنشاء أول Snapshot ثابت.", stage: "run" as AppStage, action: "run" as const }
          : { label: "راجع حزمة القرار", detail: "تتوفر لقطة قرار محفوظة قابلة للمراجعة.", stage: "decision" as AppStage, action: "navigate" as const };

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

  function validateWizardStep(): string | null {
    if (wizardStep === 0 && !form.inputs.location_region?.trim()) return "اختر المنطقة داخل المملكة.";
    if (wizardStep === 0 && !form.inputs.location_city?.trim()) return "اكتب المدينة داخل المملكة.";
    if (wizardStep === 1 && !form.inputs.primary_sector_id?.trim()) return "اختر القطاع أو أضف قطاعك.";
    if (wizardStep === 2 && !form.inputs.subsector_id?.trim()) return "اختر التصنيف الدقيق أو أضف تصنيفك.";
    if (wizardStep === 3 && !form.name.trim()) return "اكتب اسمًا واضحًا للمشروع.";
    return null;
  }

  function handleSaveAndAdvance() {
    setWizardStep((current) => Math.min(current + 1, wizardJourney.length - 1));
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
    setStage("readiness");
  }

  function advanceWizardFromChoice() {
    setWizardStep((current) => Math.min(current + 1, wizardJourney.length - 1));
  }

  async function handleRunAndOpenDecision() {
    await handleRunProject();
    setStage("decision");
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
                    if (commandAction.action === "run") void handleRunAndOpenDecision();
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
                const currentIndex = !project ? 0 : !snapshotOverview ? Math.min(Math.max(activeStageIndex - 1, 1), 2) : 3;
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
            <div className="wizard-rail">
              {wizardJourney.map((item, index) => {
                const Icon = item.icon;
                return (
                  <button
                    className={
                      index === wizardStep
                        ? "wizard-node wizard-node--active"
                        : index < wizardStep
                          ? "wizard-node wizard-node--done"
                          : "wizard-node"
                    }
                    key={item.label}
                    onClick={() => setWizardStep(index)}
                  >
                    <Icon size={16} aria-hidden="true" />
                    <span>{index + 1}</span>
                    <strong>{item.label}</strong>
                  </button>
                );
              })}
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
                <button className="primary-button" disabled={isBusy} onClick={handleWizardPrimary}>
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
              <h2>Evidence Workbench</h2>
            </div>
            <div className="journey-metrics">
              <article>
                <Database size={18} aria-hidden="true" />
                <span>Datasets</span>
                <strong>{datasets.length}</strong>
              </article>
              <article>
                <ShieldCheck size={18} aria-hidden="true" />
                <span>اجتازت الجودة</span>
                <strong>{evidenceGateCount}</strong>
              </article>
              <article>
                <FileUp size={18} aria-hidden="true" />
                <span>Transformations</span>
                <strong>{transformations.length}</strong>
              </article>
              <article>
                <BadgeCheck size={18} aria-hidden="true" />
                <span>Ledger</span>
                <strong>{evidenceLedger.length}</strong>
              </article>
            </div>
            <p className="muted">استخدم لوحة “بيانات وأدلة محلية” أدناه لاستيراد CSV/Excel أو إدخال CSV نصي ثم إنشاء التحويلات والربط.</p>
          </section>
        ) : null}

        {stage === "readiness" ? (
          <section className="panel readiness-board">
            <div className="section-title">
              <CheckCircle2 size={20} aria-hidden="true" />
              <h2>Readiness قبل التشغيل</h2>
            </div>
            <div className="workflow-steps">
              {(readiness?.steps ?? []).map((item, index) => (
                <div className={item.status === "ready" ? "workflow-step workflow-step--done" : "workflow-step"} key={item.step_id}>
                  <span>{index + 1}</span>
                  <strong>{item.label}</strong>
                  <small>{item.message}</small>
                </div>
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
              التشغيل ينشئ Snapshot جديدًا من الحالة الحالية. التقرير وحزمة القرار يقرآن هذه اللقطة بدون إعادة حساب.
            </p>
            <button className="primary-button primary-button--large" disabled={!canRunCurrentProject || isBusy} onClick={handleRunAndOpenDecision}>
              <Play size={20} aria-hidden="true" />
              ابدأ التحليل
            </button>
            {!project ? <p className="muted">أنشئ المسودة قبل التشغيل.</p> : null}
            {readiness && !readiness.ready_to_run ? <p className="muted">هناك بوابات جاهزية محجوبة. راجع قسم الجاهزية.</p> : null}
          </section>
        ) : null}

        {stage === "reality" ? (
          <section className="reality-page" aria-label="اختبار واقع المشروع">
            <header className="page-intro">
              <p className="eyebrow">اختبار الواقع والسوق</p>
              <h2>افحص فرضية المشروع قبل أن تصبح قراراً</h2>
              <p>هذه الصفحة مستقلة عن الحسابات. خريطة السوق والإشارات أدناه محاكاة محلية للتطوير، ولا تدخل Snapshot أو التقرير أو الحكم.</p>
            </header>
            <LiveCockpit />
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
              <p className="eyebrow">خارطة التنفيذ</p>
              <h2>حوّل القرار إلى خطوات يمكن متابعتها</h2>
              <p>هذه خطة عرض من الإسقاط المحفوظ. تحديث التقدم يبقى طبقة مستقلة ولا يغيّر Snapshot أو الحكم.</p>
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
                  <p>{project ? "بعد اجتياز الجاهزية شغّل التحليل لإنشاء أول Snapshot ثابت." : "التقارير لا تظهر من دون مشروع محدد؛ هذه الصفحة لا تنشئ بيانات تجريبية."}</p>
                </div>
                <div className="button-row">
                  <button className="primary-button" onClick={() => setStage(project ? "run" : "wizard")}>
                    {project ? "الانتقال إلى التشغيل" : "ابدأ تعريف المشروع"}
                  </button>
                  {projects.length ? <button onClick={() => openProject(projects[0])}>فتح آخر مشروع</button> : null}
                </div>
              </article>
            )}
          </section>
        ) : null}

        {stage === "architecture" ? (
          <section className="panel architecture-board">
            <div className="section-title">
              <ShieldCheck size={20} aria-hidden="true" />
              <h2>Architecture Runtime Status</h2>
            </div>
            {architectureStatus ? (
              <>
                <div className="journey-metrics">
                  <article>
                    <ShieldCheck size={18} aria-hidden="true" />
                    <span>الحالة النهائية</span>
                    <strong>{architectureStatus.overall_status}</strong>
                  </article>
                  <article>
                    <KeyRound size={18} aria-hidden="true" />
                    <span>المنافذ</span>
                    <strong>{architectureStatus.ports.frontend}/{architectureStatus.ports.api}</strong>
                  </article>
                  <article>
                    <ShieldCheck size={18} aria-hidden="true" />
                    <span>Mutability</span>
                    <strong>{architectureStatus.mutability}</strong>
                  </article>
                  <article>
                    <Layers3 size={18} aria-hidden="true" />
                    <span>Modules</span>
                    <strong>{architectureStatus.registry.counts.modules}</strong>
                  </article>
                  <article>
                    <Database size={18} aria-hidden="true" />
                    <span>Contracts/Sockets</span>
                    <strong>
                      {architectureStatus.registry.counts.contracts}/{architectureStatus.registry.counts.sockets}
                    </strong>
                  </article>
                </div>

                <div className="architecture-grid">
                  <article>
                    <strong>Kernel</strong>
                    <span>{String(architectureStatus.kernel.state)}</span>
                    <small>{String(architectureStatus.kernel.business_logic_owner ?? "none")}</small>
                  </article>
                  <article>
                    <strong>Bus Controller</strong>
                    <span>{String(architectureStatus.bus_controller.state)}</span>
                    <small>رسائل {String(architectureStatus.bus_controller.message_count ?? 0)}</small>
                  </article>
                  <article>
                    <strong>System Bus</strong>
                    <span>{String(architectureStatus.system_bus.state)}</span>
                    <small>Delivered {String(architectureStatus.system_bus.delivered_count ?? 0)}</small>
                  </article>
                  <article>
                    <strong>Socket Contract Layer</strong>
                    <span>{String(architectureStatus.socket_contract_layer.state)}</span>
                    <small>Socket First · Module Second</small>
                  </article>
                  <article>
                    <strong>Module Runtime</strong>
                    <span>{String(architectureStatus.module_runtime.state)}</span>
                    <small>{architectureStatus.module_runtime.registered_handlers.length} handlers</small>
                  </article>
                  <article>
                    <strong>Snapshot Assembly</strong>
                    <span>{architectureStatus.snapshot_assembly.status}</span>
                    <small>{architectureStatus.snapshot_assembly.contract_id}</small>
                  </article>
                  <article>
                    <strong>AI Integration Shell</strong>
                    <span>{architectureStatus.ai_integration_shell.state}</span>
                    <small>providers {architectureStatus.ai_integration_shell.provider_registry.provider_count}</small>
                  </article>
                  <article>
                    <strong>External Fetch</strong>
                    <span>{architectureStatus.guards.external_fetch_enabled ? "enabled" : "disabled"}</span>
                    <small>لا جلب خارجي في هذه المرحلة</small>
                  </article>
                  <article>
                    <strong>Runtime Mutation</strong>
                    <span>{architectureStatus.guards.allows_runtime_mutation ? "allowed" : "blocked"}</span>
                    <small>GET only · {architectureStatus.allowed_methods.join(", ")}</small>
                  </article>
                </div>

                <div className="architecture-hearts" aria-label="القلوب الثلاثة">
                  {architectureStatus.heart_controller.hearts.map((heart) => (
                    <article key={heart.heart_id}>
                      <strong>{heart.heart_id}</strong>
                      <span>{heart.role} · {heart.state}</span>
                      <small>{heart.health} · {heart.controlled_by}</small>
                    </article>
                  ))}
                </div>

                <div className="acceptance-list acceptance-list--wide">
                  {architectureStatus.final_aas_acceptance.checks.map((check) => (
                    <article key={check.check_id}>
                      <strong>{check.check_id}</strong>
                      <span>{check.passed ? "passed" : "failed"} · {check.label}</span>
                      <small>{check.evidence}</small>
                    </article>
                  ))}
                </div>
              </>
            ) : (
              <div className="report-box">
                <p>حالة المعمارية لم تُحمّل بعد.</p>
                <button disabled={isBusy} onClick={loadPolicy}>
                  تحديث الحالة
                </button>
              </div>
            )}
          </section>
        ) : null}

        </div>

        <section className={`builder-grid builder-grid--${stage}`}>
          <div className="panel project-room__projects">
            <div className="section-title">
              <Layers3 size={20} aria-hidden="true" />
              <h2>مساحة المشاريع</h2>
            </div>
            <div className="project-list">
              {(workspace ? [workspace.project, ...projects.filter((item) => item.project_id !== workspace.project.project_id)] : projects)
                .slice(0, 5)
                .map((item) => (
                  <button
                    className={project?.project_id === item.project_id ? "project-row project-row--active" : "project-row"}
                    key={item.project_id}
                    onClick={() => openProject(item)}
                  >
                    <strong>{item.name}</strong>
                    <span>{item.sector} · {item.depth_profile}</span>
                  </button>
                ))}
            </div>
          </div>

          <div className="panel project-room__journey">
            <div className="section-title">
              <Layers3 size={20} aria-hidden="true" />
              <h2>مسار المشروع المؤقت</h2>
            </div>
            <div className="workflow-steps">
              {(readiness?.steps ?? workflow.map((label, index) => ({
                step_id: label,
                label,
                status: index <= activeStep ? "ready" : "needs_input",
                message: "",
              }))).map((item, index) => (
                <div
                  className={
                    item.status === "ready"
                      ? "workflow-step workflow-step--done"
                      : item.status === "needs_review"
                        ? "workflow-step workflow-step--review"
                        : "workflow-step"
                  }
                  key={item.step_id}
                  title={item.message}
                >
                  <span>{index + 1}</span>
                  <strong>{item.label}</strong>
                </div>
              ))}
            </div>
          </div>

          <div className="panel project-room__source">
            <div className="section-title">
              <KeyRound size={20} aria-hidden="true" />
              <h2>بوابة المصادر</h2>
            </div>
            <dl className="source-summary">
              <div>
                <dt>مصادر مفعلة</dt>
                <dd>{sourcePolicy.enabled_sources.length}</dd>
              </div>
              <div>
                <dt>مرشحة</dt>
                <dd>{sourcePolicy.candidate_sources.length}</dd>
              </div>
              <div>
                <dt>مرجعية فقط</dt>
                <dd>{sourcePolicy.reference_only.length}</dd>
              </div>
            </dl>
            <p className="muted">{sourcePolicy.rule}</p>
            <div className="source-list">
              {sources.slice(0, 3).map((source) => (
                <article key={source.source_id}>
                  <strong>{source.source_id}</strong>
                  <span>{source.state}</span>
                </article>
              ))}
            </div>
            <p className="muted">{sourceChecklists.filter((item) => item.can_enable).length} مصدر مكتمل المراجعة</p>
          </div>

          <div className="panel evidence-room">
            <div className="section-title">
              <Database size={20} aria-hidden="true" />
              <h2>بيانات وأدلة محلية</h2>
            </div>
            <dl className="source-summary">
              <div>
                <dt>Datasets</dt>
                <dd>{datasets.length}</dd>
              </div>
              <div>
                <dt>اجتازت الجودة</dt>
                <dd>{(draftEvidenceRegister?.quality_gates ?? overview?.evidence_register.quality_gates ?? []).filter((item) => item.status === "passed").length}</dd>
              </div>
              <div>
                <dt>روابط أدلة</dt>
                <dd>{(draftEvidenceRegister?.evidence_links ?? overview?.evidence_register.evidence_links ?? []).length}</dd>
              </div>
              <div>
                <dt>تحويلات</dt>
                <dd>{transformations.length}</dd>
              </div>
            </dl>
            <label className="field file-field">
              <span>استيراد ملف بيانات</span>
              <input
                type="file"
                accept=".csv,.xlsx,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                disabled={isBusy}
                onChange={(event) => {
                  void handleFileImport(event.target.files?.[0] ?? null);
                  event.currentTarget.value = "";
                }}
              />
            </label>
            {fileImportStatus ? <p className="muted">{fileImportStatus}</p> : null}
            <label className="field">
              <span>إدخال CSV نصي يدوي</span>
              <textarea value={csvText} onChange={(event) => setCsvText(event.target.value)} rows={4} />
            </label>
            <div className="form-grid form-grid--compact">
              <label className="field">
                <span>Dataset للتحويل</span>
                <select value={selectedDataset?.dataset_id ?? ""} onChange={(event) => setSelectedDatasetId(event.target.value)}>
                  {datasets.map((dataset) => (
                    <option value={dataset.dataset_id} key={dataset.dataset_id}>
                      {dataset.title}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field">
                <span>عملية التحويل</span>
                <select value={transformationOperation} onChange={(event) => setTransformationOperation(event.target.value)}>
                  <option value="aggregate_average">متوسط عمود</option>
                  <option value="aggregate_sum">مجموع عمود</option>
                  <option value="select_column">اختيار عمود</option>
                  <option value="manual_derivation_note">ملاحظة اشتقاق</option>
                </select>
              </label>
              <label className="field">
                <span>العمود</span>
                <select value={transformationColumn} onChange={(event) => setTransformationColumn(event.target.value)}>
                  {(selectedDataset?.columns ?? ["value"]).map((column) => (
                    <option value={column} key={column}>
                      {column}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field">
                <span>Transformation</span>
                <select value={selectedTransformationId} onChange={(event) => setSelectedTransformationId(event.target.value)}>
                  <option value="">بدون تحويل</option>
                  {selectedDatasetTransformations.map((item) => (
                    <option value={item.transformation_id} key={item.transformation_id}>
                      {item.operation_type} · {item.review_status}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <div className="topbar__actions topbar__actions--inline">
              <button disabled={isBusy} onClick={handleCreateLocalDataset} title="إنشاء dataset يدوي محلي">
                <Database size={18} aria-hidden="true" />
                <span>Dataset يدوي</span>
              </button>
              <button disabled={!selectedDataset || isBusy} onClick={handleCreateTransformation} title="إنشاء تحويل خلفي معتمد محليًا">
                <FileUp size={18} aria-hidden="true" />
                <span>إنشاء تحويل</span>
              </button>
              <button disabled={!selectedDataset || isBusy} onClick={() => handleReviewSelectedDataset("approved_for_use")} title="اعتماد مراجعة Dataset محلية">
                <ShieldCheck size={18} aria-hidden="true" />
                <span>اعتماد Dataset</span>
              </button>
              <button disabled={!selectedDataset || isBusy} onClick={() => handleReviewSelectedDataset("rejected")} title="رفض Dataset محليًا">
                <AlertTriangle size={18} aria-hidden="true" />
                <span>رفض Dataset</span>
              </button>
              <button disabled={!selectedTransformationId || isBusy} onClick={() => handleReviewSelectedTransformation("approved")} title="اعتماد التحويل محليًا">
                <BadgeCheck size={18} aria-hidden="true" />
                <span>اعتماد تحويل</span>
              </button>
              <button disabled={!selectedTransformationId || isBusy} onClick={() => handleReviewSelectedTransformation("review_required")} title="إرجاع التحويل للتعديل">
                <RefreshCw size={18} aria-hidden="true" />
                <span>تعديل تحويل</span>
              </button>
              <button disabled={!project || isBusy} onClick={handleLinkApprovedDataset} title="ربط dataset مجاز بأول افتراض">
                <BadgeCheck size={18} aria-hidden="true" />
                <span>ربط دليل</span>
              </button>
              <button disabled={!project || isBusy} onClick={handleLinkSectorCriterion} title="ربط dataset مجاز بمعيار قطاعي">
                <Layers3 size={18} aria-hidden="true" />
                <span>ربط معيار</span>
              </button>
            </div>
            <div className="source-list">
              {datasets.slice(0, 3).map((dataset) => (
                <article key={dataset.dataset_id}>
                  <strong>{dataset.title}</strong>
                  <span>
                    {dataset.review_status} · جودة {dataset.notes.quality_review?.status ?? "unknown"} · {dataset.row_count} صف
                  </span>
                  <small>{dataset.columns.slice(0, 4).join(" · ")}</small>
                </article>
              ))}
            </div>
            <div className="source-list">
              {transformations.slice(0, 3).map((transformation) => (
                <article key={transformation.transformation_id}>
                  <strong>{transformation.operation_label}</strong>
                  <span>
                    {transformation.operation_type} · مراجعة {transformation.review_status} · جودة{" "}
                    {transformation.lineage.quality_review?.status ?? "unknown"}
                  </span>
                  <small>
                    {transformation.output_value ?? "بدون ناتج"} {transformation.output_unit}
                  </small>
                </article>
              ))}
            </div>
            {selectedDataset?.notes.quality_review ? (
              <dl className="source-summary">
                <div>
                  <dt>جودة Dataset</dt>
                  <dd>{selectedDataset.notes.quality_review.status}</dd>
                </div>
                <div>
                  <dt>قيم مفقودة</dt>
                  <dd>{Math.round(selectedDataset.notes.quality_review.max_missing_ratio * 100)}%</dd>
                </div>
                <div>
                  <dt>صفوف مكررة</dt>
                  <dd>{selectedDataset.notes.quality_review.duplicate_row_count}</dd>
                </div>
              </dl>
            ) : null}
            {evidenceCoverage ? (
              <p className="muted">
                تغطية الأدلة: {evidenceCoverage.supported} مدعوم · {evidenceCoverage.needs_evidence} يحتاج دليل · Ledger{" "}
                {evidenceLedger.length} · Lineage {transformationLineage.length}
              </p>
            ) : null}
            <p className="muted">أي dataset ناقص الترخيص أو مراجعة المصدر يبقى NOT_READY ولا يستخدم لدعم الافتراضات.</p>
          </div>
        </section>

        <section className={`panel project-inputs-panel project-inputs-panel--${stage} project-inputs-panel--step-${wizardStep}`}>
          <div className="section-title">
            <Calculator size={20} aria-hidden="true" />
            <h2>ابدأ مشروعك</h2>
          </div>
          <div className="guided-question-card">
            {wizardStep === 0 ? (
              <>
                <p className="guided-question-card__kicker">الموقع داخل المملكة</p>
                <h3>أين سيعمل المشروع؟</h3>
                <p>المرحلة الحالية مخصصة للسوق السعودي. اكتب المنطقة والمدينة، وأضف الحي أو الإحداثيات عند الحاجة.</p>
                <div className="location-fields">
                  <label className="field"><span>الدولة</span><input value="المملكة العربية السعودية" readOnly aria-readonly="true" /></label>
                  <label className="field"><span>المنطقة</span><input value={form.inputs.location_region} placeholder="مثال: منطقة الرياض" onChange={(event) => updateStructuredLocation("location_region", event.target.value)} /></label>
                  <label className="field"><span>المدينة</span><input value={form.inputs.location_city} placeholder="مثال: الرياض" onChange={(event) => updateStructuredLocation("location_city", event.target.value)} /></label>
                  <label className="field"><span>الحي أو الشارع <small>(اختياري)</small></span><input value={form.inputs.location_district} placeholder="مثال: حي العليا" onChange={(event) => updateStructuredLocation("location_district", event.target.value)} /></label>
                  <label className="field"><span>خط العرض <small>(اختياري)</small></span><input type="number" step="any" value={form.inputs.location_latitude || ""} placeholder="24.7136" onChange={(event) => updateStructuredLocation("location_latitude", Number(event.target.value) || 0)} /></label>
                  <label className="field"><span>خط الطول <small>(اختياري)</small></span><input type="number" step="any" value={form.inputs.location_longitude || ""} placeholder="46.6753" onChange={(event) => updateStructuredLocation("location_longitude", Number(event.target.value) || 0)} /></label>
                </div>
                <p className="guided-hint">لا تُقرأ إحداثيات الجهاز تلقائيًا. إدخالها اختياري وتحت سيطرة المستخدم.</p>
              </>
            ) : null}
            {wizardStep === 1 ? (
              <>
                <p className="guided-question-card__kicker">القطاع</p>
                <h3>في أي قطاع تريد اختبار المشروع؟</h3>
                <p>اضغط على المجال الأقرب لفكرتك، وسننتقل بك مباشرة للنوع الدقيق.</p>
                <div className="choice-grid choice-grid--sectors" role="group" aria-label="قطاعات المشروع">
                  {sectorTaxonomy.map((item) => (
                    <button type="button" key={item.sector_id} className={form.inputs.primary_sector_id === item.sector_id ? "choice-card choice-card--active" : "choice-card"} onClick={() => {
                      setShowCustomSector(false);
                      setForm((current) => ({ ...current, sector: item.arabic_name, inputs: { ...current.inputs, primary_sector_id: item.sector_id, subsector_id: "" } }));
                      advanceWizardFromChoice();
                    }}>
                      <strong>{item.arabic_name}</strong><small>{item.subsectors.length} تصنيفات متاحة</small>
                    </button>
                  ))}
                  <button type="button" className="choice-card choice-card--add" onClick={() => { setShowCustomSector(true); setForm((current) => ({ ...current, sector: "", inputs: { ...current.inputs, primary_sector_id: "CUSTOM", subsector_id: "" } })); }}><strong>+ قطاع آخر</strong><small>اكتب مجالك إذا لم تجده</small></button>
                </div>
                {showCustomSector ? (
                  <div className="guided-input-row">
                    <label className="field"><span>اسم القطاع</span><input autoFocus value={form.sector} placeholder="مثال: الصناعات الإبداعية" onChange={(event) => setForm((current) => ({ ...current, sector: event.target.value, inputs: { ...current.inputs, primary_sector_id: "CUSTOM" } }))} /></label>
                    <button type="button" className="primary-button" disabled={!form.sector.trim()} onClick={advanceWizardFromChoice}>حفظ القطاع والمتابعة</button>
                  </div>
                ) : null}
              </>
            ) : null}
            {wizardStep === 2 ? (
              <>
                <p className="guided-question-card__kicker">التصنيف الدقيق</p>
                <h3>ما نوع المشروع داخل هذا القطاع؟</h3>
                <p>اختر النوع الذي يصف مشروعك بدقة. إذا لم تجده، أضف وصفك الخاص.</p>
                <div className="choice-grid" role="group" aria-label="التصنيف الدقيق">
                  {(selectedSector?.subsectors ?? [form.inputs.subsector_id]).map((item) => (
                    <button type="button" key={item} className={form.inputs.subsector_id === item ? "choice-card choice-card--active" : "choice-card"} onClick={() => { updateInputs({ subsector_id: item }); advanceWizardFromChoice(); }}><strong>{item}</strong><small>اختيار التصنيف</small></button>
                  ))}
                  <button type="button" className="choice-card choice-card--add" onClick={() => { setShowCustomSubsector(true); updateInputs({ subsector_id: "" }); }}><strong>+ تصنيف آخر</strong><small>أضف نوع مشروعك</small></button>
                </div>
                {showCustomSubsector ? (
                  <div className="guided-input-row">
                    <label className="field"><span>وصف التصنيف</span><input autoFocus value={form.inputs.subsector_id} placeholder="اكتب النشاط بدقة" onChange={(event) => updateInputs({ subsector_id: event.target.value })} /></label>
                    <button type="button" className="primary-button" disabled={!form.inputs.subsector_id?.trim()} onClick={advanceWizardFromChoice}>حفظ التصنيف والمتابعة</button>
                  </div>
                ) : null}
              </>
            ) : null}
            {wizardStep === 3 ? (
              <>
                <p className="guided-question-card__kicker">اسم المشروع</p>
                <h3>وش اسم مشروعك؟</h3>
                <label className="field">
                  <span>اسم بسيط وواضح</span>
                  <input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} />
                </label>
                <div className="guided-actions"><button type="button" className="secondary-action" disabled><Sparkles size={17} aria-hidden="true" /> اقترح أسماء للمشروع</button><small>ستتصل هذه المساعدة لاحقاً بخدمة الذكاء الاصطناعي المعتمدة.</small></div>
              </>
            ) : null}
            {wizardStep === 4 ? (
              <>
                <p className="guided-question-card__kicker">الفجوة والميزة</p>
                <h3>ما الفجوة التي يحلها مشروعك؟ وما ميزتك؟</h3>
                <p>لا تحتاج صياغة طويلة. اختر الأقرب، ويمكنك تعديلها أو كتابة خيارك.</p>
                <div className="choice-section"><strong>ما الفجوة التي لاحظتها؟</strong><div className="choice-grid choice-grid--compact">{["الخدمة غير متوفرة في موقعي", "الانتظار أو الوصول صعب", "السعر مرتفع", "الجودة أو التخصص غير كافٍ"].map((item) => <button type="button" key={item} className={form.inputs.gap_statement === item ? "choice-card choice-card--active" : "choice-card"} onClick={() => updateInputs({ gap_statement: item })}>{item}</button>)}</div></div>
                <div className="choice-section"><strong>ما ميزتك الأقرب؟</strong><div className="choice-grid choice-grid--compact">{["موقع أفضل", "سرعة أعلى", "تخصص واضح", "سعر منافس", "تجربة أسهل"].map((item) => <button type="button" key={item} className={form.inputs.competitive_edge === item ? "choice-card choice-card--active" : "choice-card"} onClick={() => updateInputs({ competitive_edge: item, activity_description: item })}>{item}</button>)}</div></div>
                <div className="guided-actions"><button type="button" className="secondary-action" disabled><Sparkles size={17} aria-hidden="true" /> ساعدني على فهم الفجوة والميزة</button><small>ستظهر اقتراحات ذكية بعد تفعيل بوابة المساعدة.</small></div>
              </>
            ) : null}
            {wizardStep === 5 ? (
              <>
                <p className="guided-question-card__kicker">الجمهور</p>
                <h3>من هو جمهور المشروع؟</h3>
                <div className="choice-grid" role="group" aria-label="جمهور المشروع">
                  {[
                    ["individuals", "أفراد", "مستهلكون أو مرضى أو زوار"],
                    ["organizations", "مؤسسات", "جهات ومدارس ومنشآت"],
                    ["companies", "شركات", "عملاء تجاريون وتعاقدات"],
                    ["mixed", "مزيج", "أكثر من شريحة"],
                  ].map(([value, label, detail]) => (
                    <button
                      type="button"
                      key={value}
                      className={form.inputs.target_audience === value ? "choice-card choice-card--active" : "choice-card"}
                      onClick={() => { updateInputs({ target_audience: value }); advanceWizardFromChoice(); }}
                    >
                      <strong>{label}</strong>
                      <small>{detail}</small>
                    </button>
                  ))}
                </div>
              </>
            ) : null}
            {wizardStep === 6 ? (
              <>
                <p className="guided-question-card__kicker">رأس المال</p>
                <h3>كم رأس المال المتاح عندك تقريباً؟</h3>
                <div className="choice-grid choice-grid--capital">{[[100000,"100 ألف"],[200000,"200 ألف"],[500000,"500 ألف"],[1000000,"مليون"]].map(([value,label]) => <button type="button" key={value} className={form.inputs.capital_available === value ? "choice-card choice-card--active" : "choice-card"} onClick={() => { updateInputs({ capital_available: Number(value), equity_contribution: Number(value), startup_cost: Number(value) }); advanceWizardFromChoice(); }}><strong>{label} ريال</strong><small>اختيار سريع</small></button>)}<button type="button" className="choice-card choice-card--add" onClick={() => setError("اكتب المبلغ الحقيقي في الحقل أسفل الخيارات.")}><strong>مبلغ آخر</strong><small>أدخل الرقم بنفسك</small></button></div>
                <NumberField label="المبلغ الحقيقي المتاح" value={form.inputs.capital_available} onChange={(value) => updateInputs({ capital_available: value, equity_contribution: value, startup_cost: value })} />
              </>
            ) : null}
            {wizardStep === 7 ? (
              <>
                <p className="guided-question-card__kicker">طريقة تعبئة التفاصيل</p>
                <h3>كيف تريد تزويد المنصة بتفاصيل المشروع؟</h3>
                <div className="choice-grid choice-grid--three" role="group" aria-label="طريقة تعبئة تفاصيل المشروع">
                  {[
                    ["manual", "أعبي بنفسي", "أدخل الأرقام الأساسية الآن."],
                    ["file", "أرفع ملف", "Excel أو CSV يحتوي الأرقام."],
                    ["assisted_estimate", "مساعدة تقديرية لاحقاً", "غير مفعّلة في النسخة المحلية حتى بوابة AI."],
                  ].map(([value, label, detail]) => (
                    <button
                      type="button"
                      key={value}
                      className={form.inputs.intake_mode === value ? "choice-card choice-card--active" : "choice-card"}
                      onClick={() => updateInputs({ intake_mode: value })}
                      disabled={value === "assisted_estimate"}
                    >
                      <strong>{label}</strong>
                      <small>{detail}</small>
                    </button>
                  ))}
                </div>
                {form.inputs.intake_mode === "file" ? (
                  <label className="field file-field">
                    <span>ارفع ملف الأرقام</span>
                    <input
                      type="file"
                      accept=".csv,.xlsx,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                      disabled={isBusy}
                      onChange={(event) => {
                        void handleFileImport(event.target.files?.[0] ?? null);
                        event.currentTarget.value = "";
                      }}
                    />
                  </label>
                ) : null}
                {form.inputs.intake_mode === "manual" ? (
                  <div className="guided-finance-lite">
                    <NumberField label="تكلفة التأسيس التقريبية" value={form.inputs.startup_cost} onChange={(value) => updateInputs({ startup_cost: value })} />
                    <NumberField label="المصاريف الشهرية" value={form.inputs.monthly_fixed_cost} onChange={(value) => updateInputs({ monthly_fixed_cost: value })} />
                    <NumberField label="سعر البيع أو الخدمة" value={form.inputs.unit_price} onChange={(value) => updateInputs({ unit_price: value })} />
                    <NumberField label="تكلفة تقديم الخدمة" value={form.inputs.variable_cost} onChange={(value) => updateInputs({ variable_cost: value })} />
                    <NumberField label="عدد العملاء أو الطلبات شهرياً" value={form.inputs.monthly_units} onChange={(value) => updateInputs({ monthly_units: value })} />
                  </div>
                ) : null}
              </>
            ) : null}
          </div>
        </section>

        <div className={`legacy-projections legacy-projections--${stage}`}>
        {overview ? (
          <>
            {workspace ? (
              <section className="builder-grid">
                <div className="panel">
                  <div className="section-title">
                    <RefreshCw size={20} aria-hidden="true" />
                    <h2>سجل التشغيلات</h2>
                  </div>
                  <div className="run-list">
                    {workspace.runs.slice(0, 5).map((run) => (
                      <article key={run.run_id}>
                        <strong>{run.sovereign_verdict ?? "UNKNOWN"}</strong>
                        <span>{run.snapshot_id}</span>
                        <small>{run.acceptance_status} · {run.created_at}</small>
                      </article>
                    ))}
                  </div>
                </div>

                <div className="panel">
                  <div className="section-title">
                    <Calculator size={20} aria-hidden="true" />
                    <h2>مقارنة آخر لقطتين</h2>
                  </div>
                  {comparison ? (
                    <div className="comparison-list">
                      {comparison.metric_deltas.map((item) => (
                        <article key={item.output_id}>
                          <strong>{metricTitle(item.output_id)}</strong>
                          <span>
                            {item.from ?? "NA"} → {item.to ?? "NA"}
                          </span>
                          <small>Delta {item.delta ?? "NA"} {item.unit}</small>
                        </article>
                      ))}
                    </div>
                  ) : (
                    <p className="muted">تحتاج تشغيلين محفوظين للمقارنة.</p>
                  )}
                </div>
              </section>
            ) : null}

            <section className="decision-band" aria-label="ملخص القرار">
              <div className="decision-card decision-card--primary">
                <ShieldCheck size={24} aria-hidden="true" />
                <span>الحكم السيادي</span>
                <strong>{statusText(overview.decision.sovereign_verdict)}</strong>
                <p>{overview.decision.reason}</p>
              </div>
              <div className="decision-card">
                <Calculator size={24} aria-hidden="true" />
                <span>{overview.monte_carlo.label_ar}</span>
                <strong>{mcOutput ? formatValue(mcOutput) : "NOT_READY"}</strong>
                <p>Seed {overview.monte_carlo.seed} · {overview.monte_carlo.iterations} تشغيل</p>
              </div>
              <div className="decision-card">
                <Database size={24} aria-hidden="true" />
                <span>لقطة التشغيل</span>
                <strong>{statusText(overview.project.data_badge ?? "")}</strong>
                <p>{overview.snapshot.snapshot_id}</p>
              </div>
            </section>

            <section className="persona-strip" aria-label="مؤشرات الشخصيات الخمس">
              {overview.personas.map((persona) => (
                <article key={persona.persona_id}>
                  <span>{persona.metric}</span>
                  <strong>{persona.value === null ? "NOT_READY" : `${Math.round(persona.value * 100)}%`}</strong>
                  <small>{statusText(persona.status)}</small>
                </article>
              ))}
            </section>

            <section className="builder-grid">
              <div className="panel">
                <div className="section-title">
                  <Calculator size={20} aria-hidden="true" />
                  <h2>سيناريوهات المحرك المالي</h2>
                </div>
                <div className="scenario-grid">
                  {overview.finance.scenarios.map((scenario) => (
                    <article key={scenario.scenario_id}>
                      <span>{scenario.scenario_id}</span>
                      <strong>
                        {new Intl.NumberFormat("ar-SA", {
                          style: "currency",
                          currency: "SAR",
                          maximumFractionDigits: 0,
                        }).format(scenario.npv)}
                      </strong>
                      <small>NPV · Payback {scenario.payback_months?.toFixed(1) ?? "NOT_READY"} شهر</small>
                    </article>
                  ))}
                </div>
              </div>

              <div className="panel">
                <div className="section-title">
                  <Calculator size={20} aria-hidden="true" />
                  <h2>نموذج التشغيل والتمويل</h2>
                </div>
                {overview.finance.operating_model && overview.finance.capex_breakdown && overview.finance.opex_breakdown ? (
                  <dl className="audit-list">
                    <div>
                      <dt>مصدر الوحدات</dt>
                      <dd>{overview.finance.operating_model.unit_source}</dd>
                    </div>
                    <div>
                      <dt>الوحدات الشهرية</dt>
                      <dd>{overview.finance.operating_model.monthly_units}</dd>
                    </div>
                    <div>
                      <dt>OPEX شهري</dt>
                      <dd>{overview.finance.opex_breakdown.total_monthly_opex}</dd>
                    </div>
                    <div>
                      <dt>CAPEX إجمالي</dt>
                      <dd>{overview.finance.capex_breakdown.total_capex}</dd>
                    </div>
                    <div>
                      <dt>DSCR</dt>
                      <dd>{overview.finance.debt_service_profile?.dscr ?? "NOT_READY"}</dd>
                    </div>
                  </dl>
                ) : (
                  <p className="muted">نموذج التشغيل غير جاهز.</p>
                )}
              </div>

              <div className="panel">
                <div className="section-title">
                  <Layers3 size={20} aria-hidden="true" />
                  <h2>القطاع ومؤشرات الاستثمار</h2>
                </div>
                <dl className="audit-list">
                  <div>
                    <dt>القطاع</dt>
                    <dd>
                      {overview.sector_intelligence.taxonomy_record.primary_sector_ar ||
                        overview.sector_intelligence.taxonomy_record.primary_sector ||
                        "غير مصنف"}
                    </dd>
                  </div>
                  <div>
                    <dt>التصنيف الفرعي</dt>
                    <dd>{overview.sector_intelligence.taxonomy_record.subsector_id || "غير محدد"}</dd>
                  </div>
                  <div>
                    <dt>فجوات الأدلة</dt>
                    <dd>{overview.sector_intelligence.sector_evidence_map.evidence_gaps.length}</dd>
                  </div>
                </dl>
                <div className="source-list">
                  {overview.sector_intelligence.sector_criteria.criteria.slice(0, 4).map((criterion) => (
                    <article key={criterion.criterion_id}>
                      <strong>{criterion.label}</strong>
                      <span>{criterion.sector_value}</span>
                      <small>{criterion.evidence_status}</small>
                    </article>
                  ))}
                </div>
              </div>

              <div className="panel">
                <div className="section-title">
                  <ShieldCheck size={20} aria-hidden="true" />
                  <h2>التدقيق والعزل</h2>
                </div>
                <dl className="audit-list">
                  <div>
                    <dt>المسار</dt>
                    <dd>{overview.audit.owner_path}</dd>
                  </div>
                  <div>
                    <dt>الشخصيات</dt>
                    <dd>{overview.decision_council.isolation_order.length}</dd>
                  </div>
                  <div>
                    <dt>الجلب الخارجي</dt>
                    <dd>{overview.audit.source_fetch_enabled ? "مفتوح" : "مغلق"}</dd>
                  </div>
                </dl>
              </div>
            </section>

            <section className="builder-grid">
              <div className="panel">
                <div className="section-title">
                  <FileText size={20} aria-hidden="true" />
                  <h2>دفتر الافتراضات</h2>
                </div>
                <div className="assumption-list">
                  {(overview.assumption_book.length ? overview.assumption_book : assumptions).slice(0, 8).map((item) => (
                    <article key={item.assumption_id}>
                      <strong>{item.label}</strong>
                      <span>{item.value} {item.unit}</span>
                      <small>{item.source_type} · {statusText(item.review_status)}</small>
                    </article>
                  ))}
                </div>
              </div>

              <div className="panel">
                <div className="section-title">
                  <Database size={20} aria-hidden="true" />
                  <h2>سجل الأدلة والمصادر</h2>
                </div>
                <div className="source-list">
                  {overview.evidence_register.datasets.slice(0, 3).map((dataset) => {
                    const gate = overview.evidence_register.quality_gates.find((item) => item.dataset_id === dataset.dataset_id);
                    return (
                      <article key={dataset.dataset_id}>
                        <strong>{dataset.title}</strong>
                        <span>{gate?.status ?? dataset.review_status}</span>
                        <small>{dataset.row_count} صف · {dataset.import_method}</small>
                      </article>
                    );
                  })}
                  {overview.evidence_register.source_records.slice(0, 5).map((source) => (
                    <article key={source.source_id}>
                      <strong>{source.publisher}</strong>
                      <span>{source.state}</span>
                    </article>
                  ))}
                </div>
                <p className="muted">
                  روابط الأدلة {overview.evidence_register.evidence_links.length} · أسباب NOT_READY{" "}
                  {overview.evidence_register.not_ready_reasons.length}
                </p>
                <div className="source-list">
                  {overview.evidence_ledger.slice(0, 3).map((ledger) => (
                    <article key={ledger.ledger_id}>
                      <strong>{ledger.target_id}</strong>
                      <span>
                        ثقة {ledger.evidence_confidence_score} · {ledger.evidence_confidence_status}
                      </span>
                      <small>
                        بيانات {ledger.data_quality_status} · تحويل {ledger.transformation_quality_status}
                      </small>
                    </article>
                  ))}
                </div>
                <p className="muted">الجلب الخارجي {overview.evidence_register.external_fetch_enabled ? "مفتوح" : "مغلق"}</p>
              </div>
            </section>

            <section className="builder-grid">
              <div className="panel">
                <div className="section-title">
                  <ShieldCheck size={20} aria-hidden="true" />
                  <h2>بوابات الجاهزية</h2>
                </div>
                <div className="source-list">
                  {overview.readiness_gates.gates.map((gate) => (
                    <article key={gate.gate_id}>
                      <strong>{gate.label}</strong>
                      <span>{statusText(gate.status)}</span>
                      <small>{gate.reasons.length ? gate.reasons.join(" · ") : "passed"}</small>
                    </article>
                  ))}
                </div>
              </div>

              <div className="panel">
                <div className="section-title">
                  <Layers3 size={20} aria-hidden="true" />
                  <h2>خطة التنفيذ</h2>
                </div>
                <dl className="source-summary">
                  <div>
                    <dt>الحالة</dt>
                    <dd>{statusText(overview.execution_plan.status)}</dd>
                  </div>
                  <div>
                    <dt>الأيام</dt>
                    <dd>{overview.execution_plan.estimated_total_duration_days}</dd>
                  </div>
                  <div>
                    <dt>محجوبة</dt>
                    <dd>{overview.execution_plan.blocked_by_gates.length}</dd>
                  </div>
                </dl>
                <div className="source-list">
                  {overview.execution_plan.milestones.slice(0, 5).map((milestone) => (
                    <article key={milestone.phase_id}>
                      <strong>{milestone.phase_id}</strong>
                      <span>{milestone.owner_role} · {milestone.estimated_duration_days} يوم</span>
                      <small>{milestone.dependencies.length ? milestone.dependencies.join(" · ") : "start"}</small>
                    </article>
                  ))}
                </div>
              </div>

              <div className="panel">
                <div className="section-title">
                  <AlertTriangle size={20} aria-hidden="true" />
                  <h2>سجل المخاطر</h2>
                </div>
                <div className="source-list">
                  {overview.risk_register.top_risks.map((risk) => (
                    <article key={risk.risk_id}>
                      <strong>{risk.risk_id}</strong>
                      <span>{risk.severity} · {risk.owner_role}</span>
                      <small>{risk.mitigation}</small>
                    </article>
                  ))}
                </div>
              </div>
            </section>

            <section className="panel">
              <div className="section-title">
                <ShieldCheck size={20} aria-hidden="true" />
                <h2>حزمة القبول r10/r11</h2>
              </div>
              <div className="acceptance-summary">
                <article>
                  <span>الحالة</span>
                  <strong>{overview.acceptance.status === "passed" ? "مقبولة" : "فشلت"}</strong>
                </article>
                <article>
                  <span>ناجحة</span>
                  <strong>{overview.acceptance.passed}</strong>
                </article>
                <article>
                  <span>فاشلة</span>
                  <strong>{overview.acceptance.failed}</strong>
                </article>
              </div>
              <div className="acceptance-list">
                {overview.acceptance.tests.slice(0, 6).map((test) => (
                  <article key={test.test_id}>
                    <strong>{test.test_id}</strong>
                    <span>{test.status}</span>
                    <small>{test.evidence}</small>
                  </article>
                ))}
              </div>
            </section>

            {workspace?.remediation ? (
              <section className="panel">
                <div className="section-title">
                  <AlertTriangle size={20} aria-hidden="true" />
                  <h2>حلقة معالجة العوائق</h2>
                </div>
                <div className="remediation-list">
                  {workspace.remediation.items.length ? (
                    workspace.remediation.items.map((item) => (
                      <article key={item.remediation_id}>
                        <strong>{item.trigger_code}</strong>
                        <span>{item.message}</span>
                        <small>{item.target}</small>
                      </article>
                    ))
                  ) : (
                    <article>
                      <strong>لا توجد مهام مفتوحة</strong>
                      <span>آخر snapshot لا يحتوي عوائق معالجة حرجة.</span>
                    </article>
                  )}
                </div>
              </section>
            ) : null}

            <section className="panel">
              <div className="section-title">
                <ShieldCheck size={20} aria-hidden="true" />
                <h2>حزمة القرار والمراجعة</h2>
              </div>
              {decisionPack ? (
                <div className="decision-stack">
                  <div className="report-box">
                    <strong>{decisionPack.memo.recommendation}</strong>
                    <p>{decisionPack.memo.rationale}</p>
                    <small>
                      Snapshot {decisionPack.snapshot_id} · Review {decisionPack.memo.review_status}
                    </small>
                    <a href={`/api/snapshots/${decisionPack.snapshot_id}/decision-pack.html`} target="_blank" rel="noreferrer">
                      فتح حزمة القرار HTML
                    </a>
                  </div>
                  <div className="button-row">
                    <button disabled={isBusy} onClick={() => handleReviewDecision("approved_local")}>
                      اعتماد محلي
                    </button>
                    <button disabled={isBusy} onClick={() => handleReviewDecision("needs_changes")}>
                      طلب تعديل
                    </button>
                    <button disabled={isBusy} onClick={() => handleReviewDecision("rejected_local")}>
                      رفض محلي
                    </button>
                  </div>
                  <div className="remediation-list">
                    {actionItems.length ? (
                      actionItems.slice(0, 6).map((item) => (
                        <article key={item.action_item_id}>
                          <strong>{item.title}</strong>
                          <span>{item.message || item.recommended_action}</span>
                          <small>
                            {item.source_type} · {item.severity} · {item.status}
                          </small>
                          {item.status === "open" ? (
                            <button disabled={isBusy} onClick={() => handleCloseActionItem(item.action_item_id)}>
                              إغلاق محلي
                            </button>
                          ) : null}
                        </article>
                      ))
                    ) : (
                      <article>
                        <strong>لا توجد بنود مفتوحة</strong>
                        <span>آخر حزمة قرار لا تحتوي بنود معالجة مفتوحة.</span>
                      </article>
                    )}
                  </div>
                </div>
              ) : (
                <div className="report-box">
                  <p>افتح الحزمة لعرض مذكرة القرار، حالة المراجعة، والبنود المفتوحة من نفس snapshot.</p>
                  <button disabled={isBusy} onClick={handleOpenDecisionPack}>
                    فتح حزمة القرار
                  </button>
                </div>
              )}
            </section>

            <section className="content-grid">
              <div className="panel panel--wide">
                <div className="section-title">
                  <Calculator size={20} aria-hidden="true" />
                  <h2>مؤشرات محسوبة من الخلفية</h2>
                </div>
                <div className="metric-grid">
                  {overview.kpis.map((output) => (
                    <MetricCard output={output} key={output.output_id} />
                  ))}
                </div>
              </div>

              <div className="panel">
                <div className="section-title">
                  <AlertTriangle size={20} aria-hidden="true" />
                  <h2>العوائق الظاهرة</h2>
                </div>
                <div className="blocker-list">
                  {overview.blockers.map((blocker) => (
                    <article key={blocker.code}>
                      <strong>{blocker.code}</strong>
                      <p>{blocker.message}</p>
                    </article>
                  ))}
                </div>
              </div>

              <div className="panel">
                <div className="section-title">
                  <FileText size={20} aria-hidden="true" />
                  <h2>تقرير اللقطة</h2>
                </div>
                {report ? (
                  <div className="report-box">
                    <strong>{reportView?.title ?? report.title}</strong>
                    <p>{reportView?.executive_summary.reason ?? report.sections[0]?.body}</p>
                    <small>Snapshot {report.snapshot_id}</small>
                    <a href={`/api/snapshots/${report.snapshot_id}/report.html`} target="_blank" rel="noreferrer">
                      فتح تقرير HTML المحلي
                    </a>
                  </div>
                ) : (
                  <p className="muted">شغّل التقرير لقراءة نفس لقطة التشغيل بدون إعادة حساب.</p>
                )}
              </div>
            </section>
          </>
        ) : null}
        </div>
      </section>
    </main>
  );
}
