# Notification and Admin Operations Center

## مركز التنبيهات وعمليات الإدارة

## Purpose

## الهدف

Provide user notifications, external alert channels, notification preferences, and advanced admin operations for monitoring and maintenance teams.

توفير إشعارات المستخدم، قنوات التنبيه الخارجية، تفضيلات التنبيهات، ولوحة إدارة متقدمة لفرق المتابعة والصيانة.

## User Notification Channels

## قنوات إشعارات المستخدم

| Channel | Arabic | Use |
| --- | --- | --- |
| In-app notifications | إشعارات داخل المنصة | Default notification center |
| Email | البريد الإلكتروني | Account and report notifications |
| WhatsApp | واتساب | Optional urgent/user-approved alerts |
| Telegram | تليجرام | Optional bot/channel alerts |

## Notification Preference Center

## مركز تخصيص التنبيهات

Users must be able to choose:

يجب أن يستطيع المستخدم اختيار:

- Which notifications they receive / ما التنبيهات التي يستقبلها.
- Channels per notification type / القنوات لكل نوع تنبيه.
- Quiet hours / ساعات الهدوء.
- Language / اللغة.
- Frequency / التكرار.
- Critical-only mode / وضع التنبيهات الحرجة فقط.

## Notification Types

## أنواع التنبيهات

| Type | Arabic | Default |
| --- | --- | --- |
| Analysis completed | اكتمال التحليل | In-app + email |
| Evidence missing | نقص الأدلة | In-app |
| Report ready | التقرير جاهز | In-app + email |
| Subscription limit warning | تحذير حد الاشتراك | In-app |
| Payment/billing event | حدث دفع أو فوترة | Email |
| Security login alert | تنبيه دخول أمني | In-app + email |
| Admin message | رسالة من الإدارة | In-app |
| Critical system issue | مشكلة نظام حرجة | In-app + configured external channel |

## External Notification Connectors

## موصلات التنبيهات الخارجية

- `WhatsApp Notification Adapter` / موصل تنبيهات واتساب.
- `Telegram Notification Adapter` / موصل تنبيهات تليجرام.

Rules:

القواعد:

- User must opt in before WhatsApp or Telegram alerts.
- يجب موافقة المستخدم قبل تنبيهات واتساب أو تليجرام.

- Store channel tokens securely.
- تخزن رموز القنوات بأمان.

- Do not send sensitive finance details through external messaging unless user explicitly enables it.
- لا ترسل تفاصيل مالية حساسة عبر رسائل خارجية إلا إذا فعلها المستخدم صراحة.

## In-App Notification Center

## مركز الإشعارات داخل المنصة

Required:

المطلوب:

- Read/unread state / حالة مقروء وغير مقروء.
- Severity / الشدة.
- Category / الفئة.
- Source module / الموديول المصدر.
- Action link / رابط إجراء.
- Archive / أرشفة.
- Search and filter / بحث وفلترة.

## Advanced Admin Operations Center

## مركز عمليات الإدارة المتقدم

Admin and maintenance teams must have:

يجب أن يملك الآدمن وفرق المتابعة والصيانة:

- Real-time system health / صحة النظام لحظيًا.
- Incident dashboard / لوحة الحوادث.
- Quarantine queue / طابور العزل.
- Source adapter health / صحة موصلات المصادر.
- AI provider health / صحة مزودي AI.
- Job queue monitoring / مراقبة طوابير المهام.
- User activity monitoring / مراقبة نشاط المستخدمين.
- Subscription and usage monitoring / مراقبة الاشتراكات والاستخدام.
- Notification delivery monitoring / مراقبة تسليم التنبيهات.
- Maintenance mode controls / تحكم وضع الصيانة.
- Feature flag controls / تحكم Feature Flags.
- Audit investigation tools / أدوات تحقيق التدقيق.
- On-call escalation / تصعيد مناوبة.
- Role-based admin workspaces / مساحات إدارة حسب الدور.

## Admin Roles

## أدوار الإدارة

| Role | Arabic | Capabilities |
| --- | --- | --- |
| Super Admin | مدير أعلى | Full control with MFA |
| Operations Admin | مدير العمليات | Health, incidents, queues |
| Security Admin | مدير الأمن | audit, quarantine, access |
| Support Agent | موظف الدعم | user support, tickets |
| Maintenance Engineer | مهندس الصيانة | jobs, adapters, incidents |
| Finance/Billing Admin | مدير الفوترة | subscriptions, payments |

## Required Message Types

## أنواع الرسائل المطلوبة

- `notification.preference.updated.v1` / تحديث تفضيلات التنبيه.
- `notification.delivery.requested.v1` / طلب إرسال تنبيه.
- `notification.delivery.sent.v1` / إرسال تنبيه.
- `notification.delivery.failed.v1` / فشل إرسال تنبيه.
- `notification.in_app.created.v1` / إنشاء إشعار داخلي.
- `admin.incident.created.v1` / إنشاء حادث.
- `admin.incident.escalated.v1` / تصعيد حادث.
- `admin.maintenance.mode.updated.v1` / تحديث وضع الصيانة.
- `admin.operations.health.snapshot.v1` / لقطة صحة العمليات.

## Forbidden

## الممنوع

- Sending external alerts without opt-in.
- إرسال تنبيهات خارجية بلا موافقة.

- Sending secrets or MFA codes over Telegram or WhatsApp.
- إرسال أسرار أو رموز MFA عبر تليجرام أو واتساب.

- Admin mutation without audit event.
- تعديل إداري بلا حدث تدقيق.

- Maintenance action without RBAC and MFA.
- إجراء صيانة بلا RBAC وMFA.

