from __future__ import annotations

from decimal import Decimal, ROUND_HALF_EVEN, localcontext
from math import isfinite
from typing import Any

from .contracts import FinanceContractError, ValidatedFinanceInput
from .model import FinancialModel, FinancialPeriod, ZERO
from .scenarios import evaluate_scenarios


ENGINE_VERSION = "2.0.0-dark.3"
_METRIC_KEYS = (
    "npv_unlevered",
    "irr_unlevered",
    "mirr_unlevered",
    "payback_months",
    "break_even",
    "funding_need",
    "dscr_min",
    "llcr",
)


def serialize_finance_result(
    validated: ValidatedFinanceInput,
    model: FinancialModel,
    *,
    include_legacy_projection: bool = False,
) -> dict[str, Any]:
    if model.source_input_hash != validated.input_hash:
        raise FinanceContractError(
            "FIN2_MODEL_INPUT_MISMATCH",
            "$.input_hash",
            "financial model was built from a different validated input",
        )
    document = validated.thaw()
    rounding = document["rounding_policy"]
    money_scale = rounding["money_scale"]
    ratio_scale = rounding["ratio_scale"]
    lineage = _collect_lineage(document)
    debt_coverage_metrics = _debt_coverage_metric_objects(
        validated,
        model,
        document,
        lineage,
        money_scale,
        ratio_scale,
    )
    scenario_evaluations = evaluate_scenarios(validated, model)
    scenario_blockers = [
        blocker
        for evaluation in scenario_evaluations
        for blocker in evaluation.blockers
    ]
    legacy_scenario_blockers = (
        [
            {
                "code": "FIN2_LEGACY_SCENARIO_PROJECTION_NOT_READY",
                "severity": "high",
                "field_ref": "$.legacy_projection",
                "message_ar": (
                    "لا يتاح إسقاط v1 عند طلب سيناريو غير baseline "
                    "حتى يكتمل إسقاط السيناريو واختبار تطابقه."
                ),
            }
        ]
        if include_legacy_projection
        and any(
            evaluation.kind != "baseline"
            for evaluation in scenario_evaluations
        )
        else []
    )
    coverage_projection_blockers = _debt_coverage_projection_blockers(
        debt_coverage_metrics,
        model.blockers,
    )
    coverage_is_unavailable = any(
        metric["applicability_status"] in {"UNKNOWN", "NOT_READY", "BLOCKED"}
        for metric in debt_coverage_metrics.values()
    )
    result_blockers = [
        *model.blockers,
        *coverage_projection_blockers,
        *scenario_blockers,
        *legacy_scenario_blockers,
    ]
    result_status = (
        "not_ready"
        if model.status == "ready" and result_blockers
        else model.status
    )

    result = {
        "schema_version": "finance-result.v2",
        "engine_version": ENGINE_VERSION,
        "status": result_status,
        "organization_id": validated.organization_id,
        "project_id": validated.project_id,
        "run_id": validated.run_id,
        "input_document_id": validated.document_id,
        "input_hash": validated.input_hash,
        "archetype_ref": document["archetype_ref"],
        "currency": validated.currency,
        "periods": list(validated.periods),
        "rounding_policy": rounding,
        "statements": {
            "income_statement": _statement(
                model.periods,
                {
                    "revenue": "revenue",
                    "cost_of_goods_sold": "cogs",
                    "gross_profit": "gross_profit",
                    "operating_expenses": "operating_expenses",
                    "ebitda": "ebitda",
                    "depreciation": "depreciation",
                    "ebit": "ebit",
                    "finance_cost": "interest_expense",
                    "fiscal_expense": "fiscal_expense",
                    "net_income": "net_income",
                },
                money_scale,
                "income",
            ),
            "balance_sheet": _statement(
                model.periods,
                {
                    "cash": "ending_cash",
                    "accounts_receivable": "accounts_receivable",
                    "inventory": "inventory",
                    "ppe_net": "ppe_net",
                    "total_assets": "total_assets",
                    "accounts_payable": "accounts_payable",
                    "debt": "debt_closing",
                    "total_liabilities": "total_liabilities",
                    "contributed_equity": "equity_contributions",
                    "retained_earnings": "retained_earnings",
                    "total_equity": "total_equity",
                },
                money_scale,
                "balance",
                cumulative_equity=True,
            ),
            "cash_flow_statement": _statement(
                model.periods,
                {
                    "opening_cash": "opening_cash",
                    "cash_from_operations": "cash_from_operations",
                    "cash_from_investing": "cash_from_investing",
                    "cash_from_financing": "cash_from_financing",
                    "ending_cash": "ending_cash",
                    "capex": "capex_additions",
                    "debt_drawdowns": "debt_drawdowns",
                    "principal_paid": "principal_paid",
                },
                money_scale,
                "cashflow",
            ),
        },
        "cash_flows": {
            "unlevered_fcf": [_decimal(row.unlevered_fcf, money_scale) for row in model.periods],
            "equity_cash_flow": [_decimal(row.equity_cash_flow, money_scale) for row in model.periods],
            "cfads": [_decimal(row.cfads, money_scale) for row in model.periods],
        },
        "subledgers": {
            "capex": [
                {
                    "period": row.period,
                    "additions": _decimal(row.capex_additions, money_scale),
                    "depreciation": _decimal(row.depreciation, money_scale),
                    "ppe_net": _decimal(row.ppe_net, money_scale),
                }
                for row in model.periods
            ],
            "working_capital": [
                {
                    "period": row.period,
                    "accounts_receivable": _decimal(row.accounts_receivable, money_scale),
                    "inventory": _decimal(row.inventory, money_scale),
                    "accounts_payable": _decimal(row.accounts_payable, money_scale),
                    "change_in_working_capital": _decimal(row.change_in_working_capital, money_scale),
                }
                for row in model.periods
            ],
            "debt": (
                [
                    {
                        "period": period,
                        **{
                            field: _decimal(
                                getattr(debt_row, field), money_scale
                            )
                            for field in debt_row.__dataclass_fields__
                        },
                    }
                    for period, debt_row in zip(
                        validated.periods,
                        model.debt_schedule,
                        strict=True,
                    )
                ]
                if len(model.debt_schedule) == len(validated.periods)
                else []
            ),
            "fiscal": [
                {
                    "period": row.period,
                    "expense": _decimal(row.fiscal_expense, money_scale),
                }
                for row in model.periods
            ],
        },
        "metrics": {
            key: (
                debt_coverage_metrics[key]["value"]
                if key in debt_coverage_metrics
                else _metric_decimal(
                    key, model.metrics.get(key), money_scale, ratio_scale
                )
            )
            for key in _METRIC_KEYS
        },
        "debt_coverage_metrics": debt_coverage_metrics,
        "invariants": [
            {
                "invariant_id": item.invariant_id,
                "status": item.status,
                "tolerance": _decimal(item.tolerance, money_scale),
                "maximum_variance": _decimal(item.maximum_variance, money_scale),
                "period_refs": list(item.period_refs),
                "reason": item.reason,
            }
            for item in model.invariants
        ],
        "scenarios": [
            {
                "scenario_id": evaluation.scenario_id,
                "kind": evaluation.kind,
                "status": (
                    "not_ready"
                    if coverage_is_unavailable
                    else evaluation.status
                ),
                "input_hash": evaluation.input_hash,
                "override_refs": list(evaluation.override_refs),
                "metrics": {
                    key: (
                        debt_coverage_metrics[key]["value"]
                        if key in debt_coverage_metrics
                        and (
                            evaluation.kind == "baseline"
                            or coverage_is_unavailable
                        )
                        else _metric_decimal(
                            key,
                            evaluation.metrics.get(key),
                            money_scale,
                            ratio_scale,
                        )
                    )
                    for key in _METRIC_KEYS
                },
                **(
                    {"simulation_summary": evaluation.simulation_summary}
                    if evaluation.simulation_summary is not None
                    else {}
                ),
            }
            for evaluation in scenario_evaluations
        ],
        "lineage": {
            **lineage,
            "formula_registry_version": ENGINE_VERSION,
        },
        "blockers": result_blockers,
        "legacy_projection": (
            _legacy_projection(
                model,
                document,
                lineage,
                debt_coverage_metrics,
                coverage_projection_blockers,
                money_scale,
                ratio_scale,
            )
            if include_legacy_projection
            and not legacy_scenario_blockers
            else {
                "schema_version": "finance.result.v1-compatible",
                "status": "not_available",
                "derived_from": "finance-result.v2",
                "payload": {},
            }
        ),
    }
    if include_legacy_projection:
        _apply_legacy_parity(result, money_scale, ratio_scale)
    validate_finance_result_projection(result)
    return result


