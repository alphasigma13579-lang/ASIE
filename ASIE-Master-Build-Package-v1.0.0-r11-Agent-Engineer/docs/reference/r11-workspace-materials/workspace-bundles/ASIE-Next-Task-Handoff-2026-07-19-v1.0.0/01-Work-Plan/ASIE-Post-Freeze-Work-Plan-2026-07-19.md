# ASIE Post-Freeze Work Plan

## 1. Document Control

- Plan ID: `ASIE-POST-FREEZE-PLAN-2026-07-19`
- Baseline: `AAS Runtime Freeze v1.0`
- Freeze effective at: `2026-07-19T00:22:00+03:00`
- Timezone: `Asia/Riyadh`
- Latest preservation archive: `ASIE-Architecture-Correction-Archive-2026-07-19-v1.1.1.zip`
- Archive SHA-256: `84915e3237f19e1e0efd1f906e982b63e3435459ecfbda664f5093b4c8961ac2`
- Verified baseline: `130` Python tests, Python compile, and frontend build passed.

## 2. Objective

Move from architecture correction into controlled product delivery without reopening or silently changing the frozen AAS Runtime. Work is divided into small packages that can be executed in separate Codex tasks, reviewed independently, and rolled back independently.

The recommended order is:

`Baseline Release -> Frontend Decomposition -> UX/Product Hardening -> Operational Acceptance -> v1.1 Legacy Migration -> v1.1 Wrapper Removal`

## 3. Non-Negotiable Constraints

- Frontend port: `5194` only.
- API port: `8794` only.
- Never use `5173` or `8000`.
- No external network, external API, government API, key, secret, or AI Provider.
- AI owns no controlled number, calculation, legal conclusion, source-governance decision, or Sovereign Verdict.
- Snapshot remains immutable.
- Report, Decision Pack, and UI remain projections of the immutable Snapshot.
- Product work must not change runtime ownership or contract sequence.
- No frozen file may change without an approved Architectural Change Request.
- Preserve all unrelated user changes in the workspace.

## 4. Frozen Surfaces

The following surfaces are frozen by `docs/ASIE-AAS-Runtime-Freeze-Manifest-v1.0.json`:

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
- Project Run pipeline contract sequence.
- Snapshot Assembly ownership and sealing boundary.

Any change to these items must stop normal implementation and start the ACR workflow.

## 5. Work Package PF-00 - New Task Baseline Verification

### Purpose

Ensure every new task starts from the exact frozen baseline and does not operate on a stale or corrupted workspace.

### Steps

- Read this plan completely.
- Read `docs/ASIE-AAS-Runtime-Freeze-Manifest-v1.0.json`.
- Read `docs/ASIE-Architecture-Correction-Plan-2026-07-18.md`, section 22.
- Verify the Freeze timestamp is `2026-07-19T00:22:00+03:00`.
- Run `python -m unittest tests.test_runtime_freeze`.
- Run `python -m unittest discover -s tests`.
- Run `python -m compileall -q backend`.
- Run `pnpm build`.
- Confirm the frontend/API ports remain `5194/8794`.
- Record any pre-existing workspace changes without reverting them.

### Acceptance

- Freeze tests pass.
- Full suite passes with at least `130` tests.
- Python compile passes.
- Frontend build passes.
- Freeze Manifest hashes match.
- No source file is modified during this package.

### Stop Conditions

- Any Freeze hash mismatch.
- Any unexpected production reference to `build_overview()`.
- Any failed architecture acceptance check.
- Any request to modify a frozen surface without an ACR.

## 6. Work Package PF-01 - Release Baseline and Preservation

### Purpose

Create an auditable release point before product development continues.

### Steps

- Confirm the latest archive and its `.sha256.txt` file exist.
- Verify the ZIP SHA-256 against this plan.
- Create a Git commit containing only approved Freeze work and documentation.
- Create an annotated tag: `aas-runtime-v1.0-freeze`.
- Include Freeze timestamp, test count, archive hash, and constraints in the tag message.
- Store a second copy of the ZIP and SHA-256 file on separate local storage.
- Do not publish externally unless separately authorized.

### Deliverables

