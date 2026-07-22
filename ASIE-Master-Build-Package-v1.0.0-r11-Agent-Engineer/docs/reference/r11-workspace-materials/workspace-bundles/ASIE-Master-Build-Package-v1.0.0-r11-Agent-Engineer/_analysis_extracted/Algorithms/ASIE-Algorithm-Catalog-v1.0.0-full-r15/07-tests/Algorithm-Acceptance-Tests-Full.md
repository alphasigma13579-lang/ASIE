# Algorithm Acceptance Tests Full

## اختبارات قبول الخوارزميات الكاملة

## Market Tests

## اختبارات السوق

| ID | Algorithm | Arabic | Test | Expected |
| --- | --- | --- | --- | --- |
| `MI-ALG-01-T01` | Source Confidence | ثقة المصدر | Source has no issuer | Reject |
| `MI-ALG-01-T02` | Source Confidence | ثقة المصدر | Saudi official source | Score 1.00 before freshness |
| `MI-ALG-02-T01` | Evidence Pack | حزمة الأدلة | Missing required category | Mark missing |
| `MI-ALG-03-T01` | Price Outlier | شذوذ الأسعار | Fewer than 5 samples | insufficient_samples |
| `MI-ALG-03-T02` | Price Outlier | شذوذ الأسعار | Extreme high price | Outlier report |
| `MI-ALG-04-T01` | Geo Context | السياق الجغرافي | Outside Saudi Arabia | Reject |
| `MI-ALG-04-T02` | Geo Context | السياق الجغرافي | Manual city only | Reject |
| `SECTOR-ALG-01-T01` | Sector Mapping | ربط القطاع | Missing primary sector | Reject |
| `SECTOR-ALG-01-T02` | Sector Mapping | ربط القطاع | Arabic UI with English-only label | Reject |
| `SECTOR-ALG-02-T01` | Source Mapping | ربط المصادر | Sector has no source plan | Reject |
| `SECTOR-ALG-04-T01` | Evaluation Criteria | معايير التقييم | Same criteria for all sectors | Reject |
| `SECTOR-ALG-05-T01` | Opportunity Signal | إشارة فرصة | Signal without evidence link | Reject |
| `EXT-ALG-01-T01` | Public Evidence Auto Fetch | الجلب التلقائي | User asked to upload public report | Reject design |
| `EXT-ALG-02-T01` | Deep Research | البحث العميق | KIMI claim without URL | Reject |
| `EXT-ALG-03-T01` | Similar Cases | التجارب المشابهة | Similar case without link | Reject |
| `EXT-ALG-04-T01` | Price Sampling | عينات الأسعار | Price without marketplace URL | Reject |
| `EXT-ALG-04-T02` | Strict Price Source | مصدر السعر الصارم | Marketplace sampling requested under strict profile | Return `SOURCE_PROFILE_UNSUPPORTED` |
| `EXT-ALG-05-T01` | Evidence Link | رابط الإثبات | Claim without evidence id | Reject |
| `EXT-ALG-06-T01` | Pinecone Retrieval | Pinecone | Vector result without original source | Reject |
| `EXT-ALG-07-T01` | Legal Access | الوصول القانوني | Source marked restricted | Stop automatic fetch |
| `EXT-ALG-08-T01` | Source Priority | أولوية المصدر | Official and general web both exist | Official first |
| `EXT-ALG-09-T01` | Freshness | الحداثة | Stale price evidence | Refresh or mark stale |
| `EXT-ALG-10-T01` | Failure Fallback | بدائل الفشل | Crawler blocked | Stop, do not bypass |
| `EXT-ALG-11-T01` | Source Language | لغة المصدر | Arabic source with English-only display | Reject unless requested |
| `EXT-ALG-11-T02` | Source Language | لغة المصدر | Missing source_language metadata | Reject |
| `OPEN-DATA-ALG-01-T01` | Source Registration | تسجيل المصدر | Discovery attempts to enable source | Reject |
| `OPEN-DATA-ALG-01-T02` | Source Registration | تسجيل المصدر | One approval covers entire ministry domain | Reject |
| `OPEN-DATA-ALG-02-T01` | Route Classification | تصنيف المسار | Public page has no open-data license | Public-document or unknown; not open data |
| `OPEN-DATA-ALG-02-T02` | Route Classification | تصنيف المسار | Conflicting classification evidence | Most restrictive + review |
| `OPEN-DATA-ALG-03-T01` | Legal Access | الوصول النظامي | Terms or license hash missing | Deny |
| `OPEN-DATA-ALG-03-T02` | Legal Access | الوصول النظامي | AI recommends approval | Ignore AI decision; require human approver |
| `OPEN-DATA-ALG-03-T03` | Legal Access | الوصول النظامي | Approval expired | Deny |
| `OPEN-DATA-ALG-04-T01` | Data Sharing Gate | بوابة المشاركة | Non-public government data requested | Data-sharing route only |
| `OPEN-DATA-ALG-04-T02` | Data Sharing Gate | بوابة المشاركة | Data-sharing request denied then crawler used | Reject and incident |
| `OPEN-DATA-ALG-05-T01` | PDPL Gate | بوابة PDPL | Direct identifier detected | Block until privacy decision |
| `OPEN-DATA-ALG-05-T02` | PDPL Gate | بوابة PDPL | Re-identification possible after join | Reclassify and block |
| `OPEN-DATA-ALG-05-T03` | Transfer Gate | بوابة النقل | Foreign AI receives personal data without approved safeguard | Deny |
| `OPEN-DATA-ALG-06-T01` | Runtime Guard | حارس التشغيل | Redirect leaves approved scope | Block |
| `OPEN-DATA-ALG-06-T02` | Runtime Guard | حارس التشغيل | DNS resolves to private/metadata IP | Block SSRF |
| `OPEN-DATA-ALG-06-T03` | Runtime Guard | حارس التشغيل | CAPTCHA/WAF/login bypass attempted | Reject and incident |
| `OPEN-DATA-ALG-06-T04` | Runtime Guard | حارس التشغيل | Repeated 429 triggers proxy rotation | Reject; stop connector |
| `OPEN-DATA-ALG-07-T01` | Evidence Ledger | سجل الدليل | Missing license/classification/decision ID | Exclude evidence |
| `OPEN-DATA-ALG-07-T02` | Content Integrity | سلامة المحتوى | Prompt injection in retrieved page | Untrusted data; no instruction execution |
| `OPEN-DATA-ALG-07-T03` | Content Integrity | سلامة المحتوى | Malicious or decompression-bomb file | Quarantine |
| `OPEN-DATA-ALG-08-T01` | Revalidation | إعادة التحقق | Terms hash changed | Suspend and re-review |
| `OPEN-DATA-ALG-08-T02` | Revalidation | إعادة التحقق | Data stale but license current | Mark stale; do not confuse with legal status |
| `OPEN-DATA-ALG-09-T01` | NCA Applicability | انطباق NCA | Entity class unknown | Release blocker |
| `OPEN-DATA-ALG-09-T02` | NCA Applicability | انطباق NCA | Cloud used but cloud profile omitted | Reject profile |
| `OPEN-DATA-ALG-10-T01` | Kill Switch | مفتاح الإيقاف | Source suspended during active jobs | Stop and quarantine all jobs |
| `OPEN-DATA-ALG-10-T02` | Re-enable | إعادة التفعيل | Admin tries to re-enable without audited compliance decision | Reject and audit |
| `OPEN-DATA-ALG-11-T01` | Strict Eligibility | الأهلية الصارمة | Exact GASTAT open dataset, public terms, no authentication, no personal data | Eligible candidate |
| `OPEN-DATA-ALG-11-T02` | Strict Eligibility | الأهلية الصارمة | API requires free registration or approved key | Block |
| `OPEN-DATA-ALG-11-T03` | Strict Eligibility | الأهلية الصارمة | Public government page has no explicit open-reuse evidence | Reference only or block |
| `OPEN-DATA-ALG-11-T04` | Strict Eligibility | الأهلية الصارمة | Third-party scraping API offers blocked marketplace data | Block |
| `OPEN-DATA-ALG-11-T05` | Strict Eligibility | الأهلية الصارمة | Dataset contains personal or microdata fields | Block |
| `OPEN-DATA-ALG-12-T01` | Reference Guard | حارس المرجع | Save `https://mostaql.com/projects` URL and user-authored note | Save without network request |
| `OPEN-DATA-ALG-12-T02` | Reference Guard | حارس المرجع | Backend requests Mostaql title or preview metadata | Block and audit |
| `OPEN-DATA-ALG-12-T03` | Reference Guard | حارس المرجع | Mostaql URL sent to AI or vector indexing | Block and audit |
| `OPEN-DATA-ALG-12-T04` | Reference Guard | حارس المرجع | Scheduler tries to monitor Mostaql projects | Block |
| `OPEN-DATA-ALG-12-T05` | Reference Guard | حارس المرجع | Reclassify Mostaql using a commercial scraper API | Reject |
| `REF-ALG-01-T01` | Canonicalization | توحيد الرابط | NSDAI URL repeated with `#?` | One canonical record |
| `REF-ALG-01-T02` | Registration | تسجيل المرجع | Registration payload contains source HTML or screenshot | Reject |
| `REF-ALG-01-T03` | Registration | تسجيل المرجع | Unknown non-official domain submitted as national strategy | Reject |
| `REF-ALG-02-T01` | Originality | الأصالة | Card contains copied paragraph or list | Reject |
| `REF-ALG-02-T02` | Originality | الأصالة | Card uses only exact official title and an original interpretation | Send to human review |
| `REF-ALG-02-T03` | Human Review | المراجعة البشرية | AI marks its own draft approved | Reject |
| `REF-ALG-03-T01` | Alignment Pack | حزمة المواءمة | Approved current cards with project context | Build original pack with citations/disclaimer |
| `REF-ALG-03-T02` | Alignment Pack | حزمة المواءمة | Pack includes source content or copied structure | Reject |
| `REF-ALG-03-T03` | Finance Boundary | حد التمويل | Strategy theme used as numeric Finance input | Reject |
| `REF-ALG-04-T01` | Control Claim | ادعاء الضابط | NCA strategy used as proof of ECC compliance | Reject and request exact control evidence |
| `REF-ALG-04-T02` | Endorsement | الادعاء الرسمي | DGA/SDAIA/NCA endorsement implied | Reject |
| `REF-ALG-04-T03` | Participation | المشاركة | GOV.SA page used to authorize collection of submissions | Reject |
| `REF-ALG-05-T01` | Expiry | انتهاء المرجع | Card passes review due date | Block consumers |
| `REF-ALG-05-T02` | Unavailability | تعذر المرجع | SDAIA page unavailable and mirror is proposed | Reject fallback |
| `REF-ALG-05-T03` | Reactivation | إعادة التفعيل | Admin reactivates withdrawn card without human review | Reject and audit |