def validate_finance_result_projection(
    result: dict[str, Any],
) -> None:
    """Fail closed when compatibility metric values diverge from envelopes."""
    try:
        ratio_scale = result["rounding_policy"]["ratio_scale"]
        metrics = result["metrics"]
        envelopes = result["debt_coverage_metrics"]
        baseline_scenarios = [
            scenario
            for scenario in result["scenarios"]
            if scenario["kind"] == "baseline"
        ]
        if len(baseline_scenarios) != 1:
            raise ValueError("exactly one baseline scenario is required")
        baseline = baseline_scenarios[0]
        coverage_is_unavailable = any(
            envelope["applicability_status"]
            in {"UNKNOWN", "NOT_READY", "BLOCKED"}
            for envelope in envelopes.values()
        )
        if coverage_is_unavailable:
            for scenario in result["scenarios"]:
                if scenario["status"] == "ready":
                    raise FinanceContractError(
                        "FIN2_DEBT_COVERAGE_PROJECTION_MISMATCH",
                        "$.scenarios",
                        (
                            "scenario cannot remain ready when debt "
                            "coverage is unavailable"
                        ),
                    )
        expected_period_range = {
            "start_period": result["periods"][0],
            "end_period": result["periods"][-1],
        }
        expected_lineage = {
            "assumption_refs": result["lineage"]["assumption_refs"],
            "evidence_refs": result["lineage"]["evidence_refs"],
        }
        for metric_id in ("dscr_min", "llcr"):
            envelope = envelopes[metric_id]
            traceability_checks = (
                (
                    "source_artifact_id",
                    envelope["source_artifact_id"],
                    result["run_id"],
                ),
                (
                    "period_range",
                    envelope["period_range"],
                    expected_period_range,
                ),
                (
                    "lineage_refs",
                    envelope["lineage_refs"],
                    expected_lineage,
                ),
            )
            for field_name, actual, expected in traceability_checks:
                if actual != expected:
                    raise FinanceContractError(
                        "FIN2_DEBT_COVERAGE_PROJECTION_MISMATCH",
                        (
                            "$.debt_coverage_metrics."
                            f"{metric_id}.{field_name}"
                        ),
                        (
                            "debt-coverage traceability diverges from "
                            "the parent result"
                        ),
                    )
            required_result_blockers: set[str] = set()
            if envelope["applicability_status"] == "NOT_READY":
                required_result_blockers.add(
                    f"FIN2_DEBT_COVERAGE_{envelope['reason_code']}"
                )
            elif envelope["applicability_status"] == "BLOCKED":
                required_result_blockers.update(envelope["blocker_codes"])
            result_blocker_codes = {
                blocker["code"] for blocker in result["blockers"]
            }
            if not required_result_blockers.issubset(
                result_blocker_codes
            ):
                raise FinanceContractError(
                    "FIN2_DEBT_COVERAGE_PROJECTION_MISMATCH",
                    "$.blockers",
                    (
                        "result omits blockers required by governed "
                        "debt-coverage envelopes"
                    ),
                )
            blocker_codes = envelope["blocker_codes"]
            if blocker_codes != sorted(set(blocker_codes)):
                raise FinanceContractError(
                    "FIN2_DEBT_COVERAGE_PROJECTION_MISMATCH",
                    (
                        "$.debt_coverage_metrics."
                        f"{metric_id}.blocker_codes"
                    ),
                    (
                        "debt-coverage blocker codes must be unique and "
                        "canonically sorted"
                    ),
                )
            envelope_value = _canonical_projection_value(
                envelopes[metric_id]["value"],
                ratio_scale,
            )
            consumers = [
                (f"$.metrics.{metric_id}", metrics[metric_id]),
                (
                    f"$.scenarios.baseline.metrics.{metric_id}",
                    baseline["metrics"][metric_id],
                ),
            ]
            if coverage_is_unavailable:
                consumers.extend(
                    (
                        "$.scenarios"
                        f"[{scenario['scenario_id']}].metrics.{metric_id}",
                        scenario["metrics"][metric_id],
                    )
                    for scenario in result["scenarios"]
                    if scenario["kind"] != "baseline"
                )
            for field_ref, consumer_value in consumers:
                projected_value = _canonical_projection_value(
                    consumer_value,
                    ratio_scale,
                )
                if projected_value != envelope_value:
                    raise FinanceContractError(
                        "FIN2_DEBT_COVERAGE_PROJECTION_MISMATCH",
                        field_ref,
                        (
                            "projected metric diverges from the governed "
                            "debt-coverage envelope"
                        ),
                    )
        _validate_legacy_debt_coverage_projection(
            result,
            envelopes,
            ratio_scale,
        )
    except FinanceContractError:
        raise
    except (ArithmeticError, KeyError, TypeError, ValueError) as exc:
        raise FinanceContractError(
            "FIN2_DEBT_COVERAGE_PROJECTION_MISMATCH",
            "$.debt_coverage_metrics",
            "debt-coverage projection shape or decimal value is invalid",
        ) from exc


