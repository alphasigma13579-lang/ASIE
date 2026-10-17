# ASIE Canonical API & Output Register

## سجل مسارات API ومفاتيح المخرجات المعتمدة

| البند | القيمة |
|---|---|
| المعرّف | `ASIE-CANONICAL-API-OUTPUT-REGISTER-v1.0.0` |
| الحالة | `CONTROLLED BASELINE` |
| تاريخ النفاذ | `2026-07-25` — `Asia/Riyadh` |
| النطاق | API الحي، ربط TypeScript، مفاتيح Snapshot المختومة، وحقول Projection العامة |
| سلطة API | `backend/asie_local_api.py` |
| سلطة عميل الواجهة | `src/api.ts` |
| سلطة مخرجات Snapshot | `backend/snapshot_assembly.py` |
| السجل الآلي | `registry/asie-canonical-api-output.v1.json` |
| اختبار CI | `tests/test_canonical_api_output.py` |

## 1. القرار التنفيذي

لا يعاد تسمية أي مسار API أو مفتاح Snapshot مختوم أو حقل Projection عام قائم أثناء مرحلة الإطلاق. أي تغيير كاسر يحتاج إصدارًا جديدًا وخطة ترحيل واختبارات توافق.

التمييز المعتمد هو:

- **Sealed Output Key:** مفتاح داخلي يحدد مخرج الوحدة داخل `Snapshot Assembly`.
- **Module Payload Key:** المفتاح داخل مخرج الوحدة المختوم.
- **Public Projection Key:** الاسم العام الذي تقرؤه API وTypeScript والتقارير والواجهة.
- **Display Label:** النص الظاهر للمستخدم، ولا يستخدم بوصفه معرفًا برمجيًا.

## 2. خريطة المخرجات المختومة إلى الحقول العامة

| Sealed Output Key | Module | Result Contract | Module Payload | Public Projection |
|---|---|---|---|---|
| `finance_result` | `module.finance` | `finance.result.v1` | `finance`, `blockers` | `finance`, `blockers`, `monte_carlo`, `kpis` |
| `evidence_ledger` | `module.evidence_ledger` | `evidence.ledger.v1` | `evidence_ledger` | `evidence_ledger` |
| `sector_intelligence` | `module.sector_intelligence` | `sector.intelligence.v1` | `sector_intelligence` | `sector_intelligence` |
| `decision_result` | `module.decision_council` | `decision.council.v1` | `decision_council` | `decision_council`, `decision`, `personas` |
| `risk_result` | `module.risk_engine` | `risk.register.v1` | `risk_register`, `risk_advisory_summary` | `risk_register`, `risk_advisory_summary` |
| `execution_result` | `module.execution_engine` | `execution.plan.v1` | `execution_plan` | `execution_plan` |

وبذلك فإن:

- `decision_result` ليس اسمًا بديلًا عن `decision_council`؛ الأول مفتاح تجميع داخلي والثاني مخرج المجال العام.
- `risk_result` ليس اسمًا بديلًا عن `risk_register`؛ الأول وعاء Snapshot داخلي، بينما المخرج يحتوي `risk_register` و`risk_advisory_summary`.
- `execution_result` مفتاح داخلي، و`execution_plan` هو المخرج العام.

## 3. مسارات API

السجل الآلي يحتوي جميع الدوال المصدّرة من `src/api.ts` ويربط كل دالة بـ:

- HTTP Method.
- Path Template.
- دليل وجود داخل Handler الخلفي.
- Response Contract أو Response Shape.

يفشل CI عندما يحدث أحد الآتي:

1. إضافة دالة API أمامية دون تسجيلها.
2. بقاء دالة مسجلة بعد حذفها.
3. تسجيل مسار دون دليل داخل Handler الخاص بالطريقة نفسها.
4. اختلاف طريقة HTTP بين الواجهة والسجل.
5. اختلاف أجزاء المسار الثابتة بين الدالة والسجل.
6. تكرار `route_id` أو تكرار هوية `method + path`.

