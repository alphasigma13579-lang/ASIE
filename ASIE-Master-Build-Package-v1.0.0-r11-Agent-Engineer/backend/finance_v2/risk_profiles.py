from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, localcontext
from typing import Any

from .contracts import (
    FinanceContractError,
    _scenario_targets_overlap,
    parse_decimal,
    parse_scenario_target,
)
from .serialization import canonical_json, canonical_sha256


_HASH = re.compile(r"^sha256:[a-f0-9]{64}$")
_VERSION = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
_ID_PATTERN = {
    "distribution": re.compile(r"^fdp_[A-Za-z0-9_-]{4,100}$"),
    "correlation": re.compile(r"^fcp_[A-Za-z0-9_-]{4,100}$"),
    "policy": re.compile(r"^fsp_[A-Za-z0-9_-]{4,100}$"),
    "sensitivity": re.compile(r"^fsn_[A-Za-z0-9_-]{4,100}$"),
}
_VARIABLE_ID = re.compile(r"^var_[A-Za-z0-9_-]{1,80}$")
_AXIS_ID = re.compile(r"^axis_[A-Za-z0-9_-]{1,80}$")
_CURRENCY = re.compile(r"^[A-Z]{3}$")
_DATE_FORMAT = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATETIME_FORMAT = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)
_DISTRIBUTION_PROFILE_REF = re.compile(
    r"^distribution:(fdp_[A-Za-z0-9_-]{4,100})@([0-9]+\.[0-9]+\.[0-9]+)$"
)

_REQUIRED_ROLES = frozenset(
    {
        "finance_reviewer",
        "sector_expert",
        "quantitative_reviewer",
        "qa",
        "security",
    }
)
_ALLOWED_STATUSES = frozenset(
    {
        "draft",
        "calibrated",
        "finance_reviewed",
        "sector_reviewed",
        "approved",
    }
)
_SCHEMA_KIND = {
    "finance-simulation-distribution-profile.v1": "distribution",
    "finance-simulation-correlation-profile.v1": "correlation",
    "finance-simulation-policy.v1": "policy",
    "finance-sensitivity-profile.v1": "sensitivity",
}
_TOP_LEVEL = {
    "distribution": frozenset(
        {
            "schema_version",
            "profile_id",
            "version",
            "content_hash",
            "status",
            "currency",
            "archetype_ref",
            "target_contract_version",
            "variables",
            "review",
            "metadata",
        }
    ),
    "correlation": frozenset(
        {
            "schema_version",
            "profile_id",
            "version",
            "content_hash",
            "status",
            "distribution_profile_ref",
            "distribution_profile_hash",
            "method",
            "variable_ids",
            "matrix",
            "validation_policy",
            "calibration",
            "review",
            "metadata",
        }
    ),
    "policy": frozenset(
        {
            "schema_version",
            "policy_id",
            "version",
            "content_hash",
            "status",
            "rng",
            "iterations",
            "convergence",
            "outputs",
            "review",
            "metadata",
            "lineage",
        }
    ),
    "sensitivity": frozenset(
        {
            "schema_version",
            "profile_id",
            "version",
            "content_hash",
            "status",
            "currency",
            "archetype_ref",
            "axes",
            "fixed_overrides",
            "metric_ids",
            "maximum_cells",
            "review",
            "metadata",
        }
    ),
}
_DISTRIBUTION_PARAMETERS = {
    "triangular": frozenset({"minimum", "mode", "maximum"}),
    "uniform": frozenset({"minimum", "maximum"}),
    "normal_truncated": frozenset(
        {"mean", "stddev", "minimum", "maximum"}
    ),
    "lognormal_truncated": frozenset(
        {"mu", "sigma", "minimum", "maximum"}
    ),
    "discrete_empirical": frozenset({"values", "probabilities"}),
}
_SENSITIVITY_METRICS = frozenset(
    {
        "npv_unlevered",
        "irr_unlevered",
        "mirr_unlevered",
        "payback_months",
        "break_even",
        "funding_need",
        "dscr_min",
        "llcr",
    }
)
_SIMULATION_OUTPUT_METRICS = _SENSITIVITY_METRICS - {"break_even"}
_CONVERGENCE_METRICS = frozenset(
    {"npv_unlevered", "irr_unlevered", "funding_need", "dscr_min", "llcr"}
)
_MAX_TOLERANCE = Decimal("0.000001")
_PROBABILITY_TOLERANCE = Decimal("0.00000001")


@dataclass(frozen=True, slots=True)
class ManifestProfileBinding:
    schema_version: str
    profile_id: str
    version: str
    content_hash: str


@dataclass(frozen=True, slots=True)
class ResolvedRiskProfileBinding:
    expected_schema_version: str
    expected_profile_id: str
    expected_version: str
    expected_content_hash: str
    registry_snapshot_hash: str
    organization_id: str
    scope_kind: str
    owner_organization_id: str | None
    approved_manifest_id: str
    approved_manifest_hash: str
    policy_ref: str
    policy_version: str
    policy_hash: str
    as_of_date: str
    manifest_profiles: tuple[ManifestProfileBinding, ...] = ()
    authorized_reviewers: tuple[tuple[str, str], ...] = ()
    evidence_refs: tuple[str, ...] = ()
    distribution_variable_ids: tuple[str, ...] = ()
    dependency_hashes: tuple[tuple[str, str], ...] = ()
    authoritative: bool = False
    allow_global: bool = False
    require_execution_ready: bool = False


@dataclass(frozen=True, slots=True)
class ValidatedRiskProfile:
    kind: str
    profile_id: str
    version: str
    content_hash: str
    registry_snapshot_hash: str
    status: str
    scope_kind: str
    approved_manifest_id: str
    approved_manifest_hash: str
    policy_ref: str
    policy_version: str
    policy_hash: str
    dependency_hashes: tuple[tuple[str, str], ...]
    canonical_document: str
    execution_ready: bool

    def thaw(self) -> dict[str, Any]:
        return json.loads(self.canonical_document)


def validate_risk_profile(
    document: Mapping[str, Any],
    *,
    binding: ResolvedRiskProfileBinding,
) -> ValidatedRiskProfile:
    if not isinstance(document, Mapping):
        raise FinanceContractError(
            "FIN2_PROFILE_DOCUMENT_TYPE",
            "$",
            "profile must be an object",
        )
    _validate_resource_shape(document)
    _validate_binding(binding)

    schema_version = _text(
        document.get("schema_version"),
        "$.schema_version",
        maximum=100,
    )
    kind = _SCHEMA_KIND.get(schema_version)
    if kind is None:
        raise FinanceContractError(
            "FIN2_PROFILE_SCHEMA_VERSION",
            "$.schema_version",
            "unsupported risk profile schema",
        )
    if schema_version != binding.expected_schema_version:
        raise FinanceContractError(
            "FIN2_PROFILE_BINDING_MISMATCH",
            "$.schema_version",
            "resolved schema does not match trusted binding",
        )

    expected_fields = _TOP_LEVEL[kind]
    _require_exact_fields(document, expected_fields, "$")
    identifier_key = "policy_id" if kind == "policy" else "profile_id"
    identifier = _text(
        document[identifier_key],
        f"$.{identifier_key}",
        maximum=110,
    )
    identifier_pattern = _ID_PATTERN[kind]
    if identifier_pattern.fullmatch(identifier) is None:
        raise FinanceContractError(
            "FIN2_PROFILE_ID",
            f"$.{identifier_key}",
            "invalid profile identifier",
        )
    version = _text(document["version"], "$.version", maximum=40)
    if _VERSION.fullmatch(version) is None:
        raise FinanceContractError(
            "FIN2_PROFILE_VERSION",
            "$.version",
            "version must be semantic x.y.z",
        )

    supplied_hash = _hash(document["content_hash"], "$.content_hash")
    hash_document = dict(document)
    del hash_document["content_hash"]
    actual_hash = canonical_sha256(hash_document)
    if supplied_hash != actual_hash:
        raise FinanceContractError(
            "FIN2_PROFILE_HASH_MISMATCH",
            "$.content_hash",
            "content hash does not match canonical profile",
        )
    expected = {
        f"$.{identifier_key}": (identifier, binding.expected_profile_id),
        "$.version": (version, binding.expected_version),
        "$.content_hash": (
            supplied_hash,
            binding.expected_content_hash,
        ),
    }
    for field_ref, (actual, trusted) in expected.items():
        if actual != trusted:
            raise FinanceContractError(
                "FIN2_PROFILE_BINDING_MISMATCH",
                field_ref,
                "profile does not match trusted registry resolution",
            )

    scope_kind = _validate_scope(binding)
    if binding.authoritative:
        manifest_key = (schema_version, identifier, version, supplied_hash)
        allowed_manifest_keys = {
            (
                item.schema_version,
                item.profile_id,
                item.version,
                item.content_hash,
            )
            for item in binding.manifest_profiles
        }
        if manifest_key not in allowed_manifest_keys:
            raise FinanceContractError(
                "FIN2_PROFILE_MANIFEST_UNBOUND",
                "$.content_hash",
                "profile is not pinned by the approved manifest",
            )
    status = _text(document["status"], "$.status", maximum=40)
    if status not in _ALLOWED_STATUSES:
        raise FinanceContractError(
            "FIN2_PROFILE_STATUS",
            "$.status",
            "unsupported lifecycle status",
        )
    if not binding.authoritative and status == "approved":
        raise FinanceContractError(
            "FIN2_PROFILE_APPROVED_REQUIRES_ADMISSION",
            "$.status",
            "approved status requires authoritative registry admission",
        )
    created_at = _validate_metadata(
        document["metadata"],
        binding.as_of_date,
    )
    _validate_review(document["review"], status, binding, created_at)
    if binding.authoritative and status != "approved":
        raise FinanceContractError(
            "FIN2_PROFILE_NOT_APPROVED",
            "$.status",
            "authoritative admission requires approved profile",
        )

    if kind == "distribution":
        _validate_distribution(document, binding)
    elif kind == "correlation":
        _validate_correlation(document, binding)
    elif kind == "policy":
        _validate_policy(document, binding)
    else:
        _validate_sensitivity(document, binding)

    if binding.require_execution_ready:
        raise FinanceContractError(
            "FIN2_PROFILE_ENGINE_NOT_READY",
            "$.schema_version",
            "C3B validates admission only; execution is not authorized",
        )

    canonical = canonical_json(document)
    return ValidatedRiskProfile(
        kind=kind,
        profile_id=identifier,
        version=version,
        content_hash=supplied_hash,
        registry_snapshot_hash=binding.registry_snapshot_hash,
        status=status,
        scope_kind=scope_kind,
        approved_manifest_id=binding.approved_manifest_id,
        approved_manifest_hash=binding.approved_manifest_hash,
        policy_ref=binding.policy_ref,
        policy_version=binding.policy_version,
        policy_hash=binding.policy_hash,
        dependency_hashes=binding.dependency_hashes,
        canonical_document=canonical,
        execution_ready=False,
    )