def _validate_legacy_debt_coverage_projection(
    result: dict[str, Any],
    envelopes: dict[str, dict[str, Any]],
    ratio_scale: int,
) -> None:
    legacy = result["legacy_projection"]
    if legacy["status"] != "derived":
        return
    payload = legacy["payload"]
    coverage_is_unavailable = any(
        envelope["applicability_status"] in {"UNKNOWN", "NOT_READY", "BLOCKED"}
        for envelope in envelopes.values()
    )
    required_blockers: set[str] = set()
    for envelope in envelopes.values():
        if envelope["applicability_status"] == "NOT_READY":
            required_blockers.add(
                f"FIN2_DEBT_COVERAGE_{envelope['reason_code']}"
            )
        elif envelope["applicability_status"] == "BLOCKED":
            required_blockers.update(envelope["blocker_codes"])
    if coverage_is_unavailable:
        if payload["status"] == "ready":
            raise FinanceContractError(
                "FIN2_DEBT_COVERAGE_PROJECTION_MISMATCH",
                "$.legacy_projection.payload.status",
                (
                    "legacy projection cannot remain ready when governed "
                    "debt coverage is not ready or blocked"
                ),
            )
        payload_blockers = {
            blocker["code"] for blocker in payload["blockers"]
        }
        if not required_blockers.issubset(payload_blockers):
            raise FinanceContractError(
                "FIN2_DEBT_COVERAGE_PROJECTION_MISMATCH",
                "$.legacy_projection.payload.blockers",
                (
                    "legacy projection omits governed debt-coverage "
                    "blockers"
                ),
            )

    baseline = payload.get("baseline")
    if baseline is not None and coverage_is_unavailable:
        profile_statuses = [
            (
                "$.legacy_projection.payload.baseline."
                "debt_service_profile.status",
                baseline["debt_service_profile"]["status"],
            ),
            (
                "$.legacy_projection.payload."
                "debt_service_profile.status",
                payload["debt_service_profile"]["status"],
            ),
        ]
        for index, scenario in enumerate(payload["scenarios"]):
            profile_statuses.append(
                (
                    "$.legacy_projection.payload.scenarios"
                    f"[{index}].debt_service_profile.status",
                    scenario["debt_service_profile"]["status"],
                )
            )
        for field_ref, status in profile_statuses:
            if status != "not_ready":
                raise FinanceContractError(
                    "FIN2_DEBT_COVERAGE_PROJECTION_MISMATCH",
                    field_ref,
                    (
                        "legacy debt-service profile must be not_ready "
                        "when governed debt coverage is unavailable"
                    ),
                )
    if baseline is None:
        return
    governed_dscr = _canonical_projection_value(
        envelopes["dscr_min"]["value"],
        ratio_scale,
    )
    consumers = [
        (
            "$.legacy_projection.payload.baseline.dscr",
            baseline["dscr"],
        ),
        (
            "$.legacy_projection.payload.baseline."
            "debt_service_profile.dscr",
            baseline["debt_service_profile"]["dscr"],
        ),
        (
            "$.legacy_projection.payload.debt_service_profile.dscr",
            payload["debt_service_profile"]["dscr"],
        ),
    ]
    for index, scenario in enumerate(payload["scenarios"]):
        consumers.extend(
            [
                (
                    "$.legacy_projection.payload.scenarios"
                    f"[{index}].dscr",
                    scenario["dscr"],
                ),
                (
                    "$.legacy_projection.payload.scenarios"
                    f"[{index}].debt_service_profile.dscr",
                    scenario["debt_service_profile"]["dscr"],
                ),
            ]
        )
    for field_ref, value in consumers:
        if _canonical_legacy_projection_value(
            value,
            ratio_scale,
        ) != governed_dscr:
            raise FinanceContractError(
                "FIN2_DEBT_COVERAGE_PROJECTION_MISMATCH",
                field_ref,
                (
                    "legacy DSCR diverges from the governed "
                    "debt-coverage envelope"
                ),
            )


