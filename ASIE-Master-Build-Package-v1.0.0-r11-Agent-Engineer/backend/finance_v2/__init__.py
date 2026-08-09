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
from .serialization import canonical_json, canonical_sha256
from .timeline import add_months, monthly_periods, period_from_index, period_index

__all__ = [
    "FinanceContractError",
    "ServerBinding",
    "ValidatedFinanceInput",
    "add_months",
    "canonical_json",
    "canonical_sha256",
    "monthly_periods",
    "parse_decimal",
    "period_from_index",
    "period_index",
    "validate_finance_input",
]
