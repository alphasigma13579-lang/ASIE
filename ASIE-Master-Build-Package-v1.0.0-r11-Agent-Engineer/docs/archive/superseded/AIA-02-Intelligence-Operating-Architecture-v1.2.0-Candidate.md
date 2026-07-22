# AIA-02 — Intelligence Operating Architecture
## المعمارية التشغيلية للذكاء في منصة AlphaSigma Intelligence Engine — ASIE
### الإصدار `v1.2.0` — Candidate for Final Review

---

## 0. بيانات الوثيقة

| البند | القيمة |
|---|---|
| رمز الوثيقة | `AIA-02` |
| الاسم الإنجليزي | Intelligence Operating Architecture |
| الاسم العربي | المعمارية التشغيلية للذكاء |
| الإصدار | `v1.2.0` |
| الحالة المعمارية | `CANDIDATE FOR FINAL REVIEW` |
| حالة التجميد | `NOT YET FROZEN` |
| حالة التفعيل الإنتاجي | `PENDING STAGED ACRs` |
| الوثيقة الدستورية الحاكمة | `AIA-01 — Intelligence Constitution v1.0.0` |
| المعمارية التنفيذية الحاكمة | `AAS Runtime Freeze v1.0` |
| خط الأساس التنفيذي | ASIE r11 Local Core — مراجعة 21 يوليو 2026 |
| آلية تعديل AIA-01 | `ICCR — Intelligence Constitutional Change Request` |
| آلية تعديل وثائق AIA التشغيلية | `IACR — Intelligence Architecture Change Request` |
| أي تغيير يؤثر على AAS | `ACR — Architectural Change Request` |
| سلطة الختم الوحيدة | `Snapshot Assembly` |
| حالة AI الحالية | `DISABLED / DENY_ALL / NO PROVIDERS / NO NETWORK` |
| سياسة الاستحواذ الخارجي الحالية | `STRICT_OPEN_DATA_ONLY_V1` |
| سياسة أدلة المستخدم | مستقلة عن سياسة الاستحواذ الخارجي |
| مبدأ التنفيذ | `AAS governs execution. AIA governs intelligence.` |

---

# 1. الغرض

تحدد هذه الوثيقة المعمارية التشغيلية الكاملة لقدرات المعرفة والذكاء في ASIE، وتربط بصورة صريحة بين:

1. **ما هو منفذ فعليًا في المستودع.**
2. **ما هو موجود جزئيًا ويحتاج إلى توسعة.**
3. **ما هو معرف معماريًا لكنه غير منفذ.**
4. **ما يحتاج IACR.**
5. **ما يحتاج ACR مرحليًا قبل دخوله إلى الإنتاج.**
6. **ما يجب أن يبقى بعد Snapshot بوصفه Projection فقط.**
7. **ما هو معطل حاليًا بفعل السياسة الأمنية.**
8. **ما لا يجوز تنفيذه أصلًا بسبب سيادة AAS أو ملكية المحركات.**

لا تعتبر هذه الوثيقة أي قدرة `IMPLEMENTED` لمجرد ذكر اسمها أو وجود دالة غير موصولة بها. الإثبات التشغيلي يحتاج واحدًا أو أكثر من:

- Module فعلي.
- Contract مسجل.
- Socket مسجل.
- API endpoint.
- مخطط تخزين.
- UI surface.
- Automated test.
- Runtime status.
- Acceptance evidence.
- Snapshot integration evidence.

---

# 2. اللغة المعيارية

تستخدم هذه الوثيقة المصطلحات التالية:

| المصطلح | الدلالة |
|---|---|
| يجب | إلزام معماري |
| يمنع | حظر معماري |
| يجوز | خيار مسموح |
| يحتاج ACR | لا ينفذ إنتاجيًا قبل طلب تغيير معماري |
| معرف | موجود في المعمارية وليس بالضرورة في الكود |
| منفذ | مثبت بدليل داخل المستودع |
| جزئي | يوجد جزء من القدرة دون اكتمال المسار |
| مختوم | غير قابل للتعديل منطقيًا ويحمل Hash |
| Projection | قراءة مشتقة لا تعيد الحساب ولا تغير الحقيقة |
| Overlay | طبقة منفصلة لا تعدل المخرج الأصلي |
| Sovereign | مملوك حصريًا لمحرك محدد |

---

# 3. خط الأساس التنفيذي الفعلي — As-Built Baseline

## 3.1 النمط الحالي

ASIE حاليًا:

```text
React 19 + TypeScript + Vite
→ Python Local API باستخدام ThreadingHTTPServer
→ Modular Monolith
→ SQLite
→ AAS Runtime داخلي تعاقدي
→ ستة محركات إلزامية
→ Snapshot Assembly
→ Immutable Snapshot
→ Projections
```

## 3.2 ترتيب التشغيل الفعلي المجمد

الترتيب الموجود فعليًا في المستودع هو:

```text
ProjectRunWorkflow
→ Finance
→ Sector Intelligence
→ Evidence Ledger
→ Decision Council v1
→ Risk Engine
→ Execution Engine
→ Snapshot Assembly
→ Immutable Snapshot
```

هذا الترتيب هو خط الأساس التنفيذي الملزم.

**يمنع** إعادة ترتيبه أو إدخال مكوّن جديد بين مراحله دون ACR.

## 3.3 المخرجات الستة الإلزامية

| Output key | المالك الحالي | عقد المخرج |
|---|---|---|
| `finance_result` | Finance Engine | `finance.result.v1` |
| `sector_intelligence` | Sector Intelligence | `sector.intelligence.v1` |
| `evidence_ledger` | Evidence Ledger | `evidence.ledger.v1` |
| `decision_result` | Decision Council | `decision.council.v1` |
| `risk_result` | Risk Engine | `risk.register.v1` |
| `execution_result` | Execution Engine | `execution.plan.v1` |

## 3.4 مكونات موجودة يجب إعادة استخدامها

