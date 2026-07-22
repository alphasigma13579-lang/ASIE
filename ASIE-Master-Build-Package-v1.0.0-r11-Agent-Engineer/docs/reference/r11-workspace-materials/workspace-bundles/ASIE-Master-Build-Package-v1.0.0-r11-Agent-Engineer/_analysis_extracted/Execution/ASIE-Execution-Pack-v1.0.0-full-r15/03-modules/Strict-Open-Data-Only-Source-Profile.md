# Strict Open Data Only Source Profile

## ملف التشغيل الصارم للبيانات المفتوحة فقط

**Status:** Mandatory for ASIE r15  
**Profile ID:** `strict_open_data_only_v1`  
**Default:** Deny  
**Verified:** 2026-07-13

## 1. Owner Decision

ASIE may automatically retrieve and process only data that the publisher has expressly made available for public reuse without a source-specific application, subscription, account, contract, paid license, or external approval.

لا تستخدم ASIE الجلب الآلي إلا للبيانات التي صرح ناشرها صراحة بإتاحتها لإعادة الاستخدام العام، دون طلب خاص أو اشتراك أو حساب أو عقد أو ترخيص مدفوع أو موافقة خارجية.

An open-data license or published open-use policy is evidence of permission. It is not the same as a license that must be purchased, negotiated, registered, or individually approved.

وجود ترخيص بيانات مفتوحة أو سياسة استخدام مفتوح شرط إثبات، ولا يعني طلب ترخيص خاص من الجهة.

## 2. Eligible Routes

Only these routes may become `enabled`:

| Route | Conditions |
| --- | --- |
| `official_open_dataset` | Official publisher, public classification, explicit open-use terms, no individual approval, no login, no personal data, exact dataset record |
| `official_open_api` | Official documented API, public open-use terms, no registration or contract, read-only scope, published rate limits, exact endpoint record |

An official downloadable CSV, XLSX, JSON, XML, SDMX, or other machine-readable resource is preferred over HTML extraction.

## 3. Ineligible Routes

The following cannot be enabled under this profile:

- `licensed_or_registered_api`.
- `government_data_sharing`.
- Any source requiring login, account, API key approval, subscription, contract, payment, or case-specific permission.
- Personal, sensitive, micro, case-level, restricted, confidential, or classified data.
- A public webpage without explicit public-reuse terms.
- A marketplace listing, social network post, user profile, offer, comment, or other user-generated content that is visible but not published as open data.
- An official strategy, overview, terms, participation, or guidance page used for inspiration; these follow `official_strategy_reference_only_v1` and never become data feeds.
- A source whose terms or reuse status cannot be captured and revalidated.

There is no fallback from a blocked route to crawling, browser automation, search-result copying, third-party scraping APIs, proxy services, cached copies, or inferred private endpoints.

## 4. Decision Matrix

| Evidence | Decision |
| --- | --- |
| Official open-data policy + exact public dataset/API + compatible reuse terms | Candidate for internal approval and enablement |
| Government domain without dataset-level open-use evidence | Block |
| Public page indexed by search engines | Reference only or block |
| Registration or source-specific approval required | Block |
| Terms unavailable, `403`, ambiguous, or changed | Block |
| Personal or potentially identifying content | Block |
| Third-party marketplace with no official open-data/API grant | Reference only; no ingestion |

Internal ASIE legal/privacy/cybersecurity review remains mandatory. It validates that the open permission applies; it must never contact a source for permission and then treat the result as open data under this profile.

## 5. GASTAT Statistical Database

### Approved Candidate Identity

| Field | Value |
| --- | --- |
| Publisher | General Authority for Statistics / الهيئة العامة للإحصاء |
| Statistical database | `https://database.stats.gov.sa/home/landing` |
| Developer portal | `https://dp.stats.gov.sa/?locale=ar` |
| Reuse policy | `https://www.stats.gov.sa/ar/use-policy` |
| Route | `official_open_dataset` or `official_open_api` after endpoint verification |
| Strict profile | Eligible candidate |

The GASTAT use policy permits reuse of materials and data published through the website covered by that policy, including commercial reuse, while excluding trademarks, logos, and clearly identified third-party materials. The statistical database is an official GASTAT publication channel with export and API capabilities, but ASIE must verify that each exact database resource is covered by that policy or by equivalent published open-use terms before enabling it. Use must attribute GASTAT as the official source and disclose ASIE modifications or updates.

