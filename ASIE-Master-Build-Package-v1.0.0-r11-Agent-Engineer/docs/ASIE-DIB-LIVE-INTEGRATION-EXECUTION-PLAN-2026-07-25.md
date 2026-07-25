# ASIE DIB Live Integration Execution Plan — 2026-07-25

## خطة تحويل Dynamic Input Blueprint من Runtime مستقل إلى مسار منتج حي

| البند | القيمة |
|---|---|
| المنصة | AlphaSigma Intelligence Engine — ASIE |
| الوثيقة | ASIE-DIB-LIVE-INTEGRATION-EXECUTION-PLAN-2026-07-25 |
| الحالة | CONTROLLED IMPLEMENTATION PLAN |
| النطاق | DIB Runtime, المحركات، العقود، الوثائق، API، الواجهة، Project Run، Finance، Snapshot |
| لا يكسر | AAS Runtime Freeze v1.0 |
| لا يفعل | مزودي AI، الشبكة الخارجية، أو جلب بيانات حقيقي من الإنترنت |

---

## 1. سبب الوثيقة

تم تنفيذ `backend/dib_runtime.py` ودمج PR #41 لإثبات منطق Dynamic Input Blueprint كـBackend Runtime مختبر، لكن بقيت الحاجة إلى وثيقة خطة تنفيذ تربط ما سبق بالمسار الحي للمنتج.

هذه الوثيقة تجمع:

1. ما اتفق عليه في المخطط السابق.
2. ما تم تنفيذه في DIB Runtime.
3. المحركات المتفق عليها داخل ASIE.
4. العقود والـSockets والـModules المطلوبة.
5. الوثائق الحاكمة التي يجب الرجوع لها.
6. خطة التحويل إلى مسار حي داخل الواجهة وProject Run.
7. معيار الإغلاق حتى لا تبقى عناصر غير منفذة أو غير مربوطة.

---

## 2. الوضع الحالي بعد PR #41

### 2.1 ما تم تنفيذه فعليًا

تم تنفيذ Runtime مستقل ومختبر للجزئية التالية:

```text
Project Profile
→ Product AI Interview
→ Dynamic Input Blueprint
→ Data Intake / Market Evidence
→ Customer Item Decision
→ Approved Input Manifest
→ Manifest Validation Gate
→ Finance from Approved Manifest
→ DIB Draft Revision / Revision Comparison
```

الملفات الحية:

| الملف | الدور |
|---|---|
| `backend/dib_runtime.py` | تنفيذ DIB Runtime المستقل |
| `tests/test_dib_complete_runtime.py` | اختبار قبول للجزئية كاملة |

### 2.2 حدود التنفيذ الحالي

رغم نجاح PR #41، التنفيذ ما زال Backend Runtime مستقلًا، وليس بعد المسار الرسمي الذي تسلكه الواجهة وProject Run.

ما لم يكتمل بعد:

1. تسجيل DIB رسميًا داخل `backend/aas_registry.py`.
2. إضافة DIB Module Adapters إلى `backend/module_runtime.py`.
3. إضافة API رسمي للواجهة.
4. تخزين Blueprints وManifests وRevisions في Repository.
5. ربط Project Run باستهلاك `Approved Input Manifest` بدل `project.inputs` الخام.
6. إظهار lineage داخل Snapshot والتقارير.
7. بناء واجهة المستخدم لمسار الإدخال الذكي.

---

## 3. المسار الحي المطلوب

المسار النهائي المطلوب قبل اعتبار الجزئية مكتملة كمنتج:

```text
User Interface
→ API
→ Kernel
→ Heart Controller
→ Bus Controller
→ ASIE System Bus
→ Socket Contract Layer
→ Module Runtime
→ DIB Modules
→ Approved Input Manifest
→ Manifest Validation Gate
→ Finance Engine
→ Evidence Ledger
→ Sector Intelligence
→ Decision Council
→ Risk Engine
→ Execution Engine
→ Snapshot Assembly
→ Reports / Decision Pack
```

قاعدة إلزامية:

> Finance Engine لا يستقبل أرقامًا خامًا من الواجهة أو AI أو ملف. Finance Engine يستقبل فقط `Approved Input Manifest` أو `normalized_inputs` ناتجة عنه بعد مرور Manifest Validation Gate.

---

## 4. المحركات والمكونات المعتمدة

### 4.1 محركات ومكونات AAS الأساسية

