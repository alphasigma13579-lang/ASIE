from __future__ import annotations

from typing import Any

from backend.contracts import json_dumps, now_iso

SOURCE_STATES = {"candidate", "blocked", "enabled", "reference_only"}
ENABLED_SOURCE_REQUIRED_FIELDS = [
    "source_id",
    "publisher",
    "route",
    "url",
    "terms_url",
    "terms_hash",
    "license_snapshot_ref",
    "attribution",
    "classification",
    "pdpl_check",
    "nca_check",
    "lawful_purpose",
    "reviewer",
    "reviewer_decision",
]


def seed_source_records() -> list[dict[str, Any]]:
    return [
        {
            "source_id": "GASTAT_CANDIDATE",
            "publisher": "General Authority for Statistics",
            "route": "official_open_dataset_or_api",
            "state": "candidate",
            "url": "https://www.stats.gov.sa",
            "terms_url": "",
            "terms_hash": "",
            "license_snapshot_ref": "",
            "attribution": "",
            "classification": "",
            "pdpl_check": "",
            "nca_check": "",
            "lawful_purpose": "",
            "reviewer": "",
            "reviewer_decision": "",
            "reviewed_at": "",
            "notes_json": json_dumps(
                {
                    "required_before_enablement": ENABLED_SOURCE_REQUIRED_FIELDS,
                    "state_reason": "Candidate only. Exact open dataset/API and human review are still missing.",
                }
            ),
        },
        candidate_source(
            "SAMA_CANDIDATE",
            "Saudi Central Bank",
            "https://www.sama.gov.sa",
            "Candidate only. Exact open dataset/API and human review are still missing.",
        ),
        candidate_source(
            "MOF_CANDIDATE",
            "Ministry of Finance",
            "https://www.mof.gov.sa",
            "Candidate only. Exact open dataset/API and human review are still missing.",
        ),
        {
            "source_id": "VISION_2030_REFERENCE",
            "publisher": "Vision 2030",
            "route": "official_strategy_reference_only_v1",
            "state": "reference_only",
            "url": "https://www.vision2030.gov.sa",
            "terms_url": "",
            "terms_hash": "",
            "license_snapshot_ref": "",
            "attribution": "Reference-only strategic context. No automated data extraction.",
            "classification": "reference_only",
            "pdpl_check": "no_backend_retrieval",
            "nca_check": "no_backend_retrieval",
            "lawful_purpose": "strategic_reference_only",
            "reviewer": "ASIE policy seed",
            "reviewer_decision": "reference_only",
            "reviewed_at": now_iso(),
            "notes_json": json_dumps(
                {
                    "blocked": "automated data extraction or official endorsement claim",
                    "allowed": "reference-only context with no source fetch",
                }
            ),
        },
        {
            "source_id": "MOSTAQL_PROJECTS",
            "publisher": "Mostaql",
            "route": "reference_only_link",
            "state": "reference_only",
            "url": "https://mostaql.com/projects",
            "terms_url": "",
            "terms_hash": "",
            "license_snapshot_ref": "",
            "attribution": "Outbound link and private user-authored note only.",
            "classification": "reference_only",
            "pdpl_check": "no_backend_retrieval",
            "nca_check": "no_backend_retrieval",
            "lawful_purpose": "user_private_note_only",
            "reviewer": "ASIE policy seed",
            "reviewer_decision": "reference_only",
            "reviewed_at": now_iso(),
            "notes_json": json_dumps(
                {
                    "blocked": "backend fetch, crawl, summarize, embed, score, monitor, or alert",
                    "allowed": "outbound link and private user-authored note only",
                }
            ),
        },
    ]


def candidate_source(source_id: str, publisher: str, url: str, state_reason: str) -> dict[str, Any]:
    return {
        "source_id": source_id,
        "publisher": publisher,
        "route": "official_open_dataset_or_api",
        "state": "candidate",
        "url": url,
        "terms_url": "",
        "terms_hash": "",
        "license_snapshot_ref": "",
        "attribution": "",
        "classification": "",
        "pdpl_check": "",
        "nca_check": "",
        "lawful_purpose": "",
        "reviewer": "",
        "reviewer_decision": "",
        "reviewed_at": "",
        "notes_json": json_dumps(
            {
                "required_before_enablement": ENABLED_SOURCE_REQUIRED_FIELDS,
                "state_reason": state_reason,
            }
        ),
    }


def normalize_source_review(payload: dict[str, Any]) -> dict[str, Any]:
    requested_state = str(payload.get("state") or "candidate")
    if requested_state not in SOURCE_STATES:
        raise ValueError("state must be candidate, blocked, enabled, or reference_only")

    if requested_state == "enabled":
        missing = [key for key in ENABLED_SOURCE_REQUIRED_FIELDS if not payload.get(key)]
        if missing:
            raise PermissionError(
                "enabled sources require exact URL, terms, terms hash, license snapshot, attribution, "
                "classification, PDPL/NCA checks, lawful purpose, and reviewer approval. "
                f"Missing: {', '.join(missing)}"
            )
        if str(payload.get("reviewer_decision")) != "approved":
            raise PermissionError("enabled sources require reviewer_decision=approved")

    return {
        "source_id": str(payload.get("source_id") or ""),
        "publisher": str(payload.get("publisher") or "Unknown publisher"),
        "route": str(payload.get("route") or "manual_review"),
        "state": requested_state,
        "url": str(payload.get("url") or ""),
        "terms_url": str(payload.get("terms_url") or ""),
        "terms_hash": str(payload.get("terms_hash") or ""),
        "license_snapshot_ref": str(payload.get("license_snapshot_ref") or ""),
        "attribution": str(payload.get("attribution") or ""),
        "classification": str(payload.get("classification") or ""),
        "pdpl_check": str(payload.get("pdpl_check") or ""),
        "nca_check": str(payload.get("nca_check") or ""),
        "lawful_purpose": str(payload.get("lawful_purpose") or ""),
        "reviewer": str(payload.get("reviewer") or ""),
        "reviewer_decision": str(payload.get("reviewer_decision") or ""),
        "reviewed_at": now_iso(),
        "notes_json": json_dumps(
            {
                "notes": payload.get("notes", ""),
                "state_reason": payload.get("state_reason", ""),
                "external_fetch_allowed": False,
            }
        ),
    }


def source_policy(records: list[dict[str, Any]], profile_id: str) -> dict[str, Any]:
    return {
        "profile_id": profile_id,
        "external_fetch_enabled": False,
        "rule": "Default deny. Exact public open dataset/API only after terms, attribution, classification, and human review.",
        "enabled_sources": [row for row in records if row["state"] == "enabled"],
        "candidate_sources": [row for row in records if row["state"] == "candidate"],
        "reference_only": [row for row in records if row["state"] == "reference_only"],
        "blocked_sources": [row for row in records if row["state"] == "blocked"],
    }


def source_review_checklist(record: dict[str, Any]) -> dict[str, Any]:
    items = [
        {
            "field": field,
            "label": field.replace("_", " "),
            "required_for_enabled": True,
            "status": "complete" if record.get(field) else "missing",
        }
        for field in ENABLED_SOURCE_REQUIRED_FIELDS
    ]
    return {
        "source_id": record["source_id"],
        "state": record["state"],
        "can_enable": all(item["status"] == "complete" for item in items)
        and record.get("reviewer_decision") == "approved",
        "items": items,
        "external_fetch_enabled_after_approval": False,
    }
