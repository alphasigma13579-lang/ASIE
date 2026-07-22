# Open Government Data Integration and Legal Access

## الربط النظامي بالبيانات الحكومية المفتوحة والوصول القانوني

**Status:** Mandatory execution policy  
**Architecture decision:** Compliant with AAS v1.0.0 Frozen Baseline  
**Affected AAS:** AAS-11, AAS-15, AAS-16, AAS-17, AAS-18, AAS-20, AAS-32, AAS-40, AAS-60  
**Verified against official Saudi sources:** 2026-07-13  
**Active profile:** `strict_open_data_only_v1`; `Strict-Open-Data-Only-Source-Profile.md` is binding where this general policy describes broader routes.

## 1. Mandatory Disclaimer

هذه الوثيقة ضابط هندسي وامتثال داخلي، وليست فتوى أو رأيًا قانونيًا ولا شهادة اعتماد من جهة حكومية.

No software design can truthfully guarantee `1000% legal compliance`. Production activation requires documented approval from ASIE's authorized Saudi legal counsel, privacy or DPO function when applicable, cybersecurity function, and accountable business owner.

لا يجوز إظهار عبارة `متوافق نظاميًا` أو `معتمد حكوميًا` للمستخدم لمجرد اجتياز اختبارات البرمجيات. الحالة الصحيحة قبل الاعتماد البشري هي `pending_legal_approval`.

## 2. Constitutional Decision

This capability is not a new ASIE Layer, Controller, Bus, Heart, or source of truth.

هذه القدرة ليست طبقة جديدة، ولا متحكمًا، ولا ناقلًا، ولا قلبًا، ولا مصدر حقيقة جديدًا.

It is implemented through existing ASIE Modules:

| Responsibility | Owner | Forbidden |
| --- | --- | --- |
| Source discovery, retrieval, parsing, lineage | `Market Intelligence Module` | Legal approval, authorization, direct Finance writes |
| Legal/privacy/cyber policy gate | `Audit / Observability Module` with authorized human reviewers | Fetching source content, changing AAS, trusting AI judgment |
| Audit, alerts, quarantine, kill switch | `Audit / Observability Module` | Becoming source owner or silently re-enabling a source |
| Administrative approval UI | `Admin Module` | Bypassing Compliance decision or editing evidence history |
| Explanation and summarization | `AI Advisory Module` | Browsing directly, deciding legality, inventing facts or numbers |

Official internal path:

```text
Requester Module
-> Socket Contract Layer
-> APP Message
-> ASIE System Bus
-> Bus Controller participation governance
-> Audit / Observability compliance-decision Socket
-> Market Intelligence fetch Socket
-> Audit event Socket
```

Direct Module-to-Module calls, direct UI fetches, direct AI browsing, direct Finance Engine source access, and direct provider calls from Kernel are prohibited.

## 3. The Critical Distinction

ASIE must never treat every government website page as open data.

يجب الفصل بين المسارات الآتية:

| Route | Definition | Automatic Access |
| --- | --- | --- |
| `official_open_dataset` | Dataset expressly published as open data with an identifiable license or official reuse terms | Allowed only after dataset-level approval |
| `official_open_api` | Official API documented for open public reuse without registration or external approval | Allowed after exact endpoint and terms validation |
| `official_public_document` | Public webpage, PDF, bulletin, law, report, or announcement | Read/cite/summarize only after terms and copyright review; not automatically an open dataset |
| `licensed_or_registered_api` | API requiring account, subscription, agreement, credential approval, or payment | Blocked under the active profile |
| `government_data_sharing` | Government data that is not published as open data | Blocked under the active profile; ASIE will not request or ingest it |
| `personal_data` | Data relating to an identified or identifiable individual | Blocked under the active profile |
| `restricted_or_classified` | Restricted, confidential, secret, top secret, security, operational, or otherwise protected data | Prohibited |
| `unknown` | Ownership, classification, license, terms, or lawful purpose cannot be proven | Deny by default |

