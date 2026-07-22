# Builder Agent or Engineer Stop Rules

## قواعد توقف Builder Agent or Engineer

Builder Agent or Engineer must stop immediately if:

يجب على الـAgent أو مهندس البرمجيات التوقف فورًا إذا:

1. It needs a new architecture layer, controller, bus, or heart.
   احتاج إلى طبقة أو متحكم أو ناقل أو قلب جديد.

2. It wants to use `Market Data Layer`.
   أراد استخدام `Market Data Layer`.

3. It wants direct module-to-module calls.
   أراد اتصالًا مباشرًا بين الموديولات.

4. It wants AI to generate finance numbers or chart datasets.
   أراد من AI توليد أرقام مالية أو بيانات شارتات.

5. It wants the user to upload public reports.
   أراد من المستخدم رفع تقارير عامة.

6. It has evidence without source URL.
   لديه دليل بلا رابط مصدر.

7. It treats Pinecone as source of truth.
   تعامل مع Pinecone كمصدر حقيقة.

8. It treats Google Analytics or Zoho Analytics as market or finance evidence.
   تعامل مع Google Analytics أو Zoho Analytics كدليل سوق أو تمويل.

9. It crawls restricted sources or bypasses blocking.
   زحف على مصادر مقيدة أو تجاوز الحجب.

10. It displays Arabic source evidence only in English unless user requested English.
    عرض دليلًا عربيًا بالإنجليزية فقط دون طلب المستخدم.

11. It omits human verification from signup or suspicious login.
    حذف تحقق الإنسان من التسجيل أو الدخول المشبوه.

12. It allows admin or maintenance roles without MFA.
    السماح لأدوار الإدارة أو الصيانة بدون MFA.

13. It sends Telegram or WhatsApp notifications without user opt-in.
    إرسال تنبيهات تليجرام أو واتساب بلا موافقة المستخدم.

14. It sends MFA secrets or codes through external notification channels.
    إرسال أسرار أو رموز MFA عبر قنوات تنبيه خارجية.

15. It implements a weak admin panel without operations, incidents, maintenance, audit, and team monitoring.
    تنفيذ لوحة آدمن ضعيفة بلا عمليات، حوادث، صيانة، تدقيق، ومتابعة فرق.

16. It analyzes a project without primary sector, subsector, and sector-specific criteria.
    تحليل مشروع بلا قطاع رئيسي وتصنيف فرعي ومعايير خاصة بالقطاع.

17. It uses one generic scoring model for all sectors.
    استخدام نموذج تقييم عام واحد لكل القطاعات.

18. It treats a public government webpage as licensed open data.
    اعتبر صفحة حكومية عامة بيانات مفتوحة مرخصة.

19. It approves a whole ministry/authority domain instead of an exact dataset, endpoint, feed, or bounded path.
    اعتمد نطاق وزارة أو هيئة كاملًا بدل مصدر محدد.

20. It fetches government data with unknown classification, license, terms, purpose, or approval.
    جلب بيانات حكومية مع غموض في التصنيف أو الترخيص أو الشروط أو الغرض أو الاعتماد.

21. It replaces a government data-sharing agreement or denied request with crawling.
    استبدل اتفاق مشاركة البيانات أو الطلب المرفوض بالزحف.

22. It bypasses CAPTCHA, WAF, login, paywall, robots, rate limits, blocking, or another technical control.
    تجاوز CAPTCHA أو WAF أو الدخول أو الحجب أو حدود الطلب أو أي حماية تقنية.

23. It sends personal data to AI, vectors, analytics, cloud, or a foreign processor before the PDPL and transfer gates pass.
    أرسل بيانات شخصية قبل اجتياز بوابات الحماية والنقل خارج المملكة.

24. It omits the applicable NCNICC, ECC, DCC, CCC, CSCC, or sector-control assessment.
    أغفل تحديد ضوابط الأمن السيبراني السعودية المنطبقة.

25. It lets AI, Admin, or a feature flag issue or override legal approval.
    سمح للذكاء أو الآدمن أو Feature Flag بإصدار أو تجاوز الاعتماد القانوني.

