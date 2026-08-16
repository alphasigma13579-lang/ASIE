# Finance Engine

| الحقل | القيمة |
|---|---|
| Domain ID | `EKB-FINANCE-ENGINE-v1.1.0` |
| الحالة | `ACTIVE TRANSITION — v1 AUTHORITATIVE, v2 BUILD AUTHORIZED ONLY` |
| المالك | Finance + Principal Architecture |
| آخر مراجعة | 2026-08-16 |
| المصدر الحاكم | `ACR-FIN-002-v1.0.0` |
| ملحق متطلبات دورة الحياة | [`ACR-FIN-004-v0.1.0 — OWNER-APPROVED REQUIREMENTS / IMPLEMENTATION BLOCKED`](../../ACR-FIN-004-BASELINE-ACTUAL-REFORECAST-FINANCING-AND-DECISION-PROJECTION-LIFECYCLE-2026-08-16.md) |
| خط الأساس | `main@50e7328bc07c828240947536d99d47250f10383b` |
| المراجعة التالية | عند G1 أو عند إغلاق G-FLC-1 أو بعد 90 يوماً |

## الغرض

Finance Engine هو المحرك الحتمي الوحيد للحقيقة المالية داخل مسار AAS. لا يملك UI أو AI أو Market أو الملفات الخام سلطة استدعائه مباشرة أو إعادة حساب نتائجه.

## الحالة الحالية

- `backend/finance_engine.py` هو التنفيذ الحي v1.
- الغلاف الحاكم المجمد: `finance.calculate.v1 → finance.result.v1`.
- النتيجة تُختم ثم تدخل Snapshot immutable، وتقرأ التقارير والإسقاطات منها فقط.
- القوائم المالية الحالية جزئية؛ لا يجوز وصفها كنموذج مالي مهني مكتمل.
- Finance Model v2 مصرح ببنائه داخلياً فقط وفق `docs/ACR-FIN-002-FINANCE-MODEL-V2-AND-PROJECT-ARCHETYPE-CONTRACT-2026-08-09.md`.
- متطلبات `Baseline / Actual / Reforecast` ودلالة التمويل وKPI drill-down مثبتة في [`ACR-FIN-004-v0.1.0`](../../ACR-FIN-004-BASELINE-ACTUAL-REFORECAST-FINANCING-AND-DECISION-PROJECTION-LIFECYCLE-2026-08-16.md).
- وجود ACR-FIN-004 لا يثبت التنفيذ: Actual وReforecast وend-to-end KPI drill-down تظل `BLOCKED/MISSING` حتى العقود والاختبارات والأدلة.

## مصدر الحقيقة

```text
Approved inputs
→ ProjectRunWorkflow
→ Bus / Socket / Module Runtime
→ Finance
→ sealed finance output
→ Snapshot Assembly
→ immutable Snapshot
→ projections and reports
```

أي مسار يتجاوز هذه السلسلة غير مطابق.

## العقود

- `schemas/finance/finance-model-input.v2.schema.json`
- `schemas/finance/project-archetype.v1.schema.json`
- `schemas/finance/finance-result.v2.schema.json`

هذه العقود لا تغيّر الغلاف المجمد بذاتها. v2 يصبح authoritative فقط عبر بوابات ACR-FIN-002.

## ثوابت Finance v2 الحالية

- `UNKNOWN ≠ 0`.
- Decimal + rounding policy للحقيقة المالية.
- نفس المدخلات والإصدارات والـseed تعطي نتيجة حتمية.
- Assets = Liabilities + Equity لكل فترة.
- Cash Flow ending cash = Balance Sheet cash.
- debt/PPE/retained earnings roll-forwards متطابقة.
- لا readiness عند فشل invariant.
- historical Snapshot لا يعاد حسابه.
- legacy projection مشتق من v2 ولا يملك حساباً موازياً.

## ثوابت دورة الحياة المعتمدة كمتطلبات

