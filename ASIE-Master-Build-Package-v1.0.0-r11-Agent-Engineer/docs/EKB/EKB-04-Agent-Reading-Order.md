# EKB-04 — Agent Reading Order

| نوع المهمة | يجب أن يقرأ أولًا | ثم يقرأ | ممنوع |
|---|---|---|---|
| هدف هندسي حقيقي: بناء أو تغيير أو مراجعة أو تحقيق أو اختبار أو نشر | EKB-09 Goal Planning and Truthful Engineering Contract | الخطة المعتمدة، المجال المتأثر، والعقود ذات الصلة | بدء التنفيذ بلا خطة وهدف نشط، أو الموافقة بلا دليل، أو وصف حالة بلا إثبات. |
| Runtime / AAS | AAS Freeze | Canonical Terminology + affected code | تعديل frozen files دون ACR. |
| AI / Sanad / AIA | AIA-01 | AIA-02 + domain file | تفعيل AI Provider أو network fetch. |
| إصلاح توجيه السوق / الموقع / Pre-Run / التفسير | AIA-01 + AIA-02 النهائي + [تدقيق المسارات](../ASIE-AIA-PARALLEL-ROUTING-AUDIT-2026-09-23.md) | [ACR-AIA-ROUTING-REMEDIATION المقترح](../ACR-AIA-ROUTING-REMEDIATION-2026-09-27.md) + خطة بيتا المالك + سلطة FC20-12 والتجميد واعتماديات FC20-08/09/11 + ملكية ACR-AIA-09/10 وامتداد ACR-FC20-10 | التنفيذ من مقترح غير معتمد، أو استدعاء مزود/كتابة سياق تتجاوز AAS، أو إنشاء بوابة/Runtime أو سوكت AI موازٍ، أو تجاوز الاعتماديات أو اعتبار موافقة المسودة تصريح بناء. |
| فصل نطاق إصلاح التوجيه داخل البرنامج | EKB-09 + PROGRAM-CLOSE-10 + FOUNDATION والسجل الآلي | [طلب فصل FC20-12 المقترح](../FC20-12-ROUTING-SCOPE-CHANGE-2026-09-27.md) + ACR التصحيح + اعتمادياته والطلبات المالكة | اعتبار فصل مقترح تصريح تنفيذ، تعديل حالات الحزم أو اعتمادياتها ضمنيًا، أو إعلان اكتمال الأب من شريحة. |
| DIB | ACR-DIB-001 | DIB Live Plan + DIB domain files | Finance من raw inputs. |
| API | Canonical API Register | `src/api.ts`, backend handler, tests | Route غير مسجل. |
| Finance | Finance Engine domain | code/tests + MC domain | AI يولد أرقامًا نهائية. |
| Dashboard | Dashboard Command Center domain | `src/CommandCenter.tsx`, API register | بيانات وهمية كأنها حية. |
| واجهة العميل / التعريب / التقارير / التصدير | EKB-08 Customer Language and Presentation Contract | المسار المتأثر، طبقة العرض، الاختبارات، والتصدير | عرض رمز داخلي أو نص غير مترجم أو تشخيص تقني للعميل. |
| Market | Market Intelligence + Source Policy | DIB item state | أسعار بلا مصادر أو اعتماد. |
| Security | Security/Tenant domain | tests + API handlers | فتح endpoints دون صلاحيات. |
| Repository Surgery / Cleanup | PROGRAM-CLOSE-10-EMERGENCY-REMEDIATION-CONSOLIDATION-AND-REBASELINE-2026-07-29.md + EKB-06 Repository Surgery Inventory | EKB-07 Quarantine Map + AGENTS archive lockdown | نسخ أو دمج ملفات archive/reference في المسارات الحية، أو الحذف دون PR مستقل ودليل. |
| Planning | EKB-00 + Source Matrix | relevant domain docs | خلط المنفذ بالمخطط. |
| Prompt writing | Prompt Policy | prompt templates | وضع المعرفة طويلة الأجل في البرومبت. |
