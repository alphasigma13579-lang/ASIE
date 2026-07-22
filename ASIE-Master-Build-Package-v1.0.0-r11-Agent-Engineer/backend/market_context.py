from __future__ import annotations

"""Local-only market location contracts; never a source of financial truth."""

from typing import Any

RECORD_TYPES = {"competitor", "site_candidate", "coverage_area", "market_signal"}
DATA_MODES = {"demo_simulated_external", "user_verified", "official_open_data"}


def normalize_market_location(payload: dict[str, Any]) -> dict[str, Any]:
    record_type = str(payload.get("record_type") or "")
    if record_type not in RECORD_TYPES:
        raise ValueError("market_record_type_invalid")
    data_mode = str(payload.get("data_mode") or "demo_simulated_external")
    if data_mode not in DATA_MODES:
        raise ValueError("market_data_mode_invalid")
    coordinates = payload.get("coordinates")
    if coordinates is not None:
        if not isinstance(coordinates, dict) or not isinstance(coordinates.get("lat"), (int, float)) or not isinstance(coordinates.get("lng"), (int, float)):
            raise ValueError("market_coordinates_invalid")
        if not -90 <= coordinates["lat"] <= 90 or not -180 <= coordinates["lng"] <= 180:
            raise ValueError("market_coordinates_out_of_range")
    return {
        "record_type": record_type,
        "name": str(payload.get("name") or "غير مسمى"),
        "sector": str(payload.get("sector") or ""),
        "geography": str(payload.get("geography") or ""),
        "coordinates": coordinates,
        "attributes": payload.get("attributes") if isinstance(payload.get("attributes"), dict) else {},
        "evidence_refs": [str(ref) for ref in payload.get("evidence_refs", []) if ref],
        "data_mode": data_mode,
        "display_badge": "DEMO / LOCAL ONLY" if data_mode == "demo_simulated_external" else "USER VERIFIED",
        "production_admission": "blocked" if data_mode == "demo_simulated_external" else "local_only",
        "external_fetch_enabled": False,
        "decision_authority": "context_only",
    }


def market_provider_policy() -> dict[str, Any]:
    return {
        "provider": "none",
        "google_maps_enabled": False,
        "gps_enabled": False,
        "external_fetch_enabled": False,
        "consent_required_before_location": True,
        "privacy_status": "local_only_design",
        "may_change_finance_or_verdict": False,
    }
