# External Source Adapter Catalog

## كتالوج موصلات المصادر الخارجية

## Rule

## القاعدة

Every external source must enter ASIE through an approved adapter inside `Market Intelligence Module / موديول ذكاء السوق`, except product analytics which enter through `Audit / Observability Module / موديول التدقيق والمراقبة`.

كل مصدر خارجي يدخل ASIE عبر موصل معتمد داخل `Market Intelligence Module / موديول ذكاء السوق`، باستثناء تحليلات المنتج التي تدخل عبر `Audit / Observability Module / موديول التدقيق والمراقبة`.

**Active profile:** `strict_open_data_only_v1`. The catalog includes discovery candidates and reference links, but only an exact official open dataset or official open API with explicit public-reuse terms may be enabled. All other entries are blocked or reference-only regardless of older access-mode descriptions.

**الملف النشط:** البيانات المفتوحة فقط. وجود المصدر في الكتالوج لا يعني السماح بجلبه.

## Strict Profile Allowlist

| Source | Exact scope | Status | Binding condition |
| --- | --- | --- | --- |
| `data.gov.sa` | Exact official open dataset/API record | Eligible candidate | Explicit open-use terms, public classification, no login/approval, no personal data |
| `database.stats.gov.sa` | Exact published statistical table/export | Eligible candidate | GASTAT open-use policy, attribution, transformation disclosure |
| `dp.stats.gov.sa` | Exact documented public open API endpoint | Eligible candidate | No registration/approval; documented scope and rate limits |
| `mostaql.com/projects` | Outbound link only | Reference only | No server-side request, ingestion, storage, AI summary, embedding, or derived dataset |
| All other catalog entries | Discovery record only | Blocked by default | Must independently satisfy `strict_open_data_only_v1` before enablement |

## Source Catalog

## كتالوج المصادر

