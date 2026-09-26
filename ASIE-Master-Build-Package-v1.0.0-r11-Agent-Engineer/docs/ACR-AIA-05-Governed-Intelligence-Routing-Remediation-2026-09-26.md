# ACR-AIA-05 — تصحيح مسارات الذكاء والموقع إلى AAS المحكوم

## Identification — بيانات الطلب

- ACR ID: `ACR-AIA-05`.
- تاريخ الطلب: 2026-09-26، المنطقة الزمنية Asia/Riyadh.
- الحالة: **PROPOSED / REVIEW_REQUIRED**؛ مقترح للمراجعة، لا موافقة تنفيذ أو نشر.
- صاحب الطلب: مالك ASIE؛ أُجيز إعداد الطلب بعد مناقشة المسار، ولا تُنسب هذه الموافقة إلى سلطة معمارية لم تسجل قرارها بعد.
- معدّ المقترح: Engineering. المراجعون المطلوبون: سلطة المعمارية/AAS، وأمن العزل والمزودات، وحوكمة AI؛ لم يُسجل اعتمادهم في هذه الوثيقة.
- رأس الفحص الرسمي: `d29dcf78d0347f9ccd14617cde72c00236d1ff84`؛ ليس نسخة Hostinger.
- الإصدار المستهدف: امتداد محكوم داخل AAS القائم مع إبقاء مسار Project Run v1 ثابتًا؛ رقم إصدار التجميد التالي يُحسم عند الموافقة، ولا يتغير هنا.
- خطة المرحلة: [بيتا المالك والإدارة المستقلة](ASIE-BETA-EXECUTION-MASTER-PLAN-2026-09-09.md).
- الدليل السابق: [تدقيق 2026-09-23](ASIE-AIA-PARALLEL-ROUTING-AUDIT-2026-09-23.md). هذه الوثيقة طلب علاج وليست بديلًا عن تقرير التدقيق.

### السلطة والقرار المطلوب قبل التنفيذ

[PROGRAM-CLOSE-10](PROGRAM-CLOSE-10-EMERGENCY-REMEDIATION-CONSOLIDATION-AND-REBASELINE-2026-07-29.md) و[قرار التجميد](../../EMERGENCY-RELEASE-FREEZE.json) يحكمان المعالجة والإصدار. [FOUNDATION-COMPLETE-20، §6](FOUNDATION-COMPLETE-20-CORE-INTELLIGENCE-COMPLETION-PROGRAM-2026-07-29.md) يقصر اقتراح تغيير الملفات المجمدة على FC20-12؛ [السجل الآلي](../../FOUNDATION-COMPLETE-20.json) يصف FC20-12 حاليًا ضمن Decision Council v2 وgoverned AAS dispatch.

لذلك يطلب هذا ACR قرارًا مسجلًا يحدد هل يُقبل إصلاح التوجيه المحدود ضمن ملكية FC20-12 أم يحتاج تعديل نطاق برنامج مستقل أولًا. **لا يتوسع نطاق FC20-12 ضمنيًا، ولا تمنح FC20-08/09/10/13 سلطة تعديل التجميد.** تبقى اعتماديات الحزم وحالاتها كما هي؛ لا تحرر الوثيقة مانع predecessor، ولا تصف FC20-12 أو FC20-16 بالمكتمل. إذا لم يُحسم هذا الشرط، تبقى الشريحة المجمدة غير مصرح بها.

المرجع المعماري المعتمد هو [AIA-01](AIA-01-Intelligence-Constitution-v1.0.0.md) و[AIA-02 v1.2.1 النهائي](AIA-02-Intelligence-Operating-Architecture-v1.2.1.md)، وليس نسخة Candidate مؤرشفة. أي حاجة لتغيير قاعدة دستورية، بما فيها السماح باتصال متصفح لا تستوعبه الحدود المعتمدة، تُرفع عبر ICCR مستقل؛ هذا ACR لا يمنح إعفاءً دستوريًا.

## Frozen Surface — السطح الحالي المجمد

مالك السطح: AAS؛ [Manifest v1.0](ASIE-AAS-Runtime-Freeze-Manifest-v1.0.json). الحدود القائمة:

```text
Kernel → Heart Controller → Hearts → Bus Controller
       → ASIE System Bus → Socket Contract Layer → Module Runtime
       → Snapshot Assembly (في Project Run فقط)
```

