# ASIE Architecture Correction Plan

Date: 2026-07-18
Scope: مراجعة معمارية دقيقة لما بُني فعليًا على القرص مقارنةً بـ AAS Frozen Architecture، مع خطة تصحيح تحفظ العمل الحالي وتعيده إلى المسار الأساسي.

## 1. الحكم المختصر

شكّك في محله.

ما بُني هو AAS Runtime محلي مجمد v1.0 يضم Finance, Evidence, Source Governance, Sector Intelligence, Risk, Execution, Decision Pack, Snapshot خلف Kernel/Hearts/Bus/Socket/ModuleRuntime، دون اتصال خارجي أو AI Provider.

الانحراف الأساسي ليس في الحسابات، بل في **ترتيب البناء**:

المفترض حسب AAS:

```text
ASIE Kernel
-> Heart Controller
-> Primary / Assist / Reserve Hearts
-> Bus Controller
-> ASIE System Bus
-> Socket Contract Layer
-> Modules
```

الموجود فعليًا الآن:

```text
React UI
-> Python HTTP API
-> build_overview() direct orchestration
-> direct calls to finance/evidence/decision/risk/report modules
-> SQLite snapshots
```

بمعنى آخر: المنتج الوظيفي تقدم بسرعة، لكن الطبقة التشغيلية الأساسية بقيت غير منفذة.

## 2. مصادر المراجعة

راجعت الملفات التالية كمرجع حاكم:

- `AAS-02-ASIE-Operating-Architecture.md`
- `AAS-10-ASIE-Kernel-Specification.md`
- `AAS-12-ASIE-Heart-Controller-Specification.md`
- `AAS-13-ASIE-Three-Hearts-Specification.md`
- `AAS-15-ASIE-System-Bus-Specification.md`
- `AAS-16-ASIE-Socket-Contract-Layer-Specification.md`
- `AAS-17-ASIE-Module-Specification.md`
- `AAS-40-ASIE-AI-Integration-Specification.md`
- `backend/asie_local_api.py`
- `backend/repository.py`
- `backend/contracts.py`
- `src/contracts.ts`
- `src/App.tsx`
- `src/api.ts`
- `tests/test_local_platform.py`

## 3. ما هو مكتمل فعليًا

| المجال | الموجود على القرص | الحالة |
|---|---|---|
| Frontend | React/Vite UI مع landing/legal gate/sidebar/wizard/evidence/readiness/decision/snapshots | مكتمل محليًا كمستوى منتج أولي |
| API | Python stdlib HTTP API على `8794` | مكتمل محليًا، لكن ليس خلف Bus/Socket |
| Storage | SQLite مع projects/runs/snapshots/sources/assumptions/datasets/evidence_links/transformations/reviews/action_items | مكتمل محليًا |
| Snapshot | snapshots immutable تقرأ منها التقارير وDecision Pack | مكتمل وقوي |
| Finance Engine | NPV/IRR/payback/Monte Carlo/operational finance/DSCR/sensitivity | مكتمل v1 |
| Source Governance | candidate/blocked/enabled/reference_only ومراجعة صارمة للمصادر | مكتمل v1 |
| Evidence Ledger | dataset profile, evidence links, coverage matrix, target_type/target_id | مكتمل v1 |
| Transformation Layer | transformation records/lineage/review/quality and snapshot inclusion | مكتمل v1 |
| Sector Intelligence | taxonomy/criteria/evidence gaps/candidate sources | مكتمل v1 |
| Decision Council | خمس شخصيات وحكم حتمي بلا تصويت | مكتمل وظيفيًا |
| Risk Engine | risk register مستقل عن Execution | مكتمل v1 |
| Execution Engine | execution plan ومراحل التنفيذ | مكتمل v1 |
| Readiness Gates | readiness gates قبل Decision/Risk/Execution | مكتمل v1 |
| Decision Pack | review workflow, action items, HTML decision pack/report | مكتمل v1 |
| Tests | يوجد 88 اختبارًا وظيفيًا ومعماريًا وحراسات r10/r11 | جيد، ويشمل حراسات AAS runtime تدريجيًا |

## 4. ما لم يبنَ من المعمارية الأساسية

