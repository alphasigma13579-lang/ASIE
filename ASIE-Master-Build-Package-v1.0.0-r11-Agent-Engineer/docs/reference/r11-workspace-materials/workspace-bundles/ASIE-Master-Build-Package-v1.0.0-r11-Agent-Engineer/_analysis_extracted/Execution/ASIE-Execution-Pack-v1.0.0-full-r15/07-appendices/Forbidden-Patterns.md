# Forbidden Patterns

## الأنماط الممنوعة

| Pattern | Arabic | Reason |
| --- | --- | --- |
| `Market Data Layer` | طبقة بيانات السوق | Not an ASIE component / ليس مكونًا |
| Direct module call | اتصال مباشر بين موديولات | Breaks System Bus / يكسر ناقل النظام |
| AI-generated finance number | رقم مالي مولد من AI | Breaks deterministic finance / يكسر التمويل الحتمي |
| Database as source of truth | قاعدة البيانات كمرجع معماري | Breaks AAS authority / يكسر مرجعية AAS |
| Provider exposed to UI | مزود مكشوف للواجهة | Breaks contracts / يكسر العقود |
| Plugin bypassing socket | Plugin يتجاوز السوكيت | Breaks APP and SCL / يكسر APP و SCL |
| Cross-country v1 analysis | تحليل خارج السعودية | خارج نطاق v1 |
| Dashboard Module or Dashboard Layer | موديول أو طبقة للوحة | Dashboard is a composite view of existing owner outputs |
| Bare dashboard number | رقم لوحة مجرد | Missing owner, formula, lineage, unit, period, run, or timestamp |
| Frontend financial calculation | حساب مالي في الواجهة | Finance Engine owns deterministic finance |
| Confidence as success probability | الثقة كاحتمال نجاح | Conflates evidence quality with outcome probability |
| Legacy screenshot value migration | نقل قيمة من الشاشة القديمة | Legacy images are reference-only |
| Government-approved badge without exact proof | اعتماد حكومي بلا إثبات محدد | Unsupported official claim |
| Analytical framework labeled official form | تسمية إطار تحليلي نموذجًا رسميًا | SWOT/BMC/VPC are not government forms |
| Dashboard/report mismatch | اختلاف اللوحة والتقرير | Same run must use same output IDs |

## Professional Feasibility and Procurement Forbidden Patterns r15

- A universal `government-approved feasibility template` claim without an exact official document, scope, version, and review.
- Treating MOF/Etimad procurement forms as the methodology or approval of every feasibility study.
- Using a generic form when exact competition documents, addenda, answers, evaluation criteria, or contract terms exist.
- A `Feasibility Module`, `Procurement Module`, `Methodology Layer`, or direct Module-to-Module flow.
- AI-generated market size, demand, price, cost, tax, discount rate, cash flow, distribution, correlation, score, weight, or final decision.
- Unbalanced integrated statements, hidden plug figures, silent missing-to-zero conversion, or mixed real/nominal and pre/post-tax bases.
- Reporting IRR without root diagnostics and conventions, or presenting MCMC output as universal success probability.
- Mixing private financial returns with economic/social cost-benefit results.
- Hiding required chapters or contradictions behind a polished dashboard or report.
- Crawling, scraping, monitoring, copying, embedding, vectorizing, indexing, structurally reconstructing, or asking AI to summarize Aljdwa without exact written permission.
- Claiming Saudi government, MOF, Etimad, UNIDO, World Bank, IFC, Green Book, or Aljdwa endorsement.
