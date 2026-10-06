# FOUNDATION-COMPLETE-20 Package Index

This is an EKB navigation view, not a parallel status authority.

- Human program authority: `../FOUNDATION-COMPLETE-20-CORE-INTELLIGENCE-COMPLETION-PROGRAM-2026-07-29.md`
- Machine package/status/dependency authority: `/FOUNDATION-COMPLETE-20.json`
- Release/remediation authority: `../PROGRAM-CLOSE-10-EMERGENCY-REMEDIATION-CONSOLIDATION-AND-REBASELINE-2026-07-29.md` and `/EMERGENCY-RELEASE-FREEZE.json`

Package IDs are `FC20-01` through `FC20-16`. Do not create a separate package-status document. Update the machine manifest atomically with implementation and exact-commit evidence.

## FC20-12 routing slice — blocked evidence register

- Machine location: `/FOUNDATION-COMPLETE-20.json → packages[FC20-12].execution_slices[routing_repair]`.
- Current state: **`REGISTERED_BLOCKED` / `EVIDENCE_TRACKING_ONLY`** under `asie.foundation.routing-eligibility.v2`; historical blocked v1 remains compatible. This is not build eligibility.
- [Owner ordering decision](https://github.com/alphasigma13579-lang/ASIE/pull/171#issuecomment-5851434784); [pinned proposal](https://github.com/alphasigma13579-lang/ASIE/blob/d8fdedd8c768c0eb4604465fdcf870417131aff0/ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/docs/FC20-12-ROUTING-SCOPE-CHANGE-2026-09-27.md).
- Human explanation and entry-control ownership: the program's “FC20-12 routing registration” section.
- [Routing ACR](../ACR-AIA-ROUTING-REMEDIATION-2026-09-27.md) remains proposed; specialist/frozen approvals are not inferred from owner ordering consent.
- Checker: `tests/test_foundation_complete_20_program.py` rejects executable claims under v1 and current v2. [Design-only owner decision](https://github.com/alphasigma13579-lang/ASIE/pull/176#issuecomment-5898867883) permits this guard PR only; exact-head evidence, specialist/owner decisions and a separately reviewed transition are needed for eligibility. CI consistency is not approval.
- Parent dependencies FC20-08/09/11, all 16 package states/completion evidence, and FC20-16 release gates stay unchanged. FC20-05 remains recorded IN_PROGRESS; the later ordering/hold record below separates retained progress from active execution.
- No runtime, provider, secret, data migration, or Hostinger authority is granted.

This is navigation to the machine record, not an alternative current-state ledger. [PR #171](https://github.com/alphasigma13579-lang/ASIE/pull/171) was merged into `main` at [`25a82786d874aea6c37afa2f982210299d9edd10`](https://github.com/alphasigma13579-lang/ASIE/commit/25a82786d874aea6c37afa2f982210299d9edd10) as the documentation predecessor. That merge does not approve the routing ACR, grant build eligibility, or authorize frozen-runtime changes, providers, deployment, or invitations.

## F-01 trusted-context ingress — proposed defensive enabling scope

- [خطة حماية مدخل سياق المشروع — 2026-10-01](../FC20-12-F01-TRUSTED-CONTEXT-INGRESS-REPAIR-PLAN-2026-10-01.md): **PROPOSED / REVIEW_REQUIRED / NOT_BUILD_READY**؛ تحدد رفض الحالة/البصمة الخام وDraft خادميًا، وأثر توقف Pre-Run الخام قبل استعادة بناء موثوق بعقد منفصل.
- لا تصريح كود أو دمج أو تفعيل، ولا تغيير للسجل أو أهلية routing_repair أو إغلاق FC20-08/09/11. نقطة القرار هي نطاق F-01A وأثره؛ نجاح الحماية لاحقًا ليس اكتمال F-01 أو الضوابط التسعة.

## Routing entry approval pack — proposed only

- [حزمة اعتماد دخول إصلاح التوجيه](../FC20-12-ROUTING-ENTRY-APPROVAL-PACK-2026-09-28.md): **PROPOSED / REVIEW_REQUIRED / NOT_BUILD_READY**؛ تجمع متطلبات القرارات والأدلة التسع وترتيب FC20-05 والاختبارات، وليست مصدر حالة أو تصريح بناء.
- تُقرأ قبل إعداد انتقال أهلية التوجيه مع البرنامج والسجل وACR وطلب النطاق؛ لا تغيّر أي حالة أو اعتماد أو مخطط تحقق. دمج الحزمة كمقترح لا يغلق بوابة أو يفتح تنفيذًا أو شبكة أو نشرًا.

## Routing priority / retained FC20-05 work — owner decision, governance review

- [قرار الأولوية وcheckpoint](../FC20-ROUTING-PRIORITY-AND-FC20-05-CHECKPOINT-2026-09-28.md) و[سجل المالك](https://github.com/alphasigma13579-lang/ASIE/pull/173#issuecomment-5865171335): إعداد تغيير حاكم واختباراته فقط، لا دمج أو بناء.
- Machine authority: `/FOUNDATION-COMPLETE-20.json → execution_sequence`؛ **PRIORITY_AND_HOLD_ONLY**، FC20-05 held with progress IN_PROGRESS, routing priority blocked, active slot empty.
- No parent closure or release effects. This view is navigation only; specialized approvals and actual entry evidence remain required.

## Routing entry evidence after #174 — derived snapshot only

- [دليل مطابقة دخول إصلاح التوجيه — 2026-09-29](../FC20-12-ROUTING-ENTRY-EVIDENCE-2026-09-29.md): **PROPOSED / REVIEW_REQUIRED / NOT_BUILD_READY**؛ يكمل حزمة الدخول القائمة على main@`702dfdb68f4cfd6975fb2874f841bc27c79dc85c`، بدءًا من سلطة مزامنة البرنامج والأدلة الناقصة للضوابط التسعة.
- مصدر الحالات يبقى السجل الآلي. مطابقة التسجيل والأولوية ليست أهلية بناء؛ لا PASS أو تعديل مخطط أو تنفيذ أو اعتماد ACR أو تحرير إصدار من هذا الدليل أو دمجه. يقرأ قبل إعداد انتقال أهلية لاحق، مع البرنامج والسجل وACR وطلب النطاق.

## Routing eligibility transition — proposal only

- [مقترح انتقال أهلية التوجيه — 2026-09-29](../FC20-12-ROUTING-ELIGIBILITY-PROPOSAL-2026-09-29.md): **PROPOSED / REVIEW_REQUIRED / NOT_BUILD_READY**؛ بعد #175، يحدد دليل الدخول وقرار البدء ودليل التسليم المقترحة، وقائمة ملفات/فحوص تطبيق حاكم مستقل.
- لا يغير schema/status/control/slot الحالية ولا يوافق على ACR أو كود مجمد؛ شروط الدخول التسعة و08/09/11 لإغلاق الأب وFC20-16 وخطة المالك وcheckpoint محفوظة. يقرأ بعد حزمة الدخول ودليل المطابقة؛ قبول التصميم ليس تشغيلًا أو نشرًا.

## Exact-head entry audit after #177 — derived snapshot only

- [تدقيق ضوابط دخول التوجيه التسعة — 2026-09-30](../FC20-12-ROUTING-ENTRY-EXACT-HEAD-AUDIT-2026-09-30.md): قراءة ساكنة على `main@9a1d2698fde7f104c5bb74feacb28087bbf2b3a3`، تفصل المكونات الموجودة عن دليل الدخول غير المتحقق. لا تغيّر السجل أو تمنح أهلية أو تنفيذًا.

## F-01A defensive enabling registration — proposal only

- [مقترح تسجيل التمكين الدفاعي — 2026-10-01](../FC20-12-F01A-DEFENSIVE-ENABLING-REGISTRATION-PROPOSAL-2026-10-01.md): **PROPOSED / REVIEW_REQUIRED / NOT_BUILD_READY**؛ شريحة محدودة داخل البرنامج نفسه مع عد التنفيذ الواحد وحفظ routing_repair محجوبًا.
- [اعتماد نطاق F-01A وأثر التوافق](https://github.com/alphasigma13579-lang/ASIE/pull/179#issuecomment-5920890935) محفوظ؛ موضوع القرار التالي شكل التسجيل والحارس، لا إعادة قبول النطاق. لم يتغير JSON أو الحارس أو التطبيق بهذا المقترح.
- التسجيل والبدء والتسليم انتقالات منفصلة بأدلتها؛ لا PASS لضوابط التوجيه أو إغلاق حزم أو تفعيل/نشر/ترحيل/دعوات من وثيقة أو CI. هذا مدخل قراءة، وليس مصدر حالة موازٍ.


## F-01A blocked registration candidate — 2026-10-01

- [التصميم المعتمد](../FC20-12-F01A-DEFENSIVE-ENABLING-REGISTRATION-PROPOSAL-2026-10-01.md) و[قرار المالك](https://github.com/alphasigma13579-lang/ASIE/pull/180#issuecomment-5921569549): إعداد طلب السجل والحارس، لا دمج أو بدء.
- موقع المرشح: /FOUNDATION-COMPLETE-20.json → packages[FC20-12].execution_slices[f01a_defensive_ingress]؛ **REGISTERED_BLOCKED** وstart_decision=null والتنفيذ false.
- execution_sequence v2 أثرها **BOUNDED_DEFENSIVE_ENABLING_ONLY**؛ active_target = null. يبقى routing_repair محجوبًا وسجل ضوابطه دون تغيير. هذه قراءة مشتقة لمرشح، وليست حالة برنامج موازية أو صلاحية تشغيل.
- fixture انتقال البدء/التسليم معزول ولا يقبل داخل السجل الحالي؛ أي انتقال حقيقي يتطلب قرارًا مثبتًا وفرق حارس مراجع. FC20-05 held وcheckpoint 166/167 والبرنامج والإصدار BLOCK محفوظة. لا تطبيق أو شبكة أو مزود أو نشر أو ترحيل أو دعوات.

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

## F-01A test-fixture scope registration — proposal only, 2026-10-06

- [مقترح تسجيل توسعة ملف الاختبار](../FC20-12-F01A-TEST-FIXTURE-SCOPE-REGISTRATION-PROPOSAL-2026-10-06.md): **PROPOSED / REVIEW_REQUIRED / NOT_EFFECTIVE**؛ يقرأ بعد ملحق #183 وتسجيل التوقف #184. يحدد إضافة tests/test_live_location_api.py وحده وتصميم سجل التوسعة واختبارات حارسها، دون تغيير المصدر الحالي.
- main المحقق عند الإعداد 6c3806aa6cba7870253866497d4b31df194f20f9؛ السجل الحالي يحفظ F01A بحالة IN_PROGRESS/false وموضعه محسوبًا. القرار المحدد للنطاق والتصميم لم يسجل هنا؛ «التالي» إعداد مقترح لا قرار نفاذ أو استئناف.
- PR التسجيل والحارس لاحق بعد القرار والمراجعة؛ يبقى الاستئناف قرارًا وانتقالًا مستقلين. لا تعديل التطبيق أو السجل أو الحارس في هذا المقترح، ولا تخفيض T-01–T-09 أو T-08، ولا تفعيل أو نشر أو دعوات. خطة المالك و#166/#167 محفوظة؛ هذا مدخل قراءة وليس مصدر حالة موازٍ.

<!-- F01A-SCOPE-EXTENSION-2026-10-06 -->
### تسجيل توسعة F-01A دون استئناف — مرشح 2026-10-06

هذه قراءة مشتقة من /FOUNDATION-COMPLETE-20.json؛ **REGISTRATION_CANDIDATE / REVIEW_REQUIRED / NOT_EFFECTIVE_UNTIL_SEPARATE_OWNER_MERGE_APPROVAL**. التاريخ السابق محفوظ، ولا تُقرأ حالة المقترح عند إنشائه بوصفها الحالة الأحدث. [تصميم التسجيل المراجع #185](https://github.com/alphasigma13579-lang/ASIE/blob/1213fe78da66072a246c8592e69b5f4ebb91b22a/ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/docs/FC20-12-F01A-TEST-FIXTURE-SCOPE-REGISTRATION-PROPOSAL-2026-10-06.md)، blob `eeaf6354a9fc8b790812cb876cb95d4574bb562b`، مدموج عند `5daa0b15b8b120575ea627429b754bd655ffd346`.

قرار النطاق والتصميم `DECISION-FC20-12-F01A-TEST-FIXTURE-SCOPE-DESIGN-2026-10-06` محفوظ في https://github.com/alphasigma13579-lang/ASIE/pull/185#issuecomment-6023988634، وقت تسجيل الإيصال `2026-10-06T19:34:56Z`؛ موضوعه الرأس `1213fe78da66072a246c8592e69b5f4ebb91b22a` وأثره **SCOPE_DESIGN_APPROVED_NO_MERGE_NO_RESUME**. الإيصال ينقل موافقة المالك في المحادثة؛ ليس توقيع هوية مشفرًا ولا موافقة دمج هذا التسجيل.

الزيادة الوحيدة `tests/test_live_location_api.py`، لتجهيز الاختبارات التابعة فقط حسب [ملحق النطاق #183](https://github.com/alphasigma13579-lang/ASIE/blob/23659956064e6750edbf7ef0ffb7f812ae05b985/ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/docs/FC20-12-F01A-TEST-FIXTURE-SCOPE-ADDENDUM-2026-10-04.md)، blob `0fe787204f5808b9aae843e0d5d4d94fd31b2609`. تصبح allowed_paths **ثمانية مسارات** بعد السبعة الأصلية بنفس ترتيبها. حدث **SCOPE_EXTENSION** بتاريخ `2026-10-06T19:41:02Z` على baseline `5daa0b15b8b120575ea627429b754bd655ffd346`، أثره **SCOPE_EXTENSION_ONLY_NO_RESUME**، يأتي بعد START ثم STOP_CHECKPOINT دون تغيير أي منهما أو القرارات ومراجع النطاق الأصلية.

f01a_defensive_ingress **IN_PROGRESS/false**، execution_authorized=false، **active_target محفوظ ومحسوب** في FC20-12/f01a_defensive_ingress. delivery_evidence=null وclosure_effect=NONE وDARK_OFFLINE؛ network/provider/deployment=false. التسجيل لا يسمح بتعديل الملف الثامن الآن، ولا يعيد START التاريخي. يبقى الاستئناف **NEW_OWNER_DECISION_AND_REVIEWED_EXACT_HEAD_GOVERNANCE_TRANSITION** بعد نفاذ التسجيل المراجع بدمج مصرح منفصل.

الحارس يثبت oracle مستقلًا: STOP السابق + هذه الزيادة المعتمدة وحدها؛ metadata أو fixture أو CI لا تمنح سلطة. SG-01–SG-07 تغطي النطاق والتاريخ والقرار والبصمات والموضع وعكس الفرق والمقاطع المشتقة. هذه متطلبات واختبارات هذا الطلب؛ لا ندّعي نجاحها قبل نتيجة رأسه، ولا ننقلها إلى T-01–T-09 أو T-08 أو إصلاح التطبيق.

خطة بيتا المالك والإدارة المستقلة محفوظة، FC20-05 held و#166 `2dccc2c` ثم #167 `4357770`؛ routing_repair REGISTERED_BLOCKED/false وتسع ضوابط PENDING. لا تعديل حالات الحزم أو اعتمادياتها أو release BLOCK، ولا Finance أو Snapshot أو AAS أو Decision Council أو ملفات مجمدة أو تطبيق أو ترحيل أو خدمات أو أسرار أو مصادر أو Hostinger أو دعوات أو نشر.

**التوقف الآمن:** PR التسجيل والحارس والقراءات المشتقة للمراجعة، دون دمج أو استئناف. بعد نجاح الفحوص والمراجعات يطلب دمج منفصل؛ وبعده قرار/انتقال استئناف مستقل، لا يبدأ تلقائيًا. المصدر الوحيد للحالة النافذة هو السجل المدموج، وليس هذا المقطع.

## F-01A conditional resume after #186 — proposal only, 2026-10-06

- [مقترح الاستئناف الدفاعي المشروط](../FC20-12-F01A-CONDITIONAL-RESUME-PROPOSAL-2026-10-06.md): **PROPOSED / REVIEW_REQUIRED / NOT_EFFECTIVE**؛ يقرأ بعد تصميم/تسجيل توسعة #185/#186 وعقد التسجيل وملحق #183. لا يغيّر هذا المقترح المصدر الآلي أو الحارس أو التطبيق.
- أحدث baseline المحقق لهذا المقطع: `65efaba85e7a5ca2c944486f88c15ab95a7bd5e5` بعد [إثبات دمج #186](https://github.com/alphasigma13579-lang/ASIE/pull/186#issuecomment-6025070236). أصبحت قائمة الثماني مسارات نافذة؛ ما زال F01A IN_PROGRESS/false والموضع محفوظًا ومحسوبًا، والسجل يحفظ START ثم STOP_CHECKPOINT ثم SCOPE_EXTENSION دون RESUME. حالات المرشحين أعلاه تاريخية؛ المصدر الحالي /FOUNDATION-COMPLETE-20.json، لا هذا المدخل.
- القرار التالي: تصميم استئناف محدد مشروط بانتقال حاكم مراجع ودمج مصرح منفصل؛ طلب إعداد المقترح لا يسجل موافقة الاستئناف. لا إعادة استخدام START القديم أو موافقة دمج #186، ولا تغيير ضوابط التوجيه أو اعتماديات الأب أو FC20-05 held أو checkpoint #166/#167.
- يحدد المقترح فرق العلم/حدث RESUME واختبارات RG-01–RG-08 للانتقال اللاحق مع حفظ SG والتاريخ؛ T-01–T-09 وT-08 كاملة لإصلاح التطبيق لاحقًا. لا تنفيذ أو دمج أو شبكة أو مزود أو أسرار أو بيانات أو نشر أو دعوات؛ خطة بيتا المالك والإدارة المستقلة محفوظة.

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
