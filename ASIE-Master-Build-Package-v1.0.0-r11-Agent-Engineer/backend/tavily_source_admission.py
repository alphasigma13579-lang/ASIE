from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Mapping, Sequence
from urllib.parse import urlsplit

from backend.source_registry import ENABLED_SOURCE_REQUIRED_FIELDS


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_PLATFORM_SCOPE = "__platform__"


class SourceAdmissionError(PermissionError):
    """Fail-closed source admission failure safe to expose as a reason code."""


def _normalized_context(value: str, *, field: str) -> str:
    normalized = str(value or "").strip().lower().replace(" ", "_")
    if not normalized or len(normalized) > 160 or not re.fullmatch(r"[a-z0-9_.:-]+", normalized):
        raise SourceAdmissionError(f"invalid_{field}")
    return normalized


def _parsed_https_url(value: str):
    parsed = urlsplit(str(value or "").strip())
    if (
        parsed.scheme.lower() != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.port not in {None, 443}
        or parsed.fragment
    ):
        raise SourceAdmissionError("source_url_must_be_canonical_https")
    return parsed


def _host(value: str) -> str:
    return (_parsed_https_url(value).hostname or "").lower().rstrip(".")


def _scopes(record: Mapping[str, Any], field: str) -> frozenset[str]:
    raw = record.get(field)
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        return frozenset()
    return frozenset(_normalized_context(str(item), field=field) for item in raw)


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
        organization_scope = str(record.get("organization_id") or _PLATFORM_SCOPE)
        project_scope = str(record.get("project_id") or "*")
        return organization_scope in {_PLATFORM_SCOPE, self.organization_id} and project_scope in {"*", self.project_id}

    def authorize_discovery(
        self,
        *,
        sector_id: str,
        geography: str,
        requested_include_domains: Sequence[str] = (),
    ) -> dict[str, Any]:
        sector = _normalized_context(sector_id, field="sector_id")
        geography_scope = _normalized_context(geography, field="geography")
        admitted: list[Mapping[str, Any]] = []
        for record in self.records:
            if not self._owned(record) or record.get("state") not in {"candidate", "enabled"}:
                continue
            if record.get("discovery_allowed") is not True:
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

        requested = {
            str(domain or "").strip().lower().rstrip(".")
            for domain in requested_include_domains
            if str(domain or "").strip()
        }
        if requested and not requested.issubset(set(domains)):
            raise SourceAdmissionError("client_discovery_scope_widening_denied")

        return {
            "operation": "discovery_search",
            "sector_id": sector,
            "geography": geography_scope,
            "include_domains": domains,
            "source_ids": sorted(str(record.get("source_id") or "") for record in admitted),
            "review_status": "review_required",
            "eligible_for_controlled_assumptions": False,
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
        if _host(approved.geturl()) != _host(requested.geturl()):
            raise SourceAdmissionError("source_host_not_admitted")
        if requested.query and source.get("allow_query_parameters") is not True:
            raise SourceAdmissionError("source_query_parameters_not_admitted")

        approved_path = approved.path or "/"
        raw_paths = source.get("allowed_paths")
        allowed_paths = (
            [str(path) for path in raw_paths]
            if isinstance(raw_paths, Sequence) and not isinstance(raw_paths, (str, bytes))
            else []
        )
        if allowed_paths:
            canonical_paths = []
            for path in allowed_paths:
                if not path.startswith("/") or ".." in path or "//" in path:
                    raise SourceAdmissionError("invalid_admitted_source_path")
                canonical_paths.append(path)
            path_allowed = any(
                requested.path == path.rstrip("/") or requested.path.startswith(path.rstrip("/") + "/")
                for path in canonical_paths
            )
        else:
            path_allowed = requested.path.rstrip("/") == approved_path.rstrip("/")
        if not path_allowed:
            raise SourceAdmissionError("source_path_not_admitted")

        return {
            "operation": operation,
            "source_id": source_id,
            "host": _host(requested.geturl()),
            "path": requested.path or "/",
            "organization_scope": str(source.get("organization_id") or _PLATFORM_SCOPE),
            "project_scope": str(source.get("project_id") or "*"),
            "terms_hash": terms_hash,
            "license_snapshot_ref": str(source.get("license_snapshot_ref")),
            "attribution": str(source.get("attribution")),
            "review_status": "review_required",
            "eligible_for_controlled_assumptions": False,
        }
