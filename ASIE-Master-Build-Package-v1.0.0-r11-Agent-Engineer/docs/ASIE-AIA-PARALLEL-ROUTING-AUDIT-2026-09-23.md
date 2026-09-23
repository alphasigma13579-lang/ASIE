# تدقيق مسارات الذكاء الموازية — ASIE (2026-09-23)

| الحقل | القيمة |
|---|---|
| النوع | سجل تحقيق ساكن، لا عقد تغيير ولا تصريح تشغيل |
| أساس الفحص | main عند 435777008e01bafc73ab3bca86cc8945e311b610 بعد دمج #166 ثم #167 |
| النطاق | سند، السوق والموقع، التفسير، سياق Pre-Run، عقود AIA وEKB |
| الحالة | نتائج كود موثقة؛ التحقق التشغيلي الحي غير منجز |
| سلطة الإصدار | PROGRAM-CLOSE-10 وEMERGENCY-RELEASE-FREEZE.json، لا هذه الوثيقة |

## الحكم المختصر

المخالفة المثبتة هي وجود مسارات API إنتاجية الشكل تستدعي خدمة السوق أو المزود أو مستودع سياق الذكاء مباشرة، خارج انتقال AAS/Bus/Socket/Module Runtime الذي تشترطه AIA-01 وAIA-02. ليست «سند» الظاهر للمستخدم هي هذا المسار؛ فهو مساعد تنقل محلي. وجود صلاحيات وعزل وضوابط مزودات في المسارات المباشرة يقلل بعض المخاطر لكنه لا يعوض مخالفة الحد المعماري. لم يثبت هذا الفحص تشغيل طلب خارجي فعليًا على Hostinger، ولا تعديل Finance أو Snapshot أو Decision Council، ولا يفسر وحده جميع انحرافات المنتج.

## العقد المقابل

