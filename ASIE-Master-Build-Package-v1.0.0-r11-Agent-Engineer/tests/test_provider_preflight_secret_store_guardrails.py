from __future__ import annotations

from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = REPOSITORY_ROOT / ".github" / "workflows" / "provider-preflight-secret-store.yml"
TEMPLATE = PACKAGE_ROOT / ".env.provider-preflight.example"


def test_secret_store_workflow_is_manual_environment_gated_and_read_only() -> None:
    source = WORKFLOW.read_text(encoding="utf-8")
    assert "workflow_dispatch:" in source
    assert "pull_request:" not in source
    assert "push:" not in source
    assert "environment: provider-preflight" in source
    assert "contents: read" in source
    assert "timeout-minutes: 5" in source
    assert "cancel-in-progress: false" in source


def test_secret_store_workflow_cannot_activate_network_or_publish_artifacts() -> None:
    source = WORKFLOW.read_text(encoding="utf-8")
    for forbidden in (
        "--network",
        "ASIE_ALLOW_EXTERNAL_FETCH",
        "ASIE_PROVIDER_CONTROL_PLANE_ENABLED",
        "actions/upload-artifact",
        "curl ",
        "Invoke-WebRequest",
    ):
        assert forbidden not in source


def test_secret_names_are_canonical_and_values_are_not_committed() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    template = TEMPLATE.read_text(encoding="utf-8")
    for name in (
        "DEEPSEEK_API_KEY",
        "TAVILY_API_KEY",
        "GOOGLE_MAPS_API_KEY",
        "PINECONE_API_KEY",
    ):
        assert f"{name}: ${{{{ secrets.{name} }}}}" in workflow
        assert f"{name}=\n" in template
    assert "ASIE_PROVIDER_PREFLIGHT_NETWORK_AUTHORIZED=false" in template

