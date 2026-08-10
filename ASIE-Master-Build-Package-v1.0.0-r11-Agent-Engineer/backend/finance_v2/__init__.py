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
from .risk_profiles import (
    ManifestProfileBinding,
    ResolvedRiskProfileBinding,
    ValidatedRiskProfile,
    admit_risk_profile,
    profile_content_hash,
    validate_risk_profile,
)
from .serialization import canonical_json, canonical_sha256
from .statements import build_financial_model
from .timeline import add_months, monthly_periods, period_from_index, period_index

__all__ = [
    "ENGINE_VERSION",
    "FinanceContractError",
    "FinancialModel",
    "FinancialPeriod",
    "InvariantResult",
    "ManifestProfileBinding",
    "ResolvedRiskProfileBinding",
    "ServerBinding",
    "ValidatedFinanceInput",
    "ValidatedRiskProfile",
    "add_months",
    "admit_risk_profile",
    "canonical_json",
    "canonical_sha256",
    "build_financial_model",
    "monthly_periods",
    "parse_decimal",
    "period_from_index",
    "period_index",
    "profile_content_hash",
    "serialize_finance_result",
    "validate_finance_input",
    "validate_risk_profile",
]
