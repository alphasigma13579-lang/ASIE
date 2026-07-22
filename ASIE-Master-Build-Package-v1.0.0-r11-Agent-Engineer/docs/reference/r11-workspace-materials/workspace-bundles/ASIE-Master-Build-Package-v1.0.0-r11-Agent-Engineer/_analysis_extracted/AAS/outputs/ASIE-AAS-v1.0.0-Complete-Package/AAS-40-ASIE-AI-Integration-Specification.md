Document ID: AAS-40
Document Name: ASIE AI Integration Specification
Version: 1.0.0
Status: Frozen
Classification: Enterprise Architecture Specification
Owner: ASIE Architecture Board
Authority: ASIE Architecture Board
Parent References:

* AAS-01 — ASIE Constitution
* AAS-02 — ASIE Operating Architecture
* AAS-11 — ASIE Platform Protocol (APP) Specification
* AAS-15 — ASIE System Bus Specification
* AAS-16 — ASIE Socket Contract Layer Specification
* AAS-20 — ASIE Zero Trust Security Specification
  Architecture: Frozen Architecture
  Last Updated: 2026-07-11

# AAS-40 — ASIE AI Integration Specification

# مواصفة تكامل الذكاء الاصطناعي في منصة ASIE

## 1. الغرض من الوثيقة

تُعد هذه الوثيقة المرجع الرسمي الحاكم لتكامل الذكاء الاصطناعي داخل منصة ASIE ضمن ASIE Architecture Standard (AAS).

تحدد هذه الوثيقة القواعد الملزمة لاستخدام AI Models وAI Providers وAI Agents وAI Outputs داخل ASIE، بما يضمن أن الذكاء الاصطناعي يعمل كمكوّن مساعد خاضع للحوكمة، لا كسلطة معمارية، ولا كمصدر حقيقة نهائية، ولا كقناة لتجاوز ASIE Kernel أو ASIE System Bus أو Socket Contract Layer.

## 2. السلطة والمرجعية

تخضع هذه الوثيقة لأحكام:

* AAS-01 — ASIE Constitution
* AAS-02 — ASIE Operating Architecture
* AAS-10 — ASIE Kernel Specification
* AAS-11 — ASIE Platform Protocol (APP) Specification
* AAS-15 — ASIE System Bus Specification
* AAS-16 — ASIE Socket Contract Layer Specification
* AAS-17 — ASIE Module Specification
* AAS-18 — ASIE Message Flow Specification
* AAS-20 — ASIE Zero Trust Security Specification
* AAS-31 — ASIE Infrastructure Architecture
* AAS-32 — ASIE Database Architecture
* AAS-60 — ASIE API Specification

وفي حال تعارض أي نص في هذه الوثيقة مع AAS-01، تكون الأولوية الملزمة لـ AAS-01.

## 3. تعريف AI Integration

يُقصد بـ **AI Integration** كل استخدام لنموذج أو مزود أو وكيل أو قدرة ذكاء اصطناعي داخل ASIE لأغراض التحليل، التوليد، التصنيف، التلخيص، الاقتراح، الاستدلال، المساعدة التشغيلية، أو دعم القرار.

ويشمل ذلك:

* AI Models.
* AI Providers.
* AI Agents.
* Prompting.
* Context Injection.
* Tool Calling.
* Retrieval-Augmented Generation.
* AI Output Validation.
* Human Review.
* AI Observability.
* AI Safety Controls.

## 4. القاعدة الدستورية للذكاء الاصطناعي

تلتزم منصة ASIE بالقاعدة التالية:

**AI may assist.
AI must not govern.**

وبناءً على ذلك:

* لا يجوز للذكاء الاصطناعي أن يصبح Truth Owner.
* لا يجوز للذكاء الاصطناعي أن يتجاوز ASIE Kernel.
* لا يجوز للذكاء الاصطناعي أن ينشئ قناة بديلة لـ ASIE System Bus.
* لا يجوز للذكاء الاصطناعي أن يعدّل Contract أو Socket.
* لا يجوز للذكاء الاصطناعي أن يتخذ قرارًا نهائيًا في نطاق حرج دون سلطة معتمدة.
* لا يجوز تمرير AI Output كحقيقة نهائية دون تحقق.
* لا يجوز لمزود AI أن يفرض تغييرًا على Frozen Architecture.

