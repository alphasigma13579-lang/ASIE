from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

from backend.bus_controller import BusController, BusControllerError
from backend.contracts import new_id, now_iso


class SystemBusError(ValueError):
    pass


def _payload_input_hash(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class BusMessage:
    source_module_id: str
    target_module_id: str
    contract_id: str
    socket_id: str
    payload: dict[str, Any]
    correlation_id: str
    audit_ref: str
    operation_id: str = field(default_factory=lambda: new_id("op"))
    idempotency_key: str = field(default_factory=lambda: new_id("idem"))
    input_hash: str = ""
    message_id: str = field(default_factory=lambda: new_id("msg"))
    created_at: str = field(default_factory=now_iso)

    def __post_init__(self) -> None:
        if not self.input_hash:
            object.__setattr__(self, "input_hash", _payload_input_hash(self.payload))

    def to_public(self) -> dict[str, Any]:
        return {
            "message_id": self.message_id,
            "operation_id": self.operation_id,
            "idempotency_key": self.idempotency_key,
            "input_hash": self.input_hash,
            "source_module_id": self.source_module_id,
            "target_module_id": self.target_module_id,
            "contract_id": self.contract_id,
            "socket_id": self.socket_id,
            "correlation_id": self.correlation_id,
            "audit_ref": self.audit_ref,
            "payload": self.payload,
            "created_at": self.created_at,
        }


class SystemBus:
    bus_id = "asie_system_bus"

    def __init__(self, controller: BusController) -> None:
        self.controller = controller
        self.state = "created"
        self.created_at = now_iso()
        self.bootstrapped_at: str | None = None
        self.messages: list[dict[str, Any]] = []

    def bootstrap(self) -> dict[str, Any]:
        if self.controller.state != "ready":
            raise SystemBusError("Bus Controller must be ready before System Bus bootstrap")
        self.state = "ready"
        self.bootstrapped_at = now_iso()
        return self.status()

    def publish(self, message: BusMessage) -> dict[str, Any]:
        if self.state != "ready":
            raise SystemBusError("System Bus must be ready before publishing messages")
        decision = self.controller.admit(message)
        record = {
            "bus_id": self.bus_id,
            "message": message.to_public(),
            "admission": decision.to_public(),
            "delivered": decision.accepted,
            "business_logic_executed": False,
            "created_at": now_iso(),
        }
        self.messages.append(record)
        if not decision.accepted:
            raise BusControllerError(decision.reason)
        return record

    def try_publish(self, message: Any) -> dict[str, Any]:
        if self.state != "ready":
            raise SystemBusError("System Bus must be ready before publishing messages")
        decision = self.controller.admit(message)
        message_public = message.to_public() if hasattr(message, "to_public") else {"raw_message_type": type(message).__name__}
        record = {
            "bus_id": self.bus_id,
            "message": message_public,
            "admission": decision.to_public(),
            "delivered": decision.accepted,
            "business_logic_executed": False,
            "created_at": now_iso(),
        }
        self.messages.append(record)
        return record

    def status(self) -> dict[str, Any]:
        delivered = [message for message in self.messages if message["delivered"]]
        rejected = [message for message in self.messages if not message["delivered"]]
        return {
            "bus_id": self.bus_id,
            "state": self.state,
            "created_at": self.created_at,
            "bootstrapped_at": self.bootstrapped_at,
            "message_count": len(self.messages),
            "delivered_count": len(delivered),
            "rejected_count": len(rejected),
            "last_message": self.messages[-1] if self.messages else None,
            "guards": {
                "only_path_between_modules": True,
                "executes_business_logic": False,
                "external_fetch_enabled": False,
            },
        }


def bootstrap_system_bus(controller: BusController) -> SystemBus:
    bus = SystemBus(controller)
    bus.bootstrap()
    return bus
