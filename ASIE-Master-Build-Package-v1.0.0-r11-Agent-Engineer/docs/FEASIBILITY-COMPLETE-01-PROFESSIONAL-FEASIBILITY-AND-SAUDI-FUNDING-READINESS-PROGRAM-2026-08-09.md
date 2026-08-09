# FEASIBILITY-COMPLETE-01 — برنامج إكمال دراسة الجدوى والجاهزية التمويلية السعودية

| الحقل | القيمة |
|---|---|
| Document ID | `ASIE-FEASIBILITY-COMPLETE-01-v1.0.0` |
| الحالة | `AUTHORITATIVE EXECUTION PLAN / IMPLEMENTATION BLOCKED UNTIL GATES PASS` |
| خط الأساس | `main@06bc29d8163476a6073a71141dd9782e11e9de2c` |
| الفرع التوثيقي | `codex/feasibility-bankability-program` |
| تاريخ المراجعة | 2026-08-09 |
| المالك | مالك منتج ASIE |
| مسؤولو الإغلاق | Product + Principal Architecture + Finance Review + QA + Security |
| مصدر الحقيقة الأعلى | `PROGRAM-CLOSE-10` ثم `FOUNDATION-COMPLETE-20` ثم EKB والسجلات الحاكمة |
| نطاق هذه الوثيقة | تحويل نقد الجاهزية المهنية والتمويلية إلى برنامج متطلبات وتنفيذ واختبارات وأدلة |
| لا تفعل | لا تفك تجميد AAS/Finance، لا تفعّل شبكة أو مزوّدًا، لا تمنح اعتمادًا مصرفيًا، لا تعلن الإطلاق |

> **قرار ملزم:** لا يجوز وصف ASIE بأنه «يُنتج دراسة جدوى احترافية نهائية»، أو «معتمد من البنوك/وزارة المالية/منشآت/بنك التنمية الاجتماعية»، أو «صالح لأي مشروع» قبل اجتياز جميع البوابات المطلوبة في هذه الوثيقة، مع أدلة exact-commit والتحقق المهني والخارجي المحددة أدناه.

---

## 1. الغرض والسلطة

هذه الوثيقة هي عقد التنفيذ المرجعي لإكمال قدرة ASIE على إعداد دراسات جدوى مهنية قابلة للمراجعة، ثم حزم جاهزية تمويلية مخصصة لجهة ومنتج تمويلي. وهي تجمع **كل** فجوات المراجعة الأخيرة في سجل قابل للتتبع من النتيجة إلى المتطلب ثم التصميم والتنفيذ والاختبار والدليل والبوابة.

ترتيب السلطة عند التعارض:

1. AAS Runtime Freeze وAIA Constitution.
2. `PROGRAM-CLOSE-10` و`FOUNDATION-COMPLETE-20` وحالاتهما الآلية.
3. السجلات الكانونية وACR/IACR المعتمدة.
4. EKB ومواصفات المجالات النشطة.
5. هذه الوثيقة.
6. خطط الشرائح التنفيذية وطلبات السحب.
7. سياق المحادثة؛ ليس مصدر حقيقة.

لا تُعد هذه الوثيقة ACR ولا تسمح بتعديل ملف محمي. كل شريحة تمس Finance أو Snapshot أو Runtime أو سجلًا محكومًا يجب أن تحصل أولًا على آلية التغيير المطلوبة.

---

## 2. الحكم الصريح عند خط الأساس

| القدرة | الحكم الحالي | سبب الحكم |
|---|---|---|
| فرز أولي داخلي لفكرة مشروع | `APPROVE WITH CONDITIONS` | توجد حسابات حتمية ومسار Snapshot وأدلة أولية، لكن المدخلات والتغطية محدودة |
| مسودة دراسة جدوى للمراجعة البشرية | `CONDITIONAL / LIMITED` | يمكن توليد أجزاء، لكن التقرير المالي والفني والسوقي غير مكتمل |
| دراسة جدوى احترافية نهائية | `BLOCK` | لا توجد قوائم مالية متكاملة ولا نماذج قطاعية كافية ولا اعتماد مهني |
| حزمة يمكن الاعتماد عليها لدى بنك سعودي | `BLOCK` | ملفات الممولين مرجعية فقط، والمتطلبات تختلف حسب الجهة والمنتج والحالة |
| تغطية «أي مشروع» في المملكة | `BLOCK` | التصنيف والـarchetypes والنماذج الفنية والمالية غير شاملة |
| نماذج ديناميكية حسب المشروع | `DESIGN DIRECTION VALID / RUNTIME INCOMPLETE` | DIB وApproved Input Manifest مخططان جزئيًا وغير مكتملين في المسار الحي |
| اعتماد رسمي من جهة سعودية | `NOT ESTABLISHED` | لا يوجد اتفاق أو خطاب قبول أو اعتماد رسمي مثبت |

**الوصف التجاري المسموح حاليًا فقط:**

> منصة لإعداد مسودة دراسة جدوى محكومة ومدعومة بالأدلة وقياس أولي للجاهزية التمويلية.

أي وصف أعلى من ذلك يتطلب ترقية مستوى المخرج وفق القسم 5 واجتياز بواباته.

---

## 3. قاموس حالة المعرفة

كل معلومة في التنفيذ تُوسم بإحدى الحالات التالية:

- `FACT`: مثبتة بكود أو اختبار أو مصدر رسمي أو أثر exact-commit.
- `ASSUMPTION`: افتراض معلن له مالك وتاريخ انتهاء وطريقة تحقق.
- `HYPOTHESIS`: فرضية قابلة للاختبار وليست مدخلًا ماليًا معتمدًا.
- `DECISION`: قرار معماري/منتجي مسجل بسلطة تغيير واضحة.
- `UNKNOWN`: نقص يمنع التقدم أو يخفض مستوى الثقة.
- `REFERENCE_ONLY`: مفيد استرشاديًا ولا يمثل قاعدة رسمية أو قبولًا مصرفيًا.

يحظر تحويل `ASSUMPTION` أو `HYPOTHESIS` أو `REFERENCE_ONLY` إلى حقيقة في التقرير أو Snapshot.

---

## 4. سجل الأدلة المؤسسة للحكم

