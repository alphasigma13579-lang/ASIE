Document ID: AAS-15
Document Name: ASIE System Bus Specification
Version: 1.0.0
Status: Frozen
Classification: Enterprise Architecture Specification
Owner: ASIE Architecture Board
Authority: ASIE Architecture Board
Parent References:

AAS-01 — ASIE Constitution
AAS-02 — ASIE Operating Architecture
AAS-11 — ASIE Platform Protocol (APP) Specification
Architecture: Frozen Architecture
Last Updated: 2026-07-11
AAS-15 — ASIE System Bus Specification
مواصفة ASIE System Bus
1. الغرض من الوثيقة

تُعد هذه الوثيقة المواصفة الرسمية لـ ASIE System Bus ضمن ASIE Architecture Standard (AAS).

تُحدد هذه الوثيقة دور ASIE System Bus بوصفه المسار التشغيلي الوحيد لتمرير الرسائل داخل منصة ASIE، وتُبين مسؤولياته، وحدوده، وقواعده، وعلاقته بـ APP وContracts وModules وHeart Controller وBus Controller.

ولا تُنشئ هذه الوثيقة قناة بديلة، ولا تسمح باتصال مباشر بين Modules، ولا تحول ASIE System Bus إلى مكان لتنفيذ منطق الأعمال.

2. السلطة والمرجعية

تخضع هذه الوثيقة بالكامل لأحكام:

AAS-01 — ASIE Constitution
AAS-02 — ASIE Operating Architecture
AAS-11 — ASIE Platform Protocol (APP) Specification

وفي حال تعارض أي نص في هذه الوثيقة مع AAS-01، تكون الأولوية الملزمة لـ AAS-01.

وفي حال تعارض أي تفصيل بروتوكولي مع AAS-11، تكون الأولوية لـ AAS-11 ما لم يخالف ذلك AAS-01 أو AAS-02.

3. تعريف ASIE System Bus

يُعد ASIE System Bus قناة الرسائل الداخلية الرسمية والوحيدة داخل منصة ASIE.

تمر عبره الرسائل بين المكونات المعتمدة وفق:

APP
Contracts
Socket Contract Layer
Security Context
Message Flow

ولا يجوز لأي Module أو Heart أو مكون آخر تجاوز ASIE System Bus عند تمرير الرسائل التشغيلية.

4. القاعدة الدستورية لـ ASIE System Bus

تلتزم منصة ASIE بالقاعدة التالية:

All internal messages pass through ASIE System Bus.
No Module communicates directly with another Module.

وبناءً على ذلك:

لا يوجد اتصال مباشر بين Modules.
لا توجد قناة رسائل بديلة.
لا يُستخدم ASIE Kernel كمسار رسائل.
لا يُستخدم Heart Controller كمسار رسائل بين Modules.
لا يُستخدم Bus Controller كبديل عن ASIE System Bus.
لا تُقبل رسالة داخلية خارج APP.
القسم الأول: نطاق ASIE System Bus
5. ما يحكمه ASIE System Bus

يحكم ASIE System Bus الجوانب التالية:

استقبال APP Messages.
تمرير الرسائل بين المكونات.
دعم التحقق قبل التمرير.
دعم تتبع Message Flow.
دعم عزل الفشل.
دعم رفض الرسائل غير الصالحة.
دعم الحالات التشغيلية للرسائل.
منع الاتصال المباشر بين Modules.
منع التدفقات غير المعتمدة.
6. ما لا يحكمه ASIE System Bus

لا يُعد ASIE System Bus مسؤولًا عن:

تنفيذ Business Logic.
تنفيذ Provider Logic.
إدارة Modules بدل Bus Controller.
إدارة القلوب بدل Heart Controller.
فرض العقود بدل Socket Contract Layer.
تشغيل ASIE Kernel.
تنفيذ Boot Process.
اختيار مزود خارجي.
تنفيذ الحسابات الحتمية النهائية.
إنتاج قرارات AI.
إدارة قواعد البيانات.
تعريف API خارجية.

هذه المسؤوليات تُفصل في وثائق AAS المتخصصة.

القسم الثاني: مسؤوليات ASIE System Bus
7. المسؤوليات المعتمدة

