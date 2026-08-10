from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

from .serialization import canonical_json, canonical_sha256
from .timeline import monthly_periods, period_index


_DECIMAL = re.compile(r"^-?(0|[1-9][0-9]*)(\.[0-9]{1,8})?$")
_SHA256 = re.compile(r"^sha256:[a-f0-9]{64}$")
_CURRENCY = re.compile(r"^[A-Z]{3}$")
_SCENARIO_TARGET = re.compile(
    r"^(?:"
    r"\$\.revenue_streams\[(?P<revenue_id>[A-Za-z0-9_-]{1,84})\]\."
    r"(?P<revenue_series>volume_series|price_series|variable_cost_series|capacity_series)"
    r"\[(?P<revenue_period>\*|[0-9]{4}-(?:0[1-9]|1[0-2]))\]\.value"
    r"|\$\.operating_costs\[(?P<opex_id>[A-Za-z0-9_-]{1,84})\]\.schedule"
    r"\[(?P<opex_period>\*|[0-9]{4}-(?:0[1-9]|1[0-2]))\]\.value"
    r"|\$\.capex_assets\[(?P<asset_id>[A-Za-z0-9_-]{1,84})\]\."
    r"(?P<asset_field>cost|residual_value)"
    r"|\$\.working_capital\.(?P<working_field>dso_days|dio_days|dpo_days)"
    r"|\$\.valuation_policy\."
    r"(?P<valuation_field>discount_rate_annual|finance_rate_annual|reinvestment_rate_annual)"
    r"|\$\.financing\.debt_tranches\[(?P<tranche_id>[A-Za-z0-9_-]{1,84})\]\."
    r"(?P<tranche_field>annual_rate)"
    r")$"
)

REVENUE_MODELS = frozenset(
    {
        "product_unit",
        "service_capacity",
        "subscription",
        "project_contract",
        "commission_gmv",
        "room_bed_seat",
        "rent_lease",
        "agriculture_cycle",
        "manufacturing_yield",
        "transport_trip",
        "professional_hours",
        "custom_reviewed",
    }
)

REQUIRED_TOP_LEVEL = frozenset(
    {
        "schema_version",
        "document_id",
        "organization_id",
        "project_id",
        "run_id",
        "currency",
        "forecast",
        "archetype_ref",
        "rounding_policy",
        "revenue_streams",
        "operating_costs",
        "capex_assets",
        "working_capital",
        "financing",
        "fiscal_policy",
        "valuation_policy",
        "scenarios",
        "metadata",
    }
)


class FinanceContractError(ValueError):
    def __init__(self, code: str, field_ref: str, message: str) -> None:
        super().__init__(f"{code} at {field_ref}: {message}")
        self.code = code
        self.field_ref = field_ref
        self.message = message


@dataclass(frozen=True, slots=True)
class ServerBinding:
    organization_id: str
    project_id: str
    run_id: str
    approved_manifest_id: str
    approved_manifest_hash: str
    policy_ref: str


@dataclass(frozen=True, slots=True)
class ValidatedFinanceInput:
    document_id: str
    organization_id: str
    project_id: str
    run_id: str
    currency: str
    periods: tuple[str, ...]
    canonical_document: str
    input_hash: str

    def thaw(self) -> dict[str, Any]:
        return json.loads(self.canonical_document)


def parse_decimal(
    value: Any,
    field_ref: str,
    *,
    allow_negative: bool = True,
) -> Decimal:
    if not isinstance(value, str) or not _DECIMAL.fullmatch(value):
        raise FinanceContractError(
            "FIN2_DECIMAL_FORMAT",
            field_ref,
            "value must be a plain decimal string with at most 8 fractional digits",
        )
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise FinanceContractError("FIN2_DECIMAL_FORMAT", field_ref, "invalid decimal") from exc
    if not parsed.is_finite():
        raise FinanceContractError("FIN2_DECIMAL_FINITE", field_ref, "value must be finite")
    if not allow_negative and parsed < 0:
        raise FinanceContractError("FIN2_DECIMAL_NEGATIVE", field_ref, "value must be non-negative")
    return parsed


