# ACR-FIN-004 — Baseline, Actual, Reforecast, Financing and Decision-Projection Lifecycle Contract

| الحقل | القيمة |
|---|---|
| Document ID | `ACR-FIN-004-v0.2.0` |
| الحالة | `OWNER-APPROVED REQUIREMENTS / IMPLEMENTATION AND G1 BLOCKED` |
| المالك | Product Owner |
| طبقات المراجعة الفنية | GitHub Codex + CodeRabbit + GitHub Copilot + Principal Independent Audit |
| تاريخ القرار | 2026-08-16 |
| خط الأساس المراجع | `main@50e7328bc07c828240947536d99d47250f10383b` |
| البرنامج الأب | `ASIE-FEASIBILITY-COMPLETE-01-v1.0.0` داخل `FOUNDATION-COMPLETE-20` |
| القرار الأب | `ACR-FIN-002-v1.0.0` |
| نطاق التفويض | تثبيت المتطلبات ومعايير القبول فقط؛ لا Runtime أو Snapshot أو provider/network أو Production |
| وضع التنفيذ الحالي | بعض الأسس موجودة؛ دورة Actual/Reforecast وKPI drill-down غير مثبتة كمسار مكتمل |

> **قرار ملزم للمتطلبات:** هذا العقد يثبت دلالة التمويل ودورة `Baseline → Actual → Reforecast` وإسقاطات القرار في مصدر واحد. وجود هذا العقد لا يعني أن القدرات مطبقة أو جاهزة أو معتمدة مهنيًا. لا تُرفع أي حالة تنفيذ إلا بكود وعقود واختبارات وأدلة exact-commit ومراجعات البوابة ذات الصلة.

### طبقات المراجعة الفنية الأربع

1. **GitHub Codex:** مراجعة findings على exact head.
2. **CodeRabbit:** مراجعة عقدية/أمنية آلية مستقلة.
3. **GitHub Copilot:** مراجعة exact-head إضافية مستقلة.
4. **Principal Independent Audit:** مراجعة بشرية التوجيه ينفذها المستشار التقني فوق مخرجات النماذج، ويتحقق من الأدلة والسلطات والكود بدل اعتماد خلاصاتها تلقائيًا.

هذه الطبقات الأربع تكفي لبوابة المتطلبات والتنفيذ التقني المظلم داخل التفويض الحالي. لا تمثل أي منها اعتماد CPA بشريًا أو اعتمادًا مصرفيًا/مهنيًا، ولا تلغي شرط `ACR-FIN-002` لمراجعة Finance Reviewer/CPA قبل G1 أو أي claim مهني.

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
- `UNKNOWN` و`NOT_APPLICABLE` و`NOT_READY` و`BLOCKED` حالات applicability/readiness مختلفة، ولا يجوز تحويل أي منها إلى أخرى.
- `ZERO_VERIFIED` ليست `applicability_status`؛ هي `value_status` مستقلة لا تصح إلا مع `APPLICABLE` و`value=0` ودليل يثبت أن الصفر مقصود، وليست قيمة مفقودة أو غير منطبقة.

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
server-owned Approved Input Manifest
→ server-owned Manifest Validation Gate (passed; manifest/gate IDs and hashes bound)
→ BASELINE Run
→ immutable BASELINE Snapshot
   ├─→ SCENARIO artifacts
   ├─→ ACTUAL period submissions/revisions
   └─→ REFORECAST Draft
        → new server-owned Approved Input Manifest
        → new server-owned Manifest Validation Gate (passed; manifest/gate IDs and hashes bound)
        → approved REFORECAST Run
        → immutable REFORECAST Snapshot
             ├─→ SCENARIO artifacts
             └─→ later REFORECAST Drafts through the same new-manifest/new-gate path

