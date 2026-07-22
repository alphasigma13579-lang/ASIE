"""ACR-AIA-02 review and approval model; persistence/transport intentionally absent."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.intelligence_context import IntelligenceContext
from backend.snapshot_assembly import canonical_hash


@dataclass(frozen=True)
class ReviewOverlay:
    review_overlay_id: str
    intelligence_context_id: str
    intelligence_context_hash: str
    reviewer_id: str
    reviewer_role: str
    review_scope: str
    reviewed_output_hash: str
    decision: str
    conditions: list[str] = field(default_factory=list)
    reason: str = ""
    override_status: str = "NOT_REQUESTED"
    affected_contract: str = ""
    affected_snapshot_ref: str = ""
    supersedes_overlay_id: str = ""

    def material(self) -> dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if k != "review_overlay_hash"}

    @property
    def review_overlay_hash(self) -> str:
        return canonical_hash(self.material())

    def validate_for(self, context: IntelligenceContext) -> None:
        if self.intelligence_context_id != context.context_build_id or self.intelligence_context_hash != context.context_hash:
            raise ValueError("review_context_hash_mismatch")
        if not self.reviewer_id or not self.reviewer_role or not self.review_scope:
            raise ValueError("review_identity_incomplete")
        if self.decision not in {"APPROVE", "APPROVE_WITH_CONDITIONS", "REJECT", "REQUEST_CHANGES"}:
            raise ValueError("invalid_review_decision")
        if self.decision == "APPROVE_WITH_CONDITIONS" and not self.conditions:
            raise ValueError("approval_conditions_required")


@dataclass(frozen=True)
class ApprovalReceipt:
    approval_receipt_id: str
    organization_id: str
    project_id: str
    intelligence_context_id: str
    intelligence_context_hash: str
    review_overlay_id: str
    review_overlay_hash: str
    approval_scope: str
    approved_for_contract_version: str
    valid_until: str
    conditions: list[str] = field(default_factory=list)

    def material(self) -> dict[str, Any]:
        return dict(self.__dict__)

    @property
    def approval_receipt_hash(self) -> str:
        return canonical_hash(self.material())

    def validate_for(self, context: IntelligenceContext, overlay: ReviewOverlay) -> None:
        if context.state not in {"REVIEW_PENDING", "APPROVED_FOR_RUN", "APPROVED_WITH_CONDITIONS"}:
            raise ValueError("context_not_approval_eligible")
        if self.organization_id != context.organization_id or self.project_id != context.project_id:
            raise PermissionError("approval_tenant_or_project_mismatch")
        if self.intelligence_context_id != context.context_build_id or self.intelligence_context_hash != context.context_hash:
            raise ValueError("approval_context_hash_mismatch")
        if self.review_overlay_id != overlay.review_overlay_id or self.review_overlay_hash != overlay.review_overlay_hash:
            raise ValueError("approval_overlay_mismatch")
        if overlay.decision not in {"APPROVE", "APPROVE_WITH_CONDITIONS"}:
            raise ValueError("review_does_not_approve")
        if not self.approved_for_contract_version or not self.approval_scope or not self.valid_until:
            raise ValueError("approval_receipt_incomplete")


def approval_status(context: IntelligenceContext, receipt: ApprovalReceipt | None) -> str:
    """Derived consumption status; never mutates Context and never creates a Snapshot."""
    if receipt is None:
        return "REVIEW_PENDING"
    if context.context_hash != receipt.intelligence_context_hash:
        return "STALE"
    return "APPROVED_WITH_CONDITIONS" if receipt.conditions else "APPROVED_FOR_RUN"
