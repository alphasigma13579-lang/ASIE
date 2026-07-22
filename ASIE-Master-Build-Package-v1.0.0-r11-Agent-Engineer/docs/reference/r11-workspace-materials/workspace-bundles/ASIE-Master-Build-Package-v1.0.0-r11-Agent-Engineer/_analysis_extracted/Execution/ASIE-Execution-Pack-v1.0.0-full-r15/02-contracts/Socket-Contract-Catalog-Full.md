# Socket Contract Catalog Full

## كتالوج عقود السوكيت الكامل

## Contract Format

## صيغة العقد

Each contract must define:

كل عقد يجب أن يحدد:

- Name / الاسم.
- Owner / المالك.
- Caller / المستدعي.
- Purpose / الهدف.
- Input Schema / Schema المدخلات.
- Output Schema / Schema المخرجات.
- Authorization / التفويض.
- Failure Codes / أكواد الفشل.
- Audit Events / أحداث التدقيق.

## Market Contracts

## عقود السوق

### `market.query.request.v1`

طلب استعلام السوق.

Owner:

المالك:

`Market Intelligence Module` / موديول ذكاء السوق.

Allowed Callers:

المستدعون المسموحون:

- `Project Wizard Module` / موديول معالج المشروع.
- `Finance Engine Module` / موديول محرك التمويل.
- `AI Advisory Module` / موديول الاستشارة.
- `Decision Council Module` / موديول مجلس القرار.

Input Schema:

Schema المدخلات:

```json
{
  "type": "object",
  "required": ["project_id", "country", "sector", "classification", "geo_context_id", "requested_topics"],
  "properties": {
    "project_id": {"type": "string"},
    "country": {"type": "string", "const": "SA"},
    "sector": {"type": "string"},
    "classification": {"type": "string"},
    "geo_context_id": {"type": "string"},
    "requested_topics": {
      "type": "array",
      "items": {"enum": ["demand", "competitors", "prices", "regulation", "seasonality", "macro_context"]}
    }
  }
}
```

Failure Codes:

أكواد الفشل:

- `COUNTRY_SCOPE_REJECTED` / رفض نطاق الدولة.
- `MISSING_GEO_CONTEXT` / نقص سياق الموقع.
- `UNSUPPORTED_TOPIC` / موضوع غير مدعوم.

### `market.evidence.pack.v1`

حزمة أدلة السوق.

Output Schema:

Schema المخرجات:

```json
{
  "type": "object",
  "required": ["evidence_pack_id", "project_id", "country", "items", "missing_evidence", "created_at"],
  "properties": {
    "evidence_pack_id": {"type": "string"},
    "project_id": {"type": "string"},
    "country": {"type": "string", "const": "SA"},
    "items": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["topic", "claim", "source_id", "confidence_score"],
        "properties": {
          "topic": {"type": "string"},
          "claim": {"type": "string"},
          "source_id": {"type": "string"},
          "confidence_score": {"type": "number", "minimum": 0, "maximum": 1}
        }
      }
    },
    "missing_evidence": {"type": "array", "items": {"type": "string"}},
    "created_at": {"type": "string"}
  }
}
```

### `market.price.sample.v1`

عينة سعر سوقية.

Required Fields:

الحقول المطلوبة:

- `item_name` / اسم البند.
- `price` / السعر.
- `currency` / العملة.
- `unit` / الوحدة.
- `source_id` / معرف المصدر.
- `retrieved_at` / تاريخ الجلب.

### `market.geo.context.v1`

سياق الموقع الجغرافي.

Rule:

القاعدة:

Must be generated from GPS or Map Pin, not free city text.

يجب أن ينتج من GPS أو Pin الخريطة، وليس من اسم مدينة نصي فقط.

## Finance Contracts

## عقود التمويل

### `finance.calculate.request.v1`

طلب حساب التمويل.

Allowed Callers:

المستدعون المسموحون:

- `Project Wizard Module` after complete context / موديول المعالج بعد اكتمال السياق.
- `Decision Council Module` for recalculation / مجلس القرار لإعادة الحساب.

Input Requirements:

متطلبات المدخلات:

- Valid project context / سياق مشروع صحيح.
- Evidence pack id / معرف حزمة الأدلة.
- No AI-generated numbers / بلا أرقام مولدة من AI.

### `finance.result.v1`

نتيجة التمويل.

Must include:

يجب أن تشمل:

- Source map for every numeric input / خريطة مصدر لكل رقم.
- Formula version / نسخة المعادلة.
- Scenario outputs / مخرجات السيناريوهات.
- Blocking missing fields / الحقول الناقصة المانعة.

## AI Contracts

## عقود الذكاء الاصطناعي

### `ai.advisory.request.v1`

طلب استشارة AI.

Rule:

القاعدة:

Prompt must include evidence ids and numeric guard.

يجب أن يتضمن Prompt معرفات الأدلة وحارس الأرقام.

### `ai.advisory.output.v1`

مخرج استشارة AI.

Must not include unsupported numbers.

يمنع أن يحتوي على أرقام غير مدعومة.

## Decision Contracts

## عقود القرار

### `decision.evaluate.request.v1`

طلب تقييم القرار.

Requires:

يتطلب:

- Project context / سياق المشروع.
- Evidence pack / حزمة الأدلة.
- Finance result / نتيجة التمويل.
- AI advisory output optional / مخرج الاستشارة اختياري.

### `decision.result.v1`

نتيجة القرار.

Must include:

يجب أن تشمل:

- Validation status / حالة التحقق.
- Persona outputs / مخرجات الشخصيات.
- Vote mapping / خريطة الأصوات.
- Consensus score / درجة الإجماع.
- Dissent / الاعتراضات.

## Government Data Compliance Contracts

## عقود امتثال البيانات الحكومية

### `compliance.govdata.review.v1`

Owner: `Audit / Observability Module`, operating the compliance policy gate with authorized human reviewers.

Accepted message: `govdata.access.review.requested.v1`

Required permissions:

- `govdata.source.review`
- Valid Security Context and workspace scope.
- Human reviewer identity for approval actions.

Required payload fields:

- `source_id`, `dataset_or_endpoint_url`, `route`, `classification`.
- `lawful_purpose_id`, `license`, `terms_snapshot_hash`, `intended_uses`.
- `personal_data_status`, `cross_border_processing`, `retention_policy_id`.
- `security_control_profile`, `requested_by`, `requested_at`.
- `profile_id`, `open_reuse_evidence_url`, `open_reuse_evidence_hash`.
- `requires_external_approval`, `requires_registration`, `requires_payment`, `requires_login`.

Returned messages:

- `govdata.access.decision.issued.v1`
- Failure: `GOVDATA_REVIEW_INCOMPLETE`, `GOVDATA_ACCESS_REJECTED`, `GOVDATA_APPROVAL_EXPIRED`.

Rules:

- AI output cannot approve legal access.
- Unknown classification, terms, license, purpose, or required approver produces deny.
- Approval is limited to exact endpoint/path, purpose, use, period, and processing location.
- Under `strict_open_data_only_v1`, a reviewer cannot approve an ineligible route by exception.

### `market.govdata.fetch.v1`

Owner: `Market Intelligence Module`

Accepted message: `govdata.fetch.requested.v1`

Required permissions:

- `govdata.source.fetch`
- Current `approved` decision ID.
- Enabled source and kill switch set to false.

Validation:

- Exact host, path, method, redirect, response size, file type, and rate policy.
- Current license/terms hash and approval expiry.
- `profile_id` is `strict_open_data_only_v1` and eligibility result is `enabled`.
- Authentication is `none`; no registration, payment, agreement, external approval, or source-issued credential is required.
- Personal-data and classification gate.
- Source status not suspended, expired, revoked, rejected, or unknown.

Returned messages:

