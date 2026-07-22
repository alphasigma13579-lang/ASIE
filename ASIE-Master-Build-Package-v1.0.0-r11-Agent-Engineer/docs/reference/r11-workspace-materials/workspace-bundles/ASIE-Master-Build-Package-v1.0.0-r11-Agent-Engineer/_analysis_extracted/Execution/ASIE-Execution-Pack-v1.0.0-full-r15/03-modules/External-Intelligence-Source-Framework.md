# External Intelligence Source Framework

## إطار مصادر الذكاء الخارجية

## Core Principle

## المبدأ الأساسي

The user must not search for public evidence manually.

المستخدم لا يجب أن يبحث يدويًا عن الأدلة العامة.

ASIE must automatically fetch public evidence, prices, market reports, regulatory references, similar cases, and source links through controlled adapters and research workers.

يجب على ASIE أن يجلب تلقائيًا الأدلة العامة، الأسعار، تقارير السوق، المراجع التنظيمية، التجارب المشابهة، وروابط المصادر عبر موصلات وعمال بحث مضبوطين.

## No Data Layer Rule

## قاعدة منع Data Layer

This framework is not a `Data Layer`.

هذا الإطار ليس `Data Layer / طبقة بيانات`.

It lives inside:

يوضع داخل:

`Market Intelligence Module / موديول ذكاء السوق`.

## Source Access Modes

## طرق الوصول للمصادر

| Mode | Arabic | Used For | Owner |
| --- | --- | --- | --- |
| `API Source Adapter` | موصل مصدر API | Official APIs and licensed APIs | Market Intelligence |
| `Controlled Web Crawler` | زاحف ويب مضبوط | Public pages without API | Market Intelligence |
| `Document Fetcher + Parser` | جالب ومحلل مستندات | Public PDFs, HTML reports, tables | Market Intelligence |
| `Price Sampling Adapter` | موصل عينات الأسعار | Marketplaces and product prices | Market Intelligence |
| `Deep Research Worker` | عامل بحث عميق | Multi-source discovery with Tavily/KIMI | Market Intelligence |
| `Pinecone Evidence Retrieval` | استرجاع أدلة من Pinecone | Cached evidence and semantic retrieval | AI Advisory via contract |

Under `strict_open_data_only_v1`, `Controlled Web Crawler`, `Price Sampling Adapter`, licensed APIs, registered APIs, and marketplace ingestion are disabled. Only exact official open datasets and official open APIs may produce evidence. Reference-only links must never be fetched by the backend.

## Source Families and Strict-Profile Status

## عائلات المصادر المعتمدة

| Family | Arabic | Examples | Output |
| --- | --- | --- | --- |
| Saudi Government Open Data | بيانات حكومية سعودية مفتوحة | data.gov.sa, GASTAT statistical database, exact agency open datasets/APIs | Eligible only after strict-profile validation |
| Regulations | الأنظمة واللوائح | laws.boe.gov.sa | Reference/citation unless expressly open for machine reuse |
| Opportunities and Tenders | الفرص والمناقصات | expro, forsah, tendersalerts | Blocked unless exact feed is expressly open data |
| Financial Institutions | مؤسسات مالية | AlAhli Tadawul, AlRajhi Capital, Riyad Capital | Reference only unless expressly open data |
| Global Benchmarks | مقارنات عالمية | Exact open World Bank datasets/APIs | Eligible only when open terms pass |
| Marketplaces | الأسواق | Noon, Amazon.sa, Alibaba.com, Haraj, OpenSooq | Automated ingestion blocked |
| Real Estate | العقار | Aqar.sa | Automated ingestion blocked unless official open data is later proven |
| Labor Market | سوق العمل | GASTAT and exact official open labor datasets | Mostaql is reference-only; licensed LinkedIn APIs are blocked |

## User Burden Rule

## قاعدة عبء المستخدم

The user provides:

المستخدم يقدم:

- Project idea / فكرة المشروع.
- Sector and classification / القطاع والتصنيف.
- GPS or Map Pin / GPS أو Pin.
- Project size / حجم المشروع.
- Private documents if available / مستندات خاصة إن وجدت.

The platform provides:

المنصة تقدم:

- Public reports / التقارير العامة.
- Public prices / الأسعار العامة.
- Public regulations / اللوائح العامة.
- Public opportunities / الفرص العامة.
- Similar project cases / تجارب مشاريع مشابهة.
- Evidence links / روابط الإثبات.

## Evidence Link Rule

## قاعدة رابط الإثبات

Every claim shown to the user must include:

كل معلومة تعرض للمستخدم يجب أن تشمل:

- Source title / عنوان المصدر.
- Source URL / رابط المصدر.
- Retrieved date / تاريخ الجلب.
- Source type / نوع المصدر.
- Confidence score / درجة الثقة.
- Evidence id / معرف الدليل.
- Source language / لغة المصدر.
- Display language / لغة العرض.

If a claim has no source link, it must be marked as unsupported and cannot be used for decision or finance.

إذا لم يكن للمعلومة رابط مصدر، توسم كغير مدعومة ولا تستخدم في القرار أو التمويل.

## Similar Case Discovery

## اكتشاف التجارب المشابهة

ASIE must search for public similar cases related to the user's project.

يجب أن تبحث ASIE عن تجارب عامة مشابهة لمشروع المستخدم.

Similar cases may include:

قد تشمل التجارب المشابهة:

- Similar businesses / أعمال مشابهة.
- Published feasibility examples / أمثلة جدوى منشورة.
- Tender outcomes / نتائج مناقصات.
- Case studies / دراسات حالة.
- Market reports / تقارير سوق.
- News or official announcements / أخبار أو إعلانات رسمية.

Each similar case must include a link and evidence metadata.

كل تجربة مشابهة يجب أن تتضمن رابطًا وMetadata للدليل.

## Deep Research Worker

## عامل البحث العميق

KIMI or another strong model may assist deep research only as a controlled worker.

يجوز لـ KIMI أو نموذج قوي آخر المساعدة في البحث العميق فقط كعامل مضبوط.

Allowed:

المسموح:

- Generate search strategies / توليد استراتيجيات بحث.
- Read retrieved snippets and documents / قراءة المقاطع والمستندات المسترجعة.
- Summarize evidence / تلخيص الأدلة.
- Suggest missing evidence categories / اقتراح فئات أدلة ناقصة.

Forbidden:

الممنوع:

- Crawling without adapter / الزحف بدون موصل.
- Inventing facts / اختراع معلومات.
- Inventing prices / اختراع أسعار.
- Using evidence without URL / استخدام دليل بلا رابط.
- Becoming source of truth / التحول إلى مصدر حقيقة.

## Output Packs

## حزم المخرجات

| Pack | Arabic | Purpose |
| --- | --- | --- |
| `market.public.evidence.pack.v1` | حزمة أدلة عامة | Public evidence with links |
| `market.price.sample.pack.v1` | حزمة عينات أسعار | Marketplace price samples |
| `market.similar.case.pack.v1` | حزمة تجارب مشابهة | Similar cases with links |
| `market.trend.pack.v1` | حزمة اتجاهات | Trends over time |
| `market.gap.pack.v1` | حزمة فجوات | Benchmark gaps |
| `market.regulatory.signal.pack.v1` | حزمة إشارات تنظيمية | Rules and compliance |
| `market.opportunity.signal.pack.v1` | حزمة إشارات الفرص | Tenders and opportunities |