هذه خريطة السلطة وليست ادعاء بأن كل طلب HTTP يستدعي كل مكوّن على التوالي. في التنفيذ القائم يرسل `ModuleRuntime.execute` الرسالة إلى `SystemBus.publish` ثم `BusController.admit` وSocket validation **قبل** استدعاء handler. لا تُستبدل هذه الآلية بناقل أو Runtime ثانٍ.

العقود الحالية المهمة: `ai.integration.request.v1` و`ai.integration.result.v1`، والسوكت `socket.ai.integration`، والوحدة `module.ai_integration`. هذه بوابة محلية معطلة؛ `ModelRouter` يرفض سجلًا غير فارغ، وAI adapter يتطلب `AIIntegrationInputEnvelope.v1` ومرجعي run/snapshot. وRegistry وSocket وRuntime يرفضون external-fetch modules. إذًا مجرد استدعاء shell ثم استدعاء DeepSeek مباشرة ليس تصحيحًا.

### ما يثبته الكود وما لا يثبته

| المسار | البداية والوجهة الحالية | البيانات والنتيجة | الحكم المحدود |
|---|---|---|---|
| سياق السوق | HTTP → خدمة `LiveMarketContextService` → Tavily/Google/Pinecone مباشرة | سياق المشروع المحفوظ والموقع المؤكد؛ مرشحات للمراجعة | توجد ضوابط صلاحية ومصادر، لكنها لا تعوض عبور AAS المفقود |
| الموقع والمنافسون | HTTP → Google client مباشرة | عنوان أو إحداثيات؛ عنوان منظم/منشآت | الاتصال الخادمي يتجاوز السوكت في الرأس المفحوص |
| التفسير | HTTP → `LiveNarrativeService` → DeepSeek مباشرة | سياق معتمد وإيصال؛ نص للمراجعة | لا يمر عبر AIIntegrationShell؛ wrapper أمامي موجود ولا يثبت رحلة UI كاملة |
| Pre-Run | HTTP → Repository/PreRun service مباشرة | state/hash وبعض السياق من الطلب؛ سجل سياق | المسار المحكوم ونشأة الحالة الخادمية يحتاجان التصحيح |
| سند | DOM/sessionStorage/events → حقل/مرحلة | مقصد تنقل وموضع عودة | مساعد محلي، لا نموذج ولا قناة مزودات |
| عرض الخريطة | المتصفح → Google Maps JavaScript | مفتاح متصفح مقيد، viewport وموقع العرض بحسب SDK | اتصال خارجي مستقل عن بحث الخادم؛ يجب ضبطه لا إنكاره |

لا يثبت الفحص تشغيل مفاتيح Hostinger أو تسربًا فعليًا أو سبب كل عيوب المنتج. ولا تُنسب إليه إدانة Finance أو Snapshot أو Decision Council دون دليل. #166 و#167 يحافظان على أساس التخزين والتعافي؛ لا يعادان لمجرد وجود هذا ACR.

## Proposed Change — السلوك المطلوب

### 1. من أين وإلى أين

```text
واجهة العميل
  → HTTP: جلسة/صلاحية/ملكية مشروع/موافقة موقع/حدود طلب
  → IntelligenceContextWorkflow القائم (تنسيق Pre-Run)
  → ModuleRuntime القائم → System Bus/Bus Controller/Socket admission
  → الوحدة المسجلة المختصة → بوابة المزود المحكومة → المزود
  ← مرشح محدود مع مراجع ومصدر وحالة/فشل آمن
  → مخزن الأدلة الأصلي → مراجعة بشرية → سياق معتمد

طلب تفسير سياق معتمد
  → نفس حدود HTTP وAAS
  → module.ai_integration / AIIntegrationShell القائم
  → Trusted Prompt Assembly → ModelRouter المحكوم → DeepSeek
  ← validation + grounding + امتناع/مراجعة → عرض باللغة المختارة

سند → الحقل الناقص ومسار العودة فقط
Project Run v1 → تسلسله المالي/القرار/اللقطة الحالي دون إضافة هذا السياق إليه
```