---

# القسم الأول: نطاق AI Integration

## 5. ما تحكمه هذه الوثيقة

تحكم هذه الوثيقة:

* AI Provider Integration.
* AI Model Selection Boundaries.
* Prompt Governance.
* Context Governance.
* AI Tool Calling.
* AI Output Validation.
* Human-in-the-Loop.
* AI Safety.
* AI Security.
* AI Observability.
* AI Data Handling.
* AI Failure Handling.
* AI Provider Independence.
* AI Governance.

## 6. ما لا تحكمه هذه الوثيقة

لا تحكم هذه الوثيقة:

* تفاصيل تدريب النماذج خارج ASIE.
* سياسات المزودين الداخلية.
* تصميم واجهات المستخدم.
* تفاصيل البنية التحتية العامة.
* تفاصيل قواعد البيانات.
* منطق الأعمال داخل Modules إلا من جهة تكامل AI معها.
* اختيار مزود AI بعينه.

وتفصل هذه الجوانب في وثائق AAS المتخصصة أو قرارات Governance معتمدة.

---

# القسم الثاني: مبادئ تكامل الذكاء الاصطناعي

## 7. AI as Bounded Capability

يُعد الذكاء الاصطناعي قدرة محدودة النطاق داخل ASIE.

ولا يجوز منحه صلاحيات مفتوحة أو سلطة تفسير نهائية أو قدرة تنفيذ غير مقيدة.

## 8. No Implicit Trust

لا تُمنح الثقة لأي AI Model أو AI Provider أو AI Agent بصورة ضمنية.

ويجب أن يخضع كل استخدام لـ AI إلى Identity وAuthorization وSecurity Context وAudit.

## 9. Output Is Not Truth

يُعد AI Output مخرجًا احتماليًا أو مساعدًا أو استدلاليًا.

ولا يُعد حقيقة نهائية إلا بعد تحقق معتمد وفق طبيعة الاستخدام.

## 10. Contract-Governed AI

يجب أن يتكامل AI مع ASIE عبر APP وSocket Contract Layer وASIE System Bus عند تبادل الرسائل أو تنفيذ الأعمال داخل النظام.

## 11. Human Accountability

يجب أن تبقى المسؤولية النهائية عن القرارات الحرجة لدى جهة بشرية أو مكوّن حوكمي معتمد، لا لدى AI Model.

## 12. Provider Replaceability

يجب أن يحافظ تكامل AI على قابلية استبدال المزود أو النموذج متى كان ذلك لازمًا معماريًا.

---

# القسم الثالث: مكونات AI Integration

## 13. المكونات المعتمدة

يتكون AI Integration من المكونات المفاهيمية التالية:

* AI Integration Layer.
* AI Provider Adapter.
* Prompt Policy.
* Context Boundary.
* Tool Invocation Boundary.
* Output Validation Layer.
* Safety Guardrails.
* Audit and Observability Layer.
* Human Review Gate.
* Provider Abstraction.

## 14. منع تحويل AI إلى طبقة معمارية مستقلة

لا يجوز أن يتحول AI Integration إلى طبقة حاكمة فوق ASIE Kernel أو بديلة عن ASIE Operating Architecture.

ويجب أن يبقى خاضعًا للمعمارية المعتمدة.

---

# القسم الرابع: AI Provider Integration

## 15. تعريف AI Provider

يُقصد بـ AI Provider أي مزود خارجي أو داخلي يقدم نموذجًا أو خدمة ذكاء اصطناعي قابلة للاستدعاء من ASIE.

## 16. شروط AI Provider

لا يجوز اعتماد AI Provider إلا إذا أمكن ضبطه وفق:

* Security Context.
* Data Handling Policy.
* Access Control.
* Auditability.
* Provider Boundary.
* Failure Handling.
* Replaceability.
* Compliance Requirements.

## 17. حدود AI Provider

لا يجوز لـ AI Provider:

* امتلاك بيانات ASIE.
* فرض Truth Model على ASIE.
* تعديل Frozen Architecture.
* تجاوز ASIE System Bus.
* تخزين بيانات حساسة دون اعتماد.
* استخدام مدخلات ASIE للتدريب دون موافقة صريحة.
* تعطيل Audit أو Observability.
* فرض Vendor Lock-in مؤثر.

