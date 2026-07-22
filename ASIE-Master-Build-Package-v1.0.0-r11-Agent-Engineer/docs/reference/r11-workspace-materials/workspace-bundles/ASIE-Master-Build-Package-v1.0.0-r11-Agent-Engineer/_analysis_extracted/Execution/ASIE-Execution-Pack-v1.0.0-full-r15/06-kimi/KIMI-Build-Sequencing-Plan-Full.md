# KIMI Build Sequencing Plan Full

## خطة تسلسل بناء KIMI الكاملة

## Stop Before Coding

## توقف قبل كتابة الكود

KIMI must first summarize:

يجب على KIMI أولًا تلخيص:

1. AAS boundaries / حدود AAS.
2. Module ownership / ملكية الموديولات.
3. Socket contracts / عقود السوكيت.
4. Message types / أنواع الرسائل.
5. Algorithm ownership / ملكية الخوارزميات.
6. Forbidden behavior / الممنوعات.
7. Dynamic chart ownership / ملكية الشارتات الديناميكية.
8. Acceptance tests / اختبارات القبول.

## Build Order

## ترتيب البناء

### Phase 0: Repository Baseline

### المرحلة 0: خط الأساس للمستودع

- Detect frontend/backend structure / اكتشاف هيكل الواجهة والخلفية.
- Do not rewrite working code / لا تعيد كتابة كود يعمل.
- Identify old architecture names / تحديد أسماء المعمارية القديمة.

### Phase 1: Contract Foundation

### المرحلة 1: أساس العقود

- Implement message envelope / تنفيذ غلاف الرسالة.
- Implement Socket Contract registry / تنفيذ سجل عقود السوكيت.
- Implement schema validation / تنفيذ تحقق Schema.
- Implement rejection and audit path / تنفيذ مسار الرفض والتدقيق.

### Phase 2: Auth, Subscription, Audit

### المرحلة 2: المصادقة والاشتراك والتدقيق

- User sessions / جلسات المستخدم.
- Claims / Claims الصلاحيات.
- Human verification / التحقق من الإنسان.
- Authenticator App MFA / MFA عبر Authenticator.
- Usage limits / حدود الاستخدام.
- Audit events / أحداث التدقيق.

### Phase 3: Project Wizard

### المرحلة 3: معالج المشروع

- Eight-step guided wizard / معالج موجه من 8 خطوات.
- RTL Arabic UI / واجهة عربية RTL.
- GPS / Map Pin / GPS أو Pin.
- Sector taxonomy selection / اختيار تصنيف القطاع.
- Subsector and activity mapping / ربط التصنيف الفرعي والنشاط.
- Classification generation through AI contract / توليد التصنيف عبر عقد AI.

### Phase 4: Market Intelligence

### المرحلة 4: ذكاء السوق

- Source registry / سجل المصادر.
- External intelligence source framework / إطار مصادر الذكاء الخارجية.
- Public evidence auto fetch / الجلب التلقائي للأدلة العامة.
- Deep research worker contracts / عقود عامل البحث العميق.
- Similar case discovery / اكتشاف التجارب المشابهة.
- Evidence pack builder / باني حزمة الأدلة.
- Price sample handling / معالجة عينات الأسعار.
- Geo context / السياق الجغرافي.
- Outlier report / تقرير الشذوذ.

### Phase 5: Finance Engine

### المرحلة 5: محرك التمويل

- Deterministic templates / قوالب حتمية.
- CapEx / OpEx rules / قواعد CapEx و OpEx.
- Sensitivity / الحساسية.
- MCMC with seed / MCMC ببذرة.

### Phase 6: AI Advisory

### المرحلة 6: الاستشارة بالذكاء الاصطناعي

- Model routing / توجيه النماذج.
- Output guard / حارس المخرجات.
- RAG retrieval / استرجاع RAG.
- Evidence-bound summaries / ملخصات مرتبطة بالأدلة.

### Phase 7: Decision Council

### المرحلة 7: مجلس القرار

- Validation gate / بوابة التحقق.
- Five personas / الشخصيات الخمس.
- Consensus scoring / حساب الإجماع.
- Dissent preservation / حفظ الاعتراض.

### Phase 8: Reports and Admin

### المرحلة 8: التقارير والإدارة

- Reports / التقارير.
- Admin console / لوحة الإدارة.
- Advanced operations center / مركز العمليات المتقدم.
- Incident management / إدارة الحوادث.
- Maintenance controls / تحكم الصيانة.
- Feature flags / أعلام الخصائص.
- Security center / مركز الأمن.

### Phase 8B: Notifications

### المرحلة 8B: التنبيهات

