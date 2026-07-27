from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import urlsplit

from backend.external_acquisition import (
    ExternalAcquisitionPolicy,
    GovernedExternalAcquisitionGateway,
)
from backend.live_provider_clients import (
    GovernedProviderTransport,
    PineconeKnowledgeClient,
    ProviderConfigurationError,
    TavilyResearchClient,
)

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = PACKAGE_ROOT / "config" / "vision2030_sources.json"
DEFAULT_STATE = PACKAGE_ROOT / ".state" / "vision2030_sync_state.json"
ORGANIZATION_ID = "asie-sovereign-knowledge"
PROJECT_ID = "vision2030-kb-sync"
MAX_CHUNK_CHARS = 6_000
CHUNK_OVERLAP_CHARS = 300


class Vision2030SyncError(RuntimeError):
    """Raised when the governed Vision 2030 knowledge sync cannot proceed."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _normalize_text(value: str) -> str:
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _safe_id(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip()).strip("-._")
    if not cleaned:
        raise Vision2030SyncError("invalid_source_id")
    return cleaned[:180]


def _chunk_text(text: str, *, maximum: int = MAX_CHUNK_CHARS, overlap: int = CHUNK_OVERLAP_CHARS) -> list[str]:
    if maximum < 1_000 or overlap < 0 or overlap >= maximum:
        raise Vision2030SyncError("invalid_chunk_policy")
    normalized = _normalize_text(text)
    if not normalized:
        return []
    chunks: list[str] = []
    cursor = 0
    while cursor < len(normalized):
        end = min(cursor + maximum, len(normalized))
        if end < len(normalized):
            split = normalized.rfind("\n", cursor + maximum // 2, end)
            if split <= cursor:
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
    sources = registry.get("sources")
    if not isinstance(sources, list) or not sources:
        raise Vision2030SyncError("vision2030_source_registry_empty")
    seen: set[str] = set()
    for source in sources:
        if not isinstance(source, dict):
            raise Vision2030SyncError("invalid_vision2030_source_entry")
        source_id = _safe_id(str(source.get("source_id") or ""))
        if source_id in seen:
            raise Vision2030SyncError("duplicate_vision2030_source_id")
        seen.add(source_id)
        url = str(source.get("url") or "").strip()
        parsed = urlsplit(url)
        if parsed.scheme != "https" or parsed.hostname not in {"vision2030.gov.sa", "www.vision2030.gov.sa"}:
            raise Vision2030SyncError("vision2030_source_must_be_official_https")
        if str(source.get("authority") or "") != "Saudi Vision 2030":
            raise Vision2030SyncError("vision2030_source_authority_invalid")
    return registry


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"state_version": 1, "sources": {}}
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise Vision2030SyncError("invalid_vision2030_sync_state") from exc
    if not isinstance(state.get("sources"), dict):
        raise Vision2030SyncError("invalid_vision2030_sync_state_sources")
    return state


def save_state(path: Path, state: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _extract_result_text(response: Mapping[str, Any], expected_url: str) -> str:
    payload = response.get("payload")
    if not isinstance(payload, dict):
        raise Vision2030SyncError("invalid_tavily_extract_payload")
    results = payload.get("results")
    if not isinstance(results, list) or not results:
        raise Vision2030SyncError("tavily_extract_returned_no_results")
    selected: Mapping[str, Any] | None = None
    for row in results:
        if isinstance(row, dict) and str(row.get("url") or "").rstrip("/") == expected_url.rstrip("/"):
            selected = row
            break
    if selected is None:
        selected = next((row for row in results if isinstance(row, dict)), None)
    if selected is None:
        raise Vision2030SyncError("tavily_extract_result_invalid")
    text = selected.get("raw_content") or selected.get("content") or selected.get("markdown")
    normalized = _normalize_text(str(text or ""))
    if len(normalized) < 200:
        raise Vision2030SyncError("vision2030_source_content_too_short")
    return normalized


@dataclass
class Vision2030KnowledgeSync:
    tavily: TavilyResearchClient
    pinecone: PineconeKnowledgeClient
    state_path: Path = DEFAULT_STATE

    def run(self, registry: Mapping[str, Any], *, dry_run: bool = False) -> dict[str, Any]:
        started_at = _utc_now()
        state = load_state(self.state_path)
        previous_sources = state.setdefault("sources", {})
        summary: dict[str, Any] = {
            "sync_id": "asie-vision2030-kb-sync-v1",
            "started_at": started_at,
            "index_name": self.pinecone.index_name,
            "dry_run": dry_run,
            "sources_checked": 0,
            "sources_changed": 0,
            "sources_unchanged": 0,
            "records_upserted": 0,
            "records_deleted": 0,
            "errors": [],
            "source_of_truth": False,
            "snapshot_mutated": False,
            "finance_mutated": False,
        }

        for source in registry["sources"]:
            if not source.get("enabled", True):
                continue
            summary["sources_checked"] += 1
            source_id = _safe_id(str(source["source_id"]))
            source_url = str(source["url"])
            checked_at = _utc_now()
            try:
                response = self.tavily.extract(
                    urls=[source_url],
                    query="Extract the complete authoritative content, headings, tables, metrics, dates, and document links.",
                    depth=str(source.get("extract_depth") or "advanced"),
                )
                text = _extract_result_text(response, source_url)
                content_hash = _sha256_text(text)
                previous = previous_sources.get(source_id) if isinstance(previous_sources.get(source_id), dict) else {}
                previous_hash = str(previous.get("content_sha256") or "")
                previous_record_ids = [str(value) for value in previous.get("record_ids", []) if str(value)]

                if content_hash == previous_hash:
                    summary["sources_unchanged"] += 1
                    previous_sources[source_id] = {
                        **previous,
                        "last_checked_at": checked_at,
                        "last_result": "unchanged",
                    }
                    continue

                chunks = _chunk_text(text)
                if not chunks:
                    raise Vision2030SyncError("vision2030_source_produced_no_chunks")
                record_ids = [f"vision2030-{source_id}-{index:04d}" for index in range(1, len(chunks) + 1)]
                records = [
                    {
                        "_id": record_id,
                        "chunk_text": chunk,
                        "source_url": source_url,
                        "source_id": source_id,
                        "evidence_ref": f"vision2030:{source_id}:sha256:{content_hash}",
                        "review_status": "approved",
                        "data_classification": "public",
                    }
                    for record_id, chunk in zip(record_ids, chunks, strict=True)
                ]

                if not dry_run:
                    for offset in range(0, len(records), 100):
                        batch = records[offset : offset + 100]
                        self.pinecone.upsert_approved_text(
                            organization_id=ORGANIZATION_ID,
                            project_id=PROJECT_ID,
                            records=batch,
                        )
                        summary["records_upserted"] += len(batch)
                    stale_ids = sorted(set(previous_record_ids) - set(record_ids))
                    if stale_ids:
                        self.pinecone.delete_records(
                            organization_id=ORGANIZATION_ID,
                            project_id=PROJECT_ID,
                            record_ids=stale_ids,
                        )
                        summary["records_deleted"] += len(stale_ids)

                summary["sources_changed"] += 1
                previous_sources[source_id] = {
                    "source_url": source_url,
                    "title": str(source.get("title") or source_id),
                    "language": str(source.get("language") or ""),
                    "content_sha256": content_hash,
                    "record_ids": record_ids,
                    "record_count": len(record_ids),
                    "last_checked_at": checked_at,
                    "last_changed_at": checked_at,
                    "last_result": "changed_dry_run" if dry_run else "changed_upserted",
                }
            except Exception as exc:  # Per-source boundary: continue and report without secrets.
                summary["errors"].append(
                    {
                        "source_id": source_id,
                        "error_type": type(exc).__name__,
                        "reason": str(exc),
                    }
                )
                previous = previous_sources.get(source_id) if isinstance(previous_sources.get(source_id), dict) else {}
                previous_sources[source_id] = {
                    **previous,
                    "source_url": source_url,
                    "last_checked_at": checked_at,
                    "last_result": "failed",
                    "last_error_type": type(exc).__name__,
                }

        summary["completed_at"] = _utc_now()
        summary["status"] = "failed" if summary["errors"] else ("changed" if summary["sources_changed"] else "unchanged")
        state.update(
            {
                "state_version": 1,
                "registry_id": registry.get("registry_id"),
                "index_name": self.pinecone.index_name,
                "last_run_at": summary["completed_at"],
                "last_run_status": summary["status"],
                "sources": previous_sources,
            }
        )
        save_state(self.state_path, state)
        return summary


def build_sync_from_env(state_path: Path) -> Vision2030KnowledgeSync:
    policy = ExternalAcquisitionPolicy.from_env()
    if not policy.enabled:
        raise ProviderConfigurationError("external_network_disabled_by_policy")
    gateway = GovernedExternalAcquisitionGateway(policy)
    transport = GovernedProviderTransport(gateway)
    return Vision2030KnowledgeSync(
        tavily=TavilyResearchClient.from_env(transport),
        pinecone=PineconeKnowledgeClient.from_env(transport),
        state_path=state_path,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="ASIE monthly Vision 2030 Pinecone knowledge sync")
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        registry = load_registry(args.registry)
        sync = build_sync_from_env(args.state)
        result = sync.run(registry, dry_run=args.dry_run)
    except Exception as exc:
        result = {
            "sync_id": "asie-vision2030-kb-sync-v1",
            "status": "failed",
            "error_type": type(exc).__name__,
            "reason": str(exc),
            "secrets_exposed": False,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] in {"changed", "unchanged"} else 1


if __name__ == "__main__":
    sys.exit(main())
