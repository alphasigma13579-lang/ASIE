Document ID: AAS-17
Document Name: ASIE Module Specification
Version: 1.0.0
Status: Frozen
Classification: Enterprise Architecture Specification
Owner: ASIE Architecture Board
Authority: ASIE Architecture Board
Parent References:

AAS-01 — ASIE Constitution
AAS-02 — ASIE Operating Architecture
AAS-11 — ASIE Platform Protocol (APP) Specification
AAS-15 — ASIE System Bus Specification
AAS-16 — ASIE Socket Contract Layer Specification
Architecture: Frozen Architecture
Last Updated: 2026-07-11
AAS-17 — ASIE Module Specification
مواصفة ASIE Module
1. الغرض من الوثيقة

تُعد هذه الوثيقة المواصفة الرسمية لـ ASIE Module ضمن ASIE Architecture Standard (AAS).

تُحدد هذه الوثيقة تعريف Module، ومسؤولياتها، وحدودها، ودورة حياتها، وقواعد إضافتها وإزالتها واستبدالها وتعطيلها، وعلاقتها بـ ASIE Kernel وASIE System Bus وSocket Contract Layer وBus Controller.

ولا تُنشئ هذه الوثيقة نوعًا جديدًا من المكونات، ولا تسمح لـ Module بتجاوز ASIE System Bus، ولا تسمح لها بتعديل ASIE Kernel أو فرض مزود خارجي أو الاتصال المباشر بـ Module أخرى.

2. السلطة والمرجعية

تخضع هذه الوثيقة بالكامل لأحكام:

AAS-01 — ASIE Constitution
AAS-02 — ASIE Operating Architecture
AAS-11 — ASIE Platform Protocol (APP) Specification
AAS-15 — ASIE System Bus Specification
AAS-16 — ASIE Socket Contract Layer Specification

وفي حال تعارض أي نص في هذه الوثيقة مع AAS-01، تكون الأولوية الملزمة لـ AAS-01.

وفي حال تعارض أي تفصيل متعلق بـ Socket أو Contract مع AAS-16، تكون الأولوية لـ AAS-16 ما لم يخالف ذلك AAS-01 أو AAS-02.

3. تعريف ASIE Module

تُعد ASIE Module مكونًا قابلًا للإضافة أو الإزالة أو الاستبدال أو التعطيل داخل منصة ASIE دون تعديل ASIE Kernel.

وتعمل Module بوصفها وحدة تنفيذ محددة الوظيفة، ملتزمة بـ Socket وContract معتمدين، وتتبادل الرسائل عبر ASIE System Bus فقط.

4. القاعدة الدستورية للـ Module

تلتزم منصة ASIE بالقاعدة التالية:

Every replaceable capability is a Module.
Every Module is bound by Socket, Contract, and System Bus.

وبناءً على ذلك:

كل وظيفة قابلة للإضافة أو الإزالة تُعد Module.
لا تعمل Module دون Socket.
لا تعمل Module دون Contract.
لا تتصل Module مباشرة بـ Module أخرى.
لا تعدل Module ASIE Kernel.
لا تفرض Module مزودًا خارجيًا على النظام.
لا تتجاوز Module ASIE System Bus.
القسم الأول: نطاق ASIE Module
5. ما تحكمه هذه الوثيقة

تحكم هذه الوثيقة الجوانب التالية:

تعريف Module.
شروط قبول Module.
دورة حياة Module.
حدود Module.
علاقة Module بـ Socket وContract.
علاقة Module بـ ASIE System Bus.
علاقة Module بـ Bus Controller.
قابلية الإضافة والإزالة والاستبدال.
الفشل والعزل.
المحظورات الخاصة بـ Module.
6. ما لا تحكمه هذه الوثيقة

لا تحكم هذه الوثيقة:

تفاصيل ASIE Kernel.
إدارة القلوب.
تصميم ASIE System Bus.
تفاصيل Socket Contract Layer.
تفاصيل Zero Trust Security.
تفاصيل AI Integration.
تصميم API الخارجية.
تفاصيل Deployment.
تفاصيل قاعدة البيانات.

