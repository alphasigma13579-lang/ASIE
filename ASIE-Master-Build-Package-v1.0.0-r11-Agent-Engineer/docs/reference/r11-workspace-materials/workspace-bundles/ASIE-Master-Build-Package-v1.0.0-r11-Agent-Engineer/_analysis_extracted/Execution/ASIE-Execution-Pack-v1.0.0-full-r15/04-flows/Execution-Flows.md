# Execution Flows

## تدفقات التنفيذ

## Flow 1: Project Analysis

## التدفق 1: تحليل المشروع

```mermaid
sequenceDiagram
    participant U as User / المستخدم
    participant W as Wizard / المعالج
    participant B as System Bus / ناقل النظام
    participant S as SCL / عقود السوكيت
    participant M as Market / ذكاء السوق
    participant F as Finance / التمويل
    participant D as Decision / القرار

    U->>W: Submit guided context
    W->>B: market.query.request.v1
    B->>S: Validate contract
    S->>M: Authorized request
    M->>B: market.evidence.pack.v1
    W->>B: finance.calculate.request.v1
    B->>S: Validate contract
    S->>F: Deterministic calculation
    F->>B: finance.result.v1
    W->>B: decision.evaluate.request.v1
    B->>S: Validate contract
    S->>D: Decision evaluation
    D->>B: decision.result.v1
```

## Flow 2: AI Advisory

## التدفق 2: الاستشارة بالذكاء الاصطناعي

```mermaid
sequenceDiagram
    participant D as Decision / القرار
    participant B as System Bus / ناقل النظام
    participant S as SCL / عقود السوكيت
    participant A as AI Advisory / الاستشارة
    participant G as Guard / الحارس

    D->>B: ai.advisory.request.v1
    B->>S: Validate contract
    S->>A: Evidence-bound prompt
    A->>G: Check output
    G-->>A: Reject unsupported numbers
    A->>B: ai.advisory.output.v1
```

## Flow 3: Negative Direct Module Call

## التدفق 3: رفض الاتصال المباشر

```mermaid
sequenceDiagram
    participant W as Wizard / المعالج
    participant F as Finance / التمويل
    participant A as Audit / التدقيق

    W-xF: Direct call attempt
    F-->>A: audit.quarantine.event.v1
```

## Flow 4: Market Outlier

## التدفق 4: شذوذ السعر

```mermaid
sequenceDiagram
    participant M as Market / ذكاء السوق
    participant B as System Bus / ناقل النظام
    participant F as Finance / التمويل
    participant A as Audit / التدقيق

    M->>M: Filter price samples
    M->>B: market.outlier.report.v1
    B->>F: Block affected input
    B->>A: Audit outlier
```

## Flow 5: Project Dashboard Composition

## التدفق 5: تكوين لوحة المشروع

```mermaid
sequenceDiagram
    participant U as Authorized UI
    participant P as API Boundary
    participant B as APP / SCL / System Bus
    participant R as Reports
    participant A as Audit

    U->>P: dashboard.project.view.requested.v1
    P->>B: Project-scoped authorized message
    B->>R: reports.project.dashboard.view.v1
    R->>B: Resolve approved owner output IDs
    B->>A: dashboard.output.lineage.requested.v1
    A->>B: dashboard.output.lineage.resolved.v1
    R->>B: dashboard.project.view.composed.v1
    B->>P: Contract-bound view model
    P->>U: RTL/LTR dashboard response
```

Rules:

- Reports composes; it does not recalculate.
- Owner outputs remain owned by their existing Modules.
- Any cross-project, missing-contract, stale-disallowed, lineage-invalid, or permission-denied output is blocked and audited.

## Professional Feasibility Flow r15

1. UI submits project purpose/context through `project.feasibility.profile.v1`.
2. Project Wizard applies `FST-ALG-01` and emits the selected minimum profile.
3. Existing owner Modules produce their chapter outputs through approved contracts and message types.
4. Finance Engine executes applicable `FIN-ALG-06` through `FIN-ALG-12` from approved inputs only.
5. Audit / Observability reviews procurement references and methodology cards; blocked commercial content never enters AI/RAG.
6. Decision Council applies `FST-ALG-02`, `FST-ALG-03`, `PROC-ALG-01`, and the existing decision gates.
7. Reports composes dashboard/report output without recalculation and preserves chapter state and lineage.
8. Audit records profile, evidence, assumptions, formulas, official-form decisions, contradictions, decisions, and exports.

Failure branches:

- Missing mandatory chapter -> `feasibility.study.composition.blocked.v1`.
- Cross-study mismatch -> contradiction register and affected outputs blocked.
- Unbalanced statements or mixed financial bases -> `finance.feasibility.advanced.blocked.v1`.
- Missing exact competition package -> `procurement.exact.documents.required.v1`.
- Aljdwa or other commercial page requested for automated access -> `methodology.commercial.access.blocked.v1` and audit event.
