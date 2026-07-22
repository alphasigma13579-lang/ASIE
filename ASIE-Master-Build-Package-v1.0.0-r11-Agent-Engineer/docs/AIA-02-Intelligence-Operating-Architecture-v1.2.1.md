# AIA-02 — Intelligence Operating Architecture
## المعمارية التشغيلية للذكاء في منصة AlphaSigma Intelligence Engine — ASIE
### الإصدار `v1.2.1` — Adopted Controlled Baseline

---

## 0. بيانات الوثيقة

| البند | القيمة |
|---|---|
| رمز الوثيقة | `AIA-02` |
| الاسم الإنجليزي | Intelligence Operating Architecture |
| الاسم العربي | المعمارية التشغيلية للذكاء |
| الإصدار | `v1.2.1` |
| الحالة المعمارية | `FINAL / ADOPTED CONTROLLED BASELINE` |
| تاريخ الاعتماد | `2026-07-22` — `Asia/Riyadh` |
| حالة الضبط | `CONTROLLED — IACR REQUIRED FOR AIA-02 CHANGES` |
| حالة التفعيل الإنتاجي | `PENDING STAGED ACRs` |
| الوثيقة الدستورية الحاكمة | `docs/AIA-01-Intelligence-Constitution-v1.0.0.md` — `FINAL / BINDING` |
| المعمارية التنفيذية الحاكمة | `AAS Runtime Freeze v1.0` |
| خط الأساس التنفيذي | ASIE r11 Local Core — مراجعة 21 يوليو 2026 |
| آلية تعديل AIA-01 | `ICCR — Intelligence Constitutional Change Request` |
| آلية تعديل وثائق AIA التشغيلية | `IACR — Intelligence Architecture Change Request` |
| أي تغيير يؤثر على AAS | `ACR — Architectural Change Request` |
| سلطة ختم الحقيقة السيادية الوحيدة | `Snapshot Assembly` |
| حالة AI الحالية | `DISABLED / DENY_ALL / NO PROVIDERS / NO NETWORK` |
| سياسة الاستحواذ الخارجي الحالية | `STRICT_OPEN_DATA_ONLY_V1` |
| سياسة أدلة المستخدم | مستقلة عن سياسة الاستحواذ الخارجي |
| مبدأ التنفيذ | `AAS governs execution. AIA governs intelligence.` |

---

## 0.1 سجل تصحيحات v1.2.1

تعالج هذه النسخة ملاحظات المراجعة الدستورية على v1.2.0 دون تعديل AIA-01 أو AAS Runtime Freeze:

1. فصل **قفل نزاهة سياق الذكاء** عن **ختم الحقيقة السيادي** الذي يبقى حصريًا لـSnapshot Assembly.
2. تعريف دورة Production Pre-Run بوصفها دورة إعداد محكومة داخل AAS، لا Runtime ولا Orchestrator ولا Snapshot مستقلة.
3. اعتماد `Intelligence Synthesis Pack` اسماً دستورياً للمخرج، واستخدام `Pre-Decision Intelligence Envelope` كغلاف نقل فقط.
4. تثبيت عقد طلب ونتيجة مستقلين لـDecision Council v2 مع بقاء v1 دون تعديل.
5. ربط فئات استخدام AI بسياسة التنفيذ والمراجعة والتخزين والأهلية.
6. تثبيت منهج الثقة، قواعد سلة الأسعار، المقارنة، Impact Direction، ومنع ازدواج الإشارات.
7. إضافة سجل تتبع للمتطلبات الـ53 إلى المالك والعقد وACR واختبار القبول.

هذه التصحيحات **توثيقية فقط**. لا تمنح صلاحية تنفيذ إنتاجي ولا تعدل أي ملف مجمد.

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
| مختوم سياديًا | حقيقة Runtime لا تصبح رسمية إلا بعد ختم Snapshot Assembly |
| مقفل النزاهة | سجل محتوى غير قابل للتعديل ويحمل Hash، لكنه ليس Snapshot ولا حقيقة تحليلية رسمية |
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
- Integrity-Locked Intelligence Context.
- Context Approval Receipt.
- Consulting Intelligence Module.
- Strategic Intelligence Module.
- Global Economic Intelligence Module.
- National Economic Intelligence Module.
- Market Intelligence Module مستقل.
- Reference Cost, Price & Assumption Intelligence.
- Indicator Relationships Module.
- Intelligence Synthesis Pack وغلافه التشغيلي Pre-Decision Intelligence Envelope.
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
12. `decision.council.evaluate.v2` و`decision.council.v2` — إن أُنشئا — عقدا طلب ونتيجة جديدان مستقلان.
13. Finance Engine وحده يملك NPV وIRR وDSCR وBreak-even وMonte Carlo المالي.
14. Evidence Ledger يملك الأدلة وLineage.
15. Decision Council يملك Verdict.
16. Risk Engine يملك Risk Register.
17. Execution Engine يملك Execution Plan.
18. Snapshot Assembly هو سلطة **ختم الحقيقة السيادية** الوحيدة؛ قفل نزاهة سجل Pre-Run لا يجعله Snapshot ولا حقيقة رسمية.
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

