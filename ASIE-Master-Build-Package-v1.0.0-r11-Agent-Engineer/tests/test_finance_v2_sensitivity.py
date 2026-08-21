from __future__ import annotations

import copy
import json
import re
import weakref
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

import backend.finance_v2.sensitivity as sensitivity_module
from backend.finance_v2 import (
    FinanceContractError,
    build_financial_model,
    canonical_json,
    canonical_sha256,
    evaluate_sensitivity,
    prepare_sensitivity_run,
)
from backend.finance_v2.overrides import derive_validated_input
from scripts.benchmark_finance_v2_sensitivity import _peak_rss_mib
from tests.finance_v2_sensitivity_fixture import (
    MAXIMUM_PRICE_AXIS_VALUES,
    MAXIMUM_VOLUME_AXIS_VALUES,
    controlled_sensitivity_prepared_run,
)


_PRICE = "$.revenue_streams[rev-primary].price_series[*].value"
_VOLUME = "$.revenue_streams[rev-primary].volume_series[*].value"


def _metric_text(value) -> str | None:
    if value is None:
        return None
    text = format(value, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def test_peak_rss_conversion_uses_platform_specific_units() -> None:
    assert _peak_rss_mib(1024, "linux") == 1
    assert _peak_rss_mib(1024 * 1024, "darwin") == 1
    with pytest.raises(RuntimeError, match="unsupported ru_maxrss unit"):
        _peak_rss_mib(1024, "win32")


def test_governed_fixture_has_finite_requested_metrics() -> None:
    prepared = controlled_sensitivity_prepared_run()
    model = build_financial_model(prepared.validated_input)

    for metric_id in prepared.profile_document["metric_ids"]:
        value = model.metrics[metric_id]
        assert isinstance(value, Decimal)
        assert value.is_finite()


def test_deterministic_2d_grid_is_complete_ordered_and_reproducible() -> None:
    prepared = controlled_sensitivity_prepared_run()
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
    assert first.as_dict()["organization_id"] == prepared.validated_input.organization_id
    assert first.as_dict()["project_id"] == prepared.validated_input.project_id
    assert first.as_dict()["run_id"] == prepared.validated_input.run_id
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


def test_result_state_is_deeply_immutable_and_serialization_is_defensive(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ready = evaluate_sensitivity(controlled_sensitivity_prepared_run())
    ready_before = ready.as_dict()
    metrics_copy = ready.cells[0].metrics
    metrics_copy["npv_unlevered"] = "forged"
    axes_copy = ready.axes
    axes_copy[0]["values"][0] = "forged"

    assert ready.as_dict() == ready_before
    assert ready.result_hash == canonical_sha256(
        ready.as_dict(include_hash=False)
    )

    def forced_failure(_validated):
        raise FinanceContractError(
            "FIN2_TEST_IMMUTABLE_BLOCKER",
            "$.test",
            "forced blocker",
        )

    monkeypatch.setattr(
        sensitivity_module,
        "build_financial_model",
        forced_failure,
    )
    blocked = evaluate_sensitivity(controlled_sensitivity_prepared_run())
    blocked_before = blocked.as_dict()
    blocker_copy = blocked.blockers[0]
    blocker_copy["cause_code"] = "forged"

    assert blocked.as_dict() == blocked_before
    assert blocked.result_hash == canonical_sha256(
        blocked.as_dict(include_hash=False)
    )


def test_each_cell_builds_once_and_non_idempotent_fixed_override_applies_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def mutate(profile_document):
        profile_document["fixed_overrides"][0]["operation"] = "add"
        profile_document["fixed_overrides"][0]["value"] = "5"

    prepared = controlled_sensitivity_prepared_run(profile_mutator=mutate)
    baseline_dso = Decimal(
        prepared.validated_input.thaw()["working_capital"]["dso_days"]
    )
    expected_dso = _metric_text(baseline_dso + Decimal("5"))
    calls = 0
    original = sensitivity_module.build_financial_model

    def counted(validated):
        nonlocal calls
        calls += 1
        assert (
            validated.thaw()["working_capital"]["dso_days"]
            == expected_dso
        )
        return original(validated)

    monkeypatch.setattr(sensitivity_module, "build_financial_model", counted)
    result = evaluate_sensitivity(prepared)

    assert result.status == "dark_ready"
    assert calls == 9


def test_first_failed_cell_is_atomic_and_returns_no_partial_metrics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = controlled_sensitivity_prepared_run()
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
    assert result.blockers[0]["stage"] == "model_build"
    assert result.blockers[0]["cause_code"] == "FIN2_TEST_STOP"


def test_input_derivation_failure_stops_before_current_and_later_cell_builds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = controlled_sensitivity_prepared_run()
    derivations = 0
    builds = 0
    original_derive = sensitivity_module.derive_validated_input
    original_build = sensitivity_module.build_financial_model

    def fail_second_derivation(validated, overrides, field_ref):
        nonlocal derivations
        derivations += 1
        if derivations == 2:
            raise FinanceContractError(
                "FIN2_TEST_DERIVATION_STOP",
                field_ref,
                "forced derivation stop",
            )
        return original_derive(validated, overrides, field_ref)

    def counted_build(validated):
        nonlocal builds
        builds += 1
        return original_build(validated)

    monkeypatch.setattr(
        sensitivity_module,
        "derive_validated_input",
        fail_second_derivation,
    )
    monkeypatch.setattr(
        sensitivity_module,
        "build_financial_model",
        counted_build,
    )
    result = evaluate_sensitivity(prepared)

    assert result.status == "not_ready"
    assert result.cells == ()
    assert derivations == 2
    assert builds == 1
    assert result.blockers[0]["field_ref"] == "$.cells[0][1]"
    assert result.blockers[0]["stage"] == "input_derivation"
    assert (
        result.blockers[0]["cause_code"]
        == "FIN2_TEST_DERIVATION_STOP"
    )


def test_tenant_or_admission_mismatch_fails_before_any_cell_build(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = controlled_sensitivity_prepared_run()
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


@pytest.mark.parametrize(
    ("field", "forged_value"),
    [
        ("project_id", "project-forged"),
        ("run_id", "run-forged"),
        ("currency", "USD"),
    ],
)
def test_canonical_document_identity_matches_cached_and_trusted_binding(
    field: str,
    forged_value: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = controlled_sensitivity_prepared_run()
    calls = 0

    def unexpected(_) -> None:
        nonlocal calls
        calls += 1
        raise AssertionError("model must not be called")

    monkeypatch.setattr(sensitivity_module, "build_financial_model", unexpected)
    forged = replace(
        prepared,
        validated_input=replace(
            prepared.validated_input,
            **{field: forged_value},
        ),
        binding=replace(
            prepared.binding,
            **{field: forged_value},
        ),
    )

    with pytest.raises(FinanceContractError) as error:
        evaluate_sensitivity(forged)

    assert error.value.code == "FIN2_SENSITIVITY_BINDING_MISMATCH"
    assert error.value.field_ref == f"$.{field}"
    assert calls == 0


def test_evaluation_revalidates_prepared_provenance_before_any_cell_build(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = controlled_sensitivity_prepared_run()
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


def test_tampered_finance_document_with_stale_hash_fails_before_any_cell_build(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = controlled_sensitivity_prepared_run()
    calls = 0

    def unexpected(_):
        nonlocal calls
        calls += 1
        raise AssertionError("model must not be called")

    monkeypatch.setattr(sensitivity_module, "build_financial_model", unexpected)
    tampered_document = prepared.validated_input.thaw()
    tampered_document["working_capital"]["dso_days"] = "999"
    forged = replace(
        prepared,
        validated_input=replace(
            prepared.validated_input,
            canonical_document=canonical_json(tampered_document),
        ),
    )

    with pytest.raises(FinanceContractError) as error:
        evaluate_sensitivity(forged)

    assert error.value.code == "FIN2_SENSITIVITY_BINDING_MISMATCH"
    assert calls == 0


def test_forged_declared_profile_hash_fails_before_any_cell_build(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = controlled_sensitivity_prepared_run()
    calls = 0

    def unexpected(_) -> None:
        nonlocal calls
        calls += 1
        raise AssertionError("model must not be called")

    monkeypatch.setattr(sensitivity_module, "build_financial_model", unexpected)
    forged_document = prepared.profile.thaw()
    forged_document["content_hash"] = "sha256:" + "f" * 64
    forged = replace(
        prepared,
        profile=replace(
            prepared.profile,
            canonical_document=canonical_json(forged_document),
        ),
    )

    with pytest.raises(FinanceContractError) as error:
        evaluate_sensitivity(forged)

    assert error.value.code == "FIN2_SENSITIVITY_HASH_MISMATCH"
    assert error.value.field_ref == "$.content_hash"
    assert calls == 0


def test_tampered_profile_dependency_lineage_fails_before_any_cell_build(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = controlled_sensitivity_prepared_run()
    calls = 0

    def unexpected(_):
        nonlocal calls
        calls += 1
        raise AssertionError("model must not be called")

    monkeypatch.setattr(sensitivity_module, "build_financial_model", unexpected)
    forged = replace(
        prepared,
        profile=replace(
            prepared.profile,
            dependency_hashes=(
                ("archetype:forged@9.9.9", "sha256:" + "f" * 64),
            ),
        ),
    )

    with pytest.raises(FinanceContractError) as error:
        evaluate_sensitivity(forged)

    assert error.value.code == "FIN2_SENSITIVITY_BINDING_MISMATCH"
    assert calls == 0


@pytest.mark.parametrize(
    "field, value",
    [
        ("execution_scope", "runtime"),
        ("runtime_eligible", True),
        ("runtime_eligible", None),
        ("runtime_eligible", 0),
        ("runtime_eligible", ""),
    ],
)
def test_prepared_capability_is_explicitly_dark_and_not_runtime_eligible(
    field,
    value,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = controlled_sensitivity_prepared_run()
    assert prepared.execution_scope == "dark_sensitivity_v1"
    assert prepared.runtime_eligible is False
    calls = 0

    def unexpected(_):
        nonlocal calls
        calls += 1
        raise AssertionError("model must not be called")

    monkeypatch.setattr(sensitivity_module, "build_financial_model", unexpected)
    with pytest.raises(FinanceContractError) as error:
        evaluate_sensitivity(replace(prepared, **{field: value}))

    assert error.value.code == "FIN2_SENSITIVITY_PREPARED_SCOPE"
    assert calls == 0


@pytest.mark.parametrize("value", [False, None, 0, 1, "yes"])
def test_execution_binding_must_retain_authoritative_admission_source(
    value,
) -> None:
    prepared = controlled_sensitivity_prepared_run()
    forged = replace(
        prepared.binding,
        authoritative_admission=value,
    )

    with pytest.raises(FinanceContractError) as error:
        prepare_sensitivity_run(
            prepared.validated_input,
            prepared.profile,
            binding=forged,
        )

    assert error.value.code == "FIN2_SENSITIVITY_ADMISSION"


@pytest.mark.parametrize("value", [True, None, 0, 1, "yes"])
def test_profile_execution_ready_requires_exact_false(value) -> None:
    prepared = controlled_sensitivity_prepared_run()
    forged_profile = replace(prepared.profile, execution_ready=value)

    with pytest.raises(FinanceContractError) as error:
        prepare_sensitivity_run(
            prepared.validated_input,
            forged_profile,
            binding=prepared.binding,
        )

    assert error.value.code == "FIN2_SENSITIVITY_EXECUTION_STATE"


@pytest.mark.parametrize("value", [False, None, 0, 1, "yes"])
def test_retained_admission_authority_requires_exact_true(value) -> None:
    prepared = controlled_sensitivity_prepared_run()
    source = replace(
        prepared.binding.risk_profile_binding,
        authoritative=value,
    )
    forged = replace(prepared.binding, risk_profile_binding=source)

    with pytest.raises(FinanceContractError) as error:
        prepare_sensitivity_run(
            prepared.validated_input,
            prepared.profile,
            binding=forged,
        )

    assert error.value.code == "FIN2_SENSITIVITY_ADMISSION"


@pytest.mark.parametrize("value", [False, None, 0, 1, "yes"])
def test_global_admission_requires_exact_true_permission(value) -> None:
    prepared = controlled_sensitivity_prepared_run()
    source = replace(
        prepared.binding.risk_profile_binding,
        scope_kind="global",
        owner_organization_id=None,
        allow_global=value,
    )
    forged = replace(
        prepared.binding,
        scope_kind="global",
        owner_organization_id=None,
        risk_profile_binding=source,
    )

    with pytest.raises(FinanceContractError) as error:
        prepare_sensitivity_run(
            prepared.validated_input,
            prepared.profile,
            binding=forged,
        )

    assert error.value.code == "FIN2_SENSITIVITY_TENANT"


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
    assert schema["properties"]["cells"]["maxItems"] == 441
    assert schema["properties"]["cells"]["uniqueItems"] is True
    assert schema["properties"]["cell_count"]["minimum"] == 4
    non_empty_profile_fields = (
        "profile_id",
        "version",
        "approved_manifest_id",
        "policy_ref",
        "policy_version",
    )
    for field in non_empty_profile_fields:
        assert schema["properties"]["profile"]["properties"][field][
            "minLength"
        ] == 1
    assert schema["properties"]["profile"]["properties"][
        "dependency_hashes"
    ]["items"]["properties"]["ref"]["minLength"] == 1
    assert schema["properties"]["finance_engine_version"]["minLength"] == 1
    assert schema["properties"]["sensitivity_engine_version"][
        "minLength"
    ] == 1
    assert schema["properties"]["axis_ids"]["items"]["minLength"] == 1
    assert {
        "organization_id",
        "project_id",
        "run_id",
        "currency",
        "archetype_ref",
    } <= set(schema["required"])
    assert schema["properties"]["currency"]["pattern"] == "^[A-Z]{3}$"
    archetype_schema = schema["properties"]["archetype_ref"]
    assert archetype_schema["additionalProperties"] is False
    assert set(archetype_schema["required"]) == {
        "archetype_id",
        "version",
        "registry_hash",
    }
    governed_metrics = {
        "npv_unlevered",
        "irr_unlevered",
        "mirr_unlevered",
        "payback_months",
        "break_even",
        "funding_need",
        "dscr_min",
        "llcr",
    }
    assert set(schema["$defs"]["governed_metric_id"]["enum"]) == governed_metrics
    assert schema["properties"]["metric_ids"]["maxItems"] == 8
    assert schema["properties"]["metric_ids"]["items"] == {
        "$ref": "#/$defs/governed_metric_id"
    }
    metrics_schema = schema["properties"]["cells"]["items"]["properties"][
        "metrics"
    ]
    assert metrics_schema["minProperties"] == 1
    assert metrics_schema["maxProperties"] == 8
    assert metrics_schema["propertyNames"] == {
        "$ref": "#/$defs/governed_metric_id"
    }
    assert "custom_metric" not in governed_metrics
    decimal_ref = {"$ref": "#/$defs/canonical_decimal"}
    assert metrics_schema["additionalProperties"] == decimal_ref
    assert schema["properties"]["cells"]["items"]["properties"][
        "row_value"
    ] == decimal_ref
    assert schema["properties"]["cells"]["items"]["properties"][
        "column_value"
    ] == decimal_ref
    axis_values_schema = schema["properties"]["axes"]["items"][
        "properties"
    ]["values"]
    assert axis_values_schema["items"] == decimal_ref
    assert axis_values_schema["uniqueItems"] is True
    decimal_pattern = schema["$defs"]["canonical_decimal"]["pattern"]
    for accepted in ("0", "1", "-1", "0.0001", "-0.0001", "100.01"):
        assert re.fullmatch(decimal_pattern, accepted)
    for rejected in (
        "NaN",
        "Infinity",
        "-Infinity",
        "1e3",
        "text",
        "-0",
        "01",
        "1.0",
        "1.",
    ):
        assert re.fullmatch(decimal_pattern, rejected) is None
    assert {"stage", "cause_code"} <= set(
        schema["properties"]["blockers"]["items"]["required"]
    )
    assert "axes" in schema["required"]
    assert schema["properties"]["profile"]["additionalProperties"] is False
    assert "dependency_hashes" in schema["properties"]["profile"]["required"]
    assert len(schema["allOf"]) == 2


def test_2_by_3_grid_and_direct_cell_parity() -> None:
    def mutate(profile_document):
        profile_document["axes"][0]["values"] = ["20", "25.5"]
        profile_document["axes"][1]["values"] = ["0.8", "1", "1.2"]
        profile_document["maximum_cells"] = 6

    prepared = controlled_sensitivity_prepared_run(profile_mutator=mutate)
    result = evaluate_sensitivity(prepared)

    assert [(cell.row_index, cell.column_index) for cell in result.cells] == [
        (row, column) for row in range(2) for column in range(3)
    ]
    for cell in result.cells:
        direct = derive_validated_input(
            prepared.validated_input,
            [
                {
                    "target_ref": "$.working_capital.dso_days",
                    "operation": "replace",
                    "value": "30",
                },
                {
                    "target_ref": _PRICE,
                    "operation": "replace",
                    "value": cell.row_value,
                },
                {
                    "target_ref": _VOLUME,
                    "operation": "multiply",
                    "value": cell.column_value,
                },
            ],
            f"$.test.direct[{cell.row_index}][{cell.column_index}]",
        )
        model = build_financial_model(direct)
        assert cell.derived_input_hash == direct.input_hash
        assert cell.metrics == {
            metric_id: _metric_text(model.metrics[metric_id])
            for metric_id in prepared.profile_document["metric_ids"]
        }


def test_axis_values_must_remain_unique_after_canonicalization() -> None:
    def mutate(profile_document):
        profile_document["axes"][0]["values"] = ["20", "20.0"]
        profile_document["axes"][1]["values"] = ["1", "1.2"]
        profile_document["maximum_cells"] = 4

    with pytest.raises(FinanceContractError) as admission_error:
        controlled_sensitivity_prepared_run(profile_mutator=mutate)

    assert admission_error.value.code == "FIN2_PROFILE_AXIS_VALUES"
    assert admission_error.value.field_ref == "$.axes[0].values"

    axes = copy.deepcopy(controlled_sensitivity_prepared_run().profile_document["axes"])
    axes[0]["values"] = ["20", "20.0"]
    with pytest.raises(FinanceContractError) as execution_error:
        sensitivity_module._canonical_axes(axes)

    assert execution_error.value.code == "FIN2_SENSITIVITY_AXIS_DUPLICATE"
    assert execution_error.value.field_ref == "$.axes[0].values"


def test_baseline_equivalent_cell_and_input_profile_immutability() -> None:
    def mutate(profile_document):
        profile_document["axes"][0]["values"] = ["25.50", "20"]
        profile_document["axes"][1]["values"] = ["1", "1.2"]
        profile_document["fixed_overrides"][0]["value"] = "15"
        profile_document["maximum_cells"] = 4

    prepared = controlled_sensitivity_prepared_run(profile_mutator=mutate)
    input_before = prepared.validated_input.canonical_document
    profile_before = prepared.profile.canonical_document
    result = evaluate_sensitivity(prepared)
    baseline = build_financial_model(prepared.validated_input)

    assert result.axes[0]["values"][0] == "25.5"
    assert result.cells[0].row_value == "25.5"
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
        profile_document["axes"][0]["values"] = list(
            MAXIMUM_PRICE_AXIS_VALUES
        )
        profile_document["axes"][1]["values"] = list(
            MAXIMUM_VOLUME_AXIS_VALUES
        )
        profile_document["maximum_cells"] = 441

    prepared = controlled_sensitivity_prepared_run(profile_mutator=mutate)
    builds = 0
    derivations = 0
    representative = build_financial_model(prepared.validated_input)

    def derived(_validated, overrides, _field_ref):
        nonlocal derivations
        derivations += 1
        row_value = overrides[-2]["value"]
        column_value = overrides[-1]["value"]
        input_hash = canonical_sha256(
            {"row_value": row_value, "column_value": column_value}
        )
        return replace(prepared.validated_input, input_hash=input_hash)

    def counted(validated):
        nonlocal builds
        builds += 1
        return replace(
            representative,
            source_input_hash=validated.input_hash,
        )

    monkeypatch.setattr(sensitivity_module, "derive_validated_input", derived)
    monkeypatch.setattr(sensitivity_module, "build_financial_model", counted)
    result = evaluate_sensitivity(prepared)

    coordinates = {
        (
            cell.row_index,
            cell.column_index,
            cell.row_value,
            cell.column_value,
            cell.derived_input_hash,
        )
        for cell in result.cells
    }
    assert result.status == "dark_ready"
    assert len(result.cells) == 441
    assert len(coordinates) == 441
    assert len({cell.derived_input_hash for cell in result.cells}) == 441
    assert derivations == 441
    assert builds == 441
    assert all(not hasattr(cell, "model") for cell in result.cells)


def test_releases_each_model_before_building_the_next_cell(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = controlled_sensitivity_prepared_run()
    representative = build_financial_model(prepared.validated_input)
    previous_model: weakref.ReferenceType[Any] | None = None
    builds = 0

    class ModelProbe:
        __slots__ = (
            "source_input_hash",
            "status",
            "blockers",
            "metrics",
            "__weakref__",
        )

        def __init__(self, source_input_hash: str) -> None:
            self.source_input_hash = source_input_hash
            self.status = representative.status
            self.blockers = representative.blockers
            self.metrics = representative.metrics

    def one_live_model(validated):
        nonlocal previous_model, builds
        if previous_model is not None:
            assert previous_model() is None
        model = ModelProbe(validated.input_hash)
        previous_model = weakref.ref(model)
        builds += 1
        return model

    monkeypatch.setattr(
        sensitivity_module,
        "build_financial_model",
        one_live_model,
    )
    result = evaluate_sensitivity(prepared)

    assert result.status == "dark_ready"
    assert builds == result.cell_count == 9
    assert previous_model is not None
    assert previous_model() is None


@pytest.mark.parametrize(
    "profile_transform, binding_transform, expected",
    [
        (lambda prepared: replace(prepared.profile, kind="distribution"), lambda binding: binding, "FIN2_SENSITIVITY_PROFILE_KIND"),
        (lambda prepared: replace(prepared.profile, status="draft"), lambda binding: binding, "FIN2_SENSITIVITY_PROFILE_KIND"),
        (lambda prepared: prepared.profile, lambda binding: replace(binding, owner_organization_id="org-other"), "FIN2_SENSITIVITY_BINDING_MISMATCH"),
        (lambda prepared: prepared.profile, lambda binding: replace(binding, registry_snapshot_hash="sha256:" + "0" * 64), "FIN2_SENSITIVITY_BINDING_MISMATCH"),
        (lambda prepared: prepared.profile, lambda binding: replace(binding, approved_manifest_id="manifest-forged"), "FIN2_SENSITIVITY_BINDING_MISMATCH"),
        (lambda prepared: prepared.profile, lambda binding: replace(binding, approved_manifest_hash="sha256:" + "1" * 64), "FIN2_SENSITIVITY_BINDING_MISMATCH"),
        (lambda prepared: prepared.profile, lambda binding: replace(binding, policy_ref="policy-forged"), "FIN2_SENSITIVITY_BINDING_MISMATCH"),
        (lambda prepared: prepared.profile, lambda binding: replace(binding, policy_version="9.9.9"), "FIN2_SENSITIVITY_BINDING_MISMATCH"),
        (lambda prepared: prepared.profile, lambda binding: replace(binding, policy_hash="sha256:" + "2" * 64), "FIN2_SENSITIVITY_BINDING_MISMATCH"),
        (lambda prepared: prepared.profile, lambda binding: replace(binding, currency="USD"), "FIN2_SENSITIVITY_BINDING_MISMATCH"),
        (lambda prepared: prepared.profile, lambda binding: replace(binding, archetype_id="archetype-forged"), "FIN2_SENSITIVITY_BINDING_MISMATCH"),
        (lambda prepared: prepared.profile, lambda binding: replace(binding, archetype_version="9.9.9"), "FIN2_SENSITIVITY_BINDING_MISMATCH"),
        (lambda prepared: prepared.profile, lambda binding: replace(binding, archetype_registry_hash="sha256:" + "3" * 64), "FIN2_SENSITIVITY_BINDING_MISMATCH"),
    ],
)
def test_profile_and_binding_tampering_fail_before_cell_build(
    profile_transform,
    binding_transform,
    expected,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = controlled_sensitivity_prepared_run()
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


def test_model_input_hash_mismatch_fails_before_metric_projection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = controlled_sensitivity_prepared_run()
    original = sensitivity_module.build_financial_model

    def mismatched(validated) -> Any:
        model = original(validated)
        return replace(
            model,
            source_input_hash="sha256:" + "f" * 64,
        )

    monkeypatch.setattr(
        sensitivity_module,
        "build_financial_model",
        mismatched,
    )
    result = evaluate_sensitivity(prepared)

    assert result.status == "not_ready"
    assert result.cells == ()
    assert result.blockers[0]["stage"] == "model_invariant"
    assert (
        result.blockers[0]["cause_code"]
        == "FIN2_MODEL_INPUT_MISMATCH"
    )


def test_tampered_profile_body_and_missing_metric_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = controlled_sensitivity_prepared_run()
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
    assert result.blockers[0]["stage"] == "metric_projection"
    assert (
        result.blockers[0]["cause_code"]
        == "FIN2_SENSITIVITY_METRIC_UNAVAILABLE"
    )


def test_dark_ready_invariant_rejects_partial_duplicate_or_incomplete_cells() -> None:
    ready = evaluate_sensitivity(controlled_sensitivity_prepared_run())
    partial = replace(ready, cells=ready.cells[:-1])
    duplicate = replace(
        ready,
        cells=ready.cells[:-1] + (ready.cells[0],),
    )
    incomplete_metric_cell = replace(
        ready.cells[0],
        _metrics=ready.cells[0]._metrics[:-1],
    )
    incomplete_metrics = replace(
        ready,
        cells=(incomplete_metric_cell,) + ready.cells[1:],
    )

    for invalid in (partial, duplicate, incomplete_metrics):
        with pytest.raises(FinanceContractError) as error:
            sensitivity_module._validate_evaluation_invariants(invalid)
        assert error.value.code == "FIN2_SENSITIVITY_RESULT_INVARIANT"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (Decimal("1E-100"), "0." + "0" * 99 + "1"),
        (Decimal("1E+100"), "1" + "0" * 100),
        (Decimal("1.23000000000000005"), "1.23000000000000005"),
        (Decimal("-0"), "0"),
    ],
)
def test_finite_decimal_boundaries_are_canonical_and_hash_stable(
    value: Decimal,
    expected: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = controlled_sensitivity_prepared_run()
    original = sensitivity_module.build_financial_model
    metric_id = prepared.profile_document["metric_ids"][0]

    def bounded(validated) -> Any:
        model = original(validated)
        metrics = dict(model.metrics)
        metrics[metric_id] = value
        return replace(model, metrics=metrics)

    monkeypatch.setattr(sensitivity_module, "build_financial_model", bounded)
    first = evaluate_sensitivity(prepared)
    second = evaluate_sensitivity(prepared)

    assert first.status == "dark_ready"
    assert first.cells[0].metrics[metric_id] == expected
    assert first.as_dict() == second.as_dict()
    assert first.result_hash == canonical_sha256(
        first.as_dict(include_hash=False)
    )


def test_unavailable_metric_fails_atomically(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = controlled_sensitivity_prepared_run()
    original = sensitivity_module.build_financial_model
    metric_id = prepared.profile_document["metric_ids"][0]

    def unavailable(validated) -> Any:
        model = original(validated)
        metrics = dict(model.metrics)
        metrics[metric_id] = None
        return replace(model, metrics=metrics)

    monkeypatch.setattr(
        sensitivity_module,
        "build_financial_model",
        unavailable,
    )
    result = evaluate_sensitivity(prepared)

    assert result.status == "not_ready"
    assert result.cells == ()
    assert result.blockers[0]["stage"] == "metric_projection"
    assert (
        result.blockers[0]["cause_code"]
        == "FIN2_SENSITIVITY_METRIC_UNAVAILABLE"
    )


def test_non_finite_metric_fails_atomically_with_structured_provenance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = controlled_sensitivity_prepared_run()
    original = sensitivity_module.build_financial_model

    def non_finite(validated) -> Any:
        model = original(validated)
        metrics = dict(model.metrics)
        metrics[prepared.profile_document["metric_ids"][0]] = Decimal("Infinity")
        return replace(model, metrics=metrics)

    monkeypatch.setattr(sensitivity_module, "build_financial_model", non_finite)
    result = evaluate_sensitivity(prepared)

    assert result.status == "not_ready"
    assert result.cells == ()
    assert result.blockers[0]["stage"] == "metric_projection"
    assert result.blockers[0]["cause_code"] == "FIN2_SENSITIVITY_METRIC"


def test_result_hash_includes_engine_versions_and_imports_stay_dark_only() -> None:
    result = evaluate_sensitivity(controlled_sensitivity_prepared_run())
    full_result = result.as_dict()
    hash_preimage = result.as_dict(include_hash=False)
    assert set(full_result) - set(hash_preimage) == {"result_hash"}
    assert set(hash_preimage) == {
        "schema_version",
        "status",
        "execution_scope",
        "snapshot_eligible",
        "organization_id",
        "project_id",
        "run_id",
        "finance_input_hash",
        "currency",
        "archetype_ref",
        "profile",
        "finance_engine_version",
        "sensitivity_engine_version",
        "canonicalization_policy",
        "axis_ids",
        "axes",
        "metric_ids",
        "cell_count",
        "cells",
        "blockers",
    }
    assert hash_preimage["currency"] == "SAR"
    assert hash_preimage["archetype_ref"] == {
        "archetype_id": "arc_retail",
        "version": "1.0.0",
        "registry_hash": "sha256:" + "b" * 64,
    }

    changed_finance = dict(hash_preimage)
    changed_finance["finance_engine_version"] = "tampered"
    changed_sensitivity = dict(hash_preimage)
    changed_sensitivity["sensitivity_engine_version"] = "tampered"
    changed_organization = dict(hash_preimage)
    changed_organization["organization_id"] = "org-forged"
    changed_project = dict(hash_preimage)
    changed_project["project_id"] = "project-forged"
    changed_run = dict(hash_preimage)
    changed_run["run_id"] = "run-forged"
    changed_currency = dict(hash_preimage)
    changed_currency["currency"] = "USD"
    changed_archetype = copy.deepcopy(hash_preimage)
    changed_archetype["archetype_ref"]["archetype_id"] = "arc-forged"

    assert canonical_sha256(changed_finance) != result.result_hash
    assert canonical_sha256(changed_sensitivity) != result.result_hash
    assert canonical_sha256(changed_organization) != result.result_hash
    assert canonical_sha256(changed_project) != result.result_hash
    assert canonical_sha256(changed_run) != result.result_hash
    assert canonical_sha256(changed_currency) != result.result_hash
    assert canonical_sha256(changed_archetype) != result.result_hash
    source = Path(sensitivity_module.__file__).read_text(encoding="utf-8")
    forbidden = ("module_runtime", "snapshot_assembly", "requests", "http", "socket", "provider")
    assert all(token not in source for token in forbidden)
