# External Intelligence Algorithms

## خوارزميات الذكاء الخارجي

Owner:

المالك:

`Market Intelligence Module` / موديول ذكاء السوق.

## EXT-ALG-01 Approved Open Evidence Auto Fetch

## الجلب التلقائي للأدلة العامة

Purpose:

الهدف:

Fetch approved open data automatically from exact official open datasets and open APIs.

جلب الأدلة العامة تلقائيًا حتى لا يبحث المستخدم عن التقارير يدويًا.

Inputs:

المدخلات:

- Project sector / قطاع المشروع.
- Precise classification / التصنيف الدقيق.
- Saudi geo context / السياق الجغرافي السعودي.
- Project size / حجم المشروع.
- Requested evidence categories / فئات الأدلة المطلوبة.

Steps:

الخطوات:

1. Build source plan by sector and country.
2. Check Pinecone evidence cache first.
3. If cache is stale or missing, call approved adapters.
4. Fetch only exact open datasets, documented open API responses, and approved machine-readable resources.
5. Parse and normalize evidence.
6. Require source URL and retrieved date.
7. Score source reliability.
8. Produce `market.public.evidence.pack.v1`.

Forbidden:

الممنوع:

- Asking user to upload public reports.
- مطالبة المستخدم برفع تقارير عامة.

- Using unsupported evidence.
- استخدام أدلة غير مدعومة.

- Fetching public pages, reports, marketplaces, or reference-only links.
- جلب صفحات أو تقارير أو أسواق أو روابط مرجعية غير مفتوحة.

## EXT-ALG-02 Deep Research Orchestrator

## منسق البحث العميق

Purpose:

الهدف:

Use research capabilities only to discover candidate official open-data locators; discovery does not authorize content retrieval.

استخدام قدرات بحث قوية مثل Tavily وKIMI لاكتشاف الأدلة تحت تحكم ASIE.

AI Role:

دور الذكاء:

KIMI may propose search queries, inspect retrieved content, summarize evidence, and identify missing evidence.

يجوز لـ KIMI اقتراح استعلامات بحث، قراءة المحتوى المسترجع، تلخيص الأدلة، وتحديد الأدلة الناقصة.

Steps:

الخطوات:

1. Receive research objective from Market Intelligence Module.
2. Generate search strategy.
3. Execute metadata discovery through an approved search adapter.
4. Keep candidate URLs as locators only.
5. Run `OPEN-DATA-ALG-11` before any network retrieval or claim extraction.
6. Reject candidates without official open-use evidence.
7. Deduplicate eligible dataset/API candidates.
8. Return candidates for internal source approval, not directly to Evidence Pack Assembly.

Forbidden:

الممنوع:

- KIMI crawling without adapter.
- زحف KIMI بدون موصل.

- KIMI inventing evidence.
- اختراع KIMI للأدلة.

- Claim without URL.
- معلومة بلا رابط.

- Fetching or summarizing candidate content before strict-profile approval.
- جلب أو تلخيص المحتوى قبل اعتماد الأهلية الصارمة.

## EXT-ALG-03 Similar Case Discovery

## اكتشاف التجارب المشابهة

Purpose:

الهدف:

Find similar cases only inside already approved open datasets and open APIs.

إيجاد مشاريع أو أعمال أو مناقصات أو دراسات حالة أو تقارير عامة مشابهة لمشروع المستخدم.

Inputs:

المدخلات:

- Sector / القطاع.
- Classification / التصنيف.
- Location / الموقع.
- Project size / حجم المشروع.
- Keywords / كلمات مفتاحية.

Steps:

الخطوات:

1. Generate Arabic and English structured queries.
2. Query approved open-data adapters only.
3. Extract candidate aggregate cases without personal or user-generated marketplace content.
4. Require source URL.
5. Score similarity by sector, geography, business model, and scale.
6. Produce `market.similar.case.pack.v1`.

Outputs:

المخرجات:

- Similar case title / عنوان التجربة.
- URL / الرابط.
- Source type / نوع المصدر.
- Similarity score / درجة التشابه.
- Relevance explanation / شرح الصلة.

## EXT-ALG-04 Price Sampling Auto Fetch

## الجلب التلقائي لعينات الأسعار

Purpose:

الهدف:

This algorithm is disabled under `strict_open_data_only_v1`. Marketplace prices are not open-data evidence merely because listings are public.

جلب عينات أسعار من الأسواق والمصادر العامة المعتمدة.

Former source candidates, now blocked from automated access:

المصادر:

- Noon / نون.
- Amazon.sa / أمازون السعودية.
- Amazon / أمازون.
- Alibaba.com / علي بابا.
- OpenSooq / السوق المفتوح.
- Haraj / حراج.
- Aqar.sa / عقار for real estate signals / لإشارات العقار.
- Other approved marketplaces / أسواق معتمدة أخرى.

Steps:

الخطوات:

1. Return `SOURCE_PROFILE_UNSUPPORTED` for marketplace requests.
2. Use an exact official open price/index dataset when available.
3. Otherwise return `insufficient_open_data`; do not crawl or ask AI to estimate.

Forbidden:

الممنوع:

- Price without URL.
- سعر بلا رابط.

- AI guessed price.
- سعر مخمن من AI.

## EXT-ALG-05 Evidence Link Enforcement

## فرض رابط الإثبات

Purpose:

الهدف:

Ensure every user-visible evidence claim has a traceable source.

ضمان أن كل معلومة ظاهرة للمستخدم لها مصدر قابل للتتبع.

Rule:

القاعدة:

No source URL, no evidence.

لا رابط مصدر، لا دليل.

Required Metadata:

Metadata المطلوبة:

- Evidence id / معرف الدليل.
- Source title / عنوان المصدر.
- Source URL / رابط المصدر.
- Retrieved date / تاريخ الجلب.
- Source type / نوع المصدر.
- Confidence score / درجة الثقة.

Failure:

الفشل:

Unsupported claims are excluded from Finance, Decision, and Reports.

المعلومات غير المدعومة تستبعد من التمويل والقرار والتقارير.

## EXT-ALG-06 Pinecone Evidence Cache Retrieval

## استرجاع ذاكرة الأدلة من Pinecone

Purpose:

الهدف:

Use Pinecone as evidence cache and retrieval index, not source of truth.

استخدام Pinecone كذاكرة أدلة وفهرس استرجاع، وليس كمصدر حقيقة.

Steps:

الخطوات:

1. Query by sector, classification, country, and evidence category.
2. Filter by freshness and source metadata.
3. Return evidence ids and source metadata.
4. If stale, trigger public evidence auto fetch.
5. Never return vector text without original source metadata.

Forbidden:

الممنوع:

- Pinecone as final numeric authority.
- Pinecone كمرجع رقمي نهائي.

- Evidence without original URL.
- دليل بلا رابط أصلي.

## EXT-ALG-07 Source Legal Access Evaluation

## تقييم الوصول القانوني للمصدر

Purpose:

الهدف:

Classify whether ASIE can access a source automatically.

تصنيف هل يمكن لـ ASIE الوصول إلى المصدر تلقائيًا.

Access Classes:

فئات الوصول:

- `official_open_dataset` / مجموعة بيانات رسمية مفتوحة.
- `official_open_api` / API رسمي مفتوح بلا تسجيل أو موافقة خارجية.
- `reference_only` / رابط مرجعي لا يجلبه الخادم.
- `blocked_registration` / يتطلب تسجيلًا أو حسابًا.
- `blocked_license_or_approval` / يتطلب ترخيصًا أو موافقة خاصة.
- `blocked_personal_or_restricted` / شخصي أو مقيّد.
- `unknown` / غير محسوم.

Steps:

الخطوات:

1. Identify source domain and family.
2. Check configured access class.
3. Require explicit open public-reuse terms for the exact dataset/API.
4. Reject registration, login, payment, contract, credential approval, or source-specific permission.
5. Reject personal, user-generated marketplace, micro, restricted, or unknown data.
6. Return `eligible_candidate`, `reference_only`, or `blocked`.

Stop:

توقف:

Only an internally approved `eligible_candidate` may run. `reference_only` must not be resolved by the backend.

إذا كان الوصول `restricted` أو `needs_review`، يمنع الجلب التلقائي.

## EXT-ALG-08 Source Priority Selection

## اختيار أولوية المصدر

Purpose:

الهدف:

Select best source order for each evidence request.

اختيار أفضل ترتيب مصادر لكل طلب دليل.

Priority:

الأولوية:

1. Saudi official / سعودي رسمي.
2. Regulated financial / مالي منظم.
3. Exact open dataset from another official or institutional publisher.
4. Reference-only official document.

Licensed APIs, marketplaces, and general web pages are excluded from automatic evidence selection under the active profile.

Output:

المخرج:

Ordered source plan with fallback list.

خطة مصادر مرتبة مع قائمة بدائل.

## EXT-ALG-09 Source Freshness Evaluation

## تقييم حداثة المصدر

Purpose:

الهدف:

Decide whether evidence is fresh, stale, or expired.

تحديد هل الدليل حديث أو قديم أو منتهي.

Steps:

الخطوات:

1. Read evidence type.
2. Load freshness target.
3. Compare retrieved date and source published date.
4. Return `fresh`, `stale`, or `expired`.
5. If stale, trigger refresh when possible.

## EXT-ALG-10 Source Failure Fallback

## بدائل فشل المصدر

Purpose:

الهدف:

Handle source failure without hallucination or unsafe bypass.

التعامل مع فشل المصدر بدون هلوسة أو تجاوز غير آمن.

Rules:

القواعد:

- API failure may use fresh cache.
- فشل API قد يستخدم كاش حديث.

- Blocked crawler must stop.
- الزاحف المحجوب يجب أن يتوقف.

- Parse failure must be marked `parse_failed`.
- فشل التحليل يوسم `parse_failed`.

- Insufficient price samples return `insufficient_samples`.
- نقص عينات الأسعار يرجع `insufficient_samples`.

- No fallback may invent evidence.
- لا بديل يخترع دليلًا.

## EXT-ALG-11 Source Language Resolution

## تحديد لغة المصدر والعرض

Purpose:

الهدف:

Preserve Arabic and English source context and display evidence in the correct user-facing language.

حفظ سياق المصدر العربي والإنجليزي وعرض الدليل باللغة المناسبة للمستخدم.

Steps:

الخطوات:

1. Detect source language from metadata, domain, and content.
2. Preserve official source name.
3. Store `source_language`.
4. Resolve `display_language` from user interface language.
5. If Arabic UI and English source, show English title when official plus Arabic explanation.
6. If English UI and Arabic source, show Arabic official title when official plus English explanation.
7. Reject evidence with missing language metadata.

Forbidden:

الممنوع:

- Misleading translation of official source names.
- ترجمة مضللة لأسماء المصادر الرسمية.

- Dropping Arabic evidence because it is Arabic.
- إسقاط الدليل العربي لأنه عربي.