def parse_scenario_target(value: Any, field_ref: str) -> dict[str, str]:
    if not isinstance(value, str):
        raise FinanceContractError(
            "FIN2_SCENARIO_TARGET",
            field_ref,
            "target_ref must be a string",
        )
    match = _SCENARIO_TARGET.fullmatch(value)
    if match is None:
        raise FinanceContractError(
            "FIN2_SCENARIO_TARGET",
            field_ref,
            "target_ref is outside the governed scenario allowlist",
        )
    return {
        key: item
        for key, item in match.groupdict().items()
        if item is not None
    }


def validate_finance_input(
    document: Mapping[str, Any],
    *,
    binding: ServerBinding,
) -> ValidatedFinanceInput:
    if not isinstance(document, Mapping):
        raise FinanceContractError("FIN2_DOCUMENT_TYPE", "$", "document must be an object")

    missing = REQUIRED_TOP_LEVEL.difference(document)
    if missing:
        raise FinanceContractError(
            "FIN2_REQUIRED_FIELD",
            "$",
            f"missing required fields: {','.join(sorted(missing))}",
        )
    unknown = set(document).difference(REQUIRED_TOP_LEVEL)
    if unknown:
        raise FinanceContractError(
            "FIN2_UNKNOWN_FIELD",
            "$",
            f"unknown top-level fields: {','.join(sorted(unknown))}",
        )
    _validate_closed_shape(document)
    if document["schema_version"] != "finance-model-input.v2":
        raise FinanceContractError(
            "FIN2_SCHEMA_VERSION", "$.schema_version", "unsupported schema version"
        )

    _validate_server_binding(document, binding)
    currency = document["currency"]
    if not isinstance(currency, str) or not _CURRENCY.fullmatch(currency):
        raise FinanceContractError(
            "FIN2_CURRENCY", "$.currency", "currency must be an ISO-4217 alpha-3 code"
        )

    forecast = _mapping(document["forecast"], "$.forecast")
    start_period = _text(forecast.get("start_period"), "$.forecast.start_period")
    count = forecast.get("monthly_periods")
    try:
        periods = monthly_periods(start_period, count)
    except (TypeError, ValueError) as exc:
        raise FinanceContractError("FIN2_FORECAST_HORIZON", "$.forecast", str(exc)) from exc
    horizon = frozenset(periods)

    _validate_rounding(document["rounding_policy"])
    _validate_revenue(document["revenue_streams"], horizon)
    _validate_opex(document["operating_costs"], horizon)
    _validate_capex(document["capex_assets"], horizon)
    _validate_working_capital(document["working_capital"], horizon)
    _validate_financing(document["financing"], horizon)
    _validate_fiscal(document["fiscal_policy"])
    _validate_valuation(document["valuation_policy"])
    _validate_scenarios(document["scenarios"])

    try:
        canonical = canonical_json(document)
    except (TypeError, ValueError) as exc:
        raise FinanceContractError(
            "FIN2_CANONICAL_SERIALIZATION", "$", "document is not canonically serializable"
        ) from exc

    return ValidatedFinanceInput(
        document_id=_text(document["document_id"], "$.document_id"),
        organization_id=binding.organization_id,
        project_id=binding.project_id,
        run_id=binding.run_id,
        currency=currency,
        periods=periods,
        canonical_document=canonical,
        input_hash=canonical_sha256(document),
    )


