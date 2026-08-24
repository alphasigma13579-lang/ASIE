# FC20-05 baseline gap map

- Baseline: `6247a3fed8bb9cd973d36e47379cbff99d492733`
- Source: `https://github.com/alphasigma13579-lang/ASIE`
- Tree at capture: clean
- Frontend build: pass
- Python baseline: `978 passed, 4 failed, 3 skipped`; three deterministic
  Windows test-portability defects and one transient socket failure that passed
  five isolated repetitions.
- Frozen AAS/Runtime/Snapshot files: all hashes match the freeze manifest.
- Prerequisite rebuild base: `0a0da250ba507589a645c0c43a92c8ef076dedd4`
  after clean license PR #141 and Windows portability PR #142 were independently
  reviewed and merged.

## Status map

| Status | Evidence |
|---|---|
| `EXISTS` | `backend/external_acquisition.py`, `backend/provider_security_control_plane.py`, `backend/live_provider_clients.py`, `backend/tavily_source_admission.py`, `backend/vision2030_kb_sync.py`, `.github/workflows/vision2030-kb-sync.yml`, and their focused tests provide the network, provider, source, hashing, no-op, and stale-tail foundations. |
| `PARTIAL` | FC20-05 is Vision-only, manual, and uses an incomplete source/record lifecycle. Deletion is tail-only; restore and authoritative rebuild are absent. |
| `CONFLICT` | `vision2030_kb_sync.py` calls obsolete Tavily/Pinecone signatures. The workflow is manual while `LIVE-INTEL-002` says monthly. Current Pinecone namespaces are tenant-project scoped while FC20-05 requires a separate shared public corpus. |
| `MISSING` | Unified public-source contract, public namespace, platform-workload write scope, tenant-authorized public read, quarantine, retained canonical versions, audited delete/restore/reindex, complete display evidence, and cross-tenant negative tests. |

## Initial severity decisions

- `High / Defect`: FC20-05 cannot use the current governed provider clients.
- `High / Risk`: reusing a tenant namespace for public knowledge would either
  duplicate the corpus per tenant or invite cross-tenant leakage.
- `High / Risk`: a public write path without an exact platform-workload scope
  would create an over-privileged provider capability.
- `Medium / Defect`: dry-run currently mutates local sync state.
- `Medium / Conflict`: documentation claims a schedule that the workflow does
  not contain.
- `Low / Test defect`: three baseline tests encode non-portable Windows
  assumptions. Product code must not be changed to satisfy them.

Decision before repair: `BLOCK` live activation; `APPROVE` governed offline and
dry-run implementation under ACR-FC20-05.