def admit_risk_profile(
    document: Mapping[str, Any],
    *,
    binding: ResolvedRiskProfileBinding,
) -> ValidatedRiskProfile:
    if not isinstance(binding, ResolvedRiskProfileBinding):
        raise FinanceContractError(
            "FIN2_PROFILE_BINDING_TYPE",
            "binding",
            "binding must be a trusted ResolvedRiskProfileBinding",
        )
    if not binding.authoritative:
        raise FinanceContractError(
            "FIN2_PROFILE_ADMISSION_MODE",
            "binding.authoritative",
            "registry admission requires an authoritative trusted binding",
        )
    return validate_risk_profile(document, binding=binding)


def profile_content_hash(document: Mapping[str, Any]) -> str:
    if not isinstance(document, Mapping):
        raise FinanceContractError(
            "FIN2_PROFILE_DOCUMENT_TYPE",
            "$",
            "profile must be an object",
        )
    _validate_resource_shape(document)
    payload = dict(document)
    payload.pop("content_hash", None)
    return canonical_sha256(payload)


def _validate_binding(binding: ResolvedRiskProfileBinding) -> None:
    if not isinstance(binding, ResolvedRiskProfileBinding):
        raise FinanceContractError(
            "FIN2_PROFILE_BINDING_TYPE",
            "binding",
            "binding must be a trusted ResolvedRiskProfileBinding",
        )
    for field_ref, value, maximum in (
        ("binding.expected_schema_version", binding.expected_schema_version, 100),
        ("binding.expected_profile_id", binding.expected_profile_id, 110),
        ("binding.expected_version", binding.expected_version, 40),
        ("binding.organization_id", binding.organization_id, 120),
        ("binding.approved_manifest_id", binding.approved_manifest_id, 160),
        ("binding.policy_ref", binding.policy_ref, 160),
        ("binding.policy_version", binding.policy_version, 40),
        ("binding.as_of_date", binding.as_of_date, 10),
    ):
        _text(value, field_ref, maximum=maximum)
    if binding.expected_schema_version not in _SCHEMA_KIND:
        raise FinanceContractError(
            "FIN2_PROFILE_BINDING_SCHEMA",
            "binding.expected_schema_version",
            "trusted binding names an unsupported schema",
        )
    expected_pattern = _ID_PATTERN[
        _SCHEMA_KIND[binding.expected_schema_version]
    ]
    if expected_pattern.fullmatch(binding.expected_profile_id) is None:
        raise FinanceContractError(
            "FIN2_PROFILE_BINDING_ID",
            "binding.expected_profile_id",
            "trusted binding carries an invalid profile identifier",
        )
    if _VERSION.fullmatch(binding.expected_version) is None:
        raise FinanceContractError(
            "FIN2_PROFILE_BINDING_VERSION",
            "binding.expected_version",
            "trusted binding version must be semantic x.y.z",
        )
    _hash(binding.expected_content_hash, "binding.expected_content_hash")
    _hash(binding.registry_snapshot_hash, "binding.registry_snapshot_hash")
    _hash(binding.approved_manifest_hash, "binding.approved_manifest_hash")
    if _ID_PATTERN["policy"].fullmatch(binding.policy_ref) is None:
        raise FinanceContractError(
            "FIN2_PROFILE_POLICY_BINDING",
            "binding.policy_ref",
            "trusted policy ref must be a governed policy identifier",
        )
    if _VERSION.fullmatch(binding.policy_version) is None:
        raise FinanceContractError(
            "FIN2_PROFILE_POLICY_BINDING",
            "binding.policy_version",
            "trusted policy version must be semantic x.y.z",
        )
    _hash(binding.policy_hash, "binding.policy_hash")
    _date(binding.as_of_date, "binding.as_of_date")
    if type(binding.authoritative) is not bool:
        raise FinanceContractError(
            "FIN2_PROFILE_BINDING_TYPE",
            "binding.authoritative",
            "authoritative must be a boolean",
        )
    if type(binding.allow_global) is not bool:
        raise FinanceContractError(
            "FIN2_PROFILE_BINDING_TYPE",
            "binding.allow_global",
            "allow_global must be a boolean",
        )
    if type(binding.require_execution_ready) is not bool:
        raise FinanceContractError(
            "FIN2_PROFILE_BINDING_TYPE",
            "binding.require_execution_ready",
            "require_execution_ready must be a boolean",
        )
    for field_name, items, maximum in (
        ("manifest_profiles", binding.manifest_profiles, 100),
        ("authorized_reviewers", binding.authorized_reviewers, 5),
        ("evidence_refs", binding.evidence_refs, 100),
        (
            "distribution_variable_ids",
            binding.distribution_variable_ids,
            50,
        ),
        ("dependency_hashes", binding.dependency_hashes, 100),
    ):
        if not isinstance(items, tuple) or len(items) > maximum:
            raise FinanceContractError(
                "FIN2_PROFILE_BINDING_SIZE",
                f"binding.{field_name}",
                f"trusted binding must be an immutable tuple of at most {maximum}",
            )

    if binding.scope_kind == "organization":
        owner = _text(
            binding.owner_organization_id,
            "binding.owner_organization_id",
            maximum=120,
        )
        if owner != binding.organization_id:
            raise FinanceContractError(
                "FIN2_PROFILE_TENANT_MISMATCH",
                "binding.owner_organization_id",
                "registry owner does not match trusted request organization",
            )
    elif binding.scope_kind == "global":
        if binding.owner_organization_id is not None:
            raise FinanceContractError(
                "FIN2_PROFILE_SCOPE",
                "binding.owner_organization_id",
                "global registry entry must not carry tenant ownership",
            )
        if not binding.allow_global:
            raise FinanceContractError(
                "FIN2_PROFILE_SCOPE_DENIED",
                "binding.scope_kind",
                "trusted request does not allow global profiles",
            )
    else:
        raise FinanceContractError(
            "FIN2_PROFILE_SCOPE",
            "binding.scope_kind",
            "unsupported registry scope",
        )

    manifest_seen: set[tuple[str, str, str, str]] = set()
    for index, item in enumerate(binding.manifest_profiles):
        ref = f"binding.manifest_profiles[{index}]"
        if not isinstance(item, ManifestProfileBinding):
            raise FinanceContractError(
                "FIN2_PROFILE_MANIFEST_BINDING",
                ref,
                "manifest entry must be ManifestProfileBinding",
            )
        schema_version = _text(
            item.schema_version,
            f"{ref}.schema_version",
            maximum=100,
        )
        if schema_version not in _SCHEMA_KIND:
            raise FinanceContractError(
                "FIN2_PROFILE_MANIFEST_BINDING",
                f"{ref}.schema_version",
                "manifest entry names an unsupported schema",
            )
        profile_id = _text(item.profile_id, f"{ref}.profile_id", maximum=110)
        pattern = _ID_PATTERN[_SCHEMA_KIND[schema_version]]
        if pattern.fullmatch(profile_id) is None:
            raise FinanceContractError(
                "FIN2_PROFILE_MANIFEST_BINDING",
                f"{ref}.profile_id",
                "manifest entry carries an invalid profile identifier",
            )
        version = _text(item.version, f"{ref}.version", maximum=40)
        if _VERSION.fullmatch(version) is None:
            raise FinanceContractError(
                "FIN2_PROFILE_MANIFEST_BINDING",
                f"{ref}.version",
                "manifest entry version must be semantic x.y.z",
            )
        content_hash = _hash(item.content_hash, f"{ref}.content_hash")
        key = (schema_version, profile_id, version, content_hash)
        if key in manifest_seen:
            raise FinanceContractError(
                "FIN2_PROFILE_MANIFEST_BINDING",
                ref,
                "duplicate manifest profile binding",
            )
        manifest_seen.add(key)
    if binding.authoritative and not manifest_seen:
        raise FinanceContractError(
            "FIN2_PROFILE_MANIFEST_UNBOUND",
            "binding.manifest_profiles",
            "authoritative admission requires approved manifest bindings",
        )
    if binding.authoritative and (
        (
            "finance-simulation-policy.v1",
            binding.policy_ref,
            binding.policy_version,
            binding.policy_hash,
        )
        not in manifest_seen
    ):
        raise FinanceContractError(
            "FIN2_PROFILE_POLICY_UNBOUND",
            "binding.policy_ref",
            "selected policy is not pinned by the approved manifest",
        )

    reviewer_seen: set[str] = set()
    reviewer_identity_seen: set[str] = set()
    for index, item in enumerate(binding.authorized_reviewers):
        ref = f"binding.authorized_reviewers[{index}]"
        if (
            not isinstance(item, tuple)
            or len(item) != 2
            or not all(isinstance(value, str) for value in item)
        ):
            raise FinanceContractError(
                "FIN2_PROFILE_REVIEWER_BINDING",
                ref,
                "reviewer binding must be (role, reviewer_ref)",
            )
        role, reviewer_ref = item
        if role not in _REQUIRED_ROLES or role in reviewer_seen:
            raise FinanceContractError(
                "FIN2_PROFILE_REVIEWER_BINDING",
                ref,
                "reviewer roles must be unique and allowlisted",
            )
        reviewer_ref = _text(reviewer_ref, f"{ref}[1]", maximum=160)
        if reviewer_ref in reviewer_identity_seen:
            raise FinanceContractError(
                "FIN2_PROFILE_REVIEWER_BINDING",
                ref,
                "one reviewer identity cannot satisfy multiple governed roles",
            )
        reviewer_seen.add(role)
        reviewer_identity_seen.add(reviewer_ref)

    evidence_seen: set[str] = set()
    for index, item in enumerate(binding.evidence_refs):
        ref = f"binding.evidence_refs[{index}]"
        evidence = _text(item, ref, maximum=200)
        if evidence in evidence_seen:
            raise FinanceContractError(
                "FIN2_PROFILE_EVIDENCE_BINDING",
                ref,
                "duplicate trusted evidence reference",
            )
        evidence_seen.add(evidence)

    parsed_distribution_variables = tuple(
        _text(
            item,
            f"binding.distribution_variable_ids[{index}]",
            maximum=84,
        )
        for index, item in enumerate(binding.distribution_variable_ids)
    )
    if (
        len(set(parsed_distribution_variables))
        != len(parsed_distribution_variables)
        or any(
            _VARIABLE_ID.fullmatch(item) is None
            for item in parsed_distribution_variables
        )
    ):
        raise FinanceContractError(
            "FIN2_PROFILE_DEPENDENCY_VARIABLES",
            "binding.distribution_variable_ids",
            "distribution variable ids must be unique and governed",
        )
    expects_distribution_variables = (
        binding.expected_schema_version
        == "finance-simulation-correlation-profile.v1"
    )
    if expects_distribution_variables and len(parsed_distribution_variables) < 2:
        raise FinanceContractError(
            "FIN2_PROFILE_DEPENDENCY_VARIABLES",
            "binding.distribution_variable_ids",
            "correlation admission requires resolved distribution variables",
        )
    if not expects_distribution_variables and parsed_distribution_variables:
        raise FinanceContractError(
            "FIN2_PROFILE_DEPENDENCY_VARIABLES",
            "binding.distribution_variable_ids",
            "distribution variables are only valid for correlation admission",
        )

    dependency_seen: set[str] = set()
    for index, item in enumerate(binding.dependency_hashes):
        ref = f"binding.dependency_hashes[{index}]"
        if (
            not isinstance(item, tuple)
            or len(item) != 2
            or not all(isinstance(value, str) for value in item)
        ):
            raise FinanceContractError(
                "FIN2_PROFILE_DEPENDENCY_BINDING",
                ref,
                "dependency binding must be (ref, hash)",
            )
        dependency_ref = _text(item[0], f"{ref}[0]", maximum=200)
        if dependency_ref in dependency_seen:
            raise FinanceContractError(
                "FIN2_PROFILE_DEPENDENCY_BINDING",
                ref,
                "duplicate dependency ref",
            )
        dependency_seen.add(dependency_ref)
        _hash(item[1], f"{ref}[1]")


