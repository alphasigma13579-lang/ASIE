# EKB-02 — Source of Truth Matrix

| المجال | المصدر الأعلى | ما لا يجوز فعله |
|---|---|---|
| Program/remediation/release state | PROGRAM-CLOSE-10 + /EMERGENCY-RELEASE-FREEZE.json | استنتاج تفويض نشر أو شبكة أو Provider من وثيقة حزمة مؤرخة أو نجاح Workflow فقط. |
| Runtime execution | AAS Runtime Freeze | تعديل الملفات المجمدة مباشرة. |
| AI/intelligence | AIA-01 ثم AIA-02 | جعل AI يملك الأرقام أو القرار. |
| Contracts/Sockets/Modules | Canonical Terminology Register | إضافة معرف دون تحديث السجل والاختبارات. |
| API/output keys | Canonical API Output Register | إضافة Route أو Output دون التسجيل. |
| DIB | ACR-DIB-001 + DIB Live Plan + backend/dib_runtime.py | جعل Finance يقرأ raw UI/AI/files. |
| Finance | Finance Engine code + Decision/MC specs | اختراع أرقام أو منطق مالي خارج الكود. |
| Dashboard | Command Center implementation + Product Domain | عرض أقسام غير مفعلة كأنها حية. |
| Market data | Market Source Policy / Market Estimation | ادعاء أسعار إنترنت حية دون مصدر/تفعيل. |
| Prompting | EKB Prompt Policy | وضع مواصفات كاملة داخل البرومبت. |
