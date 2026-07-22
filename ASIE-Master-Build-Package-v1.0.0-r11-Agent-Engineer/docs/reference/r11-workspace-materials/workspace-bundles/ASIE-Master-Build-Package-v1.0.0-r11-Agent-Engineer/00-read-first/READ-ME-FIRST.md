# READ ME FIRST

## اقرأ هذا أولًا

This is the ASIE Master Build Package, r11 Architect-Resolution-Closed Feasibility Decision Integration.

هذه هي حزمة البناء الرئيسية لأي Agent أو مهندس برمجيات في مشروع ASIE.

Builder Agent or Engineer must read all included packages before writing code.

يجب على الـAgent أو مهندس البرمجيات قراءة كل الحزم المرفقة قبل كتابة أي كود.

## Included Packages

## الحزم المرفقة

1. `ASIE-AAS-v1.0.0-Complete-Package-v3-Market-Intelligence.zip`
   `AAS / الدستور المعماري`

2. `ASIE-Agent-Governance-Pack-v3-Market-Intelligence.zip`
   `Agent Governance / حوكمة الوكلاء`

3. `ASIE-Execution-Pack-v1.0.0-full-r15.zip`
   `Execution Pack / حزمة التنفيذ`

4. `ASIE-Algorithm-Catalog-v1.0.0-full-r15.zip`
   `Algorithm Catalog / كتالوج الخوارزميات`

5. `ASIE-Saudi-Feasibility-Decision-Pack-v1.0.0.zip`
   `Saudi Feasibility Decision Pack / حزمة قرار الجدوى السعودية`

6. `05-audits/ASIE-Project-Dashboard-Visual-Specification-Audit-2026-07-13.md`
   `Dashboard Review / مراجعة لوحة المشروع`

7. `05-audits/ASIE-Professional-Feasibility-and-Procurement-Reference-Audit-2026-07-13.md`
   `Feasibility and Procurement Review / مراجعة الجدوى والمشتريات`

8. `06-integration/ASIE-r10-Correction-Closure-and-Traceability.md`
   `Correction Closure / إغلاق التصحيحات ومصفوفة التتبع`

9. `07-architect-decisions/ASIE-r11-Architect-Resolution-Closure.md`
   `Architect Resolution Closure / إغلاق القرارات المعمارية`

10. `07-architect-decisions/originals/`
    `Original Architect Inputs / مراجع أصلية للحفظ والتتبع فقط`

## Binding Rule

## قاعدة الإلزام

If packages conflict, this order wins:

إذا تعارضت الحزم، فهذا ترتيب المرجعية:

1. AAS / الدستور المعماري.
2. Agent Governance / حوكمة الوكلاء.
3. Execution Pack / حزمة التنفيذ.
4. Algorithm Catalog / كتالوج الخوارزميات.
5. `06-integration/ASIE-r10-Correction-Closure-and-Traceability.md` for the six closed feasibility-decision corrections.
6. `06-integration/ASIE-Feasibility-Decision-Integration-Addendum-v1.0.0.md` for feasibility decision conflicts not restated by r10.
7. `07-architect-decisions/ASIE-r11-Architect-Resolution-Closure.md` for the reviewed architect resolutions received after r10.
8. Original files under `07-architect-decisions/originals/` are context only and are not directly binding.

Read the r10 correction-closure document, the integration addendum, and the r11 architect-resolution closure before implementation. They map logical capability labels to existing approved ASIE modules, preserve AAS boundaries, and define mandatory rejection tests.

## r11 Gate

## بوابة r11

This is one self-contained delivery file. Do not replace any embedded `r15` package with older `r13` or earlier copies. The package must be rejected if any r10 or r11 mandatory correction is missing, bypassed, or not proven by its mapped acceptance test.

هذه حزمة تسليم واحدة مكتفية ذاتيًا. يمنع استبدال أي حزمة `r15` مضمنة بنسخة `r13` أو أقدم. يجب رفض الحزمة إذا غاب أي تصحيح إلزامي في r10 أو r11 أو تم تجاوزه أو لم تثبته حالة اختبار القبول المرتبطة به.

## First Task

## المهمة الأولى

Do not write code first.

لا تكتب كود أولًا.

First, produce the expected first response from:

أولًا، أخرج الرد الأول المتوقع من:

`04-stop-rules/Agent-Engineer-Expected-First-Response.md`

## Government Data Warning

## تحذير البيانات الحكومية

Builder Agent or Engineer must not describe a public government page as open data, approve an entire government domain, or implement a generic crawler for all ministries and authorities.

يجب التمييز بين البيانات المفتوحة المرخصة، والوثيقة العامة، والـAPI المرخص، ومشاركة البيانات الحكومية غير المفتوحة، والبيانات الشخصية أو المصنفة. عند الغموض يتوقف التنفيذ.

## Strict Open Data Only Decision

## قرار البيانات المفتوحة فقط

The active profile is `strict_open_data_only_v1`. Builder Agent or Engineer must not implement registered, licensed, paid, login-based, agreement-based, externally approved, government-sharing, marketplace-crawling, or personal-data source routes.

GASTAT statistical database is an eligible candidate only through exact official open datasets or documented open API endpoints with attribution and transformation disclosure.

`https://mostaql.com/projects` is reference-only. Builder Agent or Engineer may implement an outbound link and private user-authored bookmark/note, but no backend request, preview, crawl, storage of target content, AI summary, embedding, scoring, monitoring, or alerts.

## Official Strategy Reference Decision

## قرار المراجع الاستراتيجية الرسمية

The SDAIA terms, NCA National Cybersecurity Strategy, GOV.SA e-participation, DGA sustainable-development and digital-transformation pages, and SDAIA National Strategy for Data and AI are `reference_only`.

They may inspire approved ASIE-authored alignment cards after human accuracy and originality review. Builder Agent or Engineer must not fetch, copy, mirror, summarize, embed, reconstruct, or store source-page content, and must not imply government approval or use a strategy overview as a formal compliance control.

## Project Intelligence Dashboard Decision

## قرار لوحة ذكاء المشروع

Legacy screenshots are functional and visual references only. Builder Agent or Engineer must implement the fourteen r15 project routes using the universal output envelope and `DASH-ALG-01` through `DASH-ALG-12`.

The dashboard is not a new ASIE Module or truth owner. Every visible number requires owner, contract, algorithm, formula, evidence/assumption, unit, period, run, and timestamp. SWOT, PESTEL, Porter, BMC, and VPC are analytical frameworks, not government forms. A government-approved label requires exact official form evidence and documented review.

## Professional Feasibility and Procurement Decision

## قرار دراسة الجدوى والمنافسات

Professional feasibility is a depth-scaled, cross-reconciled decision process. It is not one universal government template. Builder Agent or Engineer must implement `FST-ALG-01` through `FST-ALG-03`, `FIN-ALG-06` through `FIN-ALG-12`, `PROC-ALG-01` through `PROC-ALG-02`, and `METH-ALG-01` through `METH-ALG-02` in their existing owners.

MOF and Etimad materials are official references for applicable Saudi procurement workflows. The exact live competition package overrides general forms. Aljdwa is a commercial reference only: no automated browsing, copying, AI summary, RAG, embedding, indexing, or monitoring without explicit written permission.