Public accessibility is not legal permission. `HTTP 200`, search-engine indexing, or absence of login does not prove that automated collection, reuse, republication, commercial use, or AI processing is permitted.

## 4. Authoritative Source Order

For discovery, ASIE uses this order:

1. National Open Data Platform and National Data Bank (`data.gov.sa`).
2. Official agency dataset catalog or documented official API.
3. Official ministry, authority, regulator, fund, municipality, university, or public institution publication.
4. Official public documents as outbound references or citations only.

If a dataset is not open, discovery ends with `blocked`; ASIE does not initiate a data-sharing request under the active profile.

The phrase `all ministries and authorities` means registry coverage and continuous discovery. It does not mean that every entity has an API, that every dataset is open, or that ASIE may crawl every government domain.

## 5. Mandatory Source Registry

Every dataset, endpoint, document feed, or bounded website path is a separate registry record. Domain-level blanket approval is prohibited.

Required fields:

```json
{
  "source_id": "uuid",
  "source_owner_ar": "string",
  "source_owner_en": "string",
  "owner_type": "ministry|authority|regulator|fund|municipality|university|public_institution",
  "official_domain": "https://example.gov.sa",
  "dataset_or_endpoint_url": "https://example.gov.sa/open-data/dataset",
  "route": "official_open_dataset",
  "data_classification": "public|restricted|confidential|secret|top_secret|unknown",
  "contains_personal_data": false,
  "contains_sensitive_personal_data": false,
  "lawful_purpose_id": "string",
  "license_name": "string",
  "license_url": "string",
  "license_version_or_hash": "sha256",
  "terms_url": "string",
  "terms_snapshot_hash": "sha256",
  "allowed_uses": ["analysis", "aggregation", "citation"],
  "prohibited_uses": ["redistribution_raw"],
  "commercial_use_status": "allowed|prohibited|unclear",
  "attribution_text_ar": "string",
  "attribution_text_en": "string",
  "access_method": "api|file_download|reference_link",
  "authentication_method": "none",
  "approved_paths": ["/open-data/"],
  "allowed_http_methods": ["GET", "HEAD"],
  "rate_limit_policy": "string",
  "robots_review": "pass|block|not_applicable",
  "storage_region": "string",
  "cross_border_processing": false,
  "retention_policy_id": "string",
  "security_control_profile": ["NCNICC-1:2025", "DCC-1:2022"],
  "legal_review_status": "pending|approved|rejected|expired|suspended|revoked",
  "legal_approver_id": "string",
  "privacy_approver_id": "string",
  "cybersecurity_approver_id": "string",
  "business_owner_id": "string",
  "approved_at": "iso_datetime",
  "review_due_at": "iso_datetime",
  "last_terms_check_at": "iso_datetime",
  "last_successful_fetch_at": "iso_datetime",
  "kill_switch": true
}
```

No record may become `approved` while classification, terms, license, permitted use, legal basis, retention, or an applicable approval is unknown.

## 6. Pre-Activation Approval Gate

The connector remains disabled until all applicable checks pass:

1. Official ownership and endpoint authenticity are proven.
2. Dataset route is classified correctly and is either `official_open_dataset` or `official_open_api`; every other route is blocked or reference-only.
3. The exact license and terms are captured, versioned, and reviewed.
4. Intended purpose and output uses fit the license and source terms.
5. Data classification is `public` for automatic open-data ingestion.
6. Personal-data detection is completed before content enters analytics, vectors, AI, or reports.
7. PDPL lawful basis, transparency, minimization, rights handling, retention, processor terms, breach handling, and DPIA requirements are assessed when applicable.
8. Any personal-data or unresolved cross-border condition blocks the dataset from this profile instead of opening an exception route.
9. Applicable NCA profile is selected: `NCNICC`, `ECC`, `DCC`, `CCC`, `CSCC`, or another sector-specific control set.
10. Credentials use least privilege and backend-only secret storage.
11. Fetch scope, methods, redirects, file types, sizes, and rate limits are bounded.
12. Legal, privacy, cybersecurity, and business approvals are recorded according to applicability.
13. A kill switch, incident owner, and revocation procedure exist.

