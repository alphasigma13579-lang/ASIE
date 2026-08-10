from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from typing import Callable

import pytest

from backend.finance_v2.contracts import FinanceContractError
from backend.finance_v2.risk_profiles import (
    ManifestProfileBinding,
    ResolvedRiskProfileBinding,
    admit_risk_profile,
    profile_content_hash,
    validate_risk_profile,
)


ROLES = (
    "finance_reviewer",
    "sector_expert",
    "quantitative_reviewer",
    "qa",
    "security",
)
REVIEWERS = tuple(
    (role, f"reviewer:{role}") for role in ROLES
)
EVIDENCE_REFS = tuple(f"evidence:{role}" for role in ROLES)
H_ARCHETYPE = "sha256:" + "a" * 64
H_DISTRIBUTION = "sha256:" + "b" * 64
H_POLICY = "sha256:" + "c" * 64
H_VECTOR = "sha256:" + "1" * 64
H_REGISTRY = "sha256:" + "d" * 64
H_MANIFEST = "sha256:" + "e" * 64


def _lineage() -> dict:
    return {
        "assumption_refs": ["assumption:sector-demand"],
        "evidence_refs": ["evidence:calibration-source"],
    }


def _calibration() -> dict:
    return {
        "method": "historical_empirical",
        "sample_size": 36,
        "period_from": "2023-01-01",
        "period_to": "2025-12-31",
        "geography": "Saudi Arabia",
        "freshness_as_of": "2026-07-31",
        "data_source_refs": ["public-data:source-1"],
        "lineage": _lineage(),
    }


def _review(*, rejected_role: str | None = None) -> dict:
    approvals = []
    for role in ROLES:
        approvals.append(
            {
                "role": role,
                "reviewer_ref": f"reviewer:{role}",
                "status": "rejected" if role == rejected_role else "approved",
                "reviewed_at": "2026-08-01T10:00:00+03:00",
                "evidence_ref": f"evidence:{role}",
            }
        )
    return {
        "required_roles": list(ROLES),
        "approvals": approvals,
    }


def _metadata() -> dict:
    return {
        "owner_ref": "finance-governance",
        "effective_from": "2026-08-01",
        "created_at": "2026-07-31T12:00:00+03:00",
    }


def _archetype() -> dict:
    return {
        "archetype_id": "retail_small",
        "version": "1.0.0",
        "registry_hash": H_ARCHETYPE,
    }


def distribution_profile() -> dict:
    return _finalize(
        {
            "schema_version": "finance-simulation-distribution-profile.v1",
            "profile_id": "fdp_default",
            "version": "1.0.0",
            "content_hash": "",
            "status": "approved",
            "currency": "SAR",
            "archetype_ref": _archetype(),
            "target_contract_version": "finance-model-input.v2",
            "variables": [
                {
                    "variable_id": "var_price",
                    "target_ref": (
                        "$.revenue_streams[sales].price_series[*].value"
                    ),
                    "operation": "replace",
                    "unit": "money",
                    "distribution": {
                        "kind": "triangular",
                        "parameters": {
                            "minimum": "80",
                            "mode": "100",
                            "maximum": "120",
                        },
                    },
                    "bounds": {"minimum": "80", "maximum": "120"},
                    "calibration": _calibration(),
                }
            ],
            "review": _review(),
            "metadata": _metadata(),
        }
    )


def correlation_profile() -> dict:
    return _finalize(
        {
            "schema_version": "finance-simulation-correlation-profile.v1",
            "profile_id": "fcp_default",
            "version": "1.0.0",
            "content_hash": "",
            "status": "approved",
            "distribution_profile_ref": "distribution:fdp_default@1.0.0",
            "distribution_profile_hash": H_DISTRIBUTION,
            "method": "pearson_gaussian_copula",
            "variable_ids": ["var_price", "var_volume"],
            "matrix": [["1", "0.25"], ["0.25", "1"]],
            "validation_policy": {
                "symmetry_tolerance": "0.000001",
                "diagonal_tolerance": "0.000001",
                "psd_tolerance": "0.000001",
                "non_psd_behavior": "reject",
            },
            "calibration": _calibration(),
            "review": _review(),
            "metadata": _metadata(),
        }
    )