## 4. تصحيح TypeScript العام

ثبت التدقيق أن Backend يصدر الحقول التالية فعلًا:

- `ProjectOverview.risk_advisory_summary`.
- `SnapshotReport.risk_advisory_summary`.
- `SnapshotReport.funder_report`.
- `SnapshotReportView.risk_advisory_summary`.
- `SnapshotReportView.funder_report`.

كانت هذه الحقول غير ممثلة بالكامل في سطح TypeScript. أضيفت بصورة غير كاسرة عبر:

```text
src/contracts.canonical.d.ts
```

ولا يغير ذلك JSON أو Runtime أو العقود المجمدة؛ بل يجعل TypeScript يصف المخرجات الموجودة فعليًا.

## 5. المسميات الظاهرة

يفحص التدقيق الأسطح النشطة الأساسية للتأكد من عدم استخدام الأسماء الممنوعة، مع بقاء Runtime Labels التقنية كما هي. الأسماء المعمارية العامة المعتمدة تظل:

- `Finance Engine` — المحرك المالي.
- `Decision Council` — مجلس القرار.
- `Risk Engine` — محرك المخاطر.
- `Execution Engine` — محرك التنفيذ.
- `AI Integration Shell` — غلاف تكامل الذكاء الاصطناعي.
- `Snapshot Assembly` — تجميع اللقطة.

## 6. حدود السلطة

هذا السجل لا:

- يغير AAS Runtime Freeze.
- يعيد تسمية Contract أو Socket أو Module ID.
- يغير ترتيب المحركات.
- يغير Snapshot hashes السابقة.
- يفعّل AI أو الشبكة الخارجية.
- يحول وثائق `docs/reference/**` إلى مصدر تنفيذ.

## 7. بوابة الإغلاق

يعد تدقيق API والمخرجات مغلقًا عندما تكون النتيجة:

```text
Frontend API Function Inventory = MATCH
Backend Method/Path Evidence = MATCH
Sealed Output Mapping = MATCH
Public Projection Mapping = MATCH
TypeScript Public Fields = MATCH
Active Surface Labels = MATCH
Frontend Build = PASS
Backend Compile = PASS
Python Tests = PASS
```


## Customer recovery contract extension — 2026-10-14

Authority: accepted FC20-12 customer recovery design, registered STOP17/SCOPE18 and RESUME19. This section registers the implementation interface; it does not grant release, provider, live-database or merge authority.

- `customer.recovery.v1` is a current-read projection on the existing project workspace, evidence-ledger and DIB session routes. It is not a second source of business truth. The machine-readable `customer_recovery_extension` lists exact fields and consumers.
- `current_recovery` describes the current draft. The existing historical `remediation` and sealed Snapshot readiness remain unchanged. The default workflow readiness result does not include customer navigation fields.
- Each item identifies its source scope/version, requirement, safe explanation key, exact target and required action permission. A displayed permission never replaces HTTP authorization. Unknown mappings remain open for owner review.
- Project/evidence version markers detect stale editing context; they do not claim atomic concurrency guarantees. Evidence binding versions include current target/dependency material; source-review targets bind the source review itself.
- Evidence corrections use existing path-bound dataset, transformation, source and project writers. Dataset and transformation parent identity is verified. Reference-only sources are never offered review-to-enable actions. Unlinked draft data does not create required project obligations.

### Versioned DIB write on the existing route

`POST /api/dib/sessions/{session_id}/blueprints` accepts `contract_id=dib.blueprint.write.v2` with `expected_original={session_id,project_id,blueprint_id,revision,payload_hash}` for updates. These values come from the exact stored GET response, not a browser-computed hash or a last-second automatic rebase.

Every update reloads and compares the origin inside the existing persistence transaction. A new server-owned Blueprint identity/revision preserves the prior row and invalidates the previous Manifest/Gate pointers. Missing origins and conflicts fail with 409 and no success event or partial mutation. First creation checks absence atomically and retains legacy-create compatibility. Legacy unversioned updates intentionally cease to be accepted.

