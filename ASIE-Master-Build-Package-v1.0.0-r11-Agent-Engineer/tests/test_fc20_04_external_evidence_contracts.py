from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from backend.external_evidence_contracts import (
    ContractValidationError,
    DiscoveryCandidate,
    EvidenceArtifact,
    EvidenceReview,
    ExtractionJob,
    SupersessionRecord,
    sha256_hex,
)


NOW = "2026-08-05T00:00:00Z"
LATER = "2026-09-05T00:00:00Z"
HASH_A = sha256_hex("a")
HASH_B = sha256_hex("b")


def candidate(**overrides: object) -> DiscoveryCandidate:
    values = {
        "candidate_id": "candidate-1",
        "organization_id": "org-1",
        "project_id": "project-1",
        "source_id": "source-1",
        "provider_id": "tavily",
        "operation": "search",
        "canonical_url": "https://example.com/evidence",
        "title": "Bounded candidate metadata",
        "discovered_at": NOW,
        "payload_hash": HASH_A,
        "provenance_hash": HASH_B,
    }
    values.update(overrides)
    return DiscoveryCandidate(**values)  # type: ignore[arg-type]


def artifact(**overrides: object) -> EvidenceArtifact:
    values = {
        "artifact_id": "artifact-1",
        "organization_id": "org-1",
        "project_id": "project-1",
        "job_id": "job-1",
        "candidate_id": "candidate-1",
        "source_id": "source-1",
        "canonical_url": "https://example.com/evidence",
        "content_hash": HASH_A,
        "provenance_hash": HASH_B,
        "captured_at": NOW,
        "freshness_expires_at": LATER,
    }
    values.update(overrides)
    return EvidenceArtifact.build(**values)  # type: ignore[arg-type]


def test_five_contracts_are_immutable_and_hash_bound() -> None:
    discovery = candidate()
    job = ExtractionJob(
        job_id="job-1",
        organization_id="org-1",
        project_id="project-1",
        provider_id="tavily",
        operation="extract",
        idempotency_key_hash=HASH_A,
        request_hash=HASH_B,
        state="queued",
        created_at=NOW,
        updated_at=NOW,
        candidate_id=discovery.candidate_id,
    )
    evidence = artifact()
    review = EvidenceReview.build(
        review_id="review-1",
        organization_id="org-1",
        project_id="project-1",
        artifact_id=evidence.artifact_id,
        artifact_hash=evidence.artifact_hash,
        reviewer_user_id="reviewer-1",
        decision="approved",
        reason="Source and provenance verified.",
        reviewed_at=NOW,
    )
    supersession = SupersessionRecord.build(
        record_id="supersession-1",
        organization_id="org-1",
        project_id="project-1",
        predecessor_artifact_id=evidence.artifact_id,
        predecessor_artifact_hash=evidence.artifact_hash,
        disposition="revoked",
        reason="Source authority revoked.",
        actor_user_id="reviewer-1",
        recorded_at=NOW,
    )

    assert discovery.review_state == "review_required"
    assert evidence.review_state == "review_required"
    assert len(review.review_hash) == 64
    assert len(supersession.record_hash) == 64
    with pytest.raises(FrozenInstanceError):
        job.state = "running"  # type: ignore[misc]


def test_candidate_and_artifact_cannot_self_claim_approval() -> None:
    with pytest.raises(ContractValidationError, match="candidate_must_be_review_required"):
        candidate(review_state="approved")
    with pytest.raises(ContractValidationError, match="artifact_must_be_review_required"):
        EvidenceArtifact(
            **{**artifact().as_dict(), "review_state": "approved"}
        )


def test_contracts_reject_unsafe_url_hash_and_naive_time() -> None:
    with pytest.raises(ContractValidationError, match="invalid_canonical_url"):
        candidate(canonical_url="http://127.0.0.1/private")
    with pytest.raises(ContractValidationError, match="invalid_canonical_url"):
        candidate(canonical_url="https://[::1")
    for forbidden_url in (
        "https://127.0.0.1/private",
        "https://localhost/private",
        "https://[::1]/private",
        "https://192.168.1.10/private",
    ):
        with pytest.raises(ContractValidationError, match="canonical_url_host_forbidden"):
            candidate(canonical_url=forbidden_url)
    with pytest.raises(ContractValidationError, match="invalid_payload_hash"):
        candidate(payload_hash="not-a-hash")
    with pytest.raises(ContractValidationError, match="invalid_discovered_at"):
        candidate(discovered_at="2026-08-05T00:00:00")
    with pytest.raises(ContractValidationError, match="freshness_must_follow_capture"):
        artifact(freshness_expires_at=NOW)


def test_failed_and_partial_jobs_require_failure_codes() -> None:
    base = {
        "job_id": "job-1",
        "organization_id": "org-1",
        "project_id": "project-1",
        "provider_id": "tavily",
        "operation": "extract",
        "idempotency_key_hash": HASH_A,
        "request_hash": HASH_B,
        "created_at": NOW,
        "updated_at": NOW,
    }
    for state in ("failed", "partial"):
        with pytest.raises(ContractValidationError, match="failure_code_required_for_state"):
            ExtractionJob(**base, state=state)


def test_record_hashes_detect_tampering() -> None:
    evidence = artifact()
    with pytest.raises(ContractValidationError, match="artifact_hash_mismatch"):
        EvidenceArtifact(**{**evidence.as_dict(), "content_hash": sha256_hex("tampered")})

    review = EvidenceReview.build(
        review_id="review-1",
        organization_id="org-1",
        project_id="project-1",
        artifact_id=evidence.artifact_id,
        artifact_hash=evidence.artifact_hash,
        reviewer_user_id="reviewer-1",
        decision="rejected",
        reason="Insufficient provenance.",
        reviewed_at=NOW,
    )
    with pytest.raises(ContractValidationError, match="review_hash_mismatch"):
        EvidenceReview(**{**review.as_dict(), "reason": "Changed after review."})


def test_supersession_shape_is_fail_closed() -> None:
    with pytest.raises(ContractValidationError, match="successor_required"):
        SupersessionRecord.build(
            record_id="supersession-1",
            organization_id="org-1",
            project_id="project-1",
            predecessor_artifact_id="artifact-1",
            predecessor_artifact_hash=HASH_A,
            disposition="superseded",
            reason="New version available.",
            actor_user_id="reviewer-1",
            recorded_at=NOW,
        )


def test_p0_a_modules_have_no_network_or_provider_client_dependency() -> None:
    backend = Path(__file__).resolve().parents[1] / "backend"
    forbidden_modules = {
        "requests",
        "socket",
        "httpx",
        "aiohttp",
        "urllib.request",
        "backend.live_provider_clients",
        "backend.external_acquisition",
        "backend.provider_security_control_plane",
    }

    imported: set[str] = set()
    for name in (
        "external_evidence_contracts.py",
        "external_evidence_authorization.py",
        "external_evidence_persistence.py",
    ):
        tree = ast.parse((backend / name).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
                imported.update(f"{node.module}.{alias.name}" for alias in node.names)

    assert not {
        imported_name
        for imported_name in imported
        for forbidden in forbidden_modules
        if imported_name == forbidden or imported_name.startswith(f"{forbidden}.")
    }