| Source | Arabic | Access Mode | Evidence Type | Priority | Notes |
| --- | --- | --- | --- | --- | --- |
| `World Bank API` | API البنك الدولي | API Adapter | Global indicators, benchmarks | High | Benchmark only for v1, not project country scope |
| `data.gov.sa` | بنك البيانات الوطني ومنصة البيانات المفتوحة | Official API / published dataset | Government open datasets and metadata | Highest | Dataset-level license and approval required |
| `MOF` | وزارة المالية | Exact official open dataset/API only | Fiscal policy, budgets, economic context | High | Block unless open-use evidence passes; no site crawling |
| `SDB` | بنك التنمية الاجتماعية | Exact official open dataset/API only | Funding and SME indicators | High | Block unless open-use evidence passes |
| `SAMA` | البنك المركزي السعودي | Exact official open dataset/API only | Monetary indicators, finance context | High | Block unless open-use evidence and sector terms pass |
| `GASTAT Statistical Database` | قاعدة البيانات الإحصائية للهيئة العامة للإحصاء | Official open API / published statistical export | Saudi statistics, demographics, economic and social indicators | Highest | `database.stats.gov.sa`; attribute GASTAT and disclose ASIE transformations |
| `SDAIA Portal Terms` | شروط وأحكام بوابة سدايا | Outbound strategy/legal reference | Portal-use and intellectual-property caution | Reference | Human review only; no automated retrieval or copied clauses |
| `NCA National Cybersecurity Strategy` | الاستراتيجية الوطنية للأمن السيبراني | Outbound strategy reference | Security, resilience, trust, capability, and growth alignment | Reference | Not a substitute for NCA control documents |
| `GOV.SA E-Participation` | منصة المشاركة الإلكترونية | Outbound service-design reference | Participation, consultation, feedback, and co-creation patterns | Reference | No consultation, submission, metric, or personal-data ingestion |
| `DGA Sustainable Development` | التنمية المستدامة لهيئة الحكومة الرقمية | Outbound strategy reference | Sustainability and SDG alignment | Reference | No copying or certification claims |
| `DGA Digital Transformation` | التحول الرقمي لهيئة الحكومة الرقمية | Outbound strategy reference | Digital-first, governance, interoperability, and capability themes | Reference | Overview, not a formal compliance standard |
| `SDAIA National Strategy for Data and AI` | الاستراتيجية الوطنية للبيانات والذكاء الاصطناعي | Outbound strategy reference | National data and AI alignment | Reference | Canonical URL once; human review only; no automated retrieval |
| `HRSD` | وزارة الموارد البشرية والتنمية الاجتماعية | Exact official open dataset/API only | Aggregate labor and employment indicators | High | Personal, case-level, registered, or approval-based routes blocked |
| `laws.boe.gov.sa` | هيئة الخبراء بمجلس الوزراء، الأنظمة واللوائح | Outbound reference/citation | Official regulatory text | Highest | No bulk ingestion; cite exact law/version; Arabic governs interpretation |
| `expro.gov.sa` | هيئة كفاءة الإنفاق والمشروعات الحكومية | Exact official open dataset/API or reference | Project and expenditure-efficiency information | High | EXPRO is not Etimad; blocked unless exact open-use evidence passes |
| `forsah.sa` | فرصة | Reference only by default | Opportunities and SME signals | Reference | No crawling; exact open feed must pass before reconsideration |
| `tendersalerts.com` | تنبيهات المناقصات | Reference only | Tender alerts | Reference | Non-official and not open-data evidence |
| `Vision 2030` | رؤية 2030 | Reference/citation or exact open resource | National targets, strategic alignment | High | No crawling under strict profile |
| `AlAhli Tadawul` | الأهلي تداول | Reference only | Financial and sector reports | Reference | No parser under strict profile |
| `AlRajhi Capital` | الراجحي المالية | Reference only | Financial and sector reports | Reference | No parser under strict profile |
| `Riyad Capital` | الرياض المالية | Reference only | Financial and sector reports | Reference | No parser under strict profile |
| `McKinsey` | ماكينزي | Reference only | Global reports and case studies | Reference | No web retrieval or report copying |
| `Noon` | نون | Reference only | Product listings | Reference | Automated price sampling blocked |
| `Amazon.sa` | أمازون السعودية | Reference only | Saudi product listings | Reference | Automated price sampling blocked |
| `Amazon` | أمازون | Reference only | Product listings | Reference | Automated price sampling blocked |
| `Alibaba.com` | علي بابا | Reference only | Equipment and wholesale listings | Reference | Automated price sampling blocked |
| `OpenSooq` | السوق المفتوح | Reference only | Used/new listings | Reference | Automated price sampling blocked |
| `Haraj` | حراج | Reference only | Local used/new listings | Reference | Automated price sampling blocked |
| `Aqar.sa` | عقار | Reference only | Real-estate listings | Reference | Automated ingestion blocked |
| `Mostaql Projects` | مشاريع مستقل | Outbound reference link only | Human discovery outside ASIE | Reference | Not open data; automated ingestion blocked under strict profile |
| `LinkedIn Marketing/Data API` | LinkedIn API | Blocked external evidence source | Labor and audience signals | Blocked | Licensed/registered route excluded by strict profile |
| `Google Analytics` | تحليلات جوجل | Analytics API Adapter | Product usage analytics | Operational | Not market/finance evidence |
| `Zoho Analytics` | تحليلات زوهو | Analytics API Adapter | Product BI analytics | Operational | Not market/finance evidence |
| `Tavily` | Tavily | Search API Adapter | Search discovery | Research | Discovery only, not source of truth |
| `Pinecone` | Pinecone | Vector Retrieval | Cached evidence retrieval | Cache | Not source of truth |
| `MOF Contracts and Projects` | وزارة المالية: العقود والمشاريع | Official outbound reference / controlled exact file | Government contracts and projects library | Highest for named procurement purpose | `https://www.mof.gov.sa/docslibrary/ContractsProjects/Pages/default.aspx`; not a universal feasibility-study template |
| `MOF Terms and Specifications Forms` | نماذج كراسات الشروط والمواصفات | Official outbound reference / controlled exact form | Government tender booklets by contract type | Highest for applicable form class | `https://www.mof.gov.sa/Knowledgecenter/newGovTendandProcLow/Pages/Terms_Conditions.aspx`; exact competition documents override generic forms |
| `MOF Operating Data Forms` | نماذج البيانات التشغيلية | Official outbound reference / controlled exact form | Operating data for named procurement categories | Highest for applicable category | `https://www.mof.gov.sa/Knowledgecenter/newGovTendandProcLow/Pages/OperatiionData.aspx`; no bulk crawl |
| `MOF Government Procurement Forms Index` | فهرس نماذج المنافسات والمشتريات الحكومية | Official outbound reference / controlled exact form | Qualification, contractor evaluation, forms, contracts, award and operating data | Highest for procurement workflow discovery | `https://www.mof.gov.sa/Knowledgecenter/newGovTendandProcLow/Pages/forms.aspx`; verify exact form/version before use |
| `Etimad Competition Content` | اعتماد: محتوى المنافسات والمشتريات | Official outbound reference / controlled exact form | Law, regulations, guidance, qualification, contractor evaluation, terms/specifications | Highest for government competition workflow | `https://etimad.sa/LandingPage/CompetationContent`; exact live competition package controls |
| `UNIDO Feasibility Manual` | دليل اليونيدو لإعداد دراسات الجدوى الصناعية | International methodology reference | Industrial feasibility concepts and study structure | Methodology | `reference_pending_revalidation`; endpoint returned HTTP 502 on 2026-07-13, so no active methodology card until human revalidation |
| `World Bank Economic Analysis of Investment Operations` | التحليل الاقتصادي للعمليات الاستثمارية للبنك الدولي | International methodology reference | Economic CBA, alternatives, risk, sensitivity and Monte Carlo | Methodology | Reference only; rights and citation controls apply; not Saudi authority |
| `IFC Feasibility Studies` | دراسات الجدوى بمؤسسة التمويل الدولية | International methodology reference | Project-planning and feasibility concepts | Methodology | Reference only; not Saudi authority or project approval |
| `UK Green Book` | الكتاب الأخضر البريطاني للتقييم | International public appraisal methodology reference | Options, appraisal, uncertainty and evaluation concepts | Methodology | Reference only; not Saudi authority and not automatically applicable |
| `Aljdwa` | منصة الجدوى | Commercial methodology reference only | General human inspiration about feasibility practice | Reference | No automated browsing, crawling, scraping, monitoring, AI summary, RAG, embedding, copying, or reconstruction without explicit written permission |

