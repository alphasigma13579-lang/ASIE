# ASIE — AAS Execution Path Correction Pack v1.0.0

## الغرض

هذه الحزمة مخصصة لتصحيح وتثبيت **مسار تشغيل المشروع الكامل** داخل منصة ASIE وفق معمارية AAS، من React UI حتى Immutable Snapshot، ثم إنشاء Report Projection وDecision Pack Projection بصورة مستقلة.

## النطاق

هذه الحزمة لا تضيف ميزات منتجية جديدة، ولا مزودات AI، ولا مفاتيح، ولا جلبًا خارجيًا، ولا منافذ جديدة.

المنافذ المسموحة فقط:

- Frontend: `5194`
- API: `8794`

## القاعدة العليا

```text
React
→ Python API
→ ASIE Kernel
→ Heart Controller
→ M1/M2/M3
→ Bus Controller
→ ASIE System Bus
→ Socket Contract Layer
→ Module Runtime
→ Sealed Module Outputs
→ Snapshot Assembly
→ Atomic Immutable Snapshot
→ Report Projection + Decision Pack Projection
```

## ممنوعات غير قابلة للتفاوض

- لا حسابات داخل React.
- لا استدعاء مباشر من API إلى أي Engine.
- لا Direct Module Calls.
- لا استخدام `aas.kernel.boot.v1` لتشغيل مشروع.
- لا إعادة حساب عند قراءة Report أو Decision Pack.
- لا ربط `Report → Decision Pack`.
- لا Snapshot جزئي.
- لا Security Audit كمصدر استجابة للمستخدم.
- لا AI يملك الأرقام أو الحكم أو تفعيل المصادر.
