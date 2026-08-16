# ACR-FIN-004 — Baseline, Actual, Reforecast, Financing and Decision-Projection Lifecycle Contract

| الحقل | القيمة |
|---|---|
| Document ID | `ACR-FIN-004-v0.1.0` |
| الحالة | `OWNER-APPROVED REQUIREMENTS / IMPLEMENTATION AND G1 BLOCKED` |
| المالك | Product Owner |
| المراجعون المطلوبون | Principal Architecture + Finance Reviewer/CPA + QA + Security + Product Experience |
| تاريخ القرار | 2026-08-16 |
| خط الأساس المراجع | `main@50e7328bc07c828240947536d99d47250f10383b` |
| البرنامج الأب | `ASIE-FEASIBILITY-COMPLETE-01-v1.0.0` داخل `FOUNDATION-COMPLETE-20` |
| القرار الأب | `ACR-FIN-002-v1.0.0` |
| نطاق التفويض | تثبيت المتطلبات ومعايير القبول فقط؛ لا Runtime أو Snapshot أو provider/network أو Production |
| وضع التنفيذ الحالي | بعض الأسس موجودة؛ دورة Actual/Reforecast وKPI drill-down غير مثبتة كمسار مكتمل |

> **قرار ملزم للمتطلبات:** هذا العقد يثبت دلالة التمويل ودورة `Baseline → Actual → Reforecast` وإسقاطات القرار في مصدر واحد. وجود هذا العقد لا يعني أن القدرات مطبقة أو جاهزة أو معتمدة مهنيًا. لا تُرفع أي حالة تنفيذ إلا بكود وعقود واختبارات وأدلة exact-commit ومراجعات البوابة ذات الصلة.

---

## 1. السبب والسلطة

أثبت Consolidation Audit على خط الأساس أعلاه أن ASIE يملك بالفعل:

- دينًا اختياريًا وشرائح متعددة وسحوبات مؤرخة في Finance v2؛
- سيناريوهات حتمية تحافظ على المدخل الأساسي؛
- Snapshots غير قابلة للتعديل ومقارنة نتائج محفوظة في المسار الحالي؛
- تقارير وإسقاطات تقرأ من Snapshot.

لكنه لا يملك بعد عقدًا موحدًا يميز دلاليًا بين:

- Baseline معتمد؛
- Scenario مشتق للاستكشاف؛
- Actual مثبت لفترات منقضية؛
- Reforecast جديد نتيجة Actual أو shock أو تمويل جديد؛
- عدم انطباق مؤشرات الدين؛
- تسلسل `Summary → Drill-down → Comparison → Snapshot-backed Report`.

هذا الملف **ملحق متطلبات** لـ`ACR-FIN-002` وليس خطة برنامج جديدة، ولا يتجاوز قاعدة منع التجزئة في `FOUNDATION-COMPLETE-20`.

### ترتيب السلطة عند التعارض

1. AAS Runtime Freeze وAIA Constitution.
2. `PROGRAM-CLOSE-10` و`FOUNDATION-COMPLETE-20`.
3. السجلات الكانونية والعقود المجمدة.
4. `ACR-FIN-002`.
5. هذا العقد في نطاق lifecycle/applicability/product boundary فقط.
6. وثائق التنفيذ والأدلة المشتقة.

إذا احتاج التنفيذ إلى تغيير ملف مجمد أو غلاف `finance.calculate/result.v1` أو Snapshot Assembly، فالقرار `STOP-THE-LINE` ويلزم ACR/Freeze gate مستقل.

---

## 2. لغة الإلزام

- **MUST / يجب:** شرط قبول لا يجوز تجاوزه.
- **MUST NOT / يحظر:** سلوك مرفوض.
- **SHOULD / ينبغي:** مطلوب ما لم يوجد استثناء موثق ومراجع.
- **MAY / يجوز:** خيار لا يغير مصدر الحقيقة.
- `UNKNOWN` و`NOT_APPLICABLE` و`NOT_READY` و`ZERO_VERIFIED` حالات مختلفة، ولا يجوز تحويل أي منها إلى أخرى.

