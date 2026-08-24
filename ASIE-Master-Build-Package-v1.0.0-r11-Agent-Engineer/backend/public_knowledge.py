from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import ipaddress
import json
import math
from pathlib import Path, PurePosixPath
import re
import sys
from typing import Any, Callable, Mapping, Sequence
from urllib.parse import unquote, urlsplit

from backend.provider_security_control_plane import TrustedProviderScope


PUBLIC_KNOWLEDGE_SCHEMA_VERSION = 1
PUBLIC_KNOWLEDGE_WORKLOAD = "public-knowledge-sync"
PACKAGE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PUBLIC_SOURCE_REGISTRY = PACKAGE_ROOT / "config" / "public_knowledge_sources.json"
DEFAULT_PUBLIC_CORPUS = PACKAGE_ROOT / ".state" / "public_knowledge_corpus.json"
MAX_SOURCES = 100
MAX_CONTENT_CHARS = 2_000_000
MAX_CHUNK_CHARS = 6_000
CHUNK_OVERLAP_CHARS = 300
MAX_RETAINED_VERSIONS = 3
MAX_CRAWL_DEPTH = 3
MAX_CRAWL_RESULTS = 50
_SOURCE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{1,159}$")
_RECORD_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,511}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_OFFICIAL_AUTHORITIES = frozenset({"saudi_official", "international_official"})
_STATES = frozenset({"candidate", "enabled", "reference_only", "blocked"})
_INJECTION_MARKERS = (
    "ignore previous instructions",
    "ignore all previous instructions",
    "system prompt",
    "developer message",
    "reveal secrets",
    "<|system|>",
    "[system]",
)


