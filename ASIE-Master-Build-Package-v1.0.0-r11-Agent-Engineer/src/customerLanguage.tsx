import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

export type CustomerLocale = "ar" | "en";

const CUSTOMER_LOCALE_STORAGE_KEY = "asie.customer_locale.v1";
const DEFAULT_CUSTOMER_LOCALE: CustomerLocale = "ar";

type CustomerLanguageContextValue = {
  locale: CustomerLocale;
  selectionVersion: number;
  direction: "rtl" | "ltr";
  setLocale: (locale: CustomerLocale) => void;
  text: (arabic: string, english: string) => string;
};

const CustomerLanguageContext = createContext<CustomerLanguageContextValue | null>(null);

export function customerLocaleFromUrl(search = window.location.search): CustomerLocale | null {
  try {
    const requested = new URLSearchParams(search).get("lang");
    return requested === "ar" || requested === "en" ? requested : null;
  } catch {
    return null;
  }
}

function readStoredLocale(): CustomerLocale {
  const linkedLocale = customerLocaleFromUrl();
  if (linkedLocale) return linkedLocale;
  try {
    const stored = window.localStorage.getItem(CUSTOMER_LOCALE_STORAGE_KEY);
    return stored === "en" ? "en" : DEFAULT_CUSTOMER_LOCALE;
  } catch {
    return DEFAULT_CUSTOMER_LOCALE;
  }
}

function writeLocaleToUrl(locale: CustomerLocale) {
  try {
    const url = new URL(window.location.href);
    url.searchParams.set("lang", locale);
    window.history.replaceState(window.history.state, "", `${url.pathname}${url.search}${url.hash}`);
  } catch {
    // Language remains active even when the browser blocks URL state changes.
  }
}

export function CustomerLanguageProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<CustomerLocale>(() => readStoredLocale());
  const [selectionVersion, setSelectionVersion] = useState(0);

  function setLocale(nextLocale: CustomerLocale) {
    setLocaleState(nextLocale);
    setSelectionVersion((version) => version + 1);
    writeLocaleToUrl(nextLocale);
    try {
      window.localStorage.setItem(CUSTOMER_LOCALE_STORAGE_KEY, nextLocale);
    } catch {
      // The selected language still applies to the current session.
    }
  }

  useEffect(() => {
    document.documentElement.lang = locale;
    document.documentElement.dir = locale === "ar" ? "rtl" : "ltr";
    document.title = locale === "ar" ? "ASIE | مرصد القرار المحلي" : "ASIE | Local decision workspace";
    const skipLink = document.querySelector<HTMLAnchorElement>('a.skip-link[href="#main-content"]');
    if (skipLink) skipLink.textContent = locale === "ar" ? "تجاوز إلى المحتوى الرئيسي" : "Skip to main content";
  }, [locale]);

  const value = useMemo<CustomerLanguageContextValue>(
    () => ({
      locale,
      selectionVersion,
      direction: locale === "ar" ? "rtl" : "ltr",
      setLocale,
      text: (arabic, english) => (locale === "ar" ? arabic : english),
    }),
    [locale, selectionVersion]
  );

  return <CustomerLanguageContext.Provider value={value}>{children}</CustomerLanguageContext.Provider>;
}

export function useCustomerLanguage(): CustomerLanguageContextValue {
  const context = useContext(CustomerLanguageContext);
  if (!context) throw new Error("CustomerLanguageProvider is required");
  return context;
}

export function CustomerLanguageSwitcher({ className = "" }: { className?: string }) {
  const { locale, setLocale, text } = useCustomerLanguage();
  return (
    <div className={`customer-language-switcher ${className}`} role="group" aria-label={text("اختيار اللغة", "Language selection")}>
      <button
        type="button"
        className={locale === "ar" ? "is-active" : ""}
        aria-pressed={locale === "ar"}
        onClick={() => setLocale("ar")}
      >
        العربية
      </button>
      <button
        type="button"
        className={locale === "en" ? "is-active" : ""}
        aria-pressed={locale === "en"}
        onClick={() => setLocale("en")}
      >
        English
      </button>
    </div>
  );
}