- API يستقبل نية محدودة؛ لا يبني عميل مزود ولا يستدعي provider service/handler مباشرة. يشتق tenant/project/scope من الجلسة والمشروع لا من ادعاء المتصفح.
- منشئ الرسائل الخادمي يستعمل هوية source module مسجلة يملكها Workflow، لا module/socket من المتصفح. يتحقق مالك التنفيذ من التفويض الخادمي وملكية السياق قبل أي أثر؛ التسجيل وحده ليس صلاحية.
- Workflow يستعمل نفس ModuleRuntime ونفس Bus/Registry؛ لا يُنشأ `RunScopedModuleRuntime` قبل وجود run، ولا تُختلق run_id أو snapshot_id لإرضاء عقد v1.
- وحدات الموقع والسوق تجمع المرشحات خلف سوكتات مسجلة. التنسيق لا يحسب Finance ولا يتصل به.
- إنشاء السياق ومراجعته واعتماده يمر بأوامر مسجلة إلى مالك كتابة السياق؛ Workflow ينسق الأوامر، وhandler الكتابة لا يعيد استدعاء Workflow على الأمر نفسه. Repository تبقى آلية التخزين داخل هذا المالك، لا مسار كتابة بديل من HTTP.
- قراءة السياق تبقى قراءة مخولة بلا تشغيل مزود. إخفاء الواجهة أو wrapper جديد لا يغلق مسار POST المتجاوز: كل منفذ قديم إمّا يعاد توجيهه إلى الأمر المحكوم أو يفشل برسالة انتقال آمنة قبل أي أثر.
- المخرجات تعود للعميل كمعنى أعمال ومصادر وحدود وخطوة تالية، بلا contract/engine/hash/secret diagnostics. العربية افتراضية واللغة المختارة تشمل الفشل والتفسير؛ [EKB-08](EKB/EKB-08-Customer-Language-and-Presentation-Contract.md) حاكم.

### 2. سجل التدفق والملكية

الأسماء في القسم التالي **مقترحة وليست مسجلة الآن**. يُرفض التنفيذ قبل تسجيلها ومراجعتها في Registry وسجل API.

| الأمر / مالك التنفيذ | المدخل الأدنى المأذون | الوجهة والنتيجة | الأثر والفشل |
|---|---|---|---|
| موقع / وحدة موقع مسجلة | project ref، عملية geocode/reverse، عنوان محدود أو إحداثيات أكدها المستخدم؛ scope خادمي | Google geocode فقط؛ عنوان/إحداثيات/دقة ومصدر | لا حفظ GPS خام قبل التأكيد؛ فشل الموقع يبقي الإدخال اليدوي |
| سوق / وحدة سياق سوق مسجلة | activity/sector/country/location من المشروع المحفوظ، ومراجع قبول المصدر | Tavily، Places، استرجاع Pinecone كل بعملية مسموحة؛ مرشحات مستقلة | لا زحف Maps ولا تحويل مرجع إلى مصدر قابل للجلب؛ partial result معلّم ولا اعتماد تلقائي |
| سياق / مالك كتابة سياق مسجل داخل التنسيق القائم | مراجع مرشحات مقبولة ومراجعة خادمية، إصدار وfingerprint | SQLite وسجل الأدلة؛ draft/review/approved receipt | state/hash من الخادم؛ transaction/CAS تمنع اعتماد إصدار تغير أثناء المراجعة |
| تفسير / AIIntegrationShell | context ref/version + receipt + locale + template/output types مسجلة | passages معتمدة محدودة من المخزن → DeepSeek؛ تفسير مرتبط بمراجع أو امتناع | لا أرقام مالية جديدة أو verdict؛ لا أدوات أو إجراء؛ فشل لا يغيّر السياق |
| عرض خريطة / UI | الموقع الذي أكد المستخدم عرضه ومفتاح SDK المقيد | Maps JavaScript؛ خريطة عرض | لا حساب/بحث مالي في المتصفح؛ اتصال SDK محكوم بإذن منفصل وkill state |
| سند / UI محلي | معرف حقل عرض ونية تنقل وreturn route | الحقل بالضبط ثم العودة | لا إرسال معلومات إلى مزود ولا منح صلاحية |

لكل عملية خادمية: correlation/audit ref غير حساس، tenant/project/op/version/fingerprint، deadline شامل، محاولة أصلية وإعادة واحدة على الأكثر للفشل العابر وداخل المهلة. لا retry لرفض الصلاحية أو المصدر أو المخطط أو سياسة الإيقاف. تُراجع السياسة الحالية إن كانت أشد وتُحفظ الأشد. يمنع الإيقاف الطلبات الجديدة وإعادتها؛ لا يُدّعى سحب طلب أُرسل بالفعل.

