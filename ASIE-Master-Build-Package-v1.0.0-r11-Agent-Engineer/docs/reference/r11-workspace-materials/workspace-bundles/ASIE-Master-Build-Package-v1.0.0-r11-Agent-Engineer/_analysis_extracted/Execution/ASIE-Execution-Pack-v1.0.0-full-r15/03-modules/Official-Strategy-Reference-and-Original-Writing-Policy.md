# Official Strategy Reference and Original Writing Policy

## سياسة المراجع الاستراتيجية الرسمية والكتابة الأصلية

**Status:** Mandatory  
**Profile:** `official_strategy_reference_only_v1`  
**Source access:** Reference-only; no automated retrieval  
**Verified:** 2026-07-13

## 1. Purpose

ASIE may use selected official Saudi strategy and government-service pages to understand national direction, design better questions, and write original ASIE alignment material.

تستخدم هذه الصفحات للاستئناس وفهم الاتجاهات الوطنية وبناء أسئلة المواءمة، وليس لنسخ النص أو إعادة نشر الصفحة أو تكوين قاعدة محتوى منها.

These references are not:

- Open datasets.
- Runtime evidence feeds.
- Legal or regulatory controls by themselves.
- Proof of government approval, certification, partnership, or endorsement.
- Permission to copy text, images, charts, icons, trademarks, or page structure.

## 2. Binding Rule

Every listed page is `reference_only`. The ASIE backend must not fetch, crawl, mirror, snapshot, parse, summarize, embed, vectorize, monitor, or index the target content.

The permitted workflow is:

```text
Authorized human curator opens the official page manually
-> records source metadata and review date
-> writes an original ASIE interpretation in their own words
-> links each alignment theme to the official page
-> Legal/Content/Governance reviewer checks originality and accuracy
-> approved ASIE alignment card becomes available to UI and AI
```

AI receives the approved ASIE-authored alignment card, never the copied source page or a full-text extraction.

## 3. Canonical Reference Catalog

The duplicate SDAIA strategy URL is normalized to one canonical record without the fragment suffix.

| ID | Official reference | Canonical URL | ASIE use | Status |
| --- | --- | --- | --- | --- |
| `STRAT-REF-SDAIA-TERMS` | SDAIA Portal Terms and Conditions / شروط وأحكام بوابة سدايا | `https://sdaia.gov.sa/ar/SDAIA/AboutPortal/Pages/TermsAndConditions.aspx` | Guide lawful portal use, attribution, IP caution, and non-copying review | Reference only; automated request rejected during verification |
| `STRAT-REF-NCA-NCS` | National Cybersecurity Strategy / الاستراتيجية الوطنية للأمن السيبراني | `https://nca.gov.sa/ar/national-cybersecurity-strategy/` | Strategic security, resilience, trust, governance, capability, and growth alignment | Reference only |
| `STRAT-REF-GOV-EPART` | GOV.SA E-Participation / منصة المشاركة الإلكترونية | `https://eparticipation.my.gov.sa/` | Participation, consultation, feedback, co-creation, inclusion, and transparency patterns | Reference only |
| `STRAT-REF-DGA-SDG` | DGA Sustainable Development / التنمية المستدامة | `https://dga.gov.sa/ar/sustainable-development` | Sustainability and SDG alignment questions | Reference only |
| `STRAT-REF-DGA-DT` | DGA Digital Transformation / التحول الرقمي | `https://dga.gov.sa/ar/digital-transformation` | Digital-first, user-centricity, governance, interoperability, lifecycle, and capability themes | Reference only |
| `STRAT-REF-SDAIA-NSDAI` | National Strategy for Data and AI / الاستراتيجية الوطنية للبيانات والذكاء الاصطناعي | `https://sdaia.gov.sa/ar/SDAIA/SdaiaStrategies/Pages/NationalStrategyForDataAndAI.aspx` | National data and AI alignment themes | Reference only; automated request rejected during verification |

## 4. Source-Specific Boundaries

### 4.1 SDAIA Terms and Conditions

- The terms page is a governing reference, not reusable content.
- Its current text must be reviewed manually by an authorized legal/content reviewer because automated access was rejected during verification.
- ASIE stores only URL, official title, review date, reviewer, status, and original internal conclusions.
- No terms text, screenshots, logos, HTML, or extracted clauses enter AI, vectors, reports, or product copy.
- Any uncertainty results in stronger non-copying and reference-only treatment.

### 4.2 National Cybersecurity Strategy

- Use the strategy to frame original ASIE objectives around resilience, risk reduction, trust, governance, national capability, research, and secure growth.
- Do not copy strategic descriptions, diagrams, objectives, or implementation-path wording.
- Do not treat the strategy page as an implementation control catalog.
- Mandatory cybersecurity compliance continues to come from the applicable NCA controls such as NCNICC, ECC, DCC, CCC, CSCC, and sector requirements.
- Reports may say `Aligned for consideration with national cybersecurity strategy themes`; they must not say `NCA approved` or `NCA compliant` based on this reference.

### 4.3 GOV.SA E-Participation

- Use the service model to inspire original ASIE features for consultations, feedback, suggestions, co-creation, inclusion, status visibility, and closing the feedback loop.
- Do not collect consultation listings, public submissions, participant data, complaints, ideas, platform metrics, logos, or page content.
- Do not submit forms, vote, comment, authenticate, or interact with consultations on behalf of ASIE users.
- Any actual open dataset linked from the platform must pass the separate `strict_open_data_only_v1` dataset gate.

### 4.4 DGA Sustainable Development