- يعمل داخل المنصة بعد ACR إنتاجي معتمد يغطي العقود والسockets والـRepository والـAPI والتكامل مع Run. سجل `ACR-AIA-01` المؤرخ 2026-07-21 يثبت Offline Foundation فقط، ولا يمنح هذا التفعيل.
- يستخدم Kernel وBus وSocket وModule Runtime الموجودين؛ لا ينشئ Runtime أو Bus أو Registry أو Orchestrator موازيًا.
- يدار بواسطة `IntelligenceContextWorkflow` جديد داخل AAS، بمعرف `context_build_id` مستقل عن `run_id`، ويطبق idempotency وtimeouts وretry limits وaudit.
- يكتب Draft ونسخًا مقفلة النزاهة إلى Repository رسمي داخل transaction، لكنه لا ينشئ Snapshot ولا يدعي حقيقة تحليلية رسمية.
- لا يستخدم `RunScopedModuleRuntime` الحالي قسرًا قبل وجود Run؛ يحدد ACR adapter نطاق Context Build فوق `ModuleRuntime` نفسه.
- لا تكتمل العملية الدستورية كمخرج تحليلي رسمي إلا عندما يستهلك ProjectRunWorkflow نسخة معتمدة، ويحفظ مراجعها في Decision Input Manifest، ثم يختم Snapshot Assembly نتيجة التشغيل.
- فشل Pre-Run لا يغيّر Snapshot سابقة ولا يكتب نتيجة جزئية بوصفها معتمدة.
- **يحتاج ACR** لأنه يضيف workflow وعقودًا وsockets وتخزينًا إنتاجيًا خارج Freeze الحالي.

### 6.3.1 دورة الحالة والاتساق

```text
DRAFT
→ VALIDATING
→ INTEGRITY_LOCKED
→ REVIEW_PENDING
→ APPROVED_FOR_RUN | APPROVED_WITH_CONDITIONS | REJECTED | STALE
```

- كل انتقال حالة يستخدم optimistic version وidempotency key.
- قفل النزاهة يحسب `context_hash` على محتوى canonical ولا ينشئ seal سياديًا.
- المراجعة Overlay منفصل ولا يدخل `context_hash`.
- Approval Receipt هو إذن الاستهلاك، وليس حقيقة جديدة.
- تغيير dependency محكوم ينقل الحالة إلى `STALE` دون تعديل النسخة القديمة.
- لا retries غير محدودة، ولا retry لخطأ validation حتمي.

## 6.4 Runtime Intelligence

- يقرأ مخرجات مختومة من المحركات ومراجع Context مقفلة النزاهة ومعتمدة للاستهلاك.
- لا يجمع بيانات جديدة.
- لا يتفاعل مع المستخدم.
- لا يعيد بناء Context.
- ينشئ `Intelligence Synthesis Pack` بالمسمى الدستوري.
- يغلف مرجعه داخل `Pre-Decision Intelligence Envelope` للنقل فقط.
- يمرر الغلاف إلى `decision.council.evaluate.v2` عبر `socket.decision.council` الموجود.
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

الرسم يصف المسار المنطقي الكامل، ولا يعني أن مخرجات Pre-Run تضاف مباشرة إلى `REQUIRED_MODULE_OUTPUTS`. يظل عدد output keys السيادية ستة. في v2 يبقى output key باسم `decision_result`، ويتغير عقد نتيجته من `decision.council.v1` إلى `decision.council.v2` وفق dispatch مسجل في ACR. أما مراجع Context وSynthesis وApproval فتدخل `decision_input_manifest` وتختم داخل Snapshot بوصفها أساس القرار، لا كمحركات سيادية إضافية.

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

### 8.1.1 ربط فئات AI الدستورية بالتشغيل

| الفئة | الاستخدام المسموح | المراجعة | التخزين | Snapshot eligibility | سياسة المزود الحالية |
|---|---|---|---|---|---|
| `UX-LOW` | شرح، ترجمة، إعادة صياغة، تنظيم نص | مراجعة المستخدم عند الحفظ؛ sampling تشغيلي بعد التفعيل | مؤقت افتراضيًا؛ يحفظ فقط بطلب صريح | غير مؤهل | `DENY_ALL` |
| `ADVISORY` | اقتراحات وأسئلة وملخصات غير ملزمة | إلزامية قبل نشره أو ربطه بالمشروع | Generation record منفصل عن الحقيقة | غير مؤهل؛ يمكن حفظ مرجع العرض فقط | `DENY_ALL` |
| `EVIDENCE-SENSITIVE` | استخراج أو تفسير محتوى مع source refs | Human Review إلزامي + OutputValidation + source validation | output وprovenance وreview منفصلة | ليس Evidence Primary؛ لا يدخل إلا كمخرج مراجع ومصنف | `DENY_ALL` |
| `DECISION-ADJACENT` | شرح نتيجة محفوظة أو شروط قرار دون تعديلها | Human Review إلزامي قبل release خارجي | Overlay مرتبط بـSnapshot ولا يغيرها | غير مؤهل لتغيير Verdict أو الأرقام | `DENY_ALL` |
| `PROHIBITED` | رقم رسمي، Verdict، قانون ملزم، تفعيل مصدر، تعديل Snapshot | يرفض قبل provider routing | audit metadata للرفض فقط | محظور | `DENY_ALL` |

