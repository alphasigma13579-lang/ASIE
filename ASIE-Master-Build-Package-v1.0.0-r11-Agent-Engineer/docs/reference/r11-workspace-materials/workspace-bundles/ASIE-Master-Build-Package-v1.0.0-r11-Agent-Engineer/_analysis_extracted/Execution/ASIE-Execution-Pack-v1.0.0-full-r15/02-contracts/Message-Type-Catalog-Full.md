# Message Type Catalog Full

## كتالوج أنواع الرسائل الكامل

## Message Envelope

## غلاف الرسالة

All internal messages use this envelope.

كل الرسائل الداخلية تستخدم هذا الغلاف.

```json
{
  "message_id": "uuid",
  "message_type": "string",
  "source_module": "string",
  "target_contract": "string",
  "project_id": "string",
  "workspace_id": "string",
  "actor_id": "string",
  "created_at": "iso_datetime",
  "payload": {},
  "trace_id": "string"
}
```

## Required Validation

## التحقق المطلوب

1. `source_module` is registered / الموديول المصدر مسجل.
2. `target_contract` exists / العقد الهدف موجود.
3. Message type is allowed for contract / نوع الرسالة مسموح للعقد.
4. Payload matches schema / Payload يطابق Schema.
5. Actor has permission / الفاعل لديه صلاحية.

## Official Message Types

## أنواع الرسائل الرسمية