تتكون مسؤوليات ASIE System Bus من الآتي:

Message Intake
Message Validation Support
Message Routing
Message Delivery
Message Traceability
Message Failure Handling
Message Isolation Support
Message State Reporting
Direct Communication Prevention

ولا يجوز إضافة مسؤوليات تغير طبيعة ASIE System Bus إلا عبر Architecture Change Proposal (ACP) معتمد إذا كان التغيير يمس Frozen Architecture.

8. Message Intake

يتولى ASIE System Bus استقبال الرسائل الداخلية الملتزمة بـ APP.

ولا يجوز له استقبال رسالة لا تحتوي الحد الأدنى من الحقول الإلزامية المعتمدة في AAS-11.

9. Message Validation Support

يدعم ASIE System Bus التحقق من صلاحية الرسالة قبل تمريرها.

ويشمل ذلك:

التحقق من Source.
التحقق من Destination.
التحقق من Contract ID.
التحقق من Socket ID.
التحقق من Security Context.
التحقق من Message Type.
التحقق من صلاحية Payload وفق المكون المختص.

ولا يعني ذلك أن ASIE System Bus يحل محل Socket Contract Layer أو Bus Controller، بل يدعم تطبيق قواعد التمرير المعتمدة.

10. Message Routing

يتولى ASIE System Bus توجيه الرسائل إلى الوجهات المعتمدة فقط.

ولا يجوز توجيه رسالة إلى:

Destination غير مسجلة.
Module غير مفعلة.
Socket غير صالح.
Contract غير معتمد.
مسار مباشر خارج ASIE System Bus.
11. Message Delivery

يتولى ASIE System Bus تسليم الرسائل وفق APP وMessage Flow المعتمد.

ويجب أن يكون التسليم:

قابلًا للتتبع.
مرتبطًا بـ Correlation ID عند الحاجة.
ملتزمًا بالسياق الأمني.
غير متجاوز للعقود.
غير مسبب لفشل متسلسل.
12. Message Traceability

يجب أن يدعم ASIE System Bus تتبع الرسائل داخليًا بما يكفي للتشخيص والتدقيق التشغيلي.

ويشمل التتبع:

Message ID.
Correlation ID.
Source.
Destination.
Contract ID.
Socket ID.
الحالة التشغيلية.
وقت الاستقبال.
وقت التسليم أو الرفض.
13. Message Failure Handling

عند فشل رسالة، يجب أن يتعامل ASIE System Bus مع الفشل بطريقة تمنع:

إعادة المحاولة غير المحدودة.
تضخيم الحمل.
تعطيل القلوب.
إسقاط النظام.
نشر الفشل إلى Modules أخرى.
14. Message Isolation Support

يدعم ASIE System Bus عزل الرسائل أو التدفقات التي تسبب خطرًا تشغيليًا.

ويجوز أن يشمل ذلك:

رفض الرسالة.
إيقاف تمرير رسائل إلى Module معزولة.
إبلاغ Bus Controller.
إبلاغ Heart Controller عند وجود أثر تشغيلي.
تحديث الحالة التشغيلية عند الحاجة.
15. Message State Reporting

يجب أن يتيح ASIE System Bus حالة الرسائل للمكونات المختصة دون كشف تفاصيل غير مصرح بها.

وقد تشمل الحالات:

الحالة	الوصف
Received	تم استقبال الرسالة
Validating	الرسالة قيد التحقق
Accepted	الرسالة مقبولة للتمرير
Routed	تم توجيه الرسالة
Delivered	تم تسليم الرسالة
Rejected	تم رفض الرسالة
Failed	فشل تمرير الرسالة
Isolated	تم عزل الرسالة أو التدفق
Expired	انتهت صلاحية الرسالة
Retried	تمت إعادة المحاولة وفق سياسة معتمدة
16. Direct Communication Prevention

يُعد منع الاتصال المباشر بين Modules مسؤولية جوهرية لـ ASIE System Bus.

ويجب أن يمنع أو يرفض أي محاولة لـ:

