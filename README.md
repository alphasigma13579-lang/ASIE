# ASIE

AlphaSigma Intelligence Engine (ASIE) is a local-first decision platform for structured project analysis.

## Source of truth

The runnable workspace is kept under:

`ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/`

The repository root is intentionally a navigation and governance layer. Start with [`AGENTS.md`](AGENTS.md) and the package guide before editing. Runtime code, frontend code, tests, and operational documents live in the canonical workspace above.

## What is current

- `backend/`: local API, AAS runtime, modules, finance, evidence, decision, and snapshot assembly.
- `src/`: React/Vite client.
- `tests/`: deterministic Python test suite, including runtime-freeze tests.
- `docs/`: current architecture, release, runbook, ACR records, orientation, and implementation status.
- `docs/reference/`: historical reference material; it is not an executable source or a production policy by itself.

The AAS Runtime Freeze v1.0 remains mandatory:

`Kernel -> Heart Controller -> Hearts -> Bus Controller -> ASIE System Bus -> Socket Contract Layer -> Module Runtime -> Snapshot Assembly`

## Local development

Prerequisites: **Python 3.13+** (the runtime uses PEP 702 `warnings.deprecated`) and Node.js 22+ with pnpm.

```bash
cd ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer
pip install -r requirements.txt
corepack enable
pnpm install --frozen-lockfile
pnpm build
python -m unittest discover -s tests
python backend/asie_local_api.py
```

The local development profile keeps external network access and real AI providers disabled unless a separate approved ACR changes that control.

## Product direction

The two customer entry paths meet at one governed `Dynamic Input Blueprint`:

1. Idea-only users receive a short, template-governed Product AI interview.
2. Users with numbers, estimates, Excel, PDF, or supplier quotes map their data into the same blueprint.
3. Only an approved, normalized input manifest may cross into Finance.

The governing record for this decision is [`ACR-DIB-001`](ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/docs/ACR-DIB-001-Dynamic-Input-Blueprint.md), merged into `main`.

## Read first

- [`AGENTS.md`](AGENTS.md): repository rules for programmers and agents.
- [`AGENTS.md`](ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/AGENTS.md): canonical package map and runtime boundaries.
- [`PROJECT-ORIENTATION.md`](ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/docs/PROJECT-ORIENTATION.md): two entry paths, one blueprint, current gaps, and build order.
- [`IMPLEMENTATION-STATUS-MATRIX.md`](ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/docs/IMPLEMENTATION-STATUS-MATRIX.md): implemented versus planned versus reference.

## Branch discipline

- `main` is the integration target.
- `agent/*` branches are working branches and must not be treated as release branches.
- Changes to the frozen runtime, contracts, external network policy, or AI provider policy require an ACR before implementation.

## License and status

ASIE is an active development repository. See the canonical workspace documentation for the current readiness and release status.