def _validate_scope(binding: ResolvedRiskProfileBinding) -> str:
    return binding.scope_kind

def _validate_metadata(value: Any, as_of_text: str) -> datetime:
    row = _mapping(value, "$.metadata")
    _require_fields(
        row,
        {"owner_ref", "effective_from", "created_at"},
        {
            "owner_ref",
            "effective_from",
            "expires_at",
            "supersedes_ref",
            "created_at",
        },
        "$.metadata",
    )
    _text(row["owner_ref"], "$.metadata.owner_ref", maximum=160)
    effective = _date(
        row["effective_from"],
        "$.metadata.effective_from",
    )
    created = _datetime(row["created_at"], "$.metadata.created_at")
    as_of = _date(as_of_text, "binding.as_of_date")
    if created.date() > as_of:
        raise FinanceContractError(
            "FIN2_PROFILE_LIFECYCLE",
            "$.metadata.created_at",
            "profile creation is after trusted as-of date",
        )
    if effective > as_of:
        raise FinanceContractError(
            "FIN2_PROFILE_NOT_EFFECTIVE",
            "$.metadata.effective_from",
            "profile is not effective at trusted as-of date",
        )
    if "expires_at" in row:
        expires = _date(row["expires_at"], "$.metadata.expires_at")
        if expires < effective:
            raise FinanceContractError(
                "FIN2_PROFILE_LIFECYCLE",
                "$.metadata.expires_at",
                "expiry precedes effective date",
            )
        if expires < as_of:
            raise FinanceContractError(
                "FIN2_PROFILE_EXPIRED",
                "$.metadata.expires_at",
                "profile expired before trusted as-of date",
            )
    if "supersedes_ref" in row:
        _text(
            row["supersedes_ref"],
            "$.metadata.supersedes_ref",
            maximum=160,
        )
    return created