كل generation record مستقبلي يحمل: `request_id`, `organization_id`, `project_id`, `snapshot_id` إن وجد، `prompt_template_id`, `prompt_hash`, `model_provider`, `model_id`, `model_version`, `policy_version`, `input_ref_hashes`, `redaction_policy_version`, `output_hash`, `token_usage`, `cost_minor`, `review_status`, `retention_class`, وtimestamps. يمنع تخزين prompt خام أو secrets في Audit.

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

## 8.7 سجل التتبع الدستوري للمتطلبات الـ53

الاختبار المذكور هو معرّف قبول إلزامي، وليس ادعاءً بوجود ملف اختبار حالي. لا ينتقل المتطلب إلى `IMPLEMENTED` قبل ربط المعرّف بملف اختبار ودليل تشغيل محفوظ.

| Requirement | المالك | العقد/السطح | بوابة التغيير | اختبار القبول |
|---|---|---|---|---|
| `AIA-REQ-AI-001` | AI Experience | `ai.integration.request.v2` | ACR-AIA-09 | `AIA-T-AI-001` |
| `AIA-REQ-AI-002` | AI Experience | `ai.integration.request.v2` | ACR-AIA-09 | `AIA-T-AI-002` |
| `AIA-REQ-AI-003` | AI Experience + Validation | `ai.integration.request.v2` | ACR-AIA-09 | `AIA-T-AI-003` |
| `AIA-REQ-AI-004` | AI Integration Shell | `ai.integration.request.v2` | ACR-AIA-09 | `AIA-T-AI-004` |
| `AIA-REQ-AI-005` | OutputValidation | `ai.integration.result.v1` | As-Built guard | `AIA-T-AI-005` |
| `AIA-REQ-AI-006` | HumanReviewGate | `ai.narrative.overlay.v1` | ACR-AIA-09 | `AIA-T-AI-006` |
| `AIA-REQ-AI-007` | AAS/AIA governance | `socket.ai.integration` فقط | Invariant | `AIA-T-AI-007` |
| `AIA-REQ-CON-001` | Consulting Intelligence | `consulting.frame.build.v1` | ACR-AIA-03 | `AIA-T-CON-001` |
| `AIA-REQ-CON-002` | Consulting Intelligence | `consulting.frame.build.v1` | ACR-AIA-03 | `AIA-T-CON-002` |
| `AIA-REQ-CON-003` | Consulting Intelligence | `consulting.frame.build.v1` | ACR-AIA-03 | `AIA-T-CON-003` |
| `AIA-REQ-CON-004` | Consulting Intelligence | `consulting.frame.build.v1` | ACR-AIA-03 | `AIA-T-CON-004` |
| `AIA-REQ-CON-005` | Consulting Intelligence | `consulting.frame.build.v1` | ACR-AIA-03 | `AIA-T-CON-005` |
| `AIA-REQ-CON-006` | Consulting Intelligence | `consulting.frame.build.v1` | ACR-AIA-03 | `AIA-T-CON-006` |
| `AIA-REQ-CON-007` | Consulting Intelligence | `consulting.frame.build.v1` | ACR-AIA-03 | `AIA-T-CON-007` |
| `AIA-REQ-CON-008` | Consulting Intelligence | `consulting.frame.build.v1` | ACR-AIA-03 | `AIA-T-CON-008` |
| `AIA-REQ-CON-009` | Consulting Intelligence | `consulting.frame.build.v1` | ACR-AIA-03 | `AIA-T-CON-009` |
| `AIA-REQ-STR-001` | Strategic Intelligence | `strategic.alignment.evaluate.v1` | ACR-AIA-03 | `AIA-T-STR-001` |
| `AIA-REQ-STR-002` | Strategic Intelligence | `strategic.alignment.evaluate.v1` | ACR-AIA-03 | `AIA-T-STR-002` |
| `AIA-REQ-STR-003` | Strategic Intelligence | `strategic.alignment.evaluate.v1` | ACR-AIA-03 | `AIA-T-STR-003` |
| `AIA-REQ-GLO-001` | Global Economic Intelligence | `global.economic.context.build.v1` | ACR-AIA-04 | `AIA-T-GLO-001` |
| `AIA-REQ-GLO-002` | Global Economic Intelligence | `global.opportunity.analyze.v1` | ACR-AIA-04 | `AIA-T-GLO-002` |
| `AIA-REQ-NAT-001` | National Economic Intelligence | `national.economic.context.build.v1` | ACR-AIA-04 | `AIA-T-NAT-001` |
| `AIA-REQ-NAT-002` | National Economic Intelligence | `national.economic.context.build.v1` | ACR-AIA-04 | `AIA-T-NAT-002` |
| `AIA-REQ-NAT-003` | National Economic Intelligence | `national.economic.context.build.v1` | ACR-AIA-04 | `AIA-T-NAT-003` |
| `AIA-REQ-MKT-001` | Market Intelligence | `market.context.build.v1` | ACR-AIA-05 | `AIA-T-MKT-001` |
| `AIA-REQ-MKT-002` | Market Intelligence | `market.context.build.v1` | ACR-AIA-05 | `AIA-T-MKT-002` |
| `AIA-REQ-COST-001` | Reference Cost Intelligence | `market.assumptions.build.v1` | ACR-AIA-05 | `AIA-T-COST-001` |
| `AIA-REQ-COST-002` | Reference Cost Intelligence | `market.assumptions.build.v1` | ACR-AIA-05 | `AIA-T-COST-002` |
| `AIA-REQ-COST-003` | Reference Cost Intelligence | `market.assumptions.build.v1` | ACR-AIA-05 | `AIA-T-COST-003` |
| `AIA-REQ-COST-004` | Reference Cost Intelligence | `market.assumptions.build.v1` | ACR-AIA-05 | `AIA-T-COST-004` |
| `AIA-REQ-COST-005` | Reference Cost Intelligence | `market.assumptions.build.v1` | ACR-AIA-05 | `AIA-T-COST-005` |
| `AIA-REQ-COST-006` | Reference Cost + Finance | assumption output → Finance | ACR-AIA-05 | `AIA-T-COST-006` |
| `AIA-REQ-COST-007` | Reference Cost Intelligence | maturity policy | ACR-AIA-05 | `AIA-T-COST-007` |
| `AIA-REQ-COST-008` | Project Intake + Reference Cost | intake state | Product PR + ACR-AIA-05 | `AIA-T-COST-008` |
| `AIA-REQ-COST-009` | Review Policy | review overlay | ACR-AIA-02.1/02.2/05 | `AIA-T-COST-009` |
| `AIA-REQ-COST-010` | Reference Cost + Finance boundary | finance eligibility | ACR-AIA-05 | `AIA-T-COST-010` |
| `AIA-REQ-CMP-001` | Indicator Relationships | `indicator.relationships.analyze.v1` | ACR-AIA-06 | `AIA-T-CMP-001` |
| `AIA-REQ-CMP-002` | Indicator Relationships | `indicator.relationships.analyze.v1` | ACR-AIA-06 | `AIA-T-CMP-002` |
| `AIA-REQ-CMP-003` | Indicator Relationships | contradiction register | ACR-AIA-06 | `AIA-T-CMP-003` |
| `AIA-REQ-CMP-004` | Indicator Relationships | comparability policy | ACR-AIA-06 | `AIA-T-CMP-004` |
| `AIA-REQ-CMP-005` | Indicator Relationships | causality guard | Invariant + ACR-AIA-06 | `AIA-T-CMP-005` |
| `AIA-REQ-CMP-006` | Intelligence Synthesis | signal ledger | ACR-AIA-06 | `AIA-T-CMP-006` |
| `AIA-REQ-UX-001` | Product UI | RTL design system | Product PR | `AIA-T-UX-001` |
| `AIA-REQ-UX-002` | Product UI | locale contract | Product PR | `AIA-T-UX-002` |
| `AIA-REQ-UX-003` | Product UI | guided journey | Product PR | `AIA-T-UX-003` |
| `AIA-REQ-UX-004` | Product UI + Location Policy | consented geolocation | Product PR | `AIA-T-UX-004` |
| `AIA-REQ-UX-005` | Product UI + Market Gateway | map pin/provider | Product PR + ACR-AIA-10 | `AIA-T-UX-005` |
| `AIA-REQ-UX-006` | Dataset Intake | file intake API/UI | Product PR | `AIA-T-UX-006` |
| `AIA-REQ-UX-007` | Finance projection | Snapshot KPI | Product PR | `AIA-T-UX-007` |
| `AIA-REQ-UX-008` | Decision projection | Snapshot personas | Product PR | `AIA-T-UX-008` |
| `AIA-REQ-RPT-001` | Reporting/Export | Snapshot projections | Product PR | `AIA-T-RPT-001` |
| `AIA-REQ-RPT-002` | Reporting/Frontend | no-recalculation guard | Invariant | `AIA-T-RPT-002` |
| `AIA-REQ-RPT-003` | Entitlement + Reporting | critical-warning policy | Product PR | `AIA-T-RPT-003` |

