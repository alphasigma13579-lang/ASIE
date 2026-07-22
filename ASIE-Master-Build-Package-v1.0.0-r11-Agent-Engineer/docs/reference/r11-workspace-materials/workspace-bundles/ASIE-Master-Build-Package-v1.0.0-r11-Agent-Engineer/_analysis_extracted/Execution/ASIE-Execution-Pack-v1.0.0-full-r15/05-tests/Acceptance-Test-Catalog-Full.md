# Acceptance Test Catalog Full

## كتالوج اختبارات القبول الكامل

## Architecture Tests

## اختبارات المعمارية

| ID | Test | Arabic | Expected |
| --- | --- | --- | --- |
| `AAS-T01` | No direct module calls | لا اتصال مباشر بين الموديولات | Rejected and quarantined |
| `AAS-T02` | All messages use System Bus | كل الرسائل عبر ناقل النظام | Pass |
| `AAS-T03` | SCL validates every payload | طبقة العقود تتحقق من كل Payload | Pass |
| `AAS-T04` | Market Data Layer term rejected | رفض مصطلح Market Data Layer | Non-compliant |
| `AAS-T05` | Kernel has no business logic | النواة بلا منطق أعمال | Pass |
| `AUTH-T01` | Signup without human verification when required | تسجيل بلا تحقق إنسان عند الحاجة | Rejected |
| `AUTH-T02` | Suspicious login skips bot challenge | دخول مشبوه يتجاوز التحدي | Rejected |
| `AUTH-T03` | Admin login without MFA | دخول آدمن بلا MFA | Rejected unless audited break-glass |
| `AUTH-T04` | TOTP secret sent to AI | سر TOTP يرسل إلى AI | Rejected |

## Market Tests

## اختبارات السوق

| ID | Test | Arabic | Expected |
| --- | --- | --- | --- |
| `MI-T01` | GPS outside Saudi Arabia | GPS خارج السعودية | Rejected |
| `MI-T02` | Manual city only | مدينة نصية فقط | Rejected |
| `MI-T03` | Source without URL or issuer | مصدر بلا رابط أو جهة | Rejected |
| `MI-T04` | Fewer than 5 price samples | أقل من 5 عينات سعر | Insufficient samples |
| `MI-T05` | Outlier price detected | سعر شاذ مكتشف | Outlier report |
| `MI-T06` | User required to upload public report | إجبار المستخدم على رفع تقرير عام | Rejected |
| `MI-T07` | Evidence claim without source URL | معلومة بلا رابط مصدر | Rejected |
| `MI-T08` | Similar case without link | تجربة مشابهة بلا رابط | Rejected |
| `MI-T09` | AI deep research claim without evidence id | ادعاء بحث عميق بلا Evidence ID | Rejected |
| `MI-T10` | Price sample without marketplace source | عينة سعر بلا مصدر سوق | Rejected |
| `SECTOR-T01` | Project has no primary sector | مشروع بلا قطاع رئيسي | Rejected |
| `SECTOR-T02` | Project has sector but no subsector | مشروع بلا تصنيف فرعي | Rejected |
| `SECTOR-T03` | Generic scoring used for all sectors | تقييم عام لكل القطاعات | Rejected |
| `SECTOR-T04` | Sector source mapping missing | ربط مصادر القطاع مفقود | Rejected |
| `SECTOR-T05` | English sector shown without Arabic in Arabic UI | قطاع إنجليزي بلا عربي في واجهة عربية | Rejected |
| `SRC-T01` | Source adapter lacks legal access status | موصل بلا حالة وصول قانونية | Rejected |
| `SRC-T02` | Restricted source auto-crawled | زحف تلقائي لمصدر مقيد | Rejected |
| `SRC-T03` | Stale Pinecone evidence used as fresh | استخدام كاش Pinecone قديم كحديث | Rejected |
| `SRC-T04` | Full report copied into user output | نسخ تقرير كامل للمستخدم | Rejected |
| `SRC-T05` | Crawler bypasses blocking protection | زاحف يتجاوز الحجب | Rejected |
| `SRC-T06` | Arabic source displayed only in English | مصدر عربي يعرض بالإنجليزية فقط | Rejected unless user requested English |
| `SRC-T07` | English source mistranslated as official Arabic name | مصدر إنجليزي يترجم اسمًا رسميًا بشكل مضلل | Rejected |
| `SRC-T08` | Source language metadata missing | Metadata لغة المصدر مفقودة | Rejected |

