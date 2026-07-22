Document ID: AAS-31
Document Name: ASIE Infrastructure Architecture
Version: 1.0.0
Status: Frozen
Classification: Enterprise Architecture Specification
Owner: ASIE Architecture Board
Authority: ASIE Architecture Board
Parent References:

AAS-01 — ASIE Constitution
AAS-02 — ASIE Operating Architecture
AAS-20 — ASIE Zero Trust Security Specification
AAS-30 — ASIE Deployment Architecture
Architecture: Frozen Architecture
Last Updated: 2026-07-11
AAS-31 — ASIE Infrastructure Architecture
معمارية البنية التحتية لمنصة ASIE
1. الغرض من الوثيقة

تُعد هذه الوثيقة المرجع الرسمي الحاكم لـ ASIE Infrastructure Architecture ضمن ASIE Architecture Standard (AAS).

تحدد هذه الوثيقة القواعد المعمارية الملزمة للبنية التحتية التي تستضيف وتشغل منصة ASIE، بما يشمل الحوسبة، والشبكات، والعزل، والأسرار، والمراقبة، والتوافر، والتعافي، والاعتماد على المزودين، دون تغيير Frozen Architecture أو فرض مزود بنية تحتية بعينه.

ولا تُعد هذه الوثيقة وثيقة تنفيذ تفصيلية، ولا تحدد أسماء أدوات أو خدمات بعينها إلا إذا اعتمدتها وثيقة AAS متخصصة.

2. السلطة والمرجعية

تخضع هذه الوثيقة لأحكام:

AAS-01 — ASIE Constitution
AAS-02 — ASIE Operating Architecture
AAS-10 — ASIE Kernel Specification
AAS-15 — ASIE System Bus Specification
AAS-16 — ASIE Socket Contract Layer Specification
AAS-20 — ASIE Zero Trust Security Specification
AAS-30 — ASIE Deployment Architecture
AAS-32 — ASIE Database Architecture

وفي حال تعارض أي نص في هذه الوثيقة مع AAS-01، تكون الأولوية الملزمة لـ AAS-01.

3. تعريف ASIE Infrastructure Architecture

يُقصد بـ ASIE Infrastructure Architecture النموذج المعماري الذي يحدد قدرات البنية التحتية اللازمة لتشغيل ASIE بصورة آمنة، قابلة للعزل، قابلة للتوسع، قابلة للمراقبة، وقابلة للتعافي.

وتشمل هذه القدرات:

Compute.
Network.
Runtime Isolation.
Secrets Management.
Storage Infrastructure.
Observability Infrastructure.
Security Enforcement.
Availability.
Recovery.
Provider Abstraction.
Operational Boundaries.
4. القاعدة الدستورية للبنية التحتية

تلتزم منصة ASIE بالقاعدة التالية:

Infrastructure hosts the architecture.
Infrastructure must not become the architecture.

وبناءً على ذلك:

لا يجوز للبنية التحتية أن تعيد تعريف ASIE Kernel.
لا يجوز للبنية التحتية أن تنشئ قناة بديلة لـ ASIE System Bus.
لا يجوز للبنية التحتية أن تمنح ثقة ضمنية.
لا يجوز للبنية التحتية أن تكسر حدود Module.
لا يجوز للبنية التحتية أن تربط ASIE بمزود واحد بصورة غير قابلة للاستبدال.
لا يجوز للبنية التحتية أن تعطل APP أو Contract أو Socket.
لا يجوز للبنية التحتية أن تتحول إلى مصدر الحقيقة النهائية للنظام.
القسم الأول: نطاق Infrastructure Architecture
5. ما تحكمه هذه الوثيقة

تحكم هذه الوثيقة:

Compute Architecture.
Network Architecture.
Runtime Isolation.
Infrastructure Security.
Identity and Access Boundaries.
Secrets Infrastructure.
Storage Infrastructure.
Observability Infrastructure.
Availability and Resilience.
Backup and Recovery Foundations.
Provider Independence.
Infrastructure Change Control.
Environment Separation.
6. ما لا تحكمه هذه الوثيقة

لا تحكم هذه الوثيقة:

منطق الأعمال داخل Modules.
تصميم APP.
تفاصيل Message Flow.
تفاصيل Database Schema.
تفاصيل CI/CD.
تفاصيل API الخارجية.
تفاصيل AI Provider Integration.
تصميم واجهات المستخدم.
اختيار أداة بنية تحتية محددة.

وتفصل هذه الجوانب في وثائق AAS المتخصصة.

القسم الثاني: مبادئ البنية التحتية
7. Architecture Compliance

يجب أن تلتزم البنية التحتية بـ Frozen Architecture.

ولا يجوز اعتماد أي بنية تحتية تتطلب تعديل المعمارية المعتمدة.

8. Zero Trust by Infrastructure

يجب أن تدعم البنية التحتية Zero Trust Security.

ولا يجوز أن تستند إلى الثقة بالشبكة الداخلية أو البيئة أو المزود.

9. Isolation First

يجب أن تدعم البنية التحتية العزل بين المكونات والبيئات والتدفقات.

ولا يجوز أن يؤدي فشل مكون واحد إلى انهيار كامل غير محتوى.

10. Provider Neutrality

يجب أن تحافظ البنية التحتية على قابلية الاستبدال أو النقل أو التجريد عن المزود متى كان ذلك معماريًا لازمًا.

11. Observability Native

يجب أن تكون البنية التحتية قابلة للمراقبة والتتبع والتدقيق من الأصل.

ولا يجوز تشغيل مكون حرج دون مؤشرات تشغيلية وأمنية كافية.

12. Recovery Ready

يجب أن تُصمم البنية التحتية بحيث تدعم التعافي من الفشل والكوارث دون كسر Security أو Frozen Architecture.

القسم الثالث: طبقات البنية التحتية
13. الطبقات المعتمدة

تتكون Infrastructure Architecture من الطبقات التالية:

Compute Layer.
Network Layer.
Runtime Layer.
Storage Layer.
Security Layer.
Observability Layer.
Recovery Layer.
Provider Abstraction Layer.
14. منع الخلط بين الطبقات

لا يجوز أن يؤدي تنفيذ البنية التحتية إلى خلط حدود الطبقات بما يسمح بـ:

تجاوز ASIE System Bus.
دمج Modules دون عزل.
إعطاء Runtime صلاحيات غير لازمة.
كشف Secrets.
تجاوز Security Context.
تحويل Storage إلى Message Bus غير معتمد.
استخدام Network كقناة جانبية بين Modules.
القسم الرابع: Compute Architecture
15. تعريف Compute

تُعد Compute Infrastructure القدرة المسؤولة عن تشغيل مكونات ASIE Runtime.

وتشمل، بحسب التنفيذ:

Application Runtimes.
Containers.
Virtual Machines.
Serverless Runtimes.
Worker Nodes.
Processing Units.
16. قواعد Compute

يجب أن تكون Compute Infrastructure:

قابلة للعزل.
قابلة للتوسع.
قابلة للمراقبة.
قابلة للتحديث.
قابلة للإزالة.
غير مالكة للمعمارية.
خاضعة لـ Zero Trust.
17. حدود Compute

لا يجوز لـ Compute Infrastructure:

تعديل ASIE Kernel.
تجاوز ASIE System Bus.
دمج Modules قسرًا.
منح صلاحيات عامة.
تخزين Secrets بصورة مكشوفة.
تمرير رسائل خارج APP.
اتخاذ قرارات معمارية نيابة عن AAS.
18. Compute Isolation

يجب أن تدعم Compute Infrastructure عزل:

ASIE Kernel Runtime.
ASIE System Bus Runtime.
Controllers.
Modules.
AI Integration Components.
API Layer.
Observability Components.
19. Resource Controls

يجب ضبط الموارد بما يمنع:

استهلاك مفرط من Module واحدة.
فشل متسلسل.
تضخم Retry.
ضغط غير مبرر على ASIE System Bus.
تعطيل القلوب.
إسقاط Runtime بالكامل.
القسم الخامس: Network Architecture
20. تعريف Network

تُعد Network Infrastructure القدرة المسؤولة عن الاتصال بين مكونات ASIE والأنظمة الخارجية وفق القواعد المعتمدة.

21. قواعد الشبكة

يجب أن تكون Network Architecture:

مقيدة.
قابلة للتدقيق.
خاضعة لـ Zero Trust.
غير معتمدة على الثقة الداخلية.
داعمة لعزل البيئات.
مانعة للقنوات الجانبية.
22. منع الثقة الشبكية

لا يجوز اعتبار الاتصال داخل الشبكة دليلًا على الثقة.

وتبقى كل رسالة أو عملية خاضعة لـ Identity وSecurity Context وAuthorization.

23. منع القنوات الجانبية

يُحظر استخدام Network لإنشاء اتصال مباشر بين Modules أو تجاوز ASIE System Bus.

24. Network Segmentation

يجب أن تدعم البنية التحتية تقسيمًا منطقيًا أو فعليًا مناسبًا بين:

Production.
Staging.
Testing.
Development.
Sandbox.
Recovery.
External Provider Access.
Observability Access.
25. Ingress وEgress

يجب ضبط Ingress وEgress وفق سياسة معتمدة.

ولا يجوز السماح بخروج أو دخول غير محدد أو غير قابل للتتبع.

القسم السادس: Runtime Architecture
26. تعريف Runtime

يُعد Runtime البيئة التنفيذية التي تعمل داخلها مكونات ASIE.

27. شروط Runtime

يجب أن يكون Runtime:

خاضعًا للمراقبة.
قابلًا للعزل.
قابلًا للتحديث.
قابلًا للتراجع.
محدود الصلاحيات.
متوافقًا مع Deployment Architecture.
غير مالك لمنطق الأعمال إلا في موضعه المعتمد.
28. Runtime Boundaries

يجب أن يحافظ Runtime على الحدود بين:

ASIE Kernel.
ASIE System Bus.
Bus Controller.
Heart Controller.
Modules.
Socket Contract Layer.
API Layer.
AI Integration.
External Provider Connectors.
29. Runtime Failure

عند فشل Runtime، يجب:

احتواء الفشل.
منع انتقاله إلى بقية المكونات.
تسجيل الحدث.
تفعيل Recovery عند الحاجة.
عدم تجاوز Security Context بحجة الاستعادة.
القسم السابع: Storage Infrastructure
30. تعريف Storage Infrastructure

تُعد Storage Infrastructure القدرة المسؤولة عن تخزين البيانات والملفات والسجلات والحالة التشغيلية حسب ما تسمح به وثائق AAS.

31. العلاقة مع Database Architecture

لا تُعرّف هذه الوثيقة بنية قواعد البيانات التفصيلية.

وتخضع قواعد البيانات وأشكال التخزين المنظم لـ AAS-32 — ASIE Database Architecture.

32. قواعد Storage

يجب أن يكون Storage:

مصنفًا حسب الحساسية.
محميًا.
قابلًا للتدقيق.
قابلًا للنسخ الاحتياطي.
قابلًا للاستعادة.
محدود الوصول.
غير مستخدم كقناة رسائل بديلة.
33. منع Storage كـ Bus

يُحظر استخدام Storage Infrastructure كبديل لـ ASIE System Bus.

ولا يجوز أن تصبح قواعد البيانات أو الملفات قناة جانبية للتواصل بين Modules.

34. Retention

يجب أن تخضع سياسات الاحتفاظ للغرض والحساسية والامتثال.

ولا يجوز الاحتفاظ ببيانات أو Logs أو Payloads حساسة دون مبرر معتمد.

القسم الثامن: Secrets Infrastructure
35. إدارة الأسرار

يجب أن توفر البنية التحتية قدرة آمنة لإدارة Secrets وCredentials.

36. قواعد Secrets

يجب أن تكون Secrets:

مخزنة بصورة آمنة.
محدودة النطاق.
قابلة للدوران.
قابلة للإبطال.
غير مضمنة في Code.
غير مكشوفة في Logs.
غير منقولة عبر APP Payload عادي.
37. الوصول إلى Secrets

لا يجوز لأي Module أو Service أو Runtime الوصول إلى Secret إلا إذا كان ذلك:

مصرحًا به.
مرتبطًا بهوية.
محدود النطاق.
قابلًا للتدقيق.
لازمًا للوظيفة المعتمدة.
38. تسرب Secrets

عند الاشتباه في تسرب Secret، يجب:

إبطال Secret.
تدويره.
عزل المكون المتأثر عند الحاجة.
تسجيل الحدث.
مراجعة أثر التسرب.
منع إعادة استخدامه.
القسم التاسع: Security Infrastructure
39. الأمن كبنية تحتية

يجب أن توفر البنية التحتية قدرات أمنية داعمة لـ Zero Trust.

وتشمل:

Identity Integration.
Access Control.
Network Policy.
Runtime Policy.
Secret Management.
Audit Logging.
Threat Detection.
Policy Enforcement.
40. منع الأمن الشكلي

لا يجوز اعتبار وجود أدوات أمنية كافيًا للالتزام الأمني.

والالتزام يتحقق فقط عند إنفاذ السياسات فعليًا على الهوية والرسائل والمكونات والتدفقات.

41. Infrastructure Policy Enforcement

يجب أن تفرض البنية التحتية السياسات عند:

الوصول إلى Runtime.
استدعاء Secrets.
الاتصال الشبكي.
الوصول إلى Storage.
تشغيل Deployment Unit.
استدعاء External Provider.
إرسال أو استقبال الرسائل.
القسم العاشر: Observability Infrastructure
42. تعريف Observability Infrastructure

تُعد Observability Infrastructure القدرة المسؤولة عن جمع وتحليل وعرض المؤشرات والسجلات والتتبعات والأحداث الأمنية والتشغيلية.

43. عناصر Observability

يجب أن تدعم البنية التحتية:

Logs.
Metrics.
Traces.
Health Checks.
Security Events.
Audit Events.
Message Flow Events.
Module State Events.
System Bus Events.
44. شروط Observability

يجب أن تكون Observability:

آمنة.
قابلة للتدقيق.
محدودة الوصول.
غير كاشفة للأسرار.
غير معطلة للأداء.
مرتبطة بـ Correlation ID عند الحاجة.
45. منع Observability غير الآمنة

يُحظر أن تحتوي Observability على:

Secrets.
Credentials.
Payloads حساسة دون مبرر.
Security Context كامل دون حاجة.
بيانات شخصية غير مصرح بها.
تفاصيل تساعد على تجاوز النظام.
القسم الحادي عشر: Availability and Resilience
46. التوافر

يجب أن تدعم البنية التحتية مستوى التوافر المطلوب لتشغيل ASIE وفق السياسات المعتمدة.

47. المرونة

يجب أن تُصمم البنية التحتية لاحتواء:

فشل Compute.
فشل Network.
فشل Runtime.
فشل Storage.
فشل Provider.
فشل Module.
فشل ASIE System Bus.
تدهور External Provider.
48. منع نقطة الفشل الواحدة

يجب تقليل Single Points of Failure في المكونات الحرجة.

ولا يجوز أن يعتمد تشغيل ASIE على عنصر واحد غير قابل للتعافي إذا كان ذلك يؤثر في Production.

49. Degraded Mode

يجوز تشغيل Degraded Mode إذا كان:

محددًا.
آمنًا.
قابلًا للتتبع.
لا يكسر Frozen Architecture.
لا يتجاوز Zero Trust.
لا يسمح برسائل غير مصرح بها.
القسم الثاني عشر: Backup and Recovery Infrastructure
50. النسخ الاحتياطي

يجب أن تدعم البنية التحتية Backup مناسبًا للبيانات والحالة والسجلات اللازمة.

51. شروط Backup

يجب أن تكون النسخ الاحتياطية:

محمية.
قابلة للاستعادة.
خاضعة للتحكم في الوصول.
مختبرة دوريًا.
غير كاشفة للأسرار.
متوافقة مع سياسات الاحتفاظ.
52. الاستعادة

يجب أن تتم Recovery دون:

كسر Security Context.
تعطيل Audit.
تجاوز ASIE System Bus.
دمج Modules.
استخدام بيانات غير مصرح بها.
إضعاف Zero Trust.
53. Recovery Objectives

يجب تحديد Recovery Objectives للمكونات الحرجة.

وتشمل:

RTO.
RPO.
Criticality.
Dependency Mapping.
Recovery Priority.
القسم الثالث عشر: Environment Separation
54. فصل البيئات

يجب أن تدعم البنية التحتية فصلًا واضحًا بين البيئات.

55. منع اختلاط البيئات

