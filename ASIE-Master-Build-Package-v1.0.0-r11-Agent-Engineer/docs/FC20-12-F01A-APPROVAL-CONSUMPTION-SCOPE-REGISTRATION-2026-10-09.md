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


<!-- F01A-CONSUMPTION-CONDITIONAL-RESUME-2026-10-10 -->
### استئناف F-01A الدفاعي بعد نطاق الاستهلاك — مرشح 2026-10-10

الحالة: `GOVERNANCE_TRANSITION_CANDIDATE / REVIEW_REQUIRED / NOT_EFFECTIVE_UNTIL_SEPARATE_OWNER_MERGE_APPROVAL`. هذا إسقاط مشتق للانتقال المقترح وليس سلطة حالة موازية؛ مصدر الحالة النافذة هو `/FOUNDATION-COMPLETE-20.json` المدموج. كل بايت سابق محفوظ كتاريخ؛ المقاطع المتوقفة والقرارات القديمة لا تمنح استئنافًا جديدًا.
مصدر هذا الإسقاط: `docs/FC20-12-F01A-APPROVAL-CONSUMPTION-SCOPE-REGISTRATION-2026-10-09.md`؛ prefix blob `b6e992d4ddfcea63661a7aa2feb66f4f255b91a5` عند رأس الإعداد `c5f7f991f126ca9afdfa83c923635f8e01ef08f0`، بعد #195 الذي غيّر التصميم ومدخل EKB فقط دون السجل.