- AAS Kernel.
- Registry.
- Heart Controller.
- M1 / M2 / M3.
- Bus Controller.
- System Bus.
- Socket Contract Layer.
- Module Runtime.
- ProjectRunWorkflow.
- Snapshot Assembly.
- Runtime Freeze verification.
- Source Registry.
- Datasets.
- CSV / JSON / XLSX intake.
- Transformations وLineage.
- Evidence Links.
- Dataset Review.
- Snapshot Reviews.
- Decision Pack Review Overlay.
- Report Projection.
- Decision Pack Projection.
- Funder Report Projection.
- Security Audit.
- AI Integration Shell.
- Runtime Status.
- Repository وSQLite.

## 3.5 قدرات موجودة جزئيًا

| القدرة | الحالة |
|---|---|
| عزل المؤسسات | موجود جزئيًا ويحتاج اختبارات سلبية شاملة |
| GPS | موجود في الواجهة ويحتاج تثبيت سياسة الموافقة والأخطاء |
| External file intake | موجود Backend جزئيًا، غير مكتمل UX |
| DOCX/PDF/PPTX exports | وظائف خادم موجودة، غير موصولة بالكامل للواجهة |
| Subscription control plane | محلي وتجريبي، بلا بوابة دفع |
| Live Cockpit | تجريبي، وليس مصدر حقيقة |
| Password recovery | محلي، بلا قناة إرسال خارجية |
| AI integration | Shell وحراس موجودة، التنفيذ معطل |
| Source governance | موجود، بلا Connectors حية |
| Backup/restore | محلي، بلا تشفير أو جدولة |

## 3.6 قدرات غير منفذة

- AIA Production Pre-Run.
- Intelligence Context Manager.
- Draft Intelligence Context.
- Sealed Intelligence Context.
- Context Approval Receipt.
- Consulting Intelligence Module.
- Strategic Intelligence Module.
- Global Economic Intelligence Module.
- National Economic Intelligence Module.
- Market Intelligence Module مستقل.
- Reference Cost, Price & Assumption Intelligence.
- Indicator Relationships Module.
- Pre-Decision Intelligence Pack.
- Decision Council v2.
- Deterministic Final Intelligence Projection.
- AI Narrative Overlay الفعلي.
- Trusted Prompt Assembly.
- External data connectors.
- AI providers.
- Cloud deployment.
- Production observability.
- Payment provider.
- Messaging providers.

---

# 4. الثوابت المعمارية غير القابلة للكسر

1. `Snapshot` هو مصدر الحقيقة التحليلية الوحيد.
2. الواجهة لا تعيد الحساب.
3. جميع الرسائل الإنتاجية تمر عبر AAS.
4. لا Direct Module Calls.
5. لا Runtime ثانٍ.
6. لا Bus ثانٍ.
7. لا Registry ثانٍ.
8. لا Snapshot Store ثانٍ.
9. لا AI Gateway ثانٍ.
10. AI Integration Shell الحالي هو بوابة AI الوحيدة.
11. `decision.council.v1` لا يعدل.
12. `decision.council.v2` — إن أُنشئ — عقد جديد مستقل.
13. Finance Engine وحده يملك NPV وIRR وDSCR وBreak-even وMonte Carlo المالي.
14. Evidence Ledger يملك الأدلة وLineage.
15. Decision Council يملك Verdict.
16. Risk Engine يملك Risk Register.
17. Execution Engine يملك Execution Plan.
18. Snapshot Assembly هو سلطة الختم الوحيدة.
19. Post-Snapshot Projections لا تعيد الحساب.
20. AI لا يملك رقمًا رسميًا أو Verdict أو تفسيرًا قانونيًا ملزمًا.
21. AI Output ليس Evidence Primary.
22. لا Source أو Provider يتفعل دون سياسة واعتماد.
23. لا ادعاء بالسببية من مجرد الارتباط.
24. Contradiction Register لا يُخفى.
25. قبول المستخدم لا يساوي صحة الافتراض.
26. `Listed Price` لا يساوي `Landed Cost` أو `Installed Cost`.
27. Low/Base/High يجب أن تحمل `Impact Direction`.
28. كل تغيير إنتاجي جديد يحتاج AAS governance.
29. كل تأثير على Runtime Freeze يحتاج ACR.
30. كل متطلب عالي القيمة يجب أن يمتلك مالكًا وعقدًا واختبارًا أو حالة فجوة صريحة.

---

# 5. نموذج حالات المكونات

كل مكوّن أو متطلب يحمل واحدة أو أكثر من الحالات التالية:

```text
AS_BUILT
PARTIALLY_IMPLEMENTED
DEFINED_NOT_IMPLEMENTED
OFFLINE_PROTOTYPE_ONLY
PENDING_IACR
PENDING_ACR
DISABLED_BY_POLICY
POST_SNAPSHOT_ONLY
PROHIBITED
```

لا تستخدم حالة `IMPLEMENTED` دون دليل.

---

# 6. طبقات تشغيل AIA

## 6.1 Documentation Mode

- مواصفات.
- عقود.
- Schemas.
- رسومات.
- اختبارات قبول.
- لا تنفيذ إنتاجي.
- لا يحتاج ACR ما دام توثيقًا فقط.

## 6.2 Offline Engineering Prototype

```text
OFFLINE_PROTOTYPE
```

- بيئة تطوير معزولة.
- بيانات اختبار أو ملفات مرفوعة تجريبيًا.
- لا يكتب إلى قاعدة الإنتاج.
- لا يظهر للمستخدم كقدرة إنتاجية.
- لا يدخل Snapshot.
- لا يستخدم External Sources غير معتمدة.
- لا يحتاج ACR ما دام خارج الإنتاج.

## 6.3 Governed Production Pre-Run

```text
PRODUCTION_PRE_RUN
```

- يعمل داخل المنصة.
- يستخدم API وBus وSocket وModule Runtime.
- يكتب إلى Repository رسمي.
- يسجل Audit.
- ينتج Intelligence Context رسميًا.
- **يحتاج ACR** إذا لم يكن ضمن Runtime Freeze الحالي.