def _validate_closed_shape(document: Mapping[str, Any]) -> None:
    _reject_unknown(_mapping(document["forecast"], "$.forecast"), {"start_period", "monthly_periods", "construction_periods"}, "$.forecast")
    _reject_unknown(_mapping(document["archetype_ref"], "$.archetype_ref"), {"archetype_id", "version", "registry_hash"}, "$.archetype_ref")
    _reject_unknown(_mapping(document["rounding_policy"], "$.rounding_policy"), {"money_scale", "ratio_scale", "mode"}, "$.rounding_policy")
    _reject_unknown(_mapping(document["metadata"], "$.metadata"), {"approved_manifest_id", "approved_manifest_hash", "policy_ref"}, "$.metadata")

    for index, raw in enumerate(_sequence(document["revenue_streams"], "$.revenue_streams", minimum=1, maximum=200)):
        ref = f"$.revenue_streams[{index}]"
        row = _mapping(raw, ref)
        _reject_unknown(row, {"stream_id", "model_kind", "unit", "volume_series", "price_series", "variable_cost_series", "capacity_series", "lineage"}, ref)
        for name in ("volume_series", "price_series", "variable_cost_series", "capacity_series"):
            if name in row:
                _close_series(row[name], f"{ref}.{name}")
        _close_lineage(row.get("lineage"), f"{ref}.lineage")

    for index, raw in enumerate(_sequence(document["operating_costs"], "$.operating_costs", minimum=0, maximum=500)):
        ref = f"$.operating_costs[{index}]"
        row = _mapping(raw, ref)
        _reject_unknown(row, {"cost_id", "behavior", "driver_ref", "schedule", "lineage"}, ref)
        _close_series(row.get("schedule"), f"{ref}.schedule")
        _close_lineage(row.get("lineage"), f"{ref}.lineage")

    for index, raw in enumerate(_sequence(document["capex_assets"], "$.capex_assets", minimum=0, maximum=500)):
        ref = f"$.capex_assets[{index}]"
        row = _mapping(raw, ref)
        _reject_unknown(row, {"asset_id", "acquisition_period", "cost", "useful_life_months", "depreciation_method", "residual_value", "disposal_period", "replacement_asset_ref", "lineage"}, ref)
        _close_lineage(row.get("lineage"), f"{ref}.lineage")

    working = _mapping(document["working_capital"], "$.working_capital")
    _reject_unknown(working, {"mode", "dso_days", "dio_days", "dpo_days", "accounts_receivable", "inventory", "accounts_payable", "lineage"}, "$.working_capital")
    for name in ("accounts_receivable", "inventory", "accounts_payable"):
        if name in working:
            _close_series(working[name], f"$.working_capital.{name}")
    _close_lineage(working.get("lineage"), "$.working_capital.lineage")

    financing = _mapping(document["financing"], "$.financing")
    _reject_unknown(financing, {"equity_contributions", "debt_tranches"}, "$.financing")
    for index, raw in enumerate(_sequence(financing.get("equity_contributions"), "$.financing.equity_contributions", minimum=1, maximum=50)):
        ref = f"$.financing.equity_contributions[{index}]"
        row = _mapping(raw, ref)
        _reject_unknown(row, {"period", "amount", "lineage"}, ref)
        _close_lineage(row.get("lineage"), f"{ref}.lineage")
    for index, raw in enumerate(_sequence(financing.get("debt_tranches"), "$.financing.debt_tranches", minimum=0, maximum=20)):
        ref = f"$.financing.debt_tranches[{index}]"
        row = _mapping(raw, ref)
        _reject_unknown(row, {"tranche_id", "drawdowns", "annual_rate", "tenor_months", "principal_grace_months", "interest_grace_policy", "repayment_profile", "balloon_amount", "fee_treatment", "fees", "lineage"}, ref)
        for item_index, raw_draw in enumerate(_sequence(row.get("drawdowns"), f"{ref}.drawdowns", minimum=1, maximum=50)):
            _reject_unknown(_mapping(raw_draw, f"{ref}.drawdowns[{item_index}]"), {"period", "amount"}, f"{ref}.drawdowns[{item_index}]")
        for item_index, raw_fee in enumerate(_sequence(row.get("fees"), f"{ref}.fees", minimum=0, maximum=30)):
            _reject_unknown(_mapping(raw_fee, f"{ref}.fees[{item_index}]"), {"fee_id", "period", "amount"}, f"{ref}.fees[{item_index}]")
        _close_lineage(row.get("lineage"), f"{ref}.lineage")

    valuation = _mapping(document["valuation_policy"], "$.valuation_policy")
    _reject_unknown(valuation, {"discount_rate_annual", "finance_rate_annual", "reinvestment_rate_annual", "lineage"}, "$.valuation_policy")
    _close_lineage(valuation.get("lineage"), "$.valuation_policy.lineage")

    fiscal = _mapping(document["fiscal_policy"], "$.fiscal_policy")
    _reject_unknown(fiscal, {"policy_id", "effective_from", "modules", "vat_rate", "income_tax_rate", "zakat_rate", "lineage"}, "$.fiscal_policy")
    _close_lineage(fiscal.get("lineage"), "$.fiscal_policy.lineage")

    for index, raw in enumerate(_sequence(document["scenarios"], "$.scenarios", minimum=1, maximum=20)):
        ref = f"$.scenarios[{index}]"
        row = _mapping(raw, ref)
        _reject_unknown(row, {"scenario_id", "kind", "overrides", "simulation"}, ref)
        for item_index, raw_override in enumerate(_sequence(row.get("overrides"), f"{ref}.overrides", minimum=0, maximum=200)):
            _reject_unknown(_mapping(raw_override, f"{ref}.overrides[{item_index}]"), {"target_ref", "operation", "value"}, f"{ref}.overrides[{item_index}]")
        if "simulation" in row:
            _reject_unknown(_mapping(row["simulation"], f"{ref}.simulation"), {"seed", "iterations", "distribution_profile_ref", "correlation_profile_ref"}, f"{ref}.simulation")