## 18. Provider Adapter

يجب أن يتم التكامل مع AI Provider عبر Adapter أو طبقة تجريد معتمدة عند الحاجة.

ويجب أن يمنع Adapter تسرب تفاصيل المزود إلى المعمارية الأساسية.

---

# القسم الخامس: AI Models

## 19. تعريف AI Model

يُقصد بـ AI Model النموذج المستخدم لإنتاج أو تحليل أو تصنيف أو تحويل أو تقييم معلومات داخل ASIE.

## 20. شروط استخدام AI Model

يجب أن يكون استخدام AI Model:

* محدد الغرض.
* محدود النطاق.
* قابلًا للتدقيق.
* قابلًا للتعطيل.
* خاضعًا للسياسات.
* متوافقًا مع تصنيف البيانات.
* غير مانح لثقة ضمنية.

## 21. Model Selection

يجب أن يخضع اختيار النموذج لمعايير تشمل:

* طبيعة المهمة.
* حساسية البيانات.
* مستوى المخاطر.
* قابلية التتبع.
* متطلبات الخصوصية.
* متطلبات الأمان.
* تكلفة الفشل.
* قابلية الاستبدال.

## 22. منع الاعتماد الأعمى على النموذج

يُحظر تصميم أي مسار حرج يفترض صحة مخرجات AI Model دون تحقق أو ضوابط تعويضية.

---

# القسم السادس: Prompt Governance

## 23. تعريف Prompt

يُقصد بـ Prompt كل تعليمات أو سياق أو مدخلات تُرسل إلى AI Model لتوجيه السلوك أو إنتاج المخرجات.

## 24. قواعد Prompt

يجب أن تكون Prompts المستخدمة في المسارات الحرجة:

* موثقة.
* مملوكة.
* قابلة للتتبع.
* خاضعة للإصدار.
* محددة الغرض.
* غير كاشفة للأسرار.
* متوافقة مع Contract.
* قابلة للمراجعة.

## 25. Prompt Injection

يُعد Prompt Injection خطرًا أمنيًا ومعماريًا.

ويجب تصميم الضوابط لمنع المدخلات غير الموثوقة من تعديل تعليمات النظام أو تجاوز السياسات.

## 26. منع التعليمات المخالفة

لا يجوز لأي Prompt أن يطلب من AI:

* تجاوز Security Context.
* تجاهل AAS.
* كشف Secrets.
* إنشاء قناة جانبية.
* تعديل Contract.
* اتخاذ قرار نهائي غير مصرح به.
* إخفاء أثره عن Audit.
* تمرير مخرجاته كحقيقة دون تحقق.

---

# القسم السابع: Context Governance

## 27. تعريف AI Context

يُقصد بـ AI Context البيانات أو الوثائق أو الرسائل أو الحالة التي تُقدَّم إلى AI Model لأداء مهمة.

## 28. قواعد إدخال السياق

يجب أن يخضع AI Context إلى:

* Data Classification.
* Purpose Limitation.
* Least Privilege.
* Need-to-Know.
* Redaction عند الحاجة.
* Retention Control.
* Audit Logging.

## 29. منع تسريب السياق

يُحظر إدخال بيانات إلى AI Context إذا كانت:

* غير لازمة للمهمة.
* أعلى حساسية من صلاحية النموذج أو المزود.
* تحتوي Secrets غير محمية.
* تحتوي بيانات لا يجوز مشاركتها خارجيًا.
* تخالف Retention أو Privacy أو Security Policy.

## 30. Retrieval-Augmented Generation

يجوز استخدام RAG إذا كان:

* مصدر البيانات معتمدًا.
* الوصول مضبوطًا.
* النتائج قابلة للتتبع.
* السياق محدودًا.
* البيانات مصنفة.
* المخرجات تخضع للتحقق.
* لا يتجاوز قاعدة Data Ownership.

---

# القسم الثامن: AI Tool Calling

## 31. تعريف Tool Calling

يُقصد بـ Tool Calling قدرة AI على استدعاء أدوات أو Services أو APIs أو Actions داخل ASIE أو خارجها.

