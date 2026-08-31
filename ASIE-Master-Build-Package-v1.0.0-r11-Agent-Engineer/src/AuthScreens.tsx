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

export type AuthMode = "login" | "register" | "recover-request" | "recover-complete";

interface AuthScreenProps {
  initialMode?: AuthMode;
  onAuthenticated: (response: LoginResponse) => void;
}

/**
 * Sign-in surface for the client workspace. Three flows, all served by the
 * local API only: invitation-bound password registration, returning-user
 * login, and the local password-recovery record (no external email delivery).
 */
export function AuthScreen({ initialMode = "login", onAuthenticated }: AuthScreenProps) {
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
      else if (message.includes("registration_invite_invalid")) setError("رمز الدعوة غير صالح أو لا يطابق هذا البريد.");
      else if (message.includes("email_already_registered")) setError("هذا البريد مسجل بالفعل. استخدم تسجيل الدخول.");
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
    register: {
      icon: <UserPlus size={20} aria-hidden="true" />,
      title: "إنشاء حساب بيتا",
      body: "التسجيل متاح للمستخدمين المدعوين فقط. ينشئ حسابك ومنظمتك الخاصة.",
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
          {mode === "register" ? (
            <>
              <label>
                الاسم المعروض
                <input required maxLength={80} value={displayName} onChange={(event) => setDisplayName(event.target.value)} />
              </label>
              <label>
                رمز الدعوة
                <input required autoComplete="one-time-code" value={inviteToken} onChange={(event) => setInviteToken(event.target.value)} />
              </label>
            </>
          ) : null}
          {mode !== "recover-complete" ? (
            <label>
              البريد المحلي
              <input type="email" required value={email} onChange={(event) => setEmail(event.target.value)} />
            </label>
          ) : null}
          {mode === "login" || mode === "register" ? (
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
          {error ? (
            <p className="admin-error" role="alert">
              {error}
            </p>
          ) : null}
          {notice ? <p className="muted">{notice}</p> : null}
          <button className="primary-button" disabled={busy}>
            {busy ? "جارٍ المعالجة" : mode === "login" ? "دخول" : mode === "register" ? "إنشاء الحساب" : mode === "recover-request" ? "إصدار رمز الاستعادة" : "تعيين كلمة المرور"}
          </button>
        </form>
        <div className="auth-links">
          {mode !== "login" ? (
            <button type="button" className="landing-text-link" onClick={() => switchMode("login")}>
              تسجيل الدخول
            </button>
          ) : null}
          {mode !== "register" ? (
            <button type="button" className="landing-text-link" onClick={() => switchMode("register")}>
              إنشاء حساب بيتا
            </button>
          ) : null}
          {mode !== "recover-request" ? (
            <button type="button" className="landing-text-link" onClick={() => switchMode("recover-request")}>
              نسيت كلمة المرور
            </button>
          ) : null}
        </div>
        {mode === "register" ? (
          <p className="muted" role="status">
            في البيتا المغلقة، التسجيل العادي بالدعوة فقط. تسجيل Google مؤجل لنسخة لاحقة بعد اعتماده واختباره.
          </p>
        ) : null}
        <p className="muted auth-security-note">
          <ShieldCheck size={14} aria-hidden="true" /> كلمات المرور بـ PBKDF2-SHA256 (310 ألف تكرار) والجلسات هاش فقط — لا تُخزّن الأسرار بصيغة صريحة.
        </p>
      </section>
    </main>
  );
}
