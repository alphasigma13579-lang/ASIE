# ACR-FIN-002 — Finance Model v2 and Project Archetype Contract

| الحقل | القيمة |
|---|---|
| Document ID | `ACR-FIN-002-v1.0.0` |
| الحالة | `ACCEPTED FOR S2 INTERNAL IMPLEMENTATION` |
| المالك | Product Owner + Principal Architecture |
| المراجعون المطلوبون قبل G1 | Finance Reviewer/CPA + QA + Security |
| آخر مراجعة | 2026-08-09 |
| خط الأساس | `main@f4d38bb28c950c0ebae0e465ad7d2d4534f6c081` |
| البرنامج الأب | `ASIE-FEASIBILITY-COMPLETE-01-v1.0.0` |
| مستوى التفويض | بناء واختبار محلي/CI فقط؛ لا شبكة ولا مزود ولا Production |
| قرار G0 | `PASS — BUILD READY FOR S2 WITHIN THIS ACR` |

> هذا القرار يسمح ببناء محرك مالي v2 داخلي وحتمي خلف الغلاف المجمد الحالي، ولا يسمح بتعديل AAS Runtime أو Snapshot Assembly أو السجل المجمد، ولا يثبت صحة مهنية أو قبولاً مصرفياً. الترقية إلى L1 محجوبة حتى G1 ومراجعة مالية مستقلة.

## 1. السياق والحكم الحالي

### FACT

- `backend/finance_engine.py@112e7487dae0a9acb4978ae268b23cfecfb4f608` يستخدم أربعة مدخلات أساسية ونموذج إيراد وحدي وتدفقاً سنوياً ثابتاً لخمس سنوات وسيناريوهات ثابتة.
- `backend/funder_report.py@62b0ab02940ffc0eb7be54aabb25f4a7d1cef0ab` يبني قائمة دخل وتدفقاً جزئيين ويُبقي الميزانية `not_ready`.
- `backend/module_runtime.py` و`backend/aas_registry.py` و`backend/snapshot_assembly.py` ضمن حدود Freeze.
- Finance يدخل فقط عبر `ProjectRunWorkflow → Bus → Socket → module.finance` وفق `ACR-DIB-001-CORR-01`.
- مستهلكو v1 يعتمدون حقولاً بعينها: `baseline` و`scenarios` و`sensitivity` و`operating_model` و`capex_breakdown` و`opex_breakdown` و`debt_service_profile` و`monte_carlo`.
- لا يوجد حالياً JSON Schema حاكم للنموذج المالي أو واجهة archetype في المستودع.

### UNKNOWN

- المراجع المالي/المحاسبي المسمّى للحالات الذهبية لم يُثبت بعد.
- سياسات الزكاة والضريبة وضريبة القيمة المضافة تختلف باختلاف الكيان والفترة، ولا يجوز تثبيتها كقواعد سعودية عامة داخل المحرك.
- جودة ومعايرة توزيعات Monte Carlo لكل عائلة مشروع لم تُثبت بعد.

### DECISION

نبني `Finance Model v2` كحزمة داخلية حتمية ضمن modular monolith، مع عقود إصدار صريحة ودقة Decimal وقوائم مالية مترابطة. يبقى الغلاف المجمد `finance.calculate.v1 → finance.result.v1` دون تغيير في S2، ويحتوي نتيجة v2 إضافية مع إسقاط توافق v1 مشتق ومؤقت. لا يُسمح بأن يكون الإسقاط القديم مصدر حقيقة جديداً.

## 2. محركات القرار

1. صحة مالية قابلة للمطابقة والتدقيق.
2. دعم نماذج مشاريع متعددة دون منطق قطاعي متشعب داخل المحرك.
3. الحفاظ على AAS Freeze وSnapshot immutability.
4. منع تغيير صامت لعقود المستهلكين الحاليين.
5. قابلية إعادة الحساب الحتمي على exact input/version/seed.
6. فصل الحساب المالي عن شروط الممول والادعاءات التنظيمية.
7. fail-closed عند نقص مدخل جوهري؛ `UNKNOWN ≠ 0`.

## 3. البدائل

