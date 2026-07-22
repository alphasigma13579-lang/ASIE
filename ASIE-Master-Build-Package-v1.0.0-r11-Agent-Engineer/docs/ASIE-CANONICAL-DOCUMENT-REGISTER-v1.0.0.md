# ASIE Canonical Document Register

## سجل الوثائق والعقود الحاكمة

| البند | القيمة |
|---|---|
| الإصدار | `v1.0.0` |
| الحالة | `FINAL / BINDING` |
| تاريخ النفاذ | `2026-07-22` |
| المنطقة الزمنية | `Asia/Riyadh` |
| الغرض | تحديد مصدر الحقيقة الوثائقي ومنع البناء على نسخة قديمة أو مرشحة أو مكررة |

## 1. قاعدة السلطة

لا يُحدد الاعتماد باسم الملف أو تاريخ التعديل وحدهما. ترتيب السلطة هو:

1. الوثيقة النهائية الملزمة ذات رقم وإصدار صريحين.
2. خط الأساس المجمد أو المعتمد وسجل التحكم المرتبط به.
3. الوثيقة الأحدث التي تنص صراحة على استبدال سابقتها.
4. تقرير As-Built الأحدث لوصف حالة التنفيذ فقط.
5. سجلات التنفيذ التاريخية.
6. المسودات والنسخ المرشحة والمراجع المؤرشفة؛ لا توجه البناء.

عند التعارض تتقدم السلطة الأعلى، ولا تجعل حداثة التاريخ وثيقة `DRAFT` أو `CANDIDATE` أعلى من وثيقة `FINAL / BINDING`.

## 2. الخطوط الأساسية المعتمدة

| المجال | الوثيقة المعتمدة | الإصدار/التاريخ | الحالة | ما تستبدله أو تقيده |
|---|---|---|---|---|
| التنفيذ والمعمارية الأساسية | `docs/ASIE-AAS-Runtime-Freeze-Manifest-v1.0.json` مع Release Note | `AAS Runtime Freeze v1.0` — 2026-07-19 | `FROZEN / BINDING` | أي وصف سابق لمسار Runtime؛ تعديل الملفات العشرة يحتاج ACR |
| دستور الذكاء | `docs/AIA-01-Intelligence-Constitution-v1.0.0.md` | `v1.0.0` | `FINAL / BINDING` | أي مسودة أو نسخة مكررة من AIA-01 |
| المعمارية التشغيلية للذكاء | `docs/AIA-02-Intelligence-Operating-Architecture-v1.2.1.md` | `v1.2.1` — معتمد 2026-07-22 | `FINAL / ADOPTED CONTROLLED BASELINE` | يستبدل AIA-02 v1.2.0 بالكامل؛ التفعيل الإنتاجي يبقى مرهونًا بالـIACR/ACRs المحددة |
| وصف النظام المبني | `docs/ASIE-Complete-System-Architecture-2026-07-21.md` | 2026-07-21 | `CURRENT AS-BUILT DESCRIPTION` | يستبدل تقارير الوصف الأقدم عند وصف الكود، ولا يتقدم على AAS/AIA |
| حالة المشروع | `docs/ASIE-Project-Status-Assessment-2026-07-21.md` | 2026-07-21 | `CURRENT STATUS ASSESSMENT` | يستبدل `ASIE-Platform-Readiness-Assessment-2026-07-20.md` لأرقام الحالة والجاهزية |
| خطة الجاهزية | `docs/ASIE-Product-Readiness-Master-Plan-2026-07-19.md` | 2026-07-19 | `ACTIVE MASTER PLAN` | يحل محل ترتيب `PF-02` إلى `PF-07` في Post-Freeze Work Plan؛ يبقى `PF-00` و`PF-01` صالحين |
| خطة ما بعد التجميد | `docs/ASIE-Post-Freeze-Work-Plan-2026-07-19.md` | 2026-07-19 | `PARTIALLY SUPERSEDED` | مرجع لـPF-00/PF-01 وقيود Freeze فقط؛ لا يستخدم لترتيب PF-02..PF-07 |
| تغيير المعمارية | `docs/ASIE-Architectural-Change-Request-Template-v1.0.md` | `v1.0` | `ACTIVE TEMPLATE` | القالب المطلوب لأي أثر على السطح المجمد |

## 3. سجل العقود التنفيذي المعتمد

العقود الفعلية النافذة هي العقود المسجلة في `backend/aas_registry.py` والمحمية باختبارات Runtime وFreeze Manifest. أهم خط التشغيل الحالي:

1. `project.run.workflow.v1`
2. `finance.calculate.v1` → `finance.result.v1`
3. `sector.intelligence.build.v1` → `sector.intelligence.v1`
4. `evidence.ledger.build.v1` → `evidence.ledger.v1`
5. `decision.council.evaluate.v1` → `decision.council.v1`
6. `risk.register.build.v1` → `risk.register.v1`
7. `execution.plan.build.v1` → `execution.plan.v1`
8. `snapshot.assemble.v1`
9. `decision.pack.project.v1` → `decision.pack.v1`
10. `report.snapshot.project.v1` → `report.snapshot.v1`
11. `ai.integration.request.v1` → `ai.integration.result.v1` بحالة `DENY_ALL / NO PROVIDERS`

