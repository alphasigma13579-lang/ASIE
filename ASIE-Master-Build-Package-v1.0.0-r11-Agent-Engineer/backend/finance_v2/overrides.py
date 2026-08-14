from __future__ import annotations

from decimal import Decimal, ROUND_HALF_EVEN, localcontext
from typing import Any

from .contracts import (
    FinanceContractError,
    ServerBinding,
    ValidatedFinanceInput,
    parse_decimal,
    parse_scenario_target,
    validate_finance_input,
)


def derive_validated_input(
    validated: ValidatedFinanceInput,
    overrides: list[dict[str, Any]],
    field_ref: str,
) -> ValidatedFinanceInput:
    """Apply governed overrides to a fresh input document and re-admit it."""
    document = validated.thaw()
    for index, override in enumerate(overrides):
        apply_override(document, override, f"{field_ref}[{index}]")
    metadata = document["metadata"]
    return validate_finance_input(
        document,
        binding=ServerBinding(
            organization_id=validated.organization_id,
            project_id=validated.project_id,
            run_id=validated.run_id,
            approved_manifest_id=metadata["approved_manifest_id"],
            approved_manifest_hash=metadata["approved_manifest_hash"],
            policy_ref=metadata["policy_ref"],
        ),
    )


def apply_override(
    document: dict[str, Any],
    override: dict[str, Any],
    field_ref: str,
) -> None:
    target_ref = override["target_ref"]
    target = parse_scenario_target(target_ref, f"{field_ref}.target_ref")
    locations = _target_locations(document, target, field_ref)
    value = parse_decimal(override["value"], f"{field_ref}.value")
    for container, key, value_ref in locations:
        if key not in container:
            raise FinanceContractError(
                "FIN2_SCENARIO_TARGET_MISSING",
                value_ref,
                "target field is absent",
            )
        current = parse_decimal(container[key], value_ref)
        operation = override["operation"]
        if operation == "replace":
            updated = value
        else:
            with localcontext() as context:
                context.prec = max(
                    50,
                    len(current.as_tuple().digits)
                    + len(value.as_tuple().digits)
                    + abs(current.as_tuple().exponent)
                    + abs(value.as_tuple().exponent)
                    + 20,
                )
                updated = (
                    current * value
                    if operation == "multiply"
                    else current + value
                )
        container[key] = _decimal_text(updated, value_ref)


def _target_locations(
    document: dict[str, Any],
    target: dict[str, str],
    field_ref: str,
) -> tuple[tuple[dict[str, Any], str, str], ...]:
    if "revenue_id" in target:
        row = _find(
            document["revenue_streams"],
            "stream_id",
            target["revenue_id"],
            field_ref,
        )
        return _series_locations(
            row,
            target["revenue_series"],
            target["revenue_period"],
            field_ref,
        )
    if "opex_id" in target:
        row = _find(
            document["operating_costs"],
            "cost_id",
            target["opex_id"],
            field_ref,
        )
        return _series_locations(
            row,
            "schedule",
            target["opex_period"],
            field_ref,
        )
    if "asset_id" in target:
        row = _find(
            document["capex_assets"],
            "asset_id",
            target["asset_id"],
            field_ref,
        )
        return ((row, target["asset_field"], field_ref),)
    if "working_field" in target:
        return ((document["working_capital"], target["working_field"], field_ref),)
    if "valuation_field" in target:
        return ((document["valuation_policy"], target["valuation_field"], field_ref),)
    if "tranche_id" in target:
        row = _find(
            document["financing"]["debt_tranches"],
            "tranche_id",
            target["tranche_id"],
            field_ref,
        )
        return ((row, target["tranche_field"], field_ref),)
    raise FinanceContractError(
        "FIN2_SCENARIO_TARGET",
        field_ref,
        "unsupported target",
    )


def _series_locations(
    row: dict[str, Any],
    series_name: str,
    period_selector: str,
    field_ref: str,
) -> tuple[tuple[dict[str, Any], str, str], ...]:
    series = row.get(series_name)
    if not isinstance(series, list):
        raise FinanceContractError(
            "FIN2_SCENARIO_TARGET_MISSING",
            field_ref,
            "target series is absent",
        )
    points = [
        point
        for point in series
        if period_selector == "*" or point.get("period") == period_selector
    ]
    if not points:
        raise FinanceContractError(
            "FIN2_SCENARIO_TARGET_MISSING",
            field_ref,
            "target period is absent",
        )
    return tuple((point, "value", field_ref) for point in points)


def _find(
    rows: list[dict[str, Any]],
    id_field: str,
    expected: str,
    field_ref: str,
) -> dict[str, Any]:
    for row in rows:
        if row.get(id_field) == expected:
            return row
    raise FinanceContractError(
        "FIN2_SCENARIO_TARGET_MISSING",
        field_ref,
        "target id is absent",
    )


def _decimal_text(value: Decimal, field_ref: str) -> str:
    if not value.is_finite():
        raise FinanceContractError(
            "FIN2_SCENARIO_VALUE",
            field_ref,
            "scenario arithmetic must remain finite",
        )
    with localcontext() as context:
        context.prec = max(
            50,
            len(value.as_tuple().digits) + abs(value.as_tuple().exponent) + 20,
        )
        if value.as_tuple().exponent < -8:
            value = value.quantize(
                Decimal("0.00000001"),
                rounding=ROUND_HALF_EVEN,
            )
    if value == 0:
        return "0"
    text = format(value, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text
