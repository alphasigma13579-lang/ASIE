# ACR-FIN-003-C3C — Deterministic 2D Sensitivity Dark Build

| الحقل | القيمة |
|---|---|
| Document ID | `ACR-FIN-003-C3C-v1.0.0` |
| الحالة | `ACCEPTED FOR C3C DARK-BUILD UPON MERGE` |
| خط الأساس | `main@d2fe4198bea150b67c183dcbdb60ecb780d64c05` |
| القرار الأب | `ACR-FIN-003-v1.0.0` ثم `ACR-FIN-002-v1.0.0` |
| البرنامج الأب | `ASIE-FEASIBILITY-COMPLETE-01-v1.0.0` |
| نطاق التفويض | C3C deterministic 2D sensitivity داخل `finance_v2` وفي CI فقط |
| خارج التفويض | RNG، sampling، distributions، correlation، copula، convergence، Runtime، Snapshot، شبكة، مزود، أسرار، G1، L1، أو ادعاء مهني/مصرفي |
| المالك | Product Owner + Principal Architecture + Finance Engineering |
| بوابة التنفيذ | دمج هذا القرار بعد CI ومراجعة exact-head، ثم PR تنفيذ مستقل |

> **قرار ملزم:** C3C ليست Monte Carlo. هي تعداد حتمي محدود لخلايا محورين يعيد تشغيل Finance v2 كاملًا لكل خلية. لا يجوز ربط الناتج بالمسار الرسمي أو Snapshot، ولا وصفه بأنه تحليل حساسية مهني معتمد، قبل البوابات اللاحقة.

---

## 1. سبب القرار

### FACT

- `main@d2fe4198` يحتوي Finance v2 حتميًا، وسيناريوات deterministic تعيد التحقق من المدخل المشتق ثم تعيد بناء النموذج كاملًا.
- `ACR-FIN-003` وملف `finance-sensitivity-profile.v1` يفرضان محورين، targets allowlisted، lineage، عدم التداخل، وحدًا أقصى `21×21` و`maximum_cells<=441`.
- C3B يقبل profile من trusted registry/Approved Manifest ويفصل التحقق غير السلطوي عن القبول السلطوي.
- C3B يبقي `ValidatedRiskProfile.execution_ready=False` لأنه لا يملك محركًا.
- ACR-FIN-003 الأصلي يفوض العقود static فقط، لذلك يلزم هذا الملحق قبل كود C3C.
- الملفات `backend/finance_engine.py` و`backend/module_runtime.py` و`backend/snapshot_assembly.py` محمية وخارج النطاق.

### UNKNOWN / DEFERRED

- لا توجد موافقة CPA/Quant/Sector مسماة على calibration أو تحليل مهني.
- لا توجد توزيعات معايرة أو RNG vectors منفذة.
- لا يوجد performance baseline معتمد بعد لأقصى شبكة `441` خلية.
- لا يوجد تفويض M3 أو تشغيل authoritative أو Snapshot.

### DECISION

نبني C3C كحزمة داخلية dark-build ذات capability ضيقة:

1. تقبل فقط `ValidatedFinanceInput` و`ValidatedRiskProfile(kind="sensitivity", status="approved")`.
2. تنشئ preparation داخليًا خاصًا بـ`dark_sensitivity_v1`؛ لا تعدل `execution_ready` العام ولا تمنح صلاحية Runtime.
3. تطبق fixed overrides ثم قيمة المحور الأول ثم قيمة المحور الثاني على نسخة جديدة من المدخل الأساسي لكل خلية.
4. تعيد `validate_finance_input` ثم `build_financial_model` كاملًا لكل خلية.
5. لا تستخدم تقريبًا خطيًا، caching بين الخلايا، interpolation، sampling، RNG أو fallback.
6. تفشل المصفوفة ذريًا: أي خلية invalid/not-ready تمنع إخراج أي metrics جزئية.
7. تحتفظ فقط بهوية الخلية وinput hash والmetrics المطلوبة؛ لا تحتفظ بقوائم مالية كاملة لكل خلية.
8. تنتج عقد نتيجة داخليًا versioned، صريح `execution_scope="dark_build"` و`snapshot_eligible=false`.

---

## 2. تفسير حدود المراجعة المهنية

