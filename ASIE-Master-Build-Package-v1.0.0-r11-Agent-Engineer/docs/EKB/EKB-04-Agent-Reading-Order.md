# EKB-04 — Agent Reading Order

| نوع المهمة | يجب أن يقرأ أولًا | ثم يقرأ | ممنوع |
|---|---|---|---|
| Runtime / AAS | AAS Freeze | Canonical Terminology + affected code | تعديل frozen files دون ACR. |
| AI / Sanad / AIA | AIA-01 | AIA-02 + domain file | تفعيل AI Provider أو network fetch. |
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
