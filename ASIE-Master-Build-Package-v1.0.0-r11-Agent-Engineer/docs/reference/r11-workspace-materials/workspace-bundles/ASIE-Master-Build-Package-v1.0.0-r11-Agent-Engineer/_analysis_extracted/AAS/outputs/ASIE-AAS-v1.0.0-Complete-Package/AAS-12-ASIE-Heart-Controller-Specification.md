Document ID: AAS-12
Document Name: ASIE Heart Controller Specification
Version: 1.0.0
Status: Frozen
Classification: Enterprise Architecture Specification
Owner: ASIE Architecture Board
Authority: ASIE Architecture Board
Parent References:

AAS-01 — ASIE Constitution
AAS-02 — ASIE Operating Architecture
AAS-10 — ASIE Kernel Specification
AAS-11 — ASIE Platform Protocol (APP) Specification
Architecture: Frozen Architecture
Last Updated: 2026-07-11
AAS-12 — ASIE Heart Controller Specification
مواصفة ASIE Heart Controller
1. الغرض من الوثيقة

تُعد هذه الوثيقة المواصفة الرسمية لـ ASIE Heart Controller ضمن ASIE Architecture Standard (AAS).

تُحدد هذه الوثيقة مسؤوليات Heart Controller، وحدوده، وسلطته التشغيلية، وعلاقته بالقلوب الثلاثة، وبقية مكونات منصة ASIE.

ولا تُنشئ هذه الوثيقة مكونًا جديدًا، ولا تضيف قلبًا رابعًا، ولا تعدل البنية التشغيلية المعتمدة في AAS-02، بل تفصل دور Heart Controller بوصفه الجهة المسؤولة عن إدارة القلوب داخل Frozen Architecture.

2. السلطة والمرجعية

تخضع هذه الوثيقة بالكامل لأحكام:

AAS-01 — ASIE Constitution
AAS-02 — ASIE Operating Architecture
AAS-10 — ASIE Kernel Specification
AAS-11 — ASIE Platform Protocol (APP) Specification

وفي حال تعارض أي نص في هذه الوثيقة مع AAS-01، تكون الأولوية الملزمة لـ AAS-01.

وفي حال تعارض أي تفصيل تشغيلي مع AAS-02، تكون الأولوية التشغيلية لـ AAS-02 ما لم يخالف ذلك AAS-01.

3. تعريف Heart Controller

يُعد Heart Controller المكون التشغيلي المسؤول عن إدارة القلوب الثلاثة داخل منصة ASIE:

Primary Heart
Assist Heart
Reserve Heart

ويتولى Heart Controller مراقبة صحة القلوب، وتوزيع الأحمال، وتفعيل القلوب عند الحاجة، وإيقافها عند انتفاء الحاجة، وترقية الأدوار عند الفشل، ومنع أي Heart من اتخاذ قرار منفرد.

4. القاعدة الدستورية لـ Heart Controller

تلتزم منصة ASIE بالقاعدة التالية:

No Heart acts alone.
All Hearts operate under Heart Controller.

وبناءً على ذلك:

لا يجوز لأي Heart اتخاذ قرار منفرد.
لا يجوز لأي Heart تفعيل نفسه.
لا يجوز لأي Heart تغيير دوره ذاتيًا.
لا يجوز لأي Heart عزل Heart آخر.
لا يجوز لأي Heart تجاوز Heart Controller.
لا يجوز تشغيل القلوب الثلاثة بكامل طاقتها بصورة دائمة.
القسم الأول: نطاق Heart Controller
5. ما يحكمه Heart Controller

يحكم Heart Controller الجوانب التالية:

مراقبة صحة القلوب.
إدارة حالة كل Heart.
توزيع الأحمال التشغيلية.
تفعيل Assist Heart عند الحاجة.
تفعيل Reserve Heart عند الطوارئ أو الأحمال العالية.
إيقاف القلوب غير اللازمة.
ترقية Heart إلى دور تشغيلي عند الفشل.
عزل Heart متعطل.
إبلاغ المكونات المختصة بالحالة التشغيلية المؤثرة.
منع القرار المنفرد من أي Heart.
6. ما لا يحكمه Heart Controller

