# مقترح تسجيل تمكين F-01A الدفاعي داخل FOUNDATION-COMPLETE-20

## 1. النطاق والسلطة

- التاريخ: 2026-10-01، Asia/Riyadh.
- الحالة: **PROPOSED / REVIEW_REQUIRED / NOT_BUILD_READY**؛ هذا طلب تغيير حاكم محدود، وليس سجل حالة بديلًا أو تصريح بدء.
- المرجع الحالي: [main@08a825ae046ba3595981590ca03ea5ef03f04ace](https://github.com/alphasigma13579-lang/ASIE/commit/08a825ae046ba3595981590ca03ea5ef03f04ace).
- [خطة F-01A](FC20-12-F01-TRUSTED-CONTEXT-INGRESS-REPAIR-PLAN-2026-10-01.md) و[اعتماد المالك للنطاق وأثر التوافق](https://github.com/alphasigma13579-lang/ASIE/pull/179#issuecomment-5920890935) محفوظان. لا نعيد طلب قبول النطاق من الصفر. موضوع القرار الجديد هو شكل التسجيل والحارس وشروط بدء التمكين، لا إعادة قبول F-01A.
- دُمج #178 عند 04782a76c6adcc62a73ec710d8c4383210237f45، و#179 عند 08a825ae046ba3595981590ca03ea5ef03f04ace. تغييرات العرض العربي/الإنجليزي والتعافي ضمن خطة #179 المدموجة تبقى ملزمة؛ لا تُنقل مراجعاتها إلى هذا الطلب.
- المالك صاحب القرار النهائي؛ Codex معدّ ومستشار تقني، وليس معتمدًا مستقلًا. التعليقات تسجل طلب الإنسان ولا تمثل توقيعًا مشفرًا.

**تسليم هذا الطلب:** هذه الوثيقة ورابط مدخل EKB فقط. لا تعديل JSON أو الحارس أو التطبيق أو البيانات أو ACR المجمد، ولا دمج أو تشغيل أو نشر.

## 2. الدليل ولماذا يلزم التغيير

| الحقيقة عند الرأس أعلاه | المرجع | النتيجة |
|---|---|---|
| السجل الآلي هو مصدر حالة البرنامج؛ يمنع برنامج معالجة موازٍ | [FOUNDATION، §3 و§8](FOUNDATION-COMPLETE-20-CORE-INTELLIGENCE-COMPLETION-PROGRAM-2026-07-29.md) | يسجل التمكين داخل البرنامج نفسه |
| execution_sequence v1 يثبت الأولوية/الانتظار فقط؛ active_target=null | [السجل الآلي](../../FOUNDATION-COMPLETE-20.json)؛ blob ad87be6b2368bc75b499314211f63c636b8fd090 | موافقة النطاق وحدها لا تملأ الموضع |
| validate_execution_sequence يرفض أي نشاط، وvalidate_routing_registration يقبل شريحة واحدة محجوبة فقط | [الحارس، 206–350](https://github.com/alphasigma13579-lang/ASIE/blob/08a825ae046ba3595981590ca03ea5ef03f04ace/ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/tests/test_foundation_complete_20_program.py#L206)؛ blob a37c4920db79ab62bc5809ef9e499ac6f7334630 | يلزم انتقال صريح مختبر، لا حذف assertion أو إخفاء عمل |
| F-01A تقوية مدخل قائم ورفض البناء الخام، لا استعادة البناء الموثوق | [خطة الإصلاح §3–6](FC20-12-F01-TRUSTED-CONTEXT-INGRESS-REPAIR-PLAN-2026-10-01.md) | لا يُشترط إكمال التوجيه المتعذر قبل إصلاح عيبه؛ ولا يصبح إصلاح العيب أهلية توجيه |

هذا تحليل اتساق ساكن، لا تجربة استغلال حي. قبول السجل لاحقًا يثبت اتساق التسجيل فقط، وليس أمان التطبيق أو هوية صاحب القرار أو قدرة تشغيلية.

## 3. القرار التصميمي المقترح — أصغر تغيير داخل السجل القائم

إضافة شريحة ثانية **محددة بالاسم والنطاق** داخل packages[FC20-12].execution_slices:
`f01a_defensive_ingress`، بمخطط `asie.foundation.defensive-enabling.v1`. لا إنشاء قائمة برامج أو مصدر حالة آخر، ولا استخدام مخطط أهلية routing_repair لمنح هذا التمكين.

- يبقى سجل routing_repair الحالي، بمخطط routing-eligibility.v2 وجميع حقوله، **دون تغيير**: REGISTERED_BLOCKED، execution_authorized=false، الضوابط التسعة PENDING، eligibility_record فارغ.
- تبقى حالات الحزم الست عشرة واعتمادياتها وأدلة اكتمالها وتجميدها كما هي؛ FC20-12 يظل ACR_REQUIRED، واعتماديات إغلاقه FC20-08/09/11 لم تسقط.
- الشريحة الدفاعية متطلب تمكين سابق للتوجيه، وليست تنفيذًا لقرار المجلس أو Snapshot. لها تحقق دخول محصور، لا PASS تلقائيًا لأي ضابط توجيه.
- يبقى FC20-05 held مع تقدم IN_PROGRESS وcheckpoint الأصلي؛ حد التنفيذ الفعلي واحد ويحسب الحزم غير الموقوفة وكل شريحة IN_PROGRESS، حتى داخل حزمة موقوفة.
- يحدّث execution_sequence إلى v2 ذات أثر `BOUNDED_DEFENSIVE_ENABLING_ONLY`؛ تحفظ ordering_decision وpriority_target الحاليين وheld_packages وmax_active_executions=1. الأولوية النهائية ما زالت routing_repair؛ الشريحة الجديدة تمكينها السابق الوحيد المسموح، لا استبدال الأولوية.

### 3.1 محتوى الشريحة والتحقق

يحدد PR التسجيل القادم مجموعة مفاتيح صارمة، ويرفض أي مفتاح مجهول أو ناقص أو نوع غير صحيح. تشمل المجموعة:

| الحقل | الشرط |
|---|---|
| schema / id / registry_effect | القيم المحددة أعلاه؛ أثر BOUNDED_DEFENSIVE_ENABLING_ONLY |
| state / execution_authorized | REGISTERED_BLOCKED وfalse عند التسجيل؛ لا true إلا مع انتقال البدء المنضبط أدناه |
| prerequisite_for | FC20-12/routing_repair؛ علاقة ترتيب فقط، لا فتح سجل التوجيه |
| scope_document | مسار خطة F-01A المدموجة، commit مثبت وblob مطابق؛ لا branch متحرك |
| owner_scope_decision | تعليق #179 أعلاه وتوقيته وأثره؛ لا يحل محل قرار التسجيل/البدء الجديد |
| registration_decision / start_decision | قراران محددا الموضوع والرأس والأثر والتاريخ والرابط؛ start_decision=null في التسجيل الأول |
| subject / allowed_paths / environment | baseline SHA كامل مثبت؛ قائمة ملفات F-01A §4 مطابقة، وDARK_OFFLINE؛ لا wildcard أو ملفات مجمدة |
| entry_requirements | قبول أثر التوافق، صلاحيات/عزل/سلامة بيانات وخطة الاختبارات T-01–T-09، ملكية تغيير خادمي دفاعي، وعدم وجود تنفيذ آخر؛ لا ادعاء نجاح اختبارات التطبيق قبل كوده |
| delivery_evidence / events | فارغتان عند التسجيل؛ تحفظان أدلة الرأس النهائي وتاريخ الانتقالات/المنع لاحقًا، دون مسح التاريخ |
| closure_effect | NONE؛ تسليم الشريحة لا يغلق F-01 أو حزمة أو ضابط توجيه |
| network_authorized / provider_activation_authorized / deployment_authorized | false دائمًا؛ لا مفاتيح أو مهاجرات أو دعوات من هذا السجل |

هذه مواصفة للتحقق المقترح، لا JSON نافذ الآن. أدوات الحارس تتحقق من البنية والمراجع المثبتة والتوافق بين الحالة والقرار والموضع؛ لا تدّعي التحقق المشفر من هوية المالك أو تنفيذ قفل عمليات حي.

## 4. الانتقالات والبدء والتوقف

1. **التسجيل:** بعد مراجعة هذا التصميم واعتماده، PR حاكم مستقل يعدّل السجل والحارس وواجهات القراءة معًا. يبدأ السجل الجديد REGISTERED_BLOCKED، التنفيذ false، وactive_target=null. لا تطبيق في هذا PR.
2. **البدء:** بعد دمج التسجيل وقرار مالك صريح يسمح ببدء F-01A على المرجع المراجع، يسجل انتقال واحد: الشريحة IN_PROGRESS/true، وactive_target={kind: slice, package_id: FC20-12, slice_id: f01a_defensive_ingress}. يجب أن تطابق قائمة النشاط هذا الهدف وحده؛ لا مسار route يُفتح. يسجل الانتقال بفرق حاكم مراجع قبل كود الإصلاح.
3. **ربط الرأس دون استحالة self-hash:** موضوع قرار البدء هو commit موجود ومراجع وخطة/قائمة ملفات مثبتة، لا SHA المفترض للـcommit الذي يحتوي القرار نفسه. كل رأس إصلاح لاحق يتتبع ancestry والفرق إلى الموضوع؛ أدلة الاختبارات والمراجعات النهائية مرتبطة برأس التسليم الحقيقي. لا يُعاد ادعاء صلاحية رأس مختلف من مجرد سلسلة ancestry.
4. **تغير مؤثر/سحب قرار/توسع خارج القائمة:** توقف الشريحة المتأثرة قبل كود التوسع، وتسجل واقعة المنع والـcheckpoint؛ لا يخفى العمل بوضع null أو تغيير اسم الهدف. تبقى الشريحة والموضع محسوبين أثناء توقف غير مغلق حتى قرار توثيقي مراجع ينهي/يلغي نشاطها بأثر محفوظ. لا بدء هدف آخر تلقائيًا.
5. **التسليم:** بعد T-01–T-09، أدلة exact-head، مراجعة الأمان/الاتساق وقرار الدمج والتسليم، تنتقل الشريحة إلى DELIVERED وexecution_authorized=false مع أدلتها؛ يفرغ الموضع باتساق. DELIVERED ليست COMPLETE لحزمة وليست تصريح استعادة Pre-Run.
6. **الاستئناف/التراجع:** لا استئناف تلقائي أو إعادة ثقة خام. يسجل قرار جديد على checkpoint ورأس محقق، مع إثبات موضع واحد. يبقى الأصل والتاريخ؛ لا بيانات مالك تتغير ضمن الحوكمة. F-01B وبوابات التوجيه أعمال لاحقة بعقودها.

التسجيل ليس مانعًا للإصلاح إلى الأبد: مسار الانتقال أعلاه محدود وواضح. لكنه لا يخفي بدءًا غير مأذون داخل تغيير توثيقي.

## 5. الملفات المسموح بتعديلها في PR التسجيل اللاحق

المسارات من جذر المستودع؛ هذه **خطة** وليست ملفات تغيرت بهذا الطلب:

- /FOUNDATION-COMPLETE-20.json: الشريحة الثانية وexecution_sequence v2 فقط؛ لا إعادة كتابة الحزم أو أدلة الإنجاز.
- ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/tests/test_foundation_complete_20_program.py: dispatch تحقق حسب هوية/مخطط الشريحتين، وعداد/مطابقة النشاط والاختبارات السلبية. منع العام والمجهول باقٍ؛ تاريخ v1 لا يجيز downgrade للمصدر الحالي.
- docs/FOUNDATION-COMPLETE-20-CORE-INTELLIGENCE-COMPLETION-PROGRAM-2026-07-29.md، docs/EKB/FOUNDATION-COMPLETE-20-PACKAGE-INDEX.md، docs/ASIE-BETA-EXECUTION-MASTER-PLAN-2026-09-09.md داخل الحزمة: مزامنة أثر التسجيل وخطوة البدء وcheckpoint، لا إنشاء سلطة حالة.
- هذه الوثيقة: رابط قرار اعتماد التصميم ودليل تسليم التسجيل، مع الحفاظ على حقيقة أنه مقترح عند إنشائه.

ملفات التطبيق واختبارات إصلاحه تبقى قائمة §4 من خطة F-01A، خارج PR التسجيل. لا تغيير API registry أو AIA أو SQLite schema أو عقد التشغيل المجمد. أي احتياج خارج هذه القائمة يعرض كتوسع محدد قبل تنفيذه.

## 6. بوابات قبول التسجيل — اختبارات مطلوبة لا نتائج

| ID | الدليل المطلوب في PR الحارس |
|---|---|
| G-01 | التسجيل المحجوب صحيح، وactive_target=null؛ قبول المثالين المعروفين فقط ورفض slice/field/schema/type/decision مجهول أو مفقود أو مكرر |
| G-02 | fixture انتقال بدء صحيح يمكّن F-01A وحده؛ رفض state/flag/slot غير متطابقة أو بدء بلا قرار مثبت أو بنطاق أوسع |
| G-03 | رفض تنفيذ routing_repair أو حزمة أخرى أو هدفين؛ عد slices داخل held package؛ لا إخفاء نشاط بتغيير hold/state |
| G-04 | بقاء سجل routing_repair كاملًا دون تغيير، وتسع ضوابط PENDING وإثبات فارغ؛ رفض أي PASS/receipt/eligibility مزور أو إسقاط اعتماديات |
| G-05 | baseline/الخطة/قرار النطاق/قرار التسجيل/البدء لها SHAs وروابط مطابقة؛ رفض مرجع متحرك أو بصمة مختلفة أو replay من موضوع آخر؛ فحص القراءة البشرية مستقل عن اتساق JSON |
| G-06 | رفض frozen paths/wildcards وأثر الشبكة/المزود/النشر/المهاجرات؛ كل الحزم وأدلة الإنجاز وrelease BLOCK وملفات freeze وcheckpoint #166/#167 محفوظة |
| G-07 | تاريخ توقف/إلغاء/تسليم محفوظ، ولا DELIVERED دون دليل رأس نهائي ومراجعة وقرار؛ رفض تحرير الموضع مع شريحة نشطة أو استئناف دون قرار جديد |
| G-08 | تطابق شرح البرنامج ومدخل EKB والخطة مع السجل؛ استمرار اختبارات الحارس الحالية السلبية والتوافق التاريخي المقيد دون إسقاطها لإرضاء مخطط جديد |

اختبارات الحوكمة مستهدفة في GitHub CI على الرأس النهائي، مع بوابات المستودع الإلزامية وفحص الفرق/التجميد. لا إعادة فحوص التطبيق الناجحة يدويًا لتغيير توثيق صرف؛ لا اختبارات حيّة أو تشغيل مزود. TestSprite غير المفعّل ليس بوابة. قبول G-01–G-08 لا يثبت T-01–T-09 أو أمان إصلاح لم ينفذ.

## 7. المخاطر ونقطة القرار والاستمرار

التوثيق الحالي منخفض الأثر التشغيلي؛ انتقال الحارس اللاحق **متوسط الخطر الحاكم** لأنه يسمح بنشاط محدد كان مرفوضًا. تقليله يكون بقائمة مغلقة للشريحتين، مطابقة الموضع/النشاط، اختبارات mutations، وحفظ المنع الحالي للتوجيه والتجميد. التراجع عن التسجيل لا يبرر إعادة الثغرة أو إخفاء تنفيذ قائم.

**القرار التالي بعد المراجعة:** اعتماد هذا التصميم لإعداد PR السجل والحارس المحدد، لا إعادة اعتماد النطاق الأمني ولا دمج تلقائيًا. بدء كود F-01A له انتقال وقرار البدء الموصوفان؛ لا تصريح frozen routing من أي خطوة هنا.

[خطة بيتا المالك والإدارة المستقلة](ASIE-BETA-EXECUTION-MASTER-PLAN-2026-09-09.md) و[checkpoint FC20-05](FC20-ROUTING-PRIORITY-AND-FC20-05-CHECKPOINT-2026-09-28.md) محفوظان. #166: 2dccc2c45c2b1967e277edf6db6a681a04b2654a، #167: 435777008e01bafc73ab3bca86cc8945e311b610. بعد التصحيح وبواباته نعود إلى /admin والنشاط والعربية وسند ثم تهيئة المالك بتفويض مستقل؛ لا دعوات أو أسواق أو محرك استدلال عام الآن.

**التوقف الآمن الحالي:** PR مقترح توثيقي مراجع؛ السجل والحارس والتطبيق والبيئة لم تتغير. المصدر الحالي للحالة يظل JSON الرسمي، لا هذه الوثيقة.

<!-- F01A-REGISTRATION-DELIVERY -->

## 8. أثر اعتماد التصميم وتسليم التسجيل — 2026-10-01

[قرار المالك](https://github.com/alphasigma13579-lang/ASIE/pull/180#issuecomment-5921569549) اعتمد التصميم ودمج #180 وإعداد طلب السجل والحارس فقط. دُمج المقترح عند 8fb47f3668133093197844816eb2a644793e5f20؛ حالة PROPOSED في §1 محفوظة كلقطة الإنشاء، لا إنكار لاعتماد التصميم ولا إعلان بدء. موضوع القرار c000c11f5d9952090c4bfb6622456fb550106bdb وblob e41b6e612b29e22079fbf231b299ad4aab5a9b4b. النص الأصلي أعلاه محفوظ دون تعديل.

مرشح التسجيل يضيف شريحة REGISTERED_BLOCKED، تنفيذ false، start_decision=null، وslot فارغة؛ لا تطبيق. يتضمن الحارس oracle ثابتًا لمراجع النطاق/التصميم والحقول المسموحة، ولا يستمد تصريحًا من JSON نفسه. يختبر G-02/G-07 عبر نموذج lifecycle معزول يرفضه مسار قبول السجل الحالي دائمًا؛ الانتقال الحقيقي اللاحق يثبت قرار البدء/التسليم وأدلته في تعديل حارس مراجع، وليس إدخال fixture أو علامة true.

تتحقق اختبارات G-01/G-03–G-06/G-08 والاختبارات السابقة من التزوير/الحقول/الموضع والتزامن الحاكم وملكية الشريحة والمراجع/بصمة وثائق LF وحفظ الضوابط/الحالات/checkpoint. تحويل CRLF إلى LF في فحص النص يجعل الدليل مطابقًا لتمثيل Git على Windows/Linux، لا يدّعي توقيعًا أو إثبات هوية. التنفيذ والفحوص الناجحة تسجل في طلب التسجيل على رأسه النهائي؛ هذه الفقرة لا تصنع نتيجة CI مسبقًا.

التوقف: طلب السجل والحارس للمراجعة دون دمج؛ التالي مراجعات رأسه ثم قرار دمج منفصل. قرار بدء F-01A منفصل كما في §4، مع بقاء التوجيه المجمد محجوبًا وT-01–T-09 متطلبات لم تنفذ.

<!-- F01A-CONDITIONAL-START-2026-10-03 -->

### انتقال بدء F-01A الدفاعي المشروط — مرشح 2026-10-03

دُمج التسجيل #181 عند `de88be7710164c2fe9f176759745b986b0400112`. فقرات التسجيل/البدء المحجوب أعلاه تصف مراحلها التاريخية؛ مصدر الحالة الحالي هو /FOUNDATION-COMPLETE-20.json، لا هذه القراءة المشتقة.

[توجيه المالك](https://github.com/alphasigma13579-lang/ASIE/pull/181#issuecomment-5963212063) بعد [المقترح](https://github.com/alphasigma13579-lang/ASIE/pull/181#issuecomment-5963144564) يجيز إعداد هذا الانتقال فقط. أثره المرشح **F01A_DEFENSIVE_START_ONLY**؛ شرط النفاذ **REVIEWED_GOVERNANCE_TRANSITION_MERGED_AFTER_SEPARATE_OWNER_MERGE_APPROVAL**. لا يبدأ إصلاح التطبيق قبل مراجعات وفحوص الرأس النهائي وقرار دمج مستقل ودمج الانتقال؛ لا يكفي إنشاء الفرع أو CI أو هذا التعليق.

يسجل المرشح f01a_defensive_ingress وحده IN_PROGRESS/true، بقرار مثبت وحدث START، وactive_target={kind: slice, package_id: FC20-12, slice_id: f01a_defensive_ingress}. موضوع البدء هو المرجع الموجود `de88be7710164c2fe9f176759745b986b0400112`؛ baseline التسجيل السابق 8fb47f3668133093197844816eb2a644793e5f20 محفوظ في مرجعه التاريخي. لا self-hash ولا قبول قرار من manifest؛ oracle الحارس يثبت هذا القرار والنطاق نفسه. عد التنفيذ الفعلي واحد؛ FC20-05 held بلا تغيير تقدمه أو checkpoint #166/#167.

routing_repair يظل REGISTERED_BLOCKED/false، وضوابطه التسعة PENDING وسجله دون تغيير. الحزم الست عشرة واعتمادياتها وأدلتها والملفات المجمدة محفوظة. DARK_OFFLINE؛ release BLOCK؛ network/provider/deployment=false؛ لا Runtime أو Finance أو Snapshot أو Decision Council أو ترحيل أو دعوات من هذا الانتقال.

نموذج lifecycle يبقى اختبارًا معزولًا ولا يجيز قرارًا أو تسليمًا. الحارس يقبل START المثبت فقط؛ checkpoint/سحب القرار/التسليم الحقيقي يحتاج فرقًا حاكمًا مراجعًا يحفظ التاريخ والموضع إلى الإغلاق، ولا يغيره هذا الطلب. لا استئناف تلقائي أو إفراغ موضع لإخفاء العمل. أدلة T-01–T-09 غير منفذة هنا؛ الشريحة التالية إصلاح التطبيق المحصور بعد نفاذ الانتقال، لا F-01B أو فتح التوجيه أو Hostinger. خطة بيتا المالك والإدارة المستقلة محفوظة.

التوقف الآمن: PR السجل والحارس للمراجعة دون دمج، وقبل كود التطبيق. نصوص المراحل السابقة محفوظة كتاريخ، لا تستخدم لنقل اعتماد رأس قديم أو إسقاط بوابة.

<!-- F01A-STOP-CHECKPOINT-2026-10-05 -->

### توقف F-01A الدفاعي — مرشح 2026-10-05

هذا فرق حاكم لتسجيل واقعة الاحتياج خارج النطاق، وفق عقد التسجيل §4 و[الملحق المدموج #183](https://github.com/alphasigma13579-lang/ASIE/blob/23659956064e6750edbf7ef0ffb7f812ae05b985/ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/docs/FC20-12-F01A-TEST-FIXTURE-SCOPE-ADDENDUM-2026-10-04.md)، على المرجع الموجود `23659956064e6750edbf7ef0ffb7f812ae05b985`. وقت إعداد التسجيل `2026-10-05T10:21:21Z` ليس ادعاء وقت اكتشاف الخلل أو إيقاف خدمة حية.

السجل المرشح يحفظ START وقرار البدء والنطاق الأصلي، ثم يضيف STOP_CHECKPOINT بسبب OUT_OF_SCOPE_TEST_FIXTURE: الحاجة إلى `tests/test_live_location_api.py`؛ الملف ليس ضمن allowed_paths ولا يضاف في هذا الطلب. f01a_defensive_ingress بحالة **IN_PROGRESS/false**: عمل غير مغلق مع execution_authorized=false؛ **active_target محفوظ ومحسوب** في FC20-12/f01a_defensive_ingress. لا إفراغ للموضع أو إخفاء للعمل أو إعلان DELIVERED.

شرط الاستئناف **NEW_OWNER_DECISION_AND_REVIEWED_EXACT_HEAD_GOVERNANCE_TRANSITION**. قرار البدء القديم محفوظ تاريخيًا ولا يجيز استمرارًا بعد هذا التوقف. تسجيل التوسعة وقبول نطاقها وقرار استئنافها انتقالات مستقلة لاحقة؛ دمج الملحق لا يمنح الاستئناف. نفاذ هذا التسجيل يتطلب مراجعات وفحوص رأسه وموافقة دمج منفصلة؛ هذه القراءة مشتقة من السجل وليست سلطة تشغيل.

الحارس يقبل checkpoint المثبت فقط ويرفض محوه أو إعادة START أو تبديل الرأس أو تزوير المرجع أو إضافة الملف أو استئناف التنفيذ من metadata. نموذج lifecycle المعزول يبقى اختبارًا لا إذنًا؛ لا يوسع هذا الطلب نموذجه ولا يستعمله للقبول الحقيقي.

FC20-05 held و#166 `2dccc2c` ثم #167 `4357770` وخطة بيتا المالك والإدارة المستقلة محفوظة. routing_repair REGISTERED_BLOCKED/false وضوابطه التسعة PENDING؛ حالات الحزم واعتمادياتها وأدلتها والملفات المجمدة وقرار release BLOCK دون تغيير. DARK_OFFLINE، network/provider/deployment=false؛ لا Finance أو Snapshot أو AAS أو Decision Council أو كود تطبيق أو ترحيل أو دعوات أو Hostinger.

نقطة التسليم: PR السجل والحارس وهذه القراءات الأربعة للمراجعة فقط. التالي بعد قبول التسجيل ودمجه: تسجيل توسعة ملف الاختبار المحدد مع حارسها ضمن تفويض مستقل، ثم قرار استئناف مستقل؛ لا يبدأ أي منهما تلقائيًا.

<!-- F01A-SCOPE-EXTENSION-2026-10-06 -->
### تسجيل توسعة F-01A دون استئناف — مرشح 2026-10-06

هذه قراءة مشتقة من /FOUNDATION-COMPLETE-20.json؛ **REGISTRATION_CANDIDATE / REVIEW_REQUIRED / NOT_EFFECTIVE_UNTIL_SEPARATE_OWNER_MERGE_APPROVAL**. التاريخ السابق محفوظ، ولا تُقرأ حالة المقترح عند إنشائه بوصفها الحالة الأحدث. [تصميم التسجيل المراجع #185](https://github.com/alphasigma13579-lang/ASIE/blob/1213fe78da66072a246c8592e69b5f4ebb91b22a/ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/docs/FC20-12-F01A-TEST-FIXTURE-SCOPE-REGISTRATION-PROPOSAL-2026-10-06.md)، blob `eeaf6354a9fc8b790812cb876cb95d4574bb562b`، مدموج عند `5daa0b15b8b120575ea627429b754bd655ffd346`.

قرار النطاق والتصميم `DECISION-FC20-12-F01A-TEST-FIXTURE-SCOPE-DESIGN-2026-10-06` محفوظ في https://github.com/alphasigma13579-lang/ASIE/pull/185#issuecomment-6023988634، وقت تسجيل الإيصال `2026-10-06T19:34:56Z`؛ موضوعه الرأس `1213fe78da66072a246c8592e69b5f4ebb91b22a` وأثره **SCOPE_DESIGN_APPROVED_NO_MERGE_NO_RESUME**. الإيصال ينقل موافقة المالك في المحادثة؛ ليس توقيع هوية مشفرًا ولا موافقة دمج هذا التسجيل.

الزيادة الوحيدة `tests/test_live_location_api.py`، لتجهيز الاختبارات التابعة فقط حسب [ملحق النطاق #183](https://github.com/alphasigma13579-lang/ASIE/blob/23659956064e6750edbf7ef0ffb7f812ae05b985/ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/docs/FC20-12-F01A-TEST-FIXTURE-SCOPE-ADDENDUM-2026-10-04.md)، blob `0fe787204f5808b9aae843e0d5d4d94fd31b2609`. تصبح allowed_paths **ثمانية مسارات** بعد السبعة الأصلية بنفس ترتيبها. حدث **SCOPE_EXTENSION** بتاريخ `2026-10-06T19:41:02Z` على baseline `5daa0b15b8b120575ea627429b754bd655ffd346`، أثره **SCOPE_EXTENSION_ONLY_NO_RESUME**، يأتي بعد START ثم STOP_CHECKPOINT دون تغيير أي منهما أو القرارات ومراجع النطاق الأصلية.

f01a_defensive_ingress **IN_PROGRESS/false**، execution_authorized=false، **active_target محفوظ ومحسوب** في FC20-12/f01a_defensive_ingress. delivery_evidence=null وclosure_effect=NONE وDARK_OFFLINE؛ network/provider/deployment=false. التسجيل لا يسمح بتعديل الملف الثامن الآن، ولا يعيد START التاريخي. يبقى الاستئناف **NEW_OWNER_DECISION_AND_REVIEWED_EXACT_HEAD_GOVERNANCE_TRANSITION** بعد نفاذ التسجيل المراجع بدمج مصرح منفصل.

الحارس يثبت oracle مستقلًا: STOP السابق + هذه الزيادة المعتمدة وحدها؛ metadata أو fixture أو CI لا تمنح سلطة. SG-01–SG-07 تغطي النطاق والتاريخ والقرار والبصمات والموضع وعكس الفرق والمقاطع المشتقة. هذه متطلبات واختبارات هذا الطلب؛ لا ندّعي نجاحها قبل نتيجة رأسه، ولا ننقلها إلى T-01–T-09 أو T-08 أو إصلاح التطبيق.

خطة بيتا المالك والإدارة المستقلة محفوظة، FC20-05 held و#166 `2dccc2c` ثم #167 `4357770`؛ routing_repair REGISTERED_BLOCKED/false وتسع ضوابط PENDING. لا تعديل حالات الحزم أو اعتمادياتها أو release BLOCK، ولا Finance أو Snapshot أو AAS أو Decision Council أو ملفات مجمدة أو تطبيق أو ترحيل أو خدمات أو أسرار أو مصادر أو Hostinger أو دعوات أو نشر.

**التوقف الآمن:** PR التسجيل والحارس والقراءات المشتقة للمراجعة، دون دمج أو استئناف. بعد نجاح الفحوص والمراجعات يطلب دمج منفصل؛ وبعده قرار/انتقال استئناف مستقل، لا يبدأ تلقائيًا. المصدر الوحيد للحالة النافذة هو السجل المدموج، وليس هذا المقطع.

<!-- F01A-CONDITIONAL-RESUME-TRANSITION-2026-10-07 -->
### انتقال استئناف F-01A الدفاعي المشروط — مرشح 2026-10-07

- الحالة: **GOVERNANCE_TRANSITION_CANDIDATE / REVIEW_REQUIRED / NOT_EFFECTIVE_UNTIL_SEPARATE_OWNER_MERGE_APPROVAL**. هذا المقطع إسقاط مرشح لانتقال السجل؛ لا يصبح نافذًا من فتح PR أو نجاح فحص، بل بعد مراجعات الرأس وموافقة دمج منفصلة ونفاذه بالدمج. المقاطع السابقة محفوظة كتاريخ غير معاد الكتابة؛ مصدر الحالة هو السجل المدموج لا هذا النص.
- قرار المالك الحقيقي: [DECISION-FC20-12-F01A-CONDITIONAL-RESUME-2026-10-07](https://github.com/alphasigma13579-lang/ASIE/pull/187#issuecomment-6026149350)؛ وقت تسجيله `2026-10-06T21:53:52Z`، أثره `F01A_DEFENSIVE_RESUME_ONLY`، وشرطه `REVIEWED_GOVERNANCE_TRANSITION_MERGED_AFTER_SEPARATE_OWNER_MERGE_APPROVAL`. لا يعاد استخدام قرار START أو قرار تصميم النطاق أو دمج #186 كإذن استئناف.
- موضوع القرار: baseline `65efaba85e7a5ca2c944486f88c15ab95a7bd5e5`، manifest blob `7b32044eabe0fe450bf2d5ba0d2aa4dee67ad545`؛ المقترح المراجع commit `8398d9fa9f09bf04779420e50d40c1ed684051ec` وblob `bfa9d315ae66a804f9a12dcd532d05e61d841b8b`. خط إنشاء الفرع `a1f96a0e688f33cb54a80e4ca9c6eef5a97e5211` بعد دمج #187: تغير ملفا التصميم فقط، وبقي manifest مطابقًا؛ لا نقل سلطة من ancestry وحدها.
- وقت تسجيل RESUME المرشح: `2026-10-06T22:03:09Z`. الفرق الآلي الوحيد: `execution_authorized=false → execution_authorized=true`، ثم إلحاق حدث واحد؛ **f01a_defensive_ingress IN_PROGRESS/true**. يحفظ التاريخ **START → STOP_CHECKPOINT → SCOPE_EXTENSION → RESUME**؛ موضوع START وقراره الأصليان محفوظان. checkpoint وscope_extension نسختان كاملتان مثبتتان في الحدث الجديد، لا استبدال لهما.
- `active_target محفوظ ومحسوب`؛ الموضع الوحيد `FC20-12/f01a_defensive_ingress`، max_active_executions=1؛ **FC20-05 held**. يبقى شرط التوقف التاريخي `NEW_OWNER_DECISION_AND_REVIEWED_EXACT_HEAD_GOVERNANCE_TRANSITION` مستوفى بالانتقال المراجع فقط، لا بالعلم منفردًا.
- النطاق المسجل **ثمانية مسارات** فقط، نسبية لجذر الحزمة، لا توسعة من هذا الانتقال:
  - `backend/asie_local_api.py`
  - `backend/repository.py`
  - `backend/intelligence_prerun_service.py`
  - `tests/test_repository_intelligence.py`
  - `tests/test_intelligence_prerun_service.py`
  - `tests/test_intelligence_context_ingress_api.py`
  - `docs/FC20-12-F01-TRUSTED-CONTEXT-INGRESS-REPAIR-PLAN-2026-10-01.md`
  - `tests/test_live_location_api.py`
- الحدود: `delivery_evidence=null`، `closure_effect=NONE`، `DARK_OFFLINE`، `network/provider/deployment=false`؛ routing_repair **REGISTERED_BLOCKED/false** وتسعة ضوابط **PENDING**؛ FC20-12 ACR_REQUIRED واعتمادياته محفوظة، release BLOCK. لا F-01B أو توجيه أو إغلاق حزمة أو ترحيل أو شبكة أو مزود أو نشر أو دعوات.
- خطة التحقق: **RG-01–RG-08** على الرأس النهائي؛ oracle مستقل من الإيصال وليس مدخل manifest؛ عكس RESUME والعلم يعيد كامل blob #186، ثم تحقق **SG-05** التاريخي يعيد baseline السابق. تبقى اختبارات START/STOP/SCOPE_EXTENSION والـlifecycle المعزولة واختبارات الرفض؛ التاريخ ليس fallback لقبول الحالة الحالية.
- تسليم هذه الشريحة: السجل والحارس وهذه القراءات الست فقط. لا تعديل تطبيق أو ملف مجمد، ولا إدعاء نجاح T-01–T-09 من فحوص الحوكمة. نتائج الفحوص والمراجعات الفعلية تسجل في PR؛ هذه خطة قبول وليست إعلان نجاحها.
- نقطة التوقف: عرض نتيجة الانتقال المراجع وطلب موافقة الدمج المنفصلة. بعد نفاذه فقط تُعرض خطة وهدف مستقلان لإصلاح التطبيق داخل القائمة؛ T-08 كاملة وحدود توسعتها كما في المقترح الأصلي. خطة بيتا المالك والإدارة المستقلة و#166 `2dccc2c45c2b1967e277edf6db6a681a04b2654a` ثم #167 `435777008e01bafc73ab3bca86cc8945e311b610` محفوظة.

<!-- F01A-CONSUMPTION-SCOPE-REGISTRATION-2026-10-09 -->
### تسجيل نطاق استهلاك F-01A دون استئناف — مرشح 2026-10-09

الحالة: `GOVERNANCE_TRANSITION_CANDIDATE / REVIEW_REQUIRED / NOT_EFFECTIVE_UNTIL_SEPARATE_OWNER_MERGE_APPROVAL`.
هذا إسقاط مرشح لا يعيد كتابة السجلات التاريخية. لا يصبح التسجيل نافذًا إلا بعد مراجعة الرأس نفسه وموافقة دمج منفصلة من المالك؛ ويظل الاستئناف قرارًا وانتقالًا منفصلين لاحقًا.

الحالة المقترحة: `f01a_defensive_ingress IN_PROGRESS/false`، `execution_authorized=false`، `active_target محفوظ ومحسوب` دون تحرير موضع التنفيذ أو شغل موضع ثانٍ. يبقى `routing_repair REGISTERED_BLOCKED/false`، وضوابطه `PENDING`، و`FC20-05 held`.
التاريخ: `START → STOP_CHECKPOINT → SCOPE_EXTENSION → RESUME → STOP_CHECKPOINT → SCOPE_EXTENSION`؛ أول أربعة أحداث محفوظة كما هي، لا RESUME جديد.

وثيقة الانتقال: [تسجيل نطاق إصلاح الاستهلاك](FC20-12-F01A-APPROVAL-CONSUMPTION-SCOPE-REGISTRATION-2026-10-09.md).

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
مصدر هذا الإسقاط: `docs/FC20-12-F01A-DEFENSIVE-ENABLING-REGISTRATION-PROPOSAL-2026-10-01.md`؛ prefix blob `8ada62ac7aaab62dbe244be4639a05bad684a241` عند رأس الإعداد `c5f7f991f126ca9afdfa83c923635f8e01ef08f0`، بعد #195 الذي غيّر التصميم ومدخل EKB فقط دون السجل.

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
مصدر الإسقاط: `docs/FC20-12-F01A-DEFENSIVE-ENABLING-REGISTRATION-PROPOSAL-2026-10-01.md`؛ prefix blob `ba79ba386d39a9094d1d992e96462ac3ab364936` عند baseline `83afd28398c0cef9821e08c8db1162d6ec2fdfc4` بعد دمج #197. لا يغير هذا المرشح كود #189 أو SQLite.

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
مصدر الإسقاط: `docs/FC20-12-F01A-DEFENSIVE-ENABLING-REGISTRATION-PROPOSAL-2026-10-01.md`؛ prefix blob `6f14a56dfc1bfa329f793bfa012ecd1dff948117`، محفوظ بعد #198 ودون تغيير من #199. قاعدة فرع إعداد الانتقال `63b18a192e8eac3c66ad5440a667e6d1d9959d10` بعد دمج التصميم فقط؛ baseline الحاكم للاستئناف كما ثبته التصميم `37b96ec504d60f62bcdb5f4e69e0e5a0d8082f34` وmanifest blob `386687c230db26e46ad831bbaeaeddddecfae795`. لا يستبدل به الزوج التاريخي 83afd283/1cfbaf19 داخل checkpoint/scope.

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
مصدر الإسقاط `docs/FC20-12-F01A-DEFENSIVE-ENABLING-REGISTRATION-PROPOSAL-2026-10-01.md`؛ prefix blob `b9ec8c2625b3a81334cdd8d53669edcebd3f1197` محفوظ بايتًا. baseline بعد دمج #201 هو `abbdea3913630a7e940c454c46919f88c673aa0f` وmanifest blob `d76e7b0f6d18a701985469664c0cb6c1f757c869`؛ التصميم المراجع #201 عند `ae4b69ee3e56930ce1af944a2577e79e5ab44681` وblob `7aa270286535f831a8eac25170ee495043b40bf5`. كل ما سبق هذا القسم تاريخ محفوظ، بما فيه أوصاف الفهرس القديمة.

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

مصدر الإسقاط `docs/FC20-12-F01A-DEFENSIVE-ENABLING-REGISTRATION-PROPOSAL-2026-10-01.md`؛ prefix blob `97b126adc06e063ed29a3d4a856e82f7955631d6` محفوظ بايتًا. مصدر الحالة النافذة manifest على main `fcfd9222e1b47b9d95b96b589ec204b91bae8378` بعد دمج #202 عند الرأس `5af26b37986c75a5f8e014d6d69c449f93bca61e`، blob `ef142b9a2c2001e0bea4d6068b0f36d5c44c5a4c`: اثنا عشر حدثًا و`execution_authorized=false`. التصميم المقبول #201 عند `ae4b69ee3e56930ce1af944a2577e79e5ab44681` وblob `7aa270286535f831a8eac25170ee495043b40bf5` يثبت هذا الانتقال في §6–6.1؛ لا حاجة إلى طلب تصميم مستقل إضافي.

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