| ID | النوع | الدليل | الاستنتاج المنضبط |
|---|---|---|---|
| EV-001 | `FACT` | نموذج بنك التنمية الاجتماعية المرفق، 8 صفحات | نموذج مبسط/نوعي لا يثبت وجود نموذج مالي متكامل |
| EV-002 | `FACT` | نموذج منشآت المرفق، 23 صفحة و16 قسمًا وقوائم لثلاث سنوات | مرجع أوسع، لكن منشآت تصفه استرشاديًا وغير ملزم ولا يضمن النتيجة |
| EV-003 | `FACT` | ملف «ما هي دراسة الجدوى ولماذا هي مهمة» المرفق | شرح تمهيدي وليس معيار قبول أو مصدرًا تنظيميًا |
| EV-004 | `FACT` | صفحة صندوق دعم المشاريع بوزارة المالية | قد تُطلب دراسة حديثة من مكتب استشاري معتمد تشمل الفني والتسويقي والمؤشرات والتراخيص |
| EV-005 | `FACT` | المادة 24 من قواعد SAMA للتمويل الجماعي بالدين | الجدارة الائتمانية تتطلب منهجًا موثقًا وعناية واجبة وسجلًا ائتمانيًا ووضعًا نظاميًا وملاءة وخطة أعمال |
| EV-006 | `FACT` | `backend/finance_engine.py` | نموذج مدخلات ووحدة/منتج واحد وتدفقات مبسطة وسيناريوات ثابتة |
| EV-007 | `FACT` | `backend/funder_report.py` و`tests/test_funder_report.py` | القوائم `partial` والميزانية `not_ready` وفجوات معلنة |
| EV-008 | `FACT` | `backend/funding_readiness.py` | ملفات جهات/قطاعات `reference_only` وليست قواعد رسمية |
| EV-009 | `FACT` | DIB ACR وخطة الدمج ومصفوفة التنفيذ | DIB وApproved Input Manifest والمقابلة والسجلات وربط الملفات غير مكتملة |
| EV-010 | `FACT` | `backend/sector_intelligence.py` | ثمانية قطاعات عريضة فقط؛ لا تعادل تصنيف ISIC4 التفصيلي |
| EV-011 | `FACT` | `backend/risk_engine.py` | ستة مخاطر وحدود عامة ثابتة لا تكفي لكل قطاع أو ممول |
| EV-012 | `FACT` | `/FOUNDATION-COMPLETE-20.json` | الحكم الحالي `BLOCK` وحزم لاحقة محجوبة أو تحتاج ACR |
| EV-013 | `UNKNOWN` | قبول مصرفي فعلي | لا يوجد Pilot/UAT أو خطاب قبول مؤسسي مثبت |
| EV-014 | `UNKNOWN` | صحة افتراضات كل نشاط | تحتاج مصادر، نطاقًا جغرافيًا وزمنيًا، ومراجعًا بشريًا |
| EV-015 | `DECISION` | توجيه المنتج | البيانات المفتوحة تُستخدم لتحسين الدراسة والتوجيه، لا لإعادة بيعها كمادة خام |
| EV-016 | `DECISION` | حدود المشروع | موردو المعدات منفصلون عن ملفات/مصادر البيانات العامة، وكلاهما له lineage مستقل |

المصادر الرسمية المرجعية لهذه الوثيقة:

- منشآت — نموذج دراسة الجدوى: https://www.monshaat.gov.sa/ar/node/13993
- وزارة المالية — التقدم لصندوق دعم المشاريع: https://www.mof.gov.sa/psf/Pages/Apply.aspx
- SAMA Rulebook — المادة 24: https://rulebook.sama.gov.sa/ar/المادة-الرابعة-والعشرون-تقييم-الجدارة-الائتمانية-وتدابير-العناية-الواجبة-تجاه-المنشأة-المستفيدة
- أي شرط لمنتج تمويلي يجب أن يُثبت من صفحة/وثيقة الجهة الفعلية بتاريخ السريان، لا من هذا السجل وحده.

### 4.1 مصفوفة الجهات والمرجعيات السعودية

| الجهة/المرجع | ما يثبته المصدر | ما يجب أن تبنيه ASIE | ما لا يجوز استنتاجه |
|---|---|---|---|
| بنك التنمية الاجتماعية — نموذج دراسة الجدوى | يشرح أهمية الدراسة ونقاطها الرئيسة بصيغة مبسطة | تغطية البنود مع نموذج مالي/فني/سوقي أعمق | أن النموذج وحده معيار قبول كامل |
| بنك التنمية الاجتماعية — تمويل التميز/المنتج الفعلي | بحسب لقطة المراجعة، قد تتضمن الحزمة دراسة جدوى/خطة أعمال، عروض أسعار، سجلًا تجاريًا، عقد تأسيس، هوية، مؤهلات، سيرة ذاتية، خبرة، ضمانات وسجلًا ائتمانيًا | Profile منفصل لكل منتج وإصدار؛ document checklist وexpiry ومصدر رسمي | تعميم هذه المتطلبات على كل منتجات البنك أو تثبيتها بلا إعادة تحقق عند التقديم |
| منشآت — نموذج دراسة الجدوى | نموذج استرشادي، غير ملزم، خاضع للتحديث ولا يضمن النتيجة | استعماله كمرجع completeness فقط | اعتماد منشآت أو ضمان فعالية/تمويل |
| وزارة المالية — صندوق دعم المشاريع | دراسة حديثة من مكتب استشاري معتمد قد تشمل الوصف والفني والتسويقي والمؤشرات والتراخيص | L3 workflow للمكتب/المراجع المعتمد والتراخيص | أن تقريرًا آليًا غير موقع يفي بالشرط |
| وزارة المالية — إقراض مشاريع تعليمية/تدريبية | دراسة عربية معدة ومعتمدة من مكتب مرخص ووثائق ملاءة وأرض/إيجار وغيرها بحسب البرنامج | Sector/product-specific checklist ومراجعة بشرية | وجود نموذج موحد لكل القطاعات |
| SAMA — المادة 24 للتمويل الجماعي بالدين | منهج جدارة موثق، سجل ائتماني، وضع وهوية وعنوان وملاءة وأداء وتمويل قائم وخطة أعمال | due-diligence evidence وrisk/readiness process | تطبيق المادة كمعيار موحد لكل بنك أو منح ASIE سلطة قرار ائتماني |
| الهيئة العامة للإحصاء — ISIC4 | التصنيف الوطني مرجع لوصف الأنشطة الإنتاجية | سجل رسمي versioned وتفصيل النشاط لا القطاعات العريضة | أن ثمانية sector IDs تغطي الاقتصاد السعودي |

**قرار مؤسسي:** لا توجد «استمارة واحدة معتمدة من جميع البنوك». القبول يتغير حسب الجهة والمنتج والقطاع وحجم المشروع والضمانات وتاريخ الشروط. لذلك يكون كل Lender Profile محدود النطاق والزمن، ويجب إعادة التحقق من المصدر الرسمي عند إنشاء الحزمة الفعلية.

### 4.2 خريطة حالة FOUNDATION/FC20 عند خط الأساس

| الحزمة | الحالة عند `main@06bc29d8` | أثرها على هذا البرنامج |
|---|---|---|
| FC20-05 | `ACR_REQUIRED` | لا توسيع حوكمة المصادر/الوصول قبل ACR |
| FC20-06 | `BLOCKED` | National/Global Intelligence غير متاح كقدرة حية |
| FC20-07 | `BLOCKED` | Market estimation/sector/reference cost غير مكتملة |
| FC20-08 | `BLOCKED` | context/synthesis غير مكتملة |
| FC20-09 | `BLOCKED` | Product AI/template/question registry غير مكتملة |
| FC20-10 | `BLOCKED` | Google Maps غير مفعل ولا تفويض شبكة |
| FC20-11 | `OPEN` | Data intake/PDF quote extraction/blueprint mapping مسار عمل نشط لكنه غير مغلق |
| FC20-12 | `ACR_REQUIRED` | أي توسيع Finance/Decision يحتاج قرار تغيير منفصل |
| FC20-13 | `BLOCKED` | risk/readiness المتقدم غير مكتمل |
| FC20-14 | `BLOCKED` | professional/report assurance غير مكتمل |
| FC20-15 | `BLOCKED` | external validation/pilot غير مثبت |
| FC20-16 | `BLOCKED` | release/product completion غير مخول |

