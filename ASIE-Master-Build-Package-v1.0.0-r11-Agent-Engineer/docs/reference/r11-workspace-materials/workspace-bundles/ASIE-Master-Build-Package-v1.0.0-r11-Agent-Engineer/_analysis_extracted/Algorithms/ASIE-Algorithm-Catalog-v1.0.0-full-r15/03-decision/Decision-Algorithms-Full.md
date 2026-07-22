# Decision Algorithms Full

## خوارزميات القرار الكاملة

Owner:

المالك:

`Decision Council Module` / موديول مجلس القرار.

## DEC-ALG-01 Validation Gate

## بوابة التحقق

Purpose:

الهدف:

Prevent weak or incomplete analysis from becoming a final decision.

منع التحليل الضعيف أو الناقص من التحول إلى قرار نهائي.

Checks:

الفحوصات:

1. Project context complete / سياق المشروع مكتمل.
2. Saudi geo context valid / السياق السعودي صحيح.
3. Evidence pack available / حزمة الأدلة موجودة.
4. Finance result available / نتيجة التمويل موجودة.
5. No unresolved blocking outlier / لا يوجد شذوذ مانع.
6. No AI-generated numeric input / لا توجد أرقام مولدة من AI.

Outputs:

المخرجات:

- `PASS` / ناجح.
- `REVISE_REQUIRED` / يحتاج مراجعة.
- `BLOCKED` / ممنوع.

## DEC-ALG-02 Five Sovereign Personas

## الشخصيات السيادية الخمس

Purpose:

الهدف:

Generate five independent structured viewpoints.

إنتاج خمس وجهات نظر مستقلة ومنظمة.

Persona Output Schema:

Schema مخرج الشخصية:

```json
{
  "persona_id": "string",
  "strengths": ["string"],
  "weaknesses": ["string"],
  "risks": ["string"],
  "recommendation": "string",
  "confidence": 0.0,
  "vote": "APPROVE | CONDITIONAL_APPROVE | REVISE | REJECT",
  "evidence_refs": ["string"]
}
```

Rules:

القواعد:

- Same input to all personas / نفس المدخلات لكل الشخصيات.
- No persona modifies another / لا شخصية تعدل الأخرى.
- New numbers are rejected / الأرقام الجديدة ترفض.

## DEC-ALG-03 Decision Consensus Scoring

## حساب إجماع القرار

Vote Scores:

درجات الأصوات:

| Vote | Arabic | Score |
| --- | --- | ---: |
| `APPROVE` | موافقة | 1.00 |
| `CONDITIONAL_APPROVE` | موافقة مشروطة | 0.66 |
| `REVISE` | مراجعة | 0.33 |
| `REJECT` | رفض | 0.00 |

Steps:

الخطوات:

1. Validate votes.
2. Convert votes to scores.
3. Compute average score.
4. Compute disagreement spread.
5. Apply validation gate ceiling.
6. Produce decision and dissent.

Decision Bands:

نطاقات القرار:

| Average | Arabic | Decision |
| --- | --- | --- |
| >= 0.80 | عالي | Approve unless blocked |
| 0.60-0.79 | متوسط عالي | Conditional approve |
| 0.35-0.59 | متوسط منخفض | Revise |
| < 0.35 | منخفض | Reject |