Silence, an unanswered request, or an unavailable terms page is not approval.

## 7. Open Data Route

For an approved open dataset:

1. Prefer the official API or machine-readable published resource.
2. Store dataset identifier, publisher, license, release date, update cadence, schema, checksum, and source URL.
3. Preserve required attribution and link to the original dataset.
4. Do not imply government endorsement of ASIE, its analysis, or its conclusions.
5. Do not alter official labels in a way that misrepresents the data.
6. Separate raw official facts from ASIE-derived calculations and AI explanations.
7. Mark transformations, joins, imputations, filtering, and calculation versions.
8. Revalidate license, terms, classification, schema, and endpoint status before scheduled ingestion.

## 8. Government Data-Sharing Route: Disabled

If the data is not expressly open/public for reuse, the open-data connector must stop. ASIE r15 does not request, receive, or ingest agreement-based government data.

The following description is retained only as a legal boundary and must not be implemented as an active ASIE ingestion route:

1. Submit the request through the relevant entity Data Management Office or approved National Data Bank/Data Marketplace process.
2. Document the legitimate purpose, legal basis or justified operational need, minimum fields, classification, format, frequency, recipients, security controls, retention, destruction, and third parties.
3. Execute the required Data Sharing Agreement or controls template.
4. Use the approved secure sharing channel. ASIE's internal System Bus must not be confused with the Saudi Government Service Bus.
5. Keep authorization expiry, revocation, usage restrictions, and audit rights enforceable in code.
6. Destroy, anonymize, or revoke access at purpose completion or agreement termination as required.

No crawler may substitute for a denied, unanswered, restricted, or agreement-based data-sharing request. No Admin feature flag may enable this route.

## 9. Personal Data and PDPL Gate

The following are automatic stop triggers and exclude the source from `strict_open_data_only_v1`:

- Names, national IDs, account identifiers, phone numbers, emails, precise locations, IP/device identifiers, biometrics, financial records, health data, employment records, or other identifiable information.
- Data that becomes identifying after combining datasets.
- Free text or documents that may contain personal or sensitive personal data.
- Transfer to an AI, analytics, storage, notification, or cloud provider outside the approved processing scope.

Mandatory controls:

- Purpose limitation and data minimization.
- Documented lawful basis and privacy notice where required.
- Data subject rights workflow.
- Processor and subprocessor inventory.
- Encryption, least privilege, masking, pseudonymization, and access audit.
- Retention and verifiable deletion.
- Privacy Impact Assessment when applicable.
- Personal data breach detection, escalation, and notification workflow.
- Cross-border transfer assessment and approved safeguard before transfer.

AI and vector stores receive only approved, minimized, and sanitized content. Raw personal data must not be sent to AI for convenience.

## 10. Controlled Retrieval Rules

### Allowed

- Documented official API under its exact scope.
- Official downloadable CSV, XLSX, JSON, XML, PDF, or other published resource permitted by the source.
- Read-only retrieval from exact approved open-data API or file paths.
- Honest identification of the ASIE client where technically supported.
- Respect for source rate limits, `Retry-After`, cache controls, and published schedules.

### Hard Block

- CAPTCHA solving or bypass.
- Rotating proxies to evade blocking or rate limits.
- Account sharing, stolen sessions, browser-cookie replay, credential stuffing, or impersonation.
- Login automation not expressly authorized.
- Access to hidden endpoints, undocumented private APIs, admin panels, object storage listings, source code, backups, or directory enumeration.
- Circumventing robots rules, paywalls, WAF, access controls, geographic restrictions, or technical protection measures.
- Continuing after `401`, `403`, repeated `429`, legal notice, cease-and-desist, or source revocation.
- Automated form submission, mutation, deletion, or non-read HTTP methods unless an approved API contract expressly requires them.
- Scraping any source under the strict profile; machine access must use an approved official open API or published machine-readable open-data resource.