لا يُعد Heart Controller مسؤولًا عن:

تنفيذ منطق الأعمال.
تمرير رسائل Modules بدل ASIE System Bus.
إدارة Modules بدل Bus Controller.
فرض Contracts بدل Socket Contract Layer.
تشغيل ASIE Kernel.
تنفيذ Boot Process.
تنفيذ تكامل خارجي مباشر.
اختيار مزودي الخدمات.
تشغيل AI كمصدر حقيقة.
إدارة قواعد البيانات.
تعريف APIs الخارجية.

هذه المسؤوليات تُحكم بوثائق AAS المتخصصة.

القسم الثاني: مسؤوليات Heart Controller
7. المسؤوليات المعتمدة

تتكون مسؤوليات Heart Controller من الآتي:

Heart Health Monitoring
Load Distribution
Task Rebalancing
Heart Activation
Heart Deactivation
Role Promotion
Failure Isolation
Heart State Management
Operational Notification

ولا يجوز إضافة مسؤوليات أخرى إلى Heart Controller إلا عبر Architecture Change Proposal (ACP) معتمد إذا كان التغيير يمس Frozen Architecture.

8. Heart Health Monitoring

يتولى Heart Controller مراقبة صحة كل Heart.

وتشمل مراقبة الصحة:

حالة التشغيل.
القدرة على استقبال المهام.
زمن الاستجابة.
فشل التنفيذ.
الضغط التشغيلي.
الحاجة إلى دعم من Assist Heart أو Reserve Heart.

ولا يجوز أن تعتمد مراقبة الصحة على تخمين غير قابل للتحقق أو قرار ناتج من AI كمصدر حقيقة.

9. Load Distribution

يتولى Heart Controller توزيع الأحمال على القلوب وفق الحالة التشغيلية.

ويجب أن يلتزم بالآتي:

Primary Heart يعمل في الحالة الطبيعية.
Assist Heart يُفعّل عند الحاجة.
Reserve Heart يُستخدم للطوارئ أو الأحمال العالية أو الاستبدال.
لا تُشغّل القلوب الثلاثة بكامل طاقتها دائمًا.
لا تُوزع الأحمال بطريقة تكسر العزل أو الأداء.
10. Task Rebalancing

عند تغير الحالة التشغيلية، يتولى Heart Controller إعادة توزيع المهام بين القلوب.

ويجب أن تتم إعادة التوزيع بما يضمن:

استمرار النظام إن أمكن.
عدم إسقاط ASIE System Bus.
عدم تجاوز Contracts.
عدم تمرير الرسائل خارج APP.
عدم تحويل Heart Controller إلى منفذ لمنطق الأعمال.
11. Heart Activation

يتولى Heart Controller تفعيل Assist Heart أو Reserve Heart عند وجود حاجة تشغيلية.

وتشمل أسباب التفعيل:

ارتفاع الحمل.
بطء Primary Heart.
تعطل Heart.
حاجة مؤقتة للدعم.
حالة Recovery.
حالة Degraded.

ولا يجوز تفعيل Heart بلا سبب تشغيلي واضح.

12. Heart Deactivation

يتولى Heart Controller إيقاف Heart عندما لا تكون هناك حاجة تشغيلية لاستمرار تفعيله.

ويجب أن يكون الإيقاف:

منظمًا.
غير مسبب لفقدان مهام قيد المعالجة.
غير مؤدٍ إلى كسر Message Flow.
غير مخالف لحالة النظام التشغيلية.
13. Role Promotion

يتولى Heart Controller ترقية دور Heart عند الفشل أو الحاجة.

وتشمل أمثلة الترقية:

استخدام Assist Heart لدعم Primary Heart.
استخدام Reserve Heart بدل Heart متعطل.
إعادة Primary Heart إلى دوره بعد التعافي إن كانت السياسة التشغيلية تسمح.

ولا يجوز لأي Heart أن يرقّي نفسه أو يغيّر دوره ذاتيًا.

14. Failure Isolation

عند فشل Heart، يجب أن يعزله Heart Controller ويمنع انتشار أثره.

ويشمل العزل:

إيقاف استقبال مهام جديدة للقلب المتعطل.
إعادة توزيع المهام إن أمكن.
تحديث الحالة التشغيلية.
إبلاغ ASIE System Bus أو Bus Controller عند وجود أثر على الرسائل أو Modules.
منع تكرار الفشل عبر القلوب الأخرى.
15. Heart State Management

يدير Heart Controller حالات القلوب.

وتشمل حالات Heart المعتمدة:

الحالة	الوصف
Inactive	القلب غير مفعل
Starting	القلب قيد التفعيل
Active	القلب يعمل
Assisting	القلب يقدم دعمًا تشغيليًا
Reserved	القلب في وضع احتياطي
Degraded	القلب يعمل بقدرة جزئية
Failing	القلب تظهر عليه مؤشرات فشل
Isolated	القلب معزول
Recovering	القلب في مرحلة تعافٍ
Stopped	القلب متوقف

ولا يجوز استخدام حالة تشغيلية غير معتمدة إذا كانت تؤثر على Frozen Architecture إلا بمسار تغيير معتمد.

16. Operational Notification

يجب أن يُبلغ Heart Controller المكونات المختصة بالحالات التي تؤثر على التشغيل.

وقد يشمل الإبلاغ:

ASIE System Bus عند تغير قدرة المعالجة.
Bus Controller عند تأثر Modules أو تدفقات الرسائل.
Registry عند تغير حالة Heart.
Security Context عند وجود أثر أمني وفق AAS-20.

ولا يجوز أن يتحول الإبلاغ إلى مسار بديل للرسائل بين Modules.

القسم الثالث: علاقة Heart Controller بالقلوب الثلاثة
17. العلاقة مع Primary Heart

يُعد Primary Heart القلب الأساسي في الحالة التشغيلية الطبيعية.

ويتولى Heart Controller:

مراقبة Primary Heart.
توجيه الحمل الأساسي إليه.
تقليل الضغط عنه عند الحاجة.
تفعيل Assist Heart أو Reserve Heart إذا ظهرت مؤشرات فشل أو حمل مرتفع.
عزل Primary Heart عند الفشل.

ولا يجوز لـ Primary Heart تجاوز Heart Controller أو اتخاذ قرار منفرد.

18. العلاقة مع Assist Heart

يُعد Assist Heart قلبًا مساعدًا.

ويتولى Heart Controller:

تفعيله عند الحاجة.
تحديد دوره التشغيلي المؤقت.
توجيه المهام المناسبة له.
إيقافه عند انتفاء الحاجة.
منعه من التحول إلى Heart دائم دون سبب تشغيلي.

ولا يجوز تشغيل Assist Heart بكامل طاقته بصورة دائمة.

19. العلاقة مع Reserve Heart

يُعد Reserve Heart قلبًا احتياطيًا.

ويتولى Heart Controller:

إبقاءه جاهزًا للطوارئ أو الأحمال العالية.
تفعيله عند فشل Heart أو الحاجة الحرجة.
استخدامه للاستبدال المؤقت.
إعادته إلى وضعه الاحتياطي عند انتهاء الحاجة.
منعه من العمل كقلب دائم في الحالة الطبيعية.
20. منع القرار المنفرد

تُحظر الحالات التالية:

Heart يقرر تفعيل نفسه.
Heart يعزل Heart آخر.
Heart يغير دوره دون Heart Controller.
Heart يقرر إعادة توزيع المهام ذاتيًا.
Heart يتجاوز ASIE System Bus في الرسائل.
Heart يتجاوز APP في التخاطب.
Heart يتعامل مباشرة مع Provider خارجي.
القسم الرابع: علاقة Heart Controller ببقية مكونات ASIE
21. العلاقة مع ASIE Kernel

تقوم ASIE Kernel بتفعيل Heart Controller Bootstrap فقط.

وبعد اكتمال Heart Controller Bootstrap، يتولى Heart Controller إدارة القلوب.

ولا يجوز لـ ASIE Kernel أن تتدخل في إدارة القلوب بعد انتقال المسؤولية إلى Heart Controller.

22. العلاقة مع ASIE System Bus

لا يحل Heart Controller محل ASIE System Bus.

