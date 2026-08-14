from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from .contracts import (
    FinanceContractError,
    ValidatedFinanceInput,
    parse_decimal,
)
from .overrides import derive_validated_input
from .result import ENGINE_VERSION
from .risk_profiles import (
    ResolvedRiskProfileBinding,
    ValidatedRiskProfile,
    profile_content_hash,
)
from .serialization import canonical_sha256
from .statements import build_financial_model


SENSITIVITY_ENGINE_VERSION = "1.0.0-dark"
_CANONICALIZATION_POLICY = "finance-v2-canonical-json.v1"
_PROFILE_SCHEMA = "finance-sensitivity-profile.v1"
_EXECUTION_SCOPE = "dark_sensitivity_v1"
_HARD_MAXIMUM_CELLS = 441


@dataclass(frozen=True, slots=True)
class SensitivityExecutionBinding:
    risk_profile_binding: ResolvedRiskProfileBinding
    authoritative_admission: bool
    organization_id: str
    project_id: str
    run_id: str
    owner_organization_id: str | None
    scope_kind: str
    profile_schema_version: str
    profile_id: str
    profile_version: str
    profile_hash: str
    registry_snapshot_hash: str
    approved_manifest_id: str
    approved_manifest_hash: str
    policy_ref: str
    policy_version: str
    policy_hash: str
    finance_input_hash: str
    currency: str
    archetype_id: str
    archetype_version: str
    archetype_registry_hash: str
    execution_scope: str = _EXECUTION_SCOPE

@dataclass(frozen=True, slots=True)
class PreparedSensitivityRun:
    validated_input: ValidatedFinanceInput
    profile: ValidatedRiskProfile
    binding: SensitivityExecutionBinding
    profile_document: dict[str, Any]
    execution_scope: str = _EXECUTION_SCOPE
    runtime_eligible: bool = False


@dataclass(frozen=True, slots=True)
class SensitivityAxis:
    axis_id: str
    target_ref: str
    operation: str
    values: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "axis_id": self.axis_id,
            "target_ref": self.target_ref,
            "operation": self.operation,
            "values": list(self.values),
        }


@dataclass(frozen=True, slots=True)
class SensitivityBlocker:
    code: str
    severity: str
    field_ref: str
    stage: str
    cause_code: str
    message_ar: str

    def as_dict(self) -> dict[str, str]:
        return {
            "code": self.code,
            "severity": self.severity,
            "field_ref": self.field_ref,
            "stage": self.stage,
            "cause_code": self.cause_code,
            "message_ar": self.message_ar,
        }


@dataclass(frozen=True, slots=True)
class SensitivityCell:
    row_index: int
    column_index: int
    row_value: str
    column_value: str
    derived_input_hash: str
    _metrics: tuple[tuple[str, str | None], ...]

    @property
    def metrics(self) -> dict[str, str | None]:
        return dict(self._metrics)

    def as_dict(self) -> dict[str, Any]:
        return {
            "row_index": self.row_index,
            "column_index": self.column_index,
            "row_value": self.row_value,
            "column_value": self.column_value,
            "derived_input_hash": self.derived_input_hash,
            "metrics": dict(self._metrics),
        }


