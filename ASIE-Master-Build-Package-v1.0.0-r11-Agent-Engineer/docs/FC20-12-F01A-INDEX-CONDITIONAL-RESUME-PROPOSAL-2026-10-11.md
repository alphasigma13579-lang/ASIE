# F-01A — تصميم طلب الاستئناف المشروط لنطاق الفهرس فقط

## 1. الحالة وحدود الإعداد

التاريخ: 2026-10-11. الحالة **PROPOSED / REVIEW_REQUIRED / NOT_EFFECTIVE / EXECUTION_DECISION_MISSING**.

وافق المالك عند `2026-10-11T16:26:39Z` على دمج #198 بالرأس المحدد ثم **إعداد طلب الاستئناف المنفصل للمراجعة**. أثر الجزء اللاحق هو إعداد الطلب؛ ليس «استأنف الآن» ولا قرارًا يرفع `execution_authorized`. لم ينشر إيصال إعداد جديد لهذا التصميم بعد؛ لا نخترع له رابطًا أو نستعمل إيصال إعداد تسجيل النطاق كقرار استئناف.

مرشح التصميم ملفان فقط: هذه الوثيقة ورابط ملاحي في `docs/EKB/README-AR.md`. لا manifest أو حارس أو إسقاط حاكم أو كود تطبيق في فرق التصميم. أذن المالك عند `2026-10-11T16:35:31Z` بنشر ملفي التصميم كطلب مسودة مستقل فقط؛ هذه موافقة نشر وليست قرار استئناف. الاختبارات المستقبلية أدناه خطة قبول وليست نتائج منفذة.

**القرار الناقص قبل إعداد انتقال يجيز true:** قرار مالك جديد يوافق صراحةً على الاستئناف الدفاعي المشروط للعملية المحددة، بموضوع يربط خط الأساس المتوقف وcheckpoint والتوسعة ورأس التطبيق والمسارات والعملية، ثم انتقال مستقل مراجع وموافقة دمجه المنفصلة. موافقة إعداد الطلب أو دمج #198 أو RESUME تاريخي لا تعوض ذلك القرار. يبقى التصميم قابلًا للمراجعة مع بقاء هذا القرار غائبًا.

## 2. خط الأساس النافذ بعد دمج التسجيل

