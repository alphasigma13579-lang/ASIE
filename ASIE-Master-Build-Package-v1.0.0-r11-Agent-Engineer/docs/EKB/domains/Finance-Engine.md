# Finance Engine

| الحقل | القيمة |
|---|---|
| Domain ID | `EKB-FINANCE-ENGINE-v1.0.0` |
| الحالة | `ACTIVE TRANSITION — v1 AUTHORITATIVE, v2 BUILD AUTHORIZED ONLY` |
| المالك | Finance + Principal Architecture |
| آخر مراجعة | 2026-08-09 |
| المصدر الحاكم | `ACR-FIN-002-v1.0.0` |
| خط الأساس | `main@f4d38bb28c950c0ebae0e465ad7d2d4534f6c081` |
| المراجعة التالية | عند G1 أو بعد 90 يوماً |

## الغرض

Finance Engine هو المحرك الحتمي الوحيد للحقيقة المالية داخل مسار AAS. لا يملك UI أو AI أو Market أو الملفات الخام سلطة استدعائه مباشرة أو إعادة حساب نتائجه.

## الحالة الحالية

- `backend/finance_engine.py` هو التنفيذ الحي v1.
- الغلاف الحاكم المجمد: `finance.calculate.v1 → finance.result.v1`.
- النتيجة تُختم ثم تدخل Snapshot immutable، وتقرأ التقارير والإسقاطات منها فقط.
- القوائم المالية الحالية جزئية؛ لا يجوز وصفها كنموذج مالي مهني مكتمل.
- Finance Model v2 مصرح ببنائه داخلياً فقط وفق `docs/ACR-FIN-002-FINANCE-MODEL-V2-AND-PROJECT-ARCHETYPE-CONTRACT-2026-08-09.md`.

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

## الثوابت

- `UNKNOWN ≠ 0`.
- Decimal + rounding policy للحقيقة المالية.
- نفس المدخلات والإصدارات والـseed تعطي نتيجة حتمية.
- Assets = Liabilities + Equity لكل فترة.
- Cash Flow ending cash = Balance Sheet cash.
- debt/PPE/retained earnings roll-forwards متطابقة.
- لا readiness عند فشل invariant.
- historical Snapshot لا يعاد حسابه.
- legacy projection مشتق من v2 ولا يملك حساباً موازياً.

## الحدود

- لا قاعدة ضريبية/زكوية عامة غير مرتبطة بسياسة معتمدة وتاريخ سريان.
- لا AI داخل الحساب أو اختيار السياسة.
- لا network/provider/key.
- لا تغيير ملفات Freeze في S2.
- لا claim L1 قبل G1 ومراجعة Finance Reviewer/CPA.
- لا claim قبول مصرفي قبل بوابات الجهة والمنتج والـPilot.

## الاختبارات الحاكمة

- `T-FIN`: وحدات، قوائم، ديون، CAPEX، WC، fiscal، سيناريوات، توافق، Snapshot وأمن.
- `T-PROP`: المطابقات والحتمية والخواص الرياضية والحدود.
- `tests/test_feasibility_s1_finance_contracts.py`: يمنع انجراف عقد S1.
- `tests/test_runtime_freeze.py`: يمنع تغيير الحدود المجمدة.

## دورة الحياة

1. M0 عقود فقط.
2. M1 dark build؛ v1 authoritative.
3. M2 shadow في tests/CI بلا Snapshot.
4. M3 opt-in خادمي مع Snapshot جديد.
5. M4 v2 default بعد G1.
6. M5 ترقية الغلاف عبر ACR مستقل.

## روابط التتبع

- البرنامج: `ASIE-FEASIBILITY-COMPLETE-01-v1.0.0`.
- القرار: `ACR-FIN-002-v1.0.0`.
- المتطلبات: `FR-FIN-001..013` و`FR-ARC-001/002`.
- الاختبارات: `T-FIN` و`T-PROP`.
- البوابات: G0 ثم G1؛ ولا تعني أي منهما تفويض إطلاق.
