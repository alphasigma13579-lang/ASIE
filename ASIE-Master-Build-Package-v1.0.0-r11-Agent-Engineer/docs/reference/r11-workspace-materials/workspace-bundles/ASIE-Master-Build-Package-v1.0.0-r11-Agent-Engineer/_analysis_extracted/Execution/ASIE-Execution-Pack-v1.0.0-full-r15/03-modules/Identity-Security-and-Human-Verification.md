# Identity Security and Human Verification

## أمن الهوية والتحقق من أن المستخدم إنسان

## Purpose

## الهدف

Protect ASIE login, signup, and sensitive actions from bots, account abuse, and unauthorized access.

حماية الدخول والتسجيل والإجراءات الحساسة في ASIE من الروبوتات وإساءة الاستخدام والوصول غير المصرح.

## Required Capabilities

## القدرات المطلوبة

| Capability | Arabic | Required |
| --- | --- | --- |
| Human verification | التحقق أن المستخدم إنسان وليس روبوت | Required on signup and suspicious login |
| Risk-based bot challenge | تحدي روبوت حسب المخاطر | Required |
| Optional Authenticator App MFA | تحقق اختياري عبر تطبيق Authenticator | Required |
| TOTP support | دعم TOTP | Required |
| Backup recovery codes | رموز استرداد احتياطية | Required |
| Session risk evaluation | تقييم مخاطر الجلسة | Required |
| Admin-enforced MFA | إلزام MFA من الإدارة | Required for admin roles |

## Human Verification

## التحقق من الإنسان

ASIE must verify human presence during:

يجب على ASIE التحقق من الإنسان عند:

- Signup / التسجيل.
- Suspicious login / دخول مشبوه.
- Repeated failed login / محاولات دخول فاشلة متكررة.
- Password reset / إعادة تعيين كلمة المرور.
- High-risk admin action / إجراء إداري عالي الخطورة.

Implementation may use a provider such as Turnstile, reCAPTCHA, hCaptcha, or equivalent behind a contract.

يمكن التنفيذ عبر مزود مثل Turnstile أو reCAPTCHA أو hCaptcha أو بديل مكافئ خلف عقد.

Provider must not become architecture authority.

المزود لا يصبح مرجعًا معماريًا.

## Authenticator App MFA

## التحقق عبر تطبيق Authenticator

Authenticator app MFA is optional for normal users and required for admin and maintenance roles unless explicitly disabled by policy.

التحقق عبر تطبيق Authenticator اختياري للمستخدم العادي وإجباري لأدوار الإدارة والصيانة إلا إذا عطّلته سياسة صريحة.

Supported:

المدعوم:

- TOTP / رمز زمني.
- QR enrollment / تفعيل عبر QR.
- Recovery codes / رموز استرداد.
- Device trust policy / سياسة الثقة بالجهاز.

## Message Types

## أنواع الرسائل

- `auth.human.challenge.requested.v1` / طلب تحدي تحقق إنسان.
- `auth.human.challenge.verified.v1` / نجاح تحقق الإنسان.
- `auth.mfa.enrollment.started.v1` / بدء تفعيل MFA.
- `auth.mfa.enrollment.verified.v1` / نجاح تفعيل MFA.
- `auth.mfa.challenge.required.v1` / طلب تحدي MFA.
- `auth.mfa.challenge.verified.v1` / نجاح تحدي MFA.
- `auth.recovery.code.used.v1` / استخدام رمز استرداد.
- `auth.risk.event.v1` / حدث مخاطر هوية.

## Forbidden

## الممنوع

- Bypass human verification after repeated abuse.
- تجاوز تحقق الإنسان بعد إساءة متكررة.

- Store TOTP secrets unencrypted.
- تخزين أسرار TOTP بلا تشفير.

- Send MFA secret to AI.
- إرسال سر MFA إلى AI.

- Allow admin role without MFA unless emergency break-glass policy is audited.
- السماح بدور Admin بلا MFA إلا بسياسة طوارئ مدققة.