| البديل | الحكم | السبب |
|---|---|---|
| A. استبدال `finance.result.v1` مباشرة | مرفوض | يكسر مستهلكين متعددين ويستلزم تغيير ملفات مجمدة |
| B. v2 داخلي خلف الغلاف v1 مع إسقاط توافق مؤقت | **مختار** | أقل تغيير آمن، قابل للاختبار والتراجع ولا يمس Freeze |
| C. Microservice مالي جديد | مرفوض الآن | يضيف شبكة وتشغيلاً موزعاً دون حاجة ويضعف الحتمية |
| D. توسيع الدوال الحالية فقط | مرفوض | يزيد الاقتران ويُبقي غياب العقود والقوائم المترابطة |
| E. محركان مستقلان دائمان v1/v2 | مرفوض | حقيقتان ماليتان دائمتان وانجراف غير قابل للضبط |

## 4. الحدود والتدفق المسموح

```text
Persisted DIB / approved Project inputs
→ Server-owned Approved Input Manifest
→ Canonical ProjectRunWorkflow
→ frozen finance.calculate.v1 envelope
→ FinanceModuleAdapter (unchanged)
→ finance_engine.finance_result_set (compatibility entrypoint)
→ finance_v2 input admission and schema validation
→ archetype driver projection
→ deterministic monthly timeline
→ revenue / OPEX / CAPEX / WC / fiscal / debt subledgers
→ three-statement assembly
→ metrics / scenarios / calibrated simulation
→ invariant gate
→ finance_model_v2 result
→ derived legacy_projection
→ frozen finance.result.v1 envelope
→ sealed output
→ immutable Snapshot
→ read-only projections
```

### قاعدة السلطة

- UI وAI والملفات الخام لا تنادي Finance مباشرة.
- لا يقبل المحرك Manifest أو tenant أو run IDs من العميل.
- الهوية وسلسلة الاعتماد تأتي من الغلاف الخادمي ومسار ProjectRun.
- كل تشغيل authoritative يختار إصدار نموذج واحداً فقط.
- تشغيل shadow في الاختبارات لا يُختم ولا يدخل Snapshot.
- Snapshot تاريخي لا يعاد حسابه أو تعديله.

## 5. العقود

العقود التنفيذية المرتبطة بهذا القرار:

- `schemas/finance/finance-model-input.v2.schema.json`
- `schemas/finance/project-archetype.v1.schema.json`
- `schemas/finance/finance-result.v2.schema.json`

### سياسة الأرقام والوقت

- القيم المالية والنسب في عقود v2 تُنقل كسلاسل Decimal وفق pattern صريح.
- الحساب الداخلي يستخدم Decimal وسياسة rounding موثقة؛ لا binary float للحقيقة المالية.
- أساس التوقع شهري، والفترة `YYYY-MM`، والتواريخ ISO-8601.
- العملة ISO-4217، وعملة تشغيل واحدة في S2. العملات المتعددة `not_supported` حتى ACR لاحق.
- كل نتيجة تحمل `schema_version` و`engine_version` و`archetype_version` و`rounding_policy` و`input_hash`.
- seed مطلوب لأي محاكاة؛ نفس المدخلات والإصدارات والـseed تعطي نفس البايتات المنطقية بعد canonical serialization.

### null/default

- الغياب الجوهري ينتج blocker ولا يتحول إلى صفر.
- الصفر صالح فقط إذا ورد صراحة واجتاز سياسة الحقل.
- defaults المسموحة تقنية فقط، مثل rounding mode؛ لا defaults تجارية أو ضريبية صامتة.
- القيم المشتقة تحمل formula ID ومراجع المدخلات.

## 6. نموذج البيانات المالي المستهدف

### 6.1 خط الزمن

- 12–240 فترة شهرية.
- فترة إنشاء/تشغيل قابلة للتمييز.
- بداية ونهاية واضحة، ولا extrapolation بعد الأفق.
- كل schedule يجب أن يقع داخل الأفق أو يفشل التحقق.

### 6.2 الإيراد

كل revenue stream يعلن `model_kind` وdriver series وprice/volume أو معادلة archetype مصرح بها. الأنواع الابتدائية:

- `product_unit`
- `service_capacity`
- `subscription`
- `project_contract`
- `commission_gmv`
- `room_bed_seat`
- `rent_lease`
- `agriculture_cycle`
- `manufacturing_yield`
- `transport_trip`
- `professional_hours`
- `custom_reviewed`

لا تُنفذ صيغة نصية أو expression واردة من المستخدم. archetype code/registry يحدد الصيغ المسموحة.

### 6.3 OPEX وCAPEX

