from __future__ import annotations

from pathlib import Path

from backend.beta_access import (
    beta_access_status,
    beta_billing_mutation_blocked,
    beta_provider_incident,
)


ROOT = Path(__file__).resolve().parents[1]
API_SOURCE = (ROOT / "backend" / "asie_local_api.py").read_text(encoding="utf-8")


def test_closed_beta_is_full_access_free_and_never_auto_converts() -> None:
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
    first = beta_access_status()
    first["feature_restrictions"].append("live_map")
    first["technical_protection_limits"]["may_trigger_upgrade_prompt"] = True
    second = beta_access_status()
    assert second["feature_restrictions"] == []
    assert second["technical_protection_limits"]["may_trigger_upgrade_prompt"] is False


def test_provider_exhaustion_is_an_operator_incident_not_an_upsell() -> None:
    incident = beta_provider_incident(provider_id="tavily", correlation_id="corr-1")
    assert incident["status"] == "temporarily_unavailable"
    assert incident["retry_scheduled"] is True
    assert incident["upgrade_required"] is False
    assert incident["payment_required"] is False
    assert "سنعيد المحاولة" in incident["user_message_ar"]


def test_billing_mutations_are_dormant_during_beta() -> None:
    assert beta_billing_mutation_blocked() is True
    assert 'if path == "/api/v1/beta/access-status":' in API_SOURCE
    assert API_SOURCE.count('write_error(self, "beta_billing_disabled", 409)') == 2
    assert "beta_access_status()" in API_SOURCE