- `govdata.fetch.completed.v1`
- `govdata.fetch.blocked.v1`
- `govdata.source.change.detected.v1`

Failure codes:

- `GOVDATA_NO_APPROVAL`
- `GOVDATA_SCOPE_MISMATCH`
- `GOVDATA_TERMS_CHANGED`
- `GOVDATA_CLASSIFICATION_BLOCK`
- `GOVDATA_PDPL_BLOCK`
- `GOVDATA_CROSS_BORDER_BLOCK`
- `GOVDATA_RATE_LIMITED`
- `GOVDATA_SOURCE_DENIED`
- `GOVDATA_CONTENT_QUARANTINED`
- `GOVDATA_STRICT_PROFILE_BLOCK`
- `GOVDATA_REFERENCE_ONLY`

### `market.reference.link.v1`

Owner: `Market Intelligence Module`

Accepted message: `market.reference.link.save.requested.v1`

Required payload:

- `url`, `user_authored_label`, optional `user_authored_private_note`.
- Valid actor, workspace security context, and `reference_only` classification.

Rules:

- Validate URL syntax and configured domain/path without DNS, HTTP, browser, preview, or metadata requests.
- Store only the URL and user-authored private fields.
- Do not store target titles, descriptions, budgets, usernames, screenshots, extracted text, or embeddings.
- Do not pass the target URL to AI, Finance, Decision, Reports, Pinecone, analytics, alerting, or evidence-pack contracts.
- `https://mostaql.com/projects` is allowed only through this contract in r15.

Returned messages:

- `market.reference.link.saved.v1`
- `market.reference.link.blocked.v1`

## Official Strategy Reference Contracts

### `compliance.strategy.reference.review.v1`

Owner: `Audit / Observability Module`, with authorized Content/Governance and Legal reviewers where applicable.

Accepted message: `market.strategy.reference.card.submit.requested.v1`

Required fields:

- `reference_id`, `canonical_url`, `publisher`, `official_title`, `source_language`.
- `access_class=reference_only`, `purpose=inspiration_and_alignment_only`.
- ASIE-authored themes, questions, interpretation, reviewer IDs, review dates, and expiry.
- Assertions `no_source_content_stored=true`, `not_legal_control=true`, `not_government_endorsement=true`.

Forbidden payload:

- Source HTML, full text, copied paragraphs/lists, screenshots, images, logos, embeddings, search-snippet reconstruction, or personal data.

Returned messages:

- `market.strategy.reference.card.approved.v1`
- `market.strategy.reference.card.rejected.v1`

Rules:

- AI cannot approve accuracy, originality, legal meaning, or endorsement status.
- Missing review, copied content, inaccurate attribution, or an endorsement implication produces reject.
- Approval is versioned, time-limited, and revocable.

### `market.strategy.reference.v1`

Owner: `Market Intelligence Module`

Accepted message: `market.strategy.alignment.requested.v1`

Required permissions and fields:

- Authorized workspace/actor and valid project context.
- Approved, unexpired strategy-card IDs and requested alignment themes.
- Arabic/English display language.

Returned message: `market.strategy.alignment.pack.v1`

Rules:

- Read approved ASIE-authored card fields only.
- Do not fetch or resolve any official reference URL.
- Output separates official-source metadata, ASIE interpretation, project-specific question, and recommendation.
- Output includes source link, review date, and `ASIE interpretation; not government approval` disclaimer.
- A strategy page cannot satisfy a formal law, regulation, standard, or cybersecurity-control requirement.

### `audit.strategy.reference.event.v1`

Owner: `Audit / Observability Module`

Accepted message: `audit.strategy.reference.event.v1`

Required fields:

- `event_id`, `correlation_id`, `reference_id`, `card_version`, `actor_id`, `workspace_id`.
- `action`, `decision`, `reason_codes`, `reviewer_ids`, `timestamp`.
- No source-page content, personal data, credentials, or unnecessary payload.

Returned message: `audit.strategy.reference.recorded.v1`.

