# F-01A — تصميم الاستئناف المشروط بعد تسجيل نطاق الاستهلاك

## 1. الحالة وحدود موافقة الإعداد

- التاريخ: 2026-10-10، Asia/Riyadh. الحالة **PROPOSED / REVIEW_REQUIRED / NOT_EFFECTIVE**.
- موافقة المالك «موافق» على الإعداد والمراجعة موثقة في [إيصال الإعداد](https://github.com/alphasigma13579-lang/ASIE/pull/194#issuecomment-6100617449)، المسجل `2026-10-10T18:09:43Z`. أثرها **PREPARE_RESUME_DESIGN_AND_REVIEW_ONLY**؛ لا نستنتج منها قرار استئناف التطبيق أو إذن دمج.
- هذه الشريحة تعدل هذه الوثيقة ورابطها في مدخل EKB فقط. السجل والحارس والتطبيق والبيئة دون تعديل؛ الاختبارات المستقبلية أدناه خطة قبول لا نتائج منفذة.
- المالك صاحب الاعتماد النهائي، وCodex معدّ ومستشار تقني. الإيصال نقل لتوجيهه في المحادثة، لا توقيع أو إثبات هوية مشفر.

**القرار الذي يعرض بعد مراجعة التصميم:** قبول الاستئناف الدفاعي لـF-01A على checkpoint والنطاق المثبتين أدناه، مشروطًا بانتقال سجل وحارس مراجع على رأسه وبموافقة دمج منفصلة. لا يسجل قرار مستقبلي أو وقت افتراضي الآن. إعداد هذا التصميم لا يرفع `execution_authorized`.

## 2. خط الأساس والحالة الفعلية

المصدر الحاكم [main@cf45bd9ecfda815c4c2e848f69832ebf02935fb9](https://github.com/alphasigma13579-lang/ASIE/commit/cf45bd9ecfda815c4c2e848f69832ebf02935fb9)، بعد [إثبات دمج #194](https://github.com/alphasigma13579-lang/ASIE/pull/194#issuecomment-6100506181). [السجل المثبت](https://github.com/alphasigma13579-lang/ASIE/blob/cf45bd9ecfda815c4c2e848f69832ebf02935fb9/FOUNDATION-COMPLETE-20.json) blob `e8d700eed195244ed6e2236ca53df655b5ac561f`؛ ليس نص هذه الوثيقة مصدر حالة بديلًا.

- F-01A **IN_PROGRESS/false**؛ `delivery_evidence=null` و`closure_effect=NONE`.
- تاريخ الأحداث الستة: **START → STOP_CHECKPOINT → SCOPE_EXTENSION → RESUME → STOP_CHECKPOINT → SCOPE_EXTENSION**. الاستئناف التاريخي لا يعالج التوقف الأخير.
- checkpoint الأخير `2026-10-09T12:31:30Z`، baseline `23ea4b48e4c2f4c94e4f54c33bb0310bd6e0adc3` وblob `ac40d84cb7bfca4ea025cf754483a0561037e994`؛ سبب **CONSUMPTION_REVIEW_AND_TEST_SCOPE_GAP**؛ رأس التطبيق #189 `6211418ca295e710be7f686bd1592bb30649f1d6`.
- #194 سجّل `tests/test_intelligence_consumption.py` فقط؛ أثر التوسعة **SCOPE_EXTENSION_ONLY_NO_RESUME**، وشرط الاستئناف **NEW_OWNER_DECISION_AND_REVIEWED_EXACT_HEAD_GOVERNANCE_TRANSITION**.
- `active_target` محفوظ ومحسوب: FC20-12/f01a_defensive_ingress، موضع واحد و`max_active_executions=1`؛ **FC20-05 held**.
- FC20-12 يظل **ACR_REQUIRED** واعتمادياته FC20-08/09/11 محفوظة؛ routing_repair **REGISTERED_BLOCKED/false** وضوابطه التسعة **PENDING**؛ release **BLOCK** و`DARK_OFFLINE` و`network/provider/deployment=false`.

### قيد فحص ما بعد الدمج

[Governed Freeze Review — run 38073779503](https://github.com/alphasigma13579-lang/ASIE/actions/runs/38073779503)، job `114276396528`، فشل في **Verify cleared marker against fresh technical-limited gate**: القرار **REJECT_UNFREEZE** بسبب `technical_limited_gate_state`، والبوابة **NO_GO** مع `foundation_completion_program_cleared`. كانت سلامة marker وربط الرأس والعقد وفحص التجميد ناجحة؛ `frozen_files_unchanged=true` و`aas_runtime_freeze_mutated/finance_mutated/snapshot_mutated=false`.

هذه نتيجة محققة لهذا الرأس وليست إثبات أمان عام أو نشر Hostinger. نجاح تشغيل Evidence-Backed Beta Release Gate لا يلغي حكم NO_GO. لا نخفف marker أو البوابة أو نعيد الفحص بلا تغير. إعداد تصميم دفاعي غير تشغيلي لا يعلن اكتمال البرنامج؛ إن ظهرت بوابة مستقلة تمنع التنفيذ اللاحق تُعرض صراحةً ولا تُسقط.

## 3. نطاق إصلاح التطبيق المحفوظ — لا يبدأ هنا

إعادة استخدام [خطة F-01A الأصلية](FC20-12-F01-TRUSTED-CONTEXT-INGRESS-REPAIR-PLAN-2026-10-01.md) و[ملحق الاستهلاك وسياسة C-02 المعتمدة §4.1](FC20-12-F01A-APPROVAL-CONSUMPTION-SCOPE-ADDENDUM-2026-10-09.md) و[تسجيل #194](FC20-12-F01A-APPROVAL-CONSUMPTION-SCOPE-REGISTRATION-2026-10-09.md). نطاق التطبيق المسجل، مرتبًا ونسبياً لجذر الحزمة:

1. `backend/asie_local_api.py`
2. `backend/repository.py`
3. `backend/intelligence_prerun_service.py`
4. `tests/test_repository_intelligence.py`
5. `tests/test_intelligence_prerun_service.py`
6. `tests/test_intelligence_context_ingress_api.py`
7. `docs/FC20-12-F01-TRUSTED-CONTEXT-INGRESS-REPAIR-PLAN-2026-10-01.md`
8. `tests/test_live_location_api.py`
9. `tests/test_intelligence_consumption.py`

- **C-01:** صلاحية إيصال الاعتماد تُراجع عند الاستهلاك، ولا تكفي سلامته وقت الحفظ. لا نعمم الخلل على narrative الذي كان يعيد فحص الانتهاء.
- **C-02:** إثبات منشأ خادمي للسجلات الجديدة في معاملة SQLite نفسها باستخدام `security_audit_events` القائم؛ لا جدول أو schema جديد، ولا `Repository.audit()` ذي commit مستقل داخل المعاملة. هو دليل منشأ محلي، لا توقيع أو اعتماد. هوية الإنشاء ثابتة ولا تستمد من payload أو correlation_id؛ يميّز Draft بمعرف خادمي عن نموذج داخلي متحقق. replay يتحقق من العلاقة والمنشأ والملكية؛ legacy غير المثبت يرفض مغلقًا دون حذف أو تعديل أو إثبات بأثر رجعي. حصر الاستدعاءات وصيغة الدليل الدقيقة يثبتان قبل الكود.
- **C-03:** مفتاح الطلب غير النصي أو الفارغ يرفض قبل أي حساب أو كتابة، مع إبقاء الحالة النصية المشروعة.
- تبقى T-01–T-09 كاملة واختبارات AC-01–AC-13 في الملحق؛ خاصة **T08 OPEN**. لا إغلاق تعافي المتصفح باختبار HTTP، ولا بناء شاشة أو مسار موازٍ لتعويض واجهة غير مربوطة.
- يبقى المدخل العام Draft محدودًا؛ لا builder خام أو trusted flag أو تشغيل Pre-Run الخام. F-01B وبناء السياق الموثوق ليسا ضمن الاستئناف.

## 4. انتقال السجل اللاحق المقترح

هذا القسم تصميم **غير منفذ**. بعد قرار مالك مشروط محدد فقط:

1. تغيير `f01a_defensive_ingress.execution_authorized` من false إلى **true حرفيًا**، وإلحاق **RESUME واحد** كحدث سابع. لا تغيير لأي حقل آخر في manifest كله.
2. الحدث ذو مفاتيح مغلقة: `type` و`recorded_at` و`baseline_commit_sha` و`baseline_manifest_blob_sha` و`checkpoint` و`scope_extension` و`owner_resume_decision` و`effect`.
3. baseline وblob يثبتان على الحالة المتوقفة أعلاه. checkpoint وscope_extension نسختان كاملتان مطابقـتان للحدثين الخامس والسادس، لا اختزال أو إعادة كتابة للتاريخ.
4. `owner_resume_decision` يربط ID ورابط الإيصال ووقت التسجيل الحقيقي وموضوع القرار وcommit/blob موجودين لهذا المقترح المراجع. الموضوع يثبت baseline/blob وcheckpoint ورأس #189 والمسارات التسعة. الأثر **F01A_DEFENSIVE_RESUME_ONLY**، وشرط النفاذ **REVIEWED_GOVERNANCE_TRANSITION_MERGED_AFTER_SEPARATE_OWNER_MERGE_APPROVAL**.
5. لا قرار مصطنع أو self-hash أو مرجع main متحرك؛ موافقة الإعداد الحالية أو دمج #194 أو RESUME القديم لا تعوض القرار الجديد. إذا تغير الرأس تفحص الفروق؛ لا تنقل الموافقة من ancestry وحدها. تغير مادي يعرض قبل الانتقال.
6. state وموضع التنفيذ والقائمة والأب والتوجيه والحزم والاعتماديات والتجميد والإطلاق تبقى كما هي؛ لا DELIVERED أو START جديد أو إخلاء للموضع أو تشغيل ثانٍ.

### حراس الاستئناف وتاريخ التحقق

[الحارس المثبت](https://github.com/alphasigma13579-lang/ASIE/blob/cf45bd9ecfda815c4c2e848f69832ebf02935fb9/ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/tests/test_foundation_complete_20_program.py)، blob `27f0b15df804436703dfd62454e9d7e0aee5a45d`، يقبل الحالة المتوقفة فقط. تكييفه لاحقًا ليس تبديل assertion أو السماح العام بـtrue:

- oracle مستقل ثابت من السجل والإيصال المراجعين، لا قيمة متوقعة مشتقة من manifest أو الوثيقة الجاري اختبارها.
- عكس حدث RESUME والعلم يعيد **manifest الكامل** إلى blob `e8d700eed195244ed6e2236ca53df655b5ac561f`؛ ثم تستمر سلسلة العكس القديمة CS-05 وRG-05 وSG-05 بموادها الأصلية.
- السجل الحالي يقبل الاستئناف المحدد فقط بعد الانتقال؛ الحالة المتوقفة والتاريخ تبقيان مواد تحقق تاريخية لا fallback لمنح التنفيذ.
- CS-07 الحالي يختم خمسة إسقاطات من marker إلى EOF. إلحاق قسم استئناف لاحق يحتاج حدًا جديدًا فريدًا وصريحًا: البايتات السابقة كاملة تثبت على blobs #194، والقسم القديم يعاد اختباره بحده التاريخي المثبت؛ ثم ختم مستقل لكل قسم جديد. لا حذف لختم قديم أو digest افتراضي/مشترك، ولا تقسيم متساهل يقبل تعليقًا أو suffix غير محكوم. القسم القديم يبقى تاريخيًا لا مصدر حالة حالية.
- اختبارات التحوير القديمة تبقى؛ يرفض الحارس إعادة الترتيب أو الحذف أو التكرار أو تعديل السياسة/التاريخ أو marker أو نهايات الأسطر أو ادعاءات صلاحية خارج القسم المحدد.

## 5. قائمة ملفات انتقال الحوكمة اللاحق واختباراته

القائمة أدناه **سبعة ملفات فقط** تخص PR انتقال منفصل، وليست توسعة مسارات التطبيق ولا فرق هذه الشريحة:

1. `/FOUNDATION-COMPLETE-20.json`
2. `tests/test_foundation_complete_20_program.py` داخل الحزمة.
3. `docs/FOUNDATION-COMPLETE-20-CORE-INTELLIGENCE-COMPLETION-PROGRAM-2026-07-29.md`
4. `docs/EKB/FOUNDATION-COMPLETE-20-PACKAGE-INDEX.md`
5. `docs/ASIE-BETA-EXECUTION-MASTER-PLAN-2026-09-09.md`
6. `docs/FC20-12-F01A-DEFENSIVE-ENABLING-REGISTRATION-PROPOSAL-2026-10-01.md`
7. `docs/FC20-12-F01A-APPROVAL-CONSUMPTION-SCOPE-REGISTRATION-2026-10-09.md`

الخمسة الأخيرة تستقبل مقطعًا مشتقًا مؤرخًا بحد صريح، مع حفظ كل بايت سابق. هذا المقترح يثبت كمرجع قرار ولا يحتاج تعديله كي يصبح مصدر حالة. أي مسار إضافي يوقف الجزء المتأثر ويعرض قبل الكتابة.

| ID | دليل قبول انتقال الحوكمة المطلوب — NOT_RUN الآن |
|---|---|
| CRG-01 | فرق العلم/الحدث فقط، تسعة مسارات بالترتيب، لا wildcard أو زيادة حقول أو توسيع تطبيق |
| CRG-02 | حفظ الأحداث الستة ونسخ checkpoint/scope كاملة، رفض حذف أو تكرار أو ترتيب مختلف |
| CRG-03 | قرار المالك الجديد وموضوعه وcommit/blob مطابقون؛ رفض موافقات الإعداد/النطاق/الدمج/الاستئناف القديم |
| CRG-04 | true حرفي لا 1؛ موضع واحد محفوظ ومحسوب، FC20-05 held، رفض موضع ثانٍ أو null |
| CRG-05 | عكس manifest الكامل ثم السلسلة التاريخية؛ لا تغيير حزمة أو ضابط أو freeze أو release |
| CRG-06 | إسقاطات byte-exact قديمة وجديدة وحدود فريدة؛ رفض suffix/duplicate-marker/CRLF/تزوير السلطة/نقل قسم بين الملفات |
| CRG-07 | لا authority من fixture أو lifecycle أو مدخل manifest؛ حفظ اختبارات الرفض التاريخية دون مسار قبول مخفف |
| CRG-08 | routing_repair محجوب، كل ضوابطه PENDING؛ منع الشبكة والمزود والنشر والترحيل والتسليم أو إغلاق F-01A |

فحوص الحوكمة المستهدفة ثم بوابات المستودع المطلوبة مرة على الرأس النهائي؛ لا تكرار CI ناجح بلا تغير. مراجعات إضافية عند توافرها على الرأس نفسه؛ rate-limited أو skipped ليس اعتمادًا. TestSprite غير المفعّل ليس بوابة. نجاح هذه الاختبارات لا يثبت نجاح التطبيق أو العربية أو جاهزية البيتا.

## 6. التسليم والعودة إلى الخطة

1. تسليم هذا التصميم ورابط EKB في PR مستقل وفحص الفرق والروابط؛ لا تعديل للحارس أو التطبيق الآن.
2. بعد المراجعة، عرض التصميم وقرار الاستئناف المشروط المحدد على المالك. دمج المقترح يتطلب موافقته؛ لا إذن تطبيق من دمج وثيقة.
3. إعداد انتقال الملفات السبعة بعد القرار فقط؛ فحص ومراجعة رأسه ثم موافقة دمج منفصلة. كود #189 لا يستأنف قبل نفاذ الانتقال المراجع.
4. بعدها تنفيذ C-01/C-02/C-03 ضمن المسارات التسعة مع AC-01–AC-13 وT-01–T-09 وأدلة أمان/بيانات/عزل/تزامن؛ لا نقل نتائج #194 إلى التطبيق. #192 يبقى طلبًا منفصلًا، لا توسعة تلقائية أو اعتمادًا لهذا الإصلاح.
5. [خطة بيتا المالك والإدارة المستقلة](ASIE-BETA-EXECUTION-MASTER-PLAN-2026-09-09.md) وأهدافها وحدودها محفوظة؛ #166 `2dccc2c45c2b1967e277edf6db6a681a04b2654a` ثم #167 `435777008e01bafc73ab3bca86cc8945e311b610`. لا محو لتقدم التخزين أو استئناف FC20-05 تلقائي.
6. لا تعديل Finance أو Snapshot أو AAS أو Decision Council أو Kernel/Hearts/Bus/Socket/Module Runtime أو AIA-01/02 أو API registry أو SQLite schema؛ لا F-01B أو تشغيل Hostinger أو أسرار أو دعوات أو خدمات أو محرك استدلال عام.

الخطر التشغيلي لهذه الوثيقة منخفض لأنها لا تغير إذنًا أو تشغيلًا؛ خطر تفسير الموافقات حقيقي ولذلك فصلت الإعداد عن الاستئناف والدمج. تقدير مرحلة الإعداد 12–20 ألف توكن للقياس، دون سقف؛ تقرير واحد في نهايتها، ولا قيمة مصطنعة إذا تعذر العداد.

**نقطة التوقف الآمنة:** تصميم محفوظ وطلب مراجعة، F-01A ما زال IN_PROGRESS/false. الهدف الكامل لإصلاح المدخل غير مكتمل؛ الخطوة التالية نتيجة المراجعة ثم قرار المالك المشروط المحدد، لا بدء تطبيق أو دمج تلقائي.
