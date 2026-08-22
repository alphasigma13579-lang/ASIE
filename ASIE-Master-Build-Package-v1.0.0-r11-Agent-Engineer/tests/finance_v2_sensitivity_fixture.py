"""Shared governed fixture for C3C tests and CI evidence scripts."""

from __future__ import annotations

import copy
from collections.abc import Callable
from dataclasses import replace
from decimal import Decimal

from backend.finance_v2 import (
    SensitivityExecutionBinding,
    ServerBinding,
    admit_risk_profile,
    monthly_periods,
    prepare_sensitivity_run,
    profile_content_hash,
    validate_finance_input,
)
from backend.finance_v2.risk_profiles import (
    ManifestProfileBinding,
    ResolvedRiskProfileBinding,
)

_PRICE = "$.revenue_streams[rev-primary].price_series[*].value"
_VOLUME = "$.revenue_streams[rev-primary].volume_series[*].value"

MAXIMUM_METRIC_IDS = (
    "npv_unlevered",
    "irr_unlevered",
    "mirr_unlevered",
    "payback_months",
    "break_even",
    "funding_need",
    "dscr_min",
    "llcr",
)
MAXIMUM_PRICE_AXIS_VALUES = tuple(str(20 + index) for index in range(21))
MAXIMUM_VOLUME_AXIS_VALUES = tuple(
    format(Decimal("0.80") + Decimal(index) * Decimal("0.02"), "f")
    for index in range(21)
)

_POLICY_HASH = "sha256:" + "c" * 64
_REGISTRY_HASH = "sha256:" + "d" * 64
_MANIFEST_HASH = "sha256:" + "e" * 64
_ROLES = (
    "finance_reviewer",
    "sector_expert",
    "quantitative_reviewer",
    "qa",
    "security",
)


def _finance_lineage() -> dict:
    return {"assumption_refs": ["asm-1"], "evidence_refs": ["ev-1"]}


def _profile_lineage() -> dict:
    return {
        "assumption_refs": ["assumption:sector-demand"],
        "evidence_refs": ["evidence:calibration-source"],
    }


def _finance_binding() -> ServerBinding:
    return ServerBinding(
        organization_id="org-1",
        project_id="project-1",
        run_id="run-1",
        approved_manifest_id="manifest-1",
        approved_manifest_hash="sha256:" + "a" * 64,
        policy_ref="finance-policy-v2-dark",
    )


def _valid_document() -> dict:
    periods = monthly_periods("2026-01", 12)
    lineage = _finance_lineage
    return {
        "schema_version": "finance-model-input.v2",
        "document_id": "fmi_example01",
        "organization_id": "org-1",
        "project_id": "project-1",
        "run_id": "run-1",
        "currency": "SAR",
        "forecast": {
            "start_period": "2026-01",
            "monthly_periods": 12,
            "construction_periods": 0,
        },
        "archetype_ref": {
            "archetype_id": "arc_retail",
            "version": "1.0.0",
            "registry_hash": "sha256:" + "b" * 64,
        },
        "rounding_policy": {
            "money_scale": 2,
            "ratio_scale": 6,
            "mode": "ROUND_HALF_EVEN",
        },
        "revenue_streams": [
            {
                "stream_id": "rev-primary",
                "model_kind": "product_unit",
                "unit": "unit",
                "volume_series": [
                    {"period": period, "value": "100"} for period in periods
                ],
                "price_series": [
                    {"period": period, "value": "25.50"} for period in periods
                ],
                "variable_cost_series": [
                    {"period": period, "value": "10"} for period in periods
                ],
                "lineage": lineage(),
            }
        ],
        "operating_costs": [],
        "capex_assets": [
            {
                "asset_id": "asset-sensitivity-base",
                "acquisition_period": periods[0],
                "cost": "100000",
                "useful_life_months": 240,
                "depreciation_method": "straight_line",
                "residual_value": "0",
                "lineage": lineage(),
            }
        ],
        "working_capital": {
            "mode": "days",
            "dso_days": "15",
            "dio_days": "20",
            "dpo_days": "10",
            "lineage": lineage(),
        },
        "financing": {
            "equity_contributions": [
                {"period": periods[0], "amount": "100000", "lineage": lineage()}
            ],
            "debt_tranches": [
                {
                    "tranche_id": "debt-sensitivity-base",
                    "drawdowns": [
                        {"period": periods[0], "amount": "1200"}
                    ],
                    "annual_rate": "0",
                    "tenor_months": 12,
                    "principal_grace_months": 0,
                    "interest_grace_policy": "paid",
                    "repayment_profile": "equal_principal",
                    "fee_treatment": "expense_upfront",
                    "fees": [],
                    "lineage": lineage(),
                }
            ],
        },
        "fiscal_policy": {
            "policy_id": "fiscal-none",
            "effective_from": "2026-01-01",
            "modules": [],
            "lineage": lineage(),
        },
        "valuation_policy": {
            "discount_rate_annual": "0.12",
            "finance_rate_annual": "0.08",
            "reinvestment_rate_annual": "0.10",
            "lineage": lineage(),
        },
        "scenarios": [
            {"scenario_id": "scn_baseline", "kind": "baseline", "overrides": []}
        ],
        "metadata": {
            "approved_manifest_id": "manifest-1",
            "approved_manifest_hash": "sha256:" + "a" * 64,
            "policy_ref": "finance-policy-v2-dark",
        },
    }


