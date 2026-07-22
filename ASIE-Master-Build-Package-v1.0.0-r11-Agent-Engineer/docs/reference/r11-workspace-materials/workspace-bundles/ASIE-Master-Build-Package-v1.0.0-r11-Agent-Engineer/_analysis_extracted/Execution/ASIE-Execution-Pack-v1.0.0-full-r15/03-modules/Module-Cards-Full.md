# Module Cards Full

## بطاقات الموديولات الكاملة

## Module Card Template

## قالب بطاقة الموديول

```text
Module:
Arabic:
Purpose:
Owns:
Does Not Own:
Inbound Contracts:
Outbound Contracts:
Data Tables:
Algorithms:
Failure Behavior:
Audit Events:
KIMI Build Tasks:
Acceptance Tests:
Forbidden Behavior:
```

## User / Auth Module

## موديول المستخدمين والمصادقة

Inbound Contracts:

العقود الداخلة:

- `auth.login.request.v1` / طلب دخول.
- `auth.session.validate.v1` / تحقق جلسة.

Outbound Contracts:

العقود الخارجة:

- `auth.claims.issued.v1` / إصدار Claims.
- `usage.entitlement.check.v1` / فحص الاستحقاق.

Data Tables:

جداول البيانات:

- `users` / المستخدمون.
- `sessions` / الجلسات.
- `roles` / الأدوار.
- `workspace_memberships` / عضويات مساحات العمل.

KIMI Build Tasks:

مهام بناء KIMI:

1. Implement auth session model / بناء نموذج الجلسة.
2. Emit claims through System Bus / إصدار Claims عبر ناقل النظام.
3. Add audit events for login, logout, failed login / إضافة تدقيق للدخول والخروج والفشل.
4. Reject expired or revoked sessions / رفض الجلسات المنتهية أو الملغاة.

Acceptance Tests:

اختبارات القبول:

- Expired session rejected / رفض الجلسة المنتهية.
- Role claim required for admin access / Claim الدور مطلوبة لدخول الإدارة.

## Project Wizard Module

## موديول معالج إنشاء المشروع

Inbound Contracts:

العقود الداخلة:

- `project.create.request.v1` / طلب إنشاء مشروع.
- `project.step.submit.v1` / إرسال خطوة.

Outbound Contracts:

العقود الخارجة:

- `market.geo.context.request.v1` / طلب سياق جغرافي.
- `market.query.request.v1` / طلب سوق.
- `market.strategy.alignment.requested.v1` / طلب مواءمة استراتيجية.
- `ai.classification.request.v1` / طلب تصنيف من AI.
- `finance.calculate.request.v1` / طلب حساب مالي.

Data Tables:

جداول البيانات:

- `projects` / المشاريع.
- `project_wizard_steps` / خطوات المعالج.
- `project_context_snapshots` / لقطات سياق المشروع.

Rules:

القواعد:

- Wizard must prefer choices over free text / المعالج يفضل الاختيارات على النص الحر.
- Free text must be limited and validated / النص الحر محدود ومتحقق.
- Location must come from GPS or Map Pin / الموقع من GPS أو Pin.

KIMI Build Tasks:

مهام بناء KIMI:

1. Build eight-step wizard state machine / بناء آلة حالة من 8 خطوات.
2. Add RTL Arabic labels / إضافة تسميات عربية RTL.
3. Add classification refresh / إضافة تحديث التصنيفات.
4. Block submit until required context is complete / منع الإرسال قبل اكتمال السياق.

## Market Intelligence Module

## موديول ذكاء السوق

Inbound Contracts:

العقود الداخلة:

- `market.query.request.v1`.
- `market.geo.context.request.v1`.
- `market.price.request.v1`.
- `market.govdata.fetch.v1` through `govdata.fetch.requested.v1`.
- `market.reference.link.v1` through `market.reference.link.save.requested.v1`.
- `market.strategy.reference.v1` through `market.strategy.alignment.requested.v1`.

Outbound Contracts:

العقود الخارجة:

- `market.evidence.pack.v1`.
- `market.price.sample.v1`.
- `market.geo.context.v1`.
- `market.source.health.v1`.
- `market.outlier.report.v1`.
- `govdata.fetch.completed.v1`.
- `govdata.fetch.blocked.v1`.
- `govdata.source.change.detected.v1`.
- `market.reference.link.saved.v1`.
- `market.reference.link.blocked.v1`.
- `market.strategy.alignment.pack.v1`.
- `market.strategy.reference.card.submit.requested.v1`.

Data Tables:

جداول البيانات:

- `market_sources` / مصادر السوق.
- `market_evidence_packs` / حزم الأدلة.
- `market_price_samples` / عينات الأسعار.
- `market_geo_contexts` / السياقات الجغرافية.
- `market_source_health` / صحة المصادر.
- `market_outlier_reports` / تقارير الشذوذ.
- `government_data_sources` / سجل مصادر ومجموعات البيانات الحكومية.
- `government_data_evidence_ledger` / سجل أدلة البيانات الحكومية.
- `market_reference_links` / روابط مرجعية خاصة بلا محتوى مجلوب.
- `official_strategy_reference_cards` / بطاقات مواءمة أصلية دون نسخ محتوى المصدر.

Algorithms:

الخوارزميات:

- Source Confidence Scoring / تقييم ثقة المصدر.
- Evidence Pack Assembly / بناء حزمة الأدلة.
- Price Outlier Filtering / فلترة الأسعار الشاذة.
- Geo Context Resolution / حل السياق الجغرافي.
- Open Government Data Source Discovery / اكتشاف مصادر البيانات الحكومية.
- Retrieval Runtime Guard / حارس الجلب وقت التشغيل.
- Content Integrity and Evidence Ledger / سلامة المحتوى وسجل الدليل.
- Strict Open-Data-Only Eligibility / أهلية البيانات المفتوحة فقط.
- Reference-Only Link Guard / حارس الرابط المرجعي فقط.
- Official Strategy Reference Registration / تسجيل المرجع الاستراتيجي.
- Original Synthesis and Compliance-Claim Guards / حارس الصياغة الأصلية وفصل ادعاءات الامتثال.

Forbidden:

الممنوع:

- No provider exposed outside module / لا يكشف أي مزود خارج الموديول.
- No Market Data Layer / لا Market Data Layer.
- No legal/privacy approval owned by Market Intelligence / لا يملك الموديول اعتماد الوصول القانوني أو الخصوصية.
- No blanket government-domain crawling / لا زحف عام على نطاقات الجهات الحكومية.
- No fetch without a current audited decision / لا جلب بلا قرار ساري ومدقق.
- Only exact official open datasets and open APIs may be enabled under `strict_open_data_only_v1`.
- Never fetch, preview, summarize, embed, score, or monitor a reference-only link, including Mostaql projects.
- Never store official strategy source text, screenshots, HTML, images, logos, copied lists, or embeddings.
- Strategy alignment packs use approved ASIE-authored cards only and cannot imply government endorsement.

## Finance Engine Module

## موديول محرك التمويل الحتمي

Inbound Contracts:

العقود الداخلة:

- `finance.calculate.request.v1`.
- `finance.sensitivity.request.v1`.
- `finance.mcmc.request.v1`.

Outbound Contracts:

العقود الخارجة:

- `finance.result.v1`.
- `finance.sensitivity.result.v1`.
- `finance.mcmc.result.v1`.
- `finance.blocking.missing.input.v1`.

Data Tables:

جداول البيانات:

- `finance_templates` / قوالب التمويل.
- `finance_runs` / تشغيلات التمويل.
- `finance_inputs` / مدخلات التمويل.
- `finance_outputs` / مخرجات التمويل.
- `finance_scenarios` / السيناريوهات.

Rules:

القواعد:

- Every number must have source / كل رقم له مصدر.
- Missing required input blocks calculation / نقص مدخل مطلوب يمنع الحساب.
- AI text cannot become numeric input / نص AI لا يصبح مدخلًا رقميًا.

## AI Advisory Module