هذه الحالات قيود فعلية وليست ترتيبًا تجميليًا. لا ترفع هذه الوثيقة أي حالة منها؛ الترقية تتطلب كودًا واختبارات ودليل exact-commit وتراجعًا ومراجعة مخاطر حسب الحزمة.

---

## 5. مستويات المخرج ومنع التضليل

| المستوى | الاسم | ما يسمح به | ما لا يسمح به | بوابة الترقية |
|---|---|---|---|---|
| L0 | Screening | فرز أولي، فجوات، نطاقات تقريبية معلنة | قرار تمويل أو دراسة نهائية | G1 جزئي + تحذير واضح |
| L1 | Professional Draft | دراسة متكاملة قابلة لمراجعة متخصص | ادعاء قبول ممول | G1–G4 + مراجعة بشرية |
| L2 | Lender-Profile Pack | حزمة مهيأة لمنتج ممول محدد وإصدار شروط محدد | «معتمدة» بلا قبول رسمي | G1–G6 + profile validated |
| L3 | Accredited/Signable Pack | حزمة قابلة للتوقيع/الاعتماد المهني حيث يلزم | إحلال المنصة محل مكتب مرخص أو قرار الجهة | G1–G7 + توقيع/اعتماد خارجي |
| L4 | Institutionally Accepted | تنسيق/تكامل ثبت قبوله لدى جهة محددة | تعميم القبول على جميع الجهات | خطاب/اتفاق قبول صالح ومحدّث |

كل تقرير يحمل: المستوى، الإصدار، تاريخ القطع، الجهة/المنتج إن وجدا، حالة الأدلة، الفجوات، اسم المراجع، وعبارة عدم ضمان التمويل.

---

## 6. النتائج المستهدفة

- **OUT-01:** إنشاء دراسة جدوى ديناميكية تختار نموذجها حسب النشاط وطبيعة الإيراد والتشغيل والتمويل، لا حسب قطاع عريض فقط.
- **OUT-02:** إنتاج نموذج مالي متكامل قابل لإعادة الحساب والمطابقة والتدقيق.
- **OUT-03:** ربط كل رقم بمصدر أو افتراض معتمد أو اشتقاق حتمي.
- **OUT-04:** فصل الجاهزية المهنية عن الجاهزية لمنتج تمويلي وعن الاعتماد الخارجي.
- **OUT-05:** تغطية النشاط السعودي بتصنيف رسمي وتحديد التراخيص والاشتراطات والقيود.
- **OUT-06:** جعل النواقص مرئية وفشل النظام مغلقًا بدل توليد يقين زائف.
- **OUT-07:** الحفاظ على AAS/Snapshot/tenant isolation وعدم منح AI أو UI سلطة على الحقيقة المالية.
- **OUT-08:** إثبات الجودة بحالات ذهبية ومراجعة مستقلة وPilot، لا بعدد الاختبارات وحده.

مؤشرات نجاح البرنامج:

- 100% من بنود التقرير لها lineage وحالة ثقة.
- 100% من القوائم المالية تجتاز معادلات المطابقة دون tolerance غير مفسر.
- 100% من اختبارات tenant isolation والأذونات السلبية تمر.
- صفر ادعاء اعتماد بلا Evidence ID صالح.
- صفر قراءة Finance من raw UI/AI/file.
- 100% من profiles تحمل الجهة والمنتج والإصدار وتاريخ السريان والمصدر والحالة.
- ≥ 95% من الحقول الإلزامية في الحالات الذهبية مكتملة قبل L1؛ والباقي يظهر كـgap مانع لا كصفر.
- مراجعة مستقلة لكل عائلة نموذج مالي قبل السماح بها في L1.

---

## 7. النطاق وعدم النطاق

داخل النطاق:

- التصنيف السعودي، project archetypes، DIB، intake، market/technical/finance/risk، evidence، lender profiles، التقارير، UX، الاختبارات والمراجعة الخارجية.
- ملفات CSV/XLSX/PDF وعروض الموردين كمدخلات منفصلة ذات lineage.
- بيانات مفتوحة مجانية كمصدر للبحث والتوجيه والتقدير، مع احترام الترخيص والإسناد وعدم الادعاء بإعادة بيع البيانات الخام.

خارج النطاق حتى تفويض مستقل:

- إطلاق Production/Public Beta.
- تفعيل AI provider أو Google Maps أو أي network fetch حي.
- استخدام مفاتيح أو أسرار.
- الادعاء بأن ASIE مكتب استشاري معتمد أو جهة ائتمان.
- اتخاذ قرار التمويل نيابة عن البنك.
- تعديل AAS Runtime Freeze أو Finance المحمي دون ACR.
- دمج PRs قديمة لمجرد وجودها؛ PR #42 و#10 سياق تاريخي حتى إعادة التحقق/rebase.

---

## 8. الثوابت المعمارية

1. المسار الوحيد للحقيقة:
   `Project Run → Bus/Socket/Module Runtime → sealed outputs → snapshot.assemble.v1 → immutable Snapshot → projections`.
2. Finance يقرأ `Approved Input Manifest / normalized_inputs` فقط.
3. UI وAI وMarket وReport لا تحسب الحقيقة المالية ولا تستدعي Finance خارج المسار المحكوم.
4. كل تعديل مدخلات بعد Snapshot ينشئ `Draft Revision` ثم Snapshot جديدًا؛ لا تعديل رجعي.
5. القيم `UNKNOWN` و`NOT_APPLICABLE` و`ZERO_VERIFIED` حالات مختلفة.
6. كل سجل وSnapshot وعرض وتقرير مرتبط بـ `organization_id` مع فشل مغلق.
7. AI يشرح ويسأل ويلخص؛ لا يخترع أسعارًا أو أرقامًا نهائية ولا يمنح قرارًا ائتمانيًا.
8. الشبكة والمزوّدات تظل معطلة، وأي connector مستقبلي يمر عبر سياسة مصدر وegress وSSRF ودليل تفعيل مستقل.
9. كل مخرج حتمي يحمل `schema_version` و`engine_version` و`source_hashes` و`generated_at`.
10. التقارير Projection من Snapshot؛ لا إعادة حساب في PDF/frontend.

---

## 9. المتطلبات الوظيفية ومعايير القبول

### 9.1 التصنيف ونماذج المشروع

- **FR-CLS-001:** سجل نشاط سعودي رسمي يدعم رمز ISIC4 من ست خانات، الاسم العربي/الإنجليزي، القسم/الفئة، وحالة السريان.
  - AC: البحث والاختيار يعيدان code/version/source/effective_date؛ الرموز الملغاة لا تُقبل دون mapping.
  - Tests: `T-CLS-001..004`.
