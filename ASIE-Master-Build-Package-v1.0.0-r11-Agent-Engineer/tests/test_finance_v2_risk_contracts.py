from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schemas" / "finance"
DOC = ROOT / "docs" / (
    "ACR-FIN-003-GOVERNED-SENSITIVITY-AND-SIMULATION-PROFILES-2026-08-10.md"
)
C3B_DOC = ROOT / "docs" / (
    "FINANCE-V2-S2C3B-GOVERNED-RISK-PROFILE-ADMISSION-2026-08-10.md"
)
DISTRIBUTION = SCHEMA_DIR / (
    "finance-simulation-distribution-profile.v1.schema.json"
)
CORRELATION = SCHEMA_DIR / (
    "finance-simulation-correlation-profile.v1.schema.json"
)
POLICY = SCHEMA_DIR / "finance-simulation-policy.v1.schema.json"
SENSITIVITY = SCHEMA_DIR / "finance-sensitivity-profile.v1.schema.json"
INPUT = SCHEMA_DIR / "finance-model-input.v2.schema.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_distribution_profile_is_closed_hashed_calibrated_and_reviewed() -> None:
    document = load(DISTRIBUTION)

    assert document["properties"]["schema_version"]["const"] == (
        "finance-simulation-distribution-profile.v1"
    )
    assert document["additionalProperties"] is False
    assert {
        "content_hash",
        "status",
        "currency",
        "archetype_ref",
        "target_contract_version",
        "variables",
        "review",
        "metadata",
    } <= set(document["required"])

    variable = document["properties"]["variables"]["items"]
    assert variable["additionalProperties"] is False
    assert {
        "target_ref",
        "operation",
        "distribution",
        "bounds",
        "calibration",
    } <= set(variable["required"])
    kinds = set(
        variable["properties"]["distribution"]["properties"]["kind"]["enum"]
    )
    assert kinds == {
        "triangular",
        "uniform",
        "normal_truncated",
        "lognormal_truncated",
        "discrete_empirical",
    }
    assert len(
        variable["properties"]["distribution"]["allOf"]
    ) == len(kinds)


def test_all_risk_profiles_reuse_the_governed_scenario_target_allowlist() -> None:
    input_schema = load(INPUT)
    expected = input_schema["properties"]["scenarios"]["items"]["properties"][
        "overrides"
    ]["items"]["properties"]["target_ref"]["pattern"]

    distribution = load(DISTRIBUTION)
    actual_distribution = distribution["properties"]["variables"]["items"][
        "properties"
    ]["target_ref"]["pattern"]
    sensitivity = load(SENSITIVITY)
    actual_axis = sensitivity["properties"]["axes"]["items"]["properties"][
        "target_ref"
    ]["pattern"]
    actual_fixed = sensitivity["properties"]["fixed_overrides"]["items"][
        "properties"
    ]["target_ref"]["pattern"]

    assert actual_distribution == expected
    assert actual_axis == expected
    assert actual_fixed == expected
    assert "$.organization_id" not in expected
    assert "$.metadata" not in expected


def test_correlation_contract_requires_hash_matrix_and_reject_policy() -> None:
    document = load(CORRELATION)

    assert document["additionalProperties"] is False
    assert {
        "distribution_profile_ref",
        "distribution_profile_hash",
        "variable_ids",
        "matrix",
        "validation_policy",
        "calibration",
        "review",
    } <= set(document["required"])
    matrix = document["properties"]["matrix"]
    assert matrix["maxItems"] == 50
    assert matrix["items"]["maxItems"] == 50
    policy = document["properties"]["validation_policy"]
    assert policy["properties"]["non_psd_behavior"]["const"] == "reject"
    assert "metadata" in document["required"]
    assert set(document["properties"]["method"]["enum"]) == {
        "pearson_gaussian_copula",
        "spearman_gaussian_copula",
    }


def test_simulation_policy_pins_rng_limits_and_fail_closed_convergence() -> None:
    document = load(POLICY)

    rng = document["properties"]["rng"]
    assert rng["properties"]["algorithm"]["const"] == "pcg64_dxsm_v1"
    assert "reference_vector_ref" in rng["required"]
    iterations = document["properties"]["iterations"]["properties"]
    assert iterations["maximum"]["maximum"] == 100000
    convergence = document["properties"]["convergence"]
    assert convergence["properties"]["failure_policy"]["const"] == "not_ready"
    assert "lineage" in document["required"]
    assert "metadata" in document["required"]
    assert {
        "monitored_metrics",
        "quantiles",
        "relative_tolerance",
        "absolute_tolerance",
        "minimum_batches",
        "stable_batches",
    } <= set(convergence["required"])


def test_sensitivity_contract_is_two_dimensional_bounded_and_reviewed() -> None:
    document = load(SENSITIVITY)

    axes = document["properties"]["axes"]
    assert axes["minItems"] == axes["maxItems"] == 2
    assert axes["items"]["properties"]["values"]["maxItems"] == 21
    assert document["properties"]["maximum_cells"]["maximum"] == 441
    assert "content_hash" in document["required"]
    assert "currency" in document["required"]
    assert "review" in document["required"]
    assert "metadata" in document["required"]
    assert "lineage" in axes["items"]["required"]


def test_acr_keeps_engine_and_professional_claims_blocked() -> None:
    text = DOC.read_text(encoding="utf-8")

    for stage in ("C3A", "C3B", "C3C", "C3D", "C3E", "C3F"):
        assert stage in text
    for token in (
        "FIN2_SIMULATION_NOT_READY",
        "ref+content_hash",
        "positive semidefinite",
        "non_psd_behavior=reject",
        "Finance Reviewer/CPA",
        "Quantitative Reviewer",
        "لا محاكاة إنتاجية",
        "لا تغيّر الحكم",
        "ResolvedRiskProfileBinding",
        "registry_snapshot_hash",
        "FIN2_PROFILE_ENGINE_NOT_READY",
    ):
        assert token in text


def test_approved_profiles_require_all_roles_and_no_rejection() -> None:
    for path in (DISTRIBUTION, CORRELATION, POLICY, SENSITIVITY):
        document = load(path)
        gate = document["allOf"][0]
        assert gate["if"]["properties"]["status"]["const"] == "approved"
        approvals = gate["then"]["properties"]["review"]["properties"][
            "approvals"
        ]
        required_roles = gate["then"]["properties"]["review"]["properties"][
            "required_roles"
        ]

        assert approvals["minItems"] == 5
        assert len(approvals["allOf"]) == 5
        assert approvals["not"]["contains"]["properties"]["status"] == {
            "const": "rejected"
        }
        assert len(required_roles["allOf"]) == 5


def test_c3b_admission_evidence_keeps_registry_and_execution_boundaries() -> None:
    text = C3B_DOC.read_text(encoding="utf-8")

    for token in (
        "ResolvedRiskProfileBinding",
        "registry_snapshot_hash",
        "Approved Manifest",
        "execution_ready=False",
        "FIN2_PROFILE_ENGINE_NOT_READY",
        "O(n^3)",
        "cross-tenant",
        "IMPLEMENTED_AWAITING_EXACT_HEAD_CI_AND_REVIEW",
    ):
        assert token in text