def _canonical_legacy_projection_value(
    value: Any,
    ratio_scale: int,
) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("legacy projected metric must be numeric")
    if not isfinite(float(value)):
        raise ValueError("legacy projected metric must be finite")
    return Decimal(_decimal(Decimal(str(value)), ratio_scale))


def _canonical_projection_value(
    value: Any,
    ratio_scale: int,
) -> Decimal | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError("projected metric value must be a decimal string")
    return Decimal(_decimal(Decimal(value), ratio_scale))


_DEBT_COVERAGE_FORMULAS = {
    "dscr_min": "fin2.metric.dscr_min.rolling_12m.v1",
    "llcr": "fin2.metric.llcr.minimum_loan_life.v1",
}
_DEBT_COVERAGE_AGGREGATIONS = {
    "dscr_min": "minimum_rolling_12_month",
    "llcr": "minimum_loan_life",
}
_DEBT_COVERAGE_ALLOWED_BLOCKER_CODES = frozenset(
    {
        "FIN2_INVARIANT_BALANCE_EQUATION",
        "FIN2_INVARIANT_CASH_STATEMENT_BALANCE_SHEET",
        "FIN2_INVARIANT_CASH_ROLLFORWARD",
        "FIN2_INVARIANT_RETAINED_EARNINGS_ROLLFORWARD",
        "FIN2_INVARIANT_PPE_ROLLFORWARD",
        "FIN2_INVARIANT_DEBT_ROLLFORWARD",
        "FIN2_INVARIANT_SOURCES_USES_BALANCE",
        "FIN2_INVARIANT_GROSS_PROFIT_EQUATION",
        "FIN2_INVARIANT_EBIT_EQUATION",
        "FIN2_INVARIANT_CASH_FLOW_EQUATION",
        "FIN2_INVARIANT_FINITE_NUMBERS",
        "FIN2_INVARIANT_PERIOD_ORDER",
        "FIN2_INVARIANT_LEGACY_PROJECTION_PARITY",
        "FIN2_INVARIANT_DETERMINISTIC_REPLAY",
        "FIN2_DSCR_MIN_VALUE_MISSING",
        "FIN2_LLCR_VALUE_MISSING",
        "FIN2_DEBT_COVERAGE_BLOCKER_UNRECOGNIZED",
    }
)
_DEBT_COVERAGE_MODEL_BLOCKER_CODES = (
    _DEBT_COVERAGE_ALLOWED_BLOCKER_CODES
    - {
        "FIN2_DSCR_MIN_VALUE_MISSING",
        "FIN2_LLCR_VALUE_MISSING",
        "FIN2_DEBT_COVERAGE_BLOCKER_UNRECOGNIZED",
    }
)
_DEBT_COVERAGE_READINESS_CODES = frozenset(
    {
        "FIN2_DEBT_PROFILE_UNSUPPORTED",
        "FIN2_VAT_LEDGER_NOT_READY",
    }
)
_DEBT_COVERAGE_FIELD_PREFIXES = (
    "$.financing",
    "$.fiscal_policy",
    "$.statements",
    "$.cash_flows",
    "$.metrics.dscr",
    "$.metrics.llcr",
)


