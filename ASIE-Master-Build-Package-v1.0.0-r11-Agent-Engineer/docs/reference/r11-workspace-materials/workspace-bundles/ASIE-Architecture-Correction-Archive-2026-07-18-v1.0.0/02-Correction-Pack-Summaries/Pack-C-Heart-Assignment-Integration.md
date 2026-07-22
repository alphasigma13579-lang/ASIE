# Pack C - Heart Assignment Integration

الهدف: ربط تعيين M1/M2/M3 بمصدر التنفيذ الفعلي بدل إبقائه وصفًا منفصلًا.

النتيجة:

- تسجيل القلوب M1/M2/M3 كواصفات Runtime.
- استدعاء `HeartController.assign_task()` قبل تشغيل Workflow.
- تثبيت القلب المختار في `source_module_id` لكل رسائل التشغيل.
- رفض أي مصدر Module لا يطابق جلسة التشغيل.

الملفات الأساسية: `heart_controller.py`, `aas_registry.py`, `module_runtime.py`, `asie_local_api.py`.