## 8.8 مصفوفة التوافق مع AIA-01

| بند AIA-01 | الالتزام الدستوري | موضع تنفيذه في AIA-02 v1.2.1 |
|---|---|---|
| 5.1 | سيادة AAS وعدم إنشاء Runtime/Bus/Snapshot موازية | 4، 6.3، 7، 32، 34.1 |
| 5.2 | المصدر والثقة والمراجعة والـLineage والـHash | 10، 13، 17، 23 |
| 5.3 | فصل Fact/Indicator/Assumption/Interpretation وغيرها | 17، 18، 30 |
| 5.4 | AI لا يملك الأرقام أو القرار | 8.1.1، 26، 27، 34.5 |
| 5.5 | Evidence First | 13، 15، 17، 20 |
| 5.6 | استقلال ملكيات المحركات | 4، 14، 16، 20، 21 |
| 7 | فئات استخدام AI | 8.1.1 |
| 8–9 | التوافق الاستراتيجي والمؤشرات الاقتصادية | 8.3، 17، 18 |
| 10 | الافتراضات السوقية المرجعية | 15–17 |
| 11 | المقارنة والتقاطع والتعارض | 18–19 |
| 12 | Intelligence Synthesis لا يصدر Verdict | 20–21 |
| 13 | تصنيف وحوكمة المصادر | 13 |
| 14 | Human Review | 11 و8.1.1 |
| 15 | حقول عقود الذكاء | 28.5 |
| 16 | تكامل ProjectRunEnvelope بالمراجع فقط | 20.4، 22، 23 |
| 17 | دستور Snapshot | 7، 23–25 |
| 18 | تمييز أنواع المخرجات في UI | 30 |
| 20 | الانحرافات المحظورة | 4، 24، 27، 34، 35 |
| 22–23 | اختبارات القبول وتعريف الإغلاق | 34–35 |