## 32. قاعدة Tool Calling

لا يجوز لـ AI تنفيذ Tool Call إلا عبر صلاحية معتمدة وسياق أمني محدد.

## 33. شروط Tool Calling

يجب أن يكون كل Tool Call:

* مصرحًا به.
* محدود النطاق.
* قابلًا للتدقيق.
* قابلًا للإبطال.
* مرتبطًا بهوية.
* مرتبطًا بالغرض.
* خاضعًا لـ Contract عند الحاجة.
* قابلًا للإيقاف.

## 34. منع التنفيذ الحر

يُحظر منح AI Agent قدرة تنفيذ مفتوحة أو وصولًا عامًا إلى الأدوات أو قواعد البيانات أو APIs.

## 35. الأعمال الحرجة

لا يجوز لـ AI تنفيذ إجراء حرج دون Human Review Gate أو Governance Gate معتمد، متى كان الإجراء يؤثر في:

* Security.
* Finance.
* Legal.
* Production.
* Data Deletion.
* Privileged Access.
* User Rights.
* Contract State.
* System Configuration.

---

# القسم التاسع: AI Output Validation

## 36. تعريف AI Output

يُقصد بـ AI Output كل نتيجة صادرة عن AI Model، سواء كانت نصًا أو تصنيفًا أو قرارًا مقترحًا أو كودًا أو خطة أو استدعاء أداة أو تحليلًا.

## 37. قواعد التحقق

يجب التحقق من AI Output وفق مستوى المخاطر.

ويشمل التحقق:

* Schema Validation.
* Contract Validation.
* Policy Validation.
* Security Review.
* Factual Verification.
* Human Review عند الحاجة.
* Consistency Check.
* Safety Check.

## 38. منع الإخراج غير المتحقق

يُحظر استخدام AI Output مباشرة في مسار حرج إذا لم يخضع لضوابط التحقق المناسبة.

## 39. المخرجات الهيكلية

يجب أن تخضع المخرجات الهيكلية من AI إلى Schema أو Contract واضح قبل استخدامها في النظام.

## 40. المخرجات النصية

لا يجوز اعتبار المخرجات النصية من AI حكمًا نهائيًا أو تفسيرًا رسميًا أو قرارًا ملزمًا إلا إذا اعتمدتها جهة مخولة.

---

# القسم العاشر: Human-in-the-Loop

## 41. قاعدة المراجعة البشرية

يجب إدخال Human-in-the-Loop في المسارات التي يكون فيها خطأ AI مؤثرًا على الأمن أو الحقوق أو المال أو الإنتاج أو الامتثال أو السمعة.

## 42. مسؤولية الإنسان

لا تُعد مراجعة الإنسان إجراءً شكليًا.

ويجب أن تكون المراجعة قادرة فعليًا على:

* قبول المخرج.
* رفض المخرج.
* تعديله.
* طلب إعادة التوليد.
* إيقاف التنفيذ.
* تصعيد القرار.

## 43. منع الموافقة الآلية المقنعة

يُحظر تصميم واجهة أو مسار يجعل الموافقة البشرية تلقائية أو شكلية أو غير واعية بالمخاطر.

---

# القسم الحادي عشر: AI Security

## 44. متطلبات AI Security

يجب أن يخضع AI Integration لضوابط أمنية تشمل:

* Prompt Injection Protection.
* Data Exfiltration Prevention.
* Output Filtering.
* Tool Permission Control.
* Model Access Control.
* Provider Boundary Control.
* Audit Logging.
* Abuse Detection.

## 45. Data Exfiltration

يُعد إخراج البيانات عبر AI خطرًا أمنيًا.

ويجب منع AI من استخدام المخرجات أو Tool Calls أو External Providers لتسريب بيانات غير مصرح بها.

## 46. Jailbreak and Policy Bypass

يجب التعامل مع Jailbreak ومحاولات تجاوز السياسات كأحداث أمنية، لا كمدخلات عادية.

## 47. Secrets

يُحظر إرسال Secrets إلى AI Model إلا إذا كان ذلك معتمدًا صراحة، ومشفرًا أو مضبوطًا، ولازمًا للوظيفة، وخاضعًا للتدقيق.