def _close_series(value: Any, field_ref: str) -> None:
    for index, raw in enumerate(_sequence(value, field_ref, minimum=1, maximum=240)):
        _reject_unknown(_mapping(raw, f"{field_ref}[{index}]"), {"period", "value"}, f"{field_ref}[{index}]")


def _close_lineage(value: Any, field_ref: str) -> None:
    _reject_unknown(_mapping(value, field_ref), {"assumption_refs", "evidence_refs"}, field_ref)


def _reject_unknown(row: Mapping[str, Any], allowed: set[str], field_ref: str) -> None:
    unknown = set(row).difference(allowed)
    if unknown:
        raise FinanceContractError(
            "FIN2_UNKNOWN_FIELD",
            field_ref,
            f"unknown fields: {','.join(sorted(unknown))}",
        )


def _validate_server_binding(document: Mapping[str, Any], binding: ServerBinding) -> None:
    expected = {
        "$.organization_id": (document["organization_id"], binding.organization_id),
        "$.project_id": (document["project_id"], binding.project_id),
        "$.run_id": (document["run_id"], binding.run_id),
    }
    metadata = _mapping(document["metadata"], "$.metadata")
    expected.update(
        {
            "$.metadata.approved_manifest_id": (
                metadata.get("approved_manifest_id"),
                binding.approved_manifest_id,
            ),
            "$.metadata.approved_manifest_hash": (
                metadata.get("approved_manifest_hash"),
                binding.approved_manifest_hash,
            ),
            "$.metadata.policy_ref": (metadata.get("policy_ref"), binding.policy_ref),
        }
    )
    for field_ref, (actual, trusted) in expected.items():
        if not isinstance(trusted, str) or not trusted:
            raise FinanceContractError(
                "FIN2_SERVER_BINDING_MISSING", field_ref, "trusted server binding is missing"
            )
        if actual != trusted:
            raise FinanceContractError(
                "FIN2_SERVER_BINDING_MISMATCH",
                field_ref,
                "document value does not match trusted server context",
            )
    if not _SHA256.fullmatch(binding.approved_manifest_hash):
        raise FinanceContractError(
            "FIN2_MANIFEST_HASH",
            "$.metadata.approved_manifest_hash",
            "manifest hash must be sha256-prefixed lowercase hex",
        )


def _validate_rounding(value: Any) -> None:
    policy = _mapping(value, "$.rounding_policy")
    if policy.get("mode") != "ROUND_HALF_EVEN":
        raise FinanceContractError(
            "FIN2_ROUNDING_MODE", "$.rounding_policy.mode", "unsupported rounding mode"
        )
    money_scale = policy.get("money_scale")
    ratio_scale = policy.get("ratio_scale")
    if isinstance(money_scale, bool) or not isinstance(money_scale, int) or not 0 <= money_scale <= 4:
        raise FinanceContractError(
            "FIN2_ROUNDING_SCALE", "$.rounding_policy.money_scale", "must be 0..4"
        )
    if isinstance(ratio_scale, bool) or not isinstance(ratio_scale, int) or not 4 <= ratio_scale <= 8:
        raise FinanceContractError(
            "FIN2_ROUNDING_SCALE", "$.rounding_policy.ratio_scale", "must be 4..8"
        )