لا تعد هذه المصفوفة دليلاً تنفيذياً؛ هي دليل عدم تعارض وثائقي. الدليل التنفيذي يبقى اختبارات وعقوداً ومسارات مسجلة بعد ACR.

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
            Integrity Lock
                    │
                    ▼
    Integrity-Locked Intelligence Context
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
| Review Overlay | Integrity-Locked Context | Domain expert review |
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
- لا Partial Synthesis Pack يدخل Decision Council دون وسم وحكم أهليته.
- لا تحويل صامت من v2 إلى v1.

---

# 10. Draft وIntegrity-Locked Intelligence Context

## 10.1 Draft Intelligence Context

خصائصه:

- قابل للتعديل.
- لا يملك Hash نهائيًا.
- لا يدخل Run.
- لا يستخدمه Decision Council.
- يمكن حذف أو تعديل مكوناته.
- يحمل `draft_version`.

## 10.2 Integrity-Locked Intelligence Context

خصائصه:

- غير قابل للتعديل.
- يمتلك `context_id`.
- يمتلك `context_hash`.
- يمتلك `context_version`.
- يرتبط بمخرجات مختومة.
- أي تعديل ينتج إصدارًا جديدًا.
- لا يحتوي مرجع Review Overlay.
- ليس Snapshot ولا مخرجاً رسمياً ولا يملك Verdict أو رقماً مالياً سيادياً.
- قفله عملية نزاهة content-addressing داخل Repository، وليس استدعاءً لـSnapshot Assembly.
- لا يصبح قابلاً للاستهلاك في Run إلا بوجود Approval Receipt صالح ومطابق للـhash.

## 10.3 الحقول المعتمدة

```text
intelligence_context_id
context_build_id
organization_id
project_id
context_status
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
operation_id
idempotency_key_hash
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
reviewed_output_hash
decision
conditions
reason
override_status
affected_contract
affected_snapshot_ref
created_at
supersedes_overlay_id
```

## 11.2 Approval Receipt

هو الإثبات القابل للاستهلاك في Run، ويحتوي:

```text
approval_receipt_id
approval_receipt_hash
organization_id
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

تصنيف المصدر الدستوري الإلزامي الموروث من AIA-01:

```text
official_primary
official_secondary
international_institution
regulated_financial_research
academic_research
industry_research
consulting_reference
manufacturer
authorized_distributor
commercial_marketplace
classified_marketplace
user_supplied
ai_generated
unverified
```

لا يغير رفع المستخدم للملف تصنيفه تلقائيًا إلى موثوق. يحتفظ السجل بفصل واضح بين `source_classification`, `evidence_validation_status`, و`human_review_decision`.

### 13.2.1 أمن الملفات المرفوعة

- allowlist للامتداد وMIME وmagic bytes، لا امتداد الملف وحده.
- حد للحجم وعدد الصفحات/الصفوف وعمق ZIP ونسبة الضغط لمنع zip bombs.
- malware scan وquarantine قبل parsing في بيئة الإنتاج.
- parser معزول بلا macros ولا روابط خارجية ولا تنفيذ محتوى نشط.
- استخراج OCR/text يسجل extractor وversion وhash ولا يستبدل الملف الأصلي.
- تخزين الملف الأصلي في Object Storage مشفر مستقبلاً؛ SQLite تحفظ metadata والمراجع فقط.
- تصنيف بيانات وretention وحق حذف مرتبطان بالمؤسسة والمشروع.
- أي محتوى مستخرج يبقى `user_supplied` حتى المراجعة ولا يصبح Evidence Primary تلقائيًا.

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

### 15.5.1 قواعد السلة والتقدير الافتراضية

- بعد deduplication، أقل من 3 ملاحظات قابلة للمقارنة أو أقل من ناشرين مستقلين يبقي النتيجة `SCREENING_ONLY` ولا يمنح `MARKET_ESTIMATED`.
- المورد نفسه عبر Marketplace متعددة يعد ناشرًا اقتصادياً واحداً عند اكتشافه.
- عند `n >= 4` يستخدم IQR لاكتشاف القيم الشاذة؛ الاستبعاد يحتاج reason code ويحفظ القيمة الأصلية. عند `n < 4` لا يوجد حذف آلي، بل `OUTLIER_REVIEW_REQUIRED`.
- `Weighted Median` هو estimator الافتراضي للسلة غير المتجانسة جزئياً. الأوزان versioned ومطبّعة ومشتقة من جودة المصدر والحداثة وتشابه المواصفة والملاءمة الجغرافية.
- كل تحويل عملة يحمل `fx_rate`, `fx_source_ref`, `fx_as_of`, وbase currency. يمنع خلط أسعار من تواريخ مختلفة دون normalization.
- VAT والجمارك والشحن والتأمين والتركيب والاختبار والتدريب والقطع الأولية تفصل في `included_costs` و`excluded_costs` ولا تفترض ضمنياً.
- L2 يحتاج عرض مورد قابل للتحقق؛ L3 يحتاج عقداً أو أمر شراء نافذاً. عدد النتائج وحده لا يرفع النضج.
- قواعد الحد الأدنى قابلة للتخصيص حسب `item_class` بعقد versioned، ولا يجوز للواجهة تغييرها.

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

القيم المسموحة لـ`impact_direction`:

```text
COST_INCREASE_NEGATIVE
REVENUE_INCREASE_POSITIVE
NON_MONOTONIC
UNKNOWN
```

`NON_MONOTONIC` و`UNKNOWN` لا يسمحان بالربط الآلي بين Low/High والسيناريو؛ يجب أن يحدد Finance Engine mapping موثقاً أو يعيد `NOT_READY`.

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

- كل بعد رقم في `[0,1]` مع reason codes ومراجع أدلة.
- يحدد كل contract مجموعة أوزان versioned مجموعها `1.0`.
- يحسب `overall_confidence` بمتوسط هندسي موزون حتى لا تخفي قيمة قوية ضعفاً حرجاً:

```text
overall_confidence = exp(Σ weight_i × ln(max(dimension_i, 0.01)))
```

- الأوزان الافتراضية لعقد الافتراضات السوقية: جودة المصدر 0.20، التغطية 0.15، تشابه المواصفة 0.20، الجغرافيا 0.10، القطاع 0.10، الحداثة 0.10، القابلية للمقارنة 0.10، وثقة المنهج 0.05.
- أي `critical_confidence_failure` قد يمنع Finance Eligibility.
- الفشل الحرج يشمل: مصدر محظور، مواصفة غير متطابقة، عملة/وحدة غير قابلة للتوحيد، تاريخ منتهي، سلة غير متجانسة، أو مراجعة إلزامية مفقودة.
- المستويات الافتراضية: أقل من 0.40 منخفض، 0.40–0.69 متوسط، 0.70–0.84 مرتفع، و0.85 فأعلى مرتفع جداً؛ هذه درجة جودة دليل وليست احتمال صحة إحصائياً.
- كل بُعد قابل للتفسير.
- يجب عرض أسباب انخفاض الثقة للمستخدم.
- لا ترفع User Acceptance الثقة تلقائيًا.
- لا يسمح بتغيير الأوزان أو thresholds دون إصدار جديد للعقد واختبارات معايرة وحساسية.

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
frequency_compatibility
geographic_compatibility
sector_compatibility
denominator_compatibility
nominal_real_basis
currency_normalization_ref
seasonal_adjustment_ref
rebasing_ref
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

لا ينتج `difference` أو`direction` قبل نجاح فحوص التعريف والوحدة والفترة والتكرار والجغرافيا والقطاع والمقام والأساس الاسمي/الحقيقي. أي تحويل أو rebasing أو seasonal adjustment يسجل كTransformation مستقل في Lineage.

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
source_lineage_hash
signal_fingerprint
duplicate_of
consumed_by
double_count_guard
```

يحسب `signal_fingerprint` حتميًا من: المخرج الأصلي، تعريف المقياس، الفترة، الجغرافيا، القطاع، baseline، وlineage hash. إذا تطابقت البصمة أو تشاركت إشارتان الأصل الاقتصادي نفسه، تحفظ الثانية كـ`duplicate_of` ولا تدخل الوزن أو العد مرة أخرى. يسجل `consumed_by` كدفتر استهلاك append-only داخل سياق التشغيل.

Intelligence Synthesis Pack لا يعيد:

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

# 20. Intelligence Synthesis Pack وPre-Decision Intelligence Envelope

## 20.1 الحالة

```text
DEFINED_NOT_IMPLEMENTED
PENDING_ACR
```

`Intelligence Synthesis Pack` هو الاسم الدستوري للمخرج المعرفي. `Pre-Decision Intelligence Envelope` ليس مخرج ذكاء آخر؛ هو غلاف نقل AAS يحمل مرجع الـPack وhash والـApproval Receipt إلى Decision Council v2، ولا يكرر محتواه.

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

## 20.4 العقود والهوية

```text
Build request contract: intelligence.synthesis.build.v1
Domain output contract: intelligence.synthesis.v1
Transport envelope: PreDecisionIntelligenceEnvelope.v1
Existing transport socket: socket.decision.council
```

الحقول الدنيا للغلاف:

```text
project_id
run_id
snapshot_id
intelligence_synthesis_pack_id
intelligence_synthesis_pack_hash
intelligence_context_id
intelligence_context_hash
approval_receipt_id
approval_receipt_hash
contract_set_version
correlation_id
```

---

# 21. Decision Council v1 وv2

## 21.1 v1

يبقى دون تغيير:

```text
Request: decision.council.evaluate.v1
Result:  decision.council.v1
Socket:  socket.decision.council
Output key: decision_result
```

## 21.2 v2

يُنشأ بعقدي طلب ونتيجة جديدين بعد `ACR-AIA-07`، مع إعادة استخدام socket نفسه:

```text
Request: decision.council.evaluate.v2
Result:  decision.council.v2
Socket:  socket.decision.council
Output key: decision_result
```

المدخلات:

```text
finance
blockers
readiness_gates
sector_intelligence
predecision_intelligence_envelope
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
decision_input_contract_id
decision_output_contract_id
aia_runtime_mode
intelligence_context_required
intelligence_synthesis_required
projection_version
```

## Run v1

```text
decision_contract_version = v1
decision_input_contract_id = decision.council.evaluate.v1
decision_output_contract_id = decision.council.v1
aia_runtime_mode = DISABLED
intelligence_context_required = false
intelligence_synthesis_required = false
```

## Run v2

```text
decision_contract_version = v2
decision_input_contract_id = decision.council.evaluate.v2
decision_output_contract_id = decision.council.v2
aia_runtime_mode = GOVERNED
intelligence_context_required = true
intelligence_synthesis_required = true
```

يحظر التحويل الصامت بين النسختين.

---

# 23. Decision Input Manifest

عند v2 يجب أن تحفظ Snapshot:

```text
decision_input_manifest:
  decision_contract_version
  decision_input_contract_id
  decision_output_contract_id
  intelligence_synthesis_pack_id
  intelligence_synthesis_pack_hash
  intelligence_context_id
  intelligence_context_hash
  approval_receipt_id
  approval_receipt_hash
  external_acquisition_policy_version
  user_evidence_intake_policy_version
  review_policy_version
  contract_set_version
```

ويحمل `decision.council.v2` المراجع نفسها. يعدل `SnapshotAssembly` تحت ACR ليقبل عقد نتيجة واحداً فقط يطابق dispatch المختار، مع بقاء output key `decision_result` وبقية المخرجات الستة كما هي. يمنع قبول v1 وv2 معاً في Run واحد.

---

# 24. Failure Semantics

## v1

- فشل AIA لا يؤثر؛ لأنها ليست جزءًا من Run.

## v2

- Missing required Context → `FAIL_CLOSED`.
- Missing Intelligence Synthesis Pack أو envelope/hash mismatch → `FAIL_CLOSED`.
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
- يحمل provider/model/version وtemplate/policy versions وinput/output hashes وreview status وretention class.
- أي regeneration ينشئ Overlay جديدًا ولا يستبدل سجلًا مراجعًا بصمت.
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
intelligence.context.lock.v1
intelligence.review.submit.v1
intelligence.approval.issue.v1
```

## 28.2 عقود Runtime المستقبلية

```text
intelligence.synthesis.build.v1
intelligence.synthesis.v1
PreDecisionIntelligenceEnvelope.v1
decision.council.evaluate.v2
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

## 28.5 الحقول الإلزامية لكل عقد AIA

تنفيذاً لـAIA-01، لا يكفي تسجيل contract ID. يحدد كل عقد قبل التنفيذ:

```text
contract_id
contract_version
producer
consumer
permitted_input
prohibited_input
output_type
evidence_requirements
confidence_rules
freshness_rules
review_requirement
snapshot_eligibility
audit_behavior
rejection_behavior
idempotency_policy
lineage_policy
tenant_scope
timeout_policy
retry_policy
```

أي عقد يفتقد واحداً منها يبقى `DEFINED_NOT_IMPLEMENTED` ولا يسجل في Runtime production registry.

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
- `intelligence_synthesis_packs`
- `ai_generation_records`
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
- Composite uniqueness وindexes تبدأ بـ`organization_id` للكيانات Tenant-owned.
- Repository lookup يتحقق من tenant قبل إرجاع وجود الكيان لمنع enumeration.
- كل endpoint جديد يملك اختبارات: same-tenant allow، cross-tenant deny، spoofed header deny، role deny، platform break-glass audit.
- لا تعتمد سلامة العزل على UI أو header وحده؛ principal + membership + resource ownership تتحقق server-side.

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
| Decision v2 | غير موجود | `evaluate.v2` طلب و`council.v2` نتيجة، output key نفسه | ACR |
| AI Shell | منفذ ومعطل | يعاد استخدامه | ACR للتفعيل |
| Source Registry | منفذ | سياسات منفصلة | IACR/ACR |
| Dataset Intake | جزئي | UX كامل | خارج Runtime غالبًا |
| Intelligence Context | غير موجود | Draft/Integrity-Locked/Overlay/Receipt | ACR |
| Market Intelligence | غير موجود | Module مستقل | ACR |
| Reference Cost | غير موجود | Module مستقل | ACR |
| Indicator Relationships | غير موجود | Module مستقل | ACR |
| Final Projection | غير موجود | Post-Snapshot | ACR |
| AI Narrative | غير موجود | Overlay | ACR |
| Exports | Backend موجود | UX/API كامل | خارج Runtime غالبًا |

---

# 32. خطة ACR المرحلية

```text
ACR-AIA-01  Offline Production Pre-Run Foundation Record — historical, no production activation
ACR-AIA-02.1  Intelligence Context / Review / Approval Model — historical offline phase
ACR-AIA-02.2  Authorization and Audit Boundary — historical offline phase
NEXT-UNASSIGNED  As-Built Reconciliation + governed production admission gate
ACR-AIA-03  Consulting & Strategic Intelligence Modules
ACR-AIA-04  Global & National Economic Intelligence Modules
ACR-AIA-05  Market Intelligence & Reference Cost Modules
ACR-AIA-06  Indicator Relationships & Intelligence Synthesis Pack
ACR-AIA-07  Decision Council v2
ACR-AIA-08  Post-Snapshot Deterministic Projection
ACR-AIA-09  Governed AI Experience Activation
ACR-AIA-10  External Source Connector Activation
```