26. It claims government approval or complete legal compliance without documented authorized human sign-off.
    ادعى اعتمادًا حكوميًا أو توافقًا كاملًا بلا توقيع بشري مختص وموثق.

27. It cannot stop all source jobs and downstream use through the source kill switch.
    عجز عن إيقاف كل عمليات المصدر واستخداماته التابعة بمفتاح الإيقاف.

28. It enables a source requiring registration, login, payment, subscription, contract, licensed API, source-issued credential, or external approval.
    فعّل مصدرًا يحتاج تسجيلًا أو دخولًا أو دفعًا أو عقدًا أو ترخيصًا أو موافقة خارجية.

29. It implements government data sharing as an active route in r15.
    نفّذ مشاركة البيانات الحكومية غير المفتوحة كمسار نشط في r15.

30. It fetches, crawls, previews, stores, summarizes, embeds, scores, monitors, or alerts on Mostaql project content.
    جمع أو حلل أو خزّن أو راقب محتوى مشاريع مستقل.

31. It treats a commercial third-party scraper as proof of official open-data permission.
    اعتبر خدمة جمع خارجية دليلًا على الإتاحة الرسمية.

32. It uses GASTAT data without attribution, dataset-level scope, or a clear ASIE transformation label.
    استخدم بيانات الهيئة بلا نسبة أو تحديد للمجموعة أو بيان المعالجة.

33. It fetches, crawls, mirrors, snapshots, parses, embeds, or stores content from an official strategy-reference page.
    جلب أو نسخ أو فهرس محتوى صفحة مرجعية استراتيجية.

34. It sends source-page text, HTML, screenshots, images, or search-snippet reconstruction to AI.
    أرسل محتوى المرجع أو إعادة بنائه إلى الذكاء الاصطناعي.

35. It publishes an alignment card without human accuracy, originality, attribution, and non-endorsement review.
    نشر بطاقة مواءمة دون مراجعة بشرية للدقة والأصالة والنسبة.

36. It uses the NCA strategy page as proof of NCNICC, ECC, DCC, CCC, CSCC, or sector-control compliance.
    استخدم صفحة الاستراتيجية بدل دليل تطبيق ضوابط الأمن السيبراني.

37. It treats DGA overview pages as certification or substitutes them for exact formal standards.
    اعتبر صفحات هيئة الحكومة الرقمية شهادة أو بديلًا للمعيار الرسمي.

38. It ingests consultations, submissions, metrics, or participant data from GOV.SA e-participation.
    جمع محتوى المشاركة الإلكترونية أو بيانات المشاركين.

39. It claims SDAIA, NCA, DGA, GOV.SA, or any government approval, partnership, endorsement, or official measurement.
    ادعى موافقة أو شراكة أو اعتمادًا أو قياسًا حكوميًا.

40. It creates a Dashboard Module, Dashboard Layer, alternative orchestrator, or new truth owner.
    أنشأ موديولًا أو طبقة أو منسقًا معماريًا أو مصدر حقيقة جديدًا للوحة.

41. It displays a number without owner, contract, algorithm, formula, evidence/assumption, unit, period, run, and timestamp.
    عرض رقمًا بلا مالك أو عقد أو خوارزمية أو معادلة أو دليل أو وحدة أو فترة أو تشغيل أو توقيت.

42. It calculates finance in the frontend or lets AI generate a metric or chart value.
    حسب التمويل في الواجهة أو سمح للذكاء بتوليد رقم بطاقة أو شارت.

43. It labels evidence confidence, decision agreement, or a named scenario as probability of business success.
    سمى ثقة الأدلة أو اتفاق القرار أو السيناريو احتمالًا لنجاح المشروع.

44. It publishes a final readiness score while a required domain is missing or the Validation Gate is blocked.
    نشر درجة جاهزية مع نقص مجال مطلوب أو منع بوابة التحقق.

45. It uses generic scoring weights instead of the active sector-specific profile.
    استخدم أوزان تقييم عامة بدل ملف القطاع النشط.

46. It migrates a company name, provider, score, percentage, amount, date, map, claim, or wording from a legacy screenshot.
    نقل اسمًا أو مزودًا أو درجة أو مبلغًا أو تاريخًا أو خريطة أو ادعاءً من صورة قديمة.