| Message Type | Arabic | Source | Target Contract |
| --- | --- | --- | --- |
| `auth.session.created.v1` | إنشاء جلسة | User / Auth | Audit |
| `auth.claims.issued.v1` | إصدار Claims | User / Auth | Zero Trust |
| `auth.human.challenge.requested.v1` | طلب تحقق إنسان | User / Auth | Audit |
| `auth.human.challenge.verified.v1` | نجاح تحقق الإنسان | User / Auth | Audit |
| `auth.mfa.enrollment.started.v1` | بدء تفعيل MFA | User / Auth | Audit |
| `auth.mfa.challenge.required.v1` | طلب تحدي MFA | User / Auth | UI / Audit |
| `auth.mfa.challenge.verified.v1` | نجاح تحدي MFA | User / Auth | Audit |
| `project.context.updated.v1` | تحديث سياق المشروع | Project Wizard | Audit |
| `project.classification.requested.v1` | طلب تصنيف دقيق | Project Wizard | AI Advisory |
| `sector.mapping.request.v1` | طلب ربط قطاع | Project Wizard | Market Intelligence |
| `sector.mapping.result.v1` | نتيجة ربط قطاع | Market Intelligence | Wizard / Finance / AI / Decision |
| `sector.investment.indicator.pack.v1` | حزمة مؤشرات الاستثمار | Market Intelligence | Finance / AI / Decision / Reports |
| `market.query.request.v1` | طلب سوق | Wizard / Finance / AI / Decision | Market Intelligence |
| `market.evidence.pack.v1` | حزمة أدلة | Market Intelligence | Finance / AI / Decision |
| `market.price.sample.v1` | عينة سعر | Market Intelligence | Finance |
| `market.outlier.report.v1` | تقرير شذوذ سعر | Market Intelligence | Finance / Audit |
| `market.geo.context.v1` | سياق جغرافي | Market Intelligence | Wizard / Finance |
| `market.public.evidence.pack.v1` | حزمة أدلة عامة | Market Intelligence | Finance / AI / Decision / Reports |
| `market.price.sample.pack.v1` | حزمة عينات أسعار | Market Intelligence | Finance / Reports |
| `market.similar.case.pack.v1` | حزمة تجارب مشابهة | Market Intelligence | AI / Decision / Reports |
| `market.regulatory.signal.pack.v1` | حزمة إشارات تنظيمية | Market Intelligence | Decision / Reports |
| `market.opportunity.signal.pack.v1` | حزمة إشارات فرص | Market Intelligence | Decision / Reports |
| `finance.calculate.request.v1` | طلب حساب مالي | Wizard / Decision | Finance Engine |
| `finance.result.v1` | نتيجة مالية | Finance Engine | Decision / Reports / AI |
| `finance.sensitivity.result.v1` | نتيجة حساسية | Finance Engine | Decision / Reports |
| `finance.mcmc.result.v1` | نتيجة MCMC | Finance Engine | Decision / Reports |
| `ai.advisory.request.v1` | طلب استشارة | Wizard / Decision / Reports | AI Advisory |
| `ai.advisory.output.v1` | مخرج استشارة | AI Advisory | Decision / Reports |
| `decision.evaluate.request.v1` | طلب تقييم قرار | Wizard / User | Decision Council |
| `decision.result.v1` | نتيجة قرار | Decision Council | Reports / UI |
| `report.generate.request.v1` | طلب تقرير | UI / Decision | Reports |
| `report.generated.v1` | تقرير مولد | Reports | UI / Audit |
| `feasibility.study.profile.select.requested.v1` | طلب اختيار عمق دراسة الجدوى | UI / Decision | Project Wizard |
| `feasibility.study.profile.selected.v1` | تحديد ملف عمق الدراسة | Project Wizard | Decision / Finance / Market / Reports |
| `feasibility.study.profile.blocked.v1` | تعذر تحديد ملف الدراسة | Project Wizard | UI / Audit |
| `feasibility.study.compose.requested.v1` | طلب تركيب دراسة الجدوى | UI / Reports | Decision Council |
| `feasibility.study.chapter.state.v1` | حالة فصل الدراسة | Decision Council | Reports / UI / Audit |
| `feasibility.study.reconciliation.result.v1` | نتيجة مطابقة فصول الدراسة | Decision Council | Reports / UI / Audit |
| `feasibility.study.composition.ready.v1` | جاهزية تركيب الدراسة | Decision Council | Reports / UI |
| `feasibility.study.composition.blocked.v1` | حجب تركيب الدراسة | Decision Council | Reports / UI / Audit |
| `finance.feasibility.advanced.calculate.requested.v1` | طلب حساب الجدوى المالية المتقدمة | Wizard / Decision | Finance Engine |
| `finance.integrated.statements.result.v1` | القوائم المالية المترابطة | Finance Engine | Decision / Reports |
| `finance.investment.appraisal.result.v1` | نتيجة التقييم الاستثماري | Finance Engine | Decision / Reports |
| `finance.working.capital.funding.result.v1` | رأس المال العامل والتمويل | Finance Engine | Decision / Reports |
| `finance.unit.economics.result.v1` | اقتصاديات الوحدة والتعادل | Finance Engine | Decision / Reports |
| `finance.debt.metrics.result.v1` | مؤشرات خدمة الدين | Finance Engine | Decision / Reports |
| `finance.economic.analysis.result.v1` | التحليل الاقتصادي للتكلفة والمنفعة | Finance Engine | Decision / Reports |
| `finance.uncertainty.analysis.result.v1` | السيناريوهات والضغط وعدم اليقين | Finance Engine | Decision / Reports |
| `finance.feasibility.advanced.blocked.v1` | حجب التحليل المالي المتقدم | Finance Engine | Decision / UI / Audit |
| `procurement.reference.review.requested.v1` | طلب مراجعة مرجع مشتريات | Admin / Market / Decision | Audit / Observability |
| `procurement.reference.approved.v1` | اعتماد المرجع للمسار المحدد | Audit / Observability | Decision / Reports / Admin |
| `procurement.reference.controlled.template.v1` | اعتماد قالب رسمي مضبوط | Audit / Observability | Decision / Reports / Admin |
| `procurement.reference.blocked.v1` | حجب مرجع المشتريات | Audit / Observability | Decision / Admin |
| `procurement.exact.documents.required.v1` | طلب مستندات المنافسة المحددة | Decision Council | UI / Reports / Audit |
| `methodology.card.review.requested.v1` | طلب مراجعة بطاقة منهجية أصلية | Market / Admin | Audit / Observability |
| `methodology.card.approved.v1` | اعتماد بطاقة منهجية أصلية | Audit / Observability | Market / AI / Decision / Reports |
| `methodology.card.rejected.v1` | رفض بطاقة منهجية | Audit / Observability | Market / Admin |
| `methodology.commercial.access.blocked.v1` | حجب وصول تجاري غير مصرح | Audit / Observability | Market / AI / Admin |
| `admin.policy.updated.v1` | تحديث سياسة | Admin | Audit / Runtime |
| `admin.incident.created.v1` | إنشاء حادث | Admin / Audit | Admin |
| `admin.incident.escalated.v1` | تصعيد حادث | Admin / Audit | Notification |
| `admin.maintenance.mode.updated.v1` | تحديث وضع الصيانة | Admin | Audit / Runtime |
| `usage.limit.checked.v1` | فحص حد الاستخدام | Subscription | Audit |
| `audit.quarantine.event.v1` | حدث عزل | Audit | Admin |
| `notification.preference.updated.v1` | تحديث تفضيلات التنبيه | User / Admin | Audit |
| `notification.delivery.requested.v1` | طلب إرسال تنبيه | Any authorized module | Notification |
| `notification.delivery.sent.v1` | إرسال تنبيه | Notification | Audit |
| `notification.delivery.failed.v1` | فشل إرسال تنبيه | Notification | Audit / Admin |
| `notification.in_app.created.v1` | إنشاء إشعار داخلي | Notification | UI |
| `analytics.event.ingested.v1` | استيعاب حدث تحليلي | Audit / Observability | Admin / Reports |
| `analytics.funnel.metric.v1` | مقياس قمع تحليلي | Audit / Observability | Admin |
| `analytics.dashboard.dataset.v1` | Dataset لوحة تحليلات | Audit / Observability | Admin / Reports |
| `govdata.source.discovered.v1` | اكتشاف مصدر بيانات حكومي | Market Intelligence | Audit / Observability |
| `govdata.access.review.requested.v1` | طلب مراجعة وصول حكومي | Admin / Market Intelligence | Audit / Observability |
| `govdata.access.decision.issued.v1` | إصدار قرار الوصول | Audit / Observability + authorized reviewer | Market Intelligence / Admin / Audit |
| `govdata.fetch.requested.v1` | طلب جلب بيانات حكومية | Authorized requester | Market Intelligence |
| `govdata.fetch.completed.v1` | اكتمال الجلب النظامي | Market Intelligence | Audit / approved consumer |
| `govdata.fetch.blocked.v1` | منع الجلب | Market Intelligence / Audit policy gate | Audit / Admin |
| `govdata.source.change.detected.v1` | اكتشاف تغير المصدر أو الشروط | Market Intelligence | Audit / Observability / Admin |
| `govdata.source.suspend.requested.v1` | طلب تعليق المصدر | Security / Legal / Privacy / Admin | Admin / Audit |
| `govdata.source.suspended.v1` | تعليق المصدر | Admin | Market Intelligence / Audit |
| `govdata.source.reapprove.requested.v1` | طلب إعادة اعتماد المصدر | Admin / Business owner | Audit / Observability policy gate |
| `govdata.audit.recorded.v1` | تسجيل حدث بيانات حكومية | Audit | Authorized requester |
| `govdata.strict_profile.evaluated.v1` | تقييم ملف البيانات المفتوحة الصارم | Audit / Observability | Market Intelligence / Admin |
| `govdata.open_source.enabled.v1` | تفعيل مصدر مفتوح محدد | Audit / Observability | Market Intelligence / Admin |
| `govdata.open_source.blocked.v1` | منع مصدر غير مؤهل | Audit / Observability | Market Intelligence / Admin |
| `market.reference.link.save.requested.v1` | طلب حفظ رابط مرجعي خاص | UI / Project Wizard | Market Intelligence |
| `market.reference.link.saved.v1` | حفظ رابط مرجعي دون جلبه | Market Intelligence | UI / Audit |
| `market.reference.link.blocked.v1` | منع رابط مرجعي غير صالح | Market Intelligence | UI / Audit |
| `market.strategy.reference.card.submit.requested.v1` | طلب مراجعة بطاقة مواءمة أصلية | Admin / Market Intelligence | Audit / Observability |
| `market.strategy.reference.card.approved.v1` | اعتماد بطاقة مواءمة أصلية | Audit / Observability | Market Intelligence / Admin |
| `market.strategy.reference.card.rejected.v1` | رفض بطاقة مواءمة | Audit / Observability | Market Intelligence / Admin |
| `market.strategy.alignment.requested.v1` | طلب مواءمة استراتيجية | Project Wizard / Reports / AI Advisory | Market Intelligence |
| `market.strategy.alignment.pack.v1` | حزمة مواءمة أصلية | Market Intelligence | Project Wizard / Reports / AI Advisory |
| `audit.strategy.reference.event.v1` | حدث تدقيق مرجع استراتيجي | Market Intelligence / Audit | Audit / Admin |
| `audit.strategy.reference.recorded.v1` | تسجيل حدث مرجع استراتيجي | Audit / Observability | Authorized requester |
| `dashboard.project.view.requested.v1` | طلب عرض لوحة المشروع | Authorized UI/API boundary | Reports |
| `dashboard.project.view.composed.v1` | تكوين عرض لوحة المشروع | Reports | Authorized UI/API boundary |
| `dashboard.project.view.blocked.v1` | منع عرض لوحة المشروع | Reports / Audit | Authorized UI/API boundary |
| `dashboard.output.presentation.decision.v1` | قرار صلاحية عرض المخرج | Audit / owner Module | Reports / UI |
| `dashboard.output.lineage.requested.v1` | طلب سلسلة إثبات المخرج | Authorized UI/API boundary | Audit / Observability |
| `dashboard.output.lineage.resolved.v1` | حل سلسلة إثبات المخرج | Audit / Observability | Authorized UI/API boundary |
| `dashboard.output.lineage.blocked.v1` | منع الوصول لسلسلة الإثبات | Audit / Observability | Authorized UI/API boundary |
| `dashboard.project.readiness.result.v1` | نتيجة جاهزية المشروع | Decision Council | Reports / UI |
| `dashboard.confidence.breakdown.v1` | تفصيل مؤشرات الثقة | Decision Council | Reports / UI |
| `dashboard.strategy.framework.pack.v1` | حزمة الأطر الاستراتيجية | Decision Council | Reports / UI |
| `dashboard.risk.register.v1` | سجل ومصفوفة المخاطر | Decision Council | Reports / UI |
| `dashboard.finance.scenario.compare.v1` | مقارنة السيناريوهات المالية | Finance Engine | Reports / UI |
| `dashboard.investment.readiness.v1` | جاهزية العرض الاستثماري | Decision Council | Reports / UI |
| `dashboard.section.state.v1` | حالة قسم لوحة المشروع | Owner Module / Audit | Reports / UI |
| `dashboard.localized.view.v1` | عرض محلي عربي أو إنجليزي | Reports | UI / Export |
| `dashboard.report.parity.result.v1` | نتيجة تطابق اللوحة والتقرير | Reports / Audit | UI / Audit |
| `dashboard.external.context.signal.v1` | إشارة سياق خارجي مقيدة | Market Intelligence | Reports / UI |
| `dashboard.legacy.reference.review.v1` | مراجعة استخدام مرجع الشاشة القديمة | Audit / Observability | Admin / Build gate |
| `dashboard.project.run.compare.requested.v1` | طلب مقارنة تشغيلات المشروع | Authorized UI/API boundary | Reports |
| `dashboard.project.run.compare.composed.v1` | تكوين مقارنة التشغيلات | Reports | Authorized UI/API boundary |
| `dashboard.project.run.compare.blocked.v1` | منع مقارنة التشغيلات | Reports / Audit | Authorized UI/API boundary |

