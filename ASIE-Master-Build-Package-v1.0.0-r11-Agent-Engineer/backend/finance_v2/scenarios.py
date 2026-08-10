from __future__ import annotations

from dataclasses import dataclass
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
from .model import FinancialModel
from .statements import build_financial_model


@dataclass(frozen=True, slots=True)
class ScenarioEvaluation:
    scenario_id: str
    kind: str
    status: str
    input_hash: str
    override_refs: tuple[str, ...]
    metrics: dict[str, Decimal | None]
    blockers: tuple[dict[str, str], ...]
    simulation_summary: dict[str, Any] | None = None


def evaluate_scenarios(
    validated: ValidatedFinanceInput,
    baseline_model: FinancialModel,
) -> tuple[ScenarioEvaluation, ...]:
    document = validated.thaw()
    output: list[ScenarioEvaluation] = []
    for index, scenario in enumerate(document["scenarios"]):
        scenario_id = scenario["scenario_id"]
        kind = scenario["kind"]
        override_refs = tuple(
            item["target_ref"] for item in scenario["overrides"]
        )
        if kind == "baseline":
            output.append(
                ScenarioEvaluation(
                    scenario_id=scenario_id,
                    kind=kind,
                    status=baseline_model.status,
                    input_hash=validated.input_hash,
                    override_refs=(),
                    metrics=dict(baseline_model.metrics),
                    blockers=(),
                )
            )
            continue

        if kind == "simulation":
            simulation = scenario["simulation"]
            blocker = _blocker(
                "FIN2_SIMULATION_NOT_READY",
                f"$.scenarios[{index}].simulation",
                "المحاكاة المعيّرة والارتباطات لم تُنفذ بعد؛ لم تُحسب نتيجة صورية.",
            )
            output.append(
                ScenarioEvaluation(
                    scenario_id=scenario_id,
                    kind=kind,
                    status="not_ready",
                    input_hash=validated.input_hash,
                    override_refs=(),
                    metrics={},
                    blockers=(blocker,),
                    simulation_summary={
                        "seed": simulation["seed"],
                        "iterations": simulation["iterations"],
                        "distribution_profile_ref": simulation[
                            "distribution_profile_ref"
                        ],
                        **(
                            {
                                "correlation_profile_ref": simulation[
                                    "correlation_profile_ref"
                                ]
                            }
                            if "correlation_profile_ref" in simulation
                            else {}
                        ),
                        "quantiles": {},
                    },
                )
            )
            continue

        try:
            scenario_document = validated.thaw()
            for override_index, override in enumerate(scenario["overrides"]):
                _apply_override(
                    scenario_document,
                    override,
                    f"$.scenarios[{index}].overrides[{override_index}]",
                )
            scenario_validated = validate_finance_input(
                scenario_document,
                binding=_binding(validated, scenario_document),
            )
            scenario_model = build_financial_model(scenario_validated)
        except FinanceContractError as exc:
            blocker = _blocker(
                "FIN2_SCENARIO_INVALID",
                f"$.scenarios[{index}]",
                f"فشل تطبيق السيناريو الحتمي وفق العقد: {exc.code}.",
            )
            output.append(
                ScenarioEvaluation(
                    scenario_id=scenario_id,
                    kind=kind,
                    status="invalid",
                    input_hash=validated.input_hash,
                    override_refs=override_refs,
                    metrics={},
                    blockers=(blocker,),
                )
            )
            continue

        blockers: tuple[dict[str, str], ...] = ()
        if scenario_model.status != "ready":
            blockers = tuple(
                _blocker(
                    "FIN2_SCENARIO_MODEL_NOT_READY",
                    f"$.scenarios[{index}]",
                    (
                        "أنتج السيناريو نموذجاً غير جاهز بسبب مانع المحرك: "
                        f"{item['code']}."
                    ),
                )
                for item in scenario_model.blockers
            )
        output.append(
            ScenarioEvaluation(
                scenario_id=scenario_id,
                kind=kind,
                status=scenario_model.status,
                input_hash=scenario_validated.input_hash,
                override_refs=override_refs,
                metrics=dict(scenario_model.metrics),
                blockers=blockers,
            )
        )
    return tuple(output)


def _apply_override(
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
        container[key] = _decimal_text(updated)


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
        return (
            (
                document["working_capital"],
                target["working_field"],
                field_ref,
            ),
        )
    if "valuation_field" in target:
        return (
            (
                document["valuation_policy"],
                target["valuation_field"],
                field_ref,
            ),
        )
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


def _binding(
    validated: ValidatedFinanceInput,
    document: dict[str, Any],
) -> ServerBinding:
    metadata = document["metadata"]
    return ServerBinding(
        organization_id=validated.organization_id,
        project_id=validated.project_id,
        run_id=validated.run_id,
        approved_manifest_id=metadata["approved_manifest_id"],
        approved_manifest_hash=metadata["approved_manifest_hash"],
        policy_ref=metadata["policy_ref"],
    )


def _decimal_text(value: Decimal) -> str:
    if not value.is_finite():
        raise FinanceContractError(
            "FIN2_SCENARIO_VALUE",
            "$.scenarios",
            "scenario arithmetic must remain finite",
        )
    with localcontext() as context:
        context.prec = max(
            50,
            len(value.as_tuple().digits)
            + abs(value.as_tuple().exponent)
            + 20,
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


def _blocker(code: str, field_ref: str, message_ar: str) -> dict[str, str]:
    return {
        "code": code,
        "severity": "high",
        "field_ref": field_ref,
        "message_ar": message_ar,
    }