47. It labels SWOT, PESTEL, Porter, BMC, VPC, an ASIE template, or AI prose as an official government form.
    سمى إطارًا تحليليًا أو قالب ASIE أو نص AI نموذجًا حكوميًا رسميًا.

48. It shows a government-approved badge without exact issuer, form ID, version, scope, source, and documented review.
    عرض اعتمادًا حكوميًا بلا جهة ونموذج وإصدار ونطاق ومصدر ومراجعة موثقة.

49. Dashboard, PDF, presentation, or spreadsheet values differ for the same run and scenario.
    اختلفت قيم اللوحة أو PDF أو العرض أو الجدول لنفس التشغيل والسيناريو.

50. Arabic RTL or English LTR visual acceptance fails on desktop or mobile.
    فشل فحص العربية RTL أو الإنجليزية LTR على الحاسوب أو الجوال.

51. It creates a Feasibility, Procurement, or Methodology Module or calls owner Modules directly.
    أنشأ موديولًا جديدًا للجدوى أو المشتريات أو المنهجية أو اتصل مباشرة بالموديولات.

52. It selects or downgrades a feasibility depth profile with AI or to hide a required chapter.
    اختار أو خفض ملف عمق الدراسة بالذكاء أو لإخفاء فصل مطلوب.

53. It marks the study complete while a required chapter is missing, stale, blocked, or unreconciled.
    أعلن اكتمال الدراسة مع فصل مطلوب ناقص أو قديم أو محجوب أو غير مطابق.

54. Market demand, practical capacity, operating resources, implementation timing, and financial volume do not reconcile.
    لم تتطابق السوق والطاقة والتشغيل والتوقيت والحجم المالي.

55. Integrated statements do not balance or silently mix currency, period, real/nominal, tax, or perspective bases.
    لم تتوازن القوائم أو اختلطت أسس الحساب دون تصريح.

56. It displays NPV, IRR, break-even, debt, or economic metrics without the required conventions and applicability.
    عرض مؤشرات مالية أو اقتصادية بلا اصطلاحات وانطباق واضح.

57. It mixes private financial analysis with economic/social cost-benefit analysis.
    خلط التحليل المالي الخاص بالتحليل الاقتصادي والاجتماعي.

58. It runs Monte Carlo without a fixed seed, approved distributions/ranges, correlation controls, and reproducible configuration.
    شغّل مونت كارلو بلا بذرة أو توزيعات أو ارتباطات أو إعداد قابل للإعادة.

59. It lets AI supply prices, demand, costs, tax, discount rates, formulas, ranges, distributions, correlations, weights, or final decisions.
    سمح للذكاء بتوريد مدخلات أو صيغ أو أوزان أو قرارات.

60. It treats a MOF/Etimad general form as a universal feasibility template or as controlling over exact competition documents.
    اعتبر نموذج المالية أو اعتماد العام قالب جدوى شاملًا أو مقدمًا على مستند المنافسة المحدد.

61. It uses an official form that is stale, superseded, from the wrong contract type, or not human-reviewed for the exact purpose.
    استخدم نموذجًا رسميًا قديمًا أو غير منطبق أو غير مراجع للغرض المحدد.

62. It fetches, crawls, scrapes, summarizes, copies, embeds, vectorizes, indexes, reconstructs, monitors, or trains on Aljdwa content without exact written permission.
    جلب أو نسخ أو فهرس أو لخص أو راقب محتوى منصة الجدوى دون إذن كتابي محدد.

63. It presents UNIDO, World Bank, IFC, Green Book, Aljdwa, MOF, or Etimad as project endorsement or Saudi legal authority outside exact scope.
    قدم مرجعًا منهجيًا أو رسميًا كاعتماد للمشروع أو سلطة خارج نطاقه.

64. Reports, frontend, charts, or AI recalculate feasibility truth or hide a blocked chapter in export.
    أعادت الواجهة أو التقارير أو الشارت أو الذكاء حساب الحقيقة أو أخفت فصلًا محجوبًا.

65. It claims abstract complete legal compliance without exact current documents and authorized Saudi professional sign-off.
    ادعى امتثالًا قانونيًا كاملًا دون مستندات حالية وتوقيع مختص مخول.
