# Subscription and Admin Algorithms Full

## خوارزميات الاشتراكات والإدارة الكاملة

## SUB-ALG-01 Trial Cooldown

## تهدئة التجربة المجانية

Owner:

المالك:

`Subscription / Usage Module` / موديول الاشتراكات والاستخدام.

Purpose:

الهدف:

Control free trial usage and prevent abuse.

ضبط استخدام التجربة المجانية ومنع إساءة الاستخدام.

Inputs:

المدخلات:

- User id / معرف المستخدم.
- Workspace id / معرف مساحة العمل.
- Trial usage count / عدد استخدامات التجربة.
- Last trial timestamp / آخر وقت تجربة.
- Admin override flag / علم تجاوز إداري.

Steps:

الخطوات:

1. Check active subscription.
2. Check trial quota.
3. Check cooldown window.
4. Allow, deny, or require upgrade.
5. Audit decision.

Forbidden:

الممنوع:

- AI cannot grant trial or credits.
- الذكاء الاصطناعي لا يمنح تجربة أو رصيدًا.

## SUB-ALG-02 Usage Limit Evaluation

## تقييم حدود الاستخدام

Purpose:

الهدف:

Determine whether a user can run an analysis, report, AI advisory, or premium model request.

تحديد هل يستطيع المستخدم تشغيل تحليل أو تقرير أو استشارة AI أو طلب نموذج مدفوع.

Steps:

الخطوات:

1. Load plan.
2. Load current consumption.
3. Classify requested operation cost tier.
4. Check monthly or annual limits.
5. Reserve usage token.
6. Release or consume token based on outcome.
7. Audit usage event.

## ADM-ALG-01 Feature Flag Evaluation

## تقييم أعلام الخصائص

Owner:

المالك:

`Admin Module` / موديول الإدارة.

Purpose:

الهدف:

Decide whether a feature is enabled for a user, workspace, plan, or environment.

تحديد هل الخاصية مفعلة لمستخدم أو مساحة عمل أو خطة أو بيئة.

Inputs:

المدخلات:

- Feature key / مفتاح الخاصية.
- User id / معرف المستخدم.
- Workspace id / معرف مساحة العمل.
- Plan / الخطة.
- Environment / البيئة.

Steps:

الخطوات:

1. Check global flag.
2. Check environment override.
3. Check workspace override.
4. Check plan entitlement.
5. Return enabled or disabled with reason.
6. Audit changes, not reads.

Forbidden:

الممنوع:

- Silent mutation.
- تعديل صامت.

