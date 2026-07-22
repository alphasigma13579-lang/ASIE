# حزمة الانتقال إلى مهمة ASIE الجديدة

الإصدار: `v1.0.0`

تاريخ الإعداد: `2026-07-19`

خط الأساس: `AAS Runtime Freeze v1.0`

وقت التجميد: `2026-07-19T00:22:00+03:00` بتوقيت `Asia/Riyadh`

ابدأ بقراءة `01-Work-Plan/ASIE-Post-Freeze-Work-Plan-2026-07-19.md` كاملًا، ثم نفذ `PF-00` و`PF-01` فقط في المهمة التالية.

## المحتويات

- `01-Work-Plan`: خطة العمل المفصلة وبصمتها المستقلة.
- `02-Freeze-Baseline`: Freeze Manifest ومخطط المعمارية.
- `03-Change-Control`: نموذج Architectural Change Request.
- `START-NEXT-TASK.md`: نص جاهز لبدء المهمة التالية.
- `HANDOFF-MANIFEST.json`: فهرس الملفات وبصماتها.
- `SHA256SUMS.txt`: بصمات SHA-256 لجميع محتويات الحزمة.

## القيود الثابتة

- Frontend على `5194` فقط وAPI على `8794` فقط.
- لا اتصال خارجي أو مفاتيح أو Government APIs أو AI Provider.
- Snapshot immutable.
- Report وDecision Pack وUI إسقاطات من Snapshot فقط.
- لا تعديل لملفات Runtime المجمدة دون ACR معتمد.

