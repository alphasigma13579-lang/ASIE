# Tavily Governed Source Admission

## الغرض

هذا هو ملف المجال الحي الذي يحدد ما يجوز لـ Tavily اكتشافه أو استخراجه داخل ASIE. لا تُستخدم الوثائق المؤرخة أو `docs/reference` كمصدر تنفيذي لهذا المجال.

## المصدر الوحيد للحقيقة

- سجل المصادر: `backend/source_registry.py`
- قرار القبول: `backend/tavily_source_admission.py`
- عميل المزود: `backend/live_provider_clients.py`
- القرار المعماري: `docs/ACR-FC20-02-GOVERNED-TAVILY-SOURCE-ADMISSION-2026-07-29.md`

## قاعدة البحث

يستطيع Tavily تنفيذ discovery فقط عندما توجد سجلات خادمية تحمل:

- `state` يساوي `candidate` أو `enabled`.
- `discovery_allowed=true`.
- قطاع وجغرافيا مطابقان لسياق المشروع.
- نطاق HTTPS رسمي مضبوط في السجل.
- نطاق مؤسسة/مشروع يطابق الطالب أو `__platform__/*`.

لا يحدد العميل قائمة النطاقات؛ يمكنه طلب تضييقها فقط، ولا يستطيع توسيعها.

## قاعدة الاستخراج والزحف

`extract/crawl/map` تتطلب مصدرًا `enabled` وموافقة `reviewer_decision=approved` وجميع أدلة الشروط والترخيص والنسبة والتصنيف وPDPL/NCA والغرض المشروع. المضيف والمسار يطابقان السجل حرفيًا ضمن `allowed_paths`. query parameters ممنوعة افتراضيًا.

## الحالة الحالية للمصادر البذرية

- GASTAT وSAMA وMOF: `candidate`؛ لا استخراج ولا زحف حتى اكتمال المراجعة.
- Vision 2030: `reference_only` في سجل المصادر العام؛ مزامنة Vision الاستثنائية تحكمها `FC20-05` ولا توسع Tavily تلقائيًا.
- Mostaql: `reference_only`؛ الرابط والملاحظة الخاصة فقط، وكل fetch/crawl/embed/monitor ممنوع.

## حدود المخرجات

كل نتيجة Tavily تظل `review_required` و`eligible_for_controlled_assumptions=false`. لا تدخل Finance أو Snapshot أو Decision Council إلا عبر حزم الأدلة والمراجعة اللاحقة.