def _validate_review(
    value: Any,
    status: str,
    binding: ResolvedRiskProfileBinding,
    created_at: datetime,
) -> None:
    row = _mapping(value, "$.review")
    _require_fields(
        row,
        {"required_roles", "approvals"},
        {"required_roles", "approvals"},
        "$.review",
    )
    raw_roles = _sequence(
        row["required_roles"],
        "$.review.required_roles",
        minimum=2,
        maximum=5,
    )
    roles = [
        _text(
            role,
            f"$.review.required_roles[{index}]",
            maximum=40,
        )
        for index, role in enumerate(raw_roles)
    ]
    if len(set(roles)) != len(roles) or any(
        role not in _REQUIRED_ROLES for role in roles
    ):
        raise FinanceContractError(
            "FIN2_PROFILE_REVIEW_ROLE",
            "$.review.required_roles",
            "review roles must be unique and allowlisted",
        )
    approvals = _sequence(
        row["approvals"],
        "$.review.approvals",
        minimum=0,
        maximum=20,
    )
    trusted_reviewers = dict(binding.authorized_reviewers)
    trusted_evidence = set(binding.evidence_refs)
    as_of = _date(binding.as_of_date, "binding.as_of_date")
    seen_roles: set[str] = set()
    approved_roles: set[str] = set()
    rejected = False
    for index, raw in enumerate(approvals):
        ref = f"$.review.approvals[{index}]"
        approval = _mapping(raw, ref)
        _require_fields(
            approval,
            {
                "role",
                "reviewer_ref",
                "status",
                "reviewed_at",
                "evidence_ref",
            },
            {
                "role",
                "reviewer_ref",
                "status",
                "reviewed_at",
                "evidence_ref",
            },
            ref,
        )
        role = _text(approval["role"], f"{ref}.role", maximum=40)
        if (
            role not in _REQUIRED_ROLES
            or role not in roles
            or role in seen_roles
        ):
            raise FinanceContractError(
                "FIN2_PROFILE_REVIEW_ROLE",
                f"{ref}.role",
                "approval role is unsupported, undeclared, or duplicated",
            )
        seen_roles.add(role)
        reviewer_ref = _text(
            approval["reviewer_ref"],
            f"{ref}.reviewer_ref",
            maximum=160,
        )
        if trusted_reviewers.get(role) != reviewer_ref:
            raise FinanceContractError(
                "FIN2_PROFILE_REVIEWER_UNBOUND",
                f"{ref}.reviewer_ref",
                "reviewer identity is not authorized by trusted admission context",
            )
        reviewed_at = _datetime(
            approval["reviewed_at"],
            f"{ref}.reviewed_at",
        )
        if reviewed_at.date() > as_of:
            raise FinanceContractError(
                "FIN2_PROFILE_REVIEW_FUTURE",
                f"{ref}.reviewed_at",
                "review timestamp is after trusted as-of date",
            )
        if reviewed_at < created_at:
            raise FinanceContractError(
                "FIN2_PROFILE_REVIEW_ORDER",
                f"{ref}.reviewed_at",
                "review timestamp precedes profile creation",
            )
        evidence_ref = _text(
            approval["evidence_ref"],
            f"{ref}.evidence_ref",
            maximum=200,
        )
        if evidence_ref not in trusted_evidence:
            raise FinanceContractError(
                "FIN2_PROFILE_EVIDENCE_UNBOUND",
                f"{ref}.evidence_ref",
                "review evidence is not bound to trusted admission context",
            )
        decision = _text(
            approval["status"],
            f"{ref}.status",
            maximum=20,
        )
        if decision not in {"approved", "rejected"}:
            raise FinanceContractError(
                "FIN2_PROFILE_REVIEW_STATUS",
                f"{ref}.status",
                "unsupported review decision",
            )
        rejected = rejected or decision == "rejected"
        if decision == "approved":
            approved_roles.add(role)
    if status == "approved" and (
        set(roles) != _REQUIRED_ROLES
        or approved_roles != _REQUIRED_ROLES
        or rejected
    ):
        raise FinanceContractError(
            "FIN2_PROFILE_APPROVAL_INCOMPLETE",
            "$.review",
            "approved profile requires five unique approvals and no rejection",
        )


def _validate_distribution(
    document: Mapping[str, Any],
    binding: ResolvedRiskProfileBinding,
) -> None:
    if document["target_contract_version"] != "finance-model-input.v2":
        raise FinanceContractError(
            "FIN2_PROFILE_TARGET_CONTRACT",
            "$.target_contract_version",
            "unsupported target contract",
        )
    _currency(document["currency"], "$.currency")
    _validate_archetype(document["archetype_ref"], binding)
    variables = _sequence(
        document["variables"],
        "$.variables",
        minimum=1,
        maximum=50,
    )
    seen_ids: set[str] = set()
    parsed_targets: list[Mapping[str, str]] = []
    for index, raw in enumerate(variables):
        ref = f"$.variables[{index}]"
        row = _mapping(raw, ref)
        _require_fields(
            row,
            {
                "variable_id",
                "target_ref",
                "operation",
                "unit",
                "distribution",
                "bounds",
                "calibration",
            },
            {
                "variable_id",
                "target_ref",
                "operation",
                "unit",
                "distribution",
                "bounds",
                "calibration",
            },
            ref,
        )
        variable_id = _text(
            row["variable_id"],
            f"{ref}.variable_id",
            maximum=84,
        )
        if _VARIABLE_ID.fullmatch(variable_id) is None:
            raise FinanceContractError(
                "FIN2_PROFILE_VARIABLE_ID",
                f"{ref}.variable_id",
                "invalid variable id",
            )
        if variable_id in seen_ids:
            raise FinanceContractError(
                "FIN2_PROFILE_VARIABLE_DUPLICATE",
                f"{ref}.variable_id",
                "duplicate variable id",
            )
        seen_ids.add(variable_id)
        target = parse_scenario_target(
            row["target_ref"],
            f"{ref}.target_ref",
        )
        if any(
            _scenario_targets_overlap(target, prior)
            for prior in parsed_targets
        ):
            raise FinanceContractError(
                "FIN2_PROFILE_TARGET_OVERLAP",
                f"{ref}.target_ref",
                "profile targets overlap",
            )
        parsed_targets.append(target)
        operation = _text(
            row["operation"],
            f"{ref}.operation",
            maximum=20,
        )
        if operation not in {"replace", "multiply", "add"}:
            raise FinanceContractError(
                "FIN2_PROFILE_OPERATION",
                f"{ref}.operation",
                "unsupported operation",
            )
        unit = _text(row["unit"], f"{ref}.unit", maximum=20)
        if unit not in {
            "money",
            "units",
            "count",
            "days",
            "rate",
            "ratio",
            "multiplier",
        }:
            raise FinanceContractError(
                "FIN2_PROFILE_UNIT",
                f"{ref}.unit",
                "unsupported unit",
            )
        bounds = _mapping(row["bounds"], f"{ref}.bounds")
        _require_fields(
            bounds,
            {"minimum", "maximum"},
            {"minimum", "maximum"},
            f"{ref}.bounds",
        )
        minimum = _profile_decimal(
            bounds["minimum"],
            f"{ref}.bounds.minimum",
        )
        maximum = _profile_decimal(
            bounds["maximum"],
            f"{ref}.bounds.maximum",
        )
        if minimum > maximum:
            raise FinanceContractError(
                "FIN2_PROFILE_BOUNDS",
                f"{ref}.bounds",
                "minimum exceeds maximum",
            )
        if operation == "multiply" and minimum < 0:
            raise FinanceContractError(
                "FIN2_PROFILE_BOUNDS",
                f"{ref}.bounds.minimum",
                "multiplier distribution must be non-negative",
            )
        _validate_distribution_spec(
            row["distribution"],
            minimum,
            maximum,
            f"{ref}.distribution",
        )
        _validate_calibration(
            row["calibration"],
            f"{ref}.calibration",
            binding.as_of_date,
        )