@dataclass(frozen=True, slots=True)
class SensitivityEvaluation:
    status: str
    organization_id: str
    project_id: str
    run_id: str
    finance_input_hash: str
    profile_schema_version: str
    profile_id: str
    profile_version: str
    profile_hash: str
    dependency_hashes: tuple[tuple[str, str], ...]
    registry_snapshot_hash: str
    approved_manifest_id: str
    approved_manifest_hash: str
    policy_ref: str
    policy_version: str
    policy_hash: str
    finance_engine_version: str
    sensitivity_engine_version: str
    canonicalization_policy: str
    axis_ids: tuple[str, str]
    _axes: tuple[SensitivityAxis, SensitivityAxis]
    metric_ids: tuple[str, ...]
    cell_count: int
    cells: tuple[SensitivityCell, ...]
    _blockers: tuple[SensitivityBlocker, ...]
    result_hash: str

    @property
    def axes(self) -> tuple[dict[str, Any], dict[str, Any]]:
        return tuple(axis.as_dict() for axis in self._axes)  # type: ignore[return-value]

    @property
    def blockers(self) -> tuple[dict[str, str], ...]:
        return tuple(blocker.as_dict() for blocker in self._blockers)

    def as_dict(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": "finance-sensitivity-result.v1",
            "status": self.status,
            "execution_scope": "dark_build",
            "snapshot_eligible": False,
            "organization_id": self.organization_id,
            "project_id": self.project_id,
            "run_id": self.run_id,
            "finance_input_hash": self.finance_input_hash,
            "profile": {
                "schema_version": self.profile_schema_version,
                "profile_id": self.profile_id,
                "version": self.profile_version,
                "content_hash": self.profile_hash,
                "dependency_hashes": [
                    {"ref": ref, "content_hash": content_hash}
                    for ref, content_hash in self.dependency_hashes
                ],
                "registry_snapshot_hash": self.registry_snapshot_hash,
                "approved_manifest_id": self.approved_manifest_id,
                "approved_manifest_hash": self.approved_manifest_hash,
                "policy_ref": self.policy_ref,
                "policy_version": self.policy_version,
                "policy_hash": self.policy_hash,
            },
            "finance_engine_version": self.finance_engine_version,
            "sensitivity_engine_version": self.sensitivity_engine_version,
            "canonicalization_policy": self.canonicalization_policy,
            "axis_ids": list(self.axis_ids),
            "axes": [axis.as_dict() for axis in self._axes],
            "metric_ids": list(self.metric_ids),
            "cell_count": self.cell_count,
            "cells": [cell.as_dict() for cell in self.cells],
            "blockers": [blocker.as_dict() for blocker in self._blockers],
        }
        if include_hash:
            payload["result_hash"] = self.result_hash
        return payload


