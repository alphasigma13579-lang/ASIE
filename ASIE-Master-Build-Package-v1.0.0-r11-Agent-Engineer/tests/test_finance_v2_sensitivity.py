from __future__ import annotations

import copy
import json
from dataclasses import replace
from pathlib import Path

import pytest

import backend.finance_v2.sensitivity as sensitivity_module
from backend.finance_v2 import (
    FinanceContractError,
    SensitivityExecutionBinding,
    admit_risk_profile,
    canonical_sha256,
    evaluate_sensitivity,
    prepare_sensitivity_run,
    validate_finance_input,
)
from tests.test_finance_v2_contracts import binding as finance_binding
from tests.test_finance_v2_contracts import valid_document
from tests.test_finance_v2_risk_profile_admission import (
    _binding as profile_binding,
    _finalize,
    sensitivity_profile,
)


_PRICE = "$.revenue_streams[rev-primary].price_series[*].value"
_VOLUME = "$.revenue_streams[rev-primary].volume_series[*].value"


def _prepared():
    document = valid_document()
    profile_document = sensitivity_profile()
    profile_document["archetype_ref"] = copy.deepcopy(document["archetype_ref"])
    profile_document["axes"][0]["target_ref"] = _PRICE
    profile_document["axes"][1]["target_ref"] = _VOLUME
    _finalize(profile_document)
    risk_binding = profile_binding(profile_document)

    document["metadata"] = {
        "approved_manifest_id": risk_binding.approved_manifest_id,
        "approved_manifest_hash": risk_binding.approved_manifest_hash,
        "policy_ref": risk_binding.policy_ref,
    }
    validated = validate_finance_input(
        document,
        binding=replace(
            finance_binding(),
            approved_manifest_id=risk_binding.approved_manifest_id,
            approved_manifest_hash=risk_binding.approved_manifest_hash,
            policy_ref=risk_binding.policy_ref,
        ),
    )
    profile = admit_risk_profile(profile_document, binding=risk_binding)
    binding = SensitivityExecutionBinding(
        risk_profile_binding=risk_binding,
        authoritative_admission=True,
        organization_id=validated.organization_id,
        owner_organization_id=risk_binding.owner_organization_id,
        scope_kind=risk_binding.scope_kind,
        profile_schema_version=profile_document["schema_version"],
        profile_id=profile.profile_id,
        profile_version=profile.version,
        profile_hash=profile.content_hash,
        registry_snapshot_hash=profile.registry_snapshot_hash,
        approved_manifest_id=profile.approved_manifest_id,
        approved_manifest_hash=profile.approved_manifest_hash,
        policy_ref=profile.policy_ref,
        policy_version=profile.policy_version,
        policy_hash=profile.policy_hash,
        finance_input_hash=validated.input_hash,
        currency=validated.currency,
        archetype_id=document["archetype_ref"]["archetype_id"],
        archetype_version=document["archetype_ref"]["version"],
        archetype_registry_hash=document["archetype_ref"]["registry_hash"],
    )
    return prepare_sensitivity_run(validated, profile, binding=binding)


def test_deterministic_2d_grid_is_complete_ordered_and_reproducible() -> None:
    prepared = _prepared()
    first = evaluate_sensitivity(prepared)
    second = evaluate_sensitivity(prepared)

    assert first.status == "dark_ready"
    assert first.cell_count == 9
    assert len(first.cells) == 9
    assert first.blockers == ()
    assert [(cell.row_index, cell.column_index) for cell in first.cells] == [
        (row, column) for row in range(3) for column in range(3)
    ]
    assert first.cells[0].derived_input_hash != first.cells[-1].derived_input_hash
    assert first.result_hash == canonical_sha256(first.as_dict(include_hash=False))
    assert first.as_dict() == second.as_dict()
    assert first.as_dict()["execution_scope"] == "dark_build"
    assert first.as_dict()["snapshot_eligible"] is False


def test_each_cell_builds_once_and_fixed_overrides_apply(monkeypatch: pytest.MonkeyPatch) -> None:
    prepared = _prepared()
    calls = 0
    original = sensitivity_module.build_financial_model

    def counted(validated):
        nonlocal calls
        calls += 1
        assert validated.thaw()["working_capital"]["dso_days"] == "30"
        return original(validated)

    monkeypatch.setattr(sensitivity_module, "build_financial_model", counted)
    result = evaluate_sensitivity(prepared)

    assert result.status == "dark_ready"
    assert calls == 9


def test_first_failed_cell_is_atomic_and_returns_no_partial_metrics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = _prepared()
    calls = 0
    original = sensitivity_module.build_financial_model

    def fail_second(validated):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise FinanceContractError("FIN2_TEST_STOP", "$.test", "forced test stop")
        return original(validated)

    monkeypatch.setattr(sensitivity_module, "build_financial_model", fail_second)
    result = evaluate_sensitivity(prepared)

    assert result.status == "not_ready"
    assert result.cells == ()
    assert calls == 2
    assert result.blockers[0]["code"] == "FIN2_SENSITIVITY_CELL_NOT_READY"
    assert result.blockers[0]["field_ref"] == "$.cells[0][1]"


def test_tenant_or_admission_mismatch_fails_before_any_cell_build(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = _prepared()
    calls = 0

    def unexpected(_):
        nonlocal calls
        calls += 1
        raise AssertionError("model must not be called")

    monkeypatch.setattr(sensitivity_module, "build_financial_model", unexpected)
    forged = replace(
        prepared.binding,
        organization_id="org-other",
    )
    with pytest.raises(FinanceContractError) as error:
        prepare_sensitivity_run(prepared.validated_input, prepared.profile, binding=forged)

    assert error.value.code == "FIN2_SENSITIVITY_BINDING_MISMATCH"
    assert calls == 0


def test_execution_binding_must_retain_authoritative_admission_source() -> None:
    prepared = _prepared()
    forged = replace(
        prepared.binding,
        authoritative_admission=False,
    )

    with pytest.raises(FinanceContractError) as error:
        prepare_sensitivity_run(prepared.validated_input, prepared.profile, binding=forged)

    assert error.value.code == "FIN2_SENSITIVITY_ADMISSION"


def test_result_schema_expresses_dark_only_and_atomic_contract() -> None:
    schema_path = (
        Path(__file__).resolve().parents[1]
        / "schemas"
        / "finance"
        / "finance-sensitivity-result.v1.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    assert schema["properties"]["execution_scope"]["const"] == "dark_build"
    assert schema["properties"]["snapshot_eligible"]["const"] is False
    assert schema["properties"]["cell_count"]["maximum"] == 441
    assert len(schema["allOf"]) == 2