- OPEX line items: ثابت، متغير، step، موسمي؛ كل بند له schedule وassumption/evidence refs.
- CAPEX asset groups: تكلفة، تاريخ اقتناء، عمر نافع، residual value، طريقة إهلاك، replacement policy.
- S2 يدعم straight-line فقط ويعلن غيره `not_supported`.
- سجل الأصول يطابق PPE roll-forward: opening + additions - disposals - depreciation = closing.

### 6.4 رأس المال العامل

- AR/AP/Inventory مبني على DSO/DPO/DIO أو schedules صريحة.
- `ΔNWC` يدخل التدفق النقدي ولا يُحسب كمصروف دخل.
- القيم السالبة تحتاج سياسة archetype ومراجعة؛ لا تُقبل افتراضياً.

### 6.5 التمويل

- مصادر واستخدامات متوازنة.
- شرائح دين متعددة، drawdowns، fees، annual rate، tenor، grace، amortization وballoon.
- grace يطبق فعلياً على principal/interest وفق policy، لا يُعرض فقط.
- جدول الدين يطابق: opening + drawdowns + capitalized interest - principal = closing.
- DSCR وLLCR لا يظهران ready ما لم يكتمل تعريف CFADS وجدول الدين.

### 6.6 السياسات المالية/الضريبية

- المحرك generic policy-driven.
- `vat` و`income_tax` و`zakat` وحدات مستقلة ذات effective dates ومصدر/مراجع.
- لا يزعم المحرك اختيار السياسة النظامية الصحيحة؛ الاختيار مدخل معتمد.
- إذا كان مستوى المخرج يتطلب سياسة ناقصة تكون النتيجة `not_ready`.

### 6.7 القوائم والتدفقات

لكل فترة:

- Income Statement: revenue, COGS, gross profit, OPEX, EBITDA, depreciation, EBIT, finance cost, tax/zakat, net income.
- Balance Sheet: cash, AR, inventory, other current assets, PPE net, liabilities, debt, equity, retained earnings.
- Cash Flow: CFO, CFI, CFF، opening/ending cash.
- Unlevered FCF وEquity cash flow منفصلان.
- metrics: NPV, IRR, MIRR, payback, break-even, DSCR, LLCR، margins، funding need.

## 7. الثوابت المحاسبية والحسابية

يُحجب `status=ready` عند فشل أي invariant مطلوب:

1. `Assets = Liabilities + Equity` لكل فترة ضمن tolerance المحدد.
2. ending cash في Cash Flow = cash في Balance Sheet.
3. opening cash(t) = ending cash(t-1).
4. retained earnings(t) = retained earnings(t-1) + net income - distributions.
5. PPE roll-forward مطابق لسجل الأصول.
6. debt roll-forward مطابق لجداول الشرائح.
7. sources = uses عند الإقفال الأولي.
8. gross profit = revenue - COGS.
9. EBIT = EBITDA - depreciation/amortization.
10. ending cash = opening cash + CFO + CFI + CFF.
11. لا NaN/Infinity ولا قسمة صامتة على صفر.
12. لا period مكرر أو خارج الترتيب.
13. legacy projection مشتق بالكامل من v2 ولا يعيد الحساب.
14. إعادة التنفيذ بنفس المدخلات والإصدارات والseed حتمية.

## 8. واجهة Project Archetype

archetype لا يحسب الحقيقة ولا يخزن أرقام مشروع. هو عقد versioned يحدد:

- family وISIC bindings.
- revenue model kinds والdrivers المطلوبة/الاختيارية.
- technical units وcapacity constraints.
- required schedules والسياسات.
- evidence minimums.
- applicable validation rules.
- golden-case refs وreview status.

العائلات الإلزامية قبل ادعاء تغطية واسعة:

1. تجارة/تجزئة.
2. تصنيع.
3. مطاعم وضيافة.
4. خدمات مهنية.
5. SaaS/اشتراكات.
6. سوق/عمولة.
7. عقار/إيجار.
8. نقل/لوجستيات.
9. صحة/تعليم قائم على السعة.
10. زراعة/دورات إنتاج.
11. مشاريع مقاولات/عقود.

وجود interface لا يعني اعتماد العائلة. كل عائلة تبقى `draft` حتى golden cases ومراجع تخصصي.

## 9. خريطة الأثر

### ملفات إنتاجية متوقعة في S2، غير موجودة بعد

