# أرشيف تصحيح معمارية ASIE

الإصدار: `v1.1.0 - AAS Runtime Freeze v1.0`

تاريخ الحفظ: `2026-07-19`

هذا الأرشيف يجمع حزمة المرجع، والخطط والمخططات، وملخصات حزم التصحيح A-G، ووثائق Freeze وACR، ونسخة من ملفات التنفيذ المرتبطة بمسار Project Run، واختبارات التحقق النهائية.

## المحتويات

- `00-Reference-Pack`: حزمة مسارات التنفيذ المرجعية كاملة من 00 إلى 08 مع `MANIFEST.json` والبصمة الأصلية.
- `01-Plans-and-Maps`: خطة التصحيح التراكمية ومخطط المعمارية ذي الصفحة الواحدة.
- `02-Correction-Pack-Summaries`: وصف مستقل لكل حزمة تصحيح نُفذت، بما فيها Pack G الخاصة بالتجميد.
- `03-Implementation/backend`: نسخة حفظ من ملفات مسار التنفيذ والملكية والإسقاطات ذات الصلة.
- `04-Verification/tests`: اختبارات AAS والمنصة المحلية المستخدمة في التحقق.
- `VERIFICATION-RESULTS.md`: نتيجة التحقق النهائية والقيود الثابتة.
- `SHA256SUMS.txt`: بصمة SHA-256 لكل ملف داخل الأرشيف.
- `ARCHIVE-MANIFEST.json`: فهرس آلي للملفات والأحجام والبصمات.

## المسار المعماري المحفوظ

`Project Run HTTP -> ProjectRunWorkflow -> ProjectRunEnvelope -> execute_project_run_pipeline -> RunScopedModuleRuntime -> Bus/Socket -> sealed outputs -> session.assemble -> Immutable Snapshot -> Report/Decision Pack/UI projections`

`build_overview()` موجود في النسخة المحفوظة كغلاف توافق لاختبارات parity القديمة فقط، ولا يستخدمه مسار HTTP/Project Run الإنتاجي.

الحالة النهائية: `AAS Runtime Freeze v1.0`. أي تغيير للأسطح المجمدة يتطلب Architectural Change Request رسميًا ويجب أن يحدث Freeze Manifest واختباراته.
