# Product Analytics Adapters

## موصلات تحليلات المنتج

## Purpose

## الهدف

ASIE may use external product analytics systems to understand platform usage, conversion, funnels, retention, and operational adoption.

يجوز لـ ASIE استخدام أنظمة تحليلات المنتج الخارجية لفهم استخدام المنصة، التحويل، القمع، الاحتفاظ، وتبني الخصائص.

These adapters are not market intelligence sources and are not financial authority.

هذه الموصلات ليست مصادر ذكاء سوق وليست سلطة مالية.

## Approved Analytics Adapters

## موصلات التحليلات المعتمدة

| Adapter | Arabic | Owner | Purpose |
| --- | --- | --- | --- |
| `Google Analytics Adapter` | موصل تحليلات جوجل | `Audit / Observability Module` | Product behavior, traffic, funnels |
| `Zoho Analytics Adapter` | موصل تحليلات زوهو | `Audit / Observability Module` + `Admin Module` | BI dashboards, operational analytics |

## Allowed Uses

## الاستخدامات المسموحة

- Landing page traffic / زيارات صفحة الهبوط.
- Signup conversion / تحويل التسجيل.
- Wizard step drop-off / تسرب خطوات المعالج.
- Feature adoption / تبني الخصائص.
- Report export usage / استخدام تصدير التقارير.
- AI advisory usage counts / عدد استخدام الاستشارات.
- Subscription funnel / قمع الاشتراكات.
- Admin operational dashboards / لوحات الإدارة التشغيلية.

## Forbidden Uses

## الاستخدامات الممنوعة

- Do not use Google Analytics or Zoho Analytics as market evidence for project feasibility.
- لا تستخدم Google Analytics أو Zoho Analytics كدليل سوق لجدوى مشروع المستخدم.

- Do not use them as finance inputs.
- لا تستخدمهما كمدخلات مالية.

- Do not use them to bypass ASIE Audit / Observability.
- لا تستخدمهما لتجاوز موديول التدقيق والمراقبة.

- Do not expose personal analytics identifiers to AI.
- لا تكشف معرفات التحليلات الشخصية للذكاء الاصطناعي.

## Data Contracts

## عقود البيانات

### `analytics.event.ingested.v1`

حدث تحليلي مستوعب.

Required fields:

الحقول المطلوبة:

- `event_id` / معرف الحدث.
- `event_name` / اسم الحدث.
- `source_adapter` / موصل المصدر.
- `timestamp` / الوقت.
- `workspace_id` / مساحة العمل.
- `anonymous_user_key` / مفتاح مستخدم مجهول.
- `properties` / الخصائص.

### `analytics.funnel.metric.v1`

مقياس قمع تحليلي.

Required fields:

الحقول المطلوبة:

- `funnel_id` / معرف القمع.
- `steps` / الخطوات.
- `conversion_rate` / معدل التحويل.
- `dropoff_rate` / معدل التسرب.
- `date_range` / نطاق التاريخ.

### `analytics.dashboard.dataset.v1`

Dataset لوحة التحليلات.

Required fields:

الحقول المطلوبة:

- `dashboard_id` / معرف اللوحة.
- `metrics` / المقاييس.
- `dimensions` / الأبعاد.
- `source_adapter` / موصل المصدر.
- `privacy_level` / مستوى الخصوصية.

## Privacy Rules

## قواعد الخصوصية

- Prefer anonymous user keys / تفضيل مفاتيح مستخدم مجهولة.
- Do not store raw PII unless legally required and explicitly approved / لا تخزن PII خام إلا لضرورة قانونية وموافقة صريحة.
- AI summaries must receive aggregated analytics only / ملخصات AI تستلم بيانات مجمعة فقط.
- Admin dashboards may show operational metrics under RBAC / لوحات الإدارة تعرض مقاييس تشغيلية وفق RBAC.

## Chart Requirements

## متطلبات الشارتات

- Funnel chart for signup and wizard completion / شارت قمع للتسجيل وإكمال المعالج.
- Line chart for traffic and active users / شارت خطي للزيارات والمستخدمين.
- Cohort chart for retention / شارت Cohort للاحتفاظ.
- Heatmap for feature usage / خريطة حرارة لاستخدام الخصائص.
- Stacked bar for plan and model usage / أعمدة مكدسة للخطة واستخدام النماذج.

