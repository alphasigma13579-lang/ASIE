# External Provider Security Control Plane

## الغرض

هذا هو ملف المجال الحي الذي يحكم عبور DeepSeek وTavily وGoogle Maps Platform وPinecone إلى الشبكة. ملف البرنامج `/FOUNDATION-COMPLETE-20.json` هو مصدر حالة الحزم؛ هذه الوثيقة تصف العقد التشغيلي الحالي ولا تمنح سلطة تفعيل.

## مسار القبول

`client -> ProviderSecurityControlPlane -> ExternalAcquisitionPolicy -> HTTPS transport -> response bounds/schema -> audit`

يفشل الطلب قبل الشبكة إذا غاب أي من:

- control plane enabled؛
- حالة المزود المناسبة للعملية؛
- عدم تفعيل kill switch؛
- تطابق المضيف والعقد والعملية؛
- سياق المؤسسة والمشروع؛
- request quota وcost budget؛
- circuit مغلق؛
- HTTPS allowlist وعنوان DNS عام.

## العزل والميزانية

يشتق النظام `tenant_scope_ref` من المؤسسة والمشروع ولا يضع المعرفين الخام في سجل النقل. quota وcost units وcircuit keys مستقلة لكل مزود ولكل tenant/project. القيم الحالية bounded وقابلة للضبط من البيئة دون كشف الأسرار.

## retries والحدود

- GET فقط يمكن أن يعاد عند 408/425/429/5xx أو فشل نقل عابر.
- POST وNDJSON لا يعادان تلقائيًا لتجنب التكرار غير الآمن.
- timeout وresponse bytes محكومان بسياسة المزود وسياسة الشبكة، ويطبق الحد الأصغر.
- JSON غير الصالح، body الأكبر من الحد، host mismatch، أو operation غير معتمدة تُرفض.

## الاستعداد

`production_provider_readiness.v2` لا يكتفي بوجود المفاتيح. يتطلب flags، حالات المزودين، kill switches، وallowlist كاملة، ومع ذلك يبقى `activation_authority_granted=false`: قرار التفعيل والإصدار منفصل.

## الحالة الحالية

FC20-03 ما زال `IN_PROGRESS`. التفعيل الخارجي غير مصرح. يلزم قبل الإغلاق مخزن مشترك للحصص/circuit في بيئة متعددة النسخ، إغلاق نافذة DNS pinning، وصحة وعقود استجابة فعلية لكل مزود.
