# LIVE-INTEL-001 — Governed External Acquisition and Deployment Foundation

Status: IMPLEMENTED ON FEATURE BRANCH — CI REQUIRED BEFORE MERGE  
Date: 2026-07-27  
Scope: live provider adapters, governed network gateway, Pinecone knowledge isolation, and production deployment package

## 1. Purpose

This package establishes the first executable foundation for live external intelligence and VPS deployment after the frontend surface baseline was completed.

It admits the following initial providers selected for ASIE:

| Provider | Assigned role | Initial configuration |
|---|---|---|
| DeepSeek | governed narrative and reasoning | `deepseek-v4-flash` |
| Tavily | search, extraction, site mapping, and governed crawl | API base `api.tavily.com` |
| Google Maps Platform | backend geocoding and Places search | Geocoding API v4 and Places API (New) |
| Pinecone | knowledge vector storage and semantic retrieval | existing index `vision2030-kb` |

The Pinecone console project identifier supplied for administration is not required by the runtime APIs and is not embedded in application code. Runtime access uses `PINECONE_API_KEY`, `PINECONE_INDEX=vision2030-kb`, and Describe Index to discover the data-plane host.

## 2. Architectural position

This package does not insert a component into the frozen analytical execution path.

```text
External APIs / governed crawl
→ Governed External Acquisition Gateway
→ source review / evidence eligibility / transformation lineage
→ approved intelligence context (future package)
→ existing AAS-governed execution
→ Snapshot Assembly
```

The current package stops before approved intelligence context and before the frozen AAS runtime.

Therefore:

- external payloads are marked `review_required`;
- external payloads are not eligible for controlled assumptions by default;
- DeepSeek outputs are narrative-only and require human review;
- Tavily results are discovery material, not evidence by themselves;
- Google Places results are not eligible for Pinecone persistence until terms review permits the intended storage;
- Pinecone is not a Snapshot, Evidence Ledger, or source of sovereign truth.

## 3. Governed external acquisition gateway

`backend/external_acquisition.py` provides:

- disabled-by-default network policy;
- explicit host allowlist;
- HTTPS-only requests;
- ports restricted to 443;
- credentials-in-URL rejection;
- DNS resolution before transport;
- private, loopback, link-local, reserved, and non-global address blocking;
- redirect validation;
- response size limits;
- request timeout;
- per-host rate limiting;
- content-type validation;
- SHA-256 response digest;
- fail-closed `robots.txt` enforcement for direct HTML crawl;
- audit events that never store payloads, API keys, authorization headers, or provider secrets.

Enabling `ASIE_ALLOW_EXTERNAL_FETCH=true` is insufficient on its own. Every destination must also match `ASIE_EXTERNAL_ALLOWED_HOSTS`.

## 4. Provider clients

### 4.1 DeepSeek

The client calls the OpenAI-compatible Chat Completions endpoint using `deepseek-v4-flash` by default.

Required controls:

- prompt template identifier;
- SHA-256 prompt hash;
- context references;
- bounded messages and output tokens;
- narrative-only ownership;
- no controlled numbers;
- no financial ownership;
- no sovereign verdict;
- mandatory human-review state;
- prompt content not stored by ASIE transport/audit.

The client is not yet connected to the current `AIIntegrationShell`. Activating provider execution through that shell requires the applicable AIA IACR and tests.

### 4.2 Tavily

The client supports:

- Search;
- Extract;
- Crawl;
- Map.

Default controls:

- generated answer disabled in search;
- raw content disabled in broad search;
- Saudi Arabia country boost for general search;
- bounded result counts and crawl depth;
- external-domain expansion disabled in crawl/map;
- source URLs and provider request identifiers retained for subsequent evidence review;
- API key and optional Tavily project identifier passed only through protected headers/environment.

### 4.3 Google Maps Platform

The client supports:

- backend Geocoding API v4 forward geocoding;
- Places API (New) text search;
- Arabic language and Saudi region defaults;
- coordinate and radius validation;
- field masks to limit returned data;
- API key in `X-Goog-Api-Key`, not in URLs.

The first persistence policy permits project location identity and Place ID. Broader Places data storage, caching, redistribution, or Pinecone ingestion requires a specific terms review.

