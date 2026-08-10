# ACR-FIN-003 — Governed Sensitivity and Simulation Profiles

| الحقل | القيمة |
|---|---|
| Document ID | `ACR-FIN-003-v1.0.0` |
| الحالة | `ACCEPTED FOR CONTRACT-ONLY IMPLEMENTATION` |
| المالك | Principal Architecture + Finance Engineering |
| المراجعون الإلزاميون قبل محرك المحاكاة | Finance Reviewer/CPA + Quantitative Reviewer + Sector Expert + QA + Security |
| آخر مراجعة | 2026-08-10 |
| خط الأساس | `main@a704fc44311a9e6b5535170b0bfb9bd5fa5c840a` |
| البرنامج الأب | `ASIE-FEASIBILITY-COMPLETE-01-v1.0.0` |
| القرار الأب | `ACR-FIN-002-v1.0.0` |
| مستوى التفويض | عقود واختبارات static في GitHub CI فقط؛ لا محاكاة إنتاجية ولا Runtime ولا شبكة ولا مزود ولا G1 |

> هذا القرار يعرّف العقود التي يجب أن تسبق `FR-FIN-012`. لا يثبت أن أي توزيع معاير، ولا يسمح بإنتاج Monte Carlo أو sensitivity authoritative، ولا يغير Finance v1 أو AAS Freeze.

## 1. المشكلة والحكم

### FACT

- Finance v2 ينفذ baseline وdeterministic scenarios محكومة في `main@a704fc44`.
- عقد الإدخال الحالي يحمل `distribution_profile_ref` و`correlation_profile_ref` فقط، بلا hash غير قابل للتبديل وبلا schema للملفات المشار إليها.
- لا يوجد عقد حاكم لمصفوفة correlation أو convergence policy أو sensitivity matrix.
- `FIN2_SIMULATION_NOT_READY` يمنع النتيجة من `ready` بدل إنتاج أرقام صورية.
- `FR-FIN-012` يشترط distributions مبررة حسب sector/archetype، correlation، seed، convergence diagnostics وsensitivity matrix.

### DECISION

نعتمد أربعة عقود مستقلة ومحدودة:

1. `finance-simulation-distribution-profile.v1`
2. `finance-simulation-correlation-profile.v1`
3. `finance-simulation-policy.v1`
4. `finance-sensitivity-profile.v1`

تبقى profiles خارج مستند المشروع الخام، وتُحلّ خادميًا من registry versioned بواسطة `ref + content_hash` مرتبطين بالـApproved Manifest. لا يقبل المحرك profile body أو path أو expression من العميل.

## 2. بدائل القرار

| البديل | الحكم | السبب |
|---|---|---|
| عوامل ±10% عامة | مرفوض | يعيد عيب السيناريوات الثابتة ولا يمثل archetype |
| توزيع يرسله العميل داخل الطلب | مرفوض | سطح تلاعب وغياب مراجعة/إصدار |
| ref قابل للتبديل بلا hash | مرفوض | لا يعيد إنتاج النتيجة تاريخيًا |
| ملفات versioned + hash + review state + registry | **مختار** | تتبع، حتمية، وإمكانية fail-closed |
| استخدام مكتبة Monte Carlo مباشرة الآن | مرفوض | لا profile calibration ولا cross-platform vectors ولا قرار Quant |

## 3. حدود البيانات والسلطة

```text
Approved Manifest
→ server-owned model-selection policy
→ immutable profile refs + content hashes
→ registry resolution
→ schema + semantic validator
→ profile review gate
→ deterministic RNG policy + seed
→ scenario target allowlist from Finance v2
→ simulation/sensitivity engine (future slice)
→ convergence and invariant gate
→ finance-result.v2 diagnostics
```

- لا يقرأ UI/AI ملف profile مباشرة.
- لا يسمح target خارج allowlist S2-C2.
- لا raw JSONPath حر، لا expression، لا eval، لا callable.
- لا profile status أقل من `approved` في تشغيل authoritative مستقبلي.
- profile `draft/calibrated/reviewed` مسموح فقط للاختبارات غير المختومة.
- كل نتيجة مستقبلية تحمل refs/hashes، algorithm versions، seed، iterations الفعلية، convergence status وblockers.

## 4. عقود الملفات

### 4.1 Distribution profile

كل variable يربط:

- `variable_id` ثابت.
- target allowlisted.
- operation: replace/multiply/add.
- unit.
- distribution kind ومعلمات صريحة.
- minimum/maximum.
- calibration method، الفترة، الجغرافيا، freshness، sample size، data/evidence/assumption refs.
- review state مستقل عن مجرد وجود البيانات.
- currency صريحة، وmetadata تحمل owner/effective date/supersession؛ لا profile مجهول الملكية أو الصلاحية.

الأنواع العقدية: triangular، uniform، normal_truncated، lognormal_truncated، discrete_empirical.

قرار التنفيذ: triangular/uniform/discrete_empirical هي البداية المسموحة للحساب الحتمي. normal/lognormal تبقيان `not_supported` حتى اعتماد deterministic transform version وgolden reference vectors؛ وجودهما في العقد لا يعني تنفيذًا.

### 4.2 Correlation profile

- يربط distribution profile بـref+hash.
- variable IDs تطابقه واحدًا لواحد.
- matrix مربعة، القطر 1، القيم [-1,1]، متناظرة وpositive semidefinite ضمن tolerance.
- `non_psd_behavior=reject`؛ لا nearest-PSD أو تصحيح صامت.
- methods العقدية: Pearson/Spearman Gaussian copula.
- لا تنفيذ copula قبل اعتماد Quant reviewer وخوارزمية transform حتمية.

