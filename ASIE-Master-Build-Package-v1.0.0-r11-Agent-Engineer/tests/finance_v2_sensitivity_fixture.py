"""Shared governed fixture for C3C tests and CI evidence scripts."""

from __future__ import annotations

import copy
from dataclasses import replace
from typing import Callable

from backend.finance_v2 import (
    SensitivityExecutionBinding,
    admit_risk_profile,
    prepare_sensitivity_run,
    profile_content_hash,
    validate_finance_input,
)
from backend.finance_v2.risk_profiles import (
    ManifestProfileBinding,
    ResolvedRiskProfileBinding,
)
from tests.test_finance_v2_contracts import binding as finance_binding
from tests.test_finance_v2_contracts import valid_document
from tests.test_finance_v2_risk_profile_admission import sensitivity_profile


_PRICE = "$.revenue_streams[rev-primary].price_series[*].value"
_VOLUME = "$.revenue_streams[rev-primary].volume_series[*].value"
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
                f"archetype:{archetype_ref['archetype_id']}@"
                f"{archetype_ref['version']}",
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
    document = valid_document()
    if input_mutator is not None:
        input_mutator(document)

    profile_document = sensitivity_profile()
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
            finance_binding(),
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
