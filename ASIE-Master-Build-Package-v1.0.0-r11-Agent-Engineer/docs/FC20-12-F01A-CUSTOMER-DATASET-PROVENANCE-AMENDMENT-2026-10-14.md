# F-01A — Customer Dataset Provenance Contract and Scope Amendment

Status: **PROPOSED / REVIEW_REQUIRED / NOT_EFFECTIVE / NO_IMPLEMENTATION_AUTHORITY**. Date: 2026-10-14.

This publication changes two documents only: this proposal and a navigation entry in `docs/EKB/README-AR.md`. It does not modify the effective manifest, guard, API, Dataset rows or application branch.

## Baselines and decision evidence

- Governing main: `9eeddedd08fab13f393d76ba15c648085a0f7f80`, effective RESUME19 for the existing 24-file customer-recovery operation.
- Application dependency: unmerged [Draft #189](https://github.com/alphasigma13579-lang/ASIE/pull/189), pinned `b011a6b3773f4c5e0a905161b5504fff339496f6`. The code findings below concern this application baseline, not a claim that all its repairs are on main. The 24-file recovery implementation is local and unpublished at this design checkpoint.
- Accepted parent design: [customer recovery/T08](FC20-12-F01A-CUSTOMER-RECOVERY-ACCEPTANCE-SCOPE-PROPOSAL-2026-10-14.md), especially source ownership, EKB-08 presentation, exact evidence targets and scope-stop conditions.
- [Assistant-relayed publication decision](https://github.com/alphasigma13579-lang/ASIE/pull/207#issuecomment-6174495549): owner approval `2026-10-14T17:37:35.212064Z`; public receipt created `2026-10-14T17:39:11Z`. This is not an independent owner signature or execution receipt.
- T08 remains OPEN, browser acceptance NOT_RUN, startup acceptance UNKNOWN_NOT_APPROVED, release BLOCK. No #189 merge, live database, network/provider activation or deployment authority is added.

## Settled product direction
Customer-supplied quotations, items and prices used in the customer's studies require no license/terms proof. The customer is responsible for this material. The platform manages eligibility and reuse conditions for platform-sourced external/open data, including websites, agencies and companies. API access/rate permissions do not themselves establish reuse permission. Quality/completeness/numerical consistency remain separate.

## Existing defect and canonical correction
Application baseline #189 b011a6b3773f4c5e0a905161b5504fff339496f6 applies license_snapshot_ref, terms_hash and external source approval to every Dataset. Local imports in App.tsx also hard-code GASTAT_CANDIDATE. Dataset records are organization-scoped; existing project links support both assumption and sector_criterion targets.

Keep the existing Dataset row, notes_json and API routes. Add a reserved versioned server-owned provenance object recording customer-study material versus governed external material, authenticated creator, organization, initial project context and creation time. This records the authenticated submission context and responsibility, not a certification of copyright ownership or independent factual verification. The initial project is audit context, not a new exclusive-use lock. Preserve reuse across the customer's authorized projects in the same organization using existing project-link authorization. Never infer origin from a filename, source_id, client classification, manual import or missing proof.

The existing import request expresses own-study intent and selected project. The server resolves the actual project/organization, checks selected-tenant consistency and project.edit, then creates the provenance. Client input cannot supply or replace the reserved object. Platform/legacy entries cannot be relabeled, reassigned or overwritten through collection-create or review calls. An explicitly new customer submission is a new record; it does not rewrite old records or historical links.

## Persistence and compatibility
Use the common Repository Dataset writer within a transaction: separate create intent from update intent, reject existing identities for collection creation, and preserve stored organization/provenance on updates. Reject conflicting reserved fields, including nested notes. Preserve legacy internal update behavior only where explicitly compatible; do not silently alter every existing caller. Enforce transformation parent identity in its common writer as well as HTTP admission.

On material Dataset content replacement, explicitly invalidate current Dataset approval and dependent transformation/link review in the same canonical persistence boundary; retain prior historical snapshots and provenance. The exact affected-record and rollback behavior must be registered and tested, rather than leaving previously approved derived output attached to changed input. Metadata-only edits must not be treated as content replacement without an explicit rule.

Storage representation: the existing `datasets.source_id TEXT NOT NULL` column stores the empty string (`source_id = ""`) for recognized customer-study material. This means no platform-source association, not SQL NULL or an omitted INSERT binding. The existing normalizer already emits this empty string for a missing source and the current writer persists it; there is no source foreign key. Do not create a placeholder SourceReviewRecord or credit a source review. Reject any nonempty platform source association for this category. External and legacy records retain their existing nonempty-source eligibility checks. Acceptance must prove both storage compatibility and that reports/ledger emit no official-source URL or confidence credit.

No table/column/index migration, new store, route, original-file archive, automatic backfill or data rewrite. Existing storage retains only a preview/profile, not the complete original file. Legacy, missing, malformed or unsupported provenance receives no exemption and retains existing eligibility checks.

## One eligibility authority and truthful consumption
Amend normalization-time approval and dataset_quality_gate together. Recognized customer-study records do not require external source approval, fabricated source_id, license_snapshot_ref or terms_hash. Retain applicable data-quality/privacy/classification and explicit content/link/transformation review. Customer-study records must have no platform source_id association: reject attempts to attach one rather than crediting its approval or URL. The platform must not describe a customer submission as an independently verified official source.

The current-run caller in backend/asie_local_api.py must pass the authoritative project organization into the existing register builder; its present unscoped call cannot remain for customer material. Filter admission before constructing the register, not merely after disclosure in a failed gate. Carry trusted consuming organization/project context through the existing evidence_register payload, which the runtime already forwards unchanged. The ledger's fallback calls the same gate with this context. Preserve confidence weights, existing target types and the separate sector-intelligence predicate requiring an enabled sector source; this amendment neither grants official-source confidence nor silently rewrites that predicate. No new assumption-only restriction.

## Minimal implementation scope
Four additional production paths beyond the active 24. The proposed active repair inventory becomes 28; the historical cumulative union becomes 35, not 36, because backend/repository.py is already among the 32 cumulative paths. Historical membership alone does not authorize these new Dataset operations.

Additional paths:
1. backend/datasets.py — reserved provenance preservation/validation and canonical eligibility conditions.
2. backend/repository.py — atomic immutable ownership/provenance, create/update distinction and transformation-parent protection.
3. backend/evidence_ledger.py — trusted-context fallback and honest provenance/source projection.
4. src/api.ts — project/intended-use fields through existing import requests.

Already active paths: backend/asie_local_api.py; src/contracts.ts; src/App.tsx; src/customerLanguage.tsx; canonical registry and its documentation; recovery API, language and browser tests. Their final diff must remain limited to this amendment. No provider/source_registry/frozen runtime change.

## Required acceptance
- Customer own-study material is accepted without license/terms proof after applicable quality/review checks.
- Same-owner authorized project reuse works; another organization cannot use or relabel it.
- Platform and legacy records retain permission requirements.
- Collection-create cannot overwrite a known Dataset; review cannot reassign ownership/provenance.
- Nested reserved-field injection, unknown versions and wrong typed provenance fail closed.
- Transformations preserve parent and ownership; evidence links use the correct project/organization.
- Customer records never acquire official-source labels/confidence simply through their exemption.
- Existing snapshots, legacy rows, confidence weights and external source checks remain unchanged.

## Governance/publication
This document is a published design proposal only. The accepted 24-path operation does not authorize the four additional paths or changed admission semantics. Publication for review is authorized; design merge/adoption and the necessary scope registration/RESUME remain separate governed decisions. No application changes under this amendment have been made. Avoid a separate approval for each field or repeating the settled product requirement.

## Pinned source evidence

All application links below are pinned to the unmerged application baseline, while governing design links above belong to the main baseline.

- [Dataset requirements and normalization](https://github.com/alphasigma13579-lang/ASIE/blob/b011a6b3773f4c5e0a905161b5504fff339496f6/ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/backend/datasets.py): blanket license/terms/source requirements, notes reconstruction and manual-import formats.
- [Common Dataset/Transformation persistence](https://github.com/alphasigma13579-lang/ASIE/blob/b011a6b3773f4c5e0a905161b5504fff339496f6/ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/backend/repository.py): Dataset upsert/review and transformation parent writes.
- [Existing HTTP owners and register builder](https://github.com/alphasigma13579-lang/ASIE/blob/b011a6b3773f4c5e0a905161b5504fff339496f6/ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/backend/asie_local_api.py): manual/file/general creation, review, authorization, evidence links and current-run register.
- [Ledger fallback and confidence](https://github.com/alphasigma13579-lang/ASIE/blob/b011a6b3773f4c5e0a905161b5504fff339496f6/ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/backend/evidence_ledger.py): common gate fallback and existing target types.
- [Customer imports](https://github.com/alphasigma13579-lang/ASIE/blob/b011a6b3773f4c5e0a905161b5504fff339496f6/ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/src/App.tsx) and [client requests](https://github.com/alphasigma13579-lang/ASIE/blob/b011a6b3773f4c5e0a905161b5504fff339496f6/ASIE-Master-Build-Package-v1.0.0-r11-Agent-Engineer/src/api.ts): existing routes, including the fabricated GASTAT_CANDIDATE association to remove for customer material.

## Next governed transition

After design acceptance, prepare one bounded STOP_CHECKPOINT/SCOPE_EXTENSION registration preserving the 19 historical events, existing cumulative paths, active 24-file work, held slot and index exception. Register the four additional paths and the specific admission/identity/content-invalidation operations above; registration keeps execution false. Its merge and the separately reviewed RESUME require the governing owner decisions. No new standalone design is needed merely to repeat this accepted requirement. The subsequent implementation should use focused compatibility/security regressions, not an unrelated expansion of historical mutation matrices. No tests, historical seals or CI deadline may be weakened.
