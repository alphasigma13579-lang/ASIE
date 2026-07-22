# Chart Data Algorithms

## خوارزميات بيانات الشارتات

## Principle

## المبدأ

Charts are generated from verified platform data, not from AI imagination.

الشارتات تولد من بيانات منصة موثقة، وليس من خيال الذكاء الاصطناعي.

AI may explain chart meaning, but chart datasets must be produced by owner modules.

يجوز للذكاء الاصطناعي شرح معنى الشارت، لكن Dataset الشارت يجب أن ينتج من الموديولات المالكة.

## CHART-ALG-01 Chart Dataset Authorization

## تفويض Dataset الشارت

Owner:

المالك:

`Audit / Observability Module` / موديول التدقيق والمراقبة, with data owner approval.

Steps:

الخطوات:

1. Identify chart id / تحديد معرف الشارت.
2. Identify owner module / تحديد الموديول المالك.
3. Verify actor permission / التحقق من صلاحية المستخدم.
4. Verify data contract / التحقق من عقد البيانات.
5. Verify source map or formula map / التحقق من خريطة المصدر أو المعادلة.
6. Return authorized dataset / إرجاع Dataset مصرح بها.

Reject if:

يرفض إذا:

- No owner module / لا يوجد موديول مالك.
- No source or formula map / لا توجد خريطة مصدر أو معادلة.
- AI-generated numbers detected / اكتشاف أرقام مولدة من AI.

## CHART-ALG-02 Market Chart Dataset Builder

## باني بيانات شارتات السوق

Owner:

المالك:

`Market Intelligence Module` / موديول ذكاء السوق.

Produces:

ينتج:

- Competitor map points / نقاط خريطة المنافسين.
- Demand heatmap cells / خلايا خريطة حرارة الطلب.
- Source confidence bars / أعمدة ثقة المصادر.
- Price distribution box plot values / قيم صندوق توزيع الأسعار.
- Price scatter samples / عينات نقاط الأسعار.
- Source health timeline / خط صحة المصادر.

Rules:

القواعد:

- Every point must have source id / كل نقطة لها مصدر.
- Geo charts require GPS or Map Pin context / شارتات الخريطة تتطلب GPS أو Pin.
- Price charts use valid samples after outlier filtering / شارتات الأسعار تستخدم عينات صحيحة بعد فلترة الشذوذ.

## CHART-ALG-03 Finance Chart Dataset Builder

## باني بيانات شارتات التمويل

Owner:

المالك:

`Finance Engine Module` / موديول محرك التمويل.

Produces:

ينتج:

- Cost breakdown / تقسيم التكلفة.
- CapEx / OpEx split / فصل CapEx و OpEx.
- Cash flow series / سلسلة التدفق النقدي.
- Revenue and expense series / سلسلة الإيرادات والمصاريف.
- Break-even dataset / بيانات نقطة التعادل.
- Sensitivity dataset / بيانات الحساسية.
- MCMC histogram bins / سلال مدرج MCMC.
- Waterfall bridge / شارت شلال الربح.

Rules:

القواعد:

- Dataset must come from `finance.result.v1` or related finance outputs.
- Dataset يجب أن تأتي من `finance.result.v1` أو مخرجات التمويل المرتبطة.

- No chart dataset from AI advisory text.
- لا Dataset للشارت من نص استشارة AI.

## CHART-ALG-04 Decision Chart Dataset Builder

## باني بيانات شارتات القرار

Owner:

المالك:

`Decision Council Module` / موديول مجلس القرار.

Produces:

ينتج:

- Vote distribution / توزيع الأصوات.
- Persona radar values / قيم رادار الشخصيات.
- Consensus gauge / عداد الإجماع.
- Risk matrix / مصفوفة المخاطر.
- Dissent evidence table / جدول اعتراضات بالأدلة.

Rules:

القواعد:

- Persona chart values must map to persona outputs.
- قيم شارت الشخصيات يجب أن ترتبط بمخرجات الشخصيات.

- Consensus gauge must use deterministic consensus scoring.
- عداد الإجماع يستخدم حساب الإجماع الحتمي.

## CHART-ALG-05 Admin and Observability Chart Dataset Builder

## باني بيانات شارتات الإدارة والمراقبة

Owner:

المالك:

`Admin Module` / موديول الإدارة and `Audit / Observability Module` / موديول التدقيق والمراقبة.

Produces:

ينتج:

- Real-time user activity / نشاط المستخدمين الحالي.
- Revenue trend / اتجاه الإيرادات.
- Subscription distribution / توزيع الاشتراكات.
- AI model usage / استخدام نماذج AI.
- Provider latency / زمن استجابة المزود.
- Error heatmap / خريطة حرارة الأخطاء.
- Quarantine queue / طابور العزل.
- Feature flag adoption / تبني الخصائص.
- Message flow Sankey / سانكي تدفق الرسائل.
- Module network graph / شبكة الموديولات.
- Google Analytics traffic trend / اتجاه زيارات Google Analytics.
- Zoho Analytics BI dashboard dataset / Dataset لوحات Zoho Analytics.
- Product funnel chart / شارت قمع المنتج.
- Retention cohort chart / شارت Cohort الاحتفاظ.