The three existing engineering writers and the customer item editor share this same persistence guard. A customer item decision identifies the stored item; it cannot supply an evidence pack or assert verified/reviewer authority. File-import provenance remains explicitly unverified. Intentional zero and not-applicable require an explicit reason. Neither a preview nor an item-decision response counts as persistence: success requires save and reread of the same revision and target.

### Display capability ownership

The current unconditional pre-run denial owns the F01A disabled display fact. Temporary failure requires a classified result from the actual operation owner; unknown exceptions retain an unclassified safe error. Product & Engineering owns separately versioned `not_built`/`coming_soon` declarations in release_info. No such declaration is invented merely because a feature is missing; the current declaration collection is empty. The customer projection exposes only its allowlisted fields, not administrative SBOM/release details or runtime enablement flags.

### Customer behavior and acceptance

The client preserves the original source reference and unsaved edit buffer, binds asynchronous responses to organization/project/session lifetimes, retains work on save failure/conflict and verifies the exact requirement after reread. Browser storage failure is disclosed; in-memory retention does not claim refresh durability. Navigation uses allowlisted target kinds and fields, not payload URLs or CSS selectors. Arabic and English customer text does not display origin hashes, protocol identifiers or raw exceptions. Sanad opens the selected target and returns focus to its origin. Voice remains deferred.

The registered focused tests cover isolation, safe errors, source-specific writes, CAS/rollback/legacy compatibility, predicate preservation, capability ownership and actual browser interaction. Browser evidence is synthetic and does not authorize production startup placement or live-data use.


## Dataset submission provenance extension — 2026-10-15

Authority: accepted customer Dataset provenance amendment #210, STOP20/SCOPE21 registration #211 and effective RESUME22 #212. The machine-readable `dataset_provenance_extension` records the interface on the existing Dataset routes and notes column. No new route, database schema or business-truth store is introduced.

Authenticated creation accepts an explicit `intended_use` and a current authorized `project_id`. The server records version 1 provenance with immutable organization, actual creator, initial project and creation time. Customer-study records have an empty, non-null source ID and cannot claim a platform source. Collection creation rejects a known Dataset ID; path-bound review cannot create or reparent a record. Nested provenance and raw notes_json input are rejected. Legacy zero-user external imports remain legacy; they cannot obtain customer provenance.

Valid customer-study provenance removes only the source, license-reference and terms-hash requirements. Classification, privacy, attribution, actual quality and human review remain required. Missing, malformed or legacy provenance receives no exemption and is never silently rewritten. Same-organization authorized reuse is retained; initial project is an audit fact, not a new exclusive project lock. Public visibility and API access are not reuse permission.

On an existing record, supplying rows, json_rows or csv_text explicitly replaces content. Malformed shapes fail before mutation. A valid empty replacement stores zero rows; the quality gate still blocks its use. Even identical resubmission conservatively requires fresh review because previews and aggregate profiles cannot prove full-content equality. Replacement clears Dataset approval and all dependent transformation/link reviews in the same write transaction. Metadata-only edits preserve them. Stored transformation outputs are not automatically recalculated, and historical Snapshots remain immutable. HTTP link admission rechecks its admitted Dataset revision and approved state inside the link writer transaction.

The existing Repository reads sources, Dataset records, transformations and links in one SQLite read transaction, preventing combinations of approvals from different committed states. The exact existing Manifest overlay retains its Manifest-derived assumptions and delegates only evidence to its documented Repository owner. There is no fallback to incoherent reads.

The current-run evidence register receives the current project's authoritative organization and carries consuming_context to ledger fallback evaluation. Customer evidence has its own origin label, no official source association or source-review confidence credit; confidence weights and sector predicates are unchanged. The ordinary customer import uses the existing route with customer_study intent. Legacy/external proof metadata remains platform-managed in an explicitly entered authorized administrative surface, while other authorized metadata edits remain available.

This interface implementation is being validated using synthetic data and disposable databases. It does not establish browser acceptance, production startup suitability, deployment or application merge approval.
