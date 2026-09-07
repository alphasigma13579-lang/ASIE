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
import { useEffect, useMemo, useRef, useState, useSyncExternalStore, type FormEvent } from "react";
import { LiveCockpit } from "./LiveCockpit";
import { LocationConsentInput } from "./LocationConsentInput";
import { customerLocationLabel } from "./customerLocationLabels";
import { BrandLockup } from "./BrandMark";
import { CommandCenter } from "./CommandCenter";
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
  createOrganization,
  fetchFundingProfiles,
  fetchMe,
  fetchReleaseRecord,
  fetchSectorProfiles,
  logout,
  openSnapshotDocument,
  type AuthUser,
  type FundingProfile,
  type LoginResponse,
  type Membership,
  type ReleaseRecord,
  type SectorProfile,
} from "./api";
import { AuthScreen } from "./AuthScreens";
import { CustomerLanguageSwitcher, customerBusinessText, customerErrorText, customerNarrativeText, customerSourceName, customerStatusText, useCustomerLanguage } from "./customerLanguage";
import {
  clearSession,
  getActiveOrganizationId,
  getSessionToken,
  getSessionRevision,
  onSessionContextChanged,
  onSessionExpired,
  setActiveOrganizationId,
  setSessionToken,
} from "./session";
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
  { ar: "إنشاء مشروع", en: "Create project" },
  { ar: "مدخلات أساسية", en: "Essential inputs" },
  { ar: "اختيار العمق", en: "Choose detail level" },
  { ar: "تشغيل التقييم", en: "Run assessment" },
  { ar: "مراجعة القرار", en: "Review decision" },
  { ar: "التقرير المحفوظ", en: "Saved report" },
];

type AppStage = "dashboard" | "wizard" | "evidence" | "readiness" | "run" | "reality" | "decision" | "execution" | "architecture" | "snapshots";
type AuthState = "probing" | "anonymous" | "legacy" | "authenticated";
type AppOverlay = "settings" | "profiles" | null;