---

## 3. حدود المنتج: منصة قرار وليست ERP

### 3.1 المسارات الأساسية

يجب أن يخدم المنتج ثلاثة مقاصد أولية مترابطة:

1. **دراسة الجدوى:** بناء Baseline محكوم وتحليل السيناريوهات والمخاطر.
2. **الجاهزية التمويلية:** إعداد مخرجات مرتبطة بجهة/منتج تمويلي محدد دون ضمان قبول أو قرار ائتماني.
3. **الجاهزية للحاضنات والمسرعات:** إعداد ملف تقديم وقياس اكتمال ومتطلبات برنامج محدد بإصدار ومصدر وتاريخ سريان، دون ادعاء قبول أو شراكة أو اعتماد.

المتابعة بعد اعتماد الدراسة هي **امتداد قرار** يقارن Baseline وActual وReforecast، وليست نظام تشغيل مؤسسي عامًا.

### 3.2 الحد السلبي الملزم

يحظر توسيع هذا النطاق ليجعل ASIE نظام ERP أو مصدر حقيقة للعمليات اليومية. لا يملك هذا العقد:

- دفتر الأستاذ العام أو القيود المحاسبية التشغيلية؛
- الفوترة والتحصيل والمدفوعات التشغيلية؛
- الرواتب والموارد البشرية؛
- أوامر الشراء والمخزون والمستودعات؛
- CRM أو إدارة الموردين؛
- المطابقة البنكية أو الإقفال المحاسبي النظامي.

يجوز استقبال **ملخصات Actual معتمدة وذات lineage** من المستخدم أو مصدر مصرح به، لكن ASIE لا يصبح النظام المنشئ لتلك المعاملات ولا يحل محل النظام المحاسبي أو المراجع المهني.

---

## 4. نموذج دورة الحياة

### 4.1 الأنواع الكانونية

| النوع | الدلالة | قابلية التعديل |
|---|---|---|
| `BASELINE` | توقع معتمد يمثل نقطة القرار الأصلية | Immutable بعد الاعتماد |
| `SCENARIO` | اشتقاق تحليلي من Baseline أو Reforecast لاختبار فرضية | Artifact جديد؛ لا يغير الأصل |
| `ACTUAL` | قيم مثبتة لفترات منقضية مرتبطة بأدلة وحالة مراجعة | Append/correct عبر revision؛ لا overwrite صامت |
| `REFORECAST` | توقع جديد للفترات المفتوحة مبني على Baseline + Actual + تغييرات معتمدة | Artifact/Snapshot جديد |
| `COMPARISON` | إسقاط فروقات من artifacts محفوظة | Read-only؛ لا يعيد الحساب |
| `REPORT` | إسقاط من Snapshot محدد | Read-only؛ لا يعيد الحساب |

### 4.2 الرسم المسموح

```text
Approved Input Manifest
→ BASELINE Run
→ immutable BASELINE Snapshot
   ├─→ SCENARIO artifacts
   ├─→ ACTUAL period submissions/revisions
   └─→ REFORECAST Draft
        → approved REFORECAST Run
        → immutable REFORECAST Snapshot
             ├─→ SCENARIO artifacts
             └─→ later REFORECAST revisions

Saved artifacts
→ COMPARISON
→ KPI Summary
→ KPI Drill-down
→ Snapshot-backed REPORT
```

### 4.3 الثوابت