## Government Open Data and Legal Access Tests

## اختبارات البيانات الحكومية المفتوحة والوصول النظامي

| ID | Test | Arabic | Expected |
| --- | --- | --- | --- |
| `GOV-T01` | Public webpage assumed to be open data | اعتبار صفحة عامة بيانات مفتوحة | Rejected |
| `GOV-T02` | Entire government domain approved by one record | اعتماد نطاق حكومي كامل بسجل واحد | Rejected |
| `GOV-T03` | Dataset license is missing or cannot be versioned | ترخيص المجموعة مفقود أو غير قابل للتوثيق | Deny |
| `GOV-T04` | Source terms changed after approval | تغيرت الشروط بعد الاعتماد | Suspend and re-review |
| `GOV-T05` | Data classification is unknown | تصنيف البيانات غير معلوم | Deny |
| `GOV-T06` | Non-public government data fetched by crawler | جلب بيانات حكومية غير مفتوحة بالزحف | Reject and quarantine |
| `GOV-T07` | Denied data-sharing request replaced by scraping | استبدال طلب مشاركة مرفوض بالزحف | Reject and security incident |
| `GOV-T08` | CAPTCHA, WAF, paywall, login, or rate limit bypass | تجاوز حماية أو دخول أو حد طلبات | Reject and security incident |
| `GOV-T09` | Repeated `401`, `403`, or `429` ignored | تجاهل رفض أو حجب أو تحديد متكرر | Stop connector |
| `GOV-T10` | Undocumented private endpoint used | استخدام API خاص غير موثق | Reject and incident |
| `GOV-T11` | Source fetch has no lawful purpose ID | الجلب بلا معرف غرض مشروع | Deny |
| `GOV-T12` | Personal data reaches AI before privacy gate | وصول بيانات شخصية إلى AI قبل بوابة الخصوصية | Reject and quarantine |
| `GOV-T13` | Joined datasets make individuals identifiable | دمج مجموعات يجعل الأفراد قابلين للتعرف | Reclassify and block |
| `GOV-T14` | Foreign processor receives personal data without transfer assessment | نقل بيانات شخصية لمعالج خارجي بلا تقييم | Deny |
| `GOV-T15` | Retention or deletion policy is missing | سياسة الاحتفاظ أو الإتلاف مفقودة | Deny |
| `GOV-T16` | Approval is expired, suspended, revoked, or missing | اعتماد منتهي أو معلق أو ملغى أو مفقود | Deny |
| `GOV-T17` | Admin enables source without new Compliance decision | الآدمن يفعل مصدرًا بلا قرار امتثال جديد | Reject and audit |
| `GOV-T18` | Retrieved redirect leaves approved host/path scope | إعادة التوجيه تخرج عن النطاق المعتمد | Block |
| `GOV-T19` | Fetch resolves to private IP or metadata service | المصدر يتحول إلى عنوان خاص أو خدمة Metadata | Block as SSRF |
| `GOV-T20` | Oversized, malicious, active, or decompression-bomb file | ملف ضار أو نشط أو كبير أو قنبلة ضغط | Quarantine |
| `GOV-T21` | Retrieved text attempts prompt injection | النص المسترجع يحاول حقن Prompt | Treat as untrusted data |
| `GOV-T22` | Evidence lacks license, classification, hash, or decision ID | الدليل ينقصه ترخيص أو تصنيف أو بصمة أو قرار | Exclude from all consumers |
| `GOV-T23` | Government fact and ASIE transformation are not separated | خلط الحقيقة الرسمية بتحويل ASIE | Reject report |
| `GOV-T24` | Output implies government endorsement | المخرج يوحي بتأييد حكومي | Reject report |
| `GOV-T25` | Required attribution is omitted | إغفال النسبة المطلوبة للمصدر | Reject report |
| `GOV-T26` | Raw data redistributed despite license restriction | إعادة توزيع خام رغم قيد الترخيص | Reject export |
| `GOV-T27` | Credential or token appears in log, event, or AI prompt | ظهور سر في السجل أو الرسالة أو Prompt | Reject and incident |
| `GOV-T28` | Source is enabled without applicable NCA profile | تفعيل المصدر بلا ملف ضوابط NCA منطبق | Deny |
| `GOV-T29` | User-facing claim says legally certified without human approval | ادعاء اعتماد نظامي بلا اعتماد بشري | Reject |
| `GOV-T30` | Kill switch does not stop scheduled and interactive fetches | مفتاح الإيقاف لا يوقف كل الجلب | Release blocker |
| `GOV-T31` | Registered or source-approved API is enabled | تفعيل API يحتاج تسجيلًا أو موافقة | Deny under strict profile |
| `GOV-T32` | Paid, subscription, login, or contract source is enabled | تفعيل مصدر مدفوع أو تعاقدي أو يتطلب دخولًا | Deny under strict profile |
| `GOV-T33` | Government data-sharing route is enabled | تفعيل مسار مشاركة بيانات حكومية غير مفتوحة | Release blocker |
| `GOV-T34` | Public document is ingested without explicit open-use terms | إدخال وثيقة عامة بلا تصريح استخدام مفتوح | Reference only or deny |
| `GOV-T35` | GASTAT exact dataset/API has open-use evidence and no authentication | مصدر إحصائي محدد ومفتوح بلا مصادقة | Eligible for internal approval |
| `GOV-T36` | GASTAT output omits official attribution | مخرج إحصائي بلا نسبة للهيئة | Reject report/export |
| `GOV-T37` | Transformed GASTAT value is labeled as unchanged official fact | قيمة معالجة تعرض كحقيقة رسمية دون تعديل | Reject report |
| `GOV-T38` | GASTAT logo, trademark, third-party item, or microdata is ingested | إدخال شعار أو مادة طرف ثالث أو بيانات دقيقة | Block |
| `GOV-T39` | Entire GASTAT domain is approved instead of an exact dataset/endpoint | اعتماد نطاق الهيئة كاملًا | Reject |
| `GOV-T40` | Mostaql projects page is crawled or fetched by backend | جلب صفحة مشاريع مستقل آليًا | Block and audit |
| `GOV-T41` | Mostaql project text, budget, username, offer, or screenshot is stored | تخزين محتوى مشروع أو بيانات مستخدم من مستقل | Block and quarantine |
| `GOV-T42` | Mostaql content is summarized, embedded, scored, or used for alerts | تحليل أو فهرسة أو تنبيه مشتق من مستقل | Block |
| `GOV-T43` | Third-party scraper is used to bypass Mostaql reference-only status | استخدام وسيط جمع لتجاوز حالة المرجع | Block and incident |
| `GOV-T44` | Mostaql outbound link is saved without a target fetch | حفظ رابط مستقل دون جلبه | Pass |
| `GOV-T45` | UI claims Mostaql is integrated, synced, or monitored | الواجهة تدعي ربط أو مزامنة مستقل | Reject copy |