- [دمج #198](https://github.com/alphasigma13579-lang/ASIE/pull/198): رأس التسجيل `29bf388828bfd16142e4b7704b07ec5aab13ddcb`، main الفعلي بعد الدمج `37b96ec504d60f62bcdb5f4e69e0e5a0d8082f34`؛ tree `fc18bd4ad69dfbb48133e27bef8312077bb09d75`.
- [السجل النافذ](https://github.com/alphasigma13579-lang/ASIE/blob/37b96ec504d60f62bcdb5f4e69e0e5a0d8082f34/FOUNDATION-COMPLETE-20.json): blob `386687c230db26e46ad831bbaeaeddddecfae795`؛ F01A **IN_PROGRESS/false**. الوثيقة ليست مصدر حالة بديلًا.
- تسعة أحداث محفوظة: `START → STOP_CHECKPOINT → SCOPE_EXTENSION → RESUME → STOP_CHECKPOINT → SCOPE_EXTENSION → RESUME → STOP_CHECKPOINT → SCOPE_EXTENSION`.
- الحدثان الثامن والتاسع عند `2026-10-11T14:50:33Z`؛ baseline التاريخي داخلهما `83afd28398c0cef9821e08c8db1162d6ec2fdfc4` وmanifest blob `1cfbaf1940bfc0a1e7c276fde4a9d0a8cea05a70`. سبب التوقف `AUDIT_ORIGIN_INDEX_SCHEMA_OPERATION_OUTSIDE_REGISTERED_SCOPE`؛ أثر التوسعة `SCOPE_EXTENSION_ONLY_NO_RESUME` وشرطها `NEW_OWNER_DECISION_BOUND_TO_INDEX_OPERATION_AND_REVIEWED_EXACT_HEAD_GOVERNANCE_TRANSITION`.
- موضع واحد محفوظ ومحسوب: `FC20-12/f01a_defensive_ingress` و`max_active_executions=1`؛ `FC20-05 held`.
- `routing_repair REGISTERED_BLOCKED/false` وضوابطه التسعة `PENDING`؛ FC20-12 `ACR_REQUIRED`؛ release `BLOCK` و`DARK_OFFLINE` و`network/provider/deployment=false`؛ `delivery_evidence=null` و`closure_effect=NONE`.
- التطبيق [#189](https://github.com/alphasigma13579-lang/ASIE/pull/189) منفصل، Draft وغير مدمج عند `7df4ea3c6dfbcfb70cc219ef59622b7387052dc4`؛ لا يفترض دخوله إلى main. الفهرس **NOT_IMPLEMENTED** وT08 **OPEN**.

أدلة التسجيل لا أدلة تنفيذ الفهرس: [CI38154460460/job114514448515](https://github.com/alphasigma13579-lang/ASIE/actions/runs/38154460460/job/114514448515) على رأس #198: 3471 passed / 2 skipped / 10 warnings؛ الفحوص الخمسة عشر ناجحة. [CodeRabbit5484013887](https://github.com/alphasigma13579-lang/ASIE/pull/198#pullrequestreview-5484013887) APPROVED؛ [Copilot5483999379](https://github.com/alphasigma13579-lang/ASIE/pull/198#pullrequestreview-5483999379) COMMENTED، صفر ملاحظات. هذه النتائج لا تثبت قبول استئناف جديد أو ملاءمة startup أو جاهزية الإطلاق.

بعد دمج #198، [فحص التجميد على main37b96ec5](https://github.com/alphasigma13579-lang/ASIE/actions/runs/38155591268/job/114517795495) أبقى **REJECT_UNFREEZE / NO_GO** بسبب `technical_limited_gate_state`؛ تقرير البوابة يدرج `foundation_completion_program_cleared` ضمن `critical_failures`، بينما `frozen_files_unchanged=true`. لا يخفض هذا التصميم البوابة ولا يعيد الفحص بلا تغير، ولا يحول نجاح فحوص التسجيل إلى إذن إطلاق.

## 3. موضوع النطاق المحفوظ

[تصميم الفهرس المراجع #197](FC20-12-F01A-AUDIT-ORIGIN-INDEX-SCOPE-PROPOSAL-2026-10-11.md)، رأس `33ac90a47966afda4917f34162f11f5826eab565` وblob `9be7964b01ebd393724dc2adf6a559a8a1eddd64`، يبقى دون تعديل. لا يلغى منع schema العام؛ الاستثناء المسجل محصور في هوية العملية التالية فقط:

```json
{
  "operation": "CREATE_INDEX_IF_NOT_EXISTS",
  "index_name": "idx_security_audit_origin_proof",
  "table": "security_audit_events",
  "columns": ["action", "target_type", "target_id", "organization_id"],
  "unique": false,
  "implementation_path": "backend/repository.py",
  "test_path": "tests/test_repository_intelligence.py"
}
```

تبقى `allowed_schema_operations` مطابقة لهذه القائمة الوحيدة و`allowed_paths` التسعة مرتبة كما يلي، دون زيادة أو حذف:

1. `backend/asie_local_api.py`
2. `backend/repository.py`
3. `backend/intelligence_prerun_service.py`
4. `tests/test_repository_intelligence.py`
5. `tests/test_intelligence_prerun_service.py`
6. `tests/test_intelligence_context_ingress_api.py`
7. `docs/FC20-12-F01-TRUSTED-CONTEXT-INGRESS-REPAIR-PLAN-2026-10-01.md`
8. `tests/test_live_location_api.py`
9. `tests/test_intelligence_consumption.py`

العمل المطلوب لهذه الدفعة هو الفهرس المحدد واختباراته ضمن مساري repository واختباراته؛ بقاء المسارات التسعة في السجل ليس طلبًا لتغييرات تطبيق أخرى. لا استعلام أو مخزن أو مصدر ثقة أو resolver موازٍ، ولا proof migration أو backfill أو تغيير ذرية record+proof أو سياسة legacy/replay. لا merge لـ#189 أو تعديل C01–C03 أو F01B أو واجهة T08 من هذا التصميم.

## 4. بوابة إتاحة البدء تبقى مفتوحة

التسجيل لا يقر موضع `init_schema()`، والاستئناف الحاكم اللاحق لا يعلن استيفاء بوابة التصميم. التهيئة متزامنة عند إنشاء Repository واستيراد API؛ مهلة انتظار القفل 30 ثانية ليست حدًا لبناء الفهرس.

قبل قبول موضع التطبيق، تبقى متطلبات #197 كما هي:

- تحديد المالك حجم بيانات تمثيليًا وحدود انتظار/جاهزية مقبولة ونافذة صيانة وقيود تزامن وقرار معالجة الفشل. جميعها **UNKNOWN / NOT_APPROVED** هنا؛ لا SLO أو قيمة افتراضية من المساعد.
- دليل منفصل على بيانات اصطناعية قابلة للتخلص منها، بدء بارد وبدء متزامن وفق قيد المالك وبحد أدنى عمليتين، كاتب دون مهلة القفل وفوقها، كلفة البناء والمساحة والتعارض/الانقطاع وإعادة الفتح وسلامة الصفوف. لا نسخ أو تعديل قاعدة المالك.
- خطة معالجة فشل/صيانة/استعادة معتمدة؛ لا retry أو DROP تلقائي أو live migration أو تشغيل خلفي أو route بديل مفترض.
- إذا غابت المعايير أو الأدلة أو الخطة، يظل قبول الموضع محجوبًا. إذا أثبتت الأدلة عدم الملاءمة يعود قرار التصميم إلى المالك؛ لا يستبدل المسار تلقائيًا.

هذا التصميم لا يأذن حتى بتشغيل تجربة index؛ لا بد من تفويض المرحلة المحددة قبل أي SQL أو اختبار تنفيذ جديد. عند طلب قرار الاستئناف يوضح أي عمل معزول يمكن تفويضه وما الذي يبقى متوقفًا بسبب بوابة الإتاحة؛ لا تستنتج هذه الحدود من العلم true وحده. لا يساوي اجتياز حارس الحوكمة قبول التطبيق أو التشغيل الفعلي.

## 5. انتقال RESUME اللاحق المقترح — محجوب بغياب القرار

بعد قرار المالك الجديد المرتبط بالعملية فقط، يقترح انتقال مستقل:

1. الدلتا الوحيدة في manifest الكامل: `execution_authorized=false → true` حرفيًا وإلحاق RESUME عاشر واحد؛ لا تغيير أي مسار أو عملية أو تاريخ أو سلطة أخرى.
2. مفاتيح الحدث مغلقة وفق النمط السابق: `type`، `recorded_at`، `baseline_commit_sha`، `baseline_manifest_blob_sha`، `checkpoint`، `scope_extension`، `owner_resume_decision`، `effect`. لا يكتب وقت أو قرار مستقبلي هنا.
3. baseline الحدث الجديد هو `37b96ec504d60f62bcdb5f4e69e0e5a0d8082f34` وblob `386687c230db26e46ad831bbaeaeddddecfae795`، لا الزوج التاريخي `83afd283/1cfbaf19` الموجود في نسختي checkpoint/scope. ينسخ الحدثان الثامن والتاسع كاملين دون اختزال أو إعادة كتابة.
4. `owner_resume_decision` يثبت ID ورابط إيصال ووقت فعليين، وcommit/blob فعليين لهذا التصميم بعد مراجعته. موضوعه يربط baseline/blob وcheckpoint والنطاق المضاف ورأس #189 والمسارات التسعة و`allowed_schema_operations` بهويتها وأنواعها الكاملة. لا تطابق مسارات وحدها، ولا unique=0 بدل false، ولا مرجع main متحرك.
5. يبقى أثر الاستئناف ضمن `F01A_DEFENSIVE_RESUME_ONLY` بشرط `REVIEWED_GOVERNANCE_TRANSITION_MERGED_AFTER_SEPARATE_OWNER_MERGE_APPROVAL`؛ لا يوسع التصميم أثر هذا النمط السابق أو يجعل التوثيق إذنًا للتطبيق. يجب أن ينص القرار الجديد على قيد العملية وبوابة الإتاحة، وإلا يرفض إعداد انتقال التنفيذ حتى توضيح المالك.
6. لا تستخدم موافقة إعداد هذا الطلب، إيصال إعداد #198، موافقة دمج #197/#198، أو RESUME السابع كقرار استئناف جديد. عند تغير baseline أو التطبيق تعاد مقارنة الفروق ويعرض التغير المادي، لا تورث الموافقة من ancestry.

لا يوجد الآن `owner_resume_decision` صالح لهذا الانتقال. لذلك لا يعدّل هذا المرشح manifest أو oracle لقبول true، ولا ينشر انتقالًا بموافقة مختلقة أو placeholder قابل للمرور.

## 6. الملفات والحراس اللاحقة

PR انتقال الحوكمة، إن فوض بعد القرار، يبقى في الملفات السبعة نفسها:

1. `/FOUNDATION-COMPLETE-20.json`
2. `tests/test_foundation_complete_20_program.py`
3. `docs/FOUNDATION-COMPLETE-20-CORE-INTELLIGENCE-COMPLETION-PROGRAM-2026-07-29.md`
4. `docs/EKB/FOUNDATION-COMPLETE-20-PACKAGE-INDEX.md`
5. `docs/ASIE-BETA-EXECUTION-MASTER-PLAN-2026-09-09.md`
6. `docs/FC20-12-F01A-DEFENSIVE-ENABLING-REGISTRATION-PROPOSAL-2026-10-01.md`
7. `docs/FC20-12-F01A-APPROVAL-CONSUMPTION-SCOPE-REGISTRATION-2026-10-09.md`

هذه قائمة مستقبلية محجوبة، لا ملفات التصميم المحلي الحالي. الحارس الحالي blob `46d55ca29cf1181dbde4c97841ddb1b2ec9f078c` يقبل حالة التسجيل المتوقفة فقط، ويبقى كما هو.

اختبارات القبول المستقبلية **NOT_RUN**:

- IRG-01: فرق العلم/الحدث فقط، والمسارات التسعة والعملية الواحدة دون توسعة.
- IRG-02: حفظ الأحداث التسعة ونسختي checkpoint/scope كاملتين؛ رفض الحذف والتكرار وإعادة الترتيب أو تاريخ إضافي.
- IRG-03: oracle مستقل للقرار الفعلي وموضوع العملية/التصميم/الرأس/الوقت؛ رفض الإعداد أو الدمج أو القرار القديم والحقول غير المعروفة وجميع أنواع Boolean الملتبسة.
- IRG-04: true حرفي وموضع واحد محفوظ ومحسوب وFC20-05 held؛ رفض موضع ثانٍ أو null أو انتقال DELIVERED.
- IRG-05: عكس RESUME والعلم يعيد manifest كاملًا إلى blob `386687c230db26e46ad831bbaeaeddddecfae795` ثم ISG→CRG→CS→RG→SG دون تغيير أختامها أو إسقاط اختبارات التحوير القديمة.
- IRG-06: prefixes الإسقاطات الخمسة المثبتة بعد #198 تبقى byte-exact، يليها حد فريد وختم terminal لكل مسار. رفض suffix/تعليق/CRLF/نقل قسم؛ استخراج التاريخ بعد التحقق من الختم، لا truncation صامت.
- IRG-07: الاختبارات التاريخية تعمل على inverse متحقق قبل تحوير الحدث المقصود؛ لا fixture أو حالة تاريخية تقبل كسلطة حالية، ولا فشل مبكر في wrapper يحل محل فحص oracle القديم.
- IRG-08: routing/release/freeze/network/provider/deployment والحزم والاعتماديات وبوابة الإتاحة وT08 محفوظة؛ لا تنفيذ schema أو نشر من اجتياز الحارس.

أختام prefixes الخمسة: FOUNDATION `be62522331e6ee4517bd43e49ac439451dfeeb3a`؛ EKB package index `a5e4f95f86cc0f2995097b3cbde81a9a1907c036`؛ خطة المالك `6ad9850c3407c5a90422ac4fcb1dd2b1f5f88b3e`؛ تسجيل F01A `6f14a56dfc1bfa329f793bfa012ecd1dff948117`؛ تسجيل الاستهلاك `391940ecbb9b6be83bd0f9e1570bdeecd3a8d4b7`.

## 7. التسليم والتوقف الآمن

المخرج الحالي تصميم من ملفين مأذون بنشره للمراجعة مع فحص مراجع واتساق ومراجعة مستقلة. التالي نتائج مراجعة رأس التصميم ثم القرار الجديد المشروط المحدد؛ لا نشر انتقال RESUME أو تعديل التطبيق من موافقة «إعداد الطلب».

بعد قرار التنفيذ المشروط: انتقال حاكم مستقل، اختبارات مركزة وexact-head CI ومراجعات ثم موافقة دمجه المنفصلة. يبقى تنفيذ الفهرس نفسه محكومًا بقيود التفويض وبوابة الإتاحة، ويعرض أي نقص مهم قبل العمل؛ لا قاعدة مالك أو نشر أو secrets أو خدمات أو تغيير AAS/Finance/Snapshot/Decision Council.

**نقطة التوقف الحالية:** F01A IN_PROGRESS/false، التصميم غير نافذ، قرار الاستئناف التنفيذي مفقود ومعايير الإتاحة غير معتمدة. لا يدعي هذا التصميم اكتمال المنصة أو إغلاق T08 أو ملاحظة الفحص الخطي قبل التنفيذ والدليل.