1. اعتماد Baseline يختم artifact وSnapshot لا يجوز تعديلهما أو إعادة حسابهما تاريخيًا.
2. Scenario ليس Actual وليس Reforecast، ولا يجوز ترقيته ضمنيًا إلى أي منهما.
3. Actual لا يستبدل Baseline؛ يرتبط به وبالفترات التي يغطيها.
4. Reforecast لا يعدل Baseline؛ ينشئ run وSnapshot جديدين مع `parent_baseline_snapshot_id`.
5. كل Reforecast يعلن `as_of_period`، والفترات المغلقة تأتي من Actual المعتمد، والفترات المفتوحة تأتي من forecast الجديد.
6. التصحيح بعد الختم ينشئ revision جديدًا ويحافظ على السابق.
7. كل artifact يحمل `organization_id` وIDs خادمية وschema/engine versions وinput/content hashes وlineage.
8. لا يختار العميل tenant أو manifest أو gate أو authoritative model.
9. Comparison وReport يقرآن artifacts/فوائد محفوظة فقط، ولا يستدعيان Finance لإعادة حساب تاريخي.
10. لا يجوز دمج قيم من Snapshots مختلفة دون تصريح comparison واضح ومراجع IDs.

---

## 5. عقد التمويل

### 5.1 الدين اختياري

- يجب أن يقبل النموذج `debt_tranches=[]`.
- غياب الدين ليس خطأ، ولا missing input، ولا تمويلًا صفريًا مفترضًا.
- لا يجوز إنشاء دين أو ممول أو شروط سداد لأن المشروع «يبدو محتاجًا للتمويل».

### 5.2 تمويل واحد كما صرح به المستخدم

عند إدخال المستخدم تمويلًا واحدًا:

- يجب حفظه كشريحة واحدة ذات ID ثابت.
- لا يجوز تقسيمه إلى عدة ممولين أو منتجات أو مصادر إلا إذا كان التقسيم اشتقاقًا حسابيًا معلنًا لا يغير دلالة المصدر.
- لا يجوز استنتاج اسم ممول أو نوع provenance أو حالة اعتماد.
- إذا كانت هوية الممول غير معروفة، تبقى `UNKNOWN` أو null بعلة صريحة؛ لا تُخترع قيمة.
- `lineage` يثبت أصل المدخل أو الافتراض، ولا يثبت تلقائيًا هوية دائن أو قبول تمويل.

### 5.3 عدة تمويلات

لا تنشأ عدة شرائح إلا من تصريح مستخدم معتمد أو مصدر خادمي مصرح به. لكل شريحة يجب حفظ:

- `tranche_id` ثابت؛
- هوية الجهة/المنتج إن صرح بها، وإلا حالة المعرفة؛
- drawdowns مؤرخة؛
- العملة والمبلغ والفائدة والمدة والسماح والسداد والballoon والرسوم؛
- assumption/evidence refs؛
- حالة المراجعة؛
- جدول فرعي ونتائج قابلة للـdrill-down.

يجوز تجميع النتائج للـSummary، لكن يحظر فقد هوية الشريحة من النتيجة الكانونية أو منع الرجوع من الإجمالي إلى مساهمات الشرائح.

### 5.4 التمويل المتأخر والتمويل الجديد

- drawdown معروف وقت Baseline ويقع في فترة لاحقة هو جزء من Baseline.
- تمويل لم يكن ضمن Baseline ثم ظهر بعد الاعتماد هو **حدث تغيير**، وليس تعديلًا رجعيًا.
- يجب أن يدخل التمويل الجديد عبر Draft Revision وApproved Input Manifest جديدين ثم Reforecast Run وSnapshot جديد.
- يجب أن تظل المقارنة قادرة على إظهار أثر التمويل الجديد منفصلًا: proceeds، fees، finance cost، principal، closing debt، cash، equity returns وDSCR/LLCR حيث تنطبق.

---

## 6. عقد applicability للمؤشرات

كل مؤشر يجب أن يحمل على الأقل:

- `metric_id`;
- `value` أو null؛
- `applicability_status`;
- `reason_code`;
- `source_artifact_id`;
- `formula_version`;
- `lineage_refs` اللازمة للتفسير.

القيم المسموحة لـ`applicability_status`:

- `APPLICABLE`;
- `NOT_APPLICABLE`;
- `UNKNOWN`;
- `NOT_READY`;
- `BLOCKED`.

### قاعدة no-debt

إذا لم توجد خدمة دين مؤهلة:

- `DSCR.applicability_status = NOT_APPLICABLE`;
- `LLCR.applicability_status = NOT_APPLICABLE`;
- `value = null`;
- `reason_code = NO_DEBT_SERVICE`;
- لا يفشل النموذج بسبب المؤشرين؛
- لا تعرض الواجهة صفرًا أو `ready` أو لون نجاح يوحي بقوة تغطية الدين.

إذا وجد دين لكن CFADS أو الجدول المطلوب ناقص، تكون الحالة `NOT_READY` أو `BLOCKED` وليست `NOT_APPLICABLE`.

---

## 7. Actual وReforecast

### 7.1 Actual

يجب أن يحدد كل Actual:

- الفترة أو النطاق الزمني؛
- القيمة والوحدة والعملة؛
- المصدر وevidence refs؛
- حالة `submitted/reviewed/approved/rejected`;
- هوية المراجع الخادمية؛
- content hash؛
- رابط Baseline/Reforecast المرجعي.

يحظر:

- تحويل غياب Actual إلى صفر؛
- استبدال forecast بقيمة Actual دون أثر revision؛
- تعديل Actual معتمد في مكانه؛
- خلط actual-to-date مع full-year actual دون دلالة.

### 7.2 Reforecast

يجب أن يعلن Reforecast:

- Baseline الأب؛
- آخر Snapshot مرجعي؛
- `as_of_period`;
- actual periods المستخدمة؛
- change set مع reason/evidence/approval؛
- التمويلات الجديدة أو المعدلة؛
- السياسات والإصدارات؛
- resulting input hash وrun/snapshot IDs.

يجب أن تكون المقارنات التالية ممكنة دون إعادة حساب الأصل:

- Baseline مقابل Actual-to-date؛
- Baseline مقابل Reforecast؛
- Reforecast سابق مقابل Reforecast لاحق؛
- Actual مقابل Reforecast للفترات المتطابقة أو المخططة؛
- Scenario مقابل الأصل الذي اشتق منه، مع منع مقارنات grain غير المتوافقة.

---

## 8. عقد تجربة المؤشرات والتقارير

لكل KPI قابل للعرض يجب توفير سلسلة واحدة متسقة:

1. **Summary:** القيمة والحالة والفترة ووحدة القياس.
2. **Drill-down:** الصيغة والمدخلات والمكونات والفترات والشرائح/البنود والlineage.
3. **Comparison:** الأصلان المقارنان، delta مطلق ونسبي عند صلاحية المقام، وسبب عدم المقارنة إن تعذرت.
4. **Report:** نفس القيمة والحالة والمصدر من Snapshot المحدد؛ لا حساب موازي.

الثوابت:

- UI وReport لا يحسبان الحقيقة المالية.
- الضغط على KPI لا يغير run أو Snapshot.
- التجميع لا يلغي إمكانية تتبع البند أو الشريحة.
- اختلاف العملة أو الفترة أو grain يمنع delta مضللًا.
- `UNKNOWN/NOT_APPLICABLE/NOT_READY` تظهر نصيًا بالعربية ولا تعتمد على اللون وحده.
- Snapshot ID وrun ID وas-of period وحالة المراجعة ظاهرة في drill-down/report metadata.

---

## 9. الحاضنات والمسرعات وجهات التمويل

يجب تمثيل كل جهة أو برنامج عبر Profile مستقل محدود النطاق والزمن يحتوي:

- `institution_kind ∈ {LENDER, INCUBATOR, ACCELERATOR, GRANT_PROGRAM, OTHER_REVIEWED}`;
- اسم الجهة والبرنامج والإصدار وتاريخ السريان؛
- المصدر الرسمي وحالة freshness؛
- eligibility rules وdocument checklist؛
- متطلبات العرض والمؤشرات؛
- حالة `REFERENCE_ONLY/REVIEWED/VALIDATED/EXPIRED`;
- حدود الادعاء.

يحظر:

- تعميم متطلبات جهة على جميع الجهات؛
- الادعاء بالاعتماد أو القبول أو الشراكة دون Evidence ID صالح؛
- منح ASIE سلطة قرار ائتماني أو قبول حاضنة؛
- خلط Profile الجهة مع شروط التمويل الفعلية التي أدخلها المستخدم.