- **FR-CLS-002:** سجل متطلبات تنظيمية يربط النشاط بالجهات والتراخيص والموقع والقيود، مع حالة `verified/reference/unknown`.
  - AC: لا يعرض اشتراطًا كنهائي بلا مصدر وتاريخ؛ التعارض يولد gap.
  - Tests: `T-CLS-005..008`.
- **FR-ARC-001:** `Project Archetype Registry` يختار عائلة النموذج حسب اقتصاد المشروع، لا الاسم فقط.
  - العائلات الدنيا: تصنيع؛ تجارة/تجزئة/e-commerce؛ خدمات مهنية؛ SaaS/اشتراك؛ marketplace/عمولة؛ إيجار/تأجير؛ عقار/ضيافة؛ زراعة؛ صحة/تعليم منظم؛ عقود/مشاريع مرحلية؛ hybrid.
  - AC: كل archetype يعرّف revenue drivers وcost drivers وworking capital وcapex وtimeline وrisks وrequired evidence.
  - Tests: `T-ARC-001..012`.
- **FR-ARC-002:** المشاريع الهجينة تركب نماذج فرعية دون مضاعفة الإيراد أو التكلفة.
  - AC: reconciliation بين submodels والإجمالي يساوي صفرًا ضمن tolerance محدد.
  - Tests: `T-ARC-013..016`.

### 9.2 DIB والمدخلات والملفات

- **FR-DIB-001:** مساران متكافئان: «فكرة فقط» و«لدي أرقام/ملفات/عروض».
- **FR-DIB-002:** Template Registry وQuestion Registry بإصدارات واختبارات توافق.
- **FR-DIB-003:** كل item يحمل النوع والوحدة والعملة والفترة والموقع والمصدر وحالة الثقة والمالك.
- **FR-DIB-004:** حالات item الدنيا: `unknown`, `user_estimate`, `derived`, `source_observed`, `quote_observed`, `reviewed`, `approved`, `rejected`, `not_applicable`.
- **FR-DIB-005:** Approved Input Manifest موقّع/مختوم منطقيًا، immutable، tenant-bound، versioned.
- **FR-DIB-006:** mapping محكوم لـmanual/CSV/XLSX/PDF-text/supplier quote؛ لا يُقبل extraction كقيمة مالية قبل مراجعة بشرية.
- **FR-DIB-007:** عروض موردي المعدات سجل مستقل عن open/public data sources.
- **FR-DIB-008:** أي نقص إلزامي يمنع Finance أو يخفض مستوى المخرج وفق policy معلنة.
  - AC المشترك: raw input لا يصل إلى Finance؛ إعادة المحاولة idempotent؛ provenance كامل؛ رفض خلط المؤسسة.
  - Tests: `T-DIB-001..020`, `T-SEC-001..006`.

### 9.3 المحرك المالي المتكامل

- **FR-FIN-001:** مدخلات متعددة للمنتجات/الخدمات/الوحدات/القنوات مع أسعار وأحجام وramp-up موسمية.
- **FR-FIN-002:** شهرية السنة الأولى كحد أدنى؛ 24–36 شهرًا حيث يتطلب archetype؛ سنوية 5–10 سنوات وفق طبيعة الأصل/التمويل.
- **FR-FIN-003:** Income Statement وBalance Sheet وCash Flow مترابطة.
- **FR-FIN-004:** Sources & Uses، رأس مال عامل، مخزون، ذمم مدينة/دائنة، deposits، opening cash.
- **FR-FIN-005:** CAPEX timing، depreciation/amortization، replacement capex، maintenance capex، salvage/terminal value.
- **FR-FIN-006:** VAT/Zakat/Tax كإعدادات jurisdiction/versioned؛ لا تُفترض معاملة قانونية بلا مراجعة.
- **FR-FIN-007:** inflation/escalation، FX عند اللزوم، wage/utilities growth، construction/ramp-up delays.
- **FR-FIN-008:** جدول دين حقيقي: drawdowns، grace على principal/interest، fees، rates، amortization، balloon، prepayment.
- **FR-FIN-009:** فصل project/unlevered cash flow عن equity/levered cash flow.
- **FR-FIN-010:** NPV/IRR/MIRR/payback/break-even/DSCR، وLLCR حيث يلزم، على التدفق الصحيح والفترات الصحيحة.
- **FR-FIN-011:** سيناريوات base/upside/downside مرتبطة بمحركات النشاط وليست عوامل عامة ثابتة.
- **FR-FIN-012:** Sensitivity مصفوفية وMonte Carlo بمعلمات sector/archetype، distributions مبررة، correlation، seed، convergence diagnostics.
- **FR-FIN-013:** `loan_grace_months` وأي مدخل مماثل يجب أن يغير الجدول فعلًا أو يُرفض؛ لا حقول ميتة.
- **FR-FIN-014:** منع الثوابت العامة الحالية من الادعاء بتمثيل كل مشروع.
  - AC: جميع الثوابت في القسم 10؛ golden vectors مراجعة؛ backward compatibility مقصودة؛ failure on missing/invalid.
  - Tests: `T-FIN-001..045`, `T-PROP-001..020`, `T-MC-001..010`.

### 9.4 السوق والفني والتشغيل

- **FR-MKT-001:** تقدير TAM/SAM/SOM أو بديله الملائم مع تعريف المنهج والوحدة والجغرافيا والتاريخ وعدم اليقين.
- **FR-MKT-002:** triangulation بين ≥2 مصدر مستقل حيث يمكن؛ خلاف ذلك تنخفض الثقة ويظهر gap.
- **FR-MKT-003:** المنافسون والأسعار والطلب لا تُعرض كبيانات حية إذا كانت offline/reference.
- **FR-MKT-004:** السيناريو السوقي يغذي drivers المعتمدة عبر Manifest فقط.
- **FR-TEC-001:** وحدات فنية حسب archetype: الطاقة/السعة/BOM/yield/utilities/labor/site/quality.
- **FR-TEC-002:** التراخيص والجدول التنفيذي والمشتريات والعروض ومخاطر التوريد.
- **FR-TEC-003:** السعودة/المهارات والسلامة والأثر البيئي/الاجتماعي عند انطباقها.
- **FR-TEC-004:** القطاعات المنظمة تفرض review checklist متخصصًا.
  - Tests: `T-MKT-001..015`, `T-TEC-001..020`.

### 9.5 المخاطر والجاهزية التمويلية

- **FR-RSK-001:** Risk taxonomy قطاعية وتمويلية وتشغيلية وسوقية وتنظيمية وتقنية وESG.
- **FR-RSK-002:** الحدود ليست عامة؛ تُربط بالـarchetype والجهة والمنتج والإصدار.
- **FR-RSK-003:** كل risk يحمل likelihood/impact/velocity/owner/mitigation/evidence/residual status.
- **FR-LND-001:** Lender Profile = institution + product + borrower type + effective date + source + version + status.
- **FR-LND-002:** حالات profile: `reference_only`, `source_verified`, `professionally_validated`, `institutionally_accepted`, `expired`.
- **FR-LND-003:** لا يترقى profile إلى accepted دون وثيقة/اتفاق مكتوب قابل للتدقيق.
- **FR-LND-004:** تمرير `profile_id` end-to-end؛ اختبار يمنع سقوطه إلى base profile. يعالج الخطر المرصود في `build_funder_report_projection`.
- **FR-LND-005:** readiness تجمع اكتمال المستندات، الجدارة، المؤشرات، التراخيص، الضمانات، السجل والخبرة حيث يطلب المنتج.
- **FR-LND-006:** النتيجة «جاهزية/فجوات»، وليست ضمان موافقة أو قرار ائتمان.
  - Tests: `T-RSK-001..012`, `T-LND-001..018`.