## Required Adapter Fields

## حقول الموصل المطلوبة

- `adapter_id` / معرف الموصل.
- `source_name` / اسم المصدر.
- `source_family` / عائلة المصدر.
- `access_mode` / طريقة الوصول.
- `allowed_outputs` / المخرجات المسموحة.
- `legal_access_status` / حالة الوصول القانونية.
- `freshness_policy` / سياسة الحداثة.
- `fallback_policy` / سياسة البديل.
- `rate_limit_policy` / سياسة حدود الطلب.
- `audit_events` / أحداث التدقيق.
- `source_language` / لغة المصدر.
- `display_language_policy` / سياسة لغة العرض.
- `dataset_or_endpoint_url` / رابط مجموعة البيانات أو نقطة الاتصال المحددة.
- `data_classification` / تصنيف البيانات.
- `license_name`, `license_url`, `license_version_or_hash` / الترخيص وإصداره أو بصمته.
- `terms_url`, `terms_snapshot_hash` / الشروط وبصمتها وقت الاعتماد.
- `lawful_purpose_id` / معرف الغرض المشروع.
- `contains_personal_data`, `contains_sensitive_personal_data` / حالة البيانات الشخصية.
- `commercial_use_status` / حالة الاستخدام التجاري.
- `allowed_http_methods`, `approved_paths` / الطرق والمسارات المحصورة.
- `storage_region`, `cross_border_processing` / موقع المعالجة والنقل خارج المملكة.
- `retention_policy_id` / سياسة الاحتفاظ والإتلاف.
- `legal_approver_id`, `privacy_approver_id`, `cybersecurity_approver_id`, `business_owner_id` / جهات الاعتماد.
- `approved_at`, `review_due_at`, `last_terms_check_at` / زمن الاعتماد والمراجعة.
- `kill_switch` / مفتاح الإيقاف الفوري.
- `strict_profile_status` / `eligible_candidate|enabled|reference_only|blocked`.
- `open_reuse_evidence_url`, `open_reuse_evidence_hash` / دليل الإتاحة العامة وبصمته.
- `requires_external_approval`, `requires_registration`, `requires_payment`, `requires_login` / موانع الملف الصارم.

