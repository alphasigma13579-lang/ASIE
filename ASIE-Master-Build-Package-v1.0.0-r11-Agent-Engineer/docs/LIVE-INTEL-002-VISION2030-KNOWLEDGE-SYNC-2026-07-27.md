# LIVE-INTEL-002 — Vision 2030 Knowledge Sync

**Status:** Implemented foundation, activation requires production secrets  
**Target index:** `vision2030-kb`  
**Cadence:** First day of every month at `03:17 UTC`, plus manual execution  
**Source policy:** Official Saudi Vision 2030 hosts only

## 1. Purpose

This package checks registered official Vision 2030 sources monthly, extracts authoritative content through the governed Tavily client, calculates a normalized SHA-256 digest, and writes to Pinecone only when content has changed.

Pinecone remains a retrieval index. It is not the sovereign source of truth. The official URL, content hash, source identifier, timestamps, and evidence reference remain attached to every admitted chunk.

## 2. Components

- `config/vision2030_sources.json` — governed official source registry.
- `backend/vision2030_kb_sync.py` — validation, extraction, normalization, hashing, chunking, change detection, Pinecone admission, stale-record cleanup, and state persistence.
- `.github/workflows/vision2030-kb-sync.yml` — monthly and manually dispatchable workflow.
- `tests/test_vision2030_kb_sync.py` — deterministic tests for no-op, changed content, stale cleanup, dry-run, and architectural boundaries.

## 3. Change-detection flow

```text
Official source registry
  → Tavily governed extraction
  → normalized content
  → SHA-256
  → compare with prior cached state
      → unchanged: no Pinecone write
      → changed: deterministic chunks + upsert + stale tail deletion
  → redacted summary artifact
```

The workflow restores the latest state through GitHub Actions cache and saves a new immutable cache entry after each run. The state contains URLs, hashes, record IDs, counts, and timestamps only. It contains no API keys or extracted source payloads.

## 4. Pinecone admission

All records are admitted through the existing `PineconeKnowledgeClient.upsert_approved_text` contract:

- `review_status=approved`
- `data_classification=public`
- deterministic organization/project namespace
- official `source_url`
- stable `source_id`
- evidence reference containing the SHA-256 version
- maximum 100 records per upsert request

When a changed source produces fewer chunks than its previous version, stale record IDs are deleted through the governed Pinecone transport.

## 5. Schedule

The workflow uses:

```yaml
schedule:
  - cron: "17 3 1 * *"
```

It runs on the latest commit of the default branch. A manual `workflow_dispatch` path supports a safe `dry_run=true` default.

## 6. Required production secrets

Configure these in the GitHub `production` environment:

- `TAVILY_API_KEY`
- `TAVILY_PROJECT` — optional
- `PINECONE_API_KEY`

The index name is not secret and is fixed to `vision2030-kb`.

## 7. Activation sequence

1. Merge this package after both CI paths pass.
2. Add Tavily and Pinecone secrets to the GitHub `production` environment.
3. Run **Vision 2030 Knowledge Sync** manually with `dry_run=true`.
4. Review the redacted summary artifact.
5. Run manually with `dry_run=false` for the first controlled admission.
6. Leave the monthly schedule enabled.

## 8. Source registry governance

The initial registry contains official Arabic and English Vision 2030 portals, the National Transformation Program page, and the official Open Data page. Exact official document/PDF URLs can be added as separate entries after verification.

A registry entry is rejected unless:

- the URL uses HTTPS;
- the hostname is `vision2030.gov.sa` or `www.vision2030.gov.sa`;
- authority is exactly `Saudi Vision 2030`;
- source IDs are unique.

## 9. Hard boundaries

This package does not import or modify:

- AAS Kernel
- Heart Controller
- System Bus
- Socket Contract Layer
- Project Run Workflow
- Finance Engine
- Decision Council
- Snapshot Assembly

The sync output explicitly reports:

- `source_of_truth=false`
- `snapshot_mutated=false`
- `finance_mutated=false`

## 10. Operational notes

- A missing or expired GitHub cache causes a full comparison baseline run and deterministic re-upsert; it does not delete the index or namespace.
- A source-level failure is recorded without secrets and does not silently admit partial content for that source.
- Scheduled runs fail when any enabled source fails, making the issue visible in GitHub Actions.
- The source registry should be reviewed whenever the official Vision 2030 portal changes document locations or publishing structure.
