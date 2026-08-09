"""Finance Model v2 dark-build package.

This package is not connected to the canonical runtime until later ACR-FIN-002 gates pass.
"""

from .contracts import (
    FinanceContractError,
    ServerBinding,
    ValidatedFinanceInput,
    parse_decimal,
    validate_finance_input,
)
from .model import FinancialModel, FinancialPeriod, InvariantResult
from .result import ENGINE_VERSION, serialize_finance_result
from .serialization import canonical_json, canonical_sha256
from .statements import build_financial_model
from .timeline import add_months, monthly_periods, period_from_index, period_index

__all__ = [
    "ENGINE_VERSION",
    "FinanceContractError",
    "FinancialModel",
    "FinancialPeriod",
    "InvariantResult",
    "ServerBinding",
    "ValidatedFinanceInput",
    "add_months",
    "canonical_json",
    "canonical_sha256",
    "build_financial_model",
    "monthly_periods",
    "parse_decimal",
    "period_from_index",
    "period_index",
    "serialize_finance_result",
    "validate_finance_input",
]
