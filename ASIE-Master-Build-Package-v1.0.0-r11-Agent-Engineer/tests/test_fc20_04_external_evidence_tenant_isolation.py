from __future__ import annotations

from dataclasses import dataclass, replace

import pytest

from backend.external_evidence_authorization import (
    CANCEL,
    READ,
    REVIEW,
    WRITE,
    ExternalEvidenceAuthorizationError,
    ExternalEvidenceAuthorizer,
)
from backend.external_evidence_contracts import (
    DiscoveryCandidate,
    EvidenceArtifact,
    EvidenceReview,
    ExtractionJob,
    SupersessionRecord,
    sha256_hex,
)
from backend.external_evidence_persistence import ExternalEvidenceStore


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


def actor(org: str, role: str = "organization_owner", user: str | None = None) -> Principal:
    suffix = org[-1]
    return Principal(user or f"owner-{suffix}", f"session-{suffix}", org, role)


def seed_scope(store: ExternalEvidenceStore) -> tuple[EvidenceArtifact, ExtractionJob]:
    owner = actor("org-a")
    candidate = DiscoveryCandidate(
        candidate_id="candidate-shared-id",
        organization_id="org-a",
        project_id="project-a",
        source_id="source-1",
        provider_id="tavily",
        operation="search",
        canonical_url="https://example.com/evidence",
        title="Tenant A evidence",
        discovered_at=NOW,
        payload_hash=sha256_hex("payload"),
        provenance_hash=sha256_hex("provenance"),
    )
    store.create_candidate(owner, candidate)
    queued = ExtractionJob(
        job_id="job-shared-id",
        organization_id="org-a",
        project_id="project-a",
        provider_id="tavily",
        operation="extract",
        idempotency_key_hash=sha256_hex("key"),
        request_hash=sha256_hex("request"),
        state="queued",
        created_at=NOW,
        updated_at=NOW,
        candidate_id=candidate.candidate_id,
    )
    store.create_or_get_job(owner, queued)
    running = store.transition_job(owner, replace(queued, state="running", updated_at=T1))
    succeeded = store.transition_job(
        owner, replace(running, state="succeeded", updated_at=T2, result_count=1)
    )
    artifact = EvidenceArtifact.build(
        artifact_id="artifact-shared-id",
        organization_id="org-a",
        project_id="project-a",
        job_id=succeeded.job_id,
        candidate_id=candidate.candidate_id,
        source_id="source-1",
        canonical_url="https://example.com/evidence",
        content_hash=sha256_hex("content"),
        provenance_hash=sha256_hex("provenance"),
        captured_at=T2,
        freshness_expires_at=LATER,
    )
    store.create_or_get_artifact(owner, artifact)
    reviewer = actor("org-a", "reviewer", "reviewer-a")
    review = EvidenceReview.build(
        review_id="review-shared-id",
        organization_id="org-a",
        project_id="project-a",
        artifact_id=artifact.artifact_id,
        artifact_hash=artifact.artifact_hash,
        reviewer_user_id="reviewer-a",
        decision="approved",
        reason="Verified by tenant A reviewer.",
        reviewed_at=T2,
    )
    store.record_review(reviewer, review)
    record = SupersessionRecord.build(
        record_id="supersession-shared-id",
        organization_id="org-a",
        project_id="project-a",
        predecessor_artifact_id=artifact.artifact_id,
        predecessor_artifact_hash=artifact.artifact_hash,
        disposition="revoked",
        reason="Revocation test.",
        actor_user_id="reviewer-a",
        recorded_at=T2,
    )
    store.record_supersession(reviewer, record)
    return artifact, succeeded


def test_authorization_matrix_is_same_tenant_and_project_owned() -> None:
    authorizer = ExternalEvidenceAuthorizer(Ownership())
    owner_a = actor("org-a")
    for action in (READ, WRITE, REVIEW, CANCEL):
        assert authorizer.authorize(
            owner_a,
            organization_id="org-a",
            project_id="project-a",
            action=action,
        ).organization_id == "org-a"

    for action in (READ, WRITE, REVIEW, CANCEL):
        with pytest.raises(ExternalEvidenceAuthorizationError, match="access_denied"):
            authorizer.authorize(
                actor("org-b"),
                organization_id="org-a",
                project_id="project-a",
                action=action,
            )

    with pytest.raises(ExternalEvidenceAuthorizationError, match="access_denied"):
        authorizer.authorize(
            owner_a,
            organization_id="org-a",
            project_id="client-invented-project",
            action=READ,
        )


def test_cross_tenant_denied_for_all_five_objects_and_job_actions(tmp_path) -> None:
    store = ExternalEvidenceStore(
        tmp_path / "tenant.sqlite3",
        authorizer=ExternalEvidenceAuthorizer(Ownership()),
        clock=lambda: NOW,
    )
    store.initialize()
    artifact, succeeded_job = seed_scope(store)
    owner_a = actor("org-a")
    attacker = actor("org-b")

    assert store.get_candidate(
        owner_a,
        organization_id="org-a",
        project_id="project-a",
        candidate_id="candidate-shared-id",
    ).title == "Tenant A evidence"
    assert store.get_job(
        owner_a,
        organization_id="org-a",
        project_id="project-a",
        job_id="job-shared-id",
    ).state == "succeeded"
    assert store.get_artifact(
        owner_a,
        organization_id="org-a",
        project_id="project-a",
        artifact_id="artifact-shared-id",
    ).artifact_hash == artifact.artifact_hash
    assert len(
        store.list_reviews_for_artifact(
            owner_a,
            organization_id="org-a",
            project_id="project-a",
            artifact_id="artifact-shared-id",
        )
    ) == 1
    assert len(
        store.list_supersessions_for_artifact(
            owner_a,
            organization_id="org-a",
            project_id="project-a",
            artifact_id="artifact-shared-id",
        )
    ) == 1

    denied_calls = (
        lambda: store.get_candidate(
            attacker,
            organization_id="org-a",
            project_id="project-a",
            candidate_id="candidate-shared-id",
        ),
        lambda: store.get_job(
            attacker,
            organization_id="org-a",
            project_id="project-a",
            job_id="job-shared-id",
        ),
        lambda: store.get_artifact(
            attacker,
            organization_id="org-a",
            project_id="project-a",
            artifact_id="artifact-shared-id",
        ),
        lambda: store.list_reviews_for_artifact(
            attacker,
            organization_id="org-a",
            project_id="project-a",
            artifact_id="artifact-shared-id",
        ),
        lambda: store.list_supersessions_for_artifact(
            attacker,
            organization_id="org-a",
            project_id="project-a",
            artifact_id="artifact-shared-id",
        ),
        lambda: store.transition_job(
            attacker,
            replace(succeeded_job, state="cancelled", updated_at=LATER),
        ),
    )
    for call in denied_calls:
        with pytest.raises(ExternalEvidenceAuthorizationError, match="access_denied"):
            call()