## Finance Tests

## اختبارات التمويل

| ID | Algorithm | Arabic | Test | Expected |
| --- | --- | --- | --- | --- |
| `FIN-ALG-01-T01` | Deterministic Finance | التمويل الحتمي | Missing source for number | Blocking error |
| `FIN-ALG-01-T02` | Deterministic Finance | التمويل الحتمي | AI-generated number | Reject |
| `FIN-ALG-02-T01` | CapEx OpEx | تصنيف المصاريف | Equipment item | CapEx |
| `FIN-ALG-02-T02` | CapEx OpEx | تصنيف المصاريف | Monthly salary | OpEx |
| `FIN-ALG-03-T01` | Sensitivity | الحساسية | No baseline | Reject |
| `FIN-ALG-04-T01` | MCMC | مونت كارلو | No fixed seed | Reject |
| `FIN-ALG-05-T01` | Supplier Quote | عروض الموردين | Missing unit | Reject row |
| `FST-ALG-01-T01` | Depth Profile | ملف العمق | Government competition requests SME profile | Force government profile |
| `FST-ALG-01-T02` | Depth Profile | ملف العمق | Downgrade omits mandatory chapter | Reject and audit |
| `FST-ALG-02-T01` | Chapter Gate | بوابة الفصول | Required chapter `stale` | Block completion |
| `FST-ALG-02-T02` | Chapter Gate | بوابة الفصول | `not_applicable` without reviewer/reason | Reject |
| `FST-ALG-03-T01` | Reconciliation | المطابقة | Forecast volume exceeds practical capacity | Blocking contradiction |
| `FST-ALG-03-T02` | Reconciliation | المطابقة | Revenue before commissioning | Blocking contradiction |
| `FIN-ALG-06-T01` | Integrated Statements | القوائم المترابطة | Assets differ from liabilities plus equity | Reject run |
| `FIN-ALG-06-T02` | Integrated Statements | القوائم المترابطة | Cash flow closing cash differs from balance-sheet cash | Reject run |
| `FIN-ALG-06-T03` | Basis Control | ضبط الأساس | Real cash flows with nominal rate | Reject run |
| `FIN-ALG-07-T01` | Investment Appraisal | التقييم الاستثماري | Missing discount rate source/version | Block NPV |
| `FIN-ALG-07-T02` | IRR Diagnostics | تشخيص IRR | Multiple roots | Return warning; do not select silently |
| `FIN-ALG-07-T03` | Payback | الاسترداد | Horizon ends before recovery | `not_reached` |
| `FIN-ALG-08-T01` | Funding Need | الاحتياج التمويلي | Source/use schedule does not balance | Reject |
| `FIN-ALG-08-T02` | Working Capital | رأس المال العامل | Supported negative NWC | Preserve; do not force zero |
| `FIN-ALG-09-T01` | Break-Even | التعادل | Contribution is negative | Block/not meaningful |
| `FIN-ALG-09-T02` | LTV/CAC | اقتصاديات الوحدة | Mixed cohort periods | Reject |
| `FIN-ALG-10-T01` | DSCR | خدمة الدين | No debt | `not_applicable` |
| `FIN-ALG-10-T02` | Covenant | التعهدات | Average passes but one period fails | Report breach |
| `FIN-ALG-11-T01` | Economic CBA | التحليل الاقتصادي | Financial and economic cash flows mixed | Reject |
| `FIN-ALG-11-T02` | Counterfactual | الحالة المرجعية | Missing without-project case | Block |
| `FIN-ALG-11-T03` | Externality | الأثر الخارجي | Material non-monetized impact hidden | Reject decision-ready status |
| `FIN-ALG-12-T01` | MCMC Integration | دمج مونت كارلو | Missing seed or generator version | Reject |
| `FIN-ALG-12-T02` | Correlation | الارتباط | Invalid correlation matrix | Reject or apply documented repair policy with audit |
| `FIN-ALG-12-T03` | Probability Label | تسمية الاحتمال | P(NPV&lt;0) labeled universal failure probability | Reject label |
| `PROC-ALG-01-T01` | Applicability | انطباق المشتريات | Competition ID exists but exact package absent | Require exact documents |
| `PROC-ALG-01-T02` | Override | أولوية المستند | Generic form conflicts with addendum | Addendum controls |
| `PROC-ALG-02-T01` | Official Form Gate | بوابة النموذج | Form is superseded | Block |
| `PROC-ALG-02-T02` | Official Form Gate | بوابة النموذج | Wrong contract category | Block |
| `PROC-ALG-02-T03` | Approval Claim | ادعاء الاعتماد | Official reference used to badge whole study | Reject |
| `METH-ALG-01-T01` | Methodology Registration | تسجيل المنهجية | World Bank reference labeled Saudi authority | Reject |
| `METH-ALG-01-T02` | Methodology Card | بطاقة المنهجية | Original card, rights-reviewed, human-approved | Allow reference use |
| `METH-ALG-02-T01` | Commercial Guard | الحارس التجاري | AI browses Aljdwa | Block and audit |
| `METH-ALG-02-T02` | Commercial Guard | الحارس التجاري | Aljdwa text embedded/vectorized | Block and purge/quarantine |
| `METH-ALG-02-T03` | Commercial Guard | الحارس التجاري | Exact written permission absent | Keep network access blocked |

