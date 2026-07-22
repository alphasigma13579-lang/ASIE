# ASIE Master r11 Architect Resolution Review

## Findings

### High: original implementation plan defers core r10 requirements

The original `implementation_plan.md` places "adaptive personas" in Phase 2. This is unsafe if interpreted as the FSDP sovereign personas. r11 corrects this: the five sovereign personas, deterministic KPIs, and no-vote Sovereign Verdict are Phase 1 core requirements.

### High: performance optimizations could be misread as architecture changes

Shared memory and zero-copy transfer are valid implementation optimizations only below SCL. They must not create a new transport layer, bypass the Bus Controller, or weaken audit and authorization.

### High: UI sensitivity preview could leak calculation ownership into React

The sensitivity matrix is allowed only as a Finance Engine output. React may display bounded preview interpolation, but final decisions and exports must use backend immutable snapshots.

### Medium: data strategy references external collection agents

Builder Agent or Engineer and Tevali are not ASIE authorities. Market baselines and synthetic fixtures require labeling, rights review, human approval, and no runtime crawling under `strict_open_data_only_v1`.

### Medium: provider-specific AI references require neutralization

DeepSeek or any named model/provider is replaceable implementation detail. AI cannot own controlled numbers, legal interpretation, or final verdicts.

## ACP Required?

No ACP is required for r11 as written, because accepted items are constrained as implementation mechanisms under existing AAS contracts and component ownership.

ACP becomes required if any accepted optimization changes official component names, message path, source-of-truth ownership, trust authority, module boundaries, or AI/provider authority.

## Corrections Applied

- Added `07-architect-decisions/ASIE-r11-Architect-Resolution-Closure.md`.
- Preserved the four original source files under `07-architect-decisions/originals/`.
- Updated README, MANIFEST, Builder Agent or Engineer prompt, and preflight checklist to require r11 closure.
- Added seven `R11-AC-*` rejection tests.

## Residual Risk

Implementation remains unverified until code is inspected and tests prove r10 and r11 rejection cases. r11 is a corrected build specification, not proof that any existing implementation is compliant.

## Verdict

GOOD -- r11 architect resolutions closed with mandatory constraints.

