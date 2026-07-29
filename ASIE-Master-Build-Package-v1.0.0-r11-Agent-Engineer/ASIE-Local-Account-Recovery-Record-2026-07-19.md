# ASIE — استعادة الحساب المحلية

## القرار الأمني الحالي

استعادة الحساب ذاتياً عبر قناة HTTP العامة معطلة ما دامت ASIE لا تملك قناة
تسليم خارجية معتمدة. لا يعيد الخادم رمز استعادة، ولا يسمح باستهلاك رموز
استعادة عبر HTTP.

## المسار الإداري المسموح

`POST /api/admin/users/{user_id}/local-password-reset`

- يتطلب `platform.manage` خادمياً.
- يقبل `new_password` وفق سياسة PBKDF2 الحالية.
- يستبدل password hash فقط؛ لا يحفظ كلمة المرور.
- يبطل كل جلسات المستخدم المستهدف فوراً.
- يكتب `identity.local_password_reset` في `security_audit_events`.
- لا يصدر token ولا يفتح قناة خارجية.

## المسارات العامة المقيدة

- `POST /api/auth/password-recovery/request` يعيد إقراراً عاماً متطابقاً
  للبريد الموجود وغير الموجود، ولا يعيد `recovery_token`.
- `POST /api/auth/password-recovery/complete` يفشل مغلقاً برمز
  `password_recovery_external_delivery_unavailable`.
- أي تفعيل مستقبلي للاستعادة الذاتية يتطلب قناة out-of-band معتمدة وحزمة
  أمنية واختبارات قبول سلبية منفصلة.

## دليل الإصدار

`sec_beta_10_password_recovery_lockdown` دليل تنفيذي حرج داخل
`REL-BETA-07`. غيابه أو فشله يبقي قرار الإصدار `NO_GO`.

## الحدود المحمية

لا يغير هذا القرار AAS Runtime Freeze أو Finance أو Snapshot Assembly أو
Decision Council، ولا يفعّل البريد أو SMS أو AI providers أو الشبكة الخارجية.