## 6.4 Runtime Intelligence

- يقرأ مخرجات مختومة فقط.
- لا يجمع بيانات جديدة.
- لا يتفاعل مع المستخدم.
- لا يعيد بناء Context.
- ينشئ Pre-Decision Pack.
- يمرر Pack إلى `decision.council.v2`.
- غير مفعل حاليًا.
- يحتاج ACRs مرحلية.

## 6.5 Post-Snapshot Intelligence

```text
Immutable Snapshot
├── Report Projection
├── Decision Pack Projection
├── Deterministic Final Intelligence Projection
└── AI Narrative Overlay
```

- لا تغير Snapshot.
- لا تعيد الحساب.
- لا تغير Verdict.
- فشلها لا يبطل Snapshot.

---

# 7. الخريطة المستهدفة دون Runtime ثانٍ

```text
React UI
→ Python API
→ AAS Kernel
→ Heart Controller
→ Bus Controller
→ System Bus
→ Socket Contract Layer
→ Module Runtime
→ AIA Modules / Existing Domain Modules
→ Snapshot Assembly
→ Immutable Snapshot
→ Deterministic Projections
→ Optional AI Narrative Overlay
```

AIA لا تملك Orchestrator مستقلًا. تنسيقها الإنتاجي يجب أن يتم داخل AAS بعد ACR.

---

# 8. سجل المتطلبات المعمارية — Architecture Requirement Register

## 8.1 الذكاء وتجربة المستخدم

| المعرّف | المتطلب | المالك المستهدف | الحالة الحالية |
|---|---|---|---|
| `AIA-REQ-AI-001` | شرح الحقول والنتائج | AI Experience فوق AI Shell | معرف، معطل |
| `AIA-REQ-AI-002` | اقتراح الأفكار والتحسينات | AI Experience | معرف، معطل |
| `AIA-REQ-AI-003` | اكتشاف فجوات البيانات | AI Experience + Validation | معرف، معطل |
| `AIA-REQ-AI-004` | Trusted Prompt Assembly | AI Integration Shell | غير منفذ |
| `AIA-REQ-AI-005` | منع AI من الأرقام والقرار | OutputValidation | منفذ حوكميًا |
| `AIA-REQ-AI-006` | Human Review حسب المخاطر | HumanReviewGate | منفذ جزئيًا |
| `AIA-REQ-AI-007` | عدم إنشاء socket.ai.experience | AIA-02 invariant | ملزم |

## 8.2 الذكاء الاستشاري

| المعرّف | المتطلب | الحالة |
|---|---|---|
| `AIA-REQ-CON-001` | Hypothesis-led Analysis | غير منفذ |
| `AIA-REQ-CON-002` | MECE | غير منفذ |
| `AIA-REQ-CON-003` | Issue Trees | غير منفذ |
| `AIA-REQ-CON-004` | Driver Trees | غير منفذ |
| `AIA-REQ-CON-005` | Root Cause Analysis | غير منفذ |
| `AIA-REQ-CON-006` | Scenario Thinking | غير منفذ |
| `AIA-REQ-CON-007` | Triangulation | غير منفذ |
| `AIA-REQ-CON-008` | Pyramid Principle | غير منفذ |
| `AIA-REQ-CON-009` | Assumption Stress Testing | غير منفذ |

## 8.3 الذكاء الاستراتيجي والاقتصادي

| المعرّف | المتطلب | الحالة |
|---|---|---|
| `AIA-REQ-STR-001` | Strategic Alignment Score | غير منفذ |
| `AIA-REQ-STR-002` | رؤية 2030 وبرامجها | غير منفذ |
| `AIA-REQ-STR-003` | الاستراتيجيات القطاعية والإقليمية | غير منفذ |
| `AIA-REQ-GLO-001` | Global Economic Context | غير منفذ |
| `AIA-REQ-GLO-002` | Opportunity Hypotheses | غير منفذ |
| `AIA-REQ-NAT-001` | National Economic Context | غير منفذ |
| `AIA-REQ-NAT-002` | سياق التمويل والطلب الوطني | غير منفذ |
| `AIA-REQ-NAT-003` | Freshness وGeographic Scope | غير منفذ |

## 8.4 السوق والتكاليف والافتراضات

| المعرّف | المتطلب | الحالة |
|---|---|---|
| `AIA-REQ-MKT-001` | Market Intelligence Module مستقل | غير منفذ |
| `AIA-REQ-MKT-002` | Market Context مملوك بوضوح | غير منفذ |
| `AIA-REQ-COST-001` | Market-Derived Assumptions | غير منفذ |
| `AIA-REQ-COST-002` | Asset Requirement Profile | غير منفذ |
| `AIA-REQ-COST-003` | HOME/LIGHT_COMMERCIAL/COMMERCIAL/PROFESSIONAL/INDUSTRIAL | غير منفذ |
| `AIA-REQ-COST-004` | Listed/Landed/Installed/Operational Readiness | غير منفذ |
| `AIA-REQ-COST-005` | Median/Trimmed Mean/IQR/Weighted Median | غير منفذ |
| `AIA-REQ-COST-006` | Low/Base/High + Impact Direction | غير منفذ |
| `AIA-REQ-COST-007` | L0–L3 Maturity | غير منفذ |
| `AIA-REQ-COST-008` | Actual/Partial/No figures user states | غير منفذ |
| `AIA-REQ-COST-009` | User Acceptance منفصل عن Quality | غير منفذ |
| `AIA-REQ-COST-010` | Finance Eligibility منفصلة | غير منفذ |

## 8.5 المؤشرات والتعارضات

