# Snapshot وProjections

## Snapshot Assembly

يستقبل كل المخرجات المغلقة:

```text
Finance ───────┐
Evidence ──────┤
Sector ────────┤
Decision ──────┤
Risk ──────────┤
Execution ─────┘
        ↓
Snapshot Assembly
```

## شروط القبول

- كل output sealed
- كل output يطابق نفس `run_id`
- hashes صحيحة
- lineage مكتمل
- versions معتمدة
- correlation chain سليمة

## Atomic Commit

```text
Commit كامل
أو
Rollback كامل
```

لا Snapshot جزئي.

## Projections

```text
Immutable Snapshot
├── Report Projection
└── Decision Pack Projection
```

### ممنوع

- Report → Decision Pack
- Decision Pack → Report
- أي Projection يعيد الحساب
- أي Projection يستدعي Finance/Decision/Risk/Execution
- فتح Decision Pack يقرأ Draft الحالي
