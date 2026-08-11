from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from .contracts import FinanceContractError, ValidatedFinanceInput
from .overrides import derive_validated_input
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
            scenario_validated = derive_validated_input(
                validated,
                scenario["overrides"],
                f"$.scenarios[{index}].overrides",
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


def _blocker(code: str, field_ref: str, message_ar: str) -> dict[str, str]:
    return {
        "code": code,
        "severity": "high",
        "field_ref": field_ref,
        "message_ar": message_ar,
    }