العقود المذكورة في AIA-02 v1.2.1 بصيغة v2 أو بحالة `DEFINED_NOT_IMPLEMENTED` هي عقود مستهدفة فقط، ولا تصبح نافذة لمجرد اعتماد الوثيقة. خصوصًا:

- `decision.council.evaluate.v2`
- `decision.council.v2`
- `ai.integration.request.v2`
- عقود Consulting/Strategic/Global/National/Market/Reference Cost/Indicator Relationships/Synthesis

لا يجوز استبدال عقد v1 بعقد v2 أو تسجيل Socket/Module جديد قبل بوابة التغيير والاختبارات المحددة في AIA-02.

## 4. سجلات ACR-AIA الحالية

ملفات `docs/ACR-AIA-*.md` الحالية هي سجلات بناء Offline مؤرخة في 2026-07-21، وليست تصريحًا عامًا بالتفعيل الإنتاجي.

وُجد تعارض تسمية تاريخي: ملفان كانا يحملان `ACR-AIA-02`:

- Context / Review / Approval Model.
- Authorization and Audit Boundary.

اعتمد ترقيمهما التصحيحي كمرحلتين تاريخيتين `ACR-AIA-02.1` و`ACR-AIA-02.2` للقراءة فقط. لا يغيّر التصحيح محتواهما ولا يمنحهما سلطة إنتاجية. أي ACR جديد يجب أن يحمل معرفًا فريدًا وسجل مصالحة As-Built واضحًا.

كما أن `ACR-AIA-04 / ACR-AIA-06` يجمع معرفين في ملف واحد؛ يبقى سجلًا تاريخيًا ولا يمثل اعتمادًا مستقلًا لأي منهما.

## 5. وثائق غير معتمدة للتنفيذ

| الوثيقة/الفئة | الحالة | القرار |
|---|---|---|
| `docs/archive/superseded/AIA-02-...v1.2.0-Candidate.md` | `SUPERSEDED` | مرجع تاريخي فقط |
| `docs/reference/**` | `REFERENCE / ARCHIVE` | لا توجه البناء ولا تتقدم على الملفات الحاكمة |
| `ASIE-AAS-Execution-Path-Correction-Pack-v1.0.0/**` | `HISTORICAL CORRECTION EVIDENCE` | يفسر الانتقال؛ Freeze Manifest هو السلطة الحالية |
| `ASIE-Funder-Ready-Report-Decision-and-Work-Plan-2026-07-20.md` | `DRAFT` | غير معتمد كخطة تنفيذ |
| `ASIE-FunderReportProfile-v1-and-FundingReadinessChecklist-v1-2026-07-20.md` | `FR-0 DRAFT` | لا يصبح عقدًا نافذًا قبل Gate صريح |
| Blueprints وUX replans المؤرخة 2026-07-19 | `DESIGN INPUT` | مدخل تصميم؛ لا يغير AAS/AIA ولا سجل العقود |

## 6. قاعدة الوكيل والمهندس

قبل أي بناء أو مراجعة:

1. اقرأ هذا السجل.
2. اقرأ AAS Freeze Manifest وAIA-01 وAIA-02 v1.2.1.
3. افحص Registry الفعلي قبل ادعاء أن عقدًا منفذ.
4. لا تستخدم ملفًا من `archive` أو `reference` كمصدر سلطة.
5. عند تعارض تقرير حالة مع الكود، يصنف التعارض ويصدر As-Built reconciliation؛ لا يعدل التاريخ بصمت.
6. أي تغيير في ملفات Runtime العشرة يحتاج ACR.
7. أي تعديل على AIA-02 المعتمد يحتاج IACR، وأي مساس بـAIA-01 يحتاج ICCR.

## 7. قرار الاعتماد

اعتبارًا من 2026-07-22، تعتمد الوثائق الواردة في القسم 2 فقط وفق نطاق سلطتها. تعتمد `AIA-02 v1.2.1` بدل `v1.2.0` كمرجع معماري تشغيلي، مع الفصل الصريح بين **اعتماد التصميم** و**تفعيل القدرة إنتاجيًا**.

## 8. ملاحظات التحقق من التاريخ

- تواريخ Git في هذا المستودع هي تواريخ رفع الحزمة إلى GitHub في 2026-07-22، وليست بالضرورة تواريخ إنشاء الوثائق الأصلية.
- عند وجود تاريخ داخل اسم الملف أو متن الوثيقة استخدم كتاريخ المحتوى.
- لا تعلن AIA-01 تاريخ نفاذ داخليًا؛ لذلك يعتمد إصدارها وحالتها `FINAL / BINDING` دون اختلاق تاريخ إنشاء.
- AIA-02 v1.2.1 يثبت سجل تصحيحاته بالنسبة إلى v1.2.0، واعتماده الحالي مؤرخ صراحة في 2026-07-22.