| مكون AAS | المطلوب حسب AAS | الموجود فعليًا | الحالة |
|---|---|---|---|
| ASIE Kernel | يبدأ النظام فقط، يحمل configuration/registry/contracts، لا ينفذ منطق أعمال | `backend/aas_kernel.py` | مكتمل v1 كهيكل تشغيل غير كاسر |
| Boot Process | Runtime -> Config -> Registry -> Contracts -> Security -> Heart Bootstrap | تشغيل مباشر للـAPI | غير مبني |
| Registry | تسجيل contracts/sockets/modules/states/health | `backend/aas_registry.py` يسجل contracts/sockets/module descriptors | مكتمل v1 كسجل Runtime، وليس بديلًا عن SQLite |
| Heart Controller | يدير القلوب ويمنع أي قلب من القرار المنفرد | `backend/heart_controller.py` | مكتمل v1 كطبقة تشغيل غير كاسرة |
| Primary Heart | القلب الأساسي الدائم | `backend/hearts.py` / `M1` | مكتمل v1 |
| Assist Heart | القلب المساعد عند الحاجة | `backend/hearts.py` / `M2` | مكتمل v1 |
| Reserve Heart | القلب الاحتياطي للطوارئ | `backend/hearts.py` / `M3` | مكتمل v1 كاحتياطي failover فقط |
| Bus Controller | يقبل/يرفض modules/sockets/messages ويتحقق من العقود | `backend/bus_controller.py` | مكتمل v1 كحارس رسائل غير كاسر |
| ASIE System Bus | المسار الوحيد للرسائل بين modules | `backend/system_bus.py` | مكتمل v1؛ Finance داخل `build_overview()` يمر عبره الآن |
| Socket Contract Layer | Socket First, Module Second | `backend/socket_contracts.py` | مكتمل v1 كطبقة تحقق مستقلة قبل تسليم الرسائل |
| Module Lifecycle | discovery/registration/validation/binding/activation/isolation | `backend/module_runtime.py` يشغل handler مسجل بعد Bus/Socket | مكتمل Freeze v1.0؛ جميع المحركات الأساسية وReport وDecision Pack مسجلة خلف Bus/Socket/ModuleRuntime |
| Message Flow | messages with source/target/contract/socket/correlation/audit | `BusMessage` يفرض envelope تشغيليًا | مكتمل Freeze v1.0؛ كل عقود التشغيل تتبع ترتيب Workflow مغلقًا، وExecution يقرأ `risk.advisory.summary.v1` فقط |
| AI Integration | AI كقدرة bounded خلف contract، لا يحكم ولا ينتج الحقيقة | لا توجد طبقة AI فعلية؛ فقط حراسات تمنع AI من امتلاك الأرقام | غير مبني |
| Zero Trust Runtime | تحقق رسائل وصلاحيات وسياق أمني | سياسة مصادر صارمة، لكن لا يوجد Zero Trust runtime عام | جزئي |

## 5. أين وقع الانحراف بالضبط

الملف المركزي الحالي هو:

`backend/asie_local_api.py`

الدالة الحاسمة:

`build_overview(project, repo)`

هذه الدالة تنفذ سلسلة مباشرة:

```text
finance_result_set
source_policy
build_evidence_register
build_sector_intelligence
build_evidence_ledger
build_transformation_lineage
build_evidence_coverage
build_readiness_gates
evaluate_decision_council
build_execution_plan
build_risk_register
project_readiness
build_acceptance_pack
build_report
```

هذا جيد كنموذج منتج محلي، لكنه يخالف شكل AAS لأن:

- لا يوجد Kernel يبدأ النظام.
- لا يوجد Heart Controller يدير التنفيذ.
- لا توجد قلوب Primary/Assist/Reserve.
- لا يوجد Bus Controller يوافق على مشاركة module.
- لا توجد رسائل عبر ASIE System Bus.
- لا يوجد Socket Contract Layer يفرض العقود قبل التنفيذ.
- لا توجد AI Integration Layer، فقط منع لاستخدام AI كمالك حقيقة.

## 6. أين القلوب الثلاثة M1/M2/M3

التسمية الرسمية في AAS ليست M1/M2/M3، بل:

| تسمية المستخدم | تسمية AAS الرسمية | الحالة |
|---|---|---|
| M1 | Primary Heart | منفذ v1 |
| M2 | Assist Heart | منفذ v1 |
| M3 | Reserve Heart | منفذ v1 |

يجب ألا تكون القلوب مجرد أسماء في الواجهة. يجب أن تظهر ككيانات تشغيلية لها:

- `heart_id`
- `role`
- `state`
- `health`
- `load`
- `activation_reason`
- `last_heartbeat_at`
- `controlled_by: heart_controller`

## 7. أين طبقات الذكاء الاصطناعي

