"""Compatibility entrypoint for the former Vision-only FC20-05 sync.

The governed implementation now lives in :mod:`backend.public_knowledge` and
uses the shared public corpus. This wrapper preserves the old import and CLI
surface without retaining a second, stale provider integration.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any, Mapping
from urllib.parse import urlsplit

from backend.provider_security_control_plane import TrustedProviderScope
from backend.public_knowledge import (
    DEFAULT_PUBLIC_CORPUS,
    PUBLIC_KNOWLEDGE_REGISTRY_POLICY,
    PublicKnowledgeError,
    PublicKnowledgeSync,
    build_public_knowledge_sync_from_env,
)


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = PACKAGE_ROOT / "config" / "vision2030_sources.json"
DEFAULT_STATE = DEFAULT_PUBLIC_CORPUS
Vision2030SyncError = PublicKnowledgeError


def _normalize_text(value: str) -> str:
    normalized = value.replace("\r\n", "\n").replace("\r", "\n")
    normalized = re.sub(r"[ \t]+", " ", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()


def _chunk_text(text: str, *, maximum: int = 6_000, overlap: int = 300) -> list[str]:
    if maximum < 1_000 or overlap < 0 or overlap >= maximum:
        raise Vision2030SyncError("invalid_chunk_policy")
    normalized = _normalize_text(text)
    chunks: list[str] = []
    cursor = 0
    while cursor < len(normalized):
        end = min(cursor + maximum, len(normalized))
        if end < len(normalized):
            split = normalized.rfind(" ", cursor + maximum // 2, end)
            if split > cursor:
                end = split
        chunk = normalized[cursor:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(normalized):
            break
        cursor = max(end - overlap, cursor + 1)
    return chunks


def load_registry(path: Path) -> dict[str, Any]:
    try:
        registry = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise Vision2030SyncError("invalid_vision2030_source_registry") from exc
    sources = registry.get("sources") if isinstance(registry, dict) else None
    if not isinstance(sources, list) or not sources:
        raise Vision2030SyncError("vision2030_source_registry_empty")
    seen: set[str] = set()
    for source in sources:
        if not isinstance(source, dict):
            raise Vision2030SyncError("invalid_vision2030_source_entry")
        source_id = str(source.get("source_id") or "").strip().lower()
        if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{1,159}", source_id):
            raise Vision2030SyncError("invalid_vision2030_source_id")
        if source_id in seen:
            raise Vision2030SyncError("duplicate_vision2030_source_id")
        seen.add(source_id)
        parsed = urlsplit(str(source.get("url") or "").strip())
        if parsed.scheme != "https" or parsed.hostname not in {"vision2030.gov.sa", "www.vision2030.gov.sa"}:
            raise Vision2030SyncError("vision2030_source_must_be_official_https")
        if str(source.get("authority") or "") != "Saudi Vision 2030":
            raise Vision2030SyncError("vision2030_source_authority_invalid")
    return registry


def _as_public_registry(registry: Mapping[str, Any]) -> dict[str, Any]:
    sources: list[dict[str, Any]] = []
    for source in registry["sources"]:
        parsed = urlsplit(str(source["url"]))
        enabled = source.get("enabled", True) is True
        path = (parsed.path or "/").rstrip("/") or "/"
        if enabled and path == "/":
            raise Vision2030SyncError("vision2030_enabled_source_root_path_forbidden")
        sources.append(
            {
                "source_id": str(source["source_id"]).lower(),
                "publisher": "Saudi Vision 2030",
                "authority": "saudi_official",
                "url": source["url"],
                "state": "enabled" if enabled else "candidate",
                "admission_mode": "official_open_auto" if enabled else "metadata_only",
                "license_id": "saudi-open-data-license-2.0",
                "license_ref": "docs/legal/third-party/saudi-open-data/README.md",
                "attribution": "Saudi Vision 2030",
                "classification": "public_open_data",
                "geographies": ["saudi_arabia"],
                "sectors": ["all"],
                "language": str(source.get("language") or "ar,en"),
                "freshness_days": 31,
                "expiry_days": 93,
                "unit": "not_applicable",
                "confidence": 0.98,
                "allowed_paths": [path],
                "allow_query_parameters": False,
                "extract_depth": str(source.get("extract_depth") or "advanced"),
            }
        )
    return {
        "registry_id": "asie-vision2030-public-knowledge-compatibility-v1",
        "schema_version": 1,
        "policy": PUBLIC_KNOWLEDGE_REGISTRY_POLICY,
        "sources": sources,
    }


class Vision2030KnowledgeSync:
    def __init__(self, *, tavily: Any, pinecone: Any, state_path: Path) -> None:
        self._delegate = PublicKnowledgeSync(
            tavily=tavily,
            pinecone=pinecone,
            scope=TrustedProviderScope.for_platform_workload("public-knowledge-sync"),
            corpus_path=state_path,
        )

    def run(self, registry: Mapping[str, Any], *, dry_run: bool = False) -> dict[str, Any]:
        return self._delegate.run(_as_public_registry(registry), dry_run=dry_run)


def build_sync_from_env(
    state_path: Path,
    registry: Mapping[str, Any],
    *,
    dry_run: bool = False,
) -> PublicKnowledgeSync:
    public_registry = _as_public_registry(registry)
    return build_public_knowledge_sync_from_env(
        public_registry,
        corpus_path=state_path,
        dry_run=dry_run,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="ASIE Vision 2030 compatibility sync")
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        registry = load_registry(args.registry)
        public_registry = _as_public_registry(registry)
        result = build_sync_from_env(
            args.state,
            registry,
            dry_run=bool(args.dry_run),
        ).run(
            public_registry,
            dry_run=args.dry_run,
        )
    except Exception as exc:
        result = {
            "sync_id": "fc20-05-public-economic-knowledge-v1",
            "status": "failed",
            "error_type": type(exc).__name__,
            "reason": str(exc),
            "secrets_exposed": False,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] in {"changed", "unchanged", "changed_dry_run"} else 1


if __name__ == "__main__":
    sys.exit(main())