## Forbidden Message Patterns

## أنماط رسائل ممنوعة

- `module.direct.call.*` / أي رسالة اتصال مباشر بين موديولات.
- `ai.generated.finance.number.*` / أي رسالة رقم مالي مولد من AI.
- `market.data.layer.*` / أي رسالة تشير إلى Market Data Layer.
- `cross.country.analysis.v1` / تحليل خارج السعودية في v1.
- `analytics.raw.pii.to.ai.*` / إرسال بيانات شخصية خام من التحليلات إلى AI.
- `analytics.as.finance.input.*` / استخدام التحليلات كمدخل مالي.
- `ai.unsourced.deep.research.claim.*` / ادعاء بحث عميق بلا مصدر.
- `ui.user.required.public.report.upload.*` / إجبار المستخدم على رفع تقرير عام.
- `notification.external.without.optin.*` / تنبيه خارجي بلا موافقة.
- `auth.mfa.secret.to.ai.*` / إرسال سر MFA إلى AI.
- `admin.maintenance.without.mfa.*` / صيانة إدارية بلا MFA.
- `govdata.fetch.without.current.approval.*` / جلب بيانات حكومية بلا اعتماد ساري.
- `govdata.domain.blanket.approval.*` / اعتماد كامل النطاق بدل مجموعة بيانات محددة.
- `govdata.captcha.or.access.bypass.*` / تجاوز CAPTCHA أو حماية الوصول.
- `govdata.unknown.classification.fetch.*` / جلب بيانات مجهولة التصنيف.
- `govdata.personal.data.to.ai.unapproved.*` / إرسال بيانات شخصية إلى AI بلا اعتماد.
- `govdata.denied.sharing.via.crawler.*` / استبدال مشاركة بيانات مرفوضة بالزحف.
- `govdata.registered.or.licensed.source.enabled.*` / تفعيل مصدر يحتاج تسجيلًا أو ترخيصًا خاصًا.
- `market.reference.link.backend.fetch.*` / جلب الخادم لمحتوى رابط مرجعي.
- `market.mostaql.content.ingested.*` / جمع أو تخزين محتوى مشاريع مستقل.
- `market.strategy.source.content.ingested.*` / إدخال النص أو الصور أو HTML من المرجع الاستراتيجي.
- `market.strategy.source.content.to.ai.*` / إرسال محتوى المرجع الرسمي إلى AI.
- `market.strategy.government.endorsement.claim.*` / ادعاء اعتماد أو موافقة حكومية من مرجع استراتيجي.
- `market.strategy.overview.as.compliance.control.*` / استخدام صفحة استراتيجية أو نظرة عامة كضابط امتثال رسمي.
- `dashboard.bare.numeric.output.*` / رقم لوحة بلا مالك أو عقد أو خوارزمية أو سلسلة إثبات.
- `dashboard.frontend.finance.calculation.*` / إعادة حساب التمويل داخل الواجهة.
- `dashboard.ai.generated.chart.value.*` / رقم شارت أو بطاقة مولد من AI.
- `dashboard.confidence.as.success.probability.*` / تحويل مؤشر الثقة إلى احتمال نجاح.
- `dashboard.legacy.value.migrated.*` / نقل قيمة أو ادعاء من شاشة قديمة.
- `dashboard.government.approved.without.proof.*` / ادعاء اعتماد حكومي بلا إثبات رسمي محدد.
- `dashboard.cross.project.output.*` / عرض مخرج من مشروع أو مساحة عمل أخرى.
- `dashboard.report.value.mismatch.*` / اختلاف قيمة التقرير عن اللوحة لنفس التشغيل.