const customerStatuses: Record<string, { ar: string; en: string }> = {
  ready: { ar: "جاهز", en: "Ready" },
  passed: { ar: "مكتمل", en: "Passed" },
  warning: { ar: "يحتاج انتباهًا", en: "Needs attention" },
  blocked: { ar: "متوقف حتى استكمال المتطلبات", en: "Blocked until requirements are completed" },
  ready_with_warnings: { ar: "جاهز مع ملاحظات", en: "Ready with notes" },
  needs_input: { ar: "يحتاج مدخلات", en: "Needs input" },
  insufficient_data: { ar: "البيانات غير كافية", en: "Insufficient data" },
  completed: { ar: "مكتمل", en: "Completed" },
  preliminary_only: { ar: "تقييم أولي", en: "Preliminary assessment" },
  revise_and_reassess: { ar: "راجع المدخلات وأعد التقييم", en: "Review inputs and reassess" },
  blocked_not_ready: { ar: "متوقف لمدخلات ناقصة", en: "Blocked by missing inputs" },
  user_verified: { ar: "أكده المستخدم", en: "User verified" },
  demo_data: { ar: "بيانات تجريبية", en: "Demo data" },
  candidate: { ar: "مرشح للمراجعة", en: "Review candidate" },
  reference_only: { ar: "مرجع إرشادي", en: "Guidance only" },
  approved_for_use: { ar: "معتمد للاستخدام", en: "Approved for use" },
  review_required: { ar: "بانتظار المراجعة", en: "Awaiting review" },
  draft_review: { ar: "بانتظار المراجعة", en: "Awaiting review" },
  rejected: { ar: "مرفوض", en: "Rejected" },
  unknown: { ar: "غير محدد", en: "Not specified" },
  approved: { ar: "معتمد", en: "Approved" },
  approved_local: { ar: "معتمد داخليًا", en: "Internally approved" },
  draft: { ar: "مسودة", en: "Draft" },
  needs_review: { ar: "يحتاج مراجعة", en: "Needs review" },
  pending: { ar: "قيد الانتظار", en: "Pending" },
  enabled: { ar: "مفعّل", en: "Enabled" },
  disabled: { ar: "غير مفعّل", en: "Disabled" },
  closed: { ar: "مغلق", en: "Closed" },
  open: { ar: "مفتوح", en: "Open" },
  high: { ar: "مرتفع", en: "High" },
  medium: { ar: "متوسط", en: "Medium" },
  low: { ar: "منخفض", en: "Low" },
  not_ready: { ar: "غير جاهز", en: "Not ready" },
};

function normalizeStatus(value: string): string {
  return value.trim().toLowerCase().replace(/[^a-z0-9\u0600-\u06ff]+/gi, "_").replace(/^_+|_+$/g, "");
}

export function customerStatusText(value: unknown, locale: CustomerLocale): string {
  if (typeof value !== "string" || !value.trim()) return locale === "ar" ? "غير محدد" : "Not specified";
  const status = customerStatuses[normalizeStatus(value)];
  return status?.[locale] ?? (locale === "ar" ? "حالة تحتاج مراجعة" : "Status requires review");
}

