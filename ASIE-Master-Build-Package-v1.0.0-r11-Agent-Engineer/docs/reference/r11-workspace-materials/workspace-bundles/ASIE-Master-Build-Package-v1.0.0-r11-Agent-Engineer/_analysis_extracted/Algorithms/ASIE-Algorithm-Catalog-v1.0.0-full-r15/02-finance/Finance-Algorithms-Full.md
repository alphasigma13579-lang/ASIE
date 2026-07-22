# Finance Algorithms Full

## خوارزميات التمويل الكاملة

Owner:

المالك:

`Finance Engine Module` / موديول محرك التمويل الحتمي.

## FIN-ALG-01 Deterministic Finance Calculation

## الحساب المالي الحتمي

Purpose:

الهدف:

Calculate financial outputs using verified inputs and approved formulas.

حساب المخرجات المالية باستخدام مدخلات موثقة ومعادلات معتمدة.

Input Requirements:

متطلبات المدخلات:

- Every number has source id / كل رقم له معرف مصدر.
- Every money value has currency / كل قيمة مالية لها عملة.
- Every quantity has unit / كل كمية لها وحدة.
- Evidence pack exists / حزمة الأدلة موجودة.
- Project size selected / حجم المشروع مختار.

Core Outputs:

المخرجات الأساسية:

- Startup cost / تكلفة التأسيس.
- Monthly operating cost / تكلفة التشغيل الشهرية.
- Revenue estimate from approved inputs / تقدير الإيراد من مدخلات معتمدة.
- Gross margin / هامش الربح الإجمالي.
- Net profit / صافي الربح.
- Cash flow / التدفق النقدي.
- Break-even point / نقطة التعادل.
- ROI / العائد على الاستثمار.

Steps:

الخطوات:

1. Validate required inputs.
2. Classify costs using `FIN-ALG-02`.
3. Apply approved template by project size.
4. Calculate baseline.
5. Run required checks for missing or inconsistent units.
6. Produce source map for every output.
7. Emit `finance.result.v1`.

Forbidden:

الممنوع:

- AI-generated numbers.
- أرقام مولدة من AI.

## FIN-ALG-02 CapEx / OpEx Classification

## تصنيف CapEx و OpEx

Purpose:

الهدف:

Classify financial inputs as capital or operating expenses.

تصنيف المدخلات المالية إلى مصاريف رأسمالية أو تشغيلية.

Rules:

القواعد:

- One-time setup asset = CapEx / أصل تأسيسي مرة واحدة = CapEx.
- Monthly recurring expense = OpEx / تكلفة شهرية متكررة = OpEx.
- Rent deposit = CapEx or prepayment by template / التأمين الإيجاري حسب القالب.
- Salaries = OpEx / الرواتب OpEx.
- Equipment = CapEx / المعدات CapEx.
- Subscription software = OpEx unless prepaid asset / البرمجيات الاشتراكية OpEx إلا إذا كانت أصلًا مدفوعًا مقدمًا.

AI Role:

دور الذكاء:

AI may suggest classification from text, but Finance Engine must validate rules.

يجوز للذكاء اقتراح التصنيف من النص، لكن محرك التمويل يتحقق بالقواعد.

## FIN-ALG-03 Sensitivity Analysis

## تحليل الحساسية

Purpose:

الهدف:

Measure impact of controlled changes.

قياس أثر تغييرات مضبوطة.

Mandatory Axes:

المحاور الإلزامية:

1. Revenue decrease / انخفاض الإيرادات.
2. Cost increase / ارتفاع التكاليف.
3. Demand or occupancy change / تغير الطلب أو الإشغال.

Steps:

الخطوات:

1. Load baseline result.
2. Apply one axis at a time.
3. Recalculate same formulas.
4. Compare against baseline.
5. Return risk level and changed metrics.

Stop:

توقف:

No baseline, no sensitivity.

لا تحليل حساسية بلا خط أساس.

## FIN-ALG-04 MCMC Simulation

## محاكاة مونت كارلو

Purpose:

الهدف:

Estimate risk distribution under controlled uncertainty.

تقدير توزيع المخاطر تحت عدم يقين مضبوط.

Requirements:

المتطلبات:

- Deterministic baseline / خط أساس حتمي.
- Approved ranges / نطاقات معتمدة.
- Fixed seed / بذرة ثابتة.
- Iteration count from admin policy / عدد التكرارات من سياسة الإدارة.
- Distribution policy from Finance Engine configuration / سياسة التوزيعات من إعدادات محرك التمويل.
- Source map for every variable range / خريطة مصدر لكل نطاق متغير.

Allowed Variable Families:

عائلات المتغيرات المسموحة:

- Revenue variability / تذبذب الإيرادات.
- Cost variability / تذبذب التكاليف.
- Demand or occupancy variability / تذبذب الطلب أو الإشغال.
- Price variability from validated samples / تذبذب السعر من عينات صحيحة.

Forbidden Variable Sources:

مصادر المتغيرات الممنوعة:

- AI guesses / تخمينات AI.
- Unsourced assumptions / افتراضات بلا مصدر.
- Analytics usage events / أحداث استخدام التحليلات.

Steps:

الخطوات:

1. Validate baseline.
2. Validate ranges and distributions.
3. Set fixed seed.
4. Run simulation.
5. Produce probability bands.
6. Store seed, ranges, and result.
7. Produce histogram dataset / إنتاج Dataset المدرج التكراري.
8. Produce percentile table / إنتاج جدول Percentiles.
9. Emit audit event with seed and config / إصدار حدث تدقيق بالبذرة والإعدادات.

Outputs:

المخرجات:

- `finance.mcmc.result.v1`.
- Histogram bins / سلال المدرج التكراري.
- Percentiles P5, P25, P50, P75, P95 / Percentiles.
- Downside risk probability / احتمال الخطر الهابط.
- Seed and run configuration / البذرة وإعدادات التشغيل.

Forbidden:

الممنوع:

- AI chooses ranges.
- AI يختار النطاقات.

- Product analytics data becomes finance uncertainty input.
- بيانات تحليلات المنتج تصبح مدخل عدم يقين مالي.

## FIN-ALG-05 Supplier Quote Parsing Gate

## بوابة تحليل عروض الموردين

Purpose:

الهدف:

Parse PDF/Excel supplier offers into controlled structured inputs.

تحليل عروض الموردين PDF/Excel إلى مدخلات منظمة.

Extracted Fields:

الحقول المستخرجة:

- Supplier name / اسم المورد.
- Item name / اسم البند.
- Quantity / الكمية.
- Unit / الوحدة.
- Unit price / سعر الوحدة.
- Currency / العملة.
- VAT / الضريبة.
- Validity date / تاريخ الصلاحية.

Rules:

القواعد:

- Missing price rejects row / نقص السعر يرفض الصف.
- Missing unit rejects row / نقص الوحدة يرفض الصف.
- Expired quote requires review / العرض المنتهي يحتاج مراجعة.
- Extracted numeric values must match document text / الأرقام المستخرجة تطابق نص المستند.
