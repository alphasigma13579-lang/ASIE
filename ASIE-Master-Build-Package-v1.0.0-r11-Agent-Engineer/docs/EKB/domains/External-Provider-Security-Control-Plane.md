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

يشتق النظام `tenant_scope_ref` من المؤسسة والمشروع ولا يضع المعرفين الخام في سجل النقل. quota وcost units وcircuit keys مستقلة لكل مزود ولكل tenant/project. عند تفعيل control plane يصبح `ASIE_PROVIDER_CONTROL_DB_PATH` إلزاميًا، وتُحفظ العدادات والحالة في SQLite WAL بمعاملات `BEGIN IMMEDIATE` واتصال مستقل لكل عملية، بما يمنع تجاوز الحصة بين workers على المضيف الواحد. القيم bounded وقابلة للضبط دون كشف الأسرار.

## retries والحدود

- GET فقط يمكن أن يعاد عند 408/425/429/5xx أو فشل نقل عابر.
- POST وNDJSON لا يعادان تلقائيًا لتجنب التكرار غير الآمن.
- timeout وresponse bytes محكومان بسياسة المزود وسياسة الشبكة، ويطبق الحد الأصغر.
- JSON غير الصالح، body الأكبر من الحد، host mismatch، أو operation غير معتمدة تُرفض.
- النقل الافتراضي لا يعيد حل DNS بعد التحقق ثم يتصل بالاسم؛ بل يتحقق من العناوين ويصل إلى IP رقمي مثبت مع SNI/hostname الأصلي، ويرفض proxy البيئة.

## الاستعداد

`production_provider_readiness.v2` لا يكتفي بوجود المفاتيح. يتطلب flags، حالات المزودين، kill switches، وallowlist كاملة، ومع ذلك يبقى `activation_authority_granted=false`: قرار التفعيل والإصدار منفصل.

## الحالة الحالية

FC20-03 هو `COMPLETE` تقنيًا عند commit `e63f1039ad5a2a1278f0c43a184bbfe4a4862125`. نجحت عقود الاستجابة الحية المحدودة للمزودات الأربعة، مع بقاء المزودات والشبكة معطلة افتراضيًا وعدم منح سلطة تفعيل أو إصدار. SQLite الحالي صالح لمضيف مشترك؛ النشر متعدد المضيفات يحتاج مخزنًا موزعًا منفصلًا قبل التفعيل.

## سجل أدلة 2026-08-03

- PR #112 دُمج في `main` عند `500ccba0b0b2d81708da789c6ff0c286c5415caa` بعد نجاح ASIE CI `30820331603` وLIVE-INTEL `30820328314` وCross-Platform Determinism `30820330663`.
- يثبت هذا التغيير tenant/project scope الموثوق والرفض المتقاطع، ولا يثبت استجابة مزود حية.
- PR #113 دُمج في `main` عند `34ec77d1c3b7abb3cde22c4302cfd69413e39edd` وأضاف عقود الاستجابة fail-closed وcancellation/timeout evidence وبوابة المخزن الموزع. أدلته: ASIE CI `30849216181` (`634 passed`) وLIVE-INTEL `30849215774` وProduction Provider Readiness `30849215897` وCross-Platform Determinism `30849215778`، وجميعها ناجحة.

- PR #115 أضاف مخزن الأسرار المحمي، وأثبت run `30853644493` وجود الأسرار دون كشف قيمها.
- PR #116 أضاف preflight يدويًا محدودًا بمزود واحد، وأغلق PRا #117 و#118 فجوات مسار runner وتوافق Python 3.13.
- نجحت التشغيلات الحية: DeepSeek `30856284242`، Tavily `30856375006`، Google `30856449273`، وPinecone `30857803201`.
- PR #119 عند commit `e63f1039ad5a2a1278f0c43a184bbfe4a4862125` أنشأ فهرس `vision2030-kb-e5` المتوافق والمحمي؛ run `30857670636` لم يكتب vectors أو بيانات عملاء.

الحالة الآن `COMPLETE` لـFC20-03 و`OPEN` لـFC20-04. الشبكة والمزودون يظلان معطلين افتراضيًا، وحكم الإصدار يبقى `BLOCK`.

