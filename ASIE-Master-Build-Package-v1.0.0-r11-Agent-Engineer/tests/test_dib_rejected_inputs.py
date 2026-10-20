"""REJECTED values remain review history, never approved calculation inputs."""
from copy import deepcopy
from contextlib import closing
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from backend.dib_canonical_finance_admission import DIBCanonicalFinanceAdmission
from backend.dib_manifest_run_readiness import build_manifest_run_readiness
from backend.dib_persistence import DIBPersistenceStore
from backend.dib_project_run_gate import build_dib_project_run_manifest_gate
from backend.dib_runtime import (
    APPROVABLE_STATES, FINANCE_REQUIRED_KEYS, OPTIONAL_FINANCE_DEFAULTS,
    _item, apply_customer_decision, build_approved_input_manifest,
    build_dynamic_input_blueprint, finance_from_approved_manifest,
    validate_manifest_for_runtime,
)
from backend.dib_server_owned_manifest_chain import DIBServerOwnedManifestChain
from backend.dib_tenant_boundary import DIBTenantContext


def blueprint_with_value(key, value=123):
    values = dict(zip(FINANCE_REQUIRED_KEYS, (120000, 42000, 18, 7, 4200)))
    values[key] = value
    items = [apply_customer_decision(
        _item(k, required=k in FINANCE_REQUIRED_KEYS), {"action": "enter_value", "value": v},
    ) for k, v in values.items()]
    return build_dynamic_input_blueprint({"project_id": "synthetic-rejected-project"}, items)


REJECTED_KEYS = (*FINANCE_REQUIRED_KEYS, "rent_monthly", "annual_discount_rate", "custom_cost")


@pytest.mark.parametrize("key", REJECTED_KEYS)
@pytest.mark.parametrize("value", [123, 0, None])
def test_rejected_item_is_not_normalized_or_approved(key, value):
    blueprint = blueprint_with_value(key)
    blueprint["items"] = [apply_customer_decision(row | {"value": value}, {"action": "reject"})
                          if row["input_key"] == key else row for row in blueprint["items"]]
    before = deepcopy(blueprint)
    manifest = build_approved_input_manifest(blueprint)
    assert key not in manifest["normalized_inputs"]
    assert manifest["status"] == "blocked"
    assert validate_manifest_for_runtime(manifest)["status"] == "blocked"
    assert any(b["code"] == f"REJECTED_{key.upper()}" for b in manifest["blockers"])
    rejected = next(row for row in manifest["items"] if row["input_key"] == key)
    assert rejected["value"] == value
    assert rejected["value_state"] == rejected["state"] == "REJECTED"
    assert blueprint == before
    with patch("backend.dib_runtime.finance_result_set") as finance:
        result, blockers = finance_from_approved_manifest(manifest)
    assert result["status"] == "not_ready" and blockers
    finance.assert_not_called()


@pytest.mark.parametrize("state", sorted(APPROVABLE_STATES))
def test_existing_approvable_states_and_defaults_preserved(state):
    blueprint = blueprint_with_value("unit_price", 18)
    value = 0 if state in {"INTENTIONAL_ZERO", "NOT_APPLICABLE"} else 18
    blueprint["items"] = [row | {"value_state": state, "value": value, "reason": "Synthetic explicit reason"}
                          if row["input_key"] == "unit_price" else row for row in blueprint["items"]]
    manifest = build_approved_input_manifest(blueprint)
    assert manifest["status"] == "approved"
    assert manifest["normalized_inputs"] == OPTIONAL_FINANCE_DEFAULTS | {
        "startup_cost": 120000., "monthly_fixed_cost": 42000., "unit_price": float(value),
        "variable_cost": 7., "monthly_units": 4200.,
    }
    assert validate_manifest_for_runtime(manifest)["status"] == "passed"


@pytest.mark.parametrize("key", ["unit_price", "rent_monthly", "annual_discount_rate"])
def test_old_approved_manifest_and_passed_gate_cannot_admit_rejected_value(key):
    manifest = build_approved_input_manifest(blueprint_with_value(key))
    old_gate = validate_manifest_for_runtime(manifest)
    # Shape emitted by the defective builder: retained numeric value plus REJECTED,
    # with status approved, no blockers, and a previously passed validation gate.
    manifest["items"] = [row | {"value_state": "REJECTED", "state": "REJECTED", "review_status": "rejected"}
                         if row["input_key"] == key else row for row in manifest["items"]]
    before = deepcopy((manifest, old_gate))
    assert validate_manifest_for_runtime(manifest)["status"] == "blocked"
    admission = build_dib_project_run_manifest_gate(manifest, old_gate)
    assert admission["status"] == "blocked"
    assert admission["normalized_inputs"] == {}
    assert (manifest, old_gate) == before