- In-app notification center / مركز الإشعارات داخل المنصة.
- Notification preference center / مركز تخصيص التنبيهات.
- WhatsApp notification adapter / موصل تنبيهات واتساب.
- Telegram notification adapter / موصل تنبيهات تليجرام.
- Delivery audit / تدقيق التسليم.

### Phase 9: Smart Site Visual Analytics

### المرحلة 9: التحليلات المرئية للموقع الذكي

- Dynamic chart registry / سجل الشارتات الديناميكية.
- Chart dataset contracts / عقود بيانات الشارتات.
- Product analytics adapters / موصلات تحليلات المنتج.
- Google Analytics adapter / موصل تحليلات جوجل.
- Zoho Analytics adapter / موصل تحليلات زوهو.
- Market charts / شارتات السوق.
- Finance charts / شارتات التمويل.
- Decision charts / شارتات القرار.
- Admin and observability charts / شارتات الإدارة والمراقبة.
- RTL chart labels and Arabic number formatting / تسميات RTL وتنسيق الأرقام العربي.
- Empty, loading, error, insufficient data states / حالات الفراغ والتحميل والخطأ ونقص البيانات.

### Phase 9B: Project Intelligence Dashboard

### المرحلة 9B: لوحة ذكاء المشروع

- Read `KIMI-Project-Dashboard-Build-Prompt.md` before implementation.
- Build the fourteen canonical project routes without creating a Dashboard Module.
- Implement the universal output envelope and project-scoped authorization first.
- Build readiness, confidence decomposition, strategic frameworks, market evidence, finance, risk, scenarios, Decision Council, execution, investment, evidence, and report views.
- Enforce `DASH-ALG-01` through `DASH-ALG-12`.
- Verify dashboard/report parity and the legacy-screenshot migration guard.
- Run Arabic RTL and English LTR desktop/mobile visual acceptance.

## Stop Rules

## قواعد التوقف

KIMI must stop if:

يجب على KIMI التوقف إذا:

- A needed socket contract is missing / عقد سوكيت مطلوب غير موجود.
- A needed algorithm is missing / خوارزمية مطلوبة غير موجودة.
- A component boundary is unclear / حد مكون غير واضح.
- The implementation requires a new layer, bus, controller, or heart / التنفيذ يحتاج طبقة أو ناقل أو متحكم أو قلب جديد.
- A chart needs data not owned by any module / الشارت يحتاج بيانات لا يملكها أي موديول.
- A chart would require AI-generated numeric data / الشارت يتطلب أرقامًا مولدة من AI.
- Analytics data would expose raw PII to AI / بيانات التحليلات ستكشف PII خام إلى AI.
- Analytics data is being used as finance evidence / بيانات التحليلات تستخدم كدليل مالي.
- The implementation asks the user to upload public reports / التنفيذ يطلب من المستخدم رفع تقارير عامة.
- Deep research output has no source link / مخرج البحث العميق بلا رابط مصدر.
- Human verification is missing from signup or suspicious login / تحقق الإنسان مفقود من التسجيل أو الدخول المشبوه.
- Admin or maintenance actions bypass MFA / إجراءات الإدارة أو الصيانة تتجاوز MFA.
- WhatsApp or Telegram alerts are sent without opt-in / تنبيهات واتساب أو تليجرام ترسل بلا موافقة.
- A dashboard number lacks owner, contract, algorithm, formula, evidence/assumption, unit, period, run, or timestamp.
- The implementation creates a Dashboard Module, performs frontend finance calculation, or lets AI generate chart values.
- Confidence is presented as probability of success, or a named scenario receives an invented probability.
- A government-approved label lacks exact official form evidence.
- A legacy screenshot value, name, claim, map, or wording is reused as production truth.

## r15 Professional Feasibility Build Increment

Build only after the frozen AAS contracts, message flow, Zero Trust, and existing Module boundaries are understood.

1. Add schemas and enums for study profiles, chapter states, financial conventions, procurement references, and methodology cards.
2. Implement `FST-ALG-01` through `FST-ALG-03` in their existing owners.
3. Implement `FIN-ALG-06` through `FIN-ALG-12` in Finance Engine with deterministic fixtures and reconciliation tests.
4. Implement `PROC-ALG-01`, `PROC-ALG-02`, `METH-ALG-01`, and `METH-ALG-02` in the owners stated by the catalog.
5. Add the three r15 routes to the existing project dashboard shell; do not create a Dashboard or Feasibility Module.
6. Add controlled registry/review queues to Admin under MFA, RBAC, audit, separation of duties, and kill switch.
7. Add Arabic/English report composition and visual states with no example value treated as production data.
8. Run all r15 acceptance tests before enabling any source, official-form workflow, or completion badge.

Stop and ask when a formula, convention, tax/Zakat applicability, social discount rate, official-form version, competition document, rights permission, or owner contract is unspecified.
