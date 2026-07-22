# ASIE — استعادة الحساب المحلية

## النطاق

استعادة محلية تحت إشراف `platform_admin` فقط. لا بريد، ولا SMS، ولا رابط استعادة، ولا token خارج الجهاز.

## المسار

`POST /api/admin/users/{user_id}/local-password-reset`

- يتطلب `platform.manage` خادمياً.
- يقبل `new_password` وفق سياسة PBKDF2 الحالية.
- يستبدل password hash فقط؛ لا يحفظ كلمة المرور.
- يبطل كل جلسات المستخدم المستهدف فوراً.
- يكتب `identity.local_password_reset` في `security_audit_events`.
- يعيد `external_delivery_enabled: false`.

## التحقق

- `python -m unittest tests.test_local_account_recovery tests.test_identity_control_plane`: **4 tests passed**.
- `python -m compileall -q backend`: **passed**.
- `pnpm build`: **passed**.

## القيد

هذا مسار تطوير محلي وإشرافي؛ لا يعد استعادة ذاتية أو فتح وصول خارجي.
