# ASIE Canonical Terminology Register

## سجل المصطلحات والمعرفات الحاكمة

| البند | القيمة |
|---|---|
| المعرّف | `ASIE-CANONICAL-TERMINOLOGY-REGISTER-v1.0.0` |
| الحالة | `CONTROLLED BASELINE` |
| تاريخ النفاذ | `2026-07-25` |
| النطاق | ملفات التشغيل الحية على `main` داخل مساحة العمل canonical |
| المصدر الآلي | `registry/asie-canonical-terminology.v1.json` |
| سلطة العقود والـSockets والـModules | `backend/aas_registry.py` |

## 1. الغرض

يمنع هذا السجل استخدام أكثر من اسم معماري للمفهوم نفسه، مع الفصل بين:

- الاسم المعماري الرسمي `Canonical Name`.
- معرّف Runtime الثابت `Runtime ID`.
- الاسم المعروض داخل Registry أو الواجهة `Display Label`.
- نوع التسجيل التشغيلي `Module Role`.
- الاسم التاريخي المسموح للقراءة فقط `Legacy Alias`.
- الاسم الممنوع في الوثائق الحاكمة `Prohibited Alias`.

وجود كلمة `Module` في اسم التسجيل لا يحوّل المحرك إلى مفهوم معماري جديد. المحرك يحتفظ بملكيته المنطقية، بينما الـModule هو غلاف تشغيله داخل `Module Runtime`.

## 2. قاعدة عدم كسر الإطلاق

لا يعاد تسمية أي `contract_id` أو `socket_id` أو `module_id` حي في مكانه. أي تغيير كاسر يحتاج:

1. عقدًا جديدًا بإصدار رئيسي جديد.
2. بوابة تغيير معتمدة حسب AAS/AIA.
3. اختبارات توافق وترحيل.
4. إبقاء المعرف القديم للقراءة أو التوافق وفق سياسة محددة.

المعرف التالي استثناء تاريخي مجمد:

```text
ProjectRunHttpRequest.v1
```

لا يعتمد كنمط تسمية جديد، ولا يعاد تسميته بصمت. البديل المستقبلي يحتاج عقدًا بإصدار رئيسي جديد.

## 3. الأسماء المعمارية الرسمية

| Concept ID | الاسم الرسمي | الاسم العربي | Runtime Module ID | Runtime Label |
|---|---|---|---|---|
| `FINANCE_ENGINE` | Finance Engine | المحرك المالي | `module.finance` | Finance Module |
| `EVIDENCE_LEDGER` | Evidence Ledger | سجل الأدلة | `module.evidence_ledger` | Evidence Ledger Module |
| `SECTOR_INTELLIGENCE` | Sector Intelligence | ذكاء القطاع | `module.sector_intelligence` | Sector Intelligence Module |
| `DECISION_COUNCIL` | Decision Council | مجلس القرار | `module.decision_council` | Decision Council Module |
| `RISK_ENGINE` | Risk Engine | محرك المخاطر | `module.risk_engine` | Risk Engine Module |
| `EXECUTION_ENGINE` | Execution Engine | محرك التنفيذ | `module.execution_engine` | Execution Engine Module |
| `SNAPSHOT_ASSEMBLY` | Snapshot Assembly | تجميع اللقطة | `module.snapshot_assembly` | Snapshot Assembly Module |
| `AI_INTEGRATION_SHELL` | AI Integration Shell | غلاف تكامل الذكاء الاصطناعي | `module.ai_integration` | AI Integration Shell |
| `DECISION_PACK` | Decision Pack | حزمة القرار | `module.decision_pack` | Decision Pack Module |
| `REPORT_PROJECTION` | Report Projection | إسقاط التقارير | `module.reports` | Report Module |

## 4. العقود الحية

القائمة الكاملة للعقود المسجلة تحفظ آليًا داخل:

```text
registry/asie-canonical-terminology.v1.json
```

ولا تستخدم قائمة مختصرة باسم يوحي بالشمول. عند الحاجة إلى قوائم فرعية يجب تسميتها بدقة، مثل:

- `aas_infrastructure_contracts`.
- `workflow_contracts`.
- `product_command_contracts`.
- `product_result_contracts`.
- `projection_contracts`.
- `disabled_shell_contracts`.
- `planned_contracts`.

## 5. قواعد التسمية

### العقود

```text
<domain>.<operation-or-output>.v<major>
```

ويستخدم lowercase مع الفصل بالنقاط. لا يسمح بإضافة معرف جديد بصيغة PascalCase.

### الـSockets

```text
socket.<domain>.<capability>
```

لا يشترط تطابق اسم الـSocket حرفيًا مع اسم العقد؛ الـSocket يصف القدرة، والعقد يصف الأمر أو المخرج. لكن يجب أن تكون العلاقة مسجلة في `backend/aas_registry.py` وفي السجل الآلي.

### الـModules

```text
aas.<component>
module.<component>
```

المعرّف التقني لا يستبدل الاسم المعماري الرسمي.

## 6. الأسماء الممنوعة

يحظر استخدامها بوصفها أسماء رسمية جديدة في الوثائق الحاكمة أو العقود أو الواجهة:

| المفهوم | أسماء ممنوعة |
|---|---|
| Finance Engine | `Financial Engine`, `Financial Module`, `Finance Service` |
| Decision Council | `Decision Engine`, `AI Decision Engine` |
| Risk Engine | `Risk Module`, `Risk Service` |
| Execution Engine | `Execution Module`, `Execution Service` |
| Snapshot Assembly | `Snapshot Builder` |

`AI Integration Module` اسم تاريخي/تقني مسموح للقراءة، لكن الاسم المعماري الرسمي هو `AI Integration Shell` ما دامت الحالة `DISABLED / DENY_ALL`.

## 7. نطاق الفحص

يفحص CI الملفات الحية ولا يعتبر ما يلي مصدرًا تنفيذيًا:

```text
docs/reference/**
docs/archive/**
```

يمكن فحصها في تقرير Legacy مستقل لاكتشاف التسرب، لكن لا تفشل البناء بسبب الأسماء التاريخية المحفوظة للتتبع.

## 8. بوابة القبول

يعتبر سجل المصطلحات سليمًا فقط إذا تحقق:

```text
Registry contracts == Canonical registered_contract_ids
Registry sockets == Canonical registered_socket_ids
Registry modules == Canonical registered_module_ids
Every socket references an existing contract
Every module references existing sockets
No new PascalCase contract identifiers
Every concept runtime_module_id exists
Every concept contract/socket reference exists
No duplicate concept_id or canonical_name
```

## 9. سلطة التغيير

- تغيير الاسم المعماري فقط: تحديث هذا السجل مع مراجعة الوثائق والواجهة.
- تغيير Label غير كاسر: مراجعة أثره على Runtime Status والاختبارات.
- تغيير Runtime ID أو Contract ID أو Socket ID: تغيير معماري/تعاقدي، ولا ينفذ كتعديل تسمية بسيط.
- تغيير ملفات AAS المجمدة: يتطلب `ACR`.
- تغيير AIA-01: يتطلب `ICCR`.
- تغيير AIA-02: يتطلب `IACR`، و`ACR` إذا أثر على AAS.
