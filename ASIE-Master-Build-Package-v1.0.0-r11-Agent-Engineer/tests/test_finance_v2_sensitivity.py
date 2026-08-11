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
    build_financial_model,
    canonical_sha256,
    evaluate_sensitivity,
    prepare_sensitivity_run,
    validate_finance_input,
)
from backend.finance_v2.overrides import derive_validated_input
from tests.test_finance_v2_contracts import binding as finance_binding
from tests.test_finance_v2_contracts import valid_document
from tests.test_finance_v2_risk_profile_admission import (
    _binding as profile_binding,
    _finalize,
    sensitivity_profile,
)


_PRICE = "$.revenue_streams[rev-primary].price_series[*].value"
_VOLUME = "$.revenue_streams[rev-primary].volume_series[*].value"


def _metric_text(value) -> str | None:
    if value is None:
        return None
    text = format(value, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def _prepared(*, profile_mutator=None):
    document = valid_document()
    profile_document = sensitivity_profile()
    profile_document["archetype_ref"] = copy.deepcopy(document["archetype_ref"])
    profile_document["axes"][0]["target_ref"] = _PRICE
    profile_document["axes"][1]["target_ref"] = _VOLUME
    if profile_mutator is not None:
        profile_mutator(profile_document)
    _finalize(profile_document)
    risk_binding = replace(
        profile_binding(profile_document),
        dependency_hashes=(
            (
                f"archetype:{document['archetype_ref']['archetype_id']}@{document['archetype_ref']['version']}",
                document["archetype_ref"]["registry_hash"],
            ),
        ),
    )

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
    assert first.as_dict()["profile"]["schema_version"] == "finance-sensitivity-profile.v1"
    assert first.as_dict()["profile"]["dependency_hashes"]
    assert first.as_dict()["axes"] == [
        {
            "axis_id": "axis_price",
            "target_ref": _PRICE,
            "operation": "replace",
            "values": ["80", "100", "120"],
        },
        {
            "axis_id": "axis_volume",
            "target_ref": _VOLUME,
            "operation": "multiply",
            "values": ["0.8", "1", "1.2"],
        },
    ]


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


def test_evaluation_revalidates_prepared_provenance_before_any_cell_build(
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
        prepared,
        binding=replace(prepared.binding, organization_id="org-other"),
    )

    with pytest.raises(FinanceContractError) as error:
        evaluate_sensitivity(forged)

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
    assert "axes" in schema["required"]
    assert schema["properties"]["profile"]["additionalProperties"] is False
    assert "dependency_hashes" in schema["properties"]["profile"]["required"]
    assert len(schema["allOf"]) == 2


def test_2_by_3_grid_and_direct_cell_parity() -> None:
    def mutate(profile_document):
        profile_document["axes"][0]["values"] = ["20", "25.5"]
        profile_document["axes"][1]["values"] = ["0.8", "1", "1.2"]
        profile_document["maximum_cells"] = 6

    prepared = _prepared(profile_mutator=mutate)
    result = evaluate_sensitivity(prepared)

    assert [(cell.row_index, cell.column_index) for cell in result.cells] == [
        (row, column) for row in range(2) for column in range(3)
    ]
    first = result.cells[0]
    direct = derive_validated_input(
        prepared.validated_input,
        [
            {"target_ref": "$.working_capital.dso_days", "operation": "replace", "value": "30"},
            {"target_ref": _PRICE, "operation": "replace", "value": "20"},
            {"target_ref": _VOLUME, "operation": "multiply", "value": "0.8"},
        ],
        "$.test.direct",
    )
    model = build_financial_model(direct)
    assert first.derived_input_hash == direct.input_hash
    assert first.metrics == {
        metric_id: _metric_text(model.metrics[metric_id])
        for metric_id in prepared.profile_document["metric_ids"]
    }


def test_baseline_equivalent_cell_and_input_profile_immutability() -> None:
    def mutate(profile_document):
        profile_document["axes"][0]["values"] = ["25.50", "20"]
        profile_document["axes"][1]["values"] = ["1", "1.2"]
        profile_document["fixed_overrides"][0]["value"] = "15"
        profile_document["maximum_cells"] = 4

    prepared = _prepared(profile_mutator=mutate)
    input_before = prepared.validated_input.canonical_document
    profile_before = prepared.profile.canonical_document
    result = evaluate_sensitivity(prepared)
    baseline = build_financial_model(prepared.validated_input)

    assert result.cells[0].derived_input_hash != prepared.validated_input.input_hash
    assert result.cells[0].metrics == {
        metric_id: _metric_text(baseline.metrics[metric_id])
        for metric_id in prepared.profile_document["metric_ids"]
    }
    assert prepared.validated_input.canonical_document == input_before
    assert prepared.profile.canonical_document == profile_before


def test_maximum_21_by_21_grid_builds_exactly_once_per_cell(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def mutate(profile_document):
        profile_document["axes"][0]["values"] = [str(value) for value in range(1, 22)]
        profile_document["axes"][1]["values"] = [str(value) for value in range(1, 22)]
        profile_document["maximum_cells"] = 441

    prepared = _prepared(profile_mutator=mutate)
    builds = 0
    derivations = 0
    representative = build_financial_model(prepared.validated_input)

    def derived(_validated, _overrides, _field_ref):
        nonlocal derivations
        derivations += 1
        return prepared.validated_input

    def counted(_validated):
        nonlocal builds
        builds += 1
        return representative

    monkeypatch.setattr(sensitivity_module, "derive_validated_input", derived)
    monkeypatch.setattr(sensitivity_module, "build_financial_model", counted)
    result = evaluate_sensitivity(prepared)

    assert result.status == "dark_ready"
    assert len(result.cells) == 441
    assert derivations == 441
    assert builds == 441
    assert all(not hasattr(cell, "model") for cell in result.cells)


@pytest.mark.parametrize(
    "profile_transform, binding_transform, expected",
    [
        (lambda prepared: replace(prepared.profile, kind="distribution"), lambda binding: binding, "FIN2_SENSITIVITY_PROFILE_KIND"),
        (lambda prepared: replace(prepared.profile, status="draft"), lambda binding: binding, "FIN2_SENSITIVITY_PROFILE_KIND"),
        (lambda prepared: prepared.profile, lambda binding: replace(binding, owner_organization_id="org-other"), "FIN2_SENSITIVITY_BINDING_MISMATCH"),
        (lambda prepared: prepared.profile, lambda binding: replace(binding, registry_snapshot_hash="sha256:" + "0" * 64), "FIN2_SENSITIVITY_BINDING_MISMATCH"),
        (lambda prepared: prepared.profile, lambda binding: replace(binding, currency="USD"), "FIN2_SENSITIVITY_BINDING_MISMATCH"),
        (lambda prepared: prepared.profile, lambda binding: replace(binding, archetype_version="9.9.9"), "FIN2_SENSITIVITY_BINDING_MISMATCH"),
    ],
)
def test_profile_and_binding_tampering_fail_before_cell_build(
    profile_transform,
    binding_transform,
    expected,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = _prepared()
    calls = 0

    def unexpected(_):
        nonlocal calls
        calls += 1
        raise AssertionError("model must not be called")

    monkeypatch.setattr(sensitivity_module, "build_financial_model", unexpected)
    with pytest.raises(FinanceContractError) as error:
        prepare_sensitivity_run(
            prepared.validated_input,
            profile_transform(prepared),
            binding=binding_transform(prepared.binding),
        )

    assert error.value.code == expected
    assert calls == 0


def test_tampered_profile_body_and_missing_metric_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = _prepared()
    tampered = replace(
        prepared.profile,
        canonical_document=prepared.profile.canonical_document.replace(
            '"axis_price"', '"axis_price_tampered"', 1
        ),
    )
    with pytest.raises(FinanceContractError) as error:
        prepare_sensitivity_run(prepared.validated_input, tampered, binding=prepared.binding)
    assert error.value.code == "FIN2_SENSITIVITY_HASH_MISMATCH"

    original = sensitivity_module.build_financial_model

    def missing_metric(validated):
        model = original(validated)
        return replace(model, metrics={})

    monkeypatch.setattr(sensitivity_module, "build_financial_model", missing_metric)
    result = evaluate_sensitivity(prepared)
    assert result.status == "not_ready"
    assert result.cells == ()
    assert result.blockers[0]["code"] == "FIN2_SENSITIVITY_CELL_NOT_READY"


def test_result_hash_includes_engine_versions_and_imports_stay_dark_only() -> None:
    result = evaluate_sensitivity(_prepared())
    changed_finance = dict(result.as_dict(include_hash=False))
    changed_finance["finance_engine_version"] = "tampered"
    changed_sensitivity = dict(result.as_dict(include_hash=False))
    changed_sensitivity["sensitivity_engine_version"] = "tampered"

    assert canonical_sha256(changed_finance) != result.result_hash
    assert canonical_sha256(changed_sensitivity) != result.result_hash
    source = Path(sensitivity_module.__file__).read_text(encoding="utf-8")
    forbidden = ("module_runtime", "snapshot_assembly", "requests", "http", "socket", "provider")
    assert all(token not in source for token in forbidden)
