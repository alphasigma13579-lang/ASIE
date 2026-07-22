# Prompt تنفيذي للوكيل/المهندس

نفّذ حزمة **ASIE AAS Execution Path Correction Pack v1.0.0** فقط.

## الهدف

تصحيح مسار تشغيل المشروع ليصبح:

```text
React → API → Kernel → Heart Controller → Heart
→ Bus Controller → System Bus → Socket Layer
→ Project Run Workflow → Runtime Modules
→ Sealed Outputs → Snapshot Assembly
→ Atomic Immutable Snapshot
→ Report + Decision Pack Projections
```

## القيود

- لا Features جديدة.
- لا Providers.
- لا API keys.
- لا External Fetch.
- لا منافذ جديدة.
- لا تغييرات UI غير لازمة.
- لا كسر للاختبارات الحالية.
- لا إعادة كتابة محركات سليمة.
- استخدم adapters/wrappers عند الحاجة.
- نفذ التغييرات جراحيًا.
- أضف parity tests.
- أضف architectural rejection tests.
- حافظ على backward compatibility ما لم يتعارض مع الدستور المعماري.

## تسليم إلزامي

1. تقرير قبل التنفيذ.
2. قائمة الملفات التي ستتغير.
3. تنفيذ مرحلة واحدة في كل مرة.
4. اختبارات بعد كل مرحلة.
5. تقرير نهائي يوضح:
   - ما نُقل.
   - ما بقي.
   - نتائج الاختبارات.
   - أي bypass تم إزالته.
   - أي contract تم فصله.