def _debt_coverage_metric_objects(
    validated: ValidatedFinanceInput,
    model: FinancialModel,
    document: dict[str, Any],
    lineage: dict[str, list[str]],
    money_scale: int,
    ratio_scale: int,
) -> dict[str, dict[str, Any]]:
    declared_debt = bool(document["financing"]["debt_tranches"])
    model_blocker_codes = {
        blocker.get("code", "")
        for blocker in model.blockers
    }
    cfads_ready = (
        len(model.periods) == len(validated.periods)
        and bool(model.periods)
    )
    debt_schedule_ready = (
        len(model.debt_schedule) == len(validated.periods)
        and bool(model.debt_schedule)
    )
    if "FIN2_DEBT_PROFILE_UNSUPPORTED" in model_blocker_codes:
        debt_schedule_ready = False
        # The engine returns before building periods, but the root readiness
        # cause is the absent reviewed debt schedule, not absent CFADS.
        cfads_ready = True
    if "FIN2_VAT_LEDGER_NOT_READY" in model_blocker_codes:
        cfads_ready = False
    has_eligible_debt_service = debt_schedule_ready and any(
        row.interest_paid + row.principal_paid + row.fees_paid > ZERO
        for row in model.debt_schedule
    )
    blocker_codes = _debt_coverage_blocker_codes(model.blockers)
    applicability, reason_code, detail_codes = _debt_coverage_state(
        declared_debt=declared_debt,
        cfads_ready=cfads_ready,
        debt_schedule_ready=debt_schedule_ready,
        has_eligible_debt_service=has_eligible_debt_service,
        blocker_codes=blocker_codes,
    )

    output: dict[str, dict[str, Any]] = {}
    for metric_id in ("dscr_min", "llcr"):
        metric_applicability = applicability
        metric_reason = reason_code
        metric_detail_codes = detail_codes
        value = (
            _metric_decimal(
                metric_id,
                model.metrics.get(metric_id),
                money_scale,
                ratio_scale,
            )
            if metric_applicability == "APPLICABLE"
            else None
        )
        if metric_applicability == "APPLICABLE" and value is None:
            missing_code = (
                f"FIN2_{metric_id.upper()}_VALUE_MISSING"
            )
            metric_applicability = "BLOCKED"
            metric_reason = missing_code
            metric_detail_codes = (missing_code,)

        output[metric_id] = {
            "metric_id": metric_id,
            "value": value,
            "value_status": (
                "VALUE_PRESENT" if value is not None else "VALUE_ABSENT"
            ),
            "applicability_status": metric_applicability,
            "reason_code": metric_reason,
            "blocker_codes": list(metric_detail_codes),
            "period_range": {
                "start_period": validated.periods[0],
                "end_period": validated.periods[-1],
            },
            "unit": "ratio",
            "currency": None,
            "currency_reason": "NOT_MONETARY_METRIC",
            "grain": {
                "schema_version": "finance-metric-grain.v1",
                "frequency": "monthly",
                "aggregation": _DEBT_COVERAGE_AGGREGATIONS[metric_id],
                "dimensions": [],
            },
            "source_artifact_id": validated.run_id,
            "formula_version": _DEBT_COVERAGE_FORMULAS[metric_id],
            "lineage_refs": {
                "assumption_refs": list(lineage["assumption_refs"]),
                "evidence_refs": list(lineage["evidence_refs"]),
            },
        }
    return output


def _debt_coverage_state(
    *,
    declared_debt: bool,
    cfads_ready: bool,
    debt_schedule_ready: bool,
    has_eligible_debt_service: bool,
    blocker_codes: tuple[str, ...] = (),
) -> tuple[str, str, tuple[str, ...]]:
    canonical_blockers = tuple(sorted(set(blocker_codes)))
    if not declared_debt:
        return "NOT_APPLICABLE", "NO_DEBT_SERVICE", ()
    if canonical_blockers:
        reason = (
            canonical_blockers[0]
            if len(canonical_blockers) == 1
            else "MULTIPLE_DEBT_COVERAGE_BLOCKERS"
        )
        return "BLOCKED", reason, canonical_blockers
    if not cfads_ready and not debt_schedule_ready:
        return (
            "NOT_READY",
            "CFADS_AND_DEBT_SCHEDULE_NOT_READY",
            (),
        )
    if not cfads_ready:
        return "NOT_READY", "CFADS_NOT_READY", ()
    if not debt_schedule_ready:
        return "NOT_READY", "DEBT_SCHEDULE_NOT_READY", ()
    if not has_eligible_debt_service:
        return "NOT_APPLICABLE", "NO_DEBT_SERVICE", ()
    return "APPLICABLE", "READY", ()


def _debt_coverage_blocker_codes(
    blockers: tuple[dict[str, str], ...],
) -> tuple[str, ...]:
    relevant = []
    for blocker in blockers:
        code = blocker.get("code", "")
        field_ref = blocker.get("field_ref", "")
        if code in _DEBT_COVERAGE_READINESS_CODES:
            continue
        is_relevant = (
            code.startswith("FIN2_INVARIANT_")
            or field_ref.startswith(_DEBT_COVERAGE_FIELD_PREFIXES)
        )
        if is_relevant:
            relevant.append(
                code
                if code in _DEBT_COVERAGE_MODEL_BLOCKER_CODES
                else "FIN2_DEBT_COVERAGE_BLOCKER_UNRECOGNIZED"
            )
    return tuple(sorted(set(relevant)))


def _debt_coverage_projection_blockers(
    metrics: dict[str, dict[str, Any]],
    model_blockers: tuple[dict[str, str], ...],
) -> list[dict[str, str]]:
    existing_codes = {
        blocker["code"]
        for blocker in model_blockers
        if blocker.get("code")
    }
    projected: dict[str, str] = {}
    for metric_id, metric in metrics.items():
        applicability = metric["applicability_status"]
        if applicability == "NOT_READY":
            code = f"FIN2_DEBT_COVERAGE_{metric['reason_code']}"
            projected.setdefault(
                code,
                (
                    "مدخلات مقياس تغطية الدين غير جاهزة: "
                    f"{metric['reason_code']}."
                ),
            )
        elif applicability == "BLOCKED":
            for code in metric["blocker_codes"]:
                if code not in existing_codes:
                    projected.setdefault(
                        code,
                        (
                            "إسقاط تغطية الدين محجوب للمقياس "
                            f"{metric_id}: {code}."
                        ),
                    )
    return [
        {
            "code": code,
            "severity": "high",
            "field_ref": "$.debt_coverage_metrics",
            "message_ar": message,
        }
        for code, message in sorted(projected.items())
    ]