---

# القسم الثاني عشر: AI Data Handling

## 48. استخدام البيانات

يجب أن يكون استخدام البيانات في AI:

* محدد الغرض.
* متناسبًا مع المهمة.
* محدود النطاق.
* خاضعًا للتصنيف.
* قابلًا للتتبع.
* متوافقًا مع Retention.
* غير ناقل للملكية إلى AI Provider.

## 49. تدريب النماذج

لا يجوز استخدام بيانات ASIE لتدريب أو تحسين AI Model إلا بقرار معتمد يحدد:

* نوع البيانات.
* الغرض.
* التصنيف.
* الحدود.
* الحماية.
* الاحتفاظ.
* حق الإزالة.
* أثر المزود.
* الأثر الأمني.

## 50. ذاكرة AI

يُحظر إنشاء AI Memory غير محكومة.

وأي ذاكرة مرتبطة بـ AI يجب أن تكون:

* مملوكة.
* مصنفة.
* محدودة الغرض.
* قابلة للحذف.
* قابلة للتدقيق.
* غير كاشفة للأسرار.
* متوافقة مع AAS-32.

---

# القسم الثالث عشر: AI Observability

## 51. مراقبة AI

يجب أن يدعم AI Integration مراقبة:

* Model Requests.
* Prompt Versions.
* Context Sources.
* Tool Calls.
* Output Types.
* Validation Results.
* Human Review Decisions.
* Provider Errors.
* Safety Events.
* Policy Violations.

## 52. شروط المراقبة

يجب أن تكون AI Observability:

* آمنة.
* محدودة الوصول.
* غير كاشفة للأسرار.
* مرتبطة بـ Correlation ID عند الحاجة.
* قابلة للتدقيق.
* متوافقة مع Retention.
* قادرة على دعم التحقيق.

## 53. منع المراقبة الضارة

يُحظر أن تحتوي سجلات AI على:

* Secrets.
* Credentials.
* سياق حساس كامل دون حاجة.
* بيانات Restricted غير مموهة.
* مخرجات تكشف معلومات غير مصرح بها.
* تفاصيل تمكّن من تجاوز الضوابط.

---

# القسم الرابع عشر: AI Failure

## 54. تعريف AI Failure

يُعد AI Failure كل حالة ينتج عنها إخراج غير آمن أو غير صحيح أو غير قابل للتحقق أو مخالف لـ Contract أو مؤثر في التزام ASIE.

## 55. أنواع AI Failure

تشمل أنواع الفشل:

* Hallucination.
* Unsafe Output.
* Prompt Injection Success.
* Data Leakage.
* Tool Misuse.
* Model Unavailability.
* Provider Failure.
* Validation Failure.
* Policy Bypass.
* Context Contamination.
* Incorrect Classification.
* Unauthorized Action.

## 56. التعامل مع AI Failure

عند حدوث AI Failure، يجب:

* إيقاف المسار المتأثر عند الحاجة.
* منع استخدام المخرج.
* تسجيل الحدث.
* عزل السياق أو الأداة المتأثرة.
* إبلاغ المكونات المختصة.
* مراجعة الأثر الأمني.
* تفعيل Provider Fallback عند الحاجة.
* منع تكرار الفشل.

---

# القسم الخامس عشر: Provider Fallback and Degraded Mode

## 57. Provider Fallback

يجوز استخدام AI Provider Fallback إذا كان:

* معتمدًا.
* متوافقًا مع نفس التصنيف الأمني.
* لا يوسع نطاق مشاركة البيانات.
* لا يكسر Contract.
* لا يغير دلالة المخرجات.
* لا يحول المزود البديل إلى Truth Owner.

## 58. Degraded AI Mode

يجوز تعطيل أو تقليل قدرات AI عند فشل المزود أو ارتفاع المخاطر.

ويجب أن يكون Degraded AI Mode:

* آمنًا.
* واضح الأثر.
* قابلًا للتتبع.
* غير كاسر للتشغيل الأساسي.
* غير متجاوز لـ Zero Trust.

## 59. منع الاعتماد الحرج غير المحمي