| المعرّف | المتطلب | الحالة |
|---|---|---|
| `AIA-REQ-CMP-001` | Comparison Matrix | غير منفذ |
| `AIA-REQ-CMP-002` | Intersection Insights | غير منفذ |
| `AIA-REQ-CMP-003` | Contradiction Register | غير منفذ |
| `AIA-REQ-CMP-004` | Comparability Status | غير منفذ |
| `AIA-REQ-CMP-005` | No unsupported causality | ملزم |
| `AIA-REQ-CMP-006` | Double-count guard | غير منفذ |

## 8.6 UX والتقارير

| المعرّف | المتطلب | الحالة |
|---|---|---|
| `AIA-REQ-UX-001` | Arabic RTL first | موجود جزئيًا |
| `AIA-REQ-UX-002` | Bilingual switch | يحتاج تثبيت شامل |
| `AIA-REQ-UX-003` | Click-first guided journey | موجود جزئيًا |
| `AIA-REQ-UX-004` | Location/GPS first | موجود جزئيًا |
| `AIA-REQ-UX-005` | Map pin + no manual city by default | غير مكتمل |
| `AIA-REQ-UX-006` | External file field CSV/XLSX/PDF | Backend جزئي، UI غير مكتمل |
| `AIA-REQ-UX-007` | Monte Carlo KPI | المحرك موجود، العرض يحتاج تحقق |
| `AIA-REQ-UX-008` | Five persona KPIs | المنطق موجود جزئيًا، العرض يحتاج تثبيت |
| `AIA-REQ-RPT-001` | UI/PDF/PPTX/DOCX/XLSX من Snapshot | جزئي |
| `AIA-REQ-RPT-002` | No recalculation in UI | ملزم |
| `AIA-REQ-RPT-003` | Critical warnings not hidden by subscription | ملزم |

---

# 9. DAG التشغيلي لوحدات Pre-Run

## 9.1 الرسم المعتمد

```text
Validated Project Context
        │
        ├── Consulting Intelligence
        ├── Strategic Intelligence
        ├── Global Economic Intelligence
        ├── National Economic Intelligence
        ├── Market Intelligence
        └── Reference Cost & Assumption Intelligence
                    │
                    ▼
          Validated Component Outputs
                    │
                    ▼
       Indicator Relationships Intelligence
                    │
                    ▼
         Draft Intelligence Context
                    │
                    ▼
                  Seal
                    │
                    ▼
         Sealed Intelligence Context
                    │
                    ▼
              Review Overlay
                    │
                    ▼
            Approval Receipt
```

## 9.2 الاعتماديات

| المكوّن | الاعتماديات الإلزامية | الاعتماديات الاختيارية |
|---|---|---|
| Consulting Intelligence | Project Context | Evidence refs |
| Strategic Intelligence | Project Context + Strategic sources | Consulting Frame |
| Global Economic | Project Context + Global sources | Consulting Frame |
| National Economic | Project Context + National sources | Global context |
| Market Intelligence | Project Context + Sector context | National context |
| Reference Cost | Requirement profiles + approved sources | Market context |
| Indicator Relationships | مخرجان صالحان على الأقل | جميع المخرجات |
| Context Assembly | Component manifests | Optional component gaps |
| Review Overlay | Sealed Context | Domain expert review |
| Approval Receipt | Valid Overlay + Context hash | Conditions |

## 9.3 التوازي

يمكن تشغيل الوحدات التالية بالتوازي بعد تحقق Project Context:

- Consulting.
- Strategic.
- Global Economic.
- National Economic.
- Market Intelligence.
- Reference Cost — بشرط اكتمال Requirement Profile.

Indicator Relationships لا يبدأ قبل توفر مخرجات صالحة قابلة للمقارنة.

## 9.4 سياسة الفشل

- فشل مكوّن إلزامي: `FAIL_CLOSED`.
- فشل مكوّن اختياري: يستمر مع `DATA_GAP`.
- انتهاء المهلة: يسجل `TIMEOUT` ولا يعاد المحاولة بلا حدود.
- Retry: حد أقصى افتراضي 2 للمصادر المحلية و1 للمصادر الخارجية بعد التفعيل.
- لا Partial Pack يدخل Decision Council دون وسم وحكم أهليته.
- لا تحويل صامت من v2 إلى v1.

---

# 10. Draft وSealed Intelligence Context

## 10.1 Draft Intelligence Context

خصائصه:

- قابل للتعديل.
- لا يملك Hash نهائيًا.
- لا يدخل Run.
- لا يستخدمه Decision Council.
- يمكن حذف أو تعديل مكوناته.
- يحمل `draft_version`.

## 10.2 Sealed Intelligence Context

خصائصه:

- غير قابل للتعديل.
- يمتلك `context_id`.
- يمتلك `context_hash`.
- يمتلك `context_version`.
- يرتبط بمخرجات مختومة.
- أي تعديل ينتج إصدارًا جديدًا.
- لا يحتوي مرجع Review Overlay.

## 10.3 الحقول المعتمدة

```text
intelligence_context_id
project_id
context_version
context_hash
previous_context_id
previous_context_hash
revision_reason
created_at
created_by
effective_from
effective_to
retrieved_at
valid_until
freshness_rule_id
historical_use_allowed
geographic_scope
sector_scope
project_input_hash
maturity_level
external_acquisition_policy_version
user_evidence_intake_policy_version
review_policy_version
aas_compatibility_version
contract_set_version
component_manifest
confidence_profile
```

لا يوضع `superseded_by` داخل السياق القديم.

---

# 11. Review Overlay وApproval Receipt

## 11.1 Review Overlay

يخزن منفصلًا ويشير إلى:

```text
review_overlay_id
review_overlay_hash
intelligence_context_id
intelligence_context_hash
reviewer_id
reviewer_role
review_scope
decision
conditions
reason
created_at
supersedes_overlay_id
```

## 11.2 Approval Receipt

هو الإثبات القابل للاستهلاك في Run، ويحتوي:

```text
approval_receipt_id
approval_receipt_hash
intelligence_context_id
intelligence_context_hash
review_overlay_id
review_overlay_hash
approval_scope
approved_for_contract_version
approved_for_project_id
valid_until
conditions
created_at
```

