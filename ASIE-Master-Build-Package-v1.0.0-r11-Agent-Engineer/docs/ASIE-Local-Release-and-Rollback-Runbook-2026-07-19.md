# ASIE — إجراء الإصدار والرجوع المحلي

## الغرض والحدود

هذا الإجراء خاص ببيئة التطوير المحلية فقط (`frontend: 5194`, `API: 8794`). لا ينشئ نشرًا أو tag أو اتصالاً خارجياً، ولا يفتح أي مزود.

## فحص ما قبل التشغيل

1. شغّل `python -m unittest discover -s tests`.
2. شغّل `python -m compileall -q backend` و`pnpm build`.
3. تحقق من SHA-256 لملفات AAS Runtime عبر `docs/ASIE-AAS-Runtime-Freeze-Manifest-v1.0.json`.
4. تأكد من بقاء `external_fetch_enabled=false` وAI `DISABLED/DENY_ALL` وعدم وجود دفع أو إرسال خارجي.
5. خذ نسخة محلية عبر `create_local_backup` وتحقق منها قبل أي تغيير قاعدة بيانات.

## رجوع محلي لقاعدة البيانات

1. أوقف API المحلي فقط.
2. استدعِ `restore_local_backup(archive_path, target_database_path)` على نسخة backup محلية معلومة المصدر.
3. يجب أن ينجح manifest checksum و`PRAGMA integrity_check` قبل الاستبدال الذري.
4. شغّل API محلياً وأعد فحص صحة التشغيل.
5. قارن `snapshot.integrity_hash` لعينة موثقة بعد الاستعادة؛ لا تحرر Snapshot أو Report أو Decision Pack لإصلاح اختلاف.

## رجوع الشيفرة

لا ينفذ هذا السجل أوامر Git مدمرة. الرجوع عن الشيفرة يحتاج نقطة مراجعة/commit معروفاً وموافقة منفصلة؛ لا تستخدم `reset --hard` ضد مساحة عمل قد تحتوي تعديلات المستخدم.

## دليل التحقق الحالي

- الاختبارات الكاملة: **146 passed**.
- Freeze manifest: **0 mismatches**.
- لا يمثل ذلك إذناً لوصول خارجي أو تجربة عميل.