Tavily يرسل query محدودًا ونطاقات مسموحة؛ Google يرسل الموقع/التصنيف اللازمين فقط؛ Pinecone يرسل query إلى namespace خادمي مأذون؛ DeepSeek يستقبل الأدلة المعتمدة اللازمة فقط، لا المشروع كاملًا أو بيانات اتصال المالك. أسماء المزودات تفاصيل إدارية وليست حالات برمجية تعرض للعميل.

## Contract Impact — أثر العقود والملكية

### إضافات مطلوبة للمراجعة، لا تسجيل فعلي

| العقود المقترحة | socket المقترح | المالك |
|---|---|---|
| `location.resolve.v1` / `location.resolved.v1` | `socket.location.resolve` | `module.location_context` |
| `market.context.build.v1` / `market.context.candidate.v1` | `socket.market.context` | `module.market_context` |
| `intelligence.context.command.v1` / `intelligence.context.result.v1` | `socket.intelligence.context` | `module.intelligence_context` |
| `ai.integration.request.v2` / `ai.integration.result.v2` | `socket.ai.integration.v2` | نفس `module.ai_integration`؛ لا بوابة جديدة |

- v1 للذكاء يبقى disabled محليًا بعقوده واختباراته. v2 إضافي في shell نفسه، منفصل dispatch ولا fallback صامت إلى v1 أو إلى الخدمة المباشرة.
- Request v2 يفرض tenant/project/context/version/receipt/op refs وlocale؛ run/snapshot لا يُطلبان لـcontext build، ولا يقبلان إلا عند مرجع فعلي مخول. input_hash والقالب وprompt_hash يحسبها الخادم؛ raw prompt أو URL/namespace اختاره المتصفح ممنوع.
- العقود تحدد أنواع الحقول والطول/enums/extra-field rejection، وليس مجرد presence validation. حارس السلطة الخادمي ينقلها إلى الوحدة ولا يكتفي بأن module_id مسجل.
- Bus يحمل مراجع سياق وأدلة وبصمات لا prompt خام أو أسرار أو passages. Trusted Prompt Assembly داخل shell فقط بعد إعادة التحقق من الهوية والإيصال والإصدار والمصدر.
- Result v2 structured: locale، claims مرتبطة بـevidence_refs، limits/missing evidence، abstention/review status. schema وcitation resolution والسياسة تُتحقق خارج النموذج؛ ثقة النموذج الذاتية ليست احتمالًا إحصائيًا موثوقًا.
- المحتوى المسترجع بيانات غير موثوقة لا تعليمات. النص المعتمد يربط بموضع/إصدار/إسناد قابل للتحقق؛ metadata وحدها لا تكفي لتفسير مضمون مصدر. عند غياب passages معتمدة يمتنع عن التحليل ويشرح النقص.
- منع numeric ownership لا يمنع اقتباس حقيقة منشورة موثقة ومراجعة؛ لكنه يمنع إنشاء assumption مالي نهائي أو حساب NPV/IRR/DSCR أو قرار تمويل.
- current HTTP paths لا تُعاد تسميتها في موضعها. تبقى projections المسجلة حيث تستوعب المعنى؛ أي كسر يتطلب API version/migration صريحة. تسجل تغييرات response/types/clients بالتوافق.
- لا يتغير ProjectRun v1 sequence ولا sealed output ولا Snapshot lineage. إدخال السياق المعتمد في ProjectRun/Snapshot في المستقبل يحتاج شريحة وعقد frozen-boundary منفصلين؛ إكمال هذا التوجيه لا يعني اكتمال FC20-08 أو FC20-12.

### السماح المحدود والتجميد

قائمة التغيير المجمد **المطلوب الموافقة عليها فقط**:

| الملف | لماذا يلزم | المسموح المقترح |
|---|---|---|
| `backend/aas_registry.py` | التسجيل الحالي لا يعرف أوامر السياق؛ external flag مرفوض | إضافة العقود/السوكتات/الملاك المحصورين ووصف القدرة دون إخفائها |
| `backend/socket_contracts.py` | منع خارجي مطلق مع validation | قبول محدد لعقد/هدف/هوية مأذونة بعد سياسة deny-by-default؛ رفض كل ما عداها |
| `backend/module_runtime.py` | adapters/handlers ورفض external modules الحالي | تسجيل المحدد، تفويض execution وإعادة فحص السياسة قبل الأثر؛ v1 محفوظ |
| `docs/ASIE-AAS-Runtime-Freeze-Manifest-v1.0.json` | بصمات الثلاثة تتغير لاحقًا | تحديث محكوم مع ACR/version/old-new hashes/diff؛ ليس تعديلًا في هذا PR |

