# ASIE

AlphaSigma Intelligence Engine (ASIE) is a local-first decision platform for structured project analysis.

## Source of truth

The runnable workspace is kept under:

`ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/`

The repository root is intentionally a navigation and governance layer. Runtime code, frontend code, tests, and operational documents live in the canonical workspace above.

## What is current

- `backend/`: local API, AAS runtime, modules, finance, evidence, decision, and snapshot assembly.
- `src/`: React/Vite client.
- `tests/`: deterministic Python test suite, including runtime-freeze tests.
- `docs/`: current architecture, release, runbook, and ACR records.
- `docs/reference/`: historical reference material; it is not an executable source or a production policy by itself.

The AAS Runtime Freeze v1.0 remains mandatory:

`Kernel -> Heart Controller -> Hearts -> Bus Controller -> ASIE System Bus -> Socket Contract Layer -> Module Runtime -> Snapshot Assembly`

## Local development

```bash
cd ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer
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

The ACR for this decision is tracked in [PR #7](https://github.com/alphasigma13579-lang/ASIE/pull/7) until it is merged into `main`.

## Branch discipline

- `main` is the integration target.
- `agent/*` branches are working branches and must not be treated as release branches.
- Changes to the frozen runtime, contracts, external network policy, or AI provider policy require an ACR before implementation.

## License and status

ASIE is an active development repository. See the canonical workspace documentation for the current readiness and release status.