هذه الجوانب تُفصل في وثائق AAS المتخصصة.

القسم الثاني: خصائص Module
7. الخصائص المعتمدة

يجب أن تحقق كل Module الخصائص التالية:

قابلة للإضافة.
قابلة للإزالة.
قابلة للاستبدال.
قابلة للتعطيل.
قابلة للعزل.
ملتزمة بـ Socket.
ملتزمة بـ Contract.
ملتزمة بـ APP.
ملتزمة بـ ASIE System Bus.
غير معدلة لـ ASIE Kernel.
غير معتمدة على اتصال مباشر بـ Module أخرى.
غير فارضة لمزود خارجي محدد.
8. Module كضيف على النظام

تُعد Module ضيفًا على منصة ASIE.

ولا يجوز لـ Module أن تفرض بنيتها أو متطلباتها أو مزودها أو منطقها على ASIE Kernel أو ASIE System Bus أو Heart Controller.

9. Module كقدرة قابلة للاستبدال

تمثل Module قدرة محددة يمكن استبدالها بقدرة أخرى تحقق نفس Socket وContract.

ولا يجوز أن يكون استبدال Module سببًا لتعديل ASIE Kernel.

10. أمثلة على Modules

تشمل أمثلة Modules، دون إضافة حصر معماري جديد:

AI
Geo
Export
Reports
Payment
OCR
Search
Notification

ويجب أن تلتزم كل Module من هذه الأمثلة بذات القواعد الدستورية والمعمارية.

القسم الثالث: شروط قبول Module
11. شروط القبول المعماري

تُقبل Module معماريًا إذا حققت الشروط التالية:

تحقق Socket معتمدًا.
تحقق Contract معتمدًا.
تمر رسائلها عبر ASIE System Bus.
تلتزم بـ APP.
لا تعدل ASIE Kernel.
لا تتصل مباشرة بـ Module أخرى.
لا تعتمد على مزود خارجي بوصفه مرجع التكامل.
قابلة للعزل.
قابلة للإزالة دون إسقاط النظام.
قابلة للاستبدال دون تعديل النواة.
لا تستخدم AI كمصدر حقيقة في المجالات المحظورة.
12. شروط الرفض المعماري

تُرفض Module إذا تحقق أي مما يلي:

تحتاج تعديل ASIE Kernel.
تعمل دون Socket.
تعمل دون Contract.
تتصل مباشرة بـ Module أخرى.
تتجاوز ASIE System Bus.
تفرض مزودًا خارجيًا.
تحتوي منطقًا يجب أن يكون حتميًا لكنها تنفذه عبر AI.
لا يمكن عزلها.
لا يمكن إزالتها دون إسقاط النظام.
تكسر Message Flow.
تضعف Zero Trust.
تسبب حملًا غير مبرر على القلوب.
13. منع الاستثناءات

لا يجوز قبول Module مخالفة بحجة السرعة أو الأولوية التجارية أو سهولة التنفيذ.

وأي استثناء يمس Frozen Architecture يجب أن يمر عبر Architecture Change Proposal (ACP) معتمد.

القسم الرابع: دورة حياة Module
14. مراحل دورة الحياة

تمر Module بالمراحل التالية:

Declaration.
Discovery.
Registration.
Contract Validation.
Socket Binding.
Security Validation.
Activation.
Execution.
Health Monitoring.
Suspension.
Isolation.
Deactivation.
Removal.
Replacement.

ولا يجوز تجاوز Contract Validation أو Socket Binding أو Security Validation.

15. Declaration

تعلن Module عن قدراتها ومتطلباتها وفق Contracts مجردة.

ولا يجوز أن تعلن اعتمادًا مباشرًا على Module أخرى أو مزود خارجي محدد.

16. Discovery

يجوز اكتشاف Module ضمن الآليات التشغيلية المعتمدة.

ولا يعني اكتشاف Module قبولها أو تشغيلها.

17. Registration

تُسجل Module عبر الجهة المختصة في Registry وفق القواعد التشغيلية.

ولا يُعد التسجيل تصريحًا نهائيًا للتشغيل ما لم تكتمل Validation وBinding.