def _validate_distribution_spec(
    value: Any,
    outer_minimum: Decimal,
    outer_maximum: Decimal,
    field_ref: str,
) -> None:
    row = _mapping(value, field_ref)
    _require_fields(
        row,
        {"kind", "parameters"},
        {"kind", "parameters"},
        field_ref,
    )
    kind = _text(row["kind"], f"{field_ref}.kind", maximum=40)
    required = _DISTRIBUTION_PARAMETERS.get(kind)
    if required is None:
        raise FinanceContractError(
            "FIN2_PROFILE_DISTRIBUTION_KIND",
            f"{field_ref}.kind",
            "unsupported distribution kind",
        )
    parameters = _mapping(row["parameters"], f"{field_ref}.parameters")
    _require_exact_fields(parameters, required, f"{field_ref}.parameters")
    if kind == "discrete_empirical":
        values = _sequence(
            parameters["values"],
            f"{field_ref}.parameters.values",
            minimum=2,
            maximum=500,
        )
        probabilities = _sequence(
            parameters["probabilities"],
            f"{field_ref}.parameters.probabilities",
            minimum=2,
            maximum=500,
        )
        if len(values) != len(probabilities):
            raise FinanceContractError(
                "FIN2_PROFILE_PROBABILITY_LENGTH",
                f"{field_ref}.parameters",
                "values and probabilities must have equal length",
            )
        parsed_values = [
            _profile_decimal(item, f"{field_ref}.parameters.values[{index}]")
            for index, item in enumerate(values)
        ]
        parsed_probabilities = [
            _profile_decimal(
                item,
                f"{field_ref}.parameters.probabilities[{index}]",
                allow_negative=False,
            )
            for index, item in enumerate(probabilities)
        ]
        if any(item > 1 for item in parsed_probabilities):
            raise FinanceContractError(
                "FIN2_PROFILE_PROBABILITY_RANGE",
                f"{field_ref}.parameters.probabilities",
                "probabilities must be <= 1",
            )
        if abs(sum(parsed_probabilities, Decimal("0")) - 1) > _PROBABILITY_TOLERANCE:
            raise FinanceContractError(
                "FIN2_PROFILE_PROBABILITY_SUM",
                f"{field_ref}.parameters.probabilities",
                "probabilities must sum to one within tolerance",
            )
        if any(
            item < outer_minimum or item > outer_maximum
            for item in parsed_values
        ):
            raise FinanceContractError(
                "FIN2_PROFILE_BOUNDS",
                f"{field_ref}.parameters.values",
                "empirical value is outside declared bounds",
            )
        return

    minimum = _profile_decimal(
        parameters["minimum"],
        f"{field_ref}.parameters.minimum",
    )
    maximum = _profile_decimal(
        parameters["maximum"],
        f"{field_ref}.parameters.maximum",
    )
    if minimum != outer_minimum or maximum != outer_maximum:
        raise FinanceContractError(
            "FIN2_PROFILE_BOUNDS",
            field_ref,
            "distribution and variable bounds must match",
        )
    if minimum > maximum:
        raise FinanceContractError(
            "FIN2_PROFILE_BOUNDS",
            field_ref,
            "distribution minimum exceeds maximum",
        )
    if kind == "triangular":
        mode = _profile_decimal(
            parameters["mode"],
            f"{field_ref}.parameters.mode",
        )
        if not minimum <= mode <= maximum:
            raise FinanceContractError(
                "FIN2_PROFILE_DISTRIBUTION_PARAMETERS",
                f"{field_ref}.parameters.mode",
                "mode must lie within bounds",
            )
    elif kind == "normal_truncated":
        mean = _profile_decimal(
            parameters["mean"],
            f"{field_ref}.parameters.mean",
        )
        stddev = _profile_decimal(
            parameters["stddev"],
            f"{field_ref}.parameters.stddev",
            allow_negative=False,
        )
        if stddev == 0 or not minimum <= mean <= maximum:
            raise FinanceContractError(
                "FIN2_PROFILE_DISTRIBUTION_PARAMETERS",
                f"{field_ref}.parameters",
                "normal mean/bounds/stddev are invalid",
            )
    elif kind == "lognormal_truncated":
        _profile_decimal(
            parameters["mu"],
            f"{field_ref}.parameters.mu",
        )
        sigma = _profile_decimal(
            parameters["sigma"],
            f"{field_ref}.parameters.sigma",
            allow_negative=False,
        )
        if sigma == 0 or minimum < 0:
            raise FinanceContractError(
                "FIN2_PROFILE_DISTRIBUTION_PARAMETERS",
                f"{field_ref}.parameters",
                "lognormal sigma/bounds are invalid",
            )


def _validate_correlation(
    document: Mapping[str, Any],
    binding: ResolvedRiskProfileBinding,
) -> None:
    dependency_ref = _text(
        document["distribution_profile_ref"],
        "$.distribution_profile_ref",
        maximum=160,
    )
    dependency_hash = _hash(
        document["distribution_profile_hash"],
        "$.distribution_profile_hash",
    )
    dependency_match = _DISTRIBUTION_PROFILE_REF.fullmatch(dependency_ref)
    if dependency_match is None:
        raise FinanceContractError(
            "FIN2_PROFILE_DEPENDENCY_UNBOUND",
            "$.distribution_profile_ref",
            "correlation dependency ref must pin distribution id and version",
        )
    dependencies = dict(binding.dependency_hashes)
    if dependencies.get(dependency_ref) != dependency_hash:
        raise FinanceContractError(
            "FIN2_PROFILE_DEPENDENCY_UNBOUND",
            "$.distribution_profile_hash",
            "correlation dependency is not bound to trusted resolution",
        )
    if binding.authoritative:
        dependency_manifest_key = (
            "finance-simulation-distribution-profile.v1",
            dependency_match.group(1),
            dependency_match.group(2),
            dependency_hash,
        )
        manifest_keys = {
            (
                item.schema_version,
                item.profile_id,
                item.version,
                item.content_hash,
            )
            for item in binding.manifest_profiles
        }
        if dependency_manifest_key not in manifest_keys:
            raise FinanceContractError(
                "FIN2_PROFILE_DEPENDENCY_MANIFEST_UNBOUND",
                "$.distribution_profile_ref",
                "correlation distribution is not pinned by the approved manifest",
            )
    method = _text(document["method"], "$.method", maximum=40)
    if method not in {
        "pearson_gaussian_copula",
        "spearman_gaussian_copula",
    }:
        raise FinanceContractError(
            "FIN2_PROFILE_CORRELATION_METHOD",
            "$.method",
            "unsupported correlation method",
        )
    raw_variable_ids = _sequence(
        document["variable_ids"],
        "$.variable_ids",
        minimum=2,
        maximum=50,
    )
    variable_ids = [
        _text(item, f"$.variable_ids[{index}]", maximum=84)
        for index, item in enumerate(raw_variable_ids)
    ]
    if len(set(variable_ids)) != len(variable_ids) or any(
        _VARIABLE_ID.fullmatch(item) is None for item in variable_ids
    ):
        raise FinanceContractError(
            "FIN2_PROFILE_VARIABLE_ID",
            "$.variable_ids",
            "variable ids must be unique and valid",
        )
    if set(variable_ids) != set(binding.distribution_variable_ids):
        raise FinanceContractError(
            "FIN2_PROFILE_DEPENDENCY_VARIABLES",
            "$.variable_ids",
            "correlation variables do not match the resolved distribution",
        )
    policy = _mapping(
        document["validation_policy"],
        "$.validation_policy",
    )
    _require_fields(
        policy,
        {
            "symmetry_tolerance",
            "diagonal_tolerance",
            "psd_tolerance",
            "non_psd_behavior",
        },
        {
            "symmetry_tolerance",
            "diagonal_tolerance",
            "psd_tolerance",
            "non_psd_behavior",
        },
        "$.validation_policy",
    )
    tolerances = {
        name: _profile_decimal(
            policy[name],
            f"$.validation_policy.{name}",
            allow_negative=False,
        )
        for name in (
            "symmetry_tolerance",
            "diagonal_tolerance",
            "psd_tolerance",
        )
    }
    if any(value > _MAX_TOLERANCE for value in tolerances.values()):
        raise FinanceContractError(
            "FIN2_PROFILE_TOLERANCE",
            "$.validation_policy",
            "correlation tolerance exceeds governed maximum",
        )
    if policy["non_psd_behavior"] != "reject":
        raise FinanceContractError(
            "FIN2_PROFILE_PSD_POLICY",
            "$.validation_policy.non_psd_behavior",
            "non-PSD matrices must be rejected",
        )

    rows = _sequence(
        document["matrix"],
        "$.matrix",
        minimum=2,
        maximum=50,
    )
    size = len(variable_ids)
    if len(rows) != size:
        raise FinanceContractError(
            "FIN2_PROFILE_MATRIX_DIMENSION",
            "$.matrix",
            "matrix size must equal variable count",
        )
    matrix: list[list[Decimal]] = []
    for row_index, raw_row in enumerate(rows):
        items = _sequence(
            raw_row,
            f"$.matrix[{row_index}]",
            minimum=size,
            maximum=size,
        )
        parsed = [
            _profile_decimal(
                item,
                f"$.matrix[{row_index}][{column_index}]",
            )
            for column_index, item in enumerate(items)
        ]
        if any(item < -1 or item > 1 for item in parsed):
            raise FinanceContractError(
                "FIN2_PROFILE_CORRELATION_RANGE",
                f"$.matrix[{row_index}]",
                "correlation coefficient must be within [-1,1]",
            )
        matrix.append(parsed)
    for index in range(size):
        if abs(matrix[index][index] - 1) > tolerances["diagonal_tolerance"]:
            raise FinanceContractError(
                "FIN2_PROFILE_CORRELATION_DIAGONAL",
                f"$.matrix[{index}][{index}]",
                "correlation diagonal must equal one",
            )
        for other in range(index):
            if abs(matrix[index][other] - matrix[other][index]) > tolerances[
                "symmetry_tolerance"
            ]:
                raise FinanceContractError(
                    "FIN2_PROFILE_CORRELATION_SYMMETRY",
                    f"$.matrix[{index}][{other}]",
                    "correlation matrix must be symmetric",
                )
    if not _is_positive_semidefinite(
        matrix,
        tolerances["psd_tolerance"],
    ):
        raise FinanceContractError(
            "FIN2_PROFILE_CORRELATION_NOT_PSD",
            "$.matrix",
            "correlation matrix is not positive semidefinite",
        )
    _validate_calibration(
        document["calibration"],
        "$.calibration",
        binding.as_of_date,
    )