### 9.6 الأدلة والمراجعة والتقارير

- **FR-EVD-001:** lineage لكل قيمة: source URI/document hash/page/cell، observed_at، effective_date، geography، unit، currency، license، reviewer.
- **FR-EVD-002:** freshness policy حسب نوع البيانات؛ stale لا يتحول تلقائيًا إلى current.
- **FR-EVD-003:** open-data license وattribution وpermitted-use مسجلة؛ المنصة تستخدم البيانات للتحليل والتوجيه ولا تسوق البيانات الخام كمنتج.
- **FR-EVD-004:** quotation evidence منفصل عن public-data evidence.
- **FR-EVD-005:** تعارض المصادر لا يُسوّى بصمت؛ يسجل Transformation/Resolution Record.
- **FR-RPT-001:** التقرير يغطي التنفيذي والسوقي والفني والتشغيلي والتنظيمي والمالي والمخاطر والتنفيذ.
- **FR-RPT-002:** الجداول المالية في التقرير تطابق Snapshot حرفيًا؛ PDF لا يعيد الحساب.
- **FR-RPT-003:** كل جدول/رسم له unit/currency/period/source/confidence.
- **FR-RPT-004:** الأقسام الناقصة تظهر `GAP/BLOCKED` لا نصًا عامًا يوحي بالاكتمال.
- **FR-REV-001:** workflow لمراجعة محاسب ومهندس/خبير قطاع ومحلل ائتمان بحسب المستوى.
- **FR-REV-002:** L3 يتطلب جهة/مكتبًا مرخصًا أو معتمدًا عندما تشترط الجهة ذلك.
- **FR-REV-003:** التوقيع لا يغير Snapshot؛ ينشئ ApprovalReceipt/ReviewOverlay.
  - Tests: `T-EVD-001..016`, `T-RPT-001..018`, `T-REV-001..010`.

### 9.7 تجربة المستخدم

- **FR-UX-001:** المسار العربي RTL: الموقع → القطاع → ISIC4 → اسم المشروع → الفجوة/الميزة → الجمهور → رأس المال → التفاصيل.
- **FR-UX-002:** اختيار archetype شفاف قابل للتعديل مع أثر التغيير.
- **FR-UX-003:** Progressive disclosure؛ لا تعرض كل الحقول لكل مشروع.
- **FR-UX-004:** Live Cockpit يعرض status/provenance/drill-down، لكنه لا يعيد الحساب.
- **FR-UX-005:** حالات الثقة والنقص والمراجعة مفهومة بالعربية ولا تستعمل ألوانًا وحدها.
- **FR-UX-006:** export وscreen وAPI تعرض مستوى المخرج نفسه والتحذيرات نفسها.
  - Tests: `T-UX-001..015`, `T-A11Y-001..008`, `T-E2E-001..012`.

---

## 10. ثوابت مالية واجبة الاختبار

- `Assets = Liabilities + Equity` لكل فترة ضمن tolerance موثق.
- `Closing Cash(t) = Opening Cash(t) + CFO(t) + CFI(t) + CFF(t)`.
- `Debt Closing = Opening + Drawdowns + Capitalized Interest - Principal Repaid ± Adjustments`.
- `Sources = Uses` عند الإغلاق، وأي funding gap ظاهر.
- depreciation لا تتجاوز depreciable base، وتحترم in-service date والعمر والقيمة المتبقية.
- inventory/receivables/payables تتبع drivers والفترات ولا تُستبدل بنسب سنوية عمياء.
- VAT لا يُعامل إيرادًا أو تكلفة إلا حسب configuration الموثقة.
- grace period يغير cashflow/debt balance/interest schedule.
- project IRR لا يستخدم equity cash flow، وequity IRR لا يستخدم unlevered cash flow.
- terminal value/salvage لا يُضاف مرتين.
- scenario/Monte Carlo يعاد إنتاجه مع seed والإصدار نفسيهما.
- القيم المفقودة لا تتحول إلى صفر.
- التقريب يحدث في العرض لا في الحساب الأساسي.
- جميع العملات والفترات والوحدات قابلة للتحقق.
- أي تغيير input manifest ينتج run/snapshot جديدين.

---

## 11. المتطلبات غير الوظيفية

- **NFR-DET-001:** حتمية الحساب؛ نفس المدخلات والإصدارات تعطي نفس النتائج.
- **NFR-AUD-001:** سجل append-only للتغييرات والمراجعات والاعتمادات.
- **NFR-SEC-001:** tenant isolation وفشل مغلق لجميع API/storage/export.
- **NFR-SEC-002:** حماية ingestion من path traversal، formula injection، zip bombs، malformed PDFs، SSRF عند تفعيل شبكة مستقبلًا.
- **NFR-PRV-001:** تقليل البيانات وحماية المستندات المالية والشخصية وسياسة احتفاظ وحذف.
- **NFR-PERF-001:** ميزانية أداء معلنة لكل run/report؛ لا قبول دون قياس p50/p95 وحجم الحالة.
- **NFR-REL-001:** idempotency، retry safety، transaction boundaries، backup/restore proof.
- **NFR-VER-001:** versioning لكل schema/template/profile/source policy/engine.
- **NFR-LOC-001:** العربية RTL أساسية؛ الأرقام والوحدات والعملات غير ملتبسة.
- **NFR-A11Y-001:** WCAG 2.1 AA للمسار الأساسي.
- **NFR-OBS-001:** structured logs/metrics/traces بلا تسريب بيانات حساسة.
- **NFR-COMP-001:** تراخيص المصادر وسياسات الاستخدام والإسناد قابلة للتدقيق.
- **NFR-PORT-001:** اختبارات Windows/Linux وline-ending/path behavior للبوابات المطلوبة.

---

## 12. مسارات العمل والحزم

| WS | الحزمة | الارتباط بـFC20 | المخرجات | شرط البدء | شرط الإغلاق |
|---|---|---|---|---|---|
| WS-00 | Baseline & Contract | FC20 governance | هذه الوثيقة، traceability، issue slices | main ثابت | G0 |
| WS-01 | Finance ACR & Model Kernel | FC20-12 + Finance boundary | ACR، schemas، three statements، debt/tax/WC | موافقة ACR | G1 |
| WS-02 | DIB & Intake | FC20-09/11 | registries، manifest، mappings، quote intake | contracts approved | G2 |
| WS-03 | Classification & Archetypes | FC20-07/09 | ISIC4، archetypes، sector packs | source policy | G3 |
| WS-04 | Evidence/Market/National | FC20-05/06/07/08 | source registry، market methods، transformations | FC20-05 governance | G4 |
| WS-05 | Risk/Lender/Reports | FC20-12/13/14 | profiles، risk rules، report levels، review | G1–G4 | G5/G6 |
| WS-06 | UX & Live Cockpit | FC20-09/10/16 | guided journey، gaps، drill-down، parity | stable APIs | G6 |
| WS-07 | Independent Validation | FC20-14/15/16 | golden cases، expert review، lender pilot | G1–G6 | G7 |
| WS-08 | Release Evidence | PROGRAM-CLOSE-10 | exact commit، CI، rollback، residual risk | G7 | G8 |

