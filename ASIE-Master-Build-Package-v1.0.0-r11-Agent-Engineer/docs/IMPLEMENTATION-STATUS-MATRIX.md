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
| Real AI providers | Disabled | runtime policy and local development profile | Requires separate ACR |
| External network research | Disabled | local API/intelligence controls | Requires separate ACR |
| Historical workspace bundles | Reference only | `docs/reference/r11-workspace-materials/` | Do not execute or treat as current policy |

## Reading rule

“Implemented” means code and tests exist. “Planned” means the decision and
acceptance criteria exist but runtime behavior is not complete. “Reference only”
means provenance, not source of truth.