def _is_positive_semidefinite(
    matrix: list[list[Decimal]],
    tolerance: Decimal,
) -> bool:
    size = len(matrix)
    lower = [
        [Decimal("0") for _ in range(size)]
        for _ in range(size)
    ]
    diagonal = [Decimal("0") for _ in range(size)]
    with localcontext() as context:
        context.prec = 80
        for column in range(size):
            pivot = matrix[column][column] - sum(
                (
                    lower[column][prior]
                    * lower[column][prior]
                    * diagonal[prior]
                    for prior in range(column)
                ),
                Decimal("0"),
            )
            if pivot < -tolerance:
                return False
            if pivot <= 0:
                diagonal[column] = Decimal("0")
                for row in range(column + 1, size):
                    residual = matrix[row][column] - sum(
                        (
                            lower[row][prior]
                            * lower[column][prior]
                            * diagonal[prior]
                            for prior in range(column)
                        ),
                        Decimal("0"),
                    )
                    if abs(residual) > tolerance:
                        return False
                continue
            diagonal[column] = pivot
            lower[column][column] = Decimal("1")
            for row in range(column + 1, size):
                residual = matrix[row][column] - sum(
                    (
                        lower[row][prior]
                        * lower[column][prior]
                        * diagonal[prior]
                        for prior in range(column)
                    ),
                    Decimal("0"),
                )
                lower[row][column] = residual / pivot
    return True


def _validate_policy(
    document: Mapping[str, Any],
    binding: ResolvedRiskProfileBinding,
) -> None:
    _validate_lineage(document["lineage"], "$.lineage")
    rng = _mapping(document["rng"], "$.rng")
    _require_fields(
        rng,
        {
            "algorithm",
            "stream_derivation",
            "reference_vector_ref",
            "reference_vector_hash",
        },
        {
            "algorithm",
            "stream_derivation",
            "reference_vector_ref",
            "reference_vector_hash",
        },
        "$.rng",
    )
    if (
        rng["algorithm"] != "pcg64_dxsm_v1"
        or rng["stream_derivation"] != "seed_scenario_variable_v1"
    ):
        raise FinanceContractError(
            "FIN2_PROFILE_RNG_POLICY",
            "$.rng",
            "RNG algorithm or stream derivation is not pinned",
        )
    reference_vector_ref = _text(
        rng["reference_vector_ref"],
        "$.rng.reference_vector_ref",
        maximum=200,
    )
    reference_vector_hash = _hash(
        rng["reference_vector_hash"],
        "$.rng.reference_vector_hash",
    )
    dependencies = dict(binding.dependency_hashes)
    if dependencies.get(reference_vector_ref) != reference_vector_hash:
        raise FinanceContractError(
            "FIN2_PROFILE_DEPENDENCY_UNBOUND",
            "$.rng.reference_vector_ref",
            "RNG reference vector is not bound to trusted content hash",
        )
    iterations = _mapping(document["iterations"], "$.iterations")
    _require_fields(
        iterations,
        {"minimum", "maximum", "batch_size"},
        {"minimum", "maximum", "batch_size"},
        "$.iterations",
    )
    minimum = _integer(
        iterations["minimum"],
        "$.iterations.minimum",
        minimum=100,
        maximum=100000,
    )
    maximum = _integer(
        iterations["maximum"],
        "$.iterations.maximum",
        minimum=100,
        maximum=100000,
    )
    batch_size = _integer(
        iterations["batch_size"],
        "$.iterations.batch_size",
        minimum=50,
        maximum=10000,
    )
    if minimum > maximum or batch_size > maximum:
        raise FinanceContractError(
            "FIN2_PROFILE_ITERATION_POLICY",
            "$.iterations",
            "iteration bounds or batch size are inconsistent",
        )
    convergence = _mapping(document["convergence"], "$.convergence")
    _require_fields(
        convergence,
        {
            "monitored_metrics",
            "quantiles",
            "relative_tolerance",
            "absolute_tolerance",
            "minimum_batches",
            "stable_batches",
            "failure_policy",
        },
        {
            "monitored_metrics",
            "quantiles",
            "relative_tolerance",
            "absolute_tolerance",
            "minimum_batches",
            "stable_batches",
            "failure_policy",
        },
        "$.convergence",
    )
    monitored_metrics = _validate_unique_metrics(
        convergence["monitored_metrics"],
        "$.convergence.monitored_metrics",
        _CONVERGENCE_METRICS,
    )
    _validate_quantiles(
        convergence["quantiles"],
        "$.convergence.quantiles",
        {"0.10", "0.50", "0.90"},
    )
    relative_tolerance = _profile_decimal(
        convergence["relative_tolerance"],
        "$.convergence.relative_tolerance",
        allow_negative=False,
    )
    absolute_tolerance = _profile_decimal(
        convergence["absolute_tolerance"],
        "$.convergence.absolute_tolerance",
        allow_negative=False,
    )
    if relative_tolerance == 0 and absolute_tolerance == 0:
        raise FinanceContractError(
            "FIN2_PROFILE_CONVERGENCE_POLICY",
            "$.convergence",
            "at least one convergence tolerance must be positive",
        )
    minimum_batches = _integer(
        convergence["minimum_batches"],
        "$.convergence.minimum_batches",
        minimum=2,
        maximum=1000,
    )
    stable_batches = _integer(
        convergence["stable_batches"],
        "$.convergence.stable_batches",
        minimum=2,
        maximum=100,
    )
    available_batches = maximum // batch_size
    if (
        minimum_batches > available_batches
        or stable_batches > available_batches
        or minimum_batches + stable_batches - 1 > available_batches
    ):
        raise FinanceContractError(
            "FIN2_PROFILE_CONVERGENCE_POLICY",
            "$.convergence",
            "convergence batches exceed maximum iteration budget",
        )
    if convergence["failure_policy"] != "not_ready":
        raise FinanceContractError(
            "FIN2_PROFILE_CONVERGENCE_POLICY",
            "$.convergence.failure_policy",
            "convergence failure must remain not_ready",
        )
    outputs = _mapping(document["outputs"], "$.outputs")
    _require_fields(
        outputs,
        {"metric_ids", "quantiles", "probability_thresholds"},
        {"metric_ids", "quantiles", "probability_thresholds"},
        "$.outputs",
    )
    output_metrics = _validate_unique_metrics(
        outputs["metric_ids"],
        "$.outputs.metric_ids",
        _SIMULATION_OUTPUT_METRICS,
    )
    if not set(monitored_metrics).issubset(output_metrics):
        raise FinanceContractError(
            "FIN2_PROFILE_CONVERGENCE_POLICY",
            "$.convergence.monitored_metrics",
            "monitored metrics must be included in governed outputs",
        )
    _validate_quantiles(
        outputs["quantiles"],
        "$.outputs.quantiles",
        {
            "0.01",
            "0.05",
            "0.10",
            "0.25",
            "0.50",
            "0.75",
            "0.90",
            "0.95",
            "0.99",
        },
    )
    thresholds = _sequence(
        outputs["probability_thresholds"],
        "$.outputs.probability_thresholds",
        minimum=0,
        maximum=50,
    )
    seen_thresholds: set[tuple[str, str, Decimal]] = set()
    for index, raw in enumerate(thresholds):
        ref = f"$.outputs.probability_thresholds[{index}]"
        row = _mapping(raw, ref)
        _require_fields(
            row,
            {"metric_id", "operator", "value"},
            {"metric_id", "operator", "value"},
            ref,
        )
        metric_id = _text(
            row["metric_id"],
            f"{ref}.metric_id",
            maximum=60,
        )
        if metric_id not in output_metrics:
            raise FinanceContractError(
                "FIN2_PROFILE_METRIC",
                f"{ref}.metric_id",
                "threshold metric must be included in governed outputs",
            )
        operator = _text(
            row["operator"],
            f"{ref}.operator",
            maximum=8,
        )
        if operator not in {"lt", "lte", "gt", "gte"}:
            raise FinanceContractError(
                "FIN2_PROFILE_THRESHOLD_OPERATOR",
                f"{ref}.operator",
                "unsupported threshold operator",
            )
        threshold_value = _profile_decimal(
            row["value"],
            f"{ref}.value",
        )
        threshold_key = (metric_id, operator, threshold_value)
        if threshold_key in seen_thresholds:
            raise FinanceContractError(
                "FIN2_PROFILE_THRESHOLD_DUPLICATE",
                ref,
                "duplicate probability threshold",
            )
        seen_thresholds.add(threshold_key)