**ترتيب إلزامي:** لا يبدأ كود WS-01 قبل ACR. لا يبدأ claim/UI نهائي قبل ثبات العقود. لا يفتح أي مصدر حي ضمن WS-04 أو خرائط ضمن WS-06 دون تفويض شبكة مستقل.

---

## 13. الشرائح التنفيذية

### S0 — قبول برنامج العمل
- مراجعة هذه الوثيقة، تثبيت baseline، إنشاء issue لكل WS، وربطها بالمتطلبات.
- لا كود إنتاجي.
- المخرج: G0 review record.

### S1 — ACR للنموذج المالي والعقود
- تعريف schemas، الفترات، الدقة، الأخطاء، migration وcompatibility.
- تحديد الملفات المحمية ومسار rollback.
- المخرج: ACR مقبول؛ لا يُعد تنفيذًا.

### S2 — Financial Kernel
- three statements + debt + working capital + capex + tax configuration.
- property tests وgolden vectors.
- يمنع التقرير من ترقية L1 قبل G1.

### S3 — DIB/Manifest
- dynamic questions/templates، file/quote mapping، review state، manifest seal.
- tenant/security negative tests.
- يمنع Finance من raw input.

### S4 — Archetypes/ISIC4
- سجل الأنشطة والعائلات الدنيا ومصفوفة applicability.
- حالات ذهبية لكل عائلة، مع sector expert.

### S5 — Market/Technical/Evidence
- منهجيات تقدير، source policy، freshness، technical modules، license/regulatory mapping.
- لا network activation ضمن الشريحة؛ fixtures ومصادر معتمدة يدويًا أولًا.

### S6 — Lender Profiles & Reports
- إصلاح propagation، versioned profiles، readiness gaps، report parity.
- فصل reference/validated/accepted.

### S7 — UX/E2E
- رحلة عربية ديناميكية، cockpit، drill-down، gaps، exports.
- لا client-side truth.

### S8 — Independent Review & Pilot
- محاسب + خبير قطاع + محلل ائتمان.
- Pilot محدود مع جهة/مستشار إن أمكن، دون ادعاء قبول قبل الدليل.

### S9 — Release Decision
- exact-commit workflows، artifacts/checksums، restore rehearsal، residual risks.
- G8 لا يساوي إطلاقًا؛ يحتاج سلطة إصدار مستقلة وفق PROGRAM-CLOSE-10.

---

## 14. استراتيجية الاختبار

### 14.1 طبقات الاختبار

1. **Unit:** المعادلات، validation، state transitions، profile selection.
2. **Property/Invariant:** المطابقات المالية، monotonicity المنطقية، الحدود، missing-vs-zero.
3. **Golden vectors:** ملفات حالات مع نتائج مراجعة مستقلة.
4. **Contract:** schemas، API register، socket/module outputs، backward compatibility.
5. **Integration:** DIB → Manifest → Finance → Snapshot → Report.
6. **Security negative:** cross-tenant، forged manifest، stale approval، path/file attacks، role denial.
7. **Migration:** snapshots/templates/profiles القديمة والجديدة وعدم تعديل التاريخ.
8. **E2E:** المساران «فكرة» و«ملفات» لكل archetype.
9. **Export parity:** API/UI/PDF/CSV نفس الأرقام والمستوى والتحذيرات.
10. **Performance/reliability:** load profile معلوم، timeout، retries، crash recovery، backup/restore.
11. **Cross-platform:** Linux CI وWindows للpaths/PDF/line endings.
12. **Independent validation:** recalculation خارجي وعينات قطاعية ومراجعة ائتمانية.

### 14.2 أوامر البوابة الأساسية

من جذر الحزمة الحية في GitHub Actions:

```text
pnpm build
python -m compileall -q backend
python -m pytest -q
```

تضاف اختبارات الشريحة المحددة ولا تُستبدل بها الأوامر الأساسية.

### 14.3 الحالات الذهبية الدنيا

| Case | Archetype | خصائص إلزامية |
|---|---|---|
| GC-01 | تصنيع | BOM/yield/capacity/inventory/capex/debt |
| GC-02 | تجارة/e-commerce | SKU mix/returns/fees/inventory/WC |
| GC-03 | خدمات مهنية | utilization/headcount/milestones |
| GC-04 | SaaS | MRR/churn/cohorts/CAC/deferred revenue |
| GC-05 | Marketplace | GMV/take rate/sides/refunds |
| GC-06 | Rental | fleet/utilization/deposits/maintenance/residual |
| GC-07 | عقار/ضيافة | development phases/occupancy/ADR/terminal |
| GC-08 | زراعة | cycles/yield/weather sensitivity/working capital |
| GC-09 | صحة/تعليم | licenses/capacity/staffing/compliance |
| GC-10 | عقود مرحلية | backlog/progress billing/retention |
| GC-11 | Hybrid | تركيب نموذجين ومطابقة دون double counting |
| GC-12 | Failure case | نقص حاسم يجب أن يفشل مغلقًا |

كل حالة لها input manifest ثابت، نتائج متوقعة، reviewer، tolerance، engine version، checksum، ومبرر الاختيار.

---

## 15. بوابات القرار

نتيجة كل بوابة واحدة من: `PASS`, `CONDITIONAL PASS`, `FAIL`, `DEFER`.

### G0 — BUILD READY
يلزم:
- scope/outcomes/FR/NFR/owners/dependencies/risks/DoD/test plan مكتملة.
- ACR boundaries محددة.
- traceability 100%.
- لا UNKNOWN بلا مالك أو disposition.

### G1 — FINANCE CORE VERIFIED
يلزم:
- FR-FIN وinvariants تمر.
- مراجعة محاسب مستقل للمعادلات والحالات الذهبية.
- لا balance sheet `not_ready` ولا statements `partial` لمستوى L1.
- debt grace والتدفقات والضرائب/WC تختبر فعليًا.

### G2 — DYNAMIC MODEL VERIFIED
يلزم:
- DIB/registries/manifest حية عبر المسار الرسمي.
- صفر raw input إلى Finance.
- file/quote human-review وtenant isolation.

### G3 — SECTOR COVERAGE VERIFIED
يلزم:
- ISIC4 versioned.
- 11 archetypes الدنيا وحالات ذهبية.
- applicability/unknown behavior موثق؛ لا ادعاء «أي مشروع» قبل coverage evidence.

### G4 — EVIDENCE & MARKET VERIFIED
يلزم:
- lineage/freshness/license/geography/units.
- market methods وconfidence والتعارض.
- فصل public data عن equipment suppliers.