### 4.3 Simulation policy

- RNG: `pcg64_dxsm_v1` مع reference vector إلزامي.
- اشتقاق stream: seed + scenario + variable وفق إصدار ثابت.
- حدود iterations/batch تمنع الاستنزاف.
- convergence يراقب metrics وquantiles عبر batches.
- failure policy دائمًا `not_ready`.
- لا ترقية إلى ready لمجرد إكمال عدد iterations إذا فشل التقارب.

### 4.4 Sensitivity profile

- محوران بالضبط، values صريحة وlineage لكل محور/override، حد أقصى 21×21 و`maximum_cells<=441`.
- fixed overrides اختيارية لكنها allowlisted.
- لا تداخل axis/axis أو axis/fixed أو wildcard/period.
- كل cell يعيد تشغيل النموذج المالي كاملًا؛ لا تقريب خطي للنتيجة.
- missing/invalid cell يمنع مصفوفة ready ولا يتحول إلى صفر.

## 5. content hash والحتمية

- `content_hash` هو SHA-256 لـcanonical JSON بعد حذف حقل `content_hash` نفسه فقط.
- canonical serialization هي سياسة Finance v2 نفسها.
- ref دون hash أو hash mismatch: رفض.
- نفس Finance input/profile hashes/policy version/seed يعطي نفس stream وlogical output bytes.
- أي تغيير في calibration أو review أو parameters ينتج version/hash جديدًا؛ لا overwrite.
- historical results لا تعاد حسابها ولا تُعدّل.

## 6. القيود الدلالية غير القابلة للإثبات بـJSON Schema وحده

يجب أن تنفذ C3B validators قبل أي حساب:

- unique variable IDs وunique/non-overlapping targets.
- bounds: minimum ≤ mode/mean/value ≤ maximum؛ stddev/sigma > 0.
- discrete values/probabilities بنفس الطول، probabilities غير سالبة ومجموعها 1 ضمن tolerance.
- calibration period_from ≤ period_to وfreshness policy.
- approved status يتطلب approvals مكتملة للأدوار المطلوبة ولا rejection.
- matrix dimensions = عدد variables؛ القيم ضمن [-1,1]؛ symmetry؛ diagonal=1؛ PSD.
- simulation minimum ≤ maximum؛ batch size صالح؛ stable_batches ≤ available batches.
- sensitivity axes مختلفة، cells = حاصل أطوال المحورين ≤ maximum_cells، ولا overlap.
- refs/hashes تطابق registry snapshot وApproved Manifest.

الفشل في أي قاعدة ينتج blocker `FIN2_*` ولا fallback.

## 7. الأمن والاعتمادية

| الخطر | الضبط |
|---|---|
| path/expression injection | target allowlist مغلق؛ additionalProperties=false |
| profile substitution | ref+content_hash+Manifest binding |
| cross-tenant profile | registry authorization server-side؛ لا client authority |
| resource exhaustion | variables≤50، matrix≤50×50، iterations≤100000، cells≤441 |
| silent correlation repair | reject non-PSD |
| reproducibility drift | pinned algorithms + reference vectors + hashes |
| false professional claim | review states + G1 block + explicit not_ready |
| stale public data | freshness/data/evidence refs؛ owner review |

لا secrets ولا network ولا provider في العقود أو الاختبارات.

## 8. مراحل التنفيذ الملزمة

| المرحلة | المخرج | بوابة الخروج |
|---|---|---|
| C3A | ACR + 4 schemas + static tests | CI + architecture review؛ لا engine |
| C3B | registry admission + semantic validators + hash checks | negative/property tests |
| C3C | deterministic 2D sensitivity | cell parity + bounds + performance |
| C3D | RNG + independent distributions | published reference vectors + cross-platform byte parity |
| C3E | correlation + convergence | Quant review + PSD/golden/convergence tests |
| C3F | archetype calibration/golden cases | sector experts + CPA + G1 evidence |

لا يجوز القفز من C3A إلى C3E.

## 9. الاختبارات المطلوبة لاحقًا

- schema closure and required-field tests.
- hash mismatch/ref substitution/forged approval negatives.
- distribution parameter property tests.
- probability sum and bounds tests.
- correlation symmetry/diagonal/range/PSD property tests.
- RNG reference vectors and seed repeatability.
- cross-platform exact logical serialization.
- sensitivity overlap/cell-limit/missing-cell tests.
- convergence success/failure/near-threshold tests.
- golden vectors reviewed independently for each archetype.
- all-consumer/API/UI/PDF/CSV parity before G1.

## 10. التراجع والمهاجرة

C3A تضيف ملفات فقط؛ لا migration ولا runtime flag. التراجع هو revert واحد للوثيقة والعقود والاختبارات. C3B–C3E تبقى dark build. أي ربط بالمسار الرسمي أو Snapshot يحتاج بوابة مستقلة وACR/Freeze review حسب ACR-FIN-002.

## 11. الفجوات المانعة بعد C3A

- لا registry persistence/admission.
- لا semantic validators.
- لا sensitivity engine.
- لا RNG/sampling/correlation/convergence engine.
- لا calibration datasets أو approved profile instances.
- لا Quant/CPA/Sector approvals.
- لا VAT ledger، ولا golden cases الإحدى عشرة، ولا G1.

لذلك C3A لا تغيّر الحكم: Finance v2 غير مفعل، وادعاء «دراسة احترافية معتمدة لأي مشروع» غير مسموح.
