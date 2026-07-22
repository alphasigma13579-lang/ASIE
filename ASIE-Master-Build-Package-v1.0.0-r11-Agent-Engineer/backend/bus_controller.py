from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.aas_kernel import AASKernel
from backend.contracts import now_iso
from backend.heart_controller import HeartController
from backend.socket_contracts import SocketContractLayer, bootstrap_socket_contract_layer


class BusControllerError(ValueError):
    pass


@dataclass(frozen=True)
class BusAdmissionDecision:
    accepted: bool
    reason: str
    message_id: str
    socket_id: str | None
    contract_id: str | None
    correlation_id: str | None
    audit_ref: str | None
    decided_at: str

    def to_public(self) -> dict[str, Any]:
        return {
            "accepted": self.accepted,
            "reason": self.reason,
            "message_id": self.message_id,
            "socket_id": self.socket_id,
            "contract_id": self.contract_id,
            "correlation_id": self.correlation_id,
            "audit_ref": self.audit_ref,
            "decided_at": self.decided_at,
        }


class BusController:
    controller_id = "bus_controller"

    def __init__(
        self,
        kernel: AASKernel,
        heart_controller: HeartController,
        socket_layer: SocketContractLayer | None = None,
    ) -> None:
        self.kernel = kernel
        self.heart_controller = heart_controller
        self.socket_layer = socket_layer
        self.state = "created"
        self.created_at = now_iso()
        self.bootstrapped_at: str | None = None
        self.decisions: list[BusAdmissionDecision] = []

    def bootstrap(self) -> dict[str, Any]:
        if self.kernel.state != "booted":
            raise BusControllerError("kernel must be booted before Bus Controller bootstrap")
        if self.heart_controller.state != "ready":
            raise BusControllerError("Heart Controller must be ready before Bus Controller bootstrap")
        self.kernel.registry.validate_contract_payload(
            "aas.bus.status.v1",
            {
                "controller_id": self.controller_id,
                "state": "ready",
                "message_count": 0,
            },
        )
        self.kernel.registry.assert_socket_contract("socket.bus.status", "aas.bus.status.v1")
        if self.socket_layer is None:
            self.socket_layer = bootstrap_socket_contract_layer(self.kernel.registry)
        elif self.socket_layer.state != "enforcing":
            self.socket_layer.bootstrap()
        self.state = "ready"
        self.bootstrapped_at = now_iso()
        return self.status()

    def admit(self, message: Any) -> BusAdmissionDecision:
        if self.state != "ready":
            raise BusControllerError("Bus Controller must be ready before message admission")

        message_id = getattr(message, "message_id", "")
        socket_id = getattr(message, "socket_id", None)
        contract_id = getattr(message, "contract_id", None)
        correlation_id = getattr(message, "correlation_id", None)
        audit_ref = getattr(message, "audit_ref", None)
        if self.socket_layer is None:
            raise BusControllerError("Socket Contract Layer must be bootstrapped before message admission")
        socket_check = self.socket_layer.verify_message(message)
        reason = socket_check.reason
        decision = BusAdmissionDecision(
            accepted=reason == "accepted",
            reason=reason,
            message_id=message_id or "missing_message_id",
            socket_id=socket_id,
            contract_id=contract_id,
            correlation_id=correlation_id,
            audit_ref=audit_ref,
            decided_at=now_iso(),
        )
        self.decisions.append(decision)
        return decision

    def status(self) -> dict[str, Any]:
        accepted = [decision for decision in self.decisions if decision.accepted]
        rejected = [decision for decision in self.decisions if not decision.accepted]
        return {
            "controller_id": self.controller_id,
            "state": self.state,
            "created_at": self.created_at,
            "bootstrapped_at": self.bootstrapped_at,
            "message_count": len(self.decisions),
            "accepted_count": len(accepted),
            "rejected_count": len(rejected),
            "last_decision": self.decisions[-1].to_public() if self.decisions else None,
            "guards": {
                "requires_contract_id": True,
                "requires_socket_id": True,
                "requires_operation_id": True,
                "requires_idempotency_key": True,
                "requires_input_hash": True,
                "requires_correlation_id": True,
                "requires_audit_ref": True,
                "executes_business_logic": False,
                "external_fetch_enabled": False,
                "socket_contract_layer": self.socket_layer.status() if self.socket_layer else None,
            },
        }


def bootstrap_bus_controller(kernel: AASKernel, heart_controller: HeartController) -> BusController:
    controller = BusController(kernel, heart_controller)
    controller.bootstrap()
    return controller