### G5 — LENDER PROFILE VERIFIED
يلزم:
- profile propagation.
- product/version/effective date/source/status.
- requirements matrix وnegative tests.
- لا accepted بلا دليل مؤسسي.

### G6 — PROFESSIONAL STUDY READY
يلزم:
- L1 report كامل، parity، gaps، review receipts.
- مراجعة فنية وسوقية ومالية ومخاطر.
- UX/E2E/A11Y.

### G7 — EXTERNAL VALIDATION/PILOT
يلزم:
- مراجعة مستقلة موثقة.
- pilot cases بنتائج وملاحظات وإغلاقات.
- شروط L2/L3 حسب الجهة، مع disclaimer وعدم ضمان التمويل.

### G8 — RELEASE EVIDENCE COMPLETE
يلزم لكل حزمة:
- exact commit SHA.
- workflow run ناجح على SHA نفسه.
- artifacts/checksums.
- rollback/restore proof.
- residual-risk review.
- لا regression في AAS Freeze/Snapshot/tenant isolation.
- تفويض إطلاق مستقل؛ `PASS` هنا لا يفتح الشبكة أو production تلقائيًا.

---

## 16. Definition of Ready وDefinition of Done

### DoR لكل شريحة
- Requirement IDs وacceptance tests معروفة.
- source-of-truth وaffected paths محددة.
- ACR/IACR موجود إذا لزم.
- threat model/data classification محددان.
- fixtures ومراجع الاختبار جاهزة.
- owner/reviewer/dependencies/rollback معلومون.
- لا اعتماد على network/provider غير مصرح.

### DoD لكل شريحة
- الكود والعقود والوثائق محدثة في PR صغير.
- unit/integration/negative/golden tests تمر.
- baseline tests تمر.
- exact-commit workflow evidence.
- AAS Freeze وtenant isolation مثبتان.
- traceability وروابط الأدلة محدثة.
- migration/rollback مجربان.
- لا TODO أو stub أو `partial/not_ready` في نطاق الادعاء.
- residual risks وUNKNOWNs معلنة.
- مراجعة الاختصاص المطلوبة مكتملة.

لا يساوي merge الإغلاق ما لم يستوفِ DoD.

---

## 17. سجل المخاطر الأولي

| ID | الخطر | الشدة | التخفيف | شرط التوقف |
|---|---|---:|---|---|
| R-01 | يقين زائف/ادعاء اعتماد | P0 | levels + claim gate + legal/product review | أي نص غير مدعوم |
| R-02 | كسر Finance/AAS Freeze | P0 | ACR + narrow PR + freeze tests | تغير hash/contract غير مصرح |
| R-03 | أخطاء مالية صامتة | P0 | invariants + golden + accountant review | mismatch أو missing→zero |
| R-04 | خلط tenant | P0 | org-bound manifest/snapshot/export + negative tests | أي cross-tenant read/write |
| R-05 | نموذج واحد لكل المشاريع | P1 | archetype registry + coverage gate | ادعاء any-project بلا evidence |
| R-06 | شروط ممول قديمة/خاطئة | P1 | effective dates/status/expiry/source | profile بلا مصدر صالح |
| R-07 | بيانات عامة قديمة أو مرخصة خطأ | P1 | license/freshness/attribution | مصدر بلا permission metadata |
| R-08 | خلط المورد بمصدر البيانات | P1 | registries منفصلة | lineage مبهم |
| R-09 | AI يخترع أرقامًا | P0 | AI non-authoritative + approval gate | رقم بلا source/approval |
| R-10 | تقارير لا تطابق Snapshot | P0 | projection-only + parity tests | فرق غير صفري |
| R-11 | PR تاريخي يلوث main | P1 | rebase/re-audit؛ archive lockdown | نسخ من archive/reference |
| R-12 | نجاح CI يخفي نقصًا مهنيًا | P1 | external review + gate evidence | claim مبني على CI فقط |
| R-13 | توسيع نطاق لا ينتهي | P1 | stage gates + archetype coverage matrix | شريحة بلا DoR |
| R-14 | إحباط القرار بسبب إعلان مبكر | P1 | حكم صريح، progress بالأدلة، stop-the-line | لغة نجاح غير مثبتة |

---

## 18. قواعد Stop-the-Line

يوقف العمل في الشريحة ولا ينتقل لما بعدها عند:

- تعارض مع Freeze/Constitution/PROGRAM-CLOSE-10/FOUNDATION.
- عدم وجود ACR لتغيير محمي.
- failure في tenant isolation أو authorization.
- اختلاف القوائم أو debt schedule أو report parity.
- تحول unknown إلى zero أو assertion غير موثق.
- profile أو مصدر بلا إصدار/تاريخ/حالة.
- تعديل Snapshot تاريخي.
- حاجة إلى network/provider/key بلا تفويض مستقل.
- عدم وجود rollback لمهاجرة أو schema change.
- اكتشاف أن مخرجًا تسويقيًا أعلى من مستوى البوابة.
- فشل مستقل لم يعالج أو residual risk P0/P1 غير مقبول.

---

## 19. إدارة التغيير

- كل Requirement له owner وtest IDs وgate.
- إضافة/حذف/تغيير متطلب يمر PR ويشرح أثره على المخاطر والاختبارات.
- لا يُحذف متطلب لسد فشل؛ إما إصلاح أو قرار `DEFER` صريح مع أثره على claim.
- أي تغيير في معايير جهة تمويل ينشئ profile version جديدًا ولا يعيد كتابة التاريخ.
- أي تغيير model/template ينشئ Draft Revision وSnapshot جديدًا.
- مراجعة هذه الوثيقة عند: تغيير FOUNDATION/PROGRAM، ACR مالي، إضافة archetype، تغيير تنظيمي، pilot خارجي، أو قبل G6/G8.
- سجل القرارات يستخدم ADR/ACR، وسجل الأدلة يحمل source/hash/date/reviewer.

---

## 20. مصفوفة تتبع النقد إلى التنفيذ

