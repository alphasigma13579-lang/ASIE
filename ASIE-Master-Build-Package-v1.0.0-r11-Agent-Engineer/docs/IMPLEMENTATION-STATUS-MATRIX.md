# Implementation Status Matrix

This matrix prevents a design document, UI mock, or historical bundle from
being mistaken for executable behavior.

| Area | Status | Evidence / source | Build implication |
| --- | --- | --- | --- |
| AAS Runtime Freeze path | Implemented | `docs/ASIE-AAS-Runtime-Freeze-Manifest-v1.0.json`, `backend/module_runtime.py`, `tests/test_runtime_freeze.py` | Preserve the path and tests |
| Project run orchestration | Implemented | `backend/project_run_workflow.py` | New runs use `ProjectRunWorkflow` |
| Deterministic Finance calculations | Implemented, legacy input semantics | `backend/finance_engine.py` | Do not claim zero-aware readiness yet |
| Scalar `ProjectInputs` flow | Implemented, compatibility path | `src/contracts.ts`, local API project run path | DIB manifest now sits before Finance; legacy path remains for parity |
| Repository assumptions | Partial, semantic metadata added | `backend/repository.py` | Zero reasons and treatment are retained in `metadata_json` |
| Dataset/manual/file intake | Implemented | `backend/datasets.py`, local API dataset routes | Mapping into DIB is still pending |
| Evidence and source ledger | Implemented | `backend/evidence_ledger.py`, `backend/source_registry.py` | Reuse for manifest lineage |
| Simulated Market Intelligence | Implemented as post-study guidance | existing market/intelligence module and contracts | Not an external research provider; keep clearly labeled |
| Product AI interview | Planned | `ACR-DIB-001` | Needs Template/Question registries and bounded orchestration |
| Dynamic Input Blueprint | Partial / governing ACR merged | `backend/input_manifest.py` and `ACR-DIB-001` | Manifest builder exists; editor and registries remain |
| Blueprint item states and zero semantics | Partial | `backend/input_manifest.py`, `backend/finance_engine.py`, repository metadata | Intentional zero and not-applicable are accepted with reasons |
| Approved Input Manifest | Partial | `backend/input_manifest.py`, `backend/asie_local_api.py`, `backend/module_runtime.py` | Finance now receives normalized manifest data; revision persistence remains |
| Per-item Market Intelligence research | Planned / simulated first | `ACR-DIB-001` and market socket contracts | Return results to the same blueprint item |
| Snapshot rerun comparison | Partially implemented | `backend/workspace.py`, snapshot routes | Extend with DIB revision lineage |
| Tenant isolation negative matrix | Implemented | `tests/test_tenant_isolation_matrix.py` | Every sensitive route fails closed cross-tenant; run in CI |
| Server-side PDF renderer | Implemented (image-pinned) | `Dockerfile.backend`, `ASIE_PDF_RENDERER`, `tests/test_pdf_renderer_configuration.py` | Export never uses a client browser |
| Real AI providers | Disabled | runtime policy and local development profile | Requires separate ACR |
| External network research | Disabled | local API/intelligence controls | Requires separate ACR |
| Historical workspace bundles | Reference only | `docs/reference/r11-workspace-materials/` | Do not execute or treat as current policy |
| Client session plumbing (Bearer + organization scope) | Implemented | `src/session.ts`, `src/api.ts` | Token in sessionStorage; 401 returns to sign-in |
| Client auth screens (login, first-run bootstrap, local recovery) | Implemented | `src/AuthScreens.tsx` | Local recovery record only; no external email delivery |
| Organization switcher and team management (client) | Implemented | `src/App.tsx` overlay | Server-side permission enforcement unchanged |
| Organization scope resolution for collection endpoints | Implemented | `backend/asie_local_api.py` `_organization_from_request` | No silent connection drops; clean 400/401/403 |
| Snapshot-bound report exports over HTTP (PDF/DOCX/PPTX) | Implemented | `backend/asie_local_api.py`, `tests/test_report_export_routes.py` | Renderer pinned in image; clean 503 when absent |
| Funding/sector profile browser (client) | Implemented | `src/App.tsx` overlay | Reference catalogs, local only |

## Reading rule

“Implemented” means code and tests exist. “Planned” means the decision and
acceptance criteria exist but runtime behavior is not complete. “Reference only”
means provenance, not source of truth.