لا يجوز أن يعتمد مسار حرج على AI Provider واحد دون ضوابط فشل أو تعطيل أو بديل أو مسار مراجعة مناسب.

---

# القسم السادس عشر: AI Agents

## 60. تعريف AI Agent

يُقصد بـ AI Agent أي كيان AI قادر على التخطيط أو استخدام الأدوات أو اتخاذ خطوات متتابعة لتحقيق هدف.

## 61. حدود AI Agent

يجب أن يكون AI Agent:

* محدود الهدف.
* محدود الأدوات.
* محدود الصلاحيات.
* قابلًا للإيقاف.
* قابلًا للتدقيق.
* خاضعًا للتتبع.
* غير قادر على توسيع صلاحياته ذاتيًا.

## 62. منع الاستقلال غير المحكوم

يُحظر تشغيل AI Agent بصلاحيات مفتوحة أو هدف عام أو قدرة ذاتية على تعديل سياساته أو أدواته أو نطاقه.

## 63. Agent Memory

يجب أن تخضع Agent Memory لقواعد AI Memory وAAS-32، ولا يجوز أن تتحول إلى قاعدة معرفة غير محكومة أو مصدر حقيقة بديل.

---

# القسم السابع عشر: المحظورات

## 64. محظورات AI Integration

يُحظر في AI Integration ما يلي:

* AI يتخذ قرارًا نهائيًا في مسار حرج دون اعتماد.
* AI Output يُعامل كحقيقة نهائية دون تحقق.
* Prompt يطلب تجاوز AAS.
* AI Tool Calling بصلاحيات مفتوحة.
* AI Agent يوسع صلاحياته ذاتيًا.
* إرسال Secrets إلى AI دون اعتماد.
* استخدام بيانات ASIE للتدريب دون قرار معتمد.
* AI Provider يملك بيانات ASIE.
* AI يتجاوز ASIE System Bus.
* AI يكتب مباشرة في قاعدة بيانات Module دون Contract.
* AI يعدل Schema أو Configuration دون Governance.
* AI Memory غير محكومة.
* RAG من مصادر غير مصرح بها.
* Prompt Injection غير معالج في مسار حرج.
* Provider Lock-in يفرض تغييرًا معماريًا.
* AI يستخدم كواجهة لإخفاء قرار بشري غير موثق.

---

# القسم الثامن عشر: معايير التحقق من الالتزام

## 65. معايير قبول AI Integration

يُقبل AI Integration إذا تحققت الشروط التالية:

* يحافظ على Frozen Architecture.
* لا يتجاوز ASIE Kernel.
* يستخدم ASIE System Bus عند تبادل الرسائل.
* يلتزم بـ Socket Contract Layer.
* يخضع لـ Zero Trust.
* يحدد الغرض والنطاق.
* يضبط Prompt وContext.
* يتحقق من AI Output.
* يضبط Tool Calling.
* يدعم Human Review عند الحاجة.
* يمنع Data Leakage.
* يدعم Audit وObservability.
* يحافظ على Provider Replaceability.
* لا يحول AI أو Provider إلى Truth Owner.

## 66. مؤشرات الانحراف المعماري

تُعد الحالات التالية مؤشرات انحراف:

* استخدام AI Output مباشرة في Production دون تحقق.
* Prompt غير موثق في مسار حرج.
* Context يحتوي بيانات غير لازمة.
* AI Agent بصلاحيات عامة.
* Tool Call غير قابل للتدقيق.
* AI Provider يحتفظ ببيانات حساسة دون اعتماد.
* AI Memory غير مصنفة.
* RAG يستدعي مصادر غير محكومة.
* AI يتجاوز Contract للوصول إلى بيانات.
* Human Review شكلية.
* فشل AI لا يوقف المسار الخطر.
* Vendor Lock-in يجعل استبدال النموذج غير ممكن.

---

# القسم التاسع عشر: العلاقة مع وثائق AAS الأخرى

## 67. العلاقة مع AAS-01

تستمد هذه الوثيقة سلطتها من AAS-01 — ASIE Constitution.

ولا يجوز تفسير AI Integration بما يسمح بتجاوز المبادئ الدستورية أو Frozen Architecture.

## 68. العلاقة مع AAS-02

