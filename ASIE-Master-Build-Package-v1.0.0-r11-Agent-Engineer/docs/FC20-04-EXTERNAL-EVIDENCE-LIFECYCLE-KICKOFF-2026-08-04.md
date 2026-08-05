# FC20-04 — External Evidence Persistence, Review, and Job Lifecycle

- **الحالة:** `COMPLETE`
- **الأولوية:** `P0`
- **المالك:** Project Owner
- **الإصدار:** 1.0
- **تاريخ الفتح:** 2026-08-04
- **نقطة الانطلاق:** `main@e63f1039ad5a2a1278f0c43a184bbfe4a4862125`
- **مصدر الحقيقة:** `/FOUNDATION-COMPLETE-20.json`
- **قرار الإصدار:** `BLOCK`
- **صلاحية الشبكة/المزودات:** غير ممنوحة

## الهدف

بناء دورة حياة أدلة خارجية متعددة المستأجرين تفصل الاكتشاف غير الموثوق عن الأدلة المراجعة والمعتمدة، مع jobs غير متزامنة idempotent، provenance كامل، وإخفاق آمن يمنع أي payload غير مراجع من دخول approved intelligence context.

## التتبع

`Outcome -> FC20-04 scope -> persistence/job contracts -> tenant authorization -> tests -> completion evidence -> release gate`

السلفان FC20-02 وFC20-03 في حالة `COMPLETE`. فتح هذه الحزمة لا يفعّل شبكة، ولا يسمح باستدعاء مزود، ولا يكتب vectors إلى Pinecone.

## P0 — شريحة التنفيذ الأولى

1. عقود ثابتة لـ`DiscoveryCandidate` و`ExtractionJob` و`EvidenceArtifact` و`EvidenceReview` و`SupersessionRecord`.
2. مخزن معاملات يحفظ hash وsource/provenance وfreshness وtenant/project ownership وحالة المراجعة.
3. lifecycle واضح: `queued -> running -> partial|succeeded|failed|cancelled` مع idempotency key وعدم ازدواج الأدلة.
4. authorization خادمي المصدر لكل read/write/review/cancel؛ لا ثقة في tenant أو project من client.
5. بوابة تمنع `candidate` و`review_required` و`rejected` و`stale` و`revoked` من approved context.
6. audit منقح لكل انتقال وفشل، دون payload خام أو أسرار.

## P1

- اكتملت داخل FC20-04: cancellation، result/failure accounting المحدود، supersession، revocation، freshness invalidation، والعزل الكامل لسجل التدقيق.
- تبقى retries والحصص الخاصة باستدعاءات المزود محكومة بعقود FC20-03 ولا تُكرر هنا.
- تبقى pagination التشغيلية، job observability، retention، backup، وincident exercises ضمن FC20-15 قبل أي تشغيل إنتاجي.
- هذا الفصل في الملكية لا يفتح endpoint أو worker ولا يمنح صلاحية شبكة أو مزود.

## قائمة الملفات الجراحية المسموحة

- وحدات جديدة تحت `backend/` خاصة بـexternal evidence persistence وjob lifecycle.
- migrations جديدة غير مدمرة للجداول الخاصة بالحزمة.
- اختبارات FC20-04 الجديدة تحت `tests/`.
- وثائق FC20-04 وEKB.
- `FOUNDATION-COMPLETE-20.json` عند تسجيل الأدلة.
- workflow CI غير شبكي إذا لزم.

## denylist

- `backend/aas_kernel.py`
- `backend/aas_registry.py`
- `backend/heart_controller.py`
- `backend/bus_controller.py`
- `backend/system_bus.py`
- `backend/socket_contracts.py`
- `backend/module_runtime.py`
- `backend/project_run_workflow.py`
- `backend/snapshot_assembly.py`
- `backend/runtime_freeze.py`
- Finance وDecision Council.
- تفعيل الشبكة أو المزودات أو public signup/release.
- كتابة vectors أو تمرير payload غير مراجع إلى أي سياق معتمد.

## معايير القبول

- same-tenant allow وcross-tenant deny مثبتان لكل object وjob action.
- replay لنفس idempotency key لا ينشئ job أو evidence مكررًا.
- stale/revoked/غير مراجع لا يدخل approved context.
- partial provider failure لا ينشئ evidence معتمدًا.
- audit failure ظاهر ويفشل مغلقًا.
- cancellation لا يترك حالة نجاح أو approval جزئي.
- hashes وprovenance وsupersession قابلة للتتبع وإعادة الاختبار.
- لا أسرار أو payload خام في logs أو artifacts.
- الملفات المجمدة لم تتغير.

## استراتيجية الاختبار

- Offline unit/policy tests أولًا.
- Fake-provider integration tests بلا شبكة.
- معاملات SQLite وتزامن workers على مضيف مشترك.
- negative tenant/object authorization matrix.
- crash/replay/cancel/partial-failure tests.
- schema migration forward/rollback rehearsal.
- لا live provider test في أول شريحة.

## Rollback

- migrations additive قدر الإمكان.
- rollback برجع commits عكسيًا وتعطيل endpoints/worker الخاصة بالحزمة.
- لا حذف للأدلة أو الجداول دون تفويض منفصل وخطة استعادة.
- أي migration غير قابلة للعكس تتطلب قرارًا منفصلًا قبل التنفيذ.

## أدلة الإغلاق المطلوبة

- implementation paths وtest paths.
- exact commit SHA.
- workflow run IDs ناجحة.
- migration/rollback proof.
- residual-risk review.
- tenant-isolation negative evidence.
- frozen-files unchanged.
- تحديث manifest فقط بعد تحقق كل ما سبق.

## نقطة البدء

ابدأ بجرد مخازن evidence/jobs الحالية وعقود API والمigrations، ثم قدم gap map قبل أي تعديل. لا يُنفذ أي اتصال خارجي أثناء هذا الجرد.

## سجل الإغلاق — 2026-08-05

- نُفذت العقود الخمسة والمخزن المعزول وauthorization وmigration registry وبوابة approved context في PR #122.
- implementation SHA: `ef4579c7f41dead63a506f7cdf6e163d11dd5c74`.
- merge commit على `main`: `853e2b706a9e0bc49f7da061106f8c89f7c56612`.
- نجح ASIE CI `30968258858` وCross-Platform Determinism `30968258854` على SHA التنفيذ نفسه.
- أثبتت الاختبارات offline: `30 passed`، وأثبتت Runtime Freeze + FOUNDATION: `17 passed`.
- لم تتغير الملفات المجمدة، ولم تُستخدم شبكة أو أسرار أو payloads حية.
- بقي حكم الإصدار `BLOCK`، وانتقلت FC20-05 إلى `ACR_REQUIRED` دون بدء تنفيذها.