- `backend/finance_v2/__init__.py`
- `backend/finance_v2/contracts.py`
- `backend/finance_v2/timeline.py`
- `backend/finance_v2/revenue.py`
- `backend/finance_v2/opex.py`
- `backend/finance_v2/capex.py`
- `backend/finance_v2/working_capital.py`
- `backend/finance_v2/fiscal.py`
- `backend/finance_v2/debt.py`
- `backend/finance_v2/statements.py`
- `backend/finance_v2/metrics.py`
- `backend/finance_v2/scenarios.py`
- `backend/finance_v2/invariants.py`
- `backend/finance_v2/serialization.py`
- `backend/finance_engine.py` كـcompatibility entrypoint فقط.

### مستهلكون يلزمهم regression coverage قبل أي تفعيل

- `backend/decision_council.py`
- `backend/risk_engine.py`
- `backend/readiness_gates.py`
- `backend/funder_report.py`
- `backend/funding_readiness.py`
- `backend/execution_engine.py`
- `backend/reports.py`
- `backend/decision_pack.py`
- `src/contracts.ts`

### ملفات مجمدة محظور تعديلها في S2

- `backend/aas_kernel.py`
- `backend/aas_registry.py`
- `backend/heart_controller.py`
- `backend/bus_controller.py`
- `backend/system_bus.py`
- `backend/socket_contracts.py`
- `backend/module_runtime.py`
- `backend/project_run_workflow.py`
- `backend/snapshot_assembly.py`
- `backend/runtime_freeze.py`

إذا تعذر التنفيذ دون تغيير أي ملف أعلاه: Stop-the-Line وACR جديد؛ لا توسيع لهذا القرار ضمنياً.

## 10. التوافق والإيقاف التدريجي

### envelope

يبقى الغلاف الخارجي v1 في S2. النتيجة الداخلية تضيف:

- `finance_model_v2`: الحقيقة الجديدة عند اختيار v2.
- `model_selection`: الإصدار والسبب والـpolicy ref.
- حقول v1 الحالية: إسقاط read-only مشتق من v2 أو نتيجة v1 الأصلية.

### قواعد الإسقاط

- يحافظ على أسماء وأنواع الحقول الحالية للمستهلكين.
- يصرح `legacy_projection_status` و`derived_from`.
- لا يخفي blocker من v2؛ status الخارجي لا يصبح ready إذا فشل v2.
- لا يحول Decimal ناقصاً إلى صفر.
- يجب أن يمر parity test لكل حقل legacy.
- sunset لا يبدأ قبل انتقال كل المستهلكين واختبارات Snapshot/report parity وACR منفصل لترقية الغلاف.

## 11. استراتيجية الهجرة

### Phase M0 — contracts only

هذه الحزمة: ACR + schemas + static contract tests. لا إنتاج.

### Phase M1 — engine dark build

- إضافة `finance_v2` واختبارات unit/property/golden.
- لا ربط بمسار ProjectRun.
- v1 يظل المصدر الوحيد.

### Phase M2 — canonical offline shadow

- نفس approved input fixture يشغل v1 وv2 في الاختبارات/CI فقط.
- مقارنة معلنة؛ لا ختم shadow ولا Snapshot ولا كتابة مشروع.
- الاختلاف المتوقع موثق، والاختلاف غير المتوقع blocker.

### Phase M3 — opt-in authoritative

- اختيار v2 بسياسة خادمية versioned مرتبطة بعقد Approved Manifest؛ لا flag من العميل.
- تشغيل authoritative واحد ينتج Snapshot جديداً.
- v1 legacy projection مشتق من v2.
- historical snapshots لا تتغير.

### Phase M4 — default v2

لا يتم قبل G1 واختبارات كل المستهلكين وgolden cases ومراجعة CPA.

### Phase M5 — envelope promotion

ترقية `finance.calculate/result` إلى v2 تحتاج ACR/Freeze change مستقل، ولا تدخل هذا القرار.

### قاعدة البيانات

S2 لا يهاجر جداول قائمة. إذا احتاجت DIB/archetype persistence تغييراً تخطيطياً، تُنشأ migration forward-only مستقلة مع expand/contract ونسخة احتياطية واختبار restore. لا backfill للـSnapshots.

## 12. التراجع والاستعادة