const customerErrors: Array<{ pattern: RegExp; ar: string; en: string }> = [
  { pattern: /^(dib_blueprint_write_conflict|recovery_source_changed|dib_blueprint_origin_required)$/, ar: "تغيرت النسخة الأصلية. احتُفظ بعملك؛ راجع التعارض قبل إعادة الحفظ.", en: "The original version changed. Your work is retained; review the conflict before saving again." },
  { pattern: /^recovery_target_missing$/, ar: "حُذف الهدف أو تغيرت صلاحيته. احتُفظ بعملك؛ اختر الهدف الحالي.", en: "The target was removed or its eligibility changed. Your work is retained; choose the current target." },
  { pattern: /^(recovery_input_invalid|recovery_content_required|recovery_reason_required|dib_item_value_invalid|dib_item_reason_required)$/, ar: "أكمل القيمة والسبب المطلوبين قبل الحفظ.", en: "Complete the required value and reason before saving." },
  { pattern: /invalid_credentials/i, ar: "بيانات الدخول غير صحيحة.", en: "The sign-in details are incorrect." },
  { pattern: /registration_invite_invalid/i, ar: "رمز الدعوة غير صالح أو لا يطابق هذا البريد.", en: "The invitation code is invalid or does not match this email." },
  { pattern: /password_length_must_be_between_6_and_12_characters/i, ar: "يجب أن تتكون كلمة المرور من 6 إلى 12 حرفًا.", en: "The password must contain 6 to 12 characters." },
  { pattern: /email_already_registered/i, ar: "هذا البريد مسجل بالفعل. استخدم تسجيل الدخول.", en: "This email is already registered. Please sign in." },
  { pattern: /invalid_or_expired_recovery_token/i, ar: "رمز الاستعادة غير صالح أو منتهي. اطلب رمزًا جديدًا.", en: "The recovery code is invalid or expired. Request a new code." },
  { pattern: /local_bootstrap_unavailable/i, ar: "إنشاء الحساب غير متاح الآن. حاول لاحقًا أو تواصل مع مشرف البيتا.", en: "Account creation is temporarily unavailable. Try again later or contact the beta administrator." },
  { pattern: /unauthorized|forbidden|permission/i, ar: "ليست لديك صلاحية لتنفيذ هذا الإجراء.", en: "You do not have permission to perform this action." },
  { pattern: /report_export_unavailable/i, ar: "تعذر تجهيز ملف التقرير الآن. حاول مرة أخرى لاحقًا.", en: "The report file could not be prepared. Try again later." },
  { pattern: /network|fetch|timeout|timed out/i, ar: "تعذر الاتصال بالخدمة. تحقق من الشبكة ثم أعد المحاولة.", en: "The service could not be reached. Check your connection and try again." },
];

export function customerErrorText(reason: unknown, locale: CustomerLocale): string {
  const code = reason && typeof reason === "object" && "code" in reason && typeof reason.code === "string" ? reason.code : null;
  const raw = code ?? (reason instanceof Error ? reason.message : typeof reason === "string" ? reason : "");
  const match = customerErrors.find((entry) => entry.pattern.test(raw));
  if (match) return match[locale];
  return locale === "ar"
    ? "تعذر إتمام الطلب. حاول مرة أخرى، وإذا استمرت المشكلة تواصل مع مشرف البيتا."
    : "The request could not be completed. Try again, and contact the beta administrator if the problem continues.";
}


const customerSourceNames: Record<string, { ar: string; en: string }> = {
  gastat_candidate: { ar: "الهيئة العامة للإحصاء", en: "General Authority for Statistics" },
  general_authority_for_statistics: { ar: "الهيئة العامة للإحصاء", en: "General Authority for Statistics" },
  sama_candidate: { ar: "البنك المركزي السعودي", en: "Saudi Central Bank" },
  saudi_central_bank: { ar: "البنك المركزي السعودي", en: "Saudi Central Bank" },
  mof_candidate: { ar: "وزارة المالية", en: "Ministry of Finance" },
  ministry_of_finance: { ar: "وزارة المالية", en: "Ministry of Finance" },
  vision_2030_reference: { ar: "رؤية السعودية 2030", en: "Saudi Vision 2030" },
  monshaat: { ar: "الهيئة العامة للمنشآت الصغيرة والمتوسطة", en: "Small and Medium Enterprises General Authority" },
};

export function customerSourceName(value: unknown, locale: CustomerLocale): string {
  if (typeof value !== "string" || !value.trim()) return locale === "ar" ? "مصدر قيد المراجعة" : "Source under review";
  const normalized = normalizeStatus(value);
  const mapped = customerSourceNames[normalized];
  if (mapped) return mapped[locale];
  const clean = value.trim();
  const hasArabic = /[\u0600-\u06ff]/.test(clean);
  const looksInternal = /(?:candidate|reference|source|[_]{1,})/i.test(clean);
  if (!looksInternal && ((locale === "ar" && hasArabic) || (locale === "en" && !hasArabic))) return clean;
  return locale === "ar" ? "مصدر قيد المراجعة" : "Source under review";
}

