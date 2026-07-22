# Project Dashboard Decision and Presentation Algorithms

## خوارزميات قرار وعرض لوحة المشروع

These algorithms compose, validate, and present outputs owned by existing ASIE Modules. They do not create a Dashboard Module and do not move source-of-truth ownership.

## DASH-ALG-01 Output Provenance Envelope Validation

Owner: `Audit / Observability Module` with the output-owning Module.

Purpose: reject any visible output that cannot be traced to an authorized run, owner, contract, algorithm, and evidence or assumption basis.

Required fields:

- `output_id`, `project_id`, `run_id`.
- `owner_module`, `contract_id`, `algorithm_id`, `algorithm_version`.
- `value_type`, `unit`, `period`, `geography`, `scenario_id` where applicable.
- `evidence_refs` or `assumption_refs` for every factual or numeric value.
- `formula_ref` for calculated values.
- `as_of`, `status`, `audit_ref`.

Steps:

1. Validate project-scoped authorization.
2. Validate contract and algorithm ownership.
3. Validate type, unit, period, geography, and scenario compatibility.
4. Require evidence for observed values and approved assumptions for estimated inputs.
5. Require formula lineage for calculated values.
6. Require simulation configuration for simulated values.
7. Reject a narrative that introduces a value absent from its referenced outputs.
8. Emit presentation allow/block audit event.

Output: `dashboard.output.presentation.decision.v1`.

## DASH-ALG-02 Project Readiness Score

Owner: `Decision Council Module`.

Purpose: calculate a reproducible 0-100 internal readiness index and a 0-10 display score from validated domain scores.

Required domains:

- Market evidence and attractiveness.
- Financial viability.
- Execution readiness.
- Strategic fit.
- Risk resilience.
- Evidence and input quality.

Domain-score input rule:

- Each domain score must be produced by a versioned rule set referenced by the active sector template.
- Every raw metric declares directionality, lower/upper benchmark, unit, period, source output ID, and weight within the domain.
- Higher-is-better normalization uses `clamp(100 * (x - lower) / (upper - lower), 0, 100)`.
- Lower-is-better normalization uses `clamp(100 * (upper - x) / (upper - lower), 0, 100)`.
- Ordinal metrics use an explicit versioned lookup table; labels are not converted to numbers by AI.
- A domain score is the normalized weighted mean of its required metrics only after every required metric passes validation.
- Missing benchmark, directionality, unit, rule ID, or required metric returns `insufficient_data`.
- The result stores `domain_rule_id`, `domain_rule_version`, raw metric refs, normalized values, and contribution.

Weights:

- Base weights come from the active sector template and `sector.evaluation.criteria.v1`.
- Every required weight is non-negative and the normalized sum equals 1.00.
- Weight changes require a versioned template and approval record.
- A generic weight profile must not replace a sector-specific profile when one exists.

Formula:

```text
normalized_weight_i = weight_i / sum(required_weights)
raw_readiness_100 = sum(normalized_weight_i * domain_score_i)
display_readiness_10 = round(raw_readiness_100 / 10, 1)
```

Validation ceiling:

| Validation result | Maximum publishable score | Behavior |
| --- | ---: | --- |
| `PASS` | 100 | Publish score and band |
| `REVISE_REQUIRED` | 59 | Publish capped score with failed checks |
| `BLOCKED` | none | Do not publish a numeric final score |

Bands:

| Score | Arabic | English |
| --- | --- | --- |
| 0-34 | غير جاهز | Not ready |
| 35-59 | يحتاج تطويرًا جوهريًا | Material development required |
| 60-79 | تقدم بحذر | Proceed cautiously |
| 80-100 | جاهز بشروط التحقق | Ready subject to validation |

Rules:

- A readiness score is not probability of success, government approval, investment advice, or the Decision Council vote score.
- Missing a required domain returns `insufficient_data`; missing values are never treated as zero.
- Final decision remains governed by `DEC-ALG-01` and `DEC-ALG-03` and may be stricter than the score.

Output: `dashboard.project.readiness.result.v1`.

## DASH-ALG-03 Confidence Decomposition

Owner: `Decision Council Module`. Market evidence coverage, source confidence, and freshness arrive as approved Market Intelligence outputs through contracts.

Purpose: prevent one ambiguous confidence percentage from representing unrelated concepts.

Outputs:

1. `evidence_coverage_index`: weighted percentage of required evidence categories with eligible evidence.
2. `input_quality_index`: weighted percentage of required numeric inputs that are verified rather than assumed.
3. `freshness_index`: weighted freshness under source-specific policy.
4. `decision_agreement`: vote agreement derived from `DEC-ALG-03`.
5. `simulation_uncertainty`: intervals and downside probability from `FIN-ALG-04`.

Evidence coverage:

```text
coverage = 100 * sum(requirement_weight_j * resolved_j) / sum(requirement_weight_j)
resolved_j = 1 only when an eligible, current evidence reference satisfies requirement j
```

