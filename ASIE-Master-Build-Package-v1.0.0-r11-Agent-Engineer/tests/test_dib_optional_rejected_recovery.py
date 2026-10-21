"""Customer correction targets for nonrequired REJECTED persisted inputs."""
from contextlib import closing
from copy import deepcopy
from unittest.mock import patch

import pytest

from backend.dib_api import dib_customer_recovery, DIBApiError
from backend.dib_persistence import DIBPersistenceStore
from backend.dib_runtime import (
    FINANCE_REQUIRED_KEYS, _item, apply_customer_decision,
    build_dynamic_input_blueprint, build_approved_input_manifest,
)
from backend.dib_tenant_api import create_tenant_scoped_dib_api_controller
from backend.dib_tenant_boundary import DIBTenantContext


def optional_rejected_blueprint(key):
    values = dict(zip(FINANCE_REQUIRED_KEYS, (120000, 42000, 18, 7, 4200))) | {key: 123}
    rows = [apply_customer_decision(_item(k, required=k in FINANCE_REQUIRED_KEYS),
                                   {"action": "enter_value", "value": value}) for k, value in values.items()]
    rows[-1] = apply_customer_decision(rows[-1], {"action": "reject"})
    return build_dynamic_input_blueprint({"project_id": "synthetic-optional-project"}, rows)


@pytest.mark.parametrize("key", ["rent_monthly", "annual_discount_rate", "synthetic_custom_cost"])
def test_persisted_optional_rejection_has_exact_recovery_target_and_can_be_corrected(key):
    with closing(DIBPersistenceStore()) as store:
        context = DIBTenantContext("synthetic-org", "synthetic-user", "synthetic-principal")
        controller = create_tenant_scoped_dib_api_controller(
            store, project_organization_resolver=lambda p: "synthetic-org" if p == "synthetic-optional-project" else None,
            trusted_internal_context=context,
        )
        sid = controller.dispatch("POST", "/api/dib/sessions", {
            "project_profile": {"project_id": "synthetic-optional-project"},
        }).payload["session"]["session_id"]
        blueprint = optional_rejected_blueprint(key)
        original = controller.dispatch("POST", f"/api/dib/sessions/{sid}/blueprints", {"blueprint": blueprint}).payload["blueprint"]
        before = deepcopy(store.load_session(sid))
        with patch("backend.dib_api.execute_dib_module_adapter", side_effect=AssertionError("GET must not build")):
            loaded = controller.dispatch("GET", f"/api/dib/sessions/{sid}").payload["session"]
        assert store.load_session(sid) == before
        assert build_approved_input_manifest(loaded["current_blueprint"])["status"] == "blocked"
        assert len(loaded["recovery_items"]) == 1
        recovery = loaded["recovery_items"][0]
        row = next(row for row in loaded["current_blueprint"]["items"] if row["input_key"] == key)
        assert recovery["target"] == {
            "kind": "dib_item", "session_id": sid, "blueprint_id": original["blueprint_id"],
            "item_id": row["item_id"], "input_key": key, "field_keys": [key],
        }
        assert recovery["source"]["payload_hash"] == original["payload_hash"]
        assert recovery["source"]["organization_id"] == context.organization_id
        assert recovery["required"] is True and recovery["resolution"] == "unresolved"
        assert recovery["action"]["allowed"] is False  # HTTP principal owns display permission.
        controller.dispatch("POST", f"/api/dib/sessions/{sid}/blueprints", {
            "contract_id": "dib.blueprint.write.v2", "expected_original": loaded["origin_reference"],
            "item_decisions": [{"item_id": row["item_id"], "input_key": key,
                                "decision": {"action": "enter_value", "value": 42}}],
        })
        corrected = controller.dispatch("GET", f"/api/dib/sessions/{sid}").payload["session"]
        assert corrected["recovery_items"] == []
        assert next(row for row in corrected["current_blueprint"]["items"] if row["input_key"] == key)["value"] == 42
        assert store.load_blueprint(original["blueprint_id"])["payload"] == original["payload"]
        assert corrected.get("approved_manifest") is None and corrected.get("validation_gate") is None
        with pytest.raises(DIBApiError):
            controller.dispatch("GET", f"/api/dib/sessions/{sid}", context=DIBTenantContext("other-org", "other-user", "other-principal"))


def test_projection_extends_only_rejected_optional_rows_and_preserves_required_order():
    blueprint = optional_rejected_blueprint("synthetic_custom_cost")
    blueprint["items"][0].update(value=None, value_state="UNKNOWN")
    blueprint["items"] += [_item("optional_unknown", required=False), _item("optional_suggested", state="AI_SUGGESTED")]
    session = {"session_id": "s", "project_id": blueprint["project_id"], "current_blueprint": blueprint,
               "origin_reference": {"blueprint_id": blueprint["blueprint_id"], "revision": 1, "payload_hash": "synthetic-hash"}}
    result = dib_customer_recovery(session, "synthetic-org")
    assert [row["target"].get("input_key") for row in result] == [FINANCE_REQUIRED_KEYS[0], "synthetic_custom_cost"]
    blueprint["items"][-3]["item_id"] = blueprint["items"][0]["item_id"]
    invalid = dib_customer_recovery(session, "synthetic-org")
    assert invalid and all(row["target"] == {"kind": "owner_review"} for row in invalid)