def _apply_legacy_parity(
    result: dict[str, Any],
    money_scale: int,
    ratio_scale: int,
) -> None:
    payload = result["legacy_projection"]["payload"]
    baseline = payload.get("baseline")
    if baseline is None:
        return
    pairs = (
        ("npv", "npv_unlevered", money_scale),
        ("irr", "irr_unlevered", ratio_scale),
        ("payback_months", "payback_months", ratio_scale),
        ("break_even_units", "break_even", money_scale),
        ("funding_gap", "funding_need", money_scale),
        ("funding_need_after_equity", "funding_need", money_scale),
        ("dscr", "dscr_min", ratio_scale),
    )
    maximum = ZERO
    failed = False
    for legacy_key, metric_key, scale in pairs:
        actual = baseline[legacy_key]
        expected = result["metrics"][metric_key]
        if actual is None or expected is None:
            failed = failed or actual is not None or expected is not None
            continue
        expected_float = float(_decimal(Decimal(expected), scale))
        if not isfinite(expected_float) or not isfinite(float(actual)):
            failed = True
            continue
        variance = abs(
            Decimal(str(actual)) - Decimal(str(expected_float))
        )
        maximum = max(maximum, variance)
        failed = failed or variance != ZERO

    for invariant in result["invariants"]:
        if invariant["invariant_id"] != "legacy_projection_parity":
            continue
        invariant["status"] = "failed" if failed else "passed"
        invariant["maximum_variance"] = _decimal(
            maximum, max(money_scale, ratio_scale)
        )
        invariant["reason"] = (
            "derived_legacy_projection_mismatch" if failed else ""
        )
        break

    if failed:
        result["status"] = "not_ready"
        for scenario in result["scenarios"]:
            scenario["status"] = "not_ready"
        result["blockers"].append(
            {
                "code": "FIN2_INVARIANT_LEGACY_PROJECTION_PARITY",
                "severity": "high",
                "field_ref": "$.legacy_projection.payload.baseline",
                "message_ar": "فشل تطابق الإسقاط المشتق مع نتيجة Finance v2.",
            }
        )