An optional `evidence_confidence_index` may be displayed:

```text
evidence_confidence = 0.50 * evidence_coverage
                    + 0.30 * input_quality
                    + 0.20 * freshness
```

It must be labeled `Evidence confidence index / مؤشر ثقة الأدلة`, never `probability of success`.

Output: `dashboard.confidence.breakdown.v1`.

## DASH-ALG-04 Strategic Framework Pack Assembly

Owner: `Decision Council Module`; evidence remains owned by its source Modules.

Purpose: assemble SWOT, PESTEL, Porter Five Forces, Business Model Canvas, Value Proposition Canvas, cultural fit, national alignment, and sector dimensions without converting narrative into unverified fact.

Item schema:

```json
{
  "item_id": "uuid",
  "framework": "SWOT | PESTEL | PORTER | BMC | VPC | CULTURAL | ALIGNMENT",
  "slot": "string",
  "statement": "string",
  "statement_type": "verified_fact | calculated_result | approved_assumption | analytical_judgment | reference_alignment",
  "evidence_refs": [],
  "assumption_refs": [],
  "counter_evidence_refs": [],
  "confidence_basis": "string",
  "review_status": "draft | approved | needs_review | blocked"
}
```

Rules:

- AI may draft wording from approved outputs; `AI-ALG-03` must validate it.
- A draft remains `analytical_judgment` until deterministic and human review gates pass.
- `reference_alignment` uses only approved ASIE-authored cards under `REF-ALG-03`.
- Framework items cannot create financial input values.
- Duplicate or contradictory items are grouped and surfaced, not silently merged.

Output: `dashboard.strategy.framework.pack.v1`.

## DASH-ALG-05 Risk Register and Matrix Builder

Owner: `Decision Council Module`.

Purpose: create a traceable risk register and 5x5 matrix from evidence, finance sensitivity, security/compliance states, and approved judgments.

Ordinal scales:

| Band | Probability label | Impact label |
| ---: | --- | --- |
| 1 | Rare / نادر | Insignificant / محدود جدًا |
| 2 | Unlikely / غير مرجح | Minor / منخفض |
| 3 | Possible / ممكن | Moderate / متوسط |
| 4 | Likely / مرجح | Major / عالٍ |
| 5 | Almost certain / شبه مؤكد | Severe / جسيم |

```text
inherent_exposure = probability_band * impact_band
residual_exposure = residual_probability_band * residual_impact_band
```

Rules:

- Ordinal bands are not displayed as exact probability percentages.
- Every risk has cause, event, impact, owner, treatment, due date, evidence, and residual state.
- A risk caused by missing evidence is categorized as evidence/model risk, not hidden.
- Regulatory or cybersecurity risks may be `blocked` independently of overall commercial attractiveness.

Output: `dashboard.risk.register.v1`.

## DASH-ALG-06 Scenario Comparison Presenter

Owner: `Finance Engine Module`.

Purpose: provide presentation-ready comparison without recalculating Finance Engine outputs.

Steps:

1. Load approved finance results sharing project, formula version, currency, horizon, and time basis.
2. Verify each scenario's changed variables and assumption/source refs.
3. Align series to the same period and unit.
4. Reject comparisons with incompatible horizons or formula versions unless explicitly normalized by Finance Engine.
5. Calculate display deltas only from stored owner outputs.
6. Attach break-even, cash deficit, margin, and runway markers.

Output: `dashboard.finance.scenario.compare.v1`.

Forbidden:

- Assigning probabilities to named scenarios without simulation.
- Labeling the best case as expected case.
- Hiding variables that differ from baseline.

## DASH-ALG-07 Investor Readiness Gate

Owner: `Decision Council Module` with `Finance Engine Module` outputs.

Purpose: decide whether funding, valuation, equity, and investor-facing sections may be displayed.

Required gates:

- Current finance baseline passes validation.
- Use-of-funds equals deterministic funding need within rounding policy.
- Runway and milestone financed are defined.
- Downside scenario is present.
- Valuation method and assumptions are present if valuation is shown.
- Legal and investment disclaimer is visible.
- No guaranteed return, funding, valuation, or legal term appears.

Results:

- `READY_FOR_DRAFT`.
- `NEEDS_INPUT`.
- `NEEDS_PROFESSIONAL_REVIEW`.
- `BLOCKED`.

Output: `dashboard.investment.readiness.v1`.

## DASH-ALG-08 Dashboard Section State Resolver

Owner: each output-owning Module; presentation enforcement by `Audit / Observability Module`.

Priority order:

1. `permission_denied`.
2. `blocked`.
3. `error`.
4. `stale`.
5. `needs_input`.
6. `insufficient_data`.
7. `loading`.
8. `ready`.

Rules:

- A section state is derived from its required outputs, not from frontend guesses.
- `stale` remains visible with the last approved value only when policy permits.
- `blocked` includes a stable reason code and remediation route.
- AI cannot upgrade any state.

Output: `dashboard.section.state.v1`.

