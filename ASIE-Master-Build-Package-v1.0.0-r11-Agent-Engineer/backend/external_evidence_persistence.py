from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping, Sequence

from backend.external_evidence_authorization import (
    CANCEL,
    READ,
    REVIEW,
    WRITE,
    AuthorizedScope,
    ExternalEvidenceAuthorizer,
    PrincipalLike,
)
from backend.external_evidence_contracts import (
    ContractValidationError,
    DiscoveryCandidate,
    EvidenceArtifact,
    EvidenceReview,
    ExtractionJob,
    SupersessionRecord,
    canonical_json,
    sha256_hex,
)


Clock = Callable[[], str]
SourceStatusResolver = Callable[[str, str, str], str | None]
Migration = tuple[int, str, Sequence[str]]


class ExternalEvidencePersistenceError(RuntimeError):
    pass


class ExternalEvidenceNotFound(ExternalEvidencePersistenceError):
    pass


class ExternalEvidenceConflict(ExternalEvidencePersistenceError):
    pass


class ExternalEvidenceMigrationError(ExternalEvidencePersistenceError):
    pass


class ExternalEvidenceAdmissionError(ExternalEvidenceConflict):
    pass


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


class ExternalEvidenceStore:
    """Isolated SQLite store for FC20-04 external-evidence metadata.

    Raw provider payloads are intentionally absent. The store persists bounded
    metadata and cryptographic hashes only; every tenant object operation is
    authorized before its transaction begins.
    """

    SCHEMA_VERSION = 2
    _ALLOWED_TRANSITIONS = {
        "queued": frozenset({"running", "failed", "cancelled"}),
        "running": frozenset({"partial", "succeeded", "failed", "cancelled"}),
        "partial": frozenset(),
        "succeeded": frozenset(),
        "failed": frozenset(),
        "cancelled": frozenset(),
    }
    _SAFE_AUDIT_KEYS = frozenset(
        {
            "state",
            "prior_state",
            "decision",
            "disposition",
            "created",
            "failure_code",
            "result_count",
        }
    )

    def __init__(
        self,
        db_path: str | Path,
        *,
        authorizer: ExternalEvidenceAuthorizer,
        clock: Clock = utc_now,
        busy_timeout_ms: int = 5_000,
        source_status_resolver: SourceStatusResolver | None = None,
    ) -> None:
        if isinstance(busy_timeout_ms, bool) or not isinstance(busy_timeout_ms, int):
            raise ValueError("busy_timeout_ms_must_be_non_negative_integer")
        if busy_timeout_ms < 0:
            raise ValueError("busy_timeout_ms_must_be_non_negative_integer")
        self._db_path = Path(db_path)
        self._authorizer = authorizer
        self._clock = clock
        self._busy_timeout_ms = busy_timeout_ms
        self._source_status_resolver = source_status_resolver

    def initialize(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        migration_plan = self._migrations()
        expected_versions = list(range(1, self.SCHEMA_VERSION + 1))
        if [version for version, _, _ in migration_plan] != expected_versions:
            raise ExternalEvidenceMigrationError("invalid_runtime_migration_plan")

        with self._transaction() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS external_evidence_schema_migrations (
                    version INTEGER PRIMARY KEY,
                    migration_id TEXT NOT NULL UNIQUE,
                    checksum TEXT NOT NULL,
                    applied_at TEXT NOT NULL
                )
                """
            )
            applied = connection.execute(
                "SELECT version, migration_id, checksum FROM external_evidence_schema_migrations ORDER BY version"
            ).fetchall()
            if any(int(row["version"]) > self.SCHEMA_VERSION for row in applied):
                raise ExternalEvidenceMigrationError("database_schema_is_newer_than_runtime")

            applied_by_version = {int(row["version"]): row for row in applied}
            if any(version not in expected_versions for version in applied_by_version):
                raise ExternalEvidenceMigrationError("database_migration_history_unknown")

            for version, migration_id, statements in migration_plan:
                checksum = sha256_hex("\n".join(statements))
                existing = applied_by_version.get(version)
                if existing is not None:
                    if (
                        existing["migration_id"] != migration_id
                        or existing["checksum"] != checksum
                    ):
                        raise ExternalEvidenceMigrationError("migration_checksum_mismatch")
                    continue

                for statement in statements:
                    connection.execute(statement)
                connection.execute(
                    """
                    INSERT INTO external_evidence_schema_migrations(
                        version, migration_id, checksum, applied_at
                    ) VALUES (?, ?, ?, ?)
                    """,
                    (version, migration_id, checksum, self._clock()),
                )

    def migration_registry(self) -> list[dict[str, Any]]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT version, migration_id, checksum, applied_at FROM external_evidence_schema_migrations ORDER BY version"
            ).fetchall()
        return [dict(row) for row in rows]

    def create_candidate(
        self, principal: PrincipalLike, candidate: DiscoveryCandidate
    ) -> DiscoveryCandidate:
        scope = self._scope(principal, candidate.organization_id, candidate.project_id, WRITE)
        with self._transaction(integrity_error_code="candidate_persistence_conflict") as connection:
            connection.execute(
                """
                INSERT INTO external_evidence_candidates(
                    organization_id, project_id, candidate_id, source_id, provider_id,
                    operation, canonical_url, title, discovered_at, payload_hash,
                    provenance_hash, review_state
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    candidate.organization_id,
                    candidate.project_id,
                    candidate.candidate_id,
                    candidate.source_id,
                    candidate.provider_id,
                    candidate.operation,
                    candidate.canonical_url,
                    candidate.title,
                    candidate.discovered_at,
                    candidate.payload_hash,
                    candidate.provenance_hash,
                    candidate.review_state,
                ),
            )
            self._append_audit(
                connection,
                scope,
                object_type="candidate",
                object_id=candidate.candidate_id,
                action="candidate.created",
                details={"state": candidate.review_state},
            )
        return candidate

    def get_candidate(
        self,
        principal: PrincipalLike,
        *,
        organization_id: str,
        project_id: str,
        candidate_id: str,
    ) -> DiscoveryCandidate:
        self._scope(principal, organization_id, project_id, READ)
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT * FROM external_evidence_candidates
                WHERE organization_id = ? AND project_id = ? AND candidate_id = ?
                """,
                (organization_id, project_id, candidate_id),
            ).fetchone()
        if row is None:
            raise ExternalEvidenceNotFound("external_evidence_object_not_found")
        return self._candidate_from_row(row)

    def create_or_get_job(
        self, principal: PrincipalLike, job: ExtractionJob
    ) -> tuple[ExtractionJob, bool]:
        if job.state != "queued":
            raise ExternalEvidenceConflict("new_job_must_be_queued")
        scope = self._scope(principal, job.organization_id, job.project_id, WRITE)
        with self._transaction(integrity_error_code="job_persistence_conflict") as connection:
            existing = connection.execute(
                """
                SELECT * FROM external_evidence_jobs
                WHERE organization_id = ? AND project_id = ? AND idempotency_key_hash = ?
                """,
                (job.organization_id, job.project_id, job.idempotency_key_hash),
            ).fetchone()
            if existing is not None:
                stored = self._job_from_row(existing)
                if (
                    stored.request_hash != job.request_hash
                    or stored.provider_id != job.provider_id
                    or stored.operation != job.operation
                    or stored.candidate_id != job.candidate_id
                ):
                    raise ExternalEvidenceConflict("idempotency_key_reused_for_different_request")
                return stored, False

            connection.execute(
                """
                INSERT INTO external_evidence_jobs(
                    organization_id, project_id, job_id, provider_id, operation,
                    idempotency_key_hash, request_hash, state, created_at, updated_at,
                    candidate_id, result_count, failure_code
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job.organization_id,
                    job.project_id,
                    job.job_id,
                    job.provider_id,
                    job.operation,
                    job.idempotency_key_hash,
                    job.request_hash,
                    job.state,
                    job.created_at,
                    job.updated_at,
                    job.candidate_id,
                    job.result_count,
                    job.failure_code,
                ),
            )
            self._append_audit(
                connection,
                scope,
                object_type="job",
                object_id=job.job_id,
                action="job.created",
                details={"state": job.state, "created": True},
            )
        return job, True

    def transition_job(self, principal: PrincipalLike, job: ExtractionJob) -> ExtractionJob:
        action = CANCEL if job.state == "cancelled" else WRITE
        scope = self._scope(principal, job.organization_id, job.project_id, action)
        with self._transaction() as connection:
            row = connection.execute(
                """
                SELECT * FROM external_evidence_jobs
                WHERE organization_id = ? AND project_id = ? AND job_id = ?
                """,
                (job.organization_id, job.project_id, job.job_id),
            ).fetchone()
            if row is None:
                raise ExternalEvidenceNotFound("external_evidence_object_not_found")
            prior = self._job_from_row(row)
            immutable_changed = any(
                getattr(prior, field) != getattr(job, field)
                for field in (
                    "organization_id",
                    "project_id",
                    "job_id",
                    "provider_id",
                    "operation",
                    "idempotency_key_hash",
                    "request_hash",
                    "created_at",
                    "candidate_id",
                )
            )
            if immutable_changed:
                raise ExternalEvidenceConflict("job_identity_is_immutable")
            if self._parse_admission_timestamp(job.updated_at) < self._parse_admission_timestamp(
                prior.updated_at
            ):
                raise ExternalEvidenceConflict("job_updated_at_must_be_monotonic")
            if prior.state == job.state:
                if prior == job:
                    return prior
                raise ExternalEvidenceConflict("same_state_transition_must_be_identical")
            if job.state not in self._ALLOWED_TRANSITIONS[prior.state]:
                raise ExternalEvidenceConflict("invalid_job_state_transition")

            connection.execute(
                """
                UPDATE external_evidence_jobs
                SET state = ?, updated_at = ?, result_count = ?, failure_code = ?
                WHERE organization_id = ? AND project_id = ? AND job_id = ?
                """,
                (
                    job.state,
                    job.updated_at,
                    job.result_count,
                    job.failure_code,
                    job.organization_id,
                    job.project_id,
                    job.job_id,
                ),
            )
            self._append_audit(
                connection,
                scope,
                object_type="job",
                object_id=job.job_id,
                action="job.transitioned",
                details={
                    "prior_state": prior.state,
                    "state": job.state,
                    "failure_code": job.failure_code,
                    "result_count": job.result_count,
                },
            )
        return job

    def get_job(
        self,
        principal: PrincipalLike,
        *,
        organization_id: str,
        project_id: str,
        job_id: str,
    ) -> ExtractionJob:
        self._scope(principal, organization_id, project_id, READ)
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT * FROM external_evidence_jobs
                WHERE organization_id = ? AND project_id = ? AND job_id = ?
                """,
                (organization_id, project_id, job_id),
            ).fetchone()
        if row is None:
            raise ExternalEvidenceNotFound("external_evidence_object_not_found")
        return self._job_from_row(row)

    def create_or_get_artifact(
        self, principal: PrincipalLike, artifact: EvidenceArtifact
    ) -> tuple[EvidenceArtifact, bool]:
        scope = self._scope(principal, artifact.organization_id, artifact.project_id, WRITE)
        try:
            with self._transaction(integrity_error_code="artifact_persistence_conflict") as connection:
                job_row = connection.execute(
                    """
                    SELECT state, candidate_id FROM external_evidence_jobs
                    WHERE organization_id = ? AND project_id = ? AND job_id = ?
                    """,
                    (artifact.organization_id, artifact.project_id, artifact.job_id),
                ).fetchone()
                if job_row is None or job_row["state"] != "succeeded":
                    raise ExternalEvidenceConflict("artifact_requires_succeeded_job")
                if job_row["candidate_id"] != artifact.candidate_id:
                    raise ExternalEvidenceConflict("artifact_candidate_mismatch")

                candidate_row = connection.execute(
                    """
                    SELECT source_id, canonical_url, provenance_hash
                    FROM external_evidence_candidates
                    WHERE organization_id = ? AND project_id = ? AND candidate_id = ?
                    """,
                    (artifact.organization_id, artifact.project_id, artifact.candidate_id),
                ).fetchone()
                if candidate_row is None or any(
                    candidate_row[field] != getattr(artifact, field)
                    for field in ("source_id", "canonical_url", "provenance_hash")
                ):
                    raise ExternalEvidenceConflict("artifact_provenance_mismatch")

                existing = connection.execute(
                    """
                    SELECT * FROM external_evidence_artifacts
                    WHERE organization_id = ? AND project_id = ? AND source_id = ? AND content_hash = ?
                    """,
                    (
                        artifact.organization_id,
                        artifact.project_id,
                        artifact.source_id,
                        artifact.content_hash,
                    ),
                ).fetchone()
                if existing is not None:
                    stored = self._artifact_from_row(existing)
                    if stored.provenance_hash != artifact.provenance_hash:
                        raise ExternalEvidenceConflict("duplicate_content_has_different_provenance")
                    return stored, False

                connection.execute(
                    """
                    INSERT INTO external_evidence_artifacts(
                        organization_id, project_id, artifact_id, job_id, candidate_id,
                        source_id, canonical_url, content_hash, provenance_hash, captured_at,
                        freshness_expires_at, artifact_hash, review_state
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        artifact.organization_id,
                        artifact.project_id,
                        artifact.artifact_id,
                        artifact.job_id,
                        artifact.candidate_id,
                        artifact.source_id,
                        artifact.canonical_url,
                        artifact.content_hash,
                        artifact.provenance_hash,
                        artifact.captured_at,
                        artifact.freshness_expires_at,
                        artifact.artifact_hash,
                        artifact.review_state,
                    ),
                )
                self._append_audit(
                    connection,
                    scope,
                    object_type="artifact",
                    object_id=artifact.artifact_id,
                    action="artifact.created",
                    details={"state": artifact.review_state, "created": True},
                )
            return artifact, True
        except ExternalEvidenceConflict as exc:
            with self._transaction() as connection:
                self._append_audit(
                    connection,
                    scope,
                    object_type="artifact",
                    object_id=artifact.artifact_id,
                    action="artifact.rejected",
                    details={"decision": "denied", "failure_code": str(exc)},
                )
            raise

    def get_artifact(
        self,
        principal: PrincipalLike,
        *,
        organization_id: str,
        project_id: str,
        artifact_id: str,
    ) -> EvidenceArtifact:
        self._scope(principal, organization_id, project_id, READ)
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT * FROM external_evidence_artifacts
                WHERE organization_id = ? AND project_id = ? AND artifact_id = ?
                """,
                (organization_id, project_id, artifact_id),
            ).fetchone()
        if row is None:
            raise ExternalEvidenceNotFound("external_evidence_object_not_found")
        return self._artifact_from_row(row)

    def require_approved_artifact(
        self,
        principal: PrincipalLike,
        *,
        organization_id: str,
        project_id: str,
        artifact_id: str,
        as_of: str,
    ) -> EvidenceArtifact:
        scope = self._scope(principal, organization_id, project_id, READ)
        as_of_timestamp = self._parse_admission_timestamp(as_of)
        denial: str | None = None
        admitted: EvidenceArtifact | None = None

        # Resolve the source state without holding SQLite's write lock. The
        # resolver is a local, bounded dependency supplied by the composition root.
        with self._connection() as connection:
            status_snapshot_row = connection.execute(
                """
                SELECT * FROM external_evidence_artifacts
                WHERE organization_id = ? AND project_id = ? AND artifact_id = ?
                """,
                (organization_id, project_id, artifact_id),
            ).fetchone()
        if status_snapshot_row is None:
            raise ExternalEvidenceNotFound("external_evidence_object_not_found")
        status_snapshot = self._artifact_from_row(status_snapshot_row)

        if self._source_status_resolver is None:
            source_state = None
            source_denial = "artifact_source_status_unavailable"
        else:
            try:
                source_state = self._source_status_resolver(
                    organization_id, project_id, status_snapshot.source_id
                )
            except Exception:  # noqa: BLE001 - trust-boundary failures must fail closed
                source_state = None
                source_denial = "artifact_source_status_unavailable"
            else:
                source_denial = (
                    None if source_state == "enabled" else "artifact_source_not_enabled"
                )

        with self._transaction() as connection:
            artifact_row = connection.execute(
                """
                SELECT * FROM external_evidence_artifacts
                WHERE organization_id = ? AND project_id = ? AND artifact_id = ?
                """,
                (organization_id, project_id, artifact_id),
            ).fetchone()
            if artifact_row is None:
                raise ExternalEvidenceNotFound("external_evidence_object_not_found")
            try:
                admitted = self._artifact_from_row(artifact_row)
            except ContractValidationError:
                admitted = status_snapshot
                denial = "artifact_changed_during_admission"

            captured_at = self._parse_admission_timestamp(admitted.captured_at)
            freshness_expires_at = self._parse_admission_timestamp(
                admitted.freshness_expires_at
            )
            if captured_at > as_of_timestamp:
                denial = "artifact_not_yet_captured"
            elif freshness_expires_at <= as_of_timestamp:
                denial = "artifact_stale"

            if (
                denial == "artifact_changed_during_admission"
                or admitted != status_snapshot
            ):
                denial = "artifact_changed_during_admission"
            elif source_denial:
                denial = source_denial

            review_rows = connection.execute(
                """
                SELECT rowid AS review_sequence, decision, reviewed_at
                FROM external_evidence_reviews
                WHERE organization_id = ? AND project_id = ? AND artifact_id = ?
                """,
                (organization_id, project_id, artifact_id),
            ).fetchall()
            eligible_reviews = [
                row
                for row in review_rows
                if captured_at
                <= self._parse_admission_timestamp(row["reviewed_at"])
                <= as_of_timestamp
            ]
            if not eligible_reviews:
                denial = denial or "artifact_review_required"
            else:
                latest_review = max(
                    eligible_reviews,
                    key=lambda row: int(row["review_sequence"]),
                )
                if latest_review["decision"] != "approved":
                    denial = denial or "artifact_review_rejected"

            dispositions = {
                row["disposition"]
                for row in connection.execute(
                    """
                    SELECT disposition FROM external_evidence_supersessions
                    WHERE organization_id = ? AND project_id = ?
                      AND predecessor_artifact_id = ?
                    """,
                    (organization_id, project_id, artifact_id),
                ).fetchall()
            }
            if "revoked" in dispositions:
                denial = "artifact_revoked"
            elif "superseded" in dispositions:
                denial = "artifact_superseded"

            action = "artifact.admission_denied" if denial else "artifact.admitted"
            details: dict[str, Any] = {"decision": "denied" if denial else "approved"}
            if denial:
                details["failure_code"] = denial
            self._append_audit(
                connection,
                scope,
                object_type="artifact",
                object_id=artifact_id,
                action=action,
                details=details,
            )

        if denial:
            raise ExternalEvidenceAdmissionError(denial)
        if admitted is None:  # pragma: no cover - defensive invariant
            raise ExternalEvidenceNotFound("external_evidence_object_not_found")
        return admitted

    def record_review(self, principal: PrincipalLike, review: EvidenceReview) -> EvidenceReview:
        scope = self._scope(principal, review.organization_id, review.project_id, REVIEW)
        if review.reviewer_user_id != scope.actor_user_id:
            raise ExternalEvidenceConflict("reviewer_identity_must_be_server_owned")
        with self._transaction(integrity_error_code="review_persistence_conflict") as connection:
            artifact = connection.execute(
                """
                SELECT artifact_hash FROM external_evidence_artifacts
                WHERE organization_id = ? AND project_id = ? AND artifact_id = ?
                """,
                (review.organization_id, review.project_id, review.artifact_id),
            ).fetchone()
            if artifact is None:
                raise ExternalEvidenceNotFound("external_evidence_object_not_found")
            if artifact["artifact_hash"] != review.artifact_hash:
                raise ExternalEvidenceConflict("review_artifact_hash_mismatch")
            latest_review = connection.execute(
                """
                SELECT reviewed_at FROM external_evidence_reviews
                WHERE organization_id = ? AND project_id = ? AND artifact_id = ?
                ORDER BY rowid DESC LIMIT 1
                """,
                (review.organization_id, review.project_id, review.artifact_id),
            ).fetchone()
            if latest_review is not None and self._parse_admission_timestamp(
                review.reviewed_at
            ) < self._parse_admission_timestamp(latest_review["reviewed_at"]):
                raise ExternalEvidenceConflict("review_timestamp_must_be_monotonic")
            connection.execute(
                """
                INSERT INTO external_evidence_reviews(
                    organization_id, project_id, review_id, artifact_id, artifact_hash,
                    reviewer_user_id, decision, reason, reviewed_at, review_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    review.organization_id,
                    review.project_id,
                    review.review_id,
                    review.artifact_id,
                    review.artifact_hash,
                    review.reviewer_user_id,
                    review.decision,
                    review.reason,
                    review.reviewed_at,
                    review.review_hash,
                ),
            )
            self._append_audit(
                connection,
                scope,
                object_type="review",
                object_id=review.review_id,
                action="review.recorded",
                details={"decision": review.decision},
            )
        return review

    def list_reviews_for_artifact(
        self,
        principal: PrincipalLike,
        *,
        organization_id: str,
        project_id: str,
        artifact_id: str,
    ) -> list[EvidenceReview]:
        self._scope(principal, organization_id, project_id, READ)
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT * FROM external_evidence_reviews
                WHERE organization_id = ? AND project_id = ? AND artifact_id = ?
                ORDER BY rowid
                """,
                (organization_id, project_id, artifact_id),
            ).fetchall()
        return [
            EvidenceReview(**{key: row[key] for key in EvidenceReview.__dataclass_fields__})
            for row in rows
        ]

    def record_supersession(
        self, principal: PrincipalLike, record: SupersessionRecord
    ) -> SupersessionRecord:
        scope = self._scope(principal, record.organization_id, record.project_id, REVIEW)
        if record.actor_user_id != scope.actor_user_id:
            raise ExternalEvidenceConflict("supersession_actor_must_be_server_owned")
        if record.successor_artifact_id == record.predecessor_artifact_id:
            raise ExternalEvidenceConflict("artifact_cannot_supersede_itself")
        with self._transaction(integrity_error_code="supersession_persistence_conflict") as connection:
            predecessor = connection.execute(
                """
                SELECT artifact_hash FROM external_evidence_artifacts
                WHERE organization_id = ? AND project_id = ? AND artifact_id = ?
                """,
                (record.organization_id, record.project_id, record.predecessor_artifact_id),
            ).fetchone()
            if predecessor is None or predecessor["artifact_hash"] != record.predecessor_artifact_hash:
                raise ExternalEvidenceConflict("predecessor_artifact_mismatch")
            if record.successor_artifact_id is not None:
                successor = connection.execute(
                    """
                    SELECT artifact_hash FROM external_evidence_artifacts
                    WHERE organization_id = ? AND project_id = ? AND artifact_id = ?
                    """,
                    (record.organization_id, record.project_id, record.successor_artifact_id),
                ).fetchone()
                if successor is None or successor["artifact_hash"] != record.successor_artifact_hash:
                    raise ExternalEvidenceConflict("successor_artifact_mismatch")
            connection.execute(
                """
                INSERT INTO external_evidence_supersessions(
                    organization_id, project_id, record_id, predecessor_artifact_id,
                    predecessor_artifact_hash, disposition, reason, actor_user_id,
                    recorded_at, record_hash, successor_artifact_id, successor_artifact_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.organization_id,
                    record.project_id,
                    record.record_id,
                    record.predecessor_artifact_id,
                    record.predecessor_artifact_hash,
                    record.disposition,
                    record.reason,
                    record.actor_user_id,
                    record.recorded_at,
                    record.record_hash,
                    record.successor_artifact_id,
                    record.successor_artifact_hash,
                ),
            )
            self._append_audit(
                connection,
                scope,
                object_type="supersession",
                object_id=record.record_id,
                action="artifact.disposition_recorded",
                details={"disposition": record.disposition},
            )
        return record

    def list_supersessions_for_artifact(
        self,
        principal: PrincipalLike,
        *,
        organization_id: str,
        project_id: str,
        artifact_id: str,
    ) -> list[SupersessionRecord]:
        self._scope(principal, organization_id, project_id, READ)
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT * FROM external_evidence_supersessions
                WHERE organization_id = ? AND project_id = ?
                  AND (predecessor_artifact_id = ? OR successor_artifact_id = ?)
                ORDER BY recorded_at, record_id
                """,
                (organization_id, project_id, artifact_id, artifact_id),
            ).fetchall()
        return [
            SupersessionRecord(
                **{key: row[key] for key in SupersessionRecord.__dataclass_fields__}
            )
            for row in rows
        ]

    def list_audit_events(
        self,
        principal: PrincipalLike,
        *,
        organization_id: str,
        project_id: str,
    ) -> list[dict[str, Any]]:
        self._scope(principal, organization_id, project_id, READ)
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT event_id, organization_id, project_id, object_type, object_id,
                       action, actor_user_id, occurred_at, details_json
                FROM external_evidence_audit_events
                WHERE organization_id = ? AND project_id = ?
                ORDER BY sequence_id
                """,
                (organization_id, project_id),
            ).fetchall()
        return [
            {
                **{key: row[key] for key in row.keys() if key != "details_json"},
                "details": json.loads(row["details_json"]),
            }
            for row in rows
        ]

    def _scope(
        self,
        principal: PrincipalLike,
        organization_id: str,
        project_id: str,
        action: str,
    ) -> AuthorizedScope:
        return self._authorizer.authorize(
            principal,
            organization_id=organization_id,
            project_id=project_id,
            action=action,
        )

    def _append_audit(
        self,
        connection: sqlite3.Connection,
        scope: AuthorizedScope,
        *,
        object_type: str,
        object_id: str,
        action: str,
        details: Mapping[str, Any],
    ) -> None:
        if not set(details).issubset(self._SAFE_AUDIT_KEYS):
            raise ExternalEvidencePersistenceError("unsafe_audit_detail_key")
        for value in details.values():
            if value is not None and not isinstance(value, (str, int, bool)):
                raise ExternalEvidencePersistenceError("unsafe_audit_detail_value")
            if isinstance(value, str) and len(value) > 128:
                raise ExternalEvidencePersistenceError("unsafe_audit_detail_value")
        occurred_at = self._clock()
        event_material = {
            "sequence_hint": int(
                connection.execute(
                    "SELECT COALESCE(MAX(sequence_id), 0) + 1 FROM external_evidence_audit_events"
                ).fetchone()[0]
            ),
            "organization_id": scope.organization_id,
            "project_id": scope.project_id,
            "object_type": object_type,
            "object_id": object_id,
            "action": action,
            "actor_user_id": scope.actor_user_id,
            "occurred_at": occurred_at,
            "details": dict(details),
        }
        connection.execute(
            """
            INSERT INTO external_evidence_audit_events(
                event_id, organization_id, project_id, object_type, object_id,
                action, actor_user_id, occurred_at, details_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"evt:{sha256_hex(event_material)[:32]}",
                scope.organization_id,
                scope.project_id,
                object_type,
                object_id,
                action,
                scope.actor_user_id,
                occurred_at,
                canonical_json(dict(details)),
            ),
        )

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self._db_path, timeout=self._busy_timeout_ms / 1000)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(f"PRAGMA busy_timeout = {self._busy_timeout_ms}")
        connection.execute("PRAGMA journal_mode = WAL")
        try:
            yield connection
        finally:
            connection.close()

    @contextmanager
    def _transaction(
        self, *, integrity_error_code: str | None = None
    ) -> Iterator[sqlite3.Connection]:
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                yield connection
                connection.commit()
            except sqlite3.IntegrityError:
                connection.rollback()
                if integrity_error_code is None:
                    raise
                raise ExternalEvidenceConflict(integrity_error_code) from None
            except BaseException:
                connection.rollback()
                raise

    @staticmethod
    def _parse_admission_timestamp(value: str) -> datetime:
        if not isinstance(value, str) or len(value) > 40:
            raise ExternalEvidenceAdmissionError("invalid_admission_timestamp")
        normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError as exc:
            raise ExternalEvidenceAdmissionError("invalid_admission_timestamp") from exc
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ExternalEvidenceAdmissionError("invalid_admission_timestamp")
        return parsed

    def _migrations(self) -> Sequence[Migration]:
        return (
            (1, "fc20_04_p0_a_v1", self._migration_statements_v1()),
            (2, "fc20_04_review_hardening_v2", self._migration_statements_v2()),
        )

    def _migration_statements_v1(self) -> Sequence[str]:
        return (
            """
            CREATE TABLE external_evidence_candidates (
                organization_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                candidate_id TEXT NOT NULL,
                source_id TEXT NOT NULL,
                provider_id TEXT NOT NULL,
                operation TEXT NOT NULL,
                canonical_url TEXT NOT NULL,
                title TEXT NOT NULL,
                discovered_at TEXT NOT NULL,
                payload_hash TEXT NOT NULL,
                provenance_hash TEXT NOT NULL,
                review_state TEXT NOT NULL CHECK (review_state = 'review_required'),
                PRIMARY KEY (organization_id, project_id, candidate_id)
            )
            """,
            """
            CREATE TABLE external_evidence_jobs (
                organization_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                job_id TEXT NOT NULL,
                provider_id TEXT NOT NULL,
                operation TEXT NOT NULL,
                idempotency_key_hash TEXT NOT NULL,
                request_hash TEXT NOT NULL,
                state TEXT NOT NULL CHECK (state IN ('queued','running','partial','succeeded','failed','cancelled')),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                candidate_id TEXT,
                result_count INTEGER NOT NULL CHECK (result_count >= 0),
                failure_code TEXT,
                PRIMARY KEY (organization_id, project_id, job_id),
                UNIQUE (organization_id, project_id, job_id, candidate_id),
                UNIQUE (organization_id, project_id, idempotency_key_hash),
                FOREIGN KEY (organization_id, project_id, candidate_id)
                    REFERENCES external_evidence_candidates(organization_id, project_id, candidate_id)
            )
            """,
            """
            CREATE TABLE external_evidence_artifacts (
                organization_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                artifact_id TEXT NOT NULL,
                job_id TEXT NOT NULL,
                candidate_id TEXT NOT NULL,
                source_id TEXT NOT NULL,
                canonical_url TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                provenance_hash TEXT NOT NULL,
                captured_at TEXT NOT NULL,
                freshness_expires_at TEXT NOT NULL,
                artifact_hash TEXT NOT NULL,
                review_state TEXT NOT NULL CHECK (review_state = 'review_required'),
                PRIMARY KEY (organization_id, project_id, artifact_id),
                UNIQUE (organization_id, project_id, source_id, content_hash),
                FOREIGN KEY (organization_id, project_id, job_id, candidate_id)
                    REFERENCES external_evidence_jobs(
                        organization_id, project_id, job_id, candidate_id
                    ),
                FOREIGN KEY (organization_id, project_id, candidate_id)
                    REFERENCES external_evidence_candidates(organization_id, project_id, candidate_id)
            )
            """,
            """
            CREATE TABLE external_evidence_reviews (
                organization_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                review_id TEXT NOT NULL,
                artifact_id TEXT NOT NULL,
                artifact_hash TEXT NOT NULL,
                reviewer_user_id TEXT NOT NULL,
                decision TEXT NOT NULL CHECK (decision IN ('approved','rejected')),
                reason TEXT NOT NULL,
                reviewed_at TEXT NOT NULL,
                review_hash TEXT NOT NULL,
                PRIMARY KEY (organization_id, project_id, review_id),
                FOREIGN KEY (organization_id, project_id, artifact_id)
                    REFERENCES external_evidence_artifacts(organization_id, project_id, artifact_id)
            )
            """,
            """
            CREATE TABLE external_evidence_supersessions (
                organization_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                record_id TEXT NOT NULL,
                predecessor_artifact_id TEXT NOT NULL,
                predecessor_artifact_hash TEXT NOT NULL,
                disposition TEXT NOT NULL CHECK (disposition IN ('superseded','revoked')),
                reason TEXT NOT NULL,
                actor_user_id TEXT NOT NULL,
                recorded_at TEXT NOT NULL,
                record_hash TEXT NOT NULL,
                successor_artifact_id TEXT,
                successor_artifact_hash TEXT,
                PRIMARY KEY (organization_id, project_id, record_id),
                FOREIGN KEY (organization_id, project_id, predecessor_artifact_id)
                    REFERENCES external_evidence_artifacts(organization_id, project_id, artifact_id),
                FOREIGN KEY (organization_id, project_id, successor_artifact_id)
                    REFERENCES external_evidence_artifacts(organization_id, project_id, artifact_id)
            )
            """,
            """
            CREATE TABLE external_evidence_audit_events (
                sequence_id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT NOT NULL UNIQUE,
                organization_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                object_type TEXT NOT NULL,
                object_id TEXT NOT NULL,
                action TEXT NOT NULL,
                actor_user_id TEXT NOT NULL,
                occurred_at TEXT NOT NULL,
                details_json TEXT NOT NULL
            )
            """,
            "CREATE INDEX idx_external_evidence_jobs_scope_state ON external_evidence_jobs(organization_id, project_id, state)",
            "CREATE INDEX idx_external_evidence_artifacts_scope_freshness ON external_evidence_artifacts(organization_id, project_id, freshness_expires_at)",
            "CREATE INDEX idx_external_evidence_audit_scope_sequence ON external_evidence_audit_events(organization_id, project_id, sequence_id)",
        )

    def _migration_statements_v2(self) -> Sequence[str]:
        return (
            "UPDATE external_evidence_jobs SET failure_code = 'legacy_unspecified_failure' WHERE state IN ('failed','partial') AND failure_code IS NULL",
            "CREATE INDEX idx_external_evidence_reviews_scope_artifact ON external_evidence_reviews(organization_id, project_id, artifact_id, reviewed_at)",
            "CREATE INDEX idx_external_evidence_supersessions_scope_predecessor ON external_evidence_supersessions(organization_id, project_id, predecessor_artifact_id, disposition)",
            "CREATE INDEX idx_external_evidence_supersessions_scope_successor ON external_evidence_supersessions(organization_id, project_id, successor_artifact_id)",
        )

    @staticmethod
    def _candidate_from_row(row: sqlite3.Row) -> DiscoveryCandidate:
        return DiscoveryCandidate(
            **{key: row[key] for key in DiscoveryCandidate.__dataclass_fields__}
        )

    @staticmethod
    def _job_from_row(row: sqlite3.Row) -> ExtractionJob:
        return ExtractionJob(**{key: row[key] for key in ExtractionJob.__dataclass_fields__})

    @staticmethod
    def _artifact_from_row(row: sqlite3.Row) -> EvidenceArtifact:
        return EvidenceArtifact(
            **{key: row[key] for key in EvidenceArtifact.__dataclass_fields__}
        )