`APPROVED_FOR_RUN` حالة مشتقة من Receipt، وليست تعديلًا في Context.

---

# 12. Context Dependency & Invalidation Matrix

| تغيير المشروع | المخرجات التي تصبح STALE |
|---|---|
| الدولة | جميع السياقات الوطنية والسوقية والقانونية والتكاليف |
| المدينة/الموقع | الإيجار، السوق المحلي، اللوجستيات، السياق الإقليمي، المنافسة |
| الإحداثيات | الإيجار، نطاق الخدمة، الوصول، اللوجستيات |
| القطاع | Strategic، Sector، Market، Global/National Context، Cost Profiles |
| النشاط الفرعي | المنافسة، المعدات، الموردون، التسعير، الأدلة القطاعية |
| فئة المشروع | السعة، العمالة، المساحة، المعدات، الافتراضات |
| الطاقة الإنتاجية | المعدات، العمالة، المواد، المساحة، التمويل |
| مستوى الجودة | المعدات، الموردون، التجهيز، سعر البيع |
| نموذج الإيراد | التسعير، الطلب، الافتراضات المالية، القنوات |
| العميل المستهدف | الطلب، التسعير، القنوات، المنافسة |
| رأس المال | السيناريوهات والتمويل والتوسع |
| تاريخ التحليل | كل مخرج محدود الصلاحية |
| مصدر رئيسي | كل مخرج يعتمد على المصدر |
| عرض مورد | الافتراض المرتبط وتكاليفه |
| سعر بيع مستهدف | Market assumptions وFinance scenarios |
| الملف الخارجي | Evidence Links والمخرجات المستهلكة له |

## 12.1 قواعد الإبطال

- الإبطال لا يحذف النسخة القديمة.
- يغير Registry status إلى `STALE`.
- لا يعدل Hash القديم.
- أي Run v2 يرفض Required Context المتقادم.
- الاستخدام التاريخي ممكن إذا كان `historical_use_allowed=true`.

---

# 13. سياسات المصادر

## 13.1 External Acquisition Policy

```text
STRICT_OPEN_DATA_ONLY_V1
```

تطبق على البيانات التي تجمعها المنصة خارجيًا.

المسموح حاليًا:

- Open Data.
- Official open APIs بعد التفعيل.
- Public lawful sources بعد المراجعة.

غير المسموح:

- Unlicensed scraping.
- Paid datasets دون ترخيص.
- Marketplace feeds غير معتمدة.
- Automated collection بلا Terms review.

## 13.2 User Evidence Intake Policy

تطبق على:

- PDF.
- Excel.
- CSV.
- XLSX.
- عروض الموردين.
- العقود.
- الفواتير.
- الملفات الخاصة بالمستخدم.
- الإدخال اليدوي الموثق.

بيانات المستخدم ليست Open Data، لكنها Evidence خاصة بالمشروع.

## 13.3 Source Activation

```text
Candidate
→ Terms Review
→ License Review
→ Legal Review
→ Security Review
→ Technical Review
→ Data Quality Review
→ Approval
→ Source Registry
→ Controlled Activation
```

AI لا يفعل مصدرًا.

---

# 14. ملكية Market Context

## 14.1 الحالة الحالية

الموجود فعليًا:

```text
Sector Intelligence
```

وهو يملك `sector_intelligence` فقط.

## 14.2 الحالة المستهدفة

```text
Market Context
Owned by Market Intelligence Module
```

حتى تنفيذ الوحدة:

```text
market_context_status = NOT_AVAILABLE
```

لا يجوز إعادة تسمية Sector Intelligence إلى Market Context، ولا يجوز لـReference Cost أو National Economic أو Synthesis امتلاك Market Context.

---

# 15. Reference Cost, Price & Assumption Intelligence

## 15.1 حالات المستخدم

```text
ACTUAL_DATA_AVAILABLE
PARTIAL_DATA_AVAILABLE
NO_ACTUAL_DATA
```

## 15.2 المسار

```text
Project Requirement
→ Asset/Cost Requirement Profile
→ Approved Source Set
→ Comparable Basket
→ Classification
→ Specification Matching
→ Deduplication
→ Outlier Treatment
→ Currency/Unit Normalization
→ Landed/Installed Cost Adjustment
→ Low/Base/High
→ Confidence Profile
→ Evidence Validation
→ Assumption Quality
→ User Acceptance
→ Finance Eligibility
```

## 15.3 تصنيف الاستخدام

```text
HOME
LIGHT_COMMERCIAL
COMMERCIAL
PROFESSIONAL
INDUSTRIAL
```

يمنع خلطها في Basket واحدة.

## 15.4 أنواع السعر

```text
LISTED_PRICE
LANDED_COST
INSTALLED_COST
OPERATIONAL_READINESS_COST
```

## 15.5 الإحصاءات المسموحة

- Median.
- Trimmed Mean.
- Weighted Median.
- IQR.
- Source Quality Weight.
- Recency Weight.
- Specification Similarity Weight.
- Geographic Relevance Weight.

يمنع الاعتماد على المتوسط البسيط لسلة غير متجانسة.

## 15.6 حالات الجودة

```text
UNVERIFIED
SCREENING_ONLY
MARKET_ESTIMATED
SUPPLIER_VALIDATED
CONTRACT_BACKED
REJECTED
```

## 15.7 مستويات النضج

| المستوى | الدلالة |
|---|---|
| L0 | Idea Screening |
| L1 | Market Estimated |
| L2 | Supplier Validated |
| L3 | Contract Backed |

قبول المستخدم لا يرفع المستوى.

## 15.8 الحقول الأساسية

```text
assumption_id
project_id
item_class
requirement_profile_ref
value_low
value_base
value_high
currency
unit
price_basis
impact_direction
scenario_mapping
included_costs
excluded_costs
source_refs
source_count
source_diversity
outlier_method
confidence_profile
evidence_validation_status
assumption_quality_status
user_acceptance_status
finance_eligibility_status
maturity_level
valid_until
```