Approval is dataset/endpoint/path-specific. Approval of `example.gov.sa` does not approve every API, page, file, or subdomain owned by that entity.

الاعتماد للمصدر المحدد وليس للنطاق كله، ويمنع التوسع التلقائي إلى مسارات أو ملفات جديدة.

## Language Display Policy

## سياسة لغة العرض

ASIE supports Arabic and English source handling.

يدعم ASIE التعامل مع المصادر العربية والإنجليزية.

Rules:

القواعد:

- If the source content is Arabic, user-facing evidence title, summary, and labels should appear in Arabic by default.
- إذا كان محتوى المصدر عربيًا، يظهر عنوان الدليل وملخصه وتسمياته للمستخدم بالعربية افتراضيًا.

- If the source content is English, user-facing evidence may appear in English with Arabic explanation when the user interface is Arabic.
- إذا كان محتوى المصدر إنجليزيًا، يجوز عرض الدليل بالإنجليزية مع شرح عربي عندما تكون واجهة المستخدم عربية.

- Technical adapter names remain English with Arabic translation.
- أسماء الموصلات التقنية تبقى بالإنجليزية مع ترجمة عربية.

- Do not mistranslate official names. Preserve official source names.
- لا تترجم الأسماء الرسمية ترجمة مضللة. احفظ أسماء المصادر الرسمية.

- Reports should support bilingual output when requested: Arabic-first for Arabic users, English-first for English users.
- التقارير تدعم إخراجًا ثنائي اللغة عند الطلب: العربية أولًا للمستخدم العربي، والإنجليزية أولًا للمستخدم الإنجليزي.

## Forbidden

## الممنوع

- Direct UI access to source / وصول الواجهة مباشرة للمصدر.
- Direct AI browsing outside adapter / تصفح AI خارج الموصل.
- Finance Engine source access / وصول محرك التمويل للمصدر.
- Using cached evidence without original source URL / استخدام دليل مخزن بلا رابط أصلي.
- Treating a public page as licensed open data / اعتبار الصفحة العامة بيانات مفتوحة مرخصة.
- Replacing a denied data-sharing request with crawling / استبدال طلب مشاركة مرفوض بالزحف.
- CAPTCHA, WAF, login, rate-limit, or technical-control bypass / تجاوز وسائل الحماية أو الدخول أو الحدود.
- Enabling a source with missing or expired human approval / تفعيل مصدر باعتماد بشري ناقص أو منتهي.
- Enabling a registered, licensed, paid, login-based, agreement-based, or externally approved source under `strict_open_data_only_v1`.
- Fetching or deriving data from a `reference_only` source, including Mostaql projects.
- Copying, mirroring, embedding, or reconstructing official strategy-reference pages.
- Treating a strategy page as a legal control, certification, or government endorsement.
- Treating MOF/Etimad procurement forms as a universal government-approved feasibility-study template.
- Treating a general MOF/Etimad form as controlling over exact competition documents, addenda, answers, evaluation criteria, or contract terms.
- Loading Aljdwa pages or copied content into AI, RAG, vectors, search indexes, caches, training sets, or scheduled monitoring.
- Treating UNIDO, World Bank, IFC, Green Book, or Aljdwa as Saudi legal authority, government approval, or project certification.

## Procurement and Methodology Reference Access Matrix

| Reference class | Network behavior | Stored material | AI access | Output label |
| --- | --- | --- | --- | --- |
| Exact MOF/Etimad index page | Human-reviewed metadata check | Canonical metadata, review and hashes | Approved metadata/card only | Official procurement reference |
| Exact official MOF/Etimad form | Controlled retrieval only after purpose/terms/security approval | Exact file in controlled vault plus hash/version/retention | No raw form to external AI without approved lawful basis and security/privacy decision | Official form for named workflow, never universal feasibility approval |
| Exact live competition package | Authorized user/document workflow | Competition-scoped controlled records | Contract-scoped extraction only after approval | Controlling competition document |
| International methodology | Human-reviewed reference | Citation metadata and original ASIE method card | Approved ASIE card only | Methodology reference |
| Aljdwa commercial website | No automated network access | URL, terms decision, original reviewer note/card | Approved original ASIE card only | Commercial methodology reference only |

The controlled vault is an implementation mechanism behind existing Contracts and Zero Trust. It is not a new AAS component or source of authority.
