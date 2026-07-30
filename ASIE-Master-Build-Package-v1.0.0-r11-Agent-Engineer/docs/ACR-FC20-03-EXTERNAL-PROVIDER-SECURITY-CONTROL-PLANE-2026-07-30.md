# ACR-FC20-03 — External Provider Security Control Plane

- الحالة: `IMPLEMENTATION_IN_PROGRESS`
- البرنامج: `FOUNDATION-COMPLETE-20 / FC20-03`
- النطاق: مصدر GitHub الرسمي فقط
- قرار الإصدار: `BLOCK`
- تفعيل الشبكة أو أي مزود: غير مصرح به

## القرار

تُرفض كل مكالمة مزود قبل طبقة الشبكة ما لم تجتز بوابتين مستقلتين:

1. `ExternalAcquisitionPolicy`: HTTPS وallowlist وحجب الشبكات الخاصة وحد الاستجابة.
2. `ProviderSecurityControlPlane`: تفعيل عام، وحالة المزود، وkill switches، وربط `provider_id` بالمضيف والعملية والعقد، وسياق المؤسسة/المشروع، والحصة والميزانية، وحالة circuit breaker.

وجود مفتاح أو ضبط `ASIE_ALLOW_EXTERNAL_FETCH=true` لا يكفي. الوضع الافتراضي لكل مزود هو `disabled`، والـcontrol plane نفسه معطل افتراضيًا.

## حالات التفعيل

- `disabled`: لا preflight ولا تشغيل حي.
- `preflight`: يسمح فقط بالعمليات المدرجة صراحة في `preflight_operations`.
- `enabled`: يسمح بالعمليات العقدية المعتمدة، مع بقاء بوابة الشبكة والميزانية والعزل مطلوبة.
- global/provider kill switch: منع فوري قبل أي socket attempt.

هذه الحالات إعداد تشغيلي فقط، ولا تمنح سلطة إصدار أو نشر.

## ثوابت الأمان

- كل طلب يحمل `organization_id` و`project_id` و`operation` و`cost_units`.
- لا تُسجل IDs الخام؛ يسجل audit مرجع نطاق مشتقًا بـSHA-256.
- لا يسجل النقل headers أو body أو مفاتيح.
- ربط المضيف خاص بالمزود، ولا تكفي allowlist الشبكة العامة.
- retries مسموحة لطلبات GET العابرة فقط وبحد أقصى صغير؛ POST لا يعاد تلقائيًا.
- response size والtimeout يأخذان الأصغر بين سياسة الشبكة وسياسة المزود.
- الخطأ في quota أو budget أو circuit أو schema/JSON يفشل مغلقًا.
- لا اتصال مباشر بـAAS Runtime أو Finance أو Snapshot.

## التنفيذ الحالي

- `backend/provider_security_control_plane.py`
- `backend/live_provider_catalog.py`
- `backend/live_provider_clients.py`
- `backend/live_provider_preflight.py`
- `backend/production_provider_readiness.py`

## اختبارات القبول السلبية

- غياب تفعيل control plane يمنع النقل قبل URL validation أو opener.
- mismatch بين provider والمضيف مرفوض.
- preflight لا يستطيع تنفيذ عملية live.
- quotas وcost budgets معزولة حسب المؤسسة/المشروع.
- circuit يفتح بعد فشل عابر متكرر ويغلق بعد cooldown.
- global/provider kill switches تمنع الطلب.
- retries محدودة لـGET ولا تكشف المفتاح في audit.
- presence-only secrets لا تعني production readiness.

## ما يمنع إغلاق FC20-03 حالياً

- مخزن quota/circuit الحالي single-process ويحتاج backend مشتركًا قبل multi-replica activation.
- يلزم تثبيت اتصال DNS/العنوان أو transport أقوى لإغلاق نافذة DNS rebinding بين الفحص والاتصال.
- يلزم preflight/health وعقد schema فعلي لكل DeepSeek وTavily وGoogle وPinecone.
- يلزم إثبات cancellation/timeout وresponse-contract violations عبر جميع المزودين.
- لا يوجد تفويض provider/network للبيئة الحية.

## Rollback

التغييرات خارج الحدود المجمدة ولا تتطلب migration. يمكن عكس commits الخاصة بـFC20-03؛ وبما أن التحكم الافتراضي fail-closed، فإن rollback لا يمنح تفعيلًا تلقائيًا. قرار الإصدار يبقى `BLOCK`.