- One clean Freeze commit.
- One annotated release tag.
- One secondary offline backup.
- A short release note referencing the Freeze Manifest and ACR template.

### Acceptance

- Commit contains no caches, `node_modules`, temporary databases, or secrets.
- Tag resolves to the verified Freeze commit.
- Primary and secondary archive hashes match.
- No runtime source changes occur while packaging.

## 7. Work Package PF-02 - Frontend Structural Decomposition

### Purpose

Reduce maintenance risk in the current frontend without changing product behavior or API contracts. `src/App.tsx` is currently a large orchestration surface and should be decomposed surgically.

### Allowed Scope

- `src/App.tsx`
- `src/api.ts`
- `src/contracts.ts`
- `src/styles.css`
- New files under `src/components`, `src/features`, `src/hooks`, and `src/lib`.
- Frontend-focused tests and local visual verification assets.

### Prohibited Scope

- Frozen backend files.
- Project Run contract sequence.
- Snapshot schema or hashes.
- New backend engines or product truth owners.

### Proposed Structure

```text
src/
  app/
    AppShell.tsx
    navigation.ts
  features/
    dashboard/
    project-wizard/
    evidence/
    readiness/
    run/
    decision/
    architecture-status/
    snapshots/
  components/
    ui/
    status/
    layout/
  hooks/
    useProjectWorkspace.ts
    useProjectRun.ts
  lib/
    formatting.ts
    status.ts
  api.ts
  contracts.ts
  styles.css
```

### Execution Slices

#### PF-02.1 - Pure Utilities

- Extract formatting and status-label functions.
- Add unit tests for deterministic formatting.
- Preserve Arabic labels exactly unless a copy change is separately approved.

#### PF-02.2 - Static Navigation

- Extract application stage definitions and navigation controls.
- Preserve stage IDs and transition behavior.
- Keep the first screen as the working dashboard, not a marketing landing page.

#### PF-02.3 - Read-Only Views

- Extract Architecture Status and Snapshot History first.
- Keep all values read-only.
- Preserve Snapshot identifiers, hashes, and lineage visibility.

#### PF-02.4 - Decision and Report Views

- Extract Decision Pack, report projection, reviews, and action items.
- Confirm they read saved Snapshot projections only.
- Do not move calculations into React.

#### PF-02.5 - Wizard and Evidence Workbench

- Extract the project wizard and evidence workflow last because they own the most state transitions.
- Preserve validation, readiness, dataset review, and evidence-link behavior.
- Keep manual/local import only; no external fetch.

#### PF-02.6 - State Hooks

- Consolidate project/workspace loading into focused hooks.
- Keep server state authoritative.
- Avoid adding a state-management dependency unless measured complexity justifies it.

### Acceptance

- No API endpoint or payload changes.
- No visible workflow regressions.
- `App.tsx` becomes a thin composition shell.
- TypeScript build passes.
- Existing backend tests remain green.
- Desktop and mobile screenshots show no overlap, truncation, or layout shift.
- Frontend runs on `5194`; API runs on `8794`.

## 8. Work Package PF-03 - UX and Product Hardening

### Purpose

Improve clarity, speed, and decision confidence above the frozen Runtime without adding a competing truth path.

### Priority User Journey

`Dashboard -> Project Wizard -> Evidence Readiness -> Run -> Decision -> Snapshot History`

### Tasks

#### PF-03.1 - Dashboard Hierarchy

- Make project state, readiness, latest run, and latest Snapshot the first scan targets.
- Reduce decorative content and keep the interface operational and work-focused.
- Present one dominant next action based on server state.

#### PF-03.2 - Wizard Friction Reduction

- Group inputs by user decision rather than backend field ownership.
- Preserve all controlled numeric inputs and labels.
- Show validation next to the field that caused it.
- Prevent accidental loss when moving between steps.

#### PF-03.3 - Evidence Confidence

- Show source review, dataset quality, transformation lineage, and target coverage as separate concepts.
- Use restrained status colors with text labels.
- Never imply official-source status when external fetch is disabled.

#### PF-03.4 - Run Feedback

- Show a stable pending state while ProjectRunWorkflow executes.
- Prevent duplicate clicks on Run.
- Generate and preserve an idempotency key per user-triggered attempt in the frontend client boundary.
- Do not expose internal module controls to the user.