def prepare_sensitivity_run(
    validated_input: ValidatedFinanceInput,
    profile: ValidatedRiskProfile,
    *,
    binding: SensitivityExecutionBinding,
) -> PreparedSensitivityRun:
    if not isinstance(validated_input, ValidatedFinanceInput):
        raise FinanceContractError(
            "FIN2_SENSITIVITY_INPUT_TYPE",
            "validated_input",
            "sensitivity requires a server-validated finance input",
        )
    if not isinstance(profile, ValidatedRiskProfile):
        raise FinanceContractError(
            "FIN2_SENSITIVITY_PROFILE_TYPE",
            "profile",
            "sensitivity requires an admitted risk profile",
        )
    if not isinstance(binding, SensitivityExecutionBinding):
        raise FinanceContractError(
            "FIN2_SENSITIVITY_BINDING_TYPE",
            "binding",
            "sensitivity requires a trusted execution binding",
        )
    _validate_risk_admission_binding(binding)
    if binding.execution_scope != _EXECUTION_SCOPE or not binding.authoritative_admission:
        raise FinanceContractError(
            "FIN2_SENSITIVITY_ADMISSION",
            "binding",
            "dark sensitivity requires authoritative server admission provenance",
        )
    if profile.execution_ready:
        raise FinanceContractError(
            "FIN2_SENSITIVITY_EXECUTION_STATE",
            "profile.execution_ready",
            "C3C can consume admitted profiles only while their general execution state remains false",
        )
    if profile.kind != "sensitivity" or profile.status != "approved":
        raise FinanceContractError(
            "FIN2_SENSITIVITY_PROFILE_KIND",
            "profile",
            "only an approved sensitivity profile is accepted",
        )
    _require_equal(profile.profile_id, binding.profile_id, "binding.profile_id")
    _require_equal(profile.version, binding.profile_version, "binding.profile_version")
    _require_equal(profile.content_hash, binding.profile_hash, "binding.profile_hash")
    _require_equal(
        profile.dependency_hashes,
        binding.risk_profile_binding.dependency_hashes,
        "binding.risk_profile_binding.dependency_hashes",
    )
    _require_equal(
        profile.registry_snapshot_hash,
        binding.registry_snapshot_hash,
        "binding.registry_snapshot_hash",
    )
    _require_equal(
        profile.approved_manifest_id,
        binding.approved_manifest_id,
        "binding.approved_manifest_id",
    )
    _require_equal(
        profile.approved_manifest_hash,
        binding.approved_manifest_hash,
        "binding.approved_manifest_hash",
    )
    _require_equal(profile.policy_ref, binding.policy_ref, "binding.policy_ref")
    _require_equal(profile.policy_version, binding.policy_version, "binding.policy_version")
    _require_equal(profile.policy_hash, binding.policy_hash, "binding.policy_hash")
    _require_equal(validated_input.input_hash, binding.finance_input_hash, "binding.finance_input_hash")
    _require_equal(validated_input.organization_id, binding.organization_id, "binding.organization_id")
    _require_equal(validated_input.project_id, binding.project_id, "binding.project_id")
    _require_equal(validated_input.run_id, binding.run_id, "binding.run_id")
    if binding.scope_kind not in {"organization", "global"}:
        raise FinanceContractError(
            "FIN2_SENSITIVITY_TENANT",
            "binding.scope_kind",
            "unsupported sensitivity profile scope",
        )
    if binding.scope_kind == "organization" and binding.owner_organization_id != binding.organization_id:
        raise FinanceContractError(
            "FIN2_SENSITIVITY_TENANT",
            "binding.owner_organization_id",
            "organization scope owner must equal the trusted organization",
        )
    if binding.scope_kind == "global" and binding.owner_organization_id is not None:
        raise FinanceContractError(
            "FIN2_SENSITIVITY_TENANT",
            "binding.owner_organization_id",
            "global scope must not carry tenant ownership",
        )

    profile_document = profile.thaw()
    if profile_document.get("schema_version") != _PROFILE_SCHEMA:
        raise FinanceContractError(
            "FIN2_SENSITIVITY_PROFILE_KIND",
            "$.schema_version",
            "profile document is not a sensitivity profile",
        )
    if (
        profile_document.get("content_hash") != profile.content_hash
        or profile_content_hash(profile_document) != profile.content_hash
    ):
        raise FinanceContractError(
            "FIN2_SENSITIVITY_HASH_MISMATCH",
            "$.content_hash",
            "profile canonical document no longer matches admitted content hash",
        )
    _require_equal(
        profile_document.get("profile_id"),
        binding.profile_id,
        "$.profile_id",
    )
    _require_equal(profile_document.get("version"), binding.profile_version, "$.version")

    input_document = validated_input.thaw()
    input_document_hash = canonical_sha256(input_document)
    _require_equal(
        input_document_hash,
        validated_input.input_hash,
        "validated_input.input_hash",
    )
    _require_equal(
        input_document_hash,
        binding.finance_input_hash,
        "binding.finance_input_hash",
    )
    metadata = input_document["metadata"]
    _require_equal(
        input_document.get("organization_id"),
        validated_input.organization_id,
        "$.organization_id",
    )
    _require_equal(
        input_document.get("project_id"),
        validated_input.project_id,
        "$.project_id",
    )
    _require_equal(
        input_document.get("run_id"),
        validated_input.run_id,
        "$.run_id",
    )
    _require_equal(
        input_document.get("currency"),
        validated_input.currency,
        "$.currency",
    )
    _require_equal(metadata.get("approved_manifest_id"), binding.approved_manifest_id, "$.metadata.approved_manifest_id")
    _require_equal(metadata.get("approved_manifest_hash"), binding.approved_manifest_hash, "$.metadata.approved_manifest_hash")
    _require_equal(metadata.get("policy_ref"), binding.policy_ref, "$.metadata.policy_ref")
    _require_equal(validated_input.currency, binding.currency, "binding.currency")
    _require_equal(profile_document.get("currency"), binding.currency, "$.currency")
    _validate_archetype_match(
        input_document["archetype_ref"],
        profile_document["archetype_ref"],
        binding,
    )
    return PreparedSensitivityRun(
        validated_input=validated_input,
        profile=profile,
        binding=binding,
        profile_document=profile_document,
    )


