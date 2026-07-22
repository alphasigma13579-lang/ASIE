# ASIE — مخطط التحول إلى نظام ذكاء سياقي واستراتيجي

## أطروحة المنتج

لا تنتهي ASIE عند تقرير الجدوى. تحوّل نتيجة الجدوى إلى سؤال تشغيلي يومي:

> ما مدى واقعية هذا المشروع في السياق الحالي، ما المخاطر التي تعلّمناها من حالات مشابهة، وما الخطوة التي يجب تنفيذها الآن؟

لا تعد المنصة بـ«اليقين». تقدم **ثقة قابلة للتتبع**: نتيجة، سياق، دليل، افتراض، فجوة، وخطوة تنفيذية.

## 1. Benchmark Reality Engine

بعد تكوين Snapshot، تظهر وحدة «أين أنت من الواقع؟» ولا تعيد حساب الحكم المالي.

| العنصر | العقد الخلفي المقترح | العرض للعميل |
|---|---|---|
| حالة مرجعية | `benchmark_case_id`, geography, sector, lifecycle, scale band | بطاقة مشروع مشابه محلي/إقليمي/عالمي |
| حالة الأداء | `outcome_status`, status_basis, observed_at | ناجح/متعثّر/قيد التشغيل + تاريخ وحالة الدليل |
| عوامل الواقع | `factor_id`, factor_type, summary, evidence_refs | ما الذي ساعد أو أضر بالحالة |
| صلة مشروع العميل | `similarity_dimensions`, `similarity_limitations` | لماذا هذه الحالة مفيدة، وأين لا تنطبق |
| مصدر | publisher, source_ref, review_status, terms | رابط/مرجع وحالة المراجعة |

لا يسمح بعرض عبارة «سبب النجاح» إلا باعتبارها عاملًا موثقاً أو استنتاجاً موسوماً، لا حقيقة مطلقة.

## 2. Macro-Context Integration

وحدة «السياق الاقتصادي» تربط المشروع بحزمة مؤشرات لا برقم معزول:

```text
macro_signal_id
indicator_name / geography / period / value / unit
publisher / source_ref / review_status / observed_at
relevance_to_project / limitations / evidence_refs
```

تعرض الواجهة: اتجاه المؤشر، لماذا يهم المشروع، مدى ملاءمة النطاق، وتاريخ آخر مراجعة. لا تستخدم اسم بنك أو جهة أو شركة استشارية كإشارة هيبة من دون مصدر مرخص ومراجع.

## 3. Advisory Core المحكوم

في الإنتاج، الاستشارة ليست مالكة للحكم أو الأرقام أو المصدر. هي طبقة فوق Snapshot مغلق ومدخلات سياق مراجعة:

```text
sealed Snapshot + reviewed Context Pack
  → advisory policy / template / local reasoning adapter
  → recommendation cards
  → human review and action tracking
```

لكل توصية: `recommendation_id`, rationale_refs, confidence, limitations, owner, due_window, review_state`.

### وضع التطوير الحالي

- `AI provider = DISABLED / DENY_ALL` يبقى كما هو.
- تستخدم المنصة توصيات تجريبية محلية من قوالب محكومة (`DEMO / LOCAL ONLY`).
- لا تنسب هذه التوصيات إلى AI أو مصدر خارجي حقيقي، ولا تغير Sovereign Verdict أو Snapshot.

## 4. Execution Compass

يتحول Report إلى خطة متابعة:

| الطبقة | مثال |
|---|---|
| الآن | تحقق من الإيجار والمواقف للموقع المرشح |
| خلال 7 أيام | استكمل دليل المنافسين والأسعار |
| قبل الإطلاق | راجع قائمة الترخيص والتمويل مع المختص |
| حالة التقدم | لم يبدأ / جارٍ / بانتظار دليل / مكتمل |
| مرجع القرار | Snapshot أو Guidance/Benchmark record الذي سبب الإجراء |

لا يتغير Snapshot عند تحديث تقدم التنفيذ؛ التقدم Human/Operations overlay مستقل ومراجع.

## 5. واجهة العميل: مقر العمل اليومي

التبويبات البسيطة:

1. **قراري اليوم:** الحكم، السبب، الإجراء الأهم.
2. **اختبار الواقع:** Benchmark cases + المنافسة + السياق الاقتصادي.
3. **خارطة التنفيذ:** خطوات، مالك، موعد، تقدم، عائق.
4. **تقاريري:** Report، Decision Pack، تغيرات Snapshot.

كل تبويب يبدأ بجواب واحد، ثم drill-down اختياري. لا يعرض واجهة Runtime أو جداول خام أو عشرات KPIs بلا قرار.

## 6. بيانات التطوير المحاكاة

يسمح محلياً بإنشاء:

- حالات طاقة خضراء محلية/إقليمية/عالمية محاكاة.
- مؤشرات اقتصادية محاكاة منسوبة إلى `assumed_source`.
- مقالات/عوامل نجاح أو تعثر محاكاة.
- توصيات وخارطة تنفيذ محاكاة.

كل سجل يجب أن يحمل `data_mode=demo_simulated_external`, `DEMO / LOCAL ONLY`, و`production_admission=blocked`. تزال أو تستبدل بمصادر مراجعَة قبل الإطلاق.

## 7. الترتيب التنفيذي

1. نماذج `BenchmarkCase`, `MacroSignal`, `GuidanceRecord`, `ExecutionAction` محلية + seed demo.
2. API مفوض ومنظمياً لهذه السجلات، منفصل عن AAS Runtime وSnapshot.
3. Widgets «اختبار الواقع» و«خارطة التنفيذ» داخل Live Cockpit.
4. overlay مستقل لتقدم التنفيذ وربطه بـSnapshot المرجعي.
5. لاحقاً فقط: مصادر خارجية حقيقية وAI adapter ضمن P0 وسياسات قبول ومراجعة.