Module to Module direct call.
Module to Provider bypass.
Heart to Module bypass.
Message Flow خارج APP.
تمرير رسالة دون Contract أو Socket.
القسم الثالث: بنية الرسائل داخل ASIE System Bus
17. اعتماد APP Message

لا يقبل ASIE System Bus إلا الرسائل المتوافقة مع APP.

ويجب أن تحتوي الرسائل على الحقول الإلزامية المحددة في AAS-11.

18. الحقول اللازمة للتمرير

يعتمد ASIE System Bus على الحقول التالية كحد أدنى:

Message ID
Message Type
Source
Destination
Contract ID
Socket ID
Correlation ID
Execution Context
Payload
Timestamp
Security Context
Validation State
19. سلامة Payload

لا يجوز لـ ASIE System Bus تعديل Payload بطريقة تغير معناها أو تنقل منطق أعمال إلى قناة الرسائل.

ويجوز له فقط تطبيق ما يلزم من تحقق أو تغليف أو وسم تشغيلي وفق APP وContracts.

20. الحفاظ على Correlation ID

يجب الحفاظ على Correlation ID خلال Message Flow حتى يمكن تتبع التدفق وربط الاستجابات والأخطاء.

ولا يجوز إنشاء Correlation ID جديد إلا عند وجود سياق تشغيلي يبرر فصل التدفق.

القسم الرابع: قواعد تمرير الرسائل
21. المسار المعتمد

يمر التدفق الأساسي للرسالة كما يلي:

مصدر معتمد ينشئ APP Message.
الرسالة ترتبط بـ Contract ID.
الرسالة ترتبط بـ Socket ID.
الرسالة تُرسل إلى ASIE System Bus.
ASIE System Bus يدعم التحقق من صلاحية الرسالة.
الرسالة تُوجّه إلى Destination معتمدة.
الوجهة تعالج الرسالة ضمن Contract.
الحالة التشغيلية تُسجل عند الحاجة.
22. منع المسارات البديلة

يُحظر أي مسار رسالة بديل داخل ASIE.

ويشمل ذلك:

تمرير الرسائل عبر ASIE Kernel.
تمرير الرسائل عبر Heart Controller بدل ASIE System Bus.
تمرير الرسائل عبر Bus Controller كقناة بديلة.
اتصال مباشر بين Modules.
اتصال مباشر بين Module ومزود خارجي دون Contract.
تدفق رسائل خارج APP.
23. شروط قبول الرسالة

تُقبل الرسالة للتمرير إذا تحققت الشروط التالية:

Source مسجل ومعتمد.
Destination مسجلة ومعتمدة.
Contract ID صالح.
Socket ID صالح.
Message Type معتمد.
Payload مطابق.
Security Context صالح.
Execution Context صالح.
الرسالة لا تخالف حالة النظام التشغيلية.
24. شروط رفض الرسالة

تُرفض الرسالة إذا تحقق أي مما يلي:

مصدر غير معروف.
وجهة غير مسجلة.
غياب Contract ID.
غياب Socket ID.
Payload غير مطابق.
Security Context غير صالح.
Message Type غير معتمد.
محاولة اتصال مباشر.
محاولة تجاوز ASIE System Bus.
محاولة تنفيذ Business Logic داخل ASIE System Bus.
محاولة تمرير AI Output كحقيقة نهائية غير حتمية.
القسم الخامس: العلاقة مع APP
25. APP هو لغة الرسائل

يُعد APP اللغة البروتوكولية الحاكمة للرسائل التي تمر عبر ASIE System Bus.

ولا يجوز لـ ASIE System Bus قبول نمط رسائل غير متوافق مع APP.

26. عدم استقلال ASIE System Bus عن APP

لا يعمل ASIE System Bus بمعزل عن APP.

ويجب أن تكون قواعد التمرير والرفض والتتبع متوافقة مع AAS-11.

27. حدود APP داخل ASIE System Bus

لا يجوز استخدام APP داخل ASIE System Bus لتبرير:

تجاوز Contracts.
تجاوز Socket Contract Layer.
نقل Business Logic إلى ASIE System Bus.
بناء قناة مباشرة بين Modules.
ربط النظام بمزود خارجي محدد.
القسم السادس: العلاقة مع Contracts وSocket Contract Layer
28. Contract Required

