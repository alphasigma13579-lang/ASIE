# الرفض والفشل والاسترداد

## رفض API

- unauthorized user
- project not found
- ownership mismatch
- invalid schema
- conflicting idempotency key
- forbidden/unknown fields

المخرج: `request_rejected`

## رفض Kernel

- runtime unavailable
- maintenance mode
- unknown contract
- operation not permitted

المخرج: `kernel_admission_rejected`

## فشل Heart Assignment

- لا قلب سليم
- M1 غير متاح وM3 غير جاهز
- execution policy رفضت المهمة

المخرج: `heart_assignment_failed`

## رفض Bus/Socket

- unauthorized sender
- unregistered target
- missing socket
- incompatible contract version
- open broadcast
- incomplete envelope

المخرج: `message_rejected`

## رفض Module Runtime

- module unregistered
- unhealthy module
- payload mismatch
- direct call attempt
- module حاول امتلاك حقيقة خارج نطاقه

المخرج: `module_execution_rejected`

## رفض Snapshot

- missing output
- hash mismatch
- run_id mismatch
- broken correlation lineage
- unsupported contract version
- unsealed result

المخرج: `snapshot_rejected`

ولا ينشأ Snapshot جزئي.

## Failover

عند فشل M1 قبل Commit:

```text
M1 failure
→ Heart Controller
→ M3 Reserve
```

مع الحفاظ على:

- نفس `run_id`
- نفس `correlation_id`
- نفس `idempotency_key`
- عدم تكرار commit
- عدم إنشاء Snapshotين

## فشل Module

إذا فشل Finance مثلًا:

```text
Finance failed
→ Decision لا يبدأ
→ Snapshot لا ينشأ
```

## فشل Commit

```text
No Snapshot
No Report
No Decision Pack
```

## فشل Projection

- Snapshot يبقى محفوظًا.
- Report وDecision Pack حالتان مستقلتان.
- يجوز إعادة محاولة Projection دون إعادة الحساب.
