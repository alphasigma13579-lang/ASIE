# S2-C2 — Governed Deterministic Scenario Evaluation

| الحقل | القيمة |
|---|---|
| Document ID | `FIN2-S2C2-SCENARIOS-v1.0.0` |
| الحالة | `IMPLEMENTED — AWAITING EXACT-HEAD CI AND REVIEW` |
| المالك | Principal Architecture + Finance Engineering |
| آخر مراجعة | 2026-08-10 |
| خط الأساس | `main@4ede962cfc06d18846b421fabfcf8d2e18e8f1d0` |
| البرنامج الأب | `ASIE-FEASIBILITY-COMPLETE-01-v1.0.0` |
| القرار الأب | `ACR-FIN-002-v1.0.0` |
| مستوى التفويض | بناء داكن واختبارات GitHub CI فقط؛ لا Runtime أو Snapshot أو شبكة أو مزود أو Production |

## 1. القرار والنطاق

تنفذ هذه الشريحة الجزء الحتمي من `FR-FIN-011`: كل سيناريو deterministic يغير محركات مالية مسماة ومسموحًا بها فقط، ثم يعيد تشغيل Finance v2 من مستند مشتق، كامل التحقق، وذي `input_hash` مستقل. لا يغير السيناريو مستند الإدخال المعتمد، ولا هوية المستأجر أو المشروع أو التشغيل، ولا Manifest أو policy أو archetype أو العملة أو الأفق.

هذه الشريحة لا تنفذ `FR-FIN-012`. أي scenario من نوع simulation يبقى `not_ready` مع `FIN2_SIMULATION_NOT_READY`، ولا تُنتج quantiles أو Monte Carlo صورية.

## 2. مسار البيانات

```text
ValidatedFinanceInput (immutable canonical document)
→ baseline FinancialModel
→ scenario declaration from the same approved input hash
→ governed target allowlist
→ isolated cloned document
→ Decimal override (replace / multiply / add)
→ full validate_finance_input with the original trusted binding
→ distinct canonical scenario input_hash
→ build_financial_model
→ scenario status + metrics + blockers
→ finance-result.v2
```

لا يوجد اتصال بـ`finance_engine.py` أو `module_runtime.py` أو `snapshot_assembly.py` في هذه الشريحة.

## 3. قائمة الأهداف المسموحة

| العائلة | الصيغة |
|---|---|
| Revenue series | `$.revenue_streams[<id>].(volume_series|price_series|variable_cost_series|capacity_series)[*|YYYY-MM].value` |
| OPEX series | `$.operating_costs[<id>].schedule[*|YYYY-MM].value` |
| CAPEX | `$.capex_assets[<id>].(cost|residual_value)` |
| Working capital | `$.working_capital.(dso_days|dio_days|dpo_days)` |
| Valuation | `$.valuation_policy.(discount_rate_annual|finance_rate_annual|reinvestment_rate_annual)` |
| Debt | `$.financing.debt_tranches[<id>].annual_rate` |

أي path آخر مرفوض عند admission. والهدف المسموح نحويًا لكنه غير موجود في المستند ينتج scenario `invalid` ونتيجة كلية `not_ready`.

## 4. ثوابت القبول

- exactly one baseline، بلا overrides.
- deterministic يحتوي override واحدًا على الأقل.
- simulation لا يقبل overrides يدوية.
- لا يتكرر target داخل السيناريو، ولا يتداخل wildcard مع شهر محدد على السلسلة نفسها؛ منعًا للاعتماد على ترتيب العمليات.
- multiplier غير سالب.
- الحساب Decimal، ويقرب إلى 8 منازل فقط عند تجاوز عقد الإدخال وبـ`ROUND_HALF_EVEN`.
- المستند المشتق يعاد التحقق منه كاملًا؛ السالب غير المسموح أو علاقة CAPEX غير الصالحة لا تتحول إلى صفر.
- baseline يحافظ على `input_hash` الأصلي؛ كل deterministic صالح يحمل hash مشتقًا مختلفًا.
- simulation غير المنفذة تمنع `status=ready`.
- النتيجة المتكررة للمدخل نفسه متطابقة canonical bytes منطقيًا.

## 5. التتبع والاختبارات

| المتطلب/الخطر | التنفيذ | الاختبار |
|---|---|---|
| FR-FIN-011: سيناريو مرتبط بمحرك | `backend/finance_v2/scenarios.py` | `test_deterministic_scenario_changes_governed_driver_and_is_reproducible` |
| عدم تغيير baseline | clone + revalidation | نفس الاختبار + `test_specific_period_override_is_scoped_and_has_distinct_hash` |
| منع path حر أو مفقود | allowlist + fail closed | `test_scenario_targets_are_allowlisted_and_unique` و`test_missing_allowlisted_target_fails_closed_in_result` |
| missing ≠ zero | full contract validation | `test_invalid_scenario_arithmetic_is_not_coerced_to_zero` |
| FR-FIN-012 غير مكتملة | explicit blocker | `test_simulation_request_is_explicitly_not_ready_until_calibrated` |
| kind semantics | contract + schema conditionals | `test_scenario_kind_contracts_fail_closed` و`test_simulation_contract_does_not_accept_manual_overrides` |
| result traceability | kind/input_hash/override_refs | اختبارات `test_finance_v2_scenarios.py` |

أوامر البوابة تبقى أوامر البرنامج الأب: `pnpm build`، `python -m compileall -q backend`، و`python -m pytest -q` في GitHub Actions، إضافة إلى Cross-Platform Determinism.

## 6. التراجع والتوافق

- لا migration ولا كتابة بيانات ولا feature flag ولا runtime activation.
- التراجع قبل الدمج: إغلاق PR وحذف الفرع.
- التراجع بعد الدمج: revert واحد لشريحة S2-C2؛ Finance v1 والغلاف المجمد لم يتغيرا.
- عند طلب legacy projection مع أي scenario غير baseline، يكون الإسقاط `not_available` والنتيجة `not_ready` حتى يكتمل إسقاط السيناريو وتطابقه؛ لا يعاد baseline فقط باعتباره توافقًا كاملاً.
- baseline-only input يظل صالحًا، لكن `finance-result.v2.scenarios[]` أصبح يصرح `kind` و`input_hash` و`override_refs`. هذه إضافة داخل عقد v2 الداكن وترافقها زيادة `engine_version` إلى `2.0.0-dark.2`.

## 7. الفجوات المتبقية المانعة

- `FR-FIN-012`: توزيعات sector/archetype، correlation، seed، convergence diagnostics، sensitivity matrix وMonte Carlo.
- golden vectors والحالات الإحدى عشرة ومراجعة sector experts.
- VAT input/output ledger.
- all-consumer/API/UI/PDF/CSV parity.
- مراجعة Finance Reviewer/CPA وقرار G1.

لذلك هذه الوثيقة لا تمنح L1 أو G1 أو صلاحية مصرفية، ولا تسمح بتفعيل Finance v2 في المسار الرسمي.