def _review() -> dict:
    return {
        "required_roles": list(_ROLES),
        "approvals": [
            {
                "role": role,
                "reviewer_ref": f"reviewer:{role}",
                "status": "approved",
                "reviewed_at": "2026-08-01T10:00:00+03:00",
                "evidence_ref": f"evidence:{role}",
            }
            for role in _ROLES
        ],
    }


def _sensitivity_profile() -> dict:
    document = {
        "schema_version": "finance-sensitivity-profile.v1",
        "profile_id": "fsn_default",
        "version": "1.0.0",
        "content_hash": "",
        "status": "approved",
        "currency": "SAR",
        "archetype_ref": {
            "archetype_id": "retail_small",
            "version": "1.0.0",
            "registry_hash": "sha256:" + "b" * 64,
        },
        "axes": [
            {
                "axis_id": "axis_price",
                "target_ref": _PRICE,
                "operation": "replace",
                "values": ["80", "100", "120"],
                "lineage": _profile_lineage(),
            },
            {
                "axis_id": "axis_volume",
                "target_ref": _VOLUME,
                "operation": "multiply",
                "values": ["0.8", "1", "1.2"],
                "lineage": _profile_lineage(),
            },
        ],
        "fixed_overrides": [
            {
                "target_ref": "$.working_capital.dso_days",
                "operation": "replace",
                "value": "30",
                "lineage": _profile_lineage(),
            }
        ],
        "metric_ids": ["npv_unlevered", "irr_unlevered"],
        "maximum_cells": 9,
        "review": _review(),
        "metadata": {
            "owner_ref": "finance-governance",
            "effective_from": "2026-08-01",
            "created_at": "2026-07-31T12:00:00+03:00",
        },
    }
    document["content_hash"] = profile_content_hash(document)
    return document


def _resolved_binding(
    profile_document: dict,
    document: dict,
) -> ResolvedRiskProfileBinding:
    profile_manifest = ManifestProfileBinding(
        schema_version=profile_document["schema_version"],
        profile_id=profile_document["profile_id"],
        version=profile_document["version"],
        content_hash=profile_document["content_hash"],
    )
    policy_manifest = ManifestProfileBinding(
        schema_version="finance-simulation-policy.v1",
        profile_id="fsp_default",
        version="1.0.0",
        content_hash=_POLICY_HASH,
    )
    archetype_ref = document["archetype_ref"]
    return ResolvedRiskProfileBinding(
        expected_schema_version=profile_document["schema_version"],
        expected_profile_id=profile_document["profile_id"],
        expected_version=profile_document["version"],
        expected_content_hash=profile_document["content_hash"],
        registry_snapshot_hash=_REGISTRY_HASH,
        organization_id=document["organization_id"],
        scope_kind="organization",
        owner_organization_id=document["organization_id"],
        approved_manifest_id="manifest:approved",
        approved_manifest_hash=_MANIFEST_HASH,
        policy_ref="fsp_default",
        policy_version="1.0.0",
        policy_hash=_POLICY_HASH,
        as_of_date="2026-08-10",
        manifest_profiles=(profile_manifest, policy_manifest),
        authorized_reviewers=tuple(
            (role, f"reviewer:{role}") for role in _ROLES
        ),
        evidence_refs=tuple(f"evidence:{role}" for role in _ROLES),
        distribution_variable_ids=(),
        dependency_hashes=(
            (
                (
                    f"archetype:{archetype_ref['archetype_id']}@"
                    f"{archetype_ref['version']}"
                ),
                archetype_ref["registry_hash"],
            ),
        ),
        authoritative=True,
        allow_global=False,
    )


def controlled_sensitivity_prepared_run(
    *,
    profile_mutator: Callable[[dict], None] | None = None,
    input_mutator: Callable[[dict], None] | None = None,
):
    """Build the server-bound deterministic C3C fixture used by tests and CI."""
    document = _valid_document()
    if input_mutator is not None:
        input_mutator(document)

    profile_document = _sensitivity_profile()
    profile_document["archetype_ref"] = copy.deepcopy(
        document["archetype_ref"]
    )
    profile_document["axes"][0]["target_ref"] = _PRICE
    profile_document["axes"][1]["target_ref"] = _VOLUME
    if profile_mutator is not None:
        profile_mutator(profile_document)
    profile_document["content_hash"] = profile_content_hash(profile_document)

    risk_binding = _resolved_binding(profile_document, document)
    document["metadata"] = {
        "approved_manifest_id": risk_binding.approved_manifest_id,
        "approved_manifest_hash": risk_binding.approved_manifest_hash,
        "policy_ref": risk_binding.policy_ref,
    }
    validated = validate_finance_input(
        document,
        binding=replace(
            _finance_binding(),
            approved_manifest_id=risk_binding.approved_manifest_id,
            approved_manifest_hash=risk_binding.approved_manifest_hash,
            policy_ref=risk_binding.policy_ref,
        ),
    )
    profile = admit_risk_profile(profile_document, binding=risk_binding)
    execution_binding = SensitivityExecutionBinding(
        risk_profile_binding=risk_binding,
        authoritative_admission=True,
        organization_id=validated.organization_id,
        project_id=validated.project_id,
        run_id=validated.run_id,
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
    return prepare_sensitivity_run(
        validated,
        profile,
        binding=execution_binding,
    )