const forbiddenCustomerToken = /(?:\b(?:project|run|snapshot|profile|contract|review|projection|release|algorithm|engine|session|manifest|validation_gate|payload|hash)_id\b|\b(?:not_ready|review_required|demo_or_user_input_only|blocked_not_ready|no_evidence_links)\b)/i;

export function containsForbiddenCustomerToken(value: string): boolean {
  return forbiddenCustomerToken.test(value);
}

const forbiddenOperationalDetail = /(?:\b(?:tavily|pinecone|deepseek|google places|api key|secret|environment variable|traceback|exception|stack trace|http [45]\d\d)\b|[_]{1,})/i;

export function customerMessageText(value: unknown, locale: CustomerLocale): string {
  const raw = typeof value === "string" ? value.trim() : "";
  if (!raw || containsForbiddenCustomerToken(raw) || forbiddenOperationalDetail.test(raw)) {
    return customerErrorText(value, locale);
  }
  const hasArabic = /[\u0600-\u06ff]/.test(raw);
  if ((locale === "ar" && hasArabic) || (locale === "en" && !hasArabic)) return raw;
  return customerErrorText(value, locale);
}

const customerUnits: Record<string, { ar: string; en: string }> = {
  sar: { ar: "ر.س", en: "SAR" },
  sar_month: { ar: "ر.س شهريًا", en: "SAR/month" },
  sar_year: { ar: "ر.س سنويًا", en: "SAR/year" },
  percent: { ar: "٪", en: "%" },
  percentage: { ar: "٪", en: "%" },
  probability: { ar: "احتمال", en: "Probability" },
  count: { ar: "عدد", en: "Count" },
  unit: { ar: "وحدة", en: "Unit" },
  units: { ar: "وحدة", en: "Units" },
  month: { ar: "شهر", en: "Month" },
  months: { ar: "شهر", en: "Months" },
  year: { ar: "سنة", en: "Year" },
  years: { ar: "سنة", en: "Years" },
  day: { ar: "يوم", en: "Day" },
  days: { ar: "يوم", en: "Days" },
  ratio: { ar: "نسبة", en: "Ratio" },
};

export function customerUnitText(value: unknown, locale: CustomerLocale): string {
  if (typeof value !== "string" || !value.trim()) return "";
  const normalized = normalizeStatus(value).replace(/_per_/g, "_");
  return customerUnits[normalized]?.[locale] ?? (locale === "ar" ? "وحدة قياس" : "Unit");
}


