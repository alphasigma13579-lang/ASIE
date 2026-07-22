# AI Routing Algorithms Full

## خوارزميات توجيه الذكاء الاصطناعي الكاملة

Owner:

المالك:

`AI Advisory Module` / موديول الاستشارة بالذكاء الاصطناعي.

## AI-ALG-01 Model Routing

## توجيه النماذج

Purpose:

الهدف:

Select model by task, plan, cost, risk, and latency.

اختيار النموذج حسب المهمة، الخطة، التكلفة، الخطورة، والسرعة.

Routing Table:

جدول التوجيه:

| Task | Arabic | Model |
| --- | --- | --- |
| Fast classification | تصنيف سريع | Llama 3.1 70B via Groq |
| Free/basic explanation | شرح مجاني أو أساسي | Llama 3.1 70B via Groq |
| Premium deep advisory | استشارة عميقة مدفوعة | Kimi K2.5 |
| Backup | احتياطي | DeepSeek V3 |
| Internet search | بحث إنترنت | Tavily |

Steps:

الخطوات:

1. Classify task.
2. Check subscription entitlement.
3. Check if deterministic authority is requested.
4. If yes, reject and route to owner module.
5. Select model.
6. Log provider, reason, and cost tier.

## AI-ALG-02 RAG Retrieval Ranking

## ترتيب الاسترجاع من RAG

Purpose:

الهدف:

Retrieve approved knowledge with evidence references.

استرجاع معرفة معتمدة مع مراجع أدلة.

Ranking Factors:

عوامل الترتيب:

- Semantic match / التطابق الدلالي.
- Source confidence / ثقة المصدر.
- Freshness / الحداثة.
- Saudi relevance / الصلة بالسعودية.
- Document authority / سلطة الوثيقة.

Failure:

الفشل:

If evidence is insufficient, return `insufficient_evidence`.

إذا كانت الأدلة غير كافية، يرجع `insufficient_evidence`.

## AI-ALG-03 Advisory Output Guard

## حارس مخرجات الاستشارة

Checks:

الفحوصات:

1. No unsupported numbers / لا أرقام غير مدعومة.
2. No cross-country analysis / لا تحليل خارج السعودية.
3. No architecture changes / لا تغيير معماري.
4. No provider authority / لا سلطة للمزود.
5. Evidence references required / مراجع الأدلة مطلوبة.

Output:

المخرج:

- `ACCEPTED` / مقبول.
- `REJECTED_UNSUPPORTED_NUMBER` / مرفوض بسبب رقم غير مدعوم.
- `REJECTED_SCOPE` / مرفوض بسبب النطاق.
- `REJECTED_ARCHITECTURE` / مرفوض بسبب المعمارية.

