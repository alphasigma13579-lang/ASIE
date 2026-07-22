# ASIE PR-04 — حماية API والاستعادة والصحة التشغيلية

## الحالة والنطاق

- **الحالة:** منفذ ومتحقق محلياً.
- **المسارات:** `A2 + A3 + B1` فقط.
- **لا تغيير:** AAS Runtime Freeze v1.0، تسلسل Project Run، Snapshot Assembly، أو محتوى Snapshot / Report / Decision Pack.
- **الوصول الخارجي:** معطل؛ لا شبكة أو دفع أو API حكومي أو مزود AI أو مفاتيح.

## A2 — حدود API الخادمية

| الضبط | التنفيذ |
|---|---|
| التفويض | يبقى فحص المورد والمنظمة على الخادم؛ وأضيف فحص `platform.manage` لمسارات المشغل. لا تمنح الواجهة صلاحية. |
| أصل المتصفح | يسمح فقط بـ `http://127.0.0.1:5194` و`http://localhost:5194` عند وجود `Origin`. أي أصل آخر يرفض بـ `403 origin_not_allowed`. |
| الحمولة | JSON object فقط، وبحد أقصى `1 MiB`؛ تجاوز الحد يرد `413 request_body_too_large` قبل قراءة المحتوى. |
| المعدل | حاجز process-local لكل IP/verb/path: 120 طلباً/60 ثانية، ولا يحفظ محتوى الطلب. |
| الاستجابة | غلاف خطأ موحد يحوي `error`, `status`, `request_id`، ورأس `X-Request-Id`. لا يعاد stack trace. |
| رؤوس المتصفح | `no-store`, `nosniff`, `DENY`, `no-referrer`, CSP مقيد، Permissions-Policy، وCORS محلي مقيد. |

CSRF غير مطلوب لمسار Bearer token لأنه لا يستخدم cookie تلقائياً؛ ولن يقبل الإصدار الأول جلسات cookie من دون تصميم CSRF مستقل.

## A3 — البيانات والاستعادة

### جرد الحقول الحساسة وقرار التخزين

| الفئة | أمثلة | القرار |
|---|---|---|
| اعتماد | password، session token | password = PBKDF2-HMAC-SHA256، token الخام لا يخزن بل SHA-256؛ لا يظهر أي منهما في audit. |
| تعريف شخصي/منظمة | email، display name، organization name، membership | SQLite محلي محكوم بالمنظمة؛ يمنع التصدير الخارجي في هذا الإصدار. |
| بيانات مشروع/أدلة | inputs، datasets، evidence links، reviews | مقيدة بالمنظمة؛ Snapshot وما ينتج عنه ثابت وغير قابل للحذف الصامت. |
| تدقيق | actor، target، reason، correlation id | metadata-only؛ لا كلمات مرور أو tokens أو محتوى أدلة حساس. |

### النسخ والاستعادة

- الصيغة: `asie-local-backup.v1` (ZIP محلي يحوي نسخة SQLite متسقة و`manifest.json` مع SHA-256).
- الاستعادة تتحقق من قائمة المحتوى، صيغة الـmanifest، SHA-256، و`PRAGMA integrity_check` قبل استبدال ذري للملف الهدف.
- تحقق الاختبار من بقاء `snapshot.integrity_hash` نفسه بعد دورة backup/restore.
- **قرار التشفير الصريح:** لا تتوفر في بيئة الحزمة مكتبة تشفير موثوقة معتمدة، لذلك لا تدّعي النسخة تشفيراً. الأرشيف يحمل `not_embedded` و`external_export_allowed: false`. قبل أي وصول خارجي أو تصدير خارج الجهاز، يلزم ACR لاختيار وتطبيق AEAD/KMS معتمدين، ومفتاح خارج قاعدة البيانات، وسياسة تدوير واحتفاظ.
- الاحتفاظ التشغيلي المقترح محلياً: 7 نسخ يومية + 4 أسبوعية، وصول مشغل منصة فقط، وفحص checksum واستعادة دورية. لا يوجد تنفيذ جدولة أو نسخ خارجي في PR-04.

### سير بيانات المنظمة

`POST /api/organizations/{organization_id}/data-requests` يسجل طلب `export` أو `delete` بعد تفويض `organization.manage` وبـ legal basis إلزامي. حالته الابتدائية `queued_for_legal_review`، ولا ينفذ حذفاً تلقائياً ولا يغير Snapshot. هذا يحافظ على مسار قانوني ومراجع بدلاً من حذف غير قابل للمراجعة.

## B1 — التشغيل المحلي للقراءة فقط

| المسار | القيد | البيانات الحقيقية المعروضة |
|---|---|---|
| `GET /api/operations/health` | `platform.manage` | SQLite integrity، حالات فشل runs، حالة الأرشيف المحلي، incidents، وعدد أحداث التدقيق. |
| `GET /api/operations/audit-events?limit=…` | `platform.manage` | آخر 1–200 حدث تدقيق، للقراءة فقط. |
| `GET /api/architecture/runtime-status` | إسقاط عام محلي للقراءة فقط | لا يحتوي بيانات منظمة أو secrets؛ لا mutation. ينقل عرضه من تنقل العميل إلى المشغل في PR-05. |

لا تعرض هذه المسارات أسراراً، ولا تشغل اتصالاً خارجياً، ولا تحسب قراراً أو readiness خارج الـSnapshot.

## التحقق المنفذ

- `python -m unittest tests.test_pr04_security_recovery tests.test_identity_control_plane`: **8 tests passed**.
- `python -m unittest discover -s tests`: **138 tests passed**.
- `python -m compileall -q backend`: **passed**.
- `pnpm build`: **passed**.
- فحص SHA-256 للـFreeze Manifest: **0 mismatches**.
- يشمل: Origin مرفوض، رؤوس الاستجابة وrequest id، تفويض صحة التشغيل، حد الحمولة، طلب حذف محكوم، وbackup/restore مع سلامة Snapshot.

## النطاق المؤجل / Gate التالي

- تشفير archive معتمد ومفاتيح/KMS وجدولة نسخ واحتفاظ فعلي، قبل أي إتاحة خارجية.
- واجهة Admin Console وسجل الحوادث/الدعم القابلين للكتابة، إشعارات أو وصول دعم مقيد: `PR-05`.
- لا تغيير لملفات AAS Runtime المجمدة دون ACR معتمد.
