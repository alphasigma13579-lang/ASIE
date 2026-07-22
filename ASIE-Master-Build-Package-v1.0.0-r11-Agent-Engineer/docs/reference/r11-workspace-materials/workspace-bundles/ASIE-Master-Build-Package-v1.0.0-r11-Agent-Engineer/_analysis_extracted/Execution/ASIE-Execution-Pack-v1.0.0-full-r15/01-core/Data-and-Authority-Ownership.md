# Data and Authority Ownership

## ملكية البيانات والسلطة

| Data / Authority | Arabic | Owner | Consumers |
| --- | --- | --- | --- |
| Identity / الهوية | هوية المستخدم | `User / Auth Module` | All modules via claims / كل الموديولات عبر Claims |
| Entitlements / الاستحقاقات | صلاحيات الخطة | `Subscription / Usage Module` | AI, Reports, Wizard, Admin |
| Project Context / سياق المشروع | بيانات المشروع | `Project Wizard Module` | Market, Finance, AI, Decision |
| Market Evidence / أدلة السوق | أدلة السوق | `Market Intelligence Module` | Finance, AI, Decision, Reports |
| Price Samples / عينات الأسعار | الأسعار | `Market Intelligence Module` | Finance |
| Deterministic Finance / التمويل الحتمي | الحسابات المالية | `Finance Engine Module` | Decision, Reports, AI summary |
| Advisory Text / النص الاستشاري | الشرح والتوصيات | `AI Advisory Module` | Decision, Reports, UI |
| Final Decision / القرار النهائي | قرار المجلس | `Decision Council Module` | Reports, UI |
| Audit Events / أحداث التدقيق | السجلات | `Audit / Observability Module` | Admin |
| Feature Flags / أعلام الخصائص | التحكم بالخصائص | `Admin Module` | Runtime policy checks |

## Authority Rule

## قاعدة السلطة

Consumers can read owner outputs through contracts, but cannot mutate owner data.

المستهلكون يقرؤون مخرجات المالك عبر العقود، لكن لا يغيرون بيانات المالك.

## Rejection Rule

## قاعدة الرفض

Any data without owner, source, schema, or audit path is rejected.

أي بيانات بلا مالك أو مصدر أو Schema أو مسار تدقيق ترفض.

