# Open Government Data Compliance Algorithms

## خوارزميات امتثال البيانات الحكومية المفتوحة

**Owner:** Market Intelligence + Audit / Observability, with authorized Legal, Privacy/DPO, Cybersecurity, and Business reviewers  
**Affected AAS:** AAS-11, AAS-15, AAS-16, AAS-17, AAS-18, AAS-20, AAS-32, AAS-40, AAS-60  
**Rule:** Deterministic code evaluates machine-enforceable policy. Human authorized reviewers issue legal/privacy approvals. AI never approves access.

## OPEN-DATA-ALG-01 Source Discovery and Registration

Purpose: discover candidate datasets without granting access.

Inputs:

- National Open Data Platform metadata.
- Official agency dataset catalogs and documented API directories.
- Existing approved source registry.

Steps:

1. Verify HTTPS and official publisher identity.
2. Record exact dataset, endpoint, file, or bounded path.
3. Record owner type and Arabic/English official names.
4. Capture dataset metadata, license URL, terms URL, update cadence, and contact.
5. Create status `discovered` then `pending_classification`.
6. Emit `govdata.source.discovered.v1`.

Hard rules:

- Discovery never enables fetching.
- No blanket domain approval.
- Search results and AI suggestions are candidate locators, not legal evidence.

## OPEN-DATA-ALG-02 Route and Classification Decision

Purpose: distinguish open data from public documents, licensed APIs, data sharing, personal data, and restricted data.

Decision order:

```text
explicit government classification
-> explicit dataset publication and license
-> explicit API documentation and terms
-> public-document route
-> unknown and deny
```

Outputs:

- `official_open_dataset`
- `official_open_api`
- `official_public_document`
- `licensed_or_registered_api`
- `government_data_sharing`
- `personal_data`
- `restricted_or_classified`
- `unknown`

Any conflict resolves to the more restrictive route and triggers human review.

Under `strict_open_data_only_v1`, only `official_open_dataset` and `official_open_api` continue to eligibility evaluation. `official_public_document` becomes reference-only; every remaining route is blocked.

## OPEN-DATA-ALG-03 Legal Access and License Evaluation

Purpose: produce a bounded, time-limited access decision.

Required checks:

1. Exact owner, URL, endpoint/path, and authentication mode.
2. License identity, URL, version or content hash.
3. Terms URL and snapshot hash.
4. Intended purpose and outputs.
5. Commercial use, transformation, redistribution, attribution, and endorsement restrictions.
6. Copyright handling for documents and reports.
7. Approval identities, dates, expiry, and reason codes.

Result:

```json
{
  "decision": "approved|rejected|pending|expired|suspended|revoked",
  "allowed_uses": [],
  "prohibited_uses": [],
  "approved_scope": {},
  "decision_id": "uuid",
  "review_due_at": "iso_datetime",
  "reason_codes": []
}
```

AI summaries may assist a reviewer but are never decision inputs for final approval.

## OPEN-DATA-ALG-04 Open Data vs Data Sharing Gate

Purpose: prevent crawling from replacing lawful government data-sharing procedures.

Steps:

1. Require proof that data is classified public and published for open reuse.
2. If proof exists, route to open-data approval.
3. If data requires registration, credentials, payment, agreement, or approval, block it under the active profile.
4. If data is non-public government data, classify it as blocked; do not initiate an ASIE sharing workflow.
5. Block all crawler, browser-automation, and third-party-scraper fallbacks.
6. Emit an audit event for route and decision.

Forbidden: treating `HTTP 200`, search indexing, or a government domain as proof of open-data status.

## OPEN-DATA-ALG-05 Personal Data and Cross-Border Gate

Purpose: enforce PDPL-related controls before ingestion or disclosure.

Steps:

1. Detect declared and observed personal/sensitive data fields.
2. Evaluate re-identification risk from joins and free text.
3. Require lawful purpose/basis and privacy-review decision.
4. Enforce minimization and field allowlist.
5. Select masking, pseudonymization, aggregation, or rejection.
6. Check processor/subprocessor and storage locations.
7. If processing or disclosure leaves the Kingdom, require approved transfer assessment and safeguards.
8. Attach retention, rights, deletion, and breach workflows.
9. Block AI/vector/analytics/report consumers until sanitization is proven.

Consent is not assumed and is not the only possible legal basis. The configured privacy authority selects the applicable basis.

## OPEN-DATA-ALG-06 Retrieval Runtime Guard

Purpose: constrain every network request to its approved technical and legal scope.

Validation order:

1. Current source status and kill switch.
2. Current decision ID, purpose ID, and approval expiry.
3. Scheme, host, port, path, method, query-field allowlist.
4. DNS resolution and private/metadata IP block.
5. Redirect destination revalidation.
6. Authentication and least-privilege credential scope.
7. Rate, concurrency, time, and retry budget.
8. Response status handling.
9. Content type, size, decompression, malware, and parser sandbox.
10. Audit outcome.

Stop on CAPTCHA, WAF challenge, login wall, `401`, `403`, repeated `429`, legal notice, source revocation, or terms mismatch. Never rotate proxies or identities to continue.