#### PF-03.5 - Decision Clarity

- Separate Sovereign Verdict, advisory personas, risks, execution plan, and human review.
- Keep advisory consensus visually subordinate to the deterministic verdict.
- Show Snapshot ID and integrity status near every decision projection.

#### PF-03.6 - Accessibility and Responsive QA

- Verify keyboard navigation and visible focus.
- Verify Arabic RTL reading order.
- Verify labels and long Arabic text on narrow mobile widths.
- Verify color contrast and non-color status cues.
- Verify loading, empty, blocked, stale, and error states.

### Acceptance

- No finance, risk, sector, verdict, or readiness calculation exists in React.
- Every displayed controlled value traces to API/Snapshot data.
- No duplicate Run request is produced by repeated interaction.
- All expected empty/error/loading states are implemented.
- No text overlap at mobile or desktop widths.
- No nested cards or marketing-style hero treatment inside the operational application.

## 9. Work Package PF-04 - Operational Acceptance

### Purpose

Prove the complete local product workflow on the frozen Runtime before considering v1.1.

### Test Matrix

- Create a project with incomplete inputs.
- Confirm readiness blockers appear without a Run.
- Complete financial and sector inputs.
- Add local source review and dataset evidence.
- Verify dataset quality and transformation lineage.
- Execute one Project Run.
- Repeat the same idempotent request and confirm no second Snapshot.
- Open Report and Decision Pack from the saved Snapshot.
- Add a human review overlay and confirm Snapshot hash is unchanged.
- Create a second legitimate run after changing project inputs.
- Compare the two immutable Snapshots.
- Confirm Runtime Status remains read-only.

### Viewports

- Desktop: `1440 x 900`.
- Compact desktop/tablet: `1024 x 768`.
- Mobile: `390 x 844`.

### Acceptance

- All workflows complete using ports `5194/8794`.
- No request is made to an external host.
- No console error or failed local request remains unexplained.
- Snapshot lineage contains all required outputs.
- Report and Decision Pack match the selected Snapshot.
- Visual screenshots are retained as release evidence.

## 10. Work Package PF-05 - Legacy Parity Fixture Migration

### Purpose

Prepare AAS Runtime v1.1 by removing test dependence on the deprecated compatibility wrapper without changing Runtime behavior yet.

### Scope

- Tests and test fixtures only.
- No frozen runtime source changes in this package.

### Steps

- Add a dedicated parity fixture factory that creates `ProjectRunEnvelope` explicitly.
- Replace every test call to `api.build_overview()` with `execute_project_run_pipeline()` through the fixture factory.
- Give every fixture explicit `operation_id`, `idempotency_key`, `input_hash`, `run_id`, `snapshot_id`, and source Heart.
- Preserve all existing expected values and parity assertions.
- Add a static test proving tests no longer reference `build_overview()`.
- Keep the deprecated wrapper in production code until this package is fully green.

### Acceptance

- Zero test references to `build_overview()`.
- All parity assertions remain unchanged and pass.
- Full suite passes.
- Freeze Manifest remains unchanged because no frozen runtime file changed.
- No production behavior changes.

## 11. Work Package PF-06 - AAS Runtime v1.1 Wrapper Removal

### Purpose

Remove `build_overview()` only after PF-05 completes.

### Mandatory ACR

- Create an ACR from `docs/ASIE-Architectural-Change-Request-Template-v1.0.md`.
- Proposed version: `AAS Runtime v1.1`.
- State that the change removes a deprecated compatibility entry point and does not alter contract order or truth ownership.
- Include rollback and test evidence.
- Obtain explicit approval before editing.

### Steps After Approval

- Remove `build_overview()`.
- Remove its deprecation constants if unused.
- Confirm HTTP and Workflow still call only `execute_project_run_pipeline()`.
- Update Runtime Freeze status to v1.1.
- Recompute hashes only for intentionally changed frozen files.
- Create a new Freeze Manifest; never rewrite the v1.0 historical manifest.
- Update architecture documentation and map.
- Run all Freeze, backend, and frontend checks.
- Produce a new signed/checksummed preservation archive.

### Acceptance