| المرحلة | trigger | إجراء التراجع | سلامة البيانات | تحقق ما بعد التراجع |
|---|---|---|---|---|
| M1 | فشل اختبارات v2 | إزالة الربط/الحزمة في PR عكسي | لا بيانات إنتاجية | v1 suite + freeze |
| M2 | parity غير مفسر | تعطيل shadow | لا Snapshot للshadow | exact fixture v1 |
| M3 | invariant/consumer regression | policy خادمية تعيد التشغيلات الجديدة إلى v1 | Snapshots v2 تبقى immutable/readable | run جديد v1، القديم دون تعديل |
| M4 | فشل واسع | rollback للإصدار والسياسة؛ لا rewrite تاريخي | preserve v2 artifacts | restore rehearsal + parity |
| M5 | غير داخل النطاق | ACR ترقية مستقل | حسبه | حسبه |

ممنوع:

- حذف أو تعديل Snapshot v2 لإخفاء خطأ.
- force-convert نتائج v2 إلى v1.
- تغيير schema version دون migrator/reader.
- التراجع عبر تعديل الملفات المجمدة بلا ACR.

## 13. نموذج التهديد والفشل

| الخطر | السيناريو | الضابط | الاختبار |
|---|---|---|---|
| كسر tenant | document له organization آخر | identity binding server-side | T-FIN-SEC-01 |
| client model selection | العميل يرسل v2/seed/manifest مزوراً | server-owned policy + manifest | T-FIN-SEC-02 |
| formula injection | expression نصي في archetype/input | enum/registry only | T-FIN-SEC-03 |
| resource exhaustion | 240 شهراً × آلاف streams/simulations | حدود schema وquota وbounded iterations | T-FIN-NFR-01 |
| silent zero | حقل مفقود يتحول صفر | blockers + null policy | T-PROP-NULL-01 |
| nondeterminism | ترتيب map أو float أو seed غائب | Decimal + canonical order + seed | T-PROP-DET-01 |
| contract drift | مستهلك v1 ينهار | legacy projection contract tests | T-FIN-COMPAT |
| false readiness | statements غير متطابقة لكن status ready | invariant gate fail-closed | T-FIN-INV |
| fiscal misclaim | policy افتراضية خاطئة | approved policy ref/effective date | T-FIN-FISCAL |
| snapshot rewrite | إعادة حساب تاريخي | new run/new snapshot only | T-FIN-SNAP |

لا AI في الحساب أو اختيار القواعد. يمكنه اقتراح assumption في مسار منفصل، ولا يدخل Finance قبل الموافقة.

## 14. مواصفة الاختبار الملزمة

### T-FIN — أمثلة وحالات ذهبية

- `T-FIN-INPUT-*`: schema positive/negative، حدود المدد، Decimal، periods، refs.
- `T-FIN-REV-*`: كل revenue model kind، zero volume، seasonality، capacity.
- `T-FIN-OPEX-*`: fixed/variable/step/seasonal.
- `T-FIN-CAPEX-*`: acquisition، depreciation، replacement، residual، disposal.
- `T-FIN-WC-*`: DSO/DPO/DIO، ΔNWC، negative-policy.
- `T-FIN-DEBT-*`: multi-tranche، fees، grace، balloon، zero rate، invalid tenor.
- `T-FIN-FISCAL-*`: modules enabled/disabled، effective dates، missing policy blocker.
- `T-FIN-STMT-*`: الثلاث قوائم وroll-forwards.
- `T-FIN-METRIC-*`: NPV/IRR/MIRR/payback/DSCR/LLCR.
- `T-FIN-SCEN-*`: baseline/scenario overrides بلا mutation.
- `T-FIN-MC-*`: seed، bounds، correlation PSD validation، calibrated profile ref.
- `T-FIN-COMPAT-*`: كل حقل v1 مستخدم في المستهلكين الحاليين.
- `T-FIN-SNAP-*`: one run/one immutable snapshot/report parity.
- `T-FIN-SEC-*`: tenant، forged manifest/model selection، formula injection.
- `T-FIN-ARC-01..11`: حالة ذهبية لكل عائلة قبل اعتمادها.

قواعد golden vector:

- input JSON مثبت hash.
- expected statements/metrics مثبتة مع tolerance وrounding policy.
- الحساب المرجعي واسم المراجع وتاريخ المراجعة.
- status `draft` حتى توقيع Finance Reviewer/CPA.
- CI لا يساوي توقيعاً مهنياً.

### T-PROP — خصائص