def _validate_revenue(value: Any, horizon: frozenset[str]) -> None:
    rows = _sequence(value, "$.revenue_streams", minimum=1, maximum=200)
    _unique_ids(rows, "stream_id", "$.revenue_streams")
    for index, raw in enumerate(rows):
        ref = f"$.revenue_streams[{index}]"
        row = _mapping(raw, ref)
        if row.get("model_kind") not in REVENUE_MODELS:
            raise FinanceContractError(
                "FIN2_REVENUE_MODEL", f"{ref}.model_kind", "unregistered revenue model"
            )
        for name in ("volume_series", "price_series", "variable_cost_series"):
            _validate_series(row.get(name), f"{ref}.{name}", horizon, allow_negative=False)
        if "capacity_series" in row:
            _validate_series(
                row["capacity_series"], f"{ref}.capacity_series", horizon, allow_negative=False
            )
        _validate_lineage(row.get("lineage"), f"{ref}.lineage")


def _validate_opex(value: Any, horizon: frozenset[str]) -> None:
    rows = _sequence(value, "$.operating_costs", minimum=0, maximum=500)
    _unique_ids(rows, "cost_id", "$.operating_costs")
    for index, raw in enumerate(rows):
        ref = f"$.operating_costs[{index}]"
        row = _mapping(raw, ref)
        if row.get("behavior") not in {"fixed", "variable", "step", "seasonal"}:
            raise FinanceContractError("FIN2_OPEX_BEHAVIOR", f"{ref}.behavior", "unsupported")
        _validate_series(row.get("schedule"), f"{ref}.schedule", horizon, allow_negative=False)
        _validate_lineage(row.get("lineage"), f"{ref}.lineage")


def _validate_capex(value: Any, horizon: frozenset[str]) -> None:
    rows = _sequence(value, "$.capex_assets", minimum=0, maximum=500)
    _unique_ids(rows, "asset_id", "$.capex_assets")
    for index, raw in enumerate(rows):
        ref = f"$.capex_assets[{index}]"
        row = _mapping(raw, ref)
        _period_in_horizon(row.get("acquisition_period"), f"{ref}.acquisition_period", horizon)
        cost = parse_decimal(row.get("cost"), f"{ref}.cost", allow_negative=False)
        residual = parse_decimal(
            row.get("residual_value"), f"{ref}.residual_value", allow_negative=False
        )
        if residual > cost:
            raise FinanceContractError(
                "FIN2_CAPEX_RESIDUAL", f"{ref}.residual_value", "must not exceed cost"
            )
        life = row.get("useful_life_months")
        if isinstance(life, bool) or not isinstance(life, int) or not 1 <= life <= 1200:
            raise FinanceContractError(
                "FIN2_CAPEX_LIFE", f"{ref}.useful_life_months", "must be 1..1200"
            )
        if row.get("depreciation_method") != "straight_line":
            raise FinanceContractError(
                "FIN2_DEPRECIATION_METHOD",
                f"{ref}.depreciation_method",
                "only straight_line is supported in S2",
            )
        if "disposal_period" in row:
            _period_in_horizon(row["disposal_period"], f"{ref}.disposal_period", horizon)
        _validate_lineage(row.get("lineage"), f"{ref}.lineage")


def _validate_working_capital(value: Any, horizon: frozenset[str]) -> None:
    row = _mapping(value, "$.working_capital")
    mode = row.get("mode")
    if mode == "days":
        for name in ("dso_days", "dio_days", "dpo_days"):
            parse_decimal(row.get(name), f"$.working_capital.{name}", allow_negative=False)
    elif mode == "explicit_schedule":
        for name in ("accounts_receivable", "inventory", "accounts_payable"):
            _validate_series(
                row.get(name), f"$.working_capital.{name}", horizon, allow_negative=False
            )
    else:
        raise FinanceContractError(
            "FIN2_WORKING_CAPITAL_MODE", "$.working_capital.mode", "unsupported mode"
        )
    _validate_lineage(row.get("lineage"), "$.working_capital.lineage")