## Official Strategy Reference and Original Writing Tests

## اختبارات المراجع الاستراتيجية والكتابة الأصلية

| ID | Test | Arabic | Expected |
| --- | --- | --- | --- |
| `STRAT-T01` | Backend fetches SDAIA terms or NSDAI page after automated rejection | جلب سدايا بعد رفض الطلب الآلي | Block and audit |
| `STRAT-T02` | Duplicate NSDAI URL with fragment creates a second record | تكرار رابط الاستراتيجية بسبب Fragment | Canonicalize to one record |
| `STRAT-T03` | Source HTML, full text, paragraph, list, or screenshot is stored | تخزين محتوى المرجع أو صورته | Reject and quarantine |
| `STRAT-T04` | Official logo, icon, diagram, or page layout is copied | نسخ هوية أو رسم أو تخطيط الصفحة | Reject |
| `STRAT-T05` | Source text or embedding is sent to AI/Pinecone | إرسال نص المرجع أو تضمينه للذكاء | Block and audit |
| `STRAT-T06` | ASIE card lacks accuracy or originality review | بطاقة بلا مراجعة دقة أو أصالة | Reject |
| `STRAT-T07` | Generated copy follows source wording or structure | نص مولد يحاكي صياغة المصدر أو بنيته | Reject publication |
| `STRAT-T08` | Official title and publisher name are used accurately with a source link | استخدام الاسم الرسمي والرابط بدقة | Pass |
| `STRAT-T09` | NCA strategy page is used as an ECC/NCNICC control | استخدام الاستراتيجية بدل ضابط NCA | Reject compliance claim |
| `STRAT-T10` | Report says NCA approved or certified ASIE | ادعاء اعتماد أو تصديق NCA | Reject |
| `STRAT-T11` | E-participation consultations, submissions, metrics, or user data are ingested | جمع استشارات أو مشاركات أو بيانات مستخدمين | Block |
| `STRAT-T12` | ASIE submits, votes, comments, or authenticates on e-participation | تفاعل آلي مع منصة المشاركة | Block and incident |
| `STRAT-T13` | DGA sustainability page is treated as a certification score | استخدام صفحة الاستدامة كشهادة أو درجة | Reject |
| `STRAT-T14` | DGA digital-transformation overview replaces an exact formal standard | استبدال المعيار الرسمي بصفحة عامة | Reject |
| `STRAT-T15` | SDAIA strategy text is reconstructed from search snippets | إعادة بناء نص استراتيجية سدايا من نتائج البحث | Reject |
| `STRAT-T16` | Report shows original ASIE interpretation, official link, review date, and disclaimer | عرض مواءمة أصلية مع الرابط والتنبيه | Pass |
| `STRAT-T17` | Expired or withdrawn strategy card reaches AI or Reports | بطاقة منتهية تصل للذكاء أو التقرير | Block |
| `STRAT-T18` | Output implies partnership, approval, endorsement, or official measurement | إيحاء بشراكة أو موافقة أو قياس رسمي | Reject |
| `STRAT-T19` | Arabic official name is mistranslated or replaced by an invented English name | تحريف الاسم الرسمي | Reject |
| `STRAT-T20` | Reference unavailable and system uses crawler, cache service, or mirror | تجاوز تعذر المرجع بزاحف أو نسخة مرآة | Block |