## Decision Tests

## اختبارات القرار

| ID | Algorithm | Arabic | Test | Expected |
| --- | --- | --- | --- | --- |
| `DEC-ALG-01-T01` | Validation Gate | بوابة التحقق | No evidence pack | BLOCKED |
| `DEC-ALG-02-T01` | Personas | الشخصيات | Persona adds new number | Reject persona |
| `DEC-ALG-03-T01` | Consensus | الإجماع | Mixed votes | Average + dissent |
| `DEC-ALG-03-T02` | Consensus | الإجماع | Validation failed | Cannot approve |

## Dashboard Decision and Presentation Tests

## اختبارات قرار وعرض اللوحة

| ID | Algorithm | Arabic | Test | Expected |
| --- | --- | --- | --- | --- |
| `DASH-ALG-01-T01` | Provenance | سلسلة الإثبات | Numeric card has no algorithm ID | Reject |
| `DASH-ALG-01-T02` | Provenance | سلسلة الإثبات | Narrative introduces unsupported number | Reject |
| `DASH-ALG-01-T03` | Authorization | التفويض | Output belongs to another project | Deny and audit |
| `DASH-ALG-02-T01` | Readiness | الجاهزية | Required domain missing | `insufficient_data` |
| `DASH-ALG-02-T02` | Readiness | الجاهزية | Validation blocked | No numeric score |
| `DASH-ALG-02-T03` | Readiness | الجاهزية | Generic weights replace sector weights | Reject |
| `DASH-ALG-03-T01` | Confidence | الثقة | Evidence index called success probability | Reject |
| `DASH-ALG-03-T02` | Confidence | الثقة | MCMC uncertainty called decision agreement | Reject |
| `DASH-ALG-04-T01` | Frameworks | الأطر | SWOT claim lacks evidence/judgment label | Reject |
| `DASH-ALG-04-T02` | Frameworks | الأطر | Framework creates finance input | Reject |
| `DASH-ALG-05-T01` | Risk | المخاطر | Ordinal band shown as exact probability | Reject |
| `DASH-ALG-05-T02` | Risk | المخاطر | Risk lacks owner/treatment | Reject |
| `DASH-ALG-06-T01` | Scenario | السيناريو | Formula versions differ | Block comparison |
| `DASH-ALG-06-T02` | Scenario | السيناريو | Invented scenario probability | Reject |
| `DASH-ALG-07-T01` | Investment | الاستثمار | Valuation lacks method | Block panel |
| `DASH-ALG-07-T02` | Investment | الاستثمار | Narrative promises return | Reject |
| `DASH-ALG-08-T01` | State | الحالة | Frontend upgrades blocked to ready | Reject and audit |
| `DASH-ALG-09-T01` | Locale | اللغة | Required Arabic label missing | Fail UI acceptance |
| `DASH-ALG-10-T01` | Parity | التطابق | Dashboard and PDF differ | Block export |
| `DASH-ALG-11-T01` | External context | السياق الخارجي | Search snippet used as source | Reject |
| `DASH-ALG-11-T02` | External context | السياق الخارجي | Crawler fallback proposed | Reject fallback |
| `DASH-ALG-12-T01` | Legacy guard | حارس القديم | Screenshot value copied | Reject |
| `DASH-ALG-12-T02` | Legacy guard | حارس القديم | Generic pattern rebuilt with current contracts | Allow after review |

