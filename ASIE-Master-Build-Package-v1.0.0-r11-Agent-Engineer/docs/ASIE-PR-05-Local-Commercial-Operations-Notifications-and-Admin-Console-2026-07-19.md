# ASIE PR-05 — العمليات التجارية المحلية والإشعارات ولوحة المشغّل

## الحالة والنطاق

- **الحالة:** منفذ ومتحقق محلياً.
- **المسارات:** `B2 + B3 + B4` فقط.
- **الخارج:** معطل بالكامل: لا تحصيل أو بوابة دفع أو ضريبة أو بطاقة أو بريد أو SMS أو WhatsApp أو AI أو شبكة خارجية.
- **الحقيقة المحكومة:** لا تغير الاشتراكات أو الفواتير أو الإشعارات أي Snapshot أو Report أو Decision Pack أو حكم.

## B2 — سجلات العمليات التجارية المحلية

| السجل | السلوك |
|---|---|
| `organization_entitlements` | الخطة والحالة والحصص لكل منظمة. الحالات المسموحة: `trial`, `active`, `grace`, `suspended`, `cancelled`. |
| `subscription_change_events` | حدث append-only لكل تعديل يدوي مع الحالة السابقة والسبب والمشغل والوقت. |
| `usage_meters` + `usage_summary()` | تعريفات استخدام قابلة للمراجعة مشتقة من سجلات فعلية: المشاريع، الأدلة، وعمليات التشغيل. |
| `local_invoices` | دفتر فواتير محلي فقط؛ الفاتورة الجديدة `issued_uncollected` ولا تعني دفعاً. |

المسارات السلطوية للمشغل:

- `GET /api/admin/overview`
- `GET/POST /api/admin/organizations/{organization_id}/subscription`
- `POST /api/admin/organizations/{organization_id}/invoices`

كل تغيير يتطلب `platform.manage` أو `subscription.manage` من الخادم، ويسجل audit. لا تؤدي حالة اشتراك إلى حجب حقيقة قرار أو Snapshot.

## B3 — الإشعارات والدعم

- مركز الإشعارات داخل المنتج يسجل template/reference/delivery state فقط، ولا يخزن محتوى Snapshot.
- القوالب المسموحة: `review_requested`, `review_recorded`, `subscription_changed`, `support_updated`.
- يسجل إنشاء review على Snapshot إشعار `review_recorded` داخل المنظمة نفسها.
- `POST /api/admin/organizations/{organization_id}/notifications` يتطلب مشغل منصة، ويعيد دائماً `external_delivery_enabled: false`.
- توجد بنية `support_threads` المقيدة بمرجع منظمة وSnapshot؛ الواجهة والمراسلات القابلة للكتابة مؤجلة إلى PR-06/قرار وصول الدعم المقيد. لا يكشف أي مسار محتوى Snapshot عبر المنظمات.

## B4 — لوحة المشغّل

تتوفر عند `/#admin` كمساحة منفصلة عن رحلة العميل. تطلب تسجيل دخول المشغّل المحلي ثم تقرأ `/api/admin/overview`، وتعرض فقط سجلات backend السلطوية:

`نظرة عامة → المنظمات والاشتراكات → المستخدمون والأدوار → دفتر الفواتير المحلي → الصحة المحلية`.

تظهر حالة دفع/إرسال خارجي معطلة صراحة، وحالات الفراغ لا تدعي وجود بيانات. لا تتضمن أي قيمة قرار أو readiness محسوبة في React.

## القبول والتحقق

- `tests/test_pr05_control_plane.py`: اشتراك محلي مدقق، فاتورة غير محصلة، إشعار in-app فقط، وauthorization للوحة المشغل.
- فحص DOM المحلي لواجهة الدخول إلى `/#admin`: عناصر الدخول والرسالة المقيدة ظاهرة.
- `python -m unittest discover -s tests`: **141 tests passed**.
- `python -m compileall -q backend`: **passed**.
- `pnpm build`: **passed**.
- فحص SHA-256 للـFreeze Manifest: **0 mismatches**.

## النطاق المؤجل

- أي تحصيل أو بوابة دفع أو ضريبة أو بيانات بطاقات.
- إرسال خارجي أو قنوات مراسلة.
- منح دعم مؤقت ومسبب لعرض محتوى منظمة أو Snapshot.
- إدارة واجهية كاملة لتعديل الاشتراك وإصدار الفواتير؛ طبقة API والسجل السلطوي موجودان، وتبقى هذه الضوابط مقصورة على API المشغّل حتى تصميم workflow الإداري الكامل.
