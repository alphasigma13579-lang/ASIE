import unittest

from backend.intelligence_context import ContextComponent, IntelligenceContext, idempotency_fingerprint


class IntelligenceContextTests(unittest.TestCase):
    def context(self):
        return IntelligenceContext(
            "ctx-1", "org-a", "project-a", "SA", "retail", "idem-1",
            components=[ContextComponent("c-1", "vision_reference", {"goal": "alignment"},
                "VISION_2030_REFERENCE", "2026-07-21", "SA", "retail", "medium", ["manual:brief"])]
        )

    def test_lifecycle_hash_and_approval(self):
        ctx = self.context().transition("VALIDATING").transition("INTEGRITY_LOCKED").transition("REVIEW_PENDING")
        self.assertTrue(ctx.context_hash)
        self.assertEqual("REVIEW_PENDING", ctx.state)
        ctx.transition("APPROVED_WITH_CONDITIONS")
        self.assertEqual("APPROVED_WITH_CONDITIONS", ctx.state)

    def test_missing_evidence_fails_closed(self):
        ctx = self.context()
        ctx.components[0] = ContextComponent("c-1", "x", {}, "", "", "SA", "retail", "", [])
        with self.assertRaises(ValueError):
            ctx.transition("VALIDATING")

    def test_tenant_scoped_idempotency(self):
        self.assertNotEqual(idempotency_fingerprint("org-a", "p", "k"), idempotency_fingerprint("org-b", "p", "k"))


if __name__ == "__main__":
    unittest.main()
