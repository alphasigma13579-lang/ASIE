# Pack F - Pipeline Responsibility Boundary

الهدف: إزالة التباس ملكية التنسيق الذي سببه الاسم القديم `build_overview()`.

النتيجة:

- المسار الإنتاجي يستدعي `execute_project_run_pipeline()` فقط.
- `ProjectRunWorkflow` ينشئ `ProjectRunEnvelope` المجمد ويملك run/snapshot identity وسياسة ترتيب العقود.
- المنفذ يتطلب Envelope مغلقًا وواجهة `ProjectRunDataAccess`.
- إنشاء `RunScopedModuleRuntime` واحد لكل تشغيل.
- تنفيذ ترتيب العقود وفق سياسة Workflow.
- طلب `snapshot.assemble.v1` مرة واحدة فقط بعد اكتمال sealed outputs.
- رفض نتيجة Pipeline إذا غيّرت `run_id` أو `snapshot_id`.
- إبقاء `build_overview()` كغلاف توافق للاختبارات القديمة فقط.

الملفات الأساسية: `project_run_workflow.py`, `asie_local_api.py`, `acceptance.py`, `test_aas_runtime.py`, `test_local_platform.py`.