يُحظر:

استخدام Secrets إنتاجية في Development.
استخدام بيانات Production في Testing دون ضبط.
اتصال Sandbox بـ Production دون سياسة معتمدة.
نشر مكونات غير مختبرة في Production.
مشاركة Credentials بين البيئات.
تجاوز Security Gates بحجة التجربة.
56. اتساق البيئات

يجب أن تحافظ البيئات على اتساق معماري كافٍ للتحقق.

ولا يجوز أن تكون Production مختلفة معماريًا بصورة تجعل اختبارات Staging غير ذات معنى.

القسم الرابع عشر: Provider Abstraction
57. تجريد المزود

يجب أن تُدار علاقة ASIE بمزودي البنية التحتية بطريقة تحافظ على قابلية الاستبدال متى كان ذلك مطلوبًا معماريًا.

58. استخدام خصائص المزود

يجوز استخدام خصائص مزود محدد إذا كانت:

موثقة.
معزولة.
لا تكسر Frozen Architecture.
لا تمنع Recovery.
لا تمنع Rollback.
لا تمنح ثقة ضمنية.
لا تحول المزود إلى Architecture Owner.
59. منع Provider Lock-in

يُحظر الاعتماد على Provider بما يؤدي إلى:

تعطيل قابلية الاستبدال.
منع العزل.
كسر Recovery.
كسر Security.
فرض تعديل ASIE Kernel.
تجاوز ASIE System Bus.
تحويل Provider إلى مصدر الحقيقة النهائية.
القسم الخامس عشر: Infrastructure Change Control
60. ضبط تغييرات البنية التحتية

يجب أن تخضع تغييرات البنية التحتية لـ Change Control معتمد.

ويجب أن تكون:

موثقة.
قابلة للتتبع.
قابلة للتراجع عند الإمكان.
خاضعة لمراجعة أمنية.
خاضعة لمراجعة أثر معماري.
متوافقة مع Deployment Architecture.
61. منع التغييرات غير المصرح بها

يُحظر تنفيذ تغيير في البنية التحتية دون Authorization مناسب.

وتُعد التغييرات اليدوية غير الموثقة خطرًا معماريًا وأمنيًا.

62. Configuration Drift

يجب اكتشاف ومعالجة Configuration Drift.

ولا يجوز ترك الانحرافات التشغيلية تتراكم حتى تصبح معمارية فعلية غير معتمدة.

القسم السادس عشر: Infrastructure Failure
63. تعريف فشل البنية التحتية

يُعد Infrastructure Failure كل خلل في قدرات التشغيل الأساسية يؤثر في قدرة ASIE على الالتزام بـ AAS.

64. أنواع الفشل

تشمل أنواع الفشل:

Compute Failure.
Network Failure.
Runtime Failure.
Storage Failure.
Secrets Failure.
Observability Failure.
Security Enforcement Failure.
Provider Failure.
Recovery Failure.
Configuration Failure.
65. التعامل مع فشل البنية التحتية

عند حدوث فشل، يجب:

احتواء الفشل.
عزل النطاق المتأثر.
منع الفشل المتسلسل.
تسجيل الحدث.
تفعيل Recovery عند الحاجة.
منع تجاوز Zero Trust.
مراجعة السبب وفق Governance.
القسم السابع عشر: المحظورات
66. محظورات Infrastructure Architecture

يُحظر في Infrastructure Architecture ما يلي:

بنية تحتية تعيد تعريف المعمارية.
شبكة تمنح ثقة ضمنية.
Storage كبديل لـ ASIE System Bus.
Compute يدمج Modules دون عزل.
Runtime يمنح صلاحيات عامة.
Secrets داخل Code أو Logs.
Observability تكشف أسرارًا.
Provider غير قابل للعزل.
Recovery يتجاوز Zero Trust.
Environment Mixing غير معتمد.
تغييرات يدوية غير موثقة.
Configuration Drift غير معالج.
بنية تمنع Rollback أو Recovery.
قناة جانبية بين Modules عبر الشبكة أو التخزين.
اعتماد Provider كـ Truth Owner.
القسم الثامن عشر: معايير التحقق من الالتزام
67. معايير قبول Infrastructure Architecture

تُقبل Infrastructure Architecture إذا تحققت الشروط التالية:

تحافظ على Frozen Architecture.
تدعم Zero Trust.
تفصل بين البيئات.
تعزل المكونات الحرجة.
تحافظ على ASIE System Bus كقناة معتمدة.
تمنع القنوات الجانبية.
تدير Secrets بأمان.
توفر Observability آمنة.
تدعم Recovery.
تدعم Backup مناسبًا.
تمنع Provider Lock-in المؤثر.
تضبط Ingress وEgress.
تمنع Configuration Drift.
تدعم Change Control.
لا تمنح ثقة ضمنية لأي شبكة أو Runtime أو Provider.
68. مؤشرات الانحراف المعماري

تُعد الحالات التالية مؤشرات انحراف:

اعتماد الثقة على الشبكة الداخلية.
اتصال مباشر بين Modules عبر الشبكة.
استخدام قاعدة بيانات كقناة رسائل.
تخزين Secrets في Configuration مكشوفة.
فشل غير قابل للعزل.
بيئات غير مفصولة.
Observability تكشف Payload حساسًا.
Provider يفرض تعديلًا معماريًا.
Recovery يتجاوز Security.
Runtime بصلاحيات واسعة.
Drift غير موثق.
عدم القدرة على تتبع تغييرات البنية التحتية.
القسم التاسع عشر: العلاقة مع وثائق AAS الأخرى
69. العلاقة مع AAS-01

تستمد هذه الوثيقة سلطتها من AAS-01 — ASIE Constitution.

ولا يجوز تفسير البنية التحتية بما يسمح بكسر المبادئ الدستورية أو Frozen Architecture.

70. العلاقة مع AAS-02

تلتزم هذه الوثيقة بالبنية التشغيلية المحددة في AAS-02 — ASIE Operating Architecture.

71. العلاقة مع AAS-10

يجب أن تحمي البنية التحتية ASIE Kernel، ولا يجوز أن تسمح بتعديله أو تجاوزه.

72. العلاقة مع AAS-15

يجب أن تدعم البنية التحتية ASIE System Bus بوصفه قناة الرسائل المعتمدة، ولا يجوز أن تستبدله.

73. العلاقة مع AAS-20

تُعد Zero Trust Security شرطًا أساسيًا في Infrastructure Architecture، ولا يجوز تعطيله على مستوى الشبكة أو Runtime أو Provider.

74. العلاقة مع AAS-30

تُنفذ Deployment Architecture فوق Infrastructure Architecture، ويجب أن تتوافق البيئات وRuntime وRecovery مع قواعد النشر المعتمدة.

75. العلاقة مع AAS-32

تخضع قواعد البيانات والتخزين المنظم لـ AAS-32 — ASIE Database Architecture، بينما تحدد هذه الوثيقة القدرات التحتية العامة للتخزين والحماية والتعافي.

أحكام ختامية
76. الأثر الملزم

تُعد AAS-31 — ASIE Infrastructure Architecture المرجع الرسمي الحاكم للبنية التحتية التي تستضيف وتشغل منصة ASIE.

ويلتزم كل تصميم أو تنفيذ أو تشغيل أو مراجعة متعلق بالحوسبة أو الشبكة أو Runtime أو الأسرار أو التخزين أو المراقبة أو التعافي أو المزودين بأحكام هذه الوثيقة.

77. حدود التعديل

لا يجوز تعديل Infrastructure Architecture بما يمس Frozen Architecture أو يسمح بثقة ضمنية أو قناة جانبية أو Provider Lock-in مؤثر إلا عبر Architecture Change Proposal (ACP) معتمد.

78. الصفة النهائية

تُعتمد هذه الوثيقة بوصفها المواصفة الرسمية لـ ASIE Infrastructure Architecture ضمن ASIE Architecture Standard (AAS).

وبموجبها، لا تُعد أي بنية تحتية صالحة لمنصة ASIE إلا إذا استضافت المعمارية دون إعادة تعريفها، ودعمت Zero Trust، وحافظت على العزل والتتبع والتعافي، ومنعت تجاوز ASIE System Bus أو Socket أو Contract أو Frozen Architecture.

End of Document

ــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــ

AAS-32 ASIE Database Architecture

ASIE Architecture Standard (AAS)