ويجوز له إرسال أو استقبال رسائل تشغيلية معتمدة عبر APP، لكن لا يجوز أن يتحول إلى قناة تمرير بديلة بين Modules.

ويجب أن تمر الرسائل المرتبطة بـ Message Flow عبر ASIE System Bus.

23. العلاقة مع Bus Controller

يتكامل Heart Controller مع Bus Controller في الحالات التي تؤثر فيها حالة القلوب على Modules أو Message Flow.

وتشمل العلاقة:

إبلاغ Bus Controller بفشل يؤثر على تنفيذ Module.
تلقي حالة تشغيلية تؤثر على توزيع الحمل.
دعم العزل عند فشل Module يضغط على Heart.
منع تضارب قرارات التشغيل بين إدارة القلوب وإدارة Modules.

ولا يجوز لـ Heart Controller إدارة Modules بدل Bus Controller.

24. العلاقة مع Socket Contract Layer

لا يفرض Heart Controller العقود بدل ASIE Socket Contract Layer.

وإذا أدى فشل Socket أو Contract إلى أثر تشغيلي على القلوب، يجوز لـ Heart Controller التعامل مع الأثر التشغيلي فقط، دون تجاوز الجهة المختصة بالعقد.

25. العلاقة مع Modules

لا يدير Heart Controller Modules مباشرة.

ولا يجوز لأي Module الاعتماد على Heart Controller لتجاوز Bus Controller أو ASIE System Bus.

وتظل إدارة Modules من اختصاص Bus Controller، بينما يظل Heart Controller مسؤولًا عن القلوب وحالتها التشغيلية.

26. العلاقة مع AI

لا يجوز لـ Heart Controller استخدام AI كمصدر حقيقة في قرارات تشغيل القلوب.

ويجب أن تستند قراراته إلى مؤشرات تشغيلية قابلة للقياس والتحقق.

ويجوز استخدام AI للشرح أو التحليل اللغوي فقط، إذا كان ذلك خلف Contract معتمد، ودون إنتاج قرار تشغيلي نهائي.

القسم الخامس: قواعد تشغيل Heart Controller
27. تفعيل Heart Controller

يتم تفعيل Heart Controller عبر Heart Controller Bootstrap بعد اكتمال المراحل اللازمة من ASIE Kernel.

ولا يجوز تشغيل القلوب قبل تفعيل Heart Controller.

28. دورة تشغيل Heart Controller

تتكون دورة تشغيل Heart Controller من المراحل التالية:

Initialization.
Heart Discovery.
Heart State Loading.
Health Monitoring Start.
Primary Heart Activation.
Load Evaluation.
Assist Heart Activation عند الحاجة.
Reserve Heart Activation عند الطوارئ أو الأحمال العالية.
Continuous Monitoring.
Failure Isolation عند الحاجة.
Recovery Handling.
Controlled Deactivation.
29. الحالة الطبيعية للتشغيل

في الحالة الطبيعية:

Heart Controller يعمل.
Primary Heart يعمل.
Assist Heart غير مفعل إلا عند الحاجة.
Reserve Heart غير مفعل إلا عند الحاجة.
لا توجد قرارات منفردة من أي Heart.
لا توجد قنوات مباشرة خارج ASIE System Bus.
توزيع الحمل متوافق مع الأداء والعزل.
30. حالة Degraded

تدخل المنصة حالة Degraded عندما يستمر النظام في العمل بقدرة جزئية بسبب فشل أو ضغط أو عزل.

في هذه الحالة، يتولى Heart Controller:

تحديد أثر الفشل.
عزل Heart المتأثر عند الحاجة.
تفعيل Assist Heart أو Reserve Heart.
إعادة توزيع المهام.
إبلاغ المكونات المختصة.
منع تحول الفشل إلى انهيار كامل.
31. حالة Recovery

في حالة Recovery، يتولى Heart Controller إعادة النظام إلى حالة تشغيلية مستقرة.

ويجب أن تتم Recovery دون:

تجاوز ASIE System Bus.
تجاهل APP.
تجاوز Contracts.
تشغيل جميع القلوب بكامل طاقتها بلا حاجة.
إعادة Heart متعطل إلى الخدمة دون تحقق.
القسم السادس: سياسات القرار التشغيلي
32. مصدر القرار التشغيلي