18. Contract Validation

تخضع Module للتحقق من التزامها بـ Contract معتمد.

ولا يجوز تفعيل Module تفشل في Contract Validation.

19. Socket Binding

تُربط Module بـ Socket معتمد.

ولا يجوز لـ Module إرسال أو استقبال APP Messages قبل نجاح Socket Binding.

20. Security Validation

تخضع Module للتحقق الأمني وفق Zero Trust.

ولا يجوز تشغيل Module لا تملك Security Context صالحًا أو حدود صلاحيات واضحة.

21. Activation

تُفعّل Module بعد اجتياز الشروط المطلوبة.

ويجب أن يكون التفعيل:

خاضعًا لـ Bus Controller.
ملتزمًا بـ Registry.
متوافقًا مع الحالة التشغيلية للنظام.
غير مسبب لتجاوز ASIE System Bus.
22. Execution

أثناء التنفيذ، تلتزم Module بما يلي:

تنفيذ وظيفتها المحددة.
استقبال الرسائل عبر ASIE System Bus.
إرسال الرسائل عبر ASIE System Bus.
احترام Contract.
احترام Socket.
احترام APP.
عدم تنفيذ مهام خارج نطاقها.
23. Health Monitoring

يجب أن تكون Module قابلة للمراقبة من حيث الحالة التشغيلية والصحية.

وقد تشمل الحالة:

Active.
Suspended.
Isolated.
Failed.
Degraded.
Removed.
24. Suspension

يجوز تعليق Module مؤقتًا إذا تطلبت الحالة التشغيلية ذلك.

ويجب عند التعليق:

منع استقبال رسائل جديدة حسب الحالة.
تحديث Registry.
إبلاغ ASIE System Bus.
إبلاغ Bus Controller.
إبلاغ Heart Controller عند وجود أثر تشغيلي.
25. Isolation

تُعزل Module إذا سببت خطرًا أو خالفت Socket أو Contract أو APP أو Security Context.

ويجب أن يمنع العزل انتشار الفشل إلى بقية النظام.

26. Deactivation

يجوز إيقاف Module منظمًا دون إعادة نشر النظام.

ويجب أن يتم الإيقاف بطريقة لا تكسر Message Flow أو تسقط Modules أخرى.

27. Removal

يجوز إزالة Module إذا لم تعد مطلوبة أو إذا فشلت في الالتزام.

ويجب أن تتم الإزالة دون تعديل ASIE Kernel.

28. Replacement

يجوز استبدال Module بأخرى إذا كانت البديلة تحقق نفس Socket وContract.

ولا يجوز أن يتطلب الاستبدال تعديل ASIE Kernel أو تجاوز ASIE System Bus.

القسم الخامس: علاقة Module بـ Socket وContract
29. الالتزام بـ Socket

لا تعمل Module دون Socket معتمد.

ويُعد Socket شرط الدخول الرسمي للـ Module إلى منصة ASIE.

30. الالتزام بـ Contract

لا تعمل Module دون Contract معتمد.

ويحدد Contract حدود الرسائل والوظائف والقيود التي تلتزم بها Module.

31. منع تجاوز Socket Contract Layer

لا يجوز لـ Module تجاوز ASIE Socket Contract Layer.

ولا يجوز لها إرسال أو استقبال رسائل خارج Socket Binding صالح.

32. منع العقود التقنية

لا يجوز لـ Module فرض Contract قائم على مزود خارجي محدد.

ويجب أن تتعامل Module مع القدرات عبر عقود مجردة مثل:

IAIProvider
IGeoProvider
IPaymentProvider
ISearchProvider
INotificationProvider
القسم السادس: علاقة Module بـ ASIE System Bus
33. ASIE System Bus هو المسار الوحيد

يجب أن تمر جميع رسائل Module عبر ASIE System Bus.

ولا يجوز لـ Module أن تتصل مباشرة بـ Module أخرى.

34. منع الاتصال المباشر

يُحظر على Module القيام بما يلي:

استدعاء Module أخرى مباشرة.
مشاركة حالة داخلية مباشرة مع Module أخرى.
تجاوز ASIE System Bus لاعتبارات الأداء.
إنشاء قناة جانبية للرسائل.
الاتصال بمزود خارجي دون Contract.
35. الرسائل الصادرة من Module

يجب أن تكون كل رسالة صادرة من Module:

APP-compliant.
مرتبطة بـ Contract ID.
مرتبطة بـ Socket ID.
ذات Source معروف.
ذات Destination معتمدة.
تحمل Security Context صالحًا.
36. الرسائل الواردة إلى Module

لا يجوز لـ Module قبول رسالة واردة إلا إذا كانت:

قادمة عبر ASIE System Bus.
متوافقة مع APP.
مرتبطة بـ Contract.
مرتبطة بـ Socket.
مصرحًا بها أمنيًا.
مطابقة للـ Payload المتوقع.
القسم السابع: علاقة Module بـ ASIE Kernel
37. عدم تعديل ASIE Kernel

لا يجوز لأي Module تعديل ASIE Kernel أو مطالبتها بتغيير مسؤولياتها.

38. عدم الاعتماد على تفاصيل النواة

لا يجوز لـ Module الاعتماد على تفاصيل داخلية غير منصوص عليها في Contract.

ويجب أن يكون تعامل Module مع المنصة عبر Socket وContract وASIE System Bus فقط.

39. منع نقل منطق Module إلى Kernel

لا يجوز نقل منطق Module إلى ASIE Kernel بدعوى المشاركة أو الأداء أو التبسيط.

ويجب أن تبقى الوظائف القابلة للاستبدال خارج ASIE Kernel.

القسم الثامن: علاقة Module بـ Bus Controller
40. Bus Controller يدير Modules

تخضع Module لإدارة Bus Controller من حيث:

التسجيل.
التحقق.
التفعيل.
التعطيل.
العزل.
الإزالة.
حالة الالتزام.
41. عدم تجاوز Bus Controller

لا يجوز لـ Module تفعيل نفسها أو تسجيل نفسها أو فرض تشغيلها خارج Bus Controller.

42. إبلاغ Bus Controller

يجب إبلاغ Bus Controller عند:

فشل Module.
مخالفة Contract.
فشل Socket Binding.
تدهور الحالة.
الحاجة إلى تعليق أو عزل.
انتهاء صلاحية التشغيل.
محاولة تجاوز ASIE System Bus.
القسم التاسع: علاقة Module بـ Heart Controller والقلوب
43. عدم إدارة القلوب

لا يجوز لـ Module إدارة Heart أو تفعيل Heart أو عزل Heart أو التأثير المباشر في توزيع الأحمال.

44. العلاقة التشغيلية غير المباشرة

إذا أثرت Module على الحمل أو الفشل أو الحالة التشغيلية، يتم إبلاغ المكونات المختصة عبر ASIE System Bus وBus Controller وHeart Controller حسب القواعد المعتمدة.

45. منع الاعتماد على Heart محدد

لا يجوز لـ Module أن تعتمد على Heart محدد لتنفيذها خارج ما تسمح به البنية التشغيلية.

القسم العاشر: علاقة Module بالمزودين الخارجيين
46. المزود خلف Contract

إذا احتاجت Module إلى مزود خارجي، يجب أن يكون ذلك خلف Contract معتمد.

ولا يجوز أن تفرض Module المزود على ASIE Kernel أو على النظام ككل.

47. منع المزود المباشر

يُحظر أن تصبح Module مجرد غلاف مباشر لمزود بطريقة تكسر التجريد المعماري.

ويجب أن تبقى العلاقة مع المزود قابلة للاستبدال وفق Contract.

48. حياد التقنية

تلتزم Module بالحياد تجاه التقنية من منظور ASIE.

ولا يجوز لها أن تكسر قابلية الاستبدال بربط تدفق النظام بمزود محدد.

القسم الحادي عشر: علاقة Module بـ AI
49. AI كـ Module أو Provider

يُعامل AI داخل ASIE بوصفه Module أو Provider خلف Contract معتمد.

ولا يجوز أن يكون AI جزءًا من ASIE Kernel أو مصدر حقيقة نهائية.

