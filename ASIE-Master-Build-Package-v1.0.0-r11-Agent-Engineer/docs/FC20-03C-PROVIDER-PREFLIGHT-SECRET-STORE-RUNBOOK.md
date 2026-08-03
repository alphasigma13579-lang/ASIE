# FC20-03C — Provider Preflight Secret Store Runbook

## القرار

يستخدم FC20-03 بيئة GitHub مستقلة باسم `provider-preflight`. لا توضع مفاتيح الاختبار في `production`، أو Repository Secrets العامة، أو ملفات `.env` المرفوعة إلى Git، أو المحادثات، أو artifacts.

بوابة مخزن الأسرار تثبت وجود الأسماء المطلوبة فقط. نجاحها لا يفعّل الشبكة أو المزودين ولا يمنح قرار إصدار.

## الأسرار المطلوبة

- `DEEPSEEK_API_KEY`
- `TAVILY_API_KEY`
- `GOOGLE_MAPS_API_KEY`
- `PINECONE_API_KEY`

اختيارية:

- `TAVILY_PROJECT`
- `GOOGLE_MAP_ID`

يجب أن تكون المفاتيح مخصصة للاختبار، بأقل الصلاحيات والحصص والميزانية الممكنة، ومختلفة عن مفاتيح الإنتاج.

## إنشاء GitHub Environment

من المستودع الرسمي:

1. افتح `Settings → Environments → New environment`.
2. أنشئ البيئة بالاسم الدقيق `provider-preflight`.
3. فعّل Required reviewers بمراجع أمني/مالك منصة مخول.
4. فعّل منع المراجع من اعتماد تشغيله بنفسه إن كانت الخطة تدعم ذلك.
5. قيد Deployment branches and tags إلى `main` فقط.
6. لا تضف environment URL ولا deployment target عام.
7. أضف الأسرار المطلوبة من واجهة GitHub؛ لا تنسخ قيمها إلى issue أو PR أو Actions input.

## اختبار الوجود الآمن

شغّل يدويًا:

`Actions → FC20-03 Provider Preflight Secret Store → Run workflow`

الـworkflow:

- يعمل فقط عبر `workflow_dispatch`؛
- ينتظر موافقة بيئة `provider-preflight`؛
- يملك `contents: read` فقط؛
- لا يشغّل `live_provider_preflight --network`؛
- لا ينشئ artifacts؛
- لا يطبع أو يخزن أو يجزئ قيم الأسرار؛
- يعيد فقط `present: true/false` وأسماء القيم المفقودة.

## معايير القبول

- Environment موجود ومحمي ومقيد إلى `main`.
- كل الأسرار الأربعة المطلوبة موجودة.
- نتيجة workflow هي `ready`.
- `network_authorized=false` و`provider_activation_authorized=false` و`release_authorized=false` في التقرير.
- لا توجد قيمة سرية في logs أو artifacts أو commit أو PR.
- يسجل رقم workflow run وcommit SHA واسم البيئة في سجل FC20-03.

## الدوران والإبطال

1. أنشئ مفتاح اختبار بديل من المزود قبل إبطال القديم عندما يدعم المزود تداخلًا آمنًا.
2. حدّث Environment secret من GitHub Settings.
3. شغّل presence-only gate ثم live preflight المحدود في مرحلة منفصلة.
4. أبطل المفتاح القديم من لوحة المزود.
5. سجل التاريخ والمالك والسبب ومعرف الدليل دون تسجيل قيمة المفتاح.
6. عند الاشتباه بالتسرب: فعّل global kill switch، أبطل المفتاح فورًا، راجع Actions logs، وأنشئ حادثة أمنية.

## الفصل عن التفعيل الحي

لا تضاف `ASIE_ALLOW_EXTERNAL_FETCH=true` أو حالات المزود `enabled` إلى هذا workflow. تفعيل preflight الحي يحتاج PR/ACR منفصلًا، موافقة البيئة، حصة مالية محدودة، allowlist، ومفتاح إيقاف طارئ.