لا تمر أي رسالة عبر ASIE System Bus دون Contract ID صالح.

ويُعد غياب Contract سببًا مباشرًا للرفض.

29. Socket Required

لا تمر أي رسالة عبر ASIE System Bus دون Socket ID صالح.

ويُعد غياب Socket أو فشل Socket Binding سببًا مباشرًا للرفض أو العزل.

30. عدم حلول ASIE System Bus محل Socket Contract Layer

لا يحل ASIE System Bus محل ASIE Socket Contract Layer.

وتبقى مسؤولية فرض الالتزام التفصيلي بالعقود والسوكيتات من اختصاص Socket Contract Layer وفق AAS-16.

31. منع العقود التقنية

لا يجوز تمرير رسائل تعتمد على مزود خارجي بوصفه Contract.

ويجب أن تكون Contracts مجردة ومحايدة تجاه التقنيات.

القسم السابع: العلاقة مع Bus Controller
32. دور Bus Controller

يتولى Bus Controller إدارة Modules وContracts وSockets والتسجيل والتحقق التشغيلي.

ويتكامل ASIE System Bus معه عند الحاجة إلى:

التحقق من Destination.
التحقق من حالة Module.
التحقق من Socket Binding.
رفض Module أو عزلها.
تحديث Registry.
التعامل مع فشل Module مؤثر.
33. حدود العلاقة

لا يجوز لـ ASIE System Bus أن يدير Modules بدل Bus Controller.

كما لا يجوز لـ Bus Controller أن يتحول إلى قناة تمرير بديلة بدل ASIE System Bus.

34. إبلاغ Bus Controller

يجب إبلاغ Bus Controller عند وجود حالات مثل:

Module غير مسجلة تستقبل رسالة.
Module معزولة تحاول إرسال رسالة.
Socket Binding فاشل.
Contract غير صالح.
تكرار فشل رسائل مرتبط بـ Module.
محاولة اتصال مباشر.
القسم الثامن: العلاقة مع Heart Controller والقلوب
35. العلاقة مع Heart Controller

يتكامل ASIE System Bus مع Heart Controller في الحالات التي تؤثر فيها الرسائل على الحالة التشغيلية للقلوب.

ويشمل ذلك:

ضغط رسائل يؤثر على Primary Heart.
فشل Message Flow مرتبط بحالة Heart.
حاجة إلى دعم من Assist Heart.
حاجة إلى Reserve Heart أثناء Recovery.
حالة Degraded تؤثر على التمرير.
36. حدود العلاقة مع Heart Controller

لا يجوز لـ ASIE System Bus إدارة القلوب.

ولا يجوز لـ Heart Controller استخدام نفسه كمسار رسائل بديل بين Modules.

37. العلاقة مع ASIE Three Hearts

تتعامل القلوب مع الرسائل عبر القواعد المعتمدة في APP وASIE System Bus.

ولا يجوز لأي Heart تمرير رسائل Modules خارج ASIE System Bus أو اتخاذ قرار مستقل بتجاوز التدفق المعتمد.

القسم التاسع: العلاقة مع ASIE Kernel
38. العلاقة مع ASIE Kernel

تبدأ ASIE Kernel النظام وتهيئ الأساس التشغيلي.

ولا تعمل ASIE Kernel كمسار رسائل بين Modules.

39. منع تحويل Kernel إلى Bus

يُحظر تحويل ASIE Kernel إلى:

Message Router.
Event Broker.
Module Dispatcher.
Provider Gateway.
Direct Integration Layer.

وتبقى ASIE System Bus القناة الوحيدة لتمرير الرسائل.

القسم العاشر: الفشل والعزل
40. فشل الرسالة

عند فشل رسالة، يجب أن يحدد ASIE System Bus حالة الفشل ويمنع انتقال أثره.

ويجب التعامل مع الفشل وفق:

APP.
Contract.
Socket.
Retry Policy عند وجودها.
Timeout Policy عند وجودها.
Security Context.
الحالة التشغيلية للنظام.
41. منع إعادة المحاولة غير المحدودة