| فجوة المراجعة | المتطلبات | الاختبارات | البوابة |
|---|---|---|---|
| نموذج مالي ذو وحدة واحدة | FR-ARC-001/002, FR-FIN-001 | T-ARC, T-FIN | G1/G3 |
| تدفق سنوي ثابت وNPV/IRR مبسط | FR-FIN-002/009/010 | T-FIN, T-PROP | G1 |
| قوائم partial وBalance Sheet not_ready | FR-FIN-003/004, FR-RPT-001 | T-FIN, T-RPT | G1/G6 |
| لا tax/zakat/VAT/WC/inflation/replacement | FR-FIN-004..007 | T-FIN | G1 |
| grace مسجل غير مطبق | FR-FIN-008/013 | T-FIN profile regression | G1 |
| Monte Carlo ثابت وغير معاير | FR-FIN-011/012 | T-MC | G1/G3 |
| profile_id غير مار end-to-end | FR-LND-004 | T-LND regression | G5 |
| ملفات ممولين reference_only | FR-LND-001..003 | T-LND | G5/G7 |
| أربعة sector profiles فقط | FR-CLS, FR-ARC, FR-TEC | T-CLS/ARC/TEC | G3 |
| ثمانية قطاعات عريضة لا ISIC4 | FR-CLS-001 | T-CLS | G3 |
| ستة مخاطر وحدود عامة | FR-RSK-001..003 | T-RSK | G5 |
| DIB/Manifest/registries غير مكتملة | FR-DIB-001..008 | T-DIB | G2 |
| file/PDF/quote mapping ناقص | FR-DIB-006/007, FR-EVD | T-DIB/T-EVD | G2/G4 |
| data العامة ≠ موردي المعدات | FR-DIB-007, FR-EVD-003/004 | T-EVD | G4 |
| البيانات المجانية للاستفادة لا إعادة البيع | FR-EVD-003 | T-EVD license | G4 |
| الدراسة الفنية/التسويقية/التراخيص ناقصة | FR-MKT, FR-TEC, FR-RPT | T-MKT/TEC/RPT | G4/G6 |
| نموذج منشآت استرشادي غير ملزم | Levels + FR-LND-003 | claim tests | G5/G7 |
| متطلبات وزارة المالية قد تتطلب مكتبًا معتمدًا | FR-REV-002 | T-REV | G7 |
| العناية الواجبة والجدارة الائتمانية | FR-LND-005/006, FR-RSK | T-LND/RSK | G5 |
| لا معيار واحد لكل البنوك | FR-LND-001/002 | profile matrix tests | G5 |
| صلاحية «أي مشروع» غير مثبتة | FR-CLS/ARC + coverage metric | golden cases | G3 |
| تقارير/UI قد توحي باكتمال غير موجود | FR-RPT-004, FR-UX-005/006 | T-RPT/UX/E2E | G6 |
| حماية AAS/Snapshot/tenant | invariants + NFR-SEC/AUD | freeze/security tests | كل البوابات |
| FC20-05..16 محجوبة/ACR_REQUIRED | WS mapping | package-specific tests | حسب الحزمة |
| PR #42/#10 غير مدمجة | WS-02 rule | rebase/audit evidence | G2 |
| لا قبول مصرفي خارجي | FR-REV + G7 | pilot/UAT | G7 |

**قاعدة الاكتمال:** لا تُعتبر هذه المصفوفة مكتملة إذا وجد نقد بلا Requirement وTest وGate.

---

## 21. المسؤوليات

| الدور | المسؤولية | لا يملك |
|---|---|---|
| Product Owner | النطاق والclaims ومستوى المخرج | تجاوز بوابة فنية/نظامية |
| Principal Architect | الحدود والعقود وACR والتتبع | اعتماد مالي مهني منفرد |
| Finance Reviewer/CPA | المعادلات والقوائم والحالات الذهبية | قرار تمويل الجهة |
| Sector Expert/Engineer | النموذج الفني والافتراضات القطاعية | تغيير Runtime |
| Credit Analyst | lender profile والجاهزية والمخاطر | إعلان قبول مؤسسي |
| Security/QA | tenant/negative/reliability/evidence | تخفيض الشدة لإغلاق شكلي |
| Licensed/Accredited Office | توقيع/اعتماد حين تشترطه الجهة | تغيير Snapshot بلا revision |
| Institution | قرار القبول والتمويل | لا تمثله ASIE دون اتفاق |

يجب تسمية الأشخاص/الجهات الفعلية قبل G6/G7؛ الأدوار غير المسماة تبقى `UNKNOWN`.

---

## 22. أول شريحة تنفيذية بعد قبول الوثيقة

**الاختيار:** S1 — ACR للنموذج المالي المتكامل والعقود، لا تعديل Finance مباشرة.

السبب: أكبر خطر هو أن تُبنى DIB/UX وتقارير جديدة فوق نموذج مالي غير قادر على تمثيل المشاريع المطلوبة. ولأن Finance ومسار Snapshot محميان، فإن البدء الصحيح هو عقد تغيير ضيق يحدد:

- schemas والمدخلات والفترات والوحدات والدقة.
- three-statement invariants.
- debt/working-capital/capex/tax interfaces.
- versioning/migration/backward compatibility.
- module/socket/output impacts والسجلات المطلوبة.
- threat model وrollback.
- golden test vectors وقواعد قبول المحاسب.

مخرجات S1 المطلوبة:

1. ACR مرشح مع affected paths وfreeze impact.
2. JSON schemas للنموذج المالي وarchetype interface.
3. test specification لـ T-FIN/T-PROP.
4. migration/rollback design.
5. قرار بوابة G0 ثم إذن بدء S2؛ لا كود قبل ذلك.

---

## 23. قائمة تحقق القبول النهائي للبرنامج

- [ ] كل نقد سابق موجود في القسم 20.
- [ ] كل فجوة مرتبطة بـFR/NFR.
- [ ] كل FR له AC/Test/Gate.
- [ ] كل ملف ممول يحمل status/version/source/effective date.
- [ ] كل archetype له golden case ومراجع.
- [ ] Finance متكامل ومطابق.
- [ ] DIB/Manifest حي ومحكوم.
- [ ] ISIC4 والتراخيص محدثة ومصدرة.
- [ ] السوق والفني والأدلة مكتملة.
- [ ] public data منفصلة عن suppliers وتراخيصها موثقة.
- [ ] reports تطابق Snapshot.
- [ ] مراجعات accountant/sector/credit مكتملة.
- [ ] tenant/security/restore/cross-platform تمر.
- [ ] exact commit/workflows/artifacts/checksums موثقة.
- [ ] rollback مجرب.
- [ ] residual risks موقعة.
- [ ] pilot/UAT خارجي موثق لمستوى L2/L3.
- [ ] لا claim يتجاوز المستوى المثبت.
- [ ] تفويض الإصدار مستقل ومثبت.

إذا بقي أي بند مطلوب للمستوى المستهدف غير مكتمل، تكون النتيجة `FAIL` أو `CONDITIONAL PASS` مع حجب الادعاء الموافق، وليس «نجاحًا جزئيًا» مبهمًا.

---

## 24. قرار النفاذ

تدخل هذه الوثيقة حيز العمل بعد مراجعتها ودمجها في `main`. حتى الدمج هي `DRAFT AUTHORITATIVE CANDIDATE`.

بعد الدمج:

- تصبح المرجع الملزم لبرنامج إكمال دراسة الجدوى والجاهزية التمويلية.
- لا تلغي PROGRAM-CLOSE-10 أو FOUNDATION-COMPLETE-20 أو EKB أو Freeze.
- لا تمنح تفويض شبكة/Provider/Production.
- لا تثبت أن المنصة اكتملت.
- يظل الحكم الحالي `BLOCK` للمستوى المهني/المصرفي إلى أن تمر البوابات.
- يستمر التنفيذ شريحةً شريحةً، ولا تُغلق المهمة النهائية قبل G8 والتفويض المستقل.

**النجاح المقبول ليس كثرة الميزات؛ بل أن تكون كل نتيجة صحيحة، قابلة للتتبع، قابلة للمراجعة، صريحة في حدودها، ومثبتة على commit بعينه.**