- [AIA-01، القسم 5.1](https://github.com/alphasigma13579-lang/ASIE/blob/435777008e01bafc73ab3bca86cc8945e311b610/ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/docs/AIA-01-Intelligence-Constitution-v1.0.0.md#L136-L153) يمنع تجاوز Bus/Socket واستدعاء Module مباشرة أو إنشاء Runtime بديل.
- [AIA-02، الثوابت وProduction Pre-Run](https://github.com/alphasigma13579-lang/ASIE/blob/435777008e01bafc73ab3bca86cc8945e311b610/ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/docs/AIA-02-Intelligence-Operating-Architecture-v1.2.1.md#L219-L320) يطلب عبور الرسائل الإنتاجية AAS؛ ويجعل Pre-Run داخل AAS بعد ACR، لا مسارًا مستقلًا إلى Repository.
- [AIA-02، Trusted Prompt Assembly](https://github.com/alphasigma13579-lang/ASIE/blob/435777008e01bafc73ab3bca86cc8945e311b610/ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/docs/AIA-02-Intelligence-Operating-Architecture-v1.2.1.md#L1459-L1480) يجعل AI Integration Shell بوابة الذكاء الوحيدة.
- [ACR-FC20-11](https://github.com/alphasigma13579-lang/ASIE/blob/435777008e01bafc73ab3bca86cc8945e311b610/ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/docs/ACR-FC20-11-OWNER-LIVE-MARKET-CONTEXT-2026-09-02.md) يقبل مسار مالك مشروطًا ببوابات التفعيل ويقول إنه لا يغيّر AAS؛ لا ينص على استثناء يسمح بتجاوزه. أي تعارض يُحسم بعقد أعلى أو ACR صريح، لا بافتراض استثناء.
- [PROGRAM-CLOSE-10](https://github.com/alphasigma13579-lang/ASIE/blob/435777008e01bafc73ab3bca86cc8945e311b610/ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/docs/PROGRAM-CLOSE-10-EMERGENCY-REMEDIATION-CONSOLIDATION-AND-REBASELINE-2026-07-29.md) لا يمنح نشرًا عامًا أو تشغيل مزودات/شبكة لمجرد نجاح الكود أو وجود مفتاح.

## المسارات المرصودة والبيانات

| المسار | من أين يبدأ وإلى أين يذهب | المدخلات الخارجة أو المكتوبة | ما يعود ولمن | الضبط الموجود والفجوة |
|---|---|---|---|---|
| سند | [الواجهة المحلية](https://github.com/alphasigma13579-lang/ASIE/blob/435777008e01bafc73ab3bca86cc8945e311b610/ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/src/ASIECompleteSurfaceMount.tsx#L292-L398) تنقل بين مراحل وتطلب فتح المدخل الناقص | موضع التنقل واسم المدخل في حالة الواجهة | تعليمات انتقال للمستخدم نفسه | لا استدعاء HTTP أو AI ظاهر في هذا المكوّن؛ ليس سبب التجاوز المرصود |
| سياق السوق | [LiveCockpit](https://github.com/alphasigma13579-lang/ASIE/blob/435777008e01bafc73ab3bca86cc8945e311b610/ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/src/LiveCockpit.tsx#L1-L95) → [API](https://github.com/alphasigma13579-lang/ASIE/blob/435777008e01bafc73ab3bca86cc8945e311b610/ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/backend/asie_local_api.py#L2227-L2307) → [LiveIntelligenceProductService](https://github.com/alphasigma13579-lang/ASIE/blob/435777008e01bafc73ab3bca86cc8945e311b610/ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/backend/live_intelligence_product.py#L141-L272) → Tavily/Google/Pinecone | عبارة بحث حرة إلى Tavily/Pinecone، وعبارة موقع وإحداثيات المشروع المؤكدة إلى Google | مرشحو مصادر وأماكن ونتائج معرفة بحالة مراجعة، للمستخدم المصرح عبر API | إذن platform.manage ونطاق المستأجر/المشروع والإيقاف موجودة؛ لا عبور AAS/Bus/Socket. النتائج ليست مدخلات Finance معتمدة |
| الموقع والمنافسون | [API](https://github.com/alphasigma13579-lang/ASIE/blob/435777008e01bafc73ab3bca86cc8945e311b610/ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/backend/asie_local_api.py#L2418-L2514) → GoogleLocationClient | عنوان أو إحداثيات مؤكدة وعبارة/نطاق بحث المنافسين | Geocode أو أماكن للمستخدم المصرح | تحقق الإذن وتطابق إحداثيات المشروع موجود؛ الاستدعاء المباشر خارج حد الوحدة المعمارية |
| التفسير | [API](https://github.com/alphasigma13579-lang/ASIE/blob/435777008e01bafc73ab3bca86cc8945e311b610/ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/backend/asie_local_api.py#L2308-L2415) → Repository context/receipt → [الخدمة](https://github.com/alphasigma13579-lang/ASIE/blob/435777008e01bafc73ab3bca86cc8945e311b610/ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/backend/live_intelligence_product.py#L275-L336) → DeepSeekNarrativeClient | قالب خادمي + بيانات وصفية لأدلة معتمدة ومراجعها، لا ملف المشروع الكامل بحسب المسار المفحوص | نص تفسير مع حالة مراجعة معلقة إلى المستدعي المصرح | تحقق إيصال ومشروع ومراجعة قبل الاستدعاء؛ لا يمر عبر [AIIntegrationShell المسجل](https://github.com/alphasigma13579-lang/ASIE/blob/435777008e01bafc73ab3bca86cc8945e311b610/ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/backend/module_runtime.py#L399-L429)، ولا يثبت الاختبار الدلالي للمخرج بمجرد القالب |
| سياق Pre-Run | [API](https://github.com/alphasigma13579-lang/ASIE/blob/435777008e01bafc73ab3bca86cc8945e311b610/ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/backend/asie_local_api.py#L2517-L2574) → [خدمة محلية](https://github.com/alphasigma13579-lang/ASIE/blob/435777008e01bafc73ab3bca86cc8945e311b610/ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/backend/intelligence_prerun_service.py#L1-L32) أو [Repository مباشرة](https://github.com/alphasigma13579-lang/ASIE/blob/435777008e01bafc73ab3bca86cc8945e311b610/ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/backend/repository.py#L1476-L1534) | جسم طلب سياق/مكونات، ومراجعة/اعتماد؛ إنشاء السياق المباشر يقبل state وcontext_hash من الجسم | سجلات سياق/مراجعة/اعتماد للمستخدم ذي صلاحية المشروع | تحقق المستأجر والصلاحية موجود؛ الكتابة خارج AAS، وقيمة القفل والحالة في مسار الإنشاء المباشر ليستا مشتقتين خادميًا |

الوصول الخارجي المذكور مسار كود مشروط بسياسة المزود ومفاتيحه. إفادة المالك بأن مفاتيح Hostinger لم تُربط بعد هي إفادة مستخدم غير متحقق منها في هذا التدقيق؛ لذلك لا نصف أي نتيجة بأنها جلب حي. لم نجد في هذه المسارات استدعاءً مباشرًا إلى Finance أو تعديل Snapshot أو Verdict، لكن عدم العثور في النطاق المفحوص ليس برهانًا شاملًا على جميع مسارات التطبيق.

## كيف حدث الانحراف وما الذي لا يمكن الجزم به

1. **سبب تنفيذي مثبت:** ربطت واجهات API الخدمات والمستودع والمزودات مباشرة، كما تبين الوصلات أعلاه، من دون نقطة عبور AAS/Socket. المسار محمي محليًا، لكنه موازٍ معماريًا.
2. **سبب ضبط مرجعي مثبت:** [EKB-00](https://github.com/alphasigma13579-lang/ASIE/blob/435777008e01bafc73ab3bca86cc8945e311b610/ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/docs/EKB/EKB-00-Knowledge-Map.md) و[EKB-01](https://github.com/alphasigma13579-lang/ASIE/blob/435777008e01bafc73ab3bca86cc8945e311b610/ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/docs/EKB/EKB-01-Verified-Document-Inventory.md) يشيران إلى اسم AIA-02 مرشح غير موجود ويصفانه بغير حالته المعتمدة؛ [سجل الوثائق v1.2.0](https://github.com/alphasigma13579-lang/ASIE/blob/435777008e01bafc73ab3bca86cc8945e311b610/ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/docs/ASIE-CANONICAL-DOCUMENT-REGISTER-v1.2.0.json) يحسم الاسم والحالة. README الكانوني يشير إلى v1.1.0 المتجاوز. هذا خلل إرشاد في مسار قراءة إلزامي، وليس تصريحًا بتجاوز العقد الصحيح.
3. **فجوة تحقق مثبتة:** الاختبارات القائمة تثبت ضوابط كثيرة، ومنها منع Finance/Snapshot وتسرب المستأجرين، لكنها لا تجعل عبور AAS/Socket شرط قبول لطرق السوق والتفسير وPre-Run. نجاحها لا ينفي المخالفة.
4. **غير مثبت:** سبب قرار المهندس أو الوكيل الفردي، وهل قرأ مهارة بعينها، وهل خلل الفهرسة تسبب مباشرة بهذا التنفيذ، أو إن كانت كل آثار التنفيذ على البيئة الحية. لا تُنسب هذه النوايا أو السببية بلا سجل إضافي.

التصنيف: انحراف معماري مادي يمنع اعتماد المسار الحي وفق العقد الحالي. لا يُحوّل تلقائيًا إلى ادعاء خرق بيانات أو تغيير أرقام. يراجع الأمن أثر تجاوز نقاط الضبط والحمولات قبل أي تفعيل.

## تقويم المسار بأقل تدخل

- في هذه الشريحة: حفظ التقرير والخطة، وتصحيح إحالات EKB/README، وإضافة اختبار يمنع عودة اسم AIA-02 وحالته الخاطئين. لا تعديل كود تشغيل ولا شبكة.
- قبل أي تشغيل خارجي: إبقاء الإيقاف والتفويض الحاكم، وكتابة ACR يحدد عقود ومسار السوق وPre-Run والتفسير ويبيّن إن كان عرض Google Maps في المتصفح استثناء عرض فقط؛ لا يُخترع Runtime أو Gateway ثانٍ.
- شريحة التنفيذ التالية بعد ACR: منع الكتابة المباشرة غير المحكومة، ثم توصيل الوظائف بالعقود والوحدات القائمة وبـAIIntegrationShell، مع اختبارات عبور إيجابية وسلبية، صلاحيات/عزل، حقن تعليمات، فشل مزود، وسلامة Snapshot.
- لا يُعلن تصحيح الانحراف حتى تظهر أدلة الاختبارات والمراجعة على رأس الكود النهائي. لا فتح دعوات، ولا تفعيل مفاتيح، ولا نشر من هذا التقرير.

## نقطة الاستئناف

راجع PR التوثيقي ورأسه؛ ثم ابدأ ACR معماريًا مستقلًا وفحصًا أمنيًا للتصميم قبل لمس المسارات الحية. استكمل خطة بيتا المالك من [الخطة الرئيسية](ASIE-BETA-EXECUTION-MASTER-PLAN-2026-09-09.md) مع إبقاء #166 و#167 كتنفيذ مظلم مدمج لا كدليل تشغيل حي.
