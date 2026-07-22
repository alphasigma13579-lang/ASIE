import { Activity, Bell, Building2, CreditCard, LogIn, ShieldCheck, Users } from "lucide-react";
import { FormEvent, useState } from "react";
import { BrandMark } from "./BrandMark";

type Organization = { organization_id: string; name: string; subscription_status: string; plan_code: string; member_count: number; project_count: number };
type Overview = { organizations: Organization[]; users: Array<{ user_id: string; display_name: string; email: string; platform_role: string | null }>; invoices: Array<{ invoice_id: string; status: string; amount_minor: number; currency: string }>; health: { database: { state: string }; run_failures: unknown[]; backup: { state: string } }; external_payments_enabled: boolean; external_notifications_enabled: boolean };

async function adminRequest<T>(path: string, token: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, { ...init, headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}`, ...(init?.headers ?? {}) } });
  const payload = await response.json() as T & { error?: string };
  if (!response.ok) throw new Error(payload.error ?? "تعذر إتمام طلب المشغل");
  return payload;
}

export function AdminConsole() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [token, setToken] = useState("");
  const [overview, setOverview] = useState<Overview | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function signIn(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError("");
    try {
      const login = await adminRequest<{ access_token: string }>("/api/auth/login", "", { method: "POST", body: JSON.stringify({ email, password }) });
      const nextOverview = await adminRequest<Overview>("/api/admin/overview", login.access_token);
      setToken(login.access_token); setOverview(nextOverview);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "تعذر تسجيل الدخول"); }
    finally { setBusy(false); }
  }

  async function refresh() {
    if (!token) return;
    setBusy(true); setError("");
    try { setOverview(await adminRequest<Overview>("/api/admin/overview", token)); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "تعذر التحديث"); }
    finally { setBusy(false); }
  }

  if (!overview) return <main id="main-content" className="admin-shell"><section className="admin-login"><div className="admin-mark"><BrandMark size="sm" /><span>ASIE / المشغّل</span></div><h1>لوحة التحكم المحلية</h1><p>مساحة منفصلة لمشغل المنصة. لا توجد بوابة دفع أو مراسلات خارجية.</p><form onSubmit={signIn}><label>البريد المحلي<input type="email" required value={email} onChange={(event) => setEmail(event.target.value)} /></label><label>كلمة المرور<input type="password" required value={password} onChange={(event) => setPassword(event.target.value)} /></label>{error ? <p className="admin-error" role="alert">{error}</p> : null}<button className="primary-button" disabled={busy}><LogIn size={18} />{busy ? "جارٍ التحقق" : "دخول المشغّل"}</button></form><a href="/">العودة لمساحة العميل</a></section></main>;

  return <main id="main-content" className="admin-shell"><header className="admin-topbar"><div><p className="eyebrow">سطح مشغّل منفصل · قراءة من سجلات التحكم</p><h1>نظرة عامة للمنصة</h1></div><button className="primary-button" onClick={() => void refresh()} disabled={busy}>تحديث السجلات</button></header>{error ? <p className="admin-error" role="alert">{error}</p> : null}<section className="admin-metrics"><article><Building2 /><span>المنظمات</span><strong>{overview.organizations.length}</strong></article><article><Users /><span>المستخدمون</span><strong>{overview.users.length}</strong></article><article><CreditCard /><span>دفتر الفواتير المحلي</span><strong>{overview.invoices.length}</strong></article><article><Activity /><span>حالة قاعدة البيانات</span><strong>{overview.health.database.state === "healthy" ? "سليمة" : "تحتاج مراجعة"}</strong></article></section><section className="admin-grid"><article className="admin-panel"><div className="section-title"><Building2 /><h2>المنظمات والاشتراكات</h2></div>{overview.organizations.length ? <div className="admin-table">{overview.organizations.map((organization) => <div key={organization.organization_id}><strong>{organization.name}</strong><span>{organization.plan_code} · {organization.subscription_status}</span><small>{organization.member_count} أعضاء · {organization.project_count} مشاريع</small></div>)}</div> : <p className="muted">لا توجد منظمات بعد.</p>}</article><article className="admin-panel"><div className="section-title"><Bell /><h2>تشغيل محلي فقط</h2></div><p>الدفع الخارجي: {overview.external_payments_enabled ? "مفعل" : "معطل"}</p><p>الإرسال الخارجي: {overview.external_notifications_enabled ? "مفعل" : "معطل"}</p><p>النسخ الاحتياطية: {overview.health.backup.state}</p><p>عمليات تشغيل تحتاج مراجعة: {overview.health.run_failures.length}</p></article></section><section className="admin-panel"><div className="section-title"><Users /><h2>المستخدمون والأدوار</h2></div><div className="admin-table">{overview.users.map((user) => <div key={user.user_id}><strong>{user.display_name}</strong><span>{user.email}</span><small>{user.platform_role ?? "دور منظمة فقط"}</small></div>)}</div></section></main>;
}