def _validate_financing(value: Any, horizon: frozenset[str]) -> None:
    financing = _mapping(value, "$.financing")
    equity = _sequence(
        financing.get("equity_contributions"),
        "$.financing.equity_contributions",
        minimum=1,
        maximum=50,
    )
    for index, raw in enumerate(equity):
        ref = f"$.financing.equity_contributions[{index}]"
        row = _mapping(raw, ref)
        _period_in_horizon(row.get("period"), f"{ref}.period", horizon)
        parse_decimal(row.get("amount"), f"{ref}.amount", allow_negative=False)
        _validate_lineage(row.get("lineage"), f"{ref}.lineage")

    debt = _sequence(
        financing.get("debt_tranches"),
        "$.financing.debt_tranches",
        minimum=0,
        maximum=20,
    )
    _unique_ids(debt, "tranche_id", "$.financing.debt_tranches")
    for index, raw in enumerate(debt):
        ref = f"$.financing.debt_tranches[{index}]"
        row = _mapping(raw, ref)
        parse_decimal(row.get("annual_rate"), f"{ref}.annual_rate", allow_negative=False)
        tenor = row.get("tenor_months")
        grace = row.get("principal_grace_months")
        if isinstance(tenor, bool) or not isinstance(tenor, int) or not 1 <= tenor <= 600:
            raise FinanceContractError("FIN2_DEBT_TENOR", f"{ref}.tenor_months", "must be 1..600")
        if isinstance(grace, bool) or not isinstance(grace, int) or not 0 <= grace <= 120:
            raise FinanceContractError(
                "FIN2_DEBT_GRACE", f"{ref}.principal_grace_months", "must be 0..120"
            )
        if grace >= tenor:
            raise FinanceContractError(
                "FIN2_DEBT_GRACE", f"{ref}.principal_grace_months", "must be less than tenor"
            )
        if row.get("interest_grace_policy") not in {"paid", "capitalized"}:
            raise FinanceContractError(
                "FIN2_DEBT_INTEREST_GRACE", f"{ref}.interest_grace_policy", "unsupported"
            )
        if row.get("repayment_profile") not in {
            "annuity",
            "equal_principal",
            "bullet",
            "custom_reviewed",
        }:
            raise FinanceContractError(
                "FIN2_DEBT_PROFILE", f"{ref}.repayment_profile", "unsupported"
            )
        if row.get("fee_treatment") != "expense_upfront":
            raise FinanceContractError(
                "FIN2_DEBT_FEE_TREATMENT",
                f"{ref}.fee_treatment",
                "S2-B requires explicit expense_upfront treatment",
            )
        drawdowns = _sequence(row.get("drawdowns"), f"{ref}.drawdowns", minimum=1, maximum=50)
        for item_index, draw in enumerate(drawdowns):
            draw_ref = f"{ref}.drawdowns[{item_index}]"
            item = _mapping(draw, draw_ref)
            _period_in_horizon(item.get("period"), f"{draw_ref}.period", horizon)
            parse_decimal(item.get("amount"), f"{draw_ref}.amount", allow_negative=False)
        for item_index, fee in enumerate(
            _sequence(row.get("fees"), f"{ref}.fees", minimum=0, maximum=30)
        ):
            fee_ref = f"{ref}.fees[{item_index}]"
            item = _mapping(fee, fee_ref)
            _period_in_horizon(item.get("period"), f"{fee_ref}.period", horizon)
            parse_decimal(item.get("amount"), f"{fee_ref}.amount", allow_negative=False)
        if "balloon_amount" in row:
            parse_decimal(row["balloon_amount"], f"{ref}.balloon_amount", allow_negative=False)
        _validate_lineage(row.get("lineage"), f"{ref}.lineage")


def _validate_fiscal(value: Any) -> None:
    policy = _mapping(value, "$.fiscal_policy")
    modules = _sequence(policy.get("modules"), "$.fiscal_policy.modules", minimum=0, maximum=3)
    if len(set(modules)) != len(modules) or not set(modules) <= {"vat", "income_tax", "zakat"}:
        raise FinanceContractError(
            "FIN2_FISCAL_MODULES", "$.fiscal_policy.modules", "invalid or duplicate modules"
        )
    rate_fields = {"vat": "vat_rate", "income_tax": "income_tax_rate", "zakat": "zakat_rate"}
    combined = Decimal("0")
    for module in modules:
        rate = parse_decimal(
            policy.get(rate_fields[module]),
            f"$.fiscal_policy.{rate_fields[module]}",
            allow_negative=False,
        )
        if rate > 1:
            raise FinanceContractError(
                "FIN2_FISCAL_RATE", f"$.fiscal_policy.{rate_fields[module]}", "must be <= 1"
            )
        if module != "vat":
            combined += rate
    if combined > 1:
        raise FinanceContractError(
            "FIN2_FISCAL_RATE",
            "$.fiscal_policy.modules",
            "combined income tax and zakat rates must be <= 1",
        )
    _validate_lineage(policy.get("lineage"), "$.fiscal_policy.lineage")


