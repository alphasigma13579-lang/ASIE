# ACR-AIA-02.2 — Authorization and Audit Boundary

> سجل تاريخي لمرحلة Offline بتاريخ 2026-07-21. أعيد ترقيمه في سجل الاعتماد بتاريخ 2026-07-22 لإزالة تعارض المعرّف مع مرحلة Context / Review / Approval. لا يمثل تصريح تفعيل إنتاجي.

## الحالة

`IMPLEMENTED_OFFLINE_FOUNDATION` — طبقة حراسة server-side قابلة للاختبار، غير موصولة بـAPI أو واجهة أو Run.

## السياسة

`authorize_intelligence_action` يطلب Principal حقيقياً، يطابق `organization_id`، ويتحقق من permission عبر الدور. يسجل allow/deny في AuditSink، ولا يسجل payload أو الأسرار. غياب Principal، اختلاف المؤسسة، أو غياب الصلاحية يؤدي إلى رفض مغلق.

## التغطية

تم إثبات same-tenant reviewer allow، cross-tenant deny، missing-principal deny، وviewer role deny. ربط الحارس بمسارات Repository/HTTP مؤجل إلى حزمة API مستقلة بعد مراجعة عقد endpoint.
