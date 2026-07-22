from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.aas_registry import AASRegistry, ContractValidationError, UnknownRegistrationError
from backend.contracts import now_iso


class SocketContractError(ValueError):
    pass


@dataclass(frozen=True)
class SocketContractCheck:
    passed: bool
    reason: str
    message_id: str
    socket_id: str | None
    contract_id: str | None
    source_module_id: str | None
    target_module_id: str | None
    checked_at: str

    def to_public(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "reason": self.reason,
            "message_id": self.message_id,
            "socket_id": self.socket_id,
            "contract_id": self.contract_id,
            "source_module_id": self.source_module_id,
            "target_module_id": self.target_module_id,
            "checked_at": self.checked_at,
        }


class SocketContractLayer:
    layer_id = "socket_contract_layer"

    def __init__(self, registry: AASRegistry) -> None:
        self.registry = registry
        self.state = "created"
        self.created_at = now_iso()
        self.bootstrapped_at: str | None = None
        self.checks: list[SocketContractCheck] = []

    def bootstrap(self) -> dict[str, Any]:
        self.registry.validate_contract_payload(
            "aas.socket.enforcement.v1",
            {
                "layer_id": self.layer_id,
                "state": "enforcing",
                "checked_count": 0,
            },
        )
        self.registry.assert_socket_contract("socket.contract.enforcement", "aas.socket.enforcement.v1")
        self.state = "enforcing"
        self.bootstrapped_at = now_iso()
        return self.status()

    def verify_message(self, message: Any) -> SocketContractCheck:
        if self.state != "enforcing":
            raise SocketContractError("Socket Contract Layer must be enforcing before verification")

        fields = self._message_fields(message)
        reason = self._verification_reason(fields)
        check = SocketContractCheck(
            passed=reason == "accepted",
            reason=reason,
            message_id=fields["message_id"] or "missing_message_id",
            socket_id=fields["socket_id"],
            contract_id=fields["contract_id"],
            source_module_id=fields["source_module_id"],
            target_module_id=fields["target_module_id"],
            checked_at=now_iso(),
        )
        self.checks.append(check)
        return check

    def status(self) -> dict[str, Any]:
        passed = [check for check in self.checks if check.passed]
        failed = [check for check in self.checks if not check.passed]
        return {
            "layer_id": self.layer_id,
            "state": self.state,
            "created_at": self.created_at,
            "bootstrapped_at": self.bootstrapped_at,
            "checked_count": len(self.checks),
            "passed_count": len(passed),
            "failed_count": len(failed),
            "last_check": self.checks[-1].to_public() if self.checks else None,
            "guards": {
                "socket_first_module_second": True,
                "requires_registered_socket": True,
                "requires_socket_contract_match": True,
                "requires_target_provider_match": True,
                "requires_payload_contract": True,
                "executes_business_logic": False,
            },
        }

    def _message_fields(self, message: Any) -> dict[str, Any]:
        return {
            "message_id": getattr(message, "message_id", None),
            "operation_id": getattr(message, "operation_id", None),
            "idempotency_key": getattr(message, "idempotency_key", None),
            "input_hash": getattr(message, "input_hash", None),
            "socket_id": getattr(message, "socket_id", None),
            "contract_id": getattr(message, "contract_id", None),
            "correlation_id": getattr(message, "correlation_id", None),
            "audit_ref": getattr(message, "audit_ref", None),
            "payload": getattr(message, "payload", None),
            "source_module_id": getattr(message, "source_module_id", None),
            "target_module_id": getattr(message, "target_module_id", None),
        }

    def _verification_reason(self, fields: dict[str, Any]) -> str:
        required = {
            "message_id": fields["message_id"],
            "operation_id": fields["operation_id"],
            "idempotency_key": fields["idempotency_key"],
            "input_hash": fields["input_hash"],
            "socket_id": fields["socket_id"],
            "contract_id": fields["contract_id"],
            "correlation_id": fields["correlation_id"],
            "audit_ref": fields["audit_ref"],
            "source_module_id": fields["source_module_id"],
            "target_module_id": fields["target_module_id"],
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            return f"missing_required_message_fields:{','.join(missing)}"
        if not isinstance(fields["payload"], dict):
            return "payload_must_be_object"

        try:
            socket = self.registry.socket(str(fields["socket_id"]))
        except UnknownRegistrationError as exc:
            return f"unknown_registry_reference:{exc}"

        try:
            self.registry.assert_socket_contract(str(fields["socket_id"]), str(fields["contract_id"]))
        except ContractValidationError as exc:
            return f"socket_contract_mismatch:{exc}"

        try:
            self.registry.module(str(fields["source_module_id"]))
            target_module = self.registry.module(str(fields["target_module_id"]))
        except UnknownRegistrationError as exc:
            return f"unknown_registry_reference:{exc}"

        if socket.provider_module_id != target_module.module_id:
            return "target_module_does_not_provide_socket"
        if target_module.external_fetch_enabled:
            return "target_module_external_fetch_forbidden"

        try:
            self.registry.validate_contract_payload(str(fields["contract_id"]), fields["payload"])
        except ContractValidationError as exc:
            return f"contract_validation_failed:{exc}"
        return "accepted"


def bootstrap_socket_contract_layer(registry: AASRegistry) -> SocketContractLayer:
    layer = SocketContractLayer(registry)
    layer.bootstrap()
    return layer
