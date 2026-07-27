# ASIE Beta Readiness Package Program

**Document ID:** ASIE-BETA-READINESS-PACKAGE-PROGRAM-2026-07-27  
**Status:** Active execution baseline  
**Platform:** ALPHASIGMA Intelligence Engine — ASIE™  
**Target:** controlled technical beta, then public beta readiness

## 1. Verified starting position

The following capabilities are already implemented and SHALL NOT be rebuilt in this program:

- Dynamic Input Blueprint runtime and registry admission.
- DIB persistence, API, workspace, module adapters, and Snapshot lineage.
- Approved Input Manifest readiness and Project Run Manifest Gate.
- Controlled Finance Wiring.
- AAS Runtime Freeze and deterministic Finance Engine.

The remaining work is packaged around incomplete product paths and production activation.

## 2. Execution order

### BETA-PKG-01 — Dataset-to-DIB Mapping Completion

**Objective:** convert supported imported datasets into governed DIB candidate items and require explicit review before manifest approval.

**Scope:**

- canonical mapping contract from dataset columns/rows to DIB fields and items;
- deterministic rule-based mapping before any AI assistance;
- mapping confidence, provenance, unresolved fields, and rejection reasons;
- CSV/XLSX mapping workflow;
- preview, edit, accept, reject, and remap operations;
- persistence of mapping drafts and approved mappings;
- Approved Input Manifest admission only after explicit approval;
- controlled handoff to existing Finance Wiring;
- tests for tenant isolation, idempotency, zero values, duplicate rows, and invalid units.

**Not in scope:** PDF extraction, supplier quote extraction, changes to Finance formulas, or AAS frozen runtime files.

**Exit gate:** one CSV/XLSX dataset can travel through import → mapping review → approved manifest → controlled Finance input without raw-input bypass.

### BETA-PKG-02 — Product AI Interview

**Objective:** implement the first-entry path for users who only have a project idea.

**Scope:**

- Product Interview Session contract;
- sector-aware Question Registry;
- required/optional/adaptive question rules;
- click-first Arabic RTL interview UX;
- location-first gating;
- capital, geographic scope, data method, project type, operating model, capacity, products/services, staffing, equipment, licensing, and funding questions;
- Needs and Items candidate generation;
- user accept/edit/reject loop;
- deterministic validation of numeric fields;
- AI narrative assistance without AI-owned controlled numbers;
- conversion of approved interview outputs into DIB candidates.

**Exit gate:** an idea-only user can create reviewed DIB candidates and reach manifest readiness without entering the legacy scalar form.

### BETA-PKG-03 — Live Intelligence Product Wiring

**Objective:** connect the existing governed provider foundation to product-facing services without bypassing evidence governance.

**Scope:**

- provider status and preflight endpoints;
- Tavily source discovery/extraction admission;
- Google geocoding and Places product services;
- Pinecone Vision 2030 retrieval service;
- DeepSeek narrative advisory service;
- Source Review and Evidence Candidate persistence;
- approved-context admission into intelligence modules;
- capability-status UI and explicit simulated/live labels;
- timeout, quota, failure, and fallback UX;
- prohibition on provider-owned Finance numbers or sovereign verdicts.

**Exit gate:** a beta user receives at least one live, cited market/location/national-intelligence result with review state and source provenance visible.

### BETA-PKG-04 — Production Secrets and Provider Readiness

**Objective:** make production activation verifiable without exposing secret values.

**Scope:**

- required-secret registry for `DEEPSEEK_API_KEY`, `TAVILY_API_KEY`, `GOOGLE_MAPS_API_KEY`, and `PINECONE_API_KEY`;
- optional-secret registry for `TAVILY_PROJECT` and `GOOGLE_MAP_ID`;
- presence-only readiness checks;
- provider-by-provider preflight;
- GitHub Environment `production` deployment guard;
- redacted readiness report;
- fail-closed deployment when required secrets are missing;
- no secret values in logs, artifacts, responses, or committed files.

**Exit gate:** deployment reports provider readiness as ready/not-ready with reasons, while secret material remains inaccessible.

### BETA-PKG-05 — Beta Release Gate

**Objective:** produce one enforceable go/no-go gate for the controlled beta.

**Scope:**

- end-to-end smoke scenario covering auth, tenant isolation, DIB, mapping/interview, manifest, Finance, Snapshot, reports, and provider status;
- explicit live-versus-simulated capability matrix;
- backup and restore drill;
- HTTPS and health verification;
- production configuration validation;
- beta limitations and operator runbook;
- release evidence artifact and signed gate result.

**Exit gate:** no critical failure, no raw-input Finance bypass, no cross-tenant access, no secret exposure, and all advertised live capabilities verified.

## 3. Package rules

Each package SHALL:

1. use a separate branch and pull request;
2. include implementation, tests, execution record, and rollback notes;
3. pass ASIE CI before merge;
4. preserve canonical terminology;
5. avoid changes to AAS frozen runtime files unless an approved ACR exists;
6. avoid mixing frontend decomposition with behavior changes unless required by that package;
7. expose unfinished capability honestly in the UI;
8. leave external providers disabled by default until production readiness is verified.

## 4. Dependency graph

```text
BETA-PKG-01 Dataset-to-DIB Mapping
        ├──────────────┐
        ▼              ▼
BETA-PKG-02       BETA-PKG-03
Product Interview Live Intelligence Wiring
        └──────┬───────┘
               ▼
BETA-PKG-04 Production Secrets & Readiness
               ▼
BETA-PKG-05 Beta Release Gate
```

BETA-PKG-01 is first because both imported-data users and idea-only users must converge on the same governed DIB and Approved Input Manifest path.

## 5. Deferred but tracked work

The following work is valuable but is not a substitute for the five launch packages:

- PDF intake and supplier quote extraction;
- full template registry and template matching;
- progressive decomposition of the large `App.tsx` file;
- additional repository compaction guardrails;
- broader GCC data-source expansion.

`App.tsx` decomposition should run as behavior-preserving subpackages after the first product-critical path is stable, or alongside packages only when required to isolate a new surface.

## 6. Definition of beta-ready

ASIE is beta-ready only when:

- imported and idea-only paths converge on reviewed DIB candidates;
- Approved Input Manifest is the enforced Finance boundary;
- live intelligence is visibly sourced and governed;
- production providers are verifiably configured;
- deployment, backups, security checks, and end-to-end scenarios pass;
- simulated capabilities are not presented as live.
