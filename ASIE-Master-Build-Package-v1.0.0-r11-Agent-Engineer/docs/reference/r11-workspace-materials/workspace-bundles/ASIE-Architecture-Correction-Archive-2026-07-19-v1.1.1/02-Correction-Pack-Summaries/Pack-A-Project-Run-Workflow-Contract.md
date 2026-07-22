# Pack A - Project Run Workflow Contract

الهدف: جعل `ProjectRunWorkflow` نقطة الدخول المالكة لتشغيل المشروع بدل التنسيق المباشر من API.

النتيجة:

- تسجيل عقود وSocket وModule لمسار Project Run.
- تمرير طلب التشغيل عبر Bus/Socket/ModuleRuntime.
- تطبيق idempotency على مستوى Workflow.
- حفظ Snapshot وReport بعد اكتمال المسار فقط.

الملفات الأساسية: `project_run_workflow.py`, `aas_registry.py`, `module_runtime.py`, `asie_local_api.py`.