C3C تعداد حتمي لقيم صريحة وافق عليها profile؛ لا ينشئ توزيعًا ولا correlation ولا calibration ولا استنتاجًا إحصائيًا. لذلك:

- مراجعة Quantitative/Sector/CPA المطلوبة في ACR-FIN-003 تبقى مانعة لـC3D/C3E/C3F وG1.
- C3C يحتاج قبل الدمج: architecture review، exact-cell parity، invariants، QA/security negatives، وقياس أداء.
- اجتياز C3C لا يثبت معقولية قيم المحاور أو كفاية الدراسة؛ يثبت فقط صحة تنفيذ العقد الحتمي.

---

## 3. حدود السلطة والبيانات

```text
Server-owned ValidatedFinanceInput
+ C3B authoritative admitted sensitivity profile
→ C3C capability preparation (dark_sensitivity_v1 only)
→ canonical baseline thaw per cell
→ shared allowlisted override kernel
→ full finance input revalidation
→ full Finance v2 model rebuild
→ invariant/status gate
→ selected metric projection only
→ atomic sensitivity result
→ canonical result hash
```

محظور:

- profile body/path/expression/callable من العميل؛
- raw JSONPath أو `eval` أو target خارج allowlist S2-C2؛
- client-supplied tenant/manifest authority؛
- استدعاء Runtime/Bus/Socket/Snapshot أو كتابة قاعدة بيانات؛
- استدعاء network/provider/secret؛
- نسخ منطق override مستقل ينجرف عن deterministic scenarios؛
- تحويل missing/invalid/`None` إلى صفر؛
- إخراج grid جزئي على أنه ready.

---

## 4. شروط الدخول

يجب أن تفشل C3C مغلقًا ما لم تتحقق جميع الشروط:

- المدخل `ValidatedFinanceInput` صالح ومربوط بخادم، و`input_hash` مطابق لوثيقته canonical.
- profile هو `ValidatedRiskProfile` من النوع `sensitivity` وبحالة `approved`.
- لأن C3B يمنع `approved` في non-authoritative mode، فحالة `approved` تعني اجتياز مسار registry admission.
- schema/id/version/hash وregistry/manifest/policy/dependency hashes تبقى في lineage النتيجة.
- profile document يعاد thaw دون تعديل ويطابق `content_hash`.
- عدد الخلايا الفعلي يساوي حاصل طولي المحورين، ولا يتجاوز `maximum_cells` أو hard cap `441`.
- metric IDs كلها موجودة في FinancialModel؛ metric مفقود blocker وليس null/zero.
- لا يقبل C3C distribution/correlation/policy profile.

`execution_ready=False` في C3B لا يتحول إلى `True`. ينشئ C3C نوعًا داخليًا منفصلًا `PreparedSensitivityRun` يحمل `execution_scope="dark_sensitivity_v1"` و`runtime_eligible=False`.

---

## 5. عقد نتيجة C3C

العقد المقترح `finance-sensitivity-result.v1` مغلق وداخلي، ويحتوي كحد أدنى:

- `schema_version`
- `sensitivity_engine_version`
- `status ∈ {dark_ready, not_ready}`
- `execution_scope = dark_build`
- `snapshot_eligible = false`
- baseline `finance_input_hash`
- profile id/version/content hash
- registry snapshot وApproved Manifest وpolicy hashes
- axis IDs/target refs/operations/ordered values
- ordered metric IDs
- `cell_count`
- row-major cells
- blockers
- canonical `result_hash`

كل خلية ready تحتوي:

- `row_index`, `column_index`
- قيمة المحور الأول والثاني كسلاسل Decimal canonical
- `derived_input_hash`
- metrics المطلوبة فقط كسلاسل Decimal canonical أو null حقيقي إذا كان metric نفسه غير قابل للتعريف وفق Finance؛ لا missing→zero
- لا periods، debt schedule أو raw input document.

الترتيب canonical:

- ترتيب المحاور كما ورد في profile.
- المحور الأول outer loop، والمحور الثاني inner loop.
- ترتيب metric IDs كما ورد في profile.
- fixed overrides تطبق أولًا، ثم axis 0، ثم axis 1.
- كل خلية تبدأ من thaw جديد للمدخل الأساسي؛ لا mutation مشتركة.

---

## 6. الذرية والفشل المغلق

### Contract/preparation errors

ترفع `FinanceContractError` برمز ثابت، مثل:

