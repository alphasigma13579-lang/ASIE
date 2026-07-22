# Sector Taxonomy Algorithms

## خوارزميات تصنيف القطاعات

Owner:

المالك:

`Market Intelligence Module` / موديول ذكاء السوق.

## SECTOR-ALG-01 Sector Mapping

## ربط القطاع

Purpose:

الهدف:

Map user project context to ASIE official sector, subsector, and activity classification.

ربط سياق مشروع المستخدم بالقطاع الرسمي والتصنيف الفرعي وتصنيف النشاط في ASIE.

Inputs:

المدخلات:

- User idea / فكرة المستخدم.
- User selected sector / القطاع المختار.
- AI suggested classification / التصنيف المقترح من AI.
- Location / الموقع.
- Project size / حجم المشروع.

Steps:

الخطوات:

1. Match project to official sector taxonomy.
2. Select primary sector.
3. Select subsector.
4. Generate or validate activity classification.
5. Attach bilingual labels.
6. Return `sector.mapping.result.v1`.

Forbidden:

الممنوع:

- Project without primary sector.
- مشروع بلا قطاع رئيسي.

- English-only sector labels in Arabic UI.
- تسميات إنجليزية فقط في واجهة عربية.

## SECTOR-ALG-02 Sector Source Mapping

## ربط القطاع بالمصادر

Purpose:

الهدف:

Select evidence sources relevant to each sector.

اختيار مصادر الأدلة المناسبة لكل قطاع.

Steps:

الخطوات:

1. Read sector and subsector.
2. Select official Saudi sources first.
3. Select sector reports.
4. Select price sources if relevant.
5. Select labor sources if relevant.
6. Select global benchmarks if useful.
7. Produce source plan.

Output:

المخرج:

`sector.source.plan.v1`.

## SECTOR-ALG-03 Investment Indicator Pack Builder

## باني حزمة مؤشرات الاستثمار

Purpose:

الهدف:

Build sector-specific investment indicators.

بناء مؤشرات استثمار مخصصة لكل قطاع.

Indicator Families:

عائلات المؤشرات:

- Growth / النمو.
- Market size / حجم السوق.
- Competition / المنافسة.
- Regulation / التنظيم.
- Capital intensity / كثافة رأس المال.
- Labor dependency / الاعتماد على العمالة.
- Price volatility / تذبذب الأسعار.
- Location sensitivity / حساسية الموقع.
- Vision 2030 alignment / التوافق مع رؤية 2030.
- Sustainability / الاستدامة.

Output:

المخرج:

`sector.investment.indicator.pack.v1`.

## SECTOR-ALG-04 Sector Evaluation Criteria Selection

## اختيار معايير تقييم القطاع

Purpose:

الهدف:

Prevent generic evaluation by selecting criteria appropriate to the sector.

منع التقييم العام عبر اختيار معايير مناسبة للقطاع.

Examples:

أمثلة:

- Real Estate prioritizes location, rent, demand, regulation, and capital intensity.
- العقار يعطي أولوية للموقع والإيجار والطلب والتنظيم وكثافة رأس المال.

- Technology prioritizes talent, digital adoption, scalability, cybersecurity, and cloud readiness.
- التقنية تعطي أولوية للمواهب والتبني الرقمي وقابلية التوسع والأمن السيبراني والجاهزية السحابية.

- Food Security prioritizes supply chain, import dependency, water, seasonality, and regulation.
- الأمن الغذائي يعطي أولوية لسلاسل الإمداد والاعتماد على الاستيراد والمياه والموسمية والتنظيم.

- Healthcare prioritizes regulation, licensing, insurance, location, and demand demographics.
- الصحة تعطي أولوية للتنظيم والترخيص والتأمين والموقع والديموغرافيا.

Output:

المخرج:

`sector.evaluation.criteria.v1`.

## SECTOR-ALG-05 Sector Opportunity Signal Detection

## اكتشاف إشارات الفرص حسب القطاع

Purpose:

الهدف:

Detect investment opportunity signals based on sector-specific evidence.

اكتشاف إشارات الفرص الاستثمارية بناءً على أدلة خاصة بالقطاع.

Steps:

الخطوات:

1. Load sector indicator pack.
2. Load trend and gap packs.
3. Load similar cases.
4. Load regulatory and opportunity signals.
5. Score opportunity signals.
6. Attach evidence links.

Forbidden:

الممنوع:

- Opportunity signal without evidence link.
- إشارة فرصة بلا رابط دليل.