def _validate_valuation(value: Any) -> None:
    policy = _mapping(value, "$.valuation_policy")
    for name in ("discount_rate_annual", "finance_rate_annual", "reinvestment_rate_annual"):
        rate = parse_decimal(policy.get(name), f"$.valuation_policy.{name}", allow_negative=False)
        if rate > Decimal("10"):
            raise FinanceContractError(
                "FIN2_VALUATION_RATE",
                f"$.valuation_policy.{name}",
                "annual rate must be <= 10",
            )
    _validate_lineage(policy.get("lineage"), "$.valuation_policy.lineage")


def _validate_scenarios(value: Any) -> None:
    rows = _sequence(value, "$.scenarios", minimum=1, maximum=20)
    _unique_ids(rows, "scenario_id", "$.scenarios")
    baseline_count = sum(
        int(_mapping(raw, f"$.scenarios[{index}]").get("kind") == "baseline")
        for index, raw in enumerate(rows)
    )
    if baseline_count != 1:
        raise FinanceContractError(
            "FIN2_BASELINE_COUNT",
            "$.scenarios",
            "exactly one baseline scenario is required",
        )

    for index, raw in enumerate(rows):
        ref = f"$.scenarios[{index}]"
        row = _mapping(raw, ref)
        kind = row.get("kind")
        if kind not in {"baseline", "deterministic", "simulation"}:
            raise FinanceContractError(
                "FIN2_SCENARIO_KIND",
                f"{ref}.kind",
                "unsupported",
            )
        overrides = _sequence(
            row.get("overrides"),
            f"{ref}.overrides",
            minimum=0,
            maximum=200,
        )
        if kind == "baseline" and overrides:
            raise FinanceContractError(
                "FIN2_BASELINE_OVERRIDE",
                f"{ref}.overrides",
                "baseline must not contain overrides",
            )
        if kind == "deterministic" and not overrides:
            raise FinanceContractError(
                "FIN2_SCENARIO_OVERRIDE_REQUIRED",
                f"{ref}.overrides",
                "deterministic scenario requires at least one override",
            )
        if kind == "simulation" and overrides:
            raise FinanceContractError(
                "FIN2_SIMULATION_OVERRIDE",
                f"{ref}.overrides",
                "simulation scenario must use its governed profile",
            )
        if kind != "simulation" and "simulation" in row:
            raise FinanceContractError(
                "FIN2_SCENARIO_SIMULATION_UNEXPECTED",
                f"{ref}.simulation",
                "simulation settings are allowed only for simulation scenarios",
            )

        seen_targets: set[str] = set()
        for item_index, raw_override in enumerate(overrides):
            override_ref = f"{ref}.overrides[{item_index}]"
            override = _mapping(raw_override, override_ref)
            operation = override.get("operation")
            if operation not in {"replace", "multiply", "add"}:
                raise FinanceContractError(
                    "FIN2_SCENARIO_OPERATION",
                    f"{override_ref}.operation",
                    "unsupported",
                )
            target_ref = override.get("target_ref")
            parse_scenario_target(target_ref, f"{override_ref}.target_ref")
            if target_ref in seen_targets:
                raise FinanceContractError(
                    "FIN2_SCENARIO_TARGET_DUPLICATE",
                    f"{override_ref}.target_ref",
                    "a target may be overridden only once per scenario",
                )
            seen_targets.add(target_ref)
            parsed = parse_decimal(
                override.get("value"),
                f"{override_ref}.value",
            )
            if operation == "multiply" and parsed < 0:
                raise FinanceContractError(
                    "FIN2_SCENARIO_MULTIPLIER_NEGATIVE",
                    f"{override_ref}.value",
                    "multiplier must be non-negative",
                )

        if kind == "simulation":
            simulation = _mapping(row.get("simulation"), f"{ref}.simulation")
            seed = simulation.get("seed")
            iterations = simulation.get("iterations")
            if (
                isinstance(seed, bool)
                or not isinstance(seed, int)
                or not 0 <= seed <= 2147483647
            ):
                raise FinanceContractError(
                    "FIN2_SIMULATION_SEED",
                    f"{ref}.simulation.seed",
                    "invalid seed",
                )
            if (
                isinstance(iterations, bool)
                or not isinstance(iterations, int)
                or not 100 <= iterations <= 100000
            ):
                raise FinanceContractError(
                    "FIN2_SIMULATION_ITERATIONS",
                    f"{ref}.simulation.iterations",
                    "must be 100..100000",
                )


