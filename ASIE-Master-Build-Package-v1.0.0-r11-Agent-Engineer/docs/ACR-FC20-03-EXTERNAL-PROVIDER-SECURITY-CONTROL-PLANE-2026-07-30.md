# ACR-FC20-03 — External Provider Security Control Plane

- الحالة: `COMPLETE`
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
- النقل الافتراضي يربط socket بعنوان IP عام تم التحقق منه في لحظة الاتصال، مع إبقاء اسم المضيف الأصلي لـTLS/SNI والتحقق من الشهادة، ولا يرث proxy من البيئة.
- الخطأ في quota أو budget أو circuit أو schema/JSON يفشل مغلقًا.
- لا اتصال مباشر بـAAS Runtime أو Finance أو Snapshot.

## التنفيذ الحالي

- `backend/provider_security_control_plane.py`
- `backend/live_provider_catalog.py`
- `backend/live_provider_clients.py`
- `backend/live_provider_preflight.py`
- `backend/production_provider_readiness.py`
- `docker-compose.production.yml` (مسار المخزن فقط؛ لا يفعّل المزود)

## اختبارات القبول السلبية

- غياب تفعيل control plane يمنع النقل قبل URL validation أو opener.
- mismatch بين provider والمضيف مرفوض.
- preflight لا يستطيع تنفيذ عملية live.
- quotas وcost budgets معزولة حسب المؤسسة/المشروع ومثبتة بمعاملة SQLite ذرية عبر workers على المضيف المشترك.
- circuit يفتح بعد فشل عابر متكرر ويغلق بعد cooldown.
- global/provider kill switches تمنع الطلب.
- retries محدودة لـGET ولا تكشف المفتاح في audit.
- إجابة DNS خاصة/محجوزة تُرفض قبل إنشاء socket، والاتصال يستخدم IP رقمياً مثبتاً مع اسم TLS الأصلي.
- presence-only secrets لا تعني production readiness.

## قيود التشغيل المتبقية بعد الإغلاق

- مخزن SQLite WAL صالح لعمليات المضيف الواحد فقط؛ أي نشر متعدد المضيفات يظل محجوبًا حتى اعتماد backend موزع.
- بوابة DNS pinning وTLS/SNI ومنع proxy البيئي تبقى اختبارات CI إلزامية.
- فشل timeout/rate-limit الحقيقي لم يُفتعل لدى المزودين؛ السلوك الحتمي للفشل مثبت offline، وتم نقل التمرين التشغيلي إلى FC20-15.
- التفويض الحي المستخدم للـpreflight كان محدودًا بالتشغيلات المسجلة وانتهى بانتهائها؛ لا يوجد تفعيل مستمر للشبكة أو المزودات.

هذه مخاطر تشغيل متبقية مقبولة لاستمرار البرنامج، ولا تمنح سلطة نشر أو إصدار.

## Rollback

التغييرات خارج الحدود المجمدة ولا تتطلب migration. يمكن عكس commits الخاصة بـFC20-03؛ وبما أن التحكم الافتراضي fail-closed، فإن rollback لا يمنح تفعيلًا تلقائيًا. قرار الإصدار يبقى `BLOCK`.

## تحديث الأدلة المرحلي — PR #112