## AI Tests

## اختبارات الذكاء

| ID | Algorithm | Arabic | Test | Expected |
| --- | --- | --- | --- | --- |
| `AI-ALG-01-T01` | Model Routing | توجيه النماذج | Free classification | Llama/Groq |
| `AI-ALG-01-T02` | Model Routing | توجيه النماذج | Premium deep advisory | Kimi |
| `AI-ALG-03-T01` | Output Guard | حارس المخرجات | Unsupported price | Reject |
| `AI-ALG-03-T02` | Output Guard | حارس المخرجات | Cross-country analysis | Reject |

## Security and Admin Tests

## اختبارات الأمن والإدارة

| ID | Algorithm | Arabic | Test | Expected |
| --- | --- | --- | --- | --- |
| `SEC-ALG-01-T01` | Zero Trust | الأمن الصفري | Unauthorized contract | Reject |
| `SEC-ALG-02-T01` | Quarantine | العزل | Direct module call | Quarantine |
| `OPS-ALG-01-T01` | Health | صحة النظام | High error rate | Lower health |
| `ID-ALG-01-T01` | Human Verification | تحقق الإنسان | Suspicious signup | Challenge required |
| `ID-ALG-02-T01` | Authenticator MFA | MFA | Admin without MFA | Reject |
| `NOTIF-ALG-01-T01` | Notification Preferences | تفضيلات التنبيه | User disabled report email | Do not email |
| `NOTIF-ALG-02-T01` | External Delivery | التسليم الخارجي | WhatsApp without opt-in | Reject |
| `ADM-ALG-02-T01` | Admin Ops | عمليات الإدارة | Source adapter failing | Health snapshot shows degradation |
| `ADM-ALG-03-T01` | Incident Escalation | تصعيد الحوادث | Critical incident | Escalate and audit |
| `SUB-ALG-01-T01` | Trial | التجربة | Trial over quota | Deny |
| `ADM-ALG-01-T01` | Feature Flag | أعلام الخصائص | Workspace override | Applies with reason |
| `AN-ALG-01-T01` | Analytics Ingestion | استيعاب التحليلات | Unknown adapter | Reject |
| `AN-ALG-03-T01` | Privacy Sanitization | تنقيح الخصوصية | Raw email in payload | Reject or sanitize |
| `AN-ALG-04-T01` | Dashboard Dataset | Dataset لوحة | AI requests raw user events | Reject |
