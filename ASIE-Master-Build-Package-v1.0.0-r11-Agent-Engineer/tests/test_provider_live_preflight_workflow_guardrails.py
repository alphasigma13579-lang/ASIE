from __future__ import annotations

from pathlib import Path


WORKFLOW = Path(__file__).parents[2] / ".github" / "workflows" / "provider-live-preflight.yml"


def test_live_preflight_workflow_is_manual_gated_and_bounded() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "workflow_dispatch:" in text
    assert "pull_request:" not in text
    assert "push:" not in text
    assert "confirm_live_preflight:" in text
    assert "environment: provider-preflight" in text
    assert "contents: read" in text
    assert "timeout-minutes: 5" in text
    assert "--network" in text
    assert "--provider \"${{ inputs.provider }}\"" in text
    assert "actions/upload-artifact" not in text
    assert "curl " not in text
    assert "ASIE_PROVIDER_GLOBAL_KILL_SWITCH: \"false\"" in text
    assert "REQUESTS_PER_WINDOW: \"1\"" in text
    assert "COST_UNITS_PER_WINDOW: \"1\"" in text

