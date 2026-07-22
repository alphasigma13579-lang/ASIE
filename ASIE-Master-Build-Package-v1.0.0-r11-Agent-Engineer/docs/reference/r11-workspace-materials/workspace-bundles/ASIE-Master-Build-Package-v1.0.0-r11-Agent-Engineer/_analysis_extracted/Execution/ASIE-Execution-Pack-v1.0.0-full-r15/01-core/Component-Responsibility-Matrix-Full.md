# Component Responsibility Matrix Full

## مصفوفة مسؤوليات المكونات الكاملة

## Format

## الصيغة

Each component is defined by:

كل مكون يعرف عبر:

- Purpose / الهدف.
- Owns / يملك.
- Does Not Own / لا يملك.
- Inputs / المدخلات.
- Outputs / المخرجات.
- Allowed Calls / الاتصالات المسموحة.
- Forbidden Calls / الاتصالات الممنوعة.
- Data Authority / سلطة البيانات.
- Failure Behavior / سلوك الفشل.
- Audit Events / أحداث التدقيق.
- KIMI Build Notes / ملاحظات بناء KIMI.

## 1. User / Auth Module

## موديول المستخدمين والمصادقة

Purpose:

الهدف:

Manage identity, sessions, roles, workspaces, and access claims.

إدارة الهوية، الجلسات، الأدوار، مساحات العمل، وClaims الوصول.

Owns:

يملك:

- User profile / ملف المستخدم.
- Authentication session / جلسة المصادقة.
- Role membership / عضوية الدور.
- Workspace membership / عضوية مساحة العمل.
- Permission claims emitted to Zero Trust evaluation / Claims الصلاحيات المرسلة لتقييم الأمن الصفري.
- Human verification challenge state / حالة تحدي التحقق من الإنسان.
- Authenticator App MFA enrollment / تفعيل MFA عبر Authenticator.
- TOTP recovery codes / رموز استرداد TOTP.

Does Not Own:

لا يملك:

- Subscription limits / حدود الاشتراك.
- Admin policy / سياسات الإدارة.
- Finance numbers / الأرقام المالية.
- Market evidence / أدلة السوق.

Inputs:

المدخلات:

- Login credentials / بيانات الدخول.
- OAuth or provider identity / هوية مزود الدخول.
- Workspace selection / اختيار مساحة العمل.

Outputs:

المخرجات:

- `auth.session.created.v1` / إنشاء جلسة.
- `auth.claims.issued.v1` / إصدار Claims.
- `auth.session.revoked.v1` / إلغاء جلسة.

Allowed Calls:

الاتصالات المسموحة:

- Send auth state through System Bus / إرسال حالة المصادقة عبر ناقل النظام.
- Request subscription entitlement through contract / طلب استحقاق الاشتراك عبر عقد.

Forbidden Calls:

الاتصالات الممنوعة:

- Direct access to Finance Engine / اتصال مباشر بمحرك التمويل.
- Direct write to Admin settings / كتابة مباشرة لإعدادات الإدارة.

Failure Behavior:

سلوك الفشل:

- Invalid session returns `AUTH_REJECTED`.
- الجلسة غير الصحيحة ترجع `AUTH_REJECTED`.

- Suspicious login emits audit event.
- الدخول المشبوه يصدر حدث تدقيق.

- Bot or abuse suspicion triggers human verification.
- الاشتباه بروبوت أو إساءة يفعّل تحقق الإنسان.

## 2. Project Wizard Module

## موديول معالج إنشاء المشروع

Purpose:

الهدف:

Collect controlled project context through guided steps.

جمع سياق المشروع عبر خطوات موجهة.

Owns:

يملك:

- Wizard step state / حالة خطوات المعالج.
- User-selected sector / القطاع المختار.
- Precise classification selection / اختيار التصنيف الدقيق.
- GPS or map pin context request / طلب سياق GPS أو Pin.
- Project size selection / اختيار حجم المشروع.

Does Not Own:

لا يملك:

- Market data retrieval / جلب بيانات السوق.
- Finance calculations / الحسابات المالية.
- Final decision / القرار النهائي.

Required Steps:

الخطوات المطلوبة:

1. General idea / فكرة عامة.
2. Sector / القطاع.
3. Precise classification / التصنيف الدقيق.
4. Location via GPS or Map Pin / الموقع عبر GPS أو Pin.
5. Target audience / الجمهور المستهدف.
6. Problem and differentiation / المشكلة والتمييز.
7. Project size and constraints / الحجم والقيود.
8. Review and submit / المراجعة والإرسال.

Forbidden:

الممنوع:

- Free city text as location source / إدخال المدينة نصيًا كمصدر موقع.
- Sending raw prompt to AI without contract guard / إرسال Prompt خام إلى AI بلا حارس عقد.

## 3. Market Intelligence Module

## موديول ذكاء السوق

Purpose:

الهدف:

Own all market source access, evidence packs, price samples, geo context, source health, and outlier reports.

امتلاك كل الوصول لمصادر السوق، حزم الأدلة، عينات الأسعار، السياق الجغرافي، صحة المصادر، وتقارير الشذوذ.

Owns:

يملك:

- `market.query.request.v1` handling / معالجة طلبات السوق.
- Source adapters behind contracts / موصلات المصادر خلف العقود.
- Evidence Pack Builder / باني حزم الأدلة.
- Price outlier reports / تقارير الأسعار الشاذة.
- Geo context / السياق الجغرافي.
- Source health / صحة المصادر.

Does Not Own:

لا يملك:

- Finance formulas / معادلات التمويل.
- AI final explanation / شرح AI النهائي.
- UI display logic / منطق عرض الواجهة.

Forbidden:

الممنوع:

- Exposing providers directly to UI, AI, Plugin, Module, or Finance Engine.
- كشف مزودي البيانات مباشرة للواجهة أو AI أو Plugin أو Module أو Finance Engine.

- Using `Market Data Layer`.
- استخدام `Market Data Layer`.

## 4. Finance Engine Module

## موديول محرك التمويل الحتمي

Purpose:

الهدف:

Own deterministic financial computation and scenario calculation.

امتلاك الحسابات المالية الحتمية وحساب السيناريوهات.

Owns:

يملك:

- CapEx / OpEx classification rules / قواعد تصنيف CapEx و OpEx.
- Baseline finance calculation / الحساب المالي الأساسي.
- Sensitivity analysis / تحليل الحساسية.
- MCMC simulation with fixed seed / محاكاة MCMC ببذرة ثابتة.
- Break-even, ROI, cash flow / نقطة التعادل، العائد، التدفق النقدي.

Does Not Own:

لا يملك:

- Market source access / الوصول لمصادر السوق.
- AI text generation / توليد النص بالذكاء.
- Subscription billing / فوترة الاشتراكات.

Forbidden:

الممنوع:

- Accepting AI-generated numbers / قبول أرقام مولدة من AI.
- Calling providers directly / الاتصال المباشر بالمزودين.

## 5. AI Advisory Module

## موديول الاستشارة بالذكاء الاصطناعي

Purpose:

الهدف:

Provide explanations, summaries, classifications, advisory narratives, and model routing under strict limits.

تقديم الشرح، التلخيص، التصنيف، النصائح، وتوجيه النماذج ضمن حدود صارمة.

Owns:

يملك:

- Model routing / توجيه النماذج.
- Advisory prompt templates / قوالب Prompt الاستشارية.
- RAG retrieval requests / طلبات RAG.
- Output guard / حارس المخرجات.

Does Not Own:

لا يملك:

- Deterministic numbers / الأرقام الحتمية.
- Final decision authority / سلطة القرار النهائي.
- Market source truth / حقيقة مصادر السوق.

Forbidden:

الممنوع:

- Inventing numbers / اختراع الأرقام.
- Replacing Finance Engine / استبدال محرك التمويل.
- Bypassing Evidence Pack / تجاوز حزمة الأدلة.

## 6. Decision Council Module

## موديول مجلس القرار

Purpose:

الهدف:

Run validation gate, collect persona outputs, compute consensus, and preserve dissent.

تشغيل بوابة التحقق، جمع مخرجات الشخصيات، حساب الإجماع، وحفظ الاعتراضات.

Owns:

يملك:

- Validation Gate / بوابة التحقق.
- Five Sovereign Personas protocol / بروتوكول الشخصيات السيادية الخمس.
- Vote mapping / خريطة الأصوات.
- Consensus score / درجة الإجماع.
- Final decision object / كائن القرار النهائي.

Forbidden:

الممنوع:

- Approving without evidence pack / الموافقة بدون حزمة أدلة.
- Hiding minority objection / إخفاء اعتراض الأقلية.

## 7. Reports Module

## موديول التقارير

Purpose:

الهدف:

Generate structured user-facing reports from approved outputs.

إنتاج تقارير منظمة للمستخدم من المخرجات المعتمدة.

Owns:

يملك:

- Report templates / قوالب التقارير.
- Executive summary composition / تركيب الملخص التنفيذي.
- Export packaging / تغليف التصدير.

Does Not Own:

لا يملك:

- Changing calculations / تعديل الحسابات.
- Changing final decision / تعديل القرار النهائي.

## 8. Admin Module

## موديول الإدارة

Purpose:

الهدف:

Manage platform policies, users, feature flags, subscriptions override, and operational controls.

إدارة سياسات المنصة، المستخدمين، Feature Flags، تجاوزات الاشتراكات، والتحكم التشغيلي.

Owns:

يملك:

- Feature flags / أعلام الخصائص.
- User administration / إدارة المستخدمين.
- Coupon and credit operations / الكوبونات والرصيد.
- Provider policy configuration / إعداد سياسات المزودين.
- Advanced operations dashboard / لوحة العمليات المتقدمة.
- Maintenance mode / وضع الصيانة.
- Incident management / إدارة الحوادث.
- Admin role workspaces / مساحات عمل الإدارة حسب الدور.

Forbidden:

الممنوع:

- Silent override without audit / تجاوز صامت بلا تدقيق.

## 9. Audit / Observability Module

## موديول التدقيق والمراقبة

Purpose:

الهدف:

Own audit events, telemetry, health, quarantine, and security observation.

امتلاك أحداث التدقيق، Telemetry، صحة النظام، العزل، والمراقبة الأمنية.

Owns:

يملك:

- Audit log / سجل التدقيق.
- Telemetry events / أحداث Telemetry.
- Quarantine queue / طابور العزل.
- Health scoring / حساب صحة النظام.
- Product analytics ingestion / استيعاب تحليلات المنتج.
- Google Analytics Adapter / موصل تحليلات جوجل.
- Zoho Analytics Adapter / موصل تحليلات زوهو.
- Notification delivery events / أحداث تسليم التنبيهات.
- Incident and on-call events / أحداث الحوادث والمناوبة.

## 10. Subscription / Usage Module

## موديول الاشتراكات والاستخدام

Purpose:

الهدف:

Own plans, usage limits, trial cooldown, consumption tracking, and billing state.

امتلاك الخطط، حدود الاستخدام، تهدئة التجربة، تتبع الاستهلاك، وحالة الفوترة.

Owns:

يملك:

- Trial limits / حدود التجربة.
- Usage counters / عدادات الاستخدام.
- Plan entitlement / استحقاق الخطة.
- Billing state / حالة الفوترة.

Forbidden:

الممنوع:

- Letting AI grant credits / السماح للذكاء بمنح رصيد.
