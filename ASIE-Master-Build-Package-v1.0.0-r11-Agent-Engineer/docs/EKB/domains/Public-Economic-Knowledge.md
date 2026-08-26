# Public Economic Knowledge

## Authority

- Change gate: `docs/ACR-FC20-05-PUBLIC-ECONOMIC-KNOWLEDGE-2026-08-23.md`
- Program package: `FOUNDATION-COMPLETE-20 / FC20-05`
- Runtime status: offline/dark implementation only; live activation blocked.

## Boundary

Public economic knowledge is platform-owned, public, cited context used to
support feasibility research. It is not:

- customer/project data;
- a procurement supplier catalog;
- a Finance input until a separate approved assumption contract admits it;
- a Snapshot, Verdict, promise of project success, or promise of funding;
- permission to copy private or subscription research.

Saudi official sources govern Saudi regulatory and national claims. World Bank,
IMF, and other official international institutions provide comparisons and
scenarios. McKinsey and similar private sources are analytical references only
unless a separate permission record explicitly authorizes bounded ingestion.

## Source and record rules

- The versioned source registry is the admission authority.
- Official open sources may use `official_open_auto`; ambiguous terms, source
  changes, sensitive content, corruption, or injection indicators quarantine
  the candidate instead of indexing it.
- Tavily extraction or bounded crawl is selected by the registry. Crawl depth,
  result count, domain, and path roots are server-owned, and every returned URL
  is re-admitted before its content can enter the canonical corpus.
- Every record exposes publisher, URL, license, attribution, dates, geography,
  sector, unit, version, freshness, confidence, and evidence reference.
- The canonical local corpus is the source of truth. Pinecone is a derived,
  disposable index and must be rebuildable.
- Retrieved Pinecone hits are not trusted merely because they came from the
  derived namespace: record ID, field types, safe license reference, content
  hash, evidence lineage, retrieval time, derived freshness, expiry, authority,
  admission, confidence, score, and content anomalies are revalidated.
- Public writes/deletes require the exact platform workload. Tenant-authenticated
  reads are charged and audited to the requesting tenant, but never persist the
  tenant query or project context in the public corpus.

## Feasibility use

Permitted uses include market size evidence, demand context, competition
signals, funding-cost context, government spending, investment opportunities,
Vision 2030 alignment, and sensitivity assumptions. Each use must preserve the
evidence fields and distinguish fact, estimate, assumption, interpretation,
and gap. Missing unit/date/geography/source or expired evidence causes
abstention, not an invented value.

## Protected dependencies

FC20-05 must not import from or mutate AAS Kernel, ProjectRunWorkflow, Finance,
Snapshot Assembly, or Decision Council. Any future production Pre-Run wiring
requires the appropriate AIA/AAS change request and parity tests.