Saved artifacts
→ KPI Summary
→ KPI Drill-down
→ COMPARISON
→ Snapshot-backed REPORT
```

### 4.3 الثوابت المطلوبة عند التنفيذ

هذه ثوابت مستهدفة ومحجوبة حتى G-FLC-1 وما بعده؛ لا تصف Snapshot الحالي بأنها مطبقة لمجرد وجود العقد.

1. اعتماد Baseline يختم artifact وSnapshot لا يجوز تعديلهما أو إعادة حسابهما تاريخيًا.
2. Scenario ليس Actual وليس Reforecast، ولا يجوز ترقيته ضمنيًا إلى أي منهما.
3. Actual لا يستبدل Baseline؛ يرتبط به وبالفترات التي يغطيها.
4. Reforecast لا يعدل Baseline؛ ينشئ run وSnapshot جديدين مع `parent_baseline_snapshot_id`، ويحمل `predecessor_reforecast_snapshot_id` للنسخ اللاحقة فقط.
5. `as_of_period` هو period key كانوني وفق `period_calendar_id` وليس timestamp حرًا. الفترات `<= as_of_period` مغلقة وتأتي من Actual معتمد، والفترات `> as_of_period` مفتوحة وتأتي من forecast الجديد؛ يمنع overlap أو gap أو خلط calendars.
6. كل Baseline وكل Reforecast يجب أن يرتبطا بـApproved Input Manifest خادمي جديد وبـManifest Validation Gate خادمية ناجحة مرتبطة به ID/hash قبل استدعاء Finance؛ لا مسار مباشر من Manifest أو Draft أو change set إلى Run.
7. كل Reforecast، سواء سببه Actual أو shock أو تمويلًا جديدًا، يمر بمسار manifest/gate الجديد كاملًا؛ لا يعيد استخدام gate لmanifest سابق.
8. التصحيح بعد الختم ينشئ revision جديدًا ويحافظ على السابق.
9. كل artifact يحمل `organization_id` وIDs خادمية وschema/engine versions وcontent hashes وlineage، ويحفظ manifest/gate IDs وhashes عند انطباق مسار التنفيذ.
10. يميز العقد بين `finance_input_hash` لوثيقة `finance-model-input.v2` و`admission_input_hash` لسلسلة القبول الخادمية؛ لا يجوز استخدام اسم `input_hash` الغامض للجمع بين preimages مختلفين.
11. لا يختار العميل tenant أو manifest أو gate أو authoritative model.
12. Comparison وReport يقرآن artifacts/نتائج محفوظة فقط، ولا يستدعيان Finance لإعادة حساب تاريخي.
13. لا يجوز دمج قيم من Snapshots مختلفة دون تصريح comparison واضح ومراجع IDs.
14. metadata المطلوبة تُحدد حسب lifecycle type: Baseline الجذري لا يحتاج parent، بينما Reforecast وActual يحتاجان روابط الأب المحددة في هذا العقد؛ null مسموح فقط حيث يصرح العقد بذلك.

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
- `value_status ∈ {VALUE_PRESENT, ZERO_VERIFIED, VALUE_ABSENT}`؛
- `applicability_status`;
- `reason_code`;
- `period` أو `period_range`؛
- `unit`؛
- `currency` عندما تكون القيمة مالية، وإلا null مفسرة؛
- `grain` versioned يحدد frequency ونطاق التجميع والأبعاد؛
- `source_artifact_id`;
- `formula_version`;
- `lineage_refs` اللازمة للتفسير.

يجب أن تستخدم Summary وDrill-down وComparison وReport هذا الـmetric object نفسه أو projection envelope صادرًا منه دون إعادة تعريف period/unit/currency/grain.

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
- `value_status = VALUE_ABSENT`;
- `reason_code = NO_DEBT_SERVICE`;
- لا يفشل النموذج بسبب المؤشرين؛
- لا تعرض الواجهة صفرًا أو `ready` أو لون نجاح يوحي بقوة تغطية الدين.

إذا وجد دين، يكون القرار حتميًا وفق الآتي:

| الشرط | `applicability_status` | `reason_code` |
|---|---|---|
| CFADS وحده غير مكتمل/غير معتمد بعد، دون خرق سلامة أو تفويض | `NOT_READY` | `CFADS_NOT_READY` |
| جدول الدين وحده غير مكتمل/غير معتمد بعد، دون خرق سلامة أو تفويض | `NOT_READY` | `DEBT_SCHEDULE_NOT_READY` |
| CFADS وجدول الدين كلاهما غير مكتملين/غير معتمدين، دون خرق سلامة أو تفويض | `NOT_READY` | `CFADS_AND_DEBT_SCHEDULE_NOT_READY` |
| CFADS أو جدول الدين موجود لكنه يفشل schema/hash/tenant/authorization أو invariant مطلوب | `BLOCKED` | رمز blocker المحدد؛ وإذا وجد أكثر من blocker يستخدم `MULTIPLE_DEBT_COVERAGE_BLOCKERS` وتُحفظ detail codes مرتبة كانونيًا |
| CFADS وجدول الدين صالحان وخدمة الدين موجودة | `APPLICABLE` | `READY` |

الأولوية عند اجتماع الشروط: `BLOCKED` ثم `NOT_READY` ثم `APPLICABLE`. داخل `NOT_READY` يحدد الجدول أعلاه رمز الحالة المفردة أو المركبة. داخل `BLOCKED` يستخدم الرمز المفرد عند علة واحدة و`MULTIPLE_DEBT_COVERAGE_BLOCKERS` عند تعددها. لا يجوز أن تختار Finance وAPI وUI حالات أو reason codes مختلفة لنفس metric object.

---

## 7. Actual وReforecast

### 7.1 Actual

يجب أن يحدد كل Actual:

- `organization_id` و`project_id` مربوطين خادميًا؛
- `parent_baseline_snapshot_id` الذي يحدد Baseline المرجعي؛
- `actual_id` ثابتًا للسجل المنطقي عبر revisions ولا يتغير لتجاوز تعارض target؛
- `revision_id` فريدًا لكل نسخة؛
- `parent_revision_id`، ويكون null للنسخة الأولى؛
- `supersedes_revision_id` عند التصحيح، ويطابق revision السابقة التي يحل محلها للاستخدام المستقبلي دون حذفها؛
- `financial_item_id` كانونيًا ثابتًا ومصدره سجل versioned؛
- `governed_target_ref` يشير إلى بند/مسار مالي allowlisted يمكن ربطه حتميًا بالـBaseline وReforecast؛
- `grain` صريحًا يحدد frequency والفترة ونطاق التجميع والأبعاد اللازمة، ولا تُقارن قيم ذات grain مختلف ضمنيًا؛
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
- خلط actual-to-date مع full-year actual دون دلالة؛
- دمج revisions متعارضة أو اختيار «الأحدث زمنيًا» وحده دون تحقق سلسلة الاعتماد.

قاعدة الهوية المنطقية: يبني الخادم `actual_logical_target_key` حتميًا من `(organization_id, project_id, parent_baseline_snapshot_id, financial_item_id, governed_target_ref, canonical_grain_hash, period_or_period_range)`. لا تدخل `actual_id` أو العملة أو الوحدة في المفتاح كي لا يسمح تغييرها بإنشاء سلسلة ثانية لنفس خانة النموذج؛ بل تتحقق العملة والوحدة مقابل تعريف target الحاكم.

يجب أن توجد سلسلة Actual واحدة فقط لكل `actual_logical_target_key`. محاولة إنشاء `actual_id` ثانٍ للمفتاح نفسه ترفض `BLOCKED/ACTUAL_LOGICAL_TARGET_CONFLICT` أو تعاد idempotently إلى السلسلة الموجودة وفق command خادمي صريح. داخل السلسلة يجب أن يوجد leaf واحد معتمد فقط في parent/supersedes chain الصحيحة، ويعتمد downstream ذلك الـleaf. إذا وجد أكثر من leaf معتمد أو parent مفقود/غير مطابق، تكون الحالة `BLOCKED/ACTUAL_REVISION_CONFLICT` ولا تُدمج القيم. تبقى كل revision سابقة immutable وقابلة للقراءة التاريخية.

### 7.2 Reforecast

يجب أن يعلن Reforecast:

- `parent_baseline_snapshot_id` إلزاميًا؛
- `predecessor_reforecast_snapshot_id`: null للنسخة الأولى فقط، وإلزامي لكل نسخة لاحقة؛
- `period_calendar_id` و`as_of_period` كانونيين، مع Actual معتمد لكل target مطلوب في الفترات `<= as_of_period` وforecast للفترات `> as_of_period` دون overlap/gap؛
- `approved_manifest_id` خادميًا؛
- `manifest_payload_hash` للحمولة normalized المعتمدة؛
- `manifest_validation_gate_id` خادميًا؛
- `manifest_validation_gate_payload_hash` لحالة gate ناجحة ومربوطة بنفس manifest ID/hash؛
- `finance_input_hash` كـcanonical hash لوثيقة `finance-model-input.v2` المغلقة؛
- `admission_input_hash` كـcanonical hash لسلسلة القبول الخادمية، وتشمل على الأقل organization/project، blueprint ID/hash، manifest ID/hash، gate ID/hash، normalized inputs، lifecycle type، parent IDs، `period_calendar_id/as_of_period`، scenario/policy/engine versions؛ ويبقى حقل `input_hash` في الغلاف الحالي مرادفًا موثقًا لـ`admission_input_hash` فقط؛
- actual revision IDs وlogical-target keys المستخدمة؛
- change set مع reason/evidence/approval؛
- التمويلات الجديدة أو المعدلة؛
- السياسات والإصدارات؛
- run/snapshot IDs الناتجة.

أي غياب أو mismatch أو عدم قابلية حل أو stale/expired في manifest/gate/parents/Actual bindings يرفض قبل Finance. إذا احتاج حمل حقول lifecycle الجديدة داخل الغلاف المجمد أو Snapshot Assembly إلى تغييرهما، فالقرار `STOP-THE-LINE` وبوابة مستقلة؛ لا يبرر العقد تجاوز المسار الحالي.

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
- تظهر الحالات نصيًا بالعربية ولا تعتمد على اللون وحده: `UNKNOWN = غير معروف`، و`NOT_APPLICABLE = غير منطبق`، و`NOT_READY = غير جاهز`، و`BLOCKED = محجوب`.
- Snapshot ID وrun ID وas-of period وحالة المراجعة ظاهرة في drill-down/report metadata.

---

## 9. الحاضنات والمسرعات وجهات التمويل

يجب تمثيل كل جهة أو برنامج عبر Profile مستقل محدود النطاق والزمن يحتوي:

- `institution_kind ∈ {LENDER, INCUBATOR, ACCELERATOR, GRANT_PROGRAM, OTHER_REVIEWED}`;
- اسم الجهة والبرنامج والإصدار وتاريخ السريان؛
- `scope ∈ {PUBLIC_REFERENCE, ORGANIZATION_OWNED}`؛
- `organization_id` إلزامي ومربوط خادميًا عندما يكون `scope=ORGANIZATION_OWNED`، ويكون null فقط للـ`PUBLIC_REFERENCE`؛
- `access_policy_id` وpolicy hash؛
- المصدر الرسمي وحالة freshness؛
- eligibility rules وdocument checklist؛
- متطلبات العرض والمؤشرات؛
- حالة من القاموس الحاكم نفسه في `FEASIBILITY-COMPLETE-01`: `reference_only` أو `source_verified` أو `professionally_validated` أو `institutionally_accepted` أو `expired`;
- حدود الادعاء.

لا ينشئ هذا العقد قاموسًا موازيًا. تنطبق الحالات نفسها على `LENDER` و`INCUBATOR` و`ACCELERATOR` و`GRANT_PROGRAM`، وتبقى `institutionally_accepted` محجوبة حتى وجود Evidence ID صالح يحدد الجهة والبرنامج/المنتج والإصدار والنطاق وتاريخ السريان.

قاعدة الوصول: Profile مملوك لا يقرأه إلا principal من `organization_id` نفسه بعد تحقق خادمي من `access_policy_id/hash`. Profile عام يكون read-only ولا يقبل private tenant evidence، ولا يصبح قابلًا للوصول إلا إذا كان registry-admitted و`source_verified` أو أعلى وغير `expired` وسياسة الوصول العامة صالحة. أي cross-tenant أو scope/owner/policy mismatch يفشل قبل القراءة أو المقارنة.

يحظر:

- تعميم متطلبات جهة على جميع الجهات؛
- الادعاء بالاعتماد أو القبول أو الشراكة دون Evidence ID صالح؛
- منح ASIE سلطة قرار ائتماني أو قبول حاضنة؛
- خلط Profile الجهة مع شروط التمويل الفعلية التي أدخلها المستخدم.

---

## 10. مصفوفة القبول الإلزامية

| ID | الحالة | معيار القبول |
|---|---|---|
| FLC-F1 | مشروع بلا دين | النموذج ready إذا اكتملت بقية المدخلات؛ DSCR/LLCR = `NOT_APPLICABLE/NO_DEBT_SERVICE` و`VALUE_ABSENT`؛ لا صفر ولا فشل |
| FLC-F1A | دين وبيانات تغطية غير مكتملة دون خرق | DSCR/LLCR = `NOT_READY`؛ يستخدم `CFADS_NOT_READY` أو `DEBT_SCHEDULE_NOT_READY` عند نقص واحد، و`CFADS_AND_DEBT_SCHEDULE_NOT_READY` عند نقصهما معًا، بنفس النتيجة عبر Finance/API/UI |
| FLC-F1B | دين وفشل validation/invariant/authorization | DSCR/LLCR = `BLOCKED` مع reason code المحدد نفسه عبر Finance/API/UI، ولا نتيجة جزئية |
| FLC-F2 | تمويل واحد مصرح به | شريحة واحدة فقط، نفس الشروط والlineage، لا ممول أو provenance مستنتج |
| FLC-F3 | عدة تمويلات مصرح بها | كل شريحة وسحب محفوظان وقابلان للـdrill-down؛ الإجمالي يطابق مجموع الجداول |
| FLC-F4 | سحب متأخر معروف في Baseline | يبدأ في الفترة المعلنة وتنعكس الفائدة/السداد دون نقله إلى البداية |
| FLC-F5 | تمويل جديد بعد Baseline | Baseline bytes/hash ثابتان؛ Reforecast جديد يحمل الشريحة والتغيير والparent IDs وmanifest/gate IDs+hashes؛ gate ناجحة ومربوطة بالmanifest؛ `finance_input_hash` و`admission_input_hash` يطابقان preimages المحددة قبل Finance |
| FLC-F6 | Actual مقابل Baseline | `actual_logical_target_key` خادمي صحيح؛ سلسلة واحدة فقط للمفتاح عبر tenant/project/Baseline/target/grain/period؛ `actual_id/revision_id` وparent/supersedes صالحة؛ leaf معتمد واحد؛ العملة والوحدة متوافقتان مع target؛ delta من نتائج محفوظة بلا إعادة حساب Snapshot |
| FLC-F6A | Actual duplicate logical target | إنشاء `actual_id` ثانٍ لنفس `actual_logical_target_key` يرفض حتميًا أو يعاد idempotently إلى السلسلة القائمة؛ لا double-count ولا اختيار بالأحدث زمنيًا |
| FLC-F7 | Reforecast متكرر | كل نسخة immutable ومرتبطة بـ`parent_baseline_snapshot_id` وبـ`predecessor_reforecast_snapshot_id` عند الانطباق، وبـmanifest/gate جديدين صالحين؛ hashا Finance/admission مطابقان؛ المقارنة حتمية |
| FLC-F7A | temporal splice | `period_calendar_id/as_of_period` ثابتان؛ كل target مطلوب للفترات المغلقة يأتي من Actual approved leaf، والمفتوحة من forecast؛ أي overlap أو gap أو calendar mismatch = `BLOCKED` قبل Finance |
| FLC-F8 | KPI chain | السلسلة `Summary → Drill-down → Comparison → Report` تستخدم metric object/projection envelope نفسه، وتعرض القيمة والحالة والأبعاد ومراجع artifacts/Snapshots نفسها دون إعادة حساب |
| FLC-F9 | حدود ERP | يقبل Actual summary ولا ينشئ GL/payroll/inventory/procurement transactions |
| FLC-F10 | Profile حاضنة/ممول | Profile محدد الإصدار والمصدر ويستخدم قاموس حالات FEASIBILITY-COMPLETE-01 نفسه؛ `institutionally_accepted` يحتاج Evidence ID صالحًا ولا ينشأ ادعاء قبول أو اعتماد بلا دليل |
| FLC-F11 | tenant isolation | artifact/comparison و`ORGANIZATION_OWNED` Profile يربطان خادميًا بنفس `organization_id`؛ cross-tenant وscope/owner/access-policy mismatch ترفض قبل القراءة أو الحساب؛ `PUBLIC_REFERENCE` يسمح به فقط وفق registry/status/freshness/policy الصريحة أعلاه |
| FLC-F12 | revision/tamper mismatch | hash أو manifest/parent/evidence/revision mismatch يفشل مغلقًا ولا ينتج Snapshot جزئيًا |
| FLC-F12A | metadata missing/null | غياب أو null لأي metadata إلزامية **لنمط lifecycle المحدد**، ومنها manifest/gate/revision/organization/policy IDs أو hashes، يفشل قبل Finance ولا ينتج Snapshot جزئيًا؛ Baseline الجذري يسمح فقط بالـparent null المصرح به |
| FLC-F12B | metadata unresolvable | ID أو parent أو evidence أو policy لا يمكن حله من المصدر الخادمي يفشل مغلقًا |
| FLC-F12C | metadata stale/expired | manifest/evidence/Profile/policy منتهي أو خارج freshness/effective window يفشل مغلقًا |
| FLC-F12D | manifest/gate/input binding | manifest ID/hash أو gate ID/hash أو رابط gate→manifest أو `finance_input_hash/admission_input_hash` غير متسق مع preimage الحاكمة يرفض قبل Finance |

الحد الأدنى للأدلة قبل أي claim:

- contract/schema tests؛
- unit/property tests لحالات F1–F7؛
- integration tests لمسار Approved Manifest → passed Manifest Validation Gate → Run → Snapshot، مع ID/hash binding؛
- API/projection tests لـF1A/F1B وF8 تثبت تطابق الحالة وreason code والأبعاد؛
- negative scope tests لـF9–F12D تشمل mismatch/missing/null/unresolvable/stale/expired؛
- fixtures مستقلة قابلة لإعادة الاستخدام؛
- exact-head CI وCross-Platform؛
- نجاح طبقات GitHub Codex وCodeRabbit وGitHub Copilot وPrincipal Independent Audit على exact head؛ وتبقى مراجعة Finance Reviewer/CPA البشرية مطلوبة قبل G1/claim المهني وفق ACR-FIN-002؛
- مراجعة Product Experience لعرض الحالات بالعربية وRTL؛
- rollback وعدم تغيير historical snapshots.

---

## 11. خريطة التتبع

| Outcome | Requirements | التنفيذ المتوقع | الاختبار | البوابة |
|---|---|---|---|---|
| دين اختياري صحيح | §5.1 + §6 | Finance contracts/results | FLC-F1 | Finance review |
| تمويل واحد/متعدد بلا استنتاج | §5.2–5.3 | input/result/subledger contracts | FLC-F2/F3 | G1 |
| تمويل منتصف العمر | §5.4 + §7 | revision/reforecast admission | FLC-F4/F5 | ACR/architecture |
| Baseline/Actual/Reforecast | §4 + §7 | versioned artifacts and snapshots | FLC-F5–F7 | Snapshot/freeze gate مستقل إذا لزم لمس مسار Snapshot المجمد؛ هذا PR لا ينفذه |
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
- مراجعة عدم التعارض مع ACR-FIN-002 وACR-DIB-001 وFreeze والبرامج الأب عبر طبقات المراجعة الفنية الأربع؛
- دمج هذا الملف من exact head؛
- لا claim تنفيذ.

### G-FLC-1 — Executable contracts ready

- schemas/versioning/applicability/lineage مغلقة؛
- fixtures F1–F12 موجودة؛
- نجاح GitHub Codex وCodeRabbit وGitHub Copilot وPrincipal Independent Audit على exact head لدخول dark implementation؛ ولا يحول ذلك إلى اعتماد CPA/G1؛
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