def _validate_sensitivity(
    document: Mapping[str, Any],
    binding: ResolvedRiskProfileBinding,
) -> None:
    _currency(document["currency"], "$.currency")
    _validate_archetype(document["archetype_ref"], binding)
    axes = _sequence(
        document["axes"],
        "$.axes",
        minimum=2,
        maximum=2,
    )
    parsed_targets: list[Mapping[str, str]] = []
    seen_axis_ids: set[str] = set()
    axis_lengths: list[int] = []
    for index, raw in enumerate(axes):
        ref = f"$.axes[{index}]"
        row = _mapping(raw, ref)
        _require_fields(
            row,
            {"axis_id", "target_ref", "operation", "values", "lineage"},
            {"axis_id", "target_ref", "operation", "values", "lineage"},
            ref,
        )
        axis_id = _text(row["axis_id"], f"{ref}.axis_id", maximum=84)
        if _AXIS_ID.fullmatch(axis_id) is None:
            raise FinanceContractError(
                "FIN2_PROFILE_AXIS_ID",
                f"{ref}.axis_id",
                "invalid sensitivity axis id",
            )
        if axis_id in seen_axis_ids:
            raise FinanceContractError(
                "FIN2_PROFILE_AXIS_DUPLICATE",
                f"{ref}.axis_id",
                "duplicate sensitivity axis",
            )
        seen_axis_ids.add(axis_id)
        target = parse_scenario_target(
            row["target_ref"],
            f"{ref}.target_ref",
        )
        _reject_target_overlap(target, parsed_targets, f"{ref}.target_ref")
        parsed_targets.append(target)
        operation = _text(
            row["operation"],
            f"{ref}.operation",
            maximum=20,
        )
        if operation not in {"replace", "multiply", "add"}:
            raise FinanceContractError(
                "FIN2_PROFILE_OPERATION",
                f"{ref}.operation",
                "unsupported operation",
            )
        values = _sequence(
            row["values"],
            f"{ref}.values",
            minimum=2,
            maximum=21,
        )
        parsed_values = [
            _profile_decimal(item, f"{ref}.values[{item_index}]")
            for item_index, item in enumerate(values)
        ]
        if operation == "multiply" and any(value < 0 for value in parsed_values):
            raise FinanceContractError(
                "FIN2_SCENARIO_MULTIPLIER_NEGATIVE",
                f"{ref}.values",
                "sensitivity multipliers must be non-negative",
            )
        if len(set(parsed_values)) != len(parsed_values):
            raise FinanceContractError(
                "FIN2_PROFILE_AXIS_VALUES",
                f"{ref}.values",
                "axis values must be unique",
            )
        axis_lengths.append(len(values))
        _validate_lineage(row["lineage"], f"{ref}.lineage")

    fixed = _sequence(
        document["fixed_overrides"],
        "$.fixed_overrides",
        minimum=0,
        maximum=50,
    )
    for index, raw in enumerate(fixed):
        ref = f"$.fixed_overrides[{index}]"
        row = _mapping(raw, ref)
        _require_fields(
            row,
            {"target_ref", "operation", "value", "lineage"},
            {"target_ref", "operation", "value", "lineage"},
            ref,
        )
        target = parse_scenario_target(
            row["target_ref"],
            f"{ref}.target_ref",
        )
        _reject_target_overlap(target, parsed_targets, f"{ref}.target_ref")
        parsed_targets.append(target)
        operation = _text(
            row["operation"],
            f"{ref}.operation",
            maximum=20,
        )
        if operation not in {"replace", "multiply", "add"}:
            raise FinanceContractError(
                "FIN2_PROFILE_OPERATION",
                f"{ref}.operation",
                "unsupported operation",
            )
        parsed_value = _profile_decimal(row["value"], f"{ref}.value")
        if operation == "multiply" and parsed_value < 0:
            raise FinanceContractError(
                "FIN2_SCENARIO_MULTIPLIER_NEGATIVE",
                f"{ref}.value",
                "sensitivity multiplier must be non-negative",
            )
        _validate_lineage(row["lineage"], f"{ref}.lineage")
    _validate_unique_metrics(
        document["metric_ids"],
        "$.metric_ids",
        _SENSITIVITY_METRICS,
    )
    maximum_cells = _integer(
        document["maximum_cells"],
        "$.maximum_cells",
        minimum=4,
        maximum=441,
    )
    cells = axis_lengths[0] * axis_lengths[1]
    if cells > maximum_cells:
        raise FinanceContractError(
            "FIN2_PROFILE_SENSITIVITY_CELLS",
            "$.maximum_cells",
            "axis product exceeds declared cell budget",
        )


def _reject_target_overlap(
    target: Mapping[str, str],
    prior_targets: Sequence[Mapping[str, str]],
    field_ref: str,
) -> None:
    if any(
        _scenario_targets_overlap(target, prior)
        for prior in prior_targets
    ):
        raise FinanceContractError(
            "FIN2_PROFILE_TARGET_OVERLAP",
            field_ref,
            "profile targets overlap",
        )


def _validate_calibration(
    value: Any,
    field_ref: str,
    as_of_text: str,
) -> None:
    row = _mapping(value, field_ref)
    _require_fields(
        row,
        {
            "method",
            "sample_size",
            "period_from",
            "period_to",
            "geography",
            "freshness_as_of",
            "data_source_refs",
            "lineage",
        },
        {
            "method",
            "sample_size",
            "period_from",
            "period_to",
            "geography",
            "freshness_as_of",
            "data_source_refs",
            "lineage",
        },
        field_ref,
    )
    method = _text(row["method"], f"{field_ref}.method", maximum=40)
    if method not in {
        "historical_empirical",
        "benchmark_reviewed",
        "expert_elicitation_reviewed",
        "hybrid_reviewed",
    }:
        raise FinanceContractError(
            "FIN2_PROFILE_CALIBRATION_METHOD",
            f"{field_ref}.method",
            "unsupported calibration method",
        )
    sample_size = _integer(
        row["sample_size"],
        f"{field_ref}.sample_size",
        minimum=0,
        maximum=1000000000,
    )
    if method == "historical_empirical" and sample_size == 0:
        raise FinanceContractError(
            "FIN2_PROFILE_CALIBRATION_SAMPLE",
            f"{field_ref}.sample_size",
            "historical calibration requires a positive sample size",
        )
    period_from = _date(
        row["period_from"],
        f"{field_ref}.period_from",
    )
    period_to = _date(row["period_to"], f"{field_ref}.period_to")
    freshness = _date(
        row["freshness_as_of"],
        f"{field_ref}.freshness_as_of",
    )
    as_of = _date(as_of_text, "binding.as_of_date")
    if (
        period_from > period_to
        or freshness < period_to
        or freshness > as_of
    ):
        raise FinanceContractError(
            "FIN2_PROFILE_CALIBRATION_PERIOD",
            field_ref,
            "calibration dates are inconsistent",
        )
    _text(row["geography"], f"{field_ref}.geography", maximum=120)
    sources = _sequence(
        row["data_source_refs"],
        f"{field_ref}.data_source_refs",
        minimum=1,
        maximum=100,
    )
    parsed_sources = [
        _text(
            item,
            f"{field_ref}.data_source_refs[{index}]",
            maximum=200,
        )
        for index, item in enumerate(sources)
    ]
    if len(set(parsed_sources)) != len(parsed_sources):
        raise FinanceContractError(
            "FIN2_PROFILE_SOURCE_DUPLICATE",
            f"{field_ref}.data_source_refs",
            "data source refs must be unique",
        )
    _validate_lineage(row["lineage"], f"{field_ref}.lineage")


def _validate_lineage(value: Any, field_ref: str) -> None:
    row = _mapping(value, field_ref)
    _require_fields(
        row,
        {"assumption_refs", "evidence_refs"},
        {"assumption_refs", "evidence_refs"},
        field_ref,
    )
    total_refs = 0
    for name, maximum in (("assumption_refs", 160), ("evidence_refs", 200)):
        items = _sequence(
            row[name],
            f"{field_ref}.{name}",
            minimum=0,
            maximum=200,
        )
        parsed_items = [
            _text(
                item,
                f"{field_ref}.{name}[{index}]",
                maximum=maximum,
            )
            for index, item in enumerate(items)
        ]
        if len(set(parsed_items)) != len(parsed_items):
            raise FinanceContractError(
                "FIN2_PROFILE_LINEAGE_DUPLICATE",
                f"{field_ref}.{name}",
                "lineage refs must be unique",
            )
        total_refs += len(parsed_items)
    if total_refs == 0:
        raise FinanceContractError(
            "FIN2_PROFILE_LINEAGE_EMPTY",
            field_ref,
            "lineage requires at least one assumption or evidence reference",
        )


