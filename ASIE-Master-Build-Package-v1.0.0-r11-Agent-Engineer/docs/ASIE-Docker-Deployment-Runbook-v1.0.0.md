# ASIE Docker Deployment Runbook

## Current mode

Single-node Pilot using SQLite in the named volume `asie-data`. This is not a horizontally scaled production topology.

## Start

```powershell
docker compose build
docker compose up -d
docker compose ps
```

The public local entry point is `http://localhost:8080`; API traffic is proxied by Nginx. The API container is not published directly.

## Required checks

```powershell
Invoke-WebRequest http://localhost:8080/api/health
docker compose exec api python -m compileall -q backend
docker compose restart api
docker compose ps
```

## Data and recovery

SQLite is persisted in the `asie-data` volume. Before any production-like use, export a tested backup and restore it into a fresh volume. Do not run multiple API replicas against this SQLite volume.

## Explicit gates

- `ASIE_ALLOW_EXTERNAL_FETCH=false` remains mandatory.
- AI provider keys remain unset.
- HTTPS and a managed secret store are required before public exposure.
- `ASIE_PDF_RENDERER` must point to a tested renderer before PDF release is enabled.
- PostgreSQL/object storage are required before horizontal scaling.
