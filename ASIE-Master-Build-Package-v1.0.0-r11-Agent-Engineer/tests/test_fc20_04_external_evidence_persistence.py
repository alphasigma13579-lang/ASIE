from __future__ import annotations

from dataclasses import dataclass, replace

import pytest

from backend.external_evidence_authorization import ExternalEvidenceAuthorizer
from backend.external_evidence_contracts import (
    DiscoveryCandidate,
    EvidenceArtifact,
    EvidenceReview,
    ExtractionJob,
    sha256_hex,
)
from backend.external_evidence_persistence import (
    ExternalEvidenceConflict,
    ExternalEvidenceNotFound,
    ExternalEvidenceStore,
)


NOW = "2026-08-05T00:00:00Z"
T1 = "2026-08-05T00:01:00Z"
T2 = "2026-08-05T00:02:00Z"
LATER = "2026-09-05T00:00:00Z"


@dataclass(frozen=True)
class Principal:
    user_id: str
    session_id: str
    organization_id: str | None
    role: str | None
    platform_role: str | None = None

    def can(self, permission: str) -> bool:
        return False


class Ownership:
    def project_belongs_to(self, organization_id: str, project_id: str) -> bool:
        return (organization_id, project_id) in {
            ("org-a", "project-a"),
            ("org-b", "project-b"),
        }


def principal(role: str = "organization_owner", user_id: str = "owner-a") -> Principal:
    return Principal(user_id, "session-a", "org-a", role)


def candidate() -> DiscoveryCandidate:
    return DiscoveryCandidate(
        candidate_id="candidate-1",
        organization_id="org-a",
        project_id="project-a",
        source_id="source-1",
        provider_id="tavily",
        operation="search",
        canonical_url="https://example.com/evidence",
        title="Hashed external evidence candidate",
        discovered_at=NOW,
        payload_hash=sha256_hex("raw-provider-payload-never-stored"),
        provenance_hash=sha256_hex("provenance"),
    )


def job(*, job_id: str = "job-1", key_material: str = "key-1") -> ExtractionJob:
    return ExtractionJob(
        job_id=job_id,
        organization_id="org-a",
        project_id="project-a",
        provider_id="tavily",
        operation="extract",
        idempotency_key_hash=sha256_hex(key_material),
        request_hash=sha256_hex("request-1"),
        state="queued",
        created_at=NOW,
        updated_at=NOW,
        candidate_id="candidate-1",
    )


def artifact(*, artifact_id: str = "artifact-1", **overrides: str) -> EvidenceArtifact:
    material = {
        "artifact_id": artifact_id,
        "organization_id": "org-a",
        "project_id": "project-a",
        "job_id": "job-1",
        "candidate_id": "candidate-1",
        "source_id": "source-1",
        "canonical_url": "https://example.com/evidence",
        "content_hash": sha256_hex("content"),
        "provenance_hash": sha256_hex("provenance"),
        "captured_at": T2,
        "freshness_expires_at": LATER,
    }
    material.update(overrides)
    return EvidenceArtifact.build(**material)


@pytest.fixture
def store(tmp_path) -> ExternalEvidenceStore:
    result = ExternalEvidenceStore(
        tmp_path / "external-evidence.sqlite3",
        authorizer=ExternalEvidenceAuthorizer(Ownership()),
        clock=lambda: NOW,
    )
    result.initialize()
    return result


def seed_succeeded_job(store: ExternalEvidenceStore) -> None:
    actor = principal()
    store.create_candidate(actor, candidate())
    queued, created = store.create_or_get_job(actor, job())
    assert created is True
    running = replace(queued, state="running", updated_at=T1)
    store.transition_job(actor, running)
    store.transition_job(actor, replace(running, state="succeeded", updated_at=T2, result_count=1))


def test_idempotent_job_and_evidence_replay_do_not_duplicate(store: ExternalEvidenceStore) -> None:
    seed_succeeded_job(store)
    actor = principal()

    replayed, created = store.create_or_get_job(actor, job(job_id="job-replay"))
    assert created is False
    assert replayed.job_id == "job-1"

    stored, created = store.create_or_get_artifact(actor, artifact())
    assert created is True
    duplicate, created = store.create_or_get_artifact(actor, artifact(artifact_id="artifact-replay"))
    assert created is False
    assert duplicate.artifact_id == stored.artifact_id


def test_idempotency_collision_with_different_request_fails_closed(store: ExternalEvidenceStore) -> None:
    actor = principal()
    store.create_candidate(actor, candidate())
    store.create_or_get_job(actor, job())
    conflicting = replace(job(job_id="job-other"), request_hash=sha256_hex("other-request"))
    with pytest.raises(ExternalEvidenceConflict, match="idempotency_key_reused"):
        store.create_or_get_job(actor, conflicting)


def test_partial_or_cancelled_job_cannot_create_artifact(store: ExternalEvidenceStore) -> None:
    actor = principal()
    store.create_candidate(actor, candidate())
    queued, _ = store.create_or_get_job(actor, job())
    running = store.transition_job(actor, replace(queued, state="running", updated_at=T1))
    store.transition_job(
        actor,
        replace(running, state="partial", updated_at=T2, result_count=1, failure_code="provider_partial"),
    )
    with pytest.raises(ExternalEvidenceConflict, match="requires_succeeded_job"):
        store.create_or_get_artifact(actor, artifact())

    second, _ = store.create_or_get_job(actor, job(job_id="job-2", key_material="key-2"))
    cancelled = store.transition_job(actor, replace(second, state="cancelled", updated_at=T1))
    with pytest.raises(ExternalEvidenceConflict, match="invalid_job_state_transition"):
        store.transition_job(actor, replace(cancelled, state="succeeded", updated_at=T2))