لا يجوز لـ ASIE System Bus تنفيذ Retry غير محدود.

ويجب أن تكون أي إعادة محاولة:

محدودة.
مبررة.
مرتبطة بسياسة معتمدة.
غير مسببة لتضخيم الحمل.
غير مؤدية إلى انهيار القلوب أو Modules.
42. عزل التدفق

يجوز عزل Message Flow إذا ثبت أنه يسبب خطرًا تشغيليًا.

وتشمل أسباب العزل:

تكرار فشل الرسائل.
Payload غير صالح متكرر.
مصدر غير موثوق.
محاولة تجاوز APP.
ضغط غير طبيعي على النظام.
فشل مرتبط بـ Module معطلة.
43. عزل Module من منظور الرسائل

إذا كانت Module معزولة، يجب على ASIE System Bus منع إرسال الرسائل إليها أو منها، وفق الحالة المعتمدة من Bus Controller وRegistry.

44. إبلاغ الفشل

عند وجود فشل مؤثر، يجب إبلاغ:

Bus Controller إذا تعلق الفشل بـ Module أو Socket أو Contract.
Heart Controller إذا أثر الفشل على القلوب أو الحمل.
Registry إذا تغيرت حالة مكون.
Security Layer وفق AAS-20 إذا كان الفشل أمنيًا.
القسم الحادي عشر: الأمان
45. Zero Trust في ASIE System Bus

تخضع جميع الرسائل داخل ASIE System Bus لمبدأ Zero Trust.

ولا تُقبل أي رسالة بسبب وجودها داخل النظام فقط.

46. Security Context إلزامي

يجب أن تحمل كل رسالة Security Context صالحًا.

ولا يجوز تمرير أي رسالة لا يمكن التحقق من سياقها الأمني.

47. منع إساءة استخدام الرسائل

يجب أن يمنع ASIE System Bus استخدام الرسائل في:

تجاوز الصلاحيات.
الوصول إلى Module غير مصرح.
تمرير Payload غير مشروع.
استدعاء Provider دون Contract.
تنفيذ أمر خارج حدود الدور.
تسريب تفاصيل أمنية.
48. فشل التحقق الأمني

إذا فشل التحقق الأمني، يجب:

رفض الرسالة.
تسجيل الحالة.
عدم تمرير Payload.
إبلاغ المكون المختص وفق AAS-20.
منع إعادة المحاولة غير المضبوطة.
القسم الثاني عشر: الأداء
49. الأداء كقيد في ASIE System Bus

يُعد الأداء قيدًا تشغيليًا ملزمًا لـ ASIE System Bus.

ويجب أن يدعم:

تمريرًا منضبطًا للرسائل.
رفض الرسائل غير الصالحة مبكرًا.
تقليل Payload الزائد.
منع التدفقات غير المحدودة.
منع الضغط غير المبرر على القلوب.
منع استدعاء AI عند عدم الحاجة.
50. منع تضخم الرسائل

يُحظر استخدام الرسائل كحاويات عامة لبيانات غير لازمة.

ويجب أن تبقى Payload محدودة بما يتطلبه Contract.

51. حماية القلوب من ضغط الرسائل

يجب أن يدعم ASIE System Bus حماية القلوب من ضغط الرسائل غير المنضبط عبر:

رفض الرسائل غير الصالحة.
تطبيق Timeout Policy.
احترام Retry Policy.
إبلاغ Heart Controller عند وجود ضغط مؤثر.
عزل التدفقات الضارة.
القسم الثالث عشر: المحظورات الخاصة بـ ASIE System Bus
52. محظورات ASIE System Bus

يُحظر على ASIE System Bus ما يلي:

تنفيذ Business Logic.
تنفيذ Provider Logic.
إدارة Modules بدل Bus Controller.
إدارة القلوب بدل Heart Controller.
فرض العقود بدل Socket Contract Layer.
تمرير رسالة دون Contract.
تمرير رسالة دون Socket.
تمرير رسالة دون Security Context.
قبول مصدر مجهول.
قبول وجهة غير مسجلة.
تمرير رسائل خارج APP.
السماح باتصال مباشر بين Modules.
استخدام ASIE Kernel كقناة رسائل.
استخدام AI لإنتاج حقيقة نهائية.
تحويل نفسه إلى API خارجية.
53. مخالفة حدود ASIE System Bus

