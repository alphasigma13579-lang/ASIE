from __future__ import annotations

import pytest

from backend.beta_release_gate import (
    CRITICAL_CHECKS,
    DEGRADABLE_CHECKS,
    SECRET_NAMES,
    assert_releaseable,
    evaluate_beta_release,
)


def _all_ready() -> dict[str, bool]:
    return {check_id: True for check_id in (*CRITICAL_CHECKS, *DEGRADABLE_CHECKS)}


def _secrets() -> dict[str, str]:
    return {name: f"secret-{index}" for index, name in enumerate(SECRET_NAMES, 1)}


def test_all_checks_produce_go_without_secret_values() -> None:
    env = _secrets()
    report = evaluate_beta_release(_all_ready(), env=env)

    assert report["decision"] == "GO"
    assert report["public_beta_allowed"] is True
    assert report["critical_failures"] == []
    assert report["degraded_capabilities"] == []
    assert report["secrets_exposed"] is False
    rendered = str(report)
    assert not any(value in rendered for value in env.values())


def test_degradable_failure_produces_conditional_go() -> None:
    assertions = _all_ready()
    assertions["live_intelligence_ready"] = False

    report = evaluate_beta_release(assertions, env=_secrets())

    assert report["decision"] == "CONDITIONAL_GO"
    assert report["release_allowed"] is True
    assert report["public_beta_allowed"] is False
    assert report["technical_limited_beta_allowed"] is True
    assert report["degraded_capabilities"] == ["live_intelligence_ready"]


def test_critical_failure_produces_no_go() -> None:
    assertions = _all_ready()
    assertions["approved_manifest_gate_ready"] = False

    report = evaluate_beta_release(assertions, env=_secrets())

    assert report["decision"] == "NO_GO"
    assert report["release_allowed"] is False
    assert "approved_manifest_gate_ready" in report["critical_failures"]


def test_missing_provider_secret_is_degradable_not_exposed() -> None:
    assertions = _all_ready()
    assertions.pop("provider_secrets_ready")
    env = _secrets()
    env["PINECONE_API_KEY"] = ""

    report = evaluate_beta_release(assertions, env=env)

    assert report["decision"] == "CONDITIONAL_GO"
    assert report["provider_secret_presence"]["PINECONE_API_KEY"] is False
    assert "provider_secrets_ready" in report["degraded_capabilities"]


def test_assert_releaseable_requires_go_by_default() -> None:
    assertions = _all_ready()
    assertions["external_fetch_enabled"] = False
    report = evaluate_beta_release(assertions, env=_secrets())

    with pytest.raises(RuntimeError, match="beta_release_blocked:CONDITIONAL_GO"):
        assert_releaseable(report)

    assert_releaseable(report, allow_conditional=True)


def test_gate_never_mutates_controlled_domains() -> None:
    report = evaluate_beta_release(_all_ready(), env=_secrets())
    assert report["finance_mutated"] is False
    assert report["snapshot_mutated"] is False
    assert report["external_fetch_changed"] is False