غير منفذة حاليًا.

الموجود الآن هو حراسة صحيحة تمنع AI من امتلاك الأرقام أو الأحكام، مثل:

- `AI-owned controlled numbers`
- `provider-neutral guard recorded`
- `no AI or provider owns controlled outputs`

لكن غير الموجود:

- AI Integration Layer
- Provider Abstraction
- Provider Adapter
- Model Router
- Prompt Governance
- Context Governance
- RAG/Evidence Retrieval
- Tool Calling Guard
- Output Validation
- Human Review Gate
- AI Observability
- Degraded/Fallback Mode

التصحيح لا يعني إضافة مفاتيح أو مزود الآن. المرحلة الصحيحة هي بناء **طبقة AI فارغة/محكومة**:

```text
AI Integration Module
status: disabled_by_default
providers: []
external_calls: blocked
allowed_use: explain/summarize/draft only
forbidden_use: finance/legal/final decisions/numeric truth
```

## 8. لماذا لا نرمي ما تم

العمل الحالي ليس خطأ يجب حذفه. هو يمثل Modules وظيفية جاهزة، لكنها تحتاج أن تُغلف داخل AAS runtime.

إعادة التصحيح الصحيحة:

```text
current finance_engine.py        -> Finance Module
current source_registry.py       -> Source Governance Module
current datasets.py              -> Dataset Module
current transformations.py       -> Transformation Module
current evidence_ledger.py       -> Evidence Ledger Module
current sector_intelligence.py   -> Sector Intelligence Module
current decision_council.py      -> Decision Council Module
current risk_engine.py           -> Risk Module
current execution_engine.py      -> Execution Module
current reports.py               -> Report Module
current decision_pack.py         -> Decision Pack Module
current repository.py            -> Local Persistence Adapter
```

## 9. خطة التصحيح المقترحة

### Phase 0 - تثبيت الحقيقة الحالية

الهدف: إيقاف التوسع الوظيفي مؤقتًا وتوثيق خط الأساس.

المطلوب:

- حفظ هذه الوثيقة كمرجع تصحيح.
- اعتماد مخطط صفحة واحدة يوضح ما بُني وما لم يبنَ.
- عدم إضافة modules منتجية جديدة قبل بناء AAS runtime skeleton.

المخرجات:

- `docs/ASIE-Architecture-Correction-Plan-2026-07-18.md`
- `docs/ASIE-Architecture-One-Page-Map-2026-07-18.svg`

### Phase 1 - AAS Runtime Skeleton

الهدف: بناء الهيكل التشغيلي دون تغيير نتائج المنتج.

ملفات مقترحة:

```text
backend/aas_kernel.py
backend/aas_registry.py
backend/heart_controller.py
backend/hearts.py
backend/bus_controller.py
backend/system_bus.py
backend/socket_contracts.py
backend/module_runtime.py
backend/ai_integration.py
```

قواعد:

- Kernel يبدأ فقط ولا يحسب.
- Registry يسجل modules/contracts/sockets.
- Heart Controller يدير Primary/Assist/Reserve.
- Bus لا ينفذ business logic.
- Socket layer يتحقق من contract قبل استدعاء module.
- AI module يبقى disabled ولا يملك أرقامًا.

حالة التنفيذ بتاريخ 2026-07-18:

| الحزمة | الحالة | الملفات | ملاحظات |
|---|---|---|---|
| Kernel & Registry v1 | مكتملة | `backend/aas_kernel.py`, `backend/aas_registry.py`, `tests/test_aas_runtime.py` | لا تغير نتائج المنتج، ولا تستبدل `build_overview()` بعد |
| Heart Controller + Three Hearts | مكتملة | `backend/heart_controller.py`, `backend/hearts.py`, `tests/test_aas_runtime.py` | القلوب تشغيلية فقط ولا تنفذ منطق أعمال |
| Bus Controller + System Bus | مكتملة | `backend/bus_controller.py`, `backend/system_bus.py`, `tests/test_aas_runtime.py` | يفرض `contract_id`, `socket_id`, `correlation_id`, و`audit_ref` ولا ينفذ منطق أعمال |
| Socket Contract enforcement runtime | مكتملة | `backend/socket_contracts.py`, `tests/test_aas_runtime.py` | يفرض Socket First, Module Second وpayload contract قبل التسليم |
| Module Runtime wrapping | مكتملة v1 | `backend/module_runtime.py`, `tests/test_aas_runtime.py` | Finance يعمل خلف Bus/Socket |
| Gradual Orchestrator Replacement v1 | مكتملة | `backend/asie_local_api.py`, `tests/test_local_platform.py` | Finance داخل `build_overview()` انتقل إلى `ModuleRuntime` مع parity test |
| Gradual Orchestrator Replacement v2 | مكتملة | `backend/module_runtime.py`, `backend/asie_local_api.py`, `tests/test_local_platform.py` | Evidence Ledger داخل `build_overview()` انتقل إلى `ModuleRuntime` مع parity test |
| Gradual Orchestrator Replacement v3 | مكتملة | `backend/module_runtime.py`, `backend/asie_local_api.py`, `tests/test_local_platform.py` | Sector Intelligence داخل `build_overview()` انتقل إلى `ModuleRuntime` مع parity test |
| Gradual Orchestrator Replacement v4 | مكتملة | `backend/aas_registry.py`, `backend/module_runtime.py`, `backend/asie_local_api.py`, `tests/test_local_platform.py` | Decision Council انتقل إلى `ModuleRuntime` بعقد مدخلات مغلق يمنع Risk/Execution |
| Gradual Orchestrator Replacement v5 | مكتملة | `backend/aas_registry.py`, `backend/module_runtime.py`, `backend/asie_local_api.py`, `tests/test_local_platform.py`, `tests/test_aas_runtime.py` | Risk Engine انتقل وحده إلى `ModuleRuntime` بعقد مستقل ولا يستقبل Decision/Execution |
| Gradual Orchestrator Replacement v6 | مكتملة | `backend/aas_registry.py`, `backend/module_runtime.py`, `backend/asie_local_api.py`, `tests/test_local_platform.py`, `tests/test_aas_runtime.py` | Execution Engine انتقل وحده إلى `ModuleRuntime` بعقد مستقل ولا يستقبل Risk |
| Gradual Orchestrator Replacement v7 | مكتملة | `backend/aas_registry.py`, `backend/module_runtime.py`, `backend/asie_local_api.py`, `tests/test_local_platform.py`, `tests/test_aas_runtime.py` | Report Module انتقل إلى `ModuleRuntime` بعقد تقرير snapshot مغلق ولا يقرأ repository/reviews |
| Gradual Orchestrator Replacement v7.1 | مكتملة | `backend/risk_engine.py`, `backend/execution_engine.py`, `backend/aas_registry.py`, `backend/module_runtime.py`, `backend/asie_local_api.py`, `tests/test_local_platform.py`, `tests/test_aas_runtime.py` | Execution لا يستقبل `risk_register` الكامل ولا يستدعي Risk مباشرة؛ يستقبل فقط `risk.advisory.summary.v1` مغلقًا يحتوي ids/constraints مختصرة |
| AI Integration Shell v9 | مكتملة كطبقة معطلة ومحكومة | `backend/ai_integration.py`, `backend/module_runtime.py`, `backend/aas_registry.py`, `tests/test_aas_runtime.py` | لا يوجد provider أو network route؛ يمنع numeric truth/finance/legal/verdict ownership |

### Phase 2 - تحويل المحركات الحالية إلى Modules

الهدف: الاحتفاظ بالنتائج الحالية مع تغيير طريقة الاستدعاء.

قبل:

```text
build_overview -> finance_result_set()
```

بعد:

```text
build_overview -> SystemBus.dispatch("finance.evaluate", payload)
             -> SocketContract.validate(...)
             -> FinanceModule.handle(...)
```

الوحدات الأولى التي تُغلف:

- Finance Module
- Source Governance Module
- Evidence Ledger Module
- Sector Intelligence Module
- Decision Council Module
- Report Module

### Phase 3 - استبدال build_overview بمنسق رسائل

الهدف: يصبح `build_overview` مسارًا تشغيليًا، لا منسق أعمال مباشر.

المسار الجديد:

```text
API request
-> Kernel runtime context
-> Heart Controller assigns task to Primary Heart
-> Primary Heart submits messages to System Bus
-> Bus Controller verifies module participation
-> Socket Contract Layer validates payload
-> Modules execute
-> Snapshot Assembler stores immutable snapshot
```

### Phase 4 - AI Integration Shell

الهدف: بناء حدود AI الآن، دون تشغيل AI خارجي.

المطلوب:

- `AIIntegrationModule`
- `ProviderRegistry` empty
- `ModelRouter` returns `disabled_no_provider`
- `PromptGovernance` rules
- `OutputValidation` rejects numeric truth/legal/finance ownership
- `HumanReviewGate` placeholder
- Audit entries for any AI request attempt

