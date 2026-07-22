import unittest

from backend.intelligence_workflow import IntelligenceContextWorkflow


class IntelligenceWorkflowTests(unittest.TestCase):
    def test_success_is_review_pending_and_not_snapshot(self):
        result = IntelligenceContextWorkflow().execute(organization_id="o", project_id="p", context_build_id="c", idempotency_key="k", builder=lambda: {"components": ["x"]})
        self.assertEqual("REVIEW_PENDING", result.state)
        self.assertTrue(all(event["snapshot_mutation"] is False for event in result.audit))

    def test_replay_is_idempotent(self):
        workflow = IntelligenceContextWorkflow()
        first = workflow.execute(organization_id="o", project_id="p", context_build_id="c", idempotency_key="k", builder=lambda: {"x": 1})
        second = workflow.execute(organization_id="o", project_id="p", context_build_id="other", idempotency_key="k", builder=lambda: {"x": 2})
        self.assertIs(first, second)

    def test_deterministic_failure_is_fail_closed_without_retry(self):
        calls = []
        result = IntelligenceContextWorkflow(max_retries=2).execute(organization_id="o", project_id="p", context_build_id="c", idempotency_key="k", builder=lambda: calls.append(1) or {})
        self.assertEqual("FAILED", result.state)
        self.assertEqual(1, len(calls))

    def test_transient_os_error_has_bounded_retry(self):
        calls = []
        def builder():
            calls.append(1)
            if len(calls) < 3: raise OSError("local transient")
            return {"ok": True}
        result = IntelligenceContextWorkflow(max_retries=2).execute(organization_id="o", project_id="p", context_build_id="c", idempotency_key="k", builder=builder)
        self.assertEqual("REVIEW_PENDING", result.state)
        self.assertEqual(3, result.attempts)


if __name__ == "__main__": unittest.main()