لا يجوز ادعاء `external_fetch_enabled=false` لوحدة ترسل فعليًا إلى الخارج؛ تُصرّح القدرة وتبقى غير مفعلة افتراضيًا. التحقق من feature flag وحده أو وجود مفتاح ليس موافقة. لا يُحذف الحظر العام ولا يفتح كل module خارجي؛ يُقيد الاستثناء بالأمر والمالك والمصدر والمستأجر والبيئة والمدة وقرار التفعيل.

خارج allowlist: `aas_kernel.py` و`heart_controller.py` و`bus_controller.py` و`system_bus.py` و`project_run_workflow.py` و`snapshot_assembly.py` و`runtime_freeze.py`. إذا ظهر احتياج لتغيير أحدها يتوقف الجزء المتأثر ويعاد تقدير ACR؛ لا تُوسّع القائمة خلال التنفيذ. Finance وDecision Council خارج النطاق تمامًا.

ملفات غير مجمدة متوقعة في شرائح التنفيذ اللاحقة: `asie_local_api.py`، `intelligence_workflow.py`، `intelligence_prerun_service.py`، `ai_integration.py`، `live_intelligence_product.py`، `live_provider_clients.py`، `provider_security_control_plane.py`، `repository.py`، سجلا canonical terminology/API، `src/api.ts` وtypes وعناصر العرض المتأثرة، والاختبارات. كل ملف يُراجع بسبب مثبت؛ لا تصريح إعادة كتابة عامة. محولات الموقع/السوق الجديدة إن لزمت تملك التنفيذ خلف السوكت فقط.

## Safety Constraints — الضوابط الملزمة

- الشبكة والمزودات معطلة في البناء والاختبارات المعزولة؛ لا مفاتيح فعلية ولا preflight حي بهذا الطلب.
- AI لا يمتلك controlled numbers أو حكمًا سياديًا أو source activation؛ لا أدوات أو تنفيذ إجراءات.
- منافذ التشغيل تبقى frontend 5194 وAPI 8794.
- Report/Decision Pack/UI تبقى projections للّقطة الرسمية؛ المرشح/التفسير يُعرضان كطبقة مراجعة منفصلة لا كحقيقة Snapshot جديدة.
- SQLite/السجل الأصلي مصدر الحقيقة؛ Pinecone فهرس مشتق قابل لإعادة البناء. namespace من الخادم ومعزول حسب النوع/المستأجر/المشروع؛ المعرفة العامة لا تتضمن private project أو Places. لا تغيير ترحيل #166/#167 بلا عيب مثبت.
- الإذن الحالي `platform.manage`/platform_admin لا يُخفف لتشغيل المالك؛ البريد/اسم asie لا يمنحان دورًا. لا cross-tenant حتى للطلب ذي context_id صحيح.
- الإيصال مربوط بالسياق والنسخة والبصمة ومدة الاعتماد؛ التحقق والاستهلاك atomic مع operation ledger. replay لنفس العملية يعيد نتيجتها، لا يستهلك إيصالًا ثانيًا؛ changed body/key conflict يرفض. stale/expired/revoked context يفشل قبل client construction.
- GPS بموافقة، وتأكيد موقع المشروع مستقل عن إذن الجهاز. لا حفظ raw location قبل التأكيد. العنوان اليدوي لا يتحول تلقائيًا إلى location معتمد.
- Maps SDK يُحجب قبل موافقة عرضه وتفويض تشغيله، وkill state يمنع تحميلًا جديدًا/بحثًا جديدًا؛ لا يَعِد بإزالة اتصال SDK بدأ. قيود key/referrer/API، attribution/terms/retention وحدود الإرسال توثق قبل التشغيل. إن استلزم ذلك خروجًا دستوريًا، لا يشغّل قبل ICCR.
- نتائج Places ليست تلقائيًا داخل دائرة البحث: locationBias انحياز لا حد هندسي. لا تعرض مسافة/نطاقًا صارمًا دون حساب موثق وفلترة إذا وُعد المستخدم بذلك.
- الأخطاء والـaudit والملخصات تستخدم allowlist من حالات آمنة؛ لا `str(exc)` أو أسرار أو اسم متغير سري. التفاصيل الفنية في سجل مشرف محمي ومنقح، لا raw exception dump.
- telemetry: حالة/مدة/محاولات/usage/request correlation فقط؛ لا prompt/passages/secret/location raw في Bus/audit/log. رد المزود الكبير/غير الصحيح يرفض قبل الحفظ.
- لا بوابة دفع/ترقية في فشل المزود؛ تعافٍ محدود أو إدخال يدوي أو انتظار واضح.

