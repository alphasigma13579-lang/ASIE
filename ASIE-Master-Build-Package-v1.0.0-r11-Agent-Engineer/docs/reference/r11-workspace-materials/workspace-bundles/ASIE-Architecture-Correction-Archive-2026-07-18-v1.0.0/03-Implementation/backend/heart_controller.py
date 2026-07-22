from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from backend.aas_kernel import AASKernel
from backend.contracts import now_iso
from backend.hearts import AASHeart, HeartError, default_hearts


AssignmentMode = Literal["primary_only", "primary_with_assist"]


class HeartControllerError(ValueError):
    pass


@dataclass(frozen=True)
class HeartTask:
    task_id: str
    purpose: str
    requires_assist: bool = False
    reason: str = "controller_assignment"

    def to_payload(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "purpose": self.purpose,
            "requires_assist": self.requires_assist,
            "reason": self.reason,
        }


class HeartController:
    controller_id = "heart_controller"

    def __init__(self, kernel: AASKernel, hearts: dict[str, AASHeart] | None = None) -> None:
        self.kernel = kernel
        self.hearts = hearts or default_hearts()
        self.state = "created"
        self.created_at = now_iso()
        self.bootstrapped_at: str | None = None
        self.assignment_log: list[dict[str, Any]] = []

    def bootstrap(self) -> dict[str, Any]:
        if self.kernel.state != "booted":
            raise HeartControllerError("kernel must be booted before Heart Controller bootstrap")
        self.kernel.registry.validate_contract_payload(
            "aas.heart.status.v1",
            {
                "controller_id": self.controller_id,
                "hearts": [heart.to_public() for heart in self.hearts.values()],
            },
        )
        self.kernel.registry.assert_socket_contract("socket.heart.status", "aas.heart.status.v1")
        self.hearts["primary"].bootstrap(state="active", activation_reason="runtime_bootstrap")
        self.hearts["assist"].bootstrap(state="assist_ready", activation_reason="available_when_requested")
        self.hearts["reserve"].bootstrap(state="reserved", activation_reason="failover_only")
        self.state = "ready"
        self.bootstrapped_at = now_iso()
        return self.status()

    def assign_task(self, task: HeartTask) -> dict[str, Any]:
        if self.state != "ready":
            raise HeartControllerError("Heart Controller must be ready before task assignment")
        payload = task.to_payload() | {"controller_id": self.controller_id}
        self.kernel.registry.validate_contract_payload("aas.heart.assignment.v1", payload)
        self.kernel.registry.assert_socket_contract("socket.heart.assignment", "aas.heart.assignment.v1")

        assignments = [
            self.hearts["primary"].assign(
                task_id=task.task_id,
                assigned_by=self.controller_id,
                reason=task.reason,
            )
        ]
        mode: AssignmentMode = "primary_only"
        if task.requires_assist:
            assignments.append(
                self.hearts["assist"].assign(
                    task_id=task.task_id,
                    assigned_by=self.controller_id,
                    reason="assist_requested_by_controller",
                )
            )
            mode = "primary_with_assist"

        record = {
            "task": task.to_payload(),
            "mode": mode,
            "assignments": assignments,
            "reserve_used": False,
            "controlled_by": self.controller_id,
            "created_at": now_iso(),
            "business_logic_executed": False,
            "sovereign_verdict_issued": False,
        }
        self.assignment_log.append(record)
        return record

    def failover_to_reserve(self, *, reason: str) -> dict[str, Any]:
        if self.state != "ready":
            raise HeartControllerError("Heart Controller must be ready before failover")
        primary = self.hearts["primary"]
        reserve = self.hearts["reserve"]
        primary.state = "degraded"
        primary.health = "degraded"
        primary.activation_reason = reason
        reserve.bootstrap(state="active", activation_reason=f"reserve_failover:{reason}")
        record = {
            "event": "reserve_failover",
            "controlled_by": self.controller_id,
            "reason": reason,
            "primary": primary.to_public(),
            "reserve": reserve.to_public(),
            "created_at": now_iso(),
            "business_logic_executed": False,
            "sovereign_verdict_issued": False,
        }
        self.assignment_log.append(record)
        return record

    def heartbeat(self) -> dict[str, Any]:
        return {
            "controller_id": self.controller_id,
            "state": self.state,
            "hearts": [heart.heartbeat() for heart in self.hearts.values()],
            "created_at": now_iso(),
        }

    def status(self) -> dict[str, Any]:
        return {
            "controller_id": self.controller_id,
            "state": self.state,
            "created_at": self.created_at,
            "bootstrapped_at": self.bootstrapped_at,
            "hearts": [heart.to_public() for heart in self.hearts.values()],
            "assignment_count": len(self.assignment_log),
            "last_assignment": self.assignment_log[-1] if self.assignment_log else None,
            "guards": {
                "no_heart_acts_without_controller": True,
                "no_heart_executes_business_logic": True,
                "no_heart_issues_sovereign_verdict": True,
                "reserve_is_failover_only": self.hearts["reserve"].state in {"reserved", "active"},
            },
        }


def bootstrap_heart_controller(kernel: AASKernel) -> HeartController:
    controller = HeartController(kernel)
    controller.bootstrap()
    return controller