يجب أن يعمل AI Integration داخل Operating Architecture المعتمدة، ولا يجوز أن ينشئ نموذج تشغيل موازٍ.

## 69. العلاقة مع AAS-10

لا يجوز للذكاء الاصطناعي تعديل ASIE Kernel أو تجاوزه أو تفسير سلطته بدلًا عنه.

## 70. العلاقة مع AAS-11

يجب أن تخضع رسائل AI وتفاعلاته مع المنصة لـ APP عند دخولها في نطاق الرسائل المعتمدة.

## 71. العلاقة مع AAS-15

يجب أن يستخدم AI Integration ASIE System Bus في تبادل الرسائل داخل ASIE، ولا يجوز أن ينشئ قناة بديلة.

## 72. العلاقة مع AAS-16

يجب أن تخضع أدوات AI ومخرجاته وتفاعلاته مع Modules لـ Socket Contract Layer حيثما ينطبق.

## 73. العلاقة مع AAS-18

يجب أن تكون مساهمة AI في Message Flow قابلة للتتبع والتحقق، ولا يجوز أن تكسر تسلسل الرسائل أو دلالتها.

## 74. العلاقة مع AAS-20

يخضع AI Integration بالكامل لـ Zero Trust Security، ولا يجوز منح الثقة لأي نموذج أو مزود أو مخرج بصورة ضمنية.

## 75. العلاقة مع AAS-32

تخضع بيانات AI وContext وMemory وTraining Data وRAG Sources لقواعد AAS-32 — ASIE Database Architecture.

## 76. العلاقة مع AAS-60

لا يجوز أن تكشف APIs مخرجات AI أو تسمح بإجراءات AI إلا وفق العقود والصلاحيات والتحقق المعتمد.

---

# أحكام ختامية

## 77. الأثر الملزم

تُعد AAS-40 — ASIE AI Integration Specification المرجع الرسمي الحاكم لكل تكامل ذكاء اصطناعي داخل منصة ASIE.

ويلتزم كل تصميم أو تنفيذ أو تشغيل أو مراجعة تتعلق بـ AI Models أو AI Providers أو AI Agents أو Prompting أو Context أو Tool Calling أو AI Output أو AI Memory بأحكام هذه الوثيقة.

## 78. حدود التعديل

لا يجوز تعديل AI Integration بما يمس Frozen Architecture أو يحول AI إلى Truth Owner أو يتجاوز ASIE System Bus أو Socket Contract Layer إلا عبر Architecture Change Proposal (ACP) معتمد.

## 79. الصفة النهائية

تُعتمد هذه الوثيقة بوصفها المواصفة الرسمية لـ ASIE AI Integration Specification ضمن ASIE Architecture Standard (AAS).

وبموجبها، لا يُعد أي تكامل ذكاء اصطناعي صالحًا داخل منصة ASIE إلا إذا كان محدود النطاق، قابلًا للتدقيق، خاضعًا لـ Zero Trust، ملتزمًا بـ APP وASIE System Bus وSocket Contract Layer، ولا يمنح AI أو مزوده سلطة الحقيقة النهائية أو سلطة الحكم على المعمارية.

**End of Document**

---

# ملحق رسمي: AI Rules for Market Evidence

يجوز للذكاء الاصطناعي تلخيص **Market Evidence Pack** أو شرح دلالاته، لكنه لا يجوز أن يخترع أرقامًا، أو يعوض بيانات ناقصة بتقدير غير موثق، أو يغير نتائج **Finance Engine**.

## AI Permission Matrix

| AI Action | Allowed? | Condition |
|---|---:|---|
| Summarize evidence pack | Yes | Must cite evidence fields |
| Explain market signal | Yes | Must distinguish evidence from inference |
| Generate financial number | No | Finance Engine only |
| Fill missing supplier price | No | Must request evidence or mark unavailable |
| Choose source authority | No | Source whitelist and contracts decide |
| Rewrite deterministic output | No | Must preserve Finance Engine output |

## قاعدة منع الهلوسة السوقية

أي مخرج AI يحتوي رقمًا سوقيًا أو ماليًا غير مرتبط بـ Evidence Pack أو Finance Engine Output يُعد غير صالح، ويجب رفضه أو وسمه بأنه غير متاح.