تُعد أي محاولة لتحويل ASIE System Bus إلى منفذ منطق أعمال أو قناة تكامل مباشر مخالفة معمارية.

ويجب عند اكتشافها:

رفض التغيير.
إعادة المسؤولية إلى المكون المختص.
مراجعة الأثر على AAS-01 وAAS-02 وAAS-11.
عدم اعتمادها إلا عبر Architecture Change Proposal (ACP) إذا كانت تمس Frozen Architecture.
القسم الرابع عشر: معايير التحقق من الالتزام
54. معايير قبول ASIE System Bus

يُقبل ASIE System Bus معماريًا إذا حقق الآتي:

جميع الرسائل تمر عبره.
لا يسمح باتصال مباشر بين Modules.
يقبل APP Messages فقط.
يتطلب Contract ID.
يتطلب Socket ID.
يتطلب Security Context.
يدعم التتبع عبر Message ID وCorrelation ID.
يرفض الرسائل غير الصالحة.
يدعم عزل الفشل.
لا ينفذ Business Logic.
لا يدير Modules أو Hearts.
لا يتصل بمزود خارجي مباشرة.
55. مؤشرات الانحراف المعماري

تُعد الحالات التالية مؤشرات انحراف:

Module تستدعي Module مباشرة.
ASIE System Bus يحتوي Business Rules.
ASIE System Bus يستدعي Provider خارجيًا.
ASIE Kernel تمرر رسائل بين Modules.
Heart Controller يعمل كMessage Router.
رسائل تمر دون Contract.
رسائل تمر دون Socket.
Payload تحمل Implementation خاص بمزود.
Retry غير محدود.
Error Flow يسبب فشلًا متسلسلًا.
القسم الخامس عشر: العلاقة مع وثائق AAS الأخرى
56. الوثائق المرتبطة

ترتبط هذه الوثيقة بالوثائق التالية:

AAS-01 — ASIE Constitution
AAS-02 — ASIE Operating Architecture
AAS-10 — ASIE Kernel Specification
AAS-11 — ASIE Platform Protocol (APP) Specification
AAS-12 — ASIE Heart Controller Specification
AAS-13 — ASIE Three Hearts Specification
AAS-14 — ASIE Bus Controller Specification
AAS-16 — ASIE Socket Contract Layer Specification
AAS-17 — ASIE Module Specification
AAS-18 — ASIE Message Flow Specification
AAS-20 — ASIE Zero Trust Security Specification
AAS-40 — ASIE AI Integration Specification
AAS-60 — ASIE API Specification

ولا يجوز لأي وثيقة منها أن تُفسر ASIE System Bus بما يسمح بتجاوزه أو تحويله إلى منفذ منطق أعمال أو قناة تكامل مباشر.

أحكام ختامية
57. الأثر الملزم

تُعد AAS-15 — ASIE System Bus Specification المرجع الرسمي الحاكم لتعريف ASIE System Bus ومسؤولياته وحدوده.

ويلتزم كل تصميم أو تنفيذ أو مراجعة أو تطوير متعلق بتمرير الرسائل داخل منصة ASIE بأحكام هذه الوثيقة.

58. حدود التعديل

لا يجوز تعديل دور ASIE System Bus أو إنشاء مسار رسائل بديل أو السماح باتصال مباشر بين Modules إلا عبر Architecture Change Proposal (ACP) معتمد إذا كان التغيير يمس Frozen Architecture.

59. الصفة النهائية

تُعتمد هذه الوثيقة بوصفها المواصفة الرسمية لـ ASIE System Bus ضمن ASIE Architecture Standard (AAS).

وبموجبها، يكون ASIE System Bus هو المسار التشغيلي الوحيد للرسائل داخل منصة ASIE، ولا يجوز لأي Module أو Heart أو مكون آخر تجاوزه أو استخدام قناة بديلة.

End of Document

ـــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــ

AAS-16 ASIE Socket Contract Layer Specification

ASIE Architecture Standard (AAS)
