# Audit وMessage Envelope

## Message Envelope إلزامي

كل رسالة تحمل:

```json
{
  "message_id": "...",
  "correlation_id": "...",
  "audit_ref": "...",
  "contract_id": "...",
  "contract_version": "...",
  "socket_id": "...",
  "sender": "...",
  "target": "...",
  "run_id": "...",
  "operation_id": "...",
  "idempotency_key": "...",
  "input_hash": "...",
  "payload": {}
}
```

## Audit مسار جانبي

```text
Runtime Event
├── Result → Operational Path
└── Metadata → SecurityAuditSink
```

## أحداث مقبولة

- run accepted
- heart assigned
- message routed
- module executed
- snapshot committed
- report projected
- decision pack projected

## أحداث مرفوضة

- invalid contract
- invalid socket
- direct module call
- unauthorized sender
- hash mismatch
- partial snapshot attempt
- duplicate commit
- projection attempted recalculation

## Metadata فقط

```text
event_type
reason_code
run_id
message_id
correlation_id
contract_id
socket_id
module_id
status
timestamp
```

## ممنوع تسجيله

- API keys
- secrets
- raw prompts
- complete user files
- unnecessary sensitive financial content