---

## 10. مصفوفة القبول الإلزامية

| ID | الحالة | معيار القبول |
|---|---|---|
| FLC-F1 | مشروع بلا دين | النموذج ready إذا اكتملت بقية المدخلات؛ DSCR/LLCR = `NOT_APPLICABLE/NO_DEBT_SERVICE`؛ لا صفر ولا فشل |
| FLC-F2 | تمويل واحد مصرح به | شريحة واحدة فقط، نفس الشروط والlineage، لا ممول أو provenance مستنتج |
| FLC-F3 | عدة تمويلات مصرح بها | كل شريحة وسحب محفوظان وقابلان للـdrill-down؛ الإجمالي يطابق مجموع الجداول |
| FLC-F4 | سحب متأخر معروف في Baseline | يبدأ في الفترة المعلنة وتنعكس الفائدة/السداد دون نقله إلى البداية |
| FLC-F5 | تمويل جديد بعد Baseline | Baseline bytes/hash ثابتان؛ Reforecast جديد يحمل الشريحة والتغيير والparent IDs |
| FLC-F6 | Actual مقابل Baseline | الفترات والعملة والgrain متوافقة؛ delta من نتائج محفوظة؛ لا إعادة حساب Snapshot |
| FLC-F7 | Reforecast متكرر | كل نسخة immutable ومرتبطة بالأصل والسابق؛ المقارنة تعيد نفس النتيجة حتميًا |
| FLC-F8 | KPI chain | Summary وDrill-down وComparison وReport تعرض القيمة والحالة وSnapshot نفسها |
| FLC-F9 | حدود ERP | يقبل Actual summary ولا ينشئ GL/payroll/inventory/procurement transactions |
| FLC-F10 | Profile حاضنة/ممول | Profile محدد الإصدار والمصدر والحالة، ولا ينتج ادعاء قبول أو اعتماد |
| FLC-F11 | tenant isolation | cross-tenant artifact/profile/comparison يرفض قبل القراءة أو الحساب |
| FLC-F12 | revision/tamper | hash أو parent أو evidence mismatch يفشل مغلقًا ولا ينتج Snapshot جزئيًا |

الحد الأدنى للأدلة قبل أي claim:

- contract/schema tests؛
- unit/property tests لحالات F1–F7؛
- integration tests لمسار Approved Manifest/Run/Snapshot؛
- API/projection tests لـF8؛
- negative scope tests لـF9–F12؛
- fixtures مستقلة قابلة لإعادة الاستخدام؛
- exact-head CI وCross-Platform؛
- مراجعة Finance Reviewer/CPA لدلالات التمويل والمؤشرات؛
- مراجعة Product Experience لعرض الحالات بالعربية وRTL؛
- rollback وعدم تغيير historical snapshots.

---

## 11. خريطة التتبع

| Outcome | Requirements | التنفيذ المتوقع | الاختبار | البوابة |
|---|---|---|---|---|
| دين اختياري صحيح | §5.1 + §6 | Finance contracts/results | FLC-F1 | Finance review |
| تمويل واحد/متعدد بلا استنتاج | §5.2–5.3 | input/result/subledger contracts | FLC-F2/F3 | G1 |
| تمويل منتصف العمر | §5.4 + §7 | revision/reforecast admission | FLC-F4/F5 | ACR/architecture |
| Baseline/Actual/Reforecast | §4 + §7 | versioned artifacts and snapshots | FLC-F5–F7 | Snapshot/freeze gate if touched |
| KPI drill-down/comparison/report | §8 | API/projections/UI | FLC-F8 | FC20-13/14 |
| عدم التحول إلى ERP | §3 | scope guards/admission | FLC-F9 | Product/architecture |
| تمويل/حاضنات/مسرعات | §3.1 + §9 | institution profiles | FLC-F10 | FEASIBILITY-COMPLETE-01 |
| عزل وتلاعب | §4.3 + §10 | server binding/hash/authorization | FLC-F11/F12 | Security |