def _statement(
    periods: tuple[FinancialPeriod, ...],
    lines: dict[str, str],
    scale: int,
    formula_prefix: str,
    *,
    cumulative_equity: bool = False,
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    cumulative = ZERO
    for line_id, field in lines.items():
        values = []
        for row in periods:
            value = getattr(row, field)
            if cumulative_equity and line_id == "contributed_equity":
                cumulative += value
                value = cumulative
            values.append({"period": row.period, "value": _decimal(value, scale)})
        if cumulative_equity and line_id == "contributed_equity":
            cumulative = ZERO
        output.append(
            {
                "line_id": line_id,
                "values": values,
                "formula_id": f"fin2.{formula_prefix}.{line_id}.v1",
                "input_refs": [f"finance-model-input.v2:{field}"],
            }
        )
    return output


def _legacy_projection(
    model: FinancialModel,
    document: dict[str, Any],
    lineage: dict[str, list[str]],
    debt_coverage_metrics: dict[str, dict[str, Any]],
    coverage_projection_blockers: list[dict[str, str]],
    money_scale: int,
    ratio_scale: int,
) -> dict[str, Any]:
    coverage_is_unavailable = any(
        metric["applicability_status"] in {"UNKNOWN", "NOT_READY", "BLOCKED"}
        for metric in debt_coverage_metrics.values()
    )
    monte_carlo = _legacy_not_ready_monte_carlo()
    if not model.periods:
        payload = _legacy_unavailable_payload(
            lineage,
            list(model.blockers),
            monte_carlo,
        )
    elif model.metrics.get("break_even") is None:
        payload = _legacy_unavailable_payload(
            lineage,
            [
                *model.blockers,
                {
                    "code": "FIN2_LEGACY_BREAK_EVEN_UNAVAILABLE",
                    "severity": "high",
                    "field_ref": "$.metrics.break_even",
                    "message_ar": "لا يمكن تمثيل نقطة التعادل المطلوبة في عقد v1.",
                },
            ],
            monte_carlo,
        )
    elif not _legacy_numbers_supported(model, document):
        payload = _legacy_unavailable_payload(
            lineage,
            [
                *model.blockers,
                {
                    "code": "FIN2_LEGACY_NUMBER_RANGE",
                    "severity": "high",
                    "field_ref": "$.legacy_projection",
                    "message_ar": "تتجاوز قيمة مالية نطاق الأرقام الآمن لعقد v1.",
                },
            ],
            monte_carlo,
        )
    else:
        count = Decimal(len(model.periods))
        average = (
            lambda field: sum(
                (getattr(row, field) for row in model.periods), ZERO
            )
            / count
        )
        total_capex = sum((row.capex_additions for row in model.periods), ZERO)
        working_capital = max(
            (row.net_working_capital for row in model.periods), default=ZERO
        )
        funding_need = model.metrics.get("funding_need") or ZERO
        average_revenue = average("revenue")
        average_gross = average("gross_profit")
        contribution_margin = (
            average_gross / average_revenue
            if average_revenue != ZERO
            else ZERO
        )
        monthly_units = sum(
            (
                Decimal(point["value"])
                for stream in document["revenue_streams"]
                for point in stream["volume_series"]
            ),
            ZERO,
        ) / count
        representative_monthly_payment = (
            _representative_debt_payment(model)
        )
        debt_amount = sum(
            (row.debt_drawdowns for row in model.periods), ZERO
        )
        has_debt = debt_amount > ZERO or any(
            row.debt_closing > ZERO for row in model.periods
        )
        annualized_debt_service = (
            representative_monthly_payment * Decimal("12")
        )
        depreciation_monthly = average("depreciation")
        depreciation_years = (
            ZERO
            if depreciation_monthly <= ZERO
            else total_capex / (depreciation_monthly * Decimal("12"))
        )
        loan_grace_months = max(
            (
                int(row["principal_grace_months"])
                for row in document["financing"]["debt_tranches"]
            ),
            default=0,
        )

        operating_model = {
            "use_operating_capacity": False,
            "capacity_units_per_day": 0.0,
            "operating_days_per_month": 0.0,
            "utilization_rate": 0.0,
            "monthly_units": float(_decimal(monthly_units, money_scale)),
            "unit_source": "manual_monthly_units",
        }
        capex_breakdown = {
            "capex_equipment": 0.0,
            "capex_fitout": 0.0,
            "capex_licenses_local": 0.0,
            "legacy_startup_cost": float(
                _decimal(total_capex, money_scale)
            ),
            "total_capex": float(_decimal(total_capex, money_scale)),
            "depreciation_years": float(
                _decimal(depreciation_years, ratio_scale)
            ),
            "depreciation_monthly": float(
                _decimal(depreciation_monthly, money_scale)
            ),
        }
        opex_breakdown = {
            "payroll_monthly": 0.0,
            "rent_monthly": 0.0,
            "utilities_monthly": 0.0,
            "marketing_monthly": 0.0,
            "maintenance_monthly": 0.0,
            "legacy_monthly_fixed_cost": float(
                _decimal(average("operating_expenses"), money_scale)
            ),
            "total_monthly_opex": float(
                _decimal(average("operating_expenses"), money_scale)
            ),
        }
        governed_dscr = debt_coverage_metrics["dscr_min"]["value"]
        dscr = _legacy_float(
            Decimal(governed_dscr)
            if governed_dscr is not None
            else None,
            ratio_scale,
        )
        debt_service_profile = {
            "status": (
                "not_ready" if coverage_is_unavailable else "ready"
            ),
            "debt_amount": float(_decimal(debt_amount, money_scale)),
            "monthly_payment": (
                float(
                    _decimal(
                        representative_monthly_payment, money_scale
                    )
                )
                if has_debt
                else None
            ),
            "annual_debt_service": (
                float(_decimal(annualized_debt_service, money_scale))
                if has_debt
                else None
            ),
            "dscr": dscr,
            "loan_grace_months": loan_grace_months,
            "warning": (
                ""
                if not has_debt or dscr is None or dscr >= 1.2
                else "DSCR below 1.2 pressure threshold."
            ),
        }
        baseline = {
            "scenario_id": "baseline",
            "startup_cost": float(_decimal(total_capex, money_scale)),
            "revenue": float(_decimal(average_revenue, money_scale)),
            "variable_total": float(
                _decimal(average("cogs"), money_scale)
            ),
            "gross_profit": float(_decimal(average_gross, money_scale)),
            "monthly_profit": float(
                _decimal(average("net_income"), money_scale)
            ),
            "annual_cashflow": float(
                _decimal(
                    sum(
                        (
                            row.equity_cash_flow
                            for row in model.periods[:12]
                        ),
                        ZERO,
                    ),
                    money_scale,
                )
            ),
            "ebitda": float(_decimal(average("ebitda"), money_scale)),
            "ebit": float(_decimal(average("ebit"), money_scale)),
            "depreciation_monthly": capex_breakdown[
                "depreciation_monthly"
            ],
            "net_operating_cashflow": float(
                _decimal(average("cash_from_operations"), money_scale)
            ),
            "break_even_units": _legacy_float(
                model.metrics.get("break_even"), money_scale
            ),
            "funding_gap": float(_decimal(funding_need, money_scale)),
            "funding_need_after_equity": float(
                _decimal(funding_need, money_scale)
            ),
            "contribution_margin": float(
                _decimal(contribution_margin, ratio_scale)
            ),
            "working_capital_need": float(
                _decimal(working_capital, money_scale)
            ),
            "initial_investment": float(
                _decimal(total_capex + working_capital, money_scale)
            ),
            "npv": float(
                _decimal(
                    model.metrics.get("npv_unlevered") or ZERO,
                    money_scale,
                )
            ),
            "irr": _legacy_float(
                model.metrics.get("irr_unlevered"), ratio_scale
            ),
            "payback_months": _legacy_float(
                model.metrics.get("payback_months"), ratio_scale
            ),
            "debt_service_monthly": debt_service_profile[
                "monthly_payment"
            ],
            "dscr": dscr,
            "operating_model": operating_model,
            "capex_breakdown": capex_breakdown,
            "opex_breakdown": opex_breakdown,
            "debt_service_profile": debt_service_profile,
        }
        payload = {
            "status": model.status,
            "baseline": baseline,
            "scenarios": [dict(baseline)],
            "sensitivity": None,
            "operational_sensitivity": None,
            "operating_model": operating_model,
            "capex_breakdown": capex_breakdown,
            "opex_breakdown": opex_breakdown,
            "debt_service_profile": debt_service_profile,
            "monte_carlo": monte_carlo,
            "assumption_refs": lineage["assumption_refs"],
            "blockers": list(model.blockers),
        }
    if coverage_is_unavailable:
        payload["status"] = "not_ready"
        payload["blockers"].extend(coverage_projection_blockers)
    return {
        "schema_version": "finance.result.v1-compatible",
        "status": "derived",
        "derived_from": "finance-result.v2",
        "payload": payload,
    }


def _legacy_unavailable_payload(
    lineage: dict[str, list[str]],
    blockers: list[dict[str, Any]],
    monte_carlo: dict[str, Any],
) -> dict[str, Any]:
    return {
        "status": "not_ready",
        "baseline": None,
        "scenarios": [],
        "sensitivity": None,
        "operational_sensitivity": None,
        "operating_model": None,
        "capex_breakdown": None,
        "opex_breakdown": None,
        "debt_service_profile": None,
        "monte_carlo": monte_carlo,
        "assumption_refs": lineage["assumption_refs"],
        "blockers": blockers,
    }


def _representative_debt_payment(model: FinancialModel) -> Decimal:
    scheduled = tuple(
        row.interest_paid + row.principal_paid
        for row in model.debt_schedule
    )
    active_indices = tuple(
        index
        for index, row in enumerate(model.debt_schedule)
        if (
            row.opening_balance > ZERO
            or row.drawdowns > ZERO
            or row.closing_balance > ZERO
        )
    )
    if not active_indices:
        return ZERO
    return (
        sum((scheduled[index] for index in active_indices), ZERO)
        / Decimal(len(active_indices))
    )


def _legacy_numbers_supported(
    model: FinancialModel,
    document: dict[str, Any],
) -> bool:
    values: list[Decimal] = []
    for row in (*model.periods, *model.debt_schedule):
        values.extend(
            value
            for field in row.__dataclass_fields__
            if isinstance((value := getattr(row, field)), Decimal)
        )
    values.extend(
        value for value in model.metrics.values() if isinstance(value, Decimal)
    )

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)
        elif isinstance(value, str):
            candidate = value.removeprefix("-")
            if (
                candidate.count(".") <= 1
                and candidate.replace(".", "").isdigit()
            ):
                values.append(Decimal(value))

    walk(document)
    if model.periods:
        count = Decimal(len(model.periods))
        average = (
            lambda field: sum(
                (getattr(row, field) for row in model.periods), ZERO
            )
            / count
        )
        total_capex = sum(
            (row.capex_additions for row in model.periods), ZERO
        )
        working_capital = max(
            (row.net_working_capital for row in model.periods),
            default=ZERO,
        )
        aggregate_monthly_units = sum(
            (
                Decimal(point["value"])
                for stream in document["revenue_streams"]
                for point in stream["volume_series"]
            ),
            ZERO,
        ) / count
        representative_payment = _representative_debt_payment(model)
        depreciation_monthly = average("depreciation")
        depreciation_years = (
            ZERO
            if depreciation_monthly <= ZERO
            else total_capex
            / (depreciation_monthly * Decimal("12"))
        )
        average_revenue = average("revenue")
        contribution_margin = (
            average("gross_profit") / average_revenue
            if average_revenue != ZERO
            else ZERO
        )
        values.extend(
            (
                aggregate_monthly_units,
                total_capex,
                working_capital,
                total_capex + working_capital,
                sum(
                    (
                        row.equity_cash_flow
                        for row in model.periods[:12]
                    ),
                    ZERO,
                ),
                sum(
                    (row.debt_drawdowns for row in model.periods),
                    ZERO,
                ),
                representative_payment,
                representative_payment * Decimal("12"),
                depreciation_monthly,
                depreciation_years,
                contribution_margin,
                *(
                    average(field)
                    for field in (
                        "revenue",
                        "cogs",
                        "gross_profit",
                        "net_income",
                        "ebitda",
                        "ebit",
                        "cash_from_operations",
                        "operating_expenses",
                    )
                ),
            )
        )
    aggregate_absolute = sum((abs(value) for value in values), ZERO)
    values.extend(
        (
            aggregate_absolute,
            aggregate_absolute * Decimal("12"),
        )
    )
    try:
        return all(isfinite(float(value)) for value in values)
    except (OverflowError, ValueError):
        return False


