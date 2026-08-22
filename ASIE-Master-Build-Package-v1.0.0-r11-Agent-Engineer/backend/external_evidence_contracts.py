from __future__ import annotations

import hashlib
import ipaddress
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Final, Mapping
from urllib.parse import urlsplit


SHA256_RE: Final[re.Pattern[str]] = re.compile(r"^[0-9a-f]{64}$")
TOKEN_RE: Final[re.Pattern[str]] = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")

JOB_STATES: Final[frozenset[str]] = frozenset(
    {"queued", "running", "partial", "succeeded", "failed", "cancelled"}
)
REVIEW_DECISIONS: Final[frozenset[str]] = frozenset({"approved", "rejected"})
SUPERSESSION_DISPOSITIONS: Final[frozenset[str]] = frozenset({"superseded", "revoked"})


class ContractValidationError(ValueError):
    """Raised when untrusted evidence metadata violates the P0 contract."""


def canonical_json(value: Mapping[str, Any] | list[Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_hex(value: str | bytes | Mapping[str, Any] | list[Any]) -> str:
    if isinstance(value, (dict, list)):
        raw = canonical_json(value).encode("utf-8")
    elif isinstance(value, str):
        raw = value.encode("utf-8")
    else:
        raw = value
    return hashlib.sha256(raw).hexdigest()


def _require_token(name: str, value: str) -> None:
    if not isinstance(value, str) or TOKEN_RE.fullmatch(value) is None:
        raise ContractValidationError(f"invalid_{name}")


def _require_text(name: str, value: str, *, maximum: int) -> None:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ContractValidationError(f"invalid_{name}")


def _require_hash(name: str, value: str) -> None:
    if not isinstance(value, str) or SHA256_RE.fullmatch(value) is None:
        raise ContractValidationError(f"invalid_{name}")


def _parse_timestamp(name: str, value: str) -> datetime:
    if not isinstance(value, str) or len(value) > 40:
        raise ContractValidationError(f"invalid_{name}")
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ContractValidationError(f"invalid_{name}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ContractValidationError(f"invalid_{name}")
    return parsed


def _require_timestamp(name: str, value: str) -> None:
    _parse_timestamp(name, value)


def _require_https_url(value: str) -> None:
    if not isinstance(value, str) or len(value) > 2048:
        raise ContractValidationError("invalid_canonical_url")
    try:
        parsed = urlsplit(value)
        hostname = parsed.hostname
    except ValueError as exc:
        raise ContractValidationError("invalid_canonical_url") from exc
    if parsed.scheme != "https" or not hostname or parsed.username or parsed.password:
        raise ContractValidationError("invalid_canonical_url")
    if parsed.fragment:
        raise ContractValidationError("canonical_url_fragment_forbidden")
    hostname = hostname.rstrip(".").lower()
    if hostname == "localhost":
        raise ContractValidationError("canonical_url_host_forbidden")
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        pass
    else:
        if not address.is_global:
            raise ContractValidationError("canonical_url_host_forbidden")


def _validate_scope(organization_id: str, project_id: str) -> None:
    _require_token("organization_id", organization_id)
    _require_token("project_id", project_id)


def _record_hash(record_type: str, material: Mapping[str, Any]) -> str:
    return sha256_hex({"record_type": record_type, "schema_version": 1, **dict(material)})


@dataclass(frozen=True, slots=True)
class DiscoveryCandidate:
    candidate_id: str
    organization_id: str
    project_id: str
    source_id: str
    provider_id: str
    operation: str
    canonical_url: str
    title: str
    discovered_at: str
    payload_hash: str
    provenance_hash: str
    review_state: str = "review_required"

    def __post_init__(self) -> None:
        _validate_scope(self.organization_id, self.project_id)
        for name in ("candidate_id", "source_id", "provider_id", "operation"):
            _require_token(name, getattr(self, name))
        _require_https_url(self.canonical_url)
        _require_text("title", self.title, maximum=512)
        _require_timestamp("discovered_at", self.discovered_at)
        _require_hash("payload_hash", self.payload_hash)
        _require_hash("provenance_hash", self.provenance_hash)
        if self.review_state != "review_required":
            raise ContractValidationError("candidate_must_be_review_required")

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ExtractionJob:
    job_id: str
    organization_id: str
    project_id: str
    provider_id: str
    operation: str
    idempotency_key_hash: str
    request_hash: str
    state: str
    created_at: str
    updated_at: str
    candidate_id: str | None = None
    result_count: int = 0
    failure_code: str | None = None

    def __post_init__(self) -> None:
        _validate_scope(self.organization_id, self.project_id)
        for name in ("job_id", "provider_id", "operation"):
            _require_token(name, getattr(self, name))
        if self.candidate_id is not None:
            _require_token("candidate_id", self.candidate_id)
        _require_hash("idempotency_key_hash", self.idempotency_key_hash)
        _require_hash("request_hash", self.request_hash)
        if self.state not in JOB_STATES:
            raise ContractValidationError("invalid_job_state")
        _require_timestamp("created_at", self.created_at)
        _require_timestamp("updated_at", self.updated_at)
        if _parse_timestamp("updated_at", self.updated_at) < _parse_timestamp(
            "created_at", self.created_at
        ):
            raise ContractValidationError("job_updated_before_created")
        if not isinstance(self.result_count, int) or self.result_count < 0:
            raise ContractValidationError("invalid_result_count")
        if self.failure_code is not None:
            _require_token("failure_code", self.failure_code)
        if self.state in {"queued", "running", "succeeded", "cancelled"} and self.failure_code is not None:
            raise ContractValidationError("failure_code_not_allowed_for_state")
        if self.state in {"failed", "partial"} and self.failure_code is None:
            raise ContractValidationError("failure_code_required_for_state")

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class EvidenceArtifact:
    artifact_id: str
    organization_id: str
    project_id: str
    job_id: str
    candidate_id: str
    source_id: str
    canonical_url: str
    content_hash: str
    provenance_hash: str
    captured_at: str
    freshness_expires_at: str
    artifact_hash: str
    review_state: str = "review_required"

    @classmethod
    def build(
        cls,
        *,
        artifact_id: str,
        organization_id: str,
        project_id: str,
        job_id: str,
        candidate_id: str,
        source_id: str,
        canonical_url: str,
        content_hash: str,
        provenance_hash: str,
        captured_at: str,
        freshness_expires_at: str,
    ) -> "EvidenceArtifact":
        material = {
            "artifact_id": artifact_id,
            "organization_id": organization_id,
            "project_id": project_id,
            "job_id": job_id,
            "candidate_id": candidate_id,
            "source_id": source_id,
            "canonical_url": canonical_url,
            "content_hash": content_hash,
            "provenance_hash": provenance_hash,
            "captured_at": captured_at,
            "freshness_expires_at": freshness_expires_at,
            "review_state": "review_required",
        }
        return cls(**material, artifact_hash=_record_hash("EvidenceArtifact", material))

    def __post_init__(self) -> None:
        _validate_scope(self.organization_id, self.project_id)
        for name in ("artifact_id", "job_id", "candidate_id", "source_id"):
            _require_token(name, getattr(self, name))
        _require_https_url(self.canonical_url)
        _require_hash("content_hash", self.content_hash)
        _require_hash("provenance_hash", self.provenance_hash)
        _require_hash("artifact_hash", self.artifact_hash)
        _require_timestamp("captured_at", self.captured_at)
        _require_timestamp("freshness_expires_at", self.freshness_expires_at)
        if _parse_timestamp("freshness_expires_at", self.freshness_expires_at) <= _parse_timestamp(
            "captured_at", self.captured_at
        ):
            raise ContractValidationError("artifact_freshness_must_follow_capture")
        if self.review_state != "review_required":
            raise ContractValidationError("artifact_must_be_review_required")
        material = self.as_dict()
        supplied_hash = material.pop("artifact_hash")
        if supplied_hash != _record_hash("EvidenceArtifact", material):
            raise ContractValidationError("artifact_hash_mismatch")

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class EvidenceReview:
    review_id: str
    organization_id: str
    project_id: str
    artifact_id: str
    artifact_hash: str
    reviewer_user_id: str
    decision: str
    reason: str
    reviewed_at: str
    review_hash: str

    @classmethod
    def build(
        cls,
        *,
        review_id: str,
        organization_id: str,
        project_id: str,
        artifact_id: str,
        artifact_hash: str,
        reviewer_user_id: str,
        decision: str,
        reason: str,
        reviewed_at: str,
    ) -> "EvidenceReview":
        material = {
            "review_id": review_id,
            "organization_id": organization_id,
            "project_id": project_id,
            "artifact_id": artifact_id,
            "artifact_hash": artifact_hash,
            "reviewer_user_id": reviewer_user_id,
            "decision": decision,
            "reason": reason,
            "reviewed_at": reviewed_at,
        }
        return cls(**material, review_hash=_record_hash("EvidenceReview", material))

    def __post_init__(self) -> None:
        _validate_scope(self.organization_id, self.project_id)
        for name in ("review_id", "artifact_id", "reviewer_user_id"):
            _require_token(name, getattr(self, name))
        _require_hash("artifact_hash", self.artifact_hash)
        _require_hash("review_hash", self.review_hash)
        if self.decision not in REVIEW_DECISIONS:
            raise ContractValidationError("invalid_review_decision")
        _require_text("reason", self.reason, maximum=1000)
        _require_timestamp("reviewed_at", self.reviewed_at)
        material = self.as_dict()
        supplied_hash = material.pop("review_hash")
        if supplied_hash != _record_hash("EvidenceReview", material):
            raise ContractValidationError("review_hash_mismatch")

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class SupersessionRecord:
    record_id: str
    organization_id: str
    project_id: str
    predecessor_artifact_id: str
    predecessor_artifact_hash: str
    disposition: str
    reason: str
    actor_user_id: str
    recorded_at: str
    record_hash: str
    successor_artifact_id: str | None = None
    successor_artifact_hash: str | None = None

    @classmethod
    def build(
        cls,
        *,
        record_id: str,
        organization_id: str,
        project_id: str,
        predecessor_artifact_id: str,
        predecessor_artifact_hash: str,
        disposition: str,
        reason: str,
        actor_user_id: str,
        recorded_at: str,
        successor_artifact_id: str | None = None,
        successor_artifact_hash: str | None = None,
    ) -> "SupersessionRecord":
        material = {
            "record_id": record_id,
            "organization_id": organization_id,
            "project_id": project_id,
            "predecessor_artifact_id": predecessor_artifact_id,
            "predecessor_artifact_hash": predecessor_artifact_hash,
            "disposition": disposition,
            "reason": reason,
            "actor_user_id": actor_user_id,
            "recorded_at": recorded_at,
            "successor_artifact_id": successor_artifact_id,
            "successor_artifact_hash": successor_artifact_hash,
        }
        return cls(**material, record_hash=_record_hash("SupersessionRecord", material))

    def __post_init__(self) -> None:
        _validate_scope(self.organization_id, self.project_id)
        for name in ("record_id", "predecessor_artifact_id", "actor_user_id"):
            _require_token(name, getattr(self, name))
        _require_hash("predecessor_artifact_hash", self.predecessor_artifact_hash)
        _require_hash("record_hash", self.record_hash)
        if self.disposition not in SUPERSESSION_DISPOSITIONS:
            raise ContractValidationError("invalid_supersession_disposition")
        _require_text("reason", self.reason, maximum=1000)
        _require_timestamp("recorded_at", self.recorded_at)
        if self.disposition == "superseded":
            if self.successor_artifact_id is None or self.successor_artifact_hash is None:
                raise ContractValidationError("successor_required")
        elif self.successor_artifact_id is not None or self.successor_artifact_hash is not None:
            raise ContractValidationError("successor_forbidden_for_revocation")
        if self.successor_artifact_id is not None:
            _require_token("successor_artifact_id", self.successor_artifact_id)
        if self.successor_artifact_hash is not None:
            _require_hash("successor_artifact_hash", self.successor_artifact_hash)
        material = self.as_dict()
        supplied_hash = material.pop("record_hash")
        if supplied_hash != _record_hash("SupersessionRecord", material):
            raise ContractValidationError("supersession_hash_mismatch")

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)