| المكوّن | الاسم المعتمد | الدور | الحالة |
|---|---|---|---|
| Kernel | AAS Kernel | حارس التشغيل الأعلى | منفذ |
| Heart Controller | Heart Controller | توزيع المهمة على القلوب | منفذ |
| Hearts | M1 / M2 / M3 | تحكم تنفيذي وسيط | منفذ |
| Bus Controller | Bus Controller | قبول أو رفض الرسائل | منفذ |
| System Bus | ASIE System Bus | قناة الرسائل الوحيدة | منفذ |
| Socket Contract Layer | Socket Contract Layer | ربط Socket بعقد | منفذ |
| Module Runtime | Module Runtime | تنفيذ الوحدات المسجلة | منفذ |
| Snapshot Assembly | Snapshot Assembly | تجميع لقطة غير قابلة للتلاعب | منفذ |

### 4.2 محركات المنتج الحالية

| المكوّن | الاسم المعتمد | Runtime ID | الدور |
|---|---|---|---|
| Finance | Finance Engine | `module.finance` | الحساب المالي والحساسية وMonte Carlo |
| Evidence | Evidence Ledger | `module.evidence_ledger` | دفتر الأدلة وروابطها |
| Sector | Sector Intelligence | `module.sector_intelligence` | استخبارات القطاع والسياق |
| Decision | Decision Council | `module.decision_council` | مجلس القرار والسيادة |
| Risk | Risk Engine | `module.risk_engine` | سجل المخاطر وملخص المخاطر |
| Execution | Execution Engine | `module.execution_engine` | خطة التنفيذ |
| Reports | Reports Module | `module.reports` | تقارير Snapshot |
| Decision Pack | Decision Pack Module | `module.decision_pack` | حزمة القرار المقروءة |
| AI | AI Integration Shell | `module.ai_integration` | غلاف مقفل؛ لا مزودات ولا شبكة |

### 4.3 مكونات DIB المطلوب إدخالها في AAS

| المكوّن | Runtime ID المقترح | الدور | مصدره الحالي |
|---|---|---|---|
| Template Registry | `module.template_registry` | اختيار قالب المشروع والاحتياجات | `dib_runtime.py` |
| Question Registry | `module.question_registry` | أسئلة المقابلة الموجهة | `dib_runtime.py` |
| Product AI Interview | `module.product_ai_interview` | مقابلة حتمية Offline لا تولد أرقامًا نهائية | `dib_runtime.py` |
| Data Intake | `module.data_intake` | CSV/XLSX/PDF-text/manual rows | `dib_runtime.py` |
| Dynamic Input Blueprint | `module.dynamic_input_blueprint` | تجميع البنود وحالاتها | `dib_runtime.py` |
| Market Intelligence | `module.market_intelligence` | متوسطات سوقية محلية/محاكاة حالية | `dib_runtime.py` |
| Approved Input Manifest | `module.approved_input_manifest` | تحويل البنود المعتمدة إلى manifest | `dib_runtime.py` |
| Manifest Validation Gate | `module.manifest_validation_gate` | منع Finance قبل الاعتماد | `dib_runtime.py` |
| DIB Revision | `module.dib_revision` | مراجعات ومسودات Blueprint | `dib_runtime.py` |

---

## 5. العقود المطلوبة

### 5.1 عقود DIB المنفذة في Runtime المستقل

هذه العقود موجودة داخل `backend/dib_runtime.py`، ويجب إدخالها رسميًا في AAS Registry عند تنفيذ DIB-LIVE-002:

```text
template.registry.v1
question.registry.v1
product.ai.interview.v1
data.intake.v1
dynamic.input.blueprint.v1
market.query.request.v1
market.evidence.pack.v1
customer.item.decision.v1
approved.input.manifest.v1
manifest.validation.v1
dib.draft.revision.v1
```

### 5.2 Sockets المطلوبة

```text
socket.template.registry
socket.question.registry
socket.product.ai.interview
socket.data.intake
socket.dynamic.input.blueprint
socket.market.query
socket.customer.item.decision
socket.approved.input.manifest
socket.manifest.validation
socket.dib.revision
```

### 5.3 سياسة العقود

1. لا يعاد تسمية أي عقد حي في AAS.
2. لا يستخدم PascalCase لعقود جديدة.
3. كل عقد جديد يجب تسجيله في:
   - `backend/aas_registry.py`
   - `registry/asie-canonical-terminology.v1.json`
   - الاختبارات المرتبطة.
4. كل API جديد يجب تسجيله في:
   - `registry/asie-canonical-api-output.v1.json`
   - `tests/test_canonical_api_output.py`

---

## 6. الوثائق الحاكمة والمرجعية