- الدين اختياري؛ غيابه لا يفشل النموذج.
- عند غياب خدمة الدين يكون DSCR وLLCR `NOT_APPLICABLE` بسبب `NO_DEBT_SERVICE`، لا صفراً ولا `ready`.
- التمويل الواحد يبقى كما صرح به المستخدم؛ لا ممول أو provenance مستنتج.
- التمويلات المتعددة لا تنشأ إلا من تصريح معتمد، وتبقى كل شريحة قابلة للتتبع والـdrill-down.
- drawdown مؤرخ ومعلوم عند Baseline جزء منه؛ التمويل الجديد بعد اعتماد Baseline يدخل عبر Reforecast جديد.
- Baseline وActual وReforecast artifacts مستقلة؛ لا overwrite أو إعادة حساب تاريخي.
- KPI يتبع `Summary → Drill-down → Comparison → Snapshot-backed Report` من الحقيقة المختومة نفسها.
- دراسة الجدوى والجاهزية التمويلية وجاهزية ملفات الحاضنات/المسرعات مسارات منتج أساسية، والمتابعة امتداد قرار.
- ASIE ليست ERP ولا تصبح مصدر حقيقة للـGL أو payroll أو inventory أو procurement أو المعاملات اليومية.
- هذه الثوابت متطلبات غير منفذة بالكامل؛ حالات القبول `FLC-F1..F12` في ACR-FIN-004 هي مرجع الترقية.

## الحدود

- لا قاعدة ضريبية/زكوية عامة غير مرتبطة بسياسة معتمدة وتاريخ سريان.
- لا AI داخل الحساب أو اختيار السياسة.
- لا network/provider/key.
- لا تغيير ملفات Freeze في S2.
- لا claim L1 قبل G1 ومراجعة Finance Reviewer/CPA.
- لا claim قبول مصرفي أو حاضنة/مسرعة قبل بوابات الجهة والبرنامج والـPilot.
- لا تحويل نطاق المتابعة إلى ERP.
- لا claim Actual/Reforecast/drill-down قبل evidence exact-commit.

## الاختبارات الحاكمة

- `T-FIN`: وحدات، قوائم، ديون، CAPEX، WC، fiscal، سيناريوات، توافق، Snapshot وأمن.
- `T-PROP`: المطابقات والحتمية والخواص الرياضية والحدود.
- `FLC-F1..F12`: no-debt applicability، تمويل واحد/متعدد، drawdown متأخر، تمويل جديد، Actual/Reforecast، KPI chain، حدود ERP، profiles، tenant/tamper.
- `tests/test_feasibility_s1_finance_contracts.py`: يمنع انجراف عقد S1.
- `tests/test_runtime_freeze.py`: يمنع تغيير الحدود المجمدة.

## دورة الحياة التنفيذية

1. M0 عقود فقط.
2. M1 dark build؛ v1 authoritative.
3. M2 shadow في tests/CI بلا Snapshot.
4. M3 opt-in خادمي مع Snapshot جديد.
5. M4 v2 default بعد G1.
6. M5 ترقية الغلاف عبر ACR مستقل.

دورة المنتج المستهدفة داخل هذه البوابات:

```text
Approved BASELINE inputs
→ server-owned Approved Input Manifest
→ BASELINE Run
→ immutable BASELINE Snapshot
→ ACTUAL submissions/revisions
→ REFORECAST Draft
→ new server-owned Approved Input Manifest
→ approved REFORECAST Run
→ immutable REFORECAST Snapshot
→ comparison / drill-down / report projections
```

## روابط التتبع

- البرنامج: `ASIE-FEASIBILITY-COMPLETE-01-v1.0.0`.
- قرار Finance v2: `ACR-FIN-002-v1.0.0`.
- عقد دورة الحياة: `ACR-FIN-004-v0.1.0`.
- المتطلبات القائمة: `FR-FIN-001..013` و`FR-ARC-001/002`.
- متطلبات دورة الحياة: أقسام 3–10 من ACR-FIN-004.
- الاختبارات القائمة: `T-FIN` و`T-PROP`.
- اختبارات دورة الحياة المطلوبة: `FLC-F1..F12`.
- البوابات: G0/G1 و`G-FLC-0..3`؛ ولا تعني أي منها تفويض إطلاق.