@pytest.mark.parametrize("write_mode", ["initial", "decisions", "full_list"])
@pytest.mark.parametrize("key", ["unit_price", "rent_monthly", "custom_cost"])
def test_persisted_rejection_blocks_server_owned_chain_and_reentry_restores_it(write_mode, key):
    with closing(DIBPersistenceStore()) as store:
        chain = DIBServerOwnedManifestChain(store)
        blueprint = blueprint_with_value(key)
        sid = store.start_session(blueprint["project_profile"])["session_id"]
        if write_mode == "initial":
            blueprint["items"] = [apply_customer_decision(row, {"action": "reject"})
                                  if row["input_key"] == key else row for row in blueprint["items"]]
        saved = store.save_blueprint(sid, blueprint)
        if write_mode != "initial":
            if write_mode == "decisions":
                target = next(row for row in blueprint["items"] if row["input_key"] == key)
                kwargs = {"item_decisions": [{"item_id": target["item_id"], "input_key": key,
                          "decision": {"action": "reject", "reason": "Synthetic rejection"}}]}
            else:
                blueprint["items"] = [row | {"value_state": "REJECTED"} if row["input_key"] == key else row
                                      for row in blueprint["items"]]
                kwargs = {}
            saved = store.save_blueprint(sid, blueprint, command_contract="dib.blueprint.write.v2",
                                         expected_original=saved["origin_reference"], **kwargs)
        rejected_record = deepcopy(saved)
        manifest = chain.build_manifest(sid, {}, actor_user_id="synthetic-owner")["payload"]
        assert key not in manifest["normalized_inputs"]
        assert manifest["status"] == "blocked"
        gate = chain.build_gate(sid, {}, actor_user_id="synthetic-owner")["payload"]
        assert gate["status"] == "blocked"
        assert not build_manifest_run_readiness(store.load_session(sid))["ready_for_project_run"]
        target = next(row for row in saved["payload"]["items"] if row["input_key"] == key)
        store.save_blueprint(sid, saved["payload"], command_contract="dib.blueprint.write.v2",
                            expected_original=saved["origin_reference"], item_decisions=[{
                                "item_id": target["item_id"], "input_key": key,
                                "decision": {"action": "enter_value", "value": 42},
                            }])
        restored = chain.build_manifest(sid, {}, actor_user_id="synthetic-owner")["payload"]
        assert restored["status"] == "approved"
        assert restored["normalized_inputs"][key] == 42
        assert chain.build_gate(sid, {}, actor_user_id="synthetic-owner")["payload"]["status"] == "passed"
        assert store.load_blueprint(rejected_record["blueprint_id"]) == {
            k: v for k, v in rejected_record.items() if k != "origin_reference"
        }


def test_old_server_owned_hash_valid_chain_stops_before_executor_without_writes():
    with closing(DIBPersistenceStore()) as store:
        chain = DIBServerOwnedManifestChain(store)
        blueprint = blueprint_with_value("unit_price")
        sid = store.start_session(blueprint["project_profile"])["session_id"]
        blueprint["items"] = [apply_customer_decision(row, {"action": "reject"})
                              if row["input_key"] == "unit_price" else row for row in blueprint["items"]]
        store.save_blueprint(sid, blueprint)
        old_manifest = build_approved_input_manifest(blueprint_with_value("unit_price"))
        old_manifest["items"] = deepcopy(blueprint["items"])
        old_gate = {"contract_id": "manifest.validation.v1", "gate_id": "synthetic-old-gate",
                    "status": "passed", "blockers": [], "created_at": old_manifest["created_at"]}
        # Persist with real server lineage/hashes; only emulate the two old outputs.
        with patch("backend.dib_module_adapters.build_approved_input_manifest", return_value=old_manifest), \
             patch("backend.dib_module_adapters.validate_manifest_for_runtime", return_value=old_gate):
            chain.build_manifest(sid, {}, actor_user_id="synthetic-owner")
            chain.build_gate(sid, {}, actor_user_id="synthetic-owner")
        def database_rows():
            with store._read_connection() as conn:
                tables = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
                return {table: [tuple(row) for row in conn.execute(f'SELECT * FROM "{table}" ORDER BY rowid')]
                        for table in tables}
        before = database_rows()
        assert not build_manifest_run_readiness(store.load_session(sid))["ready_for_project_run"]
        repository, executor = Mock(), Mock()
        repository.get_project.return_value = SimpleNamespace(organization_id="synthetic-org")
        context = DIBTenantContext(organization_id="synthetic-org", user_id="synthetic-owner",
                                   principal_session_id="synthetic-principal")
        admission = DIBCanonicalFinanceAdmission(store, repository, executor)
        result = admission.execute(sid, context)
        assert result["status"] == "blocked"
        executor.execute.assert_not_called()
        repository.save_run_snapshot.assert_not_called()
        assert database_rows() == before