def _legacy_not_ready_monte_carlo() -> dict[str, Any]:
    return {
        "status": "not_ready",
        "seed": 0,
        "iterations": 0,
        "p_pass": None,
        "p10_profit": None,
        "p50_profit": None,
        "p90_profit": None,
        "distribution_profile": "NOT_READY",
        "correlation_ref": "NOT_READY",
        "convergence": {
            "min_iterations": 0,
            "actual_iterations": 0,
            "status": "not_ready",
        },
        "label_ar": "احتمال اجتياز بوابات الجدوى",
        "label_en": "Probability of passing feasibility gates",
        "warning": "NOT_READY: FIN2_SIMULATION_NOT_READY",
    }

def _collect_lineage(document: dict[str, Any]) -> dict[str, list[str]]:
    assumptions: set[str] = set()
    evidence: set[str] = set()

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            if set(value) >= {"assumption_refs", "evidence_refs"}:
                assumptions.update(value["assumption_refs"])
                evidence.update(value["evidence_refs"])
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(document)
    return {
        "assumption_refs": sorted(assumptions),
        "evidence_refs": sorted(evidence),
    }


def _metric_decimal(
    key: str,
    value: Decimal | None,
    money_scale: int,
    ratio_scale: int,
) -> str | None:
    if value is None:
        return None
    scale = (
        money_scale
        if key in {"npv_unlevered", "funding_need", "break_even"}
        else ratio_scale
    )
    return _decimal(value, scale)


def _legacy_float(value: Decimal | None, scale: int) -> float | None:
    return None if value is None else float(_decimal(value, scale))


def _decimal(value: Decimal, scale: int) -> str:
    quantum = Decimal(1).scaleb(-scale)
    coefficient_digits = len(value.as_tuple().digits)
    integer_digits = max(1, value.adjusted() + 1)
    with localcontext() as context:
        context.prec = max(
            28,
            coefficient_digits + scale + 4,
            integer_digits + scale + 4,
        )
        rounded = value.quantize(quantum, rounding=ROUND_HALF_EVEN)
    return format(rounded, "f")
