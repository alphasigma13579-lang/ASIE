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

<!-- F01A-REVIEW-IDENTITY-SCOPE-REGISTRATION-2026-10-11 -->
### تسجيل نطاق تحقق السياق عند المراجعة والاعتماد دون استئناف — مرشح 2026-10-11

الحالة: `GOVERNANCE_TRANSITION_CANDIDATE / REVIEW_REQUIRED / NOT_EFFECTIVE_UNTIL_SEPARATE_OWNER_MERGE_APPROVAL`. هذا إسقاط مشتق؛ المصدر النافذ هو manifest المدمج. إيصال قرار إعداد التسجيل [ملخص موافقة المالك](https://github.com/alphasigma13579-lang/ASIE/pull/201#issuecomment-6113714644) مثبت؛ أذن المالك بنشر هذا الملخص والملفات السبعة كمسودة عند `2026-10-11T20:59:57Z` بعد الفحوص النهائية. الإعداد والنشر لا يجعلان هذا الانتقال نافذًا؛ موافقة دمجه منفصلة.
مصدر الإسقاط `docs/FC20-12-F01A-APPROVAL-CONSUMPTION-SCOPE-REGISTRATION-2026-10-09.md`؛ prefix blob `fb96b90af891332bc93ce01502d94383c443beb2` محفوظ بايتًا. baseline بعد دمج #201 هو `abbdea3913630a7e940c454c46919f88c673aa0f` وmanifest blob `d76e7b0f6d18a701985469664c0cb6c1f757c869`؛ التصميم المراجع #201 عند `ae4b69ee3e56930ce1af944a2577e79e5ab44681` وblob `7aa270286535f831a8eac25170ee495043b40bf5`. كل ما سبق هذا القسم تاريخ محفوظ، بما فيه أوصاف الفهرس القديمة.

قرار المالك عند `2026-10-11T20:44:24Z` أجاز دمج التصميم إذا سمحت البوابات ثم إعداد تسجيل النطاق المحدد للمراجعة؛ أثره `PREPARE_GOVERNANCE_PR_ONLY_NO_MERGE_NO_RESUME`. الإيصال تلخيص المساعد لموافقة المالك، وليس توقيع هوية مستقلًا. قرار الإعداد لا يمثل إذن دمج التسجيل أو تنفيذ الإصلاح أو الاستئناف؛ إذن النشر اللاحق منفصل ومحدد أعلاه. موافقة الإعداد الأقدم في #189 لا تستبدل هذا القرار المرتبط بالتصميم المقبول.

الدلتا المقترحة الوحيدة: `execution_authorized=true → false` حرفيًا؛ إلحاق STOP_CHECKPOINT حادي عشر وSCOPE_EXTENSION ثاني عشر عند `2026-10-11T20:51:05Z`. `f01a_defensive_ingress IN_PROGRESS/false` في المرشح، دون RESUME أو START أو DELIVERED. تحفظ الأحداث العشرة كاملة، ويثبت موضوع القرار نسخة السجل المرجعي والـRESUME العاشر كاملة. `active_target محفوظ ومحسوب` في `FC20-12/f01a_defensive_ingress` و`max_active_executions=1` و`FC20-05 held`.

المسارات التسعة ثابتة بالترتيب؛ `added_paths=[]`، ولا `added_schema_operations` في الحدث الجديد:
- `backend/asie_local_api.py`
- `backend/repository.py`
- `backend/intelligence_prerun_service.py`
- `tests/test_repository_intelligence.py`
- `tests/test_intelligence_prerun_service.py`
- `tests/test_intelligence_context_ingress_api.py`
- `docs/FC20-12-F01-TRUSTED-CONTEXT-INGRESS-REPAIR-PLAN-2026-10-01.md`
- `tests/test_live_location_api.py`
- `tests/test_intelligence_consumption.py`

تبقى عملية `allowed_schema_operations` الوحيدة كما هي: `CREATE_INDEX_IF_NOT_EXISTS` / `idx_security_audit_origin_proof` على `security_audit_events(action, target_type, target_id, organization_id)`؛ `unique=false` حرفيًا. هذه التوسعة دلالية، ولا تعدل الفهرس أو SQL أو schema أو بيانات أو إثبات منشأ أو query أو API.

موضوع الإصلاح المغلق في `owner_scope_decision.subject.repair_scope`:
- `purpose=REVIEW_APPROVAL_STORED_CONTEXT_INTEGRITY_ONLY`
- `implementation_paths=[backend/repository.py, tests/test_repository_intelligence.py]`
- `boundary=EXISTING_TRANSACTIONAL_INTELLIGENCE_REVIEW_CONTEXT`
- `validation=REUSE_CONSUMPTION_SHAPE_TYPED_ROW_EQUALITY_NATIVE_LIFECYCLE_HASH`
- `historical_read_and_origin_proof_policy=UNCHANGED`
- `additional_schema_operations=[]`
- `database_and_data_scope=DISPOSABLE_TEMPORARY_DATABASES_SYNTHETIC_DATA_ONLY`

مصدر التطبيق هو Draft #189 غير المدمج عند `3cf88c7bae98a48c5cd950df978678f452501980`، وليس كود main أو فرع الحوكمة. التحقق الصارم والحد المعاملاتي المشار إليهما موجودان في #189 فقط؛ يستمر الإصلاح بعد تفويضه على ذلك الفرع أو خلفه المتحقق مع إدخال main الحاكم بأمان. غياب التحقق أو تغير دلالته يوقف العمل ويعيد التصميم؛ لا يعاد بناؤه في main ولا ينشأ مصدر/مسار بديل. الفهرس منفذ ومختبر اصطناعيًا في #189؛ فجوة الهوية مثبتة قبله أيضًا، ولم يثبت تجاوز عزل العملاء أو وصول إلى مزود.

الإصلاح المستقبلي يعيد استعمال تحقق الصف نفسه داخل اتصال المعاملة نفسه بعد التفويض والعزل وقبل إدراج المراجعة/الإيصال. القراءة التاريخية العادية وسياسة إثبات المنشأ وبصمات ونطاق وشروط ReviewOverlay/ApprovalReceipt تبقى كما هي. لا proof مطلوب جديد لسياق أصلي صالح قديم؛ لا إصلاح صامت أو backfill أو حذف أو إعادة ختم. تبقى أخطاء المراجعة `context_not_review_eligible` واستهلاك السياق `context_integrity_invalid`، وعقد HTTP المراجعة/الاعتماد invalid/400 دون نقل 409 من narrative؛ لا ابتلاع أخطاء التخزين.

اختبارات إصلاح التطبيق في §5 من التصميم `NOT_IMPLEMENTED / NOT_RUN`: مصفوفتان مستقلتان لحفظ المراجعة والاعتماد، JSON/شكل/نوع/هوية/مادة/lifecycle غير صالح، bool مقابل int، rollback وعدم إنشاء overlay/receipt، العزل قبل الوصول، توافق السياقات الأصلية الصحيحة بلا origin proof جديد، واستعمال الاتصال المعاملاتي نفسه دون getter عام. لا تنقل نتائج #189 السابقة لتزعم نجاح الإصلاح.

حارس التسجيل RISG-01–RISG-08 مستقل ومغلق: يثبت القرار وموضوعه والتصميم والأنواع الحرفية وكل نسخة للعملية؛ يرفض القرارات السابقة أو true أو schema/مسارات/حقول إضافية. عكس الحدثين والعلم يعيد manifest الكامل إلى `d76e7b0f6d18a701985469664c0cb6c1f757c869` ثم سلسلة IRG→ISG→CRG→CS→RG→SG. أختام raw bytes لكل prefix والقسم النهائي خاصة بمساره؛ لا اقتطاع غير متحقق أو fallback حالي إلى حالة تاريخية. اختبارات التاريخ والبنية السابقة لنشر الإيصال لا تثبت وحدها القبول النهائي؛ يلزم تشغيل الحارس الكامل على الرأس ذي الإيصال المثبت.

تبقى `routing_repair REGISTERED_BLOCKED/false` وضوابطه التسعة `PENDING` وFC20-12 `ACR_REQUIRED` واعتمادياته والتجميد؛ `release BLOCK` و`DARK_OFFLINE` و`network/provider/deployment=false` و`delivery_evidence=null` و`closure_effect=NONE` و`T08 OPEN`. معايير startup/maintenance/recovery `UNKNOWN_NOT_APPROVED`؛ لا قاعدة مالك/live أو قبول production placement أو deployment أو دمج #189. لا F01B أو واجهة تعافٍ أو Finance/Snapshot/AAS/Decision Council.

التوقف الآمن: إذن نشر الإيصال والتسجيل مستوفى؛ تبقى اختبارات الرأس النهائي ومراجعته ثم موافقة دمج التسجيل منفصلة. بعد نفاذ التسجيل يلزم قرار RESUME جديد مقيد بموضوع الإصلاح وانتقال مستقل مراجع ومصرح بدمجه قبل الكود. لا يحمل RESUME الفهرس السابق أو إذن الإعداد هذا التفويض. لا ينفذ التسجيل إصلاح التطبيق أو الفهرس أو SQL.

<!-- F01A-REVIEW-IDENTITY-CONDITIONAL-RESUME-2026-10-12 -->
### استئناف مشروط لإصلاح سلامة السياق عند حفظ المراجعة والاعتماد — مرشح 2026-10-12

الحالة: `GOVERNANCE_TRANSITION_CANDIDATE / REVIEW_REQUIRED / NOT_EFFECTIVE_UNTIL_SEPARATE_OWNER_MERGE_APPROVAL`. أذن المالك في `2026-10-12T08:47:04Z` بدمج #202 ثم تجهيز طلب الاستئناف فقط. ثم وافق بقرار جديد عند `2026-10-12T09:04:31Z` على التطوير والاختبار المشروطين المحددين أدناه، وعلى نشر ملخص القرار وملفات الانتقال السبعة كمسودة بعد الفحوص. [إيصال القرار](https://github.com/alphasigma13579-lang/ASIE/pull/202#issuecomment-6121127349) تلخيص المساعد لموافقة المالك، وليس توقيع هوية مستقلًا. أثر القرار `F01A_DEFENSIVE_RESUME_ONLY`، وشرط النفاذ `REVIEWED_GOVERNANCE_TRANSITION_MERGED_AFTER_SEPARATE_OWNER_MERGE_APPROVAL`. لا يصبح الإعداد أو نشر هذا المرشح إذن دمج أو تنفيذ قبل نفاذ الاستئناف.

مصدر الإسقاط `docs/FC20-12-F01A-APPROVAL-CONSUMPTION-SCOPE-REGISTRATION-2026-10-09.md`؛ prefix blob `6234c26c218744d6796357828f719db4802f1d10` محفوظ بايتًا. مصدر الحالة النافذة manifest على main `fcfd9222e1b47b9d95b96b589ec204b91bae8378` بعد دمج #202 عند الرأس `5af26b37986c75a5f8e014d6d69c449f93bca61e`، blob `ef142b9a2c2001e0bea4d6068b0f36d5c44c5a4c`: اثنا عشر حدثًا و`execution_authorized=false`. التصميم المقبول #201 عند `ae4b69ee3e56930ce1af944a2577e79e5ab44681` وblob `7aa270286535f831a8eac25170ee495043b40bf5` يثبت هذا الانتقال في §6–6.1؛ لا حاجة إلى طلب تصميم مستقل إضافي.

الدلتا المقترحة فقط: `execution_authorized=false → true` حرفيًا، وإلحاق RESUME ثالث عشر عند `2026-10-12T09:05:19Z`. `f01a_defensive_ingress IN_PROGRESS/true` في المرشح غير النافذ، لا في main. جميع الأحداث الاثني عشر محفوظة؛ ينسخ الحدث وموضوع القرار STOP11 وSCOPE12 كاملين، ويحفظ repair_scope المثبت والقوائم والعملية. لا START أو DELIVERED أو تعديل تاريخ. `active_target محفوظ ومحسوب` في `FC20-12/f01a_defensive_ingress` و`max_active_executions=1` و`FC20-05 held`.

المسارات التسعة لا تتغير بالترتيب:
- `backend/asie_local_api.py`
- `backend/repository.py`
- `backend/intelligence_prerun_service.py`
- `tests/test_repository_intelligence.py`
- `tests/test_intelligence_prerun_service.py`
- `tests/test_intelligence_context_ingress_api.py`
- `docs/FC20-12-F01-TRUSTED-CONTEXT-INGRESS-REPAIR-PLAN-2026-10-01.md`
- `tests/test_live_location_api.py`
- `tests/test_intelligence_consumption.py`

تبقى `allowed_schema_operations` عملية واحدة byte-exact: `CREATE_INDEX_IF_NOT_EXISTS` / `idx_security_audit_origin_proof` على `security_audit_events(action, target_type, target_id, organization_id)`؛ `unique=false`. حفظ هذه العملية التاريخية لا يجعلها نشاطًا مفوضًا جديدًا في الاستئناف المقترح؛ لا تعديل index أو schema أو query أو proof أو API.

موضوع القرار التنفيذي المقترح مغلق ومقيد: `DEVELOP_REGISTERED_REVIEW_APPROVAL_CONTEXT_INTEGRITY` و`TEST_REGISTERED_REVIEW_APPROVAL_CONTEXT_INTEGRITY` فقط، في `backend/repository.py` و`tests/test_repository_intelligence.py`. ينسخ `repair_scope` نفسه: `REVIEW_APPROVAL_STORED_CONTEXT_INTEGRITY_ONLY`، حد `EXISTING_TRANSACTIONAL_INTELLIGENCE_REVIEW_CONTEXT`، تحقق `REUSE_CONSUMPTION_SHAPE_TYPED_ROW_EQUALITY_NATIVE_LIFECYCLE_HASH`، قراءة تاريخية وسياسة origin proof `UNCHANGED`، و`additional_schema_operations=[]`. لا يعاد استعمال أنشطة استئناف الفهرس أو إيصال إعداد التسجيل بوصفهما هذا القرار.

العمل بعد التفويض فقط على `DISPOSABLE_TEMPORARY_DATABASES_ONLY` و`SYNTHETIC_DATA_ONLY`. `live_database_authorized=false` و`owner_database_authorized=false` و`production_placement_accepted=false` و`deployment_authorized=false` و`application_pr_merge_authorized=false`؛ `query_and_proof_semantics=UNCHANGED`. `startup_criteria_status=UNKNOWN_NOT_APPROVED` و`maintenance_recovery_acceptance=UNKNOWN_NOT_APPROVED`؛ لا اعتماد SLO أو موضع تشغيل فعلي ضمن هذا الانتقال.

خط التطبيق هو Draft #189 غير المدمج عند `3cf88c7bae98a48c5cd950df978678f452501980` أو خلفه المتحقق، مع إدخال main الحاكم بأمان. التحقق الموجود والحد المعاملاتي مصدرهما ذلك الفرع، لا main أو فرع الحوكمة؛ إعادة التحقق من وجودهما ودلالتهما شرط قبل الكود. غيابهما أو تغير دلالتهما يعيد قرار التصميم، ولا يعاد بناء تنفيذ بديل على main. الإصلاح يشارك تحقق الصف نفسه في الاتصال المعاملاتي نفسه بعد التفويض والعزل، قبل إدراج المراجعة/الإيصال؛ لا getter بوصلة جديدة ولا resolver أو مصدر ثقة آخر.

تظل القراءة التاريخية المصرح بها والسياقات الأصلية السليمة بلا origin proof جديد صالحة بحسب عقدها؛ لا proof أو backfill أو ختم أو حذف جديد. رفض المراجعة `context_not_review_eligible` والاستهلاك `context_integrity_invalid` وعقد HTTP المراجعة invalid/400 محفوظة دون ابتلاع أخطاء التخزين. اختبارات إصلاح التطبيق في §5 `NOT_IMPLEMENTED / NOT_RUN`: رفض مستقل عند كل كتابة، تلف JSON والشكل والأنواع والهوية والمادة وlifecycle، rollback والعزل والنجاح التاريخي واختبار استعمال الاتصال نفسه؛ لا نقل لنتائج #189 السابقة إلى إصلاح لم ينفذ.

حارس RIRG-01–RIRG-08 يثبت القرار الحقيقي ووقته ونطاقه وكل نسخة تاريخية والأنواع الحرفية؛ لا يمر placeholder أو إعداد أو قرار فهرس سابق. عكس العلم والحدث الثالث عشر يعيد manifest الكامل إلى `ef142b9a2c2001e0bea4d6068b0f36d5c44c5a4c`، ثم RISG→IRG→ISG→CRG→CS→RG→SG دون إضعاف. أختام raw bytes الخمسة مستقلة وخاصة بالمسار؛ الاختبارات التاريخية تمر بعكس متحقق قبل تحويرها، ولا تستخدم فشل القبول المبكر كبديل للـoracle القديم. نتائج اختبارات البنية قبل صدور القرار لا تعوض الفحوص الكاملة على الرأس النهائي ذي الإيصال المثبت.

تبقى `routing_repair REGISTERED_BLOCKED/false` وضوابطه التسعة `PENDING` وFC20-12 `ACR_REQUIRED` واعتمادياته والتجميد؛ `release BLOCK` و`DARK_OFFLINE` و`network/provider/deployment=false` و`delivery_evidence=null` و`closure_effect=NONE` و`T08 OPEN`. لا F01B أو واجهة تعافٍ أو Finance/Snapshot/AAS/Decision Council أو نشر أو قاعدة مالك أو دمج #189.

التوقف الآمن: قرار المالك المشروط وإذن توثيقه ونشر الانتقال مستوفيان بالإيصال المثبت؛ تبقى اختبارات الرأس النهائي ومراجعته ثم موافقة دمجه المنفصلة. لا true نافذة قبل الدمج المصرح، ولا يبدأ إصلاح التطبيق بمجرد إعداد أو نشر هذا المرشح. لا يتضمن القرار قاعدة تشغيل فعلية أو نشرًا أو دمج #189 أو معيار قبول startup مخترعًا.

<!-- F01A-KEY-FINGERPRINT-SCOPE-REGISTRATION-2026-10-12 -->
### تسجيل نطاق اتساق المفتاح والبصمة دون استئناف — مرشح 2026-10-12

الحالة: `REVIEW_REQUIRED / NOT_EFFECTIVE`. هذا إسقاط مشتق لمرشح التسجيل؛ المصدر النافذ هو manifest المدمج، ولا يتغير بإعداد المرشح أو نشر مسودته. [إيصال قرار المالك](https://github.com/alphasigma13579-lang/ASIE/pull/204#issuecomment-6128022293) نقل تقني بواسطة المساعد، وليس توقيع هوية مستقلًا. أجاز القرار عند `2026-10-12T16:06:58Z` دمج التصميم #204 بالنسخة المحددة ثم تجهيز تسجيل نطاقه ونشره كمسودة؛ أثره `PREPARE_AND_PUBLISH_GOVERNANCE_DRAFT_ONLY_NO_MERGE_NO_RESUME`.

مصدر هذا الإسقاط `docs/FC20-12-F01A-APPROVAL-CONSUMPTION-SCOPE-REGISTRATION-2026-10-09.md`؛ prefix blob `0e4db455dad290f7a1b47a0f860b27ba5d076c0d` محفوظ بايتًا. baseline بعد دمج #204 هو `3d95c5443ef18b59bf42132f3df67c6c12d00bc4` وmanifest blob `76b6d5b5892cf3a839f3fde95c04ff7ee366923f`. التصميم المقبول [#204](https://github.com/alphasigma13579-lang/ASIE/blob/8d512f0123cf81332de306c9b1b60ee12defa906/ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/docs/FC20-12-F01A-KEY-FINGERPRINT-SCOPE-PROPOSAL-2026-10-12.md) عند `8d512f0123cf81332de306c9b1b60ee12defa906` وblob `c932029f3c64ba0473596947e42ae1bdc1fcd51f`. كل ما سبق هذا القسم تاريخ محفوظ. لا تستمد سلطة من وصف تاريخي أو نجاح اختبارات مرشح غير مدمج.

الدلتا المقترحة الوحيدة: `execution_authorized=true → false` حرفيًا، وإلحاق STOP_CHECKPOINT14 وSCOPE_EXTENSION15 عند `2026-10-12T16:08:54Z`. تبقى `f01a_defensive_ingress IN_PROGRESS/false` في المرشح دون RESUME أو START أو DELIVERED؛ تحفظ الأحداث الثلاثة عشر كاملة، ويثبت موضوع القرار نسخة السجل السابق وRESUME13 كاملين. `active_target محفوظ ومحسوب` في `FC20-12/f01a_defensive_ingress` و`max_active_executions=1` و`FC20-05 held`.

المسارات التسعة ثابتة بالترتيب؛ `added_paths=[]`، ولا `added_schema_operations` في الحدث الجديد:
- `backend/asie_local_api.py`
- `backend/repository.py`
- `backend/intelligence_prerun_service.py`
- `tests/test_repository_intelligence.py`
- `tests/test_intelligence_prerun_service.py`
- `tests/test_intelligence_context_ingress_api.py`
- `docs/FC20-12-F01-TRUSTED-CONTEXT-INGRESS-REPAIR-PLAN-2026-10-01.md`
- `tests/test_live_location_api.py`
- `tests/test_intelligence_consumption.py`

تبقى عملية `allowed_schema_operations` الوحيدة كما هي: `CREATE_INDEX_IF_NOT_EXISTS` / `idx_security_audit_origin_proof` على `security_audit_events(action, target_type, target_id, organization_id)`؛ `unique=false` حرفيًا. لا index أو schema أو query أو proof-format جديد.

موضوع الإصلاح المغلق في `owner_scope_decision.subject.repair_scope` مطابق للتصميم المقبول:
```json
{
  "purpose": "STORED_CONTEXT_KEY_FINGERPRINT_BINDING_ONLY",
  "implementation_paths": [
    "backend/repository.py",
    "tests/test_repository_intelligence.py"
  ],
  "boundary": "EXISTING_SHARED_STORED_CONTEXT_VALIDATOR",
  "validation": "RECOMPUTE_EXISTING_FINGERPRINT_FROM_TYPED_EXACT_STORED_ORG_PROJECT_KEY",
  "affected_gates": [
    "VALIDATED_CONTEXT_CONSUMPTION_READ",
    "TRANSACTIONAL_REVIEW_SAVE",
    "TRANSACTIONAL_APPROVAL_SAVE"
  ],
  "compatibility": "REJECT_INCONSISTENT_BINDING_WITHOUT_REWRITE_OR_BACKFILL",
  "historical_read_and_origin_proof_policy": "UNCHANGED",
  "native_context_hash_and_fingerprint_function": "UNCHANGED",
  "additional_schema_operations": [],
  "database_and_data_scope": "DISPOSABLE_TEMPORARY_DATABASES_SYNTHETIC_DATA_ONLY"
}
```

مصدر التطبيق هو Draft #189 غير المدمج عند `4fcb8b47971a8ee55fa0ae95f5928bdd5722890a`، وليس كود main أو فرع التسجيل. الدالة المشتركة `_validated_stored_intelligence_context` وحد حفظ المراجعة/الاعتماد موجودان على رأس التطبيق المثبت. بعد تفويض لاحق فقط يستمر العمل على فرع #189 أو خلفه المتحقق مع إدخال main الحاكم بأمان؛ غياب التحقق أو تغير معناه يوقف العمل، ولا يعاد بناؤه في main أو يضاف مصدر أو مسار بديل.

الفحص المستقبلي يعيد حساب `idempotency_fingerprint` القائمة من قيم `organization_id/project_id/idempotency_key` المخزنة الصحيحة النوع كما هي، دون تحويل أو قص أو تطبيع Unicode أو تغيير native hash. يلزم التطابق مع payload والصف داخل التحقق المشترك القائم، بعد التفويض والعزل وفحوص الشكل/الأنواع/هوية الصف وقبل قبول النموذج. لا اتصال أو getter أو resolver جديد؛ يستعمل الصف والاتصال المعاملاتي القائمين. بوابات القراءة المتحققة للاستهلاك وحفظ المراجعة والاعتماد تتأثر، بينما القراءة التاريخية العادية لا تتغير.

التوافق المقصود: السجل القديم الأصلي الصحيح المتسق يمر دون طلب origin proof جديد؛ عدم الاتساق الذي كان مقبولًا يرفض عند البوابات المتحققة. لا rewrite أو backfill أو حذف أو إعادة ختم أو تطبيع تلقائي، ولا حذف للإيصالات القديمة. دالة استهلاك الإيصال المباشرة لا تكتسب lookup سياق جديد؛ narrative يمر بقراءة السياق المتحققة القائمة. الربط فحص اتساق وليس دليل منشأ أو حماية من تعديل DB منسق يغير المفتاح وكل نسخ البصمة. يبقى مدى وجود سجلات مالك متأثرة `UNKNOWN`؛ لم تفحص قاعدة فعلية.

أخطاء السياق تبقى `context_integrity_invalid` و`context_not_review_eligible` بحسب الحد القائم؛ narrative يستخدم 409، وحفظ review/approval يستخدم invalid/400، دون ابتلاع أعطال التخزين. تصنيف أخطاء ReviewOverlay المؤجل خارج النطاق. الفجوة قديمة أعيدت على baseline والتطبيق الحالي؛ المادة/الإسقاط لا يتغيران وreplay يفشل مغلقًا، ولم يثبت تجاوز صلاحيات أو محتوى أو إثبات. لا يزعم التسجيل إصلاحها.

اختبارات التطبيق الجديدة في §5 من التصميم `NOT_IMPLEMENTED / NOT_RUN`: strict consumption getter وحفظ review وحفظ approval مستقلة، key-only أو fingerprint-only أو نسختا بصمة خاطئتان، حقول مفقودة/أنواع خاطئة قبل الحساب، قيم Unicode/whitespace صحيحة exact، توافق legacy بلا proof، العزل قبل الوصول، عدم كتابة أثر عند الرفض، اتصال المعاملة نفسه، وreplay/CAS/C01–C03/index دون تغيير. اختبارات HTTP القائمة يعاد تشغيلها دون تعديل؛ الحاجة لمسار خارج الملفين توقف التنفيذ. نتائج التطبيق السابقة ليست دليلًا للفحص المقترح.

حارس التسجيل KBSG-01–KBSG-08 مستقل ومغلق، يثبت القرار والرابط والوقت والموضوع والتصميم والأنواع الحرفية وكل نسخ التاريخ والعملية. يرفض true أو سلطة قديمة أو نطاق/حقل/مسار/schema زائدًا. عكس الحدثين والعلم يعيد manifest الكامل إلى `76b6d5b5892cf3a839f3fde95c04ff7ee366923f` ثم سلسلة RIRG→RISG→IRG→ISG→CRG→CS→RG→SG. أختام raw bytes مستقلة لكل prefix والقسم النهائي وخاصة بمساره؛ لا fallback إلى تاريخ لإجازة المرشح الحالي. نجاح الحارس ليس قبول تطبيق أو إذن تنفيذ.

تبقى `routing_repair REGISTERED_BLOCKED/false` وضوابطه التسعة `PENDING` وFC20-12 `ACR_REQUIRED` واعتمادياته والتجميد؛ `release BLOCK` و`DARK_OFFLINE` و`network/provider/deployment=false` و`delivery_evidence=null` و`closure_effect=NONE` و`T08 OPEN`. `startup/maintenance/recovery=UNKNOWN_NOT_APPROVED`؛ لا live/owner database أو قبول production placement أو deployment أو دمج #189، ولا F01B أو تغيير Finance/Snapshot/AAS/Decision Council.

التوقف الآمن: مراجعة رأس التسجيل وفحوصه، ثم موافقة دمجه المنفصلة. بعد نفاذه يلزم قرار تنفيذ جديد يثبت هذا الفحص والرفض والتوافق والملفين، ثم RESUME16 مستقل ينسخ STOP14/SCOPE15 والنطاق والقوائم والعملية كاملة، ومراجعة واعتماد دمجه قبل الكود. الأنشطة اللاحقة محدودة بالتطوير والاختبار على temporary/synthetic فقط؛ كل آثار live/owner/production/deployment/application-merge تبقى false. لا يعاد استخدام RESUME13 أو قرار الإعداد كإذن للفحص الجديد. لا ينفذ هذا التسجيل SQL أو تعديل بيانات أو تطبيقًا.

<!-- F01A-KEY-FINGERPRINT-CONDITIONAL-RESUME-2026-10-12 -->
### استئناف مشروط لفحص اتساق المفتاح والبصمة — مرشح 2026-10-12

الحالة: `GOVERNANCE_TRANSITION_CANDIDATE / REVIEW_REQUIRED / NOT_EFFECTIVE_UNTIL_SEPARATE_OWNER_MERGE_APPROVAL`. أذن المالك عند `2026-10-12T17:37:18Z` بدمج #205 وإعداد الاستئناف فقط؛ ثم بقرار جديد عند `2026-10-12T17:52:48Z` وافق على تطوير واختبار فحص المفتاح والبصمة المحدد، بما فيه رفض السجلات القديمة غير المتسقة دون تعديل بياناتها تلقائيًا، على temporary/synthetic فقط. أجاز أيضًا نشر ملخص القرار وملفات الانتقال السبعة كمسودة. [إيصال القرار](https://github.com/alphasigma13579-lang/ASIE/pull/205#issuecomment-6129650208) نقل تقني بواسطة المساعد، وليس توقيع هوية مستقلًا. أثر القرار `F01A_DEFENSIVE_RESUME_ONLY` مشروط بـ`REVIEWED_GOVERNANCE_TRANSITION_MERGED_AFTER_SEPARATE_OWNER_MERGE_APPROVAL`. لا تصبح true نافذة أو يبدأ التطبيق بمجرد نشر المرشح.

مصدر الإسقاط `docs/FC20-12-F01A-APPROVAL-CONSUMPTION-SCOPE-REGISTRATION-2026-10-09.md`؛ prefix blob `1b7b4d836c098cf29957710b5d19747ad3d55254` محفوظ بايتًا. main بعد دمج #205 هو `c365c85aded98811558fd190f3a2079434f1a9ad` عند رأس التسجيل `c6e7f335966baa5331a9e8fbf60b8391229f9aff`، manifest blob `6c0defd45b71bd8b28dc85d109e5bc7d1d3e8628`: خمسة عشر حدثًا و`execution_authorized=false`. التصميم المقبول #204 عند `8d512f0123cf81332de306c9b1b60ee12defa906` وblob `c932029f3c64ba0473596947e42ae1bdc1fcd51f` يحدد الاستئناف في §6؛ لا طلب تصميم مستقل إضافي.

الدلتا المقترحة: `execution_authorized=false → true` حرفيًا وإلحاق RESUME16 عند `2026-10-12T17:53:43Z`. `f01a_defensive_ingress IN_PROGRESS/true` في المرشح غير النافذ فقط. الأحداث الخمسة عشر كاملة محفوظة، وSTOP14/SCOPE15 ينسخان كاملين في الحدث وموضوع القرار، مع القوائم والعملية والنطاق المسجل. لا START أو DELIVERED أو تغيير تاريخ. `active_target محفوظ ومحسوب` في `FC20-12/f01a_defensive_ingress` و`max_active_executions=1` و`FC20-05 held`.

المسارات التسعة محفوظة بالترتيب:
- `backend/asie_local_api.py`
- `backend/repository.py`
- `backend/intelligence_prerun_service.py`
- `tests/test_repository_intelligence.py`
- `tests/test_intelligence_prerun_service.py`
- `tests/test_intelligence_context_ingress_api.py`
- `docs/FC20-12-F01-TRUSTED-CONTEXT-INGRESS-REPAIR-PLAN-2026-10-01.md`
- `tests/test_live_location_api.py`
- `tests/test_intelligence_consumption.py`

تبقى عملية `allowed_schema_operations` الوحيدة byte-exact: `CREATE_INDEX_IF_NOT_EXISTS` / `idx_security_audit_origin_proof` على `security_audit_events(action, target_type, target_id, organization_id)`؛ `unique=false`. حفظ العملية لا يمنح نشاط index جديدًا؛ لا schema أو query أو proof-format أو API جديد.

موضوع القرار المقترح ينسخ نطاق التسجيل كاملًا دون إضافة أو تطبيع:
```json
{
  "purpose": "STORED_CONTEXT_KEY_FINGERPRINT_BINDING_ONLY",
  "implementation_paths": [
    "backend/repository.py",
    "tests/test_repository_intelligence.py"
  ],
  "boundary": "EXISTING_SHARED_STORED_CONTEXT_VALIDATOR",
  "validation": "RECOMPUTE_EXISTING_FINGERPRINT_FROM_TYPED_EXACT_STORED_ORG_PROJECT_KEY",
  "affected_gates": [
    "VALIDATED_CONTEXT_CONSUMPTION_READ",
    "TRANSACTIONAL_REVIEW_SAVE",
    "TRANSACTIONAL_APPROVAL_SAVE"
  ],
  "compatibility": "REJECT_INCONSISTENT_BINDING_WITHOUT_REWRITE_OR_BACKFILL",
  "historical_read_and_origin_proof_policy": "UNCHANGED",
  "native_context_hash_and_fingerprint_function": "UNCHANGED",
  "additional_schema_operations": [],
  "database_and_data_scope": "DISPOSABLE_TEMPORARY_DATABASES_SYNTHETIC_DATA_ONLY"
}
```

الأنشطة الوحيدة المقترحة `DEVELOP_REGISTERED_STORED_KEY_FINGERPRINT_BINDING` و`TEST_REGISTERED_STORED_KEY_FINGERPRINT_BINDING` في `backend/repository.py` و`tests/test_repository_intelligence.py`. على `DISPOSABLE_TEMPORARY_DATABASES_ONLY` و`SYNTHETIC_DATA_ONLY` فقط. `live_database_authorized=false` و`owner_database_authorized=false` و`production_placement_accepted=false` و`deployment_authorized=false` و`application_pr_merge_authorized=false`؛ `query_and_proof_semantics=UNCHANGED`. `startup_criteria_status=UNKNOWN_NOT_APPROVED` و`maintenance_recovery_acceptance=UNKNOWN_NOT_APPROVED`؛ لا SLO أو قبول تشغيل فعلي مفترض.

مصدر التطبيق Draft #189 غير المدمج عند `4fcb8b47971a8ee55fa0ae95f5928bdd5722890a` أو خلفه المتحقق بعد إدخال main الحاكم بأمان. التحقق المشترك `_validated_stored_intelligence_context` على هذا الفرع، لا main أو فرع الحوكمة. بعد التفويض فقط يعاد حساب `idempotency_fingerprint` القائمة من org/project/key المخزنة الصحيحة النوع كما هي، بعد الشكل/الأنواع/مساواة الصف وقبل قبول native model؛ يطابق الحساب payload والصف. لا تحويل str أو قص أو تطبيع Unicode أو تغيير native hash/function، ولا مصدر/اتصال/getter/مسار بديل. غياب التحقق أو تغير دلالته يوقف الكود ويعيد القرار.

يتغير القبول فقط عند القراءة المتحققة للاستهلاك وحفظ review/approval: السجل المتسق القديم الصحيح يظل مقبولًا دون origin proof جديد؛ عدم الاتساق يرفض دون rewrite/backfill/deletion/reseal. القراءة التاريخية العادية وإيصالاتها لا تعاد كتابتها، ودالة استهلاك الإيصال المباشرة لا تضيف lookup. فحص الاتساق لا يثبت المنشأ ولا يكتشف كل تعديل DB منسق؛ انتشار السجلات الفعلية المتأثرة UNKNOWN. أخطاء الحدود القائمة محفوظة: `context_integrity_invalid`/narrative409 و`context_not_review_eligible`/review-approval400، دون ابتلاع أعطال التخزين. تصنيف ReviewOverlay المؤجل خارج النطاق.

اختبارات التطبيق الجديدة §5 `NOT_IMPLEMENTED / NOT_RUN`: مصفوفات مستقلة للاستهلاك والمراجعة والاعتماد، key-only وبصمة واحدة أو كلتيهما، الأنواع والحقول الناقصة قبل الحساب، Unicode/whitespace exact الصحيحة، legacy بلا proof، قراءة تاريخية عادية دون تغيير، auth/scope قبل الوصول، عدم كتابة عند الرفض والاتصال المعاملاتي نفسه، replay/CAS/C01–C03/index دون تغيير. اختبارات HTTP القائمة يعاد تشغيلها دون تعديل؛ الحاجة لمسار ثالث تعيد قرار النطاق. لا تعد نتائج التطبيق السابقة دليلًا لهذا الفحص الجديد.

حارس KBRG-01–KBRG-08 مستقل مغلق: يثبت القرار الحقيقي ووقته وكل نسخ STOP14/SCOPE15 والموضوع/الأنشطة/التوافق والأنواع. لا تمر موافقة تجهيز أو نشر أو دمج التسجيل ولا RESUME13 أو أنشطة الفهرس بدل القرار الجديد. عكس RESUME16 والعلم يعيد manifest الكامل إلى `6c0defd45b71bd8b28dc85d109e5bc7d1d3e8628` ثم KBSG→RIRG→RISG→IRG→ISG→CRG→CS→RG→SG دون تخفيف. أختام raw bytes الخمسة path-specific؛ يمر التاريخ بعكس بنيوي متحقق لأغراض الاختبار فقط، ولا يجيز placeholder أو الحالية. نجاح اختبارات البنية ليس قبول استئناف.

تبقى `routing_repair REGISTERED_BLOCKED/false` وضوابطه التسعة `PENDING` وFC20-12 `ACR_REQUIRED` واعتمادياته والتجميد؛ `release BLOCK` و`DARK_OFFLINE` و`network/provider/deployment=false` و`delivery_evidence=null` و`closure_effect=NONE` و`T08 OPEN`. لا live/owner database أو production/deployment أو دمج #189 أو F01B أو Finance/Snapshot/AAS/Decision Council.

التوقف الآمن: القرار التنفيذي المشروط وإذن نشر ملخصه والانتقال مستوفيان بالإيصال المثبت؛ تبقى الفحوص الكاملة والمراجعات على الرأس النهائي ثم موافقة دمجه المنفصلة قبل الكود. true المقترحة ليست صلاحية نافذة قبل الدمج المصرح. لا يتضمن القرار قاعدة فعلية أو بيانات مالك أو قبول production/startup أو deployment أو دمج #189؛ لا تختلق معايير غير معتمدة.
