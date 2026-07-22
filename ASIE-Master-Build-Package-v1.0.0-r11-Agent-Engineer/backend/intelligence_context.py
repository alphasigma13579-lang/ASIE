"""Offline-safe AIA context foundation.

This module deliberately does not register a socket, touch Snapshot Assembly,
or fetch external sources. It models the pre-run lifecycle that an approved
ACR can later place behind the existing AAS transport.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from backend.snapshot_assembly import canonical_hash

CONTEXT_STATES = {
    "DRAFT", "VALIDATING", "INTEGRITY_LOCKED", "REVIEW_PENDING",
    "APPROVED_FOR_RUN", "APPROVED_WITH_CONDITIONS", "REJECTED", "STALE",
}
REQUIRED_SCOPE = ("organization_id", "project_id", "geography", "sector")
REQUIRED_EVIDENCE = ("source", "freshness", "confidence", "lineage", "review")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class ContextComponent:
    component_id: str
    kind: str
    value: Any
    source: str
    freshness: str
    geography: str
    sector: str
    confidence: str
    lineage: list[str]
    review: str = "PENDING"

    def as_dict(self) -> dict[str, Any]:
        return {
            "component_id": self.component_id, "kind": self.kind,
            "value": self.value, "source": self.source,
            "freshness": self.freshness, "geography": self.geography,
            "sector": self.sector, "confidence": self.confidence,
            "lineage": list(self.lineage), "review": self.review,
        }


@dataclass
class IntelligenceContext:
    context_build_id: str
    organization_id: str
    project_id: str
    geography: str
    sector: str
    idempotency_key: str
    state: str = "DRAFT"
    version: int = 1
    components: list[ContextComponent] = field(default_factory=list)
    context_hash: str = ""
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    stale_reason: str = ""

    def _material(self) -> dict[str, Any]:
        return {
            "context_build_id": self.context_build_id,
            "organization_id": self.organization_id, "project_id": self.project_id,
            "geography": self.geography, "sector": self.sector,
            "version": self.version,
            "components": [c.as_dict() for c in self.components],
        }

    def validate(self) -> None:
        if any(not getattr(self, key) for key in REQUIRED_SCOPE):
            raise ValueError("context_scope_incomplete")
        if not self.idempotency_key:
            raise ValueError("idempotency_key_required")
        if not self.components:
            raise ValueError("context_requires_component")
        for component in self.components:
            missing = [key for key in REQUIRED_EVIDENCE if not getattr(component, key)]
            if missing:
                raise ValueError("component_evidence_incomplete:" + ",".join(missing))

    def transition(self, target: str) -> "IntelligenceContext":
        if target not in CONTEXT_STATES:
            raise ValueError("unknown_context_state")
        allowed = {
            "DRAFT": {"VALIDATING"}, "VALIDATING": {"INTEGRITY_LOCKED", "REJECTED"},
            "INTEGRITY_LOCKED": {"REVIEW_PENDING", "STALE"},
            "REVIEW_PENDING": {"APPROVED_FOR_RUN", "APPROVED_WITH_CONDITIONS", "REJECTED", "STALE"},
            "APPROVED_FOR_RUN": {"STALE"}, "APPROVED_WITH_CONDITIONS": {"STALE"},
            "REJECTED": set(), "STALE": set(),
        }
        if target not in allowed[self.state]:
            raise ValueError(f"invalid_context_transition:{self.state}->{target}")
        if target == "VALIDATING":
            self.validate()
        if target == "INTEGRITY_LOCKED":
            self.context_hash = canonical_hash(self._material())
        self.state, self.version, self.updated_at = target, self.version + 1, _now()
        return self

    def mark_stale(self, reason: str) -> "IntelligenceContext":
        if self.state not in {"INTEGRITY_LOCKED", "REVIEW_PENDING", "APPROVED_FOR_RUN", "APPROVED_WITH_CONDITIONS"}:
            raise ValueError("context_not_staleable")
        self.stale_reason = reason
        return self.transition("STALE")


def idempotency_fingerprint(organization_id: str, project_id: str, key: str) -> str:
    """Stable lookup key; tenant is part of the key to prevent cross-tenant replay."""
    return canonical_hash({"organization_id": organization_id, "project_id": project_id, "idempotency_key": key})
