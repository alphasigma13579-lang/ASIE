# ACR-AIA-02.1 — Context / Review / Approval Model

> سجل تاريخي لمرحلة Offline بتاريخ 2026-07-21. أعيد ترقيمه في سجل الاعتماد بتاريخ 2026-07-22 لإزالة تعارض المعرّف مع مرحلة Authorization and Audit. لا يمثل تصريح تفعيل إنتاجي.

## الحالة

`MODEL_IMPLEMENTED_OFFLINE` — نموذج حتمي قابل للاختبار فقط. لا Repository، API، socket، Registry، Snapshot أو Decision Council v1 integration.

## المنفذ

- `ReviewOverlay` منفصل عن `context_hash` ويحمل هوية المراجع ونطاق المراجعة والقرار والشروط.
- `ApprovalReceipt` يثبت تطابق المؤسسة والمشروع والسياق والـOverlay، ويظل إذن استهلاك لا حقيقة تحليلية.
- `approval_status` حالة مشتقة لا تعدّل السياق؛ mismatch يؤدي إلى `STALE`.
- قرارات المراجعة المقبولة: `APPROVE`, `APPROVE_WITH_CONDITIONS`, `REJECT`, `REQUEST_CHANGES`.

## القيود

لا يمكن إنشاء اعتماد لسياق غير مقفول النزاهة، أو hash غير مطابق، أو مؤسسة/مشروع مختلف. لا تتحول حالة Context إلى `APPROVED_*` تلقائياً؛ الحالة الرسمية لاحقاً تُدار عبر Repository ومعاملة وتدقيق بعد بوابة تنفيذ مستقلة.

## الخطوة المحجوزة التالية

إضافة تخزين server-side ومعاملات optimistic version واختبارات صلاحيات same-tenant/cross-tenant/role/spoofed-header، ثم adapter workflow بعد اعتماد ACR مستقل. لا يُسمح بتمرير receipt إلى Run قبل تلك البوابة.