### Phase 5 - واجهة حالة المعمارية

الهدف: تظهر للمستخدم والإدارة حالة تشغيل المنصة، لا فقط نتائج المشروع.

إضافة شاشة:

```text
Architecture Runtime Status
- Kernel: ready/not ready
- Heart Controller: ready/not ready
- Primary Heart: active
- Assist Heart: inactive
- Reserve Heart: reserved
- Bus Controller: ready
- System Bus: ready
- Socket Contract Layer: enforcing
- AI Integration: disabled/governed
```

### Phase 6 - اختبارات قبول AAS

إضافة اختبارات جديدة:

- Kernel لا يحتوي business logic.
- لا يعمل module قبل التسجيل.
- لا تمر message دون contract_id.
- لا تمر message دون socket_id.
- لا توجد direct module-to-module calls في مسار التشغيل الجديد.
- Primary Heart لا يقرر وحده.
- Assist/Reserve لا يعملان دائمًا.
- AI لا ينتج أرقامًا أو أحكامًا.
- Snapshot لا يعاد حسابه بعد التعديل.
- المنافذ تبقى `5194` و`8794`.

## 10. قرار العمل التالي

المرحلة التالية يجب أن تكون:

**Gradual Orchestrator Replacement v8**

وليس إضافة واجهات أو محركات جديدة.

هذه المرحلة لا تضيف مصادر، لا مفاتيح، لا APIs خارجية، ولا AI Provider.

تعريف النجاح:

- يبقى Kernel وRegistry وHeart Controller والقلوب الثلاثة v1 ناجحين.
- يبقى Bus Controller وSystem Bus v1 ناجحين.
- تبقى Finance عبر Module Runtime v1 ناجحة.
- تبقى Evidence Ledger عبر Module Runtime v2 ناجحة.
- تبقى Sector Intelligence عبر Module Runtime v3 ناجحة.
- تبقى Decision Council عبر Module Runtime v4 ناجحة بعقد `DecisionCouncilInputEnvelope.v1`.
- تبقى Risk Engine عبر Module Runtime v5 ناجحة بعقد `RiskRegisterInputEnvelope.v1`.
- تبقى Execution Engine عبر Module Runtime v6 ناجحة بعقد `ExecutionPlanInputEnvelope.v1`.
- تبقى Report Module عبر Module Runtime v7 ناجحة بعقد `SnapshotReportInputEnvelope.v1`.
- يبقى تصحيح v7.1 ناجحًا: انتقال نتائج Risk الضرورية إلى Execution يتم عبر `risk.advisory.summary.v1` فقط، وليس عبر `risk_register` الكامل أو استدعاء مباشر.
- يبدأ نقل محرك تالٍ من `build_overview()` إلى dispatch تدريجي، والأقرب: Decision Pack Runtime كمسار منفصل يقرأ snapshot/report/reviews ولا يعيد الحساب.
- يثبت اختبار parity أن snapshot/report لا يتغيران.
- أي اختلاف في snapshot/report يعد كسرًا يجب إصلاحه.
- snapshots والتقارير لا تتغير.
- كل الاختبارات الحالية تبقى ناجحة.
- تضاف اختبارات parity لكل محرك يتم نقله.

## 11. المخطط

المخطط المحفوظ:

`docs/ASIE-Architecture-One-Page-Map-2026-07-18.svg`

يمثل:

- المعمارية الأساسية المجمدة.
- ما بُني فعليًا.
- فجوة التصحيح.
- موضع طبقات AI.
- موضع القلوب الثلاثة.

## 12. خلاصة تنفيذية

بصراحة: نحن لم نبنِ المعمارية الأساسية أولًا. بنينا محصولًا وظيفيًا مهمًا فوق API محلي، ثم بدأنا نشعر بالفجوة من الواجهة لأن المسار يعطي إحساس منتج، لكنه لا يكشف طبقة التشغيل الحاكمة.

التصحيح ليس إعادة بداية. التصحيح هو رفع ما بُني إلى مكانه الصحيح داخل AAS:

```text
Do not delete the engines.
Wrap them as AAS Modules.
Put Kernel/Hearts/Bus/Socket before them.
Keep AI governed and disabled until formally enabled.
```

## 13. Package v7.2-A - Snapshot Assembly Core

Status: completed on 2026-07-18.

Implemented:

- `aas.sealed.module.output.v1` as the strict run-scoped output envelope.
- `snapshot.assemble.v1` through `socket.snapshot.assemble` and `module.snapshot_assembly`.
- `SnapshotAssemblyModuleAdapter` with no engine calls, recalculation, persistence, AI, or external fetch.
- One `RunScopedModuleRuntime` identity for the six required module outputs and final assembly message.
- Required producer, contract version, project, run, snapshot, correlation, audit, and output hash validation.
- Immutable assembly output with `module_outputs`, `lineage`, `correlation_map`, `content_hash`, and `integrity_hash`.
- Fail-closed behavior for missing outputs, duplicate outputs, identity mismatch, unregistered producers, and tampering.

Deferred deliberately to v7.2-B:

- Cut `build_overview()` over to the assembled snapshot.
- Seal supporting outputs such as readiness, assumptions, source governance, transformations, acceptance, and audit.
- Make Dashboard and Report projections read the same assembled snapshot.
- Persist overview/report atomically only after assembly and projection parity succeeds.

## 14. Package v7.2-B - Snapshot Projection Cutover

Status: completed on 2026-07-18.

Implemented:

- `execute_project_run_pipeline()` creates one `RunScopedModuleRuntime` for Finance, Evidence, Sector, Decision, Risk, and Execution; deprecated `build_overview()` only converts legacy parity fixtures into `ProjectRunEnvelope`.
- Finance assumption references are attached inside the Finance adapter before its output is sealed.
- Non-engine dashboard/report context is sealed as `snapshot.projection.support.v1` with Heart Controller ownership.
- `project_overview_from_assembled_snapshot()` projects the dashboard payload from assembled module outputs and sealed support only.
- Report Module consumes that projected overview after assembly and does not invoke upstream engines.
- Overview and Report carry the same assembly `content_hash` and `integrity_hash`.
- Independent overview/report projection hashes detect post-assembly mutation.
- Repository persistence validates assembly identity, projection source, all hashes, and project/run/snapshot parity before opening the SQLite transaction.
- Run and Snapshot rows remain one atomic transaction; validation failure creates neither row.

Next package:

- `v8 - Decision Pack Runtime`.
- Decision Pack must read the immutable saved snapshot only.
- Review records remain a separate overlay and never participate in snapshot hashes.

## 15. Package v8 - Decision Pack Runtime

Status: completed on 2026-07-18.

Implemented:

- `decision.pack.v1` through `socket.decision.pack` and `module.decision_pack`.
- `DecisionPackModuleAdapter` accepts only immutable saved `snapshot_overview` and its matching `snapshot_report`.
- The adapter rejects repository handles, current project state, reviews, action items, and any additional live inputs.
- Snapshot identity, assembly hashes, overview projection hash, and report projection hash are revalidated before projection.
- The Decision Pack base has an independent `decision_pack_hash` and does not contain review records.
- `apply_review_overlay()` adds review status and history after runtime projection without changing the base hash, sovereign verdict, or snapshot hashes.
- Review Overlay has its own identity and hash and validates project/run/snapshot identity for every review.
- JSON and HTML Decision Pack endpoints now use Module Runtime through Bus/Socket before applying the local overlay.
- External fetch and AI remain disabled.

Next package:

- `v9 - AI Integration Shell`.
- Build provider registry, disabled model router, prompt governance, output validation, human-review gate, and audit trail without enabling any external provider.

## 16. Package v9 - AI Integration Shell

Status: completed on 2026-07-18 as a disabled governed shell.

Implemented:

- `module.ai_integration` behind `socket.ai.integration` and `ai.integration.request.v1`.
- Empty `ProviderRegistry`; registration always fails with `ai_provider_registration_disabled`.
- `ModelRouter` returns `disabled_no_provider` and never attempts network access.
- `PromptGovernance` allows explanation/summarization/translation/draft narrative classes in principle while blocking finance calculation, controlled numeric truth, legal interpretation, source activation, and sovereign verdict requests.
- `OutputValidation` rejects controlled numbers and finance/legal/sovereign/source-governance ownership.
- `HumanReviewGate` is mandatory and cannot be bypassed for any future AI output.
- Every admitted request attempt produces an audit event with request lineage and outcome.
- Raw prompt text is not accepted by the local shell or stored on the Bus; only `prompt_template_id` and `prompt_hash` are accepted.
- No API endpoint, provider, key, model, generated output, or external network path was added.

Next correction phases from the original plan:

- Architecture Runtime Status view.
- Final AAS acceptance tests for no bypass, heart behavior, disabled AI ownership, snapshot immutability, and fixed ports.