def evaluate_sensitivity(
    prepared: PreparedSensitivityRun,
) -> SensitivityEvaluation:
    if not isinstance(prepared, PreparedSensitivityRun):
        raise FinanceContractError(
            "FIN2_SENSITIVITY_PREPARED_TYPE",
            "prepared",
            "evaluate_sensitivity requires a prepared server-bound run",
        )
    if prepared.execution_scope != _EXECUTION_SCOPE or prepared.runtime_eligible:
        raise FinanceContractError(
            "FIN2_SENSITIVITY_PREPARED_SCOPE",
            "prepared",
            "prepared sensitivity capability is dark-only and never runtime eligible",
        )
    prepared = prepare_sensitivity_run(
        prepared.validated_input,
        prepared.profile,
        binding=prepared.binding,
    )
    document = prepared.profile_document
    raw_axes = document["axes"]
    if len(raw_axes) != 2:
        raise FinanceContractError(
            "FIN2_SENSITIVITY_AXES",
            "$.axes",
            "sensitivity profile must contain exactly two axes",
        )
    axes = _canonical_axes(raw_axes)
    metric_ids = tuple(document["metric_ids"])
    maximum_cells = int(document["maximum_cells"])
    cell_count = len(axes[0]["values"]) * len(axes[1]["values"])
    if cell_count > maximum_cells or cell_count > _HARD_MAXIMUM_CELLS:
        raise FinanceContractError(
            "FIN2_SENSITIVITY_CELL_LIMIT",
            "$.maximum_cells",
            "effective cell count exceeds the governed limit",
        )

    fixed = [
        {
            "target_ref": item["target_ref"],
            "operation": item["operation"],
            "value": item["value"],
        }
        for item in document["fixed_overrides"]
    ]
    cells: list[SensitivityCell] = []
    for row_index, row_value in enumerate(axes[0]["values"]):
        for column_index, column_value in enumerate(axes[1]["values"]):
            overrides = [
                *fixed,
                {
                    "target_ref": axes[0]["target_ref"],
                    "operation": axes[0]["operation"],
                    "value": row_value,
                },
                {
                    "target_ref": axes[1]["target_ref"],
                    "operation": axes[1]["operation"],
                    "value": column_value,
                },
            ]
            try:
                derived = derive_validated_input(
                    prepared.validated_input,
                    overrides,
                    f"$.sensitivity.cells[{row_index}][{column_index}]",
                )
            except FinanceContractError as exc:
                return _not_ready(
                    prepared,
                    axes,
                    metric_ids,
                    cell_count,
                    row_index,
                    column_index,
                    "input_derivation",
                    exc.code,
                )
            try:
                model = build_financial_model(derived)
            except FinanceContractError as exc:
                return _not_ready(
                    prepared,
                    axes,
                    metric_ids,
                    cell_count,
                    row_index,
                    column_index,
                    "model_build",
                    exc.code,
                )
            if model.source_input_hash != derived.input_hash:
                return _not_ready(
                    prepared,
                    axes,
                    metric_ids,
                    cell_count,
                    row_index,
                    column_index,
                    "model_invariant",
                    "FIN2_MODEL_INPUT_MISMATCH",
                )
            if model.status != "ready":
                cause_code = (
                    model.blockers[0]["code"]
                    if model.blockers
                    else "FIN2_SENSITIVITY_MODEL_NOT_READY"
                )
                return _not_ready(
                    prepared,
                    axes,
                    metric_ids,
                    cell_count,
                    row_index,
                    column_index,
                    "model_invariant",
                    cause_code,
                )
            metrics: dict[str, str | None] = {}
            for metric_id in metric_ids:
                if metric_id not in model.metrics:
                    return _not_ready(
                        prepared,
                        axes,
                        metric_ids,
                        cell_count,
                        row_index,
                        column_index,
                        "metric_projection",
                        "FIN2_SENSITIVITY_METRIC_UNAVAILABLE",
                    )
                value = model.metrics[metric_id]
                try:
                    metrics[metric_id] = (
                        None if value is None else _decimal_text(value)
                    )
                except FinanceContractError as exc:
                    return _not_ready(
                        prepared,
                        axes,
                        metric_ids,
                        cell_count,
                        row_index,
                        column_index,
                        "metric_projection",
                        exc.code,
                    )
            cells.append(
                SensitivityCell(
                    row_index=row_index,
                    column_index=column_index,
                    row_value=row_value,
                    column_value=column_value,
                    derived_input_hash=derived.input_hash,
                    _metrics=tuple(metrics.items()),
                )
            )
            del model
    return _evaluation(
        prepared,
        axes,
        metric_ids,
        cell_count,
        tuple(cells),
        (),
        "dark_ready",
    )


