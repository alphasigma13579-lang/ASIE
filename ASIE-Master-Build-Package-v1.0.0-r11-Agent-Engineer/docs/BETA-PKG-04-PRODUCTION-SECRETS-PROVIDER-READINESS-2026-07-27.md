# BETA-PKG-04 — Production Secrets & Provider Readiness

Date: 2026-07-27
Status: Implemented in package branch; merge requires CI success.

## Purpose

Provide a production gate that verifies the presence of required provider credentials without reading, printing, persisting, or exposing their values.

## Required production secrets

- `DEEPSEEK_API_KEY`
- `TAVILY_API_KEY`
- `GOOGLE_MAPS_API_KEY`
- `PINECONE_API_KEY`

Optional settings:

- `TAVILY_PROJECT`
- `GOOGLE_MAP_ID`

## Implemented controls

1. Presence-only readiness report.
2. Missing-required-secret blocking result.
3. Recursive redaction helper for logs and payloads.
4. Manual GitHub Actions gate bound to the protected `production` environment.
5. No secret values in reports, artifacts, or test output.
6. No mutation of Finance, Snapshot, DIB, Decision Council, authentication, or tenant isolation.

## Workflow

Run:

`Actions → Production Provider Readiness → Run workflow`

The production job reads GitHub Environment secrets into process environment variables, checks presence only, and exits with code `2` when a required secret is missing. GitHub masks its own secret values, while the application report contains only boolean `present` flags.

## Readiness semantics

- `ready`: all four required secrets are present.
- `blocked`: one or more required secrets are missing.

A `ready` result proves credential presence only. It does not prove quota, billing, API entitlement, model availability, network reachability, or provider correctness. Provider-specific live preflight remains required before public beta.

## Hard boundaries

This package does not:

- store or rotate secrets;
- expose secrets through an API;
- enable external fetch automatically;
- modify `ASIE_ALLOW_EXTERNAL_FETCH`;
- invoke providers during pull-request CI;
- alter controlled numbers, Finance, Snapshot, or sovereign verdicts.

## Acceptance criteria

- all required secret names are canonical and consistent with `.env.production.example`;
- missing secrets fail the manual production gate;
- configured secrets produce a presence-only success report;
- tests prove values are absent from serialized reports;
- standard ASIE CI and package CI pass before merge.