const customerBusinessTerms: Record<string, { ar: string; en: string }> = {
  execution_readiness_index: { ar: "جاهزية التنفيذ", en: "Execution readiness" },
  commercial_acceptance_index: { ar: "قابلية السوق", en: "Market acceptance" },
  technical_robustness_index: { ar: "متانة التشغيل", en: "Operational robustness" },
  transition_readiness_index: { ar: "جاهزية الانتقال", en: "Transition readiness" },
  pressure_survival_index: { ar: "القدرة على تحمل الضغوط", en: "Pressure resilience" },
  setup: { ar: "تحديد نطاق المشروع", en: "Define project scope" },
  procurement: { ar: "تأكيد المشتريات", en: "Confirm procurement" },
  staffing: { ar: "تجهيز فريق العمل", en: "Prepare the team" },
  launch: { ar: "بدء التشغيل", en: "Launch operations" },
  stabilization: { ar: "استقرار التشغيل", en: "Stabilize operations" },
  project_manager: { ar: "مدير المشروع", en: "Project manager" },
  business_advisor: { ar: "مستشار الأعمال", en: "Business advisor" },
  analyst_coach: { ar: "مستشار التحليل", en: "Analysis advisor" },
  technical_auditor: { ar: "مراجع الأدلة", en: "Evidence reviewer" },
  project_scope_signed: { ar: "اعتماد نطاق المشروع", en: "Approve project scope" },
  capex_items_confirmed: { ar: "تأكيد بنود التأسيس", en: "Confirm setup items" },
  staffing_plan_ready: { ar: "اعتماد خطة الفريق", en: "Approve team plan" },
  operating_capacity_ready: { ar: "تأكيد القدرة التشغيلية", en: "Confirm operating capacity" },
  first_month_kpis_reviewed: { ar: "مراجعة نتائج الشهر الأول", en: "Review first-month results" },
  opex_above_60_percent_of_revenue: { ar: "المصروفات التشغيلية مرتفعة مقارنة بالإيراد", en: "Operating costs are high relative to revenue" },
  no_enabled_open_data_source: { ar: "لا يوجد مصدر سوق معتمد ومفعّل", en: "No approved market source is enabled" },
  no_enabled_open_data_sources: { ar: "لا توجد مصادر سوق معتمدة ومفعّلة", en: "No approved market sources are enabled" },
  no_evidence_links: { ar: "لا توجد أدلة مرتبطة بالافتراضات المهمة", en: "No evidence is linked to key assumptions" },
  no_assumption_evidence_links: { ar: "الافتراضات المهمة غير مرتبطة بأدلة", en: "Key assumptions are not linked to evidence" },
  financial_readiness: { ar: "الجاهزية المالية", en: "Financial readiness" },
  evidence_readiness: { ar: "جاهزية الأدلة", en: "Evidence readiness" },
  source_governance: { ar: "اعتماد المصادر", en: "Source approval" },
  launch_readiness: { ar: "جاهزية بدء التشغيل", en: "Launch readiness" },
  assumption_support_gap: { ar: "نقص في الأدلة الداعمة", en: "Supporting evidence is missing" },
  margin_pressure: { ar: "ضغط على هامش الربح", en: "Profit margin pressure" },
  organization_owner: { ar: "مالك المنظمة", en: "Organisation owner" },
  organization_reviewer: { ar: "مراجع المنظمة", en: "Organisation reviewer" },
  organization_member: { ar: "عضو في المنظمة", en: "Organisation member" },
  bank_sme_base_v1: { ar: "تمويل المنشآت الصغيرة والمتوسطة", en: "Small and medium enterprise funding" },
  base_funding_v1: { ar: "تمويل تأسيسي", en: "Foundation funding" },
  development_fund_base_v1: { ar: "تمويل من صندوق تنموي", en: "Development fund financing" },
  investor_equity_base_v1: { ar: "استثمار مقابل حصة ملكية", en: "Equity investment" },
  sec_05: { ar: "الصناعة والتصنيع", en: "Manufacturing" },
  sec_07: { ar: "العقارات", en: "Real estate" },
  sec_08: { ar: "اللوجستيات وسلاسل الإمداد", en: "Logistics and supply chain" },
  sec_09: { ar: "السياحة والترفيه", en: "Tourism and entertainment" },
  sec_11: { ar: "التقنية والابتكار", en: "Technology and innovation" },
  sec_12: { ar: "القطاع المالي", en: "Financial services" },
  sec_14: { ar: "الصحة والطب", en: "Healthcare" },
  sec_17: { ar: "الأغذية والزراعة والأمن الغذائي", en: "Agriculture, food, and food security" },
  sector_retail_v1: { ar: "قطاع التجزئة", en: "Retail sector" },
  sector_manufacturing_v1: { ar: "قطاع التصنيع", en: "Manufacturing sector" },
  sector_food_service_v1: { ar: "قطاع الأغذية والمطاعم", en: "Food service sector" },
  sector_digital_services_v1: { ar: "قطاع الخدمات الرقمية", en: "Digital services sector" },
  negative_npv: { ar: "القيمة الحالية للمشروع سالبة", en: "The project's net present value is negative" },
  non_positive_monthly_profit: { ar: "الربح الشهري المتوقع غير موجب", en: "Expected monthly profit is not positive" },
  reduce_fixed_opex_or_increase_validated_revenue_capacity: { ar: "خفّض المصروفات الثابتة أو أثبت قدرة أعلى على تحقيق الإيراد.", en: "Reduce fixed costs or validate a higher revenue capacity." },
  complete_human_review_for_exact_open_datasets: { ar: "أكمل المراجعة البشرية لمصادر البيانات المفتوحة المحددة.", en: "Complete human review of the selected open datasets." },
  link_approved_datasets_to_critical_assumptions: { ar: "اربط المصادر المعتمدة بالافتراضات المؤثرة في القرار.", en: "Link approved sources to the assumptions that affect the decision." },
  deterministic_local_evaluator_reads_allowed_finance_readiness_sector_envelopes_only: { ar: "تقييم منضبط يعتمد فقط على بيانات المشروع والجاهزية والقطاع المسموح بها.", en: "A controlled assessment based only on permitted project, readiness, and sector data." },
};

