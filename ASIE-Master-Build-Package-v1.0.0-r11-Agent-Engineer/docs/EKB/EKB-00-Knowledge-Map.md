# ASIE Engineering Knowledge Base — EKB-003

## قاعدة المعرفة الهندسية لمنصة AlphaSigma Intelligence Engine — ASIE

| الحقل | القيمة |
|---|---|
| Document ID | `ASIE-EKB-003-Engineering-Knowledge-Base-v1.0.0-RC1-AR` |
| الحالة | `GITHUB ADMISSION / REVIEW CANDIDATE` |
| اللغة | عربية، مع إبقاء المعرفات القانونية بالإنجليزية |
| النطاق | الجرد المعرفي، المجالات، المحركات، الوثائق، البرومبتات، وترتيب قراءة Agent |
| لا يفعل | لا يعدل Runtime، لا يكسر AAS Freeze، لا يفعل AI Provider، لا يفعل network fetch |

---

## 1. سبب EKB

أصبح ASIE مشروعًا واسعًا يحتوي:

- دستورًا.
- معمارية تنفيذ AAS.
- معمارية ذكاء AIA.
- عقودًا وSockets وModules.
- محركات مالية وسوقية واستراتيجية.
- Dynamic Input Blueprint.
- Decision Council.
- خطط تنفيذ.
- قواعد تسمية.
- معايير جودة.
- Dashboard وLaunch Guide.
- سياسات برومبت وتشغيل Agent.

لذلك لم يعد البرومبت مكانًا مناسبًا لحمل المعرفة. البرومبت يجب أن يحدد المهمة فقط. المعرفة طويلة الأجل يجب أن تكون داخل EKB.

---

## 2. التسلسل الحاكم للمصادر

| الترتيب | الطبقة | السلطة | آلية التغيير |
|---|---|---|---|
| 1 | AAS Runtime Freeze | يحكم التنفيذ والملفات المجمدة | ACR + Freeze Manifest جديد |
| 2 | AIA-01 Intelligence Constitution | يحكم الذكاء وحدود AI | ICCR |
| 3 | Canonical Registers | يحكم المسميات والعقود وAPI والمخرجات | Controlled PR + CI |
| 4 | ACRs / Implementation Plans | يحكم التغييرات المعتمدة | ACR/IACR/Controlled Plan |
| 5 | EKB Domain Specs | يحدد أين توضع المعرفة وما يقرأه Agent | EKB PR |
| 6 | Prompt Templates | قالب تنفيذ فقط | تحديث تحت EKB |
| 7 | Chat Context | سياق مؤقت | لا يعتمد كمصدر حقيقة |

---

## 3. الوثائق الحاكمة الأساسية

| الوثيقة | الحالة | الوظيفة |
|---|---|---|
| `docs/ASIE-AAS-Runtime-Freeze-Manifest-v1.0.json` | `FROZEN` | يحمي مسار AAS والملفات المجمدة |
| `docs/AIA-01-Intelligence-Constitution-v1.0.0.md` | `FINAL / BINDING` | يحكم حدود الذكاء وSanad وAI |
| `docs/AIA-02-Intelligence-Operating-Architecture-v1.2.1-Candidate.md` | `CANDIDATE FOR FINAL REVIEW` | يحدد تشغيل AIA كمكمل لا Runtime ثانٍ |
| `docs/ACR-DIB-001-Dynamic-Input-Blueprint.md` | `DRAFT FOR IMPLEMENTATION` | يحدد DIB وApproved Input Manifest |
| `docs/ASIE-DIB-LIVE-INTEGRATION-EXECUTION-PLAN-2026-07-25.md` | `CONTROLLED IMPLEMENTATION PLAN` | يخطط ربط DIB بالمسار الحي |
| `docs/ASIE-CANONICAL-TERMINOLOGY-REGISTER-v1.0.0.md` | `CONTROLLED BASELINE` | يحكم المسميات |
| `registry/asie-canonical-terminology.v1.json` | `CONTROLLED BASELINE` | سجل آلي للعقود/Sockets/Modules |
| `docs/ASIE-CANONICAL-API-OUTPUT-REGISTER-v1.0.0.md` | `CONTROLLED BASELINE` | يحكم API والمخرجات |
| `registry/asie-canonical-api-output.v1.json` | `CONTROLLED BASELINE` | سجل آلي لـAPI وSnapshot outputs |
| `docs/EKB/EKB-08-Customer-Language-and-Presentation-Contract.md` | `BINDING / REMEDIATION OPEN` | يحكم لغة العميل، إخفاء التفاصيل الداخلية، والتقارير والتصديرات |

---

## 4. المجالات المعرفية