---

# 16. ربط Low/Base/High بالسيناريوهات

لا تعني High دائمًا متفائلًا أو متحفظًا.

## تكلفة معدات

```text
impact_direction = COST_INCREASE_NEGATIVE
low  → optimistic
base → base
high → conservative
```

## سعر بيع

```text
impact_direction = REVENUE_INCREASE_POSITIVE
low  → conservative
base → base
high → optimistic
```

Finance Engine وحده يحول هذه القيم إلى:

- Scenarios.
- Sensitivity.
- Monte Carlo.
- NPV.
- IRR.
- DSCR.
- Break-even.

---

# 17. Confidence Profile

يعتمد ملف ثقة متعدد الأبعاد:

```text
source_quality
source_coverage
specification_similarity
geographic_relevance
sector_relevance
freshness
comparability
method_confidence
overall_confidence
critical_confidence_failures
```

قواعده:

- لا يحسب `overall_confidence` بمتوسط بسيط فقط.
- أي `critical_confidence_failure` قد يمنع Finance Eligibility.
- كل بُعد قابل للتفسير.
- يجب عرض أسباب انخفاض الثقة للمستخدم.
- لا ترفع User Acceptance الثقة تلقائيًا.

---

# 18. Indicator Comparison & Intersection

## 18.1 Comparison Matrix

```text
indicator_a_ref
indicator_b_ref
comparison_type
definition_compatibility
unit_compatibility
time_compatibility
geographic_compatibility
sector_compatibility
baseline_ref
difference
direction
confidence_profile
limitations
comparability_status
```

الحالة عند الفشل:

```text
NOT_DIRECTLY_COMPARABLE
```

## 18.2 Intersection Insights

- تفسير مركب.
- لا يغير القيم الأصلية.
- لا يصدر Verdict.
- لا يدعي السببية.

## 18.3 Contradiction Register

```text
contradiction_id
indicator_a_ref
indicator_b_ref
contradiction_type
severity
possible_explanation
time_mismatch
geographic_mismatch
methodology_mismatch
source_conflict
resolution_data_needed
confidence_impact
review_status
```

---

# 19. منع ازدواج الإشارات

كل Signal يحمل:

```text
signal_id
signal_origin
signal_owner
source_output_ref
duplicate_of
consumed_by
double_count_guard
```

Pre-Decision Pack لا يعيد:

- Finance Result.
- القيم التي حسبها Finance.
- استنتاجًا ماليًا موازيًا.
- العامل نفسه بصيغ متعددة.

يسمح له بـ:

- Strategic relevance.
- Economic context.
- Evidence quality.
- Contradictions.
- Data gaps.
- Assumption maturity.
- Non-financial context.

---

# 20. Pre-Decision Intelligence Pack

## 20.1 الحالة

```text
DEFINED_NOT_IMPLEMENTED
PENDING_ACR
```

## 20.2 المحتوى

- Consulting Frame summary.
- Strategic Alignment summary.
- Global Economic Context.
- National Economic Context.
- Market Context — إن كان متاحًا.
- Assumption maturity.
- Evidence gaps.
- Comparison Matrix.
- Contradiction Register.
- Supporting/Caution/Conflict signals.
- Confidence Profile.

## 20.3 المحظورات

- Verdict.
- Risk Register.
- Execution Plan.
- Final Projection.
- Raw AI Output.
- Raw Prompt.
- Raw Sources.
- Finance Result duplicate.

---

# 21. Decision Council v1 وv2

## 21.1 v1

يبقى دون تغيير:

```text
decision.council.v1
```

## 21.2 v2

يُنشأ بعقد جديد بعد ACR:

```text
decision.council.v2
```

المدخلات:

```text
finance
blockers
readiness_gates
sector_intelligence
predecision_intelligence_ref
```

المحظورات:

```text
risk_register
execution_plan
final_projection
raw_ai_output
raw_sources
prompt
```

---

# 22. Dispatch Policy

يضاف مستقبلًا إلى ProjectRunEnvelope:

```text
decision_contract_version
aia_runtime_mode
intelligence_context_required
predecision_pack_required
projection_version
```

## Run v1

```text
decision_contract_version = decision.council.v1
aia_runtime_mode = DISABLED
intelligence_context_required = false
predecision_pack_required = false
```

## Run v2

```text
decision_contract_version = decision.council.v2
aia_runtime_mode = GOVERNED
intelligence_context_required = true
predecision_pack_required = true
```

يحظر التحويل الصامت بين النسختين.

---

# 23. Decision Input Manifest

عند v2 يجب أن تحفظ Snapshot:

```text
decision_input_manifest:
  decision_contract_version
  predecision_pack_id
  predecision_pack_hash
  intelligence_context_id
  intelligence_context_hash
  approval_receipt_id
  approval_receipt_hash
  external_acquisition_policy_version
  user_evidence_intake_policy_version
  review_policy_version
  contract_set_version
```

ويحمل `decision.council.result.v2` المراجع نفسها.

---

# 24. Failure Semantics

## v1

- فشل AIA لا يؤثر؛ لأنها ليست جزءًا من Run.

## v2

- Missing required Context → `FAIL_CLOSED`.
- Missing Pre-Decision Pack → `FAIL_CLOSED`.
- Stale required component → Reject.
- Missing Approval Receipt → Reject.
- Optional component failure → Continue only with `DATA_GAP`.
- لا fallback صامت إلى v1.
- Final Projection failure → Snapshot remains valid.
- AI Narrative Overlay failure → Snapshot remains valid.

---

# 25. Deterministic Final Intelligence Projection

## 25.1 الموضع

```text
Execution
→ Snapshot Assembly
→ Immutable Snapshot
→ Deterministic Final Intelligence Projection
```

## 25.2 الخصائص

