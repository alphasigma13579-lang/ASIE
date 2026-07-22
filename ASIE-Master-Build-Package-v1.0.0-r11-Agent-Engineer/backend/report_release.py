"""Human review and release records for funder report projections."""

from __future__ import annotations

from typing import Any

from backend.snapshot_assembly import canonical_hash


REPORT_RELEASE_CONTRACT = "funder.report.release.v1"


def build_release_record(projection: dict[str, Any], review: dict[str, Any] | None) -> dict[str, Any]:
    profile = projection.get("profile_readiness") or {}
    snapshot_id = projection.get("snapshot_id", "")
    checks: list[str] = []
    if not review:
        checks.append("human_review_missing")
    else:
        if review.get("snapshot_id") != snapshot_id:
            checks.append("review_snapshot_mismatch")
        if not str(review.get("reviewer") or "").strip():
            checks.append("reviewer_missing")
        if review.get("decision") != "approved_local":
            checks.append("review_not_approved_local")
    if profile.get("status") != "FUNDER_PROFILE_READY":
        checks.append("profile_requirements_not_ready")
    state = "RELEASED_LOCAL" if not checks else "REVIEW_REQUIRED" if "review_not_approved_local" not in checks else "REJECTED_LOCAL"
    record = {
        "contract_id": REPORT_RELEASE_CONTRACT,
        "release_state": state,
        "snapshot_id": snapshot_id,
        "project_id": projection.get("project_id", ""),
        "run_id": projection.get("run_id", ""),
        "profile_id": profile.get("profile_id", projection.get("profile_id", "")),
        "projection_hash": projection.get("projection_hash", ""),
        "readiness_hash": profile.get("readiness_hash", ""),
        "review_id": review.get("review_id") if review else None,
        "reviewer": review.get("reviewer") if review else None,
        "review_decision": review.get("decision") if review else None,
        "reviewed_at": review.get("created_at") if review else None,
        "blocking_reasons": sorted(set(checks)),
        "disclaimer": "إصدار محلي بعد مراجعة بشرية؛ لا يمثل قبولاً أو قراراً من جهة تمويل خارجية.",
    }
    record["release_hash"] = canonical_hash(record)
    return record


def validate_release_record(projection: dict[str, Any], record: dict[str, Any]) -> None:
    if record.get("snapshot_id") != projection.get("snapshot_id"):
        raise ValueError("release_snapshot_mismatch")
    if record.get("projection_hash") != projection.get("projection_hash"):
        raise ValueError("release_projection_hash_mismatch")
    expected = dict(record)
    expected.pop("release_hash", None)
    if record.get("release_hash") != canonical_hash(expected):
        raise ValueError("release_hash_mismatch")
