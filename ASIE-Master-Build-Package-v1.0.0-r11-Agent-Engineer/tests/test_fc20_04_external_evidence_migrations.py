from __future__ import annotations

import sqlite3

import pytest

from backend.external_evidence_authorization import ExternalEvidenceAuthorizer
from backend.external_evidence_persistence import (
    ExternalEvidenceMigrationError,
    ExternalEvidenceStore,
)


NOW = "2026-08-05T00:00:00Z"


class Ownership:
    def project_belongs_to(self, organization_id: str, project_id: str) -> bool:
        return True


def build_store(path) -> ExternalEvidenceStore:
    return ExternalEvidenceStore(
        path,
        authorizer=ExternalEvidenceAuthorizer(Ownership()),
        clock=lambda: NOW,
    )


def test_migration_registry_is_idempotent_and_schema_is_isolated(tmp_path) -> None:
    db_path = tmp_path / "schema.sqlite3"
    store = build_store(db_path)
    store.initialize()
    first = store.migration_registry()
    store.initialize()
    second = store.migration_registry()

    assert first == second
    assert first == [
        {
            "version": 1,
            "migration_id": "fc20_04_p0_a_v1",
            "checksum": first[0]["checksum"],
            "applied_at": NOW,
        }
    ]
    assert len(first[0]["checksum"]) == 64

    connection = sqlite3.connect(db_path)
    try:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name LIKE 'external_evidence_%'"
            )
        }
        assert {
            "external_evidence_schema_migrations",
            "external_evidence_candidates",
            "external_evidence_jobs",
            "external_evidence_artifacts",
            "external_evidence_reviews",
            "external_evidence_supersessions",
            "external_evidence_audit_events",
        }.issubset(tables)

        for table in tables - {"external_evidence_schema_migrations"}:
            columns = {
                row[1]
                for row in connection.execute(f"PRAGMA table_info({table})")
            }
            assert "payload" not in columns
            assert "secret" not in columns
            if table != "external_evidence_audit_events":
                assert {"organization_id", "project_id"}.issubset(columns)
    finally:
        connection.close()


def test_failed_migration_rolls_back_registry_and_schema(tmp_path) -> None:
    class BrokenMigrationStore(ExternalEvidenceStore):
        def _migration_statements_v1(self):  # type: ignore[no-untyped-def]
            return (*super()._migration_statements_v1(), "CREATE TABLE broken(")

    db_path = tmp_path / "broken.sqlite3"
    store = BrokenMigrationStore(
        db_path,
        authorizer=ExternalEvidenceAuthorizer(Ownership()),
        clock=lambda: NOW,
    )
    with pytest.raises(sqlite3.OperationalError):
        store.initialize()

    connection = sqlite3.connect(db_path)
    try:
        tables = list(
            connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name LIKE 'external_evidence_%'"
            )
        )
        assert tables == []
    finally:
        connection.close()


def test_migration_checksum_drift_fails_closed(tmp_path) -> None:
    db_path = tmp_path / "checksum.sqlite3"
    build_store(db_path).initialize()

    class DriftedMigrationStore(ExternalEvidenceStore):
        def _migration_statements_v1(self):  # type: ignore[no-untyped-def]
            return (*super()._migration_statements_v1(), "CREATE INDEX drifted ON external_evidence_jobs(job_id)")

    drifted = DriftedMigrationStore(
        db_path,
        authorizer=ExternalEvidenceAuthorizer(Ownership()),
        clock=lambda: NOW,
    )
    with pytest.raises(ExternalEvidenceMigrationError, match="checksum_mismatch"):
        drifted.initialize()


def test_database_rejects_artifact_job_candidate_mismatch(tmp_path) -> None:
    db_path = tmp_path / "lineage.sqlite3"
    build_store(db_path).initialize()
    digest = "a" * 64

    connection = sqlite3.connect(db_path)
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        for candidate_id, source_id in (
            ("candidate-1", "source-1"),
            ("candidate-2", "source-2"),
        ):
            connection.execute(
                """
                INSERT INTO external_evidence_candidates(
                    organization_id, project_id, candidate_id, source_id, provider_id,
                    operation, canonical_url, title, discovered_at, payload_hash,
                    provenance_hash, review_state
                ) VALUES (?, 'project-a', ?, ?, 'tavily', 'search', ?, 'candidate', ?, ?, ?,
                          'review_required')
                """,
                (
                    "org-a",
                    candidate_id,
                    source_id,
                    f"https://example.com/{source_id}",
                    NOW,
                    digest,
                    digest,
                ),
            )
        connection.execute(
            """
            INSERT INTO external_evidence_jobs(
                organization_id, project_id, job_id, provider_id, operation,
                idempotency_key_hash, request_hash, state, created_at, updated_at,
                candidate_id, result_count, failure_code
            ) VALUES ('org-a', 'project-a', 'job-1', 'tavily', 'extract', ?, ?, 'succeeded',
                      ?, ?, 'candidate-1', 1, NULL)
            """,
            (digest, "b" * 64, NOW, NOW),
        )

        with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
            connection.execute(
                """
                INSERT INTO external_evidence_artifacts(
                    organization_id, project_id, artifact_id, job_id, candidate_id,
                    source_id, canonical_url, content_hash, provenance_hash, captured_at,
                    freshness_expires_at, artifact_hash, review_state
                ) VALUES ('org-a', 'project-a', 'artifact-1', 'job-1', 'candidate-2',
                          'source-2', 'https://example.com/source-2', ?, ?, ?,
                          '2026-09-05T00:00:00Z', ?, 'review_required')
                """,
                (digest, digest, NOW, digest),
            )
    finally:
        connection.close()