function overlayFromLocation(): AppOverlay {
  const raw = window.location.hash.replace(/^#/, "");
  return raw === "settings" || raw === "profiles" ? raw : null;
}

const appStages: Array<{ id: AppStage; label: string; labelEn: string; description: string; descriptionEn: string }> = [
  { id: "dashboard", label: "الملخص", labelEn: "Summary", description: "أين وصلنا الآن؟", descriptionEn: "Where are we now?" },
  { id: "wizard", label: "عرّف مشروعك", labelEn: "Set up your project", description: "الفكرة والموقع والأرقام", descriptionEn: "Concept, location, and figures" },
  { id: "evidence", label: "اربط الأدلة", labelEn: "Link evidence", description: "ملفاتك ومصادر الثقة", descriptionEn: "Files and trusted sources" },
  { id: "readiness", label: "افحص النواقص", labelEn: "Check missing inputs", description: "ما يمنع التحليل؟", descriptionEn: "What blocks the analysis?" },
  { id: "run", label: "شغّل التحليل", labelEn: "Run analysis", description: "أنشئ نتيجة قابلة للمراجعة", descriptionEn: "Create a reviewable result" },
  { id: "reality", label: "ذكاء السوق والفرص", labelEn: "Market intelligence", description: "مقارنات وتوصيات بعد الدراسة", descriptionEn: "Comparisons and opportunities after analysis" },
  { id: "decision", label: "افهم القرار", labelEn: "Understand the decision", description: "القرار وأسبابه", descriptionEn: "Decision and reasons" },
  { id: "execution", label: "نفّذ التالي", labelEn: "Next actions", description: "خطوات بعد القرار", descriptionEn: "Actions after the decision" },
  { id: "snapshots", label: "التقارير", labelEn: "Reports", description: "التقارير المحفوظة", descriptionEn: "Saved reports" },
];

const appStageGroups: Array<{ label: string; labelEn: string; stages: AppStage[] }> = [
  { label: "مسار الدراسة", labelEn: "Study journey", stages: ["dashboard", "wizard"] },
  { label: "التحقق قبل التشغيل", labelEn: "Pre-analysis checks", stages: ["evidence", "readiness"] },
  { label: "القرار والتنفيذ", labelEn: "Decision and execution", stages: ["run", "reality", "decision", "execution", "snapshots"] },
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
  { label: "موقع المشروع", labelEn: "Project location", icon: MapPin },
  { label: "القطاع", labelEn: "Sector", icon: Layers3 },
  { label: "التصنيف الدقيق", labelEn: "Detailed category", icon: Target },
  { label: "اسم المشروع", labelEn: "Project name", icon: Rocket },
  { label: "الفجوة والميزة", labelEn: "Market need and advantage", icon: AlertTriangle },
  { label: "الجمهور", labelEn: "Target audience", icon: Users },
  { label: "رأس المال", labelEn: "Available capital", icon: Calculator },
  { label: "طريقة التفاصيل", labelEn: "How to add details", icon: Database },
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
  "سمّ المشروع بلغة بسيطة. الاسم يساعدك لاحقًا في قراءة التقرير.",
  "قل لنا لماذا يحتاج السوق هذا المشروع، وما الذي يجعله مختلفًا.",
  "حدد من سيدفع أو يستفيد: أفراد، مؤسسات، شركات، أو مزيج.",
  "ابدأ برأس المال المتاح. لا تحتاج كل التفاصيل من أول دقيقة.",
  "اختر كيف تريد تعبئة باقي الأرقام: بنفسك، من ملف، أو بمساعدة تقديرية عند تفعيلها.",
];
const wizardStepHelpEnglish = [
  "Start with the place. Location shapes the market, competitors, and costs.",
  "Choose the project's broad sector, such as health, education, retail, or technology.",
  "Choose a precise category so the analysis is not overly general.",
  "Give the project a clear name that will remain recognizable in reports.",
  "Explain why the market needs this project and what makes it different.",
  "Identify who will pay or benefit: individuals, organizations, businesses, or a mix.",
  "Start with the available capital; you do not need every detail immediately.",
  "Choose how to provide the remaining figures: manually, from a file, or through assisted estimates when available.",
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

function governedNameError(value: string, label: string, minimumLength = 3, maximumLength = 60, locale: "ar" | "en" = "ar"): string | null {
  const normalized = value.trim().replace(/\s+/g, " ");
  if (normalized.length < minimumLength) return locale === "ar" ? `${label} قصير جدًا.` : `${label} is too short.`;
  if (normalized.length > maximumLength) return locale === "ar" ? `${label} طويل جدًا؛ الحد الأقصى ${maximumLength} حرفًا.` : `${label} is too long; the maximum is ${maximumLength} characters.`;
  if (!/^[\p{L}\p{N}][\p{L}\p{N}\s'’\-ـ]*$/u.test(normalized)) {
    return locale === "ar" ? `${label} يجب أن يحتوي على حروف وأرقام ومسافات فقط.` : `${label} may contain letters, numbers, spaces, apostrophes, and hyphens only.`;
  }
  if (/(.)\1{2,}/u.test(normalized) || /^(.{1,4})\1{2,}$/u.test(normalized)) {
    return locale === "ar" ? `${label} يحتوي على تكرار غير مقبول للحروف أو المقاطع.` : `${label} contains an invalid repeated pattern.`;
  }
  const distinctLetters = new Set((normalized.match(/\p{L}/gu) ?? []).map((letter) => letter.toLocaleLowerCase(locale === "ar" ? "ar-SA" : "en-US")));
  if (distinctLetters.size < 2) return locale === "ar" ? `${label} غير واضح؛ اكتب اسمًا حقيقيًا ومفهومًا.` : `${label} is unclear; enter a meaningful name.`;
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
  { id: "identity", label: "هوية المشروع وموقعه", labelEn: "Project identity and location", keys: ["primary_sector_id", "subsector_id", "activity_description", "location_scope", "location_country", "location_region", "location_city", "location_district", "location_latitude", "location_longitude"] },
  { id: "market", label: "السوق والميزة والجمهور", labelEn: "Market, advantage, and audience", keys: ["gap_statement", "competitive_edge", "target_audience", "intake_mode"] },
  { id: "operations", label: "التشغيل والطاقة", labelEn: "Operations and capacity", keys: ["monthly_units", "use_operating_capacity", "capacity_units_per_day", "operating_days_per_month", "utilization_rate"] },
  { id: "finance", label: "التكاليف والإيرادات", labelEn: "Costs and revenue", keys: ["capital_available", "startup_cost", "monthly_fixed_cost", "unit_price", "variable_cost", "payroll_monthly", "rent_monthly", "utilities_monthly", "marketing_monthly", "maintenance_monthly", "capex_equipment", "capex_fitout", "capex_licenses_local", "depreciation_years", "equity_contribution"] },
  { id: "funding", label: "التمويل والخصم", labelEn: "Funding and discounting", keys: ["loan_grace_months", "annual_discount_rate", "working_capital_months", "debt_amount", "annual_interest_rate", "loan_years"] },
];

const assumptionEnglishLabels: Record<string, string> = {
  primary_sector_id: "Sector",
  subsector_id: "Detailed activity",
  activity_description: "Activity description",
  location_scope: "Market scope",
  location_country: "Country",
  location_region: "Region",
  location_city: "City",
  location_district: "District or street",
  location_latitude: "Latitude",
  location_longitude: "Longitude",
  gap_statement: "Market need",
  competitive_edge: "Competitive advantage",
  target_audience: "Target audience",
  intake_mode: "Detail entry method",
  capital_available: "Available capital",
  startup_cost: "Startup cost",
  monthly_fixed_cost: "Monthly fixed costs",
  other_monthly_costs: "Other monthly costs",
  unit_price: "Sale or service price",
  variable_cost: "Service delivery cost",
  monthly_units: "Monthly customers or orders",
  use_operating_capacity: "Use operating capacity",
  capacity_units_per_day: "Daily operating capacity",
  operating_days_per_month: "Operating days per month",
  utilization_rate: "Capacity utilization",
  payroll_monthly: "Monthly payroll",
  rent_monthly: "Monthly rent",
  utilities_monthly: "Monthly utilities",
  marketing_monthly: "Monthly marketing",
  maintenance_monthly: "Monthly maintenance",
  capex_equipment: "Equipment cost",
  capex_fitout: "Fit-out cost",
  capex_licenses_local: "License cost",
  depreciation_years: "Depreciation years",
  equity_contribution: "Owner contribution",
  loan_grace_months: "Grace period",
  annual_discount_rate: "Annual discount rate",
  working_capital_months: "Working capital months",
  debt_amount: "Loan amount",
  annual_interest_rate: "Annual financing cost",
  loan_years: "Loan term",
};

function assumptionLabel(item: AssumptionRecord, locale: "ar" | "en"): string {
  return locale === "ar"
    ? assumptionArabicLabels[item.input_key] ?? customerBusinessText(item.label, locale)
    : assumptionEnglishLabels[item.input_key] ?? customerBusinessText(item.label, locale);
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

type ProjectFormInputs = Omit<Required<ProjectInputs>, "location_latitude" | "location_longitude">
  & Pick<ProjectInputs, "location_latitude" | "location_longitude">;

const defaultInputs: ProjectFormInputs = {
  primary_sector_id: "",
  subsector_id: "",
  activity_description: "",
  location_scope: "المملكة العربية السعودية",
  location_country: "SA",
  location_region: "",
  location_city: "",
  location_district: "",
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
};

function formatValue(output: OutputEnvelope, locale: "ar" | "en" = "ar"): string {
  if (output.value === null) return "—";
  if (typeof output.value === "string") return output.value;
  if (output.unit === "percent") return `${Math.round(output.value * 1000) / 10}%`;
  if (output.unit === "SAR") {
    return new Intl.NumberFormat(locale === "ar" ? "ar-SA" : "en-US", {
      style: "currency",
      currency: "SAR",
      maximumFractionDigits: 0,
    }).format(output.value);
  }
  return new Intl.NumberFormat(locale === "ar" ? "ar-SA" : "en-US", { maximumFractionDigits: 2 }).format(output.value);
}

function statusText(status: string, locale: "ar" | "en" = "ar"): string {
  return customerStatusText(status, locale);
}

function metricTitle(id: string, locale: "ar" | "en"): string {
  const titles: Record<string, { ar: string; en: string }> = {
    "startup-cost": { ar: "تكلفة التأسيس", en: "Setup cost" },
    "monthly-revenue": { ar: "الإيراد الشهري", en: "Monthly revenue" },
    "monthly-profit": { ar: "صافي شهري تقديري", en: "Estimated monthly net" },
    "break-even-units": { ar: "وحدات التعادل", en: "Break-even units" },
    "funding-gap": { ar: "فجوة التمويل", en: "Funding gap" },
    "working-capital-need": { ar: "احتياج رأس المال العامل", en: "Working capital need" },
    ebitda: { ar: "الربح التشغيلي قبل الاستهلاك والفوائد والضرائب", en: "Operating earnings before depreciation, interest, and tax" },
    ebit: { ar: "الربح التشغيلي قبل الفوائد والضرائب", en: "Operating earnings before interest and tax" },
    "net-operating-cashflow": { ar: "التدفق التشغيلي الصافي", en: "Net operating cash flow" },
    "funding-need-after-equity": { ar: "احتياج التمويل بعد رأس المال", en: "Funding need after owner capital" },
    "depreciation-monthly": { ar: "الإهلاك الشهري", en: "Monthly depreciation" },
    dscr: { ar: "قدرة المشروع على تغطية أقساط الدين", en: "Debt payment coverage" },
    npv: { ar: "صافي القيمة الحالية", en: "Net present value" },
    irr: { ar: "معدل العائد الداخلي", en: "Internal rate of return" },
    "payback-months": { ar: "مدة الاسترداد", en: "Payback period" },
    "contribution-margin": { ar: "هامش المساهمة", en: "Contribution margin" },
    "debt-service-monthly": { ar: "خدمة الدين الشهرية", en: "Monthly debt payment" },
    "mc-feasibility-gate-probability": { ar: "احتمال اجتياز متطلبات الجدوى", en: "Probability of meeting feasibility requirements" },
  };
  return titles[id]?.[locale] ?? (locale === "ar" ? "مؤشر محسوب" : "Calculated metric");
}

function MetricCard({ output }: { output: OutputEnvelope }) {
  const { locale, text } = useCustomerLanguage();
  return (
    <article className="metric-card">
      <div className="metric-card__top">
        <span className="metric-card__owner">{text("مؤشر محسوب", "Calculated metric")}</span>
        <BadgeCheck size={18} aria-hidden="true" />
      </div>
      <strong>{metricTitle(output.output_id, locale)}</strong>
      <div className="metric-card__value">{formatValue(output, locale)}</div>
      <p className="metric-card__status">{statusText(output.status, locale)}</p>
    </article>
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
  inputId,
}: {
  label: string;
  value: number;
  onChange: (nextValue: number) => void;
  inputId?: string;
}) {
  const { text } = useCustomerLanguage();
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
          id={inputId}
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
          <button type="button" tabIndex={-1} aria-label={`${text("زيادة", "Increase")} ${label}`} onMouseDown={(event) => event.preventDefault()} onClick={() => stepValue(1)}>▲</button>
          <button type="button" tabIndex={-1} aria-label={`${text("إنقاص", "Decrease")} ${label}`} onMouseDown={(event) => event.preventDefault()} onClick={() => stepValue(-1)}>▼</button>
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
  const { direction, text } = useCustomerLanguage();
  return (
    <main id="main-content" className="app-shell app-shell--center" aria-busy="true" dir={direction}>
      <Activity className="spin" size={28} aria-hidden="true" />
      <p>{text("جارٍ تجهيز مساحة العمل...", "Preparing your workspace...")}</p>
    </main>
  );
}

function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  const { direction, text } = useCustomerLanguage();
  return (
    <main id="main-content" className="app-shell app-shell--center" role="alert" dir={direction}>
      <AlertTriangle size={32} aria-hidden="true" />
      <h1>{text("تعذر تجهيز مساحة العمل", "The workspace could not be prepared")}</h1>
      <p>{message}</p>
      <button className="primary-button" onClick={onRetry}>
        <RefreshCw size={18} aria-hidden="true" />
        {text("إعادة المحاولة", "Try again")}
      </button>
    </main>
  );
}

/** Reset the entire in-memory workspace, not only the transient GPS child. */
export function App() {
  const revision = useSyncExternalStore(onSessionContextChanged, getSessionRevision);
  return <SessionWorkspace key={revision} />;
}

function SessionWorkspace() {
  const { locale, direction, text } = useCustomerLanguage();
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
  const [authState, setAuthState] = useState<AuthState>("probing");
  const [authInitialMode, setAuthInitialMode] = useState<"login" | "register">("login");
  const [authUser, setAuthUser] = useState<AuthUser | null>(null);
  const [memberships, setMemberships] = useState<Membership[]>([]);
  const [activeOrganizationId, setActiveOrganizationState] = useState<string>(() => getActiveOrganizationId());
  const [overlay, setOverlay] = useState<AppOverlay>(() => overlayFromLocation());
  const [fundingProfiles, setFundingProfiles] = useState<FundingProfile[]>([]);
  const [sectorProfiles, setSectorProfiles] = useState<SectorProfile[]>([]);
  const [releaseRecord, setReleaseRecord] = useState<ReleaseRecord | null>(null);
  const [newOrganizationName, setNewOrganizationName] = useState("");
  const [isBusy, setIsBusy] = useState(false);
  const [hasEnteredProduct, setHasEnteredProduct] = useState(() => readLocalFlag(PRODUCT_ENTRY_STORAGE_KEY));
  const [legalAccepted, setLegalAccepted] = useState(() => readLocalFlag(LEGAL_ACCEPTANCE_STORAGE_KEY));
  const [stage, setStage] = useState<AppStage>(() => stageFromLocation());
  const [pageDirection, setPageDirection] = useState<"forward" | "back">("forward");
  const lastStageRef = useRef<AppStage>("dashboard");
  const historyNavigationRef = useRef(false);
  const [wizardStep, setWizardStep] = useState(0);
  const [maxUnlockedWizardStep, setMaxUnlockedWizardStep] = useState(0);
  const [missingInputReturnStage, setMissingInputReturnStage] = useState<AppStage | null>(() => {
    const stored = window.sessionStorage.getItem("asie.sanad.return_stage") as AppStage | null;
    return stored && appStages.some((item) => item.id === stored) ? stored : null;
  });
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
  const firstIncompleteWizardStep = wizardJourney.findIndex((_, index) => Boolean(validateWizardStepAt(index)));
  const firstMissingInputLabel = firstIncompleteWizardStep >= 0
    ? validateWizardStepAt(firstIncompleteWizardStep)
    : readinessBlocked[0]?.message ?? null;
  const firstMissingInputTarget = firstIncompleteWizardStep >= 0
    ? missingInputTargetForStep(firstIncompleteWizardStep)
    : "";
  const commandAction = !project
    ? { label: text("ابدأ تعريف المشروع", "Set up the project"), detail: text("لم تُنشأ مسودة مشروع بعد.", "No project draft has been created yet."), stage: "wizard" as AppStage, action: "navigate" as const }
    : !readiness
      ? { label: text("اربط أدلة المشروع", "Link project evidence"), detail: text("أضف ما يثبت أرقامك قبل فحص الجاهزية.", "Add support for your figures before checking readiness."), stage: "evidence" as AppStage, action: "navigate" as const }
      : !readiness.ready_to_run
        ? { label: text("عالج متطلبات الجاهزية", "Complete readiness requirements"), detail: `${readinessBlocked.length} ${text("متطلبًا يحتاج انتباهك قبل التشغيل.", "requirements need your attention before analysis.")}`, stage: "readiness" as AppStage, action: "navigate" as const }
        : !snapshotOverview
          ? { label: text("شغّل التحليل", "Run analysis"), detail: text("المشروع جاهز لإنشاء أول نتيجة محفوظة.", "The project is ready to create its first saved result."), stage: "run" as AppStage, action: "run" as const }
          : { label: text("افتح ذكاء السوق والفرص", "Open market intelligence"), detail: text("اقرأ المقارنات والفرص بعد ظهور نتيجة الدراسة.", "Review comparisons and opportunities after the analysis result is available."), stage: "reality" as AppStage, action: "navigate" as const };

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
    value: string | number | undefined
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
    const handleNavigateToMissingInput = () => {
      const stored = window.sessionStorage.getItem("asie.sanad.return_stage") as AppStage | null;
      if (stored && appStages.some((item) => item.id === stored)) setMissingInputReturnStage(stored);
      const incompleteStep = wizardJourney.findIndex((_, index) => Boolean(validateWizardStepAt(index)));
      if (incompleteStep >= 0) {
        const targetId = missingInputTargetForStep(incompleteStep);
        unlockAndOpenWizardStep(incompleteStep);
        setStage("wizard");
        focusWizardTarget(targetId);
        return;
      }
      setStage("readiness");
    };
    window.addEventListener("asie:navigate-missing-input", handleNavigateToMissingInput);
    return () => window.removeEventListener("asie:navigate-missing-input", handleNavigateToMissingInput);
  });

  useEffect(() => {
    let cancelled = false;
    async function probeSession() {
      const token = getSessionToken();
      try {
        const me = await fetchMe();
        if (cancelled) return;
        if (token) {
          setAuthUser({ user_id: me.user_id, display_name: "", email: "", platform_role: me.platform_role });
          setMemberships(me.memberships ?? []);
          const nextOrganization = getActiveOrganizationId() || me.memberships?.[0]?.organization_id || "";
          if (nextOrganization) setActiveOrganizationId(nextOrganization);
          setActiveOrganizationState(nextOrganization);
          setAuthState("authenticated");
        } else {
          setAuthState(me.user_id === "local_legacy_operator" ? "legacy" : "anonymous");
        }
      } catch {
        if (!cancelled) setAuthState("anonymous");
      }
    }
    void probeSession();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(
    () =>
      onSessionExpired(() => {
        setAuthInitialMode("login");
        setAuthState("anonymous");
        setAuthUser(null);
        setMemberships([]);
        setActiveOrganizationState("");
      }),
    []
  );

  function handleAuthenticated(response: LoginResponse) {
    // The new workspace re-reads /auth/me before loading any scoped data.
    setSessionToken(response.access_token);
  }

  async function handleLogout() {
    const revision = getSessionRevision();
    try {
      await logout();
    } catch {
      // Local cleanup is still required if the current session cannot log out.
    }
    // A delayed logout must never clear a newer identity/organization lifetime.
    if (revision === getSessionRevision()) {
      setAuthInitialMode("login");
      clearSession();
    }
  }

  function switchOrganization(organizationId: string) {
    // Effective changes remount all workspace state; same-context clicks do not.
    setActiveOrganizationId(organizationId);
  }

  function openOverlay(next: Exclude<AppOverlay, null>) {
    setOverlay(next);
    window.history.pushState({ asie_stage: lastStageRef.current, asie_overlay: next }, "", `#${next}`);
    if (next === "profiles" && !fundingProfiles.length) {
      void (async () => {
        try {
          const [funding, sector] = await Promise.all([fetchFundingProfiles(), fetchSectorProfiles()]);
          setFundingProfiles(funding);
          setSectorProfiles(sector);
        } catch (err) {
          setError(customerErrorText(err, locale));
        }
      })();
    }
  }

  function closeOverlay() {
    setOverlay(null);
    window.history.pushState({ asie_stage: lastStageRef.current }, "", `#${lastStageRef.current}`);
  }

  async function handleOpenDocument(snapshotId: string, suffix: string, mode: "open" | "download") {
    setError(null);
    try {
      await openSnapshotDocument(snapshotId, suffix, mode, locale);
    } catch (err) {
      setError(customerErrorText(err, locale));
    }
  }

  async function handleShowRelease(snapshotId: string) {
    setError(null);
    try {
      setReleaseRecord(await fetchReleaseRecord(snapshotId));
    } catch (err) {
      setError(customerErrorText(err, locale));
    }
  }

  async function handleCreateOrganization(event: FormEvent) {
    event.preventDefault();
    if (!newOrganizationName.trim()) return;
    setIsBusy(true);
    setError(null);
    try {
      const organization = await createOrganization(newOrganizationName.trim());
      setNewOrganizationName("");
      setMemberships((current) => [...current, { organization_id: organization.organization_id, organization_name: organization.name, role: "organization_owner" }]);
      switchOrganization(organization.organization_id);
    } catch (err) {
      setError(customerErrorText(err, locale));
    } finally {
      setIsBusy(false);
    }
  }

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
      setError(customerErrorText(err, locale));
    }
  }

  useEffect(() => {
    // Do not hit scoped routes before the session probe resolves; legacy mode
    // (zero users) and authenticated sessions load immediately after.
    if (authState === "authenticated" || authState === "legacy") {
      void loadPolicy();
    }
  }, [authState]);

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
      setError(customerErrorText(err, locale));
    } finally {
      setIsBusy(false);
    }
  }

  async function handleApproveAssumptions(items: AssumptionRecord[]) {
    if (!project) {
      setError(text("احفظ بيانات المشروع أولًا قبل اعتماد الافتراضات.", "Save the project before approving assumptions."));
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
      setError(customerErrorText(err, locale));
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
      setError(customerErrorText(err, locale));
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
      setError(customerErrorText(err, locale));
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
      setError(customerErrorText(err, locale));
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
      setError(customerErrorText(err, locale));
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
      setError(customerErrorText(err, locale));
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
      setError(customerErrorText(err, locale));
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
      setFileImportStatus(`${dataset.title} · ${dataset.row_count} ${text("صف", "rows")} · ${dataset.columns.length} ${text("أعمدة", "columns")}`);
      if (project) {
        await loadProjectWorkspace(project.project_id);
      }
    } catch (err) {
      setError(customerErrorText(err, locale));
    } finally {
      setIsBusy(false);
    }
  }

  async function handleCreateTransformation() {
    const dataset = datasets.find((item) => item.dataset_id === selectedDatasetId);
    if (!dataset) {
      setError(text("اختر مجموعة بيانات أولًا قبل إنشاء التحويل.", "Select a dataset before creating a transformation."));
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
      setError(customerErrorText(err, locale));
    } finally {
      setIsBusy(false);
    }
  }

  async function handleReviewSelectedDataset(reviewStatus: "approved_for_use" | "rejected") {
    const dataset = selectedDataset;
    if (!dataset) {
      setError(text("اختر مجموعة بيانات أولًا قبل المراجعة.", "Select a dataset before review."));
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
      setError(customerErrorText(err, locale));
    } finally {
      setIsBusy(false);
    }
  }

  async function handleReviewSelectedTransformation(reviewStatus: "approved" | "review_required" | "rejected") {
    const transformation = transformations.find((item) => item.transformation_id === selectedTransformationId);
    if (!selectedDataset || !transformation) {
      setError(text("اختر التحويل أولًا قبل المراجعة.", "Select a transformation before review."));
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
      setError(customerErrorText(err, locale));
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
      setError(text("لا توجد مجموعة بيانات معتمدة أو افتراض متاح للربط.", "No approved dataset or available assumption can be linked."));
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
      setError(customerErrorText(err, locale));
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
      setError(text("لا توجد مجموعة بيانات معتمدة أو متطلب قطاعي يحتاج دليلًا.", "No approved dataset or sector requirement needs evidence."));
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
      setError(customerErrorText(err, locale));
    } finally {
      setIsBusy(false);
    }
  }

  function missingInputTargetForStep(step: number): string {
    if (step === 0) {
      if (!saudiCitiesByRegion[form.inputs.location_region]) return "wizard-location-region";
      if (!(saudiCitiesByRegion[form.inputs.location_region] ?? []).includes(form.inputs.location_city)) return "wizard-location-city";
      return "wizard-location-district";
    }
    if (step === 1) return form.inputs.primary_sector_id === "CUSTOM" ? "wizard-custom-sector" : "wizard-sector-choices";
    if (step === 2) return showCustomSubsector ? "wizard-custom-subsector" : "wizard-subsector-choices";
    if (step === 3) return "wizard-project-name";
    if (step === 4) return form.inputs.gap_statement?.trim() ? "wizard-advantage-choices" : "wizard-gap-choices";
    if (step === 5) return "wizard-audience-choices";
    if (step === 6) return "wizard-capital-amount";
    if (step === 7) {
      if (!form.inputs.intake_mode?.trim()) return "wizard-intake-choices";
      if (form.inputs.intake_mode === "file") return "wizard-data-file";
      if (form.inputs.startup_cost <= 0) return "wizard-startup-cost";
      if (form.inputs.unit_price <= 0) return "wizard-unit-price";
      if (form.inputs.monthly_units <= 0) return "wizard-monthly-units";
      if (form.inputs.variable_cost > form.inputs.unit_price) return "wizard-variable-cost";
      if (form.inputs.annual_discount_rate <= 0) return "wizard-discount-rate";
      if (form.inputs.debt_amount > 0 && form.inputs.annual_interest_rate <= 0) return "wizard-interest-rate";
      if (form.inputs.debt_amount > 0 && form.inputs.loan_years <= 0) return "wizard-loan-years";
      return "assumption-human-review";
    }
    return "";
  }

  function focusWizardTarget(targetId: string) {
    if (!targetId) return;
    window.setTimeout(() => {
      const container = document.getElementById(targetId);
      const candidate = container?.matches("input, select, button, textarea")
        ? container
        : container?.querySelector<HTMLElement>("input:not([disabled]), select:not([disabled]), button:not([disabled]), textarea:not([disabled])");
      candidate?.focus({ preventScroll: true });
      (candidate ?? container)?.scrollIntoView({ behavior: "smooth", block: "center" });
    }, 80);
  }

  function rememberMissingInputReturnStage(candidate: AppStage) {
    if (candidate === "wizard") return;
    window.sessionStorage.setItem("asie.sanad.return_stage", candidate);
    setMissingInputReturnStage(candidate);
  }

  function returnToMissingInputOrigin() {
    const target = missingInputReturnStage;
    window.sessionStorage.removeItem("asie.sanad.return_stage");
    setMissingInputReturnStage(null);
    if (target) setStage(target);
  }

  function validateWizardStepAt(step: number): string | null {
    if (step === 0 && !saudiCitiesByRegion[form.inputs.location_region]) return text("اختر المنطقة من القائمة المعتمدة.", "Select a region from the approved list.");
    if (step === 0 && !(saudiCitiesByRegion[form.inputs.location_region] ?? []).includes(form.inputs.location_city)) return text("اختر المدينة من القائمة.", "Select a city from the list.");
    if (step === 0 && form.inputs.location_district?.trim()) {
      const districtError = governedNameError(form.inputs.location_district, text("اسم الحي أو الشارع", "District or street"), 2, 50, locale);
      if (districtError) return districtError;
    }
    if (step === 1 && !form.inputs.primary_sector_id?.trim()) return text("اختر القطاع أو أضف قطاعك.", "Select a sector or add your own.");
    if (step === 1 && form.inputs.primary_sector_id === "CUSTOM" && !form.sector.trim()) return text("اكتب اسم القطاع.", "Enter the sector name.");
    if (step === 2 && !form.inputs.subsector_id?.trim()) return text("اختر التصنيف الدقيق أو أضف تصنيفك.", "Select a detailed category or add your own.");
    if (step === 3) {
      const nameError = governedNameError(form.name, text("اسم المشروع", "Project name"), 3, 60, locale);
      if (nameError) return nameError;
    }
    if (step === 4 && !form.inputs.gap_statement?.trim()) return text("حدد الفجوة التي يعالجها المشروع.", "Identify the market need addressed by the project.");
    if (step === 4 && !form.inputs.competitive_edge?.trim()) return text("حدد الميزة التي يقدمها المشروع.", "Identify the project’s advantage.");
    if (step === 5 && !form.inputs.target_audience?.trim()) return text("اختر جمهور المشروع.", "Select the project audience.");
    if (step === 6 && (!Number.isFinite(form.inputs.capital_available) || form.inputs.capital_available <= 0)) {
      return text("اختر رأس المال المتاح أو اكتب مبلغًا أكبر من صفر.", "Select the available capital or enter an amount greater than zero.");
    }
    if (step === 7 && !form.inputs.intake_mode?.trim()) return text("اختر طريقة تعبئة تفاصيل المشروع.", "Select how you want to provide project details.");
    if (step === 7 && form.inputs.intake_mode === "file" && !fileImportStatus && datasets.length === 0) {
      return text("ارفع ملف بيانات قبل فحص النواقص.", "Upload a data file before checking gaps.");
    }
    if (step === 7 && form.inputs.intake_mode === "manual") {
      if (form.inputs.startup_cost <= 0) return text("اكتب تكلفة التأسيس التقريبية.", "Enter the estimated setup cost.");
      if (form.inputs.unit_price <= 0) return text("اكتب سعر البيع أو الخدمة.", "Enter the product or service price.");
      if (form.inputs.monthly_units <= 0) return text("اكتب عدد العملاء أو الطلبات شهريًا.", "Enter the monthly number of customers or orders.");
      if (form.inputs.variable_cost > form.inputs.unit_price) return text("تكلفة تقديم الخدمة لا ينبغي أن تتجاوز سعر البيع دون توضيح.", "The delivery cost should not exceed the selling price without an explanation.");
      if (form.inputs.annual_discount_rate <= 0) return text("اكتب معدل الخصم السنوي المستخدم في التقييم.", "Enter the annual discount rate used in the assessment.");
      if (form.inputs.working_capital_months < 0) return text("أشهر رأس المال العامل لا يمكن أن تكون سالبة.", "Working-capital months cannot be negative.");
      if (form.inputs.debt_amount > 0 && form.inputs.annual_interest_rate <= 0) return text("اكتب معدل تكلفة التمويل للقرض.", "Enter the annual financing cost for the loan.");
      if (form.inputs.debt_amount > 0 && form.inputs.loan_years <= 0) return text("اكتب مدة القرض بالسنوات.", "Enter the loan term in years.");
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
    rememberMissingInputReturnStage("readiness");
    setMaxUnlockedWizardStep((current) => Math.max(current, target));
    setWizardStep(target);
    setStage("wizard");
    setError(null);
    focusWizardTarget(missingInputTargetForStep(target));
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
        <nav className="landing-nav" aria-label={text("تنقل صفحة ASIE", "ASIE landing navigation")}>
          <BrandLockup subtitle={text("مرصد القرار المحلي", "Local decision workspace")} />
          <div className="landing-nav__status"><span /> {text("وضع محلي محكوم", "Governed local mode")}</div>
          <div className="landing-nav__actions"><button className="landing-nav__link" onClick={() => { writeLocalFlag(PRODUCT_ENTRY_STORAGE_KEY, true); setHasEnteredProduct(true); }}>{text("دخول المساحة", "Enter workspace")}</button></div>
        </nav>
        <section className="landing-hero landing-hero--immersive">
          <div className="landing-copy">
            <p className="landing-kicker"><Sparkles size={16} aria-hidden="true" /> {text("من الدليل إلى قرار يمكن الرجوع إليه", "From evidence to a decision you can revisit")}</p>
            <h1>{text("لا تبحث عن رقمٍ جميل.", "Do not chase a flattering number.")}<br /><em>{text("ابنِ قرارًا تعرف لماذا تثق به.", "Build a decision you understand and trust.")}</em></h1>
            <p className="landing-lede">
              {text("مساحة عمل تحول مشروعك إلى رحلة منظمة: مدخلات، أدلة، جاهزية، ثم نتيجة محفوظة تربط القرار بأسبابه.", "A workspace that turns your project into a structured journey: inputs, evidence, readiness, and a saved result linked to its reasons.")}
            </p>
            <div className="landing-actions">
              <button className="primary-button primary-button--large landing-cta" onClick={() => { writeLocalFlag(PRODUCT_ENTRY_STORAGE_KEY, true); setHasEnteredProduct(true); }}>
                <Rocket size={20} aria-hidden="true" />
                {text("ابدأ مساحة المشروع", "Open project workspace")}
              </button>
              <a className="landing-text-link" href="#decision-flow">{text("شاهد كيف تعمل المنصة", "See how the platform works")} <ArrowLeft size={17} aria-hidden="true" /></a>
            </div>
            <div className="trust-row" aria-label={text("ضمانات ASIE", "ASIE safeguards")}>
              <span><ShieldCheck size={16} aria-hidden="true" /> {text("لا اتصال خارجي في الوضع الحالي", "No external connection in the current mode")}</span>
              <span><Database size={16} aria-hidden="true" /> {text("أدلة محلية", "Local evidence")}</span>
              <span><BadgeCheck size={16} aria-hidden="true" /> {text("نتيجة محفوظة لا تتغير", "Saved result does not change")}</span>
            </div>
          </div>
          <div className="decision-orbit" aria-label={text("تصور توضيحي لرحلة القرار", "Decision journey illustration")}>
            <div className="orbit-glow" />
            <div className="orbit-ring orbit-ring--one" />
            <div className="orbit-ring orbit-ring--two" />
            <div className="signal signal--one" /><div className="signal signal--two" /><div className="signal signal--three" />
            <article className="orbit-core">
              <span className="orbit-core__label">{text("قرار المشروع", "Project decision")}</span>
              <strong>{text("قيد البناء", "In progress")}</strong>
              <small>{text("بيانات توضيحية فقط", "Illustrative data only")}</small>
            </article>
            <article className="float-card float-card--evidence"><Database size={18} /><div><span>{text("الأدلة", "Evidence")}</span><strong>{text("مراجعة محلية", "Local review")}</strong></div><i /></article>
            <article className="float-card float-card--readiness"><CheckCircle2 size={18} /><div><span>{text("الجاهزية", "Readiness")}</span><strong>{text("تحقق قبل التشغيل", "Check before analysis")}</strong></div></article>
            <article className="float-card float-card--snapshot"><Layers3 size={18} /><div><span>{text("نتيجة محفوظة", "Saved result")}</span><strong>{text("مرجع ثابت", "Fixed reference")}</strong></div></article>
            <span className="orbit-caption">{text("تصور توضيحي لا يمثل بيانات مشروع حقيقية", "Illustration only; it does not represent real project data")}</span>
          </div>
        </section>
        <section className="service-ribbon" aria-label={text("خدمات المنصة", "Platform services")}>
          {[
            [text("إدخال موجّه", "Guided input"), text("نسألك فقط عما يحتاجه القرار", "We ask only for what the decision needs"), Target],
            [text("دليل قابل للتتبع", "Traceable evidence"), text("اربط البيانات بمصدرها ومراجعتها", "Link data to its source and review"), Database],
            [text("جاهزية واضحة", "Clear readiness"), text("اعرف النواقص قبل تشغيل التحليل", "Know what is missing before analysis"), CheckCircle2],
            [text("مراجعة بشرية", "Human review"), text("مراجعة مستقلة لا تغيّر الحقائق", "Independent review that does not change facts"), Users],
          ].map(([title, body, Icon]) => {
            const ServiceIcon = Icon as typeof Target;
            return <article key={title as string}><ServiceIcon size={20} aria-hidden="true" /><div><strong>{title as string}</strong><span>{body as string}</span></div></article>;
          })}
        </section>
        <section className="decision-flow" id="decision-flow">
          <div className="decision-flow__intro"><p className="eyebrow">{text("رحلة واحدة بلا مسارات خفية", "One journey with no hidden paths")}</p><h2>{text("تنظم المنصة سؤال القرار بدل توليد إجابة بلا تفسير.", "The platform structures the decision question instead of generating an unexplained answer.")}</h2></div>
          <div className="decision-flow__steps">
            {[
              ["01", text("عرّف المشروع", "Set up the project"), text("حدد النطاق والقطاع والهدف قبل التفاصيل.", "Define scope, sector, and purpose before details.")],
              ["02", text("اربط ما تعرفه", "Link what you know"), text("أضف بيانات محلية ومصدرًا واضحًا لكل مدخل.", "Add local data and a clear source for every input.")],
              ["03", text("تحقق من الجاهزية", "Check readiness"), text("تظهر العوائق كما هي دون إخفاء.", "See blockers clearly without concealment.")],
              ["04", text("شغّل وراجع", "Run and review"), text("يرتبط القرار وتفسيره بنتيجة محفوظة واحدة.", "Decision and explanation link to one saved result.")],
            ].map(([number, title, body]) => <article key={number}><span>{number}</span><h3>{title}</h3><p>{body}</p></article>)}
          </div>
        </section>
      </main>
    );
  }

  // Beta fix: an unauthenticated first visit fails loadPolicy with 401 —
  // the auth gate below must win over the generic error gate, otherwise the
  // sign-in screen is unreachable behind "الخدمة المحلية غير جاهزة".
  if (authState === "probing") {
    return <LoadingState />;
  }

  if (authState === "anonymous") {
    return <AuthScreen initialMode={authInitialMode} onAuthenticated={handleAuthenticated} />;
  }

  if (error && !sourcePolicy) return <ErrorState message={error} onRetry={loadPolicy} />;
  if (!sourcePolicy) return <LoadingState />;

  if (!legalAccepted) {
    return (
      <main id="main-content" className="legal-page">
        <section className="legal-card">
          <BrandLockup subtitle={text("خطوة أخيرة قبل البدء", "One final step before starting")} landing />
          <p className="eyebrow">{text("موافقة استخدام النسخة التجريبية", "Beta use acknowledgement")}</p>
          <h1>{text("راجع حدود النسخة قبل استخدام المنصة", "Review the beta limits before using the platform")}</h1>
          <p className="muted">{text("تحفظ هذه الخطوة موافقتك داخل حسابك ولا تضيف اشتراكًا أو صلاحيات جديدة.", "This step stores your acknowledgement in your account; it does not add a subscription or new permissions.")}</p>
          <div className="legal-list">
            {[
              [text("الخصوصية", "Privacy"), text("لا يجري اتصال خارجي في الوضع الحالي، وتبقى مفاتيح الخدمات خارج الواجهة.", "No external connection occurs in the current mode, and service credentials remain outside the interface.")],
              [text("ملكية البيانات", "Data ownership"), text("يبقى مشروعك وبياناته داخل بيئة التشغيل المخصصة.", "Your project and its data remain inside the designated operating environment.")],
              [text("حوكمة المصادر", "Source governance"), text("لا يُستخدم أي مصدر عام أو حكومي قبل مراجعة شروطه وجودته.", "No public or government source is used before its terms and quality are reviewed.")],
              [text("حدود القرار", "Decision limits"), text("المراجعة المحلية ليست ترخيصًا حكوميًا ولا وعدًا استثماريًا.", "Local review is not a government license or an investment promise.")],
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
          <button className="primary-button primary-button--large" onClick={() => { writeLocalFlag(LEGAL_ACCEPTANCE_STORAGE_KEY, true); setLegalAccepted(true); setStage("dashboard"); }}>
            <CheckCircle2 size={20} aria-hidden="true" />
            {text("أوافق وأبدأ", "Agree and start")}
          </button>
        </section>
      </main>
    );
  }

  return (
    <main id="main-content" className="app-shell" dir={direction}>
      <aside className="sidebar" aria-label={text("مسار مساحة المشروع", "Project workspace navigation")}>
        <BrandLockup subtitle={text("مرصد القرار المحلي", "Local decision workspace")} />
        <nav>
          {appStageGroups.map((group) => (
            <div className="nav-group" key={group.label}>
              <span className="nav-group__label">{locale === "ar" ? group.label : group.labelEn}</span>
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
                    <strong>{locale === "ar" ? item.label : item.labelEn}</strong>
                    <span>{locale === "ar" ? item.description : item.descriptionEn}</span>
                  </button>
                );
              })}
            </div>
          ))}
        </nav>
        <button className="nav-item nav-item--quiet" onClick={() => { writeLocalFlag(LEGAL_ACCEPTANCE_STORAGE_KEY, false); setLegalAccepted(false); }}>
          <ScrollText size={16} aria-hidden="true" />
          {text("الوثائق القانونية", "Legal documents")}
        </button>
        <button className="nav-item nav-item--quiet" onClick={() => openOverlay("profiles")}>
          <BarChart3 size={16} aria-hidden="true" />
          {text("مراجع التمويل والقطاع", "Funding and sector references")}
        </button>
        <button className="nav-item nav-item--quiet" onClick={() => openOverlay("settings")}>
          <Users size={16} aria-hidden="true" />
          {text("الحساب والفريق", "Account and team")}
        </button>
        <div className="sidebar-note">
          <Database size={18} aria-hidden="true" />
          <span>{text("مصادر محكومة ومراجعة", "Governed, reviewed sources")}</span>
        </div>
      </aside>

      <section className="workspace" data-asie-missing-label={firstMissingInputLabel ?? ""} data-asie-missing-target={firstMissingInputTarget} data-asie-missing-count={readinessBlocked.length}>
        <header className="topbar">
          <div>
            <p className="eyebrow">{text("بيئة بيتا محكومة", "Governed beta environment")}</p>
            <h1>{(() => { const current = appStages.find((item) => item.id === stage); return current ? (locale === "ar" ? current.label : current.labelEn) : "ASIE"; })()}</h1>
            <p>{project ? `${customerBusinessText(project.sector, locale)} · ${locale === "ar" ? project.jurisdiction : project.jurisdiction === "المملكة العربية السعودية" ? "Saudi Arabia" : customerBusinessText(project.jurisdiction, locale)}` : text("ابدأ من تعريف المشروع، ثم دع المنصة تقودك خطوة بخطوة.", "Start with project setup, then follow the guided journey step by step.")}</p>
          </div>
          <div className="topbar__actions topbar__actions--minimal">
            <CustomerLanguageSwitcher />
            {overview ? (
            <button disabled={isBusy} onClick={handleOpenReport} title={text("فتح التقرير", "Open report")}>
              <FileText size={18} aria-hidden="true" />
              <span>{text("افتح التقرير", "Open report")}</span>
            </button>
            ) : null}
          </div>
        </header>

        {error ? (
          <section className="status-banner status-banner--error" role="alert" aria-live="assertive">
            <AlertTriangle size={18} aria-hidden="true" />
            <span>{customerErrorText(error, locale)}</span>
          </section>
        ) : null}

        {authState === "legacy" ? (
          <section className="status-banner" role="status">
            <ShieldCheck size={18} aria-hidden="true" />
            <span>{text("استخدم دعوة بيتا مرتبطة بالبريد لإنشاء حساب ومساحة منظمة معزولة.", "Use an email-bound beta invitation to create an account and an isolated organization workspace.")}</span>
          </section>
        ) : null}

        <section className={`panel product-flow product-flow--${stage}`} aria-label={text("تقدم المشروع", "Project progress")}>
          <div className="section-title">
            <Sparkles size={20} aria-hidden="true" />
            <h2>{text("مسار المستخدم الحالي", "Current journey")}</h2>
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
                <strong>{locale === "ar" ? item.label : item.labelEn}</strong>
              </button>
            ))}
          </div>
          <div className="journey-metrics">
            <article>
              <LayoutDashboard size={18} aria-hidden="true" />
              <span>{text("المشاريع", "Projects")}</span>
              <strong>{projects.length}</strong>
            </article>
            <article>
              <Database size={18} aria-hidden="true" />
              <span>{text("الأدلة المرتبطة", "Linked evidence")}</span>
              <strong>{evidenceLinkCount}</strong>
            </article>
            <article>
              <AlertTriangle size={18} aria-hidden="true" />
              <span>{text("نواقص الجاهزية", "Missing requirements")}</span>
              <strong>{readinessBlocked.length}</strong>
            </article>
            <article>
              <FileText size={18} aria-hidden="true" />
              <span>{text("آخر تقرير", "Latest report")}</span>
              <strong>{latestRun?.snapshot_id ? text("متاح", "Available") : text("لا يوجد", "None")}</strong>
            </article>
          </div>
        </section>

        {stage !== "dashboard" ? (
          <section className="next-action-banner" aria-label={text("الخطوة التالية", "Next action")}>
            <div>
              <span>{text("الخطوة التالية", "Next action")}</span>
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

        {overlay === null ? (
        <>
        <div className={`client-page-shell client-page-shell--${pageDirection}`} key={stage}>
        {stage === "dashboard" ? (
          <CommandCenter
            onOpenProject={(projectId) => {
              const target = projects.find((item) => item.project_id === projectId);
              if (target) openProject(target);
            }}
            onNewProject={() => {
              setProject(null);
              setWorkspace(null);
              setReadiness(null);
              setOverview(null);
              setReport(null);
              setReportView(null);
              setDecisionPack(null);
              setComparison(null);
              setForm({
                name: "",
                sector: "",
                jurisdiction: "المملكة العربية السعودية",
                depth_profile: "starter",
                inputs: { ...defaultInputs },
              });
              setWizardStep(0);
              setMaxUnlockedWizardStep(0);
              setStage("wizard");
            }}
            onOpenStage={(projectId, targetStage) => {
              const target = projects.find((item) => item.project_id === projectId);
              if (!target) return;
              setProject(target);
              setForm({
                name: target.name,
                sector: target.sector,
                jurisdiction: target.jurisdiction,
                depth_profile: target.depth_profile,
                inputs: { ...defaultInputs, ...target.inputs },
              });
              setMaxUnlockedWizardStep(wizardJourney.length - 1);
              setStage(targetStage);
              void loadProjectWorkspace(target.project_id);
            }}
          />
        ) : null}

        {stage === "wizard" ? (
          <section className="panel wizard-board">
            <div className="section-title">
              <Rocket size={20} aria-hidden="true" />
              <h2>{text("إعداد المشروع", "Project setup")}</h2>
            </div>
            <div className="wizard-rail" aria-label={text("تقدم إعداد المشروع", "Project setup progress")}>
              <span className="wizard-progress-label">{text("الخطوة", "Step")} {wizardStep + 1} {text("من", "of")} {wizardJourney.length}</span>
              <strong>{locale === "ar" ? wizardJourney[wizardStep].label : wizardJourney[wizardStep].labelEn}</strong>
              <span className="wizard-progress-track" aria-hidden="true">
                <span style={{ width: `${((wizardStep + 1) / wizardJourney.length) * 100}%` }} />
              </span>
            </div>
            <div className="wizard-focus">
              <div>
                <p className="eyebrow">{text("الخطوة", "Step")} {wizardStep + 1} {text("من", "of")} {wizardJourney.length}</p>
                <h2>{locale === "ar" ? wizardJourney[wizardStep].label : wizardJourney[wizardStep].labelEn}</h2>
                <p className="muted">
                  {(locale === "ar" ? wizardStepHelp : wizardStepHelpEnglish)[wizardStep] ?? text("أكمل هذه الخطوة ثم تابع.", "Complete this step to continue.")}
                </p>
              </div>
              <div className="button-row">
                <button disabled={wizardStep === 0} onClick={() => setWizardStep((current) => Math.max(current - 1, 0))}>
                  {text("السابق", "Previous")}
                </button>
                <button className="primary-button" disabled={isBusy || Boolean(validateWizardStep())} onClick={handleWizardPrimary}>
                  {wizardStep < wizardJourney.length - 1 ? text("التالي", "Next") : text("افحص النواقص", "Check missing inputs")}
                </button>
              </div>
            </div>
          </section>
        ) : null}

        {stage === "evidence" ? (
          <section className="panel evidence-workbench-intro">
            <div className="section-title">
              <Database size={20} aria-hidden="true" />
              <h2>{text("لوحة الأدلة", "Evidence workspace")}</h2>
            </div>
            <div className="journey-metrics">
              <article>
                <Database size={18} aria-hidden="true" />
                <span>{text("مجموعات البيانات", "Datasets")}</span>
                <strong>{datasets.length}</strong>
              </article>
              <article>
                <ShieldCheck size={18} aria-hidden="true" />
                <span>{text("اجتازت الجودة", "Passed quality review")}</span>
                <strong>{evidenceGateCount}</strong>
              </article>
              <article>
                <FileUp size={18} aria-hidden="true" />
                <span>{text("التحويلات", "Transformations")}</span>
                <strong>{transformations.length}</strong>
              </article>
              <article>
                <BadgeCheck size={18} aria-hidden="true" />
                <span>{text("الأدلة المعتمدة", "Approved evidence")}</span>
                <strong>{evidenceLedger.length}</strong>
              </article>
            </div>
            <p className="muted">{text("الأدلة هي المعلومات التي تثبت أرقام مشروعك. ارفع ملفًا أو أدخل بياناتك، ثم افحص الجودة واعتمد الدليل قبل ربطه بالتحليل.", "Evidence supports your project figures. Upload a file or enter your data, review its quality, then approve it before linking it to the analysis.")}</p>
            <div className="evidence-guidance">
              <article><strong>{text("ما الذي أرفعه؟", "What should I upload?")}</strong><span>{text("مبيعات، عروض أسعار، إيجارات، رواتب، أو تقرير رسمي يخص السوق السعودي.", "Sales records, quotations, rent, payroll, or an official report relevant to the Saudi market.")}</span></article>
              <article><strong>{text("ماذا تفعل المنصة؟", "What does the platform do?")}</strong><span>{text("تفحص الملف، توضّح النواقص، ثم تعرض لك ما يحتاج اعتمادًا بشريًا.", "It checks the file, explains gaps, then shows what requires human approval.")}</span></article>
              <article><strong>{text("متى أشغّل التحليل؟", "When should I run the analysis?")}</strong><span>{canRunCurrentProject ? text("المشروع جاهز. شغّل التحليل لإنشاء أول نتيجة محفوظة.", "The project is ready. Run the analysis to create its first saved result.") : text("أكمل متطلبات الجاهزية أولًا؛ سنرشدك إليها خطوة بخطوة.", "Complete the readiness requirements first; we will guide you step by step.")}</span></article>
            </div>
            <div className="next-action-banner__actions">
              <button className="primary-button" disabled={isBusy} onClick={() => canRunCurrentProject ? void handleRunAndOpenMarketIntelligence() : setStage("readiness")}>
                <Play size={18} aria-hidden="true" />
                {canRunCurrentProject ? text("شغّل التحليل الآن", "Run analysis now") : text("انتقل إلى فحص الجاهزية", "Review readiness")}
              </button>
            </div>
          </section>
        ) : null}

        {stage === "readiness" ? (
          <section className="panel readiness-board">
            <div className="section-title">
              <CheckCircle2 size={20} aria-hidden="true" />
              <h2>{text("جاهزية المشروع قبل التحليل", "Project readiness before analysis")}</h2>
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
                {text("العودة إلى أول متطلب ناقص", "Go to the first missing requirement")}
              </button>
              <small>{text("اضغط على أي بطاقة للذهاب مباشرة إلى مكان تعديلها.", "Select any card to go directly to the place where it can be completed.")}</small>
            </div>
            <div className="workflow-steps">
              {(readiness?.steps ?? []).map((item, index) => (
                <button
                  type="button"
                  className={item.status === "ready" ? "workflow-step workflow-step--done workflow-step--action" : "workflow-step workflow-step--action"}
                  key={item.step_id}
                  title={`${customerBusinessText(item.label, locale)}: ${customerNarrativeText(item.message, locale)}`}
                  onClick={() => navigateFromReadiness(item.step_id, item.status)}
                >
                  <span>{index + 1}</span>
                  <strong>{customerBusinessText(item.label, locale)}</strong>
                  <small>{customerNarrativeText(item.message, locale)}</small>
                  <em>{item.status === "ready" ? text("عرض المدخلات", "View inputs") : text("انتقل لإكمالها", "Complete inputs")}</em>
                </button>
              ))}
            </div>
            {!readiness ? <p className="muted">{text("احفظ المسودة أولًا لعرض الجاهزية خطوة بخطوة.", "Save the draft first to view readiness step by step.")}</p> : null}
          </section>
        ) : null}

        {stage === "run" ? (
          <section className="panel run-board">
            <div className="section-title">
              <Play size={20} aria-hidden="true" />
              <h2>{text("تشغيل التحليل", "Run analysis")}</h2>
            </div>
            <p className="muted">
              {text("عند الضغط على الزر، تنشئ المنصة نتيجة محفوظة من بياناتك الحالية. لا تحتاج إلى معرفة التفاصيل التقنية.", "The platform creates a saved result from your current data. No technical knowledge is required.")}
            </p>
            <button className="primary-button primary-button--large" disabled={!canRunCurrentProject || isBusy} onClick={handleRunAndOpenMarketIntelligence}>
              <Play size={20} aria-hidden="true" />
              {text("ابدأ التحليل", "Start analysis")}
            </button>
            {!project ? <p className="muted">{text("أنشئ المسودة قبل التشغيل.", "Create the project draft before running the analysis.")}</p> : null}
            {readiness && !readiness.ready_to_run ? <p className="muted">{text("توجد متطلبات ناقصة تمنع التشغيل. راجع قسم الجاهزية.", "Missing requirements are preventing the analysis. Review project readiness.")}</p> : null}
          </section>
        ) : null}

        {stage === "reality" ? (
          <section className="reality-page" aria-label={text("السوق والفرص بعد الدراسة", "Market and opportunities after the analysis")}>
            <header className="page-intro">
              <p className="eyebrow">{text("بعد اكتمال الدراسة", "After completing the analysis")}</p>
              <h2>{text("راجع السوق والفرص قبل اعتماد القرار", "Review the market and opportunities before approving the decision")}</h2>
              <p>{text("تعرض هذه الصفحة معلومات السوق المتاحة بوضوح، وتبين عندما تكون البيانات غير متاحة. لا تغيّر نتيجة التحليل أو التقرير أو القرار.", "This page clearly presents available market information and identifies unavailable data. It does not change the analysis result, report, or decision.")}</p>
            </header>
            <LiveCockpit
              projectName={project?.name}
              projectId={project?.project_id}
              sector={project?.sector}
              primarySectorId={project?.inputs.primary_sector_id}
              location={project?.inputs.location_scope}
              locationLabel={[project?.inputs.location_city, project?.inputs.location_district].filter(Boolean).join(" · ") || project?.inputs.location_scope}
              latitude={project?.inputs.location_latitude ?? null}
              longitude={project?.inputs.location_longitude ?? null}
              onContinue={() => setStage("decision")}
            />
          </section>
        ) : null}

        {stage === "decision" ? (
          <section className="decision-command" aria-label={text("مساحة قرار العميل", "Customer decision workspace")}>
            <article className="decision-command__hero">
              <div>
                <p className="eyebrow">{text("مساحة القرار · تقرير محفوظ لا يعيد الحساب", "Decision workspace · saved report without recalculation")}</p>
                <h2>{snapshotOverview ? statusText(snapshotOverview.decision.sovereign_verdict, locale) : text("القرار غير متاح بعد", "Decision is not available yet")}</h2>
                <p>{snapshotOverview ? customerNarrativeText(snapshotOverview.decision.reason, locale) : text("شغّل التحليل أولاً لإظهار القرار وسببه من تقرير محفوظ.", "Run the analysis first to show the decision and its reason from a saved report.")}</p>
              </div>
              <div className="decision-command__identity">
                <span>{text("حالة التقرير", "Report status")}</span>
                <strong>{snapshotOverview ? text("محفوظ", "Saved") : text("غير متاح", "Not available")}</strong>
                <small>{snapshotOverview ? text("مرتبط بنتيجة التحليل الحالية", "Linked to the current analysis result") : text("أنشئ التحليل أولاً", "Run the analysis first")}</small>
              </div>
            </article>

            <div className="decision-command__summary">
              <article><span>{text("المراجعة البشرية", "Human review")}</span><strong>{statusText(decisionStatus, locale)}</strong><small>{text("مراجعة منفصلة لا تغيّر نتيجة التحليل الأصلية", "A separate review that does not change the original result")}</small></article>
              <article><span>{text("الإجراءات المفتوحة", "Open actions")}</span><strong>{openActionItems.length}</strong><small>{text("خطوات عملية مرتبطة بالتقرير", "Practical steps linked to the report")}</small></article>
              <article><span>{text("حالة التنفيذ", "Execution status")}</span><strong>{snapshotOverview ? statusText(snapshotOverview.execution_plan.status, locale) : text("غير متاح", "Not available")}</strong><small>{text("متابعة الخطوات والعوائق", "Track actions and blockers")}</small></article>
            </div>

            {snapshotOverview ? (
              <section className="decision-intelligence" aria-label={text("تفسير القرار من زوايا متعددة", "Decision explanation from multiple perspectives")}>
                <header><div><p className="eyebrow">{text("فهم القرار المحفوظ", "Understand the saved decision")}</p><h2>{text("اختبر القرار من خمس زوايا واحتمالات متعددة", "Review the decision from five perspectives and multiple scenarios")}</h2><p>{text("هذه تفسيرات للنتيجة الحالية؛ لا تغيّر القرار الأصلي.", "These explanations describe the current result without changing the original decision.")}</p></div><button onClick={() => void handleOpenDecisionPack()} disabled={isBusy}>{text("فتح التفسير الكامل", "Open full explanation")} <ArrowLeft size={16} /></button></header>
                <div className="decision-intelligence__grid">
                  <article className="monte-carlo-widget">
                    <div className="intelligence-widget__heading"><div><Calculator size={20} /><span>{text("محاكاة احتمالات المخاطر", "Risk probability simulation")}</span></div><small>{snapshotOverview.monte_carlo.status === "ready" ? text("المحاكاة جاهزة", "Simulation ready") : text("تحتاج مدخلات", "Needs inputs")}</small></div>
                    <strong>{snapshotOverview.monte_carlo.p_pass === null ? "—" : `${Math.round(snapshotOverview.monte_carlo.p_pass * 100)}%`}</strong>
                    <p>{text("احتمال استيفاء متطلبات الجدوى عبر", "Probability of meeting feasibility requirements across")} {snapshotOverview.monte_carlo.iterations.toLocaleString(locale === "ar" ? "ar-SA" : "en-US")} {text("سيناريو محفوظ.", "saved scenarios.")}</p>
                    <div className="simulation-scale"><i style={{ width: `${Math.max(0, Math.min(100, (snapshotOverview.monte_carlo.p_pass ?? 0) * 100))}%` }} /><span>{text("ضعيف", "Weak")}</span><span>{text("متوازن", "Balanced")}</span><span>{text("قوي", "Strong")}</span></div>
                  </article>
                  <div className="persona-kpi-grid">
                    {snapshotOverview.personas.map((persona) => <button key={persona.persona_id} className="persona-kpi" onClick={() => void handleOpenDecisionPack()}><span>{customerBusinessText(persona.metric, locale)}</span><strong>{persona.value === null ? "—" : `${Math.round(persona.value * 100)}%`}</strong><small>{statusText(persona.status, locale)} · {text("افتح التفسير", "Open explanation")}</small></button>)}
                  </div>
                </div>
              </section>
            ) : null}

            <div className="decision-command__grid">
              <article className="panel decision-rationale">
                <div className="section-title"><FileText size={20} aria-hidden="true" /><h2>{text("لماذا هذا القرار؟", "Why this decision?")}</h2></div>
                {decisionPack ? <><strong>{customerBusinessText(decisionPack.memo.recommendation, locale)}</strong><p>{customerNarrativeText(decisionPack.memo.rationale, locale)}</p><small>{text("مذكرة مرتبطة بالتقرير الحالي", "Memo linked to the current report")}</small></> : <p className="empty-state">{text("افتح مذكرة القرار لعرض التفسير المحفوظ.", "Open the decision memo to view the saved explanation.")}</p>}
                <div className="button-row"><button disabled={!snapshotOverview || isBusy} onClick={handleOpenDecisionPack}>{text("فتح مذكرة القرار", "Open decision memo")}</button><button disabled={!snapshotOverview || isBusy} onClick={handleOpenReport}>{text("فتح التقرير", "Open report")}</button></div>
              </article>
              <article className="panel decision-evidence">
                <div className="section-title"><Database size={20} aria-hidden="true" /><h2>{text("ثقة الأدلة", "Evidence confidence")}</h2></div>
                <strong>{snapshotOverview ? `${snapshotOverview.evidence_coverage.supported} ${text("عنصر مدعوم", "supported items")}` : text("غير متاح", "Not available")}</strong>
                <p>{snapshotOverview ? `${snapshotOverview.evidence_coverage.needs_evidence} ${text("عنصر يحتاج دليلاً قبل تحسين قوة القرار.", "items need evidence before decision confidence can improve.")}` : text("ستظهر تغطية الأدلة بعد تشغيل التحليل.", "Evidence coverage will appear after running the analysis.")}</p>
                <button disabled={!snapshotOverview} onClick={() => setStage("evidence")}>{text("عرض تفاصيل الأدلة ومصادرها", "View evidence details and sources")}</button>
              </article>
            </div>

            <div className="decision-command__grid">
              <article className="panel">
                <div className="section-title"><AlertTriangle size={20} aria-hidden="true" /><h2>{text("المخاطر وخطوات الحد منها", "Risks and mitigation steps")}</h2></div>
                <div className="command-risk-list">
                  {(decisionPack?.top_risks ?? snapshotOverview?.risk_register.top_risks ?? []).slice(0, 4).map((risk) => <article key={risk.risk_id}><strong>{customerBusinessText(risk.trigger, locale)}</strong><span>{statusText(risk.severity, locale)} · {customerBusinessText(risk.owner_role, locale)}</span><small>{customerNarrativeText(risk.mitigation, locale)}</small></article>)}
                </div>
                {!snapshotOverview?.risk_register.top_risks.length ? <p className="empty-state">{text("لا توجد مخاطر محفوظة لعرضها بعد.", "No saved risks are available yet.")}</p> : null}
              </article>
              <article className="panel">
                <div className="section-title"><Target size={20} aria-hidden="true" /><h2>{text("خطة التنفيذ", "Execution plan")}</h2></div>
                <div className="execution-list">
                  {(decisionPack?.execution_plan.milestones ?? snapshotOverview?.execution_plan.milestones ?? []).slice(0, 4).map((milestone) => <article key={milestone.phase_id}><strong>{customerBusinessText(milestone.phase_id, locale)}</strong><span>{customerBusinessText(milestone.owner_role, locale)} · {milestone.estimated_duration_days} {text("يوم", "days")}</span><small>{milestone.exit_criteria[0] ? customerNarrativeText(milestone.exit_criteria[0], locale) : text("لا يوجد معيار إتمام معلن", "No completion criterion is available")}</small></article>)}
                </div>
                {!snapshotOverview?.execution_plan.milestones.length ? <p className="empty-state">{text("تظهر مراحل التنفيذ بعد اكتمال نتيجة التحليل.", "Execution stages appear after the analysis result is complete.")}</p> : null}
              </article>
            </div>

            <article className="panel decision-review-panel">
              <div className="section-title"><Users size={20} aria-hidden="true" /><h2>{text("المراجعة البشرية والإجراءات", "Human review and actions")}</h2></div>
              <p className="muted">{text("الاعتماد أو الرفض يسجل مراجعة مستقلة ولا يغير نتيجة التحليل الأصلية.", "Approval or rejection records a separate review without changing the original analysis result.")}</p>
              <div className="button-row">
                <button disabled={!decisionPack || isBusy} onClick={() => handleReviewDecision("approved_local")}>{text("اعتماد للمراجعة الداخلية", "Approve for internal review")}</button>
                <button disabled={!decisionPack || isBusy} onClick={() => handleReviewDecision("needs_changes")}>{text("طلب تعديل", "Request changes")}</button>
                <button disabled={!decisionPack || isBusy} onClick={() => handleReviewDecision("rejected_local")}>{text("رفض للمراجعة الداخلية", "Reject for internal review")}</button>
              </div>
              <div className="remediation-list">
                {actionItems.slice(0, 6).map((item) => <article key={item.action_item_id}><strong>{customerNarrativeText(item.title, locale)}</strong><span>{customerNarrativeText(item.message || item.recommended_action, locale)}</span><small>{statusText(item.severity, locale)} · {statusText(item.status, locale)}</small>{item.status === "open" ? <button disabled={isBusy} onClick={() => handleCloseActionItem(item.action_item_id)}>{text("إتمام الإجراء", "Complete action")}</button> : null}</article>)}
                {!actionItems.length ? <p className="empty-state">{text("لا توجد إجراءات مفتوحة في التقرير الحالي.", "No open actions are available in the current report.")}</p> : null}
              </div>
            </article>
          </section>
        ) : null}

        {stage === "execution" ? (
          <section className="execution-page" aria-label={text("خطة تنفيذ المشروع", "Project execution plan")}>
            <header className="page-intro">
              <p className="eyebrow">{text("خطوات ما بعد القرار", "Post-decision steps")}</p>
              <h2>{text("حوّل القرار إلى بداية مشروع عملية", "Turn the decision into an actionable project start")}</h2>
              <p>{text("تعرض هذه الصفحة الخطوات المستندة إلى نتيجة التحليل المحفوظة. لن تُعرض متطلبات تنظيمية أو بيانات غير موثقة على أنها حقائق.", "This page shows steps derived from the saved analysis result. Regulatory requirements or unverified data are never presented as facts.")}</p>
            </header>
            <div className="execution-page__grid">
              <article className="panel">
                <div className="section-title"><Target size={20} aria-hidden="true" /><h2>{text("الخطوات القادمة", "Next steps")}</h2></div>
                <div className="execution-list">
                  {(decisionPack?.execution_plan.milestones ?? snapshotOverview?.execution_plan.milestones ?? []).map((milestone) => <article key={milestone.phase_id}><strong>{customerBusinessText(milestone.phase_id, locale)}</strong><span>{customerBusinessText(milestone.owner_role, locale)} · {milestone.estimated_duration_days} {text("يوم", "days")}</span><small>{milestone.exit_criteria[0] ? customerNarrativeText(milestone.exit_criteria[0], locale) : text("لا يوجد معيار إتمام معلن", "No completion criterion is available")}</small></article>)}
                </div>
                {!snapshotOverview?.execution_plan.milestones.length ? <p className="empty-state">{text("شغّل التحليل أولاً كي تظهر خطة تنفيذ مرتبطة بالقرار المحفوظ.", "Run the analysis first to view an execution plan linked to the saved decision.")}</p> : null}
              </article>
              <article className="panel execution-page__action">
                <div className="section-title"><CheckCircle2 size={20} aria-hidden="true" /><h2>{text("إجراء اليوم", "Today’s action")}</h2></div>
                <strong>{openActionItems[0]?.title ? customerNarrativeText(openActionItems[0].title, locale) : text("لا يوجد إجراء مفتوح", "No open action")}</strong>
                <p>{openActionItems[0] ? customerNarrativeText(openActionItems[0].message || openActionItems[0].recommended_action, locale) : text("بعد ظهور القرار ستُعرض هنا الخطوة الأهم مع سببها.", "After the decision appears, the most important next step and its reason will be shown here.")}</p>
                {openActionItems[0]?.status === "open" ? <button className="primary-button" disabled={isBusy} onClick={() => handleCloseActionItem(openActionItems[0].action_item_id)}>{text("إتمام الإجراء", "Complete action")}</button> : null}
              </article>
            </div>
            <section className="panel launch-readiness-status" aria-label={text("متطلبات البدء الرسمية", "Official launch requirements")}>
              <div className="section-title"><KeyRound size={20} aria-hidden="true" /><h2>{text("متطلبات البدء الرسمية", "Official launch requirements")}</h2></div>
              <p>{text("لن تعرض المنصة قائمة متطلبات أو تراخيص قبل ربط مصادر رسمية معتمدة حسب القطاع والموقع. عند توفرها ستظهر هنا مع مصدر كل متطلب وطريقة استكماله.", "The platform will not present requirements or licences until approved official sources are connected for the project sector and location. Once available, each requirement will appear here with its source and completion path.")}</p>
            </section>
          </section>
        ) : null}

        {stage === "snapshots" ? (
          <section className="snapshots-page" aria-label={text("التقارير المحفوظة", "Saved reports")}>
            <header className="page-intro">
              <p className="eyebrow">{text("مخرجات محفوظة · لا إعادة حساب", "Saved outputs · no recalculation")}</p>
              <h2>{text("التقارير المرجعية", "Reference reports")}</h2>
              <p>{text("كل تقرير مرتبط بنتيجة تحليل محفوظة. إذا لم تُنشأ نتيجة بعد، ستظهر الحالة بوضوح دون أرقام بديلة.", "Each report is linked to a saved analysis result. If no result exists yet, the status is shown clearly without substitute figures.")}</p>
            </header>

            {releaseRecord ? (
              <section className="panel release-record-panel" aria-label={text("حالة التقرير", "Report status")}>
                <div className="section-title">
                  <BadgeCheck size={20} aria-hidden="true" />
                  <h2>{text("حالة التقرير", "Report status")}</h2>
                  <button className="secondary-action" onClick={() => setReleaseRecord(null)}>{text("إغلاق", "Close")}</button>
                </div>
                <dl className="release-record-grid">
                  <div><dt>{text("حالة التقرير", "Report status")}</dt><dd>{statusText(String(releaseRecord.release_state ?? releaseRecord.status ?? "review_required"), locale)}</dd></div>
                  <div><dt>{text("المراجعة", "Review")}</dt><dd>{statusText(String(releaseRecord.review_decision ?? "review_required"), locale)}</dd></div>
                  <div><dt>{text("الاستخدام", "Use")}</dt><dd>{text("للمراجعة الداخلية حتى الاعتماد", "For internal review until approved")}</dd></div>
                </dl>
              </section>
            ) : null}

            {workspace?.runs.length ? (
              <div className="snapshot-list">
                {workspace.runs.map((run) => (
                  <article className="snapshot-card" key={run.run_id}>
                    <div className="snapshot-card__identity">
                      <span>{text("تقرير مرجعي", "Reference report")}</span>
                      <strong>{run.snapshot_id ? text("متاح", "Available") : text("غير متاح", "Not available")}</strong>
                      <small>{text("حالة التحليل", "Analysis status")}: {statusText(run.status, locale)}</small>
                    </div>
                    <div className="snapshot-card__decision">
                      <span>{text("حالة القرار", "Decision status")}</span>
                      <strong>{run.sovereign_verdict ? statusText(run.sovereign_verdict, locale) : text("غير متاح", "Not available")}</strong>
                      <small>{run.acceptance_status ? `${text("المراجعة", "Review")}: ${statusText(run.acceptance_status, locale)}` : text("المراجعة لم تُسجل بعد", "No review has been recorded yet")}</small>
                    </div>
                    <div className="button-row snapshot-card__actions">
                      {run.snapshot_id ? (
                        <>
                          <button className="secondary-action" onClick={() => void handleOpenDocument(run.snapshot_id!, "report.html", "open")}>{text("فتح التقرير", "Open report")}</button>
                          <button className="secondary-action" onClick={() => void handleOpenDocument(run.snapshot_id!, "decision-pack.html", "open")}>{text("فتح مذكرة القرار", "Open decision memo")}</button>
                          <button className="secondary-action" onClick={() => void handleOpenDocument(run.snapshot_id!, "funder-report.html", "open")}>{text("تقرير الممول", "Funder report")}</button>
                          <button className="secondary-action" onClick={() => void handleOpenDocument(run.snapshot_id!, "funder-report.pdf", "download")}>PDF</button>
                          <button className="secondary-action" onClick={() => void handleOpenDocument(run.snapshot_id!, "funder-report.docx", "download")}>DOCX</button>
                          <button className="secondary-action" onClick={() => void handleOpenDocument(run.snapshot_id!, "funder-report.pptx", "download")}>PPTX</button>
                          <button className="secondary-action" onClick={() => void handleShowRelease(run.snapshot_id!)}>{text("حالة التقرير", "Report status")}</button>
                        </>
                      ) : <span className="muted">{text("لا توجد تقارير قابلة للفتح.", "No reports are available to open.")}</span>}
                    </div>
                  </article>
                ))}
              </div>
            ) : (
              <article className="panel snapshots-empty-state">
                <Layers3 size={26} aria-hidden="true" />
                <div>
                  <h3>{project ? text("لا توجد نتيجة محفوظة لهذا المشروع بعد", "This project has no saved result yet") : text("اختر مشروعًا أو ابدأ مشروعًا جديدًا", "Choose a project or start a new one")}</h3>
                  <p>{project ? text("بعد استكمال المدخلات المطلوبة، شغّل التحليل لإنشاء أول نتيجة محفوظة.", "After completing required inputs, run the analysis to create the first saved result.") : text("لا تظهر التقارير دون مشروع محدد، ولا تنشئ هذه الصفحة بيانات تجريبية.", "Reports require a selected project; this page does not create demo data.")}</p>
                </div>
                <div className="button-row">
                  <button className="primary-button" onClick={() => setStage(project ? "run" : "wizard")}>
                    {project ? text("الانتقال إلى التشغيل", "Go to analysis") : text("ابدأ تعريف المشروع", "Set up a project")}
                  </button>
                  {projects.length ? <button onClick={() => openProject(projects[0])}>{text("فتح آخر مشروع", "Open latest project")}</button> : null}
                </div>
              </article>
            )}
          </section>
        ) : null}

        {stage === "architecture" && authUser?.platform_role === "platform_admin" ? (
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
              <h2>{text("مشاريعك", "Your projects")}</h2>
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
                    <span>{item.sector || text("قطاع غير محدد", "Sector not specified")}</span>
                  </button>
                ))}
            </div>
          </div>

          <div className="panel project-room__journey">
            <div className="section-title">
              <Layers3 size={20} aria-hidden="true" />
              <h2>{text("خطوات إعداد المشروع", "Project setup steps")}</h2>
            </div>
            <div className="workflow-steps">
              {(readiness?.steps ?? workflow.map((copy, index) => ({
                step_id: `fallback-${index}`,
                label: locale === "ar" ? copy.ar : copy.en,
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
                  title={customerNarrativeText(item.message, locale)}
                >
                  <span>{index + 1}</span>
                  <strong>{customerBusinessText(item.label, locale)}</strong>
                </div>
              ))}
            </div>
          </div>

          <div className="panel project-room__source">
            <div className="section-title">
              <KeyRound size={20} aria-hidden="true" />
              <h2>{text("مصادر المعلومات", "Information sources")}</h2>
            </div>
            <dl className="source-summary">
              <div>
                <dt>{text("مصادر معتمدة ومفعلة", "Approved and enabled sources")}</dt>
                <dd>{sourcePolicy.enabled_sources.length}</dd>
              </div>
              <div>
                <dt>{text("مصادر بانتظار المراجعة", "Sources awaiting review")}</dt>
                <dd>{sourcePolicy.candidate_sources.length}</dd>
              </div>
              <div>
                <dt>{text("مصادر إرشادية فقط", "Guidance-only sources")}</dt>
                <dd>{sourcePolicy.reference_only.length}</dd>
              </div>
            </dl>
            <p className="muted">{text("لا تُفعّل المنصة أي مصدر خارجي تلقائيًا. لا يُستخدم المصدر إلا بعد التحقق من الترخيص والإسناد والتصنيف والمراجعة البشرية.", "The platform never enables an external source automatically. A source is used only after licence, attribution, classification, and human review checks.")}</p>
            <div className="source-list">
              {sources.slice(0, 3).map((source) => (
                <article key={source.source_id}>
                  <strong>{customerSourceName(source.publisher || source.source_id, locale)}</strong>
                  <span>{statusText(source.state, locale)}</span>
                </article>
              ))}
            </div>
            <p className="muted">{sourceChecklists.filter((item) => item.can_enable).length} {text("مصدر مكتمل المراجعة", "sources completed review")}</p>
          </div>

          <div className="panel evidence-room">
            <div className="section-title">
              <Database size={20} aria-hidden="true" />
              <h2>{text("بيانات المشروع وأدلته", "Project data and evidence")}</h2>
            </div>
            <dl className="source-summary">
              <div>
                <dt>{text("مجموعات البيانات", "Datasets")}</dt>
                <dd>{datasets.length}</dd>
              </div>
              <div>
                <dt>{text("اجتازت فحص الجودة", "Passed quality review")}</dt>
                <dd>{(draftEvidenceRegister?.quality_gates ?? overview?.evidence_register.quality_gates ?? []).filter((item) => item.status === "passed").length}</dd>
              </div>
              <div>
                <dt>{text("أدلة مرتبطة", "Linked evidence")}</dt>
                <dd>{(draftEvidenceRegister?.evidence_links ?? overview?.evidence_register.evidence_links ?? []).length}</dd>
              </div>
              <div>
                <dt>{text("معالجات معتمدة", "Approved transformations")}</dt>
                <dd>{transformations.length}</dd>
              </div>
            </dl>
            <label className="field file-field">
              <span>{text("استيراد ملف بيانات", "Import data file")}</span>
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
              <span>{text("لصق بيانات مفصولة بفواصل", "Paste comma-separated data")}</span>
              <textarea value={csvText} onChange={(event) => setCsvText(event.target.value)} rows={4} />
            </label>
            <div className="form-grid form-grid--compact">
              <label className="field">
                <span>{text("مجموعة البيانات المراد معالجتها", "Dataset to transform")}</span>
                <select value={selectedDataset?.dataset_id ?? ""} onChange={(event) => setSelectedDatasetId(event.target.value)}>
                  {datasets.map((dataset) => (
                    <option value={dataset.dataset_id} key={dataset.dataset_id}>
                      {dataset.title}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field">
                <span>{text("طريقة المعالجة", "Transformation method")}</span>
                <select value={transformationOperation} onChange={(event) => setTransformationOperation(event.target.value)}>
                  <option value="aggregate_average">{text("متوسط العمود", "Column average")}</option>
                  <option value="aggregate_sum">{text("مجموع العمود", "Column total")}</option>
                  <option value="select_column">{text("اختيار عمود", "Select column")}</option>
                  <option value="manual_derivation_note">{text("ملاحظة توضيحية", "Explanatory note")}</option>
                </select>
              </label>
              <label className="field">
                <span>{text("العمود", "Column")}</span>
                <select value={transformationColumn} onChange={(event) => setTransformationColumn(event.target.value)}>
                  {(selectedDataset?.columns ?? ["value"]).map((column) => (
                    <option value={column} key={column}>
                      {column}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field">
                <span>{text("المعالجة المحفوظة", "Saved transformation")}</span>
                <select value={selectedTransformationId} onChange={(event) => setSelectedTransformationId(event.target.value)}>
                  <option value="">{text("بدون معالجة", "No transformation")}</option>
                  {selectedDatasetTransformations.map((item) => (
                    <option value={item.transformation_id} key={item.transformation_id}>
                      {statusText(item.operation_type)} · {statusText(item.review_status)}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <div className="topbar__actions topbar__actions--inline">
              <button disabled={isBusy} onClick={handleCreateLocalDataset} title={text("إنشاء مجموعة بيانات يدوية", "Create a manual dataset")}>
                <Database size={18} aria-hidden="true" />
                <span>{text("مجموعة بيانات يدوية", "Manual dataset")}</span>
              </button>
              <button disabled={!selectedDataset || isBusy} onClick={handleCreateTransformation} title={text("إنشاء معالجة للبيانات", "Create a data transformation")}>
                <FileUp size={18} aria-hidden="true" />
                <span>{text("إنشاء معالجة", "Create transformation")}</span>
              </button>
              <button disabled={!selectedDataset || isBusy} onClick={() => handleReviewSelectedDataset("approved_for_use")} title={text("اعتماد مجموعة البيانات", "Approve dataset")}>
                <ShieldCheck size={18} aria-hidden="true" />
                <span>{text("اعتماد مجموعة البيانات", "Approve dataset")}</span>
              </button>
              <button disabled={!selectedDataset || isBusy} onClick={() => handleReviewSelectedDataset("rejected")} title={text("رفض مجموعة البيانات", "Reject dataset")}>
                <AlertTriangle size={18} aria-hidden="true" />
                <span>{text("رفض مجموعة البيانات", "Reject dataset")}</span>
              </button>
              <button disabled={!selectedTransformationId || isBusy} onClick={() => handleReviewSelectedTransformation("approved")} title={text("اعتماد معالجة البيانات", "Approve transformation")}>
                <BadgeCheck size={18} aria-hidden="true" />
                <span>{text("اعتماد المعالجة", "Approve transformation")}</span>
              </button>
              <button disabled={!selectedTransformationId || isBusy} onClick={() => handleReviewSelectedTransformation("review_required")} title={text("إرجاع المعالجة للتعديل", "Return transformation for changes")}>
                <RefreshCw size={18} aria-hidden="true" />
                <span>{text("تعديل المعالجة", "Revise transformation")}</span>
              </button>
              <button disabled={!project || isBusy} onClick={handleLinkApprovedDataset} title={text("ربط البيانات بافتراض يحتاج دليلاً", "Link data to an assumption that needs evidence")}>
                <BadgeCheck size={18} aria-hidden="true" />
                <span>{text("ربط دليل", "Link evidence")}</span>
              </button>
              <button disabled={!project || isBusy} onClick={handleLinkSectorCriterion} title={text("ربط البيانات بمتطلب قطاعي", "Link data to a sector requirement")}>
                <Layers3 size={18} aria-hidden="true" />
                <span>{text("ربط معيار", "Link requirement")}</span>
              </button>
            </div>
            <div className="source-list">
              {datasets.slice(0, 3).map((dataset) => (
                <article key={dataset.dataset_id}>
                  <strong>{dataset.title}</strong>
                  <span>
                    {statusText(dataset.review_status, locale)} · {text("الجودة", "Quality")} {statusText(dataset.notes.quality_review?.status ?? "unknown", locale)} · {dataset.row_count} {text("صف", "rows")}
                  </span>
                  <small>{dataset.row_count} {text("صف بيانات", "data rows")}</small>
                </article>
              ))}
            </div>
            <div className="source-list">
              {transformations.slice(0, 3).map((transformation) => (
                <article key={transformation.transformation_id}>
                  <strong>{customerBusinessText(transformation.operation_type, locale)}</strong>
                  <span>
                    {text("المراجعة", "Review")}: {statusText(transformation.review_status, locale)} · {text("الجودة", "Quality")}: {statusText(transformation.lineage.quality_review?.status ?? "unknown", locale)}
                  </span>
                  <small>
                    {transformation.output_value ?? text("لا توجد نتيجة", "No result")}
                  </small>
                </article>
              ))}
            </div>
            {selectedDataset?.notes.quality_review ? (
              <dl className="source-summary">
                <div>
                  <dt>{text("جودة مجموعة البيانات", "Dataset quality")}</dt>
                  <dd>{statusText(selectedDataset.notes.quality_review.status, locale)}</dd>
                </div>
                <div>
                  <dt>{text("قيم مفقودة", "Missing values")}</dt>
                  <dd>{Math.round(selectedDataset.notes.quality_review.max_missing_ratio * 100)}%</dd>
                </div>
                <div>
                  <dt>{text("صفوف مكررة", "Duplicate rows")}</dt>
                  <dd>{selectedDataset.notes.quality_review.duplicate_row_count}</dd>
                </div>
              </dl>
            ) : null}
            {evidenceCoverage ? (
              <p className="muted">
                {text("تغطية الأدلة", "Evidence coverage")}: {evidenceCoverage.supported} {text("مدعوم", "supported")} · {evidenceCoverage.needs_evidence} {text("يحتاج دليلاً", "need evidence")} · {evidenceLedger.length} {text("سجل دليل", "evidence records")} · {transformationLineage.length} {text("معالجة موثقة", "documented transformations")}
              </p>
            ) : null}
            <p className="muted">{text("أي مجموعة بيانات ناقصة الترخيص أو مراجعة المصدر تبقى غير جاهزة ولا تستخدم لدعم الافتراضات.", "Any dataset missing a licence or source review remains unavailable and is not used to support assumptions.")}</p>
          </div>
        </section>

        <section className={`panel project-inputs-panel project-inputs-panel--${stage} project-inputs-panel--step-${wizardStep}`}>
          <div className="section-title">
            <Calculator size={20} aria-hidden="true" />
            <h2>{text("ابدأ مشروعك", "Set up your project")}</h2>
            {stage === "wizard" && missingInputReturnStage ? (
              <button type="button" className="secondary-action" onClick={returnToMissingInputOrigin}>
                <ArrowLeft size={17} aria-hidden="true" /> {text("العودة إلى موضعك السابق", "Return to your previous place")}
              </button>
            ) : null}
          </div>
          <div className="guided-question-card">
            {wizardStep === 0 ? (
              <>
                <p className="guided-question-card__kicker">{text("الموقع داخل المملكة", "Location in Saudi Arabia")}</p>
                <h3>{text("أين سيعمل المشروع؟", "Where will the project operate?")}</h3>
                <p>{text("المرحلة الحالية مخصصة للسوق السعودي. اختر المنطقة والمدينة، وأضف الحي أو الإحداثيات عند الحاجة.", "This stage is designed for the Saudi market. Select the region and city, and add the district or coordinates when needed.")}</p>
                <LocationConsentInput key={JSON.stringify([authUser?.user_id, activeOrganizationId, project?.project_id])} onConfirm={({ latitude, longitude }) => {
                  updateInputs({ location_latitude: latitude, location_longitude: longitude });
                }} />
                <div className="location-fields">
                  <label className="field"><span>{text("الدولة", "Country")}</span><input value={text("المملكة العربية السعودية", "Saudi Arabia")} readOnly aria-readonly="true" /></label>
                  <label className="field"><span>{text("المنطقة", "Region")}</span><select id="wizard-location-region" value={form.inputs.location_region} onChange={(event) => { updateStructuredLocation("location_region", event.target.value); updateStructuredLocation("location_city", ""); }}><option value="">{text("اختر المنطقة", "Select region")}</option>{Object.keys(saudiCitiesByRegion).map((region) => <option key={region} value={region}>{customerLocationLabel(region, locale)}</option>)}</select></label>
                  <label className="field"><span>{text("المدينة", "City")}</span><select id="wizard-location-city" value={form.inputs.location_city} disabled={!form.inputs.location_region} onChange={(event) => {
                        updateStructuredLocation("location_city", event.target.value);
                        if (event.target.value) setTimeout(() => advanceWizardFromChoice(), 0);
                      }}><option value="">{text("اختر المدينة", "Select city")}</option>{(saudiCitiesByRegion[form.inputs.location_region] ?? []).map((city) => <option key={city} value={city}>{customerLocationLabel(city, locale)}</option>)}</select></label>
                  <label className="field"><span>{text("الحي أو الشارع", "District or street")} <small>{text("(اختياري)", "(optional)")}</small></span><input id="wizard-location-district" maxLength={50} value={form.inputs.location_district} placeholder={text("مثال: حي العليا", "Example: Al Olaya district")} onChange={(event) => updateStructuredLocation("location_district", event.target.value)} /></label>
                  <label className="field"><span>{text("خط العرض", "Latitude")} <small>{text("(اختياري)", "(optional)")}</small></span><input type="number" step="any" value={form.inputs.location_latitude ?? ""} placeholder="24.7136" onChange={(event) => {
                    const raw = event.target.value;
                    updateStructuredLocation("location_latitude", raw === "" ? undefined : Number(raw));
                  }} /></label>
                  <label className="field"><span>{text("خط الطول", "Longitude")} <small>{text("(اختياري)", "(optional)")}</small></span><input type="number" step="any" value={form.inputs.location_longitude ?? ""} placeholder="46.6753" onChange={(event) => {
                    const raw = event.target.value;
                    updateStructuredLocation("location_longitude", raw === "" ? undefined : Number(raw));
                  }} /></label>
                </div>
                <p className="guided-hint">{text("لا تُقرأ إحداثيات الجهاز تلقائيًا. إدخالها اختياري وتحت سيطرتك.", "Device coordinates are never read automatically. Providing them is optional and under your control.")}</p>
              </>
            ) : null}
            {wizardStep === 1 ? (
              <>
                <p className="guided-question-card__kicker">{text("القطاع", "Sector")}</p>
                <h3>{text("في أي قطاع تريد اختبار المشروع؟", "Which sector does the project belong to?")}</h3>
                <p>{text("اختر المجال الأقرب لفكرتك، ثم حدد النشاط بدقة.", "Select the sector closest to your idea, then choose the detailed activity.")}</p>
                <div id="wizard-sector-choices" className="choice-grid choice-grid--sectors" role="group" aria-label={text("قطاعات المشروع", "Project sectors")}>
                  {sectorTaxonomy.map((item) => (
                    <button type="button" key={item.sector_id} className={form.inputs.primary_sector_id === item.sector_id ? "choice-card choice-card--active" : "choice-card"} onClick={() => {
                      setShowCustomSector(false);
                      setForm((current) => ({ ...current, sector: item.arabic_name, inputs: { ...current.inputs, primary_sector_id: item.sector_id, subsector_id: "" } }));
                      advanceWizardFromChoice();
                    }}>
                      <strong>{locale === "ar" ? item.arabic_name : item.sector_name}</strong><small>{item.subsectors.length} {text("تصنيفات متاحة", "available categories")}</small>
                    </button>
                  ))}
                  <button type="button" className="choice-card choice-card--add" onClick={() => { setShowCustomSector(true); setForm((current) => ({ ...current, sector: "", inputs: { ...current.inputs, primary_sector_id: "CUSTOM", subsector_id: "" } })); }}><strong>{text("+ قطاع آخر", "+ Another sector")}</strong><small>{text("اكتب مجالك إذا لم تجده", "Enter your sector if it is not listed")}</small></button>
                </div>
                {showCustomSector ? (
                  <div className="guided-input-row">
                    <label className="field"><span>{text("اسم القطاع", "Sector name")}</span><input id="wizard-custom-sector" autoFocus value={form.sector} placeholder={text("مثال: الصناعات الإبداعية", "Example: creative industries")} onChange={(event) => setForm((current) => ({ ...current, sector: event.target.value, inputs: { ...current.inputs, primary_sector_id: "CUSTOM" } }))} /></label>
                    <button type="button" className="primary-button" disabled={!form.sector.trim()} onClick={advanceWizardFromChoice}>{text("حفظ القطاع والمتابعة", "Save sector and continue")}</button>
                  </div>
                ) : null}
              </>
            ) : null}
            {wizardStep === 2 ? (
              <>
                <p className="guided-question-card__kicker">{text("التصنيف الدقيق", "Detailed category")}</p>
                <h3>{text("ما نوع المشروع داخل هذا القطاع؟", "What type of project is this within the sector?")}</h3>
                <p>{text("اختر النوع الذي يصف مشروعك بدقة. إذا لم تجده، أضف وصفك الخاص.", "Select the category that best describes your project. If it is not listed, add your own description.")}</p>
                <div id="wizard-subsector-choices" className="choice-grid" role="group" aria-label={text("التصنيف الدقيق", "Detailed category")}>
                  {(selectedSector?.subsectors ?? [form.inputs.subsector_id]).map((item) => (
                    <button type="button" key={item} className={form.inputs.subsector_id === item ? "choice-card choice-card--active" : "choice-card"} onClick={() => { updateInputs({ subsector_id: item }); advanceWizardFromChoice(); }}><strong>{locale === "ar" ? arabicSubsectorLabel(item) : item}</strong><small>{text("اختر هذا النشاط", "Select this activity")}</small></button>
                  ))}
                  <button type="button" className="choice-card choice-card--add" onClick={() => { setShowCustomSubsector(true); updateInputs({ subsector_id: "" }); }}><strong>{text("+ تصنيف آخر", "+ Another category")}</strong><small>{text("أضف نوع مشروعك", "Add your project type")}</small></button>
                </div>
                {showCustomSubsector ? (
                  <div className="guided-input-row">
                    <label className="field"><span>{text("وصف التصنيف", "Category description")}</span><input id="wizard-custom-subsector" autoFocus value={form.inputs.subsector_id} placeholder={text("اكتب النشاط بدقة", "Describe the activity precisely")} onChange={(event) => updateInputs({ subsector_id: event.target.value })} /></label>
                    <button type="button" className="primary-button" disabled={!form.inputs.subsector_id?.trim()} onClick={advanceWizardFromChoice}>{text("حفظ التصنيف والمتابعة", "Save category and continue")}</button>
                  </div>
                ) : null}
              </>
            ) : null}
            {wizardStep === 3 ? (
              <>
                <p className="guided-question-card__kicker">{text("اسم المشروع", "Project name")}</p>
                <h3>{text("ما اسم مشروعك؟", "What is your project called?")}</h3>
                <label className="field">
                  <span>{text("اسم بسيط وواضح", "A simple, clear name")}</span>
                  <input
                    id="wizard-project-name"
                    maxLength={60}
                    value={form.name}
                    placeholder={text("مثال: عيادات النخبة", "Example: Elite Clinics")}
                    aria-invalid={Boolean(form.name.trim() && governedNameError(form.name, text("اسم المشروع", "Project name"), 3, 60, locale))}
                    onChange={(event) => setForm({ ...form, name: event.target.value })}
                    onBlur={() => {
                      if (!governedNameError(form.name, text("اسم المشروع", "Project name"), 3, 60, locale)) setTimeout(() => advanceWizardFromChoice(), 0);
                    }}
                  />
                  {form.name.trim() && governedNameError(form.name, text("اسم المشروع", "Project name"), 3, 60, locale) ? (
                    <small className="field-error">{governedNameError(form.name, text("اسم المشروع", "Project name"), 3, 60, locale)}</small>
                  ) : (
                    <small className="field-hint">{text("من 3 إلى 60 حرفًا، باسم واضح غير مكرر.", "Use 3 to 60 characters and a clear, distinctive name.")}</small>
                  )}
                </label>
                <div className="guided-actions"><button type="button" className="secondary-action" disabled><Sparkles size={17} aria-hidden="true" /> {text("اقتراح أسماء للمشروع", "Suggest project names")}</button><small>{text("ستتوفر هذه المساعدة بعد تفعيلها واعتمادها.", "This assistance will be available after it is enabled and approved.")}</small></div>
              </>
            ) : null}
            {wizardStep === 4 ? (
              <>
                <p className="guided-question-card__kicker">{text("حاجة السوق والميزة", "Market need and advantage")}</p>
                <h3>{text("ما الحاجة التي يلبيها مشروعك؟ وما ميزته؟", "What need does your project address, and what is its advantage?")}</h3>
                <p>{text("لا تحتاج صياغة طويلة. اختر الأقرب، ويمكنك تعديلها أو كتابة خيارك.", "Keep it concise. Select the closest option, then edit it or add your own.")}</p>
                <div id="wizard-gap-choices" className="choice-section"><strong>{text("ما الحاجة التي لاحظتها؟", "What need did you identify?")}</strong><div className="choice-grid choice-grid--compact">{[["الخدمة غير متوفرة في موقعي", "The service is unavailable in my area"], ["الانتظار أو الوصول صعب", "Waiting or access is difficult"], ["السعر مرتفع", "The price is high"], ["الجودة أو التخصص غير كافٍ", "Quality or specialisation is insufficient"]].map(([value, labelEn]) => <button type="button" key={value} className={form.inputs.gap_statement === value ? "choice-card choice-card--active" : "choice-card"} onClick={() => updateInputs({ gap_statement: value })}>{locale === "ar" ? value : labelEn}</button>)}</div></div>
                <div id="wizard-advantage-choices" className="choice-section"><strong>{text("ما أقرب وصف لميزتك؟", "Which best describes your advantage?")}</strong><div className="choice-grid choice-grid--compact">{[["موقع أفضل", "Better location"], ["سرعة أعلى", "Faster service"], ["تخصص واضح", "Clear specialisation"], ["سعر منافس", "Competitive price"], ["تجربة أسهل", "Easier experience"]].map(([value, labelEn]) => <button type="button" key={value} className={form.inputs.competitive_edge === value ? "choice-card choice-card--active" : "choice-card"} onClick={() => {
                          updateInputs({ competitive_edge: value, activity_description: value });
                          if (form.inputs.gap_statement) setTimeout(() => advanceWizardFromChoice(), 0);
                        }}>{locale === "ar" ? value : labelEn}</button>)}</div></div>
                <div className="guided-actions"><button type="button" className="secondary-action" disabled><Sparkles size={17} aria-hidden="true" /> {text("ساعدني على صياغة الحاجة والميزة", "Help me define the need and advantage")}</button><small>{text("ستظهر المساعدة بعد تفعيلها واعتمادها.", "Assistance will appear after it is enabled and approved.")}</small></div>
              </>
            ) : null}
            {wizardStep === 5 ? (
              <>
                <p className="guided-question-card__kicker">{text("الجمهور", "Audience")}</p>
                <h3>{text("من هو جمهور المشروع؟", "Who is the project for?")}</h3>
                <div id="wizard-audience-choices" className="choice-grid" role="group" aria-label={text("جمهور المشروع", "Project audience")}>
                  {[
                    ["individuals", "أفراد", "Individuals", "مستهلكون أو مرضى أو زوار", "Consumers, patients, or visitors"],
                    ["organizations", "مؤسسات", "Organisations", "جهات ومدارس ومنشآت", "Institutions, schools, and organisations"],
                    ["companies", "شركات", "Companies", "عملاء تجاريون وتعاقدات", "Business clients and contracts"],
                    ["mixed", "مزيج", "Mixed", "أكثر من شريحة", "More than one audience segment"],
                  ].map(([value, labelAr, labelEn, detailAr, detailEn]) => (
                    <button
                      type="button"
                      key={value}
                      className={form.inputs.target_audience === value ? "choice-card choice-card--active" : "choice-card"}
                      onClick={() => { updateInputs({ target_audience: value }); advanceWizardFromChoice(); }}
                    >
                      <strong>{locale === "ar" ? labelAr : labelEn}</strong>
                      <small>{locale === "ar" ? detailAr : detailEn}</small>
                    </button>
                  ))}
                </div>
              </>
            ) : null}
            {wizardStep === 6 ? (
              <>
                <p className="guided-question-card__kicker">{text("رأس المال", "Available capital")}</p>
                <h3>{text("كم رأس المال المتاح لديك تقريبًا؟", "Approximately how much capital is available?")}</h3>
                <div className="choice-grid choice-grid--capital">{[[100000,"100 ألف","100,000"],[200000,"200 ألف","200,000"],[500000,"500 ألف","500,000"],[1000000,"مليون","1,000,000"]].map(([value,labelAr,labelEn]) => <button type="button" key={value} className={form.inputs.capital_available === value ? "choice-card choice-card--active" : "choice-card"} onClick={() => { updateInputs({ capital_available: Number(value), equity_contribution: Number(value), startup_cost: Number(value) }); advanceWizardFromChoice(); }}><strong>{locale === "ar" ? labelAr : labelEn} {text("ريال", "SAR")}</strong><small>{text("اختيار سريع", "Quick choice")}</small></button>)}<button type="button" className="choice-card choice-card--add" onClick={() => setError(text("اكتب المبلغ الحقيقي في الحقل أسفل الخيارات.", "Enter the actual amount in the field below."))}><strong>{text("مبلغ آخر", "Another amount")}</strong><small>{text("أدخل الرقم بنفسك", "Enter the amount")}</small></button></div>
                <NumberField inputId="wizard-capital-amount" label={text("المبلغ الحقيقي المتاح", "Actual available amount")} value={form.inputs.capital_available} onChange={(value) => updateInputs({ capital_available: value, equity_contribution: value, startup_cost: value })} />
              </>
            ) : null}
            {wizardStep === 7 ? (
              <>
                <p className="guided-question-card__kicker">{text("طريقة تعبئة التفاصيل", "How to provide details")}</p>
                <h3>{text("كيف تريد تزويد المنصة بتفاصيل المشروع؟", "How would you like to provide project details?")}</h3>
                <div id="wizard-intake-choices" className="choice-grid choice-grid--three" role="group" aria-label={text("طريقة تعبئة تفاصيل المشروع", "How to provide project details")}>
                  {[
                    ["manual", "أعبئ بنفسي", "Enter manually", "أدخل الأرقام الأساسية الآن.", "Enter the essential figures now."],
                    ["file", "أرفع ملفًا", "Upload a file", "ارفع ملفًا يحتوي الأرقام.", "Upload a file containing the figures."],
                    ["assisted_estimate", "مساعدة تقديرية لاحقًا", "Assisted estimate later", "غير مفعّلة حتى اكتمال الموافقة.", "Unavailable until approval is complete."],
                  ].map(([value, labelAr, labelEn, detailAr, detailEn]) => (
                    <button
                      type="button"
                      key={value}
                      className={form.inputs.intake_mode === value ? "choice-card choice-card--active" : "choice-card"}
                      onClick={() => updateInputs({ intake_mode: value })}
                      disabled={value === "assisted_estimate"}
                    >
                      <strong>{locale === "ar" ? labelAr : labelEn}</strong>
                      <small>{locale === "ar" ? detailAr : detailEn}</small>
                    </button>
                  ))}
                </div>
                {form.inputs.intake_mode === "file" ? (
                  <label className="field file-field">
                    <span>{text("ارفع ملف الأرقام", "Upload the figures file")}</span>
                    <input
                      id="wizard-data-file"
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
                  <>
                  <div className="guided-finance-lite">
                    <NumberField inputId="wizard-startup-cost" label={text("تكلفة التأسيس التقريبية", "Estimated setup cost")} value={form.inputs.startup_cost} onChange={(value) => updateInputs({ startup_cost: value })} />
                    <label className="field">
                      <span>{text("المصاريف الشهرية", "Monthly expenses")} <small>{text("(تحسب تلقائيًا)", "(calculated automatically)")}</small></span>
                      <output className="derived-number-field">{monthlyFixedCostFromInputs(form.inputs).toLocaleString("ar-SA")}</output>
                    </label>
                    <NumberField inputId="wizard-unit-price" label={text("سعر البيع أو الخدمة", "Product or service price")} value={form.inputs.unit_price} onChange={(value) => updateInputs({ unit_price: value })} />
                    <NumberField inputId="wizard-variable-cost" label={text("تكلفة تقديم الخدمة", "Service delivery cost")} value={form.inputs.variable_cost} onChange={(value) => updateInputs({ variable_cost: value })} />
                    <NumberField inputId="wizard-monthly-units" label={text("عدد العملاء أو الطلبات شهرياً", "Monthly customers or orders")} value={form.inputs.monthly_units} onChange={(value) => updateInputs({ monthly_units: value })} />
                  </div>
                  <details className="manual-advanced-fields" open>
                    <summary>{text("إضافة تفاصيل تشغيلية أدق", "Add detailed operating information")} <small>{text("(اختياري)", "(optional)")}</small></summary>
                    <p className="muted">{text("لا تُراجع هذه البنود ولا تدخل قائمة الافتراضات إلا إذا كتبت قيمة فعلية فيها.", "These items are not reviewed or added to assumptions unless you enter an actual value.")}</p>
                    <strong>{text("تفصيل المصاريف الشهرية", "Monthly expense details")}</strong>
                    <div className="other-monthly-costs">
                      <div className="other-monthly-costs__heading">
                        <strong>{text("بنود شهرية أخرى", "Other monthly items")}</strong>
                        <button type="button" className="secondary-action" onClick={() => setForm((current) => ({ ...current, inputs: { ...current.inputs, other_monthly_costs: [...(current.inputs.other_monthly_costs ?? []), { name: "", amount: 0 }] } }))}>{text("+ إضافة بند", "+ Add item")}</button>
                      </div>
                      <p className="muted">{text("مثل: التأمين، الاشتراكات، النظافة، النقل، الاتصالات أو أي مصروف آخر.", "For example: insurance, subscriptions, cleaning, transport, communications, or another expense.")}</p>
                      {(form.inputs.other_monthly_costs ?? []).map((item, index) => (
                        <div className="other-monthly-cost-row" key={index}>
                          <input maxLength={60} placeholder={text("اسم المصروف", "Expense name")} value={item.name} onChange={(event) => setForm((current) => {
                            const rows = [...(current.inputs.other_monthly_costs ?? [])];
                            rows[index] = { ...rows[index], name: event.target.value };
                            return { ...current, inputs: { ...current.inputs, other_monthly_costs: rows } };
                          })} />
                          <NumberField label={text("المبلغ الشهري", "Monthly amount")} value={item.amount} onChange={(value) => setForm((current) => {
                            const rows = [...(current.inputs.other_monthly_costs ?? [])];
                            rows[index] = { ...rows[index], amount: value };
                            return { ...current, inputs: { ...current.inputs, other_monthly_costs: rows } };
                          })} />
                          <button type="button" className="secondary-action" onClick={() => setForm((current) => ({ ...current, inputs: { ...current.inputs, other_monthly_costs: (current.inputs.other_monthly_costs ?? []).filter((_, rowIndex) => rowIndex !== index) } }))}>{text("حذف", "Remove")}</button>
                        </div>
                      ))}
                    </div>
                    <div className="guided-finance-lite">
                      <NumberField label={text("الرواتب الشهرية", "Monthly payroll")} value={form.inputs.payroll_monthly} onChange={(value) => updateInputs({ payroll_monthly: value })} />
                      <NumberField label={text("الإيجار الشهري", "Monthly rent")} value={form.inputs.rent_monthly} onChange={(value) => updateInputs({ rent_monthly: value })} />
                      <NumberField label={text("المرافق الشهرية", "Monthly utilities")} value={form.inputs.utilities_monthly} onChange={(value) => updateInputs({ utilities_monthly: value })} />
                      <NumberField label={text("التسويق الشهري", "Monthly marketing")} value={form.inputs.marketing_monthly} onChange={(value) => updateInputs({ marketing_monthly: value })} />
                      <NumberField label={text("الصيانة الشهرية", "Monthly maintenance")} value={form.inputs.maintenance_monthly} onChange={(value) => updateInputs({ maintenance_monthly: value })} />
                    </div>
                    <strong>{text("تفصيل التأسيس والأصول", "Setup and asset details")}</strong>
                    <div className="guided-finance-lite">
                      <NumberField label={text("المعدات", "Equipment")} value={form.inputs.capex_equipment} onChange={(value) => updateInputs({ capex_equipment: value })} />
                      <NumberField label={text("التجهيز والديكور", "Fit-out and furnishing")} value={form.inputs.capex_fitout} onChange={(value) => updateInputs({ capex_fitout: value })} />
                      <NumberField label={text("التراخيص المحلية", "Local licences")} value={form.inputs.capex_licenses_local} onChange={(value) => updateInputs({ capex_licenses_local: value })} />
                      <NumberField label={text("سنوات الإهلاك", "Depreciation years")} value={form.inputs.depreciation_years} onChange={(value) => updateInputs({ depreciation_years: value })} />
                      <NumberField label={text("المساهمة الذاتية", "Owner contribution")} value={form.inputs.equity_contribution} onChange={(value) => updateInputs({ equity_contribution: value })} />
                    </div>
                  </details>
                  <div className="choice-section financing-inputs" id="financing-inputs">
                    <strong>{text("افتراضات التمويل", "Financing assumptions")}</strong>
                    <p className="muted">{text("إذا لن تستخدم قرضًا، اترك مبلغ القرض صفرًا. معدل الخصم مطلوب لتقييم القيمة الحالية.", "If you will not use a loan, leave the loan amount at zero. A discount rate is required to assess present value.")}</p>
                    <div className="guided-finance-lite">
                      <NumberField inputId="wizard-discount-rate" label={text("معدل الخصم السنوي (%)", "Annual discount rate (%)")} value={Math.round(form.inputs.annual_discount_rate * 10000) / 100} onChange={(value) => updateInputs({ annual_discount_rate: value / 100 })} />
                      <NumberField label={text("أشهر رأس المال العامل", "Working-capital months")} value={form.inputs.working_capital_months} onChange={(value) => updateInputs({ working_capital_months: value })} />
                      <NumberField label={text("مبلغ القرض — صفر إذا لا يوجد", "Loan amount — zero if none")} value={form.inputs.debt_amount} onChange={(value) => updateInputs({ debt_amount: value })} />
                      {form.inputs.debt_amount > 0 ? (
                        <>
                          <NumberField inputId="wizard-interest-rate" label={text("معدل تكلفة التمويل السنوي (%)", "Annual financing cost (%)")} value={Math.round(form.inputs.annual_interest_rate * 10000) / 100} onChange={(value) => updateInputs({ annual_interest_rate: value / 100 })} />
                          <NumberField inputId="wizard-loan-years" label={text("مدة القرض بالسنوات", "Loan term in years")} value={form.inputs.loan_years} onChange={(value) => updateInputs({ loan_years: value })} />
                          <NumberField label={text("فترة السماح بالأشهر", "Grace period in months")} value={form.inputs.loan_grace_months} onChange={(value) => updateInputs({ loan_grace_months: value })} />
                        </>
                      ) : null}
                    </div>
                  </div>
                  </>
                ) : null}
                {project ? (
                  <div className="choice-section assumption-review-panel" id="assumption-human-review">
                    <div className="assumption-review-panel__heading">
                      <div>
                        <strong>{text("مراجعة المدخلات والافتراضات", "Review inputs and assumptions")}</strong>
                        <p className="muted">{text("راجع الملخصات، وافتح التفاصيل عند الحاجة، ثم اعتمد كل مجموعة.", "Review each summary, open details when needed, then approve each group.")}</p>
                      </div>
                      <span className="review-progress">
                        {assumptions.filter((item) => item.review_status === "approved").length} {text("من", "of")} {assumptions.length} {text("مكتملة", "complete")}
                      </span>
                    </div>
                    <div className="review-group-list">
                      {assumptionReviewGroups.map((group) => {
                        const groupItems = assumptions.filter((item) => group.keys.includes(item.input_key));
                        if (!groupItems.length) return null;
                        const pendingCount = groupItems.filter((item) => item.review_status !== "approved").length;
                        return (
                          <article className={pendingCount ? "review-group" : "review-group review-group--complete"} key={group.id}>
                            <div className="review-group__summary">
                              <div>
                                <strong>{locale === "ar" ? group.label : group.labelEn}</strong>
                                <small>{groupItems.length} {text("بنود", "items")} · {pendingCount ? `${pendingCount} ${text("بانتظار المراجعة", "awaiting review")}` : text("تمت مراجعتها", "Reviewed")}</small>
                              </div>
                              {pendingCount ? (
                                <button type="button" className="primary-button" disabled={isBusy} onClick={() => handleApproveAssumptions(groupItems)}>
                                  {text("اعتماد المجموعة", "Approve group")}
                                </button>
                              ) : (
                                <span className="review-complete"><CheckCircle2 size={16} aria-hidden="true" /> {text("مكتملة", "Complete")}</span>
                              )}
                            </div>
                            <details>
                              <summary>{text("عرض القيم ومراجعتها", "View and review values")}</summary>
                              <div className="review-group__items">
                                {groupItems.map((item) => (
                                  <div key={item.assumption_id}>
                                    <strong>{assumptionLabel(item, locale)}</strong>
                                    <span>{item.value || text("غير محدد", "Not specified")} {item.unit === "unit" ? "" : item.unit}</span>
                                    <small>{item.review_status === "approved" ? text("معتمد", "Approved") : text("بانتظار المراجعة", "Awaiting review")}</small>
                                  </div>
                                ))}
                              </div>
                            </details>
                          </article>
                        );
                      })}
                    </div>
                    {assumptions.length ? (
                      <button type="button" className="secondary-action review-all-button" disabled={isBusy || assumptions.every((item) => item.review_status === "approved")} onClick={() => handleApproveAssumptions(assumptions)}>
                        {text("راجعت جميع المجموعات وأعتمدها", "I reviewed and approve all groups")}
                      </button>
                    ) : <p className="muted">{text("احفظ بيانات المشروع مرة أخرى لإنشاء قائمة الافتراضات المطلوب مراجعتها.", "Save the project again to create the list of assumptions for review.")}</p>}
                  </div>
                ) : (
                  <p className="guided-hint">{text("احفظ بيانات المشروع أولًا، ثم ستظهر هنا مراجعة مختصرة ومجمعة.", "Save the project first, then a concise grouped review will appear here.")}</p>
                )}
              </>
            ) : null}
          </div>
        </section>

        {authUser?.platform_role === "platform_admin" ? (
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
                          <strong>{metricTitle(item.output_id, locale)}</strong>
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
                    <dd>{overview.sector_intelligence.taxonomy_record.subsector_id ? arabicSubsectorLabel(overview.sector_intelligence.taxonomy_record.subsector_id) : "غير محدد"}</dd>
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
                      <span>{statusText(source.state, locale)}</span>
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
                    <button className="secondary-action" onClick={() => void handleOpenDocument(decisionPack.snapshot_id, "decision-pack.html", "open")}>
                      فتح حزمة القرار HTML
                    </button>
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
                    <button className="secondary-action" onClick={() => void handleOpenDocument(report.snapshot_id, "report.html", "open")}>
                      فتح تقرير HTML المحلي
                    </button>
                  </div>
                ) : (
                  <p className="muted">شغّل التقرير لقراءة نفس لقطة التشغيل بدون إعادة حساب.</p>
                )}
              </div>
            </section>
          </>
        ) : null}
        </div>
        ) : null}
        </>
        ) : (
          <section
            className="panel overlay-panel"
            aria-label={overlay === "settings"
              ? text("الحساب والفريق", "Account and team")
              : text("خيارات التمويل والقطاع", "Funding and sector options")}
          >
            <div className="section-title">
              {overlay === "settings" ? <Users size={20} aria-hidden="true" /> : <BarChart3 size={20} aria-hidden="true" />}
              <h2>
                {overlay === "settings"
                  ? text("الحساب والفريق", "Account and team")
                  : text("خيارات التمويل والقطاع", "Funding and sector options")}
              </h2>
              <button className="secondary-action" onClick={closeOverlay}>
                {text("عودة إلى المسار", "Return to journey")}
              </button>
            </div>

            {overlay === "settings" ? (
              <div className="overlay-stack">
                {authState === "legacy" ? (
                  <article className="admin-panel">
                    <h3>{text("ابدأ حساب البيتا", "Start your beta account")}</h3>
                    <p className="muted">
                      {text(
                        "استخدم دعوة بيتا المرتبطة ببريدك لإنشاء حساب ومنظمة منفصلين وآمنين.",
                        "Use the beta invitation linked to your email to create a separate, secure account and organisation.",
                      )}
                    </p>
                    <button className="primary-button" onClick={() => { setAuthInitialMode("register"); setAuthState("anonymous"); }}>
                      <Rocket size={17} aria-hidden="true" /> {text("إنشاء حساب بيتا بدعوة", "Create an invited beta account")}
                    </button>
                  </article>
                ) : null}

                {authState === "authenticated" ? (
                  <>
                    <article className="admin-panel">
                      <h3>{text("حسابك الحالي", "Your current account")}</h3>
                      <p>
                        <strong>{authUser?.display_name || authUser?.email || text("حساب مستخدم", "User account")}</strong>
                      </p>
                      {authUser?.display_name && authUser?.email ? <p className="muted">{authUser.email}</p> : null}
                      <button className="secondary-action" onClick={() => void handleLogout()}>
                        {text("تسجيل الخروج وإنهاء الجلسة", "Sign out and end session")}
                      </button>
                    </article>

                    <article className="admin-panel">
                      <h3>{text("منظمتك النشطة", "Your active organisation")}</h3>
                      {memberships.length ? (
                        <div className="org-chip-row">
                          {memberships.map((membership, index) => (
                            <button
                              key={membership.organization_id}
                              className={membership.organization_id === activeOrganizationId ? "org-chip org-chip--active" : "org-chip"}
                              onClick={() => switchOrganization(membership.organization_id)}
                            >
                              <strong>
                                {membership.organization_name || text(`منظمة ${index + 1}`, `Organisation ${index + 1}`)}
                              </strong>
                              <small>{customerBusinessText(membership.role, locale)}</small>
                            </button>
                          ))}
                        </div>
                      ) : (
                        <p className="muted">
                          {text("لا توجد منظمة بعد. أنشئ منظمتك الأولى أدناه.", "No organisation exists yet. Create your first one below.")}
                        </p>
                      )}
                      <form className="inline-form" onSubmit={handleCreateOrganization}>
                        <label>
                          {text("منظمة جديدة", "New organisation")}
                          <input
                            maxLength={80}
                            value={newOrganizationName}
                            onChange={(event) => setNewOrganizationName(event.target.value)}
                            placeholder={text("اسم المنظمة", "Organisation name")}
                          />
                        </label>
                        <button className="primary-button" disabled={isBusy || !newOrganizationName.trim()}>
                          {text("إنشاء المنظمة واستخدامها", "Create and use organisation")}
                        </button>
                      </form>
                    </article>

                    <article className="admin-panel">
                      <h3>{text("الفريق والدعوات", "Team and invitations")}</h3>
                      <p className="muted">
                        {text(
                          "تُدار دعوات الفريق وصلاحياته من لوحة الإدارة المحمية، ولا تحتاج إلى نسخ معرّفات تقنية.",
                          "Team invitations and permissions are managed in the protected administration area; no technical identifiers are required.",
                        )}
                      </p>
                      {authUser?.platform_role === "platform_admin" ? (
                        <button
                          className="secondary-action"
                          onClick={() => {
                            closeOverlay();
                            setStage("architecture");
                          }}
                        >
                          {text("فتح لوحة الإدارة المحمية", "Open protected administration")}
                        </button>
                      ) : null}
                    </article>
                  </>
                ) : null}
              </div>
            ) : (
              <div className="overlay-stack">
                <p className="muted">
                  {text(
                    "هذه خيارات استرشادية محفوظة داخل المنصة لمساعدتك في اختيار مسار التمويل والقطاع. لا تجلب بيانات خارجية ولا تغيّر نتائج مشروعك.",
                    "These saved guidance options help you choose a funding route and sector. They do not fetch external data or change your project results.",
                  )}
                </p>
                <article className="admin-panel">
                  <h3>{text("خيارات التمويل", "Funding options")}</h3>
                  {fundingProfiles.length ? (
                    <div className="profile-grid">
                      {fundingProfiles.map((profile, index) => (
                        <article key={String(profile.profile_id ?? index)} className="profile-card">
                          <h4>{customerBusinessText(String(profile.profile_id ?? ""), locale)}</h4>
                          <p className="muted">
                            {text(
                              "افتح مشروعك لاختيار هذا المسار ومراجعة متطلباته بلغة واضحة.",
                              "Open your project to select this route and review its requirements in clear language.",
                            )}
                          </p>
                        </article>
                      ))}
                    </div>
                  ) : (
                    <p className="muted">{text("لا تتوفر خيارات تمويل بعد.", "No funding options are available yet.")}</p>
                  )}
                </article>
                <article className="admin-panel">
                  <h3>{text("القطاعات المتاحة", "Available sectors")}</h3>
                  {sectorProfiles.length ? (
                    <div className="profile-grid">
                      {sectorProfiles.map((profile, index) => (
                        <article key={String(profile.profile_id ?? profile.sector_id ?? index)} className="profile-card">
                          <h4>{customerBusinessText(String(profile.sector_id ?? profile.profile_id ?? ""), locale)}</h4>
                          <p className="muted">
                            {text(
                              "اختر القطاع داخل تعريف المشروع لتخصيص الأسئلة والتحليل.",
                              "Choose the sector while setting up the project to tailor questions and analysis.",
                            )}
                          </p>
                        </article>
                      ))}
                    </div>
                  ) : (
                    <p className="muted">{text("لا تتوفر قطاعات بعد.", "No sectors are available yet.")}</p>
                  )}
                </article>
              </div>
            )}
          </section>
        )}
      </section>
    </main>
  );
}
