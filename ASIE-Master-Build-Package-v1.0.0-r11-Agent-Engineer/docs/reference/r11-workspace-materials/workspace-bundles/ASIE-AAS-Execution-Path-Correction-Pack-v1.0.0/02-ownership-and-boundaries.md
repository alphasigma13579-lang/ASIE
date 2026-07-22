# ملكية الحقائق وحدود الوحدات

| الحقيقة | المالك الوحيد |
|---|---|
| المدخلات الأصلية | Project Input Store |
| الحسابات والأرقام | Finance Runtime |
| الأدلة والتغطية | Evidence Runtime |
| المؤشرات القطاعية | Sector Runtime |
| الحكم السيادي | Decision Runtime |
| سجل المخاطر | Risk Runtime |
| خطة التنفيذ | Execution Runtime |
| التجميع والتجميد | Snapshot Assembly |
| التقرير | Report Projection |
| حزمة القرار | Decision Pack Projection |
| تعيين القلب | Heart Controller |
| توجيه الرسائل | Bus Controller |
| صحة العقد | Socket Contract Layer |

## حدود ثابتة

- React يعرض ويرسل فقط.
- API يتحقق ويوجه، ولا يحسب.
- Kernel لا يعاد إقلاعه مع كل Run.
- Heart Controller وحده يختار القلب.
- Registry لا يدير القلوب.
- Bus Controller يملك admission/routing.
- Socket Layer يملك contract validation.
- Module Runtime يملك دورة حياة الوحدات.
- Security Audit مسار جانبي.
- AI Integration Shell لا يملك أرقامًا أو حكمًا.