- `FIN2_SENSITIVITY_PROFILE_KIND`
- `FIN2_SENSITIVITY_PROFILE_NOT_ADMITTED`
- `FIN2_SENSITIVITY_HASH_MISMATCH`
- `FIN2_SENSITIVITY_CELL_LIMIT`
- `FIN2_SENSITIVITY_METRIC_UNAVAILABLE`

### Cell/model failures

إذا فشلت خلية في override أو revalidation أو model invariants:

- النتيجة `status="not_ready"`;
- `cells=[]` دائمًا؛
- blocker يحدد row/column ومرحلة الفشل ورمز Finance الأصلي دون raw financial data؛
- لا متابعة افتراضية ولا zero ولا partial grid؛
- لا استثناء غير مضبوط أو traceback في العقد.

إذا نجحت كل الخلايا فقط تصبح `dark_ready`.

---

## 7. إعادة استخدام override kernel

يمنع نسخ منطق `scenarios.py`. التنفيذ المعتمد:

- استخراج kernel داخلي في `backend/finance_v2/overrides.py`.
- API داخلي يطبق قائمة overrides على thaw جديد، يعيد validation باستخدام server binding مشتق من المدخل الأصلي.
- `evaluate_scenarios` يستخدم kernel نفسه دون تغيير bytes/status/blockers الحالية.
- `sensitivity.py` يستخدم kernel نفسه.
- regression parity إلزامي للسيناريوات الموجودة قبل قبول C3C.

أي تعذر للاستخراج دون تغيير semantics الحالية هو Stop-the-Line ومراجعة لهذا القرار.

---

## 8. التعقيد وميزانية الموارد

لتكن:

- `R` عدد قيم المحور الأول؛
- `C` عدد قيم المحور الثاني؛
- `K=R×C<=441`;
- `P<=240` فترات النموذج؛
- `M<=8` metrics حساسية.

الحدود:

- الزمن: `O(K × FinanceModel(P))`؛ لا ادعاء `O(1)` غير واقعي.
- ذاكرة نتيجة C3C: `O(K×M)`، مع نموذج خلية واحد حي في كل لحظة.
- عدد build calls يجب أن يساوي `K` بالضبط؛ لا إعادة بناء خفية.
- لا parallelism في C3C؛ الترتيب التسلسلي جزء من الحتمية ومنع resource spikes.
- لا cache عالمي أو بين tenants.
- اختبار 21×21 يثبت الحد والذاكرة المنطقية وعدم الاحتفاظ بالنماذج.
- benchmark منفصل يسجل p50/p95 والبيئة؛ لا توضع عتبة زمنية عمياء قبل أول قياس.
- لا يدمج PR التنفيذ إذا أظهر القياس تضخمًا غير محدود أو تجاوزًا غير مبرر مقارنة ببناء `K` نماذج منفردة.

---

## 9. الملفات المسموح بها

### إضافة

- `backend/finance_v2/overrides.py`
- `backend/finance_v2/sensitivity.py`
- `schemas/finance/finance-sensitivity-result.v1.schema.json`
- `tests/test_finance_v2_sensitivity.py`
- وثيقة evidence/benchmark خاصة بـC3C

### تعديل ضيق

- `backend/finance_v2/scenarios.py` لاستخدام kernel المشترك
- `backend/finance_v2/__init__.py` لصادرات C3C الداخلية
- `tests/test_finance_v2_scenarios.py` لإثبات عدم الانحدار
- هذا ACR إذا كشفت المراجعة تناقضًا

### ممنوع

- `backend/finance_engine.py`
- `backend/module_runtime.py`
- `backend/snapshot_assembly.py`
- AAS registry/freeze files
- API/frontend/PDF/CSV/database/runtime wiring
- schemas المالية القائمة إلا إذا كشف contract review ضرورة موثقة وتعديل هذا القرار أولًا

---

## 10. مصفوفة الاختبار والإثبات

