import unittest

from backend.intelligence_approval import ApprovalReceipt, ReviewOverlay, approval_status
from backend.intelligence_context import ContextComponent, IntelligenceContext


class IntelligenceApprovalTests(unittest.TestCase):
    def setUp(self):
        self.context = IntelligenceContext("ctx-1", "org-a", "project-a", "SA", "retail", "idem-1", components=[
            ContextComponent("c-1", "reference", {"x": 1}, "VISION_2030_REFERENCE", "2026-07-21", "SA", "retail", "medium", ["manual:brief"])
        ])
        self.context.transition("VALIDATING").transition("INTEGRITY_LOCKED").transition("REVIEW_PENDING")
        self.overlay = ReviewOverlay("review-1", "ctx-1", self.context.context_hash, "user-1", "reviewer", "context", "out-1", "APPROVE")
        self.receipt = ApprovalReceipt("receipt-1", "org-a", "project-a", "ctx-1", self.context.context_hash, "review-1", self.overlay.review_overlay_hash, "run", "decision.council.v2", "2026-12-31")

    def test_matching_receipt_is_consumable_only_as_derived_status(self):
        self.overlay.validate_for(self.context)
        self.receipt.validate_for(self.context, self.overlay)
        self.assertEqual("APPROVED_FOR_RUN", approval_status(self.context, self.receipt))
        self.assertEqual("REVIEW_PENDING", self.context.state)

    def test_cross_tenant_receipt_is_denied(self):
        bad = ApprovalReceipt("r", "org-b", "project-a", "ctx-1", self.context.context_hash, "review-1", self.overlay.review_overlay_hash, "run", "decision.council.v2", "2026-12-31")
        with self.assertRaises(PermissionError):
            bad.validate_for(self.context, self.overlay)

    def test_hash_mismatch_is_stale(self):
        bad = ApprovalReceipt("r", "org-a", "project-a", "ctx-1", "wrong", "review-1", self.overlay.review_overlay_hash, "run", "decision.council.v2", "2026-12-31")
        self.assertEqual("STALE", approval_status(self.context, bad))


if __name__ == "__main__":
    unittest.main()