## Finance Tests

## اختبارات التمويل

| ID | Test | Arabic | Expected |
| --- | --- | --- | --- |
| `FIN-T01` | Missing required numeric source | رقم مطلوب بلا مصدر | Blocking error |
| `FIN-T02` | AI-generated number supplied | رقم مولد من AI | Rejected |
| `FIN-T03` | Sensitivity without baseline | حساسية بلا خط أساس | Rejected |
| `FIN-T04` | MCMC without fixed seed | MCMC بلا بذرة | Rejected |
| `FIN-T05` | Supplier quote missing unit | عرض مورد بلا وحدة | Row rejected |

## Decision Tests

## اختبارات القرار

| ID | Test | Arabic | Expected |
| --- | --- | --- | --- |
| `DEC-T01` | Missing evidence pack | حزمة أدلة ناقصة | Decision blocked |
| `DEC-T02` | Persona invents number | شخصية تخترع رقمًا | Persona rejected |
| `DEC-T03` | Minority objection exists | وجود اعتراض أقلية | Must appear |
| `DEC-T04` | Validation failed but approve attempted | فشل تحقق مع محاولة موافقة | Block approve |

## Admin and Audit Tests

## اختبارات الإدارة والتدقيق

| ID | Test | Arabic | Expected |
| --- | --- | --- | --- |
| `ADM-T01` | Admin changes feature flag | تعديل Feature Flag | Audit event |
| `ADM-T02` | Admin grants credit | منح رصيد | Audit event |
| `AUD-T01` | Contract violation | مخالفة عقد | Quarantine |
| `AUD-T02` | Provider failure repeated | فشل مزود متكرر | Health degradation |
| `ADM-T03` | Maintenance mode changed without MFA | تغيير وضع الصيانة بلا MFA | Rejected |
| `ADM-T04` | Incident escalation lacks audit | تصعيد حادث بلا تدقيق | Rejected |
| `ADM-T05` | Maintenance team sees unauthorized user data | فريق الصيانة يرى بيانات غير مصرح بها | Rejected |
| `NOTIF-T01` | WhatsApp alert without opt-in | تنبيه واتساب بلا موافقة | Rejected |
| `NOTIF-T02` | Telegram alert sends MFA code | تليجرام يرسل رمز MFA | Rejected |
| `NOTIF-T03` | User cannot customize notification type | المستخدم لا يستطيع تخصيص نوع التنبيه | Rejected |
| `NOTIF-T04` | In-app notification lacks read/unread state | إشعار داخلي بلا حالة قراءة | Rejected |
| `AN-T01` | Google Analytics raw PII sent to AI | إرسال PII خام من Google Analytics إلى AI | Rejected |
| `AN-T02` | Zoho Analytics used as finance input | استخدام Zoho Analytics كمدخل مالي | Rejected |
| `AN-T03` | Analytics event lacks anonymous user key | حدث تحليلي بلا مفتاح مجهول | Rejected or sanitized |
| `AN-T04` | Funnel chart lacks date range | شارت قمع بلا نطاق تاريخ | Rejected |