def _validate_archetype(
    value: Any,
    binding: ResolvedRiskProfileBinding,
) -> None:
    row = _mapping(value, "$.archetype_ref")
    _require_fields(
        row,
        {"archetype_id", "version", "registry_hash"},
        {"archetype_id", "version", "registry_hash"},
        "$.archetype_ref",
    )
    _text(row["archetype_id"], "$.archetype_ref.archetype_id", maximum=100)
    version = _text(
        row["version"],
        "$.archetype_ref.version",
        maximum=40,
    )
    if _VERSION.fullmatch(version) is None:
        raise FinanceContractError(
            "FIN2_PROFILE_ARCHETYPE_VERSION",
            "$.archetype_ref.version",
            "invalid archetype version",
        )
    registry_hash = _hash(
        row["registry_hash"],
        "$.archetype_ref.registry_hash",
    )
    dependency_ref = f"archetype:{row['archetype_id']}@{version}"
    dependencies = dict(binding.dependency_hashes)
    if dependencies.get(dependency_ref) != registry_hash:
        raise FinanceContractError(
            "FIN2_PROFILE_DEPENDENCY_UNBOUND",
            "$.archetype_ref.registry_hash",
            "archetype registry dependency is not bound to trusted resolution",
        )


def _validate_unique_metrics(
    value: Any,
    field_ref: str,
    allowed: frozenset[str],
) -> tuple[str, ...]:
    items = _sequence(value, field_ref, minimum=1, maximum=20)
    parsed = tuple(
        _text(item, f"{field_ref}[{index}]", maximum=60)
        for index, item in enumerate(items)
    )
    if len(set(parsed)) != len(parsed) or any(
        item not in allowed for item in parsed
    ):
        raise FinanceContractError(
            "FIN2_PROFILE_METRIC",
            field_ref,
            "metrics must be unique and allowlisted",
        )
    return parsed


def _validate_quantiles(
    value: Any,
    field_ref: str,
    allowed: set[str],
) -> None:
    items = _sequence(value, field_ref, minimum=1, maximum=20)
    parsed = tuple(
        _text(item, f"{field_ref}[{index}]", maximum=20)
        for index, item in enumerate(items)
    )
    if len(set(parsed)) != len(parsed) or any(
        item not in allowed for item in parsed
    ):
        raise FinanceContractError(
            "FIN2_PROFILE_QUANTILE",
            field_ref,
            "quantiles must be unique and allowlisted",
        )


def _profile_decimal(
    value: Any,
    field_ref: str,
    *,
    allow_negative: bool = True,
) -> Decimal:
    if not isinstance(value, str) or len(value) > 128:
        raise FinanceContractError(
            "FIN2_PROFILE_DECIMAL_SIZE",
            field_ref,
            "decimal must be a bounded string",
        )
    return parse_decimal(
        value,
        field_ref,
        allow_negative=allow_negative,
    )


def _validate_resource_shape(value: Any) -> None:
    stack: list[tuple[Any, int]] = [(value, 0)]
    nodes = 0
    string_units = 0
    while stack:
        item, depth = stack.pop()
        nodes += 1
        if nodes > 20000 or depth > 16:
            raise FinanceContractError(
                "FIN2_PROFILE_RESOURCE_LIMIT",
                "$",
                "profile structure exceeds governed limits",
            )
        if isinstance(item, Mapping):
            if len(item) > 1000:
                raise FinanceContractError(
                    "FIN2_PROFILE_RESOURCE_LIMIT",
                    "$",
                    "profile object is too large",
                )
            for key, nested in item.items():
                if not isinstance(key, str) or len(key) > 120:
                    raise FinanceContractError(
                        "FIN2_PROFILE_RESOURCE_LIMIT",
                        "$",
                        "profile key is invalid or too long",
                    )
                string_units += len(key)
                stack.append((nested, depth + 1))
        elif isinstance(item, Sequence) and not isinstance(
            item,
            (str, bytes, bytearray),
        ):
            if len(item) > 10000:
                raise FinanceContractError(
                    "FIN2_PROFILE_RESOURCE_LIMIT",
                    "$",
                    "profile array is too large",
                )
            stack.extend((nested, depth + 1) for nested in item)
        elif isinstance(item, str):
            if len(item) > 2048:
                raise FinanceContractError(
                    "FIN2_PROFILE_RESOURCE_LIMIT",
                    "$",
                    "profile string is too long",
                )
            string_units += len(item)
        elif isinstance(item, float):
            raise FinanceContractError(
                "FIN2_PROFILE_NUMBER_TYPE",
                "$",
                "binary float is not allowed in risk profiles",
            )
        elif not isinstance(item, (int, bool, type(None))):
            raise FinanceContractError(
                "FIN2_PROFILE_VALUE_TYPE",
                "$",
                "profile contains unsupported value type",
            )
        if string_units > 500000:
            raise FinanceContractError(
                "FIN2_PROFILE_RESOURCE_LIMIT",
                "$",
                "profile text budget exceeded",
            )


def _mapping(value: Any, field_ref: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise FinanceContractError(
            "FIN2_PROFILE_OBJECT",
            field_ref,
            "value must be an object",
        )
    return value


def _sequence(
    value: Any,
    field_ref: str,
    *,
    minimum: int,
    maximum: int,
) -> Sequence[Any]:
    if (
        not isinstance(value, Sequence)
        or isinstance(value, (str, bytes, bytearray))
        or not minimum <= len(value) <= maximum
    ):
        raise FinanceContractError(
            "FIN2_PROFILE_ARRAY",
            field_ref,
            f"array length must be {minimum}..{maximum}",
        )
    return value


def _require_exact_fields(
    row: Mapping[str, Any],
    fields: frozenset[str] | set[str],
    field_ref: str,
) -> None:
    _require_fields(row, set(fields), set(fields), field_ref)


def _require_fields(
    row: Mapping[str, Any],
    required: set[str],
    allowed: set[str],
    field_ref: str,
) -> None:
    missing = required.difference(row)
    if missing:
        raise FinanceContractError(
            "FIN2_PROFILE_REQUIRED_FIELD",
            field_ref,
            f"missing fields: {','.join(sorted(missing))}",
        )
    unknown = set(row).difference(allowed)
    if unknown:
        raise FinanceContractError(
            "FIN2_PROFILE_UNKNOWN_FIELD",
            field_ref,
            f"unknown fields: {','.join(sorted(unknown))}",
        )


def _text(value: Any, field_ref: str, *, maximum: int) -> str:
    if (
        not isinstance(value, str)
        or not value.strip()
        or len(value) > maximum
    ):
        raise FinanceContractError(
            "FIN2_PROFILE_TEXT",
            field_ref,
            "value must be a bounded non-empty string",
        )
    return value


def _integer(
    value: Any,
    field_ref: str,
    *,
    minimum: int,
    maximum: int,
) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not minimum <= value <= maximum
    ):
        raise FinanceContractError(
            "FIN2_PROFILE_INTEGER",
            field_ref,
            f"value must be an integer in {minimum}..{maximum}",
        )
    return value


def _hash(value: Any, field_ref: str) -> str:
    if not isinstance(value, str) or _HASH.fullmatch(value) is None:
        raise FinanceContractError(
            "FIN2_PROFILE_HASH",
            field_ref,
            "value must be sha256-prefixed lowercase hex",
        )
    return value


def _currency(value: Any, field_ref: str) -> str:
    if not isinstance(value, str) or _CURRENCY.fullmatch(value) is None:
        raise FinanceContractError(
            "FIN2_PROFILE_CURRENCY",
            field_ref,
            "currency must be ISO-4217 alpha-3",
        )
    return value


def _date(value: Any, field_ref: str) -> date:
    if not isinstance(value, str) or _DATE_FORMAT.fullmatch(value) is None:
        raise FinanceContractError(
            "FIN2_PROFILE_DATE",
            field_ref,
            "date must be ISO-8601 YYYY-MM-DD",
        )
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise FinanceContractError(
            "FIN2_PROFILE_DATE",
            field_ref,
            "date must be ISO-8601 YYYY-MM-DD",
        ) from exc


def _datetime(value: Any, field_ref: str) -> datetime:
    if not isinstance(value, str) or _DATETIME_FORMAT.fullmatch(value) is None:
        raise FinanceContractError(
            "FIN2_PROFILE_DATETIME",
            field_ref,
            "timestamp must be RFC-3339 with uppercase T and timezone",
        )
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise FinanceContractError(
            "FIN2_PROFILE_DATETIME",
            field_ref,
            "timestamp must be ISO-8601",
        ) from exc
    if parsed.tzinfo is None:
        raise FinanceContractError(
            "FIN2_PROFILE_DATETIME",
            field_ref,
            "timestamp must include timezone",
        )
    return parsed