## OPEN-DATA-ALG-07 Content Integrity and Evidence Ledger

Purpose: produce traceable evidence without trusting retrieved content.

Steps:

1. Hash raw bytes and capture retrieval metadata.
2. Sanitize active content and scan for malware.
3. Label retrieved content as untrusted for prompt-injection defense.
4. Validate schema and quarantine schema drift.
5. Separate raw facts, normalized values, derived calculations, and AI explanation.
6. Record transformations and calculation versions.
7. Attach publisher, exact URL, dataset ID, license, attribution, classification, decision ID, freshness, and language.
8. Permit downstream use only when the ledger is complete.

Pinecone/vector storage may index approved evidence but remains a cache, never the legal or factual source of truth.

## OPEN-DATA-ALG-08 Terms, License, and Freshness Revalidation

Purpose: prevent stale approval from authorizing changed sources.

Triggers:

- Before scheduled ingestion.
- At configured review time.
- On redirect, schema, authentication, terms, license, publisher, or endpoint change.
- On source complaint or regulatory update.

Steps:

1. Compare current terms/license hashes with approved hashes.
2. Validate source identity and classification.
3. Validate data release and evidence freshness separately.
4. Suspend on any material mismatch.
5. Invalidate affected cache eligibility.
6. Require a new approval decision before re-enable.

## OPEN-DATA-ALG-09 Cybersecurity Control Applicability

Purpose: map ASIE deployment and source use to current Saudi cybersecurity control profiles.

Inputs:

- Entity type and size.
- Government, private, CNI, or regulated-sector status.
- Data classification and sensitivity.
- Cloud/hosting use and locations.
- Critical-system status.
- Third parties and subprocessors.

Candidate profiles:

- `NCNICC-1:2025` for in-scope non-CNI private-sector entities.
- `ECC-2:2024` for government and CNI scope.
- `DCC-1:2022` for applicable data lifecycle controls.
- `CCC-2:2024` for in-scope cloud services.
- `CSCC` and sector controls where applicable.

Output is an applicability record, control owner, evidence requirement, gap status, and next review. Unknown entity classification is a release blocker, not a guess.

## OPEN-DATA-ALG-10 Suspension, Revocation, and Incident Kill Switch

Purpose: contain legal, privacy, security, and source-integrity incidents.

Triggers:

- Terms/license/classification change.
- Approval expiry or revocation.
- Unexpected personal/classified data.
- Credential exposure, malware, prompt injection, schema poisoning, or exfiltration risk.
- Source block, complaint, or legal notice.

Actions:

1. Atomically set source to `suspended` and kill switch to true.
2. Stop scheduled and interactive requests.
3. Quarantine in-flight and newly retrieved content.
4. Prevent downstream Finance, Decision, Reports, AI, and vector use.
5. Invalidate affected cache entries without deleting forensic evidence.
6. Notify Security, Privacy/DPO, Legal, Data Owner, and Operations according to severity.
7. Preserve immutable audit and evidence chain.
8. Require a new audited compliance decision before reactivation.

Admin cannot override this algorithm with a feature flag or normal operational permission.

## OPEN-DATA-ALG-11 Strict Open-Data-Only Eligibility

Purpose: enforce `strict_open_data_only_v1` before internal approval or network access.

Inputs:

- Exact dataset or API endpoint.
- Publisher identity and public classification.
- Open-use policy or open-data license URL and hash.
- Authentication, registration, payment, contract, and external-approval flags.
- Personal, micro, restricted, classified, and user-generated-content flags.

Decision:

```text
IF exact official open-use evidence exists
AND classification is public
AND authentication is none
AND registration/payment/contract/external approval are false
AND personal/micro/restricted/user-generated flags are false
THEN eligible_candidate
ELSE reference_only or blocked
```

Rules:

1. Internal ASIE approval validates evidence but cannot convert a closed source into open data.
2. A public webpage, search result, `HTTP 200`, downloadable response, or government domain is insufficient.
3. A third-party scraping API cannot convert a blocked source into an eligible source.
4. The final allowlist key is exact publisher + dataset/endpoint + terms hash + purpose.
5. GASTAT data must carry attribution and a transformation label.

## OPEN-DATA-ALG-12 Reference-Only Link Guard

Purpose: make non-open discovery links useful without collecting their content.

Allowed input:

- Approved reference URL.
- User-authored private label or note.
- Workspace and actor security context.

Steps:

1. Validate URL syntax and the reference-only domain/path allowlist without making a network request.
2. Store only URL, user-authored label/note, owner workspace, creation time, and classification `reference_only`.
3. Return the URL to the UI for user-initiated navigation.
4. Prevent background preview, metadata lookup, screenshot, crawl, summary, embedding, alerting, and trend calculation.
5. Audit any attempt to pass the URL to a fetch, AI, vector, Finance, Decision, or Reports consumer.

Mostaql projects are permanently `reference_only` in r15. Reclassification requires new official reusable-data evidence and a new release decision.
