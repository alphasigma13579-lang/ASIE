# AlphaSigma Intelligence Engine — ASIE

This directory is the canonical runnable workspace for the ASIE repository.

## Read first

1. [`AGENTS.md`](AGENTS.md) — engineering rules and frozen runtime boundaries.
2. [`docs/PROJECT-ORIENTATION.md`](docs/PROJECT-ORIENTATION.md) — product paths and current build direction.
3. [`docs/IMPLEMENTATION-STATUS-MATRIX.md`](docs/IMPLEMENTATION-STATUS-MATRIX.md) — implemented, planned, disabled, and reference-only capabilities.
4. [`docs/ASIE-CANONICAL-DOCUMENT-REGISTER-v1.1.0.json`](docs/ASIE-CANONICAL-DOCUMENT-REGISTER-v1.1.0.json) — document authority.
5. [`docs/ASIE-CANONICAL-TERMINOLOGY-REGISTER-v1.0.0.md`](docs/ASIE-CANONICAL-TERMINOLOGY-REGISTER-v1.0.0.md) — architectural names and runtime identifiers.
6. [`docs/ASIE-CANONICAL-API-OUTPUT-REGISTER-v1.0.0.md`](docs/ASIE-CANONICAL-API-OUTPUT-REGISTER-v1.0.0.md) — HTTP routes, sealed output keys, and public projection names.

## Runtime boundary

```text
Kernel
→ Heart Controller
→ Hearts M1 / M2 / M3
→ Bus Controller
→ ASIE System Bus
→ Socket Contract Layer
→ Module Runtime
→ Snapshot Assembly
```

The AAS Runtime Freeze v1.0 remains binding. Do not rename active Contract IDs, Socket IDs, Module IDs, API paths, sealed output keys, or public projection keys in place.

## Local verification

```bash
corepack enable
pnpm install --frozen-lockfile
pnpm build
python -m compileall -q backend
python -m unittest discover -s tests
```

Historical material under `docs/reference/` and superseded material under `docs/archive/` are provenance only and do not direct implementation.