| ID | الاختبار | معيار القبول |
|---|---|---|
| T-C3C-001 | 2×3 ordering | ست خلايا row-major بقيم وهوية ثابتة |
| T-C3C-002 | direct cell parity | كل input hash وmetric يساوي إعادة تشغيل مباشرة لنفس overrides |
| T-C3C-003 | baseline-equivalent cell | يساوي baseline model byte/logical metrics |
| T-C3C-004 | fixed override parity | يطبق في كل خلية مرة واحدة |
| T-C3C-005 | input immutability | baseline/profile bytes لا تتغير |
| T-C3C-006 | repeatability | نفس المدخل/profile يعطي result hash والبايتات نفسها |
| T-C3C-007 | max 21×21 | 441 build calls، 441 cells، لا model retention |
| T-C3C-008 | atomic invalid cell | not_ready وcells فارغة وblocker محدد |
| T-C3C-009 | model invariant failure | not_ready بلا partial metrics |
| T-C3C-010 | unavailable metric | fail closed؛ لا null/zero مخترع |
| T-C3C-011 | wrong profile kind/status | رفض قبل أول build |
| T-C3C-012 | tampered profile hash/body | رفض قبل أول build |
| T-C3C-013 | scenario regression | مخرجات deterministic scenarios الحالية لا تتغير |
| T-C3C-014 | schema closure | additionalProperties=false، required/enum/hash formats |
| T-C3C-015 | cross-platform canonical result | logical bytes/hash متطابقة |
| T-C3C-016 | protected blobs | hashes مطابقة لـmain قبل وبعد |
| T-C3C-017 | import boundary | لا Runtime/Snapshot/network/provider imports |
| T-C3C-018 | benchmark evidence | p50/p95، runner، K/P، peak logical retention مسجلة |

يلزم أيضًا baseline suite كاملة وASIE CI وCross-Platform على exact head.

---

## 11. خريطة التهديد والضبط

| الخطر | الضبط | الدليل |
|---|---|---|
| forged/non-admitted profile | approved lifecycle only via C3B authoritative admission + hash recheck | wrong-mode/tamper negatives |
| target injection | shared parsed allowlist kernel؛ لا raw expression | malformed target tests |
| cross-tenant cache leak | لا cache ولا persistence ولا runtime | import/state inspection |
| partial grid consumed | atomic empty-cells failure | invalid-cell/invariant tests |
| missing→zero | metric availability and Finance blocker propagation | unavailable/null tests |
| scenario drift | kernel واحد + exact regression | scenario parity |
| resource exhaustion | K<=441، sequential، one live model | call-count/max-grid tests |
| nondeterministic output | fixed order + Decimal + canonical serialization | repeat/cross-platform |
| false readiness | dark_ready + snapshot_eligible=false + claim boundary | result schema/claim review |
| protected-path regression | denylist + raw blob equality | exact blob hashes |

---

## 12. بوابات التنفيذ

### G-C3C-0 — ACR accepted

- هذا الملف مدمج من exact-head نظيف.
- CI وarchitecture review ناجحان.
- لا تعارض مع ACR-FIN-002/003 أو Freeze.

### G-C3C-1 — Implementation verified

- جميع T-C3C تمر.
- baseline suite وCross-Platform تمر.
- benchmark evidence منشورة.
- no unresolved review threads.
- الملفات المحمية مطابقة.

### G-C3C-2 — Merge allowed

- PR صغير مستقل؛ exact head ثابت.
- result يبقى dark/non-snapshot.
- rollback هو revert واحد بلا migration.
- residual risks وUNKNOWNs معلنة.

لا تفتح هذه البوابات C3D أو C3E أو G1 أو Runtime أو Snapshot أو إطلاقًا.

---

## 13. التراجع والتوافق

- لا migration ولا persistence ولا feature flag.
- التراجع: revert PR التنفيذ ثم، عند الحاجة، revert هذا الملحق.
- deterministic scenarios يجب أن تبقى متوافقة منطقيًا وbyte-wise حيث يوجد serialization.
- historical results وSnapshots لا تقرأ C3C ولا تتغير.
- أي حاجة لتغيير ملف ممنوع أو غلاف v1 أو Snapshot هي Stop-the-Line وACR جديد.

---

## 14. قرار G-C3C-0

عند دمج هذا الملحق بعد CI ومراجعة exact-head:

- `PASS` لبناء C3C deterministic 2D sensitivity dark-build فقط.
- `BLOCK` لـC3D RNG/distributions.
- `BLOCK` لـC3E correlation/convergence.
- `BLOCK` لأي professional/G1/L1 claim.
- `BLOCK` لأي Runtime/Snapshot/network/provider activation.