`robots.txt` is a mandatory operational signal but is not, by itself, proof of legal permission. Source terms, license, authorization, classification, and applicable law remain controlling.

## 11. Runtime Security Guard

Every retrieval executes through a hardened backend adapter with:

- Egress allowlist by scheme, host, port, path, and method.
- DNS and redirect revalidation to block SSRF, private IPs, metadata services, and domain pivoting.
- TLS certificate validation.
- Per-adapter identity, credentials, quotas, and concurrency limits.
- Secret vault, rotation, and no secrets in logs or AI prompts.
- File type, response size, decompression ratio, timeout, and redirect limits.
- Malware scanning and parser sandboxing.
- HTML/script sanitization and active-content removal.
- Prompt-injection labeling: retrieved text is untrusted data, never system instruction.
- Schema validation and schema-drift quarantine.
- Hashing, provenance, and immutable access-decision audit.
- Circuit breaker and immediate kill switch.

## 12. Evidence Ledger

Every accepted item must include:

| Field | Requirement |
| --- | --- |
| `evidence_id` | Immutable unique ID |
| `source_id` | Approved registry record |
| `publisher` | Official publisher |
| `source_url` | Exact original URL |
| `dataset_id` | Official dataset identifier when available |
| `license_name` and `license_url` | Required for open-data reuse |
| `published_at` and `retrieved_at` | Source and collection time |
| `content_hash` | Integrity checksum |
| `schema_version` | Parser/schema traceability |
| `classification` | Data classification |
| `personal_data_status` | `none`, `sanitized`, `approved`, or `blocked` |
| `transformation_log` | Normalization and calculation lineage |
| `freshness_status` | `fresh`, `stale`, `expired`, or `revoked` |
| `approval_decision_id` | Compliance decision trace |
| `language` | Arabic/English source language |
| `attribution` | Required user-facing attribution |

Evidence without the complete ledger cannot enter Finance, Decision, Reports, AI context, or Pinecone.

## 13. Change, Suspension, and Incident Rules

Immediately suspend a connector when:

- Terms, license, domain ownership, endpoint, authentication, classification, or permitted use changes.
- Approval expires or an approver revokes it.
- The source requests suspension or blocks access.
- Personal or classified data appears unexpectedly.
- Data integrity, malware, prompt injection, schema drift, or exfiltration risk is detected.
- A credential, token, or dataset is exposed.
- Applicable legal or NCA control requirements change.

Suspension must stop new retrievals, quarantine pending content, invalidate affected caches, notify Security/Privacy/Legal owners, preserve forensic evidence, and create an immutable incident event. Re-enabling requires a new approval decision.

## 14. Platform Placement

| Platform Area | Required Capability |
| --- | --- |
| Admin > Source Registry | Dataset-level records, ownership, route, classification, license, terms, approvals |
| Admin > Compliance Queue | Legal, privacy, cybersecurity, and business review workflow |
| Admin > Connector Health | Rate limits, failures, schema drift, last fetch, suspension, kill switch |
| Admin > Data Lineage | Evidence ledger, transformations, consumers, deletion and cache invalidation |
| Admin > Incidents | Unauthorized access, data leakage, source revocation, containment and escalation |
| Market Intelligence | Only approved source discovery and evidence packs |
| Reports | Source, retrieval date, freshness, license attribution, and transformation disclosure |
| User Settings | Privacy rights, consent where it is the applicable basis, export, correction, deletion requests |

## 15. Required Socket Contracts

