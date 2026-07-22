import unittest

from backend.identity import Principal
from backend.intelligence_authorization import authorize_intelligence_action


class Sink:
    def __init__(self): self.events = []
    def audit(self, **kwargs): self.events.append(kwargs)


class IntelligenceAuthorizationTests(unittest.TestCase):
    def test_same_tenant_reviewer_allowed_and_audited(self):
        sink = Sink()
        principal = Principal("u-1", "s-1", "org-a", "reviewer")
        authorize_intelligence_action(principal, organization_id="org-a", project_id="p-a", permission="review.write", action="aia.review.write", target_id="ctx-1", audit_sink=sink)
        self.assertEqual("allowed", sink.events[0]["result"])

    def test_cross_tenant_and_missing_principal_denied(self):
        sink = Sink()
        principal = Principal("u-1", "s-1", "org-a", "reviewer")
        for candidate in (principal, None):
            with self.assertRaises(PermissionError):
                authorize_intelligence_action(candidate, organization_id="org-b", project_id="p-a", permission="review.write", action="aia.review.write", target_id="ctx-1", audit_sink=sink)
        self.assertEqual(["denied", "denied"], [event["result"] for event in sink.events])

    def test_viewer_cannot_review(self):
        sink = Sink()
        with self.assertRaises(PermissionError):
            authorize_intelligence_action(Principal("u", "s", "org-a", "viewer"), organization_id="org-a", project_id="p", permission="review.write", action="aia.review.write", target_id="ctx", audit_sink=sink)


if __name__ == "__main__": unittest.main()
