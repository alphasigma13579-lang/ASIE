# ACR-FC20-10 — consented project-location input

## Decision and authority

Date: 2026-08-28. Baseline: `main@42603fc18ce387af8260b931eeeeba1bba9a338f`.
Authority: the user's approved full, free, invitation-only live-beta implementation plan and explicit continuation. This ACR authorizes only the providerless consent-input slice described below. It does not clear FC20-10 predecessors, activate Google, authorize deployment, or certify live-beta readiness. `docs/PROGRAM-CLOSE-10-EMERGENCY-REMEDIATION-CONSOLIDATION-AND-REBASELINE-2026-07-29.md` and `/EMERGENCY-RELEASE-FREEZE.json` remain the current program-state authorities; `/FOUNDATION-COMPLETE-20.json` is dated evidence only. FC20-10 remains BLOCKED_BY_PREDECESSOR.

## Verified baseline and gap map

| Capability | State | Evidence at baseline |
| --- | --- | --- |
| Saudi region/city/district and manual coordinates | EXISTS | `src/App.tsx` location wizard; `tests/test_saudi_project_intake_contract.py` |
| Browser/server Google key separation | EXISTS | PR #146; configuration only, not connectivity proof |
| User-triggered GPS and explicit confirmation | MISSING | No geolocation request in App; existing test forbids automatic device location |
| Structured address from Google | MISSING | Google client has forward geocoding; no authenticated location API or reverse geocoding |
| Real competitor map | MISSING | `src/LiveCockpit.tsx` explicitly renders demonstration competitors |
| Browser interaction tests | MISSING | Existing `tools/e2e_beta_flow.py` tests HTTP APIs, not browser consent |

Baseline PR #146 head `12a15af94d37b0314f04e30effd69bbfa249058b`: ASIE CI run 33034678456 (1041 tests, frontend build), LIVE-INTEL 33034678363, cross-platform 33034678391 passed. Main has the same tree. Post-merge evidence gate 33191425016 and cross-platform 33191424966 passed; governed freeze 33191424856 rejected unfreeze because `foundation_completion_program_cleared` is still false. Its frozen hashes remained unchanged. This existing governance failure must not be hidden or weakened.

## One bounded change

Add a consented location control to the existing first wizard step. Keep the existing manual inputs and structured address fields. No API, provider, Finance, Snapshot, Decision Council, AAS, billing, or project-persistence contract is changed.

Data flow:

`explicit user action -> browser permission -> transient candidate -> explicit confirmation -> existing form latitude/longitude -> existing reviewed project-save flow`

The browser may use OS/network-assisted geolocation according to its permission policy. CI must emulate this API; it must never request a real device position.

| Boundary | Rule |
| --- | --- |
| Before action | No geolocation request, permission query, polling, or watch |
| Candidate | Component memory only; bounded numeric coordinates and non-negative finite accuracy |
| Confirmation | Transfer only latitude/longitude atomically to the parent form |
| Cancel/retry/unmount | Invalidate late callbacks and discard candidate; getCurrentPosition itself is not cancellable |
| Denied/unavailable/timeout/insecure | Arabic explanation, no raw error text; manual entry remains available |
| Persistence | No storage, telemetry, API, or logging of candidate/accuracy |
| Project/tenant | Key the control by user/organization/project so context changes discard candidates and pending callbacks. No new persistence route or privilege; do not invent a tenant scope before a project exists |

Coordinates do not establish a Saudi administrative address. Users still select the region/city and check that the location represents their project. Reverse geocoding/address reconciliation, an authenticated location API, real maps, competitor search, provider checks, and genuine cross-tenant integration tests are separate remaining slices of the same overall goal, not claimed here.

## Experience contract

- Reuse the existing RTL wizard and button styles; no redesign or new navigation layer.
- Explicit request, pending, candidate, confirmed, denied, timeout, unavailable and cancelled states.
- Show approximate accuracy in metres; do not imply exact GPS certainty.
- Keyboard-operable buttons, descriptive labels, live status announcements; manual fields remain visible.
- No coordinate/accuracy analytics. Success metrics for this slice are behavioral acceptance checks, not user telemetry.
- Zero provider calls and zero recurring work; O(1) transient state and callback processing.
- No launch flag is changed. Browser GPS requires a secure context at runtime; real-device/hosted validation remains outstanding.

## Acceptance and non-regression evidence