يجب أن تستند قرارات Heart Controller إلى بيانات تشغيلية قابلة للتحقق، مثل:

Health Messages.
Heart State.
Load Metrics.
Failure Signals.
Timeout Events.
Operational State.
Registry Updates.

ولا يجوز أن تكون قرارات تشغيل القلوب مبنية على مخرجات AI بوصفها مصدر حقيقة.

33. حدود القرار التشغيلي

يقتصر قرار Heart Controller على إدارة القلوب.

ولا يجوز أن يمتد إلى:

تغيير Contracts.
قبول Modules.
تعديل ASIE Kernel.
إعادة تعريف APP.
تغيير Message Flow.
تنفيذ Business Logic.
اختيار Provider خارجي.
34. منع تضارب القرارات

إذا تعارض قرار Heart Controller مع Bus Controller أو ASIE System Bus، يجب الرجوع إلى حدود المسؤوليات المحددة في AAS-01 وAAS-02.

ولا يجوز لاعتبارات الحمل أن تبرر خرق Contracts أو تجاوز ASIE System Bus.

القسم السابع: الفشل والعزل
35. مؤشرات فشل Heart

تشمل مؤشرات فشل Heart:

توقف الاستجابة.
تكرار الأخطاء.
ارتفاع غير طبيعي في زمن المعالجة.
عدم القدرة على استقبال مهام.
فقدان الحالة التشغيلية.
تعارض مستمر في التقارير الصحية.
تجاوز حدود الحمل المعتمدة.
36. إجراءات عزل Heart

عند عزل Heart، يجب أن يتم:

منع إرسال مهام جديدة إليه.
حفظ الحالة التشغيلية المتاحة إن أمكن.
إعادة توزيع المهام.
تحديث Registry.
إبلاغ ASIE System Bus عند تأثر Message Flow.
إبلاغ Bus Controller عند تأثر Modules.
منع إعادة التفعيل قبل التحقق.
37. منع انتشار الفشل

يجب أن يمنع Heart Controller انتقال الفشل من Heart إلى آخر.

ويُحظر تنفيذ إجراءات Recovery تؤدي إلى:

تحميل زائد على Heart آخر.
رسائل مكررة بلا حد.
تفعيل القلوب الثلاثة بكامل طاقتها دون ضوابط.
تجاوز APP.
تعطيل ASIE System Bus.
38. إعادة التفعيل بعد الفشل

لا يجوز إعادة Heart معزول إلى الخدمة إلا بعد تحقق تشغيلي يثبت قدرته على العمل.

ويجب أن تتم إعادة التفعيل تدريجيًا عند الحاجة، ودون تعطيل الحالة المستقرة للنظام.

القسم الثامن: الأداء
39. الأداء كقيد في Heart Controller

يُعد الأداء قيدًا تشغيليًا ملزمًا في Heart Controller.

ويجب أن توازن قراراته بين:

سرعة الاستجابة.
عزل الفشل.
عدم تشغيل موارد غير لازمة.
عدم تحميل القلوب بمهام قابلة للتنفيذ برمجيًا خارج AI.
عدم التضحية بالمعمارية مقابل تحسين مؤقت.
40. منع التشغيل الزائد

يُحظر على Heart Controller تشغيل Assist Heart أو Reserve Heart بلا حاجة تشغيلية.

كما يُحظر استمرار تشغيل القلوب الثلاثة بكامل طاقتها بصورة دائمة.

41. حدود استخدام AI

لا يجوز لـ Heart Controller استدعاء AI لاتخاذ قرار توزيع حمل أو عزل أو ترقية دور.

وتُنتج هذه القرارات بواسطة منطق حتمي ومؤشرات تشغيلية قابلة للقياس.

القسم التاسع: المحظورات الخاصة بـ Heart Controller
42. محظورات Heart Controller

يُحظر على Heart Controller ما يلي:

تنفيذ منطق الأعمال.
إدارة Modules بدل Bus Controller.
تمرير رسائل Modules بدل ASIE System Bus.
فرض Contracts بدل Socket Contract Layer.
تعديل ASIE Kernel.
تشغيل AI كمصدر قرار.
ربط القلوب بمزود خارجي.
السماح لأي Heart باتخاذ قرار منفرد.
تشغيل القلوب الثلاثة بكامل طاقتها دائمًا.
تجاوز APP.
تجاوز AAS-01 أو AAS-02 باسم الأداء.
تحويل نفسه إلى Heart رابع.
43. مخالفة حدود Heart Controller

تُعد أي محاولة لتوسيع Heart Controller خارج إدارة القلوب مخالفة معمارية.

ويجب عند اكتشافها:

رفض التغيير.
إعادة المسؤولية إلى المكون المختص.
مراجعة الأثر على AAS-01 وAAS-02.
عدم الاعتماد إلا عبر Architecture Change Proposal (ACP) إذا كان التغيير يمس Frozen Architecture.
القسم العاشر: معايير التحقق من الالتزام
44. معايير قبول Heart Controller

يُقبل Heart Controller معماريًا إذا حقق الآتي:

يدير القلوب الثلاثة فقط.
يمنع القرار المنفرد من أي Heart.
يفعّل Assist Heart عند الحاجة فقط.
يفعّل Reserve Heart للطوارئ أو الأحمال العالية أو الاستبدال.
يعزل Heart المتعطل.
يعيد توزيع المهام دون تجاوز APP.
لا يدير Modules بدل Bus Controller.
لا يمرر الرسائل بدل ASIE System Bus.
لا يستخدم AI كمصدر حقيقة.
لا يتحول إلى Heart رابع.
45. مؤشرات الانحراف المعماري

تُعد الحالات التالية مؤشرات انحراف:

Heart Controller ينفذ Business Logic.
Heart Controller يستدعي Provider خارجيًا.
Heart Controller يغير Contract.
Heart Controller يدير Module مباشرة.
Heart Controller يمرر رسائل بين Modules.
Heart يفعّل نفسه دون Controller.
Assist Heart يعمل دائمًا بلا حاجة.
Reserve Heart يعمل كقلب دائم.
قرار تشغيل القلوب مصدره AI.
القسم الحادي عشر: العلاقة مع وثائق AAS الأخرى
46. الوثائق المرتبطة

ترتبط هذه الوثيقة بالوثائق التالية:

AAS-01 — ASIE Constitution
AAS-02 — ASIE Operating Architecture
AAS-10 — ASIE Kernel Specification
AAS-11 — ASIE Platform Protocol (APP) Specification
AAS-13 — ASIE Three Hearts Specification
AAS-14 — ASIE Bus Controller Specification
AAS-15 — ASIE System Bus Specification
AAS-16 — ASIE Socket Contract Layer Specification
AAS-17 — ASIE Module Specification
AAS-18 — ASIE Message Flow Specification
AAS-20 — ASIE Zero Trust Security Specification
AAS-40 — ASIE AI Integration Specification

ولا يجوز لأي وثيقة منها أن تفسر Heart Controller بما يسمح بتحويله إلى Kernel أو Bus أو Module Manager أو Heart رابع.

أحكام ختامية
47. الأثر الملزم

تُعد AAS-12 — ASIE Heart Controller Specification المرجع الرسمي الحاكم لتعريف Heart Controller وحدوده ومسؤولياته.

ويلتزم كل تصميم أو تنفيذ أو مراجعة أو تطوير متعلق بإدارة القلوب بأحكام هذه الوثيقة.

48. حدود التعديل

لا يجوز تعديل مسؤوليات Heart Controller أو توسيع نطاقه أو السماح لأي Heart بتجاوز سلطته إلا عبر Architecture Change Proposal (ACP) معتمد إذا كان التغيير يمس Frozen Architecture.

49. الصفة النهائية

تُعتمد هذه الوثيقة بوصفها المواصفة الرسمية لـ ASIE Heart Controller ضمن ASIE Architecture Standard (AAS).

وبموجبها، تعمل جميع القلوب داخل منصة ASIE تحت إدارة Heart Controller، ولا يجوز لأي Heart اتخاذ قرار منفرد أو العمل خارج الحدود التشغيلية المعتمدة.

End of Document
ــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــ
AAS-13 ASIE Three Hearts Specification
ASIE Architecture Standard (AAS)
