# ASIE PR-01 — سجل تنفيذ الهوية وطبقة التحكم

## الحالة والنطاق

- **الحالة:** منفذ ومتحقق محلياً.
- **المسار:** `A1 + B0` فقط.
- **لا تغيير:** AAS Runtime Freeze v1.0، ترتيب Project Run، Snapshot Assembly، أو إسقاطات Snapshot.
- **الوصول الخارجي:** معطل. لا شبكة خارجية أو API حكومي أو دفع أو مزود AI أو مفتاح.

## الحقيقة الخلفية المنفذة

| النطاق | سجلات الحقيقة | الثابت الأمني |
|---|---|---|
| الهوية | `users`, `sessions` | كلمة المرور تحفظ كـ PBKDF2-HMAC-SHA256 فقط؛ token الجلسة الخام لا يحفظ، بل hash؛ الجلسة قابلة للإبطال وتنتهي بعد 8 ساعات. |
| المستأجر | `organizations`, `memberships` | العضوية هي مصدر دور المنظمة؛ user+organization فريد؛ المنع افتراضي. |
| تدقيق الأمان | `security_audit_events` | append-only وmetadata-only: لا كلمات مرور أو tokens أو محتوى أدلة. |
| التحكم التجاري المحلي | `organization_entitlements`, `usage_meters`, `local_invoices` | سجلات محلية فقط؛ entitlement لا يغير Snapshot أو الحكم أو المخاطر. |
| البيانات الموجودة | `projects.organization_id`, `datasets.organization_id` | رُحّلت السجلات القديمة إلى `org_local_legacy` من دون تعديل Snapshot أو report. |

## الأدوار والتفويض

الأدوار الثابتة: `platform_admin`, `platform_support`, `organization_owner`, `organization_admin`, `analyst`, `reviewer`, `viewer`.

التفويض ينفذ في الخادم عبر session bearer token وعضوية نطاق المورد. أي قراءة مباشرة لمسار مشروع أو run أو snapshot تتحقق من المنظمة المالكة قبل قراءة البيانات. لا يمنح إخفاء زر في المتصفح أي صلاحية.

## واجهات API المحلية الجديدة

| المسار | الوظيفة | القيد |
|---|---|---|
| `POST /api/auth/local-bootstrap` | إنشاء أول مدير منصة ومنظمة محلية وOwner وجلسة | مرة واحدة فقط؛ محلياً؛ لا يسجل المستخدمين للعامة. |
| `POST /api/auth/login` | إنشاء جلسة محلية | كلمة مرور صحيحة فقط؛ يعيد Bearer token. |
| `POST /api/auth/logout` | إبطال الجلسة الحالية | يتطلب Bearer token. |
| `GET /api/auth/me` | عرض عضويات المستخدم الحالي | يتطلب Bearer token. |
| `POST /api/organizations` | إنشاء منظمة مع requester كـ Owner | يتطلب جلسة. |
| `POST /api/organizations/{organization_id}/memberships` | إضافة/تعديل عضوية | Owner/Admin للمنظمة على الخادم. |

تتطلب جميع مسارات API غير العامة جلسة. قائمة المشاريع تتطلب `X-ASIE-Organization-Id` وعضوية صالحة؛ إنشاء المشروع يفرض النطاق نفسه في الخادم ولا يثق بقيمة جسم الطلب. مسارات المشروع والـ run والـ snapshot تتحقق من ملكية المنظمة قبل القراءة أو التغيير.

**انتقال التوافق المحلي:** ما دامت قاعدة البيانات لا تحتوي أي حساب، يبقى المسار المحلي التاريخي محصوراً في `org_local_legacy` لكي لا تنكسر الواجهة الحالية قبل PR-02. لا توجد في هذه الحالة منظمة ثانية أو وصول شبكي خارجي. أول `local-bootstrap` يعطل هذا المسار فوراً ويحوّل كل API غير عام إلى جلسة Bearer وتفويض عضوية خادمي.

## نطاق مؤجل

- واجهة تسجيل الدخول وإدارة المنظمات، ودعوات البريد والاستعادة الكاملة وواجهات admin.
- تشفير الحقول الحساسة في الراحة، backup/restore drill، rate limits، CSRF/CSP/CORS، وsecurity headers: `PR-04`.
- payment gateway، بطاقات، ضرائب، إشعارات خارجية، SSO/SAML، role builder، API عام، AI أو أي تكامل خارجي.
- منح دعم مؤقتة ومسببة للوصول إلى محتوى منظمة (`support grant`)؛ لا يمنح دور الدعم وصولاً مباشراً حالياً.

## أدلة التحقق

- `python -m unittest tests.test_identity_control_plane tests.test_local_platform`: **77 tests passed**.
- `python -m compileall -q backend`: **passed**.
- فحص SHA-256 للـ Freeze Manifest: **0 mismatches**.

## بوابة الحزمة التالية

لا يبدأ PR-02 أو PR-03 قبل قرار مستقل. أول عمل أمني إلزامي لاحق هو إكمال `PR-A2 + PR-A3` قبل أي وصول خارجي؛ لا تكفي واجهات المنتج أو الهوية المحلية لفتح ذلك الوصول.