## Migration and Rollback — الانتقال والتراجع

1. بعد موافقة السلطة على النطاق، تنفذ شرائح صغيرة: تسجيل/توجيه داكن، سياق ومعاملات، shell v2 وإغلاق الاستدعاء المباشر، ثم عرض/سند. يُثبت كل جزء باختبارات قبل التالي.
2. إبقاء السجلات التاريخية والقراءات والإيصالات كما هي. Legacy context لا يعاد اعتماده لمجرد وجود state/hash؛ إعادة تقييم خادمية تولد نسخة جديدة مع provenance وتحافظ على الأصل.
3. لا ترحيل بيانات المالك في هذه الشريحة. إن احتاج schema إضافة، تكون additive مع خطة نسخ/استعادة وموافقة مستقلة واختبار توافق الإصدار السابق؛ لا حذف JSON/SQLite أو reuse namespace مشتركة.
4. التراجع يوقف أوامر القدرات الجديدة ومحاولات إعادتها ويحافظ على البيانات؛ يعود إلى إصدار رسمي known-safe مع تعطيل المنافذ المتجاوزة. **لا يعيد HTTP → provider أو HTTP → كتابة Pre-Run المباشرة كحل سريع.**
5. triggers: فشل auth/tenant/source gate، كسر v1 parity/freeze، تسرب حساس، إخراج غير موثق، تعارض/فقد بيانات، أو bypass ظاهر. يعزل capability أولًا ويثبت الدليل والرأس، لا يستخدم fallback مالي أو سياق وهمي.
6. قبول التراجع يحتاج تمرينًا يثبت القراءة وسلامة البيانات واستعادة نسخة مستقلة ورفض القديم؛ نجاح إعادة تشغيل container وحده غير كافٍ.

## Verification — بوابات الإثبات

هذه **اختبارات مطلوبة للتنفيذ اللاحق**، لا نتائج ناجحة تدعيها الوثيقة.

| البوابة | الإثبات الإيجابي والسلبي المطلوب |
|---|---|
| السلطة والتجميد | قرار نطاق FC20-12، ACR معتمد، diff محصور وmanifest old/new؛ بقية frozen hashes ثابتة |
| عبور فعلي | spy/trace على Runtime→Bus→Socket→handler، رفض الرسالة قبل provider construction؛ static import guard على HTTP كفحص مساعد لا بديل سلوكي |
| منافذ قديمة | create/pre-run/review/approval/location/market/narrative لا تكتب أو تجلب خارج dispatcher؛ manual direct requests تفشل أو تمر بالمسار نفسه |
| الصلاحية والعزل | unauthenticated/non-admin/cross-tenant/project/context/receipt denied دون client أو write؛ scope خادمي لا namespace متصفح |
| السياق | server state/hash، malformed/extra fields denied، durable idempotency وفingerprint conflict، concurrency/CAS/receipt consume وانقطاع/استئناف |
| المزودات | default denied وkey-only denied، deadline/size/retry/circuit/kill tests مع transports اصطناعية؛ لا شبكة حقيقية |
| المصادر والموقع | unadmitted/revoked/ref-only URL denied، consent/confirm/manual، no pre-confirm persist وPlaces retention/attribution |
| AI shell | v1 disabled parity، v2 same shell، injection/schema/unknown citations/ungrounded claims/controlled verdict rejected؛ abstention عند metadata-only، no raw prompt in Bus |
| المخرجات والفشل | sentinel سري في استثناء وفي رد مزود لا يظهر في UI/summary/audit؛ لغة كاملة وسبب أعمال وتعافٍ |
| سلامة المسار الرسمي | ProjectRun v1 golden/parity وSnapshot immutability وعدم partial/fake Snapshot وعدم AI/market→Finance |
| UI وسند | موافقة الموقع، حالات نقص وفشل بالعربية، سند إلى الحقل الصحيح وحفظ/عودة؛ لا استدعاء AI من سند |
| البيانات والتراجع | مخزن أصلي، private/public separation، index rebuild معزول، نسخ/استعادة وتراجع capability دون bypass |
| الفهرسة | وجود روابط EKB، الحالة PROPOSED لا APPROVED، مرجع AIA-02 النهائي لا Candidate، ربط الخطة |