## Smart Site and Dynamic Chart Tests

## اختبارات الموقع الذكي والشارتات الديناميكية

| ID | Test | Arabic | Expected |
| --- | --- | --- | --- |
| `SMART-T01` | Page uses static fake intelligence | صفحة تستخدم ذكاء وهمي ثابت | Rejected |
| `SMART-T02` | AI exists only as UI chat | الذكاء موجود كشات واجهة فقط | Rejected |
| `SMART-T03` | Smart screen lacks evidence link | شاشة ذكية بلا رابط دليل | Rejected where evidence is required |
| `LAND-T01` | Landing screenshot exposes user data | لقطة صفحة هبوط تكشف بيانات مستخدم | Rejected |
| `LAND-T02` | Landing chart implies guaranteed success | شارت هبوط يوحي بضمان النجاح | Rejected |
| `LAND-T03` | Landing preview lacks demo/anonymized/mock tag | معاينة الهبوط بلا وسم عينة/مخفي/نموذج | Rejected |
| `LAND-T04` | Landing uses fake production claim | صفحة الهبوط تستخدم ادعاء إنتاجي وهمي | Rejected |
| `CHART-T01` | Chart without owner module | شارت بلا موديول مالك | Rejected |
| `CHART-T02` | Chart data generated by AI | بيانات شارت مولدة من AI | Rejected |
| `CHART-T03` | Finance chart not based on Finance Engine | شارت مالي ليس من محرك التمويل | Rejected |
| `CHART-T04` | Market chart lacks source ids | شارت سوق بلا معرفات مصادر | Rejected |
| `CHART-T05` | Map chart lacks GPS or Map Pin context | شارت خريطة بلا GPS أو Pin | Rejected |
| `CHART-T06` | Chart has no empty/loading/error state | شارت بلا حالات فراغ/تحميل/خطأ | Rejected |
| `CHART-T07` | Chart lacks RTL labels | شارت بلا تسميات RTL | Rejected |
| `CHART-T08` | Tooltip hides source or formula | Tooltip يخفي المصدر أو المعادلة | Rejected where relevant |
| `CHART-T09` | MCMC chart has no seed reference | شارت MCMC بلا مرجع seed | Rejected |
| `CHART-T10` | Admin chart uses non-audited data | شارت إدارة يستخدم بيانات بلا تدقيق | Rejected |

## Project Intelligence Dashboard Tests

## اختبارات لوحة ذكاء المشروع