1. كل invariant في القسم 7 عبر توليد bounded valid inputs.
2. deterministic replay.
3. canonical ordering لا يغير النتيجة.
4. زيادة discount rate لا ترفع NPV لتدفقات تحقق شروط الاختبار.
5. NPV عند معدل IRR يقارب الصفر للحالات ذات IRR وحيد.
6. زيادة CAPEX وحدها لا تحسن unlevered NPV.
7. زيادة DSO وحدها لا تحسن cash balance خلال الأفق.
8. principal payments لا تدخل Income Statement كمصروف.
9. depreciation لا تغير cash مباشرة.
10. missing required ليس صفراً.
11. scenario evaluation لا يعدل baseline input.
12. projection v1 لا يخالف v2 ولا يعيد الحساب.
13. fuzz للحدود: صفر، قيم قصوى، 12/240 شهر، leap dates، ترتيب غير صحيح.
14. mutation tests للمعادلات الحرجة أو دليل مكافئ.

### أوامر التحقق المطلوبة في S2

```powershell
python -m compileall -q backend
python -m pytest -q tests/test_finance_v2_*.py
python -m pytest -q
pnpm build
```

ويجب استمرار `tests/test_runtime_freeze.py` وSnapshot/tenant tests خضراء على exact commit.

## 15. التتبع

| Outcome | Requirement | Design | Implementation target | Test | Control | Gate |
|---|---|---|---|---|---|---|
| OUT-01 | FR-ARC-001/002 | §8 + archetype schema | `finance_v2` registry | T-FIN-ARC | version/reviewer status | G3 |
| OUT-02 | FR-FIN-001..010 | §6–7 + input/result schemas | ledgers/statements/metrics | T-FIN/T-PROP | invariant gate | G1 |
| OUT-03 | FR-EVD + FR-FIN | refs in schemas | contracts/serialization | T-FIN-INPUT/LINEAGE | source/assumption refs | G1/G4 |
| OUT-06 | FR-RPT-004 | null/blocker policy | result serializer | T-PROP-NULL | fail-closed | G1/G6 |
| OUT-07 | NFR-SEC/AUD | §4/13 | canonical entrypoint | T-FIN-SEC/SNAP | Freeze + tenant | every gate |
| OUT-08 | FR-REV | §14 | golden fixtures | T-FIN-ARC | human sign-off | G1/G7 |

## 16. معايير بوابة G0

| المعيار | الدليل | الحكم |
|---|---|---|
| المشكلة والنتيجة محددتان | البرنامج الأب + §1 | PASS |
| البدائل والقرار والآثار | §3 و§9 | PASS |
| العقود قابلة للتنفيذ | ملفات JSON Schema الثلاثة | PASS |
| حدود Freeze واضحة | §4 و§9 | PASS |
| التوافق والهجرة والتراجع | §10–12 | PASS |
| حالات الفشل والأمن | §13 | PASS |
| مواصفة الاختبارات | §14 | PASS |
| لا شبكة/مزود/إطلاق | metadata والحدود | PASS |
| صحة مالية مهنية مثبتة | ليست شرط G0؛ محجوبة إلى G1 | DEFER TO G1 |

**قرار G0: `PASS`.** يسمح بالانتقال إلى S2 dark build فقط. لا يسمح بـM3 أو default v2 أو L1. إذا تغيرت الملفات المجمدة أو الغلاف أو سياسة Snapshot تصبح G0 ملغاة ويجب ACR جديد.

## 17. Definition of Done لـS2

- implementation يطابق schemas دون bypass.
- T-FIN وT-PROP المستهدفة تمر.
- v1 regression والمستهلكون يمرون.
- لا ملف مجمد تغير.
- لا direct Finance path جديد.
- migration/rollback rehearsal موثق.
- exact commit وCI evidence.
- residual risks معلنة.
- G1 يبقى BLOCK حتى golden cases ومراجعة Finance Reviewer/CPA.

## 18. مشغلات المراجعة والاستبدال

يراجع هذا القرار عند:

- طلب تعديل contract/socket/module runtime.
- إضافة عملات متعددة أو طريقة إهلاك جديدة.
- تغيير تعريف CFADS/DSCR/LLCR.
- تغيير سياسة fiscal أو مصدرها.
- انتقال M3/M4/M5.
- اكتشاف تعارض مع FOUNDATION/PROGRAM/FREEZE.
- مرور 90 يوماً دون بدء S2.

أي قرار لاحق يذكر `supersedes: ACR-FIN-002-v1.0.0` ولا يعيد كتابة التاريخ.