def simulation_policy() -> dict:
    return _finalize(
        {
            "schema_version": "finance-simulation-policy.v1",
            "policy_id": "fsp_default",
            "version": "1.0.0",
            "content_hash": "",
            "status": "approved",
            "rng": {
                "algorithm": "pcg64_dxsm_v1",
                "stream_derivation": "seed_scenario_variable_v1",
                "reference_vector_ref": "test-vector:pcg64-dxsm-v1",
                "reference_vector_hash": H_VECTOR,
            },
            "iterations": {
                "minimum": 1000,
                "maximum": 10000,
                "batch_size": 500,
            },
            "convergence": {
                "monitored_metrics": ["npv_unlevered"],
                "quantiles": ["0.10", "0.50", "0.90"],
                "relative_tolerance": "0.01",
                "absolute_tolerance": "0",
                "minimum_batches": 2,
                "stable_batches": 2,
                "failure_policy": "not_ready",
            },
            "outputs": {
                "metric_ids": ["npv_unlevered", "irr_unlevered"],
                "quantiles": ["0.05", "0.50", "0.95"],
                "probability_thresholds": [
                    {
                        "metric_id": "npv_unlevered",
                        "operator": "lt",
                        "value": "0",
                    }
                ],
            },
            "review": _review(),
            "metadata": _metadata(),
            "lineage": _lineage(),
        }
    )


def sensitivity_profile() -> dict:
    return _finalize(
        {
            "schema_version": "finance-sensitivity-profile.v1",
            "profile_id": "fsn_default",
            "version": "1.0.0",
            "content_hash": "",
            "status": "approved",
            "currency": "SAR",
            "archetype_ref": _archetype(),
            "axes": [
                {
                    "axis_id": "axis_price",
                    "target_ref": (
                        "$.revenue_streams[sales].price_series[*].value"
                    ),
                    "operation": "replace",
                    "values": ["80", "100", "120"],
                    "lineage": _lineage(),
                },
                {
                    "axis_id": "axis_volume",
                    "target_ref": (
                        "$.revenue_streams[sales].volume_series[*].value"
                    ),
                    "operation": "multiply",
                    "values": ["0.8", "1", "1.2"],
                    "lineage": _lineage(),
                },
            ],
            "fixed_overrides": [
                {
                    "target_ref": "$.working_capital.dso_days",
                    "operation": "replace",
                    "value": "30",
                    "lineage": _lineage(),
                }
            ],
            "metric_ids": ["npv_unlevered", "irr_unlevered"],
            "maximum_cells": 9,
            "review": _review(),
            "metadata": _metadata(),
        }
    )


def _identifier(document: dict) -> str:
    return document.get("policy_id", document.get("profile_id", ""))


def _finalize(document: dict) -> dict:
    document["content_hash"] = profile_content_hash(document)
    return document


def _binding(
    document: dict,
    *,
    authoritative: bool = True,
    scope_kind: str = "organization",
    owner_organization_id: str | None = "org-1",
    organization_id: str = "org-1",
    allow_global: bool = False,
) -> ResolvedRiskProfileBinding:
    identifier = _identifier(document)
    current = ManifestProfileBinding(
        schema_version=document["schema_version"],
        profile_id=identifier,
        version=document["version"],
        content_hash=document["content_hash"],
    )
    if document["schema_version"] == "finance-simulation-policy.v1":
        policy_ref = identifier
        policy_version = document["version"]
        policy_hash = document["content_hash"]
        manifest_profiles = (current,)
    else:
        policy_ref = "fsp_default"
        policy_version = "1.0.0"
        policy_hash = H_POLICY
        policy = ManifestProfileBinding(
            schema_version="finance-simulation-policy.v1",
            profile_id=policy_ref,
            version=policy_version,
            content_hash=policy_hash,
        )
        manifest_profiles = (current, policy)
    dependencies: tuple[tuple[str, str], ...]
    if document["schema_version"] in {
        "finance-simulation-distribution-profile.v1",
        "finance-sensitivity-profile.v1",
    }:
        dependencies = (("archetype:retail_small@1.0.0", H_ARCHETYPE),)
    elif document["schema_version"] == (
        "finance-simulation-correlation-profile.v1"
    ):
        dependencies = (
            ("distribution:fdp_default@1.0.0", H_DISTRIBUTION),
        )
    elif document["schema_version"] == "finance-simulation-policy.v1":
        dependencies = (("test-vector:pcg64-dxsm-v1", H_VECTOR),)
    else:
        dependencies = ()
    distribution_variable_ids = (
        tuple(document["variable_ids"])
        if document["schema_version"]
        == "finance-simulation-correlation-profile.v1"
        else ()
    )
    return ResolvedRiskProfileBinding(
        expected_schema_version=document["schema_version"],
        expected_profile_id=identifier,
        expected_version=document["version"],
        expected_content_hash=document["content_hash"],
        registry_snapshot_hash=H_REGISTRY,
        organization_id=organization_id,
        scope_kind=scope_kind,
        owner_organization_id=owner_organization_id,
        approved_manifest_id="manifest:approved",
        approved_manifest_hash=H_MANIFEST,
        policy_ref=policy_ref,
        policy_version=policy_version,
        policy_hash=policy_hash,
        as_of_date="2026-08-10",
        manifest_profiles=manifest_profiles,
        authorized_reviewers=REVIEWERS,
        evidence_refs=EVIDENCE_REFS,
        distribution_variable_ids=distribution_variable_ids,
        dependency_hashes=dependencies,
        authoritative=authoritative,
        allow_global=allow_global,
    )