| ID | Test | Arabic | Expected |
| --- | --- | --- | --- |
| `DASH-T01` | Metric has no owner Module | بطاقة رقمية بلا موديول مالك | Rejected |
| `DASH-T02` | Metric has no contract or algorithm version | رقم بلا عقد أو نسخة خوارزمية | Rejected |
| `DASH-T03` | Calculated value has no formula lineage | قيمة محسوبة بلا سلسلة معادلة | Rejected |
| `DASH-T04` | Estimate is displayed as observed fact | تقدير يعرض كحقيقة مرصودة | Rejected |
| `DASH-T05` | Evidence confidence is labeled success probability | مؤشر ثقة الأدلة يسمى احتمال نجاح | Rejected |
| `DASH-T06` | Decision agreement and MCMC probability are merged | دمج اتفاق القرار باحتمال المحاكاة | Rejected |
| `DASH-T07` | Required readiness domain is missing | مجال جاهزية مطلوب ناقص | `insufficient_data` |
| `DASH-T08` | Validation is blocked but numeric final score appears | ظهور درجة نهائية مع منع التحقق | Rejected |
| `DASH-T09` | Generic score weights replace sector weights | أوزان عامة تستبدل أوزان القطاع | Rejected |
| `DASH-T10` | SWOT fact has no evidence or judgment label | حقيقة SWOT بلا دليل أو وسم حكم | Rejected |
| `DASH-T11` | BMC item automatically becomes finance input | بند نموذج العمل يصبح مدخلًا ماليًا | Rejected |
| `DASH-T12` | Risk ordinal band is shown as exact probability | نطاق خطر ترتيبي يعرض كنسبة دقيقة | Rejected |
| `DASH-T13` | Risk record lacks owner, treatment, or due date | خطر بلا مالك أو معالجة أو تاريخ | Rejected |
| `DASH-T14` | Scenario hides variables changed from baseline | سيناريو يخفي المتغيرات المعدلة | Rejected |
| `DASH-T15` | Scenario comparison uses incompatible formula versions | مقارنة سيناريوهات بمعادلات غير متوافقة | Blocked |
| `DASH-T16` | Named scenario gets an invented probability | اختراع احتمال لسيناريو مسمى | Rejected |
| `DASH-T17` | MCMC view hides seed or distributions | شاشة MCMC تخفي البذرة أو التوزيعات | Rejected |
| `DASH-T18` | Valuation shown without method and assumptions | تقييم بلا طريقة وافتراضات | Blocked |
| `DASH-T19` | Investor text guarantees funding or return | نص المستثمر يضمن تمويلًا أو عائدًا | Rejected |
| `DASH-T20` | Dashboard and report raw values differ for same run | اختلاف قيمة اللوحة والتقرير | Export blocked |
| `DASH-T21` | Arabic view has broken RTL or clipped labels | كسر RTL أو قص التسميات العربية | Rejected |
| `DASH-T22` | English view preserves Arabic-only required UI label | واجهة إنجليزية بتسمية عربية فقط | Rejected |
| `DASH-T23` | Chart lacks accessible table | شارت بلا جدول بديل | Rejected |
| `DASH-T24` | Mobile page has horizontal page scrolling | تمرير أفقي للصفحة على الجوال | Rejected |
| `DASH-T25` | Blocked section disappears without reason | اختفاء قسم ممنوع بلا سبب | Rejected |
| `DASH-T26` | Production silently falls back to demo values | الإنتاج يستخدم أرقامًا تجريبية بصمت | Rejected |
| `DASH-T27` | Legacy screenshot score or company name is reused | إعادة استخدام درجة أو اسم من الصور القديمة | Rejected |
| `DASH-T28` | Government-approved badge has no exact form proof | وسم اعتماد حكومي بلا إثبات نموذج محدد | Rejected |
| `DASH-T29` | SWOT/BMC/VPC is labeled official government form | إطار تحليلي يسمى نموذجًا حكوميًا | Rejected |
| `DASH-T30` | Cross-project output is returned | مخرج من مشروع آخر | Denied and audited |
| `DASH-T31` | Source/formula drawer leaks credentials or hidden prompt | نافذة الإثبات تكشف سرًا أو Prompt | Rejected and incident |
| `DASH-T32` | Reference-only source text is displayed or sent to AI | عرض نص مرجعي أو إرساله للذكاء | Blocked |
| `DASH-T33` | External-context panel uses a search snippet | لوحة السياق تستخدم مقتطف بحث | Rejected |
| `DASH-T34` | External context unavailable and crawler fallback runs | تعذر السياق وتشغيل زاحف بديل | Blocked |
| `DASH-T35` | Tooltip omits unit, period, scenario, and date | Tooltip يخفي الوحدة والفترة والسيناريو والتاريخ | Rejected |
| `DASH-T36` | Low value is green where lower is worse | قيمة منخفضة خضراء رغم أنها أسوأ | Rejected |
| `DASH-T37` | Export recalculates finance | التصدير يعيد حساب التمويل | Rejected |
| `DASH-T38` | Shared link is not scoped, expiring, or revocable | رابط مشاركة غير مقيد أو غير قابل للإلغاء | Rejected |
| `DASH-T39` | Project input changes but same run is mutated | تغيير المدخلات يعدل التشغيل نفسه | Rejected; create new run |
| `DASH-T40` | Decision persona exposes hidden chain-of-thought | عرض التفكير الداخلي للشخصية | Rejected |

## Professional Feasibility and Procurement Acceptance Tests r15

