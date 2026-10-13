# F-01A — مقترح اتساق مفتاح منع التكرار وبصمته المخزنة

## 1. الحالة وحد القرار

التاريخ: 2026-10-12. الحالة **DESIGN_CANDIDATE / PROPOSED / REVIEW_REQUIRED / NOT_EFFECTIVE**.

وافق المالك عند `2026-10-12T12:23:43Z` على إعداد هذا الفحص المحدد مع أثره على السجلات القديمة، ونشر تصميمه للمراجعة. هذا تلخيص المساعد لقرار الإعداد والنشر، وليس توقيعًا مستقلًا أو إذن تطبيق أو تسجيل انتقال أو استئناف أو دمج. التسليم الحالي ملفان فقط: هذه الوثيقة وإضافة رابط ملاحي إلى `docs/EKB/README-AR.md`. لا يتغير manifest أو الحارس أو التطبيق أو قاعدة بيانات.

## 2. خطا الأساس والأثر المثبت

- مصدر الحوكمة: main `2d11053a70f901a544b0fc96bcfab0c3f00d6597` بعد [#203](https://github.com/alphasigma13579-lang/ASIE/pull/203)، manifest blob `76b6d5b5892cf3a839f3fde95c04ff7ee366923f`. الحالة النافذة F01A `IN_PROGRESS/true`، ثلاثة عشر حدثًا، تسعة مسارات، عملية فهرس واحدة، موضع FC20-12/f01a_defensive_ingress واحد محفوظ ومحسوب وFC20-05 held. RESUME13 مقيد بإعادة استخدام التحقق السابق عند المراجعة/الاعتماد؛ لا يجيز هذا الشرط الجديد.
- مصدر التطبيق: [Draft #189 عند 4fcb8b47971a8ee55fa0ae95f5928bdd5722890a](https://github.com/alphasigma13579-lang/ASIE/commit/4fcb8b47971a8ee55fa0ae95f5928bdd5722890a)، tree `ce930a56c9e232dcaf1c056a0302fe83bcd8c875`؛ repository blob `429a5608a87017d5327688e71f88a0bc757f67df`. غير مدمج. فرع هذا التصميم مبني على main، لا يتضمن كود التطبيق غير المدمج.
- [Copilot5490249922](https://github.com/alphasigma13579-lang/ASIE/pull/189#pullrequestreview-5490249922) يصنف [ملاحظة المفتاح/البصمة](https://github.com/alphasigma13579-lang/ASIE/pull/189#discussion_r4247625962) High. [رد الدليل](https://github.com/alphasigma13579-lang/ASIE/pull/189#discussion_r4247656084) يوثق إعادة إنتاج اصطناعية مستقلة على رأس التطبيق السابق `3cf88c7bae98a48c5cd950df978678f452501980` والحالي: تعديل `payload_json.idempotency_key` وحده إلى نص غير فارغ يمر من قراءة الاستهلاك المتحققة والمراجعة والاعتماد واستهلاك الإيصال، مع عدم تطابق البصمة المعاد حسابها.
- في الحالتين يبقى context ID/hash والمحتوى المسقط إلى narrative كما هو؛ إعادة الطلب بالمفتاح الأصلي ترفض `context_idempotency_conflict`، وبالمفتاح المعدل مع context ID نفسه تفشل بقيد UNIQUE، ولا ينجح replay خاطئ أو تجاوز إثبات المنشأ. لم تُستدعَ جهة مزودة أو تُفحص قاعدة مالك. هذا خلل اتساق مخزن سابق للإصلاح الأخير؛ الأدلة الحالية لا تثبت تجاوز الصلاحيات أو تغيير المحتوى المعتمد أو أثرًا أمنيًا بشدة High.
- [CI رأس التطبيق](https://github.com/alphasigma13579-lang/ASIE/actions/runs/38240454473/job/114781471301): 6829 passed / 2 skipped / 10 warnings. هذه نتيجة الإصلاح السابق، لا نجاح الفحص المقترح. الخلل باقٍ وغير محلول؛ إعادة إنتاجه لا تمنح إذن إصلاحه.

## 3. المصدر القائم وحد إعادة الاستخدام

[عقد AIA-02 §6.3.1](https://github.com/alphasigma13579-lang/ASIE/blob/2d11053a70f901a544b0fc96bcfab0c3f00d6597/ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/docs/AIA-02-Intelligence-Operating-Architecture-v1.2.1.md#L315-L330) يميز قفل المحتوى وidempotency؛ §10.3 يسجل `idempotency_key_hash`، و[§34.7، البند46](https://github.com/alphasigma13579-lang/ASIE/blob/2d11053a70f901a544b0fc96bcfab0c3f00d6597/ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/docs/AIA-02-Intelligence-Operating-Architecture-v1.2.1.md#L1818-L1822) يشترط إعادة النتيجة للمدخل والمفتاح نفسيهما ورفض اختلاف المدخل. لا نفترض أن ذلك يغير تلقائيًا نطاق RESUME13 المقبول.

الدالة الأصلية [idempotency_fingerprint](https://github.com/alphasigma13579-lang/ASIE/blob/4fcb8b47971a8ee55fa0ae95f5928bdd5722890a/ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/backend/intelligence_context.py#L113-L115)، blob `0e4f5acddc3733eaa91541102f42fda9e18574a1`، موجودة كذلك في main وتعيد:

`canonical_hash({"organization_id": organization_id, "project_id": project_id, "idempotency_key": key})`.

لا normalization أو تحويل نصي داخلها. نموذج `IntelligenceContext._material` لا يدخل المفتاح في `context_hash`، ولن يغيّر هذا المقترح مادة ذلك الـhash أو الدالة الأصلية أو `snapshot_assembly`.

أما [التحقق المشترك _validated_stored_intelligence_context](https://github.com/alphasigma13579-lang/ASIE/blob/4fcb8b47971a8ee55fa0ae95f5928bdd5722890a/ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/backend/repository.py#L1655-L1681) وحده المعاملاتي فهما موجودان في خط #189 المثبت، وليسا منفذين في main/فرع التصميم. التحقق الحالي يثبت الشكل والأنواع والتطابق بين JSON والصف وlifecycle/hash، لكنه لا يعيد اشتقاق البصمة من المفتاح. [الإدراج/replay القائم](https://github.com/alphasigma13579-lang/ASIE/blob/4fcb8b47971a8ee55fa0ae95f5928bdd5722890a/ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/backend/repository.py#L1565-L1594) يحسبها عند الإدراج ويقارن المفتاح عند replay ثم يتحقق من دليل المنشأ؛ لا تعديل لهذا الاستعلام أو الإثبات هنا.

بعد بوابات النطاق والاستئناف فقط، يستمر التنفيذ على #189 أو خلف متحقق، مع إدخال main الحاكم بأمان، دون اشتراط دمج #189 مسبقًا. غياب helper أو تغير دلالته عن المصدر المثبت يعيد قرار التصميم؛ لا يعاد إنشاء تنفيذ موازٍ على main.

## 4. الدلتا المستقبلية وحد التوافق — غير منفذة

يقترح فحص واحد إضافي داخل helper المشترك القائم، بعد تحقق الشكل والأنواع وتطابق هوية JSON والصف، وقبل قبول النموذج وإرجاعه:

1. استعمال `organization_id` و`project_id` و`idempotency_key` المخزنة التي اجتازت تحقق النص غير الفارغ وتطابق الهوية مع الصف. لا قيم من body أو caller بديل، ولا `str()` أو coercion أو تسامح bool/int أو resolver جديد.
2. استدعاء `idempotency_fingerprint` القائمة مرة بالقيم النصية الأصلية الدقيقة؛ مقارنة الناتج ببصمة payload وبصمة الصف. تطابق الاثنتين مع بعضهما لا يكفي إذا خالفتا الاشتقاق.
3. لا trim/lowercase/Unicode normalization ولا قطع طول؛ المفتاح النصي الصالح الذي يحتوي مسافات حول نص أو Unicode يحتفظ ببايتات/قيم النص نفسها. تبقى قيود الإدخال الحالية، ولا تضاف حدود طول أو قواعد تسمية جديدة. تحقق عدم فراغ `.strip()` لا يعني استعمال القيمة المقصوصة في الحساب.
4. عدم الاتساق يرفض عبر الحدود القائمة: `context_integrity_invalid` في getter المخصص للاستهلاك، و`context_not_review_eligible` عند حفظ المراجعة/الاعتماد. يبقى HTTP narrative على استجابة الاعتماد المطلوبة القائمة409، وHTTP المراجعة/الاعتماد invalid/400؛ لا عقد أو route جديد، ولا كشف تشخيص داخلي. تبقى أخطاء التخزين غير المتوقعة ظاهرة كأخطاء داخلية وفق معالجها، ولا يعاد تصنيفها قبولًا أو تلف سجل.
5. يبقى صف المعاملة نفسه عند الحفظ، وموضع getter القائم عند الاستهلاك؛ لا اتصال جديد أو getter متداخل أو مصدر ثقة آخر. لا تعديل receipt/overlay أو scope/conditions أو provider admission.

**التوافق المقصود، ويحتاج قبولًا صريحًا:** السجل الأصلي الصحيح، بما فيه القديم بلا origin proof جديد، يبقى صالحًا إذا تطابق الاشتقاق. السجل غير المتسق الذي كان يمر من هذه الحدود سيرفض بعدها، حتى لو كان context_hash والإيصال صالحين لمحتواه. لا إلغاء/حذف/تعديل للإيصالات المحفوظة؛ بوابة قراءة السياق المتحققة هي التي ترفضه في مسار الاستهلاك الحالي. دالة `consume_intelligence_approval` لا تبدأ قراءة سياق جديدة ولا تتغير ضمن هذا الفحص.

القراءة التاريخية العادية (`validate_for_consumption=False`) وعقدها السابق محفوظان؛ ليست ترقية تلقائية للقراءة إلى اعتماد. لا origin proof إلزامي جديد للسجلات الأصلية القديمة، ولا backfill أو إعادة ختم أو إعادة كتابة مفتاح/بصمة أو حذف أو “تصحيح” تلقائي. وجود سجلات غير متسقة في قاعدة المالك UNKNOWN ولم يُقَس. أي معالجة بيانات فعلية قرار منفصل؛ هذا المقترح لا يصف ترحيلًا أو مسار استعادة تنفيذيًا.

هذا **فحص اتساق مشتق، لا إثبات منشأ أو حماية من تعديل قاعدة البيانات بامتياز مباشر**. تعديل المفتاح وبصمتي JSON/الصف معًا بصورة متسقة لا يكشفه هذا الشرط وحده؛ لا نعوض ذلك بإضافة proof تاريخي أو مصدر جديد. تبقى سياسة replay ودليلها كما هي. لا يتغير محتوى context_hash أو معنى الاعتماد.

## 5. قائمة التطبيق والقبول المستقبلي — NOT_IMPLEMENTED / NOT_RUN

الملفان فقط بعد نفاذ التسجيل والاستئناف:
- `backend/repository.py`: شرط الاشتقاق داخل helper المشترك، بلا تغيير الدالة الأصلية أو API/schema/index/SQL/proof.
- `tests/test_repository_intelligence.py`: حالات مستقلة للقراءة المتحققة وحفظ المراجعة وحفظ الاعتماد؛ تنشأ مراجعة صحيحة قبل إفساد سياق اختبار الاعتماد.

المصفوفة المطلوبة:
- مفتاح معدل وحده؛ بصمتا payload/row معدلتان معًا دون المفتاح؛ بصمة payload أو الصف وحدها مخالفة؛ جميعها ترفض بالرسالة المحددة قبل اعتماد جديد.
- missing/null/bool/int/list/dict/فارغ/مسافات فقط في المفتاح أو هوية org/project، مع إثبات رفضها قبل استدعاء دالة الاشتقاق، وحفظ اختبارات الشكل والصف والـhash السابقة.
- نص صحيح ومفتاح Unicode ومفتاح بمسافات محفوظة: حساب بالدالة الأصلية دون normalization وقبول مشروع؛ رفض إعادة اشتقاق بمفتاح مقصوص أو مؤسسة/مشروع آخر.
- سجل أصلي متسق بلا proof جديد يمر من القراءة المتحققة والمراجعة/الاعتماد؛ سجل غير متسق يبقى قابلًا للقراءة التاريخية المسموحة دون تصحيح أو proof رجعي، ويرفض عند الحدود المتحققة فقط.
- نفس الصف والاتصال المعاملاتي، auth/tenant/project قبل القراءة/الاشتقاق، عدم getter أو اتصال بديل؛ فشل التحقق لا يغير السياق/المراجعات السابقة/الإيصالات/دليل المنشأ. لا منع للتدقيق المصرح القائم.
- اختبارات replay الأصلي وإثبات المنشأ وCAS وC01–C03 والفهرس تبقى ناجحة دون تعديل دلالتها؛ لا تُحوّل إعادة الطلب الفاشلة لسجل تالف إلى نجاح ولا تستنتج منه قبول البيانات.
- إعادة تشغيل اختبارات HTTP/narrative القائمة دون تعديل ملفاتها لإثبات ثبات العقد وعدم اتصال بمزود. أي حاجة مثبتة إلى مسار أو سلوك آخر توقف الجزء المتأثر قبل توسيعه.
- red مستهدف للفحص الجديد ثم green على الرأس النهائي، compilation، CI والمراجعات exact-head. أدلة §2 تخص الفجوة/الرأس السابق ولا تحل محل هذه الاختبارات.

لا يدخل إصلاح تصنيف أخطاء `ReviewOverlay` المؤجل في هذا النطاق؛ [CodeRabbit أكد أنه غير مانع ومؤجل وغير محلول](https://github.com/alphasigma13579-lang/ASIE/pull/189#discussion_r4247639275).

## 6. التسجيل والاستئناف اللاحقان وحد السلطة

يحكمهما [عقد التسجيل §4](FC20-12-F01A-DEFENSIVE-ENABLING-REGISTRATION-PROPOSAL-2026-10-01.md) و[ملحق الاستهلاك §6](FC20-12-F01A-APPROVAL-CONSUMPTION-SCOPE-ADDENDUM-2026-10-09.md). موافقة إعداد ونشر هذا التصميم لا تسجل STOP أو توسعة أو RESUME، ولا تجعل true الحالية إذنًا للفحص الجديد.

بعد مراجعة رأس التصميم، يلزم قبول مالك محدد لأثر التوافق وموافقة دمج التصميم المنفصلة، ثم قرار إعداد/نشر تسجيل محدد مع إيصال GitHub حقيقي. يقترح التسجيل المنفصل، إذا ظل baseline أعلاه دون تغير: حفظ الأحداث الثلاثة عشر كاملين ثم STOP_CHECKPOINT14 وSCOPE_EXTENSION15، وإبقاء `IN_PROGRESS/false` والموضع الواحد محفوظًا ومحسوبًا. `added_paths=[]`، المسارات التسعة بالترتيب محفوظة، وعملية الفهرس الوحيدة byte-exact بلا عملية schema جديدة. لا RESUME أو DELIVERED في التسجيل.

موضوع القرار المقترح المغلق تحت `owner_scope_decision.subject.repair_scope`، وليس صلاحية نافذة أو API:

```json
{
  "purpose": "STORED_CONTEXT_KEY_FINGERPRINT_BINDING_ONLY",
  "implementation_paths": ["backend/repository.py", "tests/test_repository_intelligence.py"],
  "boundary": "EXISTING_SHARED_STORED_CONTEXT_VALIDATOR",
  "validation": "RECOMPUTE_EXISTING_FINGERPRINT_FROM_TYPED_EXACT_STORED_ORG_PROJECT_KEY",
  "affected_gates": ["VALIDATED_CONTEXT_CONSUMPTION_READ", "TRANSACTIONAL_REVIEW_SAVE", "TRANSACTIONAL_APPROVAL_SAVE"],
  "compatibility": "REJECT_INCONSISTENT_BINDING_WITHOUT_REWRITE_OR_BACKFILL",
  "historical_read_and_origin_proof_policy": "UNCHANGED",
  "native_context_hash_and_fingerprint_function": "UNCHANGED",
  "additional_schema_operations": [],
  "database_and_data_scope": "DISPOSABLE_TEMPORARY_DATABASES_SYNTHETIC_DATA_ONLY"
}
```

يثبت موضوع القرار رأس التصميم وblob الحقيقيين، baseline/manifest blob، رأس التطبيق، التاريخ السابق، والشرط الجديد وحد التوافق كاملًا؛ لا يكفي اسم الملفين. لا يستبدل نطاق الحدث12 تاريخيًا ولا قرار RESUME13؛ التاريخ محفوظ ويضاف موضوع جديد. يلزم oracle مستقل مغلق يرفض أي قيمة/نوع/حقل زائد أو أثر أوسع وإعادة استخدام قرار الإعداد أو RESUME13 كإذن جديد.

ملفات التسجيل السبعة القائمة فقط: `/FOUNDATION-COMPLETE-20.json`، `tests/test_foundation_complete_20_program.py`، وثيقة FOUNDATION، `docs/EKB/FOUNDATION-COMPLETE-20-PACKAGE-INDEX.md`، خطة بيتا المالك، وثيقة تسجيل F01A، ووثيقة تسجيل نطاق الاستهلاك. المسارات غير الجذرية نسبية للحزمة، وتثبت أسماؤها وprefix/blob لكل إسقاط قبل التحرير. العكس الكامل للتسجيل يعيد manifest `76b6d5b5892cf3a839f3fde95c04ff7ee366923f` ثم سلسلة RIRG→RISG→IRG→ISG→CRG→CS→RG→SG دون تخفيف؛ أختام بايتية مستقلة ومراجعة رأس نهائي لا مقارنة جزئية. إذا تغير baseline، يعاد تثبيته قبل التسجيل ولا يفترض عدد الأحداث.

بعد مراجعة التسجيل واعتماد دمجه ونفاذه فقط: قرار تنفيذ جديد مقيد بهذا الفحص والرفض والتوافق والملفين، ثم انتقال RESUME16 مستقل مراجع وموافقة دمجه المنفصلة قبل الكود. ينسخ STOP14/SCOPE15 كاملين والنطاق والقوائم والعملية، ويقيد الأنشطة بتطوير/اختبار ربط المفتاح بالبصمة فقط، على قواعد مؤقتة وبيانات اصطناعية. تبقى live/owner database وproduction placement/deployment/application-PR-merge false، ومعايير startup/maintenance/recovery UNKNOWN_NOT_APPROVED. لا حاجة إلى وثيقة تصميم RESUME أخرى إذا حسم هذا التصميم المقبول تلك القيود؛ أي تصميم إضافي يحتاج مسألة فعلية غير محسومة.

## 7. التوقف والتراجع

التسليم الآمن الحالي: تصميم من ملفين منشور للمراجعة، بلا كود أو انتقال نافذ. عكس الفحص مستقبلًا يعيد قبول عدم الاتساق السابق، ولا يعد استعادة أمان مكافئة؛ لا حذف بيانات أو إسقاط فهرس ضمن التراجع. يبقى T08 OPEN، release BLOCK، DARK_OFFLINE، routing REGISTERED_BLOCKED/false وضوابطه التسعة PENDING، وnetwork/provider/deployment=false. لا F01B أو مسار موازٍ أو تغيير Finance/Snapshot/AAS/Decision Council أو دمج #189.
