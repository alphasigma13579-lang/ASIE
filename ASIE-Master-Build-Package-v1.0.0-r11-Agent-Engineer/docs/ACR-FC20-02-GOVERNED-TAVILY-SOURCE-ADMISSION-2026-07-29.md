# ACR-FC20-02 — Governed Tavily Source Admission

- الحالة: `APPROVED_FOR_CODE_ONLY`
- البرنامج: `FOUNDATION-COMPLETE-20 / FC20-02`
- النطاق: مصدر GitHub الرسمي فقط
- قرار الإطلاق: `BLOCK`
- تفعيل الشبكة أو المزود: غير مصرح به بهذه الوثيقة

## القرار

يفصل ASIE بين عمليتين مستقلتين:

1. `discovery_search`: اكتشاف مرشحين فقط، ضمن نطاقات يختارها الخادم من سياق القطاع والجغرافيا. النتيجة دائمًا `review_required` وغير مؤهلة للافتراضات المحكمة.
2. `extract/crawl/map`: وصول إلى محتوى مصدر معروف فقط بعد أن يكون `enabled`، وموافقًا عليه بشريًا، ومقيدًا بالمالك والمسار ونسخة الشروط والترخيص والنسبة والتصنيف وفحوص PDPL/NCA والغرض المشروع.

لا يقبل العميل توسيع `include_domains`، ولا يقبل Tavily بذرة URL حرة. المصادر `candidate` و`reference_only` و`blocked` لا يسمح لها بالاستخراج أو الزحف. ينطبق ذلك صراحة على `MOSTAQL_PROJECTS`.

## الثوابت

- لا تعديل لـ AAS Runtime أو Finance أو Snapshot.
- لا اتصال خارجي في الاختبارات.
- لا تخزين لمفتاح Tavily أو محتوى سري.
- لا انتقال تلقائي من نتيجة Tavily إلى Finance أو controlled assumptions.
- حدود المؤسسة والمشروع تفشل مغلقة.
- غياب السياسة أو المصدر أو دليل الشروط يؤدي إلى منع الطلب قبل طبقة النقل.

## التنفيذ

- `backend/tavily_source_admission.py`
- `backend/live_provider_clients.py`
- `backend/source_registry.py`
- `backend/live_intelligence_product.py`

## اختبارات القبول السلبية

- رفض مصدر مجهول وبذرة عشوائية قبل أي استدعاء نقل.
- رفض `candidate/reference_only`، بما فيها Mostaql.
- رفض توسيع نطاقات البحث من العميل.
- رفض سجل مصدر يعود إلى مستأجر أو مشروع آخر.
- رفض مسار أو query parameters غير مصرّح بها.
- إثبات بقاء نتائج الاكتشاف `review_required`.

## Rollback

يمكن عكس commit التنفيذ دون migration أو تغيير بيانات مجمدة. الإزالة تعيد Tavily إلى حالته السابقة، لكن بوابة `FOUNDATION-COMPLETE-20` تبقى `BLOCK` ولا تسمح بالإصدار.