def _admit(document: dict):
    return admit_risk_profile(document, binding=_binding(document))


def _assert_rejected(
    document: dict,
    code: str,
    *,
    binding_transform: Callable[
        [ResolvedRiskProfileBinding], ResolvedRiskProfileBinding
    ]
    | None = None,
) -> FinanceContractError:
    try:
        _finalize(document)
    except FinanceContractError as error:
        assert error.code == code
        return error
    binding = _binding(document)
    if binding_transform is not None:
        binding = binding_transform(binding)
    with pytest.raises(FinanceContractError) as error:
        admit_risk_profile(document, binding=binding)
    assert error.value.code == code
    return error.value


@pytest.mark.parametrize(
    "factory",
    [
        distribution_profile,
        correlation_profile,
        simulation_policy,
        sensitivity_profile,
    ],
)
def test_all_four_authoritative_profiles_admit_but_never_execute(
    factory: Callable[[], dict],
) -> None:
    document = factory()
    result = _admit(document)

    assert result.profile_id == _identifier(document)
    assert result.content_hash == document["content_hash"]
    assert result.registry_snapshot_hash == H_REGISTRY
    assert result.approved_manifest_id == "manifest:approved"
    assert result.policy_version == "1.0.0"
    assert result.policy_hash in {H_POLICY, document["content_hash"]}
    assert result.scope_kind == "organization"
    assert result.execution_ready is False
    assert result.thaw() == document

    with pytest.raises(FinanceContractError) as error:
        validate_risk_profile(
            document,
            binding=replace(
                _binding(document),
                require_execution_ready=True,
            ),
        )
    assert error.value.code == "FIN2_PROFILE_ENGINE_NOT_READY"


def test_registry_admission_requires_authoritative_binding() -> None:
    document = distribution_profile()

    with pytest.raises(FinanceContractError) as error:
        admit_risk_profile(
            document,
            binding=_binding(document, authoritative=False),
        )

    assert error.value.code == "FIN2_PROFILE_ADMISSION_MODE"


def test_canonical_hash_is_order_independent_and_excludes_only_hash() -> None:
    document = distribution_profile()
    reordered = dict(reversed(list(document.items())))

    assert profile_content_hash(reordered) == document["content_hash"]

    changed = deepcopy(document)
    changed["metadata"]["owner_ref"] = "different-owner"
    assert profile_content_hash(changed) != document["content_hash"]


@pytest.mark.parametrize(
    ("mutator", "code"),
    [
        (
            lambda document: document.__setitem__(
                "profile_id",
                "fdp_substituted",
            ),
            "FIN2_PROFILE_BINDING_MISMATCH",
        ),
        (
            lambda document: document.__setitem__(
                "content_hash",
                "sha256:" + "0" * 64,
            ),
            "FIN2_PROFILE_HASH_MISMATCH",
        ),
    ],
)
def test_ref_and_hash_substitution_fail_closed(
    mutator: Callable[[dict], None],
    code: str,
) -> None:
    document = distribution_profile()
    binding = _binding(document)
    mutator(document)
    if code == "FIN2_PROFILE_BINDING_MISMATCH":
        document["content_hash"] = profile_content_hash(document)

    with pytest.raises(FinanceContractError) as error:
        admit_risk_profile(document, binding=binding)

    assert error.value.code == code


