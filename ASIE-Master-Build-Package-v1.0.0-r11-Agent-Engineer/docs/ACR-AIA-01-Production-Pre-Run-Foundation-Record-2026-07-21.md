# ACR-AIA-01 — Production Pre-Run Foundation

## الحالة

`IMPLEMENTED_OFFLINE_FOUNDATION` — لا يوجد تفعيل إنتاجي. هذه الحزمة لا تنشئ socket أو module registry أو workflow API، ولا تدخل Snapshot، ولا تستدعي شبكة أو مزوداً أو AI.

## الحدود المحفوظة

- `AAS Runtime Freeze v1.0` و`Snapshot Assembly` و`Decision Council v1` دون تعديل.
- Vision 2030 ممثل كمرجع سياقي فقط؛ World Bank/IMF/OECD غير مفعلة.
- كل مكوّن يفرض `source`, `freshness`, `geography`, `sector`, `confidence`, `lineage`, `review`، مع `organization_id` و`project_id`.
- `context_hash` يحسب من canonical material فقط؛ المراجعة/الاعتماد Overlay وليسا جزءاً من hash.

## المنفذ

`backend/intelligence_context.py` يقدم نموذج Context Build ودورة:
`DRAFT → VALIDATING → INTEGRITY_LOCKED → REVIEW_PENDING → APPROVED_*`، مع رفض مغلق، optimistic version، stale، وtenant-scoped idempotency fingerprint.

## ACR-AIA-02 المحضر كـ model فقط

المرحلة التالية تضيف Repository transaction و`intelligence_review_overlays` و`intelligence_approval_receipts` بعد مراجعة العزل والصلاحيات. الاعتماد لا يمنح حقيقة تحليلية ولا يغير Verdict؛ هو إذن لاستهلاك Context مستقبلاً. لا يُسمح بتمريره إلى Decision Council v1.

## بوابة التحقق

نجحت اختبارات الوحدة الخاصة بدورة الحياة والحقول الإلزامية وعزل مفتاح idempotency. لم يُشغّل بعد اختبار المنصة الكامل أو build في هذا السجل.