## موديول الاستشارة بالذكاء الاصطناعي

Inbound Contracts:

العقود الداخلة:

- `ai.classification.request.v1`.
- `ai.advisory.request.v1`.
- `ai.rag.retrieve.request.v1`.
- `market.strategy.alignment.pack.v1`.

Outbound Contracts:

العقود الخارجة:

- `ai.classification.output.v1`.
- `ai.advisory.output.v1`.
- `ai.output.rejected.v1`.
- `market.strategy.alignment.requested.v1`.

Provider Policy:

سياسة المزودين:

- `Kimi K2.5` / Kimi للتحليل العميق المدفوع.
- `Llama 3.1 70B via Groq` / Llama للمهام السريعة الأساسية.
- `DeepSeek V3` / DeepSeek احتياطي.
- `Tavily` / Tavily للبحث.

Guard:

الحارس:

- Reject unsupported numbers / رفض الأرقام غير المدعومة.
- Require evidence references / طلب مراجع أدلة.
- Strategy alignment uses approved ASIE-authored cards only; source page content is excluded.
- Reject copied wording, reconstructed source text, legal-control substitution, and government-endorsement claims.

## Decision Council Module

## موديول مجلس القرار

Inbound Contracts:

العقود الداخلة:

- `decision.evaluate.request.v1`.

Outbound Contracts:

العقود الخارجة:

- `decision.validation.result.v1`.
- `decision.persona.output.v1`.
- `decision.result.v1`.
- `dashboard.project.readiness.result.v1`.
- `dashboard.confidence.breakdown.v1`.
- `dashboard.strategy.framework.pack.v1`.
- `dashboard.risk.register.v1`.
- `dashboard.investment.readiness.v1`.

Rules:

القواعد:

- Validation Gate runs first / بوابة التحقق تعمل أولًا.
- Personas receive same validated input / الشخصيات تستلم نفس المدخلات المتحققة.
- Consensus preserves dissent / الإجماع يحفظ الاعتراض.
- Readiness is an internal deterministic index, not probability of success or government approval.
- Strategic frameworks and risk synthesis cannot create unsupported finance inputs.

## Reports Module

## موديول التقارير

Contracts:

العقود:

- `report.generate.request.v1`.
- `report.generated.v1`.
- `market.strategy.alignment.requested.v1`.
- `market.strategy.alignment.pack.v1`.
- `reports.project.dashboard.view.v1`.
- `reports.project.run.compare.v1`.
- `audit.dashboard.output.lineage.v1` through an authorized request.

Rules:

القواعد:

- Reports display approved outputs only / التقارير تعرض المخرجات المعتمدة فقط.
- Reports do not recalculate / التقارير لا تعيد الحساب.
- Dashboard and export composition use the same approved output IDs and run.
- Reports cannot become a Dashboard Module or truth owner.

## Admin Module

## موديول الإدارة

Capabilities:

القدرات:

- Users / المستخدمون.
- Organizations / المنظمات.
- Workspaces / مساحات العمل.
- Subscriptions / الاشتراكات.
- Feature Flags / أعلام الخصائص.
- AI Providers / مزودو الذكاء.
- Coupons and credits / الكوبونات والرصيد.
- Security center / مركز الأمن.
- Audit logs / سجلات التدقيق.
- Government Data Source Registry / سجل مصادر البيانات الحكومية.
- Legal, Privacy/DPO, Cybersecurity, and Business review queue / طابور مراجعة المصدر.
- Connector suspension and kill switch / تعليق الموصل ومفتاح الإيقاف.
- Strict Open Data Allowlist and Reference-Only Registry / قائمة البيانات المفتوحة وسجل الروابط المرجعية.
- National Alignment Reference Registry and Originality Review Queue / سجل مراجع المواءمة وطابور مراجعة الأصالة.

Rule:

القاعدة:

Every admin mutation emits audit event.

كل تعديل إداري يصدر حدث تدقيق.

Admin displays and executes approved source state but cannot issue or override legal/privacy approval.

يعرض الآدمن حالة المصدر وينفذ التعليق، لكنه لا يعتمد مشروعية الوصول ولا يتجاوز قرار المنع.

