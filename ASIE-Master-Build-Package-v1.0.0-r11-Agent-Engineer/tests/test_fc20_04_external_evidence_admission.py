from __future__ import annotations

from dataclasses import dataclass, replace

import pytest

from backend.external_evidence_authorization import (
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
from backend.external_evidence_persistence import (
    ExternalEvidenceAdmissionError,
    ExternalEvidenceConflict,
    ExternalEvidenceNotFound,
    ExternalEvidenceStore,
)


NOW = "2026-08-05T00:00:00Z"
T1 = "2026-08-05T00:01:00Z"
T2 = "2026-08-05T00:02:00Z"
T3 = "2026-08-05T00:03:00Z"
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


class SourceStates:
    def __init__(self) -> None:
        self.states = {("org-a", "project-a", "source-1"): "enabled"}
        self.fail = False

    def __call__(
        self, organization_id: str, project_id: str, source_id: str
    ) -> str | None:
        if self.fail:
            raise RuntimeError("source_registry_unavailable")
        return self.states.get((organization_id, project_id, source_id))


def actor(org: str = "org-a", role: str = "organization_owner", user: str = "owner-a") -> Principal:
    return Principal(user, f"session-{org}", org, role)


@pytest.fixture
def source_states() -> SourceStates:
    return SourceStates()


@pytest.fixture
def store(tmp_path, source_states: SourceStates) -> ExternalEvidenceStore:
    result = ExternalEvidenceStore(
        tmp_path / "admission.sqlite3",
        authorizer=ExternalEvidenceAuthorizer(Ownership()),
        clock=lambda: T3,
        source_status_resolver=source_states,
    )
    result.initialize()
    return result


def seed_artifact(
    store: ExternalEvidenceStore,
    *,
    freshness_expires_at: str = LATER,
) -> EvidenceArtifact:
    owner = actor()
    candidate = DiscoveryCandidate(
        candidate_id="candidate-1",
        organization_id="org-a",
        project_id="project-a",
        source_id="source-1",
        provider_id="tavily",
        operation="search",
        canonical_url="https://example.com/evidence",
        title="Candidate",
        discovered_at=NOW,
        payload_hash=sha256_hex("payload"),
        provenance_hash=sha256_hex("provenance"),
    )
    store.create_candidate(owner, candidate)
    queued = ExtractionJob(
        job_id="job-1",
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
    store.transition_job(owner, replace(running, state="succeeded", updated_at=T2, result_count=1))
    artifact = EvidenceArtifact.build(
        artifact_id="artifact-1",
        organization_id="org-a",
        project_id="project-a",
        job_id="job-1",
        candidate_id="candidate-1",
        source_id="source-1",
        canonical_url="https://example.com/evidence",
        content_hash=sha256_hex("content"),
        provenance_hash=sha256_hex("provenance"),
        captured_at=T2,
        freshness_expires_at=freshness_expires_at,
    )
    return store.create_or_get_artifact(owner, artifact)[0]


def review(
    store: ExternalEvidenceStore,
    artifact: EvidenceArtifact,
    decision: str,
    review_id: str,
    *,
    reviewed_at: str = T3,
) -> None:
    store.record_review(
        actor(role="reviewer", user="reviewer-a"),
        EvidenceReview.build(
            review_id=review_id,
            organization_id="org-a",
            project_id="project-a",
            artifact_id=artifact.artifact_id,
            artifact_hash=artifact.artifact_hash,
            reviewer_user_id="reviewer-a",
            decision=decision,
            reason=f"Human decision: {decision}.",
            reviewed_at=reviewed_at,
        ),
    )


def admit(store: ExternalEvidenceStore, *, as_of: str = T3) -> EvidenceArtifact:
    return store.require_approved_artifact(
        actor(),
        organization_id="org-a",
        project_id="project-a",
        artifact_id="artifact-1",
        as_of=as_of,
    )


def test_review_required_and_candidate_ids_are_denied(store: ExternalEvidenceStore) -> None:
    seed_artifact(store)
    with pytest.raises(ExternalEvidenceAdmissionError, match="artifact_review_required"):
        admit(store)
    with pytest.raises(ExternalEvidenceNotFound):
        store.require_approved_artifact(
            actor(),
            organization_id="org-a",
            project_id="project-a",
            artifact_id="candidate-1",
            as_of=T3,
        )


def test_latest_rejected_review_is_denied(store: ExternalEvidenceStore) -> None:
    artifact = seed_artifact(store)
    # Equal reviewed_at values are resolved by server-recorded row order, not review_id.
    review(store, artifact, "approved", "review-z-approved-first")
    review(store, artifact, "rejected", "review-a-rejected-last")
    with pytest.raises(ExternalEvidenceAdmissionError, match="artifact_review_rejected"):
        admit(store)


def test_backdated_review_recorded_later_is_rejected(
    store: ExternalEvidenceStore,
) -> None:
    artifact = seed_artifact(store)
    review(store, artifact, "approved", "review-approved", reviewed_at=T3)
    with pytest.raises(ExternalEvidenceConflict, match="review_timestamp_must_be_monotonic"):
        review(store, artifact, "rejected", "review-backdated", reviewed_at=T2)


def test_fresh_latest_approved_artifact_is_admitted_and_audited(
    store: ExternalEvidenceStore,
) -> None:
    artifact = seed_artifact(store)
    review(store, artifact, "approved", "review-1")
    assert admit(store).artifact_hash == artifact.artifact_hash
    events = store.list_audit_events(actor(), organization_id="org-a", project_id="project-a")
    assert any(
        event["action"] == "artifact.admitted"
        and event["details"] == {"decision": "approved"}
        for event in events
    )


def test_stale_artifact_is_denied(store: ExternalEvidenceStore) -> None:
    artifact = seed_artifact(store, freshness_expires_at=T3)
    review(store, artifact, "approved", "review-1")
    with pytest.raises(ExternalEvidenceAdmissionError, match="artifact_stale"):
        admit(store)


def test_artifact_captured_after_as_of_is_denied(
    store: ExternalEvidenceStore,
) -> None:
    artifact = seed_artifact(store)
    review(store, artifact, "approved", "review-1")
    with pytest.raises(ExternalEvidenceAdmissionError, match="artifact_not_yet_captured"):
        admit(store, as_of=T1)


@pytest.mark.parametrize("source_state", ("blocked", "candidate", "reference_only", None))
def test_non_enabled_source_is_denied_at_admission(
    store: ExternalEvidenceStore,
    source_states: SourceStates,
    source_state: str | None,
) -> None:
    artifact = seed_artifact(store)
    review(store, artifact, "approved", "review-1")
    if source_state is None:
        source_states.states.pop(("org-a", "project-a", "source-1"))
    else:
        source_states.states[("org-a", "project-a", "source-1")] = source_state
    with pytest.raises(ExternalEvidenceAdmissionError, match="artifact_source_not_enabled"):
        admit(store)


def test_source_status_failure_is_visible_and_fails_closed(
    store: ExternalEvidenceStore,
    source_states: SourceStates,
) -> None:
    artifact = seed_artifact(store)
    review(store, artifact, "approved", "review-1")
    source_states.fail = True
    with pytest.raises(ExternalEvidenceAdmissionError, match="source_status_unavailable"):
        admit(store)
    events = store.list_audit_events(
        actor(), organization_id="org-a", project_id="project-a"
    )
    assert any(
        event["action"] == "artifact.admission_denied"
        and event["details"].get("failure_code")
        == "artifact_source_status_unavailable"
        for event in events
    )


def test_missing_source_status_resolver_fails_closed(tmp_path) -> None:
    store_without_resolver = ExternalEvidenceStore(
        tmp_path / "missing-source-resolver.sqlite3",
        authorizer=ExternalEvidenceAuthorizer(Ownership()),
        clock=lambda: T3,
    )
    store_without_resolver.initialize()
    artifact = seed_artifact(store_without_resolver)
    review(store_without_resolver, artifact, "approved", "review-1")
    with pytest.raises(ExternalEvidenceAdmissionError, match="source_status_unavailable"):
        admit(store_without_resolver)


@pytest.mark.parametrize("disposition", ("revoked", "superseded"))
def test_disposed_artifact_is_denied(
    store: ExternalEvidenceStore, disposition: str
) -> None:
    artifact = seed_artifact(store)
    review(store, artifact, "approved", "review-1")
    successor_id = None
    successor_hash = None
    if disposition == "superseded":
        successor = EvidenceArtifact.build(
            artifact_id="artifact-2",
            organization_id=artifact.organization_id,
            project_id=artifact.project_id,
            job_id=artifact.job_id,
            candidate_id=artifact.candidate_id,
            source_id=artifact.source_id,
            canonical_url=artifact.canonical_url,
            content_hash=sha256_hex("new-content"),
            provenance_hash=artifact.provenance_hash,
            captured_at=artifact.captured_at,
            freshness_expires_at=artifact.freshness_expires_at,
        )
        store.create_or_get_artifact(actor(), successor)
        successor_id = successor.artifact_id
        successor_hash = successor.artifact_hash
    store.record_supersession(
        actor(role="reviewer", user="reviewer-a"),
        SupersessionRecord.build(
            record_id=f"record-{disposition}",
            organization_id="org-a",
            project_id="project-a",
            predecessor_artifact_id=artifact.artifact_id,
            predecessor_artifact_hash=artifact.artifact_hash,
            disposition=disposition,
            reason=f"Artifact {disposition}.",
            actor_user_id="reviewer-a",
            recorded_at=T3,
            successor_artifact_id=successor_id,
            successor_artifact_hash=successor_hash,
        ),
    )
    with pytest.raises(ExternalEvidenceAdmissionError, match=f"artifact_{disposition}"):
        admit(store)


def test_admission_is_cross_tenant_denied(store: ExternalEvidenceStore) -> None:
    artifact = seed_artifact(store)
    review(store, artifact, "approved", "review-1")
    with pytest.raises(ExternalEvidenceAuthorizationError, match="access_denied"):
        store.require_approved_artifact(
            actor("org-b", user="owner-b"),
            organization_id="org-a",
            project_id="project-a",
            artifact_id="artifact-1",
            as_of=T3,
        )


def test_admission_audit_failure_fails_closed(tmp_path) -> None:
    class FailingAdmissionAuditStore(ExternalEvidenceStore):
        def _append_audit(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
            if kwargs.get("action") == "artifact.admitted":
                raise RuntimeError("admission_audit_unavailable")
            super()._append_audit(*args, **kwargs)

    failing = FailingAdmissionAuditStore(
        tmp_path / "admission-audit.sqlite3",
        authorizer=ExternalEvidenceAuthorizer(Ownership()),
        clock=lambda: T3,
    )
    failing.initialize()
    artifact = seed_artifact(failing)
    review(failing, artifact, "approved", "review-1")

    with pytest.raises(RuntimeError, match="admission_audit_unavailable"):
        admit(failing)
    events = failing.list_audit_events(
        actor(), organization_id="org-a", project_id="project-a"
    )
    assert all(event["action"] != "artifact.admitted" for event in events)