export function customerBusinessText(value: unknown, locale: CustomerLocale): string {
  if (typeof value !== "string" || !value.trim()) return locale === "ar" ? "غير محدد" : "Not specified";
  const normalized = normalizeStatus(value);
  return customerBusinessTerms[normalized]?.[locale]
    ?? customerStatuses[normalized]?.[locale]
    ?? (locale === "ar" ? "تفصيل يحتاج مراجعة" : "Detail requires review");
}


export function customerNarrativeText(value: unknown, locale: CustomerLocale): string {
  if (typeof value !== "string" || !value.trim()) return locale === "ar" ? "لا يتوفر شرح بعد." : "No explanation is available yet.";
  const clean = value.trim();
  const mapped = customerBusinessTerms[normalizeStatus(clean)]?.[locale] ?? customerStatuses[normalizeStatus(clean)]?.[locale];
  if (mapped) return mapped;
  const hasArabic = /[\u0600-\u06ff]/.test(clean);
  const looksTechnical = forbiddenCustomerToken.test(clean) || /(?:\b(?:snapshot|decision pack|monte carlo|finance engine|contract|algorithm|runtime)\b|[_]{1,})/i.test(clean);
  if (!looksTechnical && ((locale === "ar" && hasArabic) || (locale === "en" && !hasArabic))) return clean;
  return locale === "ar" ? "هذا التفصيل يحتاج صياغة واضحة قبل عرضه." : "This detail needs a clear customer-facing explanation.";
}

