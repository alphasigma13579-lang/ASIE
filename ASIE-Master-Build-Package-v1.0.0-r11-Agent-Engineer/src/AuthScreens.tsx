import { FormEvent, useState, type ReactElement } from "react";
import { KeyRound, LogIn, MailQuestion, ShieldCheck, UserPlus } from "lucide-react";
import {
  completePasswordRecovery,
  registerWithPassword,
  login,
  requestPasswordRecovery,
  type LoginResponse,
} from "./api";
import { BrandMark } from "./BrandMark";
import {
  CustomerLanguageSwitcher,
  customerErrorText,
  useCustomerLanguage,
} from "./customerLanguage";

export type AuthMode = "login" | "register" | "recover-request" | "recover-complete";

interface AuthScreenProps {
  initialMode?: AuthMode;
  onAuthenticated: (response: LoginResponse) => void;
}

export function AuthScreen({ initialMode = "login", onAuthenticated }: AuthScreenProps) {
  const { locale, direction, text } = useCustomerLanguage();
  const [mode, setMode] = useState<AuthMode>(initialMode);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [inviteToken, setInviteToken] = useState("");
  const [recoveryToken, setRecoveryToken] = useState("");
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
      } else if (mode === "register") {
        onAuthenticated(
          await registerWithPassword({
            email,
            password,
            display_name: displayName,
            invite_token: inviteToken,
          })
        );
      } else if (mode === "recover-request") {
        const result = await requestPasswordRecovery(email);
        if (result.recovery_token) {
          setRecoveryToken(result.recovery_token);
          switchMode("recover-complete");
          setNotice(text(
            "أُنشئ رمز استعادة محلي صالح لمدة 15 دقيقة. لا يوجد إرسال بريدي في هذه النسخة.",
            "A local recovery code valid for 15 minutes was created. Email delivery is not enabled in this release."
          ));
        } else {
          setNotice(text(
            "إذا كان البريد مسجلًا فستظهر تعليمات الاستعادة عند تفعيل الإرسال.",
            "If the email is registered, recovery instructions will be available when delivery is enabled."
          ));
        }
      } else {
        await completePasswordRecovery(recoveryToken, newPassword);
        switchMode("login");
        setNotice(text(
          "اكتملت الاستعادة. سجّل الدخول بكلمة المرور الجديدة.",
          "Recovery is complete. Sign in with your new password."
        ));
      }
    } catch (reason) {
      setError(customerErrorText(reason, locale));
    } finally {
      setBusy(false);
    }
  }

  const titles: Record<AuthMode, { icon: ReactElement; title: string; body: string }> = {
    login: {
      icon: <LogIn size={20} aria-hidden="true" />,
      title: text("تسجيل الدخول إلى مساحة العمل", "Sign in to your workspace"),
      body: text("ادخل إلى مشاريعك المحفوظة بأمان.", "Access your saved projects securely."),
    },
    register: {
      icon: <UserPlus size={20} aria-hidden="true" />,
      title: text("إنشاء حساب بيتا", "Create a beta account"),
      body: text(
        "التسجيل متاح للمدعوين فقط، وينشئ مساحة مستقلة لحسابك.",
        "Registration is invitation-only and creates an isolated workspace for your account."
      ),
    },
    "recover-request": {
      icon: <MailQuestion size={20} aria-hidden="true" />,
      title: text("استعادة كلمة المرور", "Recover your password"),
      body: text("أدخل بريدك لبدء الاستعادة.", "Enter your email to begin recovery."),
    },
    "recover-complete": {
      icon: <KeyRound size={20} aria-hidden="true" />,
      title: text("تعيين كلمة مرور جديدة", "Set a new password"),
      body: text("أدخل رمز الاستعادة واختر كلمة مرور جديدة.", "Enter the recovery code and choose a new password."),
    },
  };
  const current = titles[mode];

  return (
    <main id="main-content" className="admin-shell" dir={direction}>
      <section className="admin-login">
        <div className="auth-screen__language"><CustomerLanguageSwitcher /></div>
        <div className="admin-mark">
          <BrandMark size="sm" />
          <span>{text("ASIE / مساحة العميل", "ASIE / Customer workspace")}</span>
        </div>
        <h1>{current.title}</h1>
        <p>{current.body}</p>
        <form onSubmit={submit}>
          {mode === "register" ? (
            <>
              <label>
                {text("الاسم المعروض", "Display name")}
                <input required maxLength={80} value={displayName} onChange={(event) => setDisplayName(event.target.value)} />
              </label>
              <label>
                {text("رمز الدعوة", "Invitation code")}
                <input type="password" required autoComplete="one-time-code" spellCheck={false} autoCorrect="off" value={inviteToken} onChange={(event) => setInviteToken(event.target.value)} />
              </label>
            </>
          ) : null}
          {mode !== "recover-complete" ? (
            <label>
              {text("البريد الإلكتروني", "Email")}
              <input type="email" required value={email} onChange={(event) => setEmail(event.target.value)} />
            </label>
          ) : null}
          {mode === "login" || mode === "register" ? (
            <label>
              {text("كلمة المرور", "Password")}
              <input type="password" required minLength={6} maxLength={12} value={password} onChange={(event) => setPassword(event.target.value)} />
            </label>
          ) : null}
          {mode === "recover-complete" ? (
            <>
              <label>
                {text("رمز الاستعادة", "Recovery code")}
                <input required value={recoveryToken} onChange={(event) => setRecoveryToken(event.target.value)} />
              </label>
              <label>
                {text("كلمة المرور الجديدة", "New password")}
                <input type="password" required minLength={6} maxLength={12} value={newPassword} onChange={(event) => setNewPassword(event.target.value)} />
              </label>
            </>
          ) : null}
          {error ? <p className="admin-error" role="alert">{error}</p> : null}
          {notice ? <p className="muted">{notice}</p> : null}
          <button className="primary-button" disabled={busy}>
            {busy
              ? text("جارٍ المعالجة", "Processing")
              : mode === "login"
                ? text("دخول", "Sign in")
                : mode === "register"
                  ? text("إنشاء الحساب", "Create account")
                  : mode === "recover-request"
                    ? text("إصدار رمز الاستعادة", "Create recovery code")
                    : text("تعيين كلمة المرور", "Set password")}
          </button>
        </form>
        <div className="auth-links">
          {mode !== "login" ? <button type="button" className="landing-text-link" onClick={() => switchMode("login")}>{text("تسجيل الدخول", "Sign in")}</button> : null}
          {mode !== "register" ? <button type="button" className="landing-text-link" onClick={() => switchMode("register")}>{text("إنشاء حساب بيتا", "Create beta account")}</button> : null}
          {mode !== "recover-request" ? <button type="button" className="landing-text-link" onClick={() => switchMode("recover-request")}>{text("نسيت كلمة المرور", "Forgot password")}</button> : null}
        </div>
        {mode === "register" ? (
          <p className="muted" role="status">
            {text(
              "في البيتا المغلقة، التسجيل بالدعوة فقط. تسجيل Google مؤجل إلى نسخة لاحقة.",
              "Closed beta registration requires an invitation. Google sign-in is planned for a later release."
            )}
          </p>
        ) : null}
        <p className="muted auth-security-note">
          <ShieldCheck size={14} aria-hidden="true" />
          {text(
            "تُحفظ كلمات المرور والجلسات بصيغة آمنة، ولا تُخزّن الأسرار كنص صريح.",
            "Passwords and sessions are stored securely; secrets are never stored as plain text."
          )}
        </p>
      </section>
    </main>
  );
}