| Domain | الحالة | الوظيفة |
|---|---|---|
| AAS Runtime | `IMPLEMENTED / FROZEN` | Kernel → Hearts → Bus → Socket → Module Runtime → Snapshot |
| AIA Intelligence | `PARTIAL / CONTROLLED` | AI Experience, Consulting, Strategic, Economic, National Intelligence |
| DIB | `PARTIAL` | يلتقي فيه مسار الفكرة فقط ومسار الأرقام/الملفات |
| Product AI Interview | `PLANNED/PARTIAL` | مقابلة موجهة لا تولد أرقامًا نهائية |
| Template Registry | `PLANNED/PARTIAL` | اختيار نموذج بنود المشروع |
| Question Registry | `PLANNED/PARTIAL` | أسئلة محكومة حسب القالب |
| Data Intake | `PARTIAL` | Manual/CSV/XLSX/PDF-text intake |
| Quote Extraction | `PLANNED` | استخراج عروض الأسعار وربطها بالبند |
| Market Estimation Engine | `PLANNED/PARTIAL` | تقدير نطاقات سوقية P25/P75/Weighted Median |
| Finance Engine | `IMPLEMENTED / EVOLVING` | الحسابات المالية، الحساسية، Monte Carlo |
| Decision Council | `IMPLEMENTED / EVOLVING` | حكم سيادي عبر شخصيات القرار |
| Risk Engine | `IMPLEMENTED` | سجل المخاطر |
| Execution Engine | `IMPLEMENTED` | خطة التنفيذ |
| Evidence Ledger | `IMPLEMENTED` | الأدلة وسلاسلها |
| KPI Intelligence | `PLANNED/PARTIAL` | مؤشرات القرار والمتابعة |
| National Economic Intelligence | `PLANNED` | مؤشرات الاقتصاد المحلي الرسمية |
| Economic Opportunity Intelligence | `PLANNED` | بيانات World Bank/IMF/OECD/UN عند التفعيل |
| Strategic Alignment Score | `PLANNED` | توافق المشروع مع Vision 2030 والأولويات |
| Dashboard Command Center | `PARTIAL/IMPLEMENTED` | لوحة قيادة وقراري اليوم والأقسام القادمة |
| Launch Guide | `PLANNED/PARTIAL` | تراخيص، جهات، خطوات، موظفين، موردين |
| Reports / Decision Pack | `IMPLEMENTED/PARTIAL` | تقارير Snapshot وحزم قرار |
| Security / Tenant Isolation | `IMPLEMENTED` | جلسات، صلاحيات، عزل، fail closed |
| Deployment / Beta | `PARTIAL` | Docker، PDF Renderer، WAL، CORS، E2E |

---

## 5. قاعدة DIB

ASIE لا يعامل كل المشاريع بنموذج مالي ثابت. يوجد مساران:

1. مستخدم لديه فكرة فقط.
2. مستخدم لديه أرقام أو ملفات أو عروض أسعار.

كلاهما يجب أن يلتقي عند:

```text
Dynamic Input Blueprint
→ Approved Input Manifest
→ Manifest Validation Gate
→ Finance Engine
```

Finance Engine لا يقرأ:

- نص AI خام.
- ملفات خام.
- أسعار إنترنت غير معتمدة.
- UI fields غير محكومة.

Finance يقرأ فقط:

```text
Approved Input Manifest / normalized_inputs
```

---

## 6. سياسة البرومبت

### Constitution Prompt

يحتوي القواعد الثابتة:

- التزم بـEKB.
- لا تكسر AAS Freeze.
- لا تنشئ Runtime موازي.
- لا تفعّل AI Provider أو network fetch.
- لا تتجاوز Bus/Socket/Module Runtime.

### Task Prompt

يحتوي المهمة فقط:

- ما المطلوب؟
- ما الملفات/الوثائق التي تقرأ؟
- ما الملفات المسموح تعديلها؟
- ما معايير الإغلاق؟

### Context

يحمل الوثائق والملفات المطلوبة فقط، لا كل معرفة المشروع.

---

## 7. قاعدة إضافة فكرة جديدة

أي فكرة جديدة تمر بهذه الأسئلة:

1. هل هي قاعدة دستورية؟ → AAS/AIA Constitution.
2. هل تغير التنفيذ المجمد؟ → ACR.
3. هل تخص محركًا؟ → Domain Spec.
4. هل تخص واجهة؟ → Product/UX Domain.
5. هل تخص مصدر بيانات؟ → Data/Market Source Policy.
6. هل تخص برومبت؟ → Prompt Policy.
7. هل هي مجرد تنفيذ؟ → Task Prompt.

لا توضع الفكرة مباشرة داخل البرومبت الطويل.

---

## 8. حالة هذه النسخة

هذه نسخة GitHub Admission لـEKB-003. النسخة الكاملة المنسقة Word/ZIP محفوظة كأثر مراجعة محلي، أما GitHub فيعتمد Markdown/JSON كمصدر قابل للتدقيق.