const recoveryFieldLabels: Record<string, [string, string]> = {
  name: ["اسم المشروع", "Project name"], sector: ["القطاع", "Sector"], jurisdiction: ["الدولة والنطاق النظامي", "Country and jurisdiction"],
  primary_sector_id: ["تصنيف القطاع", "Sector classification"], startup_cost: ["تكلفة التأسيس", "Setup cost"],
  unit_price: ["سعر الوحدة", "Unit price"], variable_cost: ["تكلفة الوحدة", "Unit cost"], monthly_units: ["الوحدات الشهرية", "Monthly units"],
  payroll_monthly: ["الرواتب الشهرية", "Monthly payroll"], rent_monthly: ["الإيجار الشهري", "Monthly rent"], utilities_monthly: ["المرافق الشهرية", "Monthly utilities"],
  marketing_monthly: ["التسويق الشهري", "Monthly marketing"], maintenance_monthly: ["الصيانة الشهرية", "Monthly maintenance"], other_monthly_costs: ["المصاريف الشهرية الأخرى", "Other monthly expenses"],
  capacity_units_per_day: ["الطاقة اليومية", "Daily capacity"], operating_days_per_month: ["أيام العمل شهريًا", "Operating days per month"], utilization_rate: ["نسبة الاستخدام من صفر إلى واحد", "Utilization from zero to one"],
  annual_discount_rate: ["معدل الخصم السنوي", "Annual discount rate"], working_capital_months: ["أشهر رأس المال العامل", "Working capital months"],
  debt_amount: ["مبلغ القرض", "Loan amount"], annual_interest_rate: ["معدل التمويل السنوي", "Annual interest rate"], loan_years: ["مدة القرض", "Loan term"],
  nca_check: ["فحص المتطلبات الأمنية", "Security requirements review"], lawful_purpose: ["الغرض المسموح", "Permitted purpose"], reviewer: ["المراجع", "Reviewer"], reviewer_decision: ["قرار المراجع", "Reviewer decision"], state: ["حالة المصدر", "Source state"],
  label: ["الوصف", "Description"], row_count: ["عدد صفوف البيانات", "Dataset row count"],
  route: ["طريقة الحصول على المصدر", "Source acquisition route"], url: ["رابط المصدر", "Source URL"], terms_url: ["رابط شروط الاستخدام", "Terms URL"],
  source_id: ["المصدر", "Source"], title: ["عنوان البيانات", "Dataset title"], publisher: ["الناشر", "Publisher"],
  license_snapshot_ref: ["مرجع إثبات الترخيص", "License evidence reference"], terms_hash: ["بصمة الشروط الموثقة", "Verified terms fingerprint"],
  classification: ["تصنيف البيانات", "Data classification"], pdpl_check: ["نتيجة فحص حماية البيانات", "Data protection review"], attribution: ["نسبة البيانات إلى مصدرها", "Attribution"],
  human_review_decision: ["قرار المراجعة البشرية", "Human review decision"], review_status: ["حالة المراجعة", "Review status"],
  operation_type: ["طريقة التحويل", "Transformation method"], input_columns: ["الأعمدة المستخدمة", "Input columns"], output_value: ["القيمة الناتجة الموثقة", "Documented output value"],
  monthly_fixed_cost: ["التكاليف الشهرية الثابتة", "Fixed monthly costs"], reason: ["السبب", "Reason"], value: ["القيمة", "Value"],
};
export function recoveryFieldText(key: string, locale: CustomerLocale): string {
  return recoveryFieldLabels[key]?.[locale === "ar" ? 0 : 1] ?? (locale === "ar" ? "متطلب يحتاج تحديدًا من المسؤول" : "Requirement needs owner mapping");
}
export function isRecoveryField(key: string): boolean { return Object.hasOwn(recoveryFieldLabels, key); }
const recoveryReasons: Record<string, [string, string]> = {
  INVALID_UNIT_ECONOMICS: ["يجب أن يكون سعر الوحدة أعلى من تكلفتها.", "Unit price must exceed unit cost."],
  INVALID_UTILIZATION_RATE: ["نسبة الاستخدام يجب أن تكون أكبر من صفر ولا تتجاوز واحدًا.", "Utilization must be above zero and at most one."],
  ASSUMPTION_COUNT_REQUIRED: ["عدد الافتراضات الحالية أقل من الحد المطلوب. أضف مدخلًا حقيقيًا موضحًا بقيمته ومصدره.", "The current assumption count is below the required minimum. Add a real input with its value and source."],
  ASSUMPTION_REVIEW_REQUIRED: ["هذا الافتراض يحتاج مراجعة بشرية محددة.", "This specific assumption needs human review."],
  EVIDENCE_BINDING_REQUIRED: ["هذا المتطلب لا يرتبط حاليًا بدليل صالح. اختر بيانات وتحويلًا لهذا المتطلب بعينه.", "This requirement has no usable evidence binding. Select evidence for this exact target."],
  DATASET_METADATA_REQUIRED: ["بيانات المراجعة المطلوبة غير مكتملة. أدخل الدليل الحقيقي؛ لا تُنشأ إقرارات تلقائية.", "Required review metadata is missing. Supply actual evidence; declarations are not generated automatically."],
  DATASET_REVIEW_REQUIRED: ["هذه البيانات تحتاج قرار مراجعة بشرية قبل استخدامها.", "This dataset needs a human review decision before use."],
  SOURCE_REVIEW_REQUIRED: ["المصدر غير معتمد للاستخدام. يلزم المسؤول المخول لمراجعته.", "The source is not approved for use. An authorized administrator must review it."],
  REFERENCE_ONLY_SOURCE_REPLACEMENT: ["المصدر مرجعي فقط ولا يجوز تحويله إلى دليل تشغيلي. اختر مصدرًا مناسبًا.", "This source is reference-only. Select a suitable evidence source instead."],
  DATASET_SOURCE_REQUIRED: ["مصدر هذه البيانات غير موجود. حدد المصدر الصحيح.", "The dataset source no longer exists. Select the correct source."],
  SECTOR_REVIEW_REQUIRED: ["اختر تصنيفًا موجودًا في سجل القطاعات أو اطلب مراجعة التصنيف.", "Choose a registered sector classification or request classification review."],
  EMPTY_DATASET: ["البيانات فارغة؛ استبدل المحتوى ببيانات فعلية.", "The dataset is empty; replace it with actual data."],
  MISSING_VALUES_ABOVE_80_PERCENT: ["القيم المفقودة كثيرة؛ صحح المحتوى ثم أعد فحصه.", "Too many values are missing; correct the content and recheck it."],
  DUPLICATE_ROWS_ABOVE_50_PERCENT: ["الصفوف المكررة كثيرة؛ صحح المحتوى ثم أعد فحصه.", "Too many rows are duplicated; correct the content and recheck it."],
  TRANSFORMATION_NOT_APPROVED: ["هذا التحويل يحتاج مراجعة.", "This transformation needs review."],
  TRANSFORMATION_REJECTED_BY_REVIEWER: ["رُفض هذا التحويل؛ صححه وأعد مراجعته.", "This transformation was rejected; correct it and review it again."],
  INVALID_OPERATION_TYPE: ["اختر طريقة تحويل مدعومة.", "Choose a supported transformation method."],
  MISSING_INPUT_COLUMNS: ["حدد أعمدة البيانات المستخدمة في التحويل.", "Select the dataset columns used by the transformation."],
  INPUT_COLUMN_NOT_FOUND: ["أحد الأعمدة المحددة غير موجود في البيانات الحالية.", "A selected column is absent from the current dataset."],
  MISSING_DERIVED_OUTPUT_VALUE: ["النتيجة المشتقة مفقودة؛ صحح التحويل أو أرفق قيمة موثقة.", "The derived output is missing; correct the transformation or supply a documented value."],
  INVALID_WORKING_CAPITAL_MONTHS: ["أدخل عددًا صالحًا لأشهر رأس المال العامل.", "Enter a valid working-capital month count."],
  INVALID_DEBT_AMOUNT: ["أدخل مبلغ تمويل رقميًا صالحًا.", "Enter a valid numeric loan amount."],
  MISSING_DEBT_TERMS: ["التمويل يتطلب معدلًا ومدة موجبين.", "Debt financing requires a positive interest rate and term."],
};
export function recoveryReasonText(code: string, locale: CustomerLocale): string {
  const entry = recoveryReasons[code];
  if (entry) return entry[locale === "ar" ? 0 : 1];
  if (["MISSING_STARTUP_COST", "MISSING_MONTHLY_FIXED_COST", "MISSING_UNIT_PRICE", "MISSING_VARIABLE_COST", "MISSING_MONTHLY_UNITS", "MISSING_CAPACITY_UNITS_PER_DAY", "MISSING_OPERATING_DAYS_PER_MONTH", "MISSING_UTILIZATION_RATE", "MISSING_DISCOUNT_RATE"].includes(code))
    return locale === "ar" ? "القيمة المطلوبة مفقودة أو غير موجبة. صحح الحقول المحددة ثم احفظ وأعد الفحص." : "A required value is missing or nonpositive. Correct the listed fields, save, and recheck.";
  if (["MISSING_PROJECT_NAME", "MISSING_PROJECT_SECTOR", "MISSING_PROJECT_JURISDICTION"].includes(code))
    return locale === "ar" ? "هذا البيان مطلوب لتعريف المشروع الحالي." : "This information is required to identify the current project.";
  return locale === "ar" ? "تعذر تحديد إجراء آمن لهذا المتطلب. يبقى مفتوحًا حتى يراجعه المسؤول." : "No safe action is mapped for this requirement. It remains open for owner review.";
}

const volatileRecoveryStorage = new Map<string, string | null>();
export function readRecoveryStorage(key: string): string | null {
  try { return volatileRecoveryStorage.has(key) ? (volatileRecoveryStorage.get(key) ?? null) : window.sessionStorage.getItem(key); }
  catch { return volatileRecoveryStorage.get(key) ?? null; }
}
export function writeRecoveryStorage(key: string, value: string): boolean {
  volatileRecoveryStorage.set(key, value);
  try { window.sessionStorage.setItem(key, value); return true; } catch { return false; }
}
export function removeRecoveryStorage(key: string): void {
  volatileRecoveryStorage.set(key, null);
  try { window.sessionStorage.removeItem(key); } catch { /* Memory navigation remains available. */ }
}