### `audit.govdata.event.v1`

Owner: `Audit / Observability Module`

Accepted messages: all approved `govdata.*` audit events.

Required audit fields:

- `event_id`, `correlation_id`, `contract_id`, `socket_id`.
- `source_module`, `actor_id`, `workspace_id`, `source_id`, `purpose_id`.
- `approval_decision_id`, `access_result`, `reason_codes`, `timestamp`.
- No credentials, tokens, full personal payloads, or unnecessary sensitive data.

Returned message: `govdata.audit.recorded.v1`.

### `admin.govdata.control.v1`

Owner: `Admin Module`

Accepted messages:

- `govdata.source.suspend.requested.v1`
- `govdata.source.reapprove.requested.v1`

Rules:

- MFA and privileged authorization required.
- Suspension is immediate and auditable.
- Re-enable requires a new audited compliance decision; Admin cannot self-approve legal access.

## Project Dashboard Presentation Contracts

## عقود عرض لوحة المشروع

These contracts create no Dashboard Module. They allow `Reports Module` to compose approved owner outputs for an authorized project view without recalculation.

### `reports.project.dashboard.view.v1`

Owner: `Reports Module`

Accepted message: `dashboard.project.view.requested.v1`

Allowed caller:

- Authenticated UI/API boundary with project-scoped authorization and entitlement.

Required fields:

- `actor_id`, `workspace_id`, `project_id`, `run_id`.
- Requested route/section, `scenario_id`, locale, currency, and `as_of` policy.
- Approved output contract versions.

Returned messages:

- `dashboard.project.view.composed.v1`.
- `dashboard.project.view.blocked.v1`.

Rules:

- Compose only outputs accepted by `DASH-ALG-01`.
- Do not recalculate market, finance, risk, readiness, simulation, or decision values.
- Every metric resolves to the universal output envelope.
- Cross-project data, stale-disallowed values, incompatible runs, and unsupported contract versions are blocked.
- The response contains section state, source/formula/assumption drill-down references, and audit reference.

### `audit.dashboard.output.lineage.v1`

Owner: `Audit / Observability Module`

Accepted message: `dashboard.output.lineage.requested.v1`

Required fields:

- Authorized actor/workspace/project scope.
- `output_id`, `run_id`, requested lineage depth, and purpose.

Returned messages:

- `dashboard.output.lineage.resolved.v1`.
- `dashboard.output.lineage.blocked.v1`.

Rules:

- Return only authorized evidence metadata, transformations, formula/template versions, assumptions, and audit links.
- Never return credentials, MFA data, hidden prompts, private model reasoning, unnecessary personal data, or full sensitive source payloads.
- Reference-only sources expose approved metadata and ASIE-authored cards only.

### `reports.project.run.compare.v1`

Owner: `Reports Module`

Accepted message: `dashboard.project.run.compare.requested.v1`

Required fields:

- Project-scoped authorization.
- Two or more approved run IDs.
- Selected output IDs, scenario, locale, and currency.

Returned messages:

- `dashboard.project.run.compare.composed.v1`.
- `dashboard.project.run.compare.blocked.v1`.

Rules:

- Compare owner outputs only; Reports does not recalculate.
- Expose changed project inputs, evidence versions, assumptions, algorithms, formulas, and decision effects.
- Block misleading comparisons across incompatible currencies, periods, formula versions, or project identities.

## Professional Feasibility and Procurement Contracts

These contracts extend existing Module responsibilities. They do not create a Feasibility Module, Procurement Module, Methodology Layer, or direct Module call.

### `project.feasibility.profile.v1`

Owner: `Project Wizard`

Accepted message: `feasibility.study.profile.select.requested.v1`

Required fields:

- Authorized actor/workspace/project and purpose.
- Sector/subsector, stage, project size, capital intensity, financing route, regulatory/impact exposure, decision audience, and government-competition intent.
- Policy version and requested locale.

Returned messages:

- `feasibility.study.profile.selected.v1`
- `feasibility.study.profile.blocked.v1`

Rules:

- Apply `FST-ALG-01`; a profile cannot be downgraded to hide mandatory analysis.
- Government competition intent selects `GOVERNMENT_COMPETITION`.
- Missing context remains `needs_input`; AI cannot select or downgrade the profile.

### `decision.feasibility.compose.v1`

Owner: `Decision Council`

Accepted message: `feasibility.study.compose.requested.v1`

Required fields:

- Selected profile, project/run/scenario IDs, chapter output references, owner contract versions, reconciliation request, and decision purpose.

Returned messages:

- `feasibility.study.chapter.state.v1`
- `feasibility.study.reconciliation.result.v1`
- `feasibility.study.composition.ready.v1`
- `feasibility.study.composition.blocked.v1`

Rules:

- Apply `FST-ALG-02` and `FST-ALG-03`.
- Decision Council validates and synthesizes; it does not recalculate Market or Finance outputs.
- Reports may render only the returned approved composition.

### `finance.feasibility.advanced.v1`

Owner: `Finance Engine`

Accepted message: `finance.feasibility.advanced.calculate.requested.v1`

Required fields:

- Authorized project/run/scenario, approved input/evidence/assumption references, time horizon, currency, nominal/real and tax basis, model/profile versions, requested analyses, and formula conventions.

Returned messages:

- `finance.integrated.statements.result.v1`
- `finance.investment.appraisal.result.v1`
- `finance.working.capital.funding.result.v1`
- `finance.unit.economics.result.v1`
- `finance.debt.metrics.result.v1`
- `finance.economic.analysis.result.v1`
- `finance.uncertainty.analysis.result.v1`
- `finance.feasibility.advanced.blocked.v1`

Rules:

- Apply `FIN-ALG-06` through `FIN-ALG-12` as requested and applicable.
- Every number is deterministic or a reproducible seeded simulation from approved inputs.
- AI cannot provide or change inputs, rates, formulas, ranges, distributions, correlations, weights, or results.
- Failed statement reconciliation, mixed bases, missing formula conventions, or unsourced assumptions block the affected output.

### `compliance.procurement.reference.review.v1`

Owner: `Audit / Observability Module`, with authorized procurement/legal reviewer.

Accepted message: `procurement.reference.review.requested.v1`

Required fields:

- Project purpose, competition ID/entity when applicable, exact official URL, publisher/domain, title, document/form type, contract category, version/date, retrieval metadata/hash, source-page hash, terms/rights review, reviewer and review due date.

Returned messages:

- `procurement.reference.approved.v1`
- `procurement.reference.controlled.template.v1`
- `procurement.reference.blocked.v1`
- `procurement.exact.documents.required.v1`

Rules:

- Apply `PROC-ALG-01` and `PROC-ALG-02`.
- Exact competition documents and addenda override generic MOF/Etimad forms.
- A reference cannot create a government-approved feasibility claim.
- Raw files use a controlled, scoped, auditable document workflow; they do not enter AI/RAG automatically.

### `compliance.methodology.card.review.v1`

Owner: `Audit / Observability Module`, with authorized content/rights reviewer.

Accepted message: `methodology.card.review.requested.v1`

Required fields:

- Canonical reference URL, publisher, authority class, source language, allowed purpose, rights/terms review, original ASIE-authored method card, originality attestation, reviewers, review/expiry dates, and prohibited-use flags.

Returned messages:

- `methodology.card.approved.v1`
- `methodology.card.rejected.v1`
- `methodology.commercial.access.blocked.v1`

Rules:

- Apply `METH-ALG-01` and `METH-ALG-02`.
- Aljdwa network access, copying, embedding, RAG, vectorization, monitoring, or AI summary is blocked without explicit written permission covering the exact action.
- AI reads approved original ASIE cards only and cannot approve originality, rights, or authority class.
- International/commercial references never become Saudi legal authority or endorsement.
