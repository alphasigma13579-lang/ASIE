from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from backend.contracts import now_iso


HeartRole = Literal["primary", "assist", "reserve"]
HeartState = Literal["created", "standby", "active", "assist_ready", "reserved", "degraded", "offline"]


class HeartError(ValueError):
    pass


@dataclass(frozen=True)
class HeartPolicy:
    controlled_by: str = "heart_controller"
    can_execute_business_logic: bool = False
    can_issue_sovereign_verdict: bool = False
    can_act_without_controller: bool = False

    def to_public(self) -> dict[str, Any]:
        return {
            "controlled_by": self.controlled_by,
            "can_execute_business_logic": self.can_execute_business_logic,
            "can_issue_sovereign_verdict": self.can_issue_sovereign_verdict,
            "can_act_without_controller": self.can_act_without_controller,
        }


class AASHeart:
    def __init__(
        self,
        *,
        heart_id: str,
        role: HeartRole,
        state: HeartState = "created",
        activation_reason: str = "not_bootstrapped",
    ) -> None:
        self.heart_id = heart_id
        self.role = role
        self.state = state
        self.health = "unknown"
        self.load = 0.0
        self.activation_reason = activation_reason
        self.policy = HeartPolicy()
        self.created_at = now_iso()
        self.last_heartbeat_at: str | None = None
        self.assignment_count = 0

    def bootstrap(self, *, state: HeartState, activation_reason: str) -> None:
        self.state = state
        self.activation_reason = activation_reason
        self.health = "healthy"
        self.load = 0.0
        self.last_heartbeat_at = now_iso()

    def heartbeat(self) -> dict[str, Any]:
        if self.state == "offline":
            self.health = "offline"
        elif self.state == "degraded":
            self.health = "degraded"
        else:
            self.health = "healthy"
        self.last_heartbeat_at = now_iso()
        return self.to_public()

    def assign(self, *, task_id: str, assigned_by: str, reason: str) -> dict[str, Any]:
        if assigned_by != self.policy.controlled_by:
            raise HeartError("heart assignment must come from Heart Controller")
        if self.state not in {"active", "assist_ready"}:
            raise HeartError(f"heart {self.heart_id} cannot accept assignments while {self.state}")
        self.assignment_count += 1
        self.load = min(1.0, self.load + 0.15)
        self.activation_reason = reason
        self.last_heartbeat_at = now_iso()
        return {
            "task_id": task_id,
            "heart_id": self.heart_id,
            "role": self.role,
            "assigned_by": assigned_by,
            "reason": reason,
            "status": "assigned",
            "created_at": self.last_heartbeat_at,
            "business_logic_executed": False,
            "sovereign_verdict_issued": False,
        }

    def release_load(self, amount: float = 0.15) -> None:
        self.load = max(0.0, self.load - amount)

    def to_public(self) -> dict[str, Any]:
        return {
            "heart_id": self.heart_id,
            "role": self.role,
            "state": self.state,
            "health": self.health,
            "load": round(self.load, 2),
            "activation_reason": self.activation_reason,
            "last_heartbeat_at": self.last_heartbeat_at,
            "controlled_by": self.policy.controlled_by,
            "assignment_count": self.assignment_count,
            "policy": self.policy.to_public(),
        }


def default_hearts() -> dict[str, AASHeart]:
    return {
        "primary": AASHeart(heart_id="M1", role="primary"),
        "assist": AASHeart(heart_id="M2", role="assist"),
        "reserve": AASHeart(heart_id="M3", role="reserve"),
    }