## 17. Architecture Runtime Status + Final AAS Acceptance

Status: completed on 2026-07-18.

Implemented:

- `backend/architecture_status.py` builds one local read-only runtime status from Kernel, Registry, Heart Controller, M1/M2/M3, Bus Controller, System Bus, Socket Contract Layer, Module Runtime, Snapshot Assembly, and AI Integration Shell.
- `GET /api/architecture/runtime-status` exposes the status without adding product engines, external fetch, providers, keys, or source integrations.
- Frontend stage `المعمارية` displays runtime health, registry counts, registered module handlers, the three hearts, Snapshot Assembly guard state, AI Shell disabled/providerless state, and Final AAS acceptance checks.
- Final AAS tests verify fixed ports `5194`/`8794`, Kernel no-business-logic ownership, controller-managed M1/M2/M3, Bus/Socket enforcement, Module Runtime handlers, Snapshot Assembly registration, disabled providerless AI Shell, and external fetch disabled across the stack.
- Test count increased from `108` to `111`.

Validation:

- `python -m unittest discover -s tests` passed: 111 tests.
- `python -m compileall -q backend` passed.
- `pnpm build` passed.

Correction milestone:

- The architecture is now visible as runtime state, not only as documentation.
- The next work should avoid product expansion until the user explicitly chooses whether to resume product workflow, deepen acceptance tests further, or start packaging/deployment preparation.

## 18. AI Governance Hardening - Policy Registry + Rejection Audit

Status: completed on 2026-07-18.

Implemented:

- `ProviderRegistry` no longer treats provider registration as structurally impossible.
- Provider registration is now decided by `ProviderPolicyEngine`.
- Supported provider policy states exist at the architecture boundary: `DISABLED`, `GOVERNED`, `MAINTENANCE`, `READ_ONLY`, and `ACTIVE`.
- Current local policy remains `DISABLED` + `DENY_ALL`.
- No provider, model, API key, generated output, or external network path was added.
- Rejected AI events now write security audit metadata only:
  - raw prompt field attempts,
  - invalid AI input contract,
  - provider registration attempts,
  - forbidden finance/sovereign/legal/source-governance prompt classes or output types,
  - Human Review bypass fields.
- Security audit explicitly avoids storing raw prompt content, provider secrets, message payloads, headers, or API keys.

Validation:

- `python -m unittest discover -s tests` passed: 113 tests.
- `python -m compileall -q backend` passed.
- `pnpm build` passed.

Decision:

- AI remains a governed disabled capability, not a truth owner and not a runtime dependency.
- Future provider enablement can be policy-driven without redesigning `ProviderRegistry`.

## 19. Architecture Runtime Status Read-Only Hardening

Status: completed on 2026-07-18.

Implemented:

- `/api/architecture/runtime-status` is explicitly a read-only runtime projection.
- The status payload now declares:
  - `projection_type: read_only_runtime_projection`
  - `mutability: read_only_projection`
  - `allowed_methods: ["GET"]`
  - `forbidden_methods: ["POST", "PATCH", "PUT", "DELETE"]`
- Runtime mutation guards are explicit and false:
  - no reboot,
  - no Registry mutation,
  - no Provider Policy mutation,
  - no AI activation,
  - no Module registration,
  - no Heart/Bus/Socket mutation.
- `POST`, `PATCH`, `PUT`, and `DELETE` to `/api/architecture/runtime-status` return `405` with a read-only error envelope.

Validation:

- `python -m unittest discover -s tests` passed: 114 tests.
- `python -m compileall -q backend` passed.
- `pnpm build` passed.

Decision:

- Runtime Status is permanently observability-only.
- Any future administrative action must use a separate governed admin path, not this endpoint.

## 20. Project Run Envelope + Idempotency Guard Hardening

Status: completed on 2026-07-18.

Implemented:

- `BusMessage` now carries top-level `operation_id`, `idempotency_key`, and `input_hash`.
- `aas.bus.message.v1`, Bus Controller, and Socket Contract Layer require those fields before delivery.
- Project Run Workflow passes the sanitized HTTP request envelope into its Bus/Socket message.
- `RunScopedModuleRuntime` binds every module dispatch and final `snapshot.assemble.v1` message to one closed run envelope.
- Run-scoped execution rejects project/run/snapshot mismatches and operation/idempotency/input hash mismatches before module execution.
- Report and Decision Pack projection messages carry deterministic envelope fields while remaining projections from immutable snapshot/report inputs.
- Architecture Runtime Status includes `AAS-FINAL-05E` for the new bus envelope guard.