- `rg "build_overview" backend tests` returns no executable reference.
- Project Run HTTP behavior is unchanged.
- Contract sequence is unchanged.
- Snapshot hashes remain deterministic for equivalent fixture inputs.
- Full suite passes.
- New v1.1 Manifest and archive hashes verify.
- v1.0 archive and Manifest remain preserved.

## 12. Work Package PF-07 - Release Closure

### Steps

- Run the complete test/build matrix.
- Review changed files against the approved package scope.
- Verify no secret, external URL, generated cache, or local database entered the release.
- Update release notes with behavior changes and unchanged constraints.
- Generate a new archive, `ARCHIVE-MANIFEST.json`, `SHA256SUMS.txt`, and ZIP SHA-256 file.
- Verify the archive by reopening it and checking all required entries.
- Create the release commit and annotated tag.

### Definition of Done

- Required functionality is complete.
- No frozen boundary changed without ACR.
- Tests and builds pass.
- Visual acceptance passes where UI changed.
- Documentation matches implementation.
- Archive hashes verify with zero failures.
- The next task can start without relying on conversation history.

## 13. Risk Register

| Risk | Severity | Prevention | Detection |
|---|---:|---|---|
| Future developer calls deprecated wrapper | High | PF-05 migration and PF-06 removal | AST/Freeze tests |
| Frontend refactor changes controlled values | High | API remains authoritative; no calculations in React | Snapshot parity tests and UI trace review |
| Split orchestration returns | Critical | Workflow-owned envelope and contract sequence | Freeze Manifest and Runtime tests |
| Duplicate Run creates duplicate Snapshot | Critical | idempotency key and disabled repeated action | Idempotency replay tests |
| Partial Snapshot persists after failure | Critical | sealed outputs and atomic assembly | Failure injection tests |
| UI implies official external data | High | explicit local/demo labels | Content and source-policy QA |
| Frozen file changes accidentally | Critical | SHA-256 Freeze Manifest | `test_runtime_freeze` |
| Large frontend decomposition regresses flows | High | small extraction slices | build, screenshots, end-to-end matrix |
| Historical v1.0 evidence is overwritten | High | create new manifests and archives by version | archive existence and checksum audit |

## 14. Recommended Task Boundaries

Run each item as a separate Codex task:

1. `Task 1 - PF-00 + PF-01: Verify and create the release baseline.`
2. `Task 2 - PF-02.1 to PF-02.3: Extract utilities, navigation, and read-only views.`
3. `Task 3 - PF-02.4 to PF-02.6: Extract decision, wizard, evidence, and state hooks.`
4. `Task 4 - PF-03: UX and responsive hardening.`
5. `Task 5 - PF-04: Operational and visual acceptance.`
6. `Task 6 - PF-05: Migrate legacy parity fixtures.`
7. `Task 7 - PF-06: Prepare ACR and wait for approval.`
8. `Task 8 - PF-06 implementation + PF-07 release closure after approval.`

Do not combine PF-05 and PF-06. The test migration must prove independence from the wrapper before frozen production code is changed.

## 15. New Task Starter Prompt

```text
ابدأ تنفيذ Work Package PF-00 ثم PF-01 من الوثيقة:
docs/ASIE-Post-Freeze-Work-Plan-2026-07-19.md

Baseline:
- AAS Runtime Freeze v1.0
- Freeze time: 2026-07-19T00:22:00+03:00 Asia/Riyadh
- 130 tests passed
- Latest archive: ASIE-Architecture-Correction-Archive-2026-07-19-v1.1.1.zip
- ZIP SHA-256: 84915e3237f19e1e0efd1f906e982b63e3435459ecfbda664f5093b4c8961ac2

Rules:
- Read the plan and Freeze Manifest completely before any edit.
- Do not modify frozen Runtime files.
- Frontend 5194 and API 8794 only.
- No external network, keys, government APIs, or AI Provider.
- Snapshot immutable; Report/Decision Pack/UI are Snapshot projections only.
- Preserve existing user changes.
- Report findings and verification evidence before release closure.
```

## 16. Recommended Immediate Next Action

Start a new task with `PF-00 + PF-01` only. This creates a clean, auditable release baseline before any frontend decomposition or v1.1 migration begins.