قرار المالك الجديد «استأنف»: [DECISION-FC20-12-F01A-CONSUMPTION-CONDITIONAL-RESUME-2026-10-10](https://github.com/alphasigma13579-lang/ASIE/pull/195#issuecomment-6101266369)، وقت تسجيله `2026-10-10T19:21:30Z`؛ أثره `F01A_DEFENSIVE_RESUME_ONLY`، وشرط النفاذ `REVIEWED_GOVERNANCE_TRANSITION_MERGED_AFTER_SEPARATE_OWNER_MERGE_APPROVAL`. الإيصال نقل لتوجيه المالك، لا توقيع هوية مشفرًا ولا مراجعة مستقلة. موافقة الإعداد أو النطاق أو الدمج السابقة لا تعوض هذا القرار.
[التصميم المراجع](FC20-12-F01A-CONSUMPTION-CONDITIONAL-RESUME-PROPOSAL-2026-10-10.md): commit `0bc55b0b069fe8f1c0efb19c252a53251391c23e` وblob `7b73c89d3b217beb038ad16db8d1d126cba2b060`؛ يبقى دون تعديل. baseline الاستئناف الجديد `cf45bd9ecfda815c4c2e848f69832ebf02935fb9` وmanifest blob `e8d700eed195244ed6e2236ca53df655b5ac561f`، أي الحالة المتوقفة بعد #194. الزوج التاريخي `23ea4b48e4c2f4c94e4f54c33bb0310bd6e0adc3/ac40d84cb7bfca4ea025cf754483a0561037e994` يبقى داخل checkpoint ولا يستعمل baseline لهذا RESUME. رأس التطبيق #189 `6211418ca295e710be7f686bd1592bb30649f1d6` محفوظ دون تغيير.

الدلتا الوحيدة في السجل: `execution_authorized=false → execution_authorized=true` حرفيًا، وإلحاق RESUME سابع عند `2026-10-10T19:25:17Z`؛ `f01a_defensive_ingress IN_PROGRESS/true`. التاريخ الكامل `START → STOP_CHECKPOINT → SCOPE_EXTENSION → RESUME → STOP_CHECKPOINT → SCOPE_EXTENSION → RESUME`؛ الأحداث الستة محفوظة، وcheckpoint `2026-10-09T12:31:30Z` وscope_extension نسختان كاملتان في الحدث الجديد، لا إعادة START أو تعديل القرار الأصلي.
`active_target محفوظ ومحسوب` في `FC20-12/f01a_defensive_ingress` و`max_active_executions=1`؛ `FC20-05 held`. النطاق المسجل تسعة مسارات مرتبة دون زيادة:
- `backend/asie_local_api.py`
- `backend/repository.py`
- `backend/intelligence_prerun_service.py`
- `tests/test_repository_intelligence.py`
- `tests/test_intelligence_prerun_service.py`
- `tests/test_intelligence_context_ingress_api.py`
- `docs/FC20-12-F01-TRUSTED-CONTEXT-INGRESS-REPAIR-PLAN-2026-10-01.md`
- `tests/test_live_location_api.py`
- `tests/test_intelligence_consumption.py`

الحارس يستخدم oracle مستقلًا ثابتًا من الإيصال والتصميم، لا من مدخل السجل أو fixture؛ عكس RESUME والعلم يعيد manifest كاملًا إلى blob `e8d700eed195244ed6e2236ca53df655b5ac561f` ثم سلسلة CS-05/RG-05/SG-05 الأصلية. تاريخ الوثائق مثبت byte-exact على blobs #194؛ الحد الجديد فريد وصريح والقسم الجديد مختوم لكل مسار، دون إسقاط الختم القديم أو قبول suffix أو تعليق أو نهايات أسطر مختلفة. متطلبات `CRG-01–CRG-08` تختبر الدلتا والتاريخ والقرار والموضع والعكس والحدود والعزل عن fixture والقيود؛ النتائج الفعلية على رأس PR، لا إعلان نجاح مسبق.

`routing_repair REGISTERED_BLOCKED/false` وضوابطه التسعة `PENDING`؛ FC20-12 `ACR_REQUIRED` واعتماديات FC20-08/09/11 والحزم والتجميد و`release BLOCK` محفوظة. `delivery_evidence=null` و`closure_effect=NONE` و`DARK_OFFLINE` و`network/provider/deployment=false`. فحص Freeze بعد #195: `REJECT_UNFREEZE / NO_GO` بسبب technical_limited_gate_state؛ لا يخفض أو يتجاوز هنا ولا نجاح CI إذن نشر.

C-01/C-02/C-03 وAC-01–AC-13 وT-01–T-09: `NOT_RUN_IN_THIS_TRANSITION`؛ `T08 OPEN` وبعض الواجهات غير جاهزة/غير مربوطة. C02 يبقى معاملة SQLite نفسها وسجلات security_audit_events القائمة، دون schema أو شهادة legacy رجعية أو commit متداخل. لا كود تطبيق أو Finance/Snapshot/AAS/Decision Council أو Kernel/Hearts/Bus/Socket/Module Runtime أو AIA/API registry، ولا F-01B أو مسار موازٍ أو #192 أو خدمات/أسرار/نشر/ترحيل/دعوات/Hostinger.
خطة بيتا المالك والإدارة المستقلة و#166 `2dccc2c45c2b1967e277edf6db6a681a04b2654a` ثم #167 `435777008e01bafc73ab3bca86cc8945e311b610` محفوظة. **التوقف الآمن:** PR انتقال سبعة ملفات ومراجعات رأسه، ثم موافقة دمج منفصلة؛ لا يبدأ #189 قبل نفاذه. الهدف الكامل والرحلة الحية غير مكتملين.

<!-- F01A-AUDIT-ORIGIN-INDEX-SCOPE-REGISTRATION-2026-10-11 -->
### تسجيل نطاق فهرس إثبات المنشأ فقط دون استئناف — مرشح 2026-10-11

الحالة: `GOVERNANCE_TRANSITION_CANDIDATE / REVIEW_REQUIRED / NOT_EFFECTIVE_UNTIL_SEPARATE_OWNER_MERGE_APPROVAL`. هذا إسقاط مشتق؛ مصدر الحالة النافذة `/FOUNDATION-COMPLETE-20.json` المدموج. كل بايت سابق محفوظ كتاريخ، ولا يمنح RESUME السابق إذنًا للعملية الجديدة.
مصدر الإسقاط: `docs/FC20-12-F01A-APPROVAL-CONSUMPTION-SCOPE-REGISTRATION-2026-10-09.md`؛ prefix blob `5db18dd1b704b54c455c21ec5f6d2787528ebc37` عند baseline `83afd28398c0cef9821e08c8db1162d6ec2fdfc4` بعد دمج #197. لا يغير هذا المرشح كود #189 أو SQLite.

قرار إعداد التسجيل [DECISION-FC20-12-F01A-INDEX-SCOPE-REGISTRATION-PREPARATION-2026-10-11](https://github.com/alphasigma13579-lang/ASIE/pull/197#issuecomment-6110969163) عند `2026-10-11T14:44:04Z`، أثره `PREPARE_GOVERNANCE_PR_ONLY_NO_MERGE_NO_RESUME`. الإيصال نقل المساعد لسؤال المالك وجوابه، لا توقيع هوية مستقلًا أو موافقة على دمج التسجيل. التصميم المراجع #197: commit `33ac90a47966afda4917f34162f11f5826eab565` وblob `9be7964b01ebd393724dc2adf6a559a8a1eddd64`؛ دمجه `83afd28398c0cef9821e08c8db1162d6ec2fdfc4`؛ manifest المرجعي `1cfbaf1940bfc0a1e7c276fde4a9d0a8cea05a70`. رأس التطبيق غير المدمج #189 `7df4ea3c6dfbcfb70cc219ef59622b7387052dc4`؛ الاستعلام المقصود موجود في ذلك الفرع فقط، والفهرس `NOT_IMPLEMENTED / TESTS_NOT_RUN`.

الدلتا المسجلة المقترحة: `f01a_defensive_ingress IN_PROGRESS/false` و`execution_authorized=false` حرفيًا؛ إلحاق STOP_CHECKPOINT ثامن وSCOPE_EXTENSION تاسع عند `2026-10-11T14:50:33Z` مع حفظ الأحداث السبعة كاملة. `active_target محفوظ ومحسوب` في `FC20-12/f01a_defensive_ingress`، `max_active_executions=1`، و`FC20-05 held`. لا START/RESUME/DELIVERED جديد، ولا تحرير الموضع.

`allowed_paths` التسعة ثابتة بالترتيب و`added_paths=[]`؛ استثناء العملية لا يضيف ملفًا عاشرًا:
- `backend/asie_local_api.py`
- `backend/repository.py`
- `backend/intelligence_prerun_service.py`
- `tests/test_repository_intelligence.py`
- `tests/test_intelligence_prerun_service.py`
- `tests/test_intelligence_context_ingress_api.py`
- `docs/FC20-12-F01-TRUSTED-CONTEXT-INGRESS-REPAIR-PLAN-2026-10-01.md`
- `tests/test_live_location_api.py`
- `tests/test_intelligence_consumption.py`

استثناء schema مغلق واحد في `allowed_schema_operations`، مطابق لـ`added_schema_operations` وموضوع قرار المالك: `CREATE_INDEX_IF_NOT_EXISTS`، الاسم `idx_security_audit_origin_proof`، الجدول `security_audit_events`، الأعمدة المرتبة `action, target_type, target_id, organization_id`، `unique=false` حرفيًا، التنفيذ المحتمل `backend/repository.py` والاختبارات `tests/test_repository_intelligence.py`. لا جدول/عمود أو index آخر، ولا تعديل صفوف أو proof/backfill أو استعلام/معاملة الدليل. التسجيل لا ينفذ SQL ولا يقر موضع التنفيذ.

بوابة إتاحة التصميم محفوظة وغير مستوفاة: معايير المالك لحجم البيانات والإتاحة/الصيانة/الاستعادة `UNKNOWN / NOT_APPROVED`؛ `init_schema()` متزامن عند بدء/استيراد API، ومهلة القفل القائمة 30 ثانية ليست حدًا لبناء الفهرس. يلزم دليل على بيانات اصطناعية تمثيلية قابلة للتخلص منها وبدء متزامن وفق القيود المعتمدة بحد أدنى عمليتين، وخطة معالجة فشل معتمدة، قبل قبول موضع التطبيق. لا SLO مخترع أو retry أو ترحيل/مسار بديل. عدم الملاءمة يعيد قرار التصميم إلى المالك.

حارس ISG-01–ISG-08 مستقل ومغلق: يثبت القرار والتصميم والعملية وكل نسخة لها؛ يرفض الحقول غير المعروفة وقيم truthy والمسارات الإضافية والقرارات المعاد استخدامها. العكس الكامل يزيل الحقل والحدثين ويعيد العلم true حرفيًا لإنتاج manifest blob `1cfbaf1940bfc0a1e7c276fde4a9d0a8cea05a70` ثم يحفظ سلسلة CRG→CS→RG→SG. هذا عكس تاريخي للاختبار وليس قبولًا للحالة القديمة كسلطة حالية. prefixes الإسقاطات الخمسة مختومة بايتًا مع حدود فريدة وأختام marker-to-EOF خاصة بكل مسار؛ لا استخراج صامت للتاريخ من نص غير موثوق. حارس السجل لا يثبت سلوك SQL؛ ذلك يبقى لاختبارات التطبيق بعد التفويض.

`routing_repair REGISTERED_BLOCKED/false` وضوابطه التسعة `PENDING`؛ `release BLOCK` و`DARK_OFFLINE` و`network/provider/deployment=false` و`delivery_evidence=null` و`closure_effect=NONE` والتجميد واعتماديات FC20-12 محفوظة. `T08 OPEN`؛ لا إغلاق F01A أو تفعيل F01B أو تغيير Finance/Snapshot/AAS/Decision Council أو provider/network/deployment أو قاعدة المالك.

التوقف الآمن: مراجعة رأس هذا التسجيل واختباراته، ثم موافقة دمجه منفصلة؛ بعد نفاذه يلزم قرار RESUME جديد مرتبط بالعملية نفسها وانتقال مستقل مراجع ومصرح بدمجه. لا تستبدل موافقة التصميم أو إعداد التسجيل أيًا من البوابتين، ولا يدمج هذا الطلب #189 أو ينفذ الفهرس.

<!-- F01A-INDEX-CONDITIONAL-RESUME-2026-10-11 -->
### استئناف مشروط لتطوير واختبار الفهرس المحدد فقط — مرشح 2026-10-11

الحالة: `GOVERNANCE_TRANSITION_CANDIDATE / REVIEW_REQUIRED / NOT_EFFECTIVE_UNTIL_SEPARATE_OWNER_MERGE_APPROVAL`. هذا إسقاط مشتق؛ مصدر الحالة النافذة `/FOUNDATION-COMPLETE-20.json` المدموج. كل البايتات السابقة تاريخ محفوظ؛ لا تصبح true المقترحة إذن إطلاق أو عمل على قاعدة المالك.
مصدر الإسقاط: `docs/FC20-12-F01A-APPROVAL-CONSUMPTION-SCOPE-REGISTRATION-2026-10-09.md`؛ prefix blob `391940ecbb9b6be83bd0f9e1570bdeecd3a8d4b7`، محفوظ بعد #198 ودون تغيير من #199. قاعدة فرع إعداد الانتقال `63b18a192e8eac3c66ad5440a667e6d1d9959d10` بعد دمج التصميم فقط؛ baseline الحاكم للاستئناف كما ثبته التصميم `37b96ec504d60f62bcdb5f4e69e0e5a0d8082f34` وmanifest blob `386687c230db26e46ad831bbaeaeddddecfae795`. لا يستبدل به الزوج التاريخي 83afd283/1cfbaf19 داخل checkpoint/scope.

قرار المالك [DECISION-FC20-12-F01A-INDEX-CONDITIONAL-RESUME-2026-10-11](https://github.com/alphasigma13579-lang/ASIE/pull/199#issuecomment-6111816253)، وقت الرد `2026-10-11T17:37:41Z`: «التالي» بعد سؤال النطاق المشروط وتوضيح عدم وجود مسار موازٍ. الإيصال نقل المساعد للسؤال والتوضيح والجواب؛ ليس توقيع هوية مستقلًا. الأثر `F01A_DEFENSIVE_RESUME_ONLY` وشرط النفاذ `REVIEWED_GOVERNANCE_TRANSITION_MERGED_AFTER_SEPARATE_OWNER_MERGE_APPROVAL`. لا تعوض موافقات الإعداد أو النشر أو دمج التصميم هذا الشرط أو تمنح دمج الانتقال الحالي.
التصميم المراجع #199: head `369832d4c296cacf114c1181b2a65b06a49fde49`، blob `0a87463111c78263db11ac4d3bf103c16e47f261`؛ يبقى دون تعديل. رأس التطبيق #189 `7df4ea3c6dfbcfb70cc219ef59622b7387052dc4` منفصل غير مدمج. الفهرس `NOT_IMPLEMENTED` واختباراته `NOT_RUN_IN_THIS_TRANSITION`.

دلتا manifest الوحيدة المقترحة: `execution_authorized=false → true` حرفيًا، وإلحاق RESUME عاشر عند `2026-10-11T17:43:21Z`. `f01a_defensive_ingress IN_PROGRESS/true` مقترحة ومحدودة بالقرار أدناه، لا نفاذ قبل الدمج المصرح. الأحداث التسعة السابقة وcheckpoint الثامن وscope_extension التاسع محفوظة كاملة وتنسخ في الحدث الجديد وموضوع القرار دون اختزال. لا START أو DELIVERED أو تعديل تاريخ.
`active_target محفوظ ومحسوب` في `FC20-12/f01a_defensive_ingress`، `max_active_executions=1`، `FC20-05 held`؛ المسارات التسعة والعملية المسجلة لا تتغير:
- `backend/asie_local_api.py`
- `backend/repository.py`
- `backend/intelligence_prerun_service.py`
- `tests/test_repository_intelligence.py`
- `tests/test_intelligence_prerun_service.py`
- `tests/test_intelligence_context_ingress_api.py`
- `docs/FC20-12-F01-TRUSTED-CONTEXT-INGRESS-REPAIR-PLAN-2026-10-01.md`
- `tests/test_live_location_api.py`
- `tests/test_intelligence_consumption.py`

العملية الوحيدة: `CREATE_INDEX_IF_NOT_EXISTS` / `idx_security_audit_origin_proof` على `security_audit_events(action, target_type, target_id, organization_id)`؛ `unique=false` حرفيًا، ومسارا التنفيذ/الاختبار `backend/repository.py` و`tests/test_repository_intelligence.py`. لا schema آخر أو صفوف/backfill أو proof format أو query أو تعديل ذرية/قبول الدليل. لا API أو runtime أو مخزن أو مسار موازٍ أو تجاوز Bus/Socket.

**النطاق التنفيذي المشروط المغلق:** `DEVELOP_REGISTERED_INDEX` و`TEST_REGISTERED_INDEX` فقط، في مساري العملية المحددين، على `DISPOSABLE_TEMPORARY_DATABASES_ONLY` و`SYNTHETIC_DATA_ONLY`. `live_database_authorized=false` و`owner_database_authorized=false` و`production_placement_accepted=false` و`deployment_authorized=false` و`application_pr_merge_authorized=false`؛ `query_and_proof_semantics=UNCHANGED`. هذه قيود موضوع القرار الفعلي، لا حقول سلطة جديدة على مستوى الشريحة أو مسار runtime؛ لا يكفي العلم true وحده لتفسير الإذن.

بوابة قبول موضع init_schema تبقى منفصلة وغير مستوفاة: `startup_criteria_status=UNKNOWN_NOT_APPROVED` و`maintenance_recovery_acceptance=UNKNOWN_NOT_APPROVED`. بيانات حجم تمثيلي وحدود انتظار/جاهزية وصيانة وتزامن واستعادة يقرها المالك لم تعتمد؛ لا SLO مخترع. التهيئة متزامنة عند إنشاء Repository/استيراد API، ومهلة انتظار القفل 30 ثانية ليست حد بناء index. الاختبارات المعزولة اللاحقة يمكنها جمع دليل، لكنها لا تقر معايير المالك أو التشغيل على قاعدة فعلية أو ملاءمة production. إذا أثبتت الأدلة عدم ملاءمة الموضع يعود قرار التصميم إلى المالك، دون retry أو migration أو route بديل تلقائي.

حراس `IRG-01–IRG-08`: oracle مستقل مغلق للقرار ونطاقه والعملية والأنواع الحرفية وكل نسخة متداخلة؛ يرفض التوسعة والقرارات القديمة والإعداد كإذن تنفيذ. عكس العلم والحدث العاشر يعيد manifest الكامل إلى blob `386687c230db26e46ad831bbaeaeddddecfae795`، ثم سلسلة ISG→CRG→CS→RG→SG القديمة دون تخفيف. prefixes خمسة مختومة بايتًا، وحدود terminal فريدة وأختام خاصة بكل مسار؛ تبقى التحويرات التاريخية على صور inverse متحققة قبل التحوير، لا فشل wrapper مبكر بدل oracle المقصود. هذه اختبارات حوكمة، لا أدلة index أو إطلاق.

`routing_repair REGISTERED_BLOCKED/false` وضوابطه التسعة `PENDING`؛ FC20-12 `ACR_REQUIRED` واعتمادياته والتجميد محفوظة؛ `release BLOCK` و`DARK_OFFLINE` و`network/provider/deployment=false` و`delivery_evidence=null` و`closure_effect=NONE`؛ `T08 OPEN`. لا F01B أو تعديل Finance/Snapshot/AAS/Decision Council أو دعوات/أسرار/خدمات أو تشغيل المالك. لا دمج #189.

التوقف الآمن: مراجعة هذا الرأس واختباراته ثم موافقة دمج منفصلة. قبل نفاذ الانتقال لا تطوير index أو اختبار SQL جديد؛ بعده فقط العمل المعزول المحدد، مع إبقاء قاعدة المالك وقبول startup الفعلي محجوبين حتى اعتماد معاييرهما. لا يدمج هذا الطلب نفسه ولا يخفض بوابات الإطلاق.
