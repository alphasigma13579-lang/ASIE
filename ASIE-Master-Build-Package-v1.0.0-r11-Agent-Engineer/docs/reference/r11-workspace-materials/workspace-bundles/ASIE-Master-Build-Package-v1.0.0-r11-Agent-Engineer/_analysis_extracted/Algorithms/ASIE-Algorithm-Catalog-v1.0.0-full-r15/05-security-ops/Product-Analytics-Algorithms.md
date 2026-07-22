# Product Analytics Algorithms

## خوارزميات تحليلات المنتج

Owner:

المالك:

`Audit / Observability Module` / موديول التدقيق والمراقبة, with `Admin Module` / موديول الإدارة for dashboards.

## AN-ALG-01 Product Analytics Ingestion

## استيعاب تحليلات المنتج

Purpose:

الهدف:

Ingest events from Google Analytics and Zoho Analytics into ASIE-controlled observability.

استيعاب أحداث Google Analytics وZoho Analytics داخل مراقبة ASIE المضبوطة.

Allowed Adapters:

الموصلات المسموحة:

- `Google Analytics Adapter` / موصل تحليلات جوجل.
- `Zoho Analytics Adapter` / موصل تحليلات زوهو.

Inputs:

المدخلات:

- Event name / اسم الحدث.
- Timestamp / الوقت.
- Anonymous user key / مفتاح مستخدم مجهول.
- Workspace id / معرف مساحة العمل.
- Page or feature key / مفتاح الصفحة أو الخاصية.
- Aggregated properties / خصائص مجمعة.

Steps:

الخطوات:

1. Receive event from approved adapter.
2. Validate adapter identity.
3. Remove or hash personal identifiers.
4. Normalize event name.
5. Attach workspace and feature context.
6. Store as `analytics.event.ingested.v1`.
7. Emit audit event for ingestion failures.

Forbidden:

الممنوع:

- Raw PII to AI / إرسال PII خام إلى AI.
- Product analytics as market evidence / تحليلات المنتج كدليل سوق.
- Product analytics as finance input / تحليلات المنتج كمدخل مالي.

## AN-ALG-02 Funnel Metric Calculation

## حساب مقاييس القمع

Purpose:

الهدف:

Calculate conversion and drop-off across ASIE product journeys.

حساب التحويل والتسرب عبر رحلات استخدام ASIE.

Funnels:

القمع:

- Landing to signup / من صفحة الهبوط إلى التسجيل.
- Signup to onboarding / من التسجيل إلى التهيئة.
- Wizard start to submit / من بدء المعالج إلى الإرسال.
- Analysis start to report export / من بدء التحليل إلى تصدير التقرير.
- Trial to subscription / من التجربة إلى الاشتراك.

Outputs:

المخرجات:

- `analytics.funnel.metric.v1`.
- Conversion rate / معدل التحويل.
- Drop-off rate / معدل التسرب.
- Step counts / أعداد الخطوات.
- Date range / نطاق التاريخ.

## AN-ALG-03 Analytics Privacy Sanitization

## تنقيح خصوصية التحليلات

Purpose:

الهدف:

Ensure product analytics data can be used safely in dashboards and AI summaries.

ضمان أن بيانات تحليلات المنتج آمنة للوحات والملخصات.

Steps:

الخطوات:

1. Remove email, phone, names, payment data, exact coordinates.
2. Replace user id with anonymous key.
3. Aggregate small cohorts when privacy risk exists.
4. Mark privacy level.
5. Reject unsafe payloads.

Output:

المخرج:

`analytics.sanitized.dataset.v1`.

## AN-ALG-04 Analytics Dashboard Dataset Builder

## باني Dataset لوحات التحليلات

Purpose:

الهدف:

Build datasets for Admin, Audit, and product intelligence dashboards.

بناء Dataset للوحات الإدارة والتدقيق وذكاء المنتج.

Datasets:

الـ Datasets:

- Traffic trend / اتجاه الزيارات.
- Active users / المستخدمون النشطون.
- Funnel metrics / مقاييس القمع.
- Retention cohorts / Cohorts الاحتفاظ.
- Feature usage heatmap / خريطة حرارة استخدام الخصائص.
- AI model usage / استخدام نماذج AI.
- Report export usage / استخدام تصدير التقارير.

Rules:

القواعد:

- Aggregated data only for AI summaries.
- بيانات مجمعة فقط لملخصات AI.

- Admin visibility follows RBAC.
- عرض الإدارة يخضع لـ RBAC.