سُجّل PR [#112](https://github.com/alphasigma13579-lang/ASIE/pull/112) كدليل تنفيذ مرحلي داخل FC20-03، وليس كدليل إغلاق للحزمة:

- base: `f71966f34c2d55b178bb9ddc9645c9956d3da9a1`
- head: `c35194f4cde43c82bac2097b1c15372125ab7143`
- squash merge على `main`: `500ccba0b0b2d81708da789c6ff0c286c5415caa`
- ASIE CI run `30820331603`: نجاح، بما في ذلك `623 passed`.
- LIVE-INTEL CI run `30820328314`: نجاح.
- Cross-Platform Determinism run `30820330663`: نجاح.

يثبت هذا الدليل أن بناء نطاق المزود من هوية المستأجر النشطة وملكية المشروع الموثوقة يرفض النطاقات المزورة أو المتقاطعة، وأن أدوار الإدارة/الدعم بلا عضوية مستأجر نشطة لا تتجاوز هذا الحد. لا يثبت PR #112 عقود الاستجابة الحية ولا يمنح تفعيل الشبكة أو المزودين.

## تدقيق معايير الإغلاق بعد PR #112

أغلق PR [#113](https://github.com/alphasigma13579-lang/ASIE/pull/113) المدمج في `main` عند `34ec77d1c3b7abb3cde22c4302cfd69413e39edd` الفجوات غير الحية التالية:

- عقود استجابة fail-closed ومثبتة الإصدار لعمليات DeepSeek وTavily وGoogle Maps Platform وPinecone.
- منع tool calls غير المصرح بها ومنع نموذج DeepSeek خارج allowlist.
- فشل schema قبل تسجيل نجاح النقل، مع تسجيل فشل آمن.
- cancellation تعاوني قبل الشبكة وبين retries وإثبات أصغر timeout.
- منع الاستعداد متعدد النسخ عند استخدام SQLite بدل مخزن موزع.
- كشف صريح لحالة كل فحص حي دون ادعاء أنه نُفذ.

أدلة PR #113: head `67f02965b80b3db5946d3fc8255a0643561be776`؛ ASIE CI `30849216181` نجح مع `634 passed, 10 warnings`؛ LIVE-INTEL `30849215774` نجح؛ Production Provider Readiness `30849215897` نجح؛ Cross-Platform Determinism `30849215778` نجح.

## إغلاق FC20-03 وفتح FC20-04 — 2026-08-04

أُغلقت الحزمة تقنيًا على `main` عند commit `e63f1039ad5a2a1278f0c43a184bbfe4a4862125`، وسُجلت الأدلة التنفيذية في `FOUNDATION-COMPLETE-20.json`.

- Secret-store presence gate: run [30853644493](https://github.com/alphasigma13579-lang/ASIE/actions/runs/30853644493) نجح بلا كشف قيم.
- DeepSeek bounded live preflight: run [30856284242](https://github.com/alphasigma13579-lang/ASIE/actions/runs/30856284242) — HTTP 200، العقد والنموذج متوافقان.
- Tavily bounded live preflight: run [30856375006](https://github.com/alphasigma13579-lang/ASIE/actions/runs/30856375006) — HTTP 200، نتيجة واحدة وائتمان واحد، دون اعتماد تلقائي.
- Google Geocoding bounded live preflight: run [30856449273](https://github.com/alphasigma13579-lang/ASIE/actions/runs/30856449273) — HTTP 200 لعنوان عام ثابت دون حفظ الموقع.
- Pinecone bootstrap: PR [#119](https://github.com/alphasigma13579-lang/ASIE/pull/119)، run [30857670636](https://github.com/alphasigma13579-lang/ASIE/actions/runs/30857670636) أنشأ `vision2030-kb-e5` محميًا من الحذف، بلا vectors أو بيانات عملاء.
- Pinecone final preflight: run [30857803201](https://github.com/alphasigma13579-lang/ASIE/actions/runs/30857803201) — HTTP 200، ready، host مكتشف، `multilingual-e5-large` و`chunk_text` متوافقان، ولا كتابة.
- إصلاح توافق Python 3.13 للنقل المثبت: PR [#118](https://github.com/alphasigma13579-lang/ASIE/pull/118) مع نجاح LIVE-INTEL [30855663636](https://github.com/alphasigma13579-lang/ASIE/actions/runs/30855663636)، ASIE CI [30855663633](https://github.com/alphasigma13579-lang/ASIE/actions/runs/30855663633)، والحتمية [30855663695](https://github.com/alphasigma13579-lang/ASIE/actions/runs/30855663695).
- Bootstrap guardrails: LIVE-INTEL [30857455373](https://github.com/alphasigma13579-lang/ASIE/actions/runs/30857455373)، ASIE CI [30857455477](https://github.com/alphasigma13579-lang/ASIE/actions/runs/30857455477)، والحتمية [30857455554](https://github.com/alphasigma13579-lang/ASIE/actions/runs/30857455554)، وجميعها ناجحة.

لم تظهر الأسرار، ولم تُرسل بيانات عملاء، ولم تُحفظ payloads، ولم تتغير الملفات المجمدة. انتقل FC20-03 إلى `COMPLETE` وFC20-04 إلى `OPEN`. يبقى حكم الإصدار `BLOCK` وتبقى `external_network_authorized=false` و`provider_activation_authorized=false`.