### Mandatory GASTAT Controls

1. Prefer an official documented API or export offered by the statistical database or developer portal.
2. Register every dataset and API endpoint separately; do not approve the whole domain or infer policy inheritance from a shared publisher.
3. Store title, dataset/table ID, dimensions, units, frequency, release date, revision status, source URL, retrieval time, and policy hash.
4. Display `Official GASTAT data / بيانات رسمية من الهيئة العامة للإحصاء` only for unchanged official facts.
5. Display `ASIE-derived calculation / معالجة أو حساب مشتق بواسطة ASIE` for filters, joins, rebasing, estimates, forecasts, or other transformations.
6. Attribute GASTAT and describe all transformations. Never imply that GASTAT reviewed or endorsed ASIE output.
7. Exclude logos, trademarks, third-party material, microdata, personal data, and any item carrying different terms.
8. Respect published API limits and stop on authentication, access denial, changed terms, or undocumented endpoints.
9. Revalidate the reuse policy and endpoint documentation before every scheduled release cycle.

## 6. Mostaql Projects

### Classification

| Field | Value |
| --- | --- |
| Source | `https://mostaql.com/projects` |
| Content | Publicly visible user-generated project listings |
| Open-data evidence | Not established |
| Official public API with open reuse grant | Not established |
| Terms page | `https://mostaql.com/p/terms`; automated retrieval returned `403` during verification |
| Strict profile | `reference_only`; automated ingestion blocked |

Public visibility is not an open-data license. ASIE must not crawl, scrape, copy, summarize at scale, store, embed, vectorize, republish, or create a derived trends dataset from Mostaql project listings under this profile.

### Permitted Mostaql Behavior

- Show a clearly labeled outbound link: `تصفح المشاريع المفتوحة على مستقل`.
- Allow a user to save the URL as a private bookmark.
- Allow the user to write an original private note that does not copy project text or personal data.
- Label the source `External reference - not ingested / مرجع خارجي غير مجمّع`.

### Prohibited Mostaql Behavior

- Automated requests to project listing or detail pages.
- Browser automation, pagination, feeds inferred from page code, undocumented endpoints, or third-party scraping APIs.
- Storage of project titles, descriptions, budgets, client names, usernames, offers, comments, skills, profile data, or screenshots.
- AI summarization or embeddings of page content.
- Market statistics, opportunity scores, or alerts derived from collected Mostaql listings.
- Circumventing `403`, CAPTCHA, WAF, login, rate limits, or other technical controls.

Mostaql may be reconsidered only if its operator publishes an official API or dataset with explicit reusable-data terms compatible with ASIE. A commercial third-party scraper does not satisfy this requirement.

## 7. Platform Placement

| Platform Area | Requirement |
| --- | --- |
| Admin > Source Registry | `profile_id`, route, open-use evidence, exact dataset/endpoint, terms hash, attribution, block reason |
| Admin > Strict Open Data Allowlist | Only enabled GASTAT or other exact official open datasets/APIs |
| Admin > Reference-Only Registry | Mostaql and other non-ingested outbound references |
| Market Intelligence | Query approved open datasets only; never resolve reference-only links server-side |
| Reports | Show publisher, exact source URL, retrieval date, open-use policy, freshness, and transformation label |
| User Interface | Distinct badges: `Open data`, `Official fact`, `ASIE-derived`, `Reference only` |

The UI must not use the words `integrated`, `synced`, or `monitored` for Mostaql. The accurate wording is `external link` or `reference only`.

## 8. Required Messages

| Message | Purpose |
| --- | --- |
| `govdata.strict_profile.evaluated.v1` | Records deterministic strict-profile eligibility |
| `govdata.open_source.enabled.v1` | Enables one exact approved open dataset/API |
| `govdata.open_source.blocked.v1` | Blocks an ineligible route with reason codes |
| `market.reference.link.saved.v1` | Saves a private outbound reference without fetching it |

All messages must use existing Socket Contract Layer, APP, System Bus, and Bus Controller governance. This profile does not create a new Layer, Controller, Bus, Heart, or Module.

## 9. Release Stop Rule

```text
IF the source needs registration, payment, contract, login, approval, or credentials,
OR open public-reuse evidence is absent or ambiguous,
OR the item contains personal, micro, restricted, or user-generated marketplace data,
THEN block automated ingestion.

IF a source is reference_only,
THEN permit only an outbound link and private user-authored notes;
DO NOT fetch the target URL.
```