| Socket ID | Owner | Accepted Messages | Returned Messages |
| --- | --- | --- | --- |
| `compliance.govdata.review.v1` | Audit / Observability Module | `govdata.access.review.requested.v1` | `govdata.access.decision.issued.v1` |
| `market.govdata.fetch.v1` | Market Intelligence Module | `govdata.fetch.requested.v1` | `govdata.fetch.completed.v1`, `govdata.fetch.blocked.v1` |
| `audit.govdata.event.v1` | Audit / Observability Module | All `govdata.*` audit events | `govdata.audit.recorded.v1` |
| `admin.govdata.control.v1` | Admin Module | `govdata.source.suspend.requested.v1`, `govdata.source.reapprove.requested.v1` | Audited status result |

All messages require Contract ID, Socket ID, Correlation ID, Security Context, workspace scope, source ID, purpose ID, decision ID where applicable, timestamp, and audit result.

## 16. Required Decisions and States

```text
discovered
-> pending_classification
-> pending_terms_review
-> pending_privacy_review
-> pending_cybersecurity_review
-> pending_legal_approval
-> approved_disabled
-> enabled
-> degraded | suspended | expired | revoked | rejected
```

Only `enabled` may perform a scheduled or user-triggered retrieval. Any missing policy result is a deny result.

## 17. Official Saudi References

The implementation must link to the current official Arabic version when interpretation differs. References verified on 2026-07-13:

1. SDAIA/NDMO Open Data Policy: <https://sdaia.gov.sa/ar/SDAIA/about/Files/RegulationsAndPolicies07.pdf>
2. National Open Data and National Data Bank: <https://data.gov.sa/ar>
3. National Data Bank Terms and Conditions: <https://data.gov.sa/ar/policies/terms>
4. NDMO Data Sharing Policy: <https://dgp.sdaia.gov.sa/wps/wcm/connect/b5d1907f-1b54-469d-8609-204ede2fa928/Data%2BSharing%2BPolicy.pdf>
5. NDMO Data Classification Policy: <https://sdaia.gov.sa/en/SDAIA/about/Files/RegulationsAndPolicies01.pdf>
6. Personal Data Protection Law: <https://laws.boe.gov.sa/BoeLaws/Laws/LawDetails/b7cfae89-828e-4994-b167-adaa00e37188/1>
7. PDPL Implementing Regulations: <https://www.uqn.gov.sa/details?p=23595>
8. Personal Data Transfer Outside the Kingdom Regulation: <https://www.uqn.gov.sa/details?p=23597>
9. Anti-Cyber Crime Law: <https://laws.boe.gov.sa/Boelaws/Laws/LawDetails/25df73d6-0f49-4dc5-b010-a9a700f2ec1d/1>
10. Copyright Law: <https://laws.boe.gov.sa/BoeLaws/Laws/LawDetails/67d159e6-ee98-4efc-a2ee-a9a700f17083/1>
11. NCA Essential Cybersecurity Controls `ECC-2:2024`: <https://nca.gov.sa/en/regulatory-documents/controls-list/ecc/>
12. NCA Data Cybersecurity Controls `DCC-1:2022`: <https://nca.gov.sa/en/regulatory-documents/controls-list/dcc/>
13. NCA Cloud Cybersecurity Controls `CCC-2:2024`: <https://nca.gov.sa/en/regulatory-documents/controls-list/ccc/>
14. NCA Non-CNI Private Sector Entities Cybersecurity Controls `NCNICC-1:2025`: <https://nca.gov.sa/ar/regulatory-documents/controls-list/ncnicc/>
15. DGA API Guideline: <https://dga.gov.sa/ar/Guideline-Application-Programming-Interfaces>

The legal register must be reviewed continuously. A URL list in documentation is not a substitute for monitoring official amendments, circulars, sector regulations, and formal legal advice.

## 18. Final Stop Rule

```text
IF lawful access cannot be proven,
OR classification is unknown,
OR terms/license cannot be captured,
OR personal-data obligations are unresolved,
OR cross-border processing is unresolved,
OR required security controls are not implemented,
OR human approval is missing or expired,
THEN deny, audit, notify, and do not fetch.
```