الفحوص المستهدفة تتبع الملفات الفعلية. اختبارات الأمان وسلامة البيانات والعزل إلزامية. البوابة الكاملة/build/freeze/parity والمراجعات المطلوبة تُجمع مرة على الرأس النهائي؛ لا تعاد بلا تغيير مؤثر أو فشل متقلب موثق. TestSprite غير المفعّل ليس بوابة هذه المرحلة ولا سببًا لتعطيل المراجعة المتاحة.

دليل كل شريحة: commit SHA وchanged paths وأسماء الاختبارات/نتائجها وworkflow IDs وملاحظات المراجعة والتراجع والمخاطر المتبقية. لا يُعتد بعدّ test definitions أو نجاح registration كدليل تنفيذ أو live acceptance.

## Decision — القرار ونقاط التوقف

| مستوى القرار | الحالة في هذا الطلب |
|---|---|
| موافقة إعداد ACR | صريحة من المالك في 2026-09-26 |
| اعتماد معماري ونطاق FC20-12 | مطلوب؛ غير مسجل هنا |
| تصريح بناء داكن | غير ممنوح قبل القرار والتجميد المحكوم؛ لا تشغيل مزود |
| حسم معاملة SDK/الحاجة لـICCR | مطلوب قبل live map؛ لا استثناء ضمني |
| تشغيل Hostinger/Canary | قرار FC20-16 مستقل exact-head/environment/time؛ غير ممنوح |
| اكتمال بيتا/الدعوات | غير مثبت؛ الدعوات مغلقة |

نقطة التوقف الآن: PR توثيقي فقط؛ لا كود أو frozen hash أو سجل حزمة أو بيانات أو مفاتيح أو نشر. المهمة التالية: مراجعة ACR وحسم السلطة والـallowlist، ثم خطة وهدف قصير لأول شريحة توجيه داكن فقط بعد الموافقة. تبقى لوحة الإدارة وتصحيح النشاط والتعريب وتشغيل المالك في ترتيب خطة البيتا؛ لا تُحذف لصالح هذا العلاج.

## Evidence — مراجع الفحص المثبتة

جميع أرقام الأسطر أدناه تخص رأس GitHub الرسمي `d29dcf78d0347f9ccd14617cde72c00236d1ff84`؛ تعاد مطابقتها عند تغير الرأس، ولا تمثل Hostinger.

- `backend/asie_local_api.py:295–318, 1188–1213, 1240–1298, 2227–2576`: bootstrap، helpers مباشرة، metadata narrative، وHTTP routes؛ `2607–2642` للمقارنة بمسار ProjectRun.
- `backend/module_runtime.py:400–432, 494–539`: shell adapter ورفض external modules وBus admission قبل handler.
- `backend/aas_registry.py:112–120, 493–527, 656–660, 841–850`: حظر التسجيل الخارجي وعقود/سوكت/shell المحلية.
- `backend/socket_contracts.py:137–162` و`backend/system_bus.py:74–88`: registration/binding validation والمنع قبل التسليم.
- `backend/ai_integration.py`: ProviderPolicyEngine/ModelRouter/OutputValidation/AIIntegrationShell؛ default DENY_ALL وv1 disabled، لا مسار إنتاجي مفعل.
- `backend/intelligence_workflow.py`: Workflow موجود لكن cache idempotency في الذاكرة وraw error؛ لا يكفي للإثبات المعاملاتي المطلوب.
- `backend/live_intelligence_product.py:163–333`: مرشحات السوق والتفسير المباشر؛ ليست كتابة Snapshot.
- `src/LiveCockpit.tsx:65–85`، `src/LiveMarketMap.tsx:123–145`، `src/api.ts:644–654`، `src/ASIECompleteSurfaceMount.tsx:292–399`: الربط الأمامي وحدود سند؛ وجود wrapper لا يثبت caller.
- [#166](https://github.com/alphasigma13579-lang/ASIE/pull/166) → `2dccc2c45c2b1967e277edf6db6a681a04b2654a` ثم [#167](https://github.com/alphasigma13579-lang/ASIE/pull/167) → `435777008e01bafc73ab3bca86cc8945e311b610`: أعمال التخزين المحفوظة.