| الوثيقة | الدور |
|---|---|
| `docs/ASIE-AAS-Runtime-Freeze-Manifest-v1.0.json` | حدود عدم كسر AAS Runtime Freeze |
| `docs/AIA-01-Intelligence-Constitution-v1.0.0.md` | دستور الذكاء وعدم تفويض القرار للذكاء الاصطناعي |
| `docs/AIA-02-Intelligence-Operating-Architecture-v1.2.1.md` | تشغيل AIA كمكمّل لا كRuntime ثانٍ |
| `docs/ACR-DIB-001-Dynamic-Input-Blueprint.md` | قرار DIB المعماري الأصلي |
| `docs/ASIE-CANONICAL-TERMINOLOGY-REGISTER-v1.0.0.md` | المسميات الرسمية |
| `registry/asie-canonical-terminology.v1.json` | سجل المصطلحات الآلي |
| `docs/ASIE-CANONICAL-API-OUTPUT-REGISTER-v1.0.0.md` | مسارات API ومخرجات Snapshot |
| `registry/asie-canonical-api-output.v1.json` | سجل API والمخرجات الآلي |
| `docs/IMPLEMENTATION-STATUS-MATRIX.md` | تمييز المنفذ والمخطط والمعطل |
| `docs/PROJECT-ORIENTATION.md` | توجيه المطور والـAgent |
| هذه الوثيقة | خطة تنفيذ DIB Live Integration |

---

## 7. خطة DIB-LIVE-002

### المرحلة 1 — Registry Admission

إدخال عقود DIB وSockets وModules في `backend/aas_registry.py` مع تحديث سجل المصطلحات.

معيار القبول:

```text
DIB contracts registered = PASS
DIB sockets registered = PASS
DIB modules registered = PASS
Canonical terminology audit = PASS
```

### المرحلة 2 — Module Runtime Adapters

إضافة Adapters رسمية:

```text
TemplateRegistryModuleAdapter
QuestionRegistryModuleAdapter
ProductAIInterviewModuleAdapter
DataIntakeModuleAdapter
DynamicInputBlueprintModuleAdapter
MarketIntelligenceModuleAdapter
ApprovedInputManifestModuleAdapter
ManifestValidationGateModuleAdapter
DIBRevisionModuleAdapter
```

معيار القبول:

```text
All DIB module calls pass through System Bus = PASS
No DIB direct runtime bypass for live path = PASS
```

### المرحلة 3 — Repository Persistence

إضافة تخزين واسترجاع لـ:

```text
dib_blueprints
dib_items
market_evidence_packs
approved_input_manifests
dib_revisions
```

أو تخزين JSON منظّم داخل Repository الحالي إن كان ذلك أنسب للمرحلة المحلية.

معيار القبول:

```text
User can leave and resume DIB flow = PASS
Manifest can be retrieved before Project Run = PASS
Revision lineage persisted = PASS
```

### المرحلة 4 — HTTP API

إضافة مسارات API رسمية:

```text
GET  /api/projects/{project_id}/dib
POST /api/projects/{project_id}/dib/interview
POST /api/projects/{project_id}/dib/intake
POST /api/projects/{project_id}/dib/blueprint
POST /api/projects/{project_id}/dib/items/{item_id}/decision
POST /api/projects/{project_id}/dib/manifest
POST /api/projects/{project_id}/dib/revisions
```

معيار القبول:

```text
src/api.ts updated = PASS
src/contracts.ts updated = PASS
canonical API register updated = PASS
API audit = PASS
```

### المرحلة 5 — Project Run Integration

تعديل `ProjectRunWorkflow` أو طبقة `execute_project_run_pipeline` بحيث يتم قبل Finance:

```text
latest approved_input_manifest
→ manifest.validation.v1
→ finance.calculate.v1
```

لا يسمح بـ:

```text
project.inputs raw → Finance Engine
```

إلا في Legacy/compatibility test path محدد وموسوم.

معيار القبول:

```text
Project without approved manifest blocks before Finance = PASS
Project with approved manifest reaches Finance = PASS
Finance lineage references manifest_id = PASS
```

### المرحلة 6 — Snapshot / Report Lineage

إضافة lineage إلى Snapshot/Report:

```text
approved_input_manifest_id
blueprint_id
blueprint_revision
input_source_mix
unknown_items
file_imported_items
market_estimated_items
human_approved_items
manifest_validation_status
```

معيار القبول:

```text
Snapshot carries DIB lineage = PASS
Report shows input provenance = PASS
Decision Pack can reference manifest = PASS
```

### المرحلة 7 — Frontend Flow

إضافة واجهة `مسار الإدخال الذكي` داخل رحلة المشروع:

1. فكرة فقط.
2. لدي أرقام.
3. لدي ملف CSV/XLSX.
4. لدي عرض سعر PDF.
5. قائمة البنود.
6. قبول/تعديل/رفض/لا أعرف.
7. إنشاء Approved Manifest.
8. تشغيل التحليل بعد الاعتماد.

معيار القبول:

```text
Click-first Arabic RTL flow = PASS
No required step bypass = PASS
Zero can be intentional only with state/reason = PASS
Run button disabled until manifest approved = PASS
```

---

## 8. حدود AI والبحث السوقي

### 8.1 AI

`Product AI Interview` في هذه المرحلة لا يعني تفعيل مزود ذكاء اصطناعي حقيقي.

الحالة الحالية:

```text
AI providers = disabled
network = disabled
raw prompt = prohibited
AI output = suggestions only
```

### 8.2 Market Intelligence

`Market Intelligence` في DIB-LIVE-002 يبدأ كـlocal simulated/evidence-shaped adapter، ثم يفتح لاحقًا عبر ACR مستقل عندما تعتمد مصادر KSA الحقيقية.

لا يسمح بإدخال متوسطات سوقية غير موثقة إلى Finance دون:

1. Evidence Pack.
2. Outlier policy.
3. Source refs.
4. Confidence.
5. Customer decision.
6. Approved Manifest.

---

## 9. ترتيب المحركات بعد DIB Live

الترتيب النهائي داخل تشغيل المشروع:

```text
DIB Live Path
→ Approved Input Manifest
→ Finance Engine
→ Evidence Ledger
→ Sector Intelligence
→ Decision Council
→ Risk Engine
→ Execution Engine
→ Snapshot Assembly
→ Reports Module
→ Decision Pack Module
```

`AI Integration Shell` يبقى خارج التوليد الرقمي، ولا يملك قرارًا أو رقمًا ماليًا.

---

## 10. جدول الإغلاق النهائي

لا تغلق DIB-LIVE-002 إلا إذا تحقق الآتي:

| البند | معيار الإغلاق |
|---|---|
| Registry | كل عقود وSockets وModules DIB مسجلة |
| Runtime | كل DIB Adapters تعمل عبر Module Runtime |
| API | كل المسارات مسجلة ومختبرة |
| Repository | Blueprint/Manifest/Revision محفوظة وقابلة للاسترجاع |
| Finance | لا يعمل من مدخلات خام في المسار الحي |
| Snapshot | يسجل Manifest lineage |
| Frontend | المستخدم يستطيع إكمال المسار بالنقر لا بالكتابة الحرة |
| Tests | اختبارات DIB + Canonical Terminology + Canonical API ناجحة |
| CI | Build وCompile وTests كلها PASS |
| Documentation | Implementation Status Matrix محدثة بصدق |

---

## 11. ممنوعات هذه المرحلة

1. ممنوع إعادة تسمية عقود AAS المجمدة.
2. ممنوع تفعيل AI Provider حقيقي.
3. ممنوع تفعيل network fetch.
4. ممنوع تمرير أرقام AI مباشرة إلى Finance.
5. ممنوع اعتبار PDF OCR أو Document AI كاملًا إذا كان المدعوم فقط PDF-text.
6. ممنوع وصف DIB بأنه Live Product Path قبل ربطه بالواجهة وProject Run.
7. ممنوع خلط `Module` كنوع Runtime مع `Engine` كاسم معماري.

---

## 12. حالة البنود السابقة بعد PR #41 وقبل DIB-LIVE-002

| البند | بعد PR #41 | مطلوب في DIB-LIVE-002 |
|---|---:|---|
| Project Profile | جزئي | ربطه بنموذج DIB حي |
| Template Registry | Backend Runtime | تسجيله في AAS Registry |
| Product AI Interview | Backend Runtime | API + Adapter + UI |
| قائمة البنود | Backend Runtime | UI + Persistence |
| CSV/XLSX/PDF-text Intake | Backend Runtime | API + Repository |
| Dynamic Input Blueprint | Backend Runtime | Live Project State |
| حالات البند | Backend Runtime | واجهة ومراجعة بشرية |
| Market Evidence | Backend Runtime محاكى | Socket رسمي + Evidence lineage |
| Approved Manifest | Backend Runtime | Project Run source of truth |
| Manifest Validation | Backend Runtime | Gate قبل Finance |
| Finance | يعمل من Manifest داخل DIB Runtime | يعمل من Manifest داخل Project Run |
| Snapshot | موجود | إضافة DIB lineage |
| Draft Revision | Backend Runtime | Persistence + UI |

---

## 13. قرار التنفيذ

الخطوة التالية المعتمدة هي:

```text
DIB-LIVE-002 — Dynamic Input Blueprint Live Integration
```

وليست:

```text
بناء وثائق إضافية فقط
إعادة تصميم AAS
تفعيل AI
تفعيل البحث الخارجي
```

الهدف العملي: جعل المسار الذي تم إثباته في `backend/dib_runtime.py` هو المسار الفعلي للمستخدم داخل ASIE.