50. حدود AI داخل Module

إذا استخدمت Module الذكاء الاصطناعي، يجب أن تلتزم بالآتي:

AI يشرح ولا يملك الحقيقة النهائية.
الحسابات الحتمية تنتجها كود حتمي.
القرارات المالية والقانونية والرياضية لا تصدر من AI كمصدر حقيقة.
لا تُستخدم مخرجات AI لتجاوز Contract.
لا تُستخدم مخرجات AI لتجاوز Security Context.
القسم الثاني عشر: الفشل والعزل
51. فشل Module

تُعد Module في حالة فشل إذا:

توقفت عن الاستجابة.
خالفت Contract.
خالفت Socket.
أرسلت رسائل غير صالحة.
تسببت بضغط غير طبيعي.
فشلت أمنيًا.
حاولت تجاوز ASIE System Bus.
أثرت على استقرار المنصة.
52. إجراءات عزل Module

عند عزل Module، يجب:

منع استقبال رسائل جديدة.
منع إرسال رسائل غير مصرح بها.
تحديث Registry.
إبلاغ Bus Controller.
إبلاغ ASIE System Bus.
إبلاغ Heart Controller عند وجود أثر تشغيلي.
حفظ الحالة عند الإمكان.
استمرار بقية Modules في العمل إن أمكن.
53. منع انتشار الفشل

لا يجوز أن يؤدي فشل Module واحدة إلى انهيار منصة ASIE.

ويجب احتواء الفشل في حدود Module أو تدفق الرسائل المتأثر قدر الإمكان.

54. إعادة تفعيل Module

لا يجوز إعادة تفعيل Module معزولة أو فاشلة إلا بعد تحقق جديد من:

Contract.
Socket.
Security Context.
الحالة التشغيلية.
عدم تأثيرها على الأداء والاستقرار.
القسم الثالث عشر: الأمان
55. Zero Trust للـ Module

تخضع كل Module لمبدأ Zero Trust.

ولا تُمنح Module الثقة بسبب تسجيلها أو وجودها داخل النظام.

56. أقل صلاحية لازمة

يجب أن تعمل Module بأقل صلاحية لازمة لتنفيذ وظيفتها.

ولا يجوز منحها صلاحيات عامة أو غير محددة.

57. منع التصعيد

يُحظر على Module استخدام الرسائل أو العقود أو السوكيتات لتجاوز صلاحياتها أو الوصول إلى مكونات غير مصرح بها.

القسم الرابع عشر: الأداء
58. الأداء كقيد للـ Module

يُعد الأداء قيدًا إلزاميًا على Module.

ولا يجوز أن تسبب Module:

استهلاكًا زائدًا بلا مبرر.
رسائل متكررة غير لازمة.
Payload زائد.
استدعاء AI عند عدم الحاجة.
تحميلًا غير مبرر على القلوب.
تعطيل ASIE System Bus.
تدهورًا غير مقبول في النظام.
59. منع تحسينات الأداء المخالفة

لا يجوز لـ Module تجاوز ASIE System Bus أو Contract أو Socket بحجة تحسين الأداء.

ويجب معالجة الأداء ضمن الحدود المعمارية المعتمدة.

القسم الخامس عشر: المحظورات الخاصة بـ Module
60. محظورات Module

يُحظر على أي Module ما يلي:

تعديل ASIE Kernel.
العمل دون Socket.
العمل دون Contract.
تجاوز ASIE System Bus.
الاتصال المباشر بـ Module أخرى.
إدارة Heart.
إدارة Module أخرى.
فرض مزود خارجي.
تنفيذ AI كحقيقة نهائية.
كسر APP.
تجاوز Security Context.
الاحتفاظ بحالة تكسر العزل.
منع الاستبدال أو الإزالة.
تحويل نفسها إلى Kernel أو Bus أو Controller.
استخدام قناة جانبية للرسائل.
61. مخالفة حدود Module

تُعد أي مخالفة من Module لحدودها المعمارية مخالفة مباشرة.

ويجب عند اكتشافها:

رفض التشغيل أو الاستمرار.
عزل Module.
تحديث Registry.
إبلاغ Bus Controller.
إبلاغ ASIE System Bus.
إبلاغ Heart Controller عند وجود أثر تشغيلي.
مراجعة المخالفة وفق AAS-01 وAAS-02 وAAS-16.
القسم السادس عشر: معايير التحقق من الالتزام
62. معايير قبول Module

تُقبل Module معماريًا إذا تحققت المعايير التالية:

تحقق Socket معتمدًا.
تحقق Contract معتمدًا.
تمر الرسائل عبر ASIE System Bus فقط.
تلتزم بـ APP.
لا تعدل ASIE Kernel.
لا تتصل مباشرة بـ Module أخرى.
قابلة للعزل.
قابلة للإزالة.
قابلة للاستبدال.
لا تفرض مزودًا خارجيًا.
لا تستخدم AI كمصدر حقيقة نهائية.
لا تسبب فشلًا متسلسلًا.
63. مؤشرات الانحراف المعماري

تُعد الحالات التالية مؤشرات انحراف:

Module تحتاج تعديل ASIE Kernel.
Module تستدعي Module أخرى مباشرة.
Module تعمل دون Socket Binding.
Module ترسل رسائل خارج ASIE System Bus.
Module مرتبطة بمزود خارجي في Contract.
Module غير قابلة للعزل.
Module تعطل النظام عند فشلها.
Module تستخدم AI لإنتاج قيمة مالية أو قانونية أو رياضية نهائية.
Module تحتفظ بحالة تكسر الاستبدال.
القسم السابع عشر: العلاقة مع وثائق AAS الأخرى
64. الوثائق المرتبطة

ترتبط هذه الوثيقة بالوثائق التالية:

AAS-01 — ASIE Constitution
AAS-02 — ASIE Operating Architecture
AAS-10 — ASIE Kernel Specification
AAS-11 — ASIE Platform Protocol (APP) Specification
AAS-14 — ASIE Bus Controller Specification
AAS-15 — ASIE System Bus Specification
AAS-16 — ASIE Socket Contract Layer Specification
AAS-18 — ASIE Message Flow Specification
AAS-20 — ASIE Zero Trust Security Specification
AAS-40 — ASIE AI Integration Specification
AAS-50 — ASIE Plugin Development SDK
AAS-60 — ASIE API Specification

ولا يجوز لأي وثيقة منها أن تُفسر Module بما يسمح لها بتعديل ASIE Kernel أو تجاوز ASIE System Bus أو العمل دون Socket وContract.

أحكام ختامية
65. الأثر الملزم

تُعد AAS-17 — ASIE Module Specification المرجع الرسمي الحاكم لتعريف ASIE Module ومسؤولياتها وحدودها ودورة حياتها.

ويلتزم كل تصميم أو تنفيذ أو مراجعة أو تطوير متعلق بأي Module داخل منصة ASIE بأحكام هذه الوثيقة.

66. حدود التعديل

لا يجوز تعديل شروط قبول Module أو السماح لها بتجاوز Socket أو Contract أو ASIE System Bus إلا عبر Architecture Change Proposal (ACP) معتمد إذا كان التغيير يمس Frozen Architecture.

67. الصفة النهائية

تُعتمد هذه الوثيقة بوصفها المواصفة الرسمية لـ ASIE Module ضمن ASIE Architecture Standard (AAS).

وبموجبها، تُعد كل Module قدرة قابلة للإضافة والإزالة والاستبدال والتعطيل، ولا تعمل داخل ASIE إلا عبر Socket وContract وASIE System Bus، ودون تعديل ASIE Kernel.

End of Document

ـــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــ

AAS-18 ASIE Message Flow Specification
ASIE Architecture Standard (AAS)

---

# ملحق رسمي: ASIE Market Intelligence Module

## قرار الاعتماد

يُعتمد **ASIE Market Intelligence Module** بوصفه Module رسميًا داخل **AAS-17 — ASIE Module Specification**، ولا يُعتمد بوصفه Layer مستقلة أو مكونًا موازيًا لـ ASIE Kernel أو APP أو ASIE System Bus أو Socket Contract Layer.