- Read-only.
- Snapshot-derived.
- Reproducible.
- No new inference.
- No new contradiction detection.
- No new scoring.
- No new classification.
- No mutation.
- Failure does not invalidate Snapshot.

---

# 26. AI Narrative Overlay

- Non-authoritative.
- Model-attributed.
- Output-hashed.
- Review-controlled.
- Not part of Snapshot.
- Regenerable.
- لا ينتج حقيقة رسمية.
- لا ينتج تناقضًا رسميًا جديدًا.
- لا يغير Verdict.

---

# 27. Trusted Prompt Assembly

Prompt الخام لا يدخل Bus.

المسار:

```text
React / API
→ prompt_template_id
→ prompt_hash
→ structured_input_refs
→ System Bus
→ socket.ai.integration
→ AI Integration Shell
→ Trusted Prompt Assembly
→ Template Resolution
→ Structured Input Fetch
→ Redaction
→ Final Prompt Construction
→ Provider Call
```

الحالة الحالية:

```text
Provider Policy = DENY_ALL
Providers = []
Network = false
```

لا ينشأ `socket.ai.experience`.

---

# 28. العقود والـSockets المستهدفة

## 28.1 عقود Pre-Run

```text
consulting.frame.build.v1
strategic.alignment.evaluate.v1
global.economic.context.build.v1
global.opportunity.analyze.v1
national.economic.context.build.v1
market.context.build.v1
market.assumptions.build.v1
indicator.relationships.analyze.v1
intelligence.context.seal.v1
intelligence.review.submit.v1
intelligence.approval.issue.v1
```

## 28.2 عقود Runtime المستقبلية

```text
intelligence.predecision.pack.build.v1
intelligence.predecision.pack.v1
decision.council.v2
```

## 28.3 Post-Snapshot

```text
intelligence.final.projection.v1
ai.narrative.overlay.v1
```

## 28.4 AI

الحالي:

```text
ai.integration.request.v1
socket.ai.integration
module.ai_integration
```

المستقبلي المحتمل:

```text
ai.integration.request.v2
```

---

# 29. التخزين المستهدف

## 29.1 الجداول/الكيانات الجديدة المقترحة

- `intelligence_context_drafts`
- `intelligence_contexts`
- `intelligence_context_components`
- `intelligence_review_overlays`
- `intelligence_approval_receipts`
- `market_assumptions`
- `assumption_requirement_profiles`
- `indicator_relationships`
- `contradiction_register`
- `predecision_packs`
- `ai_narrative_overlays`

لا تُنشأ في الإنتاج دون ACR مناسب ومراجعة العزل متعدد المؤسسات.

## 29.2 قواعد العزل

كل كيان Tenant-owned يحمل:

```text
organization_id
project_id
```

ويخضع لـ:

- Server-side authorization.
- Cross-tenant deny tests.
- Audit.
- No legacy fallback in production.

---

# 30. الواجهة وتجربة المستخدم

## 30.1 رحلة المستخدم

- Arabic RTL first.
- English technical term مع شرح عربي عند أول استخدام.
- Bilingual switch.
- Click-first.
- تقليل الكتابة الحرة.
- الموقع أولًا.
- GPS + Map pin.
- منع التحليل عبر دولتين في المرحلة الحالية.
- External file field واضح.
- Actual/Partial/No figures choice.
- عرض مستوى نضج الدراسة.
- عرض Low/Base/High ومصادرها.
- عرض الفجوات والتعارضات.
- عرض الثقة وأسبابها.

## 30.2 KPIs

- Monte Carlo KPI من Finance Result.
- Sensitivity KPIs.
- Strategic Alignment KPI.
- Assumption Maturity.
- Evidence Coverage.
- Contradiction count.
- Five Sovereign Persona KPIs:
  - مؤشر جاهزية التنفيذ.
  - مؤشر القبول التجاري.
  - مؤشر المتانة الفنية.
  - مؤشر جاهزية الانتقال.
  - مؤشر تحمل الضغط.

الواجهة لا تعيد حسابها.

## 30.3 التقارير

- Report.
- Decision Pack.
- Funder Report.
- DOCX.
- PDF.
- PPTX.
- XLSX.

كلها مشتقة من Snapshot أو Projection معتمدة.

---

# 31. مصفوفة As-Built إلى Target

| المجال | As-Built | Target | التغيير |
|---|---|---|---|
| Runtime | AAS v1 مجمد | يبقى | لا تغيير دون ACR |
| Finance | منفذ | يبقى مالك الأرقام | توسيع Contract فقط عند الحاجة |
| Sector | منفذ | يبقى مستقلًا | لا يعاد تسميته Market |
| Evidence | منفذ | يستوعب AIA refs | توسعة |
| Decision v1 | منفذ | يبقى | لا تعديل |
| Decision v2 | غير موجود | عقد جديد | ACR |
| AI Shell | منفذ ومعطل | يعاد استخدامه | ACR للتفعيل |
| Source Registry | منفذ | سياسات منفصلة | IACR/ACR |
| Dataset Intake | جزئي | UX كامل | خارج Runtime غالبًا |
| Intelligence Context | غير موجود | Draft/Sealed/Overlay/Receipt | ACR |
| Market Intelligence | غير موجود | Module مستقل | ACR |
| Reference Cost | غير موجود | Module مستقل | ACR |
| Indicator Relationships | غير موجود | Module مستقل | ACR |
| Final Projection | غير موجود | Post-Snapshot | ACR |
| AI Narrative | غير موجود | Overlay | ACR |
| Exports | Backend موجود | UX/API كامل | خارج Runtime غالبًا |

---

# 32. خطة ACR المرحلية

```text
ACR-AIA-01  Production Pre-Run Foundation
ACR-AIA-02  Intelligence Context & Approval Model
ACR-AIA-03  Market Intelligence & Reference Cost Modules
ACR-AIA-04  Indicator Relationships & Pre-Decision Pack
ACR-AIA-05  Decision Council v2
ACR-AIA-06  Post-Snapshot Deterministic Projection
ACR-AIA-07  Governed AI Experience Activation
ACR-AIA-08  External Source Connector Activation
```