Rules:

القواعد:

- Operational charts use telemetry and audit data only.
- شارتات التشغيل تستخدم Telemetry وAudit فقط.

- Revenue charts use subscription/billing outputs only.
- شارتات الإيرادات تستخدم مخرجات الاشتراك/الفوترة فقط.

- Product analytics charts must use sanitized aggregated analytics.
- شارتات تحليلات المنتج تستخدم بيانات منقحة ومجمعة فقط.

## CHART-ALG-06 Chart State Resolver

## حل حالة الشارت

Every chart must resolve one of:

كل شارت يجب أن يحدد إحدى الحالات:

- `ready` / جاهز.
- `loading` / تحميل.
- `empty` / فارغ.
- `insufficient_data` / بيانات غير كافية.
- `blocked_by_validation` / ممنوع بسبب التحقق.
- `error` / خطأ.
- `permission_denied` / صلاحية مرفوضة.

AI must not convert `insufficient_data` into fabricated insight.

ممنوع على AI تحويل نقص البيانات إلى استنتاج مختلق.

## CHART-ALG-07 Landing Preview Dataset Sanitizer

## منقح بيانات معاينات صفحة الهبوط

Owner:

المالك:

`Reports Module` / موديول التقارير with `Audit / Observability Module` / موديول التدقيق والمراقبة.

Purpose:

الهدف:

Prepare safe chart screenshots and sample datasets for the landing page.

تجهيز لقطات شارتات وبيانات عينة آمنة لصفحة الهبوط.

Allowed Input Types:

أنواع المدخلات المسموحة:

- `demo_sample` / عينة تجريبية.
- `anonymized_real_output` / مخرج حقيقي مخفي الهوية.
- `generated_product_mock` / نموذج منتج مولد.

Sanitization Steps:

خطوات التنقيح:

1. Remove user identifiers / إزالة معرفات المستخدم.
2. Remove organization identifiers / إزالة معرفات المنظمة.
3. Remove exact coordinates / إزالة الإحداثيات الدقيقة.
4. Remove supplier names and private documents / إزالة أسماء الموردين والمستندات الخاصة.
5. Replace project names with neutral examples / استبدال أسماء المشاريع بأمثلة محايدة.
6. Mark preview type visibly or in metadata / وسم نوع المعاينة ظاهرًا أو في Metadata.
7. Audit approval before publishing / تسجيل الموافقة قبل النشر.

Forbidden:

الممنوع:

- Guaranteed revenue claims / ادعاءات ضمان الإيراد.
- Guaranteed approval claims / ادعاءات ضمان الموافقة.
- Real private user data / بيانات مستخدم حقيقية خاصة.
- Unlabeled fake production output / مخرج إنتاجي وهمي بلا وسم.

Output:

المخرج:

- `landing.preview.asset.v1` / أصل معاينة لصفحة الهبوط.

Required Tests:

الاختبارات المطلوبة:

| Test ID | Arabic | Expected |
| --- | --- | --- |
| `LAND-ALG-T01` | لقطة تحتوي بريد أو هاتف | Reject |
| `LAND-ALG-T02` | لقطة بلا وسم نوع المعاينة | Reject |
| `LAND-ALG-T03` | شارت يدعي ضمان الربح | Reject |
| `LAND-ALG-T04` | لقطة من تقرير حقيقي بلا إخفاء هوية | Reject |

## Required Chart Test Matrix

## مصفوفة اختبار الشارتات المطلوبة

| Test ID | Arabic | Expected |
| --- | --- | --- |
| `CHART-T01` | شارت بلا موديول مالك | Reject |
| `CHART-T02` | شارت يستخدم رقمًا من AI | Reject |
| `CHART-T03` | شارت سوق بلا مصدر | Reject |
| `CHART-T04` | شارت مالي بلا خريطة معادلة | Reject |
| `CHART-T05` | شارت خريطة بلا GPS أو Pin | Reject |
| `CHART-T06` | شارت MCMC بلا seed | Reject |
| `CHART-T07` | نقص بيانات | Show insufficient_data |
| `CHART-T08` | مستخدم بلا صلاحية | permission_denied |
| `CHART-T09` | Tooltip بلا مصدر عند الحاجة | Reject |
| `CHART-T10` | RTL labels missing | Reject UI acceptance |
| `LAND-T01` | لقطة هبوط تكشف بيانات خاصة | Reject |
| `LAND-T02` | لقطة هبوط بلا وسم preview type | Reject |
