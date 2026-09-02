from __future__ import annotations

from dataclasses import dataclass
import ipaddress
import re
from typing import Any, Mapping, Sequence
from urllib.parse import unquote, urlsplit

from backend.source_registry import ENABLED_SOURCE_REQUIRED_FIELDS


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_DOMAIN_LABEL_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
_PLATFORM_SCOPE = "__platform__"
_PRIVATE_HOST_SUFFIXES = (".internal", ".local", ".localhost", ".lan", ".home")


class SourceAdmissionError(PermissionError):
    """Fail-closed source admission failure safe to expose as a reason code."""


def _normalized_context(value: str, *, field: str) -> str:
    normalized = str(value or "").strip().lower().replace(" ", "_")
    if not normalized or len(normalized) > 160 or not re.fullmatch(r"[a-z0-9_.:-]+", normalized):
        raise SourceAdmissionError(f"invalid_{field}")
    return normalized


def _normalized_host(value: str) -> str:
    raw = str(value or "").strip().rstrip(".")
    try:
        normalized = raw.encode("idna").decode("ascii").lower()
    except (UnicodeError, ValueError) as exc:
        raise SourceAdmissionError("source_host_invalid") from exc
    if (
        not normalized
        or len(normalized) > 253
        or normalized == "localhost"
        or normalized.endswith(_PRIVATE_HOST_SUFFIXES)
    ):
        raise SourceAdmissionError("source_private_host_denied")
    try:
        ipaddress.ip_address(normalized)
    except ValueError:
        pass
    else:
        raise SourceAdmissionError("source_ip_literal_denied")
    labels = normalized.split(".")
    if len(labels) < 2 or any(not _DOMAIN_LABEL_RE.fullmatch(label) for label in labels):
        raise SourceAdmissionError("source_host_invalid")
    return normalized


def _parsed_https_url(value: str):
    try:
        parsed = urlsplit(str(value or "").strip())
        port = parsed.port
        host = _normalized_host(parsed.hostname or "")
    except (ValueError, UnicodeError) as exc:
        raise SourceAdmissionError("source_url_must_be_canonical_https") from exc
    if (
        parsed.scheme.lower() != "https"
        or not host
        or parsed.username
        or parsed.password
        or port not in {None, 443}
        or parsed.fragment
    ):
        raise SourceAdmissionError("source_url_must_be_canonical_https")
    return parsed


def _host(value: str) -> str:
    return _normalized_host(_parsed_https_url(value).hostname or "")


def _normalized_domain(value: str) -> str:
    raw = str(value or "").strip()
    if not raw or any(character in raw for character in ("/", "\\", "@", ":", "?", "#")):
        raise SourceAdmissionError("invalid_discovery_domain")
    return _normalized_host(raw)


def _canonical_path(value: str, *, reason: str) -> str:
    raw = str(value or "/")
    if (
        not raw.startswith("/")
        or "\\" in raw
        or "//" in raw
        or any(ord(character) < 32 or ord(character) == 127 for character in raw)
    ):
        raise SourceAdmissionError(reason)
    try:
        decoded = unquote(raw, encoding="utf-8", errors="strict")
        decoded_twice = unquote(decoded, encoding="utf-8", errors="strict")
    except (UnicodeDecodeError, ValueError) as exc:
        raise SourceAdmissionError(reason) from exc
    if decoded_twice != decoded or "%" in decoded:
        raise SourceAdmissionError(reason)
    if (
        not decoded.startswith("/")
        or "\\" in decoded
        or "//" in decoded
        or any(segment in {".", ".."} for segment in decoded.split("/"))
        or any(ord(character) < 32 or ord(character) == 127 for character in decoded)
    ):
        raise SourceAdmissionError(reason)
    return decoded if decoded == "/" else decoded.rstrip("/")


def _sequence(value: Any, *, field: str, maximum: int = 64) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or len(value) > maximum:
        raise SourceAdmissionError(f"invalid_{field}")
    values = tuple(str(item or "").strip() for item in value)
    if any(not item or len(item) > 500 for item in values):
        raise SourceAdmissionError(f"invalid_{field}")
    return values


def _record_value(record: Mapping[str, Any], field: str, default: Any = None) -> Any:
    if field in record:
        return record.get(field)
    notes = record.get("notes")
    return notes.get(field, default) if isinstance(notes, Mapping) else default