def test_manifest_and_selected_policy_must_pin_exact_profile() -> None:
    document = distribution_profile()
    binding = _binding(document)

    with pytest.raises(FinanceContractError) as missing_profile:
        admit_risk_profile(
            document,
            binding=replace(
                binding,
                manifest_profiles=binding.manifest_profiles[1:],
            ),
        )
    assert missing_profile.value.code == "FIN2_PROFILE_MANIFEST_UNBOUND"

    with pytest.raises(FinanceContractError) as missing_policy:
        admit_risk_profile(
            document,
            binding=replace(binding, policy_ref="fsp_other"),
        )
    assert missing_policy.value.code == "FIN2_PROFILE_POLICY_UNBOUND"


def test_tenant_scope_is_server_bound_and_global_requires_permission() -> None:
    document = distribution_profile()

    with pytest.raises(FinanceContractError) as tenant_error:
        admit_risk_profile(
            document,
            binding=_binding(
                document,
                owner_organization_id="org-2",
            ),
        )
    assert tenant_error.value.code == "FIN2_PROFILE_TENANT_MISMATCH"

    global_binding = _binding(
        document,
        scope_kind="global",
        owner_organization_id=None,
        allow_global=True,
    )
    assert admit_risk_profile(
        document,
        binding=global_binding,
    ).scope_kind == "global"

    with pytest.raises(FinanceContractError) as global_error:
        admit_risk_profile(
            document,
            binding=replace(global_binding, allow_global=False),
        )
    assert global_error.value.code == "FIN2_PROFILE_SCOPE_DENIED"


@pytest.mark.parametrize(
    ("mutation", "code"),
    [
        (
            lambda document: document["review"]["approvals"][0].__setitem__(
                "reviewer_ref",
                "reviewer:forged",
            ),
            "FIN2_PROFILE_REVIEWER_UNBOUND",
        ),
        (
            lambda document: document["review"]["approvals"][0].__setitem__(
                "evidence_ref",
                "evidence:forged",
            ),
            "FIN2_PROFILE_EVIDENCE_UNBOUND",
        ),
        (
            lambda document: document["review"]["approvals"][0].__setitem__(
                "reviewed_at",
                "2026-08-11T10:00:00+03:00",
            ),
            "FIN2_PROFILE_REVIEW_FUTURE",
        ),
        (
            lambda document: document["review"]["approvals"].pop(),
            "FIN2_PROFILE_APPROVAL_INCOMPLETE",
        ),
        (
            lambda document: document.__setitem__(
                "review",
                _review(rejected_role="security"),
            ),
            "FIN2_PROFILE_APPROVAL_INCOMPLETE",
        ),
    ],
)
def test_governed_review_identity_evidence_and_time_fail_closed(
    mutation: Callable[[dict], None],
    code: str,
) -> None:
    document = distribution_profile()
    mutation(document)
    _assert_rejected(document, code)


def test_distribution_semantics_reject_overlap_probability_and_sigma() -> None:
    overlap = distribution_profile()
    second = deepcopy(overlap["variables"][0])
    second["variable_id"] = "var_price_month"
    second["target_ref"] = (
        "$.revenue_streams[sales].price_series[2026-01].value"
    )
    overlap["variables"].append(second)
    _assert_rejected(overlap, "FIN2_PROFILE_TARGET_OVERLAP")

    probability = distribution_profile()
    variable = probability["variables"][0]
    variable["distribution"] = {
        "kind": "discrete_empirical",
        "parameters": {
            "values": ["80", "120"],
            "probabilities": ["0.4", "0.5"],
        },
    }
    _assert_rejected(probability, "FIN2_PROFILE_PROBABILITY_SUM")

    sigma = distribution_profile()
    variable = sigma["variables"][0]
    variable["distribution"] = {
        "kind": "normal_truncated",
        "parameters": {
            "mean": "100",
            "stddev": "0",
            "minimum": "80",
            "maximum": "120",
        },
    }
    _assert_rejected(sigma, "FIN2_PROFILE_DISTRIBUTION_PARAMETERS")