def _validate_series(
    value: Any,
    field_ref: str,
    horizon: frozenset[str],
    *,
    allow_negative: bool,
) -> None:
    rows = _sequence(value, field_ref, minimum=1, maximum=240)
    previous: int | None = None
    seen: set[str] = set()
    for index, raw in enumerate(rows):
        ref = f"{field_ref}[{index}]"
        row = _mapping(raw, ref)
        period = _period_in_horizon(row.get("period"), f"{ref}.period", horizon)
        if period in seen:
            raise FinanceContractError("FIN2_PERIOD_DUPLICATE", f"{ref}.period", "duplicate period")
        current = period_index(period)
        if previous is not None and current <= previous:
            raise FinanceContractError(
                "FIN2_PERIOD_ORDER", f"{ref}.period", "periods must be strictly increasing"
            )
        seen.add(period)
        previous = current
        parse_decimal(row.get("value"), f"{ref}.value", allow_negative=allow_negative)
    if seen != horizon:
        missing = sorted(horizon.difference(seen))
        raise FinanceContractError(
            "FIN2_PERIOD_COVERAGE",
            field_ref,
            f"series must explicitly cover the full horizon; missing {len(missing)} periods",
        )


def _validate_lineage(value: Any, field_ref: str) -> None:
    lineage = _mapping(value, field_ref)
    assumptions = _sequence(
        lineage.get("assumption_refs"), f"{field_ref}.assumption_refs", minimum=1, maximum=100
    )
    evidence = _sequence(
        lineage.get("evidence_refs"), f"{field_ref}.evidence_refs", minimum=0, maximum=100
    )
    for index, ref in enumerate((*assumptions, *evidence)):
        if not isinstance(ref, str) or not ref:
            raise FinanceContractError(
                "FIN2_LINEAGE_REF", f"{field_ref}[{index}]", "lineage refs must be non-empty text"
            )


def _period_in_horizon(value: Any, field_ref: str, horizon: frozenset[str]) -> str:
    period = _text(value, field_ref)
    try:
        period_index(period)
    except ValueError as exc:
        raise FinanceContractError("FIN2_PERIOD_FORMAT", field_ref, str(exc)) from exc
    if period not in horizon:
        raise FinanceContractError("FIN2_PERIOD_HORIZON", field_ref, "period is outside forecast")
    return period


def _unique_ids(rows: Sequence[Any], key: str, field_ref: str) -> None:
    seen: set[str] = set()
    for index, raw in enumerate(rows):
        row = _mapping(raw, f"{field_ref}[{index}]")
        identifier = _text(row.get(key), f"{field_ref}[{index}].{key}")
        if identifier in seen:
            raise FinanceContractError(
                "FIN2_DUPLICATE_ID", f"{field_ref}[{index}].{key}", "duplicate identifier"
            )
        seen.add(identifier)


def _mapping(value: Any, field_ref: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise FinanceContractError("FIN2_OBJECT_TYPE", field_ref, "must be an object")
    return value


def _sequence(
    value: Any,
    field_ref: str,
    *,
    minimum: int,
    maximum: int,
) -> Sequence[Any]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise FinanceContractError("FIN2_ARRAY_TYPE", field_ref, "must be an array")
    if not minimum <= len(value) <= maximum:
        raise FinanceContractError(
            "FIN2_ARRAY_BOUNDS", field_ref, f"must contain {minimum}..{maximum} items"
        )
    return value


def _text(value: Any, field_ref: str) -> str:
    if not isinstance(value, str) or not value:
        raise FinanceContractError("FIN2_TEXT_TYPE", field_ref, "must be non-empty text")
    return value
