from __future__ import annotations

from pathlib import Path


WORKFLOW = Path(__file__).parents[2] / ".github" / "workflows" / "pinecone-index-bootstrap.yml"


def test_pinecone_bootstrap_workflow_is_manual_exact_and_bounded() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "workflow_dispatch:" in text
    assert "pull_request:" not in text
    assert "push:" not in text
    assert "CREATE vision2030-kb-e5" in text
    assert "environment: provider-preflight" in text
    assert "contents: read" in text
    assert "timeout-minutes: 5" in text
    assert "ASIE_EXTERNAL_ALLOWED_HOSTS: api.pinecone.io" in text
    assert "PINECONE_TARGET_INDEX: vision2030-kb-e5" in text
    assert "PINECONE_API_KEY: ${{ secrets.PINECONE_API_KEY }}" in text
    assert "actions/upload-artifact" not in text
    assert "curl " not in text
    assert "delete" not in text.lower()
    assert "configure" not in text.lower()
