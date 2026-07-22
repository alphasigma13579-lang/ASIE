# Identity, Notification, and Admin Operations Algorithms

## خوارزميات الهوية والتنبيهات وعمليات الإدارة

## ID-ALG-01 Human Verification Risk Gate

## بوابة مخاطر التحقق من الإنسان

Owner:

المالك:

`User / Auth Module` / موديول المستخدمين والمصادقة.

Purpose:

الهدف:

Decide when signup, login, password reset, or sensitive action requires human verification.

تحديد متى يحتاج التسجيل أو الدخول أو إعادة كلمة المرور أو الإجراء الحساس إلى تحقق الإنسان.

Signals:

الإشارات:

- Failed login count / عدد محاولات الدخول الفاشلة.
- IP/device reputation / سمعة IP أو الجهاز.
- Signup velocity / سرعة التسجيل.
- Suspicious user agent / User Agent مشبوه.
- Admin action risk / خطورة الإجراء الإداري.

Output:

المخرج:

- `challenge_required` / التحدي مطلوب.
- `challenge_not_required` / التحدي غير مطلوب.
- `block` / منع.

Forbidden:

الممنوع:

- AI decides human verification.
- AI يقرر تحقق الإنسان.

## ID-ALG-02 Authenticator App MFA Evaluation

## تقييم MFA عبر تطبيق Authenticator

Owner:

المالك:

`User / Auth Module` / موديول المستخدمين والمصادقة.

Purpose:

الهدف:

Enroll and verify TOTP-based MFA.

تفعيل والتحقق من MFA المعتمد على TOTP.

Rules:

القواعد:

- Admin and maintenance roles require MFA.
- أدوار الإدارة والصيانة تتطلب MFA.

- TOTP secrets must be encrypted.
- أسرار TOTP يجب أن تكون مشفرة.

- Recovery codes are hashed.
- رموز الاسترداد تخزن كـ Hash.

- MFA secrets never go to AI or external notifications.
- أسرار MFA لا ترسل إلى AI أو التنبيهات الخارجية.

## NOTIF-ALG-01 Notification Preference Resolution

## حل تفضيلات التنبيهات

Owner:

المالك:

`Notification Service` under `Audit / Observability Module` / خدمة التنبيهات تحت موديول التدقيق والمراقبة.

Purpose:

الهدف:

Decide whether a notification should be sent and through which channel.

تحديد هل يرسل التنبيه وبأي قناة.

Inputs:

المدخلات:

- User preferences / تفضيلات المستخدم.
- Notification type / نوع التنبيه.
- Severity / الشدة.
- Quiet hours / ساعات الهدوء.
- Opt-in status / حالة الموافقة.
- Language / اللغة.

Steps:

الخطوات:

1. Load user preferences.
2. Check notification type.
3. Check channel opt-in.
4. Apply quiet hours unless critical.
5. Resolve language.
6. Create in-app notification.
7. Send external notification only if allowed.

## NOTIF-ALG-02 External Channel Delivery Guard

## حارس تسليم القنوات الخارجية

Purpose:

الهدف:

Prevent unsafe Telegram or WhatsApp delivery.

منع تسليم غير آمن عبر تليجرام أو واتساب.

Reject if:

يرفض إذا:

- No user opt-in / لا توجد موافقة.
- Message contains MFA code or secret / الرسالة تحتوي رمز MFA أو سر.
- Message contains sensitive finance details without explicit permission / تحتوي تفاصيل مالية حساسة بلا إذن صريح.
- Channel token invalid / رمز القناة غير صالح.

## ADM-ALG-02 Admin Operations Health Evaluation

## تقييم صحة عمليات الإدارة

Owner:

المالك:

`Admin Module` / موديول الإدارة with `Audit / Observability Module` / موديول التدقيق والمراقبة.

Purpose:

الهدف:

Provide advanced operational status for admins, maintenance, and support teams.

تقديم حالة تشغيلية متقدمة للآدمن وفرق الصيانة والدعم.

Signals:

الإشارات:

- System health / صحة النظام.
- Source adapter health / صحة موصلات المصادر.
- AI provider health / صحة مزودي AI.
- Job queues / طوابير المهام.
- Incident status / حالة الحوادث.
- Notification delivery failures / فشل تسليم التنبيهات.
- Quarantine queue / طابور العزل.

Output:

المخرج:

`admin.operations.health.snapshot.v1`.

## ADM-ALG-03 Incident Escalation

## تصعيد الحوادث

Purpose:

الهدف:

Escalate incidents to correct admin or maintenance team.

تصعيد الحوادث إلى فريق الإدارة أو الصيانة الصحيح.

Rules:

القواعد:

- Critical incidents bypass quiet hours for on-call admins.
- الحوادث الحرجة تتجاوز ساعات الهدوء لمناوبي الإدارة.

- Every escalation is audited.
- كل تصعيد يدقق.

- External escalation requires configured channel and role permission.
- التصعيد الخارجي يحتاج قناة مضبوطة وصلاحية دور.