الاسم الرسمي المعتمد:

```text
ASIE Market Intelligence Module
```

الاسم غير المعتمد:

```text
Market Data Layer
```

## التعريف

يُعد **ASIE Market Intelligence Module** موديولًا رسميًا مسؤولًا عن جمع، تطبيع، تقييم، وتغليف بيانات السوق ضمن **Evidence Packs** قابلة للاستهلاك من بقية موديولات ASIE عبر **Socket Contracts** فقط.

لا يجوز لهذا الموديول أن يكون مصدر قرار مالي نهائي، ولا يجوز له توليد أرقام مالية تقديرية بواسطة الذكاء الاصطناعي. تقتصر مسؤوليته على توفير بيانات سوقية موثقة، مصنفة، ومقيدة بالمصادر المصرح بها.

## المسؤوليات المسموحة

- جلب بيانات السوق من المصادر المعتمدة.
- توحيد البيانات الخام إلى Market Evidence منظمة.
- بناء Evidence Packs تتضمن المصدر، التاريخ، النطاق الجغرافي، درجة الثقة، وطريقة الاستخراج.
- فلترة القيم الشاذة للأسعار وفق قواعد حتمية.
- توفير السياق الجغرافي للسوق بناءً على GPS أو اختيار الخريطة أو Pin.
- استخدام RAG Cache أو Vector DB لتقليل الزمن والتكلفة دون تحويلها إلى مصدر سلطة.
- تمرير Market Evidence إلى Finance Engine أو Analysis Modules أو AI Integration عبر Socket Contracts فقط.
- حفظ بيانات صحة المصادر وحداثة الكاش وقابلية التتبع.

## المسؤوليات المحظورة

- لا يجوز له تحليل مشاريع خارج الدولة المدعومة حاليًا.
- لا يجوز له توليد أرقام مالية بواسطة AI.
- لا يجوز له استبدال Finance Engine.
- لا يجوز له الاتصال المباشر بأي Module آخر.
- لا يجوز له تحويل Tavily أو Google أو Pinecone أو Supabase أو أي Provider إلى سلطة معمارية.
- لا يجوز له تخزين الحقيقة النهائية خارج Database Architecture المعتمدة.
- لا يجوز له تمرير بيانات سوق خام غير متحققة مباشرة إلى AI Agents.
- لا يجوز له تجاوز APP أو Socket Contract Layer أو ASIE System Bus أو Bus Controller أو Zero Trust.

## مصادر البيانات المعتمدة نوعيًا

| Source Family | الدور |
|---|---|
| SAMA | بيانات مالية واقتصادية مرجعية |
| GASTAT | إحصاءات سعودية ومؤشرات مناطقية |
| Monsha'at | نماذج ومنظومة المنشآت الصغيرة والمتوسطة |
| Social Development Bank | نماذج وتمويل ومراجع مشاريع صغيرة ومتوسطة |
| MISA | فرص استثمارية وسياق القطاعات |
| PIF | اتجاهات استراتيجية وقطاعية |
| World Bank | سياق اقتصادي كلي للمملكة |
| McKinsey and similar reports | رؤى سوقية استراتيجية مع توثيق المصدر |
| Riyad Capital / Al Rajhi Capital / SNB Capital | تقارير سوقية وقطاعية سعودية |
| Noon / Amazon / Alibaba | أسعار مرجعية احتياطية تخضع لفلترة القيم الشاذة |
| Tavily / Google Search / GDELT / RSS | آليات بحث فقط وليست سلطات معمارية |

## تصنيف البيانات

| Data Type | Classification | Notes |
|---|---|---|
| Public economic indicators | Public / Verified | يجب تضمين المصدر والتاريخ |
| Supplier prices | Commercial Evidence | يجب تضمين طريقة الاستخراج ودرجة الثقة |
| Location context | Sensitive Context | يخضع لسياسة GPS وMap Consent |
| User project context | User Data | لا يرسل للمزودين إلا بعقد مصرح |
| Cached market evidence | Governed Evidence | يجب تضمين الحداثة وسلسلة المصدر |

