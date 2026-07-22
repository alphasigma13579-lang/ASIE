# Master Index

## الفهرس الرئيسي

## Read Order for KIMI

## ترتيب القراءة لـ KIMI

1. `README.md` / تعريف الحزمة.
2. `00-index/01-Build-Scope-and-Assumptions.md` / نطاق البناء والافتراضات.
3. `01-core/Component-Responsibility-Matrix-Full.md` / مصفوفة مسؤوليات المكونات.
4. `01-core/Data-and-Authority-Ownership.md` / ملكية البيانات والسلطة.
5. `02-contracts/Socket-Contract-Catalog-Full.md` / كتالوج عقود السوكيت.
6. `02-contracts/Message-Type-Catalog-Full.md` / كتالوج أنواع الرسائل.
7. `03-modules/Module-Cards-Full.md` / بطاقات الموديولات.
8. `03-modules/Smart-Site-and-Dynamic-Charts.md` / الموقع الذكي والشارتات الديناميكية.
9. `03-modules/Product-Analytics-Adapters.md` / موصلات تحليلات المنتج.
10. `03-modules/External-Intelligence-Source-Framework.md` / إطار مصادر الذكاء الخارجية.
11. `03-modules/External-Source-Adapter-Catalog.md` / كتالوج موصلات المصادر الخارجية.
12. `03-modules/Source-Legal-Access-Policy.md` / سياسة الوصول القانوني للمصادر.
13. `03-modules/Open-Government-Data-Integration-and-Legal-Access.md` / الربط النظامي بالبيانات الحكومية المفتوحة.
14. `03-modules/Strict-Open-Data-Only-Source-Profile.md` / ملف التشغيل الصارم للبيانات المفتوحة فقط.
15. `03-modules/Official-Strategy-Reference-and-Original-Writing-Policy.md` / سياسة المراجع الاستراتيجية والكتابة الأصلية.
16. `03-modules/Source-Priority-Freshness-Fallback-Policy.md` / سياسة أولوية المصادر وحداثتها وبدائل الفشل.
17. `03-modules/Identity-Security-and-Human-Verification.md` / أمن الهوية والتحقق من الإنسان.
18. `03-modules/Notification-and-Admin-Operations-Center.md` / مركز التنبيهات وعمليات الإدارة.
19. `03-modules/Sector-Taxonomy-and-Investment-Signals.md` / تصنيف القطاعات وإشارات الاستثمار.
20. `03-modules/Project-Intelligence-Dashboard-and-Visual-Outputs.md` / لوحة ذكاء المشروع والمخرجات البصرية.
21. `03-modules/Professional-Feasibility-Study-and-Procurement-Reference-Framework.md` / إطار دراسة الجدوى الاحترافية ومراجع المنافسات.
22. `04-flows/Execution-Flows.md` / تدفقات التنفيذ.
23. `05-tests/Acceptance-Test-Catalog-Full.md` / كتالوج اختبارات القبول.
24. `06-kimi/KIMI-Build-Sequencing-Plan-Full.md` / خطة تسلسل بناء KIMI.
25. `06-kimi/KIMI-Project-Dashboard-Build-Prompt.md` / أمر بناء لوحة المشروع.

## Completion Rule

## قاعدة الاكتمال

KIMI must not implement code until it can answer:

يمنع KIMI من كتابة الكود حتى يستطيع الإجابة عن:

- Which component owns each responsibility?
- من يملك كل مسؤولية؟

- Which socket contract authorizes each interaction?
- أي عقد سوكيت يسمح بكل تفاعل؟

- Which message type carries each payload?
- أي نوع رسالة يحمل كل Payload؟

- Which test proves compliance?
- أي اختبار يثبت الالتزام؟

- Which chart owner produces each dynamic dataset?
- أي موديول مالك ينتج Dataset كل شارت ديناميكي؟

- Which output envelope proves every visible number and decision?
- أي غلاف مخرج يثبت كل رقم وقرار ظاهر؟

- Which feasibility profile, chapter gate, reconciliation, and official procurement reference controls the output?
- ما ملف عمق دراسة الجدوى وبوابة الفصل والمطابقة ومرجع المشتريات الرسمي الذي يضبط المخرج؟
