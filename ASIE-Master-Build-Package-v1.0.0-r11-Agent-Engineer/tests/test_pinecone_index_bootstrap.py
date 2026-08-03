from __future__ import annotations

from typing import Any, Mapping

import pytest

from backend.pinecone_index_bootstrap import (
    EMBED_MODEL,
    PineconeIndexBootstrapError,
    SOURCE_TEXT_FIELD,
    TARGET_INDEX,
    creation_payload,
    prepare_index,
)


def compatible_index(*, name: str = TARGET_INDEX, ready: bool = True) -> dict[str, Any]:
    return {
        "name": name,
        "status": {"ready": ready},
        "deletion_protection": "enabled",
        "embed": {
            "model": EMBED_MODEL,
            "field_map": {"text": SOURCE_TEXT_FIELD},
        },
    }


def test_creation_payload_is_fixed_protected_and_integrated() -> None:
    payload = creation_payload(name=TARGET_INDEX, cloud="aws", region="us-east-1")

    assert payload["name"] == TARGET_INDEX
    assert payload["embed"]["model"] == EMBED_MODEL
    assert payload["embed"]["field_map"] == {"text": SOURCE_TEXT_FIELD}
    assert payload["embed"]["write_parameters"]["input_type"] == "passage"
    assert payload["embed"]["read_parameters"]["input_type"] == "query"
    assert payload["deletion_protection"] == "enabled"


def test_prepare_creates_new_index_in_source_serverless_location() -> None:
    calls: list[tuple[str, Any]] = []

    def describe(name: str) -> tuple[int, Mapping[str, Any]]:
        calls.append(("describe", name))
        if name == TARGET_INDEX:
            return 404, {}
        return 200, {
            "name": "vision2030-kb",
            "spec": {"serverless": {"cloud": "aws", "region": "us-east-1"}},
        }

    def create(payload: Mapping[str, Any]) -> tuple[int, Mapping[str, Any]]:
        calls.append(("create", payload))
        return 201, compatible_index(ready=False)

    result = prepare_index(
        source_index="vision2030-kb",
        target_index=TARGET_INDEX,
        describe=describe,
        create=create,
    )

    assert result["status"] == "created"
    assert result["index_ready"] is False
    assert result["embed_model_compatible"] is True
    assert result["chunk_text_compatible"] is True
    assert result["deletion_protection_enabled"] is True
    assert calls[0] == ("describe", TARGET_INDEX)
    assert calls[1] == ("describe", "vision2030-kb")
    assert calls[2][0] == "create"


def test_prepare_is_idempotent_for_existing_compatible_target() -> None:
    def describe(name: str) -> tuple[int, Mapping[str, Any]]:
        assert name == TARGET_INDEX
        return 200, compatible_index()

    def create(payload: Mapping[str, Any]) -> tuple[int, Mapping[str, Any]]:
        raise AssertionError("create must not run")

    result = prepare_index(
        source_index="vision2030-kb",
        target_index=TARGET_INDEX,
        describe=describe,
        create=create,
    )

    assert result["status"] == "existing_compatible"
    assert result["write_attempted"] is False


def test_prepare_rejects_existing_incompatible_target() -> None:
    with pytest.raises(PineconeIndexBootstrapError, match="target_index_exists_incompatible"):
        prepare_index(
            source_index="vision2030-kb",
            target_index=TARGET_INDEX,
            describe=lambda name: (200, {"name": name}),
            create=lambda payload: (201, compatible_index()),
        )


def test_prepare_rejects_unexpected_target_name() -> None:
    with pytest.raises(PineconeIndexBootstrapError, match="unexpected_target_index"):
        prepare_index(
            source_index="vision2030-kb",
            target_index="different-index",
            describe=lambda name: (404, {}),
            create=lambda payload: (201, compatible_index()),
        )


def test_prepare_requires_serverless_source_location() -> None:
    responses = {
        TARGET_INDEX: (404, {}),
        "vision2030-kb": (200, {"name": "vision2030-kb", "spec": {}}),
    }
    with pytest.raises(PineconeIndexBootstrapError, match="source_index_serverless_cloud_required"):
        prepare_index(
            source_index="vision2030-kb",
            target_index=TARGET_INDEX,
            describe=lambda name: responses[name],
            create=lambda payload: (201, compatible_index()),
        )
