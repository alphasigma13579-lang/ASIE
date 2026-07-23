# Implementation Status Matrix

This matrix prevents a design document, UI mock, or historical bundle from
being mistaken for executable behavior.

| Area | Status | Evidence / source | Build implication |
| --- | --- | --- | --- |
| AAS Runtime Freeze path | Implemented | `docs/ASIE-AAS-Runtime-Freeze-Manifest-v1.0.json`, `backend/module_runtime.py`, `tests/test_runtime_freeze.py` | Preserve the path and tests |
| Project run orchestration | Implemented | `backend/project_run_workflow.py` | New runs use `ProjectRunWorkflow` |
| Deterministic Finance calculations | Implemented, legacy input semantics | `backend/finance_engine.py` | Do not claim zero-aware readiness yet |
| Scalar `ProjectInputs` flow | Implemented | `src/contracts.ts`, local API project run path | This is the current gap DIB must replace before Finance |
| Repository assumptions | Implemented, legacy zero handling | `backend/repository.py` | Preserve source records; add semantic states |
| Dataset/manual/file intake | Implemented | `backend/datasets.py`, local API dataset routes | Mapping into DIB is still pending |
| Evidence and source ledger | Implemented | `backend/evidence_ledger.py`, `backend/source_registry.py` | Reuse for manifest lineage |
| Simulated Market Intelligence | Implemented as post-study guidance | existing market/intelligence module and contracts | Not an external research provider; keep clearly labeled |
| Product AI interview | Planned | `ACR-DIB-001` | Needs Template/Question registries and bounded orchestration |
| Dynamic Input Blueprint | Planned / governing ACR merged | `docs/ACR-DIB-001-Dynamic-Input-Blueprint.md` | First DIB runtime milestone |
| Blueprint item states and zero semantics | Planned | `ACR-DIB-001` | Requires backend, repository, Finance, and tests |
| Approved Input Manifest | Planned | `ACR-DIB-001` | Finance must receive manifest-derived inputs only |
| Per-item Market Intelligence research | Planned / simulated first | `ACR-DIB-001` and market socket contracts | Return results to the same blueprint item |
| Snapshot rerun comparison | Partially implemented | `backend/workspace.py`, snapshot routes | Extend with DIB revision lineage |
| Tenant isolation negative matrix | Implemented | `tests/test_tenant_isolation_matrix.py` | Every sensitive route fails closed cross-tenant; run in CI |
| Server-side PDF renderer | Implemented (image-pinned) | `Dockerfile.backend`, `ASIE_PDF_RENDERER`, `tests/test_pdf_renderer_configuration.py` | Export never uses a client browser |
| Real AI providers | Disabled | runtime policy and local development profile | Requires separate ACR |
| External network research | Disabled | local API/intelligence controls | Requires separate ACR |
| Historical workspace bundles | Reference only | `docs/reference/r11-workspace-materials/` | Do not execute or treat as current policy |

## Reading rule

“Implemented” means code and tests exist. “Planned” means the decision and
acceptance criteria exist but runtime behavior is not complete. “Reference only”
means provenance, not source of truth.
