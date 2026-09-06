import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

export type CustomerLocale = "ar" | "en";

const CUSTOMER_LOCALE_STORAGE_KEY = "asie.customer_locale.v1";
const DEFAULT_CUSTOMER_LOCALE: CustomerLocale = "ar";

type CustomerLanguageContextValue = {
  locale: CustomerLocale;
  direction: "rtl" | "ltr";
  setLocale: (locale: CustomerLocale) => void;
  text: (arabic: string, english: string) => string;
};

const CustomerLanguageContext = createContext<CustomerLanguageContextValue | null>(null);

function readStoredLocale(): CustomerLocale {
  try {
    const stored = window.localStorage.getItem(CUSTOMER_LOCALE_STORAGE_KEY);
    return stored === "en" ? "en" : DEFAULT_CUSTOMER_LOCALE;
  } catch {
    return DEFAULT_CUSTOMER_LOCALE;
  }
}

export function CustomerLanguageProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<CustomerLocale>(() => readStoredLocale());

  function setLocale(nextLocale: CustomerLocale) {
    setLocaleState(nextLocale);
    try {
      window.localStorage.setItem(CUSTOMER_LOCALE_STORAGE_KEY, nextLocale);
    } catch {
      // The selected language still applies to the current session.
    }
  }

  useEffect(() => {
    document.documentElement.lang = locale;
    document.documentElement.dir = locale === "ar" ? "rtl" : "ltr";
  }, [locale]);

  const value = useMemo<CustomerLanguageContextValue>(
    () => ({
      locale,
      direction: locale === "ar" ? "rtl" : "ltr",
      setLocale,
      text: (arabic, english) => (locale === "ar" ? arabic : english),
    }),
    [locale]
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
  return value.trim().toLowerCase().replace(/[-\s]+/g, "_");
}

export function customerStatusText(value: unknown, locale: CustomerLocale): string {
  if (typeof value !== "string" || !value.trim()) return locale === "ar" ? "غير محدد" : "Not specified";
  const status = customerStatuses[normalizeStatus(value)];
  return status?.[locale] ?? (locale === "ar" ? "حالة تحتاج مراجعة" : "Status requires review");
}

const customerErrors: Array<{ pattern: RegExp; ar: string; en: string }> = [
  { pattern: /invalid_credentials/i, ar: "بيانات الدخول غير صحيحة.", en: "The sign-in details are incorrect." },
  { pattern: /registration_invite_invalid/i, ar: "رمز الدعوة غير صالح أو لا يطابق هذا البريد.", en: "The invitation code is invalid or does not match this email." },
  { pattern: /password_length_must_be_between_6_and_12_characters/i, ar: "يجب أن تتكون كلمة المرور من 6 إلى 12 حرفًا.", en: "The password must contain 6 to 12 characters." },
  { pattern: /email_already_registered/i, ar: "هذا البريد مسجل بالفعل. استخدم تسجيل الدخول.", en: "This email is already registered. Please sign in." },
  { pattern: /invalid_or_expired_recovery_token/i, ar: "رمز الاستعادة غير صالح أو منتهي. اطلب رمزًا جديدًا.", en: "The recovery code is invalid or expired. Request a new code." },
  { pattern: /local_bootstrap_unavailable/i, ar: "إنشاء الحساب غير متاح الآن. حاول لاحقًا أو تواصل مع مشرف البيتا.", en: "Account creation is temporarily unavailable. Try again later or contact the beta administrator." },
  { pattern: /unauthorized|forbidden|permission/i, ar: "ليست لديك صلاحية لتنفيذ هذا الإجراء.", en: "You do not have permission to perform this action." },
  { pattern: /network|fetch|timeout|timed out/i, ar: "تعذر الاتصال بالخدمة. تحقق من الشبكة ثم أعد المحاولة.", en: "The service could not be reached. Check your connection and try again." },
];

export function customerErrorText(reason: unknown, locale: CustomerLocale): string {
  const raw = reason instanceof Error ? reason.message : typeof reason === "string" ? reason : "";
  const match = customerErrors.find((entry) => entry.pattern.test(raw));
  if (match) return match[locale];
  return locale === "ar"
    ? "تعذر إتمام الطلب. حاول مرة أخرى، وإذا استمرت المشكلة تواصل مع مشرف البيتا."
    : "The request could not be completed. Try again, and contact the beta administrator if the problem continues.";
}

const forbiddenCustomerToken = /(?:\b(?:project|run|snapshot|profile|contract|review|projection|release|algorithm|engine|session|manifest|validation_gate|payload|hash)_id\b|\b(?:not_ready|review_required|demo_or_user_input_only|blocked_not_ready|no_evidence_links)\b)/i;

export function containsForbiddenCustomerToken(value: string): boolean {
  return forbiddenCustomerToken.test(value);
}
