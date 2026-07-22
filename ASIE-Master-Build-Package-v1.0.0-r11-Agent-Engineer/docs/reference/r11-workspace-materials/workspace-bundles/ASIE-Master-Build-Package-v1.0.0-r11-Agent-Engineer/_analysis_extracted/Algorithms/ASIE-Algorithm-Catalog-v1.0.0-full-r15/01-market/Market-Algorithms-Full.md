# Market Algorithms Full

## خوارزميات السوق الكاملة

Owner:

المالك:

`Market Intelligence Module` / موديول ذكاء السوق.

## MI-ALG-01 Source Confidence Scoring

## تقييم ثقة المصدر

Purpose:

الهدف:

Assign a deterministic confidence score to every market source.

منح درجة ثقة حتمية لكل مصدر سوقي.

Inputs:

المدخلات:

- `source_type` / نوع المصدر.
- `issuer` / الجهة المصدرة.
- `country_scope` / نطاق الدولة.
- `published_at` / تاريخ النشر.
- `retrieved_at` / تاريخ الجلب.
- `url` / الرابط.
- `evidence_category` / فئة الدليل.

Base Weights:

الأوزان الأساسية:

| Source Type | Arabic | Weight |
| --- | --- | ---: |
| Saudi official government | حكومي سعودي رسمي | 1.00 |
| Saudi regulated financial | مالي سعودي منظم | 0.90 |
| Saudi institutional report | تقرير مؤسسي سعودي | 0.80 |
| Global report about Saudi market | تقرير عالمي عن السعودية | 0.70 |
| Marketplace fallback | سوق إلكتروني احتياطي | 0.55 |
| Unverified source | مصدر غير متحقق | Reject |

Freshness Factor:

عامل الحداثة:

| Age | Arabic | Factor |
| --- | --- | ---: |
| 0-90 days | 0-90 يوم | 1.00 |
| 91-365 days | 91-365 يوم | 0.85 |
| 1-3 years | سنة إلى 3 سنوات | 0.65 |
| More than 3 years | أكثر من 3 سنوات | Review |

Steps:

الخطوات:

1. Reject source with no issuer or URL.
2. Reject source outside Saudi v1 scope unless it is approved Saudi macro context.
3. Select base weight from source type.
4. Apply freshness factor.
5. Store score with source record.
6. Emit audit event for rejected source.

Output:

المخرج:

`confidence_score` between 0 and 1.

Failure Conditions:

حالات الفشل:

- Missing issuer / جهة مفقودة.
- Missing URL / رابط مفقود.
- Unsupported country / دولة غير مدعومة.

## MI-ALG-02 Evidence Pack Assembly

## بناء حزمة الأدلة

Purpose:

الهدف:

Produce a traceable evidence pack for Finance, AI, Decision, and Reports.

إنتاج حزمة أدلة قابلة للتتبع للتمويل والذكاء والقرار والتقارير.

Evidence Categories:

فئات الأدلة:

- Demand / الطلب.
- Competitors / المنافسون.
- Prices / الأسعار.
- Regulation / التنظيم.
- Geography / الجغرافيا.
- Seasonality / الموسمية.
- Macro context / السياق الاقتصادي العام.

Steps:

الخطوات:

1. Receive `market.query.request.v1`.
2. Validate Saudi scope.
3. Resolve required evidence categories.
4. Fetch only through approved source adapters.
5. Score sources using `MI-ALG-01`.
6. Group claims by category.
7. Mark missing evidence explicitly.
8. Produce `market.evidence.pack.v1`.

Stop Conditions:

حالات التوقف:

- No valid source for required category.
- لا يوجد مصدر صحيح لفئة مطلوبة.

- Unsupported geography.
- جغرافيا غير مدعومة.

## MI-ALG-03 Price Outlier Filtering

## فلترة الأسعار الشاذة

Purpose:

الهدف:

Prevent unrealistic price samples from entering deterministic finance.

منع الأسعار غير الواقعية من دخول التمويل الحتمي.

Minimum Sample Rule:

قاعدة الحد الأدنى:

At least 5 valid samples are required for a usable market price estimate.

يلزم 5 عينات صحيحة على الأقل لاستخدام تقدير سعر سوقي.

Steps:

الخطوات:

1. Normalize currency to configured currency.
2. Normalize unit.
3. Reject sample without source, timestamp, unit, or currency.
4. Sort valid prices.
5. Calculate Q1, median, Q3.
6. Calculate `IQR = Q3 - Q1`.
7. Flag lower outlier below `Q1 - 1.5 * IQR`.
8. Flag upper outlier above `Q3 + 1.5 * IQR`.
9. Emit `market.outlier.report.v1`.

Failure:

الفشل:

If fewer than 5 samples remain, output `insufficient_samples`.

إذا بقي أقل من 5 عينات، يكون المخرج `insufficient_samples`.

## MI-ALG-04 Geo Context Resolution

## حل السياق الجغرافي

Purpose:

الهدف:

Convert GPS or Map Pin into controlled Saudi market context.

تحويل GPS أو Pin إلى سياق سوق سعودي مضبوط.

Steps:

الخطوات:

1. Require latitude and longitude.
2. Validate coordinate inside Saudi borders.
3. Resolve region, city, district.
4. Resolve nearby competitor search radius.
5. Produce `market.geo.context.v1`.

Forbidden:

الممنوع:

- Manual city as sole source.
- المدينة النصية كمصدر وحيد.

## MI-ALG-05 Source Health Scoring

## تقييم صحة المصدر

Purpose:

الهدف:

Track whether data providers are usable.

تتبع قابلية استخدام مزودي البيانات.

Signals:

الإشارات:

- Success rate / معدل النجاح.
- Latency / زمن الاستجابة.
- Error rate / معدل الأخطاء.
- Freshness / الحداثة.
- Contract compliance / الالتزام بالعقد.

Output:

المخرج:

`market.source.health.v1`.