Validation:

- `python -m unittest tests.test_aas_runtime` passed: 47 tests.
- `python -m unittest discover -s tests` passed: 119 tests.
- `python -m compileall -q backend` passed.
- `pnpm build` passed.

Decision:

- Project Run Workflow remains the closed owner of run identity and idempotency context.
- Modules cannot introduce a different run envelope inside a run-scoped execution path.

## 21. Project Run Pipeline Responsibility Boundary

Status: completed on 2026-07-18.

Implemented:

- The production execution path no longer calls `build_overview()`.
- The application service is named `execute_project_run_pipeline()` and requires a frozen `ProjectRunEnvelope`.
- `ProjectRunWorkflow` owns creation of `run_id`, `snapshot_id`, operation identity, idempotency context, input hash, assigned Heart source, and pipeline policy identity.
- The closed Workflow policy carries the allowed Bus contract sequence; the pipeline rejects a different sequence.
- The pipeline accepts project data through the `ProjectRunDataAccess` interface and creates exactly one `RunScopedModuleRuntime`.
- Module outputs remain sealed in the run session; only `session.assemble()` sends `snapshot.assemble.v1`.
- Workflow rejects pipeline results whose run or snapshot identity differs from the closed envelope.
- `build_overview()` remains a compatibility-only wrapper for existing local parity tests and is not used by the HTTP/Project Run path.

Guards added:

- Calling the pipeline without `ProjectRunEnvelope` is rejected.
- A run-level test proves exactly one `snapshot.assemble.v1` request per pipeline execution.
- The same test proves the delivered module contract order matches the Workflow-owned policy.
- The run envelope input hash is preserved across every operation message.

Validation:

- `python -m unittest discover -s tests` passed: 121 tests.
- `python -m compileall -q backend` passed.
- `pnpm build` passed.

Decision:

- `ProjectRunWorkflow` is the sole owner of the run lifecycle and policy boundary.
- `execute_project_run_pipeline()` is a run-scoped pipeline executor/application service, not an HTTP entry point, truth owner, engine, or snapshot writer.

## 22. AAS Runtime Freeze v1.0

Status: frozen on `2026-07-19T00:22:00+03:00` (`Asia/Riyadh`).

Final guards:

- `build_overview()` carries a real `@deprecated` marker and is restricted to legacy `ProjectRecord` and `Repository` parity fixtures.
- The compatibility wrapper always converts legacy fixtures into `ProjectRunEnvelope` before execution.
- Static architecture tests reject any `build_overview()` reference from HTTP routes or `ProjectRunWorkflow`.
- The pipeline requires a closed `ProjectRunEnvelope` and creates one `RunScopedModuleRuntime` per run.
- Every core engine crosses admitted Bus/Socket contracts; direct engine symbols are absent from the pipeline executor.
- All six engine results and projection support appear in immutable Snapshot lineage.
- `snapshot.assemble.v1` is delivered exactly once per successful run.
- Idempotency replay creates neither a second run record nor a second Snapshot Assembly request.
- A failed module output prevents Snapshot Assembly and persistence of a partial run.
- Report and Decision Pack runtime paths do not reference calculation engines.

Validation:

- `python -m unittest discover -s tests` passed: 130 tests.
- `python -m compileall -q backend` passed.
- `pnpm build` passed.

Frozen surfaces:

- Kernel and Registry.
- Heart Controller and M1/M2/M3 roles.
- Bus Controller and System Bus.
- Socket Contract Layer.
- Module Runtime lifecycle and run-scoped sealing boundary.
- Project Run contract sequence.
- Snapshot Assembly ownership and immutable projection rule.

Change control:

- Changes to a frozen surface require a formal Architectural Change Request using `docs/ASIE-Architectural-Change-Request-Template-v1.0.md`.
- Frozen file hashes and the contract sequence are recorded in `docs/ASIE-AAS-Runtime-Freeze-Manifest-v1.0.json`; Freeze tests fail on unrecorded changes.
- The request must state contract impact, migration, rollback, security constraints, and updated Freeze tests.
- Product features may not silently modify frozen runtime ownership or contract order.
- Remove `build_overview()` in AAS Runtime v1.1 after legacy parity fixtures migrate.

Decision:

- The correction phase is complete.
- Runtime designation is `AAS Runtime Freeze v1.0`.
- Runtime Status remains read-only and exposes the freeze record and ACR requirement.
