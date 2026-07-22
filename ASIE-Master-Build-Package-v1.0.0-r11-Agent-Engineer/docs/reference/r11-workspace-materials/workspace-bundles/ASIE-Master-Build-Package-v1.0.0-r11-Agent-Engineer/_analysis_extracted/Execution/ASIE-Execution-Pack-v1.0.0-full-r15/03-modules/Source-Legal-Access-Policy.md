# Source Legal Access Policy

## سياسة الوصول القانوني للمصادر

**Status:** Mandatory and deny-by-default  
**Detailed government-data policy:** `Open-Government-Data-Integration-and-Legal-Access.md`
**Active operating profile:** `Strict-Open-Data-Only-Source-Profile.md`

## Governing Rule

A source is not approved because it is public, searchable, reachable, official, or hosted on a `gov.sa` domain.

لا يعتمد المصدر لمجرد أنه عام أو ظاهر في البحث أو متاح تقنيًا أو رسمي أو داخل نطاق حكومي.

Every dataset and API endpoint requires a separate, current, auditable access decision. Under `strict_open_data_only_v1`, bounded crawling is not an eligible ingestion route.

## Access Classes

| Class | Arabic | Default |
| --- | --- | --- |
| `official_open_dataset` | مجموعة بيانات مفتوحة رسمية | Eligible only with explicit public-reuse terms and no external approval |
| `official_open_api` | API رسمي مفتوح | Eligible only when documented, read-only, public, and approval-free |
| `official_public_document` | وثيقة رسمية عامة | Reference/citation only; not an ingestion route unless expressly open |
| `licensed_or_registered_api` | API مرخص أو يتطلب تسجيلًا | Blocked under the active profile |
| `government_data_sharing` | مشاركة بيانات حكومية غير مفتوحة | Blocked under the active profile |
| `marketplace_public` | سوق عام | Reference only unless expressly published as reusable open data |
| `personal_data` | بيانات شخصية | Blocked under the active profile |
| `restricted_or_classified` | بيانات مقيدة أو مصنفة | Prohibited |
| `user_private_document` | مستند خاص من المستخدم | Private, workspace-scoped workflow only |
| `unknown` | غير محسوم | Deny |

## Mandatory Decision Inputs

- Official owner and exact endpoint.
- Data classification.
- Dataset license and version/hash.
- Website/API terms and version/hash.
- Intended purpose, users, outputs, and commercial-use status.
- Copyright and attribution requirements.
- Personal and sensitive personal data status.
- Data-sharing agreement or authorization where applicable.
- Cross-border processor/storage assessment.
- Retention and deletion rule.
- Applicable NCA control profile.
- Legal, Privacy/DPO, Cybersecurity, and Business approvals according to applicability.
- Approval expiry and kill switch.
- Proof that no source-specific registration, payment, login, contract, external approval, or credential issuance is required.

## Copyright and Report Handling

- Do not copy or republish full reports unless the exact license permits it.
- Store only necessary metadata, compliant extracts, structured facts, and citations.
- Keep government facts separate from ASIE transformations and opinions.
- Preserve required attribution and do not imply government endorsement.
- AI may summarize approved retrieved content; it may not decide that copying is lawful.

## Privacy

- Public availability does not remove PDPL obligations.
- Detect personal data before storage, analytics, AI, vector indexing, or reporting.
- Apply purpose limitation, minimization, lawful basis, rights handling, retention, deletion, processor governance, breach workflow, and transfer controls where applicable.
- Never expose user private documents as public evidence.
- Product analytics must be minimized and sanitized; anonymization claims require deterministic validation.

## Technical Access Prohibitions

- No CAPTCHA or WAF bypass.
- No proxy rotation to evade controls.
- No credential/session theft, sharing, replay, or impersonation.
- No hidden endpoint discovery or undocumented private API use.
- No continuation after explicit denial, source revocation, or repeated blocking.
- No scraping where source terms prohibit the intended automation or reuse.
- No direct UI, AI, Finance Engine, Kernel, or cross-Module source access.
- No ingestion from `reference_only` sources; the backend must not resolve their target URLs.

## Stop Rule

If any legal, privacy, licensing, classification, authorization, cybersecurity, or permitted-use question is unresolved, status is `pending_legal_approval` or `rejected`; automatic access must not run.

إذا لم يثبت السماح، فالقرار هو المنع والتدقيق والتصعيد، وليس التجربة.
