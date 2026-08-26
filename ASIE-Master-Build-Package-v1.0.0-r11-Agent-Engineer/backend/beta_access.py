from __future__ import annotations

from copy import deepcopy
from typing import Any


_BETA_ACCESS_STATUS: dict[str, Any] = {
    "contract_id": "beta.full-access.v1",
    "program": "ASIE_CLOSED_LIVE_BETA",
    "access_mode": "invite_only",
    "entitlement_profile": "beta_full_access",
    "billing_status": "not_applicable_during_beta",
    "usage_metering_mode": "observability_only",
    "upgrade_required": False,
    "payment_method_required": False,
    "feature_restrictions": [],
    "commercial_quotas_enforced": False,
    "automatic_paid_conversion": False,
    "retroactive_charges_allowed": False,
    "pricing_decision_status": "not_decided",
    "provider_exhaustion_behavior": "operator_incident_retry_without_upsell",
    "technical_protection_limits": {
        "purpose": "security_reliability_and_abuse_prevention_only",
        "may_trigger_upgrade_prompt": False,
        "may_create_invoice": False,
        "may_permanently_disable_feature": False,
    },
    "account_suspension_policy": {
        "allowed_reasons": ["verified_abuse", "verified_security_threat"],
        "normal_beta_usage_is_suspension_reason": False,
        "non_payment_is_suspension_reason": False,
    },
    "user_message_ar": "البيتا مجانية وكاملة للمستخدمين المدعوين، ولا تتطلب دفعًا أو ترقية إلى باقة أخرى.",
}


def beta_access_status() -> dict[str, Any]:
    """Return an isolated copy of the closed-beta commercial access contract."""

    return deepcopy(_BETA_ACCESS_STATUS)


def beta_billing_mutation_blocked() -> bool:
    """Billing and subscription mutations stay dormant until a later pricing decision."""

    return True


def beta_provider_incident(*, provider_id: str, correlation_id: str | None = None) -> dict[str, Any]:
    provider = str(provider_id or "").strip()
    if not provider:
        raise ValueError("provider_id_required")
    return {
        "contract_id": "beta.provider-incident.v1",
        "status": "temporarily_unavailable",
        "provider_id": provider,
        "correlation_id": correlation_id,
        "retry_scheduled": True,
        "upgrade_required": False,
        "payment_required": False,
        "user_message_ar": "الخدمة الخارجية متوقفة مؤقتًا، حُفظ طلبك وسنعيد المحاولة.",
    }