A dedicated GitHub Actions browser job must test the real React component in Chromium, including: no automatic request; no commit before confirmation; valid coordinates and accuracy; permission denial; timeout/unavailable; invalid coordinates/accuracy; cancellation and stale callbacks; retry isolation; unmount; user/organization/project context reset; secure-context/unavailable fallback; keyboard confirmation; and mobile RTL layout with manual inputs available. Outbound browser requests must be limited to the loopback test server and unexpected requests fail the suite. Test-only fixtures are outside the production Vite entry graph and must not appear in dist.

Static intake tests remain and add integration checks; they are not substituted for browser evidence. Run full baseline tests, frontend build, frozen-file comparison, cross-platform CI, CodeRabbit, Copilot, and independent exact-head review before merge. A new commit restarts those gates. No readiness claim from a mocked browser test: it proves UI/control behavior only.

## Rollback and next handoff

This slice has no database migration or stored-data transformation. Revert its PR to restore the pre-GPS wizard and manual-only path. Preserve user-saved projects. Follow-up API/map work must extend this ACR with trusted tenant/project scope, canonical route registration, Google content-retention restrictions and negative security tests before implementation. Do not use a platform preflight scope for a tenant request.

## PR #147 review remediation — session lifetime boundary (2026-08-28)

Baseline for this repair: main `42603fc18ce387af8260b931eeeeba1bba9a338f`, PR head
`ba64f0458d93637d79c1b7d9a0eb822458c43d00`. User explicitly authorized continuation
after the one-time review stopped. CodeRabbit review 5053614646 requested changes.
This addendum authorizes only the following defensive frontend repair and tests;
it does not change release, provider, Finance, Snapshot, Council or AAS authority.

### Finding, threat and scope
F-147-01 is a High-priority frontend context-integrity defect: App's parent form
survives organization changes; a child GPS remount clears only unconfirmed
candidates. The old form can subsequently be saved with the new organization
header. The missing parent reset predates #147. Stale successful/401 responses
may also cross the session lifetime. This is a source-confirmed path, not a
claim that a real customer leak was observed.

Assets: unsaved coordinates, form fields, project/evidence/result state and
session-bound responses. Trust boundary: user/session/organization A to B in one
tab. Controls: reset the App workspace on effective identity/organization change;
invalidate old asynchronous results before they can populate current state or
expire a newer session; same-context navigation must retain ordinary drafts.
No server-side object authorization is weakened or replaced by these UI controls.

### Test-first repair and allowlist
Add a fixture importing the actual App and intercept APIs in Chromium. Prove
same-organization preservation, organization switch clearing, logout/login,
expiry/login, delayed success, delayed 401, and A-B-A stale-response rejection.
Do not call real backend/provider services or geolocation. First commit tests
only and record the failing CI evidence; repair implementation only after
distinguishing real assertion failures from harness failures.

Repair allowlist: `src/App.tsx`, `src/session.ts`, `src/api.ts`, the browser
test/fixture files under `tools/`, the existing browser workflow, directly
relevant regression tests, and this ACR. API routes/payloads and `src/contracts.ts`
remain unchanged. Source-policy, runtime and backend financial logic are out of
scope. No migration or stored-project deletion: rollback is a code revert.

After every implementation commit: focused browser tests, full build/test,
frozen-file comparison, cross-platform and evidence gates, then both reviewers
and independent exact-head review. Stop commits while reviewers run. Record
evidence in the PR rather than claiming success before CI returns. Remaining
whole-platform surfaces outside App, genuine hosted GPS, address/map/competitor
integration and live acceptance are not certified by these controlled tests.

### Reproduction evidence
Test-only head `92c7df6445549090c78e2dd10a630b7c8de702ad`, browser run
[33197520971](https://github.com/alphasigma13579-lang/ASIE/actions/runs/33197520971):
the existing 12 consent tests passed; the 7 new App tests produced **6 assertion
failures and 1 passing same-context control**. Confirmed latitude 24.7136 survived
organization switch, logout/login and expiry/login; stale successful responses
were fulfilled after A-B and A-B-A; a stale 401 cleared the active session token.
Production build and fixture-exclusion checks passed before those assertions.
No production code had changed in this test-only commit.

### Repair implementation
A monotonic session revision now keys the App workspace. An effective token or
organization change clears its in-memory descendants, while same-context
navigation retains drafts. A new token clears the previous organization before
the normal server identity probe selects membership. API replies are checked
both after response headers and after JSON/blob consumption; stale replies
cannot publish data, open an old document, or invalidate a newer session. A
delayed logout also checks its lifetime. No transport, public API shape, backend
authorization, stored project, or frozen file is changed. Passing repair evidence
is pending CI and exact-head review; the test-only failures are retained above.
