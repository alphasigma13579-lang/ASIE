# ACR-FC20-11 — Owner live market-context activation

**Date:** 2026-09-02
**Status:** Accepted for a guarded owner-only beta activation
**Extends:** ACR-FC20-02, ACR-FC20-03, ACR-FC20-05, and ACR-FC20-10

## Decision

ASIE may activate the live market-context path for the designated platform-owner
account on the closed beta domain only after every activation gate below passes.
This is not a public launch and does not open beta invitations. The path remains
disabled by default; source code or configured credentials alone do not authorize
external requests.

The path is limited to:

```text
confirmed project sector and location
  -> Google location and competitor discovery
  -> approved Tavily research
  -> governed Pinecone retrieval
  -> evidence-backed customer presentation
```

The location, reverse-geocoding, and competitor-discovery routes that support
this path inherit the same platform-owner authorization. The protected provider
readiness endpoint is also owner-only.

DeepSeek may explain accepted evidence in the selected customer language only. It
does not calculate financial outputs, decide funding, or execute an action.

## Authoritative inputs and customer boundary

- A user selects the sector and project location while creating or editing a
  project, and confirms them before live discovery.
- The live request is bound to the authenticated organization and the persisted,
  confirmed project values. Browser input cannot replace the project sector,
  country, or coordinates after that confirmation.
- Customer responses contain usable evidence, source attribution, freshness, and
  confidence. They do not expose provider diagnostics, internal IDs, hashes,
  contracts, engines, or runtime states.
- Google Places content is never admitted into Pinecone. Pinecone is a derived
  index; the governed evidence store remains the source of truth.
- A candidate, blocked, or reference-only source is never expanded into a
  crawlable source merely because it appears in a request or source policy.

## Invariants

This activation does not change Finance, Snapshot Assembly, AAS, or Decision
Council contracts. Market results are reviewable evidence only; they are not
financial facts, a project-success prediction, or a funding decision.

## Activation gates

Before the owner can use the path on the beta domain, the operator must prove:

1. Server-only secrets are held in Hostinger secrets; the Google browser key is
   restricted to the beta HTTPS origin and the server key is IP-restricted.
2. Provider-control-plane state, approved source scopes and terms, tenant/project
   authorization, and the emergency stop control all permit the exact request.
3. An authenticated, protected readiness check exposes status only and no secret
   material.
4. A limited owner canary proves manual location fallback, approved-source search,
   evidence presentation, error handling, and tenant isolation.
5. Provider failure, quota exhaustion, and slow-network paths remain operational
   incidents with retry guidance, not customer payment or upgrade prompts.

Until those gates pass, the UI shows the service as temporarily unavailable and
the server makes no external provider request. Invitations remain closed until
the owner canary succeeds and the separate protected administration interface is
ready.

## Administration and audit

The owner identity is an authenticated platform-admin account; its login address
and any credentials are deployment secrets and are not recorded here. A temporary
display name is not an authorization key. The future administration interface is
the only customer-safe place to manage invitations, provider readiness, and audit
views. Hostinger manages infrastructure and secrets, not ASIE users, projects, or
application authorization.

Each admitted or rejected market-context request is audited with its authenticated
actor, organization, project, outcome, and non-secret reason. Customer views show
only an actionable Arabic or English explanation appropriate to the selected
language.
