import { FormEvent, useState, type ReactElement } from "react";
import { KeyRound, LogIn, MailQuestion, Rocket, ShieldCheck } from "lucide-react";
import {
  completePasswordRecovery,
  localBootstrap,
  login,
  requestPasswordRecovery,
  type LoginResponse,
} from "./api";
import { BrandMark } from "./BrandMark";

export type AuthMode = "login" | "bootstrap" | "recover-request" | "recover-complete";

interface AuthScreenProps {
  initialMode?: AuthMode;
  onAuthenticated: (response: LoginResponse) => void;
}

/**
 * Sign-in surface for the client workspace. Three flows, all served by the
 * local API only: first-run bootstrap (zero users), returning-user login,
 * and the local password-recovery record (no external email delivery).
 */
export function AuthScreen({ initialMode = "login", onAuthenticated }: AuthScreenProps) {
  const [mode, setMode] = useState<AuthMode>(initialMode);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [organizationName, setOrganizationName] = useState("");
  const [recoveryToken, setRecoveryToken] = useState("");
  const [issuedToken, setIssuedToken] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);

  function switchMode(next: AuthMode) {
    setMode(next);
    setError("");
    setNotice("");
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setNotice("");
    try {
      if (mode === "login") {
        onAuthenticated(await login(email, password));
      } else if (mode === "bootstrap") {
        onAuthenticated(
          await localBootstrap({
            email,
            password,
            display_name: displayName,
            organization_name: organizationName,
          })
        );
      } else if (mode === "recover-request") {
        const result = await requestPasswordRecovery(email);
        if (result.recovery_token) {
          setIssuedToken(result.recovery_token);
          setRecoveryToken(result.recovery_token);
          setNotice("أُنشئ رمز استعادة محلي (صالح 15 دقيقة). لا يوجد إرسال بريدي خارجي في هذه النسخة.");
          switchMode("recover-complete");
          setNotice("أُنشئ رمز استعادة محلي (صالح 15 دقيقة). لا يوجد إرسال بريدي خارجي في هذه النسخة.");
        } else {
          setNotice("إن كان البريد مسجلاً فستصله تعليمات الاستعادة عند تفعيل الإرسال الخارجي.");
        }
      } else {
        await completePasswordRecovery(recoveryToken, newPassword);
        setNotice("اكتملت الاستعادة. سجّل الدخول بكلمة المرور الجديدة.");
        switchMode("login");
        setNotice("اكتملت الاستعادة. سجّل الدخول بكلمة المرور الجديدة.");
      }
    } catch (reason) {
      const message = reason instanceof Error ? reason.message : "تعذر إتمام الطلب";
      if (message.includes("invalid_credentials")) setError("بيانات الدخول غير صحيحة.");
      else if (message.includes("local_bootstrap_already_completed")) setError("اكتملت التهيئة الأولى سابقاً. سجّل الدخول بحسابك.");
      else if (message.includes("invalid_or_expired_recovery_token")) setError("رمز الاستعادة غير صالح أو منتهي. اطلب رمزاً جديداً.");
      else setError(message);
    } finally {
      setBusy(false);
    }
  }

  const titles: Record<AuthMode, { icon: ReactElement; title: string; body: string }> = {
    login: {
      icon: <LogIn size={20} aria-hidden="true" />,
      title: "تسجيل الدخول إلى مساحة العمل",
      body: "جلسات محلية موقّتة (8 ساعات) بتخزين هاش فقط على الخادم.",
    },
    bootstrap: {
      icon: <Rocket size={20} aria-hidden="true" />,
      title: "التهيئة الأولى للمنصة",
      body: "ينشئ حساب مدير المنصة ومنظمتك الأولى. يعمل مرة واحدة فقط.",
    },
    "recover-request": {
      icon: <MailQuestion size={20} aria-hidden="true" />,
      title: "استعادة كلمة المرور",
      body: "أدخل بريدك لإنشاء رمز استعادة محلي.",
    },
    "recover-complete": {
      icon: <KeyRound size={20} aria-hidden="true" />,
      title: "تعيين كلمة مرور جديدة",
      body: "ألصق رمز الاستعادة ثم اختر كلمة مرور جديدة.",
    },
  };
  const current = titles[mode];

  return (
    <main id="main-content" className="admin-shell">
      <section className="admin-login">
        <div className="admin-mark">
          <BrandMark size="sm" />
          <span>ASIE / مساحة العميل</span>
        </div>
        <h1>{current.title}</h1>
        <p>{current.body}</p>
        <form onSubmit={submit}>
          {mode === "bootstrap" ? (
            <>
              <label>
                الاسم المعروض
                <input required maxLength={80} value={displayName} onChange={(event) => setDisplayName(event.target.value)} />
              </label>
              <label>
                اسم المنظمة
                <input required maxLength={80} value={organizationName} onChange={(event) => setOrganizationName(event.target.value)} />
              </label>
            </>
          ) : null}
          {mode !== "recover-complete" ? (
            <label>
              البريد المحلي
              <input type="email" required value={email} onChange={(event) => setEmail(event.target.value)} />
            </label>
          ) : null}
          {mode === "login" || mode === "bootstrap" ? (
            <label>
              كلمة المرور
              <input type="password" required minLength={10} value={password} onChange={(event) => setPassword(event.target.value)} />
            </label>
          ) : null}
          {mode === "recover-complete" ? (
            <>
              <label>
                رمز الاستعادة
                <input required value={recoveryToken} onChange={(event) => setRecoveryToken(event.target.value)} />
              </label>
              <label>
                كلمة المرور الجديدة
                <input type="password" required minLength={10} value={newPassword} onChange={(event) => setNewPassword(event.target.value)} />
              </label>
            </>
          ) : null}
          {issuedToken && mode === "recover-complete" ? (
            <p className="muted" style={{ wordBreak: "break-all" }}>
              الرمز المحلي الصادر: <code>{issuedToken}</code>
            </p>
          ) : null}
          {error ? (
            <p className="admin-error" role="alert">
              {error}
            </p>
          ) : null}
          {notice ? <p className="muted">{notice}</p> : null}
          <button className="primary-button" disabled={busy}>
            {busy ? "جارٍ المعالجة" : mode === "login" ? "دخول" : mode === "bootstrap" ? "إنشاء الحساب والمنظمة" : mode === "recover-request" ? "إصدار رمز الاستعادة" : "تعيين كلمة المرور"}
          </button>
        </form>
        <div className="auth-links">
          {mode !== "login" ? (
            <button type="button" className="landing-text-link" onClick={() => switchMode("login")}>
              تسجيل الدخول
            </button>
          ) : null}
          {mode !== "bootstrap" ? (
            <button type="button" className="landing-text-link" onClick={() => switchMode("bootstrap")}>
              التهيئة الأولى
            </button>
          ) : null}
          {mode !== "recover-request" ? (
            <button type="button" className="landing-text-link" onClick={() => switchMode("recover-request")}>
              نسيت كلمة المرور
            </button>
          ) : null}
        </div>
        <p className="muted auth-security-note">
          <ShieldCheck size={14} aria-hidden="true" /> كلمات المرور بـ PBKDF2-SHA256 (310 ألف تكرار) والجلسات هاش فقط — لا تُخزّن الأسرار بصيغة صريحة.
        </p>
      </section>
    </main>
  );
}