class PublicKnowledgeError(RuntimeError):
    """Fail-closed public knowledge contract or lifecycle error."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_utc(value: str, *, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise PublicKnowledgeError(f"invalid_public_knowledge_datetime:{field}") from exc
    if parsed.tzinfo is None:
        raise PublicKnowledgeError(f"invalid_public_knowledge_datetime:{field}")
    return parsed.astimezone(timezone.utc)


def _iso_after(value: str, days: int) -> str:
    return (_parse_utc(value, field="retrieved_at") + timedelta(days=days)).isoformat().replace("+00:00", "Z")


def _normalize_text(value: str) -> str:
    normalized = value.replace("\r\n", "\n").replace("\r", "\n")
    normalized = re.sub(r"[ \t]+", " ", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _safe_source_id(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    if not _SOURCE_ID_RE.fullmatch(normalized):
        raise PublicKnowledgeError("invalid_public_source_id")
    return normalized


def _canonical_url(value: Any) -> tuple[str, str, str, str]:
    raw = str(value or "").strip()
    try:
        parsed = urlsplit(raw)
        port = parsed.port
        hostname = (parsed.hostname or "").encode("idna").decode("ascii").lower().rstrip(".")
    except (UnicodeError, ValueError) as exc:
        raise PublicKnowledgeError("public_source_url_must_be_canonical_https") from exc
    if (
        parsed.scheme.lower() != "https"
        or not hostname
        or parsed.username
        or parsed.password
        or port not in {None, 443}
        or parsed.fragment
    ):
        raise PublicKnowledgeError("public_source_url_must_be_canonical_https")
    try:
        ip = ipaddress.ip_address(hostname)
    except ValueError:
        ip = None
    if ip is not None or hostname == "localhost" or hostname.endswith((".local", ".internal", ".lan")):
        raise PublicKnowledgeError("public_source_private_host_denied")
    path = parsed.path or "/"
    try:
        decoded = unquote(path, encoding="utf-8", errors="strict")
    except (UnicodeDecodeError, ValueError) as exc:
        raise PublicKnowledgeError("public_source_path_invalid") from exc
    if (
        not decoded.startswith("/")
        or "\\" in decoded
        or "//" in decoded
        or unquote(decoded, encoding="utf-8", errors="strict") != decoded
        or any(segment in {".", ".."} for segment in decoded.split("/"))
    ):
        raise PublicKnowledgeError("public_source_path_invalid")
    canonical_path = decoded if decoded == "/" else decoded.rstrip("/")
    return raw, hostname, canonical_path, parsed.query


def _validated_license_ref(value: Any) -> str:
    reference = str(value or "").strip()
    if not reference or len(reference) > 2_000:
        raise PublicKnowledgeError("public_source_license_ref_invalid")
    if reference.lower().startswith("https://"):
        _canonical_url(reference)
        return reference
    if ":" in reference or "\\" in reference or reference.startswith("/"):
        raise PublicKnowledgeError("public_source_license_ref_invalid")
    path = PurePosixPath(reference)
    if (
        path.is_absolute()
        or any(part in {"", ".", ".."} for part in path.parts)
        or path.parts[:2] != ("docs", "legal")
    ):
        raise PublicKnowledgeError("public_source_license_ref_invalid")
    return reference


def _path_within(path: str, root: str) -> bool:
    return root == "/" or path == root or path.startswith(root + "/")


def _graph_path_pattern(root: str) -> str:
    return r"^/.*$" if root == "/" else rf"^{re.escape(root)}(?:/.*)?$"


def _string_list(value: Any, *, field: str, maximum: int = 64) -> list[str]:
    if not isinstance(value, list) or not value or len(value) > maximum:
        raise PublicKnowledgeError(f"invalid_public_source_{field}")
    normalized = [str(item or "").strip() for item in value]
    if any(not item or len(item) > 200 for item in normalized):
        raise PublicKnowledgeError(f"invalid_public_source_{field}")
    return normalized


def _positive_int(value: Any, *, field: str, maximum: int = 3_650) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1 or value > maximum:
        raise PublicKnowledgeError(f"invalid_public_source_{field}")
    return value


def _validate_source(source: Mapping[str, Any]) -> dict[str, Any]:
    normalized = dict(source)
    source_id = _safe_source_id(normalized.get("source_id"))
    state = str(normalized.get("state") or "").strip()
    if state not in _STATES:
        raise PublicKnowledgeError("invalid_public_source_state")
    authority = str(normalized.get("authority") or "").strip()
    admission_mode = str(normalized.get("admission_mode") or "").strip()
    _source_raw, source_host, source_path, source_query = _canonical_url(normalized.get("url"))
    if state == "enabled":
        if authority not in _OFFICIAL_AUTHORITIES:
            raise PublicKnowledgeError("private_source_auto_ingestion_forbidden")
        if admission_mode != "official_open_auto":
            raise PublicKnowledgeError("enabled_public_source_requires_official_open_auto")
        required = (
            "publisher",
            "license_id",
            "license_ref",
            "attribution",
            "classification",
            "language",
            "unit",
        )
        if any(not str(normalized.get(field) or "").strip() for field in required):
            raise PublicKnowledgeError("enabled_public_source_metadata_incomplete")
        _validated_license_ref(normalized.get("license_ref"))
        if normalized.get("classification") != "public_open_data":
            raise PublicKnowledgeError("enabled_public_source_must_be_open_data")
        _string_list(normalized.get("geographies"), field="geographies")
        _string_list(normalized.get("sectors"), field="sectors")
        allowed_paths = _string_list(normalized.get("allowed_paths"), field="allowed_paths")
        canonical_paths: list[str] = []
        for allowed_path in allowed_paths:
            if not allowed_path.startswith("/"):
                raise PublicKnowledgeError("invalid_public_source_allowed_paths")
            _raw, host, path, query = _canonical_url(f"https://{source_host}{allowed_path}")
            if host != source_host or query:
                raise PublicKnowledgeError("invalid_public_source_allowed_paths")
            canonical_paths.append(path)
        if source_path == "/" or "/" in canonical_paths:
            raise PublicKnowledgeError("public_source_root_path_not_admitted")
        if not any(_path_within(source_path, root) for root in canonical_paths):
            raise PublicKnowledgeError("public_source_url_outside_allowed_paths")
        if source_query and normalized.get("allow_query_parameters") is not True:
            raise PublicKnowledgeError("public_source_query_not_admitted")
        normalized["allowed_paths"] = canonical_paths
        _positive_int(normalized.get("freshness_days"), field="freshness_days")
        _positive_int(normalized.get("expiry_days"), field="expiry_days")
        acquisition_mode = str(normalized.get("acquisition_mode") or "extract").strip()
        if acquisition_mode not in {"extract", "crawl"}:
            raise PublicKnowledgeError("invalid_public_source_acquisition_mode")
        normalized["acquisition_mode"] = acquisition_mode
        if acquisition_mode == "crawl":
            _positive_int(
                normalized.get("crawl_max_depth"),
                field="crawl_max_depth",
                maximum=MAX_CRAWL_DEPTH,
            )
            _positive_int(
                normalized.get("crawl_limit"),
                field="crawl_limit",
                maximum=MAX_CRAWL_RESULTS,
            )
        confidence = normalized.get("confidence")
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not 0.0 <= float(confidence) <= 1.0:
            raise PublicKnowledgeError("invalid_public_source_confidence")
    elif authority == "private_analytical_reference" and (
        state != "reference_only" or admission_mode != "metadata_only"
    ):
        raise PublicKnowledgeError("private_source_auto_ingestion_forbidden")
    elif normalized.get("license_ref"):
        _validated_license_ref(normalized.get("license_ref"))
    normalized["source_id"] = source_id
    return normalized


def validate_public_source_registry(registry: Mapping[str, Any]) -> dict[str, Any]:
    if registry.get("schema_version") != PUBLIC_KNOWLEDGE_SCHEMA_VERSION:
        raise PublicKnowledgeError("public_source_registry_schema_version_invalid")
    sources = registry.get("sources")
    if not isinstance(sources, list) or not sources or len(sources) > MAX_SOURCES:
        raise PublicKnowledgeError("public_source_registry_size_invalid")
    normalized_sources: list[dict[str, Any]] = []
    seen: set[str] = set()
    for source in sources:
        if not isinstance(source, Mapping):
            raise PublicKnowledgeError("invalid_public_source_record")
        normalized = _validate_source(source)
        if normalized["source_id"] in seen:
            raise PublicKnowledgeError("duplicate_public_source_id")
        seen.add(normalized["source_id"])
        normalized_sources.append(normalized)
    return {
        **dict(registry),
        "sources": normalized_sources,
    }


def load_public_source_registry(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PublicKnowledgeError("public_source_registry_invalid") from exc
    if not isinstance(payload, Mapping):
        raise PublicKnowledgeError("public_source_registry_invalid")
    return validate_public_source_registry(payload)


def select_public_source(registry: Mapping[str, Any], source_id: str) -> dict[str, Any]:
    validated = validate_public_source_registry(registry)
    normalized_id = _safe_source_id(source_id)
    selected = [source for source in validated["sources"] if source["source_id"] == normalized_id]
    if len(selected) != 1:
        raise PublicKnowledgeError("public_source_not_found")
    return {**validated, "sources": selected}


@dataclass(frozen=True)
class PublicKnowledgeSourcePolicy:
    organization_id: str
    project_id: str
    records: tuple[Mapping[str, Any], ...]

    @classmethod
    def from_registry(cls, registry: Mapping[str, Any]) -> "PublicKnowledgeSourcePolicy":
        validated = validate_public_source_registry(registry)
        return cls(
            organization_id="__platform__",
            project_id=PUBLIC_KNOWLEDGE_WORKLOAD,
            records=tuple(validated["sources"]),
        )

    def authorize_content_url(self, *, source_id: str, url: str, operation: str) -> dict[str, Any]:
        if operation not in {"extract", "crawl"}:
            raise PublicKnowledgeError("public_source_operation_not_admitted")
        normalized_id = _safe_source_id(source_id)
        source = next((record for record in self.records if record["source_id"] == normalized_id), None)
        if source is None:
            raise PublicKnowledgeError("unknown_public_source_denied")
        if source.get("state") != "enabled" or source.get("admission_mode") != "official_open_auto":
            raise PublicKnowledgeError("public_source_not_enabled")
        _approved_raw, approved_host, _approved_path, _approved_query = _canonical_url(source.get("url"))
        _requested_raw, requested_host, requested_path, requested_query = _canonical_url(url)
        if approved_host != requested_host:
            raise PublicKnowledgeError("public_source_host_not_admitted")
        roots = [
            _canonical_url(f"https://{approved_host}{path}")[2]
            for path in source.get("allowed_paths", [])
        ]
        if not any(root == "/" or requested_path == root or requested_path.startswith(root + "/") for root in roots):
            raise PublicKnowledgeError("public_source_path_not_admitted")
        if requested_query and source.get("allow_query_parameters") is not True:
            raise PublicKnowledgeError("public_source_query_not_admitted")
        return {
            "operation": operation,
            "source_id": normalized_id,
            "host": requested_host,
            "path": requested_path,
            "allowed_path_roots": roots,
            "select_domains": [rf"^{re.escape(requested_host)}$"],
            "organization_scope": "__platform__",
            "project_scope": PUBLIC_KNOWLEDGE_WORKLOAD,
            "license_id": source["license_id"],
            "license_ref": source["license_ref"],
            "attribution": source["attribution"],
            "review_status": "auto_admitted_official_open",
            "eligible_for_controlled_assumptions": False,
        }

    def authorize_graph_scope(
        self,
        *,
        admission: Mapping[str, Any],
        requested_select_paths: Sequence[str] = (),
        requested_exclude_paths: Sequence[str] = (),
    ) -> dict[str, list[str]]:
        if admission.get("operation") != "crawl":
            raise PublicKnowledgeError("public_graph_scope_requires_crawl_admission")
        host = str(admission.get("host") or "")
        allowed_roots = tuple(str(value) for value in admission.get("allowed_path_roots") or ())
        if not host or not allowed_roots:
            raise PublicKnowledgeError("public_graph_scope_missing")

        def canonical_paths(values: Sequence[str]) -> tuple[str, ...]:
            paths: list[str] = []
            for value in values:
                _raw, requested_host, path, query = _canonical_url(f"https://{host}{value}")
                if requested_host != host or query:
                    raise PublicKnowledgeError("public_graph_scope_invalid")
                paths.append(path)
            return tuple(paths)

        selected = canonical_paths(requested_select_paths) if requested_select_paths else allowed_roots
        if any(not any(_path_within(path, root) for root in allowed_roots) for path in selected):
            raise PublicKnowledgeError("public_graph_scope_widening_denied")
        excluded = canonical_paths(requested_exclude_paths) if requested_exclude_paths else ()
        if any(not any(_path_within(path, root) for root in selected) for path in excluded):
            raise PublicKnowledgeError("public_graph_scope_widening_denied")
        return {
            "select_domains": [rf"^{re.escape(host)}$"],
            "select_paths": [_graph_path_pattern(path) for path in dict.fromkeys(selected)],
            "exclude_paths": [_graph_path_pattern(path) for path in dict.fromkeys(excluded)],
        }


def _chunk_text(text: str) -> list[str]:
    normalized = _normalize_text(text)
    if len(normalized) < 200:
        raise PublicKnowledgeError("public_source_content_too_short")
    if len(normalized) > MAX_CONTENT_CHARS:
        raise PublicKnowledgeError("public_source_content_too_large")
    chunks: list[str] = []
    cursor = 0
    while cursor < len(normalized):
        end = min(cursor + MAX_CHUNK_CHARS, len(normalized))
        if end < len(normalized):
            split = normalized.rfind("\n", cursor + MAX_CHUNK_CHARS // 2, end)
            if split <= cursor:
                split = normalized.rfind(" ", cursor + MAX_CHUNK_CHARS // 2, end)
            if split > cursor:
                end = split
        chunk = normalized[cursor:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(normalized):
            break
        cursor = max(end - CHUNK_OVERLAP_CHARS, cursor + 1)
    return chunks


def _content_anomalies(text: str) -> list[str]:
    normalized = _normalize_text(text)
    anomalies: list[str] = []
    lowered = normalized.lower()
    if any(marker in lowered for marker in _INJECTION_MARKERS):
        anomalies.append("prompt_injection_suspected")
    if normalized and normalized.count("\ufffd") / len(normalized) > 0.01:
        anomalies.append("content_encoding_corrupt")
    if "-----BEGIN PRIVATE KEY-----" in normalized or re.search(r"(?:api[_-]?key|secret)\s*[:=]\s*[A-Za-z0-9_-]{20,}", normalized, re.I):
        anomalies.append("sensitive_secret_pattern")
    if re.search(
        r"(?:national\s+id|identity\s+number|رقم\s+الهوية|الهوية\s+الوطنية)\D{0,24}[12]\d{9}\b",
        normalized,
        re.I,
    ):
        anomalies.append("sensitive_personal_identifier_pattern")
    return anomalies


def _extract_text(response: Mapping[str, Any], expected_url: str) -> str:
    payload = response.get("payload")
    if not isinstance(payload, Mapping):
        raise PublicKnowledgeError("public_source_extract_payload_invalid")
    results = payload.get("results")
    if not isinstance(results, list) or not results:
        raise PublicKnowledgeError("public_source_extract_empty")
    expected = _canonical_url(expected_url)
    selected: Mapping[str, Any] | None = None
    for result in results:
        if not isinstance(result, Mapping):
            continue
        try:
            candidate = _canonical_url(result.get("url"))
        except PublicKnowledgeError:
            continue
        if candidate[1:] == expected[1:]:
            selected = result
            break
    if selected is None:
        raise PublicKnowledgeError("public_source_extract_url_mismatch")
    return _normalize_text(str(selected.get("raw_content") or selected.get("content") or ""))


def _extract_crawl_text(
    response: Mapping[str, Any],
    *,
    source: Mapping[str, Any],
    admission_policy: PublicKnowledgeSourcePolicy,
) -> str:
    payload = response.get("payload")
    results = payload.get("results") if isinstance(payload, Mapping) else None
    if not isinstance(results, list) or not results or len(results) > int(source["crawl_limit"]):
        raise PublicKnowledgeError("public_source_crawl_payload_invalid")
    pages: dict[tuple[str, str, str], str] = {}
    total_content_chars = 0
    for result in results:
        if not isinstance(result, Mapping):
            raise PublicKnowledgeError("public_source_crawl_payload_invalid")
        url = str(result.get("url") or "")
        try:
            admission_policy.authorize_content_url(
                source_id=str(source["source_id"]),
                url=url,
                operation="crawl",
            )
            _raw, host, path, query = _canonical_url(url)
        except PublicKnowledgeError as exc:
            raise PublicKnowledgeError("public_source_crawl_url_mismatch") from exc
        content = _normalize_text(str(result.get("raw_content") or result.get("content") or ""))
        if content:
            key = (host, path, query)
            total_content_chars += len(content) - len(pages.get(key, ""))
            if total_content_chars > MAX_CONTENT_CHARS:
                raise PublicKnowledgeError("public_source_content_too_large")
            pages[key] = content
    if not pages:
        raise PublicKnowledgeError("public_source_crawl_empty")
    combined = _normalize_text(
        "\n\n".join(
            f"Source URL: https://{host}{path}{'?' + query if query else ''}\n{pages[(host, path, query)]}"
            for host, path, query in sorted(pages)
        )
    )
    if len(combined) > MAX_CONTENT_CHARS:
        raise PublicKnowledgeError("public_source_content_too_large")
    return combined


def _empty_corpus() -> dict[str, Any]:
    return {
        "schema_version": PUBLIC_KNOWLEDGE_SCHEMA_VERSION,
        "source_of_truth": True,
        "sources": {},
        "audit_events": [],
    }


def _load_corpus(path: Path) -> dict[str, Any]:
    if not path.exists():
        return _empty_corpus()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PublicKnowledgeError("public_knowledge_corpus_invalid") from exc
    if (
        not isinstance(payload, dict)
        or payload.get("schema_version") != PUBLIC_KNOWLEDGE_SCHEMA_VERSION
        or not isinstance(payload.get("sources"), dict)
        or not isinstance(payload.get("audit_events"), list)
    ):
        raise PublicKnowledgeError("public_knowledge_corpus_invalid")
    return payload


def _save_corpus(path: Path, corpus: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(corpus, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _batched(values: Sequence[Any], size: int) -> list[Sequence[Any]]:
    return [values[offset : offset + size] for offset in range(0, len(values), size)]


@dataclass
class PublicKnowledgeSync:
    tavily: Any
    pinecone: Any
    scope: TrustedProviderScope
    corpus_path: Path
    now: Callable[[], str] = _utc_now

    def _records(
        self,
        *,
        source: Mapping[str, Any],
        text: str,
        content_hash: str,
        version: int,
        retrieved_at: str,
    ) -> list[dict[str, Any]]:
        chunks = _chunk_text(text)
        fresh_until = _iso_after(retrieved_at, int(source["freshness_days"]))
        expires_at = _iso_after(retrieved_at, int(source["expiry_days"]))
        source_id = str(source["source_id"])
        record_count = len(chunks)
        records: list[dict[str, Any]] = []
        for index, chunk in enumerate(chunks, start=1):
            records.append(
                {
                    "_id": f"public-{source_id}-{index:04d}",
                    "chunk_text": chunk,
                    "source_id": source_id,
                    "publisher": str(source["publisher"]),
                    "authority": str(source["authority"]),
                    "source_url": str(source["url"]),
                    "license_id": str(source["license_id"]),
                    "license_ref": str(source["license_ref"]),
                    "attribution": str(source["attribution"]),
                    "sector": ",".join(str(value) for value in source["sectors"]),
                    "geography": ",".join(str(value) for value in source["geographies"]),
                    "language": str(source["language"]),
                    "published_at": str(source.get("published_at") or "unknown"),
                    "retrieved_at": retrieved_at,
                    "content_sha256": content_hash,
                    "version": version,
                    "freshness_days": int(source["freshness_days"]),
                    "fresh_until": fresh_until,
                    "expires_at": expires_at,
                    "unit": str(source["unit"]),
                    "confidence": float(source["confidence"]),
                    "evidence_ref": f"public:{source_id}:sha256:{content_hash}",
                    "admission_status": "auto_admitted_official_open",
                    "data_classification": "public",
                    "chunk_index": index,
                    "chunk_count": record_count,
                    "source_of_truth": False,
                }
            )
        return records

    def _upsert(self, records: Sequence[Mapping[str, Any]]) -> int:
        count = 0
        for batch in _batched(records, 100):
            self.pinecone.upsert_public_knowledge(scope=self.scope, records=list(batch))
            count += len(batch)
        return count

    def _delete_ids(self, record_ids: Sequence[str]) -> int:
        count = 0
        for batch in _batched(record_ids, 1_000):
            self.pinecone.delete_public_knowledge(
                scope=self.scope,
                record_ids=list(batch),
            )
            count += len(batch)
        return count

    def run(self, registry: Mapping[str, Any], *, dry_run: bool = False) -> dict[str, Any]:
        validated = validate_public_source_registry(registry)
        admission_policy = PublicKnowledgeSourcePolicy.from_registry(validated)
        corpus = _load_corpus(self.corpus_path)
        working = json.loads(json.dumps(corpus))
        summary: dict[str, Any] = {
            "sync_id": "fc20-05-public-economic-knowledge-v1",
            "started_at": self.now(),
            "dry_run": dry_run,
            "sources_checked": 0,
            "sources_changed": 0,
            "sources_unchanged": 0,
            "sources_quarantined": 0,
            "sources_skipped_tombstone": 0,
            "records_upserted": 0,
            "records_deleted": 0,
            "errors": [],
            "source_of_truth": False,
            "snapshot_mutated": False,
            "finance_mutated": False,
        }
        compensations: list[tuple[list[dict[str, Any]], list[str], list[str]]] = []

        def record_quarantine(
            *,
            source: Mapping[str, Any],
            previous: dict[str, Any],
            checked_at: str,
            anomalies: Sequence[str],
        ) -> None:
            previous.setdefault("status", "quarantined")
            previous.setdefault("source_url", source["url"])
            previous.setdefault("records", [])
            previous.setdefault("versions", [])
            previous["last_checked_at"] = checked_at
            previous["last_result"] = "quarantined"
            previous["last_anomalies"] = list(anomalies)
            working["sources"][source["source_id"]] = previous
            working["audit_events"].append(
                {
                    "event": "source_quarantined",
                    "source_id": source["source_id"],
                    "anomalies": list(anomalies),
                    "at": checked_at,
                }
            )

        for source in validated["sources"]:
            if source["state"] != "enabled":
                continue
            summary["sources_checked"] += 1
            source_id = source["source_id"]
            checked_at = self.now()
            previous = working["sources"].get(source_id)
            previous = previous if isinstance(previous, dict) else {}
            previous_records = previous.get("records") if isinstance(previous.get("records"), list) else []
            if previous.get("status") == "deleted_tombstone":
                summary["sources_skipped_tombstone"] += 1
                continue
            try:
                if source.get("acquisition_mode") == "crawl":
                    response = self.tavily.crawl(
                        source_id=source_id,
                        url=str(source["url"]),
                        instructions="Crawl only authoritative public-data pages, headings, tables, metrics, dates, units, and evidence links.",
                        max_depth=int(source["crawl_max_depth"]),
                        limit=int(source["crawl_limit"]),
                        select_paths=list(source["allowed_paths"]),
                    )
                    text = _extract_crawl_text(
                        response,
                        source=source,
                        admission_policy=admission_policy,
                    )
                else:
                    response = self.tavily.extract(
                        urls=[source["url"]],
                        source_ids={source["url"]: source_id},
                        query="Extract authoritative headings, tables, metrics, dates, units, and linked public evidence.",
                        depth=str(source.get("extract_depth") or "advanced"),
                    )
                    text = _extract_text(response, str(source["url"]))
                anomalies = _content_anomalies(text)
                if anomalies:
                    summary["sources_quarantined"] += 1
                    summary["errors"].append(
                        {"source_id": source_id, "reason": "public_source_quarantined", "anomalies": anomalies}
                    )
                    if not dry_run:
                        record_quarantine(
                            source=source,
                            previous=previous,
                            checked_at=checked_at,
                            anomalies=anomalies,
                        )
                    continue
                content_hash = _sha256_text(text)
                if previous.get("content_sha256") == content_hash and previous.get("status") == "active":
                    summary["sources_unchanged"] += 1
                    if not dry_run:
                        previous["last_checked_at"] = checked_at
                        previous["last_result"] = "unchanged"
                        previous.pop("last_anomalies", None)
                        working["sources"][source_id] = previous
                    continue
                version = int(previous.get("current_version") or 0) + 1
                records = self._records(
                    source=source,
                    text=text,
                    content_hash=content_hash,
                    version=version,
                    retrieved_at=checked_at,
                )
                if dry_run:
                    summary["sources_changed"] += 1
                    continue
                new_ids = [record["_id"] for record in records]
                previous_ids = [str(record.get("_id") or "") for record in previous_records]
                try:
                    source_records_upserted = self._upsert(records)
                    stale_ids = sorted(set(previous_ids) - set(new_ids))
                    source_records_deleted = self._delete_ids(stale_ids)
                except Exception:
                    if previous_records:
                        self._upsert(previous_records)
                    extra_ids = sorted(set(new_ids) - set(previous_ids))
                    if extra_ids:
                        self._delete_ids(extra_ids)
                    raise
                summary["records_upserted"] += source_records_upserted
                summary["records_deleted"] += source_records_deleted
                versions = list(previous.get("versions") or [])
                if previous_records:
                    versions.append(
                        {
                            "version": previous.get("current_version"),
                            "content_sha256": previous.get("content_sha256"),
                            "records": previous_records,
                            "retained_at": checked_at,
                        }
                    )
                versions = versions[-MAX_RETAINED_VERSIONS:]
                working["sources"][source_id] = {
                    "status": "active",
                    "source_url": source["url"],
                    "content_sha256": content_hash,
                    "current_version": version,
                    "records": records,
                    "versions": versions,
                    "last_checked_at": checked_at,
                    "last_changed_at": checked_at,
                    "last_result": "changed_upserted",
                }
                compensations.append(
                    (
                        [dict(record) for record in previous_records],
                        previous_ids,
                        new_ids,
                    )
                )
                working["audit_events"].append(
                    {"event": "source_version_activated", "source_id": source_id, "version": version, "at": checked_at}
                )
                summary["sources_changed"] += 1
            except Exception as exc:
                if isinstance(exc, PublicKnowledgeError) and str(exc) in {
                    "public_source_extract_url_mismatch",
                    "public_source_crawl_url_mismatch",
                }:
                    anomalies = [str(exc)]
                    summary["sources_quarantined"] += 1
                    summary["errors"].append(
                        {"source_id": source_id, "reason": "public_source_quarantined", "anomalies": anomalies}
                    )
                    if not dry_run:
                        record_quarantine(
                            source=source,
                            previous=previous,
                            checked_at=checked_at,
                            anomalies=anomalies,
                        )
                    continue
                summary["errors"].append(
                    {"source_id": source_id, "error_type": type(exc).__name__, "reason": str(exc)}
                )
        summary["completed_at"] = self.now()
        if dry_run:
            summary["status"] = "changed_dry_run" if summary["sources_changed"] else (
                "quarantined" if summary["sources_quarantined"] else "unchanged"
            )
        elif (
            summary["sources_changed"]
            or summary["sources_unchanged"]
            or summary["sources_quarantined"]
            or summary["sources_skipped_tombstone"]
        ):
            working["last_run_at"] = summary["completed_at"]
            try:
                _save_corpus(self.corpus_path, working)
            except Exception as commit_error:
                try:
                    for previous_records, previous_ids, new_ids in reversed(compensations):
                        if previous_records:
                            self._upsert(previous_records)
                        extra_ids = sorted(set(new_ids) - set(previous_ids))
                        if extra_ids:
                            self._delete_ids(extra_ids)
                except Exception as compensation_error:
                    raise PublicKnowledgeError(
                        "public_corpus_commit_failed_compensation_incomplete"
                    ) from compensation_error
                raise PublicKnowledgeError("public_corpus_commit_failed_compensated") from commit_error
            summary["status"] = (
                "partial" if summary["errors"] and summary["sources_changed"] else
                "quarantined" if summary["sources_quarantined"] and not summary["sources_changed"] else
                "changed" if summary["sources_changed"] else "unchanged"
            )
        else:
            summary["status"] = "failed"
        return summary

    def delete_source(self, source_id: str) -> dict[str, Any]:
        normalized_id = _safe_source_id(source_id)
        corpus = _load_corpus(self.corpus_path)
        source = corpus["sources"].get(normalized_id)
        if not isinstance(source, dict) or source.get("status") != "active":
            raise PublicKnowledgeError("public_source_not_active")
        record_ids = [str(record["_id"]) for record in source.get("records", [])]
        try:
            deleted = self._delete_ids(record_ids)
        except Exception as exc:
            try:
                self._upsert(source.get("records", []))
            except Exception as compensation_error:
                raise PublicKnowledgeError(
                    "public_source_delete_failed_compensation_incomplete"
                ) from compensation_error
            raise PublicKnowledgeError("public_source_delete_failed_compensated") from exc
        at = self.now()
        source["status"] = "deleted_tombstone"
        source["deleted_at"] = at
        source["last_result"] = "deleted"
        corpus["audit_events"].append({"event": "source_deleted", "source_id": normalized_id, "at": at})
        try:
            _save_corpus(self.corpus_path, corpus)
        except Exception as commit_error:
            try:
                self._upsert(source.get("records", []))
            except Exception as compensation_error:
                raise PublicKnowledgeError(
                    "public_source_delete_commit_failed_compensation_incomplete"
                ) from compensation_error
            raise PublicKnowledgeError(
                "public_source_delete_commit_failed_compensated"
            ) from commit_error
        return {"status": "deleted", "source_id": normalized_id, "records_deleted": deleted}

    def restore_source(self, source_id: str) -> dict[str, Any]:
        normalized_id = _safe_source_id(source_id)
        corpus = _load_corpus(self.corpus_path)
        source = corpus["sources"].get(normalized_id)
        if not isinstance(source, dict) or source.get("status") != "deleted_tombstone":
            raise PublicKnowledgeError("public_source_not_deleted")
        records = source.get("records")
        if not isinstance(records, list) or not records:
            raise PublicKnowledgeError("public_source_restore_records_missing")
        try:
            upserted = self._upsert(records)
        except Exception as exc:
            try:
                self._delete_ids([str(record["_id"]) for record in records])
            except Exception as compensation_error:
                raise PublicKnowledgeError(
                    "public_source_restore_failed_compensation_incomplete"
                ) from compensation_error
            raise PublicKnowledgeError("public_source_restore_failed_compensated") from exc
        at = self.now()
        source["status"] = "active"
        source.pop("deleted_at", None)
        source["last_result"] = "restored"
        corpus["audit_events"].append({"event": "source_restored", "source_id": normalized_id, "at": at})
        try:
            _save_corpus(self.corpus_path, corpus)
        except Exception as commit_error:
            try:
                self._delete_ids([str(record["_id"]) for record in records])
            except Exception as compensation_error:
                raise PublicKnowledgeError(
                    "public_source_restore_commit_failed_compensation_incomplete"
                ) from compensation_error
            raise PublicKnowledgeError(
                "public_source_restore_commit_failed_compensated"
            ) from commit_error
        return {"status": "restored", "source_id": normalized_id, "records_upserted": upserted}

    def reindex(self) -> dict[str, Any]:
        corpus = _load_corpus(self.corpus_path)
        records = [
            record
            for source in corpus["sources"].values()
            if isinstance(source, dict) and source.get("status") == "active"
            for record in source.get("records", [])
        ]
        if not records:
            raise PublicKnowledgeError("public_knowledge_reindex_empty")
        rebuilt_ids = {str(record["_id"]) for record in records}
        known_ids: set[str] = set(rebuilt_ids)
        for source in corpus["sources"].values():
            if not isinstance(source, Mapping):
                raise PublicKnowledgeError("public_knowledge_corpus_invalid")
            versions = source.get("versions", [])
            if not isinstance(versions, list):
                raise PublicKnowledgeError("public_knowledge_corpus_invalid")
            record_sets = [source.get("records", [])]
            record_sets.extend(
                version.get("records", [])
                for version in versions
                if isinstance(version, Mapping)
            )
            for record_set in record_sets:
                if not isinstance(record_set, list):
                    raise PublicKnowledgeError("public_knowledge_corpus_invalid")
                for record in record_set:
                    record_id = str(record.get("_id") or "") if isinstance(record, Mapping) else ""
                    if not _RECORD_ID_RE.fullmatch(record_id):
                        raise PublicKnowledgeError("public_knowledge_corpus_record_invalid")
                    known_ids.add(record_id)
        try:
            upserted = self._upsert(records)
        except Exception as exc:
            raise PublicKnowledgeError(
                "public_knowledge_reindex_failed_projection_preserved"
            ) from exc
        stale_ids = sorted(known_ids - rebuilt_ids)
        try:
            deleted = self._delete_ids(stale_ids)
        except Exception as exc:
            raise PublicKnowledgeError(
                "public_knowledge_reindex_cleanup_incomplete"
            ) from exc
        at = self.now()
        corpus["audit_events"].append(
            {
                "event": "public_namespace_reindexed",
                "records": upserted,
                "stale_records_deleted": deleted,
                "at": at,
            }
        )
        _save_corpus(self.corpus_path, corpus)
        return {
            "status": "rebuilt",
            "records_upserted": upserted,
            "records_deleted": deleted,
            "source_of_truth": "canonical_corpus",
        }


_EVIDENCE_REQUIRED_FIELDS = (
    "chunk_text",
    "source_id",
    "publisher",
    "authority",
    "source_url",
    "license_id",
    "license_ref",
    "attribution",
    "sector",
    "geography",
    "language",
    "published_at",
    "retrieved_at",
    "content_sha256",
    "version",
    "freshness_days",
    "fresh_until",
    "expires_at",
    "unit",
    "confidence",
    "evidence_ref",
    "admission_status",
    "data_classification",
)
_EVIDENCE_TEXT_FIELDS = tuple(
    field
    for field in _EVIDENCE_REQUIRED_FIELDS
    if field not in {"version", "freshness_days", "confidence"}
)


def _feasibility_evidence_context(
    *,
    as_of: str,
    evidence: Sequence[Mapping[str, Any]],
    gaps: Sequence[Mapping[str, str]],
) -> dict[str, Any]:
    evidence_rows = [dict(row) for row in evidence]
    gap_rows = [dict(row) for row in gaps]
    return {
        "contract_id": "public-knowledge-evidence.v1",
        "status": "ready" if evidence_rows and not gap_rows else "ready_with_gaps" if evidence_rows else "not_ready",
        "as_of": as_of,
        "evidence": evidence_rows,
        "gaps": gap_rows,
        "permitted_uses": [
            "market_size",
            "demand_context",
            "competition_context",
            "funding_cost_context",
            "government_spending",
            "investment_opportunities",
            "vision_2030_alignment",
            "sensitivity_context",
        ],
        "claims_project_success": False,
        "claims_funding_acceptance": False,
        "source_of_truth": False,
        "snapshot_eligible": False,
        "requires_separate_assumption_admission_for_finance": True,
    }


def build_unavailable_feasibility_evidence_context(
    reason: str,
    *,
    as_of: str | None = None,
) -> dict[str, Any]:
    normalized_reason = str(reason or "").strip()
    if not re.fullmatch(r"[a-z][a-z0-9_]{2,119}", normalized_reason):
        raise PublicKnowledgeError("public_knowledge_unavailable_reason_invalid")
    as_of_value = as_of or _utc_now()
    _parse_utc(as_of_value, field="as_of")
    return _feasibility_evidence_context(
        as_of=as_of_value,
        evidence=[],
        gaps=[{"record_id": "", "reason": normalized_reason}],
    )


def build_feasibility_evidence_context(
    search_response: Mapping[str, Any],
    *,
    as_of: str | None = None,
) -> dict[str, Any]:
    as_of_value = as_of or _utc_now()
    as_of_time = _parse_utc(as_of_value, field="as_of")
    payload = search_response.get("payload")
    result = payload.get("result") if isinstance(payload, Mapping) else None
    hits = result.get("hits") if isinstance(result, Mapping) else None
    if not isinstance(hits, list):
        raise PublicKnowledgeError("public_knowledge_search_response_invalid")
    evidence: list[dict[str, Any]] = []
    gaps: list[dict[str, str]] = []
    for hit in hits:
        fields = hit.get("fields") if isinstance(hit, Mapping) else None
        record_id = str(hit.get("_id") or "") if isinstance(hit, Mapping) else ""
        if not _RECORD_ID_RE.fullmatch(record_id):
            gaps.append({"record_id": record_id, "reason": "evidence_record_id_invalid"})
            continue
        if not isinstance(fields, Mapping):
            gaps.append({"record_id": record_id, "reason": "evidence_fields_missing"})
            continue
        missing = [
            field
            for field in _EVIDENCE_REQUIRED_FIELDS
            if fields.get(field) is None
            or (isinstance(fields.get(field), str) and not fields.get(field).strip())
            or isinstance(fields.get(field), (Mapping, list, tuple, set))
        ]
        if "unit" in missing:
            gaps.append({"record_id": record_id, "reason": "evidence_unit_missing"})
            continue
        if missing:
            gaps.append({"record_id": record_id, "reason": "evidence_metadata_incomplete"})
            continue
        if any(not isinstance(fields[field], str) for field in _EVIDENCE_TEXT_FIELDS):
            gaps.append({"record_id": record_id, "reason": "evidence_metadata_invalid"})
            continue
        try:
            _canonical_url(fields["source_url"])
            _validated_license_ref(fields["license_ref"])
            _safe_source_id(fields["source_id"])
            retrieved_at = _parse_utc(str(fields["retrieved_at"]), field="retrieved_at")
            fresh_until = _parse_utc(str(fields["fresh_until"]), field="fresh_until")
            expires_at = _parse_utc(str(fields["expires_at"]), field="expires_at")
        except PublicKnowledgeError:
            gaps.append({"record_id": record_id, "reason": "evidence_metadata_invalid"})
            continue
        if fresh_until < as_of_time:
            gaps.append({"record_id": record_id, "reason": "evidence_stale"})
            continue
        if expires_at < as_of_time:
            gaps.append({"record_id": record_id, "reason": "evidence_expired"})
            continue
        if fields.get("admission_status") != "auto_admitted_official_open":
            gaps.append({"record_id": record_id, "reason": "evidence_admission_invalid"})
            continue
        if fields.get("authority") not in _OFFICIAL_AUTHORITIES or fields.get("data_classification") != "public":
            gaps.append({"record_id": record_id, "reason": "evidence_authority_invalid"})
            continue
        if not _SHA256_RE.fullmatch(str(fields.get("content_sha256") or "")):
            gaps.append({"record_id": record_id, "reason": "evidence_hash_invalid"})
            continue
        expected_evidence_ref = (
            f"public:{fields['source_id']}:sha256:{fields['content_sha256']}"
        )
        if fields.get("evidence_ref") != expected_evidence_ref:
            gaps.append({"record_id": record_id, "reason": "evidence_lineage_invalid"})
            continue
        version = fields.get("version")
        freshness_days = fields.get("freshness_days")
        if (
            isinstance(version, bool)
            or not isinstance(version, int)
            or version < 1
            or isinstance(freshness_days, bool)
            or not isinstance(freshness_days, int)
            or freshness_days < 1
        ):
            gaps.append({"record_id": record_id, "reason": "evidence_version_invalid"})
            continue
        confidence = fields.get("confidence")
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not 0.0 <= float(confidence) <= 1.0:
            gaps.append({"record_id": record_id, "reason": "evidence_confidence_invalid"})
            continue
        score = hit.get("_score") if isinstance(hit, Mapping) else None
        if (
            isinstance(score, bool)
            or not isinstance(score, (int, float))
            or not math.isfinite(float(score))
        ):
            gaps.append({"record_id": record_id, "reason": "evidence_score_invalid"})
            continue
        if (
            retrieved_at > as_of_time
            or fresh_until != retrieved_at + timedelta(days=freshness_days)
            or expires_at < fresh_until
        ):
            gaps.append({"record_id": record_id, "reason": "evidence_temporal_invalid"})
            continue
        if _content_anomalies(fields["chunk_text"]):
            gaps.append({"record_id": record_id, "reason": "evidence_content_quarantined"})
            continue
        evidence.append(
            {
                "record_id": record_id,
                "score": float(score),
                **{field: fields[field] for field in _EVIDENCE_REQUIRED_FIELDS},
                "confidence": float(confidence),
                "source_of_truth": False,
            }
        )
    return _feasibility_evidence_context(
        as_of=as_of_value,
        evidence=evidence,
        gaps=gaps,
    )


def build_public_knowledge_sync_from_env(
    registry: Mapping[str, Any],
    *,
    corpus_path: Path = DEFAULT_PUBLIC_CORPUS,
) -> PublicKnowledgeSync:
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

    policy = ExternalAcquisitionPolicy.from_env()
    if not policy.enabled:
        raise ProviderConfigurationError("external_network_disabled_by_policy")
    scope = TrustedProviderScope.for_platform_workload(PUBLIC_KNOWLEDGE_WORKLOAD)
    admission = PublicKnowledgeSourcePolicy.from_registry(registry)
    transport = GovernedProviderTransport(GovernedExternalAcquisitionGateway(policy))
    return PublicKnowledgeSync(
        tavily=TavilyResearchClient.from_env(
            transport,
            scope=scope,
            admission_policy=admission,
        ),
        pinecone=PineconeKnowledgeClient.from_env(transport),
        scope=scope,
        corpus_path=corpus_path,
    )


def _validate_cli_mode(*, dry_run: bool, reindex: bool, source_id: str | None) -> None:
    if reindex and dry_run:
        raise PublicKnowledgeError("public_reindex_dry_run_conflict")
    if reindex and source_id:
        raise PublicKnowledgeError("public_reindex_source_filter_forbidden")


def main() -> int:
    parser = argparse.ArgumentParser(description="ASIE FC20-05 public economic knowledge sync")
    parser.add_argument("--registry", type=Path, default=DEFAULT_PUBLIC_SOURCE_REGISTRY)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_PUBLIC_CORPUS)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--reindex", action="store_true")
    parser.add_argument("--source-id")
    args = parser.parse_args()
    try:
        _validate_cli_mode(
            dry_run=bool(args.dry_run),
            reindex=bool(args.reindex),
            source_id=args.source_id,
        )
        registry = load_public_source_registry(args.registry)
        if args.source_id:
            registry = select_public_source(registry, args.source_id)
        service = build_public_knowledge_sync_from_env(registry, corpus_path=args.corpus)
        result = service.reindex() if args.reindex else service.run(registry, dry_run=args.dry_run)
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
    return 0 if result["status"] in {"changed", "unchanged", "changed_dry_run", "rebuilt"} else 1


if __name__ == "__main__":
    sys.exit(main())