كل ACR:

- محدود الأثر.
- قابل للاختبار.
- قابل للتراجع.
- مصحوب بـParity tests.
- لا يكسر v1.
- يحدث Freeze Manifest عند اللزوم.
- يحدّث Runtime Status.
- يحدد contracts وsockets وmodules والجداول والمسارات المتأثرة صراحة.
- يرفق threat model delta واختبارات cross-tenant وidempotency والفشل الجزئي.
- يثبت أن Snapshot v1 projection parity لم تتغير قبل فتح dispatch v2.
- لا ينتقل إلى ACR اللاحق قبل تحقق exit criteria وتوثيق rollback للمرحلة الحالية.

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
4. Snapshot Assembly نقطة ختم الحقيقة السيادية الوحيدة، وContext Integrity Lock لا ينتج Snapshot.
5. v1 يبقى كما هو.
6. كل Runtime extension يحتاج ACR.

## 34.2 Context

7. Draft قابل للتعديل.
8. Integrity-Locked Context غير قابل للتعديل ولا يعد حقيقة رسمية.
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
25. v2 يحتاج Context وIntelligence Synthesis Pack وApproval Receipt متطابقة hashes.
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

## 34.7 الاتساق والثقة والعزل

46. إعادة Context build بنفس idempotency key والمدخل تعيد النتيجة نفسها؛ اختلاف المدخل يرفض.
47. فشل أي كتابة في Integrity Lock يعيد transaction كاملة ولا يترك نسخة معتمدة جزئياً.
48. تعديل dependency ينشئ `STALE` دون تغيير hash أو النسخة التاريخية.
49. المتوسط الهندسي الموزون يطابق golden vectors، والفشل الحرج يمنع Finance Eligibility.
50. أقل من حجم السلة الأدنى يبقى `SCREENING_ONLY`.
51. IQR لا يحذف تلقائياً عند `n < 4`، وكل استبعاد يحمل reason وlineage.
52. currency/tax/shipping/install normalization قابلة لإعادة الإنتاج من المراجع.
53. `NON_MONOTONIC` و`UNKNOWN` لا يرتبطان بالسيناريو تلقائياً.
54. المقارنة غير المتوافقة في المقام أو nominal/real أو التكرار تعيد `NOT_DIRECTLY_COMPARABLE`.
55. signal fingerprint يمنع احتساب الأصل الاقتصادي نفسه مرتين.
56. كل عقد AIA يرفض الحقول المحظورة والـtenant mismatch قبل التنفيذ.
57. same-tenant allow وcross-tenant/spoofed-header/role deny مثبتة لكل endpoint جديد.
58. فئة `PROHIBITED` ترفض قبل provider routing ولا تخزن المحتوى الخام.
59. AI generation record يحفظ provenance والتكلفة والنسخ دون prompt خام أو secrets.
60. dispatch يقبل عقد نتيجة قرار واحداً فقط لكل Run ولا يسمح بمزيج v1/v2.

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
Constitution clauses mapped to operating controls
All 53 requirement IDs mapped to owner, contract/surface, change gate and acceptance ID
```

---

# 36. الحالة الرسمية

```text
Architecture Status = FINAL / ADOPTED CONTROLLED BASELINE
Document Version = AIA-02 v1.2.1
Adoption Date = 2026-07-22 Asia/Riyadh
As-Built Baseline = VERIFIED AGAINST 2026-07-21 ARCHITECTURE REPORT
Constitutional Compatibility = DOCUMENT-LEVEL ALIGNED WITH AIA-01 v1.0.0
Requirement Traceability = 53/53 DOCUMENTED; IMPLEMENTATION EVIDENCE PENDING
AAS Runtime Freeze Integrity = PRESERVED
Change Control = IACR REQUIRED FOR AIA-02 CHANGES; ACR REQUIRED FOR AAS IMPACT
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
Intelligence Synthesis Pack = DEFINED_NOT_IMPLEMENTED
Pre-Decision Intelligence Envelope = DEFINED_NOT_IMPLEMENTED
Final Intelligence = POST_SNAPSHOT DETERMINISTIC PROJECTION
Snapshot Assembly = SOLE SOVEREIGN TRUTH SEALING AUTHORITY
Context Integrity Lock = NON-SOVEREIGN PRE-RUN CONTENT HASH
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

هذه النسخة **معتمدة بوصفها خط الأساس المعماري التشغيلي الحاكم لـAIA-02** اعتبارًا من 22 يوليو 2026. يحل الإصدار `v1.2.1` محل `v1.2.0` بالكامل كمصدر توجيه وبناء.

هذا الاعتماد لا يعني اكتمال التنفيذ ولا يفعّل أي Provider أو شبكة أو مصدر خارجي أو `Decision Council v2`. تبقى القدرات المعلّمة `DEFINED_NOT_IMPLEMENTED` أو `PENDING STAGED ACRs` غير مفعلة حتى استكمال بواباتها واختباراتها. أي تعديل لاحق على AIA-02 يحتاج `IACR`، وأي أثر على AAS Runtime Freeze يحتاج `ACR` مستقلًا.