def _canonical_axes(
    axes: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    canonical_axes: list[dict[str, Any]] = []
    for axis_index, axis in enumerate(axes):
        canonical_values = [
            _decimal_text(
                parse_decimal(
                    value,
                    f"$.axes[{axis_index}].values[{value_index}]",
                )
            )
            for value_index, value in enumerate(axis["values"])
        ]
        if len(set(canonical_values)) != len(canonical_values):
            raise FinanceContractError(
                "FIN2_SENSITIVITY_AXIS_DUPLICATE",
                f"$.axes[{axis_index}].values",
                "axis values must remain unique after canonical decimal normalization",
            )
        canonical_axes.append(
            {
                **axis,
                "values": canonical_values,
            }
        )
    return canonical_axes


def _not_ready(
    prepared: PreparedSensitivityRun,
    axes: list[dict[str, Any]],
    metric_ids: tuple[str, ...],
    cell_count: int,
    row_index: int,
    column_index: int,
    stage: str,
    cause_code: str,
) -> SensitivityEvaluation:
    blocker = SensitivityBlocker(
        code="FIN2_SENSITIVITY_CELL_NOT_READY",
        severity="high",
        field_ref=f"$.cells[{row_index}][{column_index}]",
        stage=stage,
        cause_code=cause_code,
        message_ar=f"فشلت خلية الحساسية الحتمية بسبب {cause_code}.",
    )
    return _evaluation(
        prepared,
        axes,
        metric_ids,
        cell_count,
        (),
        (blocker,),
        "not_ready",
    )


def _evaluation(
    prepared: PreparedSensitivityRun,
    axes: list[dict[str, Any]],
    metric_ids: tuple[str, ...],
    cell_count: int,
    cells: tuple[SensitivityCell, ...],
    blockers: tuple[SensitivityBlocker, ...],
    status: str,
) -> SensitivityEvaluation:
    base = dict(
        status=status,
        organization_id=prepared.validated_input.organization_id,
        project_id=prepared.validated_input.project_id,
        run_id=prepared.validated_input.run_id,
        finance_input_hash=prepared.validated_input.input_hash,
        profile_schema_version=prepared.profile_document["schema_version"],
        profile_id=prepared.profile.profile_id,
        profile_version=prepared.profile.version,
        profile_hash=prepared.profile.content_hash,
        dependency_hashes=prepared.binding.risk_profile_binding.dependency_hashes,
        registry_snapshot_hash=prepared.profile.registry_snapshot_hash,
        approved_manifest_id=prepared.profile.approved_manifest_id,
        approved_manifest_hash=prepared.profile.approved_manifest_hash,
        policy_ref=prepared.profile.policy_ref,
        policy_version=prepared.profile.policy_version,
        policy_hash=prepared.profile.policy_hash,
        finance_engine_version=ENGINE_VERSION,
        sensitivity_engine_version=SENSITIVITY_ENGINE_VERSION,
        canonicalization_policy=_CANONICALIZATION_POLICY,
        axis_ids=(axes[0]["axis_id"], axes[1]["axis_id"]),
        _axes=(
            SensitivityAxis(
                axis_id=axes[0]["axis_id"],
                target_ref=axes[0]["target_ref"],
                operation=axes[0]["operation"],
                values=tuple(axes[0]["values"]),
            ),
            SensitivityAxis(
                axis_id=axes[1]["axis_id"],
                target_ref=axes[1]["target_ref"],
                operation=axes[1]["operation"],
                values=tuple(axes[1]["values"]),
            ),
        ),
        metric_ids=metric_ids,
        cell_count=cell_count,
        cells=cells,
        _blockers=blockers,
    )
    provisional = SensitivityEvaluation(**base, result_hash="")
    _validate_evaluation_invariants(provisional)
    result_hash = canonical_sha256(provisional.as_dict(include_hash=False))
    return SensitivityEvaluation(**base, result_hash=result_hash)


def _validate_evaluation_invariants(
    evaluation: SensitivityEvaluation,
) -> None:
    expected_cell_count = (
        len(evaluation._axes[0].values) * len(evaluation._axes[1].values)
    )
    if evaluation.cell_count != expected_cell_count:
        raise FinanceContractError(
            "FIN2_SENSITIVITY_RESULT_INVARIANT",
            "$.cell_count",
            "cell_count must equal the complete Cartesian axis size",
        )
    if evaluation.status == "dark_ready":
        expected_grid = tuple(
            (
                row_index,
                column_index,
                row_value,
                column_value,
            )
            for row_index, row_value in enumerate(evaluation._axes[0].values)
            for column_index, column_value in enumerate(
                evaluation._axes[1].values
            )
        )
        actual_grid = tuple(
            (
                cell.row_index,
                cell.column_index,
                cell.row_value,
                cell.column_value,
            )
            for cell in evaluation.cells
        )
        if actual_grid != expected_grid:
            raise FinanceContractError(
                "FIN2_SENSITIVITY_RESULT_INVARIANT",
                "$.cells",
                "dark_ready cells must be the complete ordered Cartesian grid",
            )
        if evaluation._blockers:
            raise FinanceContractError(
                "FIN2_SENSITIVITY_RESULT_INVARIANT",
                "$.blockers",
                "dark_ready results cannot contain blockers",
            )
        if any(
            tuple(metric_id for metric_id, _ in cell._metrics)
            != evaluation.metric_ids
            for cell in evaluation.cells
        ):
            raise FinanceContractError(
                "FIN2_SENSITIVITY_RESULT_INVARIANT",
                "$.cells[*].metrics",
                "every dark_ready cell must contain the complete ordered metric set",
            )
        return
    if evaluation.status == "not_ready":
        if evaluation.cells or len(evaluation._blockers) != 1:
            raise FinanceContractError(
                "FIN2_SENSITIVITY_RESULT_INVARIANT",
                "$",
                "not_ready results must be atomic with one blocker and no cells",
            )
        return
    raise FinanceContractError(
        "FIN2_SENSITIVITY_RESULT_INVARIANT",
        "$.status",
        "unsupported sensitivity result status",
    )


def _validate_risk_admission_binding(binding: SensitivityExecutionBinding) -> None:
    source = binding.risk_profile_binding
    if not isinstance(source, ResolvedRiskProfileBinding) or not source.authoritative:
        raise FinanceContractError(
            "FIN2_SENSITIVITY_ADMISSION",
            "binding.risk_profile_binding",
            "sensitivity execution must retain an authoritative admission binding",
        )
    expected = {
        "expected_schema_version": binding.profile_schema_version,
        "expected_profile_id": binding.profile_id,
        "expected_version": binding.profile_version,
        "expected_content_hash": binding.profile_hash,
        "registry_snapshot_hash": binding.registry_snapshot_hash,
        "organization_id": binding.organization_id,
        "scope_kind": binding.scope_kind,
        "owner_organization_id": binding.owner_organization_id,
        "approved_manifest_id": binding.approved_manifest_id,
        "approved_manifest_hash": binding.approved_manifest_hash,
        "policy_ref": binding.policy_ref,
        "policy_version": binding.policy_version,
        "policy_hash": binding.policy_hash,
    }
    for field, value in expected.items():
        _require_equal(getattr(source, field), value, f"binding.risk_profile_binding.{field}")
    if binding.profile_schema_version != _PROFILE_SCHEMA:
        raise FinanceContractError(
            "FIN2_SENSITIVITY_ADMISSION",
            "binding.profile_schema_version",
            "sensitivity requires the governed sensitivity profile schema",
        )
    profile_in_manifest = any(
        item.schema_version == binding.profile_schema_version
        and item.profile_id == binding.profile_id
        and item.version == binding.profile_version
        and item.content_hash == binding.profile_hash
        for item in source.manifest_profiles
    )
    policy_in_manifest = any(
        item.profile_id == binding.policy_ref
        and item.version == binding.policy_version
        and item.content_hash == binding.policy_hash
        for item in source.manifest_profiles
    )
    if not profile_in_manifest or not policy_in_manifest:
        raise FinanceContractError(
            "FIN2_SENSITIVITY_ADMISSION",
            "binding.risk_profile_binding.manifest_profiles",
            "trusted manifest must include the exact admitted profile and policy",
        )
    if binding.scope_kind == "global" and not source.allow_global:
        raise FinanceContractError(
            "FIN2_SENSITIVITY_TENANT",
            "binding.risk_profile_binding.allow_global",
            "global sensitivity profiles require explicit trusted global admission",
        )

def _validate_archetype_match(
    input_archetype: dict[str, Any],
    profile_archetype: dict[str, Any],
    binding: SensitivityExecutionBinding,
) -> None:
    expected = {
        "archetype_id": binding.archetype_id,
        "version": binding.archetype_version,
        "registry_hash": binding.archetype_registry_hash,
    }
    for key, value in expected.items():
        _require_equal(input_archetype.get(key), value, f"$.archetype_ref.{key}")
        _require_equal(profile_archetype.get(key), value, f"$.archetype_ref.{key}")


def _require_equal(actual: Any, expected: Any, field_ref: str) -> None:
    if actual != expected:
        raise FinanceContractError(
            "FIN2_SENSITIVITY_BINDING_MISMATCH",
            field_ref,
            "value does not match trusted sensitivity execution binding",
        )


def _decimal_text(value: Decimal) -> str:
    if not value.is_finite():
        raise FinanceContractError(
            "FIN2_SENSITIVITY_METRIC",
            "$.metrics",
            "sensitivity metric must remain finite",
        )
    if value == 0:
        return "0"
    text = format(value, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text