| ID | Test | Arabic | Expected |
| --- | --- | --- | --- |
| `FST-T01` | Government competition selects lower study profile | منافسة حكومية تختار ملفًا أقل | Reject; force `GOVERNMENT_COMPETITION` |
| `FST-T02` | User downgrades profile to hide economic/legal/technical work | خفض الملف لإخفاء تحليل مطلوب | Reject and audit |
| `FST-T03` | Mandatory chapter missing but study says complete | فصل إلزامي مفقود والدراسة مكتملة | Block completion |
| `FST-T04` | `not_applicable` has no approved reason | غير منطبق بلا مبرر معتمد | Reject state |
| `FST-T05` | Market demand exceeds practical capacity | الطلب يتجاوز الطاقة العملية | Contradiction; block affected forecast |
| `FST-T06` | Revenue starts before commissioning | الإيراد يبدأ قبل التشغيل التجريبي | Contradiction; block run |
| `FST-T07` | Staffing cost differs from operating headcount | تكلفة العمالة لا تطابق التشغيل | Contradiction; block run |
| `FST-T08` | Integrated balance sheet does not balance | الميزانية لا تتوازن | Block financial output |
| `FST-T09` | Cash-flow closing cash differs from balance sheet | النقد الختامي غير متطابق | Block financial output |
| `FST-T10` | NPV shown without rate, horizon, basis, or perspective | NPV بلا اصطلاحات | Block metric |
| `FST-T11` | IRR has multiple roots and UI shows one clean value | IRR متعدد الجذور يعرض رقمًا واحدًا | Reject; show diagnostic |
| `FST-T12` | Negative contribution still receives break-even value | مساهمة سالبة مع نقطة تعادل | Return blocked/not meaningful |
| `FST-T13` | Average DSCR hides a period breach | متوسط DSCR يخفي إخفاق فترة | Show breach and block covenant pass |
| `FST-T14` | Private NPV and economic ENPV are mixed | خلط المالي بالاقتصادي | Reject output |
| `FST-T15` | Economic analysis lacks with/without case | تحليل اقتصادي بلا مع/بدون | Block CBA |
| `FST-T16` | Monte Carlo lacks seed, distribution source, or correlation policy | مونت كارلو ناقص الضوابط | Reject simulation |
| `FST-T17` | MCMC probability is called project success probability | تسمية ناتج المحاكاة احتمال نجاح | Reject wording |
| `FST-T18` | AI supplies price, discount rate, tax, distribution, or weight | الذكاء يورد مدخلًا رقميًا | Reject and audit |
| `FST-T19` | Generic MOF form treated as controlling competition document | نموذج مالي عام يحل محل مستند المنافسة | Reject |
| `FST-T20` | Exact competition documents are missing | مستندات المنافسة المحددة مفقودة | `procurement.exact.documents.required.v1` |
| `FST-T21` | Official form is stale, superseded, or wrong contract type | نموذج رسمي قديم أو غير منطبق | Block active use |
| `FST-T22` | Output claims a government-approved feasibility study | ادعاء اعتماد حكومي للدراسة | Reject and compliance incident |
| `FST-T23` | Backend, AI, crawler, vector job, or scheduler accesses Aljdwa | وصول آلي لمنصة الجدوى | Block and audit |
| `FST-T24` | Approved original ASIE methodology card is used without source content | استخدام بطاقة أصلية معتمدة | Allow with reference-only label |
| `FST-T25` | UNIDO/World Bank/IFC/Green Book is presented as Saudi authority | مرجع عالمي يقدم كسلطة سعودية | Reject |
| `FST-T26` | Framework diagram creates unsupported score or finance input | إطار تحليلي يولد رقمًا بلا دليل | Reject |
| `FST-T27` | Reports or frontend recalculates feasibility values | الواجهة أو التقارير تعيد الحساب | Reject architecture |
| `FST-T28` | Direct Feasibility-to-Finance Module call | اتصال مباشر بين الموديولات | Quarantine; AAS violation |
| `FST-T29` | Arabic output translates an official form name misleadingly | ترجمة مضللة لاسم رسمي | Fail bilingual acceptance |
| `FST-T30` | Dashboard hides blocked chapter in PDF export | التصدير يخفي فصلًا محجوبًا | Block export |