def _scopes(record: Mapping[str, Any], field: str) -> frozenset[str]:
    raw = _record_value(record, field)
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        return frozenset()
    # A wildcard is valid only in a server-owned source record.  It is never
    # accepted from the request context, which still passes through
    # _normalized_context() in build_search_plan().
    return frozenset(
        "*" if str(item).strip() == "*" else _normalized_context(str(item), field=field)
        for item in raw
    )


def _path_within(path: str, root: str) -> bool:
    return root == "/" or path == root or path.startswith(root + "/")


def _graph_path_pattern(root: str) -> str:
    if root == "/":
        return r"^/.*$"
    return rf"^{re.escape(root)}(?:/.*)?$"


def _source_path_roots(source: Mapping[str, Any], approved_path: str) -> tuple[str, ...]:
    raw_paths = _record_value(source, "allowed_paths")
    if raw_paths is None or raw_paths == []:
        return (approved_path,)
    paths = _sequence(raw_paths, field="admitted_source_paths")
    canonical = tuple(
        _canonical_path(path, reason="invalid_admitted_source_path")
        for path in paths
    )
    return tuple(dict.fromkeys(canonical))


@dataclass(frozen=True)
class TavilySourceAdmissionPolicy:
    """Server-owned discovery and content-admission policy.

    Candidate sources may be used only to constrain discovery. Content access
    requires an enabled, reviewed source with exact tenant/project ownership,
    terms evidence, and an admitted URL path.
    """

    organization_id: str
    project_id: str
    records: tuple[Mapping[str, Any], ...]

    @classmethod
    def from_records(
        cls,
        *,
        organization_id: str,
        project_id: str,
        records: Sequence[Mapping[str, Any]],
    ) -> "TavilySourceAdmissionPolicy":
        organization = str(organization_id or "").strip()
        project = str(project_id or "").strip()
        if not organization or not project:
            raise SourceAdmissionError("organization_and_project_required")
        return cls(organization_id=organization, project_id=project, records=tuple(dict(row) for row in records))

    @classmethod
    def default_deny(cls) -> "TavilySourceAdmissionPolicy":
        return cls(organization_id="_unbound", project_id="_unbound", records=())

    def _owned(self, record: Mapping[str, Any]) -> bool:
        organization_scope = str(_record_value(record, "organization_id", _PLATFORM_SCOPE) or _PLATFORM_SCOPE)
        project_scope = str(_record_value(record, "project_id", "*") or "*")
        return organization_scope in {_PLATFORM_SCOPE, self.organization_id} and project_scope in {"*", self.project_id}

    def authorize_discovery(
        self,
        *,
        sector_id: str,
        geography: str,
        requested_include_domains: Sequence[str] = (),
        requested_exclude_domains: Sequence[str] = (),
    ) -> dict[str, Any]:
        sector = _normalized_context(sector_id, field="sector_id")
        geography_scope = _normalized_context(geography, field="geography")
        admitted: list[Mapping[str, Any]] = []
        for record in self.records:
            if not self._owned(record) or record.get("state") not in {"candidate", "enabled"}:
                continue
            if _record_value(record, "discovery_allowed") is not True:
                continue
            sectors = _scopes(record, "discovery_sectors")
            geographies = _scopes(record, "discovery_geographies")
            if sector not in sectors and "*" not in sectors:
                continue
            if geography_scope not in geographies and "*" not in geographies:
                continue
            _parsed_https_url(str(record.get("url") or ""))
            admitted.append(record)

        domains = sorted({_host(str(record["url"])) for record in admitted})
        if not domains:
            raise SourceAdmissionError("source_discovery_scope_empty")

        requested_includes = {
            _normalized_domain(domain)
            for domain in _sequence(requested_include_domains, field="requested_include_domains")
        } if requested_include_domains else set()
        requested_excludes = {
            _normalized_domain(domain)
            for domain in _sequence(requested_exclude_domains, field="requested_exclude_domains")
        } if requested_exclude_domains else set()
        admitted_domains = set(domains)
        if (
            requested_includes and not requested_includes.issubset(admitted_domains)
        ) or not requested_excludes.issubset(admitted_domains):
            raise SourceAdmissionError("client_discovery_scope_widening_denied")

        effective_domains = sorted(requested_includes or admitted_domains)
        effective_sources = sorted(
            str(record.get("source_id") or "")
            for record in admitted
            if _host(str(record["url"])) in set(effective_domains)
        )
        return {
            "operation": "discovery_search",
            "sector_id": sector,
            "geography": geography_scope,
            "include_domains": effective_domains,
            "exclude_domains": sorted(requested_excludes),
            "source_ids": effective_sources,
            "review_status": "review_required",
            "eligible_for_controlled_assumptions": False,
        }

    def authorize_graph_scope(
        self,
        *,
        admission: Mapping[str, Any],
        requested_select_paths: Sequence[str] = (),
        requested_exclude_paths: Sequence[str] = (),
    ) -> dict[str, list[str]]:
        if admission.get("operation") not in {"crawl", "map"}:
            raise SourceAdmissionError("graph_scope_requires_crawl_or_map_admission")
        raw_roots = admission.get("allowed_path_roots")
        allowed_roots = tuple(
            _canonical_path(path, reason="invalid_admitted_source_path")
            for path in _sequence(raw_roots, field="admitted_source_paths")
        )
        requested_roots = tuple(
            _canonical_path(path, reason="invalid_requested_graph_path")
            for path in _sequence(requested_select_paths, field="requested_select_paths")
        ) if requested_select_paths else ()
        if requested_roots and any(
            not any(_path_within(path, allowed_root) for allowed_root in allowed_roots)
            for path in requested_roots
        ):
            raise SourceAdmissionError("client_graph_scope_widening_denied")

        effective_roots = tuple(dict.fromkeys(requested_roots or allowed_roots))
        excluded_roots = tuple(
            _canonical_path(path, reason="invalid_requested_graph_path")
            for path in _sequence(requested_exclude_paths, field="requested_exclude_paths")
        ) if requested_exclude_paths else ()
        if any(
            not any(_path_within(path, selected_root) for selected_root in effective_roots)
            for path in excluded_roots
        ):
            raise SourceAdmissionError("client_graph_scope_widening_denied")

        select_domains = admission.get("select_domains")
        if not isinstance(select_domains, list) or not select_domains:
            raise SourceAdmissionError("server_graph_domain_scope_missing")
        return {
            "select_domains": [str(value) for value in select_domains],
            "select_paths": [_graph_path_pattern(path) for path in effective_roots],
            "exclude_paths": [_graph_path_pattern(path) for path in dict.fromkeys(excluded_roots)],
        }

    def authorize_content_url(self, *, source_id: str, url: str, operation: str) -> dict[str, Any]:
        if operation not in {"extract", "crawl", "map"}:
            raise SourceAdmissionError("unsupported_source_operation")
        source = next((record for record in self.records if str(record.get("source_id") or "") == source_id), None)
        if source is None:
            raise SourceAdmissionError("unknown_source_denied")
        if not self._owned(source):
            raise SourceAdmissionError("cross_tenant_source_denied")
        if source.get("state") != "enabled":
            raise SourceAdmissionError("source_not_enabled_for_content_access")
        if source.get("reviewer_decision") != "approved":
            raise SourceAdmissionError("source_review_approval_required")

        missing = [field for field in ENABLED_SOURCE_REQUIRED_FIELDS if not source.get(field)]
        if missing:
            raise SourceAdmissionError("enabled_source_evidence_incomplete")
        terms_hash = str(source.get("terms_hash") or "").strip().lower()
        if not _SHA256_RE.fullmatch(terms_hash):
            raise SourceAdmissionError("source_terms_hash_invalid")

        approved = _parsed_https_url(str(source.get("url") or ""))
        requested = _parsed_https_url(url)
        approved_host = _host(approved.geturl())
        requested_host = _host(requested.geturl())
        if approved_host != requested_host:
            raise SourceAdmissionError("source_host_not_admitted")
        if requested.query and _record_value(source, "allow_query_parameters") is not True:
            raise SourceAdmissionError("source_query_parameters_not_admitted")

        approved_path = _canonical_path(approved.path or "/", reason="invalid_admitted_source_path")
        requested_path = _canonical_path(requested.path or "/", reason="source_path_not_admitted")
        allowed_roots = _source_path_roots(source, approved_path)
        if not any(_path_within(requested_path, root) for root in allowed_roots):
            raise SourceAdmissionError("source_path_not_admitted")

        return {
            "operation": operation,
            "source_id": source_id,
            "host": requested_host,
            "path": requested_path,
            "allowed_path_roots": list(allowed_roots),
            "select_domains": [rf"^{re.escape(requested_host)}$"],
            "organization_scope": str(_record_value(source, "organization_id", _PLATFORM_SCOPE) or _PLATFORM_SCOPE),
            "project_scope": str(_record_value(source, "project_id", "*") or "*"),
            "terms_hash": terms_hash,
            "license_snapshot_ref": str(source.get("license_snapshot_ref")),
            "attribution": str(source.get("attribution")),
            "review_status": "review_required",
            "eligible_for_controlled_assumptions": False,
        }