كل ACR:

- محدود الأثر.
- قابل للاختبار.
- قابل للتراجع.
- مصحوب بـParity tests.
- لا يكسر v1.
- يحدث Freeze Manifest عند اللزوم.
- يحدّث Runtime Status.

---

# 33. الأمن والتدقيق

يسجل Metadata فقط:

```text
event_type
organization_id
project_id
run_id
snapshot_id
intelligence_context_id
contract_id
module_id
output_hash
approval_receipt_hash
policy_versions
reason_code
correlation_id
timestamp
```

لا يسجل:

- Prompt خام.
- API keys.
- Secrets.
- ملفات كاملة.
- محتوى محمي غير مصرح به.
- بيانات شخصية غير لازمة.

---

# 34. اختبارات القبول

## 34.1 AAS Integrity

1. لا Runtime ثانٍ.
2. لا Direct Calls.
3. لا Socket جديد للـAI Experience.
4. Snapshot Assembly نقطة الختم الوحيدة.
5. v1 يبقى كما هو.
6. كل Runtime extension يحتاج ACR.

## 34.2 Context

7. Draft قابل للتعديل.
8. Sealed Context غير قابل للتعديل.
9. Overlay لا يدخل Context hash.
10. Receipt يثبت الاعتماد.
11. Version chain قابل للتحقق.
12. Stale Context يرفض في v2.
13. Invalidation Matrix تعمل.

## 34.3 Assumptions

14. السلة غير المتجانسة ترفض.
15. HOME لا يخلط مع COMMERCIAL.
16. Listed Price لا يساوي CapEx.
17. User Acceptance لا يرفع Maturity.
18. Evidence Validation منفصلة.
19. Finance Eligibility منفصلة.
20. Low/Base/High تحمل Impact Direction.
21. High Cost يذهب للسيناريو المتحفظ.
22. High Selling Price يذهب للسيناريو المتفائل.
23. Monte Carlo يبقى ملك Finance.

## 34.4 Decision

24. v1 لا يتغير.
25. v2 يحتاج Context وPack.
26. لا fallback صامت.
27. Decision Input Manifest محفوظ.
28. لا Risk أو Execution يدخلان v2.
29. Double-count guard يمنع الإشارة المكررة.
30. Snapshot تحفظ أساس القرار.

## 34.5 Projection وAI

31. Final Projection لا تنتج inference جديدًا.
32. فشل Projection لا يفشل Snapshot.
33. AI Narrative ليس جزءًا من Snapshot.
34. AI Output ليس Evidence Primary.
35. Trusted Prompt Assembly داخل Shell.
36. Prompt الخام لا يدخل Bus.
37. DENY_ALL يمنع Provider call.

## 34.6 UX والتقارير

38. External file field ظاهر.
39. GPS consent يعمل.
40. Click-first flow.
41. Monte Carlo KPI من Snapshot.
42. Five Persona KPIs من المخرجات الرسمية.
43. DOCX/PDF/PPTX/XLSX downloads تعمل من الواجهة.
44. التحذيرات الحرجة لا تختفي حسب الاشتراك.
45. RTL وBilingual switch يعملان.

---

# 35. بوابة منع النسيان

لا تحصل الوثيقة على `FINAL` حتى تحقق:

```text
No orphan requirements
No ownerless outputs
No unversioned contracts
No undocumented runtime changes
No feature marked implemented without evidence
No target feature without an ACR path
No UI capability without backend ownership
No engine output without Snapshot behavior
No intelligence output without evidence and confidence
No high-value discussion item missing from traceability
No silent fallback between decision versions
No hidden contradiction
No duplicate signal weighting
```

---

# 36. الحالة الرسمية

```text
Architecture Status = CANDIDATE FOR FINAL REVIEW
Document Version = AIA-02 v1.2.0
As-Built Baseline = VERIFIED AGAINST 2026-07-21 ARCHITECTURE REPORT
Constitutional Compatibility = TARGETED
AAS Runtime Freeze Integrity = PRESERVED
Freeze Status = NOT YET FROZEN
Production Activation = PENDING STAGED ACRs
Current Runtime Integration = NOT ACTIVE
Decision Council v1 = UNCHANGED
Decision Council v2 = DEFINED_NOT_IMPLEMENTED
AI Experience Routing = EXISTING AI INTEGRATION SHELL
AI Provider Execution = DISABLED
Provider Policy = DENY_ALL
External Acquisition Policy = STRICT_OPEN_DATA_ONLY_V1
User Evidence Intake Policy = SEPARATE_GOVERNED_POLICY
Market Intelligence = DEFINED_NOT_IMPLEMENTED
Reference Cost Intelligence = DEFINED_NOT_IMPLEMENTED
Pre-Decision Pack = DEFINED_NOT_IMPLEMENTED
Final Intelligence = POST_SNAPSHOT DETERMINISTIC PROJECTION
Snapshot Assembly = SOLE SEALING AUTHORITY
```

---

# 37. الحكم الختامي

تعتمد هذه الوثيقة التوافق بين:

- ما بُني فعليًا في ASIE.
- ما قررته AIA-01.
- ما اتفق عليه في الذكاء الاستشاري والاستراتيجي والاقتصادي والسوقي.
- ما يلزم للمستخدم الذي لا يملك أرقامًا فعلية.
- ما يلزم لمقارنة المؤشرات وكشف التعارضات.
- ما يلزم لشرح النتائج دون إعطاء AI سلطة الأرقام أو الحكم.
- ما يلزم لبناء كل قدرة تدريجيًا دون كسر AAS Runtime Freeze.

هذه النسخة **مرشحة للمراجعة النهائية فقط**، ولا تعتبر مجمدة أو مفعلة إنتاجيًا قبل استكمال مراجعة التغطية واعتماد IACR/ACRs المرحلية.
