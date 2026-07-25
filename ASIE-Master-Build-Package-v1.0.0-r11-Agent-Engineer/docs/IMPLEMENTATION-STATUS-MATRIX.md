# Implementation Status Matrix

This matrix prevents a design document, UI mock, or historical bundle from being mistaken for executable behavior.

| Area | Status | Evidence / source | Build implication |
| --- | --- | --- | --- |
| AAS Runtime Freeze path | Implemented / unchanged | `docs/ASIE-AAS-Runtime-Freeze-Manifest-v1.0.json`, `tests/test_runtime_freeze.py` | All frozen file hashes remain binding |
| Project run orchestration | Implemented | `backend/project_run_workflow.py` | Runs use the existing canonical workflow |
| Project Profile and governed project classification | Implemented | `src/DIBWorkspace.tsx`, `backend/dib_registry.py` | Location, sector, stage, and activity select the governed template |
| Template Registry | Implemented | `backend/dib_registry.py`, `src/dibRegistry.ts` | Deterministic templates; no provider dependency |
| Question Registry / Product AI Interview | Implemented, bounded local mode | `backend/dib_registry.py`, `src/DIBWorkspace.tsx` | Decisive registry questions only; AI providers remain disabled |
| Idea-only path | Implemented | `src/DIBWorkspace.tsx`, `backend/input_manifest.py` | Produces the same DIB used by the data path |
| Manual/CSV/XLSX intake | Implemented | `backend/datasets.py`, `backend/dib_intake.py`, DIB UI | Imported values remain review-required |
| Text PDF and supplier quote intake | Implemented | `backend/datasets.py::extract_pdf_text`, `quote_rows_from_text` | No OCR or external service; scanned PDFs fail closed to manual mapping |
| File-to-template item mapping | Implemented | `backend/dib_intake.py`, `src/dibRegistry.ts` | Ambiguous mappings retain lower confidence and require review |
| Dynamic Input Blueprint model/editor | Implemented | `backend/input_manifest.py`, `src/DIBWorkspace.tsx` | Supports governed and custom line items |
| Blueprint item states and zero semantics | Implemented | `backend/input_manifest.py`, `backend/dib_finance_gate.py` | Zero is valid only with state, reason, and approval |
| Per-item source/evidence/treatment/approval | Implemented | DIB item model and UI | Lineage remains attached to the same item |
| Per-item Market Intelligence research | Implemented, local governed mode | `backend/market_intelligence.py`, `backend/intelligence_prerun_service.py` | Bus/Socket only; external fetch disabled |
| P25-P75, weighted median, outlier report | Implemented | `backend/market_intelligence.py` | Candidate assumptions only |
| Client accept/reject/edit loop | Implemented | `src/DIBWorkspace.tsx` | Rejection returns to the same item |
| Approved Input Manifest | Implemented | `backend/input_manifest.py`, `src/DIBWorkspace.tsx` | Manifest and revision identity are persisted in project inputs |
| Manifest Validation Gate before Finance | Implemented | `backend/dib_finance_gate.py`, `backend/dib_runtime_extension.py` | Finance adapter sends only manifest-derived normalized values to calculations |
| Deterministic Finance calculations | Implemented | `backend/finance_engine.py` through DIB gate | No AI-owned numbers |
| Evidence and source ledger | Implemented | `backend/evidence_ledger.py`, `backend/source_registry.py` | Manifest evidence references remain traceable |
| Snapshot Assembly and immutable persistence | Implemented | frozen Snapshot Assembly and repository snapshot persistence | Approved manifest is sealed inside the Finance module output |
| Draft Revision lineage | Implemented | DIB UI `blueprint_revisions` and `blueprint.revision.v1` | Every save creates a new immutable revision record |
| Rerun and Snapshot comparison | Implemented | existing run/compare APIs + DIB UI | Old Snapshots are not mutated |
| Tenant isolation negative matrix | Implemented | `tests/test_tenant_isolation_matrix.py` | Sensitive routes fail closed cross-tenant |
| Server-side report exports | Implemented | report routes and renderer tests | Snapshot-bound output only |
| Real AI providers | Disabled by governance, not a missing DIB function | AI shell policy | Separate ACR required |
| External network research | Disabled by governance, not a missing DIB function | Market evidence pack flags and runtime guards | Separate source-activation ACR required |
| Historical workspace bundles | Reference only | `docs/reference/` | Never direct implementation |

## Reading rule

“Implemented” means code and tests exist. “Disabled by governance” is an intentional security state, not an unfinished DIB capability. The DIB completion gate is enforced by `tools/audit_dib_runtime.py` and `tests/test_dib_runtime_audit.py`.
