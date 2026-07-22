# Algorithm Ownership Map Full

## خريطة ملكية الخوارزميات الكاملة

| ID | Algorithm | Arabic | Owner | Deterministic | AI Role |
| --- | --- | --- | --- | --- | --- |
| `MI-ALG-01` | Source Confidence Scoring | تقييم ثقة المصدر | Market Intelligence | Yes | Explain only |
| `MI-ALG-02` | Evidence Pack Assembly | بناء حزمة الأدلة | Market Intelligence | Yes | Summarize only |
| `MI-ALG-03` | Price Outlier Filtering | فلترة الأسعار الشاذة | Market Intelligence | Yes | None |
| `MI-ALG-04` | Geo Context Resolution | حل السياق الجغرافي | Market Intelligence | Yes | None |
| `MI-ALG-05` | Source Health Scoring | تقييم صحة المصدر | Market Intelligence | Yes | Explain only |
| `SECTOR-ALG-01` | Sector Mapping | ربط القطاع | Market Intelligence | Yes | Classification assist only |
| `SECTOR-ALG-02` | Sector Source Mapping | ربط القطاع بالمصادر | Market Intelligence | Yes | None |
| `SECTOR-ALG-03` | Investment Indicator Pack Builder | باني حزمة مؤشرات الاستثمار | Market Intelligence | Yes | Summarize only |
| `SECTOR-ALG-04` | Sector Evaluation Criteria Selection | اختيار معايير تقييم القطاع | Market Intelligence | Yes | None |
| `SECTOR-ALG-05` | Sector Opportunity Signal Detection | اكتشاف إشارات الفرص حسب القطاع | Market Intelligence | Yes | Summarize only |
| `EXT-ALG-01` | Approved Open Evidence Auto Fetch | الجلب التلقائي للأدلة المفتوحة المعتمدة | Market Intelligence | Yes | Explain approved open evidence only |
| `EXT-ALG-02` | Deep Research Orchestrator | منسق البحث العميق | Market Intelligence | Controlled | Research worker only |
| `EXT-ALG-03` | Similar Case Discovery | اكتشاف التجارب المشابهة | Market Intelligence | Yes | Summarize only |
| `EXT-ALG-04` | Price Sampling Auto Fetch | الجلب التلقائي لعينات الأسعار | Market Intelligence | Disabled in strict profile | None |
| `EXT-ALG-05` | Evidence Link Enforcement | فرض رابط الإثبات | Market Intelligence | Yes | None |
| `EXT-ALG-06` | Pinecone Evidence Cache Retrieval | استرجاع ذاكرة الأدلة من Pinecone | Market Intelligence + AI Advisory | Yes | Retrieval only |
| `EXT-ALG-07` | Source Legal Access Evaluation | تقييم الوصول القانوني للمصدر | Market Intelligence | Yes | None |
| `EXT-ALG-08` | Source Priority Selection | اختيار أولوية المصدر | Market Intelligence | Yes | None |
| `EXT-ALG-09` | Source Freshness Evaluation | تقييم حداثة المصدر | Market Intelligence | Yes | None |
| `EXT-ALG-10` | Source Failure Fallback | بدائل فشل المصدر | Market Intelligence | Yes | None |
| `EXT-ALG-11` | Source Language Resolution | تحديد لغة المصدر والعرض | Market Intelligence | Yes | None |
| `OPEN-DATA-ALG-01` | Source Discovery and Registration | اكتشاف وتسجيل المصدر الحكومي | Market Intelligence | Yes | Candidate discovery only |
| `OPEN-DATA-ALG-02` | Route and Classification Decision | تحديد مسار وتصنيف البيانات | Audit / Observability policy gate | Yes | None |
| `OPEN-DATA-ALG-03` | Legal Access and License Evaluation | تقييم الوصول والترخيص | Audit / Observability + authorized human approvers | Controlled | Summarize for reviewer only |
| `OPEN-DATA-ALG-04` | Open Data vs Data Sharing Gate | بوابة المفتوح مقابل المشاركة | Audit / Observability policy gate | Yes | None |
| `OPEN-DATA-ALG-05` | Personal Data and Cross-Border Gate | بوابة البيانات الشخصية والنقل الخارجي | Audit / Observability + Privacy/DPO | Controlled | None |
| `OPEN-DATA-ALG-06` | Retrieval Runtime Guard | حارس الجلب وقت التشغيل | Market Intelligence + Zero Trust enforcement | Yes | None |
| `OPEN-DATA-ALG-07` | Content Integrity and Evidence Ledger | سلامة المحتوى وسجل الدليل | Market Intelligence + Audit / Observability | Yes | Explain approved evidence only |
| `OPEN-DATA-ALG-08` | Terms, License, and Freshness Revalidation | إعادة تحقق الشروط والترخيص والحداثة | Audit / Observability + Market Intelligence | Yes | None |
| `OPEN-DATA-ALG-09` | Cybersecurity Control Applicability | تحديد ضوابط الأمن السيبراني المنطبقة | Audit / Observability + Cybersecurity owner | Controlled | None |
| `OPEN-DATA-ALG-10` | Suspension, Revocation, and Incident Kill Switch | التعليق والإلغاء ومفتاح الحوادث | Audit / Observability | Yes | None |
| `OPEN-DATA-ALG-11` | Strict Open-Data-Only Eligibility | أهلية البيانات المفتوحة فقط | Audit / Observability policy gate | Yes | None |
| `OPEN-DATA-ALG-12` | Reference-Only Link Guard | حارس الرابط المرجعي فقط | Market Intelligence + Audit / Observability | Yes | None |
| `REF-ALG-01` | Reference Registration and Canonicalization | تسجيل المرجع وتوحيد رابطه | Market Intelligence | Yes | None |
| `REF-ALG-02` | Original Synthesis and Non-Copying Guard | حارس الصياغة الأصلية وعدم النسخ | Audit / Observability + human reviewers | Controlled | Draft only |
| `REF-ALG-03` | Strategy Alignment Pack Builder | بناء حزمة المواءمة الاستراتيجية | Market Intelligence | Yes | Original ASIE prose only |
| `REF-ALG-04` | Strategy vs Formal Compliance Claim Guard | فصل المرجع الاستراتيجي عن ادعاء الامتثال | Audit / Observability | Yes | None |
| `REF-ALG-05` | Reference Expiry, Withdrawal, and Unavailability | انتهاء المرجع وسحبه وتعذره | Audit / Observability + Market Intelligence | Yes | None |
| `FIN-ALG-01` | Deterministic Finance Calculation | الحساب المالي الحتمي | Finance Engine | Yes | None |
| `FIN-ALG-02` | CapEx / OpEx Classification | تصنيف CapEx و OpEx | Finance Engine | Yes | Assist extraction only |
| `FIN-ALG-03` | Sensitivity Analysis | تحليل الحساسية | Finance Engine | Yes | None |
| `FIN-ALG-04` | MCMC Simulation | محاكاة مونت كارلو | Finance Engine | Yes with seed | None |
| `FIN-ALG-05` | Supplier Quote Parsing Gate | بوابة تحليل عروض الموردين | Finance Engine | Yes after parse | Extract only |
| `FST-ALG-01` | Feasibility Depth Profile Selection | اختيار عمق دراسة الجدوى | Project Wizard | Yes | None |
| `FST-ALG-02` | Study Chapter Completeness Gate | بوابة اكتمال فصول الدراسة | Decision Council | Yes | Explain only |
| `FST-ALG-03` | Cross-Study Reconciliation | مطابقة مكونات الدراسة | Decision Council + owner outputs | Yes | Explain contradictions only |
| `FIN-ALG-06` | Integrated Financial Statement Builder | بناء القوائم المالية المترابطة | Finance Engine | Yes | None |
| `FIN-ALG-07` | Investment Appraisal | التقييم الاستثماري | Finance Engine | Yes | Explain only |
| `FIN-ALG-08` | Working Capital and Funding Requirement | رأس المال العامل والاحتياج التمويلي | Finance Engine | Yes | None |
| `FIN-ALG-09` | Unit Economics and Break-Even | اقتصاديات الوحدة ونقطة التعادل | Finance Engine | Yes | Explain only |
| `FIN-ALG-10` | Debt Service and Covenant Metrics | خدمة الدين ومؤشرات التعهدات | Finance Engine | Yes | None |
| `FIN-ALG-11` | Economic Cost-Benefit Analysis | التحليل الاقتصادي للتكلفة والمنفعة | Finance Engine + Decision synthesis | Yes | Explain only |
| `FIN-ALG-12` | Scenario, Stress, Sensitivity, and MCMC Integration | دمج السيناريوهات والضغط والحساسية ومونت كارلو | Finance Engine | Yes with seed | Explain only |
| `PROC-ALG-01` | Procurement Applicability and Reference Selection | تحديد انطباق ومسار المشتريات | Decision Council | Yes | None |
| `PROC-ALG-02` | Official Form Version and Applicability Gate | بوابة إصدار وانطباق النموذج الرسمي | Audit / Observability + human reviewer | Controlled | None |
| `METH-ALG-01` | Methodology Reference Registration | تسجيل المرجع المنهجي | Market Intelligence + Audit / Observability | Controlled | None |
| `METH-ALG-02` | Commercial Methodology Non-Copying Guard | حارس عدم نسخ المرجع التجاري | Audit / Observability | Yes | None |
| `DEC-ALG-01` | Validation Gate | بوابة التحقق | Decision Council | Yes | Explain failure only |
| `DEC-ALG-02` | Five Sovereign Personas | الشخصيات السيادية الخمس | Decision Council | Controlled | Reasoning only |
| `DEC-ALG-03` | Decision Consensus Scoring | حساب إجماع القرار | Decision Council | Yes | None |
| `DASH-ALG-01` | Output Provenance Envelope Validation | تحقق غلاف إثبات المخرج | Audit / Observability + owner Module | Yes | None |
| `DASH-ALG-02` | Project Readiness Score | حساب جاهزية المشروع | Decision Council | Yes | None |
| `DASH-ALG-03` | Confidence Decomposition | تفصيل مؤشرات الثقة | Decision Council | Yes | None |
| `DASH-ALG-04` | Strategic Framework Pack Assembly | بناء حزمة الأطر الاستراتيجية | Decision Council | Controlled | Draft wording only |
| `DASH-ALG-05` | Risk Register and Matrix Builder | بناء سجل ومصفوفة المخاطر | Decision Council | Yes | Explain only |
| `DASH-ALG-06` | Scenario Comparison Presenter | عارض مقارنة السيناريوهات | Finance Engine | Yes | None |
| `DASH-ALG-07` | Investor Readiness Gate | بوابة الجاهزية الاستثمارية | Decision Council + Finance Engine outputs | Yes | Draft narrative only |
| `DASH-ALG-08` | Dashboard Section State Resolver | حل حالة قسم اللوحة | Owner Module + Audit / Observability | Yes | None |
| `DASH-ALG-09` | Bilingual Display Resolution | حل العرض ثنائي اللغة | Reports + contract-bound frontend | Yes | None |
| `DASH-ALG-10` | Dashboard and Report Parity | تطابق اللوحة والتقرير | Reports + Audit / Observability | Yes | None |
| `DASH-ALG-11` | External Context Signal Guard | حارس إشارة السياق الخارجي | Market Intelligence + Audit / Observability | Controlled | Inference only |
| `DASH-ALG-12` | Legacy Screenshot Migration Guard | حارس ترحيل مرجع الشاشة القديمة | Audit / Observability | Yes | None |
| `AI-ALG-01` | Model Routing | توجيه النماذج | AI Advisory | Yes | Uses AI providers |
| `AI-ALG-02` | RAG Retrieval Ranking | ترتيب RAG | AI Advisory | Yes | Retrieval only |
| `AI-ALG-03` | Advisory Output Guard | حارس مخرجات الاستشارة | AI Advisory | Yes | Guarded |
| `SEC-ALG-01` | Zero Trust Policy Evaluation | تقييم الأمن الصفري | Audit / Observability | Yes | None |
| `SEC-ALG-02` | Quarantine Decision | قرار العزل | Audit / Observability | Yes | None |
| `OPS-ALG-01` | Health Scoring | حساب صحة النظام | Audit / Observability | Yes | Summarize only |
| `ID-ALG-01` | Human Verification Risk Gate | بوابة مخاطر التحقق من الإنسان | User / Auth | Yes | None |
| `ID-ALG-02` | Authenticator App MFA Evaluation | تقييم MFA عبر Authenticator | User / Auth | Yes | None |
| `NOTIF-ALG-01` | Notification Preference Resolution | حل تفضيلات التنبيهات | Audit / Observability | Yes | None |
| `NOTIF-ALG-02` | External Channel Delivery Guard | حارس تسليم القنوات الخارجية | Audit / Observability | Yes | None |
| `ADM-ALG-02` | Admin Operations Health Evaluation | تقييم صحة عمليات الإدارة | Admin + Audit / Observability | Yes | Summarize only |
| `ADM-ALG-03` | Incident Escalation | تصعيد الحوادث | Admin + Audit / Observability | Yes | None |
| `SUB-ALG-01` | Trial Cooldown | تهدئة التجربة المجانية | Subscription / Usage | Yes | None |
| `SUB-ALG-02` | Usage Limit Evaluation | تقييم حدود الاستخدام | Subscription / Usage | Yes | None |
| `ADM-ALG-01` | Feature Flag Evaluation | تقييم أعلام الخصائص | Admin | Yes | None |
| `AN-ALG-01` | Product Analytics Ingestion | استيعاب تحليلات المنتج | Audit / Observability | Yes | Summarize only |
| `AN-ALG-02` | Funnel Metric Calculation | حساب مقاييس القمع | Audit / Observability | Yes | Summarize only |
| `AN-ALG-03` | Analytics Privacy Sanitization | تنقيح خصوصية التحليلات | Audit / Observability | Yes | None |
| `AN-ALG-04` | Analytics Dashboard Dataset Builder | باني Dataset لوحات التحليلات | Audit / Observability + Admin | Yes | Summarize only |
| `CHART-ALG-01` | Chart Dataset Authorization | تفويض Dataset الشارت | Audit / Observability | Yes | Explain only |
| `CHART-ALG-02` | Market Chart Dataset Builder | باني بيانات شارتات السوق | Market Intelligence | Yes | Summarize only |
| `CHART-ALG-03` | Finance Chart Dataset Builder | باني بيانات شارتات التمويل | Finance Engine | Yes | None |
| `CHART-ALG-04` | Decision Chart Dataset Builder | باني بيانات شارتات القرار | Decision Council | Yes | Explain only |
| `CHART-ALG-05` | Admin Observability Chart Dataset Builder | باني بيانات شارتات الإدارة والمراقبة | Admin + Audit / Observability | Yes | Summarize only |
| `CHART-ALG-06` | Chart State Resolver | حل حالة الشارت | Owner module + UI contract | Yes | None |
| `CHART-ALG-07` | Landing Preview Dataset Sanitizer | منقح بيانات معاينات صفحة الهبوط | Reports + Audit / Observability | Yes | None |

## Enforcement

## الإنفاذ

Algorithms cannot move owner without ACP.

لا يجوز نقل ملكية خوارزمية إلى موديول آخر بدون ACP.