def test_calibration_cannot_be_future_or_historical_with_zero_sample() -> None:
    future = distribution_profile()
    future["variables"][0]["calibration"]["freshness_as_of"] = "2026-08-11"
    _assert_rejected(future, "FIN2_PROFILE_CALIBRATION_PERIOD")

    empty = distribution_profile()
    empty["variables"][0]["calibration"]["sample_size"] = 0
    _assert_rejected(empty, "FIN2_PROFILE_CALIBRATION_SAMPLE")


@pytest.mark.parametrize(
    ("mutation", "code"),
    [
        (
            lambda document: document["metadata"].__setitem__(
                "effective_from", "20260801"
            ),
            "FIN2_PROFILE_DATE",
        ),
        (
            lambda document: document["variables"][0]["calibration"].__setitem__(
                "period_from", "2026-W31-5"
            ),
            "FIN2_PROFILE_DATE",
        ),
        (
            lambda document: document["review"]["approvals"][0].__setitem__(
                "reviewed_at", "2026-08-01 10:00:00+03:00"
            ),
            "FIN2_PROFILE_DATETIME",
        ),
    ],
)
def test_authoritative_dates_use_canonical_contract_formats(
    mutation: Callable[[dict], None],
    code: str,
) -> None:
    document = distribution_profile()
    mutation(document)
    _assert_rejected(document, code)


@pytest.mark.parametrize(
    "rho",
    ["-0.5", "0", "0.25", "0.99"],
)
def test_psd_validator_accepts_governed_equicorrelation_boundary(
    rho: str,
) -> None:
    document = correlation_profile()
    document["variable_ids"] = ["var_a", "var_b", "var_c"]
    document["matrix"] = [
        ["1", rho, rho],
        [rho, "1", rho],
        [rho, rho, "1"],
    ]

    assert _admit(_finalize(document)).kind == "correlation"


def test_psd_validator_preserves_small_positive_pivots() -> None:
    document = correlation_profile()
    document["variable_ids"] = ["var_a", "var_b", "var_c"]
    document["matrix"] = [
        ["1", "0.9999995", "0"],
        ["0.9999995", "1", "0.0005"],
        ["0", "0.0005", "1"],
    ]

    assert _admit(_finalize(document)).kind == "correlation"


@pytest.mark.parametrize(
    ("matrix", "code"),
    [
        (
            [
                ["1", "0.9", "0.9"],
                ["0.9", "1", "-0.9"],
                ["0.9", "-0.9", "1"],
            ],
            "FIN2_PROFILE_CORRELATION_NOT_PSD",
        ),
        (
            [["1", "0.2"], ["0.3", "1"]],
            "FIN2_PROFILE_CORRELATION_SYMMETRY",
        ),
        (
            [["1", "1.1"], ["1.1", "1"]],
            "FIN2_PROFILE_CORRELATION_RANGE",
        ),
    ],
)
def test_correlation_matrix_failures_are_explicit(
    matrix: list[list[str]],
    code: str,
) -> None:
    document = correlation_profile()
    if len(matrix) == 3:
        document["variable_ids"] = ["var_a", "var_b", "var_c"]
    document["matrix"] = matrix
    _assert_rejected(document, code)


def test_correlation_dependency_hash_is_bound_to_registry_resolution() -> None:
    document = correlation_profile()
    document["distribution_profile_hash"] = "sha256:" + "f" * 64

    _assert_rejected(document, "FIN2_PROFILE_DEPENDENCY_UNBOUND")


def test_correlation_variables_match_resolved_distribution_exactly() -> None:
    document = correlation_profile()

    _assert_rejected(
        document,
        "FIN2_PROFILE_DEPENDENCY_VARIABLES",
        binding_transform=lambda binding: replace(
            binding,
            distribution_variable_ids=("var_price", "var_other"),
        ),
    )


