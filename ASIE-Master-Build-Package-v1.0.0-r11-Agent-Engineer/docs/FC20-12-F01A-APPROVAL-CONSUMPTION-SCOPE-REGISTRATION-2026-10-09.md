# تسجيل نطاق إصلاح استهلاك F-01A دون استئناف — 2026-10-09

## 1. الغرض وحدود السلطة

إعداد انتقال حاكم صغير بعد ملحق #193 المدموج. طلب المالك «التالي» يجيز إعداد هذا الطلب فقط؛ لا ينقل موافقة الرأس السابق إلى هذا الرأس، ولا يجيز دمج هذا الطلب أو استئناف #189.
ملحق التصميم المعتمد: [#193](https://github.com/alphasigma13579-lang/ASIE/pull/193)، merge `23ea4b48e4c2f4c94e4f54c33bb0310bd6e0adc3`. نموذج الإيصال أدناه ليس توقيعًا مشفرًا ولا مراجعة مستقلة.

## 2. الدلتا المقترحة

- ثبت توقف مراجعة الاستهلاك ونقص نطاق اختبارها كـ STOP_CHECKPOINT جديد.
- أضف SCOPE_EXTENSION وملف `tests/test_intelligence_consumption.py` وحده إلى قائمة التطبيق، من ثمانية إلى تسعة مسارات.
- أطفئ علم التنفيذ فقط؛ أبقِ IN_PROGRESS وموضع F01A محجوزًا ومحسوبًا.
- احفظ كل الأحداث والقرارات القديمة دون تعديل، بما فيها RESUME التاريخي.
- لا تضف RESUME جديدًا، ولا تعدّل subject الأصلي أو start_decision أو خطة التطبيق المجمدة تاريخيًا.
- تحفظ سياسة C02 المعتمدة في ملحق #193 دون تنفيذها هنا: إثبات منشأ من سجلات التطبيق ومعاملة SQLite نفسها، لا مخزن أو جدول جديد؛ لا شهادة رجعية لبيانات legacy.
- يبقى #192 Draft مستقلًا وغير نافذ؛ لا يضاف اختبار عزل المستأجرين المقترح فيه تلقائيًا.

النطاق المغلق لهذا الطلب الحاكم، وليس نطاق التطبيق:
- `FOUNDATION-COMPLETE-20.json`
- `ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/tests/test_foundation_complete_20_program.py`
- `ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/docs/FOUNDATION-COMPLETE-20-CORE-INTELLIGENCE-COMPLETION-PROGRAM-2026-07-29.md`
- `ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/docs/EKB/FOUNDATION-COMPLETE-20-PACKAGE-INDEX.md`
- `ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/docs/ASIE-BETA-EXECUTION-MASTER-PLAN-2026-09-09.md`
- `ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/docs/FC20-12-F01A-DEFENSIVE-ENABLING-REGISTRATION-PROPOSAL-2026-10-01.md`
- `ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/docs/FC20-12-F01A-APPROVAL-CONSUMPTION-SCOPE-REGISTRATION-2026-10-09.md`

لا يتغير backend/src أو اختبار الاستهلاك نفسه في هذا الطلب. حارس الحوكمة أداة تحقق توثيقي وليس تنفيذًا للمسارات الخادمية.

## 3. اختبارات القبول المحددة

| الرمز | الإثبات المطلوب على رأس هذا الطلب |
|---|---|
| CS-01 | ستة أحداث بالترتيب، حالة متوقفة، تسعة مسارات دقيقة، موضع واحد محفوظ |
| CS-02 | رفض نقص/تحريف أوراق الأدلة والقرار والوقت والرؤوس والبصمات والحقول الزائدة |
| CS-03 | رفض إعادة ترتيب/حذف/تكرار التاريخ، وإعادة استخدام سجل قديم كصلاحية حالية |
| CS-04 | رفض تشغيل/إغلاق/توسعة ضمنية، wildcard، ملفات مجمدة أو ملف #192 |
| CS-05 | عكس الدلتا يعيد كامل blob manifest الأساسي؛ أي تغيير غير متعلق مرفوض |
| CS-06 | بقاء اختبارات التاريخ ومعايير routing/dependencies/frozen/release كما هي |
| CS-07 | تطابق الإسقاطات الأربعة مع الانتقال، والتحقق من بقائها append-only |
| CS-08 | ثبات ملحق #193، وفصل إعداد التسجيل عن موافقة الدمج والاستئناف، ومراجعات الرأس الحالي |

الفحوص تنفذ في GitHub الرسمي فقط. لا تكرار اختبارات تطبيق ناجحة بلا دلتا تطبيق؛ CI النهائي للمشروع بوابة تحقق لهذا الطلب، وليس تصريح نشر أو إثبات C01/C02/C03 أو نجاح رحلة المستخدم.

## 4. المخاطر والتوقف الآمن

الخطر المباشر منخفض وتشغيليًا لا خدمات تتغير، لكن خطأ الحارس قد يحرر صلاحية تنفيذ ضمنية؛ لذلك oracle مستقل، ومقارنة كاملة، ومراجعات exact-head لا مضاهاة انتقائية.
أول أربعة أحداث تبقى تاريخًا. فحص التوافق يعكس الدلتا المثبتة قبل الاختبارات التاريخية؛ لا يقبلها كحالة المصدر الحالية.
لا نعلن أن C01/C02/C03 أصلحت، أو أن T08 اجتاز، أو أن التطبيق/البيتا جاهز.
التسليم الآمن: PR مرشح ومراجعاته وأدلته للمالك؛ لا دمج تلقائي. بعد دمج منفصل، يبقى التنفيذ متوقفًا إلى قرار استئناف جديد وانتقال مراجع. بعدها فقط يمكن تعديل C01/C02/C03 واختبارات #189 ضمن النطاق المسجل.
هذا يتقدم بخطة بيتا المالك والإدارة المستقلة، ولا يحل محلها أو يسقط حدودها أو أعمالها المؤجلة.

## 5. الإسقاط المتحقق منه

<!-- F01A-CONSUMPTION-SCOPE-REGISTRATION-2026-10-09 -->
### تسجيل نطاق استهلاك F-01A دون استئناف — مرشح 2026-10-09

الحالة: `GOVERNANCE_TRANSITION_CANDIDATE / REVIEW_REQUIRED / NOT_EFFECTIVE_UNTIL_SEPARATE_OWNER_MERGE_APPROVAL`.
هذا إسقاط مرشح لا يعيد كتابة السجلات التاريخية. لا يصبح التسجيل نافذًا إلا بعد مراجعة الرأس نفسه وموافقة دمج منفصلة من المالك؛ ويظل الاستئناف قرارًا وانتقالًا منفصلين لاحقًا.

الحالة المقترحة: `f01a_defensive_ingress IN_PROGRESS/false`، `execution_authorized=false`، `active_target محفوظ ومحسوب` دون تحرير موضع التنفيذ أو شغل موضع ثانٍ. يبقى `routing_repair REGISTERED_BLOCKED/false`، وضوابطه `PENDING`، و`FC20-05 held`.
التاريخ: `START → STOP_CHECKPOINT → SCOPE_EXTENSION → RESUME → STOP_CHECKPOINT → SCOPE_EXTENSION`؛ أول أربعة أحداث محفوظة كما هي، لا RESUME جديد.

إيصال إعداد الطلب: `DECISION-FC20-12-F01A-CONSUMPTION-REGISTRATION-PREPARATION-2026-10-09`، https://github.com/alphasigma13579-lang/ASIE/pull/193#issuecomment-6080941469، عند `2026-10-09T12:31:30Z`؛ أثره `PREPARE_GOVERNANCE_PR_ONLY_NO_MERGE_NO_RESUME` فقط، وليس موافقة دمج أو استئناف أو توقيع هوية مستقل.
المرجع: main `23ea4b48e4c2f4c94e4f54c33bb0310bd6e0adc3`، manifest blob `ac40d84cb7bfca4ea025cf754483a0561037e994`؛ #189 `6211418ca295e710be7f686bd1592bb30649f1d6` محفوظ دون تعديل. ملحق #193 مراجع على `fa806ce545a3432739167fbe042a731930b15f9e` وبصمته `042f89fce3adf1509ec0e6ee3e377c921820fde6`. #192 مستقل غير مدموج ولا ينفذ منه شيء هنا.

الزيادة الوحيدة: `tests/test_intelligence_consumption.py`؛ النطاق المقترح تسعة مسارات:
- `backend/asie_local_api.py`
- `backend/repository.py`
- `backend/intelligence_prerun_service.py`
- `tests/test_repository_intelligence.py`
- `tests/test_intelligence_prerun_service.py`
- `tests/test_intelligence_context_ingress_api.py`
- `docs/FC20-12-F01-TRUSTED-CONTEXT-INGRESS-REPAIR-PLAN-2026-10-01.md`
- `tests/test_live_location_api.py`
- `tests/test_intelligence_consumption.py`

الحارس يقبل هذه الحالة المرشحة وحدها من oracle مستقل مثبت بالإيصال؛ ويثبت عكس الدلتا كامل baseline، لا حقولًا منتقاة. فحوص `CS-01–CS-08` ومراجعات exact-head مطلوبة، دون ادعاء نجاح مسبق. التاريخ السابق اختبارات توافق منفصلة وليس fallback للصلاحية الحالية.
شرط العودة: `NEW_OWNER_DECISION_AND_REVIEWED_EXACT_HEAD_GOVERNANCE_TRANSITION`. لا يستأنف التطبيق بهذه الوثيقة أو بمجرد نجاح CI أو دمج التسجيل. `delivery_evidence=null`، `closure_effect=NONE`، `DARK_OFFLINE`، `network/provider/deployment=false`؛ حزم البرنامج وبواباته لا تعلن مكتملة.
`T08 OPEN`: بعض الواجهات غير جاهزة/غير مربوطة، واختبار تعافي العميل باقٍ في خطة تجربة العميل.
مسار بيتا المالك والإدارة المستقلة محفوظ: #166 `2dccc2c45c2b1967e277edf6db6a681a04b2654a`؛ #167 `435777008e01bafc73ab3bca86cc8945e311b610`. لا نشر أو أسرار أو خدمات أو دعوات أو ترحيل أو تعديل Finance/Snapshot/AAS/Decision Council.