هذه الخريطة تحدد الملكية ولا تمنح إذن تنفيذ لملف مجمد.

---

## 12. حالة التنفيذ عند اعتماد المتطلبات

| المجال | الحالة عند الخط الأساسي |
|---|---|
| الدين الاختياري وحساب الشرائح والسحوبات المؤرخة | `PARTIAL FOUNDATION EXISTS` |
| no-debt دون فشل | `EXISTS` |
| DSCR/LLCR كـ`NOT_APPLICABLE` صريح | `MISSING/CONFLICTING LEGACY SEMANTICS` |
| baseline/scenario immutability | `PARTIAL FOUNDATION EXISTS` |
| Actual contract | `MISSING` |
| Reforecast contract/runtime | `MISSING` |
| تمويل جديد بعد Baseline | `PARTIAL: REPRESENTABLE ONLY AS PREDECLARED DRAWDOWN` |
| tranche-level result drill-down | `PARTIAL` |
| Snapshot comparison | `EXISTS IN CURRENT V1 PATH` |
| end-to-end KPI drill-down | `MISSING` |
| incubator/accelerator profiles | `MISSING` |
| explicit non-ERP invariant | `ADOPTED BY THIS REQUIREMENTS CONTRACT; NOT YET ENFORCED` |

لا يجوز تحويل أي صف إلى `COMPLETE` بسبب دمج هذا الملف وحده.

---

## 13. بوابات التغيير

### G-FLC-0 — Requirements adopted

- موافقة مالك المنتج؛
- مراجعة عدم التعارض مع ACR-FIN-002 وFreeze والبرامج الأب؛
- دمج هذا الملف من exact head؛
- لا claim تنفيذ.

### G-FLC-1 — Executable contracts ready

- schemas/versioning/applicability/lineage مغلقة؛
- fixtures F1–F12 موجودة؛
- architecture, finance, security وQA approvals؛
- لا تغيير frozen path دون ACR مستقل.

### G-FLC-2 — Dark implementation verified

- Finance v2/internal APIs فقط وفق حدود المرحلة؛
- جميع اختبارات العقد والخصائص تمر؛
- historical snapshots لم تتغير؛
- rollback مثبت؛
- لا Runtime/Public claim.

### G-FLC-3 — Authoritative integration

يتطلب بوابات ACR-FIN-002 المناسبة، وسياسة model selection خادمية، وتوافق المستهلكين، ومراجعة Finance مستقلة، وأي Freeze change مستقل. لا يفتحه هذا العقد.

---

## 14. الممنوعات

- لا تعديل AAS Runtime أو Snapshot Assembly بهذا الملف.
- لا شبكة أو مزود أو Google Maps أو AI.
- لا Production أو Public Beta أو claim مهني/مصرفي.
- لا إعادة حساب أو backfill للـSnapshots التاريخية.
- لا dual financial truth.
- لا hidden defaults أو missing→zero.
- لا استنتاج تمويل أو ممول أو قبول.
- لا خطة برنامج عليا جديدة؛ التنفيذ يُسجل داخل حزم `FOUNDATION-COMPLETE-20` و`FEASIBILITY-COMPLETE-01`.
- لا وصف Actual/Reforecast/drill-down بأنه مكتمل قبل الأدلة.

---

## 15. قرار G-FLC-0 المقترح

بعد دمج هذا العقد ومراجعة exact head:

- `PASS` لتثبيت متطلبات lifecycle/applicability/product boundary فقط.
- `BLOCK` لادعاء أن Actual أو Reforecast أو KPI drill-down مطبق.
- `BLOCK` لأي تغيير frozen/runtime/snapshot بلا بوابته المستقلة.
- `BLOCK` لأي إطلاق أو اعتماد أو قبول ممول/حاضنة.
- التنفيذ اللاحق يجب أن يكون شرائح صغيرة قابلة للعكس ومربوطة بـFLC-F1..F12، لا خطة خامسة.
