from __future__ import annotations

from backend.beta_access import (
    beta_access_status,
    beta_billing_mutation_blocked,
    beta_provider_incident,
)


def test_closed_beta_is_full_access_free_and_never_auto_converts() -> None:
    """All invited beta users receive one free, unrestricted entitlement."""

    status = beta_access_status()
    assert status["entitlement_profile"] == "beta_full_access"
    assert status["billing_status"] == "not_applicable_during_beta"
    assert status["usage_metering_mode"] == "observability_only"
    assert status["feature_restrictions"] == []
    assert status["upgrade_required"] is False
    assert status["payment_method_required"] is False
    assert status["commercial_quotas_enforced"] is False
    assert status["automatic_paid_conversion"] is False
    assert status["retroactive_charges_allowed"] is False


def test_status_callers_cannot_mutate_the_canonical_contract() -> None:
    """A caller cannot impose a restriction by mutating a returned snapshot."""

    first = beta_access_status()
    first["feature_restrictions"].append("live_map")
    first["technical_protection_limits"]["may_trigger_upgrade_prompt"] = True
    second = beta_access_status()
    assert second["feature_restrictions"] == []
    assert second["technical_protection_limits"]["may_trigger_upgrade_prompt"] is False


def test_provider_incident_never_claims_an_unaccepted_retry() -> None:
    """An outage without a durable task stays honest and never becomes an upsell."""

    incident = beta_provider_incident(provider_id="tavily", correlation_id="corr-1")
    assert incident["status"] == "temporarily_unavailable"
    assert incident["retry_scheduled"] is False
    assert incident["retry_task_id"] is None
    assert incident["upgrade_required"] is False
    assert incident["payment_required"] is False
    assert "لم تُجدول" in incident["user_message_ar"]


def test_provider_incident_exposes_a_durably_accepted_retry() -> None:
    """A persisted task identifier is required before the UI promises a retry."""

    incident = beta_provider_incident(
        provider_id="pinecone",
        correlation_id="corr-2",
        accepted_retry_task_id="retry-42",
    )
    assert incident["retry_scheduled"] is True
    assert incident["retry_task_id"] == "retry-42"
    assert "سنعيد المحاولة" in incident["user_message_ar"]


def test_beta_billing_policy_remains_enabled() -> None:
    """Commercial mutations remain dormant throughout the closed beta."""

    assert beta_billing_mutation_blocked() is True
