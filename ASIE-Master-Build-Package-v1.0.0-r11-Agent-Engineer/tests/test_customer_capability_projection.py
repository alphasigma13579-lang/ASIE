from __future__ import annotations

import copy
import unittest
from unittest.mock import patch
from backend import asie_local_api as api
from backend import release_info
from backend.identity import Principal
from backend.workflow import project_readiness
from backend.repository import ProjectRecord


class CustomerCapabilityProjectionTests(unittest.TestCase):
    def test_existing_runtime_owner_exposes_only_disabled_fact(self):
        fact = api.intelligence_context_construction_policy()
        self.assertEqual(fact["state"], "disabled")
        self.assertEqual(fact["owner"], "intelligence_ingress")
        self.assertEqual(set(fact), {"capability_id", "state", "owner", "version", "evidence_ref", "reason_key"})
        self.assertNotIn("enabled", fact)
        self.assertNotIn("sbom", fact)
        self.assertEqual(release_info.customer_capability_declarations(), [])

    def test_only_explicit_versioned_product_states_are_allowed_and_detached(self):
        declaration = {"capability_id": "synthetic", "state": "not_built", "owner": "product_engineering", "version": "test.v1", "evidence_ref": "synthetic-evidence", "reason_key": "synthetic_reason"}
        for state in ("not_built", "coming_soon"):
            source = declaration | {"state": state}
            with patch.object(release_info, "CUSTOMER_CAPABILITY_DECLARATIONS", (source,)):
                result = release_info.customer_capability_declarations()
                self.assertEqual(result, [source])
                result[0]["state"] = "mutated"
                self.assertEqual(source["state"], state)
        for change in ({"state": "disabled"}, {"state": "temporary_fault"}, {"owner": "unknown"}, {"version": ""}, {"enabled": True}, {"eta": "invented"}):
            with self.subTest(change=change), patch.object(release_info, "CUSTOMER_CAPABILITY_DECLARATIONS", (declaration | change,)), self.assertRaises(ValueError):
                release_info.customer_capability_declarations()

    def test_display_permission_uses_actual_role_without_mutating_source(self):
        item = {"action": {"required_permission": "platform.manage", "allowed": False}, "target": {"kind": "source_review"}}
        original = copy.deepcopy(item)
        viewer = Principal("u", "s", "o", "viewer")
        owner = Principal("u", "s", "o", "organization_owner")
        admin = Principal("u", "s", "o", None, "platform_admin")
        self.assertFalse(api.apply_recovery_permissions([item], viewer)[0]["action"]["allowed"])
        self.assertFalse(api.apply_recovery_permissions([item], owner)[0]["action"]["allowed"])
        self.assertTrue(api.apply_recovery_permissions([item], admin)[0]["action"]["allowed"])
        self.assertEqual(item, original)

    def test_projection_does_not_change_readiness_or_promote_reference_sources(self):
        project = ProjectRecord("p", "Name", "Sector", "SA", "starter", {}, "created", "updated", "o")
        sources = [{"source_id": "reference", "state": "reference_only", "reviewer_decision": "reference_only"}]
        baseline = project_readiness(project, [], sources)
        projected = project_readiness(project, [], sources, include_recovery=True)
        items = projected.pop("recovery_items")
        self.assertEqual(projected, baseline)
        self.assertTrue(any(item["requirement_code"] == "SOURCE_OWNER_REVIEW_REQUIRED" for item in items))
        self.assertFalse(any(item["target"]["kind"] == "source_review" for item in items))
