# ASIE Execution Pack v1.0.0 Full

## حزمة تنفيذ ASIE v1.0.0 النسخة الكاملة

This package converts `AAS / ASIE Architecture Standard / الدستور المعماري` into build instructions for KIMI.

هذه الحزمة تحول `AAS / معيار ASIE المعماري / الدستور المعماري` إلى تعليمات بناء تنفيذية لـ KIMI.

## Authority Order

## ترتيب المرجعية

1. `AAS / ASIE Architecture Standard / الدستور المعماري`.
2. `Agent Governance Pack / حزمة حوكمة الوكلاء`.
3. `Execution Pack / حزمة التنفيذ`.
4. `Algorithm Catalog / كتالوج الخوارزميات`.

If this pack conflicts with AAS, AAS wins.

إذا تعارضت هذه الحزمة مع AAS، فالدستور المعماري هو المرجع الأعلى.

## Non-Negotiable Rules

## قواعد لا تكسر

- No direct module-to-module calls.
- ممنوع الاتصال المباشر بين الموديولات.

- All internal calls go through `ASIE System Bus / ناقل النظام` then `Socket Contract Layer / طبقة عقود السوكيت`.
- كل الاتصالات الداخلية تمر عبر `ASIE System Bus / ناقل النظام` ثم `Socket Contract Layer / طبقة عقود السوكيت`.

- `Market Data Layer / طبقة بيانات السوق` is forbidden as an architecture component.
- `Market Data Layer / طبقة بيانات السوق` ممنوع كمكون معماري.

- `AI / الذكاء الاصطناعي` explains, summarizes, classifies text, and advises. It does not generate deterministic numbers.
- `AI / الذكاء الاصطناعي` يشرح ويلخص ويصنف النص وينصح. لا يولد أرقامًا حتمية.

- ASIE is a smart platform, not a static website with AI only in the UI.
- ASIE منصة ذكية، وليست موقعًا ثابتًا يستخدم AI في الواجهة فقط.

- Dynamic charts are required wherever platform outputs produce analyzable data.
- الشارتات الديناميكية مطلوبة في كل موضع تنتج فيه المنصة بيانات قابلة للتحليل.

- The Project Intelligence Dashboard is a composite view of existing Module outputs, not a new Module or truth owner.
- لوحة ذكاء المشروع عرض مركب لمخرجات الموديولات الحالية، وليست موديولًا أو مصدر حقيقة جديدًا.

- Every visible number must resolve to its owner, contract, algorithm, formula, evidence or assumption, unit, period, run, and timestamp.
- كل رقم ظاهر يجب أن يرتبط بمالكه وعقده وخوارزميته ومعادلته ودليله أو افتراضه ووحدته وفترته وتشغيله وتوقيته.

- No government-approved label is allowed without an exact official form, version, scope, source, and documented review.
- يمنع وسم الاعتماد الحكومي دون نموذج رسمي محدد وإصدار ونطاق ومصدر ومراجعة موثقة.

- Professional feasibility is a depth-scaled, cross-reconciled decision process; it is not a questionnaire, a chart collection, or one universal government form.
- دراسة الجدوى الاحترافية عملية قرار متدرجة العمق ومترابطة، وليست استبيانًا أو مجموعة رسومات أو نموذجًا حكوميًا عامًا واحدًا.

- MOF and Etimad references govern applicable government-procurement workflows; exact competition documents override general forms.
- مراجع وزارة المالية واعتماد تضبط مسارات المشتريات الحكومية المنطبقة، وتعلو مستندات المنافسة المحددة على النماذج العامة.

- Aljdwa is a commercial methodology reference only. Automated access, copying, AI summarization, RAG, embedding, or monitoring is blocked without explicit written permission.
- منصة الجدوى مرجع منهجي تجاري فقط، ويمنع جلبها آليًا أو نسخها أو تلخيصها بالذكاء أو إدخالها في RAG أو المتجهات أو مراقبتها دون إذن كتابي صريح.

- Google Analytics and Zoho Analytics are product analytics adapters only, not finance or market authority.
- Google Analytics وZoho Analytics موصلات تحليلات منتج فقط، وليست سلطة مالية أو سوقية.

- The user must not be required to search for or upload public reports. ASIE fetches public evidence automatically.
- لا يجب إلزام المستخدم بالبحث عن التقارير العامة أو رفعها. ASIE يجلب الأدلة العامة تلقائيًا.

- Every external source requires an adapter, legal access status, freshness policy, and fallback behavior.
- كل مصدر خارجي يحتاج موصلًا، حالة وصول قانونية، سياسة حداثة، وسلوك بديل عند الفشل.

- Source evidence must preserve Arabic/English language context and display in the user's language policy.
- يجب أن يحفظ الدليل سياق اللغة العربية/الإنجليزية ويعرض حسب سياسة لغة المستخدم.

- Signup and suspicious login require human verification when risk policy demands it.
- التسجيل والدخول المشبوه يتطلبان تحقق الإنسان عندما تتطلب سياسة المخاطر ذلك.

- Authenticator App MFA is supported for users and required for admin/maintenance roles.
- MFA عبر تطبيق Authenticator مدعوم للمستخدمين ومطلوب لأدوار الإدارة والصيانة.

- WhatsApp and Telegram alerts require explicit user opt-in and notification preferences.
- تنبيهات واتساب وتليجرام تتطلب موافقة صريحة وتفضيلات تنبيه.

- `Finance Engine / محرك التمويل` owns deterministic finance.
- `Finance Engine / محرك التمويل` هو مالك الحسابات المالية الحتمية.

- v1 country scope is Saudi Arabia only.
- نطاق النسخة الأولى هو السعودية فقط.

## Package Structure

## هيكل الحزمة

| Folder | Arabic | Purpose |
| --- | --- | --- |
| `00-index` | الفهارس | Navigation, definitions, source map. |
| `01-core` | النواة التنفيذية | Responsibilities, ownership, data authority. |
| `02-contracts` | العقود | Socket contracts, message types, schemas. |
| `03-modules` | الموديولات | Detailed module build cards. |
| `04-flows` | التدفقات | Directed flows, event flows, failure flows. |
| `05-tests` | الاختبارات | Acceptance, negative, security, regression tests. |
| `06-kimi` | تعليمات KIMI | Build sequence and stop rules. |
| `07-appendices` | الملاحق | Glossary, forbidden patterns, open decisions. |

Dashboard implementation must read `03-modules/Project-Intelligence-Dashboard-and-Visual-Outputs.md` and `06-kimi/KIMI-Project-Dashboard-Build-Prompt.md` before coding.

Professional feasibility implementation must also read `03-modules/Professional-Feasibility-Study-and-Procurement-Reference-Framework.md` and the Algorithm Catalog file `02-finance/Advanced-Feasibility-and-Investment-Appraisal-Algorithms.md` before coding.