## DASH-ALG-09 Bilingual Display Resolution

Owner: `Reports Module` for exported composition; frontend for contract-bound rendering.

Purpose: resolve Arabic RTL and English LTR labels without changing stored values or official source identity.

Rules:

- User locale selects UI labels and explanatory prose.
- Source official name and URL are preserved.
- Units, dates, currency, percentages, and decimal precision follow one locale policy per view.
- Formula symbols, contract IDs, algorithm IDs, and URLs remain directionally isolated.
- Missing translation fails UI acceptance; it does not fall back silently in final reports.

Output: `dashboard.localized.view.v1`.

## DASH-ALG-10 Dashboard and Report Parity

Owner: `Reports Module` with `Audit / Observability Module`.

Purpose: guarantee that the same approved run produces identical values across dashboard, PDF, presentation, and spreadsheet exports.

Steps:

1. Freeze `project_id`, `run_id`, `scenario_id`, locale, currency, and `as_of`.
2. Resolve allowed outputs through `DASH-ALG-01`.
3. Build view and exports from the same output IDs.
4. Compare raw values, units, periods, rounding policy, source refs, and formula versions.
5. Block export on mismatch.
6. Record export hash and audit event.

Output: `dashboard.report.parity.result.v1`.

## DASH-ALG-11 External Context Signal Guard

Owner: `Market Intelligence Module`; enforcement by `Audit / Observability Module`.

Purpose: control optional news, sentiment, and external-context presentation.

Rules:

- Input must come from an exact eligible source route under the active source profile.
- Search snippets, scraped pages, reference-only pages, and blocked sources are rejected.
- A model output is `MODEL_INFERENCE`, with model ID, version, input set, timestamp, confidence basis, and limitations.
- Model inference is excluded from finance, readiness, and final decision unless an explicitly approved deterministic policy says otherwise.
- The source article/page is not reproduced; allowed metadata and lawful evidence references are used.
- If no route is eligible, return `unavailable`; do not use a fallback crawler.

Output: `dashboard.external.context.signal.v1`.

## DASH-ALG-12 Legacy Screenshot Migration Guard

Owner: `Audit / Observability Module`.

Purpose: use old screenshots as functional references without importing legacy claims or confidential data.

Reject when a proposed implementation copies or infers from screenshots:

- Company, competitor, provider, investor, project, or user identity.
- Score, percentage, currency value, date, coordinate, source claim, or recommendation.
- Source logo, protected layout, copied text, or unsupported government-approval language.
- A direct vendor integration or provider authority.

Allow:

- Generic information hierarchy.
- Neutral interaction pattern.
- Chart family or card anatomy when rebuilt under the ASIE design system.
- A feature concept that is redefined through current ASIE contracts and algorithms.

Output: `dashboard.legacy.reference.review.v1`.

## Algorithm Acceptance Tests

| Test ID | Case | Expected |
| --- | --- | --- |
| `DASH-ALG-01-T01` | Numeric card has no algorithm ID | Reject |
| `DASH-ALG-01-T02` | Narrative introduces an unsupported number | Reject |
| `DASH-ALG-01-T03` | Output belongs to another project | Permission denied and audit |
| `DASH-ALG-02-T01` | Required readiness domain missing | `insufficient_data` |
| `DASH-ALG-02-T02` | Validation is blocked | No numeric final score |
| `DASH-ALG-02-T03` | Generic weights replace sector weights | Reject |
| `DASH-ALG-03-T01` | Evidence confidence labeled probability of success | Reject |
| `DASH-ALG-03-T02` | MCMC interval shown as decision agreement | Reject |
| `DASH-ALG-04-T01` | SWOT fact has no evidence or judgment label | Reject |
| `DASH-ALG-04-T02` | Strategic framework creates finance input | Reject |
| `DASH-ALG-05-T01` | Ordinal risk shown as exact probability | Reject |
| `DASH-ALG-05-T02` | Risk has no owner or treatment | Reject |
| `DASH-ALG-06-T01` | Scenarios use different formula versions | Block comparison |
| `DASH-ALG-06-T02` | Named scenario gets invented probability | Reject |
| `DASH-ALG-07-T01` | Valuation has no method | Block valuation panel |
| `DASH-ALG-07-T02` | Investor narrative promises return | Reject |
| `DASH-ALG-08-T01` | Frontend converts blocked to ready | Reject and audit |
| `DASH-ALG-09-T01` | Arabic report contains untranslated required UI label | Fail acceptance |
| `DASH-ALG-10-T01` | Dashboard and PDF values differ | Block export |
| `DASH-ALG-11-T01` | Search snippet used for sentiment source | Reject |
| `DASH-ALG-11-T02` | No eligible source and crawler fallback proposed | Reject fallback |
| `DASH-ALG-12-T01` | Legacy screenshot score copied into demo/production | Reject |
| `DASH-ALG-12-T02` | Legacy layout concept rebuilt with current contracts | Allow after review |