def test_artifact_candidate_must_match_succeeded_job_and_rolls_back(
    store: ExternalEvidenceStore,
) -> None:
    seed_succeeded_job(store)
    actor = principal()
    store.create_candidate(
        actor,
        replace(
            candidate(),
            candidate_id="candidate-2",
            source_id="source-2",
            canonical_url="https://example.com/other-evidence",
            provenance_hash=sha256_hex("other-provenance"),
        ),
    )

    mismatched = artifact(
        artifact_id="artifact-mismatched-candidate",
        candidate_id="candidate-2",
        source_id="source-2",
        canonical_url="https://example.com/other-evidence",
        provenance_hash=sha256_hex("other-provenance"),
    )
    for _ in range(2):
        with pytest.raises(ExternalEvidenceConflict, match="artifact_candidate_mismatch"):
            store.create_or_get_artifact(actor, mismatched)

    with pytest.raises(ExternalEvidenceNotFound):
        store.get_artifact(
            actor,
            organization_id="org-a",
            project_id="project-a",
            artifact_id=mismatched.artifact_id,
        )

    rejection_events = [
        event
        for event in store.list_audit_events(
            actor, organization_id="org-a", project_id="project-a"
        )
        if event["action"] == "artifact.rejected"
    ]
    assert len(rejection_events) == 2
    assert all(
        event["details"]
        == {"decision": "denied", "failure_code": "artifact_candidate_mismatch"}
        for event in rejection_events
    )


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("source_id", "source-other"),
        ("canonical_url", "https://example.com/other-evidence"),
        ("provenance_hash", sha256_hex("other-provenance")),
    ),
)
def test_artifact_provenance_must_match_candidate_and_rolls_back(
    store: ExternalEvidenceStore, field: str, value: str
) -> None:
    seed_succeeded_job(store)
    actor = principal()
    mismatched = artifact(artifact_id=f"artifact-mismatched-{field}", **{field: value})

    with pytest.raises(ExternalEvidenceConflict, match="artifact_provenance_mismatch"):
        store.create_or_get_artifact(actor, mismatched)

    with pytest.raises(ExternalEvidenceNotFound):
        store.get_artifact(
            actor,
            organization_id="org-a",
            project_id="project-a",
            artifact_id=mismatched.artifact_id,
        )


def test_review_is_hash_bound_and_audit_is_redacted(store: ExternalEvidenceStore) -> None:
    seed_succeeded_job(store)
    actor = principal()
    evidence, _ = store.create_or_get_artifact(actor, artifact())
    reviewer = principal(role="reviewer", user_id="reviewer-a")
    review = EvidenceReview.build(
        review_id="review-1",
        organization_id="org-a",
        project_id="project-a",
        artifact_id=evidence.artifact_id,
        artifact_hash=evidence.artifact_hash,
        reviewer_user_id="reviewer-a",
        decision="approved",
        reason="Human review completed; this reason is not copied into audit details.",
        reviewed_at=NOW,
    )
    store.record_review(reviewer, review)

    events = store.list_audit_events(actor, organization_id="org-a", project_id="project-a")
    serialized = str(events)
    assert "raw-provider-payload-never-stored" not in serialized
    assert review.reason not in serialized
    assert any(event["details"].get("decision") == "approved" for event in events)


def test_audit_failure_rolls_back_object_write(tmp_path) -> None:
    class FailingAuditStore(ExternalEvidenceStore):
        def _append_audit(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
            raise RuntimeError("audit_unavailable")

    db_path = tmp_path / "rollback.sqlite3"
    failing = FailingAuditStore(
        db_path,
        authorizer=ExternalEvidenceAuthorizer(Ownership()),
        clock=lambda: NOW,
    )
    failing.initialize()
    with pytest.raises(RuntimeError, match="audit_unavailable"):
        failing.create_candidate(principal(), candidate())

    healthy = ExternalEvidenceStore(
        db_path,
        authorizer=ExternalEvidenceAuthorizer(Ownership()),
        clock=lambda: NOW,
    )
    with pytest.raises(ExternalEvidenceNotFound):
        healthy.get_candidate(
            principal(),
            organization_id="org-a",
            project_id="project-a",
            candidate_id="candidate-1",
        )


def test_rejection_audit_failure_keeps_artifact_absent(tmp_path) -> None:
    class FailingRejectionAuditStore(ExternalEvidenceStore):
        def _append_audit(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
            if kwargs.get("action") == "artifact.rejected":
                raise RuntimeError("rejection_audit_unavailable")
            super()._append_audit(*args, **kwargs)

    db_path = tmp_path / "rejection-audit.sqlite3"
    failing = FailingRejectionAuditStore(
        db_path,
        authorizer=ExternalEvidenceAuthorizer(Ownership()),
        clock=lambda: NOW,
    )
    failing.initialize()
    seed_succeeded_job(failing)
    mismatched = artifact(
        artifact_id="artifact-rejected-without-audit",
        provenance_hash=sha256_hex("wrong-provenance"),
    )

    with pytest.raises(RuntimeError, match="rejection_audit_unavailable"):
        failing.create_or_get_artifact(principal(), mismatched)

    healthy = ExternalEvidenceStore(
        db_path,
        authorizer=ExternalEvidenceAuthorizer(Ownership()),
        clock=lambda: NOW,
    )
    with pytest.raises(ExternalEvidenceNotFound):
        healthy.get_artifact(
            principal(),
            organization_id="org-a",
            project_id="project-a",
            artifact_id=mismatched.artifact_id,
        )