- Use the page to create original sustainability questions and map projects to applicable environmental, social, economic, and governance themes.
- Do not reproduce the page's explanations, lists, visual assets, or program descriptions.
- ASIE may reference official SDG names where required for factual identification, while writing its analysis independently.
- Do not claim DGA or UN certification, scoring, or endorsement.

### 4.5 DGA Digital Transformation

- Use the page as an orientation index for original ASIE design questions covering digital-first service, user focus, governance, interoperability, data governance, lifecycle management, capability, and emerging technology.
- Do not treat the overview page as a substitute for an exact DGA regulation, standard, policy, or implementation guide.
- Formal compliance requirements must cite the exact current regulatory document, not this overview page.
- Do not copy taxonomy, page layout, diagrams, or descriptive text.

### 4.6 National Strategy for Data and AI

- Use the strategy only to build original national-alignment themes for responsible data and AI, capability, innovation, governance, and economic development after manual review.
- The page rejected automated access during verification, so no backend fetch, browser automation, cache service, or search-result reconstruction is allowed.
- Do not copy text, objectives, graphics, targets, or branded terminology beyond unavoidable official names.
- Do not claim SDAIA approval, NSDAI certification, or official measurement of ASIE.

## 5. Strategy Alignment Card

Only an approved ASIE-authored card may be stored:

```json
{
  "reference_id": "STRAT-REF-NCA-NCS",
  "publisher_ar": "الهيئة الوطنية للأمن السيبراني",
  "publisher_en": "National Cybersecurity Authority",
  "official_title_ar": "الاستراتيجية الوطنية للأمن السيبراني",
  "official_url": "https://nca.gov.sa/ar/national-cybersecurity-strategy/",
  "access_class": "reference_only",
  "purpose": "inspiration_and_alignment_only",
  "source_language": "ar",
  "reviewed_at": "iso_datetime",
  "reviewer_id": "uuid",
  "original_asie_themes": [],
  "original_asie_questions": [],
  "original_asie_interpretation": "string",
  "not_legal_control": true,
  "not_government_endorsement": true,
  "originality_review_status": "pending|approved|rejected|expired",
  "accuracy_review_status": "pending|approved|rejected|expired",
  "review_due_at": "iso_datetime"
}
```

Forbidden fields include source HTML, full text, screenshots, images, logos, paragraphs, copied bullet lists, embeddings, or reconstructed source content.

## 6. Original Writing Standard

ASIE-authored material must:

1. Begin from the ASIE product or project question, not from the source sentence structure.
2. Synthesize themes across approved cards in original organization and wording.
3. Separate fact, ASIE interpretation, recommendation, and implementation decision.
4. Cite the official page for the alignment theme.
5. Preserve official names accurately in Arabic and English.
6. Use `مواءمة استرشادية` or `alignment reference`, never `اعتماد`, `تصديق`, `موافقة`, or `certified`.
7. Pass accuracy, originality, and government-endorsement review before publication.
8. Be regenerated or withdrawn when a reference card expires.

Verbatim quotation is disabled by default. Only an unavoidable official title, formal name, or legally required short identifier may be used without a separate quotation review.

## 7. AI Guard

AI may:

- Draft original ASIE prose from approved ASIE-authored themes and questions.
- Suggest project-specific alignment questions.
- Explain that the output is an ASIE interpretation with a link to the official source.

AI must not:

- Browse or fetch the target page.
- Receive copied source text, screenshots, page HTML, or embeddings.
- Continue a source phrase, imitate page structure, or reconstruct unavailable text from search snippets.
- Present a strategy theme as law, regulation, mandatory control, official assessment, or government endorsement.
- Invent objectives, metrics, dates, targets, quotations, or government positions.

## 8. Platform Placement

| Platform area | Capability |
| --- | --- |
| Admin > National Alignment References | Canonical URLs, publisher, status, review dates, assigned reviewers, link-out |
| Admin > Originality Review Queue | Accuracy, originality, attribution, endorsement, expiry, approve/reject |
| Project Wizard > Alignment Questions | Optional approved ASIE-authored questions; no copied source content |
| Market Intelligence > Reference Cards | Metadata and approved ASIE interpretations only |
| AI Advisory > Alignment Context | Approved card fields only; source content excluded |
| Reports > National Alignment | ASIE interpretation, source link, review date, and non-endorsement disclaimer |

No new Layer, Controller, Bus, Heart, or Module is introduced.

## 9. Required Contracts and Messages

### Sockets

- `compliance.strategy.reference.review.v1` owned by `Audit / Observability Module`.
- `market.strategy.reference.v1` owned by `Market Intelligence Module`.
- `audit.strategy.reference.event.v1` owned by `Audit / Observability Module`.

### Messages

- `market.strategy.reference.card.submit.requested.v1`
- `market.strategy.reference.card.approved.v1`
- `market.strategy.reference.card.rejected.v1`
- `market.strategy.alignment.requested.v1`
- `market.strategy.alignment.pack.v1`
- `audit.strategy.reference.event.v1`
- `audit.strategy.reference.recorded.v1`

Every request carries workspace, actor, reference ID, card version, reviewer decisions, language, expiry, and audit context through the existing Socket Contract Layer, APP, System Bus, and Bus Controller governance.

## 10. Stop Rule

```text
IF source content is copied, fetched, mirrored, embedded, reconstructed, or stored,
OR the card lacks accuracy/originality review,
OR the output implies a legal requirement or government endorsement,
OR the exact formal control is not separately cited for a compliance claim,
THEN reject, audit, and do not publish.
```