### 4.4 Pinecone

The client is configured for the existing index:

```text
vision2030-kb
```

Controls:

- index host discovered through Describe Index;
- API version `2026-04` by default;
- support for integrated text embedding workflows;
- intended embedding model `multilingual-e5-large` when the index configuration supports it;
- deterministic hashed namespace per organization and project;
- no raw organization/project identifiers in namespace names;
- only `approved` records accepted;
- only `public` or `internal_non_sensitive` data accepted;
- every record requires source URL, source ID, and evidence reference;
- Google Places payloads are excluded until terms review;
- Pinecone retrieval requires evidence validation before use;
- Pinecone is explicitly not a sovereign source of truth.

The actual index embed model and field map must be verified using Describe Index after the production API key is installed. Upsert text expects the index field map to accept `chunk_text`.

## 5. Production deployment package

Deployment target: Hostinger VPS using Docker Compose.

Files:

```text
.env.production.example
docker-compose.production.yml
deploy/Caddyfile
deploy/hostinger-vps-deploy.sh
deploy/backup.sh
.github/workflows/deploy-hostinger.yml
```

The production stack includes:

- backend API;
- DIB API;
- built React/nginx frontend;
- Caddy reverse proxy;
- automatic HTTPS;
- HTTP/HTTPS public ports only;
- internal-only API ports;
- persistent ASIE data volume;
- persistent Caddy certificate/config volumes;
- container health checks;
- log rotation;
- read-only backend container filesystems with writable data volume;
- no-new-privileges;
- SQLite online backup script with integrity checks and retention.

## 6. GitHub production secrets

The manual deployment workflow requires:

```text
ASIE_DOMAIN
HOSTINGER_VPS_HOST
HOSTINGER_VPS_USER
HOSTINGER_VPS_SSH_KEY
DEEPSEEK_API_KEY
TAVILY_API_KEY
GOOGLE_MAPS_API_KEY
PINECONE_API_KEY
```

Optional:

```text
TAVILY_PROJECT
ASIE_TLS_EMAIL
```

The workflow is manual (`workflow_dispatch`) and uses a protected GitHub `production` environment. Live provider network access is a manual choice at deployment time. When it is requested, all four provider secrets must be present.

No secret value is committed. The workflow creates a mode-600 environment file, uploads it to the VPS, deploys, and removes local temporary secret files.

## 7. DNS and VPS prerequisites

Before the first deployment:

1. Provision a Hostinger VPS with Docker Engine, Docker Compose v2, Git, and SSH access.
2. Point the selected domain A/AAAA record to the VPS.
3. Open inbound TCP 80 and 443 and UDP 443 if HTTP/3 is desired.
4. Add the production secrets to the GitHub repository production environment.
5. Restrict provider keys:
   - Google key to required server APIs and server IP where supported;
   - Pinecone key to the intended project/index scope;
   - DeepSeek and Tavily keys to production accounts and budget controls.
6. Run deployment initially with external fetch disabled.
7. Confirm TLS, API health, authentication, project creation, DIB, run, Snapshot, and reports.
8. Run provider preflight and terms-review acceptance.
9. Deploy again with governed external fetch enabled.

## 8. Not implemented by this package

The following remain separate controlled packages:

- public/live API endpoints exposed to the frontend for these providers;
- Google map component and user-consent UX;
- source-review persistence and connector job scheduler;
- approved intelligence context;
- national, market, global, strategic, and consulting intelligence engines;
- DeepSeek activation inside `AIIntegrationShell`;
- Pinecone ingestion jobs and retention/deletion UI;
- Tavily source-admission workflow;
- live use of provider outputs by the frozen AAS runtime;
- actual VPS deployment, because the domain, VPS access, and secret values are not available to the repository code.

## 9. Completion and merge rule

This package may merge only after:

- frontend build succeeds;
- backend compilation succeeds;
- all Python tests succeed;
- gateway SSRF, robots, allowlist, response-bound, and audit tests succeed;
- provider ownership and Pinecone isolation tests succeed;
- deployment package guard tests succeed;
- no frozen AAS runtime file is modified.