## Audit / Observability Module

## موديول التدقيق والمراقبة

Capabilities:

القدرات:

- Domain events / أحداث المجال.
- OpenTelemetry / القياسات.
- Quarantine queue / طابور العزل.
- Alerts / التنبيهات.
- Health scoring / صحة النظام.
- Government-data policy gate / بوابة سياسة البيانات الحكومية.
- Dataset-level access decisions / قرارات الوصول لكل مجموعة أو نقطة اتصال.
- Legal, Privacy/DPO, Cybersecurity, and Business approval evidence / أدلة الاعتماد البشري المختص.
- Terms, license, classification, PDPL, transfer, and NCA applicability records / سجلات الامتثال.
- Strict-profile eligibility and immutable block reasons / أهلية الملف الصارم وأسباب المنع.
- Strategy-card accuracy, originality, non-endorsement, expiry, and withdrawal decisions / قرارات دقة وأصالة بطاقات المواءمة.
- Source suspension, revocation, incident response, and immutable decision audit / التعليق والإلغاء والحوادث والتدقيق غير القابل للعبث.

Inbound Contracts:

- `compliance.govdata.review.v1`.
- `audit.govdata.event.v1`.
- `compliance.strategy.reference.review.v1`.
- `audit.strategy.reference.event.v1`.

Outbound Contracts:

- `govdata.access.decision.issued.v1`.
- `govdata.audit.recorded.v1`.
- `market.strategy.reference.card.approved.v1`.
- `market.strategy.reference.card.rejected.v1`.
- `audit.strategy.reference.recorded.v1`.

Rules:

- Machine rules may deny automatically; final approval requires the configured authorized human reviewers.
- AI, Admin, Market Intelligence, and feature flags cannot issue or override approval.
- Missing or conflicting evidence results in deny and audit.

## Subscription / Usage Module

## موديول الاشتراكات والاستخدام

Capabilities:

القدرات:

- Free trial / التجربة المجانية.
- Usage limits / حدود الاستخدام.
- Plan checks / فحص الخطة.
- Consumption tracking / تتبع الاستهلاك.
- Billing provider abstraction / تجريد مزود الدفع.

## Professional Feasibility Responsibility Extension r15

This section does not create a new Module. It binds the professional feasibility workflow to existing owners.

| Existing Module | Added r15 responsibility | Must not do |
| --- | --- | --- |
| `Project Wizard` | Capture study purpose and select the minimum depth profile through `project.feasibility.profile.v1` | Calculate finance, approve law/forms, or downgrade required analysis |
| `Market Intelligence` | Produce market/commercial evidence and register procurement/methodology metadata through approved contracts | Treat a public page as open data, crawl Aljdwa, or make an official/legal claim |
| `Finance Engine` | Produce integrated statements, investment appraisal, working capital/funding, unit economics, debt metrics, economic analysis, scenarios, stress, sensitivity, and MCMC | Accept AI-generated numbers or directly access external sources |
| `Decision Council` | Apply chapter-completeness, cross-study reconciliation, procurement applicability, conditions, and final recommendation status | Recalculate owner outputs or treat a framework score as evidence |
| `AI Advisory` | Explain approved outputs and draft original Arabic/English narrative from approved cards and output envelopes | Browse Aljdwa, invent facts/numbers, choose assumptions, or issue approval/decision |
| `Reports` | Compose professional chapters, dashboard views, and exports with parity and lineage | Recalculate, fill missing values, or hide blocked chapters |
| `Audit / Observability` | Enforce official-form review, methodology-card review, rights restrictions, lineage, Zero Trust, and audit | Self-approve legal applicability or expose protected/raw content |
| `Admin` | Operate registries, review queues, suspension, version status, and policy configuration under MFA/RBAC | Override human legal/procurement review or re-enable a blocked source alone |

Required professional study chapter outputs are defined in `Professional-Feasibility-Study-and-Procurement-Reference-Framework.md`. All interactions use the socket and message catalogs; direct Module calls remain forbidden.
