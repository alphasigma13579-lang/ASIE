# ASIE Canonical API & Output Register

## سجل مسارات API ومفاتيح المخرجات المعتمدة

| البند | القيمة |
|---|---|
| المعرّف | `ASIE-CANONICAL-API-OUTPUT-REGISTER-v1.0.0` |
| الحالة | `CONTROLLED BASELINE` |
| تاريخ النفاذ | `2026-07-25` — `Asia/Riyadh` |
| النطاق | API الحي، ربط TypeScript، مفاتيح Snapshot المختومة، وحقول Projection العامة |
| سلطة API | `backend/asie_local_api.py` |
| سلطة عميل الواجهة | `src/api.ts` |
| سلطة مخرجات Snapshot | `backend/snapshot_assembly.py` |
| السجل الآلي | `registry/asie-canonical-api-output.v1.json` |
| اختبار CI | `tests/test_canonical_api_output.py` |

## 1. القرار التنفيذي

لا يعاد تسمية أي مسار API أو مفتاح Snapshot مختوم أو حقل Projection عام قائم أثناء مرحلة الإطلاق. أي تغيير كاسر يحتاج إصدارًا جديدًا وخطة ترحيل واختبارات توافق.

التمييز المعتمد هو:

- **Sealed Output Key:** مفتاح داخلي يحدد مخرج الوحدة داخل `Snapshot Assembly`.
- **Module Payload Key:** المفتاح داخل مخرج الوحدة المختوم.
- **Public Projection Key:** الاسم العام الذي تقرؤه API وTypeScript والتقارير والواجهة.
- **Display Label:** النص الظاهر للمستخدم، ولا يستخدم بوصفه معرفًا برمجيًا.

## 2. خريطة المخرجات المختومة إلى الحقول العامة

| Sealed Output Key | Module | Result Contract | Module Payload | Public Projection |
|---|---|---|---|---|
| `finance_result` | `module.finance` | `finance.result.v1` | `finance`, `blockers` | `finance`, `blockers`, `monte_carlo`, `kpis` |
| `evidence_ledger` | `module.evidence_ledger` | `evidence.ledger.v1` | `evidence_ledger` | `evidence_ledger` |
| `sector_intelligence` | `module.sector_intelligence` | `sector.intelligence.v1` | `sector_intelligence` | `sector_intelligence` |
| `decision_result` | `module.decision_council` | `decision.council.v1` | `decision_council` | `decision_council`, `decision`, `personas` |
| `risk_result` | `module.risk_engine` | `risk.register.v1` | `risk_register`, `risk_advisory_summary` | `risk_register`, `risk_advisory_summary` |
| `execution_result` | `module.execution_engine` | `execution.plan.v1` | `execution_plan` | `execution_plan` |

وبذلك فإن:

- `decision_result` ليس اسمًا بديلًا عن `decision_council`؛ الأول مفتاح تجميع داخلي والثاني مخرج المجال العام.
- `risk_result` ليس اسمًا بديلًا عن `risk_register`؛ الأول وعاء Snapshot داخلي، بينما المخرج يحتوي `risk_register` و`risk_advisory_summary`.
- `execution_result` مفتاح داخلي، و`execution_plan` هو المخرج العام.

## 3. مسارات API

السجل الآلي يحتوي جميع الدوال المصدّرة من `src/api.ts` ويربط كل دالة بـ:

- HTTP Method.
- Path Template.
- دليل وجود داخل Handler الخلفي.
- Response Contract أو Response Shape.

يفشل CI عندما يحدث أحد الآتي:

1. إضافة دالة API أمامية دون تسجيلها.
2. بقاء دالة مسجلة بعد حذفها.
3. تسجيل مسار دون دليل داخل Handler الخاص بالطريقة نفسها.
4. اختلاف طريقة HTTP بين الواجهة والسجل.
5. اختلاف أجزاء المسار الثابتة بين الدالة والسجل.
6. تكرار `route_id` أو تكرار هوية `method + path`.

## 4. تصحيح TypeScript العام

ثبت التدقيق أن Backend يصدر الحقول التالية فعلًا:

- `ProjectOverview.risk_advisory_summary`.
- `SnapshotReport.risk_advisory_summary`.
- `SnapshotReport.funder_report`.
- `SnapshotReportView.risk_advisory_summary`.
- `SnapshotReportView.funder_report`.

كانت هذه الحقول غير ممثلة بالكامل في سطح TypeScript. أضيفت بصورة غير كاسرة عبر:

```text
src/contracts.canonical.d.ts
```

ولا يغير ذلك JSON أو Runtime أو العقود المجمدة؛ بل يجعل TypeScript يصف المخرجات الموجودة فعليًا.

## 5. المسميات الظاهرة

يفحص التدقيق الأسطح النشطة الأساسية للتأكد من عدم استخدام الأسماء الممنوعة، مع بقاء Runtime Labels التقنية كما هي. الأسماء المعمارية العامة المعتمدة تظل:

- `Finance Engine` — المحرك المالي.
- `Decision Council` — مجلس القرار.
- `Risk Engine` — محرك المخاطر.
- `Execution Engine` — محرك التنفيذ.
- `AI Integration Shell` — غلاف تكامل الذكاء الاصطناعي.
- `Snapshot Assembly` — تجميع اللقطة.

## 6. حدود السلطة

هذا السجل لا:

- يغير AAS Runtime Freeze.
- يعيد تسمية Contract أو Socket أو Module ID.
- يغير ترتيب المحركات.
- يغير Snapshot hashes السابقة.
- يفعّل AI أو الشبكة الخارجية.
- يحول وثائق `docs/reference/**` إلى مصدر تنفيذ.

## 7. بوابة الإغلاق

يعد تدقيق API والمخرجات مغلقًا عندما تكون النتيجة:

```text
Frontend API Function Inventory = MATCH
Backend Method/Path Evidence = MATCH
Sealed Output Mapping = MATCH
Public Projection Mapping = MATCH
TypeScript Public Fields = MATCH
Active Surface Labels = MATCH
Frontend Build = PASS
Backend Compile = PASS
Python Tests = PASS
```