@pytest.mark.parametrize(
    ("mutation", "code"),
    [
        (
            lambda document: document["iterations"].update(
                {"minimum": 2000, "maximum": 1000}
            ),
            "FIN2_PROFILE_ITERATION_POLICY",
        ),
        (
            lambda document: document["convergence"].update(
                {"minimum_batches": 20, "stable_batches": 20}
            ),
            "FIN2_PROFILE_CONVERGENCE_POLICY",
        ),
        (
            lambda document: document["convergence"].update(
                {"relative_tolerance": "0", "absolute_tolerance": "0"}
            ),
            "FIN2_PROFILE_CONVERGENCE_POLICY",
        ),
        (
            lambda document: document["outputs"].update(
                {"metric_ids": ["irr_unlevered"]}
            ),
            "FIN2_PROFILE_CONVERGENCE_POLICY",
        ),
        (
            lambda document: document["outputs"].update(
                {"metric_ids": ["break_even"]}
            ),
            "FIN2_PROFILE_METRIC",
        ),
    ],
)
def test_simulation_policy_semantic_invariants(
    mutation: Callable[[dict], None],
    code: str,
) -> None:
    document = simulation_policy()
    mutation(document)
    _assert_rejected(document, code)


def test_rng_reference_vector_requires_trusted_content_hash() -> None:
    missing = simulation_policy()
    _assert_rejected(
        missing,
        "FIN2_PROFILE_DEPENDENCY_UNBOUND",
        binding_transform=lambda binding: replace(
            binding,
            dependency_hashes=(),
        ),
    )

    mismatched = simulation_policy()
    mismatched["rng"]["reference_vector_hash"] = "sha256:" + "f" * 64
    _assert_rejected(mismatched, "FIN2_PROFILE_DEPENDENCY_UNBOUND")


def test_empty_lineage_never_admits_an_authoritative_value() -> None:
    document = sensitivity_profile()
    document["axes"][0]["lineage"] = {
        "assumption_refs": [],
        "evidence_refs": [],
    }

    _assert_rejected(document, "FIN2_PROFILE_LINEAGE_EMPTY")


def test_sensitivity_multiply_operations_reject_negative_values() -> None:
    axis = sensitivity_profile()
    axis["axes"][1]["values"] = ["-0.8", "1", "1.2"]
    _assert_rejected(axis, "FIN2_SCENARIO_MULTIPLIER_NEGATIVE")

    fixed = sensitivity_profile()
    fixed["fixed_overrides"][0].update(
        {"operation": "multiply", "value": "-0.1"}
    )
    _assert_rejected(fixed, "FIN2_SCENARIO_MULTIPLIER_NEGATIVE")


def test_sensitivity_axes_targets_and_cell_budget_are_governed() -> None:
    duplicate_axis = sensitivity_profile()
    duplicate_axis["axes"][1]["axis_id"] = "axis_price"
    _assert_rejected(duplicate_axis, "FIN2_PROFILE_AXIS_DUPLICATE")

    overlap = sensitivity_profile()
    overlap["axes"][1]["target_ref"] = (
        "$.revenue_streams[sales].price_series[2026-01].value"
    )
    _assert_rejected(overlap, "FIN2_PROFILE_TARGET_OVERLAP")

    cells = sensitivity_profile()
    cells["axes"][0]["values"] = [str(index) for index in range(1, 22)]
    cells["axes"][1]["values"] = [str(index) for index in range(21, 42)]
    cells["maximum_cells"] = 440
    _assert_rejected(cells, "FIN2_PROFILE_SENSITIVITY_CELLS")


@pytest.mark.parametrize(
    ("mutation", "code"),
    [
        (
            lambda document: document["variables"][0]["bounds"].__setitem__(
                "minimum",
                80.0,
            ),
            "FIN2_PROFILE_NUMBER_TYPE",
        ),
        (
            lambda document: document["review"].__setitem__(
                "required_roles",
                [{}, "security"],
            ),
            "FIN2_PROFILE_TEXT",
        ),
    ],
)
def test_untrusted_types_fail_as_contract_errors_not_python_errors(
    mutation: Callable[[dict], None],
    code: str,
) -> None:
    document = distribution_profile()
    mutation(document)
    _assert_rejected(document, code)


def test_resource_depth_is_bounded_before_hashing() -> None:
    value: object = "leaf"
    for _ in range(18):
        value = {"nested": value}

    with pytest.raises(FinanceContractError) as error:
        profile_content_hash({"profile": value})

    assert error.value.code == "FIN2_PROFILE_RESOURCE_LIMIT"
