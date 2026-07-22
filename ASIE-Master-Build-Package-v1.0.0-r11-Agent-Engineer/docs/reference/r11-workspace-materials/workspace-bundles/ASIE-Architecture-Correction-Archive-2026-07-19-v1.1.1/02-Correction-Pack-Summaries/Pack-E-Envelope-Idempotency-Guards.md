# Pack E - Envelope and Idempotency Guards

الهدف: ربط كل رسائل التشغيل بظرف مغلق واحد.

النتيجة:

- إضافة `operation_id`, `idempotency_key`, و`input_hash` إلى BusMessage.
- إلزام Bus Controller وSocket Contract Layer بهذه الحقول.
- رفض اختلاف هوية العملية أو مفتاح التكرار أو بصمة المدخلات داخل RunScopedModuleRuntime.
- تمرير الظرف نفسه حتى `snapshot.assemble.v1` وإسقاطات التقرير وDecision Pack.

الملفات الأساسية: `system_bus.py`, `bus_controller.py`, `socket_contracts.py`, `module_runtime.py`, `asie_local_api.py`, `architecture_status.py`.

